"""
High contrast and accessibility themes for Cortex Cleaner.
"""

from typing import Dict, Any, Optional
import logging

try:
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPalette, QColor
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

class AccessibilityThemes:
    """Manages high contrast and accessibility themes."""
    
    def __init__(self):
        """Initialize theme manager."""
        self.logger = logging.getLogger(__name__)
        self.current_theme = "default"
        self.original_palette = None
        
        if HAS_PYSIDE6:
            app = QApplication.instance()
            if app:
                self.original_palette = app.palette()
    
    def apply_high_contrast_theme(self, widget: Optional[QWidget] = None) -> None:
        """Apply high contrast theme."""
        if not HAS_PYSIDE6:
            self.logger.warning("PySide6 not available, cannot apply theme")
            return
            
        try:
            app = QApplication.instance()
            if not app:
                return
                
            # Create high contrast palette
            palette = QPalette()
            
            # High contrast colors
            black = QColor(0, 0, 0)
            white = QColor(255, 255, 255)
            dark_gray = QColor(64, 64, 64)
            light_gray = QColor(192, 192, 192)
            blue = QColor(0, 120, 215)  # Accessible blue
            yellow = QColor(255, 255, 0)  # High contrast yellow
            
            # Set palette colors
            palette.setColor(QPalette.Window, black)
            palette.setColor(QPalette.WindowText, white)
            palette.setColor(QPalette.Base, black)
            palette.setColor(QPalette.AlternateBase, dark_gray)
            palette.setColor(QPalette.Text, white)
            palette.setColor(QPalette.Button, dark_gray)
            palette.setColor(QPalette.ButtonText, white)
            palette.setColor(QPalette.Highlight, blue)
            palette.setColor(QPalette.HighlightedText, white)
            palette.setColor(QPalette.Link, blue)
            palette.setColor(QPalette.LinkVisited, blue)
            
            # Disabled colors
            palette.setColor(QPalette.Disabled, QPalette.WindowText, light_gray)
            palette.setColor(QPalette.Disabled, QPalette.Text, light_gray)
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, light_gray)
            
            # Apply palette
            if widget:
                widget.setPalette(palette)
            else:
                app.setPalette(palette)
                
            self.current_theme = "high_contrast"
            self.logger.info("High contrast theme applied")
            
        except Exception as e:
            self.logger.error(f"Error applying high contrast theme: {e}")
    
    def apply_dark_theme(self, widget: Optional[QWidget] = None) -> None:
        """Apply dark theme with good contrast."""
        if not HAS_PYSIDE6:
            return
            
        try:
            app = QApplication.instance()
            if not app:
                return
                
            palette = QPalette()
            
            # Dark theme colors with good contrast
            dark_bg = QColor(53, 53, 53)
            darker_bg = QColor(35, 35, 35)
            light_text = QColor(255, 255, 255)
            gray_text = QColor(200, 200, 200)
            blue_accent = QColor(42, 130, 218)
            
            palette.setColor(QPalette.Window, dark_bg)
            palette.setColor(QPalette.WindowText, light_text)
            palette.setColor(QPalette.Base, darker_bg)
            palette.setColor(QPalette.AlternateBase, dark_bg)
            palette.setColor(QPalette.Text, light_text)
            palette.setColor(QPalette.Button, dark_bg)
            palette.setColor(QPalette.ButtonText, light_text)
            palette.setColor(QPalette.Highlight, blue_accent)
            palette.setColor(QPalette.HighlightedText, light_text)
            
            # Disabled colors
            palette.setColor(QPalette.Disabled, QPalette.WindowText, gray_text)
            palette.setColor(QPalette.Disabled, QPalette.Text, gray_text)
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, gray_text)
            
            if widget:
                widget.setPalette(palette)
            else:
                app.setPalette(palette)
                
            self.current_theme = "dark"
            self.logger.info("Dark theme applied")
            
        except Exception as e:
            self.logger.error(f"Error applying dark theme: {e}")
    
    def apply_light_theme(self, widget: Optional[QWidget] = None) -> None:
        """Apply light theme with good contrast."""
        if not HAS_PYSIDE6:
            return
            
        try:
            app = QApplication.instance()
            if not app:
                return
                
            palette = QPalette()
            
            # Light theme colors
            light_bg = QColor(240, 240, 240)
            white_bg = QColor(255, 255, 255)
            dark_text = QColor(0, 0, 0)
            gray_text = QColor(100, 100, 100)
            blue_accent = QColor(0, 120, 215)
            
            palette.setColor(QPalette.Window, light_bg)
            palette.setColor(QPalette.WindowText, dark_text)
            palette.setColor(QPalette.Base, white_bg)
            palette.setColor(QPalette.AlternateBase, light_bg)
            palette.setColor(QPalette.Text, dark_text)
            palette.setColor(QPalette.Button, light_bg)
            palette.setColor(QPalette.ButtonText, dark_text)
            palette.setColor(QPalette.Highlight, blue_accent)
            palette.setColor(QPalette.HighlightedText, white_bg)
            
            # Disabled colors
            palette.setColor(QPalette.Disabled, QPalette.WindowText, gray_text)
            palette.setColor(QPalette.Disabled, QPalette.Text, gray_text)
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, gray_text)
            
            if widget:
                widget.setPalette(palette)
            else:
                app.setPalette(palette)
                
            self.current_theme = "light"
            self.logger.info("Light theme applied")
            
        except Exception as e:
            self.logger.error(f"Error applying light theme: {e}")
    
    def restore_default_theme(self, widget: Optional[QWidget] = None) -> None:
        """Restore the original system theme."""
        if not HAS_PYSIDE6 or not self.original_palette:
            return
            
        try:
            app = QApplication.instance()
            if not app:
                return
                
            if widget:
                widget.setPalette(self.original_palette)
            else:
                app.setPalette(self.original_palette)
                
            self.current_theme = "default"
            self.logger.info("Default theme restored")
            
        except Exception as e:
            self.logger.error(f"Error restoring default theme: {e}")
    
    def get_available_themes(self) -> Dict[str, str]:
        """Get list of available themes."""
        return {
            "default": "System Default",
            "light": "Light Theme",
            "dark": "Dark Theme", 
            "high_contrast": "High Contrast"
        }
    
    def apply_theme(self, theme_name: str, widget: Optional[QWidget] = None) -> None:
        """Apply theme by name."""
        theme_methods = {
            "default": self.restore_default_theme,
            "light": self.apply_light_theme,
            "dark": self.apply_dark_theme,
            "high_contrast": self.apply_high_contrast_theme
        }
        
        method = theme_methods.get(theme_name)
        if method:
            method(widget)
        else:
            self.logger.warning(f"Unknown theme: {theme_name}")
    
    def get_current_theme(self) -> str:
        """Get current theme name."""
        return self.current_theme
    
    def is_high_contrast_enabled(self) -> bool:
        """Check if high contrast theme is enabled."""
        return self.current_theme == "high_contrast"

# Global theme manager instance
_theme_manager = None

def get_theme_manager() -> AccessibilityThemes:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = AccessibilityThemes()
    return _theme_manager

def apply_accessibility_theme(theme_name: str, widget: Optional[QWidget] = None) -> None:
    """Convenience function to apply accessibility theme."""
    theme_manager = get_theme_manager()
    theme_manager.apply_theme(theme_name, widget)