"""Cloud-placeholder and reparse-point safety in the scan engine.

A cloud file (OneDrive "Files On-Demand" and friends) is a reparse point, not a
symlink, so ``is_symlink()`` misses it. Its ``st_size`` is the full logical size
even though the bytes live in the cloud, and *opening* it forces a download. The
engine must therefore:

* leave dehydrated files out of scan results, but report the omission;
* never descend a junction (it would double-count the target's bytes);
* refuse to "shred" a placeholder instead of hydrating gigabytes to overwrite
  data that was never on this disk.

The placeholder is simulated with ``FILE_ATTRIBUTE_OFFLINE``, which is one of
the recall bits the engine treats as "content may be remote" - real cloud
providers set ``RECALL_ON_DATA_ACCESS``, which flows through the same code path.
"""

from __future__ import annotations

import platform
import subprocess

import pytest

from cortex_unified.engine import winattrs as wa
from cortex_unified.engine.fastwalk import FastWalker, WalkOptions

IS_WINDOWS = platform.system() == "Windows"


# ---------------------------------------------------------------------------
# Pure classification (runs on every platform)
# ---------------------------------------------------------------------------

def test_recall_attributes_mean_dehydrated():
    assert wa.is_dehydrated(wa.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS)
    assert wa.is_dehydrated(wa.FILE_ATTRIBUTE_RECALL_ON_OPEN)
    assert wa.is_dehydrated(wa.FILE_ATTRIBUTE_OFFLINE)
    assert not wa.is_dehydrated(0)
    # A plain reparse point (junction) is not a dehydrated file.
    assert not wa.is_dehydrated(wa.FILE_ATTRIBUTE_REPARSE_POINT)


def test_cloud_tag_family_is_matched():
    # The cloud filter reserves 0x9000?01A for CLOUD and CLOUD_1..CLOUD_F.
    assert wa.is_cloud_tag(wa.IO_REPARSE_TAG_CLOUD)
    assert wa.is_cloud_tag(0x9000701A)
    assert wa.is_cloud_tag(0x9000F01A)
    assert not wa.is_cloud_tag(wa.IO_REPARSE_TAG_MOUNT_POINT)
    assert not wa.is_cloud_tag(0)


def test_junction_detected_by_tag_only():
    assert wa.is_junction(wa.IO_REPARSE_TAG_MOUNT_POINT)
    assert not wa.is_junction(wa.IO_REPARSE_TAG_SYMLINK)
    assert not wa.is_junction(0)


def test_describe_explains_each_special_case():
    assert "not stored on this disk" in wa.describe(wa.FILE_ATTRIBUTE_OFFLINE)
    assert "junction" in wa.describe(
        wa.FILE_ATTRIBUTE_REPARSE_POINT, wa.IO_REPARSE_TAG_MOUNT_POINT)
    assert "sparse" in wa.describe(wa.FILE_ATTRIBUTE_SPARSE_FILE)
    # Nothing special -> no note, so the UI stays quiet for ordinary files.
    assert wa.describe(0, 0) == ""


def test_pure_helpers_never_raise_on_missing_attributes():
    """Non-Windows stat results have no attribute fields; that must be fine."""
    class Bare:
        pass

    assert wa.attrs_of(Bare()) == 0
    assert wa.reparse_tag_of(Bare()) == 0


# ---------------------------------------------------------------------------
# Walker behaviour (Windows reparse points)
# ---------------------------------------------------------------------------

def _mark_offline(path) -> bool:
    """Flag *path* with FILE_ATTRIBUTE_OFFLINE; False if the OS refused."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.SetFileAttributesW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
    return bool(k32.SetFileAttributesW(str(path), wa.FILE_ATTRIBUTE_OFFLINE))


@pytest.fixture
def cloud_tree(tmp_path):
    """A folder with one local file, one simulated placeholder, one junction."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "local.bin").write_bytes(b"a" * 4096)
    stub = real / "cloud_only.bin"
    stub.write_bytes(b"b" * 100_000)
    if not _mark_offline(stub):
        pytest.skip("could not set FILE_ATTRIBUTE_OFFLINE on this filesystem")

    link = tmp_path / "link"
    proc = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(real)],
                          capture_output=True)
    if proc.returncode != 0 or not link.exists():
        pytest.skip("could not create a junction on this filesystem")
    return tmp_path, stub


@pytest.mark.skipif(not IS_WINDOWS, reason="reparse points are a Windows concept")
def test_placeholder_excluded_and_reported(cloud_tree):
    root, stub = cloud_tree
    result = FastWalker(WalkOptions()).scan(root)

    names = [f.path.name for f in result.files]
    assert names == ["local.bin"], "the cloud placeholder must not be scanned"
    # Its logical size must not inflate the reclaimable total.
    assert result.total_bytes == 4096
    # ...but the omission is reported, never silent.
    assert result.cloud_skipped == 1
    assert result.cloud_skipped_bytes == 100_000


@pytest.mark.skipif(not IS_WINDOWS, reason="reparse points are a Windows concept")
def test_junction_not_descended(cloud_tree):
    root, _ = cloud_tree
    result = FastWalker(WalkOptions()).scan(root)
    # Without junction handling the target's file would be counted twice.
    assert result.junctions_skipped == 1
    assert result.files_scanned == 1


@pytest.mark.skipif(not IS_WINDOWS, reason="reparse points are a Windows concept")
def test_placeholder_skip_is_opt_out(cloud_tree):
    """Read-only inventory callers can still see placeholders."""
    root, _ = cloud_tree
    result = FastWalker(WalkOptions(skip_cloud_placeholders=False)).scan(root)
    assert result.files_scanned == 2
    assert result.cloud_skipped == 0
    stub_entry = next(f for f in result.files if f.path.name == "cloud_only.bin")
    assert stub_entry.is_cloud_placeholder
    # Reclaimable space is zero: deleting it frees nothing locally.
    assert stub_entry.reclaimable_size == 0
    assert "not stored on this disk" in stub_entry.special_note


@pytest.mark.skipif(not IS_WINDOWS, reason="reparse points are a Windows concept")
def test_placeholder_is_not_reported_as_empty(cloud_tree):
    """find_empty must not offer a placeholder as a deletable empty file."""
    root, _ = cloud_tree
    empty_files, _ = FastWalker(WalkOptions()).find_empty(root)
    assert all(p.name != "cloud_only.bin" for p in empty_files)


@pytest.mark.skipif(not IS_WINDOWS, reason="reparse points are a Windows concept")
def test_shredder_refuses_cloud_placeholder(cloud_tree):
    """Overwriting a placeholder would download it first - refuse instead."""
    from cortex_unified.engine.models import DeletionMethod, DeletionOutcome
    from cortex_unified.engine.secure_delete import SecureDeleter

    _, stub = cloud_tree
    # force_overwrite_on_flash=True proves the refusal is about the placeholder,
    # not about the storage medium being unsuitable for overwriting.
    result = SecureDeleter().delete(
        stub, method=DeletionMethod.OVERWRITE, force_overwrite_on_flash=True)

    assert result.outcome == DeletionOutcome.SKIPPED_UNSAFE
    assert "cloud" in result.reason.lower()
    assert stub.exists(), "the file must be left untouched"


# ---------------------------------------------------------------------------
# Allocated size
# ---------------------------------------------------------------------------

def test_on_disk_size_matches_a_plain_file(tmp_path):
    f = tmp_path / "plain.bin"
    f.write_bytes(b"x" * 5000)
    measured = wa.on_disk_size(f, 5000)
    # Either a real measurement (cluster-rounded, so >= the logical size on
    # Windows) or None when the platform cannot report it - never a bogus 0.
    assert measured is None or measured >= 5000


def test_on_disk_size_returns_none_for_missing_path(tmp_path):
    assert wa.on_disk_size(tmp_path / "nope.bin", 0) in (None, 0)


def test_entry_falls_back_to_logical_size_when_unmeasured(tmp_path):
    """reclaimable_size must never under-report an ordinary file."""
    f = tmp_path / "plain.bin"
    f.write_bytes(b"x" * 2048)
    result = FastWalker(WalkOptions(measure_on_disk=False)).scan(tmp_path)
    entry = result.files[0]
    assert entry.on_disk is None
    assert entry.reclaimable_size == 2048
