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
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QColor, QFont, QDesktopServices

from .base_tab import BaseTab
from cortex_unified.core.config import Config


class SentinelScanWorker(QThread):
    """Background worker for Sentinel Pro security scanning."""
    finished = Signal(object)  # ScanStats
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, directory: str, scan_archives: bool = False,
                 scan_git: bool = False, max_workers: int = 8):
        """Store the scan target, archive/git options, and thread budget."""
        super().__init__()
        self.directory = directory
        self.scan_archives = scan_archives
        self.scan_git = scan_git
        self.max_workers = max_workers

    def run(self):
        """Run the secrets scan via system_tools.secrets_scanner.

        Performs run_scan on the directory, optionally appends archive and
        git-history findings, and re-sorts everything by severity. Emits
        ``progress`` with status text, ``finished`` with the merged
        ScanStats, or ``error`` with the failure message.
        """
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


class VerifyWorker(QThread):
    """Background worker for live credential verification against provider APIs."""
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, findings: list):
        """Initialize worker with findings list to verify."""
        super().__init__()
        self.findings = findings

    def run(self):
        """Execute credential verification off the main UI thread."""
        try:
            from cortex_unified.system_tools.secrets_scanner import verify_all_findings
            self.progress.emit("Verifying credentials against provider APIs...")
            results = verify_all_findings(self.findings, quiet=True)
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))


class BaselineWorker(QThread):
    """Background worker for baseline save and delta calculation."""
    finished = Signal(str, object)  # (action, result)
    error = Signal(str)

    def __init__(self, action: str, findings: list, directory: str):
        """Initialize with action ('save' or 'diff'), findings, and directory."""
        super().__init__()
        self.action = action
        self.findings = findings
        self.directory = directory

    def run(self):
        """Execute baseline save or diff calculation off the main thread."""
        try:
            if self.action == "save":
                from cortex_unified.system_tools.secrets_scanner import save_baseline
                path = save_baseline(self.findings, self.directory)
                self.finished.emit("save", path)
            elif self.action == "diff":
                from cortex_unified.system_tools.secrets_scanner import load_baseline, compute_delta
                base = load_baseline(self.directory)
                if not base:
                    self.finished.emit("diff", None)
                else:
                    new_findings, known_count = compute_delta(self.findings, base)
                    self.finished.emit("diff", (new_findings, known_count))
        except Exception as exc:
            self.error.emit(str(exc))


class ExportWorker(QThread):
    """Background worker for SARIF, CSV, JSON, and HTML report export."""
    finished = Signal(str, str)  # (format, file_path)
    error = Signal(str)

    def __init__(self, fmt: str, stats: object, file_path: str):
        """Initialize with format ('sarif', 'csv', 'html', 'json'), scan stats, and output path."""
        super().__init__()
        self.fmt = fmt.lower()
        self.stats = stats
        self.file_path = file_path

    def run(self):
        """Generate and write the report to disk off the UI thread."""
        try:
            if self.fmt == "sarif":
                from cortex_unified.system_tools.secrets_scanner import export_sarif
                export_sarif(self.stats, self.file_path)
            elif self.fmt == "csv":
                from cortex_unified.system_tools.secrets_scanner import export_csv
                export_csv(self.stats, self.file_path)
            elif self.fmt == "html":
                from cortex_unified.system_tools.secrets_scanner import generate_html_report
                generate_html_report(self.stats, self.file_path)
            elif self.fmt == "json":
                import json
                with open(self.file_path, "w", encoding="utf-8") as fp:
                    json.dump(self.stats.to_dict(), fp, indent=2, default=str)
            self.finished.emit(self.fmt, self.file_path)
        except Exception as exc:
            self.error.emit(str(exc))


class DashboardWorker(QThread):
    """Background worker to generate live web dashboard report."""
    finished = Signal(str)  # output file path
    error = Signal(str)

    def __init__(self, stats: object, output_path: str):
        """Initialize with scan stats and output file path."""
        super().__init__()
        self.stats = stats
        self.output_path = output_path

    def run(self):
        """Generate dashboard HTML file off the UI thread."""
        try:
            from cortex_unified.system_tools.secrets_scanner import generate_html_report
            generate_html_report(self.stats, self.output_path)
            self.finished.emit(self.output_path)
        except Exception as exc:
            self.error.emit(str(exc))


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
        """Initialize with a null scan-stats holder before UI setup."""
        self.scan_stats = None
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Set up the security scanner UI.

        Creates a scan-target row (path input + Browse), an options group
        (archive/git checkboxes and a thread spinbox), Start Scan and
        Export JSON buttons, a busy progress bar with label, a summary
        banner, a seven-column findings table with severity coloring, and a
        read-only detail pane showing the selected finding's metadata.
        """
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

        # Verify / Baseline row — live-verify stays off until explicitly clicked
        # (backend default is air-gap safe; only this button triggers network).
        verify_layout = QHBoxLayout()
        self.verify_button = QPushButton("⚡ Verify Live Credentials (network)")
        self.verify_button.setToolTip(
            "Check verifiable findings against provider APIs. "
            "Makes network requests — click to consent.")
        self.verify_button.setEnabled(False)
        self.verify_button.clicked.connect(self._verify_live)
        verify_layout.addWidget(self.verify_button)

        self.baseline_button = QPushButton("💾 Save Baseline")
        self.baseline_button.setToolTip("Save current findings as the delta baseline.")
        self.baseline_button.setEnabled(False)
        self.baseline_button.clicked.connect(self._save_baseline)
        verify_layout.addWidget(self.baseline_button)

        self.delta_button = QPushButton("📊 New Since Baseline")
        self.delta_button.setToolTip("Compare current findings against the saved baseline.")
        self.delta_button.setEnabled(False)
        self.delta_button.clicked.connect(self._show_delta)
        verify_layout.addWidget(self.delta_button)
        verify_layout.addStretch()
        layout.addLayout(verify_layout)

        # False-positive + export row (SARIF/CSV/HTML were orphaned backend ops)
        fp_layout = QHBoxLayout()
        self.suppress_fp_button = QPushButton("🚫 Suppress Selected (FP)")
        self.suppress_fp_button.setToolTip("Add the selected finding to the FP suppression DB.")
        self.suppress_fp_button.setEnabled(False)
        self.suppress_fp_button.clicked.connect(self._suppress_selected_fp)
        fp_layout.addWidget(self.suppress_fp_button)

        self.apply_fp_button = QPushButton("🧹 Apply FP Filter")
        self.apply_fp_button.setToolTip("Hide findings listed in the FP suppression DB.")
        self.apply_fp_button.setEnabled(False)
        self.apply_fp_button.clicked.connect(self._apply_fp_filter)
        fp_layout.addWidget(self.apply_fp_button)

        self.export_sarif_button = QPushButton("📤 SARIF")
        self.export_sarif_button.setToolTip("Export findings in SARIF format.")
        self.export_sarif_button.setEnabled(False)
        self.export_sarif_button.clicked.connect(self._export_sarif)
        fp_layout.addWidget(self.export_sarif_button)

        self.export_csv_button = QPushButton("📤 CSV")
        self.export_csv_button.setToolTip("Export findings in CSV format.")
        self.export_csv_button.setEnabled(False)
        self.export_csv_button.clicked.connect(self._export_csv)
        fp_layout.addWidget(self.export_csv_button)

        self.export_html_button = QPushButton("📤 HTML")
        self.export_html_button.setToolTip("Generate the self-contained Sentinel HTML report.")
        self.export_html_button.setEnabled(False)
        self.export_html_button.clicked.connect(self._export_html)
        fp_layout.addWidget(self.export_html_button)

        self.dashboard_button = QPushButton("🌐 Live Web Dashboard")
        self.dashboard_button.setToolTip("Launch live interactive web dashboard for security findings in your browser.")
        self.dashboard_button.setEnabled(False)
        self.dashboard_button.clicked.connect(self._start_dashboard)
        fp_layout.addWidget(self.dashboard_button)

        fp_layout.addStretch()
        layout.addLayout(fp_layout)

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
        """Choose a scan directory and put it in the path input."""
        path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if path:
            self.scan_path_input.setText(path)

    def start_scan(self):
        """Validate the path and run SentinelScanWorker on a background thread.

        Disables the scan/export buttons, clears previous results, and
        wires worker progress/finished/error signals to the UI; the worker
        is tracked for cleanup.
        """
        path = self.scan_path_input.text().strip()
        if not path or not os.path.isdir(path):
            QMessageBox.warning(self, "Invalid Path", "Please select a valid directory.")
            return

        self.scan_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        self.baseline_button.setEnabled(False)
        self.delta_button.setEnabled(False)
        self.suppress_fp_button.setEnabled(False)
        self.apply_fp_button.setEnabled(False)
        self.export_sarif_button.setEnabled(False)
        self.export_csv_button.setEnabled(False)
        self.export_html_button.setEnabled(False)
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

    def _cleanup_worker(self, worker):
        """Untrack and schedule deletion of the finished scan worker."""
        self.remove_worker_thread(worker)
        worker.deleteLater()

    def _scan_complete(self, stats):
        """Render the finished ScanStats.

        Stores the stats, shows the risk-score/severity summary banner,
        fills the findings table with severity-colored rows (relative file
        paths, confidence, compliance), and enables the export button.
        """
        self.scan_stats = stats
        self.scan_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.verify_button.setEnabled(True)
        self.baseline_button.setEnabled(True)
        self.delta_button.setEnabled(True)
        self.suppress_fp_button.setEnabled(True)
        self.apply_fp_button.setEnabled(True)
        self.export_sarif_button.setEnabled(True)
        self.export_csv_button.setEnabled(True)
        self.export_html_button.setEnabled(True)
        self.dashboard_button.setEnabled(True)
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

    def _scan_error(self, error_msg):
        """Re-enable the scan button and show the scan failure dialog."""
        self.scan_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        QMessageBox.critical(self, "Scan Error", f"Security scan failed:\n{error_msg}")

    def _on_finding_selected(self, row, col, prev_row, prev_col):
        """Show the selected finding's full details in the detail pane.

        Displays pattern name, file/line, severity, category, confidence,
        entropy, compliance frameworks, line preview, match preview, and
        remediation guidance.
        """
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

    def export_report(self):
        """Export the last scan's stats to a JSON file via a save dialog using ExportWorker."""
        if not self.scan_stats:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Security Report", "sentinel_report.json", "JSON (*.json)"
        )
        if not file_path:
            return
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Exporting JSON report...")
        worker = ExportWorker("json", self.scan_stats, file_path)
        self.add_worker_thread(worker)

        def on_done(fmt, path):
            """Handle JSON export completion."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.information(self, "Export Complete", f"Report saved to:\n{path}")

        def on_err(msg):
            """Handle JSON export failure."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Export Error", f"Failed to export report:\n{msg}")

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _verify_live(self):
        """Verify findings against real provider APIs via VerifyWorker."""
        if not self.scan_stats or not self.scan_stats.findings:
            return
        reply = QMessageBox.question(
            self, "Verify Live Credentials",
            "This will send targeted, read-only authentication probes to live cloud services "
            "(AWS, GitHub, Slack, Stripe, OpenAI, npm) to determine whether discovered tokens are active.\n\n"
            "Proceed with live verification?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.progress_bar.setVisible(True)
        self.progress_label.setText("Verifying live credentials...")
        self.verify_button.setEnabled(False)

        worker = VerifyWorker(self.scan_stats.findings)
        self.add_worker_thread(worker)

        def on_progress(text):
            """Update verification progress status text."""
            self.progress_label.setText(text)

        def on_done(results):
            """Handle live verification completion."""
            self.progress_bar.setVisible(False)
            self.verify_button.setEnabled(True)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            live_count = sum(1 for r in results.values() if getattr(r, 'verified', False) is True)
            QMessageBox.information(
                self, "Verification Complete",
                f"Verified {len(results)} potential credentials.\n"
                f"Active / Live credentials found: {live_count}"
            )
            self._scan_complete(self.scan_stats)

        def on_err(msg):
            """Handle live verification failure."""
            self.progress_bar.setVisible(False)
            self.verify_button.setEnabled(True)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Verification Error", msg)

        worker.progress.connect(on_progress)
        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _save_baseline(self):
        """Save current findings as delta baseline via BaselineWorker."""
        if not self.scan_stats:
            return
        p = self.scan_path_input.text().strip() or os.getcwd()
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Saving baseline...")
        self.baseline_button.setEnabled(False)

        worker = BaselineWorker("save", self.scan_stats.findings, p)
        self.add_worker_thread(worker)

        def on_done(action, path):
            """Handle baseline save completion."""
            self.progress_bar.setVisible(False)
            self.baseline_button.setEnabled(True)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.information(self, "Baseline Saved", f"Saved baseline with {len(self.scan_stats.findings)} findings to:\n{path}")

        def on_err(msg):
            """Handle baseline save failure."""
            self.progress_bar.setVisible(False)
            self.baseline_button.setEnabled(True)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Baseline Error", msg)

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _show_delta(self):
        """Compare current findings against saved baseline via BaselineWorker."""
        if not self.scan_stats:
            return
        p = self.scan_path_input.text().strip() or os.getcwd()
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Comparing against baseline...")
        self.delta_button.setEnabled(False)

        worker = BaselineWorker("diff", self.scan_stats.findings, p)
        self.add_worker_thread(worker)

        def on_done(action, res):
            """Handle baseline comparison completion."""
            self.progress_bar.setVisible(False)
            self.delta_button.setEnabled(True)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            if res is None:
                QMessageBox.warning(self, "No Baseline", "No baseline found for this directory. Click 'Save Baseline' first.")
            else:
                new_findings, known_count = res
                QMessageBox.information(
                    self, "Baseline Delta",
                    f"Baseline comparison:\n"
                    f"• Known (previously seen) findings: {known_count}\n"
                    f"• New findings: {len(new_findings)}"
                )

        def on_err(msg):
            """Handle baseline comparison failure."""
            self.progress_bar.setVisible(False)
            self.delta_button.setEnabled(True)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Delta Error", msg)

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _suppress_selected_fp(self):
        """Add the selected finding to the false-positive suppression DB."""
        row = self.findings_table.currentRow()
        if row < 0 or not self.scan_stats or row >= len(self.scan_stats.findings):
            QMessageBox.warning(self, "Select Finding", "Please select a finding row in the table to suppress.")
            return
        f = self.scan_stats.findings[row]
        try:
            from cortex_unified.system_tools.secrets_scanner import add_fp
            p = self.scan_path_input.text().strip() or os.getcwd()
            add_fp(f.fingerprint, p, reason="User suppressed via GUI")
            QMessageBox.information(self, "Suppressed", f"Added finding '{f.pattern_name}' to false positive database.")
            self._apply_fp_filter()
        except Exception as exc:
            QMessageBox.critical(self, "Suppression Error", str(exc))

    def _apply_fp_filter(self):
        """Filter out suppressed false positives from the displayed findings."""
        if not self.scan_stats:
            return
        try:
            from cortex_unified.system_tools.secrets_scanner import apply_fp_filter
            p = self.scan_path_input.text().strip() or os.getcwd()
            filtered, suppressed = apply_fp_filter(self.scan_stats.findings, p)
            self.scan_stats.findings = filtered
            self._scan_complete(self.scan_stats)
            QMessageBox.information(self, "FP Filter Applied", f"Filtered out {suppressed} false positive findings.")
        except Exception as exc:
            QMessageBox.critical(self, "Filter Error", str(exc))

    def _export_sarif(self):
        """Export findings to a standard SARIF file via ExportWorker."""
        if not self.scan_stats:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export SARIF Report", "sentinel_report.sarif", "SARIF Files (*.sarif *.json)"
        )
        if not file_path:
            return
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Exporting SARIF report...")
        worker = ExportWorker("sarif", self.scan_stats, file_path)
        self.add_worker_thread(worker)

        def on_done(fmt, path):
            """Handle SARIF export completion."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.information(self, "Export Complete", f"SARIF report saved to:\n{path}")

        def on_err(msg):
            """Handle SARIF export failure."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Export Error", str(msg))

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _export_csv(self):
        """Export findings to a CSV file via ExportWorker."""
        if not self.scan_stats:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV Report", "sentinel_report.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Exporting CSV report...")
        worker = ExportWorker("csv", self.scan_stats, file_path)
        self.add_worker_thread(worker)

        def on_done(fmt, path):
            """Handle CSV export completion."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.information(self, "Export Complete", f"CSV report saved to:\n{path}")

        def on_err(msg):
            """Handle CSV export failure."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Export Error", str(msg))

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _export_html(self):
        """Export findings to a self-contained HTML audit report via ExportWorker."""
        if not self.scan_stats:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export HTML Report", "sentinel_report.html", "HTML Files (*.html)"
        )
        if not file_path:
            return
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Exporting HTML report...")
        worker = ExportWorker("html", self.scan_stats, file_path)
        self.add_worker_thread(worker)

        def on_done(fmt, path):
            """Handle HTML export completion."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.information(self, "Export Complete", f"HTML report saved to:\n{path}")

        def on_err(msg):
            """Handle HTML export failure."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Export Error", str(msg))

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

    def _start_dashboard(self):
        """Launch and view the interactive web dashboard via DashboardWorker."""
        if not self.scan_stats:
            return
        import tempfile
        temp_dir = tempfile.gettempdir()
        out_file = os.path.join(temp_dir, "sentinel_live_dashboard.html")
        self.progress_bar.setVisible(True)
        self.progress_label.setText("Generating live dashboard...")

        worker = DashboardWorker(self.scan_stats, out_file)
        self.add_worker_thread(worker)

        def on_done(path):
            """Handle live dashboard generation completion."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

        def on_err(msg):
            """Handle live dashboard generation failure."""
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
            self.remove_worker_thread(worker)
            worker.deleteLater()
            QMessageBox.critical(self, "Dashboard Error", str(msg))

        worker.finished.connect(on_done)
        worker.error.connect(on_err)
        worker.start()

