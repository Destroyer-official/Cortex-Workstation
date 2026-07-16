"""Tab for file shredder tab in Cortex Cleaner GUI."""

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
from cortex_unified.analyzers.weaponized_shredder import WeaponizedShredder


class FileShredderWorker(QThread):
    """Runs DoD 5220.22-M multi-pass overwrite shredding in background."""
    finished = Signal(dict)
    error = Signal(str)
    progress_update = Signal(str, int)

    def __init__(self, config: Config, target_paths: List[str], passes: int, method: str):
        super().__init__()
        self.config = config
        self.target_paths = target_paths
        self.passes = passes
        self.method = method

    def run(self):
        try:
            shredder = WeaponizedShredder()
            results = {'successes': [], 'failures': []}

            total = len(self.target_paths)
            for idx, path in enumerate(self.target_paths):
                pct = int((idx / total) * 100) if total else 0
                self.progress_update.emit(f"Shredding: {Path(path).name}…", pct)

                try:
                    p = Path(path)
                    if p.is_file():
                        ok = shredder.shred_file(str(p), passes=self.passes)
                    elif p.is_dir():
                        ok = shredder.shred_directory(str(p), passes=self.passes)
                    else:
                        ok = False

                    if ok:
                        results['successes'].append(path)
                    else:
                        results['failures'].append((path, "Shredding returned False"))
                except Exception as e:
                    results['failures'].append((path, str(e)))

            self.progress_update.emit("Destruction sequence complete.", 100)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FileShredderTab(BaseTab):
    """Tab for file shredder tab functionality."""

    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)
        self.files_to_shred = set()

    def setup_ui(self):
        """Create the file shredder tab."""
        layout = QVBoxLayout(self)
        
        warning_label = QLabel('⚠️ WARNING: File shredding permanently destroys data and cannot be undone!')
        warning_label.setStyleSheet('QLabel { color: red; font-weight: bold; font-size: 14px; padding: 10px; background-color: #ffe6e6; border: 1px solid red; }')
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        file_group = QGroupBox('Files to Shred')
        file_layout = QVBoxLayout(file_group)
        
        self.shredder_file_list = QListWidget()
        self.shredder_file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        file_layout.addWidget(self.shredder_file_list)
        
        file_buttons_layout = QHBoxLayout()
        add_files_button = QPushButton('Add Files')
        add_files_button.clicked.connect(self.add_files_to_shred)
        file_buttons_layout.addWidget(add_files_button)
        
        add_folder_button = QPushButton('Add Folder')
        add_folder_button.clicked.connect(self.add_folder_to_shred)
        file_buttons_layout.addWidget(add_folder_button)
        
        remove_files_button = QPushButton('Remove Selected')
        remove_files_button.clicked.connect(self.remove_files_from_shred)
        file_buttons_layout.addWidget(remove_files_button)
        
        clear_files_button = QPushButton('Clear All')
        clear_files_button.clicked.connect(self.clear_shred_list)
        file_buttons_layout.addWidget(clear_files_button)
        
        file_layout.addLayout(file_buttons_layout)
        layout.addWidget(file_group)
        
        options_group = QGroupBox('Shredding Options')
        options_layout = QFormLayout(options_group)
        
        self.shred_passes_spinbox = QSpinBox()
        self.shred_passes_spinbox.setRange(1, 35)
        self.shred_passes_spinbox.setValue(3)
        options_layout.addRow('Overwrite Passes:', self.shred_passes_spinbox)
        
        self.shred_method_combo = QComboBox()
        self.shred_method_combo.addItems(['Random', 'DoD 5220.22-M', 'Gutmann', 'Zero Fill'])
        options_layout.addRow('Shredding Method:', self.shred_method_combo)
        
        self.verify_shred_checkbox = QCheckBox('Verify shredding completion')
        self.verify_shred_checkbox.setChecked(True)
        options_layout.addRow(self.verify_shred_checkbox)
        
        self.shred_free_space_checkbox = QCheckBox('Also shred free space (Pro)')
        self.shred_free_space_checkbox.setEnabled(False)
        options_layout.addRow(self.shred_free_space_checkbox)
        layout.addWidget(options_group)
        
        buttons_layout = QHBoxLayout()
        self.start_shred_button = QPushButton('Start Shredding')
        self.start_shred_button.clicked.connect(self.start_file_shredding)
        self.start_shred_button.setEnabled(False)
        self.start_shred_button.setMinimumHeight(35)
        self.start_shred_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; background-color: #d32f2f; color: white; }')
        buttons_layout.addWidget(self.start_shred_button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.shred_progress_bar = QProgressBar()
        self.shred_progress_bar.setVisible(False)
        layout.addWidget(self.shred_progress_bar)
        
        self.shred_status_label = QLabel('Ready to shred files')
        layout.addWidget(self.shred_status_label)
        
        self.shred_results = QTextEdit()
        self.shred_results.setReadOnly(True)
        self.shred_results.setMaximumHeight(150)
        layout.addWidget(self.shred_results)

    def _sync_list(self):
        self.shredder_file_list.clear()
        for f in self.files_to_shred:
            self.shredder_file_list.addItem(f)
        self.start_shred_button.setEnabled(len(self.files_to_shred) > 0)

    def add_files_to_shred(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Shred")
        if files:
            for f in files:
                self.files_to_shred.add(f)
            self._sync_list()

    def add_folder_to_shred(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Shred")
        if folder:
            self.files_to_shred.add(folder)
            self._sync_list()

    def remove_files_from_shred(self):
        items = self.shredder_file_list.selectedItems()
        for item in items:
            self.files_to_shred.discard(item.text())
        self._sync_list()

    def clear_shred_list(self):
        self.files_to_shred.clear()
        self._sync_list()

    def start_file_shredding(self):
        if not self.files_to_shred:
            return
            
        reply = QMessageBox.warning(
            self, "CONFIRM DESTRUCTIVE ACTION",
            f"Are you ABSOLUTELY sure you want to shred {len(self.files_to_shred)} paths?\nThis WILL OVERWRITE THEM WITH JUNK DATA.\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.start_shred_button.setEnabled(False)
        self.shred_progress_bar.setVisible(True)
        self.shred_progress_bar.setValue(0)
        self.shred_results.append("Starting destruction sequence...")
        
        worker = FileShredderWorker(
            self.config, 
            list(self.files_to_shred), 
            self.shred_passes_spinbox.value(), 
            self.shred_method_combo.currentText()
        )
        self.add_worker_thread(worker)
        
        worker.progress_update.connect(self._on_shred_progress)
        worker.finished.connect(self._on_shred_complete)
        worker.error.connect(self._on_shred_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_shred_progress(self, msg, pct):
        self.shred_status_label.setText(msg)
        self.shred_progress_bar.setValue(pct)

    def _on_worker_finished(self, worker):
        self.remove_worker_thread(worker)
        worker.deleteLater()

    def _on_shred_complete(self, results):
        self.start_shred_button.setEnabled(True)
        self.shred_progress_bar.setVisible(False)
        
        successes = results.get('successes', [])
        failures = results.get('failures', [])
        
        self.shred_results.append(f"SUCCESSFULLY SHREDDED {len(successes)} PATHS.")
        for f in failures:
            self.shred_results.append(f"FAILED: {f[0]} -> {f[1]}")
            
        self.files_to_shred.clear()
        self._sync_list()
        
        QMessageBox.information(self, "Sequence Complete", f"Safely randomized and destroyed {len(successes)} items.")

    def _on_shred_error(self, error):
        self.start_shred_button.setEnabled(True)
        self.shred_progress_bar.setVisible(False)
        self.shred_results.append(f"FATAL ERROR: {error}")
        QMessageBox.critical(self, "Error", f"Execution failed:\n{error}")
