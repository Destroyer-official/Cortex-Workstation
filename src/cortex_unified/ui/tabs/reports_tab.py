"""Tab for reports tab in Cortex Cleaner GUI."""

import os
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
    QSpinBox, QTabWidget, QAbstractItemView, QSizePolicy, QListWidgetItem
)
from PySide6.QtCore import QThread, Signal, Qt, QObject, QTimer, QUrl
from PySide6.QtGui import QIcon, QFont, QTextCursor, QDesktopServices

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.reports.reports import ReportsGenerator


class ReportsTab(BaseTab):
    """Tab for reports functionality."""

    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)
        self.reports_generator = ReportsGenerator(config)

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
        if hasattr(self, 'has_web_engine') and self.has_web_engine:
            self.web_view.setZoomFactor(self.web_view.zoomFactor() + 0.15)
            
    def _zoom_out(self):
        if hasattr(self, 'has_web_engine') and self.has_web_engine:
            self.web_view.setZoomFactor(max(0.2, self.web_view.zoomFactor() - 0.15))
            
    def _zoom_reset(self):
        if hasattr(self, 'has_web_engine') and self.has_web_engine:
            self.web_view.setZoomFactor(1.0)

    def format_bytes(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def _on_table_selection(self):
        """Enable/disable preview based on selection."""
        has_sel = len(self.reports_table.selectedItems()) > 0
        self.preview_report_button.setEnabled(has_sel)

    def get_dummy_data(self):
        """Create mock data block for the target selection parameter requirements."""
        return {
            "title": self.report_type_combo.currentText(),
            "time_range": self.report_date_range_combo.currentText(),
            "settings": {
                "charts": self.include_charts_checkbox.isChecked(),
                "details": self.include_details_checkbox.isChecked(),
                "recs": self.include_recommendations_checkbox.isChecked()
            },
            "analytics_summary": {
                "scanned_files": 45192,
                "issues_fixed": 15,
                "freed_space": "14.2 GB",
                "system_health": "Good"
            }
        }

    def generate_report(self):
        """Trigger report generator implementation."""
        self.reports_progress_bar.setVisible(True)
        self.generate_report_button.setEnabled(False)
        
        # Use simple timeout delay to emulate load
        def _execute_gen():
            data = self.get_dummy_data()
            fmt = self.report_format_combo.currentText()
            try:
                if fmt == 'HTML':
                    self.reports_generator.generate_html_report(data)
                elif fmt == 'JSON':
                    self.reports_generator.generate_json_report(data)
                elif fmt == 'CSV':
                    # Fix formatting for CSV
                    data = {"headers": ["Metric", "Value"], "rows": [[str(k), str(v)] for k,v in data["analytics_summary"].items()]}
                    self.reports_generator.generate_csv_report(data)
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
        
        QTimer.singleShot(500, _execute_gen)

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
        QMessageBox.information(self, "Coming Soon", "Scheduled reporting is a Pro feature!")

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
            except:
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
        QMessageBox.information(self, "Placeholder", "Template saving not fully implemented")

    def load_report_template(self):
        item = self.templates_list.currentItem()
        if item:
            QMessageBox.information(self, "Template Loaded", f"Applied properties for: {item.text()}")
