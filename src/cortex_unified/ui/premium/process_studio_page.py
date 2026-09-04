"""Advanced Process & Threat Studio Page.

Integrates system_tools.process_analyzer.ProcessAnalyzer:
- Enumerate running Windows NT processes with deep memory and CPU consumption
- Filter by memory footprint or keyword search
- Terminate misbehaving or hung tasks safely
- Display session ID, window titles, user privileges, and status
"""

from __future__ import annotations

import sys
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, status_note, title_block
from .window import _Page

IS_WINDOWS = sys.platform == "win32"


class _ProcessScanWorker(QObject):
    """Processscanworker.

    Manages ProcessScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.process_analyzer import ProcessAnalyzer
            analyzer = ProcessAnalyzer()
            procs = analyzer.list_processes()
            self.finished.emit(procs)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ProcessStudioPage(_Page):
    """Processstudiopage.

    Manages ProcessStudioPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Advanced Process & Threat Studio",
            "Real-time Windows process inspection. Details memory allocation, CPU time, "
            "security session ownership, and associated top-level windows. "
            "Allows safe process termination with protected system process guarding.",
        ))

        self._all_procs = []

        # Top Control Card
        bar_card = Card(self.p)
        bar_layout = QHBoxLayout(bar_card)
        bar_layout.setContentsMargins(16, 12, 16, 12)
        bar_layout.setSpacing(10)

        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Filter processes by name, PID, or user...")
        self._filter_input.textChanged.connect(self._apply_filter)
        bar_layout.addWidget(self._filter_input, 1)

        self._refresh_btn = QPushButton("Refresh Processes")
        self._refresh_btn.clicked.connect(self._scan)
        bar_layout.addWidget(self._refresh_btn)

        self._kill_btn = QPushButton("End Selected Task")
        self._kill_btn.setObjectName("Warning")
        self._kill_btn.clicked.connect(self._kill_selected)
        bar_layout.addWidget(self._kill_btn)

        self.v.addWidget(bar_card)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        # Process Table
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels([
            "PID", "Image Name", "Memory Usage", "User Account", "CPU Time", "Window Title"
        ])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("Muted")
        self.v.addWidget(self._summary_lbl)

        # Initial scan
        self._scan()

    def _scan(self):
        """Scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        self._refresh_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Enumerating running tasks and memory sets...")
        w = _ProcessScanWorker()
        self.win.run_worker(w, self._on_done, self._fail)

    def _on_done(self, procs: list):
        """On done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            procs (list): The procs parameter.
        """
        self.progress.setVisible(False)
        self._refresh_btn.setEnabled(True)
        self._all_procs = procs
        self._apply_filter()

    def _apply_filter(self):
        """Apply filter.

        Manages apply filter operations and coordinates related state changes for the component.
        """
        query = self._filter_input.text().strip().lower()
        if not query:
            filtered = self._all_procs
        else:
            filtered = [
                p for p in self._all_procs
                if query in str(p.get("pid", "")).lower()
                or query in str(p.get("name", "")).lower()
                or query in str(p.get("username", "")).lower()
                or query in str(p.get("window_title", "")).lower()
            ]

        self.tbl.setRowCount(len(filtered))
        for r, p in enumerate(filtered):
            pid_str = str(p.get("pid", ""))
            pid_item = QTableWidgetItem(pid_str)
            pid_item.setData(Qt.ItemDataRole.UserRole, pid_str)
            self.tbl.setItem(r, 0, pid_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(str(p.get("name", ""))))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(p.get("mem_usage", ""))))
            self.tbl.setItem(r, 3, QTableWidgetItem(str(p.get("username", ""))))
            self.tbl.setItem(r, 4, QTableWidgetItem(str(p.get("cpu_time", ""))))
            self.tbl.setItem(r, 5, QTableWidgetItem(str(p.get("window_title", ""))))

        if not filtered:
            self.state.show_empty("No matching processes found.")
        else:
            self.state.clear()

        self._summary_lbl.setText(f"Showing {len(filtered)} of {len(self._all_procs)} active processes")

    def _kill_selected(self):
        """Kill selected.

        Manages kill selected operations and coordinates related state changes for the component.
        """
        sel = self.tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Select Process", "Please select a process from the list to end.")
            return

        pid_str = self.tbl.item(sel[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        name_str = self.tbl.item(sel[0].row(), 1).text()

        # OS protection check
        protected = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "explorer.exe"}
        if name_str.lower() in protected:
            QMessageBox.critical(
                self, "Action Denied",
                f"Cannot terminate protected Windows OS component '{name_str}'. "
                "Terminating this process would cause an immediate Blue Screen of Death (BSOD)."
            )
            return

        ans = QMessageBox.question(
            self, "End Task",
            f"Are you sure you want to terminate '{name_str}' (PID: {pid_str})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        from cortex_unified.core.proc import kill_process_tree
        try:
            kill_process_tree(int(pid_str))
            self.win.statusBar().showMessage(f"Terminated process {name_str} (PID: {pid_str})", 5000)
            self._scan()
        except Exception as exc:
            QMessageBox.warning(self, "Termination Error", f"Could not terminate process: {exc}")

    def _fail(self, err: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            err (str): Error message string or exception instance.
        """
        self.progress.setVisible(False)
        self._refresh_btn.setEnabled(True)
        self.state.show_error(f"Process query error: {err}")
        self.win.statusBar().showMessage(f"Error: {err}", 6000)
