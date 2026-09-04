"""Log Sweeper: find huge *.log/*.txt across user-selected roots (D:\\code).

The manual hit was 7.6GB of bot_debug*.log / full_bot_log.txt under
D:\\code\\Main_projects\\polybot. Those live outside the default
home/LOCALAPPDATA scope so the generic cache cleaner never saw them.
This page lets users point the sweep at D:\\code (or any folder) and
reports only logs >100MB, skipping .zip/.tar.gz backups.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QListWidget,
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

IS_WINDOWS = sys.platform == "win32"


class _LogWorker(QObject):
    """Logworker.

    Manages LogWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, roots, min_mb=100.0):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            roots: The roots parameter.
            min_mb: The min mb parameter.
        """
        super().__init__()
        self._roots = roots
        self._min = min_mb
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
            from cortex_unified.analyzers.cache_cleaner import CacheCleaner

            cc = CacheCleaner()
            res = cc.find_large_logs(
                self._roots,
                min_size_mb=self._min,
                exclude_archives=True,
                progress_callback=self.progress.emit,
                cancel_event=self._cancel,
            )
            self.finished.emit(res)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LogSweeperPage(_Page):
    """Logsweeperpage.

    Manages LogSweeperPage operations and coordinates related state changes for the component.
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
                "Log Sweeper",
                "Find large *.log / *.txt files (>100MB) across any folder you pick — "
                "code roots, project dirs, or other locations. Archives (.zip/.tar.gz) "
                "are excluded by default (they are backups, not logs).",
            )
        )

        # Roots picker
        roots_card = Card(self.p)
        rc = QVBoxLayout(roots_card)
        rc.setContentsMargins(14, 12, 14, 12)
        rc.setSpacing(6)
        lbl = QLabel("<b>Scan roots</b> — where to look for large logs")
        rc.addWidget(lbl)
        self.roots_list = QListWidget()
        self.roots_list.setMaximumHeight(70)
        # Seed with dynamic code root discovery
        for cand in self._discover_code_roots():
            try:
                if cand.is_dir() and str(cand) not in [
                    self.roots_list.item(i).text()
                    for i in range(self.roots_list.count())
                ]:
                    self.roots_list.addItem(str(cand))
            except Exception:
                continue
        rc.addWidget(self.roots_list)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Folder…")
        add_btn.setObjectName("Ghost")
        add_btn.clicked.connect(self._add_root)
        btn_row.addWidget(add_btn)
        code_btn = QPushButton("Select Code Root")
        code_btn.setObjectName("Primary")
        code_btn.setToolTip("Select a code root directory to scan for large logs.")
        code_btn.clicked.connect(self._select_code_root)
        btn_row.addWidget(code_btn)
        rm_btn = QPushButton("Remove Selected")
        rm_btn.setObjectName("Ghost")
        rm_btn.clicked.connect(self._rm_root)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch(1)
        rc.addLayout(btn_row)
        self.v.addWidget(roots_card)

        # Controls
        ctrl = QHBoxLayout()
        self.scan_btn = QPushButton("Find Large Logs (>100MB)")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self._scan)
        ctrl.addWidget(self.scan_btn)
        ctrl.addStretch(1)
        self.del_btn = QPushButton("Move Selected to Recycle Bin")
        self.del_btn.setObjectName("Danger")
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete)
        ctrl.addWidget(self.del_btn)
        self.v.addLayout(ctrl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.v.addWidget(self.status)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Log file", "Size", "Path"])
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.itemSelectionChanged.connect(
            lambda: self.del_btn.setEnabled(bool(self.tbl.selectedIndexes()))
        )
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        hint = QLabel(
            "Only logs >100MB are shown. .zip/.tar.gz archives are always excluded. Review before deleting — logs rotate, but you may want the latest."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        self.v.addWidget(hint)

        self._worker = None
        self._results: list[tuple[Path, int]] = []

    def _add_root(self):
        """_add_root.

        Manages add root operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder to sweep for logs", str(Path.home())
        )
        if folder and folder not in [
            self.roots_list.item(i).text() for i in range(self.roots_list.count())
        ]:
            self.roots_list.addItem(folder)

    def _discover_code_roots(self) -> list[Path]:
        """Discover common code root directories across all fixed drives.

        Manages discover code roots operations and coordinates related state changes for the component.

        Returns:
            list[Path]: List of processed items or identifiers.
        """
        import string

        roots: list[Path] = []
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:/")
            try:
                if drive.exists() and drive.is_dir():
                    for name in ("code", "projects"):
                        candidate = drive / name
                        try:
                            if candidate.is_dir() and candidate not in roots:
                                roots.append(candidate)
                        except OSError:
                            continue
            except OSError:
                continue
        home = Path.home()
        for name in ("code", "Projects"):
            candidate = home / name
            try:
                if candidate.is_dir() and candidate not in roots:
                    roots.append(candidate)
            except OSError:
                continue
        return roots

    def _select_code_root(self):
        """Open folder picker to select a code root directory.

        Manages select code root operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Select code root", str(Path.home())
        )
        if folder and folder not in [
            self.roots_list.item(i).text() for i in range(self.roots_list.count())
        ]:
            self.roots_list.addItem(folder)
            self.status.setText(f"Added {folder} — sweep will include it.")

    def _rm_root(self):
        """_rm_root.

        Manages rm root operations and coordinates related state changes for the component.
        """
        row = self.roots_list.currentRow()
        if row >= 0:
            self.roots_list.takeItem(row)

    def _scan(self):
        """_scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        roots = [self.roots_list.item(i).text() for i in range(self.roots_list.count())]
        if not roots:
            QMessageBox.information(
                self, "No roots", "Add at least one folder to scan."
            )
            return
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Sweeping for large logs…")
        self.status.setText(f"Scanning {len(roots)} root(s) for *.log >100MB…")
        w = _LogWorker(roots, min_mb=100.0)
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.status.setText(msg)

    def _on_done(self, results: list):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            results (list): Dictionary or data object holding operation results.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self._results = results
        self.tbl.setRowCount(len(results))
        total = sum(sz for _, sz in results)
        for r, (p, sz) in enumerate(results):
            self.tbl.setItem(r, 0, QTableWidgetItem(Path(p).name))
            self.tbl.setItem(r, 1, QTableWidgetItem(fmt_bytes(sz)))
            path_item = QTableWidgetItem(str(p))
            path_item.setToolTip(str(p))
            self.tbl.setItem(r, 2, path_item)
        if not results:
            self.state.show_empty(
                "No logs >100MB found under the selected roots. Try a broader folder or lower threshold."
            )
            self.status.setText("No large logs found.")
        else:
            self.state.clear()
            self.status.setText(
                f"Found {len(results)} large log(s), {fmt_bytes(total)} total. Archives (.zip/.tar.gz) excluded."
            )
        self.win.statusBar().showMessage(
            f"Log sweep: {len(results)} file(s), {fmt_bytes(total)}", 5000
        )

    def _delete(self):
        """Delete.

        Manages delete operations and coordinates related state changes for the component.
        """
        rows = {idx.row() for idx in self.tbl.selectedIndexes()}
        if not rows:
            QMessageBox.information(
                self, "No selection", "Select log files to recycle."
            )
            return
        paths = [
            self.tbl.item(r, 2).text() for r in sorted(rows) if self.tbl.item(r, 2)
        ]
        if not paths:
            return
        confirm = QMessageBox.question(
            self,
            "Move to Recycle Bin",
            f"Move {len(paths)} log(s) to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import DeleteSelectedWorker

        self.progress.setVisible(True)
        self.del_btn.setEnabled(False)
        self.win.run_worker(
            DeleteSelectedWorker(paths, "recycle"), self._on_deleted, self._fail
        )

    def _on_deleted(self, freed: int, ok: int, blocked: int):
        """_on_deleted.

        Manages on deleted operations and coordinates related state changes for the component.

        Args:
            freed (int): The freed parameter.
            ok (int): The ok parameter.
            blocked (int): The blocked parameter.
        """
        self.progress.setVisible(False)
        QMessageBox.information(
            self,
            "Done",
            f"Recycled {ok} log(s), freed {fmt_bytes(freed)}."
            + (f" {blocked} blocked." if blocked else ""),
        )
        self._scan()

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)
