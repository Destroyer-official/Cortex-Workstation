"""Navigation controller for Cortex Cleaner GUI."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget,
    QListWidgetItem, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont
from typing import Dict, Any, Optional

from .icon_helper import IconHelper

class NavigationController(QWidget):
    """Modern side-panel navigation controller that replaces QTabWidget."""
    
    # Signals
    tab_changed = Signal(int)  # Emitted when tab changes
    tab_requested = Signal(str)  # Emitted when a specific tab is requested
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Internal state
        self._tabs: Dict[str, Dict[str, Any]] = {}
        self._current_index = -1
        
        # Setup UI
        self.setup_ui()
        self.setup_styling()
        
    def setup_ui(self):
        """Set up the navigation UI components."""
        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Navigation panel (left side)
        self.nav_panel = self.create_navigation_panel()
        main_layout.addWidget(self.nav_panel)
        
        # Content area (right side)
        self.content_stack = QStackedWidget()
        self.content_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.content_stack)
        main_layout.setStretch(0, 0)  # Navigation panel - fixed
        main_layout.setStretch(1, 1)  # Content area - expandable
        
    def create_navigation_panel(self) -> QWidget:
        """Create the left navigation panel."""
        panel = QWidget()
        panel.setFixedWidth(180)  # Fixed width as per requirements
        panel.setObjectName("navigationPanel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Navigation title
        title_label = QLabel("Cortex Cleaner")
        title_label.setObjectName("navigationTitle")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Navigation list
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navigationList")
        self.nav_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Connect navigation selection
        self.nav_list.currentRowChanged.connect(self.on_navigation_changed)
        
        layout.addWidget(self.nav_list)
        
        return panel
        
    def setup_styling(self):
        """Apply professional styling to the navigation components."""
        self.setStyleSheet("""
            QWidget#navigationPanel {
                background-color: #f8f9fa;
                border-right: 1px solid #dee2e6;
            }
            
            QLabel#navigationTitle {
                color: #495057;
                padding: 8px 0px;
                border-bottom: 1px solid #dee2e6;
                margin-bottom: 8px;
            }
            
            QListWidget#navigationList {
                background-color: transparent;
                border: none;
                outline: none;
                selection-background-color: #007bff;
                selection-color: white;
            }
            
            QListWidget#navigationList::item {
                padding: 12px 8px;
                border-radius: 6px;
                margin: 2px 0px;
                color: #495057;
                font-weight: 500;
            }
            
            QListWidget#navigationList::item:hover {
                background-color: #e9ecef;
                color: #212529;
            }
            
            QListWidget#navigationList::item:selected {
                background-color: #007bff;
                color: white;
                font-weight: 600;
            }
            
            QListWidget#navigationList::item:selected:hover {
                background-color: #0056b3;
            }
        """)
        
    def add_tab(self, widget: QWidget, name: str, icon: Optional[QIcon] = None) -> int:
        """
        Add a new tab to the navigation system.
        
        Args:
            widget: The widget to display when this tab is selected
            name: Display name for the navigation item
            icon: Optional icon for the navigation item
            
        Returns:
            Index of the added tab
        """
        index = self.content_stack.addWidget(widget)
        
        # Create navigation item
        nav_item = QListWidgetItem()
        nav_item.setText(name)
        if icon:
            nav_item.setIcon(icon)
        
        # Store tab information
        tab_info = {
            'widget': widget,
            'name': name,
            'icon': icon,
            'index': index,
            'nav_item': nav_item
        }
        self._tabs[name] = tab_info
        
        # Add to navigation list
        self.nav_list.addItem(nav_item)
        
        # If this is the first tab, select it
        if len(self._tabs) == 1:
            self.set_current_tab(0)
            
        return index
        
    def remove_tab(self, name: str) -> bool:
        """
        Remove a tab from the navigation system.
        
        Args:
            name: Name of the tab to remove
            
        Returns:
            True if tab was removed, False if not found
        """
        if name not in self._tabs:
            return False
            
        tab_info = self._tabs[name]
        
        # Remove from stack
        self.content_stack.removeWidget(tab_info['widget'])
        
        # Remove from navigation list
        row = self.nav_list.row(tab_info['nav_item'])
        self.nav_list.takeItem(row)
        
        # Remove from internal tracking
        del self._tabs[name]
        
        # Update current index if needed
        if self._current_index >= len(self._tabs):
            self._current_index = len(self._tabs) - 1
            if self._current_index >= 0:
                self.nav_list.setCurrentRow(self._current_index)
                
        return True
        
    def set_current_tab(self, index: int) -> bool:
        """
        Set the current tab by index.
        
        Args:
            index: Index of the tab to select
            
        Returns:
            True if successful, False if index is invalid
        """
        if 0 <= index < len(self._tabs):
            self._current_index = index
            self.nav_list.setCurrentRow(index)
            self.content_stack.setCurrentIndex(index)
            self.tab_changed.emit(index)
            return True
        return False
        
    def set_current_tab_by_name(self, name: str) -> bool:
        """
        Set the current tab by name.
        
        Args:
            name: Name of the tab to select
            
        Returns:
            True if successful, False if tab not found
        """
        if name in self._tabs:
            tab_info = self._tabs[name]
            return self.set_current_tab(tab_info['index'])
        return False
        
    def get_current_tab_name(self) -> Optional[str]:
        """Get the name of the currently selected tab."""
        if self._current_index >= 0:
            for name, tab_info in self._tabs.items():
                if tab_info['index'] == self._current_index:
                    return name
        return None
        
    def get_current_widget(self) -> Optional[QWidget]:
        """Get the currently displayed widget."""
        return self.content_stack.currentWidget()
        
    def get_tab_count(self) -> int:
        """Get the total number of tabs."""
        return len(self._tabs)
        
    def get_tab_names(self) -> list:
        """Get a list of all tab names."""
        return list(self._tabs.keys())
        
    def on_navigation_changed(self, current_row: int):
        """Handle navigation selection changes."""
        if current_row >= 0 and current_row != self._current_index:
            self._current_index = current_row
            self.content_stack.setCurrentIndex(current_row)
            self.tab_changed.emit(current_row)
            
            # Emit tab requested signal with name
            tab_name = self.get_current_tab_name()
            if tab_name:
                self.tab_requested.emit(tab_name)
                
    def clear_tabs(self):
        """Remove all tabs from the navigation system."""
        # Clear the stack widget
        while self.content_stack.count() > 0:
            widget = self.content_stack.widget(0)
            self.content_stack.removeWidget(widget)
            
        # Clear the navigation list
        self.nav_list.clear()
        
        # Clear internal tracking
        self._tabs.clear()
        self._current_index = -1
        
    def update_tab_icon(self, name: str, icon: QIcon) -> bool:
        """
        Update the icon for a specific tab.
        
        Args:
            name: Name of the tab to update
            icon: New icon for the tab
            
        Returns:
            True if successful, False if tab not found
        """
        if name in self._tabs:
            tab_info = self._tabs[name]
            tab_info['icon'] = icon
            tab_info['nav_item'].setIcon(icon)
            return True
        return False
        
    def update_tab_name(self, old_name: str, new_name: str) -> bool:
        """
        Update the display name for a specific tab.
        
        Args:
            old_name: Current name of the tab
            new_name: New name for the tab
            
        Returns:
            True if successful, False if tab not found
        """
        if old_name in self._tabs:
            tab_info = self._tabs[old_name]
            tab_info['name'] = new_name
            tab_info['nav_item'].setText(new_name)
            
            # Update internal tracking
            self._tabs[new_name] = tab_info
            del self._tabs[old_name]
            return True
        return False
        
    def setup_default_icons(self):
        """Set up default icons for all tabs using the IconHelper."""
        default_icons = IconHelper.get_navigation_icons()
        
        for name, tab_info in self._tabs.items():
            if name in default_icons and not tab_info['icon']:
                self.update_tab_icon(name, default_icons[name])
                
    def add_tab_with_default_icon(self, widget: QWidget, name: str) -> int:
        """
        Add a tab with a default icon from the IconHelper.
        
        Args:
            widget: The widget to display when this tab is selected
            name: Display name for the navigation item
            
        Returns:
            Index of the added tab
        """
        # Get default icon for this tab name
        default_icons = IconHelper.get_navigation_icons()
        icon = default_icons.get(name, None)
        
        return self.add_tab(widget, name, icon)