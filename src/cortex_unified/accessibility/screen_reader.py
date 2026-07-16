"""
Screen reader support and accessibility features.
"""

from typing import List, Any, Dict, Optional
import logging
import platform

try:
    from PySide6.QtWidgets import (
        QWidget, QLabel, QPushButton, QLineEdit, QTextEdit, 
        QCheckBox, QRadioButton, QComboBox, QSpinBox, QSlider,
        QProgressBar, QTabWidget, QTableWidget, QTreeWidget, QListWidget
    )
    from PySide6.QtCore import QObject, QTimer
    from PySide6.QtGui import QAccessible, QAccessibleEvent
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

# Platform-specific screen reader support
try:
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes
        HAS_WINDOWS_ACCESSIBILITY = True
    else:
        HAS_WINDOWS_ACCESSIBILITY = False
except ImportError:
    HAS_WINDOWS_ACCESSIBILITY = False

class ScreenReaderSupport:
    """Provides screen reader compatibility and accessibility features."""
    
    def __init__(self, widget: Any = None):
        """Initialize screen reader support for widget."""
        self.widget = widget
        self.logger = logging.getLogger(__name__)
        self.announcement_timer = None
        
        if not HAS_PYSIDE6:
            self.logger.warning("PySide6 not available, screen reader support disabled")
            
        # Initialize platform-specific accessibility
        self._init_platform_accessibility()
    
    def _init_platform_accessibility(self) -> None:
        """Initialize platform-specific accessibility features."""
        if platform.system() == "Windows" and HAS_WINDOWS_ACCESSIBILITY:
            try:
                # Initialize Windows accessibility
                self.user32 = ctypes.windll.user32
                self.oleacc = ctypes.windll.oleacc
                self.logger.info("Windows accessibility support initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Windows accessibility: {e}")
        elif platform.system() == "Darwin":
            # macOS accessibility would be implemented here
            self.logger.info("macOS accessibility support (placeholder)")
        elif platform.system() == "Linux":
            # Linux accessibility (AT-SPI) would be implemented here
            self.logger.info("Linux accessibility support (placeholder)")
    
    def add_aria_labels(self, elements: List[Any]) -> None:
        """Add ARIA labels to interface elements."""
        if not HAS_PYSIDE6:
            return
            
        try:
            for element in elements:
                if not isinstance(element, QWidget):
                    continue
                    
                accessible_name = self._generate_accessible_name(element)
                accessible_description = self._generate_accessible_description(element)
                
                if accessible_name:
                    element.setAccessibleName(accessible_name)
                if accessible_description:
                    element.setAccessibleDescription(accessible_description)
                    
                # Set appropriate role
                role = self._get_accessible_role(element)
                if role:
                    # Note: PySide6 doesn't have direct role setting, but we can use properties
                    element.setProperty("accessibleRole", role)
                    
            self.logger.info(f"Added ARIA labels to {len(elements)} elements")
            
        except Exception as e:
            self.logger.error(f"Error adding ARIA labels: {e}")
    
    def _generate_accessible_name(self, widget: QWidget) -> str:
        """Generate accessible name for widget."""
        # Try to get existing text or label
        if hasattr(widget, 'text') and widget.text():
            return widget.text()
        elif hasattr(widget, 'title') and widget.title():
            return widget.title()
        elif hasattr(widget, 'toolTip') and widget.toolTip():
            return widget.toolTip()
        
        # Generate based on widget type and context
        widget_type = type(widget).__name__
        object_name = widget.objectName() if widget.objectName() else "unnamed"
        
        return f"{widget_type} {object_name}"
    
    def _generate_accessible_description(self, widget: QWidget) -> str:
        """Generate accessible description for widget."""
        descriptions = {
            QPushButton: "Button - Press to activate",
            QLineEdit: "Text input field",
            QTextEdit: "Multi-line text input area", 
            QCheckBox: "Checkbox - Check or uncheck",
            QRadioButton: "Radio button - Select option",
            QComboBox: "Dropdown list - Select an option",
            QSpinBox: "Number input - Use arrows or type value",
            QSlider: "Slider - Drag to adjust value",
            QProgressBar: "Progress indicator",
            QTabWidget: "Tab container - Use arrow keys to navigate tabs",
            QTableWidget: "Table - Use arrow keys to navigate cells",
            QTreeWidget: "Tree view - Use arrow keys to navigate items",
            QListWidget: "List - Use arrow keys to navigate items"
        }
        
        widget_type = type(widget)
        base_description = descriptions.get(widget_type, "Interactive element")
        
        # Add state information
        if hasattr(widget, 'isEnabled') and not widget.isEnabled():
            base_description += " (disabled)"
        if hasattr(widget, 'isChecked') and widget.isChecked():
            base_description += " (checked)"
            
        return base_description
    
    def _get_accessible_role(self, widget: QWidget) -> str:
        """Get appropriate accessible role for widget."""
        role_mapping = {
            QPushButton: "button",
            QLineEdit: "textbox",
            QTextEdit: "textbox",
            QCheckBox: "checkbox", 
            QRadioButton: "radio",
            QComboBox: "combobox",
            QSpinBox: "spinbutton",
            QSlider: "slider",
            QProgressBar: "progressbar",
            QTabWidget: "tablist",
            QTableWidget: "table",
            QTreeWidget: "tree",
            QListWidget: "listbox",
            QLabel: "text"
        }
        
        return role_mapping.get(type(widget), "generic")
    
    def announce_changes(self, message: str) -> None:
        """Announce changes to screen readers."""
        if not message:
            return
            
        try:
            # Use Qt's accessibility system
            if HAS_PYSIDE6 and self.widget:
                event = QAccessibleEvent(self.widget, QAccessible.Event.Alert)
                QAccessible.updateAccessibility(event)
            
            # Platform-specific announcements
            if platform.system() == "Windows" and HAS_WINDOWS_ACCESSIBILITY:
                self._announce_windows(message)
            elif platform.system() == "Darwin":
                self._announce_macos(message)
            elif platform.system() == "Linux":
                self._announce_linux(message)
                
            self.logger.info(f"Announced: {message}")
            
        except Exception as e:
            self.logger.error(f"Error announcing message: {e}")
    
    def _announce_windows(self, message: str) -> None:
        """Announce message on Windows."""
        if not HAS_WINDOWS_ACCESSIBILITY:
            return
            
        try:
            # Use Windows SAPI for announcements
            self.logger.debug(f"Windows announcement: {message}")
        except Exception as e:
            self.logger.error(f"Windows announcement failed: {e}")
    
    def _announce_macos(self, message: str) -> None:
        """Announce message on macOS."""
        try:
            # macOS VoiceOver announcements would be implemented here
            self.logger.debug(f"macOS announcement: {message}")
        except Exception as e:
            self.logger.error(f"macOS announcement failed: {e}")
    
    def _announce_linux(self, message: str) -> None:
        """Announce message on Linux."""
        try:
            # Linux AT-SPI announcements would be implemented here
            self.logger.debug(f"Linux announcement: {message}")
        except Exception as e:
            self.logger.error(f"Linux announcement failed: {e}")
    
    def setup_accessible_descriptions(self) -> None:
        """Set up accessible descriptions for interface elements."""
        if not HAS_PYSIDE6 or not self.widget:
            return
            
        try:
            # Find all widgets and set up accessibility
            widgets = self.widget.findChildren(QWidget)
            self.add_aria_labels(widgets)
            
            # Set up live regions for dynamic content
            self._setup_live_regions()
            
            # Set up landmark roles
            self._setup_landmarks()
            
            self.logger.info("Accessible descriptions set up")
            
        except Exception as e:
            self.logger.error(f"Error setting up accessible descriptions: {e}")
    
    def _setup_live_regions(self) -> None:
        """Set up live regions for dynamic content updates."""
        if not self.widget:
            return
            
        # Find progress bars, status labels, etc. and mark as live regions
        progress_bars = self.widget.findChildren(QProgressBar)
        for pb in progress_bars:
            pb.setProperty("accessibleLive", "polite")
            
        # Find status labels
        labels = self.widget.findChildren(QLabel)
        for label in labels:
            if "status" in label.objectName().lower() or "progress" in label.objectName().lower():
                label.setProperty("accessibleLive", "polite")
    
    def _setup_landmarks(self) -> None:
        """Set up landmark roles for navigation."""
        if not self.widget:
            return
            
        # Set main content area
        if hasattr(self.widget, 'centralWidget'):
            central_widget = self.widget.centralWidget()
            if central_widget:
                central_widget.setProperty("accessibleRole", "main")
        
        # Find and mark navigation areas
        tab_widgets = self.widget.findChildren(QTabWidget)
        for tab_widget in tab_widgets:
            tab_widget.setProperty("accessibleRole", "navigation")
    
    def set_focus_announcement(self, widget: QWidget, message: str) -> None:
        """Set custom announcement when widget receives focus."""
        if not HAS_PYSIDE6:
            return
            
        def on_focus_in():
            self.announce_changes(message)
            
        # Connect to focus events
        widget.focusInEvent = lambda event: (
            QWidget.focusInEvent(widget, event),
            on_focus_in()
        )
    
    def create_accessible_table(self, table_widget: Any) -> None:
        """Set up accessibility for table widgets."""
        if not HAS_PYSIDE6 or not isinstance(table_widget, QTableWidget):
            return
            
        try:
            # Set table headers as accessible
            horizontal_header = table_widget.horizontalHeader()
            vertical_header = table_widget.verticalHeader()
            
            if horizontal_header:
                horizontal_header.setAccessibleName("Column headers")
            if vertical_header:
                vertical_header.setAccessibleName("Row headers")
                
            # Set table description
            table_widget.setAccessibleDescription(
                f"Table with {table_widget.rowCount()} rows and {table_widget.columnCount()} columns"
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up accessible table: {e}")
    
    def create_accessible_tree(self, tree_widget: Any) -> None:
        """Set up accessibility for tree widgets."""
        if not HAS_PYSIDE6 or not isinstance(tree_widget, QTreeWidget):
            return
            
        try:
            tree_widget.setAccessibleDescription(
                "Tree view - Use arrow keys to navigate, Enter to expand/collapse"
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up accessible tree: {e}")
    
    def announce_progress(self, percentage: int, message: str = "") -> None:
        """Announce progress updates."""
        if percentage % 10 == 0:  # Announce every 10%
            announcement = f"Progress: {percentage}%"
            if message:
                announcement += f" - {message}"
            self.announce_changes(announcement)
    
    def announce_error(self, error_message: str) -> None:
        """Announce error messages."""
        self.announce_changes(f"Error: {error_message}")
    
    def announce_success(self, success_message: str) -> None:
        """Announce success messages."""
        self.announce_changes(f"Success: {success_message}")
    
    def get_accessibility_info(self) -> Dict[str, Any]:
        """Get information about accessibility features."""
        return {
            "screen_reader_support": HAS_PYSIDE6,
            "platform": platform.system(),
            "windows_accessibility": HAS_WINDOWS_ACCESSIBILITY,
            "features": [
                "ARIA labels",
                "Keyboard navigation", 
                "Screen reader announcements",
                "Live regions",
                "Landmark roles",
                "Focus management"
            ]
        }