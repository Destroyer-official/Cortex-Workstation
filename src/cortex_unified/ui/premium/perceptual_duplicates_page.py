"""Perceptual duplicate photos page – pHash / dHash / aHash.

Research: DCT perceptual hashing (IEEE 2024) tolerates re-scaling and re-coding
that byte-exact dedup cannot see; dHash/aHash are cheap pixel-domain fallbacks.
Finds *visually similar* photos, not just byte-identical files.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from .widgets import title_block
from .window import _Page, fmt_bytes
from .states import StatePanel
from cortex_unified.analyzers.perceptual_duplicate_finder import PerceptualDuplicateFinder


class _PerceptualWorker(QObject):
    """_PerceptualWorker class."""
    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, max_distance: int = 10):
        """__init__."""
        super().__init__()
        self._root = root
        self._dist = max_distance
        import threading

        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.analyzers.perceptual_duplicate_finder import (
                PerceptualDuplicateFinder,
            )

            finder = PerceptualDuplicateFinder(
                root_path=self._root, max_distance=self._dist)
            groups = finder.find_perceptual_duplicates(
                progress_callback=lambda msg, *_: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )
            self.finished.emit(groups)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PerceptualDuplicatesPage(_Page):
    """Find visually-similar photos via perceptual hashing (pHash)."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Duplicate Photos (Perceptual)",
            "pHash / dHash / aHash (IEEE 2024) – groups photos that *look* the "
            "same even after re-scaling or re-compression. Distance <= 10 of 64 bits.",
        ))
        from PySide6.QtWidgets import (
            QFileDialog, QProgressBar, QPushButton, QSpinBox,
        )

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Folder…")
        self.path_label = QLabel(str(Path.home()))
        self.run_btn = QPushButton("Find Visual Duplicates")
        self.run_btn.setObjectName("Primary")
        self.dist_spin = QSpinBox()
        self.dist_spin.setRange(0, 32)
        self.dist_spin.setValue(10)
        self.dist_spin.setToolTip("Max Hamming distance (0-64). 10 = standard pHash bound")
        pick_btn.clicked.connect(self._pick)
        self.run_btn.clicked.connect(self._run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
        picker.addWidget(QLabel("Max dist:"))
        picker.addWidget(self.dist_spin)
        picker.addWidget(self.run_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Photo", "Group", "Hint"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._folder = str(Path.home())
        self._worker = None

    def _pick(self):
        """_pick."""
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Select folder", self._folder)
        if folder:
            self._folder = folder
            self.path_label.setText(folder)

    def _run(self):
        """_run."""
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Hashing photos (pHash)…")
        self.status.setText(f"Scanning {self._folder}…")
        self.tbl.setRowCount(0)
        w = _PerceptualWorker(self._folder, max_distance=self.dist_spin.value())
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress."""
        self.status.setText(msg)

    def _on_done(self, groups: dict):
        """_on_done."""
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        if not groups:
            self.state.show_empty(
                "No visually-similar photos detected. Try a lower max-distance "
                "or pick a folder with resized/re-encoded photo sets.")
            self.status.setText("No visual duplicates found.")
            self.win.statusBar().showMessage("No visual duplicates", 5000)
            return
        self.state.clear()
        rows = [
            (str(p), gid, f"pHash dist <= {self.dist_spin.value()}")
            for gid, paths in groups.items() for p in paths
        ]
        self.tbl.setRowCount(len(rows))
        for r, (path, gid, hint) in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(path))
            self.tbl.setItem(r, 1, QTableWidgetItem(f"#{str(gid)[:8]}"))
            self.tbl.setItem(r, 2, QTableWidgetItem(hint))
        total = 0
        for path, _, _ in rows:
            try:
                total += Path(path).stat().st_size
            except OSError:
                pass
        self.status.setText(
            f"{len(groups)} visual-duplicate groups, {len(rows)} photos, "
            f"{fmt_bytes(total)} if all removed.")
        self.win.statusBar().showMessage(f"{len(groups)} visual-duplicate groups", 5000)

    def _fail(self, msg):
        """_fail."""
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)
