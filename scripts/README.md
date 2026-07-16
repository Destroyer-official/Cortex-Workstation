# scripts/

Developer and build helper scripts. These are **not** part of the installable
`cortex_unified` package and are not shipped in the wheel.

Run them from the **project root**, e.g.:

```bash
python scripts/build_exe.py       # build the standalone executable
python scripts/verify_modules.py  # smoke-test the weaponized modules
```

| Script | Purpose |
| ------ | ------- |
| `build_exe.py` | PyInstaller build of the standalone GUI executable. |
| `verify_modules.py` | Manual functional smoke test of system-tool modules. |
| `repair_imports.py` | One-off migration helper (historical; kept for reference). |
| `apply_critical_fixes.py`, `implement_phase1.py`, `setup_phase1.py`, `test_fixes.py`, `implement_phase1.bat` | Historical one-off upgrade/migration helpers. |
