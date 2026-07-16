# Phase 1: Quick Start Implementation Guide

## 🎯 Goal
Fix critical structural issues blocking production deployment.

## ⚡ Quick Wins (Start Here)

### 1. Fix pyproject.toml (30 minutes)

Navigate to project root and update `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cortex-cleaner"
version = "1.0.0"
description = "Enterprise-grade system cleaning tool"
requires-python = ">=3.10"
dependencies = [
    "PySide6>=6.6",
    "click>=8.1",
    "psutil>=5.9",
    "pyyaml>=6.0",
    "xxhash>=3.4",
    "send2trash>=1.8",
    "rich>=13.0",
    "sqlalchemy>=2.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "structlog>=24.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=4.1", "hypothesis>=6.98", "black>=24.0", "ruff>=0.2"]
ai = ["anthropic>=0.18", "pillow>=10.0", "imagehash>=4.3"]

[project.scripts]
cortex-cleaner = "cortex_unified.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]
include = ["cortex_unified*"]
```

Test: `pip install -e .` should work without errors.

### 2. Add Pydantic Config (2 hours)

Create `core/config_v2.py` - see full implementation in repo.

Key features:
- Type-safe configuration
- Environment variable support
- Validation with clear error messages
- Auto-migration from old YAML format

### 3. Add SQLite Database (3 hours)

Create `core/database.py` with SQLAlchemy 2.0:

```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Session
from datetime import datetime

class Base(DeclarativeBase): pass

class ScanRun(Base):
    __tablename__ = "scan_runs"
    id = Column(Integer, primary_key=True)
    scan_type = Column(String(64))
    started_at = Column(DateTime, default=datetime.utcnow)
    bytes_found = Column(Integer, default=0)
    # ... more fields
```

### 4. Add Structured Logging (1 hour)

Create `core/logging_setup.py`:

```python
import structlog

def configure_logging(json_output=False):
    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(processors=processors)
```

### 5. Add Test Framework (4 hours)

Create `tests/` directory structure:

```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── test_config.py
│   ├── test_scanner.py
│   └── test_analyzers.py
├── integration/
│   └── test_scan_delete_restore.py
└── security/
    └── test_path_validator.py
```

Minimum test: Config validation

```python
import pytest
from cortex_unified.core.config_v2 import Config

def test_config_validates_threads():
    with pytest.raises(ValueError):
        Config(threads=-1)
```

### 6. Add Privilege Handler (2 hours)

Create `core/privilege.py`:

```python
import sys, os

def is_elevated() -> bool:
    if sys.platform == "win32":
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    return os.geteuid() == 0

def request_elevation():
    # Platform-specific elevation logic
    pass
```

## ✅ Phase 1 Complete Checklist

- [ ] `pip install -e .` works
- [ ] Config validates input
- [ ] Database stores scan history
- [ ] Logs output structured format
- [ ] Tests run with `pytest`
- [ ] Privilege handler detects elevation

## 🚀 Next Steps

After Phase 1:
- Phase 2: Performance (xxHash, async scanner)
- Phase 3: Cross-platform (macOS/Linux modules)
- Phase 4: AI features (image dedup, folder explainer)

## 📊 Estimated Time

- **Minimum viable**: 1 day (items 1-2)
- **Production ready**: 2-3 weeks (all items + tests)
- **Recommended**: 2 weeks with proper testing

---

*Quick Start Guide v1.0*
