"""Additional premium pages: Software Updater, Drive Optimizer, System Info.

These wrap the new backend modules (app_updater, drive_optimizer, system_info)
with background workers, confirmation dialogs for anything system-modifying, and
lazy-loading. Kept separate from window.py/system_pages.py for modularity.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, Signal, QThread
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cortex_unified.licensing import Feature
from cortex_unified.analyzers.broken_link_detector import BrokenLinkDetector
from cortex_unified.analyzers.duplicate_folder_finder import DuplicateFolderFinder
from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner

from .states import StatePanel
from .tablemodel import Column, TableBinding, bind_table
from .tokens import Spacing
from .widgets import Card, StatCard, require_feature, status_note, title_block
from .window import _Page, fmt_bytes

# ``sys.platform`` is an interned constant; ``platform.system()`` costs ~50 ms
# on its first call because it populates ``uname()`` via WMI on Windows.
IS_WINDOWS = sys.platform == "win32"


def _windows_only(page: _Page, feature: str) -> bool:
    """Return True (after showing a notice on *page*) unless on Windows.

    Args:
        page: The page widget to attach the notice to.
        feature: Human-readable feature name for the notice text.
    Returns:
        True if the current platform is not Windows (notice shown),
        False on Windows (caller should proceed).
    """
    if IS_WINDOWS:
        return False
    note = status_note(
        page.p, "info", f"{feature} is only available on Windows.")
    page.v.addWidget(note)
    page.v.addStretch(1)
    return True


def _allow_multi_select(table: QTableWidget) -> None:
    """Configure *table* for multi-row selection.

    Args:
        table: The QTableWidget to configure.
    """
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)


def _selected_records(table: QTableWidget) -> list[dict]:
    """Return the dicts stored in UserRole(0) for every selected row.

    Args:
        table: The QTableWidget to query.
    Returns:
        List of record dicts from the UserRole data of selected rows.
    """
    rows = sorted({idx.row() for idx in table.selectedIndexes()})
    out: list[dict] = []
    for r in rows:
        item = table.item(r, 0)
        if item is not None:
            rec = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(rec, dict):
                out.append(rec)
    return out


# =====================================================================
#  Workers
# =====================================================================

class UpdaterListWorker(QObject):
    """Worker that lists available app updates via AppUpdater."""
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """Execute the listing operation and emit results or failure."""
        try:
            from cortex_unified.system_tools.app_updater import AppUpdater
            self.finished.emit([a.to_dict() for a in AppUpdater().list_upgradable()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class UpgradeWorker(QObject):
    """Worker that applies upgrades for the given package IDs."""
    finished = Signal(int, int)   # (succeeded, total)
    failed = Signal(str)

    def __init__(self, package_ids: list[str]):
        """Store the package IDs to upgrade."""
        super().__init__()
        self._ids = package_ids

    def run(self):
        """Execute upgrades for all package IDs and emit results."""
        try:
            from cortex_unified.system_tools.app_updater import AppUpdater
            up = AppUpdater()
            ok = 0
            for pid in self._ids:
                success, _ = up.upgrade(pid)
                ok += 1 if success else 0
            self.finished.emit(ok, len(self._ids))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DriveListWorker(QObject):
    """Worker that lists drives via DriveOptimizer."""
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """Execute the drive listing operation and emit results."""
        try:
            from cortex_unified.system_tools.drive_optimizer import DriveOptimizer
            self.finished.emit([d.to_dict() for d in DriveOptimizer().list_drives()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DriveOptimizeWorker(QObject):
    """Worker that optimizes a specific drive."""
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, letter: str):
        """__init__."""
        super().__init__()
        self._letter = letter

    def run(self):
        """Execute drive optimization and emit success status and message."""
        try:
            from cortex_unified.system_tools.drive_optimizer import DriveOptimizer
            res = DriveOptimizer().optimize(self._letter)
            self.finished.emit(res.success, res.message)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SystemInfoWorker(QObject):
    """Worker that collects system information via SystemInfo."""
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
        """Execute system info collection and emit the snapshot dict."""
        try:
            from cortex_unified.system_tools.system_info import SystemInfo
            self.finished.emit(SystemInfo().snapshot())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Software Updater
# =====================================================================

class SoftwareUpdaterPage(_Page):
    """List and apply app updates via winget."""

    def __init__(self, win):
        """Initialize the Software Updater page.

        Args:
            win: Parent window instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Software Updater",
            "Keep installed applications current via official Windows Package Manager (winget) repositories. Works cleanly without bundled extras.",
        ))
        if _windows_only(self, "The Software Updater"):
            return
        from cortex_unified.system_tools.app_updater import AppUpdater
        if not AppUpdater.is_available():
            note = status_note(
                self.p, "warning",
                "winget (Windows Package Manager) was not found. Install "
                "'App Installer' from the Microsoft Store to enable updates.")
            self.v.addWidget(note)
            self.v.addStretch(1)
            return

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Check for Updates")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.update_sel_btn = QPushButton("Update Selected")
        self.update_sel_btn.setEnabled(False)
        self.update_sel_btn.clicked.connect(self._update_selected)
        row.addWidget(self.update_sel_btn)
        self.update_all_btn = QPushButton("Update All")
        self.update_all_btn.setObjectName("Primary")
        self.update_all_btn.setEnabled(False)
        self.update_all_btn.clicked.connect(self._update_all)
        row.addWidget(self.update_all_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Application", "Installed", "Available", "Id"])
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Load and display available app updates."""
        self.refresh_btn.setEnabled(False)
        self.update_sel_btn.setEnabled(False)
        self.update_all_btn.setEnabled(False)
        self.state.show_loading("Checking for updates\u2026")
        self.win.statusBar().showMessage("Checking for updates\u2026")
        self.win.run_worker(UpdaterListWorker(), self._on_listed, self._fail)

    def _on_listed(self, apps: list):
        """Handle the list of available updates from the worker.

        Args:
            apps: List of app dicts returned by UpdaterListWorker.
        """
        if not apps:
            self.state.show_empty("All apps are up to date.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        self.tbl.setRowCount(len(apps))
        for r, a in enumerate(apps):
            id_item = QTableWidgetItem(a["id"])
            name_item = QTableWidgetItem(a["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, a["id"])
            self.tbl.setItem(r, 0, name_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(a["current"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(a["available"]))
            self.tbl.setItem(r, 3, id_item)
        has = bool(apps)
        self.update_sel_btn.setEnabled(has)
        self.update_all_btn.setEnabled(has)
        self.win.statusBar().showMessage(
            "All apps are up to date." if not has else f"{len(apps)} update(s) available", 5000)

    def _selected_ids(self) -> list[str]:
        """Return the package IDs of selected rows in the table.

        Returns:
            List of package ID strings from selected rows.
        """
        rows = {idx.row() for idx in self.tbl.selectedIndexes()}
        return [self.tbl.item(r, 3).text() for r in sorted(rows) if self.tbl.item(r, 3)]

    def _update_selected(self):
        """Handle the 'Update Selected' button click."""
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "No selection", "Select one or more apps to update.")
            return
        self._run_updates(ids, f"Update {len(ids)} selected app(s)?")

    def _update_all(self):
        """Handle the 'Update All' button click."""
        ids = [self.tbl.item(r, 3).text() for r in range(self.tbl.rowCount()) if self.tbl.item(r, 3)]
        self._run_updates(ids, f"Update all {len(ids)} app(s)?")

    def _run_updates(self, ids: list[str], prompt: str):
        """Run upgrades for the given package IDs after user confirmation.

        Args:
            ids: List of package IDs to upgrade.
            prompt: Confirmation dialog text.
        """
        confirm = QMessageBox.question(
            self, "Confirm updates",
            prompt + "\n\nApps may close and restart during the update.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.progress.setVisible(True)
        self.update_sel_btn.setEnabled(False)
        self.update_all_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.win.statusBar().showMessage("Updating\u2026")
        self.win.run_worker(UpgradeWorker(ids), self._on_updated, self._fail)

    def _on_updated(self, ok: int, total: int):
        """Handle completion of the upgrade operation.

        Args:
            ok: Number of successfully updated packages.
            total: Total number of packages attempted.
        """
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        QMessageBox.information(self, "Updates complete", f"Updated {ok} of {total} app(s).")
        self.win.statusBar().showMessage(f"Updated {ok}/{total}", 6000)
        self._load()

    def _fail(self, msg: str):
        """_fail."""
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Drive Optimizer
# =====================================================================

class DriveOptimizerPage(_Page):
    """Media-aware TRIM (SSD) / defrag (HDD) - never defragments an SSD."""

    def __init__(self, win):
        """Initialize the Drive Optimizer page.

        Args:
            win: Parent window instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block(
            "Drive Optimizer",
            "Runs the correct maintenance per medium: TRIM for SSD/NVMe, defrag for HDD. "
            "It will never defragment a solid-state drive.",
        ))
        if _windows_only(self, "Drive optimization"):
            return

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Detect Drives")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.opt_btn = QPushButton("Optimize Selected")
        self.opt_btn.setObjectName("Primary")
        self.opt_btn.setEnabled(False)
        self.opt_btn.clicked.connect(self._optimize)
        row.addWidget(self.opt_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Drive", "Medium", "Recommended action"])
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(
            lambda: self.opt_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        note = QLabel("Note: optimization requires Administrator and can take several minutes on HDDs.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.v.addWidget(note)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Load and display drive information."""
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Detecting drives\u2026")
        self.win.run_worker(DriveListWorker(), self._on_listed, self._fail)

    def _on_listed(self, drives: list):
        """Handle the list of drives from the worker.

        Args:
            drives: List of drive dicts returned by DriveListWorker.
        """
        if not drives:
            self.state.show_empty("No fixed drives detected.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        self.tbl.setRowCount(len(drives))
        for r, d in enumerate(drives):
            letter_item = QTableWidgetItem(f"{d['letter']}:")
            letter_item.setData(Qt.ItemDataRole.UserRole, d["letter"])
            self.tbl.setItem(r, 0, letter_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(d["kind"]))
            op = d["recommended_op"]
            label = {"retrim": "TRIM (SSD)", "defrag": "Defragment (HDD)", "none": "\u2014"}.get(op, op)
            self.tbl.setItem(r, 2, QTableWidgetItem(f"{label}  \u2014  {d.get('note', '')}"))
        self.win.statusBar().showMessage(f"{len(drives)} fixed drive(s)", 5000)

    def _optimize(self):
        """Handle the 'Optimize Selected' button click."""
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        r = sel[0].row()
        letter = self.tbl.item(r, 0).data(Qt.ItemDataRole.UserRole)
        medium = self.tbl.item(r, 1).text()
        confirm = QMessageBox.question(
            self, "Optimize drive",
            f"Optimize drive {letter}: ({medium})?\n\n"
            "Requires Administrator. TRIM is quick; defragmenting an HDD may take a while.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.opt_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.statusBar().showMessage(f"Optimizing {letter}:\u2026")
        self.win.run_worker(DriveOptimizeWorker(letter), self._on_done, self._fail)

    def _on_done(self, success: bool, message: str):
        """Handle completion of the drive optimization.

        Args:
            success: Whether the optimization succeeded.
            message: Result message from the worker.
        """
        self.progress.setVisible(False)
        self.opt_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Optimization complete", message)
        else:
            QMessageBox.warning(self, "Optimization", message)
        self.win.statusBar().showMessage(message, 6000)

    def _fail(self, msg: str):
        """Handle worker failure.

        Args:
            msg: Error message from the failed worker.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  System Info
# =====================================================================

class SystemInfoPage(_Page):
    """Read-only system facts + live metrics."""

    def __init__(self, win):
        """Initialize the System Info page.

        Args:
            win: Parent window instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("System Info", "Hardware, OS, memory and disk overview."))

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.v.addLayout(row)

        self.card = Card(self.p)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(20, 18, 20, 18)
        self.info_label = QLabel("Loading\u2026")
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.card_layout.addWidget(self.info_label)
        self.v.addWidget(self.card)

        self.disk_tbl = QTableWidget(0, 4)
        self.disk_tbl.setHorizontalHeaderLabels(["Drive", "Total", "Free", "Used %"])
        self.disk_tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.disk_tbl)
        self.disk_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.disk_tbl.verticalHeader().setVisible(False)
        self.v.addWidget(self.disk_tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.card, self.disk_tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        """Load and display system information."""
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading system info\u2026")
        self.win.run_worker(SystemInfoWorker(), self._on_info, self._fail)

    def _on_info(self, info: dict):
        """Handle the system info from the worker.

        Args:
            info: Dictionary containing system information.
        """
        self.refresh_btn.setEnabled(True)
        snap = info
        p = snap.get("platform", {})
        cpu = snap.get("cpu", {})
        mem = snap.get("memory", {})
        lines = [
            f"<b>OS:</b> {p.get('system', '?')} {p.get('release', '')} ({p.get('machine', '')})",
            f"<b>Host:</b> {p.get('hostname', '')}",
            f"<b>CPU:</b> {cpu.get('physical_cores', '?')} cores / "
            f"{cpu.get('logical_cores', '?')} threads @ {cpu.get('usage_percent', '?')}% now",
            f"<b>Memory:</b> {mem.get('available_human', '?')} free of {mem.get('total_human', '?')} "
            f"({mem.get('used_percent', '?')}% used)",
        ]
        bat = snap.get("battery")
        if bat:
            lines.append(f"<b>Battery:</b> {bat.get('percent', '?')}% "
                         f"({'charging' if bat.get('plugged_in') else 'on battery'})")
        self.info_label.setText("<br>".join(lines))

        disks = snap.get("disks", [])
        self.disk_tbl.setRowCount(len(disks))
        for r, d in enumerate(disks):
            self.disk_tbl.setItem(r, 0, QTableWidgetItem(f"{d.get('device', '')} {d.get('mountpoint', '')}"))
            self.disk_tbl.setItem(r, 1, QTableWidgetItem(d.get("total_human", "")))
            self.disk_tbl.setItem(r, 2, QTableWidgetItem(d.get("free_human", "")))
            self.disk_tbl.setItem(r, 3, QTableWidgetItem(f"{d.get('used_percent', 0)}%"))

    def _fail(self, msg: str):
        """Handle worker failure.

        Args:
            msg: Error message from the failed worker.
        """
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Workers for existing analyzer backends
# =====================================================================

class BrokenLinksWorker(QObject):
    """Worker that scans for broken shortcuts/links."""
    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str):
        """__init__."""
        super().__init__()
        self._root = root
        import threading
        self._cancel = threading.Event()

    def cancel(self):
        """Request cancellation of the scan."""
        self._cancel.set()

    def run(self):
        """Execute the broken link scan and emit results."""
        try:
            from cortex_unified.analyzers.broken_link_detector import BrokenLinkDetector
            links = BrokenLinkDetector().scan_all(
                self._root, progress=self.progress.emit, cancel_event=self._cancel)
            out = [{"path": str(getattr(l, "path", "")),
                    "target": str(getattr(l, "target", "")),
                    "type": str(getattr(l, "link_type", ""))} for l in links]
            self.finished.emit(out)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DuplicateFoldersWorker(QObject):
    """Worker that finds duplicate folders."""
    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str):
        """__init__."""
        super().__init__()
        self._root = root
        import threading
        self._cancel = threading.Event()

    def cancel(self):
        """Request cancellation of the scan."""
        self._cancel.set()

    def run(self):
        """Execute the duplicate folder scan and emit results."""
        try:
            from cortex_unified.analyzers.duplicate_folder_finder import DuplicateFolderFinder
            groups = DuplicateFolderFinder(root_path=self._root).find_duplicate_folders(
                progress=self.progress.emit, cancel_event=self._cancel)
            out = {k: [str(p) for p in v] for k, v in groups.items()}
            self.finished.emit(out)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PackageCacheWorker(QObject):
    """Worker that lists package manager cache sizes."""
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        """Execute the cache scan and emit results."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            pmc = PackageManagerCleaner()
            pmc.detect_package_managers()
            stats = pmc.get_stats()
            rows = []
            for name, info in stats.get("managers", {}).items():
                rows.append({
                    "name": name,
                    "version": info.get("version", ""),
                    "cache_size": info.get("cache_size", 0),
                    "cache_size_human": info.get("cache_size_human", "0 B"),
                })
            self.finished.emit(rows)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PackageCleanWorker(QObject):
    """PackageCleanWorker class."""
    finished = Signal(str, int)   # (manager, space_freed)
    failed = Signal(str)

    def __init__(self, manager: str):
        """__init__."""
        super().__init__()
        self._manager = manager

    def run(self):
        """run."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            pmc = PackageManagerCleaner()
            pmc.detect_package_managers()
            if self._manager == "pip":
                res = pmc.clean_pip_cache()
            elif self._manager == "npm":
                res = pmc.clean_npm_cache()
            else:
                res = pmc.clean_system_packages(self._manager)
            freed = getattr(res, "space_freed", 0) or 0
            self.finished.emit(self._manager, int(freed))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# =====================================================================
#  Broken Links page
# =====================================================================

class _SimpleFolderPage(_Page):
    """Minimal folder-pick + scan page (no fake Cancel affordance).

    Premium redesign: Card-wrapped picker, styled table, polished state.
    """

    title = ""
    subtitle = ""
    action_label = "Scan"

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(self.title, self.subtitle))

        # ── folder picker card ────────────────────────────────────────────
        picker_card = Card(self.p, "Card")
        pc_lay = QVBoxLayout(picker_card)
        pc_lay.setContentsMargins(16, 12, 16, 12)
        pc_lay.setSpacing(10)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)
        pick_btn = QPushButton("Choose Folder\u2026")
        pick_btn.setObjectName("Ghost")
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pick_btn.clicked.connect(self._pick)
        self.path_label = QLabel("No folder selected")
        self.path_label.setObjectName("Muted")
        self.run_btn = QPushButton(self.action_label)
        self.run_btn.setObjectName("Primary")
        self.run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._toggle_run)
        picker_row.addWidget(pick_btn)
        picker_row.addWidget(self.path_label, 1)
        picker_row.addWidget(self.run_btn)
        pc_lay.addLayout(picker_row)

        # ── progress + status ─────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        pc_lay.addWidget(self.progress)

        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        pc_lay.addWidget(self.scan_status)

        self.v.addWidget(picker_card)

        self._worker = None
        self._running = False

        # ── results table (Card-wrapped, styled) ──────────────────────────
        table_card = Card(self.p, "Card")
        tc_lay = QVBoxLayout(table_card)
        tc_lay.setContentsMargins(0, 0, 0, 0)
        tc_lay.setSpacing(0)

        self.results_table = self._build_results()
        if self.results_table is not None:
            self.results_table.setShowGrid(False)
            self.results_table.setAlternatingRowColors(True)
            self.results_table.verticalHeader().setVisible(False)
            self.results_table.setSelectionBehavior(
                QTableWidget.SelectionBehavior.SelectRows)
            self.results_table.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers)
            self.results_table.setSortingEnabled(True)
            header = self.results_table.horizontalHeader()
            header.setStretchLastSection(True)
            header.setDefaultAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        tc_lay.addWidget(self.results_table)
        self.add_scrolling_list(table_card, stretch=1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.results_table)
        self.v.addWidget(self.state, 1)

        # ── action row ────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 8, 0, 0)
        self.hint = QLabel("Select rows, then move them to the Recycle Bin.")
        self.hint.setObjectName("Muted")
        action_row.addWidget(self.hint)
        action_row.addStretch(1)
        self.del_btn = QPushButton("Move Selected to Recycle Bin")
        self.del_btn.setObjectName("Danger")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self.del_btn)
        self.v.addLayout(action_row)

        self._folder = None

    def _build_results(self) -> QTableWidget:
        """Subclasses construct and return their specific QTableWidget."""
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Path", "Size", "Details"])
        return table

    def _pick(self):
        """_pick."""
        from pathlib import Path
        folder = QFileDialog.getExistingDirectory(
            self, "Select a folder", str(Path.home()))
        if folder:
            self._folder = folder
            self.path_label.setText(folder)
            self.path_label.setObjectName("")
            self.path_label.setStyleSheet("color: inherit;")
            self.run_btn.setEnabled(True)

    def _toggle_run(self):
        """_toggle_run."""
        if self._running and self._worker is not None:
            if hasattr(self._worker, "cancel"):
                self._worker.cancel()
            self.scan_status.setText("Cancelling\u2026")
            self.run_btn.setEnabled(False)
        else:
            self._run()

    def _start(self, worker, on_done):
        """Start a scan worker with live progress + cancel support."""
        self._worker = worker
        self._running = True
        self.state.show_loading("Scanning\u2026")
        self.progress.setVisible(True)
        self.scan_status.setText("Starting\u2026")
        self.run_btn.setText("Cancel")
        self.run_btn.setEnabled(True)
        self.del_btn.setEnabled(False)
        on_progress = self._on_progress if hasattr(worker, "progress") else None
        self.win.run_worker(worker, on_done, self._fail, on_progress=on_progress)

    def _on_progress(self, text: str):
        """_on_progress."""
        self.scan_status.setText(text)

    def _finish(self):
        """_finish."""
        self._running = False
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setText(self.action_label)
        self.run_btn.setEnabled(True)

    def _busy(self, on: bool):
        """_busy."""
        self.progress.setVisible(on)
        self.run_btn.setEnabled(not on)
        if on:
            self.del_btn.setEnabled(False)

    def _selected_paths(self) -> list[str]:
        """_selected_paths."""
        rows = {idx.row() for idx in self.results_table.selectedIndexes()}
        return [self.results_table.item(r, 0).text() for r in sorted(rows)
                if self.results_table.item(r, 0)]

    def _delete_selected(self):
        """_delete_selected."""
        paths = self._selected_paths()
        if not paths:
            QMessageBox.information(self, "No selection", "Select rows first.")
            return
        confirm = QMessageBox.question(
            self, "Move to Recycle Bin",
            f"Move {len(paths)} selected item(s) to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        from .workers import DeleteSelectedWorker
        self._busy(True)
        self.win.run_worker(DeleteSelectedWorker(paths, "recycle"), self._on_deleted, self._fail)

    def _on_deleted(self, freed: int, ok: int, blocked: int):
        """_on_deleted."""
        self._busy(False)
        QMessageBox.information(self, "Done",
                               f"Recycled {ok} item(s)."
                               + (f" {blocked} blocked." if blocked else ""))
        self._run()

    def _run(self):
        """Subclasses launch their specific scan worker."""
        if not self._folder:
            return
        self._finish()

    def _fail(self, msg: str):
        """_fail."""
        self._running = False
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setText(self.action_label)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)


class BrokenLinksPage(_SimpleFolderPage):
    """BrokenLinksPage class."""
    title = "Broken Links"
    subtitle = "Find dead shortcuts and symlinks whose targets no longer exist."
    action_label = "Scan for Broken Links"

    def _build_results(self) -> QTableWidget:
        """_build_results."""
        t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels(["Path", "Target (missing)", "Type"])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        return t

    def _run(self):
        """_run."""
        self._start(BrokenLinksWorker(self._folder), self._on_done)

    def _on_done(self, links: list):
        """_on_done."""
        self._finish()
        self.results_table.setRowCount(len(links))
        for r, l in enumerate(links):
            self.results_table.setItem(r, 0, QTableWidgetItem(l["path"]))
            self.results_table.setItem(r, 1, QTableWidgetItem(l["target"]))
            self.results_table.setItem(r, 2, QTableWidgetItem(l["type"]))
        if not links:
            self.state.show_empty("No broken links found.")
        else:
            self.state.clear()
        self.del_btn.setEnabled(bool(links))
        self.win.statusBar().showMessage(f"{len(links)} broken link(s)", 5000)


class DuplicateFoldersPage(_SimpleFolderPage):
    """DuplicateFoldersPage class."""
    title = "Duplicate Folders"
    subtitle = "Find folders whose entire contents are byte-for-byte identical."
    action_label = "Find Duplicate Folders"

    def _build_results(self) -> QTableWidget:
        """_build_results."""
        t = QTableWidget(0, 2)
        t.setHorizontalHeaderLabels(["Folder", "Group"])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        return t

    def _run(self):
        """_run."""
        self._start(DuplicateFoldersWorker(self._folder), self._on_done)

    def _on_done(self, groups: dict):
        """_on_done."""
        self._finish()
        rows = [(p, i) for i, (_, members) in enumerate(groups.items(), 1) for p in members]
        self.results_table.setRowCount(len(rows))
        for r, (path, gid) in enumerate(rows):
            self.results_table.setItem(r, 0, QTableWidgetItem(path))
            self.results_table.setItem(r, 1, QTableWidgetItem(f"#{gid}"))
        if not rows:
            self.state.show_empty("No duplicate folders found.")
        else:
            self.state.clear()
        self.del_btn.setEnabled(bool(rows))
        self.win.statusBar().showMessage(f"{len(groups)} duplicate folder group(s)", 5000)


# =====================================================================
#  Package Caches page
# =====================================================================

class PackageCachePage(_Page):
    """Detect system package managers (pip/npm/conda/...) and clear their caches.

    Premium redesign: Card-wrapped sections, StatCard metrics, styled table.
    """

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "System Package Manager Caches",
            "Reclaim space from developer package-manager caches "
            "(pip, npm, conda, yarn, ...).",
        ))

        # ── package manager selection card ─────────────────────────────
        sel_card = Card(self.p, "Card")
        sc_lay = QVBoxLayout(sel_card)
        sc_lay.setContentsMargins(16, 14, 16, 14)
        sc_lay.setSpacing(8)

        sel_label = QLabel("Package managers to scan")
        sel_label.setObjectName("SectionTitle")
        sc_lay.addWidget(sel_label)

        checkbox_row = QHBoxLayout()
        checkbox_row.setSpacing(16)
        self.pm_pip_checkbox = QCheckBox("pip")
        self.pm_pip_checkbox.setChecked(True)
        self.pm_npm_checkbox = QCheckBox("npm")
        self.pm_npm_checkbox.setChecked(True)
        self.pm_yarn_checkbox = QCheckBox("yarn")
        self.pm_conda_checkbox = QCheckBox("conda")
        self.pm_system_checkbox = QCheckBox("System")
        for cb in (self.pm_pip_checkbox, self.pm_npm_checkbox,
                   self.pm_yarn_checkbox, self.pm_conda_checkbox,
                   self.pm_system_checkbox):
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            checkbox_row.addWidget(cb)
        checkbox_row.addStretch(1)
        sc_lay.addLayout(checkbox_row)

        self.v.addWidget(sel_card)

        # ── target cache directory / location selector ─────────────────
        loc_card = Card(self.p, "Card")
        lc_lay = QVBoxLayout(loc_card)
        lc_lay.setContentsMargins(16, 14, 16, 14)
        lc_lay.setSpacing(8)

        loc_title = QLabel("Target Cache Location / Custom Directories")
        loc_title.setObjectName("SectionTitle")
        lc_lay.addWidget(loc_title)

        loc_input_row = QHBoxLayout()
        loc_input_row.setSpacing(8)

        self.pm_path_input = QLineEdit()
        self.pm_path_input.setPlaceholderText(
            "Select or enter package cache directory / file location (e.g. D:\\pip_cache, D:\\npm_cache, D:\\conda)..."
        )
        loc_input_row.addWidget(self.pm_path_input, stretch=1)

        self.pm_btn_select_dir = QPushButton("Select Directory")
        self.pm_btn_select_dir.setObjectName("Primary")
        self.pm_btn_select_dir.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pm_btn_select_dir.clicked.connect(self._browse_pm_directory)
        loc_input_row.addWidget(self.pm_btn_select_dir)

        self.pm_btn_select_file = QPushButton("Select File Location")
        self.pm_btn_select_file.setObjectName("Ghost")
        self.pm_btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pm_btn_select_file.clicked.connect(self._browse_pm_file)
        loc_input_row.addWidget(self.pm_btn_select_file)

        self.pm_btn_add_loc = QPushButton("+ Add Location")
        self.pm_btn_add_loc.setObjectName("Ghost")
        self.pm_btn_add_loc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pm_btn_add_loc.clicked.connect(self._add_custom_pm_location)
        loc_input_row.addWidget(self.pm_btn_add_loc)

        lc_lay.addLayout(loc_input_row)

        self.pm_custom_locations_list = QListWidget()
        self.pm_custom_locations_list.setMaximumHeight(65)
        self.pm_custom_locations_list.setVisible(False)
        lc_lay.addWidget(self.pm_custom_locations_list)

        self.v.addWidget(loc_card)

        # ── options card ───────────────────────────────────────────────
        opt_card = Card(self.p, "Card")
        oc_lay = QFormLayout(opt_card)
        oc_lay.setContentsMargins(16, 14, 16, 14)
        oc_lay.setSpacing(8)

        self.pm_keep_recent_spinbox = QSpinBox()
        self.pm_keep_recent_spinbox.setRange(0, 365)
        self.pm_keep_recent_spinbox.setValue(7)
        self.pm_keep_recent_spinbox.setSuffix(" days")
        self.pm_keep_recent_spinbox.setCursor(
            Qt.CursorShape.PointingHandCursor)
        oc_lay.addRow("Keep caches newer than:", self.pm_keep_recent_spinbox)

        self.pm_dry_run_checkbox = QCheckBox(
            "Dry run (preview only \u2014 recommended)")
        self.pm_dry_run_checkbox.setChecked(True)
        self.pm_dry_run_checkbox.setCursor(
            Qt.CursorShape.PointingHandCursor)
        oc_lay.addRow(self.pm_dry_run_checkbox)

        self.v.addWidget(opt_card)

        # ── detect + action buttons ────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.refresh_btn = QPushButton("Detect Managers")
        self.refresh_btn.setObjectName("Ghost")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.detect_package_managers)
        btn_row.addWidget(self.refresh_btn)

        self.scan_button = QPushButton("Scan for Caches")
        self.scan_button.setObjectName("Primary")
        self.scan_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_button.clicked.connect(self.start_pm_scan)
        btn_row.addWidget(self.scan_button)

        self.clean_btn = QPushButton("Clean Selected")
        self.clean_btn.setObjectName("Danger")
        self.clean_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self.start_pm_cleanup)
        btn_row.addWidget(self.clean_btn)
        self.v.addLayout(btn_row)

        self.pm_detect_status = QLabel("Click Detect Managers to begin")
        self.pm_detect_status.setObjectName("Muted")
        self.v.addWidget(self.pm_detect_status)

        # ── progress ───────────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        # ── metric strip ───────────────────────────────────────────────
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(12)
        self.card_caches = StatCard(self.p, "Caches Found", "\u2014")
        self.card_caches.setObjectName("BentoTile")
        self.card_caches.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_caches.setMinimumHeight(64)
        self.card_files = StatCard(self.p, "Total Files", "\u2014")
        self.card_files.setObjectName("BentoTile")
        self.card_files.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_files.setMinimumHeight(64)
        self.card_size = StatCard(self.p, "Reclaimable", "\u2014")
        self.card_size.setObjectName("BentoTile")
        self.card_size.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_size.setMinimumHeight(64)
        metrics_row.addWidget(self.card_caches)
        metrics_row.addWidget(self.card_files)
        metrics_row.addWidget(self.card_size)
        self.v.addLayout(metrics_row)

        # ── results table (Card-wrapped) ───────────────────────────────
        table_card = Card(self.p, "Card")
        tc_lay = QVBoxLayout(table_card)
        tc_lay.setContentsMargins(0, 0, 0, 0)
        tc_lay.setSpacing(0)

        self.pm_table = QTableWidget(0, 5)
        self.pm_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Path", "Size", "Files"])
        self.pm_table.setShowGrid(False)
        self.pm_table.setAlternatingRowColors(True)
        self.pm_table.verticalHeader().setVisible(False)
        self.pm_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.pm_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.pm_table.horizontalHeader().setStretchLastSection(True)
        self.pm_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.pm_table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        tc_lay.addWidget(self.pm_table)
        self.v.addWidget(table_card, 1)

        # ── initial state ──────────────────────────────────────────────
        self.pm_resources: list = []
        self.pm_custom_folders: list = []

    def _browse_pm_directory(self):
        """_browse_pm_directory."""
        from pathlib import Path
        initial = self.pm_path_input.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Package Cache Directory", initial)
        if folder:
            self.pm_path_input.setText(folder)
            self._add_custom_pm_location()

    def _browse_pm_file(self):
        """_browse_pm_file."""
        from pathlib import Path
        initial = self.pm_path_input.text().strip() or str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Package File / Cache Location", initial)
        if file_path:
            parent_dir = str(Path(file_path).parent)
            self.pm_path_input.setText(parent_dir)
            self._add_custom_pm_location()

    def _add_custom_pm_location(self):
        """_add_custom_pm_location."""
        txt = self.pm_path_input.text().strip()
        if txt and txt not in self.pm_custom_folders:
            self.pm_custom_folders.append(txt)
            self.pm_custom_locations_list.addItem(txt)
            self.pm_custom_locations_list.setVisible(True)

    def detect_package_managers(self):
        """detect_package_managers."""
        self.pm_detect_status.setText("Detecting\u2026")
        self.refresh_btn.setEnabled(False)

        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            from cortex_unified.core.config import Config

            config = Config()
            cleaner = PackageManagerCleaner(config)
            managers = cleaner.detect_package_managers()

            manager_names = []
            if isinstance(managers, list):
                manager_names = [getattr(m, 'name', str(m))
                                 for m in managers if m]

            if manager_names:
                self.pm_detect_status.setText(
                    f"Detected: {', '.join(m.upper() for m in manager_names)}")
                self.pm_detect_status.setObjectName("")
                self.pm_detect_status.setStyleSheet(
                    "color: #107c10; font-weight: bold;")
            else:
                self.pm_detect_status.setText(
                    "No compatible package managers found.")
                self.pm_detect_status.setObjectName("")
                self.pm_detect_status.setStyleSheet(
                    "color: #d13438;")
        except Exception as e:
            self.pm_detect_status.setText(f"Detection failed: {e}")
            self.pm_detect_status.setObjectName("")
            self.pm_detect_status.setStyleSheet("color: #d13438;")
        finally:
            self.refresh_btn.setEnabled(True)

    def start_pm_scan(self):
        """start_pm_scan."""
        self.scan_button.setEnabled(False)
        self.progress.setVisible(True)

        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            from cortex_unified.core.config import Config

            config = Config()
            cleaner = PackageManagerCleaner(config)

            # Include any typed path in target list
            curr_text = self.pm_path_input.text().strip()
            target_list = list(self.pm_custom_folders)
            if curr_text and curr_text not in target_list:
                target_list.append(curr_text)

            keep_recent = self.pm_keep_recent_spinbox.value()
            resources = cleaner.scan_caches(target_folders=target_list if target_list else None, keep_recent_days=keep_recent)

            self.pm_resources = resources or []
            self._display_scan_results(resources)

        except Exception as e:
            self._fail(f"Scan failed: {str(e)}")
        finally:
            self.scan_button.setEnabled(True)
            self.progress.setVisible(False)

    def _display_scan_results(self, resources):
        """_display_scan_results."""
        self.progress.setVisible(False)

        if not resources:
            self.card_caches.set_value("0", animate=True)
            self.card_files.set_value("\u2014", animate=True)
            self.card_size.set_value("\u2014", animate=True)
            self.pm_table.setRowCount(0)
            return

        self.pm_table.setRowCount(len(resources))
        total_size = 0
        total_files = 0

        for row, resource in enumerate(resources):
            if not isinstance(resource, dict):
                continue

            name = resource.get('name', '')
            res_type = resource.get('type', '').replace('_', ' ').title()
            path = resource.get('path', '')
            size = resource.get('size', 0)
            file_count = resource.get('file_count', 0)

            total_size += size
            total_files += file_count

            self.pm_table.setItem(row, 0, QTableWidgetItem(name))
            self.pm_table.setItem(row, 1, QTableWidgetItem(res_type))
            self.pm_table.setItem(row, 2, QTableWidgetItem(path))
            self.pm_table.setItem(row, 3, QTableWidgetItem(
                self._fmt_bytes(size)))
            self.pm_table.setItem(row, 4, QTableWidgetItem(str(file_count)))

        self.card_caches.set_value(str(len(resources)), animate=True)
        self.card_files.set_value(f"{total_files:,}", animate=True)
        self.card_size.set_value(
            self._fmt_bytes(total_size), animate=True)
        self.clean_btn.setEnabled(True)

    def start_pm_cleanup(self):
        """start_pm_cleanup."""
        selected = []
        for row in range(self.pm_table.rowCount()):
            item = self.pm_table.item(row, 0)
            if item and item.isSelected():
                selected.append(self.pm_resources[row])

        if not selected:
            QMessageBox.information(self, "No Selection", "Select caches to clean from the table.")
            return

        dry_run = self.pm_dry_run_checkbox.isChecked()
        mode = "Preview" if dry_run else "Clean"

        confirm = QMessageBox.question(
            self, f"Confirm {mode}",
            f"About to {mode.lower()} {len(selected)} cache(s).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.scan_button.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.progress.setVisible(True)

        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            from cortex_unified.core.config import Config

            config = Config()
            cleaner = PackageManagerCleaner(config)
            results = cleaner.clean_caches(selected, dry_run=dry_run)
            self._handle_cleanup_results(results, dry_run)

        except Exception as e:
            self._fail(f"Cleanup failed: {str(e)}")
        finally:
            self.scan_button.setEnabled(True)
            self.progress.setVisible(False)

    def _handle_cleanup_results(self, results, dry_run=True):
        """_handle_cleanup_results."""
        if isinstance(results, dict):
            freed = results.get('freed', 0)
            removed = results.get('removed', 0)
            mode = "Preview" if dry_run else "Cleaned"
            QMessageBox.information(self, f"{mode} Complete", f"{mode} {removed} item(s)\nSpace freed: {self._fmt_bytes(freed)}")
        else:
            QMessageBox.information(self, "Complete", "Operation completed.")

        self.pm_resources = []
        self.pm_table.setRowCount(0)
        self.clean_btn.setEnabled(False)

    def _fail(self, msg: str):
        """_fail."""
        QMessageBox.warning(self, "Operation Failed", msg)

    @staticmethod
    def _fmt_bytes(size_bytes: int) -> str:
        """_fmt_bytes."""
        if not isinstance(size_bytes, (int, float)):
            return "0 B"
        size_bytes = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# =====================================================================
#  SortableTreeWidgetItem (numeric sort support for project cache tree)
# =====================================================================

class SortableTreeWidgetItem(QTreeWidgetItem):
    """SortableTreeWidgetItem class."""
    def __lt__(self, other: QTreeWidgetItem) -> bool:
        """__lt__."""
        tree = self.treeWidget()
        col = tree.sortColumn() if tree else 0
        if col == 5:
            s1 = self.data(5, Qt.ItemDataRole.UserRole)
            s2 = other.data(5, Qt.ItemDataRole.UserRole)
            if s1 is not None and s2 is not None:
                return s1 < s2
        return self.text(col).lower() < other.text(col).lower()


# =====================================================================
#  Project Caches page
# =====================================================================

class ProjectCachesPage(_Page):
    """Clean multi-ecosystem project development caches (__pycache__, node_modules, target, build, etc.)."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        p = self.p
        self.v.setSpacing(Spacing.MD)

        # ===== HEADER =====
        self.v.addWidget(title_block(
            "Project Folder Caches",
            "Multi-stack cleaner for Python, Node, Rust, Go, Java, C/C++, & .NET",
        ))

        # ===== METRICS STRIP (StatCard) =====
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(Spacing.SM)
        self.card_projects = StatCard(p, "Projects", "0")
        self.card_projects.setObjectName("BentoTile")
        self.card_projects.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_projects.setMinimumHeight(64)
        self.card_caches = StatCard(p, "Cache Folders", "0")
        self.card_caches.setObjectName("BentoTile")
        self.card_caches.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_caches.setMinimumHeight(64)
        self.card_size = StatCard(p, "Reclaimable", "0 B")
        self.card_size.setObjectName("BentoTile")
        self.card_size.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_size.setMinimumHeight(64)
        metrics_row.addWidget(self.card_projects)
        metrics_row.addWidget(self.card_caches)
        metrics_row.addWidget(self.card_size)
        metrics_row.addStretch(1)

        self.btn_toggle_settings = QPushButton("Scan Settings")
        self.btn_toggle_settings.setObjectName("Ghost")
        self.btn_toggle_settings.setCursor(
            Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_settings.setCheckable(True)
        self.btn_toggle_settings.setChecked(False)
        self.btn_toggle_settings.clicked.connect(
            self._toggle_settings_panel)
        metrics_row.addWidget(self.btn_toggle_settings)

        self.v.addLayout(metrics_row)

        # ===== TARGET DIRECTORY & LOCATION BAR =====
        target_card = Card(p, "Card")
        tl_lay = QVBoxLayout(target_card)
        tl_lay.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        tl_lay.setSpacing(Spacing.SM)

        tl_header = QHBoxLayout()
        tl_title = QLabel("Target Scan Directory / File Location")
        tl_title.setObjectName("SectionTitle")
        tl_header.addWidget(tl_title)
        tl_header.addStretch(1)

        self.proj_target_count_badge = QLabel("1 Active Directory")
        self.proj_target_count_badge.setObjectName("Muted")
        tl_header.addWidget(self.proj_target_count_badge)
        tl_lay.addLayout(tl_header)

        target_input_row = QHBoxLayout()
        target_input_row.setSpacing(Spacing.SM)

        self.proj_path_input = QLineEdit()
        self.proj_path_input.setPlaceholderText("Enter or select project root directory / file location...")
        import os
        default_dir = os.getcwd()
        self.proj_path_input.setText(default_dir)
        target_input_row.addWidget(self.proj_path_input, stretch=1)

        self.btn_browse_folder = QPushButton("Select Directory")
        self.btn_browse_folder.setObjectName("Primary")
        self.btn_browse_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse_folder.clicked.connect(self.add_folder_to_scan)
        target_input_row.addWidget(self.btn_browse_folder)

        self.btn_select_file = QPushButton("Select File Location")
        self.btn_select_file.setObjectName("Ghost")
        self.btn_select_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_file.clicked.connect(self.select_file_location_to_scan)
        target_input_row.addWidget(self.btn_select_file)

        self.btn_add_target = QPushButton("+ Add Target")
        self.btn_add_target.setObjectName("Ghost")
        self.btn_add_target.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_target.clicked.connect(self._add_typed_target_folder)
        target_input_row.addWidget(self.btn_add_target)

        self.btn_add_workspace = QPushButton("Workspace")
        self.btn_add_workspace.setObjectName("Ghost")
        self.btn_add_workspace.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_workspace.clicked.connect(self.add_current_workspace)
        target_input_row.addWidget(self.btn_add_workspace)

        self.btn_autodetect = QPushButton("Auto-Detect")
        self.btn_autodetect.setObjectName("Ghost")
        self.btn_autodetect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_autodetect.clicked.connect(self.auto_detect_code_folders)
        target_input_row.addWidget(self.btn_autodetect)

        tl_lay.addLayout(target_input_row)

        # Multi-folder list
        self.proj_folders_list = QListWidget()
        self.proj_folders_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.proj_folders_list.setMaximumHeight(65)
        tl_lay.addWidget(self.proj_folders_list)

        list_actions_row = QHBoxLayout()
        self.btn_remove_target = QPushButton("Remove Selected")
        self.btn_remove_target.setObjectName("Ghost")
        self.btn_remove_target.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remove_target.clicked.connect(self.remove_selected_folder)
        list_actions_row.addWidget(self.btn_remove_target)

        self.btn_clear_targets = QPushButton("Clear All")
        self.btn_clear_targets.setObjectName("Ghost")
        self.btn_clear_targets.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_targets.clicked.connect(self.clear_all_folders)
        list_actions_row.addWidget(self.btn_clear_targets)
        list_actions_row.addStretch(1)

        tl_lay.addLayout(list_actions_row)
        self.v.addWidget(target_card)

        # ===== COLLAPSIBLE SCAN SETTINGS PANEL =====
        self.settings_card = QFrame()
        self.settings_card.setObjectName("Card")
        self.settings_card.setVisible(False)
        settings_layout = QVBoxLayout(self.settings_card)
        settings_layout.setContentsMargins(Spacing.LG, Spacing.MD, Spacing.LG, Spacing.MD)
        settings_layout.setSpacing(Spacing.SM)

        grid = QHBoxLayout()
        grid.setSpacing(Spacing.LG)

        right_box = QVBoxLayout()
        right_box.setSpacing(Spacing.XS)
        eco_lbl = QLabel("Active Ecosystem Stack")
        eco_lbl.setObjectName("SectionTitle")
        right_box.addWidget(eco_lbl)

        cat_grid = QHBoxLayout()
        cat_grid.setSpacing(Spacing.XL)
        cat_c1 = QVBoxLayout()
        cat_c1.setSpacing(Spacing.XS)
        cat_c2 = QVBoxLayout()
        cat_c2.setSpacing(Spacing.XS)

        self.cat_cb_python = QCheckBox("Python  (__pycache__, .pytest_cache, .mypy_cache)")
        self.cat_cb_python.setChecked(True)
        cat_c1.addWidget(self.cat_cb_python)

        self.cat_cb_node = QCheckBox("Node.js  (node_modules, .next, .vite, dist)")
        self.cat_cb_node.setChecked(True)
        cat_c1.addWidget(self.cat_cb_node)

        self.cat_cb_rust_go = QCheckBox("Rust & Go  (target, pkg/mod)")
        self.cat_cb_rust_go.setChecked(True)
        cat_c1.addWidget(self.cat_cb_rust_go)

        self.cat_cb_java_dotnet = QCheckBox("Java & .NET  (.gradle, build, .vs)")
        self.cat_cb_java_dotnet.setChecked(True)
        cat_c2.addWidget(self.cat_cb_java_dotnet)

        self.cat_cb_cpp_cmake = QCheckBox("C/C++ & CMake  (cmake-build-*, .ninja)")
        self.cat_cb_cpp_cmake.setChecked(True)
        cat_c2.addWidget(self.cat_cb_cpp_cmake)

        self.cat_cb_mobile_other = QCheckBox("Mobile & Other  (.dart_tool, DerivedData)")
        self.cat_cb_mobile_other.setChecked(True)
        cat_c2.addWidget(self.cat_cb_mobile_other)

        cat_grid.addLayout(cat_c1)
        cat_grid.addLayout(cat_c2)
        right_box.addLayout(cat_grid)

        options_row = QHBoxLayout()
        options_row.setSpacing(Spacing.SM)
        self.radio_clean_all = QRadioButton("Clean ALL Caches")
        self.radio_clean_all.setChecked(True)
        options_row.addWidget(self.radio_clean_all)

        self.radio_filter_age = QRadioButton("Older than:")
        options_row.addWidget(self.radio_filter_age)

        self.proj_keep_recent_spinbox = QSpinBox()
        self.proj_keep_recent_spinbox.setRange(1, 365)
        self.proj_keep_recent_spinbox.setValue(7)
        self.proj_keep_recent_spinbox.setSuffix(" days")
        self.proj_keep_recent_spinbox.setEnabled(False)
        self.radio_filter_age.toggled.connect(lambda checked: self.proj_keep_recent_spinbox.setEnabled(checked))
        options_row.addWidget(self.proj_keep_recent_spinbox)

        self.proj_dry_run_checkbox = QCheckBox("Dry Run (Preview Only)")
        self.proj_dry_run_checkbox.setChecked(True)
        options_row.addWidget(self.proj_dry_run_checkbox)
        options_row.addStretch()

        right_box.addLayout(options_row)
        grid.addLayout(right_box, stretch=1)

        settings_layout.addLayout(grid)
        self.v.addWidget(self.settings_card)

        # ===== ACTION BUTTONS (primary actions only; secondary in filter bar) =====
        action_bar = QHBoxLayout()
        action_bar.setSpacing(Spacing.SM)

        self.proj_scan_button = QPushButton("Scan for Caches")
        self.proj_scan_button.setObjectName("Primary")
        self.proj_scan_button.setCursor(
            Qt.CursorShape.PointingHandCursor)
        self.proj_scan_button.clicked.connect(self.start_project_scan)
        action_bar.addWidget(self.proj_scan_button)

        self.proj_autoscan_button = QPushButton("Scan Fixed Drives (auto)")
        self.proj_autoscan_button.setObjectName("Ghost")
        self.proj_autoscan_button.setToolTip("Walk all fixed drives (D:\\, C:\\code) for PROJECT_CACHE_CATEGORIES without picking folders — finds 21.9GB targets missed before.")
        self.proj_autoscan_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.proj_autoscan_button.clicked.connect(self.start_auto_scan)
        action_bar.addWidget(self.proj_autoscan_button)

        self.proj_cancel_button = QPushButton("Cancel")
        self.proj_cancel_button.setObjectName("Ghost")
        self.proj_cancel_button.setCursor(
            Qt.CursorShape.PointingHandCursor)
        self.proj_cancel_button.setEnabled(False)
        self.proj_cancel_button.clicked.connect(
            self.cancel_project_operation)
        action_bar.addWidget(self.proj_cancel_button)

        self.proj_clean_btn = QPushButton("Clean Selected")
        self.proj_clean_btn.setObjectName("Danger")
        self.proj_clean_btn.setCursor(
            Qt.CursorShape.PointingHandCursor)
        self.proj_clean_btn.setEnabled(False)
        self.proj_clean_btn.clicked.connect(self.start_project_cleanup)
        action_bar.addWidget(self.proj_clean_btn)

        action_bar.addStretch(1)

        btn_expand_all = QPushButton("Expand All")
        btn_expand_all.setObjectName("Ghost")
        btn_expand_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_expand_all.clicked.connect(lambda: self.proj_tree.expandAll())
        action_bar.addWidget(btn_expand_all)

        btn_collapse_all = QPushButton("Collapse All")
        btn_collapse_all.setObjectName("Ghost")
        btn_collapse_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_collapse_all.clicked.connect(
            lambda: self.proj_tree.collapseAll())
        action_bar.addWidget(btn_collapse_all)

        btn_select_all = QPushButton("Select All")
        btn_select_all.setObjectName("Ghost")
        btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_all.clicked.connect(
            lambda: self.toggle_all_table_items(True))
        action_bar.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.setObjectName("Ghost")
        btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_deselect_all.clicked.connect(
            lambda: self.toggle_all_table_items(False))
        action_bar.addWidget(btn_deselect_all)

        btn_export = QPushButton("Export")
        btn_export.setObjectName("Ghost")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self.export_report)
        action_bar.addWidget(btn_export)

        self.v.addLayout(action_bar)

        # Progress bar
        self.proj_progress = QProgressBar()
        self.proj_progress.setRange(0, 0)
        self.proj_progress.setVisible(False)
        self.v.addWidget(self.proj_progress)

        self.proj_status_label = QLabel("")
        self.proj_status_label.setObjectName("Muted")
        self.proj_status_label.setVisible(False)
        self.v.addWidget(self.proj_status_label)

        # ===== SEARCH & FILTER BAR =====
        search_bar = QHBoxLayout()
        search_bar.setSpacing(Spacing.SM)

        self.proj_search_input = QLineEdit()
        self.proj_search_input.setPlaceholderText("Filter results...")
        self.proj_search_input.textChanged.connect(self.filter_results_table)
        search_bar.addWidget(self.proj_search_input, stretch=2)

        self.proj_sort_combo = QComboBox()
        self.proj_sort_combo.addItems([
            "Size (Largest)",
            "Size (Smallest)",
            "Project (A-Z)",
            "Project (Z-A)",
            "Ecosystem",
            "Cache Folder",
        ])
        self.proj_sort_combo.currentIndexChanged.connect(self.on_sort_combo_changed)
        search_bar.addWidget(self.proj_sort_combo, stretch=1)

        chips = [
            ("All", "all"),
            ("Python", "python"),
            ("Node", "node"),
            ("Rust/Go", "rust_go"),
            ("Java/.NET", "java_dotnet"),
            ("C/C++", "cpp_cmake"),
            ("Mobile", "mobile_other"),
        ]
        self.chip_buttons = {}
        for label, cat_key in chips:
            btn = QPushButton(label)
            btn.setObjectName("Ghost")
            btn.setCheckable(True)
            if cat_key == "all":
                btn.setChecked(True)
            btn.clicked.connect(lambda _c=False, k=cat_key: self.filter_by_chip(k))
            search_bar.addWidget(btn)
            self.chip_buttons[cat_key] = btn

        self.v.addLayout(search_bar)

        # ===== MAIN TREE (Card-wrapped) =====
        tree_card = Card(p, "Card")
        tc_lay = QVBoxLayout(tree_card)
        tc_lay.setContentsMargins(0, 0, 0, 0)
        tc_lay.setSpacing(0)

        self.proj_tree = QTreeWidget()
        self.proj_tree.setColumnCount(6)
        self.proj_tree.setHeaderLabels([
            "Select", "Project / File Name", "Ecosystem",
            "Cache Folder", "Full Location", "Size on Disk",
        ])
        self.proj_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_tree.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_tree.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_tree.header().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_tree.header().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch)
        self.proj_tree.header().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents)
        self.proj_tree.itemChanged.connect(self._on_tree_item_changed)
        self.proj_tree.itemDoubleClicked.connect(
            self._on_tree_item_double_clicked)
        self.proj_tree.itemExpanded.connect(self._on_tree_item_expanded)
        self.proj_tree.setSortingEnabled(True)

        tc_lay.addWidget(self.proj_tree)
        self.v.addWidget(tree_card, stretch=1)

        # ===== INITIALIZE STATE & THREADS =====
        self.proj_folders: list = []
        self.proj_resources: list = []
        self.active_chip_filter: str = "all"
        self._scan_thread: QThread | None = None
        self._scan_worker: object | None = None
        self._clean_thread: QThread | None = None
        self._clean_worker: object | None = None

        cwd = os.getcwd()
        if cwd not in self.proj_folders:
            self.proj_folders.append(cwd)
            self.proj_folders_list.addItem(cwd)
        self._update_target_count_badge()

    def _toggle_settings_panel(self, checked: bool):
        """Show or hide the settings card."""
        self.settings_card.setVisible(checked)

    def _update_target_count_badge(self):
        """_update_target_count_badge."""
        count = len(self.proj_folders)
        self.proj_target_count_badge.setText(f"{count} Active Director{'y' if count == 1 else 'ies'}")

    def _add_typed_target_folder(self):
        """_add_typed_target_folder."""
        txt = self.proj_path_input.text().strip()
        if txt:
            if txt not in self.proj_folders:
                self.proj_folders.append(txt)
                self.proj_folders_list.addItem(txt)
            self._update_target_count_badge()

    def select_file_location_to_scan(self):
        """select_file_location_to_scan."""
        from pathlib import Path
        initial = self.proj_path_input.text().strip() or str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Project File Location (e.g. package.json, Cargo.toml)", initial)
        if file_path:
            parent_dir = str(Path(file_path).parent)
            self.proj_path_input.setText(parent_dir)
            if parent_dir not in self.proj_folders:
                self.proj_folders.append(parent_dir)
                self.proj_folders_list.addItem(parent_dir)
            self._update_target_count_badge()

    def auto_detect_code_folders(self):
        """auto_detect_code_folders."""
        from pathlib import Path
        try:
            from cortex_unified.analyzers.project_cache_scanner import _known_code_roots
            candidates = _known_code_roots()
        except Exception:
            candidates = [
                Path.home() / "code",
                Path.home() / "Projects",
                Path.home() / "Main_projects",
                Path.home() / "source" / "repos",
                Path.home() / "workspace",
            ]
        added = 0
        for cand in candidates:
            if cand.exists() and cand.is_dir():
                cand_str = str(cand)
                if cand_str not in self.proj_folders:
                    self.proj_folders.append(cand_str)
                    self.proj_folders_list.addItem(cand_str)
                    added += 1
        self._update_target_count_badge()
        if added > 0:
            QMessageBox.information(self, "Code Folders Detected", f"Added {added} code directory candidate(s) to scan list.")
        else:
            QMessageBox.information(self, "Auto-Detect Complete", "No new standard code directories found. You can manually click 'Select Directory'.")

    def add_current_workspace(self):
        """add_current_workspace."""
        import os
        cwd = os.getcwd()
        self.proj_path_input.setText(cwd)
        if cwd not in self.proj_folders:
            self.proj_folders.append(cwd)
            self.proj_folders_list.addItem(cwd)
            self._update_target_count_badge()
        else:
            QMessageBox.information(self, "Folder Already Added", f"{cwd} is already in the list.")

    def add_folder_to_scan(self):
        """add_folder_to_scan."""
        from pathlib import Path
        initial = self.proj_path_input.text().strip() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, 'Select Project Directory to Scan', initial)
        if folder:
            self.proj_path_input.setText(folder)
            if folder not in self.proj_folders:
                self.proj_folders.append(folder)
                self.proj_folders_list.addItem(folder)
            self._update_target_count_badge()

    def remove_selected_folder(self):
        """remove_selected_folder."""
        current_item = self.proj_folders_list.currentItem()
        if current_item:
            folder = current_item.text()
            if folder in self.proj_folders:
                self.proj_folders.remove(folder)
            row = self.proj_folders_list.row(current_item)
            self.proj_folders_list.takeItem(row)
            self._update_target_count_badge()

    def clear_all_folders(self):
        """clear_all_folders."""
        if self.proj_folders:
            confirm = QMessageBox.question(
                self, "Clear All Folders",
                "Remove all folders from the scan list?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.proj_folders.clear()
                self.proj_folders_list.clear()
                self._update_target_count_badge()

    def select_all_categories(self):
        """select_all_categories."""
        self.cat_cb_python.setChecked(True)
        self.cat_cb_node.setChecked(True)
        self.cat_cb_rust_go.setChecked(True)
        self.cat_cb_java_dotnet.setChecked(True)
        self.cat_cb_cpp_cmake.setChecked(True)
        self.cat_cb_mobile_other.setChecked(True)

    def clear_all_categories(self):
        """clear_all_categories."""
        self.cat_cb_python.setChecked(False)
        self.cat_cb_node.setChecked(False)
        self.cat_cb_rust_go.setChecked(False)
        self.cat_cb_java_dotnet.setChecked(False)
        self.cat_cb_cpp_cmake.setChecked(False)
        self.cat_cb_mobile_other.setChecked(False)

    def _get_enabled_categories(self) -> list[str]:
        """_get_enabled_categories."""
        cats = []
        if self.cat_cb_python.isChecked():
            cats.append('python')
        if self.cat_cb_node.isChecked():
            cats.append('node')
        if self.cat_cb_rust_go.isChecked():
            cats.append('rust_go')
        if self.cat_cb_java_dotnet.isChecked():
            cats.append('java_dotnet')
        if self.cat_cb_cpp_cmake.isChecked():
            cats.append('cpp_cmake')
        if self.cat_cb_mobile_other.isChecked():
            cats.append('mobile_other')
        return cats

    def start_project_scan(self):
        """start_project_scan."""
        txt = self.proj_path_input.text().strip()
        if txt and txt not in self.proj_folders:
            self.proj_folders.append(txt)
            self.proj_folders_list.addItem(txt)
            self._update_target_count_badge()

        if not self.proj_folders:
            QMessageBox.information(self, "No Folders Selected", "Please select or enter at least one project folder to scan.")
            return

        enabled_cats = self._get_enabled_categories()
        if not enabled_cats:
            QMessageBox.warning(self, "No Categories Selected", "Please check at least one cache ecosystem category.")
            return

        self.proj_scan_button.setEnabled(False)
        self.proj_cancel_button.setEnabled(True)
        self.proj_clean_btn.setEnabled(False)
        self.proj_progress.setVisible(True)
        self.proj_status_label.setVisible(True)
        self.proj_status_label.setText("Starting background project cache scan...")
        self.proj_tree.clear()

        from cortex_unified.ui.premium.workers import ProjectCacheScanWorker

        keep_recent = 0 if self.radio_clean_all.isChecked() else self.proj_keep_recent_spinbox.value()
        self._scan_worker = ProjectCacheScanWorker(
            target_folders=list(self.proj_folders),
            keep_recent_days=keep_recent,
            enabled_categories=enabled_cats,
        )
        self._scan_thread = QThread(self)
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_proj_scan_finished)
        self._scan_worker.failed.connect(self._on_scan_failed)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_thread.start()

    def _on_scan_progress(self, status_text: str, items_found: int, total_bytes: int):
        """_on_scan_progress."""
        self.proj_status_label.setText(f"Scanning\u2026 {status_text}")
        self.card_caches.set_value(f"{items_found:,}")
        self.card_size.set_value(self._fmt_bytes(total_bytes))

    def _on_proj_scan_finished(self, resources: list):
        """_on_proj_scan_finished."""
        self._cleanup_scan_thread()
        self.proj_resources = resources or []
        self.proj_resources.sort(key=lambda r: r.get('size', 0) if isinstance(r, dict) else 0, reverse=True)
        self._display_project_scan_results(self.proj_resources)

    def start_auto_scan(self):
        """Auto-discover across all fixed drives (no folder pick needed)."""
        enabled_cats = self._get_enabled_categories()
        if not enabled_cats:
            QMessageBox.warning(self, "No Categories Selected", "Please check at least one ecosystem.")
            return
        self.proj_scan_button.setEnabled(False)
        if hasattr(self, 'proj_autoscan_button'):
            self.proj_autoscan_button.setEnabled(False)
        self.proj_cancel_button.setEnabled(True)
        self.proj_clean_btn.setEnabled(False)
        self.proj_progress.setVisible(True)
        self.proj_status_label.setVisible(True)
        self.proj_status_label.setText("Auto-scanning all fixed drives… (this may take a minute)")
        self.proj_tree.clear()
        from cortex_unified.ui.premium.workers import AutoProjectCacheWorker
        keep_recent = 0 if self.radio_clean_all.isChecked() else self.proj_keep_recent_spinbox.value()
        self._scan_worker = AutoProjectCacheWorker(
            enabled_categories=enabled_cats,
            keep_recent_days=keep_recent,
        )
        self._scan_thread = QThread(self)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_proj_scan_finished)
        self._scan_worker.failed.connect(self._on_scan_failed)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_thread.start()

    def _on_scan_failed(self, err_msg: str):
        """_on_scan_failed."""
        self._cleanup_scan_thread()
        self._fail(f"Scan failed: {err_msg}")

    def _cleanup_scan_thread(self):
        """_cleanup_scan_thread."""
        if self._scan_thread:
            self._scan_thread.quit()
            self._scan_thread.wait()
            self._scan_thread = None
        self._scan_worker = None

        self.proj_scan_button.setEnabled(True)
        if hasattr(self, 'proj_autoscan_button'):
            self.proj_autoscan_button.setEnabled(True)
        self.proj_cancel_button.setEnabled(False)
        self.proj_progress.setVisible(False)
        self.proj_status_label.setVisible(False)

    def cancel_project_operation(self):
        """cancel_project_operation."""
        if self._scan_worker and hasattr(self._scan_worker, 'cancel'):
            self._scan_worker.cancel()
            self.proj_status_label.setText("Cancelling scan operation...")
        if self._clean_worker and hasattr(self._clean_worker, 'cancel'):
            self._clean_worker.cancel()
            self.proj_status_label.setText("Cancelling cleanup operation...")

    def _display_project_scan_results(self, resources: list):
        """_display_project_scan_results."""
        self.proj_tree.blockSignals(True)
        self.proj_tree.setSortingEnabled(False)
        self.proj_tree.clear()

        if not resources:
            self.card_projects.set_value("0", animate=True)
            self.card_caches.set_value("0", animate=True)
            self.card_size.set_value("0 B", animate=True)
            self.proj_tree.blockSignals(False)
            return

        total_size = 0
        projects_set = set()

        eco_badge_map = {
            "python": "Python",
            "node": "Node.js",
            "rust_go": "Rust / Go",
            "java_dotnet": "Java / .NET",
            "cpp_cmake": "C/C++ / CMake",
            "mobile_other": "Mobile / Vendor",
        }

        for resource in resources:
            if not isinstance(resource, dict):
                continue

            path = resource.get('path', '')
            project = resource.get('name', 'Unknown')
            projects_set.add(project)

            cat_id = resource.get('category', 'python')
            ecosystem_label = eco_badge_map.get(cat_id, resource.get('manager_name', cat_id.title()))
            cache_dir = resource.get('cache_name', resource.get('description', 'Cache'))
            size = resource.get('size', 0)
            file_cnt = resource.get('file_count', 0)
            total_size += size

            parent_item = SortableTreeWidgetItem(self.proj_tree)
            parent_item.setFlags(parent_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            parent_item.setCheckState(0, Qt.CheckState.Checked)
            parent_item.setText(1, project)
            parent_item.setText(2, ecosystem_label)
            parent_item.setText(3, cache_dir)
            parent_item.setText(4, path)
            parent_item.setText(5, f"{self._fmt_bytes(size)} ({file_cnt:,} files)")

            parent_item.setData(5, Qt.ItemDataRole.UserRole, size)
            parent_item.setData(0, Qt.ItemDataRole.UserRole, resource)
            parent_item.setData(2, Qt.ItemDataRole.UserRole, cat_id)

            dummy_child = SortableTreeWidgetItem(parent_item)
            dummy_child.setText(1, "Expand to load file details...")

        self.proj_tree.setSortingEnabled(True)
        self.proj_tree.sortByColumn(5, Qt.SortOrder.DescendingOrder)
        self.proj_tree.blockSignals(False)

        self.card_projects.set_value(
            f"{len(projects_set):,}", animate=True)
        self.card_caches.set_value(
            f"{len(resources):,}", animate=True)
        self.card_size.set_value(
            self._fmt_bytes(total_size), animate=True)

        self.proj_clean_btn.setEnabled(True)

        self.proj_tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.proj_tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

    def _on_tree_item_expanded(self, item: QTreeWidgetItem):
        """_on_tree_item_expanded."""
        if item.childCount() == 1 and "Expand" in item.child(0).text(1):
            self.proj_tree.blockSignals(True)
            item.removeChild(item.child(0))

            path_str = item.text(4)
            eco_label = item.text(2)
            cache_dir = item.text(3)

            from pathlib import Path
            dir_path = Path(path_str)
            if dir_path.exists() and dir_path.is_dir():
                try:
                    sub_count = 0
                    for entry in dir_path.iterdir():
                        if sub_count >= 50:
                            more_item = SortableTreeWidgetItem(item)
                            more_item.setText(1, "  ... and more items inside")
                            break
                        child_item = SortableTreeWidgetItem(item)
                        child_item.setFlags(child_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        child_item.setCheckState(0, item.checkState(0))

                        icon_prefix = "" if entry.is_dir() else ""
                        entry_size = 0
                        if entry.is_file():
                            try:
                                entry_size = entry.stat().st_size
                            except Exception:
                                pass
                        child_item.setText(1, f"  {icon_prefix} {entry.name}")
                        child_item.setText(2, eco_label)
                        child_item.setText(3, cache_dir)
                        child_item.setText(4, str(entry))
                        child_item.setText(5, self._fmt_bytes(entry_size) if entry.is_file() else "Directory")
                        child_item.setData(5, Qt.ItemDataRole.UserRole, entry_size)
                        sub_count += 1
                except Exception:
                    pass
        self.proj_clean_btn.setEnabled(True)

        self.proj_tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.proj_tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

    def on_sort_combo_changed(self, index: int):
        """on_sort_combo_changed."""
        self.proj_tree.blockSignals(True)
        if index == 0:
            self.proj_tree.sortByColumn(5, Qt.SortOrder.DescendingOrder)
        elif index == 1:
            self.proj_tree.sortByColumn(5, Qt.SortOrder.AscendingOrder)
        elif index == 2:
            self.proj_tree.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        elif index == 3:
            self.proj_tree.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        elif index == 4:
            self.proj_tree.sortByColumn(2, Qt.SortOrder.AscendingOrder)
        elif index == 5:
            self.proj_tree.sortByColumn(3, Qt.SortOrder.AscendingOrder)
        self.proj_tree.blockSignals(False)

    def filter_by_chip(self, cat_key: str):
        """filter_by_chip."""
        self.active_chip_filter = cat_key
        for k, btn in self.chip_buttons.items():
            btn.setChecked(k == cat_key)
        self.filter_results_table(self.proj_search_input.text())

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """_on_tree_item_double_clicked."""
        import os
        path_str = item.text(4)
        if path_str and os.path.exists(path_str):
            try:
                os.startfile(path_str)
            except Exception:
                from PySide6.QtGui import QDesktopServices
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(path_str))

    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """_on_tree_item_changed."""
        if column == 0:
            self.proj_tree.blockSignals(True)
            state = item.checkState(0)
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
            parent = item.parent()
            if parent:
                all_checked = all(parent.child(i).checkState(0) == Qt.CheckState.Checked for i in range(parent.childCount()))
                parent.setCheckState(0, Qt.CheckState.Checked if all_checked else Qt.CheckState.Unchecked)
            self.proj_tree.blockSignals(False)

    def filter_results_table(self, query: str):
        """filter_results_table."""
        q = query.strip().lower()
        chip = self.active_chip_filter

        visible_cnt = 0
        visible_bytes = 0

        for i in range(self.proj_tree.topLevelItemCount()):
            parent = self.proj_tree.topLevelItem(i)
            res = parent.data(0, Qt.ItemDataRole.UserRole)
            cat_id = parent.data(2, Qt.ItemDataRole.UserRole) or ""

            match_chip = (chip == "all") or (cat_id == chip)
            match_query = True
            if q:
                match_query = any(q in parent.text(col).lower() for col in range(1, 6))

            show = match_chip and match_query
            parent.setHidden(not show)

            if show:
                visible_cnt += 1
                if isinstance(res, dict):
                    visible_bytes += res.get('size', 0)

        if visible_cnt < self.proj_tree.topLevelItemCount():
            self.proj_status_label.setText(
                f"Showing {visible_cnt:,} of "
                f"{self.proj_tree.topLevelItemCount():,} cache(s)")
        elif self.proj_resources:
            total = sum(
                r.get('size', 0) for r in self.proj_resources)
            self.proj_status_label.setText(
                f"{len(self.proj_resources):,} cache(s) \u2014 "
                f"{self._fmt_bytes(total)}")

    def toggle_all_table_items(self, checked: bool):
        """toggle_all_table_items."""
        self.proj_tree.blockSignals(True)
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.proj_tree.topLevelItemCount()):
            item = self.proj_tree.topLevelItem(i)
            item.setCheckState(0, state)
            for c in range(item.childCount()):
                item.child(c).setCheckState(0, state)
        self.proj_tree.blockSignals(False)

    def export_report(self):
        """export_report."""
        if not self.proj_resources:
            QMessageBox.information(self, "No Results", "No scan results available to export.")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Scan Report",
            "cortex_cache_report.csv",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            if file_path.endswith('.json'):
                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.proj_resources, f, indent=2)
            else:
                import csv
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Project', 'Ecosystem', 'Cache Directory', 'Full Path', 'Size Bytes', 'Size Human', 'File Count'])
                    for r in self.proj_resources:
                        if isinstance(r, dict):
                            writer.writerow([
                                r.get('name', ''),
                                r.get('manager_name', r.get('category', '')),
                                r.get('cache_name', ''),
                                r.get('path', ''),
                                r.get('size', 0),
                                self._fmt_bytes(r.get('size', 0)),
                                r.get('file_count', 0)
                            ])
            QMessageBox.information(self, "Report Exported", f"Successfully saved scan report to:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Could not export report: {e}")

    def _get_selected_resources(self) -> list[dict]:
        """_get_selected_resources."""
        selected = []
        for i in range(self.proj_tree.topLevelItemCount()):
            item = self.proj_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                res = item.data(0, Qt.ItemDataRole.UserRole)
                if res and isinstance(res, dict):
                    selected.append(res)
        return selected

    def start_project_cleanup(self):
        """start_project_cleanup."""
        selected_resources = self._get_selected_resources()
        if not selected_resources:
            QMessageBox.warning(self, "No Caches Selected", "Please select at least one project cache to clean.")
            return

        dry_run = self.proj_dry_run_checkbox.isChecked()
        mode = "Preview" if dry_run else "Clean"

        confirm = QMessageBox.question(
            self, f"Confirm {mode}",
            f"About to {mode.lower()} {len(selected_resources):,} selected project cache(s).\nDry Run Mode: {dry_run}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.proj_clean_btn.setEnabled(False)
        self.proj_scan_button.setEnabled(False)
        self.proj_cancel_button.setEnabled(True)
        self.proj_progress.setVisible(True)
        self.proj_status_label.setVisible(True)

        from cortex_unified.ui.premium.workers import ProjectCacheCleanWorker

        self._clean_worker = ProjectCacheCleanWorker(selected_resources, dry_run=dry_run)
        self._clean_thread = QThread(self)
        self._clean_worker.moveToThread(self._clean_thread)

        self._clean_worker.progress.connect(self._on_clean_progress)
        self._clean_worker.finished.connect(lambda results: self._on_proj_clean_finished(results, dry_run))
        self._clean_worker.failed.connect(self._on_clean_failed)

        self._clean_thread.started.connect(self._clean_worker.run)
        self._clean_thread.start()

    def _on_clean_progress(self, done_count: int, total_count: int, freed_bytes: int):
        """_on_clean_progress."""
        self.proj_status_label.setText(
            f"Cleaning {done_count:,} of {total_count:,}\u2026")

    def _on_proj_clean_finished(self, results: dict, dry_run: bool):
        """_on_proj_clean_finished."""
        self._cleanup_clean_thread()

        freed_size = results.get('freed', 0)
        removed_count = results.get('removed', 0)
        errors = results.get('errors', [])

        mode = "Preview" if dry_run else "Cleaned"

        if errors:
            error_msg = '\n'.join(errors[:3])
            if len(errors) > 3:
                error_msg += f"\n... and {len(errors)-3} more errors"
            self._fail(f"Cleanup completed with errors:\n{error_msg}")
        else:
            message = f"{mode} {removed_count:,} item(s)\nSpace freed: {self._fmt_bytes(freed_size)}"
            QMessageBox.information(self, f"{mode} Complete", message)

        self.proj_resources = []
        self.proj_tree.clear()
        self.card_projects.set_value("0")
        self.card_caches.set_value("0")
        self.card_size.set_value("0 B")

    def _handle_project_cleanup_results(self, results: dict, dry_run: bool = True):
        """_handle_project_cleanup_results."""
        self._on_proj_clean_finished(results, dry_run)

    def _on_clean_failed(self, err_msg: str):
        """_on_clean_failed."""
        self._cleanup_clean_thread()
        self._fail(f"Cleanup failed: {err_msg}")

    def _cleanup_clean_thread(self):
        """_cleanup_clean_thread."""
        if self._clean_thread:
            self._clean_thread.quit()
            self._clean_thread.wait()
            self._clean_thread = None
        self._clean_worker = None

        self.proj_scan_button.setEnabled(True)
        self.proj_clean_btn.setEnabled(False)
        self.proj_cancel_button.setEnabled(False)
        self.proj_progress.setVisible(False)
        self.proj_status_label.setVisible(False)

    def _fail(self, msg: str):
        """_fail."""
        QMessageBox.warning(self, "Operation Failed", msg)

    @staticmethod
    def _fmt_bytes(size_bytes: int) -> str:
        """_fmt_bytes."""
        if not isinstance(size_bytes, (int, float)):
            return "0 B"
        size_bytes = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# =====================================================================
#  Secrets Scanner (offline security audit)
# =====================================================================

class SecretsScanWorker(QObject):
    """SecretsScanWorker class."""
    finished = Signal(list, int)
    failed = Signal(str)

    def __init__(self, directory: str):
        """__init__."""
        super().__init__()
        self._directory = directory

    def run(self):
        """run."""
        try:
            from cortex_unified.system_tools.secrets_scanner import run_scan
            stats = run_scan(self._directory, quiet=True)
            rows = []
            for f in stats.findings:
                rows.append({
                    "severity": getattr(f, "severity", ""),
                    "rule": getattr(f, "pattern_name", ""),
                    "file": getattr(f, "file_path", ""),
                    "line": getattr(f, "line_number", ""),
                    "preview": getattr(f, "match_preview", ""),
                })
            self.finished.emit(rows, int(getattr(stats, "risk_score", 0)))
        except Exception as exc:
            self.failed.emit(str(exc))


_SEVERITY_RANK = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
}


def _severity_rank(finding: dict) -> int:
    """_severity_rank."""
    return _SEVERITY_RANK.get(str(finding.get("severity", "")).strip().upper(), 0)


def _line_sort_key(finding: dict) -> int:
    """_line_sort_key."""
    raw = finding.get("line", "")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


class SecretsScannerPage(_Page):
    """Scan a project folder for exposed secrets/credentials - fully offline."""

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Secrets Scanner",
            "Find exposed API keys, tokens, passwords and private keys in a folder. "
            "Runs entirely offline - nothing is sent anywhere.",
        ))

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Folder\u2026")
        pick_btn.clicked.connect(self._pick)
        self.path_label = QLabel("No folder selected")
        self.path_label.setObjectName("Muted")
        self.run_btn = QPushButton("Scan for Secrets")
        self.run_btn.setObjectName("Primary")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
        picker.addWidget(self.run_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.risk_label = QLabel("")
        self.v.addWidget(self.risk_label)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Severity", "Rule", "File", "Line"])
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._folder = None

    def _pick(self):
        """_pick."""
        from pathlib import Path
        folder = QFileDialog.getExistingDirectory(self, "Select a folder", str(Path.home()))
        if folder:
            self._folder = folder
            self.path_label.setText(folder)
            self.run_btn.setEnabled(True)

    def _run(self):
        """_run."""
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Scanning for secrets\u2026")
        self.win.statusBar().showMessage("Scanning for secrets\u2026")
        self.win.run_worker(SecretsScanWorker(self._folder), self._on_done, self._fail)

    def _on_done(self, findings: list, risk: int):
        """_on_done."""
        self.progress.setVisible(False)
        if not findings:
            self.state.show_empty("No secrets found \u2014 nothing exposed.")
        else:
            self.state.clear()
        self.run_btn.setEnabled(True)
        colour = self.p.danger if risk >= 60 else (self.p.warning if risk >= 30 else self.p.success)
        self.risk_label.setText(f"Risk score: {risk}/100  \u2014  {len(findings)} finding(s)")
        self.risk_label.setStyleSheet(f"color: {colour}; font-weight: 700;")
        self.tbl.setRowCount(len(findings))
        for r, f in enumerate(findings):
            self.tbl.setItem(r, 0, QTableWidgetItem(str(f["severity"])))
            self.tbl.setItem(r, 1, QTableWidgetItem(str(f["rule"])))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(f["file"])))
            self.tbl.setItem(r, 3, QTableWidgetItem(str(f["line"])))
        self.win.statusBar().showMessage(f"{len(findings)} secret finding(s), risk {risk}/100", 6000)

    def _fail(self, msg: str):
        """_fail."""
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)


# =====================================================================
#  Virtual Disks (WSL / Docker / Hyper-V VHDX reclaim)
# =====================================================================

class VirtualDisksPage(_Page):
    """Reclaim space from WSL / Docker / Hyper-V virtual disks.

    These ``.vhdx`` files grow on demand and never shrink by themselves, so
    deleting files inside a Linux distribution or removing Docker images frees
    space *inside* the guest while Windows still reports the drive as full. This
    page finds those disks, explains the situation, and compacts them safely.
    """

    def __init__(self, win):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Virtual Disks",
            "WSL, Docker and Hyper-V keep their filesystems in virtual disks that "
            "grow but never shrink on their own. Deleting files inside them frees "
            "nothing on Windows until the disk is compacted.",
        ))
        if _windows_only(self, "Virtual disk compaction"):
            return

        self._disks: list = []

        # -- explanation card ------------------------------------------------
        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        explain = QLabel(
            "<b>Why this happens:</b> inside a distribution, <code>df</code> shows "
            "the space as free, because it is - inside the virtual disk. The host "
            "file keeps its old size regardless.<br><br>"
            "<b>What compacting does:</b> it returns the unused blocks to Windows. "
            "Nothing inside the guest is deleted. The disk must be fully stopped "
            "first, which is why Cortex refuses while WSL or Docker is running - "
            "compacting an attached disk is how these files get corrupted."
        )
        explain.setObjectName("Muted")
        explain.setWordWrap(True)
        cl.addWidget(explain)
        self.v.addWidget(card)

        # -- controls --------------------------------------------------------
        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Find Virtual Disks")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        self.stop_btn = QPushButton("Stop WSL")
        self.stop_btn.clicked.connect(self._shutdown)
        row.addWidget(self.stop_btn)
        self.sparse_btn = QPushButton("Keep Sparse")
        self.sparse_btn.setEnabled(False)
        self.sparse_btn.clicked.connect(self._set_sparse)
        row.addWidget(self.sparse_btn)
        row.addStretch(1)
        self.compact_btn = QPushButton("Compact Selected")
        self.compact_btn.setObjectName("Primary")
        self.compact_btn.setEnabled(False)
        self.compact_btn.clicked.connect(self._compact)
        row.addWidget(self.compact_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        self.v.addWidget(self.status)

        # -- table -----------------------------------------------------------
        self._COLS = ["Disk", "Owner", "Size on disk", "Status", "Location"]
        self.tbl = QTableWidget(0, len(self._COLS))
        self.tbl.setHorizontalHeaderLabels(self._COLS)
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(self._on_select)
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        note = QLabel(
            "Compaction needs Administrator rights and can take several minutes per "
            "disk. Stopping WSL closes every running distribution and Docker's WSL "
            "backend - save your work inside them first."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.v.addWidget(note)

        self._autoload = self._load
        self._loaded = False

    # -- selection -----------------------------------------------------------

    def _selected_disks(self) -> list:
        """_selected_disks."""
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()})
        return [self._disks[r] for r in rows if 0 <= r < len(self._disks)]

    def _on_select(self):
        """_on_select."""
        chosen = self._selected_disks()
        self.compact_btn.setEnabled(bool(chosen) and all(d.can_compact for d in chosen))
        self.sparse_btn.setEnabled(
            len(chosen) == 1 and getattr(chosen[0].kind, "value", "") == "wsl")

    # -- load ----------------------------------------------------------------

    def _load(self):
        """_load."""
        from .workers import VhdxListWorker
        self.refresh_btn.setEnabled(False)
        self.compact_btn.setEnabled(False)
        self.state.show_loading("Looking for virtual disks\u2026")
        self.win.run_worker(VhdxListWorker(), self._on_listed, self._fail)

    def _on_listed(self, disks: list):
        """_on_listed."""
        self.refresh_btn.setEnabled(True)
        self._disks = disks
        self.tbl.setRowCount(len(disks))
        total = 0
        for r, d in enumerate(disks):
            total += d.on_disk_bytes
            self.tbl.setItem(r, 0, QTableWidgetItem(d.label))
            self.tbl.setItem(r, 1, QTableWidgetItem(d.kind.value.upper()))
            size_item = QTableWidgetItem(fmt_bytes(d.on_disk_bytes))
            size_item.setData(Qt.ItemDataRole.UserRole, d.on_disk_bytes)
            self.tbl.setItem(r, 2, size_item)
            self.tbl.setItem(r, 3, QTableWidgetItem(d.status_note))
            self.tbl.setItem(r, 4, QTableWidgetItem(str(d.path)))

        self.tbl.clearSelection()
        self._on_select()

        if not disks:
            self.state.show_empty(
                "No WSL, Docker or Hyper-V virtual disks found on this PC.")
            self.status.setText("")
            return
        self.state.clear()

        blocked = [d for d in disks if d.running]
        msg = f"{len(disks)} virtual disk(s) using {fmt_bytes(total)} on this PC."
        if blocked:
            msg += (f" {len(blocked)} cannot be compacted yet - stop the runtime "
                    f"first (use Stop WSL, or quit Docker Desktop).")
        self.status.setText(msg)
        self.win.statusBar().showMessage(msg, 6000)

    # -- actions -------------------------------------------------------------

    def _shutdown(self):
        """_shutdown."""
        from .workers import WslShutdownWorker
        confirm = QMessageBox.question(
            self, "Stop WSL",
            "Stop every WSL distribution now?\n\n"
            "This also stops Docker Desktop's WSL backend. Unsaved work inside a "
            "distribution will be lost, exactly as with a hard stop.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.stop_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(WslShutdownWorker(), self._on_shutdown, self._fail)

    def _on_shutdown(self, ok: bool, message: str):
        """_on_shutdown."""
        self.progress.setVisible(False)
        self.stop_btn.setEnabled(True)
        self.win.statusBar().showMessage(message, 6000)
        if not ok:
            QMessageBox.warning(self, "Stop WSL", message)
            return
        self._load()

    def _compact(self):
        """_compact."""
        from .workers import VhdxCompactWorker
        disks = [d for d in self._selected_disks() if d.can_compact]
        if not disks:
            return
        names = "\n".join(f"  \u2022 {d.label}  ({fmt_bytes(d.on_disk_bytes)})"
                          for d in disks)
        confirm = QMessageBox.question(
            self, "Compact virtual disks",
            f"Compact {len(disks)} virtual disk(s)?\n\n{names}\n\n"
            "Nothing inside the disks is deleted - only unused blocks are returned "
            "to Windows. Needs Administrator, and can take several minutes each.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.compact_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Compacting\u2026 this can take several minutes")
        self.win.run_worker(VhdxCompactWorker(disks), self._on_compacted, self._fail)

    def _on_compacted(self, results: list):
        """_on_compacted."""
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.state.clear()

        freed = sum(r.freed_bytes for r in results)
        failed = [r for r in results if not r.success]
        ok_mark, fail_mark = "OK", "FAILED"
        lines = [
            f"{ok_mark if r.success else fail_mark} {r.label}: "
            f"{fmt_bytes(r.freed_bytes)} returned \u2014 {r.message}"
            for r in results
        ]
        summary = (f"Reclaimed {fmt_bytes(freed)} in total."
                   if freed else "No space could be returned.")
        self.win.statusBar().showMessage(summary, 8000)

        box = QMessageBox(self)
        box.setWindowTitle("Compaction finished")
        box.setText(summary)
        box.setInformativeText("\n".join(lines))
        if failed and failed[0].detail:
            box.setDetailedText(failed[0].detail)
        box.setIcon(QMessageBox.Icon.Information if not failed
                    else QMessageBox.Icon.Warning)
        box.exec()
        self._load()

    def _set_sparse(self):
        """_set_sparse."""
        from .workers import VhdxSparseWorker
        chosen = self._selected_disks()
        if len(chosen) != 1:
            return
        disk = chosen[0]
        confirm = QMessageBox.question(
            self, "Keep this disk sparse",
            f"Turn on sparse mode for {disk.label}?\n\n"
            "A sparse virtual disk hands free blocks back to Windows as they are "
            "released, so the bloat does not build up again. Requires a recent "
            "version of WSL.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.sparse_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(VhdxSparseWorker(disk, True), self._on_sparse, self._fail)

    def _on_sparse(self, ok: bool, message: str):
        """_on_sparse."""
        self.progress.setVisible(False)
        self.sparse_btn.setEnabled(True)
        self.win.statusBar().showMessage(message, 6000)
        if ok:
            QMessageBox.information(self, "Sparse mode", message)
        else:
            QMessageBox.warning(self, "Sparse mode", message)

    def _fail(self, msg: str):
        """_fail."""
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)
