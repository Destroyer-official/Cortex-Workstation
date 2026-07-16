# Phase 1: Foundation & Production Hardening - Implementation Checklist

## ✅ Task 1: Fix namespace & import chaos

### Current Problem
- Project imports from 'cortex_unified' but package isn't properly configured
- `__main__.py` calls `from cortex_unified.cli.cli import main` which breaks
- No proper package installation setup

### Solution: Create pyproject.toml

**Action:** Copy the content below into `d:\desktop\desktop\Main_projects\Cortex_Cleaner\pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cortex-cleaner"
version = "1.0.0"
description = "A comprehensive utility to find and remove unnecessary files and folders"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Cortex Cleaner Team", email = "team@deepcleaner.com"}
]

dependencies = [
    "PySide6>=6.6",
    "click>=8.1",
    "psutil>=5.9",
    "pyyaml>=6.0",
    "xxhash>=3.4",
    "send2trash>=1.8",
    "rich>=13.0",
    "sqlalchemy>=2.0",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
    "structlog>=23.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "hypothesis>=6.92.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[project.scripts]
cortex-cleaner = "cortex_unified.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["cortex_unified*"]
```

**Commands to run:**

```bash
# Navigate to project root
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner

# Install in editable mode
pip install -e .

# Verify installation
cortex-cleaner --help
```

**Verification:**
- [ ] pyproject.toml exists in project root
- [ ] `pip install -e .` completes without errors
- [ ] `cortex-cleaner` command is available
- [ ] Imports work: `python -c "from cortex_unified.core.config import Config; print('OK')"`

---

## ✅ Task 2: Replace YAML config with Pydantic v2 schema

### Current Problem
- Config uses raw YAML dict with no validation
- Bad values silently pass through
- No type checking

### Solution: Already created `core/config_v2.py`

**Action:** Update existing code to use new config

**Step 1: Test the new config**

```bash
cd src\cortex_unified
python -c "from core.config_v2 import Config; c = Config(); print('Config OK:', c.scan.min_age_days)"
```

**Step 2: Update __main__.py**

Open `src\cortex_unified\__main__.py` and change:

```python
# OLD
from cortex_unified.core.config import Config

# NEW
from cortex_unified.core.config_v2 import Config
```

**Step 3: Update Scanner**

Open `src\cortex_unified\core\scanner.py` and change:

```python
# OLD
from cortex_unified.core.config import Config

# NEW
from cortex_unified.core.config_v2 import Config
```

**Verification:**
- [ ] New config imports without errors
- [ ] Config validation works (try invalid value)
- [ ] Backward compatibility works (old property access)
- [ ] Environment variables work (set CORTEX_SCAN__MIN_AGE_DAYS=7)

---

## ✅ Task 3: Add SQLite persistence layer

### Current Problem
- Every scan result is lost when app closes
- No history tracking
- No restore capability

### Solution: Already created `core/database.py`

**Action:** Test the database

**Step 1: Test database creation**

```bash
cd src\cortex_unified
python core\database.py
```

Expected output: "✓ Database tests passed!"

**Step 2: Integrate into Scanner**

Create `src\cortex_unified\core\scanner_v2.py`:

```python
"""Enhanced scanner with database tracking."""

from pathlib import Path
from typing import List, Tuple
from cortex_unified.core.scanner import Scanner
from cortex_unified.core.database import get_database
from cortex_unified.core.config_v2 import Config

class ScannerV2(Scanner):
    """Scanner with database persistence."""
    
    def __init__(self, config: Config = None, root_path: str = "."):
        super().__init__(config, root_path)
        self.db = get_database()
        self.current_scan_id = None
    
    def scan(self, threads: int = 0) -> Tuple[List[Path], List[Path]]:
        """Scan with database tracking."""
        # Create scan record
        self.current_scan_id = self.db.create_scan_run(
            scan_type="empty_files",
            root_path=str(self.root_path)
        ).id
        
        try:
            # Run original scan
            empty_files, empty_dirs = super().scan(threads)
            
            # Update database
            self.db.update_scan_run(
                run_id=self.current_scan_id,
                status="completed",
                items_found=len(empty_files) + len(empty_dirs),
                bytes_found=sum(f.stat().st_size for f in empty_files if f.exists())
            )
            
            return empty_files, empty_dirs
            
        except Exception as e:
            # Record failure
            self.db.update_scan_run(
                run_id=self.current_scan_id,
                status="failed",
                error_message=str(e)
            )
            raise
```

**Verification:**
- [ ] Database file created at `~/.cortex_cleaner/history.db`
- [ ] Scan records are saved
- [ ] History can be queried
- [ ] Stats are calculated correctly

---

## ✅ Task 4: Structured logging with structlog

### Current Problem
- Scattered stdlib logging
- No structured output
- Can't ingest into monitoring systems

### Solution: Already created `core/logging_setup.py`

**Action:** Configure logging at startup

**Step 1: Test logging**

```bash
cd src\cortex_unified
python core\logging_setup.py
```

Expected output: Colored console logs with structured data

**Step 2: Update __main__.py**

Add at the top of `main()` function:

```python
from cortex_unified.core.logging_setup import configure_logging, get_logger

def main():
    # Configure logging first
    configure_logging(log_level="INFO", json_output=False)
    log = get_logger(__name__)
    
    log.info("cortex_cleaner_started", version="1.0.0")
    
    # ... rest of code
```

**Step 3: Update Scanner to use structured logging**

In `core/scanner.py`, replace:

```python
# OLD
import logging
logger = logging.getLogger(__name__)
logger.info(f"Scanning {path}")

# NEW
from cortex_unified.core.logging_setup import get_logger
log = get_logger(__name__)
log.info("scan_started", path=str(path), scan_type="empty_files")
```

**Verification:**
- [ ] Logs are structured (key=value format)
- [ ] JSON output works (set json_output=True)
- [ ] Sensitive data is censored
- [ ] Correlation IDs work

---

## ✅ Task 5: Complete test suite

### Current Problem
- Zero tests exist
- Any refactor can silently break things
- No confidence in changes

### Solution: Already created `tests/test_config_v2.py`

**Action:** Set up testing infrastructure

**Step 1: Install test dependencies**

```bash
pip install pytest pytest-cov hypothesis
```

**Step 2: Create test directory structure**

```bash
cd d:\desktop\desktop\Main_projects\Cortex_Cleaner
mkdir tests
mkdir tests\unit
mkdir tests\integration
mkdir tests\safety
```

**Step 3: Copy test file**

Copy `src\cortex_unified\tests\test_config_v2.py` to `tests\unit\test_config_v2.py`

**Step 4: Run tests**

```bash
pytest tests\unit\test_config_v2.py -v --cov=cortex_unified.core.config_v2
```

**Step 5: Create more tests**

Create `tests\unit\test_database.py`:

```python
"""Tests for database module."""

import pytest
from pathlib import Path
from cortex_unified.core.database import Database, ScanRun, DeletedItem

class TestDatabase:
    def setup_method(self):
        """Create in-memory database for testing."""
        self.db = Database()  # In-memory
    
    def test_create_scan_run(self):
        """Test creating a scan run."""
        scan = self.db.create_scan_run("test_scan", "/tmp")
        assert scan.id is not None
        assert scan.scan_type == "test_scan"
        assert scan.status == "running"
    
    def test_update_scan_run(self):
        """Test updating scan results."""
        scan = self.db.create_scan_run("test_scan", "/tmp")
        
        self.db.update_scan_run(
            run_id=scan.id,
            status="completed",
            items_found=10,
            bytes_found=1024
        )
        
        history = self.db.get_scan_history(limit=1)
        assert len(history) == 1
        assert history[0].status == "completed"
        assert history[0].items_found == 10
    
    def test_add_deleted_item(self):
        """Test recording deleted items."""
        scan = self.db.create_scan_run("test_scan", "/tmp")
        
        item = self.db.add_deleted_item(
            run_id=scan.id,
            path="/tmp/test.txt",
            size_bytes=100,
            backup_path="/backup/test.txt"
        )
        
        assert item.id is not None
        assert item.can_restore is True
        assert item.in_quarantine is True
    
    def test_get_restorable_items(self):
        """Test querying restorable items."""
        scan = self.db.create_scan_run("test_scan", "/tmp")
        
        self.db.add_deleted_item(
            run_id=scan.id,
            path="/tmp/test1.txt",
            size_bytes=100,
            backup_path="/backup/test1.txt"
        )
        
        restorable = self.db.get_restorable_items()
        assert len(restorable) == 1
        assert restorable[0].path == "/tmp/test1.txt"
```

**Verification:**
- [ ] All tests pass
- [ ] Coverage report generated
- [ ] Tests run in CI/CD (future)
- [ ] New code has tests

---

## ✅ Task 6: Privilege escalation handler

### Current Problem
- Operations fail with PermissionError
- No graceful handling of elevation
- User doesn't know why operations fail

### Solution: Create privilege handler

**Action:** Create `src\cortex_unified\core\privilege.py`

```python
"""Privilege escalation handler for Windows/Linux/macOS."""

import sys
import os
import subprocess
from enum import Enum
from typing import Optional

class PrivilegeLevel(Enum):
    """Current privilege level."""
    USER = "user"
    ELEVATED = "elevated"

def current_level() -> PrivilegeLevel:
    """
    Detect current privilege level.
    
    Returns:
        PrivilegeLevel.ELEVATED if running as admin/root
        PrivilegeLevel.USER otherwise
    """
    if sys.platform == "win32":
        try:
            import ctypes
            return (PrivilegeLevel.ELEVATED 
                    if ctypes.windll.shell32.IsUserAnAdmin() 
                    else PrivilegeLevel.USER)
        except Exception:
            return PrivilegeLevel.USER
    else:
        # Linux/macOS
        return (PrivilegeLevel.ELEVATED 
                if os.geteuid() == 0 
                else PrivilegeLevel.USER)

def request_elevation() -> bool:
    """
    Re-launch the application with elevated privileges.
    
    Returns:
        False if already elevated, True if elevation requested
    """
    if current_level() == PrivilegeLevel.ELEVATED:
        return False
    
    if sys.platform == "win32":
        # Windows: Use ShellExecuteW with "runas"
        import ctypes
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                " ".join(sys.argv), 
                None, 
                1  # SW_SHOWNORMAL
            )
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            return False
    
    elif sys.platform == "darwin":
        # macOS: Use osascript
        script = f'do shell script "{sys.executable} {" ".join(sys.argv)}" with administrator privileges'
        try:
            subprocess.Popen(["osascript", "-e", script])
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            return False
    
    else:
        # Linux: Use pkexec
        try:
            subprocess.Popen(["pkexec"] + [sys.executable] + sys.argv)
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            return False
    
    return True

def require_elevation(operation: str) -> None:
    """
    Check if elevated, request if not.
    
    Args:
        operation: Description of operation requiring elevation
    
    Raises:
        PermissionError: If not elevated and elevation fails
    """
    if current_level() != PrivilegeLevel.ELEVATED:
        print(f"Operation '{operation}' requires administrator privileges.")
        print("Requesting elevation...")
        
        if not request_elevation():
            raise PermissionError(
                f"Operation '{operation}' requires administrator privileges. "
                "Please run as administrator/root."
            )

# Example usage
if __name__ == "__main__":
    print(f"Current privilege level: {current_level().value}")
    
    if current_level() == PrivilegeLevel.USER:
        print("Running as regular user")
        print("To test elevation, uncomment the line below:")
        # request_elevation()
    else:
        print("Running with elevated privileges")
```

**Usage in code:**

```python
from cortex_unified.core.privilege import require_elevation, current_level

# Before dangerous operation
try:
    require_elevation("Registry cleanup")
    # ... perform registry cleanup ...
except PermissionError as e:
    log.error("permission_denied", operation="registry_cleanup", error=str(e))
```

**Verification:**
- [ ] Detects privilege level correctly
- [ ] Elevation works on Windows (UAC prompt)
- [ ] Elevation works on Linux (pkexec)
- [ ] Elevation works on macOS (osascript)
- [ ] Graceful failure when elevation denied

---

## 📊 Phase 1 Completion Checklist

### Infrastructure
- [ ] pyproject.toml created and working
- [ ] Package installs with `pip install -e .`
- [ ] Command `cortex-cleaner` is available

### Code Quality
- [ ] Config system migrated to Pydantic
- [ ] Database persistence working
- [ ] Structured logging configured
- [ ] Tests running and passing
- [ ] Privilege handler implemented

### Documentation
- [ ] All documentation files reviewed
- [ ] Migration guide followed
- [ ] Team understands new components

### Verification
- [ ] Run full test suite: `pytest tests/ -v --cov`
- [ ] Check coverage: Should be >50% for new code
- [ ] Manual testing: Run a scan and verify DB records
- [ ] Check logs: Verify structured output

---

## 🚀 Next Steps After Phase 1

Once all checkboxes above are complete:

1. **Commit changes** to version control
2. **Tag release** as v1.0.0-phase1
3. **Begin Phase 2** (Performance improvements)
4. **Set up CI/CD** for automated testing

---

## 💡 Tips

- **Test each task** before moving to the next
- **Keep old code** until new code is verified
- **Use git branches** for each major change
- **Document issues** you encounter
- **Ask for help** if stuck on any task

---

## 📞 Getting Help

If you encounter issues:

1. Check error messages carefully
2. Review relevant documentation file
3. Test in isolation (create minimal test case)
4. Check that all dependencies are installed
5. Verify Python version (>=3.10 required)
