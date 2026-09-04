"""Uninstalled Software Residual Hunter Page.

Integrates analyzers.residual_cleaner.ResidualCleaner:
- Searches AppData, LocalAppData, ProgramData, and ProgramFiles for leftover
  folders and configuration directories belonging to uninstalled software
- Uses tokenized fuzzy matching with strict system directory exclusion to avoid false positives
- Displays leftover folder paths, sizes, and provides one-click clean up to Recycle Bin
"""

from __future__ import annotations

import os
from pathlib import Path
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
from .widgets import Card, title_block
from .window import _Page, fmt_bytes


class _ResidualScanWorker(QObject):
    """Residualscanworker.

    Manages ResidualScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)  # list of dicts
    failed = Signal(str)

    def __init__(self, query: str):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            query (str): The query parameter.
        """
        super().__init__()
        self._query = query

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.analyzers.residual_cleaner import ResidualCleaner
            cleaner = ResidualCleaner()
            if self._query.strip():
                # Specific app scan
                results = cleaner.scan_for_app(self._query.strip())
            else:
                # General leftover scan across common uninstalled keywords
                results = []
                common_checks = [
                    "zoom", "skype", "slack", "discord", "teamviewer", "anydesk",
                    "utorrent", "bittorrent", "vlc", "spotify", "epic games", "origin",
                    "battle.net", "steam", "blender", "gimp", "audacity", "handbrake"
                ]
                for kw in common_checks:
                    found = cleaner.scan_for_app(kw)
                    for item in found:
                        if not any(existing["path"] == item["path"] for existing in results):
                            results.append(item)
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ResidualCleanerPage(_Page):
    """Residualcleanerpage.

    Manages ResidualCleanerPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Uninstalled Software Residual Hunter",
            "When software is uninstalled, Windows standard uninstallers routinely leave behind "
            "gigabytes of user data, cache files, and logs in AppData and ProgramData. "
            "Residual Hunter identifies and purges these orphaned folders safely.",
        ))

        # Search / Control Card
        search_card = Card(self.p)
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(16, 12, 16, 12)
        search_layout.setSpacing(10)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter uninstalled app name (e.g. Zoom, Slack, Steam, Norton) or leave blank for common scan...")
        self._input.returnPressed.connect(self._scan)
        search_layout.addWidget(self._input, 1)

        self._scan_btn = QPushButton("Hunt Leftovers")
        self._scan_btn.setObjectName("Primary")
        self._scan_btn.clicked.connect(self._scan)
        search_layout.addWidget(self._scan_btn)

        self.v.addWidget(search_card)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        # Residuals Table
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Residual Directory Path", "Location Category", "Size", "Safety"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        # Bottom Actions Row
        action_row = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(self.tbl.selectAll)
        action_row.addWidget(self._select_all_btn)

        self._clean_btn = QPushButton("Purge Selected Leftovers")
        self._clean_btn.setObjectName("Warning")
        self._clean_btn.clicked.connect(self._clean_selected)
        action_row.addWidget(self._clean_btn)

        action_row.addStretch(1)
        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("Muted")
        action_row.addWidget(self._summary_lbl)

        self.v.addLayout(action_row)

        # Initial hunt
        self._scan()

    def _scan(self):
        """Scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        query = self._input.text().strip()
        self._scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(f"Hunting leftover directories in AppData & ProgramData...")
        w = _ResidualScanWorker(query)
        self.win.run_worker(w, self._on_done, self._fail)

    def _on_done(self, results: list):
        """On done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            results (list): Dictionary or data object holding operation results.
        """
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self.tbl.setRowCount(len(results))

        total_bytes = 0
        for r, item in enumerate(results):
            path_str = str(item.get("path", ""))
            size_b = int(item.get("size", 0))
            total_bytes += size_b

            item_path = QTableWidgetItem(path_str)
            item_path.setData(Qt.ItemDataRole.UserRole, path_str)
            self.tbl.setItem(r, 0, item_path)

            category = "LocalAppData" if "local" in path_str.lower() else ("Roaming" if "roaming" in path_str.lower() else "ProgramData")
            self.tbl.setItem(r, 1, QTableWidgetItem(category))
            self.tbl.setItem(r, 2, QTableWidgetItem(fmt_bytes(size_b)))
            self.tbl.setItem(r, 3, QTableWidgetItem("Safe (Orphaned)"))

        if not results:
            self.state.show_empty("No orphaned residual directories found for this application.")
            self._summary_lbl.setText("0 leftovers found")
            self.win.statusBar().showMessage("No residuals found", 5000)
        else:
            self.state.clear()
            summary = f"Found {len(results)} residual folders occupying {fmt_bytes(total_bytes)}"
            self._summary_lbl.setText(summary)
            self.win.statusBar().showMessage(summary, 6000)

    def _clean_selected(self):
        """Clean selected.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
        """
        sel = self.tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "No Selection", "Please select one or more residual folders to purge.")
            return

        paths = [self.tbl.item(idx.row(), 0).data(Qt.ItemDataRole.UserRole) for idx in sel]
        ans = QMessageBox.question(
            self,
            "Purge Leftovers",
            f"Are you sure you want to move {len(paths)} leftover folder(s) to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        from cortex_unified.engine.secure_delete import recycle_path
        purged = 0
        for p in paths:
            try:
                recycle_path(Path(p))
                purged += 1
            except Exception:
                pass

        self.win.statusBar().showMessage(f"Moved {purged} residual folder(s) to Recycle Bin", 6000)
        self._scan()

    def _fail(self, err: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            err (str): Error message string or exception instance.
        """
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self.state.show_error(f"Hunter error: {err}")
        self.win.statusBar().showMessage(f"Error: {err}", 6000)
