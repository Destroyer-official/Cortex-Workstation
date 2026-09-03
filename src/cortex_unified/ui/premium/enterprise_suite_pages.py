"""Cortex Cleaner & NexusExplorer — Enterprise Next-Gen Suite GUI Pages.

Contains 10 interactive, theme-aware GUI pages:
1. VssManagerPage (Volume Shadow Copy & Snapshot Manager)
2. DevDriveOptimizerPage (ReFS Dev Drive & Block-Cloning Optimizer)
3. BitLockerAuditorPage (BitLocker & Drive Encryption Auditor)
4. JunctionAuditorPage (NTFS Hard Link, Junction & Reparse Point Auditor)
5. BitRotScrubberPage (Silent BitRot & File Integrity Scrubber)
6. MemoryCompressionPage (Windows Memory Compression & SysMain Optimizer)
7. SandboxCleanerPage (Virtual Environment & Sandbox Artifact Purger)
8. SmbShareAuditorPage (Network Share & SMB Exposure Auditor)
9. ProcessTokenPage (Process Security Token & Integrity Forensics)
10. StorageGrowthTrackerPage (Storage Growth Tracker & Timeline Differ)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .tokens import Spacing
from .widgets import Card, hline, title_block
from .window import PremiumMainWindow, _Page

from cortex_unified.system_tools.vss_manager import VssManager, VssAuditReport
from cortex_unified.system_tools.dev_drive_optimizer import DevDriveOptimizer, DevDriveAuditReport
from cortex_unified.system_tools.bitlocker_auditor import BitLockerAuditor, BitLockerAuditReport
from cortex_unified.system_tools.junction_auditor import JunctionAuditor, JunctionAuditReport
from cortex_unified.system_tools.bitrot_scrubber import BitRotScrubber, BitRotScrubReport
from cortex_unified.system_tools.memory_compression_tuner import MemoryCompressionTuner, MemoryTunerReport
from cortex_unified.system_tools.sandbox_cleaner import SandboxCleaner, SandboxCleanReport
from cortex_unified.system_tools.smb_share_auditor import SmbShareAuditor, SmbSecurityReport
from cortex_unified.system_tools.process_token_auditor import ProcessTokenAuditor, ProcessTokenAuditReport
from cortex_unified.system_tools.storage_growth_tracker import StorageGrowthTracker, SnapshotSummary, StorageGrowthDiffReport


def _fmt_bytes(b: int) -> str:
    """Format a byte count into a human-readable B/KB/MB/GB string."""
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    return f"{b / (1024 * 1024 * 1024):.2f} GB"


def _PrimaryButton(text: str, parent=None) -> QPushButton:
    """Create a QPushButton styled as the primary (accented) action button."""
    btn = QPushButton(text, parent if isinstance(parent, QWidget) else None)
    btn.setObjectName("Primary")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _SecondaryButton(text: str, parent=None) -> QPushButton:
    """Create a QPushButton styled as a secondary action button with a pointing-hand cursor."""
    btn = QPushButton(text, parent if isinstance(parent, QWidget) else None)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _run_task(win: PremiumMainWindow, work_fn, done_fn, err_fn=None):
    """Run work_fn on the window's worker runtime, or inline as a fallback, dispatching to done_fn / err_fn."""
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
# 1. VOLUME SHADOW COPY (VSS) MANAGER PAGE
# ===========================================================================

class VssManagerPage(_Page):
    """Page for auditing VSS shadow copies, creating snapshots, and purging the oldest shadow."""
    def __init__(self, win: PremiumMainWindow):
        """Build the VSS page with audit/create/purge buttons, summary label, and shadows table."""
        super().__init__(win)
        self.v.addWidget(title_block("Volume Shadow Copy (VSS) Manager", "Audit VSS snapshots, monitor shadow storage usage, create recovery snapshots, and reclaim space."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Audit VSS Shadows", self.p)
        self.scan_btn.clicked.connect(self._on_audit)
        row.addWidget(self.scan_btn)

        self.create_btn = _SecondaryButton("Create Snapshot on C:", self.p)
        self.create_btn.clicked.connect(self._on_create)
        row.addWidget(self.create_btn)

        self.purge_btn = _SecondaryButton("Purge Oldest Shadow", self.p)
        self.purge_btn.clicked.connect(self._on_purge)
        row.addWidget(self.purge_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Audit VSS Shadows to discover active snapshots.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Shadow ID", "Original Volume", "Creation Time", "Provider"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._mgr = VssManager()

    def _on_audit(self):
        """Start an asynchronous VSS audit and show a busy message in the summary label."""
        self.summary_label.setText("Querying vssadmin and WMI shadow copies…")
        _run_task(self.win, self._mgr.audit, self._on_audit_done, self._on_err)

    def _on_audit_done(self, rep: VssAuditReport):
        """Populate the shadows table and summary from a VssAuditReport."""
        if rep.error:
            self.summary_label.setText(f"VSS Audit Error: {rep.error}")
            return

        self.summary_label.setText(
            f"Active Snapshots: {len(rep.shadows)} | Total Shadow Storage Used: {_fmt_bytes(rep.total_used_bytes)} | Allocated: {_fmt_bytes(rep.total_allocated_bytes)}"
        )
        self.table.setRowCount(len(rep.shadows))
        for r, s in enumerate(rep.shadows):
            self.table.setItem(r, 0, QTableWidgetItem(s.shadow_id))
            self.table.setItem(r, 1, QTableWidgetItem(s.original_volume))
            self.table.setItem(r, 2, QTableWidgetItem(s.creation_time))
            self.table.setItem(r, 3, QTableWidgetItem(s.provider))

    def _on_create(self):
        """Kick off creation of a recovery shadow copy on C: in the background."""
        self.summary_label.setText("Creating recovery snapshot on C:…")
        _run_task(self.win, lambda: self._mgr.create_shadow_copy("C:"), self._on_action_done, self._on_err)

    def _on_purge(self):
        """Kick off deletion of the oldest shadow copy on C: in the background."""
        self.summary_label.setText("Purging oldest shadow on C:…")
        _run_task(self.win, lambda: self._mgr.delete_oldest_shadow("C:"), self._on_action_done, self._on_err)

    def _on_action_done(self, res: tuple[bool, str]):
        """Show the result message of a create/purge action, then refresh the audit."""
        ok, msg = res
        self.summary_label.setText(msg)
        self._on_audit()

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 2. REFS DEV DRIVE & BLOCK-CLONING OPTIMIZER PAGE
# ===========================================================================

class DevDriveOptimizerPage(_Page):
    """Page for auditing ReFS Dev Drives, block-cloning support, and Defender performance mode."""
    def __init__(self, win: PremiumMainWindow):
        """Build the Dev Drive page with an audit button, summary label, and drives table."""
        super().__init__(win)
        self.v.addWidget(title_block("ReFS Dev Drive & Block-Cloning Optimizer", "Detect ReFS Dev Drives, test Copy-on-Write block cloning, and inspect Defender Performance Mode."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Audit Storage Drives", self.p)
        self.scan_btn.clicked.connect(self._on_audit)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Audit Storage Drives to inspect ReFS and Dev Drive configurations.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Drive", "File System", "Dev Drive", "Block Cloning (CoW)", "Defender Async Mode", "Free Space"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._opt = DevDriveOptimizer()

    def _on_audit(self):
        """Start an asynchronous storage-drive audit and update the summary label."""
        self.summary_label.setText("Querying volume geometry and fsutil devdrv status…")
        _run_task(self.win, self._opt.audit, self._on_audit_done, self._on_err)

    def _on_audit_done(self, rep: DevDriveAuditReport):
        """Fill the drives table and summary from a DevDriveAuditReport."""
        if rep.error:
            self.summary_label.setText(f"Audit Error: {rep.error}")
            return

        recom = f" | Recommendation: {rep.recommendations[0]}" if rep.recommendations else ""
        self.summary_label.setText(
            f"Checked {len(rep.drives)} Drives | Has Dev Drive: {'Yes' if rep.has_dev_drives else 'No'}{recom}"
        )
        self.table.setRowCount(len(rep.drives))
        for r, d in enumerate(rep.drives):
            self.table.setItem(r, 0, QTableWidgetItem(d.drive_letter))
            self.table.setItem(r, 1, QTableWidgetItem(d.filesystem))
            self.table.setItem(r, 2, QTableWidgetItem("Yes" if d.is_dev_drive else "No"))
            self.table.setItem(r, 3, QTableWidgetItem("Supported (Instant CoW)" if d.supports_block_cloning else "Standard Copy"))
            self.table.setItem(r, 4, QTableWidgetItem("Active" if d.defender_perf_mode else "Standard Filter"))
            self.table.setItem(r, 5, QTableWidgetItem(f"{_fmt_bytes(d.free_space_bytes)} / {_fmt_bytes(d.total_space_bytes)}"))

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 3. BITLOCKER & DRIVE ENCRYPTION AUDITOR PAGE
# ===========================================================================

class BitLockerAuditorPage(_Page):
    """Page for auditing volume BitLocker protection, cipher strength, and key protectors."""
    def __init__(self, win: PremiumMainWindow):
        """Build the BitLocker page with an audit button, summary label, and volumes table."""
        super().__init__(win)
        self.v.addWidget(title_block("BitLocker & Drive Encryption Auditor", "Audit volume encryption protection, cipher strength (XTS-AES), and active TPM key protectors."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Audit BitLocker Status", self.p)
        self.scan_btn.clicked.connect(self._on_audit)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Audit BitLocker Status to check data-at-rest encryption.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Volume", "Protection", "Encrypted %", "Cipher Method", "Lock State", "Key Protectors"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._aud = BitLockerAuditor()

    def _on_audit(self):
        """Start an asynchronous BitLocker audit and update the summary label."""
        self.summary_label.setText("Querying manage-bde and Win32_EncryptableVolume…")
        _run_task(self.win, self._aud.audit, self._on_audit_done, self._on_err)

    def _on_audit_done(self, rep: BitLockerAuditReport):
        """Fill the volumes table and compliance summary from a BitLockerAuditReport."""
        if rep.error:
            self.summary_label.setText(f"Audit Error: {rep.error}")
            return

        self.summary_label.setText(
            f"Compliance: {rep.overall_compliance} | Protected: {rep.fully_protected_count} | Unprotected: {rep.unprotected_count}"
        )
        self.table.setRowCount(len(rep.volumes))
        for r, v in enumerate(rep.volumes):
            self.table.setItem(r, 0, QTableWidgetItem(f"{v.drive_letter} {v.volume_name}"))
            self.table.setItem(r, 1, QTableWidgetItem(v.protection_status))
            self.table.setItem(r, 2, QTableWidgetItem(f"{v.percent_encrypted:.1f}%"))
            self.table.setItem(r, 3, QTableWidgetItem(v.encryption_method))
            self.table.setItem(r, 4, QTableWidgetItem(v.lock_status))
            self.table.setItem(r, 5, QTableWidgetItem(", ".join(v.key_protectors) or "None"))

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 4. NTFS JUNCTION & REPARSE POINT AUDITOR PAGE
# ===========================================================================

class JunctionAuditorPage(_Page):
    """Page for scanning NTFS junctions, symlinks, dead links, and circular reparse traps."""
    def __init__(self, win: PremiumMainWindow):
        """Build the Junction Auditor page with scan/custom/unlink buttons and a links table."""
        super().__init__(win)
        self.v.addWidget(title_block("NTFS Junction & Reparse Point Auditor", "Identify directory junctions, symbolic links, broken dead links, and circular recursion traps."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan User Profile Links", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.custom_btn = _SecondaryButton("Scan Custom Folder…", self.p)
        self.custom_btn.clicked.connect(self._on_custom)
        row.addWidget(self.custom_btn)

        self.clean_dead_btn = _SecondaryButton("Unlink Selected Dead Junction", self.p)
        self.clean_dead_btn.clicked.connect(self._on_clean_dead)
        row.addWidget(self.clean_dead_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Scan User Profile Links to begin reparse point discovery.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Link Path", "Type", "Target Destination", "Status", "Circular Loop"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._aud = JunctionAuditor()

    def _on_scan(self):
        """Scan reparse points across the user profile in the background."""
        self.summary_label.setText("Scanning reparse points across user profile…")
        _run_task(self.win, lambda: self._aud.audit(), self._on_scan_done, self._on_err)

    def _on_custom(self):
        """Prompt for a folder and scan its reparse points in the background."""
        d = QFileDialog.getExistingDirectory(self.p, "Select Folder to Audit Junctions")
        if d:
            self.summary_label.setText(f"Scanning reparse points in {d}…")
            _run_task(self.win, lambda: self._aud.audit(d), self._on_scan_done, self._on_err)

    def _on_scan_done(self, rep: JunctionAuditReport):
        """Fill the links table and counters from a JunctionAuditReport."""
        if rep.error:
            self.summary_label.setText(f"Scan Error: {rep.error}")
            return

        self.summary_label.setText(
            f"Reparse Points: {rep.total_reparse_points} | Junctions: {rep.junction_count} | Symlinks: {rep.symlink_count} | Dead Links: {rep.dead_links_count} | Circular Loops: {rep.circular_loops_count}"
        )
        self.table.setRowCount(len(rep.items))
        for r, item in enumerate(rep.items):
            self.table.setItem(r, 0, QTableWidgetItem(item.path))
            self.table.setItem(r, 1, QTableWidgetItem(item.link_type))
            self.table.setItem(r, 2, QTableWidgetItem(item.target))
            status_str = "Dead (Target Missing)" if item.is_dead else "Valid"
            self.table.setItem(r, 3, QTableWidgetItem(status_str))
            self.table.setItem(r, 4, QTableWidgetItem("YES (Recursive Trap)" if item.is_circular else "No"))

    def _on_clean_dead(self):
        """Unlink the dead junction selected in the table, then rescan."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self.p, "No Selection", "Please select a dead link row to unlink.")
            return
        path = self.table.item(row, 0).text()
        ok, msg = self._aud.remove_dead_junction(path)
        QMessageBox.information(self.p, "Unlink Result", msg)
        self._on_scan()

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 5. SILENT BITROT & FILE INTEGRITY SCRUBBER PAGE
# ===========================================================================

class BitRotScrubberPage(_Page):
    """Page for detecting silent bit-rot by comparing files against a SHA-256 baseline."""
    def __init__(self, win: PremiumMainWindow):
        """Build the BitRot page with a target picker, scrub button, and corrupted-files table."""
        super().__init__(win)
        self.v.addWidget(title_block("Silent BitRot & File Integrity Scrubber", "Detect bit-level silent data corruption and hash mutations across documents, photos, and archives."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.target_edit = QLineEdit(str(Path.home() / "Documents"))
        row.addWidget(self.target_edit, 1)

        self.browse_btn = _SecondaryButton("Browse…", self.p)
        self.browse_btn.clicked.connect(self._on_browse)
        row.addWidget(self.browse_btn)

        self.scrub_btn = _PrimaryButton("Run Integrity Scrub", self.p)
        self.scrub_btn.clicked.connect(self._on_scrub)
        row.addWidget(self.scrub_btn)
        cl.addLayout(row)

        self.summary_label = QLabel("Select a folder to scrub against cryptographic SHA-256 baseline.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Corrupted File Path", "Expected Baseline Hash", "Actual Mutated Hash", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._scrubber = BitRotScrubber()

    def _on_browse(self):
        """Open a directory picker and set it as the scrub target."""
        d = QFileDialog.getExistingDirectory(self.p, "Select Folder to Scrub", self.target_edit.text())
        if d:
            self.target_edit.setText(d)

    def _on_scrub(self):
        """Hash and scrub the chosen folder in the background."""
        d = self.target_edit.text().strip()
        if not d:
            return
        self.summary_label.setText(f"Calculating SHA-256 integrity baseline and scrubbing {d}…")
        _run_task(self.win, lambda: self._scrubber.scrub(d), self._on_scrub_done, self._on_err)

    def _on_scrub_done(self, rep: BitRotScrubReport):
        """Show scrub statistics and list corrupted files from a BitRotScrubReport."""
        if rep.error:
            self.summary_label.setText(f"Scrub Error: {rep.error}")
            return

        self.summary_label.setText(
            f"Files Scanned: {rep.total_files_scanned} | Clean & Verified: {rep.clean_files_count} | Bitrot Corrupted: {rep.corrupted_count} | New Indexed: {rep.new_files_indexed} (Scrubbed in {rep.duration_seconds:.2f}s)"
        )
        self.table.setRowCount(len(rep.corrupted_items))
        for r, item in enumerate(rep.corrupted_items):
            self.table.setItem(r, 0, QTableWidgetItem(item.path))
            self.table.setItem(r, 1, QTableWidgetItem(item.expected_hash[:16] + "…"))
            self.table.setItem(r, 2, QTableWidgetItem(item.actual_hash[:16] + "…"))
            self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(item.size)))

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 6. MEMORY COMPRESSION & SYSMAIN OPTIMIZER PAGE
# ===========================================================================

class MemoryCompressionPage(_Page):
    """Page for auditing Windows memory compression and toggling it on or off."""
    def __init__(self, win: PremiumMainWindow):
        """Build the Memory Compression page with audit/toggle buttons and a metrics table."""
        super().__init__(win)
        self.v.addWidget(title_block("Windows Memory Compression & SysMain Optimizer", "Audit Windows 10/11 Memory Compression (MMAgent), RAM commit ratios, and tune compression overhead."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Audit Memory Compression", self.p)
        self.scan_btn.clicked.connect(self._on_audit)
        row.addWidget(self.scan_btn)

        self.toggle_btn = _SecondaryButton("Toggle Memory Compression", self.p)
        self.toggle_btn.clicked.connect(self._on_toggle)
        row.addWidget(self.toggle_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Audit Memory Compression to inspect MMAgent status.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Memory Subsystem Metric", "Current Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._tuner = MemoryCompressionTuner()
        self._curr_status = None

    def _on_audit(self):
        """Query MMAgent memory status in the background."""
        self.summary_label.setText("Querying Get-MMAgent and memory working sets…")
        _run_task(self.win, self._tuner.audit, self._on_audit_done, self._on_err)

    def _on_audit_done(self, rep: MemoryTunerReport):
        """Fill the metrics table from a MemoryTunerReport and remember the current status."""
        if rep.error or not rep.status:
            self.summary_label.setText(f"Audit Error: {rep.error or 'Failed to query memory status'}")
            return

        s = rep.status
        self._curr_status = s
        self.summary_label.setText(f"Compression: {'Enabled' if s.is_enabled else 'Disabled'} | {s.recommendation}")

        metrics = [
            ("Memory Compression Active", "Enabled" if s.is_enabled else "Disabled"),
            ("Page Combining (De-duplication)", "Enabled" if s.page_combining else "Disabled"),
            ("Application PreLaunch", "Enabled" if s.app_prelaunch else "Disabled"),
            ("Compressed Memory Store Size", f"{s.compressed_mb:.1f} MB"),
            ("Estimated Physical RAM Saved", f"~{s.compressed_mb * (s.compression_ratio - 1):.1f} MB"),
            ("Compression Efficiency Ratio", f"{s.compression_ratio:.2f}x"),
            ("Total Physical RAM Installed", f"{s.total_ram_gb:.2f} GB"),
            ("Available Free Physical RAM", f"{s.available_ram_gb:.2f} GB"),
        ]

        self.table.setRowCount(len(metrics))
        for r, (k, v) in enumerate(metrics):
            self.table.setItem(r, 0, QTableWidgetItem(k))
            self.table.setItem(r, 1, QTableWidgetItem(v))

    def _on_toggle(self):
        """Flip the memory-compression state to the opposite of the audited status."""
        if not self._curr_status:
            return
        new_state = not self._curr_status.is_enabled
        self.summary_label.setText(f"Applying new state ({'Enable' if new_state else 'Disable'})…")
        _run_task(self.win, lambda: self._tuner.set_memory_compression(new_state), self._on_toggle_done, self._on_err)

    def _on_toggle_done(self, res: tuple[bool, str]):
        """Report the toggle result, then re-run the audit."""
        ok, msg = res
        QMessageBox.information(self.p, "Memory Tuning", msg)
        self._on_audit()

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 7. VIRTUAL ENVIRONMENT & SANDBOX CLEANER PAGE
# ===========================================================================

class SandboxCleanerPage(_Page):
    """Page for finding and purging Windows Sandbox, Hyper-V, and WSL2 artifacts."""
    def __init__(self, win: PremiumMainWindow):
        """Build the Sandbox Cleaner page with scan/clean buttons and an artifacts table."""
        super().__init__(win)
        self.v.addWidget(title_block("Virtual Environment & Sandbox Artifact Purger", "Reclaim storage locked in Windows Sandbox containers, Hyper-V saved states (.vsv), and WSL2 swap disks."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Virtual Artifacts", self.p)
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.clean_btn = _SecondaryButton("Purge Safe Virtual Artifacts", self.p)
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Scan Virtual Artifacts to detect discarded container images.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Category", "Size", "Safe to Clean", "Path"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._cleaner = SandboxCleaner()
        self._artifacts = []

    def _on_scan(self):
        """Scan for discarded virtualization artifacts in the background."""
        self.summary_label.setText("Scanning Windows Sandbox, Hyper-V, and WSL artifacts…")
        _run_task(self.win, self._cleaner.scan, self._on_scan_done, self._on_err)

    def _on_scan_done(self, rep: SandboxCleanReport):
        """Cache the artifact list and fill the table from a SandboxCleanReport."""
        self._artifacts = rep.artifacts
        self.summary_label.setText(
            f"Artifacts: {len(rep.artifacts)} | Total Reclaimable: {_fmt_bytes(rep.total_reclaimable_bytes)} | Categories: {', '.join(rep.categories_found) or 'None'}"
        )
        self.table.setRowCount(len(rep.artifacts))
        for r, a in enumerate(rep.artifacts):
            self.table.setItem(r, 0, QTableWidgetItem(a.name))
            self.table.setItem(r, 1, QTableWidgetItem(a.category))
            self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(a.size_bytes)))
            self.table.setItem(r, 3, QTableWidgetItem("Yes" if a.is_safe_to_clean else "Review"))
            self.table.setItem(r, 4, QTableWidgetItem(a.path))

    def _on_clean(self):
        """Purge every artifact flagged safe to clean; warn when none exist."""
        targets = [a.path for a in self._artifacts if a.is_safe_to_clean]
        if not targets:
            QMessageBox.information(self.p, "Nothing to Clean", "No safe virtual artifacts found to purge.")
            return

        self.summary_label.setText(f"Purging {len(targets)} virtual artifacts…")
        _run_task(self.win, lambda: self._cleaner.clean(targets), self._on_clean_done, self._on_err)

    def _on_clean_done(self, res: tuple[int, list[str]]):
        """Report reclaimed bytes, then rescan for remaining artifacts."""
        cleaned_b, errs = res
        self.summary_label.setText(f"Successfully purged {_fmt_bytes(cleaned_b)} of virtual artifact storage.")
        self._on_scan()

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 8. SMB SHARE & NETWORK EXPOSURE AUDITOR PAGE
# ===========================================================================

class SmbShareAuditorPage(_Page):
    """Page for auditing local SMB shares, admin shares, and SMBv1 exposure."""
    def __init__(self, win: PremiumMainWindow):
        """Build the SMB Auditor page with an audit button, summary label, and shares table."""
        super().__init__(win)
        self.v.addWidget(title_block("SMB Share & Network Exposure Auditor", "Audit local Windows SMB shares, hidden administrative shares (C$, ADMIN$), and verify SMB security settings."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Audit Network Shares", self.p)
        self.scan_btn.clicked.connect(self._on_audit)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Audit Network Shares to inspect active network exposure.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Share Name", "Resource Path", "Share Type", "Administrative", "Risk Assessment"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._aud = SmbShareAuditor()

    def _on_audit(self):
        """Start an asynchronous SMB share audit and update the summary label."""
        self.summary_label.setText("Querying Get-SmbShare and SMB security configuration…")
        _run_task(self.win, self._aud.audit, self._on_audit_done, self._on_err)

    def _on_audit_done(self, rep: SmbSecurityReport):
        """Fill the shares table and risk summary from a SmbSecurityReport."""
        if rep.error:
            self.summary_label.setText(f"Audit Error: {rep.error}")
            return

        warn_str = f" | Warnings: {rep.warnings[0]}" if rep.warnings else " | Security Status: Normal"
        self.summary_label.setText(
            f"Active Shares: {rep.total_shares} | Admin Shares: {rep.administrative_shares} | SMBv1: {'ENABLED (CRITICAL RISK)' if rep.smbv1_enabled else 'Disabled (Secure)'}{warn_str}"
        )
        self.table.setRowCount(len(rep.shares))
        for r, s in enumerate(rep.shares):
            self.table.setItem(r, 0, QTableWidgetItem(s.name))
            self.table.setItem(r, 1, QTableWidgetItem(s.path))
            self.table.setItem(r, 2, QTableWidgetItem(s.share_type))
            self.table.setItem(r, 3, QTableWidgetItem("Yes" if s.is_administrative else "No"))
            self.table.setItem(r, 4, QTableWidgetItem(s.risk_level))

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 9. PROCESS SECURITY TOKEN & INTEGRITY FORENSICS PAGE
# ===========================================================================

class ProcessTokenPage(_Page):
    """Page for inspecting process token integrity levels, elevation, and privileges."""
    def __init__(self, win: PremiumMainWindow):
        """Build the Process Token page with an audit button, summary label, and processes table."""
        super().__init__(win)
        self.v.addWidget(title_block("Process Security Token & Integrity Forensics", "Inspect TokenIntegrityLevels (Untrusted to System), token elevation types, and critical sensitive privileges."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Audit Process Tokens", self.p)
        self.scan_btn.clicked.connect(self._on_audit)
        row.addWidget(self.scan_btn)
        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Audit Process Tokens to inspect running process privilege tokens.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["PID", "Process Name", "User Account", "Integrity Level", "Elevation", "Critical Privileges"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._aud = ProcessTokenAuditor()

    def _on_audit(self):
        """Start an asynchronous process token audit and update the summary label."""
        self.summary_label.setText("Querying OpenProcessToken and GetTokenInformation…")
        _run_task(self.win, self._aud.audit, self._on_audit_done, self._on_err)

    def _on_audit_done(self, rep: ProcessTokenAuditReport):
        """Fill the processes table and privilege summary from a ProcessTokenAuditReport."""
        if rep.error:
            self.summary_label.setText(f"Audit Error: {rep.error}")
            return

        self.summary_label.setText(
            f"Audited {len(rep.processes)} processes | System: {rep.system_count} | High: {rep.high_count} | Medium: {rep.medium_count} | Elevated: {rep.elevated_count} | Powerful Privileges: {rep.dangerous_privilege_count}"
        )
        self.table.setRowCount(len(rep.processes))
        for r, p in enumerate(rep.processes):
            self.table.setItem(r, 0, QTableWidgetItem(str(p.pid)))
            self.table.setItem(r, 1, QTableWidgetItem(p.name))
            self.table.setItem(r, 2, QTableWidgetItem(p.username))
            self.table.setItem(r, 3, QTableWidgetItem(p.integrity_level))
            self.table.setItem(r, 4, QTableWidgetItem(p.elevation_type))
            self.table.setItem(r, 5, QTableWidgetItem(", ".join(p.privileges) or "Standard"))

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")


# ===========================================================================
# 10. STORAGE GROWTH TRACKER & TIMELINE DIFFER PAGE
# ===========================================================================

class StorageGrowthTrackerPage(_Page):
    """Page for taking directory snapshots and diffing storage growth between them."""
    def __init__(self, win: PremiumMainWindow):
        """Build the Growth Tracker page with path picker, snapshot/diff buttons, and a growth table."""
        super().__init__(win)
        self.v.addWidget(title_block("Storage Growth Tracker & Timeline Differ", "Take persistent directory snapshots and track disk usage expansion and folder growth deltas over time."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.path_edit = QLineEdit(str(Path.home()))
        row.addWidget(self.path_edit, 1)

        self.browse_btn = _SecondaryButton("Browse…", self.p)
        self.browse_btn.clicked.connect(self._on_browse)
        row.addWidget(self.browse_btn)

        self.snap_btn = _PrimaryButton("Take Snapshot", self.p)
        self.snap_btn.clicked.connect(self._on_snapshot)
        row.addWidget(self.snap_btn)

        self.diff_btn = _SecondaryButton("Compare Last 2 Snapshots", self.p)
        self.diff_btn.clicked.connect(self._on_diff)
        row.addWidget(self.diff_btn)
        cl.addLayout(row)

        self.summary_label = QLabel("Click Take Snapshot to capture current directory size baseline.")
        self.summary_label.setObjectName("Muted")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Directory Path", "Previous Size", "Current Size", "Net Growth", "% Growth"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(350)
        cl.addWidget(self.table)
        self.v.addWidget(card)
        self._tracker = StorageGrowthTracker()

    def _on_browse(self):
        """Open a directory picker and set it as the snapshot target."""
        d = QFileDialog.getExistingDirectory(self.p, "Select Directory to Snapshot", self.path_edit.text())
        if d:
            self.path_edit.setText(d)

    def _on_snapshot(self):
        """Capture a storage snapshot of the entered path in the background."""
        p = self.path_edit.text().strip()
        if not p:
            return
        self.summary_label.setText(f"Capturing storage snapshot of {p}…")
        _run_task(self.win, lambda: self._tracker.take_snapshot(p, label=f"Scan of {Path(p).name}"), self._on_snapshot_done, self._on_err)

    def _on_snapshot_done(self, s: SnapshotSummary):
        """Show the captured snapshot id, label, and total footprint."""
        self.summary_label.setText(
            f"Captured Snapshot #{s.snapshot_id} ('{s.label}') | Total Footprint: {_fmt_bytes(s.total_bytes)} ({s.total_files} files, {s.total_folders} folders)"
        )

    def _on_diff(self):
        """Compare the two most recent snapshots, or prompt if fewer exist."""
        snaps = self._tracker.list_snapshots()
        if len(snaps) < 2:
            QMessageBox.information(self.p, "Insufficient Snapshots", "Please take at least two snapshots to compare growth deltas.")
            return

        base_id = snaps[1].snapshot_id
        target_id = snaps[0].snapshot_id
        self.summary_label.setText(f"Comparing Snapshot #{base_id} vs #{target_id}…")
        _run_task(self.win, lambda: self._tracker.compare_snapshots(base_id, target_id), self._on_diff_done, self._on_err)

    def _on_diff_done(self, rep: StorageGrowthDiffReport):
        """Show net growth between snapshots and list the fastest-growing directories."""
        if rep.error:
            self.summary_label.setText(f"Diff Error: {rep.error}")
            return

        growth_sign = "+" if rep.net_growth_bytes >= 0 else "-"
        self.summary_label.setText(
            f"Timeline Delta: {growth_sign}{_fmt_bytes(abs(rep.net_growth_bytes))} net change between {rep.base_snapshot.formatted_time} and {rep.target_snapshot.formatted_time}"
        )
        self.table.setRowCount(len(rep.top_growing_dirs))
        for r, d in enumerate(rep.top_growing_dirs):
            self.table.setItem(r, 0, QTableWidgetItem(d.path))
            self.table.setItem(r, 1, QTableWidgetItem(_fmt_bytes(d.old_bytes)))
            self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(d.new_bytes)))
            self.table.setItem(r, 3, QTableWidgetItem(f"+{_fmt_bytes(d.growth_bytes)}"))
            self.table.setItem(r, 4, QTableWidgetItem(f"+{d.growth_percent:.1f}%"))

    def _on_err(self, exc):
        """Show an error message from a failed worker in the summary label."""
        self.summary_label.setText(f"Error: {exc}")
