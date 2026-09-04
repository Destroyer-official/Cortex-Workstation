"""Bad Extensions, File Names & EXIF Studio Page.

Integrates analyzers.czkawka_tools (BadExtensionFinder, BadNamesFinder, ExifRemover):
- Bad Extensions: Detects files whose internal magic bytes mismatch their file extension
  (e.g. an executable .exe masquerading as .jpg, or .png saved as .txt)
- Bad File Names: Detects files with invalid Windows characters, trailing spaces,
  or invisible unicode characters that cause file explorer / syncing errors
- EXIF Privacy Scrubber: Scans photo collections for sensitive EXIF metadata
  (GPS location coordinates, camera serial numbers) and removes metadata in-place
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
from .window import _Page


class _BadFilesScanWorker(QObject):
    """Badfilesscanworker.

    Manages BadFilesScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, mode: str, folder: str):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            mode (str): The mode parameter.
            folder (str): Filesystem path to the target file or directory.
        """
        super().__init__()
        self._mode = mode
        self._folder = folder

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.analyzers.czkawka_tools import (
                BadExtensionFinder,
                BadNamesFinder,
                ExifCleaner,
            )
            root = Path(self._folder)
            results = []
            if self._mode == "extensions":
                finder = BadExtensionFinder(root=str(root))
                items = finder.find()
                for item in items:
                    results.append({
                        "path": str(item.path),
                        "detail": f"Actual: {item.actual} -> Claimed: {item.claimed}",
                        "issue": "Extension Mismatch",
                    })
            elif self._mode == "names":
                finder = BadNamesFinder(root=str(root))
                items = finder.find()
                for p in items:
                    results.append({
                        "path": str(p),
                        "detail": "Invalid characters or Windows reserved name",
                        "issue": "Illegal / Non-standard Filename",
                    })
            elif self._mode == "exif":
                finder = ExifCleaner(root=str(root))
                items = finder.scan()
                for p, tags in items:
                    gps = "GPS Location" if any("gps" in k.lower() for k in tags.keys()) else "Camera Metadata"
                    results.append({
                        "path": str(p),
                        "detail": f"{len(tags)} EXIF tags found ({gps})",
                        "issue": "Privacy Metadata Exposed",
                    })
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class BadFilesStudioPage(_Page):
    """Badfilesstudiopage.

    Manages BadFilesStudioPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Bad Extensions, Names & EXIF Studio",
            "Multi-tool diagnostic suite: detect mismatched file extensions (magic header analysis), "
            "invalid file names causing sync errors, and strip privacy-sensitive EXIF metadata "
            "(GPS coordinates, camera serials) from photos.",
        ))

        self._folder = str(Path.home() / "Pictures")

        # Configuration Card
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

        bar_layout.addWidget(QLabel("Audit Tool:"))
        self._tool_combo = QComboBox()
        self._tool_combo.addItem("Bad File Extensions (Magic Header)", "extensions")
        self._tool_combo.addItem("Invalid File Names (NTFS / Sync)", "names")
        self._tool_combo.addItem("EXIF Privacy Scrubber (Photos)", "exif")
        self._tool_combo.currentIndexChanged.connect(self._on_tool_changed)
        bar_layout.addWidget(self._tool_combo)

        self._scan_btn = QPushButton("Run Audit")
        self._scan_btn.setObjectName("Primary")
        self._scan_btn.clicked.connect(self._scan)
        bar_layout.addWidget(self._scan_btn)

        self.v.addWidget(bar_card)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        # Results Table
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["File Path", "Issue Type", "Details / Diagnostics"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        # Bottom Actions Row
        action_row = QHBoxLayout()
        self._action_btn = QPushButton("Strip EXIF Metadata")
        self._action_btn.setObjectName("Primary")
        self._action_btn.setVisible(False)
        self._action_btn.clicked.connect(self._strip_exif)
        action_row.addWidget(self._action_btn)

        action_row.addStretch(1)
        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("Muted")
        action_row.addWidget(self._summary_lbl)

        self.v.addLayout(action_row)

        # Initial scan
        self._scan()

    def _on_tool_changed(self, idx):
        """On tool changed.

        Manages on tool changed operations and coordinates related state changes for the component.

        Args:
            idx: The idx parameter.
        """
        mode = self._tool_combo.currentData()
        if mode == "exif":
            self._action_btn.setVisible(True)
            self._folder = str(Path.home() / "Pictures")
        else:
            self._action_btn.setVisible(False)
            self._folder = str(Path.home() / "Downloads")
        self._path_label.setText(self._folder)

    def _pick_folder(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Audit Target", self._folder)
        if folder:
            self._folder = folder
            self._path_label.setText(folder)

    def _scan(self):
        """Scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        mode = self._tool_combo.currentData()
        self._scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(f"Analyzing files for {mode} issues...")
        w = _BadFilesScanWorker(mode, self._folder)
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

        for r, item in enumerate(results):
            path_item = QTableWidgetItem(item["path"])
            path_item.setData(Qt.ItemDataRole.UserRole, item["path"])
            self.tbl.setItem(r, 0, path_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(item["issue"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(item["detail"]))

        mode = self._tool_combo.currentData()
        if not results:
            self.state.show_empty(f"Clean! No {mode} issues found in the target folder.")
            self._summary_lbl.setText("0 issues found")
            self.win.statusBar().showMessage("Target folder is clean", 5000)
        else:
            self.state.clear()
            msg = f"Found {len(results)} items requiring attention"
            self._summary_lbl.setText(msg)
            self.win.statusBar().showMessage(msg, 6000)

    def _strip_exif(self):
        """Strip exif.

        Manages strip exif operations and coordinates related state changes for the component.
        """
        sel = self.tbl.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Select Photos", "Please select one or more photos to strip EXIF data from.")
            return

        from cortex_unified.analyzers.czkawka_tools import ExifCleaner
        paths = []
        for idx in sel:
            p_str = self.tbl.item(idx.row(), 0).data(Qt.ItemDataRole.UserRole)
            if p_str:
                paths.append(Path(p_str))
        if paths:
            cleaner = ExifCleaner(root=paths[0].parent)
            res = cleaner.strip(paths)
            count = sum(1 for v in res.values() if v)
        else:
            count = 0

        QMessageBox.information(self, "EXIF Stripped", f"Successfully scrubbed EXIF metadata from {count} photo(s).")
        self._scan()

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
