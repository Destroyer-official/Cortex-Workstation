"""Model Cache page – hardlink-aware HF hub / Ollama / LM Studio.

Shows the research-backed reality: HF hub ``blobs/`` is CAS by SHA with
``refs/snapshots`` symlinks; Explorer double-counts hardlinks. We measure
unique inodes and surface *orphan* blobs (interrupted downloads, *.incomplete)
safe via ``huggingface-cli delete-cache --orphans`` (model-warden rule:
never rm inside a store another tool owns – route via owning CLI and verify).
Also surfaces Ollama blob store, quantization savings (FP16→Q4_K_M 75% per
Interconnectd table), and hardlink dedup savings.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, title_block, status_note
from .window import _Page, fmt_bytes

IS_WINDOWS = sys.platform == "win32"


class _ScanWorker(QObject):
    """_ScanWorker class.

    Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
    """
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.model_cache_manager import ModelCacheManager

            self.finished.emit(ModelCacheManager().scan_all())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _CleanOrphansWorker(QObject):
    """_CleanOrphansWorker class.

    Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
    """
    finished = Signal(bool, str, int)
    failed = Signal(str)

    def __init__(self, dry_run: bool = True):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            dry_run (bool): The dry run parameter.
        """
        super().__init__()
        self._dry = dry_run

    def run(self):
        """run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            from cortex_unified.system_tools.model_cache_manager import ModelCacheManager

            ok, msg, freed = ModelCacheManager().clean_hf_orphans(dry_run=self._dry)
            self.finished.emit(ok, msg, freed)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ModelCachePage(_Page):
    """Modelcachepage.

    Manages ModelCachePage operations and coordinates related state changes for the component.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Model Cache",
            "LLM model caches (Hugging Face hub CAS, Ollama blobs, LM Studio, ComfyUI) – "
            "measured hardlink-aware (unique inodes). Orphan blobs (interrupted downloads, *.incomplete) "
            "are safe via ‘huggingface-cli delete-cache --orphans’. FP16→Q4_K_M saves 75% (quantization table).",
        ))

        row = QHBoxLayout()
        self.scan_btn = QPushButton("Scan Model Caches")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self._scan)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        self.dry_btn = QPushButton("Preview Orphan Cleanup")
        self.dry_btn.clicked.connect(lambda: self._clean(dry_run=True))
        row.addWidget(self.dry_btn)
        self.clean_btn = QPushButton("Clean Orphans")
        self.clean_btn.setObjectName("Danger")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(lambda: self._clean(dry_run=False))
        row.addWidget(self.clean_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.info = QLabel("")
        self.info.setObjectName("Muted")
        self.info.setWordWrap(True)
        self.v.addWidget(self.info)

        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels([
            "Store", "Path", "Exists", "Actual size", "Explorer sum", "Orphans", "Hardlink saved",
        ])
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        explain = Card(self.p)
        el = QVBoxLayout(explain)
        el.setContentsMargins(14, 12, 14, 12)
        lab = QLabel(
            "<b>Why hardlink-aware:</b> HF hub stores blobs by SHA and hard-links them into "
            "snapshot dirs. Explorer counts each link, so 3 revisions sharing a 2GB shard report 6GB. "
            "Unique-inode sum is the real disk use.<br>"
            "<b>Safe cleanup:</b> Only orphan blobs (no snapshot link, *.incomplete) via the owning "
            "tool's CLI (model-warden rule) – manual rm corrupts multiple revisions.<br>"
            "<b>Space lever:</b> Quantize FP16→Q4_K_M before archiving (75% saving per Interconnectd; 70B 140GB→38GB)."
        )
        lab.setObjectName("Muted")
        lab.setWordWrap(True)
        el.addWidget(lab)
        self.v.addWidget(explain)

        self._stores: list = []
        self._autoload = self._scan
        self._loaded = False

    def _scan(self):
        """_scan.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
        """
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.state.show_loading("Scanning model caches…")
        self.win.statusBar().showMessage("Scanning HF hub / Ollama / LM Studio…")
        self.win.run_worker(_ScanWorker(), self._on_scan, self._fail)

    def _on_scan(self, stores):
        """_on_scan.

        Manages on scan operations and coordinates related state changes for the component.

        Args:
            stores: The stores parameter.
        """
        self.scan_btn.setEnabled(True)
        self._stores = stores
        if not stores or not any(getattr(s, "exists", False) for s in stores):
            self.state.show_empty("No model caches found (HF hub, Ollama, LM Studio, ComfyUI). Install a model first.")
            self.info.setText("No caches detected. Hugging Face hub at ~/.cache/huggingface/hub, Ollama at ~/.ollama/models.")
            self.tbl.setRowCount(0)
            return
        self.state.clear()
        self.tbl.setRowCount(len(stores))
        total_actual = 0
        total_orphan = 0
        has_orphan = False
        for r, s in enumerate(stores):
            # s may be ModelStore dataclass
            kind = getattr(s, "kind", "?")
            root = str(getattr(s, "root", ""))
            exists = "yes" if getattr(s, "exists", False) else "no"
            actual = getattr(s, "total_bytes_actual", 0)
            logical = getattr(s, "total_bytes_logical", 0)
            orphan = getattr(s, "orphan_bytes", 0)
            orphan_c = getattr(s, "orphan_count", 0)
            saved = getattr(s, "hardlink_savings", 0)
            total_actual += actual if getattr(s, "exists", False) else 0
            total_orphan += orphan
            if orphan > 0:
                has_orphan = True
            self.tbl.setItem(r, 0, QTableWidgetItem(kind))
            path_item = QTableWidgetItem(root)
            path_item.setToolTip(root)
            self.tbl.setItem(r, 1, path_item)
            self.tbl.setItem(r, 2, QTableWidgetItem(exists))
            self.tbl.setItem(r, 3, QTableWidgetItem(fmt_bytes(actual) if actual else "—"))
            self.tbl.setItem(r, 4, QTableWidgetItem(fmt_bytes(logical) if logical else "—"))
            self.tbl.setItem(r, 5, QTableWidgetItem(f"{orphan_c} ({fmt_bytes(orphan)})" if orphan else "0"))
            self.tbl.setItem(r, 6, QTableWidgetItem(fmt_bytes(saved) if saved else "—"))
        self.info.setText(
            f"{len([s for s in stores if getattr(s,'exists',False)])} store(s), "
            f"{fmt_bytes(total_actual)} actual disk (hardlink-aware). "
            f"Orphans: {fmt_bytes(total_orphan)} – safe via Preview/Clean. "
            f"FP16→Q4_K_M would save ~{fmt_bytes(int(total_actual*0.75))} if archiving FP16."
        )
        self.clean_btn.setEnabled(has_orphan)
        self.dry_btn.setEnabled(has_orphan)
        self.win.statusBar().showMessage(f"Model caches: {fmt_bytes(total_actual)} actual, {fmt_bytes(total_orphan)} orphans", 6000)

    def _clean(self, dry_run: bool):
        """_clean.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            dry_run (bool): The dry run parameter.
        """
        hf_store = next((s for s in self._stores if getattr(s, "kind", "") == "hf"), None)
        if not hf_store or not getattr(hf_store, "orphan_count", 0):
            QMessageBox.information(self, "No orphans", "No HF orphan blobs to clean. Run Scan first.")
            return
        if not dry_run:
            confirm = QMessageBox.question(
                self, "Clean HF orphans?",
                f"Remove {getattr(hf_store,'orphan_count',0)} orphan blobs (~{fmt_bytes(getattr(hf_store,'orphan_bytes',0))}) "
                "via ‘huggingface-cli delete-cache --orphans’? This only touches interrupted downloads (*.incomplete) "
                "with no snapshot link – verified safe (model-warden rule).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        self.progress.setVisible(True)
        self.scan_btn.setEnabled(False)
        self.win.statusBar().showMessage("Cleaning HF orphans…" if not dry_run else "Previewing orphan cleanup…")
        self.win.run_worker(_CleanOrphansWorker(dry_run), self._on_clean, self._fail)

    def _on_clean(self, ok: bool, msg: str, freed: int):
        """_on_clean.

        Manages on clean operations and coordinates related state changes for the component.

        Args:
            ok (bool): The ok parameter.
            msg (str): Informational or progress status message.
            freed (int): The freed parameter.
        """
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        if ok:
            QMessageBox.information(self, "Orphan cleanup" if freed or "Dry-run" in msg else "Preview", msg)
            self.win.statusBar().showMessage(msg, 8000)
        else:
            QMessageBox.warning(self, "Cleanup failed", msg)
        self._scan()

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self.scan_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.state.show_error(msg, on_retry=self._scan)
