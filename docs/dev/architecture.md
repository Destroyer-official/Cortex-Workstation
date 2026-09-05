# 🗺️ Repository Architecture Map & Subsystems

This document provides a comprehensive technical overview of the Cortex Workstation & Nexus Explorer architecture for engineers, systems programmers, and open-source contributors.

---

## 1. System Overview & Core Philosophy

Cortex Workstation combines a modern **PySide6 (Qt for Python)** user interface with deep **Win32 Kernel/NTFS subsystems** and a high-performance **Nexus Explorer Virtual File System (VFS)** engine.

### Architectural Principles
1. **Zero Mockery & No Placeholders**: Every tool directly queries real Windows operating system APIs, file systems, or hardware counters.
2. **Non-Destructive by Default**: High-impact actions require explicit user confirmation, provide audit reports, and support rollback where feasible.
3. **Responsive UI Threading**: The Qt main GUI thread never blocks on heavy disk I/O, hash computations, or subprocess invocations. All intensive tasks run through asynchronous worker threads (`WorkerRuntime`).
4. **Resilient Degradation**: If an optional native component is absent, the application gracefully degrades to pure Python equivalents with clear feedback.

---

## 2. High-Level Architecture Flow

```mermaid
flowchart TB
    subgraph UI_Layer["Presentation and Shell Layer - PySide6"]
        A["PremiumMainWindow"] --> B["Sidebar Navigation and Search: Ctrl+K"]
        A --> C["PageRegistry and Lazy Page Loader"]
        C --> D["139 Theme-Aware GUI Pages"]
        D --> E["WorkerRuntime / QThreadPool"]
    end

    subgraph Core_Engine["Cortex Unified Orchestration Engine"]
        E --> F["SmartScanner and Engine Service"]
        E --> G["System Tools Suite: 62 Modules"]
        E --> H["Analyzers and Cleaners: Residual Hunter, Shredder, S3-FIFO"]
        E --> I["Background Agent and Resource Tray Monitor"]
    end

    subgraph Nexus_VFS["Nexus Explorer VFS Engine"]
        E --> J["NexusCore Transport Protocol"]
        J --> K["Native C/Rust FFI Bridge"]
        J --> L["Pure Python Fallback Engine"]
        J --> M["USN Journal Scanner and MFT Traverser"]
        J --> N["PAR2 Error Correction and Reed-Solomon Codec"]
    end

    subgraph OS_Kernel["Windows NT Subsystem and Hardware"]
        G --> O["Win32 Kernel32 / Advapi32 APIs"]
        G --> P["NTFS and ReFS File Systems"]
        G --> Q["WMI / CIM Subsystem"]
        G --> R["Windows PowerShell Engine"]
    end
```

---

## 3. The `PageSpec` Contract

Pages are registered declaratively using `PageSpec` dataclasses in `cortex_unified.ui.premium.registry`:

```python
@dataclass(frozen=True, slots=True)
class PageSpec:
    id: str        # Unique identifier used for navigation routing
    title: str     # Display title in the header and search index
    icon: str      # Vector SVG filename from resources/icons/
    group: str     # Parent sidebar navigation group
    factory: str   # Lazy import string "module.path:ClassName"
```

Because `factory` is stored as a string, declaring 139 tools costs under **1 millisecond** at boot time. Modules are only imported when the user navigates to that specific page.
