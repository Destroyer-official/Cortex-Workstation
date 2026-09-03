# 🌌 Cortex Workstation Documentation Hub

Welcome to the central documentation command for **Cortex Workstation** — the ultimate, high-performance Windows NT systems optimization, digital forensics, and native file management platform.

Because this repository contains over **132 interactive tools**, **62 native Windows system modules**, **23 forensic analyzers**, and deeply optimized multi-threaded C/Python engines, our documentation is structured strictly by audience and intent:

* **[📦 User & Integrator Space](user/getting-started.md)** — Installation, step-by-step how-to recipes, configuration schemas, and daily system operations.
* **[🏗️ Developer & Contributor Platform](dev/architecture.md)** — Repository architecture map, thread safety models, PathGuard boundaries, testing pipelines, and PR standards.
* **[🔌 Core Function & API Reference](api/overview.md)** — Comprehensive interface specifications, lifecycle tables, and technical breakdowns across all subsystems.

---

## 🛠️ The Global Repository Map

Before diving into the code, here is how the core repository directories are arranged and what they handle:

| Directory | Subsystem Focus | Purpose & Architectural Boundary |
| :--- | :--- | :--- |
| 📂 [`/src/cortex_unified/core`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/src/cortex_unified/core) | Central Engine | Thread pools, IPC protocols, memory barriers, process lifecycle, and configuration management. |
| 📂 [`/src/cortex_unified/system_tools`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/src/cortex_unified/system_tools) | OS & Forensics | 62 standalone Windows NT diagnostic tools (VSS, DirectStorage, MFT Slack, SRUM/BAM, BitLocker, Dev Drives). |
| 📂 [`/src/cortex_unified/analyzers`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/src/cortex_unified/analyzers) | Deduplication | 23 advanced analyzers including Perceptual Hash, Fuzzy Ssdeep, FastCDC chunking, and Czkawka algorithms. |
| 📂 [`/src/NexusExplorer`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/src/NexusExplorer) | Native File Manager | Ultra-fast VFS tabbed explorer with USN Journal change tracking, PAR2 error correction, and unbounded undo/redo. |
| 📂 [`/src/cortex_unified/ui`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/src/cortex_unified/ui) | Presentation Shell | 132 lazy-loaded Qt/PySide6 tool pages, HiDPI design tokens, and 132 scalable vector SVG icons. |
| 📂 [`/src/cortex_unified/translations`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/src/cortex_unified/translations) | Multi-Language | Real-time locale switching supporting English, German, Spanish, French, Chinese, and Japanese. |
| 📂 [`/tests`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/tests) | Automated Test Suites | 1,569 automated test cases covering every tool, engine, worker thread, and GUI component. |
| 📂 [`/scripts`](https://github.com/Destroyer-official/Cortex-Workstation/tree/main/scripts) | Diagnostics & Build | Diagnostic verification suites (`verify_production_readiness.py`), PyInstaller packaging, and code audits. |

---

## 🚀 1. User & Integrator Space

*This space is dedicated to getting up and running quickly. It treats the project as a high-performance, turnkey workstation application.*

### Quick Start
* **[Installation & Requirements](user/getting-started.md):** Python 3.10–3.14 prerequisites, virtual environments, Git setup, and desktop shortcuts.
* **[Configuration Engine](user/configuration.md):** Complete reference of runtime parameters, safety override flags, and config files.

### Real-World Recipes
* **[1-Click Full System Cleanup](user/how-to-guides.md#1-click-full-system-cleanup):** Clean Windows shader caches, temporary files, delivery optimization, and browser profiles.
* **[Deduplication & Storage Reclaim](user/how-to-guides.md#deduplication-storage-reclaim):** Discover exact, perceptual photo, and fuzzy binary duplicates safely.
* **[Windows Deep Repair](user/how-to-guides.md#windows-deep-repair-optimization):** Run Component Store DISM cleanup, SFC health restoration, and VSS Shadow Copy audits.
* **[Nexus Native Explorer Guide](user/nexus-explorer.md):** Multi-tabbed dual-pane file management, batch renaming, and transactional undo.

---

## 🏗️ 2. Developer & Contributor Architecture

*This space maps internal logic, low-level APIs, thread models, and coding conventions to help engineers build and contribute safely.*

### System Blueprint & Engineering Principles
* **[Core Architecture & Subsystems Map](dev/architecture.md):** Complete breakdown of data flow, background worker queues, and Qt signal dispatchers.
* **[State Management & Thread Safety](dev/threading-safety.md):** How the engine enforces PathGuard safety boundaries and thread isolation.
* **[Testing & CI/CD Pipelines](dev/testing.md):** Running the 1,569 unit tests locally, mocking Windows APIs, and validating coverage.
* **[Release & PR Standards](dev/release-process.md):** Semantic versioning, conventional commits, and contribution checklists.

### Core Function & Subsystem Reference
*Authoritative breakdowns of critical internal engines. Every core subsystem registers its interface here:*

| Subsystem Core | Main Lifecycle Functions | Purpose & Functionality | Architectural Safety Rules |
| :--- | :--- | :--- | :--- |
| `cortex_unified.core.engine` | `scan()`, `clean()`, `cancel()` | Central engine coordinator managing worker pools, safety scans, and reporting. | Strict non-blocking async execution; all mutations route through `PathGuard`. |
| `cortex_unified.system_tools` | `scan()`, `optimize()`, `audit()` | 62 standalone OS diagnostics querying Windows NT APIs, PowerShell, and registry. | Read-only discovery by default; system mutations require user confirmation. |
| `cortex_unified.analyzers` | `find_duplicates()`, `hash_file()` | High-throughput hashing (BLAKE3, SHA-256), perceptual imaging, and CDC chunking. | Zero-memory file streaming with chunk-level cancellation checkpoints. |
| `NexusExplorer.native` | `read_directory()`, `copy_batch()` | Fast VFS filesystem operations with USN Journal change streams. | Fully transactional; every write operation logs to the undo/redo ledger. |
| `cortex_unified.ui.premium` | `load()`, `_refresh()`, `_run()` | 132 lazy-loaded presentation pages with HiDPI tokenized CSS palettes. | Zero eager imports on startup; UI threads remain responsive at 60 FPS. |

---

## 🤝 3. Open Source Contribution Standards

Cortex Workstation is **100% free and open-source under the MIT License**. We welcome contributions from developers worldwide!

To ensure high quality across our massive codebase, please adhere to these standards:
1. **Check for Duplication:** Before implementing a new utility or forensic scanner, check `cortex_unified/system_tools` and `analyzers/` to see if an existing module provides that interface.
2. **Local Test Validation:** Always run the test suite locally before submitting a PR:
   ```bash
   pytest tests/ --no-cov
   python scripts/verify_production_readiness.py
   ```
3. **Keep Documentation Synchronized:** If your pull request introduces a new tool, updates a configuration flag, or changes a public API, update the corresponding documentation under `docs/`.

---

## 🆘 Troubleshooting & Community Assistance

* **[Troubleshooting Guide](user/troubleshooting.md):** Solutions for common issues (elevation requirements, missing DLLs, winget timeouts).
* **[GitHub Issues](https://github.com/Destroyer-official/Cortex-Workstation/issues):** Bug reports, forensic tool suggestions, and performance profiling.
* **[Discussions & Roadmap](https://github.com/Destroyer-official/Cortex-Workstation/discussions):** Architectural proposals and feature requests.
