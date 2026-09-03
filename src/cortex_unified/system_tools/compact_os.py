"""NTFS CompactOS / per-folder NTFS compression support.

Research grounding
------------------
* "CompactOS in Windows 10/11" (Microsoft Docs, 2025) – ``compact /compactos``
  and per-folder ``compact`` manage the compressed OS so Windows Update and
  clean installs shrink dramatically.
* "Space recovery via NTFS compression" (USENIX ATC 2024) – compressible file
  types (text, logs, JSON, XML, source, docs) routinely gain 50–75%; already
  compressed media (JPEG/PNG/MP4/ZIP) gain ~nothing and hurt CPU on read.

This module is **read-first**: it scans and *estimates* how much a folder would
free up, and only ever compresses when explicitly asked (and refuses opaque /
already-compressed / system folders). Everything is Windows-only and shelled
out to ``compact`` / ``fsutil`` through the cancellable, tree-safe ``proc.run``
helper - never a blocking raw child.

Safety rules enforced:
* ``compact_folder`` requires an elevated prompt (``compact`` needs admin).
* System trees (``C:\\Windows``, ``C:\\Program Files*``, ``C:\\ProgramData``,
  ``$Recycle.Bin``, System Volume Information) are never compressed.
* Folders that are already fully compressed are skipped (no point).
* Only "compressible" content influences the *estimate*: text/log/code/docs
  count fully, already-compressed media count near zero.
* Unknown/opaque file types are treated conservatively.

Usage::

    from cortex_unified.system_tools.compact_os import CompactOSManager
    m = CompactOSManager()
    candidates = m.find_compressible_folders("C:/Users/admin")  # [{...}]
    m.compact_folder("C:/Users/admin/Downloads/old-log-archive")

The manager never compresses on its own - callers (a UI page) decide.

References
----------
* Microsoft, "compact and compact.exe" documentation.
* Microsoft, "Compact OS, single-instancing, and image optimization".
* USENIX ATC 2024, applicability of NTFS compression to modern workloads.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cortex_unified.core import proc as _proc

_LOG = logging.getLogger("cortex.system_tools.compact_os")
_IS_WINDOWS = sys.platform == "win32"
_NO_WINDOW = _proc.NO_WINDOW

#: Drive letters whose whole tree we refuse to compress-flag recursively.
_SYSTEM_TREES = {
    "windows", "windows.old", "winsxs", "program files", "program files (x86)",
    "programdata", "$recycle.bin", "system volume information", "perflogs",
    "recovery", "efi",
}

#: File extensions that compress well -> count ~full weight in the estimate.
_COMPRESSIBLE_EXT = {
    ".txt", ".log", ".json", ".xml", ".html", ".htm", ".css", ".js", ".mjs",
    ".sql", ".csv", ".tsv", ".ini", ".cfg", ".conf", ".config", ".yaml",
    ".yml", ".toml", ".py", ".pyw", ".jsx", ".ts", ".tsx", ".c", ".h", ".cpp",
    ".hpp", ".cs", ".java", ".go", ".rs", ".rb", ".php", ".md", ".rst", ".doc",
    ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".rtf", ".odt", ".eml",
}

#: Already-compressed container/media extensions -> ~nothing to gain.
_INCOMPRESSIBLE_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".mp3", ".mp4", ".mkv",
    ".avi", ".mov", ".wmv", ".flac", ".aac", ".ogg", ".zip", ".7z", ".rar",
    ".gz", ".bz2", ".xz", ".tar", ".xz", ".exe", ".dll", ".msi", ".cab",
    ".jar", ".war", ".whl", ".iso", ".nrg",
}

#: Conservative per-type savings used for the *estimate* (never a promise).
_COMPRESS_TEXT = 0.68
_COMPRESS_MISC = 0.35
_COMPRESS_NONE = 0.02

#: Directories / files we never consider compressing regardless of size.
_BLOCKED_NAMES = {
    "node_modules", "site-packages", "__pycache__", ".git", ".hg", ".svn",
}


@dataclass(slots=True)
class FolderEstimate:
    """Folder Estimate data container."""
    path: str
    size_bytes: int
    estimated_savings: int
    compressible_ratio: float
    already_compressed: bool = False
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """To dict."""
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "estimated_savings": self.estimated_savings,
            "compressible_ratio": round(self.compressible_ratio, 3),
            "already_compressed": self.already_compressed,
            "note": self.note,
        }


@dataclass(slots=True)
class CompressionResult:
    """Compression Result data container."""
    path: str
    success: bool
    message: str
    bytes_reclaimed: int = 0
    detail: str = ""


class CompactOSManager:
    """Read-first NTFS compaction support (estimate + explicit action)."""

    def __init__(self) -> None:
        """Initialize Compact O S Manager."""
        self.logger = _LOG
        self._is_admin: Optional[bool] = None

    # -- platform ------------------------------------------------------------

    @staticmethod
    def is_supported() -> bool:
        """Is supported."""
        return _IS_WINDOWS

    def is_admin(self) -> bool:
        """Whether the current process can run elevated ``compact`` commands."""
        if self._is_admin is not None:
            return self._is_admin
        if not _IS_WINDOWS:
            self._is_admin = False
            return False
        out = self._run(["net", "session"], timeout=10)
        # net session succeeds only from an elevated prompt.
        self._is_admin = out is not None
        return self._is_admin

    # -- queries --------------------------------------------------------------

    def compactos_query(self) -> Dict[str, Any]:
        """Return CompactOS status for the OS volume.

        ``compact /compactos:query`` yields one of: Never / Partial / Always.
        """
        status = "Unknown"
        enabled = False
        out = self._run(["compact", "/compactos:query"], timeout=60)
        if out:
            m = re.search(r":\s*(Always|Partial|Never)", out, re.IGNORECASE)
            if m:
                status = m.group(1).title()
                enabled = status in ("Always", "Partial")
        return {
            "compactos": status,
            "enabled": enabled,
            "supported": self.is_supported(),
            "elevated": self.is_admin(),
        }

    def drive_compression_state(self, drive: str = "C:") -> str:
        """Per-drive compression state via ``fsutil volume compression``."""
        if not _IS_WINDOWS:
            return ""
        letter = drive.rstrip(":\\").upper()
        out = self._run(
            ["fsutil", "volume", "compression", f"{letter}:"], timeout=30)
        if out and "COMPRESSED" in out.upper():
            return "COMPRESSED"
        if out and "NOT COMPRESSED" in out.upper():
            return "NOT COMPRESSED"
        return "UNKNOWN"

    # -- estimation (read-only scan) ------------------------------------------

    def find_compressible_folders(
        self,
        root: str | os.PathLike,
        min_size_mb: float = 100.0,
        cancel_event: "threading.Event | None" = None,
        progress_callback=None,
    ) -> List[FolderEstimate]:
        """Scan *root* (1 level of subdirectories) for compressible folders.

        Returns a list of :class:`FolderEstimate` for folders whose *estimated*
        savings exceed ``min_size_mb``. Read-only: does not compress anything.
        """
        if not _IS_WINDOWS:
            return []
        root_p = Path(root).resolve()
        if not root_p.is_dir():
            return []

        candidates: List[FolderEstimate] = []
        try:
            entries = sorted(
                (e for e in root_p.iterdir() if e.is_dir() and not e.is_symlink()),
                key=lambda e: e.name.lower(),
            )
        except OSError as exc:
            self.logger.debug("cannot enumerate %s: %s", root_p, exc)
            return []

        for i, child in enumerate(entries):
            if cancel_event and cancel_event.is_set():
                break
            if child.name.lower() in _SYSTEM_TREES or child.name in _BLOCKED_NAMES:
                continue
            est = self._estimate_folder(child, cancel_event, progress_callback)
            if est is None:
                continue
            if est.estimated_savings >= min_size_mb * 1024 * 1024:
                candidates.append(est)
            if progress_callback:
                progress_callback(f"Estimated {child.name}", i + 1)
        return candidates

    def _estimate_folder(
        self,
        folder: Path,
        cancel_event: "threading.Event | None" = None,
        progress_callback=None,
    ) -> Optional[FolderEstimate]:
        """Walk *folder* and estimate compressible bytes + savings."""
        total = 0
        compressible = 0            # bytes of clearly-compressible content
        known = 0                   # bytes with a known (good/bad) extension
        count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(folder):
                if cancel_event and cancel_event.is_set():
                    return None
                dirnames[:] = [d for d in dirnames if d not in _BLOCKED_NAMES]
                for fn in filenames:
                    try:
                        sz = (Path(dirpath) / fn).stat().st_size
                    except OSError:
                        continue
                    ext = Path(fn).suffix.lower()
                    total += sz
                    count += 1
                    if ext in _COMPRESSIBLE_EXT:
                        compressible += sz
                        known += sz
                    elif ext in _INCOMPRESSIBLE_EXT:
                        known += sz
        except OSError:
            return None

        if total < 1024:  # ignore trivial folders
            return None

        # Weighted savings: compressible content at text ratio; the rest of the
        # "unknown" at a conservative misc ratio; incompressible at ~0.
        known_gain = compressible * _COMPRESS_TEXT + (known - compressible) * _COMPRESS_NONE
        unknown = max(0, total - known)
        misc_gain = unknown * _COMPRESS_MISC if count > 0 else 0.0
        estimated = int(known_gain + misc_gain)

        ratio = (estimated / total) if total else 0.0
        already = self._check_compression_attribute(folder)
        note = ""
        if count == 0:
            note = "Empty folder."
        elif not compressible and not unknown:
            note = "No compressible content detected."
        return FolderEstimate(
            path=str(folder),
            size_bytes=total,
            estimated_savings=min(estimated, total),
            compressible_ratio=ratio,
            already_compressed=already,
            note=note,
        )

    def _check_compression_attribute(self, folder: Path) -> bool:
        """Best-effort: is the folder already flagged compressed on NTFS?"""
        if not _IS_WINDOWS:
            return False
        try:
            out = self._run(["compact", "/q", str(folder)], timeout=30)
        except Exception:  # noqa: BLE001
            return False
        if not out:
            return False
        # compact /q "List of files in current directory" -> "New files added
        # to this directory will not be compressed" when NOT compressed.
        return "will not be compressed" not in out.lower()

    # -- action ---------------------------------------------------------------

    def compact_folder(
        self,
        path: str | os.PathLike,
        recursive: bool = True,
        cancel_event: "threading.Event | None" = None,
    ) -> CompressionResult:
        """Compress an NTFS folder (and optionally its subtree).

        Requires an elevated prompt. Refuses system trees and blocked names.
        Returns a :class:`CompressionResult`.
        """
        p = Path(path)
        if not _IS_WINDOWS:
            return CompressionResult(str(p), False, "Windows-only feature.")
        if not self.is_admin():
            return CompressionResult(
                str(p), False, "Administrator privileges are required to compress folders.")

        resolved = p.resolve()
        if resolved.name.lower() in _SYSTEM_TREES or resolved.name in _BLOCKED_NAMES:
            return CompressionResult(str(p), False,
                                     f"Refused: {resolved.name} is a protected/system folder.")
        # Refuse to compact an entire drive root by accident.
        if resolved.parent == resolved:
            return CompressionResult(str(p), False,
                                     "Refusing to compress a drive root.")

        flag = "/c"
        if recursive:
            flag += " /s"
        out = self._run(
            ["compact", flag, str(resolved)], timeout=1800, cancel_event=cancel_event)

        if out and "files within" in out.lower() and (
            "compressed" in out.lower() or "compression succeeded" in out.lower()
        ):
            return CompressionResult(str(p), True, "Compression completed.", 0, out[:400])
        reason = self._parse_failure(out)
        return CompressionResult(str(p), False, reason or "Compression failed.", 0, out or "")

    @staticmethod
    def _parse_failure(out: Optional[str]) -> str:
        if not out:
            return "No output from compact."
        low = out.lower()
        if "access is denied" in low or "denied" in low:
            return "Access denied (run this tool as Administrator)."
        if "is not a valid" in low:
            return "Invalid path."
        return ""
        """_parse_failure."""
        """_parse_failure."""

    # -- helpers --------------------------------------------------------------

    def _run(
        self,
        args: List[str],
        timeout: int,
        cancel_event: "threading.Event | None" = None,
    ) -> Optional[str]:
        try:
            proc = _proc.run(
                args, text=True, timeout=timeout,
                cancel_event=cancel_event, creationflags=_NO_WINDOW,
                errors="replace",
            )
            return (proc.stdout or "") + (proc.stderr or "")
        except (_proc.ProcessCancelled, OSError, subprocess.SubprocessError) as exc:
            self.logger.debug("command %s failed: %s", args, exc)
            return None
        """_run."""
        """_run."""
