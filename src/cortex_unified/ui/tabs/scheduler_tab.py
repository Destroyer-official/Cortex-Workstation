"""Tab for scheduler tab in Cortex Cleaner GUI."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QHeaderView, QListWidget, QRadioButton,
    QComboBox, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QSpinBox, QTabWidget, QAbstractItemView, QSizePolicy, QListWidgetItem,
    QDialog, QDialogButtonBox, QTimeEdit
)
from PySide6.QtCore import QThread, Signal, Qt, QObject, QTimer, QTime
from PySide6.QtGui import QIcon, QFont, QTextCursor

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.scheduler.scheduler import TaskScheduler
from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules

class AddTaskDialog(QDialog):
    """Dialog collecting a task name, frequency (daily/weekly/monthly/once), and time."""
    def __init__(self, parent=None):
        """Build the schedule form with name, frequency combo, time edit, and Ok/Cancel."""
        super().__init__(parent)
        self.setWindowTitle("Schedule New Task")
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("CortexDailyClean")
        form.addRow("Task Name:", self.name_input)
        
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["daily", "weekly", "monthly", "once"])
        form.addRow("Frequency:", self.freq_combo)
        
        self.time_input = QTimeEdit()
        self.time_input.setTime(QTime(2, 0)) # 2:00 AM default
        form.addRow("Time:", self.time_input)
        
        layout.addLayout(form)
        
        # Standard buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

class SchedulerTab(BaseTab):
    """Tab for scheduler tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """Create the TaskScheduler and AutoCleanRules backends."""
        super().__init__(config, logger, safety_manager)
        self.task_scheduler = TaskScheduler(config)
        self.auto_rules = AutoCleanRules(config)

    def setup_ui(self):
        """Create the task scheduler tab.

        Builds an inner QTabWidget hosting a Scheduled Tasks sub-tab and
        an Auto-Clean Rules sub-tab.
        """
        layout = QVBoxLayout(self)
        
        title_label = QLabel('Scheduler System Configuration')
        title_label.setStyleSheet('font-size: 16px; font-weight: bold; margin: 10px;')
        layout.addWidget(title_label)
        
        scheduler_tab_widget = QTabWidget()
        layout.addWidget(scheduler_tab_widget)
        
        tasks_tab = self.create_tasks_subtab()
        scheduler_tab_widget.addTab(tasks_tab, 'Scheduled Tasks')
        
        rules_tab = self.create_auto_clean_rules_subtab()
        scheduler_tab_widget.addTab(rules_tab, 'Auto-Clean Rules')

    def create_tasks_subtab(self) -> QWidget:
        """Build the Scheduled Tasks sub-tab.

        Creates Add/Remove/Refresh task buttons, a four-column task table
        (with the raw-object column hidden), and schedules an initial
        refresh shortly after construction.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        add_btn = QPushButton("Add New Task")
        add_btn.clicked.connect(self._add_task)
        controls.addWidget(add_btn)
        
        rm_btn = QPushButton("Remove Task")
        rm_btn.clicked.connect(self._remove_task)
        controls.addWidget(rm_btn)
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self._refresh_tasks)
        controls.addWidget(refresh_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(4)
        self.tasks_table.setHorizontalHeaderLabels(['Task Name', 'Trigger', 'Status', 'Raw Object'])
        self.tasks_table.horizontalHeader().setStretchLastSection(True)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tasks_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tasks_table.setColumnHidden(3, True) # Hide raw dump column
        layout.addWidget(self.tasks_table)
        
        # Populate immediately
        QTimer.singleShot(100, self._refresh_tasks)
        return tab

    def _refresh_tasks(self):
        """Reload the task table from TaskScheduler.list_scheduled_tasks.

        Tolerates OS-specific payload shapes (name/label, next_run_time or
        schedule, status or last_exit_code) and stores the raw task dict in
        the hidden column.
        """
        tasks = self.task_scheduler.list_scheduled_tasks()
        self.tasks_table.setRowCount(len(tasks))
        
        for i, task in enumerate(tasks):
            # Parse dict based on OS returning different payload shapes
            name = task.get("name", task.get("label", "Unknown"))
            trigger = task.get("next_run_time", str(task.get("schedule", "Unknown")))
            status = task.get("status", str(task.get("last_exit_code", "Active")))
            
            self.tasks_table.setItem(i, 0, QTableWidgetItem(name))
            self.tasks_table.setItem(i, 1, QTableWidgetItem(trigger))
            self.tasks_table.setItem(i, 2, QTableWidgetItem(status))
            self.tasks_table.setItem(i, 3, QTableWidgetItem(str(task)))

    def _add_task(self):
        """Register a new scheduled cleanup task from the AddTaskDialog.

        Builds a CLI command (run_cli.py --temp --cache --auto-approve)
        with the chosen name, frequency, and time, registers it via
        TaskScheduler, and refreshes the table; failure prompts for admin
        privileges.
        """
        dialog = AddTaskDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name = dialog.name_input.text().strip()
            if not name:
                QMessageBox.warning(self, "Invalid", "Task name cannot be empty.")
                return
            
            freq = dialog.freq_combo.currentText()
            t = dialog.time_input.time()
            
            cmd = f'"{sys.executable}" "{Path(__file__).parent.parent.parent.parent}/run_cli.py" --temp --cache --auto-approve'
            
            # Pack OS params
            params = {
                "time": f"{t.hour():02d}:{t.minute():02d}",
                "hour": t.hour(),
                "minute": t.minute(),
                "days": "MON", 
                "weekday": 1
            }
            
            success = self.task_scheduler.create_scheduled_task(name, cmd, freq, params)
            if success:
                QMessageBox.information(self, "Success", f"Task '{name}' registered successfully.")
                self._refresh_tasks()
            else:
                QMessageBox.critical(self, "Error", "Failed to register OS Task. Ensure you have administrator/root privileges.")

    def _remove_task(self):
        """Delete the selected scheduled task after confirmation.

        Calls TaskScheduler.delete_scheduled_task by name and refreshes the
        table; failure suggests elevated privileges are required.
        """
        row = self.tasks_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selection", "Select a task to remove.")
            return
            
        name = self.tasks_table.item(row, 0).text()
        reply = QMessageBox.question(self, "Confirm Delete", f"Remove OS Task '{name}'?")
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.task_scheduler.delete_scheduled_task(name)
            if success:
                self._refresh_tasks()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete task. Root privileges may be required.")

    def create_auto_clean_rules_subtab(self) -> QWidget:
        """Build the Auto-Clean Rules sub-tab.

        Creates a disk-usage threshold spinner, a startup deep-clean
        checkbox, an Apply button, and a daemon status label for the
        background monitoring rules.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info = QLabel("Auto-cleanup operates via a background daemon triggering operations securely.")
        layout.addWidget(info)
        
        group = QGroupBox("Directory Monitor Rules")
        group_layout = QFormLayout(group)
        
        self.disk_rule_spin = QSpinBox()
        self.disk_rule_spin.setRange(1, 100)
        self.disk_rule_spin.setValue(90)
        self.disk_rule_spin.setSuffix(" %")
        group_layout.addRow("Purge Temp Data when Drive exceeds capacity:", self.disk_rule_spin)
        
        self.startup_rule_check = QCheckBox("Run deep clean automatically on application startup")
        group_layout.addRow(self.startup_rule_check)
        
        layout.addWidget(group)
        
        controls = QHBoxLayout()
        apply_btn = QPushButton("Apply Auto-Rules")
        apply_btn.clicked.connect(self._apply_rules)
        apply_btn.setStyleSheet('QPushButton { font-weight: bold; background-color: #2196F3; color: white; padding: 5px; }')
        controls.addWidget(apply_btn)
        
        self.daemon_status_lbl = QLabel("Daemon: OFF")
        controls.addWidget(self.daemon_status_lbl)
        
        controls.addStretch()
        layout.addLayout(controls)
        layout.addStretch()
        
        return tab

    def _apply_rules(self):
        """Apply the auto-clean rules and start the monitoring daemon.

        Resets existing rules, adds a disk-usage threshold rule (purge temp
        above the chosen percentage) and optionally a startup deep-clean
        rule, then starts hourly monitoring via AutoCleanRules.
        """
        self.auto_rules.rules.clear()
        
        # Drive percentage
        limit = self.disk_rule_spin.value()
        self.auto_rules.add_disk_usage_rule(limit, "clean_temp")
        
        if self.startup_rule_check.isChecked():
            self.auto_rules.add_startup_rule("clean_temp")
            
        # Ensure monitoring daemon is running
        self.auto_rules.start_monitoring(interval_seconds=3600) # hourly checks
        self.daemon_status_lbl.setText("Daemon: ACTIVE (Rule Enforced)")
        QMessageBox.information(self, "Rules Applied", f"System will now passively flush temp boundaries crossing {limit}% disk usage.")
