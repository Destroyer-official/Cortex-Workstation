"""Tab for reports tab in Cortex Cleaner GUI."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QHeaderView, QListWidget, QRadioButton,
    QComboBox, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QSpinBox, QTabWidget, QAbstractItemView, QSizePolicy, QListWidgetItem,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import QThread, Signal, Qt, QObject, QTimer, QUrl
from PySide6.QtGui import QIcon, QFont, QTextCursor, QDesktopServices

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.reports.reports import ReportsGenerator
from cortex_unified.scheduler.scheduler import TaskScheduler
from cortex_unified.licensing import Feature, allowed


class ReportsTab(BaseTab):
    """Tab for reports functionality."""

    def __init__(self, config, logger, safety_manager):
        """__init__."""
        super().__init__(config, logger, safety_manager)
        self.reports_generator = ReportsGenerator(config)
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Create the reports tab."""
        main_layout = QVBoxLayout(self)
        
        self.main_tab_widget = QTabWidget()
        main_layout.addWidget(self.main_tab_widget)
        
        # --- TAB 1: Generator ---
        self.generator_tab = QWidget()
        layout = QVBoxLayout(self.generator_tab)
        
        title = QLabel('Reports & Analytics')
        title.setStyleSheet('font-size: 16px; font-weight: bold; margin: 10px;')
        layout.addWidget(title)
        
        generation_group = QGroupBox('Report Generation')
        generation_layout = QFormLayout(generation_group)
        
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            'System Analysis Report', 'Disk Usage Report', 
            'Cleanup Summary Report', 'Performance Report', 
            'Security Audit Report', 'Scheduled Tasks Report', 'Custom Report'
        ])
        generation_layout.addRow('Report Type:', self.report_type_combo)
        
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(['HTML', 'JSON', 'CSV', 'Text'])
        generation_layout.addRow('Format:', self.report_format_combo)
        
        self.report_date_range_combo = QComboBox()
        self.report_date_range_combo.addItems([
            'Last 24 Hours', 'Last Week', 'Last Month', 
            'Last 3 Months', 'All Time', 'Custom Range'
        ])
        generation_layout.addRow('Date Range:', self.report_date_range_combo)
        
        self.include_charts_checkbox = QCheckBox('Include charts and graphs')
        self.include_charts_checkbox.setChecked(True)
        generation_layout.addRow(self.include_charts_checkbox)
        
        self.include_details_checkbox = QCheckBox('Include detailed statistics')
        self.include_details_checkbox.setChecked(True)
        generation_layout.addRow(self.include_details_checkbox)
        
        self.include_recommendations_checkbox = QCheckBox('Include recommendations')
        self.include_recommendations_checkbox.setChecked(True)
        generation_layout.addRow(self.include_recommendations_checkbox)
        
        layout.addWidget(generation_group)
        
        actions_layout = QHBoxLayout()
        self.generate_report_button = QPushButton('Generate Report')
        self.generate_report_button.clicked.connect(self.generate_report)
        self.generate_report_button.setMinimumHeight(35)
        self.generate_report_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        actions_layout.addWidget(self.generate_report_button)
        
        self.preview_report_button = QPushButton('Open Selected Report')
        self.preview_report_button.clicked.connect(self.preview_report)
        self.preview_report_button.setMinimumHeight(35)
        self.preview_report_button.setEnabled(False)
        actions_layout.addWidget(self.preview_report_button)
        
        self.schedule_report_button = QPushButton('Schedule Report (Pro)')
        self.schedule_report_button.clicked.connect(self.schedule_report)
        self.schedule_report_button.setMinimumHeight(35)
        if allowed(Feature.AUTO_CLEAN_RULES):
            self.schedule_report_button.setEnabled(True)
            self.schedule_report_button.setToolTip(
                'Register a recurring HTML report with the OS scheduler.')
        else:
            self.schedule_report_button.setEnabled(False)
            self.schedule_report_button.setToolTip(
                'Scheduled reporting requires an upgrade to the Pro tier '
                '(or higher).')
        actions_layout.addWidget(self.schedule_report_button)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        self.reports_progress_bar = QProgressBar()
        self.reports_progress_bar.setVisible(False)
        self.reports_progress_bar.setRange(0, 0) # Indeterminate
        layout.addWidget(self.reports_progress_bar)
        
        recent_group = QGroupBox('Recent Reports')
        recent_layout = QVBoxLayout(recent_group)
        
        refresh_reports_button = QPushButton('Refresh Activity Log')
        refresh_reports_button.clicked.connect(self.refresh_reports_list)
        recent_layout.addWidget(refresh_reports_button)
        
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(4)
        self.reports_table.setHorizontalHeaderLabels(['Report Name', 'Generated', 'Size', 'Type'])
        self.reports_table.horizontalHeader().setStretchLastSection(True)
        self.reports_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.reports_table.itemSelectionChanged.connect(self._on_table_selection)
        recent_layout.addWidget(self.reports_table)
        
        layout.addWidget(recent_group)
        
        templates_group = QGroupBox('Report Templates')
        templates_layout = QVBoxLayout(templates_group)
        templates_buttons_layout = QHBoxLayout()
        
        self.save_template_button = QPushButton('Save as Template')
        self.save_template_button.clicked.connect(self.save_report_template)
        templates_buttons_layout.addWidget(self.save_template_button)
        
        self.load_template_button = QPushButton('Load Template')
        self.load_template_button.clicked.connect(self.load_report_template)
        templates_buttons_layout.addWidget(self.load_template_button)
        
        templates_buttons_layout.addStretch()
        templates_layout.addLayout(templates_buttons_layout)
        
        self.templates_list = QListWidget()
        self.templates_list.setMaximumHeight(100)
        self.templates_list.addItem("Default Daily Report")
        self.templates_list.addItem("Monthly Security Log")
        templates_layout.addWidget(self.templates_list)
        
        layout.addWidget(templates_group)
        self.main_tab_widget.addTab(self.generator_tab, 'Report Generator')
        
        # --- TAB 2: Preview ---
        self.preview_tab = QWidget()
        preview_layout = QVBoxLayout(self.preview_tab)
        
        preview_tools = QHBoxLayout()
        self.lbl_preview_title = QLabel("No report loaded.")
        self.lbl_preview_title.setStyleSheet("font-weight: bold;")
        preview_tools.addWidget(self.lbl_preview_title)
        preview_tools.addStretch()
        
        self.btn_zoom_in = QPushButton("🔍 Zoom In")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        self.btn_zoom_out = QPushButton("🔍 Zoom Out")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        self.btn_zoom_reset = QPushButton("🔄 Reset Zoom")
        self.btn_zoom_reset.clicked.connect(self._zoom_reset)
        
        preview_tools.addWidget(self.btn_zoom_in)
        preview_tools.addWidget(self.btn_zoom_out)
        preview_tools.addWidget(self.btn_zoom_reset)
        preview_layout.addLayout(preview_tools)
        
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.web_view = QWebEngineView()
            preview_layout.addWidget(self.web_view)
            self.has_web_engine = True
        except ImportError:
             self.has_web_engine = False
             self.fallback_text = QTextEdit()
             self.fallback_text.setReadOnly(True)
             preview_layout.addWidget(self.fallback_text)
             
        self.main_tab_widget.addTab(self.preview_tab, 'HTML Preview')
        
        # Finally populate reports without risking cross-class AttributeError
        QTimer.singleShot(100, self.refresh_reports_list)
        
    def _zoom_in(self):
        """_zoom_in."""
        if hasattr(self, 'has_web_engine') and self.has_web_engine:
            self.web_view.setZoomFactor(self.web_view.zoomFactor() + 0.15)
        """_zoom_in."""
        """_zoom_in."""
            
    def _zoom_out(self):
        """_zoom_out."""
        if hasattr(self, 'has_web_engine') and self.has_web_engine:
            self.web_view.setZoomFactor(max(0.2, self.web_view.zoomFactor() - 0.15))
        """_zoom_out."""
        """_zoom_out."""
            
    def _zoom_reset(self):
        """_zoom_reset."""
        if hasattr(self, 'has_web_engine') and self.has_web_engine:
            self.web_view.setZoomFactor(1.0)
        """_zoom_reset."""
        """_zoom_reset."""

    def format_bytes(self, size):
        """format_bytes."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
        """format_bytes."""
        """format_bytes."""

    def _on_table_selection(self):
        """Enable/disable preview based on selection."""
        has_sel = len(self.reports_table.selectedItems()) > 0
        self.preview_report_button.setEnabled(has_sel)

    def get_live_analytics_data(self) -> Dict[str, Any]:
        """Collect live dynamic system analytics and telemetry for report generation."""
        import shutil
        import psutil

        # Live system drive capacity
        sys_drive = os.environ.get("SystemDrive", "C:") + "\\"
        try:
            total_b, used_b, free_b = shutil.disk_usage(sys_drive)
            free_gb = free_b / (1024 ** 3)
            used_gb = used_b / (1024 ** 3)
        except Exception:
            free_gb, used_gb = 0.0, 0.0

        # Live memory utilization
        try:
            vm = psutil.virtual_memory()
            mem_pct = vm.percent
        except Exception:
            mem_pct = 0.0

        # Inspect real temp directory to report cleanable items and size
        temp_dir = os.environ.get("TEMP", os.environ.get("TMP", ""))
        scanned_count = 0
        cleanable_bytes = 0
        if temp_dir and os.path.isdir(temp_dir):
            try:
                with os.scandir(temp_dir) as it:
                    for entry in it:
                        try:
                            scanned_count += 1
                            if entry.is_file(follow_symlinks=False):
                                cleanable_bytes += entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            continue
            except OSError:
                pass

        freed_str = self._format_size(cleanable_bytes) if cleanable_bytes > 0 else "0 B"
        health_status = "Good" if mem_pct < 85 else "High Load"

        return {
            "title": self.report_type_combo.currentText(),
            "time_range": self.report_date_range_combo.currentText(),
            "settings": {
                "charts": self.include_charts_checkbox.isChecked(),
                "details": self.include_details_checkbox.isChecked(),
                "recs": self.include_recommendations_checkbox.isChecked(),
            },
            "analytics_summary": {
                "scanned_files": scanned_count,
                "cleanable_temp_space": freed_str,
                "system_drive_free_gb": f"{free_gb:.1f} GB",
                "system_drive_used_gb": f"{used_gb:.1f} GB",
                "memory_utilization": f"{mem_pct:.1f}%",
                "system_health": health_status,
            },
        }

    def get_dummy_data(self) -> Dict[str, Any]:
        """Backward-compatible alias for get_live_analytics_data."""
        return self.get_live_analytics_data()

    def generate_report(self):
        """Generate dynamic analytical report from live system telemetry."""
        self.reports_progress_bar.setVisible(True)
        self.generate_report_button.setEnabled(False)

        try:
            data = self.get_live_analytics_data()
            fmt = self.report_format_combo.currentText()
            if fmt == 'HTML':
                self.reports_generator.generate_html_report(data)
            elif fmt == 'JSON':
                self.reports_generator.generate_json_report(data)
            elif fmt == 'CSV':
                data_csv = {"headers": ["Metric", "Value"], "rows": [[str(k), str(v)] for k, v in data["analytics_summary"].items()]}
                self.reports_generator.generate_csv_report(data_csv)
            else:
                self.reports_generator.generate_text_report(data)

            if fmt == 'HTML':
                reports = self.reports_generator.list_reports()
                if reports:
                    latest = sorted(reports, key=lambda x: str(x.get('modified', '')), reverse=True)[0]
                    file_path = latest['path']
                    if hasattr(self, 'has_web_engine') and self.has_web_engine:
                        self.web_view.setUrl(QUrl.fromLocalFile(file_path))
                        self.lbl_preview_title.setText(f"Previewing: {Path(file_path).name}")
                        self.main_tab_widget.setCurrentWidget(self.preview_tab)

            QMessageBox.information(self, "Success", f"Report generated successfully format: {fmt}")
        except Exception as e:
            self.logger.error(f"Report generation error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate report: {e}")
        finally:
            self.reports_progress_bar.setVisible(False)
            self.generate_report_button.setEnabled(True)

    def preview_report(self):
        """Open the highlighted report file manually."""
        row = self.reports_table.currentRow()
        if row < 0:
            return
            
        file_path_item = self.reports_table.item(row, 0)
        file_path = file_path_item.toolTip()
        
        try:
            if not Path(file_path).exists():
                QMessageBox.warning(self, "Missing", "The report file no longer exists.")
                return
            
            # If HTML, load directly into the responsive preview tab
            if str(file_path).lower().endswith('.html'):
                if hasattr(self, 'has_web_engine') and self.has_web_engine:
                    self.web_view.setUrl(QUrl.fromLocalFile(file_path))
                    self.lbl_preview_title.setText(f"Previewing: {Path(file_path).name}")
                    self.main_tab_widget.setCurrentWidget(self.preview_tab)
                    return
                elif hasattr(self, 'fallback_text'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.fallback_text.setHtml(f.read())
                        self.lbl_preview_title.setText(f"Previewing (Basic View): {Path(file_path).name}")
                        self.main_tab_widget.setCurrentWidget(self.preview_tab)
                        return
                    except Exception:
                        pass
                        
            # Fallback for non-HTML or missing web engine
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not launch file: {e}")

    def schedule_report(self):
        """Register a recurring HTML report job with the OS scheduler (Pro)."""
        if not allowed(Feature.AUTO_CLEAN_RULES):
            QMessageBox.warning(
                self, "Pro Feature",
                "Scheduled reporting requires an upgrade to the Pro tier.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('Schedule Report')
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        frequency_combo = QComboBox()
        frequency_combo.addItems(['Daily', 'Weekly', 'Monthly'])
        form.addRow('Frequency:', frequency_combo)
        format_label = QLabel('Format: HTML')
        form.addRow(format_label)
        layout.addLayout(form)
        note = QLabel(
            'A scheduled task will run the Cortex Cleaner CLI '
            "('generate-report --type html') at 02:00 with the chosen "
            'frequency.')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        frequency = frequency_combo.currentText().lower()
        command = (
            f'"{sys.executable}" -m cortex_unified.cli.cli '
            'generate-report --type html --name "Scheduled Report"'
        )
        scheduler = TaskScheduler(self.config)
        ok = scheduler.create_scheduled_task(
            'CortexCleaner ScheduledReport', command, frequency)

        if ok:
            QMessageBox.information(
                self, 'Scheduled',
                f'A {frequency} HTML report task was registered with the '
                f'OS scheduler:\n{command}')
        else:
            QMessageBox.warning(
                self, 'Scheduling Failed',
                'Could not create the scheduled task. On Windows this may '
                'require administrator rights.')

    def refresh_reports_list(self):
        """Update reports from directory polling."""
        reports = self.reports_generator.list_reports()
        self.reports_table.setRowCount(len(reports))
        
        for i, rep in enumerate(reports):
            # Name
            name_item = QTableWidgetItem(rep["name"])
            name_item.setToolTip(rep["path"]) # Store absolute path silently here
            self.reports_table.setItem(i, 0, name_item)
            
            # Generated
            try:
                dt_obj = datetime.fromisoformat(rep["modified"])
                dt_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                dt_str = str(rep["modified"])
            self.reports_table.setItem(i, 1, QTableWidgetItem(dt_str))
            
            # Size 
            size_str = self.format_bytes(rep.get("size_bytes", 0))
            self.reports_table.setItem(i, 2, QTableWidgetItem(size_str))
            
            # Extension/Type
            ext = str(rep.get("extension", "")).replace('.', '').upper()
            if not ext: ext = "TEXT"
            self.reports_table.setItem(i, 3, QTableWidgetItem(ext))

    def save_report_template(self):
        """Save current reporting settings to a reusable JSON template."""
        from PySide6.QtWidgets import QInputDialog
        import json
        name, ok = QInputDialog.getText(self, "Save Template", "Template Name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        template_data = {
            "type": self.report_type_combo.currentText(),
            "format": self.report_format_combo.currentText(),
            "date_range": self.report_date_range_combo.currentText(),
            "charts": self.include_charts_checkbox.isChecked(),
            "details": self.include_details_checkbox.isChecked(),
            "recommendations": self.include_recommendations_checkbox.isChecked(),
        }
        templates_dir = Path.home() / ".cortex"
        templates_dir.mkdir(parents=True, exist_ok=True)
        template_file = templates_dir / "report_templates.json"
        existing = {}
        if template_file.exists():
            try:
                existing = json.loads(template_file.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        existing[name] = template_data
        template_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        if not self.templates_list.findItems(name, Qt.MatchFlag.MatchExactly):
            self.templates_list.addItem(name)
        QMessageBox.information(self, "Template Saved", f"Saved template '{name}' successfully.")

    def load_report_template(self):
        """Load and apply saved report template settings."""
        import json
        item = self.templates_list.currentItem()
        if not item:
            return
        name = item.text()
        template_file = Path.home() / ".cortex" / "report_templates.json"
        if template_file.exists():
            try:
                existing = json.loads(template_file.read_text(encoding="utf-8"))
                if name in existing:
                    data = existing[name]
                    if "type" in data:
                        idx = self.report_type_combo.findText(data["type"])
                        if idx >= 0:
                            self.report_type_combo.setCurrentIndex(idx)
                    if "format" in data:
                        idx = self.report_format_combo.findText(data["format"])
                        if idx >= 0:
                            self.report_format_combo.setCurrentIndex(idx)
                    if "date_range" in data:
                        idx = self.report_date_range_combo.findText(data["date_range"])
                        if idx >= 0:
                            self.report_date_range_combo.setCurrentIndex(idx)
                    if "charts" in data:
                        self.include_charts_checkbox.setChecked(bool(data["charts"]))
                    if "details" in data:
                        self.include_details_checkbox.setChecked(bool(data["details"]))
                    if "recommendations" in data:
                        self.include_recommendations_checkbox.setChecked(bool(data["recommendations"]))
                    QMessageBox.information(self, "Template Loaded", f"Applied properties for: {name}")
                    return
            except Exception as e:
                self.logger.error(f"Failed to load template: {e}")
        QMessageBox.information(self, "Template Loaded", f"Applied properties for: {name}")
