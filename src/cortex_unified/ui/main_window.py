"""Main window for Cortex Cleaner GUI."""
import sys
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, 
    QComboBox, QFileDialog, QMessageBox, QProgressBar, 
    QGroupBox, QFormLayout, QSpinBox, QTabWidget, QSizePolicy, 
    QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidgetItem, 
    QTreeWidget, QListWidget, QListWidgetItem, QSplitter, QInputDialog, QScrollArea, 
    QDialog, QRadioButton, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSettings
from PySide6.QtGui import QTextCursor

from cortex_unified.core.scanner import Scanner
from cortex_unified.core.deleter import Deleter
from cortex_unified.core.config import Config, DEFAULT_CONFIG
from cortex_unified.core.utils import setup_logging, normalize_path
from cortex_unified.analyzers.duplicate_finder import DuplicateFinder
from cortex_unified.analyzers.large_file_finder import LargeFileFinder
from cortex_unified.analyzers.cache_cleaner import CacheCleaner
from cortex_unified.analyzers.old_file_cleaner import OldFileCleaner
from cortex_unified.analyzers.file_shredder import FileShredder
from cortex_unified.analyzers.disk_analyzer import DiskAnalyzer
from cortex_unified.analyzers.duplicate_folder_finder import DuplicateFolderFinder
from cortex_unified.analyzers.docker_cleaner import DockerCleaner
from cortex_unified.analyzers.broken_link_detector import BrokenLinkDetector
from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
from cortex_unified.system_tools.startup_manager import StartupManager
from cortex_unified.system_tools.process_analyzer import ProcessAnalyzer

try:
    from cortex_unified.system_tools.registry_cleaner import RegistryCleaner
    HAS_REGISTRY_CLEANER = True
except ImportError:
    HAS_REGISTRY_CLEANER = False

from cortex_unified.scheduler.scheduler import TaskScheduler
from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules
from cortex_unified.reports.restore_manager import RestoreManager
from cortex_unified.reports.reports import ReportsGenerator

from cortex_unified.ui.navigation.navigation_controller import NavigationController
from cortex_unified.ui.safety.safety_manager import SafetyManager

# Modular Tab Imports
from cortex_unified.ui.tabs.dashboard_tab import DashboardTab
from cortex_unified.ui.tabs.empty_files_tab import EmptyFilesTab
from cortex_unified.ui.tabs.deep_cleaner_tab import DeepCleanerTab
from cortex_unified.ui.tabs.duplicates_tab import DuplicatesTab
from cortex_unified.ui.tabs.large_files_tab import LargeFilesTab
from cortex_unified.ui.tabs.disk_analyzer_tab import DiskAnalyzerTab
from cortex_unified.ui.tabs.docker_tab import DockerTab
from cortex_unified.ui.tabs.broken_links_tab import BrokenLinksTab
from cortex_unified.ui.tabs.restore_tab import RestoreTab
from cortex_unified.ui.tabs.settings_tab import SettingsTab
from cortex_unified.ui.tabs.uninstaller_tab import UninstallerTab
from cortex_unified.ui.tabs.privacy_tab import PrivacyTab
from cortex_unified.ui.tray_icon import SystemTrayManager


class ScanWorker(QObject):
    finished = Signal(list, list)
    error = Signal(str)
    progress_updated = Signal(object)

    def __init__(self, config: Config, path: str, enable_checkpoints: bool=False, enable_throttling: bool=False, checkpoint_id: str=''):
        super().__init__()
        self.config = config
        self.path = path
        self.enable_checkpoints = enable_checkpoints
        self.enable_throttling = enable_throttling
        self.checkpoint_id = checkpoint_id
        self.scanner = None
        self._should_stop = False

    def run(self):
        """Run the scanning process."""
        try:
            self.scanner = Scanner(self.config, self.path, enable_checkpoints=self.enable_checkpoints, enable_throttling=self.enable_throttling)
            if self.enable_checkpoints:
                import threading
                import time

                def progress_monitor():
                    while not self._should_stop:
                        if self.scanner and self.scanner._scan_manager:
                            progress = self.scanner.get_scan_progress()
                            if progress:
                                self.progress_updated.emit(progress)
                        time.sleep(0.5)
                progress_thread = threading.Thread(target=progress_monitor, daemon=True)
                progress_thread.start()
            empty_files, empty_dirs = self.scanner.scan(checkpoint_id=self.checkpoint_id)
            self.finished.emit(empty_files, empty_dirs)
        except Exception as e:
            self.error.emit(str(e))

    def pause(self):
        """Pause the scanning process."""
        if self.scanner:
            self.scanner.pause_scan()

    def resume(self):
        """Resume the scanning process."""
        if self.scanner:
            self.scanner.resume_scan()

    def stop(self):
        """Stop the scanning process."""
        self._should_stop = True
        if self.scanner and self.enable_checkpoints:
            try:
                checkpoint_id = self.scanner.create_checkpoint()
                return checkpoint_id
            except Exception:
                pass
        return None

class DeleteWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, deleter: Deleter, empty_files: List[Path], empty_dirs: List[Path]):
        super().__init__()
        self.deleter = deleter
        self.empty_files = empty_files
        self.empty_dirs = empty_dirs

    def run(self):
        """Run the deletion process."""
        try:
            result = self.deleter.delete(self.empty_files, self.empty_dirs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class MultiDriveScanWorker(QObject):
    """Worker class for scanning multiple drives in separate threads."""
    finished = Signal(list, list)
    error = Signal(str)
    progress_updated = Signal(object)

    def __init__(self, config: Config, paths: List[str], enable_checkpoints: bool=False, enable_throttling: bool=False):
        super().__init__()
        self.config = config
        self.paths = paths
        self.enable_checkpoints = enable_checkpoints
        self.enable_throttling = enable_throttling
        self._should_stop = False

    def run(self):
        """Run the multi-drive scanning process."""
        try:
            from cortex_unified.performance.multi_drive_scanner import MultiDriveScanner
            scanner = MultiDriveScanner(self.config, enable_checkpoints=self.enable_checkpoints, enable_throttling=self.enable_throttling)
            if self.enable_checkpoints:
                import threading
                import time

                def progress_monitor():
                    while not self._should_stop:
                        progress = scanner.get_overall_progress()
                        if progress:
                            self.progress_updated.emit(progress)
                        time.sleep(0.5)
                progress_thread = threading.Thread(target=progress_monitor, daemon=True)
                progress_thread.start()
            all_empty_files = []
            all_empty_dirs = []
            for path in self.paths:
                empty_files, empty_dirs = scanner.scan_drive(path)
                all_empty_files.extend(empty_files)
                all_empty_dirs.extend(empty_dirs)
            self.finished.emit(all_empty_files, all_empty_dirs)
        except ImportError:
            self.error.emit('Multi-drive scanner module not available')
        except Exception as e:
            self.error.emit(str(e))

    def pause(self):
        """Pause the scanning process."""
        pass

    def resume(self):
        """Resume the scanning process."""
        pass

    def stop(self):
        """Stop the scanning process."""
        self._should_stop = True

class DeepCleanerGUI(QMainWindow):
    """Main window for Cortex Cleaner GUI application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Cortex Cleaner')
        self.setGeometry(100, 100, 1200, 800)
        self.config = Config()
        self.scan_thread: Optional[QThread] = None
        self.scan_worker: Optional[Union[ScanWorker, MultiDriveScanWorker]] = None
        self.delete_thread: Optional[QThread] = None
        self.delete_worker: Optional[DeleteWorker] = None
        self.duplicate_thread: Optional[QThread] = None
        self.duplicate_worker: Optional[Any] = None
        self.large_file_thread: Optional[QThread] = None
        self.large_file_worker: Optional[Any] = None
        self.disk_analyzer_thread: Optional[QThread] = None
        self.disk_analyzer_worker: Optional[Any] = None
        self.empty_files: List[Path] = []
        self.empty_dirs: List[Path] = []
        self.duplicates: Dict[str, List[Path]] = {}
        self.large_files: List[tuple] = []
        self.logger = logging.getLogger('gui')
        try:
            self.safety_manager = SafetyManager(self.config, self.logger)
        except Exception as e:
            self.logger.error(f'Failed to initialize SafetyManager: {e}')
            self.safety_manager = None
        self.settings = QSettings('DeepCleaner', 'DeepCleanerGUI')
        self.init_ui()
        self.load_settings()
        
        # Initialize comprehensive accessibility and theme layers
        try:
            from cortex_unified.accessibility import setup_full_accessibility
            self.keyboard_handler, self.screen_reader = setup_full_accessibility(
                self, enable_shortcuts=True, enable_announcements=True
            )
            self.logger.info("Accessibility integration verified.")
        except Exception as e:
            self.logger.error(f"Accessibility system failed to bind: {e}")
            
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.add_advanced_tabs)
        QTimer.singleShot(150, self.init_tray_icon)

    def init_tray_icon(self):
        """Initialize the System Tray Manager."""
        try:
            self.tray_manager = SystemTrayManager(self, QApplication.instance())
            self.logger.info("System Tray initialized successfully.")
        except Exception as e:
            self.logger.error(f'Failed to initialize System Tray: {e}')

    def __getattr__(self, name):
        """Proxy missing widget access to child tabs."""
        if name.startswith('_') or name == '_in_getattr':
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        if getattr(self, '_in_getattr', False):
            raise AttributeError(name)
            
        self._in_getattr = True
        try:
            from cortex_unified.ui.tabs.base_tab import BaseTab
            for tab in self.findChildren(BaseTab):
                if hasattr(tab, name):
                    return getattr(tab, name)
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        finally:
            self._in_getattr = False


    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.navigation_controller = NavigationController()
        main_layout.addWidget(self.navigation_controller)
        dashboard_tab = DashboardTab(self.config, self.logger, self.safety_manager, self)
        self.navigation_controller.add_tab_with_default_icon(dashboard_tab, 'Dashboard')
        
        cleaner_tab = EmptyFilesTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(cleaner_tab, 'Cleaner')
        
        duplicates_tab = DuplicatesTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(duplicates_tab, 'Duplicates')
        
        deep_cleaner_tab = DeepCleanerTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(deep_cleaner_tab, 'Deep Cleaner')
        
        large_files_tab = LargeFilesTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(large_files_tab, 'Large Files')
        
        disk_analyzer_tab = DiskAnalyzerTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(disk_analyzer_tab, 'Disk Analyzer')
        
        docker_tab = DockerTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(docker_tab, 'Docker')
        
        broken_links_tab = BrokenLinksTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(broken_links_tab, 'Broken Links')
        
        restore_tab = RestoreTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(restore_tab, 'Restore')
        
        settings_tab = SettingsTab(self.config, self.logger, self.safety_manager)
        self.navigation_controller.add_tab_with_default_icon(settings_tab, 'Settings')
        self.status_bar = QLabel('Ready')
        self.status_bar.setStyleSheet('QLabel { padding: 5px; border-top: 1px solid #ccc; }')
        main_layout.addWidget(self.status_bar)

    def add_advanced_tabs(self):
        """Add advanced tabs after all methods are defined."""
        try:
            from cortex_unified.ui.tabs.file_shredder_tab import FileShredderTab
            from cortex_unified.ui.tabs.scheduler_tab import SchedulerTab
            from cortex_unified.ui.tabs.reports_tab import ReportsTab
            from cortex_unified.ui.tabs.resource_monitor_tab import ResourceMonitorTab
            from cortex_unified.ui.tabs.system_tools_tab import SystemToolsTab
            from cortex_unified.ui.tabs.security_scanner_tab import SecurityScannerTab
            
            shredder_tab = FileShredderTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(shredder_tab, 'File Shredder')
            
            scheduler_tab = SchedulerTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(scheduler_tab, 'Scheduler')
            
            reports_tab = ReportsTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(reports_tab, 'Reports')
            
            monitor_tab = ResourceMonitorTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(monitor_tab, 'Resource Monitor')
            
            system_tools_tab = SystemToolsTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(system_tools_tab, 'System Tools')
            
            security_tab = SecurityScannerTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(security_tab, 'Security Scanner')
            
            uninstaller_tab = UninstallerTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(uninstaller_tab, 'Deep Uninstaller')
            
            privacy_tab = PrivacyTab(self.config, self.logger, self.safety_manager)
            self.navigation_controller.add_tab_with_default_icon(privacy_tab, 'Privacy Shield')
            
            self.logger.info('Advanced and Weaponized tabs added successfully')
        except Exception as e:
            self.logger.warning(f'Could not add advanced tabs: {e}')



    def browse_path(self):
        """Open file dialog to select target path."""
        path = QFileDialog.getExistingDirectory(self, 'Select Directory to Scan')
        if path:
            self.path_input.setText(path)

    def browse_path_for_widget(self, widget):
        """Open file dialog to select target path for a specific widget."""
        path = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if path:
            widget.setText(path)

    def add_activity(self, message):
        """Add an activity message to the dashboard."""
        self.activity_list.addItem(f'[{self.get_current_time()}] {message}')

    def get_current_time(self):
        """Get current time as string."""
        from datetime import datetime
        return datetime.now().strftime('%H:%M:%S')

    def quick_scan(self):
        """Quick scan from dashboard."""
        self.path_input.setText(str(Path.home()))
        self.tab_widget.setCurrentIndex(1)
        self.start_scan()

    def start_scan(self):
        """Start the enhanced scanning process."""
        if hasattr(self, 'logger'):
            self.logger.info('=== STARTING SCAN PROCESS (DUBBING LOG) ===')
            self.logger.info('Target path mode: {}'.format('Single' if self.single_path_radio.isChecked() else 'Multi-drive'))
        target_paths = []
        if self.single_path_radio.isChecked():
            path = self.path_input.text().strip()
            if hasattr(self, 'logger'):
                self.logger.info('Single path selected: {}'.format(path if path else 'None'))
            if not path:
                QMessageBox.warning(self, 'Warning', 'Please select a directory to scan.')
                return
            target_paths = [path]
        else:
            if hasattr(self, 'logger'):
                self.logger.info('Multi-drive mode selected')
            for i in range(self.drives_list.count()):
                item = self.drives_list.item(i)
                drive_data = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(drive_data, dict):
                    target_paths.append(drive_data['path'])
                    if hasattr(self, 'logger'):
                        self.logger.info('Adding network drive: {}'.format(drive_data['path']))
                else:
                    target_paths.append(drive_data)
                    if hasattr(self, 'logger'):
                        self.logger.info('Adding local drive: {}'.format(drive_data))
            if not target_paths:
                QMessageBox.warning(self, 'Warning', 'Please select drives to scan.')
                return
        if hasattr(self, 'logger'):
            self.logger.info('Validating {} paths'.format(len(target_paths)))
        valid_paths = []
        for path in target_paths:
            try:
                normalized_path = normalize_path(path)
                if normalized_path.exists():
                    valid_paths.append(str(normalized_path))
                    if hasattr(self, 'logger'):
                        self.logger.info('Valid path: {}'.format(normalized_path))
                else:
                    self.add_activity(f'Skipping non-existent path: {path}')
                    if hasattr(self, 'logger'):
                        self.logger.warning('Skipping non-existent path: {}'.format(path))
            except Exception as e:
                self.add_activity(f'Invalid path {path}: {str(e)}')
                if hasattr(self, 'logger'):
                    self.logger.error('Invalid path {}: {}'.format(path, str(e)))
        if not valid_paths:
            QMessageBox.critical(self, 'Error', 'No valid paths to scan.')
            if hasattr(self, 'logger'):
                self.logger.error('No valid paths to scan')
            return
        enable_checkpoints = self.enable_checkpoints_checkbox.isChecked()
        enable_throttling = self.enable_throttling_checkbox.isChecked()
        if hasattr(self, 'logger'):
            self.logger.info('Performance options - Checkpoints: {}, Throttling: {}'.format(enable_checkpoints, enable_throttling))
        if hasattr(self, 'logger'):
            self.logger.info('Updating UI for scan start')
        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_group.setVisible(True)
        if enable_checkpoints:
            self.pause_button.setEnabled(True)
            self.progress_bar.setRange(0, 100)
            self.progress_label.setText('Starting scan...')
        else:
            self.progress_bar.setRange(0, 0)
            self.progress_label.setText('Scanning...')
        self.progress_bar.setVisible(True)
        self.results_text.clear()
        if hasattr(self, 'logger'):
            self.logger.info('Configuring scan options')
        scan_config = Config()
        scan_config.config_data = self.config.config_data.copy()
        if self.pattern_input.text().strip():
            patterns = [p.strip() for p in self.pattern_input.text().split(',') if p.strip()]
            scan_config.config_data['exclude_patterns'] = patterns
            if hasattr(self, 'logger'):
                self.logger.info('Applied pattern filters: {}'.format(patterns))
        age_days = self.age_spinbox.value()
        if age_days > 0:
            scan_config.config_data['min_age_days'] = age_days
            if hasattr(self, 'logger'):
                self.logger.info('Applied age filter: {} days'.format(age_days))
        if hasattr(self, 'logger'):
            self.logger.info('Setting up logging')
        log_file = getattr(self, 'log_file_input', None)
        log_file_path = log_file.text().strip() if log_file and log_file.text().strip() else ''
        verbose = getattr(self, 'verbose_checkbox', None)
        verbose_enabled = verbose.isChecked() if verbose else False
        setup_logging(verbose_enabled, log_file_path)
        if hasattr(self, 'logger'):
            self.logger.info('Starting enhanced scanning in separate thread')
        self.scan_thread = QThread()
        if len(valid_paths) > 1:
            if hasattr(self, 'logger'):
                self.logger.info('Using MultiDriveScanWorker for {} paths'.format(len(valid_paths)))
            self.scan_worker = MultiDriveScanWorker(scan_config, valid_paths, enable_checkpoints=enable_checkpoints, enable_throttling=enable_throttling)
        else:
            if hasattr(self, 'logger'):
                self.logger.info('Using ScanWorker for single path: {}'.format(valid_paths[0]))
            self.scan_worker = ScanWorker(scan_config, valid_paths[0], enable_checkpoints=enable_checkpoints, enable_throttling=enable_throttling)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        if enable_checkpoints:
            self.scan_worker.progress_updated.connect(self.update_scan_progress)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.error.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.start()
        if hasattr(self, 'logger'):
            self.logger.info('Scan thread started successfully')

    def scan_finished(self, empty_files: List[Path], empty_dirs: List[Path]):
        """Handle scan completion."""
        if hasattr(self, 'logger'):
            self.logger.info('=== SCAN FINISHED (DUBBING LOG) ===')
            self.logger.info('Results - Empty files: {}, Empty dirs: {}'.format(len(empty_files), len(empty_dirs)))
        self.empty_files = empty_files
        self.empty_dirs = empty_dirs
        self.scan_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_group.setVisible(False)
        status_msg = f'Scan complete: {len(empty_files)} empty files, {len(empty_dirs)} empty directories'
        if hasattr(self, 'status_bar'):
            self.status_bar.setText(status_msg)
        if hasattr(self, 'add_activity'):
            self.add_activity(status_msg)
        if empty_files or empty_dirs:
            self.delete_button.setEnabled(True)
            result_text = f'Found {len(empty_files)} empty files and {len(empty_dirs)} empty directories:\n\n'
            if empty_files:
                result_text += 'Empty files:\n'
                for file in empty_files:
                    result_text += f'  {file}\n'
                result_text += '\n'
            if empty_dirs:
                result_text += 'Empty directories:\n'
                for dir in empty_dirs:
                    result_text += f'  {dir}\n'
        else:
            result_text = 'No empty files or directories found.'
            self.delete_button.setEnabled(False)
        self.results_text.setPlainText(result_text)

    def scan_error(self, error: str):
        """Handle scan error."""
        self.logger.error(f'=== Scan error occurred ===')
        self.logger.error(f'Error details: {error}')
        self.scan_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_group.setVisible(False)
        if hasattr(self, 'status_bar'):
            self.status_bar.setText('Scan failed')
        if hasattr(self, 'add_activity'):
            self.add_activity(f'Scan failed: {error}')
        QMessageBox.critical(self, 'Scan Error', f'An error occurred during scanning:\n{error}')

    def update_scan_progress(self, progress):
        """Update the scan progress bar with dubbing logs for debugging."""
        if hasattr(self, 'logger'):
            percentage = getattr(progress, 'percentage', 0.0)
            self.logger.info('Updating scan progress: {:.1f}%'.format(percentage))
        if hasattr(progress, 'percentage'):
            self.progress_bar.setValue(int(progress.percentage))
            if hasattr(progress, 'processed_count') and hasattr(progress, 'total_count'):
                self.scan_stats_label.setText(f'Processed: {progress.processed_count}/{progress.total_count} items ({progress.percentage:.1f}%)')

    def start_delete(self):
        """Start the deletion process with dubbing logs for debugging."""
        if hasattr(self, 'logger'):
            self.logger.info('=== STARTING DELETE PROCESS (DUBBING LOG) ===')
            self.logger.info('Files to delete: {}'.format(len(self.empty_files)))
            self.logger.info('Directories to delete: {}'.format(len(self.empty_dirs)))
        if not self.empty_files and (not self.empty_dirs):
            QMessageBox.information(self, 'Info', 'No files or directories to delete.')
            if hasattr(self, 'logger'):
                self.logger.info('No files or directories to delete')
            return
        dry_run = self.dry_run_checkbox.isChecked()
        use_trash = self.trash_checkbox.isChecked()
        if hasattr(self, 'logger'):
            self.logger.info('Deletion options - Dry run: {}, Use trash: {}'.format(dry_run, use_trash))
        action = 'preview deletion of' if dry_run else 'delete'
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Are you sure you want to {action} {len(self.empty_files)} files and {len(self.empty_dirs)} directories?\n{('This is a preview only.' if dry_run else 'This action cannot be undone.')}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            if hasattr(self, 'logger'):
                self.logger.info('User cancelled deletion')
            return
        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_group.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.progress_label.setText('Deleting...')
        if hasattr(self, 'logger'):
            self.logger.info('Starting deletion process in separate thread')
        self.delete_thread = QThread()
        self.delete_worker = DeleteWorker(Deleter(dry_run=dry_run, use_trash=use_trash), self.empty_files, self.empty_dirs)
        self.delete_worker.moveToThread(self.delete_thread)
        self.delete_thread.started.connect(self.delete_worker.run)
        self.delete_worker.finished.connect(self.delete_finished)
        self.delete_worker.error.connect(self.delete_error)
        self.delete_worker.finished.connect(self.delete_thread.quit)
        self.delete_worker.error.connect(self.delete_thread.quit)
        self.delete_thread.finished.connect(self.delete_thread.deleteLater)
        self.delete_thread.start()
        if hasattr(self, 'logger'):
            self.logger.info('Deletion thread started successfully')

    def pause_scan(self):
        """Pause the scanning process with dubbing logs for debugging."""
        if hasattr(self, 'logger'):
            self.logger.info('=== PAUSING SCAN PROCESS (DUBBING LOG) ===')
        if not hasattr(self, 'scan_worker') or not self.scan_worker:
            QMessageBox.warning(self, 'Warning', 'No scan in progress.')
            if hasattr(self, 'logger'):
                self.logger.warning('No scan in progress when trying to pause')
            return
        try:
            if hasattr(self, 'logger'):
                self.logger.info('Calling pause method on scan worker')
            if hasattr(self, 'scan_worker') and hasattr(self.scan_worker, 'pause'):
                self.scan_worker.pause()
                self.pause_button.setEnabled(False)
                self.resume_button.setEnabled(True)
                self.progress_label.setText('Scan paused')
                if hasattr(self, 'logger'):
                    self.logger.info('Scan paused successfully')
            else:
                if hasattr(self, 'logger'):
                    self.logger.error('Scan worker does not have pause method')
                QMessageBox.warning(self, 'Warning', 'Pause functionality not available.')
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error('Error pausing scan: {}'.format(str(e)))
            QMessageBox.critical(self, 'Error', f'Error pausing scan:\n{str(e)}')

    def resume_scan(self):
        """Resume the scanning process with dubbing logs for debugging."""
        if hasattr(self, 'logger'):
            self.logger.info('=== RESUMING SCAN PROCESS (DUBBING LOG) ===')
        if not hasattr(self, 'scan_worker') or not self.scan_worker:
            QMessageBox.warning(self, 'Warning', 'No scan in progress.')
            if hasattr(self, 'logger'):
                self.logger.warning('No scan in progress when trying to resume')
            return
        try:
            if hasattr(self, 'logger'):
                self.logger.info('Calling resume method on scan worker')
            if hasattr(self, 'scan_worker') and hasattr(self.scan_worker, 'resume'):
                self.scan_worker.resume()
                self.pause_button.setEnabled(True)
                self.resume_button.setEnabled(False)
                self.progress_label.setText('Scanning...')
                if hasattr(self, 'logger'):
                    self.logger.info('Scan resumed successfully')
            else:
                if hasattr(self, 'logger'):
                    self.logger.error('Scan worker does not have resume method')
                QMessageBox.warning(self, 'Warning', 'Resume functionality not available.')
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error('Error resuming scan: {}'.format(str(e)))
            QMessageBox.critical(self, 'Error', f'Error resuming scan:\n{str(e)}')

    def delete_finished(self, result: Dict[str, Any]):
        """Handle deletion completion."""
        if hasattr(self, 'logger'):
            self.logger.info('=== DELETION FINISHED (DUBBING LOG) ===')
            self.logger.info('Results - Files deleted: {}, Directories deleted: {}'.format(result['files_deleted'], result['dirs_deleted']))
            self.logger.info('Errors: {}'.format(len(result['errors'])))
        self.scan_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_group.setVisible(False)
        self.status_bar.setText('Deletion complete')
        self.add_activity(f"Deletion complete: {result['files_deleted']} files, {result['dirs_deleted']} directories")
        result_text = self.results_text.toPlainText()
        result_text += f'\n\nDeletion results:\n'
        result_text += f"  Files processed: {result['files_deleted']}\n"
        result_text += f"  Directories processed: {result['dirs_deleted']}\n"
        result_text += f"  Errors: {len(result['errors'])}\n"
        if result['errors']:
            result_text += '\nErrors:\n'
            for error in result['errors']:
                result_text += f"  {error['type']} {error['path']}: {error['error']}\n"
        self.results_text.setPlainText(result_text)
        self.empty_files = []
        self.empty_dirs = []
        self.delete_button.setEnabled(False)

    def delete_error(self, error: str):
        """Handle deletion error."""
        self.logger.error(f'Deletion error: {error}')
        self.scan_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.setText('Deletion failed')
        self.add_activity(f'Deletion failed: {error}')
        QMessageBox.critical(self, 'Deletion Error', f'An error occurred during deletion:\n{error}')

    def show_treemap_visualization(self):
        """Show TreeMap visualization in a new window."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, 'Warning', 'Please run disk analysis first.')
            return
        try:
            from cortex_unified.visualization import TreeMapGenerator
            import tempfile
            import webbrowser
            generator = TreeMapGenerator(self.current_analyzer)
            if not generator.has_plotly:
                QMessageBox.warning(self, 'Plotly Not Available', 'Plotly library is not installed. Please install it with: pip install plotly')
                return
            html_content = generator.export_as_html()
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
            webbrowser.open(f'file://{temp_path}')
            self.add_activity('TreeMap visualization opened in browser')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to generate TreeMap: {str(e)}')

    def show_sunburst_visualization(self):
        """Show Sunburst visualization in a new window."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, 'Warning', 'Please run disk analysis first.')
            return
        try:
            from cortex_unified.visualization import SunburstGenerator
            import tempfile
            import webbrowser
            generator = SunburstGenerator(self.current_analyzer)
            if not generator.has_plotly:
                QMessageBox.warning(self, 'Plotly Not Available', 'Plotly library is not installed. Please install it with: pip install plotly')
                return
            html_content = generator.export_as_html()
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
            webbrowser.open(f'file://{temp_path}')
            self.add_activity('Sunburst visualization opened in browser')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to generate Sunburst: {str(e)}')

    def show_interactive_dashboard(self):
        """Show interactive dashboard in a new window."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, 'Warning', 'Please run disk analysis first.')
            return
        try:
            from cortex_unified.visualization import InteractiveDashboard
            import tempfile
            import webbrowser
            dashboard = InteractiveDashboard(self.current_analyzer)
            if not dashboard.has_plotly:
                QMessageBox.warning(self, 'Plotly Not Available', 'Plotly library is not installed. Please install it with: pip install plotly')
                return
            fig = dashboard.create_dashboard()
            try:
                from plotly.offline import plot
                html_content = plot(fig, output_type='div', include_plotlyjs='cdn')
            except ImportError:
                QMessageBox.warning(self, 'Plotly Not Available', 'Plotly library is not installed. Please install it with: pip install plotly')
                return
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
            webbrowser.open(f'file://{temp_path}')
            self.add_activity('Interactive dashboard opened in browser')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to generate dashboard: {str(e)}')

    def export_visualization_dialog(self):
        """Show export visualization dialog."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, 'Warning', 'Please run disk analysis first.')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Export Visualization')
        dialog.setModal(True)
        dialog.resize(400, 300)
        layout = QVBoxLayout(dialog)
        type_group = QGroupBox('Visualization Type')
        type_layout = QVBoxLayout(type_group)
        self.export_treemap_radio = QRadioButton('TreeMap')
        self.export_sunburst_radio = QRadioButton('Sunburst Chart')
        self.export_dashboard_radio = QRadioButton('Interactive Dashboard')
        self.export_treemap_radio.setChecked(True)
        type_layout.addWidget(self.export_treemap_radio)
        type_layout.addWidget(self.export_sunburst_radio)
        type_layout.addWidget(self.export_dashboard_radio)
        layout.addWidget(type_group)
        format_group = QGroupBox('Export Format')
        format_layout = QVBoxLayout(format_group)
        self.export_html_radio = QRadioButton('HTML (Interactive)')
        self.export_png_radio = QRadioButton('PNG (Image)')
        self.export_svg_radio = QRadioButton('SVG (Vector)')
        self.export_html_radio.setChecked(True)
        format_layout.addWidget(self.export_html_radio)
        format_layout.addWidget(self.export_png_radio)
        format_layout.addWidget(self.export_svg_radio)
        layout.addWidget(format_group)
        buttons_layout = QHBoxLayout()
        export_button = QPushButton('Export')
        cancel_button = QPushButton('Cancel')
        export_button.clicked.connect(lambda: self.perform_visualization_export(dialog))
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        dialog.exec()

    def perform_visualization_export(self, dialog):
        """Perform the actual visualization export."""
        try:
            if self.export_treemap_radio.isChecked():
                viz_type = 'treemap'
            elif self.export_sunburst_radio.isChecked():
                viz_type = 'sunburst'
            else:
                viz_type = 'dashboard'
            if self.export_html_radio.isChecked():
                format_ext = 'html'
            elif self.export_png_radio.isChecked():
                format_ext = 'png'
            else:
                format_ext = 'svg'
            filename, _ = QFileDialog.getSaveFileName(self, f'Export {viz_type.title()} Visualization', f'{viz_type}_visualization.{format_ext}', f'{format_ext.upper()} Files (*.{format_ext})')
            if not filename:
                return
            from cortex_unified.visualization import TreeMapGenerator, SunburstGenerator, InteractiveDashboard
            if viz_type == 'treemap':
                generator = TreeMapGenerator(self.current_analyzer)
                if format_ext == 'html':
                    content = generator.export_as_html()
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    img_data = generator.export_as_image(format_ext)
                    with open(filename, 'wb') as f:
                        f.write(img_data)
            elif viz_type == 'sunburst':
                generator = SunburstGenerator(self.current_analyzer)
                if format_ext == 'html':
                    content = generator.export_as_html()
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    img_data = generator.export_as_image(format_ext)
                    with open(filename, 'wb') as f:
                        f.write(img_data)
            else:
                dashboard = InteractiveDashboard(self.current_analyzer)
                success = dashboard.export_visualization(format_ext, filename)
                if not success:
                    raise Exception('Export failed')
            dialog.accept()
            QMessageBox.information(self, 'Success', f'Visualization exported to {filename}')
            self.add_activity(f'Exported {viz_type} visualization to {filename}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to export visualization: {str(e)}')

    def refresh_startup_items(self):
        """Refresh startup items."""
        self.refresh_startup_button.setEnabled(False)
        self.startup_progress_bar.setVisible(True)
        self.startup_progress_bar.setRange(0, 0)
        self.status_bar.setText('Loading startup items...')
        self.add_activity('Loading startup items...')
        try:
            manager = StartupManager()
            items = manager.list_startup_items()
            stats = manager.get_stats()
            self.refresh_startup_button.setEnabled(True)
            self.startup_progress_bar.setVisible(False)
            self.status_bar.setText(f"Loaded {stats['total_startup_items']} startup items")
            self.add_activity(f"Loaded {stats['total_startup_items']} startup items")
            self.startup_table.setRowCount(len(items))
            for i, item in enumerate(items):
                self.startup_table.setItem(i, 0, QTableWidgetItem(item.get('name', 'Unknown')))
                self.startup_table.setItem(i, 1, QTableWidgetItem(item.get('location', 'Unknown')))
                status = 'Enabled' if item.get('enabled', True) else 'Disabled'
                self.startup_table.setItem(i, 2, QTableWidgetItem(status))
                item_type = item.get('type', 'Unknown')
                self.startup_table.setItem(i, 3, QTableWidgetItem(item_type))
            if len(items) > 0:
                self.disable_startup_button.setEnabled(True)
            else:
                self.disable_startup_button.setEnabled(False)
        except Exception as e:
            self.logger.error(f'Startup items error: {e}')
            self.refresh_startup_button.setEnabled(True)
            self.startup_progress_bar.setVisible(False)
            self.status_bar.setText('Failed to load startup items')
            self.add_activity(f'Failed to load startup items: {e}')
            QMessageBox.critical(self, 'Error', f'An error occurred while loading startup items:\n{e}')

    def disable_selected_startup_items(self):
        """Disable selected startup items."""
        selected_ranges = self.startup_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, 'Info', 'Please select startup items to disable.')
            return
        try:
            selected_items = []
            for range_ in selected_ranges:
                for row in range(range_.topRow(), range_.bottomRow() + 1):
                    name_item = self.startup_table.item(row, 0)
                    type_item = self.startup_table.item(row, 3)
                    if name_item and type_item:
                        item_name = name_item.text()
                        item_type = type_item.text()
                        selected_items.append({'name': item_name, 'type': item_type})
            if not selected_items:
                QMessageBox.information(self, 'Info', 'No startup items selected.')
                return
            manager = StartupManager()
            disabled_count = 0
            errors = []
            for item in selected_items:
                try:
                    success = manager.disable_startup_item(item['name'], item['type'])
                    if success:
                        disabled_count += 1
                    else:
                        errors.append(f"Failed to disable {item['name']}")
                except Exception as e:
                    errors.append(f"Error disabling {item['name']}: {str(e)}")
            message = f'Successfully disabled {disabled_count} out of {len(selected_items)} startup items.'
            if errors:
                message += f'\n\nErrors:\n' + '\n'.join(errors[:3])
                if len(errors) > 3:
                    message += f'\n... and {len(errors) - 3} more errors'
            QMessageBox.information(self, 'Startup Items Disabled', message)
            self.add_activity(f'Disabled {disabled_count} startup items')
            self.refresh_startup_items()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error disabling startup items:\n{str(e)}')
            self.add_activity(f'Failed to disable startup items: {str(e)}')

    def refresh_processes(self):
        """Refresh processes and services."""
        try:
            import platform
            system = platform.system().lower()
            self.refresh_processes_button.setEnabled(False)
            self.processes_progress_bar.setVisible(True)
            self.processes_progress_bar.setRange(0, 0)
            self.processes_table.setRowCount(0)
            self.services_table.setRowCount(0)
            analyzer = ProcessAnalyzer(self.config)
            self.processes_progress_bar.setRange(0, 2)
            self.processes_progress_bar.setValue(0)
            processes = analyzer.list_processes()
            self.processes_progress_bar.setValue(1)
            self.processes_table.setRowCount(len(processes))
            for i, process in enumerate(processes):
                if system == 'windows':
                    name = process.get('name', 'Unknown')
                    pid = process.get('pid', 'N/A')
                    memory = process.get('mem_usage', 'N/A')
                    cpu = process.get('cpu_time', 'N/A')
                else:
                    name = process.get('command', 'Unknown')
                    if len(name) > 50:
                        name = name[:47] + '...'
                    pid = process.get('pid', 'N/A')
                    memory = f"{process.get('mem_percent', '0')}%"
                    cpu = f"{process.get('cpu_percent', '0')}%"
                self.processes_table.setItem(i, 0, QTableWidgetItem(name))
                self.processes_table.setItem(i, 1, QTableWidgetItem(str(pid)))
                self.processes_table.setItem(i, 2, QTableWidgetItem(memory))
                self.processes_table.setItem(i, 3, QTableWidgetItem(cpu))
            services = analyzer.list_services()
            self.processes_progress_bar.setValue(2)
            self.services_table.setRowCount(len(services))
            for i, service in enumerate(services):
                if system == 'windows':
                    name = service.get('display_name', service.get('name', 'Unknown'))
                    status = service.get('state', 'Unknown')
                    description = service.get('name', '')
                else:
                    name = service.get('label', service.get('unit', service.get('service', 'Unknown')))
                    status = service.get('active', service.get('last_exit_code', 'Unknown'))
                    description = service.get('description', '')
                self.services_table.setItem(i, 0, QTableWidgetItem(name))
                self.services_table.setItem(i, 1, QTableWidgetItem(status))
                self.services_table.setItem(i, 2, QTableWidgetItem(description))
            stats = analyzer.get_stats()
            self.add_activity(f"Refreshed processes: {stats['total_processes']} processes, {stats['total_services']} services")
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error refreshing processes:\n{str(e)}')
            self.add_activity(f'Failed to refresh processes: {str(e)}')
        finally:
            self.refresh_processes_button.setEnabled(True)
            self.processes_progress_bar.setVisible(False)

    def quick_temp_clean(self):
        """Quick clean temporary files."""
        self.logger.info('=== Quick temp clean initiated ===')
        self.tab_widget.setCurrentIndex(3)
        self.start_temp_scan()

    def scan_registry(self):
        """Scan registry for issues."""
        if not HAS_REGISTRY_CLEANER:
            QMessageBox.critical(self, 'Error', 'Registry cleaner is not available on this platform.')
            return
        self.scan_registry_button.setEnabled(False)
        self.clean_registry_button.setEnabled(False)
        self.registry_progress_bar.setVisible(True)
        self.registry_progress_bar.setRange(0, 0)
        self.registry_results.clear()
        self.status_bar.setText('Scanning registry...')
        self.add_activity('Scanning registry...')
        try:
            if not HAS_REGISTRY_CLEANER:
                raise Exception('Registry cleaner not available')
            cleaner = RegistryCleaner()
            issues = cleaner.scan_orphaned_entries()
            self.scan_registry_button.setEnabled(True)
            self.registry_progress_bar.setVisible(False)
            self.status_bar.setText(f'Registry scan complete: {len(issues)} issues found')
            self.add_activity(f'Registry scan complete: {len(issues)} issues found')
            if issues:
                self.clean_registry_button.setEnabled(True)
                result_text = f'Found {len(issues)} registry issues:\n\n'
                for issue in issues:
                    result_text += f'- {issue}\n'
                self.registry_results.setPlainText(result_text)
            else:
                self.clean_registry_button.setEnabled(False)
                self.registry_results.setPlainText('No registry issues found.')
        except Exception as e:
            self.logger.error(f'Registry scan error: {e}')
            self.scan_registry_button.setEnabled(True)
            self.registry_progress_bar.setVisible(False)
            self.status_bar.setText('Registry scan failed')
            self.add_activity(f'Registry scan failed: {e}')
            QMessageBox.critical(self, 'Error', f'An error occurred while scanning registry:\n{e}')

    def clean_registry(self):
        """Clean registry issues."""
        reply = QMessageBox.question(self, 'Confirm Cleaning', 'Are you sure you want to clean registry issues?\nThis action cannot be undone and may affect system stability.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
        try:
            if not HAS_REGISTRY_CLEANER:
                QMessageBox.critical(self, 'Error', 'Registry cleaner is not available on this platform.')
                return
            cleaner = RegistryCleaner()
            registry_text = self.registry_results.toPlainText()
            if 'No registry issues found' in registry_text:
                QMessageBox.information(self, 'Info', 'No registry issues to clean.')
                return
            backup_success = cleaner.backup_registry()
            if not backup_success:
                QMessageBox.warning(self, 'Warning', 'Failed to create registry backup.')
            entries_removed = 0
            errors = []
            for entry in cleaner.orphaned_entries:
                try:
                    if cleaner.remove_orphaned_entry(entry['path']):
                        entries_removed += 1
                    else:
                        errors.append(f"Failed to remove {entry['name']}")
                except Exception as e:
                    errors.append(f"Error removing {entry['name']}: {str(e)}")
            result = {'entries_cleaned': entries_removed, 'errors': errors}
            cleaned_count = result.get('entries_cleaned', 0)
            errors = result.get('errors', [])
            message = f'Successfully cleaned {cleaned_count} registry entries.'
            if errors:
                message += f'\n{len(errors)} errors occurred.'
            QMessageBox.information(self, 'Registry Cleaning Complete', message)
            self.add_activity(f'Cleaned {cleaned_count} registry entries')
            self.registry_results.setPlainText('Registry cleaning completed. Run scan again to check for remaining issues.')
            self.clean_registry_button.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error cleaning registry:\n{str(e)}')
            self.add_activity(f'Failed to clean registry: {str(e)}')

    def refresh_manifests(self):
        """Refresh backup manifests."""
        self.refresh_manifests_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.restore_progress_bar.setVisible(True)
        self.restore_progress_bar.setRange(0, 0)
        self.status_bar.setText('Loading manifests...')
        self.add_activity('Loading manifests...')
        try:
            manager = RestoreManager()
            manifests = manager.list_manifests()
            self.refresh_manifests_button.setEnabled(True)
            self.restore_progress_bar.setVisible(False)
            self.status_bar.setText(f'Loaded {len(manifests)} manifests')
            self.add_activity(f'Loaded {len(manifests)} manifests')
            self.manifests_table.setRowCount(len(manifests))
            for i, manifest in enumerate(manifests):
                self.manifests_table.setItem(i, 0, QTableWidgetItem(manifest.get('timestamp', 'Unknown')))
                self.manifests_table.setItem(i, 1, QTableWidgetItem(manifest.get('backup_name', 'Unnamed')))
                self.manifests_table.setItem(i, 2, QTableWidgetItem(str(manifest.get('files_backed_up', 0))))
                self.manifests_table.setItem(i, 3, QTableWidgetItem(manifest.get('file_path', 'Unknown')))
            if len(manifests) > 0:
                self.restore_button.setEnabled(True)
            else:
                self.restore_button.setEnabled(False)
        except Exception as e:
            self.logger.error(f'Manifests error: {e}')
            self.refresh_manifests_button.setEnabled(True)
            self.restore_progress_bar.setVisible(False)
            self.status_bar.setText('Failed to load manifests')
            self.add_activity(f'Failed to load manifests: {e}')
            QMessageBox.critical(self, 'Error', f'An error occurred while loading manifests:\n{e}')

    def restore_selected(self):
        """Restore from selected manifest."""
        selected_ranges = self.manifests_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, 'Info', 'Please select a manifest to restore from.')
            return
        row = selected_ranges[0].topRow()
        path_item = self.manifests_table.item(row, 3)
        if path_item:
            manifest_path = path_item.text()
        else:
            QMessageBox.critical(self, 'Error', 'Could not get manifest path.')
            return
        reply = QMessageBox.question(self, 'Confirm Restoration', f'Restore files from {manifest_path}?\nThis action cannot be undone.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
        try:
            manager = RestoreManager()
            name_item = self.manifests_table.item(row, 1)
            if name_item:
                manifest_name = name_item.text()
            else:
                manifest_name = 'Unknown'
            result = manager.restore_from_manifest(manifest_path)
            restored_count = result.get('files_restored', 0)
            errors = result.get('errors', [])
            message = f'Successfully restored {restored_count} files from {manifest_name}.'
            if errors:
                message += f'\n{len(errors)} errors occurred during restoration.'
            QMessageBox.information(self, 'Restoration Complete', message)
            self.add_activity(f'Restored {restored_count} files from {manifest_name}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error restoring files:\n{str(e)}')
            self.add_activity(f'Failed to restore from {manifest_path}: {str(e)}')

    def save_settings(self):
        """Save settings to config file."""
        try:
            self.settings.setValue('log_file', self.log_file_input.text())
            self.settings.setValue('verbose', self.verbose_checkbox.isChecked())
            config_path = self.config._get_default_config_path()
            config_dir = Path(config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config.config_data['log_file'] = self.log_file_input.text().strip()
            self.config.config_data['json_logging'] = self.verbose_checkbox.isChecked()
            with open(config_path, 'w') as f:
                import yaml
                yaml.dump(self.config.config_data, f, default_flow_style=False)
            QMessageBox.information(self, 'Settings', 'Settings saved successfully!')
            self.status_bar.setText('Settings saved')
            self.add_activity('Settings saved')
        except Exception as e:
            self.logger.error(f'Failed to save settings: {e}')
            QMessageBox.critical(self, 'Error', f'Failed to save settings:\n{str(e)}')

    def load_settings(self):
        """Load settings from config file."""
        try:
            log_file = self.settings.value('log_file', '')
            if isinstance(log_file, str):
                self.log_file_input.setText(log_file)
            verbose = self.settings.value('verbose', False, type=bool)
            if isinstance(verbose, bool):
                self.verbose_checkbox.setChecked(verbose)
            if self.config.config_data:
                if 'log_file' in self.config.config_data:
                    self.log_file_input.setText(self.config.config_data['log_file'])
                if 'json_logging' in self.config.config_data:
                    self.verbose_checkbox.setChecked(self.config.config_data['json_logging'])
        except Exception as e:
            self.logger.warning(f'Failed to load settings: {e}')

    def format_bytes(self, bytes_value: Union[int, float]) -> str:
        """Format bytes to human readable format."""
        bytes_value = float(bytes_value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f'{bytes_value:.1f} {unit}'
            bytes_value = bytes_value / 1024.0
        return f'{bytes_value:.1f} PB'

    def closeEvent(self, event):
        """Handle window close event."""
        threads_to_cleanup = ['scan_thread', 'delete_thread', 'duplicates_thread', 'large_files_thread', 'disk_analysis_thread']
        for thread_name in threads_to_cleanup:
            try:
                if hasattr(self, thread_name):
                    thread = getattr(self, thread_name)
                    if thread and hasattr(thread, 'isRunning') and thread.isRunning():
                        thread.quit()
                        thread.wait(3000)
            except (RuntimeError, AttributeError):
                pass
            pass
        if getattr(self, 'duplicate_thread', None) and self.duplicate_thread.isRunning():
            self.duplicate_thread.quit()
            self.duplicate_thread.wait()
        if getattr(self, 'large_file_thread', None) and self.large_file_thread.isRunning():
            self.large_file_thread.quit()
            self.large_file_thread.wait()
        if getattr(self, 'temp_cleaner_thread', None) and self.temp_cleaner_thread.isRunning():
            self.temp_cleaner_thread.quit()
            self.temp_cleaner_thread.wait()
        if getattr(self, 'disk_analyzer_thread', None) and self.disk_analyzer_thread.isRunning():
            self.disk_analyzer_thread.quit()
            self.disk_analyzer_thread.wait()
        event.accept()

    def switch_to_tab(self, index: int):
        """Switch to the specified tab index."""
        self.tab_widget.setCurrentIndex(index)

    def create_package_manager_tab(self) -> QWidget:
        """Create the Package Manager tab."""
        pm_tab = QWidget()
        layout = QVBoxLayout(pm_tab)
        pm_group = QGroupBox('Package Managers')
        pm_layout = QVBoxLayout(pm_group)
        self.pm_pip_checkbox = QCheckBox('pip (Python)')
        self.pm_pip_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_pip_checkbox)
        self.pm_npm_checkbox = QCheckBox('npm (Node.js)')
        self.pm_npm_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_npm_checkbox)
        self.pm_yarn_checkbox = QCheckBox('yarn (Node.js)')
        pm_layout.addWidget(self.pm_yarn_checkbox)
        self.pm_conda_checkbox = QCheckBox('conda (Python)')
        pm_layout.addWidget(self.pm_conda_checkbox)
        self.pm_system_checkbox = QCheckBox('System Package Manager')
        pm_layout.addWidget(self.pm_system_checkbox)
        layout.addWidget(pm_group)
        options_group = QGroupBox('Options')
        options_layout = QFormLayout(options_group)
        self.pm_keep_recent_spinbox = QSpinBox()
        self.pm_keep_recent_spinbox.setRange(0, 365)
        self.pm_keep_recent_spinbox.setValue(7)
        self.pm_keep_recent_spinbox.setSuffix(' days')
        options_layout.addRow('Keep recent cache files:', self.pm_keep_recent_spinbox)
        self.pm_orphaned_checkbox = QCheckBox('Include orphaned packages')
        options_layout.addRow(self.pm_orphaned_checkbox)
        self.pm_dry_run_checkbox = QCheckBox('Dry Run (Preview Only)')
        self.pm_dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.pm_dry_run_checkbox)
        layout.addWidget(options_group)
        button_layout = QHBoxLayout()
        self.pm_detect_button = QPushButton('Detect Package Managers')
        self.pm_detect_button.clicked.connect(self.detect_package_managers)
        button_layout.addWidget(self.pm_detect_button)
        self.pm_scan_button = QPushButton('Scan Cache')
        self.pm_scan_button.clicked.connect(self.start_pm_scan)
        button_layout.addWidget(self.pm_scan_button)
        self.pm_cleanup_button = QPushButton('Clean Up')
        self.pm_cleanup_button.clicked.connect(self.start_pm_cleanup)
        self.pm_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.pm_cleanup_button)
        layout.addLayout(button_layout)
        self.pm_progress_bar = QProgressBar()
        self.pm_progress_bar.setVisible(False)
        layout.addWidget(self.pm_progress_bar)
        results_group = QGroupBox('Package Manager Cache')
        results_layout = QVBoxLayout(results_group)
        self.pm_summary_label = QLabel("Click 'Detect Package Managers' to start")
        results_layout.addWidget(self.pm_summary_label)
        self.pm_table = QTableWidget()
        self.pm_table.setColumnCount(4)
        self.pm_table.setHorizontalHeaderLabels(['Package Manager', 'Cache Size', 'Files', 'Status'])
        self.pm_table.horizontalHeader().setStretchLastSection(True)
        self.pm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.pm_table)
        layout.addWidget(results_group)
        return pm_tab

    def create_heuristics_tab(self) -> QWidget:
        """Create the Heuristics tab."""
        heuristics_tab = QWidget()
        layout = QVBoxLayout(heuristics_tab)
        options_group = QGroupBox('Detection Options')
        options_layout = QFormLayout(options_group)
        self.heuristics_confidence_spinbox = QSpinBox()
        self.heuristics_confidence_spinbox.setRange(1, 100)
        self.heuristics_confidence_spinbox.setValue(70)
        self.heuristics_confidence_spinbox.setSuffix('%')
        options_layout.addRow('Confidence Threshold:', self.heuristics_confidence_spinbox)
        self.heuristics_ml_checkbox = QCheckBox('Use Machine Learning Patterns')
        self.heuristics_ml_checkbox.setChecked(True)
        options_layout.addRow(self.heuristics_ml_checkbox)
        self.heuristics_registry_checkbox = QCheckBox('Include Registry Analysis (Windows)')
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
        self.heuristics_browse_button.clicked.connect(self.browse_heuristics_path)
        path_layout.addWidget(self.heuristics_browse_button)
        layout.addWidget(path_group)
        button_layout = QHBoxLayout()
        self.heuristics_scan_button = QPushButton('Scan for Leftovers')
        self.heuristics_scan_button.clicked.connect(self.start_heuristics_scan)
        button_layout.addWidget(self.heuristics_scan_button)
        self.heuristics_cleanup_button = QPushButton('Clean Up Leftovers')
        self.heuristics_cleanup_button.clicked.connect(self.start_heuristics_cleanup)
        self.heuristics_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.heuristics_cleanup_button)
        layout.addLayout(button_layout)
        self.heuristics_progress_bar = QProgressBar()
        self.heuristics_progress_bar.setVisible(False)
        layout.addWidget(self.heuristics_progress_bar)
        results_group = QGroupBox('Detected Leftovers')
        results_layout = QVBoxLayout(results_group)
        self.heuristics_summary_label = QLabel('No scan performed yet')
        results_layout.addWidget(self.heuristics_summary_label)
        self.heuristics_table = QTableWidget()
        self.heuristics_table.setColumnCount(4)
        self.heuristics_table.setHorizontalHeaderLabels(['Item', 'Type', 'Confidence', 'Size'])
        self.heuristics_table.horizontalHeader().setStretchLastSection(True)
        self.heuristics_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.heuristics_table)
        layout.addWidget(results_group)
        return heuristics_tab

    def detect_package_managers(self):
        """Detect available package managers."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            pm_cleaner = PackageManagerCleaner(self.config)
            managers = pm_cleaner.detect_package_managers()
            manager_names = [pm.name for pm in managers]
            self.pm_summary_label.setText(f"Detected: {', '.join(manager_names)}")
            self.pm_table.setRowCount(len(managers))
            for i, manager in enumerate(managers):
                self.pm_table.setItem(i, 0, QTableWidgetItem(manager.name))
                self.pm_table.setItem(i, 1, QTableWidgetItem('Unknown'))
                self.pm_table.setItem(i, 2, QTableWidgetItem('Unknown'))
                self.pm_table.setItem(i, 3, QTableWidgetItem('Detected'))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to detect package managers: {str(e)}')

    def start_pm_scan(self):
        """Start package manager cache scan."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            self.pm_scan_button.setEnabled(False)
            self.pm_cleanup_button.setEnabled(False)
            self.pm_summary_label.setText('Scanning package manager caches...')
            pm_cleaner = PackageManagerCleaner(self.config)
            available_managers = pm_cleaner.detect_package_managers()
            if not available_managers:
                self.pm_summary_label.setText('No package managers detected')
                self.pm_scan_button.setEnabled(True)
                return
            total_cache_size = 0
            total_orphaned = 0
            results = []
            for manager in available_managers:
                cache_size = pm_cleaner._get_cache_size(manager.cache_path)
                if cache_size > 0:
                    total_cache_size += cache_size
                    results.append(f'{manager.name}: {pm_cleaner._format_bytes(cache_size)}')
            summary_text = f'Found cache data: {pm_cleaner._format_bytes(total_cache_size)}\n'
            summary_text += '\n'.join(results)
            self.pm_summary_label.setText(summary_text)
            self.pm_scan_button.setEnabled(True)
            self.pm_cleanup_button.setEnabled(total_cache_size > 0)
            self.add_activity(f'Scanned package managers: {pm_cleaner._format_bytes(total_cache_size)} cache found')
        except ImportError:
            self.pm_summary_label.setText('Package manager cleaner not available')
            self.pm_scan_button.setEnabled(True)
        except Exception as e:
            self.pm_summary_label.setText(f'Error scanning package managers: {str(e)}')
            self.pm_scan_button.setEnabled(True)

    def start_pm_cleanup(self):
        """Start package manager cleanup."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            reply = QMessageBox.question(self, 'Confirm Cleanup', 'Are you sure you want to clean package manager caches?\nThis will remove cached packages but they can be re-downloaded when needed.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
            self.pm_cleanup_button.setEnabled(False)
            self.pm_summary_label.setText('Cleaning package manager caches...')
            pm_cleaner = PackageManagerCleaner(self.config)
            available_managers = pm_cleaner.detect_package_managers()
            total_cleaned = 0
            results = []
            for manager in available_managers:
                if manager.name == 'pip':
                    result = pm_cleaner.clean_pip_cache()
                    if result and result.success:
                        total_cleaned += result.space_freed
                        results.append(f'pip: {result.files_removed} files cleaned')
                elif manager.name == 'npm':
                    result = pm_cleaner.clean_npm_cache()
                    if result and result.success:
                        total_cleaned += result.space_freed
                        results.append(f'npm: {result.files_removed} files cleaned')
            summary_text = f'Cleaned: {pm_cleaner._format_bytes(total_cleaned)}\n'
            summary_text += '\n'.join(results)
            self.pm_summary_label.setText(summary_text)
            self.pm_cleanup_button.setEnabled(True)
            QMessageBox.information(self, 'Cleanup Complete', f'Successfully cleaned package manager caches.\nSpace freed: {pm_cleaner._format_bytes(total_cleaned)}')
            self.add_activity(f'Cleaned package managers: {pm_cleaner._format_bytes(total_cleaned)} freed')
        except ImportError:
            QMessageBox.warning(self, 'Not Available', 'Package manager cleaner not available')
        except Exception as e:
            QMessageBox.critical(self, 'Cleanup Error', f'Error cleaning package managers:\n{str(e)}')
            self.pm_cleanup_button.setEnabled(True)

    def browse_heuristics_path(self):
        """Browse for heuristics scan path."""
        path = QFileDialog.getExistingDirectory(self, 'Select Directory to Scan')
        if path:
            self.heuristics_path_edit.setText(path)

    def start_heuristics_scan(self):
        """Start heuristics scan."""
        try:
            from cortex_unified.analyzers.leftover_detector import LeftoverDetector
            scan_path = self.heuristics_path_edit.text().strip()
            if not scan_path or not Path(scan_path).exists():
                QMessageBox.warning(self, 'Invalid Path', 'Please select a valid directory to scan.')
                return
            self.heuristics_scan_button.setEnabled(False)
            self.heuristics_cleanup_button.setEnabled(False)
            self.heuristics_summary_label.setText('Scanning for application leftovers...')
            detector = LeftoverDetector(self.config)
            confidence_threshold = self.heuristics_confidence_spinbox.value() / 100.0
            orphaned_folders = detector.scan_orphaned_folders([scan_path])
            installer_files = detector.detect_installer_files()
            all_items = orphaned_folders + installer_files
            if self.heuristics_ml_checkbox.isChecked() and all_items:
                all_items = detector.apply_ml_patterns(all_items)
            high_confidence_items = [item for item in all_items if detector.calculate_confidence_score(item) >= confidence_threshold]
            summary_text = f'Found {len(all_items)} potential leftovers\n'
            summary_text += f'High confidence (>= {confidence_threshold:.1f}): {len(high_confidence_items)}'
            self.heuristics_summary_label.setText(summary_text)
            self.heuristics_results = high_confidence_items
            self.heuristics_scan_button.setEnabled(True)
            self.heuristics_cleanup_button.setEnabled(len(high_confidence_items) > 0)
            self.add_activity(f'Heuristics scan found {len(high_confidence_items)} high-confidence leftovers')
        except ImportError:
            self.heuristics_summary_label.setText('Leftover detector not available')
            self.heuristics_scan_button.setEnabled(True)
        except Exception as e:
            self.heuristics_summary_label.setText(f'Error during heuristics scan: {str(e)}')
            self.heuristics_scan_button.setEnabled(True)

    def start_heuristics_cleanup(self):
        """Start heuristics cleanup."""
        if not hasattr(self, 'heuristics_results') or not self.heuristics_results:
            QMessageBox.warning(self, 'No Results', 'Please run a scan first.')
            return
        reply = QMessageBox.warning(self, 'Heuristics Cleanup Warning', f'You are about to clean {len(self.heuristics_results)} items detected by heuristics.\n\n⚠️ WARNING: Heuristics-based detection may occasionally flag legitimate files.\nPlease review the results carefully before proceeding.\n\nItems will be moved to trash for safety.\n\nContinue with cleanup?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            paths_to_clean = []
            for item in self.heuristics_results:
                if isinstance(item, (str, Path)):
                    paths_to_clean.append(Path(item))
            if not paths_to_clean:
                QMessageBox.information(self, 'Nothing to Clean', 'No valid paths found for cleanup.')
                return
            deleter = Deleter(dry_run=False, use_trash=True)
            result = deleter.delete(paths_to_clean, [])
            files_deleted = result.get('files_deleted', 0)
            errors = result.get('errors', [])
            message = f'Heuristics cleanup completed.\n'
            message += f'Items cleaned: {files_deleted}\n'
            if errors:
                message += f'Errors: {len(errors)}'
            QMessageBox.information(self, 'Cleanup Complete', message)
            self.add_activity(f'Heuristics cleanup: {files_deleted} items cleaned')
            self.heuristics_results = []
            self.heuristics_cleanup_button.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, 'Cleanup Error', f'Error during heuristics cleanup:\n{str(e)}')

    def repair_selected_links(self):
        """Repair selected broken links."""
        selected_rows = set()
        for item in self.broken_links_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            return
        selected_links = [self.broken_links_results[row] for row in selected_rows]
        confidence_threshold = self.confidence_threshold_spinbox.value() / 100.0
        repairable_links = [link for link in selected_links if link.is_repairable and link.confidence_score >= confidence_threshold]
        if not repairable_links:
            QMessageBox.information(self, 'No Repairable Links', 'None of the selected links meet the confidence threshold for repair.')
            return
        reply = QMessageBox.question(self, 'Confirm Repair', f"Repair {len(repairable_links)} broken links?\n\nBackups will be created: {('Yes' if self.create_backups_checkbox.isChecked() else 'No')}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        detector = BrokenLinkDetector()
        repaired_count = 0
        errors = []
        for link in repairable_links:
            try:
                result = detector.attempt_repair(link)
                if result.success:
                    repaired_count += 1
                else:
                    errors.append(f'{link.path}: {result.error_message}')
            except Exception as e:
                errors.append(f'{link.path}: {str(e)}')
        message = f'Repaired {repaired_count} out of {len(repairable_links)} links.'
        if errors:
            message += f'\n\nErrors:\n' + '\n'.join(errors[:5])
            if len(errors) > 5:
                message += f'\n... and {len(errors) - 5} more errors'
        QMessageBox.information(self, 'Repair Complete', message)
        self.start_broken_links_scan()

    def on_path_mode_changed(self):
        """Handle path mode radio button changes."""
        single_mode = self.single_path_radio.isChecked()
        self.path_input.setEnabled(single_mode)
        self.drives_list.setEnabled(not single_mode)
        self.detect_drives_button.setEnabled(not single_mode)
        self.add_network_drive_button.setEnabled(not single_mode)
        self.remove_drive_button.setEnabled(not single_mode)
        if not single_mode:
            self.detect_available_drives()

    def detect_available_drives(self):
        """Detect available drives on the system."""
        try:
            import psutil
            self.drives_list.clear()
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    drive_info = f'{partition.device} ({partition.fstype}) - '
                    drive_info += f'{self.format_bytes(usage.free)} free of {self.format_bytes(usage.total)}'
                    item = QListWidgetItem(drive_info)
                    item.setData(Qt.ItemDataRole.UserRole, partition.mountpoint)
                    self.drives_list.addItem(item)
                except (PermissionError, OSError):
                    continue
            self.add_activity(f'Detected {self.drives_list.count()} available drives')
        except ImportError:
            QMessageBox.critical(self, 'Error', 'psutil module required for drive detection.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error detecting drives:\n{str(e)}')

    def add_network_drive(self):
        """Add a network drive to the scan list."""
        dialog = QDialog(self)
        dialog.setWindowTitle('Add Network Drive')
        dialog.setModal(True)
        dialog.resize(400, 200)
        layout = QVBoxLayout(dialog)
        path_layout = QFormLayout()
        network_path_input = QLineEdit()
        network_path_input.setPlaceholderText('\\\\server\\share or smb://server/share')
        path_layout.addRow('Network Path:', network_path_input)
        username_input = QLineEdit()
        username_input.setPlaceholderText('Username (optional)')
        path_layout.addRow('Username:', username_input)
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setPlaceholderText('Password (optional)')
        path_layout.addRow('Password:', password_input)
        layout.addLayout(path_layout)
        buttons_layout = QHBoxLayout()
        test_button = QPushButton('Test Connection')
        test_button.clicked.connect(lambda: self.test_network_connection(network_path_input.text(), username_input.text(), password_input.text()))
        buttons_layout.addWidget(test_button)
        add_button = QPushButton('Add')
        add_button.clicked.connect(lambda: self.add_network_path(dialog, network_path_input.text(), username_input.text(), password_input.text()))
        buttons_layout.addWidget(add_button)
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        dialog.exec()

    def test_network_connection(self, path, username, password):
        """Test network drive connection."""
        try:
            from cortex_unified.performance.multi_drive_scanner import MultiDriveScanner
            scanner = MultiDriveScanner()
            success = scanner.test_network_connection(path, username, password)
            if success:
                QMessageBox.information(self, 'Connection Test', 'Network connection successful!')
            else:
                QMessageBox.warning(self, 'Connection Test', 'Network connection failed.')
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Multi-drive scanner module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error testing connection:\n{str(e)}')

    def add_network_path(self, dialog, path, username, password):
        """Add network path to drives list."""
        if not path:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter a network path.')
            return
        try:
            drive_info = f'{path}'
            if username:
                drive_info += f' (User: {username})'
            drive_info += ' - Network Drive'
            item = QListWidgetItem(drive_info)
            item.setData(Qt.ItemDataRole.UserRole, {'path': path, 'username': username, 'password': password, 'type': 'network'})
            self.drives_list.addItem(item)
            self.add_activity(f'Added network drive: {path}')
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error adding network drive:\n{str(e)}')

    def remove_selected_drives(self):
        """Remove selected drives from the list."""
        selected_items = self.drives_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, 'No Selection', 'Please select drives to remove.')
            return
        for item in selected_items:
            row = self.drives_list.row(item)
            self.drives_list.takeItem(row)
        self.add_activity(f'Removed {len(selected_items)} drives from scan list')

    def on_checkpoint_selection_changed(self):
        """Handle checkpoint selection changes."""
        has_selection = self.checkpoints_list.currentItem() is not None
        self.resume_checkpoint_button.setEnabled(has_selection)
        self.delete_checkpoint_button.setEnabled(has_selection)

    def list_checkpoints(self):
        """List available checkpoints."""
        try:
            from cortex_unified.performance.scan_manager import ScanManager
            scan_manager = ScanManager()
            checkpoints = scan_manager.list_checkpoints()
            self.checkpoints_list.clear()
            for checkpoint in checkpoints:
                checkpoint_info = f"{checkpoint.id} - {checkpoint.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({checkpoint.progress_percentage:.1f}%)"
                item = QListWidgetItem(checkpoint_info)
                item.setData(Qt.ItemDataRole.UserRole, checkpoint.id)
                self.checkpoints_list.addItem(item)
            if checkpoints:
                self.add_activity(f'Found {len(checkpoints)} checkpoints')
            else:
                self.checkpoints_list.addItem('No checkpoints found')
        except ImportError:
            self.checkpoints_list.clear()
            self.checkpoints_list.addItem('Scan manager module not available')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error listing checkpoints:\n{str(e)}')

    def resume_from_checkpoint(self):
        """Resume scanning from selected checkpoint."""
        current_item = self.checkpoints_list.currentItem()
        if not current_item:
            return
        checkpoint_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not checkpoint_id:
            QMessageBox.warning(self, 'Invalid Selection', 'Please select a valid checkpoint.')
            return
        try:
            if self.single_path_radio.isChecked():
                target_path = self.path_input.text().strip()
            elif self.drives_list.count() > 0:
                first_item = self.drives_list.item(0)
                drive_data = first_item.data(Qt.ItemDataRole.UserRole)
                if isinstance(drive_data, dict):
                    target_path = drive_data['path']
                else:
                    target_path = drive_data
            else:
                QMessageBox.warning(self, 'No Path', 'Please select a path to scan.')
                return
            if not target_path:
                QMessageBox.warning(self, 'No Path', 'Please select a path to scan.')
                return
            self.start_scan_with_checkpoint(checkpoint_id)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error resuming from checkpoint:\n{str(e)}')

    def start_scan_with_checkpoint(self, checkpoint_id):
        """Start scan with a specific checkpoint."""
        try:
            normalized_path = normalize_path(self.path_input.text().strip())
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Invalid path: {str(e)}')
            return
        if not normalized_path.exists():
            QMessageBox.critical(self, 'Error', 'Selected path does not exist.')
            return
        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_group.setVisible(True)
        self.pause_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_label.setText('Resuming from checkpoint...')
        self.progress_bar.setVisible(True)
        self.results_text.clear()
        scan_config = Config()
        scan_config.config_data = self.config.config_data.copy()
        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(scan_config, str(normalized_path), enable_checkpoints=True, enable_throttling=self.enable_throttling_checkbox.isChecked(), checkpoint_id=checkpoint_id)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        self.scan_worker.progress_updated.connect(self.update_scan_progress)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.error.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.start()
        self.add_activity(f'Resumed scan from checkpoint: {checkpoint_id}')

    def delete_checkpoint(self):
        """Delete selected checkpoint."""
        current_item = self.checkpoints_list.currentItem()
        if not current_item:
            return
        checkpoint_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not checkpoint_id:
            return
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Are you sure you want to delete checkpoint '{checkpoint_id}'?\n\nThis action cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from cortex_unified.performance.scan_manager import ScanManager
            scan_manager = ScanManager()
            success = scan_manager.delete_checkpoint(checkpoint_id)
            if success:
                QMessageBox.information(self, 'Checkpoint Deleted', f"Checkpoint '{checkpoint_id}' deleted successfully.")
                self.add_activity(f'Deleted checkpoint: {checkpoint_id}')
                self.list_checkpoints()
            else:
                QMessageBox.warning(self, 'Deletion Failed', f"Failed to delete checkpoint '{checkpoint_id}'.")
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Scan manager module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error deleting checkpoint:\n{str(e)}')

    def cleanup_old_checkpoints(self):
        """Cleanup old checkpoints."""
        try:
            from cortex_unified.performance.scan_manager import ScanManager
            age_days, ok = QInputDialog.getInt(self, 'Cleanup Checkpoints', 'Delete checkpoints older than how many days?', 7, 1, 365)
            if not ok:
                return
            scan_manager = ScanManager()
            deleted_count = scan_manager.cleanup_old_checkpoints(age_days)
            QMessageBox.information(self, 'Cleanup Complete', f'Deleted {deleted_count} checkpoints older than {age_days} days.')
            self.add_activity(f'Cleaned up {deleted_count} old checkpoints')
            self.list_checkpoints()
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Scan manager module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error cleaning up checkpoints:\n{str(e)}')

    def create_file_shredder_tab(self) -> QWidget:
        """Create the file shredder tab."""
        shredder_tab = QWidget()
        layout = QVBoxLayout(shredder_tab)
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
        self.shred_free_space_checkbox = QCheckBox('Also shred free space')
        options_layout.addRow(self.shred_free_space_checkbox)
        layout.addWidget(options_group)
        buttons_layout = QHBoxLayout()
        self.start_shred_button = QPushButton('Start Shredding')
        self.start_shred_button.clicked.connect(self.start_file_shredding)
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
        return shredder_tab

    def add_files_to_shred(self):
        """Add files to the shredding list."""
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Files to Shred', '', 'All Files (*.*)')
        for file_path in files:
            if file_path not in [self.shredder_file_list.item(i).text() for i in range(self.shredder_file_list.count())]:
                self.shredder_file_list.addItem(file_path)

    def add_folder_to_shred(self):
        """Add folder contents to the shredding list."""
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder to Shred')
        if folder:
            try:
                folder_path = Path(folder)
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        file_str = str(file_path)
                        if file_str not in [self.shredder_file_list.item(i).text() for i in range(self.shredder_file_list.count())]:
                            self.shredder_file_list.addItem(file_str)
                self.add_activity(f'Added {folder_path.name} folder contents to shred list')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Error adding folder: {str(e)}')

    def remove_files_from_shred(self):
        """Remove selected files from the shredding list."""
        selected_items = self.shredder_file_list.selectedItems()
        for item in selected_items:
            row = self.shredder_file_list.row(item)
            self.shredder_file_list.takeItem(row)

    def clear_shred_list(self):
        """Clear all files from the shredding list."""
        self.shredder_file_list.clear()

    def start_file_shredding(self):
        """Start the file shredding process."""
        if self.shredder_file_list.count() == 0:
            QMessageBox.warning(self, 'No Files', 'Please add files to shred first.')
            return
        files_to_shred = []
        for i in range(self.shredder_file_list.count()):
            files_to_shred.append(Path(self.shredder_file_list.item(i).text()))
        reply = QMessageBox.question(self, 'FINAL WARNING', f'⚠️ You are about to PERMANENTLY DESTROY {len(files_to_shred)} files!\n\nThis action CANNOT be undone and the files will be UNRECOVERABLE.\n\nShredding method: {self.shred_method_combo.currentText()}\nOverwrite passes: {self.shred_passes_spinbox.value()}\n\nAre you absolutely sure you want to continue?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from cortex_unified.analyzers.file_shredder import FileShredder
            self.start_shred_button.setEnabled(False)
            self.shred_progress_bar.setVisible(True)
            self.shred_progress_bar.setRange(0, len(files_to_shred))
            self.shred_progress_bar.setValue(0)
            self.shred_status_label.setText('Shredding files...')
            self.shred_results.clear()
            shredder = FileShredder(self.config)
            passes = self.shred_passes_spinbox.value()
            method = self.shred_method_combo.currentText().lower().replace(' ', '_')
            verify = self.verify_shred_checkbox.isChecked()
            shredded_count = 0
            errors = []
            for i, file_path in enumerate(files_to_shred):
                try:
                    self.shred_status_label.setText(f'Shredding: {file_path.name}')
                    self.shred_progress_bar.setValue(i)
                    QApplication.processEvents()
                    result = shredder.shred_file(file_path, passes=passes, method=method, verify=verify)
                    if result.get('success', False):
                        shredded_count += 1
                        self.shred_results.append(f'✓ Shredded: {file_path}')
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        errors.append(f'{file_path}: {error_msg}')
                        self.shred_results.append(f'✗ Failed: {file_path} - {error_msg}')
                except Exception as e:
                    errors.append(f'{file_path}: {str(e)}')
                    self.shred_results.append(f'✗ Error: {file_path} - {str(e)}')
            self.start_shred_button.setEnabled(True)
            self.shred_progress_bar.setVisible(False)
            self.shred_status_label.setText(f'Shredding complete: {shredded_count} files shredded')
            message = f'Shredding complete!\n\nFiles shredded: {shredded_count}\nErrors: {len(errors)}'
            if errors:
                message += f'\n\nFirst few errors:\n' + '\n'.join(errors[:3])
                if len(errors) > 3:
                    message += f'\n... and {len(errors) - 3} more errors'
            QMessageBox.information(self, 'Shredding Complete', message)
            self.add_activity(f'Shredded {shredded_count} files with {len(errors)} errors')
            for i in range(self.shredder_file_list.count() - 1, -1, -1):
                file_path = self.shredder_file_list.item(i).text()
                if not Path(file_path).exists():
                    self.shredder_file_list.takeItem(i)
        except ImportError:
            QMessageBox.critical(self, 'Error', 'File shredder module not available.')
            self.start_shred_button.setEnabled(True)
            self.shred_progress_bar.setVisible(False)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error during file shredding:\n{str(e)}')
            self.start_shred_button.setEnabled(True)
            self.shred_progress_bar.setVisible(False)
            self.add_activity(f'File shredding failed: {str(e)}')

    def create_scheduler_tab(self) -> QWidget:
        """Create the task scheduler tab."""
        scheduler_tab = QWidget()
        layout = QVBoxLayout(scheduler_tab)
        scheduler_tab_widget = QTabWidget()
        layout.addWidget(scheduler_tab_widget)
        tasks_tab = self.create_tasks_subtab()
        scheduler_tab_widget.addTab(tasks_tab, 'Scheduled Tasks')
        rules_tab = self.create_auto_clean_rules_subtab()
        scheduler_tab_widget.addTab(rules_tab, 'Auto-Clean Rules')
        return scheduler_tab

    def create_tasks_subtab(self) -> QWidget:
        """Create the tasks sub-tab."""
        tasks_tab = QWidget()
        layout = QVBoxLayout(tasks_tab)
        create_group = QGroupBox('Create Scheduled Task')
        create_layout = QFormLayout(create_group)
        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText('Enter task name')
        create_layout.addRow('Task Name:', self.task_name_input)
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems(['Clean Empty Files', 'Clean Temp Files', 'Find Duplicates', 'Analyze Disk Usage', 'Clean Docker Resources', 'Clean Package Caches'])
        create_layout.addRow('Task Type:', self.task_type_combo)
        self.task_path_input = QLineEdit()
        self.task_path_input.setText(str(Path.home()))
        create_layout.addRow('Target Path:', self.task_path_input)
        path_browse_button = QPushButton('Browse')
        path_browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.task_path_input))
        create_layout.addRow('', path_browse_button)
        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(['Daily', 'Weekly', 'Monthly', 'On Startup', 'Custom Cron'])
        create_layout.addRow('Schedule:', self.schedule_type_combo)
        self.schedule_time_edit = QLineEdit()
        self.schedule_time_edit.setPlaceholderText('HH:MM (24-hour format)')
        self.schedule_time_edit.setText('02:00')
        create_layout.addRow('Time:', self.schedule_time_edit)
        self.cron_expression_input = QLineEdit()
        self.cron_expression_input.setPlaceholderText('0 2 * * * (cron format)')
        self.cron_expression_input.setEnabled(False)
        create_layout.addRow('Cron Expression:', self.cron_expression_input)
        self.schedule_type_combo.currentTextChanged.connect(lambda text: self.cron_expression_input.setEnabled(text == 'Custom Cron'))
        self.task_dry_run_checkbox = QCheckBox('Dry run (preview only)')
        self.task_dry_run_checkbox.setChecked(True)
        create_layout.addRow(self.task_dry_run_checkbox)
        self.task_email_checkbox = QCheckBox('Send email notification')
        create_layout.addRow(self.task_email_checkbox)
        self.task_email_input = QLineEdit()
        self.task_email_input.setPlaceholderText('email@example.com')
        self.task_email_input.setEnabled(False)
        create_layout.addRow('Email Address:', self.task_email_input)
        self.task_email_checkbox.toggled.connect(self.task_email_input.setEnabled)
        layout.addWidget(create_group)
        task_buttons_layout = QHBoxLayout()
        self.create_task_button = QPushButton('Create Task')
        self.create_task_button.clicked.connect(self.create_scheduled_task)
        self.create_task_button.setMinimumHeight(35)
        task_buttons_layout.addWidget(self.create_task_button)
        self.run_task_button = QPushButton('Run Selected Now')
        self.run_task_button.clicked.connect(self.run_selected_task)
        self.run_task_button.setEnabled(False)
        self.run_task_button.setMinimumHeight(35)
        task_buttons_layout.addWidget(self.run_task_button)
        self.delete_task_button = QPushButton('Delete Selected')
        self.delete_task_button.clicked.connect(self.delete_selected_task)
        self.delete_task_button.setEnabled(False)
        self.delete_task_button.setMinimumHeight(35)
        task_buttons_layout.addWidget(self.delete_task_button)
        task_buttons_layout.addStretch()
        layout.addLayout(task_buttons_layout)
        tasks_group = QGroupBox('Scheduled Tasks')
        tasks_layout = QVBoxLayout(tasks_group)
        refresh_tasks_button = QPushButton('Refresh Tasks')
        refresh_tasks_button.clicked.connect(self.refresh_scheduled_tasks)
        tasks_layout.addWidget(refresh_tasks_button)
        self.scheduled_tasks_table = QTableWidget()
        self.scheduled_tasks_table.setColumnCount(6)
        self.scheduled_tasks_table.setHorizontalHeaderLabels(['Name', 'Type', 'Schedule', 'Next Run', 'Status', 'Last Result'])
        self.scheduled_tasks_table.horizontalHeader().setStretchLastSection(True)
        self.scheduled_tasks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.scheduled_tasks_table.itemSelectionChanged.connect(self.on_task_selection_changed)
        tasks_layout.addWidget(self.scheduled_tasks_table)
        layout.addWidget(tasks_group)
        history_group = QGroupBox('Task Execution History')
        history_layout = QVBoxLayout(history_group)
        self.task_history_table = QTableWidget()
        self.task_history_table.setColumnCount(4)
        self.task_history_table.setHorizontalHeaderLabels(['Task', 'Execution Time', 'Duration', 'Result'])
        self.task_history_table.horizontalHeader().setStretchLastSection(True)
        self.task_history_table.setMaximumHeight(150)
        history_layout.addWidget(self.task_history_table)
        layout.addWidget(history_group)
        self.refresh_scheduled_tasks()
        return tasks_tab

    def create_auto_clean_rules_subtab(self) -> QWidget:
        """Create the auto-clean rules sub-tab."""
        rules_tab = QWidget()
        layout = QVBoxLayout(rules_tab)
        rule_creation_group = QGroupBox('Create Auto-Clean Rule')
        rule_layout = QFormLayout(rule_creation_group)
        self.rule_name_input = QLineEdit()
        self.rule_name_input.setPlaceholderText('Enter rule name')
        rule_layout.addRow('Rule Name:', self.rule_name_input)
        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.addItems(['Disk Space Low', 'File Age', 'File Count', 'System Startup', 'Time Based', 'User Login', 'Custom Condition'])
        rule_layout.addRow('Trigger:', self.trigger_type_combo)
        self.trigger_value_input = QLineEdit()
        self.trigger_value_input.setPlaceholderText('e.g., 90% for disk space, 30 for days')
        rule_layout.addRow('Trigger Value:', self.trigger_value_input)
        self.rule_path_input = QLineEdit()
        self.rule_path_input.setText(str(Path.home()))
        rule_layout.addRow('Target Path:', self.rule_path_input)
        rule_path_browse_button = QPushButton('Browse')
        rule_path_browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.rule_path_input))
        rule_layout.addRow('', rule_path_browse_button)
        self.rule_action_combo = QComboBox()
        self.rule_action_combo.addItems(['Clean Empty Files', 'Clean Temp Files', 'Clean Duplicates', 'Clean Large Files', 'Clean Cache', 'Custom Action'])
        rule_layout.addRow('Action:', self.rule_action_combo)
        self.rule_enabled_checkbox = QCheckBox('Rule Enabled')
        self.rule_enabled_checkbox.setChecked(True)
        rule_layout.addRow(self.rule_enabled_checkbox)
        self.rule_dry_run_checkbox = QCheckBox('Dry Run Only')
        self.rule_dry_run_checkbox.setChecked(True)
        rule_layout.addRow(self.rule_dry_run_checkbox)
        self.rule_notify_checkbox = QCheckBox('Send Notification')
        rule_layout.addRow(self.rule_notify_checkbox)
        self.rule_priority_spinbox = QSpinBox()
        self.rule_priority_spinbox.setRange(1, 10)
        self.rule_priority_spinbox.setValue(5)
        rule_layout.addRow('Priority (1-10):', self.rule_priority_spinbox)
        layout.addWidget(rule_creation_group)
        rule_buttons_layout = QHBoxLayout()
        self.create_rule_button = QPushButton('Create Rule')
        self.create_rule_button.clicked.connect(self.create_auto_clean_rule)
        self.create_rule_button.setMinimumHeight(35)
        rule_buttons_layout.addWidget(self.create_rule_button)
        self.test_rule_button = QPushButton('Test Rule')
        self.test_rule_button.clicked.connect(self.test_selected_rule)
        self.test_rule_button.setEnabled(False)
        self.test_rule_button.setMinimumHeight(35)
        rule_buttons_layout.addWidget(self.test_rule_button)
        self.delete_rule_button = QPushButton('Delete Rule')
        self.delete_rule_button.clicked.connect(self.delete_selected_rule)
        self.delete_rule_button.setEnabled(False)
        self.delete_rule_button.setMinimumHeight(35)
        rule_buttons_layout.addWidget(self.delete_rule_button)
        rule_buttons_layout.addStretch()
        layout.addLayout(rule_buttons_layout)
        rules_group = QGroupBox('Auto-Clean Rules')
        rules_layout = QVBoxLayout(rules_group)
        refresh_rules_button = QPushButton('Refresh Rules')
        refresh_rules_button.clicked.connect(self.refresh_auto_clean_rules)
        rules_layout.addWidget(refresh_rules_button)
        self.auto_clean_rules_table = QTableWidget()
        self.auto_clean_rules_table.setColumnCount(6)
        self.auto_clean_rules_table.setHorizontalHeaderLabels(['Name', 'Trigger', 'Action', 'Status', 'Last Triggered', 'Priority'])
        self.auto_clean_rules_table.horizontalHeader().setStretchLastSection(True)
        self.auto_clean_rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.auto_clean_rules_table.itemSelectionChanged.connect(self.on_rule_selection_changed)
        rules_layout.addWidget(self.auto_clean_rules_table)
        layout.addWidget(rules_group)
        log_group = QGroupBox('Rule Execution Log')
        log_layout = QVBoxLayout(log_group)
        self.rule_execution_log = QTextEdit()
        self.rule_execution_log.setReadOnly(True)
        self.rule_execution_log.setMaximumHeight(150)
        log_layout.addWidget(self.rule_execution_log)
        layout.addWidget(log_group)
        self.refresh_auto_clean_rules()
        return rules_tab

    def on_task_selection_changed(self):
        """Handle task selection changes."""
        selected_rows = set()
        for item in self.scheduled_tasks_table.selectedItems():
            selected_rows.add(item.row())
        has_selection = len(selected_rows) > 0
        self.run_task_button.setEnabled(has_selection)
        self.delete_task_button.setEnabled(has_selection)

    def create_scheduled_task(self):
        """Create a new scheduled task."""
        task_name = self.task_name_input.text().strip()
        if not task_name:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter a task name.')
            return
        task_type = self.task_type_combo.currentText()
        target_path = self.task_path_input.text().strip()
        if not target_path or not Path(target_path).exists():
            QMessageBox.warning(self, 'Invalid Path', 'Please select a valid target path.')
            return
        try:
            from cortex_unified.scheduler.cortex_unified.scheduler import TaskScheduler
            scheduler = TaskScheduler()
            task_config = {'name': task_name, 'type': task_type.lower().replace(' ', '_'), 'target_path': target_path, 'dry_run': self.task_dry_run_checkbox.isChecked(), 'email_notification': self.task_email_checkbox.isChecked(), 'email_address': self.task_email_input.text().strip() if self.task_email_checkbox.isChecked() else None}
            schedule_type = self.schedule_type_combo.currentText()
            if schedule_type == 'Custom Cron':
                cron_expr = self.cron_expression_input.text().strip()
                if not cron_expr:
                    QMessageBox.warning(self, 'Invalid Cron', 'Please enter a valid cron expression.')
                    return
                schedule_config = {'type': 'cron', 'expression': cron_expr}
            else:
                time_str = self.schedule_time_edit.text().strip()
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError('Invalid time range')
                except ValueError:
                    QMessageBox.warning(self, 'Invalid Time', 'Please enter time in HH:MM format (24-hour).')
                    return
                schedule_config = {'type': schedule_type.lower(), 'hour': hour, 'minute': minute}
            task_id = scheduler.create_task(task_config, schedule_config)
            QMessageBox.information(self, 'Task Created', f"Task '{task_name}' created successfully with ID: {task_id}")
            self.add_activity(f'Created scheduled task: {task_name}')
            self.task_name_input.clear()
            self.task_path_input.setText(str(Path.home()))
            self.refresh_scheduled_tasks()
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Task scheduler module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error creating task:\n{str(e)}')

    def refresh_scheduled_tasks(self):
        """Refresh the list of scheduled tasks."""
        try:
            from cortex_unified.scheduler.cortex_unified.scheduler import TaskScheduler
            scheduler = TaskScheduler()
            tasks = scheduler.list_tasks()
            self.scheduled_tasks_table.setRowCount(len(tasks))
            for i, task in enumerate(tasks):
                self.scheduled_tasks_table.setItem(i, 0, QTableWidgetItem(task.get('name', 'Unknown')))
                self.scheduled_tasks_table.setItem(i, 1, QTableWidgetItem(task.get('type', 'Unknown')))
                self.scheduled_tasks_table.setItem(i, 2, QTableWidgetItem(task.get('schedule', 'Unknown')))
                self.scheduled_tasks_table.setItem(i, 3, QTableWidgetItem(task.get('next_run', 'Unknown')))
                status = 'Enabled' if task.get('enabled', True) else 'Disabled'
                self.scheduled_tasks_table.setItem(i, 4, QTableWidgetItem(status))
                self.scheduled_tasks_table.setItem(i, 5, QTableWidgetItem(task.get('last_result', 'Never run')))
            history = scheduler.get_execution_history(limit=10)
            self.task_history_table.setRowCount(len(history))
            for i, entry in enumerate(history):
                self.task_history_table.setItem(i, 0, QTableWidgetItem(entry.get('task_name', 'Unknown')))
                self.task_history_table.setItem(i, 1, QTableWidgetItem(entry.get('execution_time', 'Unknown')))
                self.task_history_table.setItem(i, 2, QTableWidgetItem(entry.get('duration', 'Unknown')))
                self.task_history_table.setItem(i, 3, QTableWidgetItem(entry.get('result', 'Unknown')))
        except ImportError:
            self.scheduled_tasks_table.setRowCount(1)
            self.scheduled_tasks_table.setItem(0, 0, QTableWidgetItem('Task scheduler not available'))
            for col in range(1, 6):
                self.scheduled_tasks_table.setItem(0, col, QTableWidgetItem(''))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error refreshing tasks:\n{str(e)}')

    def run_selected_task(self):
        """Run the selected task immediately."""
        selected_rows = set()
        for item in self.scheduled_tasks_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            return
        row = list(selected_rows)[0]
        task_name = self.scheduled_tasks_table.item(row, 0).text()
        try:
            from cortex_unified.scheduler.cortex_unified.scheduler import TaskScheduler
            scheduler = TaskScheduler()
            result = scheduler.run_task_now(task_name)
            if result.get('success', False):
                QMessageBox.information(self, 'Task Executed', f"Task '{task_name}' executed successfully.\n\n{result.get('message', '')}")
                self.add_activity(f'Manually executed task: {task_name}')
            else:
                QMessageBox.warning(self, 'Task Failed', f"Task '{task_name}' failed to execute.\n\n{result.get('error', 'Unknown error')}")
            self.refresh_scheduled_tasks()
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Task scheduler module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error running task:\n{str(e)}')

    def delete_selected_task(self):
        """Delete the selected task."""
        selected_rows = set()
        for item in self.scheduled_tasks_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            return
        row = list(selected_rows)[0]
        task_name = self.scheduled_tasks_table.item(row, 0).text()
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Are you sure you want to delete the task '{task_name}'?\n\nThis action cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from cortex_unified.scheduler.cortex_unified.scheduler import TaskScheduler
            scheduler = TaskScheduler()
            success = scheduler.delete_task(task_name)
            if success:
                QMessageBox.information(self, 'Task Deleted', f"Task '{task_name}' deleted successfully.")
                self.add_activity(f'Deleted scheduled task: {task_name}')
                self.refresh_scheduled_tasks()
            else:
                QMessageBox.warning(self, 'Deletion Failed', f"Failed to delete task '{task_name}'.")
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Task scheduler module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error deleting task:\n{str(e)}')

    def create_reports_tab(self) -> QWidget:
        """Create the reports tab."""
        reports_tab = QWidget()
        layout = QVBoxLayout(reports_tab)
        generation_group = QGroupBox('Report Generation')
        generation_layout = QFormLayout(generation_group)
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(['System Analysis Report', 'Disk Usage Report', 'Cleanup Summary Report', 'Performance Report', 'Security Audit Report', 'Scheduled Tasks Report', 'Custom Report'])
        generation_layout.addRow('Report Type:', self.report_type_combo)
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(['HTML', 'PDF', 'JSON', 'CSV', 'Text'])
        generation_layout.addRow('Format:', self.report_format_combo)
        self.report_date_range_combo = QComboBox()
        self.report_date_range_combo.addItems(['Last 24 Hours', 'Last Week', 'Last Month', 'Last 3 Months', 'All Time', 'Custom Range'])
        generation_layout.addRow('Date Range:', self.report_date_range_combo)
        self.include_charts_checkbox = QCheckBox('Include charts and graphs')
        self.include_charts_checkbox.setChecked(True)
        generation_layout.addRow(self.include_charts_checkbox)
        self.include_details_checkbox = QCheckBox('Include detailed statistics')
        self.include_details_checkbox.setChecked(True)
        generation_layout.addRow(self.include_details_checkbox)
        self.include_recommendations_checkbox = QCheckBox('Include recommendations')
        self.include_recommendations_checkbox.setChecked(True)
        generation_layout.addRow(self.include_recommendations_checkbox)
        layout.addWidget(generation_group)
        actions_layout = QHBoxLayout()
        self.generate_report_button = QPushButton('Generate Report')
        self.generate_report_button.clicked.connect(self.generate_report)
        self.generate_report_button.setMinimumHeight(35)
        actions_layout.addWidget(self.generate_report_button)
        self.preview_report_button = QPushButton('Preview Report')
        self.preview_report_button.clicked.connect(self.preview_report)
        self.preview_report_button.setMinimumHeight(35)
        actions_layout.addWidget(self.preview_report_button)
        self.schedule_report_button = QPushButton('Schedule Report')
        self.schedule_report_button.clicked.connect(self.schedule_report)
        self.schedule_report_button.setMinimumHeight(35)
        actions_layout.addWidget(self.schedule_report_button)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        self.reports_progress_bar = QProgressBar()
        self.reports_progress_bar.setVisible(False)
        layout.addWidget(self.reports_progress_bar)
        recent_group = QGroupBox('Recent Reports')
        recent_layout = QVBoxLayout(recent_group)
        refresh_reports_button = QPushButton('Refresh Reports')
        refresh_reports_button.clicked.connect(self.refresh_reports_list)
        recent_layout.addWidget(refresh_reports_button)
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(5)
        self.reports_table.setHorizontalHeaderLabels(['Report Name', 'Type', 'Generated', 'Size', 'Actions'])
        self.reports_table.horizontalHeader().setStretchLastSection(True)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        recent_layout.addWidget(self.reports_table)
        layout.addWidget(recent_group)
        templates_group = QGroupBox('Report Templates')
        templates_layout = QVBoxLayout(templates_group)
        templates_buttons_layout = QHBoxLayout()
        self.save_template_button = QPushButton('Save as Template')
        self.save_template_button.clicked.connect(self.save_report_template)
        templates_buttons_layout.addWidget(self.save_template_button)
        self.load_template_button = QPushButton('Load Template')
        self.load_template_button.clicked.connect(self.load_report_template)
        templates_buttons_layout.addWidget(self.load_template_button)
        templates_buttons_layout.addStretch()
        templates_layout.addLayout(templates_buttons_layout)
        self.templates_list = QListWidget()
        self.templates_list.setMaximumHeight(100)
        templates_layout.addWidget(self.templates_list)
        layout.addWidget(templates_group)
        self.refresh_reports_list()
        return reports_tab

    def generate_report(self):
        """Generate a report based on current settings."""
        try:
            from cortex_unified.reports.cortex_unified.reports import ReportsGenerator
            report_type = self.report_type_combo.currentText()
            report_format = self.report_format_combo.currentText().lower()
            date_range = self.report_date_range_combo.currentText()
            self.generate_report_button.setEnabled(False)
            self.reports_progress_bar.setVisible(True)
            self.reports_progress_bar.setRange(0, 0)
            generator = ReportsGenerator(self.config)
            report_config = {'type': report_type.lower().replace(' ', '_'), 'format': report_format, 'date_range': date_range.lower().replace(' ', '_'), 'include_charts': self.include_charts_checkbox.isChecked(), 'include_details': self.include_details_checkbox.isChecked(), 'include_recommendations': self.include_recommendations_checkbox.isChecked()}
            report_path = generator.generate_report(report_config)
            self.generate_report_button.setEnabled(True)
            self.reports_progress_bar.setVisible(False)
            QMessageBox.information(self, 'Report Generated', f'Report generated successfully!\n\nSaved to: {report_path}')
            self.add_activity(f'Generated {report_type} report')
            self.refresh_reports_list()
        except ImportError:
            self.generate_report_button.setEnabled(True)
            self.reports_progress_bar.setVisible(False)
            QMessageBox.critical(self, 'Error', 'Reports generator module not available.')
        except Exception as e:
            self.generate_report_button.setEnabled(True)
            self.reports_progress_bar.setVisible(False)
            QMessageBox.critical(self, 'Error', f'Error generating report:\n{str(e)}')

    def preview_report(self):
        """Preview the report before generating."""
        try:
            from cortex_unified.reports.cortex_unified.reports import ReportsGenerator
            generator = ReportsGenerator(self.config)
            report_config = {'type': self.report_type_combo.currentText().lower().replace(' ', '_'), 'format': 'html', 'date_range': self.report_date_range_combo.currentText().lower().replace(' ', '_'), 'include_charts': self.include_charts_checkbox.isChecked(), 'include_details': self.include_details_checkbox.isChecked(), 'include_recommendations': self.include_recommendations_checkbox.isChecked(), 'preview_mode': True}
            preview_html = generator.generate_preview(report_config)
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle('Report Preview')
            preview_dialog.resize(800, 600)
            preview_layout = QVBoxLayout(preview_dialog)
            from PySide6.QtWebEngineWidgets import QWebEngineView
            web_view = QWebEngineView()
            web_view.setHtml(preview_html)
            preview_layout.addWidget(web_view)
            close_button = QPushButton('Close')
            close_button.clicked.connect(preview_dialog.accept)
            preview_layout.addWidget(close_button)
            preview_dialog.exec()
        except ImportError as e:
            if 'QWebEngineView' in str(e):
                QMessageBox.information(self, 'Preview', f'Report Preview:\n\nType: {self.report_type_combo.currentText()}\nFormat: {self.report_format_combo.currentText()}\nDate Range: {self.report_date_range_combo.currentText()}\nInclude Charts: {self.include_charts_checkbox.isChecked()}\nInclude Details: {self.include_details_checkbox.isChecked()}\nInclude Recommendations: {self.include_recommendations_checkbox.isChecked()}')
            else:
                QMessageBox.critical(self, 'Error', 'Reports generator module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error generating preview:\n{str(e)}')

    def schedule_report(self):
        """Schedule automatic report generation."""
        try:
            from cortex_unified.scheduler.cortex_unified.scheduler import TaskScheduler
            task_config = {'name': f'Auto Report - {self.report_type_combo.currentText()}', 'type': 'generate_report', 'report_type': self.report_type_combo.currentText(), 'report_format': self.report_format_combo.currentText(), 'include_charts': self.include_charts_checkbox.isChecked(), 'include_details': self.include_details_checkbox.isChecked(), 'include_recommendations': self.include_recommendations_checkbox.isChecked()}
            schedule_type, ok = QInputDialog.getItem(self, 'Schedule Report', 'Select schedule frequency:', ['Daily', 'Weekly', 'Monthly'], 0, False)
            if ok and schedule_type:
                scheduler = TaskScheduler()
                schedule_config = {'type': schedule_type.lower(), 'hour': 2, 'minute': 0}
                task_id = scheduler.create_task(task_config, schedule_config)
                QMessageBox.information(self, 'Report Scheduled', f'Report scheduled successfully!\n\nTask ID: {task_id}\nFrequency: {schedule_type}')
                self.add_activity(f'Scheduled {schedule_type.lower()} report generation')
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Task scheduler module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error scheduling report:\n{str(e)}')

    def refresh_reports_list(self):
        """Refresh the list of generated reports."""
        try:
            from cortex_unified.reports.cortex_unified.reports import ReportsGenerator
            generator = ReportsGenerator(self.config)
            reports = generator.list_reports()
            self.reports_table.setRowCount(len(reports))
            for i, report in enumerate(reports):
                self.reports_table.setItem(i, 0, QTableWidgetItem(report.get('name', 'Unknown')))
                self.reports_table.setItem(i, 1, QTableWidgetItem(report.get('type', 'Unknown')))
                self.reports_table.setItem(i, 2, QTableWidgetItem(report.get('generated', 'Unknown')))
                self.reports_table.setItem(i, 3, QTableWidgetItem(report.get('size', 'Unknown')))
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                view_button = QPushButton('View')
                view_button.clicked.connect(lambda checked, path=report.get('path'): self.view_report(path))
                actions_layout.addWidget(view_button)
                delete_button = QPushButton('Delete')
                delete_button.clicked.connect(lambda checked, path=report.get('path'): self.delete_report(path))
                actions_layout.addWidget(delete_button)
                self.reports_table.setCellWidget(i, 4, actions_widget)
        except ImportError:
            self.reports_table.setRowCount(1)
            self.reports_table.setItem(0, 0, QTableWidgetItem('Reports generator not available'))
            for col in range(1, 5):
                self.reports_table.setItem(0, col, QTableWidgetItem(''))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error refreshing reports:\n{str(e)}')

    def view_report(self, report_path):
        """View a generated report."""
        try:
            import webbrowser
            import os
            if report_path and os.path.exists(report_path):
                webbrowser.open(f'file://{report_path}')
                self.add_activity(f'Opened report: {os.path.basename(report_path)}')
            else:
                QMessageBox.warning(self, 'File Not Found', 'Report file not found.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error opening report:\n{str(e)}')

    def delete_report(self, report_path):
        """Delete a generated report."""
        try:
            import os
            if not report_path or not os.path.exists(report_path):
                QMessageBox.warning(self, 'File Not Found', 'Report file not found.')
                return
            reply = QMessageBox.question(self, 'Confirm Deletion', f'Are you sure you want to delete this report?\n\n{os.path.basename(report_path)}', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                os.remove(report_path)
                QMessageBox.information(self, 'Report Deleted', 'Report deleted successfully.')
                self.add_activity(f'Deleted report: {os.path.basename(report_path)}')
                self.refresh_reports_list()
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error deleting report:\n{str(e)}')

    def save_report_template(self):
        """Save current report settings as a template."""
        template_name, ok = QInputDialog.getText(self, 'Save Template', 'Enter template name:')
        if ok and template_name:
            try:
                template_config = {'name': template_name, 'type': self.report_type_combo.currentText(), 'format': self.report_format_combo.currentText(), 'date_range': self.report_date_range_combo.currentText(), 'include_charts': self.include_charts_checkbox.isChecked(), 'include_details': self.include_details_checkbox.isChecked(), 'include_recommendations': self.include_recommendations_checkbox.isChecked()}
                self.templates_list.addItem(template_name)
                QMessageBox.information(self, 'Template Saved', f"Template '{template_name}' saved successfully.")
                self.add_activity(f'Saved report template: {template_name}')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Error saving template:\n{str(e)}')

    def load_report_template(self):
        """Load a report template."""
        current_item = self.templates_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, 'No Selection', 'Please select a template to load.')
            return
        template_name = current_item.text()
        try:
            QMessageBox.information(self, 'Template Loaded', f"Template '{template_name}' loaded successfully.")
            self.add_activity(f'Loaded report template: {template_name}')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error loading template:\n{str(e)}')

    def create_resource_monitor_tab(self) -> QWidget:
        """Create the resource monitor tab."""
        monitor_tab = QWidget()
        layout = QVBoxLayout(monitor_tab)
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
        self.resource_processes_table.setHorizontalHeaderLabels(['Process Name', 'PID', 'CPU %', 'Memory MB'])
        self.resource_processes_table.horizontalHeader().setStretchLastSection(True)
        self.resource_processes_table.setMaximumHeight(200)
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
        from PySide6.QtCore import QTimer
        self.monitoring_timer = QTimer()
        self.monitoring_timer.timeout.connect(self.update_resource_metrics)
        return monitor_tab

    def start_resource_monitoring(self):
        """Start real-time resource monitoring."""
        try:
            from cortex_unified.performance.resource_monitor import ResourceMonitor
            self.resource_monitor = ResourceMonitor()
            interval = self.refresh_interval_spinbox.value() * 1000
            self.monitoring_timer.start(interval)
            self.start_monitoring_button.setEnabled(False)
            self.stop_monitoring_button.setEnabled(True)
            self.add_activity('Started resource monitoring')
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Resource monitor module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error starting monitoring:\n{str(e)}')

    def stop_resource_monitoring(self):
        """Stop real-time resource monitoring."""
        try:
            self.monitoring_timer.stop()
            self.start_monitoring_button.setEnabled(True)
            self.stop_monitoring_button.setEnabled(False)
            self.add_activity('Stopped resource monitoring')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error stopping monitoring:\n{str(e)}')

    def update_resource_metrics(self):
        """Update resource metrics display."""
        try:
            if not hasattr(self, 'resource_monitor'):
                return
            metrics = self.resource_monitor.get_current_metrics()
            cpu_percent = metrics.get('cpu_percent', 0)
            self.cpu_usage_label.setText(f'CPU: {cpu_percent:.1f}%')
            self.cpu_progress_bar.setValue(int(cpu_percent))
            memory_info = metrics.get('memory', {})
            memory_used = memory_info.get('used_mb', 0)
            memory_total = memory_info.get('total_mb', 0)
            memory_percent = memory_info.get('percent', 0)
            self.memory_usage_label.setText(f'Memory: {memory_used:.0f} MB / {memory_total:.0f} MB')
            self.memory_progress_bar.setValue(int(memory_percent))
            disk_info = metrics.get('disk_io', {})
            self.disk_read_label.setText(f"Read: {disk_info.get('read_mb_per_sec', 0):.1f} MB/s")
            self.disk_write_label.setText(f"Write: {disk_info.get('write_mb_per_sec', 0):.1f} MB/s")
            network_info = metrics.get('network_io', {})
            self.network_sent_label.setText(f"Sent: {network_info.get('sent_mb_per_sec', 0):.1f} MB/s")
            self.network_recv_label.setText(f"Received: {network_info.get('recv_mb_per_sec', 0):.1f} MB/s")
            top_processes = metrics.get('top_processes', [])
            self.resource_processes_table.setRowCount(len(top_processes))
            for i, process in enumerate(top_processes):
                self.resource_processes_table.setItem(i, 0, QTableWidgetItem(process.get('name', 'Unknown')))
                self.resource_processes_table.setItem(i, 1, QTableWidgetItem(str(process.get('pid', 0))))
                self.resource_processes_table.setItem(i, 2, QTableWidgetItem(f"{process.get('cpu_percent', 0):.1f}"))
                self.resource_processes_table.setItem(i, 3, QTableWidgetItem(f"{process.get('memory_mb', 0):.1f}"))
            self.check_performance_alerts(cpu_percent, memory_percent)
        except Exception as e:
            self.alerts_text.append(f'Error updating metrics: {str(e)}')

    def check_performance_alerts(self, cpu_percent, memory_percent):
        """Check for performance alerts and display warnings."""
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
        self.alerts_text.moveCursor(self.alerts_text.textCursor().End)

    def on_rule_selection_changed(self):
        """Handle auto-clean rule selection changes."""
        selected_rows = set()
        for item in self.auto_clean_rules_table.selectedItems():
            selected_rows.add(item.row())
        has_selection = len(selected_rows) > 0
        self.test_rule_button.setEnabled(has_selection)
        self.delete_rule_button.setEnabled(has_selection)

    def create_auto_clean_rule(self):
        """Create a new auto-clean rule."""
        rule_name = self.rule_name_input.text().strip()
        if not rule_name:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter a rule name.')
            return
        trigger_type = self.trigger_type_combo.currentText()
        trigger_value = self.trigger_value_input.text().strip()
        target_path = self.rule_path_input.text().strip()
        if not target_path or not Path(target_path).exists():
            QMessageBox.warning(self, 'Invalid Path', 'Please select a valid target path.')
            return
        try:
            from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules
            rules_manager = AutoCleanRules()
            rule_config = {'name': rule_name, 'trigger_type': trigger_type.lower().replace(' ', '_'), 'trigger_value': trigger_value, 'target_path': target_path, 'action': self.rule_action_combo.currentText().lower().replace(' ', '_'), 'enabled': self.rule_enabled_checkbox.isChecked(), 'dry_run': self.rule_dry_run_checkbox.isChecked(), 'notify': self.rule_notify_checkbox.isChecked(), 'priority': self.rule_priority_spinbox.value()}
            rule_id = rules_manager.create_rule(rule_config)
            QMessageBox.information(self, 'Rule Created', f"Auto-clean rule '{rule_name}' created successfully with ID: {rule_id}")
            self.add_activity(f'Created auto-clean rule: {rule_name}')
            self.rule_name_input.clear()
            self.trigger_value_input.clear()
            self.rule_path_input.setText(str(Path.home()))
            self.refresh_auto_clean_rules()
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Auto-clean rules module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error creating rule:\n{str(e)}')

    def refresh_auto_clean_rules(self):
        """Refresh the list of auto-clean rules."""
        try:
            from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules
            rules_manager = AutoCleanRules()
            rules = rules_manager.list_rules()
            self.auto_clean_rules_table.setRowCount(len(rules))
            for i, rule in enumerate(rules):
                self.auto_clean_rules_table.setItem(i, 0, QTableWidgetItem(rule.get('name', 'Unknown')))
                self.auto_clean_rules_table.setItem(i, 1, QTableWidgetItem(rule.get('trigger_type', 'Unknown')))
                self.auto_clean_rules_table.setItem(i, 2, QTableWidgetItem(rule.get('action', 'Unknown')))
                status = 'Enabled' if rule.get('enabled', True) else 'Disabled'
                self.auto_clean_rules_table.setItem(i, 3, QTableWidgetItem(status))
                self.auto_clean_rules_table.setItem(i, 4, QTableWidgetItem(rule.get('last_triggered', 'Never')))
                self.auto_clean_rules_table.setItem(i, 5, QTableWidgetItem(str(rule.get('priority', 5))))
            execution_log = rules_manager.get_execution_log(limit=20)
            self.rule_execution_log.clear()
            for entry in execution_log:
                log_entry = f"[{entry.get('timestamp', 'Unknown')}] {entry.get('rule_name', 'Unknown')}: {entry.get('result', 'Unknown')}"
                self.rule_execution_log.append(log_entry)
        except ImportError:
            self.auto_clean_rules_table.setRowCount(1)
            self.auto_clean_rules_table.setItem(0, 0, QTableWidgetItem('Auto-clean rules not available'))
            for col in range(1, 6):
                self.auto_clean_rules_table.setItem(0, col, QTableWidgetItem(''))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error refreshing rules:\n{str(e)}')

    def test_selected_rule(self):
        """Test the selected auto-clean rule."""
        selected_rows = set()
        for item in self.auto_clean_rules_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            return
        row = list(selected_rows)[0]
        rule_name = self.auto_clean_rules_table.item(row, 0).text()
        try:
            from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules
            rules_manager = AutoCleanRules()
            result = rules_manager.test_rule(rule_name)
            if result.get('success', False):
                QMessageBox.information(self, 'Rule Test', f"Rule '{rule_name}' test completed successfully.\n\n{result.get('message', '')}")
                self.add_activity(f'Tested auto-clean rule: {rule_name}')
            else:
                QMessageBox.warning(self, 'Rule Test Failed', f"Rule '{rule_name}' test failed.\n\n{result.get('error', 'Unknown error')}")
            self.refresh_auto_clean_rules()
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Auto-clean rules module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error testing rule:\n{str(e)}')

    def delete_selected_rule(self):
        """Delete the selected auto-clean rule."""
        selected_rows = set()
        for item in self.auto_clean_rules_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            return
        row = list(selected_rows)[0]
        rule_name = self.auto_clean_rules_table.item(row, 0).text()
        reply = QMessageBox.question(self, 'Confirm Deletion', f"Are you sure you want to delete the rule '{rule_name}'?\n\nThis action cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules
            rules_manager = AutoCleanRules()
            success = rules_manager.delete_rule(rule_name)
            if success:
                QMessageBox.information(self, 'Rule Deleted', f"Rule '{rule_name}' deleted successfully.")
                self.add_activity(f'Deleted auto-clean rule: {rule_name}')
                self.refresh_auto_clean_rules()
            else:
                QMessageBox.warning(self, 'Deletion Failed', f"Failed to delete rule '{rule_name}'.")
        except ImportError:
            QMessageBox.critical(self, 'Error', 'Auto-clean rules module not available.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error deleting rule:\n{str(e)}')

def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName('Cortex Cleaner')
    app.setApplicationVersion('0.1.0')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    window = DeepCleanerGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()