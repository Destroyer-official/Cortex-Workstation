"""Gaming Session & FPS Booster Page — one-click reversible PC optimization.

Integrates system_tools.game_mode.GameMode:
- Switches to the system's High/Ultimate Performance power scheme for the session
- Suspends (never kills) background sync and noise processes (OneDrive, Spotify, etc.)
- Fully reversible: cleanly resumes processes and restores previous power scheme on stop
"""

from __future__ import annotations

import sys
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, status_note, title_block
from .window import _Page

IS_WINDOWS = sys.platform == "win32"


class _GameModeQueryWorker(QObject):
    """Gamemodequeryworker.

    Manages GameModeQueryWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        """Run query off the UI thread.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.game_mode import GameMode
            gm = GameMode()
            preview = gm.preview()
            self.finished.emit(preview)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _GameModeActionWorker(QObject):
    """Gamemodeactionworker.

    Manages GameModeActionWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)  # BoostReport
    failed = Signal(str)

    def __init__(self, action: str, game_mode_instance=None):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            action (str): The action parameter.
            game_mode_instance: The game mode instance parameter.
        """
        super().__init__()
        self._action = action
        self._gm = game_mode_instance

    def run(self):
        """Run start or stop off UI thread.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.game_mode import GameMode
            gm = self._gm or GameMode()
            if self._action == "start":
                report = gm.start()
                self.finished.emit((gm, report))
            else:
                report = gm.stop()
                self.finished.emit((gm, report))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class GameModePage(_Page):
    """Gamemodepage.

    Manages GameModePage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Gaming Session & FPS Booster",
            "One-click, safe and fully reversible PC boost for game sessions. "
            "Temporarily switches to Ultimate Performance power plan and suspends "
            "background noise processes (sync clients, updaters). Zero data loss: "
            "all suspended processes resume cleanly when you exit.",
        ))

        if not IS_WINDOWS:
            self.v.addWidget(status_note(
                self.p, "info", "Gaming Session Booster is only available on Windows."))
            return

        self._game_mode = None
        self._is_boosted = False

        # Status & Action Card
        self._action_card = Card(self.p)
        action_layout = QHBoxLayout(self._action_card)
        action_layout.setContentsMargins(16, 14, 16, 14)

        self._status_label = QLabel("Status: Ready to boost")
        self._status_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        action_layout.addWidget(self._status_label, 1)

        self._refresh_btn = QPushButton("Refresh Status")
        self._refresh_btn.clicked.connect(self._query)
        action_layout.addWidget(self._refresh_btn)

        self._toggle_btn = QPushButton("Boost PC Now")
        self._toggle_btn.setObjectName("Primary")
        self._toggle_btn.setMinimumWidth(150)
        self._toggle_btn.clicked.connect(self._toggle_boost)
        action_layout.addWidget(self._toggle_btn)

        self.v.addWidget(self._action_card)

        # Details Header
        self._info_note = QLabel(
            "Current Power Plan: Detecting...  |  Target Boost Plan: Ultimate Performance"
        )
        self._info_note.setObjectName("Muted")
        self.v.addWidget(self._info_note)

        # Candidates Table
        cand_label = QLabel("Background Quieting Candidates (Suspended during Boost, Restored on Stop)")
        cand_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        self.v.addWidget(cand_label)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Process Name", "Category", "Safety Guarantee"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        footer_note = QLabel(
            "Protected Process Policy: Critical Windows OS components (explorer.exe, dwm.exe, "
            "svchost.exe, lsass.exe) and Cortex itself are permanently locked and cannot be suspended."
        )
        footer_note.setObjectName("Muted")
        footer_note.setWordWrap(True)
        self.v.addWidget(footer_note)

        # Initial query
        self._query()

    def _query(self):
        """Query.

        Manages query operations and coordinates related state changes for the component.
        """
        self._refresh_btn.setEnabled(False)
        self.state.show_loading("Inspecting active processes and power schemes...")
        w = _GameModeQueryWorker()
        self.win.run_worker(w, self._on_query_done, self._fail)

    def _on_query_done(self, preview: dict):
        """On query done.

        Receives the completed data from the query background worker, populates the view with results, and restores button states.

        Args:
            preview (dict): The preview parameter.
        """
        self._refresh_btn.setEnabled(True)
        power_now = preview.get("power_now") or "Balanced"
        power_to = preview.get("power_would_switch_to") or "High Performance"
        self._info_note.setText(
            f"Active Power Plan: {power_now}  |  Boost Target: {power_to}"
        )

        candidates = preview.get("would_suspend", [])
        self.tbl.setRowCount(len(candidates))

        for r, name in enumerate(candidates):
            self.tbl.setItem(r, 0, QTableWidgetItem(name))
            cat = "Cloud Sync" if any(x in name.lower() for x in ("drive", "dropbox", "cloud")) else "Background App"
            self.tbl.setItem(r, 1, QTableWidgetItem(cat))
            self.tbl.setItem(r, 2, QTableWidgetItem("Safe to Suspend & Resume"))

        if not candidates:
            self.state.show_empty("No background noise processes currently detected. System is running quiet!")
        else:
            self.state.clear()

    def _toggle_boost(self):
        """Start or stop boost.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        if not self._is_boosted:
            self._start_boost()
        else:
            self._stop_boost()

    def _start_boost(self):
        """Start boost.

        Manages start boost operations and coordinates related state changes for the component.
        """
        self._toggle_btn.setEnabled(False)
        self._status_label.setText("Status: Activating Boost Mode...")
        from cortex_unified.system_tools.game_mode import GameMode
        self._game_mode = GameMode()
        w = _GameModeActionWorker("start", self._game_mode)
        self.win.run_worker(w, self._on_boost_started, self._fail)

    def _on_boost_started(self, result):
        """On boost started.

        Manages on boost started operations and coordinates related state changes for the component.

        Args:
            result: Collection or dictionary holding operation results.
        """
        gm, report = result
        self._game_mode = gm
        self._toggle_btn.setEnabled(True)
        if report.ok:
            self._is_boosted = True
            self._toggle_btn.setText("Restore Normal Mode")
            self._toggle_btn.setObjectName("Warning")
            self._status_label.setText(
                f"Status: BOOSTED — {len(report.suspended)} processes quieted, Power: {report.power_to or 'High Perf'}"
            )
            self._status_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #10b981;")
            self.win.statusBar().showMessage(
                f"Gaming Mode Active: {len(report.suspended)} background tasks suspended", 7000
            )
        else:
            self._fail(report.message or "Failed to start boost mode")

    def _stop_boost(self):
        """Stop boost.

        Manages stop boost operations and coordinates related state changes for the component.
        """
        self._toggle_btn.setEnabled(False)
        self._status_label.setText("Status: Restoring Normal Mode...")
        w = _GameModeActionWorker("stop", self._game_mode)
        self.win.run_worker(w, self._on_boost_stopped, self._fail)

    def _on_boost_stopped(self, result):
        """On boost stopped.

        Manages on boost stopped operations and coordinates related state changes for the component.

        Args:
            result: Collection or dictionary holding operation results.
        """
        gm, report = result
        self._toggle_btn.setEnabled(True)
        self._is_boosted = False
        self._toggle_btn.setText("Boost PC Now")
        self._toggle_btn.setObjectName("Primary")
        self._status_label.setText("Status: Normal Mode Restored")
        self._status_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.win.statusBar().showMessage(
            f"Restored: {len(report.resumed)} processes resumed cleanly", 6000
        )
        self._query()

    def _fail(self, err: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            err (str): Error message string or exception instance.
        """
        self._refresh_btn.setEnabled(True)
        self._toggle_btn.setEnabled(True)
        self.state.show_error(f"Operation failed: {err}")
        self.win.statusBar().showMessage(f"Error: {err}", 6000)
