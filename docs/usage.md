# Cortex Cleaner Usage Guide

**Cortex Cleaner** is a comprehensive, production-grade system maintenance suite and advanced file manager built with Python, PySide6 (Qt6), and high-performance native engines.

---

## 🚀 Launching Cortex Cleaner

### 1. Graphical User Interface (GUI)
Launch the full premium interface with sidebar navigation, 59 system maintenance pages, and the embedded **Nexus File Manager**:

```bash
# Recommended launcher
python run_gui.py

# Or via the package module
python -m cortex_unified.ui.premium.window
```

### 2. Command Line Interface (CLI)
Cortex Cleaner provides safe, high-speed CLI commands for automated scripts and headless environments:

```bash
# General help and command list
cortex --help

# Safe dry-run scan of empty files and directories
cortex clean-empty

# Perform actual cleanup
cortex clean-empty --delete

# Move items to system trash
cortex clean-empty --trash
```

---

## 🧭 Main Interface Overview

The GUI consists of four main functional tiers:
1. **Title Bar Row**: Windows 11 frameless title bar with integrated folder tabs (`+` new tab, close, middle-click), window drag space, and native window controls (`-`, `□`, `✕`).
2. **Sidebar Navigation**: Collapsible (`Ctrl+H`) categorized navigation housing 59 system care and diagnostics tools:
   - **Command Center**: Dashboard, Quick Scan, System Status
   - **Cleanup & Storage**: Junk Cleaner, Temp Files, Empty Folders, Large Files, Duplicate Finder, Leftover Scanner, Docker Cleanup, Package Manager Caches
   - **Files & Explorer**: **Nexus File Manager** (Full native Qt6 explorer)
   - **System Performance**: RAM Optimizer, Startup Programs, Process Analyzer, Disk Benchmark, Thermal Monitor
   - **Privacy & Defense**: Privacy Sweeper, File Shredder, Browser Cleaner, Telemetry Blocker
   - **Apps & Security**: Deep Uninstaller, App Permission Manager, Extension Auditor
   - **Recovery & Reports**: Backup Vault, Undo History, System Health Reports
3. **Content Workspace**: High-performance lazy-loaded tool pages with smooth scrolling and animations.
4. **Status Bar & Notifications**: Real-time engine health, local offline suggester notifications, and resource telemetry.

---

## 📦 Available CLI Commands

| Command | Description |
| :--- | :--- |
| `clean-empty` | Find and remove empty files and folders (default dry-run) |
| `find-large-files` | Locate large files consuming significant disk space |
| `find-duplicates` | Multi-phase duplicate detection (size -> partial hash -> full BLAKE3) |
| `clean-temp` | Clean temporary system, user, and application caches |
| `analyze-disk` | Generate disk usage breakdowns and interactive TreeMaps |
| `docker-cleanup` | Remove dangling images, stopped containers, and unused volumes |
| `package-cleanup` | Clean pip, npm, yarn, conda, and build caches |
| `heuristics-scan` | Detect leftover registry keys and orphan application folders |
| `list-startup-items` | Inspect and manage Windows startup entries |
| `analyze-processes` | Monitor memory, CPU, and handle usage per process |
| `shred-files` | DoD 5220.22-M / Gutmann compliant multi-pass secure file eraser |
| `restore-files` | Restore files from safe backup manifests |
| `scan-broken-links` | Identify and repair invalid shortcuts and symlinks |

---

## ⚙️ CLI Flags & Options

### Action Mode
- `--dry-run` *(default)*: Preview changes without touching files.
- `--delete`: Permanently delete detected files.
- `--trash`: Move items to the Recycle Bin / Trash.
- `--yes`: Bypass confirmation prompts for headless automation.

### Filtering
- `--pattern GLOB`: Filter matching filenames (e.g. `*.tmp`, `*.cache`).
- `--older-than DAYS`: Only match files older than `N` days.
- `--exclude-pattern PATTERN`: Exclude specific directories or extensions.

### Performance & Safety
- `--threads N`: Parallel scanning threads (defaults to logical CPU count).
- `--config PATH`: Custom YAML configuration file path.
- `--verbose`: Detailed debug logging output.
- `--log-file PATH`: Log output destination.