"""Unit tests for CleanerService.scan_custom_roots, HubScanWorker, and CleanupHubPage targeted scanning."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from cortex_unified.engine.service import CleanerService, CleanupReport, CategoryScan
from cortex_unified.engine.categories import CleanupCategory, RiskLevel
from cortex_unified.engine.models import FileEntry
from cortex_unified.ui.premium.cleanup_hub_page import CleanupHubPage, HubScanWorker

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    """Provide shared QApplication for GUI testing."""
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app):
    """Provide a headless PremiumMainWindow fixture."""
    import gc
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow

    if not getattr(app, "_theme_applied", False):
        apply_theme(app, "dark")
        app._theme_applied = True
    win = PremiumMainWindow("dark")
    win.resize(1180, 760)
    yield win
    win._force_quit = True
    win.close()
    win.deleteLater()
    app.processEvents()
    gc.collect()


class TestCustomRootsScan:
    """Tests for CleanerService.scan_custom_roots."""

    def test_empty_directory_returns_zero(self, tmp_path: Path):
        """Scanning an empty folder must return 0 files and 0 bytes."""
        empty_dir = tmp_path / "empty_folder"
        empty_dir.mkdir()

        svc = CleanerService()
        report = svc.scan_custom_roots([empty_dir])

        assert report.total_files == 0
        assert report.total_reclaimable_bytes == 0
        assert len(report.scans) == 0

    def test_single_empty_file(self, tmp_path: Path):
        """Scanning a single empty file (0 bytes) reports 1 file under custom_empty_files."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_bytes(b"")

        svc = CleanerService()
        report = svc.scan_custom_roots([empty_file])

        assert report.total_files == 1
        assert report.total_reclaimable_bytes == 0
        assert len(report.scans) == 1
        scan = report.scans[0]
        assert scan.category.id == "custom_empty_files"
        assert len(scan.entries) == 1
        assert scan.entries[0].path == empty_file

    def test_directory_with_cleanable_categories(self, tmp_path: Path):
        """Scanning a directory categorizes build caches, temp files, logs, and empty files."""
        # 1. Build cache (node_modules)
        nm_dir = tmp_path / "node_modules" / "pkg"
        nm_dir.mkdir(parents=True)
        pkg_file = nm_dir / "index.js"
        pkg_file.write_bytes(b"console.log('test');" * 10)  # non-zero

        # 2. Temp file
        tmp_file = tmp_path / "scratch.tmp"
        tmp_file.write_bytes(b"temporary" * 50)

        # 3. Log file
        log_file = tmp_path / "app.log"
        log_file.write_bytes(b"error at 12:00\n" * 20)

        # 4. Cruft file
        cruft_file = tmp_path / "desktop.ini"
        cruft_file.write_bytes(b"[ViewState]")

        # 5. Empty file
        zero_file = tmp_path / "zero.dat"
        zero_file.write_bytes(b"")

        # 6. Important non-junk file (must NOT be counted in cleanup scans)
        important_file = tmp_path / "main.py"
        important_file.write_text("print('hello world')", encoding="utf-8")

        svc = CleanerService()
        report = svc.scan_custom_roots([tmp_path])

        cat_ids = {s.category.id for s in report.scans}
        assert "custom_build_caches" in cat_ids
        assert "custom_temp_files" in cat_ids
        assert "custom_log_files" in cat_ids
        assert "custom_cruft_files" in cat_ids
        assert "custom_empty_files" in cat_ids

        all_paths = {e.path for s in report.scans for e in s.entries}
        assert important_file not in all_paths
        assert pkg_file in all_paths
        assert tmp_file in all_paths
        assert log_file in all_paths
        assert cruft_file in all_paths
        assert zero_file in all_paths

        assert report.total_files == 5
        assert report.total_reclaimable_bytes > 0


class TestHubScanWorkerCustomRoots:
    """Tests for HubScanWorker handling custom_roots."""

    def test_worker_emits_custom_scan_report(self, tmp_path: Path):
        """HubScanWorker with custom_roots runs scan_custom_roots and emits finished."""
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        worker = HubScanWorker(custom_roots=[empty_dir])
        received_reports = []
        worker.finished.connect(received_reports.append)

        worker.run()

        assert len(received_reports) == 1
        rep = received_reports[0]
        assert rep.total_files == 0
        assert rep.total_reclaimable_bytes == 0


class TestCleanupHubPageCustomRoots:
    """Tests for CleanupHubPage displaying accurate counts for custom targets."""

    def test_empty_target_displays_zero_and_clean_state(self, window, tmp_path: Path):
        """When an empty directory is scanned, summary shows 0 B / 0 files and Clean button is disabled."""
        page = CleanupHubPage(window)
        empty_dir = tmp_path / "empty_test_folder"
        empty_dir.mkdir()

        page._custom_roots = [empty_dir]
        page._update_roots_status()
        assert "Active Scan Target:" in page.target_roots_label.text()
        assert not page.btn_clear_roots.isHidden()

        # Simulate scan result of empty target
        empty_report = CleanupReport(scans=[], duration_seconds=0.01)
        page._on_scanned(empty_report)

        assert page.card_total.value() in ("0.0 B", "0 B")
        assert page.card_files.value() == "0"
        assert page.card_cats.value() == "0"
        assert not page.clean_btn.isEnabled()

    def test_target_with_findings_populates_grid_and_enables_clean(self, window, tmp_path: Path):
        """When custom target has findings, summary shows real counts and Clean button is enabled."""
        page = CleanupHubPage(window)
        target_dir = tmp_path / "target_folder"
        target_dir.mkdir()

        page._custom_roots = [target_dir]
        page._update_roots_status()

        cat = CleanupCategory(
            id="custom_build_caches",
            label="Project Build & Package Caches",
            description="Build caches",
            risk=RiskLevel.LOW,
            paths=(target_dir,),
            reversible=True,
            default_enabled=True,
        )
        entry = FileEntry(path=target_dir / "index.js", size=1024 * 1024, mtime=0.0)
        scan = CategoryScan(category=cat, entries=[entry], total_bytes=1024 * 1024)
        report = CleanupReport(scans=[scan], duration_seconds=0.05)

        page._on_scanned(report)

        assert "1.00 MB" in page.card_total.value() or "1.0 MB" in page.card_total.value()
        assert page.card_files.value() == "1"
        assert page.card_cats.value() == "1"
        assert page.clean_btn.isEnabled()
        assert page.grid.count() == 1

    def test_reset_roots_restores_default_state(self, window, tmp_path: Path):
        """_clear_custom_roots resets targets back to default system partitions."""
        page = CleanupHubPage(window)
        page._custom_roots = [tmp_path]
        page._update_roots_status()
        assert not page.btn_clear_roots.isHidden()

        page._custom_roots.clear()
        page._update_roots_status()
        assert "Active Scan Roots: Default System Partitions" in page.target_roots_label.text()
        assert page.btn_clear_roots.isHidden()
