"""Screen-reader affordances for Qt widget hierarchies.

Derives accessible names/descriptions, maps widget classes to ARIA-style
roles, and emits announcements via Qt accessibility events.
"""

from typing import List, Any, Dict
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

# Windows-only: user32/oleacc loaded lazily below
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
    """Annotates a widget hierarchy for assistive technology.

    Accessible names fall back through text/title/tooltip before
    synthesizing from the widget type; announcements ride Qt's
    accessibility event system plus per-platform hooks.
    """
    
    def __init__(self, widget: Any = None):
        """Attach to ``widget``; logging-only degradation without Qt.

        Initializes the instance and configures internal state.

        Args:
            widget (Any): The widget parameter.
        """
        self.widget = widget
        self.logger = logging.getLogger(__name__)
        self.announcement_timer = None
        
        if not HAS_PYSIDE6:
            self.logger.warning("PySide6 not available, screen reader support disabled")
            
        self._init_platform_accessibility()
    
    def _init_platform_accessibility(self) -> None:
        """Load platform hooks; unimplemented platforms just log.

        Manages init platform accessibility operations and coordinates related state changes for the component.
        """
        if platform.system() == "Windows" and HAS_WINDOWS_ACCESSIBILITY:
            try:
                self.user32 = ctypes.windll.user32
                self.oleacc = ctypes.windll.oleacc
                self.logger.info("Windows accessibility support initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Windows accessibility: {e}")
        elif platform.system() == "Darwin":
            self.logger.debug("macOS accessibility bridge: Qt accessibility active")
        elif platform.system() == "Linux":
            self.logger.debug("Linux accessibility bridge: Qt accessibility active")
    
    def add_aria_labels(self, elements: List[Any]) -> None:
        """Set name, description, and role properties on each QWidget.

        Manages add aria labels operations and coordinates related state changes for the component.

        Args:
            elements (List[Any]): The elements parameter.
        """
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
                    
                role = self._get_accessible_role(element)
                if role:
                    # No role setter exists; expose it as a dynamic
                    # property for AT bridges and QSS styling
                    element.setProperty("accessibleRole", role)
                    
            self.logger.info(f"Added ARIA labels to {len(elements)} elements")
            
        except Exception as e:
            self.logger.error(f"Error adding ARIA labels: {e}")
    
    def _generate_accessible_name(self, widget: QWidget) -> str:
        """First non-empty of text/title/toolTip, else '<Type> <objectName>'.

        Manages generate accessible name operations and coordinates related state changes for the component.

        Args:
            widget (QWidget): The widget parameter.

        Returns:
            str: Formatted string or path.
        """
        if hasattr(widget, 'text') and widget.text():
            return widget.text()
        elif hasattr(widget, 'title') and widget.title():
            return widget.title()
        elif hasattr(widget, 'toolTip') and widget.toolTip():
            return widget.toolTip()
        
        widget_type = type(widget).__name__
        object_name = widget.objectName() if widget.objectName() else "unnamed"
        
        return f"{widget_type} {object_name}"
    
    def _generate_accessible_description(self, widget: QWidget) -> str:
        """Type-specific usage hint, suffixed with disabled/checked state.

        Manages generate accessible description operations and coordinates related state changes for the component.

        Args:
            widget (QWidget): The widget parameter.

        Returns:
            str: Formatted string or path.
        """
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
        
        if hasattr(widget, 'isEnabled') and not widget.isEnabled():
            base_description += " (disabled)"
        if hasattr(widget, 'isChecked') and widget.isChecked():
            base_description += " (checked)"
            
        return base_description
    
    def _get_accessible_role(self, widget: QWidget) -> str:
        """Map Qt widget class to the nearest WAI-ARIA role name.

        Manages get accessible role operations and coordinates related state changes for the component.

        Args:
            widget (QWidget): The widget parameter.

        Returns:
            str: Formatted string or path.
        """
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
        """Fire a Qt alert accessibility event plus platform announcements.

        Manages announce changes operations and coordinates related state changes for the component.

        Args:
            message (str): Informational or progress status message.
        """
        if not message:
            return
            
        try:
            if HAS_PYSIDE6 and self.widget:
                event = QAccessibleEvent(self.widget, QAccessible.Event.Alert)
                QAccessible.updateAccessibility(event)
            
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
        """Announce text using Windows SAPI voice synthesizer if available.

        Manages announce windows operations and coordinates related state changes for the component.

        Args:
            message (str): Informational or progress status message.
        """
        if not HAS_WINDOWS_ACCESSIBILITY:
            return
            
        try:
            # Try Windows SAPI COM voice
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            # 1 = SVSFlagsAsync (non-blocking speech)
            speaker.Speak(message, 1)
        except Exception:
            # Fallback to standard logging and Qt accessibility event
            self.logger.debug(f"Windows accessibility announcement: {message}")
    
    def _announce_macos(self, message: str) -> None:
        """Unimplemented; debug-logged only.

        Manages announce macos operations and coordinates related state changes for the component.

        Args:
            message (str): Informational or progress status message.
        """
        try:
            self.logger.debug(f"macOS announcement: {message}")
        except Exception as e:
            self.logger.error(f"macOS announcement failed: {e}")
    
    def _announce_linux(self, message: str) -> None:
        """Unimplemented; debug-logged only.

        Manages announce linux operations and coordinates related state changes for the component.

        Args:
            message (str): Informational or progress status message.
        """
        try:
            self.logger.debug(f"Linux announcement: {message}")
        except Exception as e:
            self.logger.error(f"Linux announcement failed: {e}")
    
    def setup_accessible_descriptions(self) -> None:
        """Annotate all descendants, then mark live regions and landmarks.

        Manages setup accessible descriptions operations and coordinates related state changes for the component.
        """
        if not HAS_PYSIDE6 or not self.widget:
            return
            
        try:
            widgets = self.widget.findChildren(QWidget)
            self.add_aria_labels(widgets)
            
            self._setup_live_regions()
            
            self._setup_landmarks()
            
            self.logger.info("Accessible descriptions set up")
            
        except Exception as e:
            self.logger.error(f"Error setting up accessible descriptions: {e}")
    
    def _setup_live_regions(self) -> None:
        """Flag progress bars and status/progress labels as polite live regions.

        Manages setup live regions operations and coordinates related state changes for the component.
        """
        if not self.widget:
            return
            
        progress_bars = self.widget.findChildren(QProgressBar)
        for pb in progress_bars:
            pb.setProperty("accessibleLive", "polite")
            
        labels = self.widget.findChildren(QLabel)
        for label in labels:
            if "status" in label.objectName().lower() or "progress" in label.objectName().lower():
                label.setProperty("accessibleLive", "polite")
    
    def _setup_landmarks(self) -> None:
        """Tag the central widget as main and tab containers as navigation.

        Manages setup landmarks operations and coordinates related state changes for the component.
        """
        if not self.widget:
            return
            
        if hasattr(self.widget, 'centralWidget'):
            central_widget = self.widget.centralWidget()
            if central_widget:
                central_widget.setProperty("accessibleRole", "main")
        
        tab_widgets = self.widget.findChildren(QTabWidget)
        for tab_widget in tab_widgets:
            tab_widget.setProperty("accessibleRole", "navigation")
    
    def set_focus_announcement(self, widget: QWidget, message: str) -> None:
        """Announce ``message`` whenever ``widget`` gains focus.

        Overrides the instance's ``focusInEvent`` rather than requiring a
        subclass; the original handler runs first.
        """
        if not HAS_PYSIDE6:
            return
            
        def on_focus_in():
            """on_focus_in.

            Manages on focus in operations and coordinates related state changes for the component.
            """
            self.announce_changes(message)
            
        widget.focusInEvent = lambda event: (
            QWidget.focusInEvent(widget, event),
            on_focus_in()
        )
    
    def create_accessible_table(self, table_widget: Any) -> None:
        """Name headers and describe dimensions for assistive tech.

        Manages create accessible table operations and coordinates related state changes for the component.

        Args:
            table_widget (Any): The table widget parameter.
        """
        if not HAS_PYSIDE6 or not isinstance(table_widget, QTableWidget):
            return
            
        try:
            horizontal_header = table_widget.horizontalHeader()
            vertical_header = table_widget.verticalHeader()
            
            if horizontal_header:
                horizontal_header.setAccessibleName("Column headers")
            if vertical_header:
                vertical_header.setAccessibleName("Row headers")
                
            table_widget.setAccessibleDescription(
                f"Table with {table_widget.rowCount()} rows and {table_widget.columnCount()} columns"
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up accessible table: {e}")
    
    def create_accessible_tree(self, tree_widget: Any) -> None:
        """Add a keyboard-navigation hint to the tree's description.

        Manages create accessible tree operations and coordinates related state changes for the component.

        Args:
            tree_widget (Any): The tree widget parameter.
        """
        if not HAS_PYSIDE6 or not isinstance(tree_widget, QTreeWidget):
            return
            
        try:
            tree_widget.setAccessibleDescription(
                "Tree view - Use arrow keys to navigate, Enter to expand/collapse"
            )
            
        except Exception as e:
            self.logger.error(f"Error setting up accessible tree: {e}")
    
    def announce_progress(self, percentage: int, message: str = "") -> None:
        """Throttled progress speech, emitted only at 10% multiples.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            percentage (int): The percentage parameter.
            message (str): Informational or progress status message.
        """
        if percentage % 10 == 0:
            announcement = f"Progress: {percentage}%"
            if message:
                announcement += f" - {message}"
            self.announce_changes(announcement)
    
    def announce_error(self, error_message: str) -> None:
        """announce_changes wrapped with an 'Error:' prefix.

        Manages announce error operations and coordinates related state changes for the component.

        Args:
            error_message (str): Informational or progress status message.
        """
        self.announce_changes(f"Error: {error_message}")
    
    def announce_success(self, success_message: str) -> None:
        """announce_changes wrapped with a 'Success:' prefix.

        Manages announce success operations and coordinates related state changes for the component.

        Args:
            success_message (str): Informational or progress status message.
        """
        self.announce_changes(f"Success: {success_message}")
    
    def get_accessibility_info(self) -> Dict[str, Any]:
        """Capability report for diagnostics and UI toggles.

        Manages get accessibility info operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
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