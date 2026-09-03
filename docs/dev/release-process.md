# 🚀 Release & Review Process

Guidelines for contributing code, opening pull requests, and creating official releases for Cortex Workstation.

---

## 🤝 Pull Request (PR) Lifecycle

1. **Fork & Branch:** Create a feature branch off `main` with a descriptive name (e.g. `feat/vss-snapshot-diff` or `fix/disk-health-nvme`).
2. **Conventional Commits:** Write clean commit messages following Conventional Commits format:
   * `feat: add directstorage bypassio filter validator`
   * `fix: correct mft slack scrubber cluster alignment`
   * `docs: update subsystem api lifecycle table`
   * `test: add unit tests for fastcdc gear hash`
3. **Automated Verification:** Before opening your PR, ensure all tests pass:
   ```bash
   python -m compileall -q src tests
   pytest tests/ --no-cov
   python scripts/verify_production_readiness.py
   ```
4. **Code Review:** All PRs require passing automated CI workflows and review from repository maintainers before merge.

---

## 📦 Creating a Production Release

1. **Update Version:** Increment version string in `pyproject.toml` and `src/cortex_unified/__init__.py`.
2. **Update Changelog:** Document new features, enhancements, and fixes in `CHANGELOG.md`.
3. **Build Standalone Binary:**
   ```bash
   python scripts/build_exe.py
   ```
4. **Tag & Publish:** Create a signed Git tag and push:
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0"
   git push origin v1.2.0
   ```
