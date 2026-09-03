"""Windows 11 DirectStorage & BypassIO Hardware Acceleration Page.

Displays real-time BypassIO readiness across all physical and logical volumes,
flags blocking filter drivers, and provides optimization recommendations for GPU decompression.
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.system_tools.directstorage_optimizer import (
    DirectStorageAuditReport,
    DirectStorageOptimizer,
)
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page


class _DirectStorageWorker(QObject):
    """_DirectStorageWorker class."""
    finished = Signal(object)

    def __init__(self, optimizer: DirectStorageOptimizer) -> None:
        """__init__."""
        super().__init__()
        self.optimizer = optimizer

    def run_audit(self) -> None:
        """run_audit."""
        report = self.optimizer.audit()
        self.finished.emit(report)


class DirectStorageOptimizerPage(_Page):
    """UI diagnostics page for DirectStorage BypassIO hardware acceleration."""

    def __init__(self, win) -> None:
        """__init__."""
        super().__init__(win)
        self.optimizer = DirectStorageOptimizer()
        self.current_report: Optional[DirectStorageAuditReport] = None
        self._thread: Optional[QThread] = None

        hdr = title_block(
            "DirectStorage & BypassIO Diagnostics",
            "Audit Windows 11 high-throughput BypassIO NVMe-to-GPU memory acceleration and filter drivers.",
        )
        self.v.addWidget(hdr)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_volumes = StatCard(self.p, "Total Volumes", "0")
        self.stat_ready = StatCard(self.p, "DirectStorage Ready", "0")
        self.stat_status = self.stat_ready  # alias for tests
        self.stat_os = StatCard(self.p, "OS Capability", "Supported" if sys.platform == "win32" else "N/A")
        stats_row.addWidget(self.stat_volumes)
        stats_row.addWidget(self.stat_ready)
        stats_row.addWidget(self.stat_os)
        self.v.addLayout(stats_row)

        ctrl_card = Card(self.p)
        ctrl_lay = QHBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(14, 10, 14, 10)

        self.btn_audit = QPushButton("Run BypassIO Diagnostics")
        self.btn_audit.setObjectName("AccentButton")
        self.btn_audit.clicked.connect(self._start_audit)
        ctrl_lay.addWidget(self.btn_audit)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        ctrl_lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready.")
        ctrl_lay.addWidget(self.lbl_status)
        ctrl_lay.addStretch()

        self.v.addWidget(ctrl_card)

        # Table for volumes
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Drive", "BypassIO State", "Media Type", "Storage Driver", "Blocking Minifilters"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.add_scrolling_list(self.table, stretch=1)

        # Recommendations panel
        rec_card = Card(self.p)
        rec_lay = QVBoxLayout(rec_card)
        rec_lay.setContentsMargins(14, 14, 14, 14)
        rec_lay.addWidget(QLabel("<b>Optimization Guidance & Driver Diagnostics:</b>"))
        self.txt_recommendations = QTextEdit()
        self.txt_recommendations.setReadOnly(True)
        self.txt_recommendations.setMaximumHeight(120)
        rec_lay.addWidget(self.txt_recommendations)
        self.v.addWidget(rec_card)

    def _start_audit(self) -> None:
        """_start_audit."""
        self.btn_audit.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Querying volume BypassIO states via fsutil...")

        self._thread = QThread()
        self._worker = _DirectStorageWorker(self.optimizer)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_audit)
        self._worker.finished.connect(self._on_audit_finished)
        self._thread.start()

    def _on_audit_finished(self, report: DirectStorageAuditReport) -> None:
        """_on_audit_finished."""
        self.current_report = report
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_audit.setEnabled(True)

        self.stat_volumes.set_value(str(report.total_volumes))
        self.stat_ready.set_value(str(report.directstorage_ready_volumes))
        self.lbl_status.setText(f"Audit completed. {report.directstorage_ready_volumes} volume(s) ready.")

        self.table.setRowCount(len(report.volumes))
        for row, v in enumerate(report.volumes):
            self.table.setItem(row, 0, QTableWidgetItem(v.volume_letter))
            status_item = QTableWidgetItem("Ready (Active)" if v.is_supported else f"Blocked: {v.status_reason}")
            self.table.setItem(row, 1, status_item)
            self.table.setItem(row, 2, QTableWidgetItem(v.storage_type))
            self.table.setItem(row, 3, QTableWidgetItem(v.driver_name))
            filters_str = ", ".join(v.blocking_minifilters) if v.blocking_minifilters else "None (Optimal)"
            self.table.setItem(row, 4, QTableWidgetItem(filters_str))

        rec_text = "\n".join(f"• {r}" for r in report.recommendations) if report.recommendations else "All systems optimal."
        self.txt_recommendations.setPlainText(rec_text)
