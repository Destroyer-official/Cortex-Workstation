<div align="center">
  <h1>🛡️ Cortex Cleaner Suite</h1>
  <p><strong>Military-Grade System Optimization, Privacy Shield, and Deep Maintenance Suite</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Version-1.0.0-blue.svg" alt="Version">
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgray.svg" alt="Platform">
    <img src="https://img.shields.io/badge/Python-3.8%2B-green.svg" alt="Python">
    <img src="https://img.shields.io/badge/License-MIT-orange.svg" alt="License">
  </p>
</div>

<br>

**Cortex Cleaner Suite** is a professional-grade, highly modular, and aggressive system optimization application. Designed to exceed standard cleanup utilities, Cortex Cleaner employs "weaponized" algorithms for DoD-standard file shredding, strict-heuristic residual hunting, comprehensive OS telemetry blocking, and multi-threaded deep system scanning. 

It solves real-world performance tuning, privacy management, and system decay problems for power users and enterprise environments.

---

## 🚀 Weaponized Core Features

### 1. ⚡ 1-Click Smart Scanner & Command Dashboard
- **Health Score Algorithm:** Mathematically calculates system health (0-100) based on junk accumulation, orphaned registry impact, browser privacy risks, and excessive startup loads.
- **Deep Cache Cleaning:** Simultaneously targets OS Temp, Browser Caches, Windows Update Download Caches, Prefetch, and Thumbnail Caches.
- **Background Orchestration:** Utilizes `QThread` workers for non-blocking UI during heavy I/O operations.

### 2. 🗑️ Advanced Deep Uninstaller & Residual Hunter
- **Registry-Based App Discovery:** Directly reads `HKLM`, `HKCU`, and `WOW6432Node` Windows registry hives to list installed programs (even hidden ones), retrieving exact sizes and uninstall strings.
- **Heuristic Residual Hunting:** Once an app is removed, the `ResidualHunter` scans `AppData`, `LocalAppData`, `ProgramData`, and `Program Files`. It uses strict token-based ML-lite strategies to eliminate false positives while safely removing leftover application debris.

### 3. 🛡️ Absolute Privacy Shield
- **Browser Sweeper:** Dynamically discovers browser profiles across Chrome, Edge, Brave, Vivaldi, Opera, and Firefox. Wipes History, Cookies, Cache, and Session Data completely.
- **OS Telemetry Blocker:** A powerful registry editor that terminates 16+ Windows tracking vectors (Advertising ID, Cortana, Handwriting data sharing, Clipboard cloud sync, Windows Update Telemetry, etc.). Includes a 1-click "Restore Defaults" safe mechanism.
- **System Trace Wiper:** Flushes DNS cache, destroys "Recent Documents" lists, and wipes Windows INetCache files.

### 4. 🪚 Military-Grade File Shredder (DoD 5220.22-M)
- **3-Pass Overwrite:** Completely sanitizes sensitive data by executing independent passes: `0x00` zeroization, `0xFF` writing, and cryptographically secure random data overwriting.
- **MFT Evasion:** Bypasses basic undelete capabilities by aggressively flushing IO buffers (`os.fsync`) directly to disk sectors.

### 5. ⏱️ Real-Time Resource Monitoring Agent
- **Background Autonomy:** Runs silently in the background, sampling CPU, RAM, and Disk space.
- **System Tray Integration:** Warns the user of critical spikes (>90% RAM/CPU) or low storage states via non-intrusive balloon popups, avoiding alert fatigue via cooldown governors.

### 6. 📁 Ultimate File Organization & Analytics
- **Duplicate Finder:** Fast multi-algorithm hashing (MD5/SHA256) to deduplicate drives.
- **Large File Discovery & Disk Analyzer:** Visually breaks down disk topology to find storage anomalies.
- **Sentinel Pro Security Scanner:** Scans project directories and system paths for exposed secrets, API keys, and vulnerabilities using Regex heuristics.

---

## 🏗️ System Architecture & Codebase Map

The `cortex_unified` engine is strictly modularized for professional maintainability and rapid feature scaling.

```text
src/cortex_unified/
├── __main__.py                    # Primary application entry point
├── cli/                           # Command Line Interface logic
│   └── cli.py                     # Main CLI router
├── core/                          # Fundamental engines
│   ├── background_agent.py        # Real-time resource watcher (CPU/RAM/Disk)
│   ├── config.py                  # YAML/JSON global configuration loading
│   ├── smart_scanner.py           # The Smart Scan orchestrator engine
│   ├── scanner.py                 # Core file/directory traversal methods
│   └── deleter.py                 # Safe deletion and Trash-moving logic
├── analyzers/                     # Target-specific data processors
│   ├── privacy_cleaner.py         # Advanced browser profile dynamic cleanup
│   ├── residual_hunter.py         # Strict tokenized orphan folder detector
│   ├── weaponized_shredder.py     # DoD-standard overwriting algorithms
│   ├── duplicate_finder.py        # Hashing and file matching logic
│   ├── file_shredder.py           # Legacy file shredder interface
│   ├── leftover_detector.py       # ML-assisted leftover package detector
│   └── ...                        # Broken links, cache, large files 
├── system_tools/                  # Deep OS-level interactions
│   ├── app_uninstaller.py         # Registry Uninstaller and WMI integration
│   ├── registry_cleaner.py        # Registry orphaned entry detection/removal
│   ├── telemetry_blocker.py       # Windows Privacy/Tracking registry editor
│   ├── startup_manager.py         # OS Boot execution modifier
│   └── process_analyzer.py        # Live running task enumeration
├── performance/                   # Advanced scanning algorithms
│   ├── multi_drive_scanner.py     # Parallel SSD/HDD parsing
│   ├── resource_throttler.py      # I/O limitation management
│   └── optimization.py            # Windows OS tuning module
├── ui/                            # PySide6 Qt GUI Structure
│   ├── main_window.py             # Main application GUI shell and router
│   ├── tray_icon.py               # System Tray background listener
│   ├── navigation/                # Sidebar and tab-routing logic
│   ├── safety/                    # Operational safety guards and validators
│   └── tabs/                      # Independent GUI feature sections
│       ├── dashboard_tab.py       # 1-Click Smart Scan Command Center
│       ├── uninstaller_tab.py     # Deep Uninstaller UI logic
│       ├── privacy_tab.py         # Telemetry & Browser Suite UI
│       ├── file_shredder_tab.py   # Secure Deletion UI
│       └── ...                    # 15+ other dedicated tool tabs
└── visualization/                 # Advanced Data Representation
    ├── tree.py                    # Sentinel Pro Security Scanner integrations
    ├── treemap_generator.py       # Disk usage generation
    └── sunburst_generator.py      # Visual file breakdowns
```

---

## 💻 Installation & Usage

### 1. Requirements
- Python 3.8 or higher.
- (Windows only) Administrator privileges for Telemetry Blocking, Registry Cleaning, and Deep Uninstallation.
- Recommended: 4GB+ RAM, SSD.

### 2. Setup Procedure
Ensure you are in the project root containing `pyproject.toml` and `requirements.txt`.

```bash
# 1. Create a pristine virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS / Linux

# 2. Install dependencies (Core + GUI + Visualization + Trash integration)
pip install -r requirements.txt
pip install -e .[all]
```

### 3. Execution

**Start the Graphical Interface (GUI):**
```bash
python run_gui.py
# Or use the entry point directly
python -m cortex_unified
```

**Start the CLI (Automation Ready):**
```bash
python run_cli.py --help
python run_cli.py smart-scan --auto-clean
```

---

## ⚙️ Key Technical Integrations

### Safe Execution & Sandboxing
Functions touching the Windows Registry or System directories (`ResidualHunter`, `RegistryCleaner`, `AppUninstaller`) utilize an internalized safety system. 
- **Blocklists:** Critical Windows arrays (`System32`, `WinSxS`, `Program Files` base) are completely blocklisted from automated deletions.
- **Dry-Runs:** The CLI heavily supports `--dry-run` to output changes to JSON before committing to IO.
- **Backups:** Registry removals automatically trigger a `reg export` execution, dumping a `.reg` reversion file into `~/CortexCleanerBackups/`.

### Parallel Scaling
Through customized `QThread` controllers on the GUI and `ThreadPoolExecutor` configurations in the core (`multi_drive_scanner.py`), the software saturates modern multi-core NVMe arrays, ensuring that scanning the `C:\` drive does not result in application hangs.

---

## ⚠️ Mission Critical Disclaimer

**USE WITH CAUTION.**

Certain modules within Cortex Cleaner Suite (specifically the **Weaponized Shredder**, **Telemetry Blocker**, and **Registry Cleaner**) perform system-level or destructive file operations.
- The `WeaponizedShredder` destroys files beyond recovery. Do not target active directories.
- The `TelemetryBlocker` alters OS-level properties. While an "undo" mechanism exists, applying these configurations changes how the local OS connects to Microsoft servers.

*Cortex Cleaner Team assumes no responsibility for data loss or OS instabilty resulting from improper use of advanced modules.*