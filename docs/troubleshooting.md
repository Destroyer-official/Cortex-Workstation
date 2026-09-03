# Cortex Cleaner Troubleshooting Guide

---

## 🛠️ Common Issues and Solutions

### 1. Windows File Permissions & Deletion Errors

#### `[WinError 5] Access is denied`
- **Cause**: The file has the Windows Read-Only attribute (`FILE_ATTRIBUTE_READONLY`), is locked by Windows Search indexer, or is held open by a media thumbnailer/preview process.
- **Solution**:
  - Cortex Cleaner automatically resets Windows file attributes (`FILE_ATTRIBUTE_NORMAL`) and applies an exponential backoff retry loop.
  - If a file is locked by an external application (e.g. video editor, media player), close that application and retry.
  - To permanently delete stubborn locked items, use **File Shredder** in the Privacy & Defense section.

---

### 2. Nexus File Manager & UI Interactions

#### Drag & Drop Shows Blocked Icon (`🚫`)
- **Cause**: Dragging into an uninitialized view or third-party dropped MIME format.
- **Solution**:
  - Drops are accepted anywhere in the file table, icon grid, empty folder view ("This folder is empty"), and sidebar tree.
  - Use `Ctrl+C` / `Ctrl+X` into the **Staging Shelf** and click **Paste N items** as an alternative to long-distance dragging.

#### Native CLI / FFI Warnings on Launch
- **Message**: `WARNING: CLI not found: nexus-cli.exe... using CLI / Python fallback`
- **Explanation**: This is normal in standard Python mode. Cortex Cleaner includes a high-speed pure Python fallback engine that performs all directory scanning, file transfers, BLAKE3 hashing, and undo/redo operations without needing external compiled binaries.
- **Building Rust Binaries (Optional)**:
  ```bash
  cd src/NexusExplorer
  cargo build --release
  ```

---

### 3. System Tray & Background Operation

#### Window Closes When Clicking `✕`
- **Solution**: By default, Cortex Cleaner minimizes to the system tray to keep background monitors and scheduled cleanup active. To completely exit, right-click the system tray icon and select **Exit Cortex Cleaner**, or disable "Close to Tray" in Settings (`Ctrl+,`).

---

### 4. Display & Scaling Issues

#### Blurry Text on High-DPI Displays
- Cortex Cleaner uses Qt6 native Per-Monitor V2 DPI scaling. Ensure Windows display scaling is set to standard presets (100%, 125%, 150%, 200%).
- If running in headless/remote environments, unset `QT_SCALE_FACTOR` and rely on auto-scaling.