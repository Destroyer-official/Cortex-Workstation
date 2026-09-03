# 🧪 Testing & CI/CD Pipelines

Cortex Workstation maintains an exhaustive automated test suite with **1,569 test cases** validating every system tool, forensic scanner, algorithm, and GUI presentation widget.

---

## 🏃 Running Tests Locally

### 1. Run the Complete Test Suite
```bash
pytest tests/ --no-cov
```

### 2. Run Headless GUI Tests
To run UI and window tests without launching a visible window:
```powershell
$env:QT_QPA_PLATFORM = "offscreen"
pytest tests/test_premium_gui.py tests/test_gui_pages_e2e.py --no-cov
```

### 3. Run Production Readiness Diagnostics
Execute the 7-stage production diagnostics suite (covers SVG icons, system tools, analyzers, safety guards, and 132 UI pages):
```bash
python scripts/verify_production_readiness.py
```

### 4. Run One-by-One File-by-File Audit
Validate AST syntax, bytecode compilation, and dynamic imports across all 484 repository files:
```bash
python scripts/check_all_structure_files.py
```

---

## 🏗️ Continuous Integration (GitHub Actions)

Every pull request to `main` triggers automated CI workflows:
* **Multi-Platform Lint & Compile Check:** Validates syntax across Python 3.10, 3.11, 3.12, 3.13, and 3.14.
* **Windows NT Diagnostic Test Runner:** Executes the complete test suite on hosted Windows Server runners.
* **Documentation Builder:** Validates that MkDocs Material builds with zero broken links.
