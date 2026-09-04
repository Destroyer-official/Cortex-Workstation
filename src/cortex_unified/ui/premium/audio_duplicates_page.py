"""Audio duplicate detection page – Chromaprint-inspired acoustic fingerprinting.

Research: Ke et al. CVPR 2005 + Kurth/Müller TASLP 2008 + Jang TIFS 2009;
Chromaprint/AcoustID (MusicBrainz) for cross-format duplicate detection
(FLAC vs MP3 of same master must match).
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

from .states import StatePanel
from .widgets import title_block
from .window import _Page, fmt_bytes
from cortex_unified.analyzers.audio_duplicate_finder import AudioDuplicateFinder


class _AudioWorker(QObject):
    """Audioworker.

    Manages AudioWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, threshold: float = 0.75):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            root (str): Filesystem path to the target file or directory.
            threshold (float): The threshold parameter.
        """
        super().__init__()
        self._root = root
        self._thr = threshold
        import threading

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
            from cortex_unified.analyzers.audio_duplicate_finder import AudioDuplicateFinder

            finder = AudioDuplicateFinder(self._root, threshold=self._thr)
            groups = finder.find_audio_duplicates(
                progress_callback=lambda msg, *_: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )
            self.finished.emit(groups)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class AudioDuplicatesPage(_Page):
    """Audioduplicatespage.

    Manages AudioDuplicatesPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Audio Duplicates (Acoustic)",
            "Chromaprint-inspired spectral fingerprinting (Ke CVPR 2005) – "
            "groups music that *sounds* identical even when stored as FLAC vs "
            "MP3 vs M4A. Cross-format, encoding-robust.",
        ))
        from PySide6.QtWidgets import (
            QFileDialog, QProgressBar, QPushButton, QDoubleSpinBox,
        )

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Folder…")
        self.path_label = QLabel(str(Path.home()))
        self.run_btn = QPushButton("Find Audio Duplicates")
        self.run_btn.setObjectName("Primary")
        self.thr_spin = QDoubleSpinBox()
        self.thr_spin.setRange(0.5, 0.95)
        self.thr_spin.setSingleStep(0.05)
        self.thr_spin.setValue(0.75)
        self.thr_spin.setToolTip("Similarity 0.5–0.95 (0.75 = strong match)")
        pick_btn.clicked.connect(self._pick)
        self.run_btn.clicked.connect(self._run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
        picker.addWidget(QLabel("Threshold:"))
        picker.addWidget(self.thr_spin)
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
        self.tbl.setHorizontalHeaderLabels(["Audio File", "Group", "Hint"])
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
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Select folder", self._folder)
        if folder:
            self._folder = folder
            self.path_label.setText(folder)

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Fingerprinting audio (spectral)…")
        self.status.setText(f"Scanning {self._folder}…")
        self.tbl.setRowCount(0)
        w = _AudioWorker(self._folder, threshold=float(self.thr_spin.value()))
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.status.setText(msg)

    def _on_done(self, groups: dict):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            groups (dict): The groups parameter.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        if not groups:
            self.state.show_empty(
                "No acoustically-duplicate audio found. Lower the threshold or "
                "scan a music library with FLAC+MP3 copies of the same tracks.")
            self.status.setText("No audio duplicates found.")
            self.win.statusBar().showMessage("No audio duplicates", 5000)
            return
        self.state.clear()
        rows = [
            (str(p), gid, f"acoustic ≥ {self.thr_spin.value():.2f}")
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
            f"{len(groups)} audio groups, {len(rows)} files, "
            f"{fmt_bytes(total)} if all removed.")
        self.win.statusBar().showMessage(f"{len(groups)} audio-duplicate groups", 5000)

    def _fail(self, msg):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg: Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)
