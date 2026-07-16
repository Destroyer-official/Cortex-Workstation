"""
Accessibility module for Cortex Cleaner.

This module provides accessibility features including:
- Keyboard navigation support
- Screen reader compatibility
- High contrast and visual accessibility features
"""

from .keyboard_handler import KeyboardHandler
from .screen_reader import ScreenReaderSupport
from .themes import AccessibilityThemes, get_theme_manager, apply_accessibility_theme

__version__ = "1.0.0"
__all__ = [
    "KeyboardHandler",
    "ScreenReaderSupport", 
    "AccessibilityThemes",
    "get_theme_manager",
    "apply_accessibility_theme",
    "setup_accessibility",
    "setup_full_accessibility"
]

def setup_accessibility(widget):
    """Set up accessibility features for a widget."""
    keyboard_handler = KeyboardHandler(widget)
    screen_reader = ScreenReaderSupport(widget)
    
    keyboard_handler.setup_keyboard_navigation()
    screen_reader.setup_accessible_descriptions()
    
    return keyboard_handler, screen_reader

def setup_full_accessibility(widget, enable_shortcuts=True, enable_announcements=True):
    """Set up full accessibility features with options."""
    keyboard_handler = KeyboardHandler(widget)
    screen_reader = ScreenReaderSupport(widget)
    
    # Set up keyboard navigation
    keyboard_handler.setup_keyboard_navigation()
    
    # Set up default shortcuts if enabled
    if enable_shortcuts:
        keyboard_handler.setup_default_shortcuts()
    
    # Set up screen reader support
    screen_reader.setup_accessible_descriptions()
    
    # Announce application ready if enabled
    if enable_announcements:
        screen_reader.announce_changes("Cortex Cleaner application ready")
    
    return keyboard_handler, screen_reader