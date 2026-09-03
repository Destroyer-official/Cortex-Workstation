"""Near-duplicate finder page – MinHash LSH + Bloom (SEDD/LSHBloom/SemHash).

Research: SEDD 158× CPU / 7.8× NeMo, LSHBloom 12×/18× on peS2o 39M docs,
SemHash cascaded Bloom→semantic hash→LSH→neural 0.7% pass-through.

This page finds *near*-duplicates (high Jaccard, e.g. copy-pasted code with
small edits) that exact-duplicate finder misses. Uses shingle k=5,
H=128, b=16 bands, threshold 0.8, Bloom pre-screen 40% elimination.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)

from .widgets import title_block
from .window import _Page, fmt_bytes
from .states import StatePanel
from cortex_unified.analyzers.near_duplicate_finder import NearDuplicateFinder


class _NearDupWorker(QObject):
    """_NearDupWorker class."""
    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, threshold: float = 0.8):
        """__init__."""
        super().__init__()
        self._root = root
        self._thr = threshold
        import threading

        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.analyzers.near_duplicate_finder import NearDuplicateFinder

            finder = NearDuplicateFinder(root_path=self._root, threshold=self._thr)
            groups = finder.find_near_duplicates(
                progress_callback=lambda msg, *_: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )
            self.finished.emit(groups)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class NearDuplicatesPage(_Page):
    """Find near-duplicate files (80%+ Jaccard) via MinHash LSH + Bloom."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Near Duplicates",
            "MinHash LSH + Bloom (SEDD/LSHBloom) – finds copy-pasted code with small edits, "
            "not just byte-identical files. 80% Jaccard threshold, H=128, b=16.",
        ))
        from PySide6.QtWidgets import (
            QFileDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton,
            QTableWidget, QTableWidgetItem, QVBoxLayout,
        )
        from pathlib import Path

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Folder…")
        self.path_label = QLabel(str(Path.home()))
        self.run_btn = QPushButton("Find Near-Duplicates")
        self.run_btn.setObjectName("Primary")
        pick_btn.clicked.connect(self._pick)
        self.run_btn.clicked.connect(self._run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
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
        self.tbl.setHorizontalHeaderLabels(["File", "Group", "Hint"])
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
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Select folder", self._folder)
        if folder:
            self._folder = folder
            self.path_label.setText(folder)

    def _run(self):
        """_run."""
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Finding near-duplicates (MinHash)…")
        self.status.setText(f"Scanning {self._folder}…")
        self.tbl.setRowCount(0)
        w = _NearDupWorker(self._folder, threshold=0.8)
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
            self.state.show_empty("No near-duplicates detected (threshold 80%). Try exact Duplicates page for byte-identical.")
            self.status.setText("No near-duplicates – corpus is diverse.")
            self.win.statusBar().showMessage("No near-duplicates", 5000)
            return
        self.state.clear()
        rows = [(str(p), gid, "near-dup ~80% Jaccard") for gid, paths in groups.items() for p in paths]
        self.tbl.setRowCount(len(rows))
        for r, (path, gid, hint) in enumerate(rows):
            self.tbl.setItem(r, 0, QTableWidgetItem(path))
            self.tbl.setItem(r, 1, QTableWidgetItem(f"#{str(gid)[:8]}"))
            self.tbl.setItem(r, 2, QTableWidgetItem(hint))
        from pathlib import Path as _P

        try:
            total = sum(_P(p).stat().st_size for p, _, _ in rows if _P(p).is_file())
        except OSError:
            total = 0
        self.status.setText(f"{len(groups)} near-duplicate groups, {len(rows)} files – chunked FastCDC adds +15% via Hybrid paper.")
        self.win.statusBar().showMessage(f"{len(groups)} near-duplicate groups", 5000)

    def _fail(self, msg):
        """_fail."""
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)
