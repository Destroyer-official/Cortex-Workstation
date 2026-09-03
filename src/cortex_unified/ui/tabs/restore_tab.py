"""Tab for restore tab in Cortex Cleaner GUI."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

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
from cortex_unified.reports.restore_manager import RestoreManager


class RestoreWorker(QThread):
    """Worker that restores a backup manifest off the UI thread.

    Emits ``finished_restore(dict)`` with the result of
    RestoreManager.restore_from_manifest (dry_run=False), or
    ``error_occurred(str)`` on failure.
    """
    finished_restore = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, manager: RestoreManager, target_path: str):
        """Store the RestoreManager and the manifest path to restore from."""
        super().__init__()
        self.manager = manager
        self.target_path = target_path

    def run(self):
        """Restore files from the manifest, emitting results or errors."""
        try:
            res = self.manager.restore_from_manifest(self.target_path, dry_run=False)
            self.finished_restore.emit(res)
        except Exception as e:
            self.error_occurred.emit(str(e))


class RestoreTab(BaseTab):
    """Tab for restore functionality and recovery."""

    def __init__(self, config, logger, safety_manager):
        """Create the RestoreManager backend used for manifest operations."""
        super().__init__(config, logger, safety_manager)
        self.restore_manager = RestoreManager(config)

    def setup_ui(self):
        """Create the restore tab.

        Builds a backup-overview stats label, Refresh/Restore/Delete
        buttons (restore/delete start disabled), an indeterminate progress
        bar, and a four-column snapshot table; an initial refresh is
        scheduled shortly after construction.
        """
        layout = QVBoxLayout(self)
        
        title = QLabel('System Restore & Recovery Hub')
        title.setStyleSheet('font-size: 16px; font-weight: bold; margin: 10px;')
        layout.addWidget(title)
        
        # Info Panel
        info_group = QGroupBox("Backup Overview")
        info_layout = QVBoxLayout(info_group)
        self.stats_lbl = QLabel("Fetching local backups...")
        info_layout.addWidget(self.stats_lbl)
        layout.addWidget(info_group)
        
        # Buttons Setup
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.refresh_manifests_button = QPushButton('Refresh Recovery Points')
        self.refresh_manifests_button.clicked.connect(self.refresh_manifests)
        self.refresh_manifests_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.refresh_manifests_button)
        
        self.restore_button = QPushButton('Restore Selected Snapshot')
        self.restore_button.clicked.connect(self.start_restore)
        self.restore_button.setEnabled(False)
        self.restore_button.setMinimumHeight(35)
        self.restore_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        buttons_layout.addWidget(self.restore_button)
        
        self.delete_manifest_button = QPushButton("Delete Backup")
        self.delete_manifest_button.clicked.connect(self.delete_snapshot)
        self.delete_manifest_button.setEnabled(False)
        self.delete_manifest_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.delete_manifest_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.restore_progress_bar = QProgressBar()
        self.restore_progress_bar.setVisible(False)
        self.restore_progress_bar.setRange(0, 0) # Indeterminate spinning
        layout.addWidget(self.restore_progress_bar)
        
        self.manifests_table = QTableWidget()
        self.manifests_table.setColumnCount(4)
        self.manifests_table.setHorizontalHeaderLabels(['Snapshot ID', 'Files Affected', 'Date Captured', 'Path'])
        self.manifests_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.manifests_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.manifests_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.manifests_table.horizontalHeader().setStretchLastSection(True)
        self.manifests_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.manifests_table.itemSelectionChanged.connect(self._on_table_selection)
        layout.addWidget(self.manifests_table)
        
        QTimer.singleShot(100, self.refresh_manifests)

    def _on_table_selection(self):
        """Enable the Restore and Delete buttons when a snapshot is selected."""
        has_sel = len(self.manifests_table.selectedItems()) > 0
        self.restore_button.setEnabled(has_sel)
        self.delete_manifest_button.setEnabled(has_sel)

    def refresh_manifests(self):
        """Update items in the lists dynamically using the backend.

        Loads manifests via RestoreManager.list_manifests, fills the table
        with backup name, file count, formatted timestamp, and path, and
        updates the overview stats label.
        """
        self.restore_progress_bar.setVisible(True)
        manifests = self.restore_manager.list_manifests()
        
        self.manifests_table.setRowCount(len(manifests))
        
        for i, manifest in enumerate(manifests):
            # Backup Name
            name = manifest.get("backup_name", f"Manifest-{i}")
            self.manifests_table.setItem(i, 0, QTableWidgetItem(name))
            
            # Files
            files = str(manifest.get("files_backed_up", "?"))
            self.manifests_table.setItem(i, 1, QTableWidgetItem(files))
            
            # Timestamp
            ts = manifest.get("timestamp", "")
            try:
                dt_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                dt_str = ts
            self.manifests_table.setItem(i, 2, QTableWidgetItem(dt_str))
            
            # File Path
            f_path = manifest.get("file_path", "")
            path_item = QTableWidgetItem(f_path)
            self.manifests_table.setItem(i, 3, path_item)
            
        stats = self.restore_manager.get_stats()
        self.stats_lbl.setText(
            f"Available Recovery Points: {stats.get('total_backups', 0)} | "
            f"Total Files Safely Parked: {stats.get('total_files_backed_up', 0)}"
        )
            
        self.restore_progress_bar.setVisible(False)
        self._on_table_selection() # Resync button limits

    def start_restore(self):
        """Pass the targeted manifest to the restore procedure logic!

        Confirms the restore of the selected snapshot's files, disables
        the buttons, shows the busy bar, and runs a RestoreWorker thread
        that calls restore_from_manifest.
        """
        row = self.manifests_table.currentRow()
        if row < 0: return
        
        path_item = self.manifests_table.item(row, 3)
        if not path_item: return
        
        target_path = path_item.text()
        count = self.manifests_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self, "Execute Restoration", 
            f"Are you sure you want to attempt restoring {count} files natively to your system from this snapshot?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.restore_button.setEnabled(False)
        self.refresh_manifests_button.setEnabled(False)
        self.delete_manifest_button.setEnabled(False)
        self.restore_progress_bar.setVisible(True)
        
        worker = RestoreWorker(self.restore_manager, target_path)
        self.add_worker_thread(worker)
        
        worker.finished_restore.connect(self._on_restore_completed)
        worker.error_occurred.connect(self._on_restore_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_restore_completed(self, results):
        """Report the restore outcome (restored count, warnings) and refresh."""
        restored = results.get("restored", 0)
        errors = results.get("error_details", [])
        
        if errors:
            QMessageBox.warning(self, "Restore Completed (With Warnings)", f"Restored {restored} items. Emitted {len(errors)} warnings! Check logs.")
            self.logger.warning(f"Restore output constraints: {errors}")
        else:
            QMessageBox.information(self, "Restore Completed", f"Successfully extracted and recovered {restored} files safely.")
            
        self.refresh_manifests()

    def _on_restore_error(self, err_string):
        """Log and show a fatal error dialog when the restore worker crashes."""
        self.logger.error(f"Restore Tab Thread Event Crash: {err_string}")
        QMessageBox.critical(self, "Snapshot Error", f"The operation aborted fatally: {err_string}")
        
    def _on_worker_finished(self, worker):
        """Hide the busy bar, re-enable refresh, and dispose the worker."""
        self.restore_progress_bar.setVisible(False)
        self.refresh_manifests_button.setEnabled(True)
        self.remove_worker_thread(worker)
        worker.deleteLater()

    def delete_snapshot(self):
        """Permanently delete the selected backup after confirmation.

        Calls RestoreManager.delete_backup by name; reports success or
        failure (e.g. already removed).
        """
        row = self.manifests_table.currentRow()
        if row < 0: return
        
        name_item = self.manifests_table.item(row, 0)
        target_name = name_item.text()
        
        reply = QMessageBox.warning(
            self, "Perma-Delete",
            f"WARNING: Destroying snapshot '{target_name}' cannot be undone. Remove this backup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes: return
        
        success = self.restore_manager.delete_backup(target_name)
        if success:
            QMessageBox.information(self, "Wiped", f"Terminated snapshot {target_name}.")
            self.refresh_manifests()
        else:
            QMessageBox.warning(self, "Error", f"Failed to unlink {target_name}. It might already be gone!")
