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
- **Heuristic Scanning:** Identify orphaned application leftovers, broken shortcuts, and temp files with confidence scores.
- **Docker Cleanup:** Clean dangling images, stopped containers, and unused volumes.
- **Broken Link Detection:** Find and optionally repair broken symlinks and Windows registry references.
- **Safety First:** Defaults to `dry-run` and moves items to the Recycle Bin/Trash natively instead of permanently deleting them.
- **Performance Optimized:** Multi-threaded execution (`ResourceThrottler`) with checkpoints.
- **Cross-Platform Interface:** Refined Click-based CLI and a comprehensive PySide6 native GUI.

## Installation

### From Source

```bash
git clone https://github.com/Destroyer-official/deep-cleaner.git
cd deep-cleaner
pip install -e .
```

### With GUI Support

```bash
pip install -e .[gui]
```

## Quick Start (CLI)

Deep Cleaner defaults to dry-run mode. To perform an actual deletion, you must specify options like `--delete` or `--trash`.

Scan for empty files:
```bash
deep-cleaner clean-empty "C:\Path\To\Scan"
```

Find duplicate files:
```bash
deep-cleaner find-duplicates "C:\Path\To\Scan"
```

Analyze Disk Usage:
```bash
deep-cleaner analyze-disk "C:\Path\To\Scan"
```

Clean System Temp Files:
```bash
deep-cleaner clean-temp
```

Docker Cleanup (Dry Run vs Force):
```bash
# Preview what will be cleaned
deep-cleaner docker-cleanup --all

# Actually clean
deep-cleaner docker-cleanup --all --force
```

Get comprehensive help for any command:
```bash
deep-cleaner --help
deep-cleaner scan-enhanced --help
```

## GUI Application

To launch the graphical interface, ensure you have installed the optional `[gui]` dependencies, then run:

```bash
python run_gui.py
```
Or use the provided batch scripts (`run_with_conda.bat` or `run_with_conda.ps1`).

## Configuration

Settings are persistently stored in `~/.deepcleaner.yaml` and can be overridden via CLI flags. You can specify exclusions, thread pools, memory limits, and logging preferences.

## Safety & Recovery

- Deep Cleaner always creates backup manifest files in `~/.deepcleaner/manifests/` before deleting content.
- Use the `deep-cleaner restore` command to recover mistakenly deleted files from a specific manifest.

## License

MIT License. See `LICENSE` for details.

## Testing

Deep Cleaner includes comprehensive tests for all features. See [TESTING.md](TESTING.md) for details on running tests.

## Complete Feature List

See [FEATURES.md](FEATURES.md) for a complete list of all implemented features.