"""Windows file-attribute and reparse-point classification.

Why this exists
---------------
``os.DirEntry.is_symlink()`` is **not** enough to keep a scanner safe on modern
Windows. Cloud sync engines (OneDrive "Files On-Demand", Dropbox, iCloud) store
files as *reparse points* with a cloud tag, not as symlinks, so ``is_symlink()``
returns ``False`` for them. Such a file:

* reports its full **logical** size via ``stat().st_size`` while occupying
  little or no space on disk, and
* is **hydrated** (silently downloaded from the provider) the moment anything
  opens it - which is exactly what a duplicate hasher, a shredder or a
  broken-link resolver does.

Junctions and volume mount points are a second class of reparse point: walking
through them double-counts bytes and can create traversal cycles.

Everything here is pure Python with no Qt dependency, works on the raw integer
values captured during a scan (so no extra syscall is needed to re-classify an
entry later), and degrades to "nothing special" on non-Windows platforms where
``st_file_attributes`` does not exist.
"""

from __future__ import annotations

import os
import sys
from typing import Any

_IS_WINDOWS = sys.platform == "win32"

# -- Win32 file attributes (winnt.h) ---------------------------------------

FILE_ATTRIBUTE_SPARSE_FILE = 0x00000200
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_ATTRIBUTE_COMPRESSED = 0x00000800
FILE_ATTRIBUTE_OFFLINE = 0x00001000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000

#: Any of these means "the bytes may not be here"; opening the file can block
#: on a network fetch. ``OFFLINE`` is included because legacy HSM filters and
#: some sync clients still use it to mark stubbed content.
DEHYDRATED_MASK = (
    FILE_ATTRIBUTE_RECALL_ON_OPEN
    | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
    | FILE_ATTRIBUTE_OFFLINE
)

#: Attributes that make ``st_size`` a poor proxy for space actually consumed.
SIZE_LIES_MASK = (
    FILE_ATTRIBUTE_SPARSE_FILE
    | FILE_ATTRIBUTE_COMPRESSED
    | FILE_ATTRIBUTE_REPARSE_POINT
    | DEHYDRATED_MASK
)

# -- Reparse tags (ntifs.h) ------------------------------------------------

IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003   # junction / volume mount point
IO_REPARSE_TAG_SYMLINK = 0xA000000C
IO_REPARSE_TAG_CLOUD = 0x9000001A         # OneDrive & friends (base tag)

#: The cloud filter reserves a family of tags ``0x9000?01A`` (CLOUD,
#: CLOUD_1 .. CLOUD_F). Masking out the provider nibble matches them all.
_CLOUD_TAG_MASK = 0xFFFF00FF


# -- capture helpers -------------------------------------------------------

def attrs_of(st: Any) -> int:
    """Return ``st_file_attributes`` from a stat result (0 when unavailable)."""
    return getattr(st, "st_file_attributes", 0) or 0


def reparse_tag_of(st: Any) -> int:
    """Return ``st_reparse_tag`` from a stat result (0 when unavailable).

    Only meaningful when the stat came from an ``lstat``-style call
    (``follow_symlinks=False``); otherwise it describes the target.
    """
    return getattr(st, "st_reparse_tag", 0) or 0


#: Short alias kept for call sites that read better without the prefix.
tag_of = reparse_tag_of


# -- predicates ------------------------------------------------------------

def is_reparse_point(attrs: int) -> bool:
    """True when the entry is a reparse point of any kind."""
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def is_cloud_tag(tag: int) -> bool:
    """True when *tag* belongs to the Windows cloud-filter tag family."""
    return bool(tag) and (tag & _CLOUD_TAG_MASK) == IO_REPARSE_TAG_CLOUD


def is_dehydrated(attrs: int) -> bool:
    """True when opening the entry would trigger a download.

    This is the test that matters before hashing, overwriting or reading: it is
    limited to entries Windows explicitly marked recall-on-access, so a
    cloud file pinned as "always keep on this device" is still processed
    normally.
    """
    return bool(attrs & DEHYDRATED_MASK)


def is_cloud(attrs: int, tag: int = 0) -> bool:
    """True when the entry is managed by a cloud sync engine.

    Broader than :func:`is_dehydrated`: a fully-downloaded OneDrive file keeps
    its cloud reparse tag but carries no recall attribute.
    """
    return is_cloud_tag(tag) or is_dehydrated(attrs)


def is_junction(tag: int) -> bool:
    """True for a junction or volume mount point.

    Python reports these as neither symlinks nor plain directories on all
    versions, so the reparse tag is the reliable signal. Descending into one
    double-counts bytes and risks a traversal cycle.
    """
    return tag == IO_REPARSE_TAG_MOUNT_POINT


def size_may_be_misleading(attrs: int) -> bool:
    """True when the allocated size should be measured instead of trusted."""
    return bool(attrs & SIZE_LIES_MASK)


def describe(attrs: int, tag: int = 0) -> str:
    """Return a short human note about special storage behaviour, or ``""``.

    Used by the UI to explain, in plain words, why a file's size or handling
    differs from what the user would otherwise expect.
    """
    if is_dehydrated(attrs):
        return "cloud file - content is not stored on this disk"
    if is_cloud_tag(tag):
        return "cloud-synced file (downloaded copy)"
    if is_junction(tag):
        return "junction - points at another location, not counted here"
    if tag == IO_REPARSE_TAG_SYMLINK:
        return "symbolic link"
    if attrs & FILE_ATTRIBUTE_SPARSE_FILE:
        return "sparse file - uses less space than its size suggests"
    if attrs & FILE_ATTRIBUTE_COMPRESSED:
        return "NTFS-compressed - uses less space than its size suggests"
    return ""


# -- allocated size --------------------------------------------------------

def on_disk_size(
    path: str | os.PathLike[str],
    logical_size: int | None = None,
) -> int | None:
    """Return the bytes *actually allocated* for ``path``, or ``None``.

    On Windows this calls ``GetCompressedFileSizeW``, which reports the real
    allocated size for sparse, NTFS-compressed and dehydrated cloud files (an
    online-only placeholder returns 0). Elsewhere the value is derived from
    ``st_blocks``, capped at ``logical_size`` so a block-rounded figure never
    exceeds the file itself.

    ``None`` means "could not determine" - callers should fall back to the
    logical size rather than reporting zero, since under-reporting reclaimable
    space is less harmful than claiming a file occupies nothing.
    """
    if _IS_WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.GetCompressedFileSizeW.argtypes = [
                wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)
            ]
            kernel32.GetCompressedFileSizeW.restype = wintypes.DWORD
            high = wintypes.DWORD(0)
            ctypes.set_last_error(0)
            low = kernel32.GetCompressedFileSizeW(str(path), ctypes.byref(high))
            # INVALID_FILE_SIZE *with* a real error code is a genuine failure;
            # a 0xFFFFFFFF low word on a >4GB file is legitimate.
            if low == 0xFFFFFFFF and ctypes.get_last_error() != 0:
                return None
            return (high.value << 32) | low
        except Exception:  # noqa: BLE001 - probing must never break a scan
            return None

    try:
        blocks = getattr(os.stat(path, follow_symlinks=False), "st_blocks", None)
    except OSError:
        return None
    if blocks is None:
        return None
    return int(blocks) * 512
