# 🗂️ Nexus Native File Manager Guide

**Nexus Explorer** is Cortex Workstation's high-performance native Windows file manager and dual-pane VFS workstation. Built to overcome Windows Explorer limitations when navigating massive filesystems, it provides responsive directory navigation, multi-source staging, real-time transfer telemetry, smart project scaffolding, and deep safety guards.

---

## 🌟 Key Features & Capabilities

### 1. Windows 11 Inline Tab Bar
- **Title Bar Integration**: Folder tabs sit directly in the top window title bar, perfectly aligned horizontally with the window controls (Minimize `-`, Maximize `□`, Close `✕`).
- **Tab Management**:
  - Open new tabs with `Ctrl+T` or the `+` button.
  - Close tabs with `Ctrl+W` or the tab's `✕` button.
  - Middle-click any tab to close it instantly.
  - Drag and drop tabs to reorder.
  - Automatic session restoration preserves all open tabs across application launches.

### 2. Dual-Pane & Multi-View Explorer
- **Dual Pane (`Ctrl+B`)**: Split the workspace into two independent, side-by-side file explorers for instant drag-and-drop or cross-directory file operations.
- **View Modes (`Ctrl+1` / `Ctrl+2`)**:
  - **Details Table**: Clean tabular layout with filename, modification date, file type, and human-readable size.
  - **Icon Grid**: Dynamic responsive icon cards with smooth thumbnail scaling.
- **Interactive Breadcrumb Bar**: Click any ancestor segment in the path to jump directly, or click the edit icon to type custom paths.
- **Instant Search (`Ctrl+F` / `F3`)**: Real-time regex and glob filtering directly inside the active directory with highlighted matches.

### 3. Staging Shelf (Multi-Source Clipboard Dock)
- **Persistent Bottom Dock**: Positioned in the lower half of the right-hand Preview Pane.
- **Multi-Source Accumulation**: Copy (`Ctrl+C`) or Cut (`Ctrl+X`) files from different folders over multiple navigation steps. The Staging Shelf holds and tracks them all.
- **One-Click Paste**: Navigate to any folder and click **Paste N items to [Folder]** or press `Ctrl+V`.
- **Drag & Drop Out**: Drag items directly out of the shelf into any folder view or empty space.
- **Inline Controls**: Remove individual items or clear the entire staging queue with one click.

### 4. Embedded Live Transfer Dock
- **Non-Intrusive Workflow**: No blocking popup windows. Live transfer progress is seamlessly embedded right above the Staging Shelf.
- **Rich Real-Time Telemetry**:
  - **Kind Badge**: Vibrant badge (`COPY`, `MOVE`, `DELETE`, `DONE`, `ERROR`).
  - **Active File Indicator**: Displays current file and destination (e.g. `video.mp4 → backup`).
  - **Live Metrics**: Percentage (`45%`), transfer speed (`62.4 MB/s`), byte counter (`1.2 GB / 2.8 GB`), and ETA (`ETA 24s`).
  - **Inline Controls**: Quick `Pause` / `Resume` toggle and `Cancel` button.
  - **Auto-Dismiss**: Green completion notice auto-collapses cleanly after completion.

### 5. Advanced File Creation & Project Scaffolding
- **Nested Creation**: Create deep subdirectories or files in a single step (e.g. `my_project/src/components/ui/button.py`).
- **Batch Scaffolding**: Generate entire project trees from indented text or path lists.
- **Scaffold Presets**: 1-click generation of standard project layouts (Python Package, React/TypeScript, Rust Crate, Go Service, HTML/CSS Web).
- **Template Presets**: Create new files pre-populated with boilerplate (`.py`, `.json`, `.yaml`, `.md`, `.env`, `.sh`).

### 6. Power Tools & Resilience
- **Bulk Rename (`Ctrl+Shift+R`)**: Batch rename selected files using string replacement, prefix/suffix insertion, regex substitutions, or zero-padded numbered sequences with live preview.
- **Safe Undo / Redo (`Ctrl+Z` / `Ctrl+Y`)**: Complete transaction history for file renames, copies, moves, deletions, and folder creations.
- **File Previews**: Live image previews with pixel dimensions (`1920 × 1080 px`) and background text/source code viewer.
- **Windows Read-Only Protection**: Automatically strips Windows `FILE_ATTRIBUTE_READONLY` flags and handles permission retries (`[WinError 5] Access is denied`).

---

## ⌨️ Keyboard Shortcuts Reference

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+T` | Open New Tab |
| `Ctrl+W` | Close Current Tab |
| `Ctrl+N` | New Folder |
| `Ctrl+Shift+N` | New File |
| `Ctrl+Shift+R` | Bulk Rename Selected Files |
| `Ctrl+F` / `F3` | Focus Search Box |
| `Ctrl+B` | Toggle Dual Pane View |
| `Ctrl+H` | Toggle Sidebar Navigation |
| `Ctrl+1` | Details Table View |
| `Ctrl+2` | Large Icon View |
| `Ctrl+C` | Copy Selection to Staging Shelf |
| `Ctrl+X` | Cut Selection to Staging Shelf |
| `Ctrl+V` | Paste Staged Items to Active Directory |
| `Ctrl+Z` | Undo Last File Operation |
| `Ctrl+Y` | Redo Last File Operation |
| `Delete` | Move Selection to Trash |
| `Shift+Delete` | Permanently Delete Selection |
| `F2` | Inline Rename Active File |
| `F5` | Refresh Active Directory |
| `Alt+Left` | Navigate Back in History |
| `Alt+Right` | Navigate Forward in History |
| `Alt+Up` | Navigate Up to Parent Directory |
| `Space` | Quick Look File Preview |

---

## 🏗️ Architecture & Modules

```
src/NexusExplorer/
├── native/
│   ├── nexus_explorer.py          # Main Qt6 Explorer Widget, Tab Bar, Splitter & Views
│   ├── nexus_transfer_queue.py    # Multi-threaded Transfer Engine with Speed & ETA
│   ├── nexus_transfer_monitor.py  # Standalone Detailed Transfer History Dialog
│   ├── nexus_undo.py              # Undo/Redo Transaction Journal
│   ├── nexus_icons.py             # Fluent Design Vector SVG Icon Engine
│   └── nexus_core.py              # Native FFI & Python Fallback File Operations
└── tests/
    └── native/                    # Comprehensive PySide6 UI & Engine Test Suite
```
