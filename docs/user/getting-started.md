# 🚀 Getting Started with Cortex Workstation

Welcome to Cortex Workstation! This guide will walk you through system requirements, installation, and launching the application.

---

## 💻 System Requirements

| Specification | Minimum Requirement | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 (Build 19041+) or Windows 11 | Windows 11 (22H2+ recommended for DirectStorage & Dev Drives) |
| **Python Runtime** | Python 3.10 to 3.14 (64-bit) | Python 3.12 or 3.14 |
| **Processor** | Dual-core x64 CPU | Modern Quad-core or higher (supports multi-threaded hash pipelines) |
| **Memory (RAM)** | 4 GB RAM | 8 GB+ RAM |
| **Disk Space** | 500 MB free storage | 2 GB+ (for caches, forensic reports, and index storage) |

---

## 📦 Windows Standalone Executables (No Setup Required)

If you are an end-user or system administrator who wants to run Cortex Workstation without installing Python, Rust, or compilers:

| Architecture / Distribution | Format | Support Status | Download & Execution Method |
| :--- | :--- | :--- | :--- |
| **Windows 10/11 x64 Setup Installer**<br>*(Recommended)* | `.exe` | ✅ **Fully Supported** | Download [**`Cortex-Workstation-v1.2.0-Setup.exe`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Setup.exe) (338 MB) from [**GitHub Release v1.2.0**](https://github.com/Destroyer-official/Cortex-Workstation/releases/tag/v1.2.0). Automated 1-click installer with desktop & Start Menu shortcuts and clean uninstaller. |
| **Windows 10/11 x64 Standalone Portable** | `.zip` | ✅ **Fully Supported** | Download [**`Cortex-Workstation-v1.2.0-Windows-x64.zip`**](https://github.com/Destroyer-official/Cortex-Workstation/releases/download/v1.2.0/Cortex-Workstation-v1.2.0-Windows-x64.zip) (328 MB). Extract anywhere and run `CortexCleaner.exe`. Zero installation required. |
| **Windows 11 ARM64**<br>*(Snapdragon X Elite / Copilot+ PCs)* | `.exe` / `.zip` | ✅ **Natively Supported** | Natively supported via Windows 11 Microsoft Prism x64 emulation. Runs seamlessly with zero setup. |
| **Windows 32-bit (x86)** | — | ❌ **Not Supported** | PySide6 / Qt 6 officially dropped 32-bit Windows support upstream in Qt 6.0; Windows 11 itself strictly requires a 64-bit CPU architecture. |

---

## 🛠️ Developer Installation from Source

### 1. Clone the Repository
```bash
git clone https://github.com/Destroyer-official/Cortex-Workstation.git
cd Cortex-Workstation
```

### 2. Set Up a Virtual Environment
```powershell
# Using standard Python
python -m venv venv
.\venv\Scripts\Activate.ps1

# Or using Conda
conda create -n cortex python=3.12 -y
conda activate cortex
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 🎮 Launching the Application

### Modern Presentation Shell (Recommended)
To launch the full 139-tool workstation interface with HiDPI support and modern themes:
```bash
python run_gui.py
```

Or run the one-click Conda launcher:
```powershell
.\run_with_conda.ps1
```

### Command Line Interface (CLI)
Cortex Workstation includes 21 high-throughput CLI subcommands for headless and server environments:
```bash
# View all available CLI tools
python -m cortex_unified.cli --help

# Run a quick system disk analysis
python -m cortex_unified.cli analyze-disk --path C:\

# Clean temporary files (dry run by default)
python -m cortex_unified.cli clean-temp --dry-run
```

---

## 🔐 Administrative Privileges
While basic file analysis, deduplication, and file management run in user-space, certain forensic and repair tools require elevated permissions:
* **Registry Compaction & Cleaning**
* **Windows Update (DISM / SFC) Repair**
* **DirectStorage BypassIO Tuning**
* **Memory Standby Purging**
* **VSS Shadow Copy Management**

To access these features, right-click your terminal or launcher and select **"Run as administrator"**.
