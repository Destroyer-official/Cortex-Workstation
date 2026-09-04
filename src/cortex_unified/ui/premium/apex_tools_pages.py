"""Cortex Cleaner & NexusExplorer — Apex Enterprise Power Tools Pages.

Contains 10 interactive, theme-aware GUI pages:
1. DriverStoreCleanerPage (Driver Store Explorer & Superseded Driver Purger)
2. ShellbagsCleanerPage (Shellbags, Recent Items & JumpLists Activity Purger)
3. PowerPlanOptimizerPage (Windows Power Scheme & CPU Throttle Optimizer)
4. HostsFileManagerPage (Hosts File Editor & Anti-Telemetry DNS Shield)
5. NotificationCleanerPage (Action Center Notification Database Cleaner)
6. FileSignatureSnifferPage (Binary Magic Bytes & MIME Header Sniffer)
7. BinaryDifferPage (Binary & Hex File Differ Engine)
8. UsnJournalPage (NTFS USN Change Journal Scanner)
9. Par2RecoveryPage (PAR2 Parchive Integrity & Parity Inspector)
10. ImageOptimizerPage (Batch Image Compressor & WebP Transcoder)
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .tokens import Spacing
from .widgets import Card, hline, title_block
from .window import PremiumMainWindow, _Page

from NexusExplorer.native.file_signature_sniffer import FileSignatureSniffer, SniffResult
from NexusExplorer.native.binary_differ import BinaryDiffer, BinaryDiffReport
from NexusExplorer.native.usn_journal_scanner import UsnJournalScanner, UsnJournalStatus
from NexusExplorer.native.par2_recovery import Par2RecoveryEngine, Par2ValidationReport
from NexusExplorer.native.image_optimizer import ImageOptimizer, ImageOptimizeResult, BatchOptimizeSummary
from cortex_unified.system_tools.driver_store_cleaner import DriverStoreCleaner, DriverPackage
from cortex_unified.system_tools.power_plan_optimizer import PowerPlanOptimizer, PowerPlanStatus
from cortex_unified.system_tools.shellbags_privacy_cleaner import ShellbagsPrivacyCleaner, ShellbagsTarget
from cortex_unified.system_tools.hosts_file_manager import HostsFileManager, HostEntry
from cortex_unified.system_tools.notification_cleaner import NotificationCleaner


def _fmt_bytes(b: int) -> str:
    """Format a byte count into a human-readable B/KB/MB/GB string.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        b (int): Integer number of bytes to format or process.

    Returns:
        str: Formatted string or path.
    """
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    return f"{b / (1024 * 1024 * 1024):.2f} GB"


def _PrimaryButton(text: str, parent=None) -> QPushButton:
    """Construct a styled accented QPushButton adhering to design system tokens.

    Applies consistent margins, accent styling, focus outline, and pointing-hand cursor according to theme tokens.

    Args:
        text (str): Display text string.
        parent: Parent window or shell controller instance.

    Returns:
        QPushButton: Result of the operation.
    """
    btn = QPushButton(text, parent if isinstance(parent, QWidget) else None)
    btn.setObjectName("Primary")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _SecondaryButton(text: str, parent=None) -> QPushButton:
    """Construct a styled secondary QPushButton adhering to design system tokens.

    Applies consistent margins, accent styling, focus outline, and pointing-hand cursor according to theme tokens.

    Args:
        text (str): Display text string.
        parent: Parent window or shell controller instance.

    Returns:
        QPushButton: Result of the operation.
    """
    btn = QPushButton(text, parent if isinstance(parent, QWidget) else None)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


# ===========================================================================
# 1. DRIVER STORE EXPLORER PAGE
# ===========================================================================

class DriverStoreCleanerPage(_Page):
    """Driverstorecleanerpage.

    Manages DriverStoreCleanerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Driver Store page with enumerate/export/delete buttons and a drivers table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Driver Store Explorer (RAPR)", "Enumerate, backup, and delete superseded third-party driver packages (oem*.inf)."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Enumerate Drivers", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.export_btn = _SecondaryButton("Export All Drivers…", self.p)
        self.export_btn.clicked.connect(self._on_export)
        row.addWidget(self.export_btn)

        self.del_superseded_btn = _SecondaryButton("Delete Superseded Drivers", self.p)
        self.del_superseded_btn.clicked.connect(self._on_delete_superseded)
        row.addWidget(self.del_superseded_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["INF Name", "Provider", "Class", "Version", "Date", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._drivers: List[DriverPackage] = []

    def _on_scan(self):
        """Enumerate driver packages on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return DriverStoreCleaner.enumerate_drivers()

        def _done(drivers: List[DriverPackage]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                drivers (List[DriverPackage]): List of detected driver records or driver instance.
            """
            self.scan_btn.setEnabled(True)
            self._drivers = drivers
            self.table.setRowCount(len(drivers))
            for r, d in enumerate(drivers):
                self.table.setItem(r, 0, QTableWidgetItem(d.published_name))
                self.table.setItem(r, 1, QTableWidgetItem(d.provider_name))
                self.table.setItem(r, 2, QTableWidgetItem(d.class_name))
                self.table.setItem(r, 3, QTableWidgetItem(d.driver_version))
                self.table.setItem(r, 4, QTableWidgetItem(d.driver_date))
                st_item = QTableWidgetItem("Superseded (Safe to remove)" if d.is_superseded else "Active / Current")
                if d.is_superseded:
                    st_item.setForeground(Qt.GlobalColor.yellow)
                self.table.setItem(r, 5, st_item)

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.scan_btn.setEnabled(True))

    def _on_export(self):
        """Pick a folder and export all drivers into it.

        Manages on export operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Driver Backup Folder")
        if folder:
            ok, msg = DriverStoreCleaner.export_all_drivers(folder)
            if ok:
                QMessageBox.information(self, "Backup Complete", msg)
            else:
                QMessageBox.warning(self, "Export Warning", msg)

    def _on_delete_superseded(self):
        """Confirm and force-delete all superseded driver packages, then rescan.

        Manages on delete superseded operations and coordinates related state changes for the component.
        """
        superseded = [d for d in self._drivers if d.is_superseded]
        if not superseded:
            QMessageBox.information(self, "Driver Store", "No superseded driver packages detected.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Driver Deletion",
            f"Delete {len(superseded)} superseded driver packages from the Driver Store?\n\n(Requires Administrator privileges)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            deleted = 0
            for d in superseded:
                ok, _ = DriverStoreCleaner.delete_driver(d.published_name, force=True)
                if ok:
                    deleted += 1
            QMessageBox.information(self, "Complete", f"Successfully deleted {deleted} superseded driver packages.")
            self._on_scan()


# ===========================================================================
# 2. SHELLBAGS & JUMPLISTS PRIVACY PURGER PAGE
# ===========================================================================

class ShellbagsCleanerPage(_Page):
    """Shellbagscleanerpage.

    Manages ShellbagsCleanerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Shellbags page with scan/clean buttons and a traces table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Shellbags & JumpLists Activity Purger", "Sanitize Explorer folder view history (BagMRU), Recent Items, and JumpLists."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Activity Traces", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.clean_btn = _SecondaryButton("Purge Selected Traces", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Category", "Location / Key", "Items", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._targets: List[ShellbagsTarget] = []

    def _on_scan(self):
        """Scan shell activity traces on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return ShellbagsPrivacyCleaner.scan_shell_activity()

        def _done(targets: List[ShellbagsTarget]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                targets (List[ShellbagsTarget]): The targets parameter.
            """
            self.scan_btn.setEnabled(True)
            self._targets = targets
            self.table.setRowCount(len(targets))
            for r, t in enumerate(targets):
                self.table.setItem(r, 0, QTableWidgetItem(t.category))
                self.table.setItem(r, 1, QTableWidgetItem(t.path))
                self.table.setItem(r, 2, QTableWidgetItem(str(t.items_count)))
                self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(t.size_bytes)))

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.scan_btn.setEnabled(True))

    def _on_clean(self):
        """Confirm and purge all discovered activity traces, then rescan.

        Manages on clean operations and coordinates related state changes for the component.
        """
        if not self._targets:
            QMessageBox.information(self, "Activity Purger", "Please scan for activity traces first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Purge",
            "Purge Shellbag folder histories, Recent shortcuts, and JumpLists?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = ShellbagsPrivacyCleaner.clean_shell_activity(self._targets)
            QMessageBox.information(self, "Purge Complete", f"Cleared {res.registry_keys_cleared} registry keys, {res.files_deleted} shortcuts ({_fmt_bytes(res.bytes_freed)} freed).")
            self._on_scan()


# ===========================================================================
# 3. POWER PLAN & CPU THROTTLE OPTIMIZER PAGE
# ===========================================================================

class PowerPlanOptimizerPage(_Page):
    """Powerplanoptimizerpage.

    Manages PowerPlanOptimizerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Power Plan page with status line, refresh/unlock/hibernate buttons, and a schemes table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Windows Power Scheme & Performance Optimizer", "Unlock Ultimate Performance mode and optimize CPU throttling and hibernation."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        self.status_label = QLabel("Loading Power Plan state...")
        cl.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.refresh_btn = _SecondaryButton("Refresh Schemes", self.p)
        self.refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self.refresh_btn)

        self.unlock_ultimate_btn = _PrimaryButton("Unlock Ultimate Performance Plan", self.p)
        self.unlock_ultimate_btn.clicked.connect(self._on_unlock_ultimate)
        btn_row.addWidget(self.unlock_ultimate_btn)

        self.reduce_hiber_btn = _SecondaryButton("Reduce Hibernation Footprint (40% RAM)", self.p)
        self.reduce_hiber_btn.clicked.connect(self._on_reduce_hiber)
        btn_row.addWidget(self.reduce_hiber_btn)

        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Plan Name", "GUID", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(250)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._refresh()

    def _refresh(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        st = PowerPlanOptimizer.get_status()
        self.status_label.setText(
            f"Active Scheme: {st.active_scheme_name}  •  "
            f"Hibernation: {st.hibernation_status}  •  "
            f"Privileges: {'Administrator' if st.is_admin else 'Standard User'}"
        )
        self.table.setRowCount(len(st.schemes))
        for r, s in enumerate(st.schemes):
            self.table.setItem(r, 0, QTableWidgetItem(s.name))
            self.table.setItem(r, 1, QTableWidgetItem(s.guid))
            act_item = QTableWidgetItem("Active Plan" if s.is_active else "Available")
            if s.is_active:
                act_item.setForeground(Qt.GlobalColor.green)
            self.table.setItem(r, 2, act_item)

    def _on_unlock_ultimate(self):
        """Unlock the hidden Ultimate Performance power plan, then refresh.

        Manages on unlock ultimate operations and coordinates related state changes for the component.
        """
        ok, msg = PowerPlanOptimizer.unlock_ultimate_performance_plan()
        if ok:
            QMessageBox.information(self, "Ultimate Performance", msg)
        else:
            QMessageBox.warning(self, "Power Plan Warning", msg)
        self._refresh()

    def _on_reduce_hiber(self):
        """Shrink the hibernation file to 40% of RAM, then refresh.

        Manages on reduce hiber operations and coordinates related state changes for the component.
        """
        ok, msg = PowerPlanOptimizer.set_reduced_hibernation()
        if ok:
            QMessageBox.information(self, "Hibernation Configured", msg)
        else:
            QMessageBox.warning(self, "Hibernation Warning", msg)
        self._refresh()


# ===========================================================================
# 4. HOSTS ANTI-TELEMETRY SHIELD PAGE
# ===========================================================================

class HostsFileManagerPage(_Page):
    """Hostsfilemanagerpage.

    Manages HostsFileManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Hosts page with reload/shield buttons and an entries table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Hosts File Editor & Anti-Telemetry Shield", "Inspect and edit DNS host mappings and inject Windows anti-telemetry blocks."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.load_btn = _SecondaryButton("Reload Hosts", self.p)
        self.load_btn.clicked.connect(self._on_load)
        row.addWidget(self.load_btn)

        self.shield_btn = _PrimaryButton("Apply Anti-Telemetry Shield", self.p)
        self.shield_btn.clicked.connect(self._on_apply_shield)
        row.addWidget(self.shield_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["IP Address", "Hostname", "Enabled", "Comment"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._on_load()

    def _on_load(self):
        """Parse the hosts file and list its entries.

        Manages on load operations and coordinates related state changes for the component.
        """
        entries = HostsFileManager.parse_hosts_file()
        self.table.setRowCount(len(entries))
        for r, e in enumerate(entries):
            self.table.setItem(r, 0, QTableWidgetItem(e.ip))
            self.table.setItem(r, 1, QTableWidgetItem(e.hostname))
            self.table.setItem(r, 2, QTableWidgetItem("Yes" if e.is_enabled else "Blocked (#)"))
            self.table.setItem(r, 3, QTableWidgetItem(e.comment))

    def _on_apply_shield(self):
        """Confirm and add telemetry blocking entries to the hosts file, then reload.

        Manages on apply shield operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm Shield",
            "Block known Windows telemetry and diagnostics tracking servers via Hosts file?\n\n(A backup will be created automatically)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = HostsFileManager.apply_anti_telemetry_shield()
            if res.success:
                QMessageBox.information(self, "Shield Active", res.message)
            else:
                QMessageBox.warning(self, "Shield Warning", res.message)
            self._on_load()


# ===========================================================================
# 5. ACTION CENTER NOTIFICATION CLEANER PAGE
# ===========================================================================

class NotificationCleanerPage(_Page):
    """Notificationcleanerpage.

    Manages NotificationCleanerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Notification Cleaner page with status line and refresh/clean buttons.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Action Center Notification Database Cleaner", "Purge stale push notification databases (wpndatabase.db) and badge caches."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        self.status_label = QLabel("Loading notification database status...")
        cl.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.refresh_btn = _SecondaryButton("Refresh Status", self.p)
        self.refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self.refresh_btn)

        self.clean_btn = _PrimaryButton("Purge Notification Database", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        btn_row.addWidget(self.clean_btn)
        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._refresh()

    def _refresh(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        st = NotificationCleaner.get_status()
        self.status_label.setText(
            f"Notification DB: {st.database_path}\n"
            f"Database Size: {_fmt_bytes(st.database_size_bytes)}  •  "
            f"App Metadata: {_fmt_bytes(st.appmetadata_size_bytes)}\n"
            f"Total Storage: {_fmt_bytes(st.total_size_bytes)}"
        )

    def _on_clean(self):
        """Confirm and purge notification history and badges, then refresh.

        Manages on clean operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm Notification Purge",
            "Purge Action Center notification history and badge caches?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = NotificationCleaner.clean_notification_database()
            if res.success:
                QMessageBox.information(self, "Clean Complete", res.message)
            else:
                QMessageBox.warning(self, "Clean Warning", res.message)
            self._refresh()


# ===========================================================================
# 6. FILE MAGIC HEADER FORENSIC SNIFFER PAGE
# ===========================================================================

class FileSignatureSnifferPage(_Page):
    """Filesignaturesnifferpage.

    Manages FileSignatureSnifferPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Signature Sniffer page with folder picker, spoof filter, and results table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("File Magic Header & Forensics Sniffer", "Detect spoofed file extensions and verify binary file signatures against 100+ magic bytes."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.choose_btn = _SecondaryButton("Choose Folder to Scan…", self.p)
        self.choose_btn.clicked.connect(self._on_choose_folder)
        row.addWidget(self.choose_btn)

        self.scan_btn = _PrimaryButton("Scan for Spoofed Files", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.only_spoofed_check = QCheckBox("Show Only Spoofed / Mismatched Files")
        self.only_spoofed_check.setChecked(True)
        row.addWidget(self.only_spoofed_check)
        row.addStretch(1)
        cl.addLayout(row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Filename", "Declared Ext", "Actual Magic Format", "Header Hex", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._scan_path = Path.home()

    def _on_choose_folder(self):
        """Pick the directory to sniff.

        Manages on choose folder operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan")
        if folder:
            self._scan_path = Path(folder)

    def _on_scan(self):
        """Scan the chosen folder recursively for spoofed files.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return FileSignatureSniffer.scan_directory(
                self._scan_path,
                recursive=True,
                only_spoofed=self.only_spoofed_check.isChecked(),
            )

        def _done(results: List[SniffResult]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                results (List[SniffResult]): Collection or dictionary holding operation results.
            """
            self.scan_btn.setEnabled(True)
            self.table.setRowCount(len(results))
            for r, s in enumerate(results):
                self.table.setItem(r, 0, QTableWidgetItem(s.file_name))
                self.table.setItem(r, 1, QTableWidgetItem(s.declared_extension))
                self.table.setItem(r, 2, QTableWidgetItem(s.detected_format))
                self.table.setItem(r, 3, QTableWidgetItem(s.header_hex[:12]))
                st_item = QTableWidgetItem("⚠ SPOOFED EXTENSION" if s.is_spoofed else "Valid Header")
                if s.is_spoofed:
                    st_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(r, 4, st_item)

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.scan_btn.setEnabled(True))


# ===========================================================================
# 7. BINARY & HEX FILE DIFFER PAGE
# ===========================================================================

class BinaryDifferPage(_Page):
    """Binarydifferpage.

    Manages BinaryDifferPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Binary Differ page with File A/B pickers, compare button, and a hex diff table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Binary & Hex File Differ", "Side-by-side byte-level binary comparison and discrepancy offset viewer."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        # File selection rows
        f_row = QHBoxLayout()
        self.file_a_btn = _SecondaryButton("Select File A…", self.p)
        self.file_a_btn.clicked.connect(self._on_select_a)
        f_row.addWidget(self.file_a_btn)
        self.file_a_label = QLabel("File A: (None)")
        self.file_a_label.setObjectName("Muted")
        f_row.addWidget(self.file_a_label)

        self.file_b_btn = _SecondaryButton("Select File B…", self.p)
        self.file_b_btn.clicked.connect(self._on_select_b)
        f_row.addWidget(self.file_b_btn)
        self.file_b_label = QLabel("File B: (None)")
        self.file_b_label.setObjectName("Muted")
        f_row.addWidget(self.file_b_label)

        f_row.addStretch(1)
        self.diff_btn = _PrimaryButton("Compare Binary Files", self.p)
        self.diff_btn.clicked.connect(self._on_diff)
        f_row.addWidget(self.diff_btn)
        cl.addLayout(f_row)

        self.diff_summary_label = QLabel("Ready")
        self.diff_summary_label.setObjectName("Muted")
        cl.addWidget(self.diff_summary_label)

        # Hex diff table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Offset", "Hex (File A)", "ASCII (A)", "Hex (File B)", "ASCII (B)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(300)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._path_a: Optional[Path] = None
        self._path_b: Optional[Path] = None

    def _on_select_a(self):
        """Pick the first file to compare.

        Manages on select a operations and coordinates related state changes for the component.
        """
        f, _ = QFileDialog.getOpenFileName(self, "Select First File (A)")
        if f:
            self._path_a = Path(f)
            self.file_a_label.setText(f"File A: {self._path_a.name}")

    def _on_select_b(self):
        """Pick the second file to compare.

        Manages on select b operations and coordinates related state changes for the component.
        """
        f, _ = QFileDialog.getOpenFileName(self, "Select Second File (B)")
        if f:
            self._path_b = Path(f)
            self.file_b_label.setText(f"File B: {self._path_b.name}")

    def _on_diff(self):
        """Compare the two chosen files in the background.

        Manages on diff operations and coordinates related state changes for the component.
        """
        if not self._path_a or not self._path_b:
            QMessageBox.information(self, "Binary Differ", "Please select both File A and File B.")
            return

        self.diff_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return BinaryDiffer.compare_binary_files(self._path_a, self._path_b)

        def _done(rep: BinaryDiffReport):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                rep (BinaryDiffReport): The rep parameter.
            """
            self.diff_btn.setEnabled(True)
            if rep.error:
                QMessageBox.warning(self, "Diff Error", rep.error)
                return

            self.diff_summary_label.setText(
                f"Similarity: {rep.matching_percentage}%  •  "
                f"Discrepancies: {rep.total_differences_bytes:,} bytes  •  "
                f"First Difference: Offset {rep.first_difference_offset}" if rep.first_difference_offset is not None else "Files are 100% byte-identical"
            )

            self.table.setRowCount(len(rep.diff_chunks))
            for r, chk in enumerate(rep.diff_chunks):
                self.table.setItem(r, 0, QTableWidgetItem(f"0x{chk.offset:08X}"))
                self.table.setItem(r, 1, QTableWidgetItem(chk.left_hex))
                self.table.setItem(r, 2, QTableWidgetItem(chk.left_ascii))
                self.table.setItem(r, 3, QTableWidgetItem(chk.right_hex))
                self.table.setItem(r, 4, QTableWidgetItem(chk.right_ascii))

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.diff_btn.setEnabled(True))


# ===========================================================================
# 8. NTFS USN CHANGE JOURNAL SCANNER PAGE
# ===========================================================================

class UsnJournalPage(_Page):
    """Usnjournalpage.

    Manages UsnJournalPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the USN Journal page with volume combo, query button, and an info label.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("NTFS USN Change Journal Scanner", "Inspect volume change journal state and sub-millisecond MFT update sequence records."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        row = QHBoxLayout()
        row.addWidget(QLabel("Target Volume:"))
        self.drive_combo = QComboBox()
        self.drive_combo.addItems(["C:", "D:", "E:", "F:"])
        row.addWidget(self.drive_combo)

        self.query_btn = _PrimaryButton("Query USN Journal", self.p)
        self.query_btn.clicked.connect(self._on_query)
        row.addWidget(self.query_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.info_label = QLabel("Select a volume and click Query.")
        self.info_label.setObjectName("Muted")
        cl.addWidget(self.info_label)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._on_query()

    def _on_query(self):
        """Query the selected volume's USN journal and show its state.

        Manages on query operations and coordinates related state changes for the component.
        """
        drive = self.drive_combo.currentText()
        st = UsnJournalScanner.query_volume_journal(drive)
        if st.is_active:
            self.info_label.setText(
                f"USN Journal Status on {drive} — ACTIVE\n"
                f"Journal ID: 0x{st.journal_id:016X}\n"
                f"Next USN Offset: {st.next_usn:,}\n"
                f"Allocated Maximum Size: {_fmt_bytes(st.max_size_bytes)}\n"
                f"Allocation Delta: {_fmt_bytes(st.allocation_delta_bytes)}\n"
                f"Estimated Active Records: ~{st.estimated_records:,} filesystem update events"
            )
        else:
            self.info_label.setText(f"USN Journal on {drive}: {st.error or 'Inactive or Unsupported'}")


# ===========================================================================
# 9. PAR2 PARITY INTEGRITY TOOL PAGE
# ===========================================================================

class Par2RecoveryPage(_Page):
    """Par2recoverypage.

    Manages Par2RecoveryPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the PAR2 page with an open button, summary label, and protected-files table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("PAR2 (Parchive) Parity & Packet Validator", "Inspect Reed-Solomon PAR2 recovery sets, slice hashes, and file protection packets."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.open_btn = _PrimaryButton("Open .par2 File…", self.p)
        self.open_btn.clicked.connect(self._on_open_par2)
        row.addWidget(self.open_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("No PAR2 archive opened.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Protected File Name", "File Size", "16K Header MD5", "Full File MD5"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(300)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

    def _on_open_par2(self):
        """Open and parse a .par2 file, listing its recovery set and protected files.

        Manages on open par2 operations and coordinates related state changes for the component.
        """
        f, _ = QFileDialog.getOpenFileName(self, "Open PAR2 File", "", "PAR2 Files (*.par2 *.PAR2)")
        if f:
            rep = Par2RecoveryEngine.inspect_par2_file(f)
            if not rep.is_valid_par2:
                QMessageBox.warning(self, "Invalid PAR2", rep.error or "Failed to parse PAR2 structure.")
                return

            self.summary_label.setText(
                f"Set ID: {rep.recovery_set_id[:16]}…  •  "
                f"Slice Size: {_fmt_bytes(rep.slice_size)}  •  "
                f"Data Slices: {rep.total_data_slices}  •  "
                f"Recovery Slices: {rep.recovery_slices_available}"
            )

            self.table.setRowCount(len(rep.protected_files))
            for r, pf in enumerate(rep.protected_files):
                self.table.setItem(r, 0, QTableWidgetItem(pf.file_name))
                self.table.setItem(r, 1, QTableWidgetItem(_fmt_bytes(pf.file_size_bytes)))
                self.table.setItem(r, 2, QTableWidgetItem(pf.md5_hash_16k[:12]))
                self.table.setItem(r, 3, QTableWidgetItem(pf.md5_hash_full[:12]))


# ===========================================================================
# 10. BATCH IMAGE OPTIMIZER & WEBP TRANSCODER PAGE
# ===========================================================================

class ImageOptimizerPage(_Page):
    """Imageoptimizerpage.

    Manages ImageOptimizerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Image Optimizer page with picker, format/quality controls, and results table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Batch Image Optimizer & WebP Transcoder", "Compress images and convert PNG/JPEG/BMP/TIFF to WebP with EXIF/GPS privacy stripping."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        # File row
        row = QHBoxLayout()
        self.add_btn = _SecondaryButton("Select Images…", self.p)
        self.add_btn.clicked.connect(self._on_add_images)
        row.addWidget(self.add_btn)

        self.images_label = QLabel("0 images selected")
        self.images_label.setObjectName("Muted")
        row.addWidget(self.images_label)
        row.addStretch(1)
        cl.addLayout(row)

        # Options
        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("Output Format:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["WebP", "JPG", "PNG", "Original"])
        opt_row.addWidget(self.fmt_combo)

        opt_row.addWidget(QLabel("Quality (1-100):"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(80)
        opt_row.addWidget(self.quality_spin)

        opt_row.addStretch(1)
        self.start_btn = _PrimaryButton("Compress Images", self.p)
        self.start_btn.clicked.connect(self._on_start)
        opt_row.addWidget(self.start_btn)
        cl.addLayout(opt_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Image Name", "Original Size", "Compressed", "Space Saved", "Ratio"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(300)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._images: List[Path] = []

    def _on_add_images(self):
        """Pick images to optimize and show the selection count.

        Manages on add images operations and coordinates related state changes for the component.
        """
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images to Optimize", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)")
        if files:
            self._images = [Path(f) for f in files]
            self.images_label.setText(f"{len(self._images)} images selected")

    def _on_start(self):
        """Run batch optimization with the chosen format and quality.

        Manages on start operations and coordinates related state changes for the component.
        """
        if not self._images:
            QMessageBox.information(self, "Image Optimizer", "Please select images first.")
            return

        self.start_btn.setEnabled(False)
        self.table.setRowCount(0)

        target_fmt = self.fmt_combo.currentText().lower()
        quality = self.quality_spin.value()

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return ImageOptimizer.optimize_batch(
                self._images,
                target_format=target_fmt,
                quality=quality,
            )

        def _done(summary: BatchOptimizeSummary):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                summary (BatchOptimizeSummary): The summary parameter.
            """
            self.start_btn.setEnabled(True)
            self.table.setRowCount(len(summary.results))
            for r, res in enumerate(summary.results):
                self.table.setItem(r, 0, QTableWidgetItem(Path(res.source_path).name))
                self.table.setItem(r, 1, QTableWidgetItem(_fmt_bytes(res.original_size_bytes)))
                self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(res.compressed_size_bytes)))
                self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(res.space_saved_bytes)))
                self.table.setItem(r, 4, QTableWidgetItem(f"{res.compression_ratio_pct}%"))

            QMessageBox.information(
                self, "Optimization Complete",
                f"Optimized {summary.successful_count} images, freed {_fmt_bytes(summary.total_freed_bytes)}."
            )

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.start_btn.setEnabled(True))
