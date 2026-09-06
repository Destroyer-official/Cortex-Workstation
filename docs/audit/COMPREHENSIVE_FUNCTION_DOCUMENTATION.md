# Comprehensive Function Documentation: CLI & GUI Tools

> Exhaustive technical reference detailing function signatures, parameters, operational semantics, and error behaviors across Cortex Cleaner.

## Table of Contents
1. [GUI Page Functions & Workers](#1-gui-page-functions--workers)
2. [CLI Commands & Execution Flow](#2-cli-commands--execution-flow)
3. [Backend System Tools & Cleaners](#3-backend-system-tools--cleaners)
4. [Analyzers & Duplicate Detection Engines](#4-analyzers--duplicate-detection-engines)

---

## 1. GUI Page Functions & Workers

### Module `src/cortex_unified/ui/premium/advanced_uninstaller_page.py`
#### Class `_UninstallWorker`
*_UninstallWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 40
- **Key Methods & Handlers**:
  - **`__init__(self, app_ids, force, scan_leftovers, max_leftovers_mb, sources)`** (Line 46): Initialize worker.
  - **`cancel(self)`** (Line 63): cancel.
  - **`run(self)`** (Line 67): run.

#### Class `AdvancedUninstallerPage`
*Multi-source uninstaller with forced removal and leftover detection.*

- **Inherits From**: `_Page`
- **Source Line**: 111
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 114): __init__.
  - **`_pick_root(self)`** (Line 243): _pick_root.
  - **`_scan(self)`** (Line 253): _scan.
  - **`_on_progress(self, msg)`** (Line 277): _on_progress.
  - **`_on_scan_done(self, apps)`** (Line 281): _on_scan_done.
  - **`_confirm_uninstall(self)`** (Line 308): _confirm_uninstall.
  - **`_run_uninstall(self, apps)`** (Line 370): _run_uninstall.
  - **`_on_uninstall_done(self, results)`** (Line 392): _on_uninstall_done.
  - **`_on_fail(self, msg)`** (Line 443): _on_fail.
  - **`_selected_apps(self)`** (Line 452): _selected_apps.
  - **`_fail(self, msg)`** (Line 466): _fail.

### Module `src/cortex_unified/ui/premium/analysis_pages.py`
#### Class `DiskAnalyzeWorker`
*Background worker that runs disk analyze via DiskAnalyzer (disk analyzer); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 44
- **Key Methods & Handlers**:
  - **`__init__(self, root)`** (Line 49): Store constructor arguments (root) and initialize worker signals.
  - **`run(self)`** (Line 54): Run the DiskAnalyzer (disk analyzer) backend call off the UI thread; emit finished/failed with results.

#### Class `DiskHealthWorker`
*Background worker that runs disk health via DiskHealthMonitor (disk health); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 67
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 72): Run the DiskHealthMonitor (disk health) backend call off the UI thread; emit finished/failed with results.

#### Class `ScheduledTasksWorker`
*Background worker that runs scheduled tasks via TaskScheduler (scheduler); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 81
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 86): Run the TaskScheduler (scheduler) backend call off the UI thread; emit finished/failed with results.

#### Class `BootPerfWorker`
*Background worker that runs boot perf via BootPerformanceMonitor (boot performance); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 95
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 100): Run the BootPerformanceMonitor (boot performance) backend call off the UI thread; emit finished/failed with results.

#### Class `SystemRepairWorker`
*Background worker that runs system repair via SystemRepair (system repair); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 109
- **Key Methods & Handlers**:
  - **`__init__(self, action, drive)`** (Line 114): Store constructor arguments (action, drive) and initialize worker signals.
  - **`run(self)`** (Line 120): Run the SystemRepair (system repair) backend call off the UI thread; emit finished/failed with results.

#### Class `DeleteTaskWorker`
*Background worker that runs delete task via TaskScheduler (scheduler); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 140
- **Key Methods & Handlers**:
  - **`__init__(self, name)`** (Line 145): Store constructor arguments (name) and initialize worker signals.
  - **`run(self)`** (Line 150): Run the TaskScheduler (scheduler) backend call off the UI thread; emit finished/failed with results.

#### Class `DiskAnalyzerPage`
*Break down where space goes: file types + largest directories.*

- **Inherits From**: `_Page`
- **Source Line**: 164
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 167): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_pick(self)`** (Line 244): Pick via the file dialog; results return through worker signals.
  - **`_run(self)`** (Line 251): Run via the background worker, progress state, status bar; results return through worker signals.
  - **`_on_done(self, stats)`** (Line 258): Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.
  - **`_fail(self, msg)`** (Line 304): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `DiskHealthPage`
*Read-only physical-disk health (S.M.A.R.T.) overview.*

- **Inherits From**: `_Page`
- **Source Line**: 314
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 317): Build the page layout (buttons, tables, title header, state panel) and connect button/worker actions.
  - **`_load(self)`** (Line 369): Load via the background worker, progress state, status bar; results return through worker signals.
  - **`_dash(v)`** (Line 377): Dash via the worker/widgets; results return through worker signals.
  - **`_on_done(self, disks)`** (Line 381): Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.
  - **`_fail(self, msg)`** (Line 416): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `ScheduledTasksPage`
*View OS scheduled tasks; delete Cortex-created cleanup tasks.*

- **Inherits From**: `_Page`
- **Source Line**: 426
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 429): Build the page layout (buttons, tables, title header, state panel) and connect button/worker actions.
  - **`_load(self)`** (Line 485): Load via the background worker, progress state, status bar; results return through worker signals.
  - **`_on_done(self, tasks)`** (Line 492): Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.
  - **`_delete(self)`** (Line 507): Delete via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_deleted(self, ok, name)`** (Line 526): Handle worker results: update widgets and clear the busy state.
  - **`_fail(self, msg)`** (Line 537): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `BootPerformancePage`
*Why your PC is slow to start - using Windows' own boot measurements.*

- **Inherits From**: `_Page`
- **Source Line**: 547
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 550): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_load(self)`** (Line 613): Load via the background worker, progress state, status bar; results return through worker signals.
  - **`_on_done(self, data)`** (Line 620): Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.
  - **`_fail(self, msg)`** (Line 668): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `SystemRepairPage`
*Run Windows' built-in SFC / DISM / CHKDSK repair tools, explained.*

- **Inherits From**: `_Page`
- **Source Line**: 678
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 681): Build the page layout (cards, title header, progress bar) and connect button/worker actions.
  - **`_tool_row(self, layout, title, desc, handler)`** (Line 754): Tool row via the worker/widgets; results return through worker signals.
  - **`_run(self, action, title, prompt)`** (Line 771): Run via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_done(self, r)`** (Line 789): Handle worker results: note status, re-enable buttons and clear the busy state.
  - **`_fail(self, msg)`** (Line 819): Report the worker error in the re-enable actions and clear the busy state.

#### Class `StorageSenseWorker`
*Background worker that runs storage sense via StorageSense (storage sense); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 834
- **Key Methods & Handlers**:
  - **`__init__(self, action, value)`** (Line 839): Store constructor arguments (action, value) and initialize worker signals.
  - **`run(self)`** (Line 845): Run the StorageSense (storage sense) backend call off the UI thread; emit finished/failed with results.

#### Class `StorageSensePage`
*Turn on and schedule Windows' built-in automatic cleanup.*

- **Inherits From**: `_Page`
- **Source Line**: 861
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 868): Build the page layout (cards, title header, controls) and connect button/worker actions.
  - **`_load(self)`** (Line 923): Load via the background worker; results return through worker signals.
  - **`_on_status(self, s)`** (Line 927): Handle worker results: update cards/labels and clear the busy state.
  - **`_toggle_enable(self, on)`** (Line 952): Compute and return the value for toggle enable used by the page.
  - **`_set_cadence(self, idx)`** (Line 959): Compute and return the value for set cadence used by the page.
  - **`_set_recycle(self, idx)`** (Line 966): Compute and return the value for set recycle used by the page.
  - **`_fail(self, msg)`** (Line 973): Report the worker error in the state panel/status bar and clear the busy state.

#### Class `DefenderStatusWorker`
*Background worker that runs defender status via WindowsDefender (defender); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 982
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 987): Run the WindowsDefender (defender) backend call off the UI thread; emit finished/failed with results.

#### Class `DefenderScanWorker`
*Background worker that runs defender scan via WindowsDefender (defender); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 997
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 1002): Run the WindowsDefender (defender) backend call off the UI thread; emit finished/failed with results.

#### Class `SecurityPage`
*Windows Security (Defender) status + quick scan.*

- **Inherits From**: `_Page`
- **Source Line**: 1012
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1015): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_load(self)`** (Line 1076): Load via the background worker, progress state; results return through worker signals.
  - **`_on_status(self, s, threats)`** (Line 1082): Handle worker results: refresh tables/trees, re-enable buttons and clear the busy state.
  - **`_scan(self)`** (Line 1126): Scan via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_scanned(self, ok, msg)`** (Line 1143): Handle worker results: re-enable buttons and clear the busy state.
  - **`_fail(self, msg)`** (Line 1153): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `HealthCheckWorker`
*Background worker that runs health check via HealthChecker (health check); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1164
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 1170): Run the HealthChecker (health check) backend call off the UI thread; emit finished/failed/progress with results.

#### Class `HealthCheckPage`
*One click to assess overall PC health across the fast diagnostics.*

- **Inherits From**: `_Page`
- **Source Line**: 1180
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1194): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_run(self)`** (Line 1272): Run via the background worker, progress state, results view; results return through worker signals.
  - **`_on_progress(self, msg)`** (Line 1286): Handle worker results: update widgets and clear the busy state.
  - **`_on_done(self, report)`** (Line 1290): Handle worker results: refresh tables/trees, update cards/labels, note status and clear the busy state.
  - **`_fail(self, msg)`** (Line 1341): Report the worker error in the re-enable actions and clear the busy state.

#### Class `WUActivityWorker`
*Background worker that runs wuactivity via WindowsUpdate (windows update); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1356
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 1361): Run the WindowsUpdate (windows update) backend call off the UI thread; emit finished/failed with results.

#### Class `WUPendingWorker`
*Background worker that runs wupending via WindowsUpdate (windows update); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1371
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 1376): Run the WindowsUpdate (windows update) backend call off the UI thread; emit finished/failed with results.

#### Class `WindowsUpdatePage`
*See when Windows last updated, what's pending, and recent update history.*

- **Inherits From**: `_Page`
- **Source Line**: 1385
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1388): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_load(self)`** (Line 1464): Load via the background worker, progress state; results return through worker signals.
  - **`_on_activity(self, activity, history)`** (Line 1469): Handle worker results: refresh tables/trees, update cards/labels and clear the busy state.
  - **`_check_pending(self)`** (Line 1483): Handle check pending for the page widgets and worker state.
  - **`_on_pending(self, updates)`** (Line 1490): Handle worker results: refresh tables/trees, note status, re-enable buttons and clear the busy state.
  - **`_open_settings(self)`** (Line 1504): Handle open settings for the page widgets and worker state.
  - **`_fail(self, msg)`** (Line 1512): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `ComponentStorePage`
*Shrink WinSxS the supported way, and clear upgrade leftovers.

``C:\Windows`` filling up is nearly always the component store plus upgrade
leftovers, and the internet is full of advice that breaks Windows Update or
permanently prevents uninstalling Office. This page measures first using
Windows' own analysis, then offers only supported actions - and reports what
each one costs.*

- **Inherits From**: `_Page`
- **Source Line**: 1522
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1532): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_selected_leftovers(self)`** (Line 1654): Compute and return the value for selected leftovers used by the page.
  - **`_on_select(self)`** (Line 1659): Handle worker results: re-enable buttons and clear the busy state.
  - **`_analyze(self)`** (Line 1667): Handle analyze for the page widgets and worker state.
  - **`_on_analyzed(self, analysis, leftovers)`** (Line 1676): Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.
  - **`_clean(self)`** (Line 1731): Clean via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_cleaned(self, outcome)`** (Line 1757): Handle worker results: note status, re-enable buttons and clear the busy state.
  - **`_run_task(self)`** (Line 1781): Handle run task for the page widgets and worker state.
  - **`_on_task(self, ok, message)`** (Line 1798): Handle worker results: note status, re-enable buttons and clear the busy state.
  - **`_fix_24h2(self)`** (Line 1809): Fix Windows 11 24H2 stuck staged packages using ComponentStoreCleaner.
  - **`_delete_leftovers(self)`** (Line 1835): Handle delete leftovers for the page widgets and worker state.
  - **`_on_deleted(self, freed, removed, blocked)`** (Line 1867): Handle worker results: note status and clear the busy state.
  - **`_fail(self, msg)`** (Line 1879): Report the worker error in the state panel, re-enable actions and clear the busy state.

### Module `src/cortex_unified/ui/premium/apex_tools_pages.py`
#### Class `DriverStoreCleanerPage`
*Page for enumerating, exporting, and deleting superseded driver packages.*

- **Inherits From**: `_Page`
- **Source Line**: 91
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 93): Build the Driver Store page with enumerate/export/delete buttons and a drivers table.
  - **`_on_scan(self)`** (Line 135): Enumerate driver packages on the worker runtime.
  - **`_on_export(self)`** (Line 162): Pick a folder and export all drivers into it.
  - **`_on_delete_superseded(self)`** (Line 172): Confirm and force-delete all superseded driver packages, then rescan.

#### Class `ShellbagsCleanerPage`
*Page for purging Shellbags, Recent Items, and JumpLists activity traces.*

- **Inherits From**: `_Page`
- **Source Line**: 198
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 200): Build the Shellbags page with scan/clean buttons and a traces table.
  - **`_on_scan(self)`** (Line 236): Scan shell activity traces on the worker runtime.
  - **`_on_clean(self)`** (Line 258): Confirm and purge all discovered activity traces, then rescan.

#### Class `PowerPlanOptimizerPage`
*Page for unlocking Ultimate Performance and reducing the hibernation footprint.*

- **Inherits From**: `_Page`
- **Source Line**: 279
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 281): Build the Power Plan page with status line, refresh/unlock/hibernate buttons, and a schemes table.
  - **`_refresh(self)`** (Line 323): Refresh the active scheme status and the power plans table.
  - **`_on_unlock_ultimate(self)`** (Line 340): Unlock the hidden Ultimate Performance power plan, then refresh.
  - **`_on_reduce_hiber(self)`** (Line 349): Shrink the hibernation file to 40% of RAM, then refresh.

#### Class `HostsFileManagerPage`
*Page for inspecting the hosts file and applying an anti-telemetry shield.*

- **Inherits From**: `_Page`
- **Source Line**: 363
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 365): Build the Hosts page with reload/shield buttons and an entries table.
  - **`_on_load(self)`** (Line 400): Parse the hosts file and list its entries.
  - **`_on_apply_shield(self)`** (Line 410): Confirm and add telemetry blocking entries to the hosts file, then reload.

#### Class `NotificationCleanerPage`
*Page for purging the Action Center notification database and badge caches.*

- **Inherits From**: `_Page`
- **Source Line**: 430
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 432): Build the Notification Cleaner page with status line and refresh/clean buttons.
  - **`_refresh(self)`** (Line 461): Refresh the notification database paths and sizes.
  - **`_on_clean(self)`** (Line 471): Confirm and purge notification history and badges, then refresh.

#### Class `FileSignatureSnifferPage`
*Page for detecting spoofed file extensions via magic-byte sniffing.*

- **Inherits From**: `_Page`
- **Source Line**: 491
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 493): Build the Signature Sniffer page with folder picker, spoof filter, and results table.
  - **`_on_choose_folder(self)`** (Line 533): Pick the directory to sniff.
  - **`_on_scan(self)`** (Line 539): Scan the chosen folder recursively for spoofed files.

#### Class `BinaryDifferPage`
*Page for byte-level comparison of two binary files.*

- **Inherits From**: `_Page`
- **Source Line**: 573
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 575): Build the Binary Differ page with File A/B pickers, compare button, and a hex diff table.
  - **`_on_select_a(self)`** (Line 628): Pick the first file to compare.
  - **`_on_select_b(self)`** (Line 635): Pick the second file to compare.
  - **`_on_diff(self)`** (Line 642): Compare the two chosen files in the background.

#### Class `UsnJournalPage`
*Page for querying the NTFS USN change journal of a volume.*

- **Inherits From**: `_Page`
- **Source Line**: 683
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 685): Build the USN Journal page with volume combo, query button, and an info label.
  - **`_on_query(self)`** (Line 716): Query the selected volume's USN journal and show its state.

#### Class `Par2RecoveryPage`
*Page for inspecting PAR2 recovery sets and their protected files.*

- **Inherits From**: `_Page`
- **Source Line**: 737
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 739): Build the PAR2 page with an open button, summary label, and protected-files table.
  - **`_on_open_par2(self)`** (Line 772): Open and parse a .par2 file, listing its recovery set and protected files.

#### Class `ImageOptimizerPage`
*Page for batch-compressing images and transcoding to WebP.*

- **Inherits From**: `_Page`
- **Source Line**: 800
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 802): Build the Image Optimizer page with picker, format/quality controls, and results table.
  - **`_on_add_images(self)`** (Line 858): Pick images to optimize and show the selection count.
  - **`_on_start(self)`** (Line 865): Run batch optimization with the chosen format and quality.

### Module `src/cortex_unified/ui/premium/audio_duplicates_page.py`
#### Class `_AudioWorker`
*_AudioWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 26
- **Key Methods & Handlers**:
  - **`__init__(self, root, threshold)`** (Line 32): __init__.
  - **`cancel(self)`** (Line 41): cancel.
  - **`run(self)`** (Line 45): run.

#### Class `AudioDuplicatesPage`
*Find acoustically-identical audio files (same recording, any encoding).*

- **Inherits From**: `_Page`
- **Source Line**: 60
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 63): __init__.
  - **`_pick(self)`** (Line 120): _pick.
  - **`_run(self)`** (Line 129): _run.
  - **`_on_progress(self, msg)`** (Line 140): _on_progress.
  - **`_on_done(self, groups)`** (Line 144): _on_done.
  - **`_fail(self, msg)`** (Line 177): _fail.

### Module `src/cortex_unified/ui/premium/bad_files_studio_page.py`
#### Class `_BadFilesScanWorker`
*Scan for bad files or EXIF metadata off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 36
- **Key Methods & Handlers**:
  - **`__init__(self, mode, folder)`** (Line 41): Event handler or worker task method.
  - **`run(self)`** (Line 46): Event handler or worker task method.

#### Class `BadFilesStudioPage`
*Studio for detecting bad extensions, invalid filenames, and EXIF privacy scrubbing.*

- **Inherits From**: `_Page`
- **Source Line**: 88
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 91): Event handler or worker task method.
  - **`_on_tool_changed(self, idx)`** (Line 169): Event handler or worker task method.
  - **`_pick_folder(self)`** (Line 179): Event handler or worker task method.
  - **`_scan(self)`** (Line 185): Event handler or worker task method.
  - **`_on_done(self, results)`** (Line 193): Event handler or worker task method.
  - **`_strip_exif(self)`** (Line 216): Event handler or worker task method.
  - **`_fail(self, err)`** (Line 238): Event handler or worker task method.

### Module `src/cortex_unified/ui/premium/cdc_page.py`
#### Class `_CdcWorker`
*_CdcWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 25
- **Key Methods & Handlers**:
  - **`__init__(self, root, threshold)`** (Line 31): __init__.
  - **`cancel(self)`** (Line 40): cancel.
  - **`run(self)`** (Line 44): run.

#### Class `CdcPage`
*Find shift-resistant near-duplicates via CDC chunk sets.*

- **Inherits From**: `_Page`
- **Source Line**: 59
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 62): __init__.
  - **`_pick(self)`** (Line 119): _pick.
  - **`_run(self)`** (Line 128): _run.
  - **`_on_progress(self, msg)`** (Line 139): _on_progress.
  - **`_on_done(self, groups)`** (Line 143): _on_done.
  - **`_fail(self, msg)`** (Line 176): _fail.

### Module `src/cortex_unified/ui/premium/cleanup_hub_page.py`
#### Class `HubScanWorker`
*Scans all cleanup categories via CleanerService.

Emits ``finished`` with a CleanupReport, ``progress`` with status text,
or ``failed`` with an error message.*

- **Inherits From**: `QObject`
- **Source Line**: 48
- **Key Methods & Handlers**:
  - **`__init__(self, max_risk, include_disabled)`** (Line 58): Store max-risk level, disabled-category flag, and a cancel event.
  - **`cancel(self)`** (Line 66): Request cooperative cancellation of the running scan.
  - **`run(self)`** (Line 70): Run the category scan and emit the report or a failure.

#### Class `TempScanWorker`
*Scans stale temp files via TempCleaner (core/temp_cleaner.py).

Emits ``finished`` with a list of TempFinding, ``progress`` with status
text, or ``failed`` with an error message.*

- **Inherits From**: `QObject`
- **Source Line**: 84
- **Key Methods & Handlers**:
  - **`__init__(self, min_age_days)`** (Line 94): Store the age floor and a cancel event (TempCleaner walks anyway).
  - **`cancel(self)`** (Line 101): Request cooperative cancellation of the running scan.
  - **`run(self)`** (Line 105): Run the stale-temp scan and emit findings or a failure.

#### Class `CleanupHubPage`
*Storage Sense-style hub: every CleanupCategory as a card with estimates.*

- **Inherits From**: `_Page`
- **Source Line**: 141
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 144): Build the Cleanup Hub: scan controls, summary cards, and a card grid.
  - **`_scan(self)`** (Line 288): Disable buttons and start a HubScanWorker (risk level from opt-in checkbox).
  - **`_on_progress(self, msg)`** (Line 300): Show worker progress text in the scan status label.
  - **`_on_scanned(self, report)`** (Line 304): Update summary cards and rebuild the category card grid from the scan report.
  - **`_make_card(self, cat, est_bytes, est_files)`** (Line 357): Build one category card: risk/reversible badges, paths, globs, estimate, and select checkbox.
  - **`_select_all_cards(self, state)`** (Line 424): Check or uncheck every category card checkbox at once.
  - **`_update_clean_enabled(self)`** (Line 431): Enable the Clean button only when something is selected and a scan has files.
  - **`_fail(self, msg)`** (Line 437): Reset UI state after a failed scan/clean and offer retry.
  - **`_scan_temp(self)`** (Line 445): Start a TempScanWorker (stale-temp scan+clean backend) via run_worker.
  - **`_on_temp_scanned(self, findings)`** (Line 453): Show stale-temp totals (count + bytes) in status + info dialog.
  - **`_on_temp_failed(self, msg)`** (Line 465): Re-enable the temp button and surface the scan failure.
  - **`_pick_custom_folder(self)`** (Line 474): Add a chosen directory to the scan roots and rescan.
  - **`_pick_custom_file(self)`** (Line 484): Add the parent folder of a chosen file to the scan roots and rescan.
  - **`_clear_custom_roots(self)`** (Line 494): Remove all custom scan roots (back to system defaults) and rescan.
  - **`_update_roots_status(self)`** (Line 500): Refresh the active-scan-roots label and Reset Roots button visibility.
  - **`_clean(self)`** (Line 512): Confirm selection, then run CleanWorker on the selected categories (Recycle-Bin-safe delete).
  - **`_on_cleaned(self, freed, items, skipped)`** (Line 546): Report freed bytes and item counts after cleanup finishes.

### Module `src/cortex_unified/ui/premium/cloud_storage_page.py`
#### Class `_WorkerResult`
*_WorkerResult class.*

- **Inherits From**: `object`
- **Source Line**: 47
- **Key Methods & Handlers**:

#### Class `_CloudWorker`
*_CloudWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 54
- **Key Methods & Handlers**:
  - **`__init__(self, target, max_objects, include_versions, include_delete_markers)`** (Line 60): Initialize worker.
  - **`cancel(self)`** (Line 75): cancel.
  - **`run(self)`** (Line 79): run.

#### Class `CloudStoragePage`
*Analyze cloud storage (S3, Azure, GDrive, OneDrive, rclone).*

- **Inherits From**: `_Page`
- **Source Line**: 94
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 97): __init__.
  - **`_build_summary_tab(self)`** (Line 192): _build_summary_tab.
  - **`_build_by_provider_tab(self)`** (Line 227): _build_by_provider_tab.
  - **`_build_by_class_tab(self)`** (Line 243): _build_by_class_tab.
  - **`_build_duplicates_tab(self)`** (Line 259): _build_duplicates_tab.
  - **`_refresh_targets(self)`** (Line 282): _refresh_targets.
  - **`_run(self)`** (Line 304): _run.
  - **`_on_progress(self, msg)`** (Line 333): _on_progress.
  - **`_on_done(self, result)`** (Line 337): _on_done.
  - **`_fail(self, msg)`** (Line 372): _fail.
  - **`_populate_summary(self, stats)`** (Line 379): _populate_summary.
  - **`_populate_by_provider(self, stats)`** (Line 409): _populate_by_provider.
  - **`_populate_by_class(self, stats)`** (Line 424): _populate_by_class.
  - **`_populate_duplicates(self, duplicates)`** (Line 466): _populate_duplicates.
  - **`_build_providers_tab(self)`** (Line 482): Build the interactive Cloud Providers tab with connect/disconnect/browse actions.
  - **`_init_providers_table(self)`** (Line 557): Populate the cloud providers table with connect/disconnect/browse controls.
  - **`_connect_provider(self, pt)`** (Line 599): Attempt connection to selected provider.
  - **`_disconnect_provider(self, pt)`** (Line 612): Disconnect provider.
  - **`_select_provider_for_browse(self, pt)`** (Line 618): Select provider and browse remote path.
  - **`_on_browse_cloud_path(self)`** (Line 624): Browse files in current provider path.
  - **`_on_download_cloud_file(self)`** (Line 663): Download selected cloud file.
  - **`_on_cloud_file_double_clicked(self, row, col)`** (Line 687): Navigate into folder on double click.

### Module `src/cortex_unified/ui/premium/compact_os_page.py`
#### Class `_ScanWorker`
*_ScanWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 35
- **Key Methods & Handlers**:
  - **`__init__(self, root, min_mb)`** (Line 41): __init__.
  - **`cancel(self)`** (Line 50): cancel.
  - **`run(self)`** (Line 54): run.

#### Class `_CompactWorker`
*_CompactWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 67
- **Key Methods & Handlers**:
  - **`__init__(self, path)`** (Line 72): __init__.
  - **`run(self)`** (Line 77): run.

#### Class `_QueryWorker`
*_QueryWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 88
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 93): run.

#### Class `CompactOsPage`
*Estimate and apply NTFS compression to reclaim storage.*

- **Inherits From**: `_Page`
- **Source Line**: 106
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 109): __init__.
  - **`_pick(self)`** (Line 190): _pick.
  - **`_query(self)`** (Line 199): _query.
  - **`_on_query(self, info)`** (Line 205): _on_query.
  - **`_scan(self)`** (Line 213): _scan.
  - **`_on_progress(self, msg)`** (Line 223): _on_progress.
  - **`_on_done(self, ests)`** (Line 227): _on_done.
  - **`_compress(self)`** (Line 251): _compress.
  - **`_compact_done(self, success, message)`** (Line 273): _compact_done.
  - **`_fail(self, msg)`** (Line 283): _fail.

### Module `src/cortex_unified/ui/premium/delivery_optimization_page.py`
#### Class `_DeliveryScanWorker`
*Scan Delivery Optimization cache status off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 30
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 35): Event handler or worker task method.

#### Class `_DeliveryCleanWorker`
*Purge Delivery Optimization cache off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 46
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 51): Event handler or worker task method.

#### Class `DeliveryOptimizationPage`
*Windows Delivery Optimization cache auditor and sanitizer.*

- **Inherits From**: `_Page`
- **Source Line**: 62
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 65): Event handler or worker task method.
  - **`_scan(self)`** (Line 143): Event handler or worker task method.
  - **`_on_scan_done(self, status)`** (Line 151): Event handler or worker task method.
  - **`_confirm_clean(self)`** (Line 173): Event handler or worker task method.
  - **`_clean(self)`** (Line 188): Event handler or worker task method.
  - **`_on_clean_done(self, report)`** (Line 196): Event handler or worker task method.
  - **`_fail(self, err)`** (Line 205): Event handler or worker task method.

### Module `src/cortex_unified/ui/premium/device_window.py`
#### Class `DeviceDeepScanWorker`
*Audit one authorized private host and gather its evidence.*

- **Inherits From**: `QObject`
- **Source Line**: 73
- **Key Methods & Handlers**:
  - **`__init__(self, device, networks, profile, custom_ports, nmap_modes, catalog_path)`** (Line 80): Store the device snapshot, authorized networks, and scan options for the worker.
  - **`cancel(self)`** (Line 107): Request cancellation of the running scan.
  - **`_say(self, message)`** (Line 111): Emit a progress message.
  - **`run(self)`** (Line 115): Re-check authorization, scan services, fingerprint, audit, and emit the evidence payload.
  - **`_run_nmap(self, observations, notes)`** (Line 219): Optionally verify observed TCP ports with local Nmap; merge new observations.
  - **`_ping(self)`** (Line 273): Ping the device twice and return the reachability dict.
  - **`_reverse_dns(self)`** (Line 287): Resolve the device IP to a hostname.
  - **`_history(self, device)`** (Line 295): Load inventory metadata, lifetime, and exposure trends for the device.

#### Class `DevicePingWorker`
*Run only a scope-checked ICMP reachability check for one device.*

- **Inherits From**: `QObject`
- **Source Line**: 327
- **Key Methods & Handlers**:
  - **`__init__(self, ip, networks)`** (Line 334): Store the target IP, authorized networks, and cancel event.
  - **`cancel(self)`** (Line 341): Request cancellation of the ping check.
  - **`run(self)`** (Line 345): Re-check authorization and emit an ICMP reachability result.

### Module `src/cortex_unified/ui/premium/directstorage_page.py`
#### Class `_DirectStorageWorker`
*_DirectStorageWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 34
- **Key Methods & Handlers**:
  - **`__init__(self, optimizer)`** (Line 38): __init__.
  - **`run_audit(self)`** (Line 43): run_audit.

#### Class `DirectStorageOptimizerPage`
*UI diagnostics page for DirectStorage BypassIO hardware acceleration.*

- **Inherits From**: `_Page`
- **Source Line**: 49
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 52): __init__.
  - **`_start_audit(self)`** (Line 117): _start_audit.
  - **`_on_audit_finished(self, report)`** (Line 130): _on_audit_finished.

### Module `src/cortex_unified/ui/premium/disk_analyzer_page.py`
#### Class `_ScanWorker`
*Background worker: scans a path via AdvancedDiskAnalyzer.scan_sync.*

- **Inherits From**: `QObject`
- **Source Line**: 42
- **Key Methods & Handlers**:
  - **`__init__(self, root, max_depth)`** (Line 49): __init__.
  - **`cancel(self)`** (Line 56): cancel.
  - **`run(self)`** (Line 60): run.

#### Class `DiskAnalyzerPage`
*Advanced disk analyzer: fast scan, treemap, folder breakdown by size.*

- **Inherits From**: `_Page`
- **Source Line**: 138
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 141): __init__.
  - **`_populate_drives(self)`** (Line 276): _populate_drives.
  - **`_on_drive_changed(self, idx)`** (Line 285): _on_drive_changed.
  - **`_browse(self)`** (Line 292): _browse.
  - **`_run(self)`** (Line 305): _run.
  - **`_on_progress(self, msg)`** (Line 324): _on_progress.
  - **`_on_done(self, result)`** (Line 328): _on_done.
  - **`_fail(self, msg)`** (Line 419): _fail.
  - **`_export_sunburst(self)`** (Line 426): Export current disk analysis tree as an interactive Sunburst HTML chart.
  - **`_export_treemap(self)`** (Line 445): Export current disk analysis tree as an interactive TreeMap HTML chart.

### Module `src/cortex_unified/ui/premium/driver_manager_page.py`
#### Class `_ScanWorker`
*Enumerate devices and check for driver updates.*

- **Inherits From**: `QObject`
- **Source Line**: 56
- **Key Methods & Handlers**:
  - **`__init__(self, offline_mode, index_path)`** (Line 63): Store offline-mode flag, optional index path, and a cancel event.
  - **`cancel(self)`** (Line 70): Request cooperative cancellation of the running scan.
  - **`run(self)`** (Line 74): Enumerate PnP devices via DriverManager and emit the driver list.

#### Class `_InstallWorker`
*Install driver updates for selected hardware IDs.*

- **Inherits From**: `QObject`
- **Source Line**: 92
- **Key Methods & Handlers**:
  - **`__init__(self, hardware_ids, offline_mode)`** (Line 99): Store target hardware IDs, offline flag, and a cancel event.
  - **`cancel(self)`** (Line 106): Request cooperative cancellation of the running install.
  - **`run(self)`** (Line 110): Install updates for the stored hardware IDs (restore point first).

#### Class `_BackupWorker`
*Back up all current drivers via DISM export.*

- **Inherits From**: `QObject`
- **Source Line**: 127
- **Key Methods & Handlers**:
  - **`__init__(self)`** (Line 134): Create the backup worker with a fresh cancel event.
  - **`cancel(self)`** (Line 139): No-op cancel hook (DISM export cannot be interrupted).
  - **`run(self)`** (Line 143): Export all drivers via DISM into ~/CortexBackups/drivers.

#### Class `DriverManagerPage`
*Scan, update, backup and manage device drivers.*

- **Inherits From**: `_Page`
- **Source Line**: 175
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 178): Build the Driver Manager page: filter, action buttons, progress, and results table.
  - **`_selected_hwids(self)`** (Line 268): Return hardware IDs of the currently selected table rows.
  - **`_populate_table(self, drivers)`** (Line 273): Fill the results table (class-filtered), flag outdated/missing, and enable Install if any outdated.
  - **`_scan(self)`** (Line 310): Clear the table and start a _ScanWorker for devices and update checks.
  - **`_on_progress(self, msg)`** (Line 327): Show worker progress text in the status label.
  - **`_on_scan_done(self, drivers)`** (Line 331): Populate the table with scan results and summarize outdated/missing counts.
  - **`_on_scan_fail(self, msg)`** (Line 356): Reset buttons and show the scan error with a retry option.
  - **`_install(self)`** (Line 363): Confirm selection, then run _InstallWorker for the selected hardware IDs.
  - **`_on_install_done(self, results)`** (Line 399): Report per-ID success/failure counts and show errors if any install failed.
  - **`_on_install_fail(self, msg)`** (Line 420): Reset buttons and show the install error with a retry option.
  - **`_backup(self)`** (Line 428): Disable Backup and run _BackupWorker to DISM-export all drivers.
  - **`_on_backup_done(self, path)`** (Line 440): Re-enable Backup and report the export directory.
  - **`_on_backup_fail(self, msg)`** (Line 448): Re-enable Backup and show the export error with a retry option.

### Module `src/cortex_unified/ui/premium/enterprise_suite_pages.py`
#### Class `VssManagerPage`
*Page for auditing VSS shadow copies, creating snapshots, and purging the oldest shadow.*

- **Inherits From**: `_Page`
- **Source Line**: 96
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 98): Build the VSS page with audit/create/purge buttons, summary label, and shadows table.
  - **`_on_audit(self)`** (Line 138): Start an asynchronous VSS audit and show a busy message in the summary label.
  - **`_on_audit_done(self, rep)`** (Line 143): Populate the shadows table and summary from a VssAuditReport.
  - **`_on_create(self)`** (Line 159): Kick off creation of a recovery shadow copy on C: in the background.
  - **`_on_purge(self)`** (Line 164): Kick off deletion of the oldest shadow copy on C: in the background.
  - **`_on_action_done(self, res)`** (Line 169): Show the result message of a create/purge action, then refresh the audit.
  - **`_on_err(self, exc)`** (Line 175): Show an error message from a failed worker in the summary label.

#### Class `DevDriveOptimizerPage`
*Page for auditing ReFS Dev Drives, block-cloning support, and Defender performance mode.*

- **Inherits From**: `_Page`
- **Source Line**: 184
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 186): Build the Dev Drive page with an audit button, summary label, and drives table.
  - **`_on_audit(self)`** (Line 220): Start an asynchronous storage-drive audit and update the summary label.
  - **`_on_audit_done(self, rep)`** (Line 225): Fill the drives table and summary from a DevDriveAuditReport.
  - **`_on_err(self, exc)`** (Line 244): Show an error message from a failed worker in the summary label.

#### Class `BitLockerAuditorPage`
*Page for auditing volume BitLocker protection, cipher strength, and key protectors.*

- **Inherits From**: `_Page`
- **Source Line**: 253
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 255): Build the BitLocker page with an audit button, summary label, and volumes table.
  - **`_on_audit(self)`** (Line 289): Start an asynchronous BitLocker audit and update the summary label.
  - **`_on_audit_done(self, rep)`** (Line 294): Fill the volumes table and compliance summary from a BitLockerAuditReport.
  - **`_on_err(self, exc)`** (Line 312): Show an error message from a failed worker in the summary label.

#### Class `JunctionAuditorPage`
*Page for scanning NTFS junctions, symlinks, dead links, and circular reparse traps.*

- **Inherits From**: `_Page`
- **Source Line**: 321
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 323): Build the Junction Auditor page with scan/custom/unlink buttons and a links table.
  - **`_on_scan(self)`** (Line 364): Scan reparse points across the user profile in the background.
  - **`_on_custom(self)`** (Line 369): Prompt for a folder and scan its reparse points in the background.
  - **`_on_scan_done(self, rep)`** (Line 376): Fill the links table and counters from a JunctionAuditReport.
  - **`_on_clean_dead(self)`** (Line 394): Unlink the dead junction selected in the table, then rescan.
  - **`_on_err(self, exc)`** (Line 405): Show an error message from a failed worker in the summary label.

#### Class `BitRotScrubberPage`
*Page for detecting silent bit-rot by comparing files against a SHA-256 baseline.*

- **Inherits From**: `_Page`
- **Source Line**: 414
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 416): Build the BitRot page with a target picker, scrub button, and corrupted-files table.
  - **`_on_browse(self)`** (Line 454): Open a directory picker and set it as the scrub target.
  - **`_on_scrub(self)`** (Line 460): Hash and scrub the chosen folder in the background.
  - **`_on_scrub_done(self, rep)`** (Line 468): Show scrub statistics and list corrupted files from a BitRotScrubReport.
  - **`_on_err(self, exc)`** (Line 484): Show an error message from a failed worker in the summary label.

#### Class `MemoryCompressionPage`
*Page for auditing Windows memory compression and toggling it on or off.*

- **Inherits From**: `_Page`
- **Source Line**: 493
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 495): Build the Memory Compression page with audit/toggle buttons and a metrics table.
  - **`_on_audit(self)`** (Line 530): Query MMAgent memory status in the background.
  - **`_on_audit_done(self, rep)`** (Line 535): Fill the metrics table from a MemoryTunerReport and remember the current status.
  - **`_on_toggle(self)`** (Line 561): Flip the memory-compression state to the opposite of the audited status.
  - **`_on_toggle_done(self, res)`** (Line 569): Report the toggle result, then re-run the audit.
  - **`_on_err(self, exc)`** (Line 575): Show an error message from a failed worker in the summary label.

#### Class `SandboxCleanerPage`
*Page for finding and purging Windows Sandbox, Hyper-V, and WSL2 artifacts.*

- **Inherits From**: `_Page`
- **Source Line**: 584
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 586): Build the Sandbox Cleaner page with scan/clean buttons and an artifacts table.
  - **`_on_scan(self)`** (Line 624): Scan for discarded virtualization artifacts in the background.
  - **`_on_scan_done(self, rep)`** (Line 629): Cache the artifact list and fill the table from a SandboxCleanReport.
  - **`_on_clean(self)`** (Line 643): Purge every artifact flagged safe to clean; warn when none exist.
  - **`_on_clean_done(self, res)`** (Line 653): Report reclaimed bytes, then rescan for remaining artifacts.
  - **`_on_err(self, exc)`** (Line 659): Show an error message from a failed worker in the summary label.

#### Class `SmbShareAuditorPage`
*Page for auditing local SMB shares, admin shares, and SMBv1 exposure.*

- **Inherits From**: `_Page`
- **Source Line**: 668
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 670): Build the SMB Auditor page with an audit button, summary label, and shares table.
  - **`_on_audit(self)`** (Line 703): Start an asynchronous SMB share audit and update the summary label.
  - **`_on_audit_done(self, rep)`** (Line 708): Fill the shares table and risk summary from a SmbSecurityReport.
  - **`_on_err(self, exc)`** (Line 726): Show an error message from a failed worker in the summary label.

#### Class `ProcessTokenPage`
*Page for inspecting process token integrity levels, elevation, and privileges.*

- **Inherits From**: `_Page`
- **Source Line**: 735
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 737): Build the Process Token page with an audit button, summary label, and processes table.
  - **`_on_audit(self)`** (Line 771): Start an asynchronous process token audit and update the summary label.
  - **`_on_audit_done(self, rep)`** (Line 776): Fill the processes table and privilege summary from a ProcessTokenAuditReport.
  - **`_on_err(self, exc)`** (Line 794): Show an error message from a failed worker in the summary label.

#### Class `StorageGrowthTrackerPage`
*Page for taking directory snapshots and diffing storage growth between them.*

- **Inherits From**: `_Page`
- **Source Line**: 803
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 805): Build the Growth Tracker page with path picker, snapshot/diff buttons, and a growth table.
  - **`_on_browse(self)`** (Line 848): Open a directory picker and set it as the snapshot target.
  - **`_on_snapshot(self)`** (Line 854): Capture a storage snapshot of the entered path in the background.
  - **`_on_snapshot_done(self, s)`** (Line 862): Show the captured snapshot id, label, and total footprint.
  - **`_on_diff(self)`** (Line 868): Compare the two most recent snapshots, or prompt if fewer exist.
  - **`_on_diff_done(self, rep)`** (Line 880): Show net growth between snapshots and list the fastest-growing directories.
  - **`_on_err(self, exc)`** (Line 898): Show an error message from a failed worker in the summary label.

### Module `src/cortex_unified/ui/premium/expanded_tools_pages.py`
#### Class `LinksManagerPage`
*Page for scanning and safely removing NTFS junctions, symlinks, and hardlinks.*

- **Inherits From**: `_Page`
- **Source Line**: 89
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 91): Build the Links Manager page with folder picker, recursive option, and links table.
  - **`_on_choose_folder(self)`** (Line 142): Open a directory picker and remember it as the scan target.
  - **`_on_scan(self)`** (Line 149): Scan the chosen directory (or home) for links on the worker runtime.
  - **`_on_remove_link(self)`** (Line 176): Confirm and remove the selected link without touching its target files.

#### Class `FastCopierPage`
*Page for high-throughput multi-threaded file transfer with verification modes.*

- **Inherits From**: `_Page`
- **Source Line**: 202
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 204): Build the Fast Copier page with source/destination pickers, mode combo, and progress bar.
  - **`_on_add_source(self)`** (Line 273): Append a picked source directory to the copy list.
  - **`_on_choose_dest(self)`** (Line 280): Pick the destination directory for the batch copy.
  - **`_on_start_copy(self)`** (Line 287): Run the batch copy in the background with the chosen mode and speed limit.

#### Class `TimestampTouchPage`
*Page for inspecting and stomping MACB timestamps and Win32 file attributes.*

- **Inherits From**: `_Page`
- **Source Line**: 333
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 335): Build the Timestamp Touch page with file picker, datetime editors, and attribute checkboxes.
  - **`_on_choose_files(self)`** (Line 417): Pick files and preload the first file's timestamps and attributes into the editors.
  - **`_on_apply(self)`** (Line 434): Apply the chosen timestamps and attributes to every selected file.

#### Class `ArchiveManagerPage`
*Page for creating, inspecting, testing, and extracting multi-format archives.*

- **Inherits From**: `_Page`
- **Source Line**: 460
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 462): Build the Archive Studio page with open/test/extract/create buttons and a contents table.
  - **`_on_open_archive(self)`** (Line 511): Open an archive and list its entries in the table.
  - **`_on_test_archive(self)`** (Line 525): Run an integrity test on the currently opened archive.
  - **`_on_extract_archive(self)`** (Line 537): Extract the opened archive into a chosen destination folder.
  - **`_on_create_archive(self)`** (Line 551): Pick files and a target name, then build a new archive.

#### Class `PrefetchAnalyzerPage`
*Page for analyzing and flushing Windows Prefetch execution traces.*

- **Inherits From**: `_Page`
- **Source Line**: 571
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 573): Build the Prefetch page with status line, scan/clean buttons, and a traces table.
  - **`_refresh_status(self)`** (Line 613): Refresh the prefetch cache size, SysMain state, and privilege line.
  - **`_on_scan(self)`** (Line 622): Scan prefetch trace files on the worker runtime.
  - **`_on_clean(self)`** (Line 645): Confirm and flush all prefetch traces, then rescan.

#### Class `SearchIndexOptimizerPage`
*Page for compacting and rebuilding the Windows Search index database.*

- **Inherits From**: `_Page`
- **Source Line**: 662
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 664): Build the Search Index page with status card and compact/rebuild buttons.
  - **`_refresh(self)`** (Line 699): Refresh the database path, size, item estimate, and service status.
  - **`_on_compact(self)`** (Line 710): Confirm and run offline ESENT compaction in the background.
  - **`_on_rebuild(self)`** (Line 735): Confirm and trigger a full search-index rebuild.

#### Class `DnsBenchmarkPage`
*Page for benchmarking DNS provider latency and applying the chosen resolver.*

- **Inherits From**: `_Page`
- **Source Line**: 752
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 754): Build the DNS Benchmark page with run/apply buttons and a results table.
  - **`_on_benchmark(self)`** (Line 792): Run the full DNS benchmark on the worker runtime.
  - **`_on_apply_dns(self)`** (Line 820): Apply the selected provider's DNS servers to Wi-Fi, falling back to Ethernet.

#### Class `DiskBenchmarkPage`
*Page for measuring sequential throughput and 4K random IOPS.*

- **Inherits From**: `_Page`
- **Source Line**: 843
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 845): Build the Disk Benchmark page with target picker, progress label, and results table.
  - **`_on_select_target(self)`** (Line 895): Pick the drive or folder to benchmark.
  - **`_on_start_bench(self)`** (Line 902): Run a 64 MB storage benchmark on the target in the background.

#### Class `MemoryOptimizerPage`
*Page for inspecting RAM usage and trimming process working sets.*

- **Inherits From**: `_Page`
- **Source Line**: 929
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 931): Build the RAM Optimizer page with summary line, process table, and trim button.
  - **`_on_refresh(self)`** (Line 969): Refresh the RAM summary and top-30 process memory table.
  - **`_on_trim(self)`** (Line 986): Trim background process working sets, then refresh.

#### Class `DevCleanerPage`
*Page for scanning and purging developer ecosystem build caches.*

- **Inherits From**: `_Page`
- **Source Line**: 997
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 999): Build the Dev Cleaner page with scan/clean buttons and a caches table.
  - **`_on_scan(self)`** (Line 1035): Scan developer caches on the worker runtime.
  - **`_on_clean(self)`** (Line 1057): Confirm and purge all discovered caches, then rescan.

#### Class `BrowserDeepCleanerPage`
*Page for scanning and purging caches across installed browsers.*

- **Inherits From**: `_Page`
- **Source Line**: 1078
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1080): Build the Browser Cleaner page with scan/clean buttons and a targets table.
  - **`_on_scan(self)`** (Line 1121): Scan browser caches on the worker runtime.
  - **`_on_clean(self)`** (Line 1143): Confirm and purge transient browser caches (logins preserved), then rescan.
  - **`_on_vacuum(self)`** (Line 1159): Find and VACUUM browser SQLite databases to compact and reclaim space.

### Module `src/cortex_unified/ui/premium/focus.py`
### Module `src/cortex_unified/ui/premium/fuzzy_hash_page.py`
#### Class `_FuzzyWorker`
*_FuzzyWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 26
- **Key Methods & Handlers**:
  - **`__init__(self, root, threshold)`** (Line 32): __init__.
  - **`cancel(self)`** (Line 41): cancel.
  - **`run(self)`** (Line 45): run.

#### Class `FuzzyHashPage`
*Find near-identical binaries via context-triggered piecewise hashing.*

- **Inherits From**: `_Page`
- **Source Line**: 60
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 63): __init__.
  - **`_pick(self)`** (Line 119): _pick.
  - **`_run(self)`** (Line 128): _run.
  - **`_on_progress(self, msg)`** (Line 139): _on_progress.
  - **`_on_done(self, groups)`** (Line 143): _on_done.
  - **`_fail(self, msg)`** (Line 176): _fail.

### Module `src/cortex_unified/ui/premium/game_mode_page.py`
#### Class `_GameModeQueryWorker`
*Query current power plan, support status, and suspend candidates.*

- **Inherits From**: `QObject`
- **Source Line**: 31
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 36): Run query off the UI thread.

#### Class `_GameModeActionWorker`
*Start or stop boosted gaming mode.*

- **Inherits From**: `QObject`
- **Source Line**: 47
- **Key Methods & Handlers**:
  - **`__init__(self, action, game_mode_instance)`** (Line 52): Event handler or worker task method.
  - **`run(self)`** (Line 57): Run start or stop off UI thread.

#### Class `GameModePage`
*One-click gaming session booster with reversible process suspension.*

- **Inherits From**: `_Page`
- **Source Line**: 72
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 75): Event handler or worker task method.
  - **`_query(self)`** (Line 151): Query current state and candidates.
  - **`_on_query_done(self, preview)`** (Line 158): Event handler or worker task method.
  - **`_toggle_boost(self)`** (Line 180): Start or stop boost.
  - **`_start_boost(self)`** (Line 187): Event handler or worker task method.
  - **`_on_boost_started(self, result)`** (Line 195): Event handler or worker task method.
  - **`_stop_boost(self)`** (Line 213): Event handler or worker task method.
  - **`_on_boost_stopped(self, result)`** (Line 219): Event handler or worker task method.
  - **`_fail(self, err)`** (Line 232): Event handler or worker task method.

### Module `src/cortex_unified/ui/premium/license_page.py`
#### Class `LicensePage`
*Show this machine's license state and manage its lifecycle.*

- **Inherits From**: `_Page`
- **Source Line**: 47
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 50): __init__.
  - **`_refresh(self)`** (Line 145): Project the live license state onto every control.

Validation is memoised by the manager (keyed to the license file), so
calling this after every action is effectively free.
  - **`_fill_table(self, state)`** (Line 180): One row per feature, grouped by minimum tier then name.

The 'Included' column is plain text ('Yes' or an em-dash) rather than
check glyphs: Qt 6 ships no fonts, so codepoints rendered as colour
emoji or tofu boxes depending on the machine.
  - **`_activate(self)`** (Line 198): Install the entered key. Bad input warns instead of crashing.
  - **`_start_trial(self)`** (Line 219): Start the once-per-machine PRO trial.
  - **`_deactivate(self)`** (Line 234): Remove the local license after an explicit confirmation.

### Module `src/cortex_unified/ui/premium/log_sweeper_page.py`
#### Class `_LogWorker`
*_LogWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 36
- **Key Methods & Handlers**:
  - **`__init__(self, roots, min_mb)`** (Line 42): __init__.
  - **`cancel(self)`** (Line 51): cancel.
  - **`run(self)`** (Line 55): run.

#### Class `LogSweeperPage`
*Find large logs outside the default cache roots.*

- **Inherits From**: `_Page`
- **Source Line**: 73
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 76): __init__.
  - **`_add_root(self)`** (Line 176): _add_root.
  - **`_discover_code_roots(self)`** (Line 186): Discover common code root directories across all fixed drives.
  - **`_select_code_root(self)`** (Line 214): Open folder picker to select a code root directory.
  - **`_rm_root(self)`** (Line 225): _rm_root.
  - **`_scan(self)`** (Line 231): _scan.
  - **`_on_progress(self, msg)`** (Line 247): _on_progress.
  - **`_on_done(self, results)`** (Line 251): _on_done.
  - **`_delete(self)`** (Line 279): _delete.
  - **`_on_deleted(self, freed, ok, blocked)`** (Line 309): _on_deleted.
  - **`_fail(self, msg)`** (Line 320): _fail.

### Module `src/cortex_unified/ui/premium/memory_standby_page.py`
#### Class `MemoryStandbyPurgerPage`
*UI studio for Standby List and working set kernel optimization.*

- **Inherits From**: `_Page`
- **Source Line**: 34
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 37): __init__.
  - **`_refresh_stats(self)`** (Line 113): _refresh_stats.
  - **`_on_purge_standby(self)`** (Line 121): _on_purge_standby.
  - **`_on_empty_working_sets(self)`** (Line 126): _on_empty_working_sets.
  - **`_on_purge_modified(self)`** (Line 131): _on_purge_modified.
  - **`_on_purge_all(self)`** (Line 136): _on_purge_all.
  - **`_handle_result(self, res)`** (Line 152): _handle_result.

### Module `src/cortex_unified/ui/premium/mft_slack_page.py`
#### Class `_MftScrubWorker`
*_MftScrubWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 36
- **Key Methods & Handlers**:
  - **`__init__(self, scrubber)`** (Line 41): __init__.
  - **`run_audit(self)`** (Line 46): run_audit.
  - **`run_scrub(self)`** (Line 51): run_scrub.

#### Class `MftSlackScrubberPage`
*UI page for NTFS MFT record slack auditing and sanitization.*

- **Inherits From**: `_Page`
- **Source Line**: 57
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 60): __init__.
  - **`_on_volume_changed(self, vol)`** (Line 145): _on_volume_changed.
  - **`_start_audit(self)`** (Line 154): _start_audit.
  - **`_on_audit_finished(self, report)`** (Line 168): _on_audit_finished.
  - **`_start_scrub(self)`** (Line 194): _start_scrub.
  - **`_on_scrub_finished(self, report)`** (Line 218): _on_scrub_finished.

### Module `src/cortex_unified/ui/premium/model_cache_page.py`
#### Class `_ScanWorker`
*_ScanWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 35
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 40): run.

#### Class `_CleanOrphansWorker`
*_CleanOrphansWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 50
- **Key Methods & Handlers**:
  - **`__init__(self, dry_run)`** (Line 55): __init__.
  - **`run(self)`** (Line 60): run.

#### Class `ModelCachePage`
*Hardlink-aware model cache inventory + safe orphan cleanup.*

- **Inherits From**: `_Page`
- **Source Line**: 71
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 74): __init__.
  - **`_scan(self)`** (Line 145): _scan.
  - **`_on_scan(self, stores)`** (Line 153): _on_scan.
  - **`_clean(self, dry_run)`** (Line 200): _clean.
  - **`_on_clean(self, ok, msg, freed)`** (Line 222): _on_clean.
  - **`_fail(self, msg)`** (Line 233): _fail.

### Module `src/cortex_unified/ui/premium/more_pages.py`
#### Class `UpdaterListWorker`
*Worker that lists available app updates via AppUpdater.*

- **Inherits From**: `QObject`
- **Source Line**: 110
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 115): Execute the listing operation and emit results or failure.

#### Class `UpgradeWorker`
*Worker that applies upgrades for the given package IDs.*

- **Inherits From**: `QObject`
- **Source Line**: 124
- **Key Methods & Handlers**:
  - **`__init__(self, package_ids)`** (Line 129): Store the package IDs to upgrade.
  - **`run(self)`** (Line 134): Execute upgrades for all package IDs and emit results.

#### Class `DriveListWorker`
*Worker that lists drives via DriveOptimizer.*

- **Inherits From**: `QObject`
- **Source Line**: 148
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 153): Execute the drive listing operation and emit results.

#### Class `DriveOptimizeWorker`
*Worker that optimizes a specific drive.*

- **Inherits From**: `QObject`
- **Source Line**: 162
- **Key Methods & Handlers**:
  - **`__init__(self, letter)`** (Line 167): Store constructor arguments (letter) and initialize worker signals.
  - **`run(self)`** (Line 172): Execute drive optimization and emit success status and message.

#### Class `SystemInfoWorker`
*Worker that collects system information via SystemInfo.*

- **Inherits From**: `QObject`
- **Source Line**: 182
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 187): Execute system info collection and emit the snapshot dict.

#### Class `SoftwareUpdaterPage`
*List and apply app updates via winget.*

- **Inherits From**: `_Page`
- **Source Line**: 200
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 203): Initialize the Software Updater page.

Args:
    win: Parent window instance.
  - **`_load(self)`** (Line 265): Load and display available app updates.
  - **`_on_listed(self, apps)`** (Line 274): Handle the list of available updates from the worker.

Args:
    apps: List of app dicts returned by UpdaterListWorker.
  - **`_selected_ids(self)`** (Line 300): Return the package IDs of selected rows in the table.

Returns:
    List of package ID strings from selected rows.
  - **`_update_selected(self)`** (Line 309): Handle the 'Update Selected' button click.
  - **`_update_all(self)`** (Line 317): Handle the 'Update All' button click.
  - **`_run_updates(self, ids, prompt)`** (Line 322): Run upgrades for the given package IDs after user confirmation.

Args:
    ids: List of package IDs to upgrade.
    prompt: Confirmation dialog text.
  - **`_on_updated(self, ok, total)`** (Line 344): Handle completion of the upgrade operation.

Args:
    ok: Number of successfully updated packages.
    total: Total number of packages attempted.
  - **`_fail(self, msg)`** (Line 357): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `DriveOptimizerPage`
*Media-aware TRIM (SSD) / defrag (HDD) - never defragments an SSD.*

- **Inherits From**: `_Page`
- **Source Line**: 367
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 370): Initialize the Drive Optimizer page.

Args:
    win: Parent window instance.
  - **`_load(self)`** (Line 428): Load and display drive information.
  - **`_on_listed(self, drives)`** (Line 434): Handle the list of drives from the worker.

Args:
    drives: List of drive dicts returned by DriveListWorker.
  - **`_optimize(self)`** (Line 456): Handle the 'Optimize Selected' button click.
  - **`_on_done(self, success, message)`** (Line 478): Handle completion of the drive optimization.

Args:
    success: Whether the optimization succeeded.
    message: Result message from the worker.
  - **`_fail(self, msg)`** (Line 493): Handle worker failure.

Args:
    msg: Error message from the failed worker.

#### Class `SystemInfoPage`
*Read-only system facts + live metrics.*

- **Inherits From**: `_Page`
- **Source Line**: 507
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 510): Initialize the System Info page.

Args:
    win: Parent window instance.
  - **`_load(self)`** (Line 551): Load and display system information.
  - **`_on_info(self, info)`** (Line 557): Handle the system info from the worker.

Args:
    info: Dictionary containing system information.
  - **`_fail(self, msg)`** (Line 590): Handle worker failure.

Args:
    msg: Error message from the failed worker.

#### Class `BrokenLinksWorker`
*Worker that scans for broken shortcuts/links.*

- **Inherits From**: `QObject`
- **Source Line**: 604
- **Key Methods & Handlers**:
  - **`__init__(self, root)`** (Line 610): Store constructor arguments (root) and initialize worker signals.
  - **`cancel(self)`** (Line 617): Request cancellation of the scan.
  - **`run(self)`** (Line 621): Execute the broken link scan and emit results.

#### Class `DuplicateFoldersWorker`
*Worker that finds duplicate folders.*

- **Inherits From**: `QObject`
- **Source Line**: 635
- **Key Methods & Handlers**:
  - **`__init__(self, root)`** (Line 641): Store constructor arguments (root) and initialize worker signals.
  - **`cancel(self)`** (Line 648): Request cancellation of the scan.
  - **`run(self)`** (Line 652): Execute the duplicate folder scan and emit results.

#### Class `PackageCacheWorker`
*Worker that lists package manager cache sizes.*

- **Inherits From**: `QObject`
- **Source Line**: 664
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 669): Execute the cache scan and emit results.

#### Class `PackageCleanWorker`
*Background worker that runs package clean via PackageManagerCleaner (package manager cleaner); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 689
- **Key Methods & Handlers**:
  - **`__init__(self, manager)`** (Line 694): Store constructor arguments (manager) and initialize worker signals.
  - **`run(self)`** (Line 699): Run the PackageManagerCleaner (package manager cleaner) backend call off the UI thread; emit finished/failed with results.

#### Class `_SimpleFolderPage`
*Minimal folder-pick + scan page (no fake Cancel affordance).

Premium redesign: Card-wrapped picker, styled table, polished state.*

- **Inherits From**: `_Page`
- **Source Line**: 721
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 731): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_build_results(self)`** (Line 820): Subclasses construct and return their specific QTableWidget.
  - **`_pick(self)`** (Line 826): Pick via the file dialog; results return through worker signals.
  - **`_toggle_run(self)`** (Line 838): Handle toggle run for the page widgets and worker state.
  - **`_start(self, worker, on_done)`** (Line 848): Start a scan worker with live progress + cancel support.
  - **`_on_progress(self, text)`** (Line 861): Handle worker results: update widgets and clear the busy state.
  - **`_finish(self)`** (Line 865): Handle finish for the page widgets and worker state.
  - **`_busy(self, on)`** (Line 874): Busy via the progress state; results return through worker signals.
  - **`_selected_paths(self)`** (Line 881): Compute and return the value for selected paths used by the page.
  - **`_delete_selected(self)`** (Line 887): Handle delete selected for the page widgets and worker state.
  - **`_on_deleted(self, freed, ok, blocked)`** (Line 905): Handle worker results: update widgets and clear the busy state.
  - **`_run(self)`** (Line 913): Subclasses launch their specific scan worker.
  - **`_fail(self, msg)`** (Line 919): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `BrokenLinksPage`
*BrokenLinksPage page wiring widgets, worker threads, and state-panel feedback.*

- **Inherits From**: `_SimpleFolderPage`
- **Source Line**: 930
- **Key Methods & Handlers**:
  - **`_build_results(self)`** (Line 936): Compute and return the value for build results used by the page.
  - **`_run(self)`** (Line 946): Run via the background worker; results return through worker signals.
  - **`_on_done(self, links)`** (Line 950): Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.

#### Class `DuplicateFoldersPage`
*DuplicateFoldersPage page wiring widgets, worker threads, and state-panel feedback.*

- **Inherits From**: `_SimpleFolderPage`
- **Source Line**: 966
- **Key Methods & Handlers**:
  - **`_build_results(self)`** (Line 972): Compute and return the value for build results used by the page.
  - **`_run(self)`** (Line 982): Run via the background worker; results return through worker signals.
  - **`_on_done(self, groups)`** (Line 986): Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.

#### Class `PackageCachePage`
*Detect system package managers (pip/npm/conda/...) and clear their caches.

Premium redesign: Card-wrapped sections, StatCard metrics, styled table.*

- **Inherits From**: `_Page`
- **Source Line**: 1006
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1012): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_browse_pm_directory(self)`** (Line 1211): Handle browse pm directory for the page widgets and worker state.
  - **`_browse_pm_file(self)`** (Line 1220): Handle browse pm file for the page widgets and worker state.
  - **`_add_custom_pm_location(self)`** (Line 1230): Handle add custom pm location for the page widgets and worker state.
  - **`detect_package_managers(self)`** (Line 1238): Detect package managers via the worker/widgets; results return through worker signals.
  - **`start_pm_scan(self)`** (Line 1275): Start pm scan via the progress state; results return through worker signals.
  - **`start_autodiscover_scan(self)`** (Line 1305): Auto-discover project build caches across all fixed drives using ProjectCacheScanner.
  - **`_display_scan_results(self, resources)`** (Line 1339): Handle display scan results for the page widgets and worker state.
  - **`start_pm_cleanup(self)`** (Line 1380): Start pm cleanup via the confirmation dialog, progress state, results view; results return through worker signals.
  - **`_handle_cleanup_results(self, results, dry_run)`** (Line 1424): Handle worker results: refresh tables/trees, re-enable buttons and clear the busy state.
  - **`_fail(self, msg)`** (Line 1438): Report the worker error in the state panel/status bar and clear the busy state.
  - **`_fmt_bytes(size_bytes)`** (Line 1443): Format a byte/rate value into a human-readable string (B/s, KB/s, MB/s).

#### Class `ProjectCachesPage`
*Clean multi-ecosystem project development caches (__pycache__, node_modules, target, build, etc.).*

- **Inherits From**: `_Page`
- **Source Line**: 1477
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1480): Build the page layout (buttons, trees, cards, title header) and connect button/worker actions.
  - **`_toggle_settings_panel(self, checked)`** (Line 1863): Show or hide the settings card.
  - **`_update_target_count_badge(self)`** (Line 1867): Handle update target count badge for the page widgets and worker state.
  - **`_add_typed_target_folder(self)`** (Line 1872): Handle add typed target folder for the page widgets and worker state.
  - **`select_file_location_to_scan(self)`** (Line 1881): Select file location to scan via the file dialog; results return through worker signals.
  - **`auto_detect_code_folders(self)`** (Line 1894): Auto detect code folders via the confirmation dialog; results return through worker signals.
  - **`add_current_workspace(self)`** (Line 1922): Add current workspace via the confirmation dialog; results return through worker signals.
  - **`add_folder_to_scan(self)`** (Line 1934): Add folder to scan via the file dialog; results return through worker signals.
  - **`remove_selected_folder(self)`** (Line 1946): Remove selected folder via the worker/widgets; results return through worker signals.
  - **`clear_all_folders(self)`** (Line 1957): Clear all folders via the confirmation dialog; results return through worker signals.
  - **`select_all_categories(self)`** (Line 1971): Select all categories via the worker/widgets; results return through worker signals.
  - **`clear_all_categories(self)`** (Line 1980): Clear all categories via the worker/widgets; results return through worker signals.
  - **`_get_enabled_categories(self)`** (Line 1989): Handle get enabled categories for the page widgets and worker state.
  - **`start_project_scan(self)`** (Line 2006): Start project scan via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_scan_progress(self, status_text, items_found, total_bytes)`** (Line 2049): Handle worker results: update cards/labels and clear the busy state.
  - **`_on_proj_scan_finished(self, resources)`** (Line 2055): Handle worker results: refresh tables/trees and clear the busy state.
  - **`start_auto_scan(self)`** (Line 2062): Auto-discover across all fixed drives (no folder pick needed).
  - **`_on_scan_failed(self, err_msg)`** (Line 2091): Report the worker error in the state panel/status bar and clear the busy state.
  - **`_cleanup_scan_thread(self)`** (Line 2096): Handle cleanup scan thread for the page widgets and worker state.
  - **`cancel_project_operation(self)`** (Line 2111): Cancel project operation via the worker/widgets; results return through worker signals.
  - **`_display_project_scan_results(self, resources)`** (Line 2120): Handle display project scan results for the page widgets and worker state.
  - **`_on_tree_item_expanded(self, item)`** (Line 2192): Handle worker results: refresh tables/trees, update cards/labels, re-enable buttons and clear the busy state.
  - **`on_sort_combo_changed(self, index)`** (Line 2237): Handle on sort combo changed for the page widgets and worker state.
  - **`filter_by_chip(self, cat_key)`** (Line 2254): Filter by chip via the results view; results return through worker signals.
  - **`_on_tree_item_double_clicked(self, item, column)`** (Line 2261): Handle worker results: refresh tables/trees and clear the busy state.
  - **`_on_tree_item_changed(self, item, column)`** (Line 2273): Handle worker results: refresh tables/trees and clear the busy state.
  - **`filter_results_table(self, query)`** (Line 2286): Filter results table via the results view; results return through worker signals.
  - **`toggle_all_table_items(self, checked)`** (Line 2323): Toggle all table items via the results view; results return through worker signals.
  - **`export_report(self)`** (Line 2334): Export report via the file dialog, confirmation dialog, CSV file; results return through worker signals.
  - **`_get_selected_resources(self)`** (Line 2374): Compute and return the value for get selected resources used by the page.
  - **`start_project_cleanup(self)`** (Line 2385): Start project cleanup via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_clean_progress(self, done_count, total_count, freed_bytes)`** (Line 2424): Handle worker results: update cards/labels and clear the busy state.
  - **`_on_proj_clean_finished(self, results, dry_run)`** (Line 2429): Handle worker results: refresh tables/trees, update cards/labels and clear the busy state.
  - **`_handle_project_cleanup_results(self, results, dry_run)`** (Line 2454): Handle worker results: update widgets and clear the busy state.
  - **`_on_clean_failed(self, err_msg)`** (Line 2458): Report the worker error in the state panel/status bar and clear the busy state.
  - **`_cleanup_clean_thread(self)`** (Line 2463): Handle cleanup clean thread for the page widgets and worker state.
  - **`_fail(self, msg)`** (Line 2477): Report the worker error in the state panel/status bar and clear the busy state.
  - **`_fmt_bytes(size_bytes)`** (Line 2482): Format a byte/rate value into a human-readable string (B/s, KB/s, MB/s).

#### Class `SecretsScanWorker`
*Background worker that runs secrets scan via run_scan (secrets scanner); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 2498
- **Key Methods & Handlers**:
  - **`__init__(self, directory)`** (Line 2503): Store constructor arguments (directory) and initialize worker signals.
  - **`run(self)`** (Line 2508): Run the run_scan (secrets scanner) backend call off the UI thread; emit finished/failed with results.

#### Class `SecretsScannerPage`
*Scan a project folder for exposed secrets/credentials - fully offline.*

- **Inherits From**: `_Page`
- **Source Line**: 2550
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 2553): Build the page layout (buttons, tables, title header, state panel) and connect button/worker actions.
  - **`_pick(self)`** (Line 2599): Pick via the file dialog; results return through worker signals.
  - **`_run(self)`** (Line 2608): Run via the background worker, progress state, status bar; results return through worker signals.
  - **`_on_done(self, findings, risk)`** (Line 2616): Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.
  - **`_fail(self, msg)`** (Line 2635): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `VirtualDisksPage`
*Reclaim space from WSL / Docker / Hyper-V virtual disks.

These ``.vhdx`` files grow on demand and never shrink by themselves, so
deleting files inside a Linux distribution or removing Docker images frees
space *inside* the guest while Windows still reports the drive as full. This
page finds those disks, explains the situation, and compacts them safely.*

- **Inherits From**: `_Page`
- **Source Line**: 2646
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 2655): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_selected_disks(self)`** (Line 2752): Compute and return the value for selected disks used by the page.
  - **`_on_select(self)`** (Line 2757): Handle worker results: re-enable buttons and clear the busy state.
  - **`_load(self)`** (Line 2766): Load via the background worker, progress state; results return through worker signals.
  - **`_on_listed(self, disks)`** (Line 2774): Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.
  - **`_shutdown(self)`** (Line 2810): Shutdown via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_shutdown(self, ok, message)`** (Line 2827): Handle worker results: note status, re-enable buttons and clear the busy state.
  - **`_compact(self)`** (Line 2837): Compact via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_compacted(self, results)`** (Line 2861): Handle worker results: update cards/labels, note status, re-enable buttons and clear the busy state.
  - **`_set_sparse(self)`** (Line 2890): Handle set sparse for the page widgets and worker state.
  - **`_on_sparse(self, ok, message)`** (Line 2912): Handle worker results: note status, re-enable buttons and clear the busy state.
  - **`_fail(self, msg)`** (Line 2922): Report the worker error in the state panel, re-enable actions and clear the busy state.

### Module `src/cortex_unified/ui/premium/motion.py`
### Module `src/cortex_unified/ui/premium/near_duplicates_page.py`
#### Class `_NearDupWorker`
*_NearDupWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 29
- **Key Methods & Handlers**:
  - **`__init__(self, root, threshold)`** (Line 35): __init__.
  - **`cancel(self)`** (Line 44): cancel.
  - **`run(self)`** (Line 48): run.

#### Class `NearDuplicatesPage`
*Find near-duplicate files (80%+ Jaccard) via MinHash LSH + Bloom.*

- **Inherits From**: `_Page`
- **Source Line**: 63
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 66): __init__.
  - **`_pick(self)`** (Line 117): _pick.
  - **`_run(self)`** (Line 127): _run.
  - **`_on_progress(self, msg)`** (Line 138): _on_progress.
  - **`_on_done(self, groups)`** (Line 142): _on_done.
  - **`_fail(self, msg)`** (Line 168): _fail.

### Module `src/cortex_unified/ui/premium/network_pages.py`
#### Class `TrafficMonitorPage`
*Live network throughput graph + per-interface breakdown.*

- **Inherits From**: `_Page`
- **Source Line**: 89
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 92): Build the page layout (tables, cards, title header) and connect button/worker actions.
  - **`_start(self)`** (Line 142): Handle start for the page widgets and worker state.
  - **`_tick(self)`** (Line 150): Handle tick for the page widgets and worker state.

#### Class `FirewallListWorker`
*Background worker that runs firewall list via FirewallManager (firewall manager); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 177
- **Key Methods & Handlers**:
  - **`__init__(self, cortex_only)`** (Line 182): Store constructor arguments (cortex_only) and initialize worker signals.
  - **`run(self)`** (Line 187): Run the FirewallManager (firewall manager) backend call off the UI thread; emit finished/failed with results.

#### Class `FirewallActionWorker`
*Background worker that runs firewall action via FirewallManager (firewall manager); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 197
- **Key Methods & Handlers**:
  - **`__init__(self, action)`** (Line 202): Store constructor arguments (action) and initialize worker signals.
  - **`run(self)`** (Line 208): Run the FirewallManager (firewall manager) backend call off the UI thread; emit finished/failed with results.

#### Class `FirewallPage`
*Block/allow programs and IPs via Windows Firewall (Cortex-scoped).*

- **Inherits From**: `_Page`
- **Source Line**: 235
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 238): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_browse(self)`** (Line 337): Browse via the file dialog; results return through worker signals.
  - **`_busy(self, on)`** (Line 344): Busy via the progress state; results return through worker signals.
  - **`_create(self, action)`** (Line 349): Create via the background worker, confirmation dialog; results return through worker signals.
  - **`_on_action(self, ok, msg)`** (Line 378): Handle worker results: note status and clear the busy state.
  - **`_load(self)`** (Line 387): Load via the background worker, progress state; results return through worker signals.
  - **`_on_listed(self, rules)`** (Line 393): Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.
  - **`_on_sel(self)`** (Line 414): Handle worker results: re-enable buttons and clear the busy state.
  - **`_selected(self)`** (Line 420): Selected via the worker/widgets; results return through worker signals.
  - **`_toggle(self)`** (Line 430): Toggle via the background worker; results return through worker signals.
  - **`_remove(self)`** (Line 441): Remove via the background worker, confirmation dialog; results return through worker signals.
  - **`_fail(self, msg)`** (Line 458): Report the worker error in the state panel and clear the busy state.

#### Class `NetworkMapPage`
*Visual, offline map of which apps connect to which remote hosts.*

- **Inherits From**: `_Page`
- **Source Line**: 584
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 587): Build the page layout (buttons, cards, title header, state panel) and connect button/worker actions.
  - **`_load(self)`** (Line 627): Load via the background worker, progress state; results return through worker signals.
  - **`_on_loaded(self, conns, summary)`** (Line 634): Handle worker results: refresh tables/trees, re-enable buttons and clear the busy state.
  - **`_render(self)`** (Line 641): Render via the worker/widgets; results return through worker signals.
  - **`_fail(self, msg)`** (Line 659): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `LanScanWorker`
*Deep multi-protocol LAN discovery on the worker runtime.

Cancellable: the discovery engine polls the event between passes and
inside every sweep, so closing the page stops it promptly instead of
leaving a subnet sweep running.*

- **Inherits From**: `QObject`
- **Source Line**: 669
- **Key Methods & Handlers**:
  - **`__init__(self, deep, rounds, audit_profile, include_upnp_wan, requested_networks, custom_ports, nmap_modes, advisory_catalog_path)`** (Line 681): Initialize discovery worker.
  - **`cancel(self)`** (Line 698): Request cooperative cancellation so the background operation stops promptly.
  - **`run(self)`** (Line 702): Run the NetworkDiscovery (network discovery) backend call off the UI thread; emit finished/failed/progress with results.

#### Class `VendorDatabaseWorker`
*Explicit IEEE registry refresh; never runs automatically.*

- **Inherits From**: `QObject`
- **Source Line**: 724
- **Key Methods & Handlers**:
  - **`__init__(self)`** (Line 730): Initialize the worker and its finished/failed signals.
  - **`cancel(self)`** (Line 735): Request cooperative cancellation so the background operation stops promptly.
  - **`run(self)`** (Line 739): Run the oui (system tools) backend call off the UI thread; emit finished/failed with results.

#### Class `NetworkScheduleWorker`
*Background worker that runs network schedule via network automation; emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 750
- **Key Methods & Handlers**:
  - **`__init__(self, action, spec)`** (Line 755): Store constructor arguments (action, spec) and initialize worker signals.
  - **`run(self)`** (Line 761): Run the network automation backend call off the UI thread; emit finished/failed with results.

#### Class `ExposureLookupWorker`
*Background worker that runs exposure lookup via external exposure; emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 779
- **Key Methods & Handlers**:
  - **`__init__(self, provider, public_ip, api_key, api_secret)`** (Line 784): Initialize worker.
  - **`run(self)`** (Line 793): Run the external exposure backend call off the UI thread; emit finished/failed with results.

#### Class `DeviceActionWorker`
*Run an explicit selected-device ping or Wake-on-LAN action.*

- **Inherits From**: `QObject`
- **Source Line**: 807
- **Key Methods & Handlers**:
  - **`__init__(self, action, device, networks)`** (Line 813): Store constructor arguments (action, device, networks) and initialize worker signals.
  - **`run(self)`** (Line 820): Run the NetworkTools (network tools) backend call off the UI thread; emit finished/failed with results.

#### Class `LanDevicesPage`
*Everything actually on your local network, not just the ARP cache.

The old version read ``arp -a``, which only lists devices this PC happened
to talk to recently - so a sleeping phone, a Google TV or an ESP32 board
were routinely absent. This page runs real discovery: it forces ARP replies
across the subnet and listens to mDNS, UPnP and WS-Discovery to get names
and device types as well.*

- **Inherits From**: `_Page`
- **Source Line**: 857
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 872): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_toggle_more_controls(self, visible)`** (Line 1281): Toggle more controls for the results widgets; keeps buttons/state in sync.
  - **`_load(self, deep, rounds, audit_profile, include_upnp_wan, requested_networks, custom_ports, nmap_modes, advisory_catalog_path)`** (Line 1291): Load network audit data.
  - **`_run_expert_scan(self)`** (Line 1308): Run expert scan for the results widgets after confirmation; keeps buttons/state in sync.
  - **`_browse_advisory_catalog(self)`** (Line 1348): Browse advisory catalog for the results widgets via file dialog; keeps buttons/state in sync.
  - **`_device_columns(self)`** (Line 1358): Declare the device columns once instead of filling cells per row.

Each column derives its text from the ``Device`` record on demand, so a
scan result is handed to the model in a single reset. The IP column sorts
on a packed integer rather than the dotted string - otherwise
``192.168.1.10`` would sort before ``192.168.1.9``.
  - **`_device_name(self, dev)`** (Line 1378): Return the display name for a discovered device (custom name plus router/this-PC tag).
  - **`_device_type(self, dev)`** (Line 1388): Return the type/OS string for a device including trust state and OS fingerprint.
  - **`_device_services(dev)`** (Line 1403): Return the compact service summary (port/proto/name) for the device row.
  - **`_device_findings(self, dev)`** (Line 1415): Return the severity-sorted security findings for a device IP.
  - **`_device_security(self, dev)`** (Line 1421): Return the headline security text for a device row.
  - **`_device_security_rank(self, dev)`** (Line 1431): Sort worst-first: a device with a critical finding outranks a clean one.
  - **`_identity_of(self, dev)`** (Line 1438): Return the stable identity key used for metadata/findings lookup.
  - **`_open_device_window(self)`** (Line 1443): Open the selected device in its own full-detail premium window.
  - **`_forget_device_window(self, window)`** (Line 1464): Forget device window for the results widgets; keeps buttons/state in sync.
  - **`_selected_device(self)`** (Line 1470): The selected ``Device``, resolved through the proxy.

Previously this indexed ``self._devices`` by the view's row number, which
silently returned the wrong device as soon as the table was sorted. The
binding maps the proxy index back to the source record instead.
  - **`_device_action(self, action)`** (Line 1479): Device action for the results widgets on a worker thread; keeps buttons/state in sync.
  - **`_device_action_done(self, action, payload)`** (Line 1501): Handle worker results: note status and clear the busy state.
  - **`_device_action_failed(self, message)`** (Line 1517): Report the worker error in the state panel/status bar and clear the busy state.
  - **`_open_selected_service(self)`** (Line 1524): Open selected service for the results widgets in the browser/tool; keeps buttons/state in sync.
  - **`_load_selected_metadata(self, device)`** (Line 1545): Load selected metadata for the results widgets; keeps buttons/state in sync.
  - **`_save_selected_metadata(self)`** (Line 1563): Save selected metadata for the results widgets after confirmation; keeps buttons/state in sync.
  - **`_export_inventory_csv(self)`** (Line 1592): Export inventory csv for the results widgets via file dialog as CSV; keeps buttons/state in sync.
  - **`_import_inventory_csv(self)`** (Line 1610): Import inventory csv for the results widgets via file dialog as CSV; keeps buttons/state in sync.
  - **`_lookup_external_exposure(self)`** (Line 1645): Lookup external exposure for the results widgets after confirmation on a worker thread; keeps buttons/state in sync.
  - **`_exposure_done(self, result)`** (Line 1683): Handle worker results: re-enable buttons and clear the busy state.
  - **`_exposure_failed(self, message)`** (Line 1690): Report the worker error in the re-enable actions and clear the busy state.
  - **`_create_schedule(self)`** (Line 1696): Create schedule for the results widgets after confirmation; keeps buttons/state in sync.
  - **`_delete_schedule(self)`** (Line 1726): Delete schedule for the results widgets after confirmation; keeps buttons/state in sync.
  - **`_run_schedule_action(self, action, spec)`** (Line 1737): Run schedule action for the results widgets on a worker thread; keeps buttons/state in sync.
  - **`_schedule_done(self, action, payload)`** (Line 1746): Handle worker results: note status and clear the busy state.
  - **`_schedule_failed(self, message)`** (Line 1753): Report the worker error in the state panel/status bar and clear the busy state.
  - **`_confirm_deep_audit(self)`** (Line 1758): Confirm deep audit for the results widgets after confirmation; keeps buttons/state in sync.
  - **`_update_vendors(self)`** (Line 1774): Update vendors for the results widgets on a worker thread; keeps buttons/state in sync.
  - **`_vendors_updated(self, ok, message)`** (Line 1782): Handle worker results: note status, re-enable buttons and clear the busy state.
  - **`_vendor_update_failed(self, message)`** (Line 1794): Report the worker error in the re-enable actions and clear the busy state.
  - **`_export_report(self)`** (Line 1799): Export report for the results widgets via file dialog as CSV; keeps buttons/state in sync.
  - **`_show_device_details(self)`** (Line 1881): Show device details for the results widgets; keeps buttons/state in sync.
  - **`_cancel(self)`** (Line 1945): Handle cancel for the page widgets and worker state.
  - **`_busy(self, busy)`** (Line 1955): Busy via the progress state; results return through worker signals.
  - **`_on_loaded(self, result)`** (Line 1975): Handle worker results: refresh tables/trees, update cards/labels, update the state panel and clear the busy state.
  - **`_fail(self, msg)`** (Line 2167): Report the worker error in the state panel and clear the busy state.

#### Class `_ToolWorker`
*Runs one network-tool call off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 2177
- **Key Methods & Handlers**:
  - **`__init__(self, tool, target)`** (Line 2183): Store constructor arguments (tool, target) and initialize worker signals.
  - **`run(self)`** (Line 2189): Run the NetworkTools (network tools) backend call off the UI thread; emit finished/failed with results.

#### Class `NetworkToolsPage`
*Classic diagnostics: ping, traceroute, DNS, port check, IP info.*

- **Inherits From**: `_Page`
- **Source Line**: 2222
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 2225): Build the page layout (buttons, tables, cards, title header) and connect button/worker actions.
  - **`_run(self, tool)`** (Line 2287): Run via the background worker, progress state; results return through worker signals.
  - **`_on_result(self, tool, result)`** (Line 2301): Handle worker results: update widgets and clear the busy state.
  - **`_show_ping(self, r)`** (Line 2316): Show ping for the results widgets; keeps buttons/state in sync.
  - **`_show_traceroute(self, hops)`** (Line 2329): Show traceroute for the results widgets; keeps buttons/state in sync.
  - **`_show_dns(self, r)`** (Line 2341): Show dns for the results widgets; keeps buttons/state in sync.
  - **`_show_ports(self, res)`** (Line 2357): Show ports for the results widgets; keeps buttons/state in sync.
  - **`_show_ipinfo(self, info)`** (Line 2378): Show ipinfo for the results widgets; keeps buttons/state in sync.
  - **`_fail(self, msg)`** (Line 2394): Report the worker error in the state panel/status bar and clear the busy state.

#### Class `AuthorizeWorker`
*Background worker that runs authorize via TargetAuthorizer (load tester); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 2407
- **Key Methods & Handlers**:
  - **`__init__(self, host, token)`** (Line 2412): Store constructor arguments (host, token) and initialize worker signals.
  - **`run(self)`** (Line 2418): Run the TargetAuthorizer (load tester) backend call off the UI thread; emit finished/failed with results.

#### Class `LoadTestWorker`
*Background worker that runs load test via load tester; emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 2428
- **Key Methods & Handlers**:
  - **`__init__(self, mode, cfg, auth_dict)`** (Line 2434): Store constructor arguments (mode, cfg, auth_dict) and initialize worker signals.
  - **`cancel(self)`** (Line 2443): Request cooperative cancellation so the background operation stops promptly.
  - **`run(self)`** (Line 2447): Run the load tester backend call off the UI thread; emit finished/failed/progress with results.

#### Class `LoadTesterPage`
*Measure how much load YOUR OWN service can take before it degrades.*

- **Inherits From**: `_Page`
- **Source Line**: 2470
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 2473): Build the page layout (buttons, cards, title header, controls) and connect button/worker actions.
  - **`_mode_changed(self)`** (Line 2574): Mode changed via the worker/widgets; results return through worker signals.
  - **`_check(self)`** (Line 2580): Check via the background worker; results return through worker signals.
  - **`_on_auth(self, auth)`** (Line 2590): Handle worker results: update cards/labels, re-enable buttons and clear the busy state.
  - **`_offer_token(self, auth)`** (Line 2608): Offer token via the confirmation dialog; results return through worker signals.
  - **`_auth_fail(self, msg)`** (Line 2624): Report the worker error in the re-enable actions and clear the busy state.
  - **`_toggle(self)`** (Line 2630): Toggle via the background worker; results return through worker signals.
  - **`_start(self)`** (Line 2639): Handle start for the page widgets and worker state.
  - **`_on_progress(self, snap)`** (Line 2677): Handle worker results: update widgets and clear the busy state.
  - **`_on_done(self, s)`** (Line 2683): Handle worker results: note status, re-enable buttons and clear the busy state.
  - **`_verdict(s)`** (Line 2707): Verdict via the results view; results return through worker signals.
  - **`_run_fail(self, msg)`** (Line 2721): Report the worker error in the re-enable actions and clear the busy state.

### Module `src/cortex_unified/ui/premium/nextgen_suite_pages.py`
#### Class `ShaderCachePage`
*Page for auditing and purging stale GPU shader caches by age.*

- **Inherits From**: `_Page`
- **Source Line**: 93
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 95): Build the Shader Cache page with scan/clean buttons, a min-age spinner, and a table.
  - **`_on_scan(self)`** (Line 142): Scan shader cache locations with the configured minimum age.
  - **`_on_clean(self)`** (Line 170): Purge shader binaries older than the minimum age.

#### Class `AiTelemetryCleanerPage`
*Page for auditing Copilot/Recall caches and truncating SQLite WAL logs.*

- **Inherits From**: `_Page`
- **Source Line**: 195
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 197): Build the AI Telemetry page with scan/clean buttons and an artifacts table.
  - **`_on_scan(self)`** (Line 237): Scan local AI and Recall stores in the background.
  - **`_on_clean(self)`** (Line 263): Clean transient AI caches and checkpoint WAL databases.

#### Class `SsdTrimOptimizerPage`
*Page for auditing volume TRIM state and running a ReTrim on a chosen drive.*

- **Inherits From**: `_Page`
- **Source Line**: 288
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 290): Build the SSD TRIM page with audit/trim buttons and a volumes table.
  - **`_on_audit(self)`** (Line 327): Audit volumes and filesystem TRIM status in the background.
  - **`_on_trim(self)`** (Line 356): ReTrim the drive selected in the table.

#### Class `RestartManagerUnlockerPage`
*Page for finding and killing processes that lock a file via Restart Manager.*

- **Inherits From**: `_Page`
- **Source Line**: 388
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 390): Build the Unlocker page with path input, inspect/unlock buttons, and a processes table.
  - **`_on_browse(self)`** (Line 433): Pick a file, fill the path input, and inspect it immediately.
  - **`_on_inspect(self)`** (Line 440): Query Restart Manager for processes locking the entered path.
  - **`_on_unlock(self)`** (Line 474): Force-terminate the processes locking the entered file.

#### Class `VssHealthAnalyzerPage`
*Page for diagnosing VSS writers and shadow copy storage usage.*

- **Inherits From**: `_Page`
- **Source Line**: 497
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 499): Build the VSS Health page with scan/reset buttons and a writers table.
  - **`_on_scan(self)`** (Line 539): Inspect VSS writers and shadow storage in the background.
  - **`_on_reset(self)`** (Line 567): Restart VSS services to clear stalled writer states.

#### Class `DevPackageCachePage`
*Page for auditing and purging Winget, Cargo, vcpkg, NuGet, and Pip caches.*

- **Inherits From**: `_Page`
- **Source Line**: 588
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 590): Build the Dev Package Cache page with scan/clean buttons and a stores table.
  - **`_on_scan(self)`** (Line 631): Scan developer package stores in the background.
  - **`_on_clean(self)`** (Line 658): Purge all discovered developer package stores.

#### Class `ChecksumMatrixPage`
*Page for batch hashing files and generating .sha256 manifests.*

- **Inherits From**: `_Page`
- **Source Line**: 680
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 682): Build the Checksum Matrix page with target input, hash/manifest buttons, and a digests table.
  - **`_on_browse_file(self)`** (Line 731): Pick a file, fill the target input, and hash it immediately.
  - **`_on_browse_dir(self)`** (Line 738): Pick a directory to use for manifest generation.
  - **`_on_hash(self)`** (Line 744): Compute CRC32, MD5, SHA-1, SHA-256, and SHA-512 for the chosen file.
  - **`_on_generate_manifest(self)`** (Line 780): Write a checksums.sha256 manifest for the chosen directory.

### Module `src/cortex_unified/ui/premium/nexus_page.py`
#### Class `NexusExplorerPage`
*The embedded native explorer (in-process Qt6 widget).

The explorer is heavy (models, timers, native DPI queries), so it is
constructed lazily on first visit - the same lazy-page discipline every
other page follows - and never under ``QT_QPA_PLATFORM=offscreen`` (CI),
where a native explorer cannot function and its timers only produce
event-loop noise that poisons later tests.*

- **Inherits From**: `_Page`
- **Source Line**: 78
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 88): __init__.
  - **`_build_explorer(self)`** (Line 97): _build_explorer.

### Module `src/cortex_unified/ui/premium/old_files_page.py`
#### Class `_OldFilesScanWorker`
*Scan for old inactive files off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 34
- **Key Methods & Handlers**:
  - **`__init__(self, root_path, min_age_days)`** (Line 39): Event handler or worker task method.
  - **`run(self)`** (Line 44): Event handler or worker task method.

#### Class `OldFilesPage`
*Finds inactive, old files untouched for months or years.*

- **Inherits From**: `_Page`
- **Source Line**: 57
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 60): Event handler or worker task method.
  - **`_pick_folder(self)`** (Line 145): Event handler or worker task method.
  - **`_scan(self)`** (Line 151): Event handler or worker task method.
  - **`_on_done(self, files, stats)`** (Line 159): Event handler or worker task method.
  - **`_delete_selected(self)`** (Line 186): Event handler or worker task method.
  - **`_fail(self, err)`** (Line 215): Event handler or worker task method.

### Module `src/cortex_unified/ui/premium/perceptual_duplicates_page.py`
#### Class `_PerceptualWorker`
*_PerceptualWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 26
- **Key Methods & Handlers**:
  - **`__init__(self, root, max_distance)`** (Line 32): __init__.
  - **`cancel(self)`** (Line 41): cancel.
  - **`run(self)`** (Line 45): run.

#### Class `PerceptualDuplicatesPage`
*Find visually-similar photos via perceptual hashing (pHash).*

- **Inherits From**: `_Page`
- **Source Line**: 63
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 66): __init__.
  - **`_pick(self)`** (Line 121): _pick.
  - **`_run(self)`** (Line 130): _run.
  - **`_on_progress(self, msg)`** (Line 141): _on_progress.
  - **`_on_done(self, groups)`** (Line 145): _on_done.
  - **`_fail(self, msg)`** (Line 178): _fail.

### Module `src/cortex_unified/ui/premium/portable_manager_page.py`
#### Class `_PortableWorker`
*_PortableWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 41
- **Key Methods & Handlers**:
  - **`__init__(self, roots, target_apps)`** (Line 47): __init__.
  - **`cancel(self)`** (Line 54): cancel.
  - **`run(self)`** (Line 58): run.

#### Class `_UpdateWorker`
*_UpdateWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 78
- **Key Methods & Handlers**:
  - **`__init__(self, apps)`** (Line 84): __init__.
  - **`cancel(self)`** (Line 90): cancel.
  - **`run(self)`** (Line 94): run.

#### Class `PortableManagerPage`
*Scan, track, and update portable apps on removable and local drives.*

- **Inherits From**: `_Page`
- **Source Line**: 121
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 124): __init__.
  - **`_add_root(self)`** (Line 206): _add_root.
  - **`_parse_roots(self)`** (Line 218): _parse_roots.
  - **`_get_target_apps(self)`** (Line 225): _get_target_apps.
  - **`_run(self)`** (Line 232): _run.
  - **`_on_progress(self, msg)`** (Line 247): _on_progress.
  - **`_on_done(self, apps)`** (Line 251): _on_done.
  - **`_auto_update(self, apps)`** (Line 290): _auto_update.
  - **`_on_update_done(self, result)`** (Line 318): _on_update_done.
  - **`_on_update_fail(self, msg)`** (Line 327): _on_update_fail.
  - **`_fail(self, msg)`** (Line 334): _fail.

### Module `src/cortex_unified/ui/premium/power_suite_pages.py`
#### Class `EnvVariableManagerPage`
*Page for auditing PATH entries and cleaning dead links or duplicates.*

- **Inherits From**: `_Page`
- **Source Line**: 99
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 101): Build the PATH Optimizer page with analyze/clean/export buttons and an entries table.
  - **`_on_analyze(self)`** (Line 144): Analyze PATH and list entries with dead-link and duplicate flags.
  - **`_on_clean(self)`** (Line 166): Confirm and remove dead/duplicate User PATH entries, then re-analyze.
  - **`_on_export(self)`** (Line 181): Export environment variables to a .env or .bat file.

#### Class `WindowsServiceManagerPage`
*Page for profiling services and applying preset optimization profiles.*

- **Inherits From**: `_Page`
- **Source Line**: 195
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 197): Build the Service Manager page with scan button, profile combo, and services table.
  - **`_on_scan(self)`** (Line 236): Enumerate Windows services on the worker runtime.
  - **`_on_apply_profile(self)`** (Line 264): Confirm and apply the selected service profile, then rescan.

#### Class `FontCacheManagerPage`
*Page for inspecting installed fonts and removing orphaned registry entries.*

- **Inherits From**: `_Page`
- **Source Line**: 285
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 287): Build the Font Cache page with scan/clean buttons and a fonts table.
  - **`_on_scan(self)`** (Line 327): Analyze installed fonts and flag orphans and duplicates.
  - **`_on_clean(self)`** (Line 347): Confirm and remove orphaned font entries, then rescan.

#### Class `TempFolderCleanerPage`
*Page for scanning and purging stale temp files across many locations.*

- **Inherits From**: `_Page`
- **Source Line**: 364
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 366): Build the Temp Cleaner page with age spinner, scan/clean buttons, and a locations table.
  - **`_on_scan(self)`** (Line 412): Scan all temp locations and show stale-file totals.
  - **`_on_clean(self)`** (Line 431): Confirm and delete temp files older than the chosen age, then rescan.

#### Class `ContextMenuManagerPage`
*Page for enabling and disabling Explorer context-menu handlers.*

- **Inherits From**: `_Page`
- **Source Line**: 452
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 454): Build the Context Menu page with scan button, enable/disable actions, and an entries table.
  - **`_on_scan(self)`** (Line 500): Analyze context-menu entries and flag orphaned handlers.
  - **`_on_disable_selected(self)`** (Line 522): Disable the context-menu entry selected in the table.
  - **`_on_enable_selected(self)`** (Line 534): Enable the context-menu entry selected in the table.

#### Class `PagefileOptimizerPage`
*Page for configuring fixed or system-managed pagefile allocation.*

- **Inherits From**: `_Page`
- **Source Line**: 551
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 553): Build the Pagefile page with status labels, drive/size controls, and apply/reset buttons.
  - **`_refresh(self)`** (Line 604): Refresh RAM/pagefile status and prefill recommended sizes.
  - **`_on_apply(self)`** (Line 616): Confirm and set a fixed pagefile on the chosen drive, then refresh.
  - **`_on_reset_auto(self)`** (Line 634): Reset the pagefile to system-managed, then refresh.

#### Class `DiagnosticDataManagerPage`
*Page for auditing telemetry settings and enforcing maximum privacy.*

- **Inherits From**: `_Page`
- **Source Line**: 648
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 650): Build the Telemetry page with audit/harden buttons, score label, and settings table.
  - **`_on_audit(self)`** (Line 688): Audit telemetry settings and show the privacy hardening score.
  - **`_on_harden(self)`** (Line 708): Confirm and apply maximum-privacy telemetry policies, then re-audit.

#### Class `StartupImpactPage`
*Page for analyzing startup impact and toggling startup items.*

- **Inherits From**: `_Page`
- **Source Line**: 728
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 730): Build the Startup Impact page with scan/toggle buttons and an items table.
  - **`_on_scan(self)`** (Line 772): Analyze startup items and show impact levels and boot delay.
  - **`_on_toggle(self)`** (Line 798): Enable or disable the startup item selected in the table.

#### Class `SlackSpaceAnalyzerPage`
*Page for measuring NTFS cluster slack waste per directory.*

- **Inherits From**: `_Page`
- **Source Line**: 817
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 819): Build the Slack Space page with folder picker, analyze button, and offenders table.
  - **`_on_choose(self)`** (Line 859): Pick a directory and immediately analyze it.
  - **`_on_scan(self)`** (Line 866): Analyze cluster slack waste on the worker runtime.

#### Class `EventLogMonitorPage`
*Page for scanning event logs for hardware faults and crashes.*

- **Inherits From**: `_Page`
- **Source Line**: 903
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 905): Build the Event Monitor page with scan button and an events table.
  - **`_on_scan(self)`** (Line 940): Query event-log anomalies on the worker runtime.

### Module `src/cortex_unified/ui/premium/power_tools_pages.py`
#### Class `HashVerifierPage`
*File checksum calculator and manifest validator.*

- **Inherits From**: `_Page`
- **Source Line**: 60
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 63): Build the Hash Verifier page with file picker, digests table, and manifest actions.
  - **`_pick_file(self)`** (Line 118): Pick a file to hash and enable computation.
  - **`_compute_hashes(self)`** (Line 128): Compute MD5, SHA-1, SHA-256, SHA-512, and CRC32 for the chosen file.
  - **`_copy_to_clip(self, text)`** (Line 151): Copy a checksum digest to the clipboard and confirm.
  - **`_verify_manifest(self)`** (Line 157): Verify a .sfv/.md5/.sha256/.sha512 manifest and summarize match results.

#### Class `BatchRenamerPage`
*Regex, token template, and EXIF batch multi-renamer.*

- **Inherits From**: `_Page`
- **Source Line**: 183
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 186): Build the Batch Renamer page with pattern form, preview table, and apply/undo buttons.
  - **`_pick_files(self)`** (Line 267): Pick files to rename and refresh the preview.
  - **`_update_preview(self)`** (Line 275): Recompute the rename plan and show per-file status in the table.
  - **`_apply_rename(self)`** (Line 318): Execute the previewed rename plan and report the outcome.
  - **`_undo_rename(self)`** (Line 330): Revert the last executed rename.

#### Class `FolderSyncPage`
*Side-by-side folder comparison matrix and 1-click sync engine.*

- **Inherits From**: `_Page`
- **Source Line**: 344
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 347): Build the Folder Sync page with folder pickers, compare controls, diff table, and sync mode.
  - **`_pick_left(self)`** (Line 425): Pick the left folder to compare.
  - **`_pick_right(self)`** (Line 434): Pick the right folder to compare.
  - **`_run_compare(self)`** (Line 443): Compare the two folders and fill the diff table; enable sync.
  - **`_run_sync(self)`** (Line 476): Confirm and execute the selected sync mode, then re-compare.

#### Class `FileSplitterPage`
*File chunk splitter and reconstructor with SHA256 integrity check.*

- **Inherits From**: `_Page`
- **Source Line**: 512
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 515): Build the Splitter/Joiner page with split and join tabs.
  - **`_pick_split_src(self)`** (Line 588): Pick the file to split and enable the split button.
  - **`_execute_split(self)`** (Line 598): Split the source file into preset-sized chunks with a manifest.
  - **`_pick_join_src(self)`** (Line 624): Pick the first part or manifest to join and enable the join button.
  - **`_execute_join(self)`** (Line 634): Reassemble the split parts into the original file.

#### Class `FileUnlockerPage`
*File handle inspector and process unlocker.*

- **Inherits From**: `_Page`
- **Source Line**: 655
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 658): Build the File Unlocker page with a picker, lock table, and per-process kill actions.
  - **`_pick_file(self)`** (Line 697): Pick the locked file and immediately inspect its locks.
  - **`_inspect_locks(self)`** (Line 708): List processes holding locks on the chosen file.
  - **`_terminate_proc(self, pid)`** (Line 732): Force-terminate a locking process, then re-inspect locks.

#### Class `AdsManagerPage`
*NTFS Alternate Data Stream inspector and Zone.Identifier unblocker.*

- **Inherits From**: `_Page`
- **Source Line**: 747
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 750): Build the ADS Manager page with a file picker, unblock button, and streams table.
  - **`_pick_file(self)`** (Line 787): Pick a file and list its alternate data streams.
  - **`_refresh_streams(self)`** (Line 797): List the file's NTFS streams and enable unblocking when a Zone.Identifier exists.
  - **`_unblock_file(self)`** (Line 818): Remove the Zone.Identifier stream to unblock the file.
  - **`_delete_stream(self, stream_name)`** (Line 830): Delete the named alternate data stream, then refresh.

#### Class `EventLogCleanerPage`
*Windows Event Log manager and cleaner.*

- **Inherits From**: `_Page`
- **Source Line**: 847
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 850): Build the Event Log page with stat cards, log table, and refresh/clear actions.
  - **`_load_logs(self)`** (Line 897): Load all event log channels into the table and stat cards.
  - **`_clear_all_logs(self)`** (Line 916): Confirm and clear every event log channel, then reload.

#### Class `SystemCacheRebuilderPage`
*Font, Icon, and Thumbnail cache rebuilder and Shell restarter.*

- **Inherits From**: `_Page`
- **Source Line**: 937
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 940): Build the Cache Rebuilder page with restart-shell option and rebuild button.
  - **`_execute_rebuild(self)`** (Line 970): Rebuild font and icon caches and report the outcome.

#### Class `NetworkOptimizerPage`
*DNS Resolver and TCP/IP stack tuning toolkit.*

- **Inherits From**: `_Page`
- **Source Line**: 985
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 988): Build the Network Optimizer page with TCP status form, tuning buttons, and repair actions.
  - **`_load_tcp_status(self)`** (Line 1055): Show current TCP autotuning, RSS, and ECN status.
  - **`_set_autotuning(self, level)`** (Line 1063): Set the TCP autotuning level, then refresh status.
  - **`_flush_dns(self)`** (Line 1070): Flush the DNS resolver cache and report.
  - **`_clear_arp(self)`** (Line 1076): Clear the ARP cache and report.
  - **`_reset_winsock(self)`** (Line 1082): Reset the Winsock catalog and report.
  - **`_repair_all(self)`** (Line 1088): Run the complete network repair sequence, then refresh status.

#### Class `CrashDumpCleanerPage`
*Windows Kernel & User Memory Dump and WER Sanitizer.*

- **Inherits From**: `_Page`
- **Source Line**: 1100
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1103): Build the Crash Dump page with stat cards, dumps table, and scan/clean actions.
  - **`_scan_dumps(self)`** (Line 1149): Scan crash dumps and WER reports, updating table and stat cards.
  - **`_clean_dumps(self)`** (Line 1166): Delete all discovered crash dumps, then rescan.

### Module `src/cortex_unified/ui/premium/privacy_blocker_page.py`
#### Class `_PrivacyWorker`
*Apply or revert privacy tweaks on a background thread.*

- **Inherits From**: `QObject`
- **Source Line**: 33
- **Key Methods & Handlers**:
  - **`__init__(self, mode, profile, tweak_ids)`** (Line 40): Initialize worker.
  - **`cancel(self)`** (Line 52): cancel.
  - **`run(self)`** (Line 56): run.

#### Class `PrivacyBlockerPage`
*Block Windows telemetry via profiles and per-category tweak control.*

- **Inherits From**: `_Page`
- **Source Line**: 106
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 109): __init__.
  - **`_discover_categories()`** (Line 216): Extract unique categories from the tweak catalog.
  - **`_selected_tweak_ids(self)`** (Line 222): Return tweak IDs matching the chosen profile and checked categories.
  - **`_apply(self)`** (Line 236): _apply.
  - **`_revert(self)`** (Line 254): _revert.
  - **`_set_busy(self, busy)`** (Line 264): _set_busy.
  - **`_on_progress(self, msg)`** (Line 273): _on_progress.
  - **`_on_done(self, rows)`** (Line 277): _on_done.
  - **`_fail(self, msg)`** (Line 302): _fail.

### Module `src/cortex_unified/ui/premium/process_studio_page.py`
#### Class `_ProcessScanWorker`
*Enumerate running processes off UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 34
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 39): Event handler or worker task method.

#### Class `ProcessStudioPage`
*Advanced Process & Task Studio for system inspection.*

- **Inherits From**: `_Page`
- **Source Line**: 49
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 52): Event handler or worker task method.
  - **`_scan(self)`** (Line 117): Event handler or worker task method.
  - **`_on_done(self, procs)`** (Line 124): Event handler or worker task method.
  - **`_apply_filter(self)`** (Line 130): Event handler or worker task method.
  - **`_kill_selected(self)`** (Line 162): Event handler or worker task method.
  - **`_fail(self, err)`** (Line 198): Event handler or worker task method.

### Module `src/cortex_unified/ui/premium/registry.py`
#### Class `PageSpec`
*Everything the shell needs to know about one tool page.

``factory`` is a ``"module.path:ClassName"`` string rather than an imported
class so that declaring a page costs nothing at import time - the module is
only imported when the user actually opens that page.

``icon`` is the *name* of a shipped SVG in ``resources/icons`` (without the
extension), not a Unicode glyph. Glyphs depended on system font fallback,
which Qt 6 no longer guarantees, so they rendered at inconsistent weights
and sizes - and five were duplicated across different tools.*

- **Inherits From**: `object`
- **Source Line**: 52
- **Key Methods & Handlers**:
  - **`load(self)`** (Line 71): Import and return the page class this spec points at.

### Module `src/cortex_unified/ui/premium/registry_ai_page.py`
#### Class `_RegistryWorker`
*_RegistryWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 39
- **Key Methods & Handlers**:
  - **`__init__(self, root, categories, risk_threshold, create_restore_point)`** (Line 45): Initialize worker.
  - **`cancel(self)`** (Line 60): cancel.
  - **`run(self)`** (Line 64): run.

#### Class `RegistryAICleanerPage`
*AI-enhanced registry cleaner with ML risk scoring.*

- **Inherits From**: `_Page`
- **Source Line**: 92
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 97): __init__.
  - **`_pick(self)`** (Line 179): _pick.
  - **`_run(self)`** (Line 188): _run.
  - **`_all_categories(self)`** (Line 216): _all_categories.
  - **`_on_progress(self, msg)`** (Line 222): _on_progress.
  - **`_on_done(self, data)`** (Line 226): _on_done.
  - **`_fail(self, msg)`** (Line 270): _fail.

### Module `src/cortex_unified/ui/premium/report_pages.py`
#### Class `HealthReportWorker`
*Collects read-only diagnostics and writes a report in the chosen format.*

- **Inherits From**: `QObject`
- **Source Line**: 37
- **Key Methods & Handlers**:
  - **`__init__(self, fmt)`** (Line 43): Store the report output format ("html", "json", or "text").
  - **`_collect(self)`** (Line 48): Gather system snapshot and disk health data, capturing per-section errors.
  - **`run(self)`** (Line 64): Collect diagnostics, generate the report file, and emit its path and data.

#### Class `ManifestListWorker`
*List cleanup backups: operation manifests + leftover-clean journals.

Leftover sessions appear as read-only history rows: files went to the
Recycle Bin and registry keys have .reg exports inside the session
folder, so there is deliberately no in-app restore button for them -
the row's detail says exactly where each undo artifact lives.*

- **Inherits From**: `QObject`
- **Source Line**: 81
- **Key Methods & Handlers**:
  - **`_leftover_sessions()`** (Line 94): Build read-only history rows from leftover-cleanup journals (newest first).
  - **`run(self)`** (Line 124): List restore manifests plus leftover sessions and emit the combined rows.

#### Class `RestoreWorker`
*Restores files from a backup manifest (dry-run or real, optional overwrite).

Emits ``finished`` with the restore result dict or ``failed`` with an error.*

- **Inherits From**: `QObject`
- **Source Line**: 137
- **Key Methods & Handlers**:
  - **`__init__(self, manifest_file, dry_run, overwrite)`** (Line 145): Store the manifest path plus dry-run and overwrite flags.
  - **`run(self)`** (Line 152): Run the manifest restore via RestoreManager and emit the result.

#### Class `HealthReportPage`
*Generate an exportable, shareable PC health report.*

- **Inherits From**: `_Page`
- **Source Line**: 167
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 170): Build the PC Health Report page: export buttons, progress, and preview card.
  - **`_generate(self, fmt)`** (Line 217): Disable export buttons and run HealthReportWorker for the given format.
  - **`_on_done(self, path, data)`** (Line 225): Show a summary preview of the saved report and enable opening it.
  - **`_open_last(self)`** (Line 250): Open the most recently generated report with the OS default viewer.
  - **`_fail(self, msg)`** (Line 265): Re-enable export buttons and show the report error.

#### Class `BackupsPage`
*List backup manifests and restore files from them.*

- **Inherits From**: `_Page`
- **Source Line**: 276
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 279): Build the Backups & Restore page: refresh/preview/restore buttons and a manifests table.
  - **`_on_sel(self)`** (Line 337): Enable Preview/Restore buttons based on table selection.
  - **`_load(self)`** (Line 343): Refresh the manifest list via ManifestListWorker.
  - **`_on_listed(self, manifests)`** (Line 349): Populate the backups table and show an empty state when none exist.
  - **`_selected_manifest(self)`** (Line 371): Return the file path of the currently selected backup row.
  - **`_preview(self)`** (Line 379): Dry-run the restore of the selected manifest and report what would happen.
  - **`_on_preview(self, res)`** (Line 387): Show dry-run counts (would-restore / skipped / errors) in the status line.
  - **`_restore(self)`** (Line 395): Confirm overwrite choice, then run the real restore via RestoreWorker.
  - **`_on_restored(self, res)`** (Line 418): Report restore results (restored / skipped / errors) in a dialog and status line.
  - **`_busy(self, on)`** (Line 427): Toggle progress bar and action buttons while a worker runs.
  - **`_fail(self, msg)`** (Line 434): Clear the busy state and show the worker error with a reload retry.

### Module `src/cortex_unified/ui/premium/residual_cleaner_page.py`
#### Class `_ResidualScanWorker`
*Scan for leftovers of a specific application off UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 33
- **Key Methods & Handlers**:
  - **`__init__(self, query)`** (Line 38): Event handler or worker task method.
  - **`run(self)`** (Line 42): Event handler or worker task method.

#### Class `ResidualCleanerPage`
*Residual Hunter for leftover files/folders of uninstalled software.*

- **Inherits From**: `_Page`
- **Source Line**: 67
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 70): Event handler or worker task method.
  - **`_scan(self)`** (Line 139): Event handler or worker task method.
  - **`_on_done(self, results)`** (Line 147): Event handler or worker task method.
  - **`_clean_selected(self)`** (Line 177): Event handler or worker task method.
  - **`_fail(self, err)`** (Line 206): Event handler or worker task method.

### Module `src/cortex_unified/ui/premium/s3_fifo_page.py`
#### Class `_BenchWorker`
*_BenchWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 28
- **Key Methods & Handlers**:
  - **`__init__(self, capacity, trace_len)`** (Line 33): __init__.
  - **`run(self)`** (Line 39): run.

#### Class `S3FifoPage`
*Visualise and benchmark the S3-FIFO eviction policy.*

- **Inherits From**: `_Page`
- **Source Line**: 79
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 82): __init__.
  - **`_run(self)`** (Line 135): _run.
  - **`_on_done(self, stats)`** (Line 143): _on_done.
  - **`_fail(self, msg)`** (Line 171): _fail.

### Module `src/cortex_unified/ui/premium/search_optimizer_page.py`
#### Class `_SearchWorker`
*_SearchWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 33
- **Key Methods & Handlers**:
  - **`run_status(self)`** (Line 38): run_status.
  - **`run_compact(self)`** (Line 43): run_compact.
  - **`run_rebuild(self)`** (Line 48): run_rebuild.

#### Class `SearchIndexOptimizerPage`
*UI page for Windows Search Index (Windows.edb) compaction and catalog reset.*

- **Inherits From**: `_Page`
- **Source Line**: 54
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 57): __init__.
  - **`_start_status_query(self)`** (Line 135): _start_status_query.
  - **`_on_status_ready(self, status)`** (Line 149): _on_status_ready.
  - **`_start_compact(self)`** (Line 167): _start_compact.
  - **`_start_rebuild(self)`** (Line 181): _start_rebuild.
  - **`_run_async_op(self, call_fn, status_text)`** (Line 195): _run_async_op.
  - **`_on_op_finished(self, res)`** (Line 210): _on_op_finished.

### Module `src/cortex_unified/ui/premium/secure_shredder_page.py`
#### Class `_ShredWorker`
*Background worker that shreds a list of files.*

- **Inherits From**: `QObject`
- **Source Line**: 39
- **Key Methods & Handlers**:
  - **`__init__(self, file_paths, standard, verify)`** (Line 46): Initialize worker.
  - **`cancel(self)`** (Line 59): cancel.
  - **`run(self)`** (Line 63): run.

#### Class `SecureShredderPage`
*Production-grade secure file shredder with multi-standard support.*

- **Inherits From**: `_Page`
- **Source Line**: 117
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 120): __init__.
  - **`_add_files(self)`** (Line 262): _add_files.
  - **`_add_folder(self)`** (Line 273): _add_folder.
  - **`_clear_list(self)`** (Line 292): _clear_list.
  - **`_update_file_count(self)`** (Line 299): _update_file_count.
  - **`_confirm_shred(self)`** (Line 320): _confirm_shred.
  - **`_run_shred(self, standard, verify)`** (Line 350): _run_shred.
  - **`_on_progress(self, msg)`** (Line 366): _on_progress.
  - **`_on_done(self, results)`** (Line 370): _on_done.
  - **`_fail(self, msg)`** (Line 407): _fail.

### Module `src/cortex_unified/ui/premium/settings_store.py`
### Module `src/cortex_unified/ui/premium/skeleton.py`
### Module `src/cortex_unified/ui/premium/smoothscroll.py`
### Module `src/cortex_unified/ui/premium/srum_bam_page.py`
#### Class `_SrumBamWorker`
*_SrumBamWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 35
- **Key Methods & Handlers**:
  - **`__init__(self, cleaner, entries)`** (Line 40): __init__.
  - **`run_scan(self)`** (Line 46): run_scan.
  - **`run_clean(self)`** (Line 51): run_clean.

#### Class `SrumBamCleanerPage`
*UI page for BAM/DAM execution traces and SRUM metrics.*

- **Inherits From**: `_Page`
- **Source Line**: 57
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 60): __init__.
  - **`_start_scan(self)`** (Line 117): _start_scan.
  - **`_on_scan_finished(self, report)`** (Line 131): _on_scan_finished.
  - **`_start_clean(self)`** (Line 157): _start_clean.
  - **`_on_clean_finished(self, cleaned_count)`** (Line 184): _on_clean_finished.

### Module `src/cortex_unified/ui/premium/startup_optimizer_page.py`
#### Class `_StartupScanWorker`
*Background worker: enumerate all startup entries.*

- **Inherits From**: `QObject`
- **Source Line**: 42
- **Key Methods & Handlers**:
  - **`__init__(self)`** (Line 49): Create the scan worker with a fresh cancel event.
  - **`cancel(self)`** (Line 54): Request cooperative cancellation of the running scan.
  - **`run(self)`** (Line 58): Enumerate startup entries via StartupOptimizer and emit the list.

#### Class `_DisableWorker`
*Disable selected startup entries by toggling registry values.*

- **Inherits From**: `QObject`
- **Source Line**: 73
- **Key Methods & Handlers**:
  - **`__init__(self, entries)`** (Line 80): Store the entries to disable and a cancel event.
  - **`cancel(self)`** (Line 86): Request cooperative cancellation of the disable loop.
  - **`run(self)`** (Line 90): Move each registry Run value into the CortexBackup subkey, emitting disabled entries.

#### Class `_EnableWorker`
*Re-enable startup entries from the Cortex backup registry location.*

- **Inherits From**: `QObject`
- **Source Line**: 135
- **Key Methods & Handlers**:
  - **`__init__(self, entries)`** (Line 142): Store the entries to re-enable and a cancel event.
  - **`cancel(self)`** (Line 148): Request cooperative cancellation of the enable loop.
  - **`run(self)`** (Line 152): Restore each backed-up Run value to its original key, emitting re-enabled entries.

#### Class `StartupOptimizerPage`
*Manage Windows startup entries — enable, disable, and inspect resource impact.*

- **Inherits From**: `_Page`
- **Source Line**: 251
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 254): Build the Startup Optimizer page: filter/sort bar, summary cards, and results table; auto-scans.
  - **`_run_scan(self)`** (Line 412): Disable buttons, clear the table, and start a _StartupScanWorker.
  - **`_on_scan_progress(self, msg)`** (Line 430): Show worker progress text in the status label.
  - **`_on_scan_done(self, entries)`** (Line 434): Store results, refresh table/filters, and show an empty state when nothing found.
  - **`_on_scan_fail(self, msg)`** (Line 453): Reset buttons and show the scan error with a retry option.
  - **`_apply_filters(self)`** (Line 462): Filter entries by type combo, sort by sort combo, and repopulate the table.
  - **`_populate_table(self, entries)`** (Line 474): Fill the table rows with name/type/path/command and color-coded impact status.
  - **`_update_summary(self)`** (Line 498): Refresh the Total / Enabled / Disabled / High Impact metric cards.
  - **`_selected_entries(self)`** (Line 511): Return the entries behind the currently selected table rows.
  - **`_update_buttons(self)`** (Line 518): Enable Disable/Enable buttons only when rows are selected.
  - **`_disable_selected(self)`** (Line 526): Run _DisableWorker on the selected startup entries.
  - **`_on_disable_done(self, disabled)`** (Line 545): Report disabled count and rescan to refresh the table.
  - **`_on_disable_fail(self, msg)`** (Line 555): Show the disable error with a retry option.
  - **`_enable_selected(self)`** (Line 563): Run _EnableWorker on the selected startup entries.
  - **`_on_enable_done(self, enabled)`** (Line 582): Report re-enabled count and rescan to refresh the table.
  - **`_on_enable_fail(self, msg)`** (Line 592): Show the enable error with a retry option.
  - **`_on_action_progress(self, msg)`** (Line 600): Show enable/disable worker progress in the status label.

### Module `src/cortex_unified/ui/premium/states.py`
### Module `src/cortex_unified/ui/premium/system_pages.py`
#### Class `PrivacyScanWorker`
*Background worker scanning browsers and system traces for privacy data.*

- **Inherits From**: `QObject`
- **Source Line**: 69
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 74): Scan browser data and system traces; emit both results.

#### Class `PrivacyCleanWorker`
*Background worker deleting selected browser items and system traces.*

- **Inherits From**: `QObject`
- **Source Line**: 84
- **Key Methods & Handlers**:
  - **`__init__(self, to_clean, clean_system)`** (Line 89): Store the per-browser item map and the system-traces flag.
  - **`run(self)`** (Line 95): Clean the selected browser items (and system traces if requested).

#### Class `StartupListWorker`
*Background worker listing startup items from the startup manager.*

- **Inherits From**: `QObject`
- **Source Line**: 111
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 116): Fetch the startup item list; emit it as a list of dicts.

#### Class `TaskSnapshotWorker`
*Full task-manager snapshot: CPU, memory reconciliation + process list.*

- **Inherits From**: `QObject`
- **Source Line**: 125
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 131): Take a task-manager snapshot; emit the error or the snapshot dict.

#### Class `NetworkWorker`
*Read-only snapshot of active network connections + a summary.*

- **Inherits From**: `QObject`
- **Source Line**: 144
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 150): Snapshot active connections and emit them with a summary dict.

#### Class `PrivacyPage`
*Scan and sweep browser data + system privacy traces.*

- **Inherits From**: `_Page`
- **Source Line**: 165
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 168): Build the scan/sweep buttons, results tree and state panel.
  - **`_scan(self)`** (Line 208): Launch the privacy scan worker with buttons disabled.
  - **`_on_scan(self, browsers, traces)`** (Line 216): Populate the checkable results tree from the scan results.
  - **`_sweep(self)`** (Line 255): Confirm and delete the checked browser/system items via a worker.
  - **`_on_swept(self, ok)`** (Line 285): Report the sweep result, then re-scan.
  - **`_fail(self, msg)`** (Line 293): Re-enable the scan button and show the error with a retry.

#### Class `StartupPage`
*List startup items and disable selected ones.*

- **Inherits From**: `_Page`
- **Source Line**: 299
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 302): Build the startup table with refresh/disable controls.
  - **`_load(self)`** (Line 346): Kick off the startup-items listing worker.
  - **`_on_loaded(self, items)`** (Line 352): Fill the table with the fetched startup items.
  - **`_disable(self)`** (Line 369): Confirm and disable each selected startup item, then reload.
  - **`_fail(self, msg)`** (Line 398): Re-enable refresh and show the error with a retry.

#### Class `ProcessesPage`
*Live task-manager page: CPU/memory monitor plus a sortable, searchable
process list, with a breakdown reconciling where memory actually goes.*

- **Inherits From**: `_Page`
- **Source Line**: 404
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 408): Build summary cards, per-core bars, search/live controls and the
model/view process table.
  - **`_columns(self)`** (Line 533): Declare the eight process columns once, instead of filling cells.

Numeric columns carry a ``sort_key`` returning the raw number, so the
cell can show a human string ("1.4 GB", "3.5") while the proxy still
orders on the value behind it. Those same columns opt out of the search
so typing "8" filters on names, PIDs and descriptions - the fields the
old python-side filter looked at - rather than matching stray digits in
a byte count.
  - **`_start_live(self)`** (Line 566): Load once and start the live timer if "Live" is checked.
  - **`_toggle_live(self, on)`** (Line 572): Start or stop the live refresh timer.
  - **`_tick(self)`** (Line 580): Reload the snapshot when visible and no load is in flight.
  - **`_load(self)`** (Line 585): Launch a snapshot worker, skipping if one is already running.
  - **`_on_snapshot(self, snap)`** (Line 596): Update cards, core bars, memory breakdown and the process model
from a fresh snapshot.
  - **`_render_breakdown(self, mem)`** (Line 622): Set the memory one-liner and cache the detailed HTML, pushing it
into the label only when expanded and changed.
  - **`_build_breakdown_html(self, mem)`** (Line 638): Build the explanatory HTML about hardware-reserved memory and why
process working sets don't add up to "in use".
  - **`_toggle_why(self, on)`** (Line 663): Expand/collapse the detailed memory explanation.
  - **`_apply_filter(self)`** (Line 674): Forward the search box text to the model's proxy filter.
  - **`_on_select(self)`** (Line 683): Enable End Task when a row is selected; remember its PID.
  - **`_restore_selection(self)`** (Line 692): Reselect the previously selected PID after model/filter changes.
  - **`_kill(self)`** (Line 698): Confirm and end the selected process's task, then reload.
  - **`_fail(self, msg)`** (Line 721): Show the snapshot error with retry, or a transient status message
if data is already on screen.

#### Class `NetworkPage`
*Security-minded view of active network connections and their owners.*

- **Inherits From**: `_Page`
- **Source Line**: 732
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 735): Build summary cards, search/live controls and the risk-coloured
connections table.
  - **`_start_live(self)`** (Line 824): Load once and start the live timer if "Live" is checked.
  - **`_toggle_live(self, on)`** (Line 830): Start or stop the live refresh timer.
  - **`_tick(self)`** (Line 838): Reload when visible and no load is in flight.
  - **`_load(self)`** (Line 843): Launch a connections snapshot worker, skipping if one is running.
  - **`_on_loaded(self, conns, summary)`** (Line 853): Update the summary cards and hint, then reapply the filter.
  - **`_apply_filter(self)`** (Line 877): Filter the connections by search term and the risky-only checkbox,
then refill the table.
  - **`_risk(c)`** (Line 907): ``"external"``, ``"public"`` or ``""`` for a connection.

External wins over public: an established connection out to the internet
is the stronger signal, and it is what the page checked first before the
model/view migration.
  - **`_risk_colour(self, c)`** (Line 920): Return the row colour for a process risk level.
  - **`_risk_tooltip(self, c)`** (Line 924): Return the tooltip text explaining a process risk level.
  - **`_process_icon(self, c)`** (Line 928): Real native icon where available, else a token placeholder glyph, so
the connection's owning process is never shown iconless (Req 8.3).
  - **`_columns(self)`** (Line 934): Define the table columns for the processes/connections view.
  - **`_local_text(self, c)`** (Line 959): Format the local endpoint address for the connections table.
  - **`_remote_text(self, c)`** (Line 965): Format the remote endpoint address for the connections table.
  - **`_fill(self, rows)`** (Line 971): Fill via the results view; results return through worker signals.
  - **`_socket_key(c)`** (Line 985): Identity of a connection, stable across refreshes.
  - **`_kill(self)`** (Line 989): Kill via the confirmation dialog, status bar, results view; results return through worker signals.
  - **`_fail(self, msg)`** (Line 1016): Report the worker error in the state panel, status bar, re-enable actions and clear the busy state.

#### Class `UninstallerListWorker`
*Background worker that runs uninstaller list via AppUninstaller (app uninstaller); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1030
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 1035): Run the AppUninstaller (app uninstaller) backend call off the UI thread; emit finished/failed with results.

#### Class `LeftoverScanWorker`
*Sweep standard locations for the recently uninstalled apps' leftovers.*

- **Inherits From**: `QObject`
- **Source Line**: 1044
- **Key Methods & Handlers**:
  - **`__init__(self, apps, exclusions)`** (Line 1050): Store constructor arguments (apps, exclusions) and initialize worker signals.
  - **`cancel(self)`** (Line 1058): Cooperative stop: checked between apps and inside every sweep.
  - **`run(self)`** (Line 1062): Run the leftover cleaner backend call off the UI thread; emit finished/failed with results.

#### Class `OrphanScanWorker`
*Find orphaned Program Files folders no installed app claims.*

- **Inherits From**: `QObject`
- **Source Line**: 1092
- **Key Methods & Handlers**:
  - **`__init__(self, exclusions)`** (Line 1098): Store constructor arguments (exclusions) and initialize worker signals.
  - **`cancel(self)`** (Line 1105): Request cooperative cancellation so the background operation stops promptly.
  - **`run(self)`** (Line 1109): Run the leftover cleaner backend call off the UI thread; emit finished/failed with results.

#### Class `LeftoverCleanWorker`
*Clean a reviewed batch: one journal, one restore point, cancellable.*

- **Inherits From**: `QObject`
- **Source Line**: 1124
- **Key Methods & Handlers**:
  - **`__init__(self, findings, create_restore_point, exclusions)`** (Line 1130): Initialize worker.
  - **`cancel(self)`** (Line 1140): Stop before the next item; items already cleaned stay cleaned.
  - **`run(self)`** (Line 1144): Run the leftover cleaner backend call off the UI thread; emit finished/failed with results.

#### Class `TelemetryStatusWorker`
*Background worker that runs telemetry status via TelemetryBlocker (telemetry blocker); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1163
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 1168): Run the TelemetryBlocker (telemetry blocker) backend call off the UI thread; emit finished/failed with results.

#### Class `TelemetryApplyWorker`
*Background worker that runs telemetry apply via TelemetryBlocker (telemetry blocker); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1177
- **Key Methods & Handlers**:
  - **`__init__(self, restore)`** (Line 1182): Store constructor arguments (restore) and initialize worker signals.
  - **`run(self)`** (Line 1187): Run the TelemetryBlocker (telemetry blocker) backend call off the UI thread; emit finished/failed with results.

#### Class `RegistryScanWorker`
*Background worker that runs registry scan via RegistryCleaner (registry cleaner); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1198
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 1203): Run the RegistryCleaner (registry cleaner) backend call off the UI thread; emit finished/failed with results.

#### Class `RegistryCleanWorker`
*Background worker that runs registry clean via RegistryCleaner (registry cleaner); emits finished/failed off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 1212
- **Key Methods & Handlers**:
  - **`__init__(self, entries)`** (Line 1217): Store constructor arguments (entries) and initialize worker signals.
  - **`run(self)`** (Line 1222): Run the RegistryCleaner (registry cleaner) backend call off the UI thread; emit finished/failed with results.

#### Class `UninstallerPage`
*List installed apps and launch their official uninstallers.
Post-uninstall residual cleanup lives in the dedicated Leftover
Scanner page (sidebar: Apps & Security -> Leftover Scanner).*

- **Inherits From**: `_Page`
- **Source Line**: 1524
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1529): Build the page layout (buttons, tables, title header, state panel) and connect button/worker actions.
  - **`_columns(self)`** (Line 1597): Declare the three app columns once, instead of filling cells.

The whole app dict rides along with its row in the model, so the
uninstall action reads real records instead of looking up a python list
by the view's row number - which stops being the record's index the
moment the user sorts or searches. No ``sort_key`` is needed here: all
three columns display the string they sort on. (A size column would need
one - "9 MB" sorts above "10 MB" when the comparison is textual - but
this table doesn't show size.)
  - **`_load(self)`** (Line 1614): Load via the background worker, progress state; results return through worker signals.
  - **`_on_loaded(self, apps)`** (Line 1620): Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.
  - **`_filter(self, text)`** (Line 1633): Handle filter for the page widgets and worker state.
  - **`_selected_apps(self)`** (Line 1640): Every selected app record, resolved through the proxy.

``TableBinding.selected_record()`` covers the single-selection tables;
this one acts on several rows, so it applies the same mapping per row.
Going through the proxy is the point: a view row number stops matching
the source list the moment the user sorts or searches, which is exactly
what the old ``self.tbl.item(r, 0)`` lookup got wrong.
  - **`_on_select(self)`** (Line 1661): Handle worker results: re-enable buttons and clear the busy state.
  - **`_uninstall(self)`** (Line 1665): Uninstall via the confirmation dialog; results return through worker signals.
  - **`_fail(self, msg)`** (Line 1707): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `LeftoverScannerPage`
*Dedicated sidebar page for the post-uninstall leftover scanner.

The Deep Uninstaller page only launches official uninstallers; residual
cleanup lives here so each concern stays on its own page.*

- **Inherits From**: `_Page, _LeftoverSection`
- **Source Line**: 1712
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1719): Build the page layout (widgets) and connect button/worker actions.

#### Class `TelemetryPage`
*Block / restore Windows telemetry (Windows, admin required to apply).*

- **Inherits From**: `_Page`
- **Source Line**: 1729
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1732): Build the page layout (buttons, trees, title header, state panel) and connect button/worker actions.
  - **`_refresh(self)`** (Line 1772): Refresh via the background worker, progress state; results return through worker signals.
  - **`_on_status(self, status)`** (Line 1777): Handle worker results: refresh tables/trees, update cards/labels and clear the busy state.
  - **`_apply(self, restore)`** (Line 1787): Apply via the background worker, confirmation dialog; results return through worker signals.
  - **`_on_applied(self, ok)`** (Line 1805): Handle worker results: re-enable buttons and clear the busy state.
  - **`_fail(self, msg)`** (Line 1813): Report the worker error in the state panel, re-enable actions and clear the busy state.

#### Class `RegistryPage`
*Scan for orphaned registry entries and remove them with a backup first.*

- **Inherits From**: `_Page`
- **Source Line**: 1820
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1823): Build the page layout (buttons, tables, title header, state panel) and connect button/worker actions.
  - **`_columns(self)`** (Line 1881): Declare the three entry columns once, instead of filling cells.
  - **`_scan(self)`** (Line 1889): Scan via the background worker, progress state, results view; results return through worker signals.
  - **`_on_scan(self, entries)`** (Line 1899): Handle worker results: refresh tables/trees, update the state panel, note status and clear the busy state.
  - **`_clean(self)`** (Line 1914): Clean via the background worker, confirmation dialog, progress state; results return through worker signals.
  - **`_on_clean(self, removed, backup)`** (Line 1933): Handle worker results: note status and clear the busy state.
  - **`_fail(self, msg)`** (Line 1941): Report the worker error in the state panel, re-enable actions and clear the busy state.

### Module `src/cortex_unified/ui/premium/tablemodel.py`
### Module `src/cortex_unified/ui/premium/theme.py`
### Module `src/cortex_unified/ui/premium/tokens.py`
### Module `src/cortex_unified/ui/premium/tools_pages.py`
#### Class `PowerPlanListWorker`
*PowerPlanListWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 48
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 53): run.

#### Class `PowerPlanSetWorker`
*PowerPlanSetWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 62
- **Key Methods & Handlers**:
  - **`__init__(self, guid)`** (Line 67): __init__.
  - **`run(self)`** (Line 72): run.

#### Class `ExtensionAuditWorker`
*ExtensionAuditWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 82
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 87): run.

#### Class `DriverListWorker`
*DriverListWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 138
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 143): run.

#### Class `PerformancePage`
*Switch Windows power plans - reversible, low-risk performance control.*

- **Inherits From**: `_Page`
- **Source Line**: 156
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 159): __init__.
  - **`_load(self)`** (Line 236): _load.
  - **`_on_listed(self, plans)`** (Line 242): _on_listed.
  - **`_apply(self)`** (Line 256): _apply.
  - **`_on_applied(self, ok, msg)`** (Line 279): _on_applied.
  - **`_fail(self, msg)`** (Line 288): _fail.

#### Class `BrowserExtensionsPage`
*Read-only inventory of installed browser extensions and permissions.*

- **Inherits From**: `_Page`
- **Source Line**: 298
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 301): __init__.
  - **`_load(self)`** (Line 372): _load.
  - **`_on_done(self, exts)`** (Line 378): _on_done.
  - **`_fail(self, msg)`** (Line 399): _fail.

#### Class `DriverInventoryPage`
*Read-only device-driver inventory (Cortex never auto-installs drivers).*

- **Inherits From**: `_Page`
- **Source Line**: 409
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 412): __init__.
  - **`_load(self)`** (Line 476): _load.
  - **`_on_done(self, drivers)`** (Line 483): _on_done.
  - **`_fail(self, msg)`** (Line 495): _fail.

### Module `src/cortex_unified/ui/premium/tray.py`
### Module `src/cortex_unified/ui/premium/video_duplicates_page.py`
#### Class `_VideoWorker`
*_VideoWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 25
- **Key Methods & Handlers**:
  - **`__init__(self, root, threshold)`** (Line 31): __init__.
  - **`cancel(self)`** (Line 40): cancel.
  - **`run(self)`** (Line 44): run.

#### Class `VideoDuplicatesPage`
*Find temporally-similar videos (re-encodes, trims, watermarked copies).*

- **Inherits From**: `_Page`
- **Source Line**: 59
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 62): __init__.
  - **`_pick(self)`** (Line 128): _pick.
  - **`_run(self)`** (Line 137): _run.
  - **`_on_progress(self, msg)`** (Line 148): _on_progress.
  - **`_on_done(self, groups)`** (Line 152): _on_done.
  - **`_fail(self, msg)`** (Line 185): _fail.
  - **`_optimize_video(self)`** (Line 192): Optimize selected or picked video with VideoOptimizer.

### Module `src/cortex_unified/ui/premium/wan_audit_page.py`
#### Class `_WanAuditWorker`
*Run local-only WAN & UPnP audit off the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 32
- **Key Methods & Handlers**:
  - **`__init__(self)`** (Line 38): Event handler or worker task method.
  - **`cancel(self)`** (Line 42): Event handler or worker task method.
  - **`run(self)`** (Line 45): Event handler or worker task method.

#### Class `WanAuditPage`
*Local WAN and UPnP gateway security auditor.*

- **Inherits From**: `_Page`
- **Source Line**: 59
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 62): Event handler or worker task method.
  - **`_scan(self)`** (Line 137): Event handler or worker task method.
  - **`_on_progress(self, msg)`** (Line 145): Event handler or worker task method.
  - **`_on_done(self, status)`** (Line 148): Event handler or worker task method.
  - **`_export(self)`** (Line 185): Event handler or worker task method.
  - **`_fail(self, err)`** (Line 202): Event handler or worker task method.

### Module `src/cortex_unified/ui/premium/widgets.py`
### Module `src/cortex_unified/ui/premium/win_update_repair_page.py`
#### Class `_RepairWorker`
*Background worker for Windows Update repair phases.*

- **Inherits From**: `QObject`
- **Source Line**: 36
- **Key Methods & Handlers**:
  - **`__init__(self, phases)`** (Line 43): __init__.
  - **`cancel(self)`** (Line 49): cancel.
  - **`run(self)`** (Line 53): run.

#### Class `_PreflightWorker`
*Run preflight diagnostics in background.*

- **Inherits From**: `QObject`
- **Source Line**: 91
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 97): run.

#### Class `WinUpdateRepairPage`
*Comprehensive Windows Update component repair with phase-based control.*

- **Inherits From**: `_Page`
- **Source Line**: 143
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 146): __init__.
  - **`_run_preflight(self)`** (Line 265): _run_preflight.
  - **`_pf_done(self, data)`** (Line 274): _pf_done.
  - **`_pf_fail(self, msg)`** (Line 310): _pf_fail.
  - **`_run_repair(self)`** (Line 318): _run_repair.
  - **`_on_progress(self, msg)`** (Line 352): _on_progress.
  - **`_on_done(self, data)`** (Line 356): _on_done.
  - **`_on_fail(self, msg)`** (Line 388): _on_fail.

### Module `src/cortex_unified/ui/premium/winapp2_page.py`
#### Class `_Winapp2Worker`
*_Winapp2Worker class.*

- **Inherits From**: `QObject`
- **Source Line**: 31
- **Key Methods & Handlers**:
  - **`__init__(self, cleaner, targets)`** (Line 37): __init__.
  - **`run_scan(self)`** (Line 43): run_scan.
  - **`run_clean(self)`** (Line 48): run_clean.

#### Class `Winapp2CleanerPage`
*UI page for Winapp2 community third-party application cleaning.*

- **Inherits From**: `_Page`
- **Source Line**: 58
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 61): __init__.
  - **`_start_scan(self)`** (Line 122): _start_scan.
  - **`_on_progress(self, current, total, name)`** (Line 138): _on_progress.
  - **`_on_scan_finished(self, report)`** (Line 144): _on_scan_finished.
  - **`_start_clean(self)`** (Line 166): _start_clean.
  - **`_on_clean_finished(self, cleaned_bytes, cleaned_count)`** (Line 194): _on_clean_finished.

### Module `src/cortex_unified/ui/premium/window.py`
#### Class `_LazyPageRegistry`
*A ``dict[str, QWidget]``-compatible view that builds pages on demand.

Reads like the eager dictionary it replaced - ``len()``, iteration,
``in``, and ``registry["dashboard"]`` all behave identically and report all
43 pages - but a page widget is only constructed the first time it is
actually requested, and is then cached and added to the window's
``QStackedWidget``.

This keeps every existing call site and test working (``set(win._pages)``,
``win._pages["dashboard"]``) while removing ~2.6 s from window startup.*

- **Inherits From**: `Mapping`
- **Source Line**: 129
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 142): Keep the owning window and the cache of already-built pages.
  - **`is_built(self, page_id)`** (Line 179): True when *page_id* has actually been constructed.
  - **`built_ids(self)`** (Line 184): The pages constructed so far - useful for tests and diagnostics.

#### Class `_WorkerTaskSignals`
- **Inherits From**: `QObject`
- **Source Line**: 191
- **Key Methods & Handlers**:

#### Class `_WorkerTaskRunnable`
- **Inherits From**: `QRunnable`
- **Source Line**: 196
- **Key Methods & Handlers**:
  - **`__init__(self, work_fn, signals)`** (Line 197): Event handler or worker task method.
  - **`run(self)`** (Line 202): Event handler or worker task method.

#### Class `WorkerRuntime`
*ThreadPool-based background execution runtime for GUI pages.*

- **Inherits From**: `QObject`
- **Source Line**: 210
- **Key Methods & Handlers**:
  - **`__init__(self, parent)`** (Line 213): Event handler or worker task method.
  - **`run(self, work_fn, on_result, on_error)`** (Line 217): Execute work_fn off the UI thread and dispatch results/errors via Qt signals.

#### Class `_Page`
*Base page with access to the window + palette and a vertical layout.

Scroll policy (Req 5)
---------------------
Content sits inside a single outer vertical ``QScrollArea`` (the page's
``Scroll_Container``) with ``widgetResizable=True`` and ``ScrollBarAsNeeded``
on both axes, so a scrollbar appears only when content exceeds the viewport
(Req 5.1, 5.4) and is hidden when the page fits.

Two page shapes share this base:

- **Card-heavy pages** simply add cards to ``self.v``; the *outer* area
  scrolls when the stacked cards exceed the viewport (Req 5.1).
- **List/tree/table-dominant pages** call :meth:`add_scrolling_list` (or
  apply the same policy by hand): the list gets a stretch factor plus a
  small ``minimumHeight`` so the page fits the viewport and only the *inner*
  list scrolls - no janky whole-page jump (Req 5.2). A
  :class:`SingleScrollFilter` is attached so a wheel gesture is routed to a
  single ``Scroll_Container`` and nested regions never scroll at once
  (Req 5.5).

Subclasses keep using ``self.v`` as before.*

- **Inherits From**: `QWidget`
- **Source Line**: 1365
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1394): Set up the page: window/palette refs and an outer momentum-scrolling vertical layout.
  - **`pin_footer(self, widget)`** (Line 1426): Pin *widget* below the scroll area so it is ALWAYS fully visible.

A footer added here lives *outside* the page's outer ``QScrollArea`` and
therefore is never pushed below the fold or clipped when the scrollable
content overflows. Use this for a page's primary action row (e.g. the
dashboard "Clean" button) so it stays reachable at every window size
while the scroll area (or an inner list) absorbs the overflow. Returns
the widget for convenient chaining.
  - **`attach_single_scroll(self, inner)`** (Line 1441): Route wheel gestures over ``inner`` to a single ``Scroll_Container``.

Installs a :class:`SingleScrollFilter` on ``inner`` (and its viewport
when it exposes one) wired to this page's outer scroll area, so a wheel
gesture scrolls either the inner list or the page - never both at once
(Req 5.5). Returns the filter (also retained on ``self``).
  - **`add_scrolling_list(self, inner)`** (Line 1459): Add a list/tree/table under the page's scroll policy (Req 5.2, 5.5).

Gives ``inner`` a small ``minimumHeight`` and a layout stretch factor so
the page fits the viewport and only the inner view scrolls, then routes
its wheel gestures to a single ``Scroll_Container``. Returns ``inner``
for convenient chaining.

#### Class `DashboardPage`
*1-click hero scan + reclaimable overview + category table.*

- **Inherits From**: `_Page`
- **Source Line**: 1475
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1478): Build the hero gauge, metric tiles, category tree, and pinned Clean action.
  - **`_toggle_scan(self)`** (Line 1627): Start or cancel the scan depending on current state.
  - **`_scan(self)`** (Line 1634): Launch the ScanWorker and flip the hero into scanning UI.
  - **`_cancel_scan(self)`** (Line 1648): Cancel the running scan worker and show Cancelling state.
  - **`_on_progress(self, text)`** (Line 1655): Show live scan progress text in the status label.
  - **`_on_scanned(self, report)`** (Line 1659): Render the CleanupReport: metrics, auto-checked category tree, risk badges, gauge.
  - **`_selected_bytes(self)`** (Line 1723): Sum of what's currently checked, respecting per-app/folder exclusions.
  - **`_update_selection(self)`** (Line 1741): Refresh the gauge + Clean button to show the live selected size.
  - **`_expand_category(self, item)`** (Line 1759): Lazily populate a node's contents off the UI thread when expanded.

Works for both category nodes (aggregate per root folder) and folder
nodes (drill into subfolders/files) - to any depth. All grouping runs
in a background worker so expanding never freezes the UI, even for
categories with 100k+ files.
  - **`_apply_preview(self, nid, children)`** (Line 1809): Replace a node's placeholder with worker-computed children as checkable rows.
  - **`_preview_fail(self, msg)`** (Line 1847): Report a preview failure briefly in the status bar.
  - **`_on_item_changed(self, item, column)`** (Line 1852): Track per-app / per-folder selection so cleaning respects it.
  - **`_set_subtree_check(self, item, state)`** (Line 1876): Recursively apply a check state to a node's loaded checkable descendants.
  - **`_filtered_entries(self, scan, scan_idx)`** (Line 1886): Entries for *scan* minus any the user deselected in the preview.
  - **`_clean(self, method)`** (Line 1899): Clean the checked (and not excluded) categories after a confirm dialog, via CleanWorker.
  - **`_on_clean_progress(self, text)`** (Line 1957): Show live cleaning progress text.
  - **`_on_cleaned(self, freed, items, skipped)`** (Line 1961): Report freed space and skipped files, then rescan to refresh the report.
  - **`_on_fail(self, msg)`** (Line 1974): Reset the scan UI and surface the error via the window's default handler.

#### Class `_FolderScanPage`
*Shared scaffold for pages that pick a folder and list results.

Premium redesign: Card-wrapped picker, StatCard metrics, styled table,
and a polished empty state.*

- **Inherits From**: `_Page`
- **Source Line**: 1986
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 1997): Build the shared scaffold: picker card, metric strip, results table, and delete action row.
  - **`_build_results(self)`** (Line 2105): Subclasses construct and return their specific results widget.
  - **`_pick(self)`** (Line 2111): Open a folder dialog and enable the run button on selection.
  - **`_run(self)`** (Line 2122): Subclasses launch their specific scan worker.
  - **`_start(self, worker, on_done, on_fail)`** (Line 2128): Start a scan worker with live progress + cancel support.

on_done/on_fail MUST be bound methods of this page (main-thread
QObject) so Qt queues them onto the GUI thread.
  - **`_toggle_run(self)`** (Line 2143): Cancel the running worker, or start the subclass's scan.
  - **`_on_progress(self, text)`** (Line 2153): Show live scan progress text.
  - **`_finish(self)`** (Line 2157): Reset the run button and hide progress after a worker ends.
  - **`_busy(self, on)`** (Line 2166): Toggle the progress indicator and run-button enablement.
  - **`_enable_actions(self, has_rows)`** (Line 2171): Enable or disable the delete action based on whether rows exist.
  - **`_selected_paths(self)`** (Line 2178): Return the paths in column 0 of the currently selected table rows.
  - **`_delete_selected(self)`** (Line 2190): Confirm and recycle the selected rows via DeleteSelectedWorker.
  - **`_on_deleted(self, freed, ok, blocked)`** (Line 2212): Report the recycle result and rescan the folder.
  - **`_del_fail(self, msg)`** (Line 2224): Reset busy state and surface the deletion error.

#### Class `DuplicatesPage`
*Finds byte-identical duplicate files under a chosen folder.*

- **Inherits From**: `_FolderScanPage`
- **Source Line**: 2231
- **Key Methods & Handlers**:
  - **`_build_results(self)`** (Line 2237): Build the two-column duplicate file / group table.
  - **`_run(self)`** (Line 2247): Launch the DuplicateWorker for the chosen folder.
  - **`_done(self, groups)`** (Line 2252): Fill the table with grouped duplicates and update the metric cards.
  - **`_fail(self, msg)`** (Line 2273): Reset the run state and surface the error.

#### Class `DuplicatePhotosPage`
*Finds duplicate image files under a chosen folder.*

- **Inherits From**: `_FolderScanPage`
- **Source Line**: 2279
- **Key Methods & Handlers**:
  - **`_build_results(self)`** (Line 2286): Build the two-column duplicate photo / group table.
  - **`_run(self)`** (Line 2295): Launch the DuplicatePhotosWorker for the chosen folder.
  - **`_done(self, groups)`** (Line 2301): Fill the table with grouped duplicate photos and update the metric cards.
  - **`_fail(self, msg)`** (Line 2327): Reset the run state and surface the error.

#### Class `LargeFilesPage`
*Finds large files (50 MB+) under a chosen folder, flagging AI models.*

- **Inherits From**: `_FolderScanPage`
- **Source Line**: 2333
- **Key Methods & Handlers**:
  - **`_build_results(self)`** (Line 2339): Build the file / size / tag results table.
  - **`_run(self)`** (Line 2351): Launch the LargeFilesWorker for the chosen folder.
  - **`_done(self, entries)`** (Line 2356): Fill the table, tag AI-model files as high-risk, and update metric cards.
  - **`_fail(self, msg)`** (Line 2393): Reset the run state and surface the error.

#### Class `EmptyPage`
*Finds empty files and empty directories under a chosen folder.*

- **Inherits From**: `_FolderScanPage`
- **Source Line**: 2399
- **Key Methods & Handlers**:
  - **`_build_results(self)`** (Line 2405): Build the two-column path / type results table.
  - **`_run(self)`** (Line 2414): Launch the EmptyWorker for the chosen folder.
  - **`_done(self, files, dirs)`** (Line 2419): Fill the table with empty files and directories and update metric cards.
  - **`_fail(self, msg)`** (Line 2436): Reset the run state and surface the error.

#### Class `ShredPage`
*Storage-aware secure deletion, honest about SSD limitations.*

- **Inherits From**: `_Page`
- **Source Line**: 2442
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 2445): Build the shredder card (target picker, passes, privacy level) and the free-space wipe card.
  - **`_populate_drives(self)`** (Line 2561): Fill the wipe drive combo with all existing drive letters.
  - **`_wipe_free_space(self)`** (Line 2569): License-gate, confirm, and start a FreeSpaceWipeWorker on the chosen drive.
  - **`_on_wiped(self, success, message)`** (Line 2592): Report the free-space wipe result and reset the button.
  - **`_on_wipe_fail(self, msg)`** (Line 2602): Reset the wipe UI and surface the error.
  - **`_pick(self)`** (Line 2608): Choose a file, then detect its storage medium via StorageWorker.
  - **`_on_medium(self, kind, overwrite_effective)`** (Line 2620): Show the detected medium and whether overwriting is reliable on it.
  - **`_shred(self)`** (Line 2629): Confirm, then shred via AdaptiveShredWorker (explicit PL / flash) or ShredWorker.
  - **`_on_adaptive_done(self, outcome, message, detail)`** (Line 2678): Report the adaptive shred outcome and reset the picker.
  - **`_on_done(self, outcome, reason)`** (Line 2689): Report the shred outcome and reset the picker.
  - **`_on_refused(self, kind, guidance)`** (Line 2700): Explain why overwriting was refused for this medium and offer guidance.
  - **`_fail(self, msg)`** (Line 2711): Reset the shred UI and surface the error.

#### Class `SettingsPage`
*Settings page: theme, tray, motion, update-check, smart suggestions, restore points.*

- **Inherits From**: `_Page`
- **Source Line**: 2718
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 2720): Build the appearance/preference card plus the smart-suggestion and safety cards.
  - **`_choose_theme(self, theme)`** (Line 2798): Apply the chosen theme and refresh the button highlight.
  - **`_sync_theme_buttons(self)`** (Line 2803): Give the active theme's button the accent (Primary) styling.

Uses the object-name/repolish mechanism so the highlight is driven by
the same token-based QSS as every other control, and updates live when
the theme is switched.
  - **`_on_close_to_tray_toggled(self, checked)`** (Line 2818): Persist the close-to-tray preference.
  - **`_on_reduced_motion_toggled(self, checked)`** (Line 2822): Apply and persist the reduce-motion preference.
  - **`_on_update_check_toggled(self, checked)`** (Line 2828): Persist the opt-in startup release-check preference.
  - **`_build_smart_card(self)`** (Line 2832): Build the Smart Suggestions card showing learning stats and a reset button.
  - **`_reset_smart(self)`** (Line 2858): Confirm, then wipe and reload the offline learning model.
  - **`_build_safety_card(self)`** (Line 2877): Build the restore-point card (Windows-only) with create/refresh actions and list.
  - **`_create_restore_point(self)`** (Line 2944): Start a RestorePointWorker to create a restore point.
  - **`_on_rp_created(self, status, message)`** (Line 2953): Report the create outcome per status and refresh the list.
  - **`_on_rp_fail(self, msg)`** (Line 2970): Reset the restore-point UI and surface the error.
  - **`_refresh_restore_points(self)`** (Line 2976): Load existing restore points via RestorePointListWorker.
  - **`_on_rp_listed(self, points)`** (Line 2981): Fill the restore-point table from the listed points.

### Module `src/cortex_unified/ui/premium/workers.py`
#### Class `ScanWorker`
*Runs a full category scan and emits the resulting ``CleanupReport``.

:attr:`progress` streams live status text; :meth:`cancel` sets a shared
event the engine checks during its walk, so an in-flight scan stops
early rather than running to completion.*

- **Inherits From**: `QObject`
- **Source Line**: 25
- **Key Methods & Handlers**:
  - **`__init__(self, max_risk, include_disabled)`** (Line 37): Store the risk ceiling, disabled-category flag and a shared cancel event.
  - **`cancel(self)`** (Line 44): Signal the engine to abort the in-flight scan via the shared event.
  - **`run(self)`** (Line 48): Run the category scan (emits finished with the CleanupReport, or failed).

#### Class `CleanWorker`
*Executes deletion for a previously produced report (batched + cancellable).*

- **Inherits From**: `QObject`
- **Source Line**: 62
- **Key Methods & Handlers**:
  - **`__init__(self, report, method)`** (Line 69): Hold the report to clean, the deletion method, and a cancel event.
  - **`cancel(self)`** (Line 76): Signal the engine to abort the in-flight clean via the shared event.
  - **`run(self)`** (Line 80): Clean the report's categories, emitting finished (freed, cleaned, skipped) or failed.

#### Class `DuplicateWorker`
*Finds byte-identical duplicate files under the given roots.*

- **Inherits From**: `QObject`
- **Source Line**: 102
- **Key Methods & Handlers**:
  - **`__init__(self, roots)`** (Line 108): Store the root folders to scan and a cancel event.
  - **`cancel(self)`** (Line 114): Signal the engine to abort the duplicate scan via the shared event.
  - **`run(self)`** (Line 118): Find duplicates (emits finished with {hash: [Path, ...]} groups, or failed).

#### Class `DirPreviewWorker`
*Compute a tree node's children off the UI thread (keeps expand snappy).*

- **Inherits From**: `QObject`
- **Source Line**: 232
- **Key Methods & Handlers**:
  - **`__init__(self, node_id, entries, mode, roots, prefix)`** (Line 238): Initialize worker.
  - **`run(self)`** (Line 248): Compute the node's children per mode, emitting finished (node_id, up to 400 children) or failed.

#### Class `DuplicatePhotosWorker`
*Find duplicate image files only (byte-for-byte, extension-filtered).*

- **Inherits From**: `QObject`
- **Source Line**: 262
- **Key Methods & Handlers**:
  - **`__init__(self, roots)`** (Line 274): Store the root folders to scan and a cancel event.
  - **`cancel(self)`** (Line 280): Signal the engine to abort the photo-duplicate scan via the shared event.
  - **`run(self)`** (Line 284): Find duplicate images (emits finished with {hash: [Path, ...]} groups, or failed).

#### Class `LargeFilesWorker`
*Finds the largest files under a root path.*

- **Inherits From**: `QObject`
- **Source Line**: 298
- **Key Methods & Handlers**:
  - **`__init__(self, root, min_mb)`** (Line 304): Store the scan root, minimum size in MB, and a cancel event.
  - **`cancel(self)`** (Line 311): Signal the engine to abort the large-file scan via the shared event.
  - **`run(self)`** (Line 315): Find up to 200 large files (emits finished with FileEntry list, or failed).

#### Class `EmptyWorker`
*Finds empty files and empty directories under a root path.*

- **Inherits From**: `QObject`
- **Source Line**: 327
- **Key Methods & Handlers**:
  - **`__init__(self, root)`** (Line 333): Store the scan root and a cancel event.
  - **`cancel(self)`** (Line 339): Signal the engine to abort the empty-file scan via the shared event.
  - **`run(self)`** (Line 343): Find empty files/dirs (emits finished with both lists, or failed).

#### Class `DeleteSelectedWorker`
*Delete an arbitrary list of paths via the safe SecureDeleter.*

- **Inherits From**: `QObject`
- **Source Line**: 352
- **Key Methods & Handlers**:
  - **`__init__(self, paths, method)`** (Line 358): Store the paths to delete and the deletion method.
  - **`run(self)`** (Line 364): Delete the given paths (emits finished with (freed, succeeded, blocked), or failed).

#### Class `RestorePointWorker`
*Create a Windows System Restore point (PowerShell-backed, so threaded).*

- **Inherits From**: `QObject`
- **Source Line**: 380
- **Key Methods & Handlers**:
  - **`__init__(self, description)`** (Line 386): Store the restore-point description text.
  - **`run(self)`** (Line 391): Create a restore point (emits finished with (status, message), or failed).

#### Class `RestorePointListWorker`
*List existing restore points (read-only).*

- **Inherits From**: `QObject`
- **Source Line**: 401
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 407): List restore points (emits finished with the list, or failed).

#### Class `StorageWorker`
*Detect the storage medium behind a path (subprocess-backed, so threaded).*

- **Inherits From**: `QObject`
- **Source Line**: 416
- **Key Methods & Handlers**:
  - **`__init__(self, path)`** (Line 422): Store the path whose storage medium to detect.
  - **`run(self)`** (Line 427): Detect the storage kind (emits finished with (kind, overwrite_effective), or failed).

#### Class `FreeSpaceWipeWorker`
*Overwrite a volume's free space (Windows cipher /w). Long-running.*

- **Inherits From**: `QObject`
- **Source Line**: 437
- **Key Methods & Handlers**:
  - **`__init__(self, drive_letter)`** (Line 443): Store the drive letter to wipe and a cancel event.
  - **`cancel(self)`** (Line 449): Signal cancellation; kills the cipher /w process tree promptly.
  - **`run(self)`** (Line 457): Wipe the volume's free space (emits finished with (success, message), or failed).

#### Class `ShredWorker`
*Storage-aware secure deletion of a single target.*

- **Inherits From**: `QObject`
- **Source Line**: 467
- **Key Methods & Handlers**:
  - **`__init__(self, target, passes, force_flash)`** (Line 474): Store the target, overwrite pass count, and flash-overwrite override.
  - **`run(self)`** (Line 481): Shred one target (emits finished (outcome, reason), refused, or failed).

#### Class `AdaptiveShredWorker`
*Adaptive PL0-PL3 shred (HolePunch/PULSE/WAS-Deletion).

Picks PL by storage kind + file hotness when level is 'auto', otherwise
uses the requested PL0-PL3. Verifies and reports wear/latency costs.*

- **Inherits From**: `QObject`
- **Source Line**: 501
- **Key Methods & Handlers**:
  - **`__init__(self, target, level, verify)`** (Line 511): Store the target, privacy level (None/auto or pl0-pl3), and verify flag.
  - **`run(self)`** (Line 518): Adaptive shred (emits finished with (outcome, message, detail), or failed).

#### Class `VhdxListWorker`
*Discovers WSL / Docker / Hyper-V virtual disks (read-only).*

- **Inherits From**: `QObject`
- **Source Line**: 545
- **Key Methods & Handlers**:
  - **`__init__(self)`** (Line 552): Create the shared cancel event for the discovery run.
  - **`cancel(self)`** (Line 557): Signal cancellation of the virtual-disk discovery.
  - **`run(self)`** (Line 561): Discover virtual disks (emits finished with VirtualDisk list, or failed).

#### Class `WslShutdownWorker`
*Runs ``wsl --shutdown`` so virtual disks can be detached and compacted.*

- **Inherits From**: `QObject`
- **Source Line**: 576
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 583): Shut down WSL (emits finished with (ok, message), or failed).

#### Class `VhdxCompactWorker`
*Compacts one or more virtual disks, reporting measured space returned.

Compaction is not interruptible once diskpart owns the file - cancelling
stops the run *between* disks rather than mid-disk, which is the only safe
place to stop.*

- **Inherits From**: `QObject`
- **Source Line**: 594
- **Key Methods & Handlers**:
  - **`__init__(self, disks)`** (Line 606): Store the disks to compact and a cancel event.
  - **`cancel(self)`** (Line 612): Signal cancellation; stops between disks, not mid-compaction.
  - **`run(self)`** (Line 616): Compact each disk (emits finished with CompactResult list, or failed).

#### Class `VhdxSparseWorker`
*Turns on WSL sparse mode so the bloat doesn't come back.*

- **Inherits From**: `QObject`
- **Source Line**: 635
- **Key Methods & Handlers**:
  - **`__init__(self, disk, enabled)`** (Line 642): Store the disk and whether sparse mode should be enabled.
  - **`run(self)`** (Line 648): Toggle WSL sparse mode (emits finished with (ok, message), or failed).

#### Class `ComponentStoreAnalyzeWorker`
*Runs DISM /AnalyzeComponentStore and inventories upgrade leftovers.

Both halves are read-only. Analysis can take a few minutes on a machine
with a long update history, so it never blocks the UI thread.*

- **Inherits From**: `QObject`
- **Source Line**: 663
- **Key Methods & Handlers**:
  - **`__init__(self)`** (Line 674): Create the cancel event for the analysis run.
  - **`cancel(self)`** (Line 679): Signal cancellation of the component-store analysis.
  - **`run(self)`** (Line 683): Analyze the component store (emits finished with (analysis, leftovers), or failed).

#### Class `ComponentStoreCleanWorker`
*Runs DISM /StartComponentCleanup (optionally /ResetBase).*

- **Inherits From**: `QObject`
- **Source Line**: 705
- **Key Methods & Handlers**:
  - **`__init__(self, reset_base)`** (Line 712): Store whether ResetBase should be included in the cleanup.
  - **`run(self)`** (Line 717): Run component-store cleanup (emits finished with CleanupOutcome, or failed).

#### Class `ServicingTaskWorker`
*Triggers Windows' own scheduled component-cleanup task.*

- **Inherits From**: `QObject`
- **Source Line**: 728
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 735): Trigger the servicing task (emits finished with (ok, message), or failed).

#### Class `LeftoverDeleteWorker`
*Deletes selected upgrade leftovers through the engine's guarded deleter.

Routing through ``SecureDeleter`` means the path guard still applies, so a
mistake in the leftover list cannot turn into a destructive delete.*

- **Inherits From**: `QObject`
- **Source Line**: 746
- **Key Methods & Handlers**:
  - **`__init__(self, paths, sizes)`** (Line 757): Store the leftover paths, optional size map, and a cancel event.
  - **`cancel(self)`** (Line 764): Signal cancellation of the leftover deletion run.
  - **`run(self)`** (Line 768): Delete leftovers (emits finished with (freed, removed, blocked), or failed).

#### Class `ProjectCacheScanWorker`
*Scans target folders for developer project caches across enabled categories.*

- **Inherits From**: `QObject`
- **Source Line**: 790
- **Key Methods & Handlers**:
  - **`__init__(self, target_folders, keep_recent_days, enabled_categories)`** (Line 797): Store target folders, retention days, categories, and a cancel event.
  - **`cancel(self)`** (Line 805): Signal cancellation of the project-cache scan.
  - **`run(self)`** (Line 809): Scan project caches (emits finished with resources, or failed).

#### Class `ProjectCacheCleanWorker`
*Cleans selected project caches off-thread; dry run by default.*

- **Inherits From**: `QObject`
- **Source Line**: 833
- **Key Methods & Handlers**:
  - **`__init__(self, resources, dry_run)`** (Line 840): Store the resources to clean, the dry-run flag, and a cancel event.
  - **`cancel(self)`** (Line 847): Signal cancellation of the cache cleanup run.
  - **`run(self)`** (Line 851): Clean project caches (emits finished with a results dict, or failed).

#### Class `AutoProjectCacheWorker`
*Walks all fixed drives (or known D:\code) for PROJECT_CACHE_CATEGORIES.*

- **Inherits From**: `QObject`
- **Source Line**: 878
- **Key Methods & Handlers**:
  - **`__init__(self, enabled_categories, keep_recent_days)`** (Line 885): Store enabled categories, retention days, and a cancel event.
  - **`cancel(self)`** (Line 892): Signal cancellation of the auto-discovery scan.
  - **`run(self)`** (Line 896): Auto-discover project caches (emits finished with resources, or failed).

#### Class `CacheLogSweepWorker`
*Finds large logs (*.log/*.txt) across user-selected roots (D:\code).*

- **Inherits From**: `QObject`
- **Source Line**: 918
- **Key Methods & Handlers**:
  - **`__init__(self, roots, min_size_mb)`** (Line 925): Store the roots to sweep, minimum log size, and a cancel event.
  - **`cancel(self)`** (Line 932): Signal cancellation of the log sweep.
  - **`run(self)`** (Line 936): Find large logs (emits finished with (Path, size) pairs, or failed).

#### Class `DockerFsCacheWorker`
*Measures Docker Desktop filesystem cache (AppData\Local\Docker).*

- **Inherits From**: `QObject`
- **Source Line**: 949
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 955): Measure Docker's filesystem cache (emits finished with a size dict, or failed).

#### Class `WslListWorker`
*Lists WSL distros + their ext4.vhdx sizes.*

- **Inherits From**: `QObject`
- **Source Line**: 964
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 970): List WSL distros (emits finished with distro dicts, or failed).

#### Class `LargeFileAiWorker`
*Finds large files and tags AI models vs other.*

- **Inherits From**: `QObject`
- **Source Line**: 979
- **Key Methods & Handlers**:
  - **`__init__(self, root, min_mb)`** (Line 986): Store the scan root, minimum size in MB, and a cancel event.
  - **`cancel(self)`** (Line 993): Signal cancellation of the large-file scan.
  - **`run(self)`** (Line 997): Split large files into non-AI and AI-model lists, emitting finished with both.

### Module `src/cortex_unified/ui/premium/wsl_page.py`
#### Class `_WslListWorker`
*_WslListWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 35
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 39): run.

#### Class `_WslShutdownWorker`
*_WslShutdownWorker class.*

- **Inherits From**: `QObject`
- **Source Line**: 48
- **Key Methods & Handlers**:
  - **`run(self)`** (Line 52): run.

#### Class `WslPage`
*List WSL distros, show ext4.vhdx sizes, shutdown + compact.*

- **Inherits From**: `_Page`
- **Source Line**: 62
- **Key Methods & Handlers**:
  - **`__init__(self, win)`** (Line 65): __init__.
  - **`_load(self)`** (Line 124): _load.
  - **`_on_list(self, distros)`** (Line 136): _on_list.
  - **`_shutdown(self)`** (Line 171): _shutdown.
  - **`_on_shutdown(self, ok, msg)`** (Line 187): _on_shutdown.
  - **`_compact(self)`** (Line 198): _compact.
  - **`_on_compact(self, results)`** (Line 252): _on_compact.
  - **`_fail(self, msg)`** (Line 266): _fail.

---

## 2. CLI Commands & Execution Flow

### File: `src/cortex_unified/cli/cli.py`
*Command-line interface for Cortex Cleaner (legacy ``cortex-cleaner``).

.. note::
   The modern, dry-run-first CLI is ``cortex``
   (:mod:`cortex_unified.engine.cli`), which is backed by the typed engine and
   is the recommended entry point. This command is retained because it exposes
   11 capabilities the engine CLI does not yet cover (Docker and package-cache
   cleanup, leftover heuristics, restore, reports, checkpoints, startup and
   process inspection, broken-link repair).

Import cost policy
------------------
Click builds the whole command tree at import time, so anything imported at
module scope is paid on *every* invocation - including ``--help``. Importing the
analyzers eagerly meant ``cortex-cleaner --help`` loaded 718 modules and took
~1.1 s, pulling in the Docker SDK, ``send2trash`` (-> pywin32/COM), ``psutil``
and ``pyyaml`` merely to print help text.

Each heavy dependency is therefore imported inside the single command that
needs it. The mapping is 1:1 - ``DockerCleaner`` is only used by
``docker-cleanup``, ``FileShredder`` only by ``secure-delete``, and so on - so
this defers cost without changing behaviour. Only genuinely shared, cheap
helpers stay at module scope.*

#### Command Function: `clean_empty`
- **Parameters**: `dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, cpu_priority, io_priority, checkpoint_interval, resume_from, path`
- **Line**: 92
- **Decorators**: `main.command(), click.option('--dry-run', is_flag=True, default=None, help='Show what would be deleted without actually deleting (default)'), click.option('--delete', is_flag=True, default=False, help='Permanently delete empty files and folders'), click.option('--trash', is_flag=True, default=False, help='Move empty files and folders to trash/recycle bin'), click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)'), click.option('--older-than', type=int, default=None, help='Only consider files older than N days'), click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--quiet', is_flag=True, default=False, help='Suppress all output except errors'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)'), click.option('--cpu-priority', type=click.Choice(['low', 'normal', 'high']), default='normal', help='CPU priority for scanning'), click.option('--io-priority', type=click.Choice(['low', 'normal', 'high']), default='low', help='I/O priority for scanning'), click.option('--checkpoint-interval', type=int, default=1000, help='Save checkpoint every N directories'), click.option('--resume-from', type=click.Path(), help='Resume from checkpoint file'), click.argument('path', type=click.Path(exists=True), default='.')`
- **Documentation**:
```text
Find and remove empty files and folders safely.

Dry run by default; pass --delete or --trash (with --yes to skip the
confirmation prompt) to act. Supports glob filters, an age cutoff
(--older-than), tuned thread counts and priorities, and resumable
scans via --resume-from.
```

#### Command Function: `find_large_files`
- **Parameters**: `min_size, pattern, exclude_pattern, config, no_config, verbose, log_file, json_log, threads, export, path`
- **Line**: 275
- **Decorators**: `main.command(), click.option('--min-size', type=int, default=100, help='Minimum file size in MB (default: 100)'), click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)'), click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)'), click.option('--export', type=click.Path(), help='Export results to JSON file'), click.argument('path', type=click.Path(exists=True), default='.')`
- **Documentation**:
```text
List files larger than --min-size MB under PATH, biggest first.
```

#### Command Function: `find_duplicates`
- **Parameters**: `strategy, hash_algorithm, preview, delete, pattern, exclude_pattern, config, no_config, yes, verbose, log_file, json_log, threads, export, path`
- **Line**: 371
- **Decorators**: `main.command(), click.option('--strategy', type=click.Choice(['keep_newest', 'keep_oldest', 'keep_largest', 'keep_smallest']), default='keep_newest', help='Strategy for auto-selecting duplicates'), click.option('--hash-algorithm', type=click.Choice(['md5', 'sha1', 'sha256']), default='md5', help='Hash algorithm for duplicate detection'), click.option('--preview', is_flag=True, default=False, help='Preview duplicates without deleting'), click.option('--delete', is_flag=True, default=False, help='Delete duplicates (requires confirmation)'), click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)'), click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)'), click.option('--export', type=click.Path(), help='Export results to JSON file'), click.argument('path', type=click.Path(exists=True), default='.')`
- **Documentation**:
```text
Find duplicate files by content hash.

Duplicate groups are listed with potential space savings. With
--delete, all but one file per group (chosen by --strategy) are moved
to the recycle bin after confirmation.
```

#### Command Function: `clean_temp`
- **Parameters**: `dry_run, delete, trash, min_age, exclude_pattern, config, no_config, yes, verbose, log_file, json_log`
- **Line**: 500
- **Decorators**: `main.command(), click.option('--dry-run', is_flag=True, default=True, help='Show what would be deleted without actually deleting (default)'), click.option('--delete', is_flag=True, default=False, help='Permanently delete stale temp files'), click.option('--trash', is_flag=True, default=False, help='Move stale temp files to trash/recycle bin'), click.option('--min-age', type=int, default=1, help='Only consider temp files older than N days (default: 1)'), click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')`
- **Documentation**:
```text
Find and remove stale temporary files from system temp locations safely.

Only files older than --min-age days are considered. Dry run by
default; use --delete or --trash to act.
```

#### Command Function: `analyze_disk`
- **Parameters**: `analyze, export_json, export_treemap, export_sunburst, export_dashboard, max_depth, threads, cpu_priority, io_priority, memory_limit, checkpoint_interval, resume_from, config, no_config, verbose, log_file, json_log, path`
- **Line**: 625
- **Decorators**: `main.command(), click.option('--analyze', is_flag=True, default=False, help='Analyze disk usage'), click.option('--export-json', type=click.Path(), help='Export analysis to JSON file'), click.option('--export-treemap', type=click.Path(), help='Export TreeMap visualization (HTML/PNG/SVG) - hierarchical disk usage map'), click.option('--export-sunburst', type=click.Path(), help='Export Sunburst visualization (HTML/PNG/SVG) - circular directory tree'), click.option('--export-dashboard', type=click.Path(), help='Export Interactive Dashboard (HTML/PNG/SVG) - comprehensive analysis view'), click.option('--max-depth', type=int, default=3, help='Maximum directory depth for visualization analysis (deeper = more detail)'), click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)'), click.option('--cpu-priority', type=click.Choice(['low', 'normal', 'high']), default='normal', help='CPU priority for scanning process'), click.option('--io-priority', type=click.Choice(['low', 'normal', 'high']), default='low', help='I/O priority for disk operations'), click.option('--memory-limit', type=int, default=0, help='Memory limit in MB (0 = no limit, prevents system overload)'), click.option('--checkpoint-interval', type=int, default=1000, help='Save checkpoint every N directories (for resumable scans)'), click.option('--resume-from', type=click.Path(), help='Resume from checkpoint file (continue interrupted scan)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.argument('path', type=click.Path(exists=True), default='.')`
- **Documentation**:
```text
Analyze disk usage with interactive visualizations.

This command provides comprehensive disk usage analysis with support for
interactive visualizations including TreeMaps, Sunburst charts, and dashboards.

Examples:
  cortex-cleaner analyze-disk                              # Basic analysis
  cortex-cleaner analyze-disk --export-treemap tree.html  # Interactive TreeMap
  cortex-cleaner analyze-disk --export-sunburst sun.html  # Sunburst chart
  cortex-cleaner analyze-disk --max-depth 5               # Deeper analysis
  cortex-cleaner analyze-disk --resume-from checkpoint.json  # Resume scan

Performance: Use --cpu-priority and --memory-limit to control resource usage.
```

#### Command Function: `list_startup_items`
- **Parameters**: ``
- **Line**: 824
- **Decorators**: `main.command()`
- **Documentation**:
```text
List system startup items with enabled/disabled status and location.
```

#### Command Function: `analyze_processes`
- **Parameters**: `export`
- **Line**: 853
- **Decorators**: `main.command(), click.option('--export', type=click.Path(), help='Export results to JSON file')`
- **Documentation**:
```text
Summarize running processes and services.

Prints totals for each; --export writes the full process and service
listings plus stats to a JSON file.
```

#### Command Function: `docker_cleanup`
- **Parameters**: `dry_run, clean, images, containers, volumes, networks, clean_all, config, no_config, yes, verbose, log_file, json_log, export`
- **Line**: 908
- **Decorators**: `main.command(), click.option('--dry-run', is_flag=True, default=True, help='Show what would be cleaned without actually cleaning (default)'), click.option('--clean', is_flag=True, default=False, help='Actually clean Docker resources'), click.option('--images', is_flag=True, default=False, help='Clean unused Docker images (dangling and untagged)'), click.option('--containers', is_flag=True, default=False, help='Clean stopped containers and their associated data'), click.option('--volumes', is_flag=True, default=False, help='Clean unused volumes (not attached to any container)'), click.option('--networks', is_flag=True, default=False, help='Clean unused networks (not used by any container)'), click.option('--all', 'clean_all', is_flag=True, default=False, help='Clean all Docker resources (images, containers, volumes, networks)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts (use with caution)'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output with detailed resource information'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.option('--export', type=click.Path(), help='Export results to JSON file for analysis')`
- **Documentation**:
```text
Clean Docker resources (images, containers, volumes, networks).

This command helps free up disk space by removing unused Docker resources.
By default, it performs a dry run to show what would be cleaned.

Examples:
  cortex-cleaner docker-cleanup                    # Show what would be cleaned
  cortex-cleaner docker-cleanup --clean --all     # Clean all Docker resources
  cortex-cleaner docker-cleanup --images --clean  # Clean only unused images
  cortex-cleaner docker-cleanup --export report.json  # Export findings to JSON

Safety: Creates backup manifests for potential restoration.
```

#### Command Function: `package_cleanup`
- **Parameters**: `pip, npm, yarn, conda, system, clean_all, orphaned, keep_recent_days, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export`
- **Line**: 1067
- **Decorators**: `main.command(), click.option('--pip', is_flag=True, default=False, help='Clean pip cache (Python package manager)'), click.option('--npm', is_flag=True, default=False, help='Clean npm cache (Node.js package manager)'), click.option('--yarn', is_flag=True, default=False, help='Clean yarn cache (Alternative Node.js package manager)'), click.option('--conda', is_flag=True, default=False, help='Clean conda cache (Python/R package manager)'), click.option('--system', is_flag=True, default=False, help='Clean system package manager cache (apt, dnf, pacman, brew, chocolatey)'), click.option('--all', 'clean_all', is_flag=True, default=False, help='Clean all detected package managers automatically'), click.option('--orphaned', is_flag=True, default=False, help='Find and clean orphaned packages (packages no longer needed)'), click.option('--keep-recent-days', type=int, default=7, help='Keep cache files newer than N days (preserves recent downloads)'), click.option('--dry-run', is_flag=True, default=True, help='Show what would be cleaned without actually cleaning (default)'), click.option('--clean', is_flag=True, default=False, help='Actually clean package manager resources'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts (use with caution)'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output with detailed package information'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.option('--export', type=click.Path(), help='Export results to JSON file for analysis')`
- **Documentation**:
```text
Clean package manager caches and orphaned packages.

This command helps free up disk space by cleaning package manager caches
and removing orphaned packages that are no longer needed.

Examples:
  cortex-cleaner package-cleanup                    # Show what would be cleaned
  cortex-cleaner package-cleanup --clean --all     # Clean all package managers
  cortex-cleaner package-cleanup --pip --clean     # Clean only pip cache
  cortex-cleaner package-cleanup --orphaned        # Find orphaned packages

Safety: Creates backups of package lists before making changes.
```

#### Command Function: `heuristics_scan`
- **Parameters**: `confidence_threshold, scan_registry, ml_patterns, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export, path`
- **Line**: 1215
- **Decorators**: `main.command(), click.option('--confidence-threshold', type=float, default=0.7, help='Minimum confidence score for leftover detection (0.0-1.0, higher = more certain)'), click.option('--scan-registry', is_flag=True, default=False, help='Include Windows registry analysis for orphaned entries (Windows only)'), click.option('--ml-patterns', is_flag=True, default=True, help='Use machine learning patterns for intelligent leftover detection'), click.option('--dry-run', is_flag=True, default=True, help='Show what would be cleaned without actually cleaning (default)'), click.option('--clean', is_flag=True, default=False, help='Actually clean detected leftovers (use with caution)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts (use with extreme caution)'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output with confidence scores and reasoning'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.option('--export', type=click.Path(), help='Export results to JSON file with confidence scores'), click.argument('path', type=click.Path(exists=True), default='.')`
- **Documentation**:
```text
Scan for application leftovers using advanced heuristics.

This command uses machine learning and pattern recognition to detect
leftover files and folders from uninstalled applications.

Examples:
  cortex-cleaner heuristics-scan                           # Scan current directory
  cortex-cleaner heuristics-scan --confidence-threshold 0.9  # High confidence only
  cortex-cleaner heuristics-scan --scan-registry          # Include registry analysis (Windows)
  cortex-cleaner heuristics-scan /path/to/scan            # Scan specific directory

Warning: This feature uses heuristics and may flag legitimate files.
Always review results carefully before cleaning.
```

#### Command Function: `secure_delete`
- **Parameters**: `shred, passes, verify, yes, verbose, log_file, json_log, files`
- **Line**: 1370
- **Decorators**: `main.command(), click.option('--shred', is_flag=True, default=False, help='Shred files securely'), click.option('--passes', type=int, default=3, help='Number of overwrite passes for shredding'), click.option('--verify', is_flag=True, default=True, help='Verify deletion after shredding'), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.argument('files', type=click.Path(exists=True), nargs=-1)`
- **Documentation**:
```text
Securely delete FILES (preview by default).

Without --shred only shows how each file would be shredded; with
--shred, overwrites each file with --passes passes (verifying when
--verify is on) after a confirmation prompt unless --yes is given.
```

#### Command Function: `restore`
- **Parameters**: `restore, dry_run, yes, verbose, log_file, json_log`
- **Line**: 1432
- **Decorators**: `main.command(), click.option('--restore', type=click.Path(exists=True), help='Restore from manifest file'), click.option('--dry-run', is_flag=True, default=True, help='Preview restore without actually restoring'), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')`
- **Documentation**:
```text
Restore files from a deletion manifest, or list saved backups.

With --restore MANIFEST, replays a recorded deletion (previews it
while --dry-run is active, the default). Without it, lists the
available backup manifests.
```

#### Command Function: `generate_report`
- **Parameters**: `type, export, name, verbose, log_file, json_log`
- **Line**: 1499
- **Decorators**: `main.command(), click.option('--type', type=click.Choice(['text', 'html', 'json', 'csv']), default='text', help='Report type'), click.option('--export', type=click.Path(), help='Export report to file'), click.option('--name', type=str, help='Report name'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')`
- **Documentation**:
```text
Generate a system report as text, html, json, or csv.

Captures platform and Python version details; --export copies the
generated report to another location.
```

#### Command Function: `list_checkpoints`
- **Parameters**: `config, verbose`
- **Line**: 1573
- **Decorators**: `checkpoint.command(name='list'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')`
- **Documentation**:
```text
List saved scan checkpoints with id, timestamp, path, and progress.
```

#### Command Function: `delete`
- **Parameters**: `checkpoint_id, verbose`
- **Line**: 1603
- **Decorators**: `checkpoint.command(), click.argument('checkpoint_id'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')`
- **Documentation**:
```text
Delete a saved checkpoint by its id.
```

#### Command Function: `cleanup`
- **Parameters**: `max_age, verbose`
- **Line**: 1625
- **Decorators**: `checkpoint.command(), click.option('--max-age', type=int, default=7, help='Maximum age in days (default: 7)'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')`
- **Documentation**:
```text
Delete checkpoints older than --max-age days (default: 7).
```

#### Command Function: `scan_enhanced`
- **Parameters**: `checkpoint_id, enable_checkpoints, enable_throttling, cpu_limit, memory_limit, dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, path`
- **Line**: 1665
- **Decorators**: `main.command(), click.option('--checkpoint-id', help='Resume from specific checkpoint'), click.option('--enable-checkpoints', is_flag=True, default=False, help='Enable checkpoint functionality'), click.option('--enable-throttling', is_flag=True, default=False, help='Enable resource throttling'), click.option('--cpu-limit', type=float, default=0.8, help='CPU usage limit (0.0-1.0, default: 0.8)'), click.option('--memory-limit', type=float, default=0.85, help='Memory usage limit (0.0-1.0, default: 0.85)'), click.option('--dry-run', is_flag=True, default=None, help='Show what would be deleted without actually deleting (default)'), click.option('--delete', is_flag=True, default=False, help='Permanently delete empty files and folders'), click.option('--trash', is_flag=True, default=False, help='Move empty files and folders to trash/recycle bin'), click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)'), click.option('--older-than', type=int, default=None, help='Only consider files older than N days'), click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)'), click.option('--config', type=click.Path(exists=False), help='Path to configuration file'), click.option('--no-config', is_flag=True, default=False, help="Don't load any configuration file"), click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts'), click.option('--verbose', is_flag=True, default=False, help='Enable verbose output'), click.option('--quiet', is_flag=True, default=False, help='Suppress all output except errors'), click.option('--log-file', type=click.Path(), help='Write logs to file'), click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format'), click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)'), click.argument('path', type=click.Path(exists=True), default='.')`
- **Documentation**:
```text
Empty-file scan with optional checkpointing and resource throttling.

Extends the basic scan with resumable checkpoints
(--enable-checkpoints, --checkpoint-id) and CPU/memory usage caps
(--enable-throttling, --cpu-limit, --memory-limit). Deletion
behaviour matches clean-empty.
```

#### Command Function: `scan_broken_links`
- **Parameters**: `scan_symlinks, scan_shortcuts, scan_registry, repair, backup, confidence_threshold, export, verbose, path`
- **Line**: 1860
- **Decorators**: `main.command(), click.option('--scan-symlinks', is_flag=True, default=True, help='Scan for broken symlinks'), click.option('--scan-shortcuts', is_flag=True, default=True, help='Scan for broken Windows shortcuts (.lnk files)'), click.option('--scan-registry', is_flag=True, default=False, help='Scan for broken registry references (Windows only)'), click.option('--repair', is_flag=True, default=False, help='Attempt to repair broken links'), click.option('--backup', is_flag=True, default=True, help='Create backups before repair'), click.option('--confidence-threshold', type=float, default=0.7, help='Minimum confidence score for repairs (0.0-1.0)'), click.option('--export', type=click.Path(), help='Export results to JSON file'), click.option('--verbose', '-v', is_flag=True, help='Enable verbose output'), click.argument('path', type=click.Path(exists=True), default='.')`
- **Documentation**:
```text
Scan for and optionally repair broken symlinks, shortcuts, and registry references.
```

#### Command Function: `clean_shaders_cmd`
- **Parameters**: `min_age_days, dry_run`
- **Line**: 2006
- **Decorators**: `main.command('clean-shaders'), click.option('--min-age-days', default=0, type=int, help='Minimum age in days to consider a shader file stale (default: 0)'), click.option('--dry-run', is_flag=True, default=False, help='Show cleanable shaders without deleting')`
- **Documentation**:
```text
Audit and purge DirectX and GPU vendor shader caches.
```

#### Command Function: `clean_ai_cmd`
- **Parameters**: `dry_run`
- **Line**: 2023
- **Decorators**: `main.command('clean-ai'), click.option('--dry-run', is_flag=True, default=False, help='Show AI artifacts without cleaning')`
- **Documentation**:
```text
Audit and clean Windows 11 Copilot, Recall, and SQLite WAL journals.
```

#### Command Function: `trim_ssd_cmd`
- **Parameters**: `drive`
- **Line**: 2038
- **Decorators**: `main.command('trim-ssd'), click.argument('drive', default='C')`
- **Documentation**:
```text
Trigger SSD NVMe flash block deallocation (TRIM/ReTrim).
```

#### Command Function: `vss_health_cmd`
- **Parameters**: ``
- **Line**: 2050
- **Decorators**: `main.command('vss-health')`
- **Documentation**:
```text
Inspect Volume Shadow Copy (VSS) writers and shadow storage.
```

#### Command Function: `verify_checksums_cmd`
- **Parameters**: `manifest_file`
- **Line**: 2063
- **Decorators**: `main.command('verify-checksums'), click.argument('manifest_file', type=click.Path(exists=True))`
- **Documentation**:
```text
Verify an integrity manifest (.sha256, .md5, .sfv) against files on disk.
```

### File: `src/cortex_unified/engine/cli.py`
*Modern, safe CLI for the Cortex engine.

Design principles:
* **Dry-run by default.** Nothing is deleted unless ``--apply`` is passed.
* **Honest.** ``shred`` refuses on flash media unless forced, and says why.
* **Scriptable.** ``--json`` emits machine-readable output for automation.
* **Fast.** Backed by the scandir walker + size-prefiltered dedup.

Exposed as ``cortex`` (see pyproject ``[project.scripts]``):

    cortex scan                      # what could be reclaimed (dry, human)
    cortex scan --json               # same, machine-readable
    cortex clean --apply             # actually reclaim (recycle bin)
    cortex clean --apply --method delete
    cortex duplicates PATH [PATH...]
    cortex large PATH --min-mb 200
    cortex empty PATH
    cortex shred FILE --apply        # storage-aware secure delete
    cortex leftovers scan "App"      # post-uninstall residual scan (read-only)
    cortex leftovers orphans         # unclaimed Program Files folders
    cortex leftovers clean "App" --apply   # recycle findings (+ .reg backups)*

---

## 3. Backend System Tools & Cleaners

### Module: `scripts/audit_system_tools.py`
*Audit script to inspect classes and functions across all system tools.*

### Module: `src/cortex_unified/system_tools/adaptive_sanitizer.py`
*Adaptive privacy-preserving sanitization (PL0-PL3).

Implements the graduated deletion model from:

* Ahn & Lee, *Adaptive Privacy-Preserving SSD*, arXiv:2506.02030 (2025) –
  four privacy levels selecting among address / data / parity deletion
  techniques with ML-adjusted levels.
* Li et al., *WAS-Deletion: Workload-Aware Secure Deletion for SSDs* (NSF 10446654) –
  hot/cold separation and vertical encryption allocation to cut migration
  overhead 1.2×–12.9×.
* HolePunch (Harvard, 2025) – puncturable PRF + TPM journaling for
  crash-consistent cryptographic erasure on black-box SSDs.
* PULSE (NSF 10633397, ACM TEC 2025) – low-disturbance page-overwrite
  for 3D NAND (SLC robust, TLC median RBER 0.57% FG).
* FlashFox (Comput. J. 2025) – RAID-4 secret-sharing scrubbing, 15%
  endurance saving.

Why this module exists
----------------------
``engine/secure_delete.py`` correctly refuses to *pretend* that overwriting
an SSD works (wear-leveling + out-of-place writes leave the original
recoverable, median RBER >0.93% on FG SLC, ~13% on TLC per PULSE). Naively
calling ``shred`` on flash is therefore **less private and more wear** than
doing nothing. This module gives callers a *graduated* knob:

* PL0 – block erase (highest assurance, heavy wear, HDD: 3-pass overwrite,
  SSD: ATA Secure Erase / NVMe Format + TRIM).
* PL1 – page scrubbing/overwrite pulses (PULSE-low-disturbance).
* PL2 – parity/ECC disruption (crypto-erase / TRIM + key destruction).
* PL3 – controller block lockout (mark bad-block / TRIM range).

The caller picks a level or lets the sanitizer auto-pick by storage kind
and file hotness (WAS-Deletion). Every path is still vetted by
``PathGuard`` first.

All operations are *verified*: after sanitization we attempt to read the
original LBAs and/or check TRIM completion, reporting verifiability
(high/medium/low per paper Table 2). On non-Windows or without elevation
we degrade gracefully and report what would have run.

References
----------
* Ahn/Lee §4 Table 1 (PL0-PL3 trade-offs), §5 Table 2 (efficiency vs
  verifiability).
* WAS-Deletion §3 (hot/cold splitting, vertical encryption, adaptive
  region scheduling).
* HolePunch §3-5 (PPRF + TPM journaling).
* PULSE §4 (sub-block aware victim selection, hotness allocator).*

#### Class `PrivacyLevel`
PL0-PL3 per Ahn & Lee §4.

* PL0 – full block erase (HDD overwrite, SSD secure-erase)
* PL1 – page scrubbing / overwrite pulses (PULSE)
* PL2 – parity/ECC disruption (crypto erase)
* PL3 – controller block lockout (TRIM range)


#### Class `SanitizeResult`
Outcome of one sanitization attempt.

- **`to_dict(self)`** (Line 103): To dict.

#### Class `AdaptiveSanitizer`
Graduated sanitizer.

Usage::

    san = AdaptiveSanitizer()
    res = san.sanitize(Path("secret.dat"), PrivacyLevel.PL2)
    if not res.success: ...

- **`__init__(self, guard, probe)`** (Line 150): Initialize Adaptive Sanitizer.
- **`auto_level(self, path, requested)`** (Line 161): Pick PL if caller did not request one.

* HDD + file -> PL0 (overwrite effective)
* SSD + hot file -> PL2 (low wear, WAS-Deletion hot path)
* SSD + cold file -> PL1 (PULSE) if elevated, else PL2
* Unknown -> PL2 (safe default per paper §6)
- **`sanitize(self, path, level, verify, force, timeout)`** (Line 186): Sanitize *path* at *level* (auto if None).

Steps (HolePunch journaling idea):
1. Guard check (fail-closed)
2. Storage probe + auto-level
3. Pre-journal (write intent to sidecar for crash consistency)
4. Execute PL-specific method
5. Verify (read-back / TRIM poll)
6. Commit journal
- **`_execute(self, p, lvl, kind, verify, force, timeout)`** (Line 250): Dispatch PL.

Each PL degrades gracefully when not elevated / not Windows.
- **`_pl0(self, p, kind, verify, force, timeout)`** (Line 267): _pl0.
- **`_pl1(self, p, kind, verify, force, timeout)`** (Line 301): _pl1.
- **`_pl2(self, p, kind, verify, timeout)`** (Line 380): _pl2.
- **`_pl3(self, p, kind, verify, timeout)`** (Line 435): _pl3.
- **`_trim_parent(self, p)`** (Line 458): Best-effort TRIM hint for the parent filesystem.

On Windows we ask the FS to TRIM the free range via
``fsutil volume diskfree`` side-effect or ``defrag /L`` not. The most
portable hint is ``fsutil file queryAllocRanges`` not needed; we just
run ``fsutil volume diskfree C:`` which triggers a no-op TRIM probe and
is harmless. Silently ignored on failure / non-Windows.

### Module: `src/cortex_unified/system_tools/ai_telemetry_cleaner.py`
*Windows 11 AI, Copilot, Recall & Semantic Telemetry Cleaner.

Research Grounding
------------------
* Windows 11 Copilot & Windows Recall Storage Architecture (Microsoft Docs, 2024-2025):
  Windows Recall takes continuous periodic UI screenshots, extracts text via OCR,
  and generates local vector embeddings stored in SQLite databases under:
  `%LOCALAPPDATA%\CoreAIPlatform.00\UKP` and `SemanticSearch` stores.
* Microsoft Edge & Windows AI WebView2 Cache:
  Generative AI prompts, history, and transient vector data are cached in
  `Microsoft.Copilot_*` application containers and Edge IndexedDB stores.
* Windows 11 24H2 CapabilityAccessManager Bloat Bug:
  `CapabilityAccessManager.db-wal` (Write-Ahead Log) frequently fails to checkpoint,
  expanding into tens of gigabytes of unindexed disk consumption.

This module safely analyzes Windows AI artifacts, checkpoints/truncates bloated
SQLite WAL journals without data corruption, and purges unreferenced offline caches.*

#### Class `AiArtifactInfo`
Detailed metadata for a discovered AI or Copilot local storage artifact.

- **`to_dict(self)`** (Line 45): To dict.

#### Class `AiTelemetryReport`
Comprehensive analysis report of Windows AI and generative telemetry artifacts.

- **`to_dict(self)`** (Line 68): To dict.

#### Class `AiCleanResult`
Results of AI cache cleaning and SQLite WAL checkpoint operations.

- **`to_dict(self)`** (Line 89): To dict.

#### Class `AiTelemetryCleaner`
Forensic inspector and optimizer for Windows 11 AI and Recall caches.

- **`__init__(self)`** (Line 103): Initialize Ai Telemetry Cleaner.
- **`_get_search_roots(self)`** (Line 107): Resolve candidate search locations dynamically from active user and system environments.
- **`scan(self)`** (Line 157): Examine local disk for AI artifacts, Recall databases, and inflated WAL files.
- **`_record_artifact(self, report, name, category, path, description, is_wal)`** (Line 183): _record_artifact.
- **`checkpoint_wal_journal(self, wal_path)`** (Line 216): Safely truncate a SQLite WAL file by connecting to its parent DB and executing PRAGMA wal_checkpoint(TRUNCATE).
- **`clean(self, checkpoint_wal, dry_run)`** (Line 246): Purge temporary AI caches and truncate uncheckpointed SQLite WAL journals.

### Module: `src/cortex_unified/system_tools/app_uninstaller.py`
*Windows Application Uninstaller for Cortex Cleaner.

Reads installed software from the Windows Registry Uninstall keys
and provides safe uninstallation + silent uninstall support.*

#### Class `AppUninstaller`
Lists and uninstalls Windows applications via the Registry.

- **`__init__(self)`** (Line 22): Initialize App Uninstaller.
- **`get_installed_apps(self)`** (Line 30): Return a deduplicated, sorted list of installed applications.
- **`uninstall_app(self, app_info, silent)`** (Line 79): Execute the uninstall string for an application.

Args:
    app_info: dict returned by get_installed_apps()
    silent: if True, attempt to add quiet-mode flags for MSI-based installers
Returns:
    True if the uninstaller process was launched successfully.
- **`get_app_size_mb(self, app_info)`** (Line 119): Return estimated size in MB from the registry's EstimatedSize (KB) value.
- **`_read_app_entry(winreg, hive, parent_path, subkey_name)`** (Line 131): Read a single Uninstall subkey and return an app dict, or None.

### Module: `src/cortex_unified/system_tools/app_updater.py`
*Software Updater - a safe GUI-friendly wrapper over Windows Package Manager.

``winget`` can update most installed apps, but it's command-line only and
intimidating. This wraps it: list what's upgradable, then upgrade selected apps
(or all) with explicit confirmation. Keeping third-party apps current is a real
security win, and unlike shady updaters this bundles nothing and hides nothing -
it just drives Microsoft's own tool.

Parsing note: ``winget upgrade`` has no stable machine-readable output, so we
parse its fixed-width table by locating column offsets from the header row -
robust to winget truncating long names with an ellipsis. All calls are
time-boxed; upgrades are launched non-interactively with agreements accepted.*

#### Class `UpgradableApp`
Upgradable App data container.

- **`to_dict(self)`** (Line 40): To dict.

#### Class `AppUpdater`
List and apply application updates via winget.

- **`__init__(self)`** (Line 54): Initialize App Updater.
- **`is_available()`** (Line 59): True if winget is installed and usable.
- **`list_upgradable(self)`** (Line 63): Return apps with available updates. Empty list if winget is absent.
- **`upgrade(self, package_id)`** (Line 72): Upgrade a single package by its winget Id.
- **`upgrade_all(self)`** (Line 91): Upgrade every upgradable package (caller must confirm first).
- **`parse_upgrade_output(text)`** (Line 105): Parse winget's fixed-width upgrade table into structured rows.
- **`_run(self, cmd, timeout)`** (Line 153): _run.

### Module: `src/cortex_unified/system_tools/bitlocker_auditor.py`
*Cortex Cleaner — BitLocker & Drive Encryption Auditor.

Audits hardware and volume encryption status across all storage volumes:
- Queries BitLocker protection state, encryption percentage, and conversion status.
- Audits encryption ciphers (XTS-AES 128, XTS-AES 256, AES-CBC).
- Identifies active Key Protectors (TPM, PIN, Recovery Password).
- Alerts on unprotected volumes containing sensitive user data or system files.*

#### Class `EncryptedVolumeInfo`
Encrypted Volume Info data container.

- **`is_protected(self)`** (Line 37): Is protected.
- **`is_fully_encrypted(self)`** (Line 42): Is fully encrypted.

#### Class `BitLockerAuditReport`
Bit Locker Audit Report data container.


#### Class `BitLockerAuditor`
Enterprise BitLocker Drive Encryption Auditor.

- **`__init__(self)`** (Line 61): Initialize Bit Locker Auditor.
- **`audit(self)`** (Line 65): Run complete BitLocker audit across all physical and logical volumes.
- **`_query_manage_bde(self)`** (Line 99): Query BitLocker status via manage-bde command line.
- **`_query_wmi_powershell(self)`** (Line 185): Fallback querying Get-BitLockerVolume via PowerShell.

### Module: `src/cortex_unified/system_tools/bitrot_scrubber.py`
*Cortex Cleaner — Silent BitRot & File Integrity Scrubber.

Detects silent archival corruption, bit flips, and storage degradation:
- Maintains a lightweight SQLite cryptographic integrity database.
- Calculates streaming SHA-256 hashes of critical files, photos, and system libraries.
- During scrub passes, detects files whose modified timestamp is unchanged but cryptographic hash has mutated (silent bitrot).
- Alerts on corrupted files, bit flip anomalies, and unauthorized tampering.*

#### Class `ScrubberRecord`
Scrubber Record data container.


#### Class `BitRotIssue`
Bit Rot Issue data container.


#### Class `BitRotScrubReport`
Bit Rot Scrub Report data container.


#### Class `BitRotScrubber`
Enterprise BitRot Scrubber & Integrity Baseline Manager.

- **`__init__(self, db_path)`** (Line 60): Initialize Bit Rot Scrubber.
- **`_init_db(self)`** (Line 71): Initialize integrity database schema.
- **`_compute_sha256(path)`** (Line 88): Stream SHA-256 calculation for arbitrary file sizes.
- **`scrub(self, target_dir, max_files)`** (Line 100): Perform a cryptographic integrity scrub on target directory.
- **`reset_baseline(self, target_dir)`** (Line 188): Reset records in integrity database.

### Module: `src/cortex_unified/system_tools/boot_performance.py`
*Boot performance analysis - using Windows' OWN boot measurements.

Windows records detailed boot diagnostics in the event log
``Microsoft-Windows-Diagnostics-Performance/Operational``:

* Event ID 100 - a summary of each boot, including total boot time and the
  "main path" boot time (until the desktop is usable), in milliseconds.
* Event IDs 101/102/103/109 - specific apps, drivers, services or devices that
  Windows measured as taking *longer than usual* and thereby degrading your
  boot, each with the offending name and time impact.

Because these numbers come straight from Windows' own instrumentation, this is
an honest answer to "why is my PC slow to start?" - no guessing, no fabricated
"boot score". Read-only.*

#### Class `BootRecord`
Boot Record data container.

- **`boot_seconds(self)`** (Line 52): Boot seconds.
- **`to_dict(self)`** (Line 56): To dict.

#### Class `BootIssue`
Boot Issue data container.

- **`impact_seconds(self)`** (Line 71): Impact seconds.
- **`to_dict(self)`** (Line 75): To dict.

#### Class `BootPerformanceMonitor`
Reads Windows boot diagnostics (read-only).

- **`is_supported()`** (Line 85): Is supported.
- **`analyze(self, max_boots, max_issues)`** (Line 89): Analyze.
- **`_script(max_boots, max_issues)`** (Line 105): _script.
- **`_parse(out)`** (Line 126): _parse.
- **`_run(self, script)`** (Line 180): _run.

### Module: `src/cortex_unified/system_tools/browser_cleaner.py`
*Deep Browser Cleaner — IndexedDB, Service Workers, Code Cache, GPU cache, cookies.

Research grounding
------------------
* BleachBit 6.0 (2024): deeper Chromium (component cache, extension cache,
  Graphite Dawn cache, shader cache, DIPS, crash reports, code cache,
  media device salts, reporting data, IndexedDB, network state, search
  suggestions) + Firefox (storage, permissions, bounce tracking, site
  security, alternate services, favicons, session backups).
* CCleaner / Wise Disk Cleaner: scheduled cleanup with persistent exclusions,
  browser cache rules with granular toggles.
* Chromium docs: Code Cache (V8 bytecode), GPUCache, ShaderCache,
  ServiceWorker CacheStorage, IndexedDB LevelDB, MediaDeviceSalts.
* SQLite vacuuming: Firefox places.sqlite, Chrome History/Login Data.
* CleanerML + winapp2.ini: custom cleaners for niche apps.

Why this matters
------------------
* Standard temp cleaners miss IndexedDB (GBs of site data), Service Workers
  (offline caches), Code Cache (V8), GPU/Shader (hundreds of MB).
* SQLite databases bloat + fragment; vacuuming reclaims space + speed.
* Cookie manager with keep-list is #1 user-requested CCleaner feature.

Design — dynamic, no hardcoded profile paths
* Profile discovery via platformdirs + registry + JSON (Chrome Local State,
  Firefox profiles.ini), not C:\\\\Users\... assumptions.
* Per-browser handlers: ChromiumHandler, FirefoxHandler, EdgeHandler,
  OperaHandler, BraveHandler — each discovers its own cache locations.
* All cleaners expose `scan() -> List[Cleanable>` + `clean(paths)` +
  `vacuum_databases()` with progress/cancel, dry-run preview.
* Cookie manager: keep-list regex + sqlite `SELECT host_key FROM cookies`
  filtering, not whole-file delete.
* Safety: never delete Login Data / passwords unless explicit; Expert Mode
  gate for sensitive deletions.

Usage::

    from cortex_unified.system_tools.browser_cleaner import DeepBrowserCleaner
    cleaner = DeepBrowserCleaner()
    items = cleaner.scan()
    cleaner.clean([i.path for i in items if i.category == "Cache"])

References
----------
* BleachBit 6.0.0 release notes (bleachbit.org)
* Chromium source: components/viz, third_party/blink/renderer
* Mozilla Firefox profile docs
* CCleaner browser cache rules*

#### Class `Cleanable`
Cleanable data container.


#### Class `DeepBrowserCleaner`
Deep Browser Cleaner.

- **`__init__(self, keep_cookies, progress, cancel)`** (Line 158): Initialize Deep Browser Cleaner.
- **`scan(self)`** (Line 167): Scan.
- **`_scan_chromium_profile(self, profile, browser)`** (Line 183): _scan_chromium_profile.
- **`_scan_firefox_profile(self, profile)`** (Line 225): _scan_firefox_profile.
- **`clean(self, paths, shred)`** (Line 257): Clean.
- **`clean_cookies_keep_list(self, cookies_db)`** (Line 285): Delete cookies not matching keep-list, return removed count.
- **`vacuum_databases(self, dbs)`** (Line 309): VACUUM SQLite DBs, return saved bytes per DB.

### Module: `src/cortex_unified/system_tools/browser_deep_cleaner.py`
*Cortex Cleaner — Forensic Multi-Browser Deep Privacy & Cache Sanitizer.

Scans and cleans:
1. Web Cache, GPU Cache, and Code Cache (JS/WASM).
2. Service Worker CacheStorage and IndexedDB blobs.
3. Crashpad memory dumps, JumpListIcons, and media caches.
Across Chrome, Edge, Firefox, Brave, Opera, Opera GX, Vivaldi, and Arc while preserving user logins and cookies.*

#### Class `BrowserTarget`
Browser Target data container.


#### Class `BrowserCleanResult`
Browser Clean Result data container.


#### Class `BrowserDeepCleaner`
Production Multi-Browser cache and forensic artifact sanitizer.

- **`_dir_stats(cls, path)`** (Line 49): Compute size in bytes and file count for directory.
- **`scan_browser_caches(cls)`** (Line 69): Scan all detected web browsers for non-essential cache and transient stores.
- **`clean_targets(cls, targets)`** (Line 145): Purge selected browser cache directories.

### Module: `src/cortex_unified/system_tools/browser_extensions.py`
*Browser-extension audit - read-only inventory of installed extensions.

Scans the on-disk extension folders of Chromium-based browsers (Chrome, Edge,
Brave, Vivaldi) and Firefox to list what's installed, reading each extension's
own manifest for its name, version and requested permissions. This is purely
informational: it helps a user notice extensions they forgot about or ones
requesting broad permissions. It never disables or removes anything - browsers
guard their own extension state, and removing files out from under them can
corrupt a profile.*

#### Class `BrowserExtension`
Browser Extension data container.

- **`broad_permissions(self)`** (Line 36): True if the extension requests notably powerful permissions.
- **`to_dict(self)`** (Line 43): To dict.

#### Class `BrowserExtensionAuditor`
Read-only inventory of installed browser extensions.

- **`__init__(self, home)`** (Line 66): Initialize Browser Extension Auditor.
- **`_localappdata(self)`** (Line 70): _localappdata.
- **`audit(self)`** (Line 79): Audit.
- **`_scan_chromium(self)`** (Line 88): _scan_chromium.
- **`_scan_chromium_ext_root(self, browser, ext_root)`** (Line 106): _scan_chromium_ext_root.
- **`_from_chromium_manifest(browser, ext_id, manifest)`** (Line 130): _from_chromium_manifest.
- **`_firefox_root(self)`** (Line 147): _firefox_root.
- **`_scan_firefox(self)`** (Line 156): _scan_firefox.
- **`_safe_iterdir(path)`** (Line 189): _safe_iterdir.
- **`_read_manifest(path)`** (Line 199): _read_manifest.

### Module: `src/cortex_unified/system_tools/checksum_matrix.py`
*Forensic Checksum Matrix & Integrity Manifest Generator/Verifier.

Research Grounding
------------------
* File Integrity Verification Standards (FIPS 180-4, RFC 1321, ISO 3309):
  Data corruption, silent bit-rot on long-term storage, and transfer alterations
  require verifiable cryptographic hashes.
* Enterprise File Manager Formats (Total Commander, Directory Opus, FreeCommander):
  Batch verification manifests:
  - `.sfv` (Simple File Verification - CRC32 checksums)
  - `.md5` (BSD / GNU coreutils md5sum standard format)
  - `.sha256` (GNU coreutils sha256sum standard format)

This module provides multithreaded chunked streaming hash computation
(CRC32, MD5, SHA-1, SHA-256, SHA-512) and batch manifest generation/verification
across entire directory trees.*

#### Class `FileChecksumResult`
Calculated cryptographic and cyclic redundancy hashes for a file.

- **`to_dict(self)`** (Line 48): To dict.

#### Class `ManifestVerifyItem`
Individual verification status of a file against its manifest entry.

- **`to_dict(self)`** (Line 71): To dict.

#### Class `ManifestVerificationReport`
Consolidated outcome of verifying a manifest file against on-disk files.

- **`is_all_valid(self)`** (Line 96): Is all valid.
- **`to_dict(self)`** (Line 100): To dict.

#### Class `ChecksumMatrix`
Production file hashing, manifest generation, and integrity verification engine.

- **`__init__(self)`** (Line 119): Initialize Checksum Matrix.
- **`hash_file(self, file_path, algorithms)`** (Line 123): Stream a file through selected hash algorithms in parallel.
- **`generate_manifest(self, directory, output_file, algorithm, recursive)`** (Line 173): Scan directory and write standard checksum manifest file (.sha256, .md5, or .sfv).
- **`verify_manifest(self, manifest_file)`** (Line 216): Parse manifest (.sha256, .md5, .sfv) and verify all referenced files.

### Module: `src/cortex_unified/system_tools/compact_os.py`
*NTFS CompactOS / per-folder NTFS compression support.

Research grounding
------------------
* "CompactOS in Windows 10/11" (Microsoft Docs, 2025) – ``compact /compactos``
  and per-folder ``compact`` manage the compressed OS so Windows Update and
  clean installs shrink dramatically.
* "Space recovery via NTFS compression" (USENIX ATC 2024) – compressible file
  types (text, logs, JSON, XML, source, docs) routinely gain 50–75%; already
  compressed media (JPEG/PNG/MP4/ZIP) gain ~nothing and hurt CPU on read.

This module is **read-first**: it scans and *estimates* how much a folder would
free up, and only ever compresses when explicitly asked (and refuses opaque /
already-compressed / system folders). Everything is Windows-only and shelled
out to ``compact`` / ``fsutil`` through the cancellable, tree-safe ``proc.run``
helper - never a blocking raw child.

Safety rules enforced:
* ``compact_folder`` requires an elevated prompt (``compact`` needs admin).
* System trees (``C:\Windows``, ``C:\Program Files*``, ``C:\ProgramData``,
  ``$Recycle.Bin``, System Volume Information) are never compressed.
* Folders that are already fully compressed are skipped (no point).
* Only "compressible" content influences the *estimate*: text/log/code/docs
  count fully, already-compressed media count near zero.
* Unknown/opaque file types are treated conservatively.

Usage::

    from cortex_unified.system_tools.compact_os import CompactOSManager
    m = CompactOSManager()
    candidates = m.find_compressible_folders("C:/Users/admin")  # [{...}]
    m.compact_folder("C:/Users/admin/Downloads/old-log-archive")

The manager never compresses on its own - callers (a UI page) decide.

References
----------
* Microsoft, "compact and compact.exe" documentation.
* Microsoft, "Compact OS, single-instancing, and image optimization".
* USENIX ATC 2024, applicability of NTFS compression to modern workloads.*

#### Class `FolderEstimate`
Folder Estimate data container.

- **`to_dict(self)`** (Line 106): To dict.

#### Class `CompressionResult`
Compression Result data container.


#### Class `CompactOSManager`
Read-first NTFS compaction support (estimate + explicit action).

- **`__init__(self)`** (Line 131): Initialize Compact O S Manager.
- **`is_supported()`** (Line 139): Is supported.
- **`is_admin(self)`** (Line 143): Whether the current process can run elevated ``compact`` commands.
- **`compactos_query(self)`** (Line 157): Return CompactOS status for the OS volume.

``compact /compactos:query`` yields one of: Never / Partial / Always.
- **`drive_compression_state(self, drive)`** (Line 177): Per-drive compression state via ``fsutil volume compression``.
- **`find_compressible_folders(self, root, min_size_mb, cancel_event, progress_callback)`** (Line 192): Scan *root* (1 level of subdirectories) for compressible folders.

Returns a list of :class:`FolderEstimate` for folders whose *estimated*
savings exceed ``min_size_mb``. Read-only: does not compress anything.
- **`_estimate_folder(self, folder, cancel_event, progress_callback)`** (Line 234): Walk *folder* and estimate compressible bytes + savings.
- **`_check_compression_attribute(self, folder)`** (Line 292): Best-effort: is the folder already flagged compressed on NTFS?
- **`compact_folder(self, path, recursive, cancel_event)`** (Line 308): Compress an NTFS folder (and optionally its subtree).

Requires an elevated prompt. Refuses system trees and blocked names.
Returns a :class:`CompressionResult`.
- **`_parse_failure(out)`** (Line 349): _parse_failure.
- **`_run(self, args, timeout, cancel_event)`** (Line 364): _run.

### Module: `src/cortex_unified/system_tools/component_store.py`
*Component store (WinSxS) analysis and Windows upgrade leftovers.

``C:\Windows`` bloat is almost always WinSxS plus upgrade leftovers, and
hand-deleting either breaks Windows Update, feature repair, or the ability to
uninstall installed software. This module measures the store read-only via
``DISM /AnalyzeComponentStore``, cleans it the supported way
(``DISM /StartComponentCleanup``, with ``/ResetBase`` as an explicit opt-in
because it permanently blocks uninstalling currently installed updates), and
inventories leftovers such as ``Windows.old`` with the cost of removing each.
WinSxS and ``C:\Windows\Installer`` are reported, never deleted directly.
Windows-only; every subprocess call is time-boxed with a hidden window and
nothing modifies the system unless a cleanup method is called explicitly.*

#### Class `LeftoverRisk`
What you give up by removing a leftover.


#### Class `StoreAnalysis`
Result of ``DISM /AnalyzeComponentStore`` - all figures from Windows.

- **`explorer_gap_note(self)`** (Line 65): Why Explorer's WinSxS figure exceeds the actual on-disk size.
- **`reclaimable_estimate(self)`** (Line 79): Upper bound on what a cleanup could return.

Only the backup/disabled-feature and cache portions are candidates; the
part shared with Windows is never reclaimable. This is Windows' own
breakdown, not a guess of ours.
- **`to_dict(self)`** (Line 88): To dict.

#### Class `Leftover`
One upgrade/servicing leftover on disk.

- **`removable_here(self)`** (Line 120): True when Cortex may delete this itself.
- **`rollback_expired(self)`** (Line 125): True once Windows' own rollback window has passed.
- **`to_dict(self)`** (Line 129): To dict.

#### Class `CleanupOutcome`
Result of a component-store cleanup, with measured before/after.

- **`freed_bytes(self)`** (Line 157): Freed bytes.
- **`to_dict(self)`** (Line 161): To dict.

#### Class `ComponentStore`
Analyze and clean the WinSxS component store; inventory leftovers.

- **`__init__(self)`** (Line 177): Initialize Component Store.
- **`is_supported()`** (Line 182): Is supported.
- **`is_elevated()`** (Line 187): True when running as Administrator (required for every cleanup).
- **`analyze(self, timeout, cancel_event)`** (Line 199): Run ``DISM /AnalyzeComponentStore`` and parse Windows' own figures.
- **`_parse_analysis(out)`** (Line 216): Parse DISM's human-readable report into numbers.

DISM localizes its output, so parsing is keyed on the stable English
labels and degrades to "unknown" (0) rather than guessing when a label
isn't found - a wrong number here would be worse than none.
- **`find_leftovers(self, progress, cancel_event, analysis)`** (Line 281): Inventory upgrade/servicing leftovers with size, age and cost.

Pass ``analysis`` to source the component store's size from DISM instead
of walking ``WinSxS``. That is both far faster (the folder holds hundreds
of thousands of entries) and *more correct*: walking it counts each hard
link separately, which is exactly the inflated figure Explorer shows and
that this page exists to explain.
- **`_try_remove_spurious_package(self, timeout)`** (Line 425): Attempt to remove the deeply-superseded 24H2 rollup fix package.

Returns (removed, log). Failure is benign (package absent or not
superseded) – DISM simply fails, no store harm.
- **`cleanup(self, reset_base, timeout, progress, cancel_event, auto_fix_spurious)`** (Line 443): Run ``DISM /StartComponentCleanup``, optionally with ``/ResetBase``.

``reset_base`` removes *all* superseded versions, which permanently
prevents uninstalling the updates currently installed. Callers must have
made that trade-off explicit to the user before passing ``True``.

``auto_fix_spurious`` – when True (default), handles the Windows 11
24H2 staged-package bug: if after a successful cleanup
``reclaimable_packages == 2`` (the spurious fingerprint), Cortex will
offer to run ``Remove-Package`` for ``Package_for_RollupFix`` and then
re-run ``StartComponentCleanup`` to reclaim the ~1.2GB. This mirrors the
manual 3-step fix from Microsoft Q&A / Azimstech and is only triggered
on that exact condition, never blindly.
- **`run_servicing_task(self, timeout)`** (Line 574): Trigger Windows' own scheduled StartComponentCleanup task.

Windows ships this task and runs it on idle. Triggering it is gentler
than a manual DISM cleanup (it self-limits to one hour and skips
components newer than 30 days), which makes it the safer default.
- **`_run_dism(self, args, timeout, cancel_event)`** (Line 601): _run_dism.
- **`_decode(raw)`** (Line 624): Decode DISM output, which is UTF-16LE with NULs on many consoles.
- **`_dir_size(path)`** (Line 638): Sum a directory tree, skipping what we cannot read (never raises).
- **`_age_days(path)`** (Line 659): _age_days.

### Module: `src/cortex_unified/system_tools/component_store_cleaner.py`
*Component Store / WinSxS Cleaner — DISM-based analysis and cleanup.

Research grounding
------------------
* Microsoft Learn: "Clean Up the WinSxS Folder" / "Determine the Actual Size
  of the WinSxS Folder" — official DISM commands for component store
  maintenance.
* AzimsTech (2025) — Windows 11 24H2 bug where two packages (26100.1742)
  remain "Staged" after `/StartComponentCleanup`; fix requires targeted
  `/Remove-Package` followed by cleanup.
* Ed Tittel (2025) — "Spurious reclaimables" persist after cleanup; removing
  the deeply superseded top-level package (`Package_for_RollupFix~...`)
  eliminates them.
* RobzTech (2025) — Complete DISM cleanup guide: `/AnalyzeComponentStore`,
  `/StartComponentCleanup`, `/StartComponentCleanup /ResetBase`,
  `/SPSuperseded`; `ResetBase` trade-off (no rollback); PowerShell module;
  Intune Remediations for fleet automation.
* Microsoft Learn: "Reduce the Size of the Component Store in an Offline
  Windows Image" — offline WIM/VHD/VHDX support for golden images.

Why this matters for Cortex Cleaner
-----------------------------------
* WinSxS routinely grows to 15–25 GB after a year of updates. Explorer
  reports a smaller size due to hard links; actual reclaimable space is
  only visible via `DISM /AnalyzeComponentStore`.
* Standard cleanup (`/StartComponentCleanup`) respects 30-day retention.
  `/ResetBase` maximizes reclaim but prevents update rollback — safe for
  stable images / VDI / Autopilot pre-handoff.
* 24H2 "checkpoint cumulative updates" leave packages in "Staged" state
  that standard cleanup ignores; targeted removal is required.

Design
------
* **Read-first**: `analyze()` runs `DISM /AnalyzeComponentStore`, parses
  output into structured `ComponentStoreInfo` (actual size, shared,
  backups, cache, reclaimable packages, cleanup recommended).
* **Cleanup actions**: `cleanup(reset_base=False, sp_superseded=False)`
  runs appropriate DISM command; returns `CleanupResult` with before/after
  sizes and reclaimed bytes.
* **Targeted fix**: `fix_staged_packages()` identifies stuck "Staged"
  packages via `dism /get-packages`, removes the known problematic
  `Package_for_RollupFix~...` if present, then runs cleanup.
* **Offline support**: `analyze_offline(wim_path, index)` and
  `cleanup_offline(wim_path, index)` for golden image maintenance.
* **Safety**: All mutating operations create System Restore point first
  (via `RestorePointManager`). `/ResetBase` requires explicit confirmation.
* **Automation**: `schedule_cleanup(task_name, frequency)` registers
  Proactive Remediation for Intune / Task Scheduler.

Usage::

    from cortex_unified.system_tools.component_store_cleaner import (
        ComponentStoreCleaner, ComponentStoreInfo,
    )
    cleaner = ComponentStoreCleaner()
    info = cleaner.analyze()
    if info.cleanup_recommended:
        result = cleaner.cleanup()
        print(f"Reclaimed {result.reclaimed_bytes:,} bytes")
    # For 24H2 staged packages:
    cleaner.fix_staged_packages()

References
----------
* Microsoft Learn: Clean Up the WinSxS Folder
* Microsoft Learn: Determine the Actual Size of the WinSxS Folder
* Microsoft Learn: Reduce the Size of the Component Store in an Offline Windows Image
* DISM Operating System Package Servicing Command-Line Options
* USENIX ATC 2016 FastCDC (chunking context for delta compression)*

#### Class `ComponentStoreInfo`
Parsed output of `DISM /AnalyzeComponentStore`.

- **`reclaimable_gb(self)`** (Line 106): Reclaimable gb.

Returns:
    Result of the operation.

#### Class `CleanupResult`
Cleanup Result data container.


#### Class `PackageInfo`
Single package from `dism /get-packages`.


#### Class `ComponentStoreCleaner`
DISM-based Component Store analyzer and cleaner.

- **`__init__(self, dism_path, create_restore_point, progress_callback, cancel_event)`** (Line 142): Initialize Component Store Cleaner.

Args:
    dism_path: dism path.
    create_restore_point: create restore point.
    progress_callback: progress callback.
    cancel_event: cancel event.
- **`_run_dism(self, args, timeout)`** (Line 164): Run DISM command, return (returncode, stdout, stderr).
- **`_parse_analyze(self, output)`** (Line 181): Parse `DISM /AnalyzeComponentStore` output.
- **`_parse_packages(self, output)`** (Line 227): Parse `dism /get-packages` table output.
- **`analyze(self)`** (Line 250): Run `DISM /Online /Cleanup-Image /AnalyzeComponentStore`.
- **`cleanup(self, reset_base, sp_superseded)`** (Line 260): Run component store cleanup.

Args:
    reset_base: Use `/ResetBase` — removes ALL superseded components
        (including those within 30-day window), prevents rollback.
    sp_superseded: Use `/SPSuperseded` — removes service pack backup
        components (legacy, rarely needed on Win10/11).
- **`fix_staged_packages(self)`** (Line 305): Fix Windows 11 24H2 stuck 'Staged' packages (26100.1742).

Identifies the problematic `Package_for_RollupFix~31bf3856ad364e35~amd64~~26100.1742.1.10`
package, removes it via `/Remove-Package`, then runs standard cleanup.
- **`analyze_offline(self, wim_path, index)`** (Line 349): Analyze component store in offline WIM/VHD/VHDX.
- **`cleanup_offline(self, wim_path, index, reset_base)`** (Line 359): Cleanup component store in offline image.
- **`schedule_cleanup(self, task_name, frequency_days, reset_base)`** (Line 388): Register a scheduled task for automatic cleanup (admin required).

### Module: `src/cortex_unified/system_tools/context_menu_manager.py`
*Cortex Cleaner — Windows Context Menu & Shell Extension Manager.

Inspects and manages right-click context menu bloat:
1. Enumerates all shell extensions registered in HKCR\*\shell, Directory\shell, etc.
2. Detects orphaned context menu entries (pointing to uninstalled programs).
3. Provides non-destructive disable/enable toggle for individual menu items.
4. Flags orphaned entries and LegacyDisable state for review.*

#### Class `ContextMenuItem`
Context Menu Item data container.


#### Class `ContextMenuReport`
Context Menu Report data container.


#### Class `ContextMenuManager`
Production Windows shell context menu inspector and cleaner.

- **`_extract_command(cls, key_path)`** (Line 59): Read the command value from a shell key.
- **`_check_program_exists(cls, command)`** (Line 72): Check if the executable referenced in the command actually exists.
- **`enumerate_context_menu(cls)`** (Line 91): Enumerate all right-click context menu entries from the registry.
- **`analyze(cls)`** (Line 156): Generate analysis report of context menu entries.
- **`disable_entry(cls, registry_path)`** (Line 167): Disable a context menu entry by setting LegacyDisable.
- **`enable_entry(cls, registry_path)`** (Line 182): Re-enable a disabled context menu entry.

### Module: `src/cortex_unified/system_tools/crash_dump_cleaner.py`
*Cortex Cleaner — Windows Crash Dump & Error Reporting (WER) Cleaner.

Discovers and safely sanitizes Windows Kernel Memory Dumps (MEMORY.DMP), Minidumps,
LiveKernelReports, User-Mode Crash Dumps (%LocalAppData%\CrashDumps), and WER report queues.*

#### Class `CrashDumpItem`
Crash Dump Item data container.


#### Class `CrashDumpCleanReport`
Crash Dump Clean Report data container.


#### Class `CrashDumpCleaner`
Production Windows crash dump and WER queue sanitizer.

- **`scan_dumps(cls)`** (Line 48): Scan all known Windows crash dump and error reporting locations.
- **`clean_dumps(cls, items_to_delete)`** (Line 120): Purge selected or all discovered crash dumps and WER files.

### Module: `src/cortex_unified/system_tools/defender.py`
*Windows Security (Defender) status + quick scan trigger.

Surfaces the protection state most users never check - is real-time protection
on, when did it last scan, are signatures current - and lets them kick off a
quick scan. It reads ``Get-MpComputerStatus`` / ``Get-MpThreatDetection`` and
starts scans with ``Start-MpScan`` (the official Defender PowerShell module).
Read-only status; scanning is an explicit, harmless action the user triggers.*

#### Class `DefenderStatus`
Defender Status data container.

- **`healthy(self)`** (Line 40): Healthy.
- **`to_dict(self)`** (Line 45): To dict.

#### Class `WindowsDefender`
Read Defender status, list recent detections, start a quick scan.

- **`is_supported()`** (Line 65): Is supported.
- **`status(self)`** (Line 69): Status.
- **`_parse_status(out)`** (Line 83): _parse_status.
- **`recent_threats(self, limit)`** (Line 117): Recent threats.
- **`_parse_threats(out)`** (Line 132): _parse_threats.
- **`start_quick_scan(self)`** (Line 154): Kick off a Defender quick scan (harmless; scans, doesn't delete data).
- **`_clean_date(raw)`** (Line 165): _clean_date.
- **`_run(self, script, timeout, want_returncode)`** (Line 181): _run.

### Module: `src/cortex_unified/system_tools/delivery_optimization_cleaner.py`
*Cortex Cleaner — Windows Delivery Optimization (WUDO) Cache Cleaner.

Scans and purges Windows Delivery Optimization peer cache and staging files
in %WinDir%\SoftwareDistribution\DeliveryOptimization and ProgramData cache locations.*

#### Class `DeliveryOptimizationStatus`
Delivery Optimization Status data container.


#### Class `DeliveryOptimizationCleanReport`
Delivery Optimization Clean Report data container.


#### Class `DeliveryOptimizationCleaner`
Production Delivery Optimization cache sanitizer.

- **`get_status(cls)`** (Line 45): Query total cache size and file count in Delivery Optimization stores.
- **`clean_cache(cls)`** (Line 81): Purge all Delivery Optimization cache files.

### Module: `src/cortex_unified/system_tools/dev_cleaner.py`
*Cortex Cleaner — Developer Ecosystem & Build Artifacts Purger.

Scans and purges:
1. Docker: Buildx cache, dangling images, stopped containers, and unused volumes.
2. Python: pip cache, poetry cache, __pycache__, and .pytest_cache.
3. Node.js: npm cache, yarn cache, pnpm store, .next/cache, and .turbo cache.
4. Rust / Cargo: Cargo registry cache and git database.
5. Java / Kotlin: Gradle cache and Maven local repository.
6. Go: Go build cache and module cache.
7. .NET: NuGet global packages and v3 cache.*

#### Class `DevCacheItem`
Dev Cache Item data container.


#### Class `DevCleanResult`
Dev Clean Result data container.


#### Class `DevCleaner`
Production Developer Ecosystem build artifact and cache purge engine.

- **`_dir_metrics(cls, dir_path)`** (Line 54): Compute directory size and file count.
- **`scan_dev_caches(cls)`** (Line 74): Scan system for all developer ecosystem build caches and artifacts.
- **`clean_items(cls, items)`** (Line 172): Purge selected developer cache locations.

### Module: `src/cortex_unified/system_tools/dev_drive_optimizer.py`
*Cortex Cleaner — ReFS Dev Drive & Block-Cloning Optimizer.

Provides inspection and optimization for modern Windows 11 ReFS Dev Drives:
- Identifies Resilient File System (ReFS) and Dev Drive formatting across all volumes.
- Checks support for instant Copy-on-Write (CoW) block cloning (FSCTL_DUPLICATE_EXTENTS_TO_FILE).
- Audits Microsoft Defender Performance Mode (asynchronous scan filters).
- Inspects attached file system filter drivers to maximize developer compilation throughput.*

#### Class `DevDriveInfo`
Dev Drive Info data container.


#### Class `DevDriveAuditReport`
Dev Drive Audit Report data container.


#### Class `DevDriveOptimizer`
Enterprise ReFS Dev Drive & Block Cloning Optimizer.

- **`__init__(self)`** (Line 53): Initialize Dev Drive Optimizer.
- **`audit(self)`** (Line 57): Audit all mounted volumes for ReFS, Dev Drive status, and Block Cloning.
- **`_get_logical_drives(self)`** (Line 89): Get all valid local drive letters.
- **`_inspect_drive(self, drive_letter)`** (Line 98): Inspect a single drive for ReFS, Dev Drive, and Block Cloning.
- **`test_block_cloning(self, source_path, target_path)`** (Line 173): Test instant CoW block cloning between two paths via FSCTL_DUPLICATE_EXTENTS_TO_FILE.

### Module: `src/cortex_unified/system_tools/dev_package_cache_cleaner.py`
*Developer Package Caches (Winget, Cargo, Vcpkg, NuGet, Pip) Deep Cleaner.

Research Grounding
------------------
* Modern Developer Workstation Storage Overhead:
  Developers working across multiple toolchains accumulate dozens of gigabytes
  of immutable compiled tarballs, crate archives, wheel caches, and installer payloads.
* Targeted Ecosystem Stores:
  1. Windows Package Manager (`winget`): Installer downloads cached in
     `%LOCALAPPDATA%\Packages\Microsoft.DesktopAppInstaller_*\LocalState` and Temp directories.
  2. Rust Cargo: Compressed crate archives in `%USERPROFILE%\.cargo\registry\cache`
     and git repository checkouts in `%USERPROFILE%\.cargo\git\checkouts`.
  3. Microsoft C++ `vcpkg`: Pre-built binary archives in `%LOCALAPPDATA%\vcpkg\archives`.
  4. .NET NuGet: HTTP package download caches in `%LOCALAPPDATA%\NuGet\v3-cache`.
  5. Python Pip: Wheel and source download caches in `%LOCALAPPDATA%\pip\cache`.
  6. Node Yarn/Pnpm: Global content-addressable package tarballs.

This module dynamically inspects and cleans these developer package stores without
damaging installed toolchains, build environments, or active source trees.*

#### Class `DevPackageStoreInfo`
Status and storage consumption of a specific developer package cache.

- **`to_dict(self)`** (Line 46): To dict.

#### Class `DevPackageReport`
Consolidated storage consumption across all developer package ecosystems.

- **`to_dict(self)`** (Line 67): To dict.

#### Class `DevPackageCleanResult`
Outcome of a developer package cache purge.

- **`to_dict(self)`** (Line 86): To dict.

#### Class `DevPackageCacheCleaner`
Production developer environment cache detection and cleanup engine.

- **`__init__(self)`** (Line 100): Initialize Dev Package Cache Cleaner.
- **`get_candidate_stores(self)`** (Line 104): Resolve candidate developer cache roots dynamically from active user profiles.
- **`scan(self)`** (Line 168): Analyze developer package stores and measure disk space consumption.
- **`clean(self, selected_ecosystems, dry_run)`** (Line 204): Purge developer package cache archives.

### Module: `src/cortex_unified/system_tools/device_fingerprint.py`
*Pure, conservative device fingerprinting from observed LAN evidence.*

#### Class `FingerprintEvidence`
Fingerprint Evidence data container.

- **`to_dict(self)`** (Line 21): To dict.

#### Class `DeviceFingerprint`
Device Fingerprint data container.

- **`to_dict(self)`** (Line 43): To dict.

### Module: `src/cortex_unified/system_tools/diagnostic_data_manager.py`
*Cortex Cleaner — Windows Telemetry & Diagnostic Data Manager.

Audits and configures Windows diagnostic telemetry levels:
1. Controls AllowTelemetry level (0=Security, 1=Required/Basic, 2=Enhanced, 3=Optional/Full).
2. Manages Customer Experience Improvement Program (CEIP) tracking.
3. Manages Application Impact Telemetry (AIT) and Windows Error Reporting auto-submission.
4. Manages Windows Advertising ID and Timeline Activity Feed publication.
5. Computes a privacy telemetry exposure score and provides 1-click maximum privacy enforcement.*

#### Class `TelemetrySetting`
Telemetry Setting data container.


#### Class `TelemetryAuditReport`
Telemetry Audit Report data container.


#### Class `DiagnosticDataManager`
Production Windows Telemetry & Diagnostic Data level management engine.

- **`_read_dword(cls, hive, subkey, name)`** (Line 132): _read_dword.
- **`_write_dword(cls, hive, subkey, name, value)`** (Line 146): _write_dword.
- **`audit_telemetry(cls)`** (Line 162): Inspect all diagnostic telemetry settings and calculate score.
- **`apply_maximum_privacy(cls)`** (Line 199): Harden all telemetry settings to maximum privacy values.

### Module: `src/cortex_unified/system_tools/directstorage_optimizer.py`
*Windows 11 DirectStorage & BypassIO Hardware Acceleration Auditor.

Audits per-volume BypassIO capability (FSCTL_MANAGE_BYPASS_IO) introduced in Windows 11
for DirectStorage v1.2+ GPU decompression pipelines. Identifies incompatible storage stacks,
legacy file system minifilters, or third-party filter drivers blocking direct NVMe transfers.*

#### Class `BypassIoVolumeReport`
BypassIO and DirectStorage status for a single storage volume.

- **`to_dict(self)`** (Line 34): To dict.

#### Class `DirectStorageAuditReport`
Comprehensive system-wide DirectStorage readiness report.

- **`to_dict(self)`** (Line 56): To dict.

#### Class `DirectStorageOptimizer`
Audits and provides diagnostics for Windows DirectStorage and BypassIO.

- **`__init__(self)`** (Line 70): Initialize Direct Storage Optimizer.
- **`parse_bypassio_output(cls, volume, text)`** (Line 75): Parse the standard stdout of 'fsutil bypassio state <volume> /v'.
- **`_get_active_drives(self)`** (Line 114): Detect all mounted active drive letters on Windows.
- **`audit(self)`** (Line 130): Audit all mounted volumes for DirectStorage BypassIO readiness.

### Module: `src/cortex_unified/system_tools/disk_benchmark.py`
*Cortex Cleaner — Storage Performance & IOPS Disk Benchmark.

Performs non-destructive storage benchmarks measuring:
1. Sequential Read (1MB block size)
2. Sequential Write (1MB block size)
3. Random 4KB Read (IOPS & Access Latency)
4. Random 4KB Write (IOPS & Access Latency)*

#### Class `DiskBenchmarkMetric`
Disk Benchmark Metric data container.


#### Class `DiskBenchmarkReport`
Disk Benchmark Report data container.


#### Class `DiskBenchmarkEngine`
Production non-destructive disk throughput and IOPS storage benchmark.

- **`run_benchmark(cls, target_directory, file_size_mb, progress_cb, cancel_check)`** (Line 49): Execute full benchmark suite on the specified storage location.

### Module: `src/cortex_unified/system_tools/disk_health.py`
*Disk health (S.M.A.R.T.) reporting - read-only, honest.

Reads each physical disk's health/operational status (and, where the driver
exposes it, wear %, temperature and read errors) via Windows'
``Get-PhysicalDisk`` / ``Get-StorageReliabilityCounter``. Purely informational;
it never modifies anything. Values that a drive doesn't report are left as
``None`` rather than guessed.*

#### Class `DiskHealth`
Disk Health data container.

- **`is_healthy(self)`** (Line 40): Is healthy.
- **`to_dict(self)`** (Line 44): To dict.

#### Class `DiskHealthMonitor`
Reads S.M.A.R.T. / physical-disk health information.

- **`is_supported()`** (Line 63): Is supported.
- **`get_health(self)`** (Line 67): Get health.
- **`_parse(out)`** (Line 92): _parse.
- **`_run(self, script)`** (Line 129): _run.

### Module: `src/cortex_unified/system_tools/dns_benchmark.py`
*Cortex Cleaner — Multi-Threaded DNS Latency Benchmark & Optimizer.

Benchmarks query round-trip latency across top global, privacy, and secure DNS providers
using raw DNS socket queries (A-record resolution) and enables 1-click optimal adapter configuration.*

#### Class `DnsServerSpec`
Dns Server Spec data container.


#### Class `DnsBenchmarkResult`
Dns Benchmark Result data container.


#### Class `DnsBenchmarkEngine`
Production DNS query benchmarking and network configuration engine.

- **`_build_dns_query(domain)`** (Line 63): Construct raw DNS wire format query for an A record.
- **`_query_dns(cls, server_ip, domain, timeout_seconds)`** (Line 83): Send a direct UDP DNS query and measure round-trip latency in milliseconds.
- **`benchmark_server(cls, server, domains, timeout_seconds)`** (Line 101): Benchmark a DNS provider across multiple test domains.
- **`run_full_benchmark(cls, servers, progress_cb, cancel_check)`** (Line 145): Concurrently benchmark all known DNS providers.
- **`apply_dns_servers(cls, interface_name, primary_ip, secondary_ip)`** (Line 180): Configure DNS servers on the specified network adapter via netsh.

### Module: `src/cortex_unified/system_tools/drive_optimizer.py`
*Media-aware drive optimization - the honest way.

The #1 correctness rule (well-established): **never defragment an SSD.** On SSD/
NVMe the right maintenance is TRIM (``Optimize-Volume -ReTrim``); on rotational
HDDs it's defragmentation (``Optimize-Volume -Defrag``). Windows' own Optimize
Drives does the right thing per medium; many third-party "defraggers" get this
dangerously wrong. We detect the medium first (reusing the engine's StorageProbe)
and pick the correct operation - or refuse and explain.

All operations are read-first (analyze) and only act when explicitly asked.
Windows-only; time-boxed, window-hidden subprocess calls.*

#### Class `OptimizeOp`
Optimize Op enumeration.


#### Class `DriveInfo`
Drive Info data container.

- **`to_dict(self)`** (Line 48): To dict.

#### Class `OptimizeResult`
Optimize Result data container.


#### Class `DriveOptimizer`
List fixed drives, recommend the correct op per medium, and run it safely.

- **`__init__(self)`** (Line 70): Initialize Drive Optimizer.
- **`is_supported()`** (Line 75): Is supported.
- **`list_drives(self)`** (Line 79): Return fixed drives with the medium-correct recommended operation.
- **`_recommend(kind)`** (Line 91): _recommend.
- **`optimize(self, letter, op, cancel_event)`** (Line 103): Run the correct optimization for *letter*. If *op* is None, auto-pick.

Refuses to defrag SSD/NVMe even if explicitly asked (safety).
- **`_fixed_drive_letters(self)`** (Line 146): Return fixed (non-removable, non-network) drive letters.
- **`_run_ps(self, script, timeout, cancel_event)`** (Line 161): _run_ps.

### Module: `src/cortex_unified/system_tools/driver_inventory.py`
*Driver inventory - READ-ONLY listing of installed device drivers.

Research is clear that automatic "driver updater" tools are a common vector for
scareware and bundled junk, and that pushing generic drivers can destabilize a
system. So Cortex intentionally does NOT download or install drivers. Instead
it gives you an honest, read-only inventory (device name, provider, version,
date) via ``Get-CimInstance Win32_PnPSignedDriver`` so you can check versions
yourself against the manufacturer's site. Nothing here modifies the system.*

#### Class `DriverInfo`
Driver Info data container.

- **`to_dict(self)`** (Line 36): To dict.

#### Class `DriverInventory`
Read-only inventory of signed device drivers (Windows).

- **`is_supported()`** (Line 51): Is supported.
- **`list_drivers(self)`** (Line 55): List drivers.
- **`_parse(out)`** (Line 68): _parse.
- **`_clean_date(raw)`** (Line 105): _clean_date.
- **`_run(self, script)`** (Line 124): _run.

### Module: `src/cortex_unified/system_tools/driver_manager.py`
*Driver Cleaner & Updater — offline-capable, WHQL-verified, restore points.

Research grounding
------------------
* Snappy Driver Installer Origin (SDIO) — portable, offline driver packs,
  state-of-the-art matching algorithm, no ads, GPLv3, supports XP–11.
  Can download driverpacks for offline use on air-gapped machines.
* Driver Booster 13 (IObit) — 18M+ driver database, 1200+ brands,
  WHQL + IObit security scan, Game Boost mode, Hot Fix tools
  (Fix No Sound, Fix Network Failure, Fix Bad Resolution), auto
  restore points, offline updater, ARM64 support.
* Windows built-in: `pnputil.exe` for driver store management,
  `devcon.exe` for device enumeration, `DISM /Add-Driver` for
  offline image servicing.

Why this matters for Cortex Cleaner
-----------------------------------
* Corrupt/outdated drivers cause BSODs, audio loss, network drops,
  GPU crashes, display flicker. Windows Update often lags OEM drivers.
* Technicians need offline capability (clean install, air-gapped).
* Safety: automatic restore points, WHQL verification, rollback.

Design
------
* **Detection**: `devcon` / WMI `Win32_PnPSignedDriver` / `Get-PnpDevice`
  to enumerate devices, current driver version/date, hardware IDs.
* **Matching**: Windows Update Agent COM search (``Type='Driver'``) against
  the machine's real hardware IDs, with offline fallback to a local
  driverpack index (SDIO-compatible).
* **Download**: Multi-threaded with resume, SHA256 verification,
  WHQL signature check via `signtool verify /pa`.
* **Install**: `pnputil /add-driver /install` with `/reboot` suppression;
  force-install for broken packages; creates restore point before each.
* **Cleanup**: `pnputil /delete-driver` for orphaned/duplicate drivers
  in Driver Store; size reporting; dry-run mode.
* **Offline mode**: Export driverpack index JSON; download selected
  packs to USB; install on target via `pnputil` without internet.

Usage::

    from cortex_unified.system_tools.driver_manager import DriverManager
    mgr = DriverManager()
    outdated = mgr.scan()
    for drv in outdated:
        print(f"{drv.device}: {drv.current_version} -> {drv.latest_version}")
    mgr.update_selected([d.hardware_id for d in outdated])

References
----------
* Snappy Driver Installer Origin (github.com/snappy-driver-installer/snappy-driver-installer)
* Driver Booster 13 technical specs (iobit.com)
* Microsoft pnputil documentation
* Windows Update Catalog API*

#### Class `DriverInfo`
Single device driver information.

- **`to_dict(self)`** (Line 98): To dict.

#### Class `DriverPack`
Driver pack metadata (SDIO-compatible).


#### Class `ScanResult`
Scan Result data container.

- **`to_json(self)`** (Line 127): To json.

#### Class `DriverManager`
Detect, update, and clean device drivers.

- **`__init__(self, create_restore_point, progress_callback, cancel_event, offline_mode, driverpack_index)`** (Line 145): Initialize Driver Manager.
- **`_run(self, cmd, timeout)`** (Line 166): _run.
- **`_run_ps(self, script, timeout)`** (Line 183): _run_ps.
- **`_load_index(self, path)`** (Line 189): _load_index.
- **`_save_index(self, path)`** (Line 204): _save_index.
- **`_pack_to_dict(self, pack)`** (Line 215): _pack_to_dict.
- **`_enumerate_pnp(self)`** (Line 224): Use WMI/PowerShell to get all PnP devices with driver info.
- **`_check_updates_online(self, drivers)`** (Line 311): Search Windows Update for driver updates for this machine's hardware.

Uses the Windows Update Agent COM API (``Microsoft.Update.Session``)
with ``DriverUpdates`` criteria — the same source Windows itself and
SDIO's "from Windows Update" mode use. Matching is by the driver's
hardware ID as reported by WUA, never by guessing vendors.

Requires an active connection and, for install rights, elevation.
When WUA is unavailable (service disabled, offline host) the input is
returned unchanged and the reason is reported via progress.
- **`_wua_driver_updates(self)`** (Line 411): Driver updates WUA currently offers, or None when unavailable.

``ServerSelection`` 2 (``ssWindowsUpdate``) mirrors what a user sees
in Settings; ``IsInstalled=0`` restricts to pending offers, so an
already-installed driver never shows as an update.
- **`_check_updates_offline(self, drivers)`** (Line 435): Match against local driverpack index.
- **`_version_newer(self, v1, v2)`** (Line 459): Compare version strings (handles multi-part versions).
- **`scan(self)`** (Line 472): Scan all devices and check for outdated/missing drivers.
- **`update_selected(self, hardware_ids, force)`** (Line 496): Install driver updates for specified hardware IDs.
- **`_download_and_install(self, drv, force)`** (Line 529): Download driver package and install via pnputil.
- **`_install_from_store(self, inf_name, force)`** (Line 549): Install driver already in driver store.
- **`cleanup_driver_store(self, dry_run)`** (Line 557): Remove orphaned/duplicate drivers from Driver Store.

Returns (removed_count, freed_mb).
- **`export_driverpack_index(self, path)`** (Line 610): Export current index to JSON for offline use.
- **`get_stats(self)`** (Line 615): Get stats.

### Module: `src/cortex_unified/system_tools/driver_store_cleaner.py`
*Cortex Cleaner — Driver Store Explorer & Superseded Driver Purger.

Inspects and manages the Windows Driver Store repository (%WinDir%\System32\DriverStore):
1. Enumerates all third-party INF driver packages (oem*.inf) via pnputil.exe.
2. Identifies duplicate, superseded, and obsolete driver versions for the same hardware.
3. Provides selective and batch driver deletion (pnputil /delete-driver oemXX.inf /force).
4. Exports driver packages to backup archive directory (pnputil /export-driver * <folder>).*

#### Class `DriverPackage`
Driver Package data container.


#### Class `DriverCleanResult`
Driver Clean Result data container.


#### Class `DriverStoreCleaner`
Production Driver Store Explorer (RAPR) and superseded INF driver purger.

- **`enumerate_drivers(cls)`** (Line 54): Query and parse all third-party driver packages via pnputil /enum-drivers.
- **`delete_driver(cls, published_name, force)`** (Line 116): Delete a single third-party driver package from the Windows Driver Store.
- **`export_all_drivers(cls, backup_dir)`** (Line 138): Export and backup all installed third-party drivers to directory.

### Module: `src/cortex_unified/system_tools/env_variable_manager.py`
*Cortex Cleaner — Windows Environment Variable & PATH Optimizer.

Inspects and sanitizes Windows environment variables:
1. Detects duplicate PATH entries (case-insensitive deduplication).
2. Identifies dead links — directory entries that no longer exist on disk.
3. Provides non-destructive toggling (disable without deleting) with snapshot rollback.
4. Separates User vs System variable scopes for safe editing.
5. Exports and imports environment configurations as .env or .bat files.*

#### Class `PathEntry`
Path Entry data container.


#### Class `EnvVariable`
Env Variable data container.


#### Class `PathAnalysisReport`
Path Analysis Report data container.


#### Class `CleanupResult`
Cleanup Result data container.


#### Class `EnvironmentVariableManager`
Production Windows environment variable and PATH optimizer.

- **`_read_registry_value(cls, hive, subkey, name)`** (Line 72): Read a single registry value and its type.
- **`_write_registry_value(cls, hive, subkey, name, value, reg_type)`** (Line 84): Write a registry value.
- **`enumerate_variables(cls, scope)`** (Line 96): List all environment variables for the specified scope.
- **`analyze_path(cls)`** (Line 123): Analyze both User and System PATH for dead links, duplicates, and empty entries.
- **`clean_path(cls, scope, remove_dead, remove_duplicates, remove_empty)`** (Line 176): Clean PATH variable by removing dead links, duplicates, and empty entries.
- **`export_env_to_file(cls, output_path, scope, fmt)`** (Line 238): Export environment variables to .env or .bat file.

### Module: `src/cortex_unified/system_tools/event_log_cleaner.py`
*Cortex Cleaner — Enterprise Windows Event Log Sweeper.

Enumerates Windows Event Log channels (Application, System, Security, PowerShell, Diagnostics),
inspects record counts and on-disk sizes (%WinDir%\System32\Winevt\Logs),
and provides selective/batch clearing with automated EVTX backup archiving.*

#### Class `EventLogChannel`
Event Log Channel data container.


#### Class `EventLogCleanResult`
Event Log Clean Result data container.


#### Class `EventLogCleaner`
Production Windows Event Log manager and sweeper.

- **`list_all_logs(cls, progress_cb)`** (Line 63): Enumerate all available Windows event log channels and their metrics.
- **`clear_log(cls, channel_name, backup_directory)`** (Line 105): Clear a specific Windows event log with optional backup export.
- **`clear_all_logs(cls, backup_directory, progress_cb)`** (Line 148): Clean all active Windows event log channels.

### Module: `src/cortex_unified/system_tools/event_log_monitor.py`
*Cortex Cleaner — Windows Event Log Anomaly & Hardware Error Monitor.

Queries Windows Event Log channels for critical system faults and hardware warnings:
1. Disk & NTFS Errors (Event IDs 7, 11, 55 — bad blocks, controller errors, MFT corruption).
2. Kernel Crashes & BugChecks (Event ID 1001 — BlueScreen of Death events).
3. Sudden Power Loss & Dirty Shutdowns (Event ID 6008, Event ID 41 Kernel-Power).
4. Application Crash Events (Event ID 1000 — faulty modules and exception codes).
5. Security Audit Failures (Event ID 4625 — failed authentication attempts).*

#### Class `LogAnomalyEvent`
Log Anomaly Event data container.


#### Class `AnomalyScanReport`
Anomaly Scan Report data container.


#### Class `EventLogMonitor`
Production Windows Event Log hardware and crash anomaly detector.

- **`query_anomalies(cls, max_events_per_category)`** (Line 57): Query Event Log channels for recent critical errors and hardware warnings.

### Module: `src/cortex_unified/system_tools/external_exposure.py`
*Explicit, read-only exposure lookup for a router-reported public IPv4.*

#### Class `ExposureLookupError`
Raised for invalid consent, target, credentials, or provider output.


#### Class `ExternalService`
External Service data container.

- **`to_dict(self)`** (Line 32): To dict.

#### Class `ExposureResult`
Exposure Result data container.

- **`to_dict(self)`** (Line 49): To dict.

#### Class `ExternalExposureClient`
Opt-in Shodan/Censys host lookup with an injectable transport.

- **`__init__(self, provider, api_key, api_secret, transport)`** (Line 108): Initialize External Exposure Client.
- **`lookup(self, public_ip)`** (Line 124): Lookup.
- **`_parse_shodan(payload)`** (Line 154): _parse_shodan.
- **`_parse_censys(payload)`** (Line 180): _parse_censys.

### Module: `src/cortex_unified/system_tools/firewall_manager.py`
*Windows Firewall control - block/allow programs and remote addresses.

This drives Windows Defender Firewall via the ``NetSecurity`` PowerShell module
(``New-NetFirewallRule`` etc.), which is the supported, fully-reversible way to
add rules without a kernel driver. Real per-packet filtering (like simplewall or
GlassWire) needs a signed WFP driver, which is out of scope for a lightweight
app; firewall rules achieve the user-facing goal - stop or allow a program's
traffic - safely and undoably.

Safety design:
* Every rule we create is prefixed ``Cortex Cleaner:`` so we can list and manage
  *only our own* rules and never touch built-in Windows or third-party rules.
* Creating/removing rules needs Administrator; we surface that honestly.
* Listing existing rules is read-only.*

#### Class `FirewallRule`
Firewall Rule data container.

- **`to_dict(self)`** (Line 47): To dict.

#### Class `FirewallManager`
Create, list, toggle and remove Windows Firewall rules (Cortex-scoped).

- **`is_supported()`** (Line 66): Is supported.
- **`block_program(self, program_path, direction, label)`** (Line 72): Block a program's traffic. Reversible via remove_rule/toggle.
- **`allow_program(self, program_path, direction, label)`** (Line 78): Allow program.
- **`block_remote_address(self, address, direction, label)`** (Line 84): Block traffic to/from a remote IP or range.
- **`_new_rule(self, action, direction, label, program, remote_address)`** (Line 92): _new_rule.
- **`list_rules(self, cortex_only)`** (Line 120): List rules.
- **`set_enabled(self, name, enabled)`** (Line 142): Set enabled.
- **`remove_rule(self, name)`** (Line 150): Remove rule.
- **`_parse_rules(out)`** (Line 160): _parse_rules.
- **`_valid_address(addr)`** (Line 192): _valid_address.
- **`_ps_quote(value)`** (Line 214): Single-quote a value for PowerShell, escaping embedded quotes.
- **`_run(self, script, want_output)`** (Line 218): _run.

### Module: `src/cortex_unified/system_tools/font_cache_manager.py`
*Cortex Cleaner — Windows Font Cache Inspector & Optimizer.

Manages installed system and user fonts:
1. Enumerates all installed fonts with file size, format (TTF/OTF/WOFF/TTC), and installation type.
2. Detects orphaned font files (registry entries pointing to missing font files).
3. Detects duplicate fonts (same font family installed in multiple locations).
4. Calculates total font cache footprint and identifies fonts consuming the most space.
5. Provides cleanup of orphaned font registry entries.*

#### Class `FontEntry`
Font Entry data container.


#### Class `FontAnalysisReport`
Font Analysis Report data container.


#### Class `FontCleanResult`
Font Clean Result data container.


#### Class `FontCacheManager`
Production Windows font inventory and orphan cleanup engine.

- **`_get_fonts_dir(cls)`** (Line 64): Return the system fonts directory.
- **`_detect_format(cls, file_name)`** (Line 70): Detect font format from file extension.
- **`enumerate_fonts(cls)`** (Line 81): Enumerate all registered system fonts from the registry.
- **`analyze(cls)`** (Line 135): Produce full analysis report of installed font set.
- **`clean_orphaned_entries(cls)`** (Line 157): Remove orphaned font registry entries (fonts pointing to missing files).

### Module: `src/cortex_unified/system_tools/free_space_wipe.py`
*Free-space wipe - overwrite the unused space on a volume.

After you delete a file normally, its bytes usually remain on disk until they
happen to be overwritten. Wiping free space overwrites all currently-unused
clusters so previously-deleted files can no longer be recovered by undelete
tools. On Windows this uses the built-in ``cipher /w`` command.

Honesty note: like single-file shredding, this is only a hard guarantee on
spinning HDDs. On SSDs/NVMe, wear-levelling and over-provisioning mean some
old data may physically remain even after a free-space wipe. We surface that
caveat rather than promising more than the medium can deliver.*

#### Class `WipeResult`
Wipe Result data container.


#### Class `FreeSpaceWiper`
Overwrite a volume's free space (Windows ``cipher /w``).

- **`is_supported()`** (Line 44): Is supported.
- **`medium_for(self, drive_letter)`** (Line 48): Return (medium_kind, overwrite_effective) for the drive.
- **`wipe(self, drive_letter, cancel_event)`** (Line 56): Wipe free space on *drive_letter* (e.g. 'C'). Blocking; can be slow.

### Module: `src/cortex_unified/system_tools/game_mode.py`
*Gaming Mode - one-click, fully reversible PC boost for game sessions.

What "boost" honestly means here (no FPS fairy dust):

* **Power plan switch** - move to the machine's best high-performance scheme
  for the session, restore the previous plan on exit.
* **Background quieting** - *suspend* (never kill) known-noise processes such
  as sync clients and updaters so they stop competing for CPU/disk during the
  session, then resume exactly those processes afterwards.

Safety model:

* A fixed protected list keeps every OS-critical process (and Cortex itself)
  untouchable; suspend candidates come from a conservative default allowlist
  plus caller-supplied extras - nothing arbitrary is ever touched.
* ``preview()`` shows exactly what would change before anything happens;
  ``start()`` returns per-item results and ``stop()`` restores state even if
  the session ended abnormally (see :meth:`GameMode.__exit__`).

Requires Premium (``Feature.GAMING_MODE``); callers gate via licensing.*

#### Class `BoostReport`
Outcome of starting or stopping a boosted session.

- **`to_dict(self)`** (Line 77): To dict.

#### Class `GameMode`
Apply and revert a gaming-session performance profile.

- **`__init__(self, extra_suspend, dry_run)`** (Line 95): Initialize Game Mode.
- **`is_supported()`** (Line 112): Boost needs Windows power plans + psutil.
- **`_candidates(self)`** (Line 116): Running processes matching the suspend lists (protected excluded).
- **`preview(self)`** (Line 133): Read-only view of exactly what ``start()`` would change.
- **`start(self)`** (Line 149): Apply the boost profile (idempotent; safe while already active).
- **`stop(self)`** (Line 195): Restore power plan and resume everything this session suspended.
- **`_pick_boost_plan(self, plans)`** (Line 240): Choose the highest-performance scheme available, else None.

### Module: `src/cortex_unified/system_tools/health_check.py`
*One-click PC health check - aggregates the fast, read-only diagnostics.

Runs a handful of cheap, honest checks (free space, memory pressure, drive
S.M.A.R.T. health, boot time, and Windows Security state), each producing a
clear status and, where relevant, a pointer to the page that fixes it. It then
rolls them into an overall score/grade.

Design principles:
* Every check is read-only and quick - no long scans, no system changes.
* A check that can't gather data reports "unknown" (info), never a fake pass.
* The score is a transparent weighted deduction, not a mysterious number.*

#### Class `HealthCheck`
Health Check data container.

- **`to_dict(self)`** (Line 39): To dict.

#### Class `HealthReport`
Health Report data container.

- **`to_dict(self)`** (Line 52): To dict.

#### Class `HealthChecker`
Runs the read-only health checks and scores them.

- **`run(self, progress)`** (Line 64): Run.
- **`_score(checks)`** (Line 90): _score.
- **`_check_disk_space()`** (Line 113): _check_disk_space.
- **`_check_memory()`** (Line 133): _check_memory.
- **`_check_disk_health()`** (Line 150): _check_disk_health.
- **`_check_boot()`** (Line 172): _check_boot.
- **`_check_security()`** (Line 197): _check_security.
- **`_check_updates()`** (Line 220): _check_updates.

### Module: `src/cortex_unified/system_tools/hosts_file_manager.py`
*Cortex Cleaner — Windows Hosts File Editor & Anti-Telemetry DNS Shield.

Inspects and manages the Windows Hosts file (%WinDir%\System32\drivers\etc\hosts):
1. Parses entries with IP mapping, hostname, comments, and enabled/disabled state.
2. Enables, disables, adds, and removes host records with automatic syntax validation.
3. Injects curated Windows Anti-Telemetry & Ad-Tracking blocklist rules.
4. Generates automated timestamped backups before applying modifications.*

#### Class `HostEntry`
Host Entry data container.


#### Class `HostsOperationResult`
Hosts Operation Result data container.


#### Class `HostsFileManager`
Production Windows Hosts file and Anti-Telemetry DNS manager.

- **`get_hosts_path(cls)`** (Line 63): Locate hosts file path across platforms.
- **`parse_hosts_file(cls, hosts_path)`** (Line 71): Parse hosts file into structured entries.
- **`_create_backup(cls, hosts_path)`** (Line 112): Create a timestamped backup before modifying the hosts file.
- **`save_hosts_entries(cls, entries, hosts_path)`** (Line 125): Write modified host entries back to the hosts file.
- **`apply_anti_telemetry_shield(cls, hosts_path)`** (Line 160): Inject anti-telemetry blocklist rules into hosts file.

### Module: `src/cortex_unified/system_tools/junction_auditor.py`
*Cortex Cleaner — NTFS Hard Link, Junction & Reparse Point Auditor.

Deep forensic auditor for NTFS filesystem links:
- Discovers and categorizes Directory Junctions (IO_REPARSE_TAG_MOUNT_POINT) and Symlinks.
- Detects orphaned / dead junction points whose target paths no longer exist on disk.
- Identifies circular symlink traps and infinite recursion loops.
- Tracks multi-hardlinked files (st_nlink > 1) and calculates true cluster deduplication savings.*

#### Class `ReparseItem`
Reparse Item data container.


#### Class `JunctionAuditReport`
Junction Audit Report data container.


#### Class `JunctionAuditor`
Enterprise NTFS Junction Point & Reparse Tag Auditor.

- **`__init__(self)`** (Line 53): Initialize Junction Auditor.
- **`audit(self, root_path, max_depth)`** (Line 57): Audit a folder hierarchy or default system profile for reparse links.
- **`remove_dead_junction(self, link_path)`** (Line 167): Safely unlink a dead junction or symlink without touching target files.

### Module: `src/cortex_unified/system_tools/lan_scanner.py`
*LAN device discovery - see what else is on your local network.

Reads the operating system's ARP cache (``arp -a``) to list the devices your
machine has recently talked to on the local network: their IP, MAC (hardware)
address, and a best-effort vendor guess from the MAC's OUI prefix via the
full IEEE registry (:mod:`cortex_unified.system_tools.oui`). This is read-only and offline - it inspects a cache the OS
already maintains, it does not send probes or scan ports.

Why it's useful: spotting an unfamiliar device on your network (the kind of
"new device joined" alert premium tools charge for) is a simple, honest
security win. We clearly mark entries we can't identify rather than guessing.*

#### Class `LanDevice`
Lan Device data container.

- **`to_dict(self)`** (Line 44): To dict.

#### Class `LanScanner`
Enumerate LAN devices from the OS ARP cache (read-only).

- **`scan(self)`** (Line 52): Scan.
- **`_vendor_for(mac)`** (Line 58): Vendor from the authoritative IEEE registry (empty when unknown).

Previously this used a small hand-written table, which turned out to be
wrong for 13% of its entries - it reported ``d8:eb:97`` as TP-Link when
IEEE assigns it to TRENDnet. Vendor data now comes only from the IEEE
registry via :mod:`cortex_unified.system_tools.oui`.
- **`_parse(cls, out)`** (Line 69): _parse.
- **`_run(self)`** (Line 96): _run.

### Module: `src/cortex_unified/system_tools/leftover_cleaner.py`
*Leftover Cleaner - find and safely remove what an uninstaller leaves behind.

Why this exists
---------------
Most Windows uninstallers only remove the files they wrote at install time.
Folders under ``AppData``, ``ProgramData``, ``Program Files``, orphaned Start
Menu shortcuts and ``SOFTWARE`` registry keys routinely survive, and on C:\
they accumulate to gigabytes over years of installs. This module implements
the detection pipeline used by the reputable open-source uninstallers
(Bulk Crap Uninstaller's published ``JunkManager``/``ConfidenceGenerators``
heuristics, cross-checked against Revo/Geek documented behaviour):

1. **Inventory** every installed app from the four Uninstall registry branches
   (HKLM/HKCU x 64-bit/WOW6432Node) with publisher, InstallLocation and
   installer type (MSI GUID / InnoSetup ``_is1`` / NSIS).
2. **Sweep** the standard leftover locations for folders, registry keys and
   shortcuts whose names match the target app's tokens (bounded edit distance
with a
   hard <=4-char floor and a 1/3-length cut-off - never naive substring).
3. **Score** every finding with signed evidence points (empty folder +4,
   publisher match +4, executables present -4, name claimed by a live app -7,
   ...) and map the raw score to Bad / Questionable / Good / VeryGood.
4. **Gate** results through safety filters: known-folder prohibition, a
   directory-name blacklist (``Microsoft``, ``Common Files``, ``Intel``-style
   shared vendor folders), the Windows System attribute, self-protection, and
   a cross-check against every currently-installed app.
5. **Clean** with three undo layers: Recycle Bin for files (never a silent
   permanent delete), ``reg export`` backups before any registry deletion, and
   an atomic JSON operation journal recording every disposition.

Nothing is deleted by scanning; deletion always happens through
:class:`LeftoverCleaner` with explicit user-reviewed findings.*

#### Class `SafetyPolicy`
Paths the scanner/cleaner must never propose or touch.

- **`build(cls, extra_protected)`** (Line 238): Build a policy protecting known-folder roots plus *extra_protected*.

Protects the directories named by _KNOWN_FOLDER_ENVS (SystemRoot,
Program Files, ProgramData, APPDATA, TEMP, ...), any caller-supplied
extra paths, and this module's own directory (self-protection).
- **`is_prohibited(self, path)`** (Line 258): True when *path* IS a protected root (its children are allowed).

#### Class `InstalledApp`
One entry from an Uninstall registry branch.

- **`to_dict(self)`** (Line 325): Return a plain-dict view of this app entry (for journals/reports).

#### Class `LeftoverFinding`
One reviewed-able leftover candidate with its evidence.

- **`to_dict(self)`** (Line 450): Return a plain-dict view of this finding (for journals/reports).

#### Class `ExclusionsStore`
Persisted list of paths the user chose to keep.

When a leftover review flags something the user recognises as wanted
(a shared vendor folder, a profile they care about), they can exclude it:
the path is stored in ``~/.cortex_cleaner/exclusions.json`` and every
later scan silently drops findings at or beneath it. Writes are atomic;
a corrupt file degrades to an empty list rather than raising.

- **`__init__(self, path)`** (Line 481): Initialize the store, loading from *path* (default
``~/.cortex_cleaner/exclusions.json``).
- **`_load(self)`** (Line 491): Load the JSON exclusion list; unreadable/corrupt file means empty.
- **`save(self)`** (Line 506): Atomically persist the exclusion list (tmp file + replace).

Returns True on success; an OSError is logged and False is returned
rather than raised.
- **`_norm(path)`** (Line 526): Normalize a path (case + separators) for exclusion matching.
- **`add(self, path)`** (Line 533): Exclude *path* (and everything beneath it). Persists immediately.
- **`discard(self, path)`** (Line 541): Remove *path* from the exclusions and persist immediately.
- **`paths(self)`** (Line 549): Sorted tuple of all excluded (normalized) paths.
- **`is_excluded(self, path)`** (Line 557): True when *path* IS an excluded entry or lives beneath one.

#### Class `LeftoverScanner`
Finds leftovers for one uninstalled app, or orphaned folders generally.

The scanner is strictly read-only. Every method returns findings with
evidence; nothing is removed here.

``exclusions`` (optional) drops findings the user previously chose to
keep; ``cancel_event`` makes every long sweep cooperative - once set,
sweeps stop early and partial results are returned.

- **`__init__(self, installed_apps, policy, exclusions, cancel_event)`** (Line 605): Initialize the scanner; the app inventory loads lazily on first scan.
- **`_cancelled(self)`** (Line 619): True when the caller's cancel_event (if any) has been set.
- **`_allowed(self, f)`** (Line 623): True when the finding is not under a user exclusion.
- **`_ensure_inventory(self)`** (Line 629): Lazily load installed apps and build name/publisher/location sets.
- **`_load_live_inventory(self)`** (Line 645): Return a copy of the installed-app list (loading it if needed).
- **`scan_app(self, app)`** (Line 653): Full leftover sweep for one uninstalled application.

Sweeps run in sequence; setting ``cancel_event`` stops the pipeline
between sweeps and returns whatever was found so far.
- **`scan_orphans(self)`** (Line 685): Find Program Files orphan folders (no live app claims them).
- **`_disambiguate_similar(self, app, findings)`** (Line 715): Penalise weaker name matches when several folders compete.

BCU's ``TestForSimilarNames`` guard: if multiple leftover folders
match the product's tokens, only the one whose name is closest to the
display name keeps its full confidence - e.g. for "AppX", a folder
"AppX" must outrank "AppX Extended", which likely belongs to another
product. Applied only when there IS a clear winner (distance strictly
smaller than a competitor's).
- **`_sweep_roots(self)`** (Line 745): Sweep roots: Program Files (both), ProgramData, AppData variants.

Includes LocalLow, VirtualStore and the per-user Programs folders;
duplicates and non-existent roots are filtered out.
- **`_program_dir_roots(self)`** (Line 773): Program-directories only (Program Files x2, LocalAppData\Programs).
- **`_sweep_filesystem(self, app, tokens, findings)`** (Line 785): Walk every sweep root (max 2 levels) matching folder names to tokens.
- **`_walk_fs_level(self, app, tokens, directory, depth, findings)`** (Line 791): Depth-limited directory walk collecting token-matching folders.

Skips blacklisted names, prohibited paths, reparse points and
system-attributed folders; matches folders by cleaned-name
containment or product-name distance, scores content, and descends
regardless of match (vendor\App\Cache nesting), but never past
_MAX_FS_DEPTH. Loose files at the root level are ignored.
- **`_score_folder_content(self, path, f, app)`** (Line 838): Score a matched folder by walking its contents (read-only).

Counts files and total size (reparse points are not descended),
awards points for empty/leaf/publisher-parent folders, and penalizes
executables present, >100 files, and folders named after the publisher
(shared vendor-folder risk).
- **`_score_orphan_folder(self, path, f)`** (Line 886): Score an orphan folder: emptiness, executables, file count, name.
- **`_claimed_by_live_app(self, path, name_lower)`** (Line 919): True when a currently-installed app claims this name/location.
- **`_folder_identity(self, name)`** (Line 931): Strip trailing version numbers/decorations from a folder name.
- **`_sweep_registry(self, app, tokens, findings)`** (Line 945): Walk HKLM/HKCU SOFTWARE branches (read-only) matching keys to tokens.

Covers SOFTWARE, Wow6432Node and VirtualStore MACHINE\SOFTWARE in
both hives, blacklisting system subtrees and stopping at
_MAX_REG_DEPTH levels.
- **`_walk_reg_level(self, app, tokens, hive, hive_name, key, display_path, depth, findings)`** (Line 970): Recursive registry walk: matches subkey names or explicit pointers.

Skips blacklisted subkeys; scores token matches by depth and adds a
strong bonus when a value in the key points into the app's install
location; recurses up to _MAX_REG_DEPTH levels (read-only access).
- **`_explicit_pointer(self, key, app)`** (Line 1018): True when a value under *key* references the app's install dir.
- **`find_residual_uninstall_keys(self, app)`** (Line 1040): Uninstall keys still present after the app was removed.
- **`_same_product(a, b)`** (Line 1068): True when two uninstall entries denote the same product.

Matches on identical name, identical install location, or a
near-perfect name distance.
- **`_start_menu_dirs(self)`** (Line 1085): Existing user and common Start Menu directories, if present.
- **`_sweep_shortcuts(self, app, findings)`** (Line 1096): Flag .lnk files whose target lives in the dead install location.
- **`_com_branches(self)`** (Line 1133): Registry branches searched for orphaned COM registrations.
- **`_sweep_com(self, app, findings)`** (Line 1143): Flag CLSID/TypeLib registrations whose server binary is gone.

BCU's guard rails apply: GUIDs containing ``-0000-`` are treated as
OS classes and skipped, and a registration only counts when its
InprocServer32/LocalServer32 (or TypeLib win32 path) resolves into
the app's dead install location.
- **`_com_server_path(key, branch)`** (Line 1199): Default value naming the server binary under a COM key.
- **`_sweep_inno_log(self, app, findings)`** (Line 1240): Files the installer wrote that its own uninstaller failed to remove.

InnoSetup records every installed file in ``unins000.dat`` inside the
install directory. The format is undocumented, but absolute paths are
stored as plain UTF-16LE runs - extracting and existence-checking them
yields an exact leftover manifest without depending on format details.
- **`_sweep_services(self, app, findings)`** (Line 1284): Services whose ImagePath binary lives in the dead install dir.
- **`_sweep_tasks(self, app, findings)`** (Line 1333): Scheduled tasks whose <Command> points into the dead install dir.
- **`_cross_check(self, app, findings)`** (Line 1365): Penalize findings that a still-installed sibling app claims.

#### Class `CleanOutcome`
What happened to one finding during cleanup.

- **`to_dict(self)`** (Line 1409): Return a plain-dict view of this outcome (for journals).

#### Class `LeftoverCleaner`
Removes reviewed findings with Recycle Bin + registry backups + journal.

Undo layers, in order of preference:

0. Optional **System Restore point** created before anything is touched
   (``create_restore_point=True``). The outcome - created, throttled by
   Windows' 24-hour rule, or unavailable - is recorded honestly in the
   journal either way; a failed checkpoint never blocks the cleanup.
1. Files/folders go to the **Recycle Bin** via ``send2trash``. If the bin
   cannot hold an item (too large / volume without one) send2trash raises
   instead of silently destroying data - that outcome is surfaced, never
   hidden.
2. Every registry key is exported with ``reg export`` to a timestamped
   backup folder *before* deletion; double-clicking the ``.reg`` file
   restores it.
3. An atomic JSON journal records every disposition for support/audit.

- **`__init__(self, backup_root, policy)`** (Line 1434): Initialize with a safety policy and session-backup root
(default ``~/CortexCleanerBackups/leftovers``).
- **`clean(self, findings, create_restore_point, exclusions, cancel_event)`** (Line 1442): Remove reviewed findings, one per disposition, with undo layers.

Dispatches by kind: registry keys and services via ``reg`` (backed
up first), tasks via ``schtasks`` (XML backed up), and
folders/files/shortcuts via send2trash (Recycle Bin). Honors
protected paths and user exclusions as defense in depth, supports
cooperative cancellation between items, optionally creates a System
Restore point, and always writes a JSON journal of outcomes to a
timestamped session folder under backup_root.
- **`_restore_point()`** (Line 1493): Best-effort System Restore checkpoint; returns an honest note.
- **`_recycle(self, f)`** (Line 1508): Move a file/folder/shortcut to the Recycle Bin via send2trash.

Returns a failed outcome when send2trash is not installed or the
bin rejects the item; never falls back to permanent deletion.
- **`_clean_registry(self, f, session)`** (Line 1527): Export a registry key with ``reg export``, then delete it.

The .reg backup is written into the session folder so a double-click
restores the key; both commands run with a 30s timeout and
shell=False. Requires admin rights for HKLM keys.
- **`_clean_service(self, f, session)`** (Line 1566): Stop + delete a Windows service, with a .reg backup first.
- **`_clean_task(self, f, session)`** (Line 1601): Delete a scheduled task; its XML definition is backed up first.
- **`_tasks_root_for(self, task_name)`** (Line 1633): On-disk XML for a task: Tasks stores '<name>.xml' per task.
- **`_write_journal(self, session, journal, outcomes, restore_note)`** (Line 1639): Write the session journal.json atomically (tmp file + os.replace).

Records the timestamp, restore-point note, per-item dispositions
and ok/fail counts; write failures are logged, never raised.

### Module: `src/cortex_unified/system_tools/load_tester.py`
*Load / resilience tester - measure how much YOUR OWN service can take.

This is the legitimate, defensive counterpart to a stress tool: you point it at
infrastructure you control, push realistic high load, and learn where it
degrades and where it falls over - so you fix the weak point before a real
incident. It reports the same metrics professional tools (k6, Locust, JMeter)
report: throughput (RPS), latency percentiles (p50/p95/p99), and error rate.

SAFETY MODEL (enforced in code, not deferred):
* A target is only allowed if it is loopback / private-LAN / link-local (your
  own environment), OR a public host you prove you control by hosting a token
  file at ``/.well-known/cortex-loadtest-authorization``.
* There is NO source spoofing, NO evasion, NO stealth, NO distributed
  coordination - none of which have any place when testing your own systems.
  The traffic is honest and identifies itself so your own defenses (rate
  limiters, WAF, autoscaling) engage - which is the whole point of the test.
* Concurrency and duration are capped, and every run is written to an audit log.*

#### Class `Authorization`
Authorization data container.

- **`to_dict(self)`** (Line 60): To dict.

#### Class `TargetAuthorizer`
Decides whether a target may be load-tested. Private = yours = allowed.

- **`classify(host)`** (Line 72): Return (category, resolved_ip) for *host* without any network calls
beyond DNS resolution.
- **`authorize(self, host, ownership_token, verify_public)`** (Line 99): Authorize.
- **`_verify_ownership(host, token)`** (Line 124): Fetch the token file the user placed on their server and compare.
- **`new_token()`** (Line 139): Generate a random token for the user to host on their server.

#### Class `HttpLoadConfig`
Http Load Config data container.


#### Class `TcpLoadConfig`
Tcp Load Config data container.


#### Class `LoadResult`
Load Result data container.

- **`rps(self)`** (Line 185): Rps.
- **`error_rate(self)`** (Line 190): Error rate.
- **`percentile(self, p)`** (Line 194): Percentile.
- **`summary(self)`** (Line 202): Summary.

#### Class `LoadTester`
Runs authorized load tests and reports resilience metrics.

- **`__init__(self)`** (Line 230): Initialize Load Tester.
- **`run_http(self, cfg, auth, progress, cancel_event, confirm, safe_mode)`** (Line 236): Run http.
- **`run_tcp(self, cfg, auth, progress, cancel_event, confirm, safe_mode)`** (Line 308): Run tcp.
- **`_run_pool(worker, conc, deadline, cancel, progress, result, start)`** (Line 366): _run_pool.
- **`_progress_snapshot(result, start, final)`** (Line 384): _progress_snapshot.
- **`_audit(kind, target, auth, conc, dur)`** (Line 399): _audit.

### Module: `src/cortex_unified/system_tools/memory_compression_tuner.py`
*Cortex Cleaner — Windows Memory Compression & SysMain Optimizer.

Inspects and tunes Windows 10/11 Memory Compression (MMAgent):
- Measures real-time RAM compressed store size, total working set, and commit footprint.
- Audits MMAgent subsystem state: MemoryCompression, PageCombining, ApplicationPreLaunch.
- Calculates memory compression efficiency ratio and physical RAM savings.
- Allows toggling memory compression for latency-critical gaming/rendering workstations.*

#### Class `MemoryCompressionStatus`
Memory Compression Status data container.

- **`compressed_mb(self)`** (Line 38): Compressed mb.
- **`total_ram_gb(self)`** (Line 43): Total ram gb.
- **`available_ram_gb(self)`** (Line 48): Available ram gb.

#### Class `MemoryTunerReport`
Memory Tuner Report data container.


#### Class `MemoryCompressionTuner`
Enterprise Windows Memory Compression & MMAgent Optimizer.

- **`__init__(self)`** (Line 63): Initialize Memory Compression Tuner.
- **`audit(self)`** (Line 67): Query memory compression configuration and memory pressure.
- **`set_memory_compression(self, enable)`** (Line 157): Enable or disable Windows memory compression via MMAgent.

### Module: `src/cortex_unified/system_tools/memory_optimizer.py`
*Cortex Cleaner — Working Set & System RAM Memory Optimizer.

Inspects:
1. Physical RAM composition (Total, Used, Free, Cached, Available).
2. Per-process Working Set and Private Bytes.
3. Safe process working set trimming via Win32 psapi.EmptyWorkingSet.*

#### Class `SystemRamMetrics`
System Ram Metrics data container.


#### Class `ProcessMemoryItem`
Process Memory Item data container.


#### Class `MemoryOptimizeResult`
Memory Optimize Result data container.

- **`ok(self)`** (Line 59): Ok.
- **`message(self)`** (Line 64): Message.
- **`to_dict(self)`** (Line 70): To dict.

#### Class `MemoryOptimizer`
Production Windows RAM composition inspector and process working set optimizer.

- **`get_system_ram_metrics(cls)`** (Line 92): Query physical RAM metrics using psutil and Win32 GlobalMemoryStatusEx.
- **`scan_process_memory(cls, limit)`** (Line 112): Scan active processes and sort by Working Set (physical RAM consumption).
- **`trim_process_working_set(cls, pid)`** (Line 143): Trim the working set of a specific process via Win32 EmptyWorkingSet.
- **`optimize_all_background_working_sets(cls, pids)`** (Line 179): Trim working sets of non-critical processes.

### Module: `src/cortex_unified/system_tools/memory_standby_purger.py`
*Windows NT Kernel RAM Standby List & Working Set Purger.

Utilizes undocumented native NTDLL SystemMemoryListInformation (Class 80) calls
to flush the system standby memory cache, empty process working sets, and eliminate
micro-stutter in competitive gaming, video rendering, and heavy local LLM inference.
Requires SeProfileSingleProcessPrivilege (automatically acquired via TokenPrivileges).*

#### Class `LUID`
L U I D.


#### Class `LUID_AND_ATTRIBUTES`
L U I D_ A N D_ A T T R I B U T E S.


#### Class `TOKEN_PRIVILEGES`
T O K E N_ P R I V I L E G E S.


#### Class `MEMORYSTATUSEX`
M E M O R Y S T A T U S E X.


#### Class `MemorySnapshot`
Current system memory status.

- **`to_dict(self)`** (Line 89): To dict.

#### Class `PurgeResult`
Outcome of kernel memory purge operations.


#### Class `MemoryStandbyPurger`
Manages kernel memory standby list purging and working set trimming.

- **`__init__(self)`** (Line 115): Initialize Memory Standby Purger.
- **`get_memory_snapshot(self)`** (Line 129): Query real-time physical and virtual memory allocation.
- **`enable_privilege(self, priv_name)`** (Line 149): Enable specified security privilege in current process token.
- **`purge_standby_list(self)`** (Line 177): Purge system standby list cache (MemoryPurgeStandbyList = 4).
- **`purge_working_sets(self)`** (Line 181): Flush working sets across processes (MemoryEmptyWorkingSets = 2).
- **`purge_modified_page_list(self)`** (Line 185): Flush modified page list to storage (MemoryPurgeModifiedPageList = 3).
- **`_send_memory_command(self, cmd_val, label)`** (Line 189): Issue command to NtSetSystemInformation.

### Module: `src/cortex_unified/system_tools/mft_slack_scrubber.py`
*NTFS Master File Table ($MFT) & Directory Index Slack Scrubber.

Forensically inspects NTFS MFT geometry, resident record slack, and directory index
allocation buffers ($INDEX_ALLOCATION). Identifies residual filenames and resident
data fragments left behind in unallocated MFT records after file deletion, and provides
safe sanitization according to NIST 800-88 standards.*

#### Class `NtfsMftGeometry`
NTFS volume geometry and MFT allocation metadata.

- **`to_dict(self)`** (Line 39): To dict.

#### Class `MftScrubReport`
Report on MFT slack and index allocation sanitization.

- **`to_dict(self)`** (Line 65): To dict.

#### Class `MftSlackScrubber`
Auditor and scrubber for NTFS Master File Table and directory slack space.

- **`__init__(self, volume)`** (Line 80): Initialize Mft Slack Scrubber.
- **`query_geometry(self)`** (Line 87): Query volume geometry using fsutil fsinfo ntfsinfo.
- **`parse_ntfsinfo_output(cls, volume, text)`** (Line 109): Parse stdout of 'fsutil fsinfo ntfsinfo <volume>'.
- **`audit(self)`** (Line 149): Perform non-destructive audit of MFT record slack.
- **`scrub(self)`** (Line 160): Execute sanitization of unallocated MFT slack records and index slack.

### Module: `src/cortex_unified/system_tools/model_cache_manager.py`
*Model cache manager – hardlink-aware HF hub, Ollama, LM Studio, ComfyUI.

Research grounding
----------------
* Interconnectd Forum (2026) – HF hub ``~/.cache/huggingface/hub`` CAS:
  blobs/ (SHA) + refs/snapshots symlinks; interrupted downloads create
  orphan blobs; 1.2T token dedup 3h on 32 GPUs; quantization table
  (FP16→Q4 saves 75%); ``docker pull vllm`` overlay2 dangling layers.
* ai-model-scanner (PyPI 2026) – known tool paths scan + duplicate hashing.
* model-warden (Rust, 2024) – content-identity SHA256, hardlink dedup,
  verified backup, ``hf cache rm`` / ``ollama rm`` via owning tool.
* GriffinCanCode/clearmodel (Rust 2025) – TOML path traversal hardening,
  async ``walkdir`` + ``tokio`` parallel ops.
* Hugging Face Skills/hf-mem – HTTP Range estimate of GGUF/safetensors
  RAM without download.

Why hardlink-aware
------------------
HF hub uses *hard links* (or symlinks on some FS) from
``blobs/<sha>`` to ``refs/models--org--repo/snapshots/<rev>/model.safetensors``.
Explorer counts each link separately → “actual size” is inflated
(Dirty). The *real* disk usage is the sum of unique inodes (st_ino+st_dev).
Deleting a blob without checking refs corrupts *multiple* model revisions.
Similarly, Ollama's ``~/.ollama/models/blobs/sha256-*`` is content-addressed
but managed by the ``ollama`` CLI; manual rm breaks the manifest.

This manager therefore:

* Measures HF cache via inode deduplication (hardlink-aware).
* Finds *orphan* blobs (no incoming snapshot symlink) – safe via
  ``huggingface-cli delete-cache --orphans``.
* Finds Ollama / LM Studio / ComfyUI / MLX model files with size and
  hardlink-aware duplicate detection (same inode = zero extra disk).
* Never deletes inside a store another tool owns directly; it routes
  through the owning CLI (``hf cache rm``, ``ollama rm``) and verifies.

All paths validated against traversal (clearmodel-style).*

#### Class `ModelStore`
One cache store (HF hub, Ollama, etc.).

- **`to_dict(self)`** (Line 95): To dict.

#### Class `ModelCacheManager`
Scan and safely clean model caches.

- **`_get_comfyui_candidates(cls)`** (Line 174): _get_comfyui_candidates.
- **`COMFYUI_CANDIDATES(self)`** (Line 199): COMFYUI CANDIDATES.
- **`_first_existing(self, candidates)`** (Line 208): _first_existing.
- **`scan_hf_hub(self, progress, cancel_event)`** (Line 226): Measure HF hub cache, hardlink-aware, and count orphan blobs.
- **`scan_ollama(self)`** (Line 284): Scan ollama.
- **`scan_all(self, progress, cancel_event)`** (Line 296): Scan all.
- **`clean_hf_orphans(self, dry_run, timeout)`** (Line 321): Run ``huggingface-cli delete-cache --orphans`` safely.

Returns (success, message, freed_bytes_estimate). Uses owning tool's
own CLI (model-warden rule: never write inside a store another tool owns
directly). Verifies via before/after actual size.
- **`delete_hf_revision(self, repo, revision, dry_run, timeout)`** (Line 349): Delete a specific HF revision via ``huggingface-cli delete-cache`` (verified).

``repo`` is ``org/repo`` and ``revision`` is the snapshot hash or tag.
- **`explain_quantization_saving(model_bytes, quant)`** (Line 370): Quantization saving estimate per Interconnectd table (FP16 2B/param).

Q4_K_M ≈ 0.5 B/param = 75% saving vs FP16.
- **`read_safetensors_metadata(path)`** (Line 383): Zero-copy SafeTensors metadata parser.
Reads 8-byte little-endian header length + JSON metadata header without loading weights.
- **`read_gguf_metadata(path)`** (Line 435): Zero-copy GGUF binary metadata parser (extracts arch, quantization, context size).
- **`summarize(self)`** (Line 461): Summarize.

### Module: `src/cortex_unified/system_tools/network_automation.py`
*Safe Windows scheduling for unattended private-LAN inventory scans.*

#### Class `NetworkSchedule`
Network Schedule data container.


#### Class `NetworkScheduleError`
Raised when schedule validation or OS task creation fails.


#### Class `NetworkScanScheduler`
Purpose-built adapter that can only schedule Cortex LAN scans.

- **`supported()`** (Line 110): Supported.
- **`create(self, spec)`** (Line 114): Create.
- **`delete(self)`** (Line 127): Delete.
- **`status(self)`** (Line 136): Status.

### Module: `src/cortex_unified/system_tools/network_discovery.py`
*Deep LAN device discovery - find everything actually on your network.

Why the old ARP-only scan missed devices
----------------------------------------
``arp -a`` prints the OS **neighbour cache**, which only holds entries for
hosts this PC has exchanged unicast traffic with recently (entries also age
out in minutes). Nothing proactively fills it in for the rest of the subnet.
So a sleeping phone, a Google TV you have never opened a socket to, or an
ESP32 quietly running its own firmware are all simply absent - not because
they are hidden, but because the cache was never the right place to look.

How this module finds them instead
----------------------------------
No single technique finds every device, so all of these run and their results
are merged, with each device recording *which* methods saw it:

* **Forced ARP resolution** (the workhorse). Sending any packet to a LAN IP
  makes the OS ARP for it first, and a device must answer ARP at the link
  layer to use the network at all - even when it silently drops ICMP and every
  TCP/UDP port, which phones, printers and IoT gear routinely do. We poke
  every address in the subnet with a cheap UDP datagram, then re-read the
  neighbour cache. This is the same reason ``nmap`` prefers ARP for local
  targets.
* **Neighbour cache read**, including IPv6 via ``Get-NetNeighbor`` on Windows.
* **mDNS / DNS-SD** (224.0.0.251:5353) - the richest source of *names*.
  Chromecast/Google TV, AirPlay, ESPHome/Arduino boards, printers and NAS
  boxes all advertise here, so this is what turns "192.168.1.47" into
  "living-room-tv".
* **SSDP / UPnP** (239.255.255.250:1900) - smart TVs, streamers, routers,
  consoles.
* **WS-Discovery** (239.255.255.250:3702) - Windows PCs and network printers.
* **NetBIOS name service** (UDP 137) - names for Windows and Samba hosts.
* **Reverse DNS** - names handed out by the router's resolver.

Honesty and safety
------------------
* Unlike the old passive scan, this **actively sends probes**. They go only to
  the private subnets of this PC's own interfaces - the module refuses to probe
  anything else, and never touches the internet.
* Every device says which methods observed it, so "we think this exists"
  is always backed by evidence rather than asserted.
* Two things genuinely cannot be worked around, and are reported rather than
  papered over: Wi-Fi **client isolation** (the access point refuses to forward
  traffic between clients, making peers unreachable from your PC by design),
  and **MAC randomization** (a phone deliberately hiding its identity). Both
  are surfaced as findings so the user knows the limit is the network, not the
  tool.*

#### Class `Device`
One discovered device, with the evidence that found it.

- **`randomized_mac(self)`** (Line 200): True when the device is using a privacy/randomized MAC.
- **`label(self)`** (Line 205): Best available human name for the device, never empty.

Preference order is deliberately "what a person would recognise":
the device's own friendly name, then its model, then a service
instance name, then the hostname - because many devices (Chromecast
in particular) use a raw UUID as their hostname, which is useless to
read and worse than showing the model.
- **`_looks_like_uuid(text)`** (Line 232): True for machine-generated identifiers not worth showing as a name.
- **`kind(self)`** (Line 239): Best-effort device category, derived only from observed evidence.

Every rule below reads either a protocol the device actually answered,
a port it actually accepted, or a name the device (or the IEEE registry)
actually reported. Nothing is inferred from a hand-maintained list of
MAC prefixes, so this cannot go stale or mislabel new hardware - it can
only say less than it might, which is the safer failure.
- **`evidence(self)`** (Line 292): Plain description of how we know this device is there.
- **`merge(self, other)`** (Line 307): Fold another observation of the same device into this one.
- **`to_dict(self)`** (Line 336): To dict.

#### Class `Interface`
A local IPv4 interface worth scanning.

- **`network(self)`** (Line 380): Network.

#### Class `DiscoveryResult`
Everything a scan found, plus evidence-backed audit results.

- **`to_dict(self)`** (Line 403): To dict.

#### Class `NetworkDiscovery`
Multi-protocol LAN discovery. Probes only this PC's own subnets.

- **`__init__(self, timeout_s, workers)`** (Line 434): Initialize Network Discovery.
- **`scan(self, progress, cancel_event, deep, rounds, audit_profile, include_upnp_wan, record_history, requested_networks, custom_ports, nmap_modes, advisory_catalog_path)`** (Line 442): Discover devices, then run the selected defensive audit tier.

``deep`` controls host discovery (ARP sweep and name resolution).
``audit_profile`` controls service coverage: ``targeted`` checks a
compact classifier set, ``advanced`` checks common services plus safe
UDP probes, and ``deep`` checks every TCP port. ``requested_networks``
can narrow scanning to subnets attached to this PC, never broaden it.
``custom_ports`` augments the selected profile. Optional Nmap modes are
explicit and operate only on discovered in-scope hosts. UPnP WAN reads
and local history are explicit caller choices.
- **`local_interfaces()`** (Line 663): Return this PC's up, private IPv4 interfaces.
- **`_local_devices(interfaces)`** (Line 693): Represent this PC itself, one entry per active interface.
- **`default_gateways(self)`** (Line 726): Return default-gateway IPs (used to label the router).
- **`_read_neighbors(self)`** (Line 753): Read the OS neighbour cache (ARP for IPv4, NDP for IPv6).
- **`_read_neighbors_windows(self)`** (Line 761): Use ``Get-NetNeighbor``, which exposes reachability state too.
- **`_read_arp_command(self)`** (Line 786): Fallback: parse ``arp -a`` (works on every platform).
- **`_broadcast_ping(targets)`** (Line 813): Send a UDP datagram to each subnet's broadcast address.

Cheap and occasionally productive: some stacks answer broadcast traffic
and end up in the ARP table before the unicast sweep begins. Failure is
completely uninteresting, so it is ignored.
- **`_arp_sweep(self, hosts, cancel_event, settle_s)`** (Line 829): Send one cheap UDP datagram per host to force ARP resolution.

We deliberately ignore whether anything answers on the port: the point
is that the OS must resolve the MAC *before* it can send the datagram,
and a device has to answer ARP to function on the network at all. This
is why it finds hosts that drop every ping and every port probe.

Concurrency is capped well below the thread pool's usual width because
blasting a whole subnet's worth of simultaneous ARP requests makes the
OS drop queued resolutions - which shows up as a device "missing" even
though it is right there. Slower and complete beats fast and wrong.
- **`_is_ipv4(value)`** (Line 872): _is_ipv4.
- **`_usable_host(cls, ip, mac)`** (Line 883): Filter out entries that are not a real, present device.

The critical case is the all-zero MAC. After an ARP sweep, Windows
keeps a neighbour entry for *every* address we probed; the ones that
never answered sit in ``Incomplete``/``Unreachable`` with a
``00-00-00-00-00-00`` link-layer address. Treating those as devices
would report an entire subnet of phantom hosts, so a zero MAC is proof
of absence, not presence.
- **`_ip_sort_key(ip)`** (Line 906): _ip_sort_key.
- **`_merge(into, found)`** (Line 916): _merge.
- **`_run_ps(self, script, timeout)`** (Line 927): _run_ps.
- **`_discover_mdns(self, cancel_event)`** (Line 943): Query mDNS for common service types and collect names + addresses.

Implemented directly on a UDP socket (no extra dependency): we build
standard DNS queries, send them to the mDNS multicast group from every
local interface, then parse every answer that arrives during the
listen window. Devices answer with A records (address), PTR/SRV
(service instance names) and TXT (model details), which together give
us the friendly name that makes a device recognisable.
- **`_absorb_mdns(self, found, data, src_ip)`** (Line 998): Parse an mDNS response and record names/services for the sender.
- **`_split_service_instance(value)`** (Line 1046): Split ``Living Room._googlecast._tcp.local`` into (type, instance).
- **`_build_dns_query(name, qtype)`** (Line 1059): Build a minimal DNS query packet (PTR by default) for *name*.
- **`_parse_dns_records(cls, data)`** (Line 1069): Parse answer/authority/additional records out of a DNS message.

Handles DNS name compression (the 0xC0 pointer form), which mDNS
responders use heavily; without it most real packets are unreadable.
- **`_read_name(data, offset)`** (Line 1114): Read a (possibly compressed) DNS name; returns (name, next_offset).
- **`_discover_ssdp(self, cancel_event)`** (Line 1144): Send an SSDP M-SEARCH and record every responder.

Smart TVs, streaming sticks, consoles and routers answer this even when
they ignore ping, and the ``SERVER``/``ST`` headers usually name the
product directly.
- **`_discover_wsd(self, cancel_event)`** (Line 1206): Send a WS-Discovery Probe - the way Windows itself finds PCs/printers.
- **`_pseudo_uuid()`** (Line 1270): _pseudo_uuid.
- **`_parse_http_headers(data)`** (Line 1278): Parse SSDP's HTTP-style headers into a lower-cased dict.
- **`_resolve_names(self, devices, cancel_event)`** (Line 1289): Fill in hostnames via reverse DNS and NetBIOS, in parallel.
- **`_netbios_name(self, ip, timeout)`** (Line 1319): Send a NetBIOS node-status query (UDP 137) and read the name.
- **`_fingerprint(self, devices, cancel_event)`** (Line 1357): Enumerate services only on discovered, in-scope private hosts.

The scanner revalidates every host against ``_audit_targets`` before a
socket is opened. The attributes are set immediately before this
synchronous call so the established two-argument test/mocking API stays
compatible with older callers.
- **`_build_notes(devices, targets, gateways)`** (Line 1428): Explain the scan's limits, so gaps read as facts not failures.

### Module: `src/cortex_unified/system_tools/network_inventory.py`
*Persistent, point-in-time network inventory with typed change reporting.

This module performs no discovery and starts no background work.  Callers pass
completed observations explicitly; each call is committed atomically to a
bounded SQLite history.  Device identity is necessarily probabilistic because
DHCP can move addresses and modern clients intentionally randomize MACs.*

#### Class `InventoryService`
Inventory Service data container.

- **`key(self)`** (Line 68): Stable dedup key of protocol, port, and lowercase name.
- **`to_dict(self)`** (Line 72): Serialize the service with details made JSON-safe.

#### Class `InventoryFinding`
Inventory Finding data container.

- **`key(self)`** (Line 91): Dedup key: the code, falling back to the title.
- **`to_dict(self)`** (Line 95): Serialize the finding with details made JSON-safe.

#### Class `InventoryDevice`
Inventory Device data container.

- **`to_dict(self)`** (Line 117): Serialize the device, expanding services and findings.

#### Class `DeviceMetadata`
Device Metadata data container.

- **`to_dict(self)`** (Line 141): Serialize metadata (custom name, trust state, tags, notes).

#### Class `InventoryChange`
Inventory Change data container.

- **`to_dict(self)`** (Line 164): Serialize the change, JSON-sanitizing previous/current values.

#### Class `InventoryChanges`
Inventory Changes data container.

- **`to_dict(self)`** (Line 183): Serialize the change groups as lists of change dicts.

#### Class `InventorySnapshot`
Inventory Snapshot data container.

- **`to_dict(self)`** (Line 211): Serialize the snapshot: devices, changes, gateway MAC, identity notice.

#### Class `NetworkInventory`
SQLite inventory with all writes in explicit transactions.

- **`__init__(self, path, retention)`** (Line 381): Open (creating parent dirs) the SQLite store, bound retention, and migrate.
- **`close(self)`** (Line 403): Close the in-memory connection, if any; file DBs close per use.
- **`_new_connection(self)`** (Line 418): Open a SQLite connection with row access and FK/busy-timeout pragmas.
- **`_connect(self)`** (Line 429): Reuse the memory connection, or open a fresh file connection.
- **`_release(self, connection)`** (Line 435): Close a file connection; keep the shared memory connection open.
- **`_migrate(self)`** (Line 440): Create or upgrade the schema version in a transaction (v0 -> v2).
- **`record_snapshot(self, devices, observed_at, gateway_mac)`** (Line 558): Thread-safe compatibility API for complete point-in-time snapshots.
- **`_record_snapshot(self, devices, observed_at, gateway_mac)`** (Line 568): Atomically store a snapshot and compare it with the prior one.
- **`update(self, devices, findings)`** (Line 629): Persist current devices and return the requested focused change groups.
- **`_load_previous(connection)`** (Line 675): Load the newest snapshot's observations, services, findings, and gateway.
- **`_compare(current, previous, previous_gateway, gateway_mac)`** (Line 724): Diff current vs previous observations, flagging identity/service/severity changes.
- **`_store_device(connection, snapshot_id, timestamp, identity_key, confidence, device)`** (Line 848): Upsert device, observation, service, and finding rows for one snapshot.
- **`_enforce_retention(self, connection)`** (Line 913): Delete snapshots beyond the retention limit and orphaned catalog rows.
- **`_metadata_identity(value)`** (Line 934): Validate an ``id:/mac:/ip:`` key, or derive one from a device.
- **`_metadata_values(custom_name, trust_state, tags, notes)`** (Line 949): Validate and normalize custom name, trust state, tags, and notes.
- **`set_metadata(self, identity)`** (Line 971): Atomically create or replace user-owned device metadata.
- **`get_metadata(self, identity)`** (Line 1008): Fetch one device's user metadata, or ``None``.
- **`list_metadata(self)`** (Line 1022): Return all device metadata records ordered by identity key.
- **`_metadata_from_row(row)`** (Line 1035): Rebuild DeviceMetadata from a database row, tolerating bad tag JSON.
- **`exposure_trends(self, limit)`** (Line 1055): Return bounded per-snapshot device/service/finding aggregates.
- **`_csv_cell(value)`** (Line 1083): Escape CSV cells that would parse as spreadsheet formulas.
- **`_csv_value(value)`** (Line 1091): Strip the formula-escape apostrophe when importing CSV cells.
- **`export_inventory_csv(self, path)`** (Line 1100): Export the latest inventory plus metadata with formula escaping.
- **`import_inventory_csv(self, path)`** (Line 1144): Validate and optionally import metadata in one transaction.
- **`snapshot_count(self)`** (Line 1216): Number of retained snapshots in the store.
- **`device_lifetimes(self)`** (Line 1226): Return retained first/last-seen metadata for display or export.

### Module: `src/cortex_unified/system_tools/network_monitor.py`
*Network connection monitor - see what's talking to your machine and out.

Lists active TCP/UDP connections with the owning process, protocol, local and
remote address:port, and connection state. This is a defensive, read-only tool:
it helps a user notice things like an unexpected process making an outbound
connection, or a service listening on all network interfaces (a remote-attack
surface). It never blocks or kills connections - that's the OS firewall's job -
but it points you at what to investigate.

Interpreting the flags we add:
* ``listening_public`` - the socket listens on 0.0.0.0 / :: (every interface),
  so it's reachable from other machines, not just localhost. Worth checking the
  owning program is one you trust to be network-exposed.
* ``remote_external`` - an ESTABLISHED connection to an address that isn't
  loopback or a private LAN range, i.e. out to the internet.*

#### Class `Connection`
Connection data container.

- **`listening_public(self)`** (Line 65): Listening public.
- **`remote_external(self)`** (Line 71): Remote external.
- **`to_dict(self)`** (Line 77): To dict.

#### Class `NetworkMonitor`
Read-only listing of active network connections and their owners.

- **`connections(self)`** (Line 109): Connections.
- **`_meta_for(psutil, pid)`** (Line 156): Return (name, exe_path, friendly_description) for a PID.
- **`summarize(conns)`** (Line 176): Summarize.

### Module: `src/cortex_unified/system_tools/network_scan_cli.py`
*Noninteractive entry point for scheduled private-LAN inventory scans.*

### Module: `src/cortex_unified/system_tools/network_security_audit.py`
*Evidence-backed analysis for authorized private-LAN observations.*

#### Class `SecurityFinding`
Security Finding data container.

- **`to_dict(self)`** (Line 37): To dict.
- **`finding_id(self)`** (Line 54): Finding id.
- **`description(self)`** (Line 59): Description.
- **`recommendation(self)`** (Line 64): Recommendation.
- **`cve(self)`** (Line 69): Cve.

### Module: `src/cortex_unified/system_tools/network_service_scanner.py`
*Bounded, non-destructive service observation on authorized private LANs.

Scans explicit private IPv4 hosts via TCP connect plus passive banner reads,
then narrows identification with bounded HTTP/TLS/MQTT/Redis probes and a small
set of read-only UDP discovery requests. Every target is re-checked against the
caller-supplied allow-list immediately before each probe, responses are capped,
and timeouts/rate limits are hard-bounded so a scan stays quiet and finite.*

#### Class `ScanProfile`
Probe breadth for a scan.

Attributes:
    TARGETED: Common home/lab TCP ports only.
    ADVANCED: Extended TCP list plus UDP discovery probes.
    DEEP: All 65535 TCP ports plus UDP discovery probes.


#### Class `ServiceObservation`
One observed service endpoint on an authorized host.

Attributes:
    ip: Address that answered.
    port: Port probed.
    transport: ``"tcp"`` or ``"udp"``.
    name: Service label; ``"unknown"`` when unidentified.
    state: Connection outcome; only open ports yield observations.
    source: Probe type that produced the evidence.
    banner: Sanitized, size-capped response text.
    product: Server product parsed from the banner, if any.
    version: Product version parsed from the banner, if any.
    metadata: Probe-specific evidence (TLS details, HTTP status, MQTT/Redis codes).
    latency_ms: Round-trip milliseconds for connect or reply.
    confidence: 0-1 estimate that ``name`` is correct.

- **`to_dict(self)`** (Line 94): Serialize the observation with NaN/Inf-safe latency and confidence.
- **`target(self)`** (Line 117): Alias for the observed IP.
- **`service(self)`** (Line 122): Alias for the service name.
- **`details(self)`** (Line 127): Alias for the metadata dict.
- **`evidence(self)`** (Line 132): Evidence strings from metadata, always as a list.

#### Class `_RateLimiter`
Spaces probe starts at most ``rate`` per second across worker threads.

- **`__init__(self, rate)`** (Line 391): Compute the per-probe interval for the given probes-per-second rate.
- **`acquire(self, cancel)`** (Line 397): Wait for the next slot; return False if cancelled while waiting.

#### Class `NetworkServiceScanner`
Scan explicit, authorized private IPv4 hosts with bounded resources.

- **`__init__(self, timeout, workers, rate_limit)`** (Line 409): Clamp socket timeout, worker count, and rate limit into safe bounds.
- **`scan(self, hosts, allowed_networks, profile, progress, cancel_event, custom_ports)`** (Line 420): Return observations for authorized hosts and optional extra ports.

Custom ports augment (rather than replace) the selected profile and are
validated before any socket is created.
- **`_progress(progress, message)`** (Line 464): Invoke the progress callback, swallowing callback exceptions.
- **`_jobs(addresses, ports)`** (Line 475): Yield (ip, port) jobs for every address/port combination.
- **`_scan_tcp(self, addresses, profile, ports, limiter, cancel, observations, progress)`** (Line 486): Probe all (address, port) TCP jobs on a bounded thread pool.
- **`_probe_tcp(self, ip, port, profile, limiter, cancel)`** (Line 533): Rate-limited TCP connect plus passive banner read for one port.
- **`_connect(self, observation)`** (Line 583): Open a TCP socket to the observed endpoint with the scan timeout.
- **`_identify(self, observation, profile, cancel)`** (Line 592): Deepen identification via TLS, HTTP, MQTT, or Redis probes by port.
- **`_probe_tls(self, observation)`** (Line 617): TLS handshake (cert unverified) recording version, cipher, and cert hash.
- **`_probe_http(self, observation, path)`** (Line 641): Bounded HEAD/GET request to fingerprint HTTP servers (Docker, ES).
- **`_probe_mqtt(self, observation)`** (Line 707): Credential-free MQTT CONNECT; flags brokers that accept it (CONNACK 0).
- **`_probe_redis(self, observation)`** (Line 731): Redis PING probe detecting unauthenticated access (+PONG vs NOAUTH).
- **`_scan_udp(self, addresses, profile, limiter, cancel, observations)`** (Line 753): Send bounded UDP discovery probes (plus SNMP for advanced/deep).
- **`_probe_udp(self, ip, port, name, payload)`** (Line 775): One UDP probe requiring a unicast reply from the same scoped host.

### Module: `src/cortex_unified/system_tools/network_stack_optimizer.py`
*Cortex Cleaner — Enterprise Network Stack & DNS Optimizer.

Flushes DNS Resolver cache, purges ARP tables, resets Winsock catalog and TCP/IP stack,
and inspects/tunes TCP Window Auto-Tuning, RSS, and ECN capabilities via netsh.*

#### Class `TcpGlobalSettings`
Tcp Global Settings data container.


#### Class `NetworkResetReport`
Network Reset Report data container.


#### Class `NetworkStackOptimizer`
Production Windows network stack diagnostic and optimization engine.

- **`flush_dns(cls)`** (Line 48): Flush the Windows DNS Resolver cache (ipconfig /flushdns).
- **`clear_arp_cache(cls)`** (Line 62): Purge ARP cache tables (netsh interface ip delete arpcache).
- **`reset_winsock(cls)`** (Line 76): Reset the Winsock catalog back to default configuration.
- **`reset_tcp_ip_stack(cls)`** (Line 90): Reset the TCP/IP stack configuration.
- **`get_tcp_settings(cls)`** (Line 104): Query active Windows TCP global parameters.
- **`set_tcp_autotuning(cls, level)`** (Line 132): Configure TCP Window Auto-Tuning (disabled, highlyrestricted, restricted, normal, experimental).
- **`set_ecn_capability(cls, state)`** (Line 150): Configure Explicit Congestion Notification (enabled / disabled).
- **`execute_complete_network_repair(cls)`** (Line 164): Perform a complete flush and reset of DNS, ARP, Winsock, and TCP/IP.

### Module: `src/cortex_unified/system_tools/network_tools.py`
*Network diagnostic utilities: ping, traceroute, DNS, port & IP checks.

A focused toolbox of the classic utilities every power user reaches for, wired
to the OS's own ``ping``/``tracert`` and Python's ``socket`` so there are no
extra dependencies. These tools inherently reach the target you name (that's
their purpose) - the UI states that clearly - but nothing is sent anywhere you
don't ask for.

Scope choices for safety and honesty:
* The port check is a *connectivity diagnostic* (is host:port reachable) and a
  self-audit of THIS PC's own open ports, not a mass scanner of arbitrary
  hosts.
* IP classification is computed offline from the address itself; we do not call
  external reputation/geolocation services (that needs internet + licensed
  data), so we never claim a location or "reputation" we can't verify.*

#### Class `PingResult`
Ping Result data container.

- **`to_dict(self)`** (Line 59): To dict.

#### Class `Hop`
Hop data container.

- **`to_dict(self)`** (Line 76): To dict.

#### Class `NetworkTools`
Stateless collection of network diagnostics.

- **`ping(self, host, count, timeout_s, cancel_event)`** (Line 88): Ping.
- **`_parse_ping(host, out)`** (Line 114): _parse_ping.
- **`traceroute(self, host, max_hops)`** (Line 147): Traceroute.
- **`_parse_traceroute(out)`** (Line 161): _parse_traceroute.
- **`dns_lookup(host)`** (Line 183): Dns lookup.
- **`reverse_dns(ip)`** (Line 195): Reverse dns.
- **`check_port(host, port, timeout)`** (Line 206): True if a TCP connection to host:port succeeds (reachability).
- **`scan_common_ports(self, host, timeout)`** (Line 214): Check the COMMON_PORTS on *host* (self-audit when host is this PC).
- **`ip_info(address)`** (Line 227): Classify an IP entirely offline - no external lookups, no guesses.
- **`_category(ip)`** (Line 249): _category.
- **`_run(self, args, timeout, cancel_event)`** (Line 269): _run.

### Module: `src/cortex_unified/system_tools/network_traffic.py`
*Live network throughput monitor - system-wide and per-interface.

Uses psutil's I/O counters and computes up/download *rates* from the delta
between successive samples. This is accurate, needs no admin, and is very
cheap (two counter reads per tick), which keeps it in line with Cortex's
lightweight goal.

Honesty note: this reports throughput per network interface, not per process.
Attributing bytes-on-the-wire to individual processes on Windows requires
kernel ETW tracing (the ``Microsoft-Windows-Kernel-Network`` provider) running
as Administrator, which is heavy and fragile; we deliberately don't fake a
per-process byte figure. For per-process insight we use active-connection
counts (see NetworkMonitor), which are real.*

#### Class `NicSample`
Counters and derived rates (bytes/sec) for one network interface.

- **`to_dict(self)`** (Line 34): To dict.

#### Class `TrafficSample`
System-wide rates plus per-NIC breakdown, sorted by total activity.

- **`to_dict(self)`** (Line 57): To dict.

#### Class `TrafficMonitor`
Stateful throughput sampler. Reuse ONE instance for correct rates.

Rates come from the delta between successive samples, so a fresh monitor
reports zeros until its second :meth:`sample` call.

- **`instance(cls)`** (Line 81): Instance.
- **`__init__(self)`** (Line 89): Initialize Traffic Monitor.
- **`sample(self)`** (Line 97): Read psutil I/O counters once and derive rates from the previous sample.

The first call only establishes the baseline. Negative deltas (counter
reset, e.g. after a NIC restart) are clamped to 0 rather than reported
as negative throughput.

### Module: `src/cortex_unified/system_tools/nmap_adapter.py`
*Optional Nmap integration, bounded to explicitly authorized private LANs.

Invokes a user-installed ``nmap`` executable directly (no shell), parses its
XML under hard resource limits, and rejects any target outside the caller's
authorized private IPv4 scopes. Nmap output is treated as untrusted data:
byte/node/depth caps and DTD/entity rejection bound parser exposure.*

#### Class `NmapError`
Base exception for adapter failures.


#### Class `NmapUnavailableError`
Raised when the optional Nmap executable cannot be found.


#### Class `NmapAuthorizationError`
Raised when any requested target is not explicitly authorized.


#### Class `NmapPrivilegeError`
Raised when an expert mode is requested without Windows elevation.


#### Class `NmapExecutionError`
Raised when Nmap exits unsuccessfully.


#### Class `NmapOutputError`
Raised when Nmap XML is malformed, unsafe, or exceeds a bound.


#### Class `NmapStatus`
Side-effect-free optional executable status.


#### Class `NmapAdapter`
Discover and invoke optional Nmap without shell or script support.

- **`__init__(self, executable)`** (Line 327): Initialize Nmap Adapter.
- **`_executable(self)`** (Line 331): _executable.
- **`available(self)`** (Line 338): Available.
- **`status(self)`** (Line 342): Status.
- **`build_arguments(self, targets, allowed_networks, ports, modes)`** (Line 352): Build the nmap argv for one scan; no shell interpolation involved.

``-n -Pn`` skip DNS resolution and host discovery so every target is
probed exactly as given; XML is written to stdout via ``-oX -``.
- **`scan(self, targets, allowed_networks, ports, modes)`** (Line 388): Run one bounded scan and return parsed observations.

*timeout* is clamped to [0.1, 600] seconds. Non-zero exit raises
:class:`NmapExecutionError` with up to 512 bytes of stderr.

### Module: `src/cortex_unified/system_tools/notification_cleaner.py`
*Cortex Cleaner — Windows Action Center & Push Notification Database Cleaner.

Scans and purges Windows Push Notification service databases:
1. %LocalAppData%\Microsoft\Windows\Notifications\wpndatabase.db (Notification history).
2. %LocalAppData%\Microsoft\Windows\Notifications\appmetadata.db (Notification endpoints).
3. Stale push badge caches and transient notification payloads.*

#### Class `NotificationDatabaseStatus`
Notification Database Status data container.


#### Class `NotificationCleanResult`
Notification Clean Result data container.


#### Class `NotificationCleaner`
Production Windows Notification database (wpndatabase.db) sanitizer.

- **`get_status(cls)`** (Line 49): Query notification database paths and sizes.
- **`clean_notification_database(cls)`** (Line 72): Stop WpnService, purge notification database files, and restart service.

### Module: `src/cortex_unified/system_tools/oui.py`
*MAC address identity: IEEE-backed vendor lookup and privacy detection.

Vendor names come only from authoritative sources: the IEEE Registration
Authority registry (MA-L/MA-M/MA-S, downloaded and cached locally) and the
device's own self-reported identity collected elsewhere in the discovery
engine. A hand-curated table was removed deliberately - an audit of its 322
entries against IEEE found 43 wrong vendors, 6 prefixes claimed twice, and
coverage of well under 1% of real assignments, and a wrong name is worse
than none. Whether an address is locally administered (privacy/randomized)
or multicast is computed from the MAC's own bits, so those answers cannot go
stale.*

### Module: `src/cortex_unified/system_tools/pagefile_optimizer.py`
*Cortex Cleaner — Windows Pagefile & Virtual Memory Optimizer.

Inspects and optimizes Windows virtual memory paging files (pagefile.sys, swapfile.sys):
1. Reads active paging file configuration from HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management.
2. Queries total physical RAM and active committed virtual memory via Win32 GlobalMemoryStatusEx.
3. Calculates hardware-tailored recommendations (NVMe vs SATA vs HDD, low RAM vs high RAM).
4. Recommends fixed-size allocation on SSDs to eliminate write amplification from dynamic resizing.
5. Provides safe configuration with automatic backup and rollback.*

#### Class `MEMORYSTATUSEX`
M E M O R Y S T A T U S E X.


#### Class `PagefileConfig`
Pagefile Config data container.


#### Class `VirtualMemoryStatus`
Virtual Memory Status data container.


#### Class `PagefileOptimizer`
Production Windows Virtual Memory and Paging File management engine.

- **`get_memory_metrics(cls)`** (Line 72): Query physical and pagefile memory sizes via GlobalMemoryStatusEx.
- **`get_pagefile_config(cls)`** (Line 92): Read active pagefile registry configuration.
- **`get_status(cls)`** (Line 148): Analyze virtual memory and compute hardware-tailored recommendations.
- **`set_custom_pagefile(cls, drive_letter, initial_mb, maximum_mb)`** (Line 189): Configure custom min/max pagefile size in Windows registry.
- **`set_automatic_pagefile(cls)`** (Line 210): Revert paging file to Windows system-managed automatic mode.

### Module: `src/cortex_unified/system_tools/performance_tuner.py`
*Windows power-plan tuner - safe, reversible performance control.

Wraps ``powercfg`` to list the available power schemes and switch the active
one (e.g. High Performance for gaming, Balanced for everyday, Power Saver on
battery). Switching a power plan is fully reversible and does not delete
anything, so this is a low-risk optimization. We deliberately do NOT touch
registry-based visual-effects tweaks or "game mode" hacks here - those are
easy to get wrong and hard to undo.*

#### Class `PowerPlan`
One Windows power scheme as reported by ``powercfg /list``.

- **`to_dict(self)`** (Line 41): To dict.

#### Class `PerformanceTuner`
List and switch Windows power plans via powercfg.

- **`is_supported()`** (Line 50): powercfg-based control only exists on Windows.
- **`list_plans(self)`** (Line 54): Return available schemes; empty off-Windows or if powercfg fails.
- **`_parse(out)`** (Line 61): _parse.
- **`active_plan(self)`** (Line 75): Return the scheme powercfg marks active, or ``None`` if unknown.
- **`set_active(self, guid)`** (Line 82): Switch the active power plan. Reversible; returns (ok, message).

The GUID is shape-checked before it reaches argv because it comes from
UI state, not from a prior ``/list`` call.
- **`_run(self, args, want_returncode)`** (Line 97): _run.

### Module: `src/cortex_unified/system_tools/power_plan_optimizer.py`
*Cortex Cleaner — Windows Power Scheme & CPU Throttle Optimizer.

Manages Windows Power Plans via powercfg.exe:
1. Lists installed power schemes (Balanced, High Performance, Power Saver, Ultimate Performance).
2. Unlocks Ultimate Performance mode (GUID e9a42b02-d5df-448d-aa00-03f14749eb61).
3. Configures CPU throttling states (Minimum/Maximum processor state) and Core Parking.
4. Manages Windows Hibernation footprint (powercfg /h /type reduced vs off).*

#### Class `PowerScheme`
Power Scheme data container.


#### Class `PowerPlanStatus`
Power Plan Status data container.


#### Class `PowerPlanOptimizer`
Production Windows Power Scheme and CPU performance optimization engine.

- **`get_status(cls)`** (Line 46): Query all installed power schemes and active configuration.
- **`set_active_scheme(cls, scheme_guid)`** (Line 97): Activate the specified power plan GUID.
- **`unlock_ultimate_performance_plan(cls)`** (Line 111): Duplicate and unlock the hidden Ultimate Performance power plan.
- **`set_reduced_hibernation(cls)`** (Line 133): Reduce hiberfil.sys size to 40% of RAM (enables Fast Startup without full RAM snapshot).
- **`disable_hibernation(cls)`** (Line 147): Disable hibernation entirely and delete hiberfil.sys to reclaim gigabytes of disk space.

### Module: `src/cortex_unified/system_tools/prefetch_analyzer.py`
*Cortex Cleaner — Windows Prefetch & SysMain (SuperFetch) Trace Analyzer.

Inspects %WinDir%\Prefetch\*.pf files:
1. Extracts executable name, run count, hash code, and last run time.
2. Identifies stale or orphaned prefetch traces.
3. Provides selective and bulk prefetch trace sanitization.
4. Queries Windows SysMain (SuperFetch) service status.*

#### Class `PrefetchEntry`
Prefetch Entry data container.


#### Class `PrefetchStatus`
Prefetch Status data container.


#### Class `PrefetchCleanResult`
Prefetch Clean Result data container.


#### Class `PrefetchAnalyzer`
Production Windows Prefetch and SuperFetch diagnostic engine.

- **`get_status(cls)`** (Line 64): Query Prefetch directory metrics and SysMain service status.
- **`scan_prefetch_files(cls)`** (Line 115): Scan and parse all .pf files in the Windows Prefetch directory.
- **`clean_prefetch(cls, file_paths)`** (Line 156): Purge selected or all prefetch files.

### Module: `src/cortex_unified/system_tools/privacy_blocker.py`
*Privacy & Telemetry Blocker — 300+ settings, IFEO persistence, profiles.

Research grounding
------------------
* O&O ShutUp10++ 2.0.1009 (2025) — ~300 privacy settings across 20+
  categories, Copilot/Recall removal, .NET 8 portable, Free + Premium
  (client/service architecture with automatic re-application after
  Windows updates, no admin rights for end users, profiles editor).
* WallabyDesigns/windows-telemetry-guard — reversible toolkit with
  timestamped backup, Strict mode (hosts file block of 26 Microsoft
  endpoints), Balanced mode (diagnostic data to Required/Basic),
  IFEO debugger on CompatTelRunner.exe (survives updates).
* SysAdminDoc/TelemetrySlayer — WPF GUI, IFEO on CompatTelRunner.exe
  (taskkill.exe), firewall rules, clears DiagTrack ETL logs, Office
  telemetry, Edge/WebView2, NVIDIA/VS telemetry, preflight recovery
  bundle, survives feature updates.
* N0tHorizon/WindowsTelemetryBlocker — PowerShell, modular (telemetry,
  services, apps, misc), registry backups, rollback scripts, dry-run.
* NX1X/Windows-Privacy-Toolkit — 24-check audit, 25-step OS telemetry
  disable, 9-step Office, 4-step PowerShell, optional advanced
  (15+ tasks, 35+ hosts, firewall), 3 hardening levels, Restore script.
* RajwanYair/RegiLattice — 7,718 tweaks across 158 categories, 5
  machine profiles (business/gaming/privacy/minimal/server), CorporateGuard
  blocks unsafe tweaks on domain/Azure AD/Intune, declarative RegOp
  engine, WinForms GUI + CLI, .NET 10.

Why this matters for Cortex Cleaner
-----------------------------------
* Windows scatters privacy controls across ~150 panels; feature updates
  quietly reset choices or add new endpoints.
* A production tool must be reversible, profile-based, survive updates
  (IFEO + firewall), and support enterprise deployment (profiles,
  no-admin-rights client/service).

Design
------
* **Declarative tweak definitions**: YAML/JSON tweak catalog with
  path, type, recommended value, risk level, category, profile tags.
* **Engine**: `apply(tweak_ids)`, `remove(tweak_ids)`, `status(tweak_ids)`,
  `profile(profile_name)`, `audit()` → JSON report.
* **Persistence**: IFEO debugger on `CompatTelRunner.exe` → `taskkill.exe`
  (survives re-enablement), firewall rules, scheduled task monitoring.
* **Profiles**: `privacy`, `gaming`, `business`, `minimal`, `server`
  (like RegiLattice).
* **Enterprise**: client/service split (Premium) — service holds
  privileges, client UI no admin rights, automatic re-application.
* **Rollback**: timestamped registry exports, restore point, hosts file
  backup, firewall rule export before changes.

Usage::

    from cortex_unified.system_tools.privacy_blocker import PrivacyBlocker
    pb = PrivacyBlocker()
    report = pb.audit()
    pb.apply_profile("privacy")
    # Enterprise:
    pb.enable_auto_enforcement()

References
----------
* O&O ShutUp10++ manual (manuals.oo-software.com)
* WallabyDesigns/windows-telemetry-guard (GitHub)
* SysAdminDoc/TelemetrySlayer (GitHub)
* N0tHorizon/WindowsTelemetryBlocker (GitHub)
* NX1X/Windows-Privacy-Toolkit (GitHub)
* RajwanYair/RegiLattice (GitHub)*

#### Class `TweakDef`
Single privacy tweak definition.

- **`applies_to_current_os(self)`** (Line 129): Applies to current os.

#### Class `PrivacyBlocker`
Declarative privacy tweak engine with profiles and persistence.

- **`__init__(self, tweaks, create_restore_point, progress_callback, cancel_event, dry_run)`** (Line 462): Initialize Privacy Blocker.
- **`_reg_set(self, path, value, data, dtype)`** (Line 482): _reg_set.
- **`_reg_get(self, path, value)`** (Line 499): _reg_get.
- **`_reg_backup(self, path)`** (Line 512): Export registry key to .reg file.
- **`_svc_set_start(self, name, start_type)`** (Line 526): _svc_set_start.
- **`_svc_get_start(self, name)`** (Line 542): _svc_get_start.
- **`_task_set_enabled(self, path, enabled)`** (Line 557): _task_set_enabled.
- **`_fw_add_block(self, name, direction, program)`** (Line 571): _fw_add_block.
- **`_ifeo_set(self, target, debugger)`** (Line 585): _ifeo_set.
- **`_ifeo_remove(self, target)`** (Line 595): _ifeo_remove.
- **`apply(self, tweak_ids)`** (Line 611): Apply tweaks by ID list.
- **`remove(self, tweak_ids)`** (Line 651): Remove/revert tweaks by ID list.
- **`status(self, tweak_ids)`** (Line 694): Check current status of tweaks.
- **`apply_profile(self, profile_name)`** (Line 722): Apply all tweaks tagged with a profile.
- **`audit(self)`** (Line 728): Full privacy audit — returns JSON-serializable report.
- **`list_profiles(self)`** (Line 755): Return profile -> tweak IDs mapping.
- **`export_config(self, path)`** (Line 763): Export current applied tweaks as JSON config.
- **`import_config(self, path)`** (Line 775): Import and apply tweaks from JSON config.
- **`enable_auto_enforcement(self, interval_minutes)`** (Line 780): Register scheduled task for periodic re-application (Premium feature).

### Module: `src/cortex_unified/system_tools/process_analyzer.py`
*Process and service enumeration via platform CLI tools.

Wraps ``tasklist``/``sc`` on Windows and ``ps``/``launchctl``/``systemctl``
elsewhere, parsing their text output into plain dicts. Parsing is deliberately
tolerant: per-line failures increment ``error_count`` instead of aborting the
listing, because partial data still serves a diagnostics view.*

#### Class `ProcessAnalyzer`
Enumerate running processes/services and flag high-resource consumers.

- **`__init__(self, config)`** (Line 19): Use *config* or a default Config; the OS decides which backends run.
- **`list_processes(self)`** (Line 29): Populate ``processes`` from the platform's process listing.
- **`_list_windows_processes(self)`** (Line 46): _list_windows_processes.
- **`_list_macos_processes(self)`** (Line 74): _list_macos_processes.
- **`_list_linux_processes(self)`** (Line 104): _list_linux_processes.
- **`list_services(self)`** (Line 134): Populate ``services`` from the platform's service listing.
- **`_list_windows_services(self)`** (Line 151): List Windows services using sc query.
- **`_list_macos_services(self)`** (Line 182): _list_macos_services.
- **`_list_linux_services(self)`** (Line 204): List Linux services using systemctl, falling back to ``service``.
- **`find_high_resource_processes(self, cpu_threshold, mem_threshold)`** (Line 238): Flag processes at or above the CPU/memory percentage thresholds.
- **`get_stats(self)`** (Line 277): Snapshot counts for UI display.
- **`filter_processes_by_name(self, name_pattern)`** (Line 291): Case-insensitive substring match on process name.
- **`filter_services_by_state(self, state)`** (Line 299): Case-insensitive substring match on service state.

### Module: `src/cortex_unified/system_tools/process_meta.py`
*Human-friendly process identity: what a running program actually is.

Task managers show cryptic names like ``svchost.exe`` or ``fontdrvhost.exe``.
This module turns those into plain-language descriptions so users understand
what's running. It combines two honest sources:

1. A curated table of well-known Windows / common-app processes (instant, no
   disk access), so users get a trustworthy explanation for the usual suspects.
2. The program's own embedded ``FileDescription`` from its PE version resource
   (via pywin32), read once per path and cached. This is the same text Windows
   shows, straight from the vendor - never guessed.

If neither yields anything, we return an empty string rather than inventing a
description. All results are cached, so it stays lightweight on live refreshes.*

### Module: `src/cortex_unified/system_tools/process_token_auditor.py`
*Cortex Cleaner — Process Security Token & Integrity Forensics.

Forensic inspector for Windows process security tokens:
- Inspects Token Integrity Levels (Untrusted, Low, Medium, High, System).
- Audits Token Elevation Types (Default, Full Elevated, Limited Standard).
- Identifies critical dangerous privileges (SeDebugPrivilege, SeImpersonatePrivilege, SeTakeOwnershipPrivilege).
- Detects unauthorized privilege escalation or unconstrained background processes.*

#### Class `ProcessTokenInfo`
Process Token Info data container.


#### Class `ProcessTokenAuditReport`
Process Token Audit Report data container.


#### Class `ProcessTokenAuditor`
Enterprise Process Security Token & Privilege Auditor.

- **`__init__(self)`** (Line 66): Initialize Process Token Auditor.
- **`audit(self, max_processes)`** (Line 70): Audit active running processes and decode their security tokens.
- **`_inspect_token(self, pid)`** (Line 132): Inspect a single process token via Win32 APIs.
- **`_get_integrity_level(self, h_token)`** (Line 153): Query TokenIntegrityLevel.
- **`_get_elevation_type(self, h_token)`** (Line 200): Query TokenElevationType.
- **`_get_privileges(self, h_token)`** (Line 221): Query enabled privileges on the token.

### Module: `src/cortex_unified/system_tools/registry_cleaner.py`
*Orphaned Windows registry entry detection with export-before-delete safety.

Finds uninstall entries whose install path or uninstaller is gone, Run/RunOnce
values pointing at missing executables, file associations whose handler no
longer exists, and SharedDLLs values with a zero reference count and no file
on disk. Deletion via ``winreg`` is irreversible, so :meth:`RegistryCleaner.
backup_registry` should run first - though it only exports the HKCU Uninstall
key, so HKLM deletions have no restore path.*

#### Class `RegistryCleaner`
Find and remove registry entries that reference files no longer on disk.

- **`__init__(self, config)`** (Line 24): Initialize Registry Cleaner.
- **`scan(self)`** (Line 40): Alias used by SmartScanner.
- **`scan_orphaned_entries(self)`** (Line 44): Run all category scans and return the accumulated orphans.
- **`_scan_uninstall_entries(self, hive)`** (Line 66): _scan_uninstall_entries.
- **`_check_uninstall_entry(self, hive, hive_name, full_path, subkey_name)`** (Line 99): _check_uninstall_entry.
- **`_scan_startup_entries(self)`** (Line 140): Check Run/RunOnce keys for entries that reference missing executables.
- **`_scan_file_associations(self)`** (Line 180): Check HKCR (via HKLM\Software\Classes) for associations pointing to missing executables.
- **`_scan_shared_dlls(self)`** (Line 221): Check SharedDLLs registry for entries with reference count = 0.
- **`backup_registry(self, backup_dir)`** (Line 255): Export the HKCU Uninstall key to a .reg file for safety.

Scope is deliberately narrow: ``reg export`` of HKLM trees needs
elevation, so entries under HKLM have no restore path from here.
- **`backup_entry(self, entry, backup_dir)`** (Line 286): Export a specific registry entry to a .reg file before deletion for instant rollback.
- **`remove_orphaned_entry(self, entry, auto_backup)`** (Line 321): Delete an orphaned registry entry with auto-backup for rollback.

Requires appropriate permissions.
- **`get_stats(self)`** (Line 368): Get stats.
- **`filter_by_type(self, entry_type)`** (Line 376): Filter by type.
- **`_reg_val(winreg, key, name, default)`** (Line 385): _reg_val.
- **`_extract_exe_path(raw)`** (Line 395): Extract a file path from a registry value string like:
'"C:\Program Files\App\app.exe" --args'  or  'C:\path\app.exe'

### Module: `src/cortex_unified/system_tools/restart_manager_unlocker.py`
*Windows Native Restart Manager File Unlocker & Process Lock Auditor.

Research Grounding
------------------
* Microsoft Windows Restart Manager Architecture (`rstrtmgr.dll`, Windows Vista - Windows 11):
  Traditional file unlockers rely on brute-force scanning of every kernel handle across
  the entire operating system (`NtQuerySystemInformation` with `SystemHandleInformation`),
  which can cause hard driver deadlocks, AV heuristic flags, and system instability.
  The native Windows Restart Manager is Microsoft's official, zero-impact API designed
  to identify exactly which applications or NT services hold open locks on specific files.
* Restart Manager Sequence:
  1. `RmStartSession`: Allocates a unique caller session GUID.
  2. `RmRegisterResources`: Registers target file paths with the session.
  3. `RmGetList`: Queries `RM_PROCESS_INFO` records for PIDs, executable names, and service identities.
  4. `RmShutdown`: (Optional) Gracefully requests locked processes to save state and terminate.
  5. `RmEndSession`: Releases session memory and kernel structures.

This module binds `rstrtmgr.dll` via `ctypes` for native lock detection, with an
integrated fallback to `psutil` open-file inspection when non-elevated or on test platforms.*

#### Class `RM_UNIQUE_PROCESS`
R M_ U N I Q U E_ P R O C E S S.


#### Class `RM_PROCESS_INFO`
R M_ P R O C E S S_ I N F O.


#### Class `LockingProcessInfo`
Identity and telemetry of a process holding an exclusive file lock.

- **`to_dict(self)`** (Line 70): To dict.

#### Class `FileLockReport`
Forensic report detailing whether a file is locked and which processes lock it.

- **`to_dict(self)`** (Line 89): To dict.

#### Class `UnlockResult`
Outcome of an unlock or process termination attempt.

- **`to_dict(self)`** (Line 108): To dict.

#### Class `RestartManagerUnlocker`
Native Windows Restart Manager file lock analyzer and process unlocker.

- **`__init__(self)`** (Line 121): Initialize Restart Manager Unlocker.
- **`inspect_locks(self, file_path)`** (Line 131): Query which processes currently lock the given file using Windows Restart Manager.
- **`_get_locking_processes_native(self, abs_path)`** (Line 155): Query rstrtmgr.dll for processes locking abs_path.
- **`_get_locking_processes_psutil(self, abs_path)`** (Line 238): Fallback process inspection via psutil open file handle auditing.
- **`unlock_file(self, file_path, force_terminate)`** (Line 261): Release locks on a file by gracefully or forcefully terminating the locking processes.

### Module: `src/cortex_unified/system_tools/restore_point.py`
*Windows System Restore point management - the trust/safety foundation.

Every risky operation (registry cleaning, telemetry changes, driver updates)
should offer to create a restore point first. This module does that *honestly*:
it never claims success it can't verify.

Reality handled (researched, not assumed):
* ``Checkpoint-Computer`` requires **Administrator**; without elevation it is
  silently rejected - so we check elevation first and report NOT_ELEVATED
  rather than pretending a point was made.
* **System Protection is frequently OFF by default** on Windows 10/11 - a
  create call then does nothing; we detect the failure and report
  PROTECTION_DISABLED with guidance to enable it.
* Windows **throttles** creation to once per 24h (a warning, not an error). We
  compare the restore-point count before/after and report THROTTLED truthfully.

Non-Windows platforms report NOT_SUPPORTED. Nothing here creates a point unless
explicitly asked, and all subprocess calls are time-boxed and window-hidden.*

#### Class `RestoreStatus`
Outcome of a restore-point create attempt - each is honest & distinct.


#### Class `RestorePointResult`
Result of a create attempt.

- **`created(self)`** (Line 66): Created.
- **`ok_to_proceed(self)`** (Line 71): True if it's reasonable to continue a risky op after this attempt.

CREATED and THROTTLED both mean a recent restore point exists; the
others mean the user should be warned before proceeding without one.
- **`to_dict(self)`** (Line 79): To dict.

#### Class `RestorePointManager`
Create and list Windows System Restore points, honestly.

- **`__init__(self)`** (Line 87): Initialize Restore Point Manager.
- **`is_supported()`** (Line 94): Is supported.
- **`is_elevated()`** (Line 99): True if running as Administrator (required to create a point).
- **`create(self, description, restore_point_type)`** (Line 111): Attempt to create a restore point and report the verified outcome.
- **`_parse_create_output(out)`** (Line 156): _parse_create_output.
- **`list_points(self, limit)`** (Line 186): Return existing restore points (most recent first). Empty on failure.
- **`_parse_wmi_time(value)`** (Line 220): Best-effort parse of a WMI CreationTime into an ISO-ish string.
- **`_run_ps(self, script, timeout)`** (Line 230): _run_ps.

### Module: `src/cortex_unified/system_tools/s3_fifo.py`
*S3-FIFO cache eviction — "FIFO queues are all you need" (SOSP'23).

Research grounding
------------------
* Yang et al., "FIFO Queues Are All You Need for Cache Eviction"
  (SOSP'23, best-paper contender, 6594 traces, 14 datasets,
  856 B requests). The central insight is *quick demotion*:
  most objects are accessed once and should be evicted early.
  A tiny 10 % FIFO filter (S) proves more precise than adaptive
  alternatives; the main 90 % queue (M) re-inserts hot objects
  via FIFO-Reinsertion, while a Ghost queue (G) remembers S-evicted
  keys to admit second-chance objects directly to M.

Why this matters for Cortex Cleaner
-----------------------------------
* The cleaner ships a ``CacheCleaner`` and ``ModelCacheManager`` that
  still use naive LRU / age-based policies. Those thrash on scans
  (``.cache/huggingface``, ``.npm``, ``.cargo``, ``.docker``) and
  over-retain one-hit wonders at the expense of hot reuse.
* Replacing the ad-hoc recency logic with S3-FIFO improves hit rate
  *and* scalability: FIFO queues are lock-friendly and 6× faster than
  LRU at 16 threads (SOSP'23 §4). For the desktop cleaner this means
  snappier cache panels and fewer “re-downloaded model” complaints.

Design (faithful to the paper, §4)
----------------------------------
* **Three static FIFO queues** – Small (10 %), Main (90 %), Ghost
  (capacity = |M|, stores only fingerprints, not values).
* **Per-object 2-bit frequency** (capped at 3) incremented on hits;
  no update is needed after the second hit, keeping the fast path
  atomic and branch-free.
* **Insertion** – new key: S if not Ghost, else M; on re-insertion
  from Ghost the Ghost entry is removed.
* **S eviction** (paper Alg. 1, line 14-20): head of S:
  ``freq > 1 → move to M (freq cleared)``, else ``→ Ghost``.
* **M eviction** (FIFO-Reinsertion, §4.1): head of M:
  ``freq ≥ 1 → freq-- and re-insert at tail``, else evict.
* **Thread-safety** – a single re-entrant lock guards all mutations;
  the hot read path (freq bump) is an atomic integer op under the lock,
  matching the paper’s “atomic write upon first/second request”.

References
----------
* J. Yang, Y. Zhang, Z. Qiu, Y. Yue, K. V. Rashmi, "FIFO Queues Are All
  You Need for Cache Eviction", SOSP'23, Koblenz, 2023.
  https://dl.acm.org/doi/10.1145/3600006.3613147  (open preprint:
  https://junchengyang.com/publication/sosp23-s3fifo.pdf)
* HOTOS'23 precursor "FIFO Can Be Better Than LRU" (Yang et al.).
* Thesys-lab/sosp23-s3fifo reference implementation (MIT).

Usage::

    from cortex_unified.system_tools.s3_fifo import S3FIFO
    cache = S3FIFO(capacity=1000)          # 100 small + 900 main
    cache.put("model:bert", b"...")         # insertion follows Ghost rule
    val = cache.get("model:bert")           # hit → freq bump, miss → None
    cache.stats()  # hit/miss/ghost-hit/eviction counters

The class is intentionally *generic* (``Any`` values) so it can back
``ModelCacheManager``, ``DiskAnalyzer`` result caches, and the premium
UI’s memoised page data without a second implementation.*

#### Class `_Entry`
_Entry.


#### Class `S3FIFOStats`
S3 F I F O Stats data container.

- **`to_dict(self)`** (Line 93): To dict.

Returns:
    Result of the operation.

#### Class `S3FIFO`
S3-FIFO cache (SOSP'23) – three static FIFO queues.

Args:
    capacity: Total number of live entries (|S| + |M| ≤ capacity).
        Must be ≥10 (so S gets at least one slot). Default 256.
    small_ratio: Fraction of capacity for the Small queue (default
        0.1 = 10 % as proven optimal in the paper; changing it is
        rarely beneficial).

- **`__init__(self, capacity, small_ratio)`** (Line 122): Initialize S3 F I F O.

Args:
    capacity: capacity.
    small_ratio: small ratio.
- **`_ghost_contains(self, key)`** (Line 150): _ghost_contains.
- **`_ghost_add(self, key)`** (Line 156): _ghost_add.
- **`_ghost_remove(self, key)`** (Line 172): _ghost_remove.
- **`_evict_small_if_needed(self)`** (Line 183): _evict_small_if_needed.
- **`_evict_main_if_needed(self)`** (Line 203): _evict_main_if_needed.
- **`get(self, key)`** (Line 222): Return value or ``None`` on miss; bumps frequency on hit.
- **`put(self, key, value)`** (Line 235): Insert or update ``key``.

Update path: if the key already lives in S or M, only the value
and frequency are updated (no queue movement).
Insertion path: Ghost hit → M, else S, then rebalance.
- **`delete(self, key)`** (Line 265): Remove ``key`` if present; returns True if removed.
- **`contains(self, key)`** (Line 281): Contains.

Args:
    key: key.

Returns:
    Result of the operation.
- **`clear(self)`** (Line 305): Clear.
- **`stats(self)`** (Line 315): Stats.

Returns:
    Result of the operation.
- **`keys(self)`** (Line 337): Keys.

Returns:
    Result of the operation.
- **`snapshot(self)`** (Line 345): Return a JSON-serialisable snapshot of queue states (ordered).

### Module: `src/cortex_unified/system_tools/sandbox_cleaner.py`
*Cortex Cleaner — Windows Sandbox & Virtual Environment Artifact Purger.

Forensic cleaner for virtual environments, containers, and hypervisors:
- Scans Windows Sandbox temporary base images, user containers, and scratch VHDs.
- Audits Hyper-V checkpoint differencing disks (.avhdx) and saved state files (.vsv, .bin).
- Detects orphaned WSL2/WSA virtual disk snapshots.
- Reclaims tens of gigabytes of storage locked in virtual machine caches.*

#### Class `VirtualArtifact`
Virtual Artifact data container.

- **`size_mb(self)`** (Line 33): Size mb.
- **`size_gb(self)`** (Line 38): Size gb.

#### Class `SandboxCleanReport`
Sandbox Clean Report data container.


#### Class `SandboxCleaner`
Enterprise Virtual Environment & Sandbox Artifact Purger.

- **`__init__(self)`** (Line 56): Initialize Sandbox Cleaner.
- **`scan(self)`** (Line 60): Scan system for virtual environment leftovers and sandbox files.
- **`clean(self, target_paths)`** (Line 145): Safely clean selected virtual artifacts.

### Module: `src/cortex_unified/system_tools/search_index_optimizer.py`
*Cortex Cleaner — Windows Search Index Database (Windows.edb) Optimizer.

Inspects, compacts, and rebuilds the Windows Search Catalog database:
1. Queries database size and index locations (%ProgramData%\Microsoft\Search\Data\Applications\Windows).
2. Inspects and manages WSearch (Windows Search) service state.
3. Performs database compaction via ESENT utility (esentutl.exe /d).
4. Provides full search catalog index rebuild reset.*

#### Class `SearchIndexStatus`
Search Index Status data container.


#### Class `SearchIndexOperationResult`
Search Index Operation Result data container.


#### Class `SearchIndexOptimizer`
Production Windows Search Index database diagnostic and compaction toolkit.

- **`get_status(cls)`** (Line 53): Query Windows Search Index database metrics and service status.
- **`compact_database(cls)`** (Line 100): Stop WSearch service, perform offline ESENT compaction (esentutl /d), and restart service.
- **`rebuild_index(cls)`** (Line 157): Trigger an official Windows Search index catalog rebuild.

### Module: `src/cortex_unified/system_tools/secrets_scanner.py`
*Filesystem secrets scanner with live credential validation.

Detects hardcoded credentials and sensitive data (API keys, tokens,
private keys, PII, infrastructure config) using 90+ regex patterns, then
grades each finding by context-aware confidence -- a key in a test fixture
is treated differently from the same key in production code.

Capabilities:
* Archive scanning: zip/tar/tar.gz/tar.bz2 trees that a plain git scan misses.
* Optional live verification against provider APIs (AWS, GitHub, Stripe,
  Slack, OpenAI, npm). Off by default so scanning stays air-gap safe; the
  only network traffic happens when ``--verify`` is explicitly passed.
* Blast-radius assessment: what an attacker could do with each exposed key.
* Git history mode: walks all commits, not just the working tree.
* Baseline/delta mode: report only findings newer than a saved baseline.
* Persistent false-positive suppression database.
* Self-contained HTML report plus Jira/GitHub issue export.
* Compliance mapping (GDPR/HIPAA/PCI-DSS/SOC2) for audit workflows.

Usage:
  sentinel_pro.py scan /path/to/scan
  sentinel_pro.py scan /path/to/scan --verify --archives --report audit.html
  sentinel_pro.py scan /path/to/scan --diff           # delta since baseline
  sentinel_pro.py scan /path/to/scan --git-history    # walk git commits
  sentinel_pro.py scan /path/to/scan --jira-project SEC --jira-url https://...
  sentinel_pro.py baseline save /path/to/scan
  sentinel_pro.py baseline diff /path/to/scan
  sentinel_pro.py verify findings.json
  sentinel_pro.py serve --port 8080
  sentinel_pro.py fp add <finding-id>
  sentinel_pro.py fp list*

#### Class `DetectionPattern`
Detection Pattern data container.


#### Class `Finding`
Finding data container.

- **`to_dict(self)`** (Line 150): To dict.
- **`severity_rank(self)`** (Line 155): Severity rank.
- **`fingerprint(self)`** (Line 160): Fingerprint.

#### Class `ScanStats`
Scan Stats data container.

- **`critical(self)`** (Line 185): Critical.
- **`high(self)`** (Line 189): High.
- **`medium(self)`** (Line 193): Medium.
- **`low(self)`** (Line 197): Low.
- **`unique_files(self)`** (Line 201): Unique files.
- **`live_credentials(self)`** (Line 205): Live credentials.
- **`to_dict(self)`** (Line 209): To dict.

#### Class `VerificationResult`
Verification Result data container.

- **`status_emoji(self)`** (Line 232): Status emoji.

#### Class `DashboardHandler`
Dashboard Handler.

- **`log_message(self, format)`** (Line 2147): Log message.
- **`do_GET(self)`** (Line 2150): Do GET.

### Module: `src/cortex_unified/system_tools/secure_shredder.py`
*Secure File Shredder — DoD 5220.22-M, Gutmann, NIST 800-88, SSD TRIM.

Research grounding
------------------
* NIST SP 800-88 Rev.1 — modern US federal standard: Clear (single
  verified overwrite), Purge (cryptographic erase or block erase),
  Destroy (physical). For post-2001 HDDs and all SSDs, single-pass
  verified overwrite is sufficient; multi-pass is for legacy compliance.
* DoD 5220.22-M (3-pass: 0x00, 0xFF, random + verify) and ECE
  (7-pass with verification) — still required by many government
  contracts for HDDs.
* Gutmann 35-pass — targets specific MFM/RLL encoding patterns of
  pre-2001 drives; overkill for modern media but used for audit checkboxes.
* British HMG IS5 (Baseline/Enhanced), German VSITR, Russian GOST
  R 50739-95, Bruce Schneier 7-pass, RCMP TSSIT OPS-II — international
  standards for compliance.
* SSD/Flash: firmware-level Secure Erase (ATA SECURITY ERASE UNIT /
  NVMe FORMAT with Crypto Erase) is near-instant and reaches
  over-provisioned/reallocated sectors that software overwrites miss.
  TRIM + single random pass is NIST Clear equivalent.

Why this matters for Cortex Cleaner
-----------------------------------
* Standard delete only removes filesystem reference; data remains
  recoverable until overwritten.
* Compliance-driven users (government, healthcare, finance) need
  specific standards with verification reports.
* SSD users need TRIM/Secure Erase, not multi-pass overwrites that
  wear flash cells without adding security.

Design
------
* **Standard enum**: `ShredStandard` with all 15+ algorithms.
* **Storage detection**: `StorageType` (HDD, SSD_NVME, SSD_SATA,
  USB_FLASH, UNKNOWN) via `wmic diskdrive` / `lsblk` / `smartctl`.
* **Smart default**: auto-selects NIST Clear for SSD, DoD 3-pass for
  HDD, Gutmann for legacy compliance flag.
* **Verification**: read-back after each pass (full or sample),
  entropy check, pattern match.
* **Free space wipe**: creates temporary files to fill free space,
  then shreds them; or `cipher /w` on Windows, `fstrim` on Linux.
* **Context menu integration**: `shred.exe "file"` for Explorer.
* **Audit report**: JSON/PDF with standard, passes, verification
  results, timestamps, drive serial, file hashes.
* **Safety**: never shreds system files, pagefile, hibernation,
  BitLocker keys; dry-run mode; recycle bin fallback.

Usage::

    from cortex_unified.system_tools.secure_shredder import SecureShredder, ShredStandard
    shredder = SecureShredder()
    result = shredder.shred_file("secret.pdf", ShredStandard.DOD_5220_22_M)
    # or auto-detect:
    result = shredder.shred_file("secret.pdf")
    # free space wipe:
    result = shredder.wipe_free_space("C:", ShredStandard.NIST_CLEAR)

References
----------
* NIST SP 800-88 Revision 1
* DoD 5220.22-M / ECE
* Peter Gutmann, "Secure Deletion of Data from Magnetic and Solid-State Memory" (1996)
* HMG IA Standard No.5, BSI VSITR, GOST R 50739-95
* ATA SECURITY ERASE UNIT, NVMe FORMAT NVM Command
* cipher.exe /w, fstrim, blkdiscard*

#### Class `StorageType`
Storage Type enumeration.


#### Class `ShredStandard`
Software-executable sanitization standards.

NIST SP 800-88 defines Clear, Purge and Destroy. Destroy is physical
(shredder/incinerator) and therefore has no software implementation;
it is deliberately absent rather than present as a dead enum entry.
Purge via firmware is covered by the two PURGE members, which invoke
ATA/NVMe sanitize commands rather than pattern writes.

- **`passes(self)`** (Line 158): Passes.
- **`name(self)`** (Line 239): Name.
- **`pass_count(self)`** (Line 244): Pass count.
- **`recommended_for(self, storage)`** (Line 248): Recommended for.

#### Class `ShredResult`
Shred Result data container.

- **`to_dict(self)`** (Line 271): To dict.

#### Class `SecureShredder`
Multi-standard secure file shredder with verification.

- **`__init__(self, progress_callback, cancel_event, verify_passes, sample_verification_pct, dry_run)`** (Line 395): Initialize Secure Shredder.
- **`_write_pass(self, f, offset, size, pattern)`** (Line 411): Write a single pass pattern at offset.
- **`shred_file(self, file_path, standard, auto_detect)`** (Line 428): Shred a single file according to standard.
- **`_shred_ssd_firmware(self, path, standard)`** (Line 505): Use firmware Secure Erase for SSD (requires admin).
- **`shred_files(self, file_paths, standard, auto_detect)`** (Line 536): Shred multiple files.
- **`wipe_free_space(self, drive, standard)`** (Line 550): Wipe free space on a drive.
- **`get_smart_default(self, path)`** (Line 582): Get recommended standard for a path.

### Module: `src/cortex_unified/system_tools/service_manager.py`
*Cortex Cleaner — Windows Service Manager & Profile Optimizer.

Provides safe, scenario-based Windows service management:
1. Enumerates all installed Windows services with status, startup type, and PID.
2. Classifies services into safe-to-disable categories (Telemetry, Print, Xbox, Fax, Bluetooth).
3. Offers named optimization profiles (Gaming, Minimal, Developer, Default) with dry-run preview.
4. Creates snapshot restore points before applying service changes.
5. Supports batch start/stop/toggle operations with safety guards for critical OS services.*

#### Class `ServiceInfo`
Service Info data container.


#### Class `ServiceProfileResult`
Service Profile Result data container.


#### Class `WindowsServiceManager`
Production Windows Service profiler and optimizer.

- **`enumerate_services(cls)`** (Line 85): List all Windows services with status, startup type, and safety classification.
- **`stop_service(cls, service_name)`** (Line 138): Stop a running Windows service.
- **`set_startup_type(cls, service_name, startup_type)`** (Line 155): Set service startup type (Auto, Manual, Disabled).
- **`apply_profile(cls, profile)`** (Line 175): Apply a named service optimization profile.

### Module: `src/cortex_unified/system_tools/shader_cache_cleaner.py`
*GPU & DirectX Shader Cache Forensics & Cleanup Engine.

Research Grounding
------------------
* Microsoft DirectX Graphics Infrastructure (DXGI) & Direct3D 12 Pipeline:
  DirectX pre-compiles High-Level Shader Language (HLSL) code into hardware-specific
  binary shader blobs stored in `%LOCALAPPDATA%\D3DSCache`.
* NVIDIA Graphics Architecture:
  Proprietary driver-level shader caches reside in `%LOCALAPPDATA%\NVIDIA\DXCache`
  (DirectX) and `GLCache` (OpenGL/Vulkan), plus legacy `%APPDATA%\NVIDIA\ComputeCache`.
* AMD Radeon Adrenalin Driver Architecture:
  Compiled shader bytecode accumulates in `%LOCALAPPDATA%\AMD\DxCache` and `DxcCache`.
* Intel Graphics Software:
  Intel Arc and Iris Xe shader caches reside in `%LOCALAPPDATA%\Intel\ShaderCache`.

Over time, driver updates, game patches, and uninstalled applications leave gigabytes
of orphaned, unreferenced shader binaries that are never purged by Windows. This module
safely scans, analyzes by access age, and reclaims stale shader cache storage.*

#### Class `ShaderLocationInfo`
Metadata and size analysis for a specific shader cache target location.

- **`to_dict(self)`** (Line 46): To dict.

#### Class `ShaderCacheReport`
Consolidated inventory of GPU shader caches across all hardware vendors.

- **`to_dict(self)`** (Line 70): To dict.

#### Class `ShaderCleanResult`
Outcome of a shader cache purge operation.

- **`to_dict(self)`** (Line 91): To dict.

#### Class `ShaderCacheCleaner`
Production GPU shader cache detection, forensics, and cleanup engine.

- **`__init__(self)`** (Line 105): Initialize Shader Cache Cleaner.
- **`get_known_locations(self)`** (Line 109): Resolve standard shader cache paths dynamically from current user profile.
- **`scan(self, min_age_days)`** (Line 135): Scan all GPU shader cache locations and analyze disk consumption.
- **`clean(self, min_age_days, dry_run)`** (Line 179): Purge stale or orphaned shader cache files across all detected locations.

### Module: `src/cortex_unified/system_tools/shellbags_privacy_cleaner.py`
*Cortex Cleaner — Windows Shellbags & JumpLists Activity Forensics Purger.

Scans and purges Windows Explorer historical activity artifacts:
1. Shellbags Registry Keys (BagMRU, Bags) which record folder view history and directory accesses.
2. Windows JumpLists (AutomaticDestinations, CustomDestinations).
3. Windows Recent Items (%AppData%\Microsoft\Windows\Recent).
4. Explorer Run dialog MRU and TypedPaths.*

#### Class `ShellbagsTarget`
Shellbags Target data container.


#### Class `ShellbagsCleanResult`
Shellbags Clean Result data container.


#### Class `ShellbagsPrivacyCleaner`
Production Windows Shellbags and JumpLists activity forensics sanitizer.

- **`_count_reg_keys(cls, subkey)`** (Line 64): Count subkeys and values in a registry key.
- **`_delete_reg_tree(cls, subkey)`** (Line 76): Recursively delete a registry key tree.
- **`scan_shell_activity(cls)`** (Line 96): Scan system for all Shellbag and Explorer activity artifacts.
- **`clean_shell_activity(cls, targets)`** (Line 154): Purge selected or all Explorer activity and Shellbag targets.

### Module: `src/cortex_unified/system_tools/sieve_cache.py`
*SIEVE Cache Eviction Algorithm.

Reference:
    "SIEVE is Simpler than LRU: an Efficient Turn-Key Eviction Algorithm for Web Caches"
    Juncheng Yang, Yazhuo Zhang, Yao Yue, Ymir Vigfusson, K.V. Rashmi
    USENIX NSDI 2024 (Community Award Winner).

Characteristics:
    - Superior miss ratio compared to LRU, FIFO, ARC, and 2Q across wide trace distributions.
    - Zero lock contention on cache hits: hits simply flip a single `visited` bit without moving nodes.
    - O(1) amortized insertion, eviction, and lookup.*

#### Class `SieveNode`
Internal doubly-linked list node for SIEVE cache.

- **`__init__(self, key, value)`** (Line 27): Initialize Sieve Node.

#### Class `SieveCache`
Production thread-safe implementation of the NSDI 2024 SIEVE Cache Algorithm.

- **`__init__(self, capacity)`** (Line 45): Initialize Sieve Cache.
- **`get(self, key, default)`** (Line 61): Lookup key in cache. On hit, flips `visited = True` without linked-list mutation.
- **`contains(self, key)`** (Line 72): Check if key exists in cache without mutating hit counters or visited bit.
- **`put(self, key, value)`** (Line 77): Insert or update a key-value pair. Evicts using SIEVE algorithm if full.
- **`_insert_head(self, node)`** (Line 93): Insert node at head (most recent insertion point).
- **`_remove_node(self, node)`** (Line 103): Remove node from doubly linked list and advance hand if pointing to it.
- **`_evict(self)`** (Line 121): Run SIEVE eviction loop. Returns (evicted_key, evicted_value) or None.
- **`delete(self, key)`** (Line 136): Explicitly remove a key from cache.
- **`clear(self)`** (Line 145): Purge all entries and reset hand.
- **`size(self)`** (Line 154): Size.
- **`hit_ratio(self)`** (Line 160): Hit ratio.
- **`stats(self)`** (Line 166): Return operational cache statistics.
- **`keys(self)`** (Line 179): Return snapshot of currently cached keys.

### Module: `src/cortex_unified/system_tools/slack_space_analyzer.py`
*Cortex Cleaner — NTFS Disk Cluster & Slack Space Forensics Analyzer.

Analyzes filesystem cluster allocation efficiency and unallocated slack space:
1. Queries drive cluster geometry (sectors per cluster, bytes per sector) via Win32 GetDiskFreeSpaceW.
2. Compares logical file sizes vs physical cluster allocation across directory trees.
3. Calculates total slack space (wasted bytes within allocated clusters).
4. Identifies directories with severe cluster fragmentation and storage waste (e.g. node_modules, caches).
5. Recommends NTFS filesystem compression (compact /c) for high-waste directories to reclaim space.*

#### Class `DirectorySlackStat`
Directory Slack Stat data container.


#### Class `VolumeSlackReport`
Volume Slack Report data container.


#### Class `SlackSpaceAnalyzer`
Production NTFS cluster geometry and slack space forensics analyzer.

- **`get_cluster_size(cls, drive_path)`** (Line 50): Query physical volume cluster allocation size in bytes via Win32 GetDiskFreeSpaceW.
- **`analyze_directory(cls, target_dir, max_depth, progress_cb, cancel_check)`** (Line 78): Scan directory and calculate logical vs physical cluster slack space.

### Module: `src/cortex_unified/system_tools/smb_share_auditor.py`
*Cortex Cleaner — Network Share & SMB Exposure Auditor.

Audits local Windows Server/Workstation SMB shares and network file exposure:
- Discovers all active network shares (WMI Win32_Share / NetShareEnum).
- Identifies hidden administrative shares (C$, ADMIN$, IPC$, print$).
- Audits SMB server security: flags SMBv1 activation (WannaCry / EternalBlue vector).
- Audits SMB signing requirements and identifies overly permissive guest/anonymous access.*

#### Class `SmbShareInfo`
Smb Share Info data container.


#### Class `SmbSecurityReport`
Smb Security Report data container.


#### Class `SmbShareAuditor`
Enterprise Network Share & SMB Security Auditor.

- **`__init__(self)`** (Line 50): Initialize Smb Share Auditor.
- **`audit(self)`** (Line 54): Run comprehensive SMB and network share audit.
- **`_list_shares(self)`** (Line 86): List active shares via PowerShell Get-SmbShare or net share.
- **`_check_smbv1(self)`** (Line 162): Check if SMBv1 protocol is enabled on the server.
- **`_check_smb_signing(self)`** (Line 177): Check if SMB signing is required.

### Module: `src/cortex_unified/system_tools/srum_bam_cleaner.py`
*Windows BAM/DAM & SRUM Forensic Privacy Cleaner.

Inspects and sanitizes deep Windows execution tracking artifacts:
1. BAM (Background Activity Moderator) & DAM (Desktop Activity Moderator):
   Registry persistence tracking exact execution timestamps of every executable run.
   Located under: HKLM\SYSTEM\CurrentControlSet\Services\bam\State\UserSettings\<SID>
2. SRUM (System Resource Usage Monitor):
   ESE database tracking historical per-process network bandwidth, CPU seconds, and energy.
   Located under: C:\Windows\System32\sru\SRUDB.dat*

#### Class `BamExecutionEntry`
Represents an execution record captured by BAM/DAM.

- **`to_dict(self)`** (Line 41): To dict.

#### Class `SrumDatabaseInfo`
Status of the Windows SRUM forensic database.

- **`to_dict(self)`** (Line 62): To dict.

#### Class `SrumBamReport`
Forensic report containing BAM/DAM execution traces and SRUM metrics.

- **`to_dict(self)`** (Line 82): To dict.

#### Class `SrumBamCleaner`
Forensic scanner and cleaner for Windows BAM/DAM and SRUM stores.

- **`_filetime_to_datetime(cls, ft_bytes)`** (Line 99): Convert an 8-byte Windows FILETIME structure to ISO timestamp and UNIX epoch.
- **`query_srum(self)`** (Line 116): Inspect the presence, size, and status of Windows SRUM database.
- **`scan(self)`** (Line 153): Scan BAM, DAM, and SRUM execution traces.
- **`clean_bam_entries(self, entries)`** (Line 204): Sanitize specified or all BAM/DAM registry execution records.

### Module: `src/cortex_unified/system_tools/ssd_trim_optimizer.py`
*Solid-State Drive (SSD) NVMe TRIM & Flash Wear-Leveling Optimizer.

Research Grounding
------------------
* NIST SP 800-88 Rev. 1 Guidelines for Media Sanitization & Flash Storage:
  NAND flash cells cannot overwrite in-place; blocks must be erased before being
  re-programmed. Without TRIM (ATA Data Set Management / SCSI UNMAP / NVMe Deallocate),
  write amplification escalates, degrading sequential write throughput and lifetime endurance.
* Microsoft Windows Storage Management Architecture:
  NTFS and ReFS notify underlying storage controllers of freed cluster LBNs via
  `DisableDeleteNotify`. Manual volume deallocation is executed via the Storage PowerShell
  subsystem (`Optimize-Volume -DriveLetter <X> -ReTrim`) or Win32 IOCTL commands.

This module audits global filesystem TRIM notifications, inspects physical media
types (NVMe SSD, SATA SSD, vs HDD) to prevent invalid commands on magnetic media,
and executes real asynchronous NVMe flash block deallocation.*

#### Class `VolumeTrimStatus`
Storage volume status, media classification, and TRIM capability.

- **`to_dict(self)`** (Line 49): To dict.

#### Class `TrimAuditReport`
Comprehensive inspection report of storage drives and filesystem TRIM readiness.

- **`to_dict(self)`** (Line 70): To dict.

#### Class `TrimExecutionResult`
Outcome of an SSD NVMe block deallocation operation.

- **`to_dict(self)`** (Line 89): To dict.

#### Class `SsdTrimOptimizer`
Production SSD / NVMe TRIM auditing and block deallocation engine.

- **`__init__(self)`** (Line 103): Initialize Ssd Trim Optimizer.
- **`query_global_trim_enabled(self)`** (Line 107): Query NTFS and ReFS DisableDeleteNotify values via fsutil.

Returns (ntfs_trim_enabled, refs_trim_enabled).
When DisableDeleteNotify is 0, TRIM is ENABLED.
- **`audit_volumes(self)`** (Line 143): Inspect all mounted logical drives, detect SSD media types, and evaluate TRIM status.
- **`retrim_volume(self, drive_letter)`** (Line 215): Trigger an immediate, non-destructive flash block deallocation on the target volume.

### Module: `src/cortex_unified/system_tools/startup_impact_analyzer.py`
*Cortex Cleaner — Windows Startup Impact Analyzer & Delayed Launch Sequencer.

Deeply inspects startup applications using Windows Task Manager internal metadata:
1. Decodes Explorer\StartupApproved binary records (tracks user-disabled states & timestamps).
2. Calculates startup impact ratings (High, Medium, Low, None) based on binary footprint and dependencies.
3. Discovers startup applications across Registry Run, RunOnce, Startup Folder, and Task Scheduler.
4. Identifies heavy startup applications suitable for Delayed Launch sequencing.
5. Provides safe non-destructive toggle without deleting entry command definitions.*

#### Class `StartupAppItem`
Startup App Item data container.


#### Class `StartupImpactReport`
Startup Impact Report data container.


#### Class `StartupImpactAnalyzer`
Production Windows Startup Impact analyzer and optimizer.

- **`_extract_exe_path(cls, command)`** (Line 63): _extract_exe_path.
- **`_read_startup_approved_state(cls, hive, approved_key, item_name)`** (Line 78): Decode Windows StartupApproved 12-byte binary blob. Byte 0: 0x02=Enabled, 0x03=Disabled.
- **`_calculate_impact(cls, file_size, exe_name)`** (Line 93): Calculate startup impact based on binary size and application profile.
- **`analyze_startup(cls)`** (Line 112): Enumerate and assess startup impact of all registered startup items.
- **`toggle_item_state(cls, item_name, enable, is_user)`** (Line 170): Toggle startup item enabled/disabled state via StartupApproved registry binary key.

### Module: `src/cortex_unified/system_tools/startup_manager.py`
*Startup item enumeration and disabling across platforms.

Reads autostart locations read-only: registry Run/RunOnce keys, Startup
folders, launchd plists, XDG .desktop files. Disabling is implemented for
Windows only. Every failed location increments ``error_count`` instead of
aborting, so one broken source never hides the others.*

#### Class `StartupManager`
Enumerate autostart entries; disable them on Windows.

- **`__init__(self, config)`** (Line 19): Use *config* or a default Config; the OS decides which backends run.
- **`list_startup_items(self)`** (Line 27): Populate ``startup_items`` from every autostart location for this OS.
- **`_list_windows_startup_items(self)`** (Line 44): Collect registry Run/RunOnce values plus Startup-folder files.
- **`_read_registry_startup_items(self, hive, key_path)`** (Line 86): Append every value under one Run/RunOnce key.
- **`_read_startup_folder_items(self, folder_path)`** (Line 109): Append each file in one Startup folder.
- **`_list_macos_startup_items(self)`** (Line 125): _list_macos_startup_items.
- **`_read_plist_items(self, folder_path)`** (Line 144): Append each launchd plist in one folder (name only, no parsing).
- **`_list_linux_startup_items(self)`** (Line 163): _list_linux_startup_items.
- **`_read_desktop_items(self, folder_path)`** (Line 179): Read startup items from Linux .desktop files.
- **`_registry_backup_path(self)`** (Line 198): JSON sidecar where disabled Run/RunOnce values are preserved.
- **`_load_registry_backup(self)`** (Line 202): _load_registry_backup.
- **`_save_registry_backup(self, backup)`** (Line 214): _save_registry_backup.
- **`enable_startup_item(self, item_name)`** (Line 226): Re-enable a previously disabled startup item.

File-based items are restored from ``~/StartupBackup`` (where
:meth:`_disable_startup_folder_item` moves them). Registry items are
restored from the JSON sidecar written at disable time; without that
record the original value cannot be reconstructed, so this returns
False rather than guessing.

Args:
    item_name: The ``name`` of the startup item.

Returns:
    bool: True if the item was restored successfully.
- **`disable_startup_item(self, name, item_type)`** (Line 311): Disable a specific startup item.

Args:
    name (str): The name of the startup item.
    item_type (str): The type of the item ('registry' or 'file').

Returns:
    bool: True if successful, False otherwise.
- **`_disable_registry_item(self, name)`** (Line 329): Disable a registry-based startup item (values backed up first).
- **`_disable_startup_folder_item(self, name)`** (Line 395): Disable a file-based startup item.
- **`get_stats(self)`** (Line 431): Get statistics about startup items.
- **`filter_by_type(self, item_type)`** (Line 444): Filter startup items by type.

### Module: `src/cortex_unified/system_tools/startup_optimizer.py`
*Startup Optimizer — stagger/delay engine with resource-aware gating.

Research grounding
------------------
* Startup Delayer (r2 Studios) — delay engine launching apps when CPU/disk
  idle, advanced launch options (days, internet, priority, elevation,
  confirmation), profiles, backup/restore, deleted recovery.
* Autoruns (Sysinternals, Mark Russinovich) — most comprehensive autostart
  knowledge: startup folder, Run/RunOnce, services, drivers, Explorer
  extensions, BHOs, Winlogon, AppInit DLLs, image hijacks, boot execute,
  Winlogon notifications, services, Winsock LSPs, codecs.
* CCleaner / Advanced SystemCare — startup impact rating, enable/disable,
  simple 2-click cleanup.
* Sakerplus (2026) evidence-based: 12–28 s boot-to-ready reduction,
  22–42% peak RAM reduction via keystroke-level modelling, staggered
  delays (1–120 s), process-aware scheduling (GUI-heavy vs network-bound),
  resource-threshold gating (CPU<5%, RAM>1.2 GB, disk queue<3), contextual
  persistence (battery +25%, thermal +40%).

Why this matters
------------------
* Windows Startup Apps toggle has no delay granularity, no resource awareness,
  no persistence across Update resets.
* CCleaner/Advanced SystemCare apply blanket disable; 68% failure rate due
  to broken dependencies (Sakerplus 37-config benchmark).
* Stagger prevents CPU saturation, disk queue buildup, UI thread starvation;
  preserves foreground readiness, eliminates "spinning cursor + frozen
  taskbar".

Design — dynamic, no hardcoded app lists
* Autostart enumeration via Windows Registry + WMI + Startup folders +
  Scheduled Tasks (schtasks), dynamically discovered per user/machine.
* Each entry classified via PE header manifest parsing: GUI-heavy
  (has message loop), service-dependent (imports Service Control),
  network-bound (imports WinINet).
* Delay persists in JSON under %LOCALAPPDATA%\Cortex\startup_delays.json,
  adaptively scaled by power/thermal state at boot.
* Resource gating before launch: CPU <5%, free RAM >1.2 GB, disk queue <3.
* Profiles: Work/Games/Minimal, backed up with timestamp.

Usage::

    from cortex_unified.system_tools.startup_optimizer import StartupOptimizer
    opt = StartupOptimizer()
    entries = opt.enumerate()
    opt.set_delay(entries[0].id, delay_seconds=8)
    opt.launch_delayed()  # called at login*

#### Class `AppType`
High-level classification for startup entries used by the UI filter.


#### Class `StartupEntry`
Startup Entry data container.

- **`to_dict(self)`** (Line 95): To dict.

#### Class `StartupOptimizer`
Startup Optimizer.

- **`__init__(self, progress, cancel)`** (Line 252): Initialize Startup Optimizer.
- **`enumerate(self)`** (Line 258): Enumerate.
- **`_load_delays(self)`** (Line 289): _load_delays.
- **`_save_delays(self, delays)`** (Line 301): _save_delays.
- **`set_delay(self, entry_id, delay_seconds, conditions)`** (Line 308): Set delay.
- **`remove_delay(self, entry_id)`** (Line 316): Remove delay.
- **`launch_delayed(self, entries)`** (Line 322): Launch delayed.
- **`_jitter(self)`** (Line 387): _jitter.
- **`backup(self)`** (Line 394): Backup.
- **`restore(self, backup)`** (Line 402): Restore.

### Module: `src/cortex_unified/system_tools/storage_growth_tracker.py`
*Cortex Cleaner — Storage Growth Tracker & Timeline Differ.

Records persistent disk snapshots and visualizes folder tree expansion over time:
- Creates persistent snapshots of folder trees, file sizes, and directory hierarchies.
- Compares any two historical snapshots to calculate net growth deltas (+GB / -GB).
- Pinpoints exactly which directories and applications are consuming new storage.
- Identifies newly added high-footprint files and purged directories.*

#### Class `SnapshotSummary`
Snapshot Summary data container.

- **`formatted_time(self)`** (Line 36): Formatted time.
- **`total_gb(self)`** (Line 41): Total gb.

#### Class `DirectoryDelta`
Directory Delta data container.

- **`growth_mb(self)`** (Line 56): Growth mb.
- **`growth_gb(self)`** (Line 61): Growth gb.

#### Class `StorageGrowthDiffReport`
Storage Growth Diff Report data container.

- **`net_growth_gb(self)`** (Line 79): Net growth gb.

#### Class `StorageGrowthTracker`
Enterprise Storage Growth Tracker & Snapshot Differ.

- **`__init__(self, db_path)`** (Line 87): Initialize Storage Growth Tracker.
- **`_init_db(self)`** (Line 98): Create sqlite schema for snapshot metadata and items.
- **`take_snapshot(self, root_path, label, max_depth)`** (Line 130): Scan directory and capture persistent snapshot.
- **`list_snapshots(self)`** (Line 202): List all captured snapshots.
- **`compare_snapshots(self, base_id, target_id)`** (Line 221): Calculate differential storage growth between two snapshots.

### Module: `src/cortex_unified/system_tools/storage_sense.py`
*Storage Sense - surface and configure Windows' built-in auto-cleanup.

Windows already ships an automatic cleaner ("Storage Sense") that removes temp
files, empties the Recycle Bin on a schedule, and can clean the Downloads
folder. Most users never discover it. Cortex reads its current policy and lets
you turn it on and set the schedule - working *with* Windows instead of
duplicating it.

Everything here lives under the per-user registry key
``HKCU\...\StorageSense\Parameters\StoragePolicy`` (DWORD values), so changes
are per-user and fully reversible. No admin required.*

#### Class `StorageSense`
Read and configure Windows Storage Sense (per-user, reversible).

- **`is_supported()`** (Line 35): Is supported.
- **`get_status(self)`** (Line 41): Get status.
- **`_read_values(self)`** (Line 47): _read_values.
- **`_interpret(v)`** (Line 71): Pure mapping of raw DWORD values -> a friendly status dict.
- **`_write(self, name, value)`** (Line 92): _write.
- **`set_enabled(self, enabled)`** (Line 107): Set enabled.
- **`set_cadence(self, days)`** (Line 116): Set cadence.
- **`set_recycle_bin_days(self, days)`** (Line 124): Set recycle bin days.

### Module: `src/cortex_unified/system_tools/system_cache_rebuilder.py`
*Cortex Cleaner — Windows Font, Icon & Thumbnail Cache Rebuilder.

Purges corrupted Windows icon databases (IconCache.db, iconcache_*.db, thumbcache_*.db),
rebuilds the system Font Cache (FontCache service stop + DAT purge + restart),
and issues shell refresh notifications / explorer restart to repair UI corruption.*

#### Class `CacheRebuildReport`
Cache Rebuild Report data container.


#### Class `SystemCacheRebuilder`
Production Windows system cache recovery and rebuilding toolkit.

- **`rebuild_font_cache(cls)`** (Line 44): Stop FontCache service, delete cached .dat files, and restart service.
- **`rebuild_icon_thumbnail_cache(cls)`** (Line 91): Purge IconCache.db, iconcache_*.db, and thumbcache_*.db files.
- **`notify_shell_refresh(cls)`** (Line 122): Issue Windows Shell change notification to reload icons without killing explorer.
- **`restart_explorer(cls)`** (Line 136): Gracefully terminate and restart Windows Explorer.
- **`execute_full_cache_rebuild(cls, restart_shell)`** (Line 150): Run a full system cache rebuild across fonts, icons, thumbnails, and shell.

### Module: `src/cortex_unified/system_tools/system_info.py`
*System information & diagnostics - lightweight, offline, read-only.

Gathers CPU / RAM / disk / OS / battery facts using ``psutil`` + stdlib
``platform``. Everything is a cheap read; nothing is modified and no network is
touched. Values degrade gracefully to ``None`` when a source is unavailable.*

#### Class `SystemInfo`
Collect a snapshot of system facts and live metrics.

- **`platform_info(self)`** (Line 40): Platform info.
- **`cpu_info(self)`** (Line 53): Cpu info.
- **`memory_info(self)`** (Line 69): Memory info.
- **`disk_info(self)`** (Line 85): Disk info.
- **`battery_info(self)`** (Line 107): Battery info.
- **`boot_time(self)`** (Line 123): Boot time.
- **`snapshot(self)`** (Line 132): Full read-only snapshot for the dashboard/report.

### Module: `src/cortex_unified/system_tools/system_repair.py`
*System file health & repair - orchestrating Windows' own repair tools.

Corrupted system files are a leading cause of crashes, update failures and
mysterious slowness. Microsoft's supported fixes are three built-in tools, and
Cortex simply runs them in the right order with plain-language results and
explicit confirmation - it does not invent its own "repair":

* ``sfc /scannow`` - System File Checker: verifies and repairs protected
  Windows files against a known-good cache.
* ``DISM /Online /Cleanup-Image /CheckHealth|ScanHealth|RestoreHealth`` -
  checks and repairs the component store that SFC relies on.
* ``chkdsk`` - checks the filesystem for errors (read-only scan here; a full
  ``/F`` fix must be scheduled for reboot, which we surface honestly).

These are long-running and (for the repair actions) system-modifying, so the UI
confirms first and runs them on a worker thread. All require Administrator.*

#### Class `RepairResult`
Repair Result data container.

- **`to_dict(self)`** (Line 46): To dict.

#### Class `SystemRepair`
Runs SFC / DISM / CHKDSK and interprets their results honestly.

- **`is_supported()`** (Line 59): Is supported.
- **`is_elevated()`** (Line 64): Is elevated.
- **`run_sfc(self, cancel_event)`** (Line 76): Run sfc.
- **`_parse_sfc(out)`** (Line 84): _parse_sfc.
- **`run_dism(self, action, cancel_event)`** (Line 112): Run dism.
- **`_parse_dism(out, action)`** (Line 125): _parse_dism.
- **`run_chkdsk_scan(self, drive, cancel_event)`** (Line 157): Run chkdsk scan.
- **`_parse_chkdsk(out, letter)`** (Line 169): _parse_chkdsk.
- **`_run(self, args, timeout, cancel_event)`** (Line 191): _run.
- **`_decode(raw)`** (Line 222): _decode.

### Module: `src/cortex_unified/system_tools/task_manager.py`
*Task manager backend - live process + resource monitor with honest totals.

This deliberately reconciles the numbers people find confusing:

* Summing every process's memory never equals "in use", because per-process
  figures are *working sets* only and exclude the kernel, drivers, paged /
  non-paged pool, compressed memory, cached/standby memory and GPU-shared RAM.
* Installed RAM can exceed the RAM the OS can use, because integrated GPUs and
  firmware reserve some ("Hardware reserved").

So alongside the process list we return a breakdown that adds up, and we label
the leftover honestly rather than pretending it doesn't exist.

Everything is read-only except :meth:`end_process`, which asks psutil to
terminate a PID (guarded in the UI by a confirmation dialog).*

#### Class `TaskManager`
Stateful monitor. Reuse ONE instance so CPU deltas are meaningful.

psutil reports a process's CPU as usage *since the previous call* on the
same object, so we cache Process handles by PID between snapshots.

- **`instance(cls)`** (Line 48): Instance.
- **`__init__(self)`** (Line 54): Initialize Task Manager.
- **`snapshot(self, sample_interval)`** (Line 65): Return {'cpu':..., 'memory':..., 'processes':[...]} or {'error':...}.

CPU is measured over a short *blocking* window (``sample_interval``
seconds). Because this runs on a worker thread, blocking is fine, and it
makes every reading reliable instead of depending on how long ago the
previous snapshot happened.
- **`_refresh_handles(self, psutil)`** (Line 106): Return {pid: Process} reusing cached handles; drop dead ones.
- **`end_process(self, pid, force)`** (Line 118): Terminate (or kill) a process by PID. Returns (ok, message).
- **`_collect_processes(self, psutil, cores, handles)`** (Line 141): _collect_processes.
- **`_collect_memory(self, psutil, processes)`** (Line 182): _collect_memory.
- **`_installed_ram(self, psutil)`** (Line 216): Physically-installed RAM (may exceed OS-usable due to reservations).

Cached after the first successful read so we don't shell out on every
refresh. Returns None if it can't be determined.

### Module: `src/cortex_unified/system_tools/telemetry_blocker.py`
*Telemetry Blocker — comprehensive Windows privacy hardening via Registry.

Covers 15+ telemetry vectors including:
  - Data Collection / Diagnostics
  - Advertising ID
  - Cortana / Search
  - Location Tracking
  - App Launch Tracking
  - Feedback & Tips
  - Wi-Fi Sense
  - Cloud Content / Suggested Apps
  - Activity History
  - Handwriting data sharing
  - Clipboard sync*

#### Class `TelemetryBlocker`
Disables OS telemetry and diagnostic tracking via Windows Registry.

- **`__init__(self)`** (Line 54): Initialize Telemetry Blocker.
- **`rules(self)`** (Line 60): Rules.
- **`_build_rules()`** (Line 65): Define all telemetry registry rules.
- **`_backup_key(self, rule)`** (Line 229): _backup_key.
- **`_save_backup(self, entries)`** (Line 248): _save_backup.
- **`backup_telemetry(self)`** (Line 259): Backup telemetry.
- **`restore_from_backup(self, backup_path)`** (Line 284): Restore from backup.
- **`check_status(self)`** (Line 336): Return {label: is_blocked} for every rule.
- **`block_telemetry(self)`** (Line 360): Apply all rules. Returns True if ALL succeeded.
- **`restore_defaults(self)`** (Line 400): Remove all custom telemetry registry values (restore OS defaults).

### Module: `src/cortex_unified/system_tools/temp_folder_cleaner.py`
*Cortex Cleaner — Windows Temp Folder Deep Scanner & Auto-Cleaner.

Advanced temp file cleanup beyond what Storage Sense handles:
1. Scans all system, user, and application temp directories.
2. Detects stale temp files (configurable age threshold in hours).
3. Identifies locked files and skips them gracefully.
4. Provides per-directory breakdown of recoverable space.
5. Cleans Windows Installer orphaned patches ($PatchCache$).*

#### Class `TempLocation`
Temp Location data container.


#### Class `TempScanReport`
Temp Scan Report data container.


#### Class `TempCleanResult`
Temp Clean Result data container.


#### Class `TempFolderCleaner`
Production Windows temp directory deep scanner and auto-cleaner.

- **`_get_temp_locations(cls)`** (Line 57): Discover all known temp directories on the system.
- **`scan(cls, stale_hours)`** (Line 94): Scan all temp locations and categorize files by age.
- **`clean(cls, stale_hours, locations_filter, progress_cb)`** (Line 139): Delete stale temp files across all discovered temp locations.

### Module: `src/cortex_unified/system_tools/update_checker.py`
*Release update checker - informational only.

Queries the project's GitHub releases API over HTTPS and reports whether a
newer tagged release exists. It NEVER downloads or installs anything: the
result is surfaced to the user (status bar / tray), who then updates through
the signed installer. This keeps the security surface minimal until a
verified auto-update channel (tufup / WinSparkle) is adopted - see
installer/README.md.*

### Module: `src/cortex_unified/system_tools/vhdx_manager.py`
*Virtual disk (VHDX) reclaim for WSL2, Docker Desktop and Hyper-V.

Dynamically expanding ``.vhdx`` files grow on demand and never shrink on their
own, so data deleted inside a guest does not return space to the host until the
disk is compacted - and compacting an attached disk can corrupt it. This module
finds the disks that matter (WSL distributions from the registry, Docker Desktop
data disks, Hyper-V VM disks), measures host size sparse-aware, refuses to
compact while the owning runtime is running (naming which processes to close),
and compacts via a diskpart attach-read-only/compact/detach sequence, reporting
the measured before/after delta rather than an estimate. Windows-only and
read-only until explicitly asked to act; every subprocess call is time-boxed
with a hidden window.*

#### Class `DiskKind`
Which runtime owns a virtual disk (drives the shutdown advice).


#### Class `VirtualDisk`
One discovered ``.vhdx`` plus what we honestly know about it.

- **`potential_saving_bytes(self)`** (Line 70): Best-case reclaim, or ``None`` when it cannot be known yet.

Compaction can only release space the guest is no longer using, so the
honest upper bound is ``host size - bytes used inside``. Without a guest
measurement there is no defensible number, and the UI says "unknown"
instead of showing a fabricated one.
- **`can_compact(self)`** (Line 83): True when compaction can be attempted right now.
- **`status_note(self)`** (Line 88): Plain explanation of the current state, always safe to display.
- **`to_dict(self)`** (Line 100): To dict.

#### Class `CompactResult`
Outcome of one compaction, measured rather than estimated.

- **`freed_bytes(self)`** (Line 130): Actual bytes returned to the host (never negative).
- **`to_dict(self)`** (Line 134): To dict.

#### Class `VhdxManager`
Discover and compact WSL / Docker / Hyper-V virtual disks.

- **`__init__(self)`** (Line 150): Initialize Vhdx Manager.
- **`is_supported()`** (Line 155): Virtual-disk compaction is a Windows-only concern.
- **`list_disks(self)`** (Line 161): Return every virtual disk we can account for, largest first.
- **`_wsl_disks(self)`** (Line 184): Read WSL distributions straight from the registry (no wsl.exe start).

Shelling out to ``wsl --list`` can spin up the WSL service, which then
holds the very file we want to compact. The registry has everything we
need and touching it starts nothing.
- **`_docker_disks(self)`** (Line 233): Find Docker Desktop data disks outside the WSL registry entries.
- **`_hyperv_disks(self)`** (Line 255): List Hyper-V VM disks, but only when the role is actually installed.
- **`_measure(self, disk)`** (Line 277): Fill in host sizes, using the engine's sparse-aware measurement.
- **`measure_guest_usage(self, disk, timeout)`** (Line 294): Return bytes used inside a WSL distribution, or ``None``.

This **starts the distribution** to run ``df``, which is why it is a
separate, explicit call rather than part of discovery: the caller has to
opt in, and must shut WSL down again before compacting.
- **`shutdown_wsl(self, timeout)`** (Line 322): Run ``wsl --shutdown`` so the virtual disks can be detached.

This stops every WSL distribution *and* Docker Desktop's WSL backend, so
callers must confirm with the user first - unsaved work inside a distro
is lost exactly as it would be with a hard stop.
- **`compact(self, disk, timeout, cancel_event)`** (Line 343): Compact one virtual disk and report the measured space returned.

Uses ``diskpart``: select the vdisk, attach it **read-only** (so the
guest filesystem cannot be modified), compact, then detach. Refuses when
the owning runtime still holds the file, because a partial compaction of
an attached disk is how these files get corrupted.
- **`set_sparse(self, disk, enabled, timeout)`** (Line 418): Ask WSL to keep a distribution's disk sparse (WSL 2.3+ only).

A sparse VHDX returns free blocks to the host automatically, which
prevents the bloat from coming back. Older WSL builds don't support the
flag; that is reported plainly rather than treated as an error.
- **`_explain_failure(out)`** (Line 451): Translate diskpart's output into something actionable.
- **`_run_diskpart(self, script, timeout, cancel_event)`** (Line 467): Run a diskpart script from a temp file; return (looks_ok, output).

Compaction can run for many minutes, so this polls ``timeout`` and
``cancel_event`` instead of blocking uninterruptibly (see
``core/proc.py``). A kill always lands on the ``diskpart`` process tree,
never on the calling thread, so it is always safe even if the caller is
abandoned mid-operation during app shutdown.
- **`_run_ps(self, script, timeout)`** (Line 509): Run a PowerShell snippet with a hidden window; None on any failure.
- **`_running_processes()`** (Line 523): Lower-cased names of running processes (empty set if unavailable).
- **`_decode(raw)`** (Line 540): _decode.
- **`_reg_str(key, name)`** (Line 556): _reg_str.
- **`_reg_int(key, name)`** (Line 568): _reg_int.

### Module: `src/cortex_unified/system_tools/vss_health_analyzer.py`
*Volume Shadow Copy (VSS) Writer Health, Shadow Storage & State Recovery Engine.

Research Grounding
------------------
* Microsoft Volume Shadow Copy Service (VSS) Architecture (Windows Server & Windows 10/11):
  VSS coordinates volume block snapshots between Requestors (backup software), Writers
  (applications like Registry, Hyper-V, MSSearch, and System Writer), and Providers.
* Interrupted Snapshot Deadlocks:
  When an update, crash, or backup fails midway, VSS writers often freeze in
  `[5] Waiting for completion` or `[8] Failed` states. In this state, Windows cannot
  create new restore points, system backups fail, and orphaned differential area
  storage accumulates in `System Volume Information`.
* Storage Allocations (`vssadmin list shadowstorage`):
  NTFS shadow copies use a dynamic Copy-on-Write diff area. Auditing allocated vs
  maximum shadow storage bounds ensures unconstrained growth is detected before disk starvation.

This module parses `vssadmin list writers` and `vssadmin list shadowstorage`,
flags stalled or failed writers, and provides automated 1-click state reset.*

#### Class `VssWriterStatus`
Status, state code, and error condition of an NT VSS Writer.

- **`to_dict(self)`** (Line 48): To dict.

#### Class `VssStorageAllocation`
Volume shadow copy storage allocation and limit metrics.

- **`to_dict(self)`** (Line 69): To dict.

#### Class `VssHealthReport`
Comprehensive health and storage report of the Windows VSS subsystem.

- **`to_dict(self)`** (Line 90): To dict.

#### Class `VssResetResult`
Outcome of a VSS service and writer state reset operation.

- **`to_dict(self)`** (Line 109): To dict.

#### Class `VssHealthAnalyzer`
Production Volume Shadow Copy diagnostics and state recovery engine.

- **`__init__(self)`** (Line 121): Initialize Vss Health Analyzer.
- **`inspect_health(self)`** (Line 125): Query vssadmin for active writers and volume shadow storage bounds.
- **`_parse_writers(self, text)`** (Line 170): _parse_writers.
- **`_build_writer_status(self, d)`** (Line 202): _build_writer_status.
- **`_parse_shadowstorage(self, text)`** (Line 227): _parse_shadowstorage.
- **`_build_storage_allocation(self, d)`** (Line 258): _build_storage_allocation.
- **`reset_vss_writers(self)`** (Line 280): Reset stalled VSS writers by cycling dependent Windows services.

### Module: `src/cortex_unified/system_tools/vss_manager.py`
*Cortex Cleaner — Volume Shadow Copy (VSS) & Snapshot Manager.

Provides programmatic inspection and maintenance of Windows Volume Shadow Copies:
- Discovers existing VSS snapshots, creation timestamps, and space consumption.
- Audits VSS shadow storage allocations (Used, Allocated, Maximum).
- Prunes stale or excessive shadow copies to reclaim gigabytes of disk space.
- Creates on-demand recovery snapshots before performing destructive cleanup operations.*

#### Class `ShadowCopyInfo`
Shadow Copy Info data container.


#### Class `ShadowStorageInfo`
Shadow Storage Info data container.

- **`used_gb(self)`** (Line 45): Used gb.
- **`allocated_gb(self)`** (Line 50): Allocated gb.
- **`max_gb(self)`** (Line 55): Max gb.

#### Class `VssAuditReport`
Vss Audit Report data container.


#### Class `VssManager`
Enterprise Volume Shadow Copy (VSS) Manager.

- **`__init__(self)`** (Line 73): Initialize Vss Manager.
- **`audit(self)`** (Line 77): Audit all shadow copies and storage allocations across volumes.
- **`list_shadows(self)`** (Line 95): List all active shadow copies via vssadmin.
- **`list_shadow_storage(self)`** (Line 162): List shadow copy storage space allocations.
- **`create_shadow_copy(self, volume)`** (Line 243): Create an on-demand volume shadow copy.
- **`delete_oldest_shadow(self, volume)`** (Line 269): Delete the oldest shadow copy on a given volume to reclaim space.

### Module: `src/cortex_unified/system_tools/vulnerability_catalog.py`
*Versioned, local-only advisory catalog with exact product/version matching.*

#### Class `CatalogError`
Catalog Error error.


#### Class `VersionConstraint`
Version Constraint data container.

- **`to_dict(self)`** (Line 28): To dict.

#### Class `Advisory`
Advisory data container.

- **`to_dict(self)`** (Line 45): To dict.
- **`to_finding(self, device_ip, evidence)`** (Line 58): To finding.

#### Class `VulnerabilityCatalog`
Immutable catalog loaded explicitly from a bounded local JSON file.

- **`__init__(self, advisories, catalog_version)`** (Line 179): Initialize Vulnerability Catalog.
- **`to_dict(self)`** (Line 190): To dict.
- **`load(cls, path)`** (Line 198): Load.
- **`match(self, product, version)`** (Line 223): Match normalized product equality plus an explicit parseable version.
- **`correlate(self, product, version, evidence)`** (Line 234): Compatibility helper that emits findings only with observation evidence.

### Module: `src/cortex_unified/system_tools/wake_on_lan.py`
*Strict, scope-bound Wake-on-LAN packet construction and transmission.*

#### Class `WakeOnLanError`
Base exception for Wake-on-LAN failures.


#### Class `InvalidMacAddress`
Raised when a MAC is malformed or unsafe for a unicast device.


#### Class `InvalidBroadcastAddress`
Raised when a broadcast is outside supplied active LAN scopes.


#### Class `WakeOnLanSendError`
Raised when the bounded UDP send fails.


### Module: `src/cortex_unified/system_tools/wan_audit.py`
*Read-only, local-only WAN and UPnP IGD audit.

The auditor never contacts an Internet service and never invokes a mutating
UPnP action.  Every HTTP target must be an IPv4 literal inside one of the
machine's active private interface networks, preventing DNS rebinding and
SSRF through malicious SSDP replies.*

#### Class `InterfaceStatus`
A local IPv4 interface used to establish the audit trust boundary.

- **`to_dict(self)`** (Line 50): To dict.

#### Class `PortMapping`
One port mapping returned by ``GetGenericPortMappingEntry``.

- **`to_dict(self)`** (Line 69): To dict.

#### Class `WanStatus`
JSON-safe outcome of a WAN audit.

- **`public_ip_classification(self)`** (Line 83): Compatibility classification used by the earlier WAN UI.
- **`to_dict(self)`** (Line 101): To dict.

#### Class `WanAuditor`
Perform a synchronous, cancellable, read-only local WAN audit.

- **`__init__(self, timeout, max_response_bytes, max_mappings)`** (Line 241): Initialize Wan Auditor.
- **`audit(self, gateway_ips, include_upnp, progress, cancel_event)`** (Line 254): Audit.
- **`_cancelled(cancel_event)`** (Line 332): _cancelled.
- **`_progress(progress, message)`** (Line 339): _progress.
- **`local_interfaces()`** (Line 347): Return private IPv4 addresses using only standard-library lookups.

Netmasks are not exposed portably by the standard library, so inferred
/24 networks are used only as a narrow trust boundary for optional
local IGD reads. Explicit gateway scopes are added separately.
- **`discover_locations(self, networks, cancel_event)`** (Line 380): Issue bounded SSDP searches; return trusted LOCATION URLs.
- **`_load_igd(self, location, networks)`** (Line 418): _load_igd.
- **`_read_soap_status(self, status, service_type, control_url, networks, cancel_event, progress)`** (Line 453): _read_soap_status.
- **`_soap(self, url, service_type, action, arguments)`** (Line 509): _soap.
- **`_mapping_from_xml(index, root)`** (Line 557): _mapping_from_xml.
- **`_http_request(self, method, url, body, headers)`** (Line 581): Perform one no-redirect request with a hard response-size cap.
- **`default_gateway()`** (Line 634): Read the local default IPv4 route without network traffic.
- **`dns_servers()`** (Line 665): Read locally configured DNS server addresses.

#### Class `_NoMoreMappings`
Internal sentinel for the normal end of mapping enumeration.


### Module: `src/cortex_unified/system_tools/winapp2_cleaner.py`
*Declarative Community & Third-Party Application Cleaner (Winapp2.ini Engine).

Parses and executes declarative application cleaning rules supporting thousands of
Windows desktop applications, tools, browsers, and developer environments.
Provides variable path expansion, registry-based software detection, and strict safety
boundaries to prevent accidental removal of operating system or critical user data.*

#### Class `Winapp2Rule`
Represents a single parsed Winapp2 application cleaning rule.


#### Class `AppCleanTarget`
Target item identified for removal.


#### Class `Winapp2Report`
Scan and cleanup report from the Winapp2 engine.

- **`to_dict(self)`** (Line 174): To dict.

#### Class `Winapp2Cleaner`
High-throughput declarative cleaner engine for Windows applications.

- **`__init__(self, custom_ini_content)`** (Line 210): Initialize Winapp2 Cleaner.
- **`expand_vars(cls, path_str)`** (Line 216): Dynamically expand Windows environment variables and handle variations.
- **`_load_rules(self, ini_content)`** (Line 243): Parse winapp2.ini declarative syntax into rule definitions.
- **`_is_app_installed(self, rule)`** (Line 285): Determine if target application exists via filesystem or registry.
- **`is_safe_path(self, path)`** (Line 318): Enforce strict safety boundary check preventing deletion of OS/system roots.
- **`scan(self, progress_cb, cancel_event)`** (Line 335): Scan candidate application targets matching detected software rules.
- **`clean(self, targets, dry_run, progress_cb)`** (Line 425): Execute safe removal of identified cache targets. Returns (cleaned_bytes, cleaned_items).

### Module: `src/cortex_unified/system_tools/windows_update.py`
*Windows Update status - what's pending and when you last updated.

Two honest layers:

* Offline & instant - the dates of your last successful update *check* and
  *install*, read from the registry. This needs no network and tells you at a
  glance whether Windows has been keeping itself current.
* On demand & online - a search for pending updates via the official Windows
  Update COM API (``Microsoft.Update.Session``). This reaches Microsoft's update
  service (so it needs internet and can take a while), which the UI states
  plainly. Cortex only *reports* pending updates - installing them is left to
  Windows Update itself, which handles reboots and rollback safely.*

#### Class `PendingUpdate`
Pending Update data container.

- **`to_dict(self)`** (Line 43): To dict.

#### Class `WindowsUpdate`
Read Windows Update state (read-only).

- **`is_supported()`** (Line 53): Is supported.
- **`last_activity(self)`** (Line 59): Last activity.
- **`_read_result_time(sub)`** (Line 69): _read_result_time.
- **`check_pending(self)`** (Line 86): Check pending.
- **`_parse_pending(out)`** (Line 100): _parse_pending.
- **`recent_history(self, limit)`** (Line 139): Recent history.
- **`_parse_history(out)`** (Line 154): _parse_history.
- **`_run(self, script, timeout)`** (Line 185): _run.

### Module: `src/cortex_unified/system_tools/windows_update_repair.py`
*Windows Update Repair Toolkit — comprehensive component reset and repair.

Research grounding
------------------
* Microsoft Learn: "How do I reset Windows Update components?" — official
  procedure: stop services (wuauserv, bits, cryptsvc, appidsvc), rename
  SoftwareDistribution/catroot2, re-register 30+ DLLs, reset Winsock,
  restart services.
* WURepair (SysAdminDoc, 2026) — PowerShell module with 14 phases:
  hosts file cleanup (25+ Microsoft domains), SSL/TLS repair, firewall
  rules, Winsock/TCP reset, proxy cleanup, BITS repair, Delivery
  Optimization, service dependencies, registry policy cleanup,
  SoftwareDistribution/catroot2 reset, DLL re-registration, DISM
  integration (with `/AnalyzeComponentStore`, `/ResetBase` gated by
  reclaimable >= 1024 MB), SFC, servicing stack preflight, catalog SSU
  repair, selective repair phases, JSON reports, event log integration.
* thatKinji/Reset-WindowsUpdateTools — single cmdlet `Reset-WindowsUpdate`.
* matbanik/rwu — 14-step fix with TUI, AI-ready diagnostics, dry-run,
  reversible (timestamped cache folders, registry exports).
* limehawk/rmm-scripts — PowerShell script with security descriptor
  reset, DLL re-registration, Winsock reset, optional reboot.
* ManuelGil/Script-Reset-Windows-Update-Tool — 10.5.x versions, 500K+
  downloads, includes SFC, DISM, cleanup superseded.

Why this matters for Cortex Cleaner
-----------------------------------
* Windows Update breaks frequently (0x80070643, 0x80070002, 0x800f081f,
  stuck at 0%/33%/100%). Built-in troubleshooter is shallow.
* Privacy tools, malware, system corruption, misconfiguration disable
  services, block domains, break SSL/TLS, corrupt catroot2.
* A production-grade repair must be *selective* (phase-based), *reversible*
  (backups, restore points), *diagnostic* (pre-check report), and
  *automatable* (JSON output, exit codes, event log).

Design
------
* **Phase-based architecture**: each repair phase is a method with
  `dry_run` support, returns `PhaseResult` (success, changes, rollback
  info). Phases: Diagnose, Services, Caches, Registry, DLLs, Network,
  DISM, SFC, SSU, DeliveryOpt, WaaS, Verify.
* **Safety**: System Restore point before any mutation; timestamped
  rename of SoftwareDistribution/catroot2 (not delete); registry exports
  before policy changes; IFEO debugger removal on rollback.
* **Diagnostics**: `preflight()` returns `DiagnosticReport` (services,
  disk, connectivity, DISM health, pending reboot, recent errors).
* **Selective repair**: `repair(phases=[...])` runs only requested phases.
* **Automation**: JSON report with before/after comparison; event log
  entry; exit codes (0=success, 1=partial, 2=failed, 3=cancelled).
* **24H2 awareness**: DeliveryOptimization path change; WaaSMedicSvc
  aggressive restart — stop it first.

Usage::

    from cortex_unified.system_tools.windows_update_repair import WindowsUpdateRepair
    repair = WindowsUpdateRepair()
    report = repair.preflight()
    if report.issues:
        result = repair.repair_all()
        print(result.summary())

References
----------
* Microsoft Learn: How to Reset Windows Update Components
* WURepair (GitHub: SysAdminDoc/WURepair)
* Reset-WindowsUpdateTools (GitHub: thatKinji/Reset-WindowsUpdateTools)
* rwu (GitHub: matbanik/rwu)
* Microsoft Learn: Additional resources for Windows Update*

#### Class `PhaseResult`
Phase Result data container.


#### Class `DiagnosticReport`
Diagnostic Report data container.

- **`to_json(self)`** (Line 118): To json.

#### Class `RepairResult`
Repair Result data container.

- **`summary(self)`** (Line 133): Summary.

#### Class `WindowsUpdateRepair`
Comprehensive Windows Update component repair.

- **`__init__(self, create_restore_point, progress_callback, cancel_event, dry_run)`** (Line 188): Initialize Windows Update Repair.
- **`_run(self, cmd, timeout, shell)`** (Line 211): _run.
- **`_run_ps(self, script, timeout)`** (Line 231): _run_ps.
- **`_sc_query(self, name)`** (Line 237): _sc_query.
- **`_service_status(self, name)`** (Line 244): _service_status.
- **`_stop_service(self, name, retries)`** (Line 254): _stop_service.
- **`_start_service(self, name)`** (Line 267): _start_service.
- **`preflight(self)`** (Line 276): Run diagnostic pre-checks.
- **`_phase_stop_services(self)`** (Line 354): _phase_stop_services.
- **`_phase_clear_caches(self)`** (Line 370): _phase_clear_caches.
- **`_phase_reset_registry_policies(self)`** (Line 410): _phase_reset_registry_policies.
- **`_phase_reset_security_descriptors(self)`** (Line 437): _phase_reset_security_descriptors.
- **`_phase_reregister_dlls(self)`** (Line 452): _phase_reregister_dlls.
- **`_phase_reset_network(self)`** (Line 467): _phase_reset_network.
- **`_phase_dism_repair(self)`** (Line 493): _phase_dism_repair.
- **`_phase_sfc(self)`** (Line 508): _phase_sfc.
- **`_phase_component_store(self)`** (Line 517): Analyze and optionally cleanup component store.
- **`_phase_start_services(self)`** (Line 528): _phase_start_services.
- **`_phase_verify(self)`** (Line 544): _phase_verify.
- **`repair_all(self, phases)`** (Line 564): Run all repair phases (or specified subset).
- **`repair_selective(self, phase_names)`** (Line 606): Run only specified phases.
- **`quick_reset(self)`** (Line 610): Minimal reset: services, caches, DLLs, network, restart.

### Module: `src/cortex_unified/system_tools/wsl_cleaner.py`
*WSL distro cleanup: size reporting, shutdown + vhdx compaction.

The 1.37GB AppData\Local\wsl hit from manual cleaning was a WSL2
ext4.vhdx that never shrinks on its own. This module offers:

* list_distros() - parse ``wsl --list --verbose`` + registry fallback
* get_sizes() - ext4.vhdx sizes via VhdxManager (sparse-aware)
* shutdown() - ``wsl --shutdown`` (stops all distros + Docker WSL backend)
* compact(vhdx) - diskpart compact via VhdxManager
* export_size(distro) - estimate export cost via ``wsl --export`` dry probe

Windows-only; all methods degrade gracefully on other platforms.*

#### Class `WslDistro`
One WSL distribution with its vhdx estimate.

- **`to_dict(self)`** (Line 42): To dict.

#### Class `WslCleaner`
Discover and clean WSL distro disks (Windows-only).

- **`is_supported()`** (Line 88): Is supported.
- **`is_wsl_available(self)`** (Line 92): Is wsl available.
- **`list_distros(self)`** (Line 111): Enumerate distros via ``wsl --list --verbose`` + vhdx size probe.
- **`shutdown(self, timeout)`** (Line 204): Run ``wsl --shutdown`` so vhdx files can be detached for compaction.
- **`compact_vhdx(self, vhdx_path, timeout, cancel_event)`** (Line 220): Compact a single vhdx via VhdxManager.diskpart path (read-only attach).
- **`get_total_vhdx_size(self)`** (Line 245): Total (logical, on-disk) bytes across all distro vhdx files.
- **`_reg_str(key, name)`** (Line 251): _reg_str.
- **`_reg_int(key, name)`** (Line 263): _reg_int.

### Module: `src/cortex_unified/ui/tabs/system_tools_tab.py`
*Tab for system tools tab in Cortex Cleaner GUI.*

#### Class `SystemToolsTab`
Container Tab mapping System Tools sub-tabs dynamically.

- **`__init__(self, config, logger, safety_manager)`** (Line 21): Initialize the container tab via the base class.
- **`setup_ui(self)`** (Line 25): Create the system tools tab natively injecting components.

Fills an inner QTabWidget with StartupManagerTab, ProcessAnalyzerTab,
and (if importable) RegistryCleanerTab as sub-tabs.

---

## 4. Analyzers & Duplicate Detection Engines

### Module: `src/cortex_unified/analyzers/advanced_disk_analyzer.py`
#### Class `FileEntry`
Single file system entry from scanner.


#### Class `FolderNode`
Aggregated folder node for visualization.

- **`add_file(self, rel_path, size, ext)`** (Line 130): Add one file's size to this node and every intermediate folder node.
- **`to_treemap(self, max_depth)`** (Line 147): Convert tree to flat list of hierarchy dictionaries for treemaps.
- **`to_sunburst(self, max_depth)`** (Line 165): Convert tree to sunburst parent-child dictionary list.
- **`to_bar_chart(self, top_n)`** (Line 182): Convert tree to top largest folders bar chart format.
- **`top_extensions(self, limit)`** (Line 196): Return top N file extensions by space consumed.

#### Class `Scanner`
Read-only filesystem scanner yielding FileEntry objects with cancellation and progress.

- **`__init__(self, cancel_event, progress_cb)`** (Line 207): Store the cancellation event and progress callback with zeroed counters.
- **`scan(self, root)`** (Line 217): Yield every FileEntry under root; implemented by each platform backend.
- **`_check_cancel(self)`** (Line 222): True once the caller has signalled the cancel event.
- **`_report(self, path)`** (Line 226): Count the file and invoke progress_cb every 100th entry.

#### Class `NTFSScanner`
NTFS scanner that probes raw volume access but scans via scandir walk.

- **`__init__(self)`** (Line 242): Initialize and probe whether raw MFT/volume access is available.
- **`_check_mft_access(self)`** (Line 247): Test raw volume handle access via CreateFileW; needs Administrator.
- **`scan(self, root)`** (Line 262): Yield entries via scandir walk (MFT fast path not yet implemented).
- **`_scan_mft(self, root)`** (Line 269): MFT fast path; currently delegates to the scandir walk.
- **`_scan_walk(self, root)`** (Line 273): Iterative scandir walk skipping symlinks and unreadable directories.

#### Class `PosixScanner`
Linux/macOS scanner using iterative scandir with stat metadata.

- **`scan(self, root)`** (Line 314): Yield entries under root via an iterative scandir walk.

#### Class `CloudScanner`
Cloud target scanner delegating to rclone ``lsf`` per configured remote.

- **`__init__(self)`** (Line 356): Store provider list and verify the rclone binary is usable.
- **`_check_rclone(self)`** (Line 362): Run ``rclone version`` to confirm the binary works; no admin needed.
- **`scan(self, root)`** (Line 370): Scan each configured ``provider:`` remote, or a single ``root`` remote.
- **`_scan_remote(self, remote)`** (Line 378): List a remote's files via ``rclone lsf`` and convert each line to FileEntry.

#### Class `AdvancedDiskAnalyzer`
Disk usage analyzer that scans (local or cloud) and builds FolderNode trees for charts.

- **`__init__(self, include_cloud, cloud_providers, cancel_event, progress_cb)`** (Line 424): Store cancellation/progress hooks and pick the platform or cloud scanner.
- **`_create_scanner(self, include_cloud, providers)`** (Line 437): Choose NTFS/Posix scanner by platform, or CloudScanner when cloud deps exist.
- **`scan(self, root)`** (Line 453): Async wrapper that streams entries from the underlying sync scanner.
- **`build_tree(self, entries)`** (Line 464): Fold all file entries into an aggregated FolderNode hierarchy.
- **`get_visualizations(self)`** (Line 476): Return treemap/sunburst/bar data plus extension and size totals from the last tree.
- **`get_stats(self)`** (Line 491): Return files and bytes counted by the scanner so far.

### Module: `src/cortex_unified/analyzers/advanced_shredder.py`
#### Class `ShredMethod`
Sanitization standards for secure data erasure.


#### Class `AdvancedShredder`
Overwrites files with certified pass patterns before deletion.

- **`__init__(self)`** (Line 54): __init__.
- **`_generate_pass_data(self, pattern, size)`** (Line 60): Generate byte pattern for a single chunk.
- **`shred_file(self, file_path, passes, method)`** (Line 67): Overwrite *file_path* with the chosen sanitization pattern, then remove it.

The file is renamed to a random name just before unlinking: on NTFS
the MFT entry outlives deletion, and a scrambled name prevents
trivial filename-based recovery tools from re-linking the data.
- **`shred_directory(self, dir_path, passes, method)`** (Line 148): Recursively shreds a directory and its contents.

### Module: `src/cortex_unified/analyzers/advanced_uninstaller.py`
#### Class `AppInfo`
Unified application representation.

- **`to_dict(self)`** (Line 106): to_dict.

#### Class `LeftoverScanResult`
LeftoverScanResult.

- **`to_dict(self)`** (Line 127): to_dict.

#### Class `UninstallResult`
UninstallResult.


#### Class `AdvancedUninstaller`
Multi-source uninstaller with leftover detection and forced uninstall.

- **`__init__(self, create_restore_point, progress_callback, cancel_event)`** (Line 598): __init__.
- **`enumerate_all(self, force_refresh)`** (Line 613): Enumerate apps from all sources.
- **`uninstall_batch(self, app_ids, force, scan_leftovers)`** (Line 651): Uninstall multiple apps with single restore point.
- **`_uninstall_one(self, app, force, scan_leftovers)`** (Line 685): Uninstall one app. Returns (success, leftovers, duration, error).
- **`_split_command(cmd)`** (Line 724): Split an uninstall string into argv, honouring quoted exes.

Windows uninstall strings mix quoted paths, bare paths and switch
arguments; this parser keeps the quoted exe as one token.
- **`_run_uninstaller(self, cmd, app)`** (Line 747): Execute one uninstall command and report real success.

MSI entries look like ``MsiExec.exe /X{GUID}`` (no .msi path); the
product code is passed to msiexec with quiet flags. Everything else
runs as a direct argv list — no shell, no string interpolation of
registry data.
- **`_forced_uninstall(self, app)`** (Line 803): Forced uninstall: remove the app's traces after killing it.

Destructive by design, so every step is guarded: the install
directory must not be a drive root, system directory, or user
profile; registry removal only touches keys whose *publisher
matches*, not any key whose name happens to contain the app name.
- **`_remove_install_dir(self, app)`** (Line 825): Delete the app's install directory if it is safe to do so.

Refuses (returns False without deleting) when the location is a
drive root, Windows, Program Files, or the user profile — a
malformed InstallLocation must never turn into rmtree on C:\.
An app installed *inside* one of these (the normal case) is fine;
only the protected directory itself is untouchable.
- **`_kill_processes(self, name)`** (Line 873): _kill_processes.
- **`_cleanup_registry_traces(self, app)`** (Line 883): Remove the app's own Uninstall entry and publisher-matched keys.

Substring matching on key names is not used: a "Code" app would
otherwise match every key containing "code". Instead:

* the app's own Uninstall subkey (from its source id) is removed;
* top-level SOFTWARE keys are removed only when the key's
  DisplayName/Publisher actually belongs to this app.
- **`_cleanup_services_tasks(self, name)`** (Line 935): Remove the app's services and scheduled tasks.

Matching is word-boundary on the app name against the service's
registry Display名/binary path and the task's name — not substring
contains, which would delete unrelated services.
- **`_scan_leftovers_deep(self, app)`** (Line 987): Scan the standard per-app locations for surviving data.

Checks the concrete places Windows apps persist state — the
registry Uninstall entry, Program Files, both AppData trees and
LOCALLOW — and reports only paths that still exist.

### Module: `src/cortex_unified/analyzers/audio_duplicate_finder.py`
#### Class `AudioDuplicateFinder`
Find acoustically-similar audio groups (same recording, any encoding).

Args:
    root_path: Directory (or iterable of directories) to scan.
    threshold: Minimum :func:`audio_compare` score (0..1) to group.
        0.75 is a good default (≈ 8 bit errors per 32-bit subfp on average
        across the best alignment). Lower = more permissive.
    config: Exclusion rules / symlink policy.

- **`__init__(self, root_path, threshold, config)`** (Line 517): __init__.
- **`_should_exclude(self, path)`** (Line 544): _should_exclude.
- **`_is_audio(self, path)`** (Line 556): _is_audio.
- **`find_audio_duplicates(self, threads, progress_callback, cancel_event)`** (Line 564): Scan roots and return acoustically-duplicate groups (size >= 2).
- **`get_stats(self)`** (Line 704): get_stats.

### Module: `src/cortex_unified/analyzers/broken_link_detector.py`
#### Class `BrokenLink`
Base class for broken link information.


#### Class `BrokenSymlink`
Information about a broken symlink.


#### Class `BrokenShortcut`
Information about a broken Windows shortcut (.lnk file).


#### Class `BrokenRegistryRef`
Information about a broken registry reference (Windows only).


#### Class `RepairResult`
Result of a repair attempt.


#### Class `RepairOutcome`
Per-item outcome of a :func:`repair` run.


#### Class `BrokenLinkDetector`
Detector for broken symlinks, shortcuts, and registry references.

- **`__init__(self, config)`** (Line 215): Initialize broken link detector.
- **`_setup_windows_modules(self)`** (Line 239): Set up Windows-specific modules for shortcut and registry handling.
- **`_should_exclude_path(self, path)`** (Line 261): Check if a path should be excluded based on patterns.
- **`_get_file_stats(self, path)`** (Line 281): Get file size and timestamps.
- **`scan_symlinks(self, path)`** (Line 292): Scan for broken symlinks in the given path.
- **`scan_windows_shortcuts(self, path)`** (Line 369): Scan for broken Windows shortcuts (.lnk files).
- **`_analyze_shortcut(self, lnk_path)`** (Line 433): Analyze a Windows shortcut file to extract target information.
- **`_analyze_shortcut_basic(self, lnk_path)`** (Line 475): Basic shortcut analysis without COM (limited functionality).
- **`scan_registry_references(self)`** (Line 506): Scan for broken registry references (Windows only).
- **`_scan_registry_key(self, hkey, subkey_path)`** (Line 532): Scan a specific registry key for broken file references.
- **`_extract_paths_from_string(self, text)`** (Line 577): Extract potential file paths from a string.
- **`_assess_symlink_repairability(self, broken_link)`** (Line 612): True when a plausible new target for the symlink exists.

A moved-but-present target means repair is just a retarget; with no
candidates there is nothing sane to point the link at.
- **`_assess_shortcut_repairability(self, broken_shortcut)`** (Line 621): True when a plausible new target for the shortcut exists.
- **`_assess_registry_repairability(self, broken_ref)`** (Line 626): Assess if a broken registry reference can potentially be repaired.
- **`_calculate_confidence_score(self, broken_link)`** (Line 632): Calculate confidence score for a broken link detection.
- **`find_moved_targets(self, original_target)`** (Line 658): Find potential new locations for a moved target using heuristics.
- **`_get_search_locations(self, original_path)`** (Line 695): Get prioritized list of locations to search for moved files.
- **`attempt_repair(self, broken_link)`** (Line 750): attempt_repair.
- **`_create_backup(self, original_path)`** (Line 794): Create a backup of the original link before repair.
- **`_repair_symlink(self, broken_link, new_target, backup_result)`** (Line 820): Repair a broken symlink.
- **`_repair_shortcut(self, broken_shortcut, new_target, backup_result)`** (Line 844): Repair a broken Windows shortcut.
- **`_repair_registry_ref(self, broken_ref, new_target, backup_result)`** (Line 899): Repair a broken registry reference (not implemented for safety).
- **`categorize_broken_links(self, links)`** (Line 910): Categorize broken links by type and repairability.
- **`scan_all(self, path, progress, cancel_event, include_registry)`** (Line 945): Scan for broken symlinks and shortcuts under the given folder.

Args:
    path: Root directory to scan.
    progress: Optional callable(str) invoked with live status text.
    cancel_event: Optional threading.Event; if set, the scan stops early.
    include_registry: Off by default. Registry references are NOT tied
        to the chosen folder, and the path-extraction heuristic can
        mis-parse registry values that contain spaces, producing false
        positives (e.g. truncating ``D:\Program Files\App`` to
        ``D:\Program``). We therefore exclude them from a folder scan
        unless explicitly requested. Startup Run-key auditing lives in
        the dedicated Startup page instead.
- **`_cancelled(self)`** (Line 988): _cancelled.
- **`_emit(self, text)`** (Line 995): _emit.
- **`get_scan_statistics(self)`** (Line 1006): Get statistics about the last scan.

### Module: `src/cortex_unified/analyzers/cache_cleaner.py`
#### Class `CacheCleaner`
Finds cache/log files and directories under the platform's cache roots.

- **`__init__(self, config)`** (Line 20): Args:
    config: Exclusion rules; defaults to ``Config()``.
- **`_get_platform_cache_paths(self)`** (Line 124): Cache roots for this platform, deduplicated, existing ones only.
- **`get_custom_scan_roots(self)`** (Line 162): Suggest user-selected roots for deeper sweeps.

Returns existing directories that are safe to offer as shortcuts in the UI
without forcing a full fixed-drive walk.
- **`is_archive(self, path)`** (Line 195): True when *path* is a keep-as-backup archive (.zip/.tar.gz).
- **`_should_exclude_path(self, path)`** (Line 202): True when *path* hits an excluded directory name or pattern.
- **`_is_cache_directory(self, path)`** (Line 214): True when the directory name contains a known cache marker.
- **`_is_cache_file(self, path)`** (Line 222): True when the file name matches a cache/log/build-artifact glob.
- **`find_large_logs(self, roots, min_size_mb, exclude_archives, progress_callback, cancel_event)`** (Line 232): Find large log/text files across user-selected roots (D:\code sweeper).

Args:
    roots: Directories to walk (e.g. ["D:\code"]).
    min_size_mb: Minimum size to report (manual hits were 7.6GB of >100MB logs).
    exclude_archives: When True, skip .zip/.tar.gz (they are backups, not logs).
    progress_callback: Optional fn(msg, count, bytes).
    cancel_event: Optional threading.Event to abort early.

Returns:
    List of (path, size) sorted largest-first.
- **`find_cache_files(self, custom_paths)`** (Line 312): Find cache and log files.

Args:
    custom_paths: Optional list of custom paths to scan instead of default cache paths

Returns:
    Tuple of (files, directories) that are cache/log related
- **`get_stats(self)`** (Line 380): Get statistics about the cache file finding process.
- **`_format_bytes(self, bytes_count)`** (Line 401): Format bytes into human-readable format.
- **`get_cache_directories(self)`** (Line 409): Get list of cache directories that would be scanned.

### Module: `src/cortex_unified/analyzers/cloud_storage_analyzer.py`
#### Class `CloudFileEntry`
Single cloud object entry.

- **`to_dict(self)`** (Line 90): Serialize this entry to a plain dict, with ``mtime`` as ISO-8601.

#### Class `CloudScanStats`
Aggregate totals for one scan: sizes by class/provider, cost, errors.


#### Class `DuplicateGroup`
Cross-cloud/local duplicate group.

- **`wasted_bytes(self)`** (Line 125): Bytes reclaimable if all but one copy of this group were removed.

#### Class `PricingCatalog`
Storage pricing resolved at runtime from the provider's public API.

Rates are never compiled into the binary: they are fetched from the
vendor's price list endpoint, cached on disk for ``ttl_hours``, and
resolved per (provider, region, storage_class). If the network is
unavailable and no cache exists, ``rate()`` returns ``None`` and the
caller reports "unknown" instead of a fabricated number.

- **`__init__(self, ttl_hours, timeout)`** (Line 157): Set the cache TTL in hours and the network timeout in seconds.
- **`_cache_file(self, provider, region)`** (Line 166): Filesystem path of the cache file for one provider/region pair.
- **`_read_cache(self, provider, region)`** (Line 173): Return cached rates for this pair, or ``None`` when missing, stale, or corrupt.
- **`_write_cache(self, provider, region, rates)`** (Line 189): Persist rates with a fetch timestamp, silently ignoring filesystem errors.
- **`_http_json(self, url)`** (Line 201): GET a URL and parse the JSON response; return ``None`` on any failure.
- **`_fetch_aws(self, region)`** (Line 215): Fetch S3 per-GB-month storage rates from AWS's public Price List Query API.
- **`_fetch_azure(self, region)`** (Line 259): Fetch per-GB-month blob rates from Azure's unauthenticated Retail Prices API.
- **`rates(self, provider, region)`** (Line 289): Return normalized class -> USD/GB/month, from cache or a live vendor fetch.
- **`rate(self, provider, region, storage_class)`** (Line 306): Resolve one storage class to a USD/GB/month rate, or ``None`` if unknown.

#### Class `CloudProvider`
Abstract cloud storage provider.

- **`__init__(self, config)`** (Line 347): Store config and derive the lowercase provider name from the class name.
- **`list_objects(self, bucket, prefix, max_keys)`** (Line 355): Stream every object under a bucket/prefix as :class:`CloudFileEntry` items.
- **`region(self)`** (Line 367): Region used for pricing lookups, resolved from config or environment.
- **`estimate_cost(self, stats)`** (Line 377): Monthly USD estimate from live vendor rates for this provider only.

Storage classes with no resolvable rate are skipped and recorded in
``stats.unpriced_classes`` so the UI can label them "unknown" rather
than silently pricing them at a guessed value.
- **`validate_config(self)`** (Line 395): Hook for providers to reject bad config; base accepts everything.

#### Class `S3Provider`
AWS S3 backend driven by boto3, listing object versions when available.

- **`__init__(self, config)`** (Line 410): Initialize and create the boto3 S3 client from config/environment.
- **`_init_client(self)`** (Line 419): Build the boto3 client, letting boto3 fall back to env/IAM/SSO credentials.
- **`region(self)`** (Line 448): The bucket-resolved region if known, else the inherited default.
- **`_bucket_region(self, bucket)`** (Line 455): Query GetBucketLocation for the bucket's region; ``None`` on failure.
- **`list_objects(self, bucket, prefix, max_keys)`** (Line 473): Stream S3 objects, preferring versioned listing to surface billable old versions.
- **`estimate_cost(self, stats)`** (Line 526): Estimate monthly USD via base live rates for S3 classes scanned.

#### Class `AzureBlobProvider`
Azure Blob backend via BlobServiceClient (connection string or token auth).

- **`__init__(self, config)`** (Line 542): Initialize and create the BlobServiceClient from config/environment.
- **`_init_client(self)`** (Line 551): Build the BlobServiceClient from a connection string, account URL, or DefaultAzureCredential.
- **`region(self)`** (Line 577): Resolved ARM region for pricing, from config or the account information.
- **`list_objects(self, container, prefix, max_keys)`** (Line 598): Stream container blobs with metadata, tags, and versions where enabled.
- **`estimate_cost(self, stats)`** (Line 641): Delegate to the base class cost estimate using Azure live rates.

#### Class `GoogleDriveProvider`
Google Drive listing via the Drive v3 REST API.

The access token is taken from config or ``GOOGLE_OAUTH_ACCESS_TOKEN``;
Drive storage is bundled with the Workspace/One plan, so no per-GB rate
exists and ``estimate_cost`` correctly reports ``0.0``.

- **`__init__(self, config)`** (Line 664): Store config and resolve the Drive OAuth access token.
- **`_get(self, params)`** (Line 673): Issue an authorized Drive v3 GET; return parsed JSON or ``None``.
- **`list_objects(self, bucket, prefix, max_keys)`** (Line 690): Stream non-trashed Drive files in a folder, skipping size-less native docs.

#### Class `OneDriveProvider`
OneDrive / SharePoint listing via Microsoft Graph ``/children``.

Token comes from config or ``MSGRAPH_ACCESS_TOKEN``. Storage is part of
the M365 subscription, so there is no per-GB storage rate to apply.

- **`__init__(self, config)`** (Line 763): Store config and resolve the Microsoft Graph access token.
- **`_get(self, url)`** (Line 772): Issue an authorized Graph GET; return parsed JSON or ``None``.
- **`list_objects(self, bucket, prefix, max_keys)`** (Line 788): Stream non-folder drive items via Graph ``/children`` pages.

#### Class `RcloneProvider`
Any of rclone's 40+ backends via ``rclone lsjson``.

``lsjson`` is used instead of ``lsf`` because it emits well-formed JSON
(no delimiter ambiguity in names) including per-object hashes. The rclone
binary is located dynamically via ``PATH`` or ``RCLONE_BINARY``.

- **`__init__(self, config)`** (Line 850): Store config, remote name, and locate the rclone binary.
- **`_locate_binary(explicit)`** (Line 859): Find rclone via explicit hint, ``RCLONE_BINARY``, or ``PATH``.
- **`available(self)`** (Line 873): Whether a usable rclone binary was found.
- **`list_remotes(self)`** (Line 879): Configured rclone remotes, so callers never guess a remote name.
- **`list_objects(self, bucket, prefix, max_keys)`** (Line 892): Run ``rclone lsjson`` recursively and stream each file as an entry.
- **`estimate_cost(self, stats)`** (Line 944): Return 0.0: pricing belongs to the backend's native provider class.

#### Class `CloudStorageAnalyzer`
Unified cloud storage analyzer with multi-provider support.

- **`__init__(self, default_provider, provider_configs, cancel_event, progress_cb)`** (Line 967): Set up cancellation, progress callbacks, and instantiate all providers.
- **`_init_providers(self, default)`** (Line 983): Instantiate every provider (skipping ones that fail) and pick the default.
- **`get_provider(self, name)`** (Line 996): Return the instantiated provider by name, or ``None``.
- **`available_targets(self)`** (Line 1002): Enumerate what this machine can actually scan.

Returns ``{provider: [target, ...]}`` built from live sources — S3
``list_buckets``, Azure ``list_containers``, configured rclone remotes,
and Graph/Drive roots when a token is present. Nothing is assumed.
- **`scan(self, target, max_objects)`** (Line 1037): Scan cloud target. target format: 's3://bucket/prefix' or 'rclone://remote/path'.
- **`scan_sync(self, target, max_objects, progress_cb, cancel_event)`** (Line 1074): Synchronous scan returning all entries and stats.
- **`find_duplicates(self, entries, local_hashes)`** (Line 1117): Group objects that share a content hash, optionally including local files.

``local_hashes`` maps ``hash -> [local path, ...]`` (e.g. from
``DuplicateFinder``), letting a single group span cloud and disk.
Multipart S3 ETags are excluded because they hash the part list,
not the object body, so they cannot prove equality.
- **`generate_report(self, entries, stats, duplicates)`** (Line 1157): Self-contained HTML report with a per-class cost breakdown.

Classes without a live vendor rate are shown as ``unknown`` instead of
being priced with a guess. Object counts are computed from ``entries``
so the table reflects what was actually scanned.

### Module: `src/cortex_unified/analyzers/content_defined_chunker.py`
#### Class `Chunk`
Chunk.

- **`to_dict(self)`** (Line 108): to_dict.

#### Class `ChunkStats`
ChunkStats.


#### Class `ContentDefinedChunker`
Find shift-resistant near-duplicate files via CDC chunk sets.

Complements ``FuzzyDuplicateFinder`` (CTPH, 0..100) with a
Jaccard-over-chunks score that is robust to insertions/deletions at
arbitrary offsets (the classic CDC advantage).

Args:
    root_path: Directory (or iterable) to scan.
    threshold: Minimum Jaccard (0..1) to group (default 0.5).
    avg_size: Target chunk size (default 8 KiB).
    config: Exclusion rules / symlink policy.

- **`__init__(self, root_path, threshold, avg_size, min_size, max_size, config)`** (Line 246): __init__.
- **`_should_exclude(self, path)`** (Line 280): _should_exclude.
- **`find_cdc_duplicates(self, threads, progress_callback, cancel_event)`** (Line 292): find_cdc_duplicates.
- **`get_stats(self)`** (Line 425): get_stats.

#### Class `IdeaInvertedIndex`
IDEA: Inverted Deduplication-Aware Index (FAST '24).
Maps chunk fingerprints directly to file postings, enabling O(1) similarity matching
without all-pairs O(N^2) Jaccard scanning.

- **`__init__(self)`** (Line 500): __init__.
- **`insert(self, path, chunks)`** (Line 507): insert.
- **`find_similar(self, path, threshold)`** (Line 516): Find files sharing chunks with `path` exceeding Jaccard `threshold`.

### Module: `src/cortex_unified/analyzers/czkawka_tools.py`
#### Class `EmptyResult`
Empty scan result with empty files, folders, and scan stats.


#### Class `EmptyFinder`
Walk a root tree collecting zero-byte files and empty folders.

- **`__init__(self, root, config)`** (Line 144): __init__.
- **`find(self, cancel, progress)`** (Line 152): Collect empty files then empty folders under the root.

#### Class `SymlinkResult`
Broken-symlink scan result with link targets and scan stats.


#### Class `InvalidSymlinkFinder`
Walk a root tree collecting symlinks whose targets no longer exist.

- **`__init__(self, root, config)`** (Line 202): __init__.
- **`find(self, cancel, progress)`** (Line 210): Collect symlinks whose resolved targets are missing.

#### Class `BrokenFileFinder`
Detect corrupt images, archives, and PDFs via content verification.

- **`__init__(self, root, config)`** (Line 241): __init__.
- **`_is_broken(self, p)`** (Line 249): _is_broken.
- **`find(self, threads, cancel, progress)`** (Line 282): Check every file under the root returning paths that fail verification.

#### Class `BadExtResult`
One file whose sniffed content type disagrees with its extension.


#### Class `BadExtensionFinder`
Compare each file's magic-byte type against its claimed extension.

- **`__init__(self, root, config)`** (Line 327): __init__.
- **`find(self, cancel, progress)`** (Line 335): Return files whose sniffed extension differs from the file suffix.

#### Class `BadNamesFinder`
Collect files and folders with illegal, reserved, or overlong names.

- **`__init__(self, root, config)`** (Line 373): __init__.
- **`find(self, cancel)`** (Line 381): Return paths whose names match control-char or reserved patterns.

#### Class `ExifCleaner`
Scan images for EXIF metadata and strip it to protect privacy.

- **`__init__(self, root, config)`** (Line 399): __init__.
- **`scan(self, cancel)`** (Line 406): List JPEG/TIFF/WebP files that still carry EXIF metadata.
- **`strip(self, paths)`** (Line 435): Remove EXIF metadata from the given images reporting per-file success.

#### Class `TempFileFinder`
Locate temp/log/backup files under a root or system temp dirs.

- **`__init__(self, root, config)`** (Line 467): __init__.
- **`find(self, cancel)`** (Line 474): find.

#### Class `VideoInfo`
VideoInfo.


#### Class `VideoOptimizer`
VideoOptimizer.

- **`find_static_borders(self, video)`** (Line 519): find_static_borders.
- **`optimize(self, video, out, crf, preset)`** (Line 547): Re-encode with libx264, crop static borders if detected.

### Module: `src/cortex_unified/analyzers/deep_cleaner.py`
#### Class `DeepCleaner`
Finds temp files, caches, and orphaned app data across platforms.

- **`__init__(self, config)`** (Line 42): Args:
    config: Retained for interface parity; defaults are applied when
        omitted.
- **`_find_orphaned_app_data(self)`** (Line 51): Find app data folders for apps that are no longer installed.

Detection is per-platform negative evidence: a folder is orphaned
when no matching binary/desktop entry (Linux), no ``*.app`` bundle
(macOS), or no uninstall registry entry (Windows) references it.
Conservative filters drop known system folders and tiny metadata
directories to keep the false-positive rate near zero.
- **`_get_scan_targets(self)`** (Line 165): Declarative scan table for the current platform.

Maps a display label to its paths, match pattern, category and
flags. ``recursive`` walks the whole subtree; ``is_orphan`` marks
the special target whose paths are produced by
:meth:`_find_orphaned_app_data` instead of the filesystem.
- **`find_junk(self, progress_callback)`** (Line 217): Run every platform target and return one record per finding.

Records carry ``category``, ``description``, ``path``, ``size`` and
an ``is_orphan`` marker so callers can apply stricter confirmation
before deleting orphaned app data.
- **`get_stats(self)`** (Line 273): get_stats.
- **`_format_bytes(self, bytes_count)`** (Line 284): _format_bytes.

### Module: `src/cortex_unified/analyzers/disk_analyzer.py`
#### Class `DiskAnalyzer`
Analyzes disk usage and directory composition under a root.

- **`__init__(self, config, root_path)`** (Line 20): Args:
    config: Exclusion rules; defaults to ``Config()``.
    root_path: Directory (or drive) to analyze.
- **`_should_exclude_path(self, path)`** (Line 38): True when *path* hits an excluded directory name or pattern.
- **`analyze_disk_usage(self)`** (Line 50): Volume-level totals for the root path's drive.

Uses ``shutil.disk_usage`` on Windows; POSIX gets ``os.statvfs``
with ``f_bavail`` so the free figure reflects unprivileged space
(reserved blocks excluded).
- **`analyze_directory_tree(self, max_depth)`** (Line 87): Build a bounded-depth tree with sizes rolled up to each parent.

Args:
    max_depth: Maximum depth to analyze (to prevent excessive recursion)
- **`_analyze_directory_recursive(self, path, max_depth, current_depth)`** (Line 98): Build one tree node; child sizes roll up into their parent.

Returns ``{}`` past the depth limit, for excluded paths, or when
the directory cannot be read -- callers treat that as a pruned
branch rather than an error.
- **`analyze_file_types(self)`** (Line 150): Analyze files by type/extension.
- **`find_largest_directories(self, limit)`** (Line 203): Return the *limit* biggest directories by direct file content.

Sizes are per-directory (files directly inside), not recursive
rollups -- cheap to compute during a single walk and enough for a
top-N list.
- **`get_stats(self)`** (Line 244): Get comprehensive statistics about the disk analysis.
- **`_format_bytes(self, bytes_count)`** (Line 279): Format bytes into human-readable format.
- **`export_to_json(self, filepath)`** (Line 287): Export analysis results to JSON file.

### Module: `src/cortex_unified/analyzers/docker_cleaner.py`
#### Class `DockerImage`
An image flagged as dangling or referenced by no container.


#### Class `DockerContainer`
A non-running container eligible for removal.


#### Class `DockerVolume`
A volume not mounted by any container.


#### Class `DockerNetwork`
A user-defined network with no attached containers.


#### Class `CleanupResult`
Outcome of a cleanup pass; counts include dry-run simulations.

- **`total_removed(self)`** (Line 97): total_removed.

#### Class `DockerCleaner`
Finds and removes reclaimable Docker resources via the Docker SDK.

The daemon connection is created lazily, so instantiating this class
never touches Docker. Per-resource failures are logged and collected
rather than raised.

- **`__init__(self, config)`** (Line 111): Initialize state; the Docker client itself connects lazily.

Args:
    config: Optional application configuration.
- **`client(self)`** (Line 130): Return a connected ``docker.DockerClient``, creating it on first use.

Raises:
    ImportError: If the ``docker`` package is not installed.
- **`is_docker_available(self)`** (Line 150): Check if Docker is available and running.
- **`scan_unused_images(self)`** (Line 167): Collect images that are dangling or referenced by no container.
- **`scan_stopped_containers(self)`** (Line 221): Collect containers that are not currently running.
- **`scan_unused_volumes(self)`** (Line 262): Collect volumes not mounted by any container.
- **`scan_unused_networks(self)`** (Line 302): Collect user-defined networks with no attached containers.
- **`cleanup_resources(self, resources, dry_run)`** (Line 342): Remove the given resources, or simulate removal when dry_run.

Counters and ``space_freed`` are updated regardless of dry_run, so a
simulated pass reports what a real one would free.

Args:
    resources: Mixed list of scan results to remove.
    dry_run: When True, no destructive API calls are made.

Returns:
    Per-type removal counts, bytes freed, and error strings.
- **`get_filesystem_cache_size(self)`** (Line 408): Fallback: measure Docker Desktop's on-disk cache under AppData\Local\Docker.

The 8.6GB manual hit at ``AppData\Local\Docker`` is not visible via the
SDK (docker system prune); this probes the filesystem directly for the
Storage Sense file-based docker_desktop_cache category.
- **`get_space_usage(self)`** (Line 445): Get Docker space usage information (SDK + filesystem fallback).
- **`get_stats(self)`** (Line 471): Return a snapshot copy of cumulative scan counters.
- **`_is_image_unused(self, image_id)`** (Line 475): True if no container references the image; False on API errors (fail-safe).
- **`_is_volume_orphaned(self, volume_name)`** (Line 486): True if no container mounts the volume; False on API errors (fail-safe).
- **`_is_network_unused(self, network_id)`** (Line 499): True if the network reports zero attached containers; False on errors.
- **`_get_container_size(self, container)`** (Line 508): Approximate container size in bytes.

Uses stats ``storage_stats`` when the daemon exposes it; otherwise
falls back to the image size, which overstates usage because shared
layers are counted per container.
- **`_get_volume_size(self, volume)`** (Line 524): Approximate volume size in bytes.

Prefers daemon-reported ``UsageData``; otherwise walks the
mountpoint, which only works for local-storage volumes on this host.
- **`_format_bytes(self, bytes_size)`** (Line 551): Render a byte count using the largest fitting binary unit.

### Module: `src/cortex_unified/analyzers/duplicate_finder.py`
#### Class `DuplicateFinder`
Finds duplicate files via size grouping followed by content hashing.

- **`__init__(self, config, root_path)`** (Line 100): Args:
    config: Exclusion rules; defaults to ``Config()``.
    root_path: Directory tree to search.
- **`_should_exclude_path(self, path)`** (Line 125): True when *path* hits an excluded directory name or pattern.
- **`_get_file_hash(self, filepath)`** (Line 137): Content hash of *filepath*, or None when unreadable.

Small files are hashed fully. Files over ~1 MB sample three 64 KiB
regions (start/middle/end) plus the exact size -- enough to separate
real-world duplicates at a fraction of the I/O cost of a full read.
- **`_get_file_size(self, filepath)`** (Line 191): Size in bytes, or -1 when the file cannot be stat'ed.
- **`_find_files_by_size(self)`** (Line 198): Group files by exact size; only sizes shared by 2+ files survive.

Unique-size files cannot have duplicates, so dropping them here makes
the expensive hashing pass proportional to actual duplication.
- **`find_duplicates(self, threads)`** (Line 240): Return ``{hash: [paths]}`` for groups of 2+ identical files.
- **`get_stats(self)`** (Line 274): Get statistics about the duplicate finding process.
- **`_calculate_potential_savings(self)`** (Line 287): Calculate potential bytes that could be saved by removing duplicates.
- **`auto_select_duplicates(self, strategy)`** (Line 300): Pick the redundant copies from each duplicate group.

Args:
    strategy: Which copy to keep -- "keep_newest", "keep_oldest",
        "keep_largest", or "keep_smallest". Everything else in the
        group is returned for deletion.
- **`_format_bytes(self, size)`** (Line 332): Format bytes to human-readable string.
- **`get_hash_algorithm_info(self)`** (Line 340): Get information about the current hash algorithm.
- **`_fastcdc_chunks(self, data, min_size, avg_size, max_size)`** (Line 353): Content-defined chunking via FastCDC (Gear rolling hash).

Uses a Gear table (256 random 64-bit) and mask = avg_size-1 normalized.
This yields variable-size chunks that realign after insertions (unlike
fixed chunking), giving +15% dedup ratio per Hybrid paper Table.
- **`_fsb_hash(self, chunk)`** (Line 408): Lightweight FSB-like hash (syndrome-based).

Real FSB uses parity-check matrix H * chunk^T over GF(2). We approximate
with xxhash64 (fast, 10×) plus blake2b secondary to keep collision <1e-18,
matching paper's lightweight claim.
- **`find_duplicates_chunked(self, min_chunk, avg_chunk, max_chunk, threads, progress_callback, cancel_event)`** (Line 419): Chunk-level deduplication via FastCDC + FSB hybrid.

Returns:
    {chunk_hash: [(Path, offset, length), ...]} for chunks appearing
    in ≥2 files. Higher granularity catches shifted duplicates that
    file-level hashing misses (+15% ratio per paper).

Unlike ``find_duplicates`` which hashes whole files, this splits each
file into content-defined chunks and dedups chunks, reporting
reclaimable chunk bytes.
- **`get_chunked_stats(self, dup_chunks)`** (Line 509): Stats for chunked dedup.

### Module: `src/cortex_unified/analyzers/duplicate_folder_finder.py`
#### Class `DuplicateFolderFinder`
Finds folders whose contents are byte-for-byte identical.

- **`__init__(self, config, root_path)`** (Line 22): Args:
    config: Exclusion rules applied inside each folder hash.
    root_path: Directory tree to search.
- **`_should_exclude_path(self, path)`** (Line 42): True when *path* hits an excluded directory name or pattern.
- **`_get_folder_hash(self, folderpath)`** (Line 54): Order-independent content fingerprint of *folderpath*.

Combines each file's relative path with its content hash. Sorting
the pairs before folding them in makes the result independent of
filesystem enumeration order, so identical trees hash identically.
Unreadable files are skipped -- they weaken the fingerprint but
must not crash the scan.
- **`find_duplicate_folders(self, threads, progress, cancel_event)`** (Line 104): Find folders with identical content.

Args:
    threads: Number of threads to use (0 = auto)
    progress: Optional callable(str) invoked with live status text.
    cancel_event: Optional threading.Event; if set, the scan stops early.
- **`get_stats(self)`** (Line 193): Get statistics about the duplicate folder finding process.
- **`auto_select_folders(self, strategy)`** (Line 205): Pick the redundant folder from each duplicate group.

Args:
    strategy: Which copy to keep -- "keep_first", "keep_last",
        "keep_shortest_path", or "keep_longest_path". All other
        members are returned for deletion.

### Module: `src/cortex_unified/analyzers/file_shredder.py`
#### Class `FileShredder`
Securely deletes files by overwriting contents before unlinking.

- **`__init__(self, config)`** (Line 21): Args:
    config: Unused today beyond interface parity with other analyzers;
        defaults are applied when omitted.
- **`_generate_random_data(self, size)`** (Line 34): _generate_random_data.
- **`_generate_pattern_data(self, size, pattern)`** (Line 40): _generate_pattern_data.
- **`shred_file(self, filepath, passes, allow_system_files)`** (Line 46): Overwrite *filepath* in place, then unlink it.

Args:
    filepath: Path to the file to shred
    passes: Number of overwrite passes (defaults to self.passes)
    allow_system_files: Whether to allow shredding system files
    
Returns:
    True if successful, False otherwise (reason recorded in ``errors``)
- **`shred_files(self, filepaths, passes)`** (Line 122): Securely delete multiple files.

Args:
    filepaths: List of file paths to shred
    passes: Number of overwrite passes (defaults to self.passes)
    
Returns:
    Dictionary with statistics
- **`get_stats(self)`** (Line 150): Get statistics about the shredding process.
- **`set_passes(self, passes)`** (Line 158): Set the number of overwrite passes.
- **`verify_deletion(self, verify)`** (Line 164): Set whether to verify file deletion.

### Module: `src/cortex_unified/analyzers/fuzzy_finder.py`
#### Class `FuzzyDuplicateFinder`
Find near-identical *binary/content* files via CTPH similarity.

Args:
    root_path: Directory (or iterable) to scan.
    threshold: Minimum similarity score (0..100) to group two files.
        Default 60 (matches ssdeep's "highly similar" range).
    block_size: Base CTPH block size (default 64).
    config: Exclusion rules / symlink policy.

- **`__init__(self, root_path, threshold, block_size, config)`** (Line 285): __init__.
- **`_should_exclude(self, path)`** (Line 312): _should_exclude.
- **`_eligible(self, path)`** (Line 324): _eligible.
- **`find_fuzzy_duplicates(self, threads, progress_callback, cancel_event)`** (Line 332): Return groups (size >= 2) of files whose fuzzy similarity reaches the
threshold.
- **`get_stats(self)`** (Line 451): get_stats.

### Module: `src/cortex_unified/analyzers/large_file_finder.py`
#### Class `LargeFileFinder`
Finds files larger than a size threshold under a root directory.

- **`__init__(self, config, root_path)`** (Line 34): Args:
    config: Exclusion rules; defaults to ``Config()``.
    root_path: Directory tree to search.
- **`_should_exclude_path(self, path)`** (Line 56): True when *path* hits an excluded directory name or pattern.
- **`_get_file_size(self, filepath)`** (Line 68): Size in bytes, or -1 when the file cannot be stat'ed.
- **`find_large_files(self, min_size_mb, threads)`** (Line 75): Find files larger than the specified size threshold.

Args:
    min_size_mb: Minimum file size in MB (defaults to self.min_size_mb)
    threads: Accepted for interface parity; os.walk is single-threaded.
- **`get_stats(self)`** (Line 133): Get statistics about the large file finding process.
- **`_format_bytes(self, bytes_count)`** (Line 149): Format bytes into human-readable format.
- **`filter_by_size(self, min_size_mb, max_size_mb)`** (Line 157): Filter large files by size range.

Args:
    min_size_mb: Minimum file size in MB
    max_size_mb: Maximum file size in MB (optional)
- **`group_by_extension(self)`** (Line 173): Group large files by file extension.
- **`group_by_ai_models(self)`** (Line 185): Split large files into ``ai_models`` vs ``other`` for UI surfacing.

Returns:
    Dict with keys ``ai_models`` and ``other``; ai_models holds
    (*.gguf, *.safetensors, ...) entries tagged HIGH-risk, disabled by default.
- **`get_ai_models(self, min_size_mb)`** (Line 200): Return only AI model files among large files (for HIGH-risk UI).
- **`tag_file(self, path)`** (Line 205): Return a display tag for a large file (ai_models, video, archive, etc.).

### Module: `src/cortex_unified/analyzers/leftover_detector.py`
#### Class `DetectedItem`
Base class for detected leftover items.

- **`to_dict(self)`** (Line 35): to_dict.

#### Class `OrphanedFolder`
Represents an orphaned application folder.


#### Class `InstallerFile`
Represents a detected installer file.


#### Class `RegistryOrphan`
Represents an orphaned registry entry (Windows only).


#### Class `CleanupRecommendation`
Represents a cleanup recommendation with risk assessment.


#### Class `LeftoverDetector`
Advanced heuristics and leftover detection system.

- **`__init__(self, config)`** (Line 94): __init__.
- **`_setup_installation_paths(self)`** (Line 123): Set up common installation paths for different platforms.
- **`_load_detection_patterns(self)`** (Line 161): Load ML patterns and heuristics for leftover detection.
- **`scan_orphaned_folders(self, paths)`** (Line 221): Scan for orphaned application folders in common installation paths.
- **`_scan_directory_for_orphans(self, directory)`** (Line 246): Scan a specific directory for orphaned folders.
- **`_is_system_directory(self, path)`** (Line 276): Check if a directory is a system directory that should be skipped.
- **`_analyze_folder_for_orphan_signs(self, folder)`** (Line 286): Analyze a folder for signs that it might be an orphan.
- **`_folder_appears_abandoned(self, folder)`** (Line 322): Check if a folder appears to be abandoned.
- **`_contains_uninstaller_remnants(self, folder)`** (Line 343): Check if folder contains uninstaller remnants.
- **`_create_orphaned_folder_object(self, folder, confidence)`** (Line 355): Create an OrphanedFolder object from analysis results.
- **`_determine_installation_path_type(self, folder)`** (Line 392): Determine the type of installation path.
- **`_contains_executables(self, folder)`** (Line 409): Check if folder contains executable files.
- **`_contains_config_files(self, folder)`** (Line 420): Check if folder contains configuration files.
- **`_contains_data_files(self, folder)`** (Line 435): Check if folder contains data files.
- **`_calculate_folder_size(self, folder)`** (Line 446): Calculate total size of folder in bytes.
- **`_extract_app_name(self, folder_name)`** (Line 460): Extract application name from folder name.
- **`detect_installer_files(self, paths)`** (Line 468): detect_installer_files.
- **`_scan_for_installer_files(self, directory, installer_extensions)`** (Line 515): Scan directory for installer files.
- **`_analyze_installer_file(self, file_path)`** (Line 538): Analyze a potential installer file.
- **`_check_installer_duplicate(self, file_path)`** (Line 574): Check if installer file is a duplicate (simplified implementation).
- **`_extract_version_from_filename(self, filename)`** (Line 587): Extract version number from filename.
- **`_calculate_installer_confidence(self, file_path, size_bytes)`** (Line 604): Calculate confidence score for installer file detection.
- **`analyze_registry_orphans(self)`** (Line 622): Analyze Windows registry for orphaned entries.
- **`_analyze_registry_key(self, hive, hive_name, key_path)`** (Line 647): Analyze a specific registry key for orphaned entries.
- **`_check_registry_subkey_for_orphans(self, hive, hive_name, full_key_path, subkey_name)`** (Line 669): Check a registry subkey for orphaned file references.
- **`_create_registry_orphan(self, registry_key, hive, referenced_path, key_type)`** (Line 696): Create a RegistryOrphan object.
- **`apply_ml_patterns(self, items)`** (Line 720): Apply machine learning patterns to improve detection accuracy.
- **`_apply_pattern_adjustments(self, item)`** (Line 767): Apply pattern-based adjustments to confidence score.
- **`calculate_confidence_score(self, item)`** (Line 793): Calculate overall confidence score for a detected item.
- **`generate_cleanup_recommendations(self, confidence_threshold)`** (Line 797): Generate cleanup recommendations based on detected items.
- **`export_results(self, filepath)`** (Line 849): Export detection results to JSON file.
- **`get_stats(self)`** (Line 871): Get detection statistics.

### Module: `src/cortex_unified/analyzers/near_duplicate_finder.py`
#### Class `BloomFilter`
Simple Bloom filter with k hash functions.

m = -n ln p / (ln 2)^2 , k = (m/n) ln2  – standard sizing.
We fix k=7 (SemHash Stage 1) and size m ≈ 10× expected n for p<0.01.

- **`__init__(self, n, p, k)`** (Line 79): __init__.
- **`_hashes(self, data)`** (Line 91): _hashes.
- **`add(self, data)`** (Line 107): add.
- **`fpr(self)`** (Line 124): Theoretical false-positive rate after n insertions.

#### Class `NearDuplicateFinder`
Near-duplicate finder via MinHash LSH + Bloom pre-screen.

Args:
    root_path: Directory to scan.
    threshold: Jaccard threshold for near-duplicate (≈0.8 = 80% overlap).
    shingle_k: Shingle size (default 5 per Broder).
    hash_perm: Number of MinHash permutations H (default 128).
    bands: LSH bands b (default 16, r=8 => H=128).
    use_bloom: Enable Bloom pre-screen (LSHBloom).
    config: Exclusion rules.

- **`__init__(self, root_path, threshold, shingle_k, hash_perm, bands, use_bloom, config)`** (Line 176): __init__.
- **`_should_exclude(self, path)`** (Line 209): _should_exclude.
- **`_is_text(self, path)`** (Line 221): _is_text.
- **`_minhash(self, shingles)`** (Line 232): MinHash signature length H: min_{shingle} h_perm(shingle).
- **`_lsh_candidates(self, signatures)`** (Line 244): Band-hashing (LSH) to generate candidate pairs without O(n²).

LSHBloom §3: bands hashed to Bloom-like bit vectors; here we use dict
buckets (exact) but same S-curve: P(candidate|J) = 1-(1-J^r)^b
- **`_jaccard(self, a, b)`** (Line 272): _jaccard.
- **`_weighted_jaccard(self, a, b, df, n_docs)`** (Line 282): Attention-weighted Jaccard (SemHash AW-MinHash): down-weight boilerplate.

Boilerplate shingles appearing in >50% docs get weight 0.5, else 1.0.
- **`find_near_duplicates(self, threads, progress_callback, cancel_event)`** (Line 306): Find near-duplicate groups.

Returns:
    {group_id: [Path, ...]} where group_id is representative hash.
    Groups sized 1 are omitted (same as duplicate_finder).
- **`get_stats(self)`** (Line 477): Stats akin to DuplicateFinder.

### Module: `src/cortex_unified/analyzers/old_file_cleaner.py`
#### Class `OldFileCleaner`
Finds files older than an age threshold under a root directory.

- **`__init__(self, config, root_path)`** (Line 17): Args:
    config: Exclusion rules; defaults to ``Config()``.
    root_path: Directory tree to search.
- **`_should_exclude_path(self, path)`** (Line 35): True when *path* hits an excluded directory name or pattern.
- **`find_old_files(self, min_age_days)`** (Line 47): Find files that haven't been modified in the specified number of days (mtime age).

Args:
    min_age_days: Minimum age in days (defaults to self.min_age_days)
- **`get_stats(self)`** (Line 96): Get statistics about the old file finding process.
- **`_format_bytes(self, bytes_count)`** (Line 124): Format bytes into human-readable format.
- **`filter_by_age_range(self, min_days, max_days)`** (Line 132): Filter old files by age range.

Args:
    min_days: Minimum age in days
    max_days: Maximum age in days (optional)
- **`group_by_age(self)`** (Line 146): Group old files by age ranges.

### Module: `src/cortex_unified/analyzers/package_manager_cleaner.py`
#### Class `Package`
Single installed package as reported by a manager's list command.


#### Class `PackageManager`
Detected manager executable with its resolved cache/config paths.


#### Class `CleanupResult`
Outcome of one cache-clean operation (counts, bytes, errors).


#### Class `HealthStatus`
Post-cleanup health verdict for a single package manager.


#### Class `PackageManagerCleaner`
Cleans caches for well-known package managers across platforms.

Detection probes PATH per-OS; cache locations are queried from each tool
itself rather than hard-coded, so custom cache dirs are honored. Package
lists are backed up under ~/.cortex_cleaner_backups before any destructive
operation.

- **`__init__(self, config)`** (Line 175): Build manager definitions, logger, and the backup directory.

Args:
    config: Optional application Config; a default is built if omitted.
- **`detect_package_managers(self)`** (Line 302): Probe PATH for supported managers on the current OS.

A manager counts as detected only if its executable exists and answers
--version; failures are logged at debug level and skipped.
- **`_get_package_manager_version(self, name, executable)`** (Line 338): Return the version string, parsed per-tool from --version output.
- **`_get_cache_path(self, name, config)`** (Line 366): Get cache directory path for a package manager.
- **`clean_pip_cache(self, keep_recent_days)`** (Line 457): Delete pip cache files older than keep_recent_days.

The pip cache holds only downloaded wheels and HTTP responses; pip
refetches anything missing, so removal is safe. Keeping recent files
preserves cache hits for imminent reinstalls.

Args:
    keep_recent_days: Age threshold in days; newer files stay.

Returns:
    CleanupResult with per-file counts, or a failure result when pip
    is unavailable or its cache dir is missing.
- **`clean_npm_cache(self, verify_integrity)`** (Line 513): Wipe npm's content-addressed cache, then optionally verify it.

npm caches tarballs/metadata keyed by integrity hash and refetches on
demand, so wiping is safe. `npm cache verify` afterwards rebuilds the
index and confirms consistency.

Args:
    verify_integrity: Run `npm cache verify` after cleaning.

Returns:
    CleanupResult; space_freed comes from before/after size sampling
    and files_removed is 0 if the tool does not report discrete file counts.
- **`clean_system_packages(self, package_manager)`** (Line 561): Run a system manager's native cache-clean command.

Applies to apt/dnf/pacman/brew/chocolatey-style managers; each command
drops only downloaded archives/metadata that get refetched on demand.

Args:
    package_manager: Name key from self.package_managers.

Returns:
    CleanupResult with space_freed measured before/after the run.
- **`find_orphaned_packages(self, package_manager)`** (Line 603): Dispatch to per-manager orphan detection.

Orphans are packages nothing else depends on (safe-to-remove
candidates). Unsupported managers yield [] with a warning.

Args:
    package_manager: Manager name (pip, npm, apt, dnf, pacman, brew).

Returns:
    List of Package records; empty on error or unsupported manager.
- **`_find_pip_orphaned_packages(self, manager)`** (Line 640): List installed pip packages without flagging any as orphaned.

True orphan detection would require cross-referencing requirements
files; this simplified pass reports is_orphaned=False everywhere.
- **`_find_npm_orphaned_packages(self, manager)`** (Line 671): Find extraneous / unreferenced npm packages.
- **`_find_apt_orphaned_packages(self, manager)`** (Line 697): Cross-references auto-installed packages with autoremove dry-run.
- **`_find_dnf_orphaned_packages(self, manager)`** (Line 731): Runs `dnf repoquery --unneeded` or `dnf leaves` to locate unreferenced packages.
- **`_find_pacman_orphaned_packages(self, manager)`** (Line 760): `pacman -Qtdq` lists dependency packages nothing requires anymore;
each name is returned as an orphaned Package (version unknown).
- **`_find_brew_orphaned_packages(self, manager)`** (Line 790): Runs `brew leaves` (installed formulas that no other formula depends on).
- **`backup_package_lists(self)`** (Line 816): Snapshot package lists for every detected manager.
- **`_backup_package_lists(self, managers)`** (Line 820): Write each manager's installed-package listing to a timestamped
file under ~/.cortex_cleaner_backups before destructive operations,
so removals can later be audited or replayed.

Returns:
    Dict mapping manager name to backup file path; only managers
    whose list command succeeded are included.
- **`verify_package_manager_health(self, package_manager)`** (Line 860): Post-cleanup sanity check for one manager.

Runs the manager's list command, probes cache-dir writability with a
touch/unlink file, and adds tool-specific checks (npm doctor,
pip check) where applicable.

Returns:
    HealthStatus; is_healthy is True only when no issues were found.
- **`_get_manager_by_name(self, name)`** (Line 914): Look up a detected manager by name key; None when absent.
- **`_get_cache_size(self, cache_path)`** (Line 921): Recursive byte total for a cache dir; missing paths count 0.
- **`get_stats(self)`** (Line 940): Get statistics about detected package managers.
- **`_format_bytes(self, bytes_count)`** (Line 959): Format bytes into human-readable format.
- **`scan_caches(self, target_folders, include_python_projects, keep_recent_days, enabled_categories, progress_callback, cancel_event)`** (Line 968): Locate cleanable caches in manager-owned dirs or project trees.

Without target_folders, reports each detected manager's global cache
(regenerable downloads). With target_folders, walks those trees and
matches directory names against PROJECT_CACHE_CATEGORIES.

Args:
    target_folders: Folders to scan for project caches; None selects
        global package-manager cache scanning instead.
    include_python_projects: Accepted for compatibility; category
        selection is controlled via enabled_categories.
    keep_recent_days: Ignore files younger than this many days (0 = all).
    enabled_categories: Restrict scan to these category IDs
        ('python', 'node', ...); None means all.
    progress_callback: Called as fn(status_text, items_found, total_size).
    cancel_event: threading.Event-like; set() aborts the walk.

Returns:
    List of resource dicts (schema in _scan_project_caches_in_folder
    and _scan_manager_cache).
- **`_scan_project_caches_in_folder(self, folder, keep_recent_days, enabled_categories, progress_callback, cancel_event)`** (Line 1019): Walk `folder` matching directory names against PROJECT_CACHE_CATEGORIES.

Dotted patterns (e.g. `.egg-info`) also match as name suffixes; each
hit is reported as a project_cache resource and pruned from deeper
descent. Loose .pyc/.pyo files are tallied into the running totals
when the python category is active but emit no per-file resource.
- **`_scan_manager_cache(self, manager, keep_recent_days)`** (Line 1119): Summarize one manager's global cache as a resource dict; None when
the dir is missing or holds no eligible files.
- **`_get_dir_size(self, path, cutoff_date)`** (Line 1147): Total bytes and file count under path.

Files modified at/after cutoff_date are excluded; callers use this to
keep recent cache entries and count only stale ones.
- **`clean_cargo_project(self, target_path, dry_run)`** (Line 1176): Run ``cargo clean`` for a Rust project's target dir.

Args:
    target_path: Path to the target folder (parent must contain Cargo.toml).
    dry_run: When True, only estimates size without deleting.

Returns:
    Dict with freed/removed/errors, cargo-aware message.
- **`auto_discover_project_caches(self, enabled_categories, keep_recent_days, progress_callback, cancel_event, max_depth)`** (Line 1207): Walk all fixed drives for PROJECT_CACHE_CATEGORIES without manual folder.

Scans common code roots (D:\code, C:\Users\...\code, ...) plus the
root of each fixed drive shallowly (max_depth) to catch the 21.9GB
NexusExplorer/target etc. cases where the user never picked a folder.

Returns:
    Same resource dicts as scan_caches(target_folders=...).
- **`cleanup_caches(self, resources, dry_run, progress_callback, cancel_event)`** (Line 1300): Dispatch each scanned resource to its cleaner and aggregate results.

Args:
    resources: Resource dicts as produced by scan_caches.
    dry_run: Passed through to the per-type cleaners; only some
        managers honor it (see _cleanup_manager_cache).
    progress_callback: Called as fn(done, total, freed_bytes).
    cancel_event: Set to stop before processing the next resource.

Returns:
    Summary dict with success/freed/removed/errors plus per-resource
    results keyed by resource name.
- **`_cleanup_python_cache(self, cache_path, dry_run)`** (Line 1373): Delete every file under a project-cache directory.

Contents (bytecode, tool/test caches, build outputs) are regenerated
by the toolchain, so wholesale deletion is safe; the directory itself
is removed only if it ends up empty.

Args:
    cache_path: Cache directory to clean.
    dry_run: Count files/sizes without unlinking.

Returns:
    Dict with freed bytes, removed count, errors, and dry_run echo.
- **`_cleanup_manager_cache(self, manager_name, dry_run)`** (Line 1426): Run the manager's native cache-clean command.

Package lists are backed up first and freed space is inferred from
before/after cache-size sampling. Only pip gets a true dry-run
(reported as a would-free estimate); every other manager executes its
real clean command regardless of dry_run.

Args:
    manager_name: Key into self.package_managers.
    dry_run: Estimate-only for pip; ignored by other managers.

Returns:
    Dict with freed/removed/errors, plus the backup path when a clean
    actually ran.

### Module: `src/cortex_unified/analyzers/perceptual_duplicate_finder.py`
#### Class `PerceptualDuplicateFinder`
Find visually-similar image groups via perceptual hashing.

Args:
    root_path: Directory (or iterable of directories) to scan.
    max_distance: Max Hamming distance (0..64) to treat as *similar*. For
        pHash, <=10 is the conventional "really different" bound; lower is
        stricter. Default 10.
    kinds: Which hashes to compute, e.g. ``("phash",)`` or
        ``("phash", "dhash")``.
    require_all_kinds: When more than one kind is given, require *every*
        kind to be within ``max_distance`` for two images to group
        (precision > recall). Default False (any single kind suffices).
    config: Exclusion rules / symlink policy.

- **`__init__(self, root_path, max_distance, kinds, require_all_kinds, config)`** (Line 316): __init__.
- **`_should_exclude(self, path)`** (Line 352): _should_exclude.
- **`_is_image(self, path)`** (Line 364): _is_image.
- **`find_perceptual_duplicates(self, threads, progress_callback, cancel_event)`** (Line 372): Scan the roots and return visual-duplicate groups (size >= 2).
- **`_window_size(self, n)`** (Line 511): Neighbourhood size for the sorted-hash candidate scan.
- **`get_stats(self)`** (Line 519): Aggregate stats akin to ``DuplicateFinder.get_stats``.

### Module: `src/cortex_unified/analyzers/portable_manager.py`
#### Class `PortableApp`
PortableApp.

- **`to_dict(self)`** (Line 87): to_dict.

#### Class `PortableManager`
PortableManager.

- **`__init__(self, progress, cancel)`** (Line 218): __init__.
- **`scan_portable_roots(self, roots)`** (Line 226): scan_portable_roots.
- **`check_updates(self, apps)`** (Line 270): Compare each app's installed version to its declared source.

Version sources, in order, exactly as the PortableApps Format
defines them (no invented marker files):

1. ``appinfo.ini`` → ``[Details] UpdateURL`` — a URL that serves
   the app's *current* ``appinfo.ini``; diffing versions tells us
   whether the installed copy is behind.
2. ``appinfo.ini`` → ``[Details] Website`` — vendor page, used
   only as metadata when no UpdateURL exists (not a version check).

Offline or undecorated apps simply report "not update-checkable";
fabricating a verdict is worse than none.
- **`update_app(self, app, timeout)`** (Line 334): Run the app's own PAF installer in silent mode, in place.

The PAF format's updater convention is the installer located at
``<app>\PortableApps.comInstaller.exe`` when the app ships one;
when the app maintains a local ``App\AppInfo\installer.exe`` we
use that. No download URL is guessed — the installer present in the
app directory is the only trusted source.
- **`export_toolkit(self, target, include_sysinternals, sysinternals_tools, include_live_iso, timeout)`** (Line 371): Build a portable toolkit on *target* (typically a USB drive).

Portable apps are copied from every discovered root. Sysinternals
tools are fetched from the live share (the documented distribution
point) rather than a guessed local path, and each download is
verified to be a PE executable before it is kept.
- **`_download_sysinternals(self, tool, dest, timeout)`** (Line 417): Fetch one Sysinternals tool and verify it is a real PE file.

The MZ header check catches HTML error pages and truncated
downloads before they masquerade as executables on a repair stick.

### Module: `src/cortex_unified/analyzers/privacy_cleaner.py`
#### Class `PrivacyCleaner`
Removes privacy-sensitive browser data and Windows activity traces.

Every deletion helper swallows OS errors, so a locked or missing file
never aborts a cleaning pass.

- **`__init__(self)`** (Line 25): __init__.
- **`scan_browsers(self)`** (Line 46): Scan all known browsers and return {browser: {category: size_bytes}}.
- **`scan_system_traces(self)`** (Line 72): Return sizes of cleanable Windows system privacy traces.
- **`clean_browser(self, browser, items)`** (Line 94): Delete selected data categories for one browser.

Args:
    browser: Key into ``browser_paths`` (e.g. "Chrome").
    items: Subset of {"Cache", "Cookies", "History", "Sessions"}.

Returns:
    False if any profile could not be fully cleaned.
- **`clean_system_traces(self, clean_recent)`** (Line 134): Clean system-level privacy traces, return bytes freed.
- **`_discover_chromium_profiles(base_path)`** (Line 161): Dynamically find Chromium profile directories.
- **`_scan_chromium_profile(self, prof_path, stats)`** (Line 178): Accumulate sizes from one Chromium profile.
- **`_clean_chromium_profile(self, prof_path, items)`** (Line 196): Delete specified items in one Chromium profile.
- **`_scan_firefox(self, profiles_path, stats)`** (Line 220): _scan_firefox.
- **`_get_file_size(path)`** (Line 241): _get_file_size.
- **`_get_dir_size(path)`** (Line 251): _get_dir_size.
- **`_safe_delete(path)`** (Line 270): Remove a file, ignoring errors (browsers commonly hold locks).
- **`_safe_delete_dir(path)`** (Line 279): Recursively remove a directory tree, ignoring failures.
- **`_clean_directory_contents(self, path)`** (Line 284): Remove all files inside a directory, return bytes freed.

Walks bottom-up so emptied subdirectories can be pruned too.

### Module: `src/cortex_unified/analyzers/project_cache_scanner.py`
#### Class `ProjectCacheScanner`
Drive-aware scanner for PROJECT_CACHE_CATEGORIES patterns.

Usage:
    scanner = ProjectCacheScanner(enabled_categories=["rust_go", "node"])
    resources = scanner.scan_fixed_drives()
    # resources are dicts compatible with PackageManagerCleaner.cleanup_caches

- **`__init__(self, enabled_categories, keep_recent_days)`** (Line 128): __init__.
- **`scan_fixed_drives(self, progress_callback, cancel_event, max_depth, prefer_code_roots)`** (Line 147): Scan all fixed drives (or known code roots) for project caches.
- **`_scan_root(self, folder, keep_recent_days, progress_callback, cancel_event, max_depth)`** (Line 185): Walk *folder* matching dir names against PROJECT_CACHE_CATEGORIES.
- **`_get_dir_size(self, path, cutoff_date)`** (Line 356): _get_dir_size.
- **`_format_bytes(n)`** (Line 379): _format_bytes.

### Module: `src/cortex_unified/analyzers/registry_cleaner_ai.py`
#### Class `RegistryIssue`
Single registry issue with ML risk score.

- **`to_dict(self)`** (Line 106): to_dict.

#### Class `ScanResult`
ScanResult.

- **`to_json(self)`** (Line 122): to_json.

#### Class `CleanResult`
CleanResult.


#### Class `_MLModel`
ONNX model wrapper for risk scoring.

- **`__init__(self, model_path)`** (Line 683): __init__.
- **`predict(self, features)`** (Line 698): Return (risk_score, confidence).
- **`_heuristic_score(self, features)`** (Line 713): Rule-based fallback when ML unavailable.

#### Class `AIRegistryCleaner`
AI-enhanced registry cleaner with learned safety.

- **`__init__(self, model_path, create_restore_point, progress_callback, cancel_event)`** (Line 750): __init__.
- **`_run_ps(self, script, timeout)`** (Line 770): _run_ps.
- **`_key_exists(self, path)`** (Line 786): _key_exists.
- **`_get_parent(self, path)`** (Line 805): _get_parent.
- **`_values_map(self, path, access)`** (Line 814): {name: (data, type)} for a key; empty dict when unreadable.
- **`_enum_values(self, path)`** (Line 834): _enum_values.
- **`_check_uninstaller(self, path)`** (Line 840): True when this key names an uninstaller that still exists on disk.
- **`_check_signature(self, path)`** (Line 850): Authenticode check on the first referenced binary, via WinVerifyTrust.
- **`_estimate_age(self, path)`** (Line 866): Days since the key's last write, from the FILETIME QueryInfoKey returns.
- **`scan(self, categories)`** (Line 886): Scan registry for issues.

Walks each category's roots directly through ``winreg`` (both the
64-bit and 32-bit views where relevant) and only emits an issue when
the category's detector proves the referenced target is gone. No
PowerShell, no whole-hive recursion.
- **`_iter_subkeys(self, root, access)`** (Line 973): Immediate subkey paths of *root* (plus *root* itself for value-only keys).
- **`_offending_value(self, key_path, values, category)`** (Line 992): Pick the value whose target is missing, for display and removal.
- **`clean(self, issues, selected_ids, full_hive_backup)`** (Line 1024): Clean selected issues (by index in the *issues* list).

Safety model: every mutation is preceded by a per-key ``reg export``
covering exactly what is about to change. A full hive export
(minutes of I/O on real machines) is available via
``full_hive_backup=True`` for users who want a belt-and-braces
rollback file before a large batch.
- **`_remove_and_backup(self, issue)`** (Line 1075): Back the key up first, then remove what the issue names.

The backup is written *before* the mutation so a crash mid-clean can
never leave a change without a matching .reg file. Key-level
categories remove the whole key; the rest remove the one value.
- **`_delete_key(self, key_path)`** (Line 1089): Delete a key and all its values, honouring the registry view.

Refuses to delete a key that still has subkeys: an Uninstall entry
with children (MSI can nest) is not what the scan proved dead, and
recursive deletion would be a guess. Succeeds silently if already
gone, so a partially-cleaned rerun is idempotent.
- **`_delete_value(self, key_path, value_name)`** (Line 1125): Delete one value, honouring the registry view the scan used.
- **`_backup_key(self, key_path)`** (Line 1151): Export the key to a timestamped .reg file, native view first.

Only HKLM keys have a separate 32-bit view; for those both views are
exported so a restore is complete. Raises when neither export
succeeds — a clean must never run without its backup.
- **`_backup_registry(self)`** (Line 1175): Export HKLM and HKCU so a failed clean is fully reversible.
- **`_create_restore_point(self)`** (Line 1190): _create_restore_point.

### Module: `src/cortex_unified/analyzers/residual_cleaner.py`
#### Class `ResidualCleaner`
Finds leftover files and folders for uninstalled applications.

- **`__init__(self)`** (Line 28): __init__.
- **`scan_for_app(self, app_name, publisher)`** (Line 43): Scan for leftover folders matching an uninstalled app.

Args:
    app_name:  Display name of the application (e.g. "Sublime Text")
    publisher: Publisher name for secondary matching (e.g. "Sublime HQ")
Returns:
    List of dicts: {"type", "path", "size"}
- **`_build_search_tokens(app_name, publisher)`** (Line 94): Build strict search tokens from the app name and publisher.

Filters out tokens that are too short or too generic to avoid
false positives (e.g. "MS" would match everything Microsoft).
- **`_matches_tokens(entry, tokens)`** (Line 127): Check if a directory name matches any of the search tokens.

Uses substring matching but only when the token is specific enough
(already enforced by _build_search_tokens).
- **`_get_size(path)`** (Line 142): Total size of a directory tree.

### Module: `src/cortex_unified/analyzers/residual_hunter.py`
### Module: `src/cortex_unified/analyzers/video_duplicate_finder.py`
#### Class `VideoDuplicateFinder`
Find temporally-similar video groups (re-encodes, trims, watermarks).

Args:
    root_path: Directory (or iterable) to scan.
    threshold: Minimum :func:`video_compare` score (0..1) to group.
        0.55 is the default (≈ a 3-frame temporal run on a 30-frame
        fingerprint). Lower = more permissive; raise to 0.7 for near-exact.
    max_distance: Per-frame Hamming threshold (default 10, Zauner).
    config: Exclusion rules / symlink policy.

- **`__init__(self, root_path, threshold, max_distance, config)`** (Line 417): __init__.
- **`_should_exclude(self, path)`** (Line 446): _should_exclude.
- **`_is_video(self, path)`** (Line 458): _is_video.
- **`find_video_duplicates(self, threads, progress_callback, cancel_event)`** (Line 464): find_video_duplicates.
- **`get_stats(self)`** (Line 593): get_stats.

### Module: `src/cortex_unified/analyzers/weaponized_shredder.py`