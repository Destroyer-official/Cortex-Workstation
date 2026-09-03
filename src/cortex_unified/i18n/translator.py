"""
Translation and internationalization management.

Loads JSON catalogs from locales/<code>.json, resolves dotted keys against
nested dicts, and falls back to English for missing locales or keys. A
lazily created singleton backs the module-level translate() helper.
"""

from typing import Dict, List, Any
import json
import logging
from pathlib import Path

class Translator:
    """Resolves translation keys against cached JSON locale catalogs.

    Unknown locales and missing keys fall back to ``fallback_locale``;
    an unresolved key is returned verbatim so UI text degrades to the
    identifier rather than raising.
    """
    
    def __init__(self, locale: str = "en"):
        """Create the translator and load ``locale`` immediately.

        Args:
            locale: Locale code matching a ``locales/<code>.json`` file.
        """
        self.locale = locale
        self.translations = {}
        self.locales_dir = Path(__file__).parent / "locales"
        self.fallback_locale = "en"
        self.logger = logging.getLogger(__name__)
        
        # Load initial translations
        self.load_translations(locale)
    
    def load_translations(self, locale: str) -> Dict[str, str]:
        """Load and cache a catalog, recursing into the fallback on failure.

        Args:
            locale: Locale code naming ``locales/<code>.json``.

        Returns:
            The loaded mapping, or {} if even the fallback fails.
        """
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
        """Resolve ``key`` in the active locale, then the fallback.

        Args:
            key: Dotted lookup path such as "menu.file.open".
            **kwargs: Values interpolated into the template via str.format.

        Returns:
            Translated text, or ``key`` itself when unresolved.
        """
        translation = self._get_translation(key, self.locale)
        
        # Key miss: retry the fallback before returning the bare key
        if translation == key and self.locale != self.fallback_locale:
            translation = self._get_translation(key, self.fallback_locale)
        
        if kwargs and translation != key:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Error formatting translation for key '{key}': {e}")
                # Raw template beats crashing on bad placeholders
                pass
        
        return translation
    
    def _get_translation(self, key: str, locale: str) -> str:
        """Walk a dotted key through one locale's cached catalog."""
        if locale not in self.translations:
            self.load_translations(locale)
        
        translations = self.translations.get(locale, {})
        
        # Catalogs nest dicts, so dots address successive levels
        keys = key.split('.')
        value = translations
        
        try:
            for k in keys:
                value = value[k]
            return str(value)
        except (KeyError, TypeError):
            return key  # Return the key itself if translation not found
    
    def get_available_locales(self) -> List[str]:
        """Locale codes present on disk; always contains the fallback."""
        if not self.locales_dir.exists():
            return ["en"]
        
        locales = []
        for file_path in self.locales_dir.glob("*.json"):
            locale = file_path.stem
            locales.append(locale)
        
        # Fallback must resolve even with no en.json shipped
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
        """Display metadata from the locale file's ``_meta`` block.

        Args:
            locale: Locale code to inspect.

        Returns:
            Code, name, native_name, direction, completion; degraded to
            ``{'code': ..., 'name': ...}`` when the file is unreadable.
        """
        locale_file = self.locales_dir / f"{locale}.json"
        
        if not locale_file.exists():
            return {}
        
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
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
        """True when the locale metadata declares RTL direction."""
        if locale is None:
            locale = self.locale
            
        locale_info = self.get_locale_info(locale)
        return locale_info.get('direction', 'ltr') == 'rtl'

# Process-wide singleton, built on first request
_global_translator = None

def get_translator() -> Translator:
    """Return the shared Translator, creating it on first call."""
    global _global_translator
    if _global_translator is None:
        _global_translator = Translator()
    return _global_translator

def set_global_locale(locale: str) -> None:
    """Point the shared Translator at a new locale."""
    translator = get_translator()
    translator.set_locale(locale)

def translate(key: str, **kwargs) -> str:
    """Module-level shorthand delegating to the shared Translator."""
    translator = get_translator()
    return translator.translate(key, **kwargs)

# gettext-style short alias for dense UI code
_ = translate