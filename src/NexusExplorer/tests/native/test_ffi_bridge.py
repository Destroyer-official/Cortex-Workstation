"""Stage-1 tests: ctypes FFI bridge (nexus_ffi.NexusFfi) contract."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "native"))

pytest.importorskip(
    "nexus_ffi", reason="nexus_ffi.py present",
)
nexus_ffi = pytest.importorskip("nexus_ffi")

try:
    _DLL = nexus_ffi.find_dll()
except FileNotFoundError:
    pytest.skip("nexus_engine.dll not built", allow_module_level=True)


@pytest.fixture(scope="module")
def ffi():
    f = nexus_ffi.NexusFfi()
    yield f
    f.close()


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "hello.txt").write_text("abcdef", encoding="utf-8")
    (tmp_path / "emoji_📁.dat").write_bytes(b"x")
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "nested.md").write_text("# t")
    return tmp_path


def test_dll_discovery_paths():
    assert _DLL.is_file()


def test_version_nonempty(ffi):
    v = ffi.version()
    assert isinstance(v, str) and v.strip() != ""


def test_read_dir_sync_rows(tree, ffi):
    rows = {r["name"]: r for r in ffi.read_dir_sync(str(tree))}
    assert "hello.txt" in rows and "subdir" in rows
    assert rows["hello.txt"]["isDir"] is False
    assert rows["hello.txt"]["ext"] == "txt"
    assert rows["hello.txt"]["size"] == 6
    assert rows["subdir"]["isDir"] is True
    assert rows["subdir"]["ext"] == ""
    assert rows["emoji_📁.dat"]["ext"] == "dat"


def test_read_dir_sync_missing_dir_raises(ffi):
    with pytest.raises(OSError):
        ffi.read_dir_sync(r"C:\__nexus_definitely_missing_xyz__")


def test_get_drives(ffi):
    drives = ffi.get_drives()
    assert len(drives) >= 1
    d = drives[0]
    for key in ("path", "driveType", "freeBytes", "totalBytes", "isReady"):
        assert key in d


def test_home_dir(ffi):
    home = ffi.home_dir()
    assert home and os.path.isdir(home)


def test_search_finds_seeded(ffi):
    base = Path(tempfile.mkdtemp(prefix="nexus_search_"))
    try:
        for i in range(5):
            (base / f"decoy_{i}.bin").write_bytes(b"")
        needle = base / "paritoneedel_a.txt"
        needle.write_text("x", encoding="utf-8")
        sid, rows = ffi.search(str(base), "paritoneedel", max_results=100)
        assert isinstance(sid, str)
        names = [r["name"] for r in rows]
        assert "paritoneedel_a.txt" in names
        assert not any(n.startswith("decoy_") for n in names)
    finally:
        import shutil

        shutil.rmtree(base, ignore_errors=True)


def test_cancel_search_after_completion_is_safe(ffi, tmp_path):
    (tmp_path / "z.txt").write_bytes(b"")
    sid, rows = ffi.search(str(tmp_path), "z", max_results=10)
    assert isinstance(ffi.cancel_search(sid), bool)


def test_rename_roundtrip(ffi, tmp_path):
    src = tmp_path / "before.txt"
    src.write_text("", encoding="utf-8")
    assert ffi.rename(str(src), "after.txt") is True
    assert (tmp_path / "after.txt").is_file() and not src.exists()


def test_create_folder(ffi, tmp_path):
    assert ffi.create_folder(str(tmp_path), "made_by_ffi") is True
    assert (tmp_path / "made_by_ffi").is_dir()


def test_read_text_file_content_and_truncation(ffi, tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("0123456789" * 10, encoding="utf-8")
    content, truncated, size = ffi.read_text_file(str(p), 4096)
    assert content == "0123456789" * 10 and truncated is False and size == 100
    content2, truncated2, size2 = ffi.read_text_file(str(p), 7)
    assert truncated2 is True and len(content2) <= 7 < size2


def test_close_idempotent():
    f = nexus_ffi.NexusFfi()
    f.close()
    f.close()  # must not raise
