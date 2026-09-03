"""Smart Scanner — orchestrates parallel system analysis and produces a Health Score.

Scans:
  1. Junk/temp files across all temp directories + browser caches + Windows Update cache
  2. Registry orphans (if on Windows)
  3. Startup impact (reads real startup items from StartupManager)
  4. Privacy exposure (browser cookies/history/cache sizes)
  5. Recycle Bin, Prefetch, Thumbnail cache
"""

import logging
import os
import time
from typing import Dict, List, Any
from PySide6.QtCore import QObject, Signal
from cortex_unified.core.config import Config

try:
    from cortex_unified.system_tools.registry_cleaner import RegistryCleaner
    HAS_REGISTRY_CLEANER = True
except ImportError:
    HAS_REGISTRY_CLEANER = False


class SmartScanReport:
    """Holds the result of a Smart Scan."""

    def __init__(self):
        self.health_score: int = 100
        self.total_junk_mb: float = 0.0
        self.browser_cache_mb: float = 0.0
        self.win_update_cache_mb: float = 0.0
        self.recycle_bin_mb: float = 0.0
        self.prefetch_mb: float = 0.0
        self.thumbnail_cache_mb: float = 0.0
        self.registry_issues_count: int = 0
        self.startup_impact_score: int = 0
        self.startup_items_count: int = 0
        self.privacy_risks_count: int = 0
        self.scan_time_seconds: float = 0.0
        self.issues: List[Dict[str, Any]] = []
        """__init__."""

    @property
    def total_cleanable_mb(self) -> float:
        return (self.total_junk_mb + self.browser_cache_mb +
                self.win_update_cache_mb + self.recycle_bin_mb +
                self.prefetch_mb + self.thumbnail_cache_mb)
        """total_cleanable_mb."""

    def calculate_score(self):
        """Calculate 0-100 health score from real metrics."""
        deductions = 0

        # 1 point per 200 MB of junk (up to 30)
        deductions += min(30, int(self.total_cleanable_mb / 200))

        # Registry: 1 point per 20 issues (up to 15)
        if self.registry_issues_count > 0:
            deductions += min(15, int(self.registry_issues_count / 20))

        # Startup impact (already capped at 20)
        deductions += self.startup_impact_score

        # Privacy: 3 points per browser with data (up to 15)
        deductions += min(15, self.privacy_risks_count * 3)

        self.health_score = max(0, min(100, 100 - deductions))


class SmartScannerWorker(QObject):
    """Worker that runs in a QThread to perform the full smart scan."""

    finished = Signal(object)   # SmartScanReport
    error = Signal(str)
    progress_updated = Signal(str, int)  # (status_msg, percentage)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger("smart_scanner")
        self._should_stop = False
        """__init__."""

    def run(self):
        try:
            report = SmartScanReport()
            start_time = time.time()

            # ── Phase 1: Temp / Junk Files ─────────────────────────────
            self.progress_updated.emit("Scanning temporary files…", 5)
            report.total_junk_mb = self._scan_temp_dirs()
            if self._should_stop:
                return

            # ── Phase 2: Browser Caches ────────────────────────────────
            self.progress_updated.emit("Scanning browser caches…", 15)
            browser_mb, browser_count = self._scan_browser_caches()
            report.browser_cache_mb = browser_mb
            report.privacy_risks_count = browser_count
            if self._should_stop:
                return

            # ── Phase 3: Windows-specific caches ───────────────────────
            self.progress_updated.emit("Scanning Windows caches…", 30)
            report.win_update_cache_mb = self._scan_dir_mb(
                os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SoftwareDistribution", "Download")
            )
            report.prefetch_mb = self._scan_dir_mb(
                os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Prefetch")
            )
            report.thumbnail_cache_mb = self._scan_dir_mb(
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Explorer")
            )
            report.recycle_bin_mb = self._scan_recycle_bin()
            if self._should_stop:
                return

            # ── Phase 4: Registry Orphans ──────────────────────────────
            self.progress_updated.emit("Analyzing Windows Registry…", 50)
            if HAS_REGISTRY_CLEANER:
                try:
                    rc = RegistryCleaner()
                    orphans = rc.scan_orphaned_entries()
                    report.registry_issues_count = len(orphans)
                except Exception as exc:
                    self.logger.error("Registry scan error: %s", exc)
            if self._should_stop:
                return

            # ── Phase 5: Startup Impact ────────────────────────────────
            self.progress_updated.emit("Measuring startup impact…", 70)
            try:
                from cortex_unified.system_tools.startup_manager import StartupManager
                sm = StartupManager()
                items = sm.list_startup_items()
                report.startup_items_count = len(items)
                # Each startup item adds load; deduct 2 points per item over 5, capped at 20
                excess = max(0, len(items) - 5)
                report.startup_impact_score = min(20, excess * 2)
            except Exception as exc:
                self.logger.error("Startup scan error: %s", exc)
            if self._should_stop:
                return

            # ── Phase 6: Finalize ──────────────────────────────────────
            self.progress_updated.emit("Calculating health score…", 90)
            report.calculate_score()
            report.scan_time_seconds = time.time() - start_time

            self.progress_updated.emit("Smart Scan complete!", 100)
            self.finished.emit(report)

        except Exception as exc:
            self.logger.error("Smart Scan failed: %s", exc, exc_info=True)
            self.error.emit(str(exc))
        """run."""

    def stop(self):
        """Cooperative cancel: checked between phases and inside directory walks."""
        self._should_stop = True

    # ──────────────────────────────────────────────────────────────────
    # Helpers — each returns real bytes from the OS
    # ──────────────────────────────────────────────────────────────────

    def _scan_temp_dirs(self) -> float:
        """Walk every temp directory and sum file sizes.  Returns MB."""
        temp_paths = set()
        for var in ("TEMP", "TMP"):
            val = os.environ.get(var)
            if val:
                temp_paths.add(val)
        windir = os.environ.get("WINDIR", r"C:\Windows")
        temp_paths.add(os.path.join(windir, "Temp"))

        total = 0
        for tmp in temp_paths:
            if not os.path.isdir(tmp):
                continue
            for root, _dirs, files in os.walk(tmp):
                if self._should_stop:
                    break
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        return total / (1024 * 1024)

    def _scan_browser_caches(self) -> tuple:
        """Return (total_mb, number_of_browsers_with_data)."""
        local = os.environ.get("LOCALAPPDATA", "")
        appdata = os.environ.get("APPDATA", "")

        browsers = {
            "Chrome":  os.path.join(local, "Google", "Chrome", "User Data"),
            "Edge":    os.path.join(local, "Microsoft", "Edge", "User Data"),
            "Brave":   os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data"),
            "Opera":   os.path.join(appdata, "Opera Software", "Opera Stable"),
            "Firefox": os.path.join(appdata, "Mozilla", "Firefox", "Profiles"),
        }

        total = 0
        count = 0
        for name, base in browsers.items():
            if not os.path.isdir(base):
                continue
            size = self._scan_dir_mb(base, max_depth=3)
            if size > 0:
                total += size
                count += 1

        return total, count

    def _scan_dir_mb(self, path: str, max_depth: int = 5) -> float:
        """Recursively sum file sizes under *path*. Returns MB."""
        if not path or not os.path.isdir(path):
            return 0.0
        total = 0
        base_depth = path.count(os.sep)
        for root, _dirs, files in os.walk(path):
            if self._should_stop:
                break
            if root.count(os.sep) - base_depth >= max_depth:
                _dirs.clear()   # prune
                continue
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return total / (1024 * 1024)

    def _scan_recycle_bin(self) -> float:
        """Return approximate Recycle Bin size in MB."""
        recycle = os.path.join(os.environ.get("SystemDrive", "C:"), "$Recycle.Bin")
        if not os.path.isdir(recycle):
            return 0.0
        total = 0
        try:
            for root, _dirs, files in os.walk(recycle):
                if self._should_stop:
                    break
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
        except PermissionError:
            pass
        return total / (1024 * 1024)
