# 🚀 START HERE - Phase 1 Implementation Guide

## What You Need to Do (Step by Step)

Follow these steps **in order**. Each step must complete successfully before moving to the next.

---

## ✅ Step 1: Copy pyproject.toml to Project Root

**What:** Create the package configuration file  
**Why:** Fixes import chaos and enables proper installation  
**Time:** 2 minutes

### Commands:

```cmd
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner

copy src\cortex_unified\pyproject.toml.template pyproject.toml
```

### Verify:
- File `pyproject.toml` exists in project root
- File contains `[project]` section with `name = "cortex-cleaner"`

---

## ✅ Step 2: Install Core Dependencies

**What:** Install the new foundation libraries  
**Why:** Required for config, database, and logging  
**Time:** 5 minutes

### Commands:

```cmd
pip install pydantic pydantic-settings sqlalchemy structlog pytest hypothesis
```

### Verify:
```cmd
python -c "import pydantic; import sqlalchemy; import structlog; print('OK')"
```

Expected output: `OK`

---

## ✅ Step 3: Install Package in Editable Mode

**What:** Install Cortex Cleaner as a package  
**Why:** Makes imports work correctly  
**Time:** 2 minutes

### Commands:

```cmd
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner

pip install -e .
```

### Verify:
```cmd
cortex-cleaner --help
```

Expected: Help text appears (or error about missing CLI, which is OK for now)

---

## ✅ Step 4: Test New Components

**What:** Verify all new components work  
**Why:** Catch issues early  
**Time:** 3 minutes

### Commands:

```cmd
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner\src\cortex_unified

python setup_phase1.py
```

### Expected Output:
```
✓ Python version: 3.10+
✓ pydantic is installed
✓ sqlalchemy is installed
✓ structlog is installed
✓ Config created successfully
✓ Database created successfully
✓ Logging configured successfully
✓ Phase 1 setup complete!
```

---

## ✅ Step 5: Run Tests

**What:** Run the test suite  
**Why:** Ensure everything works correctly  
**Time:** 2 minutes

### Commands:

```cmd
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner

# Create tests directory if it doesn't exist
mkdir tests
mkdir tests\unit

# Copy test file
copy src\cortex_unified\tests\test_config_v2.py tests\unit\

# Run tests
pytest tests\unit\test_config_v2.py -v
```

### Expected Output:
```
tests/unit/test_config_v2.py::TestScanConfig::test_default_values PASSED
tests/unit/test_config_v2.py::TestScanConfig::test_min_age_validation PASSED
...
======================== X passed in Y.YYs ========================
```

---

## ✅ Step 6: Update Existing Code (One File at a Time)

**What:** Migrate existing code to use new components  
**Why:** Get benefits of new infrastructure  
**Time:** 30-60 minutes

### 6a. Update __main__.py

**File:** `src\cortex_unified\__main__.py`

**Change:**
```python
# Add at the top
from cortex_unified.core.config_v2 import Config
from cortex_unified.core.logging_setup import configure_logging, get_logger

def main():
    # Add these lines at the start
    configure_logging(log_level="INFO", json_output=False)
    log = get_logger(__name__)
    log.info("cortex_cleaner_started", version="1.0.0")
    
    # Rest of your code...
```

**Test:**
```cmd
python src\cortex_unified\__main__.py
```

### 6b. Update Scanner

**File:** `src\cortex_unified\core\scanner.py`

**Change imports:**
```python
# OLD
from cortex_unified.core.config import Config
import logging
logger = logging.getLogger(__name__)

# NEW
from cortex_unified.core.config_v2 import Config
from cortex_unified.core.logging_setup import get_logger
log = get_logger(__name__)
```

**Change logging calls:**
```python
# OLD
logger.info(f"Scanning {path}")

# NEW
log.info("scan_started", path=str(path), scan_type="empty_files")
```

**Test:**
```cmd
python -c "from cortex_unified.core.scanner import Scanner; print('OK')"
```

### 6c. Add Database Tracking to Scanner

**File:** `src\cortex_unified\core\scanner.py`

**Add to __init__:**
```python
from cortex_unified.core.database import get_database

class Scanner:
    def __init__(self, config: Config = None, root_path: str = "."):
        # ... existing code ...
        self.db = get_database()
        self.current_scan_id = None
```

**Update scan method:**
```python
def scan(self, threads: int = 0):
    # Create scan record
    scan_run = self.db.create_scan_run(
        scan_type="empty_files",
        root_path=str(self.root_path)
    )
    self.current_scan_id = scan_run.id
    
    try:
        # ... existing scan logic ...
        
        # Update database with results
        self.db.update_scan_run(
            run_id=self.current_scan_id,
            status="completed",
            items_found=len(self.empty_files) + len(self.empty_dirs),
            bytes_found=sum(f.stat().st_size for f in self.empty_files if f.exists())
        )
        
        return self.empty_files, self.empty_dirs
        
    except Exception as e:
        # Record failure
        self.db.update_scan_run(
            run_id=self.current_scan_id,
            status="failed",
            error_message=str(e)
        )
        raise
```

**Test:**
```cmd
python -c "from cortex_unified.core.scanner import Scanner; s = Scanner(); print('OK')"
```

---

## ✅ Step 7: Verify Everything Works

**What:** Run a complete scan and verify database records  
**Why:** Ensure end-to-end functionality  
**Time:** 5 minutes

### Commands:

```cmd
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner

# Run a test scan
python -c "
from cortex_unified.core.scanner import Scanner
from cortex_unified.core.config_v2 import Config
from cortex_unified.core.database import get_database

config = Config()
scanner = Scanner(config, root_path='.')
files, dirs = scanner.scan()

print(f'Found {len(files)} empty files, {len(dirs)} empty dirs')

# Check database
db = get_database()
history = db.get_scan_history(limit=1)
print(f'Database has {len(history)} scan records')
"
```

### Expected Output:
```
Found X empty files, Y empty dirs
Database has 1 scan records
```

---

## ✅ Step 8: Check Database File

**What:** Verify database was created  
**Why:** Confirm persistence is working  
**Time:** 1 minute

### Commands:

```cmd
# Check if database file exists
dir %USERPROFILE%\.cortex_cleaner\history.db
```

### Expected Output:
```
... history.db
```

---

## 🎉 Success Criteria

You've completed Phase 1 when:

- [x] pyproject.toml exists in project root
- [x] All dependencies installed
- [x] Package installs with `pip install -e .`
- [x] All tests pass
- [x] Scanner uses new config
- [x] Scanner uses structured logging
- [x] Scanner saves to database
- [x] Database file exists at `~/.cortex_cleaner/history.db`

---

## 🚨 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'pydantic'"

**Solution:**
```cmd
pip install pydantic pydantic-settings
```

### Problem: "ImportError: cannot import name 'Config' from 'cortex_unified.core.config_v2'"

**Solution:**
```cmd
# Make sure you're in the right directory
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner

# Reinstall in editable mode
pip install -e .
```

### Problem: "pytest: command not found"

**Solution:**
```cmd
pip install pytest pytest-cov hypothesis
```

### Problem: Database file not created

**Solution:**
```cmd
# Check if directory exists
mkdir %USERPROFILE%\.cortex_cleaner

# Run a test scan
python -c "from cortex_unified.core.database import get_database; db = get_database(); print('DB created')"
```

### Problem: Tests fail with import errors

**Solution:**
```cmd
# Make sure package is installed
pip install -e .

# Make sure you're running from project root
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner
pytest tests\unit\test_config_v2.py -v
```

---

## 📚 Reference Documents

- **PHASE1_IMPLEMENTATION_CHECKLIST.md** - Detailed task list
- **UPGRADE_SUMMARY.md** - What was done and why
- **MIGRATION_GUIDE.md** - How to migrate existing code
- **IMPLEMENTATION_ROADMAP.md** - Full 8-phase plan

---

## 🎯 Next Steps After Phase 1

Once all checkboxes above are checked:

1. **Commit your changes** to git
2. **Review** `PHASE1_IMPLEMENTATION_CHECKLIST.md` for any missed items
3. **Read** Phase 2 in `IMPLEMENTATION_ROADMAP.md`
4. **Begin** Phase 2: Performance improvements

---

## 💡 Quick Commands Reference

```cmd
# Install dependencies
pip install pydantic pydantic-settings sqlalchemy structlog pytest hypothesis

# Install package
pip install -e .

# Run setup script
python src\cortex_unified\setup_phase1.py

# Run tests
pytest tests\unit\test_config_v2.py -v

# Check database
dir %USERPROFILE%\.cortex_cleaner\history.db

# Test imports
python -c "from cortex_unified.core.config_v2 import Config; print('OK')"
python -c "from cortex_unified.core.database import get_database; print('OK')"
python -c "from cortex_unified.core.logging_setup import get_logger; print('OK')"
```

---

**Ready? Start with Step 1!** 🚀
