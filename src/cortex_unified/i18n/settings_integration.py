"""
Settings integration for internationalization and accessibility.
"""

from typing import Dict, Any, Optional, Callable
import logging
from pathlib import Path

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
        QCheckBox, QSpinBox, QGroupBox, QFormLayout, QPushButton
    )
    from PySide6.QtCore import QSettings, Signal, QObject
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

from .translator import get_translator, set_global_locale, translate as _
from cortex_unified.accessibility import get_theme_manager

class I18nSettingsWidget(QWidget):
    """Widget for internationalization and accessibility settings."""
    
    # Signals
    locale_changed = Signal(str)
    theme_changed = Signal(str)
    accessibility_changed = Signal(dict)
    
    def __init__(self, parent=None):
        """Initialize settings widget."""
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.settings = QSettings()
        self.translator = get_translator()
        self.theme_manager = get_theme_manager()
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Set up the user interface."""
        if not HAS_PYSIDE6:
            return
            
        layout = QVBoxLayout(self)
        
        # Language settings
        lang_group = QGroupBox(_("settings.language"))
        lang_layout = QFormLayout(lang_group)
        
        self.language_combo = QComboBox()
        self.populate_languages()
        lang_layout.addRow(_("settings.language_selection"), self.language_combo)
        
        layout.addWidget(lang_group)
        
        # Accessibility settings
        a11y_group = QGroupBox(_("settings.accessibility"))
        a11y_layout = QFormLayout(a11y_group)
        
        self.theme_combo = QComboBox()
        self.populate_themes()
        a11y_layout.addRow(_("settings.theme"), self.theme_combo)
        
        self.high_contrast_cb = QCheckBox(_("settings.high_contrast"))
        a11y_layout.addRow(self.high_contrast_cb)
        
        self.keyboard_nav_cb = QCheckBox(_("settings.keyboard_navigation"))
        a11y_layout.addRow(self.keyboard_nav_cb)
        
        self.screen_reader_cb = QCheckBox(_("settings.screen_reader"))
        a11y_layout.addRow(self.screen_reader_cb)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(10)
        a11y_layout.addRow(_("settings.font_size"), self.font_size_spin)
        
        layout.addWidget(a11y_group)
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        self.high_contrast_cb.toggled.connect(self.on_accessibility_changed)
        self.keyboard_nav_cb.toggled.connect(self.on_accessibility_changed)
        self.screen_reader_cb.toggled.connect(self.on_accessibility_changed)
        self.font_size_spin.valueChanged.connect(self.on_accessibility_changed) 
   
    def populate_languages(self):
        """Populate language combo box."""
        if not HAS_PYSIDE6:
            return
            
        locales = self.translator.get_available_locales()
        self.language_combo.clear()
        
        for locale in locales:
            locale_info = self.translator.get_locale_info(locale)
            display_name = locale_info.get('native_name', locale)
            self.language_combo.addItem(display_name, locale)
    
    def populate_themes(self):
        """Populate theme combo box."""
        if not HAS_PYSIDE6:
            return
            
        themes = self.theme_manager.get_available_themes()
        self.theme_combo.clear()
        
        for theme_id, theme_name in themes.items():
            self.theme_combo.addItem(theme_name, theme_id)
    
    def load_settings(self):
        """Load settings from QSettings."""
        if not HAS_PYSIDE6:
            return
            
        # Load language setting
        current_locale = self.settings.value("i18n/locale", "en")
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_locale:
                self.language_combo.setCurrentIndex(i)
                break
        
        # Load theme setting
        current_theme = self.settings.value("accessibility/theme", "default")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        # Load accessibility settings
        self.high_contrast_cb.setChecked(
            self.settings.value("accessibility/high_contrast", False, type=bool)
        )
        self.keyboard_nav_cb.setChecked(
            self.settings.value("accessibility/keyboard_navigation", True, type=bool)
        )
        self.screen_reader_cb.setChecked(
            self.settings.value("accessibility/screen_reader", True, type=bool)
        )
        self.font_size_spin.setValue(
            self.settings.value("accessibility/font_size", 10, type=int)
        )
    
    def save_settings(self):
        """Save settings to QSettings."""
        if not HAS_PYSIDE6:
            return
            
        # Save language
        current_locale = self.language_combo.currentData()
        if current_locale:
            self.settings.setValue("i18n/locale", current_locale)
        
        # Save theme
        current_theme = self.theme_combo.currentData()
        if current_theme:
            self.settings.setValue("accessibility/theme", current_theme)
        
        # Save accessibility settings
        self.settings.setValue("accessibility/high_contrast", self.high_contrast_cb.isChecked())
        self.settings.setValue("accessibility/keyboard_navigation", self.keyboard_nav_cb.isChecked())
        self.settings.setValue("accessibility/screen_reader", self.screen_reader_cb.isChecked())
        self.settings.setValue("accessibility/font_size", self.font_size_spin.value())
        
        self.settings.sync()
    
    def on_language_changed(self, language_name):
        """Handle language change."""
        locale = self.language_combo.currentData()
        if locale:
            set_global_locale(locale)
            self.save_settings()
            self.locale_changed.emit(locale)
            self.logger.info(f"Language changed to: {locale}")
    
    def on_theme_changed(self, theme_name):
        """Handle theme change."""
        theme_id = self.theme_combo.currentData()
        if theme_id:
            self.theme_manager.apply_theme(theme_id)
            self.save_settings()
            self.theme_changed.emit(theme_id)
            self.logger.info(f"Theme changed to: {theme_id}")
    
    def on_accessibility_changed(self):
        """Handle accessibility setting changes."""
        settings = {
            'high_contrast': self.high_contrast_cb.isChecked(),
            'keyboard_navigation': self.keyboard_nav_cb.isChecked(),
            'screen_reader': self.screen_reader_cb.isChecked(),
            'font_size': self.font_size_spin.value()
        }
        
        # Apply high contrast if enabled
        if settings['high_contrast']:
            self.theme_manager.apply_high_contrast_theme()
        
        self.save_settings()
        self.accessibility_changed.emit(settings)
        self.logger.info(f"Accessibility settings changed: {settings}")

class I18nManager:
    """Manager for internationalization and accessibility integration."""
    
    def __init__(self):
        """Initialize i18n manager."""
        self.logger = logging.getLogger(__name__)
        self.settings = QSettings() if HAS_PYSIDE6 else None
        self.translator = get_translator()
        self.theme_manager = get_theme_manager()
        
        # Load saved settings
        self.load_saved_settings()
    
    def load_saved_settings(self):
        """Load and apply saved settings."""
        if not self.settings:
            return
            
        try:
            # Load and apply locale
            saved_locale = self.settings.value("i18n/locale", "en")
            set_global_locale(saved_locale)
            
            # Load and apply theme
            saved_theme = self.settings.value("accessibility/theme", "default")
            self.theme_manager.apply_theme(saved_theme)
            
            self.logger.info(f"Loaded settings - Locale: {saved_locale}, Theme: {saved_theme}")
            
        except Exception as e:
            self.logger.error(f"Error loading saved settings: {e}")
    
    def create_settings_widget(self, parent=None):
        """Create settings widget."""
        if HAS_PYSIDE6:
            return I18nSettingsWidget(parent)
        return None
    
    def get_current_locale(self) -> str:
        """Get current locale."""
        return self.translator.locale
    
    def get_current_theme(self) -> str:
        """Get current theme."""
        return self.theme_manager.get_current_theme()
    
    def is_rtl_layout(self) -> bool:
        """Check if current locale uses RTL layout."""
        return self.translator.is_rtl_locale()

# Global i18n manager instance
_i18n_manager = None

def get_i18n_manager() -> I18nManager:
    """Get the global i18n manager instance."""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager