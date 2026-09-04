"""NTFS Master File Table ($MFT) & Directory Index Slack Scrubber Page.

Forensic UI studio for analyzing and sanitizing unallocated MFT resident record slack
and directory index allocation ($INDEX_ALLOCATION) buffers.
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.system_tools.mft_slack_scrubber import (
    MftScrubReport,
    MftSlackScrubber,
    NtfsMftGeometry,
)
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page, fmt_bytes


class _MftScrubWorker(QObject):
    """Mftscrubworker.

    Manages MftScrubWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)
    scrub_finished = Signal(object)

    def __init__(self, scrubber: MftSlackScrubber) -> None:
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            scrubber (MftSlackScrubber): The scrubber parameter.
        """
        super().__init__()
        self.scrubber = scrubber

    def run_audit(self) -> None:
        """run_audit.

        Manages run audit operations and coordinates related state changes for the component.
        """
        rep = self.scrubber.audit()
        self.finished.emit(rep)

    def run_scrub(self) -> None:
        """run_scrub.

        Manages run scrub operations and coordinates related state changes for the component.
        """
        rep = self.scrubber.scrub()
        self.scrub_finished.emit(rep)


class MftSlackScrubberPage(_Page):
    """Mftslackscrubberpage.

    Manages MftSlackScrubberPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win) -> None:
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.current_volume = "C:"
        self.scrubber = MftSlackScrubber(self.current_volume)
        self.current_report: Optional[MftScrubReport] = None
        self._thread: Optional[QThread] = None

        hdr = title_block(
            "NTFS Master File Table ($MFT) Slack Scrubber",
            "Detect and sanitize resident filename and data fragments lingering in deleted NTFS MFT records.",
        )
        self.v.addWidget(hdr)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_total_records = StatCard(self.p, "MFT Records", "0")
        self.stat_free_records = StatCard(self.p, "Unallocated Records", "0")
        self.stat_slack_bytes = StatCard(self.p, "Estimated MFT Slack", "0 B")
        stats_row.addWidget(self.stat_total_records)
        stats_row.addWidget(self.stat_free_records)
        stats_row.addWidget(self.stat_slack_bytes)
        self.v.addLayout(stats_row)

        ctrl_card = Card(self.p)
        ctrl_lay = QHBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(14, 10, 14, 10)

        ctrl_lay.addWidget(QLabel("Select Volume:"))
        self.cmb_volume = QComboBox()
        self.cmb_volume.addItems(["C:", "D:", "E:", "F:"])
        self.cmb_volume.currentTextChanged.connect(self._on_volume_changed)
        ctrl_lay.addWidget(self.cmb_volume)

        self.btn_audit = QPushButton("Analyze MFT Geometry")
        self.btn_audit.setObjectName("AccentButton")
        self.btn_audit.clicked.connect(self._start_audit)
        ctrl_lay.addWidget(self.btn_audit)

        self.btn_scrub = QPushButton("Sanitize MFT Record Slack")
        self.btn_scrub.setEnabled(False)
        self.btn_scrub.clicked.connect(self._start_scrub)
        ctrl_lay.addWidget(self.btn_scrub)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        ctrl_lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready.")
        ctrl_lay.addWidget(self.lbl_status)
        ctrl_lay.addStretch()

        self.v.addWidget(ctrl_card)

        # Geometry Card
        geom_card = Card(self.p)
        geom_lay = QVBoxLayout(geom_card)
        geom_lay.setContentsMargins(16, 16, 16, 16)
        geom_lay.addWidget(QLabel("<b>NTFS Volume & MFT Allocation Specifications:</b>"))

        form = QFormLayout()
        self.lbl_cluster_size = QLabel("4,096 bytes")
        self.lbl_sector_size = QLabel("512 bytes")
        self.lbl_record_size = QLabel("1,024 bytes (Standard NTFS)")
        self.lbl_mft_size = QLabel("0 MB")
        self.lbl_zone_clusters = QLabel("0 clusters")

        form.addRow("Bytes Per Cluster:", self.lbl_cluster_size)
        form.addRow("Bytes Per Sector:", self.lbl_sector_size)
        form.addRow("File Record Segment Size:", self.lbl_record_size)
        form.addRow("MFT Total Valid Data Length:", self.lbl_mft_size)
        form.addRow("MFT Reserved Zone Size:", self.lbl_zone_clusters)
        geom_lay.addLayout(form)

        self.v.addWidget(geom_card)

        self.note = status_note(
            self.p,
            "info",
            "Forensic Note: In NTFS, files smaller than ~700 bytes reside entirely inside the MFT record ($DATA resident). "
            "Deleting the file marks the record as inactive, but the raw text and timestamps remain indefinitely.",
        )
        self.v.addWidget(self.note)

    def _on_volume_changed(self, vol: str) -> None:
        """_on_volume_changed.

        Manages on volume changed operations and coordinates related state changes for the component.

        Args:
            vol (str): The vol parameter.
        """
        self.current_volume = vol
        self.scrubber = MftSlackScrubber(vol)
        self.stat_total_records.set_value("0")
        self.stat_free_records.set_value("0")
        self.stat_slack_bytes.set_value("0 B")
        self.btn_scrub.setEnabled(False)

    def _start_audit(self) -> None:
        """_start_audit.

        Manages start audit operations and coordinates related state changes for the component.
        """
        self.btn_audit.setEnabled(False)
        self.btn_scrub.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText(f"Querying NTFS geometry for {self.current_volume}...")

        self._thread = QThread()
        self._worker = _MftScrubWorker(self.scrubber)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_audit)
        self._worker.finished.connect(self._on_audit_finished)
        self._thread.start()

    def _on_audit_finished(self, report: MftScrubReport) -> None:
        """_on_audit_finished.

        Manages on audit finished operations and coordinates related state changes for the component.

        Args:
            report (MftScrubReport): The generated report data object from the backend.
        """
        self.current_report = report
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_audit.setEnabled(True)
        self.btn_scrub.setEnabled(report.is_ntfs)

        if report.geometry:
            g = report.geometry
            self.stat_total_records.set_value(f"{g.estimated_mft_records:,}")
            self.stat_free_records.set_value(f"{g.estimated_free_mft_records:,}")
            self.stat_slack_bytes.set_value(fmt_bytes(report.slack_bytes_estimated))

            self.lbl_cluster_size.setText(f"{g.bytes_per_cluster:,} bytes")
            self.lbl_sector_size.setText(f"{g.bytes_per_sector:,} bytes")
            self.lbl_record_size.setText(f"{g.bytes_per_file_record_segment:,} bytes")
            self.lbl_mft_size.setText(fmt_bytes(g.mft_valid_data_length))
            self.lbl_zone_clusters.setText(f"{g.mft_zone_clusters:,} clusters")

        self.lbl_status.setText(f"Audit complete for {self.current_volume}.")

    def _start_scrub(self) -> None:
        """_start_scrub.

        Manages start scrub operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self,
            "Confirm MFT Slack Sanitization",
            f"Sanitize unallocated MFT record slack on volume {self.current_volume}?\n\n"
            "This overwrites orphaned resident filename fragments without affecting live data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.btn_audit.setEnabled(False)
        self.btn_scrub.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText(f"Sanitizing MFT slack on {self.current_volume}...")

        self._thread = QThread()
        self._worker = _MftScrubWorker(self.scrubber)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_scrub)
        self._worker.scrub_finished.connect(self._on_scrub_finished)
        self._thread.start()

    def _on_scrub_finished(self, report: MftScrubReport) -> None:
        """_on_scrub_finished.

        Manages on scrub finished operations and coordinates related state changes for the component.

        Args:
            report (MftScrubReport): The generated report data object from the backend.
        """
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_audit.setEnabled(True)
        self.btn_scrub.setEnabled(True)
        self.lbl_status.setText(f"MFT slack sanitized for {self.current_volume}.")

        QMessageBox.information(
            self,
            "Sanitization Complete",
            f"Successfully compacted and sanitized MFT records on {self.current_volume}.\n"
            f"Scrubbed approximately {report.scrubbed_records_count:,} unallocated records.",
        )
