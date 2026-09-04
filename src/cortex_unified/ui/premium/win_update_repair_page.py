"""Windows Update Repair page — comprehensive component reset and repair.

Phase-based repair of Windows Update components: stop services, clear caches,
reset registry policies, re-register DLLs, reset network stack, run DISM,
run SFC, and clean component store. Includes preflight diagnostics and
selective phase execution.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
)

from .widgets import Card, status_note, title_block
from .states import StatePanel
from .window import _Page, fmt_bytes

# ---------------------------------------------------------------------------
#  Repair worker
# ---------------------------------------------------------------------------


class _RepairWorker(QObject):
    """Repairworker.

    Manages RepairWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, phases: list[str]):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            phases (list[str]): The phases parameter.
        """
        super().__init__()
        self._phases = phases
        self._cancel = threading.Event()

    def cancel(self):
        """cancel.

        Sets the internal cancellation event to cooperatively stop worker execution at the next safe boundary.
        """
        self._cancel.set()

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.windows_update_repair import (
                WindowsUpdateRepair,
            )

            repair = WindowsUpdateRepair(
                create_restore_point=True,
                progress_callback=lambda msg: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )
            result = repair.repair_all(phases=self._phases)
            self.finished.emit(
                {
                    "summary": result.summary(),
                    "cancelled": result.cancelled,
                    "phases": [
                        {
                            "phase": p.phase,
                            "success": p.success,
                            "changes": p.changes,
                            "error": p.error,
                            "duration": f"{p.duration_seconds:.1f}s",
                        }
                        for p in result.phases
                    ],
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
#  Preflight worker
# ---------------------------------------------------------------------------


class _PreflightWorker(QObject):
    """Preflightworker.

    Manages PreflightWorker operations and coordinates related state changes for the component.
    """

    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.windows_update_repair import (
                WindowsUpdateRepair,
            )

            repair = WindowsUpdateRepair(create_restore_point=False)
            report = repair.preflight()
            self.finished.emit(
                {
                    "os_version": report.os_version,
                    "services": report.services,
                    "disk_free_gb": report.disk_free_gb,
                    "connectivity": report.connectivity,
                    "dism_health": report.dism_health,
                    "pending_reboot": report.pending_reboot,
                    "recent_wu_errors": report.recent_wu_errors,
                    "issues": report.issues,
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
#  Phase definitions
# ---------------------------------------------------------------------------

_PHASES = [
    ("stop_services", "Stop WU Services"),
    ("clear_caches", "Clear Caches"),
    ("reset_registry_policies", "Reset Registry"),
    ("reregister_dlls", "Re-register DLLs"),
    ("reset_network", "Reset Network"),
    ("dism_repair", "DISM Repair"),
    ("sfc", "SFC Scan"),
    ("component_store", "Component Store"),
]


# ---------------------------------------------------------------------------
#  Page
# ---------------------------------------------------------------------------


class WinUpdateRepairPage(_Page):
    """Winupdaterepairpage.

    Manages WinUpdateRepairPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(
            title_block(
                "Update Repair",
                "Comprehensive Windows Update component reset: stop services, clear "
                "caches, reset policies, re-register DLLs, fix network stack, run "
                "DISM/SFC, and clean the component store. Requires Administrator.",
            )
        )

        # -- Warning banner --
        warn = status_note(
            self.p,
            "warning",
            "This tool requires Administrator privileges and may trigger a "
            "reboot. A System Restore point is created before any changes.",
        )
        self.v.addWidget(warn)

        # -- Preflight card --
        self._preflight_card = Card(self.p, "Preflight Diagnostics")
        pf_layout = QVBoxLayout(self._preflight_card)
        pf_layout.setSpacing(8)

        self._svc_label = QLabel("Services: \u2014")
        self._svc_label.setWordWrap(True)
        self._disk_label = QLabel("Disk: \u2014")
        self._net_label = QLabel("Network: \u2014")
        self._dism_label = QLabel("DISM: \u2014")
        self._reboot_label = QLabel("Pending reboot: \u2014")
        self._errors_label = QLabel("Recent errors: \u2014")
        self._errors_label.setWordWrap(True)
        self._errors_label.setObjectName("Muted")

        for lbl in (
            self._svc_label,
            self._disk_label,
            self._net_label,
            self._dism_label,
            self._reboot_label,
            self._errors_label,
        ):
            pf_layout.addWidget(lbl)

        self._pf_btn = QPushButton("Run Preflight")
        self._pf_btn.setObjectName("Ghost")
        self._pf_btn.clicked.connect(self._run_preflight)
        pf_layout.addWidget(self._pf_btn)
        self.v.addWidget(self._preflight_card)

        # -- Phase selection card --
        self._phase_card = Card(self.p, "Repair Phases")
        phase_layout = QVBoxLayout(self._phase_card)
        phase_layout.setSpacing(6)

        self._checkboxes: dict[str, QCheckBox] = {}
        for key, label in _PHASES:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self._checkboxes[key] = cb
            phase_layout.addWidget(cb)

        self.v.addWidget(self._phase_card)

        # -- Action buttons --
        btn_row = QHBoxLayout()
        self._run_btn = QPushButton("Run Repair")
        self._run_btn.setObjectName("Primary")
        self._run_btn.clicked.connect(self._run_repair)
        btn_row.addWidget(self._run_btn)
        btn_row.addStretch(1)
        self.v.addLayout(btn_row)

        # -- Progress bar --
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self.v.addWidget(self._progress)

        # -- Status label --
        self._status = QLabel("")
        self._status.setObjectName("Muted")
        self.v.addWidget(self._status)

        # -- Results table --
        self._tbl = QTableWidget(0, 4)
        self._tbl.setHorizontalHeaderLabels(["Phase", "Status", "Duration", "Details"])
        self._tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self._tbl)
        self._tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tbl.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tbl.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tbl.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.v.addWidget(self._tbl, 1)

        # -- State panel --
        self._state = StatePanel(self.p)
        self._state.bind_content(self._tbl)
        self.v.addWidget(self._state, 1)

        self._worker = None
        self._pf_worker = None

    # -- Preflight --

    def _run_preflight(self):
        """_run_preflight.

        Manages run preflight operations and coordinates related state changes for the component.
        """
        self._pf_btn.setEnabled(False)
        self._state.show_loading("Running preflight diagnostics\u2026")
        self.win.statusBar().showMessage("Running preflight diagnostics\u2026")
        w = _PreflightWorker()
        self._pf_worker = w
        self.win.run_worker(w, self._pf_done, self._pf_fail)

    def _pf_done(self, data: dict):
        """Handle completion of the pf asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

        Args:
            data (dict): The data parameter.
        """
        self._pf_worker = None
        self._pf_btn.setEnabled(True)
        self._state.clear()

        services = data.get("services", {})
        svc_parts = [f"{s}: {st}" for s, st in services.items()]
        self._svc_label.setText(
            "Services: " + (", ".join(svc_parts) if svc_parts else "\u2014")
        )

        disk_gb = data.get("disk_free_gb", 0.0)
        self._disk_label.setText(f"Disk free: {disk_gb:.1f} GB")

        conn = data.get("connectivity", False)
        self._net_label.setText(
            "Network: " + ("Connected" if conn else "No connectivity")
        )

        dism = data.get("dism_health", "\u2014")
        self._dism_label.setText(f"DISM: {dism}")

        pending = data.get("pending_reboot", False)
        self._reboot_label.setText("Pending reboot: " + ("Yes" if pending else "No"))

        errors = data.get("recent_wu_errors", [])
        if errors:
            self._errors_label.setText("Recent errors:\n" + "\n".join(errors[:5]))
        else:
            self._errors_label.setText("Recent errors: None")

        issues = data.get("issues", [])
        self._status.setText(f"Preflight complete. {len(issues)} issue(s) found.")
        self.win.statusBar().showMessage(f"Preflight: {len(issues)} issue(s)", 5000)

    def _pf_fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._pf_worker = None
        self._pf_btn.setEnabled(True)
        self._state.show_error(msg, on_retry=self._run_preflight)

    # -- Repair --

    def _run_repair(self):
        """_run_repair.

        Manages run repair operations and coordinates related state changes for the component.
        """
        phases = [k for k, cb in self._checkboxes.items() if cb.isChecked()]
        if not phases:
            QMessageBox.information(
                self, "No phases", "Select at least one repair phase."
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Repair",
            f"Run {len(phases)} repair phase(s)?\n\n"
            "A System Restore point will be created first. This may take "
            "several minutes and a reboot may be required.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._run_btn.setEnabled(False)
        self._pf_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._tbl.setRowCount(0)
        self._state.show_loading("Running repair phases\u2026")
        self._status.setText(f"Running {len(phases)} phase(s)\u2026")
        self.win.statusBar().showMessage("Running Windows Update repair\u2026")

        w = _RepairWorker(phases)
        self._worker = w
        self.win.run_worker(
            w, self._on_done, self._on_fail, on_progress=self._on_progress
        )

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self._status.setText(msg)

    def _on_done(self, data: dict):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            data (dict): The data parameter.
        """
        self._worker = None
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._pf_btn.setEnabled(True)
        self._state.clear()

        phases = data.get("phases", [])
        self._tbl.setRowCount(len(phases))
        for r, p in enumerate(phases):
            phase_item = QTableWidgetItem(p["phase"].replace("_", " ").title())
            status_item = QTableWidgetItem("OK" if p["success"] else "FAILED")
            if not p["success"]:
                from PySide6.QtGui import QColor

                status_item.setForeground(QColor("#EF4444"))
            detail = p.get("error") or ", ".join(p.get("changes", []))
            self._tbl.setItem(r, 0, phase_item)
            self._tbl.setItem(r, 1, status_item)
            self._tbl.setItem(r, 2, QTableWidgetItem(p.get("duration", "\u2014")))
            self._tbl.setItem(r, 3, QTableWidgetItem(detail[:300]))

        ok = sum(1 for p in phases if p["success"])
        total = len(phases)
        summary = data.get("summary", "")
        self._status.setText(f"{summary}  ({ok}/{total} phases succeeded)")
        self.win.statusBar().showMessage(summary, 8000)

        if data.get("cancelled"):
            self._status.setText(self._status.text() + "  [Cancelled]")

    def _on_fail(self, msg: str):
        """_on_fail.

        Captures worker error messages, presents diagnostic feedback to the user, and resets interactive controls for retry.

        Args:
            msg (str): Informational or progress status message.
        """
        self._worker = None
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._pf_btn.setEnabled(True)
        self._state.show_error(msg, on_retry=self._run_repair)
