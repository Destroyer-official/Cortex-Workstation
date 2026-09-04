"""Cortex Cleaner & NexusExplorer — Expanded Enterprise Power Tools Pages.

Contains 11 interactive, theme-aware GUI pages:
1. LinksManagerPage (NTFS Junctions, Symlinks & Hardlinks)
2. FastCopierPage (High-Throughput Fast File Transfer & Copier)
3. TimestampTouchPage (Forensic MACB File Timestamp & Attribute Touch)
4. ArchiveManagerPage (Multi-Format Archive Studio)
5. PrefetchAnalyzerPage (Windows Prefetch & SysMain Trace Analyzer)
6. SearchIndexOptimizerPage (Windows Search Index Database Optimizer)
7. DnsBenchmarkPage (DNS Latency Benchmark & Resolver Selector)
8. DiskBenchmarkPage (Storage Throughput & 4K IOPS Benchmark)
9. MemoryOptimizerPage (RAM Composition & Process Working Set Optimizer)
10. DevCleanerPage (Developer Ecosystem Build Artifacts Purger)
11. BrowserDeepCleanerPage (Multi-Browser Deep Privacy & Cache Sanitizer)
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
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

def PrimaryButton(text: str, parent=None) -> QPushButton:
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

def SecondaryButton(text: str, parent=None) -> QPushButton:
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

from NexusExplorer.native.nexus_links_manager import LinksManager, LinkType, LinkItem
from NexusExplorer.native.nexus_fast_copier import FastCopier, CopyMode, CopyItemProgress, CopySummary
from NexusExplorer.native.nexus_timestamp_touch import TimestampTouchEngine, TimestampInfo
from NexusExplorer.native.nexus_archive_manager import ArchiveManager, ArchiveFormat, CompressionLevel
from cortex_unified.system_tools.prefetch_analyzer import PrefetchAnalyzer, PrefetchEntry
from cortex_unified.system_tools.search_index_optimizer import SearchIndexOptimizer
from cortex_unified.system_tools.dns_benchmark import DnsBenchmarkEngine, DnsBenchmarkResult, KNOWN_DNS_PROVIDERS
from cortex_unified.system_tools.disk_benchmark import DiskBenchmarkEngine, DiskBenchmarkReport
from cortex_unified.system_tools.memory_optimizer import MemoryOptimizer, ProcessMemoryItem
from cortex_unified.system_tools.dev_cleaner import DevCleaner, DevCacheItem
from cortex_unified.system_tools.browser_deep_cleaner import BrowserDeepCleaner, BrowserTarget


def _fmt_bytes(b: int) -> str:
    """Format bytes into human-readable string.

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


# ===========================================================================
# 1. LINKS & JUNCTIONS MANAGER PAGE
# ===========================================================================

class LinksManagerPage(_Page):
    """Linksmanagerpage.

    Manages LinksManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Links Manager page with folder picker, recursive option, and links table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("NTFS Links & Junctions Manager", "Inspect, create, and safely manage Directory Junctions, Symlinks, and Hardlinks."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        # Controls row
        row = QHBoxLayout()
        self.choose_btn = SecondaryButton("Choose Folder…", self.p)
        self.choose_btn.clicked.connect(self._on_choose_folder)
        row.addWidget(self.choose_btn)

        self.scan_btn = PrimaryButton("Scan for Links", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.recursive_box = QCheckBox("Scan Subdirectories (Recursive)")
        row.addWidget(self.recursive_box)
        row.addStretch(1)

        self.remove_btn = SecondaryButton("Safely Remove Selected Link", self.p)
        self.remove_btn.clicked.connect(self._on_remove_link)
        row.addWidget(self.remove_btn)
        cl.addLayout(row)

        self.selected_path_label = QLabel("Scan Target: (Not Selected)")
        self.selected_path_label.setObjectName("Muted")
        cl.addWidget(self.selected_path_label)

        # Links Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Target Destination", "Status", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._scan_dir: Optional[Path] = None
        self._items: List[LinkItem] = []

    def _on_choose_folder(self):
        """Open a directory picker and remember it as the scan target.

        Manages on choose folder operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Scan for Links")
        if folder:
            self._scan_dir = Path(folder)
            self.selected_path_label.setText(f"Scan Target: {self._scan_dir}")

    def _on_scan(self):
        """Scan the chosen directory (or home) for links on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        target = self._scan_dir or Path.home()
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return LinksManager.scan_links_in_directory(target, recursive=self.recursive_box.isChecked())

        def _done(items: List[LinkItem]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                items (List[LinkItem]): Collection of items or entries to process.
            """
            self.scan_btn.setEnabled(True)
            self._items = items
            self.table.setRowCount(len(items))
            for r, it in enumerate(items):
                self.table.setItem(r, 0, QTableWidgetItem(it.name))
                self.table.setItem(r, 1, QTableWidgetItem(it.link_type.value))
                self.table.setItem(r, 2, QTableWidgetItem(it.target_path))
                status_item = QTableWidgetItem("Broken Link" if it.is_broken else "Valid Link")
                if it.is_broken:
                    status_item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(r, 3, status_item)
                self.table.setItem(r, 4, QTableWidgetItem(_fmt_bytes(it.size_bytes)))

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.scan_btn.setEnabled(True))

    def _on_remove_link(self):
        """Confirm and remove the selected link without touching its target files.

        Manages on remove link operations and coordinates related state changes for the component.
        """
        sel = self.table.currentRow()
        if sel < 0 or sel >= len(self._items):
            QMessageBox.information(self, "Links Manager", "Please select a link to remove.")
            return

        item = self._items[sel]
        confirm = QMessageBox.question(
            self, "Confirm Link Removal",
            f"Safely remove {item.link_type.value} '{item.name}'?\n\nTarget directory files will NOT be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = LinksManager.remove_link_safely(item.path)
            if res.success:
                QMessageBox.information(self, "Success", res.message)
                self._on_scan()
            else:
                QMessageBox.warning(self, "Removal Error", res.message)


# ===========================================================================
# 2. FAST COPIER & TRANSFER ENGINE PAGE
# ===========================================================================

class FastCopierPage(_Page):
    """Fastcopierpage.

    Manages FastCopierPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Fast Copier page with source/destination pickers, mode combo, and progress bar.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("High-Throughput Fast File Copier", "Multi-threaded asynchronous transfer engine with unbuffered direct streaming and SHA-256 verification."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        # Source / Dest rows
        s_row = QHBoxLayout()
        self.add_source_btn = SecondaryButton("Add Source Files / Folders…", self.p)
        self.add_source_btn.clicked.connect(self._on_add_source)
        s_row.addWidget(self.add_source_btn)
        self.sources_label = QLabel("Sources: 0 items selected")
        self.sources_label.setObjectName("Muted")
        s_row.addWidget(self.sources_label)
        s_row.addStretch(1)
        cl.addLayout(s_row)

        d_row = QHBoxLayout()
        self.dest_btn = SecondaryButton("Choose Destination Folder…", self.p)
        self.dest_btn.clicked.connect(self._on_choose_dest)
        d_row.addWidget(self.dest_btn)
        self.dest_label = QLabel("Destination: (Not Selected)")
        self.dest_label.setObjectName("Muted")
        d_row.addWidget(self.dest_label)
        d_row.addStretch(1)
        cl.addLayout(d_row)

        # Mode & options
        m_row = QHBoxLayout()
        m_row.addWidget(QLabel("Copy Strategy:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([CopyMode.STANDARD.value, CopyMode.DIRECT_IO.value, CopyMode.VERIFY_SHA256.value])
        m_row.addWidget(self.mode_combo)

        m_row.addWidget(QLabel("Speed Limit (KB/s, 0=Max):"))
        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(0, 1000000)
        self.speed_limit_spin.setValue(0)
        m_row.addWidget(self.speed_limit_spin)
        m_row.addStretch(1)
        cl.addLayout(m_row)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        cl.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("Muted")
        cl.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.start_btn = PrimaryButton("Start Fast Copy", self.p)
        self.start_btn.clicked.connect(self._on_start_copy)
        btn_row.addWidget(self.start_btn)
        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._sources: List[Path] = []
        self._dest_dir: Optional[Path] = None

    def _on_add_source(self):
        """Append a picked source directory to the copy list.

        Manages on add source operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Source Directory")
        if folder:
            self._sources.append(Path(folder))
            self.sources_label.setText(f"Sources: {len(self._sources)} items selected ({self._sources[-1].name})")

    def _on_choose_dest(self):
        """Pick the destination directory for the batch copy.

        Manages on choose dest operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Directory")
        if folder:
            self._dest_dir = Path(folder)
            self.dest_label.setText(f"Destination: {self._dest_dir}")

    def _on_start_copy(self):
        """Run the batch copy in the background with the chosen mode and speed limit.

        Manages on start copy operations and coordinates related state changes for the component.
        """
        if not self._sources or not self._dest_dir:
            QMessageBox.information(self, "Fast Copier", "Please select source files/folders and destination directory.")
            return

        self.start_btn.setEnabled(False)
        self.status_label.setText("Transferring files...")

        mode_map = {
            CopyMode.STANDARD.value: CopyMode.STANDARD,
            CopyMode.DIRECT_IO.value: CopyMode.DIRECT_IO,
            CopyMode.VERIFY_SHA256.value: CopyMode.VERIFY_SHA256,
        }
        selected_mode = mode_map.get(self.mode_combo.currentText(), CopyMode.STANDARD)
        speed_lim = self.speed_limit_spin.value()

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return FastCopier.copy_batch(
                self._sources,
                self._dest_dir,
                mode=selected_mode,
                speed_limit_kb_s=speed_lim,
            )

        def _done(summary: CopySummary):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                summary (CopySummary): The summary parameter.
            """
            self.start_btn.setEnabled(True)
            self.progress_bar.setValue(100)
            if summary.success:
                msg = f"Transferred {summary.files_copied} files ({_fmt_bytes(summary.bytes_transferred)}) in {summary.elapsed_seconds:.2f}s ({summary.average_speed_mb_s:.2f} MB/s)."
                self.status_label.setText(msg)
                QMessageBox.information(self, "Copy Complete", msg)
            else:
                err_text = "\n".join(summary.errors[:5])
                self.status_label.setText("Completed with errors.")
                QMessageBox.warning(self, "Copy Finished with Errors", f"Errors:\n{err_text}")

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.start_btn.setEnabled(True))


# ===========================================================================
# 3. FORENSIC TIMESTAMP & ATTRIBUTE TOUCH PAGE
# ===========================================================================

class TimestampTouchPage(_Page):
    """Timestamptouchpage.

    Manages TimestampTouchPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Timestamp Touch page with file picker, datetime editors, and attribute checkboxes.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Forensic File Timestamp & Attribute Modifier", "Inspect, stomp, and synchronize MACB timestamps (Created, Modified, Accessed) and Win32 attribute flags."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.choose_file_btn = SecondaryButton("Select Files…", self.p)
        self.choose_file_btn.clicked.connect(self._on_choose_files)
        row.addWidget(self.choose_file_btn)
        self.files_label = QLabel("No files selected")
        self.files_label.setObjectName("Muted")
        row.addWidget(self.files_label)
        row.addStretch(1)
        cl.addLayout(row)

        # Datetime editors
        t_box = QGroupBox("Target Timestamps")
        tl = QVBoxLayout(t_box)

        c_row = QHBoxLayout()
        c_row.addWidget(QLabel("Created Time:"))
        self.created_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.created_edit.setCalendarPopup(True)
        c_row.addWidget(self.created_edit)
        self.set_created_check = QCheckBox("Apply Created Time")
        self.set_created_check.setChecked(True)
        c_row.addWidget(self.set_created_check)
        tl.addLayout(c_row)

        m_row = QHBoxLayout()
        m_row.addWidget(QLabel("Modified Time:"))
        self.modified_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.modified_edit.setCalendarPopup(True)
        m_row.addWidget(self.modified_edit)
        self.set_modified_check = QCheckBox("Apply Modified Time")
        self.set_modified_check.setChecked(True)
        m_row.addWidget(self.set_modified_check)
        tl.addLayout(m_row)

        a_row = QHBoxLayout()
        a_row.addWidget(QLabel("Accessed Time:"))
        self.accessed_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.accessed_edit.setCalendarPopup(True)
        a_row.addWidget(self.accessed_edit)
        self.set_accessed_check = QCheckBox("Apply Accessed Time")
        self.set_accessed_check.setChecked(True)
        a_row.addWidget(self.set_accessed_check)
        tl.addLayout(a_row)

        cl.addWidget(t_box)

        # Attribute checkboxes
        a_box = QGroupBox("Win32 File Attributes")
        al = QHBoxLayout(a_box)
        self.readonly_check = QCheckBox("Read-Only")
        self.hidden_check = QCheckBox("Hidden")
        self.system_check = QCheckBox("System")
        self.archive_check = QCheckBox("Archive")
        al.addWidget(self.readonly_check)
        al.addWidget(self.hidden_check)
        al.addWidget(self.system_check)
        al.addWidget(self.archive_check)
        al.addStretch(1)
        cl.addWidget(a_box)

        btn_row = QHBoxLayout()
        self.apply_btn = PrimaryButton("Apply Timestamp & Attribute Updates", self.p)
        self.apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(self.apply_btn)
        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._selected_files: List[Path] = []

    def _on_choose_files(self):
        """Pick files and preload the first file's timestamps and attributes into the editors.

        Manages on choose files operations and coordinates related state changes for the component.
        """
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Touch")
        if files:
            self._selected_files = [Path(f) for f in files]
            self.files_label.setText(f"{len(self._selected_files)} files selected")
            # Load metadata from first file to populate UI
            meta = TimestampTouchEngine.get_file_metadata(self._selected_files[0])
            if meta:
                self.created_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(meta.created_time)))
                self.modified_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(meta.modified_time)))
                self.accessed_edit.setDateTime(QDateTime.fromSecsSinceEpoch(int(meta.accessed_time)))
                self.readonly_check.setChecked(meta.is_readonly)
                self.hidden_check.setChecked(meta.is_hidden)
                self.system_check.setChecked(meta.is_system)
                self.archive_check.setChecked(meta.is_archive)

    def _on_apply(self):
        """Apply the chosen timestamps and attributes to every selected file.

        Manages on apply operations and coordinates related state changes for the component.
        """
        if not self._selected_files:
            QMessageBox.information(self, "Timestamp Touch", "Please select files first.")
            return

        c_ts = self.created_edit.dateTime().toSecsSinceEpoch() if self.set_created_check.isChecked() else None
        m_ts = self.modified_edit.dateTime().toSecsSinceEpoch() if self.set_modified_check.isChecked() else None
        a_ts = self.accessed_edit.dateTime().toSecsSinceEpoch() if self.set_accessed_check.isChecked() else None

        ro = self.readonly_check.isChecked()
        hid = self.hidden_check.isChecked()
        sys = self.system_check.isChecked()
        arch = self.archive_check.isChecked()

        for f in self._selected_files:
            TimestampTouchEngine.set_timestamps(f, c_ts, m_ts, a_ts)
            TimestampTouchEngine.set_attributes(f, readonly=ro, hidden=hid, system=sys, archive=arch)

        QMessageBox.information(self, "Success", f"Updated timestamps and attributes on {len(self._selected_files)} file(s).")


# ===========================================================================
# 4. ARCHIVE STUDIO PAGE
# ===========================================================================

class ArchiveManagerPage(_Page):
    """Archivemanagerpage.

    Manages ArchiveManagerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Archive Studio page with open/test/extract/create buttons and a contents table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Multi-Format Archive Studio", "Create, inspect, extract, and test ZIP, TAR, GZ, BZ2, and XZ archives with compression presets."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        # Top row: actions
        row = QHBoxLayout()
        self.open_arc_btn = SecondaryButton("Open Archive…", self.p)
        self.open_arc_btn.clicked.connect(self._on_open_archive)
        row.addWidget(self.open_arc_btn)

        self.test_btn = SecondaryButton("Test Integrity", self.p)
        self.test_btn.clicked.connect(self._on_test_archive)
        row.addWidget(self.test_btn)

        self.extract_btn = PrimaryButton("Extract All…", self.p)
        self.extract_btn.clicked.connect(self._on_extract_archive)
        row.addWidget(self.extract_btn)

        row.addStretch(1)
        self.create_btn = SecondaryButton("+ Create New Archive…", self.p)
        self.create_btn.clicked.connect(self._on_create_archive)
        row.addWidget(self.create_btn)
        cl.addLayout(row)

        self.archive_info_label = QLabel("Archive: None opened")
        self.archive_info_label.setObjectName("Muted")
        cl.addWidget(self.archive_info_label)

        # Archive contents table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Filename", "Original Size", "Compressed Size", "CRC32 / Checksum"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(300)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._current_archive: Optional[Path] = None

    def _on_open_archive(self):
        """Open an archive and list its entries in the table.

        Manages on open archive operations and coordinates related state changes for the component.
        """
        f, _ = QFileDialog.getOpenFileName(self, "Open Archive", "", "Archives (*.zip *.tar *.tar.gz *.tgz *.tar.bz2 *.tbz2 *.tar.xz)")
        if f:
            self._current_archive = Path(f)
            self.archive_info_label.setText(f"Archive: {self._current_archive.name} ({_fmt_bytes(self._current_archive.stat().st_size)})")
            entries = ArchiveManager.list_entries(self._current_archive)
            self.table.setRowCount(len(entries))
            for r, e in enumerate(entries):
                self.table.setItem(r, 0, QTableWidgetItem(e.filename))
                self.table.setItem(r, 1, QTableWidgetItem(_fmt_bytes(e.uncompressed_size)))
                self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(e.compressed_size)))
                self.table.setItem(r, 3, QTableWidgetItem(e.crc or "-"))

    def _on_test_archive(self):
        """Run an integrity test on the currently opened archive.

        Manages on test archive operations and coordinates related state changes for the component.
        """
        if not self._current_archive:
            QMessageBox.information(self, "Archive Studio", "Please open an archive first.")
            return

        ok, msg = ArchiveManager.test_archive(self._current_archive)
        if ok:
            QMessageBox.information(self, "Archive Integrity Test", f"✓ {msg}")
        else:
            QMessageBox.warning(self, "Archive Integrity Test", f"✗ {msg}")

    def _on_extract_archive(self):
        """Extract the opened archive into a chosen destination folder.

        Manages on extract archive operations and coordinates related state changes for the component.
        """
        if not self._current_archive:
            QMessageBox.information(self, "Archive Studio", "Please open an archive first.")
            return

        dest = QFileDialog.getExistingDirectory(self, "Select Extraction Destination")
        if dest:
            res = ArchiveManager.extract_archive(self._current_archive, dest)
            if res.success:
                QMessageBox.information(self, "Extracted", f"Successfully extracted {res.total_files} files ({_fmt_bytes(res.total_uncompressed_bytes)}) in {res.elapsed_seconds:.2f}s.")
            else:
                QMessageBox.warning(self, "Extraction Error", res.error or "Failed to extract archive.")

    def _on_create_archive(self):
        """Pick files and a target name, then build a new archive.

        Manages on create archive operations and coordinates related state changes for the component.
        """
        sources, _ = QFileDialog.getOpenFileNames(self, "Select Files to Compress")
        if not sources:
            return

        out, _ = QFileDialog.getSaveFileName(self, "Save Archive As", "archive.zip", "ZIP Archive (*.zip);;Gzipped Tarball (*.tar.gz);;Bzip2 Tarball (*.tar.bz2);;XZ Tarball (*.tar.xz)")
        if out:
            fmt = ArchiveManager.detect_format(out) or ArchiveFormat.ZIP
            res = ArchiveManager.create_archive(sources, out, fmt=fmt)
            if res.success:
                QMessageBox.information(self, "Archive Created", f"Created archive: {Path(out).name} ({_fmt_bytes(res.total_compressed_bytes)}).")
            else:
                QMessageBox.warning(self, "Archive Creation Error", res.error or "Failed to create archive.")


# ===========================================================================
# 5. PREFETCH & SYSMAIN ANALYZER PAGE
# ===========================================================================

class PrefetchAnalyzerPage(_Page):
    """Prefetchanalyzerpage.

    Manages PrefetchAnalyzerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Prefetch page with status line, scan/clean buttons, and a traces table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Windows Prefetch & SysMain Trace Analyzer", "Analyze execution traces, executable run counts, and purge orphaned prefetch caches."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        # Status row
        self.status_label = QLabel("Prefetch Status: Loading...")
        cl.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        self.scan_btn = PrimaryButton("Scan Prefetch Traces", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(self.scan_btn)

        self.clean_btn = SecondaryButton("Flush All Prefetch Traces", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        btn_row.addWidget(self.clean_btn)
        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Executable Name", "Hash Code", "File Size", "Last Run Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._refresh_status()

    def _refresh_status(self):
        """Refresh the prefetch cache size, SysMain state, and privilege line.

        Manages refresh status operations and coordinates related state changes for the component.
        """
        st = PrefetchAnalyzer.get_status()
        self.status_label.setText(
            f"Prefetch Cache: {st.total_files} traces ({_fmt_bytes(st.total_size_bytes)})  •  "
            f"SysMain Service: {st.sysmain_status}  •  "
            f"Privileges: {'Administrator' if st.is_admin else 'Standard User'}"
        )

    def _on_scan(self):
        """Scan prefetch trace files on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return PrefetchAnalyzer.scan_prefetch_files()

        def _done(entries: List[PrefetchEntry]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                entries (List[PrefetchEntry]): Collection of items or entries to process.
            """
            self.scan_btn.setEnabled(True)
            self.table.setRowCount(len(entries))
            for r, e in enumerate(entries):
                self.table.setItem(r, 0, QTableWidgetItem(e.executable_name))
                self.table.setItem(r, 1, QTableWidgetItem(e.hash_code))
                self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(e.size_bytes)))
                t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.modified_time))
                self.table.setItem(r, 3, QTableWidgetItem(t_str))
            self._refresh_status()

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.scan_btn.setEnabled(True))

    def _on_clean(self):
        """Confirm and flush all prefetch traces, then rescan.

        Manages on clean operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm Prefetch Purge",
            "Flush all Windows Prefetch execution trace files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = PrefetchAnalyzer.clean_prefetch()
            QMessageBox.information(self, "Prefetch Flushed", f"Deleted {res.files_deleted} traces, freed {_fmt_bytes(res.bytes_freed)}.")
            self._on_scan()


# ===========================================================================
# 6. SEARCH INDEX OPTIMIZER PAGE
# ===========================================================================

class SearchIndexOptimizerPage(_Page):
    """Searchindexoptimizerpage.

    Manages SearchIndexOptimizerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Search Index page with status card and compact/rebuild buttons.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Windows Search Index Database Optimizer", "Inspect, compact, and repair the Windows Search Catalog database (Windows.edb)."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        self.status_info = QLabel("Loading Search Index state...")
        self.status_info.setObjectName("Muted")
        cl.addWidget(self.status_info)

        btn_row = QHBoxLayout()
        self.refresh_btn = SecondaryButton("Refresh Metrics", self.p)
        self.refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self.refresh_btn)

        self.compact_btn = PrimaryButton("Compact Database (esentutl /d)", self.p)
        self.compact_btn.clicked.connect(self._on_compact)
        btn_row.addWidget(self.compact_btn)

        self.rebuild_btn = SecondaryButton("Rebuild Search Index", self.p)
        self.rebuild_btn.clicked.connect(self._on_rebuild)
        btn_row.addWidget(self.rebuild_btn)

        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._refresh()

    def _refresh(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        st = SearchIndexOptimizer.get_status()
        self.status_info.setText(
            f"Database Location: {st.database_path}\n"
            f"Database Size: {_fmt_bytes(st.database_size_bytes)} ({'Bloated' if st.is_bloated else 'Optimal'})\n"
            f"Estimated Indexed Items: {st.indexed_items_estimate:,}\n"
            f"Windows Search Service (WSearch): {st.service_status}\n"
            f"Admin Rights: {'Yes' if st.is_admin else 'No (Required for compaction)'}"
        )

    def _on_compact(self):
        """Confirm and run offline ESENT compaction in the background.

        Manages on compact operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm Compaction",
            "Stop Windows Search service and run offline ESENT database compaction?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.compact_btn.setEnabled(False)

            def _work():
                """Execute background processing off the main UI thread.

                Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
                """
                return SearchIndexOptimizer.compact_database()

            def _done(res):
                """Handle completion of the asynchronous task.

                Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

                Args:
                    res: The res parameter.
                """
                self.compact_btn.setEnabled(True)
                self._refresh()
                if res.success:
                    QMessageBox.information(self, "Compaction Complete", res.message)
                else:
                    QMessageBox.warning(self, "Compaction Warning", res.message)

            self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.compact_btn.setEnabled(True))

    def _on_rebuild(self):
        """Confirm and trigger a full search-index rebuild.

        Manages on rebuild operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Confirm Index Rebuild",
            "Reset and rebuild the entire Windows Search catalog? (Indexing will run in background)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = SearchIndexOptimizer.rebuild_index()
            QMessageBox.information(self, "Rebuild Triggered", res.message)
            self._refresh()


# ===========================================================================
# 7. DNS BENCHMARK PAGE
# ===========================================================================

class DnsBenchmarkPage(_Page):
    """Dnsbenchmarkpage.

    Manages DnsBenchmarkPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the DNS Benchmark page with run/apply buttons and a results table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("DNS Latency Benchmark & Resolver Selector", "Benchmark real round-trip DNS latency across top global and security providers."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.run_btn = PrimaryButton("Run DNS Benchmark", self.p)
        self.run_btn.clicked.connect(self._on_benchmark)
        row.addWidget(self.run_btn)

        self.apply_dns_btn = SecondaryButton("Apply Selected DNS to Adapter", self.p)
        self.apply_dns_btn.clicked.connect(self._on_apply_dns)
        row.addWidget(self.apply_dns_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Provider", "Name", "Primary IP", "Avg Latency", "Min / Max", "Category"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._results: List[DnsBenchmarkResult] = []

    def _on_benchmark(self):
        """Run the full DNS benchmark on the worker runtime.

        Manages on benchmark operations and coordinates related state changes for the component.
        """
        self.run_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return DnsBenchmarkEngine.run_full_benchmark()

        def _done(results: List[DnsBenchmarkResult]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                results (List[DnsBenchmarkResult]): Collection or dictionary holding operation results.
            """
            self.run_btn.setEnabled(True)
            self._results = results
            self.table.setRowCount(len(results))
            for r, res in enumerate(results):
                self.table.setItem(r, 0, QTableWidgetItem(res.server.provider))
                name_str = f"★ {res.server.name} (Fastest)" if res.is_fastest else res.server.name
                name_item = QTableWidgetItem(name_str)
                if res.is_fastest:
                    name_item.setForeground(Qt.GlobalColor.green)
                self.table.setItem(r, 1, name_item)
                self.table.setItem(r, 2, QTableWidgetItem(res.server.primary_ip))
                self.table.setItem(r, 3, QTableWidgetItem(f"{res.avg_ms} ms" if res.is_reachable else "Timeout"))
                self.table.setItem(r, 4, QTableWidgetItem(f"{res.min_ms} / {res.max_ms} ms" if res.is_reachable else "-"))
                self.table.setItem(r, 5, QTableWidgetItem(res.server.category))

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.run_btn.setEnabled(True))

    def _on_apply_dns(self):
        """Apply the selected provider's DNS servers to Wi-Fi, falling back to Ethernet.

        Manages on apply dns operations and coordinates related state changes for the component.
        """
        sel = self.table.currentRow()
        if sel < 0 or sel >= len(self._results):
            QMessageBox.information(self, "DNS Selector", "Please select a DNS provider from the benchmark table.")
            return

        res = self._results[sel]
        ok, msg = DnsBenchmarkEngine.apply_dns_servers("Wi-Fi", res.server.primary_ip, res.server.secondary_ip)
        if not ok:
            # Try Ethernet
            ok, msg = DnsBenchmarkEngine.apply_dns_servers("Ethernet", res.server.primary_ip, res.server.secondary_ip)

        if ok:
            QMessageBox.information(self, "DNS Applied", f"Successfully set DNS to {res.server.name} ({res.server.primary_ip}).")
        else:
            QMessageBox.warning(self, "DNS Configuration", f"Failed to apply DNS: {msg}")


# ===========================================================================
# 8. DISK BENCHMARK PAGE
# ===========================================================================

class DiskBenchmarkPage(_Page):
    """Diskbenchmarkpage.

    Manages DiskBenchmarkPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Disk Benchmark page with target picker, progress label, and results table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Storage Throughput & IOPS Benchmark", "Measure Sequential Read/Write and Random 4KB IOPS performance across storage drives."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(14)

        row = QHBoxLayout()
        row.addWidget(QLabel("Target Directory:"))
        self.target_btn = SecondaryButton("Select Drive / Folder…", self.p)
        self.target_btn.clicked.connect(self._on_select_target)
        row.addWidget(self.target_btn)

        self.target_label = QLabel("Target: System Temp")
        self.target_label.setObjectName("Muted")
        row.addWidget(self.target_label)

        row.addStretch(1)
        self.start_btn = PrimaryButton("Start Benchmark", self.p)
        self.start_btn.clicked.connect(self._on_start_bench)
        row.addWidget(self.start_btn)
        cl.addLayout(row)

        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("Muted")
        cl.addWidget(self.progress_label)

        # Results table
        self.table = QTableWidget(4, 3)
        self.table.setHorizontalHeaderLabels(["Test Profile", "Throughput (MB/s)", "IOPS / Latency"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        test_names = ["Sequential Read (1MB)", "Sequential Write (1MB)", "Random Read (4KB)", "Random Write (4KB)"]
        for r, name in enumerate(test_names):
            self.table.setItem(r, 0, QTableWidgetItem(name))
            self.table.setItem(r, 1, QTableWidgetItem("-"))
            self.table.setItem(r, 2, QTableWidgetItem("-"))
        self.table.setMaximumHeight(200)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._target_path = Path.home()

    def _on_select_target(self):
        """Pick the drive or folder to benchmark.

        Manages on select target operations and coordinates related state changes for the component.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Benchmark Target Drive")
        if folder:
            self._target_path = Path(folder)
            self.target_label.setText(f"Target: {self._target_path}")

    def _on_start_bench(self):
        """Run a 64 MB storage benchmark on the target in the background.

        Manages on start bench operations and coordinates related state changes for the component.
        """
        self.start_btn.setEnabled(False)
        self.progress_label.setText("Running storage benchmark (64MB sample)...")

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return DiskBenchmarkEngine.run_benchmark(self._target_path, file_size_mb=64)

        def _done(report: DiskBenchmarkReport):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                report (DiskBenchmarkReport): The generated report data object from the backend.
            """
            self.start_btn.setEnabled(True)
            self.progress_label.setText(f"Completed in {report.elapsed_seconds}s on {report.target_drive}")

            # Populate table
            metrics = [report.sequential_read, report.sequential_write, report.random_read_4k, report.random_write_4k]
            for r, m in enumerate(metrics):
                self.table.setItem(r, 1, QTableWidgetItem(f"{m.speed_mb_s:.2f} MB/s"))
                self.table.setItem(r, 2, QTableWidgetItem(f"{m.iops:.1f} IOPS ({m.avg_latency_ms:.3f} ms)"))

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.start_btn.setEnabled(True))


# ===========================================================================
# 9. RAM & WORKING SET OPTIMIZER PAGE
# ===========================================================================

class MemoryOptimizerPage(_Page):
    """Memoryoptimizerpage.

    Manages MemoryOptimizerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the RAM Optimizer page with summary line, process table, and trim button.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("RAM & Working Set Optimizer", "Inspect physical RAM composition and safely trim background process working sets."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        self.ram_summary = QLabel("Loading RAM metrics...")
        cl.addWidget(self.ram_summary)

        btn_row = QHBoxLayout()
        self.refresh_btn = SecondaryButton("Refresh Processes", self.p)
        self.refresh_btn.clicked.connect(self._on_refresh)
        btn_row.addWidget(self.refresh_btn)

        self.trim_btn = PrimaryButton("Optimize Working Sets", self.p)
        self.trim_btn.clicked.connect(self._on_trim)
        btn_row.addWidget(self.trim_btn)
        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["PID", "Process Name", "Working Set (RAM)", "Private Bytes"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._on_refresh()

    def _on_refresh(self):
        """Refresh the RAM summary and top-30 process memory table.

        Manages on refresh operations and coordinates related state changes for the component.
        """
        m = MemoryOptimizer.get_system_ram_metrics()
        self.ram_summary.setText(
            f"Physical RAM: {_fmt_bytes(m.used_bytes)} / {_fmt_bytes(m.total_bytes)} ({m.percent_used:.1f}% used)  •  "
            f"Available: {_fmt_bytes(m.available_bytes)}  •  "
            f"Commit: {_fmt_bytes(m.commit_total_bytes)}"
        )

        procs = MemoryOptimizer.scan_process_memory(limit=30)
        self.table.setRowCount(len(procs))
        for r, p in enumerate(procs):
            self.table.setItem(r, 0, QTableWidgetItem(str(p.pid)))
            self.table.setItem(r, 1, QTableWidgetItem(p.name))
            self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(p.working_set_bytes)))
            self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(p.private_bytes)))

    def _on_trim(self):
        """Trim background process working sets, then refresh.

        Manages on trim operations and coordinates related state changes for the component.
        """
        res = MemoryOptimizer.optimize_all_background_working_sets()
        QMessageBox.information(self, "Memory Optimized", f"Trimmed working sets of {res.processes_trimmed} background processes.")
        self._on_refresh()


# ===========================================================================
# 10. DEVELOPER ARTIFACTS CLEANER PAGE
# ===========================================================================

class DevCleanerPage(_Page):
    """Devcleanerpage.

    Manages DevCleanerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Dev Cleaner page with scan/clean buttons and a caches table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Developer Build Artifacts & Cache Purger", "Scan and clean Docker, Python, Node.js, Rust/Cargo, Gradle, Go, and .NET NuGet caches."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        btn_row = QHBoxLayout()
        self.scan_btn = PrimaryButton("Scan Dev Caches", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(self.scan_btn)

        self.clean_btn = SecondaryButton("Clean Selected Caches", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        btn_row.addWidget(self.clean_btn)
        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Ecosystem", "Cache Name", "Size", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._items: List[DevCacheItem] = []

    def _on_scan(self):
        """Scan developer caches on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return DevCleaner.scan_dev_caches()

        def _done(items: List[DevCacheItem]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                items (List[DevCacheItem]): Collection of items or entries to process.
            """
            self.scan_btn.setEnabled(True)
            self._items = items
            self.table.setRowCount(len(items))
            for r, it in enumerate(items):
                self.table.setItem(r, 0, QTableWidgetItem(it.ecosystem))
                self.table.setItem(r, 1, QTableWidgetItem(it.name))
                self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(it.size_bytes)))
                self.table.setItem(r, 3, QTableWidgetItem(it.description))

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.scan_btn.setEnabled(True))

    def _on_clean(self):
        """Confirm and purge all discovered caches, then rescan.

        Manages on clean operations and coordinates related state changes for the component.
        """
        if not self._items:
            QMessageBox.information(self, "Dev Cleaner", "Please scan for developer caches first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Clean",
            f"Purge all {len(self._items)} developer build and package caches?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = DevCleaner.clean_items(self._items)
            QMessageBox.information(self, "Clean Complete", f"Cleaned {res.items_cleaned} cache stores, freed {_fmt_bytes(res.bytes_freed)}.")
            self._on_scan()


# ===========================================================================
# 11. BROWSER DEEP CLEANER PAGE
# ===========================================================================

class BrowserDeepCleanerPage(_Page):
    """Browserdeepcleanerpage.

    Manages BrowserDeepCleanerPage operations and coordinates related state changes for the component.
    """
    def __init__(self, win: PremiumMainWindow):
        """Build the Browser Cleaner page with scan/clean buttons and a targets table.

        Initializes the instance and configures internal state.

        Args:
            win (PremiumMainWindow): Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.addWidget(title_block("Multi-Browser Deep Privacy & Cache Sanitizer", "Forensic cache and storage cleaner across Chrome, Edge, Firefox, Brave, Opera, Vivaldi, and Arc."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        btn_row = QHBoxLayout()
        self.scan_btn = PrimaryButton("Scan Browser Caches", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(self.scan_btn)

        self.clean_btn = SecondaryButton("Clean Browser Caches", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        btn_row.addWidget(self.clean_btn)

        self.vacuum_btn = SecondaryButton("Vacuum Databases", self.p)
        self.vacuum_btn.setToolTip("Defragments and compacts browser SQLite databases (History, Cookies, Places) to improve launch speed and reclaim space.")
        self.vacuum_btn.clicked.connect(self._on_vacuum)
        btn_row.addWidget(self.vacuum_btn)
        btn_row.addStretch(1)
        cl.addLayout(btn_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Browser", "Category", "Cache Size", "Path"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)

        self._targets: List[BrowserTarget] = []

    def _on_scan(self):
        """Scan browser caches on the worker runtime.

        Manages on scan operations and coordinates related state changes for the component.
        """
        self.scan_btn.setEnabled(False)
        self.table.setRowCount(0)

        def _work():
            """Execute background processing off the main UI thread.

            Performs the intensive analysis, scanning, or file operations in a worker thread to keep the interface responsive.
            """
            return BrowserDeepCleaner.scan_browser_caches()

        def _done(targets: List[BrowserTarget]):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                targets (List[BrowserTarget]): The targets parameter.
            """
            self.scan_btn.setEnabled(True)
            self._targets = targets
            self.table.setRowCount(len(targets))
            for r, t in enumerate(targets):
                self.table.setItem(r, 0, QTableWidgetItem(t.browser_name))
                self.table.setItem(r, 1, QTableWidgetItem(t.category))
                self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(t.size_bytes)))
                self.table.setItem(r, 3, QTableWidgetItem(t.path))

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.scan_btn.setEnabled(True))

    def _on_clean(self):
        """Confirm and purge transient browser caches (logins preserved), then rescan.

        Manages on clean operations and coordinates related state changes for the component.
        """
        if not self._targets:
            QMessageBox.information(self, "Browser Cleaner", "Please scan for browser caches first.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Clean",
            "Purge transient browser caches? (Logins and cookies are preserved)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            res = BrowserDeepCleaner.clean_targets(self._targets)
            QMessageBox.information(self, "Browsers Cleaned", f"Cleaned {res.browsers_cleaned} browser profiles ({res.files_deleted} files), freed {_fmt_bytes(res.bytes_freed)}.")
            self._on_scan()

    def _on_vacuum(self):
        """Find and VACUUM browser SQLite databases to compact and reclaim space.

        Manages on vacuum operations and coordinates related state changes for the component.
        """
        confirm = QMessageBox.question(
            self, "Vacuum Databases",
            "Defragment and optimize browser SQLite databases (History, Cookies, Places)?\n\n"
            "Please make sure your web browsers are closed before running this operation.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.vacuum_btn.setEnabled(False)

        def _work():
            """Execute SQLite database vacuum and defragmentation in the background.

            Scans browser profiles for candidate SQLite databases and runs VACUUM
            commands to compact disk pages and rebuild indexes.

            Returns:
                tuple: Count of databases vacuumed and total bytes reclaimed.
            """
            from pathlib import Path
            from cortex_unified.system_tools.browser_cleaner import DeepBrowserCleaner
            cleaner = DeepBrowserCleaner()
            items = cleaner.scan()
            dbs = [item.path for item in items if getattr(item, "can_vacuum", False) and item.path.is_file()]
            # Also discover common SQLite DB files in browser profiles
            res = cleaner.vacuum_databases(dbs)
            total_saved = sum(res.values())
            return len(res), total_saved

        def _done(result):
            """Handle completion of the asynchronous task.

            Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.

            Args:
                result: Collection or dictionary holding operation results.
            """
            count, saved = result
            self.vacuum_btn.setEnabled(True)
            QMessageBox.information(
                self, "Databases Vacuumed",
                f"Optimized {count} browser database file(s), compacted and reclaimed {_fmt_bytes(saved)}.",
            )

        self.win.worker_runtime.run(_work, on_result=_done, on_error=lambda err: self.vacuum_btn.setEnabled(True))

