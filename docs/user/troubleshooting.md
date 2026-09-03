# 🆘 Troubleshooting & Frequently Asked Questions

Common failure modes and troubleshooting solutions for Cortex Workstation.

---

## ⚠️ Common Issues & Solutions

### 1. "Access Denied" or Operation Blocked
* **Cause:** Modifying protected system areas (e.g., Windows Component Store, registry root hives, service controllers) requires administrator rights.
* **Fix:** Close Cortex Workstation, right-click `run_gui.py` or your launcher shortcut, and select **"Run as administrator"**.

### 2. Winget Times Out on Software Updater Page
* **Cause:** The official Microsoft Winget catalog update may be experiencing network latency or a background package lock.
* **Fix:** Open PowerShell as administrator and run `winget update`. Once completed, click **Refresh** inside Cortex Workstation.

### 3. Missing Vector Icons or Rendering Glitches
* **Cause:** Running on older Windows builds with missing DirectWrite fonts or outdated Qt dependencies.
* **Fix:** Ensure PySide6 is updated (`pip install --upgrade PySide6`). Cortex Workstation ships standalone vector SVG icons that render independently of system fonts.

### 4. DirectStorage BypassIO Shows "Blocked by Filter"
* **Cause:** A legacy third-party antivirus or filesystem filter driver is attached to the target volume.
* **Fix:** Review the filter driver list displayed in the DirectStorage Optimizer diagnostic table. Update the respective driver or configure bypass exceptions.
