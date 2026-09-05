# Internationalization and Accessibility Guide

This guide covers the internationalization (i18n) and accessibility features implemented in Cortex Workstation.

## Internationalization (i18n)

### Overview

Cortex Workstation supports multiple languages through a comprehensive internationalization system that includes:

- Translation management for multiple languages
- Locale detection and switching
- Parameter substitution in translations
- Fallback to default language
- Right-to-left (RTL) language support

### Supported Languages

- English (en) - Default
- Spanish (es) - Español
- French (fr) - Français  
- German (de) - Deutsch
- Chinese (zh) - 中文

### Using Translations

#### Basic Usage

```python
from cortex_unified.translations import translate as _

# Simple translation
message = _("buttons.ok")  # Returns "OK" in English

# Translation with parameters
greeting = _("scanner.files_found", count=42)  # Returns "Files found: 42"
```

#### Advanced Usage

```python
from cortex_unified.translations import get_translator, set_global_locale

# Get translator instance
translator = get_translator()

# Change language
set_global_locale("es")  # Switch to Spanish

# Check available languages
locales = translator.get_available_locales()

# Get locale information
info = translator.get_locale_info("es")
print(info["native_name"])  # "Español"

# Check if locale uses RTL layout
is_rtl = translator.is_rtl_locale("ar")
```

### Translation File Format

Translation files are stored in `src/cortex_unified/translations/locales/` as JSON files:

```json
{
  "_meta": {
    "name": "English",
    "native_name": "English", 
    "direction": "ltr",
    "completion": 100
  },
  "app": {
    "name": "Cortex Workstation",
    "description": "The Ultimate Windows NT Systems, Forensics & File Management Platform"
  },
  "buttons": {
    "ok": "OK",
    "cancel": "Cancel"
  },
  "messages": {
    "confirm_delete": "Are you sure you want to delete {count} items?"
  }
}
```

### Adding New Languages

1. Create a new JSON file in `src/cortex_unified/translations/locales/` (e.g., `it.json` for Italian)
2. Copy the structure from `en.json`
3. Translate all text values
4. Update the `_meta` section with language information
5. The new language will be automatically detected

## Accessibility Features

### Overview

Cortex Workstation includes comprehensive accessibility features:

- Keyboard navigation support
- Screen reader compatibility
- High contrast themes
- ARIA labels and descriptions
- Focus management
- Keyboard shortcuts

### Keyboard Navigation

#### Setup

```python
from cortex_unified.accessibility import KeyboardHandler

# Create keyboard handler
handler = KeyboardHandler(widget)
handler.setup_keyboard_navigation()

# Set up default shortcuts
handler.setup_default_shortcuts()
```

#### Default Shortcuts

- `Ctrl+S` - Start Scan
- `Ctrl+D` - Clean Selected Items
- `Ctrl+,` - Open Settings
- `F5` - Refresh View
- `Ctrl+A` - Select All
- `F1` - Show Help
- `Ctrl+Q` - Quit Application
- `Tab` - Next Widget
- `Shift+Tab` - Previous Widget
- `Arrow Keys` - Navigate Items

#### Custom Shortcuts

```python
shortcuts = {
    "Ctrl+N": my_new_function,
    "F2": my_rename_function,
    "Delete": my_delete_function
}
handler.setup_shortcuts(shortcuts)
```

### Screen Reader Support

#### Setup

```python
from cortex_unified.accessibility import ScreenReaderSupport

# Create screen reader support
support = ScreenReaderSupport(widget)
support.setup_accessible_descriptions()

# Add ARIA labels to widgets
widgets = [button1, button2, input_field]
support.add_aria_labels(widgets)
```

#### Announcements

```python
# Announce changes
support.announce_changes("Scan completed successfully")

# Announce progress
support.announce_progress(75, "Scanning files...")

# Announce errors
support.announce_error("Failed to access directory")
```

#### Accessible Tables and Trees

```python
# Set up accessible table
support.create_accessible_table(table_widget)

# Set up accessible tree
support.create_accessible_tree(tree_widget)
```

### Themes and Visual Accessibility

#### Theme Manager

```python
from cortex_unified.accessibility import get_theme_manager

theme_manager = get_theme_manager()

# Apply themes
theme_manager.apply_high_contrast_theme()
theme_manager.apply_dark_theme()
theme_manager.apply_light_theme()
theme_manager.restore_default_theme()

# Check current theme
current = theme_manager.get_current_theme()
is_high_contrast = theme_manager.is_high_contrast_enabled()
```

#### Available Themes

- **Default** - System default theme
- **Light** - Light theme with good contrast
- **Dark** - Dark theme with good contrast  
- **High Contrast** - High contrast theme for accessibility

### Settings Integration

#### Creating Settings Widget

```python
from cortex_unified.translations import get_i18n_manager

manager = get_i18n_manager()
settings_widget = manager.create_settings_widget(parent)

# Connect to signals
settings_widget.locale_changed.connect(on_locale_changed)
settings_widget.theme_changed.connect(on_theme_changed)
settings_widget.accessibility_changed.connect(on_accessibility_changed)
```

#### Settings Management

```python
# Get current settings
current_locale = manager.get_current_locale()
current_theme = manager.get_current_theme()
is_rtl = manager.is_rtl_layout()

# Settings are automatically saved to QSettings
```

### Complete Setup Example

```python
from cortex_unified.translations import get_i18n_manager
from cortex_unified.accessibility import setup_full_accessibility

class MyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set up i18n
        self.i18n_manager = get_i18n_manager()
        
        # Set up accessibility
        self.keyboard_handler, self.screen_reader = setup_full_accessibility(
            self, 
            enable_shortcuts=True,
            enable_announcements=True
        )
        
        # Create UI
        self.setup_ui()
    
    def setup_ui(self):
        # Use translations in UI
        self.setWindowTitle(_("app.name"))
        
        # Create settings widget
        settings_widget = self.i18n_manager.create_settings_widget(self)
        
        # Connect signals
        settings_widget.locale_changed.connect(self.on_language_changed)
        settings_widget.theme_changed.connect(self.on_theme_changed)
    
    def on_language_changed(self, locale):
        # Update UI text
        self.update_ui_text()
        
        # Announce change
        self.screen_reader.announce_changes(f"Language changed to {locale}")
    
    def on_theme_changed(self, theme):
        # Theme is automatically applied
        self.screen_reader.announce_changes(f"Theme changed to {theme}")
```

## Testing

Run the accessibility-related test suites:

```bash
pytest tests/ -k "translation or accessibility or premium" -v
```

## Best Practices

### Internationalization

1. **Use translation keys consistently** - Use descriptive, hierarchical keys
2. **Provide context** - Include parameter names that make sense
3. **Test with different languages** - Especially longer text (German) and RTL (Arabic)
4. **Handle missing translations** - Always provide fallbacks
5. **Consider cultural differences** - Colors, icons, and layouts may have different meanings

### Accessibility

1. **Provide keyboard alternatives** - Every mouse action should have a keyboard equivalent
2. **Use semantic markup** - Proper roles, labels, and descriptions
3. **Test with screen readers** - Use NVDA, JAWS, or VoiceOver
4. **Ensure sufficient contrast** - Follow WCAG guidelines
5. **Provide multiple ways to access features** - Menus, shortcuts, and buttons
6. **Announce important changes** - Keep users informed of state changes

### Performance

1. **Load translations lazily** - Only load needed languages
2. **Cache translations** - Avoid repeated file I/O
3. **Minimize announcements** - Don't overwhelm screen reader users
4. **Optimize theme switching** - Cache palettes when possible

## Troubleshooting

### Common Issues

1. **Missing translations** - Check file paths and JSON syntax
2. **Keyboard shortcuts not working** - Ensure proper event handling setup
3. **Screen reader not announcing** - Check platform-specific accessibility APIs
4. **Theme not applying** - Verify QApplication instance exists
5. **RTL layout issues** - Test with actual RTL languages

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('cortex_unified.translations').setLevel(logging.DEBUG)
logging.getLogger('cortex_unified.accessibility').setLevel(logging.DEBUG)
```

## Contributing

When adding new features:

1. Add translation keys to all language files
2. Include accessibility attributes (ARIA labels, keyboard support)
3. Test with multiple languages and themes
4. Update documentation
5. Add tests for new functionality

## Platform-Specific Notes

### Windows
- Uses Windows accessibility APIs
- Supports NVDA and JAWS screen readers
- High contrast mode integrates with Windows settings

### macOS  
- Uses macOS accessibility APIs
- Supports VoiceOver
- Integrates with system appearance settings

### Linux
- Uses AT-SPI accessibility framework
- Supports Orca screen reader
- Integrates with desktop environment themes