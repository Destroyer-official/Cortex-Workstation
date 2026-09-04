# 🆘 Troubleshooting & Frequently Asked Questions

Common failure modes, diagnostics, and troubleshooting solutions for Cortex Workstation.

---

## 🛠️ Common Issues & Solutions

### 1. "Access Denied" or Operation Blocked (`[WinError 5]`)
* **Cause:** Modifying protected system areas (e.g., Windows Component Store, registry root hives, service controllers) requires administrator rights. Additionally, files with the Windows Read-Only attribute (`FILE_ATTRIBUTE_READONLY`) or files held open by Windows Search indexer or media thumbnailers can trigger access errors.
* **Fix:** 
  - Run Cortex Workstation as administrator (right-click the executable or shortcut and choose **"Run as administrator"**).
  - Cortex Workstation automatically resets Windows file attributes (`FILE_ATTRIBUTE_NORMAL`) and applies an exponential backoff retry loop.
  - If a file is locked by a background process, use the **Process Restart Manager File Unlocker** (Files & Explorer section) to safely release handles without rebooting.

### 2. Winget Times Out on Software Updater Page
* **Cause:** The official Microsoft Winget catalog update may be experiencing network latency or a background package lock.
* **Fix:** Open PowerShell as administrator and run `winget update`. Once completed, click **Refresh** inside Cortex Workstation.

### 3. Missing Vector Icons or Rendering Glitches
* **Cause:** Running on older Windows builds with missing DirectWrite fonts or outdated Qt dependencies.
* **Fix:** Ensure PySide6 is updated (`pip install --upgrade PySide6`). Cortex Workstation ships standalone vector SVG icons that render independently of system fonts.

### 4. DirectStorage BypassIO Shows "Blocked by Filter"
* **Cause:** A legacy third-party antivirus or filesystem filter driver is attached to the target volume.
* **Fix:** Review the filter driver list displayed in the DirectStorage Optimizer diagnostic table. Update the respective driver or configure bypass exceptions.

### 5. Native CLI / FFI Warnings on Launch
* **Message:** `WARNING: CLI not found: nexus-cli.exe... using CLI / Python fallback`
* **Explanation:** This is standard and expected in pure Python environments. Cortex Workstation includes a high-speed Python fallback engine that performs all directory scanning, file transfers, BLAKE3 hashing, and undo/redo operations with full functionality.

### 6. Drag & Drop Shows Blocked Icon (`🚫`) in Nexus Explorer
* **Cause:** Dragging into an uninitialized view or unrecognized third-party MIME format.
* **Fix:** Drops are accepted in the file table, icon grid, empty folder view, and sidebar tree. Use `Ctrl+C` / `Ctrl+X` into the **Staging Shelf** and click **Paste N items** as an alternative to long-distance mouse dragging.
