# Cortex Cleaner Usage Guide

**Cortex Cleaner** is a comprehensive, production-grade system maintenance suite and advanced file manager built with Python, PySide6 (Qt6), and high-performance native engines.

---

## 🚀 Launching Cortex Cleaner

### 1. Graphical User Interface (GUI)
Launch the full premium interface with sidebar navigation, **139 system maintenance and power tool pages**, and the embedded **Nexus File Manager**:

```bash
# Recommended launcher
python run_gui.py

# Or via the package module
python -m cortex_unified.ui.premium.window
```

### 2. Command Line Interface (CLI)
Cortex Cleaner provides safe, high-speed CLI commands for automated scripts, CI/CD pipelines, and headless environments:

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
2. **Sidebar Navigation**: Collapsible (`Ctrl+H`) categorized navigation housing **139 system care and diagnostics tools**:
   - **Command Center**: Dashboard, PC Health Check, Quick Scan, System Overview.
   - **Cleanup & Storage**: Cleanup Hub, Junk Files, Large Files, Empty Files, Temp Files, Browser Deep Cleaner, WinSxS Store (24H2 Staged Packages), WUDO Delivery Optimization, Developer Package Caches, App Residual Hunter, Old & Inactive Files Finder.
   - **Performance & Gaming**: Game Mode & FPS Booster, RAM Optimizer, Standby Memory Purger, DirectStorage Acceleration, CPU Power Plans, Startup Optimizer, Process Studio, Disk Benchmark.
   - **Privacy & Security**: Windows Privacy Blocker, Telemetry Sanitizer, AI & Recall Sanitizer, Bad Extensions & EXIF Studio, Secure File Shredder, Secret/API Key Scanner, Restart Manager File Unlocker.
   - **System Maintenance & OS**: Windows Update Repair, VSS Snapshot Manager, VSS Subsystem Health, Device Driver Manager, Context Menu Cleaner, Registry Deep Scan, Environment Variables.
   - **Network & Diagnostics**: Network Security Audit, LAN Device Discovery, WAN & UPnP Gateway Auditor, Active Connections, TCP/IP Tuning, Hosts File Shield, DNS Speed Benchmark.
   - **Files & Nexus Explorer**: **Nexus File Manager**, Batch File Renamer, File Hash & Checksum Matrix, Directory Diff, File Splitter/Joiner, ADS Manager, Binary Differ, PAR2 Parity Recovery.
3. **Content Workspace**: High-performance lazy-loaded tool pages with smooth scrolling and animations.
4. **Status Bar & Notifications**: Real-time engine health, local offline suggester notifications, and resource telemetry.

---

## 🛠️ Specialized Studios & Feature Integrations

### 1. Gaming Session & FPS Booster (`gamemode`)
- Switches Windows power plan to Ultimate / High Performance.
- Suspends or lowers CPU priority of background services.
- Trims working set memory of non-essential processes before launching games.

### 2. Delivery Optimization (WUDO) Cleaner (`delivery`)
- Scans and safely purges Windows Update Delivery Optimization peer caches (`C:\Windows\SoftwareDistribution\DeliveryOptimization`).
- Safely coordinates `DoSvc` service state during cache purges.

### 3. WAN & UPnP Gateway Auditor (`wanaudit`)
- Discovers local UPnP/IGD router gateways.
- Audits open external WAN ports and active NAT port forward mappings.
- Evaluates exposure risks on administrative services (SSH, Telnet, RDP, Web GUI).

### 4. Old & Inactive Files Finder (`oldfiles`)
- Discovers files untouched for 30, 60, 90, 180, or 365+ days.
- Smart system exclusions prevent touching essential OS dependencies.

### 5. Uninstalled App Residual Hunter (`residuals`)
- Cross-references installed application registries with `AppData` and `ProgramData` directories.
- Identifies orphaned cache and configuration folders from uninstalled applications.

### 6. Bad Extensions & EXIF Studio (`badfiles`)
- Detects magic-byte spoofing (e.g. executables masked with `.jpg` extensions).
- Finds invalid or illegal file names.
- Scrubs sensitive camera and GPS location EXIF metadata from photos.

### 7. Advanced Process & Threat Studio (`procstudio`)
- Live process monitoring with CPU, memory (MB), and path details.
- Filter search and safe process termination actions.

### 8. Interactive Sunburst & TreeMap Visualizations
- In **Disk Space Scanner** (`diskanalyzer`), export full interactive Plotly Sunburst and TreeMap HTML diagrams directly to disk.

### 9. Project Cache Auto-Discovery
- In **Package Managers** (`packages`), auto-discover project build directories (`node_modules`, `target`, `.venv`, etc.) across all mounted fixed drives with a single click.

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
| `package-cleanup` | Clean pip, npm, yarn, cargo, and build caches |
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