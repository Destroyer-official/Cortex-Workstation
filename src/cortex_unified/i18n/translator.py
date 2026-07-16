"""
Translation and internationalization management.
"""

from typing import Dict, List, Any, Optional
import json
import os
import logging
from pathlib import Path

class Translator:
    """Manages translations and internationalization."""
    
    def __init__(self, locale: str = "en"):
        """Initialize translator with default locale."""
        self.locale = locale
        self.translations = {}
        self.locales_dir = Path(__file__).parent / "locales"
        self.fallback_locale = "en"
        self.logger = logging.getLogger(__name__)
        
        # Load initial translations
        self.load_translations(locale)
    
    def load_translations(self, locale: str) -> Dict[str, str]:
        """Load translations for specified locale."""
        try:
            locale_file = self.locales_dir / f"{locale}.json"
            
            if not locale_file.exists():
                self.logger.warning(f"Translation file for locale '{locale}' not found")
                if locale != self.fallback_locale:
                    self.logger.info(f"Falling back to '{self.fallback_locale}' locale")
                    return self.load_translations(self.fallback_locale)
                return {}
            
            with open(locale_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
                
            self.translations[locale] = translations
            self.logger.info(f"Loaded {len(translations)} translations for locale '{locale}'")
            return translations
            
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error loading translations for locale '{locale}': {e}")
            if locale != self.fallback_locale:
                return self.load_translations(self.fallback_locale)
            return {}
    
    def translate(self, key: str, **kwargs) -> str:
        """Translate text key with optional parameters."""
        # Get translation from current locale
        translation = self._get_translation(key, self.locale)
        
        # If not found and not using fallback, try fallback locale
        if translation == key and self.locale != self.fallback_locale:
            translation = self._get_translation(key, self.fallback_locale)
        
        # Perform parameter substitution
        if kwargs and translation != key:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Error formatting translation for key '{key}': {e}")
                # Return the unformatted translation
                pass
        
        return translation
    
    def _get_translation(self, key: str, locale: str) -> str:
        """Get translation for key from specific locale."""
        if locale not in self.translations:
            self.load_translations(locale)
        
        translations = self.translations.get(locale, {})
        
        # Support nested keys with dot notation (e.g., "menu.file.open")
        keys = key.split('.')
        value = translations
        
        try:
            for k in keys:
                value = value[k]
            return str(value)
        except (KeyError, TypeError):
            return key  # Return the key itself if translation not found
    
    def get_available_locales(self) -> List[str]:
        """Get list of available locales."""
        if not self.locales_dir.exists():
            return ["en"]
        
        locales = []
        for file_path in self.locales_dir.glob("*.json"):
            locale = file_path.stem
            locales.append(locale)
        
        # Ensure English is always available
        if "en" not in locales:
            locales.append("en")
        
        return sorted(locales)
    
    def set_locale(self, locale: str) -> None:
        """Set current locale for translations."""
        if locale in self.get_available_locales():
            self.locale = locale
            self.load_translations(locale)
            self.logger.info(f"Locale set to '{locale}'")
        else:
            self.logger.warning(f"Locale '{locale}' not available, keeping current locale '{self.locale}'")
    
    def get_locale_info(self, locale: str) -> Dict[str, Any]:
        """Get information about a specific locale."""
        locale_file = self.locales_dir / f"{locale}.json"
        
        if not locale_file.exists():
            return {}
        
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract metadata if available
            return {
                'code': locale,
                'name': data.get('_meta', {}).get('name', locale),
                'native_name': data.get('_meta', {}).get('native_name', locale),
                'direction': data.get('_meta', {}).get('direction', 'ltr'),
                'completion': data.get('_meta', {}).get('completion', 100)
            }
        except (json.JSONDecodeError, IOError):
            return {'code': locale, 'name': locale}
    
    def is_rtl_locale(self, locale: str = None) -> bool:
        """Check if locale uses right-to-left text direction."""
        if locale is None:
            locale = self.locale
            
        locale_info = self.get_locale_info(locale)
        return locale_info.get('direction', 'ltr') == 'rtl'

# Global translator instance
_global_translator = None

def get_translator() -> Translator:
    """Get the global translator instance."""
    global _global_translator
    if _global_translator is None:
        _global_translator = Translator()
    return _global_translator

def set_global_locale(locale: str) -> None:
    """Set the global locale."""
    translator = get_translator()
    translator.set_locale(locale)

def translate(key: str, **kwargs) -> str:
    """Convenience function for translation using global translator."""
    translator = get_translator()
    return translator.translate(key, **kwargs)

# Alias for shorter usage
_ = translate