"""Backwards-compatibility alias for cortex_unified.translations."""

from cortex_unified.translations import *  # noqa: F403
from cortex_unified.translations.settings_integration import (
    I18nManager,
    I18nSettingsWidget,
    get_i18n_manager,
)
from cortex_unified.translations.translator import Translator, get_translator

__all__ = [
    "I18nManager",
    "I18nSettingsWidget",
    "Translator",
    "get_i18n_manager",
    "get_translator",
]
