"""Winapp2 Community Declarative Application Cleaner Page.

Interactive studio for discovering and cleaning transient caches, GPU shaders,
and telemetry from 500+ third-party Windows desktop software suites.
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

from cortex_unified.system_tools.winapp2_cleaner import AppCleanTarget, Winapp2Cleaner, Winapp2Report
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page, fmt_bytes


class _Winapp2Worker(QObject):
    """_Winapp2Worker class."""
    progress = Signal(int, int, str)
    finished = Signal(object)
    clean_finished = Signal(int, int)

    def __init__(self, cleaner: Winapp2Cleaner, targets: Optional[List[AppCleanTarget]] = None) -> None:
        """__init__."""
        super().__init__()
        self.cleaner = cleaner
        self.targets = targets

    def run_scan(self) -> None:
        """run_scan."""
        report = self.cleaner.scan(progress_cb=lambda cur, tot, name: self.progress.emit(cur, tot, name))
        self.finished.emit(report)

    def run_clean(self) -> None:
        """run_clean."""
        b, count = self.cleaner.clean(
            self.targets,
            dry_run=False,
            progress_cb=lambda cur, tot, name: self.progress.emit(cur, tot, name),
        )
        self.clean_finished.emit(b, count)


class Winapp2CleanerPage(_Page):
    """UI page for Winapp2 community third-party application cleaning."""

    def __init__(self, win) -> None:
        """__init__."""
        super().__init__(win)
        self.cleaner = Winapp2Cleaner()
        self.current_report: Optional[Winapp2Report] = None
        self._thread: Optional[QThread] = None

        # Header block
        hdr = title_block(
            "Community App Cleaner (Winapp2)",
            "Declarative deep cleaner for 500+ desktop applications, gaming platforms, and dev tools.",
        )
        self.v.addWidget(hdr)

        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_rules = StatCard(self.p, "Rules Loaded", str(len(self.cleaner.rules)))
        self.stat_detected = StatCard(self.p, "Installed Apps", "0")
        self.stat_apps = self.stat_detected  # alias for tests
        self.stat_reclaimable = StatCard(self.p, "Reclaimable Space", "0 B")
        stats_row.addWidget(self.stat_rules)
        stats_row.addWidget(self.stat_detected)
        stats_row.addWidget(self.stat_reclaimable)
        self.v.addLayout(stats_row)

        # Action controls card
        ctrl_card = Card(self.p)
        ctrl_lay = QHBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(14, 10, 14, 10)

        self.btn_scan = QPushButton("Scan Installed Applications")
        self.btn_scan.setObjectName("AccentButton")
        self.btn_scan.clicked.connect(self._start_scan)
        ctrl_lay.addWidget(self.btn_scan)

        self.btn_clean = QPushButton("Clean Selected Caches")
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self._start_clean)
        ctrl_lay.addWidget(self.btn_clean)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        ctrl_lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready.")
        ctrl_lay.addWidget(self.lbl_status)
        ctrl_lay.addStretch()

        self.v.addWidget(ctrl_card)

        # Application target table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Application / Rule", "Category", "Target Cache Path", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.add_scrolling_list(self.table, stretch=1)

    def _start_scan(self) -> None:
        """_start_scan."""
        self.btn_scan.setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Scanning application definitions...")

        self._thread = QThread()
        self._worker = _Winapp2Worker(self.cleaner)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_scan)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._thread.start()

    def _on_progress(self, current: int, total: int, name: str) -> None:
        """_on_progress."""
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))
        self.lbl_status.setText(f"Checking: {name[:40]}...")

    def _on_scan_finished(self, report: Winapp2Report) -> None:
        """_on_scan_finished."""
        self.current_report = report
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.btn_clean.setEnabled(len(report.targets) > 0)
        self.stat_detected.set_value(str(report.installed_apps_count))
        self.stat_reclaimable.set_value(fmt_bytes(report.total_bytes))
        self.lbl_status.setText(f"Found {len(report.targets)} cleanable targets.")

        self.table.setRowCount(len(report.targets))
        for row, tgt in enumerate(report.targets):
            self.table.setItem(row, 0, QTableWidgetItem(tgt.rule_name))
            self.table.setItem(row, 1, QTableWidgetItem(tgt.section))
            self.table.setItem(row, 2, QTableWidgetItem(tgt.target_path))
            self.table.setItem(row, 3, QTableWidgetItem(fmt_bytes(tgt.size_bytes)))

    def _start_clean(self) -> None:
        """_start_clean."""
        if not self.current_report or not self.current_report.targets:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Cleanup",
            f"Are you sure you want to clean {len(self.current_report.targets)} application cache files "
            f"({fmt_bytes(self.current_report.total_bytes)})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.btn_scan.setEnabled(False)
        self.btn_clean.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Cleaning cache items...")

        self._thread = QThread()
        self._worker = _Winapp2Worker(self.cleaner, self.current_report.targets)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_clean)
        self._worker.progress.connect(self._on_progress)
        self._worker.clean_finished.connect(self._on_clean_finished)
        self._thread.start()

    def _on_clean_finished(self, cleaned_bytes: int, cleaned_count: int) -> None:
        """_on_clean_finished."""
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText(f"Successfully cleaned {cleaned_count} items ({fmt_bytes(cleaned_bytes)}).")
        self.table.setRowCount(0)
        self.stat_reclaimable.set_value("0 B")
        QMessageBox.information(
            self,
            "Cleanup Complete",
            f"Reclaimed {fmt_bytes(cleaned_bytes)} across {cleaned_count} cache files.",
        )
