"""Tab for startup manager tab in Cortex Cleaner GUI."""

from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import QThread, Signal, Qt

from .base_tab import BaseTab
from cortex_unified.system_tools.startup_manager import StartupManager

class StartupScanWorker(QThread):
    """StartupScanWorker."""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, config):
        """__init__."""
        super().__init__()
        self.manager = StartupManager(config)
        """__init__."""
        """__init__."""
        
    def run(self):
        """run."""
        try:
            items = self.manager.list_startup_items()
            self.finished.emit(items)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
    """StartupScanWorker class."""
    """StartupScanWorker class."""

class StartupManagerTab(BaseTab):
    """Tab for startup manager tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """__init__."""
        super().__init__(config, logger, safety_manager)
        self.manager = StartupManager(config)
        self.worker = None
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Create the startup manager tab."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.refresh_startup_button = QPushButton('Refresh Startup Items')
        self.refresh_startup_button.clicked.connect(self.refresh_startup_items)
        self.refresh_startup_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.refresh_startup_button)
        
        self.disable_startup_button = QPushButton('Disable Selected Item')
        self.disable_startup_button.clicked.connect(self.disable_selected_startup_items)
        self.disable_startup_button.setEnabled(False)
        self.disable_startup_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.disable_startup_button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.startup_progress_bar = QProgressBar()
        self.startup_progress_bar.setVisible(False)
        self.startup_progress_bar.setRange(0, 0)
        self.startup_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.startup_progress_bar)
        
        self.startup_table = QTableWidget()
        self.startup_table.setColumnCount(4)
        self.startup_table.setHorizontalHeaderLabels(['Name', 'Location', 'Status', 'Type'])
        self.startup_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.startup_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.startup_table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self.startup_table)

    def _on_selection(self):
        """_on_selection."""
        self.disable_startup_button.setEnabled(len(self.startup_table.selectedItems()) > 0)
        """_on_selection."""
        """_on_selection."""

    def refresh_startup_items(self):
        """refresh_startup_items."""
        if self.worker and self.worker.isRunning():
            return
            
        self.startup_progress_bar.setVisible(True)
        self.refresh_startup_button.setEnabled(False)
        self.disable_startup_button.setEnabled(False)
        self.startup_table.setRowCount(0)
        
        self.worker = StartupScanWorker(self.config)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()
        """refresh_startup_items."""
        """refresh_startup_items."""

    def _on_scan_finished(self, items: List[Dict]):
        """_on_scan_finished."""
        self.startup_progress_bar.setVisible(False)
        self.refresh_startup_button.setEnabled(True)
        
        self.startup_table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.startup_table.setItem(row, 0, QTableWidgetItem(item.get("name", "")))
            self.startup_table.setItem(row, 1, QTableWidgetItem(item.get("location", "")))
            self.startup_table.setItem(row, 2, QTableWidgetItem("Enabled" if item.get("enabled", True) else "Disabled"))
            self.startup_table.setItem(row, 3, QTableWidgetItem(item.get("type", "")))
        """_on_scan_finished."""
        """_on_scan_finished."""

    def _on_scan_error(self, err_msg):
        """_on_scan_error."""
        self.startup_progress_bar.setVisible(False)
        self.refresh_startup_button.setEnabled(True)
        self.logger.error(f"Startup manager scan failed: {err_msg}")
        QMessageBox.critical(self, "Scan Failed", f"Failed to list startup items:\n{err_msg}")
        """_on_scan_error."""
        """_on_scan_error."""

    def disable_selected_startup_items(self):
        """disable_selected_startup_items."""
        row = self.startup_table.currentRow()
        if row < 0: return
        
        name = self.startup_table.item(row, 0).text()
        type_ = self.startup_table.item(row, 3).text()
        
        reply = QMessageBox.question(
            self, "Confirm Disable", 
            f"Are you sure you want to disable startup app '{name}' from loading on boot?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self.manager.disable_startup_item(name, type_)
            if success:
                QMessageBox.information(self, "Success", f"Disabled '{name}'.")
                self.refresh_startup_items()
            else:
                QMessageBox.critical(self, "Failed", "Could not modify registry/folder access directly. Elevate privileges.")
        """disable_selected_startup_items."""
        """disable_selected_startup_items."""
