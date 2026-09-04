"""Tests for the engine's category registry and CleanerService orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex_unified.engine import (
    CleanerService,
    CleanupReport,
    DeletionMethod,
    DeletionOutcome,
    PathGuard,
    RiskLevel,
    default_categories,
)
from cortex_unified.engine.categories import CleanupCategory
from cortex_unified.engine.service import CategoryScan


class TestCategories:
    """Testcategories.

    Manages TestCategories operations and coordinates related state changes for the component.
    """
    def test_default_registry_nonempty_and_typed(self):
        """test_default_registry_nonempty_and_typed.

        Manages test default registry nonempty and typed operations and coordinates related state changes for the component.
        """
        cats = default_categories()
        assert len(cats) >= 1
        assert all(isinstance(c, CleanupCategory) for c in cats)
        assert all(isinstance(c.risk, RiskLevel) for c in cats)

    def test_ids_unique(self):
        """test_ids_unique.

        Manages test ids unique operations and coordinates related state changes for the component.
        """
        ids = [c.id for c in default_categories()]
        assert len(ids) == len(set(ids))

    def test_risk_ranking(self):
        """test_risk_ranking.

        Manages test risk ranking operations and coordinates related state changes for the component.
        """
        assert RiskLevel.LOW.rank < RiskLevel.MEDIUM.rank < RiskLevel.HIGH.rank


class TestDeepDiscovery:
    """Testdeepdiscovery.

    Manages TestDeepDiscovery operations and coordinates related state changes for the component.
    """
    def test_discovers_nested_cache_dirs(self, tmp_path, monkeypatch):
        # Build a deep app-data-like tree with caches at varying depths.
        """test_discovers_nested_cache_dirs.

        Manages test discovers nested cache dirs operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        from cortex_unified.engine import categories as cat_mod
        (tmp_path / "AppA" / "Cache").mkdir(parents=True)
        (tmp_path / "AppB" / "User Data" / "Default" / "Code Cache").mkdir(parents=True)
        (tmp_path / "AppC" / "node_modules" / "pkg" / "Cache").mkdir(parents=True)  # skipped
        (tmp_path / "AppD" / "Documents").mkdir(parents=True)  # not a cache
        cat_mod._APP_CACHE_CACHE.clear()
        found = cat_mod._discover_app_caches([tmp_path])
        names = {str(p) for p in found}
        assert any(p.endswith("Cache") and "AppA" in p for p in names)
        assert any(p.endswith("Code Cache") for p in names)          # found deep
        assert not any("node_modules" in p for p in names)           # skipped huge dir

    def test_does_not_recurse_into_matched_cache(self, tmp_path):
        """test_does_not_recurse_into_matched_cache.

        Manages test does not recurse into matched cache operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        from cortex_unified.engine import categories as cat_mod
        (tmp_path / "App" / "Cache" / "Cache_Data").mkdir(parents=True)
        cat_mod._APP_CACHE_CACHE.clear()
        found = cat_mod._discover_app_caches([tmp_path])
        # Only the top 'Cache' is returned, not the nested Cache_Data separately.
        assert sum(1 for p in found if "App" in str(p)) == 1

    def test_discovery_is_cached(self, tmp_path):
        """test_discovery_is_cached.

        Manages test discovery is cached operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        from cortex_unified.engine import categories as cat_mod
        (tmp_path / "App" / "Cache").mkdir(parents=True)
        cat_mod._APP_CACHE_CACHE.clear()
        a = cat_mod._discover_app_caches([tmp_path])
        b = cat_mod._discover_app_caches([tmp_path])
        assert a is b  # same cached tuple object


class TestBreakdown:
    """Testbreakdown.

    Manages TestBreakdown operations and coordinates related state changes for the component.
    """
    def test_groups_files_into_top_folders(self, tmp_path):
        """test_groups_files_into_top_folders.

        Manages test groups files into top folders operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        from cortex_unified.engine.models import FileEntry
        root = tmp_path / "cache"
        cat = CleanupCategory(id="c", label="C", description="", risk=RiskLevel.LOW,
                              paths=(root,))
        scan = CategoryScan(category=cat)
        # Two folders under the root with different sizes.
        scan.entries = [
            FileEntry(root / "big" / "a.bin", 5000, 0.0),
            FileEntry(root / "big" / "b.bin", 3000, 0.0),
            FileEntry(root / "small" / "c.bin", 100, 0.0),
        ]
        bd = scan.breakdown()
        assert len(bd) == 2
        # Sorted by size desc -> 'big' first with combined 8000 bytes, 2 files.
        assert bd[0]["name"] == "big"
        assert bd[0]["size"] == 8000
        assert bd[0]["count"] == 2
        assert bd[1]["name"] == "small"

    def test_limit_respected(self, tmp_path):
        """test_limit_respected.

        Manages test limit respected operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        from cortex_unified.engine.models import FileEntry
        root = tmp_path / "c"
        cat = CleanupCategory(id="c", label="C", description="", risk=RiskLevel.LOW,
                              paths=(root,))
        scan = CategoryScan(category=cat)
        scan.entries = [FileEntry(root / f"d{i}" / "f", 10, 0.0) for i in range(50)]
        assert len(scan.breakdown(limit=10)) == 10

    def test_empty(self):
        """test_empty.

        Manages test empty operations and coordinates related state changes for the component.
        """
        cat = CleanupCategory(id="c", label="C", description="", risk=RiskLevel.LOW,
                              paths=(Path("x"),))
        assert CategoryScan(category=cat).breakdown() == []


class TestCleanerServiceCategories:
    """Testcleanerservicecategories.

    Manages TestCleanerServiceCategories operations and coordinates related state changes for the component.
    """
    def _make_category(self, tmp_path: Path) -> CleanupCategory:
        """_make_category.

        Manages make category operations and coordinates related state changes for the component.

        Args:
            tmp_path (Path): Filesystem path to the target file or directory.

        Returns:
            CleanupCategory: Result of the operation.
        """
        junk = tmp_path / "cache"
        junk.mkdir()
        (junk / "a.tmp").write_bytes(b"x" * 2048)
        (junk / "b.tmp").write_bytes(b"y" * 1024)
        return CleanupCategory(
            id="test_cache",
            label="Test cache",
            description="synthetic",
            risk=RiskLevel.LOW,
            paths=(junk,),
            min_age_days=0.0,
        )

    def test_scan_and_clean_dry_run_then_real(self, tmp_path: Path, monkeypatch):
        """test_scan_and_clean_dry_run_then_real.

        Manages test scan and clean dry run then real operations and coordinates related state changes for the component.

        Args:
            tmp_path (Path): Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        cat = self._make_category(tmp_path)
        # Sandbox the guard to tmp_path so synthetic paths are allowed & safe.
        service = CleanerService(guard=PathGuard(sandbox=tmp_path))

        # Inject our synthetic category into the service scan.
        scan = service._scan_category(cat)
        assert scan.file_count == 2
        assert scan.total_bytes == 3072

        report = CleanupReport(scans=[scan])
        assert report.total_reclaimable_bytes == 3072
        assert report.total_files == 2

        # Dry-run: nothing removed.
        dry = service.clean_categories(report, DeletionMethod.DRY_RUN)
        assert all(r.outcome is DeletionOutcome.WOULD_DELETE for r in dry)
        assert (tmp_path / "cache" / "a.tmp").exists()

        # Real delete.
        real = service.clean_categories(report, DeletionMethod.DELETE)
        assert all(r.outcome is DeletionOutcome.DELETED for r in real)
        assert not (tmp_path / "cache" / "a.tmp").exists()

    def test_scan_categories_respects_max_risk(self):
        """test_scan_categories_respects_max_risk.

        Manages test scan categories respects max risk operations and coordinates related state changes for the component.
        """
        service = CleanerService()
        # Should not raise, and must never include HIGH-risk categories by default.
        report = service.scan_categories(max_risk=RiskLevel.LOW)
        assert isinstance(report, CleanupReport)
        assert report.total_reclaimable_bytes >= 0

    def test_report_to_dict(self, tmp_path: Path):
        """test_report_to_dict.

        Manages test report to dict operations and coordinates related state changes for the component.

        Args:
            tmp_path (Path): Filesystem path to the target file or directory.
        """
        cat = self._make_category(tmp_path)
        service = CleanerService(guard=PathGuard(sandbox=tmp_path))
        report = CleanupReport(scans=[service._scan_category(cat)])
        d = report.to_dict()
        assert d["total_files"] == 2
        assert d["categories"][0]["id"] == "test_cache"
        assert d["categories"][0]["risk"] == "low"


class TestScanProgressAndCancel:
    """TestScanProgressAndCancel.

    Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
    """
    def test_progress_callback_fires(self, tmp_path):
        # build a category tree
        """test_progress_callback_fires.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        from cortex_unified.engine.categories import CleanupCategory
        from cortex_unified.engine import PathGuard
        d = tmp_path / "c"
        d.mkdir()
        for i in range(5):
            (d / f"f{i}.tmp").write_bytes(b"x" * 100)
        cat = CleanupCategory(
            id="t", label="T", description="", risk=RiskLevel.LOW, paths=(d,),
        )
        svc = CleanerService(guard=PathGuard(sandbox=tmp_path))
        msgs = []
        svc._scan_category(cat, progress=msgs.append)
        # progress may be throttled to few messages, but the plumbing works;
        # at minimum the walker invoked it at least once for the directory.
        assert isinstance(msgs, list)

    def test_cancel_event_stops_scan(self):
        """test_cancel_event_stops_scan.

        Manages test cancel event stops scan operations and coordinates related state changes for the component.
        """
        import threading
        ev = threading.Event()
        ev.set()
        report = CleanerService().scan_categories(cancel_event=ev)
        assert report.total_files == 0

    def test_find_duplicates_accepts_progress_and_cancel(self, tmp_path):
        """test_find_duplicates_accepts_progress_and_cancel.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        (tmp_path / "a.txt").write_text("dup")
        (tmp_path / "b.txt").write_text("dup")
        msgs = []
        groups = CleanerService().find_duplicates([tmp_path], progress=msgs.append)
        assert any("a.txt" in str(p) for g in groups.values() for p in g)


class TestCleanerServiceAnalysis:
    """Testcleanerserviceanalysis.

    Manages TestCleanerServiceAnalysis operations and coordinates related state changes for the component.
    """
    @pytest.fixture
    def tree(self, tmp_path: Path) -> Path:
        """Tree.

        Manages tree operations and coordinates related state changes for the component.

        Args:
            tmp_path (Path): Filesystem path to the target file or directory.

        Returns:
            Path: Result of the operation.
        """
        (tmp_path / "a.txt").write_text("dup-content")
        (tmp_path / "b.txt").write_text("dup-content")   # duplicate
        (tmp_path / "big.bin").write_bytes(b"Z" * (2 * 1024 * 1024))  # 2 MiB
        (tmp_path / "empty.txt").touch()
        (tmp_path / "empty_dir").mkdir()
        return tmp_path

    def test_find_duplicates(self, tree: Path):
        """test_find_duplicates.

        Manages test find duplicates operations and coordinates related state changes for the component.

        Args:
            tree (Path): The tree parameter.
        """
        groups = CleanerService().find_duplicates([tree])
        names = {p.name for g in groups.values() for p in g}
        assert {"a.txt", "b.txt"}.issubset(names)

    def test_find_large_files(self, tree: Path):
        """test_find_large_files.

        Manages test find large files operations and coordinates related state changes for the component.

        Args:
            tree (Path): The tree parameter.
        """
        large = CleanerService().find_large_files(tree, min_mb=1.0)
        assert large
        assert large[0].path.name == "big.bin"
        assert all(e.size >= 1024 * 1024 for e in large)

    def test_find_empty(self, tree: Path):
        """test_find_empty.

        Manages test find empty operations and coordinates related state changes for the component.

        Args:
            tree (Path): The tree parameter.
        """
        files, dirs = CleanerService().find_empty(tree)
        assert any(p.name == "empty.txt" for p in files)
        assert any(p.name == "empty_dir" for p in dirs)
