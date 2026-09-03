# scripts/

Developer and build helper scripts. These are **not** part of the installable
`cortex_unified` package and are not shipped in the wheel.

Run them from the **project root**, e.g.:

```bash
python scripts/build_exe.py       # build the standalone executable
python scripts/verify_modules.py  # smoke-test the core system modules
```

| Script | Purpose |
| ------ | ------- |
| `build_exe.py` | PyInstaller build of the standalone GUI executable. |
| `run_all_tests.py` | Runs all test suites across the repository. |
| `test_all_pages.py` | Fast smoke test validating instantiation of all 126 UI pages. |
| `test_navigation.py` | Fast UI navigation smoke test cycling through all pages. |
| `check_lint_issues.py` | Scans the codebase with pyflakes for syntax errors or undefined variables. |
| `check_hardcoded_paths.py` | Scans codebase for hardcoded static drive letters or usernames. |
| `audit_imports.py` | Audits module imports and dependency graphs. |
| `audit_pages.py` | Audits UI page registry and metadata. |
| `audit_system_tools.py` | Verifies system tool module availability. |
| `verify_modules.py` | Functional smoke test of system tools. |
| `scan_codebase.py` | General codebase health scanner. |
