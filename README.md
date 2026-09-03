<div align="center">
  <h1>🛡️ Cortex Workstation</h1>
  <p><strong>The Ultimate Windows NT Systems, Forensics & File Management Platform</strong></p>
  <p>
    <a href="https://github.com/Destroyer-official/Cortex-Workstation"><img src="https://img.shields.io/badge/Version-1.2.0-blue.svg?style=for-the-badge" alt="Version"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blueviolet.svg?style=for-the-badge" alt="Python"></a>
    <a href="https://www.microsoft.com/windows"><img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(x64)-0078D6.svg?style=for-the-badge" alt="Platform"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License"></a>
    <a href="docs/FEATURE_DIRECTORY.md"><img src="https://img.shields.io/badge/Interactive%20Pages-132%20Pages-00D2FF.svg?style=for-the-badge" alt="Interactive Pages"></a>
    <a href="ONE_BY_ONE_VERIFICATION_REPORT.md"><img src="https://img.shields.io/badge/Program%20Files-471%20Verified%20(100%25)-success.svg?style=for-the-badge" alt="Program Files"></a>
    <a href="tests/"><img src="https://img.shields.io/badge/Diagnostics-297%20Passed%20(100%25)-success.svg?style=for-the-badge" alt="Tests"></a>
  </p>
</div>

<br>

**Cortex Workstation** is an enterprise-grade Windows operating system workstation, forensic storage analyzer, and dual-pane virtual file manager. Designed for systems administrators, forensic investigators, power users, and developers, Cortex Workstation provides direct, low-level control over Windows NT internals, NTFS/ReFS filesystems, kernel memory management, and process security tokens.

Combining the **Cortex Unified Optimization Engine** with the high-performance **Nexus Explorer VFS Subsystem**, Cortex Workstation delivers a responsive, non-destructive, and military-grade toolkit that eliminates system rot, reclaims gigabytes of locked storage, and protects data integrity.

---

## 📑 Table of Contents

- [Key Capabilities & Feature Highlights](#-key-capabilities--feature-highlights)
- [System Architecture](#-system-architecture)
- [Interactive Navigation & UI Pages](#-interactive-navigation--ui-pages)
- [Quickstart & Installation](#-quickstart--installation)
- [Command Line Interface (CLI)](#-command-line-interface-cli)
- [Verification & Quality Assurance](#-verification--quality-assurance)
- [Documentation Index](#-documentation-index)
- [Contributing](#-contributing)
- [Security & Safe Execution Policy](#-security--safe-execution-policy)
- [License](#-license)

---

## ⚡ Key Capabilities & Feature Highlights

### 🛡️ Enterprise Security & Forensics
- **Process Security Token Forensics**: Decodes Win32 process tokens, TokenIntegrityLevels (Untrusted, Low, Medium, High, System), TokenElevationTypes, and detects dangerous elevated privileges (`SeDebugPrivilege`, `SeImpersonatePrivilege`).
- **Windows BAM/DAM & SRUM Execution Forensics**: Audits kernel Background Activity Moderator (BAM) timestamps, Desktop Activity Moderator (DAM) traces, and inspects `SRUDB.dat` metrics with selective sanitization.
- **NTFS MFT Record Slack & Directory Index Sanitizer**: Audits 1024-byte file record segments and `$INDEX_ALLOCATION` buffers for orphaned resident file fragments, sanitizing slack space safely.
- **BitLocker & Drive Encryption Auditor**: Audits volume encryption status, cipher strength (XTS-AES 128 vs 256), and active TPM/PIN Key Protectors via `manage-bde` and WMI.
- **SMB Share & Network Exposure Auditor**: Audits active Windows shares, flags exposed administrative shares (`C$`, `ADMIN$`, `IPC$`), checks SMB signing, and alerts on deprecated SMBv1 protocols (EternalBlue vector).
- **Silent BitRot & Integrity Scrubber**: Maintains a persistent SQLite cryptographic baseline (SHA-256) to detect silent bit flips, physical storage degradation, and unauthorized file tampering.
- **Forensic Checksum Matrix**: Parallel multithreaded calculation of CRC32, MD5, SHA-1, SHA-256, and SHA-512 with batch manifest generation and directory verification (.sha256, .sfv, .md5).
- **Windows Restart Manager File Unlocker**: Uses native Win32 `rstrtmgr.dll` APIs to identify and release processes holding exclusive locks without crashing system services.

### 🚀 Hardware & System Performance Tuning
- **DirectStorage & BypassIO Hardware Acceleration Auditor**: Queries Windows 11 BypassIO state, validates NVMe-to-GPU DirectStorage paths, and flags blocking storage minifilters (antivirus, legacy filters).
- **RAM Standby List & Working Set Kernel Purger**: Invokes native `NtSetSystemInformation` (Class 80) to purge standby memory pages, empty process working sets, and flush modified pages directly to disk.
- **Windows Search Index (Windows.edb) Optimizer**: Stops WSearch and performs offline ESENT B-tree defragmentation (`esentutl.exe /d`) or clean background catalog resets.
- **SSD NVMe TRIM & Wear-Leveling Optimizer**: Queries physical flash media types, inspects NTFS/ReFS `DisableDeleteNotify`, and triggers live volume block deallocation (`Optimize-Volume -ReTrim`).
- **ReFS Dev Drive & CoW Optimizer**: Detects Windows 11 Resilient File System (ReFS) Dev Drives, verifies instant Copy-on-Write (CoW) block cloning (`FSCTL_DUPLICATE_EXTENTS_TO_FILE`), and inspects Defender Performance Mode.
- **Windows Memory Compression (MMAgent)**: Measures real-time RAM compressed store size, working sets, and page combining savings. Allows toggling memory compression for low-latency competitive gaming or audio workstations.
- **Virtual Memory & Pagefile Hardware Tuner**: Audits physical RAM commit limits, peak paging loads, and multi-disk pagefile placement across high-speed NVMe drives.
- **Windows Service Manager**: Analyzes background services and provides 1-click scenario-based tuning profiles (Minimal, Workstation, Gamer, Enterprise Safe).

### 🧹 Deep Forensic Cleaning & Space Reclamation
- **Winapp2.ini Community Application Cleaner**: Declarative deep cleaning engine supporting over 500+ desktop applications, browsers, game launchers, and IDEs with dynamic path variable resolution.
- **GPU & DirectX Shader Cache Cleaner**: Deep cleans orphaned compiled shader binaries across DirectX D3DSCache, NVIDIA DXCache/GLCache, AMD DxCache, and Intel GPU caches.
- **Windows 11 AI & Recall Telemetry Cleaner**: Scans Copilot offline caches, Recall semantic stores, and checkpoints/truncates inflated SQLite WAL databases.
- **Developer Package Stores Cleaner**: Reclaims gigabytes of cached installer packages and build artifacts across Windows `winget`, Rust `cargo`, C++ `vcpkg`, and .NET `nuget`.
- **Volume Shadow Copy (VSS) Manager & Health Analyzer**: Audits shadow copy snapshots, flags stalled VSS writers (`[5] Waiting for completion`, `[8] Failed`), and provides 1-click state reset.
- **Virtual Environment & Sandbox Purger**: Reclaims storage locked in Windows Sandbox containers, Hyper-V saved states (`.vsv`, `.bin`), checkpoint differencing disks (`.avhdx`), and WSL2 scratch containers.

### 📁 Nexus Explorer Dual-Pane VFS File Manager
- **High-Throughput VFS Transport**: Dual-pane file management interface supporting tabs, split views, and asynchronous thread-pool transfer queues.
- **Native C/Rust FFI Bridge**: Hardware-accelerated transport bridge with seamless pure Python fallbacks.
- **NTFS USN Change Journal Indexer**: Queries `FSCTL_READ_USN_JOURNAL` for sub-second file indexing across millions of files without recursive directory walking.
- **PAR2 Reed-Solomon Error Correction**: Creates packet-based parity volumes for mission-critical archives, verifying cryptographic blocks and repairing corrupted sectors.

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph UI_Layer ["Presentation & Shell Layer (PySide6)"]
        A[PremiumMainWindow] --> B["Sidebar Navigation & Search (Ctrl+K)"]
        A --> C[PageRegistry & Lazy Page Loader]
        C --> D[132 Theme-Aware GUI Pages]
        D --> E[WorkerRuntime / QThreadPool]
    end

    subgraph Core_Engine ["Cortex Unified Orchestration Engine"]
        E --> F[SmartScanner & Engine Service]
        E --> G["System Tools Suite (62 Specialized Modules)"]
        E --> H["Analyzers & Cleaners (Residual Hunter, Shredder, S3-FIFO)"]
        E --> I[Background Agent & Resource Tray Monitor]
    end

    subgraph Nexus_VFS ["Nexus Explorer VFS Engine"]
        E --> J[NexusCore Transport Protocol]
        J --> K[Native C/Rust FFI Bridge]
        J --> L[Pure Python Fallback Engine]
        J --> M[USN Journal Scanner & MFT Traverser]
        J --> N[PAR2 Error Correction & Reed-Solomon Codec]
    end

    subgraph OS_Kernel ["Windows NT Subsystem & Hardware"]
        G --> O[Win32 Kernel32 / Advapi32 / Rstrtmgr APIs]
        G --> P[NTFS & ReFS File Systems]
        G --> Q[WMI / CIM Subsystem]
        G --> R[Windows PowerShell Engine]
    end
```

For comprehensive technical specifications on threading, Win32 interop, and design tokens, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🖥️ Interactive Navigation & UI Pages

Cortex Workstation features **132 interactive GUI pages** organized into **10 intuitive sections**:

| Section ID | Section Title | Page Count | Primary Features |
| :--- | :--- | :--- | :--- |
| `overview` | **Command Center** | 2 | System Overview Dashboard, PC Health Check |
| `cleanup` | **Cleanup & Storage** | 32 | One-Click Cleanup Hub, Extended Third-Party App Caches, Shader Caches, Dev Packages |
| `files` | **Files & Explorer** | 21 | Nexus File Explorer, Process Restart Manager Unlocker, Checksum Matrix, USN Journal |
| `system` | **System Performance** | 29 | DirectStorage BypassIO, Kernel Standby Purger, SSD NVMe TRIM, Dev Drive CoW |
| `activity` | **Privacy & Activity** | 9 | BAM/SRUM Execution Forensics, AI Features & Recall Sanitizer, Privacy Shield |
| `network` | **Network & Defense** | 10 | SMB Share Auditor, DNS Benchmark, Firewall Manager, Traffic Monitor |
| `apps` | **Apps & Security** | 14 | Deep Software Uninstaller, Outdated Driver Store Cleaner, Context Menu Manager |
| `security` | **Security Tools** | 5 | Process Tokens, BitLocker Encryption Status, BitRot Scrubber, Secure Shredder |
| `recovery` | **Recovery & Reports** | 5 | Volume Shadow Copies (VSS), Restore Points, Audit Reports, System Recovery |
| `maintenance`| **Maintenance & Repair** | 5 | VSS Writer Health, Windows Update Cleaner, Update Repair, Deep Disk Space Scanner |

*Full catalog and factory class mapping available in [`docs/FEATURE_DIRECTORY.md`](docs/FEATURE_DIRECTORY.md).*

---

## 🚀 Quickstart & Installation

### Prerequisites
- **Operating System**: Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Python**: Version 3.10 through 3.14 (64-bit).

### Development Setup

```powershell
# 1. Clone the repository
git clone https://github.com/Destroyer-official/Cortex-Workstation.git
cd Cortex-Workstation

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install dependencies and editable package
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# 4. Launch the Interactive GUI
python run_gui.py
```

---

## 💻 Command Line Interface (CLI)

Cortex Workstation provides a comprehensive command-line interface for automation and administrative scripts:

```powershell
# Display help and available commands
cortex --help
# or
python -m cortex_unified.cli.cli --help

# Run a quick system diagnostic scan
python -m cortex_unified.cli.cli scan

# Clean temporary files with dry-run preview
python -m cortex_unified.cli.cli clean --dry-run

# Run full production readiness verification
python -m cortex_unified.debug.runner
```

---

## 🧪 Verification & Quality Assurance

Every program file, tool, and page in the repository is backed by automated tests and strict validation:

| Test / Diagnostic Suite | Target Scope | Passed | Failures | Pass Rate |
| :--- | :--- | :--- | :--- | :--- |
| **Complete Unit Test Suite** (`pytest`) | Backend tools, VFS, hashing, and OS modules | **86 / 86** | **0** | **100%** |
| **Page Registry & Factory Verification** | All 132 page factories dynamically resolve | **132 / 132** | **0** | **100%** |
| **Vector SVG Icon Pipeline** | Crisp vector assets (no glyphs, no duplicates) | **132 / 132** | **0** | **100%** |
| **One-by-One Program File Audit** | AST syntax, compilation, and package imports | **471 / 471** | **0** | **100%** |

```powershell
# Run the complete test suite
pytest tests/ -v --no-cov

# Run one-by-one compilation and import audit
python scripts/check_all_structure_files.py
```

---

## 📚 Documentation Index

- 🏛️ **[Technical Architecture Specification](docs/ARCHITECTURE.md)**: Deep dive into threading models, VFS transport, Win32 interop, and design tokens.
- 🛠️ **[Developer Onboarding & Extension Guide](docs/DEVELOPER_GUIDE.md)**: Step-by-step tutorial on building new tools, GUI pages, and unit tests.
- 📖 **[Core API Reference](docs/API_REFERENCE.md)**: Signatures, methods, and dataclasses for all core modules.
- 📋 **[Complete Feature Directory (132 Pages)](docs/FEATURE_DIRECTORY.md)**: Detailed catalog of all interactive pages and factory bindings.
- ✅ **[Master Features Checklist (364 Items)](COMPLETE_FEATURES_CHECKLIST.md)**: Double-checked verification checklist of all 364 capabilities.
- 🔍 **[One-by-One Verification Report](ONE_BY_ONE_VERIFICATION_REPORT.md)**: Complete audit report covering all 471 program files.
- 🤝 **[Contributing Guidelines](CONTRIBUTING.md)**: Pull request workflows, code conventions, and commit standards.
- 🔒 **[Security Policy](SECURITY.md)**: Vulnerability disclosure, least privilege execution, and data safety guarantees.

---

## 🤝 Contributing

We welcome contributions from the open-source community! Whether you are implementing new system tools, refining UI animations, or reporting bugs, please read our [`CONTRIBUTING.md`](CONTRIBUTING.md) guide and adhere to our coding standards.

---

## 🔒 Security & Safe Execution Policy

Cortex Workstation is built on the principle of **non-destructive operation by default**:
- Scan passes are strictly read-only.
- Destructive actions (permanent file deletion, registry purging, service reconfiguration) require explicit user confirmation.
- Directory junctions and symlinks are unlinked safely without touching target directory contents.
- Least privilege execution ensures the application functions smoothly under standard user privileges, prompting for UAC elevation only when interacting with kernel-level components.

For vulnerability reporting procedures, see [`SECURITY.md`](SECURITY.md).

---

## 📄 License

Cortex Workstation is distributed under the open-source **MIT License**. See [`LICENSE`](LICENSE) for complete terms.