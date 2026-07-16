"""Tests for the batched recycle path (production performance + correctness).

The batch path recycles many files in one shell operation instead of one call
per file - critical for clearing tens of thousands of cache files quickly.
"""

from __future__ import annotations

import threading

import pytest

from cortex_unified.engine.models import DeletionMethod, DeletionOutcome
from cortex_unified.engine.secure_delete import SecureDeleter, _HAS_TRASH


def _make_files(base, n):
    files = []
    for i in range(n):
        f = base / f"junk_{i}.tmp"
        f.write_bytes(b"x" * 128)
        files.append(f)
    return files


@pytest.mark.skipif(not _HAS_TRASH, reason="send2trash not installed")
def test_batch_recycle_removes_all_and_reports_progress(tmp_path):
    files = _make_files(tmp_path, 12)
    progress = []
    results = SecureDeleter().delete_many(
        [str(f) for f in files], DeletionMethod.RECYCLE,
        progress=lambda done, total: progress.append((done, total)),
    )
    assert len(results) == 12
    assert all(r.outcome is DeletionOutcome.RECYCLED for r in results)
    assert all(not f.exists() for f in files)          # actually removed
    assert progress and progress[-1][0] == progress[-1][1] == 12   # reached total


@pytest.mark.skipif(not _HAS_TRASH, reason="send2trash not installed")
def test_batch_recycle_cancel_stops_early(tmp_path):
    files = _make_files(tmp_path, 20)
    cancel = threading.Event()
    cancel.set()   # cancelled before it starts
    results = SecureDeleter().delete_many(
        [str(f) for f in files], DeletionMethod.RECYCLE, cancel_event=cancel)
    # Nothing processed; all files remain.
    assert results == []
    assert all(f.exists() for f in files)


@pytest.mark.skipif(not _HAS_TRASH, reason="send2trash not installed")
def test_batch_recycle_reports_freed_bytes(tmp_path):
    files = _make_files(tmp_path, 5)
    results = SecureDeleter().delete_many([str(f) for f in files], DeletionMethod.RECYCLE)
    freed = sum(r.size for r in results if r.succeeded)
    assert freed == 5 * 128


def test_fast_delete_batch_uses_known_sizes_and_removes_files(tmp_path):
    """The optimized DELETE path deletes files, reports freed bytes from the
    supplied ``sizes`` map (no re-stat), and reaches 100% progress."""
    files = _make_files(tmp_path, 15)
    sizes = {str(f): 999 for f in files}   # deliberately != real size (128)
    progress = []
    results = SecureDeleter().delete_many(
        [str(f) for f in files], DeletionMethod.DELETE, sizes=sizes,
        progress=lambda done, total: progress.append((done, total)),
    )
    assert len(results) == 15
    assert all(r.outcome is DeletionOutcome.DELETED for r in results)
    assert all(not f.exists() for f in files)
    # Freed bytes came from the sizes map, not a fresh stat.
    assert sum(r.size for r in results if r.succeeded) == 15 * 999
    assert progress and progress[-1][0] == progress[-1][1] == 15


def test_fast_delete_batch_cancel_stops_early(tmp_path):
    files = _make_files(tmp_path, 30)
    cancel = threading.Event()
    cancel.set()
    results = SecureDeleter().delete_many(
        [str(f) for f in files], DeletionMethod.DELETE, cancel_event=cancel)
    assert results == []
    assert all(f.exists() for f in files)


def test_fast_delete_batch_dry_run_deletes_nothing(tmp_path):
    files = _make_files(tmp_path, 8)
    results = SecureDeleter().delete_many(
        [str(f) for f in files], DeletionMethod.DRY_RUN)
    assert all(r.outcome is DeletionOutcome.WOULD_DELETE for r in results)
    assert all(f.exists() for f in files)   # dry run touches nothing
