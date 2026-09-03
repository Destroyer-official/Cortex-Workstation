"""Tab for registry cleaner tab in Cortex Cleaner GUI."""

from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import QThread, Signal, Qt
import platform

from .base_tab import BaseTab
from cortex_unified.system_tools.registry_cleaner import RegistryCleaner

class RegistryScanWorker(QThread):
    """RegistryScanWorker."""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, config):
        """__init__."""
        super().__init__()
        self.cleaner = RegistryCleaner(config)
        """__init__."""
        """__init__."""
        
    def run(self):
        """run."""
        try:
            items = self.cleaner.scan_orphaned_entries()
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
    """RegistryScanWorker class."""
    """RegistryScanWorker class."""

class RegistryCleanWorker(QThread):
    """RegistryCleanWorker."""
    finished = Signal(int)
    error = Signal(str)
    
    def __init__(self, config, paths_to_remove: List[str]):
        """__init__."""
        super().__init__()
        self.cleaner = RegistryCleaner(config)
        self.paths_to_remove = paths_to_remove
        """__init__."""
        """__init__."""
        
    def run(self):
        """run."""
        try:
            # Always backup first
            self.cleaner.backup_registry()
            
            count = 0
            for path in self.paths_to_remove:
                if self.cleaner.remove_orphaned_entry(path):
                    count += 1
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
    """RegistryCleanWorker class."""
    """RegistryCleanWorker class."""

class RegistryCleanerTab(BaseTab):
    """Tab for registry cleaner tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """__init__."""
        super().__init__(config, logger, safety_manager)
        self.cleaner = RegistryCleaner(config)
        self.worker = None
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Create the registry cleaner tab."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        warning_label = QLabel('Registry cleaning can be dangerous. Use with caution. Backups are automatic.')
        warning_label.setStyleSheet('QLabel { color: red; font-weight: bold; }')
        layout.addWidget(warning_label)
        
        if platform.system().lower() != "windows":
            layout.addWidget(QLabel("Registry operations are restricted to Windows nodes. Module disabled."))
            layout.addStretch()
            return
            
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.scan_registry_button = QPushButton('Scan Registry')
        self.scan_registry_button.clicked.connect(self.scan_registry)
        self.scan_registry_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.scan_registry_button)
        
        self.clean_registry_button = QPushButton('Clean Registry')
        self.clean_registry_button.clicked.connect(self.clean_registry)
        self.clean_registry_button.setEnabled(False)
        self.clean_registry_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.clean_registry_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.clean_registry_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.registry_progress_bar = QProgressBar()
        self.registry_progress_bar.setVisible(False)
        self.registry_progress_bar.setRange(0, 0)
        self.registry_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.registry_progress_bar)
        
        self.registry_table = QTableWidget()
        self.registry_table.setColumnCount(3)
        self.registry_table.setHorizontalHeaderLabels(['Registry SubKey', 'Hive', 'Target Program'])
        self.registry_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.registry_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.registry_table)

    def scan_registry(self):
        """scan_registry."""
        if self.worker and self.worker.isRunning():
            return
            
        self.registry_progress_bar.setVisible(True)
        self.scan_registry_button.setEnabled(False)
        self.clean_registry_button.setEnabled(False)
        self.registry_table.setRowCount(0)
        
        self.worker = RegistryScanWorker(self.config)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
        """scan_registry."""
        """scan_registry."""

    def _on_scan_finished(self, items: List[Dict]):
        """_on_scan_finished."""
        self.registry_progress_bar.setVisible(False)
        self.scan_registry_button.setEnabled(True)
        
        if items:
            self.clean_registry_button.setEnabled(True)
            
        self.registry_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.registry_table.setItem(row, 0, QTableWidgetItem(item.get("path", "")))
            self.registry_table.setItem(row, 1, QTableWidgetItem(item.get("hive", "")))
            self.registry_table.setItem(row, 2, QTableWidgetItem(item.get("name", "")))
        """_on_scan_finished."""
        """_on_scan_finished."""

    def _on_error(self, err_msg):
        """_on_error."""
        self.registry_progress_bar.setVisible(False)
        self.scan_registry_button.setEnabled(True)
        self.clean_registry_button.setEnabled(self.registry_table.rowCount() > 0)
        
        self.logger.error(f"Registry operation failed: {err_msg}")
        QMessageBox.critical(self, "Error", f"Registry Error:\n{err_msg}")
        """_on_error."""
        """_on_error."""

    def clean_registry(self):
        """clean_registry."""
        if self.worker and self.worker.isRunning(): return
        
        items_to_clean = []
        for row in range(self.registry_table.rowCount()):
            path = self.registry_table.item(row, 0).text()
            if path: items_to_clean.append(path)
            
        if not items_to_clean: return
        
        reply = QMessageBox.question(self, "Confirm Registry Purge", "Are you sure you want to sweep these entries? A backup will be generated first.")
        if reply == QMessageBox.StandardButton.Yes:
            self.registry_progress_bar.setVisible(True)
            self.scan_registry_button.setEnabled(False)
            self.clean_registry_button.setEnabled(False)
            
            self.worker = RegistryCleanWorker(self.config, items_to_clean)
            self.worker.finished.connect(self._on_clean_finished)
            self.worker.error.connect(self._on_error)
            self.worker.start()
        """clean_registry."""
        """clean_registry."""

    def _on_clean_finished(self, count):
        """_on_clean_finished."""
        self.registry_progress_bar.setVisible(False)
        self.scan_registry_button.setEnabled(True)
        
        QMessageBox.information(self, "Cleanup Complete", f"Successfully cleaned {count} orphaned registry entries. Backup generated.")
        self.registry_table.setRowCount(0)
        self.clean_registry_button.setEnabled(False)
        """_on_clean_finished."""
        """_on_clean_finished."""
