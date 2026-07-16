# Cortex Cleaner - Quick Reference Card

**Last Updated:** May 13, 2026  
**Version:** Pre-Production (Fixes Required)

---

## 🚨 Critical Issues - Fix IMMEDIATELY

```bash
# Apply all critical fixes automatically
python apply_critical_fixes.py

# Or apply manually (see IMPLEMENTATION_PLAN_V2.md)
```

### Top 3 Blockers
1. **Keyring crash** - `performance/multi_drive_scanner.py:9`
2. **Path traversal** - `analyzers/file_shredder.py`, `core/deleter.py`
3. **Slow MD5 hashing** - `analyzers/duplicate_finder.py`

---

## 📁 Project Structure

```
cortex_unified/
├── analyzers/          # 15 file analyzers
│   ├── duplicate_finder.py      ⚠️ MD5 → xxHash
│   ├── privacy_cleaner.py       ⚠️ Windows-only
│   ├── file_shredder.py         🔴 No validation
│   └── ...
├── core/               # Core functionality
│   ├── scanner.py               🔴 Recursion risk
│   ├── deleter.py               🔴 No validation
│   ├── config.py                ⚠️ Use config_v2.py
│   ├── config_v2.py             ✅ NEW - Use this!
│   ├── database.py              ✅ NEW
│   └── logging_setup.py         ✅ NEW
├── system_tools/       # Windows system tools
│   ├── registry_cleaner.py      ⚠️ No rollback
│   └── ...
├── performance/        # Performance features
│   ├── multi_drive_scanner.py   🔴 Keyring crash
│   └── resource_monitor.py      ✅ Good
├── cli/                # Command-line interface
├── ui/                 # GUI (25+ tabs)
└── tests/              ❌ EMPTY - Add tests!
```

**Legend:** ✅ Good | ⚠️ Needs work | 🔴 Critical issue

---

## 🔧 Common Tasks

### Run the Application
```bash
# CLI mode
python -m cortex_unified.cli.cli --help
python -m cortex_unified.cli.cli clean-empty --dry-run .

# GUI mode (if available)
python -m cortex_unified
```

### Find Duplicates
```bash
python -m cortex_unified.cli.cli find-duplicates /path/to/scan
python -m cortex_unified.cli.cli find-duplicates --strategy keep_newest .
```

### Clean Privacy Data
```bash
python -m cortex_unified.cli.cli clean-privacy --scan-only
python -m cortex_unified.cli.cli clean-privacy --clean
```

### Analyze Disk Usage
```bash
python -m cortex_unified.cli.cli analyze-disk .
python -m cortex_unified.cli.cli analyze-disk --export-treemap tree.html
```

---

## 🐛 Known Issues & Workarounds

### Issue: Keyring Import Crash
**Symptom:** `ModuleNotFoundError: No module named 'keyring'`  
**Workaround:** Install keyring: `pip install keyring`  
**Fix:** Apply critical fixes script

### Issue: Can Delete System Files
**Symptom:** Accidentally deleted important files  
**Workaround:** Always use `--dry-run` first  
**Fix:** Apply path validation from critical fixes

### Issue: Slow Duplicate Finding
**Symptom:** Takes hours to scan large directories  
**Workaround:** Use `--threads` option  
**Fix:** Switch to xxHash (10x faster)

### Issue: Crashes on Deep Directories
**Symptom:** `RecursionError: maximum recursion depth exceeded`  
**Workaround:** Scan shallower directories  
**Fix:** Refactor scanner to use iterative BFS

---

## 📊 Performance Tips

### Duplicate Finding
```bash
# Slow (MD5)
python -m cortex_unified.cli.cli find-duplicates .

# Fast (after fixes - xxHash)
python -m cortex_unified.cli.cli find-duplicates --threads 8 .

# Fastest (with exclusions)
python -m cortex_unified.cli.cli find-duplicates \
    --exclude-pattern "node_modules" \
    --exclude-pattern ".git" \
    --threads 8 .
```

### Scanning
```bash
# Use checkpoints for large scans
python -m cortex_unified.cli.cli clean-empty \
    --checkpoint-interval 1000 \
    /large/directory

# Resume from checkpoint
python -m cortex_unified.cli.cli clean-empty \
    --resume-from checkpoint_12345.json \
    /large/directory
```

### Resource Management
```bash
# Low priority (background)
python -m cortex_unified.cli.cli clean-empty \
    --cpu-priority low \
    --io-priority low \
    .

# High priority (foreground)
python -m cortex_unified.cli.cli clean-empty \
    --cpu-priority high \
    --threads 16 \
    .
```

---

## 🔒 Security Best Practices

### Always Use Dry Run First
```bash
# GOOD: Preview changes
python -m cortex_unified.cli.cli clean-empty --dry-run .
python -m cortex_unified.cli.cli find-duplicates --preview .

# BAD: Direct deletion
python -m cortex_unified.cli.cli clean-empty --delete .  # ⚠️ Dangerous!
```

### Validate Paths
```python
from cortex_unified.core.security import is_safe_path, is_system_file

# Check before any file operation
if is_safe_path(user_path) and not is_system_file(user_path):
    # Safe to proceed
    delete_file(user_path)
```

### Use Trash Instead of Permanent Delete
```bash
# GOOD: Recoverable
python -m cortex_unified.cli.cli clean-empty --trash .

# BAD: Permanent
python -m cortex_unified.cli.cli clean-empty --delete .
```

---

## 🧪 Testing

### Run Tests (after adding them)
```bash
# All tests
pytest tests/

# Specific module
pytest tests/test_duplicate_finder.py

# With coverage
pytest --cov=cortex_unified tests/
```

### Manual Testing Checklist
- [ ] Dry run mode works
- [ ] Trash mode works (files recoverable)
- [ ] Excludes system directories
- [ ] Handles permission errors gracefully
- [ ] Progress reporting works
- [ ] Checkpoint/resume works
- [ ] Doesn't crash on deep directories
- [ ] Cross-platform (test on Windows/macOS/Linux)

---

## 📚 Documentation

### For Users
- `README.md` - Installation and basic usage
- `QUICK_START.md` - Get started in 5 minutes
- `MIGRATION_GUIDE.md` - Upgrade from old version

### For Developers
- `DEEP_CODE_ANALYSIS.md` - Detailed code review
- `IMPLEMENTATION_PLAN_V2.md` - Step-by-step fixes
- `PRODUCTION_READINESS_SUMMARY.md` - Overall status
- `cortex_cleaner_upgrade_plan.jsx` - 8-phase roadmap

### For Operations
- `START_HERE.md` - Phase 1 implementation
- `PHASE1_IMPLEMENTATION_CHECKLIST.md` - Detailed tasks

---

## 🔍 Debugging

### Enable Verbose Logging
```bash
python -m cortex_unified.cli.cli clean-empty --verbose .
python -m cortex_unified.cli.cli clean-empty --log-file debug.log .
```

### Check Configuration
```python
from cortex_unified.core.config_v2 import CortexConfig

config = CortexConfig.from_yaml("config.yaml")
print(config.model_dump_json(indent=2))
```

### Monitor Resources
```python
from cortex_unified.performance.resource_monitor import ResourceMonitor

monitor = ResourceMonitor()
monitor.start_monitoring()
# ... run operations ...
print(monitor.get_metrics_summary())
monitor.stop_monitoring()
```

---

## 🚀 Quick Wins

### 1. Install xxHash (10x faster duplicate finding)
```bash
pip install xxhash
```

### 2. Use Configuration File
```yaml
# ~/.deepcleaner.yaml
exclude_patterns:
  - "*.log"
  - "node_modules"
  - ".git"
exclude_dirs:
  - "__pycache__"
  - ".venv"
min_age_days: 7
threads: 8
```

### 3. Create Aliases
```bash
# Add to ~/.bashrc or ~/.zshrc
alias cc-scan='python -m cortex_unified.cli.cli clean-empty --dry-run'
alias cc-clean='python -m cortex_unified.cli.cli clean-empty --trash'
alias cc-dupes='python -m cortex_unified.cli.cli find-duplicates'
```

---

## 📞 Getting Help

### Check Documentation
1. Read `PRODUCTION_READINESS_SUMMARY.md` for overview
2. Check `DEEP_CODE_ANALYSIS.md` for specific issues
3. Follow `IMPLEMENTATION_PLAN_V2.md` for fixes

### Common Questions

**Q: Why does it crash on startup?**  
A: Keyring dependency issue. Run `python apply_critical_fixes.py`

**Q: How do I make it faster?**  
A: Install xxhash, use `--threads`, exclude unnecessary directories

**Q: Is it safe to use?**  
A: Not yet - apply critical fixes first, always use `--dry-run`

**Q: Does it work on macOS/Linux?**  
A: Core features yes, but privacy cleaner is Windows-only (for now)

**Q: Where are deleted files?**  
A: Use `--trash` to send to recycle bin, or check manifest file

---

## 🎯 Next Steps

### Today
1. Run `python apply_critical_fixes.py`
2. Test with `--dry-run` mode
3. Review changes with `git diff`

### This Week
4. Complete Week 1 fixes (see IMPLEMENTATION_PLAN_V2.md)
5. Add basic tests
6. Set up CI/CD

### This Month
7. Complete all 5 weeks of fixes
8. Achieve 80% test coverage
9. Deploy to production

---

## 📋 Cheat Sheet

```bash
# Quick commands
python apply_critical_fixes.py              # Fix critical issues
python -m cortex_unified.cli.cli --help     # Show help
python -m cortex_unified.cli.cli clean-empty --dry-run .  # Safe scan
python -m cortex_unified.cli.cli find-duplicates .        # Find dupes

# With options
--dry-run           # Preview only (ALWAYS USE FIRST)
--trash             # Move to recycle bin (safer)
--delete            # Permanent delete (dangerous!)
--verbose           # Show detailed output
--threads N         # Use N threads
--exclude-pattern   # Skip matching files
--config FILE       # Use config file

# Performance
--cpu-priority low|normal|high
--io-priority low|normal|high
--checkpoint-interval N
--resume-from FILE
```

---

*Keep this card handy for quick reference!*
