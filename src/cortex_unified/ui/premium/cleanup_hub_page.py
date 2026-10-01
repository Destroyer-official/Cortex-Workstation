"""Cleanup Hub: unified one-click full-device view of all cleanup categories.

A state-of-the-art, storage sense-style central hub that provides upfront target
selection (Full Device, System Drive, or Custom Folder/File), real-time traversal
telemetry, itemized file origin inspection, and one-click reversible cleanup.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.engine import CleanerService, RiskLevel
from cortex_unified.engine.categories import CleanupCategory, default_categories

from .states import StatePanel
from .widgets import Card, StatCard, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = sys.platform == "win32"

_CATEGORY_ICONS = {
    "windows_temp": "🔥",
    "user_temp": "🔥",
    "deep_temp": "🔥",
    "update_cache": "🔄",
    "delivery_opt": "🚀",
    "prefetch": "⚡",
    "wer_reports": "📋",
    "recent_files": "🕒",
    "thumbnail_cache": "🖼️",
    "browser_caches": "🌐",
    "docker_cache": "🐳",
    "wsl_vhdx": "🐧",
    "rustup_toolchains": "🦀",
    "cargo_cache": "📦",
    "npm_cache": "📦",
    "pip_cache": "🐍",
    "custom_build_caches": "🛠️",
    "custom_temp_files": "📄",
    "custom_log_files": "📜",
    "custom_cruft_files": "🧹",
    "custom_empty_files": "📁",
}


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------


class HubScanWorker(QObject):
    """Scans all cleanup categories via CleanerService.

    Emits ``finished`` with a CleanupReport, ``progress`` with status text,
    or ``failed`` with an error message.
    """

    finished = Signal(object)  # CleanupReport
    progress = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        max_risk: str = "medium",
        include_disabled: bool = True,
        custom_roots: list[Path] | None = None,
    ):
        """Store max-risk level, disabled-category flag, custom roots, and a cancel event.

        Args:
            max_risk (str): The max risk parameter.
            include_disabled (bool): The include disabled parameter.
            custom_roots (list[Path] | None): Optional custom target paths to scan.
        """
        super().__init__()
        self._max_risk = max_risk
        self._include_disabled = include_disabled
        self._custom_roots = custom_roots
        import threading

        self._cancel = threading.Event()

    def cancel(self):
        """Request cooperative cancellation of the running scan."""
        self._cancel.set()

    def run(self):
        """Run the category scan or custom root scan and emit the report or a failure."""
        try:
            if self._custom_roots:
                svc = CleanerService()
                report = svc.scan_custom_roots(
                    roots=self._custom_roots,
                    progress=self.progress.emit,
                    cancel_event=self._cancel,
                )
            else:
                from cortex_unified.engine.guard import PathGuard

                svc = CleanerService(guard=PathGuard(allow_system=True))
                report = svc.scan_categories(
                    max_risk=RiskLevel(self._max_risk),
                    include_disabled=self._include_disabled,
                    progress=self.progress.emit,
                    cancel_event=self._cancel,
                )
            self.finished.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TempScanWorker(QObject):
    """Scans stale temp files via TempCleaner (core/temp_cleaner.py).

    Emits ``finished`` with a list of TempFinding, ``progress`` with status
    text, or ``failed`` with an error message.
    """

    finished = Signal(object)  # list[TempFinding]
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, min_age_days: int = 1):
        """Store the age floor and a cancel event."""
        super().__init__()
        self._min_age_days = min_age_days
        import threading

        self._cancel = threading.Event()

    def cancel(self):
        """Request cooperative cancellation of the running scan."""
        self._cancel.set()

    def run(self):
        """Run the stale-temp scan and emit findings or a failure."""
        try:
            from cortex_unified.core.temp_cleaner import TempCleaner

            self.progress.emit("Scanning stale temp files…")
            findings = TempCleaner(min_age_days=self._min_age_days).scan()
            if self._cancel.is_set():
                self.failed.emit("Temp scan cancelled.")
                return
            self.finished.emit(findings)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RecycleBinWorker(QObject):
    """Measures or empties the OS Recycle Bin off the UI thread.

    ``mode="measure"`` emits ``finished`` with a ``RecycleBinReport``;
    ``mode="empty"`` emits ``finished`` with a ``RecycleBinEmptyResult``.
    """

    finished = Signal(object)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, mode: str = "measure", dry_run: bool = True):
        super().__init__()
        self._mode = mode
        self._dry_run = dry_run
        import threading

        self._cancel = threading.Event()

    def cancel(self):
        """Request cooperative cancellation of the running bin operation."""
        self._cancel.set()

    def run(self):
        """Measure or empty the bin and emit the result or a failure."""
        try:
            from cortex_unified.system_tools.recycle_bin import RecycleBinManager

            mgr = RecycleBinManager()
            if self._mode == "empty" and not self._dry_run:
                self.progress.emit("Emptying Recycle Bin…")
                self.finished.emit(mgr.empty(dry_run=False))
            else:
                self.progress.emit("Measuring Recycle Bin…")
                self.finished.emit(mgr.measure())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# Risk -> badge color / label
_RISK_STYLE = {
    RiskLevel.LOW: ("LOW", "#34D399"),
    RiskLevel.MEDIUM: ("MEDIUM", "#FBBF24"),
    RiskLevel.HIGH: ("HIGH", "#FB7185"),
}


def _risk_label(risk: RiskLevel) -> str:
    """Return the display label ("LOW"/"MEDIUM"/"HIGH") for a risk level."""
    return _RISK_STYLE[risk][0]


def _risk_color(risk: RiskLevel) -> str:
    """Return the badge hex color for a risk level."""
    return _RISK_STYLE[risk][1]


# ---------------------------------------------------------------------------
# Dialog: Itemized Category Inspection
# ---------------------------------------------------------------------------


class CategoryFilesDialog(QDialog):
    """Interactive modal dialog to inspect discovered files within a cleanup category."""

    def __init__(self, parent: QWidget | None, scan, cat: CleanupCategory):
        super().__init__(parent)
        self.setWindowTitle(f"Discovered Files — {cat.label}")
        self.resize(960, 580)
        self.scan = scan
        self.cat = cat
        self._entries = list(scan.entries) if scan else []
        self._filtered = list(self._entries)

        palette = getattr(parent, "p", None)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header card
        hdr = Card(palette, "HeroCard", self) if palette else Card(self)
        h_lay = QVBoxLayout(hdr)
        h_lay.setContentsMargins(16, 14, 16, 14)
        h_lay.setSpacing(8)

        t_row = QHBoxLayout()
        icon = _CATEGORY_ICONS.get(cat.id, "💾")
        t_lbl = QLabel(f"<span style='font-size:16px;'>{icon}</span> <b>{cat.label}</b>")
        t_lbl.setTextFormat(Qt.TextFormat.RichText)
        t_row.addWidget(t_lbl)
        t_row.addStretch(1)

        risk_txt, risk_col = _risk_label(cat.risk), _risk_color(cat.risk)
        risk_lbl = QLabel(
            f"<span style='background:{risk_col}; color:#111; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:700;'>{risk_txt}</span>"
        )
        risk_lbl.setTextFormat(Qt.TextFormat.RichText)
        t_row.addWidget(risk_lbl)

        rev_lbl = QLabel(
            f"<span style='border:1px solid #4B5563; padding:2px 8px; border-radius:6px; font-size:11px;'>{'↩ Reversible' if cat.reversible else 'Irreversible'}</span>"
        )
        rev_lbl.setTextFormat(Qt.TextFormat.RichText)
        t_row.addWidget(rev_lbl)
        h_lay.addLayout(t_row)

        desc = QLabel(cat.description)
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        h_lay.addWidget(desc)

        stats_lbl = QLabel(
            f"<b>{len(self._entries):,}</b> file(s) found &middot; <b>{fmt_bytes(scan.total_bytes if scan else 0)}</b> reclaimable storage space"
        )
        stats_lbl.setTextFormat(Qt.TextFormat.RichText)
        h_lay.addWidget(stats_lbl)
        layout.addWidget(hdr)

        # Search filter
        s_row = QHBoxLayout()
        s_row.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files by name or source directory…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filter)
        s_row.addWidget(self.search_input)
        layout.addLayout(s_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["File Name", "Size", "Source Location / Path", "Last Modified"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table, 1)

        # Footer actions
        btn_row = QHBoxLayout()
        self.btn_reveal = QPushButton("Reveal in Explorer")
        self.btn_reveal.setObjectName("Ghost")
        self.btn_reveal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reveal.clicked.connect(self._reveal_selected)
        btn_row.addWidget(self.btn_reveal)
        btn_row.addStretch(1)

        self.lbl_count = QLabel(f"Showing {len(self._filtered):,} of {len(self._entries):,} files")
        self.lbl_count.setObjectName("Muted")
        btn_row.addWidget(self.lbl_count)

        btn_close = QPushButton("Close")
        btn_close.setObjectName("Primary")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._populate_table()

    def _apply_filter(self, text: str):
        query = text.strip().lower()
        if not query:
            self._filtered = list(self._entries)
        else:
            self._filtered = [
                e for e in self._entries if query in e.path.name.lower() or query in str(e.path.parent).lower()
            ]
        self._populate_table()

    def _populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._filtered))
        for row, entry in enumerate(self._filtered):
            name_item = QTableWidgetItem(entry.path.name or str(entry.path))
            name_item.setData(Qt.ItemDataRole.UserRole, str(entry.path))
            self.table.setItem(row, 0, name_item)

            sz_item = QTableWidgetItem(fmt_bytes(entry.size))
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 1, sz_item)

            loc_item = QTableWidgetItem(str(entry.path.parent))
            loc_item.setToolTip(str(entry.path))
            self.table.setItem(row, 2, loc_item)

            try:
                mod_str = datetime.fromtimestamp(entry.mtime).strftime("%Y-%m-%d %H:%M:%S")
            except (OSError, ValueError):
                mod_str = "—"
            mod_item = QTableWidgetItem(mod_str)
            self.table.setItem(row, 3, mod_item)
        self.table.setSortingEnabled(True)
        self.lbl_count.setText(f"Showing {len(self._filtered):,} of {len(self._entries):,} files")

    def _reveal_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.table.item(row, 0)
        if not item:
            return
        fp = item.data(Qt.ItemDataRole.UserRole)
        if fp and os.path.exists(fp):
            import subprocess

            subprocess.Popen(f'explorer /select,"{fp}"')
        elif fp and os.path.exists(os.path.dirname(fp)):
            import subprocess

            subprocess.Popen(f'explorer "{os.path.dirname(fp)}"')


# ---------------------------------------------------------------------------
# Page: CleanupHubPage
# ---------------------------------------------------------------------------


class CleanupHubPage(_Page):
    """Storage Sense-style hub: every CleanupCategory as a card with estimates."""

    def __init__(self, win):
        """Build the Cleanup Hub: scan controls, summary cards, findings, and tool suites."""
        super().__init__(win)

        # Header Title
        self.v.addWidget(
            title_block(
                "Cleanup Hub",
                "Unified full-device & targeted directory cleaner. "
                "Select scan target (Full Device, System Drive C:, or Custom Folder/File), preview live activity feed, "
                "and inspect itemized file origins before one-click reversible cleanup to Recycle Bin.",
            )
        )

        # Modular visual sections
        self._build_command_center()
        self._build_telemetry_feed()
        self._build_metrics_bar()
        self._build_findings_workbench()
        self._build_extra_sweeps_grid()
        self._build_mission_control_card()
        self._build_all_tools_section()

        # Operational state
        self._selected: dict[str, bool] = {}
        self._card_checkboxes: dict[str, QCheckBox] = {}
        self._card_risks: dict[str, object] = {}
        self._report = None
        self._scan_map: dict[str, object] = {}
        self._temp_findings: list = []
        self._proj_resources: list = []
        self._extra_logs: list = []
        self._large_files: list = []
        self._empty_files: list = []
        self._empty_dirs: list = []
        self._dupe_groups: dict = {}
        self._dupe_waste: int = 0
        self._bin_bytes: int = 0
        self._bin_items: int = 0
        self._bin_worker = None
        self._extra_worker = None
        self._sweep_workers: dict = {}
        self._silent_sweeps: set = set()
        self._feed_lines: list = []
        self._no_confirm: bool = False
        self._custom_roots: list[Path] = []
        self._worker = None
        self._loaded = False
        self._autoload = None

        self._build_action_footer()
        self._show_initial_ready_state()

    # -----------------------------------------------------------------------
    # Section Builders
    # -----------------------------------------------------------------------

    def _build_command_center(self):
        """Construct the Command Center card with Target Scope pills and scan triggers."""
        target_card = Card(self.p, "HeroCard")
        t_card_lay = QVBoxLayout(target_card)
        t_card_lay.setContentsMargins(18, 16, 18, 16)
        t_card_lay.setSpacing(12)

        # Header within command center
        cc_top = QHBoxLayout()
        cc_lbl = QLabel("<b>Scan Target Scope</b>")
        cc_lbl.setTextFormat(Qt.TextFormat.RichText)
        cc_top.addWidget(cc_lbl)
        cc_top.addStretch(1)

        self.include_disabled_chk = QCheckBox("Include opt-in (HIGH)")
        self.include_disabled_chk.setToolTip(
            "Also scan HIGH-risk / disabled categories (rustup toolchains, WSL vhdx). ON = true full-device sweep."
        )
        self.include_disabled_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.include_disabled_chk.setChecked(True)
        cc_top.addWidget(self.include_disabled_chk)
        t_card_lay.addLayout(cc_top)

        # Scope selector buttons row
        scope_row = QHBoxLayout()
        scope_row.setSpacing(8)

        self.btn_target_full = QPushButton("🖥️ Full Device (All Partitions)")
        self.btn_target_full.setObjectName("Primary")
        self.btn_target_full.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_target_full.setToolTip("Scan all default system caches and partitions across the entire device.")
        self.btn_target_full.clicked.connect(self._select_target_full_device)
        scope_row.addWidget(self.btn_target_full)

        self.btn_target_sys = QPushButton("💽 System Drive (C:)")
        self.btn_target_sys.setObjectName("Ghost")
        self.btn_target_sys.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_target_sys.setToolTip("Focus scan strictly on the Windows system drive.")
        self.btn_target_sys.clicked.connect(self._select_target_system_drive)
        scope_row.addWidget(self.btn_target_sys)

        self.btn_select_dir = QPushButton("📁 Choose Custom Folder…")
        self.btn_select_dir.setObjectName("Ghost")
        self.btn_select_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_dir.setToolTip("Select any custom drive or directory to scan.")
        self.btn_select_dir.clicked.connect(self._pick_custom_folder)
        scope_row.addWidget(self.btn_select_dir)

        self.btn_select_file = QPushButton("📄 Choose Custom File…")
        self.btn_select_file.setObjectName("Ghost")
        self.btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_file.setToolTip("Select a specific file or file location to inspect.")
        self.btn_select_file.clicked.connect(self._pick_custom_file)
        scope_row.addWidget(self.btn_select_file)

        scope_row.addStretch(1)
        t_card_lay.addLayout(scope_row)

        # Active target indicator + Start & Cancel buttons
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.target_roots_label = QLabel("Active Scan Roots: Full Device (System Caches • All Drives • AppData)")
        self.target_roots_label.setObjectName("Muted")
        action_bar.addWidget(self.target_roots_label, 1)

        self.btn_clear_roots = QPushButton("↺ Reset to Full Device Scan")
        self.btn_clear_roots.setObjectName("Ghost")
        self.btn_clear_roots.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_roots.setToolTip("Clear any custom folder/file target and reset to Full Device.")
        self.btn_clear_roots.setVisible(False)
        self.btn_clear_roots.clicked.connect(self._clear_custom_roots)
        action_bar.addWidget(self.btn_clear_roots)

        self.scan_btn = QPushButton("▶ Start Scan")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setToolTip("Start scanning the selected target.")
        self.scan_btn.clicked.connect(self._start_scan)
        action_bar.addWidget(self.scan_btn)

        self.btn_cancel_scan = QPushButton("✕ Cancel Scan")
        self.btn_cancel_scan.setObjectName("Danger")
        self.btn_cancel_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_scan.setToolTip("Cancel the active scanning process.")
        self.btn_cancel_scan.setVisible(False)
        self.btn_cancel_scan.clicked.connect(self._cancel_scan)
        action_bar.addWidget(self.btn_cancel_scan)

        t_card_lay.addLayout(action_bar)
        self.v.addWidget(target_card)

    def _build_telemetry_feed(self):
        """Build the live scanning telemetry console card."""
        self.scan_feed_card = Card(self.p, "HeroCard")
        sfc_lay = QVBoxLayout(self.scan_feed_card)
        sfc_lay.setContentsMargins(16, 12, 16, 12)
        sfc_lay.setSpacing(8)

        sfc_hdr = QHBoxLayout()
        sfc_title = QLabel(
            "<b>📡 Live Traversal & Execution Telemetry</b> "
            "<span style='color:#8A93A8'>— real-time directories, paths, and items analyzed</span>"
        )
        sfc_title.setTextFormat(Qt.TextFormat.RichText)
        sfc_hdr.addWidget(sfc_title)
        sfc_hdr.addStretch(1)

        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        sfc_hdr.addWidget(self.scan_status)
        sfc_lay.addLayout(sfc_hdr)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        sfc_lay.addWidget(self.progress)

        self.scan_log_text = QTextEdit()
        self.scan_log_text.setReadOnly(True)
        self.scan_log_text.setMaximumHeight(130)
        self.scan_log_text.setStyleSheet(
            "QTextEdit { font-family: 'Cascadia Mono', Consolas, monospace; font-size: 11px; "
            "background: rgba(0, 0, 0, 0.40); border-radius: 6px; padding: 6px; border: 1px solid rgba(255, 255, 255, 0.08); }"
        )
        sfc_lay.addWidget(self.scan_log_text)
        self.scan_feed_card.setVisible(False)
        self.v.addWidget(self.scan_feed_card)

    def _build_metrics_bar(self):
        """Build high-level stat summary cards."""
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        self.card_total = StatCard(self.p, "Reclaimable", "—")
        self.card_files = StatCard(self.p, "Files", "—")
        self.card_cats = StatCard(self.p, "Categories", "—")
        for c in (self.card_total, self.card_files, self.card_cats):
            summary_row.addWidget(c)
        self.v.addLayout(summary_row)

    def _build_findings_workbench(self):
        """Build the findings workbench: view switcher, selection helpers, and view stack."""
        # Workbench Toolbar Header
        bench_toolbar = QHBoxLayout()
        bench_toolbar.setSpacing(10)

        self.view_title = QLabel("<b>Findings & Discovered Storage</b>")
        self.view_title.setTextFormat(Qt.TextFormat.RichText)
        bench_toolbar.addWidget(self.view_title)

        bench_toolbar.addStretch(1)

        # Quick selection helpers
        self.btn_select_safe = QPushButton("✓ Select Safe")
        self.btn_select_safe.setObjectName("Ghost")
        self.btn_select_safe.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_safe.setToolTip("Tick all LOW + MEDIUM cards with found files. HIGH-risk stays unticked.")
        self.btn_select_safe.clicked.connect(self._select_safe_cards)
        bench_toolbar.addWidget(self.btn_select_safe)

        self.btn_select_all = QPushButton("☑ Select All")
        self.btn_select_all.setObjectName("Ghost")
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.setToolTip("Tick every card, including HIGH-risk (rustup, WSL). Use with care.")
        self.btn_select_all.clicked.connect(lambda: self._select_all_cards(True))
        bench_toolbar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("☐ Deselect All")
        self.btn_deselect_all.setObjectName("Ghost")
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.clicked.connect(lambda: self._select_all_cards(False))
        bench_toolbar.addWidget(self.btn_deselect_all)

        # View Switcher segmented buttons
        self.btn_view_cards = QPushButton("⊞ Category Cards View")
        self.btn_view_cards.setObjectName("Primary")
        self.btn_view_cards.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_cards.clicked.connect(self._switch_to_cards_view)
        bench_toolbar.addWidget(self.btn_view_cards)

        self.btn_view_table = QPushButton("☰ Itemized Files Breakdown Table")
        self.btn_view_table.setObjectName("Ghost")
        self.btn_view_table.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_table.clicked.connect(self._switch_to_table_view)
        bench_toolbar.addWidget(self.btn_view_table)

        self.v.addLayout(bench_toolbar)

        # View Stack: Cards View & Table View
        self.view_stack = QStackedWidget()

        # Page 0: Cards View (Scrollable Grid)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        holder = QWidget()
        self.grid = QGridLayout(holder)
        self.grid.setContentsMargins(4, 8, 4, 8)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(holder)
        self.attach_single_scroll(self.scroll)
        self.view_stack.addWidget(self.scroll)

        # Page 1: All Files Table View
        self.all_files_widget = QWidget()
        af_lay = QVBoxLayout(self.all_files_widget)
        af_lay.setContentsMargins(0, 4, 0, 4)
        af_lay.setSpacing(8)

        af_filter_row = QHBoxLayout()
        self.all_files_filter = QLineEdit()
        self.all_files_filter.setPlaceholderText("Filter itemized files by name, parent directory, or category…")
        self.all_files_filter.setClearButtonEnabled(True)
        self.all_files_filter.textChanged.connect(self._filter_all_files_table)
        af_filter_row.addWidget(self.all_files_filter)

        self.btn_reveal_table_item = QPushButton("Reveal in Explorer")
        self.btn_reveal_table_item.setObjectName("Ghost")
        self.btn_reveal_table_item.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reveal_table_item.clicked.connect(self._reveal_all_files_table_item)
        af_filter_row.addWidget(self.btn_reveal_table_item)
        af_lay.addLayout(af_filter_row)

        self.all_files_table = QTableWidget()
        self.all_files_table.setColumnCount(5)
        self.all_files_table.setHorizontalHeaderLabels(
            ["Category", "File Name", "Size", "Source Location / Path", "Last Modified"]
        )
        self.all_files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.all_files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.all_files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.all_files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.all_files_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.all_files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.all_files_table.setAlternatingRowColors(True)
        self.all_files_table.setSortingEnabled(True)
        af_lay.addWidget(self.all_files_table, 1)

        self.view_stack.addWidget(self.all_files_widget)
        self.v.addWidget(self.view_stack, 1)

        self._all_itemized_entries: list = []

        self.state = StatePanel(self.p)
        self.state.bind_content(self.view_stack)
        self.v.addWidget(self.state, 1)

    def _build_extra_sweeps_grid(self):
        """Construct the 2x4 Bento Grid of specialized sweeps and quick hygiene actions."""
        extras_section = QWidget()
        sec_lay = QVBoxLayout(extras_section)
        sec_lay.setContentsMargins(0, 8, 0, 4)
        sec_lay.setSpacing(10)

        ex_title = QLabel(
            "<b>Specialized Fast Sweeps & Quick Hygiene</b> "
            "<span style='color:#8A93A8'>— independent scans, zero configuration needed</span>"
        )
        ex_title.setTextFormat(Qt.TextFormat.RichText)
        sec_lay.addWidget(ex_title)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        # Tile 1: Project Build Caches
        t1 = Card(self.p, "BentoTile")
        l1 = QVBoxLayout(t1)
        l1.setContentsMargins(14, 12, 14, 12)
        l1.setSpacing(6)
        l1_hdr = QLabel("<b>📦 Developer Build Caches</b>")
        l1_hdr.setTextFormat(Qt.TextFormat.RichText)
        l1.addWidget(l1_hdr)
        l1_sub = QLabel("node_modules, target, __pycache__, dist, .next across code roots.")
        l1_sub.setObjectName("Muted")
        l1_sub.setWordWrap(True)
        l1.addWidget(l1_sub)
        self.proj_status = QLabel("Project caches: not scanned yet.")
        self.proj_status.setObjectName("Muted")
        self.proj_status.setWordWrap(True)
        l1.addWidget(self.proj_status)
        l1.addStretch(1)
        r1 = QHBoxLayout()
        self.btn_scan_proj = QPushButton("Scan Caches")
        self.btn_scan_proj.setObjectName("Ghost")
        self.btn_scan_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_proj.clicked.connect(self._scan_project_caches)
        r1.addWidget(self.btn_scan_proj)
        self.btn_clean_proj = QPushButton("Clean Caches")
        self.btn_clean_proj.setObjectName("Danger")
        self.btn_clean_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean_proj.setEnabled(False)
        self.btn_clean_proj.clicked.connect(self._clean_project_caches)
        r1.addWidget(self.btn_clean_proj)
        l1.addLayout(r1)
        grid.addWidget(t1, 0, 0)

        # Tile 2: Deep Stale Temp Files
        t2 = Card(self.p, "BentoTile")
        l2 = QVBoxLayout(t2)
        l2.setContentsMargins(14, 12, 14, 12)
        l2.setSpacing(6)
        l2_hdr = QLabel("<b>🔥 Deep Stale Temp Files</b>")
        l2_hdr.setTextFormat(Qt.TextFormat.RichText)
        l2.addWidget(l2_hdr)
        l2_sub = QLabel("Deep temp sweep via TempCleaner (stale > 1 day across temp roots).")
        l2_sub.setObjectName("Muted")
        l2_sub.setWordWrap(True)
        l2.addWidget(l2_sub)
        self.temp_result_label = QLabel("Deep temp: not scanned yet.")
        self.temp_result_label.setObjectName("Muted")
        self.temp_result_label.setWordWrap(True)
        l2.addWidget(self.temp_result_label)
        l2.addStretch(1)
        r2 = QHBoxLayout()
        self.btn_temp = QPushButton("Scan Deep Temp")
        self.btn_temp.setObjectName("btn_scan_temp")
        self.btn_temp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_temp.clicked.connect(self._scan_temp)
        r2.addWidget(self.btn_temp)
        self.btn_clean_temp = QPushButton("Clean Deep Temp")
        self.btn_clean_temp.setObjectName("Danger")
        self.btn_clean_temp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean_temp.setVisible(False)
        self.btn_clean_temp.setEnabled(False)
        self.btn_clean_temp.clicked.connect(self._clean_temp)
        r2.addWidget(self.btn_clean_temp)
        l2.addLayout(r2)
        grid.addWidget(t2, 0, 1)

        # Tile 3: Large Log Files
        t3 = Card(self.p, "BentoTile")
        l3 = QVBoxLayout(t3)
        l3.setContentsMargins(14, 12, 14, 12)
        l3.setSpacing(6)
        l3_hdr = QLabel("<b>📜 Large Log Files</b>")
        l3_hdr.setTextFormat(Qt.TextFormat.RichText)
        l3.addWidget(l3_hdr)
        l3_sub = QLabel("Finds *.log & *.txt over 20 MB across code roots.")
        l3_sub.setObjectName("Muted")
        l3_sub.setWordWrap(True)
        l3.addWidget(l3_sub)
        self.logs_status = QLabel("Large logs: not scanned yet.")
        self.logs_status.setObjectName("Muted")
        self.logs_status.setWordWrap(True)
        l3.addWidget(self.logs_status)
        l3.addStretch(1)
        r3 = QHBoxLayout()
        self.btn_scan_logs = QPushButton("Scan Logs")
        self.btn_scan_logs.setObjectName("Ghost")
        self.btn_scan_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_logs.clicked.connect(self._scan_extra_logs)
        r3.addWidget(self.btn_scan_logs)
        self.btn_clean_logs = QPushButton("Recycle Logs")
        self.btn_clean_logs.setObjectName("Danger")
        self.btn_clean_logs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean_logs.setEnabled(False)
        self.btn_clean_logs.clicked.connect(self._clean_extra_logs)
        r3.addWidget(self.btn_clean_logs)
        l3.addLayout(r3)
        grid.addWidget(t3, 1, 0)

        # Tile 4: Large Files Hunter
        t4 = Card(self.p, "BentoTile")
        l4 = QVBoxLayout(t4)
        l4.setContentsMargins(14, 12, 14, 12)
        l4.setSpacing(6)
        l4_hdr = QLabel("<b>💾 Large Files Hunter</b>")
        l4_hdr.setTextFormat(Qt.TextFormat.RichText)
        l4.addWidget(l4_hdr)
        l4_sub = QLabel("Finds files over 100 MB across code roots + Documents/Downloads.")
        l4_sub.setObjectName("Muted")
        l4_sub.setWordWrap(True)
        l4.addWidget(l4_sub)
        self.large_status = QLabel("Large files: not scanned yet.")
        self.large_status.setObjectName("Muted")
        self.large_status.setWordWrap(True)
        l4.addWidget(self.large_status)
        l4.addStretch(1)
        r4 = QHBoxLayout()
        self.btn_scan_large = QPushButton("Scan Large Files")
        self.btn_scan_large.setObjectName("Ghost")
        self.btn_scan_large.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_large.clicked.connect(self._scan_large_files)
        r4.addWidget(self.btn_scan_large)
        self.btn_clean_large = QPushButton("Recycle Files")
        self.btn_clean_large.setObjectName("Danger")
        self.btn_clean_large.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean_large.setEnabled(False)
        self.btn_clean_large.clicked.connect(self._clean_large_files)
        r4.addWidget(self.btn_clean_large)
        l4.addLayout(r4)
        grid.addWidget(t4, 1, 1)

        # Tile 5: Empty Files & Folders
        t5 = Card(self.p, "BentoTile")
        l5 = QVBoxLayout(t5)
        l5.setContentsMargins(14, 12, 14, 12)
        l5.setSpacing(6)
        l5_hdr = QLabel("<b>📁 Empty Files & Folders</b>")
        l5_hdr.setTextFormat(Qt.TextFormat.RichText)
        l5.addWidget(l5_hdr)
        l5_sub = QLabel("0-byte ghost files and empty folders across code roots.")
        l5_sub.setObjectName("Muted")
        l5_sub.setWordWrap(True)
        l5.addWidget(l5_sub)
        self.empty_status = QLabel("Empty files: not scanned yet.")
        self.empty_status.setObjectName("Muted")
        self.empty_status.setWordWrap(True)
        l5.addWidget(self.empty_status)
        l5.addStretch(1)
        r5 = QHBoxLayout()
        self.btn_scan_empty = QPushButton("Scan Empty")
        self.btn_scan_empty.setObjectName("Ghost")
        self.btn_scan_empty.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_empty.clicked.connect(self._scan_empty_files)
        r5.addWidget(self.btn_scan_empty)
        self.btn_clean_empty = QPushButton("Recycle Empty")
        self.btn_clean_empty.setObjectName("Danger")
        self.btn_clean_empty.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean_empty.setEnabled(False)
        self.btn_clean_empty.clicked.connect(self._clean_empty_files)
        r5.addWidget(self.btn_clean_empty)
        l5.addLayout(r5)
        grid.addWidget(t5, 2, 0)

        # Tile 6: Duplicate Waste Finder
        t6 = Card(self.p, "BentoTile")
        l6 = QVBoxLayout(t6)
        l6.setContentsMargins(14, 12, 14, 12)
        l6.setSpacing(6)
        l6_hdr = QLabel("<b>👥 Duplicate Waste Finder</b>")
        l6_hdr.setTextFormat(Qt.TextFormat.RichText)
        l6.addWidget(l6_hdr)
        l6_sub = QLabel("Byte-identical duplicates. Review-only, never auto-deleted.")
        l6_sub.setObjectName("Muted")
        l6_sub.setWordWrap(True)
        l6.addWidget(l6_sub)
        self.dupes_status = QLabel("Duplicates: not scanned yet.")
        self.dupes_status.setObjectName("Muted")
        self.dupes_status.setWordWrap(True)
        l6.addWidget(self.dupes_status)
        l6.addStretch(1)
        r6 = QHBoxLayout()
        self.btn_scan_dupes = QPushButton("Scan Dupes")
        self.btn_scan_dupes.setObjectName("Ghost")
        self.btn_scan_dupes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_dupes.clicked.connect(self._scan_duplicates)
        r6.addWidget(self.btn_scan_dupes)
        self.btn_open_dupes = QPushButton("Review in Tool")
        self.btn_open_dupes.setObjectName("Ghost")
        self.btn_open_dupes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_dupes.clicked.connect(lambda: self._open_tool("duplicates"))
        r6.addWidget(self.btn_open_dupes)
        l6.addLayout(r6)
        grid.addWidget(t6, 2, 1)

        # Tile 7: OS Recycle Bin Hub
        t7 = Card(self.p, "BentoTile")
        l7 = QVBoxLayout(t7)
        l7.setContentsMargins(14, 12, 14, 12)
        l7.setSpacing(6)
        l7_hdr = QLabel("<b>🗑️ OS Recycle Bin Hub</b>")
        l7_hdr.setTextFormat(Qt.TextFormat.RichText)
        l7.addWidget(l7_hdr)
        l7_sub = QLabel("Measure and permanently empty Recycle Bin on all drives.")
        l7_sub.setObjectName("Muted")
        l7_sub.setWordWrap(True)
        l7.addWidget(l7_sub)
        self.bin_status = QLabel("Recycle Bin: not measured yet.")
        self.bin_status.setObjectName("Muted")
        self.bin_status.setWordWrap(True)
        l7.addWidget(self.bin_status)
        l7.addStretch(1)
        r7 = QHBoxLayout()
        self.btn_scan_bin = QPushButton("Measure Bin")
        self.btn_scan_bin.setObjectName("Ghost")
        self.btn_scan_bin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_bin.clicked.connect(self._measure_bin)
        r7.addWidget(self.btn_scan_bin)
        self.btn_empty_bin = QPushButton("Empty Recycle Bin")
        self.btn_empty_bin.setObjectName("Danger")
        self.btn_empty_bin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_empty_bin.setEnabled(False)
        self.btn_empty_bin.clicked.connect(self._empty_bin)
        r7.addWidget(self.btn_empty_bin)
        l7.addLayout(r7)
        grid.addWidget(t7, 3, 0)

        # Tile 8: Instant System Hygiene
        t8 = Card(self.p, "BentoTile")
        l8 = QVBoxLayout(t8)
        l8.setContentsMargins(14, 12, 14, 12)
        l8.setSpacing(6)
        l8_hdr = QLabel("<b>🛡️ Instant System Hygiene</b>")
        l8_hdr.setTextFormat(Qt.TextFormat.RichText)
        l8.addWidget(l8_hdr)
        l8_sub = QLabel("Instant actions: flush DNS resolver cache & clear clipboard.")
        l8_sub.setObjectName("Muted")
        l8_sub.setWordWrap(True)
        l8.addWidget(l8_sub)
        self.hygiene_status = QLabel("Hygiene: DNS + clipboard actions run instantly.")
        self.hygiene_status.setObjectName("Muted")
        self.hygiene_status.setWordWrap(True)
        l8.addWidget(self.hygiene_status)
        l8.addStretch(1)
        r8 = QHBoxLayout()
        self.btn_flush_dns = QPushButton("Flush DNS")
        self.btn_flush_dns.setObjectName("Ghost")
        self.btn_flush_dns.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_flush_dns.clicked.connect(self._flush_dns_now)
        r8.addWidget(self.btn_flush_dns)
        self.btn_clear_clipboard = QPushButton("Clear Clipboard")
        self.btn_clear_clipboard.setObjectName("Ghost")
        self.btn_clear_clipboard.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_clipboard.clicked.connect(self._clear_clipboard_now)
        r8.addWidget(self.btn_clear_clipboard)
        l8.addLayout(r8)
        grid.addWidget(t8, 3, 1)

        sec_lay.addLayout(grid)
        self.v.addWidget(extras_section)

    def _build_mission_control_card(self):
        """Construct the Mission Control command deck card."""
        mission = Card(self.p, "HeroCard")
        mc = QVBoxLayout(mission)
        mc.setContentsMargins(18, 16, 18, 16)
        mc.setSpacing(10)

        mc_title = QLabel(
            "<b>🚀 Mission Control Master Operations</b> "
            "<span style='color:#8A93A8'>— all fast sweeps at once, orchestrated execution</span>"
        )
        mc_title.setTextFormat(Qt.TextFormat.RichText)
        mc.addWidget(mc_title)

        mc_row = QHBoxLayout()
        mc_row.setSpacing(10)

        self.btn_scan_everything = QPushButton("⚡ Scan Everything")
        self.btn_scan_everything.setObjectName("Primary")
        self.btn_scan_everything.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_scan_everything.setToolTip(
            "Runs all fast sweeps at once: system caches + deep temp + project + logs + large + empty + duplicates."
        )
        self.btn_scan_everything.clicked.connect(self._scan_everything)
        mc_row.addWidget(self.btn_scan_everything)

        self.btn_clean_everything = QPushButton("🛡️ Clean Everything Safe")
        self.btn_clean_everything.setObjectName("Danger")
        self.btn_clean_everything.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clean_everything.setToolTip(
            "Recycles all safe hits (system LOW+MEDIUM, temp, project, logs, large, empty). Duplicates + HIGH-risk + Recycle Bin never auto-deleted."
        )
        self.btn_clean_everything.clicked.connect(self._clean_everything_safe)
        mc_row.addWidget(self.btn_clean_everything)

        mc_row.addStretch(1)
        mc.addLayout(mc_row)

        self.mission_total = QLabel(
            "Mission total: scan first — aggregates system + temp + project + logs + large + empty."
        )
        self.mission_total.setObjectName("Muted")
        self.mission_total.setWordWrap(True)
        mc.addWidget(self.mission_total)

        self.mission_feed = QLabel("")
        self.mission_feed.setObjectName("Muted")
        self.mission_feed.setWordWrap(True)
        mc.addWidget(self.mission_feed)

        self.v.addWidget(mission)

    def _build_all_tools_section(self):
        """Build the clean tools directory with launcher cards."""
        self.tools_title = QLabel(
            "<b>All Clean Tools Directory</b> "
            "<span style='color:#8A93A8'>— every cleaner, one directory. Wired rows clean inline above; the rest open in one click.</span>"
        )
        self.tools_title.setTextFormat(Qt.TextFormat.RichText)
        self.tools_title.setWordWrap(True)
        self.v.addWidget(self.tools_title)

        self.tools_scroll = QScrollArea()
        self.tools_scroll.setWidgetResizable(True)
        self.tools_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.tools_scroll.setMaximumHeight(260)
        tools_holder = QWidget()
        self.tools_grid = QGridLayout(tools_holder)
        self.tools_grid.setContentsMargins(4, 4, 4, 4)
        self.tools_grid.setSpacing(8)
        self.tools_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tools_scroll.setWidget(tools_holder)
        self.attach_single_scroll(self.tools_scroll)
        self.v.addWidget(self.tools_scroll)
        self._build_all_tools_grid()

    def _build_action_footer(self):
        """Build the pinned glassmorphism footer with action buttons and safety hints."""
        action_row = QHBoxLayout()
        action_row.setSpacing(12)

        self.clean_btn = QPushButton("Clean Selected")
        self.clean_btn.setObjectName("Danger")
        self.clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clean_btn.setEnabled(False)
        self.clean_btn.setToolTip("Clean ticked cards only (moves to Recycle Bin).")
        self.clean_btn.clicked.connect(self._clean)
        action_row.addWidget(self.clean_btn)

        self.clean_all_btn = QPushButton("Clean All Found (Safe)")
        self.clean_all_btn.setObjectName("Primary")
        self.clean_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clean_all_btn.setToolTip(
            "One click: ticks every LOW + MEDIUM card with found files (HIGH stays unticked) and cleans. Full-device clean in one place."
        )
        self.clean_all_btn.setEnabled(False)
        self.clean_all_btn.clicked.connect(self._clean_all_safe)
        action_row.addWidget(self.clean_all_btn)

        action_row.addStretch(1)

        hint = QLabel(
            "LOW = auto-regenerated • MEDIUM = re-downloadable • HIGH = requires confirmation. "
            "Everything moves to the Recycle Bin (reversible) — empty the bin above to free disk space."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        action_row.addWidget(hint, 1)

        footer = QWidget()
        footer.setLayout(action_row)
        self.pin_footer(footer)

    # -----------------------------------------------------------------------
    # Operational State & Target Scope Handlers
    # -----------------------------------------------------------------------

    def _show_initial_ready_state(self):
        """Display initial ready state prompting user to select target and click Start Scan."""
        self.state.show_empty(
            "Ready to scan.\n\n"
            "Select target scope above (Full Device, System Drive C:, or Custom Folder/File) "
            "and click '▶ Start Scan' to begin analysis."
        )
        self.scan_status.setText("Ready to scan.")
        self.clean_btn.setEnabled(False)
        self.clean_all_btn.setEnabled(False)
        if hasattr(self, "btn_cancel_scan"):
            self.btn_cancel_scan.setVisible(False)
        if hasattr(self, "scan_feed_card"):
            self.scan_feed_card.setVisible(False)

    def _select_target_full_device(self):
        """Select full device partitions and system caches as target."""
        self._custom_roots.clear()
        self._update_roots_status()
        self.btn_target_full.setObjectName("Primary")
        self.btn_target_sys.setObjectName("Ghost")
        self._reapply_target_button_styles()

    def _select_target_system_drive(self):
        """Select OS system drive (e.g. C:\\) as target."""
        sys_drive = os.environ.get("SystemDrive", "C:")
        if not sys_drive.endswith("\\"):
            sys_drive += "\\"
        self._custom_roots = [Path(sys_drive)]
        self._update_roots_status()
        self.btn_target_full.setObjectName("Ghost")
        self.btn_target_sys.setObjectName("Primary")
        self._reapply_target_button_styles()

    def _reapply_target_button_styles(self):
        for btn in (self.btn_target_full, self.btn_target_sys, self.btn_select_dir, self.btn_select_file):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _start_scan(self):
        """Start scan on the currently selected target."""
        self._scan()

    def _cancel_scan(self):
        """Cooperatively cancel running scan worker."""
        if self._worker is not None:
            self._worker.cancel()
            self.scan_status.setText("Cancelling scan…")
            self._log_feed("Scan cancellation requested by user…")
            self.btn_cancel_scan.setEnabled(False)

    def _switch_to_cards_view(self):
        self.view_stack.setCurrentIndex(0)
        self.btn_view_cards.setObjectName("Primary")
        self.btn_view_table.setObjectName("Ghost")
        for b in (self.btn_view_cards, self.btn_view_table):
            b.style().unpolish(b)
            b.style().polish(b)

    def _switch_to_table_view(self):
        self.view_stack.setCurrentIndex(1)
        self.btn_view_cards.setObjectName("Ghost")
        self.btn_view_table.setObjectName("Primary")
        for b in (self.btn_view_cards, self.btn_view_table):
            b.style().unpolish(b)
            b.style().polish(b)

    def _open_inspect_dialog(self, scan, cat: CleanupCategory):
        """Open modal dialog to inspect itemized files discovered in this category."""
        if not scan or not scan.entries:
            QMessageBox.information(self, "Inspect Category", f"No files discovered under {cat.label}.")
            return
        dlg = CategoryFilesDialog(self, scan, cat)
        dlg.exec()

    def _populate_all_files_table(self, all_entries: list[tuple[CleanupCategory, object]]):
        """Populate the itemized breakdown table of all discovered files."""
        self._all_itemized_entries = list(all_entries)
        filter_text = self.all_files_filter.text() if hasattr(self, "all_files_filter") else ""
        self._filter_all_files_table(filter_text)

    def _filter_all_files_table(self, text: str):
        query = text.strip().lower()
        if not query:
            filtered = self._all_itemized_entries
        else:
            filtered = [
                (cat, e)
                for cat, e in self._all_itemized_entries
                if query in cat.label.lower() or query in e.path.name.lower() or query in str(e.path.parent).lower()
            ]

        self.all_files_table.setSortingEnabled(False)
        self.all_files_table.setRowCount(len(filtered))
        for row, (cat, entry) in enumerate(filtered):
            cat_item = QTableWidgetItem(cat.label)
            self.all_files_table.setItem(row, 0, cat_item)

            name_item = QTableWidgetItem(entry.path.name or str(entry.path))
            name_item.setData(Qt.ItemDataRole.UserRole, str(entry.path))
            self.all_files_table.setItem(row, 1, name_item)

            sz_item = QTableWidgetItem(fmt_bytes(entry.size))
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.all_files_table.setItem(row, 2, sz_item)

            loc_item = QTableWidgetItem(str(entry.path.parent))
            loc_item.setToolTip(str(entry.path))
            self.all_files_table.setItem(row, 3, loc_item)

            try:
                mod_str = datetime.fromtimestamp(entry.mtime).strftime("%Y-%m-%d %H:%M:%S")
            except (OSError, ValueError):
                mod_str = "—"
            mod_item = QTableWidgetItem(mod_str)
            self.all_files_table.setItem(row, 4, mod_item)

        self.all_files_table.setSortingEnabled(True)

    def _reveal_all_files_table_item(self):
        selected = self.all_files_table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.all_files_table.item(row, 1)
        if not item:
            return
        fp = item.data(Qt.ItemDataRole.UserRole)
        if fp and os.path.exists(fp):
            import subprocess

            subprocess.Popen(f'explorer /select,"{fp}"')
        elif fp and os.path.exists(os.path.dirname(fp)):
            import subprocess

            subprocess.Popen(f'explorer "{os.path.dirname(fp)}"')

    # -----------------------------------------------------------------------
    # Scan Execution
    # -----------------------------------------------------------------------

    def _on_scan_all_clicked(self):
        """Full-device sweep: reset custom targets and scan all default system caches."""
        self._custom_roots.clear()
        if not self.include_disabled_chk.isChecked():
            self.include_disabled_chk.setChecked(True)
        self._update_roots_status()
        self._scan()

    def _scan(self):
        """Auto scan across target (custom roots if chosen, else full device)."""
        self.scan_btn.setEnabled(False)
        self.btn_cancel_scan.setEnabled(True)
        self.btn_cancel_scan.setVisible(True)
        self.clean_btn.setEnabled(False)
        self.clean_all_btn.setEnabled(False)

        target_name = (
            ", ".join(str(r) for r in self._custom_roots)
            if self._custom_roots
            else "Full Device (all system caches & partitions)"
        )
        loading_text = f"Scanning target: {target_name}…"
        self.state.show_loading(loading_text)
        self.progress.setVisible(True)
        self.scan_status.setText("Scanning…")

        self.scan_feed_card.setVisible(True)
        self.scan_log_text.clear()
        self._log_feed(f"Scan initiated for target: {target_name}")

        risk = "high" if self.include_disabled_chk.isChecked() else "medium"
        w = HubScanWorker(
            max_risk=risk,
            include_disabled=True,
            custom_roots=list(self._custom_roots) if self._custom_roots else None,
        )
        self._worker = w
        self.win.run_worker(w, self._on_scanned, self._fail, on_progress=self._on_progress)

    def _on_progress(self, msg: str):
        """Show worker progress text in the scan status label and live activity feed."""
        self.scan_status.setText(msg)
        self._log_feed(msg)

    def _log_feed(self, msg: str):
        """Append line to the scanning activity feed and scroll to bottom."""
        now_str = time.strftime("%H:%M:%S")
        self.scan_log_text.append(f"[{now_str}] {msg}")
        sb = self.scan_log_text.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_scanned(self, report):
        """Update summary cards, rebuild the category card grid, and populate the all-files table."""
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.scan_btn.setEnabled(True)
        self.btn_cancel_scan.setVisible(False)
        self._report = report
        self._scan_map = {s.category.id: s for s in report.scans}

        dur = getattr(report, "duration_seconds", 0.0) or 0.0
        self._log_feed(
            f"✓ Scan completed in {dur:.2f}s: {report.total_files:,} files found ({fmt_bytes(report.total_reclaimable_bytes)}) across {len(report.scans)} categories."
        )

        try:
            self._measure_bin()
        except Exception:  # noqa: BLE001
            pass

        # Clear grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._selected = {}
        self._card_checkboxes = {}
        self._card_risks = {}

        # Summary cards
        self.card_total.set_value(fmt_bytes(report.total_reclaimable_bytes), animate=True)
        self.card_files.set_value(f"{report.total_files:,}", animate=True)
        self.card_cats.set_value(str(len(report.scans)), animate=True)

        cols = 2
        if not report.scans or report.total_files == 0:
            target_desc = (
                ", ".join(str(r) for r in self._custom_roots) if self._custom_roots else "the scanned system categories"
            )
            self.state.show_empty(f"No reclaimable files found under:\n{target_desc}\n\nThis target location is clean!")
            self.win.statusBar().showMessage("Scan complete: 0 files found, 0 B reclaimable", 5000)
            self._populate_all_files_table([])
            self._update_clean_enabled()
            return

        self.state.clear()

        all_entries: list[tuple[CleanupCategory, object]] = [
            (scan.category, e) for scan in report.scans for e in scan.entries
        ]

        if self._custom_roots:
            for idx, scan in enumerate(report.scans):
                card = self._make_card(scan.category, scan.total_bytes, scan.file_count)
                r, c = divmod(idx, cols)
                self.grid.addWidget(card, r, c)
            self.win.statusBar().showMessage(
                f"Scanned custom target: {len(report.scans)} categories, {report.total_files:,} files, {fmt_bytes(report.total_reclaimable_bytes)} reclaimable",
                5000,
            )
        else:
            cats = default_categories()
            all_by_id = {c.id: c for c in cats}
            ids_sorted = sorted(all_by_id.keys(), key=lambda cid: (all_by_id[cid].risk.rank, cid))
            for idx, cid in enumerate(ids_sorted):
                cat = all_by_id[cid]
                scan = self._scan_map.get(cid)
                est_bytes = scan.total_bytes if scan else 0
                est_files = scan.file_count if scan else 0
                card = self._make_card(cat, est_bytes, est_files)
                r, c = divmod(idx, cols)
                self.grid.addWidget(card, r, c)
            self.win.statusBar().showMessage(
                f"Scanned {len(ids_sorted)} categories, {report.total_files:,} files, {fmt_bytes(report.total_reclaimable_bytes)} reclaimable",
                5000,
            )

        self._populate_all_files_table(all_entries)
        self._update_clean_enabled()

    def _make_card(self, cat: CleanupCategory, est_bytes: int, est_files: int) -> Card:
        """Build one category card: risk/reversible badges, source breakdown, estimate, inspect, and checkbox."""
        card = Card(self.p, "BentoTile")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        title_row = QHBoxLayout()
        icon = _CATEGORY_ICONS.get(cat.id, "💾")
        title = QLabel(f"<span style='font-size:15px;'>{icon}</span> <b>{cat.label}</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title_row.addWidget(title)
        title_row.addStretch(1)

        # Risk badge
        risk_txt, risk_col = _risk_label(cat.risk), _risk_color(cat.risk)
        risk_lbl = QLabel(
            f"<span style='background:{risk_col}; color:#111; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:700;'>{risk_txt}</span>"
        )
        risk_lbl.setTextFormat(Qt.TextFormat.RichText)
        risk_lbl.setToolTip(f"Risk: {cat.risk.value} — {cat.description}")
        title_row.addWidget(risk_lbl)

        # Reversible badge
        rev = QLabel(
            f"<span style='border:1px solid #4B5563; padding:2px 8px; border-radius:6px; font-size:11px;'>{'↩ Reversible' if cat.reversible else 'Irreversible'}</span>"
        )
        rev.setTextFormat(Qt.TextFormat.RichText)
        rev.setToolTip(
            "Reversible = safe to undo (cache regenerates or goes to Recycle Bin)"
            if cat.reversible
            else "Irreversible = manual re-download / reinstall"
        )
        title_row.addWidget(rev)
        lay.addLayout(title_row)

        desc = QLabel(cat.description)
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # Paths line
        paths = cat.existing_paths()
        path_text = str(paths[0]) if paths else (str(cat.paths[0]) if cat.paths else "—")
        if len(cat.paths) > 1:
            path_text += f"  (+{len(cat.paths)-1} more)"
        path_lbl = QLabel(path_text)
        path_lbl.setObjectName("Muted")
        path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(path_lbl)

        # Globs
        if cat.globs != ("*",):
            globs_lbl = QLabel(f"Matches: {', '.join(cat.globs)}")
            globs_lbl.setObjectName("Muted")
            lay.addWidget(globs_lbl)

        # Top source directories breakdown
        scan = self._scan_map.get(cat.id)
        if scan and scan.entries:
            breakdown = scan.breakdown(limit=3)
            if breakdown:
                source_box = QWidget()
                sb_lay = QVBoxLayout(source_box)
                sb_lay.setContentsMargins(10, 8, 10, 8)
                sb_lay.setSpacing(4)
                source_box.setStyleSheet(
                    "background: rgba(255, 255, 255, 0.035); border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.07);"
                )
                sb_title = QLabel("<b>Source Origin Breakdown:</b>")
                sb_title.setTextFormat(Qt.TextFormat.RichText)
                sb_lay.addWidget(sb_title)
                for item in breakdown:
                    fname = item.get("name", "")
                    fcnt = item.get("count", 0)
                    fsz = item.get("size", 0)
                    item_lbl = QLabel(f"• 📁 <b>{fname}</b>: {fcnt:,} files ({fmt_bytes(fsz)})")
                    item_lbl.setObjectName("Muted")
                    item_lbl.setWordWrap(True)
                    sb_lay.addWidget(item_lbl)
                lay.addWidget(source_box)

        # Estimate + Inspect + Checkbox row
        est_row = QHBoxLayout()
        est_row.setSpacing(8)
        est_row.addWidget(
            QLabel(
                f"<b>{fmt_bytes(est_bytes)}</b> &middot; {est_files:,} file(s)"
                if est_bytes or est_files
                else "<span style='color:#888'>No files found</span>"
            )
        )
        est_row.addStretch(1)

        btn_inspect = QPushButton(f"🔍 Inspect ({est_files:,})" if est_files else "🔍 Inspect")
        btn_inspect.setObjectName("Ghost")
        btn_inspect.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_inspect.setEnabled(est_files > 0)
        btn_inspect.setToolTip("Inspect itemized files, parent directories, and exact sizes.")
        btn_inspect.clicked.connect(lambda _c=False, s=scan, c=cat: self._open_inspect_dialog(s, c))
        est_row.addWidget(btn_inspect)

        chk = QCheckBox("Select")
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setChecked(bool(est_bytes or est_files) and cat.risk != RiskLevel.HIGH)
        cid = cat.id
        self._selected[cid] = chk.isChecked()
        self._card_checkboxes[cid] = chk
        self._card_risks[cid] = cat.risk

        def _on_toggled(checked, _cid=cid):
            self._selected[_cid] = checked
            self._update_clean_enabled()

        chk.toggled.connect(_on_toggled)
        est_row.addWidget(chk)
        lay.addLayout(est_row)

        return card

    def _select_all_cards(self, state: bool):
        """Check or uncheck every category card checkbox at once."""
        for cid, chk in self._card_checkboxes.items():
            chk.blockSignals(True)
            chk.setChecked(state)
            chk.blockSignals(False)
            self._selected[cid] = state
        self._update_clean_enabled()

    def _select_safe_cards(self):
        """Tick all LOW + MEDIUM cards with hits; untick HIGH-risk."""
        for cid, chk in self._card_checkboxes.items():
            safe = self._card_risks.get(cid) != RiskLevel.HIGH
            scan = self._scan_map.get(cid)
            has_hits = bool(scan is not None and (scan.total_bytes or scan.file_count))
            want = bool(has_hits and safe)
            chk.blockSignals(True)
            chk.setChecked(want)
            chk.blockSignals(False)
            self._selected[cid] = want
        self._update_clean_enabled()

    def _update_clean_enabled(self):
        """Enable Clean buttons when at least one card is ticked and the report has files."""
        any_sel = any(self._selected.values())
        report_ok = self._report is not None and self._report.total_files > 0
        ok = bool(any_sel and report_ok)
        self.clean_btn.setEnabled(ok)
        self.clean_all_btn.setEnabled(bool(report_ok))

    def _fail(self, msg: str):
        """Handle an operation failure and notify the user."""
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("Scan failed.")
        self.scan_btn.setEnabled(True)
        if hasattr(self, "btn_cancel_scan"):
            self.btn_cancel_scan.setVisible(False)
        self.btn_temp.setEnabled(True)
        self._log_feed(f"Error: {msg}")
        self._update_clean_enabled()
        self.state.show_error(msg, on_retry=self._scan)

    # -----------------------------------------------------------------------
    # Fast Sweeps & System Hygiene Handlers
    # -----------------------------------------------------------------------

    def _scan_temp(self):
        """Deep-temp sweep whose result stays in the Hub with a one-click Clean."""
        self.btn_temp.setEnabled(False)
        self.btn_clean_temp.setVisible(False)
        self.btn_clean_temp.setEnabled(False)
        self.temp_result_label.setText("Scanning deep temp (stale > 1 day)…")
        w = TempScanWorker(min_age_days=1)
        self._worker = w
        self.win.run_worker(w, self._on_temp_scanned, self._on_temp_failed, on_progress=self._on_temp_progress)

    def _on_temp_progress(self, msg: str):
        self.temp_result_label.setText(str(msg))

    def _on_temp_scanned(self, findings):
        self._worker = None
        self.btn_temp.setEnabled(True)
        self.scan_status.setText("")
        self._temp_findings = list(findings or [])
        total = sum(int(getattr(f, "size_bytes", 0) or 0) for f in self._temp_findings)
        count = len(self._temp_findings)
        msg = f"Deep temp: {count:,} file(s), {fmt_bytes(total)} reclaimable (stale > 1 day, trash-safe)"
        self.temp_result_label.setText(msg)
        self.win.statusBar().showMessage(msg, 6000)
        self.scan_status.setText(msg)
        has = count > 0
        self.btn_clean_temp.setVisible(True)
        self.btn_clean_temp.setEnabled(has)
        if not has:
            self.temp_result_label.setText("Deep temp: clean — no stale files found.")

    def _clean_temp(self):
        """Move stored deep-temp findings to the Recycle Bin, then rescan the Hub."""
        if not self._temp_findings:
            QMessageBox.information(self, "Deep Temp", "No stale temp findings to clean — run Scan Deep Temp first.")
            return
        total = sum(int(getattr(f, "size_bytes", 0) or 0) for f in self._temp_findings)
        confirm = QMessageBox.question(
            self,
            "Clean deep temp?",
            f"Move {len(self._temp_findings):,} stale temp file(s) ({fmt_bytes(total)}) to the Recycle Bin?\n\n"
            "Locked/in-use files are skipped automatically.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            from cortex_unified.core.temp_cleaner import TempCleaner

            res = TempCleaner(min_age_days=1).clean(self._temp_findings, use_trash=True, dry_run=False)
            freed = int(res.get("bytes_freed", 0))
            deleted = int(res.get("deleted", 0))
            failed = int(res.get("failed", 0))
            QMessageBox.information(
                self,
                "Deep temp cleaned",
                f"Moved {deleted:,} file(s) to Recycle Bin ({fmt_bytes(freed)})."
                + (f" {failed} locked/skipped." if failed else ""),
            )
            self._temp_findings = []
            self.btn_clean_temp.setEnabled(False)
            self.btn_clean_temp.setVisible(False)
            self.temp_result_label.setText("")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Deep Temp Clean", f"Clean failed:\n{exc}")
            return
        self._scan()

    def _on_temp_failed(self, msg: str):
        self._worker = None
        self.btn_temp.setEnabled(True)
        self.scan_status.setText("")
        QMessageBox.warning(self, "Stale Temp Scan", f"Temp scan failed:\n{msg}")

    def _measure_bin(self):
        """Measure Recycle Bin size across all drives."""
        self.btn_scan_bin.setEnabled(False)
        self.btn_empty_bin.setEnabled(False)
        self.bin_status.setText("Measuring Recycle Bin…")
        w = RecycleBinWorker(mode="measure")
        self._bin_worker = w
        self.win.run_worker(w, self._on_bin_measured, self._on_bin_failed, on_progress=self._on_bin_progress)

    def _on_bin_progress(self, msg: str):
        self.bin_status.setText(str(msg))

    def _on_bin_measured(self, report):
        self._bin_worker = None
        self.btn_scan_bin.setEnabled(True)
        try:
            self._bin_bytes = int(report.total_bytes)
            self._bin_items = int(report.total_items)
        except Exception:  # noqa: BLE001
            self._bin_bytes, self._bin_items = 0, 0
        if self._bin_items:
            self.bin_status.setText(
                f"Recycle Bin: {self._bin_items:,} item(s), {fmt_bytes(self._bin_bytes)} — empty to free space."
            )
            self.btn_empty_bin.setEnabled(True)
        else:
            self.bin_status.setText("Recycle Bin: empty.")
            self.btn_empty_bin.setEnabled(False)
        self._update_mission_total()

    def _empty_bin(self):
        """Permanently empty the Recycle Bin after its own confirmation."""
        if not self._bin_items:
            QMessageBox.information(self, "Recycle Bin", "The bin is already empty — nothing to do.")
            return
        confirm = QMessageBox.question(
            self,
            "Empty Recycle Bin?",
            f"PERMANENTLY delete {self._bin_items:,} item(s) ({fmt_bytes(self._bin_bytes)}) from the Recycle Bin on all drives?\n\n"
            "This cannot be undone. It is never part of automatic cleaning.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.btn_scan_bin.setEnabled(False)
        self.btn_empty_bin.setEnabled(False)
        w = RecycleBinWorker(mode="empty", dry_run=False)
        self._bin_worker = w
        self.win.run_worker(w, self._on_bin_emptied, self._on_bin_failed, on_progress=self._on_bin_progress)

    def _on_bin_emptied(self, result):
        self._bin_worker = None
        self.btn_scan_bin.setEnabled(True)
        try:
            freed = int(result.freed_bytes)
            ok = bool(result.emptied)
            msg = str(result.message)
        except Exception:  # noqa: BLE001
            freed, ok, msg = 0, False, "Unexpected result."
        if ok:
            self._feed(f"Recycle Bin emptied: {fmt_bytes(freed)} actually freed.")
            QMessageBox.information(
                self, "Recycle Bin emptied", f"{msg}\n\n{fmt_bytes(freed)} of disk space actually freed."
            )
        else:
            QMessageBox.warning(self, "Empty Recycle Bin", msg)
        self._measure_bin()

    def _on_bin_failed(self, msg: str):
        self._bin_worker = None
        self.btn_scan_bin.setEnabled(True)
        self.bin_status.setText("Recycle Bin: measurement failed.")
        QMessageBox.warning(self, "Recycle Bin", f"Operation failed:\n{msg}")

    def _run_hygiene(self, kind: str):
        """Run one instant hygiene action and report it on its row + feed."""
        try:
            from cortex_unified.system_tools.hygiene_actions import clear_clipboard, flush_dns

            result = flush_dns() if kind == "dns" else clear_clipboard()
        except Exception as exc:  # noqa: BLE001
            self.hygiene_status.setText(f"Hygiene action failed: {exc}")
            return
        self.hygiene_status.setText(result.message)
        self._feed(result.message)
        self.win.statusBar().showMessage(result.message, 5000)
        if not result.success:
            QMessageBox.warning(self, "Hygiene action", result.message)

    def _flush_dns_now(self):
        self._run_hygiene("dns")

    def _clear_clipboard_now(self):
        self._run_hygiene("clipboard")

    def _scan_project_caches(self):
        """Auto-discover project build caches across code roots."""
        self.btn_scan_proj.setEnabled(False)
        self.btn_clean_proj.setEnabled(False)
        self.proj_status.setText("Scanning project caches across code roots…")
        from .workers import AutoProjectCacheWorker

        w = AutoProjectCacheWorker(keep_recent_days=7)
        self._extra_worker = w
        self.win.run_worker(
            w, self._on_project_scanned, self._on_extra_failed, on_progress=self._on_extra_proj_progress
        )

    def _on_extra_proj_progress(self, msg: str, _items: int, _size: object):
        self.proj_status.setText(str(msg))

    def _on_project_scanned(self, resources: list):
        self._extra_worker = None
        self.btn_scan_proj.setEnabled(True)
        self._proj_resources = list(resources or [])
        total = sum(int(r.get("size_bytes", 0) or 0) for r in self._proj_resources)
        if not self._proj_resources:
            self.proj_status.setText("Project caches: clean — nothing found.")
            self.btn_clean_proj.setEnabled(False)
        else:
            self.proj_status.setText(
                f"Project caches: {len(self._proj_resources):,} item(s), {fmt_bytes(total)} reclaimable."
            )
            self.btn_clean_proj.setEnabled(True)
        self.win.statusBar().showMessage(self.proj_status.text(), 5000)

    def _clean_project_caches(self):
        """Recycle discovered project caches after confirmation."""
        if not self._proj_resources:
            return
        total = sum(int(r.get("size_bytes", 0) or 0) for r in self._proj_resources)
        confirm = QMessageBox.question(
            self,
            "Clean project caches?",
            f"Remove {len(self._proj_resources):,} project cache item(s) ({fmt_bytes(total)})?\n\n"
            "Regenerable via npm install / cargo fetch / rebuild. Locked files are skipped.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import ProjectCacheCleanWorker

        self.btn_clean_proj.setEnabled(False)
        w = ProjectCacheCleanWorker(list(self._proj_resources), dry_run=False)
        self._extra_worker = w
        self.win.run_worker(
            w, self._on_project_cleaned, self._on_extra_failed, on_progress=self._on_extra_clean_progress
        )

    def _on_extra_clean_progress(self, _done: int, _total: int, _freed: object):
        try:
            self.proj_status.setText(f"Cleaning project caches… {_done:,}/{_total:,}")
        except Exception:  # noqa: BLE001
            pass

    def _on_project_cleaned(self, results: dict):
        self._extra_worker = None
        self.btn_scan_proj.setEnabled(True)
        freed = int((results or {}).get("total_freed_bytes", (results or {}).get("freed_bytes", 0)) or 0)
        cleaned = int((results or {}).get("cleaned_count", (results or {}).get("deleted", 0)) or 0)
        QMessageBox.information(self, "Project caches cleaned", f"Removed {cleaned:,} item(s) ({fmt_bytes(freed)}).")
        self._proj_resources = []
        self.btn_clean_proj.setEnabled(False)
        self.proj_status.setText("Project caches: clean — nothing found.")
        self._scan()

    def _scan_extra_logs(self):
        """Find large logs across auto code roots."""
        roots = self._auto_log_roots()
        if not roots:
            QMessageBox.information(self, "No roots", "No code roots found to sweep for logs.")
            return
        self.btn_scan_logs.setEnabled(False)
        self.btn_clean_logs.setEnabled(False)
        self.logs_status.setText(f"Scanning {len(roots)} root(s) for large logs…")
        from .workers import CacheLogSweepWorker

        w = CacheLogSweepWorker([str(r) for r in roots], min_size_mb=20.0)
        self._extra_worker = w
        self.win.run_worker(w, self._on_extra_logs_done, self._on_extra_failed, on_progress=self._on_extra_log_progress)

    def _on_extra_log_progress(self, msg: str):
        self.logs_status.setText(str(msg))

    def _on_extra_logs_done(self, results: list):
        self._extra_worker = None
        self.btn_scan_logs.setEnabled(True)
        self._extra_logs = list(results or [])
        total = sum(int(sz) for _, sz in self._extra_logs)
        if not self._extra_logs:
            self.logs_status.setText("Large logs: clean — nothing over 20 MB found.")
            self.btn_clean_logs.setEnabled(False)
        else:
            self.logs_status.setText(f"Large logs: {len(self._extra_logs):,} file(s), {fmt_bytes(total)} reclaimable.")
            self.btn_clean_logs.setEnabled(True)

    def _clean_extra_logs(self):
        """Move selected large logs to the Recycle Bin."""
        if not self._extra_logs:
            return
        total = sum(int(sz) for _, sz in self._extra_logs)
        confirm = QMessageBox.question(
            self,
            "Recycle large logs?",
            f"Move {len(self._extra_logs):,} log(s) ({fmt_bytes(total)}) to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import DeleteSelectedWorker

        paths = [str(p) for p, _ in self._extra_logs]
        self.btn_clean_logs.setEnabled(False)
        self.win.run_worker(DeleteSelectedWorker(paths, "recycle"), self._on_extra_logs_cleaned, self._on_extra_failed)

    def _on_extra_logs_cleaned(self, freed: int, ok: int, blocked: int):
        self.btn_scan_logs.setEnabled(True)
        QMessageBox.information(
            self,
            "Done",
            f"Recycled {ok} log(s), freed {fmt_bytes(freed)}." + (f" {blocked} blocked." if blocked else ""),
        )
        self._extra_logs = []
        self.btn_clean_logs.setEnabled(False)
        self.logs_status.setText("Large logs: clean — nothing over 20 MB found.")

    def _on_extra_failed(self, msg: str):
        self._extra_worker = None
        self._sweep_workers.clear()
        self.btn_scan_proj.setEnabled(True)
        self.btn_scan_logs.setEnabled(True)
        self.btn_scan_large.setEnabled(True)
        self.btn_scan_empty.setEnabled(True)
        self.btn_scan_dupes.setEnabled(True)
        self.btn_scan_bin.setEnabled(True)
        QMessageBox.warning(self, "Extra sweep failed", str(msg))

    def _sweep_roots(self) -> list[Path]:
        """Auto roots for file sweeps: code roots + Documents/Downloads."""
        roots: list[Path] = []
        try:
            from cortex_unified.analyzers.project_cache_scanner import _known_code_roots

            for p in _known_code_roots():
                try:
                    if p.is_dir() and p not in roots:
                        roots.append(p)
                except OSError:
                    continue
                if len(roots) >= 6:
                    break
        except Exception:  # noqa: BLE001
            pass
        home = Path.home()
        for sub in ("Documents", "Downloads", "code", "Projects", "workspace", "dev"):
            p = home / sub
            try:
                if p.is_dir() and p not in roots:
                    roots.append(p)
            except OSError:
                continue
            if len(roots) >= 8:
                break
        return roots

    def _feed(self, msg: str):
        self._feed_lines.append(str(msg))
        self._feed_lines = self._feed_lines[-3:]
        self.mission_feed.setText("\n".join(self._feed_lines))
        self._update_mission_total()

    def _sweep_bytes(self, kind: str) -> int:
        try:
            if kind == "system":
                return int(self._report.total_reclaimable_bytes) if self._report else 0
            if kind == "temp":
                return sum(int(getattr(f, "size_bytes", 0) or 0) for f in self._temp_findings)
            if kind == "project":
                return sum(int(r.get("size_bytes", 0) or 0) for r in self._proj_resources)
            if kind == "logs":
                return sum(int(sz) for _, sz in self._extra_logs)
            if kind == "large":
                return sum(int(getattr(e, "size", 0) or 0) for e in self._large_files)
            if kind == "empty":
                return 0
        except Exception:  # noqa: BLE001
            return 0
        return 0

    def _update_mission_total(self):
        """Aggregate monitor: system + temp + project + logs + large."""
        sys_b = self._sweep_bytes("system")
        tmp_b = self._sweep_bytes("temp")
        proj_b = self._sweep_bytes("project")
        log_b = self._sweep_bytes("logs")
        large_b = self._sweep_bytes("large")
        total = sys_b + tmp_b + proj_b + log_b + large_b
        n_files = 0
        try:
            n_files += int(self._report.total_files) if self._report else 0
            n_files += (
                len(self._temp_findings)
                + len(self._proj_resources)
                + len(self._extra_logs)
                + len(self._large_files)
                + len(self._empty_files)
            )
        except Exception:  # noqa: BLE001
            pass
        dupe_note = f" + {fmt_bytes(self._dupe_waste)} duplicates (review-only)" if self._dupe_waste else ""
        bin_note = (
            f" + {fmt_bytes(self._bin_bytes)} sitting in the Recycle Bin (empty separately to free it)"
            if self._bin_bytes
            else ""
        )
        self.mission_total.setText(
            f"Mission total: {fmt_bytes(total)} across {n_files:,} item(s) "
            f"(system {fmt_bytes(sys_b)} • temp {fmt_bytes(tmp_b)} • project {fmt_bytes(proj_b)} • "
            f"logs {fmt_bytes(log_b)} • large {fmt_bytes(large_b)} • empty {len(self._empty_files)+len(self._empty_dirs)} items){dupe_note}{bin_note}."
        )

    def _scan_large_files(self):
        """Find files over 100 MB across sweep roots."""
        roots = self._sweep_roots()
        if not roots:
            QMessageBox.information(self, "No roots", "No sweep roots found for large files.")
            return
        self.btn_scan_large.setEnabled(False)
        self.btn_clean_large.setEnabled(False)
        self.large_status.setText(f"Scanning {len(roots)} root(s) for files over 100 MB…")
        self._feed("Large-file scan started…")
        from .workers import LargeFilesWorker

        self._large_files = []
        self._large_pending = len(roots)
        for r in roots:
            w = LargeFilesWorker(str(r), 100.0)
            self._sweep_workers[f"large:{r}"] = w
            self.win.run_worker(w, self._on_large_chunk, self._on_extra_failed, on_progress=self._on_large_progress)

    def _on_large_progress(self, msg: str):
        self.large_status.setText(str(msg))

    def _on_large_chunk(self, entries: list):
        self._large_files.extend(entries or [])
        self._large_pending = max(0, getattr(self, "_large_pending", 1) - 1)
        if self._large_pending:
            self.large_status.setText(f"Scanning large files… {len(self._large_files):,} found so far…")
            return
        self._sweep_workers = {k: v for k, v in self._sweep_workers.items() if not k.startswith("large:")}
        self.btn_scan_large.setEnabled(True)
        total = sum(int(getattr(e, "size", 0) or 0) for e in self._large_files)
        if not self._large_files:
            self.large_status.setText("Large files: clean — nothing over 100 MB found.")
            self.btn_clean_large.setEnabled(False)
        else:
            self.large_status.setText(
                f"Large files: {len(self._large_files):,} file(s), {fmt_bytes(total)} — review before recycling."
            )
            self.btn_clean_large.setEnabled(True)
        self._feed(f"Large files: {len(self._large_files):,} found ({fmt_bytes(total)}).")

    def _clean_large_files(self):
        """Recycle listed large files after confirmation."""
        if not self._large_files:
            return
        if not self._no_confirm:
            total = sum(int(getattr(e, "size", 0) or 0) for e in self._large_files)
            confirm = QMessageBox.question(
                self,
                "Recycle large files?",
                f"Move {len(self._large_files):,} large file(s) ({fmt_bytes(total)}) to the Recycle Bin?\n\nReview the list in Large Files Finder first if unsure.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        from .workers import DeleteSelectedWorker

        paths = [str(getattr(e, "path", e)) for e in self._large_files]
        self.btn_clean_large.setEnabled(False)
        self.win.run_worker(DeleteSelectedWorker(paths, "recycle"), self._on_large_cleaned, self._on_extra_failed)

    def _on_large_cleaned(self, freed: int, ok: int, blocked: int):
        self.btn_scan_large.setEnabled(True)
        silent = "large" in self._silent_sweeps
        self._silent_sweeps.discard("large")
        if not silent:
            QMessageBox.information(
                self,
                "Done",
                f"Recycled {ok} large file(s), freed {fmt_bytes(freed)}." + (f" {blocked} blocked." if blocked else ""),
            )
        self._feed(f"Large files cleaned: {fmt_bytes(freed)}.")
        self._large_files = []
        self.large_status.setText("Large files: clean — nothing over 100 MB found.")
        self._update_mission_total()

    def _scan_empty_files(self):
        """Find 0-byte files + empty folders across code roots."""
        roots = self._sweep_roots()[:6]
        if not roots:
            QMessageBox.information(self, "No roots", "No sweep roots found for empty files.")
            return
        self.btn_scan_empty.setEnabled(False)
        self.btn_clean_empty.setEnabled(False)
        self.empty_status.setText(f"Scanning {len(roots)} root(s) for empty files…")
        self._feed("Empty-file scan started…")
        from .workers import EmptyWorker

        self._empty_files = []
        self._empty_dirs = []
        self._empty_pending = len(roots)
        for r in roots:
            w = EmptyWorker(str(r))
            self._sweep_workers[f"empty:{r}"] = w
            self.win.run_worker(w, self._on_empty_chunk, self._on_extra_failed)

    def _on_empty_chunk(self, files: list, dirs: list):
        self._empty_files.extend(files or [])
        self._empty_dirs.extend(dirs or [])
        self._empty_pending = max(0, getattr(self, "_empty_pending", 1) - 1)
        if self._empty_pending:
            return
        self._sweep_workers = {k: v for k, v in self._sweep_workers.items() if not k.startswith("empty:")}
        self.btn_scan_empty.setEnabled(True)
        n = len(self._empty_files) + len(self._empty_dirs)
        if not n:
            self.empty_status.setText("Empty files: clean — nothing found.")
            self.btn_clean_empty.setEnabled(False)
        else:
            self.empty_status.setText(
                f"Empty: {len(self._empty_files):,} file(s) + {len(self._empty_dirs):,} folder(s) — safe to recycle."
            )
            self.btn_clean_empty.setEnabled(True)
        self._feed(f"Empty scan: {n:,} item(s).")

    def _clean_empty_files(self):
        """Recycle empty files and folders."""
        if not (self._empty_files or self._empty_dirs):
            return
        if not self._no_confirm:
            confirm = QMessageBox.question(
                self,
                "Recycle empty items?",
                f"Move {len(self._empty_files):,} empty file(s) + {len(self._empty_dirs):,} empty folder(s) to the Recycle Bin?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        from .workers import DeleteSelectedWorker

        paths = [str(p) for p in ([*self._empty_files, *self._empty_dirs])]
        self.btn_clean_empty.setEnabled(False)
        self.win.run_worker(DeleteSelectedWorker(paths, "recycle"), self._on_empty_cleaned, self._on_extra_failed)

    def _on_empty_cleaned(self, freed: int, ok: int, blocked: int):
        self.btn_scan_empty.setEnabled(True)
        silent = "empty" in self._silent_sweeps
        self._silent_sweeps.discard("empty")
        if not silent:
            QMessageBox.information(
                self, "Done", f"Recycled {ok} empty item(s)." + (f" {blocked} blocked." if blocked else "")
            )
        self._feed(f"Empty cleaned: {ok:,} item(s).")
        self._empty_files = []
        self._empty_dirs = []
        self.empty_status.setText("Empty files: clean — nothing found.")
        self._update_mission_total()

    def _scan_duplicates(self):
        """Estimate byte-identical duplicate waste (review-only)."""
        roots = self._sweep_roots()[:6]
        if not roots:
            QMessageBox.information(self, "No roots", "No sweep roots found for duplicates.")
            return
        self.btn_scan_dupes.setEnabled(False)
        self.dupes_status.setText(f"Hashing duplicates across {len(roots)} root(s)…")
        self._feed("Duplicate scan started…")
        from .workers import DuplicateWorker

        w = DuplicateWorker([str(r) for r in roots])
        self._sweep_workers["dupes"] = w
        self.win.run_worker(w, self._on_dupes_done, self._on_extra_failed, on_progress=self._on_dupes_progress)

    def _on_dupes_progress(self, msg: str):
        self.dupes_status.setText(str(msg))

    def _on_dupes_done(self, groups: dict):
        self._sweep_workers.pop("dupes", None)
        self.btn_scan_dupes.setEnabled(True)
        self._dupe_groups = dict(groups or {})
        waste = 0
        n_dupes = 0
        try:
            from pathlib import Path as _P

            for _h, paths in self._dupe_groups.items():
                if len(paths) < 2:
                    continue
                try:
                    sz = _P(paths[0]).stat().st_size
                except OSError:
                    continue
                waste += sz * (len(paths) - 1)
                n_dupes += len(paths) - 1
        except Exception:  # noqa: BLE001
            pass
        self._dupe_waste = int(waste)
        if not n_dupes:
            self.dupes_status.setText("Duplicates: clean — no byte-identical copies found.")
        else:
            self.dupes_status.setText(
                f"Duplicates: {n_dupes:,} redundant copies, {fmt_bytes(waste)} waste — Review in Tool."
            )
        self._feed(f"Duplicates: {fmt_bytes(waste)} waste.")
        self._update_mission_total()

    def _scan_everything(self):
        """Master scan: all fast sweeps at once."""
        self._feed("Scan Everything started…")
        self._scan()
        try:
            self._scan_temp()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._scan_project_caches()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._scan_extra_logs()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._scan_large_files()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._scan_empty_files()
        except Exception:  # noqa: BLE001
            pass
        try:
            self._scan_duplicates()
        except Exception:  # noqa: BLE001
            pass

    def _clean_everything_safe(self):
        """Master clean: one confirm, then all safe hits."""
        sys_b = self._sweep_bytes("system")
        tmp_b = self._sweep_bytes("temp")
        proj_b = sum(int(r.get("size_bytes", 0) or 0) for r in self._proj_resources)
        log_b = sum(int(sz) for _, sz in self._extra_logs)
        large_b = sum(int(getattr(e, "size", 0) or 0) for e in self._large_files)
        total = sys_b + tmp_b + proj_b + log_b + large_b
        n = 0
        try:
            n += int(self._report.total_files) if self._report else 0
            n += (
                len(self._temp_findings)
                + len(self._proj_resources)
                + len(self._extra_logs)
                + len(self._large_files)
                + len(self._empty_files)
                + len(self._empty_dirs)
            )
        except Exception:  # noqa: BLE001
            pass
        if not total and not n:
            QMessageBox.information(self, "Nothing to clean", "Run Scan Everything first — no safe hits found yet.")
            return
        confirm = QMessageBox.question(
            self,
            "Clean everything safe?",
            f"Recycle {n:,} safe item(s) ({fmt_bytes(total)}) across system caches, temp, project, logs, large + empty?\n\n"
            "Everything above moves to the Recycle Bin (reversible) — empty the bin below to free the space. "
            "Duplicates and HIGH-risk items are NEVER auto-deleted — review them in their tools. "
            "The Recycle Bin is never auto-emptied either."
            + (
                f"\n\nDuplicate waste seen: {fmt_bytes(self._dupe_waste)} (left untouched)." if self._dupe_waste else ""
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._no_confirm = True
        self._silent_sweeps = set()
        self._feed("Clean Everything started…")
        try:
            if self._report and self._report.total_files:
                self._select_safe_cards()
                self._silent_sweeps.add("system")
                self._clean_silent_system()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._temp_findings:
                self._do_temp_clean_silent()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._proj_resources:
                self._do_proj_clean_silent()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._extra_logs:
                self._do_logs_clean_silent()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._large_files:
                self._silent_sweeps.add("large")
                self._clean_large_files()
        except Exception:  # noqa: BLE001
            pass
        try:
            if self._empty_files or self._empty_dirs:
                self._silent_sweeps.add("empty")
                self._clean_empty_files()
        except Exception:  # noqa: BLE001
            pass
        self._no_confirm = False
        self._feed("Clean Everything dispatched — each sweep reports as it finishes.")

    def _clean_silent_system(self):
        """System safe-clean without a second confirm."""
        from cortex_unified.engine.service import CleanupReport

        selected_ids = [cid for cid, on in self._selected.items() if on]
        if not selected_ids:
            return
        filtered = CleanupReport(
            scans=[s for s in self._report.scans if s.category.id in selected_ids],
            duration_seconds=self._report.duration_seconds,
        )
        if not filtered.total_files:
            return
        from cortex_unified.engine import DeletionMethod

        self.clean_btn.setEnabled(False)
        self.clean_all_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.scan_status.setText("Cleaning selected categories…")
        from .workers import CleanWorker

        w = CleanWorker(filtered, DeletionMethod.RECYCLE.value, allow_system=True)
        self.win.run_worker(w, self._on_cleaned, self._fail, on_progress=self._on_progress)

    def _do_temp_clean_silent(self):
        """Deep-temp clean without dialogs (master mode)."""
        from cortex_unified.core.temp_cleaner import TempCleaner

        res = TempCleaner(min_age_days=1).clean(self._temp_findings, use_trash=True, dry_run=False)
        self._feed(f"Temp cleaned: {fmt_bytes(int(res.get('bytes_freed', 0)))}.")
        self._temp_findings = []
        self.btn_clean_temp.setEnabled(False)
        self.btn_clean_temp.setVisible(False)
        self.temp_result_label.setText("")
        self._update_mission_total()

    def _do_proj_clean_silent(self):
        """Project-cache clean without dialogs (master mode)."""
        from .workers import ProjectCacheCleanWorker

        self.btn_clean_proj.setEnabled(False)
        w = ProjectCacheCleanWorker(list(self._proj_resources), dry_run=False)
        self._sweep_workers["proj_clean"] = w
        self.win.run_worker(w, self._on_proj_master_cleaned, self._on_extra_failed)

    def _on_proj_master_cleaned(self, results: dict):
        self._sweep_workers.pop("proj_clean", None)
        self.btn_scan_proj.setEnabled(True)
        freed = int((results or {}).get("total_freed_bytes", (results or {}).get("freed_bytes", 0)) or 0)
        self._feed(f"Project caches cleaned: {fmt_bytes(freed)}.")
        self._proj_resources = []
        self.proj_status.setText("Project caches: clean — nothing found.")
        self._update_mission_total()

    def _do_logs_clean_silent(self):
        """Large-log clean without dialogs (master mode)."""
        from .workers import DeleteSelectedWorker

        paths = [str(p) for p, _ in self._extra_logs]
        self.btn_clean_logs.setEnabled(False)
        self.win.run_worker(DeleteSelectedWorker(paths, "recycle"), self._on_logs_master_cleaned, self._on_extra_failed)

    def _on_logs_master_cleaned(self, freed: int, ok: int, _blocked: int):
        self.btn_scan_logs.setEnabled(True)
        self._feed(f"Logs cleaned: {fmt_bytes(freed)}.")
        self._extra_logs = []
        self.logs_status.setText("Large logs: clean — nothing over 20 MB found.")
        self._update_mission_total()

    def _open_tool(self, page_id: str):
        """Jump to any cleaner tool in one click."""
        try:
            self.win._select(page_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Navigation", f"Could not open {page_id}:\n{exc}")

    def _build_all_tools_grid(self):
        """Build the all-clean-tools directory (Open buttons, grouped)."""
        try:
            from .registry import PAGES
        except Exception:  # noqa: BLE001
            return
        while self.tools_grid.count():
            item = self.tools_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        wanted_groups = ("cleanup", "maintenance", "system", "activity", "apps", "security")
        specs = [p for p in PAGES if p.group in wanted_groups and p.id != "cleanuphub"]
        keep = {
            "duplicates",
            "photos",
            "dupfolders",
            "large",
            "empty",
            "analyzer",
            "brokenlinks",
            "logsweep",
            "packages",
            "projcaches",
            "modelcache",
            "neardup",
            "perceptual",
            "registryai",
            "fuzzyhash",
            "audio",
            "video",
            "cdc",
            "cloud",
            "portable",
            "crashdumps",
            "eventlogs",
            "devcleaner",
            "browserdeep",
            "imgopt",
            "fonts",
            "tempcleaner",
            "vdisks",
            "wsl",
            "compactos",
            "compstore",
            "systemcache",
            "startupopt",
            "privacy",
            "shellbags",
            "diagdata",
            "uninstaller",
            "advanced_uninstaller",
            "leftovers",
            "telemetry",
            "registry",
            "privacyblock",
            "winupdate",
            "winrepair",
            "diskanalyzer",
            "vssmanager",
            "sandbox",
            "shadercache",
            "aitelemetry",
            "vsshealth",
            "devpackage",
            "winapp2",
            "srumbam",
            "delivery",
            "oldfiles",
            "residuals",
        }
        specs = [p for p in specs if p.id in keep]
        order = {"cleanup": 0, "apps": 1, "activity": 2, "system": 3, "maintenance": 4, "security": 5}
        specs.sort(key=lambda p: (order.get(p.group, 9), p.title))
        wired = {"tempcleaner", "logsweep", "packages", "projcaches", "duplicates", "large", "empty"}
        cols = 3
        for idx, spec in enumerate(specs):
            card = Card(self.p, "BentoTile")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(12, 10, 12, 10)
            lay.setSpacing(4)
            t = QLabel(f"<b>{spec.title}</b>")
            t.setTextFormat(Qt.TextFormat.RichText)
            t.setWordWrap(True)
            lay.addWidget(t)
            sub = QLabel("Wired above — live status" if spec.id in wired else spec.group.capitalize())
            sub.setObjectName("Muted")
            lay.addWidget(sub)
            btn = QPushButton("Open")
            btn.setObjectName("Ghost")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, pid=spec.id: self._open_tool(pid))
            lay.addWidget(btn)
            r, c = divmod(idx, cols)
            self.tools_grid.addWidget(card, r, c)
        self.tools_title.setText(
            f"<b>All Clean Tools Directory</b> <span style='color:#8A93A8'>— {len(specs)} cleaners, one directory. "
            "Wired rows clean inline above; the rest open in one click.</span>"
        )

    def _auto_log_roots(self) -> list[Path]:
        """Code roots for the log sweep."""
        try:
            from cortex_unified.analyzers.project_cache_scanner import _known_code_roots

            known = [p for p in _known_code_roots() if p.is_dir()]
            if known:
                return known[:12]
        except Exception:  # noqa: BLE001
            pass
        out: list[Path] = []
        home = Path.home()
        for sub in ("code", "Projects", "source/repos", "workspace", "dev"):
            p = home / sub
            try:
                if p.is_dir():
                    out.append(p)
            except OSError:
                continue
        return out[:12]

    # -----------------------------------------------------------------------
    # Directory & File Target Pickers
    # -----------------------------------------------------------------------

    def _pick_custom_folder(self):
        """Prompt user with a directory dialog and scan the selected folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Scan", str(Path.home()))
        if folder:
            self._custom_roots = [Path(folder)]
            self._update_roots_status()
            if hasattr(self, "btn_target_full") and hasattr(self, "btn_target_sys"):
                self.btn_target_full.setObjectName("Ghost")
                self.btn_target_sys.setObjectName("Ghost")
                self._reapply_target_button_styles()
            self._scan()

    def _pick_custom_file(self):
        """Prompt user with a file dialog and scan the selected file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Scan", str(Path.home()))
        if file_path:
            self._custom_roots = [Path(file_path)]
            self._update_roots_status()
            if hasattr(self, "btn_target_full") and hasattr(self, "btn_target_sys"):
                self.btn_target_full.setObjectName("Ghost")
                self.btn_target_sys.setObjectName("Ghost")
                self._reapply_target_button_styles()
            self._scan()

    def _clear_custom_roots(self):
        """Reset custom scan targets back to default system partitions and rescan."""
        self._custom_roots.clear()
        self._update_roots_status()
        if hasattr(self, "btn_target_full") and hasattr(self, "btn_target_sys"):
            self.btn_target_full.setObjectName("Primary")
            self.btn_target_sys.setObjectName("Ghost")
            self._reapply_target_button_styles()
        self._scan()

    def _update_roots_status(self):
        """Update scan root status text and toggle reset button visibility."""
        if self._custom_roots:
            roots_str = ", ".join(str(r) for r in self._custom_roots)
            self.target_roots_label.setText(f"Active Scan Target: {roots_str}")
            self.btn_clear_roots.setText("Reset to Full Device Scan")
            self.btn_clear_roots.setVisible(True)
        else:
            self.target_roots_label.setText("Active Scan Roots: Full Device (System Caches • All Drives • AppData)")
            self.btn_clear_roots.setVisible(False)

    # -----------------------------------------------------------------------
    # Cleaning Action Triggers
    # -----------------------------------------------------------------------

    def _clean_all_safe(self):
        """One-click full-device clean: tick all LOW+MEDIUM hits, leave HIGH unticked, then clean."""
        if self._report is None or self._report.total_files == 0:
            QMessageBox.information(self, "Nothing to clean", "Scan first — no reclaimable files found yet.")
            return
        self._select_safe_cards()
        self._clean()

    def _clean(self):
        """Confirm selection, then run CleanWorker on the selected categories (Recycle-Bin-safe delete)."""
        if self._report is None:
            return
        selected_ids = [cid for cid, on in self._selected.items() if on]
        if not selected_ids:
            QMessageBox.information(self, "Nothing selected", "Tick at least one category card first.")
            return

        from cortex_unified.engine.service import CleanupReport

        filtered = CleanupReport(
            scans=[s for s in self._report.scans if s.category.id in selected_ids],
            duration_seconds=self._report.duration_seconds,
        )
        total = filtered.total_reclaimable_bytes
        high_sel = sum(1 for s in filtered.scans if s.category.risk == RiskLevel.HIGH)
        high_note = f"\n\n⚠ Includes {high_sel} HIGH-risk categor(ies) — confirm carefully." if high_sel else ""
        confirm = QMessageBox.question(
            self,
            "Confirm cleanup",
            f"Move {len(filtered.scans)} category(ies), {filtered.total_files:,} file(s), "
            f"{fmt_bytes(total)} to the Recycle Bin?\n\nReversible — restore from the bin if anything was needed. "
            f"Locked/in-use files are skipped. Empty the Recycle Bin row below afterwards to free the space.{high_note}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from cortex_unified.engine import DeletionMethod

        self.clean_btn.setEnabled(False)
        self.clean_all_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.scan_status.setText("Cleaning selected categories…")
        from .workers import CleanWorker

        w = CleanWorker(filtered, DeletionMethod.RECYCLE.value, allow_system=True)
        self.win.run_worker(w, self._on_cleaned, self._fail, on_progress=self._on_progress)

    def _on_cleaned(self, freed: int, items: int, skipped: int):
        """Report freed bytes and item counts after cleanup finishes."""
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        silent = "system" in self._silent_sweeps
        self._silent_sweeps.discard("system")
        extra = (
            f" {skipped} locked/protected/skipped (in-use files, cloud placeholders, or HIGH-risk left unticked)."
            if skipped
            else ""
        )
        done_msg = (
            f"Moved {fmt_bytes(freed)} ({items} item(s)) to the Recycle Bin.{extra}\n\n"
            "Space is freed for real once the Recycle Bin row below is emptied."
        )
        if silent:
            self._feed(f"System caches recycled: {fmt_bytes(freed)} (empty the bin to free it).")
        else:
            QMessageBox.information(self, "Cleanup done — check the Recycle Bin", done_msg)
        self.win.statusBar().showMessage(f"Recycled {fmt_bytes(freed)} to bin — empty the bin to free it", 6000)
        self._scan()
