"""Tab for resource monitor tab in Cortex Cleaner GUI."""

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
    QSpinBox, QTabWidget, QAbstractItemView, QSizePolicy, QListWidgetItem, QMenu
)
from PySide6.QtCore import QThread, Signal, Qt, QObject, QTimer
from PySide6.QtGui import QIcon, QFont, QTextCursor

from .base_tab import BaseTab
from cortex_unified.core.config import Config

class ResourceMonitorTab(BaseTab):
    """Tab for resource monitor tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """Initialize with a null ResourceMonitor before UI setup."""
        self.resource_monitor = None
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Create the resource monitor tab.

        Builds Start/Stop monitoring buttons with a refresh-interval
        spinner, CPU/memory gauges (label + progress bar), disk and
        network I/O readouts, a top-processes table with a kill context
        menu, alert threshold spinners with an alerts log, and a QTimer
        that polls the backend for metrics.
        """
        layout = QVBoxLayout(self)

        controls_group = QGroupBox('Monitoring Controls')
        controls_layout = QHBoxLayout(controls_group)
        self.start_monitoring_button = QPushButton('Start Monitoring')
        self.start_monitoring_button.clicked.connect(self.start_resource_monitoring)
        self.start_monitoring_button.setMinimumHeight(35)
        controls_layout.addWidget(self.start_monitoring_button)
        self.stop_monitoring_button = QPushButton('Stop Monitoring')
        self.stop_monitoring_button.clicked.connect(self.stop_resource_monitoring)
        self.stop_monitoring_button.setEnabled(False)
        self.stop_monitoring_button.setMinimumHeight(35)
        controls_layout.addWidget(self.stop_monitoring_button)
        self.refresh_interval_spinbox = QSpinBox()
        self.refresh_interval_spinbox.setRange(1, 60)
        self.refresh_interval_spinbox.setValue(5)
        self.refresh_interval_spinbox.setSuffix(' seconds')
        controls_layout.addWidget(QLabel('Refresh Interval:'))
        controls_layout.addWidget(self.refresh_interval_spinbox)
        controls_layout.addStretch()
        layout.addWidget(controls_group)

        metrics_group = QGroupBox('System Metrics')
        metrics_layout = QVBoxLayout(metrics_group)
        usage_layout = QHBoxLayout()

        cpu_group = QGroupBox('CPU Usage')
        cpu_layout = QVBoxLayout(cpu_group)
        self.cpu_usage_label = QLabel('CPU: 0%')
        self.cpu_usage_label.setStyleSheet('font-size: 14px; font-weight: bold;')
        cpu_layout.addWidget(self.cpu_usage_label)
        self.cpu_progress_bar = QProgressBar()
        self.cpu_progress_bar.setRange(0, 100)
        cpu_layout.addWidget(self.cpu_progress_bar)
        usage_layout.addWidget(cpu_group)

        memory_group = QGroupBox('Memory Usage')
        memory_layout = QVBoxLayout(memory_group)
        self.memory_usage_label = QLabel('Memory: 0 MB / 0 MB')
        self.memory_usage_label.setStyleSheet('font-size: 14px; font-weight: bold;')
        memory_layout.addWidget(self.memory_usage_label)
        self.memory_progress_bar = QProgressBar()
        self.memory_progress_bar.setRange(0, 100)
        memory_layout.addWidget(self.memory_progress_bar)
        usage_layout.addWidget(memory_group)
        metrics_layout.addLayout(usage_layout)

        io_layout = QHBoxLayout()
        disk_group = QGroupBox('Disk I/O')
        disk_layout = QVBoxLayout(disk_group)
        self.disk_read_label = QLabel('Read: 0 MB/s')
        disk_layout.addWidget(self.disk_read_label)
        self.disk_write_label = QLabel('Write: 0 MB/s')
        disk_layout.addWidget(self.disk_write_label)
        io_layout.addWidget(disk_group)

        network_group = QGroupBox('Network I/O')
        network_layout = QVBoxLayout(network_group)
        self.network_sent_label = QLabel('Sent: 0 MB/s')
        network_layout.addWidget(self.network_sent_label)
        self.network_recv_label = QLabel('Received: 0 MB/s')
        network_layout.addWidget(self.network_recv_label)
        io_layout.addWidget(network_group)
        metrics_layout.addLayout(io_layout)
        layout.addWidget(metrics_group)

        processes_group = QGroupBox('Top Processes by Resource Usage')
        processes_layout = QVBoxLayout(processes_group)
        self.resource_processes_table = QTableWidget()
        self.resource_processes_table.setColumnCount(4)
        self.resource_processes_table.setHorizontalHeaderLabels(
            ['Process Name', 'PID', 'CPU %', 'Memory MB'])
        self.resource_processes_table.horizontalHeader().setStretchLastSection(True)
        self.resource_processes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.resource_processes_table.setMaximumHeight(200)
        self.resource_processes_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.resource_processes_table.customContextMenuRequested.connect(self._show_process_context_menu)
        processes_layout.addWidget(self.resource_processes_table)
        layout.addWidget(processes_group)

        alerts_group = QGroupBox('Performance Alerts')
        alerts_layout = QVBoxLayout(alerts_group)
        thresholds_layout = QFormLayout()
        self.cpu_threshold_spinbox = QSpinBox()
        self.cpu_threshold_spinbox.setRange(50, 100)
        self.cpu_threshold_spinbox.setValue(80)
        self.cpu_threshold_spinbox.setSuffix('%')
        thresholds_layout.addRow('CPU Alert Threshold:', self.cpu_threshold_spinbox)
        self.memory_threshold_spinbox = QSpinBox()
        self.memory_threshold_spinbox.setRange(50, 100)
        self.memory_threshold_spinbox.setValue(85)
        self.memory_threshold_spinbox.setSuffix('%')
        thresholds_layout.addRow('Memory Alert Threshold:', self.memory_threshold_spinbox)
        alerts_layout.addLayout(thresholds_layout)
        self.alerts_text = QTextEdit()
        self.alerts_text.setMaximumHeight(100)
        self.alerts_text.setReadOnly(True)
        alerts_layout.addWidget(self.alerts_text)
        layout.addWidget(alerts_group)

        self.monitoring_timer = QTimer(self)
        self.monitoring_timer.timeout.connect(self.update_resource_metrics)

    def start_resource_monitoring(self):
        """Start real-time resource monitoring."""
        try:
            from cortex_unified.performance.resource_monitor import ResourceMonitor
            self.resource_monitor = ResourceMonitor()
            interval_sec = self.refresh_interval_spinbox.value()
            self.resource_monitor.start_monitoring(interval=interval_sec)
            self.monitoring_timer.start(interval_sec * 1000)
            self.start_monitoring_button.setEnabled(False)
            self.stop_monitoring_button.setEnabled(True)
            self.set_status('Resource monitoring started')
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Resource monitor module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error starting monitoring:\n{str(e)}')

    def stop_resource_monitoring(self):
        """Stop real-time resource monitoring."""
        try:
            if getattr(self, 'resource_monitor', None):
                self.resource_monitor.stop_monitoring()
            self.monitoring_timer.stop()
            self.start_monitoring_button.setEnabled(True)
            self.stop_monitoring_button.setEnabled(False)
            self.set_status('Resource monitoring stopped')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error stopping monitoring:\n{str(e)}')

    def update_resource_metrics(self):
        """Poll the backend's latest metrics and refresh every display.

        Updates CPU/memory labels and bars, disk/network throughput, and
        the top-5 processes table (sorted by memory RSS via psutil), then
        checks alert thresholds; errors are appended to the alerts log.
        """
        try:
            import psutil
            if not self.resource_monitor or not self.resource_monitor.metrics_history:
                return
            
            # Fetch latest metrics that have rates calculated by the backend thread
            metrics = self.resource_monitor.metrics_history[-1]
            cpu_percent = metrics.cpu_percent
            self.cpu_usage_label.setText(f'CPU: {cpu_percent:.1f}%')
            self.cpu_progress_bar.setValue(int(cpu_percent))

            mem = psutil.virtual_memory()
            memory_used = (mem.total - mem.available) / (1024 * 1024)
            memory_total = mem.total / (1024 * 1024)
            memory_percent = metrics.memory_percent
            self.memory_usage_label.setText(f'Memory: {memory_used:.0f} MB / {memory_total:.0f} MB')
            self.memory_progress_bar.setValue(int(memory_percent))

            self.disk_read_label.setText(f"Read: {metrics.disk_io_read_mb:.1f} MB/s")
            self.disk_write_label.setText(f"Write: {metrics.disk_io_write_mb:.1f} MB/s")

            self.network_sent_label.setText(f"Sent: {metrics.network_io_sent_mb:.1f} MB/s")
            self.network_recv_label.setText(f"Received: {metrics.network_io_recv_mb:.1f} MB/s")

            try:
                processes = []
                for p in sorted(psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_info']), 
                                key=lambda p: p.info['memory_info'].rss if p.info.get('memory_info') else 0, 
                                reverse=True)[:5]:
                    processes.append({
                        'name': p.info['name'],
                        'pid': p.info['pid'],
                        'cpu_percent': p.info['cpu_percent'],
                        'memory_mb': p.info['memory_info'].rss / (1024*1024) if p.info.get('memory_info') else 0
                    })
                
                self.resource_processes_table.setRowCount(len(processes))
                for i, process in enumerate(processes):
                    self.resource_processes_table.setItem(i, 0, QTableWidgetItem(process.get('name', 'Unknown')))
                    self.resource_processes_table.setItem(i, 1, QTableWidgetItem(str(process.get('pid', 0))))
                    self.resource_processes_table.setItem(i, 2, QTableWidgetItem(f"{process.get('cpu_percent', 0):.1f}"))
                    self.resource_processes_table.setItem(i, 3, QTableWidgetItem(f"{process.get('memory_mb', 0):.1f}"))
            except Exception:
                pass

            self.check_performance_alerts(cpu_percent, memory_percent)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.alerts_text.append(f'Error updating metrics: {str(e)}\n{tb}')

    def check_performance_alerts(self, cpu_percent, memory_percent):
        """Append timestamped alerts when CPU or memory exceed their thresholds."""
        from datetime import datetime
        current_time = datetime.now().strftime('%H:%M:%S')
        cpu_threshold = self.cpu_threshold_spinbox.value()
        if cpu_percent > cpu_threshold:
            alert_msg = f'[{current_time}] HIGH CPU USAGE: {cpu_percent:.1f}% (threshold: {cpu_threshold}%)'
            self.alerts_text.append(alert_msg)
        memory_threshold = self.memory_threshold_spinbox.value()
        if memory_percent > memory_threshold:
            alert_msg = f'[{current_time}] HIGH MEMORY USAGE: {memory_percent:.1f}% (threshold: {memory_threshold}%)'
            self.alerts_text.append(alert_msg)
        self.alerts_text.moveCursor(QTextCursor.MoveOperation.End)

    def _show_process_context_menu(self, position):
        """Show context menu to kill a selected process."""
        row = self.resource_processes_table.rowAt(position.y())
        if row < 0:
            return
            
        pid_item = self.resource_processes_table.item(row, 1)
        name_item = self.resource_processes_table.item(row, 0)
        if not pid_item or not name_item:
            return
            
        pid = int(pid_item.text())
        name = name_item.text()
        
        from cortex_unified.core.proc import is_protected_process
        menu = QMenu()
        if is_protected_process(pid) or is_protected_process(name):
            kill_action = menu.addAction(f"🔒 Protected System Process: {name} (PID: {pid})")
            kill_action.setEnabled(False)
        else:
            kill_action = menu.addAction(f"💀 Force Kill: {name} (PID: {pid})")
        
        action = menu.exec(self.resource_processes_table.viewport().mapToGlobal(position))
        
        if action == kill_action and kill_action.isEnabled():
            reply = QMessageBox.warning(
                self, 'Confirm Force Kill',
                f"Are you sure you want to force kill process '{name}' (PID: {pid})?\n\nWarning: Terminating system processes can cause instability or data loss.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._kill_process(pid, name)

    def _kill_process(self, pid: int, name: str):
        """Force-kill the process via psutil, reporting access/not-found errors.

        Refreshes the process table immediately after a successful kill.
        """
        from cortex_unified.core.proc import is_protected_process
        if is_protected_process(pid) or is_protected_process(name):
            QMessageBox.critical(
                self, "Action Denied",
                f"Cannot terminate protected Windows OS component '{name}'.\n"
                "Terminating this process would cause desktop blackouts or system instability."
            )
            return

        import psutil
        try:
            p = psutil.Process(pid)
            p.kill() # SECURE: forceful termination
            self.set_status(f"Killed process {name} (PID: {pid})")
            QMessageBox.information(self, "Success", f"Process '{name}' (PID: {pid}) was forcefully terminated.")
            self.update_resource_metrics() # refresh table instantly
        except psutil.AccessDenied:
            QMessageBox.critical(self, "Access Denied", f"Cannot kill '{name}'. Administrator privileges required.")
        except psutil.NoSuchProcess:
            QMessageBox.warning(self, "Not Found", f"Process '{name}' no longer exists or already exited.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to kill process:\n{e}")
