"""Video near-duplicate detection page – keyframe pHash + temporal consistence.

Research: AVSS 2024 (ViT keyframe) + TCSVT 2024 (temporal consistence
re-ranking, 98.8 % recall) + ICCC 2025 (Swin-Transformer multi-scale).
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
from cortex_unified.analyzers.video_duplicate_finder import VideoDuplicateFinder


class _VideoWorker(QObject):
    """Videoworker.

    Manages VideoWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, threshold: float = 0.55):
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
            from cortex_unified.analyzers.video_duplicate_finder import VideoDuplicateFinder

            finder = VideoDuplicateFinder(self._root, threshold=self._thr)
            groups = finder.find_video_duplicates(
                progress_callback=lambda msg, *_: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
            )
            self.finished.emit(groups)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class VideoDuplicatesPage(_Page):
    """Videoduplicatespage.

    Manages VideoDuplicatesPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Video Near-Duplicates",
            "Keyframe pHash + temporal consistence re-ranking (TCSVT 2024) – "
            "matches a trimmed or re-encoded clip against its full source by "
            "longest diagonally-consistent frame run.",
        ))
        from PySide6.QtWidgets import (
            QFileDialog, QProgressBar, QPushButton, QDoubleSpinBox,
        )

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Folder…")
        self.path_label = QLabel(str(Path.home()))
        self.run_btn = QPushButton("Find Video Duplicates")
        self.run_btn.setObjectName("Primary")
        self.thr_spin = QDoubleSpinBox()
        self.thr_spin.setRange(0.3, 0.9)
        self.thr_spin.setSingleStep(0.05)
        self.thr_spin.setValue(0.55)
        self.thr_spin.setToolTip("Temporal similarity 0.3–0.9 (0.55 ≈ 3-frame run)")
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
        self.tbl.setHorizontalHeaderLabels(["Video File", "Group", "Hint"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.v.addWidget(self.tbl, 1)

        act_row = QHBoxLayout()
        self.opt_btn = QPushButton("Optimize Selected Video (Crop & Re-Encode)")
        self.opt_btn.setObjectName("Ghost")
        self.opt_btn.setToolTip("Uses VideoOptimizer to crop static black borders and re-encode with libx264.")
        self.opt_btn.clicked.connect(self._optimize_video)
        act_row.addWidget(self.opt_btn)
        act_row.addStretch(1)
        self.v.addLayout(act_row)

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
        self.state.show_loading("Hashing video keyframes…")
        self.status.setText(f"Scanning {self._folder}…")
        self.tbl.setRowCount(0)
        w = _VideoWorker(self._folder, threshold=float(self.thr_spin.value()))
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
                "No video near-duplicates found. Lower the threshold or scan a "
                "folder with re-encoded / trimmed copies of the same source.")
            self.status.setText("No video duplicates found.")
            self.win.statusBar().showMessage("No video duplicates", 5000)
            return
        self.state.clear()
        rows = [
            (str(p), gid, f"temporal ≥ {self.thr_spin.value():.2f}")
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
            f"{len(groups)} video groups, {len(rows)} files, "
            f"{fmt_bytes(total)} if all removed.")
        self.win.statusBar().showMessage(f"{len(groups)} video-duplicate groups", 5000)

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

    def _optimize_video(self):
        """Optimize selected or picked video with VideoOptimizer.

        Manages optimize video operations and coordinates related state changes for the component.
        """
        row = self.tbl.currentRow()
        target_path = None
        if row >= 0:
            item = self.tbl.item(row, 0)
            if item and item.text():
                target_path = item.text()

        if not target_path or not Path(target_path).exists():
            from PySide6.QtWidgets import QFileDialog
            f, _ = QFileDialog.getOpenFileName(self, "Select Video to Optimize", self._folder, "Video Files (*.mp4 *.mkv *.avi *.mov)")
            if f:
                target_path = f

        if not target_path:
            return

        from PySide6.QtWidgets import QMessageBox
        self.status.setText(f"Optimizing video with VideoOptimizer: {Path(target_path).name}…")
        self.progress.setVisible(True)

        def work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            from cortex_unified.analyzers.czkawka_tools import VideoOptimizer
            opt = VideoOptimizer()
            p = Path(target_path)
            ok = opt.optimize(p)
            return ok, p

        def done(res):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                res: The res parameter.
            """
            ok, p = res
            self.progress.setVisible(False)
            if ok:
                msg = f"Successfully optimized: {p.name} -> {p.with_suffix('.optimized.mp4').name}"
                self.status.setText(msg)
                QMessageBox.information(self, "Optimization Complete", msg)
            else:
                self.status.setText("Video optimization failed or ffmpeg not available.")
                QMessageBox.warning(self, "Optimization Note", "Could not optimize video. Ensure ffmpeg is installed and video is valid.")

        def error(msg):
            """Handle an operation failure and notify the user.

            Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

            Args:
                msg: Informational or progress status message.
            """
            self.progress.setVisible(False)
            self.status.setText(f"Optimization error: {msg}")
            QMessageBox.warning(self, "Optimization Error", str(msg))

        if hasattr(self.win, "worker_runtime"):
            self.win.worker_runtime.run(work, on_result=done, on_error=error)
        else:
            try:
                done(work())
            except Exception as e:
                error(str(e))
