# Cortex Cleaner — Quick Reference Cheat Sheet

---

## ⚡ 1. Top Keyboard Shortcuts

### Global & Window Navigation
| Shortcut | Action |
| :--- | :--- |
| `Ctrl+H` | Toggle Navigation Sidebar |
| `Ctrl+,` | Open Preferences & Settings |
| `F11` | Toggle Fullscreen Mode |
| `Alt+F4` | Close Window (or Minimize to System Tray) |

### Nexus File Manager
| Shortcut | Action |
| :--- | :--- |
| `Ctrl+T` | Open New Tab |
| `Ctrl+W` | Close Current Tab |
| `Ctrl+B` | Toggle Dual-Pane View |
| `Ctrl+N` | Create New Folder |
| `Ctrl+Shift+N` | Create New File |
| `Ctrl+Shift+R` | Bulk Rename Selected Files |
| `Ctrl+F` / `F3` | Focus Instant Search Box |
| `Ctrl+1` | Switch to Details Table View |
| `Ctrl+2` | Switch to Icon Grid View |
| `Ctrl+C` | Copy Selection to Staging Shelf |
| `Ctrl+X` | Cut Selection to Staging Shelf |
| `Ctrl+V` | Paste Staged Items to Active Directory |
| `Ctrl+Z` | Undo Last File Operation |
| `Ctrl+Y` | Redo Last File Operation |
| `F2` | Inline Rename Active File |
| `F5` | Refresh Directory |
| `Space` | Quick Look File Preview |
| `Alt+Up` | Go Up to Parent Folder |

---

## 🗂️ 2. Staging Shelf & Transfer Workflow

```
[ Step 1: Accumulate ] ──> Select files across any folders & press Ctrl+C or Ctrl+X
                            (Items dock in the bottom-right Staging Shelf)
                                      │
[ Step 2: Navigate ]   ──> Freely switch tabs or browse to target folders
                                      │
[ Step 3: Paste ]      ──> Click "Paste N Items to [Folder]" or press Ctrl+V
                           (Or drag items directly out of the shelf)
                                      │
[ Step 4: Monitor ]    ──> Telemetry dock displays live speed, ETA, and progress
                           (With inline Pause / Cancel controls)
```

---

## 📦 3. System Cache & Tool Quick Actions

### Cleaning Package Manager Caches
1. Select **Package Manager Caches** from sidebar.
2. Click **Detect Package Managers** (finds pip, npm, yarn, conda, etc.).
3. Click **Scan for Caches** to compute cache sizes.
4. Toggle **Dry Run** to preview before final deletion.
5. Click **Clean Up**.

### Duplicate File Elimination
1. Select **Duplicate Finder** from sidebar.
2. Add target drives or folders to scan.
3. Fast 3-phase engine identifies bit-for-bit exact duplicates.
4. Review groups, select older duplicates or use auto-mark, and click **Remove Duplicates**.

---

## 🛡️ 4. Safety Guards & Protections

- **PathGuard System**: Critical system directories (`C:\Windows`, `C:\Program Files`, System Volume Information) are locked and protected against accidental removal.
- **Transaction Journaling**: All file creations, renames, copies, and moves are logged in `nexus_undo.py` for multi-level undo/redo.
- **Windows Read-Only Auto-Clear**: Automatically clears `FILE_ATTRIBUTE_READONLY` flags and retries safely if temporary indexer locks occur.
