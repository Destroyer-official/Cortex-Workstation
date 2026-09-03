"""Startup Optimizer page — stagger/delay engine with resource-aware gating.

Enumerates Windows autostart entries (registry, startup folders, scheduled
tasks), classifies each by resource profile (GUI-heavy, network-bound,
service-dependent, background), and lets the user enable/disable entries
with real-time progress feedback.
"""

from __future__ import annotations

import enum
import logging
import threading
from typing import List

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .states import StatePanel
from .widgets import Card, title_block
from .window import _Page

_LOG = logging.getLogger("cortex.ui.premium.startup_optimizer")


# ---------------------------------------------------------------------------
# Worker helpers
# ---------------------------------------------------------------------------


class _StartupScanWorker(QObject):
    """Background worker: enumerate all startup entries."""

    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self):
        """__init__."""
        super().__init__()
        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.startup_optimizer import StartupOptimizer

            opt = StartupOptimizer(
                progress=lambda msg: self.progress.emit(str(msg)),
                cancel=self._cancel,
            )
            entries = opt.enumerate()
            self.finished.emit(entries)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _DisableWorker(QObject):
    """Disable selected startup entries by toggling registry values."""

    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, entries: list):
        """__init__."""
        super().__init__()
        self._entries = entries
        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            import winreg

            disabled: list = []
            for entry in self._entries:
                if self._cancel.is_set():
                    break
                loc = getattr(entry, "location", "")
                name = getattr(entry, "name", "")
                self.progress.emit(f"Disabling {name}…")
                if not loc.startswith("HK"):
                    self.progress.emit(f"Skipping {name}: non-registry entry")
                    continue
                try:
                    if loc.startswith("HKCU"):
                        hive = winreg.HKEY_CURRENT_USER
                        sub = loc[5:]
                    elif loc.startswith("HKLM"):
                        hive = winreg.HKEY_LOCAL_MACHINE
                        sub = loc[5:]
                    else:
                        continue
                    with winreg.OpenKey(hive, sub, 0, winreg.KEY_WRITE) as key:
                        val, _ = winreg.QueryValueEx(key, name)
                        winreg.DeleteValue(key, name)
                        # Stash in backup location so we can re-enable
                        backup_sub = sub.replace(
                            "CurrentVersion\\Run",
                            "CurrentVersion\\Run\\CortexBackup",
                        )
                        try:
                            with winreg.CreateKey(hive, backup_sub) as bk:
                                winreg.SetValueEx(bk, name, 0, winreg.REG_SZ, val)
                        except OSError:
                            pass
                    disabled.append(entry)
                except OSError as exc:
                    self.progress.emit(f"Failed to disable {name}: {exc}")
            self.finished.emit(disabled)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _EnableWorker(QObject):
    """Re-enable startup entries from the Cortex backup registry location."""

    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, entries: list):
        """__init__."""
        super().__init__()
        self._entries = entries
        self._cancel = threading.Event()

    def cancel(self):
        """cancel."""
        self._cancel.set()

    def run(self):
        """run."""
        try:
            import winreg

            enabled: list = []
            for entry in self._entries:
                if self._cancel.is_set():
                    break
                loc = getattr(entry, "location", "")
                name = getattr(entry, "name", "")
                self.progress.emit(f"Enabling {name}…")
                if not loc.startswith("HK"):
                    self.progress.emit(f"Skipping {name}: non-registry entry")
                    continue
                try:
                    if loc.startswith("HKCU"):
                        hive = winreg.HKEY_CURRENT_USER
                        sub = loc[5:]
                    elif loc.startswith("HKLM"):
                        hive = winreg.HKEY_LOCAL_MACHINE
                        sub = loc[5:]
                    else:
                        continue
                    backup_sub = sub.replace(
                        "CurrentVersion\\Run",
                        "CurrentVersion\\Run\\CortexBackup",
                    )
                    with winreg.OpenKey(hive, backup_sub, 0, winreg.KEY_READ) as bk:
                        val, _ = winreg.QueryValueEx(bk, name)
                    with winreg.OpenKey(hive, sub, 0, winreg.KEY_WRITE) as key:
                        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, val)
                    try:
                        with winreg.OpenKey(
                            hive, backup_sub, 0, winreg.KEY_WRITE
                        ) as bk:
                            winreg.DeleteValue(bk, name)
                    except OSError:
                        pass
                    enabled.append(entry)
                except OSError as exc:
                    self.progress.emit(f"Failed to enable {name}: {exc}")
            self.finished.emit(enabled)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Type filter helpers
# ---------------------------------------------------------------------------

_TYPE_FILTERS = ("All", "GUI", "Network", "Service", "Background")
_SORT_KEYS = ("Name", "Type", "Impact")

_IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2, "unknown": 3}


def _entry_type_label(entry) -> str:
    """_entry_type_label."""
    if getattr(entry, "is_gui_heavy", False):
        return "GUI"
    if getattr(entry, "is_network_bound", False):
        return "Network"
    if getattr(entry, "is_service_dependent", False):
        return "Service"
    cat = getattr(entry, "category", "")
    if cat in ("service", "driver"):
        return "Service"
    return "Background"


def _entry_matches_filter(entry, type_filter: str) -> bool:
    """_entry_matches_filter."""
    if type_filter == "All":
        return True
    return _entry_type_label(entry) == type_filter


def _sort_entries(entries: list, sort_key: str) -> list:
    """_sort_entries."""
    if sort_key == "Name":
        return sorted(entries, key=lambda e: getattr(e, "name", "").lower())
    if sort_key == "Type":
        return sorted(entries, key=lambda e: _entry_type_label(e))
    if sort_key == "Impact":
        return sorted(
            entries,
            key=lambda e: _IMPACT_ORDER.get(getattr(e, "impact", "unknown"), 3),
        )
    return entries


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

_COLUMNS = ("Name", "Type", "Path", "Command", "Impact", "Status")


class StartupOptimizerPage(_Page):
    """Manage Windows startup entries — enable, disable, and inspect resource impact."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(
            title_block(
                "Startup Optimizer",
                "Enumerates registry, startup folders, and scheduled tasks. "
                "Classify entries by resource profile (GUI / Network / Service / "
                "Background) and toggle them on or off with a single click.",
            )
        )

        # --- top controls ---------------------------------------------------
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("Ghost")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._run_scan)
        ctrl.addWidget(self.refresh_btn)

        ctrl.addSpacing(12)

        filter_lbl = QLabel("Type:")
        filter_lbl.setObjectName("Muted")
        ctrl.addWidget(filter_lbl)

        self.type_combo = QComboBox()
        self.type_combo.addItems(_TYPE_FILTERS)
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        self.type_combo.setMinimumWidth(110)
        ctrl.addWidget(self.type_combo)

        ctrl.addSpacing(8)

        sort_lbl = QLabel("Sort:")
        sort_lbl.setObjectName("Muted")
        ctrl.addWidget(sort_lbl)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(_SORT_KEYS)
        self.sort_combo.currentTextChanged.connect(self._apply_filters)
        self.sort_combo.setMinimumWidth(100)
        ctrl.addWidget(self.sort_combo)

        ctrl.addStretch(1)

        self.disable_btn = QPushButton("Disable Selected")
        self.disable_btn.setObjectName("Danger")
        self.disable_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.disable_btn.clicked.connect(self._disable_selected)
        self.disable_btn.setEnabled(False)
        ctrl.addWidget(self.disable_btn)

        self.enable_btn = QPushButton("Enable Selected")
        self.enable_btn.setObjectName("Primary")
        self.enable_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.enable_btn.clicked.connect(self._enable_selected)
        self.enable_btn.setEnabled(False)
        ctrl.addWidget(self.enable_btn)

        self.v.addLayout(ctrl)

        # --- summary cards --------------------------------------------------
        card_row = QHBoxLayout()
        card_row.setSpacing(12)

        self.card_total = Card(self.p, "BentoTile")
        lay_t = QVBoxLayout(self.card_total)
        lay_t.setContentsMargins(16, 12, 16, 12)
        lay_t.setSpacing(2)
        self.val_total = QLabel("—")
        self.val_total.setObjectName("Metric")
        self.cap_total = QLabel("TOTAL ENTRIES")
        self.cap_total.setObjectName("MetricLabel")
        lay_t.addWidget(self.val_total)
        lay_t.addWidget(self.cap_total)
        card_row.addWidget(self.card_total)

        self.card_enabled = Card(self.p, "BentoTile")
        lay_e = QVBoxLayout(self.card_enabled)
        lay_e.setContentsMargins(16, 12, 16, 12)
        lay_e.setSpacing(2)
        self.val_enabled = QLabel("—")
        self.val_enabled.setObjectName("Metric")
        self.cap_enabled = QLabel("ENABLED")
        self.cap_enabled.setObjectName("MetricLabel")
        lay_e.addWidget(self.val_enabled)
        lay_e.addWidget(self.cap_enabled)
        card_row.addWidget(self.card_enabled)

        self.card_disabled = Card(self.p, "BentoTile")
        lay_d = QVBoxLayout(self.card_disabled)
        lay_d.setContentsMargins(16, 12, 16, 12)
        lay_d.setSpacing(2)
        self.val_disabled = QLabel("—")
        self.val_disabled.setObjectName("Metric")
        self.cap_disabled = QLabel("DISABLED")
        self.cap_disabled.setObjectName("MetricLabel")
        lay_d.addWidget(self.val_disabled)
        lay_d.addWidget(self.cap_disabled)
        card_row.addWidget(self.card_disabled)

        self.card_high = Card(self.p, "BentoTile")
        lay_h = QVBoxLayout(self.card_high)
        lay_h.setContentsMargins(16, 12, 16, 12)
        lay_h.setSpacing(2)
        self.val_high = QLabel("—")
        self.val_high.setObjectName("Metric")
        self.cap_high = QLabel("HIGH IMPACT")
        self.cap_high.setObjectName("MetricLabel")
        lay_h.addWidget(self.val_high)
        lay_h.addWidget(self.cap_high)
        card_row.addWidget(self.card_high)

        self.v.addLayout(card_row)

        # --- progress + status ----------------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.v.addWidget(self.status)

        # --- results table --------------------------------------------------
        self.tbl = QTableWidget(0, len(_COLUMNS))
        self.tbl.setHorizontalHeaderLabels(_COLUMNS)
        header = self.tbl.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.itemSelectionChanged.connect(self._update_buttons)
        self.v.addWidget(self.tbl, 1)

        # --- state panel (empty / error overlay) ---------------------------
        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        # --- internal state -------------------------------------------------
        self._all_entries: list = []
        self._visible_entries: list = []
        self._worker = None

        # Auto-scan on first show
        self._run_scan()

    # -- scan ---------------------------------------------------------------

    def _run_scan(self):
        """_run_scan."""
        self.refresh_btn.setEnabled(False)
        self.disable_btn.setEnabled(False)
        self.enable_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Enumerating startup entries…")
        self.status.setText("Scanning registry, folders, and scheduled tasks…")
        self.tbl.setRowCount(0)
        w = _StartupScanWorker()
        self._worker = w
        self.win.run_worker(
            w,
            self._on_scan_done,
            self._on_scan_fail,
            on_progress=self._on_scan_progress,
        )

    def _on_scan_progress(self, msg: str):
        """_on_scan_progress."""
        self.status.setText(msg)

    def _on_scan_done(self, entries: list):
        """_on_scan_done."""
        self._worker = None
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self._all_entries = entries
        if not entries:
            self.state.show_empty(
                "No startup entries found. This is unusual — check that "
                "you have administrative privileges."
            )
            self.status.setText("No entries found.")
            self._update_summary()
            return
        self.state.clear()
        self.status.setText(f"Found {len(entries)} startup entries.")
        self._apply_filters()
        self._update_buttons()

    def _on_scan_fail(self, msg: str):
        """_on_scan_fail."""
        self._worker = None
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run_scan)

    # -- filtering / sorting ------------------------------------------------

    def _apply_filters(self, *_args):
        """_apply_filters."""
        type_filter = self.type_combo.currentText()
        sort_key = self.sort_combo.currentText()
        filtered = [
            e for e in self._all_entries if _entry_matches_filter(e, type_filter)
        ]
        self._visible_entries = _sort_entries(filtered, sort_key)
        self._populate_table(self._visible_entries)
        self._update_summary()
        self._update_buttons()

    def _populate_table(self, entries: list):
        """_populate_table."""
        self.tbl.setRowCount(len(entries))
        for r, entry in enumerate(entries):
            self.tbl.setItem(r, 0, QTableWidgetItem(getattr(entry, "name", "")))
            self.tbl.setItem(r, 1, QTableWidgetItem(_entry_type_label(entry)))
            loc = getattr(entry, "location", "")
            self.tbl.setItem(r, 2, QTableWidgetItem(loc))
            self.tbl.setItem(r, 3, QTableWidgetItem(getattr(entry, "command", "")))
            impact = getattr(entry, "impact", "unknown")
            impact_item = QTableWidgetItem(impact.capitalize())
            if impact == "high":
                impact_item.setForeground(Qt.GlobalColor.red)
            elif impact == "medium":
                impact_item.setForeground(Qt.GlobalColor.yellow)
            else:
                impact_item.setForeground(Qt.GlobalColor.green)
            self.tbl.setItem(r, 4, impact_item)
            status = "Enabled" if getattr(entry, "enabled", True) else "Disabled"
            self.tbl.setItem(r, 5, QTableWidgetItem(status))
        self._update_summary()

    # -- summary cards ------------------------------------------------------

    def _update_summary(self):
        """_update_summary."""
        total = len(self._all_entries)
        enabled = sum(1 for e in self._all_entries if getattr(e, "enabled", True))
        disabled = total - enabled
        high = sum(1 for e in self._all_entries if getattr(e, "impact", "") == "high")
        self.val_total.setText(str(total))
        self.val_enabled.setText(str(enabled))
        self.val_disabled.setText(str(disabled))
        self.val_high.setText(str(high))

    # -- selection ----------------------------------------------------------

    def _selected_entries(self) -> list:
        """_selected_entries."""
        rows = sorted({idx.row() for idx in self.tbl.selectedIndexes()})
        return [
            self._visible_entries[r] for r in rows if r < len(self._visible_entries)
        ]

    def _update_buttons(self):
        """_update_buttons."""
        has_sel = bool(self.tbl.selectedItems())
        self.disable_btn.setEnabled(has_sel)
        self.enable_btn.setEnabled(has_sel)

    # -- disable ------------------------------------------------------------

    def _disable_selected(self):
        """_disable_selected."""
        sel = self._selected_entries()
        if not sel:
            return
        self.disable_btn.setEnabled(False)
        self.enable_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(f"Disabling {len(sel)} entries…")
        self.status.setText(f"Disabling {len(sel)} startup entries…")
        w = _DisableWorker(sel)
        self._worker = w
        self.win.run_worker(
            w,
            self._on_disable_done,
            self._on_disable_fail,
            on_progress=self._on_action_progress,
        )

    def _on_disable_done(self, disabled: list):
        """_on_disable_done."""
        self._worker = None
        self.progress.setVisible(False)
        self.status.setText(f"Disabled {len(disabled)} entries.")
        self.win.statusBar().showMessage(
            f"Disabled {len(disabled)} startup entries", 5000
        )
        self._run_scan()

    def _on_disable_fail(self, msg: str):
        """_on_disable_fail."""
        self._worker = None
        self.progress.setVisible(False)
        self.state.show_error(msg, on_retry=self._disable_selected)

    # -- enable -------------------------------------------------------------

    def _enable_selected(self):
        """_enable_selected."""
        sel = self._selected_entries()
        if not sel:
            return
        self.disable_btn.setEnabled(False)
        self.enable_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(f"Enabling {len(sel)} entries…")
        self.status.setText(f"Enabling {len(sel)} startup entries…")
        w = _EnableWorker(sel)
        self._worker = w
        self.win.run_worker(
            w,
            self._on_enable_done,
            self._on_enable_fail,
            on_progress=self._on_action_progress,
        )

    def _on_enable_done(self, enabled: list):
        """_on_enable_done."""
        self._worker = None
        self.progress.setVisible(False)
        self.status.setText(f"Enabled {len(enabled)} entries.")
        self.win.statusBar().showMessage(
            f"Enabled {len(enabled)} startup entries", 5000
        )
        self._run_scan()

    def _on_enable_fail(self, msg: str):
        """_on_enable_fail."""
        self._worker = None
        self.progress.setVisible(False)
        self.state.show_error(msg, on_retry=self._enable_selected)

    # -- shared action progress ---------------------------------------------

    def _on_action_progress(self, msg: str):
        """_on_action_progress."""
        self.status.setText(msg)
