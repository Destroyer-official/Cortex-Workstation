# 🚀 Cortex Workstation v1.2.0 — Production Release

The Ultimate Windows NT Systems, Forensics, File Management & Optimization Platform.

---

## 🌟 Highlights & What's New in v1.2.0

### 1. 📦 Standalone Windows Executable for Non-Technical Users
- **Zero-Setup Distribution**: Download [**Cortex-Workstation-v1.2.0-Windows-x64.zip**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Windows-x64.zip), extract, and run `CortexCleaner.exe`.
- No Python installation, compilers, or command-line setup required.
- Native UAC integration prompts for elevation automatically when interacting with kernel and driver-level components.
- Includes complete runtime, Qt6 graphics engine, vector SVG icon pipeline, and localized translation dictionaries.

### 2. 🖥️ 132 Interactive GUI Pages & 62 Specialized System Engines
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

### 3. 🛡️ Hardened System Process Protection
- Enhanced `kill_process_tree` with `is_protected_process` safeguarding critical Windows NT system processes including explorer.exe, dwm.exe, csrss.exe, smss.exe, services.exe, lsass.exe, and cortex.exe.

### 4. 📚 Comprehensive Multi-Tiered Documentation Hub
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
| Package | Platform | Description |
| :--- | :--- | :--- |
| 📦 [**Cortex-Workstation-v1.2.0-Windows-x64.zip**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Windows-x64.zip) | Windows 10/11 (64-bit) | Standalone pre-compiled portable application (Extract & Run) |
| 📦 **Source Code (.zip / .tar.gz)** | Cross-Platform | Full open-source repository checkout |
