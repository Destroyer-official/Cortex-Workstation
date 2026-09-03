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
from cortex_unified.analyzers.advanced_shredder import AdvancedShredder
from cortex_unified.system_tools.free_space_wipe import FreeSpaceWiper
from cortex_unified.licensing import Feature, allowed


class FileShredderWorker(QThread):
    """Runs DoD 5220.22-M multi-pass overwrite shredding in background."""
    finished = Signal(dict)
    error = Signal(str)
    progress_update = Signal(str, int)

    def __init__(self, config: Config, target_paths: List[str], passes: int, method: str,
                 wipe_drive: Optional[str] = None):
        """__init__."""
        super().__init__()
        self.config = config
        self.target_paths = target_paths
        self.passes = passes
        self.method = method
        self.wipe_drive = wipe_drive
        """__init__."""
        """__init__."""

    def run(self):
        """run."""
        try:
            shredder = AdvancedShredder()
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

            if self.wipe_drive:
                self.progress_update.emit(
                    f"Wiping free space on {self.wipe_drive}: (this may take a long time)…", 95)
                try:
                    wipe = FreeSpaceWiper().wipe(self.wipe_drive)
                    results['free_space_wipe'] = {
                        'success': wipe.success,
                        'message': wipe.message,
                        'effective': wipe.effective,
                    }
                    self.progress_update.emit(wipe.message, 99)
                except Exception as e:
                    results['free_space_wipe'] = {
                        'success': False, 'message': str(e), 'effective': False}
                    self.progress_update.emit(f"Free-space wipe failed: {e}", 99)

            self.progress_update.emit("Destruction sequence complete.", 100)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
        """run."""
        """run."""


class FileShredderTab(BaseTab):
    """Tab for file shredder tab functionality."""

    def __init__(self, config, logger, safety_manager):
        """__init__."""
        super().__init__(config, logger, safety_manager)
        self.files_to_shred = set()
        """__init__."""
        """__init__."""

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
        
        if allowed(Feature.SHRED_MULTIPASS):
            self.shred_passes_spinbox = QSpinBox()
            self.shred_passes_spinbox.setRange(1, 35)
            self.shred_passes_spinbox.setValue(3)
        else:
            self.shred_passes_spinbox = QSpinBox()
            self.shred_passes_spinbox.setRange(1, 1)
            self.shred_passes_spinbox.setValue(1)
            self.shred_passes_spinbox.setToolTip(
                'Multi-pass shredding requires the Premium tier; '
                'overwrite passes are capped at 1.')
        options_layout.addRow('Overwrite Passes:', self.shred_passes_spinbox)
        
        self.shred_method_combo = QComboBox()
        self.shred_method_combo.addItems(['Random', 'DoD 5220.22-M', 'Gutmann', 'Zero Fill'])
        options_layout.addRow('Shredding Method:', self.shred_method_combo)
        
        self.verify_shred_checkbox = QCheckBox('Verify shredding completion')
        self.verify_shred_checkbox.setChecked(True)
        options_layout.addRow(self.verify_shred_checkbox)
        
        self.shred_free_space_checkbox = QCheckBox('Also shred free space (Pro)')
        if allowed(Feature.FREE_SPACE_WIPE):
            self.shred_free_space_checkbox.setEnabled(True)
            self.shred_free_space_checkbox.setToolTip(
                'After shredding files, overwrite the unused space on the '
                'drive (cipher /w). May take a long time.')
        else:
            self.shred_free_space_checkbox.setEnabled(False)
            self.shred_free_space_checkbox.setToolTip(
                'Shredding free space requires an upgrade to the Premium '
                'tier (or higher).')
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
        """_sync_list."""
        self.shredder_file_list.clear()
        for f in self.files_to_shred:
            self.shredder_file_list.addItem(f)
        self.start_shred_button.setEnabled(len(self.files_to_shred) > 0)
        """_sync_list."""
        """_sync_list."""

    def add_files_to_shred(self):
        """add_files_to_shred."""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Shred")
        if files:
            for f in files:
                self.files_to_shred.add(f)
            self._sync_list()
        """add_files_to_shred."""
        """add_files_to_shred."""

    def add_folder_to_shred(self):
        """add_folder_to_shred."""
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Shred")
        if folder:
            self.files_to_shred.add(folder)
            self._sync_list()
        """add_folder_to_shred."""
        """add_folder_to_shred."""

    def remove_files_from_shred(self):
        """remove_files_from_shred."""
        items = self.shredder_file_list.selectedItems()
        for item in items:
            self.files_to_shred.discard(item.text())
        self._sync_list()
        """remove_files_from_shred."""
        """remove_files_from_shred."""

    def clear_shred_list(self):
        """clear_shred_list."""
        self.files_to_shred.clear()
        self._sync_list()
        """clear_shred_list."""
        """clear_shred_list."""

    def _resolve_passes(self):
        """Entitlement-checked pass count; never exceeds the licensed cap."""
        passes = self.shred_passes_spinbox.value()
        if passes > 1 and not allowed(Feature.SHRED_MULTIPASS):
            self.shred_results.append(
                'Multi-pass shredding requires Premium - capped this run to 1 pass.')
            return 1
        return passes

    @staticmethod
    def _derive_drive_letter(paths):
        """Single drive letter shared by all target paths, else None."""
        anchors = {Path(p).anchor for p in paths}
        if len(anchors) != 1:
            return None
        anchor = anchors.pop().rstrip(':\\')
        return anchor or None

    def start_file_shredding(self):
        """start_file_shredding."""
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

        passes = self._resolve_passes()

        wipe_drive = None
        if self.shred_free_space_checkbox.isEnabled() and self.shred_free_space_checkbox.isChecked():
            wipe_drive = self._derive_drive_letter(self.files_to_shred)
            if not wipe_drive:
                QMessageBox.warning(
                    self, 'Free-space Wipe',
                    'All paths must be on the same drive to shred its free space.')
                return
            reply = QMessageBox.warning(
                self, "CONFIRM FREE-SPACE WIPE",
                f"Also overwrite ALL FREE SPACE on drive {wipe_drive}: ?\n"
                "This may take a long time (up to an hour per drive).\n"
                "Continue?",
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
            passes, 
            self.shred_method_combo.currentText(),
            wipe_drive=wipe_drive
        )
        self.add_worker_thread(worker)
        
        worker.progress_update.connect(self._on_shred_progress)
        worker.finished.connect(self._on_shred_complete)
        worker.error.connect(self._on_shred_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()
        """start_file_shredding."""
        """start_file_shredding."""

    def _on_shred_progress(self, msg, pct):
        """_on_shred_progress."""
        self.shred_status_label.setText(msg)
        self.shred_progress_bar.setValue(pct)
        """_on_shred_progress."""
        """_on_shred_progress."""

    def _on_worker_finished(self, worker):
        """_on_worker_finished."""
        self.remove_worker_thread(worker)
        worker.deleteLater()
        """_on_worker_finished."""
        """_on_worker_finished."""

    def _on_shred_complete(self, results):
        """_on_shred_complete."""
        self.start_shred_button.setEnabled(True)
        self.shred_progress_bar.setVisible(False)
        
        successes = results.get('successes', [])
        failures = results.get('failures', [])
        
        self.shred_results.append(f"SUCCESSFULLY SHREDDED {len(successes)} PATHS.")
        for f in failures:
            self.shred_results.append(f"FAILED: {f[0]} -> {f[1]}")

        summary = f"Safely randomized and destroyed {len(successes)} items."
        wipe = results.get('free_space_wipe')
        if wipe:
            if wipe.get('success'):
                self.shred_results.append(f"FREE SPACE OK: {wipe.get('message')}")
                summary += f"\nFree space: {wipe.get('message')}"
            else:
                self.shred_results.append(f"FREE SPACE FAILED: {wipe.get('message')}")
                summary += f"\nFree-space wipe FAILED: {wipe.get('message')}"
            
        self.files_to_shred.clear()
        self._sync_list()
        
        QMessageBox.information(self, "Sequence Complete", summary)
        """_on_shred_complete."""
        """_on_shred_complete."""

    def _on_shred_error(self, error):
        """_on_shred_error."""
        self.start_shred_button.setEnabled(True)
        self.shred_progress_bar.setVisible(False)
        self.shred_results.append(f"FATAL ERROR: {error}")
        QMessageBox.critical(self, "Error", f"Execution failed:\n{error}")
        """_on_shred_error."""
        """_on_shred_error."""
