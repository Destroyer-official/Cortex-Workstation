# Deep Cleaner Configuration Reference

## Overview

Deep Cleaner uses a YAML configuration file to customize behavior, performance settings, and feature preferences. The default location is `~/.deepcleaner.yaml`, but you can specify a custom location with the `--config` option.

## Configuration File Structure

```yaml
# Basic Settings
exclude_patterns: []
exclude_dirs: []
exclude_regex_patterns: []
min_age_days: 0
default_action: "dry_run"
log_file: "~/.deepcleaner.log"
json_logging: false
threads: 0
follow_symlinks: false

# Performance Settings
performance:
  cpu_priority: "normal"
  io_priority: "low"
  memory_limit_mb: 0
  checkpoint_interval: 1000
  enable_streaming: true
  gc_threshold: 1000

# Docker Settings
docker:
  cleanup_dangling_images: true
  cleanup_stopped_containers: true
  cleanup_unused_volumes: true
  cleanup_unused_networks: true
  create_backup_manifest: true
  api_timeout: 30
  prune_build_cache: false

# Package Manager Settings
package_managers:
  keep_recent_days: 7
  verify_integrity: true
  backup_package_lists: true
  auto_detect: true
  supported_managers:
    - pip
    - npm
    - yarn
    - conda
    - apt
    - dnf
    - pacman
    - brew
    - chocolatey

# Heuristics Settings
heuristics:
  confidence_threshold: 0.7
  use_ml_patterns: true
  scan_registry: false
  update_ml_models: true
  common_paths:
    - "C:\\Program Files"
    - "C:\\Program Files (x86)"
    - "%APPDATA%"
    - "%LOCALAPPDATA%"
    - "/Applications"
    - "/usr/local"
    - "~/.local"

# Visualization Settings
visualization:
  max_depth: 3
  export_format: "html"
  interactive: true
  color_scheme: "viridis"
  enable_animations: true
  chart_size:
    width: 1200
    height: 800

# Internationalization
i18n:
  locale: "auto"
  fallback_locale: "en"
  rtl_support: true
  date_format: "auto"
  number_format: "auto"

# Accessibility
accessibility:
  enable_keyboard_shortcuts: true
  enable_screen_reader: true
  high_contrast_theme: false
  announce_changes: true
  keyboard_shortcuts:
    scan: "Ctrl+S"
    clean: "Ctrl+D"
    settings: "Ctrl+,"
    help: "F1"
    quit: "Ctrl+Q"

# Multi-Drive Settings
multi_drive:
  parallel_scanning: true
  network_timeout: 30
  retry_attempts: 3
  credential_storage: "secure"
  drive_priorities:
    local: "high"
    network: "normal"
    removable: "low"

# Broken Link Settings
broken_links:
  scan_symlinks: true
  scan_shortcuts: true
  scan_registry: false
  repair_confidence_threshold: 0.8
  backup_before_repair: true
  search_heuristics: true

# Reporting Settings
reporting:
  default_format: "html"
  include_charts: true
  include_statistics: true
  export_raw_data: false
  compress_reports: false

# Security Settings
security:
  secure_delete_passes: 3
  verify_deletions: true
  audit_trail: true
  encrypt_manifests: false
  hash_algorithm: "sha256"

# Scheduler Settings
scheduler:
  enable_scheduling: false
  default_schedule: "weekly"
  max_concurrent_tasks: 2
  task_timeout: 3600
  notification_method: "log"
```

## Basic Settings

### File and Directory Exclusions

```yaml
# Glob patterns to exclude
exclude_patterns:
  - "*.log"
  - "*.tmp"
  - "node_modules"
  - ".git"
  - "__pycache__"
  - "*.pyc"
  - ".DS_Store"
  - "Thumbs.db"

# Directory names to exclude
exclude_dirs:
  - "System Volume Information"
  - "$RECYCLE.BIN"
  - "lost+found"
  - ".Trash"
  - ".cache"

# Regular expression patterns
exclude_regex_patterns:
  - ".*\\.log\\.[0-9]+"
  - "temp_[0-9]{8}"
  - "backup_\\d{4}-\\d{2}-\\d{2}"
```

### Basic Behavior

```yaml
# Minimum file age in days (0 = all files)
min_age_days: 0

# Default action when no action specified
default_action: "dry_run"  # Options: dry_run, delete, trash

# Number of threads (0 = auto-detect CPU count)
threads: 0

# Whether to follow symbolic links
follow_symlinks: false
```

### Logging Configuration

```yaml
# Log file location
log_file: "~/.deepcleaner.log"

# Enable JSON structured logging
json_logging: false

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
log_level: "INFO"

# Rotate log files
log_rotation:
  max_size_mb: 10
  backup_count: 5
```

## Performance Settings

### Resource Management

```yaml
performance:
  # CPU priority: low, normal, high
  cpu_priority: "normal"
  
  # I/O priority: low, normal, high
  io_priority: "low"
  
  # Memory limit in MB (0 = no limit)
  memory_limit_mb: 0
  
  # Save checkpoint every N directories
  checkpoint_interval: 1000
  
  # Enable streaming for large datasets
  enable_streaming: true
  
  # Garbage collection threshold
  gc_threshold: 1000
  
  # Buffer sizes
  read_buffer_size: 65536
  write_buffer_size: 65536
```

### Checkpoint Configuration

```yaml
checkpoints:
  # Enable checkpoint system
  enabled: true
  
  # Checkpoint directory
  directory: "~/.deepcleaner/checkpoints"
  
  # Auto-cleanup old checkpoints
  cleanup_after_days: 7
  
  # Compression for checkpoint files
  compress: true
```

## Docker Configuration

### Docker Cleanup Settings

```yaml
docker:
  # What to clean by default
  cleanup_dangling_images: true
  cleanup_stopped_containers: true
  cleanup_unused_volumes: true
  cleanup_unused_networks: true
  
  # Safety features
  create_backup_manifest: true
  
  # API settings
  api_timeout: 30
  api_version: "auto"
  
  # Advanced cleanup options
  prune_build_cache: false
  remove_anonymous_volumes: true
  
  # Size thresholds
  min_image_age_hours: 24
  min_container_age_hours: 1
```

### Docker Connection

```yaml
docker_connection:
  # Docker daemon URL (auto-detect if not specified)
  url: "auto"
  
  # TLS settings
  tls_verify: false
  tls_cert_path: ""
  tls_key_path: ""
  tls_ca_cert: ""
  
  # Connection timeout
  timeout: 60
```

## Package Manager Configuration

### General Settings

```yaml
package_managers:
  # Keep cache files newer than N days
  keep_recent_days: 7
  
  # Verify package manager integrity after cleaning
  verify_integrity: true
  
  # Create backup of package lists
  backup_package_lists: true
  
  # Auto-detect available package managers
  auto_detect: true
  
  # Backup directory
  backup_directory: "~/.deepcleaner/package-backups"
```

### Per-Manager Settings

```yaml
package_manager_specific:
  pip:
    cache_dir: "auto"  # Auto-detect or specify path
    keep_wheels: true
    verify_downloads: true
  
  npm:
    cache_dir: "auto"
    verify_integrity: true
    audit_fix: false
  
  conda:
    cache_dir: "auto"
    clean_tarballs: true
    clean_packages: true
  
  system:
    apt:
      clean_archives: true
      autoremove: true
    dnf:
      clean_all: true
    pacman:
      clean_cache: true
```

## Heuristics and Machine Learning

### Detection Settings

```yaml
heuristics:
  # Minimum confidence score (0.0-1.0)
  confidence_threshold: 0.7
  
  # Enable ML pattern recognition
  use_ml_patterns: true
  
  # Include Windows registry analysis
  scan_registry: false
  
  # Auto-update ML models
  update_ml_models: true
  
  # Model update frequency (days)
  model_update_interval: 30
```

### Scan Paths

```yaml
heuristics_paths:
  windows:
    - "C:\\Program Files"
    - "C:\\Program Files (x86)"
    - "%APPDATA%"
    - "%LOCALAPPDATA%"
    - "%TEMP%"
  
  macos:
    - "/Applications"
    - "~/Applications"
    - "~/Library"
    - "/usr/local"
  
  linux:
    - "/usr/local"
    - "/opt"
    - "~/.local"
    - "~/.config"
```

### ML Model Configuration

```yaml
ml_models:
  # Model storage directory
  model_directory: "~/.deepcleaner/models"
  
  # Enable online learning
  online_learning: false
  
  # Training data collection
  collect_training_data: false
  
  # Model types to use
  enabled_models:
    - "filename_patterns"
    - "directory_structure"
    - "file_associations"
```

## Visualization Configuration

### Chart Settings

```yaml
visualization:
  # Maximum directory depth for analysis
  max_depth: 3
  
  # Default export format
  export_format: "html"  # html, png, svg, pdf
  
  # Enable interactive features
  interactive: true
  
  # Color scheme
  color_scheme: "viridis"  # viridis, plasma, inferno, magma, cividis
  
  # Enable animations
  enable_animations: true
  
  # Chart dimensions
  chart_size:
    width: 1200
    height: 800
  
  # Performance settings
  max_nodes: 1000
  simplify_large_trees: true
```

### Export Options

```yaml
export_settings:
  # Image DPI for static exports
  dpi: 300
  
  # Include metadata in exports
  include_metadata: true
  
  # Compression for HTML exports
  compress_html: false
  
  # Custom CSS for HTML exports
  custom_css: ""
```

## Internationalization and Accessibility

### Language Settings

```yaml
i18n:
  # Locale (auto, en, es, fr, de, zh)
  locale: "auto"
  
  # Fallback locale
  fallback_locale: "en"
  
  # Right-to-left language support
  rtl_support: true
  
  # Date and number formatting
  date_format: "auto"
  number_format: "auto"
  
  # Custom translation directory
  translation_directory: ""
```

### Accessibility Features

```yaml
accessibility:
  # Enable keyboard navigation
  enable_keyboard_shortcuts: true
  
  # Screen reader support
  enable_screen_reader: true
  
  # High contrast theme
  high_contrast_theme: false
  
  # Announce changes to screen readers
  announce_changes: true
  
  # Font scaling
  font_scale: 1.0
  
  # Animation preferences
  reduce_animations: false
```

### Keyboard Shortcuts

```yaml
keyboard_shortcuts:
  # Main actions
  scan: "Ctrl+S"
  clean: "Ctrl+D"
  settings: "Ctrl+,"
  help: "F1"
  quit: "Ctrl+Q"
  
  # Navigation
  next_tab: "Ctrl+Tab"
  prev_tab: "Ctrl+Shift+Tab"
  select_all: "Ctrl+A"
  
  # View actions
  refresh: "F5"
  toggle_details: "F2"
  export: "Ctrl+E"
```

## Multi-Drive and Network Settings

### Drive Scanning

```yaml
multi_drive:
  # Enable parallel drive scanning
  parallel_scanning: true
  
  # Network drive timeout (seconds)
  network_timeout: 30
  
  # Retry attempts for failed operations
  retry_attempts: 3
  
  # Credential storage method
  credential_storage: "secure"  # secure, config, prompt
  
  # Drive type priorities
  drive_priorities:
    local: "high"
    network: "normal"
    removable: "low"
```

### Network Configuration

```yaml
network:
  # Connection timeout
  timeout: 30
  
  # Enable connection pooling
  connection_pooling: true
  
  # Maximum concurrent connections
  max_connections: 5
  
  # Retry configuration
  retry_delay: 1
  max_retries: 3
```

## Security and Safety

### Secure Deletion

```yaml
security:
  # Number of overwrite passes for secure deletion
  secure_delete_passes: 3
  
  # Verify deletions completed successfully
  verify_deletions: true
  
  # Maintain audit trail
  audit_trail: true
  
  # Encrypt backup manifests
  encrypt_manifests: false
  
  # Hash algorithm for integrity checks
  hash_algorithm: "sha256"
```

### Backup and Restore

```yaml
backup:
  # Default backup location
  backup_directory: "~/.deepcleaner/backups"
  
  # Compress backup files
  compress_backups: true
  
  # Backup retention (days)
  retention_days: 30
  
  # Include file content in backups
  backup_content: false
  
  # Verify backup integrity
  verify_backups: true
```

## Reporting Configuration

### Report Generation

```yaml
reporting:
  # Default report format
  default_format: "html"  # html, json, csv, xml
  
  # Include charts in reports
  include_charts: true
  
  # Include detailed statistics
  include_statistics: true
  
  # Export raw data
  export_raw_data: false
  
  # Compress large reports
  compress_reports: false
  
  # Report template directory
  template_directory: ""
```

### Report Content

```yaml
report_content:
  # Sections to include
  include_summary: true
  include_details: true
  include_recommendations: true
  include_performance_metrics: true
  
  # Chart types
  chart_types:
    - "pie"
    - "bar"
    - "treemap"
    - "timeline"
```

## Environment-Specific Settings

### Windows-Specific

```yaml
windows:
  # Registry backup before cleaning
  backup_registry: true
  
  # Use Windows API for file operations
  use_win32_api: true
  
  # Handle long path names
  enable_long_paths: true
  
  # Windows-specific exclusions
  exclude_system_files: true
```

### macOS-Specific

```yaml
macos:
  # Handle resource forks
  handle_resource_forks: true
  
  # Use Spotlight for indexing
  use_spotlight: false
  
  # Respect quarantine attributes
  respect_quarantine: true
```

### Linux-Specific

```yaml
linux:
  # Use extended attributes
  use_extended_attributes: true
  
  # Handle different filesystems
  filesystem_specific_optimizations: true
  
  # Use system package managers
  integrate_package_managers: true
```

## Configuration Validation

### Schema Validation

Deep Cleaner validates configuration files against a schema. Invalid configurations will show helpful error messages.

### Configuration Testing

```bash
# Validate configuration file
deep-cleaner validate-config --config ~/.deepcleaner.yaml

# Test configuration with dry run
deep-cleaner clean-empty --config ~/.deepcleaner.yaml --dry-run --verbose

# Export current effective configuration
deep-cleaner export-config --output current-config.yaml
```

### Configuration Migration

When upgrading Deep Cleaner, configuration files are automatically migrated to new formats when possible.

```bash
# Migrate old configuration
deep-cleaner migrate-config --input old-config.yaml --output new-config.yaml

# Backup current configuration
deep-cleaner backup-config --output config-backup.yaml
```

## Best Practices

### Performance Optimization

1. **Adjust thread count** based on your system capabilities
2. **Set memory limits** to prevent system overload
3. **Use checkpoints** for long-running operations
4. **Configure appropriate I/O priority** for background operations

### Safety Configuration

1. **Enable backup manifests** for all destructive operations
2. **Use dry-run as default** action
3. **Set conservative confidence thresholds** for heuristics
4. **Enable audit trails** for compliance

### Maintenance

1. **Regularly review** exclude patterns
2. **Update ML models** periodically
3. **Clean up old** checkpoints and backups
4. **Monitor log files** for errors and performance issues

This configuration reference covers all available options in Deep Cleaner. Start with the basic settings and gradually customize advanced features as needed.