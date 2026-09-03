# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-09-03

### Added
- **Enterprise Kernel & Deep System Optimizers (6 New Modules):**
  - `winapp2_cleaner.py`: Declarative deep cleaner for 500+ desktop applications, browsers, game launchers, and IDEs using dynamic environment path resolution.
  - `srum_bam_cleaner.py`: Windows BAM/DAM execution forensics auditor and SRUM database manager with selective trace sanitization.
  - `directstorage_optimizer.py`: Windows 11 BypassIO state validator and NVMe-to-GPU DirectStorage storage minifilter analyzer.
  - `memory_standby_purger.py`: Native Windows NT kernel memory standby list purger and working set compactor via `NtSetSystemInformation` (Class 80).
  - `mft_slack_scrubber.py`: NTFS Master File Table ($MFT) resident record slack space and directory index scrubber compliant with NIST 800-88.
  - `search_index_optimizer.py`: Windows Search service (WSearch) and `Windows.edb` ESENT database offline defragmentation and catalog reset tool.
- **Nexus Explorer VFS Expansion:**
  - **Flat Branch View (`list_flat_branch`)**: Recursive single-list flat file display across deep directory trees with sorting by file size, type, or modified date.
- **UI Shell & Nomenclature Overhaul:**
  - Expanded declarative page registry to **132 theme-aware interactive pages** across 10 navigation groups.
  - **Vector SVG Navigation Chevrons**: Replaced non-standard unicode glyphs with crisp vector SVG `chevron-down` and `chevron-right` icons across all group headers.
  - **Universal SVG Palette Tinting Engine**: Implemented `CompositionMode_SourceIn` dynamic tinting so all 132 page icons render in harmonious theme slate (`#8B9BB4`) rather than saturated rainbow fills.
  - **100% Unique Icon Contract**: Shipped dedicated vector outline SVG assets for all 132 pages without any duplicate icons.
  - **Professional UI Copywriting**: Overhauled all page titles, subtitles, category tags, and action buttons to clear, professional, self-explanatory English, eliminating cryptic internal acronyms.
- **Production Verification:**
  - Expanded production diagnostics suite to **297 automated runtime checks** (100% pass rate in 9.25s).
  - 100% clean compilation (`python -m compileall -q src tests`).

## [1.1.0] - 2026-09-03

### Added
- **Next-Generation Enterprise System Tools (7 New Modules):**
  - `shader_cache_cleaner.py`: GPU & DirectX shader cache forensics covering DirectX D3DSCache, NVIDIA DXCache/GLCache, AMD DxCache, and Intel GPU caches with age-based purging.
  - `ai_telemetry_cleaner.py`: Windows 11 Copilot offline storage, Recall semantic vector DBs (`CoreAIPlatform.00\UKP`), and safe SQLite WAL checkpointing (`PRAGMA wal_checkpoint(TRUNCATE)`).
  - `ssd_trim_optimizer.py`: Solid-state drive media audit (NVMe vs SATA vs HDD), NTFS/ReFS `DisableDeleteNotify` validation, and live volume block deallocation (`Optimize-Volume -ReTrim`).
  - `restart_manager_unlocker.py`: Windows Native Restart Manager API bindings (`rstrtmgr.dll`) for lock detection and safe process termination.
  - `vss_health_analyzer.py`: Volume Shadow Copy (VSS) writer state diagnosis (`[1] Stable`, `[5] Waiting`, `[8] Failed`), shadow storage allocation audit, and 1-click state recovery.
  - `dev_package_cache_cleaner.py`: Developer package stores cleaner for Windows `winget`, Rust `cargo`, C++ `vcpkg`, .NET `nuget`, and Python `pip`.
  - `checksum_matrix.py`: Forensic multithreaded stream hashing (CRC32, MD5, SHA-1, SHA-256, SHA-512) and batch manifest generation/verification (.sha256, .sfv, .md5).
- **Presentation & UI Shell Expansion:**
  - Expanded declarative page registry to **126 theme-aware interactive pages** across 10 navigation groups.
  - Added dedicated GUI studios in `nextgen_suite_pages.py`: `ShaderCachePage`, `AiTelemetryCleanerPage`, `SsdTrimOptimizerPage`, `RestartManagerUnlockerPage`, `VssHealthAnalyzerPage`, `DevPackageCachePage`, and `ChecksumMatrixPage`.
- **Command Line Interface (CLI):**
  - Added 5 new CLI subcommands: `clean-shaders`, `clean-ai`, `trim-ssd`, `vss-health`, and `verify-checksums`.
- **Production Hardening & Verification:**
  - Expanded production diagnostics suite to 286 automated runtime checks (100% pass rate in 8.64s).
  - Audited and verified all 465 program files in the repository with zero syntax errors, zero missing modules, and zero undefined names.
  - Replaced all static local paths and drive letters with dynamic environment resolution.

## [1.0.0] - 2026-04-14

### Added
- **Core Engine:**
  - Parallel multi-threaded scanning capability
  - Resource throttling (CPU/RAM limits)
  - Pause/resume scanning with checkpoint persistence
- **New Analyzers:**
  - Duplicate file finder (MD5, SHA1)
  - Duplicate folder finder
  - Docker cleaner (images, containers, volumes, networks)
  - Windows registry broken link detector
  - Large file and old file finders
  - Broken symlink/shortcut detector
  - System temp and cache cleaners
  - Package manager cleaner (npm, pip, yarn cache)
  - Comprehensive disk space analyzer
- **System Tools:**
  - Startup manager and process analyzer
  - File shredder with configurable passes
  - Automated job scheduling
  - Exportable system reports
- **User Interfaces:**
  - Refined PySide6 GUI with comprehensive multi-tab dashboard
  - Extensive Click-based command line interface
- **Production CI/CD:**
  - automated testing pipeline with pytest
  - type hinting, linting checks via Github Actions
- **Safety Features:**
  - Interactive "dry run" defaults across all tools
  - Integration with OS recycle bin (`send2trash`)
  - Exclusions lists and custom heuristics filters

### Fixed
- Duplicate Click command definitions crashing CLI imports.
- Bare `raise` block error tracking in utilities module.
- Package module export misalignments.

## [Unreleased]

### Added
- **Dedicated "Leftover Scanner" sidebar page** under Apps & Security - the
  same engine was previously reachable only at the bottom of the Uninstaller
  page, which real-user feedback showed was not discoverable.
- **User exclusion list ("Keep Selected"):** reviewed findings can be marked
  keep-forever; stored atomically in `~/.cortex_cleaner/exclusions.json` and
  honoured by every later scan AND by the cleaner itself (defence in depth -
  a stale caller cannot delete an excluded path).
- **Consent-gated update check:** the informational release check now runs
  only when the user enables it in Settings (`update_check`, default OFF) -
  phoning home without asking is not acceptable for a tool that knows the
  user's software inventory. The leftover restore-point preference also
  persists across restarts (`leftover_restore_point`, default ON).
- **Similar-name disambiguation** (BCU's TestForSimilarNames guard): when
  several folders match an app's tokens, only the closest name keeps full
  confidence; weaker matches are penalised so "ZetaEditor" outranks
  "ZetaEditor Suite".
- **Cooperative cancellation everywhere:** scan workers stop between apps and
  inside sweeps via a cancel event; the cleaner stops between items while
  keeping already-cleaned items and the batch journal consistent. Window
  shutdown cancels in-flight leftover work automatically.
- **Backups & Restore shows leftover sessions:** each cleanup's journal
  appears as a read-only history row stating exactly where its undo
  artifacts live (Recycle Bin + .reg/.xml exports).
- **Restore point offered in both GUIs:** the premium Leftover Scanner and
  the legacy Uninstaller tab expose a "Create a System Restore point first"
  checkbox (default on) that flows through to the cleaner; the confirm dialog
  states it explicitly.
- **Leftover detection, advanced scanners:** COM registration sweep (CLSID/
  TypeLib entries whose server binary lives in the dead install location,
  with BCU's `-0000-` OS-GUID guard), InnoSetup `unins000.dat` manifest
  extraction (absolute paths recovered from the binary log and
  existence-checked - files its own uninstaller failed to remove are flagged
  with exact evidence), Windows service detection (`ImagePath` inside the
  dead install dir; cleaned via `sc delete` after a `.reg` backup and a
  best-effort stop) and scheduled-task detection (`<Command>` pointing into
  the dead install dir; cleaned via `schtasks /delete` after backing up the
  task XML).
- **Token stopwords:** generic words that carry no product identity
  ("installed", "setup", "update", "version", ...) never become search
  tokens, eliminating a whole false-positive class found by dogfooding.
- **`cortex leftovers` CLI:** `scan`/`orphans` (read-only) and `clean`
  (dry-run by default, `--apply`, `--min-level` confidence floor, optional
  `--restore-point`, `--json`). Failures exit non-zero for automation.
- **Restore point before cleanup:** `LeftoverCleaner(clean(...,
  create_restore_point=True))` attempts a System Restore checkpoint first;
  created/throttled/unavailable is recorded honestly in the operation
  journal and never blocks the cleanup.
- **Legacy Uninstaller tab upgraded:** now uses the production LeftoverScanner
  engine (confidence column + evidence tooltips) instead of the old top-level
  substring ResidualHunter, and cleans through LeftoverCleaner - replacing
  permanent `shutil.rmtree` deletion with Recycle Bin + registry backups.
- **Update checker (informational):** queries GitHub releases once per run
  after startup settles; reports newer versions in the status bar. Never
  downloads or installs anything.
- **Crash reports:** uncaught exceptions additionally persist a timestamped
  crash report under the log directory, flagged that paths may contain
  personal filenames.
- **Distribution assets:** `installer/cortex_cleaner.iss` (Inno Setup,
  onedir, per-user-capable, non-`setup.exe` name), `installer/sign.ps1`
  (SHA-256 + RFC 3161 timestamp signing of every PE with post-sign
  verification) and `installer/README.md` (full release runbook: build,
  sign, SmartScreen reputation expectations, VirusTotal pre-checks, verified
  auto-update channel options). PyInstaller spec hardened: UPX disabled
  (corrupts Qt DLLs, triggers AV heuristics), sibling Qt bindings excluded.
- **Leftover Cleaner (post-uninstall residual cleanup):** a new
  `system_tools/leftover_cleaner.py` engine that finds and safely removes the
  files, folders, caches, shortcuts and registry keys that official
  uninstallers leave behind on C:\. Detection follows the pipeline published
  by Bulk Crap Uninstaller: app inventory from all four Uninstall registry
  branches (HKLM/HKCU x 64-bit/WOW6432Node) with installer-type detection
  (MSI GUID / InnoSetup `_is1` / NSIS), a depth-limited sweep of the standard
  leftover locations (Program Files, ProgramData, AppData Roaming/Local/
  LocalLow, per-user Programs, VirtualStore), a `SOFTWARE` registry walk with
  explicit install-pointer value detection, Start Menu shortcut resolution,
  and signed evidence scoring mapped to VeryGood/Good/Questionable/Bad review
  tiers. Safety gates: known-folder prohibition, directory-name blacklist
  (shared vendor folders such as `Microsoft`/`Intel` are never candidates),
  Windows System attribute, reparse points are recorded but never descended,
  self-protection, and cross-checks against every currently-installed app
  (name still installed -4, path inside a live install -7). Cleanup keeps
  three undo layers: Recycle Bin via send2trash (permanent-delete outcomes
  are surfaced, never silent), `reg export` backups before any registry
  deletion, and an atomic JSON operation journal.
- **Deep Uninstaller page - Leftover Scanner section:** after running an
  uninstaller, "Scan for Leftovers" sweeps for that app's residuals using the
  metadata captured before uninstall; "Find Orphan Folders" reports unclaimed
  Program Files folders. Findings appear in a sortable model/view table with
  size, colour-coded confidence and per-item evidence tooltips; "Clean
  Selected" confirms, then recycles files and deletes backed-up registry
  keys, reporting freed bytes and failures honestly.
- 39 unit tests for the leftover engine (matcher, scoring, safety gates,
  synthetic filesystem/registry sweeps, cleaner with monkeypatched
  send2trash/reg) plus 6 headless GUI tests for the new page section.
- **Cloud-placeholder safety in the scan engine:** OneDrive Files On-Demand and
  similar cloud placeholders are now detected via Windows reparse attributes
  (not just `is_symlink()`), excluded from scan totals, and reported rather
  than silently mis-sized. Junctions are never descended. The shredder refuses
  to overwrite a placeholder instead of triggering a download.
- **Virtual Disks page:** discovers WSL2 / Docker Desktop / Hyper-V `.vhdx`
  files (which grow but never shrink on their own) and compacts them safely -
  refusing while the owning runtime still holds the disk open, and reporting
  measured before/after byte counts rather than an estimate.
- **Component Store page:** measures the Windows component store (WinSxS)
  honestly via `DISM /AnalyzeComponentStore` before offering a cleanup, and
  inventories upgrade leftovers (`Windows.old`, update staging, setup logs)
  with a plain statement of what removing each one costs. Refuses to
  hand-delete anything Windows manages itself (WinSxS, `Windows\Installer`).
- `core.proc`: a cancellable, tree-safe subprocess runner used by every
  long-running external-tool call (SFC, DISM, winget, diskpart, cipher,
  PowerShell). Polls a timeout and/or `cancel_event` and kills the whole
  process tree on either, rather than blocking the calling thread
  uninterruptibly.

### Fixed
- **Event-filter infinite recursion could freeze the UI** (KeyboardInterrupt
  storms from `window.py`/`focus.py` re-entering each other): both app-level
  filters now carry a re-entrancy guard.
- **Floating "NOTHING HERE" mini-window on the Leftover Scanner page:** the
  section's StatePanel was created without being added to the layout, so Qt
  promoted it to a parentless top-level window. It is now a proper child of
  the page.
- **Nexus page crashed navigation and poisoned later tests:** the embedded
  native explorer used a non-existent Qt enum (`QFont.StyleHint` vs
  `StyleType` across PySide6 versions - now compatibility-guarded), passed
  the palette object where a parent widget was expected, and built its heavy
  native widget eagerly. The explorer is now constructed lazily on first
  visit like every other page, and never in headless/offscreen mode.
- **Cross-page leftover handoff restored:** the Uninstaller page captures
  uninstalled-app metadata into a window-level buffer that the Leftover
  Scanner page consumes; without it, "Scan for Leftovers" could never find
  anything.
- `app.py` merge collision that left module-level hook installs indented
  inside `main()` (IndentationError at startup).
- README referenced a nonexistent `run_cli.py`; CLI instructions now use the
  real `cortex` / `python -m cortex_unified.engine.cli` entry points and
  document the new `leftovers` commands.
- `requirements.txt` had drifted from `pyproject.toml` (missing core deps
  structlog/pydantic/pydantic-settings; floors inconsistent with the declared
  Python 3.10+ support). Both lists now agree, with pyproject as source of
  truth.
- **GUI test-suite hang:** running the full premium GUI module could block
  indefinitely after ~26 tests on Windows. Window fixtures now release each
  window's native resources (`deleteLater()` + event pump) at teardown;
  dozens of live top-level windows were accumulating GDI/widget resources.
- Stale page-count expectations in `test_premium_gui.py` /
  `test_lazy_pages.py` after the Project Folder Caches page was added to the
  navigation registry (43 -> 44).
- **Worker shutdown could corrupt the process.** Closing the window while a
  worker was blocked inside a subprocess call used to fall back to
  `QThread.terminate()` (Windows' `TerminateThread`), which can fire while the
  thread holds a CRT/heap lock during a blocked pipe read and wedge the whole
  process - surfacing as an apparently unrelated hang later in the app's life.
  Shutdown no longer calls `terminate()`; every long-running backend call now
  honors cooperative cancellation through `core.proc`, and a worker that still
  does not stop in time is detached (never destroyed) instead.
- Packaging: dropped the deprecated `license = {file = ...}` / classifier
  form in favor of an SPDX `license` string, matching current setuptools.

### Changed
- `requires-python` raised from `>=3.8` to `>=3.10` to match the `X | None`
  union syntax and `@dataclass(slots=True)` already used throughout the
  codebase; CI's Python matrix updated to 3.10-3.13 accordingly.
