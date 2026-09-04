"""Portable App Manager page — scan, track, and update portable apps.

Research grounding
------------------
* PortableApps.com: standardized portable app format with appinfo.ini manifests.
* LiberKey: 294 portable apps with auto-update and sync with online catalog.
* HowToGeek (2026): Ventoy + exFAT toolkit, Sysinternals Suite, HWInfo64,
  CrystalDiskInfo, Malwarebytes, 7-Zip, VS Code, Everything, live ISOs.

This page scans configurable roots for portable apps (PAF format, LiberKey,
and heuristic exe-based detection), checks for updates via declared UpdateURL
in appinfo.ini, and provides update actions.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .widgets import title_block
from .window import _Page
from .states import StatePanel
from cortex_unified.analyzers.portable_manager import PortableManager


class _PortableWorker(QObject):
    """Portableworker.

    Manages PortableWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, roots: list[str], target_apps: list[str] | None = None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            roots (list[str]): The roots parameter.
            target_apps (list[str] | None): The target apps parameter.
        """
        super().__init__()
        self._roots = [Path(r) for r in roots]
        self._target_apps = target_apps
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
            mgr = PortableManager(
                progress=lambda msg: self.progress.emit(str(msg)),
                cancel=self._cancel,
            )
            apps = mgr.scan_portable_roots(roots=self._roots if self._roots else None)
            if self._target_apps:
                apps = [
                    a
                    for a in apps
                    if a.name.lower() in [t.lower() for t in self._target_apps]
                ]
            mgr.check_updates(apps)
            self.finished.emit(apps)
        except Exception as exc:
            self.failed.emit(str(exc))


class _UpdateWorker(QObject):
    """Updateworker.

    Manages UpdateWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, apps: list):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            apps (list): The apps parameter.
        """
        super().__init__()
        self._apps = apps
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
            mgr = PortableManager(
                progress=lambda msg: self.progress.emit(str(msg)),
                cancel=self._cancel,
            )
            for app in self._apps:
                if self._cancel.is_set():
                    break
                self.progress.emit(f"Updating {app.name}…")
                mgr.update_app(app)
            self.finished.emit(self._apps)
        except Exception as exc:
            self.failed.emit(str(exc))


_TARGET_APPS = [
    "Sysinternals",
    "Everything",
    "7-Zip",
    "Process Explorer",
    "ProcMon",
    "Wireshark",
]


class PortableManagerPage(_Page):
    """Portablemanagerpage.

    Manages PortableManagerPage operations and coordinates related state changes for the component.
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
                "Portable App Manager",
                "Scan for portable apps (PAF format, LiberKey, exe-based), "
                "check for updates via declared UpdateURL, and manage your toolkit.",
            )
        )

        card = QWidget()
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(8)

        roots_row = QHBoxLayout()
        roots_row.setSpacing(6)
        roots_row.addWidget(QLabel("Scan Roots:"))
        self.roots_entry = QLineEdit()
        self.roots_entry.setPlaceholderText(
            "Auto-detect (removable drives, PortableApps, LiberKey)"
        )
        self.roots_entry.setToolTip(
            "Comma-separated paths to scan. Leave empty for auto-detection."
        )
        self.add_root_btn = QPushButton("Add Root")
        self.add_root_btn.clicked.connect(self._add_root)
        roots_row.addWidget(self.roots_entry, 1)
        roots_row.addWidget(self.add_root_btn)
        card_lay.addLayout(roots_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_row.addWidget(QLabel("Target Apps:"))
        self.app_combo = QComboBox()
        self.app_combo.addItem("All Portable Apps")
        for app in _TARGET_APPS:
            self.app_combo.addItem(app)
        self.app_combo.setToolTip("Filter scan results to specific apps")
        filter_row.addWidget(self.app_combo, 1)

        self.auto_update_cb = QCheckBox("Auto-update on scan")
        self.auto_update_cb.setToolTip(
            "Automatically update apps when updates are found"
        )
        filter_row.addWidget(self.auto_update_cb)

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self._run)
        filter_row.addWidget(self.scan_btn)
        card_lay.addLayout(filter_row)

        self.v.addWidget(card)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["App Name", "Version", "Installed", "Latest", "Update Available"]
        )
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._worker = None

    def _add_root(self):
        """_add_root.

        Manages add root operations and coordinates related state changes for the component.
        """
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Select portable app root")
        if folder:
            current = self.roots_entry.text().strip()
            if current:
                self.roots_entry.setText(f"{current}, {folder}")
            else:
                self.roots_entry.setText(folder)

    def _parse_roots(self) -> list[str]:
        """_parse_roots.

        Manages parse roots operations and coordinates related state changes for the component.

        Returns:
            list[str]: List of processed items or identifiers.
        """
        text = self.roots_entry.text().strip()
        if not text:
            return []
        return [r.strip() for r in text.split(",") if r.strip()]

    def _get_target_apps(self) -> list[str] | None:
        """_get_target_apps.

        Manages get target apps operations and coordinates related state changes for the component.

        Returns:
            list[str] | None: List of processed items or identifiers.
        """
        idx = self.app_combo.currentIndex()
        if idx == 0:
            return None
        return [_TARGET_APPS[idx - 1]]

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Scanning for portable apps…")
        self.status.setText("Scanning…")
        self.tbl.setRowCount(0)

        roots = self._parse_roots()
        target = self._get_target_apps()

        w = _PortableWorker(roots, target_apps=target)
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.status.setText(msg)

    def _on_done(self, apps: list):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            apps (list): The apps parameter.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

        if not apps:
            self.state.show_empty(
                "No portable apps found. Add scan roots or check that "
                "portable apps are installed in detected locations."
            )
            self.status.setText("No portable apps found.")
            self.win.statusBar().showMessage("No portable apps found", 5000)
            return

        self.state.clear()
        self.tbl.setRowCount(len(apps))
        for r, app in enumerate(apps):
            self.tbl.setItem(r, 0, QTableWidgetItem(app.name))
            self.tbl.setItem(r, 1, QTableWidgetItem(app.version or "—"))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(app.path)))
            self.tbl.setItem(r, 3, QTableWidgetItem(app.latest_version or "—"))

            update_item = QTableWidgetItem("Yes" if app.update_available else "No")
            if app.update_available:
                update_item.setForeground(self.palette().highlight())
            self.tbl.setItem(r, 4, update_item)

        updates_available = sum(1 for a in apps if a.update_available)
        self.status.setText(
            f"{len(apps)} portable apps found, {updates_available} updates available"
        )
        self.win.statusBar().showMessage(
            f"{len(apps)} portable apps, {updates_available} updates", 5000
        )

        if self.auto_update_cb.isChecked() and updates_available:
            self._auto_update(apps)

    def _auto_update(self, apps: list):
        """_auto_update.

        Manages auto update operations and coordinates related state changes for the component.

        Args:
            apps (list): The apps parameter.
        """
        from PySide6.QtWidgets import QMessageBox

        to_update = [a for a in apps if a.update_available]
        if not to_update:
            return

        reply = QMessageBox.question(
            self,
            "Auto-Update",
            f"Found {len(to_update)} app(s) with updates available.\n\n"
            "Do you want to update them now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.status.setText(f"Updating {len(to_update)} apps…")
            self.progress.setVisible(True)
            self.scan_btn.setEnabled(False)
            w = _UpdateWorker(to_update)
            self._worker = w
            self.win.run_worker(
                w,
                self._on_update_done,
                self._on_update_fail,
                on_progress=self._on_progress,
            )

    def _on_update_done(self, result):
        """_on_update_done.

        Receives the completed data from the update background worker, populates the view with results, and restores button states.

        Args:
            result: Dictionary or data object holding operation results.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.status.setText(f"Updated {len(result)} apps")
        self.win.statusBar().showMessage(f"Updated {len(result)} apps", 5000)
        self._run()

    def _on_update_fail(self, msg):
        """_on_update_fail.

        Captures worker error messages, presents diagnostic feedback to the user, and resets interactive controls for retry.

        Args:
            msg: Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.status.setText(f"Update failed: {msg}")

    def _fail(self, msg):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg: Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)
