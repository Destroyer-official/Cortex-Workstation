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
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
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
from cortex_unified.explorer.cloud import CloudManager, CloudProviderType, CloudFile


@dataclass(slots=True)
class _WorkerResult:
    """Workerresult.

    Manages WorkerResult operations and coordinates related state changes for the component.
    """
    entries: list[CloudFileEntry]
    stats: CloudScanStats
    duplicates: list[DuplicateGroup]


class _CloudWorker(QObject):
    """Cloudworker.

    Manages CloudWorker operations and coordinates related state changes for the component.
    """
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
        """Initialize worker.

        Initializes the instance and configures internal state.

        Args:
            target (str): The target parameter.
            max_objects (int): The max objects parameter.
            include_versions (bool): The include versions parameter.
            include_delete_markers (bool): The include delete markers parameter.
        """
        super().__init__()
        self._target = target
        self._max_objects = max_objects
        self._include_versions = include_versions
        self._include_delete_markers = include_delete_markers
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
    """Cloudstoragepage.

    Manages CloudStoragePage operations and coordinates related state changes for the component.
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

        self._worker = None
        self._entries: list[CloudFileEntry] = []
        self._stats: CloudScanStats | None = None
        self._duplicates: list[DuplicateGroup] = []
        self._cloud_mgr = CloudManager()
        self._active_provider: CloudProviderType | None = CloudProviderType.S3

        self.providers_tab = QWidget()
        self._build_providers_tab()
        self.tabs.addTab(self.providers_tab, "Providers")

        self.v.addWidget(self.tabs, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tabs)
        self.v.addWidget(self.state, 1)

    def _build_summary_tab(self):
        """_build_summary_tab.

        Manages build summary tab operations and coordinates related state changes for the component.
        """
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
        """_build_by_provider_tab.

        Manages build by provider tab operations and coordinates related state changes for the component.
        """
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
        """_build_by_class_tab.

        Manages build by class tab operations and coordinates related state changes for the component.
        """
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
        """_build_duplicates_tab.

        Manages build duplicates tab operations and coordinates related state changes for the component.
        """
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
        """_refresh_targets.

        Manages refresh targets operations and coordinates related state changes for the component.
        """
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
        """Run.

        Manages run operations and coordinates related state changes for the component.
        """
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
        """_on_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            msg (str): Informational or progress status message.
        """
        self.status.setText(msg)

    def _on_done(self, result: _WorkerResult):
        """_on_done.

        Receives the completed data from the  background worker, populates the view with results, and restores button states.

        Args:
            result (_WorkerResult): Dictionary or data object holding operation results.
        """
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
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.

        Args:
            msg (str): Informational or progress status message.
        """
        self._worker = None
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)

    def _populate_summary(self, stats: CloudScanStats):
        """_populate_summary.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.

        Args:
            stats (CloudScanStats): The stats parameter.
        """
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
        """_populate_by_provider.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.

        Args:
            stats (CloudScanStats): The stats parameter.
        """
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
        """_populate_by_class.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.

        Args:
            stats (CloudScanStats): The stats parameter.
        """
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
        """_populate_duplicates.

        Refreshes table or tree items with formatted values, tooltips, and status indicators based on the provided dataset.

        Args:
            duplicates (list[DuplicateGroup]): The duplicates parameter.
        """
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

    def _build_providers_tab(self):
        """Build the interactive Cloud Providers tab with connect/disconnect/browse actions.

        Manages build providers tab operations and coordinates related state changes for the component.
        """
        lay = QVBoxLayout(self.providers_tab)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # 1. Providers Card
        prov_card = Card(self.p, "Active Cloud Accounts & Providers")
        pc_lay = QVBoxLayout(prov_card)
        pc_lay.setContentsMargins(18, 14, 18, 14)
        pc_lay.setSpacing(10)

        header_desc = QLabel("Configure, authenticate, and connect native cloud providers (OneDrive, Google Drive, Dropbox, Amazon S3).")
        header_desc.setObjectName("Muted")
        pc_lay.addWidget(header_desc)

        self.providers_table = QTableWidget(0, 4)
        self.providers_table.setHorizontalHeaderLabels(["Provider", "Protocol / Service", "Status", "Actions"])
        self.providers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.providers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.providers_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.providers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.providers_table.verticalHeader().setVisible(False)
        self.providers_table.setAlternatingRowColors(True)
        self.providers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.providers_table.setMinimumHeight(160)
        pc_lay.addWidget(self.providers_table)
        lay.addWidget(prov_card)

        # 2. File Browser Card
        browser_card = Card(self.p, "Cloud File Explorer")
        bc_lay = QVBoxLayout(browser_card)
        bc_lay.setContentsMargins(18, 14, 18, 14)
        bc_lay.setSpacing(10)

        nav_row = QHBoxLayout()
        self.cloud_provider_label = QLabel("Provider: Amazon S3")
        self.cloud_provider_label.setObjectName("PrimaryText")
        nav_row.addWidget(self.cloud_provider_label)

        self.cloud_path_input = QLineEdit()
        self.cloud_path_input.setPlaceholderText("Enter remote path / prefix (e.g. / or bucket/prefix)…")
        self.cloud_path_input.setText("/")
        nav_row.addWidget(self.cloud_path_input, 1)

        self.cloud_browse_btn = QPushButton("Browse")
        self.cloud_browse_btn.setObjectName("Primary")
        self.cloud_browse_btn.clicked.connect(self._on_browse_cloud_path)
        nav_row.addWidget(self.cloud_browse_btn)

        self.cloud_download_btn = QPushButton("Download Selected…")
        self.cloud_download_btn.setObjectName("Ghost")
        self.cloud_download_btn.clicked.connect(self._on_download_cloud_file)
        nav_row.addWidget(self.cloud_download_btn)

        bc_lay.addLayout(nav_row)

        self.cloud_files_table = QTableWidget(0, 5)
        self.cloud_files_table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Remote Path", "Sync Status"])
        self.cloud_files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cloud_files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.cloud_files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cloud_files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.cloud_files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.cloud_files_table.verticalHeader().setVisible(False)
        self.cloud_files_table.setAlternatingRowColors(True)
        self.cloud_files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cloud_files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cloud_files_table.cellDoubleClicked.connect(self._on_cloud_file_double_clicked)
        bc_lay.addWidget(self.cloud_files_table, 1)

        lay.addWidget(browser_card, 1)

        self._init_providers_table()

    def _init_providers_table(self):
        """Populate the cloud providers table with connect/disconnect/browse controls.

        Manages init providers table operations and coordinates related state changes for the component.
        """
        providers = [
            (CloudProviderType.ONEDRIVE, "Microsoft OneDrive", "Microsoft Graph API"),
            (CloudProviderType.GOOGLE_DRIVE, "Google Drive", "Google Drive API v3"),
            (CloudProviderType.DROPBOX, "Dropbox", "Dropbox v2 REST API"),
            (CloudProviderType.S3, "Amazon S3", "AWS S3 / Boto3 SDK"),
        ]

        self.providers_table.setRowCount(len(providers))
        for r, (pt, name, proto) in enumerate(providers):
            self.providers_table.setItem(r, 0, QTableWidgetItem(name))
            self.providers_table.setItem(r, 1, QTableWidgetItem(proto))

            p = self._cloud_mgr.get_provider(pt)
            is_conn = p.is_authenticated() if p else False
            status_item = QTableWidgetItem("Connected" if is_conn else "Disconnected")
            self.providers_table.setItem(r, 2, status_item)

            # Action buttons
            actions_widget = QWidget()
            aw_lay = QHBoxLayout(actions_widget)
            aw_lay.setContentsMargins(4, 2, 4, 2)
            aw_lay.setSpacing(6)

            conn_btn = QPushButton("Connect")
            conn_btn.setObjectName("Ghost")
            conn_btn.clicked.connect(lambda _, _pt=pt: self._connect_provider(_pt))
            aw_lay.addWidget(conn_btn)

            disc_btn = QPushButton("Disconnect")
            disc_btn.setObjectName("Ghost")
            disc_btn.clicked.connect(lambda _, _pt=pt: self._disconnect_provider(_pt))
            aw_lay.addWidget(disc_btn)

            browse_btn = QPushButton("Browse")
            browse_btn.setObjectName("Primary")
            browse_btn.clicked.connect(lambda _, _pt=pt: self._select_provider_for_browse(_pt))
            aw_lay.addWidget(browse_btn)

            self.providers_table.setCellWidget(r, 3, actions_widget)

    def _connect_provider(self, pt: CloudProviderType):
        """Attempt connection to selected provider.

        Manages connect provider operations and coordinates related state changes for the component.

        Args:
            pt (CloudProviderType): The pt parameter.
        """
        ok = self._cloud_mgr.connect_provider(pt)
        self._init_providers_table()
        if ok:
            QMessageBox.information(self, "Cloud Connected", f"Successfully connected to {pt.name}.")
        else:
            QMessageBox.warning(
                self,
                "Authentication Notice",
                f"Could not connect to {pt.name}. Please ensure API tokens or credentials are set in environment variables or configuration."
            )

    def _disconnect_provider(self, pt: CloudProviderType):
        """Disconnect provider.

        Manages disconnect provider operations and coordinates related state changes for the component.

        Args:
            pt (CloudProviderType): The pt parameter.
        """
        self._cloud_mgr.disconnect_provider(pt)
        self._init_providers_table()
        self.status.setText(f"Disconnected from {pt.name}.")

    def _select_provider_for_browse(self, pt: CloudProviderType):
        """Select provider and browse remote path.

        Manages select provider for browse operations and coordinates related state changes for the component.

        Args:
            pt (CloudProviderType): The pt parameter.
        """
        self._active_provider = pt
        self.cloud_provider_label.setText(f"Provider: {pt.name}")
        self._on_browse_cloud_path()

    def _on_browse_cloud_path(self):
        """Browse files in current provider path.

        Manages on browse cloud path operations and coordinates related state changes for the component.
        """
        if not self._active_provider:
            self._active_provider = CloudProviderType.S3
        p = self._cloud_mgr.get_provider(self._active_provider)
        if not p:
            QMessageBox.warning(self, "Provider Error", "Selected provider is not available.")
            return

        path = self.cloud_path_input.text().strip() or "/"
        self.status.setText(f"Listing files in {self._active_provider.name}:{path}…")

        def work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            try:
                return p.list_files(path)
            except Exception as e:
                return str(e)

        def done(res):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                res: The res parameter.
            """
            if isinstance(res, str):
                self.status.setText(f"Listing error: {res}")
                return
            files = res or []
            self.cloud_files_table.setRowCount(len(files))
            for r, f in enumerate(files):
                self.cloud_files_table.setItem(r, 0, QTableWidgetItem(f.name))
                self.cloud_files_table.setItem(r, 1, QTableWidgetItem("Folder" if f.is_dir else "File"))
                self.cloud_files_table.setItem(r, 2, QTableWidgetItem(fmt_bytes(f.size) if not f.is_dir else "—"))
                self.cloud_files_table.setItem(r, 3, QTableWidgetItem(f.path))
                status_str = getattr(f.sync_status, "value", str(f.sync_status))
                self.cloud_files_table.setItem(r, 4, QTableWidgetItem(status_str))

            self.status.setText(f"Found {len(files)} item(s) in {self._active_provider.name}:{path}")

        if hasattr(self.win, "worker_runtime"):
            self.win.worker_runtime.run(work, on_result=done)
        else:
            done(work())

    def _on_download_cloud_file(self):
        """Download selected cloud file.

        Manages on download cloud file operations and coordinates related state changes for the component.
        """
        row = self.cloud_files_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selection Required", "Please select a file to download.")
            return
        path_item = self.cloud_files_table.item(row, 3)
        remote_path = path_item.text() if path_item else ""
        if not remote_path:
            return

        dest_dir = QFileDialog.getExistingDirectory(self, "Select Download Destination")
        if not dest_dir:
            return

        p = self._cloud_mgr.get_provider(self._active_provider)
        if p and hasattr(p, "download"):
            local_dest = str(Path(dest_dir) / Path(remote_path).name)
            ok = p.download(remote_path, local_dest)
            if ok:
                QMessageBox.information(self, "Download Complete", f"Downloaded to:\n{local_dest}")
            else:
                QMessageBox.warning(self, "Download Notice", "Download could not complete or provider is unauthenticated.")

    def _on_cloud_file_double_clicked(self, row, col):
        """Navigate into folder on double click.

        Manages on cloud file double clicked operations and coordinates related state changes for the component.

        Args:
            row: Table row index or list of row indices.
            col: The col parameter.
        """
        type_item = self.cloud_files_table.item(row, 1)
        if type_item and type_item.text() == "Folder":
            path_item = self.cloud_files_table.item(row, 3)
            if path_item:
                self.cloud_path_input.setText(path_item.text())
                self._on_browse_cloud_path()
