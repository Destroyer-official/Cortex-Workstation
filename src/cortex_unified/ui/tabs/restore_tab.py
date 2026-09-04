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

try:
    from cortex_unified.system_tools.vss_manager import VssManager
except Exception:  # pragma: no cover - optional backend
    VssManager = None  # type: ignore

try:
    from cortex_unified.system_tools.vss_health_analyzer import VssHealthAnalyzer
except Exception:  # pragma: no cover - optional backend
    VssHealthAnalyzer = None  # type: ignore

try:
    from cortex_unified.core.database import get_database
except Exception:  # pragma: no cover - optional backend
    get_database = None  # type: ignore


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
        self.vss_manager = VssManager() if VssManager is not None else None
        self.vss_health = VssHealthAnalyzer() if VssHealthAnalyzer is not None else None

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

        # --- Orphaned backend wiring: VSS shadow copies + health ---
        vss_group = QGroupBox("Volume Shadow Copies (VSS)")
        vss_layout = QVBoxLayout(vss_group)
        vss_controls = QHBoxLayout()
        self.vss_health_lbl = QLabel("VSS health: unknown (press List Shadow Copies).")
        vss_controls.addWidget(self.vss_health_lbl)
        vss_controls.addStretch()
        self.vss_list_button = QPushButton("List Shadow Copies")
        self.vss_list_button.clicked.connect(self.refresh_vss)
        self.vss_list_button.setMinimumHeight(28)
        self.vss_refresh_button = self.vss_list_button
        vss_controls.addWidget(self.vss_list_button)
        vss_layout.addLayout(vss_controls)

        self.vss_tree = QTreeWidget()
        self.vss_tree.setColumnCount(4)
        self.vss_tree.setHeaderLabels(['Volume / Shadow ID', 'Created', 'Provider', 'Storage / Status'])
        self.vss_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.vss_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.vss_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.vss_tree.header().setStretchLastSection(True)
        vss_layout.addWidget(self.vss_tree)
        self.vss_table = self.vss_tree  # Backwards compatibility alias

        self.vss_storage_lbl = QLabel("Shadow storage: n/a")
        vss_layout.addWidget(self.vss_storage_lbl)
        layout.addWidget(vss_group)

        # --- Orphaned backend wiring: persisted scan history & quarantine (Database) ---
        hist_group = QGroupBox("Persisted Database & Quarantine Management")
        hist_layout = QVBoxLayout(hist_group)

        self.hist_tabs = QTabWidget()

        # Tab 1: Scan History
        hist_tab1 = QWidget()
        hist_tab1_layout = QVBoxLayout(hist_tab1)
        hist_controls = QHBoxLayout()
        hist_controls.addStretch()
        self.history_refresh_button = QPushButton("Refresh Scan History")
        self.history_refresh_button.clicked.connect(self.refresh_scan_history)
        self.history_refresh_button.setMinimumHeight(28)
        hist_controls.addWidget(self.history_refresh_button)
        hist_tab1_layout.addLayout(hist_controls)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(['ID', 'Scan Type', 'Started', 'Status', 'Found', 'Freed (bytes)'])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hist_tab1_layout.addWidget(self.history_table)
        self.hist_tabs.addTab(hist_tab1, "Scan Run History")

        # Tab 2: Quarantine / Restorable Items
        hist_tab2 = QWidget()
        hist_tab2_layout = QVBoxLayout(hist_tab2)
        quarantine_controls = QHBoxLayout()
        self.restore_item_button = QPushButton("Restore Selected Item")
        self.restore_item_button.clicked.connect(self.restore_selected_quarantine_item)
        quarantine_controls.addWidget(self.restore_item_button)
        self.cleanup_quarantine_button = QPushButton("Clean Old Quarantine (30d+)")
        self.cleanup_quarantine_button.clicked.connect(self.cleanup_old_quarantine)
        quarantine_controls.addWidget(self.cleanup_quarantine_button)
        quarantine_controls.addStretch()
        self.quarantine_refresh_button = QPushButton("Refresh Quarantine")
        self.quarantine_refresh_button.clicked.connect(self.refresh_quarantine)
        quarantine_controls.addWidget(self.quarantine_refresh_button)
        hist_tab2_layout.addLayout(quarantine_controls)

        self.quarantine_table = QTableWidget()
        self.quarantine_table.setColumnCount(6)
        self.quarantine_table.setHorizontalHeaderLabels(['ID', 'Path', 'Size', 'Deleted At', 'Backup Path', 'Can Restore'])
        self.quarantine_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.quarantine_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.quarantine_table.horizontalHeader().setStretchLastSection(True)
        self.quarantine_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.quarantine_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        hist_tab2_layout.addWidget(self.quarantine_table)
        self.hist_tabs.addTab(hist_tab2, "Quarantine / Restorable Items")

        hist_layout.addWidget(self.hist_tabs)
        layout.addWidget(hist_group)

        QTimer.singleShot(100, self.refresh_manifests)
        QTimer.singleShot(150, self.refresh_vss)
        QTimer.singleShot(200, self.refresh_scan_history)

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

    def refresh_vss(self):
        """List VSS shadow copies + storage/health using orphaned backends.

        Uses VssManager.list_shadows/list_shadow_storage and
        VssHealthAnalyzer.inspect_health; read-only, failures leave the
        existing snapshot view untouched.
        """
        if self.vss_manager is None and self.vss_health is None:
            self.vss_health_lbl.setText("VSS backends unavailable on this host.")
            return
        try:
            shadows = self.vss_manager.list_shadows() if self.vss_manager else []
        except Exception as e:
            self.logger.warning(f"VSS shadow listing failed: {e}")
            shadows = []
        try:
            storages = self.vss_manager.list_shadow_storage() if self.vss_manager else []
        except Exception as e:
            self.logger.warning(f"VSS storage listing failed: {e}")
            storages = []
        self.vss_tree.clear()
        volume_map = {}
        for s in shadows:
            vol = getattr(s, "original_volume", "") or "System Volume"
            volume_map.setdefault(vol, []).append(s)

        for vol, v_shadows in volume_map.items():
            parent_item = QTreeWidgetItem([f"📁 Volume {vol}", "", "", f"{len(v_shadows)} snapshot(s)"])
            parent_font = QFont()
            parent_font.setBold(True)
            parent_item.setFont(0, parent_font)
            for s in v_shadows:
                sid = getattr(s, "shadow_id", "")
                created = getattr(s, "creation_time", "")
                prov = getattr(s, "provider", "")
                child = QTreeWidgetItem([f"  {sid}", str(created), str(prov), "Healthy / Active"])
                parent_item.addChild(child)
            self.vss_tree.addTopLevelItem(parent_item)

        self.vss_tree.expandAll()

        if storages:
            total_used = sum(getattr(x, "used_bytes", 0) or 0 for x in storages)
            self.vss_storage_lbl.setText(
                f"Shadow storage volumes: {len(storages)} | Total used: {total_used / (1024**3):.2f} GB"
            )
        else:
            self.vss_storage_lbl.setText("Shadow storage: none reported (requires Windows VSS).")
        if self.vss_health is not None:
            try:
                report = self.vss_health.inspect_health()
                self.vss_health_lbl.setText(
                    f"VSS writers healthy: {report.healthy_writer_count} | "
                    f"failed: {report.failed_writer_count}"
                )
            except Exception as e:
                self.logger.warning(f"VSS health inspect failed: {e}")
                self.vss_health_lbl.setText("VSS health: unavailable (see logs).")

    def refresh_scan_history(self):
        """Fill the history table from Database.get_scan_history (read-only)."""
        if get_database is None:
            self.history_table.setRowCount(0)
            return
        try:
            db = get_database()
            runs = db.get_scan_history(limit=100)
        except Exception as e:
            self.logger.warning(f"Scan history load failed: {e}")
            return
        self.history_table.setRowCount(len(runs))
        for i, run in enumerate(runs):
            started = getattr(run, "started_at", "")
            try:
                started_str = started.strftime("%Y-%m-%d %H:%M:%S") if hasattr(started, "strftime") else str(started)
            except Exception:
                started_str = str(started)
            self.history_table.setItem(i, 0, QTableWidgetItem(str(getattr(run, "id", ""))))
            self.history_table.setItem(i, 1, QTableWidgetItem(str(getattr(run, "scan_type", ""))))
            self.history_table.setItem(i, 2, QTableWidgetItem(started_str))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(getattr(run, "status", ""))))
            self.history_table.setItem(i, 4, QTableWidgetItem(str(getattr(run, "items_found", ""))))
            self.history_table.setItem(i, 5, QTableWidgetItem(str(getattr(run, "bytes_freed", ""))))

        self.refresh_quarantine()

    def refresh_quarantine(self):
        """Fill the quarantine table from Database.get_restorable_items."""
        if get_database is None:
            self.quarantine_table.setRowCount(0)
            return
        try:
            db = get_database()
            items = db.get_restorable_items()
        except Exception as e:
            self.logger.warning(f"Quarantine load failed: {e}")
            return
        self.quarantine_table.setRowCount(len(items))
        for i, item in enumerate(items):
            del_at = getattr(item, "deleted_at", "")
            try:
                del_str = del_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(del_at, "strftime") else str(del_at)
            except Exception:
                del_str = str(del_at)
            self.quarantine_table.setItem(i, 0, QTableWidgetItem(str(getattr(item, "id", ""))))
            self.quarantine_table.setItem(i, 1, QTableWidgetItem(str(getattr(item, "path", ""))))
            self.quarantine_table.setItem(i, 2, QTableWidgetItem(str(getattr(item, "size_bytes", ""))))
            self.quarantine_table.setItem(i, 3, QTableWidgetItem(del_str))
            self.quarantine_table.setItem(i, 4, QTableWidgetItem(str(getattr(item, "backup_path", ""))))
            can_res = "Yes" if getattr(item, "can_restore", True) else "No"
            self.quarantine_table.setItem(i, 5, QTableWidgetItem(can_res))

    def restore_selected_quarantine_item(self):
        """Mark the selected quarantine item as restored in Database."""
        row = self.quarantine_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Selection", "Select a quarantine item to restore.")
            return
        item_id_text = self.quarantine_table.item(row, 0).text()
        try:
            item_id = int(item_id_text)
            db = get_database()
            db.mark_item_restored(item_id)
            QMessageBox.information(self, "Restored", f"Quarantine item #{item_id} marked as restored.")
            self.refresh_quarantine()
        except Exception as exc:
            QMessageBox.critical(self, "Restore Error", str(exc))

    def cleanup_old_quarantine(self):
        """Purge quarantine records older than 30 days from Database."""
        try:
            db = get_database()
            count = db.cleanup_old_quarantine(days=30)
            QMessageBox.information(self, "Quarantine Purged", f"Purged {count} expired quarantine record(s).")
            self.refresh_quarantine()
        except Exception as exc:
            QMessageBox.critical(self, "Cleanup Error", str(exc))

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
