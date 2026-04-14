"""Temporary files cleaner tab for Deep Cleaner GUI."""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QHeaderView
)
from PySide6.QtCore import QThread, Signal, Qt

from ...analyzers.temp_cleaner import TempCleaner
from .base_tab import BaseTab
from ...deleter import Deleter


class TempCleanerWorker(QThread):
    """Worker thread for temp file cleaning operations."""
    
    progress_updated = Signal(int)
    status_updated = Signal(str)
    scan_completed = Signal(list, dict)
    clean_completed = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, config, operation="scan", files_to_clean=None):
        super().__init__()
        self.config = config
        self.operation = operation
        self.files_to_clean = files_to_clean or []
        self.temp_cleaner = None
    
    def run(self):
        """Run the temp cleaning operation."""
        try:
            self.temp_cleaner = TempCleaner(self.config)
            
            if self.operation == "scan":
                self.status_updated.emit("Scanning for temporary files...")
                temp_files = self.temp_cleaner.find_temp_files()
                stats = self.temp_cleaner.get_stats()
                self.scan_completed.emit(temp_files, stats)
                
            elif self.operation == "clean":
                self.status_updated.emit("Cleaning temporary files...")
                deleter = Deleter(dry_run=False, use_trash=True)
                result = deleter.delete(self.files_to_clean, [])
                self.clean_completed.emit(result)
                
        except Exception as e:
            self.error_occurred.emit(str(e))


class TempCleanerTab(BaseTab):
    """Tab for temporary files cleaning functionality."""
    
    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)
        self.temp_files = []
        self.worker_thread = None
        
        self.setup_ui()
        self.setup_tooltips()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Temporary Files Cleaner")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Options group
        options_group = QGroupBox("Scan Options")
        options_layout = QFormLayout(options_group)
        
        # Scan locations
        self.scan_system_temp = QCheckBox("System temp directories")
        self.scan_system_temp.setChecked(True)
        self.scan_system_temp.setObjectName("scan_system_temp")
        options_layout.addRow(self.scan_system_temp)
        
        self.scan_user_temp = QCheckBox("User temp directories")
        self.scan_user_temp.setChecked(True)
        self.scan_user_temp.setObjectName("scan_user_temp")
        options_layout.addRow(self.scan_user_temp)
        
        self.scan_browser_cache = QCheckBox("Browser cache files")
        self.scan_browser_cache.setChecked(True)
        self.scan_browser_cache.setObjectName("scan_browser_cache")
        options_layout.addRow(self.scan_browser_cache)
        
        self.scan_app_temp = QCheckBox("Application temp files")
        self.scan_app_temp.setChecked(True)
        self.scan_app_temp.setObjectName("scan_app_temp")
        options_layout.addRow(self.scan_app_temp)
        
        # Age filter
        self.older_than_days = QLineEdit("0")
        self.older_than_days.setObjectName("older_than_days")
        options_layout.addRow("Only files older than (days):", self.older_than_days)
        
        layout.addWidget(options_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("Scan for Temp Files")
        self.scan_button.setObjectName("scan_temp_button")
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.scan_button)
        
        self.clean_button = QPushButton("Clean Selected")
        self.clean_button.setObjectName("clean_temp_button")
        self.clean_button.clicked.connect(self.start_clean)
        self.clean_button.setEnabled(False)
        self.clean_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.clean_button)
        
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to scan for temporary files")
        self.status_label.setObjectName("temp_status_label")
        layout.addWidget(self.status_label)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setObjectName("temp_results_table")
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Select", "File Path", "Size", "Type"])
        
        # Configure table
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.results_table)
        
        # Summary label
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("temp_summary_label")
        layout.addWidget(self.summary_label)
    
    def setup_tooltips(self):
        """Set up tooltips for UI elements."""
        self.scan_system_temp.setToolTip("Scan system-wide temporary directories like %TEMP% and /tmp")
        self.scan_user_temp.setToolTip("Scan user-specific temporary directories")
        self.scan_browser_cache.setToolTip("Scan browser cache and temporary internet files")
        self.scan_app_temp.setToolTip("Scan application-specific temporary files")
        self.older_than_days.setToolTip("Only consider files older than specified days (0 = all files)")
        self.scan_button.setToolTip("Start scanning for temporary files")
        self.clean_button.setToolTip("Clean selected temporary files")
        self.results_table.setToolTip("Results of temporary file scan - check items to select for cleaning")
    
    def start_scan(self):
        """Start scanning for temporary files."""
        if self.worker_thread and self.worker_thread.isRunning():
            return
        
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Clear previous results
        self.results_table.setRowCount(0)
        self.temp_files = []
        
        # Start worker thread
        self.worker_thread = TempCleanerWorker(self.config, "scan")
        self.worker_thread.progress_updated.connect(self.progress_bar.setValue)
        self.worker_thread.status_updated.connect(self.status_label.setText)
        self.worker_thread.scan_completed.connect(self.scan_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.operation_finished)
        self.worker_thread.start()
    
    def start_clean(self):
        """Start cleaning selected temporary files."""
        if self.worker_thread and self.worker_thread.isRunning():
            return
        
        # Get selected files
        selected_files = []
        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                file_path = self.results_table.item(row, 1).text()
                selected_files.append(Path(file_path))
        
        if not selected_files:
            QMessageBox.warning(self, "No Selection", "Please select files to clean.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Cleaning",
            f"Are you sure you want to clean {len(selected_files)} temporary files?\n"
            "Files will be moved to trash.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # Start cleaning
        self.worker_thread = TempCleanerWorker(self.config, "clean", selected_files)
        self.worker_thread.status_updated.connect(self.status_label.setText)
        self.worker_thread.clean_completed.connect(self.clean_completed)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.finished.connect(self.operation_finished)
        self.worker_thread.start()
    
    def scan_completed(self, temp_files, stats):
        """Handle scan completion."""
        self.temp_files = temp_files
        
        # Populate results table
        self.results_table.setRowCount(len(temp_files))
        
        for i, file_path in enumerate(temp_files):
            # Checkbox for selection
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.results_table.setCellWidget(i, 0, checkbox)
            
            # File path
            self.results_table.setItem(i, 1, QTableWidgetItem(str(file_path)))
            
            # File size
            try:
                size = file_path.stat().st_size
                size_str = self.format_bytes(size)
            except (OSError, AttributeError):
                size_str = "Unknown"
            self.results_table.setItem(i, 2, QTableWidgetItem(size_str))
            
            # File type
            file_type = self.get_temp_file_type(file_path)
            self.results_table.setItem(i, 3, QTableWidgetItem(file_type))
        
        # Update summary
        total_size = stats.get('total_size_human', 'Unknown')
        file_count = stats.get('temp_files_found', len(temp_files))
        self.summary_label.setText(f"Found {file_count} temporary files, total size: {total_size}")
        
        self.status_label.setText("Scan completed successfully")
        self.clean_button.setEnabled(len(temp_files) > 0)
    
    def clean_completed(self, result):
        """Handle cleaning completion."""
        files_deleted = result.get('files_deleted', 0)
        errors = result.get('errors', [])
        
        message = f"Successfully cleaned {files_deleted} temporary files."
        if errors:
            message += f"\n{len(errors)} errors occurred."
        
        QMessageBox.information(self, "Cleaning Complete", message)
        
        # Refresh the scan to show updated results
        self.start_scan()
    
    def handle_error(self, error_message):
        """Handle errors from worker thread."""
        QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")
        self.status_label.setText(f"Error: {error_message}")
    
    def operation_finished(self):
        """Handle operation completion."""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)
        
        if self.worker_thread:
            self.worker_thread.deleteLater()
            self.worker_thread = None
    
    def get_temp_file_type(self, file_path):
        """Determine the type of temporary file."""
        path_str = str(file_path).lower()
        
        if 'temp' in path_str or 'tmp' in path_str:
            return "System Temp"
        elif 'cache' in path_str:
            return "Cache"
        elif any(browser in path_str for browser in ['chrome', 'firefox', 'edge', 'safari']):
            return "Browser Temp"
        elif file_path.suffix.lower() in ['.tmp', '.temp', '.cache']:
            return "Temp File"
        else:
            return "Other"
    
    def format_bytes(self, bytes_value):
        """Format bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"