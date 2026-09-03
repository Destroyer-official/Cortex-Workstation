"""Dashboard tab — the command center for Cortex Cleaner.

Features a Smart Scan button, real-time health score, detailed breakdown
of cleanable items, and a working Optimize Now button that actually cleans.
"""

import os
import shutil
import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QListWidget, QFrame,
    QMessageBox,
)
from PySide6.QtCore import QThread, Qt, Signal, QObject
from PySide6.QtGui import QFont

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.core.smart_scanner import SmartScannerWorker, SmartScanReport


# ──────────────────────────────────────────────────────────────────────
# Optimizer worker — runs actual cleanup in a background thread
# ──────────────────────────────────────────────────────────────────────

class OptimizerWorker(QObject):
    """Deletes junk files discovered by SmartScan."""

    finished = Signal(dict)   # {"cleaned_mb": float, "errors": int}
    error = Signal(str)
    progress = Signal(str)

    def __init__(self):
        """Create the optimizer with a dedicated logger and a clear stop flag."""
        super().__init__()
        self.logger = logging.getLogger("optimizer")
        self._should_stop = False

    def run(self):
        """Delete temp files, Prefetch contents, and thumbnail caches.

        Walks %TEMP%/%TMP%/Windows\\Temp, the Prefetch folder, and the
        Explorer thumbcache directory, tallying bytes freed and files that
        could not be removed. Emits ``progress`` with status messages,
        ``finished`` with {"cleaned_mb", "errors"} on success, and ``error``
        on failure.
        """
        cleaned = 0
        errors = 0

        temp_paths = set()
        for var in ("TEMP", "TMP"):
            val = os.environ.get(var)
            if val and os.path.isdir(val):
                temp_paths.add(val)
        windir = os.environ.get("WINDIR", r"C:\Windows")
        temp_paths.add(os.path.join(windir, "Temp"))

        # 1) Clean temp directories
        for tmp in temp_paths:
            if not os.path.isdir(tmp):
                continue
            self.progress.emit(f"Cleaning {tmp}…")
            for root, dirs, files in os.walk(tmp, topdown=False):
                if self._should_stop:
                    break
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fp)
                        os.remove(fp)
                        cleaned += size
                    except OSError:
                        errors += 1
                for d in dirs:
                    dp = os.path.join(root, d)
                    try:
                        os.rmdir(dp)
                    except OSError:
                        pass

        # 2) Windows Prefetch
        prefetch = os.path.join(windir, "Prefetch")
        if os.path.isdir(prefetch):
            self.progress.emit("Cleaning Prefetch…")
            for f in os.listdir(prefetch):
                if self._should_stop:
                    break
                fp = os.path.join(prefetch, f)
                try:
                    if os.path.isfile(fp):
                        size = os.path.getsize(fp)
                        os.remove(fp)
                        cleaned += size
                except OSError:
                    errors += 1

        # 3) Thumbnail cache
        thumb_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Explorer")
        if os.path.isdir(thumb_dir):
            self.progress.emit("Cleaning thumbnail cache…")
            for f in os.listdir(thumb_dir):
                if f.startswith("thumbcache_") and f.endswith(".db"):
                    fp = os.path.join(thumb_dir, f)
                    try:
                        size = os.path.getsize(fp)
                        os.remove(fp)
                        cleaned += size
                    except OSError:
                        errors += 1

        self.finished.emit({
            "cleaned_mb": cleaned / (1024 * 1024),
            "errors": errors,
        })

    def stop(self):
        """Request a cooperative stop by setting the cancel flag."""
        self._should_stop = True


# ──────────────────────────────────────────────────────────────────────
# Dashboard Tab
# ──────────────────────────────────────────────────────────────────────

class DashboardTab(BaseTab):
    """Modern dashboard with Smart Scan and real Optimize Now."""

    def __init__(self, config, logger, safety_manager, parent=None):
        """Initialize the tab and track the scan/optimizer threads and last report."""
        super().__init__(config, logger, safety_manager)
        self.parent_window = parent
        self.scan_thread = None
        self.scanner = None
        self.opt_thread = None
        self.optimizer = None
        self.last_report: SmartScanReport = None

    # ── UI Setup ──────────────────────────────────────────────────────

    def setup_ui(self):
        """Build the dashboard layout.

        Creates the header with title/status and a large health-score
        label, a hidden progress bar, the Smart Scan button, an
        "Optimization Opportunities" group with a findings list and
        Optimize Now button (hidden until a scan completes), and a quick
        navigation row with buttons for Deep Uninstaller, Privacy Shield,
        and File Shredder tabs.
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # ── Header row ────────────────────────────────────────────────
        header_layout = QHBoxLayout()
        left = QVBoxLayout()

        title = QLabel("System Dashboard")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        left.addWidget(title)

        self.status_label = QLabel("Ready — run a Smart Scan to analyze your system")
        sf = QFont()
        sf.setPointSize(11)
        self.status_label.setFont(sf)
        self.status_label.setStyleSheet("color: gray;")
        left.addWidget(self.status_label)

        header_layout.addLayout(left)
        header_layout.addStretch()

        # Health score display
        self.score_label = QLabel("--")
        scf = QFont()
        scf.setPointSize(44)
        scf.setBold(True)
        self.score_label.setFont(scf)
        self.score_label.setStyleSheet("color: #4CAF50;")
        header_layout.addWidget(self.score_label)

        desc = QLabel("Health\nScore")
        desc.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(desc)

        layout.addLayout(header_layout)

        # ── Progress bar ──────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; height: 25px; }
            QProgressBar::chunk { background-color: #2196F3; }
        """)
        layout.addWidget(self.progress_bar)

        # ── Smart Scan button ─────────────────────────────────────────
        self.smart_scan_btn = QPushButton("START SMART SCAN")
        bfont = QFont()
        bfont.setPointSize(15)
        bfont.setBold(True)
        self.smart_scan_btn.setFont(bfont)
        self.smart_scan_btn.setMinimumHeight(55)
        self.smart_scan_btn.setStyleSheet("""
            QPushButton      { background-color: #4CAF50; color: white; border-radius: 10px; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #ccc; color: #666; }
        """)
        self.smart_scan_btn.clicked.connect(self.run_smart_scan)
        layout.addWidget(self.smart_scan_btn)

        # ── Separator ─────────────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # ── Details group (hidden until scan completes) ───────────────
        self.details_group = QGroupBox("Optimization Opportunities")
        self.details_group.setVisible(False)
        dlayout = QVBoxLayout(self.details_group)
        self.details_list = QListWidget()
        dlayout.addWidget(self.details_list)

        self.optimize_btn = QPushButton("OPTIMIZE NOW")
        self.optimize_btn.setMinimumHeight(40)
        self.optimize_btn.setStyleSheet("""
            QPushButton      { background-color: #FF9800; color: white; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background-color: #F57C00; }
            QPushButton:disabled { background-color: #ccc; color: #666; }
        """)
        self.optimize_btn.clicked.connect(self.run_optimization)
        dlayout.addWidget(self.optimize_btn)

        layout.addWidget(self.details_group)

        # ── Quick navigation ──────────────────────────────────────────
        qg = QGroupBox("Advanced Tools")
        ql = QHBoxLayout(qg)
        for label, tab in [("Deep Uninstaller", "Deep Uninstaller"),
                           ("Privacy Shield", "Privacy Shield"),
                           ("Data Shredder", "File Shredder")]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, t=tab: self.navigate_to(t))
            ql.addWidget(btn)
        layout.addWidget(qg)
        layout.addStretch()

    def setup_tooltips(self):
        """Set the Smart Scan button tooltip."""
        self.smart_scan_btn.setToolTip("Run a comprehensive system analysis")

    # ── Smart Scan ────────────────────────────────────────────────────

    def run_smart_scan(self):
        """Run SmartScannerWorker on a background QThread.

        Disables the scan button, shows the progress bar, and hides any
        previous details while the scanner analyzes the system. Progress,
        completion, and error signals update the UI and clean up the thread.
        """
        self.smart_scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Scanning…")
        self.details_group.setVisible(False)

        self.scan_thread = QThread()
        self.scanner = SmartScannerWorker(self.config)
        self.scanner.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scanner.run)
        self.scanner.progress_updated.connect(self._on_progress)
        self.scanner.finished.connect(self._on_scan_finished)
        self.scanner.error.connect(self._on_scan_error)

        self.scanner.finished.connect(self.scan_thread.quit)
        self.scanner.error.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)

        self.scan_thread.start()

    def _on_progress(self, msg, pct):
        """Forward scanner progress to the status label and progress bar."""
        self.status_label.setText(msg)
        self.progress_bar.setValue(pct)

    def _on_scan_finished(self, report: SmartScanReport):
        """Display the finished SmartScanReport.

        Stores the report, re-labels the scan button to RESCAN, colors the
        health score (green/yellow/red by threshold), and populates the
        details list with per-category junk sizes, registry orphans, and
        startup impact before revealing the results group.
        """
        self.last_report = report
        self.smart_scan_btn.setEnabled(True)
        self.smart_scan_btn.setText("RESCAN SYSTEM")
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Scan complete in {report.scan_time_seconds:.1f}s — "
                                  f"{report.total_cleanable_mb:.0f} MB reclaimable")

        # Score color
        self.score_label.setText(str(report.health_score))
        if report.health_score > 80:
            self.score_label.setStyleSheet("color: #4CAF50;")
        elif report.health_score > 55:
            self.score_label.setStyleSheet("color: #FFC107;")
        else:
            self.score_label.setStyleSheet("color: #F44336;")

        # Breakdown
        self.details_list.clear()
        self.details_list.addItem(f"🗑️  Temp files: {report.total_junk_mb:.1f} MB")
        self.details_list.addItem(f"🌐  Browser caches: {report.browser_cache_mb:.1f} MB ({report.privacy_risks_count} browsers)")
        self.details_list.addItem(f"📦  Windows Update cache: {report.win_update_cache_mb:.1f} MB")
        self.details_list.addItem(f"♻️  Recycle Bin: {report.recycle_bin_mb:.1f} MB")
        self.details_list.addItem(f"⚡  Prefetch: {report.prefetch_mb:.1f} MB")
        self.details_list.addItem(f"🖼️  Thumbnail cache: {report.thumbnail_cache_mb:.1f} MB")
        self.details_list.addItem(f"🔧  Registry orphans: {report.registry_issues_count}")
        self.details_list.addItem(f"🚀  Startup items: {report.startup_items_count} "
                                  f"({report.startup_impact_score} impact pts)")

        self.details_group.setVisible(True)
        self.optimize_btn.setEnabled(True)

    def _on_scan_error(self, msg):
        """Re-enable the scan button and show a critical error dialog."""
        self.smart_scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Scan failed")
        QMessageBox.critical(self, "Error", f"Smart Scan failed:\n{msg}")

    # ── Optimize Now (REAL cleaning) ──────────────────────────────────

    def run_optimization(self):
        """Clean junk found by the last scan using OptimizerWorker.

        Guards against running with no findings, confirms the destructive
        action (browser data is explicitly excluded), then runs the
        OptimizerWorker on a background thread with an indeterminate
        progress bar while its progress/finished/error signals update the UI.
        """
        if not self.last_report or self.last_report.total_cleanable_mb < 1:
            QMessageBox.information(self, "Nothing to clean",
                                    "No significant junk was found.")
            return

        reply = QMessageBox.question(
            self, "Confirm Optimization",
            f"This will permanently delete ~{self.last_report.total_cleanable_mb:.0f} MB "
            f"of temp files, prefetch, and thumbnail caches.\n\n"
            f"Browser data is NOT touched here (use Privacy Shield).\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.optimize_btn.setEnabled(False)
        self.optimize_btn.setText("Optimizing…")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate

        self.opt_thread = QThread()
        self.optimizer = OptimizerWorker()
        self.optimizer.moveToThread(self.opt_thread)

        self.opt_thread.started.connect(self.optimizer.run)
        self.optimizer.progress.connect(lambda m: self.status_label.setText(m))
        self.optimizer.finished.connect(self._on_optimize_done)
        self.optimizer.error.connect(self._on_optimize_error)

        self.optimizer.finished.connect(self.opt_thread.quit)
        self.optimizer.error.connect(self.opt_thread.quit)
        self.opt_thread.finished.connect(self.opt_thread.deleteLater)

        self.opt_thread.start()

    def _on_optimize_done(self, result: dict):
        """Show freed space and skipped-file counts after optimization."""
        mb = result.get("cleaned_mb", 0)
        errs = result.get("errors", 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.optimize_btn.setText("OPTIMIZE NOW")
        self.optimize_btn.setEnabled(False)
        self.status_label.setText(f"Freed {mb:.1f} MB — {errs} files skipped (in use)")

        QMessageBox.information(
            self, "Optimization Complete",
            f"Cleaned {mb:.1f} MB of junk.\n"
            f"{errs} files could not be removed (locked by other programs).\n\n"
            f"Run Smart Scan again to see your new health score.",
        )

    def _on_optimize_error(self, msg):
        """Re-enable the optimize button and show the failure dialog."""
        self.progress_bar.setVisible(False)
        self.optimize_btn.setText("OPTIMIZE NOW")
        self.optimize_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Optimization failed:\n{msg}")

    # ── Navigation ────────────────────────────────────────────────────

    def navigate_to(self, tab_name):
        """Switch to the named tab via the parent window's navigation controller."""
        if self.parent_window and hasattr(self.parent_window, "navigation_controller"):
            self.parent_window.navigation_controller.set_current_tab_by_name(tab_name)
