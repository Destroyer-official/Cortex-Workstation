"""Cloud-placeholder / reparse-point awareness in the scan engine.

Real OneDrive placeholders and junctions can't be created in a unit test without
a sync provider (or elevation), so the attribute *classification* is tested
against synthetic values and the *walker policy* is tested by patching the
attribute reader the walker uses. That covers the logic that decides what gets
skipped, which is where the risk lives.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cortex_unified.engine import winattrs
from cortex_unified.engine.fastwalk import FastWalker, WalkOptions
from cortex_unified.engine.models import FileEntry

ONLINE = winattrs.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS

# A file is treated as a placeholder when its mtime matches this marker, which
# gives the patched attribute reader a stable way to single out one test file.
_MARK_MTIME = 946_684_800.0  # 2000-01-01T00:00:00Z


def _mark_as_online(path: Path) -> None:
    os.utime(path, (_MARK_MTIME, _MARK_MTIME))


@pytest.fixture
def cloud_attrs(monkeypatch):
    """Make the walker see mtime-marked files as dehydrated placeholders."""
    monkeypatch.setattr(
        "cortex_unified.engine.fastwalk.winattrs.attrs_of",
        lambda st: ONLINE if getattr(st, "st_mtime", 0) == _MARK_MTIME else 0,
    )


# -- classification ---------------------------------------------------------

def test_dehydrated_detects_all_recall_flags():
    for bit in (winattrs.FILE_ATTRIBUTE_OFFLINE,
                winattrs.FILE_ATTRIBUTE_RECALL_ON_OPEN,
                winattrs.FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS):
        assert winattrs.is_dehydrated(bit) is True
    assert winattrs.is_dehydrated(0) is False
    # A plain reparse point on its own is not a placeholder.
    assert winattrs.is_dehydrated(winattrs.FILE_ATTRIBUTE_REPARSE_POINT) is False


def test_cloud_tag_covers_the_provider_range():
    assert winattrs.is_cloud_tag(0x9000001A) is True
    assert winattrs.is_cloud_tag(0x9000101A) is True   # provider variant 1
    assert winattrs.is_cloud_tag(0x9000F01A) is True   # provider variant 15
    assert winattrs.is_cloud_tag(winattrs.IO_REPARSE_TAG_SYMLINK) is False


def test_junction_is_distinct_from_symlink():
    """Python reports junctions as non-symlinks, so they need their own check."""
    assert winattrs.is_junction(winattrs.IO_REPARSE_TAG_MOUNT_POINT) is True
    assert winattrs.is_junction(winattrs.IO_REPARSE_TAG_SYMLINK) is False


def test_attribute_readers_tolerate_a_posix_stat(tmp_path):
    f = tmp_path / "plain.txt"
    f.write_text("x")
    st = f.stat()
    # On Linux/macOS these fields are absent; the readers must not raise.
    assert isinstance(winattrs.attrs_of(st), int)
    assert isinstance(winattrs.reparse_tag_of(st), int)


def test_describe_explains_special_entries():
    assert "cloud" in winattrs.describe(ONLINE, 0)
    assert "junction" in winattrs.describe(0, winattrs.IO_REPARSE_TAG_MOUNT_POINT)
    assert winattrs.describe(0, 0) == ""


# -- FileEntry honesty ------------------------------------------------------

def test_placeholder_entry_reclaims_nothing():
    e = FileEntry(Path("x"), size=5 * 1024 ** 3, mtime=0.0, attrs=ONLINE)
    assert e.is_cloud_placeholder is True
    # A 5 GB online-only file frees zero local bytes.
    assert e.reclaimable_size == 0


def test_measured_on_disk_size_wins_over_logical():
    sparse = FileEntry(Path("x"), size=1_000_000, mtime=0.0,
                       attrs=winattrs.FILE_ATTRIBUTE_SPARSE_FILE, on_disk=4096)
    assert sparse.reclaimable_size == 4096
    plain = FileEntry(Path("y"), size=1000, mtime=0.0)
    assert plain.reclaimable_size == 1000


def test_to_dict_reports_cloud_state():
    d = FileEntry(Path("x"), 10, 0.0, attrs=winattrs.FILE_ATTRIBUTE_OFFLINE).to_dict()
    assert d["cloud_placeholder"] is True
    assert "cloud" in d["note"]


# -- walker policy ----------------------------------------------------------

def test_walker_skips_placeholders_and_reports_the_omission(tmp_path, cloud_attrs):
    (tmp_path / "real.bin").write_bytes(b"a" * 128)
    online = tmp_path / "online.bin"
    online.write_bytes(b"b" * 64)
    _mark_as_online(online)

    result = FastWalker(WalkOptions()).scan(tmp_path)

    names = {f.path.name for f in result.files}
    assert "real.bin" in names
    assert "online.bin" not in names        # never handed to hashing or deletion
    assert result.cloud_skipped == 1
    assert result.cloud_skipped_bytes == 64
    # Totals must not claim bytes that aren't on this disk.
    assert result.total_bytes == 128


def test_placeholders_can_be_included_on_request(tmp_path, cloud_attrs):
    (tmp_path / "real.bin").write_bytes(b"a" * 128)
    online = tmp_path / "online.bin"
    online.write_bytes(b"b" * 64)
    _mark_as_online(online)

    walker = FastWalker(WalkOptions(skip_cloud_placeholders=False,
                                    measure_on_disk=False))
    result = walker.scan(tmp_path)
    assert {f.path.name for f in result.files} == {"real.bin", "online.bin"}
    assert result.cloud_skipped == 0


def test_find_empty_never_offers_a_placeholder_for_deletion(tmp_path, cloud_attrs):
    real_empty = tmp_path / "truly_empty.txt"
    real_empty.touch()
    online_empty = tmp_path / "online.txt"
    online_empty.touch()
    _mark_as_online(online_empty)

    empty_files, _ = FastWalker().find_empty(tmp_path)
    names = {p.name for p in empty_files}
    assert "truly_empty.txt" in names
    # 0 bytes locally, but the content exists in the cloud - not an empty file.
    assert "online.txt" not in names


def test_walker_still_reports_plain_trees_unchanged(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("world")
    result = FastWalker(WalkOptions()).scan(tmp_path)
    assert result.files_scanned == 2
    assert result.cloud_skipped == 0
    assert result.junctions_skipped == 0
    assert result.total_bytes == 10


# -- allocated size ---------------------------------------------------------

@pytest.mark.skipif(os.name != "nt", reason="allocated size query is Windows-specific")
def test_on_disk_size_for_a_plain_file(tmp_path):
    f = tmp_path / "plain.bin"
    f.write_bytes(b"z" * 8192)
    assert winattrs.on_disk_size(f, 8192) >= 8192


def test_on_disk_size_falls_back_when_the_path_is_gone():
    assert winattrs.on_disk_size("Z:/does/not/exist.bin", 777) in (None, 0, 777)


# -- shredder refuses placeholders -----------------------------------------

def test_shredder_refuses_to_overwrite_a_placeholder(tmp_path, monkeypatch):
    from cortex_unified.engine.models import DeletionMethod, DeletionOutcome
    from cortex_unified.engine.secure_delete import SecureDeleter

    target = tmp_path / "doc.docx"
    target.write_bytes(b"x" * 32)
    monkeypatch.setattr(SecureDeleter, "_is_cloud_placeholder",
                        staticmethod(lambda p: True))

    deleter = SecureDeleter()
    res = deleter.delete(target, method=DeletionMethod.OVERWRITE,
                         force_overwrite_on_flash=True)
    assert res.outcome is DeletionOutcome.SKIPPED_UNSAFE
    assert "cloud placeholder" in res.reason
    assert target.exists()  # refused, not silently destroyed
