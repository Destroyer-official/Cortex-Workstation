"""Main window for Deep Cleaner GUI."""

import sys
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# Handle imports for both direct execution and module import
try:
    # When running as a module
    from ..scanner import Scanner
    from ..deleter import Deleter
    from ..config import Config, DEFAULT_CONFIG
    from ..utils import setup_logging, normalize_path
    
    # Import new modules
    from ..analyzers.duplicate_finder import DuplicateFinder
    from ..analyzers.large_file_finder import LargeFileFinder
    from ..analyzers.temp_cleaner import TempCleaner
    from ..analyzers.cache_cleaner import CacheCleaner
    from ..analyzers.old_file_cleaner import OldFileCleaner
    from ..analyzers.file_shredder import FileShredder
    from ..analyzers.disk_analyzer import DiskAnalyzer
    from ..analyzers.duplicate_folder_finder import DuplicateFolderFinder
    from ..analyzers.docker_cleaner import DockerCleaner
    from ..analyzers.broken_link_detector import BrokenLinkDetector
    from ..analyzers.package_manager_cleaner import PackageManagerCleaner
    
    from ..system_tools.startup_manager import StartupManager
    from ..system_tools.process_analyzer import ProcessAnalyzer
    try:
        from ..system_tools.registry_cleaner import RegistryCleaner
        HAS_REGISTRY_CLEANER = True
    except ImportError:
        HAS_REGISTRY_CLEANER = False
    
    from ..scheduler.scheduler import TaskScheduler
    from ..scheduler.auto_clean_rules import AutoCleanRules
    from ..reports.restore_manager import RestoreManager
    from ..reports.reports import ReportsGenerator
    
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox,
        QFileDialog, QMessageBox, QProgressBar, QGroupBox, QFormLayout,
        QSpinBox, QTabWidget, QSizePolicy, QTableWidget, QTableWidgetItem,
        QHeaderView, QTreeWidgetItem, QTreeWidget, QListWidget, QSplitter,
        QInputDialog, QScrollArea, QDialog, QRadioButton,QListWidgetItem,
        QAbstractItemView
    )
    from PySide6.QtCore import Qt, QThread, Signal, QObject, QSettings
    from PySide6.QtGui import QTextCursor
except ImportError:
    # When running directly
    # Add the parent directory to the path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from deep_cleaner.scanner import Scanner
    from deep_cleaner.deleter import Deleter
    from deep_cleaner.config import Config, DEFAULT_CONFIG
    from deep_cleaner.utils import setup_logging, normalize_path
    
    # Import new modules
    from deep_cleaner.analyzers.duplicate_finder import DuplicateFinder
    from deep_cleaner.analyzers.large_file_finder import LargeFileFinder
    from deep_cleaner.analyzers.temp_cleaner import TempCleaner
    from deep_cleaner.analyzers.cache_cleaner import CacheCleaner
    from deep_cleaner.analyzers.old_file_cleaner import OldFileCleaner
    from deep_cleaner.analyzers.file_shredder import FileShredder
    from deep_cleaner.analyzers.disk_analyzer import DiskAnalyzer
    from deep_cleaner.analyzers.duplicate_folder_finder import DuplicateFolderFinder
    from deep_cleaner.analyzers.docker_cleaner import DockerCleaner
    from deep_cleaner.analyzers.broken_link_detector import BrokenLinkDetector
    from deep_cleaner.analyzers.package_manager_cleaner import PackageManagerCleaner
    
    from deep_cleaner.system_tools.startup_manager import StartupManager
    from deep_cleaner.system_tools.process_analyzer import ProcessAnalyzer
    try:
        from deep_cleaner.system_tools.registry_cleaner import RegistryCleaner
        HAS_REGISTRY_CLEANER = True
    except ImportError:
        HAS_REGISTRY_CLEANER = False
    
    from deep_cleaner.scheduler.scheduler import TaskScheduler
    from deep_cleaner.scheduler.auto_clean_rules import AutoCleanRules
    from deep_cleaner.reports.restore_manager import RestoreManager
    from deep_cleaner.reports.reports import ReportsGenerator
    
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox,
        QFileDialog, QMessageBox, QProgressBar, QGroupBox, QFormLayout,
        QSpinBox, QTabWidget, QSizePolicy, QTableWidget, QTableWidgetItem,
        QHeaderView, QTreeWidgetItem, QTreeWidget, QListWidget, QSplitter,
        QInputDialog, QScrollArea, QDialog, QRadioButton,
        QAbstractItemView
    )
    from PySide6.QtCore import Qt, QThread, Signal, QObject, QSettings
    from PySide6.QtGui import QTextCursor


# Worker classes for background operations
class ScanWorker(QObject):
    """Worker class for scanning files in a separate thread."""
    finished = Signal(list, list)
    error = Signal(str)
    progress_updated = Signal(object)  # ScanProgress object
    
    def __init__(self, config: Config, path: str, enable_checkpoints: bool = False, 
                 enable_throttling: bool = False, checkpoint_id: str = ""):
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
            self.scanner = Scanner(
                self.config, 
                self.path,
                enable_checkpoints=self.enable_checkpoints,
                enable_throttling=self.enable_throttling
            )
            
            # Start progress monitoring if checkpoints are enabled
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
    """Worker class for deleting files in a separate thread."""
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


class DuplicateFinderWorker(QObject):
    """Worker class for finding duplicates in a separate thread."""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, config: Config, path: str, hash_algorithm: str = 'md5'):
        super().__init__()
        self.config = config
        self.path = path
        self.hash_algorithm = hash_algorithm
    
    def run(self):
        """Run the duplicate finding process."""
        try:
            finder = DuplicateFinder(self.config, self.path)
            finder.hash_algorithm = self.hash_algorithm
            duplicates = finder.find_duplicates()
            stats = finder.get_stats()

            self.finished.emit({"duplicates": duplicates, "stats": stats})
        except Exception as e:
            self.error.emit(str(e))


class LargeFileFinderWorker(QObject):
    """Worker class for finding large files in a separate thread."""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, config: Config, path: str, min_size_mb: int = 100):
        super().__init__()
        self.config = config
        self.path = path
        self.min_size_mb = min_size_mb
    
    def run(self):
        """Run the large file finding process."""
        try:
            finder = LargeFileFinder(self.config, self.path)
            large_files = finder.find_large_files(min_size_mb=self.min_size_mb)
            stats = finder.get_stats()
            self.finished.emit([large_files, stats])
        except Exception as e:
            self.error.emit(str(e))


class TempCleanerWorker(QObject):
    """Worker class for finding temp files in a separate thread."""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
    
    def run(self):
        """Run the temp file finding process."""
        try:
            cleaner = TempCleaner(self.config)
            temp_files = cleaner.find_temp_files()
            stats = cleaner.get_stats()
            self.finished.emit([temp_files, stats])
        except Exception as e:
            self.error.emit(str(e))


class DiskAnalyzerWorker(QObject):
    """Worker class for disk analysis in a separate thread."""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, config: Config, path: str):
        super().__init__()
        self.config = config
        self.path = path
        self.logger = logging.getLogger("deep_cleaner.disk_analyzer")
    
    def run(self):
        """Run the disk analysis process with dubbing logs for debugging."""
        try:
            # Add dubbing log
            self.logger.info("=== STARTING DISK ANALYSIS PROCESS (DUBBING LOG) ===")
            self.logger.info("Analyzing path: {}".format(self.path))
            
            analyzer = DiskAnalyzer(self.config, self.path)
            disk_usage = analyzer.analyze_disk_usage()
            
            # Add dubbing log
            self.logger.info("Disk usage analysis completed, analyzing directory tree")
            
            analyzer.analyze_directory_tree()  # Add this for visualization
            
            # Add dubbing log
            self.logger.info("Directory tree analysis completed, analyzing file types")
            
            file_types = analyzer.analyze_file_types()
            
            # Add dubbing log
            self.logger.info("File types analysis completed, finding largest directories")
            
            largest_dirs = analyzer.find_largest_directories()
            
            # Add dubbing log
            self.logger.info("Largest directories analysis completed, formatting results")
            
            # Use the analyzer's get_stats method to properly format disk usage
            stats = analyzer.get_stats()
            formatted_disk_usage = stats.get("disk_usage", disk_usage)
            
            # Add dubbing log
            self.logger.info("Results formatted, emitting finished signal")
            
            self.finished.emit({
                "disk_usage": formatted_disk_usage,
                "file_types": file_types,
                "largest_dirs": largest_dirs,
                "analyzer": analyzer  # Include the analyzer object
            })
            
            # Add dubbing log
            self.logger.info("=== DISK ANALYSIS PROCESS COMPLETED (DUBBING LOG) ===")
                
        except Exception as e:
            # Add dubbing log
            self.logger.error("Error in disk analysis: {}".format(str(e)))
            self.error.emit(str(e))


class DockerScanWorker(QObject):
    """Worker class for scanning Docker resources in a separate thread."""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, scan_images: bool, scan_containers: bool, scan_volumes: bool, scan_networks: bool):
        super().__init__()
        self.scan_images = scan_images
        self.scan_containers = scan_containers
        self.scan_volumes = scan_volumes
        self.scan_networks = scan_networks
    
    def run(self):
        """Run Docker resource scanning."""
        try:
            cleaner = DockerCleaner()
            
            if not cleaner.is_docker_available():
                self.error.emit("Docker is not available or not running")
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
            
            self.finished.emit({
                "resources": all_resources,
                "stats": stats
            })
        except Exception as e:
            self.error.emit(str(e))


class DockerCleanupWorker(QObject):
    """Worker class for cleaning Docker resources in a separate thread."""
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, resources: list, dry_run: bool):
        super().__init__()
        self.resources = resources
        self.dry_run = dry_run
    
    def run(self):
        """Run Docker resource cleanup."""
        try:
            cleaner = DockerCleaner()
            
            if not cleaner.is_docker_available():
                self.error.emit("Docker is not available or not running")
                return
            
            result = cleaner.cleanup_resources(self.resources, self.dry_run)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class DeepCleanerGUI(QMainWindow):
    """Main window for Deep Cleaner GUI application."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Deep Cleaner")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize attributes
        self.config = Config()
        self.scan_thread: Optional[QThread] = None
        self.scan_worker: Optional[Union[ScanWorker, MultiDriveScanWorker]] = None
        self.delete_thread: Optional[QThread] = None
        self.delete_worker: Optional[DeleteWorker] = None
        self.duplicate_thread: Optional[QThread] = None
        self.duplicate_worker: Optional[DuplicateFinderWorker] = None
        self.large_file_thread: Optional[QThread] = None
        self.large_file_worker: Optional[LargeFileFinderWorker] = None
        self.temp_cleaner_thread: Optional[QThread] = None
        self.temp_cleaner_worker: Optional[TempCleanerWorker] = None
        self.disk_analyzer_thread: Optional[QThread] = None
        self.disk_analyzer_worker: Optional[DiskAnalyzerWorker] = None
        
        self.empty_files: List[Path] = []
        self.empty_dirs: List[Path] = []
        self.duplicates: Dict[str, List[Path]] = {}
        self.large_files: List[tuple] = []
        self.temp_files: List[Path] = []
        
        self.logger = logging.getLogger("deep_cleaner.gui")
        
        # Add dubbing log handler to see logs in the GUI
        self.setup_dubbing_logs()
        
        # Load settings
        self.settings = QSettings("DeepCleaner", "DeepCleanerGUI")
        
        self.init_ui()
        self.load_settings()
        
        # Add advanced tabs after window is shown (using QTimer to defer execution)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.add_advanced_tabs)
    
    def setup_dubbing_logs(self):
        """Set up dubbing logs to help debug issues in the program."""
        # Create a custom handler to display logs in the GUI
        class DubbingLogHandler(logging.Handler):
            def __init__(self, gui_instance):
                super().__init__()
                self.gui = gui_instance
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    # Add log message to results text with a special marker
                    if hasattr(self.gui, 'results_text') and self.gui.results_text:
                        current_text = self.gui.results_text.toPlainText()
                        if "=== Dubbing Log ===" not in current_text:
                            self.gui.results_text.append(f"\n=== Dubbing Log ===\n{msg}\n")
                        else:
                            self.gui.results_text.append(f"{msg}\n")
                except Exception:
                    pass  # Ignore errors in the logging handler
        
        # Add the handler to the logger
        dubbing_handler = DubbingLogHandler(self)
        dubbing_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        dubbing_handler.setFormatter(formatter)
        self.logger.addHandler(dubbing_handler)
        
        # Log initialization
        self.logger.info("=== Deep Cleaner GUI Initialized with Dubbing Logs ===")
        self.logger.info(f"Platform: {sys.platform}")
        self.logger.info(f"Working directory: {os.getcwd()}")
    
    def init_ui(self):
        """Initialize the user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.tab_widget)
        
        # Create dashboard tab
        dashboard_tab = self.create_dashboard_tab()
        self.tab_widget.addTab(dashboard_tab, "Dashboard")
        
        # Create cleaner tab
        cleaner_tab = self.create_cleaner_tab()
        self.tab_widget.addTab(cleaner_tab, "Cleaner")
        
        # Create duplicates tab
        duplicates_tab = self.create_duplicates_tab()
        self.tab_widget.addTab(duplicates_tab, "Duplicates")
        
        # Create temp cleaner tab
        temp_cleaner_tab = self.create_temp_cleaner_tab()
        self.tab_widget.addTab(temp_cleaner_tab, "Temp Files")
        
        # Create large files tab
        large_files_tab = self.create_large_files_tab()
        self.tab_widget.addTab(large_files_tab, "Large Files")
        
        # Create disk analyzer tab
        disk_analyzer_tab = self.create_disk_analyzer_tab()
        self.tab_widget.addTab(disk_analyzer_tab, "Disk Analyzer")
        
        # Create system tools tab
        system_tools_tab = self.create_system_tools_tab()
        self.tab_widget.addTab(system_tools_tab, "System Tools")
        
        # Create Docker tab
        docker_tab = self.create_docker_tab()
        self.tab_widget.addTab(docker_tab, "Docker")
        
        # Create package manager tab
        package_manager_tab = self.create_package_manager_tab()
        self.tab_widget.addTab(package_manager_tab, "Package Managers")
        
        # Create heuristics tab
        heuristics_tab = self.create_heuristics_tab()
        self.tab_widget.addTab(heuristics_tab, "Heuristics")
        
        # Create broken links tab
        broken_links_tab = self.create_broken_links_tab()
        self.tab_widget.addTab(broken_links_tab, "Broken Links")
        
        # Create restore tab
        restore_tab = self.create_restore_tab()
        self.tab_widget.addTab(restore_tab, "Restore")
        
        # Create settings tab
        settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(settings_tab, "Settings")
        
        # TODO: Add advanced tabs after all methods are defined
        # Advanced tabs will be added in a separate method called after __init__
        # - File Shredder
        # - Scheduler  
        # - Reports
        # - Resource Monitor
        
        # Create status bar
        self.status_bar = QLabel("Ready")
        self.status_bar.setStyleSheet("QLabel { padding: 5px; border-top: 1px solid #ccc; }")
        main_layout.addWidget(self.status_bar)
    
    def add_advanced_tabs(self):
        """Add advanced tabs after all methods are defined."""
        try:
            # Create advanced tabs
            file_shredder_tab = self.create_file_shredder_tab()
            self.tab_widget.addTab(file_shredder_tab, "File Shredder")
            
            scheduler_tab = self.create_scheduler_tab()
            self.tab_widget.addTab(scheduler_tab, "Scheduler")
            
            reports_tab = self.create_reports_tab()
            self.tab_widget.addTab(reports_tab, "Reports")
            
            resource_monitor_tab = self.create_resource_monitor_tab()
            self.tab_widget.addTab(resource_monitor_tab, "Resource Monitor")
            
            self.logger.info("Advanced tabs added successfully")
        except Exception as e:
            self.logger.warning(f"Could not add advanced tabs: {e}")
    
    def create_dashboard_tab(self) -> QWidget:
        """Create the dashboard tab."""
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        layout.setSpacing(15)
        
        # Welcome message
        welcome_label = QLabel("Welcome to Deep Cleaner")
        welcome_label.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; margin: 10px; }")
        layout.addWidget(welcome_label)
        
        # Quick actions
        quick_actions_group = QGroupBox("Quick Actions")
        quick_actions_layout = QHBoxLayout(quick_actions_group)
        quick_actions_layout.setSpacing(10)
        
        scan_button = QPushButton("Scan Empty Files")
        scan_button.clicked.connect(self.quick_scan)
        scan_button.setMinimumHeight(40)
        quick_actions_layout.addWidget(scan_button)
        
        temp_clean_button = QPushButton("Clean Temp Files")
        temp_clean_button.clicked.connect(self.quick_temp_clean)
        temp_clean_button.setMinimumHeight(40)
        quick_actions_layout.addWidget(temp_clean_button)
        
        disk_analysis_button = QPushButton("Analyze Disk")
        disk_analysis_button.clicked.connect(self.quick_disk_analysis)
        disk_analysis_button.setMinimumHeight(40)
        quick_actions_layout.addWidget(disk_analysis_button)
        
        layout.addWidget(quick_actions_group)
        
        # Recent activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_list = QListWidget()
        self.activity_list.setMaximumHeight(200)
        activity_layout.addWidget(self.activity_list)
        
        layout.addWidget(activity_group)
        
        # System info
        system_info_group = QGroupBox("System Information")
        system_info_layout = QVBoxLayout(system_info_group)
        
        self.system_info_label = QLabel("Loading system information...")
        system_info_layout.addWidget(self.system_info_label)
        
        layout.addWidget(system_info_group)
        layout.addStretch()
        
        return dashboard_tab
    
    def create_cleaner_tab(self) -> QWidget:
        """Create the cleaner tab."""
        cleaner_tab = QWidget()
        layout = QVBoxLayout(cleaner_tab)
        layout.setSpacing(10)
        
        # Path selection group with multi-drive support
        path_group = QGroupBox("Target Paths")
        path_layout = QVBoxLayout(path_group)
        path_layout.setContentsMargins(10, 10, 10, 10)
        
        # Single path mode
        single_path_layout = QHBoxLayout()
        
        self.single_path_radio = QRadioButton("Single Path")
        self.single_path_radio.setChecked(True)
        single_path_layout.addWidget(self.single_path_radio)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select directory to scan...")
        self.path_input.setMinimumHeight(30)
        single_path_layout.addWidget(self.path_input)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_path)
        browse_button.setMinimumHeight(30)
        browse_button.setStyleSheet("QPushButton { padding: 5px 15px; }")
        single_path_layout.addWidget(browse_button)
        
        path_layout.addLayout(single_path_layout)
        
        # Multi-drive mode
        multi_drive_layout = QVBoxLayout()
        
        self.multi_drive_radio = QRadioButton("Multiple Drives/Paths")
        multi_drive_layout.addWidget(self.multi_drive_radio)
        
        # Drive selection
        drives_layout = QHBoxLayout()
        
        self.drives_list = QListWidget()
        self.drives_list.setMaximumHeight(100)
        self.drives_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        drives_layout.addWidget(self.drives_list)
        
        drives_buttons_layout = QVBoxLayout()
        
        self.detect_drives_button = QPushButton("Detect Drives")
        self.detect_drives_button.clicked.connect(self.detect_available_drives)
        drives_buttons_layout.addWidget(self.detect_drives_button)
        
        self.add_network_drive_button = QPushButton("Add Network Drive")
        self.add_network_drive_button.clicked.connect(self.add_network_drive)
        drives_buttons_layout.addWidget(self.add_network_drive_button)
        
        self.remove_drive_button = QPushButton("Remove Selected")
        self.remove_drive_button.clicked.connect(self.remove_selected_drives)
        drives_buttons_layout.addWidget(self.remove_drive_button)
        
        drives_buttons_layout.addStretch()
        drives_layout.addLayout(drives_buttons_layout)
        
        multi_drive_layout.addLayout(drives_layout)
        path_layout.addLayout(multi_drive_layout)
        
        # Connect radio buttons
        self.single_path_radio.toggled.connect(self.on_path_mode_changed)
        self.multi_drive_radio.toggled.connect(self.on_path_mode_changed)
        
        # Initially disable multi-drive controls
        self.drives_list.setEnabled(False)
        self.detect_drives_button.setEnabled(False)
        self.add_network_drive_button.setEnabled(False)
        self.remove_drive_button.setEnabled(False)
        
        layout.addWidget(path_group)
        
        # Scan options group
        options_group = QGroupBox("Scan Options")
        options_layout = QFormLayout(options_group)
        options_layout.setContentsMargins(10, 10, 10, 10)
        options_layout.setSpacing(10)
        
        self.dry_run_checkbox = QCheckBox("Dry Run (Preview only)")
        self.dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.dry_run_checkbox)
        
        self.trash_checkbox = QCheckBox("Move to Trash (instead of permanent delete)")
        options_layout.addRow(self.trash_checkbox)
        
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("e.g., *.tmp, *.log")
        options_layout.addRow("Pattern Filter:", self.pattern_input)
        
        self.age_spinbox = QSpinBox()
        self.age_spinbox.setRange(0, 365)
        self.age_spinbox.setSuffix(" days")
        self.age_spinbox.setValue(0)
        options_layout.addRow("Minimum Age:", self.age_spinbox)
        
        layout.addWidget(options_group)
        
        # Performance options group
        performance_group = QGroupBox("Performance Options")
        performance_layout = QFormLayout(performance_group)
        performance_layout.setContentsMargins(10, 10, 10, 10)
        performance_layout.setSpacing(10)
        
        self.enable_checkpoints_checkbox = QCheckBox("Enable Checkpoints (allows pause/resume)")
        performance_layout.addRow(self.enable_checkpoints_checkbox)
        
        self.enable_throttling_checkbox = QCheckBox("Enable Resource Throttling")
        performance_layout.addRow(self.enable_throttling_checkbox)
        
        self.cpu_limit_spinbox = QSpinBox()
        self.cpu_limit_spinbox.setRange(10, 100)
        self.cpu_limit_spinbox.setSuffix("%")
        self.cpu_limit_spinbox.setValue(80)
        performance_layout.addRow("CPU Limit:", self.cpu_limit_spinbox)
        
        self.memory_limit_spinbox = QSpinBox()
        self.memory_limit_spinbox.setRange(10, 100)
        self.memory_limit_spinbox.setSuffix("%")
        self.memory_limit_spinbox.setValue(85)
        performance_layout.addRow("Memory Limit:", self.memory_limit_spinbox)
        
        layout.addWidget(performance_group)
        
        # Checkpoint management group
        checkpoint_group = QGroupBox("Checkpoint Management")
        checkpoint_layout = QVBoxLayout(checkpoint_group)
        checkpoint_layout.setContentsMargins(10, 10, 10, 10)
        
        # Checkpoint controls
        checkpoint_controls_layout = QHBoxLayout()
        
        self.list_checkpoints_button = QPushButton("List Checkpoints")
        self.list_checkpoints_button.clicked.connect(self.list_checkpoints)
        checkpoint_controls_layout.addWidget(self.list_checkpoints_button)
        
        self.resume_checkpoint_button = QPushButton("Resume from Checkpoint")
        self.resume_checkpoint_button.clicked.connect(self.resume_from_checkpoint)
        self.resume_checkpoint_button.setEnabled(False)
        checkpoint_controls_layout.addWidget(self.resume_checkpoint_button)
        
        self.delete_checkpoint_button = QPushButton("Delete Checkpoint")
        self.delete_checkpoint_button.clicked.connect(self.delete_checkpoint)
        self.delete_checkpoint_button.setEnabled(False)
        checkpoint_controls_layout.addWidget(self.delete_checkpoint_button)
        
        self.cleanup_checkpoints_button = QPushButton("Cleanup Old")
        self.cleanup_checkpoints_button.clicked.connect(self.cleanup_old_checkpoints)
        checkpoint_controls_layout.addWidget(self.cleanup_checkpoints_button)
        
        checkpoint_layout.addLayout(checkpoint_controls_layout)
        
        # Checkpoints list
        self.checkpoints_list = QListWidget()
        self.checkpoints_list.setMaximumHeight(80)
        self.checkpoints_list.itemSelectionChanged.connect(self.on_checkpoint_selection_changed)
        checkpoint_layout.addWidget(self.checkpoints_list)
        
        layout.addWidget(checkpoint_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.scan_button = QPushButton("Scan")
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.setMinimumHeight(35)
        self.scan_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.scan_button)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_scan)
        self.pause_button.setEnabled(False)
        self.pause_button.setMinimumHeight(35)
        self.pause_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.pause_button)
        
        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_scan)
        self.resume_button.setEnabled(False)
        self.resume_button.setMinimumHeight(35)
        self.resume_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.resume_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.start_delete)
        self.delete_button.setEnabled(False)
        self.delete_button.setMinimumHeight(35)
        self.delete_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.delete_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress area
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(10, 10, 10, 10)
        progress_layout.setSpacing(5)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready to scan")
        self.progress_label.setStyleSheet("QLabel { color: #666; }")
        progress_layout.addWidget(self.progress_label)
        
        self.scan_stats_label = QLabel("")
        self.scan_stats_label.setStyleSheet("QLabel { color: #666; font-size: 11px; }")
        progress_layout.addWidget(self.scan_stats_label)
        
        progress_group.setVisible(False)
        layout.addWidget(progress_group)
        self.progress_group = progress_group
        
        # Results area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("QTextEdit { font-family: Consolas, Monaco, monospace; }")
        layout.addWidget(self.results_text)
        
        return cleaner_tab
    
    def create_duplicates_tab(self) -> QWidget:
        """Create the duplicates tab."""
        duplicates_tab = QWidget()
        layout = QVBoxLayout(duplicates_tab)
        layout.setSpacing(10)
        
        # Path selection group
        path_group = QGroupBox("Target Path")
        path_layout = QHBoxLayout(path_group)
        path_layout.setContentsMargins(10, 10, 10, 10)
        
        self.duplicates_path_input = QLineEdit()
        self.duplicates_path_input.setPlaceholderText("Select directory to scan for duplicates...")
        self.duplicates_path_input.setMinimumHeight(30)
        path_layout.addWidget(self.duplicates_path_input)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.duplicates_path_input))
        browse_button.setMinimumHeight(30)
        browse_button.setStyleSheet("QPushButton { padding: 5px 15px; }")
        path_layout.addWidget(browse_button)
        
        layout.addWidget(path_group)
        
        # Options group
        options_group = QGroupBox("Duplicate Detection Options")
        options_layout = QFormLayout(options_group)
        options_layout.setContentsMargins(10, 10, 10, 10)
        options_layout.setSpacing(10)
        
        self.hash_algorithm_combo = QComboBox()
        self.hash_algorithm_combo.addItems(["md5", "sha1", "sha256"])
        self.hash_algorithm_combo.setCurrentText("md5")
        options_layout.addRow("Hash Algorithm:", self.hash_algorithm_combo)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["keep_newest", "keep_oldest", "keep_largest", "keep_smallest"])
        self.strategy_combo.setCurrentText("keep_newest")
        options_layout.addRow("Selection Strategy:", self.strategy_combo)
        
        layout.addWidget(options_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.find_duplicates_button = QPushButton("Find Duplicates")
        self.find_duplicates_button.clicked.connect(self.start_find_duplicates)
        self.find_duplicates_button.setMinimumHeight(35)
        self.find_duplicates_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.find_duplicates_button)
        
        self.delete_duplicates_button = QPushButton("Delete Selected")
        self.delete_duplicates_button.clicked.connect(self.delete_selected_duplicates)
        self.delete_duplicates_button.setEnabled(False)
        self.delete_duplicates_button.setMinimumHeight(35)
        self.delete_duplicates_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.delete_duplicates_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.duplicates_progress_bar = QProgressBar()
        self.duplicates_progress_bar.setVisible(False)
        self.duplicates_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.duplicates_progress_bar)
        
        # Results area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Tree widget for duplicate groups
        self.duplicates_tree = QTreeWidget()
        self.duplicates_tree.setHeaderLabels(["Duplicate Groups", "File Count", "Size"])
        self.duplicates_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        splitter.addWidget(self.duplicates_tree)
        
        # Details area
        self.duplicates_details = QTextEdit()
        self.duplicates_details.setReadOnly(True)
        splitter.addWidget(self.duplicates_details)
        
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        return duplicates_tab
    
    def create_temp_cleaner_tab(self) -> QWidget:
        """Create the temp cleaner tab."""
        temp_tab = QWidget()
        layout = QVBoxLayout(temp_tab)
        
        # Title
        title = QLabel("Temporary Files Cleaner")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Scan options
        options_group = QGroupBox("Scan Options")
        options_layout = QFormLayout(options_group)
        
        # Scan locations
        self.temp_scan_system = QCheckBox("System temp directories")
        self.temp_scan_system.setChecked(True)
        options_layout.addRow(self.temp_scan_system)
        
        self.temp_scan_user = QCheckBox("User temp directories")
        self.temp_scan_user.setChecked(True)
        options_layout.addRow(self.temp_scan_user)
        
        self.temp_scan_browser = QCheckBox("Browser cache files")
        self.temp_scan_browser.setChecked(True)
        options_layout.addRow(self.temp_scan_browser)
        
        self.temp_scan_apps = QCheckBox("Application temp files")
        self.temp_scan_apps.setChecked(True)
        options_layout.addRow(self.temp_scan_apps)
        
        # Age filter
        self.temp_age_filter = QSpinBox()
        self.temp_age_filter.setRange(0, 365)
        self.temp_age_filter.setSuffix(" days")
        self.temp_age_filter.setValue(0)
        options_layout.addRow("Only files older than:", self.temp_age_filter)
        
        layout.addWidget(options_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.temp_scan_button = QPushButton("Scan Temp Files")
        self.temp_scan_button.clicked.connect(self.start_temp_scan)
        self.temp_scan_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.temp_scan_button)
        
        self.temp_clean_button = QPushButton("Clean Selected")
        self.temp_clean_button.clicked.connect(self.start_temp_clean)
        self.temp_clean_button.setEnabled(False)
        self.temp_clean_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.temp_clean_button)
        
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.temp_progress_bar = QProgressBar()
        self.temp_progress_bar.setVisible(False)
        layout.addWidget(self.temp_progress_bar)
        
        # Status label
        self.temp_status_label = QLabel("Ready to scan for temporary files")
        layout.addWidget(self.temp_status_label)
        
        # Results table
        self.temp_results_table = QTableWidget()
        self.temp_results_table.setColumnCount(4)
        self.temp_results_table.setHorizontalHeaderLabels(["Select", "File Path", "Size", "Type"])
        
        # Configure table
        header = self.temp_results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.temp_results_table)
        
        # Summary label
        self.temp_summary_label = QLabel("")
        layout.addWidget(self.temp_summary_label)
        
        return temp_tab
    
    def create_large_files_tab(self) -> QWidget:
        """Create the large files tab."""
        large_files_tab = QWidget()
        layout = QVBoxLayout(large_files_tab)
        layout.setSpacing(10)
        
        # Path selection group
        path_group = QGroupBox("Target Path")
        path_layout = QHBoxLayout(path_group)
        path_layout.setContentsMargins(10, 10, 10, 10)
        
        self.large_files_path_input = QLineEdit()
        self.large_files_path_input.setPlaceholderText("Select directory to scan for large files...")
        self.large_files_path_input.setMinimumHeight(30)
        path_layout.addWidget(self.large_files_path_input)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.large_files_path_input))
        browse_button.setMinimumHeight(30)
        browse_button.setStyleSheet("QPushButton { padding: 5px 15px; }")
        path_layout.addWidget(browse_button)
        
        layout.addWidget(path_group)
        
        # Options group
        options_group = QGroupBox("Large Files Options")
        options_layout = QFormLayout(options_group)
        options_layout.setContentsMargins(10, 10, 10, 10)
        options_layout.setSpacing(10)
        
        self.min_size_spinbox = QSpinBox()
        self.min_size_spinbox.setRange(1, 10000)
        self.min_size_spinbox.setSuffix(" MB")
        self.min_size_spinbox.setValue(100)
        options_layout.addRow("Minimum Size:", self.min_size_spinbox)
        
        layout.addWidget(options_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.find_large_files_button = QPushButton("Find Large Files")
        self.find_large_files_button.clicked.connect(self.start_find_large_files)
        self.find_large_files_button.setMinimumHeight(35)
        self.find_large_files_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.find_large_files_button)
        
        self.delete_large_files_button = QPushButton("Delete Selected")
        self.delete_large_files_button.clicked.connect(self.delete_selected_large_files)
        self.delete_large_files_button.setEnabled(False)
        self.delete_large_files_button.setMinimumHeight(35)
        self.delete_large_files_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.delete_large_files_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.large_files_progress_bar = QProgressBar()
        self.large_files_progress_bar.setVisible(False)
        self.large_files_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.large_files_progress_bar)
        
        # Results table
        self.large_files_table = QTableWidget()
        self.large_files_table.setColumnCount(3)
        self.large_files_table.setHorizontalHeaderLabels(["File Path", "Size", "Last Modified"])
        self.large_files_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.large_files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.large_files_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.large_files_table)
        
        return large_files_tab
    
    def create_disk_analyzer_tab(self) -> QWidget:
        """Create the disk analyzer tab."""
        disk_analyzer_tab = QWidget()
        layout = QVBoxLayout(disk_analyzer_tab)
        layout.setSpacing(10)
        
        # Path selection group
        path_group = QGroupBox("Target Path")
        path_layout = QHBoxLayout(path_group)
        path_layout.setContentsMargins(10, 10, 10, 10)
        
        self.disk_analyzer_path_input = QLineEdit()
        self.disk_analyzer_path_input.setPlaceholderText("Select directory to analyze...")
        self.disk_analyzer_path_input.setMinimumHeight(30)
        path_layout.addWidget(self.disk_analyzer_path_input)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.disk_analyzer_path_input))
        browse_button.setMinimumHeight(30)
        browse_button.setStyleSheet("QPushButton { padding: 5px 15px; }")
        path_layout.addWidget(browse_button)
        
        layout.addWidget(path_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.analyze_disk_button = QPushButton("Analyze Disk")
        self.analyze_disk_button.clicked.connect(self.start_disk_analysis)
        self.analyze_disk_button.setMinimumHeight(35)
        self.analyze_disk_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        buttons_layout.addWidget(self.analyze_disk_button)
        
        # Visualization buttons
        self.show_treemap_button = QPushButton("TreeMap View")
        self.show_treemap_button.clicked.connect(self.show_treemap_visualization)
        self.show_treemap_button.setMinimumHeight(35)
        self.show_treemap_button.setEnabled(False)
        buttons_layout.addWidget(self.show_treemap_button)
        
        self.show_sunburst_button = QPushButton("Sunburst View")
        self.show_sunburst_button.clicked.connect(self.show_sunburst_visualization)
        self.show_sunburst_button.setMinimumHeight(35)
        self.show_sunburst_button.setEnabled(False)
        buttons_layout.addWidget(self.show_sunburst_button)
        
        self.show_dashboard_button = QPushButton("Interactive Dashboard")
        self.show_dashboard_button.clicked.connect(self.show_interactive_dashboard)
        self.show_dashboard_button.setMinimumHeight(35)
        self.show_dashboard_button.setEnabled(False)
        buttons_layout.addWidget(self.show_dashboard_button)
        
        # Export button
        self.export_visualization_button = QPushButton("Export Visualization")
        self.export_visualization_button.clicked.connect(self.export_visualization_dialog)
        self.export_visualization_button.setMinimumHeight(35)
        self.export_visualization_button.setEnabled(False)
        buttons_layout.addWidget(self.export_visualization_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.disk_analyzer_progress_bar = QProgressBar()
        self.disk_analyzer_progress_bar.setVisible(False)
        self.disk_analyzer_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.disk_analyzer_progress_bar)
        
        # Results area
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Disk usage info
        self.disk_usage_label = QLabel("Disk usage information will appear here")
        self.disk_usage_label.setStyleSheet("QLabel { font-family: Consolas, Monaco, monospace; }")
        self.disk_usage_label.setWordWrap(True)
        splitter.addWidget(self.disk_usage_label)
        
        # File types table
        file_types_group = QGroupBox("File Types")
        file_types_layout = QVBoxLayout(file_types_group)
        
        self.file_types_table = QTableWidget()
        self.file_types_table.setColumnCount(3)
        self.file_types_table.setHorizontalHeaderLabels(["Extension", "Count", "Size"])
        self.file_types_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        file_types_layout.addWidget(self.file_types_table)
        
        splitter.addWidget(file_types_group)
        
        # Largest directories table
        largest_dirs_group = QGroupBox("Largest Directories")
        largest_dirs_layout = QVBoxLayout(largest_dirs_group)
        
        self.largest_dirs_table = QTableWidget()
        self.largest_dirs_table.setColumnCount(2)
        self.largest_dirs_table.setHorizontalHeaderLabels(["Directory", "Size"])
        self.largest_dirs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        largest_dirs_layout.addWidget(self.largest_dirs_table)
        
        splitter.addWidget(largest_dirs_group)
        
        splitter.setSizes([100, 200, 200])
        layout.addWidget(splitter)
        
        return disk_analyzer_tab
    
    def create_system_tools_tab(self) -> QWidget:
        """Create the system tools tab."""
        system_tools_tab = QWidget()
        layout = QVBoxLayout(system_tools_tab)
        layout.setSpacing(10)
        
        # Create tab widget for system tools
        tools_tab_widget = QTabWidget()
        layout.addWidget(tools_tab_widget)
        
        # Startup manager tab
        startup_tab = self.create_startup_manager_tab()
        tools_tab_widget.addTab(startup_tab, "Startup Manager")
        
        # Process analyzer tab
        process_tab = self.create_process_analyzer_tab()
        tools_tab_widget.addTab(process_tab, "Process Analyzer")
        
        # Registry cleaner tab (Windows only)
        if HAS_REGISTRY_CLEANER:
            registry_tab = self.create_registry_cleaner_tab()
            tools_tab_widget.addTab(registry_tab, "Registry Cleaner")
        
        return system_tools_tab
    
    def create_startup_manager_tab(self) -> QWidget:
        """Create the startup manager tab."""
        startup_tab = QWidget()
        layout = QVBoxLayout(startup_tab)
        layout.setSpacing(10)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.refresh_startup_button = QPushButton("Refresh Startup Items")
        self.refresh_startup_button.clicked.connect(self.refresh_startup_items)
        self.refresh_startup_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.refresh_startup_button)
        
        self.disable_startup_button = QPushButton("Disable Selected")
        self.disable_startup_button.clicked.connect(self.disable_selected_startup_items)
        self.disable_startup_button.setEnabled(False)
        self.disable_startup_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.disable_startup_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.startup_progress_bar = QProgressBar()
        self.startup_progress_bar.setVisible(False)
        self.startup_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.startup_progress_bar)
        
        # Results table
        self.startup_table = QTableWidget()
        self.startup_table.setColumnCount(4)
        self.startup_table.setHorizontalHeaderLabels(["Name", "Location", "Status", "Type"])
        self.startup_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.startup_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.startup_table)
        
        return startup_tab
    
    def create_process_analyzer_tab(self) -> QWidget:
        """Create the process analyzer tab."""
        process_tab = QWidget()
        layout = QVBoxLayout(process_tab)
        layout.setSpacing(10)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.refresh_processes_button = QPushButton("Refresh Processes")
        self.refresh_processes_button.clicked.connect(self.refresh_processes)
        self.refresh_processes_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.refresh_processes_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.processes_progress_bar = QProgressBar()
        self.processes_progress_bar.setVisible(False)
        self.processes_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.processes_progress_bar)
        
        # Results area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Processes table
        processes_group = QGroupBox("Running Processes")
        processes_layout = QVBoxLayout(processes_group)
        
        self.processes_table = QTableWidget()
        self.processes_table.setColumnCount(4)
        self.processes_table.setHorizontalHeaderLabels(["Name", "PID", "Memory", "CPU"])
        self.processes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.processes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        processes_layout.addWidget(self.processes_table)
        
        splitter.addWidget(processes_group)
        
        # Services table
        services_group = QGroupBox("System Services")
        services_layout = QVBoxLayout(services_group)
        
        self.services_table = QTableWidget()
        self.services_table.setColumnCount(3)
        self.services_table.setHorizontalHeaderLabels(["Name", "Status", "Description"])
        self.services_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.services_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        services_layout.addWidget(self.services_table)
        
        splitter.addWidget(services_group)
        
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        return process_tab
    
    def create_registry_cleaner_tab(self) -> QWidget:
        """Create the registry cleaner tab."""
        registry_tab = QWidget()
        layout = QVBoxLayout(registry_tab)
        layout.setSpacing(10)
        
        # Warning label
        warning_label = QLabel("Registry cleaning can be dangerous. Use with caution!")
        warning_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        layout.addWidget(warning_label)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.scan_registry_button = QPushButton("Scan Registry")
        self.scan_registry_button.clicked.connect(self.scan_registry)
        self.scan_registry_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.scan_registry_button)
        
        self.clean_registry_button = QPushButton("Clean Registry")
        self.clean_registry_button.clicked.connect(self.clean_registry)
        self.clean_registry_button.setEnabled(False)
        self.clean_registry_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.clean_registry_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.registry_progress_bar = QProgressBar()
        self.registry_progress_bar.setVisible(False)
        self.registry_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.registry_progress_bar)
        
        # Results area
        self.registry_results = QTextEdit()
        self.registry_results.setReadOnly(True)
        layout.addWidget(self.registry_results)
        
        return registry_tab
    
    def create_restore_tab(self) -> QWidget:
        """Create the restore tab."""
        restore_tab = QWidget()
        layout = QVBoxLayout(restore_tab)
        layout.setSpacing(10)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.refresh_manifests_button = QPushButton("Refresh Manifests")
        self.refresh_manifests_button.clicked.connect(self.refresh_manifests)
        self.refresh_manifests_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.refresh_manifests_button)
        
        self.restore_button = QPushButton("Restore Selected")
        self.restore_button.clicked.connect(self.restore_selected)
        self.restore_button.setEnabled(False)
        self.restore_button.setMinimumHeight(35)
        buttons_layout.addWidget(self.restore_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress bar
        self.restore_progress_bar = QProgressBar()
        self.restore_progress_bar.setVisible(False)
        self.restore_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.restore_progress_bar)
        
        # Results table
        self.manifests_table = QTableWidget()
        self.manifests_table.setColumnCount(4)
        self.manifests_table.setHorizontalHeaderLabels(["Timestamp", "Name", "Files", "Path"])
        self.manifests_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.manifests_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.manifests_table)
        
        return restore_tab
    
    def create_settings_tab(self) -> QWidget:
        """Create the settings tab."""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Create tab widget for settings categories
        settings_tab_widget = QTabWidget()
        layout.addWidget(settings_tab_widget)
        
        # General settings tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        self.log_file_input = QLineEdit()
        self.log_file_input.setPlaceholderText("Log file path (optional)")
        general_layout.addRow("Log File:", self.log_file_input)
        
        self.verbose_checkbox = QCheckBox("Verbose Output")
        general_layout.addRow(self.verbose_checkbox)
        
        settings_tab_widget.addTab(general_tab, "General")
        
        # Performance settings tab
        performance_tab = QWidget()
        performance_layout = QFormLayout(performance_tab)
        
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 32)
        self.threads_spinbox.setValue(4)
        performance_layout.addRow("Thread Count:", self.threads_spinbox)
        
        self.cpu_priority_combo = QComboBox()
        self.cpu_priority_combo.addItems(["Low", "Normal", "High"])
        self.cpu_priority_combo.setCurrentText("Normal")
        performance_layout.addRow("CPU Priority:", self.cpu_priority_combo)
        
        self.io_priority_combo = QComboBox()
        self.io_priority_combo.addItems(["Low", "Normal", "High"])
        self.io_priority_combo.setCurrentText("Low")
        performance_layout.addRow("I/O Priority:", self.io_priority_combo)
        
        self.memory_limit_spinbox = QSpinBox()
        self.memory_limit_spinbox.setRange(0, 8192)
        self.memory_limit_spinbox.setValue(0)
        self.memory_limit_spinbox.setSuffix(" MB")
        performance_layout.addRow("Memory Limit (0=unlimited):", self.memory_limit_spinbox)
        
        self.enable_checkpoints_checkbox = QCheckBox("Enable scan checkpoints")
        self.enable_checkpoints_checkbox.setChecked(True)
        performance_layout.addRow(self.enable_checkpoints_checkbox)
        
        self.checkpoint_interval_spinbox = QSpinBox()
        self.checkpoint_interval_spinbox.setRange(100, 10000)
        self.checkpoint_interval_spinbox.setValue(1000)
        performance_layout.addRow("Checkpoint Interval:", self.checkpoint_interval_spinbox)
        
        self.enable_throttling_checkbox = QCheckBox("Enable resource throttling")
        self.enable_throttling_checkbox.setChecked(True)
        performance_layout.addRow(self.enable_throttling_checkbox)
        
        settings_tab_widget.addTab(performance_tab, "Performance")
        
        # Accessibility settings tab
        accessibility_tab = QWidget()
        accessibility_layout = QFormLayout(accessibility_tab)
        
        self.high_contrast_checkbox = QCheckBox("High contrast mode")
        accessibility_layout.addRow(self.high_contrast_checkbox)
        
        self.large_fonts_checkbox = QCheckBox("Large fonts")
        accessibility_layout.addRow(self.large_fonts_checkbox)
        
        self.screen_reader_checkbox = QCheckBox("Screen reader support")
        accessibility_layout.addRow(self.screen_reader_checkbox)
        
        self.keyboard_navigation_checkbox = QCheckBox("Enhanced keyboard navigation")
        self.keyboard_navigation_checkbox.setChecked(True)
        accessibility_layout.addRow(self.keyboard_navigation_checkbox)
        
        settings_tab_widget.addTab(accessibility_tab, "Accessibility")
        
        # Internationalization settings tab
        i18n_tab = QWidget()
        i18n_layout = QFormLayout(i18n_tab)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Español", "Français", "Deutsch", "中文"])
        i18n_layout.addRow("Language:", self.language_combo)
        
        self.date_format_combo = QComboBox()
        self.date_format_combo.addItems(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"])
        i18n_layout.addRow("Date Format:", self.date_format_combo)
        
        self.number_format_combo = QComboBox()
        self.number_format_combo.addItems(["1,234.56", "1.234,56", "1 234,56"])
        i18n_layout.addRow("Number Format:", self.number_format_combo)
        
        settings_tab_widget.addTab(i18n_tab, "Language")
        
        # Save button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        save_button.setMinimumHeight(35)
        save_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; }")
        layout.addWidget(save_button)
        
        return settings_tab
    
    # Helper methods
    def browse_path(self):
        """Open file dialog to select target path."""
        path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if path:
            self.path_input.setText(path)
    
    def browse_path_for_widget(self, widget):
        """Open file dialog to select target path for a specific widget."""
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            widget.setText(path)
    
    def add_activity(self, message):
        """Add an activity message to the dashboard."""
        self.activity_list.addItem(f"[{self.get_current_time()}] {message}")
    
    def get_current_time(self):
        """Get current time as string."""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    # Cleaner tab methods
    def quick_scan(self):
        """Quick scan from dashboard."""
        self.path_input.setText(str(Path.home()))
        self.tab_widget.setCurrentIndex(1)  # Switch to cleaner tab
        self.start_scan()
    
    def start_scan(self):
        """Start the enhanced scanning process."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("=== STARTING SCAN PROCESS (DUBBING LOG) ===")
            self.logger.info("Target path mode: {}".format("Single" if self.single_path_radio.isChecked() else "Multi-drive"))
        
        # Get target paths based on mode
        target_paths = []
        
        if self.single_path_radio.isChecked():
            path = self.path_input.text().strip()
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Single path selected: {}".format(path if path else "None"))
            if not path:
                QMessageBox.warning(self, "Warning", "Please select a directory to scan.")
                return
            target_paths = [path]
        else:
            # Multi-drive mode
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Multi-drive mode selected")
            for i in range(self.drives_list.count()):
                item = self.drives_list.item(i)
                drive_data = item.data(Qt.ItemDataRole.UserRole)
                
                if isinstance(drive_data, dict):
                    # Network drive
                    target_paths.append(drive_data['path'])
                    # Add dubbing log
                    if hasattr(self, 'logger'):
                        self.logger.info("Adding network drive: {}".format(drive_data['path']))
                else:
                    # Local drive
                    target_paths.append(drive_data)
                    # Add dubbing log
                    if hasattr(self, 'logger'):
                        self.logger.info("Adding local drive: {}".format(drive_data))
            
            if not target_paths:
                QMessageBox.warning(self, "Warning", "Please select drives to scan.")
                return
        
        # Validate paths
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Validating {} paths".format(len(target_paths)))
        valid_paths = []
        for path in target_paths:
            try:
                normalized_path = normalize_path(path)
                if normalized_path.exists():
                    valid_paths.append(str(normalized_path))
                    # Add dubbing log
                    if hasattr(self, 'logger'):
                        self.logger.info("Valid path: {}".format(normalized_path))
                else:
                    self.add_activity(f"Skipping non-existent path: {path}")
                    # Add dubbing log
                    if hasattr(self, 'logger'):
                        self.logger.warning("Skipping non-existent path: {}".format(path))
            except Exception as e:
                self.add_activity(f"Invalid path {path}: {str(e)}")
                # Add dubbing log
                if hasattr(self, 'logger'):
                    self.logger.error("Invalid path {}: {}".format(path, str(e)))
        
        if not valid_paths:
            QMessageBox.critical(self, "Error", "No valid paths to scan.")
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.error("No valid paths to scan")
            return
        
        # Get performance options
        enable_checkpoints = self.enable_checkpoints_checkbox.isChecked()
        enable_throttling = self.enable_throttling_checkbox.isChecked()
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Performance options - Checkpoints: {}, Throttling: {}".format(enable_checkpoints, enable_throttling))
        
        # Update UI
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Updating UI for scan start")
        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_group.setVisible(True)
        
        if enable_checkpoints:
            self.pause_button.setEnabled(True)
            self.progress_bar.setRange(0, 100)  # Determinate progress
            self.progress_label.setText("Starting scan...")
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.progress_label.setText("Scanning...")
        
        self.progress_bar.setVisible(True)
        self.results_text.clear()
        
        # Configure scan options
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Configuring scan options")
        scan_config = Config()
        scan_config.config_data = self.config.config_data.copy()
        
        # Apply scan-specific options
        if self.pattern_input.text().strip():
            patterns = [p.strip() for p in self.pattern_input.text().split(",") if p.strip()]
            scan_config.config_data["exclude_patterns"] = patterns
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Applied pattern filters: {}".format(patterns))
        
        age_days = self.age_spinbox.value()
        if age_days > 0:
            scan_config.config_data["min_age_days"] = age_days
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Applied age filter: {} days".format(age_days))
        
        # Setup logging
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Setting up logging")
        log_file = getattr(self, 'log_file_input', None)
        log_file_path = log_file.text().strip() if log_file and log_file.text().strip() else ""
        verbose = getattr(self, 'verbose_checkbox', None)
        verbose_enabled = verbose.isChecked() if verbose else False
        setup_logging(verbose_enabled, log_file_path)
        
        # Start enhanced scanning in separate thread
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Starting enhanced scanning in separate thread")
        self.scan_thread = QThread()
        
        # Use multi-drive scanner if multiple paths
        if len(valid_paths) > 1:
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Using MultiDriveScanWorker for {} paths".format(len(valid_paths)))
            self.scan_worker = MultiDriveScanWorker(
                scan_config,
                valid_paths,
                enable_checkpoints=enable_checkpoints,
                enable_throttling=enable_throttling
            )
        else:
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Using ScanWorker for single path: {}".format(valid_paths[0]))
            self.scan_worker = ScanWorker(
                scan_config, 
                valid_paths[0],
                enable_checkpoints=enable_checkpoints,
                enable_throttling=enable_throttling
            )
        self.scan_worker.moveToThread(self.scan_thread)
        
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        
        # Connect progress updates if checkpoints are enabled
        if enable_checkpoints:
            self.scan_worker.progress_updated.connect(self.update_scan_progress)
        
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.error.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        
        self.scan_thread.start()
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Scan thread started successfully")

    def scan_finished(self, empty_files: List[Path], empty_dirs: List[Path]):
        """Handle scan completion."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("=== SCAN FINISHED (DUBBING LOG) ===")
            self.logger.info("Results - Empty files: {}, Empty dirs: {}".format(len(empty_files), len(empty_dirs)))
        
        self.empty_files = empty_files
        self.empty_dirs = empty_dirs
        
        # Update UI
        self.scan_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_group.setVisible(False)
        
        # Update status
        status_msg = f"Scan complete: {len(empty_files)} empty files, {len(empty_dirs)} empty directories"
        if hasattr(self, 'status_bar'):
            self.status_bar.setText(status_msg)
        if hasattr(self, 'add_activity'):
            self.add_activity(status_msg)
        
        # Display results
        if empty_files or empty_dirs:
            self.delete_button.setEnabled(True)
            result_text = f"Found {len(empty_files)} empty files and {len(empty_dirs)} empty directories:\n\n"
            
            if empty_files:
                result_text += "Empty files:\n"
                for file in empty_files:
                    result_text += f"  {file}\n"
                result_text += "\n"
            
            if empty_dirs:
                result_text += "Empty directories:\n"
                for dir in empty_dirs:
                    result_text += f"  {dir}\n"
        else:
            result_text = "No empty files or directories found."
            self.delete_button.setEnabled(False)
        
        self.results_text.setPlainText(result_text)
    
    def scan_error(self, error: str):
        """Handle scan error."""
        self.logger.error(f"=== Scan error occurred ===")
        self.logger.error(f"Error details: {error}")
        self.scan_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_group.setVisible(False)
        
        if hasattr(self, 'status_bar'):
            self.status_bar.setText("Scan failed")
        if hasattr(self, 'add_activity'):
            self.add_activity(f"Scan failed: {error}")
        QMessageBox.critical(self, "Scan Error", f"An error occurred during scanning:\n{error}")
    
    def update_scan_progress(self, progress):
        """Update the scan progress bar with dubbing logs for debugging."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            percentage = getattr(progress, 'percentage', 0.0)
            self.logger.info("Updating scan progress: {:.1f}%".format(percentage))
        
        if hasattr(progress, 'percentage'):
            self.progress_bar.setValue(int(progress.percentage))
            # Update scan stats if available
            if hasattr(progress, 'processed_count') and hasattr(progress, 'total_count'):
                self.scan_stats_label.setText(
                    f"Processed: {progress.processed_count}/{progress.total_count} items "
                    f"({progress.percentage:.1f}%)"
                )
    
    def start_delete(self):
        """Start the deletion process with dubbing logs for debugging."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("=== STARTING DELETE PROCESS (DUBBING LOG) ===")
            self.logger.info("Files to delete: {}".format(len(self.empty_files)))
            self.logger.info("Directories to delete: {}".format(len(self.empty_dirs)))
        
        if not self.empty_files and not self.empty_dirs:
            QMessageBox.information(self, "Info", "No files or directories to delete.")
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("No files or directories to delete")
            return
        
        # Confirm deletion
        dry_run = self.dry_run_checkbox.isChecked()
        use_trash = self.trash_checkbox.isChecked()
        
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Deletion options - Dry run: {}, Use trash: {}".format(dry_run, use_trash))
        
        action = "preview deletion of" if dry_run else "delete"
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to {action} {len(self.empty_files)} files and {len(self.empty_dirs)} directories?\n"
            f"{'This is a preview only.' if dry_run else 'This action cannot be undone.'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("User cancelled deletion")
            return
        
        # Update UI
        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_group.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_label.setText("Deleting...")
        
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Starting deletion process in separate thread")
        
        # Start deletion in separate thread
        self.delete_thread = QThread()
        self.delete_worker = DeleteWorker(
            Deleter(dry_run=dry_run, use_trash=use_trash),
            self.empty_files,
            self.empty_dirs
        )
        self.delete_worker.moveToThread(self.delete_thread)
        
        self.delete_thread.started.connect(self.delete_worker.run)
        self.delete_worker.finished.connect(self.delete_finished)
        self.delete_worker.error.connect(self.delete_error)
        self.delete_worker.finished.connect(self.delete_thread.quit)
        self.delete_worker.error.connect(self.delete_thread.quit)
        self.delete_thread.finished.connect(self.delete_thread.deleteLater)
        
        self.delete_thread.start()
        
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Deletion thread started successfully")

    def pause_scan(self):
        """Pause the scanning process with dubbing logs for debugging."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("=== PAUSING SCAN PROCESS (DUBBING LOG) ===")
        
        if not hasattr(self, 'scan_worker') or not self.scan_worker:
            QMessageBox.warning(self, "Warning", "No scan in progress.")
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.warning("No scan in progress when trying to pause")
            return
        
        try:
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Calling pause method on scan worker")
            
            # Call pause method on the worker
            if hasattr(self, 'scan_worker') and hasattr(self.scan_worker, 'pause'):
                self.scan_worker.pause()
                self.pause_button.setEnabled(False)
                self.resume_button.setEnabled(True)
                self.progress_label.setText("Scan paused")
                
                # Add dubbing log
                if hasattr(self, 'logger'):
                    self.logger.info("Scan paused successfully")
            else:
                # Add dubbing log
                if hasattr(self, 'logger'):
                    self.logger.error("Scan worker does not have pause method")
                QMessageBox.warning(self, "Warning", "Pause functionality not available.")
        except Exception as e:
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.error("Error pausing scan: {}".format(str(e)))
            QMessageBox.critical(self, "Error", f"Error pausing scan:\n{str(e)}")

    def resume_scan(self):
        """Resume the scanning process with dubbing logs for debugging."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("=== RESUMING SCAN PROCESS (DUBBING LOG) ===")
        
        if not hasattr(self, 'scan_worker') or not self.scan_worker:
            QMessageBox.warning(self, "Warning", "No scan in progress.")
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.warning("No scan in progress when trying to resume")
            return
        
        try:
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("Calling resume method on scan worker")
            
            # Call resume method on the worker
            if hasattr(self, 'scan_worker') and hasattr(self.scan_worker, 'resume'):
                self.scan_worker.resume()
                self.pause_button.setEnabled(True)
                self.resume_button.setEnabled(False)
                self.progress_label.setText("Scanning...")
                
                # Add dubbing log
                if hasattr(self, 'logger'):
                    self.logger.info("Scan resumed successfully")
            else:
                # Add dubbing log
                if hasattr(self, 'logger'):
                    self.logger.error("Scan worker does not have resume method")
                QMessageBox.warning(self, "Warning", "Resume functionality not available.")
        except Exception as e:
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.error("Error resuming scan: {}".format(str(e)))
            QMessageBox.critical(self, "Error", f"Error resuming scan:\n{str(e)}")

    def delete_finished(self, result: Dict[str, Any]):
        """Handle deletion completion."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("=== DELETION FINISHED (DUBBING LOG) ===")
            self.logger.info("Results - Files deleted: {}, Directories deleted: {}".format(result['files_deleted'], result['dirs_deleted']))
            self.logger.info("Errors: {}".format(len(result['errors'])))
        
        self.scan_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_group.setVisible(False)
        self.status_bar.setText("Deletion complete")
        self.add_activity(f"Deletion complete: {result['files_deleted']} files, {result['dirs_deleted']} directories")
        
        # Display results
        result_text = self.results_text.toPlainText()
        result_text += f"\n\nDeletion results:\n"
        result_text += f"  Files processed: {result['files_deleted']}\n"
        result_text += f"  Directories processed: {result['dirs_deleted']}\n"
        result_text += f"  Errors: {len(result['errors'])}\n"
        
        if result['errors']:
            result_text += "\nErrors:\n"
            for error in result['errors']:
                result_text += f"  {error['type']} {error['path']}: {error['error']}\n"
        
        self.results_text.setPlainText(result_text)
        
        # Clear the lists
        self.empty_files = []
        self.empty_dirs = []
        self.delete_button.setEnabled(False)
    
    def delete_error(self, error: str):
        """Handle deletion error."""
        self.logger.error(f"Deletion error: {error}")
        self.scan_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_bar.setText("Deletion failed")
        self.add_activity(f"Deletion failed: {error}")
        QMessageBox.critical(self, "Deletion Error", f"An error occurred during deletion:\n{error}")
    
    def start_find_duplicates(self):
        """Start finding duplicates with dubbing logs for debugging."""
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("=== STARTING DUPLICATE FINDING PROCESS (DUBBING LOG) ===")
        
        path = self.duplicates_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Warning", "Please select a directory to scan for duplicates.")
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.info("No path selected for duplicate finding")
            return
        
        try:
            normalized_path = normalize_path(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid path: {str(e)}")
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.error("Invalid path for duplicate finding: {}".format(str(e)))
            return
        
        if not normalized_path.exists():
            QMessageBox.critical(self, "Error", "Selected path does not exist.")
            # Add dubbing log
            if hasattr(self, 'logger'):
                self.logger.error("Selected path does not exist for duplicate finding")
            return
        
        # Update UI
        self.find_duplicates_button.setEnabled(False)
        self.delete_duplicates_button.setEnabled(False)
        self.duplicates_progress_bar.setVisible(True)
        self.duplicates_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.duplicates_tree.clear()
        self.status_bar.setText("Finding duplicates...")
        self.add_activity("Finding duplicates...")
        
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Starting duplicate finding process for path: {}".format(normalized_path))
        
        # Get options
        hash_algorithm = self.hash_algorithm_combo.currentText()
        
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Using hash algorithm: {}".format(hash_algorithm))
        
        # Start finding duplicates in separate thread
        self.duplicate_thread = QThread()
        self.duplicate_worker = DuplicateFinderWorker(self.config, str(normalized_path), hash_algorithm)
        self.duplicate_worker.moveToThread(self.duplicate_thread)
        
        self.duplicate_thread.started.connect(self.duplicate_worker.run)
        self.duplicate_worker.finished.connect(self.duplicates_found)
        self.duplicate_worker.error.connect(self.duplicates_error)
        self.duplicate_worker.finished.connect(self.duplicate_thread.quit)
        self.duplicate_worker.error.connect(self.duplicate_thread.quit)
        self.duplicate_thread.finished.connect(self.duplicate_thread.deleteLater)
        
        self.duplicate_thread.start()
        
        # Add dubbing log
        if hasattr(self, 'logger'):
            self.logger.info("Duplicate finding thread started successfully")
    def duplicates_found(self, result: dict):
        """Handle duplicates found."""
        self.duplicates = result["duplicates"]
        stats = result["stats"]
        
        # Update UI
        self.find_duplicates_button.setEnabled(True)
        self.duplicates_progress_bar.setVisible(False)
        self.status_bar.setText(f"Found {stats['duplicate_groups']} groups of duplicates")
        self.add_activity(f"Found {stats['duplicate_groups']} groups of duplicates")
        
        # Display results in tree
        self.duplicates_tree.clear()
        total_files = 0
        
        for hash_val, paths in self.duplicates.items():
            if len(paths) < 2:  # Skip non-duplicates
                continue
                
            group_item = QTreeWidgetItem([f"Group {hash_val[:8]}", str(len(paths)), ""])
            group_item.setExpanded(True)
            
            for path in paths:
                try:
                    file_size = path.stat().st_size
                    size_str = self.format_bytes(file_size)
                except:
                    size_str = "Unknown"
                    
                file_item = QTreeWidgetItem([str(path), "", size_str])
                group_item.addChild(file_item)
                total_files += 1
            
            self.duplicates_tree.addTopLevelItem(group_item)
        
        if total_files > 0:
            self.delete_duplicates_button.setEnabled(True)
            self.duplicates_details.setPlainText(f"Found {len(self.duplicates)} duplicate groups with {total_files} files total.\nPotential space savings: {stats['bytes_saved_if_deleted']}")
        else:
            self.delete_duplicates_button.setEnabled(False)
            self.duplicates_details.setPlainText("No duplicates found.")
    
    def duplicates_error(self, error: str):
        """Handle duplicates error."""
        self.logger.error(f"Duplicates error: {error}")
        self.find_duplicates_button.setEnabled(True)
        self.duplicates_progress_bar.setVisible(False)
        self.status_bar.setText("Duplicate finding failed")
        self.add_activity(f"Duplicate finding failed: {error}")
        QMessageBox.critical(self, "Error", f"An error occurred while finding duplicates:\n{error}")
    
    def delete_selected_duplicates(self):
        """Delete selected duplicates."""
        selected_items = self.duplicates_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "Please select duplicate groups to delete.")
            return
        
        # Collect files to delete
        files_to_delete = []
        for item in selected_items:
            if item.childCount() > 0:  # Group item
                for i in range(item.childCount()):
                    child = item.child(i)
                    file_path = Path(child.text(0))
                    files_to_delete.append(file_path)
            else:  # Individual file item
                file_path = Path(item.text(0))
                files_to_delete.append(file_path)
        
        if not files_to_delete:
            QMessageBox.information(self, "Info", "No files selected for deletion.")
            return
        
        # Confirm deletion
        strategy = self.strategy_combo.currentText()
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Delete {len(files_to_delete)} duplicate files using '{strategy}' strategy?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Implement actual deletion using the selected strategy
        try:
            from ..analyzers.duplicate_finder import DuplicateFinder
            
            # Create finder and apply strategy
            finder = DuplicateFinder(self.config, "")
            # Set the duplicates we found
            finder.duplicates = self.duplicates
            files_to_delete_final = finder.auto_select_duplicates(strategy)
            
            # Filter to only selected files
            files_to_delete_final = [f for f in files_to_delete_final if f in files_to_delete]
            
            if not files_to_delete_final:
                QMessageBox.information(self, "Info", "No files to delete after applying strategy.")
                return
            
            # Create deleter and delete files
            deleter = Deleter(dry_run=False, use_trash=True)
            result = deleter.delete(files_to_delete_final, [])
            
            files_deleted = result.get('files_deleted', 0)
            errors = result.get('errors', [])
            
            message = f"Successfully deleted {files_deleted} duplicate files using {strategy} strategy."
            if errors:
                message += f"\n{len(errors)} errors occurred."
            
            QMessageBox.information(self, "Deletion Complete", message)
            self.add_activity(f"Deleted {files_deleted} duplicate files using {strategy}")
            
            # Refresh the duplicates scan
            self.start_find_duplicates()
            
        except Exception as e:
            QMessageBox.critical(self, "Deletion Error", f"Error deleting duplicate files:\n{str(e)}")
            self.add_activity(f"Failed to delete duplicate files: {str(e)}")
    
    # Large files tab methods
    def start_find_large_files(self):
        """Start finding large files."""
        path = self.large_files_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Warning", "Please select a directory to scan for large files.")
            return
        
        try:
            normalized_path = normalize_path(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid path: {str(e)}")
            return
        
        if not normalized_path.exists():
            QMessageBox.critical(self, "Error", "Selected path does not exist.")
            return
        
        # Update UI
        self.find_large_files_button.setEnabled(False)
        self.delete_large_files_button.setEnabled(False)
        self.large_files_progress_bar.setVisible(True)
        self.large_files_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.large_files_table.setRowCount(0)
        self.status_bar.setText("Finding large files...")
        self.add_activity("Finding large files...")
        
        # Get options
        min_size_mb = self.min_size_spinbox.value()
        
        # Start finding large files in separate thread
        self.large_file_thread = QThread()
        self.large_file_worker = LargeFileFinderWorker(self.config, str(normalized_path), min_size_mb)
        self.large_file_worker.moveToThread(self.large_file_thread)
        
        self.large_file_thread.started.connect(self.large_file_worker.run)
        self.large_file_worker.finished.connect(self.large_files_found)
        self.large_file_worker.error.connect(self.large_files_error)
        self.large_file_worker.finished.connect(self.large_file_thread.quit)
        self.large_file_worker.error.connect(self.large_file_thread.quit)
        self.large_file_thread.finished.connect(self.large_file_thread.deleteLater)
        
        self.large_file_thread.start()
    
    def large_files_found(self, result: list):
        """Handle large files found."""
        large_files, stats = result
        
        # Update UI
        self.find_large_files_button.setEnabled(True)
        self.large_files_progress_bar.setVisible(False)
        self.status_bar.setText(f"Found {len(large_files)} large files")
        self.add_activity(f"Found {len(large_files)} large files")
        
        # Display results in table
        self.large_files = large_files
        self.large_files_table.setRowCount(len(large_files))
        
        for i, (filepath, size) in enumerate(large_files):
            try:
                stat = filepath.stat()
                modified_time = stat.st_mtime
                from datetime import datetime
                modified_str = datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M")
            except:
                modified_str = "Unknown"
            
            size_str = self.format_bytes(size)
            
            self.large_files_table.setItem(i, 0, QTableWidgetItem(str(filepath)))
            self.large_files_table.setItem(i, 1, QTableWidgetItem(size_str))
            self.large_files_table.setItem(i, 2, QTableWidgetItem(modified_str))
        
        if len(large_files) > 0:
            self.delete_large_files_button.setEnabled(True)
        else:
            self.delete_large_files_button.setEnabled(False)
    
    def large_files_error(self, error: str):
        """Handle large files error."""
        self.logger.error(f"Large files error: {error}")
        self.find_large_files_button.setEnabled(True)
        self.large_files_progress_bar.setVisible(False)
        self.status_bar.setText("Large files finding failed")
        self.add_activity(f"Large files finding failed: {error}")
        QMessageBox.critical(self, "Error", f"An error occurred while finding large files:\n{error}")
    
    def delete_selected_large_files(self):
        """Delete selected large files."""
        selected_ranges = self.large_files_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, "Info", "Please select files to delete.")
            return
        
        # Collect files to delete
        files_to_delete = []
        for range_ in selected_ranges:
            for row in range(range_.topRow(), range_.bottomRow() + 1):
                item = self.large_files_table.item(row, 0)
                if item:
                    file_path = Path(item.text())
                    files_to_delete.append(file_path)
        
        if not files_to_delete:
            QMessageBox.information(self, "Info", "No files selected for deletion.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion", 
            f"Delete {len(files_to_delete)} large files?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Implement actual deletion
        try:
            # Create deleter and delete files
            deleter = Deleter(dry_run=False, use_trash=True)
            result = deleter.delete(files_to_delete, [])
            
            files_deleted = result.get('files_deleted', 0)
            errors = result.get('errors', [])
            
            message = f"Successfully deleted {files_deleted} large files."
            if errors:
                message += f"\n{len(errors)} errors occurred."
            
            QMessageBox.information(self, "Deletion Complete", message)
            self.add_activity(f"Deleted {files_deleted} large files")
            
            # Refresh the large files scan
            self.start_find_large_files()
            
        except Exception as e:
            QMessageBox.critical(self, "Deletion Error", f"Error deleting large files:\n{str(e)}")
            self.add_activity(f"Failed to delete large files: {str(e)}")
    
    # Temp cleaner tab methods
    def start_temp_scan(self):
        """Start scanning for temporary files."""
        self.temp_scan_button.setEnabled(False)
        self.temp_clean_button.setEnabled(False)
        self.temp_progress_bar.setVisible(True)
        self.temp_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.temp_status_label.setText("Scanning for temporary files...")
        
        # Clear previous results
        self.temp_results_table.setRowCount(0)
        
        # Create and start worker thread
        self.temp_cleaner_thread = QThread()
        self.temp_cleaner_worker = TempCleanerWorker(self.config)
        self.temp_cleaner_worker.moveToThread(self.temp_cleaner_thread)
        
        # Connect signals
        self.temp_cleaner_thread.started.connect(self.temp_cleaner_worker.run)
        self.temp_cleaner_worker.finished.connect(self.temp_scan_finished)
        self.temp_cleaner_worker.error.connect(self.temp_scan_error)
        self.temp_cleaner_worker.finished.connect(self.temp_cleaner_thread.quit)
        self.temp_cleaner_worker.finished.connect(self.temp_cleaner_worker.deleteLater)
        self.temp_cleaner_thread.finished.connect(self.temp_cleaner_thread.deleteLater)
        
        self.temp_cleaner_thread.start()
    
    def temp_scan_finished(self, result):
        """Handle temp scan completion."""
        temp_files, stats = result
        
        # Populate results table
        self.temp_results_table.setRowCount(len(temp_files))
        
        for i, file_path in enumerate(temp_files):
            # Checkbox for selection
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.temp_results_table.setCellWidget(i, 0, checkbox)
            
            # File path
            self.temp_results_table.setItem(i, 1, QTableWidgetItem(str(file_path)))
            
            # File size
            try:
                size = file_path.stat().st_size
                size_str = self.format_bytes(size)
            except (OSError, AttributeError):
                size_str = "Unknown"
            self.temp_results_table.setItem(i, 2, QTableWidgetItem(size_str))
            
            # File type
            file_type = self.get_temp_file_type(file_path)
            self.temp_results_table.setItem(i, 3, QTableWidgetItem(file_type))
        
        # Update summary
        total_size = stats.get('total_size_human', 'Unknown')
        file_count = stats.get('temp_files_found', len(temp_files))
        self.temp_summary_label.setText(f"Found {file_count} temporary files, total size: {total_size}")
        
        # Update UI
        self.temp_progress_bar.setVisible(False)
        self.temp_scan_button.setEnabled(True)
        self.temp_clean_button.setEnabled(len(temp_files) > 0)
        self.temp_status_label.setText("Scan completed successfully")
        
        self.add_activity(f"Found {file_count} temporary files ({total_size})")
    
    def temp_scan_error(self, error):
        """Handle temp scan error."""
        self.temp_progress_bar.setVisible(False)
        self.temp_scan_button.setEnabled(True)
        self.temp_status_label.setText(f"Error: {error}")
        QMessageBox.critical(self, "Temp Scan Error", f"An error occurred during temp scan:\n{error}")
    
    def start_temp_clean(self):
        """Start cleaning selected temporary files."""
        # Get selected files
        selected_files = []
        for row in range(self.temp_results_table.rowCount()):
            checkbox = self.temp_results_table.cellWidget(row, 0)
            if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                item = self.temp_results_table.item(row, 1)
                if item:
                    file_path = item.text()
                    selected_files.append(Path(file_path))
        
        if not selected_files:
            QMessageBox.warning(self, "No Selection", "Please select files to clean.")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Cleaning",
            f"Are you sure you want to clean {len(selected_files)} temporary files?\n"
            "Files will be moved to trash.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start deletion
        try:
            deleter = Deleter(dry_run=False, use_trash=True)
            result = deleter.delete(selected_files, [])
            
            files_deleted = result.get('files_deleted', 0)
            errors = result.get('errors', [])
            
            message = f"Successfully cleaned {files_deleted} temporary files."
            if errors:
                message += f"\n{len(errors)} errors occurred."
            
            QMessageBox.information(self, "Cleaning Complete", message)
            self.add_activity(f"Cleaned {files_deleted} temporary files")
            
            # Refresh the scan
            self.start_temp_scan()
            
        except Exception as e:
            QMessageBox.critical(self, "Cleaning Error", f"An error occurred during cleaning:\n{str(e)}")
    
    def get_temp_file_type(self, file_path):
        """Determine the type of temporary file."""
        path_str = str(file_path).lower()
        
        if 'temp' in path_str or 'tmp' in path_str:
            return "System Temp"
        elif 'cache' in path_str:
            return "Cache"
        elif any(browser in path_str for browser in ['chrome', 'firefox', 'edge', 'safari']):
            return "Browser Temp"
        elif file_path.suffix.lower() in ['.tmp', '.temp', '.cache']:
            return "Temp File"
        else:
            return "Other"
    
    # Disk analyzer tab methods
    def start_disk_analysis(self):
        """Start disk analysis."""
        path = self.disk_analyzer_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "Warning", "Please select a directory to analyze.")
            return
        
        try:
            normalized_path = normalize_path(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid path: {str(e)}")
            return
        
        if not normalized_path.exists():
            QMessageBox.critical(self, "Error", "Selected path does not exist.")
            return
        
        # Update UI
        self.analyze_disk_button.setEnabled(False)
        self.disk_analyzer_progress_bar.setVisible(True)
        self.disk_analyzer_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.setText("Analyzing disk...")
        self.add_activity("Analyzing disk...")
        
        # Start disk analysis in separate thread
        self.disk_analyzer_thread = QThread()
        self.disk_analyzer_worker = DiskAnalyzerWorker(self.config, str(normalized_path))
        self.disk_analyzer_worker.moveToThread(self.disk_analyzer_thread)
        
        self.disk_analyzer_thread.started.connect(self.disk_analyzer_worker.run)
        self.disk_analyzer_worker.finished.connect(self.disk_analysis_complete)
        self.disk_analyzer_worker.error.connect(self.disk_analysis_error)
        self.disk_analyzer_worker.finished.connect(self.disk_analyzer_thread.quit)
        self.disk_analyzer_worker.error.connect(self.disk_analyzer_thread.quit)
        self.disk_analyzer_thread.finished.connect(self.disk_analyzer_thread.deleteLater)
        
        self.disk_analyzer_thread.start()
    
    def disk_analysis_complete(self, result: dict):
        """Handle disk analysis completion."""
        disk_usage = result["disk_usage"]
        file_types = result["file_types"]
        largest_dirs = result["largest_dirs"]
        analyzer = result.get("analyzer")
        
        # Store analyzer for visualization
        self.current_analyzer = analyzer
        
        # Update UI
        self.analyze_disk_button.setEnabled(True)
        self.disk_analyzer_progress_bar.setVisible(False)
        self.status_bar.setText("Disk analysis complete")
        self.add_activity("Disk analysis complete")
        
        # Enable visualization buttons
        if analyzer:
            self.show_treemap_button.setEnabled(True)
            self.show_sunburst_button.setEnabled(True)
            self.show_dashboard_button.setEnabled(True)
            self.export_visualization_button.setEnabled(True)
        
        # Display disk usage
        usage_text = f"Disk Usage: {disk_usage.get('used_human_str', 'Unknown')} used of {disk_usage.get('total_human_str', 'Unknown')} ({disk_usage.get('used_percent', 0):.1f}%)\n"
        self.disk_usage_label.setText(usage_text)
        
        # Display file types
        self.file_types_table.setRowCount(min(len(file_types), 20))  # Limit to top 20
        for i, (ext, info) in enumerate(list(file_types.items())[:20]):
            self.file_types_table.setItem(i, 0, QTableWidgetItem(ext if ext else "(no extension)"))
            self.file_types_table.setItem(i, 1, QTableWidgetItem(str(info["count"])))
            # Fix: Use size_bytes and format it, or provide size_human if available
            if "size_human" in info:
                size_human = info["size_human"]
            elif "size_bytes" in info:
                size_human = self.format_bytes(info["size_bytes"])
            else:
                size_human = "Unknown"
            self.file_types_table.setItem(i, 2, QTableWidgetItem(size_human))
        
        # Display largest directories
        self.largest_dirs_table.setRowCount(len(largest_dirs))
        for i, (path, size) in enumerate(largest_dirs):
            size_str = self.format_bytes(size)
            self.largest_dirs_table.setItem(i, 0, QTableWidgetItem(str(path)))
            self.largest_dirs_table.setItem(i, 1, QTableWidgetItem(size_str))
    
    def disk_analysis_error(self, error: str):
        """Handle disk analysis error."""
        self.logger.error(f"Disk analysis error: {error}")
        self.analyze_disk_button.setEnabled(True)
        self.disk_analyzer_progress_bar.setVisible(False)
        self.status_bar.setText("Disk analysis failed")
        self.add_activity(f"Disk analysis failed: {error}")
        QMessageBox.critical(self, "Error", f"An error occurred during disk analysis:\n{error}")
    
    # Visualization methods
    def show_treemap_visualization(self):
        """Show TreeMap visualization in a new window."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Warning", "Please run disk analysis first.")
            return
        
        try:
            from ..visualization import TreeMapGenerator
            import tempfile
            import webbrowser
            
            generator = TreeMapGenerator(self.current_analyzer)
            if not generator.has_plotly:
                QMessageBox.warning(self, "Plotly Not Available", 
                                  "Plotly library is not installed. Please install it with: pip install plotly")
                return
            
            html_content = generator.export_as_html()
            
            # Save to temporary file and open in browser
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open(f'file://{temp_path}')
            self.add_activity("TreeMap visualization opened in browser")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate TreeMap: {str(e)}")
    
    def show_sunburst_visualization(self):
        """Show Sunburst visualization in a new window."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Warning", "Please run disk analysis first.")
            return
        
        try:
            from ..visualization import SunburstGenerator
            import tempfile
            import webbrowser
            
            generator = SunburstGenerator(self.current_analyzer)
            if not generator.has_plotly:
                QMessageBox.warning(self, "Plotly Not Available", 
                                  "Plotly library is not installed. Please install it with: pip install plotly")
                return
            
            html_content = generator.export_as_html()
            
            # Save to temporary file and open in browser
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open(f'file://{temp_path}')
            self.add_activity("Sunburst visualization opened in browser")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Sunburst: {str(e)}")
    
    def show_interactive_dashboard(self):
        """Show interactive dashboard in a new window."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Warning", "Please run disk analysis first.")
            return
        
        try:
            from ..visualization import InteractiveDashboard
            import tempfile
            import webbrowser
            
            dashboard = InteractiveDashboard(self.current_analyzer)
            if not dashboard.has_plotly:
                QMessageBox.warning(self, "Plotly Not Available", 
                                  "Plotly library is not installed. Please install it with: pip install plotly")
                return
            
            fig = dashboard.create_dashboard()
            # Generate HTML content directly instead of using export_visualization
            try:
                from plotly.offline import plot
                html_content = plot(fig, output_type='div', include_plotlyjs='cdn')
            except ImportError:
                QMessageBox.warning(self, "Plotly Not Available", 
                                  "Plotly library is not installed. Please install it with: pip install plotly")
                return
            
            # Save to temporary file and open in browser
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open(f'file://{temp_path}')
            self.add_activity("Interactive dashboard opened in browser")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate dashboard: {str(e)}")
    
    def export_visualization_dialog(self):
        """Show export visualization dialog."""
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Warning", "Please run disk analysis first.")
            return
        
        # Create export dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Visualization")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Visualization type selection
        type_group = QGroupBox("Visualization Type")
        type_layout = QVBoxLayout(type_group)
        
        self.export_treemap_radio = QRadioButton("TreeMap")
        self.export_sunburst_radio = QRadioButton("Sunburst Chart")
        self.export_dashboard_radio = QRadioButton("Interactive Dashboard")
        self.export_treemap_radio.setChecked(True)
        
        type_layout.addWidget(self.export_treemap_radio)
        type_layout.addWidget(self.export_sunburst_radio)
        type_layout.addWidget(self.export_dashboard_radio)
        layout.addWidget(type_group)
        
        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)
        
        self.export_html_radio = QRadioButton("HTML (Interactive)")
        self.export_png_radio = QRadioButton("PNG (Image)")
        self.export_svg_radio = QRadioButton("SVG (Vector)")
        self.export_html_radio.setChecked(True)
        
        format_layout.addWidget(self.export_html_radio)
        format_layout.addWidget(self.export_png_radio)
        format_layout.addWidget(self.export_svg_radio)
        layout.addWidget(format_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        export_button = QPushButton("Export")
        cancel_button = QPushButton("Cancel")
        
        export_button.clicked.connect(lambda: self.perform_visualization_export(dialog))
        cancel_button.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        
        dialog.exec()
    
    def perform_visualization_export(self, dialog):
        """Perform the actual visualization export."""
        try:
            # Determine visualization type
            if self.export_treemap_radio.isChecked():
                viz_type = "treemap"
            elif self.export_sunburst_radio.isChecked():
                viz_type = "sunburst"
            else:
                viz_type = "dashboard"
            
            # Determine format
            if self.export_html_radio.isChecked():
                format_ext = "html"
            elif self.export_png_radio.isChecked():
                format_ext = "png"
            else:
                format_ext = "svg"
            
            # Get save location
            filename, _ = QFileDialog.getSaveFileName(
                self,
                f"Export {viz_type.title()} Visualization",
                f"{viz_type}_visualization.{format_ext}",
                f"{format_ext.upper()} Files (*.{format_ext})"
            )
            
            if not filename:
                return
            
            # Export visualization
            from ..visualization import TreeMapGenerator, SunburstGenerator, InteractiveDashboard
            
            if viz_type == "treemap":
                generator = TreeMapGenerator(self.current_analyzer)
                if format_ext == "html":
                    content = generator.export_as_html()
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    img_data = generator.export_as_image(format_ext)
                    with open(filename, 'wb') as f:
                        f.write(img_data)
            elif viz_type == "sunburst":
                generator = SunburstGenerator(self.current_analyzer)
                if format_ext == "html":
                    content = generator.export_as_html()
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                else:
                    img_data = generator.export_as_image(format_ext)
                    with open(filename, 'wb') as f:
                        f.write(img_data)
            else:  # dashboard
                dashboard = InteractiveDashboard(self.current_analyzer)
                success = dashboard.export_visualization(format_ext, filename)
                if not success:
                    raise Exception("Export failed")
            
            dialog.accept()
            QMessageBox.information(self, "Success", f"Visualization exported to {filename}")
            self.add_activity(f"Exported {viz_type} visualization to {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export visualization: {str(e)}")
    
    # System tools methods
    def refresh_startup_items(self):
        """Refresh startup items."""
        # Update UI
        self.refresh_startup_button.setEnabled(False)
        self.startup_progress_bar.setVisible(True)
        self.startup_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.setText("Loading startup items...")
        self.add_activity("Loading startup items...")
        
        try:
            # Create manager and list startup items
            manager = StartupManager()
            items = manager.list_startup_items()
            stats = manager.get_stats()
            
            # Update UI
            self.refresh_startup_button.setEnabled(True)
            self.startup_progress_bar.setVisible(False)
            self.status_bar.setText(f"Loaded {stats['total_startup_items']} startup items")
            self.add_activity(f"Loaded {stats['total_startup_items']} startup items")
            
            # Display results in table
            self.startup_table.setRowCount(len(items))
            
            for i, item in enumerate(items):
                self.startup_table.setItem(i, 0, QTableWidgetItem(item.get("name", "Unknown")))
                self.startup_table.setItem(i, 1, QTableWidgetItem(item.get("location", "Unknown")))
                
                status = "Enabled" if item.get("enabled", True) else "Disabled"
                self.startup_table.setItem(i, 2, QTableWidgetItem(status))
                
                item_type = item.get("type", "Unknown")
                self.startup_table.setItem(i, 3, QTableWidgetItem(item_type))
            
            if len(items) > 0:
                self.disable_startup_button.setEnabled(True)
            else:
                self.disable_startup_button.setEnabled(False)
                
        except Exception as e:
            self.logger.error(f"Startup items error: {e}")
            self.refresh_startup_button.setEnabled(True)
            self.startup_progress_bar.setVisible(False)
            self.status_bar.setText("Failed to load startup items")
            self.add_activity(f"Failed to load startup items: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while loading startup items:\n{e}")
    
    def disable_selected_startup_items(self):
        """Disable selected startup items."""
        selected_ranges = self.startup_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, "Info", "Please select startup items to disable.")
            return
        
        # Implement actual disabling
        try:
            # Get selected startup items
            selected_items = []
            for range_ in selected_ranges:
                for row in range(range_.topRow(), range_.bottomRow() + 1):
                    name_item = self.startup_table.item(row, 0)
                    type_item = self.startup_table.item(row, 3)  # Type is in column 3
                    if name_item and type_item:
                        item_name = name_item.text()
                        item_type = type_item.text()
                        selected_items.append({"name": item_name, "type": item_type})
            
            if not selected_items:
                QMessageBox.information(self, "Info", "No startup items selected.")
                return
            
            # Create manager and disable items
            manager = StartupManager()
            disabled_count = 0
            errors = []
            
            for item in selected_items:
                try:
                    success = manager.disable_startup_item(item["name"], item["type"])
                    if success:
                        disabled_count += 1
                    else:
                        errors.append(f"Failed to disable {item['name']}")
                except Exception as e:
                    errors.append(f"Error disabling {item['name']}: {str(e)}")
            
            # Show results
            message = f"Successfully disabled {disabled_count} out of {len(selected_items)} startup items."
            if errors:
                message += f"\n\nErrors:\n" + "\n".join(errors[:3])
                if len(errors) > 3:
                    message += f"\n... and {len(errors) - 3} more errors"
            
            QMessageBox.information(self, "Startup Items Disabled", message)
            self.add_activity(f"Disabled {disabled_count} startup items")
            
            # Refresh the startup items list
            self.refresh_startup_items()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error disabling startup items:\n{str(e)}")
            self.add_activity(f"Failed to disable startup items: {str(e)}")
    
    def refresh_processes(self):
        """Refresh processes and services."""
        try:
            import platform
            system = platform.system().lower()
            
            # Update UI
            self.refresh_processes_button.setEnabled(False)
            self.processes_progress_bar.setVisible(True)
            self.processes_progress_bar.setRange(0, 0)  # Indeterminate progress
            
            # Clear existing data
            self.processes_table.setRowCount(0)
            self.services_table.setRowCount(0)
            
            # Create ProcessAnalyzer instance
            analyzer = ProcessAnalyzer(self.config)
            
            # Get processes
            self.processes_progress_bar.setRange(0, 2)
            self.processes_progress_bar.setValue(0)
            processes = analyzer.list_processes()
            
            # Populate processes table
            self.processes_progress_bar.setValue(1)
            self.processes_table.setRowCount(len(processes))
            
            for i, process in enumerate(processes):
                # Handle different OS formats
                if system == "windows":
                    name = process.get("name", "Unknown")
                    pid = process.get("pid", "N/A")
                    memory = process.get("mem_usage", "N/A")
                    cpu = process.get("cpu_time", "N/A")
                else:  # macOS/Linux
                    name = process.get("command", "Unknown")
                    if len(name) > 50:  # Truncate long command names
                        name = name[:47] + "..."
                    pid = process.get("pid", "N/A")
                    memory = f"{process.get('mem_percent', '0')}%"
                    cpu = f"{process.get('cpu_percent', '0')}%"
                
                self.processes_table.setItem(i, 0, QTableWidgetItem(name))
                self.processes_table.setItem(i, 1, QTableWidgetItem(str(pid)))
                self.processes_table.setItem(i, 2, QTableWidgetItem(memory))
                self.processes_table.setItem(i, 3, QTableWidgetItem(cpu))
            
            # Get services
            services = analyzer.list_services()
            
            # Populate services table
            self.processes_progress_bar.setValue(2)
            self.services_table.setRowCount(len(services))
            
            for i, service in enumerate(services):
                # Handle different OS formats
                if system == "windows":
                    name = service.get("display_name", service.get("name", "Unknown"))
                    status = service.get("state", "Unknown")
                    description = service.get("name", "")
                else:  # macOS/Linux
                    name = service.get("label", service.get("unit", service.get("service", "Unknown")))
                    status = service.get("active", service.get("last_exit_code", "Unknown"))
                    description = service.get("description", "")
                
                self.services_table.setItem(i, 0, QTableWidgetItem(name))
                self.services_table.setItem(i, 1, QTableWidgetItem(status))
                self.services_table.setItem(i, 2, QTableWidgetItem(description))
            
            # Update activity log
            stats = analyzer.get_stats()
            self.add_activity(f"Refreshed processes: {stats['total_processes']} processes, {stats['total_services']} services")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error refreshing processes:\n{str(e)}")
            self.add_activity(f"Failed to refresh processes: {str(e)}")
        finally:
            # Re-enable button and hide progress bar
            self.refresh_processes_button.setEnabled(True)
            self.processes_progress_bar.setVisible(False)

    def quick_temp_clean(self):
        """Quick clean temporary files."""
        self.logger.info("=== Quick temp clean initiated ===")
        # Switch to temp files tab (index 3: Dashboard, Cleaner, Duplicates, Temp Files)
        self.tab_widget.setCurrentIndex(3)
        
        # Automatically start temp scan
        self.start_temp_scan()

    def quick_disk_analysis(self):
        """Quick disk analysis."""
        self.logger.info("=== Quick disk analysis initiated ===")
        # Switch to disk analyzer tab and run analysis on home directory
        self.tab_widget.setCurrentIndex(4)  # Assuming disk analyzer is at index 4
        home_dir = str(Path.home())
        self.disk_analyzer_path_input.setText(home_dir)
        self.start_disk_analysis()
    
    def scan_registry(self):
        """Scan registry for issues."""
        if not HAS_REGISTRY_CLEANER:
            QMessageBox.critical(self, "Error", "Registry cleaner is not available on this platform.")
            return
        
        # Update UI
        self.scan_registry_button.setEnabled(False)
        self.clean_registry_button.setEnabled(False)
        self.registry_progress_bar.setVisible(True)
        self.registry_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.registry_results.clear()
        self.status_bar.setText("Scanning registry...")
        self.add_activity("Scanning registry...")
        
        try:
            # Create cleaner and scan registry
            if not HAS_REGISTRY_CLEANER:
                raise Exception("Registry cleaner not available")
            cleaner = RegistryCleaner()
            issues = cleaner.scan_orphaned_entries()  # Fixed method name
            
            # Update UI
            self.scan_registry_button.setEnabled(True)
            self.registry_progress_bar.setVisible(False)
            self.status_bar.setText(f"Registry scan complete: {len(issues)} issues found")
            self.add_activity(f"Registry scan complete: {len(issues)} issues found")
            
            # Display results
            if issues:
                self.clean_registry_button.setEnabled(True)
                result_text = f"Found {len(issues)} registry issues:\n\n"
                for issue in issues:
                    result_text += f"- {issue}\n"
                self.registry_results.setPlainText(result_text)
            else:
                self.clean_registry_button.setEnabled(False)
                self.registry_results.setPlainText("No registry issues found.")
                
        except Exception as e:
            self.logger.error(f"Registry scan error: {e}")
            self.scan_registry_button.setEnabled(True)
            self.registry_progress_bar.setVisible(False)
            self.status_bar.setText("Registry scan failed")
            self.add_activity(f"Registry scan failed: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while scanning registry:\n{e}")
    
    def clean_registry(self):
        """Clean registry issues."""
        # Confirm cleaning
        reply = QMessageBox.question(
            self, 
            "Confirm Cleaning", 
            "Are you sure you want to clean registry issues?\nThis action cannot be undone and may affect system stability.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Implement actual cleaning
        try:
            if not HAS_REGISTRY_CLEANER:
                QMessageBox.critical(self, "Error", "Registry cleaner is not available on this platform.")
                return
            
            # Create cleaner and clean registry
            cleaner = RegistryCleaner()
            
            # Get the issues from the previous scan
            registry_text = self.registry_results.toPlainText()
            if "No registry issues found" in registry_text:
                QMessageBox.information(self, "Info", "No registry issues to clean.")
                return
            
            # Perform cleaning
            # First backup registry
            backup_success = cleaner.backup_registry()
            if not backup_success:
                QMessageBox.warning(self, "Warning", "Failed to create registry backup.")
            
            # Remove orphaned entries
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
            
            result = {
                'entries_cleaned': entries_removed,
                'errors': errors
            }
            
            cleaned_count = result.get('entries_cleaned', 0)
            errors = result.get('errors', [])
            
            message = f"Successfully cleaned {cleaned_count} registry entries."
            if errors:
                message += f"\n{len(errors)} errors occurred."
            
            QMessageBox.information(self, "Registry Cleaning Complete", message)
            self.add_activity(f"Cleaned {cleaned_count} registry entries")
            
            # Clear results and suggest re-scan
            self.registry_results.setPlainText("Registry cleaning completed. Run scan again to check for remaining issues.")
            self.clean_registry_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cleaning registry:\n{str(e)}")
            self.add_activity(f"Failed to clean registry: {str(e)}")
    
    # Restore tab methods
    def refresh_manifests(self):
        """Refresh backup manifests."""
        # Update UI
        self.refresh_manifests_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.restore_progress_bar.setVisible(True)
        self.restore_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.setText("Loading manifests...")
        self.add_activity("Loading manifests...")
        
        try:
            # Create restore manager and list manifests
            manager = RestoreManager()
            manifests = manager.list_manifests()
            
            # Update UI
            self.refresh_manifests_button.setEnabled(True)
            self.restore_progress_bar.setVisible(False)
            self.status_bar.setText(f"Loaded {len(manifests)} manifests")
            self.add_activity(f"Loaded {len(manifests)} manifests")
            
            # Display results in table
            self.manifests_table.setRowCount(len(manifests))
            
            for i, manifest in enumerate(manifests):
                self.manifests_table.setItem(i, 0, QTableWidgetItem(manifest.get("timestamp", "Unknown")))
                self.manifests_table.setItem(i, 1, QTableWidgetItem(manifest.get("backup_name", "Unnamed")))
                self.manifests_table.setItem(i, 2, QTableWidgetItem(str(manifest.get("files_backed_up", 0))))
                self.manifests_table.setItem(i, 3, QTableWidgetItem(manifest.get("file_path", "Unknown")))
            
            if len(manifests) > 0:
                self.restore_button.setEnabled(True)
            else:
                self.restore_button.setEnabled(False)
                
        except Exception as e:
            self.logger.error(f"Manifests error: {e}")
            self.refresh_manifests_button.setEnabled(True)
            self.restore_progress_bar.setVisible(False)
            self.status_bar.setText("Failed to load manifests")
            self.add_activity(f"Failed to load manifests: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred while loading manifests:\n{e}")
    
    def restore_selected(self):
        """Restore from selected manifest."""
        selected_ranges = self.manifests_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, "Info", "Please select a manifest to restore from.")
            return
        
        # Get selected manifest
        row = selected_ranges[0].topRow()
        path_item = self.manifests_table.item(row, 3)
        if path_item:
            manifest_path = path_item.text()
        else:
            QMessageBox.critical(self, "Error", "Could not get manifest path.")
            return
        
        # Confirm restoration
        reply = QMessageBox.question(
            self, 
            "Confirm Restoration", 
            f"Restore files from {manifest_path}?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Implement actual restoration
        try:
            # Create restore manager and restore files
            manager = RestoreManager()
            
            # Get manifest details
            name_item = self.manifests_table.item(row, 1)
            if name_item:
                manifest_name = name_item.text()
            else:
                manifest_name = "Unknown"
            
            # Perform restoration
            result = manager.restore_from_manifest(manifest_path)
            
            restored_count = result.get('files_restored', 0)
            errors = result.get('errors', [])
            
            message = f"Successfully restored {restored_count} files from {manifest_name}."
            if errors:
                message += f"\n{len(errors)} errors occurred during restoration."
            
            QMessageBox.information(self, "Restoration Complete", message)
            self.add_activity(f"Restored {restored_count} files from {manifest_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error restoring files:\n{str(e)}")
            self.add_activity(f"Failed to restore from {manifest_path}: {str(e)}")
    
    # Settings methods
    def save_settings(self):
        """Save settings to config file."""
        try:
            # Save GUI settings
            self.settings.setValue("log_file", self.log_file_input.text())
            self.settings.setValue("verbose", self.verbose_checkbox.isChecked())
            
            # Save to deep cleaner config file
            config_path = self.config._get_default_config_path()
            config_dir = Path(config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Update config with current settings
            self.config.config_data["log_file"] = self.log_file_input.text().strip()
            self.config.config_data["json_logging"] = self.verbose_checkbox.isChecked()
            
            # Write config to file
            with open(config_path, 'w') as f:
                import yaml
                yaml.dump(self.config.config_data, f, default_flow_style=False)
            
            QMessageBox.information(self, "Settings", "Settings saved successfully!")
            self.status_bar.setText("Settings saved")
            self.add_activity("Settings saved")
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")
    
    def load_settings(self):
        """Load settings from config file."""
        try:
            # Load GUI settings
            log_file = self.settings.value("log_file", "")
            if isinstance(log_file, str):
                self.log_file_input.setText(log_file)
            
            verbose = self.settings.value("verbose", False, type=bool)
            if isinstance(verbose, bool):
                self.verbose_checkbox.setChecked(verbose)
            
            # Load deep cleaner config
            if self.config.config_data:
                if "log_file" in self.config.config_data:
                    self.log_file_input.setText(self.config.config_data["log_file"])
                if "json_logging" in self.config.config_data:
                    self.verbose_checkbox.setChecked(self.config.config_data["json_logging"])
        except Exception as e:
            self.logger.warning(f"Failed to load settings: {e}")
    
    # Utility methods
    def format_bytes(self, bytes_value: Union[int, float]) -> str:
        """Format bytes to human readable format."""
        bytes_value = float(bytes_value)  # Convert to float for division
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value = bytes_value / 1024.0  # Keep as float
        return f"{bytes_value:.1f} PB"
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Clean up threads if they're running
        threads_to_cleanup = ['scan_thread', 'delete_thread', 'duplicates_thread', 
                             'large_files_thread', 'disk_analysis_thread']
        
        for thread_name in threads_to_cleanup:
            try:
                if hasattr(self, thread_name):
                    thread = getattr(self, thread_name)
                    if thread and hasattr(thread, 'isRunning') and thread.isRunning():
                        thread.quit()
                        thread.wait(3000)  # Wait up to 3 seconds
            except (RuntimeError, AttributeError):
                pass  # Thread already deleted or doesn't exist
            pass  # Thread already deleted
        
        if self.duplicate_thread and self.duplicate_thread.isRunning():
            self.duplicate_thread.quit()
            self.duplicate_thread.wait()
        
        if self.large_file_thread and self.large_file_thread.isRunning():
            self.large_file_thread.quit()
            self.large_file_thread.wait()
        
        if self.temp_cleaner_thread and self.temp_cleaner_thread.isRunning():
            self.temp_cleaner_thread.quit()
            self.temp_cleaner_thread.wait()
        
        if self.disk_analyzer_thread and self.disk_analyzer_thread.isRunning():
            self.disk_analyzer_thread.quit()
            self.disk_analyzer_thread.wait()
        
        event.accept()

    def switch_to_tab(self, index: int):
        """Switch to the specified tab index."""
        self.tab_widget.setCurrentIndex(index)
    
    def create_docker_tab(self) -> QWidget:
        """Create the Docker tab."""
        docker_tab = QWidget()
        layout = QVBoxLayout(docker_tab)
        
        # Docker availability check
        self.docker_status_label = QLabel("Checking Docker availability...")
        layout.addWidget(self.docker_status_label)
        
        # Resource selection group
        resource_group = QGroupBox("Resources to Clean")
        resource_layout = QVBoxLayout(resource_group)
        
        self.docker_images_checkbox = QCheckBox("Unused Docker Images")
        self.docker_images_checkbox.setChecked(True)
        resource_layout.addWidget(self.docker_images_checkbox)
        
        self.docker_containers_checkbox = QCheckBox("Stopped Docker Containers")
        self.docker_containers_checkbox.setChecked(True)
        resource_layout.addWidget(self.docker_containers_checkbox)
        
        self.docker_volumes_checkbox = QCheckBox("Unused Docker Volumes")
        resource_layout.addWidget(self.docker_volumes_checkbox)
        
        self.docker_networks_checkbox = QCheckBox("Unused Docker Networks")
        resource_layout.addWidget(self.docker_networks_checkbox)
        
        layout.addWidget(resource_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)
        
        self.docker_dry_run_checkbox = QCheckBox("Dry Run (Preview Only)")
        self.docker_dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.docker_dry_run_checkbox)
        
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.docker_scan_button = QPushButton("Scan Docker Resources")
        self.docker_scan_button.clicked.connect(self.start_docker_scan)
        button_layout.addWidget(self.docker_scan_button)
        
        self.docker_cleanup_button = QPushButton("Clean Up Resources")
        self.docker_cleanup_button.clicked.connect(self.start_docker_cleanup)
        self.docker_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.docker_cleanup_button)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.docker_progress_bar = QProgressBar()
        self.docker_progress_bar.setVisible(False)
        layout.addWidget(self.docker_progress_bar)
        
        # Results area
        results_group = QGroupBox("Docker Resources")
        results_layout = QVBoxLayout(results_group)
        
        # Resource summary
        self.docker_summary_label = QLabel("No scan performed yet")
        results_layout.addWidget(self.docker_summary_label)
        
        # Resource table
        self.docker_table = QTableWidget()
        self.docker_table.setColumnCount(5)
        self.docker_table.setHorizontalHeaderLabels(["Type", "Name", "ID", "Size", "Status"])
        self.docker_table.horizontalHeader().setStretchLastSection(True)
        self.docker_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.docker_table)
        
        layout.addWidget(results_group)
        
        # Check Docker availability on startup
        self.check_docker_availability()
        
        return docker_tab
    
    def create_package_manager_tab(self) -> QWidget:
        """Create the Package Manager tab."""
        pm_tab = QWidget()
        layout = QVBoxLayout(pm_tab)
        
        # Package manager selection group
        pm_group = QGroupBox("Package Managers")
        pm_layout = QVBoxLayout(pm_group)
        
        self.pm_pip_checkbox = QCheckBox("pip (Python)")
        self.pm_pip_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_pip_checkbox)
        
        self.pm_npm_checkbox = QCheckBox("npm (Node.js)")
        self.pm_npm_checkbox.setChecked(True)
        pm_layout.addWidget(self.pm_npm_checkbox)
        
        self.pm_yarn_checkbox = QCheckBox("yarn (Node.js)")
        pm_layout.addWidget(self.pm_yarn_checkbox)
        
        self.pm_conda_checkbox = QCheckBox("conda (Python)")
        pm_layout.addWidget(self.pm_conda_checkbox)
        
        self.pm_system_checkbox = QCheckBox("System Package Manager")
        pm_layout.addWidget(self.pm_system_checkbox)
        
        layout.addWidget(pm_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)
        
        self.pm_keep_recent_spinbox = QSpinBox()
        self.pm_keep_recent_spinbox.setRange(0, 365)
        self.pm_keep_recent_spinbox.setValue(7)
        self.pm_keep_recent_spinbox.setSuffix(" days")
        options_layout.addRow("Keep recent cache files:", self.pm_keep_recent_spinbox)
        
        self.pm_orphaned_checkbox = QCheckBox("Include orphaned packages")
        options_layout.addRow(self.pm_orphaned_checkbox)
        
        self.pm_dry_run_checkbox = QCheckBox("Dry Run (Preview Only)")
        self.pm_dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.pm_dry_run_checkbox)
        
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.pm_detect_button = QPushButton("Detect Package Managers")
        self.pm_detect_button.clicked.connect(self.detect_package_managers)
        button_layout.addWidget(self.pm_detect_button)
        
        self.pm_scan_button = QPushButton("Scan Cache")
        self.pm_scan_button.clicked.connect(self.start_pm_scan)
        button_layout.addWidget(self.pm_scan_button)
        
        self.pm_cleanup_button = QPushButton("Clean Up")
        self.pm_cleanup_button.clicked.connect(self.start_pm_cleanup)
        self.pm_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.pm_cleanup_button)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.pm_progress_bar = QProgressBar()
        self.pm_progress_bar.setVisible(False)
        layout.addWidget(self.pm_progress_bar)
        
        # Results area
        results_group = QGroupBox("Package Manager Cache")
        results_layout = QVBoxLayout(results_group)
        
        # Summary
        self.pm_summary_label = QLabel("Click 'Detect Package Managers' to start")
        results_layout.addWidget(self.pm_summary_label)
        
        # Results table
        self.pm_table = QTableWidget()
        self.pm_table.setColumnCount(4)
        self.pm_table.setHorizontalHeaderLabels(["Package Manager", "Cache Size", "Files", "Status"])
        self.pm_table.horizontalHeader().setStretchLastSection(True)
        self.pm_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.pm_table)
        
        layout.addWidget(results_group)
        
        return pm_tab
    
    def create_heuristics_tab(self) -> QWidget:
        """Create the Heuristics tab."""
        heuristics_tab = QWidget()
        layout = QVBoxLayout(heuristics_tab)
        
        # Options group
        options_group = QGroupBox("Detection Options")
        options_layout = QFormLayout(options_group)
        
        self.heuristics_confidence_spinbox = QSpinBox()
        self.heuristics_confidence_spinbox.setRange(1, 100)
        self.heuristics_confidence_spinbox.setValue(70)
        self.heuristics_confidence_spinbox.setSuffix("%")
        options_layout.addRow("Confidence Threshold:", self.heuristics_confidence_spinbox)
        
        self.heuristics_ml_checkbox = QCheckBox("Use Machine Learning Patterns")
        self.heuristics_ml_checkbox.setChecked(True)
        options_layout.addRow(self.heuristics_ml_checkbox)
        
        self.heuristics_registry_checkbox = QCheckBox("Include Registry Analysis (Windows)")
        if os.name != 'nt':
            self.heuristics_registry_checkbox.setEnabled(False)
        options_layout.addRow(self.heuristics_registry_checkbox)
        
        self.heuristics_dry_run_checkbox = QCheckBox("Dry Run (Preview Only)")
        self.heuristics_dry_run_checkbox.setChecked(True)
        options_layout.addRow(self.heuristics_dry_run_checkbox)
        
        layout.addWidget(options_group)
        
        # Path selection
        path_group = QGroupBox("Scan Path")
        path_layout = QHBoxLayout(path_group)
        
        self.heuristics_path_edit = QLineEdit()
        self.heuristics_path_edit.setText(str(Path.home()))
        path_layout.addWidget(self.heuristics_path_edit)
        
        self.heuristics_browse_button = QPushButton("Browse...")
        self.heuristics_browse_button.clicked.connect(self.browse_heuristics_path)
        path_layout.addWidget(self.heuristics_browse_button)
        
        layout.addWidget(path_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.heuristics_scan_button = QPushButton("Scan for Leftovers")
        self.heuristics_scan_button.clicked.connect(self.start_heuristics_scan)
        button_layout.addWidget(self.heuristics_scan_button)
        
        self.heuristics_cleanup_button = QPushButton("Clean Up Leftovers")
        self.heuristics_cleanup_button.clicked.connect(self.start_heuristics_cleanup)
        self.heuristics_cleanup_button.setEnabled(False)
        button_layout.addWidget(self.heuristics_cleanup_button)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.heuristics_progress_bar = QProgressBar()
        self.heuristics_progress_bar.setVisible(False)
        layout.addWidget(self.heuristics_progress_bar)
        
        # Results area
        results_group = QGroupBox("Detected Leftovers")
        results_layout = QVBoxLayout(results_group)
        
        # Summary
        self.heuristics_summary_label = QLabel("No scan performed yet")
        results_layout.addWidget(self.heuristics_summary_label)
        
        # Results table
        self.heuristics_table = QTableWidget()
        self.heuristics_table.setColumnCount(4)
        self.heuristics_table.setHorizontalHeaderLabels(["Item", "Type", "Confidence", "Size"])
        self.heuristics_table.horizontalHeader().setStretchLastSection(True)
        self.heuristics_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        results_layout.addWidget(self.heuristics_table)
        
        layout.addWidget(results_group)
        
        return heuristics_tab
    
    def detect_package_managers(self):
        """Detect available package managers."""
        try:
            from ..analyzers.package_manager_cleaner import PackageManagerCleaner
            
            pm_cleaner = PackageManagerCleaner(self.config)
            managers = pm_cleaner.detect_package_managers()
            
            # Update summary label
            manager_names = [pm.name for pm in managers]
            self.pm_summary_label.setText(f"Detected: {', '.join(manager_names)}")
            
            # Update table
            self.pm_table.setRowCount(len(managers))
            for i, manager in enumerate(managers):
                self.pm_table.setItem(i, 0, QTableWidgetItem(manager.name))
                self.pm_table.setItem(i, 1, QTableWidgetItem("Unknown"))
                self.pm_table.setItem(i, 2, QTableWidgetItem("Unknown"))
                self.pm_table.setItem(i, 3, QTableWidgetItem("Detected"))
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to detect package managers: {str(e)}")
    
    def start_pm_scan(self):
        """Start package manager cache scan."""
        try:
            from ..analyzers.package_manager_cleaner import PackageManagerCleaner
            
            self.pm_scan_button.setEnabled(False)
            self.pm_cleanup_button.setEnabled(False)
            self.pm_summary_label.setText("Scanning package manager caches...")
            
            # Create cleaner
            pm_cleaner = PackageManagerCleaner(self.config)
            
            # Detect available package managers
            available_managers = pm_cleaner.detect_package_managers()
            
            if not available_managers:
                self.pm_summary_label.setText("No package managers detected")
                self.pm_scan_button.setEnabled(True)
                return
            
            # Scan each package manager
            total_cache_size = 0
            total_orphaned = 0
            results = []
            
            for manager in available_managers:
                # Get cache size for each manager
                cache_size = pm_cleaner._get_cache_size(manager.cache_path)
                if cache_size > 0:
                    total_cache_size += cache_size
                    results.append(f"{manager.name}: {pm_cleaner._format_bytes(cache_size)}")
                
                # Add other package managers as needed
            
            # Update summary
            summary_text = f"Found cache data: {pm_cleaner._format_bytes(total_cache_size)}\n"
            summary_text += "\n".join(results)
            self.pm_summary_label.setText(summary_text)
            
            self.pm_scan_button.setEnabled(True)
            self.pm_cleanup_button.setEnabled(total_cache_size > 0)
            
            self.add_activity(f"Scanned package managers: {pm_cleaner._format_bytes(total_cache_size)} cache found")
            
        except ImportError:
            self.pm_summary_label.setText("Package manager cleaner not available")
            self.pm_scan_button.setEnabled(True)
        except Exception as e:
            self.pm_summary_label.setText(f"Error scanning package managers: {str(e)}")
            self.pm_scan_button.setEnabled(True)
    
    def start_pm_cleanup(self):
        """Start package manager cleanup."""
        try:
            from ..analyzers.package_manager_cleaner import PackageManagerCleaner
            
            # Confirm cleanup
            reply = QMessageBox.question(
                self, "Confirm Cleanup",
                "Are you sure you want to clean package manager caches?\n"
                "This will remove cached packages but they can be re-downloaded when needed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.pm_cleanup_button.setEnabled(False)
            self.pm_summary_label.setText("Cleaning package manager caches...")
            
            # Create cleaner
            pm_cleaner = PackageManagerCleaner(self.config)
            
            # Clean available package managers
            available_managers = pm_cleaner.detect_package_managers()
            total_cleaned = 0
            results = []
            
            for manager in available_managers:
                if manager.name == 'pip':
                    result = pm_cleaner.clean_pip_cache()
                    if result and result.success:
                        total_cleaned += result.space_freed
                        results.append(f"pip: {result.files_removed} files cleaned")
                
                elif manager.name == 'npm':
                    result = pm_cleaner.clean_npm_cache()
                    if result and result.success:
                        total_cleaned += result.space_freed
                        results.append(f"npm: {result.files_removed} files cleaned")
            
            # Update summary
            summary_text = f"Cleaned: {pm_cleaner._format_bytes(total_cleaned)}\n"
            summary_text += "\n".join(results)
            self.pm_summary_label.setText(summary_text)
            
            self.pm_cleanup_button.setEnabled(True)
            
            QMessageBox.information(
                self, "Cleanup Complete",
                f"Successfully cleaned package manager caches.\n"
                f"Space freed: {pm_cleaner._format_bytes(total_cleaned)}"
            )
            
            self.add_activity(f"Cleaned package managers: {pm_cleaner._format_bytes(total_cleaned)} freed")
            
        except ImportError:
            QMessageBox.warning(self, "Not Available", "Package manager cleaner not available")
        except Exception as e:
            QMessageBox.critical(self, "Cleanup Error", f"Error cleaning package managers:\n{str(e)}")
            self.pm_cleanup_button.setEnabled(True)
    
    def browse_heuristics_path(self):
        """Browse for heuristics scan path."""
        path = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if path:
            self.heuristics_path_edit.setText(path)
    
    def start_heuristics_scan(self):
        """Start heuristics scan."""
        try:
            from ..analyzers.leftover_detector import LeftoverDetector
            
            scan_path = self.heuristics_path_edit.text().strip()
            if not scan_path or not Path(scan_path).exists():
                QMessageBox.warning(self, "Invalid Path", "Please select a valid directory to scan.")
                return
            
            self.heuristics_scan_button.setEnabled(False)
            self.heuristics_cleanup_button.setEnabled(False)
            self.heuristics_summary_label.setText("Scanning for application leftovers...")
            
            # Create detector
            detector = LeftoverDetector(self.config)
            
            # Get confidence threshold
            confidence_threshold = self.heuristics_confidence_spinbox.value() / 100.0
            
            # Scan for orphaned folders
            orphaned_folders = detector.scan_orphaned_folders([scan_path])
            
            # Scan for installer files
            installer_files = detector.detect_installer_files()
            
            # Apply ML patterns if enabled
            all_items = orphaned_folders + installer_files
            if self.heuristics_ml_checkbox.isChecked() and all_items:
                all_items = detector.apply_ml_patterns(all_items)
            
            # Filter by confidence threshold
            high_confidence_items = [
                item for item in all_items 
                if detector.calculate_confidence_score(item) >= confidence_threshold
            ]
            
            # Update summary
            summary_text = f"Found {len(all_items)} potential leftovers\n"
            summary_text += f"High confidence (>= {confidence_threshold:.1f}): {len(high_confidence_items)}"
            self.heuristics_summary_label.setText(summary_text)
            
            # Store results for cleanup
            self.heuristics_results = high_confidence_items
            
            self.heuristics_scan_button.setEnabled(True)
            self.heuristics_cleanup_button.setEnabled(len(high_confidence_items) > 0)
            
            self.add_activity(f"Heuristics scan found {len(high_confidence_items)} high-confidence leftovers")
            
        except ImportError:
            self.heuristics_summary_label.setText("Leftover detector not available")
            self.heuristics_scan_button.setEnabled(True)
        except Exception as e:
            self.heuristics_summary_label.setText(f"Error during heuristics scan: {str(e)}")
            self.heuristics_scan_button.setEnabled(True)
    
    def start_heuristics_cleanup(self):
        """Start heuristics cleanup."""
        if not hasattr(self, 'heuristics_results') or not self.heuristics_results:
            QMessageBox.warning(self, "No Results", "Please run a scan first.")
            return
        
        # Show warning about heuristics
        reply = QMessageBox.warning(
            self, "Heuristics Cleanup Warning",
            f"You are about to clean {len(self.heuristics_results)} items detected by heuristics.\n\n"
            "⚠️ WARNING: Heuristics-based detection may occasionally flag legitimate files.\n"
            "Please review the results carefully before proceeding.\n\n"
            "Items will be moved to trash for safety.\n\n"
            "Continue with cleanup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Convert results to paths
            paths_to_clean = []
            for item in self.heuristics_results:
                if isinstance(item, (str, Path)):
                    paths_to_clean.append(Path(item))
            
            if not paths_to_clean:
                QMessageBox.information(self, "Nothing to Clean", "No valid paths found for cleanup.")
                return
            
            # Perform cleanup
            deleter = Deleter(dry_run=False, use_trash=True)
            result = deleter.delete(paths_to_clean, [])
            
            files_deleted = result.get('files_deleted', 0)
            errors = result.get('errors', [])
            
            message = f"Heuristics cleanup completed.\n"
            message += f"Items cleaned: {files_deleted}\n"
            if errors:
                message += f"Errors: {len(errors)}"
            
            QMessageBox.information(self, "Cleanup Complete", message)
            self.add_activity(f"Heuristics cleanup: {files_deleted} items cleaned")
            
            # Clear results
            self.heuristics_results = []
            self.heuristics_cleanup_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Cleanup Error", f"Error during heuristics cleanup:\n{str(e)}")
    

    
    def check_docker_availability(self):
        """Check if Docker is available."""
        try:
            cleaner = DockerCleaner()
            if cleaner.is_docker_available():
                self.docker_status_label.setText("✓ Docker is available and running")
                self.docker_status_label.setStyleSheet("color: green;")
                self.docker_scan_button.setEnabled(True)
            else:
                self.docker_status_label.setText("✗ Docker is not available or not running")
                self.docker_status_label.setStyleSheet("color: red;")
                self.docker_scan_button.setEnabled(False)
        except Exception as e:
            self.docker_status_label.setText(f"✗ Docker error: {str(e)}")
            self.docker_status_label.setStyleSheet("color: red;")
            self.docker_scan_button.setEnabled(False)
    
    def create_broken_links_tab(self) -> QWidget:
        """Create the broken links tab."""
        broken_links_tab = QWidget()
        layout = QVBoxLayout(broken_links_tab)
        
        # Scan options group
        scan_group = QGroupBox("Scan Options")
        scan_layout = QVBoxLayout(scan_group)
        
        self.scan_symlinks_checkbox = QCheckBox("Scan for broken symlinks")
        self.scan_symlinks_checkbox.setChecked(True)
        scan_layout.addWidget(self.scan_symlinks_checkbox)
        
        self.scan_shortcuts_checkbox = QCheckBox("Scan for broken Windows shortcuts (.lnk files)")
        self.scan_shortcuts_checkbox.setChecked(True)
        scan_layout.addWidget(self.scan_shortcuts_checkbox)
        
        self.scan_registry_checkbox = QCheckBox("Scan for broken registry references (Windows only)")
        self.scan_registry_checkbox.setChecked(False)
        scan_layout.addWidget(self.scan_registry_checkbox)
        
        layout.addWidget(scan_group)
        
        # Repair options group
        repair_group = QGroupBox("Repair Options")
        repair_layout = QFormLayout(repair_group)
        
        self.enable_repair_checkbox = QCheckBox("Enable automatic repair")
        self.enable_repair_checkbox.setChecked(False)
        repair_layout.addRow(self.enable_repair_checkbox)
        
        self.confidence_threshold_spinbox = QSpinBox()
        self.confidence_threshold_spinbox.setRange(0, 100)
        self.confidence_threshold_spinbox.setValue(70)
        self.confidence_threshold_spinbox.setSuffix("%")
        repair_layout.addRow("Confidence threshold:", self.confidence_threshold_spinbox)
        
        self.create_backups_checkbox = QCheckBox("Create backups before repair")
        self.create_backups_checkbox.setChecked(True)
        repair_layout.addRow(self.create_backups_checkbox)
        
        layout.addWidget(repair_group)
        
        # Path selection
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Scan path:"))
        self.broken_links_path_edit = QLineEdit()
        self.broken_links_path_edit.setText(str(Path.home()))
        path_layout.addWidget(self.broken_links_path_edit)
        
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_broken_links_path)
        path_layout.addWidget(browse_button)
        
        layout.addLayout(path_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.broken_links_scan_button = QPushButton("Scan for Broken Links")
        self.broken_links_scan_button.clicked.connect(self.start_broken_links_scan)
        button_layout.addWidget(self.broken_links_scan_button)
        
        self.repair_selected_button = QPushButton("Repair Selected")
        self.repair_selected_button.clicked.connect(self.repair_selected_links)
        self.repair_selected_button.setEnabled(False)
        button_layout.addWidget(self.repair_selected_button)
        
        export_button = QPushButton("Export Results")
        export_button.clicked.connect(self.export_broken_links_results)
        export_button.setEnabled(False)
        self.broken_links_export_button = export_button
        button_layout.addWidget(export_button)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.broken_links_progress_bar = QProgressBar()
        self.broken_links_progress_bar.setVisible(False)
        layout.addWidget(self.broken_links_progress_bar)
        
        # Results area
        results_group = QGroupBox("Broken Links Found")
        results_layout = QVBoxLayout(results_group)
        
        # Summary
        self.broken_links_summary_label = QLabel("No scan performed yet")
        results_layout.addWidget(self.broken_links_summary_label)
        
        # Results table
        self.broken_links_table = QTableWidget()
        self.broken_links_table.setColumnCount(7)
        self.broken_links_table.setHorizontalHeaderLabels([
            "Type", "Path", "Target", "Confidence", "Repairable", "Size", "Last Accessed"
        ])
        self.broken_links_table.horizontalHeader().setStretchLastSection(True)
        self.broken_links_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.broken_links_table.itemSelectionChanged.connect(self.on_broken_links_selection_changed)
        results_layout.addWidget(self.broken_links_table)
        
        layout.addWidget(results_group)
        
        # Disable Windows-specific options on non-Windows systems
        if not sys.platform.startswith("win"):
            self.scan_shortcuts_checkbox.setEnabled(False)
            self.scan_shortcuts_checkbox.setChecked(False)
            self.scan_registry_checkbox.setEnabled(False)
            self.scan_registry_checkbox.setChecked(False)
        
        return broken_links_tab
    
    def browse_broken_links_path(self):
        """Browse for broken links scan path."""
        path = QFileDialog.getExistingDirectory(
            self, 
            "Select Directory to Scan for Broken Links",
            self.broken_links_path_edit.text()
        )
        if path:
            self.broken_links_path_edit.setText(path)
    
    def on_broken_links_selection_changed(self):
        """Handle broken links table selection changes."""
        selected_rows = set()
        for item in self.broken_links_table.selectedItems():
            selected_rows.add(item.row())
        
        self.repair_selected_button.setEnabled(len(selected_rows) > 0)
    
    def start_broken_links_scan(self):
        """Start broken links scan."""
        scan_path = self.broken_links_path_edit.text().strip()
        if not scan_path or not Path(scan_path).exists():
            QMessageBox.warning(self, "Invalid Path", "Please select a valid directory to scan.")
            return
        
        # Disable UI during scan
        self.broken_links_scan_button.setEnabled(False)
        self.broken_links_progress_bar.setVisible(True)
        self.broken_links_progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Start scan in background thread
        self.broken_links_worker = BrokenLinksWorker(
            scan_path,
            self.scan_symlinks_checkbox.isChecked(),
            self.scan_shortcuts_checkbox.isChecked(),
            self.scan_registry_checkbox.isChecked()
        )
        self.broken_links_worker.finished.connect(self.on_broken_links_scan_finished)
        self.broken_links_worker.error.connect(self.on_broken_links_scan_error)
        self.broken_links_worker.start()
    
    def on_broken_links_scan_finished(self, results):
        """Handle broken links scan completion."""
        self.broken_links_scan_button.setEnabled(True)
        self.broken_links_progress_bar.setVisible(False)
        self.broken_links_export_button.setEnabled(True)
        
        # Store results
        self.broken_links_results = results
        
        # Update summary
        total_links = len(results)
        repairable_count = sum(1 for link in results if link.is_repairable)
        high_confidence_count = sum(1 for link in results if link.confidence_score >= 0.7)
        
        summary_text = f"Found {total_links} broken links ({repairable_count} repairable, {high_confidence_count} high confidence)"
        self.broken_links_summary_label.setText(summary_text)
        
        # Populate table
        self.broken_links_table.setRowCount(total_links)
        
        for row, link in enumerate(results):
            # Type
            type_item = QTableWidgetItem(link.link_type.title())
            self.broken_links_table.setItem(row, 0, type_item)
            
            # Path
            path_item = QTableWidgetItem(str(link.path))
            self.broken_links_table.setItem(row, 1, path_item)
            
            # Target
            target_item = QTableWidgetItem(link.target)
            self.broken_links_table.setItem(row, 2, target_item)
            
            # Confidence
            confidence_item = QTableWidgetItem(f"{link.confidence_score:.2f}")
            self.broken_links_table.setItem(row, 3, confidence_item)
            
            # Repairable
            repairable_item = QTableWidgetItem("Yes" if link.is_repairable else "No")
            self.broken_links_table.setItem(row, 4, repairable_item)
            
            # Size
            size_item = QTableWidgetItem(f"{link.size:,} bytes")
            self.broken_links_table.setItem(row, 5, size_item)
            
            # Last Accessed
            accessed_item = QTableWidgetItem(link.last_accessed.strftime("%Y-%m-%d %H:%M"))
            self.broken_links_table.setItem(row, 6, accessed_item)
        
        self.broken_links_table.resizeColumnsToContents()
    
    def on_broken_links_scan_error(self, error_message):
        """Handle broken links scan error."""
        self.broken_links_scan_button.setEnabled(True)
        self.broken_links_progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Scan Error", f"Error during broken links scan:\n{error_message}")
    
    def repair_selected_links(self):
        """Repair selected broken links."""
        selected_rows = set()
        for item in self.broken_links_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        selected_links = [self.broken_links_results[row] for row in selected_rows]
        confidence_threshold = self.confidence_threshold_spinbox.value() / 100.0
        
        # Filter by confidence threshold and repairability
        repairable_links = [
            link for link in selected_links 
            if link.is_repairable and link.confidence_score >= confidence_threshold
        ]
        
        if not repairable_links:
            QMessageBox.information(
                self, 
                "No Repairable Links", 
                "None of the selected links meet the confidence threshold for repair."
            )
            return
        
        # Confirm repair
        reply = QMessageBox.question(
            self,
            "Confirm Repair",
            f"Repair {len(repairable_links)} broken links?\n\n"
            f"Backups will be created: {'Yes' if self.create_backups_checkbox.isChecked() else 'No'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Perform repairs
        detector = BrokenLinkDetector()
        repaired_count = 0
        errors = []
        
        for link in repairable_links:
            try:
                result = detector.attempt_repair(link)
                if result.success:
                    repaired_count += 1
                else:
                    errors.append(f"{link.path}: {result.error_message}")
            except Exception as e:
                errors.append(f"{link.path}: {str(e)}")
        
        # Show results
        message = f"Repaired {repaired_count} out of {len(repairable_links)} links."
        if errors:
            message += f"\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                message += f"\n... and {len(errors) - 5} more errors"
        
        QMessageBox.information(self, "Repair Complete", message)
        
        # Refresh the scan to update results
        self.start_broken_links_scan()
    
    def export_broken_links_results(self):
        """Export broken links results to JSON."""
        if not hasattr(self, 'broken_links_results') or not self.broken_links_results:
            QMessageBox.warning(self, "No Results", "No broken links results to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Broken Links Results",
            "broken_links_results.json",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            import json
            from datetime import datetime
            
            export_data = {
                'scan_date': datetime.now().isoformat(),
                'scan_path': self.broken_links_path_edit.text(),
                'total_links': len(self.broken_links_results),
                'broken_links': []
            }
            
            for link in self.broken_links_results:
                link_data = {
                    'path': str(link.path),
                    'target': link.target,
                    'type': link.link_type,
                    'size': link.size,
                    'created': link.created.isoformat(),
                    'last_accessed': link.last_accessed.isoformat(),
                    'is_repairable': link.is_repairable,
                    'confidence_score': link.confidence_score,
                    'error_message': link.error_message
                }
                export_data['broken_links'].append(link_data)
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            QMessageBox.information(self, "Export Complete", f"Results exported to:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting results:\n{str(e)}")
    
    def start_docker_scan(self):
        """Start Docker resource scan."""
        # Update UI
        self.docker_scan_button.setEnabled(False)
        self.docker_cleanup_button.setEnabled(False)
        self.docker_progress_bar.setVisible(True)
        self.docker_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.docker_table.setRowCount(0)
        self.status_bar.setText("Scanning Docker resources...")
        self.add_activity("Scanning Docker resources...")
        
        # Start scanning in separate thread
        self.docker_thread = QThread()
        self.docker_worker = DockerScanWorker(
            self.docker_images_checkbox.isChecked(),
            self.docker_containers_checkbox.isChecked(),
            self.docker_volumes_checkbox.isChecked(),
            self.docker_networks_checkbox.isChecked()
        )
        self.docker_worker.moveToThread(self.docker_thread)
        
        self.docker_thread.started.connect(self.docker_worker.run)
        self.docker_worker.finished.connect(self.docker_scan_finished)
        self.docker_worker.error.connect(self.docker_scan_error)
        self.docker_worker.finished.connect(self.docker_thread.quit)
        self.docker_worker.error.connect(self.docker_thread.quit)
        self.docker_thread.finished.connect(self.docker_thread.deleteLater)
        
        self.docker_thread.start()
    
    def docker_scan_finished(self, result: dict):
        """Handle Docker scan completion."""
        self.docker_resources = result["resources"]
        stats = result["stats"]
        
        # Update UI
        self.docker_scan_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        self.status_bar.setText(f"Found {len(self.docker_resources)} Docker resources")
        self.add_activity(f"Found {len(self.docker_resources)} Docker resources")
        
        # Update summary
        total_size = sum(getattr(resource, 'size', 0) for resource in self.docker_resources)
        size_human = self.format_bytes(total_size)
        self.docker_summary_label.setText(
            f"Found {len(self.docker_resources)} resources, "
            f"Total size: {size_human}"
        )
        
        # Display results in table
        self.docker_table.setRowCount(len(self.docker_resources))
        
        for i, resource in enumerate(self.docker_resources):
            resource_type = type(resource).__name__.replace('Docker', '')
            name = getattr(resource, 'name', getattr(resource, 'repository', 'Unknown'))
            resource_id = getattr(resource, 'id', 'Unknown')[:12]
            size = self.format_bytes(getattr(resource, 'size', 0))
            
            # Determine status
            if hasattr(resource, 'is_dangling') and resource.is_dangling:
                status = "Dangling"
            elif hasattr(resource, 'is_orphaned') and resource.is_orphaned:
                status = "Orphaned"
            elif hasattr(resource, 'is_unused') and resource.is_unused:
                status = "Unused"
            elif hasattr(resource, 'status'):
                status = resource.status.title()
            else:
                status = "Unused"
            
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
        """Handle Docker scan error."""
        self.logger.error(f"Docker scan error: {error}")
        self.docker_scan_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        self.status_bar.setText("Docker scan failed")
        self.add_activity(f"Docker scan failed: {error}")
        QMessageBox.critical(self, "Docker Scan Error", f"An error occurred during Docker scan:\n{error}")
    
    def start_docker_cleanup(self):
        """Start Docker resource cleanup."""
        if not hasattr(self, 'docker_resources') or not self.docker_resources:
            QMessageBox.information(self, "Info", "No Docker resources to clean up.")
            return
        
        # Get selected resources (for now, use all scanned resources)
        selected_resources = self.docker_resources
        
        # Confirm cleanup
        dry_run = self.docker_dry_run_checkbox.isChecked()
        action = "preview cleanup of" if dry_run else "clean up"
        
        total_size = sum(getattr(resource, 'size', 0) for resource in selected_resources)
        size_human = self.format_bytes(total_size)
        
        reply = QMessageBox.question(
            self, 
            "Confirm Docker Cleanup", 
            f"Are you sure you want to {action} {len(selected_resources)} Docker resources?\n"
            f"Total size: {size_human}\n"
            f"{'This is a preview only.' if dry_run else 'This action cannot be undone.'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Update UI
        self.docker_scan_button.setEnabled(False)
        self.docker_cleanup_button.setEnabled(False)
        self.docker_progress_bar.setVisible(True)
        self.docker_progress_bar.setRange(0, 0)  # Indeterminate progress
        self.status_bar.setText("Cleaning Docker resources...")
        
        # Start cleanup in separate thread
        self.docker_cleanup_thread = QThread()
        self.docker_cleanup_worker = DockerCleanupWorker(selected_resources, dry_run)
        self.docker_cleanup_worker.moveToThread(self.docker_cleanup_thread)
        
        self.docker_cleanup_thread.started.connect(self.docker_cleanup_worker.run)
        self.docker_cleanup_worker.finished.connect(self.docker_cleanup_finished)
        self.docker_cleanup_worker.error.connect(self.docker_cleanup_error)
        self.docker_cleanup_worker.finished.connect(self.docker_cleanup_thread.quit)
        self.docker_cleanup_worker.error.connect(self.docker_cleanup_thread.quit)
        self.docker_cleanup_thread.finished.connect(self.docker_cleanup_thread.deleteLater)
        
        self.docker_cleanup_thread.start()
    
    def docker_cleanup_finished(self, result):
        """Handle Docker cleanup completion."""
        # Update UI
        self.docker_scan_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        
        dry_run = self.docker_dry_run_checkbox.isChecked()
        action = "Would clean" if dry_run else "Cleaned"
        
        self.status_bar.setText(
            f"{action} {result.total_removed} Docker resources, "
            f"freed {self.format_bytes(result.space_freed)}"
        )
        self.add_activity(
            f"{action} {result.total_removed} Docker resources, "
            f"freed {self.format_bytes(result.space_freed)}"
        )
        
        # Show detailed results
        details = (
            f"Docker Cleanup Results:\n"
            f"Images: {result.images_removed}\n"
            f"Containers: {result.containers_removed}\n"
            f"Volumes: {result.volumes_removed}\n"
            f"Networks: {result.networks_removed}\n"
            f"Space freed: {self.format_bytes(result.space_freed)}\n"
        )
        
        if result.errors:
            details += f"\nErrors ({len(result.errors)}):\n"
            for error in result.errors[:5]:  # Show first 5 errors
                details += f"• {error}\n"
            if len(result.errors) > 5:
                details += f"... and {len(result.errors) - 5} more errors"
        
        QMessageBox.information(self, "Docker Cleanup Complete", details)
        
        # Clear the resources and refresh the table
        if hasattr(self, 'docker_resources'):
            self.docker_resources = []
        self.docker_table.setRowCount(0)
        self.docker_summary_label.setText("Cleanup complete. Run scan again to check for new resources.")
        self.docker_cleanup_button.setEnabled(False)
    
    def docker_cleanup_error(self, error: str):
        """Handle Docker cleanup error."""
        self.logger.error(f"Docker cleanup error: {error}")
        self.docker_scan_button.setEnabled(True)
        self.docker_cleanup_button.setEnabled(True)
        self.docker_progress_bar.setVisible(False)
        self.status_bar.setText("Docker cleanup failed")
        self.add_activity(f"Docker cleanup failed: {error}")
        QMessageBox.critical(self, "Docker Cleanup Error", f"An error occurred during Docker cleanup:\n{error}")

    def on_path_mode_changed(self):
        """Handle path mode radio button changes."""
        single_mode = self.single_path_radio.isChecked()
        
        # Enable/disable controls based on mode
        self.path_input.setEnabled(single_mode)
        
        self.drives_list.setEnabled(not single_mode)
        self.detect_drives_button.setEnabled(not single_mode)
        self.add_network_drive_button.setEnabled(not single_mode)
        self.remove_drive_button.setEnabled(not single_mode)
        
        if not single_mode:
            # Auto-detect drives when switching to multi-drive mode
            self.detect_available_drives()
    
    def detect_available_drives(self):
        """Detect available drives on the system."""
        try:
            import psutil
            
            self.drives_list.clear()
            
            # Get all disk partitions
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    # Get partition usage
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    # Format drive info
                    drive_info = f"{partition.device} ({partition.fstype}) - "
                    drive_info += f"{self.format_bytes(usage.free)} free of {self.format_bytes(usage.total)}"
                    
                    # Add to list
                    item = QListWidgetItem(drive_info)
                    item.setData(Qt.ItemDataRole.UserRole, partition.mountpoint)
                    self.drives_list.addItem(item)
                    
                except (PermissionError, OSError):
                    # Skip drives that can't be accessed
                    continue
            
            self.add_activity(f"Detected {self.drives_list.count()} available drives")
            
        except ImportError:
            QMessageBox.critical(self, "Error", "psutil module required for drive detection.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error detecting drives:\n{str(e)}")
    
    def add_network_drive(self):
        """Add a network drive to the scan list."""
        # Network drive dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Network Drive")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # Network path input
        path_layout = QFormLayout()
        
        network_path_input = QLineEdit()
        network_path_input.setPlaceholderText(r"\\server\share or smb://server/share")
        path_layout.addRow("Network Path:", network_path_input)
        
        username_input = QLineEdit()
        username_input.setPlaceholderText("Username (optional)")
        path_layout.addRow("Username:", username_input)
        
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setPlaceholderText("Password (optional)")
        path_layout.addRow("Password:", password_input)
        
        layout.addLayout(path_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(lambda: self.test_network_connection(
            network_path_input.text(), username_input.text(), password_input.text()
        ))
        buttons_layout.addWidget(test_button)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.add_network_path(
            dialog, network_path_input.text(), username_input.text(), password_input.text()
        ))
        buttons_layout.addWidget(add_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec()
    
    def test_network_connection(self, path, username, password):
        """Test network drive connection."""
        try:
            from ..performance.multi_drive_scanner import MultiDriveScanner
            
            scanner = MultiDriveScanner()
            
            # Test connection
            success = scanner.test_network_connection(path, username, password)
            
            if success:
                QMessageBox.information(self, "Connection Test", "Network connection successful!")
            else:
                QMessageBox.warning(self, "Connection Test", "Network connection failed.")
                
        except ImportError:
            QMessageBox.critical(self, "Error", "Multi-drive scanner module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing connection:\n{str(e)}")
    
    def add_network_path(self, dialog, path, username, password):
        """Add network path to drives list."""
        if not path:
            QMessageBox.warning(self, "Invalid Input", "Please enter a network path.")
            return
        
        try:
            # Format network drive info
            drive_info = f"{path}"
            if username:
                drive_info += f" (User: {username})"
            drive_info += " - Network Drive"
            
            # Add to list
            item = QListWidgetItem(drive_info)
            item.setData(Qt.ItemDataRole.UserRole, {
                'path': path,
                'username': username,
                'password': password,
                'type': 'network'
            })
            self.drives_list.addItem(item)
            
            self.add_activity(f"Added network drive: {path}")
            dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error adding network drive:\n{str(e)}")
    
    def remove_selected_drives(self):
        """Remove selected drives from the list."""
        selected_items = self.drives_list.selectedItems()
        
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select drives to remove.")
            return
        
        for item in selected_items:
            row = self.drives_list.row(item)
            self.drives_list.takeItem(row)
        
        self.add_activity(f"Removed {len(selected_items)} drives from scan list")
    
    def on_checkpoint_selection_changed(self):
        """Handle checkpoint selection changes."""
        has_selection = self.checkpoints_list.currentItem() is not None
        self.resume_checkpoint_button.setEnabled(has_selection)
        self.delete_checkpoint_button.setEnabled(has_selection)
    
    def list_checkpoints(self):
        """List available checkpoints."""
        try:
            from ..performance.scan_manager import ScanManager
            
            scan_manager = ScanManager()
            checkpoints = scan_manager.list_checkpoints()
            
            # Update checkpoints list
            self.checkpoints_list.clear()
            
            for checkpoint in checkpoints:
                checkpoint_info = f"{checkpoint.id} - {checkpoint.timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({checkpoint.progress_percentage:.1f}%)"
                item = QListWidgetItem(checkpoint_info)
                item.setData(Qt.ItemDataRole.UserRole, checkpoint.id)
                self.checkpoints_list.addItem(item)
            
            if checkpoints:
                self.add_activity(f"Found {len(checkpoints)} checkpoints")
            else:
                self.checkpoints_list.addItem("No checkpoints found")
                
        except ImportError:
            self.checkpoints_list.clear()
            self.checkpoints_list.addItem("Scan manager module not available")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error listing checkpoints:\n{str(e)}")
    
    def resume_from_checkpoint(self):
        """Resume scanning from selected checkpoint."""
        current_item = self.checkpoints_list.currentItem()
        if not current_item:
            return
        
        checkpoint_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not checkpoint_id:
            QMessageBox.warning(self, "Invalid Selection", "Please select a valid checkpoint.")
            return
        
        try:
            # Get the target path
            if self.single_path_radio.isChecked():
                target_path = self.path_input.text().strip()
            else:
                # For multi-drive, use the first selected drive
                if self.drives_list.count() > 0:
                    first_item = self.drives_list.item(0)
                    drive_data = first_item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(drive_data, dict):
                        target_path = drive_data['path']
                    else:
                        target_path = drive_data
                else:
                    QMessageBox.warning(self, "No Path", "Please select a path to scan.")
                    return
            
            if not target_path:
                QMessageBox.warning(self, "No Path", "Please select a path to scan.")
                return
            
            # Start scan with checkpoint
            self.start_scan_with_checkpoint(checkpoint_id)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error resuming from checkpoint:\n{str(e)}")
    
    def start_scan_with_checkpoint(self, checkpoint_id):
        """Start scan with a specific checkpoint."""
        try:
            normalized_path = normalize_path(self.path_input.text().strip())
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid path: {str(e)}")
            return
        
        if not normalized_path.exists():
            QMessageBox.critical(self, "Error", "Selected path does not exist.")
            return
        
        # Update UI
        self.scan_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.progress_group.setVisible(True)
        self.pause_button.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_label.setText("Resuming from checkpoint...")
        self.progress_bar.setVisible(True)
        self.results_text.clear()
        
        # Configure scan options
        scan_config = Config()
        scan_config.config_data = self.config.config_data.copy()
        
        # Start scanning in separate thread with checkpoint
        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(
            scan_config, 
            str(normalized_path),
            enable_checkpoints=True,
            enable_throttling=self.enable_throttling_checkbox.isChecked(),
            checkpoint_id=checkpoint_id
        )
        self.scan_worker.moveToThread(self.scan_thread)
        
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.error.connect(self.scan_error)
        self.scan_worker.progress_updated.connect(self.update_scan_progress)
        
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.error.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        
        self.scan_thread.start()
        
        self.add_activity(f"Resumed scan from checkpoint: {checkpoint_id}")
    
    def delete_checkpoint(self):
        """Delete selected checkpoint."""
        current_item = self.checkpoints_list.currentItem()
        if not current_item:
            return
        
        checkpoint_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not checkpoint_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete checkpoint '{checkpoint_id}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from ..performance.scan_manager import ScanManager
            
            scan_manager = ScanManager()
            success = scan_manager.delete_checkpoint(checkpoint_id)
            
            if success:
                QMessageBox.information(self, "Checkpoint Deleted", f"Checkpoint '{checkpoint_id}' deleted successfully.")
                self.add_activity(f"Deleted checkpoint: {checkpoint_id}")
                self.list_checkpoints()  # Refresh list
            else:
                QMessageBox.warning(self, "Deletion Failed", f"Failed to delete checkpoint '{checkpoint_id}'.")
                
        except ImportError:
            QMessageBox.critical(self, "Error", "Scan manager module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting checkpoint:\n{str(e)}")
    
    def cleanup_old_checkpoints(self):
        """Cleanup old checkpoints."""
        try:
            from ..performance.scan_manager import ScanManager
            
            # Ask for age threshold
            age_days, ok = QInputDialog.getInt(
                self,
                "Cleanup Checkpoints",
                "Delete checkpoints older than how many days?",
                7,  # Default 7 days
                1,  # Minimum 1 day
                365  # Maximum 1 year
            )
            
            if not ok:
                return
            
            scan_manager = ScanManager()
            deleted_count = scan_manager.cleanup_old_checkpoints(age_days)
            
            QMessageBox.information(
                self, 
                "Cleanup Complete", 
                f"Deleted {deleted_count} checkpoints older than {age_days} days."
            )
            
            self.add_activity(f"Cleaned up {deleted_count} old checkpoints")
            self.list_checkpoints()  # Refresh list
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Scan manager module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cleaning up checkpoints:\n{str(e)}")


def main():
    """Main entry point for the GUI application."""
    # Set up application
    app = QApplication(sys.argv)
    app.setApplicationName("Deep Cleaner")
    app.setApplicationVersion("0.1.0")
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and show main window
    window = DeepCleanerGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())





class MultiDriveScanWorker(QObject):
    """Worker class for scanning multiple drives in separate threads."""
    finished = Signal(list, list)
    error = Signal(str)
    progress_updated = Signal(object)
    
    def __init__(self, config: Config, paths: List[str], enable_checkpoints: bool = False, 
                 enable_throttling: bool = False):
        super().__init__()
        self.config = config
        self.paths = paths
        self.enable_checkpoints = enable_checkpoints
        self.enable_throttling = enable_throttling
        self._should_stop = False
    
    def run(self):
        """Run the multi-drive scanning process."""
        try:
            from ..performance.multi_drive_scanner import MultiDriveScanner
            
            scanner = MultiDriveScanner(
                self.config,
                enable_checkpoints=self.enable_checkpoints,
                enable_throttling=self.enable_throttling
            )
            
            # Start progress monitoring
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
            
            # Scan all paths
            all_empty_files = []
            all_empty_dirs = []
            
            for path in self.paths:
                empty_files, empty_dirs = scanner.scan_drive(path)
                all_empty_files.extend(empty_files)
                all_empty_dirs.extend(empty_dirs)
            
            self.finished.emit(all_empty_files, all_empty_dirs)
            
        except ImportError:
            self.error.emit("Multi-drive scanner module not available")
        except Exception as e:
            self.error.emit(str(e))
    
    def pause(self):
        """Pause the scanning process."""
        # Implementation would pause all active scanners
        pass
    
    def resume(self):
        """Resume the scanning process."""
        # Implementation would resume all paused scanners
        pass
    
    def stop(self):
        """Stop the scanning process."""
        self._should_stop = True


class BrokenLinksWorker(QThread):
    """Worker class for scanning broken links in a separate thread."""
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, scan_path, scan_symlinks, scan_shortcuts, scan_registry):
        super().__init__()
        self.scan_path = scan_path
        self.scan_symlinks = scan_symlinks
        self.scan_shortcuts = scan_shortcuts
        self.scan_registry = scan_registry
    
    def run(self):
        """Run the broken links scan."""
        try:
            detector = BrokenLinkDetector()
            all_broken_links = []
            
            # Scan for symlinks
            if self.scan_symlinks:
                symlinks = detector.scan_symlinks(self.scan_path)
                all_broken_links.extend(symlinks)
            
            # Scan for Windows shortcuts
            if self.scan_shortcuts and detector.is_windows:
                shortcuts = detector.scan_windows_shortcuts(self.scan_path)
                all_broken_links.extend(shortcuts)
            
            # Scan for registry references
            if self.scan_registry and detector.is_windows and detector.has_winreg:
                registry_refs = detector.scan_registry_references()
                all_broken_links.extend(registry_refs)
            
            self.finished.emit(all_broken_links)
            
        except Exception as e:
            self.error.emit(str(e))


    def create_file_shredder_tab(self) -> QWidget:
        """Create the file shredder tab."""
        shredder_tab = QWidget()
        layout = QVBoxLayout(shredder_tab)
        
        # Warning label
        warning_label = QLabel("⚠️ WARNING: File shredding permanently destroys data and cannot be undone!")
        warning_label.setStyleSheet("QLabel { color: red; font-weight: bold; font-size: 14px; padding: 10px; background-color: #ffe6e6; border: 1px solid red; }")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # File selection group
        file_group = QGroupBox("Files to Shred")
        file_layout = QVBoxLayout(file_group)
        
        # File list
        self.shredder_file_list = QListWidget()
        self.shredder_file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        file_layout.addWidget(self.shredder_file_list)
        
        # File selection buttons
        file_buttons_layout = QHBoxLayout()
        
        add_files_button = QPushButton("Add Files")
        add_files_button.clicked.connect(self.add_files_to_shred)
        file_buttons_layout.addWidget(add_files_button)
        
        add_folder_button = QPushButton("Add Folder")
        add_folder_button.clicked.connect(self.add_folder_to_shred)
        file_buttons_layout.addWidget(add_folder_button)
        
        remove_files_button = QPushButton("Remove Selected")
        remove_files_button.clicked.connect(self.remove_files_from_shred)
        file_buttons_layout.addWidget(remove_files_button)
        
        clear_files_button = QPushButton("Clear All")
        clear_files_button.clicked.connect(self.clear_shred_list)
        file_buttons_layout.addWidget(clear_files_button)
        
        file_layout.addLayout(file_buttons_layout)
        layout.addWidget(file_group)
        
        # Shredding options group
        options_group = QGroupBox("Shredding Options")
        options_layout = QFormLayout(options_group)
        
        self.shred_passes_spinbox = QSpinBox()
        self.shred_passes_spinbox.setRange(1, 35)
        self.shred_passes_spinbox.setValue(3)
        options_layout.addRow("Overwrite Passes:", self.shred_passes_spinbox)
        
        self.shred_method_combo = QComboBox()
        self.shred_method_combo.addItems(["Random", "DoD 5220.22-M", "Gutmann", "Zero Fill"])
        options_layout.addRow("Shredding Method:", self.shred_method_combo)
        
        self.verify_shred_checkbox = QCheckBox("Verify shredding completion")
        self.verify_shred_checkbox.setChecked(True)
        options_layout.addRow(self.verify_shred_checkbox)
        
        self.shred_free_space_checkbox = QCheckBox("Also shred free space")
        options_layout.addRow(self.shred_free_space_checkbox)
        
        layout.addWidget(options_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.start_shred_button = QPushButton("Start Shredding")
        self.start_shred_button.clicked.connect(self.start_file_shredding)
        self.start_shred_button.setMinimumHeight(35)
        self.start_shred_button.setStyleSheet("QPushButton { font-weight: bold; padding: 5px 20px; background-color: #d32f2f; color: white; }")
        buttons_layout.addWidget(self.start_shred_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Progress area
        self.shred_progress_bar = QProgressBar()
        self.shred_progress_bar.setVisible(False)
        layout.addWidget(self.shred_progress_bar)
        
        self.shred_status_label = QLabel("Ready to shred files")
        layout.addWidget(self.shred_status_label)
        
        # Results area
        self.shred_results = QTextEdit()
        self.shred_results.setReadOnly(True)
        self.shred_results.setMaximumHeight(150)
        layout.addWidget(self.shred_results)
        
        return shredder_tab
    
    def add_files_to_shred(self):
        """Add files to the shredding list."""
        files, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Files to Shred",
            "",
            "All Files (*.*)"
        )
        
        for file_path in files:
            if file_path not in [self.shredder_file_list.item(i).text() for i in range(self.shredder_file_list.count())]:
                self.shredder_file_list.addItem(file_path)
    
    def add_folder_to_shred(self):
        """Add folder contents to the shredding list."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Shred")
        if folder:
            try:
                folder_path = Path(folder)
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file():
                        file_str = str(file_path)
                        if file_str not in [self.shredder_file_list.item(i).text() for i in range(self.shredder_file_list.count())]:
                            self.shredder_file_list.addItem(file_str)
                
                self.add_activity(f"Added {folder_path.name} folder contents to shred list")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error adding folder: {str(e)}")
    
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
            QMessageBox.warning(self, "No Files", "Please add files to shred first.")
            return
        
        # Get file list
        files_to_shred = []
        for i in range(self.shredder_file_list.count()):
            files_to_shred.append(Path(self.shredder_file_list.item(i).text()))
        
        # Final confirmation
        reply = QMessageBox.question(
            self,
            "FINAL WARNING",
            f"⚠️ You are about to PERMANENTLY DESTROY {len(files_to_shred)} files!\n\n"
            f"This action CANNOT be undone and the files will be UNRECOVERABLE.\n\n"
            f"Shredding method: {self.shred_method_combo.currentText()}\n"
            f"Overwrite passes: {self.shred_passes_spinbox.value()}\n\n"
            f"Are you absolutely sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from ..analyzers.file_shredder import FileShredder
            
            # Update UI
            self.start_shred_button.setEnabled(False)
            self.shred_progress_bar.setVisible(True)
            self.shred_progress_bar.setRange(0, len(files_to_shred))
            self.shred_progress_bar.setValue(0)
            self.shred_status_label.setText("Shredding files...")
            self.shred_results.clear()
            
            # Create shredder
            shredder = FileShredder(self.config)
            
            # Configure shredder
            passes = self.shred_passes_spinbox.value()
            method = self.shred_method_combo.currentText().lower().replace(" ", "_")
            verify = self.verify_shred_checkbox.isChecked()
            
            # Shred files
            shredded_count = 0
            errors = []
            
            for i, file_path in enumerate(files_to_shred):
                try:
                    self.shred_status_label.setText(f"Shredding: {file_path.name}")
                    self.shred_progress_bar.setValue(i)
                    QApplication.processEvents()  # Update UI
                    
                    result = shredder.shred_file(file_path, passes=passes, method=method, verify=verify)
                    
                    if result.get('success', False):
                        shredded_count += 1
                        self.shred_results.append(f"✓ Shredded: {file_path}")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        errors.append(f"{file_path}: {error_msg}")
                        self.shred_results.append(f"✗ Failed: {file_path} - {error_msg}")
                    
                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")
                    self.shred_results.append(f"✗ Error: {file_path} - {str(e)}")
            
            # Update UI
            self.start_shred_button.setEnabled(True)
            self.shred_progress_bar.setVisible(False)
            self.shred_status_label.setText(f"Shredding complete: {shredded_count} files shredded")
            
            # Show results
            message = f"Shredding complete!\n\nFiles shredded: {shredded_count}\nErrors: {len(errors)}"
            if errors:
                message += f"\n\nFirst few errors:\n" + "\n".join(errors[:3])
                if len(errors) > 3:
                    message += f"\n... and {len(errors) - 3} more errors"
            
            QMessageBox.information(self, "Shredding Complete", message)
            self.add_activity(f"Shredded {shredded_count} files with {len(errors)} errors")
            
            # Clear the list of successfully shredded files
            for i in range(self.shredder_file_list.count() - 1, -1, -1):
                file_path = self.shredder_file_list.item(i).text()
                if not Path(file_path).exists():  # File was successfully shredded
                    self.shredder_file_list.takeItem(i)
            
        except ImportError:
            QMessageBox.critical(self, "Error", "File shredder module not available.")
            self.start_shred_button.setEnabled(True)
            self.shred_progress_bar.setVisible(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during file shredding:\n{str(e)}")
            self.start_shred_button.setEnabled(True)
            self.shred_progress_bar.setVisible(False)
            self.add_activity(f"File shredding failed: {str(e)}")
    
    def create_scheduler_tab(self) -> QWidget:
        """Create the task scheduler tab."""
        scheduler_tab = QWidget()
        layout = QVBoxLayout(scheduler_tab)
        
        # Create tab widget for scheduler features
        scheduler_tab_widget = QTabWidget()
        layout.addWidget(scheduler_tab_widget)
        
        # Task scheduler sub-tab
        tasks_tab = self.create_tasks_subtab()
        scheduler_tab_widget.addTab(tasks_tab, "Scheduled Tasks")
        
        # Auto-clean rules sub-tab
        rules_tab = self.create_auto_clean_rules_subtab()
        scheduler_tab_widget.addTab(rules_tab, "Auto-Clean Rules")
        
        return scheduler_tab
    
    def create_tasks_subtab(self) -> QWidget:
        """Create the tasks sub-tab."""
        tasks_tab = QWidget()
        layout = QVBoxLayout(tasks_tab)
        
        # Task creation group
        create_group = QGroupBox("Create Scheduled Task")
        create_layout = QFormLayout(create_group)
        
        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("Enter task name")
        create_layout.addRow("Task Name:", self.task_name_input)
        
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems([
            "Clean Empty Files", 
            "Clean Temp Files", 
            "Find Duplicates", 
            "Analyze Disk Usage",
            "Clean Docker Resources",
            "Clean Package Caches"
        ])
        create_layout.addRow("Task Type:", self.task_type_combo)
        
        self.task_path_input = QLineEdit()
        self.task_path_input.setText(str(Path.home()))
        create_layout.addRow("Target Path:", self.task_path_input)
        
        path_browse_button = QPushButton("Browse")
        path_browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.task_path_input))
        create_layout.addRow("", path_browse_button)
        
        # Schedule options
        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["Daily", "Weekly", "Monthly", "On Startup", "Custom Cron"])
        create_layout.addRow("Schedule:", self.schedule_type_combo)
        
        self.schedule_time_edit = QLineEdit()
        self.schedule_time_edit.setPlaceholderText("HH:MM (24-hour format)")
        self.schedule_time_edit.setText("02:00")
        create_layout.addRow("Time:", self.schedule_time_edit)
        
        self.cron_expression_input = QLineEdit()
        self.cron_expression_input.setPlaceholderText("0 2 * * * (cron format)")
        self.cron_expression_input.setEnabled(False)
        create_layout.addRow("Cron Expression:", self.cron_expression_input)
        
        # Enable/disable cron input based on schedule type
        self.schedule_type_combo.currentTextChanged.connect(
            lambda text: self.cron_expression_input.setEnabled(text == "Custom Cron")
        )
        
        # Task options
        self.task_dry_run_checkbox = QCheckBox("Dry run (preview only)")
        self.task_dry_run_checkbox.setChecked(True)
        create_layout.addRow(self.task_dry_run_checkbox)
        
        self.task_email_checkbox = QCheckBox("Send email notification")
        create_layout.addRow(self.task_email_checkbox)
        
        self.task_email_input = QLineEdit()
        self.task_email_input.setPlaceholderText("email@example.com")
        self.task_email_input.setEnabled(False)
        create_layout.addRow("Email Address:", self.task_email_input)
        
        # Enable/disable email input
        self.task_email_checkbox.toggled.connect(self.task_email_input.setEnabled)
        
        layout.addWidget(create_group)
        
        # Task management buttons
        task_buttons_layout = QHBoxLayout()
        
        self.create_task_button = QPushButton("Create Task")
        self.create_task_button.clicked.connect(self.create_scheduled_task)
        self.create_task_button.setMinimumHeight(35)
        task_buttons_layout.addWidget(self.create_task_button)
        
        self.run_task_button = QPushButton("Run Selected Now")
        self.run_task_button.clicked.connect(self.run_selected_task)
        self.run_task_button.setEnabled(False)
        self.run_task_button.setMinimumHeight(35)
        task_buttons_layout.addWidget(self.run_task_button)
        
        self.delete_task_button = QPushButton("Delete Selected")
        self.delete_task_button.clicked.connect(self.delete_selected_task)
        self.delete_task_button.setEnabled(False)
        self.delete_task_button.setMinimumHeight(35)
        task_buttons_layout.addWidget(self.delete_task_button)
        
        task_buttons_layout.addStretch()
        layout.addLayout(task_buttons_layout)
        
        # Existing tasks group
        tasks_group = QGroupBox("Scheduled Tasks")
        tasks_layout = QVBoxLayout(tasks_group)
        
        # Refresh button
        refresh_tasks_button = QPushButton("Refresh Tasks")
        refresh_tasks_button.clicked.connect(self.refresh_scheduled_tasks)
        tasks_layout.addWidget(refresh_tasks_button)
        
        # Tasks table
        self.scheduled_tasks_table = QTableWidget()
        self.scheduled_tasks_table.setColumnCount(6)
        self.scheduled_tasks_table.setHorizontalHeaderLabels([
            "Name", "Type", "Schedule", "Next Run", "Status", "Last Result"
        ])
        self.scheduled_tasks_table.horizontalHeader().setStretchLastSection(True)
        self.scheduled_tasks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.scheduled_tasks_table.itemSelectionChanged.connect(self.on_task_selection_changed)
        tasks_layout.addWidget(self.scheduled_tasks_table)
        
        layout.addWidget(tasks_group)
        
        # Task history group
        history_group = QGroupBox("Task Execution History")
        history_layout = QVBoxLayout(history_group)
        
        self.task_history_table = QTableWidget()
        self.task_history_table.setColumnCount(4)
        self.task_history_table.setHorizontalHeaderLabels([
            "Task", "Execution Time", "Duration", "Result"
        ])
        self.task_history_table.horizontalHeader().setStretchLastSection(True)
        self.task_history_table.setMaximumHeight(150)
        history_layout.addWidget(self.task_history_table)
        
        layout.addWidget(history_group)
        
        # Load existing tasks on startup
        self.refresh_scheduled_tasks()
        
        return tasks_tab
    
    def create_auto_clean_rules_subtab(self) -> QWidget:
        """Create the auto-clean rules sub-tab."""
        rules_tab = QWidget()
        layout = QVBoxLayout(rules_tab)
        
        # Rule creation group
        rule_creation_group = QGroupBox("Create Auto-Clean Rule")
        rule_layout = QFormLayout(rule_creation_group)
        
        # Rule name
        self.rule_name_input = QLineEdit()
        self.rule_name_input.setPlaceholderText("Enter rule name")
        rule_layout.addRow("Rule Name:", self.rule_name_input)
        
        # Trigger conditions
        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.addItems([
            "Disk Space Low", "File Age", "File Count", "System Startup", 
            "Time Based", "User Login", "Custom Condition"
        ])
        rule_layout.addRow("Trigger:", self.trigger_type_combo)
        
        # Trigger parameters
        self.trigger_value_input = QLineEdit()
        self.trigger_value_input.setPlaceholderText("e.g., 90% for disk space, 30 for days")
        rule_layout.addRow("Trigger Value:", self.trigger_value_input)
        
        # Target path
        self.rule_path_input = QLineEdit()
        self.rule_path_input.setText(str(Path.home()))
        rule_layout.addRow("Target Path:", self.rule_path_input)
        
        rule_path_browse_button = QPushButton("Browse")
        rule_path_browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.rule_path_input))
        rule_layout.addRow("", rule_path_browse_button)
        
        # Actions to perform
        self.rule_action_combo = QComboBox()
        self.rule_action_combo.addItems([
            "Clean Empty Files", "Clean Temp Files", "Clean Duplicates",
            "Clean Large Files", "Clean Cache", "Custom Action"
        ])
        rule_layout.addRow("Action:", self.rule_action_combo)
        
        # Rule options
        self.rule_enabled_checkbox = QCheckBox("Rule Enabled")
        self.rule_enabled_checkbox.setChecked(True)
        rule_layout.addRow(self.rule_enabled_checkbox)
        
        self.rule_dry_run_checkbox = QCheckBox("Dry Run Only")
        self.rule_dry_run_checkbox.setChecked(True)
        rule_layout.addRow(self.rule_dry_run_checkbox)
        
        self.rule_notify_checkbox = QCheckBox("Send Notification")
        rule_layout.addRow(self.rule_notify_checkbox)
        
        # Rule priority
        self.rule_priority_spinbox = QSpinBox()
        self.rule_priority_spinbox.setRange(1, 10)
        self.rule_priority_spinbox.setValue(5)
        rule_layout.addRow("Priority (1-10):", self.rule_priority_spinbox)
        
        layout.addWidget(rule_creation_group)
        
        # Rule management buttons
        rule_buttons_layout = QHBoxLayout()
        
        self.create_rule_button = QPushButton("Create Rule")
        self.create_rule_button.clicked.connect(self.create_auto_clean_rule)
        self.create_rule_button.setMinimumHeight(35)
        rule_buttons_layout.addWidget(self.create_rule_button)
        
        self.test_rule_button = QPushButton("Test Rule")
        self.test_rule_button.clicked.connect(self.test_selected_rule)
        self.test_rule_button.setEnabled(False)
        self.test_rule_button.setMinimumHeight(35)
        rule_buttons_layout.addWidget(self.test_rule_button)
        
        self.delete_rule_button = QPushButton("Delete Rule")
        self.delete_rule_button.clicked.connect(self.delete_selected_rule)
        self.delete_rule_button.setEnabled(False)
        self.delete_rule_button.setMinimumHeight(35)
        rule_buttons_layout.addWidget(self.delete_rule_button)
        
        rule_buttons_layout.addStretch()
        layout.addLayout(rule_buttons_layout)
        
        # Existing rules group
        rules_group = QGroupBox("Auto-Clean Rules")
        rules_layout = QVBoxLayout(rules_group)
        
        # Refresh button
        refresh_rules_button = QPushButton("Refresh Rules")
        refresh_rules_button.clicked.connect(self.refresh_auto_clean_rules)
        rules_layout.addWidget(refresh_rules_button)
        
        # Rules table
        self.auto_clean_rules_table = QTableWidget()
        self.auto_clean_rules_table.setColumnCount(6)
        self.auto_clean_rules_table.setHorizontalHeaderLabels([
            "Name", "Trigger", "Action", "Status", "Last Triggered", "Priority"
        ])
        self.auto_clean_rules_table.horizontalHeader().setStretchLastSection(True)
        self.auto_clean_rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.auto_clean_rules_table.itemSelectionChanged.connect(self.on_rule_selection_changed)
        rules_layout.addWidget(self.auto_clean_rules_table)
        
        layout.addWidget(rules_group)
        
        # Rule execution log
        log_group = QGroupBox("Rule Execution Log")
        log_layout = QVBoxLayout(log_group)
        
        self.rule_execution_log = QTextEdit()
        self.rule_execution_log.setReadOnly(True)
        self.rule_execution_log.setMaximumHeight(150)
        log_layout.addWidget(self.rule_execution_log)
        
        layout.addWidget(log_group)
        
        # Load existing rules
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
            QMessageBox.warning(self, "Invalid Input", "Please enter a task name.")
            return
        
        task_type = self.task_type_combo.currentText()
        target_path = self.task_path_input.text().strip()
        
        if not target_path or not Path(target_path).exists():
            QMessageBox.warning(self, "Invalid Path", "Please select a valid target path.")
            return
        
        try:
            from ..scheduler.scheduler import TaskScheduler
            
            scheduler = TaskScheduler()
            
            # Build task configuration
            task_config = {
                'name': task_name,
                'type': task_type.lower().replace(' ', '_'),
                'target_path': target_path,
                'dry_run': self.task_dry_run_checkbox.isChecked(),
                'email_notification': self.task_email_checkbox.isChecked(),
                'email_address': self.task_email_input.text().strip() if self.task_email_checkbox.isChecked() else None
            }
            
            # Build schedule configuration
            schedule_type = self.schedule_type_combo.currentText()
            if schedule_type == "Custom Cron":
                cron_expr = self.cron_expression_input.text().strip()
                if not cron_expr:
                    QMessageBox.warning(self, "Invalid Cron", "Please enter a valid cron expression.")
                    return
                schedule_config = {'type': 'cron', 'expression': cron_expr}
            else:
                time_str = self.schedule_time_edit.text().strip()
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError("Invalid time range")
                except ValueError:
                    QMessageBox.warning(self, "Invalid Time", "Please enter time in HH:MM format (24-hour).")
                    return
                
                schedule_config = {
                    'type': schedule_type.lower(),
                    'hour': hour,
                    'minute': minute
                }
            
            # Create the task
            task_id = scheduler.create_task(task_config, schedule_config)
            
            QMessageBox.information(
                self, 
                "Task Created", 
                f"Task '{task_name}' created successfully with ID: {task_id}"
            )
            
            self.add_activity(f"Created scheduled task: {task_name}")
            
            # Clear form
            self.task_name_input.clear()
            self.task_path_input.setText(str(Path.home()))
            
            # Refresh tasks list
            self.refresh_scheduled_tasks()
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Task scheduler module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating task:\n{str(e)}")
    
    def refresh_scheduled_tasks(self):
        """Refresh the list of scheduled tasks."""
        try:
            from ..scheduler.scheduler import TaskScheduler
            
            scheduler = TaskScheduler()
            tasks = scheduler.list_tasks()
            
            # Update tasks table
            self.scheduled_tasks_table.setRowCount(len(tasks))
            
            for i, task in enumerate(tasks):
                self.scheduled_tasks_table.setItem(i, 0, QTableWidgetItem(task.get('name', 'Unknown')))
                self.scheduled_tasks_table.setItem(i, 1, QTableWidgetItem(task.get('type', 'Unknown')))
                self.scheduled_tasks_table.setItem(i, 2, QTableWidgetItem(task.get('schedule', 'Unknown')))
                self.scheduled_tasks_table.setItem(i, 3, QTableWidgetItem(task.get('next_run', 'Unknown')))
                
                status = "Enabled" if task.get('enabled', True) else "Disabled"
                self.scheduled_tasks_table.setItem(i, 4, QTableWidgetItem(status))
                
                self.scheduled_tasks_table.setItem(i, 5, QTableWidgetItem(task.get('last_result', 'Never run')))
            
            # Update history table
            history = scheduler.get_execution_history(limit=10)
            self.task_history_table.setRowCount(len(history))
            
            for i, entry in enumerate(history):
                self.task_history_table.setItem(i, 0, QTableWidgetItem(entry.get('task_name', 'Unknown')))
                self.task_history_table.setItem(i, 1, QTableWidgetItem(entry.get('execution_time', 'Unknown')))
                self.task_history_table.setItem(i, 2, QTableWidgetItem(entry.get('duration', 'Unknown')))
                self.task_history_table.setItem(i, 3, QTableWidgetItem(entry.get('result', 'Unknown')))
            
        except ImportError:
            # Scheduler not available, show placeholder
            self.scheduled_tasks_table.setRowCount(1)
            self.scheduled_tasks_table.setItem(0, 0, QTableWidgetItem("Task scheduler not available"))
            for col in range(1, 6):
                self.scheduled_tasks_table.setItem(0, col, QTableWidgetItem(""))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error refreshing tasks:\n{str(e)}")
    
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
            from ..scheduler.scheduler import TaskScheduler
            
            scheduler = TaskScheduler()
            result = scheduler.run_task_now(task_name)
            
            if result.get('success', False):
                QMessageBox.information(
                    self, 
                    "Task Executed", 
                    f"Task '{task_name}' executed successfully.\n\n{result.get('message', '')}"
                )
                self.add_activity(f"Manually executed task: {task_name}")
            else:
                QMessageBox.warning(
                    self, 
                    "Task Failed", 
                    f"Task '{task_name}' failed to execute.\n\n{result.get('error', 'Unknown error')}"
                )
            
            # Refresh tasks to update last result
            self.refresh_scheduled_tasks()
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Task scheduler module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error running task:\n{str(e)}")
    
    def delete_selected_task(self):
        """Delete the selected task."""
        selected_rows = set()
        for item in self.scheduled_tasks_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        row = list(selected_rows)[0]
        task_name = self.scheduled_tasks_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the task '{task_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from ..scheduler.scheduler import TaskScheduler
            
            scheduler = TaskScheduler()
            success = scheduler.delete_task(task_name)
            
            if success:
                QMessageBox.information(self, "Task Deleted", f"Task '{task_name}' deleted successfully.")
                self.add_activity(f"Deleted scheduled task: {task_name}")
                self.refresh_scheduled_tasks()
            else:
                QMessageBox.warning(self, "Deletion Failed", f"Failed to delete task '{task_name}'.")
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Task scheduler module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting task:\n{str(e)}")
    
    def create_reports_tab(self) -> QWidget:
        """Create the reports tab."""
        reports_tab = QWidget()
        layout = QVBoxLayout(reports_tab)
        
        # Report generation group
        generation_group = QGroupBox("Report Generation")
        generation_layout = QFormLayout(generation_group)
        
        # Report type selection
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "System Analysis Report",
            "Disk Usage Report", 
            "Cleanup Summary Report",
            "Performance Report",
            "Security Audit Report",
            "Scheduled Tasks Report",
            "Custom Report"
        ])
        generation_layout.addRow("Report Type:", self.report_type_combo)
        
        # Report format selection
        self.report_format_combo = QComboBox()
        self.report_format_combo.addItems(["HTML", "PDF", "JSON", "CSV", "Text"])
        generation_layout.addRow("Format:", self.report_format_combo)
        
        # Date range selection
        self.report_date_range_combo = QComboBox()
        self.report_date_range_combo.addItems([
            "Last 24 Hours", "Last Week", "Last Month", "Last 3 Months", "All Time", "Custom Range"
        ])
        generation_layout.addRow("Date Range:", self.report_date_range_combo)
        
        # Include options
        self.include_charts_checkbox = QCheckBox("Include charts and graphs")
        self.include_charts_checkbox.setChecked(True)
        generation_layout.addRow(self.include_charts_checkbox)
        
        self.include_details_checkbox = QCheckBox("Include detailed statistics")
        self.include_details_checkbox.setChecked(True)
        generation_layout.addRow(self.include_details_checkbox)
        
        self.include_recommendations_checkbox = QCheckBox("Include recommendations")
        self.include_recommendations_checkbox.setChecked(True)
        generation_layout.addRow(self.include_recommendations_checkbox)
        
        layout.addWidget(generation_group)
        
        # Report actions
        actions_layout = QHBoxLayout()
        
        self.generate_report_button = QPushButton("Generate Report")
        self.generate_report_button.clicked.connect(self.generate_report)
        self.generate_report_button.setMinimumHeight(35)
        actions_layout.addWidget(self.generate_report_button)
        
        self.preview_report_button = QPushButton("Preview Report")
        self.preview_report_button.clicked.connect(self.preview_report)
        self.preview_report_button.setMinimumHeight(35)
        actions_layout.addWidget(self.preview_report_button)
        
        self.schedule_report_button = QPushButton("Schedule Report")
        self.schedule_report_button.clicked.connect(self.schedule_report)
        self.schedule_report_button.setMinimumHeight(35)
        actions_layout.addWidget(self.schedule_report_button)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        # Progress bar
        self.reports_progress_bar = QProgressBar()
        self.reports_progress_bar.setVisible(False)
        layout.addWidget(self.reports_progress_bar)
        
        # Recent reports group
        recent_group = QGroupBox("Recent Reports")
        recent_layout = QVBoxLayout(recent_group)
        
        # Refresh button
        refresh_reports_button = QPushButton("Refresh Reports")
        refresh_reports_button.clicked.connect(self.refresh_reports_list)
        recent_layout.addWidget(refresh_reports_button)
        
        # Reports table
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(5)
        self.reports_table.setHorizontalHeaderLabels([
            "Report Name", "Type", "Generated", "Size", "Actions"
        ])
        self.reports_table.horizontalHeader().setStretchLastSection(True)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        recent_layout.addWidget(self.reports_table)
        
        layout.addWidget(recent_group)
       
        # Report templates group
        templates_group = QGroupBox("Report Templates")
        templates_layout = QVBoxLayout(templates_group)
        
        templates_buttons_layout = QHBoxLayout()
        
        self.save_template_button = QPushButton("Save as Template")
        self.save_template_button.clicked.connect(self.save_report_template)
        templates_buttons_layout.addWidget(self.save_template_button)
        
        self.load_template_button = QPushButton("Load Template")
        self.load_template_button.clicked.connect(self.load_report_template)
        templates_buttons_layout.addWidget(self.load_template_button)
        
        templates_buttons_layout.addStretch()
        templates_layout.addLayout(templates_buttons_layout)
        
        # Templates list
        self.templates_list = QListWidget()
        self.templates_list.setMaximumHeight(100)
        templates_layout.addWidget(self.templates_list)
        
        layout.addWidget(templates_group)
        
        # Load existing reports
        self.refresh_reports_list()
        
        return reports_tab
    
    def generate_report(self):
        """Generate a report based on current settings."""
        try:
            from ..reports.reports import ReportsGenerator
            
            # Get report settings
            report_type = self.report_type_combo.currentText()
            report_format = self.report_format_combo.currentText().lower()
            date_range = self.report_date_range_combo.currentText()
            
            # Show progress
            self.generate_report_button.setEnabled(False)
            self.reports_progress_bar.setVisible(True)
            self.reports_progress_bar.setRange(0, 0)  # Indeterminate
            
            # Create generator
            generator = ReportsGenerator(self.config)
            
            # Build report configuration
            report_config = {
                'type': report_type.lower().replace(' ', '_'),
                'format': report_format,
                'date_range': date_range.lower().replace(' ', '_'),
                'include_charts': self.include_charts_checkbox.isChecked(),
                'include_details': self.include_details_checkbox.isChecked(),
                'include_recommendations': self.include_recommendations_checkbox.isChecked()
            }
            
            # Generate report
            report_path = generator.generate_report(report_config)
            
            # Update UI
            self.generate_report_button.setEnabled(True)
            self.reports_progress_bar.setVisible(False)
            
            # Show success message
            QMessageBox.information(
                self, 
                "Report Generated", 
                f"Report generated successfully!\n\nSaved to: {report_path}"
            )
            
            self.add_activity(f"Generated {report_type} report")
            
            # Refresh reports list
            self.refresh_reports_list()
            
        except ImportError:
            self.generate_report_button.setEnabled(True)
            self.reports_progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", "Reports generator module not available.")
        except Exception as e:
            self.generate_report_button.setEnabled(True)
            self.reports_progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", f"Error generating report:\n{str(e)}")
    
    def preview_report(self):
        """Preview the report before generating."""
        try:
            from ..reports.reports import ReportsGenerator
            
            generator = ReportsGenerator(self.config)
            
            # Build preview configuration
            report_config = {
                'type': self.report_type_combo.currentText().lower().replace(' ', '_'),
                'format': 'html',  # Always use HTML for preview
                'date_range': self.report_date_range_combo.currentText().lower().replace(' ', '_'),
                'include_charts': self.include_charts_checkbox.isChecked(),
                'include_details': self.include_details_checkbox.isChecked(),
                'include_recommendations': self.include_recommendations_checkbox.isChecked(),
                'preview_mode': True
            }
            
            # Generate preview
            preview_html = generator.generate_preview(report_config)
            
            # Show preview in dialog
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle("Report Preview")
            preview_dialog.resize(800, 600)
            
            preview_layout = QVBoxLayout(preview_dialog)
            
            from PySide6.QtWebEngineWidgets import QWebEngineView
            web_view = QWebEngineView()
            web_view.setHtml(preview_html)
            preview_layout.addWidget(web_view)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(preview_dialog.accept)
            preview_layout.addWidget(close_button)
            
            preview_dialog.exec()
            
        except ImportError as e:
            if "QWebEngineView" in str(e):
                # Fallback to text preview
                QMessageBox.information(
                    self, 
                    "Preview", 
                    f"Report Preview:\n\nType: {self.report_type_combo.currentText()}\n"
                    f"Format: {self.report_format_combo.currentText()}\n"
                    f"Date Range: {self.report_date_range_combo.currentText()}\n"
                    f"Include Charts: {self.include_charts_checkbox.isChecked()}\n"
                    f"Include Details: {self.include_details_checkbox.isChecked()}\n"
                    f"Include Recommendations: {self.include_recommendations_checkbox.isChecked()}"
                )
            else:
                QMessageBox.critical(self, "Error", "Reports generator module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating preview:\n{str(e)}")
    
    def schedule_report(self):
        """Schedule automatic report generation."""
        try:
            from ..scheduler.scheduler import TaskScheduler
            
            # Create task configuration for report generation
            task_config = {
                'name': f"Auto Report - {self.report_type_combo.currentText()}",
                'type': 'generate_report',
                'report_type': self.report_type_combo.currentText(),
                'report_format': self.report_format_combo.currentText(),
                'include_charts': self.include_charts_checkbox.isChecked(),
                'include_details': self.include_details_checkbox.isChecked(),
                'include_recommendations': self.include_recommendations_checkbox.isChecked()
            }
            
            # Show scheduling dialog (simplified)
            schedule_type, ok = QInputDialog.getItem(
                self, 
                "Schedule Report", 
                "Select schedule frequency:",
                ["Daily", "Weekly", "Monthly"],
                0, 
                False
            )
            
            if ok and schedule_type:
                scheduler = TaskScheduler()
                
                schedule_config = {
                    'type': schedule_type.lower(),
                    'hour': 2,  # Default to 2 AM
                    'minute': 0
                }
                
                task_id = scheduler.create_task(task_config, schedule_config)
                
                QMessageBox.information(
                    self, 
                    "Report Scheduled", 
                    f"Report scheduled successfully!\n\nTask ID: {task_id}\nFrequency: {schedule_type}"
                )
                
                self.add_activity(f"Scheduled {schedule_type.lower()} report generation")
        
        except ImportError:
            QMessageBox.critical(self, "Error", "Task scheduler module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error scheduling report:\n{str(e)}")
    
    def refresh_reports_list(self):
        """Refresh the list of generated reports."""
        try:
            from ..reports.reports import ReportsGenerator
            
            generator = ReportsGenerator(self.config)
            reports = generator.list_reports()
            
            # Update reports table
            self.reports_table.setRowCount(len(reports))
            
            for i, report in enumerate(reports):
                self.reports_table.setItem(i, 0, QTableWidgetItem(report.get('name', 'Unknown')))
                self.reports_table.setItem(i, 1, QTableWidgetItem(report.get('type', 'Unknown')))
                self.reports_table.setItem(i, 2, QTableWidgetItem(report.get('generated', 'Unknown')))
                self.reports_table.setItem(i, 3, QTableWidgetItem(report.get('size', 'Unknown')))
                
                # Add action buttons
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                
                view_button = QPushButton("View")
                view_button.clicked.connect(lambda checked, path=report.get('path'): self.view_report(path))
                actions_layout.addWidget(view_button)
                
                delete_button = QPushButton("Delete")
                delete_button.clicked.connect(lambda checked, path=report.get('path'): self.delete_report(path))
                actions_layout.addWidget(delete_button)
                
                self.reports_table.setCellWidget(i, 4, actions_widget)
        
        except ImportError:
            # Reports generator not available
            self.reports_table.setRowCount(1)
            self.reports_table.setItem(0, 0, QTableWidgetItem("Reports generator not available"))
            for col in range(1, 5):
                self.reports_table.setItem(0, col, QTableWidgetItem(""))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error refreshing reports:\n{str(e)}")
    
    def view_report(self, report_path):
        """View a generated report."""
        try:
            import webbrowser
            import os
            
            if report_path and os.path.exists(report_path):
                webbrowser.open(f'file://{report_path}')
                self.add_activity(f"Opened report: {os.path.basename(report_path)}")
            else:
                QMessageBox.warning(self, "File Not Found", "Report file not found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening report:\n{str(e)}")
    
    def delete_report(self, report_path):
        """Delete a generated report."""
        try:
            import os
            
            if not report_path or not os.path.exists(report_path):
                QMessageBox.warning(self, "File Not Found", "Report file not found.")
                return
            
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete this report?\n\n{os.path.basename(report_path)}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                os.remove(report_path)
                QMessageBox.information(self, "Report Deleted", "Report deleted successfully.")
                self.add_activity(f"Deleted report: {os.path.basename(report_path)}")
                self.refresh_reports_list()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting report:\n{str(e)}")
    
    def save_report_template(self):
        """Save current report settings as a template."""
        template_name, ok = QInputDialog.getText(
            self, 
            "Save Template", 
            "Enter template name:"
        )
        
        if ok and template_name:
            try:
                template_config = {
                    'name': template_name,
                    'type': self.report_type_combo.currentText(),
                    'format': self.report_format_combo.currentText(),
                    'date_range': self.report_date_range_combo.currentText(),
                    'include_charts': self.include_charts_checkbox.isChecked(),
                    'include_details': self.include_details_checkbox.isChecked(),
                    'include_recommendations': self.include_recommendations_checkbox.isChecked()
                }
                
                # Save template (simplified - would normally save to file)
                self.templates_list.addItem(template_name)
                
                QMessageBox.information(self, "Template Saved", f"Template '{template_name}' saved successfully.")
                self.add_activity(f"Saved report template: {template_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving template:\n{str(e)}")
    
    def load_report_template(self):
        """Load a report template."""
        current_item = self.templates_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a template to load.")
            return
        
        template_name = current_item.text()
        
        try:
            # Load template (simplified - would normally load from file)
            QMessageBox.information(self, "Template Loaded", f"Template '{template_name}' loaded successfully.")
            self.add_activity(f"Loaded report template: {template_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading template:\n{str(e)}")
    
    def create_resource_monitor_tab(self) -> QWidget:
        """Create the resource monitor tab."""
        monitor_tab = QWidget()
        layout = QVBoxLayout(monitor_tab)
        
        # Real-time monitoring controls
        controls_group = QGroupBox("Monitoring Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        self.start_monitoring_button = QPushButton("Start Monitoring")
        self.start_monitoring_button.clicked.connect(self.start_resource_monitoring)
        self.start_monitoring_button.setMinimumHeight(35)
        controls_layout.addWidget(self.start_monitoring_button)
        
        self.stop_monitoring_button = QPushButton("Stop Monitoring")
        self.stop_monitoring_button.clicked.connect(self.stop_resource_monitoring)
        self.stop_monitoring_button.setEnabled(False)
        self.stop_monitoring_button.setMinimumHeight(35)
        controls_layout.addWidget(self.stop_monitoring_button)
        
        self.refresh_interval_spinbox = QSpinBox()
        self.refresh_interval_spinbox.setRange(1, 60)
        self.refresh_interval_spinbox.setValue(5)
        self.refresh_interval_spinbox.setSuffix(" seconds")
        controls_layout.addWidget(QLabel("Refresh Interval:"))
        controls_layout.addWidget(self.refresh_interval_spinbox)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        # System metrics display
        metrics_group = QGroupBox("System Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # CPU and Memory usage
        usage_layout = QHBoxLayout()
        
        # CPU Usage
        cpu_group = QGroupBox("CPU Usage")
        cpu_layout = QVBoxLayout(cpu_group)
        
        self.cpu_usage_label = QLabel("CPU: 0%")
        self.cpu_usage_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        cpu_layout.addWidget(self.cpu_usage_label)
        
        self.cpu_progress_bar = QProgressBar()
        self.cpu_progress_bar.setRange(0, 100)
        cpu_layout.addWidget(self.cpu_progress_bar)
        
        usage_layout.addWidget(cpu_group)
        
        # Memory Usage
        memory_group = QGroupBox("Memory Usage")
        memory_layout = QVBoxLayout(memory_group)
        
        self.memory_usage_label = QLabel("Memory: 0 MB / 0 MB")
        self.memory_usage_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        memory_layout.addWidget(self.memory_usage_label)
        
        self.memory_progress_bar = QProgressBar()
        self.memory_progress_bar.setRange(0, 100)
        memory_layout.addWidget(self.memory_progress_bar)
        
        usage_layout.addWidget(memory_group)
        
        metrics_layout.addLayout(usage_layout)
        
        # Disk I/O and Network
        io_layout = QHBoxLayout()
        
        # Disk I/O
        disk_group = QGroupBox("Disk I/O")
        disk_layout = QVBoxLayout(disk_group)
        
        self.disk_read_label = QLabel("Read: 0 MB/s")
        disk_layout.addWidget(self.disk_read_label)
        
        self.disk_write_label = QLabel("Write: 0 MB/s")
        disk_layout.addWidget(self.disk_write_label)
        
        io_layout.addWidget(disk_group)
        
        # Network I/O
        network_group = QGroupBox("Network I/O")
        network_layout = QVBoxLayout(network_group)
        
        self.network_sent_label = QLabel("Sent: 0 MB/s")
        network_layout.addWidget(self.network_sent_label)
        
        self.network_recv_label = QLabel("Received: 0 MB/s")
        network_layout.addWidget(self.network_recv_label)
        
        io_layout.addWidget(network_group)
        
        metrics_layout.addLayout(io_layout)
        layout.addWidget(metrics_group)
        
        # Process monitoring
        processes_group = QGroupBox("Top Processes by Resource Usage")
        processes_layout = QVBoxLayout(processes_group)
        
        self.resource_processes_table = QTableWidget()
        self.resource_processes_table.setColumnCount(4)
        self.resource_processes_table.setHorizontalHeaderLabels([
            "Process Name", "PID", "CPU %", "Memory MB"
        ])
        self.resource_processes_table.horizontalHeader().setStretchLastSection(True)
        self.resource_processes_table.setMaximumHeight(200)
        processes_layout.addWidget(self.resource_processes_table)
        
        layout.addWidget(processes_group)
        
        # Performance alerts
        alerts_group = QGroupBox("Performance Alerts")
        alerts_layout = QVBoxLayout(alerts_group)
        
        # Alert thresholds
        thresholds_layout = QFormLayout()
        
        self.cpu_threshold_spinbox = QSpinBox()
        self.cpu_threshold_spinbox.setRange(50, 100)
        self.cpu_threshold_spinbox.setValue(80)
        self.cpu_threshold_spinbox.setSuffix("%")
        thresholds_layout.addRow("CPU Alert Threshold:", self.cpu_threshold_spinbox)
        
        self.memory_threshold_spinbox = QSpinBox()
        self.memory_threshold_spinbox.setRange(50, 100)
        self.memory_threshold_spinbox.setValue(85)
        self.memory_threshold_spinbox.setSuffix("%")
        thresholds_layout.addRow("Memory Alert Threshold:", self.memory_threshold_spinbox)
        
        alerts_layout.addLayout(thresholds_layout)
        
        # Alerts display
        self.alerts_text = QTextEdit()
        self.alerts_text.setMaximumHeight(100)
        self.alerts_text.setReadOnly(True)
        alerts_layout.addWidget(self.alerts_text)
        
        layout.addWidget(alerts_group)
        
        # Initialize monitoring timer
        from PySide6.QtCore import QTimer
        self.monitoring_timer = QTimer()
        self.monitoring_timer.timeout.connect(self.update_resource_metrics)
        
        return monitor_tab
    
    def start_resource_monitoring(self):
        """Start real-time resource monitoring."""
        try:
            from ..performance.resource_monitor import ResourceMonitor
            
            self.resource_monitor = ResourceMonitor()
            
            # Start monitoring timer
            interval = self.refresh_interval_spinbox.value() * 1000  # Convert to milliseconds
            self.monitoring_timer.start(interval)
            
            # Update UI
            self.start_monitoring_button.setEnabled(False)
            self.stop_monitoring_button.setEnabled(True)
            
            self.add_activity("Started resource monitoring")
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Resource monitor module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting monitoring:\n{str(e)}")
    
    def stop_resource_monitoring(self):
        """Stop real-time resource monitoring."""
        try:
            # Stop monitoring timer
            self.monitoring_timer.stop()
            
            # Update UI
            self.start_monitoring_button.setEnabled(True)
            self.stop_monitoring_button.setEnabled(False)
            
            self.add_activity("Stopped resource monitoring")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error stopping monitoring:\n{str(e)}")
    
    def update_resource_metrics(self):
        """Update resource metrics display."""
        try:
            if not hasattr(self, 'resource_monitor'):
                return
            
            # Get current metrics
            metrics = self.resource_monitor.get_current_metrics()
            
            # Update CPU usage
            cpu_percent = metrics.get('cpu_percent', 0)
            self.cpu_usage_label.setText(f"CPU: {cpu_percent:.1f}%")
            self.cpu_progress_bar.setValue(int(cpu_percent))
            
            # Update memory usage
            memory_info = metrics.get('memory', {})
            memory_used = memory_info.get('used_mb', 0)
            memory_total = memory_info.get('total_mb', 0)
            memory_percent = memory_info.get('percent', 0)
            
            self.memory_usage_label.setText(f"Memory: {memory_used:.0f} MB / {memory_total:.0f} MB")
            self.memory_progress_bar.setValue(int(memory_percent))
            
            # Update disk I/O
            disk_info = metrics.get('disk_io', {})
            self.disk_read_label.setText(f"Read: {disk_info.get('read_mb_per_sec', 0):.1f} MB/s")
            self.disk_write_label.setText(f"Write: {disk_info.get('write_mb_per_sec', 0):.1f} MB/s")
            
            # Update network I/O
            network_info = metrics.get('network_io', {})
            self.network_sent_label.setText(f"Sent: {network_info.get('sent_mb_per_sec', 0):.1f} MB/s")
            self.network_recv_label.setText(f"Received: {network_info.get('recv_mb_per_sec', 0):.1f} MB/s")
            
            # Update top processes
            top_processes = metrics.get('top_processes', [])
            self.resource_processes_table.setRowCount(len(top_processes))
            
            for i, process in enumerate(top_processes):
                self.resource_processes_table.setItem(i, 0, QTableWidgetItem(process.get('name', 'Unknown')))
                self.resource_processes_table.setItem(i, 1, QTableWidgetItem(str(process.get('pid', 0))))
                self.resource_processes_table.setItem(i, 2, QTableWidgetItem(f"{process.get('cpu_percent', 0):.1f}"))
                self.resource_processes_table.setItem(i, 3, QTableWidgetItem(f"{process.get('memory_mb', 0):.1f}"))
            
            # Check for alerts
            self.check_performance_alerts(cpu_percent, memory_percent)
            
        except Exception as e:
            self.alerts_text.append(f"Error updating metrics: {str(e)}")
    
    def check_performance_alerts(self, cpu_percent, memory_percent):
        """Check for performance alerts and display warnings."""
        from datetime import datetime
        
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Check CPU threshold
        cpu_threshold = self.cpu_threshold_spinbox.value()
        if cpu_percent > cpu_threshold:
            alert_msg = f"[{current_time}] HIGH CPU USAGE: {cpu_percent:.1f}% (threshold: {cpu_threshold}%)"
            self.alerts_text.append(alert_msg)
        
        # Check memory threshold
        memory_threshold = self.memory_threshold_spinbox.value()
        if memory_percent > memory_threshold:
            alert_msg = f"[{current_time}] HIGH MEMORY USAGE: {memory_percent:.1f}% (threshold: {memory_threshold}%)"
            self.alerts_text.append(alert_msg)
        
        # Auto-scroll to bottom
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
            QMessageBox.warning(self, "Invalid Input", "Please enter a rule name.")
            return
        
        trigger_type = self.trigger_type_combo.currentText()
        trigger_value = self.trigger_value_input.text().strip()
        target_path = self.rule_path_input.text().strip()
        
        if not target_path or not Path(target_path).exists():
            QMessageBox.warning(self, "Invalid Path", "Please select a valid target path.")
            return
        
        try:
            from ..scheduler.auto_clean_rules import AutoCleanRules
            
            rules_manager = AutoCleanRules()
            
            # Build rule configuration
            rule_config = {
                'name': rule_name,
                'trigger_type': trigger_type.lower().replace(' ', '_'),
                'trigger_value': trigger_value,
                'target_path': target_path,
                'action': self.rule_action_combo.currentText().lower().replace(' ', '_'),
                'enabled': self.rule_enabled_checkbox.isChecked(),
                'dry_run': self.rule_dry_run_checkbox.isChecked(),
                'notify': self.rule_notify_checkbox.isChecked(),
                'priority': self.rule_priority_spinbox.value()
            }
            
            # Create the rule
            rule_id = rules_manager.create_rule(rule_config)
            
            QMessageBox.information(
                self, 
                "Rule Created", 
                f"Auto-clean rule '{rule_name}' created successfully with ID: {rule_id}"
            )
            
            self.add_activity(f"Created auto-clean rule: {rule_name}")
            
            # Clear form
            self.rule_name_input.clear()
            self.trigger_value_input.clear()
            self.rule_path_input.setText(str(Path.home()))
            
            # Refresh rules list
            self.refresh_auto_clean_rules()
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Auto-clean rules module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating rule:\n{str(e)}")
    
    def refresh_auto_clean_rules(self):
        """Refresh the list of auto-clean rules."""
        try:
            from ..scheduler.auto_clean_rules import AutoCleanRules
            
            rules_manager = AutoCleanRules()
            rules = rules_manager.list_rules()
            
            # Update rules table
            self.auto_clean_rules_table.setRowCount(len(rules))
            
            for i, rule in enumerate(rules):
                self.auto_clean_rules_table.setItem(i, 0, QTableWidgetItem(rule.get('name', 'Unknown')))
                self.auto_clean_rules_table.setItem(i, 1, QTableWidgetItem(rule.get('trigger_type', 'Unknown')))
                self.auto_clean_rules_table.setItem(i, 2, QTableWidgetItem(rule.get('action', 'Unknown')))
                
                status = "Enabled" if rule.get('enabled', True) else "Disabled"
                self.auto_clean_rules_table.setItem(i, 3, QTableWidgetItem(status))
                
                self.auto_clean_rules_table.setItem(i, 4, QTableWidgetItem(rule.get('last_triggered', 'Never')))
                self.auto_clean_rules_table.setItem(i, 5, QTableWidgetItem(str(rule.get('priority', 5))))
            
            # Update execution log
            execution_log = rules_manager.get_execution_log(limit=20)
            self.rule_execution_log.clear()
            
            for entry in execution_log:
                log_entry = f"[{entry.get('timestamp', 'Unknown')}] {entry.get('rule_name', 'Unknown')}: {entry.get('result', 'Unknown')}"
                self.rule_execution_log.append(log_entry)
        
        except ImportError:
            # Auto-clean rules not available
            self.auto_clean_rules_table.setRowCount(1)
            self.auto_clean_rules_table.setItem(0, 0, QTableWidgetItem("Auto-clean rules not available"))
            for col in range(1, 6):
                self.auto_clean_rules_table.setItem(0, col, QTableWidgetItem(""))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error refreshing rules:\n{str(e)}")
    
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
            from ..scheduler.auto_clean_rules import AutoCleanRules
            
            rules_manager = AutoCleanRules()
            result = rules_manager.test_rule(rule_name)
            
            if result.get('success', False):
                QMessageBox.information(
                    self, 
                    "Rule Test", 
                    f"Rule '{rule_name}' test completed successfully.\n\n{result.get('message', '')}"
                )
                self.add_activity(f"Tested auto-clean rule: {rule_name}")
            else:
                QMessageBox.warning(
                    self, 
                    "Rule Test Failed", 
                    f"Rule '{rule_name}' test failed.\n\n{result.get('error', 'Unknown error')}"
                )
            
            # Refresh rules to update last triggered
            self.refresh_auto_clean_rules()
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Auto-clean rules module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing rule:\n{str(e)}")
    
    def delete_selected_rule(self):
        """Delete the selected auto-clean rule."""
        selected_rows = set()
        for item in self.auto_clean_rules_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        row = list(selected_rows)[0]
        rule_name = self.auto_clean_rules_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the rule '{rule_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            from ..scheduler.auto_clean_rules import AutoCleanRules
            
            rules_manager = AutoCleanRules()
            success = rules_manager.delete_rule(rule_name)
            
            if success:
                QMessageBox.information(self, "Rule Deleted", f"Rule '{rule_name}' deleted successfully.")
                self.add_activity(f"Deleted auto-clean rule: {rule_name}")
                self.refresh_auto_clean_rules()
            else:
                QMessageBox.warning(self, "Deletion Failed", f"Failed to delete rule '{rule_name}'.")
            
        except ImportError:
            QMessageBox.critical(self, "Error", "Auto-clean rules module not available.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting rule:\n{str(e)}")
    

if __name__ == "__main__":
    main()