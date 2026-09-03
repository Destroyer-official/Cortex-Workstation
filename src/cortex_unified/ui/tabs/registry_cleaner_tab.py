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
    """Worker that scans for orphaned registry entries off the UI thread.

    Emits ``finished(list)`` with RegistryCleaner.scan_orphaned_entries()
    results, or ``error(str)`` on failure.
    """
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, config):
        """Create the RegistryCleaner backend used for scanning."""
        super().__init__()
        self.cleaner = RegistryCleaner(config)
        
    def run(self):
        """Scan for orphaned entries, emitting the item list or an error."""
        try:
            items = self.cleaner.scan_orphaned_entries()
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(str(e))

class RegistryCleanWorker(QThread):
    """Worker that removes orphaned registry entries after a backup.

    Emits ``finished(int)`` with the number of entries successfully
    removed, or ``error(str)`` on failure.
    """
    finished = Signal(int)
    error = Signal(str)
    
    def __init__(self, config, paths_to_remove: List[str]):
        """Create the cleaner and store the registry paths to remove."""
        super().__init__()
        self.cleaner = RegistryCleaner(config)
        self.paths_to_remove = paths_to_remove
        
    def run(self):
        """Back up the registry, then remove each listed orphaned entry.

        Emits the removed-entry count via ``finished`` or the failure
        message via ``error``.
        """
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

class RegistryCleanerTab(BaseTab):
    """Tab for registry cleaner tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """Create the RegistryCleaner backend and a null worker reference."""
        super().__init__(config, logger, safety_manager)
        self.cleaner = RegistryCleaner(config)
        self.worker = None

    def setup_ui(self):
        """Create the registry cleaner tab.

        Shows a red safety warning and, on non-Windows systems, a
        disabled notice. On Windows, builds Scan/Clean buttons, an
        indeterminate progress bar, and a three-column
        SubKey/Hive/Program table.
        """
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
        """Run a RegistryScanWorker to find orphaned entries.

        Skips if a worker is already running; otherwise shows the busy
        bar, disables the buttons, clears the table, and starts the
        background scan.
        """
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

    def _on_scan_finished(self, items: List[Dict]):
        """Fill the table with scanned orphaned entries.

        Each row shows the registry subkey path, hive, and target program
        name; the Clean button is enabled only when findings exist.
        """
        self.registry_progress_bar.setVisible(False)
        self.scan_registry_button.setEnabled(True)
        
        if items:
            self.clean_registry_button.setEnabled(True)
            
        self.registry_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.registry_table.setItem(row, 0, QTableWidgetItem(item.get("path", "")))
            self.registry_table.setItem(row, 1, QTableWidgetItem(item.get("hive", "")))
            self.registry_table.setItem(row, 2, QTableWidgetItem(item.get("name", "")))

    def _on_error(self, err_msg):
        """Re-enable buttons and show a critical dialog for registry errors.

        The Clean button is re-enabled only if the table still holds rows.
        """
        self.registry_progress_bar.setVisible(False)
        self.scan_registry_button.setEnabled(True)
        self.clean_registry_button.setEnabled(self.registry_table.rowCount() > 0)
        
        self.logger.error(f"Registry operation failed: {err_msg}")
        QMessageBox.critical(self, "Error", f"Registry Error:\n{err_msg}")

    def clean_registry(self):
        """Remove all scanned orphaned entries via RegistryCleanWorker.

        Collects every path from the table, confirms the purge (noting
        that a backup is generated first), and runs the background
        cleanup worker.
        """
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

    def _on_clean_finished(self, count):
        """Report the number of cleaned entries, clear the table, and disable Clean."""
        self.registry_progress_bar.setVisible(False)
        self.scan_registry_button.setEnabled(True)
        
        QMessageBox.information(self, "Cleanup Complete", f"Successfully cleaned {count} orphaned registry entries. Backup generated.")
        self.registry_table.setRowCount(0)
        self.clean_registry_button.setEnabled(False)
