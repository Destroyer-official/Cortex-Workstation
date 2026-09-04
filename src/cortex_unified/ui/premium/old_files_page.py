"""Old & Inactive Files Finder Page.

Integrates analyzers.old_file_cleaner.OldFileCleaner:
- Discovers files untouched/unmodified for N days (30, 60, 90, 180, 365+ days)
- Returns results sorted oldest-first
- Displays file age, last modified timestamp, and size
- Allows safe selection and cleanup to Recycle Bin or permanent deletion
"""

from __future__ import annotations

import os
from pathlib import Path
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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


class _OldFilesScanWorker(QObject):
    """Oldfilesscanworker.

    Manages OldFilesScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list, dict)  # old_files list, stats dict
    failed = Signal(str)

    def __init__(self, root_path: str, min_age_days: int):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            root_path (str): Filesystem path to the target file or directory.
            min_age_days (int): The min age days parameter.
        """
        super().__init__()
        self._root = root_path
        self._age = min_age_days

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.analyzers.old_file_cleaner import OldFileCleaner
            cleaner = OldFileCleaner(root_path=self._root)
            files = cleaner.find_old_files(min_age_days=self._age)
            stats = cleaner.get_stats()
            # Convert Path objects to string tuples for Qt thread safety
            res = [(str(p), age, p.stat().st_size if p.exists() else 0) for p, age in files]
            self.finished.emit(res, stats)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class OldFilesPage(_Page):
    """Oldfilespage.

    Manages OldFilesPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Old & Inactive Files Finder",
            "Identifies files that have not been modified or accessed for extended periods "
            "(30 to 365+ days). Results surface oldest-first so you can safely identify forgotten "
            "downloads, obsolete installers, and stale project caches.",
        ))

        self._folder = str(Path.home() / "Downloads")
        self._files = []

        # Filter and Search Bar Card
        bar_card = Card(self.p)
        bar_layout = QHBoxLayout(bar_card)
        bar_layout.setContentsMargins(16, 12, 16, 12)
        bar_layout.setSpacing(10)

        pick_btn = QPushButton("Select Folder…")
        pick_btn.clicked.connect(self._pick_folder)
        bar_layout.addWidget(pick_btn)

        self._path_label = QLabel(self._folder)
        self._path_label.setObjectName("Muted")
        bar_layout.addWidget(self._path_label, 1)

        bar_layout.addWidget(QLabel("Minimum Age:"))
        self._age_combo = QComboBox()
        self._age_combo.addItem("30 Days", 30)
        self._age_combo.addItem("60 Days", 60)
        self._age_combo.addItem("90 Days (Quarter)", 90)
        self._age_combo.addItem("180 Days (Half Year)", 180)
        self._age_combo.addItem("365 Days (1 Year)", 365)
        self._age_combo.setCurrentIndex(2)  # Default 90 days
        bar_layout.addWidget(self._age_combo)

        self._scan_btn = QPushButton("Scan Old Files")
        self._scan_btn.setObjectName("Primary")
        self._scan_btn.clicked.connect(self._scan)
        bar_layout.addWidget(self._scan_btn)

        self.v.addWidget(bar_card)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        # Old Files Table
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["File Path", "Age (Days)", "Size", "Action"])
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

        self._delete_btn = QPushButton("Delete Selected (Recycle Bin)")
        self._delete_btn.setObjectName("Warning")
        self._delete_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self._delete_btn)

        action_row.addStretch(1)
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("Muted")
        action_row.addWidget(self._summary_label)

        self.v.addLayout(action_row)

        # Initial scan
        self._scan()

    def _pick_folder(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Target Folder", self._folder)
        if folder:
            self._folder = folder
            self._path_label.setText(folder)

    def _scan(self):
        """Scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        self._scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        age = self._age_combo.currentData()
        self.state.show_loading(f"Searching for files unmodified for over {age} days...")
        w = _OldFilesScanWorker(self._folder, age)
        self.win.run_worker(w, self._on_done, self._fail)

    def _on_done(self, files: list, stats: dict):
        """On done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            files (list): The files parameter.
            stats (dict): The stats parameter.
        """
        self._files = files
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)

        self.tbl.setRowCount(len(files))
        total_bytes = 0

        for r, (path_str, age_days, size_bytes) in enumerate(files):
            total_bytes += size_bytes
            item_path = QTableWidgetItem(path_str)
            item_path.setData(Qt.ItemDataRole.UserRole, path_str)
            self.tbl.setItem(r, 0, item_path)
            self.tbl.setItem(r, 1, QTableWidgetItem(f"{age_days} days old"))
            self.tbl.setItem(r, 2, QTableWidgetItem(fmt_bytes(size_bytes)))
            self.tbl.setItem(r, 3, QTableWidgetItem("Ready"))

        if not files:
            self.state.show_empty("No old inactive files found matching the age threshold.")
            self._summary_label.setText("0 files found")
            self.win.statusBar().showMessage("No old files found", 5000)
        else:
            self.state.clear()
            summary = f"Found {len(files)} old files occupying {fmt_bytes(total_bytes)}"
            self._summary_label.setText(summary)
            self.win.statusBar().showMessage(summary, 6000)

    def _delete_selected(self):
        """Delete selected.

        Manages delete selected operations and coordinates related state changes for the component.
        """
        sel = self.tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "No Selection", "Please select one or more files to delete.")
            return

        paths = [self.tbl.item(idx.row(), 0).data(Qt.ItemDataRole.UserRole) for idx in sel]
        ans = QMessageBox.question(
            self,
            "Delete Old Files",
            f"Are you sure you want to move {len(paths)} selected old file(s) to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        from cortex_unified.engine.secure_delete import recycle_path
        deleted = 0
        for p in paths:
            try:
                recycle_path(Path(p))
                deleted += 1
            except Exception:
                pass

        self.win.statusBar().showMessage(f"Moved {deleted} file(s) to the Recycle Bin", 6000)
        self._scan()

    def _fail(self, err: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            err (str): Error message string or exception instance.
        """
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self.state.show_error(f"Scan error: {err}")
        self.win.statusBar().showMessage(f"Error: {err}", 6000)
