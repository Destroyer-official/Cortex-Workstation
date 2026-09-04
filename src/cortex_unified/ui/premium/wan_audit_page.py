"""WAN & UPnP IGD Security Auditor Page.

Integrates system_tools.wan_audit.WanAuditor:
- Read-only, local-only SSDP router discovery and UPnP IGD gateway audit
- Classifies external IP (globally routable public vs CGNAT vs RFC1918 private)
- Enumerates all active router port mappings (external port -> internal client)
- Audits network security posture with warnings and export support
"""

from __future__ import annotations

import json
import threading
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, title_block
from .window import _Page


class _WanAuditWorker(QObject):
    """Wanauditworker.

    Manages WanAuditWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)  # WanStatus
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self):
        """Initialize the instance and configure internal state.

        Sets up sub-widgets, event signal connections, and default options.
        """
        super().__init__()
        self._cancel = threading.Event()

    def cancel(self):
        """Cancel.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.wan_audit import WanAuditor
            auditor = WanAuditor()
            status = auditor.audit(
                include_upnp=True,
                cancel_event=self._cancel,
                progress=self.progress.emit,
            )
            self.finished.emit(status)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WanAuditPage(_Page):
    """Wanauditpage.

    Manages WanAuditPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "WAN & UPnP Gateway Auditor",
            "Discovers Internet Gateway Devices (IGD) on your local network using SSDP/UPnP. "
            "Inspects your router's external WAN interface, classifications (Public vs CGNAT), "
            "and lists active port forwarding mappings. Completely read-only and local: "
            "never contacts external internet servers.",
        ))

        self._last_status = None

        # Summary Header Card
        self._card = Card(self.p)
        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(18, 14, 18, 14)

        v_summary = QVBoxLayout()
        self._ext_ip_label = QLabel("External IP: Detecting...")
        self._ext_ip_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        v_summary.addWidget(self._ext_ip_label)

        self._class_label = QLabel("Classification: Detecting...")
        self._class_label.setObjectName("Muted")
        v_summary.addWidget(self._class_label)
        card_layout.addLayout(v_summary, 1)

        self._scan_btn = QPushButton("Audit Gateway")
        self._scan_btn.setObjectName("Primary")
        self._scan_btn.clicked.connect(self._scan)
        card_layout.addWidget(self._scan_btn)

        self._export_btn = QPushButton("Export Report")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export)
        card_layout.addWidget(self._export_btn)

        self.v.addWidget(self._card)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self._status_text = QLabel("")
        self._status_text.setObjectName("Muted")
        self.v.addWidget(self._status_text)

        # Port Mappings Table
        table_hdr = QLabel("Active Router Port Mappings (UPnP IGD)")
        table_hdr.setStyleSheet("font-weight: 600; font-size: 14px; margin-top: 6px;")
        self.v.addWidget(table_hdr)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels([
            "External Port", "Protocol", "Internal Client", "Internal Port", "Description", "Status"
        ])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        # Initial audit
        self._scan()

    def _scan(self):
        """Scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        self._scan_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Probing local gateway via SSDP and UPnP...")
        w = _WanAuditWorker()
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """On progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self._status_text.setText(msg)

    def _on_done(self, status):
        """On done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            status: The status parameter.
        """
        self._last_status = status
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        self._status_text.setText(f"Audit completed in {status.duration_seconds:.2f}s")

        ip = status.external_ip or "Not Reported"
        classification = status.external_ip_classification.upper().replace("_", " ")
        self._ext_ip_label.setText(f"External IP: {ip}")
        self._class_label.setText(
            f"Classification: {classification}  |  Gateway: {status.gateway or 'Auto'}  |  IGD Found: {'Yes' if status.igd_found else 'No'}"
        )

        mappings = status.port_mappings
        self.tbl.setRowCount(len(mappings))

        for r, m in enumerate(mappings):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(m.external_port)))
            self.tbl.setItem(r, 1, QTableWidgetItem(m.protocol))
            self.tbl.setItem(r, 2, QTableWidgetItem(m.internal_client))
            self.tbl.setItem(r, 3, QTableWidgetItem(str(m.internal_port)))
            self.tbl.setItem(r, 4, QTableWidgetItem(m.description or "N/A"))
            self.tbl.setItem(r, 5, QTableWidgetItem("Active" if m.enabled else "Disabled"))

        if not mappings:
            if not status.igd_found:
                self.state.show_empty("No UPnP IGD router discovered on local subnets (UPnP may be disabled on router).")
            else:
                self.state.show_empty("Gateway discovered! No active external port mappings found (secure posture).")
        else:
            self.state.clear()

        self.win.statusBar().showMessage(
            f"WAN Audit: {len(mappings)} port mappings on {status.gateway or 'gateway'}", 6000
        )

    def _export(self):
        """Export.

        Manages export operations and coordinates related state changes for the component.
        """
        if not self._last_status:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export WAN Audit Report", "wan_audit_report.json", "JSON Files (*.json)")
        if path:
            report_data = {
                "external_ip": self._last_status.external_ip,
                "classification": self._last_status.external_ip_classification,
                "gateway": self._last_status.gateway,
                "igd_found": self._last_status.igd_found,
                "port_mappings": [m.to_dict() for m in self._last_status.port_mappings],
                "warnings": self._last_status.warnings,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
            self.win.statusBar().showMessage(f"Exported audit report to {path}", 5000)

    def _fail(self, err: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            err (str): Error message string or exception instance.
        """
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self.state.show_error(f"Audit error: {err}")
        self.win.statusBar().showMessage(f"Error: {err}", 6000)
