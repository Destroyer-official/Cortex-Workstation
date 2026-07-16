"""Tab for deep disk cleaning in Cortex Cleaner GUI."""

import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QGroupBox, QFormLayout, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont, QColor

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.core.deleter import Deleter
from cortex_unified.analyzers.deep_cleaner import DeepCleaner

class DeepCleanerWorker(QThread):
    finished_scan = Signal(list)
    error_occurred = Signal(str)
    status_updated = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._is_running = True

    def run(self):
        try:
            self.status_updated.emit("Deep scanning disk...")
            cleaner = DeepCleaner(self.config)
            
            def poll_progress():
                while self._is_running:
                    self.progress_updated.emit(0)
                    time.sleep(0.1)

            t = threading.Thread(target=poll_progress, daemon=True)
            t.start()
            
            def update_status(msg):
                self.status_updated.emit(msg)
                
            items = cleaner.find_junk(progress_callback=update_status)
            stats = cleaner.get_stats()
            
            self._is_running = False
            self.finished_scan.emit([items, stats])
        except Exception as e:
            self._is_running = False
            self.error_occurred.emit(str(e))

class DeepCleanerTab(BaseTab):
    """Tab for deep cleaner functionality (Temp, Cache, Logs, Orphans)."""

    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel('🧹 Deep Disk Cleaner')
        title.setStyleSheet('font-size: 18px; font-weight: bold; margin: 10px;')
        layout.addWidget(title)
        
        desc = QLabel('Safely remove temporary files, cache & orphaned application data.')
        desc.setStyleSheet('color: gray; margin-bottom: 5px;')
        layout.addWidget(desc)
        
        # Options
        options_group = QGroupBox('Target Areas')
        options_layout = QHBoxLayout(options_group)
        self.lbl_status = QLabel("Ready to scan")
        options_layout.addWidget(self.lbl_status)
        layout.addWidget(options_group)
        
        # Actions
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.scan_btn = QPushButton('🔍 Start Deep Scan')
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setMinimumHeight(35)
        self.scan_btn.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; font-size: 13px; }')
        buttons_layout.addWidget(self.scan_btn)
        
        self.select_all_btn = QPushButton('☑ Check All')
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setMinimumHeight(35)
        buttons_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton('☐ Uncheck All')
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setMinimumHeight(35)
        buttons_layout.addWidget(self.deselect_all_btn)

        self.clean_btn = QPushButton('🗑️ Clean Selected')
        self.clean_btn.clicked.connect(self.start_clean)
        self.clean_btn.setEnabled(False)
        self.clean_btn.setMinimumHeight(35)
        self.clean_btn.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; font-size: 13px; background-color: #8B0000; color: white; }')
        buttons_layout.addWidget(self.clean_btn)
        layout.addLayout(buttons_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(10)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results Tree
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(['Category / Items', 'Type', 'Path', 'Size'])
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)
        
        self.summary_lbl = QLabel('')
        self.summary_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.summary_lbl)

    def start_scan(self):
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.tree.clear()
        
        worker = DeepCleanerWorker(self.config)
        self.add_worker_thread(worker)
        
        worker.status_updated.connect(self.lbl_status.setText)
        worker.progress_updated.connect(lambda: None)
        worker.finished_scan.connect(self.scan_finished)
        worker.error_occurred.connect(self.scan_error)
        worker.finished.connect(lambda: self.operation_finished(worker))
        worker.start()

    def format_bytes(self, bytes_count: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"

    def scan_finished(self, result):
        items, stats = result
        self.tree.blockSignals(True)
        
        # Group by category
        categories = {}
        for item in items:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
            
        for cat, cat_items in categories.items():
            cat_size = sum(i["size"] for i in cat_items)
            cat_node = QTreeWidgetItem(self.tree)
            cat_node.setText(0, f"📁 {cat} ({len(cat_items)} items)")
            cat_node.setText(3, self.format_bytes(cat_size))
            cat_node.setFlags(cat_node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            cat_node.setCheckState(0, Qt.CheckState.Checked)
            
            for item in cat_items:
                child = QTreeWidgetItem(cat_node)
                path = item["path"]
                child.setText(0, item["description"])
                child.setText(1, "Orphaned" if item["is_orphan"] else "File/Dir")
                child.setText(2, str(path))
                child.setText(3, self.format_bytes(item["size"]))
                # Highlight orphans
                if item["is_orphan"]:
                    child.setForeground(1, QColor("#e74c3c"))
                    child.setToolTip(0, "Leftover from uninstalled application!")
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Checked)
                # Store path inside user data
                child.setData(0, Qt.ItemDataRole.UserRole, path)
                
            cat_node.setExpanded(True)
            
        self.tree.blockSignals(False)
        
        total_size = stats.get('total_size_human', '0 B')
        file_count = stats.get('items_found', 0)
        
        self.summary_lbl.setText(f'Found {file_count} junk items, totaling {total_size}')
        self.lbl_status.setText('Scan completed ✅')
        self.clean_btn.setEnabled(file_count > 0)
        self.update_selection_summary()

    def _on_item_changed(self, item, column):
        """Handle cascade checking/unchecking logic"""
        if column == 0:
            self.tree.blockSignals(True)
            state = item.checkState(0)
            
            # If parent, check all children
            if item.childCount() > 0:
                for i in range(item.childCount()):
                    item.child(i).setCheckState(0, state)
            else:
                # If child, possibly update parent state
                parent = item.parent()
                if parent:
                    all_checked = True
                    any_checked = False
                    for i in range(parent.childCount()):
                        if parent.child(i).checkState(0) == Qt.CheckState.Checked:
                            any_checked = True
                        else:
                            all_checked = False
                    
                    if all_checked:
                        parent.setCheckState(0, Qt.CheckState.Checked)
                    elif any_checked:
                        parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                    else:
                        parent.setCheckState(0, Qt.CheckState.Unchecked)
                        
            self.tree.blockSignals(False)
            self.update_selection_summary()

    def update_selection_summary(self):
        checked_count = 0
        total_size = 0
        
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    checked_count += 1
                    
        self.clean_btn.setText(f'🗑️ Clean Selected ({checked_count})')

    def scan_error(self, error):
        self.lbl_status.setText(f'Error: {error}')
        QMessageBox.critical(self, 'Scan Error', f'An error occurred:\\n{error}')

    def start_clean(self):
        selected_paths = []
        
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    path = child.data(0, Qt.ItemDataRole.UserRole)
                    if path:
                        selected_paths.append(path)
                        
        if not selected_paths:
            QMessageBox.warning(self, 'No Selection', 'Please select items to clean.')
            return
            
        reply = QMessageBox.question(
            self, 'Confirm Deep Clean', 
            f'Permanently delete {len(selected_paths)} items?\\nThis action clears caches and orphaned app data.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.scan_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText("Cleaning items...")
        
        try:
            deleter = Deleter(dry_run=False, use_trash=True)
            # Separate files from dirs conceptually (deleter handles it usually, but we need to pass correctly)
            files_to_del = [p for p in selected_paths if p.is_file()]
            dirs_to_del = [p for p in selected_paths if p.is_dir()]
            
            result = deleter.delete(files_to_del, dirs_to_del)
            files_deleted = result.get('files_deleted', 0)
            dirs_deleted = result.get('dirs_deleted', 0)
            errors = result.get('errors', [])
            
            msg = f'Successfully cleaned {files_deleted} files and {dirs_deleted} directories.'
            if errors:
                msg += f'\\n{len(errors)} errors occurred.'
                
            QMessageBox.information(self, 'Cleaning Complete', msg)
            self.logger.info(f'Deep cleaned {files_deleted+dirs_deleted} items')
            
        except Exception as e:
            QMessageBox.critical(self, 'Cleaning Error', f'An error occurred:\\n{str(e)}')
            
        self.start_scan()

    def select_all(self):
        self._toggle_checkboxes(Qt.CheckState.Checked)

    def deselect_all(self):
        self._toggle_checkboxes(Qt.CheckState.Unchecked)

    def _toggle_checkboxes(self, state):
        self.tree.blockSignals(True)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            parent.setCheckState(0, state)
            for j in range(parent.childCount()):
                parent.child(j).setCheckState(0, state)
        self.tree.blockSignals(False)
        self.update_selection_summary()

    def operation_finished(self, worker):
        self.progress_bar.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.remove_worker_thread(worker)
        worker.deleteLater()
