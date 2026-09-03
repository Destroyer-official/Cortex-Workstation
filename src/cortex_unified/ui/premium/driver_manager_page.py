"""Driver Manager page — scan, update, backup and clean device drivers.

Uses the DriverManager backend to enumerate PnP devices, check for
updates via Windows Update Agent (online) or a local driverpack index
(offline), install selected driver packages, and back up current drivers.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
)

from .widgets import Card, status_note, title_block
from .states import StatePanel
from .window import _Page, fmt_bytes

_DRIVER_CLASSES = [
    "All",
    "Display",
    "Network",
    "Storage",
    "System",
    "USB",
    "Printer",
]

_CLASS_GUID_MAP = {
    "Display": "{4d36e968-e325-11ce-bfc1-08002be10318}",
    "Network": "{4d36e972-e325-11ce-bfc1-08002be10318}",
    "Storage": "{4d36e967-e325-11ce-bfc1-08002be10318}",
    "System": "{4d36e966-e325-11ce-bfc1-08002be10318}",
    "USB": "{36fc9e60-c465-11cf-8056-444553540000}",
    "Printer": "{4d36e979-e325-11ce-bfc1-08002be10318}",
}


# ---------------------------------------------------------------------------
#  Background workers
# ---------------------------------------------------------------------------


class _ScanWorker(QObject):
    """Enumerate devices and check for driver updates."""

    finished = Signal(list)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, offline_mode: bool = False, index_path: str | None = None):
        """Store offline-mode flag, optional index path, and a cancel event."""
        super().__init__()
        self._offline = offline_mode
        self._index_path = index_path
        self._cancel = threading.Event()

    def cancel(self):
        """Request cooperative cancellation of the running scan."""
        self._cancel.set()

    def run(self):
        """Enumerate PnP devices via DriverManager and emit the driver list."""
        try:
            from cortex_unified.system_tools.driver_manager import DriverManager

            mgr = DriverManager(
                create_restore_point=False,
                progress_callback=lambda msg: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
                offline_mode=self._offline,
                driverpack_index=self._index_path,
            )
            result = mgr.scan()
            self.finished.emit(list(result.drivers))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _InstallWorker(QObject):
    """Install driver updates for selected hardware IDs."""

    finished = Signal(dict)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, hardware_ids: list[str], offline_mode: bool = False):
        """Store target hardware IDs, offline flag, and a cancel event."""
        super().__init__()
        self._hwids = hardware_ids
        self._offline = offline_mode
        self._cancel = threading.Event()

    def cancel(self):
        """Request cooperative cancellation of the running install."""
        self._cancel.set()

    def run(self):
        """Install updates for the stored hardware IDs (restore point first)."""
        try:
            from cortex_unified.system_tools.driver_manager import DriverManager

            mgr = DriverManager(
                create_restore_point=True,
                progress_callback=lambda msg: self.progress.emit(str(msg)),
                cancel_event=self._cancel,
                offline_mode=self._offline,
            )
            results = mgr.update_selected(self._hwids)
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _BackupWorker(QObject):
    """Back up all current drivers via DISM export."""

    finished = Signal(str)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self):
        """Create the backup worker with a fresh cancel event."""
        super().__init__()
        self._cancel = threading.Event()

    def cancel(self):
        """No-op cancel hook (DISM export cannot be interrupted)."""
        self._cancel.set()

    def run(self):
        """Export all drivers via DISM into ~/CortexBackups/drivers."""
        try:
            import subprocess
            import sys
            from pathlib import Path

            out_dir = Path.home() / "CortexBackups" / "drivers"
            out_dir.mkdir(parents=True, exist_ok=True)

            self.progress.emit("Exporting drivers via DISM...")
            proc = subprocess.run(
                ["dism", "/online", "/export-driver", str(out_dir)],
                capture_output=True,
                text=True,
                timeout=600,
                encoding=sys.getdefaultencoding(),
                errors="replace",
            )
            if proc.returncode == 0:
                self.finished.emit(str(out_dir))
            else:
                self.failed.emit(proc.stderr.strip() or "DISM export failed")
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
#  Page
# ---------------------------------------------------------------------------


class DriverManagerPage(_Page):
    """Scan, update, backup and manage device drivers."""

    def __init__(self, win):
        """Build the Driver Manager page: filter, action buttons, progress, and results table."""
        super().__init__(win)
        self.v.addWidget(
            title_block(
                "Driver Manager",
                "Enumerate all PnP devices, check for outdated drivers via Windows "
                "Update, install selected updates, or back up your current driver set.",
            )
        )

        # -- Controls card ---------------------------------------------------
        card = Card(self.p)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.class_combo = QComboBox()
        self.class_combo.addItems(_DRIVER_CLASSES)
        self.class_combo.setMinimumWidth(130)
        row1.addWidget(QLabel("Filter class:"))
        row1.addWidget(self.class_combo)

        row1.addStretch()

        self.scan_btn = QPushButton("Scan for Updates")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self._scan)
        row1.addWidget(self.scan_btn)

        self.install_btn = QPushButton("Install Selected")
        self.install_btn.setObjectName("Primary")
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(self._install)
        row1.addWidget(self.install_btn)

        self.backup_btn = QPushButton("Backup All")
        self.backup_btn.setObjectName("Ghost")
        self.backup_btn.clicked.connect(self._backup)
        row1.addWidget(self.backup_btn)

        card_layout.addLayout(row1)

        # -- Status + progress ------------------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        card_layout.addWidget(self.progress)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        card_layout.addWidget(self.status)

        self.v.addWidget(card)

        # -- Results table ----------------------------------------------------
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(
            [
                "Device Name",
                "Class",
                "Version",
                "Provider",
                "Status",
                "Update Available",
            ]
        )
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.v.addWidget(self.tbl, 1)

        # -- State panel (empty / error / loading) ---------------------------
        self.state = StatePanel(self.p)
        self.state.bind_content(self.tbl)
        self.v.addWidget(self.state, 1)

        # -- Internal state ---------------------------------------------------
        self._drivers: list = []
        self._scan_worker = None
        self._install_worker = None

    # -- helpers -------------------------------------------------------------

    def _selected_hwids(self) -> list[str]:
        """Return hardware IDs of the currently selected table rows."""
        rows = sorted(set(idx.row() for idx in self.tbl.selectedIndexes()))
        return [self._drivers[r].hardware_id for r in rows if r < len(self._drivers)]

    def _populate_table(self, drivers: list) -> None:
        """Fill the results table (class-filtered), flag outdated/missing, and enable Install if any outdated."""
        self._drivers = drivers
        cls_filter = self.class_combo.currentText()
        if cls_filter != "All":
            guid = _CLASS_GUID_MAP.get(cls_filter, "")
            filtered = [d for d in drivers if getattr(d, "class_guid", "") == guid]
        else:
            filtered = list(drivers)

        self.tbl.setRowCount(len(filtered))
        for r, drv in enumerate(filtered):
            self.tbl.setItem(r, 0, QTableWidgetItem(drv.device_name))
            self.tbl.setItem(
                r, 1, QTableWidgetItem(cls_filter if cls_filter != "All" else "")
            )
            self.tbl.setItem(r, 2, QTableWidgetItem(drv.current_version))
            self.tbl.setItem(r, 3, QTableWidgetItem(drv.provider))

            status = "Up to date"
            update = "No"
            if getattr(drv, "is_outdated", False):
                status = "Outdated"
                update = drv.latest_version or "Yes"
            elif getattr(drv, "is_missing", False):
                status = "Missing"

            self.tbl.setItem(r, 4, QTableWidgetItem(status))
            self.tbl.setItem(r, 5, QTableWidgetItem(update))

        self.tbl.resizeColumnsToContents()
        self.install_btn.setEnabled(
            any(getattr(d, "is_outdated", False) for d in filtered)
        )

    # -- actions -------------------------------------------------------------

    def _scan(self):
        """Clear the table and start a _ScanWorker for devices and update checks."""
        self.scan_btn.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(
            "Scanning devices and checking for driver updates\u2026"
        )
        self.status.setText("Enumerating PnP devices\u2026")
        self.tbl.setRowCount(0)

        w = _ScanWorker()
        self._scan_worker = w
        self.win.run_worker(
            w, self._on_scan_done, self._on_scan_fail, on_progress=self._on_progress
        )

    def _on_progress(self, msg: str):
        """Show worker progress text in the status label."""
        self.status.setText(msg)

    def _on_scan_done(self, drivers: list):
        """Populate the table with scan results and summarize outdated/missing counts."""
        self._scan_worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

        if not drivers:
            self.state.show_empty(
                "No devices found. Ensure you are running with "
                "sufficient privileges."
            )
            self.status.setText("No devices detected.")
            self.win.statusBar().showMessage("Scan complete — no devices", 5000)
            return

        self.state.clear()
        self._populate_table(drivers)
        outdated = sum(1 for d in drivers if getattr(d, "is_outdated", False))
        missing = sum(1 for d in drivers if getattr(d, "is_missing", False))
        self.status.setText(
            f"{len(drivers)} devices found \u2014 {outdated} outdated, "
            f"{missing} missing."
        )
        self.win.statusBar().showMessage(f"Scan complete: {len(drivers)} devices", 5000)

    def _on_scan_fail(self, msg: str):
        """Reset buttons and show the scan error with a retry option."""
        self._scan_worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._scan)

    def _install(self):
        """Confirm selection, then run _InstallWorker for the selected hardware IDs."""
        hwids = self._selected_hwids()
        if not hwids:
            QMessageBox.information(
                self,
                "Driver Manager",
                "Select one or more outdated drivers in the table first.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Driver Manager",
            f"Install updates for {len(hwids)} selected driver(s)?\n"
            "A restore point will be created before each installation.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.install_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading(f"Installing {len(hwids)} driver update(s)\u2026")
        self.status.setText("Creating restore point and installing\u2026")

        w = _InstallWorker(hwids)
        self._install_worker = w
        self.win.run_worker(
            w,
            self._on_install_done,
            self._on_install_fail,
            on_progress=self._on_progress,
        )

    def _on_install_done(self, results: dict):
        """Report per-ID success/failure counts and show errors if any install failed."""
        self._install_worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

        ok = sum(1 for v in results.values() if v)
        fail = sum(1 for v in results.values() if not v)
        self.status.setText(f"Install complete: {ok} succeeded, {fail} failed.")
        self.win.statusBar().showMessage(
            f"Driver install: {ok} ok, {fail} failed", 5000
        )

        if fail:
            self.state.show_error(
                f"{fail} driver(s) failed to install. Check the log for details.",
                on_retry=self._install,
            )
        else:
            self.state.clear()

    def _on_install_fail(self, msg: str):
        """Reset buttons and show the install error with a retry option."""
        self._install_worker = None
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.install_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._install)

    def _backup(self):
        """Disable Backup and run _BackupWorker to DISM-export all drivers."""
        self.backup_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.state.show_loading("Backing up all drivers via DISM\u2026")
        self.status.setText("Exporting drivers\u2026")

        w = _BackupWorker()
        self.win.run_worker(
            w, self._on_backup_done, self._on_backup_fail, on_progress=self._on_progress
        )

    def _on_backup_done(self, path: str):
        """Re-enable Backup and report the export directory."""
        self.progress.setVisible(False)
        self.backup_btn.setEnabled(True)
        self.state.clear()
        self.status.setText(f"Drivers backed up to {path}")
        self.win.statusBar().showMessage("Driver backup complete", 5000)

    def _on_backup_fail(self, msg: str):
        """Re-enable Backup and show the export error with a retry option."""
        self.progress.setVisible(False)
        self.backup_btn.setEnabled(True)
        self.state.show_error(msg, on_retry=self._backup)
