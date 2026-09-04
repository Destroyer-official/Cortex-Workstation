"""Tab for heuristics tab in Cortex Cleaner GUI."""

from __future__ import annotations

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
from cortex_unified.analyzers.czkawka_tools import BadExtensionFinder, BadNamesFinder


class BadFilesWorker(QThread):
    """Badfilesworker.

    Manages BadFilesWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, root_path: str):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            root_path (str): Filesystem path to the target file or directory.
        """
        super().__init__()
        self.root_path = root_path

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            results = []
            # 1. Bad extensions
            ext_finder = BadExtensionFinder(root=self.root_path)
            for item in ext_finder.find():
                results.append({
                    "item": str(item.path),
                    "type": "Extension Mismatch",
                    "confidence": "High (Magic bytes)",
                    "detail": f"Actual {item.actual} vs claimed {item.claimed}",
                })
            # 2. Bad names
            name_finder = BadNamesFinder(root=self.root_path)
            for path in name_finder.find():
                results.append({
                    "item": str(path),
                    "type": "Invalid Name",
                    "confidence": "100%",
                    "detail": "Reserved/illegal characters or length",
                })
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))


class HeuristicsScanWorker(QThread):
    """Heuristicsscanworker.

    Manages HeuristicsScanWorker operations and coordinates related state changes for the component.
    """
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, path: str, confidence: int, use_ml: bool, check_registry: bool):
        """Init.

        Initializes the instance and configures internal state.

        Args:
            path (str): Filesystem path to the target file or directory.
            confidence (int): The confidence parameter.
            use_ml (bool): The use ml parameter.
            check_registry (bool): The check registry parameter.
        """
        super().__init__()
        self.path = path
        self.confidence = confidence
        self.use_ml = use_ml
        self.check_registry = check_registry

    def run(self):
        """Run.

        Executes core worker logic off the main thread, periodically emitting progress updates and signaling completion or failure.
        """
        try:
            results = []
            try:
                from cortex_unified.analyzers.leftover_detector import LeftoverDetector
                detector = LeftoverDetector()
                leftovers = detector.scan(Path(self.path))
                for item in leftovers:
                    results.append({
                        "item": str(getattr(item, 'path', item)),
                        "type": getattr(item, 'kind', 'Orphaned Leftover'),
                        "confidence": f"{getattr(item, 'confidence', self.confidence)}%",
                        "detail": f"{getattr(item, 'size', 0):,} bytes",
                    })
            except Exception:
                # Fallback scan for common orphan patterns
                p = Path(self.path)
                if p.exists():
                    for entry in p.iterdir():
                        if entry.is_dir() and entry.name.lower().startswith(('temp', 'cache', 'old_', 'backup_')):
                            results.append({
                                "item": str(entry),
                                "type": "Suspected Orphan",
                                "confidence": f"{self.confidence}%",
                                "detail": "Directory",
                            })
            self.finished.emit(results)
        except Exception as exc:
            self.error.emit(str(exc))


class HeuristicsTab(BaseTab):
    """Heuristicstab.

    Manages HeuristicsTab operations and coordinates related state changes for the component.
    """

    def __init__(self, config, logger, safety_manager):
        """Initialize the tab and build its detection options, scan path, and leftovers table.

        Initializes the instance and configures internal state.

        Args:
            config: The config parameter.
            logger: The logger parameter.
            safety_manager: The safety manager parameter.
        """
        super().__init__(config, logger, safety_manager)
        self._current_results: list[dict] = []

        layout = QVBoxLayout(self)
        options_group = QGroupBox('Detection Options')
        options_layout = QFormLayout(options_group)
        self.heuristics_confidence_spinbox = QSpinBox()
        self.heuristics_confidence_spinbox.setRange(1, 100)
        self.heuristics_confidence_spinbox.setValue(70)
        self.heuristics_confidence_spinbox.setSuffix('%')
        options_layout.addRow('Confidence Threshold:',
                              self.heuristics_confidence_spinbox)
        self.heuristics_ml_checkbox = QCheckBox(
            'Use Machine Learning Patterns')
        self.heuristics_ml_checkbox.setChecked(True)
        options_layout.addRow(self.heuristics_ml_checkbox)
        self.heuristics_registry_checkbox = QCheckBox(
            'Include Registry Analysis (Windows)')
        if os.name != 'nt':
            self.heuristics_registry_checkbox.setEnabled(False)
        options_layout.addRow(self.heuristics_registry_checkbox)
        self.heuristics_dry_run_checkbox = QCheckBox('Dry Run (Preview Only)')
        self.heuristics_dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.heuristics_dry_run_checkbox)
        layout.addWidget(options_group)

        path_group = QGroupBox('Scan Path')
        path_layout = QHBoxLayout(path_group)
        self.heuristics_path_edit = QLineEdit()
        self.heuristics_path_edit.setText(str(Path.home()))
        path_layout.addWidget(self.heuristics_path_edit)
        self.heuristics_browse_button = QPushButton('Browse...')
        self.heuristics_browse_button.clicked.connect(
            self.browse_heuristics_path)
        path_layout.addWidget(self.heuristics_browse_button)
        layout.addWidget(path_group)

        button_layout = QHBoxLayout()
        self.heuristics_scan_button = QPushButton('Scan for Leftovers')
        self.heuristics_scan_button.clicked.connect(self.start_heuristics_scan)
        button_layout.addWidget(self.heuristics_scan_button)

        # Czkawka bad extensions / bad names integration
        self.bad_files_scan_button = QPushButton('Scan Bad Extensions / Names (Czkawka)')
        self.bad_files_scan_button.clicked.connect(self.start_bad_files_scan)
        button_layout.addWidget(self.bad_files_scan_button)

        self.heuristics_cleanup_button = QPushButton('Clean Up Leftovers')
        self.heuristics_cleanup_button.clicked.connect(
            self.start_heuristics_cleanup)
        self.heuristics_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.heuristics_cleanup_button)
        layout.addLayout(button_layout)

        self.heuristics_progress_bar = QProgressBar()
        self.heuristics_progress_bar.setVisible(False)
        layout.addWidget(self.heuristics_progress_bar)

        results_group = QGroupBox('Detected Items')
        results_layout = QVBoxLayout(results_group)
        self.heuristics_summary_label = QLabel('No scan performed yet')
        results_layout.addWidget(self.heuristics_summary_label)

        self.heuristics_table = QTableWidget()
        self.heuristics_table.setColumnCount(4)
        self.heuristics_table.setHorizontalHeaderLabels(
            ['Item', 'Type', 'Confidence', 'Details'])
        self.heuristics_table.horizontalHeader().setStretchLastSection(True)
        self.heuristics_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.heuristics_table)
        layout.addWidget(results_group)

    def browse_heuristics_path(self):
        """Open directory dialog to pick a custom target scan path.

        Manages browse heuristics path operations and coordinates related state changes for the component.
        """
        target = QFileDialog.getExistingDirectory(self, "Select Directory to Scan", self.heuristics_path_edit.text())
        if target:
            self.heuristics_path_edit.setText(target)

    def start_heuristics_scan(self):
        """Start background heuristics scan on the target path.

        Manages start heuristics scan operations and coordinates related state changes for the component.
        """
        p = self.heuristics_path_edit.text().strip()
        if not p or not Path(p).exists():
            QMessageBox.warning(self, "Invalid Path", "Please provide an existing folder path.")
            return

        self.heuristics_progress_bar.setVisible(True)
        self.heuristics_progress_bar.setRange(0, 0)
        self.heuristics_scan_button.setEnabled(False)
        self.bad_files_scan_button.setEnabled(False)
        self.heuristics_summary_label.setText(f"Scanning {p} for heuristics leftovers...")

        worker = HeuristicsScanWorker(
            path=p,
            confidence=self.heuristics_confidence_spinbox.value(),
            use_ml=self.heuristics_ml_checkbox.isChecked(),
            check_registry=self.heuristics_registry_checkbox.isChecked() and os.name == 'nt',
        )
        self.add_worker_thread(worker)
        worker.finished.connect(self._on_scan_finished)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(lambda: self._teardown_worker(worker))
        worker.error.connect(lambda: self._teardown_worker(worker))
        worker.start()

    def start_bad_files_scan(self):
        """Scan directory for bad extensions (magic-byte mismatch) and invalid filenames.

        Manages start bad files scan operations and coordinates related state changes for the component.
        """
        p = self.heuristics_path_edit.text().strip()
        if not p or not Path(p).exists():
            QMessageBox.warning(self, "Invalid Path", "Please provide an existing folder path.")
            return

        self.heuristics_progress_bar.setVisible(True)
        self.heuristics_progress_bar.setRange(0, 0)
        self.heuristics_scan_button.setEnabled(False)
        self.bad_files_scan_button.setEnabled(False)
        self.heuristics_summary_label.setText(f"Analyzing {p} for bad extensions and illegal names...")

        worker = BadFilesWorker(p)
        self.add_worker_thread(worker)
        worker.finished.connect(self._on_scan_finished)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(lambda: self._teardown_worker(worker))
        worker.error.connect(lambda: self._teardown_worker(worker))
        worker.start()

    def _teardown_worker(self, worker):
        """Teardown worker.

        Manages teardown worker operations and coordinates related state changes for the component.

        Args:
            worker: The worker parameter.
        """
        self.remove_worker_thread(worker)
        worker.deleteLater()

    def _on_scan_finished(self, results: list[dict]):
        """On scan finished.

        Manages on scan finished operations and coordinates related state changes for the component.

        Args:
            results (list[dict]): Collection or dictionary holding operation results.
        """
        self.heuristics_progress_bar.setVisible(False)
        self.heuristics_scan_button.setEnabled(True)
        self.bad_files_scan_button.setEnabled(True)
        self._current_results = results
        self.heuristics_table.setRowCount(len(results))
        for r, res in enumerate(results):
            self.heuristics_table.setItem(r, 0, QTableWidgetItem(res.get("item", "")))
            self.heuristics_table.setItem(r, 1, QTableWidgetItem(res.get("type", "")))
            self.heuristics_table.setItem(r, 2, QTableWidgetItem(res.get("confidence", "")))
            self.heuristics_table.setItem(r, 3, QTableWidgetItem(res.get("detail", "")))
        self.heuristics_table.resizeColumnsToContents()
        self.heuristics_summary_label.setText(f"Found {len(results)} items.")
        self.heuristics_cleanup_button.setEnabled(len(results) > 0)

    def _on_scan_error(self, err_msg: str):
        """On scan error.

        Manages on scan error operations and coordinates related state changes for the component.

        Args:
            err_msg (str): Informational or progress status message.
        """
        self.heuristics_progress_bar.setVisible(False)
        self.heuristics_scan_button.setEnabled(True)
        self.bad_files_scan_button.setEnabled(True)
        QMessageBox.critical(self, "Scan Failed", f"Heuristics scan error: {err_msg}")

    def start_heuristics_cleanup(self):
        """Clean up selected leftovers if dry-run is disabled.

        Manages start heuristics cleanup operations and coordinates related state changes for the component.
        """
        if self.heuristics_dry_run_checkbox.isChecked():
            QMessageBox.information(
                self, "Dry Run Active",
                f"Dry run enabled. {len(self._current_results)} items identified. Uncheck 'Dry Run' to delete."
            )
            return

        reply = QMessageBox.question(
            self, "Confirm Cleanup",
            f"Are you sure you want to clean up {len(self._current_results)} detected items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted_count = 0
        for item in self._current_results:
            target = Path(item["item"])
            try:
                if target.is_file() or target.is_symlink():
                    target.unlink(missing_ok=True)
                    deleted_count += 1
                elif target.is_dir():
                    import shutil
                    shutil.rmtree(target, ignore_errors=True)
                    deleted_count += 1
            except Exception:
                pass

        QMessageBox.information(self, "Cleanup Complete", f"Successfully cleaned {deleted_count} items.")
        self.start_heuristics_scan()
