"""Cloud Storage Analyzer — S3, Azure, Google Drive, OneDrive, rclone.

Research: Unified cloud enumeration via provider APIs and rclone (40+ backends).
Live pricing from AWS Price List Query API and Azure Retail Prices API.
Finds duplicates across cloud + local via etag/hash comparison.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .widgets import Card, StatCard, title_block, status_note
from .window import _Page, fmt_bytes
from .states import StatePanel
from cortex_unified.analyzers.cloud_storage_analyzer import (
    CloudStorageAnalyzer,
    CloudScanStats,
    CloudFileEntry,
    DuplicateGroup,
)


@dataclass(slots=True)
class _WorkerResult:
    """_WorkerResult class."""
    entries: list[CloudFileEntry]
    stats: CloudScanStats
    duplicates: list[DuplicateGroup]


class _CloudWorker(QObject):
    """_CloudWorker class."""
    finished = Signal(_WorkerResult)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        target: str,
        max_objects: int,
        include_versions: bool,
        include_delete_markers: bool,
    ):
        """Initialize worker."""
        super().__init__()
        self._target = target
        self._max_objects = max_objects
        self._include_versions = include_versions
        self._include_delete_markers = include_delete_markers
        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            analyzer = CloudStorageAnalyzer(cancel_event=self._cancel)
            entries, stats = analyzer.scan_sync(
                self._target,
                max_objects=self._max_objects,
                progress_cb=lambda cur, tot, msg: self.progress.emit(msg),
            )
            duplicates = analyzer.find_duplicates(entries)
            self.finished.emit(_WorkerResult(entries, stats, duplicates))
        except Exception as exc:
            self.failed.emit(str(exc))


class CloudStoragePage(_Page):
    """Analyze cloud storage (S3, Azure, GDrive, OneDrive, rclone)."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(
            title_block(
                "Cloud Storage Analyzer",
                "S3 / Azure / Google Drive / OneDrive / rclone — live pricing, "
                "duplicate detection, cost optimization.",
            )
        )

        picker = QHBoxLayout()
        pick_btn = QPushButton("Pick Target…")
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.addItems(
            [
                "s3://bucket/prefix",
                "azure://container/prefix",
                "gdrive://root/folder",
                "onedrive://me/drive/folder",
                "rclone://remote/path",
            ]
        )
        self.target_combo.setMinimumWidth(300)
        self.run_btn = QPushButton("Analyze")
        self.run_btn.setObjectName("Primary")
        self.max_spin = QSpinBox()
        self.max_spin.setRange(100, 1000000)
        self.max_spin.setValue(10000)
        self.max_spin.setToolTip("Maximum objects to enumerate")
        self.ver_chk = QCheckBox("Include versions (S3)")
        self.ver_chk.setToolTip(
            "Enumerate non-current object versions (billable storage)"
        )
        self.del_chk = QCheckBox("Include delete markers (S3)")
        self.del_chk.setToolTip("Include S3 delete markers in scan")

        pick_btn.clicked.connect(self._refresh_targets)
        self.run_btn.clicked.connect(self._run)

        picker.addWidget(pick_btn)
        picker.addWidget(self.target_combo, 1)
        picker.addWidget(QLabel("Max objects:"))
        picker.addWidget(self.max_spin)
        picker.addWidget(self.ver_chk)
        picker.addWidget(self.del_chk)
        picker.addWidget(self.run_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.summary_tab = QWidget()
        self._build_summary_tab()
        self.tabs.addTab(self.summary_tab, "Summary")

        self.by_provider_tab = QWidget()
        self._build_by_provider_tab()
        self.tabs.addTab(self.by_provider_tab, "By Provider")

        self.by_class_tab = QWidget()
        self._build_by_class_tab()
        self.tabs.addTab(self.by_class_tab, "By Storage Class")

        self.dup_tab = QWidget()
        self._build_duplicates_tab()
        self.tabs.addTab(self.dup_tab, "Duplicates")

        self.v.addWidget(self.tabs, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tabs)
        self.v.addWidget(self.state, 1)

        self._worker = None
        self._entries: list[CloudFileEntry] = []
        self._stats: CloudScanStats | None = None
        self._duplicates: list[DuplicateGroup] = []

    def _build_summary_tab(self):
        """_build_summary_tab."""
        lay = QVBoxLayout(self.summary_tab)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self.stat_total_objects = StatCard(self.p, "Total Objects", "—")
        self.stat_total_size = StatCard(self.p, "Total Size", "—")
        self.stat_monthly_cost = StatCard(self.p, "Est. Monthly Cost", "—")
        self.stat_wasted = StatCard(self.p, "Wasted (Dupes)", "—")

        cards_row.addWidget(self.stat_total_objects, 1)
        cards_row.addWidget(self.stat_total_size, 1)
        cards_row.addWidget(self.stat_monthly_cost, 1)
        cards_row.addWidget(self.stat_wasted, 1)
        lay.addLayout(cards_row)

        self.unpriced_note = QLabel("")
        self.unpriced_note.setObjectName("Muted")
        self.unpriced_note.setWordWrap(True)
        lay.addWidget(self.unpriced_note)

        self.provider_breakdown = QTableWidget(0, 3)
        self.provider_breakdown.setHorizontalHeaderLabels(
            ["Provider", "Objects", "Size"]
        )
        self.provider_breakdown.horizontalHeader().setStretchLastSection(True)
        self.provider_breakdown.verticalHeader().setVisible(False)
        self.provider_breakdown.setAlternatingRowColors(True)
        self.provider_breakdown.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.provider_breakdown, 1)

    def _build_by_provider_tab(self):
        """_build_by_provider_tab."""
        lay = QVBoxLayout(self.by_provider_tab)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.provider_tbl = QTableWidget(0, 4)
        self.provider_tbl.setHorizontalHeaderLabels(
            ["Provider", "Objects", "Size", "Est. Cost/mo"]
        )
        self.provider_tbl.horizontalHeader().setStretchLastSection(True)
        self.provider_tbl.verticalHeader().setVisible(False)
        self.provider_tbl.setAlternatingRowColors(True)
        self.provider_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.provider_tbl, 1)

    def _build_by_class_tab(self):
        """_build_by_class_tab."""
        lay = QVBoxLayout(self.by_class_tab)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.class_tbl = QTableWidget(0, 5)
        self.class_tbl.setHorizontalHeaderLabels(
            ["Storage Class", "Provider", "Objects", "Size (GB)", "Est. Cost/mo"]
        )
        self.class_tbl.horizontalHeader().setStretchLastSection(True)
        self.class_tbl.verticalHeader().setVisible(False)
        self.class_tbl.setAlternatingRowColors(True)
        self.class_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.class_tbl, 1)

    def _build_duplicates_tab(self):
        """_build_duplicates_tab."""
        lay = QVBoxLayout(self.dup_tab)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.dup_tbl = QTableWidget(0, 6)
        self.dup_tbl.setHorizontalHeaderLabels(
            [
                "Hash",
                "Object Size",
                "Cloud Copies",
                "Local Copies",
                "Wasted Space",
                "Paths",
            ]
        )
        self.dup_tbl.horizontalHeader().setStretchLastSection(True)
        self.dup_tbl.verticalHeader().setVisible(False)
        self.dup_tbl.setAlternatingRowColors(True)
        self.dup_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.dup_tbl, 1)

    def _refresh_targets(self):
        """_refresh_targets."""
        analyzer = CloudStorageAnalyzer()
        targets = analyzer.available_targets()
        self.target_combo.clear()
        for provider, items in targets.items():
            for item in items:
                self.target_combo.addItem(item)
        if self.target_combo.count() == 0:
            self.target_combo.addItems(
                [
                    "s3://bucket/prefix",
                    "azure://container/prefix",
                    "gdrive://root/folder",
                    "onedrive://me/drive/folder",
                    "rclone://remote/path",
                ]
            )
        self.status.setText(
            f"Found {sum(len(v) for v in targets.values())} targets across {len(targets)} providers"
        )

    def _run(self):
        """_run."""
        target = self.target_combo.currentText().strip()
        if not target:
            self.state.show_error("Select or enter a cloud target to analyze.")
            return
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Scanning cloud storage…")
        self.status.setText(f"Scanning {target}…")
        self.provider_breakdown.setRowCount(0)
        self.provider_tbl.setRowCount(0)
        self.class_tbl.setRowCount(0)
        self.dup_tbl.setRowCount(0)
        self.stat_total_objects.set_value("—")
        self.stat_total_size.set_value("—")
        self.stat_monthly_cost.set_value("—")
        self.stat_wasted.set_value("—")
        self.unpriced_note.setText("")

        w = _CloudWorker(
            target,
            max_objects=self.max_spin.value(),
            include_versions=self.ver_chk.isChecked(),
            include_delete_markers=self.del_chk.isChecked(),
        )
        self._worker = w
        self.win.run_worker(w, self._on_done, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """_on_progress."""
        self.status.setText(msg)

    def _on_done(self, result: _WorkerResult):
        """_on_done."""
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self._entries = result.entries
        self._stats = result.stats
        self._duplicates = result.duplicates

        if not result.entries:
            self.state.show_empty(
                "No objects found. Check credentials, target path, and permissions."
            )
            self.status.setText("No objects found.")
            self.win.statusBar().showMessage("No objects found", 5000)
            return

        self.state.clear()
        self._populate_summary(result.stats)
        self._populate_by_provider(result.stats)
        self._populate_by_class(result.stats)
        self._populate_duplicates(result.duplicates)

        wasted = sum(g.wasted_bytes for g in result.duplicates)
        self.status.setText(
            f"{result.stats.total_objects:,} objects, "
            f"{fmt_bytes(result.stats.total_size_bytes)}, "
            f"${result.stats.estimated_monthly_cost_usd:,.2f}/mo, "
            f"{len(result.duplicates)} dup groups ({fmt_bytes(wasted)} wasted)"
        )
        self.win.statusBar().showMessage(
            f"{result.stats.total_objects:,} objects, ${result.stats.estimated_monthly_cost_usd:,.2f}/mo",
            5000,
        )

    def _fail(self, msg: str):
        """_fail."""
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)

    def _populate_summary(self, stats: CloudScanStats):
        """_populate_summary."""
        self.stat_total_objects.set_value(f"{stats.total_objects:,}", animate=True)
        self.stat_total_size.set_value(fmt_bytes(stats.total_size_bytes), animate=True)
        self.stat_monthly_cost.set_value(
            f"${stats.estimated_monthly_cost_usd:,.2f}/mo", animate=True
        )
        wasted = sum(g.wasted_bytes for g in self._duplicates)
        self.stat_wasted.set_value(fmt_bytes(wasted), animate=True)

        if stats.unpriced_classes:
            unpriced = ", ".join(sorted(stats.unpriced_classes))
            self.unpriced_note.setText(
                f"Note: No live pricing available for: {unpriced}. "
                "Costs shown are for priced classes only."
            )
        else:
            self.unpriced_note.setText(
                "All storage classes priced from live vendor APIs."
            )

        self.provider_breakdown.setRowCount(len(stats.by_provider))
        for r, (prov, count) in enumerate(
            sorted(stats.by_provider.items(), key=lambda x: -x[1])
        ):
            size = sum(e.size for e in self._entries if e.provider == prov)
            self.provider_breakdown.setItem(r, 0, QTableWidgetItem(prov))
            self.provider_breakdown.setItem(r, 1, QTableWidgetItem(f"{count:,}"))
            self.provider_breakdown.setItem(r, 2, QTableWidgetItem(fmt_bytes(size)))

    def _populate_by_provider(self, stats: CloudScanStats):
        """_populate_by_provider."""
        analyzer = CloudStorageAnalyzer()
        self.provider_tbl.setRowCount(len(stats.by_provider))
        for r, (prov, count) in enumerate(
            sorted(stats.by_provider.items(), key=lambda x: -x[1])
        ):
            provider = analyzer.get_provider(prov)
            size = sum(e.size for e in self._entries if e.provider == prov)
            cost = provider.estimate_cost(stats) if provider else 0.0
            self.provider_tbl.setItem(r, 0, QTableWidgetItem(prov))
            self.provider_tbl.setItem(r, 1, QTableWidgetItem(f"{count:,}"))
            self.provider_tbl.setItem(r, 2, QTableWidgetItem(fmt_bytes(size)))
            self.provider_tbl.setItem(r, 3, QTableWidgetItem(f"${cost:,.2f}"))

    def _populate_by_class(self, stats: CloudScanStats):
        """_populate_by_class."""
        from collections import defaultdict

        obj_per_class: dict[str, int] = defaultdict(int)
        prov_for_class: dict[str, str] = {}
        for e in self._entries:
            obj_per_class[e.storage_class] += 1
            prov_for_class.setdefault(e.storage_class, e.provider)

        analyzer = CloudStorageAnalyzer()
        rows = []
        for cls, byte_count in sorted(
            stats.by_storage_class.items(), key=lambda kv: -kv[1]
        ):
            gb = byte_count / (1024**3)
            provider = analyzer.get_provider(prov_for_class.get(cls, ""))
            rate = None
            if provider and provider.pricing_key and provider.region:
                from cortex_unified.analyzers.cloud_storage_analyzer import _PRICING

                rate = _PRICING.rate(provider.pricing_key, provider.region, cls)
            cost = gb * rate if rate is not None else 0.0
            cost_str = f"${cost:,.2f}" if rate is not None else "unknown"
            rows.append(
                (
                    cls,
                    prov_for_class.get(cls, ""),
                    obj_per_class.get(cls, 0),
                    f"{gb:,.2f}",
                    cost_str,
                )
            )

        self.class_tbl.setRowCount(len(rows))
        for r, (cls, prov, obj_count, gb, cost) in enumerate(rows):
            self.class_tbl.setItem(r, 0, QTableWidgetItem(cls))
            self.class_tbl.setItem(r, 1, QTableWidgetItem(prov))
            self.class_tbl.setItem(r, 2, QTableWidgetItem(f"{obj_count:,}"))
            self.class_tbl.setItem(r, 3, QTableWidgetItem(gb))
            self.class_tbl.setItem(r, 4, QTableWidgetItem(cost))

    def _populate_duplicates(self, duplicates: list[DuplicateGroup]):
        """_populate_duplicates."""
        if not duplicates:
            return
        self.dup_tbl.setRowCount(min(len(duplicates), 500))
        for r, g in enumerate(duplicates[:500]):
            paths = "; ".join(e.path for e in g.entries[:3])
            if len(g.entries) > 3:
                paths += f" … (+{len(g.entries) - 3} more)"
            self.dup_tbl.setItem(r, 0, QTableWidgetItem(g.hash[:24]))
            self.dup_tbl.setItem(r, 1, QTableWidgetItem(fmt_bytes(g.size)))
            self.dup_tbl.setItem(r, 2, QTableWidgetItem(str(len(g.entries))))
            self.dup_tbl.setItem(r, 3, QTableWidgetItem(str(len(g.local_paths))))
            self.dup_tbl.setItem(r, 4, QTableWidgetItem(fmt_bytes(g.wasted_bytes)))
            self.dup_tbl.setItem(r, 5, QTableWidgetItem(paths))
