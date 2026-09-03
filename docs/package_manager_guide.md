# Package Manager Cache Cleaner - User Guide

## What Was Fixed

The Package Manager Cache feature now:
✓ **Has folder selection** - Choose which folders to clean
✓ **Is selective** - Only cleans Python caches, not project files  
✓ **Is safe** - Limits scanning depth to prevent aggressive deletion in deep projects
✓ **Shows previews** - Dry-run mode lets you see what will be deleted
✓ **Preserves source** - Won't delete your .py files, only cache (.pyc, __pycache__, etc.)

## Two Operating Modes

### Mode 1: Clean Package Manager Caches (Global)

**Best for:** Cleaning system package caches (pip, npm, conda, etc.)

**Steps:**
1. Open Cortex Cleaner
2. Go to Package Manager Caches tab
3. Click "Detect Package Managers" to find available package managers
4. Make sure the tab shows "Package Managers"
5. Click "Scan" 
6. Review the detected caches in the results table
7. (Optional) Uncheck "Dry Run" if you're confident
8. Click "Clean Up"

**Example:**
```
Found 4 cache locations: 2.3 GB total
- pip cache: 1.2 GB
- npm cache: 800 MB  
- conda cache: 300 MB
```

---

### Mode 2: Clean Project Folder Caches (Local)

**Best for:** Cleaning cache files in large Python projects

**Steps:**
1. Open Cortex Cleaner
2. Go to Package Manager Caches → "Project Folders" tab
3. Click "Add Folder"
4. Select a project directory (e.g., `C:\Users\shant\Documents\my_project`)
5. (Optional) Add more folders to scan
6. Make sure "Scan for Python caches" is checked
7. Click "Scan"
8. Review found caches (only __pycache__, .egg-info, etc. shown)
9. Review the results table showing:
   - **Name**: Cache type (e.g., __pycache__)
   - **Type**: Cache category
   - **Path**: Exact location
   - **Size**: How much space it uses
   - **Files**: Number of cache files
10. (Optional) Uncheck "Dry Run" for actual deletion
11. Click "Clean Up"

**Example:**
```
Selected: C:\projects\my_big_app

Scan Results - Found 6 cache locations: 850 MB total
- __pycache__ (my_big_app/src): 450 MB
- __pycache__ (my_big_app/tests): 180 MB
- .egg-info: 120 MB
- .pytest_cache: 75 MB
- .mypy_cache: 15 MB
- .tox: 10 MB
```

## Important Settings

### "Keep cache files newer than: X days"
- **Default:** 7 days
- **Purpose:** Don't delete recently cached files
- **Use case:** If you're actively developing, keeping recent caches can speed up rebuilds
- **Recommendation:** Keep at 7-14 days for development, increase to 30 for cleanup

### "Dry Run (Preview Only)" 
- **Default:** ✓ Checked
- **Purpose:** Shows what would be deleted WITHOUT actually deleting it
- **Workflow:** Always run with this checked first, review results, then uncheck and re-run
- **Safety:** Highly recommended to always preview first

### "Scan for Python caches"
- **Default:** ✓ Checked (in Project Folders mode)
- **Purpose:** Looks for Python-specific cache files
- **Targets:** __pycache__, .egg-info, .dist-info, .pyc, .pyo, .pytest_cache, .mypy_cache, etc.

## Safety Features Built In

1. **Depth Limiting (3 levels)**
   - Won't scan through massive nested structures
   - Protects deeply nested vendor dependencies
   - Prevents performance degradation on large projects

2. **Pattern Matching**
   - Only targets known cache patterns
   - Won't delete .py source files
   - Won't delete configuration files

3. **Dry-Run Preview**
   - See exactly what will be deleted
   - Verify sizes and locations
   - Safe to run multiple times

4. **Automatic Backups**
   - Package lists backed up before cleanup
   - Stored in: `~/.cortex_cleaner_backups/`
   - Can help recovery if issues occur

5. **Error Handling**
   - Continues even if individual files fail to delete
   - Reports detailed error messages
   - No data loss from permission errors

## Common Scenarios

### Scenario 1: Reduce Large Project Size

**Problem:** Your Python project folder is 5 GB, mostly cache files

**Solution:**
1. Go to "Project Folders" tab
2. Click "Add Folder", select project root
3. Click "Scan"
4. See results: __pycache__ = 2.5 GB, .egg-info = 800 MB, etc.
5. Keep "Dry Run" checked, click "Clean Up"
6. Review what would be deleted: safe?
7. Uncheck "Dry Run", click "Clean Up" again
8. Freed 3.3 GB!

---

### Scenario 2: Clean All Python Development Caches

**Problem:** Multiple Python projects, all have stale caches

**Solution:**
1. Go to "Project Folders" tab
2. Add Folder → select `C:\projects`
3. Add Folder → select `C:\dev`
4. Add Folder → select `C:\work`
5. Click "Scan"
6. Reviews all __pycache__ folders across all 3 locations
7. Click "Clean Up" with dry-run to preview
8. Uncheck dry-run and run actual cleanup

---

### Scenario 3: Clean Just Package Manager Cache

**Problem:** pip/npm/conda caches are taking up space

**Solution:**
1. Go to "Package Managers" tab (default)
2. Click "Detect Package Managers"
3. Click "Scan"
4. See pip cache (1.2 GB), npm cache (500 MB), etc.
5. Uncheck "Dry Run" (you trust the official cache dirs)
6. Click "Clean Up"

---

### Scenario 4: Deep Project with Vendor Folder

**Problem:** Project has `vendor/` folder with 20+ nested levels

**Solution:** 
- **OLD BEHAVIOR:** Would scan all 20 levels, might delete files incorrectly
- **NEW BEHAVIOR:** Stops at 3 levels deep automatically
- Only caches in first 3 levels are cleaned
- Deep vendor code is protected

---

## Tips & Best Practices

✓ **Always do a dry-run first**
  - Click "Clean Up" with "Dry Run" checked
  - Review what would be deleted
  - Then uncheck and run for real

✓ **Start with small projects**
  - Add one folder at a time
  - Review results carefully
  - Then add more folders

✓ **Keep recent caches (7-14 days)**
  - Active development needs recent cache
  - Clean builds might be slower without it
  - Balance between space and speed

✓ **Clean large projects individually**
  - Don't add 10 projects at once
  - Process one or two at a time
  - Monitor available disk space after each

✓ **Schedule regular cleanups**
  - Run monthly or quarterly
  - Prevents cache buildup
  - Keeps projects responsive

## Troubleshooting

### "Scan found 0 cache locations"
- **Cause:** No caches exist in selected folder
- **Solution:** Project might be new or caches already cleaned
- **Action:** Select a different folder with active cache

### "Clean Up is grayed out after Scan"
- **Cause:** No valid caches were found
- **Solution:** Check folder selection or patterns
- **Action:** Manually verify folder contains __pycache__ or .egg-info

### "Dry Run shows large numbers but I trust these folders"
- **Cause:** Script is correctly reporting cache sizes
- **Solution:** Uncheck "Dry Run" and run actual cleanup
- **Safety:** Your source files are protected by pattern matching

### "Clean Up deleted source files!"
- **Report as bug** (this should not happen with current version)
- **Immediate fix:** Restore from backup
  - Backups stored in `~/.cortex_cleaner_backups/`
  - Or restore from version control

## Performance Impact

**Before Cleanup:**
- Project loads slowly (cache invalidation)
- IDE rebuild takes 2-5 minutes
- Disk usage: 5 GB

**After Cleanup (typical):**
- First load slightly slower (rebuilding cache)
- Subsequent loads: same speed
- IDE rebuild: first time ~3-5 min, then cached
- Disk usage: 1-2 GB
- Long-term: same or faster (fresh cache)

## FAQ

**Q: Will this break my project?**
A: No. Caches are always rebuilable. The cleaner only removes cache files (like .pyc), not source code.

**Q: Do I need to reinstall packages after cleanup?**
A: No. The cleaner only removes cache, not packages themselves. Package managers still know what's installed.

**Q: Should I clean before or after git push?**
A: Either time is fine. Caches are typically in .gitignore, so they're not in git anyway.

**Q: Why keep caches at all? Why not clean everything?**
A: Caches speed up rebuilds and imports. Cleaning old caches but keeping recent ones balances space savings with performance.

**Q: Can I exclude specific folders?**
A: Currently no, but you can manually select which folders to add. Exclusion list may be added in future versions.

**Q: What if cleanup is interrupted?**
A: The cleaner will report what was successfully deleted and what failed. Re-run if needed. Partial cleanups are safe.

## Version History

**Current Version**: With folder selection and selective cleaning
- ✓ Folder selection dialog
- ✓ Python cache pattern matching
- ✓ Depth limiting (3 levels)
- ✓ Dry-run preview mode
- ✓ Package backup before cleanup

**Previous Version**: No folder selection, aggressive deletion
- ✗ No folder choice (all caches deleted)
- ✗ No pattern selectivity
- ✗ Would traverse entire project recursively
- ✗ Risk of deleting files in deep nested projects
