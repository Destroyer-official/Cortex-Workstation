"""Windows BAM/DAM & SRUM Forensic Privacy Studio Page.

Forensic UI studio allowing inspection and sanitization of Windows Background Activity Moderator
(BAM/DAM) execution traces and System Resource Usage Monitor (SRUM) database.
"""

from __future__ import annotations

import sys
from typing import List, Optional

from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.system_tools.srum_bam_cleaner import (
    BamExecutionEntry,
    SrumBamCleaner,
    SrumBamReport,
)
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page, fmt_bytes


class _SrumBamWorker(QObject):
    """_SrumBamWorker class."""
    finished = Signal(object)
    clean_finished = Signal(int)

    def __init__(self, cleaner: SrumBamCleaner, entries: Optional[List[BamExecutionEntry]] = None) -> None:
        """__init__."""
        super().__init__()
        self.cleaner = cleaner
        self.entries = entries

    def run_scan(self) -> None:
        """run_scan."""
        report = self.cleaner.scan()
        self.finished.emit(report)

    def run_clean(self) -> None:
        """run_clean."""
        count = self.cleaner.clean_bam_entries(self.entries)
        self.clean_finished.emit(count)


class SrumBamCleanerPage(_Page):
    """UI page for BAM/DAM execution traces and SRUM metrics."""

    def __init__(self, win) -> None:
        """__init__."""
        super().__init__(win)
        self.cleaner = SrumBamCleaner()
        self.current_report: Optional[SrumBamReport] = None
        self._thread: Optional[QThread] = None

        hdr = title_block(
            "Windows Execution & SRUM Forensics",
            "Audit and sanitize Windows BAM/DAM execution timestamps and SRUDB resource database metrics.",
        )
        self.v.addWidget(hdr)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_bam = StatCard(self.p, "Execution Traces", "0")
        self.stat_bam_records = self.stat_bam  # alias for tests
        self.stat_srum_size = StatCard(self.p, "SRUM Database", "0 B")
        self.stat_srum_state = StatCard(self.p, "SRUM Lock State", "Unknown")
        stats_row.addWidget(self.stat_bam)
        stats_row.addWidget(self.stat_srum_size)
        stats_row.addWidget(self.stat_srum_state)
        self.v.addLayout(stats_row)

        ctrl_card = Card(self.p)
        ctrl_lay = QHBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(14, 10, 14, 10)

        self.btn_scan = QPushButton("Inspect Execution Traces")
        self.btn_scan.setObjectName("AccentButton")
        self.btn_scan.clicked.connect(self._start_scan)
        ctrl_lay.addWidget(self.btn_scan)

        self.btn_clean = QPushButton("Sanitize BAM Execution History")
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self._start_clean)
        ctrl_lay.addWidget(self.btn_clean)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # indeterminate
        ctrl_lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready.")
        ctrl_lay.addWidget(self.lbl_status)
        ctrl_lay.addStretch()

        self.v.addWidget(ctrl_card)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Executable Path", "Last Execution Time (UTC)", "User SID", "Subsystem"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.add_scrolling_list(self.table, stretch=1)

    def _start_scan(self) -> None:
        """_start_scan."""
        self.btn_scan.setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Reading BAM/DAM registry hives & SRUDB...")

        self._thread = QThread()
        self._worker = _SrumBamWorker(self.cleaner)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_scan)
        self._worker.finished.connect(self._on_scan_finished)
        self._thread.start()

    def _on_scan_finished(self, report: SrumBamReport) -> None:
        """_on_scan_finished."""
        self.current_report = report
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.btn_clean.setEnabled(len(report.bam_entries) > 0)

        self.stat_bam.set_value(str(len(report.bam_entries)))
        if report.srum_info:
            self.stat_srum_size.set_value(fmt_bytes(report.srum_info.size_bytes))
            self.stat_srum_state.set_value("Exclusively Locked" if report.srum_info.is_locked_by_system else "Accessible")

        self.lbl_status.setText(f"Found {len(report.bam_entries)} execution trace records.")

        self.table.setRowCount(len(report.bam_entries))
        for row, entry in enumerate(report.bam_entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.path))
            self.table.setItem(row, 1, QTableWidgetItem(entry.last_run_timestamp))
            self.table.setItem(row, 2, QTableWidgetItem(entry.user_sid))
            self.table.setItem(row, 3, QTableWidgetItem(entry.source.upper()))

    def _start_clean(self) -> None:
        """_start_clean."""
        if not self.current_report or not self.current_report.bam_entries:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm BAM Sanitization",
            f"Are you sure you want to sanitize {len(self.current_report.bam_entries)} execution records from the registry?\n\n"
            "This removes application launch timestamps logged by Windows.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.btn_scan.setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Sanitizing BAM/DAM registry values...")

        self._thread = QThread()
        self._worker = _SrumBamWorker(self.cleaner, self.current_report.bam_entries)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_clean)
        self._worker.clean_finished.connect(self._on_clean_finished)
        self._thread.start()

    def _on_clean_finished(self, cleaned_count: int) -> None:
        """_on_clean_finished."""
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText(f"Successfully sanitized {cleaned_count} BAM registry entries.")
        self.table.setRowCount(0)
        self.stat_bam.set_value("0")
        QMessageBox.information(
            self,
            "BAM Sanitization Complete",
            f"Successfully cleared {cleaned_count} forensic execution records from the registry.",
        )
