"""Tab for docker tab in Cortex Cleaner GUI."""

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
# Assuming DockerCleaner exists or will be mocked/available
try:
    from cortex_unified.analyzers.docker_cleaner import DockerCleaner
except ImportError:
    class DockerCleaner:
        """Dockercleaner.

        Manages DockerCleaner operations and coordinates related state changes for the component.
        """
        def is_docker_available(self):
            """Check if Docker is available.

            Manages is docker available operations and coordinates related state changes for the component.
            """
            return False

class DockerScanWorker(QThread):
    """Dockerscanworker.

    Manages DockerScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, scan_images: bool, scan_containers: bool, scan_volumes: bool, scan_networks: bool):
        """Store the four resource-type scan flags.

        Initializes the instance and configures internal state.

        Args:
            scan_images (bool): The scan images parameter.
            scan_containers (bool): The scan containers parameter.
            scan_volumes (bool): The scan volumes parameter.
            scan_networks (bool): The scan networks parameter.
        """
        super().__init__()
        self.scan_images = scan_images
        self.scan_containers = scan_containers
        self.scan_volumes = scan_volumes
        self.scan_networks = scan_networks

    def run(self):
        """Run Docker resource scanning.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            cleaner = DockerCleaner()
            if not cleaner.is_docker_available():
                self.error.emit('Docker is not available or not running')
                return
            all_resources = []
            if self.scan_images:
                images = cleaner.scan_unused_images()
                all_resources.extend(images)
            if self.scan_containers:
                containers = cleaner.scan_stopped_containers()
                all_resources.extend(containers)
            if self.scan_volumes:
                volumes = cleaner.scan_unused_volumes()
                all_resources.extend(volumes)
            if self.scan_networks:
                networks = cleaner.scan_unused_networks()
                all_resources.extend(networks)
            stats = cleaner.get_stats()
            self.finished.emit({'resources': all_resources, 'stats': stats})
        except Exception as e:
            self.error.emit(str(e))

class DockerCleanupWorker(QThread):
    """Dockercleanupworker.

    Manages DockerCleanupWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, resources: list, dry_run: bool):
        """Store the resources to clean and the dry-run flag.

        Initializes the instance and configures internal state.

        Args:
            resources (list): The resources parameter.
            dry_run (bool): The dry run parameter.
        """
        super().__init__()
        self.resources = resources
        self.dry_run = dry_run

    def run(self):
        """Run Docker resource cleanup.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            cleaner = DockerCleaner()
            if not cleaner.is_docker_available():
                self.error.emit('Docker is not available or not running')
                return
            result = cleaner.cleanup_resources(self.resources, self.dry_run)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class DockerTab(BaseTab):
    """Dockertab.

    Manages DockerTab operations and coordinates related state changes for the component.
    """

    def __init__(self, config, logger, safety_manager):
        """Initialize the tab and call setup_ui.

        Initializes the instance and configures internal state.

        Args:
            config: The config parameter.
            logger: The logger parameter.
            safety_manager: The safety manager parameter.
        """
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Set up the user interface.

        Manages setup ui operations and coordinates related state changes for the component.
        """
        layout = QVBoxLayout(self)
        self.docker_status_label = QLabel('Checking Docker availability...')
        layout.addWidget(self.docker_status_label)
        
        resource_group = QGroupBox('Resources to Clean')
        resource_layout = QVBoxLayout(resource_group)
        self.docker_images_checkbox = QCheckBox('Unused Docker Images')
        self.docker_images_checkbox.setChecked(True)
        resource_layout.addWidget(self.docker_images_checkbox)
        
        self.docker_containers_checkbox = QCheckBox('Stopped Docker Containers')
        self.docker_containers_checkbox.setChecked(True)
        resource_layout.addWidget(self.docker_containers_checkbox)
        
        self.docker_volumes_checkbox = QCheckBox('Unused Docker Volumes')
        self.docker_volumes_checkbox.setChecked(True)
        resource_layout.addWidget(self.docker_volumes_checkbox)
        
        self.docker_networks_checkbox = QCheckBox('Unused Docker Networks')
        self.docker_networks_checkbox.setChecked(True)
        resource_layout.addWidget(self.docker_networks_checkbox)
        layout.addWidget(resource_group)
        
        options_group = QGroupBox('Options')
        options_layout = QFormLayout(options_group)
        self.docker_dry_run_checkbox = QCheckBox('Dry Run (Preview Only)')
        self.docker_dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.docker_dry_run_checkbox)
        layout.addWidget(options_group)
        
        button_layout = QHBoxLayout()
        self.docker_scan_button = QPushButton('Scan Docker Resources')
        self.docker_scan_button.clicked.connect(self.start_docker_scan)
        button_layout.addWidget(self.docker_scan_button)
        
        self.docker_cleanup_button = QPushButton('Clean Up Resources')
        self.docker_cleanup_button.clicked.connect(self.start_docker_cleanup)
        self.docker_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.docker_cleanup_button)
        layout.addLayout(button_layout)
        
        self.docker_progress_bar = QProgressBar()
        self.docker_progress_bar.setVisible(False)
        layout.addWidget(self.docker_progress_bar)
        
        results_group = QGroupBox('Docker Resources')
        results_layout = QVBoxLayout(results_group)
        self.docker_summary_label = QLabel('No scan performed yet')
        results_layout.addWidget(self.docker_summary_label)
        
        self.docker_table = QTableWidget()
        self.docker_table.setColumnCount(5)
        self.docker_table.setHorizontalHeaderLabels(['Type', 'Name', 'ID', 'Size', 'Status'])
        self.docker_table.horizontalHeader().setStretchLastSection(True)
        self.docker_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.docker_table)
        layout.addWidget(results_group)
        
        QTimer.singleShot(100, self.check_docker_availability)

    def check_docker_availability(self):
        """Check if Docker is available.

        Manages check docker availability operations and coordinates related state changes for the component.
        """
        try:
            cleaner = DockerCleaner()
            if cleaner.is_docker_available():
                self.docker_status_label.setText('✓ Docker is available and running')
                self.docker_status_label.setStyleSheet('color: green;')
                self.docker_scan_button.setEnabled(True)
            else:
                self.docker_status_label.setText('✗ Docker is not available or not running')
                self.docker_status_label.setStyleSheet('color: red;')
                self.docker_scan_button.setEnabled(False)
        except Exception as e:
            self.docker_status_label.setText(f'✗ Docker error: {str(e)}')
            self.docker_status_label.setStyleSheet('color: red;')
            self.docker_scan_button.setEnabled(False)

    def start_docker_scan(self):
        """Start Docker resource scan dynamically linked to worker threads.

        Manages start docker scan operations and coordinates related state changes for the component.
        """
        self.docker_scan_button.setEnabled(False)
        self.docker_cleanup_button.setEnabled(False)
        self.docker_progress_bar.setVisible(True)
        self.docker_progress_bar.setRange(0, 0)
        self.docker_table.setRowCount(0)
        self.set_status('Scanning Docker resources...')
        self.add_activity('Scanning Docker resources...')
        
        worker = DockerScanWorker(
            self.docker_images_checkbox.isChecked(), 
            self.docker_containers_checkbox.isChecked(), 
            self.docker_volumes_checkbox.isChecked(), 
            self.docker_networks_checkbox.isChecked()
        )
        self.add_worker_thread(worker)
        
        worker.finished.connect(self.docker_scan_finished)
        worker.error.connect(self.docker_scan_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_worker_finished(self, worker):
        """Unregister a finished worker thread and delete it.

        Manages on worker finished operations and coordinates related state changes for the component.

        Args:
            worker: The worker parameter.
        """
        self.remove_worker_thread(worker)
        worker.deleteLater()

    def docker_scan_finished(self, result: dict):
        """Handle Docker scan completion.

        Manages docker scan finished operations and coordinates related state changes for the component.

        Args:
            result (dict): Collection or dictionary holding operation results.
        """
        self.docker_resources = result['resources']
        stats = result['stats']
        self.docker_scan_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        self.set_status(f'Found {len(self.docker_resources)} Docker resources')
        self.add_activity(f'Found {len(self.docker_resources)} Docker resources')
        
        total_size = sum((getattr(resource, 'size', 0) for resource in self.docker_resources))
        size_human = self.format_bytes(total_size)
        self.docker_summary_label.setText(f'Found {len(self.docker_resources)} resources, Total size: {size_human}')
        
        self.docker_table.setRowCount(len(self.docker_resources))
        for i, resource in enumerate(self.docker_resources):
            resource_type = type(resource).__name__.replace('Docker', '')
            name = getattr(resource, 'name', getattr(resource, 'repository', 'Unknown'))
            resource_id = getattr(resource, 'id', 'Unknown')[:12]
            size = self.format_bytes(getattr(resource, 'size', 0))
            if hasattr(resource, 'is_dangling') and resource.is_dangling:
                status = 'Dangling'
            elif hasattr(resource, 'is_orphaned') and resource.is_orphaned:
                status = 'Orphaned'
            elif hasattr(resource, 'is_unused') and resource.is_unused:
                status = 'Unused'
            elif hasattr(resource, 'status'):
                status = resource.status.title()
            else:
                status = 'Unused'
            self.docker_table.setItem(i, 0, QTableWidgetItem(resource_type))
            self.docker_table.setItem(i, 1, QTableWidgetItem(name))
            self.docker_table.setItem(i, 2, QTableWidgetItem(resource_id))
            self.docker_table.setItem(i, 3, QTableWidgetItem(size))
            self.docker_table.setItem(i, 4, QTableWidgetItem(status))
            
        if len(self.docker_resources) > 0:
            self.docker_cleanup_button.setEnabled(True)
        else:
            self.docker_cleanup_button.setEnabled(False)

    def docker_scan_error(self, error: str):
        """Reset the scan controls and report the Docker scan error.

        Manages docker scan error operations and coordinates related state changes for the component.

        Args:
            error (str): Error message string or exception instance.
        """
        self.logger.error(f'Docker scan error: {error}')
        self.docker_scan_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        self.set_status('Docker scan failed')
        self.add_activity(f'Docker scan failed: {error}')
        QMessageBox.critical(self, 'Docker Scan Error', f'An error occurred during Docker scan:\n{error}')

    def start_docker_cleanup(self):
        """Start Docker resource cleanup.

        Manages start docker cleanup operations and coordinates related state changes for the component.
        """
        if not hasattr(self, 'docker_resources') or not self.docker_resources:
            QMessageBox.information(self, 'Info', 'No Docker resources to clean up.')
            return
            
        selected_resources = self.docker_resources
        dry_run = self.docker_dry_run_checkbox.isChecked()
        action = 'preview cleanup of' if dry_run else 'clean up'
        total_size = sum((getattr(resource, 'size', 0) for resource in selected_resources))
        size_human = self.format_bytes(total_size)
        
        reply = QMessageBox.question(
            self, 'Confirm Docker Cleanup', 
            f"Are you sure you want to {action} {len(selected_resources)} Docker resources?\nTotal size: {size_human}\n{('This is a preview only.' if dry_run else 'This action cannot be undone.')}", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return
            
        self.docker_scan_button.setEnabled(False)
        self.docker_cleanup_button.setEnabled(False)
        self.docker_progress_bar.setVisible(True)
        self.docker_progress_bar.setRange(0, 0)
        self.set_status('Cleaning Docker resources...')
        
        worker = DockerCleanupWorker(selected_resources, dry_run)
        self.add_worker_thread(worker)
        
        worker.finished.connect(self.docker_cleanup_finished)
        worker.error.connect(self.docker_cleanup_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def docker_cleanup_finished(self, result):
        """Handle Docker cleanup completion.

        Manages docker cleanup finished operations and coordinates related state changes for the component.

        Args:
            result: Collection or dictionary holding operation results.
        """
        self.docker_scan_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        
        dry_run = self.docker_dry_run_checkbox.isChecked()
        action = 'Would clean' if dry_run else 'Cleaned'
        self.set_status(f'{action} {result.total_removed} Docker resources, freed {self.format_bytes(result.space_freed)}')
        self.add_activity(f'{action} {result.total_removed} Docker resources, freed {self.format_bytes(result.space_freed)}')
        
        details = f'Docker Cleanup Results:\nImages: {result.images_removed}\nContainers: {result.containers_removed}\nVolumes: {result.volumes_removed}\nNetworks: {result.networks_removed}\nSpace freed: {self.format_bytes(result.space_freed)}\n'
        if result.errors:
            details += f'\nErrors ({len(result.errors)}):\n'
            for error in result.errors[:5]:
                details += f'• {error}\n'
            if len(result.errors) > 5:
                details += f'... and {len(result.errors) - 5} more errors'
                
        QMessageBox.information(self, 'Docker Cleanup Complete', details)
        
        if hasattr(self, 'docker_resources'):
            self.docker_resources = []
            
        self.docker_table.setRowCount(0)
        self.docker_summary_label.setText('Cleanup complete. Run scan again to check for new resources.')
        self.docker_cleanup_button.setEnabled(False)

    def docker_cleanup_error(self, error: str):
        """Reset the cleanup controls and report the Docker cleanup error.

        Manages docker cleanup error operations and coordinates related state changes for the component.

        Args:
            error (str): Error message string or exception instance.
        """
        self.logger.error(f'Docker cleanup error: {error}')
        self.docker_scan_button.setEnabled(True)
        self.docker_cleanup_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        self.set_status('Docker cleanup failed')
        self.add_activity(f'Docker cleanup failed: {error}')
        QMessageBox.critical(self, 'Docker Cleanup Error', f'An error occurred during Docker cleanup:\n{error}')
