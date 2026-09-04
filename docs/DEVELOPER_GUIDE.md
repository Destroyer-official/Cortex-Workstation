# Cortex Cleaner — Developer Onboarding & Extension Guide

Welcome to the Cortex Cleaner developer guide. This document provides step-by-step instructions for contributors on how to set up the development environment, understand coding conventions, build new system tools, create UI pages, and verify code with automated tests.

---

## 1. Development Environment Setup

### Prerequisites
- **Operating System**: Windows 10 (Build 19041+) or Windows 11 (recommended for ReFS Dev Drive / MMAgent tools).
- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14 (64-bit).
- **Git**: For version control.

### Installation Steps

```powershell
# 1. Clone the repository
git clone https://github.com/Destroyer40/Cortex_Cleaner.git
cd Cortex_Cleaner

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Upgrade build tools
python -m pip install --upgrade pip setuptools wheel

# 4. Install production and development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 5. Install package in editable development mode
pip install -e .
```

### Launching the Application
- **Interactive GUI Shell**:
  ```powershell
  python run_gui.py
  ```
- **CLI Interface**:
  ```powershell
  python -m cortex_unified.cli.cli --help
  ```

---

## 2. Code Style & Quality Standards

- **Python Standards**: Follow PEP 8 style guidelines.
- **Type Annotations**: Use `from __future__ import annotations` and comprehensive type hints on all public functions and methods.
- **Dataclasses**: Use `@dataclass` for return values, reports, and data transfer objects rather than raw dictionaries or tuples.
- **Thread Safety**: Never interact with Qt GUI widgets from background worker threads. Use `_run_task` with `on_result` and `on_error` callbacks that execute safely on the Qt GUI thread.
- **Windows Safety**: Always check `os.name == "nt"` before invoking Win32 APIs, providing a descriptive error string if invoked on non-Windows platforms.

---

## 3. Tutorial: Adding a New System Tool & UI Page

Let's walk through an end-to-end example of building a new tool: a hypothetical **DNS Flush & Resolver Tool**.

> **Note:** `dns_resolver.py`, `dnsflush.svg`, `DnsResolverPage`, and `test_dns_resolver.py` below are illustrative example names for files you will create in this tutorial — they do not ship with the repository. The existing `src/cortex_unified/ui/premium/network_pages.py` ships with `TrafficMonitorPage`, `FirewallPage`, `NetworkMapPage`, `LanDevicesPage`, `NetworkToolsPage`, and `LoadTesterPage`; for a real-world backend reference see `src/cortex_unified/system_tools/dns_benchmark.py`.

### Step 1: Implement the Backend Module
Create `src/cortex_unified/system_tools/dns_resolver.py`:

```python
"""Cortex Cleaner — DNS Resolver & Cache Tool."""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cortex.system_tools.dns_resolver")


@dataclass
class DnsReport:
    cache_entries_count: int = 0
    flush_status: str = "Ready"
    servers: list[str] = field(default_factory=list)
    error: Optional[str] = None


class DnsResolverTool:
    """Forensic DNS Resolver Cache & Flushing Tool."""

    def __init__(self):
        self._is_windows = os.name == "nt"

    def audit(self) -> DnsReport:
        if not self._is_windows:
            return DnsReport(error="Windows NT required")

        # Query DNS servers via netsh or ipconfig
        try:
            res = subprocess.run(
                ["ipconfig", "/displaydns"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            entries = res.stdout.count("Record Name")
            return DnsReport(cache_entries_count=entries, flush_status="OK")
        except Exception as exc:
            return DnsReport(error=str(exc))

    def flush(self) -> tuple[bool, str]:
        try:
            res = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return res.returncode == 0, res.stdout.strip()
        except Exception as exc:
            return False, str(exc)
```

---

### Step 2: Create a Vector SVG Icon
Create `src/cortex_unified/resources/icons/dnsflush.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="12" r="10"/>
  <line x1="2" y1="12" x2="22" y2="12"/>
  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
</svg>
```

---

### Step 3: Implement the UI Page
Create the page class inside `src/cortex_unified/ui/premium/network_pages.py` or your suite file:

```python
from .window import _Page, PremiumMainWindow
from .widgets import Card, title_block
from .tokens import Spacing
from cortex_unified.system_tools.dns_resolver import DnsResolverTool, DnsReport

class DnsResolverPage(_Page):
    def __init__(self, win: PremiumMainWindow):
        super().__init__(win)
        self.v.addWidget(title_block("DNS Cache & Resolver", "Flush local DNS resolver cache and audit active entries."))

        card = Card(self.p)
        cl = QVBoxLayout(card)
        
        self.flush_btn = QPushButton("Flush DNS Cache", self.p)
        self.flush_btn.clicked.connect(self._on_flush)
        cl.addWidget(self.flush_btn)

        self.summary_label = QLabel("Click Flush DNS Cache to clear resolver cache.")
        cl.addWidget(self.summary_label)
        self.v.addWidget(card)

        self._tool = DnsResolverTool()

    def _on_flush(self):
        self.summary_label.setText("Flushing cache…")
        _run_task(self.win, self._tool.flush, self._on_flush_done, self._on_err)

    def _on_flush_done(self, res: tuple[bool, str]):
        ok, msg = res
        self.summary_label.setText(msg if ok else f"Failed: {msg}")

    def _on_err(self, exc):
        self.summary_label.setText(f"Error: {exc}")
```

---

### Step 4: Register in `registry.py`
Open `src/cortex_unified/ui/premium/registry.py` and register the new spec in `PAGES`:

```python
    PageSpec(
        id="dnsflush",
        title="DNS Resolver",
        icon="dnsflush",
        group="network",
        factory="cortex_unified.ui.premium.network_pages:DnsResolverPage",
    ),
```

---

### Step 5: Write the Automated Unit Test
Create or update `tests/test_dns_resolver.py`:

```python
from cortex_unified.system_tools.dns_resolver import DnsResolverTool, DnsReport

def test_dns_resolver_audit():
    tool = DnsResolverTool()
    rep = tool.audit()
    assert isinstance(rep, DnsReport)
    assert rep.cache_entries_count >= 0

def test_dns_resolver_flush():
    tool = DnsResolverTool()
    ok, msg = tool.flush()
    assert ok is True
    assert "successfully" in msg.lower()
```

---

## 4. Running Tests & Quality Verification

Run all test suites before submitting a pull request:

```powershell
# 1. Run full unit test suite
pytest tests/ -v --no-cov

# 2. Run icon and registry consistency checks
pytest tests/test_page_registry.py tests/test_icons.py -v

# 3. Run complete file-by-file AST and compilation audit
python scripts/check_all_structure_files.py

# 4. Verify launch and diagnostic health
python -m cortex_unified.debug.runner
```
