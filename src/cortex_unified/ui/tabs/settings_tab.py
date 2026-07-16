"""Tab for settings tab in Cortex Cleaner GUI."""

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

from .base_tab import BaseTab

try:
    from cortex_unified.i18n.settings_integration import get_i18n_manager
    HAS_I18N = True
except ImportError:
    HAS_I18N = False
    
try:
    from cortex_unified.performance.settings_integration import get_performance_manager
    HAS_PERF = True
except ImportError:
    HAS_PERF = False


class SettingsTab(BaseTab):
    """Tab for settings tab functionality."""

    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)

    def setup_ui(self):
        """Create the settings tab natively hooking I18n modules."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        settings_tab_widget = QTabWidget()
        layout.addWidget(settings_tab_widget)
        
        # General Settings (System Core)
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        self.log_file_input = QLineEdit()
        self.log_file_input.setPlaceholderText('Log file path (optional)')
        general_layout.addRow('Log File:', self.log_file_input)
        self.verbose_checkbox = QCheckBox('Verbose Output')
        general_layout.addRow(self.verbose_checkbox)
        settings_tab_widget.addTab(general_tab, 'General')
        
        # Performance Constraints
        performance_tab = QWidget()
        perf_tab_layout = QVBoxLayout(performance_tab)
        
        if HAS_PERF:
            manager = get_performance_manager()
            self.perf_widget = manager.create_settings_widget(self)
            if self.perf_widget:
                perf_tab_layout.addWidget(self.perf_widget)
            else:
                perf_tab_layout.addWidget(QLabel("Error mapping PySide6 properties to localized widget."))
        else:
            perf_tab_layout.addWidget(QLabel("Performance Management Module failed to import!"))
            
        settings_tab_widget.addTab(performance_tab, 'Performance')
        
        # Internationalization & Accessibility (i18n)
        i18n_tab_container = QWidget()
        i18n_tab_layout = QVBoxLayout(i18n_tab_container)
        
        if HAS_I18N:
            # Safely hook the massive standalone integration widget
            manager = get_i18n_manager()
            self.i18n_widget = manager.create_settings_widget(self)
            if self.i18n_widget:
                i18n_tab_layout.addWidget(self.i18n_widget)
            else:
                i18n_tab_layout.addWidget(QLabel("Error mapping PySide6 properties to localized widget."))
        else:
            i18n_tab_layout.addWidget(QLabel("Internationalization (I18N) Module failed to import!"))
            
        settings_tab_widget.addTab(i18n_tab_container, 'Language & Accessibility')
        
        # Execution
        save_button = QPushButton('Save System Configurations')
        save_button.clicked.connect(self.save_settings)
        save_button.setMinimumHeight(35)
        save_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        layout.addWidget(save_button)

    def save_settings(self):
        """Invoke global configuration application parameters."""
        # Typically maps UI values back down to Cortex settings
        if hasattr(self, 'i18n_widget') and self.i18n_widget:
            self.i18n_widget.save_settings()
            
        if hasattr(self, 'perf_widget') and self.perf_widget:
            self.perf_widget.save_settings()
            
        QMessageBox.information(self, "Configurations Applied", "Safely applied properties to internal schema buffers.")
