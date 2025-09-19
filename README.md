# Deep Cleaner

A safe, powerful, cross-platform utility to find and remove unnecessary files and folders across entire machines while following security and usability best practices.

## Features

- **Safe-by-default**: `--dry-run` enabled by default. No destructive actions unless explicitly confirmed.
- **Move to OS Trash/Recycle Bin**: uses `send2trash` when available; fallbacks to permanent delete only when asked.
- **Audit manifest & undo**: every deletion writes a timestamped JSON manifest that records moved/deleted paths and can be used to restore.
- **Config file support** (`~/.deepcleaner.yaml`): exclude patterns, size thresholds, age thresholds, default actions.
- **Default system-safe excludes** (Windows and POSIX) — opt-out by flag.
- **Interactive + Fully non-interactive (CI-friendly) modes** — `--yes` to skip prompts.
- **Pattern filters and age filters** (`--pattern`, `--older-than` (days)).
- **Recursive, bottom-up directory detection** — directories considered empty only after checking children and ignored empty files.
- **Concurrency-aware scanning** with limited thread pool for `stat()` calls; optional progress bars if `tqdm` present.
- **Comprehensive logging** to console and file (structured JSON optional).
- **Cross-platform behavior and admin awareness** (warns on non-elevated Windows runs for system directories).
- **Plugin-friendly architecture**: small modular packages for scanner, deleter, config, CLI.
- **Robust tests** using `pytest` (non-destructive tests, fixture-based with temp dirs).
- **CI pipeline** with linting, formatting, typing, and tests using GitHub Actions.
- **Duplicate file detection**: Find and remove duplicate files using hash-based algorithms
- **Large file finder**: Identify files larger than specified size thresholds
- **Temporary file cleaner**: Remove temporary files from system and application caches
- **Cache and log cleaner**: Clean application cache and log files
- **Old file cleaner**: Remove files not accessed for specified periods
- **Secure file shredder**: Permanently delete files with multiple overwrite passes
- **Disk space analyzer**: Analyze disk usage and identify space-hogging files/folders
- **Duplicate folder finder**: Find folders with identical content
- **System startup manager**: Manage system startup items
- **Process and service analyzer**: Analyze running processes and system services
- **Windows registry cleaner**: Clean orphaned registry entries (Windows only)
- **Task scheduler integration**: Schedule cleaning tasks using native system schedulers
- **Auto-clean rules**: Define rules for automatic cleaning
- **Backup and restore**: Restore files from backup manifests
- **Comprehensive reporting**: Generate reports in multiple formats
- **Graphical user interface**: Full-featured GUI with tabbed interface
- **Cross-platform packaging**: Native executables for Windows, macOS, and Linux

## Installation

```bash
pip install deep-cleaner
```

Or for development:

```bash
git clone https://github.com/Destroyer-official/deep-cleaner.git
cd deep-cleaner
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Dry run (default) - shows what would be deleted without actually deleting
deep-cleaner

# Actually delete empty files and folders
deep-cleaner --delete

# Delete and move to trash (requires send2trash)
deep-cleaner --trash

# Filter by pattern
deep-cleaner --pattern "*.tmp"

# Only delete files older than 30 days
deep-cleaner --older-than 30

# Non-interactive mode (useful for scripts/CIs)
deep-cleaner --yes

# Custom configuration file
deep-cleaner --config ~/.my-deepcleaner.yaml

# Find duplicate files
deep-cleaner find-duplicates /path/to/scan

# Find large files (>100MB)
deep-cleaner find-large-files --min-size 100 /path/to/scan

# Clean temporary files
deep-cleaner clean-temp --clean

# Analyze disk usage
deep-cleaner analyze-disk /path/to/analyze
```

### Graphical User Interface

```bash
# Launch the GUI
deep-cleaner-gui
```

## Configuration

Create a `~/.deepcleaner.yaml` file to customize behavior:

```yaml
# Exclude patterns (glob patterns)
exclude_patterns:
  - "*.log"
  - "node_modules"
  - ".git"
  - "__pycache__"

# Exclude directories by name
exclude_dirs:
  - "System Volume Information"
  - "$RECYCLE.BIN"

# Minimum age in days (0 = all files)
min_age_days: 0

# Default action (dry_run, delete, trash)
default_action: dry_run

# Log file location
log_file: "~/.deepcleaner.log"

# Enable JSON logging
json_logging: false
```

## Safety

By default, Deep Cleaner runs in dry-run mode and will not delete anything. System directories are excluded by default on all platforms.

To actually delete files, you must explicitly use `--delete` or `--trash` flags.

## Testing

Deep Cleaner includes comprehensive tests for all features. See [TESTING.md](TESTING.md) for details on running tests.

## Complete Feature List

See [FEATURES.md](FEATURES.md) for a complete list of all implemented features.