# Deep Cleaner Usage Guide

## Basic Usage

Deep Cleaner is designed to be safe by default. When run without any arguments, it performs a dry run that shows what would be deleted without actually deleting anything.

```bash
deep-cleaner
```

## Available Commands

Deep Cleaner provides multiple specialized commands for different cleanup tasks:

- `clean-empty` - Find and remove empty files and folders (default command)
- `find-large-files` - Locate large files consuming disk space
- `find-duplicates` - Detect and manage duplicate files
- `clean-temp` - Clean temporary files and folders
- `analyze-disk` - Comprehensive disk usage analysis with visualizations
- `docker-cleanup` - Clean Docker resources (images, containers, volumes, networks)
- `package-cleanup` - Clean package manager caches and orphaned packages
- `heuristics-scan` - Advanced leftover detection using machine learning
- `list-startup-items` - List system startup programs
- `analyze-processes` - Analyze running processes and services
- `shred-files` - Securely delete files with multiple overwrite passes
- `restore-files` - Restore files from backup manifests
- `generate-report` - Generate cleanup reports in various formats
- `scan-broken-links` - Find and repair broken symlinks and shortcuts

## Command Line Options

### Action Flags

- `--dry-run` (default): Show what would be deleted without actually deleting
- `--delete`: Permanently delete empty files and folders
- `--trash`: Move empty files and folders to the system trash/recycle bin (requires `send2trash`)

### Filter Options

- `--pattern GLOB_PATTERN`: Only consider files matching this glob pattern (e.g., `*.tmp`)
- `--older-than DAYS`: Only consider files older than the specified number of days
- `--exclude-pattern PATTERN`: Exclude files/directories matching this pattern (can be used multiple times)

### Configuration

- `--config PATH`: Path to configuration file (default: `~/.deepcleaner.yaml`)
- `--no-config`: Don't load any configuration file

### Execution Mode

- `--yes`: Skip confirmation prompts (useful for scripts/CIs)
- `--threads N`: Number of threads to use for scanning (default: number of CPU cores)

### Output Options

- `--verbose`: Enable verbose output
- `--quiet`: Suppress all output except errors
- `--log-file PATH`: Write logs to file
- `--json-log`: Output logs in JSON format

## Configuration File

Deep Cleaner looks for a configuration file at `~/.deepcleaner.yaml`. You can specify a different location with the `--config` option or disable config loading with `--no-config`.

Example configuration:

```yaml
# Exclude patterns (glob patterns)
exclude_patterns:
  - "*.log"
  - "node_modules"
  - ".git"
  - "__pycache__"
  - "*.tmp"

# Exclude directories by name
exclude_dirs:
  - "System Volume Information"
  - "$RECYCLE.BIN"
  - "lost+found"

# Minimum age in days (0 = all files)
min_age_days: 0

# Default action (dry_run, delete, trash)
default_action: dry_run

# Log file location
log_file: "~/.deepcleaner.log"

# Enable JSON logging
json_logging: false

# Number of threads for scanning
threads: 4

# Whether to follow symlinks
follow_symlinks: false
```

## Examples

### Basic Dry Run

Show all empty files and folders that would be deleted:

```bash
deep-cleaner
```

### Delete All Empty Files and Folders

Permanently delete empty files and folders (requires confirmation):

```bash
deep-cleaner --delete
```

### Move to Trash

Move empty files and folders to the system trash (requires `send2trash`):

```bash
deep-cleaner --trash
```

### Filter by Pattern

Only consider files matching a specific pattern:

```bash
deep-cleaner --pattern "*.tmp"
```

### Filter by Age

Only consider files older than 30 days:

```bash
deep-cleaner --older-than 30
```

### Non-Interactive Mode

Skip confirmation prompts for use in scripts:

```bash
deep-cleaner --delete --yes
```

### Custom Configuration

Use a custom configuration file:

```bash
deep-cleaner --config /path/to/my-config.yaml
```

## Safety Features

1. **Dry Run by Default**: No destructive actions unless explicitly requested
2. **Confirmation Prompts**: Interactive confirmation required for destructive actions (unless `--yes` is used)
3. **System Directory Protection**: Critical system directories are excluded by default
4. **Audit Trail**: All actions are logged with an option to generate a manifest for undo operations
5. **Cross-Platform Awareness**: Behavior adapts to the operating system

## Advanced Features

### Docker Cleanup

Clean unused Docker resources to free up significant disk space:

```bash
# Show what Docker resources would be cleaned
deep-cleaner docker-cleanup

# Clean all Docker resources
deep-cleaner docker-cleanup --clean --all

# Clean only unused images
deep-cleaner docker-cleanup --clean --images

# Clean with detailed output
deep-cleaner docker-cleanup --clean --verbose --export docker-report.json
```

### Package Manager Cleanup

Clean package manager caches across multiple platforms:

```bash
# Clean all detected package managers
deep-cleaner package-cleanup --clean --all

# Clean specific package managers
deep-cleaner package-cleanup --clean --pip --npm

# Find orphaned packages
deep-cleaner package-cleanup --orphaned

# Keep recent cache files (last 30 days)
deep-cleaner package-cleanup --clean --keep-recent-days 30
```

### Advanced Heuristics Scanning

Use machine learning to detect application leftovers:

```bash
# Scan for leftovers with default confidence
deep-cleaner heuristics-scan

# High confidence detection only
deep-cleaner heuristics-scan --confidence-threshold 0.9

# Include Windows registry analysis
deep-cleaner heuristics-scan --scan-registry

# Scan specific directory
deep-cleaner heuristics-scan /path/to/scan
```

### Interactive Disk Analysis

Generate interactive visualizations of disk usage:

```bash
# Basic disk analysis
deep-cleaner analyze-disk

# Generate TreeMap visualization
deep-cleaner analyze-disk --export-treemap disk-usage.html

# Generate Sunburst chart
deep-cleaner analyze-disk --export-sunburst disk-chart.html

# Create interactive dashboard
deep-cleaner analyze-disk --export-dashboard dashboard.html

# Deep analysis with performance controls
deep-cleaner analyze-disk --max-depth 5 --cpu-priority low --memory-limit 1024
```

### Performance and Scalability

For large-scale operations, Deep Cleaner provides advanced performance features:

```bash
# Use checkpoints for resumable scans
deep-cleaner analyze-disk --checkpoint-interval 500

# Resume from checkpoint
deep-cleaner analyze-disk --resume-from checkpoint_20231201_143022.json

# Control resource usage
deep-cleaner clean-empty --cpu-priority low --io-priority low --threads 2

# Multi-drive scanning
deep-cleaner scan-multi-drive --drives "C:,D:,E:" --parallel
```

### Broken Link Detection and Repair

Find and fix broken symlinks, shortcuts, and registry references:

```bash
# Scan for all types of broken links
deep-cleaner scan-broken-links

# Scan specific types
deep-cleaner scan-broken-links --scan-symlinks --scan-shortcuts

# Attempt automatic repair
deep-cleaner scan-broken-links --repair --confidence-threshold 0.8

# Windows registry reference checking
deep-cleaner scan-broken-links --scan-registry --repair
```

## Configuration File

Deep Cleaner looks for a configuration file at `~/.deepcleaner.yaml`. You can specify a different location with the `--config` option or disable config loading with `--no-config`.

Example configuration with new features:

```yaml
# Exclude patterns (glob patterns)
exclude_patterns:
  - "*.log"
  - "node_modules"
  - ".git"
  - "__pycache__"
  - "*.tmp"

# Exclude directories by name
exclude_dirs:
  - "System Volume Information"
  - "$RECYCLE.BIN"
  - "lost+found"

# Minimum age in days (0 = all files)
min_age_days: 0

# Default action (dry_run, delete, trash)
default_action: dry_run

# Log file location
log_file: "~/.deepcleaner.log"

# Enable JSON logging
json_logging: false

# Number of threads for scanning
threads: 4

# Whether to follow symlinks
follow_symlinks: false

# Performance settings
performance:
  cpu_priority: "normal"  # low, normal, high
  io_priority: "low"      # low, normal, high
  memory_limit_mb: 0      # 0 = no limit
  checkpoint_interval: 1000

# Docker cleanup settings
docker:
  cleanup_dangling_images: true
  cleanup_stopped_containers: true
  cleanup_unused_volumes: true
  cleanup_unused_networks: true
  create_backup_manifest: true

# Package manager settings
package_managers:
  keep_recent_days: 7
  verify_integrity: true
  backup_package_lists: true
  auto_detect: true

# Heuristics settings
heuristics:
  confidence_threshold: 0.7
  use_ml_patterns: true
  scan_registry: false  # Windows only
  common_paths:
    - "C:\\Program Files"
    - "C:\\Program Files (x86)"
    - "%APPDATA%"
    - "%LOCALAPPDATA%"

# Visualization settings
visualization:
  max_depth: 3
  export_format: "html"  # html, png, svg
  interactive: true
  color_scheme: "viridis"

# Internationalization
i18n:
  locale: "auto"  # auto, en, es, fr, de, zh
  fallback_locale: "en"

# Accessibility
accessibility:
  enable_keyboard_shortcuts: true
  enable_screen_reader: true
  high_contrast_theme: false
  announce_changes: true
```

## Undo Operations

When using `--trash` or when backups are enabled in the configuration, Deep Cleaner creates a manifest file that can be used to restore deleted items. The manifest is stored in the log directory and contains a timestamped record of all operations.

### Restoring Files

```bash
# List available restore points
deep-cleaner restore-files --list

# Preview restore operation
deep-cleaner restore-files --restore manifest_20231201_143022.json --dry-run

# Restore files from manifest
deep-cleaner restore-files --restore manifest_20231201_143022.json
```