"""Additional premium pages: Software Updater, Drive Optimizer, System Info.

These wrap the new backend modules (app_updater, drive_optimizer, system_info)
with background workers, confirmation dialogs for anything system-modifying, and
lazy-loading. Kept separate from window.py/system_pages.py for modularity.
"""

from __future__ import annotations

import platform

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .states import StatePanel
from .widgets import Card, hline, title_block
from .window import _Page, fmt_bytes

IS_WINDOWS = platform.system() == "Windows"


def _windows_only(page: _Page, feature: str) -> bool:
    if IS_WINDOWS:
        return False
    note = QLabel(f"\u2139  {feature} is only available on Windows.")
    note.setObjectName("Muted")
    note.setWordWrap(True)
    page.v.addWidget(note)
    page.v.addStretch(1)
    return True


# =====================================================================
#  Workers
# =====================================================================

class UpdaterListWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.app_updater import AppUpdater
            self.finished.emit([a.to_dict() for a in AppUpdater().list_upgradable()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class UpgradeWorker(QObject):
    finished = Signal(int, int)   # (succeeded, total)
    failed = Signal(str)

    def __init__(self, package_ids: list[str]):
        super().__init__()
        self._ids = package_ids

    def run(self):
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
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            from cortex_unified.system_tools.drive_optimizer import DriveOptimizer
            self.finished.emit([d.to_dict() for d in DriveOptimizer().list_drives()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DriveOptimizeWorker(QObject):
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, letter: str):
        super().__init__()
        self._letter = letter

    def run(self):
        try:
            from cortex_unified.system_tools.drive_optimizer import DriveOptimizer
            res = DriveOptimizer().optimize(self._letter)
            self.finished.emit(res.success, res.message)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SystemInfoWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def run(self):
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
        super().__init__(win)
        self.v.addWidget(title_block(
            "Software Updater  \u2014  \U0001F310 requires internet",
            "Keep installed apps current via Windows Package Manager (winget). "
            "This is the only feature that needs internet (to fetch updates); "
            "everything else in Cortex works fully offline. No bundled extras.",
        ))
        if _windows_only(self, "The Software Updater"):
            return
        from cortex_unified.system_tools.app_updater import AppUpdater
        if not AppUpdater.is_available():
            note = QLabel("\u26A0  winget (Windows Package Manager) was not found. "
                          "Install 'App Installer' from the Microsoft Store to enable updates.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
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
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
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
        self.refresh_btn.setEnabled(False)
        self.update_sel_btn.setEnabled(False)
        self.update_all_btn.setEnabled(False)
        self.state.show_loading("Checking for updates\u2026")
        self.win.statusBar().showMessage("Checking for updates\u2026")
        self.win.run_worker(UpdaterListWorker(), self._on_listed, self._fail)

    def _on_listed(self, apps: list):
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
        rows = {idx.row() for idx in self.tbl.selectedIndexes()}
        return [self.tbl.item(r, 3).text() for r in sorted(rows) if self.tbl.item(r, 3)]

    def _update_selected(self):
        ids = self._selected_ids()
        if not ids:
            QMessageBox.information(self, "No selection", "Select one or more apps to update.")
            return
        self._run_updates(ids, f"Update {len(ids)} selected app(s)?")

    def _update_all(self):
        ids = [self.tbl.item(r, 3).text() for r in range(self.tbl.rowCount()) if self.tbl.item(r, 3)]
        self._run_updates(ids, f"Update all {len(ids)} app(s)?")

    def _run_updates(self, ids: list[str], prompt: str):
        if not ids:
            return
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
        self.progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        QMessageBox.information(self, "Updates complete", f"Updated {ok} of {total} app(s).")
        self.win.statusBar().showMessage(f"Updated {ok}/{total}", 6000)
        self._load()

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Drive Optimizer
# =====================================================================

class DriveOptimizerPage(_Page):
    """Media-aware TRIM (SSD) / defrag (HDD) - never defragments an SSD."""

    def __init__(self, win):
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
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
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
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Detecting drives\u2026")
        self.win.run_worker(DriveListWorker(), self._on_listed, self._fail)

    def _on_listed(self, drives: list):
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
        self.progress.setVisible(False)
        self.opt_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Optimization complete", message)
        else:
            QMessageBox.warning(self, "Optimization", message)
        self.win.statusBar().showMessage(message, 6000)

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  System Info
# =====================================================================

class SystemInfoPage(_Page):
    """Read-only system facts + live metrics."""

    def __init__(self, win):
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
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
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
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Reading system info\u2026")
        self.win.run_worker(SystemInfoWorker(), self._on_info, self._fail)

    def _on_info(self, snap: dict):
        self.state.clear()
        self.refresh_btn.setEnabled(True)
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
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Workers for existing analyzer backends
# =====================================================================

class BrokenLinksWorker(QObject):
    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str):
        super().__init__()
        self._root = root
        import threading
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
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
    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str):
        super().__init__()
        self._root = root
        import threading
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def run(self):
        try:
            from cortex_unified.analyzers.duplicate_folder_finder import DuplicateFolderFinder
            groups = DuplicateFolderFinder(root_path=self._root).find_duplicate_folders(
                progress=self.progress.emit, cancel_event=self._cancel)
            out = {k: [str(p) for p in v] for k, v in groups.items()}
            self.finished.emit(out)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class PackageCacheWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def run(self):
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
    finished = Signal(str, int)   # (manager, space_freed)
    failed = Signal(str)

    def __init__(self, manager: str):
        super().__init__()
        self._manager = manager

    def run(self):
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
    """Minimal folder-pick + scan page (no fake Cancel affordance)."""

    title = ""
    subtitle = ""
    action_label = "Scan"

    def __init__(self, win):
        super().__init__(win)
        from PySide6.QtWidgets import QFileDialog  # local import
        self._QFileDialog = QFileDialog
        self.v.addWidget(title_block(self.title, self.subtitle))

        picker = QHBoxLayout()
        pick_btn = QPushButton("Choose Folder\u2026")
        pick_btn.clicked.connect(self._pick)
        self.path_label = QLabel("No folder selected")
        self.path_label.setObjectName("Muted")
        self.run_btn = QPushButton(self.action_label)
        self.run_btn.setObjectName("Primary")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._toggle_run)
        picker.addWidget(pick_btn)
        picker.addWidget(self.path_label, 1)
        picker.addWidget(self.run_btn)
        self.v.addLayout(picker)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.scan_status = QLabel("")
        self.scan_status.setObjectName("Muted")
        self.v.addWidget(self.scan_status)

        self._worker = None
        self._running = False

        self.results_table = self._build_results()
        # Scroll policy (Req 5.2, 5.5): give the list a small floor + stretch and
        # route the wheel to a single container so only the inner table scrolls.
        self.add_scrolling_list(self.results_table, stretch=1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.results_table)
        self.v.addWidget(self.state, 1)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.del_btn = QPushButton("Move Selected to Recycle Bin")
        self.del_btn.setObjectName("Danger")
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self.del_btn)
        self.v.addLayout(action_row)

        self._folder = None

    def _build_results(self) -> QTableWidget:
        raise NotImplementedError

    def _pick(self):
        from pathlib import Path
        folder = self._QFileDialog.getExistingDirectory(self, "Select a folder", str(Path.home()))
        if folder:
            self._folder = folder
            self.path_label.setText(folder)
            self.run_btn.setEnabled(True)

    def _toggle_run(self):
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
        self.scan_status.setText(text)

    def _finish(self):
        self._running = False
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setText(self.action_label)
        self.run_btn.setEnabled(True)

    def _busy(self, on: bool):
        self.progress.setVisible(on)
        self.run_btn.setEnabled(not on)
        if on:
            self.del_btn.setEnabled(False)

    def _selected_paths(self) -> list[str]:
        rows = {idx.row() for idx in self.results_table.selectedIndexes()}
        return [self.results_table.item(r, 0).text() for r in sorted(rows)
                if self.results_table.item(r, 0)]

    def _delete_selected(self):
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
        self._busy(False)
        QMessageBox.information(self, "Done",
                               f"Recycled {ok} item(s)."
                               + (f" {blocked} blocked." if blocked else ""))
        self._run()

    def _run(self):
        raise NotImplementedError

    def _fail(self, msg: str):
        self._running = False
        self._worker = None
        self.progress.setVisible(False)
        self.scan_status.setText("")
        self.run_btn.setText(self.action_label)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)


class BrokenLinksPage(_SimpleFolderPage):
    title = "Broken Links"
    subtitle = "Find dead shortcuts and symlinks whose targets no longer exist."
    action_label = "Scan for Broken Links"

    def _build_results(self) -> QTableWidget:
        t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels(["Path", "Target (missing)", "Type"])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        return t

    def _run(self):
        self._start(BrokenLinksWorker(self._folder), self._on_done)

    def _on_done(self, links: list):
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
    title = "Duplicate Folders"
    subtitle = "Find folders whose entire contents are byte-for-byte identical."
    action_label = "Find Duplicate Folders"

    def _build_results(self) -> QTableWidget:
        t = QTableWidget(0, 2)
        t.setHorizontalHeaderLabels(["Folder", "Group"])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        return t

    def _run(self):
        self._start(DuplicateFoldersWorker(self._folder), self._on_done)

    def _on_done(self, groups: dict):
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
    """Detect package managers (pip/npm/conda/...) and clear their caches."""

    def __init__(self, win):
        super().__init__(win)
        self.v.addWidget(title_block(
            "Package Manager Caches",
            "Reclaim space from developer package-manager caches (pip, npm, conda, ...).",
        ))
        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Detect Managers")
        self.refresh_btn.setObjectName("Primary")
        self.refresh_btn.clicked.connect(self._load)
        row.addWidget(self.refresh_btn)
        row.addStretch(1)
        self.clean_btn = QPushButton("Clean Selected Cache")
        self.clean_btn.setObjectName("Danger")
        self.clean_btn.setEnabled(False)
        self.clean_btn.clicked.connect(self._clean)
        row.addWidget(self.clean_btn)
        self.v.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.v.addWidget(self.progress)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels(["Manager", "Version", "Cache Size"])
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
        self.tbl.setMinimumHeight(self.LIST_MIN_HEIGHT)
        self.attach_single_scroll(self.tbl)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.itemSelectionChanged.connect(
            lambda: self.clean_btn.setEnabled(bool(self.tbl.selectedIndexes())))
        self.v.addWidget(self.tbl, 1)

        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        self._autoload = self._load
        self._loaded = False

    def _load(self):
        self.refresh_btn.setEnabled(False)
        self.state.show_loading("Detecting package managers\u2026")
        self.win.run_worker(PackageCacheWorker(), self._on_listed, self._fail)

    def _on_listed(self, rows: list):
        if not rows:
            self.state.show_empty("No package managers detected.")
        else:
            self.state.clear()
        self.refresh_btn.setEnabled(True)
        self.tbl.setRowCount(len(rows))
        for r, m in enumerate(rows):
            name_item = QTableWidgetItem(m["name"])
            self.tbl.setItem(r, 0, name_item)
            self.tbl.setItem(r, 1, QTableWidgetItem(str(m.get("version", ""))))
            self.tbl.setItem(r, 2, QTableWidgetItem(m.get("cache_size_human", "0 B")))
        self.win.statusBar().showMessage(f"{len(rows)} package manager(s) detected", 5000)

    def _clean(self):
        sel = self.tbl.selectedIndexes()
        if not sel:
            return
        manager = self.tbl.item(sel[0].row(), 0).text()
        confirm = QMessageBox.question(
            self, "Clean cache",
            f"Clear the {manager} cache? Packages will be re-downloaded when next needed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.clean_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.win.run_worker(PackageCleanWorker(manager), self._on_cleaned, self._fail)

    def _on_cleaned(self, manager: str, freed: int):
        self.progress.setVisible(False)
        QMessageBox.information(self, "Cache cleaned",
                               f"Cleared {manager} cache ({fmt_bytes(freed)} freed).")
        self._load()

    def _fail(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._load)


# =====================================================================
#  Secrets Scanner (offline security audit)
# =====================================================================

class SecretsScanWorker(QObject):
    finished = Signal(list, int)   # (findings, risk_score)
    failed = Signal(str)

    def __init__(self, directory: str):
        super().__init__()
        self._directory = directory

    def run(self):
        try:
            from cortex_unified.system_tools.secrets_scanner import run_scan
            # quiet=True: no stderr spam; NO live verification (that would send
            # secrets over the network - we stay fully offline here).
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
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SecretsScannerPage(_Page):
    """Scan a project folder for exposed secrets/credentials - fully offline."""

    def __init__(self, win):
        super().__init__(win)
        from PySide6.QtWidgets import QFileDialog
        self._QFileDialog = QFileDialog
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
        # Scroll policy (Req 5.2, 5.5): small floor so the page fits the viewport
        # and only the inner table scrolls; route the wheel to one container.
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
        from pathlib import Path
        folder = self._QFileDialog.getExistingDirectory(self, "Select a folder", str(Path.home()))
        if folder:
            self._folder = folder
            self.path_label.setText(folder)
            self.run_btn.setEnabled(True)

    def _run(self):
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Scanning for secrets\u2026")
        self.win.statusBar().showMessage("Scanning for secrets\u2026")
        self.win.run_worker(SecretsScanWorker(self._folder), self._on_done, self._fail)

    def _on_done(self, findings: list, risk: int):
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
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._run)
