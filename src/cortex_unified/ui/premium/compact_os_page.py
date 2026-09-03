"""CompactOS / NTFS compression page – estimate, then compress only on demand.

Research: CompactOS (Windows 10/11) and USENIX ATC 2024 NTFS-compression
applicability. Read-first: lists folders with estimated reclaimable bytes, and
only ever compresses a folder the user explicitly selects, behind an
Administrator check and a confirmation dialog.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
)

from .states import StatePanel
from .widgets import status_note, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = sys.platform == "win32"


class _ScanWorker(QObject):
    """_ScanWorker class."""
    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, min_mb: float):
        """__init__."""
        super().__init__()
        self._root = root
        self._min = min_mb
        import threading

        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.compact_os import CompactOSManager

            ests = CompactOSManager().find_compressible_folders(
                self._root, min_size_mb=self._min,
                cancel_event=self._cancel, progress_callback=self.progress.emit)
            self.finished.emit([e.to_dict() for e in ests] if ests else [])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _CompactWorker(QObject):
    """_CompactWorker class."""
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, path: str):
        """__init__."""
        super().__init__()
        self._path = path

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.compact_os import CompactOSManager

            res = CompactOSManager().compact_folder(self._path, recursive=True)
            self.finished.emit(res.success, res.message)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _QueryWorker(QObject):
    """_QueryWorker class."""
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.compact_os import CompactOSManager

            m = CompactOSManager()
            info = m.compactos_query()
            info["drive_state"] = m.drive_compression_state("C:")
            self.finished.emit(info)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class CompactOsPage(_Page):
    """Estimate and apply NTFS compression to reclaim storage."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "CompactOS / NTFS Compression",
            "Question, then act (USENIX ATC 2024): find folders whose text/log/"
            "code content would compress by 50-75%, then compress only what you "
            "select. Media and already-compressed files gain ~nothing.",
        ))
        if not IS_WINDOWS:
            self.v.addWidget(status_note(
                self.p, "info", "CompactOS is only available on Windows."))
            return

        self._query_btn = QPushButton("Check CompactOS Status")
        self._query_btn.clicked.connect(self._query)
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("Muted")

        row = QHBoxLayout()
        row.addWidget(self._query_btn)
        row.addWidget(self._status_lbl, 1)
        self.v.addLayout(row)

        picker = QHBoxLayout()
        pick_btn = QPushButton("Scan Folder…")
        self._scan_btn = QPushButton("Estimate Compressible Folders")
        self._scan_btn.setObjectName("Primary")
        self._folder = str(Path.home())
        self._path_lbl = QLabel(self._folder)
        self._path_lbl.setObjectName("Muted")
        self._min_spin = QSpinBox()
        self._min_spin.setRange(1, 4096)
        self._min_spin.setValue(100)
        self._min_spin.setSuffix(" MB")
        self._min_spin.setToolTip("Only keep folders whose *estimated* savings exceed this.")
        pick_btn.clicked.connect(self._pick)
        self._scan_btn.clicked.connect(self._scan)
        picker.addWidget(pick_btn)
        picker.addWidget(self._path_lbl, 1)
        picker.addWidget(QLabel("Min savings:"))
        picker.addWidget(self._min_spin)
        picker.addWidget(self._scan_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(
            ["Folder", "Size", "Estimated savings", "Ratio", "State"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(
            lambda: self._compress_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self._compress_btn = QPushButton("Compress Selected Folder")
        self._compress_btn.setObjectName("Primary")
        self._compress_btn.setEnabled(False)
        self._compress_btn.clicked.connect(self._compress)
        self.v.addWidget(self._compress_btn)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        note = QLabel("Compression requires Administrator and is reversible "
                      "(CompactOS / right-click Properties). Logs and source "
                      "compress best; leave media and already-packed files alone.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.v.addWidget(note)

        self._worker = None

    def _pick(self):
        """_pick."""
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "Select folder", self._folder)
        if folder:
            self._folder = folder
            self._path_lbl.setText(folder)

    def _query(self):
        """_query."""
        self._query_btn.setEnabled(False)
        self._status_lbl.setText("Querying…")
        self.win.run_worker(_QueryWorker(), self._on_query, self._fail)

    def _on_query(self, info: dict):
        """_on_query."""
        self._query_btn.setEnabled(True)
        text = (f"CompactOS: {info.get('compactos', 'Unknown')}  |  "
                f"C: drive: {info.get('drive_state', 'Unknown')}  |  "
                f"Elevated: {'Yes' if info.get('elevated') else 'No (compression needs Administrator)'}")
        self._status_lbl.setText(text)

    def _scan(self):
        """_scan."""
        self._scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Estimating compressible folders…")
        self.tbl.setRowCount(0)
        w = _ScanWorker(self._folder, min_mb=float(self._min_spin.value()))
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress."""
        self._status_lbl.setText(msg)

    def _on_done(self, ests: list):
        """_on_done."""
        self._worker = None
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        if not ests:
            self.state.show_empty("No folders above the savings threshold found here.")
            self.win.statusBar().showMessage("No compressible folders", 5000)
            return
        self.state.clear()
        self.tbl.setRowCount(len(ests))
        for r, e in enumerate(ests):
            item0 = QTableWidgetItem(e["path"])
            item0.setData(Qt.ItemDataRole.UserRole, e)
            self.tbl.setItem(r, 0, item0)
            self.tbl.setItem(r, 1, QTableWidgetItem(fmt_bytes(e["size_bytes"])))
            self.tbl.setItem(r, 2, QTableWidgetItem(fmt_bytes(e["estimated_savings"])))
            self.tbl.setItem(r, 3, QTableWidgetItem(f"{e['compressible_ratio'] * 100:.0f}%"))
            self.tbl.setItem(r, 4, QTableWidgetItem(
                "Compressed" if e.get("already_compressed") else "Ready"))
        total = sum(e["estimated_savings"] for e in ests)
        self.win.statusBar().showMessage(
            f"{len(ests)} compressible folders, ~{fmt_bytes(total)} potential savings", 6000)

    def _compress(self):
        """_compress."""
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        rec = self.tbl.item(sel[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        if not rec:
            return
        confirm = QMessageBox.question(
            self, "Compress folder",
            f"Compress {rec['path']}?\n\n"
            "This flags the folder (and contents) for NTFS compression. "
            "Requires Administrator. Reversible via Properties.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._compress_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(_CompactWorker(rec["path"]), self._compact_done, self._fail)

    def _compact_done(self, success: bool, message: str):
        """_compact_done."""
        self.progress.setVisible(False)
        self._compress_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Compression complete", message)
        else:
            QMessageBox.warning(self, "Compression", message)
        self.win.statusBar().showMessage(message, 6000)

    def _fail(self, msg: str):
        """_fail."""
        self._worker = None
        self.progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self._query_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)
