"""Delivery Optimization (WUDO) Peer Cache Cleaner Page.

Integrates system_tools.delivery_optimization_cleaner.DeliveryOptimizationCleaner:
- Scans Windows Delivery Optimization peer distribution caches in
  %WinDir%\\SoftwareDistribution\\DeliveryOptimization and ProgramData
- Displays reclaimable cache size and file count
- Purges stale peer download chunks safely
"""

from __future__ import annotations

import sys
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, status_note, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = sys.platform == "win32"


class _DeliveryScanWorker(QObject):
    """Deliveryscanworker.

    Manages DeliveryScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)  # DeliveryOptimizationStatus
    failed = Signal(str)

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.delivery_optimization_cleaner import (
                DeliveryOptimizationCleaner,
            )
            status = DeliveryOptimizationCleaner.get_status()
            self.finished.emit(status)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _DeliveryCleanWorker(QObject):
    """Deliverycleanworker.

    Manages DeliveryCleanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)  # DeliveryOptimizationCleanReport
    failed = Signal(str)

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.delivery_optimization_cleaner import (
                DeliveryOptimizationCleaner,
            )
            report = DeliveryOptimizationCleaner.clean_cache()
            self.finished.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DeliveryOptimizationPage(_Page):
    """Deliveryoptimizationpage.

    Manages DeliveryOptimizationPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Delivery Optimization (WUDO) Cache",
            "Scans and purges the Windows Delivery Optimization peer cache. "
            "Windows Update downloads update chunks and stores them locally to "
            "share with other PCs on your local network or the Internet. Over "
            "time, this cache can occupy tens of gigabytes of hidden disk space.",
        ))

        if not IS_WINDOWS:
            self.v.addWidget(status_note(
                self.p, "info", "Delivery Optimization is a Windows-specific OS subsystem."))
            return

        self._status = None

        # Main Info Card
        self._card = Card(self.p)
        card_v = QVBoxLayout(self._card)
        card_v.setContentsMargins(20, 18, 20, 18)
        card_v.setSpacing(14)

        self._size_headline = QLabel("0 B Reclaimable")
        self._size_headline.setStyleSheet("font-size: 26px; font-weight: 700;")
        card_v.addWidget(self._size_headline)

        self._desc_label = QLabel("Analyzing Delivery Optimization cache stores...")
        self._desc_label.setObjectName("Muted")
        card_v.addWidget(self._desc_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        card_v.addWidget(self.progress)

        btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("Scan Peer Cache")
        self._scan_btn.clicked.connect(self._scan)
        btn_row.addWidget(self._scan_btn)

        self._clean_btn = QPushButton("Purge Cache Files")
        self._clean_btn.setObjectName("Primary")
        self._clean_btn.setEnabled(False)
        self._clean_btn.clicked.connect(self._confirm_clean)
        btn_row.addWidget(self._clean_btn)

        btn_row.addStretch(1)
        card_v.addLayout(btn_row)

        self.v.addWidget(self._card)

        # Technical Details Card
        tech_card = Card(self.p)
        tech_v = QVBoxLayout(tech_card)
        tech_v.setContentsMargins(20, 16, 20, 16)
        tech_v.setSpacing(8)

        tech_title = QLabel("Subsystem & Storage Architecture")
        tech_title.setStyleSheet("font-weight: 600; font-size: 14px;")
        tech_v.addWidget(tech_title)

        self._path_label = QLabel("Primary Cache Path: %WinDir%\\SoftwareDistribution\\DeliveryOptimization")
        self._path_label.setObjectName("Muted")
        tech_v.addWidget(self._path_label)

        self._service_label = QLabel("Service: Delivery Optimization Service (DoSvc)")
        self._service_label.setObjectName("Muted")
        tech_v.addWidget(self._service_label)

        self.v.addWidget(tech_card)

        self.state = StatePanel(self.p)
        self.v.addWidget(self.state, 1)

        # Initial scan
        self._scan()

    def _scan(self):
        """Scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        self._scan_btn.setEnabled(False)
        self._clean_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Calculating Delivery Optimization peer cache size...")
        w = _DeliveryScanWorker()
        self.win.run_worker(w, self._on_scan_done, self._fail)

    def _on_scan_done(self, status):
        """On scan done.

        Receives the completed data from the scan background worker, populates the view with results, and restores button states.

        Args:
            status: The status parameter.
        """
        self._status = status
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)

        self._size_headline.setText(fmt_bytes(status.size_bytes))
        self._desc_label.setText(
            f"Found {status.file_count:,} cached update chunks across peer distribution folders."
        )
        self._path_label.setText(f"Cache Location: {status.cache_path}")

        if status.size_bytes > 0:
            self._clean_btn.setEnabled(True)
            self.state.clear()
            self.win.statusBar().showMessage(
                f"Delivery Optimization: {fmt_bytes(status.size_bytes)} in {status.file_count} files", 6000
            )
        else:
            self._clean_btn.setEnabled(False)
            self.state.show_empty("Delivery Optimization peer cache is clean! No leftover update chunks.")
            self.win.statusBar().showMessage("Delivery Optimization cache is empty", 5000)

    def _confirm_clean(self):
        """Confirm clean.

        Manages confirm clean operations and coordinates related state changes for the component.
        """
        if not self._status or self._status.size_bytes == 0:
            return
        ans = QMessageBox.question(
            self,
            "Purge Delivery Optimization Cache",
            f"Are you sure you want to purge {fmt_bytes(self._status.size_bytes)} ({self._status.file_count} files) "
            "from the Delivery Optimization peer cache?\n\n"
            "This will not affect installed Windows updates; it only removes cached peer distribution files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._clean()

    def _clean(self):
        """Clean.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
        """
        self._scan_btn.setEnabled(False)
        self._clean_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Purging Delivery Optimization cache files...")
        w = _DeliveryCleanWorker()
        self.win.run_worker(w, self._on_clean_done, self._fail)

    def _on_clean_done(self, report):
        """On clean done.

        Receives the completed data from the clean background worker, populates the view with results, and restores button states.

        Args:
            report: The generated report data object from the backend.
        """
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        freed = fmt_bytes(report.bytes_freed)
        self._size_headline.setText("0 B Reclaimable")
        self._desc_label.setText(f"Cleaned {report.files_deleted} files, freed {freed}.")
        self.state.show_empty(f"Successfully purged {freed} of Delivery Optimization peer cache!")
        self.win.statusBar().showMessage(f"Purged {freed} Delivery Optimization cache", 7000)

    def _fail(self, err: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            err (str): Error message string or exception instance.
        """
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self.state.show_error(f"Scan/Clean error: {err}")
        self.win.statusBar().showMessage(f"Error: {err}", 6000)
