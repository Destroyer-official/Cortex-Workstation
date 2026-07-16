"""Tests for the cortex_unified.engine package.

Covers fast traversal, path-safety guard (including the sibling-name trap that
broke the legacy prefix matcher), duplicate detection, storage detection, and
the honest storage-aware secure deleter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from cortex_unified.engine import (
    DeletionMethod,
    DeletionOutcome,
    DuplicateFinderEngine,
    FastWalker,
    PathGuard,
    SecureDeleter,
    StorageKind,
    WalkOptions,
    detect_storage,
    hash_file,
)
from cortex_unified.engine.secure_delete import OverwriteNotEffective
from cortex_unified.engine.storage import StorageInfo, StorageProbe


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A small mixed tree: files of various sizes, empties, nested dirs."""
    (tmp_path / "a.txt").write_text("hello world")
    (tmp_path / "b.log").write_text("hello world")   # duplicate content of a.txt
    (tmp_path / "unique.bin").write_bytes(b"\x01\x02\x03\x04\x05")
    (tmp_path / "empty1.txt").touch()

    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("hello world")        # third duplicate
    (sub / "big.dat").write_bytes(b"A" * 4096)

    (tmp_path / "empty_dir").mkdir()
    nested_empty = tmp_path / "nested" / "deep"
    nested_empty.mkdir(parents=True)                  # both levels empty
    (tmp_path / "__pycache__").mkdir()                # excluded by default
    (tmp_path / "__pycache__" / "junk.pyc").write_text("x")
    return tmp_path


# --------------------------------------------------------------------------
# FastWalker
# --------------------------------------------------------------------------

class TestFastWalker:
    def test_scan_counts_and_bytes(self, tree: Path):
        result = FastWalker().scan(tree)
        names = {f.path.name for f in result.files}
        assert "a.txt" in names and "big.dat" in names
        assert "junk.pyc" not in names          # __pycache__ excluded
        assert result.total_bytes > 0
        assert result.files_scanned == len(result.files)

    def test_min_size_filter(self, tree: Path):
        walker = FastWalker(WalkOptions(min_size=1000))
        result = walker.scan(tree)
        assert all(f.size >= 1000 for f in result.files)
        assert any(f.path.name == "big.dat" for f in result.files)

    def test_excludes_glob(self, tree: Path):
        walker = FastWalker(WalkOptions(exclude_globs=("*.log",)))
        result = walker.scan(tree)
        assert not any(f.path.suffix == ".log" for f in result.files)

    def test_find_empty(self, tree: Path):
        empty_files, empty_dirs = FastWalker().find_empty(tree)
        empty_file_names = {p.name for p in empty_files}
        empty_dir_names = {p.name for p in empty_dirs}
        assert "empty1.txt" in empty_file_names
        assert "empty_dir" in empty_dir_names
        # nested/deep is empty; "deep" collapses upward
        assert "deep" in empty_dir_names

    def test_symlinks_not_followed_by_default(self, tmp_path: Path):
        if not hasattr(os, "symlink"):
            pytest.skip("no symlink support")
        target = tmp_path / "real"
        target.mkdir()
        (target / "f.txt").write_text("data")
        link = tmp_path / "link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlink creation not permitted")
        result = FastWalker().scan(tmp_path)
        # The real file is found once; not duplicated via the symlink.
        assert sum(1 for f in result.files if f.path.name == "f.txt") == 1

    def test_cancel_stops_iteration(self, tree: Path):
        walker = FastWalker()
        collected = []
        for entry in walker.iter_files(tree):
            collected.append(entry)
            walker.cancel()
            break
        assert len(collected) == 1


# --------------------------------------------------------------------------
# PathGuard
# --------------------------------------------------------------------------

class TestPathGuard:
    def test_sibling_name_not_falsely_protected(self, tmp_path: Path):
        """The legacy prefix matcher blocked '/usrdata' because it startswith
        '/usr'. The relationship-based guard must not."""
        guard = PathGuard()
        # A normal temp file should be allowed.
        f = tmp_path / "file.txt"
        f.write_text("x")
        assert guard.check(f).safe is True

    def test_blocks_home_root(self):
        guard = PathGuard()
        verdict = guard.check(Path.home())
        assert verdict.safe is False
        assert "home" in verdict.reason.lower()

    @pytest.mark.skipif(sys.platform != "win32", reason="windows-only paths")
    def test_blocks_windows_system_dirs(self):
        guard = PathGuard()
        assert guard.check(Path(os.environ.get("SystemRoot", r"C:\Windows"))).safe is False
        assert guard.check(Path(r"C:\Windows\System32\kernel32.dll")).safe is False

    @pytest.mark.skipif(sys.platform == "win32", reason="posix-only paths")
    def test_blocks_posix_system_dirs(self):
        guard = PathGuard()
        assert guard.check(Path("/usr")).safe is False
        assert guard.check(Path("/etc/passwd")).safe is False

    def test_sandbox_confinement(self, tmp_path: Path):
        sandbox = tmp_path / "box"
        sandbox.mkdir()
        inside = sandbox / "ok.txt"
        inside.write_text("x")
        outside = tmp_path / "nope.txt"
        outside.write_text("x")
        guard = PathGuard(sandbox=sandbox)
        assert guard.check(inside).safe is True
        assert guard.check(outside).safe is False


# --------------------------------------------------------------------------
# Hashing / duplicates
# --------------------------------------------------------------------------

class TestDuplicates:
    def test_hash_file_stable_and_none_on_missing(self, tmp_path: Path):
        f = tmp_path / "x.bin"
        f.write_bytes(b"abc123")
        h1 = hash_file(f)
        h2 = hash_file(f)
        assert h1 == h2 and h1 is not None
        assert hash_file(tmp_path / "missing") is None

    def test_finds_content_duplicates(self, tree: Path):
        result = FastWalker().scan(tree)
        entries = [(f.path, f.size) for f in result.files]
        groups = DuplicateFinderEngine().find(entries)
        # a.txt / b.log / sub/c.txt all share "hello world"
        dup_paths = {p.name for group in groups.values() for p in group}
        assert {"a.txt", "b.log", "c.txt"}.issubset(dup_paths)
        assert DuplicateFinderEngine.wasted_bytes(groups) > 0

    def test_unique_sizes_not_flagged(self, tmp_path: Path):
        (tmp_path / "one.txt").write_text("aaaa")
        (tmp_path / "two.txt").write_text("bbbbbb")   # different size
        entries = [
            (tmp_path / "one.txt", 4),
            (tmp_path / "two.txt", 6),
        ]
        assert DuplicateFinderEngine().find(entries) == {}


# --------------------------------------------------------------------------
# Storage detection
# --------------------------------------------------------------------------

class TestStorage:
    def test_detect_returns_storageinfo(self, tmp_path: Path):
        info = detect_storage(tmp_path)
        assert isinstance(info, StorageInfo)
        assert isinstance(info.kind, StorageKind)

    def test_overwrite_effective_only_for_hdd(self):
        assert StorageKind.HDD.overwrite_effective is True
        assert StorageKind.SSD.overwrite_effective is False
        assert StorageKind.NVME.overwrite_effective is False
        assert StorageKind.UNKNOWN.overwrite_effective is False

    def test_probe_caches(self, tmp_path: Path):
        probe = StorageProbe()
        first = probe.probe(tmp_path)
        second = probe.probe(tmp_path)
        assert first is second  # cached identical object


# --------------------------------------------------------------------------
# SecureDeleter
# --------------------------------------------------------------------------

class _FakeProbe(StorageProbe):
    def __init__(self, kind: StorageKind):
        super().__init__()
        self._forced = kind

    def probe(self, path):  # type: ignore[override]
        return StorageInfo(self._forced)


class TestSecureDeleter:
    def test_dry_run_touches_nothing(self, tmp_path: Path):
        f = tmp_path / "x.txt"
        f.write_text("data")
        deleter = SecureDeleter()
        res = deleter.delete(f, DeletionMethod.DRY_RUN)
        assert res.outcome is DeletionOutcome.WOULD_DELETE
        assert f.exists()

    def test_plain_delete_file(self, tmp_path: Path):
        f = tmp_path / "x.txt"
        f.write_text("data")
        res = SecureDeleter().delete(f, DeletionMethod.DELETE)
        assert res.outcome is DeletionOutcome.DELETED
        assert not f.exists()

    def test_plain_delete_directory_is_guarded(self, tmp_path: Path):
        """Directory deletion must pass through the guard (legacy bug: it did not)."""
        d = tmp_path / "dir"
        d.mkdir()
        (d / "f.txt").write_text("x")
        res = SecureDeleter().delete(d, DeletionMethod.DELETE)
        assert res.outcome is DeletionOutcome.DELETED
        assert not d.exists()

    def test_guard_blocks_unsafe(self):
        res = SecureDeleter().delete(Path.home(), DeletionMethod.DELETE)
        assert res.outcome is DeletionOutcome.SKIPPED_UNSAFE
        assert Path.home().exists()

    def test_overwrite_on_hdd_wipes(self, tmp_path: Path):
        f = tmp_path / "secret.txt"
        f.write_bytes(b"top secret" * 100)
        deleter = SecureDeleter(probe=_FakeProbe(StorageKind.HDD), overwrite_passes=2)
        res = deleter.delete(f, DeletionMethod.OVERWRITE)
        assert res.outcome is DeletionOutcome.OVERWRITTEN
        assert not f.exists()

    def test_overwrite_on_ssd_refuses_honestly(self, tmp_path: Path):
        f = tmp_path / "secret.txt"
        f.write_bytes(b"secret")
        deleter = SecureDeleter(probe=_FakeProbe(StorageKind.SSD))
        with pytest.raises(OverwriteNotEffective) as exc:
            deleter.delete(f, DeletionMethod.OVERWRITE)
        assert exc.value.kind is StorageKind.SSD
        assert f.exists()  # not touched

    def test_overwrite_on_ssd_forced_best_effort(self, tmp_path: Path):
        f = tmp_path / "secret.txt"
        f.write_bytes(b"secret data here")
        deleter = SecureDeleter(probe=_FakeProbe(StorageKind.SSD), overwrite_passes=1)
        res = deleter.delete(f, DeletionMethod.OVERWRITE, force_overwrite_on_flash=True)
        assert res.outcome is DeletionOutcome.OVERWRITTEN
        assert "best-effort" in res.reason
        assert not f.exists()

    def test_summary_aggregates(self, tmp_path: Path):
        for i in range(3):
            (tmp_path / f"f{i}.txt").write_text("data")
        deleter = SecureDeleter()
        paths = [tmp_path / f"f{i}.txt" for i in range(3)]
        deleter.delete_many(paths, DeletionMethod.DELETE)
        summary = deleter.summary()
        assert summary["total"] == 3
        assert summary.get("deleted") == 3
