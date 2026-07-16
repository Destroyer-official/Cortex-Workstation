"""
Keyboard navigation and accessibility support.
"""

from typing import Dict, Any, Optional, Callable, List
import logging

try:
    from PySide6.QtWidgets import QWidget, QApplication, QTabWidget, QTableWidget, QTreeWidget, QListWidget
    from PySide6.QtCore import Qt, QObject, QEvent
    from PySide6.QtGui import QKeySequence, QShortcut, QKeyEvent
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

class KeyboardHandler(QObject):
    """Handles keyboard navigation and shortcuts."""
    
    def __init__(self, widget: Any = None):
        """Initialize keyboard handler for widget."""
        super().__init__()
        self.widget = widget
        self.shortcuts = {}
        self.focusable_widgets = []
        self.current_focus_index = 0
        self.logger = logging.getLogger(__name__)
        
        if not HAS_PYSIDE6:
            self.logger.warning("PySide6 not available, keyboard navigation disabled")
    
    def setup_keyboard_navigation(self) -> None:
        """Set up keyboard navigation for interface elements."""
        if not HAS_PYSIDE6 or not self.widget:
            return
            
        try:
            # Find all focusable widgets
            self._find_focusable_widgets()
            
            # Set up tab order
            self._setup_tab_order()
            
            # Install event filter for custom navigation
            self.widget.installEventFilter(self)
            
            # Set initial focus
            if self.focusable_widgets:
                self.focusable_widgets[0].setFocus()
                
            self.logger.info(f"Keyboard navigation set up for {len(self.focusable_widgets)} widgets")
            
        except Exception as e:
            self.logger.error(f"Error setting up keyboard navigation: {e}")
    
    def _find_focusable_widgets(self) -> None:
        """Find all focusable widgets in the interface."""
        if not self.widget:
            return
            
        self.focusable_widgets = []
        
        # Recursively find focusable widgets
        def find_widgets(parent):
            for child in parent.findChildren(QWidget):
                if (child.focusPolicy() != Qt.NoFocus and 
                    child.isVisible() and 
                    child.isEnabled()):
                    self.focusable_widgets.append(child)
        
        find_widgets(self.widget)
        
        # Sort by tab order or position
        self.focusable_widgets.sort(key=lambda w: (w.y(), w.x()))
    
    def _setup_tab_order(self) -> None:
        """Set up proper tab order for widgets."""
        if len(self.focusable_widgets) < 2:
            return
            
        try:
            # Set tab order
            for i in range(len(self.focusable_widgets) - 1):
                QWidget.setTabOrder(
                    self.focusable_widgets[i], 
                    self.focusable_widgets[i + 1]
                )
        except Exception as e:
            self.logger.error(f"Error setting tab order: {e}")
    
    def handle_tab_navigation(self, event: QKeyEvent) -> bool:
        """Handle tab key navigation between elements."""
        if not HAS_PYSIDE6 or not self.focusable_widgets:
            return False
            
        try:
            if event.key() == Qt.Key_Tab:
                # Move to next widget
                self.current_focus_index = (self.current_focus_index + 1) % len(self.focusable_widgets)
                self.focusable_widgets[self.current_focus_index].setFocus()
                return True
                
            elif event.key() == Qt.Key_Backtab or (event.key() == Qt.Key_Tab and event.modifiers() & Qt.ShiftModifier):
                # Move to previous widget
                self.current_focus_index = (self.current_focus_index - 1) % len(self.focusable_widgets)
                self.focusable_widgets[self.current_focus_index].setFocus()
                return True
                
        except Exception as e:
            self.logger.error(f"Error handling tab navigation: {e}")
            
        return False
    
    def setup_shortcuts(self, shortcuts: Dict[str, Callable]) -> None:
        """Set up keyboard shortcuts for actions."""
        if not HAS_PYSIDE6 or not self.widget:
            return
            
        try:
            for key_sequence, callback in shortcuts.items():
                shortcut = QShortcut(QKeySequence(key_sequence), self.widget)
                shortcut.activated.connect(callback)
                self.shortcuts[key_sequence] = shortcut
                
            self.logger.info(f"Set up {len(shortcuts)} keyboard shortcuts")
            
        except Exception as e:
            self.logger.error(f"Error setting up shortcuts: {e}")
    
    def setup_default_shortcuts(self) -> None:
        """Set up default application shortcuts."""
        if not HAS_PYSIDE6:
            return
            
        default_shortcuts = {
            "Ctrl+S": self._trigger_scan,
            "Ctrl+D": self._trigger_clean,
            "Ctrl+,": self._open_settings,
            "F5": self._refresh,
            "Ctrl+A": self._select_all,
            "F1": self._show_help,
            "Ctrl+Q": self._quit_application,
            "Escape": self._cancel_operation,
            "Enter": self._activate_focused,
            "Space": self._toggle_selection
        }
        
        self.setup_shortcuts(default_shortcuts)
    
    def _trigger_scan(self):
        """Trigger scan operation."""
        # This will be connected to the actual scan function
        self.logger.info("Scan shortcut triggered")
    
    def _trigger_clean(self):
        """Trigger clean operation."""
        # This will be connected to the actual clean function
        self.logger.info("Clean shortcut triggered")
    
    def _open_settings(self):
        """Open settings dialog."""
        # This will be connected to the settings dialog
        self.logger.info("Settings shortcut triggered")
    
    def _refresh(self):
        """Refresh current view."""
        self.logger.info("Refresh shortcut triggered")
    
    def _select_all(self):
        """Select all items in current view."""
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, (QTableWidget, QTreeWidget, QListWidget)):
            focused_widget.selectAll()
        self.logger.info("Select all shortcut triggered")
    
    def _show_help(self):
        """Show help dialog."""
        self.logger.info("Help shortcut triggered")
    
    def _quit_application(self):
        """Quit the application."""
        if self.widget:
            self.widget.close()
    
    def _cancel_operation(self):
        """Cancel current operation."""
        self.logger.info("Cancel shortcut triggered")
    
    def _activate_focused(self):
        """Activate the currently focused widget."""
        focused_widget = QApplication.focusWidget()
        if focused_widget and hasattr(focused_widget, 'click'):
            focused_widget.click()
    
    def _toggle_selection(self):
        """Toggle selection of focused item."""
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, (QTableWidget, QTreeWidget, QListWidget)):
            current_item = focused_widget.currentItem()
            if current_item:
                current_item.setSelected(not current_item.isSelected())
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events for custom keyboard handling."""
        if event.type() == QEvent.KeyPress:
            key_event = event
            
            # Handle tab navigation
            if self.handle_tab_navigation(key_event):
                return True
                
            # Handle arrow key navigation in lists/tables
            if self._handle_arrow_navigation(key_event):
                return True
        
        return False
    
    def _handle_arrow_navigation(self, event: QKeyEvent) -> bool:
        """Handle arrow key navigation in list widgets."""
        focused_widget = QApplication.focusWidget()
        
        if isinstance(focused_widget, (QTableWidget, QTreeWidget, QListWidget)):
            # Let the widget handle arrow keys naturally
            return False
            
        # For other widgets, implement custom arrow navigation
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            return self._navigate_with_arrows(event.key())
            
        return False
    
    def _navigate_with_arrows(self, key: int) -> bool:
        """Navigate between widgets using arrow keys."""
        if not self.focusable_widgets:
            return False
            
        current_widget = QApplication.focusWidget()
        if current_widget not in self.focusable_widgets:
            return False
            
        current_index = self.focusable_widgets.index(current_widget)
        
        if key == Qt.Key_Down or key == Qt.Key_Right:
            next_index = (current_index + 1) % len(self.focusable_widgets)
        else:  # Up or Left
            next_index = (current_index - 1) % len(self.focusable_widgets)
            
        self.focusable_widgets[next_index].setFocus()
        self.current_focus_index = next_index
        return True
    
    def add_widget_to_navigation(self, widget: Any) -> None:
        """Add a widget to the navigation order."""
        if widget not in self.focusable_widgets:
            self.focusable_widgets.append(widget)
            self._setup_tab_order()
    
    def remove_widget_from_navigation(self, widget: Any) -> None:
        """Remove a widget from the navigation order."""
        if widget in self.focusable_widgets:
            self.focusable_widgets.remove(widget)
            self._setup_tab_order()
    
    def get_shortcut_info(self) -> Dict[str, str]:
        """Get information about available shortcuts."""
        return {
            "Ctrl+S": "Start Scan",
            "Ctrl+D": "Clean Selected Items", 
            "Ctrl+,": "Open Settings",
            "F5": "Refresh View",
            "Ctrl+A": "Select All",
            "F1": "Show Help",
            "Ctrl+Q": "Quit Application",
            "Escape": "Cancel Operation",
            "Enter": "Activate Focused Item",
            "Space": "Toggle Selection",
            "Tab": "Next Widget",
            "Shift+Tab": "Previous Widget",
            "Arrow Keys": "Navigate Items"
        }