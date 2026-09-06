# 📑 Cortex Workstation — Master Feature Directory & Reference

Welcome to the centralized feature catalog for **Cortex Workstation**. This document provides an exhaustive, structured overview of every interactive UI page, command-line utility, analyzer engine, and system maintenance tool.

---

## 🧭 High-Level Organization

Cortex Workstation organizes its capabilities into **10 dedicated functional sections** encompassing **139 interactive pages**, **62 system tools**, and **23 specialized file & deduplication analyzers**:

| Section ID | Section Title | Page Count | Primary Subsystems |
| :--- | :--- | :--- | :--- |
| `overview` | **Command Center** | 2 | Real-time System Dashboard, PC Health Score (Cortex Heuristic Index) |
| `cleanup` | **Cleanup & Storage** | 34 | Winapp2.ini engine, Shader caches, Dev package purger, WUDO, Old large files |
| `files` | **Files & Explorer** | 22 | Nexus VFS Explorer, Restart Manager Unlocker, Checksum Matrix, USN Journal |
| `system` | **System Performance** | 31 | DirectStorage BypassIO, Kernel Standby Purger, SSD TRIM, Dev Drive CoW |
| `activity` | **Privacy & Activity** | 9 | BAM/SRUM Execution Forensics, AI Features & Recall Sanitizer, Privacy Shield |
| `network` | **Network & Defense** | 11 | Network Security Audit, UPnP/WAN Gateway, TCP/IP Optimizer, Hosts Shield |
| `apps` | **Apps & Security** | 15 | Installed App Manager, Residual Leftover Hunter, Windows Services, Context Menus |
| `security` | **Security Tools** | 5 | Process Security Tokens, BitLocker & TPM Status, Silent BitRot Integrity Scrubber |
| `recovery` | **Recovery & Reports** | 5 | Undo/Redo Manifest Restoration, Diagnostic Bundles, System Reports |
| `maintenance` | **Maintenance & Repair** | 5 | Component Store Repair (DISM/SFC), Windows Update, VSS Shadow Health |

---

## 🔍 Detailed Feature Catalogs

For granular breakdowns, please refer to the dedicated reference documents:

- **[Interactive Feature Directory](FEATURE_DIRECTORY.md)**: Catalog of all 139 interactive pages with navigation IDs, category icons, and factory bindings.
- **[System Tools Reference](api/system-tools.md)**: Specifications for all 62 Windows NT maintenance tools.
- **[Analyzers Reference](api/analyzers.md)**: Specifications for duplicate finders, storage probes, and heuristic analyzers.
- **[CLI & Shell Usage Guide](usage.md)**: Syntax and flag reference for automated shell execution.
- **[Historical Verification & Feature Audit Archive](audit/COMPLETE_FEATURES_CHECKLIST.md)**: Archive of detailed feature completion checklists and verification runs.
