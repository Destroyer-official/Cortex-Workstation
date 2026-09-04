"""
Keyboard-only navigation: focus cycling, tab order, and app shortcuts.

An event filter on the host widget intercepts Tab/arrow presses so
traversal works uniformly across widgets that lack built-in handling.
Default shortcut actions are stubs awaiting wiring to real operations.
"""

from typing import Dict, Any, Callable
import logging

try:
    from PySide6.QtWidgets import QWidget, QApplication, QTabWidget, QTableWidget, QTreeWidget, QListWidget
    from PySide6.QtCore import Qt, QObject, QEvent
    from PySide6.QtGui import QKeySequence, QShortcut, QKeyEvent
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

class KeyboardHandler(QObject):
    """Focus management and shortcut routing for a host widget.

    Owns the ordered ``focusable_widgets`` list driving Tab/Shift+Tab
    and arrow-key traversal, plus a QShortcut table for app actions.
    """
    
    def __init__(self, widget: Any = None):
        """Bind to ``widget``; logging-only when PySide6 is absent.

        Initializes the instance and configures internal state.

        Args:
            widget (Any): The widget parameter.
        """
        super().__init__()
        self.widget = widget
        self.shortcuts = {}
        self.focusable_widgets = []
        self.current_focus_index = 0
        self.logger = logging.getLogger(__name__)
        
        if not HAS_PYSIDE6:
            self.logger.warning("PySide6 not available, keyboard navigation disabled")
    
    def setup_keyboard_navigation(self) -> None:
        """Discover focusable children, fix tab order, install the filter.

        Manages setup keyboard navigation operations and coordinates related state changes for the component.
        """
        if not HAS_PYSIDE6 or not self.widget:
            return
            
        try:
            self._find_focusable_widgets()
            
            self._setup_tab_order()
            
            # Sits ahead of Qt defaults so Tab/arrows can be redirected
            self.widget.installEventFilter(self)
            
            if self.focusable_widgets:
                self.focusable_widgets[0].setFocus()
                
            self.logger.info(f"Keyboard navigation set up for {len(self.focusable_widgets)} widgets")
            
        except Exception as e:
            self.logger.error(f"Error setting up keyboard navigation: {e}")
    
    def _find_focusable_widgets(self) -> None:
        """Collect visible/enabled widgets sorted top-to-bottom, left-to-right.

        Positional order stands in for a designer-defined tab chain, which
        Qt would otherwise derive from widget creation order.
        """
        if not self.widget:
            return
            
        self.focusable_widgets = []
        
        def find_widgets(parent):
            """find_widgets.

            Manages find widgets operations and coordinates related state changes for the component.

            Args:
                parent: Parent window or shell controller instance.
            """
            for child in parent.findChildren(QWidget):
                if (child.focusPolicy() != Qt.NoFocus and 
                    child.isVisible() and 
                    child.isEnabled()):
                    self.focusable_widgets.append(child)
        
        find_widgets(self.widget)
        
        # Reading order: row by row, then column within a row
        self.focusable_widgets.sort(key=lambda w: (w.y(), w.x()))
    
    def _setup_tab_order(self) -> None:
        """Chain consecutive widgets so Qt Tab matches the visual order.

        Manages setup tab order operations and coordinates related state changes for the component.
        """
        if len(self.focusable_widgets) < 2:
            return
            
        try:
            for i in range(len(self.focusable_widgets) - 1):
                QWidget.setTabOrder(
                    self.focusable_widgets[i], 
                    self.focusable_widgets[i + 1]
                )
        except Exception as e:
            self.logger.error(f"Error setting tab order: {e}")
    
    def handle_tab_navigation(self, event: QKeyEvent) -> bool:
        """Advance/wrap focus on Tab and Shift+Tab; True when consumed.

        Manages handle tab navigation operations and coordinates related state changes for the component.

        Args:
            event (QKeyEvent): The Qt event object.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if not HAS_PYSIDE6 or not self.focusable_widgets:
            return False
            
        try:
            if event.key() == Qt.Key_Tab:
                self.current_focus_index = (self.current_focus_index + 1) % len(self.focusable_widgets)
                self.focusable_widgets[self.current_focus_index].setFocus()
                return True
                
            elif event.key() == Qt.Key_Backtab or (event.key() == Qt.Key_Tab and event.modifiers() & Qt.ShiftModifier):
                self.current_focus_index = (self.current_focus_index - 1) % len(self.focusable_widgets)
                self.focusable_widgets[self.current_focus_index].setFocus()
                return True
                
        except Exception as e:
            self.logger.error(f"Error handling tab navigation: {e}")
            
        return False
    
    def setup_shortcuts(self, shortcuts: Dict[str, Callable]) -> None:
        """Register a QShortcut for each key sequence -> callback pair.

        Manages setup shortcuts operations and coordinates related state changes for the component.

        Args:
            shortcuts (Dict[str, Callable]): The shortcuts parameter.
        """
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
        """Install the app-wide scheme (scan, clean, settings, quit...).

        Manages setup default shortcuts operations and coordinates related state changes for the component.
        """
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
        """Dispatch scan trigger to active window or page.

        Manages trigger scan operations and coordinates related state changes for the component.
        """
        self.logger.info("Scan shortcut triggered")
        if self.widget:
            for method in ("start_scan", "_start_scan", "_scan", "scan"):
                fn = getattr(self.widget, method, None)
                if callable(fn):
                    fn()
                    break

    def _trigger_clean(self):
        """Dispatch clean trigger to active window or page.

        Manages trigger clean operations and coordinates related state changes for the component.
        """
        self.logger.info("Clean shortcut triggered")
        if self.widget:
            for method in ("start_clean", "_start_clean", "_clean", "clean", "_cleanup"):
                fn = getattr(self.widget, method, None)
                if callable(fn):
                    fn()
                    break

    def _open_settings(self):
        """Dispatch settings navigation to active window.

        Manages open settings operations and coordinates related state changes for the component.
        """
        self.logger.info("Settings shortcut triggered")
        if self.widget and hasattr(self.widget, "_select"):
            self.widget._select("settings")

    def _refresh(self):
        """Fetch and reload the latest data entries into the view.

        Queries the underlying system service or storage cache and refreshes view tables with up-to-date state.
        """
        self.logger.info("Refresh shortcut triggered")
        if self.widget:
            for method in ("_refresh", "refresh", "_reload_current", "_autoload"):
                fn = getattr(self.widget, method, None)
                if callable(fn):
                    fn()
                    break

    def _select_all(self):
        """SelectAll on the focused item view, when applicable.

        Manages select all operations and coordinates related state changes for the component.
        """
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, (QTableWidget, QTreeWidget, QListWidget)):
            focused_widget.selectAll()
        self.logger.info("Select all shortcut triggered")

    def _show_help(self):
        """_show_help.

        Manages show help operations and coordinates related state changes for the component.
        """
        self.logger.info("Help shortcut triggered")
        if self.widget and hasattr(self.widget, "_select"):
            self.widget._select("report")

    def _quit_application(self):
        """Close the host widget's window.

        Manages quit application operations and coordinates related state changes for the component.
        """
        if self.widget:
            self.widget.close()

    def _cancel_operation(self):
        """Cancel any running operation in the host widget.

        Manages cancel operation operations and coordinates related state changes for the component.
        """
        self.logger.info("Cancel shortcut triggered")
        if self.widget:
            for method in ("cancel", "_cancel", "stop", "_stop", "cancel_scan"):
                fn = getattr(self.widget, method, None)
                if callable(fn):
                    fn()
                    break
    
    def _activate_focused(self):
        """Click the focused widget if it supports click().

        Manages activate focused operations and coordinates related state changes for the component.
        """
        focused_widget = QApplication.focusWidget()
        if focused_widget and hasattr(focused_widget, 'click'):
            focused_widget.click()
    
    def _toggle_selection(self):
        """Invert selection of the current item in an item view.

        Toggles selection states or operational modes, recalculating active selection counts and enabling/disabling dependent actions.
        """
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, (QTableWidget, QTreeWidget, QListWidget)):
            current_item = focused_widget.currentItem()
            if current_item:
                current_item.setSelected(not current_item.isSelected())
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter monitored Qt events for target child widgets.

        Intercepts specific mouse, keyboard, or focus events to provide custom interactive behaviors before standard event dispatch.

        Args:
            obj (QObject): The obj parameter.
            event (QEvent): The Qt event object.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if event.type() == QEvent.KeyPress:
            key_event = event
            
            if self.handle_tab_navigation(key_event):
                return True
                
            if self._handle_arrow_navigation(key_event):
                return True
        
        return False
    
    def _handle_arrow_navigation(self, event: QKeyEvent) -> bool:
        """Route arrows to custom traversal unless an item view owns them.

        Manages handle arrow navigation operations and coordinates related state changes for the component.

        Args:
            event (QKeyEvent): The Qt event object.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        focused_widget = QApplication.focusWidget()
        
        if isinstance(focused_widget, (QTableWidget, QTreeWidget, QListWidget)):
            # Item views already move their own selection with arrows
            return False
            
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            return self._navigate_with_arrows(event.key())
            
        return False
    
    def _navigate_with_arrows(self, key: int) -> bool:
        """Step focus forward/backward through focusable_widgets.

        Manages navigate with arrows operations and coordinates related state changes for the component.

        Args:
            key (int): The key parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
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
        """Append to the traversal order and rechain tab order.

        Manages add widget to navigation operations and coordinates related state changes for the component.

        Args:
            widget (Any): The widget parameter.
        """
        if widget not in self.focusable_widgets:
            self.focusable_widgets.append(widget)
            self._setup_tab_order()
    
    def remove_widget_from_navigation(self, widget: Any) -> None:
        """remove_widget_from_navigation.

        Manages remove widget from navigation operations and coordinates related state changes for the component.

        Args:
            widget (Any): The widget parameter.
        """
        if widget in self.focusable_widgets:
            self.focusable_widgets.remove(widget)
            self._setup_tab_order()
    
    def get_shortcut_info(self) -> Dict[str, str]:
        """Human-readable shortcut cheat sheet for help displays.

        Manages get shortcut info operations and coordinates related state changes for the component.

        Returns:
            Dict[str, str]: Dictionary mapping identifiers to status or values.
        """
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