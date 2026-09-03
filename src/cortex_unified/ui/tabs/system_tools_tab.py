"""Tab for system tools tab in Cortex Cleaner GUI."""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel
)

from .base_tab import BaseTab

from cortex_unified.ui.tabs.process_analyzer_tab import ProcessAnalyzerTab
from cortex_unified.ui.tabs.startup_manager_tab import StartupManagerTab
try:
    from cortex_unified.ui.tabs.registry_cleaner_tab import RegistryCleanerTab
    HAS_REGISTRY_CLEANER = True
except ImportError:
    HAS_REGISTRY_CLEANER = False

class SystemToolsTab(BaseTab):
    """Container Tab mapping System Tools sub-tabs dynamically."""

    def __init__(self, config, logger, safety_manager):
        """__init__."""
        super().__init__(config, logger, safety_manager)
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Create the system tools tab natively injecting components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        tools_tab_widget = QTabWidget()
        layout.addWidget(tools_tab_widget)
        
        # Instantiate natively directly into view rather than faking creation
        startup_tab = StartupManagerTab(self.config, self.logger, self.safety_manager)
        tools_tab_widget.addTab(startup_tab, 'Startup Manager')
        
        process_tab = ProcessAnalyzerTab(self.config, self.logger, self.safety_manager)
        tools_tab_widget.addTab(process_tab, 'Process Analyzer')
        
        if HAS_REGISTRY_CLEANER:
            registry_tab = RegistryCleanerTab(self.config, self.logger, self.safety_manager)
            tools_tab_widget.addTab(registry_tab, 'Registry Cleaner')
