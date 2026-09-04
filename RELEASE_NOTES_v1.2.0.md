# 🚀 Cortex Workstation v1.2.0 — Production Release

The Ultimate Windows NT Systems, Forensics, File Management & Optimization Platform.

---

## 🌟 Highlights & What's New in v1.2.0

### 1. 📦 Standalone Windows Installer (.exe) & Portable Zip
- **1-Click Windows Setup**: Download [**`Cortex-Workstation-v1.2.0-Setup.exe`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Setup.exe) (370 MB) for an automated setup wizard with Desktop and Start Menu shortcut integration.
- **Portable Distribution**: Download [**`Cortex-Workstation-v1.2.0-Windows-x64.zip`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Windows-x64.zip) (362 MB) to extract and run anywhere without installation.
- No Python, Rust, compilers, or developer tools required.
- Native UAC integration prompts for elevation automatically when interacting with kernel and driver-level components.

### 2. 🧪 Non-Destructive Evaluation Sandbox Mode
- **Optional Enterprise Sandbox**: For IT administrators, software evaluators, and automated test runners wishing to audit UI layout, telemetry widgets, and navigation without modifying files on disk:
  - Run GUI in Sandbox Mode: `python run_gui.py --demo` (or `CortexCleaner.exe --demo`). Pre-populates 13.9 GB in simulated scan telemetry with live gauge preview.
  - Run Terminal CLI Sandbox: `python -m cortex_unified.cli.cli demo` (or `cortex demo`).
- **100% Live Production by Default**: Normal execution without `--demo` operates in live production mode, executing against real Windows NT APIs, filesystems, and hardware controllers.

### 3. 🖥️ 132 Interactive GUI Pages & 62 Specialized System Engines
- **System Performance & Kernel Management**:
  - DirectStorage BypassIO optimization
  - Dev Drive copy-on-write (CoW) configuration
  - Windows Kernel Standby Memory Purger
  - SSD NVMe TRIM & Flash Wear Leveling
  - High-precision CPU & RAM load monitoring
- **Forensic & Privacy Protection**:
  - BAM (Background Activity Moderator) & SRUM (System Resource Usage Monitor) execution forensics
  - Windows 11 Copilot, Recall, and Semantic Telemetry Sanitizer
  - Forensic multi-browser deep cache cleaner
- **Nexus File Explorer & High-Performance VFS**:
  - USN Journal Scanner & MFT direct traverser
  - PAR2 Reed-Solomon error correction and data recovery
  - Process Restart Manager unlocker for locked and in-use files
- **System Maintenance & Diagnostics**:
  - Component Store (WinSxS) analyzer
  - VSS (Volume Shadow Copies) and System Restore management
  - Registry AI analyzer with safe backup checkpoints
  - Outdated driver store cleaner & package cache manager

### 4. 🛡️ Hardened System Process Protection
- Enhanced `kill_process_tree` with `is_protected_process` safeguarding critical Windows NT system processes including explorer.exe, dwm.exe, csrss.exe, smss.exe, services.exe, lsass.exe, and cortex.exe.

### 5. 📚 Comprehensive Multi-Tiered Documentation Hub
- Three-column layout documentation hub deployed to GitHub Pages: [https://destroyer-official.github.io/Cortex-Workstation/](https://destroyer-official.github.io/Cortex-Workstation/)
- Complete AST-verified function inventory across 494 program files documented in [docs/FUNCTION_INVENTORY.md](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/docs/FUNCTION_INVENTORY.md).

---

## 🧪 Quality & Verification Metrics
- **AST & Compilation Audit**: **494 / 494** Python program files passed (100% Pass Rate).
- **Unit & Functional Tests**: All tests passing across backend engines, GUI widgets, and system tools.
- **Native Rust Subsystem**: Compiled and verified cleanly with Rust 1.98.0 toolchain.
- **Docstring Coverage**: 100% docstring coverage across all public functions and classes.

---

## 📥 Downloads
| Package | Format | Target Platform | Description |
| :--- | :--- | :--- | :--- |
| 🛡️ [**`Cortex-Workstation-v1.2.0-Setup.exe`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Setup.exe) | **Setup Installer (.exe)** | Windows 10/11 (64-bit) | Automated setup wizard with Desktop & Start Menu shortcut creation |
| 📦 [**`Cortex-Workstation-v1.2.0-Windows-x64.zip`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Windows-x64.zip) | **Portable Archive (.zip)** | Windows 10/11 (64-bit) | Pre-compiled standalone portable package (Extract & Run) |
| 📦 **Source Code (.zip / .tar.gz)** | **Source Archive** | Cross-Platform | Full open-source repository checkout |
