# Package Manager Cache Tab - Visual Guide

## Main Interface Layout

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         PACKAGE MANAGER CACHES                            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  [📦 System Package Managers] [📁 Project Folders]                        ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                             ║
║  ┌─ TAB 1: SYSTEM PACKAGE MANAGERS ────────────────────────────────────┐  ║
║  │                                                                      │  ║
║  │  □ ✓ pip (Python)                                                   │  ║
║  │  □ ✓ npm (Node.js)                                                  │  ║
║  │  □   yarn (Node.js)                                                 │  ║
║  │  □   conda (Python)                                                 │  ║
║  │  □   System Package Manager                                         │  ║
║  │                                                                      │  ║
║  │  [🔍 Detect Available Package Managers]                             │  ║
║  │                                                                      │  ║
║  │  ✓ Detected: PIP, NPM                                               │  ║
║  │                                                                      │  ║
║  └──────────────────────────────────────────────────────────────────────┘  ║
║                                                                             ║
║  ┌─ CLEANUP OPTIONS ───────────────────────────────────────────────────┐   ║
║  │ Keep cache files newer than: [7] days                              │   ║
║  │ □ Include orphaned packages                                         │   ║
║  │ ☑ Dry Run (Preview Only - RECOMMENDED)                             │   ║
║  └──────────────────────────────────────────────────────────────────────┘   ║
║                                                                             ║
║  [🔍 Scan for Caches]  [🧹 Clean Selected Caches]                        ║
║                                                                             ║
║  ╔═══════════════════════════════════════════════════════════════════╗    ║
║  ║ ✓ Found 2 cache locations: 1.7 GB total                           ║    ║
║  ╠════════════════════════════════════════════════════════════════════╣    ║
║  ║ Name    │ Type                    │ Path              │ Size  │Files║    ║
║  ╠════════════════════════════════════════════════════════════════════╣    ║
║  ║ pip     │ package_manager_cache   │ ~/.cache/pip      │ 1.2GB │ 850 ║    ║
║  ║ npm     │ package_manager_cache   │ ~/.npm            │ 500MB │ 320 ║    ║
║  ╚════════════════════════════════════════════════════════════════════╝    ║
║                                                                             ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Tab 1: System Package Managers 📦

### What You See

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📦 SYSTEM PACKAGE MANAGERS TAB                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  System Package Managers to Clean                                        │
│  ┌────────────────────────────────────┐                                 │
│  │ ☑ ✓ pip (Python)                  │                                 │
│  │ ☑ ✓ npm (Node.js)                 │                                 │
│  │ ☐   yarn (Node.js)                │                                 │
│  │ ☐   conda (Python)                │                                 │
│  │ ☐   System Package Manager        │                                 │
│  └────────────────────────────────────┘                                 │
│                                                                           │
│  [🔍 Detect Available Package Managers]                                 │
│                                                                           │
│  ✓ Detected: PIP (26.2.1), NPM (9.8.1)                                  │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Steps to Use

1. **Detect** - Click "Detect Available Package Managers"
   - Shows which package managers are installed on your system
   - Status shows as green ✓ when detected

2. **Select** - Check which package managers to clean
   - pip and npm are checked by default (most common)
   - Uncheck system packages you don't want to clean

3. **Scan** - Click "Scan for Caches"
   - Finds cache directories for selected package managers
   - Shows progress bar during scanning

4. **Review** - Check results in table
   - Name: Package manager name
   - Size: Cache directory total size
   - Files: Number of cache files

5. **Preview** - Keep "Dry Run" checked (default)
   - Click "Clean Selected Caches"
   - Shows what would be deleted without actually deleting

6. **Cleanup** - Uncheck "Dry Run" and run again
   - Click "Clean Selected Caches" to actually delete
   - Files permanently removed

---

## Tab 2: Project Folders 📁

### What You See

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 📁 PROJECT FOLDERS TAB                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Select Folders to Scan                                                 │
│  ┌─────────────────────────────────────────┐                            │
│  │ Selected Folders:                       │                            │
│  │                                         │                            │
│  │ • C:\Users\user\my_project              │                            │
│  │ • D:\dev\ml-project                     │                            │
│  │                                         │                            │
│  └─────────────────────────────────────────┘                            │
│  [➕ Add Folder] [➖ Remove Selected] [🗑️ Clear All]                     │
│                                                                           │
│  Python Cache Types to Clean                                             │
│  ┌────────────────────────────────────┐                                 │
│  │ ☑ ✓ __pycache__ (Python bytecode)  │                                 │
│  │ ☑ ✓ .egg-info (Egg metadata)       │                                 │
│  │ ☑ ✓ .dist-info (Dist metadata)     │                                 │
│  │ ☑ ✓ .pytest_cache                  │                                 │
│  │ ☑ ✓ .mypy_cache                    │                                 │
│  └────────────────────────────────────┘                                 │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Steps to Use

1. **Add Folders** - Click "➕ Add Folder"
   - File browser opens
   - Select a project directory
   - Can add multiple folders

2. **Configure** - Select cache types to clean
   - All types checked by default
   - Uncheck types you want to skip
   - Most common: __pycache__ and .egg-info

3. **Scan** - Click "Scan for Caches"
   - Scans each selected folder (limited to 3 levels deep for safety)
   - Shows progress bar

4. **Review Results** - Check what was found
   - Shows cache locations with sizes and file counts
   - Only Python cache patterns shown (source code not included)

5. **Preview** - Keep "Dry Run" checked (default)
   - Click "Clean Selected Caches"
   - See exactly what would be deleted

6. **Cleanup** - Uncheck "Dry Run" and confirm
   - Click "Clean Selected Caches"
   - Caches permanently removed, source code preserved

---

## Common Options (Same for Both Tabs)

```
┌──────────────────────────────────────────────────────┐
│ CLEANUP OPTIONS                                      │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Keep cache files newer than:  [7] days              │
│                                                      │
│ □ Include orphaned packages                         │
│                                                      │
│ ☑ Dry Run (Preview Only - RECOMMENDED)              │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Settings Explained

- **Keep cache files newer than:** 7 days (default)
  - Cache files newer than this are preserved
  - Old caches (older than 7 days) are deleted
  - Change to higher value to preserve more recent caches

- **Include orphaned packages:** (For system caches only)
  - Unchecked by default
  - When checked: also removes unused packages

- **Dry Run (Preview Only):** ☑ CHECKED by default
  - Shows what will be deleted WITHOUT deleting
  - Highly recommended to always check first
  - Uncheck only after verifying results

---

## Results Table Format

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Scan Results                                                              │
├───────┬──────────────────────┬────────────────────┬──────────┬───────────┤
│ Name  │ Type                 │ Path               │ Size     │ Files     │
├───────┼──────────────────────┼────────────────────┼──────────┼───────────┤
│__pyc  │ python_cache         │ project/src/cache  │ 450 MB   │ 12,000    │
├───────┼──────────────────────┼────────────────────┼──────────┼───────────┤
│.egg   │ python_cache         │ venv/lib/egg-info  │ 280 MB   │ 1,500     │
├───────┼──────────────────────┼────────────────────┼──────────┼───────────┤
│pip    │ package_manager_cache│ ~/.cache/pip       │ 1.2 GB   │ 850       │
├───────┼──────────────────────┼────────────────────┼──────────┼───────────┤
│ ...   │ ...                  │ ...                │ ...      │ ...       │
└───────┴──────────────────────┴────────────────────┴──────────┴───────────┘

✓ Found 3 cache locations: 1.93 GB total
```

---

## Action Buttons

### 🔍 Scan for Caches
- **What it does:** Searches for caches
- **When to click:** After selecting folders or package managers
- **What happens:** Progress bar shows, results populate table
- **Time:** 1-30 seconds depending on folder size

### 🧹 Clean Selected Caches
- **What it does:** Deletes found caches
- **When to click:** After reviewing Scan results
- **What happens:** If "Dry Run" checked, shows preview. If unchecked, actually deletes.
- **Requires:** Scan must be run first

---

## Typical User Experience

### Scenario 1: Clean System Caches (5 minutes)

```
User opens Cortex Cleaner
        ↓
Goes to "Package Manager Caches"
        ↓
Clicks "Detect Available Package Managers" ← Sees: pip, npm detected ✓
        ↓
Clicks "Scan for Caches" ← Sees: pip 313.3 MB, npm 450 MB
        ↓
Checks "Dry Run" (default), clicks "Clean Selected Caches" ← Preview shown
        ↓
Unchecks "Dry Run", clicks "Clean Selected Caches" ← Caches deleted ✓
        ↓
Result: ~760 MB freed! ✓
```

### Scenario 2: Clean Project Caches (10 minutes)

```
User opens Cortex Cleaner
        ↓
Goes to "Package Manager Caches" → "Project Folders" tab
        ↓
Clicks "Add Folder" → Selects C:\Users\me\my_project
        ↓
Folder appears in list ✓
        ↓
Clicks "Scan for Caches" ← Sees: __pycache__ 850 MB, .egg-info 120 MB
        ↓
Checks "Dry Run" (default), clicks "Clean" ← Preview shows 970 MB
        ↓
Unchecks "Dry Run", clicks "Clean" ← Caches deleted ✓
        ↓
Result: 970 MB freed, project still works! ✓
```

---

## Safety Guardrails

### Before You See Deletion

```
1. "Dry Run" is CHECKED by default
   └─ Must manually UNCHECK to actually delete

2. Confirmation dialog asks:
   ┌──────────────────────────────────┐
   │ Are you sure you want to DELETE? │
   │                                  │
   │ [Cancel]  [Yes, Delete]          │
   └──────────────────────────────────┘

3. Source code is NEVER targeted
   └─ Only cache patterns selected

4. Depth limited to 3 levels
   └─ Won't scan deep nested structures
```

### Undo / Recovery

```
If files are accidentally deleted:

1. Backups created:
   Location: ~/.cortex_cleaner_backups/
   These are package list backups (can help verify what was installed)

2. Git recovery:
   If project is in git: git checkout (restores from history)

3. Recache:
   First project load will rebuild caches

But the key is: Dry Run mode prevents this in the first place!
```

---

## Color Meanings

- **🟢 Green** - Success, detected, working
- **🟠 Orange** - Warning, requires attention
- **🔵 Blue** - Information, clickable, important
- **🔴 Red** - Error, something failed

In UI:
- Green checkmarks (✓) = Detected, ready
- Blue buttons = Important actions
- Orange/bold text = Important warning (Dry Run)

---

## Keyboard Shortcuts

- **Enter** = Click focused button
- **Tab** = Move between controls
- **Space** = Check/uncheck checkboxes
- **Ctrl+A** = Select text in input fields

---

This visual guide shows exactly what users will see and how to use the new tab interface!
