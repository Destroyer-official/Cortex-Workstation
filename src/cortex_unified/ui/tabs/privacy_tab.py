"""Privacy Shield tab — comprehensive browser and system privacy management.

Features:
  - OS Telemetry blocking (16 rules) with restore capability
  - Browser data scanning and cleaning for all major browsers
  - System privacy traces (Recent docs, INetCache, DNS cache)
  - Detailed tree-view with per-category checkboxes
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QLineEdit, QFileDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from .base_tab import BaseTab
from cortex_unified.analyzers.privacy_cleaner import PrivacyCleaner
from cortex_unified.system_tools.telemetry_blocker import TelemetryBlocker
from cortex_unified.analyzers.czkawka_tools import ExifCleaner


# ──────────────────────────────────────────────────────────────────────
# Workers
# ──────────────────────────────────────────────────────────────────────

class BrowserScanWorker(QObject):
    """Browserscanworker.

    Manages BrowserScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict, dict)  # browser_data, system_traces

    def run(self):
        """Scan browsers and system traces via PrivacyCleaner.

        Runs scan_browsers() and scan_system_traces() off the UI thread
        and emits ``finished(browser_data, system_traces)``.
        """
        cleaner = PrivacyCleaner()
        browsers = cleaner.scan_browsers()
        traces = cleaner.scan_system_traces()
        self.finished.emit(browsers, traces)


class ExifScanWorker(QThread):
    """Exifscanworker.

    Manages ExifScanWorker operations and coordinates related state changes for the component.
    """
    scan_finished = Signal(list)
    strip_finished = Signal(dict)
    error = Signal(str)

    def __init__(self, root: str, action: str = "scan", paths_to_strip: list | None = None):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            root (str): Filesystem path to the target file or directory.
            action (str): The action parameter.
            paths_to_strip (list | None): Filesystem path to the target file or directory.
        """
        super().__init__()
        self.root = root
        self.action = action
        self.paths_to_strip = paths_to_strip or []

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            cleaner = ExifCleaner(root=self.root)
            if self.action == "scan":
                findings = cleaner.scan()
                self.scan_finished.emit([(str(p), tags) for p, tags in findings])
            elif self.action == "strip":
                res = cleaner.strip([Path(p) for p in self.paths_to_strip])
                self.strip_finished.emit({str(p): ok for p, ok in res.items()})
        except Exception as exc:
            self.error.emit(str(exc))


# ──────────────────────────────────────────────────────────────────────
# Privacy Tab
# ──────────────────────────────────────────────────────────────────────

class PrivacyTab(BaseTab):
    """Privacytab.

    Manages PrivacyTab operations and coordinates related state changes for the component.
    """

    def __init__(self, config, logger, safety_manager, parent=None):
        """Create the PrivacyCleaner/TelemetryBlocker backends and scan state.

        Initializes the instance and configures internal state.

        Args:
            config: The config parameter.
            logger: The logger parameter.
            safety_manager: The safety manager parameter.
            parent: Parent window or shell controller instance.
        """
        self.cleaner = PrivacyCleaner()
        self.telemetry = TelemetryBlocker()
        self._scan_thread = None
        self._scan_worker = None
        self._last_browser_results = {}
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Build the Privacy Shield layout.

        Creates a telemetry group with block/restore buttons and a
        per-rule status tree, plus a browser data group with a scan
        button, busy bar, a checkable browser/traces tree, and a Sweep
        button. Ends by checking the current telemetry status.
        """
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

        self.chk_sweep_strip_exif = QCheckBox("Also Strip Photo EXIF metadata during sweep (Czkawka)")
        self.chk_sweep_strip_exif.setToolTip("Strip GPS locations and camera metadata from photos in the target folder during privacy sweep")
        browser_layout.addWidget(self.chk_sweep_strip_exif)

        self.btn_sweep = QPushButton("Sweep Selected Data")
        self.btn_sweep.setMinimumHeight(38)
        self.btn_sweep.setStyleSheet(
            "background-color: #F44336; color: white; font-weight: bold; border-radius: 5px;"
        )
        self.btn_sweep.setEnabled(False)
        self.btn_sweep.clicked.connect(self._clean_browsers)
        browser_layout.addWidget(self.btn_sweep)

        main_layout.addWidget(browser_group)

        # ── EXIF Privacy Group (Czkawka) ──────────────────────────────
        exif_group = QGroupBox("Photo EXIF & Location Privacy (Czkawka)")
        exif_layout = QVBoxLayout(exif_group)

        self._exif_findings = []
        path_row = QHBoxLayout()
        self.exif_path_edit = QLineEdit(str(Path.home() / "Pictures"))
        path_row.addWidget(self.exif_path_edit)
        self.btn_exif_browse = QPushButton("Browse...")
        self.btn_exif_browse.clicked.connect(self._pick_exif_folder)
        path_row.addWidget(self.btn_exif_browse)
        exif_layout.addLayout(path_row)

        btn_row2 = QHBoxLayout()
        self.btn_exif_scan = QPushButton("Scan Photos for EXIF")
        self.btn_exif_scan.setStyleSheet("padding: 8px; font-weight: bold;")
        self.btn_exif_scan.clicked.connect(self._scan_exif)
        btn_row2.addWidget(self.btn_exif_scan)

        self.btn_exif_strip = QPushButton("Strip EXIF Metadata")
        self.btn_exif_strip.setStyleSheet(
            "background-color: #E91E63; color: white; padding: 8px; font-weight: bold; border-radius: 5px;"
        )
        self.btn_exif_strip.setEnabled(False)
        self.btn_exif_strip.clicked.connect(self._strip_exif)
        btn_row2.addWidget(self.btn_exif_strip)
        exif_layout.addLayout(btn_row2)

        self.exif_progress = QProgressBar()
        self.exif_progress.setRange(0, 0)
        self.exif_progress.setVisible(False)
        exif_layout.addWidget(self.exif_progress)

        self.lbl_exif_status = QLabel("Ready to scan photo library for GPS coordinates and camera metadata.")
        self.lbl_exif_status.setWordWrap(True)
        exif_layout.addWidget(self.lbl_exif_status)

        main_layout.addWidget(exif_group)
        main_layout.addStretch()

        # Initial telemetry check
        self._refresh_telemetry()

    def setup_tooltips(self):
        """Set tooltips for the telemetry block/restore buttons.

        Manages setup tooltips operations and coordinates related state changes for the component.
        """
        self.btn_block.setToolTip("Modify registry to disable Windows telemetry (Admin required)")
        self.btn_restore.setToolTip("Remove custom telemetry blocks and restore Windows defaults")

    # ── Telemetry ─────────────────────────────────────────────────────

    def _refresh_telemetry(self):
        """Reload the per-rule telemetry tree from TelemetryBlocker status.

        Marks each feature Blocked/Active and updates the summary label
        and Block button state (all blocked, partial, or none).
        """
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

    def _apply_block(self):
        """Confirm, then apply all telemetry blocks via TelemetryBlocker.

        Warns about partial success (admin privileges may be required) and
        refreshes the status tree afterwards.
        """
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

    def _restore_telemetry(self):
        """Confirm, then restore default telemetry settings via TelemetryBlocker.

        Reports full or partial restoration and refreshes the status tree.
        """
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

    # ── Browser Scan ──────────────────────────────────────────────────

    def _scan_browsers(self):
        """Run BrowserScanWorker on a background thread.

        Clears the results tree, disables the scan/sweep buttons, shows
        the busy bar, and wires the worker's finished signal back to the
        UI while quitting/deleting the thread afterwards.
        """
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

    def _on_scan_done(self, browser_results: dict, system_traces: dict):
        """Build the checkable results tree from the scan.

        Adds per-browser parents with checked category children (each
        sized in MB), a System Traces group, and a grand total; enables
        the Sweep button sized to the total or reports a clean result.
        """
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

    # ── Browser Clean ─────────────────────────────────────────────────

    def _clean_browsers(self):
        """Delete the checked browser categories and system traces.

        Gathers checked children per browser (stripping emoji prefixes),
        confirms after warning that browsers must be closed, calls
        PrivacyCleaner.clean_browser/clean_system_traces, reports full or
        partial success, and rescans.
        """
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

        if self.chk_sweep_strip_exif.isChecked():
            if self._exif_findings:
                self._strip_exif()
            else:
                self._scan_exif()

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

    # ── Photo EXIF Metadata (Czkawka) ─────────────────────────────────

    def _pick_exif_folder(self):
        """Browse to select a photo folder for EXIF scanning.

        Manages pick exif folder operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Photos Directory", self.exif_path_edit.text())
        if folder:
            self.exif_path_edit.setText(folder)

    def _scan_exif(self):
        """Scan selected photo folder for embedded EXIF metadata.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        target = self.exif_path_edit.text().strip()
        if not target or not Path(target).exists():
            QMessageBox.warning(self, "Invalid Path", "Please select a valid folder.")
            return
        self.exif_progress.setVisible(True)
        self.btn_exif_scan.setEnabled(False)
        self.btn_exif_strip.setEnabled(False)
        self.lbl_exif_status.setText("Scanning photos for EXIF metadata...")

        worker = ExifScanWorker(root=target, action="scan")
        self.add_worker_thread(worker)
        worker.scan_finished.connect(self._on_exif_scan_done)
        worker.error.connect(self._on_exif_error)
        worker.finished.connect(lambda: self._teardown_worker(worker))
        worker.start()

    def _on_exif_scan_done(self, findings: list):
        """Handle completion of photo EXIF scan.

        Receives the completed data from the exif scan background worker, populates the view with results, and restores button states.

        Args:
            findings (list): The findings parameter.
        """
        self.exif_progress.setVisible(False)
        self.btn_exif_scan.setEnabled(True)
        self._exif_findings = findings
        if not findings:
            self.lbl_exif_status.setText("✅ No photo files with exposed EXIF metadata found.")
            self.btn_exif_strip.setEnabled(False)
        else:
            gps_count = sum(1 for _, tags in findings if any("gps" in str(k).lower() for k in tags.keys()))
            self.lbl_exif_status.setText(
                f"Found {len(findings)} photos with EXIF metadata ({gps_count} containing GPS location coordinates)."
            )
            self.btn_exif_strip.setEnabled(True)

    def _strip_exif(self):
        """Strip EXIF metadata in-place from scanned photos.

        Manages strip exif operations and coordinates related state changes for the component.
        """
        if not self._exif_findings:
            return
        reply = QMessageBox.question(
            self, "Confirm EXIF Strip",
            f"This will remove EXIF metadata (including GPS location coordinates) in-place from {len(self._exif_findings)} photos.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.exif_progress.setVisible(True)
        self.btn_exif_scan.setEnabled(False)
        self.btn_exif_strip.setEnabled(False)
        self.lbl_exif_status.setText("Stripping EXIF metadata...")

        paths = [p for p, _ in self._exif_findings]
        worker = ExifScanWorker(root=self.exif_path_edit.text(), action="strip", paths_to_strip=paths)
        self.add_worker_thread(worker)
        worker.strip_finished.connect(self._on_exif_strip_done)
        worker.error.connect(self._on_exif_error)
        worker.finished.connect(lambda: self._teardown_worker(worker))
        worker.start()

    def _on_exif_strip_done(self, results: dict):
        """Handle completion of EXIF stripping.

        Receives the completed data from the exif strip background worker, populates the view with results, and restores button states.

        Args:
            results (dict): Dictionary or data object holding operation results.
        """
        self.exif_progress.setVisible(False)
        self.btn_exif_scan.setEnabled(True)
        success_count = sum(1 for ok in results.values() if ok)
        self.lbl_exif_status.setText(f"Successfully stripped EXIF metadata from {success_count} / {len(results)} photos.")
        QMessageBox.information(self, "EXIF Scrubbed", f"Stripped EXIF metadata from {success_count} photos.")
        self._scan_exif()

    def _on_exif_error(self, err: str):
        """Handle EXIF worker error.

        Manages on exif error operations and coordinates related state changes for the component.

        Args:
            err (str): Error message string or exception instance.
        """
        self.exif_progress.setVisible(False)
        self.btn_exif_scan.setEnabled(True)
        self.lbl_exif_status.setText(f"Error: {err}")
        QMessageBox.critical(self, "EXIF Processing Error", err)

    def _teardown_worker(self, worker):
        """Teardown finished worker.

        Manages teardown worker operations and coordinates related state changes for the component.

        Args:
            worker: The worker parameter.
        """
        self.remove_worker_thread(worker)
        worker.deleteLater()
