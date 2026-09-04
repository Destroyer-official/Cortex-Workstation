"""
Settings integration for performance optimization and throttling logic.
"""

import logging

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QComboBox, 
        QCheckBox, QSpinBox, QGroupBox, QFormLayout
    )
    from PySide6.QtCore import QSettings, Signal
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from .optimization import OptimizationSettings, PerformanceOptimizer
from .resource_throttler import ResourceThrottler

class PerformanceSettingsWidget(QWidget):
    """Performancesettingswidget.

    Manages PerformanceSettingsWidget operations and coordinates related state changes for the component.
    """
    
    settings_applied = Signal(dict)
    
    def __init__(self, parent=None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.settings = QSettings()
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Build the UI structure mirroring old properties natively.

        Manages setup ui operations and coordinates related state changes for the component.
        """
        if not HAS_PYSIDE6:
            return
            
        layout = QVBoxLayout(self)
        
        perf_group = QGroupBox("Core Performance Optimizations")
        perf_layout = QFormLayout(perf_group)
        
        self.threads_spinbox = QSpinBox()
        self.threads_spinbox.setRange(1, 32)
        self.threads_spinbox.setValue(4)
        perf_layout.addRow('Thread Count:', self.threads_spinbox)
        
        self.cpu_priority_combo = QComboBox()
        self.cpu_priority_combo.addItems(['Low', 'Normal', 'High'])
        self.cpu_priority_combo.setCurrentText('Normal')
        perf_layout.addRow('CPU Priority:', self.cpu_priority_combo)
        
        self.io_priority_combo = QComboBox()
        self.io_priority_combo.addItems(['Low', 'Normal', 'High'])
        self.io_priority_combo.setCurrentText('Low')
        perf_layout.addRow('I/O Priority:', self.io_priority_combo)
        
        self.memory_limit_spinbox = QSpinBox()
        self.memory_limit_spinbox.setRange(0, 8192)
        self.memory_limit_spinbox.setValue(0)
        self.memory_limit_spinbox.setSuffix(' MB')
        perf_layout.addRow('Memory Limit (0=unlimited):', self.memory_limit_spinbox)
        layout.addWidget(perf_group)
        
        safety_group = QGroupBox("Throttling and System Safety")
        safety_layout = QFormLayout(safety_group)
        
        self.enable_checkpoints_checkbox = QCheckBox('Enable scan checkpoints')
        self.enable_checkpoints_checkbox.setChecked(True)
        safety_layout.addRow(self.enable_checkpoints_checkbox)
        
        self.checkpoint_interval_spinbox = QSpinBox()
        self.checkpoint_interval_spinbox.setRange(100, 10000)
        self.checkpoint_interval_spinbox.setValue(1000)
        safety_layout.addRow('Checkpoint Interval:', self.checkpoint_interval_spinbox)
        
        self.enable_throttling_checkbox = QCheckBox('Enable active resource throttling')
        self.enable_throttling_checkbox.setChecked(True)
        safety_layout.addRow(self.enable_throttling_checkbox)
        layout.addWidget(safety_group)

    def load_settings(self):
        """Restore properties from persistence.

        Manages load settings operations and coordinates related state changes for the component.
        """
        if not HAS_PYSIDE6:
            return
            
        self.threads_spinbox.setValue(self.settings.value("performance/threads", 4, type=int))
        
        cpu_val = self.settings.value("performance/cpu_priority", "Normal", type=str)
        self.cpu_priority_combo.setCurrentText(cpu_val)
        
        io_val = self.settings.value("performance/io_priority", "Low", type=str)
        self.io_priority_combo.setCurrentText(io_val)
        
        self.memory_limit_spinbox.setValue(self.settings.value("performance/memory_limit", 0, type=int))
        self.enable_checkpoints_checkbox.setChecked(self.settings.value("performance/checkpoints_enabled", True, type=bool))
        self.checkpoint_interval_spinbox.setValue(self.settings.value("performance/checkpoint_interval", 1000, type=int))
        self.enable_throttling_checkbox.setChecked(self.settings.value("performance/throttling_enabled", True, type=bool))

    def save_settings(self):
        """Persist properties and sync natively into systems.

        Manages save settings operations and coordinates related state changes for the component.
        """
        if not HAS_PYSIDE6:
            return
            
        properties = {
            "threads": self.threads_spinbox.value(),
            "cpu_priority": self.cpu_priority_combo.currentText(),
            "io_priority": self.io_priority_combo.currentText(),
            "memory_limit": self.memory_limit_spinbox.value(),
            "checkpoints_enabled": self.enable_checkpoints_checkbox.isChecked(),
            "checkpoint_interval": self.checkpoint_interval_spinbox.value(),
            "throttling_enabled": self.enable_throttling_checkbox.isChecked()
        }
        
        for k, v in properties.items():
            self.settings.setValue(f"performance/{k}", v)
        self.settings.sync()
        
        # Now inform the global manager to broadcast constraints
        self.settings_applied.emit(properties)
        get_performance_manager().apply_properties(properties)
        self.logger.info("Synchronized and emitted core performance properties.")

class PerformanceManager:
    """Performancemanager.

    Manages PerformanceManager operations and coordinates related state changes for the component.
    """
    
    def __init__(self):
        """Initialize the instance and configure internal state.

        Sets up sub-widgets, event signal connections, and default options.
        """
        self.logger = logging.getLogger(__name__)
        self.settings = QSettings() if HAS_PYSIDE6 else None
        
        self.optimizer = PerformanceOptimizer()
        self.throttler = ResourceThrottler()
        
        self.load_saved_settings()

    def load_saved_settings(self):
        """load_saved_settings.

        Manages load saved settings operations and coordinates related state changes for the component.
        """
        if not self.settings: return
        try:
            properties = {
                "threads": self.settings.value("performance/threads", 4, type=int),
                "cpu_priority": self.settings.value("performance/cpu_priority", "Normal", type=str),
                "io_priority": self.settings.value("performance/io_priority", "Low", type=str),
                "memory_limit": self.settings.value("performance/memory_limit", 0, type=int),
                "checkpoints_enabled": self.settings.value("performance/checkpoints_enabled", True, type=bool),
                "checkpoint_interval": self.settings.value("performance/checkpoint_interval", 1000, type=int),
                "throttling_enabled": self.settings.value("performance/throttling_enabled", True, type=bool)
            }
            self.apply_properties(properties)
        except Exception as e:
            self.logger.error(f"Error loading performance states: {e}")

    def apply_properties(self, properties: dict):
        """Translates basic dictionary states into core optimization classes natively.

        Manages apply properties operations and coordinates related state changes for the component.

        Args:
            properties (dict): The properties parameter.
        """
        # Setup Optimizer Limits
        opt_config = OptimizationSettings()
        opt_config.max_threads = properties["threads"]
        opt_config.max_memory_mb = properties["memory_limit"]
        opt_config.checkpoint_interval = properties["checkpoint_interval"]
        self.optimizer.settings = opt_config
        
        # Trigger CPU Priority via Optimizer wrapper
        if properties["cpu_priority"] == "Low":
            self.optimizer.start_optimization()
        else:
            self.optimizer.stop_optimization()
            
        # Hook Resource Throttler System Hooks
        io = properties["io_priority"].lower()
        self.throttler.set_process_priority(io)
        
        if properties["throttling_enabled"]:
            self.throttler.start_monitoring()
        else:
            self.throttler.stop_monitoring()

    def create_settings_widget(self, parent=None):
        """create_settings_widget.

        Manages create settings widget operations and coordinates related state changes for the component.

        Args:
            parent: Parent window or shell controller instance.
        """
        if HAS_PYSIDE6:
            return PerformanceSettingsWidget(parent)
        return None

_perf_manager = None
def get_performance_manager() -> PerformanceManager:
    """get_performance_manager.

    Manages get performance manager operations and coordinates related state changes for the component.

    Returns:
        PerformanceManager: Result of the operation.
    """
    global _perf_manager
    if _perf_manager is None:
        _perf_manager = PerformanceManager()
    return _perf_manager
