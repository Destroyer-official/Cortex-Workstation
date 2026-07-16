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
        def __init__(self, *args, **kwargs): pass
        def detect_package_managers(self): return {}
        def scan_caches(self): return []
        def cleanup_caches(self): return {}


class PMSearchWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            cleaner = PackageManagerCleaner(self.config)
            managers = cleaner.detect_package_managers()
            self.finished.emit(managers)
        except Exception as e:
            self.error.emit(str(e))


class PMScanWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config, managers: dict, keep_recent: int, orphaned: bool):
        super().__init__()
        self.config = config
        self.managers = managers
        self.keep_recent = keep_recent
        self.orphaned = orphaned

    def run(self):
        try:
            # Need to implement the wrapper to scan caches
            cleaner = PackageManagerCleaner(self.config)
            results = cleaner.scan_caches()  # Or pass the params if accepted
            stats = getattr(cleaner, 'get_stats', lambda: {})()
            self.finished.emit({"resources": results, "stats": stats})
        except Exception as e:
            self.error.emit(str(e))


class PMCLeanWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config, targets: list, dry_run: bool):
        super().__init__()
        self.config = config
        self.targets = targets
        self.dry_run = dry_run

    def run(self):
        try:
            cleaner = PackageManagerCleaner(self.config)
            results = cleaner.cleanup_caches(self.targets, dry_run=self.dry_run)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class PackageManagerTab(BaseTab):
    """Tab for package manager tab functionality."""

    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Create the Package Manager tab."""
        layout = QVBoxLayout(self)
        
        pm_group = QGroupBox('Package Managers')
        pm_layout = QVBoxLayout(pm_group)
        self.pm_pip_checkbox = QCheckBox('pip (Python)')
        self.pm_pip_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_pip_checkbox)
        
        self.pm_npm_checkbox = QCheckBox('npm (Node.js)')
        self.pm_npm_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_npm_checkbox)
        
        self.pm_yarn_checkbox = QCheckBox('yarn (Node.js)')
        pm_layout.addWidget(self.pm_yarn_checkbox)
        
        self.pm_conda_checkbox = QCheckBox('conda (Python)')
        pm_layout.addWidget(self.pm_conda_checkbox)
        
        self.pm_system_checkbox = QCheckBox('System Package Manager')
        pm_layout.addWidget(self.pm_system_checkbox)
        layout.addWidget(pm_group)
        
        options_group = QGroupBox('Options')
        options_layout = QFormLayout(options_group)
        self.pm_keep_recent_spinbox = QSpinBox()
        self.pm_keep_recent_spinbox.setRange(0, 365)
        self.pm_keep_recent_spinbox.setValue(7)
        self.pm_keep_recent_spinbox.setSuffix(' days')
        options_layout.addRow('Keep recent cache files:', self.pm_keep_recent_spinbox)
        
        self.pm_orphaned_checkbox = QCheckBox('Include orphaned packages')
        options_layout.addRow(self.pm_orphaned_checkbox)
        
        self.pm_dry_run_checkbox = QCheckBox('Dry Run (Preview Only)')
        self.pm_dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.pm_dry_run_checkbox)
        layout.addWidget(options_group)
        
        button_layout = QHBoxLayout()
        self.pm_detect_button = QPushButton('Detect Package Managers')
        self.pm_detect_button.clicked.connect(self.detect_package_managers)
        button_layout.addWidget(self.pm_detect_button)
        
        self.pm_scan_button = QPushButton('Scan Cache')
        self.pm_scan_button.clicked.connect(self.start_pm_scan)
        button_layout.addWidget(self.pm_scan_button)
        
        self.pm_cleanup_button = QPushButton('Clean Up')
        self.pm_cleanup_button.clicked.connect(self.start_pm_cleanup)
        self.pm_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.pm_cleanup_button)
        layout.addLayout(button_layout)
        
        self.pm_progress_bar = QProgressBar()
        self.pm_progress_bar.setVisible(False)
        layout.addWidget(self.pm_progress_bar)
        
        results_group = QGroupBox('Package Manager Cache')
        results_layout = QVBoxLayout(results_group)
        self.pm_summary_label = QLabel("Click 'Detect Package Managers' to start")
        results_layout.addWidget(self.pm_summary_label)
        
        self.pm_table = QTableWidget()
        self.pm_table.setColumnCount(4)
        self.pm_table.setHorizontalHeaderLabels(['Package Manager', 'Cache Size', 'Files', 'Status'])
        self.pm_table.horizontalHeader().setStretchLastSection(True)
        self.pm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.pm_table)
        layout.addWidget(results_group)

    def detect_package_managers(self):
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

    def _on_detect_finished(self, managers):
        self.pm_progress_bar.setVisible(False)
        self.pm_detect_button.setEnabled(True)
        
        msg = []
        for name, detected in managers.items():
            check_box = getattr(self, f"pm_{name}_checkbox", None)
            if check_box:
                check_box.setEnabled(detected)
                check_box.setChecked(detected)
            if detected:
                msg.append(name.upper())
                
        if msg:
            self.pm_summary_label.setText(f"Detected: {', '.join(msg)}")
        else:
            self.pm_summary_label.setText("No compatible package managers found on system.")

    def _on_detect_error(self, err):
        self.pm_progress_bar.setVisible(False)
        self.pm_detect_button.setEnabled(True)
        QMessageBox.warning(self, "Detection Failed", str(err))

    def start_pm_scan(self):
        managers = {
            "pip": self.pm_pip_checkbox.isChecked(),
            "npm": self.pm_npm_checkbox.isChecked(),
            "yarn": self.pm_yarn_checkbox.isChecked(),
            "conda": self.pm_conda_checkbox.isChecked(),
            "system": self.pm_system_checkbox.isChecked()
        }
        
        self.pm_progress_bar.setVisible(True)
        self.pm_progress_bar.setRange(0, 0)
        self.pm_scan_button.setEnabled(False)
        self.pm_cleanup_button.setEnabled(False)
        self.pm_table.setRowCount(0)
        
        worker = PMScanWorker(self.config, managers, self.pm_keep_recent_spinbox.value(), self.pm_orphaned_checkbox.isChecked())
        self.add_worker_thread(worker)
        
        worker.finished.connect(self._on_scan_finished)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_scan_finished(self, data):
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        
        self.pm_resources = data.get("resources", [])
        self.pm_table.setRowCount(len(self.pm_resources))
        
        total_size = 0
        for i, res in enumerate(self.pm_resources):
            # Safe parsing
            pm_name = getattr(res, 'manager_name', type(res).__name__)
            size = getattr(res, 'size', 0)
            files = getattr(res, 'file_count', 0)
            status = "Found"
            total_size += size
            
            self.pm_table.setItem(i, 0, QTableWidgetItem(pm_name))
            self.pm_table.setItem(i, 1, QTableWidgetItem(self.format_bytes(size)))
            self.pm_table.setItem(i, 2, QTableWidgetItem(str(files)))
            self.pm_table.setItem(i, 3, QTableWidgetItem(status))
            
        self.pm_summary_label.setText(f"Found caches: {self.format_bytes(total_size)} total")
        if total_size > 0:
            self.pm_cleanup_button.setEnabled(True)

    def _on_scan_error(self, err):
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        QMessageBox.warning(self, "Scan Error", str(err))

    def start_pm_cleanup(self):
        if not hasattr(self, 'pm_resources'): return
        
        dry_run = self.pm_dry_run_checkbox.isChecked()
        act = "dry_run" if dry_run else "PERMANENT DELETION"
        reply = QMessageBox.warning(
            self, "Execute Clean",
            f"Are you sure you want to execute {act} on Package Manager caches?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.pm_cleanup_button.setEnabled(False)
        self.pm_scan_button.setEnabled(False)
        self.pm_progress_bar.setVisible(True)
        
        worker = PMCLeanWorker(self.config, self.pm_resources, dry_run=dry_run)
        self.add_worker_thread(worker)
        worker.finished.connect(self._on_clean_finished)
        worker.error.connect(self._on_clean_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_clean_finished(self, data):
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        freed = data.get("freed", 0)
        QMessageBox.information(self, "Cleanup Complete", f"Process complete. Recovered space approx: {self.format_bytes(freed)}")
        self.pm_table.setRowCount(0)
        self.pm_resources = []

    def _on_clean_error(self, err):
        self.pm_progress_bar.setVisible(False)
        self.pm_scan_button.setEnabled(True)
        self.pm_cleanup_button.setEnabled(True)
        QMessageBox.warning(self, "Clean Error", str(err))

    def _on_worker_finished(self, worker):
        self.remove_worker_thread(worker)
        worker.deleteLater()
