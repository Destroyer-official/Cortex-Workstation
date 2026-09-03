"""Tab for package manager tab in Cortex Cleaner GUI."""

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
try:
    from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
except ImportError:
    class PackageManagerCleaner:
        """PackageManagerCleaner fallback class."""
        def __init__(self, *args, **kwargs):
            """Accept any arguments; fallback stub does nothing."""
            pass
        def detect_package_managers(self):
            """Report no package managers (fallback stub)."""
            return {}
        def scan_caches(self):
            """Report no caches found (fallback stub)."""
            return []
        def cleanup_caches(self):
            """Report no cleanup results (fallback stub)."""
            return {}

class PMSearchWorker(QThread):
    """Detects installed package managers off the GUI thread."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config):
        """Store the config used to build the cleaner."""
        super().__init__()
        self.config = config
        """__init__."""

    def run(self):
        """Detect package managers (emits finished with them, or error)."""
        try:
            cleaner = PackageManagerCleaner(self.config)
            managers = cleaner.detect_package_managers()
            self.finished.emit(managers)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
    """PMSearchWorker class."""

class PMScanWorker(QThread):
    """Scans package-manager/project caches off the GUI thread."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config, managers: dict, target_folders: List[str], 
                 keep_recent: int, orphaned: bool, include_python: bool):
        """Store config, manager flags, target folders, retention, and scope flags."""
        super().__init__()
        self.config = config
        self.managers = managers
        self.target_folders = target_folders
        self.keep_recent = keep_recent
        self.orphaned = orphaned
        self.include_python = include_python
        """__init__."""

    def run(self):
        """Scan system or project caches (emits finished with {resources, stats}, or error)."""
        try:
            cleaner = PackageManagerCleaner(self.config)
            
            # Determine what to scan
            if self.target_folders and self.include_python:
                # Scan selected folders for Python caches
                resources = cleaner.scan_caches(
                    target_folders=self.target_folders,
                    include_python_projects=True,
                    keep_recent_days=self.keep_recent
                )
            else:
                # Scan default package manager caches
                resources = cleaner.scan_caches(
                    keep_recent_days=self.keep_recent
                )
            
            stats = cleaner.get_stats()
            self.finished.emit({"resources": resources, "stats": stats})
        except Exception as e:
            self.error.emit(str(e))
        """run."""
    """PMScanWorker class."""

class PMCleanWorker(QThread):
    """Cleans scanned cache resources (optionally dry-run) off the GUI thread."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config, resources: list, dry_run: bool):
        """Store the config, resources to clean, and dry-run flag."""
        super().__init__()
        self.config = config
        self.resources = resources
        self.dry_run = dry_run
        """__init__."""

    def run(self):
        """Clean the caches (emits finished with a results dict, or error)."""
        try:
            cleaner = PackageManagerCleaner(self.config)
            results = cleaner.cleanup_caches(self.resources, dry_run=self.dry_run)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
    """PMCleanWorker class."""

class PackageManagerTab(BaseTab):
    """Tab for package manager tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """Initialize the tab and call setup_ui."""
        super().__init__(config, logger, safety_manager)
        """__init__."""

    def setup_ui(self):
        """Create the Package Manager tab with tabs for different scan modes."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Main tab widget
        self.mode_tabs = QTabWidget()
        main_layout.addWidget(self.mode_tabs)
        
        # Tab 1: system package managers
        tab1_widget = QWidget()
        tab1_layout = QVBoxLayout(tab1_widget)
        
        # Package Manager Selection
        pm_group = QGroupBox('System Package Managers to Clean')
        pm_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        pm_layout = QVBoxLayout(pm_group)
        
        self.pm_pip_checkbox = QCheckBox('✓ pip (Python)')
        self.pm_pip_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_pip_checkbox)
        
        self.pm_npm_checkbox = QCheckBox('✓ npm (Node.js)')
        self.pm_npm_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_npm_checkbox)
        
        self.pm_yarn_checkbox = QCheckBox('yarn (Node.js)')
        pm_layout.addWidget(self.pm_yarn_checkbox)
        
        self.pm_conda_checkbox = QCheckBox('conda (Python)')
        pm_layout.addWidget(self.pm_conda_checkbox)
        
        self.pm_system_checkbox = QCheckBox('System Package Manager')
        pm_layout.addWidget(self.pm_system_checkbox)
        
        tab1_layout.addWidget(pm_group)
        
        # Detection Button
        detect_layout = QHBoxLayout()
        self.pm_detect_button = QPushButton('🔍 Detect Available Package Managers')
        self.pm_detect_button.setMinimumHeight(40)
        self.pm_detect_button.clicked.connect(self.detect_package_managers)
        detect_layout.addWidget(self.pm_detect_button)
        tab1_layout.addLayout(detect_layout)
        
        self.pm_detect_status = QLabel("Click 'Detect Available Package Managers'")
        self.pm_detect_status.setStyleSheet("color: #888; font-style: italic;")
        tab1_layout.addWidget(self.pm_detect_status)
        
        tab1_layout.addStretch()
        self.mode_tabs.addTab(tab1_widget, "📦 System Package Managers")
        
        # Tab 2: project folder cleanup
        tab2_widget = QWidget()
        tab2_layout = QVBoxLayout(tab2_widget)
        
        # Folder Selection Group
        folder_group = QGroupBox('Select Project Folders to Scan')
        folder_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        folder_layout = QVBoxLayout(folder_group)
        
        # Folder List
        folder_list_label = QLabel("Selected Folders:")
        folder_list_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        folder_layout.addWidget(folder_list_label)
        
        self.pm_folders_list = QListWidget()
        self.pm_folders_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.pm_folders_list.setMinimumHeight(150)
        folder_layout.addWidget(self.pm_folders_list)
        
        # Folder Buttons
        folder_button_layout = QHBoxLayout()
        
        self.pm_add_folder_button = QPushButton('➕ Add Folder')
        self.pm_add_folder_button.setMinimumHeight(35)
        self.pm_add_folder_button.clicked.connect(self.add_folder_to_scan)
        folder_button_layout.addWidget(self.pm_add_folder_button)
        
        self.pm_remove_folder_button = QPushButton('➖ Remove Selected')
        self.pm_remove_folder_button.setMinimumHeight(35)
        self.pm_remove_folder_button.clicked.connect(self.remove_selected_folder)
        folder_button_layout.addWidget(self.pm_remove_folder_button)
        
        self.pm_clear_folders_button = QPushButton('🗑️ Clear All')
        self.pm_clear_folders_button.setMinimumHeight(35)
        self.pm_clear_folders_button.clicked.connect(self.clear_all_folders)
        folder_button_layout.addWidget(self.pm_clear_folders_button)
        
        folder_layout.addLayout(folder_button_layout)
        tab2_layout.addWidget(folder_group)
        
        # Cache Detection Options
        cache_group = QGroupBox('Python Cache Types to Clean')
        cache_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        cache_layout = QVBoxLayout(cache_group)
        
        self.pm_scan_python_checkbox = QCheckBox('✓ __pycache__ (Python bytecode)')
        self.pm_scan_python_checkbox.setChecked(True)
        cache_layout.addWidget(self.pm_scan_python_checkbox)
        
        self.pm_scan_egg_checkbox = QCheckBox('✓ .egg-info (Egg metadata)')
        self.pm_scan_egg_checkbox.setChecked(True)
        cache_layout.addWidget(self.pm_scan_egg_checkbox)
        
        self.pm_scan_dist_checkbox = QCheckBox('✓ .dist-info (Dist metadata)')
        self.pm_scan_dist_checkbox.setChecked(True)
        cache_layout.addWidget(self.pm_scan_dist_checkbox)
        
        self.pm_scan_pytest_checkbox = QCheckBox('✓ .pytest_cache')
        self.pm_scan_pytest_checkbox.setChecked(True)
        cache_layout.addWidget(self.pm_scan_pytest_checkbox)
        
        self.pm_scan_mypy_checkbox = QCheckBox('✓ .mypy_cache')
        self.pm_scan_mypy_checkbox.setChecked(True)
        cache_layout.addWidget(self.pm_scan_mypy_checkbox)
        
        tab2_layout.addWidget(cache_group)
        tab2_layout.addStretch()
        self.mode_tabs.addTab(tab2_widget, "📁 Project Folders")
        
        # Options shared by both tabs
        options_group = QGroupBox('Cleanup Options')
        options_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 10px; }")
        options_layout = QFormLayout(options_group)
        
        self.pm_keep_recent_spinbox = QSpinBox()
        self.pm_keep_recent_spinbox.setRange(0, 365)
        self.pm_keep_recent_spinbox.setValue(7)
        self.pm_keep_recent_spinbox.setSuffix(' days')
        options_layout.addRow('Keep cache files newer than:', self.pm_keep_recent_spinbox)
        
        self.pm_orphaned_checkbox = QCheckBox('Include orphaned packages')
        options_layout.addRow(self.pm_orphaned_checkbox)
        
        self.pm_dry_run_checkbox = QCheckBox('Dry Run (Preview Only - RECOMMENDED)')
        self.pm_dry_run_checkbox.setChecked(True)
        self.pm_dry_run_checkbox.setStyleSheet("QCheckBox { font-weight: bold; color: #d4860c; }")
        options_layout.addRow(self.pm_dry_run_checkbox)
        
        main_layout.addWidget(options_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.pm_scan_button = QPushButton('🔍 Scan for Caches')
        self.pm_scan_button.setMinimumHeight(45)
        self.pm_scan_button.setStyleSheet("QPushButton { font-weight: bold; background-color: #0078d4; color: white; border-radius: 4px; }")
        self.pm_scan_button.clicked.connect(self.start_pm_scan)
        button_layout.addWidget(self.pm_scan_button)
        
        self.pm_cleanup_button = QPushButton('🧹 Clean Selected Caches')
        self.pm_cleanup_button.setMinimumHeight(45)
        self.pm_cleanup_button.setStyleSheet("QPushButton { font-weight: bold; background-color: #d4860c; color: white; border-radius: 4px; } QPushButton:disabled { background-color: #999; }")
        self.pm_cleanup_button.clicked.connect(self.start_pm_cleanup)
        self.pm_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.pm_cleanup_button)
        
        main_layout.addLayout(button_layout)
        
        # Progress bar
        self.pm_progress_bar = QProgressBar()
        self.pm_progress_bar.setVisible(False)
        self.pm_progress_bar.setStyleSheet("QProgressBar { border: 1px solid #ccc; border-radius: 4px; text-align: center; }")
        main_layout.addWidget(self.pm_progress_bar)
        
        # Results section
        results_group = QGroupBox('Scan Results')
        results_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        results_layout = QVBoxLayout(results_group)
        
        self.pm_summary_label = QLabel("Results will appear here after scanning")
        self.pm_summary_label.setStyleSheet("font-weight: bold; color: #0078d4;")
        results_layout.addWidget(self.pm_summary_label)
        
        self.pm_table = QTableWidget()
        self.pm_table.setColumnCount(5)
        self.pm_table.setHorizontalHeaderLabels(['Name', 'Type', 'Path', 'Size', 'Files'])
        self.pm_table.horizontalHeader().setStretchLastSection(True)
        self.pm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pm_table.setMinimumHeight(200)
        results_layout.addWidget(self.pm_table)
        
        main_layout.addWidget(results_group)
        
        # State
        self.pm_folders: List[str] = []
        self.pm_resources: List[Dict] = []

    def detect_package_managers(self):
        """Launch the detection worker and show busy state."""
        self.pm_summary_label.setText("Detecting Package Managers...")
        self.pm_progress_bar.setVisible(True)
        self.pm_progress_bar.setRange(0, 0)
        self.pm_detect_button.setEnabled(False)
        
        worker = PMSearchWorker(self.config)
        self.add_worker_thread(worker)
        worker.finished.connect(self._on_detect_finished)
        worker.error.connect(self._on_detect_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()
        """detect_package_managers."""

    def _on_detect_finished(self, managers):
        """List detected manager names, or report none found."""
        self.pm_progress_bar.setVisible(False)
        self.pm_detect_button.setEnabled(True)
        
        # managers is a list of PackageManager objects
        msg = []
        if isinstance(managers, list):
            for mgr in managers:
                mgr_name = getattr(mgr, 'name', 'unknown')
                msg.append(mgr_name.upper())
        
        if msg:
            self.pm_detect_status.setText(f"✓ Detected: {', '.join(msg)}")
            self.pm_detect_status.setStyleSheet("color: #107c10; font-weight: bold;")
        else:
            self.pm_detect_status.setText("✗ No compatible package managers found on system.")
            self.pm_detect_status.setStyleSheet("color: #d13438; font-weight: bold;")
        """_on_detect_finished."""

    def _on_detect_error(self, err):
        """Reset the detect button and warn about the failure."""
        self.pm_progress_bar.setVisible(False)
        self.pm_detect_button.setEnabled(True)
        QMessageBox.warning(self, "Detection Failed", str(err))
        """_on_detect_error."""
    
    def add_folder_to_scan(self):
        """Append a chosen folder to the scan list if not already present."""
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder to Scan')
        if folder:
            if folder not in self.pm_folders:
                self.pm_folders.append(folder)
                self.pm_folders_list.addItem(folder)
            else:
                QMessageBox.information(self, "Folder Already Added", f"{folder} is already in the list.")
        """add_folder_to_scan."""
    
    def remove_selected_folder(self):
        """Remove the selected folder from the scan list."""
        current = self.pm_folders_list.currentRow()
        if current >= 0:
            self.pm_folders.pop(current)
            self.pm_folders_list.takeItem(current)
    
    def clear_all_folders(self):
        """Clear all folders from the scan list."""
        reply = QMessageBox.question(
            self, "Clear All Folders",
            "Remove all folders from the scan list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.pm_folders.clear()
            self.pm_folders_list.clear()

    def start_pm_scan(self):
        # Determine which tab is active
        """Collect mode/manager options and launch the cache scan worker."""
        if self.mode_tabs.currentIndex() == 0:
            # System Package Managers tab
            target_folders = []
        else:
            # Project Folders tab
            target_folders = self.pm_folders.copy()
        
        self.pm_progress_bar.setVisible(True)
        self.pm_progress_bar.setRange(0, 0)
        self.pm_scan_button.setEnabled(False)
        self.pm_cleanup_button.setEnabled(False)
        self.pm_table.setRowCount(0)
        
        managers = {
            "pip": self.pm_pip_checkbox.isChecked(),
            "npm": self.pm_npm_checkbox.isChecked(),
            "yarn": self.pm_yarn_checkbox.isChecked(),
            "conda": self.pm_conda_checkbox.isChecked(),
            "system": self.pm_system_checkbox.isChecked()
        }
        
        worker = PMScanWorker(
            self.config,
            managers,
            target_folders,
            self.pm_keep_recent_spinbox.value(),
            self.pm_orphaned_checkbox.isChecked(),
            self.pm_scan_python_checkbox.isChecked()
        )
        self.add_worker_thread(worker)
        
        worker.finished.connect(self._on_scan_finished)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()
        """start_pm_scan."""

    def _on_scan_finished(self, data):
        """Fill the results table and enable cleanup when caches were found."""
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        
        self.pm_resources = data.get("resources", [])
        self.pm_table.setRowCount(len(self.pm_resources))
        
        total_size = 0
        for i, res in enumerate(self.pm_resources):
            # Handle both dict and object resources
            if isinstance(res, dict):
                name = res.get('name', 'Unknown')
                cache_type = res.get('type', 'Unknown')
                path = res.get('path', '')
                size = res.get('size', 0)
                files = res.get('file_count', 0)
            else:
                name = getattr(res, 'name', 'Unknown')
                cache_type = getattr(res, 'type', 'Unknown')
                path = getattr(res, 'path', '')
                size = getattr(res, 'size', 0)
                files = getattr(res, 'file_count', 0)
            
            total_size += size
            
            self.pm_table.setItem(i, 0, QTableWidgetItem(name))
            self.pm_table.setItem(i, 1, QTableWidgetItem(cache_type))
            self.pm_table.setItem(i, 2, QTableWidgetItem(path))
            self.pm_table.setItem(i, 3, QTableWidgetItem(self.format_bytes(size)))
            self.pm_table.setItem(i, 4, QTableWidgetItem(str(files)))
        
        self.pm_summary_label.setText(f"Found {len(self.pm_resources)} cache locations: {self.format_bytes(total_size)} total")
        if total_size > 0:
            self.pm_cleanup_button.setEnabled(True)
        """_on_scan_finished."""

    def _on_scan_error(self, err):
        """Reset the scan button and warn about the scan failure."""
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        QMessageBox.warning(self, "Scan Error", str(err))
        """_on_scan_error."""

    def start_pm_cleanup(self):
        """Confirm, then launch the cleanup worker (dry-run aware)."""
        if not self.pm_resources:
            QMessageBox.warning(self, "No Caches", "No caches to clean. Run 'Scan' first.")
            return
        
        dry_run = self.pm_dry_run_checkbox.isChecked()
        action_text = "preview" if dry_run else "PERMANENTLY DELETE"
        
        reply = QMessageBox.warning(
            self, "Confirm Cleanup",
            f"Are you sure you want to {action_text} {len(self.pm_resources)} cache location(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.pm_cleanup_button.setEnabled(False)
        self.pm_scan_button.setEnabled(False)
        self.pm_progress_bar.setVisible(True)
        self.pm_progress_bar.setRange(0, 0)
        
        worker = PMCleanWorker(self.config, self.pm_resources, dry_run=dry_run)
        self.add_worker_thread(worker)
        worker.finished.connect(self._on_clean_finished)
        worker.error.connect(self._on_clean_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()
        """start_pm_cleanup."""

    def _on_clean_finished(self, data):
        """Report freed space and errors; clear results unless dry run."""
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        
        freed = data.get("freed", 0)
        errors = data.get("errors", [])
        dry_run = data.get("dry_run", False)
        
        message = f"Cleanup {'preview' if dry_run else 'complete'}.\n"
        message += f"Space recovered: {self.format_bytes(freed)}\n"
        
        if errors:
            message += f"\nErrors ({len(errors)}):\n"
            message += "\n".join(errors[:5])  # Show first 5 errors
            if len(errors) > 5:
                message += f"\n... and {len(errors) - 5} more errors"
        
        QMessageBox.information(self, "Cleanup Complete", message)
        
        # Clear table if not dry run
        if not dry_run:
            self.pm_table.setRowCount(0)
            self.pm_resources = []
        """_on_clean_finished."""

    def _on_clean_error(self, err):
        """Reset the buttons and warn about the cleanup failure."""
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        self.pm_cleanup_button.setEnabled(True)
        QMessageBox.warning(self, "Cleanup Error", str(err))
        """_on_clean_error."""

    def _on_worker_finished(self, worker):
        """Unregister a finished worker thread and delete it."""
        self.remove_worker_thread(worker)
        worker.deleteLater()
        """_on_worker_finished."""
