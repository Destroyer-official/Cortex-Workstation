"""Privacy Shield tab — comprehensive browser and system privacy management.

Features:
  - OS Telemetry blocking (16 rules) with restore capability
  - Browser data scanning and cleaning for all major browsers
  - System privacy traces (Recent docs, INetCache, DNS cache)
  - Detailed tree-view with per-category checkboxes
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QProgressBar,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from .base_tab import BaseTab
from cortex_unified.analyzers.privacy_cleaner import PrivacyCleaner
from cortex_unified.system_tools.telemetry_blocker import TelemetryBlocker


# ──────────────────────────────────────────────────────────────────────
# Workers
# ──────────────────────────────────────────────────────────────────────

class BrowserScanWorker(QObject):
    """Scan browsers + system traces in a background thread."""
    finished = Signal(dict, dict)  # browser_data, system_traces

    def run(self):
        cleaner = PrivacyCleaner()
        browsers = cleaner.scan_browsers()
        traces = cleaner.scan_system_traces()
        self.finished.emit(browsers, traces)
        """run."""
        """run."""


# ──────────────────────────────────────────────────────────────────────
# Privacy Tab
# ──────────────────────────────────────────────────────────────────────

class PrivacyTab(BaseTab):
    """Privacy Shield — telemetry blocking and browser data management."""

    def __init__(self, config, logger, safety_manager, parent=None):
        self.cleaner = PrivacyCleaner()
        self.telemetry = TelemetryBlocker()
        self._scan_thread = None
        self._scan_worker = None
        self._last_browser_results = {}
        super().__init__(config, logger, safety_manager)
        """__init__."""
        """__init__."""

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # ── Header ───────────────────────────────────────────────────
        header = QLabel("Privacy Shield")
        hf = QFont(); hf.setPointSize(18); hf.setBold(True)
        header.setFont(hf)
        main_layout.addWidget(header)

        # ── OS Telemetry Group ───────────────────────────────────────
        os_group = QGroupBox("Windows Telemetry & Tracking")
        os_layout = QVBoxLayout(os_group)

        self.lbl_telemetry = QLabel("Checking…")
        self.lbl_telemetry.setWordWrap(True)
        os_layout.addWidget(self.lbl_telemetry)

        btn_row = QHBoxLayout()
        self.btn_block = QPushButton("Block All Telemetry")
        self.btn_block.setStyleSheet(
            "background-color: #2196F3; color: white; padding: 8px; font-weight: bold;"
        )
        self.btn_block.clicked.connect(self._apply_block)
        btn_row.addWidget(self.btn_block)

        self.btn_restore = QPushButton("Restore Defaults")
        self.btn_restore.setStyleSheet("padding: 8px;")
        self.btn_restore.clicked.connect(self._restore_telemetry)
        btn_row.addWidget(self.btn_restore)

        os_layout.addLayout(btn_row)

        # Per-rule status
        self.telemetry_tree = QTreeWidget()
        self.telemetry_tree.setHeaderLabels(["Telemetry Feature", "Status"])
        self.telemetry_tree.setMaximumHeight(200)
        os_layout.addWidget(self.telemetry_tree)

        main_layout.addWidget(os_group)

        # ── Browser Data Group ───────────────────────────────────────
        browser_group = QGroupBox("Browser & System Privacy Sweeper")
        browser_layout = QVBoxLayout(browser_group)

        self.btn_scan = QPushButton("Scan Browsers & System Traces")
        self.btn_scan.setStyleSheet("padding: 8px; font-weight: bold;")
        self.btn_scan.clicked.connect(self._scan_browsers)
        browser_layout.addWidget(self.btn_scan)

        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)
        self.scan_progress.setVisible(False)
        browser_layout.addWidget(self.scan_progress)

        self.browser_tree = QTreeWidget()
        self.browser_tree.setHeaderLabels(["Browser / Data Type", "Size"])
        browser_layout.addWidget(self.browser_tree)

        self.btn_sweep = QPushButton("Sweep Selected Data")
        self.btn_sweep.setMinimumHeight(38)
        self.btn_sweep.setStyleSheet(
            "background-color: #F44336; color: white; font-weight: bold; border-radius: 5px;"
        )
        self.btn_sweep.setEnabled(False)
        self.btn_sweep.clicked.connect(self._clean_browsers)
        browser_layout.addWidget(self.btn_sweep)

        main_layout.addWidget(browser_group)
        main_layout.addStretch()

        # Initial telemetry check
        self._refresh_telemetry()
        """setup_ui."""
        """setup_ui."""

    def setup_tooltips(self):
        self.btn_block.setToolTip("Modify registry to disable Windows telemetry (Admin required)")
        self.btn_restore.setToolTip("Remove custom telemetry blocks and restore Windows defaults")
        """setup_tooltips."""
        """setup_tooltips."""

    # ── Telemetry ─────────────────────────────────────────────────────

    def _refresh_telemetry(self):
        status = self.telemetry.check_status()
        blocked = sum(1 for v in status.values() if v)
        total = len(status)

        self.telemetry_tree.clear()
        for label, is_blocked in status.items():
            item = QTreeWidgetItem(self.telemetry_tree)
            item.setText(0, label)
            if is_blocked:
                item.setText(1, "✅ Blocked")
            else:
                item.setText(1, "⚠️ Active")

        if blocked == total and total > 0:
            self.lbl_telemetry.setText(f"✅ All {total} telemetry features are blocked.")
            self.lbl_telemetry.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.btn_block.setEnabled(False)
            self.btn_block.setText("All Blocked")
        elif blocked > 0:
            self.lbl_telemetry.setText(f"⚠️ {total - blocked} of {total} telemetry features are still active.")
            self.lbl_telemetry.setStyleSheet("color: #FF9800; font-weight: bold;")
            self.btn_block.setEnabled(True)
            self.btn_block.setText("Block All Telemetry")
        else:
            self.lbl_telemetry.setText(f"🔴 All {total} telemetry features are active.")
            self.lbl_telemetry.setStyleSheet("color: #F44336; font-weight: bold;")
            self.btn_block.setEnabled(True)
        """_refresh_telemetry."""
        """_refresh_telemetry."""

    def _apply_block(self):
        reply = QMessageBox.question(
            self, "Block Telemetry",
            "This will modify Windows Registry settings to disable diagnostic "
            "tracking, advertising, Cortana web search, and more.\n\n"
            "Administrator privileges are required.\nProceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok = self.telemetry.block_telemetry()
            if ok:
                QMessageBox.information(self, "Success", "All telemetry features have been blocked.")
            else:
                QMessageBox.warning(
                    self, "Partial Success",
                    "Some rules could not be applied.\n"
                    "Ensure the app is running as Administrator.",
                )
            self._refresh_telemetry()
        """_apply_block."""
        """_apply_block."""

    def _restore_telemetry(self):
        reply = QMessageBox.question(
            self, "Restore Defaults",
            "This will remove all custom telemetry blocks and restore "
            "Windows default settings.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok = self.telemetry.restore_defaults()
            if ok:
                QMessageBox.information(self, "Restored", "Telemetry settings restored to defaults.")
            else:
                QMessageBox.warning(self, "Warning", "Some defaults could not be restored.")
            self._refresh_telemetry()
        """_restore_telemetry."""
        """_restore_telemetry."""

    # ── Browser Scan ──────────────────────────────────────────────────

    def _scan_browsers(self):
        self.browser_tree.clear()
        self.btn_scan.setEnabled(False)
        self.btn_sweep.setEnabled(False)
        self.scan_progress.setVisible(True)

        self._scan_thread = QThread()
        self._scan_worker = BrowserScanWorker()
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)

        self._scan_thread.start()
        """_scan_browsers."""
        """_scan_browsers."""

    def _on_scan_done(self, browser_results: dict, system_traces: dict):
        self._last_browser_results = browser_results
        self.browser_tree.clear()
        self.scan_progress.setVisible(False)
        self.btn_scan.setEnabled(True)

        grand_total = 0

        # Browser entries
        for browser, stats in browser_results.items():
            b_item = QTreeWidgetItem(self.browser_tree)
            b_item.setText(0, f"🌐 {browser}")
            b_item.setFlags(b_item.flags() | Qt.ItemIsUserCheckable)
            b_item.setCheckState(0, Qt.Checked)

            b_total = 0
            for category, size_bytes in stats.items():
                if size_bytes > 0:
                    c_item = QTreeWidgetItem(b_item)
                    c_item.setText(0, category)
                    mb = size_bytes / (1024 * 1024)
                    c_item.setText(1, f"{mb:.2f} MB")
                    c_item.setFlags(c_item.flags() | Qt.ItemIsUserCheckable)
                    c_item.setCheckState(0, Qt.Checked)
                    b_total += size_bytes

            b_item.setText(1, f"{b_total / (1024 * 1024):.2f} MB")
            grand_total += b_total

        # System traces
        if system_traces:
            sys_item = QTreeWidgetItem(self.browser_tree)
            sys_item.setText(0, "🖥️ System Traces")
            sys_item.setFlags(sys_item.flags() | Qt.ItemIsUserCheckable)
            sys_item.setCheckState(0, Qt.Checked)

            s_total = 0
            for name, size_bytes in system_traces.items():
                c_item = QTreeWidgetItem(sys_item)
                c_item.setText(0, name)
                mb = size_bytes / (1024 * 1024)
                c_item.setText(1, f"{mb:.2f} MB")
                c_item.setFlags(c_item.flags() | Qt.ItemIsUserCheckable)
                c_item.setCheckState(0, Qt.Checked)
                s_total += size_bytes

            sys_item.setText(1, f"{s_total / (1024 * 1024):.2f} MB")
            grand_total += s_total

        self.browser_tree.expandAll()

        if grand_total > 0:
            self.btn_sweep.setEnabled(True)
            self.btn_sweep.setText(
                f"Sweep Selected Data ({grand_total / (1024 * 1024):.1f} MB)"
            )
        else:
            QMessageBox.information(self, "Clean", "No privacy traces found!")
        """_on_scan_done."""
        """_on_scan_done."""

    # ── Browser Clean ─────────────────────────────────────────────────

    def _clean_browsers(self):
        # Gather checked items
        to_clean = {}
        clean_system = False

        for i in range(self.browser_tree.topLevelItemCount()):
            top = self.browser_tree.topLevelItem(i)
            label = top.text(0)

            items = []
            for j in range(top.childCount()):
                child = top.child(j)
                if child.checkState(0) == Qt.Checked:
                    items.append(child.text(0))

            if items:
                if "System Traces" in label:
                    clean_system = True
                else:
                    # Strip the emoji prefix to get browser name
                    browser_name = label.replace("🌐 ", "").strip()
                    to_clean[browser_name] = items

        if not to_clean and not clean_system:
            return

        reply = QMessageBox.question(
            self, "Confirm Privacy Sweep",
            "Make sure your browsers are CLOSED.\n\n"
            "This will permanently delete the selected cookies, cache, "
            "history, and session data.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        all_ok = True
        for browser, items in to_clean.items():
            if not self.cleaner.clean_browser(browser, items):
                all_ok = False

        if clean_system:
            self.cleaner.clean_system_traces()

        if all_ok:
            QMessageBox.information(self, "Success", "Selected privacy traces have been cleared.")
        else:
            QMessageBox.warning(
                self, "Partial Success",
                "Some files could not be deleted.\n"
                "Make sure browsers are closed and try again.",
            )

        # Rescan
        self._scan_browsers()
        """_clean_browsers."""
        """_clean_browsers."""
