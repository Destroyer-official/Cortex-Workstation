"""Empty files cleaner tab for Cortex Cleaner GUI."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

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

class EmptyFilesWorker(QThread):
    """Worker thread for empty files operations."""

    progress_updated = Signal(int)
    status_updated = Signal(str)
    scan_completed = Signal(list, list, dict)
    delete_completed = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, config, path, operation="scan", files_to_delete=None, dirs_to_delete=None):
        """Store config, path, operation type, and the delete file/dir lists."""
        super().__init__()
        self.config = config
        self.path = path
        self.operation = operation
        self.files_to_delete = files_to_delete or []
        self.dirs_to_delete = dirs_to_delete or []
        """__init__."""
        """__init__."""

    def run(self):
        """Scan for or delete empty items (emits scan_completed/delete_completed, or error_occurred)."""
        try:
            if self.operation == "scan":
                self.status_updated.emit(
                    "Scanning for empty files and directories...")
                scanner = Scanner(self.config, self.path, enable_checkpoints=True)
                
                # Polling thread for live progress
                import time
                import threading
                
                def poll_progress():
                    """Relay scanner percentage and current path every 0.1s until the scan ends."""
                    while not getattr(scanner, '_scan_finished', False):
                        prog = scanner.get_scan_progress()
                        if prog:
                            self.progress_updated.emit(min(100, int(prog.percentage)))
                            current = Path(prog.current_path).name if prog.current_path else ""
                            self.status_updated.emit(f"Scanning: {current}")
                        time.sleep(0.1)
                    """poll_progress."""
                    """poll_progress."""
                
                t = threading.Thread(target=poll_progress)
                t.daemon = True
                t.start()
                
                try:
                    empty_files, empty_dirs = scanner.scan()
                finally:
                    scanner._scan_finished = True
                    self.progress_updated.emit(100)
                    
                stats = scanner.get_stats()
                self.scan_completed.emit(empty_files, empty_dirs, stats)

            elif self.operation == "delete":
                self.status_updated.emit(
                    "Deleting empty files and directories...")
                deleter = Deleter(dry_run=False, use_trash=True)
                result = deleter.delete(
                    self.files_to_delete, self.dirs_to_delete)
                self.delete_completed.emit(result)

        except Exception as e:
            self.error_occurred.emit(str(e))
        """run."""
        """run."""

class EmptyFilesTab(BaseTab):
    """Tab for empty files cleaning functionality."""

    def __init__(self, config, logger, safety_manager):
        """Initialize the tab and clear the empty file/dir caches."""
        super().__init__(config, logger, safety_manager)
        self.empty_files = []
        self.empty_dirs = []
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Empty Files and Directories Cleaner")
        title.setStyleSheet(
        "font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Path selection
        path_group = QGroupBox("Scan Location")
        path_layout = QHBoxLayout(path_group)

        self.path_input = QLineEdit()
        self.path_input.setText(str(Path.home()))
        self.path_input.setObjectName("empty_files_path_input")
        path_layout.addWidget(self.path_input)

        browse_button = QPushButton("Browse")
        browse_button.setObjectName("empty_files_browse_button")
        browse_button.clicked.connect(self.browse_path)
        path_layout.addWidget(browse_button)

        layout.addWidget(path_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)

        self.dry_run_checkbox = QCheckBox("Dry Run (Preview only)")
        self.dry_run_checkbox.setChecked(True)
        self.dry_run_checkbox.setObjectName("empty_files_dry_run")
        options_layout.addRow(self.dry_run_checkbox)

        self.trash_checkbox = QCheckBox("Move to Trash")
        self.trash_checkbox.setChecked(True)
        self.trash_checkbox.setObjectName("empty_files_trash")
        options_layout.addRow(self.trash_checkbox)

        self.age_spinbox = QSpinBox()
        self.age_spinbox.setRange(0, 365)
        self.age_spinbox.setSuffix(" days")
        self.age_spinbox.setObjectName("empty_files_age")
        options_layout.addRow("Minimum age:", self.age_spinbox)

        layout.addWidget(options_group)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.scan_button = QPushButton("Scan")
        self.scan_button.setObjectName("empty_files_scan_button")
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.scan_button)

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setObjectName("empty_files_delete_button")
        self.delete_button.clicked.connect(self.start_delete)
        self.delete_button.setEnabled(False)
        self.delete_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.delete_button)

        layout.addLayout(buttons_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready to scan")
        self.status_label.setObjectName("empty_files_status")
        layout.addWidget(self.status_label)

        # Selection buttons
        selection_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_items)
        selection_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)
        selection_layout.addWidget(self.deselect_all_btn)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setObjectName("empty_files_results")
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(
        ["Select", "Type", "Path", "Size"])

        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.results_table)

        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("empty_files_summary")
        layout.addWidget(self.summary_label)

    def setup_tooltips(self):
        """Set up tooltips."""
        self.path_input.setToolTip(
            "Directory path to scan for empty files and folders")
        self.dry_run_checkbox.setToolTip(
            "Preview what would be deleted without actually deleting")
        self.trash_checkbox.setToolTip(
            "Move files to trash instead of permanent deletion")
        self.age_spinbox.setToolTip(
            "Only consider files/folders older than specified days")
        self.scan_button.setToolTip(
            "Start scanning for empty files and directories")
        self.delete_button.setToolTip(
            "Delete selected empty files and directories")

    def browse_path(self):
        """Browse for directory to scan."""
        path = QFileDialog.getExistingDirectory(
            self, "Select Directory to Scan")
        if path:
            self.path_input.setText(path)

    def start_scan(self):
        """Validate the path and launch the scan worker."""
        path = self.path_input.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "Invalid Path",
                                "Please select a valid directory to scan.")
            return

        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.results_table.setRowCount(0)
        self.empty_files = []
        self.empty_dirs = []

        worker = EmptyFilesWorker(self.config, path, "scan")
        self.add_worker_thread(worker)

        worker.status_updated.connect(self.status_label.setText)
        worker.progress_updated.connect(self.progress_bar.setValue)
        worker.scan_completed.connect(self.scan_completed)
        worker.error_occurred.connect(self.handle_error)
        worker.finished.connect(lambda: self.operation_finished(worker))

        worker.start()
        """start_scan."""
        """start_scan."""

    def start_delete(self):
        """Start deleting selected items."""
        selected_files = []
        selected_dirs = []

        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                item_type = self.results_table.item(row, 1).text()
                path = Path(self.results_table.item(row, 2).text())

                if item_type == "File":
                    selected_files.append(path)
                else:
                    selected_dirs.append(path)

        if not selected_files and not selected_dirs:
            QMessageBox.warning(self, "No Selection",
                                "Please select items to delete.")
            return

        # Confirm deletion
        total_items = len(selected_files) + len(selected_dirs)
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Delete {total_items} empty items?\n"
            f"Files: {len(selected_files)}, Directories: {len(selected_dirs)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        worker = EmptyFilesWorker(
            self.config, "", "delete", selected_files, selected_dirs)
        self.add_worker_thread(worker)

        worker.status_updated.connect(self.status_label.setText)
        worker.progress_updated.connect(self.progress_bar.setValue)
        worker.delete_completed.connect(self.delete_completed)
        worker.error_occurred.connect(self.handle_error)
        worker.finished.connect(lambda: self.operation_finished(worker))

        worker.start()

    def scan_completed(self, empty_files, empty_dirs, stats):
        """Handle scan completion."""
        self.empty_files = empty_files
        self.empty_dirs = empty_dirs

        # Populate results table
        total_items = len(empty_files) + len(empty_dirs)
        self.results_table.setRowCount(total_items)

        row = 0

        # Add files
        for file_path in empty_files:
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.results_table.setCellWidget(row, 0, checkbox)
            self.results_table.setItem(row, 1, QTableWidgetItem("File"))
            self.results_table.setItem(
                row, 2, QTableWidgetItem(str(file_path)))
            self.results_table.setItem(row, 3, QTableWidgetItem("0 B"))
            row += 1

        # Add directories
        for dir_path in empty_dirs:
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.results_table.setCellWidget(row, 0, checkbox)
            self.results_table.setItem(row, 1, QTableWidgetItem("Directory"))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(dir_path)))
            self.results_table.setItem(row, 3, QTableWidgetItem("0 B"))
            row += 1

        self.summary_label.setText(
            f"Found {len(empty_files)} empty files and {len(empty_dirs)} empty directories"
        )

        self.status_label.setText("Scan completed")
        self.delete_button.setEnabled(total_items > 0)

    def select_all_items(self):
        """Check every row checkbox in the results table."""
        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
        """select_all_items."""
        """select_all_items."""

    def deselect_all_items(self):
        """Uncheck every row checkbox in the results table."""
        for row in range(self.results_table.rowCount()):
            checkbox = self.results_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
        """deselect_all_items."""
        """deselect_all_items."""

    def delete_completed(self, result):
        """Handle deletion completion."""
        files_deleted = result.get('files_deleted', 0)
        dirs_deleted = result.get('dirs_deleted', 0)
        errors = result.get('errors', [])

        message = f"Deleted {files_deleted} files and {dirs_deleted} directories."
        if errors:
            message += f"\n{len(errors)} errors occurred."

        QMessageBox.information(self, "Deletion Complete", message)

        # Refresh scan
        self.start_scan()

    def handle_error(self, error_message):
        """Show the error in a dialog and the status label."""
        QMessageBox.critical(
            self, "Error", f"An error occurred: {error_message}")
        self.status_label.setText(f"Error: {error_message}")
        """handle_error."""
        """handle_error."""

    def operation_finished(self, worker):
        """Handle operation completion."""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)

        self.remove_worker_thread(worker)
        worker.deleteLater()
