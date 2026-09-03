"""Tab for Sentinel Pro security scanner in Cortex Cleaner GUI."""

import os
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QHeaderView, QSpinBox, QTextEdit, QSplitter
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QColor, QFont

from .base_tab import BaseTab
from cortex_unified.core.config import Config


class SentinelScanWorker(QThread):
    """Background worker for Sentinel Pro security scanning."""
    finished = Signal(object)  # ScanStats
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, directory: str, scan_archives: bool = False,
                 scan_git: bool = False, max_workers: int = 8):
        super().__init__()
        self.directory = directory
        self.scan_archives = scan_archives
        self.scan_git = scan_git
        self.max_workers = max_workers
        """__init__."""
        """__init__."""

    def run(self):
        try:
            from cortex_unified.system_tools.secrets_scanner import (
                run_scan, scan_archives, scan_git_history
            )
            self.progress.emit(f"Scanning {self.directory}...")
            stats = run_scan(self.directory, max_workers=self.max_workers, quiet=True)

            if self.scan_archives:
                self.progress.emit("Scanning archives...")
                archive_findings, archive_count = scan_archives(self.directory, quiet=True)
                stats.findings.extend(archive_findings)
                stats.archives_scanned = archive_count

            if self.scan_git:
                self.progress.emit("Scanning git history...")
                git_findings, git_count = scan_git_history(self.directory, quiet=True)
                stats.findings.extend(git_findings)
                stats.git_commits_scanned = git_count

            # Re-sort after merging
            stats.findings.sort(key=lambda f: (-f.severity_rank, f.file_path, f.line_number))
            self.finished.emit(stats)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
        """run."""


SEVERITY_COLORS = {
    "CRITICAL": QColor(239, 68, 68),
    "HIGH": QColor(249, 115, 22),
    "MEDIUM": QColor(234, 179, 8),
    "LOW": QColor(34, 197, 94),
    "INFO": QColor(59, 130, 246),
}


class SecurityScannerTab(BaseTab):
    """Tab for Sentinel Pro security & secrets scanner."""

    def __init__(self, config, logger, safety_manager):
        self.scan_stats = None
        super().__init__(config, logger, safety_manager)
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Set up the security scanner UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel("🔐 Sentinel Pro — Security & Secrets Scanner")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(header)

        # Target path
        path_group = QGroupBox("Scan Target")
        path_layout = QHBoxLayout(path_group)
        self.scan_path_input = QLineEdit()
        self.scan_path_input.setPlaceholderText("Select directory to scan for secrets & vulnerabilities...")
        self.scan_path_input.setMinimumHeight(30)
        path_layout.addWidget(self.scan_path_input)
        browse_btn = QPushButton("Browse")
        browse_btn.setMinimumHeight(30)
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)
        layout.addWidget(path_group)

        # Options
        options_group = QGroupBox("Scan Options")
        options_layout = QHBoxLayout(options_group)
        self.archive_checkbox = QCheckBox("Scan Archives (zip/tar)")
        self.archive_checkbox.setToolTip("Also scan inside .zip, .tar.gz files")
        options_layout.addWidget(self.archive_checkbox)
        self.git_checkbox = QCheckBox("Scan Git History")
        self.git_checkbox.setToolTip("Walk git commit history for leaked secrets")
        options_layout.addWidget(self.git_checkbox)
        options_layout.addWidget(QLabel("Threads:"))
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 32)
        self.threads_spinbox.setValue(8)
        options_layout.addWidget(self.threads_spinbox)
        options_layout.addStretch()
        layout.addWidget(options_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.scan_button = QPushButton("🔍 Start Security Scan")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setStyleSheet("QPushButton { font-weight: bold; font-size: 14px; padding: 8px 24px; }")
        self.scan_button.clicked.connect(self.start_scan)
        btn_layout.addWidget(self.scan_button)

        self.export_button = QPushButton("📄 Export JSON Report")
        self.export_button.setMinimumHeight(40)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_report)
        btn_layout.addWidget(self.export_button)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)

        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 13px; padding: 6px; background: #1a1a2e; border-radius: 6px;")
        self.summary_label.setWordWrap(True)
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # Findings table
        findings_group = QGroupBox("Findings")
        findings_layout = QVBoxLayout(findings_group)
        self.findings_table = QTableWidget()
        self.findings_table.setColumnCount(7)
        self.findings_table.setHorizontalHeaderLabels([
            "Severity", "Category", "Pattern", "File", "Line", "Confidence", "Compliance"
        ])
        self.findings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.findings_table.horizontalHeader().setStretchLastSection(True)
        self.findings_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.findings_table.setAlternatingRowColors(True)
        self.findings_table.currentCellChanged.connect(self._on_finding_selected)
        findings_layout.addWidget(self.findings_table)
        layout.addWidget(findings_group, stretch=1)

        # Detail pane
        detail_group = QGroupBox("Finding Details")
        detail_layout = QVBoxLayout(detail_group)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(140)
        self.detail_text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        detail_layout.addWidget(self.detail_text)
        layout.addWidget(detail_group)

    def _browse_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if path:
            self.scan_path_input.setText(path)
        """_browse_path."""
        """_browse_path."""

    def start_scan(self):
        path = self.scan_path_input.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, "Invalid Path", "Please select a valid directory.")
            return

        self.scan_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.summary_label.setVisible(False)
        self.findings_table.setRowCount(0)
        self.detail_text.clear()
        self.progress_label.setText("Starting security scan...")

        worker = SentinelScanWorker(
            directory=path,
            scan_archives=self.archive_checkbox.isChecked(),
            scan_git=self.git_checkbox.isChecked(),
            max_workers=self.threads_spinbox.value()
        )
        self.add_worker_thread(worker)
        worker.finished.connect(self._scan_complete)
        worker.error.connect(self._scan_error)
        worker.progress.connect(lambda msg: self.progress_label.setText(msg))
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.error.connect(lambda: self._cleanup_worker(worker))
        worker.start()
        """start_scan."""
        """start_scan."""

    def _cleanup_worker(self, worker):
        self.remove_worker_thread(worker)
        worker.deleteLater()
        """_cleanup_worker."""
        """_cleanup_worker."""

    def _scan_complete(self, stats):
        self.scan_stats = stats
        self.scan_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")

        findings = stats.findings
        crit = len([f for f in findings if f.severity == "CRITICAL"])
        high = len([f for f in findings if f.severity == "HIGH"])
        med = len([f for f in findings if f.severity == "MEDIUM"])
        low = len([f for f in findings if f.severity == "LOW"])

        self.summary_label.setText(
            f"📊 Risk Score: {stats.risk_score}/100  |  "
            f"Files Scanned: {stats.files_scanned}  |  "
            f"Duration: {stats.duration_seconds}s  |  "
            f"🔴 Critical: {crit}  🟠 High: {high}  🟡 Medium: {med}  🟢 Low: {low}  |  "
            f"Total Findings: {len(findings)}"
        )
        self.summary_label.setVisible(True)

        self.findings_table.setRowCount(len(findings))
        for i, f in enumerate(findings):
            sev_item = QTableWidgetItem(f.severity)
            color = SEVERITY_COLORS.get(f.severity, QColor(200, 200, 200))
            sev_item.setBackground(color)
            sev_item.setForeground(QColor(0, 0, 0) if f.severity in ("MEDIUM", "LOW") else QColor(255, 255, 255))
            font = QFont()
            font.setBold(True)
            sev_item.setFont(font)
            self.findings_table.setItem(i, 0, sev_item)
            self.findings_table.setItem(i, 1, QTableWidgetItem(f.category))
            self.findings_table.setItem(i, 2, QTableWidgetItem(f.pattern_name))

            rel_path = f.file_path
            try:
                rel_path = os.path.relpath(f.file_path, self.scan_path_input.text().strip())
            except ValueError:
                pass
            self.findings_table.setItem(i, 3, QTableWidgetItem(rel_path))
            self.findings_table.setItem(i, 4, QTableWidgetItem(str(f.line_number)))
            self.findings_table.setItem(i, 5, QTableWidgetItem(f"{f.confidence:.0%}"))
            self.findings_table.setItem(i, 6, QTableWidgetItem(", ".join(f.compliance)))

        self.findings_table.resizeColumnsToContents()
        self.set_status(f"Security scan complete: {len(findings)} findings (Risk: {stats.risk_score}/100)")
        """_scan_complete."""
        """_scan_complete."""

    def _scan_error(self, error_msg):
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        QMessageBox.critical(self, "Scan Error", f"Security scan failed:\n{error_msg}")
        """_scan_error."""
        """_scan_error."""

    def _on_finding_selected(self, row, col, prev_row, prev_col):
        if not self.scan_stats or row < 0 or row >= len(self.scan_stats.findings):
            return
        f = self.scan_stats.findings[row]
        detail = (
            f"📌 {f.pattern_name}\n"
            f"{'═' * 60}\n"
            f"File:       {f.file_path}\n"
            f"Line:       {f.line_number}\n"
            f"Severity:   {f.severity}   |   Category: {f.category}\n"
            f"Confidence: {f.confidence:.0%}   |   Entropy: {f.entropy:.2f}\n"
            f"Compliance: {', '.join(f.compliance)}\n"
            f"{'─' * 60}\n"
            f"Preview:    {f.line_preview}\n"
            f"Match:      {f.match_preview}\n"
            f"{'─' * 60}\n"
            f"Remediation:\n{f.remediation}\n"
        )
        self.detail_text.setPlainText(detail)
        """_on_finding_selected."""
        """_on_finding_selected."""

    def export_report(self):
        if not self.scan_stats:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Security Report", "sentinel_report.json", "JSON (*.json)"
        )
        if not file_path:
            return
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as fp:
                json.dump(self.scan_stats.to_dict(), fp, indent=2, default=str)
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export report:\n{str(e)}")
        """export_report."""
        """export_report."""
