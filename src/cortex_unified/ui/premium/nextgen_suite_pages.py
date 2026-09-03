"""Cortex Cleaner & NexusExplorer — Next-Generation Enterprise Suite GUI Pages.

Contains 7 interactive, theme-aware GUI pages:
1. ShaderCachePage (DirectX & Multi-Vendor GPU Shader Cache Cleaner)
2. AiTelemetryCleanerPage (Windows 11 Copilot, Recall & SQLite WAL Cleaner)
3. SsdTrimOptimizerPage (SSD NVMe Flash Wear-Leveling & TRIM Optimizer)
4. RestartManagerUnlockerPage (Windows Native Restart Manager File Unlocker)
5. VssHealthAnalyzerPage (VSS Writer Diagnostics & Shadow Storage Analyzer)
6. DevPackageCachePage (Developer Package Caches - Winget, Cargo, Vcpkg, NuGet)
7. ChecksumMatrixPage (Forensic Checksum Matrix & Batch Manifest Verifier)
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

from cortex_unified.system_tools.shader_cache_cleaner import ShaderCacheCleaner, ShaderCacheReport, ShaderCleanResult
from cortex_unified.system_tools.ai_telemetry_cleaner import AiTelemetryCleaner, AiTelemetryReport, AiCleanResult
from cortex_unified.system_tools.ssd_trim_optimizer import SsdTrimOptimizer, TrimAuditReport, TrimExecutionResult
from cortex_unified.system_tools.restart_manager_unlocker import RestartManagerUnlocker, FileLockReport, UnlockResult
from cortex_unified.system_tools.vss_health_analyzer import VssHealthAnalyzer, VssHealthReport, VssResetResult
from cortex_unified.system_tools.dev_package_cache_cleaner import DevPackageCacheCleaner, DevPackageReport, DevPackageCleanResult
from cortex_unified.system_tools.checksum_matrix import ChecksumMatrix, FileChecksumResult, ManifestVerificationReport


def _fmt_bytes(b: int) -> str:
    """_fmt_bytes."""
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.1f} MB"
    return f"{b / (1024 * 1024 * 1024):.2f} GB"


def _PrimaryButton(text: str) -> QPushButton:
    """_PrimaryButton."""
    btn = QPushButton(text)
    btn.setObjectName("Primary")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _SecondaryButton(text: str) -> QPushButton:
    """_SecondaryButton."""
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def _run_task(win, work_fn, done_fn, err_fn=None):
    """_run_task."""
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
# 1. GPU & DIRECTX SHADER CACHE CLEANER PAGE
# ===========================================================================

class ShaderCachePage(_Page):
    """ShaderCachePage class."""
    def __init__(self, win: PremiumMainWindow):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "GPU & DirectX Shader Cache Cleaner",
            "Audit and reclaim orphaned compiled shader binaries across DirectX D3DSCache, NVIDIA, AMD, and Intel drivers."
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Shader Caches")
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.clean_btn = _SecondaryButton("Clean Stale Shaders")
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)

        row.addWidget(QLabel("Min Age (Days):"))
        self.age_spin = QSpinBox()
        self.age_spin.setRange(0, 365)
        self.age_spin.setValue(14)
        row.addWidget(self.age_spin)

        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click 'Scan Shader Caches' to inspect GPU cache locations.")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Location Name", "Hardware Vendor", "Files", "Total Size", "Path"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)
        self.cleaner = ShaderCacheCleaner()

    def _on_scan(self):
        """_on_scan."""
        self.summary_label.setText("Scanning shader cache stores...")
        age = self.age_spin.value()

        def work():
            """work."""
            return self.cleaner.scan(min_age_days=age)

        def done(report: ShaderCacheReport):
            """done."""
            self.table.setRowCount(0)
            for loc in report.locations:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(loc.name))
                self.table.setItem(r, 1, QTableWidgetItem(loc.vendor))
                self.table.setItem(r, 2, QTableWidgetItem(str(loc.file_count)))
                self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(loc.total_bytes)))
                self.table.setItem(r, 4, QTableWidgetItem(loc.path))

            self.summary_label.setText(
                f"Discovered {report.total_files} shader files ({_fmt_bytes(report.total_bytes)}). "
                f"Older than {age} days: {report.stale_files} files ({_fmt_bytes(report.stale_bytes)})."
            )

        _run_task(self.win, work, done)

    def _on_clean(self):
        """_on_clean."""
        age = self.age_spin.value()
        self.summary_label.setText("Purging stale shader binaries...")

        def work():
            """work."""
            return self.cleaner.clean(min_age_days=age, dry_run=False)

        def done(result: ShaderCleanResult):
            """done."""
            msg = f"Cleaned {result.cleaned_files} shader files, freeing {_fmt_bytes(result.freed_bytes)}."
            if result.skipped_locked_files:
                msg += f" (Skipped {result.skipped_locked_files} currently locked by running games/drivers)."
            self.summary_label.setText(msg)
            QMessageBox.information(self.win, "Shader Cache Cleaned", msg)
            self._on_scan()

        _run_task(self.win, work, done)


# ===========================================================================
# 2. WINDOWS 11 AI & RECALL TELEMETRY CLEANER PAGE
# ===========================================================================

class AiTelemetryCleanerPage(_Page):
    """AiTelemetryCleanerPage class."""
    def __init__(self, win: PremiumMainWindow):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Windows 11 AI & Recall Telemetry Cleaner",
            "Audit Windows Copilot offline caches, Recall semantic vector databases, and truncate bloated SQLite WAL logs."
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan AI Telemetry")
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.clean_btn = _SecondaryButton("Clean Caches & Truncate WAL")
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)

        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click 'Scan AI Telemetry' to detect local AI stores.")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Artifact Name", "Category", "Size", "Target Path"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)
        self.cleaner = AiTelemetryCleaner()

    def _on_scan(self):
        """_on_scan."""
        self.summary_label.setText("Analyzing AI and Recall stores...")

        def work():
            """work."""
            return self.cleaner.scan()

        def done(report: AiTelemetryReport):
            """done."""
            self.table.setRowCount(0)
            for a in report.artifacts:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(a.name))
                self.table.setItem(r, 1, QTableWidgetItem(a.category))
                self.table.setItem(r, 2, QTableWidgetItem(_fmt_bytes(a.size_bytes)))
                self.table.setItem(r, 3, QTableWidgetItem(a.path))

            self.summary_label.setText(
                f"Found {len(report.artifacts)} AI artifacts consuming {_fmt_bytes(report.total_size_bytes)} "
                f"(WAL Journals: {_fmt_bytes(report.wal_journal_bytes)})."
            )

        _run_task(self.win, work, done)

    def _on_clean(self):
        """_on_clean."""
        self.summary_label.setText("Optimizing AI stores and truncating WAL logs...")

        def work():
            """work."""
            return self.cleaner.clean(checkpoint_wal=True, dry_run=False)

        def done(result: AiCleanResult):
            """done."""
            msg = (
                f"Cleaned {result.cleaned_items} transient cache items and checkpointed "
                f"{result.truncated_wal_count} SQLite WAL databases, freeing {_fmt_bytes(result.freed_bytes)}."
            )
            self.summary_label.setText(msg)
            QMessageBox.information(self.win, "AI Telemetry Cleaned", msg)
            self._on_scan()

        _run_task(self.win, work, done)


# ===========================================================================
# 3. SSD NVME TRIM & WEAR-LEVELING OPTIMIZER PAGE
# ===========================================================================

class SsdTrimOptimizerPage(_Page):
    """SsdTrimOptimizerPage class."""
    def __init__(self, win: PremiumMainWindow):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "SSD NVMe TRIM & Wear-Leveling Optimizer",
            "Audit physical flash media types, inspect NTFS/ReFS DisableDeleteNotify, and trigger live NVMe block deallocation."
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.audit_btn = _PrimaryButton("Audit Volumes & TRIM")
        self.audit_btn.clicked.connect(self._on_audit)
        row.addWidget(self.audit_btn)

        self.trim_btn = _SecondaryButton("Execute ReTrim on Selected Drive")
        self.trim_btn.clicked.connect(self._on_trim)
        row.addWidget(self.trim_btn)

        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click 'Audit Volumes & TRIM' to evaluate storage drives.")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Drive", "Media Type", "Filesystem", "TRIM Status", "Free Space", "Total Capacity"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)
        self.optimizer = SsdTrimOptimizer()

    def _on_audit(self):
        """_on_audit."""
        self.summary_label.setText("Querying physical disk controller and filesystem status...")

        def work():
            """work."""
            return self.optimizer.audit_volumes()

        def done(report: TrimAuditReport):
            """done."""
            self.table.setRowCount(0)
            for v in report.volumes:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(f"{v.drive_letter}:\\"))
                self.table.setItem(r, 1, QTableWidgetItem(v.media_type))
                self.table.setItem(r, 2, QTableWidgetItem(v.file_system))
                self.table.setItem(r, 3, QTableWidgetItem("Enabled (Active)" if v.trim_enabled else "Disabled"))
                self.table.setItem(r, 4, QTableWidgetItem(_fmt_bytes(v.free_bytes)))
                self.table.setItem(r, 5, QTableWidgetItem(_fmt_bytes(v.total_bytes)))

            status_str = "Enabled" if report.ntfs_trim_enabled else "Disabled"
            self.summary_label.setText(
                f"Filesystem TRIM: NTFS {status_str} (ReFS {'Enabled' if report.refs_trim_enabled else 'Disabled'}). "
                f"Audited {len(report.volumes)} mounted volumes."
            )

        _run_task(self.win, work, done)

    def _on_trim(self):
        """_on_trim."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self.win, "Selection Required", "Please select a drive volume from the table to execute TRIM.")
            return

        drive_item = self.table.item(row, 0)
        drive_letter = drive_item.text()[:1] if drive_item else "C"

        self.summary_label.setText(f"Executing non-destructive ReTrim on volume {drive_letter}:...")

        def work():
            """work."""
            return self.optimizer.retrim_volume(drive_letter)

        def done(result: TrimExecutionResult):
            """done."""
            self.summary_label.setText(result.message)
            if result.success:
                QMessageBox.information(self.win, "TRIM Complete", result.message)
            else:
                QMessageBox.warning(self.win, "TRIM Alert", result.message)
            self._on_audit()

        _run_task(self.win, work, done)


# ===========================================================================
# 4. WINDOWS RESTART MANAGER FILE UNLOCKER PAGE
# ===========================================================================

class RestartManagerUnlockerPage(_Page):
    """RestartManagerUnlockerPage class."""
    def __init__(self, win: PremiumMainWindow):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Windows Restart Manager File Unlocker",
            "Identify and terminate processes locking files using native Windows Restart Manager (rstrtmgr.dll) APIs."
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select or enter path to locked file…")
        row.addWidget(self.path_input, 1)

        self.browse_btn = _SecondaryButton("Browse…")
        self.browse_btn.clicked.connect(self._on_browse)
        row.addWidget(self.browse_btn)

        self.check_btn = _PrimaryButton("Inspect Locks")
        self.check_btn.clicked.connect(self._on_inspect)
        row.addWidget(self.check_btn)

        self.unlock_btn = _SecondaryButton("Unlock File (Kill Locking Procs)")
        self.unlock_btn.clicked.connect(self._on_unlock)
        row.addWidget(self.unlock_btn)
        cl.addLayout(row)

        self.summary_label = QLabel("Select a file to inspect for exclusive process locks.")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["PID", "Application Name", "Service Name", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)
        self.unlocker = RestartManagerUnlocker()

    def _on_browse(self):
        """_on_browse."""
        f, _ = QFileDialog.getOpenFileName(self.win, "Select File to Inspect Locks")
        if f:
            self.path_input.setText(f)
            self._on_inspect()

    def _on_inspect(self):
        """_on_inspect."""
        p = self.path_input.text().strip()
        if not p:
            return

        self.summary_label.setText("Querying Windows Restart Manager session...")

        def work():
            """work."""
            return self.unlocker.inspect_locks(p)

        def done(report: FileLockReport):
            """done."""
            self.table.setRowCount(0)
            if not report.exists:
                self.summary_label.setText("Specified file does not exist on disk.")
                return

            for proc in report.locking_processes:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(str(proc.pid)))
                self.table.setItem(r, 1, QTableWidgetItem(proc.name))
                self.table.setItem(r, 2, QTableWidgetItem(proc.service_name or "N/A"))
                self.table.setItem(r, 3, QTableWidgetItem(proc.app_type))

            if report.is_locked:
                self.summary_label.setText(f"File is locked by {len(report.locking_processes)} active process(es).")
            else:
                self.summary_label.setText("File is currently unlocked and free of exclusive locks.")

        _run_task(self.win, work, done)

    def _on_unlock(self):
        """_on_unlock."""
        p = self.path_input.text().strip()
        if not p:
            return

        def work():
            """work."""
            return self.unlocker.unlock_file(p, force_terminate=True)

        def done(result: UnlockResult):
            """done."""
            self.summary_label.setText(result.message)
            QMessageBox.information(self.win, "Unlock Status", result.message)
            self._on_inspect()

        _run_task(self.win, work, done)


# ===========================================================================
# 5. VSS WRITER & SHADOW STORAGE ANALYZER PAGE
# ===========================================================================

class VssHealthAnalyzerPage(_Page):
    """VssHealthAnalyzerPage class."""
    def __init__(self, win: PremiumMainWindow):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "VSS Writer Health & Shadow Storage Analyzer",
            "Diagnose Volume Shadow Copy (VSS) writers for stalled or failed states and inspect shadow copy storage bounds."
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Inspect VSS Subsystem")
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.reset_btn = _SecondaryButton("Reset Stalled VSS Writers")
        self.reset_btn.clicked.connect(self._on_reset)
        row.addWidget(self.reset_btn)

        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click 'Inspect VSS Subsystem' to audit shadow copy writers.")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Writer Name", "State Code & Description", "Last Error", "Health Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)
        self.analyzer = VssHealthAnalyzer()

    def _on_scan(self):
        """_on_scan."""
        self.summary_label.setText("Querying vssadmin writers and shadow storage...")

        def work():
            """work."""
            return self.analyzer.inspect_health()

        def done(report: VssHealthReport):
            """done."""
            self.table.setRowCount(0)
            for w in report.writers:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(w.name))
                self.table.setItem(r, 1, QTableWidgetItem(w.state_desc))
                self.table.setItem(r, 2, QTableWidgetItem(w.last_error))
                status_item = QTableWidgetItem("Healthy" if w.is_healthy else "FAILED / STALLED")
                self.table.setItem(r, 3, status_item)

            self.summary_label.setText(
                f"VSS Subsystem: {report.healthy_writer_count} healthy writers, "
                f"{report.failed_writer_count} failed/stalled writers. "
                f"Total shadow copy storage used: {_fmt_bytes(report.total_shadow_used_bytes)}."
            )

        _run_task(self.win, work, done)

    def _on_reset(self):
        """_on_reset."""
        self.summary_label.setText("Restarting VSS services and clearing stalled writer states...")

        def work():
            """work."""
            return self.analyzer.reset_vss_writers()

        def done(result: VssResetResult):
            """done."""
            self.summary_label.setText(result.message)
            QMessageBox.information(self.win, "VSS Reset Status", result.message)
            self._on_scan()

        _run_task(self.win, work, done)


# ===========================================================================
# 6. DEVELOPER PACKAGE CACHES CLEANER PAGE
# ===========================================================================

class DevPackageCachePage(_Page):
    """DevPackageCachePage class."""
    def __init__(self, win: PremiumMainWindow):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Developer Package Caches Cleaner",
            "Audit and reclaim gigabytes of cached package downloads across Winget, Rust Cargo, C++ vcpkg, .NET NuGet, and Pip."
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.scan_btn = _PrimaryButton("Scan Developer Stores")
        self.scan_btn.clicked.connect(self._on_scan)
        row.addWidget(self.scan_btn)

        self.clean_btn = _SecondaryButton("Purge Selected Store Caches")
        self.clean_btn.clicked.connect(self._on_clean)
        row.addWidget(self.clean_btn)

        row.addStretch(1)
        cl.addLayout(row)

        self.summary_label = QLabel("Click 'Scan Developer Stores' to examine toolchain cache sizes.")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Ecosystem", "Store Name", "Packages", "Total Size", "Location"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)
        self.cleaner = DevPackageCacheCleaner()

    def _on_scan(self):
        """_on_scan."""
        self.summary_label.setText("Analyzing developer toolchain directories...")

        def work():
            """work."""
            return self.cleaner.scan()

        def done(report: DevPackageReport):
            """done."""
            self.table.setRowCount(0)
            for s in report.stores:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(s.ecosystem))
                self.table.setItem(r, 1, QTableWidgetItem(s.name))
                self.table.setItem(r, 2, QTableWidgetItem(str(s.package_count)))
                self.table.setItem(r, 3, QTableWidgetItem(_fmt_bytes(s.total_bytes)))
                self.table.setItem(r, 4, QTableWidgetItem(s.path))

            self.summary_label.setText(
                f"Discovered {report.total_packages} cached packages across {len(report.stores)} stores "
                f"consuming {_fmt_bytes(report.total_bytes)}."
            )

        _run_task(self.win, work, done)

    def _on_clean(self):
        """_on_clean."""
        self.summary_label.setText("Purging developer package stores...")

        def work():
            """work."""
            return self.cleaner.clean(dry_run=False)

        def done(result: DevPackageCleanResult):
            """done."""
            msg = f"Cleaned {result.cleaned_stores} stores, removing {result.deleted_packages} packages and freeing {_fmt_bytes(result.freed_bytes)}."
            self.summary_label.setText(msg)
            QMessageBox.information(self.win, "Developer Stores Cleaned", msg)
            self._on_scan()

        _run_task(self.win, work, done)


# ===========================================================================
# 7. FORENSIC CHECKSUM MATRIX & MANIFEST VERIFIER PAGE
# ===========================================================================

class ChecksumMatrixPage(_Page):
    """ChecksumMatrixPage class."""
    def __init__(self, win: PremiumMainWindow):
        """__init__."""
        super().__init__(win)
        self.v.addWidget(title_block(
            "Forensic Checksum Matrix & Manifest Verifier",
            "Batch compute CRC32, MD5, SHA-1, and SHA-256 hashes, generate standard manifests (.sha256, .sfv), and verify trees."
        ))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(22, 20, 22, 20)
        cl.setSpacing(12)

        row = QHBoxLayout()
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Select file to hash or directory to verify manifests…")
        row.addWidget(self.target_input, 1)

        self.browse_file_btn = _SecondaryButton("Browse File…")
        self.browse_file_btn.clicked.connect(self._on_browse_file)
        row.addWidget(self.browse_file_btn)

        self.browse_dir_btn = _SecondaryButton("Browse Folder…")
        self.browse_dir_btn.clicked.connect(self._on_browse_dir)
        row.addWidget(self.browse_dir_btn)

        self.hash_btn = _PrimaryButton("Calculate Hashes")
        self.hash_btn.clicked.connect(self._on_hash)
        row.addWidget(self.hash_btn)

        self.manifest_btn = _SecondaryButton("Generate .sha256 Manifest")
        self.manifest_btn.clicked.connect(self._on_generate_manifest)
        row.addWidget(self.manifest_btn)
        cl.addLayout(row)

        self.summary_label = QLabel("Select a file to compute hashes or directory to generate manifests.")
        cl.addWidget(self.summary_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Algorithm", "Checksum / Digest", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        cl.addWidget(self.table)

        self.v.addWidget(card)
        self.v.addStretch(1)
        self.matrix = ChecksumMatrix()

    def _on_browse_file(self):
        """_on_browse_file."""
        f, _ = QFileDialog.getOpenFileName(self.win, "Select File to Hash")
        if f:
            self.target_input.setText(f)
            self._on_hash()

    def _on_browse_dir(self):
        """_on_browse_dir."""
        d = QFileDialog.getExistingDirectory(self.win, "Select Folder for Manifest")
        if d:
            self.target_input.setText(d)

    def _on_hash(self):
        """_on_hash."""
        p = Path(self.target_input.text().strip())
        if not p.is_file():
            QMessageBox.warning(self.win, "File Required", "Please select a valid file to calculate checksums.")
            return

        self.summary_label.setText(f"Streaming {p.name} through hash digest matrix...")

        def work():
            """work."""
            return self.matrix.hash_file(p, algorithms=["crc32", "md5", "sha1", "sha256", "sha512"])

        def done(res: FileChecksumResult):
            """done."""
            self.table.setRowCount(0)
            rows = [
                ("CRC32", res.crc32),
                ("MD5", res.md5),
                ("SHA-1", res.sha1),
                ("SHA-256", res.sha256),
                ("SHA-512", res.sha512),
            ]
            for algo, digest in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(algo))
                self.table.setItem(r, 1, QTableWidgetItem(digest))
                self.table.setItem(r, 2, QTableWidgetItem("Computed"))

            self.summary_label.setText(
                f"Computed 5 checksum digests for {p.name} ({_fmt_bytes(res.size_bytes)}) in {res.duration_ms:.1f}ms."
            )

        _run_task(self.win, work, done)

    def _on_generate_manifest(self):
        """_on_generate_manifest."""
        p = Path(self.target_input.text().strip())
        if not p.is_dir():
            QMessageBox.warning(self.win, "Directory Required", "Please select a valid directory to generate a manifest.")
            return

        out_file = p / "checksums.sha256"
        self.summary_label.setText(f"Generating SHA-256 manifest for {p}...")

        def work():
            """work."""
            return self.matrix.generate_manifest(p, out_file, algorithm="sha256")

        def done(count: int):
            """done."""
            msg = f"Generated checksum manifest with {count} file entries at: {out_file}"
            self.summary_label.setText(msg)
            QMessageBox.information(self.win, "Manifest Created", msg)

        _run_task(self.win, work, done)
