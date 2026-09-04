"""Advanced Disk Analyzer page — MFT fast scan, treemap, deep folder breakdown.

Wraps :class:`AdvancedDiskAnalyzer` (NTFS MFT / ioctl / os.scandir) behind a
threaded worker so the UI stays responsive.  Results are presented as a
sortable table with size-bars, summary stat-cards, and state-panel feedback.
"""

from __future__ import annotations

import string
import sys
import threading
from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from . import icons
from .states import StatePanel
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page, fmt_bytes

# ---------------------------------------------------------------------------
#  Worker
# ---------------------------------------------------------------------------


class _ScanWorker(QObject):
    """Background worker: scans a path via AdvancedDiskAnalyzer.scan_sync.

    Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
    """

    finished = Signal(object)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, max_depth: int = 3):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            root (str): Filesystem path to the target file or directory.
            max_depth (int): The max depth parameter.
        """
        super().__init__()
        self._root = root
        self._max_depth = max_depth
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
            from cortex_unified.analyzers.advanced_disk_analyzer import (
                AdvancedDiskAnalyzer,
                scan_sync,
            )

            def _cb(scanned_files: int, scanned_bytes: int, current: str):
                """Cb.

                Manages cb operations and coordinates related state changes for the component.

                Args:
                    scanned_files (int): The scanned files parameter.
                    scanned_bytes (int): The scanned bytes parameter.
                    current (str): The current parameter.
                """
                if self._cancel.is_set():
                    return
                self.progress.emit(
                    f"Scanned {scanned_files:,} files "
                    f"({fmt_bytes(scanned_bytes)}) — {Path(current).name or current}"
                )

            entries, tree = scan_sync(
                self._root,
                include_cloud=False,
                progress_cb=_cb,
                cancel_event=self._cancel,
            )
            self.finished.emit(
                {
                    "entries": entries,
                    "tree": tree,
                    "root": self._root,
                    "max_depth": self._max_depth,
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _discover_fixed_drives() -> List[Tuple[str, str]]:
    """Return ``[(letter, label)]`` for every existing fixed drive letter.

    Manages discover fixed drives operations and coordinates related state changes for the component.

    Returns:
        List[Tuple[str, str]]: List of processed items or identifiers.
    """
    if sys.platform != "win32":
        return [("/", "/")]
    drives: List[Tuple[str, str]] = []
    for letter in string.ascii_uppercase:
        p = Path(f"{letter}:\\")
        try:
            if p.exists():
                vol = ""
                try:
                    import ctypes

                    buf = ctypes.create_unicode_buffer(256)
                    ctypes.windll.kernel32.GetVolumeInformationW(
                        str(p), buf, 256, None, None, None, None, 0
                    )
                    vol = buf.value
                except Exception:
                    pass
                label = f"{letter}: — {vol}" if vol else f"{letter}:"
                drives.append((letter, label))
        except OSError:
            continue
    return drives


def _compute_depth(node, target_path: str) -> int:
    """Walk the tree to find the depth of *target_path*.

    Manages compute depth operations and coordinates related state changes for the component.

    Args:
        node: The node parameter.
        target_path (str): Filesystem path to the target file or directory.

    Returns:
        int: Result of the operation.
    """
    parts = Path(target_path).parts
    return len(parts) - 1


# ---------------------------------------------------------------------------
#  Page
# ---------------------------------------------------------------------------


class DiskAnalyzerPage(_Page):
    """Diskanalyzerpage.

    Manages DiskAnalyzerPage operations and coordinates related state changes for the component.
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
                "Advanced Disk Analyzer",
                "Fast NTFS MFT scan with treemap data.  Analyze where space goes "
                "across any drive or folder with depth controls and size-bar results.",
            )
        )

        # ── Controls card ──────────────────────────────────────────────
        ctrl_card = Card(self.p, "Controls")
        ctrl_lay = QVBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(18, 16, 18, 16)
        ctrl_lay.setSpacing(10)

        # Row 1: drive picker + path entry + scan button
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self._drive_combo = QComboBox()
        self._drive_combo.setMinimumWidth(140)
        self._populate_drives()
        self._drive_combo.currentIndexChanged.connect(self._on_drive_changed)
        row1.addWidget(QLabel("Drive:"))
        row1.addWidget(self._drive_combo)

        self._path_edit = QLineEdit(str(Path.home()))
        self._path_edit.setPlaceholderText("Path to scan…")
        row1.addWidget(self._path_edit, 1)

        self._browse_btn = QPushButton("Browse\u2026")
        self._browse_btn.clicked.connect(self._browse)
        row1.addWidget(self._browse_btn)

        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setObjectName("Primary")
        self._scan_btn.clicked.connect(self._run)
        row1.addWidget(self._scan_btn)

        ctrl_lay.addLayout(row1)

        # Row 2: max depth
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self._depth_spin = QSpinBox()
        self._depth_spin.setRange(1, 12)
        self._depth_spin.setValue(3)
        self._depth_spin.setToolTip("Maximum folder depth to display in results (1–12)")
        row2.addWidget(QLabel("Max depth:"))
        row2.addWidget(self._depth_spin)
        row2.addStretch(1)
        ctrl_lay.addLayout(row2)

        self.v.addWidget(ctrl_card)

        # ── Progress / status ──────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self.v.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setObjectName("Muted")
        self.v.addWidget(self._status)

        # ── Summary stat cards ─────────────────────────────────────────
        stat_row = QHBoxLayout()
        stat_row.setSpacing(14)
        self._card_total = StatCard(self.p, "Total Scanned", "\u2014")
        self._card_largest = StatCard(self.p, "Largest Folder", "\u2014")
        self._card_files = StatCard(self.p, "File Count", "\u2014")
        for c in (self._card_total, self._card_largest, self._card_files):
            stat_row.addWidget(c)
        self.v.addLayout(stat_row)

        # ── Results table: interactive breakdown with size bars ─
        results_card = Card(self.p, "Folder Breakdown")
        results_lay = QVBoxLayout(results_card)
        results_lay.setContentsMargins(18, 16, 18, 16)
        results_lay.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Sorted by size (largest first)"))
        header_row.addStretch(1)

        self.sunburst_btn = QPushButton("Export Sunburst HTML")
        self.sunburst_btn.setObjectName("Ghost")
        self.sunburst_btn.setToolTip("Export interactive Plotly Sunburst disk hierarchy to HTML.")
        self.sunburst_btn.setEnabled(False)
        self.sunburst_btn.clicked.connect(self._export_sunburst)
        header_row.addWidget(self.sunburst_btn)

        self.treemap_btn = QPushButton("Export TreeMap HTML")
        self.treemap_btn.setObjectName("Ghost")
        self.treemap_btn.setToolTip("Export interactive Plotly TreeMap disk hierarchy to HTML.")
        self.treemap_btn.setEnabled(False)
        self.treemap_btn.clicked.connect(self._export_treemap)
        header_row.addWidget(self.treemap_btn)

        results_lay.addLayout(header_row)

        self._tbl = QTableWidget(0, 6)
        self._tbl.setHorizontalHeaderLabels(
            ["Folder", "Size", "% of Total", "Files", "Folders", "Depth"]
        )
        self._tbl.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._tbl.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tbl.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self._tbl)
        results_lay.addWidget(self._tbl, 1)

        self.v.addWidget(results_card, 1)

        # ── State panel (loading / empty / error) ─────────────────────
        self._state = StatePanel(self.p)
        self._state.bind_content(self._tbl)
        self.v.addWidget(self._state, 1)

        # ── Internal state ─────────────────────────────────────────────
        self._worker = None

    # ── Drive picker ───────────────────────────────────────────────────

    def _populate_drives(self):
        """_populate_drives.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.
        """
        self._drive_combo.blockSignals(True)
        self._drive_combo.clear()
        self._drive_combo.addItem("Custom path", None)
        for letter, label in _discover_fixed_drives():
            self._drive_combo.addItem(label, letter)
        self._drive_combo.blockSignals(False)

    def _on_drive_changed(self, idx: int):
        """_on_drive_changed.

        Manages on drive changed operations and coordinates related state changes for the component.

        Args:
            idx (int): The idx parameter.
        """
        letter = self._drive_combo.currentData()
        if letter is None:
            return
        self._path_edit.setText(f"{letter}:\\")

    def _browse(self):
        """Prompt the user to select a filesystem directory or file.

        Launches a native file dialog and populates the selected path into the corresponding target input widget.
        """
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder to analyze", self._path_edit.text()
        )
        if folder:
            self._path_edit.setText(folder)
            # Switch to "Custom path" if it isn't already
            if self._drive_combo.currentData() is not None:
                self._drive_combo.setCurrentIndex(0)

    # ── Scan ───────────────────────────────────────────────────────────

    def _run(self):
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
        path = self._path_edit.text().strip()
        if not path or not Path(path).is_dir():
            self._status.setText("Please enter a valid directory path.")
            return

        self._scan_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._state.show_loading(
            f"Scanning {path} (depth {self._depth_spin.value()})\u2026"
        )
        self._status.setText(f"Starting scan of {path}\u2026")
        self._tbl.setRowCount(0)

        w = _ScanWorker(path, max_depth=self._depth_spin.value())
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self._status.setText(msg)

    def _on_done(self, result):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            result: Dictionary or data object holding operation results.
        """
        self._worker = None
        self._progress.setVisible(False)
        self._scan_btn.setEnabled(True)

        tree = result["tree"]
        max_depth = result["max_depth"]
        total_size = tree.size or 1

        # Summary cards
        self._card_total.set_value(fmt_bytes(total_size))
        self._card_files.set_value(f"{tree.file_count:,}")

        bar_items = tree.to_bar_chart(top_n=50)
        if bar_items:
            self._card_largest.set_value(
                f"{bar_items[0]['name']} — {fmt_bytes(bar_items[0]['size'])}"
            )

        # Treemap data (table with size bars)
        treemap = tree.to_treemap(max_depth=max_depth)
        # Sort by size descending, skip root
        treemap = sorted(
            [n for n in treemap if n["path"]], key=lambda n: n["size"], reverse=True
        )

        self._last_tree = tree
        if hasattr(self, "sunburst_btn"):
            self.sunburst_btn.setEnabled(True)
            self.treemap_btn.setEnabled(True)

        if not treemap:
            self._state.show_empty(
                "No folders found. The path may be empty or inaccessible."
            )
            self._status.setText("Scan complete \u2014 no folders found.")
            return

        self._state.clear()
        self._tbl.setRowCount(len(treemap))
        for r, node in enumerate(treemap):
            name_item = QTableWidgetItem(node["name"])
            name_item.setToolTip(node["path"])
            self._tbl.setItem(r, 0, name_item)

            size_bytes = node["size"]
            pct = (size_bytes / total_size * 100) if total_size else 0

            size_item = QTableWidgetItem(fmt_bytes(size_bytes))
            size_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._tbl.setItem(r, 1, size_item)

            pct_item = QTableWidgetItem(f"{pct:.1f}%")
            pct_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._tbl.setItem(r, 2, pct_item)

            files_item = QTableWidgetItem(f"{node['file_count']:,}")
            files_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._tbl.setItem(r, 3, files_item)

            folders_item = QTableWidgetItem(f"{node['folder_count']:,}")
            folders_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self._tbl.setItem(r, 4, folders_item)

            depth_item = QTableWidgetItem(str(_compute_depth(tree, node["path"])))
            depth_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self._tbl.setItem(r, 5, depth_item)

        self._tbl.resizeRowsToContents()

        n_folders = len(treemap)
        self._status.setText(
            f"Scanned {result['root']} \u2014 "
            f"{tree.file_count:,} files, {fmt_bytes(total_size)} total, "
            f"{n_folders} folder nodes shown."
        )
        self.win.statusBar().showMessage(
            f"Disk scan complete: {n_folders} folders", 5000
        )

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._worker = None
        self._progress.setVisible(False)
        self._scan_btn.setEnabled(True)
        self._state.show_error(msg, on_retry=self._run)

    def _export_sunburst(self):
        """Export current disk analysis tree as an interactive Sunburst HTML chart.

        Manages export sunburst operations and coordinates related state changes for the component.
        """
        if not getattr(self, "_last_tree", None):
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        default_name = f"sunburst_{Path(self._path_edit.text()).stem or 'disk'}.html"
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Sunburst Chart", default_name, "HTML Files (*.html)")
        if not save_path:
            return
        try:
            from cortex_unified.visualization.sunburst_generator import SunburstGenerator
            tree_data = self._last_tree.to_sunburst()
            gen = SunburstGenerator(tree_data)
            html_content = gen.export_as_html()
            Path(save_path).write_text(html_content, encoding="utf-8")
            QMessageBox.information(self, "Export Complete", f"Sunburst chart exported to:\n{save_path}")
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", f"Failed to export chart: {exc}")

    def _export_treemap(self):
        """Export current disk analysis tree as an interactive TreeMap HTML chart.

        Manages export treemap operations and coordinates related state changes for the component.
        """
        if not getattr(self, "_last_tree", None):
            return
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        default_name = f"treemap_{Path(self._path_edit.text()).stem or 'disk'}.html"
        save_path, _ = QFileDialog.getSaveFileName(self, "Save TreeMap Chart", default_name, "HTML Files (*.html)")
        if not save_path:
            return
        try:
            from cortex_unified.visualization.treemap_generator import TreeMapGenerator
            tree_data = self._last_tree.to_treemap()
            gen = TreeMapGenerator(tree_data)
            html_content = gen.export_as_html()
            Path(save_path).write_text(html_content, encoding="utf-8")
            QMessageBox.information(self, "Export Complete", f"TreeMap chart exported to:\n{save_path}")
        except Exception as exc:
            QMessageBox.warning(self, "Export Error", f"Failed to export chart: {exc}")
