"""Dashboard tab for Deep Cleaner GUI."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QListWidget
)

from .base_tab import BaseTab

class DashboardTab(BaseTab):
    """Modern Dashboard tab for overview and quick actions."""
    
    def __init__(self, config, logger, safety_manager, parent=None):
        # BaseTab requires config, logger, and safety_manager
        super().__init__(config, logger, safety_manager)
        self.parent_window = parent

    def setup_ui(self):
        """Set up the dashboard user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        welcome_label = QLabel('Welcome to Deep Cleaner')
        welcome_label.setStyleSheet('QLabel { font-size: 18px; font-weight: bold; margin: 10px; }')
        layout.addWidget(welcome_label)
        
        quick_actions_group = QGroupBox('Quick Actions')
        quick_actions_layout = QHBoxLayout(quick_actions_group)
        quick_actions_layout.setSpacing(10)
        
        self.scan_button = QPushButton('Scan Empty Files')
        self.scan_button.clicked.connect(self.quick_scan)
        self.scan_button.setMinimumHeight(40)
        quick_actions_layout.addWidget(self.scan_button)
        
        self.temp_clean_button = QPushButton('Clean Temp Files')
        self.temp_clean_button.clicked.connect(self.quick_temp_clean)
        self.temp_clean_button.setMinimumHeight(40)
        quick_actions_layout.addWidget(self.temp_clean_button)
        
        self.disk_analysis_button = QPushButton('Analyze Disk')
        self.disk_analysis_button.clicked.connect(self.quick_disk_analysis)
        self.disk_analysis_button.setMinimumHeight(40)
        quick_actions_layout.addWidget(self.disk_analysis_button)
        
        layout.addWidget(quick_actions_group)
        
        activity_group = QGroupBox('Recent Activity')
        activity_layout = QVBoxLayout(activity_group)
        self.activity_list = QListWidget()
        self.activity_list.setMaximumHeight(200)
        activity_layout.addWidget(self.activity_list)
        layout.addWidget(activity_group)
        
        system_info_group = QGroupBox('System Information')
        system_info_layout = QVBoxLayout(system_info_group)
        self.system_info_label = QLabel('System initialized successfully. Everything is optimal.')
        system_info_layout.addWidget(self.system_info_label)
        layout.addWidget(system_info_group)
        
        layout.addStretch()

    def setup_tooltips(self):
        """Set up tooltips."""
        self.scan_button.setToolTip("Start a quick scan for empty files")
        self.temp_clean_button.setToolTip("Clean temporary system files")
        self.disk_analysis_button.setToolTip("Analyze your disk storage structure")

    def quick_scan(self):
        if self.parent_window and hasattr(self.parent_window, "navigation_controller"):
            self.parent_window.navigation_controller.set_current_tab_by_name("Cleaner")

    def quick_temp_clean(self):
        if self.parent_window and hasattr(self.parent_window, "navigation_controller"):
            self.parent_window.navigation_controller.set_current_tab_by_name("Temp Files")

    def quick_disk_analysis(self):
        if self.parent_window and hasattr(self.parent_window, "navigation_controller"):
            self.parent_window.navigation_controller.set_current_tab_by_name("Disk Analyzer")
