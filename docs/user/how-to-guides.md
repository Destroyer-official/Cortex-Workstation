# 🛠️ How-To Guides & Real-World Recipes

Step-by-step practical recipes for getting the most out of Cortex Workstation's 139 tools and forensic engines.

---

## 🧹 1-Click Full System Cleanup

Quickly reclaim dozens of gigabytes of disk space safely:

1. Open Cortex Workstation and navigate to **Cleanup Hub** in the sidebar.
2. Select your desired scan categories:
   * **System Temp & Log Files**
   * **DirectX Shader Caches** (NVIDIA, AMD, Intel)
   * **Windows Delivery Optimization Cache**
   * **Browser Caches** (Chrome, Edge, Firefox, Brave)
3. Click **Scan Reclaimable Space**.
4. Review findings by category with estimated savings.
5. Click **Clean Selected** to safely recycle files.

> [!TIP]
> All deletions use the Windows Recycle Bin (`send2trash`) by default, so files can be easily recovered if needed.

---

## 🔍 Deduplication & Storage Reclaim

Find and eliminate redundant files with zero risk of false positives:

### Exact Duplicates (Byte-for-Byte & BLAKE3)
1. Navigate to **Duplicate Files Finder** under *Cleanup & Storage*.
2. Choose the directory to scan (e.g., `D:\Media` or `C:\Users\username\Downloads`).
3. Click **Scan**.
4. The engine uses a multi-tier pipeline: size filtering $\rightarrow$ header checks $\rightarrow$ full BLAKE3 cryptographic digest.
5. Select duplicate files to remove, keeping the original intact.

### Perceptual Photo Duplicates
1. Open **Similar & Duplicate Photos**.
2. Select an image gallery folder.
3. The engine computes perceptual hashes (dHash, pHash, aHash) to detect resized, recompressed, or cropped images.
4. Preview image pairs side-by-side with similarity percentages before deleting.

---

## 🔧 Windows Deep Repair & Optimization

Repair corrupted system components without reinstalling Windows:

### Component Store & DISM Health Restore
1. Navigate to **Windows Update & Component Store** under *Maintenance & Repair*.
2. Click **Analyze Component Store** to inspect cleanup viability.
3. If corruption is detected, click **Restore Component Health** to invoke the native DISM repair engine.
4. Run **System File Checker (SFC)** to verify and repair protected system binaries.

### DirectStorage & BypassIO Verification
1. Navigate to **DirectStorage Optimizer** under *System Performance*.
2. Click **Run Diagnostic**.
3. The tool verifies if your NVMe SSD, storage controller driver, and volume filter drivers support **BypassIO** for ultra-fast GPU asset streaming.

---

## 🔒 Multi-Pass Secure File Shredding

Permanently destroy sensitive data beyond recovery:

1. Open **File Shredder** under *Security & Sanitize*.
2. Add files or folders using drag-and-drop.
3. Choose your desired sanitization standard:
   * **NIST SP 800-88 Clear** (1 Pass - Recommended for SSDs)
   * **DoD 5220.22-M** (3 Passes)
   * **DoD 5220.22-M (ECE)** (7 Passes)
   * **Peter Gutmann** (35 Passes - HDD Only)
4. Confirm deletion to securely overwrite the sectors and wipe file metadata.
