"""
Internationalization module for Deep Cleaner.

This module provides internationalization and localization support including:
- Translation management for multiple languages
- Locale detection and switching
- Text formatting for different regions
"""

from .translator import Translator, get_translator, set_global_locale, translate, _
from .settings_integration import I18nManager, I18nSettingsWidget, get_i18n_manager

__version__ = "1.0.0"
__all__ = [
    "Translator",
    "get_translator", 
    "set_global_locale",
    "translate",
    "_",
    "get_available_locales",
    "set_locale",
    "I18nManager",
    "I18nSettingsWidget", 
    "get_i18n_manager"
]

# Convenience functions
def get_available_locales():
    """Get available locales from default translator."""
    translator = get_translator()
    return translator.get_available_locales()

def set_locale(locale: str):
    """Set locale for default translator."""
    set_global_locale(locale)