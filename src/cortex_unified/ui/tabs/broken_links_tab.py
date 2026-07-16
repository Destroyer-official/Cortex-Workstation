"""Tab for broken links tab in Cortex Cleaner GUI."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QHeaderView, QListWidget, QRadioButton,
    QComboBox, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QSpinBox, QTabWidget, QAbstractItemView, QSizePolicy, QListWidgetItem
)
from PySide6.QtCore import QThread, Signal, Qt, QObject, QTimer
from PySide6.QtGui import QIcon, QFont, QTextCursor

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.analyzers.broken_link_detector import BrokenLinkDetector


class BrokenLinksWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, scan_path, scan_symlinks, scan_shortcuts, scan_registry):
        super().__init__()
        self.scan_path = scan_path
        self.scan_symlinks = scan_symlinks
        self.scan_shortcuts = scan_shortcuts
        self.scan_registry = scan_registry

    def run(self):
        """Run the broken links scan."""
        try:
            detector = BrokenLinkDetector()
            all_broken_links = []
            if self.scan_symlinks:
                symlinks = detector.scan_symlinks(self.scan_path)
                all_broken_links.extend(symlinks)
            if self.scan_shortcuts and detector.is_windows:
                shortcuts = detector.scan_windows_shortcuts(self.scan_path)
                all_broken_links.extend(shortcuts)
            if self.scan_registry and detector.is_windows and detector.has_winreg:
                registry_refs = detector.scan_registry_references()
                all_broken_links.extend(registry_refs)
            self.finished.emit(all_broken_links)
        except Exception as e:
            self.error.emit(str(e))


class BrokenLinksTab(BaseTab):
    """Tab for broken links tab functionality."""

    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        scan_group = QGroupBox('Scan Options')
        scan_layout = QVBoxLayout(scan_group)
        self.scan_symlinks_checkbox = QCheckBox('Scan for broken symlinks')
        self.scan_symlinks_checkbox.setChecked(True)
        scan_layout.addWidget(self.scan_symlinks_checkbox)
        
        self.scan_shortcuts_checkbox = QCheckBox('Scan for broken Windows shortcuts (.lnk files)')
        self.scan_shortcuts_checkbox.setChecked(True)
        scan_layout.addWidget(self.scan_shortcuts_checkbox)
        
        self.scan_registry_checkbox = QCheckBox('Scan for broken registry references (Windows only)')
        self.scan_registry_checkbox.setChecked(False)
        scan_layout.addWidget(self.scan_registry_checkbox)
        layout.addWidget(scan_group)
        
        repair_group = QGroupBox('Repair Options')
        repair_layout = QFormLayout(repair_group)
        self.enable_repair_checkbox = QCheckBox('Enable automatic repair')
        self.enable_repair_checkbox.setChecked(False)
        repair_layout.addRow(self.enable_repair_checkbox)
        
        self.confidence_threshold_spinbox = QSpinBox()
        self.confidence_threshold_spinbox.setRange(0, 100)
        self.confidence_threshold_spinbox.setValue(70)
        self.confidence_threshold_spinbox.setSuffix('%')
        repair_layout.addRow('Confidence threshold:', self.confidence_threshold_spinbox)
        
        self.create_backups_checkbox = QCheckBox('Create backups before repair')
        self.create_backups_checkbox.setChecked(True)
        repair_layout.addRow(self.create_backups_checkbox)
        layout.addWidget(repair_group)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel('Scan path:'))
        self.broken_links_path_edit = QLineEdit()
        self.broken_links_path_edit.setText(str(Path.home()))
        path_layout.addWidget(self.broken_links_path_edit)
        
        browse_button = QPushButton('Browse')
        browse_button.clicked.connect(self.browse_broken_links_path)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)
        
        button_layout = QHBoxLayout()
        
        self.broken_links_scan_button = QPushButton('Scan for Broken Links')
        self.broken_links_scan_button.clicked.connect(self.start_broken_links_scan)
        button_layout.addWidget(self.broken_links_scan_button)
        
        self.select_all_btn = QPushButton('Select All')
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        button_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton('Deselect All')
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setEnabled(False)
        button_layout.addWidget(self.deselect_all_btn)
        
        self.repair_selected_button = QPushButton('Repair Selected')
        self.repair_selected_button.clicked.connect(self.repair_selected_links)
        self.repair_selected_button.setEnabled(False)
        button_layout.addWidget(self.repair_selected_button)
        
        self.broken_links_export_button = QPushButton('Export Results')
        self.broken_links_export_button.clicked.connect(self.export_broken_links_results)
        self.broken_links_export_button.setEnabled(False)
        button_layout.addWidget(self.broken_links_export_button)
        
        layout.addLayout(button_layout)
        
        self.broken_links_progress_bar = QProgressBar()
        self.broken_links_progress_bar.setVisible(False)
        layout.addWidget(self.broken_links_progress_bar)
        
        results_group = QGroupBox('Broken Links Found')
        results_layout = QVBoxLayout(results_group)
        self.broken_links_summary_label = QLabel('No scan performed yet')
        results_layout.addWidget(self.broken_links_summary_label)
        
        self.broken_links_table = QTableWidget()
        self.broken_links_table.setColumnCount(7)
        self.broken_links_table.setHorizontalHeaderLabels(['Type', 'Path', 'Target', 'Confidence', 'Repairable', 'Size', 'Last Accessed'])
        self.broken_links_table.horizontalHeader().setStretchLastSection(True)
        self.broken_links_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.broken_links_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.broken_links_table.itemSelectionChanged.connect(self.on_broken_links_selection_changed)
        results_layout.addWidget(self.broken_links_table)
        layout.addWidget(results_group)
        
        if not sys.platform.startswith('win'):
            self.scan_shortcuts_checkbox.setEnabled(False)
            self.scan_shortcuts_checkbox.setChecked(False)
            self.scan_registry_checkbox.setEnabled(False)
            self.scan_registry_checkbox.setChecked(False)

    def select_all(self):
        self.broken_links_table.selectAll()
        
    def deselect_all(self):
        self.broken_links_table.clearSelection()

    def browse_broken_links_path(self):
        """Browse for broken links scan path."""
        path = QFileDialog.getExistingDirectory(self, 'Select Directory to Scan for Broken Links', self.broken_links_path_edit.text())
        if path:
            self.broken_links_path_edit.setText(path)

    def on_broken_links_selection_changed(self):
        """Handle broken links table selection changes."""
        has_sel = len(self.broken_links_table.selectedItems()) > 0
        self.repair_selected_button.setEnabled(has_sel)

    def start_broken_links_scan(self):
        """Start broken links scan via worker thread."""
        scan_path = self.broken_links_path_edit.text().strip()
        if not scan_path or not Path(scan_path).exists():
            QMessageBox.warning(self, 'Invalid Path', 'Please select a valid directory to scan.')
            return
            
        self.broken_links_scan_button.setEnabled(False)
        self.repair_selected_button.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.deselect_all_btn.setEnabled(False)
        self.broken_links_progress_bar.setVisible(True)
        self.broken_links_progress_bar.setRange(0, 0)
        self.broken_links_table.setRowCount(0)
        
        worker = BrokenLinksWorker(
            scan_path, 
            self.scan_symlinks_checkbox.isChecked(), 
            self.scan_shortcuts_checkbox.isChecked(), 
            self.scan_registry_checkbox.isChecked()
        )
        self.add_worker_thread(worker)
        
        worker.finished.connect(self.on_broken_links_scan_finished)
        worker.error.connect(self.on_broken_links_scan_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_worker_finished(self, worker):
        self.remove_worker_thread(worker)
        worker.deleteLater()

    def on_broken_links_scan_finished(self, results):
        """Handle broken links scan completion."""
        self.broken_links_scan_button.setEnabled(True)
        self.broken_links_progress_bar.setVisible(False)
        
        self.broken_links_results = results
        total_links = len(results)
        
        if total_links > 0:
            self.broken_links_export_button.setEnabled(True)
            self.select_all_btn.setEnabled(True)
            self.deselect_all_btn.setEnabled(True)
            
        repairable_count = sum((1 for link in results if link.is_repairable))
        high_confidence_count = sum((1 for link in results if link.confidence_score >= 0.7))
        summary_text = f'Found {total_links} broken links ({repairable_count} repairable, {high_confidence_count} high confidence)'
        self.broken_links_summary_label.setText(summary_text)
        
        self.broken_links_table.setRowCount(total_links)
        for row, link in enumerate(results):
            type_item = QTableWidgetItem(link.link_type.title())
            self.broken_links_table.setItem(row, 0, type_item)
            
            path_item = QTableWidgetItem(str(link.path))
            self.broken_links_table.setItem(row, 1, path_item)
            
            target_item = QTableWidgetItem(link.target)
            self.broken_links_table.setItem(row, 2, target_item)
            
            confidence_item = QTableWidgetItem(f'{link.confidence_score:.2f}')
            self.broken_links_table.setItem(row, 3, confidence_item)
            
            repairable_item = QTableWidgetItem('Yes' if link.is_repairable else 'No')
            self.broken_links_table.setItem(row, 4, repairable_item)
            
            size_item = QTableWidgetItem(f'{link.size:,} bytes')
            self.broken_links_table.setItem(row, 5, size_item)
            
            accessed_item = QTableWidgetItem(link.last_accessed.strftime('%Y-%m-%d %H:%M'))
            self.broken_links_table.setItem(row, 6, accessed_item)
            
        self.broken_links_table.resizeColumnsToContents()

    def on_broken_links_scan_error(self, error_message):
        """Handle broken links scan error."""
        self.broken_links_scan_button.setEnabled(True)
        self.broken_links_progress_bar.setVisible(False)
        QMessageBox.critical(self, 'Scan Error', f'Error during broken links scan:\n{error_message}')

    def repair_selected_links(self):
        """Repairs the specified nodes."""
        QMessageBox.information(self, "Repair Links", "Pro Feature: Intelligent recursive link repair is coming soon!")

    def export_broken_links_results(self):
        """Export broken links results to JSON."""
        if not hasattr(self, 'broken_links_results') or not self.broken_links_results:
            QMessageBox.warning(self, 'No Results', 'No broken links results to export.')
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, 'Export Broken Links Results', 'broken_links_results.json', 'JSON Files (*.json)')
        if not file_path:
            return
            
        try:
            import json
            from datetime import datetime
            export_data = {
                'scan_date': datetime.now().isoformat(),
                'scan_path': self.broken_links_path_edit.text(),
                'total_links': len(self.broken_links_results),
                'broken_links': []
            }
            for link in self.broken_links_results:
                link_data = {
                    'path': str(link.path),
                    'target': link.target,
                    'type': link.link_type,
                    'size': link.size,
                    'created': link.created.isoformat(),
                    'last_accessed': link.last_accessed.isoformat(),
                    'is_repairable': link.is_repairable,
                    'confidence_score': link.confidence_score,
                    'error_message': link.error_message
                }
                export_data['broken_links'].append(link_data)
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            QMessageBox.information(self, 'Export Complete', f'Results exported to:\n{file_path}')
        except Exception as e:
            QMessageBox.critical(self, 'Export Error', f'Error exporting results:\n{str(e)}')
