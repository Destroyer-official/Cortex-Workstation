"""Windows Search Index Database (Windows.edb) Optimizer Page.

Studio for querying search catalog metrics, performing offline ESENT database compaction,
and triggering full background search re-indexing.
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QObject, Signal, QThread
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.system_tools.search_index_optimizer import (
    SearchIndexOperationResult,
    SearchIndexOptimizer,
    SearchIndexStatus,
)
from .widgets import Card, StatCard, status_note, title_block
from .window import _Page, fmt_bytes


class _SearchWorker(QObject):
    """Searchworker.

    Manages SearchWorker operations and coordinates related state changes for the component.
    """
    status_ready = Signal(object)
    op_finished = Signal(object)

    def run_status(self) -> None:
        """run_status.

        Manages run status operations and coordinates related state changes for the component.
        """
        status = SearchIndexOptimizer.get_status()
        self.status_ready.emit(status)

    def run_compact(self) -> None:
        """run_compact.

        Manages run compact operations and coordinates related state changes for the component.
        """
        res = SearchIndexOptimizer.compact_database()
        self.op_finished.emit(res)

    def run_rebuild(self) -> None:
        """run_rebuild.

        Manages run rebuild operations and coordinates related state changes for the component.
        """
        res = SearchIndexOptimizer.rebuild_index()
        self.op_finished.emit(res)


class SearchIndexOptimizerPage(_Page):
    """Searchindexoptimizerpage.

    Manages SearchIndexOptimizerPage operations and coordinates related state changes for the component.
    """

    def __init__(self, win) -> None:
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.current_status: Optional[SearchIndexStatus] = None
        self._thread: Optional[QThread] = None

        hdr = title_block(
            "Windows Search Catalog & EDB Optimizer",
            "Compact inflated Windows.edb databases, eliminate B-tree fragmentation, and optimize search indexing.",
        )
        self.v.addWidget(hdr)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_size = StatCard(self.p, "Database Size", "0 MB")
        self.stat_items = StatCard(self.p, "Indexed Items", "0")
        self.stat_service = StatCard(self.p, "WSearch Service", "Unknown")
        stats_row.addWidget(self.stat_size)
        stats_row.addWidget(self.stat_items)
        stats_row.addWidget(self.stat_service)
        self.v.addLayout(stats_row)

        ctrl_card = Card(self.p)
        ctrl_lay = QHBoxLayout(ctrl_card)
        ctrl_lay.setContentsMargins(14, 10, 14, 10)

        self.btn_refresh = QPushButton("Inspect Search Database")
        self.btn_refresh.setObjectName("AccentButton")
        self.btn_refresh.clicked.connect(self._start_status_query)
        ctrl_lay.addWidget(self.btn_refresh)

        self.btn_compact = QPushButton("Compact Database (esentutl /d)")
        self.btn_compact.setToolTip("Stops WSearch, defragments Windows.edb offline, and restarts WSearch.")
        self.btn_compact.clicked.connect(self._start_compact)
        ctrl_lay.addWidget(self.btn_compact)

        self.btn_rebuild = QPushButton("Rebuild Index Catalog")
        self.btn_rebuild.setToolTip("Deletes corrupted catalog database to trigger complete clean background re-indexing.")
        self.btn_rebuild.clicked.connect(self._start_rebuild)
        ctrl_lay.addWidget(self.btn_rebuild)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        ctrl_lay.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready.")
        ctrl_lay.addWidget(self.lbl_status)
        ctrl_lay.addStretch()

        self.v.addWidget(ctrl_card)

        # Database Details Card
        info_card = Card(self.p)
        info_lay = QVBoxLayout(info_card)
        info_lay.setContentsMargins(16, 16, 16, 16)
        info_lay.addWidget(QLabel("<b>Catalog Diagnostics & System Location:</b>"))

        form = QFormLayout()
        self.lbl_db_path = QLabel("Locating...")
        self.lbl_bloated = QLabel("Normal")
        self.lbl_admin = QLabel("Yes" if sys.platform == "win32" else "N/A")

        form.addRow("Database File:", self.lbl_db_path)
        form.addRow("Bloat Level:", self.lbl_bloated)
        form.addRow("Administrative Elevation:", self.lbl_admin)
        info_lay.addLayout(form)

        self.v.addWidget(info_card)

        self.note = status_note(
            self.p,
            "info",
            "Note: Compacting or rebuilding Windows.edb requires stopping the 'WSearch' service temporarily. "
            "Please run Cortex Cleaner as Administrator to ensure service control permissions.",
        )
        self.v.addWidget(self.note)

    def _start_status_query(self) -> None:
        """_start_status_query.

        Manages start status query operations and coordinates related state changes for the component.
        """
        if self._thread and self._thread.isRunning():
            return
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Querying Windows Search catalog...")

        self._thread = QThread()
        self._worker = _SearchWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run_status)
        self._worker.status_ready.connect(self._on_status_ready)
        self._thread.start()

    def _on_status_ready(self, status: SearchIndexStatus) -> None:
        """_on_status_ready.

        Manages on status ready operations and coordinates related state changes for the component.

        Args:
            status (SearchIndexStatus): The status parameter.
        """
        self.current_status = status
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.stat_size.set_value(fmt_bytes(status.database_size_bytes))
        self.stat_items.set_value(f"{status.indexed_items_estimate:,}")
        self.stat_service.set_value(status.service_status)

        self.lbl_db_path.setText(status.database_path or "Not found")
        self.lbl_bloated.setText("Warning: Inflated (> 1 GB)" if status.is_bloated else "Optimal")
        self.lbl_admin.setText("Elevated (Full Control)" if status.is_admin else "Standard User (Limited)")
        self.lbl_status.setText("Diagnostics updated.")

    def _start_compact(self) -> None:
        """_start_compact.

        Manages start compact operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self,
            "Confirm Database Compaction",
            "Offline compaction will temporarily pause the Windows Search service, "
            "defragment Windows.edb using esentutl.exe, and restart the service.\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._run_async_op(lambda w: w.run_compact, "Compacting Windows.edb database...")

    def _start_rebuild(self) -> None:
        """_start_rebuild.

        Manages start rebuild operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self,
            "Confirm Index Rebuild",
            "This will delete the existing search catalog and initiate a complete clean index rebuild in the background.\n\n"
            "Search queries may be temporarily incomplete while Windows rebuilds the catalog. Proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._run_async_op(lambda w: w.run_rebuild, "Initiating catalog rebuild...")

    def _run_async_op(self, call_fn, status_text: str) -> None:
        """_run_async_op.

        Manages run async op operations and coordinates related state changes for the component.

        Args:
            call_fn: The call fn parameter.
            status_text (str): The status text parameter.
        """
        self.btn_refresh.setEnabled(False)
        self.btn_compact.setEnabled(False)
        self.btn_rebuild.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText(status_text)

        self._thread = QThread()
        self._worker = _SearchWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(lambda: call_fn(self._worker)())
        self._worker.op_finished.connect(self._on_op_finished)
        self._thread.start()

    def _on_op_finished(self, res: SearchIndexOperationResult) -> None:
        """_on_op_finished.

        Manages on op finished operations and coordinates related state changes for the component.

        Args:
            res (SearchIndexOperationResult): The res parameter.
        """
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None

        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
        self.btn_compact.setEnabled(True)
        self.btn_rebuild.setEnabled(True)
        self._start_status_query()

        if res.success:
            QMessageBox.information(self, "Search Optimization", res.message)
        else:
            err_details = "\n".join(res.errors) if res.errors else res.message
            QMessageBox.warning(self, "Search Optimization", f"Operation encountered issues:\n{err_details}")
