# Contributing to Cortex Workstation

Thank you for contributing to Cortex Workstation! This document provides an architectural overview, coding standards, and step-by-step guides for adding new features, UI pages, and maintaining enterprise production readiness.

---

## 1. Codebase Architecture Overview

Cortex Workstation is structured into high-performance, modular subsystems:

```text
src/
├── cortex_unified/
│   ├── analyzers/        # 23 deduplication, shredding, and disk analyzers
│   ├── core/             # PathGuard security boundaries, configuration, database
│   ├── debug/            # Comprehensive 7-stage production diagnostic engine
│   ├── engine/           # FastWalk (PEP 471), storage media awareness, typed models
│   ├── licensing/        # Hardware fingerprinting and tier gating (FREE/PRO/ENT)
│   ├── performance/      # Multi-drive scanner, CPU/IO throttler, resource monitor
│   ├── reports/          # Audit report generator and undo/restore snapshots
│   ├── resources/icons/  # 132 crisp vector SVG icons (zero glyphs)
│   ├── system_tools/     # 62 system maintenance, hardware, and network modules
│   └── ui/premium/       # Modern Fluent UI shell, design tokens, and 132 lazy pages
└── NexusExplorer/
    ├── native/           # High-performance VFS transport, C/Rust FFI bridge, USN journal scanner
    └── tests/            # Explorer benchmarks, transport parity, and UI state tests
```

---

## 2. Developer Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Destroyer40/Cortex_Cleaner.git
   cd Cortex_Cleaner
   ```
2. **Create & activate virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. **Install development dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

---

## 3. How to Add New Features

### A. Adding a New System Tool

1. **Create the tool module** in `src/cortex_unified/system_tools/<tool_name>.py`:
   ```python
   """My Tool - description of functionality."""
   from __future__ import annotations
   import logging
   import os
   from dataclasses import dataclass
   from typing import Optional

   logger = logging.getLogger("cortex.system_tools.my_tool")

   @dataclass
   class MyToolReport:
       status: str = "Ready"
       error: Optional[str] = None

   class MyTool:
       def __init__(self):
           self._is_windows = os.name == "nt"

       def audit(self) -> MyToolReport:
           if not self._is_windows:
               return MyToolReport(error="Windows NT required")
           return MyToolReport(status="Compliant")
   ```

2. **Add a dedicated test** in `tests/test_<tool_name>.py` and run `pytest`.

---

### B. Adding a New UI Page to the Shell

1. **Create the page widget** in `src/cortex_unified/ui/premium/<suite_name>_pages.py`:
   - Inherit from `_Page(win)`.
   - Use `Card`, `title_block`, and `_run_task(self.win, ...)` for non-blocking asynchronous execution.

2. **Add a vector SVG icon**:
   - Create `src/cortex_unified/resources/icons/<icon_name>.svg`.
   - Verify with `pytest tests/test_icons.py`.

3. **Register the page** in `src/cortex_unified/ui/premium/registry.py`:
   ```python
   PageSpec(
       id="mytool",
       title="My Tool",
       icon="mytool",
       group="system",  # 'overview', 'cleanup', 'system', 'files', etc.
       factory="cortex_unified.ui.premium.my_pages:MyToolPage",
   )
   ```

4. **Verify registry integrity**:
   ```bash
   pytest tests/test_page_registry.py
   ```

---

## 4. Pull Request & Commit Guidelines

### Conventional Commits
Please use clear, descriptive commit messages adhering to Conventional Commits:
- `feat: add ReFS Dev Drive block cloning verification`
- `fix: resolve 64-bit pointer overflow in process token auditor`
- `docs: update complete API reference and architecture specs`
- `test: add unit tests for VSS shadow copy manager`
- `perf: optimize USN journal NTFS record stream parsing`

### Pre-PR Verification Checklist
Before submitting a pull request, ensure:
- [ ] All unit tests pass: `pytest tests/ -v --no-cov`
- [ ] Page registry and icons pass: `pytest tests/test_page_registry.py tests/test_icons.py -v`
- [ ] Codebase audit passes: `python scripts/check_all_structure_files.py` (100% pass rate)
- [ ] No hardcoded paths, mock data, or blocking calls on the Qt GUI main thread.