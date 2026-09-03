"""Tab for duplicates tab in Cortex Cleaner GUI."""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import time
import threading

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
from cortex_unified.analyzers.duplicate_finder import DuplicateFinder
from cortex_unified.core.utils import normalize_path

class DuplicateFinderWorker(QThread):
    """Runs duplicate-file detection (size grouping + hashing) off the GUI thread."""
    finished_scan = Signal(dict)
    error_occurred = Signal(str)
    status_updated = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, config: Config, path: str, hash_algorithm: str='md5'):
        """Store config, path, hash algorithm, and the poller run flag."""
        super().__init__()
        self.config = config
        self.path = path
        self.hash_algorithm = hash_algorithm
        self._is_running = True
        """__init__."""
        """__init__."""

    def run(self):
        """Find duplicates and emit finished_scan with {duplicates, stats} (or error_occurred)."""
        try:
            self.status_updated.emit("Grouping files by size...")
            self.finder = DuplicateFinder(self.config, self.path)
            self.finder.hash_algorithm = self.hash_algorithm
            
            # Start a background polling thread for live feedback
            def poll_progress():
                """Emit file-count status every 0.1s while the scan runs."""
                while self._is_running:
                    self.status_updated.emit(f"Scanned {self.finder.file_count} files...")
                    # Indeterminate progress animates naturally if we setRange(0,0) in the main thread
                    # we emit 0 just to satisfy signature requirements
                    self.progress_updated.emit(0)
                    time.sleep(0.1)
                """poll_progress."""
                """poll_progress."""

            t = threading.Thread(target=poll_progress)
            t.daemon = True
            t.start()

            duplicates = self.finder.find_duplicates()
            self._is_running = False
            
            # Wait for poll thread to finish securely
            t.join(timeout=0.2)
            
            stats = self.finder.get_stats()
            self.finished_scan.emit({'duplicates': duplicates, 'stats': stats})
        except Exception as e:
            self._is_running = False
            self.error_occurred.emit(str(e))
        """run."""
    """DuplicateFinderWorker class."""
    """DuplicateFinderWorker class."""


class DuplicatesTab(BaseTab):
    """Tab for finding and deleting duplicate files."""
    def __init__(self, config, logger, safety_manager):
        """Initialize the tab and empty the current duplicates cache."""
        super().__init__(config, logger, safety_manager)
        self.current_duplicates = {}
        """__init__."""
        """__init__."""
        
    def setup_ui(self):
        """Build the tab: path picker, hash/strategy options, and group/details splitter."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        path_group = QGroupBox('Target Path')
        path_layout = QHBoxLayout(path_group)
        path_layout.setContentsMargins(10, 10, 10, 10)
        
        self.duplicates_path_input = QLineEdit()
        self.duplicates_path_input.setPlaceholderText('Select directory to scan for duplicates...')
        self.duplicates_path_input.setMinimumHeight(30)
        path_layout.addWidget(self.duplicates_path_input)
        
        browse_button = QPushButton('Browse')
        browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.duplicates_path_input))
        browse_button.setMinimumHeight(30)
        browse_button.setStyleSheet('QPushButton { padding: 5px 15px; }')
        path_layout.addWidget(browse_button)
        layout.addWidget(path_group)
        
        options_group = QGroupBox('Duplicate Detection Options')
        options_layout = QFormLayout(options_group)
        options_layout.setContentsMargins(10, 10, 10, 10)
        options_layout.setSpacing(10)
        
        self.hash_algorithm_combo = QComboBox()
        self.hash_algorithm_combo.addItems(['md5', 'sha1', 'sha256'])
        self.hash_algorithm_combo.setCurrentText('md5')
        options_layout.addRow('Hash Algorithm:', self.hash_algorithm_combo)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(['keep_newest', 'keep_oldest', 'keep_largest', 'keep_smallest'])
        self.strategy_combo.setCurrentText('keep_newest')
        options_layout.addRow('Selection Strategy:', self.strategy_combo)
        layout.addWidget(options_group)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.find_duplicates_button = QPushButton('Find Duplicates')
        self.find_duplicates_button.clicked.connect(self.start_find_duplicates)
        self.find_duplicates_button.setMinimumHeight(35)
        self.find_duplicates_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        buttons_layout.addWidget(self.find_duplicates_button)

        self.select_all_btn = QPushButton('Select All')
        self.select_all_btn.clicked.connect(self.select_all_duplicates)
        self.select_all_btn.setMinimumHeight(35)
        buttons_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton('Deselect All')
        self.deselect_all_btn.clicked.connect(self.deselect_all_duplicates)
        self.deselect_all_btn.setMinimumHeight(35)
        buttons_layout.addWidget(self.deselect_all_btn)

        self.delete_duplicates_button = QPushButton('Delete Selected')
        self.delete_duplicates_button.clicked.connect(self.delete_selected_duplicates)
        self.delete_duplicates_button.setEnabled(False)
        self.delete_duplicates_button.setMinimumHeight(35)
        self.delete_duplicates_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        buttons_layout.addWidget(self.delete_duplicates_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.status_label = QLabel("Ready to scan")
        layout.addWidget(self.status_label)

        self.duplicates_progress_bar = QProgressBar()
        self.duplicates_progress_bar.setVisible(False)
        self.duplicates_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.duplicates_progress_bar)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.duplicates_tree = QTreeWidget()
        self.duplicates_tree.setHeaderLabels(['Duplicate Groups', 'File Count', 'Size'])
        self.duplicates_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        splitter.addWidget(self.duplicates_tree)
        
        self.duplicates_details = QTextEdit()
        self.duplicates_details.setReadOnly(True)
        splitter.addWidget(self.duplicates_details)
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        """setup_ui."""
        """setup_ui."""
        # Note: Do not override layout manually to prevent QLayout errors

    def start_find_duplicates(self):
        """Validate the path and launch the DuplicateFinderWorker."""
        path = self.duplicates_path_input.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(self, 'Invalid Path', 'Please select a valid directory to scan for duplicates.')
            return
            
        self.logger.info(f"Starting duplicate search in {path}")
        self.find_duplicates_button.setEnabled(False)
        self.delete_duplicates_button.setEnabled(False)
        self.duplicates_progress_bar.setVisible(True)
        self.duplicates_progress_bar.setRange(0, 0) # Indeterminate mode for hash polling
        self.duplicates_tree.clear()
        
        alg = self.hash_algorithm_combo.currentText()
        worker = DuplicateFinderWorker(self.config, path, alg)
        self.add_worker_thread(worker)
        
        worker.status_updated.connect(self.status_label.setText)
        worker.finished_scan.connect(self.duplicates_found)
        worker.error_occurred.connect(self.duplicates_error)
        worker.finished.connect(lambda: self.operation_finished(worker))
        worker.start()
        """start_find_duplicates."""
        """start_find_duplicates."""
        
    def duplicates_found(self, result):
        """Populate the groups tree, pre-checking files per the chosen strategy."""
        self.logger.info("Duplicates found")
        duplicates = result.get('duplicates', {})
        self.current_duplicates = duplicates
        stats = result.get('stats', {})
        
        self.duplicates_tree.clear()
        
        # Format the bytes_saved string
        bytes_saved = stats.get('bytes_saved_if_deleted', 0)
        saved_str = f"{bytes_saved / (1024*1024):.2f} MB" if bytes_saved > 0 else "0 MB"
        
        self.status_label.setText(f"Found {stats.get('duplicate_groups', 0)} groups with {stats.get('total_duplicates', 0)} duplicates. Potential savings: {saved_str}")
        
        # Instantiate a detached duplicate finder purely to access the strategy filtering mechanism
        temp_finder = DuplicateFinder(self.config, "")
        temp_finder.duplicates = duplicates
        files_to_delete = temp_finder.auto_select_duplicates(strategy=self.strategy_combo.currentText())
        delete_set = set(str(f) for f in files_to_delete)
        
        for hash_val, paths in duplicates.items():
            if not paths: continue
            
            try:
                group_size = paths[0].stat().st_size
                size_str = f"{group_size / 1024:.2f} KB"
            except (OSError, ValueError):
                size_str = "Unknown"
                
            group_item = QTreeWidgetItem(self.duplicates_tree)
            group_item.setText(0, f"Hash: {hash_val[:8]}...")
            group_item.setText(1, str(len(paths)))
            group_item.setText(2, size_str)
            # Make grouping item checkable so you can toggle children, or just expandable
            group_item.setExpanded(True)
            
            for path in paths:
                child = QTreeWidgetItem(group_item)
                child.setText(0, str(path))
                child.setText(1, "File")
                child.setText(2, size_str)
                
                # Render checkbox
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if str(path) in delete_set:
                    child.setCheckState(0, Qt.CheckState.Checked)
                else:
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    
        self.delete_duplicates_button.setEnabled(len(duplicates) > 0)
        """duplicates_found."""
        """duplicates_found."""
        
    def select_all_duplicates(self):
        """Check every file row across all duplicate groups."""
        self._set_tree_states(Qt.CheckState.Checked)
        """select_all_duplicates."""
        """select_all_duplicates."""
        
    def deselect_all_duplicates(self):
        """Uncheck every file row across all duplicate groups."""
        self._set_tree_states(Qt.CheckState.Unchecked)
        """deselect_all_duplicates."""
        """deselect_all_duplicates."""
        
    def _set_tree_states(self, state):
        """Apply a check state to every child row in the groups tree."""
        root = self.duplicates_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group = root.child(i)
            # Optional: handle group level checkboxes here if we add them later
            for j in range(group.childCount()):
                child = group.child(j)
                child.setCheckState(0, state)
        """_set_tree_states."""
        """_set_tree_states."""

    def duplicates_error(self, error):
        """Log and report the duplicate-scan error."""
        self.logger.error(f"Error finding duplicates: {error}")
        QMessageBox.critical(self, 'Error', f'An error occurred: {error}')
        self.status_label.setText(f"Error: {error}")
        """duplicates_error."""
        """duplicates_error."""
        
    def delete_selected_duplicates(self):
        """Confirm, then recycle the checked duplicates via Deleter and rescan."""
        self.logger.info("Deleting selected duplicates")
        selected_files = []
        
        root = self.duplicates_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group = root.child(i)
            for j in range(group.childCount()):
                child = group.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    selected_files.append(Path(child.text(0)))
                    
        if not selected_files:
            QMessageBox.warning(self, "No Selection", "Please check items to delete.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Permanently delete {len(selected_files)} duplicate files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.find_duplicates_button.setEnabled(False)
        self.delete_duplicates_button.setEnabled(False)
        self.progress_bar_start_delete()
        
        deleter = Deleter(dry_run=False, use_trash=True)
        try:
            result = deleter.delete(selected_files, [])
            files_deleted = result.get('files_deleted', 0)
            errors = result.get('errors', [])
            
            msg = f"Deleted {files_deleted} files."
            if errors:
                msg += f"\\nEncountered {len(errors)} errors."
            QMessageBox.information(self, "Deletion Complete", msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete files: {e}")
            
        # Rescan to update
        self.start_find_duplicates()
        """delete_selected_duplicates."""
        """delete_selected_duplicates."""
        
    def progress_bar_start_delete(self):
        """Show Deleting status and the indeterminate progress bar."""
        self.status_label.setText("Deleting files...")
        self.duplicates_progress_bar.setVisible(True)
        self.duplicates_progress_bar.setRange(0, 0)
        """progress_bar_start_delete."""
        """progress_bar_start_delete."""
        
    def operation_finished(self, worker):
        """Hide progress, re-enable the find button, and reap the worker."""
        self.duplicates_progress_bar.setVisible(False)
        self.find_duplicates_button.setEnabled(True)
        self.remove_worker_thread(worker)
        worker.deleteLater()
        """operation_finished."""
    """DuplicatesTab class."""
    """DuplicatesTab class."""
