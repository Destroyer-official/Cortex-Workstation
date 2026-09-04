"""Cortex Cleaner & NexusExplorer — Enterprise Power Suite GUI Pages.

Contains 10 interactive, theme-aware GUI pages:
1. EnvVariableManagerPage (Environment Variable & PATH Dead-Link Optimizer)
2. WindowsServiceManagerPage (Service Profiler & Scenario-Based Optimizer)
3. FontCacheManagerPage (Font Cache & Orphaned Font Registry Cleaner)
4. TempFolderCleanerPage (Deep Multi-Location Stale Temp Cleaner)
5. ContextMenuManagerPage (Right-Click Context Menu Bloat Manager)
6. PagefileOptimizerPage (Virtual Memory & Paging File Hardware Optimizer)
7. DiagnosticDataManagerPage (Telemetry & Diagnostic Data Policy Manager)
8. StartupImpactPage (Task Manager StartupApproved & Impact Analyzer)
9. SlackSpaceAnalyzerPage (NTFS Cluster Allocation & Slack Space Forensics)
10. EventLogMonitorPage (Hardware Fault & Kernel Crash Event Monitor)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .tokens import Spacing
from .widgets import Card, hline, title_block
from .window import PremiumMainWindow, _Page

from cortex_unified.system_tools.env_variable_manager import EnvironmentVariableManager, PathAnalysisReport, PathEntry
from cortex_unified.system_tools.service_manager import WindowsServiceManager, ServiceInfo, ServiceProfileResult
from cortex_unified.system_tools.font_cache_manager import FontCacheManager, FontAnalysisReport, FontEntry
from cortex_unified.system_tools.temp_folder_cleaner import TempFolderCleaner, TempScanReport, TempLocation
from cortex_unified.system_tools.context_menu_manager import ContextMenuManager, ContextMenuReport, ContextMenuItem
from cortex_unified.system_tools.pagefile_optimizer import PagefileOptimizer, VirtualMemoryStatus
from cortex_unified.system_tools.diagnostic_data_manager import DiagnosticDataManager, TelemetryAuditReport
from cortex_unified.system_tools.startup_impact_analyzer import StartupImpactAnalyzer, StartupImpactReport
from cortex_unified.system_tools.slack_space_analyzer import SlackSpaceAnalyzer, VolumeSlackReport
from cortex_unified.system_tools.event_log_monitor import EventLogMonitor, AnomalyScanReport


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


def _run_task(win, work_fn, done_fn, err_fn=None):
    """Run work_fn on the window's worker runtime, or inline as a fallback, dispatching to done_fn / err_fn.

    Manages run task operations and coordinates related state changes for the component.

    Args:
        win: Parent window or shell controller instance.
        work_fn: The work fn parameter.
        done_fn: The done fn parameter.
        err_fn: Error message string or exception instance.
    """
    if hasattr(win, "worker_runtime") and getattr(win, "worker_runtime", None) is not None:
        win.worker_runtime.run(work_fn, on_result=done_fn, on_error=err_fn)
    else:
        try:
            res = work_fn()
            done_fn(res)
        except Exception as exc:
            if err_fn:
                err_fn(exc)


# ===========================================================================
# 1. ENVIRONMENT VARIABLE & PATH OPTIMIZER PAGE
# ===========================================================================

class EnvVariableManagerPage(_Page):
    """Envvariablemanagerpage.

    Manages EnvVariableManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the PATH Optimizer page with analyze/clean/export buttons and an entries table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Environment Variable & PATH Optimizer", "Audit PATH for dead links, duplicate directories, and manage User/System environment variables."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Analyze PATH", self.p)
        self.scan_btn.clicked.connect(self._on_analyze)
        row.addWidget(self.scan_btn)

        self.clean_btn = _SecondaryButton("Clean User PATH (Remove Dead & Duplicates)", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)

        self.export_btn = _SecondaryButton("Export to .env…", self.p)
        self.export_btn.clicked.connect(self._on_export)
        row.addWidget(self.export_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Analyze PATH to begin diagnosis.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Scope", "Directory Path", "Exists on Disk", "Duplicate"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._on_analyze()

    def _on_analyze(self):
        """Analyze PATH and list entries with dead-link and duplicate flags.

        Manages on analyze operations and coordinates related state changes for the component.
        """
        rep = EnvironmentVariableManager.analyze_path()
        self.summary_label.setText(
            f"Total PATH Entries: {rep.total_entries}  •  "
            f"Valid: {rep.valid_entries}  •  "
            f"Dead Links (Missing on Disk): {rep.dead_links}  •  "
            f"Duplicates: {rep.duplicates}"
        )
        self.table.setRowCount(len(rep.entries))
        for r, e in enumerate(rep.entries):
            self.table.setItem(r, 0, QTableWidgetItem(e.scope))
            self.table.setItem(r, 1, QTableWidgetItem(e.directory))
            ex_item = QTableWidgetItem("Yes" if e.exists else "DEAD LINK (Missing)")
            if not e.exists:
                ex_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(r, 2, ex_item)
            dup_item = QTableWidgetItem("Duplicate" if e.is_duplicate else "Unique")
            if e.is_duplicate:
                dup_item.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(r, 3, dup_item)

    def _on_clean(self):
        """Confirm and remove dead/duplicate User PATH entries, then re-analyze.

        Manages on clean operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm PATH Cleanup",
            "Clean User PATH by removing non-existent folders and redundant duplicates?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = EnvironmentVariableManager.clean_path(scope="User")
            QMessageBox.information(
                self, "Clean Complete",
                f"Removed {res.entries_removed} entries ({res.dead_links_removed} dead links, {res.duplicates_removed} duplicates)."
            )
            self._on_analyze()

    def _on_export(self):
        """Export environment variables to a .env or .bat file.

        Manages on export operations and coordinates related state changes for the component.
        """
        f, _ = QFileDialog.getSaveFileName(self, "Export Environment Variables", "environment.env", "Env Files (*.env *.bat)")
        if f:
            fmt = "bat" if f.endswith(".bat") else "env"
            ok = EnvironmentVariableManager.export_env_to_file(f, fmt=fmt)
            if ok:
                QMessageBox.information(self, "Export Complete", f"Exported variables to {f}.")


# ===========================================================================
# 2. WINDOWS SERVICE MANAGER PAGE
# ===========================================================================

class WindowsServiceManagerPage(_Page):
    """Windowsservicemanagerpage.

    Manages WindowsServiceManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Service Manager page with scan button, profile combo, and services table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Windows Service Profile Optimizer", "Profile and disable unnecessary background services with pre-tuned Gaming, Minimal, and Developer presets."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Services", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        row.addWidget(QLabel("Preset Profile:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Gaming", "Developer", "Minimal"])
        row.addWidget(self.profile_combo)

        self.apply_btn = _SecondaryButton("Apply Profile", self.p)
        self.apply_btn.clicked.connect(self._on_apply_profile)
        row.addWidget(self.apply_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Service Name", "Display Name", "Status", "Startup Type", "Category"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

    def _on_scan(self):
        """Enumerate Windows services on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return WindowsServiceManager.enumerate_services()

        def _done(services: List[ServiceInfo]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                services (List[ServiceInfo]): The services parameter.
            """
            self.scan_btn.setEnabled(True)
            self.table.setRowCount(len(services))
            for r, s in enumerate(services):
                self.table.setItem(r, 0, QTableWidgetItem(s.name))
                self.table.setItem(r, 1, QTableWidgetItem(s.display_name))
                st_item = QTableWidgetItem(s.status)
                if s.status == "Running":
                    st_item.setForeground(Qt.GlobalColor.green)
                self.table.setItem(r, 2, st_item)
                self.table.setItem(r, 3, QTableWidgetItem(s.startup_type))
                cat_item = QTableWidgetItem(s.category if s.category else "Standard")
                if s.safe_to_disable:
                    cat_item.setForeground(Qt.GlobalColor.yellow)
                self.table.setItem(r, 4, cat_item)

        _run_task(self.win, _work, _done, lambda err: self.scan_btn.setEnabled(True))

    def _on_apply_profile(self):
        """Confirm and apply the selected service profile, then rescan.

        Manages on apply profile operations and coordinates related state changes for the component.
        """
        prof = self.profile_combo.currentText()
        confirm = QMessageBox.question(
            self, f"Confirm {prof} Profile",
            f"Apply '{prof}' optimization profile to disable redundant background services?\n\n(Requires Administrator privileges)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = WindowsServiceManager.apply_profile(prof)
            QMessageBox.information(
                self, "Profile Applied",
                f"Configured {res.services_changed} services ({res.services_stopped} stopped, {res.services_disabled} disabled)."
            )
            self._on_scan()


# ===========================================================================
# 3. FONT CACHE & ORPHANED REGISTRY CLEANER PAGE
# ===========================================================================

class FontCacheManagerPage(_Page):
    """Fontcachemanagerpage.

    Manages FontCacheManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Font Cache page with scan/clean buttons and a fonts table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Font Cache & Registry Orphan Cleaner", "Inspect installed font footprint, detect duplicate font files, and clean orphaned font registry entries."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Installed Fonts", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.clean_btn = _SecondaryButton("Remove Orphaned Font Entries", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Ready")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Font Name", "File Name", "Format", "Size", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._on_scan()

    def _on_scan(self):
        """Analyze installed fonts and flag orphans and duplicates.

        Manages on scan operations and coordinates related state changes for the component.
        """
        rep = FontCacheManager.analyze()
        self.summary_label.setText(
            f"Total Fonts: {rep.total_fonts}  •  "
            f"Total Font Storage: {_fmt_bytes(rep.total_size_bytes)}  •  "
            f"Orphaned (Missing Files): {rep.orphaned_count}  •  "
            f"Duplicates: {rep.duplicate_count}"
        )
        self.table.setRowCount(len(rep.entries))
        for r, f in enumerate(rep.entries):
            self.table.setItem(r, 0, QTableWidgetItem(f.name))
            self.table.setItem(r, 1, QTableWidgetItem(f.file_name))
            self.table.setItem(r, 2, QTableWidgetItem(f.format))
            self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(f.file_size_bytes)))
            st_item = QTableWidgetItem("ORPHANED (File Missing)" if f.is_orphaned else "Installed & Active")
            if f.is_orphaned:
                st_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(r, 4, st_item)

    def _on_clean(self):
        """Confirm and remove orphaned font entries, then rescan.

        Manages on clean operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm Orphan Cleanup",
            "Delete orphaned font registry entries pointing to missing files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = FontCacheManager.clean_orphaned_entries()
            QMessageBox.information(self, "Cleanup Complete", f"Removed {res.orphans_removed} orphaned font entries.")
            self._on_scan()


# ===========================================================================
# 4. DEEP MULTI-LOCATION TEMP CLEANER PAGE
# ===========================================================================

class TempFolderCleanerPage(_Page):
    """Tempfoldercleanerpage.

    Manages TempFolderCleanerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Temp Cleaner page with age spinner, scan/clean buttons, and a locations table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Deep Multi-Location Temp Cleaner", "Scan and purge stale temporary files, GPU shader caches, and Windows patch residues."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan All Temp Locations", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        row.addWidget(QLabel("Min File Age (Hours):"))
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(1, 720)
        self.hours_spin.setValue(24)
        row.addWidget(self.hours_spin)

        self.clean_btn = _SecondaryButton("Purge Stale Temp Files", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Ready")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Location Name", "Folder Path", "Total Files", "Total Size", "Recoverable Stale Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._on_scan()

    def _on_scan(self):
        """Scan all temp locations and show stale-file totals.

        Manages on scan operations and coordinates related state changes for the component.
        """
        h = self.hours_spin.value()
        rep = TempFolderCleaner.scan(stale_hours=h)
        self.summary_label.setText(
            f"Total Discovered Files: {rep.total_files:,} ({_fmt_bytes(rep.total_size_bytes)})  •  "
            f"Stale & Recoverable: {rep.stale_files:,} files ({_fmt_bytes(rep.stale_size_bytes)})"
        )
        self.table.setRowCount(len(rep.locations))
        for r, loc in enumerate(rep.locations):
            self.table.setItem(r, 0, QTableWidgetItem(loc.name))
            self.table.setItem(r, 1, QTableWidgetItem(loc.path))
            self.table.setItem(r, 2, QTableWidgetItem(str(loc.total_files)))
            self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(loc.total_size_bytes)))
            st_item = QTableWidgetItem(_fmt_bytes(loc.stale_size_bytes))
            if loc.stale_size_bytes > 0:
                st_item.setForeground(Qt.GlobalColor.green)
            self.table.setItem(r, 4, st_item)

    def _on_clean(self):
        """Confirm and delete temp files older than the chosen age, then rescan.

        Manages on clean operations and coordinates related state changes for the component.
        """
        h = self.hours_spin.value()
        confirm = QMessageBox.question(
            self, "Confirm Temp Purge",
            f"Delete temporary files older than {h} hours across all discovered locations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = TempFolderCleaner.clean(stale_hours=h)
            QMessageBox.information(
                self, "Purge Complete",
                f"Deleted {res.files_deleted:,} files ({_fmt_bytes(res.bytes_freed)} freed). Skipped {res.locked_skipped} locked files."
            )
            self._on_scan()


# ===========================================================================
# 5. CONTEXT MENU & SHELL EXTENSION MANAGER PAGE
# ===========================================================================

class ContextMenuManagerPage(_Page):
    """Contextmenumanagerpage.

    Manages ContextMenuManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Context Menu page with scan button, enable/disable actions, and an entries table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Context Menu & Shell Extension Manager", "Inspect and disable bloated right-click Explorer context menu handlers and orphaned items."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Context Menu", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.disable_btn = _SecondaryButton("Disable Selected Entry", self.p)
        self.disable_btn.clicked.connect(self._on_disable_selected)
        row.addWidget(self.disable_btn)

        self.enable_btn = _SecondaryButton("Enable Selected Entry", self.p)
        self.enable_btn.clicked.connect(self._on_enable_selected)
        row.addWidget(self.enable_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Ready")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Scope", "Command Executable", "Status", "Target Exists"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._entries: List[ContextMenuItem] = []
        self._on_scan()

    def _on_scan(self):
        """Analyze context-menu entries and flag orphaned handlers.

        Manages on scan operations and coordinates related state changes for the component.
        """
        rep = ContextMenuManager.analyze()
        self._entries = rep.entries
        self.summary_label.setText(
            f"Total Shell Extensions: {rep.total_entries}  •  "
            f"Orphaned Handlers (Target App Missing): {rep.orphaned_entries}"
        )
        self.table.setRowCount(len(rep.entries))
        for r, e in enumerate(rep.entries):
            self.table.setItem(r, 0, QTableWidgetItem(e.name))
            self.table.setItem(r, 1, QTableWidgetItem(e.scope))
            self.table.setItem(r, 2, QTableWidgetItem(e.command))
            st_item = QTableWidgetItem("Enabled" if e.is_enabled else "Disabled")
            if not e.is_enabled:
                st_item.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(r, 3, st_item)
            ex_item = QTableWidgetItem("Found" if e.program_exists else ("ORPHANED" if e.is_orphaned else "System"))
            if e.is_orphaned:
                ex_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(r, 4, ex_item)

    def _on_disable_selected(self):
        """Disable the context-menu entry selected in the table.

        Manages on disable selected operations and coordinates related state changes for the component.
        """
        row = self.table.currentRow()
        if 0 <= row < len(self._entries):
            item = self._entries[row]
            ok, msg = ContextMenuManager.disable_entry(item.registry_path)
            if ok:
                QMessageBox.information(self, "Disabled", msg)
                self._on_scan()
            else:
                QMessageBox.warning(self, "Warning", msg)

    def _on_enable_selected(self):
        """Enable the context-menu entry selected in the table.

        Manages on enable selected operations and coordinates related state changes for the component.
        """
        row = self.table.currentRow()
        if 0 <= row < len(self._entries):
            item = self._entries[row]
            ok, msg = ContextMenuManager.enable_entry(item.registry_path)
            if ok:
                QMessageBox.information(self, "Enabled", msg)
                self._on_scan()
            else:
                QMessageBox.warning(self, "Warning", msg)


# ===========================================================================
# 6. VIRTUAL MEMORY & PAGEFILE OPTIMIZER PAGE
# ===========================================================================

class PagefileOptimizerPage(_Page):
    """Pagefileoptimizerpage.

    Manages PagefileOptimizerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Pagefile page with status labels, drive/size controls, and apply/reset buttons.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Virtual Memory & Pagefile Hardware Optimizer", "Configure pagefile.sys allocation to eliminate SSD write amplification and ensure system stability."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        self.info_label = QLabel("Loading Virtual Memory state...")
        cl.addWidget(self.info_label)

        self.rec_label = QLabel("")
        self.rec_label.setWordWrap(True)
        self.rec_label.setStyleSheet("padding: 10px; border-radius: 6px; background-color: rgba(255, 255, 255, 0.05);")
        cl.addWidget(self.rec_label)

        opt_row = QHBoxLayout()
        opt_row.addWidget(QLabel("Target Drive:"))
        self.drive_combo = QComboBox()
        self.drive_combo.addItems(["C:", "D:", "E:"])
        opt_row.addWidget(self.drive_combo)

        opt_row.addWidget(QLabel("Initial (MB):"))
        self.init_spin = QSpinBox()
        self.init_spin.setRange(512, 65536)
        self.init_spin.setValue(4096)
        opt_row.addWidget(self.init_spin)

        opt_row.addWidget(QLabel("Maximum (MB):"))
        self.max_spin = QSpinBox()
        self.max_spin.setRange(512, 65536)
        self.max_spin.setValue(8192)
        opt_row.addWidget(self.max_spin)

        opt_row.addStretch(1)
        self.apply_btn = _PrimaryButton("Apply Fixed Allocation", self.p)
        self.apply_btn.clicked.connect(self._on_apply)
        opt_row.addWidget(self.apply_btn)

        self.auto_btn = _SecondaryButton("Reset to System-Managed", self.p)
        self.auto_btn.clicked.connect(self._on_reset_auto)
        opt_row.addWidget(self.auto_btn)
        cl.addLayout(opt_row)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._refresh()

    def _refresh(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        st = PagefileOptimizer.get_status()
        self.info_label.setText(
            f"Physical RAM: {_fmt_bytes(st.total_physical_bytes)} (Available: {_fmt_bytes(st.available_physical_bytes)})\n"
            f"Committed Pagefile: {_fmt_bytes(st.total_pagefile_bytes)}  •  Memory Load: {st.memory_load_percent}%\n"
            f"Current Configuration: {'Automatic / System-Managed' if st.current_config.is_automatic else f'Custom ({st.current_config.initial_mb}MB - {st.current_config.maximum_mb}MB on {st.current_config.drive_letter})'}"
        )
        self.rec_label.setText(f"Hardware Recommendation:\n{st.recommendation_reason}\nRecommended Range: {st.recommended_min_mb} MB - {st.recommended_max_mb} MB")
        self.init_spin.setValue(st.recommended_min_mb)
        self.max_spin.setValue(st.recommended_max_mb)

    def _on_apply(self):
        """Confirm and set a fixed pagefile on the chosen drive, then refresh.

        Manages on apply operations and coordinates related state changes for the component.
        """
        drive = self.drive_combo.currentText()
        init_mb = self.init_spin.value()
        max_mb = self.max_spin.value()
        confirm = QMessageBox.question(
            self, "Confirm Pagefile Setup",
            f"Set paging file on {drive} to {init_mb}MB - {max_mb}MB?\n\n(Requires Administrator privileges)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            ok, msg = PagefileOptimizer.set_custom_pagefile(drive, init_mb, max_mb)
            if ok:
                QMessageBox.information(self, "Pagefile Configured", msg)
            else:
                QMessageBox.warning(self, "Warning", msg)
            self._refresh()

    def _on_reset_auto(self):
        """Reset the pagefile to system-managed, then refresh.

        Manages on reset auto operations and coordinates related state changes for the component.
        """
        ok, msg = PagefileOptimizer.set_automatic_pagefile()
        if ok:
            QMessageBox.information(self, "Automatic Mode", msg)
        else:
            QMessageBox.warning(self, "Warning", msg)
        self._refresh()


# ===========================================================================
# 7. TELEMETRY & DIAGNOSTIC DATA MANAGER PAGE
# ===========================================================================

class DiagnosticDataManagerPage(_Page):
    """Diagnosticdatamanagerpage.

    Manages DiagnosticDataManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Telemetry page with audit/harden buttons, score label, and settings table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Windows Telemetry & Diagnostic Data Manager", "Audit OS diagnostic data submission, CEIP tracking, and enforce maximum telemetry privacy."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.audit_btn = _SecondaryButton("Audit Telemetry State", self.p)
        self.audit_btn.clicked.connect(self._on_audit)
        row.addWidget(self.audit_btn)

        self.harden_btn = _PrimaryButton("Enforce Maximum Privacy Preset", self.p)
        self.harden_btn.clicked.connect(self._on_harden)
        row.addWidget(self.harden_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.score_label = QLabel("Auditing...")
        cl.addWidget(self.score_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Telemetry Feature", "Current Setting", "Recommended", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(300)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._on_audit()

    def _on_audit(self):
        """Audit telemetry settings and show the privacy hardening score.

        Manages on audit operations and coordinates related state changes for the component.
        """
        rep = DiagnosticDataManager.audit_telemetry()
        self.score_label.setText(
            f"Privacy Hardening Score: {rep.privacy_score_percent}%  •  "
            f"Protected: {rep.hardened_count} / {rep.total_settings} settings  •  "
            f"Telemetry Exposed: {rep.exposed_count}"
        )
        self.table.setRowCount(len(rep.settings))
        for r, s in enumerate(rep.settings):
            self.table.setItem(r, 0, QTableWidgetItem(s.name))
            self.table.setItem(r, 1, QTableWidgetItem(str(s.current_value) if s.current_value is not None else "Default / Unset"))
            self.table.setItem(r, 2, QTableWidgetItem(str(s.recommended_value)))
            st_item = QTableWidgetItem("PROTECTED" if s.is_hardened else "EXPOSED (Telemetry Active)")
            if s.is_hardened:
                st_item.setForeground(Qt.GlobalColor.green)
            else:
                st_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(r, 3, st_item)

    def _on_harden(self):
        """Confirm and apply maximum-privacy telemetry policies, then re-audit.

        Manages on harden operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm Hardening",
            "Enforce maximum privacy by disabling diagnostic telemetry, CEIP, and activity tracking?\n\n(Requires Administrator privileges)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            applied, errors = DiagnosticDataManager.apply_maximum_privacy()
            if errors:
                QMessageBox.warning(self, "Notice", f"Applied {applied} settings.\nErrors: {'; '.join(errors[:2])}")
            else:
                QMessageBox.information(self, "Hardening Complete", f"All {applied} telemetry policies successfully hardened to maximum privacy.")
            self._on_audit()


# ===========================================================================
# 8. STARTUP IMPACT ANALYZER PAGE
# ===========================================================================

class StartupImpactPage(_Page):
    """Startupimpactpage.

    Manages StartupImpactPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Startup Impact page with scan/toggle buttons and an items table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Startup Impact Analyzer & Sequencer", "Analyze boot delay impact from StartupApproved records and toggle heavy startup programs."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Startup Impact", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.toggle_btn = _SecondaryButton("Toggle Selected Item State", self.p)
        self.toggle_btn.clicked.connect(self._on_toggle)
        row.addWidget(self.toggle_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Ready")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["App Name", "Scope", "Impact Level", "Status", "Binary Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._items = []
        self._on_scan()

    def _on_scan(self):
        """Analyze startup items and show impact levels and boot delay.

        Manages on scan operations and coordinates related state changes for the component.
        """
        rep = StartupImpactAnalyzer.analyze_startup()
        self._items = rep.items
        self.summary_label.setText(
            f"Startup Items: {rep.total_startup_items}  •  "
            f"Enabled: {rep.enabled_count}  •  "
            f"High Impact Apps: {rep.high_impact_count}  •  "
            f"Estimated Boot Delay: +{rep.estimated_boot_delay_seconds} seconds"
        )
        self.table.setRowCount(len(rep.items))
        for r, it in enumerate(rep.items):
            self.table.setItem(r, 0, QTableWidgetItem(it.name))
            self.table.setItem(r, 1, QTableWidgetItem(it.scope))
            imp_item = QTableWidgetItem(it.impact_level)
            if it.impact_level == "High":
                imp_item.setForeground(Qt.GlobalColor.red)
            elif it.impact_level == "Medium":
                imp_item.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(r, 2, imp_item)
            st_item = QTableWidgetItem("Enabled" if it.is_enabled else "Disabled")
            if not it.is_enabled:
                st_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(r, 3, st_item)
            self.table.setItem(r, 4, QTableWidgetItem(_fmt_bytes(it.file_size_bytes)))

    def _on_toggle(self):
        """Enable or disable the startup item selected in the table.

        Manages on toggle operations and coordinates related state changes for the component.
        """
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            it = self._items[row]
            new_state = not it.is_enabled
            is_u = "User" in it.scope
            ok, msg = StartupImpactAnalyzer.toggle_item_state(it.name, enable=new_state, is_user=is_u)
            if ok:
                QMessageBox.information(self, "State Changed", msg)
                self._on_scan()
            else:
                QMessageBox.warning(self, "Warning", msg)


# ===========================================================================
# 9. NTFS CLUSTER ALLOCATION & SLACK SPACE FORENSICS PAGE
# ===========================================================================

class SlackSpaceAnalyzerPage(_Page):
    """Slackspaceanalyzerpage.

    Manages SlackSpaceAnalyzerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Slack Space page with folder picker, analyze button, and offenders table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("NTFS Cluster Slack Space Forensics", "Analyze storage wasted by filesystem cluster allocation and identify severe slack waste directories."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.choose_btn = _SecondaryButton("Choose Folder to Analyze…", self.p)
        self.choose_btn.clicked.connect(self._on_choose)
        row.addWidget(self.choose_btn)

        self.scan_btn = _PrimaryButton("Analyze Slack Waste", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Select a folder (e.g. workspace, node_modules, AppData) and click Analyze.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Directory Path", "File Count", "Logical Size", "Physical Allocation", "Slack Waste (% Wasted)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._target_path = Path.home()

    def _on_choose(self):
        """Pick a directory and immediately analyze it.

        Manages on choose operations and coordinates related state changes for the component.
        """
        f = QFileDialog.getExistingDirectory(self, "Select Directory to Analyze")
        if f:
            self._target_path = Path(f)
            self._on_scan()

    def _on_scan(self):
        """Analyze cluster slack waste on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return SlackSpaceAnalyzer.analyze_directory(self._target_path, max_depth=2)

        def _done(rep: VolumeSlackReport):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                rep (VolumeSlackReport): The rep parameter.
            """
            self.scan_btn.setEnabled(True)
            self.summary_label.setText(
                f"Cluster Size: {rep.cluster_size_bytes} bytes  •  "
                f"Scanned Files: {rep.total_files_scanned:,}  •  "
                f"Logical Size: {_fmt_bytes(rep.total_logical_bytes)}  •  "
                f"Physical Size: {_fmt_bytes(rep.total_physical_bytes)}  •  "
                f"Total Slack Waste: {_fmt_bytes(rep.total_slack_waste_bytes)} ({rep.overall_slack_percentage}% wasted space)"
            )
            self.table.setRowCount(len(rep.worst_offenders))
            for r, o in enumerate(rep.worst_offenders):
                self.table.setItem(r, 0, QTableWidgetItem(o.path))
                self.table.setItem(r, 1, QTableWidgetItem(str(o.file_count)))
                self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(o.logical_size_bytes)))
                self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(o.physical_size_bytes)))
                waste_item = QTableWidgetItem(f"{_fmt_bytes(o.slack_waste_bytes)} ({o.slack_percentage}%)")
                if o.slack_percentage > 20:
                    waste_item.setForeground(Qt.GlobalColor.yellow)
                self.table.setItem(r, 4, waste_item)

        _run_task(self.win, _work, _done, lambda err: self.scan_btn.setEnabled(True))


# ===========================================================================
# 10. HARDWARE FAULT & CRASH EVENT MONITOR PAGE
# ===========================================================================

class EventLogMonitorPage(_Page):
    """Eventlogmonitorpage.

    Manages EventLogMonitorPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Event Monitor page with scan button and an events table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Hardware Fault & Crash Event Monitor", "Real-time anomaly scanner for NTFS bad blocks, controller faults, BSODs, and dirty shutdowns."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Event Log for Faults", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Scan to inspect hardware and system event logs.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Category", "Event ID", "Level", "Source", "Timestamp", "Summary"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

    def _on_scan(self):
        """Query event-log anomalies on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return EventLogMonitor.query_anomalies()

        def _done(rep: AnomalyScanReport):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                rep (AnomalyScanReport): The rep parameter.
            """
            self.scan_btn.setEnabled(True)
            self.summary_label.setText(
                f"Critical Faults: {rep.critical_count}  •  "
                f"Disk/NTFS Errors: {rep.disk_errors_count}  •  "
                f"Crashes: {rep.crash_count}  •  "
                f"Total Anomalies Logged: {rep.total_anomalies}"
            )
            self.table.setRowCount(len(rep.events))
            for r, ev in enumerate(rep.events):
                self.table.setItem(r, 0, QTableWidgetItem(ev.category))
                self.table.setItem(r, 1, QTableWidgetItem(str(ev.event_id)))
                lvl_item = QTableWidgetItem(ev.level)
                if ev.level == "Critical":
                    lvl_item.setForeground(Qt.GlobalColor.red)
                elif ev.level == "Error":
                    lvl_item.setForeground(Qt.GlobalColor.yellow)
                self.table.setItem(r, 2, lvl_item)
                self.table.setItem(r, 3, QTableWidgetItem(ev.source))
                self.table.setItem(r, 4, QTableWidgetItem(ev.time_created))
                self.table.setItem(r, 5, QTableWidgetItem(ev.message))

        _run_task(self.win, _work, _done, lambda err: self.scan_btn.setEnabled(True))
