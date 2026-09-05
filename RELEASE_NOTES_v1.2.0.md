# 🚀 Cortex Workstation v1.2.0 — Production Release

The Ultimate Windows NT Systems, Forensics, File Management & Optimization Platform.

---

## 🌟 Highlights & What's New in v1.2.0

### 1. 📦 Standalone Windows Installer (.exe) & Portable Zip
- **1-Click Windows Setup**: Download [**`Cortex-Workstation-v1.2.0-Setup.exe`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Setup.exe) (338 MB) for an automated setup wizard with Desktop and Start Menu shortcut integration.
- **Portable Distribution**: Download [**`Cortex-Workstation-v1.2.0-Windows-x64.zip`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Windows-x64.zip) (328 MB) to extract and run anywhere without installation.
- No Python, Rust, compilers, or developer tools required.
- Native UAC integration prompts for elevation automatically when interacting with kernel and driver-level components.

### 2. 🖥️ 139 Interactive GUI Pages & 62 Specialized System Engines
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

### 3. 🔒 Hardened System Process Protection
- Enhanced `kill_process_tree` with `is_protected_process` safeguarding critical Windows NT system processes including explorer.exe, dwm.exe, csrss.exe, smss.exe, services.exe, lsass.exe, and cortex.exe.

### 4. 🎨 Custom High-Resolution Brand Icon & Windows Taskbar Integration
- **Multi-Layer Windows Brand Icon**: Built multi-resolution icon (`cortex.ico` in 256x256, 128x128, 64x64, 48x48, 32x32, 16x16) embedded directly into `CortexCleaner.exe` and `Cortex-Workstation-v1.2.0-Setup.exe`.
- **Windows Taskbar Identity**: Registered `SetCurrentProcessExplicitAppUserModelID("Destroyer.CortexWorkstation.App.1.2.0")` ensuring Windows groups the app under its own custom brand icon instead of generic Python/Tkinter icons.
- **Shortcuts & Registry**: Desktop and Start Menu shortcuts explicitly link to `IconLocation,0`, and uninstaller in Windows Settings registers the custom brand icon.

### 5. 🛠️ Robust Packaging & Logging Resilience
- Full crawling of all 323 submodules across `cortex_unified` ensuring standard library logging handlers, crypto, and VFS modules are bundled directly in the PYZ.
- Safe stream fallback (`_SafeStream`) ensuring windowed GUI execution on Windows never crashes with `NoneType object has no attribute 'write'`.

---

## 🧪 Quality & Verification Metrics
- **AST & Compilation Audit**: **494 / 494** Python program files passed (100% Pass Rate).
- **Unit & Functional Tests**: All tests passing across backend engines, GUI widgets, and system tools.
- **Native Rust Subsystem**: Compiled and verified cleanly with Rust 1.98.0 toolchain.
- **Docstring Coverage**: 100% docstring coverage across all public functions and classes.

---

## 📥 Downloads & Cryptographic Checksums

| Package | Format | Target Platform | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| ⚡ [**`Cortex-Workstation-v1.2.0-Setup.exe`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Setup.exe) | **Setup Installer (.exe)** | Windows 10/11 (64-bit) | `D5CBAAEABFEDB23FB0EA2CBDB7D33A7C1B906FC926E876DBB7E778C9D24B1362` |
| 📦 [**`Cortex-Workstation-v1.2.0-Windows-x64.zip`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Windows-x64.zip) | **Portable Archive (.zip)** | Windows 10/11 (64-bit) | `39B81A9A3C9FF42389648F0273A0BAAA8C5E69B20350902B2028E0068E57954F` |
| 📦 **Source Code (.zip / .tar.gz)** | **Source Archive** | Cross-Platform | Official Git Tag `v1.2.0` Archive |
