"""Tab for process analyzer tab in Cortex Cleaner GUI."""

from typing import List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter
)
from PySide6.QtCore import QThread, Signal, Qt

from .base_tab import BaseTab
from cortex_unified.system_tools.process_analyzer import ProcessAnalyzer

class ProcessAnalyzerWorker(QThread):
    """ProcessAnalyzerWorker."""
    finished = Signal(list, list) # processes, services
    error = Signal(str)
    
    def __init__(self, config):
        """__init__."""
        super().__init__()
        self.analyzer = ProcessAnalyzer(config)
        """__init__."""
        """__init__."""
        
    def run(self):
        """run."""
        try:
            processes = self.analyzer.list_processes()
            services = self.analyzer.list_services()
            # high_resource = self.analyzer.find_high_resource_processes()
            self.finished.emit(processes, services)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
    """ProcessAnalyzerWorker class."""
    """ProcessAnalyzerWorker class."""

class ProcessAnalyzerTab(BaseTab):
    """Tab for process analyzer tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """__init__."""
        super().__init__(config, logger, safety_manager)
        self.worker = None
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Create the process analyzer tab."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        buttons_layout = QHBoxLayout()
        self.refresh_processes_button = QPushButton('Refresh Activity')
        self.refresh_processes_button.clicked.connect(self.refresh_processes)
        self.refresh_processes_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.refresh_processes_button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.processes_progress_bar = QProgressBar()
        self.processes_progress_bar.setRange(0, 0) # indeterminate
        self.processes_progress_bar.setVisible(False)
        self.processes_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.processes_progress_bar)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Processes UI
        processes_group = QGroupBox('Running Processes')
        processes_layout = QVBoxLayout(processes_group)
        self.processes_table = QTableWidget()
        self.processes_table.setColumnCount(4)
        self.processes_table.setHorizontalHeaderLabels(['Name', 'PID', 'Memory', 'CPU'])
        self.processes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.processes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        processes_layout.addWidget(self.processes_table)
        splitter.addWidget(processes_group)
        
        # Services UI
        services_group = QGroupBox('System Services')
        services_layout = QVBoxLayout(services_group)
        self.services_table = QTableWidget()
        self.services_table.setColumnCount(3)
        self.services_table.setHorizontalHeaderLabels(['Name', 'Status', 'Description / PID'])
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.services_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        services_layout.addWidget(self.services_table)
        splitter.addWidget(services_group)
        
        splitter.setSizes([500, 400])
        layout.addWidget(splitter)

    def refresh_processes(self):
        """refresh_processes."""
        if self.worker and self.worker.isRunning():
            return
            
        self.processes_progress_bar.setVisible(True)
        self.refresh_processes_button.setEnabled(False)
        self.processes_table.setRowCount(0)
        self.services_table.setRowCount(0)
        
        self.worker = ProcessAnalyzerWorker(self.config)
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_scan_error)
        self.worker.start()
        """refresh_processes."""
        """refresh_processes."""

    def _on_scan_finished(self, processes: List[Dict], services: List[Dict]):
        """_on_scan_finished."""
        self.processes_progress_bar.setVisible(False)
        self.refresh_processes_button.setEnabled(True)
        
        # Populate Processes
        self.processes_table.setRowCount(len(processes))
        for row, p in enumerate(processes):
            self.processes_table.setItem(row, 0, QTableWidgetItem(p.get("name", p.get("command", "Unknown"))))
            self.processes_table.setItem(row, 1, QTableWidgetItem(str(p.get("pid", ""))))
            self.processes_table.setItem(row, 2, QTableWidgetItem(str(p.get("mem_usage", p.get("mem_percent", "")))))
            self.processes_table.setItem(row, 3, QTableWidgetItem(str(p.get("cpu_percent", p.get("cpu_time", "")))))
            
        # Populate Services
        self.services_table.setRowCount(len(services))
        for row, s in enumerate(services):
            self.services_table.setItem(row, 0, QTableWidgetItem(s.get("display_name", s.get("name", s.get("unit", s.get("service", ""))))))
            self.services_table.setItem(row, 1, QTableWidgetItem(s.get("state", s.get("active", s.get("status", "")))))
            self.services_table.setItem(row, 2, QTableWidgetItem(s.get("description", str(s.get("pid", "")))))
        """_on_scan_finished."""
        """_on_scan_finished."""
            
    def _on_scan_error(self, err_msg):
        """_on_scan_error."""
        self.processes_progress_bar.setVisible(False)
        self.refresh_processes_button.setEnabled(True)
        self.logger.error(f"Process analysis failed: {err_msg}")
        """_on_scan_error."""
        """_on_scan_error."""
