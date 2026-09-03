"""Tab for large files tab in Cortex Cleaner GUI."""

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
from PySide6.QtCore import QThread, Signal, Qt, QObject, QTimer
from PySide6.QtGui import QIcon, QFont, QTextCursor

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.core.scanner import Scanner
from cortex_unified.core.deleter import Deleter
from cortex_unified.analyzers.large_file_finder import LargeFileFinder

class LargeFileFinderWorker(QThread):
    """Finds large files above a size threshold off the GUI thread."""
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, config: Config, path: str, min_size_mb: int = 100):
        """Store the config, scan path, and minimum size in MB."""
        super().__init__()
        self.config = config
        self.path = path
        self.min_size_mb = min_size_mb
        """__init__."""
        """__init__."""

    def run(self):
        """Run the large file finding process."""
        try:
            finder = LargeFileFinder(self.config, self.path)
            large_files = finder.find_large_files(min_size_mb=self.min_size_mb)
            stats = finder.get_stats()
            self.finished.emit([large_files, stats])
        except Exception as e:
            self.error.emit(str(e))
    """LargeFileFinderWorker class."""
    """LargeFileFinderWorker class."""

class LargeFilesTab(BaseTab):
    """Tab for large files tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """Initialize the tab and call setup_ui."""
        super().__init__(config, logger, safety_manager)
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        path_group = QGroupBox('Target Path')
        path_layout = QHBoxLayout(path_group)
        path_layout.setContentsMargins(10, 10, 10, 10)
        
        self.large_files_path_input = QLineEdit()
        self.large_files_path_input.setPlaceholderText('Select directory to scan for large files...')
        self.large_files_path_input.setMinimumHeight(30)
        path_layout.addWidget(self.large_files_path_input)
        
        browse_button = QPushButton('Browse')
        browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.large_files_path_input))
        browse_button.setMinimumHeight(30)
        browse_button.setStyleSheet('QPushButton { padding: 5px 15px; }')
        path_layout.addWidget(browse_button)
        layout.addWidget(path_group)
        
        options_group = QGroupBox('Large Files Options')
        options_layout = QFormLayout(options_group)
        options_layout.setContentsMargins(10, 10, 10, 10)
        options_layout.setSpacing(10)
        
        self.min_size_spinbox = QSpinBox()
        self.min_size_spinbox.setRange(1, 10000)
        self.min_size_spinbox.setSuffix(' MB')
        self.min_size_spinbox.setValue(100)
        options_layout.addRow('Minimum Size:', self.min_size_spinbox)
        layout.addWidget(options_group)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.find_large_files_button = QPushButton('Find Large Files')
        self.find_large_files_button.clicked.connect(self.start_find_large_files)
        self.find_large_files_button.setMinimumHeight(35)
        self.find_large_files_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        buttons_layout.addWidget(self.find_large_files_button)

        self.select_all_btn = QPushButton('Select All')
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        buttons_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton('Deselect All')
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setEnabled(False)
        buttons_layout.addWidget(self.deselect_all_btn)
        
        self.delete_large_files_button = QPushButton('Delete Selected')
        self.delete_large_files_button.clicked.connect(self.delete_selected_large_files)
        self.delete_large_files_button.setEnabled(False)
        self.delete_large_files_button.setMinimumHeight(35)
        self.delete_large_files_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        buttons_layout.addWidget(self.delete_large_files_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.large_files_progress_bar = QProgressBar()
        self.large_files_progress_bar.setVisible(False)
        self.large_files_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.large_files_progress_bar)
        
        self.large_files_table = QTableWidget()
        self.large_files_table.setColumnCount(3)
        self.large_files_table.setHorizontalHeaderLabels(['File Path', 'Size', 'Last Modified'])
        self.large_files_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.large_files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.large_files_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.large_files_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.large_files_table)

    def _on_selection_changed(self):
        """Enable the delete button when table rows are selected."""
        has_sel = len(self.large_files_table.selectedItems()) > 0
        self.delete_large_files_button.setEnabled(has_sel)
        """_on_selection_changed."""
        """_on_selection_changed."""

    def select_all(self):
        """Select all rows in the large-files table."""
        self.large_files_table.selectAll()
        """select_all."""
        """select_all."""
        
    def deselect_all(self):
        """Clear the table's selection."""
        self.large_files_table.clearSelection()
        """deselect_all."""
        """deselect_all."""

    def start_find_large_files(self):
        """Start finding large files natively via Thread manager."""
        path = self.large_files_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, 'Warning', 'Please select a directory to scan for large files.')
            return
        
        try:
            normalized_path = Path(path).resolve()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Invalid path: {str(e)}')
            return
            
        if not normalized_path.exists():
            QMessageBox.critical(self, 'Error', 'Selected path does not exist.')
            return
            
        self.find_large_files_button.setEnabled(False)
        self.delete_large_files_button.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.deselect_all_btn.setEnabled(False)
        
        self.large_files_progress_bar.setVisible(True)
        self.large_files_progress_bar.setRange(0, 0)
        self.large_files_table.setRowCount(0)
        
        min_size_mb = self.min_size_spinbox.value()
        
        worker = LargeFileFinderWorker(self.config, str(normalized_path), min_size_mb)
        self.add_worker_thread(worker)
        
        worker.finished.connect(self.large_files_found)
        worker.error.connect(self.large_files_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_worker_finished(self, worker):
        """Unregister a finished worker thread and delete it."""
        self.remove_worker_thread(worker)
        worker.deleteLater()
        """_on_worker_finished."""
        """_on_worker_finished."""

    def large_files_found(self, result: list):
        """Fill the table with path/size/modified-time rows and enable actions."""
        large_files, stats = result
        self.find_large_files_button.setEnabled(True)
        self.large_files_progress_bar.setVisible(False)
        
        self.large_files = large_files
        self.large_files_table.setRowCount(len(large_files))
        
        for i, (filepath, size) in enumerate(large_files):
            try:
                stat = filepath.stat()
                modified_time = stat.st_mtime
                modified_str = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M')
            except (OSError, ValueError):
                modified_str = 'Unknown'
            size_str = self.format_bytes(size)
            
            self.large_files_table.setItem(i, 0, QTableWidgetItem(str(filepath)))
            self.large_files_table.setItem(i, 1, QTableWidgetItem(size_str))
            self.large_files_table.setItem(i, 2, QTableWidgetItem(modified_str))
            
        if len(large_files) > 0:
            self.select_all_btn.setEnabled(True)
            self.deselect_all_btn.setEnabled(True)
        """large_files_found."""
        """large_files_found."""

    def large_files_error(self, error: str):
        """Reset the find button and report the error."""
        self.logger.error(f'Large files error: {error}')
        self.find_large_files_button.setEnabled(True)
        self.large_files_progress_bar.setVisible(False)
        QMessageBox.critical(self, 'Error', f'An error occurred while finding large files:\n{error}')
        """large_files_error."""
        """large_files_error."""

    def delete_selected_large_files(self):
        """Confirm, then trash the selected large files via Deleter and rescan."""
        selected_ranges = self.large_files_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, 'Info', 'Please select files to delete.')
            return
            
        files_to_delete = []
        for range_ in selected_ranges:
            for row in range(range_.topRow(), range_.bottomRow() + 1):
                item = self.large_files_table.item(row, 0)
                if item:
                    file_path = Path(item.text())
                    files_to_delete.append(file_path)
                    
        if not files_to_delete:
            QMessageBox.information(self, 'Info', 'No files selected for deletion.')
            return
            
        reply = QMessageBox.warning(
            self, 'Confirm Deletion', 
            f'Delete {len(files_to_delete)} large files?\nThis action will move them to trash where possible.', 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return
            
        try:
            self.large_files_progress_bar.setVisible(True)
            deleter = Deleter(dry_run=False, use_trash=True)
            result = deleter.delete(files_to_delete, [])
            
            files_deleted = result.get('files_deleted', 0)
            errors = result.get('errors', [])
            message = f'Successfully deleted {files_deleted} large files.'
            if errors:
                message += f'\n{len(errors)} errors occurred.'
            
            self.large_files_progress_bar.setVisible(False)
            QMessageBox.information(self, 'Deletion Complete', message)
            
            self.start_find_large_files() # Refresh
        except Exception as e:
            self.large_files_progress_bar.setVisible(False)
            QMessageBox.critical(self, 'Deletion Error', f'Error deleting large files:\n{str(e)}')
        """delete_selected_large_files."""
        """delete_selected_large_files."""
