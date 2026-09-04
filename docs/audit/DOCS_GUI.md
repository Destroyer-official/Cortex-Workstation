# GUI Purpose Documentation (DOCS_GUI)

Scope: `src/cortex_unified/ui/premium/window.py` (_Page base + helpers only),
`src/cortex_unified/ui/main_window.py` (top 40 methods in file order),
`src/cortex_unified/ui/premium/workers.py` (all worker classes + module helpers),
`src/NexusExplorer/native/nexus_explorer.py` (ExplorerWidget: navigation, tabs,
drag-drop, transfer wiring, undo methods only).
Every entry was written from the method body. No stubs invented.
`PremiumMainWindow` and other page subclasses in `window.py` are out of scope
and are not documented here.

---

## src/cortex_unified/ui/premium/window.py

### fmt_bytes(n: int) -> str (L54)

Formats a byte count with the largest fitting binary unit (B…PB), one decimal.
Pure helper used by page labels; iterates dividing by 1024 until `size < 1024`.

### _TitleBarChrome.__init__(self, brand, min_btn, max_btn, close_btn) (L109)

Read-only handle storing the brand mark plus the three window-control buttons.
Widgets live on the window; this namespace exposes them as `_brand/_min/_max/_close`
so chrome code and tests avoid reaching into concrete attributes.

### _LazyPageRegistry.__init__(self, win: "PremiumMainWindow") -> None (L130)

Keeps the owning window and the cache (`_built`) of already-constructed pages.
Implements `Mapping`, so it reads like the eager `dict[str, QWidget]` it replaced.

### _LazyPageRegistry.__getitem__(self, page_id: str) -> QWidget (L137)

Builds (or returns cached) the page via `registry.BY_ID[page_id].load()(win)`,
adds it to `win._stack`, and caches it. Raises `KeyError(page_id)` for unknown ids.

### _LazyPageRegistry.__iter__(self) (L152)

Iterates page ids in sidebar/navigation order via `registry.ordered_ids()`.
Keeps iteration matching what the user sees rather than construction order.

### _LazyPageRegistry.__len__(self) -> int (L157)

Total number of registered pages (`len(registry.PAGES)`), built or not.
Lets `len(win._pages)` report all 43 pages while construction stays lazy.

### _LazyPageRegistry.__contains__(self, page_id: object) -> bool (L161)

Membership test against `registry.BY_ID`, so `in` works without building anything.
Backs `page_id not in self._nav_buttons_by_page`-style guards elsewhere.

### _LazyPageRegistry.is_built(self, page_id: str) -> bool (L167)

True only when the page was actually constructed (present in `_built`).
Introspection helper for tests/diagnostics; does not trigger a build.

### _LazyPageRegistry.built_ids(self) -> frozenset[str] (L172)

Property returning the frozenset of pages constructed so far.
Useful for tests and diagnostics without exposing the mutable cache.

### SingleScrollFilter.__init__(self, inner: QWidget, outer: QScrollArea | None = None, parent: QObject | None = None) (L1198)

Stores the inner scrollable view and the page's outer `QScrollArea`.
`outer` may be `None`, in which case the filter lets the inner view handle wheels alone.

### SingleScrollFilter.eventFilter(self, obj, event) (L1205)

Enforces "one gesture, one container": non-wheel events pass through; a wheel over
an inner view that can still scroll in that direction returns False (inner consumes
it), while a boundary push or a non-scrollable inner is forwarded to the outer area.

### SingleScrollFilter._forward_to_outer(self, event) -> bool (L1229)

Sends the wheel event to `outer.viewport()` via `QApplication.sendEvent` and
returns True so exactly one container reacts. Returns False when `outer` is None.

### set_tab_order(parent: QWidget | None, widgets) -> list[QWidget] (L1242)

Chains `QWidget.setTabOrder` across `widgets` so Tab moves in visual/logical order
instead of construction order. Skips `None`, never raises; returns the filtered list.

### ensure_focusable(*widgets) -> None (L1266)

Promotes any `NoFocus` widget to `StrongFocus` so primary actions stay keyboard
reachable. Ignores `None` and swallows failures; a defensive nudge, not a layout change.

### run_modal(dialog, trigger: QWidget | None = None) (L1286)

Shows the dialog modally (`exec()`) and restores keyboard focus to `trigger` on close
in a `finally` block. Returns the exec result code; focus-restore failure is swallowed.

### _Page.__init__(self, win: PremiumMainWindow) (L1344)

Base-page setup: stores `win`/`win.palette_tokens`, builds the outer `QVBoxLayout`
with a single `widgetResizable` `QScrollArea` (scrollbars `AsNeeded`), the content
`self.v` layout, momentum scrolling via `install_smooth_scroll`, and the filter list.

### _Page.pin_footer(self, widget: QWidget) -> QWidget (L1376)

Pins `widget` below the scroll area (added to `self._outer`, outside the `QScrollArea`)
so a primary action row stays visible at every window size. Returns the widget for chaining.

### _Page.attach_single_scroll(self, inner: QWidget) -> SingleScrollFilter (L1391)

Installs a `SingleScrollFilter(inner, self._scroll)` on `inner` and its viewport (when
present) so wheel gestures scroll either the list or the page, never both. Retains and
returns the filter (filters must stay referenced or Qt drops them).

### _Page.add_scrolling_list(self, inner: QWidget, *, stretch: int = 1, minimum_height: int | None = None) -> QWidget (L1409)

Applies the list-dominant scroll policy: sets `minimumHeight` (default
`LIST_MIN_HEIGHT = 140`), adds `inner` to `self.v` with stretch, then wires
`attach_single_scroll`. Returns `inner` for chaining.

---

## src/cortex_unified/ui/main_window.py

Top 40 methods in file order (L83–L1030): 3 worker classes + first 28 `DeepCleanerGUI` methods.

### ScanWorker.__init__(self, config: Config, path: str, enable_checkpoints: bool=False, enable_throttling: bool=False, checkpoint_id: str='') (L83)

Stores scan config, target path, checkpoint/throttle flags, and the stop flag.
Signals: `finished(list, list)`, `error(str)`, `progress_updated(object)`.

### ScanWorker.run(self) (L96)

Runs `Scanner(config, path, …).scan(checkpoint_id=…)` and emits `finished(files, dirs)`
or `error`. With checkpoints enabled, spawns a daemon poller thread relaying
`get_scan_progress()` through `progress_updated` every 0.5 s.

### ScanWorker.pause(self) (L126)

Pauses via `self.scanner.pause_scan()` when a scanner exists. No-op otherwise.
Called from the GUI pause button through the worker reference.

### ScanWorker.resume(self) (L133)

Resumes via `self.scanner.resume_scan()` when a scanner exists. Mirrors `pause()`.

### ScanWorker.stop(self) (L140)

Sets `_should_stop` (stops the progress poller) and, when checkpoints are enabled,
creates a resumable checkpoint and returns its id (else None). Abort-then-resume path.

### DeleteWorker.__init__(self, deleter: Deleter, empty_files: List[Path], empty_dirs: List[Path]) (L159)

Stores the `Deleter` plus the file/dir lists to remove. Signals: `finished(dict)`,
`error(str)`. Runs fully off the GUI thread.

### DeleteWorker.run(self) (L168)

Calls `self.deleter.delete(files, dirs)` and emits `finished(result_dict)` or `error`.
The GUI thread renders counts/errors in `delete_finished` / `delete_error`.

### MultiDriveScanWorker.__init__(self, config: Config, paths: List[str], enable_checkpoints: bool=False, enable_throttling: bool=False) (L185)

Stores config, the drive-path list, checkpoint/throttle flags, and pause/stop flags.
Signals mirror `ScanWorker`: `finished`, `error`, `progress_updated`.

### MultiDriveScanWorker.run(self) (L197)

Scans each drive sequentially with `MultiDriveScanner.scan_drive`, honoring pause
(busy-wait 0.2 s) and stop flags, aggregating `(files, dirs)` into one `finished`
emit. With checkpoints, polls `get_overall_progress()` from a daemon thread.

### MultiDriveScanWorker.pause(self) (L237)

Sets `_is_paused = True` so the per-drive loop waits. Cleared by `resume()`.

### MultiDriveScanWorker.resume(self) (L243)

Clears `_is_paused` so the drive loop continues. No scanner call needed.

### MultiDriveScanWorker.stop(self) (L249)

Sets `_should_stop = True` (and clears pause) to break the per-drive loop.
Less granular than `ScanWorker.stop`: no checkpoint is created here.

### DeepCleanerGUI.__init__(self) (L259)

Builds config, worker/thread slots, result stores, `SafetyManager`, `QSettings`,
base UI via `init_ui()`, then defers `add_advanced_tabs` (100 ms) and `init_tray_icon`
(150 ms) with `QTimer.singleShot` so the event loop is up first.

### DeepCleanerGUI.init_tray_icon(self) (L308)

Attaches `SystemTrayManager(self, QApplication.instance())`. Failure is logged
and ignored so a tray error never aborts the window.

### DeepCleanerGUI.__getattr__(self, name) (L316)

Proxies missing attribute access to child `BaseTab`s (e.g. legacy `scan_button`
refs). Guards underscore/dunder names and re-entrancy via `_in_getattr`.

### DeepCleanerGUI._safe_widget(self, name, default=None) (L333)

`getattr` with an `AttributeError` fallback to `default`. Used because legacy
methods reference widgets that may not exist in the navigation-controller layout.

### DeepCleanerGUI.init_ui(self) (L340)

Builds the central layout: `NavigationController` plus the 10 base tabs (Dashboard,
Cleaner, Duplicates, Deep Cleaner, Large Files, Disk Analyzer, Docker, Broken Links,
Restore, Settings), then a `Ready` status label.

### DeepCleanerGUI.add_advanced_tabs(self) (L382)

Lazily appends Package Caches, File Shredder, Scheduler, Reports, Resource Monitor,
System Tools, Security Scanner, Deep Uninstaller, Privacy Shield tabs. Any import
failure is logged as a warning, keeping the base window usable.

### DeepCleanerGUI.browse_path(self) (L423)

Opens a directory picker and writes the result into `self.path_input`.
Legacy single-path scan entry point.

### DeepCleanerGUI.browse_path_for_widget(self, widget) (L429)

Same directory picker but writes into the given widget. Generic helper for tabs
that own their own path fields.

### DeepCleanerGUI.add_activity(self, message) (L435)

Appends a `[HH:MM:SS] message` line to `activity_list` when present (via
`_safe_widget`). Central activity-feed writer for scan/delete flows.

### DeepCleanerGUI.get_current_time(self) (L443)

Returns local time as `HH:MM:SS`. Timestamp source for `add_activity`.

### DeepCleanerGUI.quick_scan(self) (L450)

Points `path_input` at the home folder, switches `tab_widget` to index 1, and calls
`start_scan()`. One-click entry guarded by `_safe_widget` lookups.

### DeepCleanerGUI.start_scan(self) (L462)

Validates single/multi-drive targets (`normalize_path` + existence), copies config
with pattern/age overrides, then moves a `ScanWorker`/`MultiDriveScanWorker` onto a
`QThread`, wiring `finished→scan_finished`, `error→scan_error`, progress signals,
and `quit`/`deleteLater` teardown before `start()`.

### DeepCleanerGUI.scan_finished(self, empty_files: List[Path], empty_dirs: List[Path]) (L581)

UI-thread completion handler: stores results, re-enables controls, hides progress,
writes the status/activity entries, and renders the file/dir listing (or the
empty-result text) while gating the delete button.

### DeepCleanerGUI.scan_error(self, error: str) (L615)

Resets scan controls, sets `Scan failed` status/activity, and shows a critical
dialog. Error path counterpart to `scan_finished`.

### DeepCleanerGUI.update_scan_progress(self, progress) (L632)

Renders a worker progress object (`percentage`, `processed_count/total_count`) into
`progress_bar` and `scan_stats_label`. Called via the checkpoint progress signal.

### DeepCleanerGUI.start_delete(self) (L642)

Confirms dry-run/trash options with the user, then runs `Deleter(dry_run, use_trash)`
in a `DeleteWorker`/`QThread` with the same moveToThread + `finished/error→quit` +
`deleteLater` lifecycle as scanning.

### DeepCleanerGUI.pause_scan(self) (L686)

Calls `scan_worker.pause()` when available, flips pause/resume buttons, and sets
`Scan paused`. Warns when no scan runs or the worker lacks `pause`.

### DeepCleanerGUI.resume_scan(self) (L714)

Calls `scan_worker.resume()` when available, restores the button states, and sets
`Scanning…`. Mirrors `pause_scan` including the no-worker warnings.

### DeepCleanerGUI.delete_finished(self, result: Dict[str, Any]) (L742)

Appends deletion counts/errors to `results_text`, re-enables controls, hides
progress, logs `files_deleted/dirs_deleted`, clears the pending lists, and disables
the delete button until the next scan.

### DeepCleanerGUI.delete_error(self, error: str) (L768)

Re-enables controls, sets `Deletion failed` status/activity, and shows a critical
dialog. Error path counterpart to `delete_finished`.

### DeepCleanerGUI.show_treemap_visualization(self) (L778)

Exports the current analyzer via `TreeMapGenerator.export_as_html()` to a temp file
and opens it in a browser. Requires `current_analyzer` and Plotly; warns otherwise.

### DeepCleanerGUI.show_sunburst_visualization(self) (L802)

Same flow as treemap but with `SunburstGenerator`. Temp-HTML + `webbrowser.open`,
gated on analyzer presence and Plotly availability.

### DeepCleanerGUI.show_interactive_dashboard(self) (L826)

Builds an `InteractiveDashboard` figure, serializes it with `plotly.offline.plot`
(CDN JS) to temp HTML, and opens it. Same analyzer/Plotly preconditions.

### DeepCleanerGUI.export_visualization_dialog(self) (L856)

Modal dialog choosing visualization type (treemap/sunburst/dashboard radio) and
format (HTML/PNG/SVG radio); stores radios on `self` and routes Export to
`perform_visualization_export(dialog)`.

### DeepCleanerGUI.perform_visualization_export(self, dialog) (L898)

Reads the dialog radios, prompts for a save filename, then writes HTML text or image
bytes from the matching generator (dashboard delegates to `export_visualization`).
Accepts the dialog and reports success; failures show a critical dialog.

### DeepCleanerGUI.refresh_startup_items(self) (L948)

Loads `StartupManager().list_startup_items()` + stats into `startup_table`
(name/location/enabled/type), updates the progress bar and status/activity, and
enables the disable button only when rows exist. Errors restore controls + dialog.

### DeepCleanerGUI.disable_selected_startup_items(self) (L985)

Collects selected `(name, type)` rows, calls `manager.disable_startup_item` per row,
tallies `disabled_count` vs errors, reports the summary, and refreshes the table.
No-op with an info dialog when nothing is selected.

### DeepCleanerGUI.refresh_processes(self) (L1030)

Loads `ProcessAnalyzer.list_processes()/list_services()` into `processes_table`
(name/pid/memory/cpu, Windows vs non-Windows field mapping) and `services_table`,
then logs totals from `get_stats()`. Button/progress restored in `finally`.

---

## src/cortex_unified/ui/premium/workers.py

Module contract: every class is a plain `QObject` moved onto a `QThread` by
`PremiumMainWindow.run_worker`; results travel only via signals. `cancel()` sets a
`threading.Event` the engine polls. `run()` never touches widgets.

### _norm(p) (L131)

Normalizes a path to Windows backslash form (`/` → `\`) for prefix matching.
Shared by the aggregate/children/group helpers below.

### aggregate_roots(entries, roots) (L136)

Aggregates already-scanned entries under each root folder into `{name, path, size,
count, is_dir, expandable}` buckets sorted by size desc. Pure computation for a
category node; no filesystem walk.

### children_under(entries, prefix: str) (L157)

Returns immediate files plus aggregated subfolders directly under `prefix` from the
in-memory entries (splits the remainder on `\`, one level deep). Caps work at the
caller (`DirPreviewWorker` slices to 400); sorted by size desc.

### group_by_app(entries, bases) (L205)

Groups cache entries by owning app (first folder after a base root like
`%LOCALAPPDATA%`), mapping vendor folder names through `_APP_FRIENDLY`
("google" → "Google Chrome"). Returns selectable app nodes sorted by size.

### ScanWorker — backend `CleanerService.scan_categories` (L25)

Signals: `finished(object/CleanupReport)`, `progress(str)`, `failed(str)`.
`__init__(max_risk, include_disabled)` (L37) stores the risk ceiling + cancel event;
`cancel()` (L44) sets it; `run()` (L48) forwards `progress.emit`/`cancel_event` to the
engine and emits `finished(report)` or `failed`.

### CleanWorker — backend `CleanerService.clean_categories` (L62)

Signals: `finished(object, int, int)` = (bytes_freed, items_cleaned, items_skipped),
`progress(str)`, `failed(str)`. `__init__(report, method)` (L69) stores inputs;
`cancel()` (L76) aborts; `run()` (L80) maps `(done, total)` to `"Cleaning… d / t"`,
sums per-result sizes, and emits the triple (dry-run bytes excluded).

### DuplicateWorker — backend `CleanerService.find_duplicates` (L102)

Signals: `finished(dict)` = `{hash: [Path, …]}`, `progress(str)`, `failed(str)`.
`__init__(roots)` (L108) stores roots + cancel event; `cancel()` (L114); `run()` (L118)
converts roots to `Path`s and emits the hash groups.

### DirPreviewWorker — backend pure helpers (`group_by_app`/`aggregate_roots`/`children_under`) (L232)

Signals: `finished(int, list)` = (node_id, children), `failed(str)`. No progress or
cancel (fast in-memory work). `__init__(node_id, entries, mode, roots, prefix)` (L238);
`run()` (L248) picks the helper by `mode` (`appwise`/`category`/else-prefix) and emits
up to 400 children so tree expansion stays snappy off the UI thread.

### DuplicatePhotosWorker — backend `CleanerService.find_duplicates` + `IMAGE_EXTS` filter (L262)

Signals: `finished(dict)`, `progress(str)`, `failed(str)`. Same shape as
`DuplicateWorker` but `run()` (L284) passes the image-extension set
(jpg/png/gif/bmp/tiff/webp/heic/raw/cr2/nef/arw/dng…); `__init__` (L274), `cancel()` (L280).

### LargeFilesWorker — backend `CleanerService.find_large_files` (L298)

Signals: `finished(list)` = up to 200 `FileEntry`s, `progress(str)`, `failed(str)`.
`__init__(root, min_mb)` (L304); `cancel()` (L311); `run()` (L315) forwards
`limit=200` + progress/cancel to the engine.

### EmptyWorker — backend `CleanerService.find_empty` (L327)

Signals: `finished(list, list)` = (empty_files, empty_dirs), `progress(str)`,
`failed(str)`. `__init__(root)` (L334); `cancel()` (L340); `run()` (L343). Note:
`find_empty` takes only `cancel_event` (no progress callback wired here).

### DeleteSelectedWorker — backend `SecureDeleter.delete_many` (L352)

Signals: `finished(object, int, int)` = (bytes_freed, succeeded, blocked), `failed(str)`.
No progress/cancel. `__init__(paths, method)` (L358); `run()` (L364) builds a
`SecureDeleter`, deletes with `DeletionMethod(method)`, and splits counts by
`succeeded` (dry-run bytes excluded from `freed`).

### RestorePointWorker — backend `RestorePointManager.create` (L380)

Signals: `finished(str, str)` = (status, message), `failed(str)`.
`__init__(description="Cortex Cleaner")` (L386); `run()` (L391) shells to
PowerShell-backed creation off the UI thread.

### RestorePointListWorker — backend `RestorePointManager.list_points` (L401)

Signals: `finished(list)`, `failed(str)`. Read-only. `run()` (L407) emits the
existing-point list; no `__init__` args, no cancel.

### StorageWorker — backend `engine.detect_storage` (L416)

Signals: `finished(str, bool)` = (kind, overwrite_effective), `failed(str)`.
`__init__(path)` (L422); `run()` (L427) emits `info.kind.value` plus
`info.kind.overwrite_effective` (subprocess-backed detection, hence threaded).

### FreeSpaceWipeWorker — backend `FreeSpaceWiper.wipe` (`cipher /w`) (L437)

Signals: `finished(bool, str)` = (success, message), `failed(str)`.
`__init__(drive_letter)` (L443); `cancel()` (L449) reaches down to `core.proc.run()`,
which kills the process tree within one poll interval (cipher can run ~1 h);
`run()` (L457) forwards the cancel event.

### ShredWorker — backend `SecureDeleter.delete` (OVERWRITE, storage-aware) (L467)

Signals: `finished(str, str)` = (outcome, reason), `refused(str, str)` = (medium_kind,
guidance), `failed(str)`. `__init__(target, passes, force_flash)` (L474); `run()` (L481)
catches `OverwriteNotEffective` into `refused` (wired to `thread.quit` by `run_worker`;
ShredPage adds its own handler) instead of `failed`.

### AdaptiveShredWorker — backend `AdaptiveSanitizer.sanitize` (PL0–PL3) (L501)

Signals: `finished(str, str, str)` = (outcome, message, detail), `failed(str)`.
`__init__(target, level=None, verify=True)` (L511) where None/"auto" picks PL by
storage kind + file hotness; `run()` (L518) maps `PrivacyLevel`, sanitizes, and emits
`shredded/failed` plus `PL=… method wear=… verified=…` detail.

### VhdxListWorker — backend `VhdxManager.list_disks` (L545)

Signals: `finished(list)` = `VirtualDisk`s, `progress(str)`, `failed(str)`.
`__init__` (L552) only makes the cancel event; `cancel()` (L557); `run()` (L561)
emits a status line, lists disks, and returns silently (no `finished`) when cancelled
mid-scan so a closed page never resolves stale results.

### WslShutdownWorker — backend `VhdxManager.shutdown_wsl` (`wsl --shutdown`) (L576)

Signals: `finished(bool, str)` = (ok, message), `progress(str)`, `failed(str)`.
No `__init__` args/cancel; `run()` (L583) announces "Stopping WSL…" then emits the
detachment result needed before compacting virtual disks.

### VhdxCompactWorker — backend `VhdxManager.compact` per disk (diskpart) (L594)

Signals: `finished(list)` = `CompactResult`s, `progress(str)`, `failed(str)`.
`__init__(disks)` (L606); `cancel()` (L612) stops *between* disks (compaction is not
interruptible once diskpart owns the file); `run()` (L616) emits per-disk progress
with position/total and the measured space-returned list.

### VhdxSparseWorker — backend `VhdxManager.set_sparse` (L635)

Signals: `finished(bool, str)`, `progress(str)`, `failed(str)`.
`__init__(disk, enabled=True)` (L642); `run()` (L648) toggles WSL sparse mode so
reclaimed bloat does not return. No cancel (single quick toggle).

### ComponentStoreAnalyzeWorker — backend `ComponentStore.analyze` + `find_leftovers` (DISM) (L663)

Signals: `finished(object, list)` = (StoreAnalysis, leftovers), `progress(str)`,
`failed(str)`. Read-only but minutes-long, hence threaded. `__init__` (L674);
`cancel()` (L679); `run()` (L683) sizes WinSxS from DISM (not a hard-link walk),
checks cancel between phases, and passes `analysis` into `find_leftovers`.

### ComponentStoreCleanWorker — backend `ComponentStore.cleanup` (DISM `/StartComponentCleanup`) (L705)

Signals: `finished(object)` = CleanupOutcome, `progress(str)`, `failed(str)`.
`__init__(reset_base=False)` (L712); `run()` (L717) forwards the flag + progress.
No cancel handle (DISM owns the run once started).

### ServicingTaskWorker — backend `ComponentStore.run_servicing_task` (L728)

Signals: `finished(bool, str)`, `progress(str)`, `failed(str)`. `run()` (L735)
triggers Windows' own scheduled component-cleanup task with a status line. No
`__init__` args/cancel.

### LeftoverDeleteWorker — backend `SecureDeleter.delete_many` (guarded) (L746)

Signals: `finished(object, int, int)` = (bytes_freed, removed, blocked), `progress(str)`,
`failed(str)`. `__init__(paths, sizes=None)` (L757); `cancel()` (L764); `run()` (L768)
forces `DeletionMethod.DELETE` (system dirs cannot go to the Recycle Bin) with the
path guard intact, mapping `(done, total)` to `"Removing…"` progress.

### ProjectCacheScanWorker — backend `PackageManagerCleaner.scan_caches` (L790)

Signals: `finished(list)` = resources, `progress(str, int, object)` = (status,
items, bytes), `failed(str)`. `__init__(target_folders, keep_recent_days=7,
enabled_categories=None)` (L797); `cancel()` (L805); `run()` (L809) relays the
`(status, items, size)` callback into the 3-arg signal.

### ProjectCacheCleanWorker — backend `PackageManagerCleaner.cleanup_caches` (L833)

Signals: `finished(dict)` = results, `progress(int, int, object)` = (done, total,
freed), `failed(str)`. `__init__(resources, dry_run=True)` (L840) — dry run by
default; `cancel()` (L847); `run()` (L851) relays `(done, total, freed)`.

### AutoProjectCacheWorker — backend `PackageManagerCleaner.auto_discover_project_caches` (L878)

Signals: `finished(list)`, `progress(str, int, object)`, `failed(str)`.
`__init__(enabled_categories=None, keep_recent_days=7)` (L885) — walks fixed drives
(or known `D:\code`) across `PROJECT_CACHE_CATEGORIES` with no manual folder pick;
`cancel()` (L892); `run()` (L896).

### CacheLogSweepWorker — backend `CacheCleaner.find_large_logs` (L918)

Signals: `finished(list)` = [(Path, size)], `progress(str)`, `failed(str)`.
`__init__(roots, min_size_mb=100.0)` (L925); `cancel()` (L932); `run()` (L936) sweeps
`*.log/*.txt` with `exclude_archives=True`, forwarding progress + cancel.

### DockerFsCacheWorker — backend `DockerCleaner.get_filesystem_cache_size` (L949)

Signals: `finished(dict)`, `failed(str)`. No progress/cancel (single measurement).
`run()` (L955) emits the `AppData\Local\Docker` cache-size dict.

### WslListWorker — backend `WslCleaner.list_distros` (L964)

Signals: `finished(list)`, `failed(str)`. `run()` (L970) emits
`[d.to_dict() for d in …]` (distro + ext4.vhdx sizes). No progress/cancel.

### LargeFileAiWorker — backend `LargeFileFinder` + `is_ai_model` (L979)

Signals: `finished(list, list)` = (other_files, ai_model_files), `progress(str)`,
`failed(str)`. `__init__(root, min_mb=100.0)` (L986); `cancel()` (L993, stored but the
finder call in `run()` takes no cancel event); `run()` (L997) splits the finder
output by `is_ai_model(path)` and emits both lists.

---

## src/NexusExplorer/native/nexus_explorer.py — ExplorerWidget only

### ExplorerWidget.__init__(self, start_path: str = "", parent=None, root: str = "") (L5479)

Builds the whole explorer: `Engine`, `FileTableModel` + `SortProxy`, tab/history
state, `QuickLookPopup`/`FolderSizeCalculator`/`ColorTagManager`/`SmartFolderManager`/
`UndoManager`/`ArchiveBrowser`, bookmarks, and the `TransferQueue` (wired to the six
`_on_transfer_*` slots below). Lays out the Tier-1 tab bar (`QTabBar` + new-tab button)
and Tier-2 nav/address/search row with `nav_btn`/`action_btn` factories.

### ExplorerWidget.mount_tabs_to_window(self, win) -> None (L6106)

Reparents `tab_container` into the host window's title-bar row via
`win.set_titlebar_tab_widget` (the `PremiumMainWindow` counterpart). Lets Nexus tabs
live in the frameless title bar instead of the page body.

### ExplorerWidget._on_about_to_quit(self) -> None (L6112)

Persists the session on app quit by calling `save_session(force=True)`.
Connected to the application `aboutToQuit` signal.

### ExplorerWidget.save_session(self, force=False) (L6117)

Writes schema-v1 session (last path, sidebar/debug flags, tab paths JSON, active tab,
view mode, dual-pane, splitter sizes) to `QSettings("Nexus", "NexusExplorer")`.
Never raises; failures log at debug.

### ExplorerWidget.restore_session(self) (L6135)

Rebuilds tabs/paths, active index, icons/details mode (`_pending_view_mode`), dual
pane, sidebar, and splitter sizes from QSettings, validating every value (bad paths
dropped, indices clamped). Never raises; falls back to initialized state.

### ExplorerWidget.add_tab(self, path: str) -> None (L6402)

Appends `{path, history:[path], hindex:0}`, adds a `QTabBar` tab with a custom
hover-red close button (resolves the button back to its index in `_on_close_btn`),
selects it, and logs the addition. New-tab button passes `~`.

### ExplorerWidget._close_tab(self, idx: int) -> None (L6430)

Refuses when only one tab remains or the index is out of range; otherwise pops the
state, removes the tab, clamps to a neighbor, and `_switch_tab`s to it.

### ExplorerWidget._on_tab_moved(self, from_pos: int, to_pos: int) -> None (L6441)

Keeps `_tabs` in sync with a `QTabBar` drag-reorder and remaps `_current_tab`
through the move. Backs the movable-tab UX.

### ExplorerWidget._close_current_tab(self) -> None (L6454)

Closes `_current_tab` via `_close_tab` when valid. Shortcut/command-palette target.

### ExplorerWidget._switch_tab(self, idx: int) -> None (L6460)

Sets `_current_tab`, clears the inline filter, and `_load`s that tab's path.
Slot for `tabbar.currentChanged`.

### ExplorerWidget._tab(self) -> dict (L6470)

Returns the current tab dict, or a synthetic home-folder tab when none is valid.
Every navigation/operation method reads the location through here.

### ExplorerWidget.navigate(self, path: str, push: bool = True) -> None (L6478)

Normalizes/expands the path, rejects non-dirs in the status bar, truncates forward
history and pushes when `push=True`, renames the tab, syncs `folder_tree.select_path`,
and `_load`s. `push=False` is the back/forward/tab-switch path.

### ExplorerWidget._load(self, path: str) -> None (L6499)

Refreshes crumbs, preview folder, filter placeholder, terminal cwd, address text, and
the `QFileSystemWatcher` (re-pointed with signals blocked), clears the folder-size
queue, bumps the `_load_seq` guard, and calls `engine.list_dir(path, _deliver)` where
`_deliver` drops stale (superseded-sequence) listings.

### ExplorerWidget._on_rows(self, code: int, rows: list[dict]) -> None (L6527)

Applies engine rows to the model, updates status, honors a pending icons-mode switch,
routes empty/non-empty rows to the empty/table/icon stack pages, and kicks off
background folder-size calculation. Delivery point for `_deliver`.

### ExplorerWidget._reload_current(self) -> None (L6551)

Reloads the current tab's path via `_load`. Called after every mutation (transfer
completion, undo/redo, create, rename) to reflect the new on-disk state.

### ExplorerWidget._on_fs_change(self, _path: str) -> None (L6620)

Debounces filesystem-watcher notifications by (re)starting `_reload_timer` instead
of reloading inline, so burst writes collapse into one refresh.

### ExplorerWidget.go_back(self) (L6625)

Steps `hindex` back and `navigate`s with `push=False`. Per-tab history; no-op at
the oldest entry.

### ExplorerWidget.go_forward(self) (L6633)

Steps `hindex` forward and `navigate`s with `push=False`. Mirrors `go_back`.

### ExplorerWidget._right_go_back(self) (L6642)

Same as `go_back` for the dual-pane right tab (`_right_tab`/`_right_navigate`).
Target of mouse BackButton when the cursor is over the right viewport.

### ExplorerWidget._right_go_forward(self) (L6650)

Same as `go_forward` for the right pane. Target of mouse ForwardButton over it.

### ExplorerWidget._install_mouse_side_buttons(self) -> None (L6658)

Enables drops and installs `eventFilter(self)` on the widget, stack, empty state,
splitter, all table/icon/quick/smart views + viewports, and the folder tree, so one
filter sees every drag event and mouse side-button press.

### ExplorerWidget.eventFilter(self, obj, ev) (L6699)

Two jobs: (1) accept-propose every DragEnter/DragMove (with `_update_drop_hint`),
route DragLeave to `_update_status` and Drop to `_handle_viewport_drop`; (2) map
BackButton/ForwardButton to left/right-pane back/forward based on which viewport the
press landed in. Falls through to super otherwise.

### ExplorerWidget._handle_viewport_drop(self, obj, ev) -> bool (L6739)

Core drop executor: gathers sources (MIME URLs → text lines → staging shelf →
selection), resolves the destination dir (current tab, or the folder row/item/tree
node under the cursor), picks move (Shift or cut mode incl. staging shelf) vs copy,
records undo per file, enqueues a `TransferQueue` copy/move job, clears cut staging,
and confirms in the status bar. Returns True when it consumed the drop.

### ExplorerWidget._update_drop_hint(self, obj, ev) -> None (L6845)

Best-effort hover hint: counts dragged items and, when hovering a folder row/item,
writes `Drop N item(s) into <name>` to `status_sel` (and current-indexes the table
row). Never raises, never changes selection otherwise.

### ExplorerWidget.go_up(self) (L6883)

Navigates to the parent directory, or `_archive_go_up()` when browsing inside an
archive. Up-button/keyboard target.

### ExplorerWidget._start_edit_path(self) (L6893)

Swaps the crumb bar for the address `QLineEdit` prefilled with the tab path, focused
and selected. Entry to type-a-path mode (commit/cancel handled by the addr slots).

### ExplorerWidget.dragEnterEvent(self, ev: QDragEnterEvent) (L7891)

Accepts the proposed drag action at widget level so external drags can enter.
Viewport-level drags are handled by `eventFilter`; this covers the chrome.

### ExplorerWidget.dragMoveEvent(self, ev: QDragMoveEvent) (L7896)

Accepts the move and, when hovering a folder row in the main table, highlights it
and shows the `Drop N item(s) into <name>` hint in `status_sel`. Failures swallowed.

### ExplorerWidget.dragLeaveEvent(self, ev) (L7922)

Refreshes the status bar via `_update_status()` to clear drop hints. Best-effort.

### ExplorerWidget.dropEvent(self, ev) (L7930)

Delegates to `_handle_viewport_drop(self, ev)`; ignores the event when it returns
False. Widget-level drop path (viewport drops arrive via `eventFilter`).

### ExplorerWidget.startDrag(self, actions: Qt.DropAction) (L7936)

Drag source: builds `QMimeData` with `file://` URLs + newline text from selected
existing paths, uses the first item's icon as the drag pixmap, and `drag.exec`s it
for inter-app / intra-view drags.

### ExplorerWidget._on_transfer_started(self, job_id: str) (L7475)

Shows `Transfer active (<id>…)` in `status_items`. Slot for `TransferQueue.job_started`.

### ExplorerWidget._on_transfer_added(self, job_id: str) (L7481)

No-op by design: the preview-pane `TransferStatusDock` tracks `job_added` itself via
`bind_queue`, so no manual refresh is needed here.

### ExplorerWidget.open_transfer_monitor(self) (L7489)

Lazily creates `TransferMonitorDialog(queue, self)` and opens it. Manual entry to the
full transfer monitor (progress/cancel per job).

### ExplorerWidget._on_transfer_progress(self, job_id: str, percent: int, text: str) (L7499)

Writes `Transfer <pct>% — <text>` to `status_items`. Slot for `job_progress`.

### ExplorerWidget._on_transfer_cancelled(self, job_id: str) (L7505)

Writes `Transfer cancelled` and reloads the current folder to drop partial state.
Slot for `job_cancelled`.

### ExplorerWidget._on_transfer_completed(self, job_id: str, success: bool, message: str) (L7512)

Reloads the current folder so copy/move/delete results appear. Slot for `job_completed`.

### ExplorerWidget._on_transfer_queue_empty(self) (L7517)

Reloads once the queue drains (final consistency after chained jobs). Slot for
`queue_empty`.

### ExplorerWidget._move_to_folder(self) (L7695)

Moves the selection via a directory picker, enqueuing `TransferQueue(kind="move",
sources, dest)`. Undo for the move is recorded inside the queue path, not here.

### ExplorerWidget._paste(self, target_dest: str | None = None) (L7745)

Pastes clipboard (falling back to the staging shelf), filters to existing sources,
records per-file undo (copy vs move), enqueues the serialized `TransferQueue` job,
and clears cut clipboard/shelf afterwards. Reports `Nothing to paste` when empty.

### ExplorerWidget._on_staging_paste(self, mode: str, paths: list[str], target_dir: str) (L7786)

Staging-shelf variant of `_paste`: validates paths, records undo per file, enqueues
the queue job, and clears the shelf/clipboard on cut. Keeps shelf and queue in sync.

### ExplorerWidget._delete(self, permanent: bool = False) (L7820)

Confirms permanent deletes, records `record_delete` per path *before* executing,
then enqueues `TransferQueue(kind="delete", sources, permanent)`. Recycle vs
permanent is decided by the flag.

### ExplorerWidget._compress_to(self, fmt: str) (L7630)

Compresses the selection with 7z (`ZIP/7z/TAR.GZ` → ext/flag map): prompts for the
archive name, shows `ExtractionProgressWidget`, builds a temp file list, and runs
`_CompressWorker(cmd, name)` with progress/finish wired to the widget + `_reload_current`.

### ExplorerWidget._undo(self) (L7843)

Calls `UndoManager.undo()`, logs + shows the message, refreshes the undo description
label, and reloads the folder; `Nothing to undo` when the stack is empty.

### ExplorerWidget._redo(self) (L7855)

Calls `UndoManager.redo()` with the same log/status-label/reload flow as `_undo`;
`Nothing to redo` when empty. Redo descriptions update `status_undo`.

Note — undo *recording* call sites (all in this file): `_handle_viewport_drop`
(record_copy/record_move per dropped file, L6821–6826), `_new_folder` (L7532),
`_new_nested_folder` / `_new_file` / `_new_nested_file` / `_batch_scaffold`
(record_new_folder/record_new_file/record_batch_create), `_rename`
(record_rename, L7725), `_paste` / `_on_staging_paste` (record_copy/record_move),
`_delete` (record_delete before enqueue, L7833–7834).
