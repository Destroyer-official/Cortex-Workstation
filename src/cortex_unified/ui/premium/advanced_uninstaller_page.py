"""Advanced Uninstaller — multi-source app removal with forced uninstall and leftover scanning.

Research: BCUninstaller, Revo Uninstaller Pro, Geek Uninstaller, Uninstalr (2026 benchmark winner).
Detects apps from Registry, Steam, Chocolatey, Winget, Scoop, Store, Portable, Windows Features.
Forced uninstall removes traces when uninstaller is missing/corrupted. Leftover scan covers
files, registry, services, tasks, startup, drivers, context menu, browser extensions.
"""

from __future__ import annotations

import os
import threading

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .widgets import title_block
from .window import _Page
from .states import StatePanel
from cortex_unified.analyzers.advanced_uninstaller import (
    AdvancedUninstaller,
    AppInfo,
    UninstallResult,
)


class _UninstallWorker(QObject):
    """Uninstallworker.

    Manages UninstallWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        app_ids: list[str],
        force: bool,
        scan_leftovers: bool,
        max_leftovers_mb: int,
        sources: list[str],
    ):
        """Initialize worker.

        Initializes the instance and configures internal state.

        Args:
            app_ids (list[str]): The app ids parameter.
            force (bool): The force parameter.
            scan_leftovers (bool): The scan leftovers parameter.
            max_leftovers_mb (int): The max leftovers mb parameter.
            sources (list[str]): The sources parameter.
        """
        super().__init__()
        self._app_ids = app_ids
        self._force = force
        self._scan_leftovers = scan_leftovers
        self._max_leftovers_mb = max_leftovers_mb
        self._sources = sources
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
            uninstaller = AdvancedUninstaller(
                create_restore_point=True,
                progress_callback=lambda msg, *_: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )
            # Enumerate first (respects source filters implicitly by returning all)
            apps = uninstaller.enumerate_all()
            # Filter by selected sources
            if self._sources:
                apps = [a for a in apps if a.source in self._sources]

            # Filter by app_ids if specific ones were selected
            if self._app_ids:
                app_map = {a.id: a for a in apps}
                targets = [app_map[aid] for aid in self._app_ids if aid in app_map]
            else:
                targets = apps

            # Run batch uninstall
            results = uninstaller.uninstall_batch(
                [a.id for a in targets],
                force=self._force,
                scan_leftovers=self._scan_leftovers,
            )

            # Filter results by leftover size if threshold set
            filtered = []
            for r in results:
                if r.leftovers.total_size_mb <= self._max_leftovers_mb:
                    filtered.append(r)
                else:
                    # Emit progress for oversized leftovers
                    self.progress.emit(
                        f"Skipped {r.app_id}: leftovers {r.leftovers.total_size_mb:.1f} MB > limit"
                    )

            self.finished.emit(filtered)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class AdvancedUninstallerPage(_Page):
    """Advanceduninstallerpage.

    Manages AdvancedUninstallerPage operations and coordinates related state changes for the component.
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
                "Advanced Uninstaller",
                "Enumerate apps from Registry, Steam, Chocolatey, Winget, Scoop, Store, "
                "Portable, and Windows Features. Forced uninstall removes traces when the "
                "uninstaller is missing or corrupted. Leftover scan covers files, registry, "
                "services, tasks, startup, drivers, context menu, and browser extensions.",
            )
        )

        # ── Root folder picker ──────────────────────────────────────────────
        root_card = QWidget()
        root_card.setObjectName("Card")
        root_lay = QVBoxLayout(root_card)
        root_lay.setContentsMargins(16, 12, 16, 12)
        root_lay.setSpacing(10)

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Root…")
        pick_btn.setObjectName("Ghost")
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        default_root = os.environ.get("ProgramFiles", "C:\\Program Files")
        self.root_label = QLabel(default_root)
        self.root_label.setObjectName("Muted")
        pick_btn.clicked.connect(self._pick_root)
        picker.addWidget(pick_btn)
        picker.addWidget(self.root_label, 1)
        root_lay.addLayout(picker)

        # ── Source checkboxes ───────────────────────────────────────────────
        sources_lay = QHBoxLayout()
        sources_lay.setSpacing(8)
        sources_lay.addWidget(QLabel("Sources:"))
        self.source_checks: dict[str, QCheckBox] = {}
        for src in (
            "registry",
            "steam",
            "chocolatey",
            "winget",
            "scoop",
            "store",
            "portable",
            "windows_feature",
        ):
            cb = QCheckBox(src.title())
            cb.setChecked(True)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            self.source_checks[src] = cb
            sources_lay.addWidget(cb)
        sources_lay.addStretch(1)
        root_lay.addLayout(sources_lay)

        # ── Options row ─────────────────────────────────────────────────────
        opts = QHBoxLayout()
        opts.setSpacing(12)
        opts.addWidget(QLabel("Max leftovers (MB):"))
        self.max_leftovers_spin = QSpinBox()
        self.max_leftovers_spin.setRange(0, 10000)
        self.max_leftovers_spin.setValue(50)
        self.max_leftovers_spin.setToolTip(
            "Skip apps whose leftover scan exceeds this size"
        )
        opts.addWidget(self.max_leftovers_spin)

        self.force_check = QCheckBox("Force uninstall if uninstaller missing")
        self.force_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.force_check.setToolTip(
            "DANGEROUS: Deletes install directory, registry keys, services, and tasks "
            "when no valid uninstaller exists. Requires explicit confirmation."
        )
        opts.addWidget(self.force_check)
        opts.addStretch(1)
        root_lay.addLayout(opts)

        self.v.addWidget(root_card)

        # ── Progress + status ───────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        # ── Results table ───────────────────────────────────────────────────
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["App Name", "Version", "Source", "Status", "Leftovers (MB)"]
        )
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSortingEnabled(True)
        self.v.addWidget(self.tbl, 1)

        # ── State panel ─────────────────────────────────────────────────────
        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        # ── Action row ──────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 8, 0, 0)
        self.scan_btn = QPushButton("Enumerate Apps")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.clicked.connect(self._scan)
        action_row.addWidget(self.scan_btn)
        action_row.addStretch(1)
        self.uninstall_btn = QPushButton("Uninstall Selected")
        self.uninstall_btn.setObjectName("Primary")
        self.uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uninstall_btn.setEnabled(False)
        self.uninstall_btn.clicked.connect(self._confirm_uninstall)
        action_row.addWidget(self.uninstall_btn)
        self.v.addLayout(action_row)

        self._root = default_root
        self._worker = None
        self._apps: list[AppInfo] = []
        self._results: list[UninstallResult] = []

    def _pick_root(self):
        """_pick_root.

        Manages pick root operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Select root folder", self._root
        )
        if folder:
            self._root = folder
            self.root_label.setText(folder)
            self.root_label.setObjectName("")

    def _scan(self):
        """_scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Enumerating applications…")
        self.status.setText(f"Scanning {self._root}…")
        self.tbl.setRowCount(0)
        self._apps = []
        self._results = []

        # Build worker with current options
        sources = [src for src, cb in self.source_checks.items() if cb.isChecked()]
        w = _UninstallWorker(
            app_ids=[],  # Empty = all apps from selected sources
            force=self.force_check.isChecked(),
            scan_leftovers=True,
            max_leftovers_mb=self.max_leftovers_spin.value(),
            sources=sources,
        )
        self._worker = w
        self.win.run_worker(
            w, self._on_scan_done, self._on_fail, on_progress=self._on_progress
        )

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.status.setText(msg)

    def _on_scan_done(self, apps: list[AppInfo]):
        """_on_scan_done.

        Receives the completed data from the scan background worker, populates the view with results, and restores button states.

        Args:
            apps (list[AppInfo]): The apps parameter.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        if not apps:
            self.state.show_empty(
                "No applications found. Try selecting different sources or a different root folder."
            )
            self.status.setText("No apps found.")
            self.win.statusBar().showMessage("No applications found", 5000)
            return
        self._apps = apps
        self.state.clear()
        self.tbl.setRowCount(len(apps))
        for r, app in enumerate(apps):
            self.tbl.setItem(r, 0, QTableWidgetItem(app.name))
            self.tbl.setItem(r, 1, QTableWidgetItem(app.version))
            self.tbl.setItem(r, 2, QTableWidgetItem(app.source))
            self.tbl.setItem(r, 3, QTableWidgetItem("Ready"))
            self.tbl.setItem(r, 4, QTableWidgetItem("—"))
            # Store app_id in row data for later lookup
            self.tbl.item(r, 0).setData(Qt.ItemDataRole.UserRole, app.id)
        self.uninstall_btn.setEnabled(True)
        self.status.setText(f"Found {len(apps)} applications from selected sources.")
        self.win.statusBar().showMessage(f"Found {len(apps)} applications", 5000)

    def _confirm_uninstall(self):
        """_confirm_uninstall.

        Manages confirm uninstall operations and coordinates related state changes for the component.
        """
        selected = self._selected_apps()
        if not selected:
            QMessageBox.information(
                self, "No selection", "Select one or more apps to uninstall."
            )
            return

        force = self.force_check.isChecked()
        if force:
            # Extra explicit confirmation for forced uninstall
            reply = QMessageBox.warning(
                self,
                "⚠ FORCED UNINSTALL — EXPLICIT CONFIRMATION REQUIRED",
                "You are about to perform a FORCED UNINSTALL.\n\n"
                "This will:\n"
                "• Kill any running processes for the selected apps\n"
                "• Delete the install directory (if not a protected system path)\n"
                "• Remove registry keys, services, and scheduled tasks\n"
                "• Scan for and report leftovers\n\n"
                "THIS IS DESTRUCTIVE AND CANNOT BE UNDONE.\n\n"
                "A system restore point WILL be created before proceeding.\n\n"
                "Type 'FORCE' in the box below to confirm you understand the risks.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            # Additional text input confirmation
            from PySide6.QtWidgets import QInputDialog

            text, ok = QInputDialog.getText(
                self,
                "Confirm Forced Uninstall",
                "Type 'FORCE' to proceed:",
                text="",
            )
            if not ok or text.strip() != "FORCE":
                return

        # Standard confirmation for normal uninstall
        names = ", ".join(a.name for a in selected[:5])
        if len(selected) > 5:
            names += f" and {len(selected) - 5} more"
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Uninstall {len(selected)} selected application(s)?\n\n"
            f"{names}\n\n"
            f"Force uninstall: {'YES' if force else 'NO'}\n"
            f"Scan leftovers: YES\n"
            f"Max leftovers: {self.max_leftovers_spin.value()} MB\n\n"
            "A system restore point will be created.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._run_uninstall(selected)

    def _run_uninstall(self, apps: list[AppInfo]):
        """_run_uninstall.

        Manages run uninstall operations and coordinates related state changes for the component.

        Args:
            apps (list[AppInfo]): The apps parameter.
        """
        self.scan_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(f"Uninstalling {len(apps)} app(s)…")
        self.status.setText("Starting uninstall…")
        self.tbl.setRowCount(0)

        sources = [src for src, cb in self.source_checks.items() if cb.isChecked()]
        w = _UninstallWorker(
            app_ids=[a.id for a in apps],
            force=self.force_check.isChecked(),
            scan_leftovers=True,
            max_leftovers_mb=self.max_leftovers_spin.value(),
            sources=sources,
        )
        self._worker = w
        self.win.run_worker(
            w, self._on_uninstall_done, self._on_fail, on_progress=self._on_progress
        )

    def _on_uninstall_done(self, results: list[UninstallResult]):
        """_on_uninstall_done.

        Receives the completed data from the uninstall background worker, populates the view with results, and restores button states.

        Args:
            results (list[UninstallResult]): Dictionary or data object holding operation results.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.uninstall_btn.setEnabled(True)
        self._results = results

        if not results:
            self.state.show_empty("No apps were uninstalled (all skipped or failed).")
            self.status.setText("No apps uninstalled.")
            self.win.statusBar().showMessage("No apps uninstalled", 5000)
            return

        self.state.clear()
        self.tbl.setRowCount(len(results))
        success = 0
        failed = 0
        total_leftovers = 0.0
        for r, res in enumerate(results):
            # Find original app info
            app = next((a for a in self._apps if a.id == res.app_id), None)
            name = app.name if app else res.app_id
            version = app.version if app else ""
            source = app.source if app else ""

            self.tbl.setItem(r, 0, QTableWidgetItem(name))
            self.tbl.setItem(r, 1, QTableWidgetItem(version))
            self.tbl.setItem(r, 2, QTableWidgetItem(source))
            status = "Success" if res.success else "Failed"
            self.tbl.setItem(r, 3, QTableWidgetItem(status))
            leftovers_str = f"{res.leftovers.total_size_mb:.1f}"
            self.tbl.setItem(r, 4, QTableWidgetItem(leftovers_str))

            if res.success:
                success += 1
            else:
                failed += 1
            total_leftovers += res.leftovers.total_size_mb

        self.status.setText(
            f"Uninstalled {success} app(s), {failed} failed. Total leftovers: {total_leftovers:.1f} MB"
        )
        msg = (
            f"Uninstall complete: {success} succeeded, {failed} failed.\n"
            f"Total leftovers detected: {total_leftovers:.1f} MB\n"
            f"Restore point created: {'Yes' if results[0].restore_point else 'No'}"
        )
        self.win.statusBar().showMessage(f"Uninstalled {success} app(s)", 5000)
        QMessageBox.information(self, "Uninstall Complete", msg)

    def _on_fail(self, msg: str):
        """_on_fail.

        Captures worker error messages, presents diagnostic feedback to the user, and resets interactive controls for retry.

        Args:
            msg (str): Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.uninstall_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)
        self.win._default_fail(msg)

    def _selected_apps(self) -> list[AppInfo]:
        """_selected_apps.

        Manages selected apps operations and coordinates related state changes for the component.

        Returns:
            list[AppInfo]: List of processed items or identifiers.
        """
        rows = {idx.row() for idx in self.tbl.selectedIndexes()}
        out = []
        for r in sorted(rows):
            item = self.tbl.item(r, 0)
            if item:
                app_id = item.data(Qt.ItemDataRole.UserRole)
                if app_id:
                    app = next((a for a in self._apps if a.id == app_id), None)
                    if app:
                        out.append(app)
        return out

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._on_fail(msg)
