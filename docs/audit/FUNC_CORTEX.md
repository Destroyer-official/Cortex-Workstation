# FUNC_CORTEX — function inventory of src/cortex_unified/**

_Source: `src/cortex_unified/**` (316 Python files, `__pycache__` skipped). Each entry read from source AST; purpose = docstring first line or first-statement summary when undocumented._

## src/cortex_unified/__init__.py — Cortex Cleaner - safe, fast cleanup and system-care toolkit.
- func __getattr__(name: str) (L62): Resolve the legacy convenience exports on first use (:pep:`562`).
- func __dir__() (L82): __dir__.

## src/cortex_unified/__main__.py — ``python -m cortex_unified`` entry point.
- func main() (L24): Run the legacy CLI and return its process exit code.

## src/cortex_unified/accessibility/__init__.py — Accessibility module for Cortex Cleaner.
- func setup_accessibility(widget) (L25): Set up accessibility features for a widget.
- func setup_full_accessibility(widget, enable_shortcuts=True, enable_announcements=True) (L35): Set up full accessibility features with options.

## src/cortex_unified/accessibility/keyboard_handler.py — Keyboard-only navigation: focus cycling, tab order, and app shortcuts.
- class KeyboardHandler(QObject) (L20): Focus management and shortcut routing for a host widget.
- method KeyboardHandler.__init__(self, widget: Any=None) (L27): Bind to ``widget``; logging-only when PySide6 is absent.
- method KeyboardHandler.setup_keyboard_navigation(self) (L39): Discover focusable children, fix tab order, install the filter.
- method KeyboardHandler._find_focusable_widgets(self) (L60): Collect visible/enabled widgets sorted top-to-bottom, left-to-right.
- func KeyboardHandler._find_focusable_widgets.find_widgets(parent) (L71): find_widgets.
- method KeyboardHandler._setup_tab_order(self) (L85): Chain consecutive widgets so Qt Tab matches the visual order.
- method KeyboardHandler.handle_tab_navigation(self, event: QKeyEvent) (L99): Advance/wrap focus on Tab and Shift+Tab; True when consumed.
- method KeyboardHandler.setup_shortcuts(self, shortcuts: Dict[str, Callable]) (L120): Register a QShortcut for each key sequence -> callback pair.
- method KeyboardHandler.setup_default_shortcuts(self) (L136): Install the app-wide scheme (scan, clean, settings, quit...).
- method KeyboardHandler._trigger_scan(self) (L156): Dispatch scan trigger to active window or page.
- method KeyboardHandler._trigger_clean(self) (L166): Dispatch clean trigger to active window or page.
- method KeyboardHandler._open_settings(self) (L176): Dispatch settings navigation to active window.
- method KeyboardHandler._refresh(self) (L182): Dispatch refresh trigger to active window or page.
- method KeyboardHandler._select_all(self) (L192): SelectAll on the focused item view, when applicable.
- method KeyboardHandler._show_help(self) (L199): _show_help.
- method KeyboardHandler._quit_application(self) (L206): Close the host widget's window.
- method KeyboardHandler._cancel_operation(self) (L211): Cancel any running operation in the host widget.
- method KeyboardHandler._activate_focused(self) (L221): Click the focused widget if it supports click().
- method KeyboardHandler._toggle_selection(self) (L227): Invert selection of the current item in an item view.
- method KeyboardHandler.eventFilter(self, obj: QObject, event: QEvent) (L235): Consume Tab and arrow presses before default widget handling.
- method KeyboardHandler._handle_arrow_navigation(self, event: QKeyEvent) (L248): Route arrows to custom traversal unless an item view owns them.
- method KeyboardHandler._navigate_with_arrows(self, key: int) (L261): Step focus forward/backward through focusable_widgets.
- method KeyboardHandler.add_widget_to_navigation(self, widget: Any) (L281): Append to the traversal order and rechain tab order.
- method KeyboardHandler.remove_widget_from_navigation(self, widget: Any) (L287): remove_widget_from_navigation.
- method KeyboardHandler.get_shortcut_info(self) (L294): Human-readable shortcut cheat sheet for help displays.

## src/cortex_unified/accessibility/screen_reader.py — Screen-reader affordances for Qt widget hierarchies.
- class ScreenReaderSupport (L34): Annotates a widget hierarchy for assistive technology.
- method ScreenReaderSupport.__init__(self, widget: Any=None) (L42): Attach to ``widget``; logging-only degradation without Qt.
- method ScreenReaderSupport._init_platform_accessibility(self) (L53): Load platform hooks; unimplemented platforms just log.
- method ScreenReaderSupport.add_aria_labels(self, elements: List[Any]) (L67): Set name, description, and role properties on each QWidget.
- method ScreenReaderSupport._generate_accessible_name(self, widget: QWidget) (L96): First non-empty of text/title/toolTip, else '<Type> <objectName>'.
- method ScreenReaderSupport._generate_accessible_description(self, widget: QWidget) (L110): Type-specific usage hint, suffixed with disabled/checked state.
- method ScreenReaderSupport._get_accessible_role(self, widget: QWidget) (L138): Map Qt widget class to the nearest WAI-ARIA role name.
- method ScreenReaderSupport.announce_changes(self, message: str) (L159): Fire a Qt alert accessibility event plus platform announcements.
- method ScreenReaderSupport._announce_windows(self, message: str) (L181): Announce text using Windows SAPI voice synthesizer if available.
- method ScreenReaderSupport._announce_macos(self, message: str) (L196): Unimplemented; debug-logged only.
- method ScreenReaderSupport._announce_linux(self, message: str) (L203): Unimplemented; debug-logged only.
- method ScreenReaderSupport.setup_accessible_descriptions(self) (L210): Annotate all descendants, then mark live regions and landmarks.
- method ScreenReaderSupport._setup_live_regions(self) (L228): Flag progress bars and status/progress labels as polite live regions.
- method ScreenReaderSupport._setup_landmarks(self) (L242): Tag the central widget as main and tab containers as navigation.
- method ScreenReaderSupport.set_focus_announcement(self, widget: QWidget, message: str) (L256): Announce ``message`` whenever ``widget`` gains focus.
- func ScreenReaderSupport.set_focus_announcement.on_focus_in() (L265): on_focus_in.
- method ScreenReaderSupport.create_accessible_table(self, table_widget: Any) (L275): Name headers and describe dimensions for assistive tech.
- method ScreenReaderSupport.create_accessible_tree(self, tree_widget: Any) (L296): Add a keyboard-navigation hint to the tree's description.
- method ScreenReaderSupport.announce_progress(self, percentage: int, message: str='') (L309): Throttled progress speech, emitted only at 10% multiples.
- method ScreenReaderSupport.announce_error(self, error_message: str) (L317): announce_changes wrapped with an 'Error:' prefix.
- method ScreenReaderSupport.announce_success(self, success_message: str) (L321): announce_changes wrapped with a 'Success:' prefix.
- method ScreenReaderSupport.get_accessibility_info(self) (L325): Capability report for diagnostics and UI toggles.

## src/cortex_unified/accessibility/themes.py — High contrast and accessibility themes for Cortex Cleaner.
- class AccessibilityThemes (L16): Applies light/dark/high-contrast palettes app-wide or per-widget.
- method AccessibilityThemes.__init__(self) (L19): Snapshot the startup palette as the default-restore target.
- method AccessibilityThemes.apply_high_contrast_theme(self, widget: Optional[QWidget]=None) (L30): Black background, white text, blue highlight scheme.
- method AccessibilityThemes.apply_dark_theme(self, widget: Optional[QWidget]=None) (L79): Charcoal surfaces, white text, blue accent.
- method AccessibilityThemes.apply_light_theme(self, widget: Optional[QWidget]=None) (L122): Light gray/white surfaces, black text, blue accent.
- method AccessibilityThemes.restore_default_theme(self, widget: Optional[QWidget]=None) (L165): Reinstate the palette snapshotted at construction.
- method AccessibilityThemes.get_available_themes(self) (L186): Theme id -> display name for settings pickers.
- method AccessibilityThemes.apply_theme(self, theme_name: str, widget: Optional[QWidget]=None) (L195): Dispatch on theme id; unknown ids log a warning.
- method AccessibilityThemes.get_current_theme(self) (L210): Active theme id.
- method AccessibilityThemes.is_high_contrast_enabled(self) (L214): True while high contrast is the active theme.
- func get_theme_manager() (L221): Return the shared AccessibilityThemes instance.
- func apply_accessibility_theme(theme_name: str, widget: Optional[QWidget]=None) (L228): Module-level convenience around the shared manager.

## src/cortex_unified/analyzers/__init__.py — Analyzers module for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/analyzers/advanced_disk_analyzer.py — Advanced Disk Analyzer — MFT fast scan, treemap/sunburst, cloud targets.
- class FileEntry (L105): Single file system entry from scanner.
- class FolderNode (L122): Aggregated folder node for visualization.
- method FolderNode.add_file(self, rel_path: str, size: int, ext: str) (L132): Add one file's size to this node and every intermediate folder node.
- method FolderNode.to_treemap(self, max_depth: int=8) (L149): Convert tree to flat list of hierarchy dictionaries for treemaps.
- func FolderNode.to_treemap.walk(node: 'FolderNode', depth: int=0) (L152): Emit one node dict, then recurse into children up to max_depth.
- method FolderNode.to_sunburst(self, max_depth: int=6) (L167): Convert tree to sunburst parent-child dictionary list.
- func FolderNode.to_sunburst.walk(node: 'FolderNode', depth: int=0, parent: str='') (L170): Emit id/parent/value rows for sunburst rings, recursing to max_depth.
- method FolderNode.to_bar_chart(self, top_n: int=20) (L184): Convert tree to top largest folders bar chart format.
- func FolderNode.to_bar_chart.walk(node: 'FolderNode') (L187): Collect non-root folder sizes for the bar chart ranking.
- method FolderNode.top_extensions(self, limit: int=10) (L198): Return top N file extensions by space consumed.
- class Scanner(ABC) (L207): Read-only filesystem scanner yielding FileEntry objects with cancellation and progress.
- method Scanner.__init__(self, cancel_event: Optional[threading.Event]=None, progress_cb: Optional[Callable[[int, int, str], None]]=None) (L209): Store the cancellation event and progress callback with zeroed counters.
- method Scanner.scan(self, root: str) (L219): Yield every FileEntry under root; implemented by each platform backend.
- method Scanner._check_cancel(self) (L224): True once the caller has signalled the cancel event.
- method Scanner._report(self, path: str) (L228): Count the file and invoke progress_cb every 100th entry.
- class NTFSScanner(Scanner) (L241): Fast NTFS scanner using direct MFT parsing via Windows API.
- method NTFSScanner.__init__(self, *args, **kwargs) (L244): Initialize and probe whether raw MFT/volume access is available.
- method NTFSScanner._check_mft_access(self) (L249): Test raw volume handle access via CreateFileW; needs Administrator.
- method NTFSScanner.scan(self, root: str) (L264): Yield entries via MFT parsing when available, else scandir fallback.
- method NTFSScanner._scan_mft(self, root: str) (L271): MFT fast path; currently delegates to the scandir walk.
- method NTFSScanner._scan_walk(self, root: str) (L275): Iterative scandir walk skipping symlinks and unreadable directories.
- class PosixScanner(Scanner) (L314): Linux/macOS scanner using iterative scandir with stat metadata.
- method PosixScanner.scan(self, root: str) (L316): Yield entries under root via an iterative scandir walk.
- class CloudScanner(Scanner) (L356): Cloud target scanner delegating to rclone ``lsf`` per configured remote.
- method CloudScanner.__init__(self, *args, providers: Optional[List[str]]=None, **kwargs) (L358): Store provider list and verify the rclone binary is usable.
- method CloudScanner._check_rclone(self) (L364): Run ``rclone version`` to confirm the binary works; no admin needed.
- method CloudScanner.scan(self, root: str) (L372): Scan each configured ``provider:`` remote, or a single ``root`` remote.
- method CloudScanner._scan_remote(self, remote: str) (L380): List a remote's files via ``rclone lsf`` and convert each line to FileEntry.
- class AdvancedDiskAnalyzer (L424): Disk usage analyzer that scans (local or cloud) and builds FolderNode trees for charts.
- method AdvancedDiskAnalyzer.__init__(self, include_cloud: bool=False, cloud_providers: Optional[List[str]]=None, cancel_event: Optional[threading.Event]=None, progress_cb: Optional[Callable[[int, int, str], None]]=None) (L426): Store cancellation/progress hooks and pick the platform or cloud scanner.
- method AdvancedDiskAnalyzer._create_scanner(self, include_cloud: bool, providers: Optional[List[str]]) (L439): Choose NTFS/Posix scanner by platform, or CloudScanner when cloud deps exist.
- method AdvancedDiskAnalyzer.async scan(self, root: str) (L455): Async wrapper that streams entries from the underlying sync scanner.
- method AdvancedDiskAnalyzer.build_tree(self, entries: List[FileEntry]) (L466): Fold all file entries into an aggregated FolderNode hierarchy.
- method AdvancedDiskAnalyzer.get_visualizations(self) (L478): Return treemap/sunburst/bar data plus extension and size totals from the last tree.
- method AdvancedDiskAnalyzer.get_stats(self) (L493): Return files and bytes counted by the scanner so far.
- func scan_sync(root: str, include_cloud: bool=False, progress_cb: Optional[Callable[[int, int, str], None]]=None, cancel_event: Optional[threading.Event]=None) (L514): Scan synchronously and return all entries plus the aggregated FolderNode tree.
- func scan_sync.async _collect() (L531): Append every streamed entry into the entries list.

## src/cortex_unified/analyzers/advanced_shredder.py — Advanced multi-pattern overwrite disk sanitization (DoD 5220.22-M style pass sequence).
- class ShredMethod(str, enum.Enum) (L23): Sanitization standards for secure data erasure.
- class AdvancedShredder (L36): Overwrites files with certified pass patterns before deletion.
- method AdvancedShredder.__init__(self) (L54): __init__.
- method AdvancedShredder._generate_pass_data(self, pattern: bytes | None, size: int) (L60): Generate byte pattern for a single chunk.
- method AdvancedShredder.shred_file(self, file_path: str, passes: int | None=None, method: Union[ShredMethod, str]=ShredMethod.DOD_5220_22_M) (L67): Overwrite *file_path* with the chosen sanitization pattern, then remove it.
- method AdvancedShredder.shred_directory(self, dir_path: str, passes: int | None=None, method: Union[ShredMethod, str]=ShredMethod.DOD_5220_22_M) (L148): Recursively shreds a directory and its contents.

## src/cortex_unified/analyzers/advanced_uninstaller.py — Advanced Uninstaller — Steam, Chocolatey, Winget, Store, portable, orphaned.
- class AppInfo (L87): Unified application representation.
- method AppInfo.to_dict(self) (L106): to_dict.
- class LeftoverScanResult (L115): LeftoverScanResult.
- method LeftoverScanResult.to_dict(self) (L127): to_dict.
- class UninstallResult (L137): UninstallResult.
- func _normalize_path(path: str) (L153): _normalize_path.
- func _get_registry_apps() (L160): Enumerate from HKLM/HKCU Uninstall keys.
- func _get_steam_apps() (L225): Parse Steam localconfig.vdf for installed games.
- func _get_chocolatey_apps() (L310): Enumerate Chocolatey packages.
- func _get_winget_apps() (L342): Enumerate Winget packages.
- func _get_scoop_apps() (L375): Enumerate Scoop packages.
- func _get_store_apps() (L407): Enumerate Windows Store (UWP) apps.
- func _get_windows_features() (L442): Enumerate Windows optional features.
- func _get_portable_apps() (L477): Scan common portable app locations.
- func _scan_leftovers(app: AppInfo, pre_snapshot: Dict[str, Set[str]]) (L530): Compare pre/post snapshots to find leftovers.
- class AdvancedUninstaller (L595): Multi-source uninstaller with leftover detection and forced uninstall.
- method AdvancedUninstaller.__init__(self, create_restore_point: bool=True, progress_callback: Optional[Callable[[str], None]]=None, cancel_event: Optional[threading.Event]=None) (L598): __init__.
- method AdvancedUninstaller.enumerate_all(self, force_refresh: bool=False) (L613): Enumerate apps from all sources.
- method AdvancedUninstaller.uninstall_batch(self, app_ids: List[str], force: bool=False, scan_leftovers: bool=True) (L651): Uninstall multiple apps with single restore point.
- method AdvancedUninstaller._uninstall_one(self, app: AppInfo, force: bool, scan_leftovers: bool) (L685): Uninstall one app. Returns (success, leftovers, duration, error).
- method AdvancedUninstaller._split_command(cmd: str) (L724): Split an uninstall string into argv, honouring quoted exes.
- method AdvancedUninstaller._run_uninstaller(self, cmd: str, app: AppInfo) (L747): Execute one uninstall command and report real success.
- method AdvancedUninstaller._forced_uninstall(self, app: AppInfo) (L803): Forced uninstall: remove the app's traces after killing it.
- method AdvancedUninstaller._remove_install_dir(self, app: AppInfo) (L825): Delete the app's install directory if it is safe to do so.
- method AdvancedUninstaller._kill_processes(self, name: str) (L873): _kill_processes.
- method AdvancedUninstaller._cleanup_registry_traces(self, app: AppInfo) (L883): Remove the app's own Uninstall entry and publisher-matched keys.
- method AdvancedUninstaller._cleanup_services_tasks(self, name: str) (L935): Remove the app's services and scheduled tasks.
- method AdvancedUninstaller._scan_leftovers_deep(self, app: AppInfo) (L987): Scan the standard per-app locations for surviving data.

## src/cortex_unified/analyzers/audio_duplicate_finder.py — Audio duplicate detection via acoustic fingerprinting (Chromaprint-inspired).
- func _build_band_edges() (L95): _build_band_edges.
- func _fft(mag: List[float]) (L120): Cooley-Tukey FFT for power-of-two real input (returns complex spectrum).
- func _magnitude_spectrum(frame: List[float]) (L151): Windowed FFT magnitude (Hann window, half spectrum).
- func _decode_wav(path: Path) (L167): Decode WAV to mono float samples in [-1, 1]; returns (samples, sr).
- func _resample(samples: List[float], sr_in: int, sr_out: int=_TARGET_SR) (L228): Simple linear resampling; preserves duration.
- func _decode_generic(path: Path) (L247): Try optional decoders for non-WAV; returns None if unavailable.
- func _band_energies(mag: List[float]) (L292): 33 log-spaced band energies (sum of squared magnitudes).
- func _subfingerprint_for_frame(energies: List[float], prev_energies: Optional[List[float]]) (L308): 32-bit subfingerprint for one frame (16 intra + 16 inter as in Chromaprint).
- func _fingerprint_from_samples(samples: List[float]) (L340): Compute sequence fingerprint (list of 32-bit subfingerprints).
- func _fallback_raw_fingerprint(path: Path) (L362): Format-agnostic fallback for non-WAV without decoders: byte-shingled.
- func compute_audio_fingerprint(path: Path | str) (L415): Compute Chromaprint-inspired acoustic fingerprint (sequence of 32-bit ints).
- func _hamming32(a: int, b: int) (L448): _hamming32.
- func audio_compare(fp_a: List[int], fp_b: List[int]) (L455): Similarity 0.0..1.0 between two fingerprints (higher = more similar).
- class AudioDuplicateFinder (L506): Find acoustically-similar audio groups (same recording, any encoding).
- method AudioDuplicateFinder.__init__(self, root_path: str | os.PathLike, threshold: float=0.75, config: Config | None=None) (L517): __init__.
- method AudioDuplicateFinder._should_exclude(self, path: Path) (L544): _should_exclude.
- method AudioDuplicateFinder._is_audio(self, path: Path) (L556): _is_audio.
- method AudioDuplicateFinder.find_audio_duplicates(self, threads: int=0, progress_callback: Optional[Callable[[str, int], None]]=None, cancel_event: Optional[threading.Event]=None) (L564): Scan roots and return acoustically-duplicate groups (size >= 2).
- func AudioDuplicateFinder.find_audio_duplicates._fp_one(p: Path) (L604): _fp_one.
- func AudioDuplicateFinder.find_audio_duplicates._find(x: Path) (L667): _find.
- func AudioDuplicateFinder.find_audio_duplicates._union(a: Path, b: Path) (L676): _union.
- method AudioDuplicateFinder.get_stats(self) (L704): get_stats.

## src/cortex_unified/analyzers/broken_link_detector.py — Enhanced broken link detector for Cortex Cleaner.
- class BrokenLink (L16): Base class for broken link information.
- class BrokenSymlink(BrokenLink) (L29): Information about a broken symlink.
- method BrokenSymlink.__post_init__(self) (L33): __post_init__.
- class BrokenShortcut(BrokenLink) (L40): Information about a broken Windows shortcut (.lnk file).
- method BrokenShortcut.__post_init__(self) (L46): __post_init__.
- class BrokenRegistryRef(BrokenLink) (L53): Information about a broken registry reference (Windows only).
- method BrokenRegistryRef.__post_init__(self) (L58): __post_init__.
- class RepairResult (L65): Result of a repair attempt.
- class RepairOutcome (L76): Per-item outcome of a :func:`repair` run.
- func _is_reparse_link(path: Path) (L84): True when *path* is itself a link (symlink or Windows junction).
- func _resolve_send2trash() (L102): Return ``send2trash`` or ``None`` when the package is unavailable.
- func repair(items, use_trash=True, dry_run=True) (L111): Safely clean up broken links found by a scan.
- class BrokenLinkDetector (L212): Detector for broken symlinks, shortcuts, and registry references.
- method BrokenLinkDetector.__init__(self, config: Config=None) (L215): Initialize broken link detector.
- method BrokenLinkDetector._setup_windows_modules(self) (L239): Set up Windows-specific modules for shortcut and registry handling.
- method BrokenLinkDetector._should_exclude_path(self, path: Path) (L261): Check if a path should be excluded based on patterns.
- method BrokenLinkDetector._get_file_stats(self, path: Path) (L281): Get file size and timestamps.
- method BrokenLinkDetector.scan_symlinks(self, path: str) (L292): Scan for broken symlinks in the given path.
- method BrokenLinkDetector.scan_windows_shortcuts(self, path: str) (L369): Scan for broken Windows shortcuts (.lnk files).
- method BrokenLinkDetector._analyze_shortcut(self, lnk_path: Path) (L433): Analyze a Windows shortcut file to extract target information.
- method BrokenLinkDetector._analyze_shortcut_basic(self, lnk_path: Path) (L475): Basic shortcut analysis without COM (limited functionality).
- method BrokenLinkDetector.scan_registry_references(self) (L506): Scan for broken registry references (Windows only).
- method BrokenLinkDetector._scan_registry_key(self, hkey, subkey_path: str) (L532): Scan a specific registry key for broken file references.
- method BrokenLinkDetector._extract_paths_from_string(self, text: str) (L577): Extract potential file paths from a string.
- method BrokenLinkDetector._assess_symlink_repairability(self, broken_link: BrokenSymlink) (L612): True when a plausible new target for the symlink exists.
- method BrokenLinkDetector._assess_shortcut_repairability(self, broken_shortcut: BrokenShortcut) (L621): True when a plausible new target for the shortcut exists.
- method BrokenLinkDetector._assess_registry_repairability(self, broken_ref: BrokenRegistryRef) (L626): Assess if a broken registry reference can potentially be repaired.
- method BrokenLinkDetector._calculate_confidence_score(self, broken_link: BrokenLink) (L632): Calculate confidence score for a broken link detection.
- method BrokenLinkDetector.find_moved_targets(self, original_target: str) (L658): Find potential new locations for a moved target using heuristics.
- method BrokenLinkDetector._get_search_locations(self, original_path: Path) (L695): Get prioritized list of locations to search for moved files.
- method BrokenLinkDetector.attempt_repair(self, broken_link: BrokenLink) (L750): attempt_repair.
- method BrokenLinkDetector._create_backup(self, original_path: Path) (L794): Create a backup of the original link before repair.
- method BrokenLinkDetector._repair_symlink(self, broken_link: BrokenSymlink, new_target: str, backup_result: Dict) (L820): Repair a broken symlink.
- method BrokenLinkDetector._repair_shortcut(self, broken_shortcut: BrokenShortcut, new_target: str, backup_result: Dict) (L844): Repair a broken Windows shortcut.
- method BrokenLinkDetector._repair_registry_ref(self, broken_ref: BrokenRegistryRef, new_target: str, backup_result: Dict) (L899): Repair a broken registry reference (not implemented for safety).
- method BrokenLinkDetector.categorize_broken_links(self, links: List[BrokenLink]) (L910): Categorize broken links by type and repairability.
- method BrokenLinkDetector.scan_all(self, path: str, progress=None, cancel_event=None, include_registry: bool=False) (L945): Scan for broken symlinks and shortcuts under the given folder.
- method BrokenLinkDetector._cancelled(self) (L988): _cancelled.
- method BrokenLinkDetector._emit(self, text: str) (L995): _emit.
- method BrokenLinkDetector.get_scan_statistics(self) (L1006): Get statistics about the last scan.

## src/cortex_unified/analyzers/cache_cleaner.py — Discovery of application caches and log files.
- class CacheCleaner (L17): Finds cache/log files and directories under the platform's cache roots.
- method CacheCleaner.__init__(self, config: Config=None) (L20): Args:
- method CacheCleaner._get_platform_cache_paths(self) (L124): Cache roots for this platform, deduplicated, existing ones only.
- method CacheCleaner.get_custom_scan_roots(self) (L162): Suggest user-selected roots for deeper sweeps.
- method CacheCleaner.is_archive(self, path: Path) (L195): True when *path* is a keep-as-backup archive (.zip/.tar.gz).
- method CacheCleaner._should_exclude_path(self, path: Path) (L202): True when *path* hits an excluded directory name or pattern.
- method CacheCleaner._is_cache_directory(self, path: Path) (L214): True when the directory name contains a known cache marker.
- method CacheCleaner._is_cache_file(self, path: Path) (L222): True when the file name matches a cache/log/build-artifact glob.
- method CacheCleaner.find_large_logs(self, roots: List[str] | List[Path], min_size_mb: float=100.0, exclude_archives: bool=True, progress_callback=None, cancel_event=None) (L232): Find large log/text files across user-selected roots (D:\code sweeper).
- func CacheCleaner.find_large_logs._is_log(name: str) (L258): _is_log.
- method CacheCleaner.find_cache_files(self, custom_paths: List[str]=None) (L312): Find cache and log files.
- method CacheCleaner.get_stats(self) (L380): Get statistics about the cache file finding process.
- method CacheCleaner._format_bytes(self, bytes_count: int) (L401): Format bytes into human-readable format.
- method CacheCleaner.get_cache_directories(self) (L409): Get list of cache directories that would be scanned.

## src/cortex_unified/analyzers/cloud_storage_analyzer.py — Cloud Storage Analyzer — rclone, S3, Azure, Google Drive, OneDrive, SharePoint.
- class CloudFileEntry (L75): Single cloud object entry.
- method CloudFileEntry.to_dict(self) (L90): Serialize this entry to a plain dict, with ``mtime`` as ISO-8601.
- class CloudScanStats (L101): Aggregate totals for one scan: sizes by class/provider, cost, errors.
- class DuplicateGroup (L117): Cross-cloud/local duplicate group.
- method DuplicateGroup.wasted_bytes(self) (L125): Bytes reclaimable if all but one copy of this group were removed.
- func _pricing_cache_dir() (L136): Return (creating if needed) the on-disk pricing cache directory.
- class PricingCatalog (L147): Storage pricing resolved at runtime from the provider's public API.
- method PricingCatalog.__init__(self, ttl_hours: int=168, timeout: int=20) (L157): Set the cache TTL in hours and the network timeout in seconds.
- method PricingCatalog._cache_file(self, provider: str, region: str) (L166): Filesystem path of the cache file for one provider/region pair.
- method PricingCatalog._read_cache(self, provider: str, region: str) (L173): Return cached rates for this pair, or ``None`` when missing, stale, or corrupt.
- method PricingCatalog._write_cache(self, provider: str, region: str, rates: Dict[str, float]) (L189): Persist rates with a fetch timestamp, silently ignoring filesystem errors.
- method PricingCatalog._http_json(self, url: str) (L201): GET a URL and parse the JSON response; return ``None`` on any failure.
- method PricingCatalog._fetch_aws(self, region: str) (L215): Fetch S3 per-GB-month storage rates from AWS's public Price List Query API.
- method PricingCatalog._fetch_azure(self, region: str) (L259): Fetch per-GB-month blob rates from Azure's unauthenticated Retail Prices API.
- method PricingCatalog.rates(self, provider: str, region: str) (L289): Return normalized class -> USD/GB/month, from cache or a live vendor fetch.
- method PricingCatalog.rate(self, provider: str, region: str, storage_class: str) (L306): Resolve one storage class to a USD/GB/month rate, or ``None`` if unknown.
- func _normalise_class(name: str) (L325): Fold vendor storage-class / meter names into a comparable key.
- class CloudProvider(ABC) (L341): Abstract cloud storage provider.
- method CloudProvider.__init__(self, config: Dict[str, Any]) (L347): Store config and derive the lowercase provider name from the class name.
- method CloudProvider.async list_objects(self, bucket: str, prefix: str='', max_keys: Optional[int]=None) (L355): Stream every object under a bucket/prefix as :class:`CloudFileEntry` items.
- method CloudProvider.region(self) (L367): Region used for pricing lookups, resolved from config or environment.
- method CloudProvider.estimate_cost(self, stats: CloudScanStats) (L377): Monthly USD estimate from live vendor rates for this provider only.
- method CloudProvider.validate_config(self) (L395): Hook for providers to reject bad config; base accepts everything.
- class S3Provider(CloudProvider) (L406): AWS S3 backend driven by boto3, listing object versions when available.
- method S3Provider.__init__(self, config: Dict[str, Any]) (L410): Initialize and create the boto3 S3 client from config/environment.
- method S3Provider._init_client(self) (L419): Build the boto3 client, letting boto3 fall back to env/IAM/SSO credentials.
- method S3Provider.region(self) (L448): The bucket-resolved region if known, else the inherited default.
- method S3Provider._bucket_region(self, bucket: str) (L455): Query GetBucketLocation for the bucket's region; ``None`` on failure.
- method S3Provider.async list_objects(self, bucket: str, prefix: str='', max_keys: Optional[int]=None) (L473): Stream S3 objects, preferring versioned listing to surface billable old versions.
- method S3Provider.estimate_cost(self, stats: CloudScanStats) (L526): estimate_cost.
- class AzureBlobProvider(CloudProvider) (L538): Azure Blob backend via BlobServiceClient (connection string or token auth).
- method AzureBlobProvider.__init__(self, config: Dict[str, Any]) (L542): Initialize and create the BlobServiceClient from config/environment.
- method AzureBlobProvider._init_client(self) (L551): Build the BlobServiceClient from a connection string, account URL, or DefaultAzureCredential.
- method AzureBlobProvider.region(self) (L577): Resolved ARM region for pricing, from config or the account information.
- method AzureBlobProvider.async list_objects(self, container: str, prefix: str='', max_keys: Optional[int]=None) (L598): Stream container blobs with metadata, tags, and versions where enabled.
- method AzureBlobProvider.estimate_cost(self, stats: CloudScanStats) (L641): Delegate to the base class cost estimate using Azure live rates.
- class GoogleDriveProvider(CloudProvider) (L652): Google Drive listing via the Drive v3 REST API.
- method GoogleDriveProvider.__init__(self, config: Dict[str, Any]) (L664): Store config and resolve the Drive OAuth access token.
- method GoogleDriveProvider._get(self, params: Dict[str, str]) (L673): Issue an authorized Drive v3 GET; return parsed JSON or ``None``.
- method GoogleDriveProvider.async list_objects(self, bucket: str='root', prefix: str='', max_keys: Optional[int]=None) (L690): Stream non-trashed Drive files in a folder, skipping size-less native docs.
- class OneDriveProvider(CloudProvider) (L752): OneDrive / SharePoint listing via Microsoft Graph ``/children``.
- method OneDriveProvider.__init__(self, config: Dict[str, Any]) (L763): Store config and resolve the Microsoft Graph access token.
- method OneDriveProvider._get(self, url: str) (L772): Issue an authorized Graph GET; return parsed JSON or ``None``.
- method OneDriveProvider.async list_objects(self, bucket: str='me/drive', prefix: str='', max_keys: Optional[int]=None) (L788): Stream non-folder drive items via Graph ``/children`` pages.
- class RcloneProvider(CloudProvider) (L840): Any of rclone's 40+ backends via ``rclone lsjson``.
- method RcloneProvider.__init__(self, config: Dict[str, Any]) (L850): Store config, remote name, and locate the rclone binary.
- method RcloneProvider._locate_binary(explicit: Optional[str]) (L859): Find rclone via explicit hint, ``RCLONE_BINARY``, or ``PATH``.
- method RcloneProvider.available(self) (L873): Whether a usable rclone binary was found.
- method RcloneProvider.list_remotes(self) (L879): Configured rclone remotes, so callers never guess a remote name.
- method RcloneProvider.async list_objects(self, bucket: str='', prefix: str='', max_keys: Optional[int]=None) (L892): Run ``rclone lsjson`` recursively and stream each file as an entry.
- method RcloneProvider.estimate_cost(self, stats: CloudScanStats) (L944): Return 0.0: pricing belongs to the backend's native provider class.
- class CloudStorageAnalyzer (L956): Unified cloud storage analyzer with multi-provider support.
- method CloudStorageAnalyzer.__init__(self, default_provider: str='rclone', provider_configs: Optional[Dict[str, Dict]]=None, cancel_event: Optional[threading.Event]=None, progress_cb: Optional[Callable[[int, int, str], None]]=None) (L967): Set up cancellation, progress callbacks, and instantiate all providers.
- method CloudStorageAnalyzer._init_providers(self, default: str) (L983): Instantiate every provider (skipping ones that fail) and pick the default.
- method CloudStorageAnalyzer.get_provider(self, name: str) (L996): Return the instantiated provider by name, or ``None``.
- method CloudStorageAnalyzer.available_targets(self) (L1002): Enumerate what this machine can actually scan.
- method CloudStorageAnalyzer.async scan(self, target: str, max_objects: Optional[int]=None) (L1037): Scan cloud target. target format: 's3://bucket/prefix' or 'rclone://remote/path'.
- method CloudStorageAnalyzer.scan_sync(self, target: str, max_objects: Optional[int]=None, progress_cb: Optional[Callable[[int, int, str], None]]=None, cancel_event: Optional[threading.Event]=None) (L1074): Synchronous scan returning all entries and stats.
- func CloudStorageAnalyzer.scan_sync.async _collect() (L1090): Accumulate entries and per-class/provider stats from the scan stream.
- method CloudStorageAnalyzer.find_duplicates(self, entries: List[CloudFileEntry], local_hashes: Optional[Dict[str, List[str]]]=None) (L1117): Group objects that share a content hash, optionally including local files.
- method CloudStorageAnalyzer.generate_report(self, entries: List[CloudFileEntry], stats: CloudScanStats, duplicates: Optional[List[DuplicateGroup]]=None) (L1157): Self-contained HTML report with a per-class cost breakdown.

## src/cortex_unified/analyzers/content_defined_chunker.py — Content-Defined Chunking (FastCDC / VectorCDC) for deduplication acceleration.
- func _build_gear_table(seed: int=11400714819323198485) (L77): _build_gear_table.
- func _mask_for_avg(avg: int) (L87): Mask with probability 1/avg (avg assumed power-of-two-ish).
- class Chunk (L102): Chunk.
- method Chunk.to_dict(self) (L108): to_dict.
- class ChunkStats (L116): ChunkStats.
- func _chunk_hash(data: bytes) (L130): _chunk_hash.
- func gear_chunk(data: bytes, avg_size: int=8192, min_size: int=2048, max_size: int=65536) (L138): Content-defined chunking via Gear (FastCDC §3).
- func file_chunks(path: Path | str, avg_size: int=8192, min_size: int=2048, max_size: int=65536, cap_bytes: int=16 * 1024 * 1024) (L190): Chunk a file (streamed, bounded).
- func jaccard(a: Iterable[int], b: Iterable[int]) (L205): Jaccard similarity of two fingerprint sets (0..1).
- func chunk_similarity(data_a: bytes, data_b: bytes, avg_size: int=8192, min_size: int=2048, max_size: int=65536) (L216): CDC-Jaccard similarity between two byte strings (1.0 = identical).
- class ContentDefinedChunker (L232): Find shift-resistant near-duplicate files via CDC chunk sets.
- method ContentDefinedChunker.__init__(self, root_path: str | os.PathLike, threshold: float=0.5, avg_size: int=8192, min_size: int=2048, max_size: int=65536, config=None) (L246): __init__.
- method ContentDefinedChunker._should_exclude(self, path: Path) (L280): _should_exclude.
- method ContentDefinedChunker.find_cdc_duplicates(self, threads: int=0, progress_callback: Optional[Callable[[str, int], None]]=None, cancel_event: Optional[threading.Event]=None) (L292): find_cdc_duplicates.
- func ContentDefinedChunker.find_cdc_duplicates._one(p: Path) (L337): _one.
- func ContentDefinedChunker.find_cdc_duplicates._find(x: Path) (L388): _find.
- func ContentDefinedChunker.find_cdc_duplicates._union(a: Path, b: Path) (L397): _union.
- method ContentDefinedChunker.get_stats(self) (L425): get_stats.
- func vector_cdc_chunk(data: bytes | bytearray | memoryview, avg_size: int=8192, min_size: int=2048, max_size: int=65536) (L444): VectorCDC (FAST'25) accelerated content-defined chunking.
- class IdeaInvertedIndex (L495): IDEA: Inverted Deduplication-Aware Index (FAST '24).
- method IdeaInvertedIndex.__init__(self) (L500): __init__.
- method IdeaInvertedIndex.insert(self, path: Path, chunks: Iterable[Chunk]) (L507): insert.
- method IdeaInvertedIndex.find_similar(self, path: Path, threshold: float=0.5) (L516): Find files sharing chunks with `path` exceeding Jaccard `threshold`.

## src/cortex_unified/analyzers/czkawka_tools.py — Czkawka multi-tool suite — empty, broken, bad-ext, bad-names, exif, video-optimizer.
- func _temp_dirs() (L62): _temp_dirs.
- func _sniff_extension(path: Path) (L112): _sniff_extension.
- class EmptyResult (L135): Empty scan result with empty files, folders, and scan stats.
- class EmptyFinder (L142): Walk a root tree collecting zero-byte files and empty folders.
- method EmptyFinder.__init__(self, root: str | os.PathLike, config: Config | None=None) (L144): __init__.
- method EmptyFinder.find(self, cancel: threading.Event | None=None, progress: Callable[[str], None] | None=None) (L152): Collect empty files then empty folders under the root.
- class SymlinkResult (L194): Broken-symlink scan result with link targets and scan stats.
- class InvalidSymlinkFinder (L200): Walk a root tree collecting symlinks whose targets no longer exist.
- method InvalidSymlinkFinder.__init__(self, root: str | os.PathLike, config: Config | None=None) (L202): __init__.
- method InvalidSymlinkFinder.find(self, cancel: threading.Event | None=None, progress: Callable[[str], None] | None=None) (L210): Collect symlinks whose resolved targets are missing.
- class BrokenFileFinder (L239): Detect corrupt images, archives, and PDFs via content verification.
- method BrokenFileFinder.__init__(self, root: str | os.PathLike, config: Config | None=None) (L241): __init__.
- method BrokenFileFinder._is_broken(self, p: Path) (L249): _is_broken.
- method BrokenFileFinder.find(self, threads: int=0, cancel: threading.Event | None=None, progress: Callable[[str], None] | None=None) (L282): Check every file under the root returning paths that fail verification.
- func BrokenFileFinder.find.check(p: Path) (L296): check.
- class BadExtResult (L319): One file whose sniffed content type disagrees with its extension.
- class BadExtensionFinder (L325): Compare each file's magic-byte type against its claimed extension.
- method BadExtensionFinder.__init__(self, root: str | os.PathLike, config: Config | None=None) (L327): __init__.
- method BadExtensionFinder.find(self, cancel: threading.Event | None=None, progress: Callable[[str], None] | None=None) (L335): Return files whose sniffed extension differs from the file suffix.
- class BadNamesFinder (L371): Collect files and folders with illegal, reserved, or overlong names.
- method BadNamesFinder.__init__(self, root: str | os.PathLike, config: Config | None=None) (L373): __init__.
- method BadNamesFinder.find(self, cancel: threading.Event | None=None) (L381): Return paths whose names match control-char or reserved patterns.
- class ExifCleaner (L397): Scan images for EXIF metadata and strip it to protect privacy.
- method ExifCleaner.__init__(self, root: str | os.PathLike, config: Config | None=None) (L399): __init__.
- method ExifCleaner.scan(self, cancel: threading.Event | None=None) (L406): List JPEG/TIFF/WebP files that still carry EXIF metadata.
- method ExifCleaner.strip(self, paths: List[Path]) (L435): Remove EXIF metadata from the given images reporting per-file success.
- class TempFileFinder (L465): Locate temp/log/backup files under a root or system temp dirs.
- method TempFileFinder.__init__(self, root: str | os.PathLike | None=None, config: Config | None=None) (L467): __init__.
- method TempFileFinder.find(self, cancel: threading.Event | None=None) (L474): find.
- class VideoInfo (L504): VideoInfo.
- class VideoOptimizer (L517): VideoOptimizer.
- method VideoOptimizer.find_static_borders(self, video: Path) (L519): find_static_borders.
- method VideoOptimizer.optimize(self, video: Path, out: Path | None=None, crf: int=28, preset: str='fast') (L547): Re-encode with libx264, crop static borders if detected.

## src/cortex_unified/analyzers/deep_cleaner.py — Cross-platform "deep clean" discovery over per-OS target tables.
- func get_path_size_safe(path: Path) (L19): Recursive byte size of *path*; 0 for anything unreadable.
- class DeepCleaner (L39): Finds temp files, caches, and orphaned app data across platforms.
- method DeepCleaner.__init__(self, config: Config=None) (L42): Args:
- method DeepCleaner._find_orphaned_app_data(self) (L51): Find app data folders for apps that are no longer installed.
- method DeepCleaner._get_scan_targets(self) (L165): Declarative scan table for the current platform.
- method DeepCleaner.find_junk(self, progress_callback=None) (L217): Run every platform target and return one record per finding.
- method DeepCleaner.get_stats(self) (L273): get_stats.
- method DeepCleaner._format_bytes(self, bytes_count: int) (L284): _format_bytes.

## src/cortex_unified/analyzers/disk_analyzer.py — Disk space analysis: volume usage, tree breakdown, per-extension stats.
- class DiskAnalyzer (L17): Analyzes disk usage and directory composition under a root.
- method DiskAnalyzer.__init__(self, config: Config=None, root_path: str='.') (L20): Args:
- method DiskAnalyzer._should_exclude_path(self, path: Path) (L38): True when *path* hits an excluded directory name or pattern.
- method DiskAnalyzer.analyze_disk_usage(self) (L50): Volume-level totals for the root path's drive.
- method DiskAnalyzer.analyze_directory_tree(self, max_depth: int=3) (L87): Build a bounded-depth tree with sizes rolled up to each parent.
- method DiskAnalyzer._analyze_directory_recursive(self, path: Path, max_depth: int, current_depth: int) (L98): Build one tree node; child sizes roll up into their parent.
- method DiskAnalyzer.analyze_file_types(self) (L150): Analyze files by type/extension.
- method DiskAnalyzer.find_largest_directories(self, limit: int=10) (L203): Return the *limit* biggest directories by direct file content.
- method DiskAnalyzer.get_stats(self) (L244): Get comprehensive statistics about the disk analysis.
- method DiskAnalyzer._format_bytes(self, bytes_count: int) (L279): Format bytes into human-readable format.
- method DiskAnalyzer.export_to_json(self, filepath: str) (L287): Export analysis results to JSON file.

## src/cortex_unified/analyzers/docker_cleaner.py — Scans a local Docker daemon for reclaimable resources (images, stopped
- class DockerImage (L26): An image flagged as dangling or referenced by no container.
- method DockerImage.__str__(self) (L35): __str__.
- class DockerContainer (L42): A non-running container eligible for removal.
- method DockerContainer.__str__(self) (L51): __str__.
- class DockerVolume (L58): A volume not mounted by any container.
- method DockerVolume.__str__(self) (L66): __str__.
- class DockerNetwork (L73): A user-defined network with no attached containers.
- method DockerNetwork.__str__(self) (L80): __str__.
- class CleanupResult (L87): Outcome of a cleanup pass; counts include dry-run simulations.
- method CleanupResult.total_removed(self) (L97): total_removed.
- class DockerCleaner (L103): Finds and removes reclaimable Docker resources via the Docker SDK.
- method DockerCleaner.__init__(self, config: Config=None) (L111): Initialize state; the Docker client itself connects lazily.
- method DockerCleaner.client(self) (L130): Return a connected ``docker.DockerClient``, creating it on first use.
- method DockerCleaner.is_docker_available(self) (L150): Check if Docker is available and running.
- method DockerCleaner.scan_unused_images(self) (L167): Collect images that are dangling or referenced by no container.
- method DockerCleaner.scan_stopped_containers(self) (L221): Collect containers that are not currently running.
- method DockerCleaner.scan_unused_volumes(self) (L262): Collect volumes not mounted by any container.
- method DockerCleaner.scan_unused_networks(self) (L302): Collect user-defined networks with no attached containers.
- method DockerCleaner.cleanup_resources(self, resources: List[Union[DockerImage, DockerContainer, DockerVolume, DockerNetwork]], dry_run: bool=True) (L342): Remove the given resources, or simulate removal when dry_run.
- method DockerCleaner.get_filesystem_cache_size(self) (L408): Fallback: measure Docker Desktop's on-disk cache under AppData\Local\Docker.
- method DockerCleaner.get_space_usage(self) (L445): Get Docker space usage information (SDK + filesystem fallback).
- method DockerCleaner.get_stats(self) (L471): Return a snapshot copy of cumulative scan counters.
- method DockerCleaner._is_image_unused(self, image_id: str) (L475): True if no container references the image; False on API errors (fail-safe).
- method DockerCleaner._is_volume_orphaned(self, volume_name: str) (L486): True if no container mounts the volume; False on API errors (fail-safe).
- method DockerCleaner._is_network_unused(self, network_id: str) (L499): True if the network reports zero attached containers; False on errors.
- method DockerCleaner._get_container_size(self, container) (L508): Approximate container size in bytes.
- method DockerCleaner._get_volume_size(self, volume) (L524): Approximate volume size in bytes.
- method DockerCleaner._format_bytes(self, bytes_size: int) (L551): Render a byte count using the largest fitting binary unit.

## src/cortex_unified/analyzers/duplicate_finder.py — Hash-based duplicate file detection.
- func _gear_hash(data: bytes) (L37): Lightweight Gear rolling hash (FastCDC §3.1) – table-less variant.
- func fastcdc_chunk(data: bytes, min_size: int=FCDC_MIN, avg_size: int=FCDC_AVG, max_size: int=FCDC_MAX) (L49): FastCDC content-defined chunking (paper Algorithm 1).
- func _fsb_hash(chunk: bytes) (L86): FSB-like lightweight syndrome hash (Hybrid paper §3.2).
- class DuplicateFinder (L97): Finds duplicate files via size grouping followed by content hashing.
- method DuplicateFinder.__init__(self, config: Config=None, root_path: str='.') (L100): Args:
- method DuplicateFinder._should_exclude_path(self, path: Path) (L125): True when *path* hits an excluded directory name or pattern.
- method DuplicateFinder._get_file_hash(self, filepath: Path) (L137): Content hash of *filepath*, or None when unreadable.
- method DuplicateFinder._get_file_size(self, filepath: Path) (L191): Size in bytes, or -1 when the file cannot be stat'ed.
- method DuplicateFinder._find_files_by_size(self) (L198): Group files by exact size; only sizes shared by 2+ files survive.
- method DuplicateFinder.find_duplicates(self, threads: int=0) (L240): Return ``{hash: [paths]}`` for groups of 2+ identical files.
- method DuplicateFinder.get_stats(self) (L274): Get statistics about the duplicate finding process.
- method DuplicateFinder._calculate_potential_savings(self) (L287): Calculate potential bytes that could be saved by removing duplicates.
- method DuplicateFinder.auto_select_duplicates(self, strategy: str='keep_newest') (L300): Pick the redundant copies from each duplicate group.
- method DuplicateFinder._format_bytes(self, size: int) (L332): Format bytes to human-readable string.
- method DuplicateFinder.get_hash_algorithm_info(self) (L340): Get information about the current hash algorithm.
- method DuplicateFinder._fastcdc_chunks(self, data: bytes, min_size: int=2048, avg_size: int=8192, max_size: int=16384) (L353): Content-defined chunking via FastCDC (Gear rolling hash).
- method DuplicateFinder._fsb_hash(self, chunk: bytes) (L408): Lightweight FSB-like hash (syndrome-based).
- method DuplicateFinder.find_duplicates_chunked(self, min_chunk: int=2048, avg_chunk: int=8192, max_chunk: int=16384, threads: int=0, progress_callback=None, cancel_event=None) (L419): Chunk-level deduplication via FastCDC + FSB hybrid.
- func DuplicateFinder.find_duplicates_chunked._process_file(p: Path) (L470): _process_file.
- method DuplicateFinder.get_chunked_stats(self, dup_chunks: Dict[str, List[Tuple[Path, int, int]]]) (L509): Stats for chunked dedup.

## src/cortex_unified/analyzers/duplicate_folder_finder.py — Content-identical folder detection.
- class DuplicateFolderFinder (L19): Finds folders whose contents are byte-for-byte identical.
- method DuplicateFolderFinder.__init__(self, config: Config=None, root_path: str='.') (L22): Args:
- method DuplicateFolderFinder._should_exclude_path(self, path: Path) (L42): True when *path* hits an excluded directory name or pattern.
- method DuplicateFolderFinder._get_folder_hash(self, folderpath: Path) (L54): Order-independent content fingerprint of *folderpath*.
- method DuplicateFolderFinder.find_duplicate_folders(self, threads: int=0, progress=None, cancel_event=None) (L104): Find folders with identical content.
- func DuplicateFolderFinder.find_duplicate_folders._cancelled() (L116): _cancelled.
- func DuplicateFolderFinder.find_duplicate_folders._emit(text: str) (L122): _emit.
- method DuplicateFolderFinder.get_stats(self) (L193): Get statistics about the duplicate folder finding process.
- method DuplicateFolderFinder.auto_select_folders(self, strategy: str='keep_first') (L205): Pick the redundant folder from each duplicate group.

## src/cortex_unified/analyzers/file_shredder.py — Overwrite-based file shredding.
- class FileShredder (L18): Securely deletes files by overwriting contents before unlinking.
- method FileShredder.__init__(self, config: Config=None) (L21): Args:
- method FileShredder._generate_random_data(self, size: int) (L34): _generate_random_data.
- method FileShredder._generate_pattern_data(self, size: int, pattern: int) (L40): _generate_pattern_data.
- method FileShredder.shred_file(self, filepath: Path, passes: int=None, allow_system_files: bool=False) (L46): Overwrite *filepath* in place, then unlink it.
- method FileShredder.shred_files(self, filepaths: List[Path], passes: int=None) (L122): Securely delete multiple files.
- method FileShredder.get_stats(self) (L150): Get statistics about the shredding process.
- method FileShredder.set_passes(self, passes: int) (L158): Set the number of overwrite passes.
- method FileShredder.verify_deletion(self, verify: bool) (L164): Set whether to verify file deletion.

## src/cortex_unified/analyzers/fuzzy_finder.py — Fuzzy (similarity, not exact) file hashing via CTPH / TLSH-style digests.
- func _fnv1a(data: bytes) (L98): _fnv1a.
- func _chunk_hash(chunk: bytes) (L109): _chunk_hash.
- func _to_char(values: int) (L118): _to_char.
- func _ctph_blocks(data: bytes, block_size: int) (L125): Context-triggered piecewise hashing at one block size (Kornblum 2006).
- func fuzzy_hash_bytes(data: bytes, block_size: int=64) (L162): Return an ssdeep-style CTPH signature for *data*.
- func fuzzy_hash_file(path: Path, block_size: int=64) (L177): Fuzzy-hash an entire file (streamed, bounded like ssdeep's 0–64 bases).
- func _edit_distance(a: str, b: str) (L192): Levenshtein distance between two signature fragments.
- func fuzzy_compare(sig1: str, sig2: str) (L207): Similarity score 0..100 between two CTPH signatures (higher = closer).
- func _parse(sig: str) (L218): _parse.
- func _compare_pair(a: str, b: str) (L233): _compare_pair.
- func _score_frag(a: str, b: str) (L252): _score_frag.
- class FuzzyDuplicateFinder (L274): Find near-identical *binary/content* files via CTPH similarity.
- method FuzzyDuplicateFinder.__init__(self, root_path: str | os.PathLike, threshold: float=60.0, block_size: int=64, config: Config | None=None) (L285): __init__.
- method FuzzyDuplicateFinder._should_exclude(self, path: Path) (L312): _should_exclude.
- method FuzzyDuplicateFinder._eligible(self, path: Path) (L324): _eligible.
- method FuzzyDuplicateFinder.find_fuzzy_duplicates(self, threads: int=0, progress_callback: Optional[Callable[[str, int], None]]=None, cancel_event: Optional[threading.Event]=None) (L332): Return groups (size >= 2) of files whose fuzzy similarity reaches the
- func FuzzyDuplicateFinder.find_fuzzy_duplicates._hash_one(p: Path) (L372): _hash_one.
- func FuzzyDuplicateFinder.find_fuzzy_duplicates._find(x: Path) (L414): _find.
- func FuzzyDuplicateFinder.find_fuzzy_duplicates._union(a: Path, b: Path) (L423): _union.
- method FuzzyDuplicateFinder.get_stats(self) (L451): get_stats.

## src/cortex_unified/analyzers/large_file_finder.py — Discovery of files above a configurable size threshold.
- func is_ai_model(path: Path) (L26): True when *path* looks like an LLM / diffusion model file.
- class LargeFileFinder (L31): Finds files larger than a size threshold under a root directory.
- method LargeFileFinder.__init__(self, config: Config=None, root_path: str='.') (L34): Args:
- method LargeFileFinder._should_exclude_path(self, path: Path) (L56): True when *path* hits an excluded directory name or pattern.
- method LargeFileFinder._get_file_size(self, filepath: Path) (L68): Size in bytes, or -1 when the file cannot be stat'ed.
- method LargeFileFinder.find_large_files(self, min_size_mb: int=None, threads: int=0) (L75): Find files larger than the specified size threshold.
- method LargeFileFinder.get_stats(self) (L133): Get statistics about the large file finding process.
- method LargeFileFinder._format_bytes(self, bytes_count: int) (L149): Format bytes into human-readable format.
- method LargeFileFinder.filter_by_size(self, min_size_mb: int, max_size_mb: int=None) (L157): Filter large files by size range.
- method LargeFileFinder.group_by_extension(self) (L173): Group large files by file extension.
- method LargeFileFinder.group_by_ai_models(self) (L185): Split large files into ``ai_models`` vs ``other`` for UI surfacing.
- method LargeFileFinder.get_ai_models(self, min_size_mb: int=100) (L200): Return only AI model files among large files (for HIGH-risk UI).
- method LargeFileFinder.tag_file(self, path: Path) (L205): Return a display tag for a large file (ai_models, video, archive, etc.).

## src/cortex_unified/analyzers/leftover_detector.py — Advanced heuristics and leftover detection for Cortex Cleaner.
- class DetectedItem (L25): Base class for detected leftover items.
- method DetectedItem.to_dict(self) (L35): to_dict.
- class OrphanedFolder(DetectedItem) (L45): Represents an orphaned application folder.
- method OrphanedFolder.__post_init__(self) (L53): Set item type after initialization.
- class InstallerFile(DetectedItem) (L58): Represents a detected installer file.
- method InstallerFile.__post_init__(self) (L65): Set item type after initialization.
- class RegistryOrphan(DetectedItem) (L70): Represents an orphaned registry entry (Windows only).
- method RegistryOrphan.__post_init__(self) (L77): Set item type after initialization.
- class CleanupRecommendation (L82): Represents a cleanup recommendation with risk assessment.
- class LeftoverDetector (L91): Advanced heuristics and leftover detection system.
- method LeftoverDetector.__init__(self, config: Config=None) (L94): __init__.
- method LeftoverDetector._setup_installation_paths(self) (L123): Set up common installation paths for different platforms.
- method LeftoverDetector._load_detection_patterns(self) (L161): Load ML patterns and heuristics for leftover detection.
- method LeftoverDetector.scan_orphaned_folders(self, paths: List[str]=None) (L221): Scan for orphaned application folders in common installation paths.
- method LeftoverDetector._scan_directory_for_orphans(self, directory: Path) (L246): Scan a specific directory for orphaned folders.
- method LeftoverDetector._is_system_directory(self, path: Path) (L276): Check if a directory is a system directory that should be skipped.
- method LeftoverDetector._analyze_folder_for_orphan_signs(self, folder: Path) (L286): Analyze a folder for signs that it might be an orphan.
- method LeftoverDetector._folder_appears_abandoned(self, folder: Path) (L322): Check if a folder appears to be abandoned.
- method LeftoverDetector._contains_uninstaller_remnants(self, folder: Path) (L343): Check if folder contains uninstaller remnants.
- method LeftoverDetector._create_orphaned_folder_object(self, folder: Path, confidence: float) (L355): Create an OrphanedFolder object from analysis results.
- method LeftoverDetector._determine_installation_path_type(self, folder: Path) (L392): Determine the type of installation path.
- method LeftoverDetector._contains_executables(self, folder: Path) (L409): Check if folder contains executable files.
- method LeftoverDetector._contains_config_files(self, folder: Path) (L420): Check if folder contains configuration files.
- method LeftoverDetector._contains_data_files(self, folder: Path) (L435): Check if folder contains data files.
- method LeftoverDetector._calculate_folder_size(self, folder: Path) (L446): Calculate total size of folder in bytes.
- method LeftoverDetector._extract_app_name(self, folder_name: str) (L460): Extract application name from folder name.
- method LeftoverDetector.detect_installer_files(self, paths: List[str]=None) (L468): detect_installer_files.
- method LeftoverDetector._scan_for_installer_files(self, directory: Path, installer_extensions: set) (L515): Scan directory for installer files.
- method LeftoverDetector._analyze_installer_file(self, file_path: Path) (L538): Analyze a potential installer file.
- method LeftoverDetector._check_installer_duplicate(self, file_path: Path) (L574): Check if installer file is a duplicate (simplified implementation).
- method LeftoverDetector._extract_version_from_filename(self, filename: str) (L587): Extract version number from filename.
- method LeftoverDetector._calculate_installer_confidence(self, file_path: Path, size_bytes: int) (L604): Calculate confidence score for installer file detection.
- method LeftoverDetector.analyze_registry_orphans(self) (L622): Analyze Windows registry for orphaned entries.
- method LeftoverDetector._analyze_registry_key(self, hive, hive_name: str, key_path: str) (L647): Analyze a specific registry key for orphaned entries.
- method LeftoverDetector._check_registry_subkey_for_orphans(self, hive, hive_name: str, full_key_path: str, subkey_name: str) (L669): Check a registry subkey for orphaned file references.
- method LeftoverDetector._create_registry_orphan(self, registry_key: str, hive: str, referenced_path: str, key_type: str) (L696): Create a RegistryOrphan object.
- method LeftoverDetector.apply_ml_patterns(self, items: List[DetectedItem]) (L720): Apply machine learning patterns to improve detection accuracy.
- method LeftoverDetector._apply_pattern_adjustments(self, item: DetectedItem) (L767): Apply pattern-based adjustments to confidence score.
- method LeftoverDetector.calculate_confidence_score(self, item: DetectedItem) (L793): Calculate overall confidence score for a detected item.
- method LeftoverDetector.generate_cleanup_recommendations(self, confidence_threshold: float=0.7) (L797): Generate cleanup recommendations based on detected items.
- method LeftoverDetector.export_results(self, filepath: str) (L849): Export detection results to JSON file.
- method LeftoverDetector.get_stats(self) (L871): Get detection statistics.

## src/cortex_unified/analyzers/near_duplicate_finder.py — Near-duplicate detection via MinHash LSH + Bloom filtering.
- class BloomFilter (L72): Simple Bloom filter with k hash functions.
- method BloomFilter.__init__(self, n: int, p: float=0.01, k: int=7) (L79): __init__.
- method BloomFilter._hashes(self, data: bytes) (L91): _hashes.
- method BloomFilter.add(self, data: bytes) (L107): add.
- method BloomFilter.__contains__(self, data: bytes) (L115): __contains__.
- method BloomFilter.fpr(self) (L124): Theoretical false-positive rate after n insertions.
- func _shingle_text(text: str, k: int=5) (L133): Character k-grams (shingles) from text, lower-cased, whitespace-normalized.
- func _shingle_bytes(data: bytes, k: int=5) (L146): Byte-level shingles for binary / mixed files.
- func _hash_shingle(shingle: bytes, seed: int) (L153): _hash_shingle.
- class NearDuplicateFinder (L163): Near-duplicate finder via MinHash LSH + Bloom pre-screen.
- method NearDuplicateFinder.__init__(self, root_path: str='.', threshold: float=0.8, shingle_k: int=5, hash_perm: int=128, bands: int=16, use_bloom: bool=True, config: Config | None=None) (L176): __init__.
- method NearDuplicateFinder._should_exclude(self, path: Path) (L209): _should_exclude.
- method NearDuplicateFinder._is_text(self, path: Path) (L221): _is_text.
- method NearDuplicateFinder._minhash(self, shingles: Set[bytes]) (L232): MinHash signature length H: min_{shingle} h_perm(shingle).
- method NearDuplicateFinder._lsh_candidates(self, signatures: Dict[Path, List[int]]) (L244): Band-hashing (LSH) to generate candidate pairs without O(n²).
- method NearDuplicateFinder._jaccard(self, a: Set[bytes], b: Set[bytes]) (L272): _jaccard.
- method NearDuplicateFinder._weighted_jaccard(self, a: Set[bytes], b: Set[bytes], df: Dict[bytes, int], n_docs: int) (L282): Attention-weighted Jaccard (SemHash AW-MinHash): down-weight boilerplate.
- method NearDuplicateFinder.find_near_duplicates(self, threads: int=0, progress_callback=None, cancel_event=None) (L306): Find near-duplicate groups.
- func NearDuplicateFinder.find_near_duplicates._shingle_one(p: Path) (L370): _shingle_one.
- func NearDuplicateFinder.find_near_duplicates._minhash_one(item: Tuple[Path, Set[bytes]]) (L411): _minhash_one.
- func NearDuplicateFinder.find_near_duplicates._find(x: Path) (L432): _find.
- func NearDuplicateFinder.find_near_duplicates._union(a: Path, b: Path) (L441): _union.
- method NearDuplicateFinder.get_stats(self) (L477): Stats akin to DuplicateFinder.

## src/cortex_unified/analyzers/old_file_cleaner.py — Discovery of files untouched for a configurable number of days.
- class OldFileCleaner (L14): Finds files older than an age threshold under a root directory.
- method OldFileCleaner.__init__(self, config: Config=None, root_path: str='.') (L17): Args:
- method OldFileCleaner._should_exclude_path(self, path: Path) (L35): True when *path* hits an excluded directory name or pattern.
- method OldFileCleaner.find_old_files(self, min_age_days: int=None) (L47): Find files that haven't been accessed in the specified number of days.
- method OldFileCleaner.get_stats(self) (L96): Get statistics about the old file finding process.
- method OldFileCleaner._format_bytes(self, bytes_count: int) (L124): Format bytes into human-readable format.
- method OldFileCleaner.filter_by_age_range(self, min_days: int, max_days: int=None) (L132): Filter old files by age range.
- method OldFileCleaner.group_by_age(self) (L146): Group old files by age ranges.

## src/cortex_unified/analyzers/package_manager_cleaner.py — Detects installed package managers and clears their regenerable caches.
- class Package (L23): Single installed package as reported by a manager's list command.
- method Package.__post_init__(self) (L33): __post_init__.
- class PackageManager (L41): Detected manager executable with its resolved cache/config paths.
- class CleanupResult (L52): Outcome of one cache-clean operation (counts, bytes, errors).
- method CleanupResult.__post_init__(self) (L60): __post_init__.
- class HealthStatus (L68): Post-cleanup health verdict for a single package manager.
- method HealthStatus.__post_init__(self) (L74): __post_init__.
- class PackageManagerCleaner (L166): Cleans caches for well-known package managers across platforms.
- method PackageManagerCleaner.__init__(self, config: Config=None) (L175): Build manager definitions, logger, and the backup directory.
- method PackageManagerCleaner.detect_package_managers(self) (L302): Probe PATH for supported managers on the current OS.
- method PackageManagerCleaner._get_package_manager_version(self, name: str, executable: str) (L338): Return the version string, parsed per-tool from --version output.
- method PackageManagerCleaner._get_cache_path(self, name: str, config: Dict) (L366): Get cache directory path for a package manager.
- method PackageManagerCleaner.clean_pip_cache(self, keep_recent_days: int=7) (L457): Delete pip cache files older than keep_recent_days.
- method PackageManagerCleaner.clean_npm_cache(self, verify_integrity: bool=True) (L513): Wipe npm's content-addressed cache, then optionally verify it.
- method PackageManagerCleaner.clean_system_packages(self, package_manager: str) (L561): Run a system manager's native cache-clean command.
- method PackageManagerCleaner.find_orphaned_packages(self, package_manager: str) (L603): Dispatch to per-manager orphan detection.
- method PackageManagerCleaner._find_pip_orphaned_packages(self, manager: PackageManager) (L640): List installed pip packages without flagging any as orphaned.
- method PackageManagerCleaner._find_npm_orphaned_packages(self, manager: PackageManager) (L671): Find extraneous / unreferenced npm packages.
- method PackageManagerCleaner._find_apt_orphaned_packages(self, manager: PackageManager) (L697): Cross-references auto-installed packages with autoremove dry-run.
- method PackageManagerCleaner._find_dnf_orphaned_packages(self, manager: PackageManager) (L731): Runs `dnf repoquery --unneeded` or `dnf leaves` to locate unreferenced packages.
- method PackageManagerCleaner._find_pacman_orphaned_packages(self, manager: PackageManager) (L760): `pacman -Qtdq` lists dependency packages nothing requires anymore;
- method PackageManagerCleaner._find_brew_orphaned_packages(self, manager: PackageManager) (L790): Runs `brew leaves` (installed formulas that no other formula depends on).
- method PackageManagerCleaner.backup_package_lists(self) (L816): Snapshot package lists for every detected manager.
- method PackageManagerCleaner._backup_package_lists(self, managers: List[str]) (L820): Write each manager's installed-package listing to a timestamped
- method PackageManagerCleaner.verify_package_manager_health(self, package_manager: str) (L860): Post-cleanup sanity check for one manager.
- method PackageManagerCleaner._get_manager_by_name(self, name: str) (L914): Look up a detected manager by name key; None when absent.
- method PackageManagerCleaner._get_cache_size(self, cache_path: Optional[Path]) (L921): Recursive byte total for a cache dir; missing paths count 0.
- method PackageManagerCleaner.get_stats(self) (L940): Get statistics about detected package managers.
- method PackageManagerCleaner._format_bytes(self, bytes_count: int) (L959): Format bytes into human-readable format.
- method PackageManagerCleaner.scan_caches(self, target_folders: Optional[List[str]]=None, include_python_projects: bool=False, keep_recent_days: int=7, enabled_categories: Optional[List[str]]=None, progress_callback: Optional[object]=None, cancel_event: Optional[object]=None) (L968): Locate cleanable caches in manager-owned dirs or project trees.
- method PackageManagerCleaner._scan_project_caches_in_folder(self, folder: Path, keep_recent_days: int=0, enabled_categories: Optional[List[str]]=None, progress_callback: Optional[object]=None, cancel_event: Optional[object]=None) (L1019): Walk `folder` matching directory names against PROJECT_CACHE_CATEGORIES.
- func PackageManagerCleaner._scan_project_caches_in_folder._match_dir(d_name: str) (L1043): _match_dir.
- method PackageManagerCleaner._scan_manager_cache(self, manager: PackageManager, keep_recent_days: int) (L1119): Summarize one manager's global cache as a resource dict; None when
- method PackageManagerCleaner._get_dir_size(self, path: Path, cutoff_date: Optional[datetime]=None) (L1147): Total bytes and file count under path.
- method PackageManagerCleaner.clean_cargo_project(self, target_path: Path, dry_run: bool=True) (L1176): Run ``cargo clean`` for a Rust project's target dir.
- method PackageManagerCleaner.auto_discover_project_caches(self, enabled_categories: Optional[List[str]]=None, keep_recent_days: int=7, progress_callback: Optional[object]=None, cancel_event: Optional[object]=None, max_depth: int=4) (L1207): Walk all fixed drives for PROJECT_CACHE_CATEGORIES without manual folder.
- method PackageManagerCleaner.cleanup_caches(self, resources: List[Dict], dry_run: bool=True, progress_callback: Optional[object]=None, cancel_event: Optional[object]=None) (L1300): Dispatch each scanned resource to its cleaner and aggregate results.
- method PackageManagerCleaner._cleanup_python_cache(self, cache_path: Path, dry_run: bool=True) (L1373): Delete every file under a project-cache directory.
- method PackageManagerCleaner._cleanup_manager_cache(self, manager_name: str, dry_run: bool=True) (L1426): Run the manager's native cache-clean command.

## src/cortex_unified/analyzers/perceptual_duplicate_finder.py — Perceptual image/photo duplicate detection via pHash / aHash / dHash.
- func _validate_pil() (L88): _validate_pil.
- func _cos_table(n: int) (L103): ``n x n`` cosine kernel ``cos((2x+1) u pi / 2n)``.
- func _dct2d(rows: List[List[float]], cos: List[List[float]], size: int) (L116): Full 2D-DCT of a ``size x size`` matrix using precomputed cosine table.
- func average_hash(path: Path) (L140): aHash: 64 bits, bit k set when the k-th 8x8-block mean >= global mean.
- func difference_hash(path: Path) (L157): dHash: 64 bits from horizontal left-vs-right gradients of an 8x9 grid.
- func perceptual_hash(path: Path) (L176): pHash: 64-bit DCT low-frequency hash (the canonical, most robust).
- func _haar_1d(arr: List[float]) (L211): Single-level Haar transform (averages + differences).
- func _haar_2d_grayscale(pixels: List[int], size: int, levels: int) (L223): 2-D Haar DWT on size×size grayscale block; returns LL subband after levels.
- func wavelet_hash(path: Path) (L248): wHash (Haar wavelet): 64 bits via multi-resolution Haar DWT.
- func compute_hash(path: Path, kind: str='phash') (L280): Compute a single perceptual hash of *kind* for an image.
- func hamming_distance(a: int, b: int) (L291): Number of differing bits between two hashes (0..64).
- class PerceptualDuplicateFinder (L300): Find visually-similar image groups via perceptual hashing.
- method PerceptualDuplicateFinder.__init__(self, root_path: str | os.PathLike, max_distance: int=10, kinds: Tuple[str, ...]=('phash',), require_all_kinds: bool=False, config: Config | None=None) (L316): __init__.
- method PerceptualDuplicateFinder._should_exclude(self, path: Path) (L352): _should_exclude.
- method PerceptualDuplicateFinder._is_image(self, path: Path) (L364): _is_image.
- method PerceptualDuplicateFinder.find_perceptual_duplicates(self, threads: int=0, progress_callback: Optional[Callable[[str, int], None]]=None, cancel_event: Optional[threading.Event]=None) (L372): Scan the roots and return visual-duplicate groups (size >= 2).
- func PerceptualDuplicateFinder.find_perceptual_duplicates._hash_one(p: Path) (L415): _hash_one.
- func PerceptualDuplicateFinder.find_perceptual_duplicates._find(x: Path) (L468): _find.
- func PerceptualDuplicateFinder.find_perceptual_duplicates._union(a: Path, b: Path) (L477): _union.
- method PerceptualDuplicateFinder._window_size(self, n: int) (L511): Neighbourhood size for the sorted-hash candidate scan.
- method PerceptualDuplicateFinder.get_stats(self) (L519): Aggregate stats akin to ``DuplicateFinder.get_stats``.

## src/cortex_unified/analyzers/portable_manager.py — Portable Manager — PortableApps.com / LiberKey catalog, USB toolkit.
- class PortableApp (L73): PortableApp.
- method PortableApp.to_dict(self) (L87): to_dict.
- func _find_removable_drives() (L101): _find_removable_drives.
- func _find_portable_roots() (L132): _find_portable_roots.
- func _parse_appinfo(ini_path: Path) (L176): _parse_appinfo.
- class PortableManager (L216): PortableManager.
- method PortableManager.__init__(self, progress: Callable[[str], None] | None=None, cancel: threading.Event | None=None) (L218): __init__.
- method PortableManager.scan_portable_roots(self, roots: List[Path] | None=None) (L226): scan_portable_roots.
- method PortableManager.check_updates(self, apps: List[PortableApp]) (L270): Compare each app's installed version to its declared source.
- method PortableManager.update_app(self, app: PortableApp, timeout: int=1800) (L334): Run the app's own PAF installer in silent mode, in place.
- method PortableManager.export_toolkit(self, target: Path, include_sysinternals: bool=True, sysinternals_tools: Optional[List[str]]=None, include_live_iso: bool=False, timeout: int=120) (L371): Build a portable toolkit on *target* (typically a USB drive).
- method PortableManager._download_sysinternals(self, tool: str, dest: Path, timeout: int) (L417): Fetch one Sysinternals tool and verify it is a real PE file.

## src/cortex_unified/analyzers/privacy_cleaner.py — Detects and removes browser traces (cache, cookies, history, sessions)
- class PrivacyCleaner (L18): Removes privacy-sensitive browser data and Windows activity traces.
- method PrivacyCleaner.__init__(self) (L25): __init__.
- method PrivacyCleaner.scan_browsers(self) (L46): Scan all known browsers and return {browser: {category: size_bytes}}.
- method PrivacyCleaner.scan_system_traces(self) (L72): Return sizes of cleanable Windows system privacy traces.
- method PrivacyCleaner.clean_browser(self, browser: str, items: List[str]) (L94): Delete selected data categories for one browser.
- method PrivacyCleaner.clean_system_traces(self, clean_recent: bool=False) (L134): Clean system-level privacy traces, return bytes freed.
- method PrivacyCleaner._discover_chromium_profiles(base_path: str) (L161): Dynamically find Chromium profile directories.
- method PrivacyCleaner._scan_chromium_profile(self, prof_path: str, stats: Dict[str, int]) (L178): Accumulate sizes from one Chromium profile.
- method PrivacyCleaner._clean_chromium_profile(self, prof_path: str, items: List[str]) (L196): Delete specified items in one Chromium profile.
- method PrivacyCleaner._scan_firefox(self, profiles_path: str, stats: Dict[str, int]) (L220): _scan_firefox.
- method PrivacyCleaner._get_file_size(path: str) (L241): _get_file_size.
- method PrivacyCleaner._get_dir_size(path: str) (L251): _get_dir_size.
- method PrivacyCleaner._safe_delete(path: str) (L270): Remove a file, ignoring errors (browsers commonly hold locks).
- method PrivacyCleaner._safe_delete_dir(path: str) (L279): Recursively remove a directory tree, ignoring failures.
- method PrivacyCleaner._clean_directory_contents(self, path: str) (L284): Remove all files inside a directory, return bytes freed.

## src/cortex_unified/analyzers/project_cache_scanner.py — Auto-discovery of project cache folders across fixed drives.
- func _fixed_drive_roots() (L38): Return fixed-drive mount points (C:\, D:\ ...) on Windows, or [home] elsewhere.
- func _known_code_roots() (L71): High-hit-rate code parents to prefer over whole-drive walks.
- class ProjectCacheScanner (L119): Drive-aware scanner for PROJECT_CACHE_CATEGORIES patterns.
- method ProjectCacheScanner.__init__(self, enabled_categories: Optional[List[str]]=None, keep_recent_days: int=7) (L128): __init__.
- method ProjectCacheScanner.scan_fixed_drives(self, progress_callback: Optional[object]=None, cancel_event: Optional[object]=None, max_depth: int=5, prefer_code_roots: bool=True) (L147): Scan all fixed drives (or known code roots) for project caches.
- method ProjectCacheScanner._scan_root(self, folder: Path, keep_recent_days: int=0, progress_callback: Optional[object]=None, cancel_event: Optional[object]=None, max_depth: Optional[int]=None) (L185): Walk *folder* matching dir names against PROJECT_CACHE_CATEGORIES.
- func ProjectCacheScanner._scan_root._match_dir(d_name: str) (L198): _match_dir.
- func ProjectCacheScanner._scan_root._should_skip_dir(name: str) (L218): _should_skip_dir.
- func _keep_for_scan(n: str) (L244): _keep_for_scan.
- method ProjectCacheScanner._get_dir_size(self, path: Path, cutoff_date: Optional[datetime]=None) (L356): _get_dir_size.
- method ProjectCacheScanner._format_bytes(n: int) (L379): _format_bytes.

## src/cortex_unified/analyzers/registry_cleaner_ai.py — AI/ML-Enhanced Registry Cleaner — learned safety, contextual risk scoring.
- class RegistryIssue (L93): Single registry issue with ML risk score.
- method RegistryIssue.to_dict(self) (L106): to_dict.
- class ScanResult (L115): ScanResult.
- method ScanResult.to_json(self) (L122): to_json.
- class CleanResult (L136): CleanResult.
- func _split(path: str) (L161): 'HKLM\Software\X' -> (hive_handle, 'Software\X', access_flags).
- func _split32(path: str) (L171): Same as _split but for the 32-bit view of HKLM (None for HKCU).
- func _expand(p: str) (L179): Expand %SystemRoot%-style references inside a registry string.
- func _resolve_target(raw: str) (L206): Resolve a registry path value to an on-disk path, or None if unresolvable.
- func _target_candidates(raw: str) (L228): Every plausible absolute path a registry ImagePath/target could mean.
- func _verifiable(path: str) (L254): True when absence of *path* can actually be proven.
- func _target_exists(raw: str) (L293): True when *raw* resolves to an existing file under any known root.
- func _target_exists_any(candidates: List[str]) (L302): Same rule as :func:`_target_exists` for pre-resolved candidates.
- func _exe_from_command(cmd: str) (L317): First absolute candidate for an executable named by a command line.
- func _detect_missing_path(key_path: str, values: Dict, access: int) (L323): App Paths\<exe> whose (Default) target is gone.
- func _detect_orphaned_uninstall(key_path: str, values: Dict, access: int) (L331): Uninstall\<app> entry whose InstallLocation / uninstaller is missing.
- func _detect_missing_path_value(key_path: str, values: Dict, access: int) (L349): Any REG_EXPAND_SZ/REG_SZ value that names a file that no longer exists.
- func _detect_shared_dll_gone(key_path: str, values: Dict, access: int) (L365): SharedDLLs: every value name is a DLL path; flag the missing ones.
- func _font_candidates(data: str) (L373): Absolute candidates for a Fonts value.
- func _detect_orphaned_font(key_path: str, values: Dict, access: int) (L386): Fonts: value data names font files under the Fonts directory.
- func _detect_orphaned_service(key_path: str, values: Dict, access: int) (L396): Services\<svc>: the driver or service binary is verifiably gone.
- func _key_age_days(key_path: str, access: Optional[int]=None) (L421): Days since the key's last write, from the FILETIME QueryInfoKey returns.
- func _detect_stale_mru(key_path: str, values: Dict, access: int, stale_days: int=_MRU_STALE_DAYS) (L445): MRU list untouched for longer than *stale_days*.
- func _log2(x: float) (L530): math.log2 with the 0-limit handled, so entropy of a single-symbol
- func _categorize_key(key_path: str) (L536): Fast rule-based categorization.
- func _extract_features(key_path: str, value_name: str, value_data: str, value_type: int, parent_exists: bool, uninstaller_exists: bool, is_signed: bool, age_days: int) (L545): Extract numerical features for ML model.
- func _is_authenticode_signed(path: Path) (L605): True when *path* carries a trusted Authenticode signature.
- class GUID(ctypes.Structure) (L618): GUID.
- class WINTRUST_FILE_INFO(ctypes.Structure) (L625): WINTRUST_FILE_INFO.
- class WINTRUST_DATA(ctypes.Structure) (L634): WINTRUST_DATA.
- class _MLModel (L680): ONNX model wrapper for risk scoring.
- method _MLModel.__init__(self, model_path: Optional[str]=None) (L683): __init__.
- method _MLModel.predict(self, features: List[float]) (L698): Return (risk_score, confidence).
- method _MLModel._heuristic_score(self, features: List[float]) (L713): Rule-based fallback when ML unavailable.
- class AIRegistryCleaner (L747): AI-enhanced registry cleaner with learned safety.
- method AIRegistryCleaner.__init__(self, model_path: Optional[str]=None, create_restore_point: bool=True, progress_callback: Optional[Callable[[str], None]]=None, cancel_event: Optional[threading.Event]=None) (L750): __init__.
- method AIRegistryCleaner._run_ps(self, script: str, timeout: int=60) (L770): _run_ps.
- method AIRegistryCleaner._key_exists(self, path: str) (L786): _key_exists.
- method AIRegistryCleaner._get_parent(self, path: str) (L805): _get_parent.
- method AIRegistryCleaner._values_map(self, path: str, access: Optional[int]=None) (L814): {name: (data, type)} for a key; empty dict when unreadable.
- method AIRegistryCleaner._enum_values(self, path: str) (L834): _enum_values.
- method AIRegistryCleaner._check_uninstaller(self, path: str) (L840): True when this key names an uninstaller that still exists on disk.
- method AIRegistryCleaner._check_signature(self, path: str) (L850): Authenticode check on the first referenced binary, via WinVerifyTrust.
- method AIRegistryCleaner._estimate_age(self, path: str) (L866): Days since the key's last write, from the FILETIME QueryInfoKey returns.
- method AIRegistryCleaner.scan(self, categories: Optional[List[str]]=None) (L886): Scan registry for issues.
- method AIRegistryCleaner._iter_subkeys(self, root: str, access: Optional[int]=None) (L973): Immediate subkey paths of *root* (plus *root* itself for value-only keys).
- method AIRegistryCleaner._offending_value(self, key_path: str, values: Dict[str, Tuple[Any, int]], category: str) (L992): Pick the value whose target is missing, for display and removal.
- method AIRegistryCleaner.clean(self, issues: List[RegistryIssue], selected_ids: Optional[List[int]]=None, full_hive_backup: bool=False) (L1024): Clean selected issues (by index in the *issues* list).
- method AIRegistryCleaner._remove_and_backup(self, issue: RegistryIssue) (L1075): Back the key up first, then remove what the issue names.
- method AIRegistryCleaner._delete_key(self, key_path: str) (L1089): Delete a key and all its values, honouring the registry view.
- method AIRegistryCleaner._delete_value(self, key_path: str, value_name: str) (L1125): Delete one value, honouring the registry view the scan used.
- method AIRegistryCleaner._backup_key(self, key_path: str) (L1151): Export the key to a timestamped .reg file, native view first.
- method AIRegistryCleaner._backup_registry(self) (L1175): Export HKLM and HKCU so a failed clean is fully reversible.
- method AIRegistryCleaner._create_restore_point(self) (L1190): _create_restore_point.

## src/cortex_unified/analyzers/residual_cleaner.py — Residual Cleaner — finds leftover folders after application uninstall.
- class ResidualCleaner (L15): Finds leftover files and folders for uninstalled applications.
- method ResidualCleaner.__init__(self) (L27): __init__.
- method ResidualCleaner.scan_for_app(self, app_name: str, publisher: str='') (L42): Scan for leftover folders matching an uninstalled app.
- method ResidualCleaner._build_search_tokens(app_name: str, publisher: str) (L93): Build strict search tokens from the app name and publisher.
- method ResidualCleaner._matches_tokens(entry: str, tokens: List[str]) (L126): Check if a directory name matches any of the search tokens.
- method ResidualCleaner._get_size(path: str) (L141): Total size of a directory tree.

## src/cortex_unified/analyzers/residual_hunter.py — Backward-compatibility alias for ResidualCleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/analyzers/video_duplicate_finder.py — Video near-duplicate detection via keyframe perceptual hashing + temporal consistency.
- func _cos_table(n: int) (L108): _cos_table.
- func _dct2d(rows: List[List[float]], cos: List[List[float]], size: int) (L117): _dct2d.
- func _phash_image(img) (L138): _phash_image.
- func _hamming(a: int, b: int) (L159): _hamming.
- func _extract_frames_cv2(path: Path, max_frames: int=_MAX_FRAMES) (L169): Extract frame pHashes via cv2 (returns list of 64-bit ints).
- func _extract_frames_imageio(path: Path, max_frames: int=_MAX_FRAMES) (L218): Fallback via imageio (ffmpeg).
- func _fallback_raw_video_fp(path: Path) (L271): Byte-level surrogate for hosts without cv2/imageio: chunk hashes.
- func compute_video_fingerprint(path: Path | str, max_frames: int=_MAX_FRAMES) (L292): Sequence fingerprint (list of 64-bit pHashes) for a video file.
- func video_compare(fp_a: List[int], fp_b: List[int], max_distance: int=10) (L312): Similarity 0.0..1.0 between two video fingerprints.
- class VideoDuplicateFinder (L405): Find temporally-similar video groups (re-encodes, trims, watermarks).
- method VideoDuplicateFinder.__init__(self, root_path: str | os.PathLike, threshold: float=0.55, max_distance: int=10, config: Config | None=None) (L417): __init__.
- method VideoDuplicateFinder._should_exclude(self, path: Path) (L446): _should_exclude.
- method VideoDuplicateFinder._is_video(self, path: Path) (L458): _is_video.
- method VideoDuplicateFinder.find_video_duplicates(self, threads: int=0, progress_callback: Optional[Callable[[str, int], None]]=None, cancel_event: Optional[threading.Event]=None) (L464): find_video_duplicates.
- func VideoDuplicateFinder.find_video_duplicates._fp_one(p: Path) (L503): _fp_one.
- func VideoDuplicateFinder.find_video_duplicates._find(x: Path) (L556): _find.
- func VideoDuplicateFinder.find_video_duplicates._union(a: Path, b: Path) (L565): _union.
- method VideoDuplicateFinder.get_stats(self) (L593): get_stats.

## src/cortex_unified/analyzers/weaponized_shredder.py — Backward-compatibility alias for AdvancedShredder.
- (no classes/functions — constants/imports only)

## src/cortex_unified/cli/__init__.py — Command Line Interface (CLI) module for Cortex Workstation.
- (no classes/functions — constants/imports only)

## src/cortex_unified/cli/cli.py — Command-line interface for Cortex Cleaner (legacy ``cortex-cleaner``).
- func _has_registry_cleaner() (L42): True when the optional Windows registry cleaner can be imported.
- func __getattr__(name: str) (L56): Preserve the historical ``HAS_REGISTRY_CLEANER`` module flag (:pep:`562`).
- func main() (L68): Cortex Workstation - The Ultimate Windows NT Systems, Forensics & File Management Platform.
- func clean_empty(dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, cpu_priority, io_priority, checkpoint_interval, resume_from, path) (L92): Find and remove empty files and folders safely.
- func find_large_files(min_size, pattern, exclude_pattern, config, no_config, verbose, log_file, json_log, threads, export, path) (L275): List files larger than --min-size MB under PATH, biggest first.
- func find_duplicates(strategy, hash_algorithm, preview, delete, pattern, exclude_pattern, config, no_config, yes, verbose, log_file, json_log, threads, export, path) (L371): Find duplicate files by content hash.
- func clean_temp(dry_run, delete, trash, min_age, exclude_pattern, config, no_config, yes, verbose, log_file, json_log) (L500): Find and remove stale temporary files from system temp locations safely.
- func analyze_disk(analyze, export_json, export_treemap, export_sunburst, export_dashboard, max_depth, threads, cpu_priority, io_priority, memory_limit, checkpoint_interval, resume_from, config, no_config, verbose, log_file, json_log, path) (L625): Analyze disk usage with interactive visualizations.
- func list_startup_items() (L824): List system startup items with enabled/disabled status and location.
- func analyze_processes(export) (L853): Summarize running processes and services.
- func docker_cleanup(dry_run, clean, images, containers, volumes, networks, clean_all, config, no_config, yes, verbose, log_file, json_log, export) (L908): Clean Docker resources (images, containers, volumes, networks).
- func package_cleanup(pip, npm, yarn, conda, system, clean_all, orphaned, keep_recent_days, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export) (L1067): Clean package manager caches and orphaned packages.
- func heuristics_scan(confidence_threshold, scan_registry, ml_patterns, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export, path) (L1215): Scan for application leftovers using advanced heuristics.
- func secure_delete(shred, passes, verify, yes, verbose, log_file, json_log, files) (L1370): Securely delete FILES (preview by default).
- func restore(restore, dry_run, yes, verbose, log_file, json_log) (L1432): Restore files from a deletion manifest, or list saved backups.
- func generate_report(type, export, name, verbose, log_file, json_log) (L1499): Generate a system report as text, html, json, or csv.
- func checkpoint() (L1567): Create, list, resume from, or delete scan checkpoints.
- func list_checkpoints(config, verbose) (L1573): List saved scan checkpoints with id, timestamp, path, and progress.
- func delete(checkpoint_id, verbose) (L1603): Delete a saved checkpoint by its id.
- func cleanup(max_age, verbose) (L1625): Delete checkpoints older than --max-age days (default: 7).
- func scan_enhanced(checkpoint_id, enable_checkpoints, enable_throttling, cpu_limit, memory_limit, dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, path) (L1665): Empty-file scan with optional checkpointing and resource throttling.
- func scan_broken_links(scan_symlinks, scan_shortcuts, scan_registry, repair, backup, confidence_threshold, export, verbose, path) (L1860): Scan for and optionally repair broken symlinks, shortcuts, and registry references.
- func clean_shaders_cmd(min_age_days: int, dry_run: bool) (L2006): Audit and purge DirectX and GPU vendor shader caches.
- func clean_ai_cmd(dry_run: bool) (L2023): Audit and clean Windows 11 Copilot, Recall, and SQLite WAL journals.
- func trim_ssd_cmd(drive: str) (L2038): Trigger SSD NVMe flash block deallocation (TRIM/ReTrim).
- func vss_health_cmd() (L2050): Inspect Volume Shadow Copy (VSS) writers and shadow storage.
- func verify_checksums_cmd(manifest_file: str) (L2063): Verify an integrity manifest (.sha256, .md5, .sfv) against files on disk.

## src/cortex_unified/core/__init__.py — Cortex Workstation Core Engine and Orchestration Framework.
- (no classes/functions — constants/imports only)

## src/cortex_unified/core/background_agent.py — Background Agent — lightweight real-time system monitor.
- class BackgroundAgent(QObject) (L16): Silently monitors system resources in a background thread.
- method BackgroundAgent.__init__(self, check_interval: int=10) (L24): __init__.
- method BackgroundAgent.start_monitoring(self) (L43): Main loop — called when the owning QThread starts.
- method BackgroundAgent.stop(self) (L96): Request loop exit; takes effect within one check interval.

## src/cortex_unified/core/config.py — Legacy YAML configuration management for Cortex Cleaner.
- class Config (L19): Configuration class for Cortex Cleaner.
- method Config.__init__(self, config_path: str=None) (L29): __init__.
- method Config._get_default_config_path(self) (L35): Get the default configuration file path.
- method Config._load_config(self) (L40): Return ``DEFAULT_CONFIG`` overlaid with the user's YAML file.
- method Config._defaults() (L85): A deep-enough copy of ``DEFAULT_CONFIG`` for safe mutation.
- method Config.exclude_patterns(self) (L98): Get exclude patterns from config.
- method Config.exclude_dirs(self) (L103): Get exclude directories from config.
- method Config.exclude_regex_patterns(self) (L108): Get exclude regex patterns from config.
- method Config.min_age_days(self) (L113): Get minimum age in days.
- method Config.default_action(self) (L118): default_action.
- method Config.log_file(self) (L124): log_file.
- method Config.json_logging(self) (L130): json_logging.
- method Config.threads(self) (L136): threads.
- method Config.follow_symlinks(self) (L142): follow_symlinks.
- method Config.matches_exclude_patterns(self, path: str) (L147): Check if a path matches any exclude patterns (glob or regex).

## src/cortex_unified/core/config_v2.py — Pydantic-based configuration management for Cortex Cleaner.
- func _read_yaml_file(path: Path) (L65): Load a YAML config file into a dict, warning (not raising) on failure.
- class _YamlConfigSource(PydanticBaseSettingsSource) (L77): A pydantic-settings source that reads from an optional YAML file.
- method _YamlConfigSource.__init__(self, settings_cls, config_file) (L85): __init__.
- method _YamlConfigSource.get_field_value(self, field, field_name) (L91): get_field_value.
- method _YamlConfigSource.__call__(self) (L96): __call__.
- class ScanConfig(BaseModel) (L102): Configuration for scan operations.
- class PerformanceConfig(BaseModel) (L149): Configuration for performance settings.
- method PerformanceConfig.clamp_threads(cls, v: int) (L183): Clamp thread count to reasonable limits.
- class SecurityConfig(BaseModel) (L190): Configuration for security and safety settings.
- class LoggingConfig(BaseModel) (L228): Configuration for logging.
- class DatabaseConfig(BaseModel) (L252): Configuration for database persistence.
- class UIConfig(BaseModel) (L278): Configuration for UI settings.
- class Config(BaseSettings) (L302): Main configuration class for Cortex Cleaner.
- method Config.__init__(self, **data) (L350): Initialize config, resolving the YAML file path (if any).
- method Config.settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings) (L369): Define source precedence, highest priority first:
- method Config._load_yaml(path: Path) (L388): Load configuration from YAML file. Kept as a public-ish helper for
- method Config.save_to_yaml(self, path: Optional[Path]=None) (L393): Save current configuration to YAML file.
- method Config.matches_exclude_patterns(self, path: str) (L412): Check if a path matches any exclude patterns (glob or regex).
- method Config.exclude_patterns(self) (L444): Backward compatibility: get exclude patterns.
- method Config.exclude_dirs(self) (L449): Backward compatibility: get exclude directories.
- method Config.exclude_regex_patterns(self) (L454): Backward compatibility: get exclude regex patterns.
- method Config.min_age_days(self) (L459): Backward compatibility: get minimum age in days.
- method Config.default_action(self) (L464): Backward compatibility: get default action.
- method Config.log_file(self) (L469): Backward compatibility: get log file path.
- method Config.json_logging(self) (L474): Backward compatibility: get JSON logging flag.
- method Config.threads(self) (L479): Backward compatibility: get number of threads.
- method Config.follow_symlinks(self) (L484): Backward compatibility: get follow symlinks flag.
- func create_default_config(path: Optional[Path]=None) (L556): Create and save a default configuration file.

## src/cortex_unified/core/database.py — SQLite persistence layer for Cortex Cleaner.
- class Base(DeclarativeBase) (L35): Base class for all database models.
- class ScanRun(Base) (L39): Record of a scan operation.
- method ScanRun.__repr__(self) (L71): __repr__.
- method ScanRun.duration_seconds(self) (L77): duration_seconds.
- method ScanRun.to_dict(self) (L84): Convert to dictionary for JSON serialization.
- class DeletedItem(Base) (L102): Record of a deleted file or directory.
- method DeletedItem.__repr__(self) (L140): __repr__.
- method DeletedItem.to_dict(self) (L145): Convert to dictionary for JSON serialization.
- class ScheduledJob(Base) (L162): Scheduled cleanup job.
- method ScheduledJob.__repr__(self) (L191): __repr__.
- class SystemMetric(Base) (L196): System health and performance metrics.
- class UserPreference(Base) (L224): User preferences and settings.
- method UserPreference.__repr__(self) (L237): __repr__.
- class Database (L242): Database manager for Cortex Cleaner.
- method Database.__init__(self, db_path: Optional[Path]=None, echo: bool=False) (L249): Initialize database connection.
- method Database.session(self) (L285): Context manager for database sessions.
- method Database.create_scan_run(self, scan_type: str, root_path: str, health_score_before: Optional[int]=None) (L299): Create a new scan run record.
- method Database.update_scan_run(self, run_id: int, status: Optional[str]=None, items_found: Optional[int]=None, bytes_found: Optional[int]=None, items_deleted: Optional[int]=None, bytes_freed: Optional[int]=None, health_score_after: Optional[int]=None, error_message: Optional[str]=None) (L318): update_scan_run.
- method Database.get_scan_history(self, limit: int=100, scan_type: Optional[str]=None, since: Optional[datetime]=None) (L351): Get scan history with optional filters.
- method Database.get_scan_stats(self, days: int=30) (L371): Get aggregate statistics for recent scans.
- method Database.add_deleted_item(self, run_id: int, path: str, size_bytes: int=0, file_type: str='file', backup_path: Optional[str]=None, deletion_method: str='trash', sha256: Optional[str]=None) (L413): Record a deleted item.
- method Database.get_restorable_items(self, limit: int=100, in_quarantine_only: bool=True) (L442): Get items that can be restored.
- method Database.mark_item_restored(self, item_id: int) (L461): Mark an item as restored.
- method Database.cleanup_old_quarantine(self, days: int=30) (L469): Remove quarantine records older than specified days.
- method Database.record_metric(self, disk_total_gb: Optional[float]=None, disk_used_gb: Optional[float]=None, disk_free_gb: Optional[float]=None, health_score: Optional[int]=None, drive_path: Optional[str]=None) (L483): Record a system metric snapshot.
- method Database.get_metrics_history(self, days: int=30, drive_path: Optional[str]=None) (L509): Get historical metrics.
- method Database.cleanup_old_history(self, max_entries: int=1000) (L531): Keep only the most recent scan history entries.
- func get_database(db_path: Optional[Path]=None) (L559): get_database.
- func db_session() (L574): Convenience context manager for database sessions.

## src/cortex_unified/core/deleter.py — File and directory deletion functionality for Cortex Cleaner.
- class Deleter (L17): Removes empty files and directories, recording every outcome.
- method Deleter.__init__(self, dry_run: bool=True, use_trash: bool=False) (L26): Create a deleter.
- method Deleter._delete_file(self, filepath: Path) (L40): Remove one file, or record it when running as a dry run.
- method Deleter._delete_directory(self, dirpath: Path) (L93): Remove one directory, or record it when running as a dry run.
- method Deleter.delete(self, empty_files: List[Path], empty_dirs: List[Path]) (L132): Delete the given empty files and directories.
- method Deleter.generate_manifest(self, output_dir: str='.') (L160): Write a JSON manifest describing every operation performed.

## src/cortex_unified/core/logging_setup.py — Structured logging configuration for Cortex Cleaner.
- func add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) (L23): Add correlation ID to log events if present.
- func add_app_context(logger: Any, method_name: str, event_dict: EventDict) (L30): Add application context to all log events.
- func censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) (L40): Censor sensitive data from logs.
- func censor_sensitive_data._censor_dict(d: Dict[str, Any]) (L51): _censor_dict.
- func configure_logging(log_level: str='INFO', log_file: Optional[Path]=None, json_output: bool=False, enable_colors: bool=True, enable_censoring: bool=True) (L72): Configure structured logging for Cortex Cleaner.
- func get_logger(name: Optional[str]=None) (L170): Get a structured logger instance.
- func set_correlation_id(correlation_id: str) (L190): Set correlation ID for the current context.
- func clear_correlation_id() (L207): clear_correlation_id.
- class LogContext (L212): Context manager for temporary log context.
- method LogContext.__init__(self, **kwargs) (L223): Initialize with context key-value pairs.
- method LogContext.__enter__(self) (L228): Enter context and bind variables.
- method LogContext.__exit__(self, exc_type, exc_val, exc_tb) (L233): Exit context and unbind variables.
- func log_scan_start(logger: structlog.BoundLogger, scan_type: str, root_path: str, **kwargs) (L239): Log the start of a scan operation.
- func log_scan_complete(logger: structlog.BoundLogger, scan_type: str, items_found: int, bytes_found: int, duration_seconds: float, **kwargs) (L253): Log the completion of a scan operation.
- func log_scan_error(logger: structlog.BoundLogger, scan_type: str, error: Exception, **kwargs) (L271): Log a scan error with exception details.
- func log_file_operation(logger: structlog.BoundLogger, operation: str, path: str, success: bool, **kwargs) (L287): log_file_operation.
- func log_performance_metric(logger: structlog.BoundLogger, metric_name: str, value: float, unit: str='seconds', **kwargs) (L305): log_performance_metric.

## src/cortex_unified/core/proc.py — Cancellable, tree-safe subprocess execution.
- class ProcessCancelled(subprocess.SubprocessError) (L56): Raised when ``cancel_event`` fired before the process finished.
- method ProcessCancelled.__init__(self, args) (L63): __init__.
- func run(args: list[str], *, timeout: float | None=None, cancel_event: 'threading.Event | None'=None, text: bool=False, encoding: str | None=None, errors: str | None=None, input: str | bytes | None=None, creationflags: int=0, cwd: str | None=None, env: dict | None=None) (L70): Drop-in replacement for ``subprocess.run`` that never leaves an orphan.
- func _kill_tree(proc: subprocess.Popen) (L148): Best-effort kill of *proc* and every descendant it spawned.
- func _reap_quietly(proc: subprocess.Popen) (L179): Collect the exit status after a kill so no zombie/handle is left.

## src/cortex_unified/core/scanner.py — Discovery of empty files and directories under a configured root.
- class Scanner (L21): Finds empty files and directories eligible for cleanup.
- method Scanner.__init__(self, config: Config=None, root_path: str='.', enable_checkpoints: bool=False, enable_throttling: bool=False) (L29): Create a scanner.
- method Scanner._should_exclude_path(self, path: Path) (L65): True when *path* hits a system directory or a configured pattern.
- method Scanner._is_file_empty(self, filepath: Path) (L71): True when *filepath* has zero bytes.
- method Scanner._is_file_old_enough(self, filepath: Path) (L82): Apply the ``min_age_days`` rule; files younger are skipped.
- method Scanner._scan_file(self, filepath: Path) (L95): True when *filepath* passes every eligibility filter.
- method Scanner._scan_directory(self, dirpath: Path, max_depth: int=1000) (L108): Scan a directory and its contents using iterative BFS to avoid stack overflow.
- method Scanner.scan(self, threads: int=0, checkpoint_id: Optional[str]=None, max_depth: int=1000) (L221): Scan for empty files and directories with optional checkpoint support.
- method Scanner._estimate_total_items(self) (L294): Rough item count for progress bars; exactness is not required.
- method Scanner._scan_directory_enhanced(self, dirpath: Path, scan_state: dict, max_depth: int=20) (L309): Recursive scan with pause/throttle hooks.
- method Scanner.pause_scan(self) (L367): Pause the current scan operation.
- method Scanner.resume_scan(self, checkpoint_id: Optional[str]=None) (L372): resume_scan.
- method Scanner.get_scan_progress(self) (L378): Get current scan progress.
- method Scanner.create_checkpoint(self) (L384): Create a checkpoint of current scan state.
- method Scanner.list_checkpoints(self) (L395): List available checkpoints.
- method Scanner.get_stats(self) (L401): Get statistics about the scan.

## src/cortex_unified/core/security.py — Security utilities for Cortex Cleaner.
- func _get_protected_paths() (L59): Protected system locations for the current platform.
- func is_safe_path(path: Union[str, Path], base_dir: Union[str, Path]=None) (L95): Check if a path is safe to modify.
- func is_system_file(path: Union[str, Path]) (L168): Check if a file is a system file.
- func validate_paths(paths: List[Union[str, Path]], base_dir: Union[str, Path]=None) (L217): Validate multiple paths and return safe ones + errors.
- func is_path_writable(path: Union[str, Path]) (L256): Check if a path is writable.
- func get_safe_temp_dir() (L280): Get a safe temporary directory for the current platform.
- func check_deletion_safety(path: Union[str, Path], allow_system_files: bool=False) (L289): Check if it's safe to delete a path.

## src/cortex_unified/core/smart_scanner.py — Smart Scanner — orchestrates parallel system analysis and produces a Health Score.
- class SmartScanReport (L25): Holds the result of a Smart Scan.
- method SmartScanReport.__init__(self) (L28): __init__.
- method SmartScanReport.total_cleanable_mb(self) (L46): total_cleanable_mb.
- method SmartScanReport.calculate_score(self) (L53): Calculate 0-100 health score from real metrics.
- class SmartScannerWorker(QObject) (L73): Worker that runs in a QThread to perform the full smart scan.
- method SmartScannerWorker.__init__(self, config: Config) (L80): __init__.
- method SmartScannerWorker.run(self) (L88): run.
- method SmartScannerWorker.stop(self) (L163): Cooperative cancel: checked between phases and inside directory walks.
- method SmartScannerWorker._scan_temp_dirs(self) (L171): Walk every temp directory and sum file sizes. Returns MB.
- method SmartScannerWorker._scan_browser_caches(self) (L195): Return (total_mb, number_of_browsers_with_data).
- method SmartScannerWorker._scan_dir_mb(self, path: str, max_depth: int=5) (L220): Recursively sum file sizes under *path*. Returns MB.
- method SmartScannerWorker._scan_recycle_bin(self) (L239): Return approximate Recycle Bin size in MB.

## src/cortex_unified/core/smart_suggest.py — Smart Suggestions - a tiny, fully-offline, on-device learning engine.
- func _sigmoid(z: float) (L40): _sigmoid.
- func _size_bucket(size_bytes: int) (L50): _size_bucket.
- func _age_bucket(age_days: float) (L67): _age_bucket.
- func featurize(context: dict[str, Any]) (L81): Turn a cleanup item's context into a small list of active feature keys.
- class SmartSuggester (L107): Online logistic-regression recommender with local JSON persistence.
- method SmartSuggester.__init__(self, model_path: Path | None=None, learning_rate: float=_DEFAULT_LR) (L110): __init__.
- method SmartSuggester.score(self, context: dict[str, Any]) (L122): Return P(user would clean this item), in [0, 1].
- method SmartSuggester.recommend(self, context: dict[str, Any], threshold: float=0.5) (L129): Whether to recommend cleaning this item (until trained, defaults to True).
- method SmartSuggester.rank(self, items: list[dict[str, Any]]) (L135): Return items paired with scores, highest-confidence-to-clean first.
- method SmartSuggester.observe(self, context: dict[str, Any], cleaned: bool) (L143): Update the model from one user decision (cleaned=True kept/removed it).
- method SmartSuggester.observe_batch(self, items: list[dict[str, Any]], cleaned: bool) (L158): observe_batch.
- method SmartSuggester._enforce_cap_locked(self) (L164): Keep the model tiny: if over cap, drop the smallest-magnitude weights.
- method SmartSuggester._load(self) (L173): _load.
- method SmartSuggester.save(self) (L187): Persist the model atomically. Returns True on success.
- method SmartSuggester.stats(self) (L205): stats.
- method SmartSuggester.reset(self) (L216): reset.

## src/cortex_unified/core/temp_cleaner.py — Discovery and safe removal of stale files from operating-system temp locations.
- class TempFinding (L57): One deletable temp file discovered by :meth:`TempCleaner.scan`.
- func _normalize(path: os.PathLike[str] | str) (L66): Case- and separator-normalised absolute form, for containment tests.
- func _is_junction(entry: os.DirEntry) (L71): True for Windows junctions/mount points (:mod:`os` reparse points).
- class TempCleaner (L88): Finds and removes stale files under the platform's temp roots.
- method TempCleaner.__init__(self, min_age_days: int=1, exclude_patterns: list[str] | None=None, follow_symlinks: bool=False) (L91): Create a temp cleaner.
- method TempCleaner.LOCATIONS(cls) (L132): Discover the temp roots for the current platform.
- func TempCleaner.LOCATIONS._usable(label: str, path: Path) (L164): _usable.
- method TempCleaner._discover_locations(self) (L193): Resolve the temp roots for this run.
- method TempCleaner._is_excluded(self, path: str, name: str) (L201): True when *path*/*name* hits a configured fnmatch pattern.
- method TempCleaner._is_old_enough(self, path: Path) (L208): True when *path*'s mtime clears the ``min_age_days`` floor.
- method TempCleaner._walk(self, root: Path, label: str, cutoff: float, findings: list[TempFinding]) (L223): Iteratively collect eligible files under *root* (read-only).
- method TempCleaner.scan(self) (L285): Scan all discovered temp roots. Read-only; never raises on IO issues.
- method TempCleaner.total_reclaimable(self) (L304): Total bytes across the most recent scan (0 before any scan).
- method TempCleaner.clean(self, findings: list[TempFinding], use_trash: bool=True, dry_run: bool=True) (L308): Delete the given findings via :class:`Deleter`.

## src/cortex_unified/core/utils.py — Shared utilities: logging setup, formatting, path helpers, error types.
- func get_system_excludes() (L15): System directories that must never be scanned or cleaned.
- func is_system_directory(path: Path) (L40): True if *path* names one of the platform's protected directories.
- func setup_logging(verbose: bool=False, log_file: str=None, json_logging: bool=False, component: str=None, log_level: str=None) (L45): Configure and return an application logger.
- class JSONFormatter(logging.Formatter) (L79): JSONFormatter.
- func format(self, record) (L81): format.
- class PerformanceFilter(logging.Filter) (L165): PerformanceFilter.
- func filter(self, record) (L167): filter.
- func get_component_logger(component: str, verbose: bool=False, log_file: str=None, json_logging: bool=False) (L179): Get a logger for a specific component with consistent configuration.
- func log_operation_start(logger: logging.Logger, operation: str, **kwargs) (L194): Log the start of an operation with context.
- func log_operation_end(logger: logging.Logger, context: dict, success: bool=True, error: Exception=None, **kwargs) (L214): Log the end of an operation with results.
- func log_performance_metrics(logger: logging.Logger, operation: str, metrics: dict) (L241): Log performance metrics for an operation.
- func generate_manifest_filename() (L257): Generate a timestamped filename for the manifest file.
- func normalize_path(path: str) (L262): Normalize a path string to a Path object.
- func get_file_age_days(filepath: Path) (L266): Get the age of a file in days.
- class DeepCleanerError(Exception) (L277): Base exception for Cortex Cleaner operations.
- method DeepCleanerError.__init__(self, message: str, operation: str=None, component: str=None, error_code: str=None, details: dict=None) (L284): __init__.
- class DockerError(DeepCleanerError) (L295): Docker-specific errors.
- class VisualizationError(DeepCleanerError) (L299): Visualization-specific errors.
- class HeuristicsError(DeepCleanerError) (L303): Heuristics and ML-specific errors.
- class PackageManagerError(DeepCleanerError) (L307): Package manager-specific errors.
- class PerformanceError(DeepCleanerError) (L311): Performance and resource-specific errors.
- class AccessibilityError(DeepCleanerError) (L315): Accessibility-specific errors.
- func handle_error(logger: logging.Logger, error: Exception, operation: str=None, component: str=None, reraise: bool=True) (L319): Centralized error handling with comprehensive logging.
- func safe_execute(func, logger: logging.Logger, operation: str=None, default_return=None, **kwargs) (L349): Safely execute a function with comprehensive error handling.
- class ResourceManager (L373): Context manager for resource cleanup and monitoring.
- method ResourceManager.__init__(self, logger: logging.Logger, operation: str=None) (L376): __init__.
- method ResourceManager.__enter__(self) (L385): __enter__.
- method ResourceManager.__exit__(self, exc_type, exc_val, exc_tb) (L392): __exit__.
- method ResourceManager.add_resource(self, resource) (L413): Add a resource to be cleaned up.
- method ResourceManager.add_cleanup_function(self, func, *args, **kwargs) (L417): add_cleanup_function.
- func format_bytes(bytes_value: int) (L422): Format a byte count for display.
- func format_duration(seconds: float) (L448): Format duration in human-readable format.
- func validate_path(path: str, must_exist: bool=True, must_be_dir: bool=False, must_be_file: bool=False) (L461): Validate and normalize a path with comprehensive checks.
- func ensure_directory(path: Path, create: bool=True) (L494): Ensure a directory exists, optionally creating it.
- func get_system_info() (L520): Get comprehensive system information for diagnostics.
- func create_error_report(error: Exception, context: dict=None) (L553): Create a comprehensive error report for debugging.

## src/cortex_unified/debug/__init__.py — Cortex Cleaner Production Debugging & Diagnostics Engine.
- (no classes/functions — constants/imports only)

## src/cortex_unified/debug/runner.py — Production-Grade Diagnostics and Debugging Runner.
- func _col(text: str, code: str) (L36): _col.
- func green(text: str) (L43): green.
- func red(text: str) (L50): red.
- func yellow(text: str) (L57): yellow.
- func cyan(text: str) (L64): cyan.
- func bold(text: str) (L71): bold.
- class DiagnosticItem (L79): DiagnosticItem.
- class DiagnosticSection (L91): DiagnosticSection.
- method DiagnosticSection.total(self) (L101): total.
- method DiagnosticSection.is_success(self) (L108): is_success.
- class DiagnosticReport (L117): DiagnosticReport.
- method DiagnosticReport.to_dict(self) (L128): to_dict.
- class DiagnosticRunner (L156): DiagnosticRunner.
- method DiagnosticRunner.__init__(self, verbose: bool=False) (L158): __init__.
- method DiagnosticRunner.run_section(self, title: str, fn: Callable[[DiagnosticSection], None]) (L168): run_section.
- method DiagnosticRunner.check_icons(self, sec: DiagnosticSection) (L197): Audit vector icon pipeline and SVG rendering.
- method DiagnosticRunner.check_system_tools(self, sec: DiagnosticSection) (L243): Audit all 55 system tools.
- method DiagnosticRunner.check_analyzers(self, sec: DiagnosticSection) (L275): Audit all 23 file and dedup analyzers.
- method DiagnosticRunner.check_core_engine(self, sec: DiagnosticSection) (L307): Audit Core Engine, FastWalk, and Security Guards.
- method DiagnosticRunner.check_caches_and_algorithms(self, sec: DiagnosticSection) (L364): Audit algorithmic performance caches & chunkers.
- method DiagnosticRunner.check_nexus_explorer(self, sec: DiagnosticSection) (L418): Audit Nexus File Manager subsystem & Fluent header.
- method DiagnosticRunner.check_ui_pages(self, sec: DiagnosticSection) (L654): Audit all 59 registered UI pages in shell.
- method DiagnosticRunner.run_all(self) (L699): run_all.
- method DiagnosticRunner._print_section_summary(self, sec: DiagnosticSection) (L774): _print_section_summary.
- func run_all_diagnostics(verbose: bool=False) (L792): run_all_diagnostics.
- func main() (L800): main.

## src/cortex_unified/engine/__init__.py — Cortex Cleaner high-performance engine.
- (no classes/functions — constants/imports only)

## src/cortex_unified/engine/categories.py — Data-driven, risk-annotated registry of cleanable locations.
- class RiskLevel(str, enum.Enum) (L25): How risky it is to remove a category's contents.
- method RiskLevel.rank(self) (L33): rank.
- class CleanupCategory (L41): A declarative cleanup target.
- method CleanupCategory.existing_paths(self) (L55): Subset of declared paths that actually exist on this machine.
- func _env_path(*names: str) (L67): Return existing directories for the first set env var among *names*.
- func _existing(paths) (L76): Filter to paths that currently exist (cheap, best-effort).
- func _fixed_drive_roots() (L151): Scan all fixed local drives for common temp/project directories.
- func _custom_temp_roots() (L172): Extra temp roots outside %TEMP% (user custom dirs, secondary drives).
- func _discover_app_caches(bases: list[Path], max_depth: int=6) (L196): Recursively find regenerable cache folders under *bases* (app-data roots).
- func _discover_app_caches._walk(path: Path, depth: int) (L214): _walk.
- func _safe_scandir(path: Path) (L243): List immediate subdirectories of *path*, ignoring errors.
- func _get_dir_size(path: Path) (L259): Fast estimate of reclaimable bytes under *path* (best-effort, no follow).
- func _ai_ide_recording_dirs(home: Path) (L274): AI IDE automation recording roots (Antigravity / Gemini browser_recordings + brain).
- func _docker_desktop_cache_dirs(local: Path) (L292): Filesystem cache used by Docker Desktop (parallel to SDK prune).
- func _cargo_cache_dirs(home: Path) (L315): Cargo registry + git checkouts (re-downloaded via cargo fetch).
- func _rustup_toolchain_dirs(home: Path) (L325): Rustup toolchains (opt-in, re-download via rustup toolchain install).
- func _scoop_cache_dirs(home: Path) (L336): Scoop package cache (scoop cache rm *).
- func _npm_pip_cache_dirs(home: Path, local: Path) (L359): Global package manager caches (npm, pip, etc.) for categories registry.
- func _wsl_vhdx_dirs(home: Path) (L384): WSL distro ext4.vhdx host files (compactable, not deletable; surfaced for info).
- func _browser_cache_dirs(local: Path) (L397): Existing browser cache directories across common Chromium browsers + Firefox.
- func _windows_categories() (L424): _windows_categories.
- func _posix_categories() (L772): _posix_categories.
- func default_categories() (L848): Return the platform-appropriate cleanup category registry.
- func categories_by_id() (L855): categories_by_id.

## src/cortex_unified/engine/cli.py — Modern, safe CLI for the Cortex engine.
- func _require_feature(feature) (L65): Gate a CLI command on a licensing Feature (clean click error if denied).
- func _fmt_memory_stats(stats: dict) (L74): Human rendering for ``cortex memory --stats-only``.
- func _find_app_by_name(name: str) (L93): Locate an installed/uninstalled app record by display name.
- func _echo_findings(findings, as_json: bool) (L107): _echo_findings.
- func _fmt_bytes(n: int) (L125): _fmt_bytes.
- func main() (L141): Cortex Cleaner - fast, safe, storage-aware system cleanup.
- func scan(as_json: bool, include_disabled: bool, max_risk: str) (L148): Report reclaimable space by category (read-only).
- func clean(apply: bool, method: str, include_disabled: bool, max_risk: str) (L180): Reclaim space. Dry-run unless --apply is given.
- func duplicates(paths: tuple[str, ...], as_json: bool) (L213): Find duplicate files across PATHS.
- func large(path: str, min_mb: float, limit: int) (L231): List the largest files under PATH.
- func empty(path: str) (L238): List empty files and directories under PATH.
- func shred(target: str, apply: bool, passes: int, force_flash: bool) (L250): Securely delete TARGET (storage-aware; honest about SSD limits).
- func leftovers() (L273): Find and clean what uninstallers leave behind (files/registry).
- func leftovers_scan(app_name: str, as_json: bool) (L279): Scan APP_NAME's leftovers (read-only; works after uninstall too).
- func leftovers_orphans(as_json: bool) (L290): List Program Files folders no installed app claims (read-only).
- func leftovers_clean(app_name: str, apply: bool, min_level: str, restore_point: bool, as_json: bool) (L309): Clean APP_NAME's leftovers. Dry-run unless --apply.
- func license() (L367): View and manage this machine's Cortex license.
- func license_status(as_json: bool) (L372): Show the current tier, features and expiry (works offline).
- func license_activate(key: str, tier: str, name: str, email: str, days: int, as_json: bool) (L403): Bind KEY to this machine and activate TIER (fully offline).
- func license_trial(as_json: bool) (L421): license_trial.
- func license_deactivate() (L436): Remove the license; this machine returns to the Free tier.
- func boost() (L444): Gaming/session performance boosts (Premium).
- func boost_status(as_json: bool) (L449): Preview what a boost would change on this machine right now.
- func boost_start(dry_run: bool, extra_suspend: tuple, as_json: bool) (L468): Apply the gaming boost (power plan + background quieting).
- func boost_stop(as_json: bool) (L484): Restore the pre-boost power plan and resume paused apps.
- func debug(as_json: bool, verbose: bool) (L495): Run comprehensive system & codebase production diagnostics.
- func memory(min_rss_mb: int, apply: bool, stats_only: bool, as_json: bool) (L512): Memory stats + working-set trim (Premium; dry-run by default).
- func main() (L529): main.

## src/cortex_unified/engine/fastwalk.py — High-performance filesystem traversal built on ``os.scandir``.
- class WalkOptions (L43): Tunable traversal parameters.
- class FastWalker (L77): Streaming, cancellable directory walker.
- method FastWalker.__init__(self, options: WalkOptions | None=None) (L84): __init__.
- method FastWalker.cancel(self) (L97): Request cooperative cancellation of an in-progress walk.
- method FastWalker.reset(self) (L101): reset.
- method FastWalker._excluded_dir(self, name: str, full: str) (L112): _excluded_dir.
- method FastWalker._matches_patterns(self, name: str, full: str) (L120): _matches_patterns.
- method FastWalker.iter_files(self, root: os.PathLike[str] | str, on_error: Callable[[str], None] | None=None, progress: ProgressCallback | None=None) (L134): Yield :class:`FileEntry` for every matching file under *root*.
- method FastWalker.scan(self, root: os.PathLike[str] | str, progress: ProgressCallback | None=None) (L227): Materialize a full :class:`ScanResult` (files, dirs, totals, errors).
- method FastWalker.find_empty(self, root: os.PathLike[str] | str) (L253): Return (empty_files, empty_dirs) using a single scandir pass.
- func FastWalker.find_empty._visit(dpath: str) (L268): _visit.
- method FastWalker.scan_ntfs_usn(self, volume_root: os.PathLike[str] | str, progress_callback: ProgressCallback | None=None) (L313): High-speed NTFS MFT/USN journal streaming on Windows.

## src/cortex_unified/engine/guard.py — Path safety guard for destructive operations.
- class GuardVerdict (L26): Outcome of a safety check.
- method GuardVerdict.__bool__(self) (L32): __bool__.
- func _windows_protected() (L39): _windows_protected.
- func _posix_protected() (L61): _posix_protected.
- class PathGuard (L74): Decides whether a path is safe to delete/overwrite.
- method PathGuard.__init__(self, sandbox: os.PathLike[str] | str | None=None, allow_system: bool=False) (L77): __init__.
- method PathGuard.check(self, path: os.PathLike[str] | str) (L95): Return a :class:`GuardVerdict` for *path*.
- method PathGuard.is_writable(self, path: os.PathLike[str] | str) (L124): True if *path* (or its parent, for not-yet-existing paths) is writable.
- method PathGuard._is_within(child: Path, parent: Path) (L135): Robust replacement for prefix matching (handles sibling-name traps).

## src/cortex_unified/engine/hashing.py — Fast content hashing and duplicate detection.
- func _new_hasher() (L56): Construct the fastest available hasher (see HASH_ALGORITHM).
- func hash_file(path: os.PathLike[str] | str, limit: int | None=None) (L65): Return the hex digest of *path* (or its first ``limit`` bytes).
- class DuplicateFinderEngine (L89): Find duplicate files among an arbitrary set of paths.
- method DuplicateFinderEngine.__init__(self, workers: int=0) (L92): __init__.
- method DuplicateFinderEngine.find(self, entries: list[tuple[Path, int]], progress: Callable[[int, int], None] | None=None) (L101): Return ``{content_hash: [paths...]}`` for groups with >1 member.
- method DuplicateFinderEngine._group_by_hash(self, paths: list[Path], limit: int | None, progress: Callable[[int, int], None] | None) (L130): _group_by_hash.
- method DuplicateFinderEngine.wasted_bytes(groups: dict[str, list[Path]]) (L155): Bytes reclaimable by keeping one copy per duplicate group.

## src/cortex_unified/engine/models.py — Immutable-ish data models shared across the engine.
- class StorageKind(str, enum.Enum) (L17): Physical medium backing a path.
- method StorageKind.overwrite_effective(self) (L34): True only when physically overwriting bytes reliably destroys data.
- class DeletionMethod(str, enum.Enum) (L39): How an item should be removed.
- class DeletionOutcome(str, enum.Enum) (L48): Result of a single item deletion.
- class FileEntry (L60): A single filesystem entry discovered during a scan.
- method FileEntry.age_days(self) (L84): age_days.
- method FileEntry.reclaimable_size(self) (L92): Bytes that deleting this entry would actually free.
- method FileEntry.is_cloud_placeholder(self) (L104): True when the content lives in the cloud, not on this disk.
- method FileEntry.is_junction(self) (L110): True for a junction / volume mount point (not a symlink to Python).
- method FileEntry.special_note(self) (L116): Short human explanation of any special storage behaviour, or ``""``.
- method FileEntry.to_dict(self) (L121): to_dict.
- class ScanResult (L138): Aggregate result of a traversal.
- method ScanResult.error_count(self) (L156): error_count.
- method ScanResult.to_dict(self) (L162): to_dict.
- class DeletionResult (L181): Per-item deletion record plus batch aggregation helpers.
- method DeletionResult.succeeded(self) (L192): succeeded.
- method DeletionResult.to_dict(self) (L198): to_dict.

## src/cortex_unified/engine/secure_delete.py — Storage-aware deletion with honest guarantees.
- func _resolve_send2trash() (L45): Import ``send2trash`` once and cache the result (``None`` if absent).
- func _has_trash() (L61): True when reversible recycle-to-trash is actually available.
- func __getattr__(name: str) (L66): Keep the historical module-level names working (:pep:`562`).
- class OverwriteNotEffective(RuntimeError) (L85): Raised when an overwrite wipe is requested on non-rotational media.
- method OverwriteNotEffective.__init__(self, kind: StorageKind, path: Path) (L92): __init__.
- class SecureDeleter (L105): Deletes files/directories with a chosen :class:`DeletionMethod`.
- method SecureDeleter.__init__(self, guard: PathGuard | None=None, probe: StorageProbe | None=None, overwrite_passes: int=3) (L108): __init__.
- method SecureDeleter.delete(self, path: os.PathLike[str] | str, method: DeletionMethod=DeletionMethod.RECYCLE, force_overwrite_on_flash: bool=False) (L124): Delete a single file or directory and record the result.
- method SecureDeleter.delete_many(self, paths: list[os.PathLike[str] | str], method: DeletionMethod=DeletionMethod.RECYCLE, progress=None, cancel_event=None, sizes: 'dict[str, int] | None'=None) (L179): Delete many paths efficiently.
- method SecureDeleter._fast_safe(self, p: Path, approved: dict[str, bool]) (L222): Guard-check *p* cheaply by caching the verdict of its parent dir.
- method SecureDeleter._delete_batch(self, files: list[Path], dirs: list[Path], method: DeletionMethod, progress=None, cancel_event=None, sizes: 'dict[str, int] | None'=None) (L243): Fast permanent-delete path: one guard check per directory, known
- func SecureDeleter._delete_batch._size(p: Path) (L253): _size.
- method SecureDeleter._recycle_batch(self, items: list[Path], progress=None, cancel_event=None, chunk: int=40, sizes: 'dict[str, int] | None'=None) (L298): Recycle *items* in chunks; fall back to per-file only for chunks that
- func SecureDeleter._recycle_batch._size(p: Path) (L313): _size.
- method SecureDeleter._recycle(self, p: Path, size: int) (L366): _recycle.
- method SecureDeleter._plain_delete(self, p: Path, size: int) (L382): _plain_delete.
- method SecureDeleter._is_cloud_placeholder(p: Path) (L393): True when *p* is a dehydrated cloud file (OneDrive Files On-Demand).
- method SecureDeleter._overwrite_delete(self, p: Path, size: int, force: bool) (L406): _overwrite_delete.
- method SecureDeleter._overwrite_file(self, p: Path) (L442): Overwrite file contents in place, then flush to the physical device.
- method SecureDeleter._record(self, p: Path, outcome: DeletionOutcome, method: DeletionMethod, size: int, reason: str='') (L466): _record.
- method SecureDeleter._quick_locked(p: Path) (L476): Cheap check: is this file exclusively locked (in use)?
- method SecureDeleter._size_of(p: Path) (L494): _size_of.
- method SecureDeleter.adaptive_delete(self, path: os.PathLike[str] | str, level: str | None=None, verify: bool=True) (L512): Adaptive sanitization (PL0-PL3) per 2025 research.
- method SecureDeleter.summary(self) (L544): Aggregate counters over all recorded results.

## src/cortex_unified/engine/service.py — High-level cleaner service - the single orchestration entry point.
- func _throttle(cb: 'Callable[[str], None] | None', interval: float=0.1) (L38): Wrap a progress callback so it fires at most every *interval* seconds.
- func _throttle.wrapped(msg: str) (L49): wrapped.
- class CategoryScan (L62): Scan outcome for one cleanup category.
- method CategoryScan.file_count(self) (L75): file_count.
- method CategoryScan.breakdown(self, limit: int=200) (L81): Group this category's files into their top folders for preview.
- method CategoryScan.to_dict(self) (L118): to_dict.
- class CleanupReport (L135): Aggregate of all scanned categories.
- method CleanupReport.total_reclaimable_bytes(self) (L142): total_reclaimable_bytes.
- method CleanupReport.total_files(self) (L149): total_files.
- method CleanupReport.cloud_skipped(self) (L156): Total cloud placeholders excluded across all categories.
- method CleanupReport.cloud_skipped_bytes(self) (L161): Logical size of the excluded placeholders (not local, not reclaimable).
- method CleanupReport.cloud_note(self) (L166): One-line explanation of skipped cloud files, or ``""`` when none.
- method CleanupReport.to_dict(self) (L179): to_dict.
- class CleanerService (L193): Unified, safe orchestration of scanning and reclamation.
- method CleanerService.__init__(self, guard: PathGuard | None=None, probe: StorageProbe | None=None) (L196): __init__.
- method CleanerService.scan_categories(self, category_ids: list[str] | None=None, max_risk: RiskLevel=RiskLevel.MEDIUM, include_disabled: bool=False, progress: 'Callable[[str], None] | None'=None, cancel_event=None) (L209): Scan cleanup categories and report reclaimable space.
- method CleanerService.clean_categories(self, report: CleanupReport, method: DeletionMethod=DeletionMethod.DRY_RUN, progress: 'Callable[[int, int], None] | None'=None, cancel_event=None) (L250): Remove everything discovered in *report* using *method*.
- method CleanerService.find_duplicates(self, roots: list[str | Path], min_size: int=1, progress: 'Callable[[str], None] | None'=None, cancel_event=None, extensions: 'set[str] | None'=None) (L274): Find duplicate files across one or more root directories.
- func CleanerService.find_duplicates._rep(cur_dir, seen) (L294): _rep.
- func CleanerService.find_duplicates._hprog(done, total) (L307): _hprog.
- method CleanerService.find_large_files(self, root: str | Path, min_mb: float=100.0, limit: int=100, progress: 'Callable[[str], None] | None'=None, cancel_event=None) (L315): Return the largest files under *root* above *min_mb*, biggest first.
- func CleanerService.find_large_files._rep(cur_dir, seen) (L331): _rep.
- method CleanerService.find_empty(self, root: str | Path, cancel_event=None) (L342): Return (empty_files, empty_dirs) under *root*.
- method CleanerService._select_categories(self, ids: list[str] | None, max_risk: RiskLevel, include_disabled: bool) (L355): _select_categories.
- method CleanerService._scan_category(self, cat: CleanupCategory, progress=None, cancel_event=None) (L369): _scan_category.
- func CleanerService._scan_category._report(cur_dir, seen, _label=cat.label) (L393): _report.
- func _matches_any(name: str, globs: tuple[str, ...]) (L415): _matches_any.

## src/cortex_unified/engine/storage.py — Cross-platform storage-medium detection.
- class StorageInfo (L54): Result of probing the medium behind a path.
- method StorageInfo.overwrite_effective(self) (L62): overwrite_effective.
- class StorageProbe (L69): Detects the physical medium for a given path, with per-mount caching.
- method StorageProbe.__init__(self) (L72): __init__.
- method StorageProbe.probe(self, path: os.PathLike[str] | str) (L79): Return :class:`StorageInfo` for the medium hosting *path*.
- method StorageProbe._mount_key(self, path: Path) (L94): _mount_key.
- method StorageProbe._probe_uncached(self, path: Path, anchor: str) (L108): _probe_uncached.
- method StorageProbe._probe_windows(self, drive_letter: str) (L122): _probe_windows.
- method StorageProbe._probe_linux(self, path: Path) (L152): _probe_linux.
- method StorageProbe._probe_macos(self, path: Path) (L179): _probe_macos.
- method StorageProbe._run(cmd: list[str]) (L194): _run.
- func _shared_probe() (L212): _shared_probe.
- func detect_storage(path: os.PathLike[str] | str) (L219): Convenience wrapper using a process-wide cached probe.

## src/cortex_unified/engine/winattrs.py — Windows file-attribute and reparse-point classification.
- func attrs_of(st: Any) (L72): Return ``st_file_attributes`` from a stat result (0 when unavailable).
- func reparse_tag_of(st: Any) (L77): Return ``st_reparse_tag`` from a stat result (0 when unavailable).
- func is_reparse_point(attrs: int) (L92): True when the entry is a reparse point of any kind.
- func is_cloud_tag(tag: int) (L97): True when *tag* belongs to the Windows cloud-filter tag family.
- func is_dehydrated(attrs: int) (L102): True when opening the entry would trigger a download.
- func is_cloud(attrs: int, tag: int=0) (L113): True when the entry is managed by a cloud sync engine.
- func is_junction(tag: int) (L122): True for a junction or volume mount point.
- func size_may_be_misleading(attrs: int) (L132): True when the allocated size should be measured instead of trusted.
- func describe(attrs: int, tag: int=0) (L137): Return a short human note about special storage behaviour, or ``""``.
- func on_disk_size(path: str | os.PathLike[str], logical_size: int | None=None) (L160): Return the bytes *actually allocated* for ``path``, or ``None``.

## src/cortex_unified/explorer/__init__.py — Cortex Cleaner Explorer Subsystem.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/archive.py — Archive inspector and extraction module.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/cloud.py — Cloud integration module.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/content_search.py — File content search and ripgrep integration.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/core.py — Native core file engine and table model.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/ffi.py — Rust FFI bridge for high-performance filesystem operations.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/folder_tree.py — Filesystem tree view navigation widget.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/icons.py — Vector icon pipeline for Explorer subsystem.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/indexer.py — Fast background filesystem indexing engine.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/network.py — Network filesystem and remote share explorer.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/plugins.py — Plugin architecture and extension manager.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/transfers.py — File transfer queue and progress monitoring module.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/undo.py — Undo and redo file operation history stack.
- (no classes/functions — constants/imports only)

## src/cortex_unified/explorer/widget.py — Fluent Qt6 File Explorer Widget module.
- (no classes/functions — constants/imports only)

## src/cortex_unified/i18n/__init__.py — Backwards-compatibility alias for cortex_unified.translations.
- (no classes/functions — constants/imports only)

## src/cortex_unified/licensing/__init__.py — Offline-first licensing and entitlement system.
- (no classes/functions — constants/imports only)

## src/cortex_unified/licensing/fingerprint.py — Stable, privacy-preserving machine fingerprint for license binding.
- func _windows_ids() (L35): _windows_ids.
- func _macos_ids() (L62): _macos_ids.
- func _linux_ids() (L86): _linux_ids.
- func collect_identifiers() (L103): Return labelled platform identifiers (never persisted or logged).
- func compute_fingerprint() (L122): Return the stable SHA-256 hex digest identifying this machine.
- func get_fingerprint() (L128): Memoised :func:`compute_fingerprint` (identifiers never change mid-run).
- func reset_cache() (L136): Forget the memoised digest (used by tests and diagnostics).

## src/cortex_unified/licensing/gating.py — Entitlement checks: the single gateway every gated feature goes through.
- class EntitlementError(PermissionError) (L39): Raised by :func:`require` when a feature's tier is not licensed.
- method EntitlementError.__init__(self, feature: Feature, required: Tier, current: Tier, message: str | None=None) (L42): __init__.
- func current_tier() (L57): The effective tier of this machine right now.
- func effective_features() (L62): Every feature unlocked on this machine right now.
- func allowed(feature: Feature) (L67): True if *feature* may be used right now (never raises).
- func require(feature: Feature) (L80): Raise :class:`EntitlementError` unless *feature* is licensed.
- func gate(feature: Feature) (L90): Decorator form of :func:`require` for whole functions/methods.
- func gate.decorator(func: Callable[..., T]) (L93): decorator.
- func gate.decorator.wrapper(*args: object, **kwargs: object) (L95): wrapper.
- func reset_cache() (L117): Drop memoised validation state (tests only).

## src/cortex_unified/licensing/license_manager.py — Offline license activation, validation and trial management.
- func _today() (L57): _today.
- func _parse_date(value: str) (L64): _parse_date.
- class LicensePayload (L75): The signed, machine-bound content of a license.
- method LicensePayload.canonical(self) (L88): Deterministic serialization used for both signing and verifying.
- method LicensePayload.sign(self) (L101): sign.
- method LicensePayload.verify_signature(self, signature: str) (L107): verify_signature.
- method LicensePayload.from_dict(cls, raw: dict[str, Any]) (L114): from_dict.
- class LicenseState (L135): Result of validating the stored license right now.
- method LicenseState.features(self) (L150): features.
- method LicenseState.allows(self, feature: Feature) (L154): allows.
- method LicenseState.to_dict(self) (L158): to_dict.
- method LicenseState._masked_key(self) (L175): _masked_key.
- func license_path() (L186): Where this machine's license lives (per-user, no admin rights).
- class LicenseManager (L191): Activate, validate and revoke the local license. Thread-safe.
- method LicenseManager.__init__(self, path: Path | None=None) (L200): __init__.
- method LicenseManager._file_signature(path: Path) (L213): Cheap identity of the on-disk license (None when absent).
- method LicenseManager.invalidate(self) (L221): Drop memoised state so the next ``validate`` re-reads disk.
- method LicenseManager._save(self, payload: LicensePayload) (L227): Atomically write the signed license (tmp + replace).
- method LicenseManager._load_document(self) (L240): _load_document.
- method LicenseManager.activate(self, key: str, tier: Tier, name: str='', email: str='', term_days: int=DEFAULT_TERM_DAYS) (L261): Install and sign a new license bound to this machine.
- method LicenseManager.start_trial(self) (L293): Start the once-per-machine PRO trial.
- method LicenseManager.deactivate(self) (L305): Remove the local license entirely (machine returns to Free).
- method LicenseManager.validate(self) (L316): Validate the stored license now.
- method LicenseManager._validate_uncached(self) (L332): _validate_uncached.
- method LicenseManager.status(self) (L379): status.
- func get_license_manager() (L390): Process-wide singleton (tests may construct their own instances).
- func reset_singleton() (L399): Forget the singleton (test isolation).

## src/cortex_unified/licensing/tiers.py — Tier and feature definitions for Cortex Cleaner.
- class Tier(str, Enum) (L19): Licensed editions, ordered cheapest to most capable.
- method Tier.rank(self) (L29): Monotonic capability rank; higher unlocks strictly more.
- method Tier.includes(self, minimum: 'Tier') (L33): True if this tier satisfies a feature's minimum-tier requirement.
- method Tier.parse(cls, value: str | None) (L38): Parse user/server supplied text into a Tier (Free on garbage).
- class Feature(str, Enum) (L55): Stable identifiers of every gateable capability.
- func features_for_tier(tier: Tier) (L130): Every feature unlocked by *tier* (cumulative across tiers below it).

## src/cortex_unified/performance/__init__.py — Performance optimization and monitoring module for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/performance/multi_drive_scanner.py — Parallel scanning across multiple drives, volumes, and user profiles.
- class DriveInfo (L34): Data structure for drive information.
- method DriveInfo.used_size(self) (L46): Bytes in use: total minus free.
- method DriveInfo.usage_percent(self) (L51): Used share of capacity; 0.0 when total size is zero.
- class NetworkDrive (L58): Connection and authentication state for a network share.
- class UserProfile (L69): One detectable OS user profile plus access metadata.
- class ScanProgress (L81): Counters describing progress through a multi-location scan.
- method ScanProgress.__post_init__(self) (L91): __post_init__.
- method ScanProgress.overall_progress(self) (L99): overall_progress.
- class AggregatedResult (L110): Totals and summary statistics merged across all scanned locations.
- class MultiUserScanner (L120): Scans across multiple OS user profiles with per-profile permission handling.
- method MultiUserScanner.__init__(self, config: Any=None) (L127): Set up scan state.
- method MultiUserScanner.detect_user_profiles(self) (L139): Enumerate user profiles with permission and activity metadata.
- method MultiUserScanner._detect_windows_user_profiles_enhanced(self) (L170): Enumerate C:/Users subdirectories, skipping built-in accounts.
- method MultiUserScanner._detect_unix_user_profiles_enhanced(self) (L213): Enumerate /home entries plus /root when accessible.
- method MultiUserScanner._check_path_permissions(self, path: Path) (L265): Probe read/write/execute access for the current process via os.access.
- method MultiUserScanner._get_windows_last_login(self, username: str) (L278): Best-effort last logon time via the net user command; None when unavailable.
- method MultiUserScanner._get_unix_last_login(self, username: str) (L313): Get last login time for Unix user.
- method MultiUserScanner._is_user_active_windows(self, username: str) (L338): True when the profile is logged in (its registry hive is loaded).
- method MultiUserScanner._is_user_active_unix(self, username: str) (L352): True if the username appears in who output.
- method MultiUserScanner.scan_user_profile(self, profile: UserProfile, scanner_factory: Optional[Callable]=None) (L366): Walk one user profile; permission gaps degrade to partial results.
- method MultiUserScanner.handle_permissions(self, path: str) (L407): Check access to a path and whether elevation would grant it.
- method MultiUserScanner._can_elevate(self) (L440): True when a UAC elevation prompt can succeed for this session.
- method MultiUserScanner.aggregate_results(self, results: Dict[str, Dict[str, Any]]) (L451): Aggregate results with cross-location analysis.
- class DriveManager (L490): Enhanced drive management with monitoring and network drive support.
- method DriveManager.__init__(self, config: Any=None) (L493): __init__.
- method DriveManager.detect_all_drives(self) (L505): Detect all available drives including network and removable drives.
- method DriveManager._create_drive_info(self, partition) (L543): Create DriveInfo object from partition information.
- method DriveManager._get_drive_type(self, partition) (L577): Determine the type of drive.
- method DriveManager._get_drive_label(self, path: str) (L605): _get_drive_label.
- method DriveManager._fallback_drive_detection(self) (L635): _fallback_drive_detection.
- method DriveManager._detect_windows_drives(self) (L652): Drive discovery via PowerShell when psutil returns nothing.
- method DriveManager._detect_unix_drives(self) (L696): Drive discovery via /proc/mounts when psutil returns nothing.
- method DriveManager.handle_network_drives(self, credentials: Dict[str, str]=None) (L723): Detect shares, prompt-free auth via stored credentials, reconnect as needed.
- method DriveManager._process_network_drive(self, partition) (L746): Process a single network drive partition.
- method DriveManager._store_credentials(self, credentials: Dict[str, str]) (L773): Securely store network drive credentials.
- method DriveManager._get_stored_credentials(self, server: str) (L804): Retrieve stored credentials for a server.
- method DriveManager._attempt_network_connection(self, network_drive: NetworkDrive, credentials: Dict[str, str]) (L818): Attempt to connect to a network drive with credentials.
- method DriveManager._connect_windows_network_drive(self, network_drive: NetworkDrive, credentials: Dict[str, str]) (L825): _connect_windows_network_drive.
- method DriveManager._connect_unix_network_drive(self, network_drive: NetworkDrive, credentials: Dict[str, str]) (L850): _connect_unix_network_drive.
- method DriveManager.monitor_drive_changes(self, callback: Callable[[str, str], None]) (L857): Poll for attach/remove events; invoke callbacks on each change.
- method DriveManager._start_monitoring(self) (L864): Start drive monitoring in a separate thread.
- method DriveManager._monitor_loop(self) (L873): Main monitoring loop.
- method DriveManager._notify_drive_change(self, drive_path: str, change_type: str) (L903): Notify callbacks of drive changes.
- method DriveManager.handle_disconnected_drives(self, drive_id: str) (L911): Attempt reconnects for dropped drives; skip after retries run out.
- method DriveManager.stop_monitoring(self) (L938): Stop drive monitoring.
- method DriveManager._parse_network_path(self, device_path: str) (L944): Parse network device path to extract server and share.
- class MultiDriveScanner (L965): Enhanced multi-drive scanner with comprehensive functionality.
- method MultiDriveScanner.__init__(self, config: Any=None) (L968): Initialize multi-drive scanner with configuration.
- method MultiDriveScanner.detect_drives(self) (L978): Detect drives using the enhanced DriveManager.
- method MultiDriveScanner.detect_all_drives(self) (L982): Detect all available drives on the system.
- method MultiDriveScanner.scan_multiple_drives(self, drives: List[str], parallel: bool=True, scanner_factory: Optional[Callable]=None) (L1036): Enhanced multi-drive scanning with progress tracking and error handling.
- func MultiDriveScanner.scan_multiple_drives.default_scanner_factory(path: str) (L1053): default_scanner_factory.
- method MultiDriveScanner._scan_drives_parallel(self, drives: List[str], scanner_factory: Callable) (L1082): Scan drives in parallel with progress tracking.
- method MultiDriveScanner._scan_drives_sequential(self, drives: List[str], scanner_factory: Callable) (L1119): Scan drives sequentially with progress tracking.
- method MultiDriveScanner._scan_single_drive_with_progress(self, drive_path: str, scanner_factory: Callable) (L1149): Walk one drive, streaming per-file progress to registered callbacks.
- method MultiDriveScanner._scan_single_drive(self, drive_path: str, scanner_factory: Callable) (L1191): _scan_single_drive.
- method MultiDriveScanner.handle_network_drives(self, credentials: Dict[str, str]=None) (L1204): Handle network drives using the enhanced DriveManager.
- method MultiDriveScanner.monitor_drive_changes(self, callback: Callable[[str, str], None]) (L1208): monitor_drive_changes.
- method MultiDriveScanner.handle_disconnected_drives(self, drive_id: str) (L1214): handle_disconnected_drives.
- method MultiDriveScanner.scan_user_profiles(self, admin_mode: bool=False) (L1220): Enhanced multi-user profile scanning with progress tracking.
- method MultiDriveScanner.detect_user_profiles(self, admin_mode: bool=False) (L1271): Detect user profiles using the enhanced MultiUserScanner.
- method MultiDriveScanner.add_progress_callback(self, callback: Callable[[str], None]) (L1275): add_progress_callback.
- method MultiDriveScanner._notify_progress(self, message: str) (L1281): Enhanced progress notification with detailed progress information.
- method MultiDriveScanner.get_scan_progress(self) (L1294): Get current scan progress information.
- method MultiDriveScanner.get_scan_results(self) (L1299): Get all scan results.
- method MultiDriveScanner.get_aggregated_results(self) (L1304): Get aggregated scan results.
- method MultiDriveScanner.clear_results(self) (L1312): Clear all scan results.
- method MultiDriveScanner.scan_multiple_locations(self, locations: List[Dict[str, Any]], parallel: bool=True) (L1318): scan_multiple_locations.
- method MultiDriveScanner.stop_monitoring(self) (L1389): Stop all monitoring activities.

## src/cortex_unified/performance/optimization.py — Performance optimization utilities for Cortex Cleaner operations.
- class OptimizationSettings (L19): Settings for performance optimization.
- class PerformanceOptimizer (L32): Optimizes performance for Cortex Cleaner operations.
- method PerformanceOptimizer.__init__(self, settings: OptimizationSettings=None, logger: logging.Logger=None) (L35): Initialize performance optimizer.
- method PerformanceOptimizer.start_optimization(self) (L59): Start performance optimization.
- method PerformanceOptimizer.stop_optimization(self) (L84): Stop performance optimization and restore defaults.
- method PerformanceOptimizer._optimize_garbage_collection(self) (L103): _optimize_garbage_collection.
- method PerformanceOptimizer._start_memory_monitoring(self) (L119): Start memory usage monitoring.
- func PerformanceOptimizer._start_memory_monitoring.monitor_memory() (L126): monitor_memory.
- method PerformanceOptimizer._trigger_memory_cleanup(self) (L156): Trigger aggressive memory cleanup.
- method PerformanceOptimizer._clear_internal_caches(self) (L174): _clear_internal_caches.
- method PerformanceOptimizer.get_optimal_thread_count(self, operation_type: str='default') (L182): Get optimal thread count for an operation.
- method PerformanceOptimizer.get_optimal_buffer_size(self, file_size: int=0) (L214): Get optimal buffer size for file operations.
- method PerformanceOptimizer.should_use_streaming(self, data_size: int) (L233): Determine if streaming should be used for large data.
- method PerformanceOptimizer.optimize_for_operation(self, operation_name: str, operation_func: Callable, *args, **kwargs) (L245): Execute an operation with optimization.
- method PerformanceOptimizer._get_current_memory_mb(self) (L295): Get current memory usage in MB.
- method PerformanceOptimizer.get_performance_report(self) (L308): Get comprehensive performance report.
- method PerformanceOptimizer.suggest_optimizations(self) (L351): Suggest performance optimizations based on current state.
- method PerformanceOptimizer.export_performance_data(self, filepath: str) (L399): Export performance data to file.

## src/cortex_unified/performance/profiler.py — Performance profiling and monitoring for Cortex Cleaner operations.
- class ProfileReport (L12): Report containing profiling information.
- method ProfileReport.to_dict(self) (L21): to_dict.
- class OperationProfiler (L34): Profiles operations for performance analysis.
- method OperationProfiler.__init__(self) (L37): __init__.
- method OperationProfiler.profile_operation(self, operation_name: str) (L47): Context manager for profiling operations.
- method OperationProfiler.start_operation(self, operation_name: str) (L55): Start profiling an operation.
- method OperationProfiler.end_operation(self) (L61): End profiling and create report.
- method OperationProfiler.get_reports(self) (L81): Get all profiling reports.
- method OperationProfiler.get_report_by_name(self, operation_name: str) (L85): Get reports for specific operation.
- method OperationProfiler.clear_reports(self) (L89): Clear all profiling reports.
- method OperationProfiler.get_summary(self) (L94): Get summary of all profiling data.

## src/cortex_unified/performance/resource_monitor.py — Resource monitoring and management for Cortex Cleaner operations.
- class SystemMetrics (L17): System resource metrics at a point in time.
- class ResourceMonitor (L30): Monitors system resources and provides optimization recommendations.
- method ResourceMonitor.__init__(self, logger: logging.Logger=None) (L33): Initialize resource monitor.
- method ResourceMonitor.start_monitoring(self, interval: float=1.0) (L55): Start continuous resource monitoring.
- method ResourceMonitor.stop_monitoring(self) (L70): Stop resource monitoring.
- method ResourceMonitor.add_callback(self, callback: Callable[[SystemMetrics], None]) (L80): Add callback for resource updates.
- method ResourceMonitor.remove_callback(self, callback: Callable[[SystemMetrics], None]) (L88): Remove callback for resource updates.
- method ResourceMonitor.get_current_metrics(self) (L97): Get current system metrics.
- method ResourceMonitor._monitor_loop(self) (L149): Main monitoring loop.
- method ResourceMonitor._add_to_history(self, metrics: SystemMetrics) (L194): Add metrics to history with size limit.
- method ResourceMonitor._check_thresholds(self, metrics: SystemMetrics) (L202): Check resource thresholds and log warnings.
- method ResourceMonitor.get_metrics_summary(self, duration_minutes: int=5) (L214): Get summary of metrics over specified duration.
- method ResourceMonitor.get_optimization_recommendations(self) (L254): Get optimization recommendations based on current metrics.
- method ResourceMonitor.should_throttle_operations(self) (L287): Determine if operations should be throttled based on system load.
- method ResourceMonitor.get_recommended_thread_count(self) (L304): Get recommended thread count based on system load.
- method ResourceMonitor.export_metrics(self, filepath: str, duration_hours: int=1) (L327): Export metrics history to file.

## src/cortex_unified/performance/resource_throttler.py — Resource throttling and system performance management.
- class SystemLoad (L14): Data structure for system load information.
- method SystemLoad.is_high_load(self, cpu_threshold: float=80.0, memory_threshold: float=85.0) (L22): Check if system is under high load.
- class ResourceThrottler (L27): Manages system resource usage and throttling.
- method ResourceThrottler.__init__(self, cpu_limit: float=0.8, io_priority: str='low', memory_limit: float=0.85) (L30): Initialize resource throttler with limits.
- method ResourceThrottler.set_process_priority(self, priority: str) (L50): Set process priority for CPU and I/O operations.
- method ResourceThrottler.set_eco_qos(self, enable: bool=True) (L92): Enable Windows 11 EcoQoS (Efficiency Mode) to schedule background
- class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure) (L102): PROCESS_POWER_THROTTLING_STATE.
- method ResourceThrottler.get_system_load(self) (L137): Get current system load information.
- method ResourceThrottler.throttle_if_needed(self) (L189): Apply throttling if system resources are constrained.
- method ResourceThrottler.adjust_thread_count(self, current_threads: int) (L214): Adjust thread count based on system load.
- method ResourceThrottler.start_monitoring(self, interval: float=1.0) (L238): Start continuous system monitoring.
- func ResourceThrottler.start_monitoring.monitor_loop() (L245): monitor_loop.
- method ResourceThrottler.stop_monitoring(self) (L259): Stop continuous system monitoring.
- method ResourceThrottler.get_cached_load(self) (L265): Get the last cached system load without new measurement.
- method ResourceThrottler.is_throttling_active(self) (L270): Check if throttling is currently active.
- method ResourceThrottler.get_throttle_delay(self) (L274): Get current throttling delay.
- method ResourceThrottler.reset_throttling(self) (L278): Reset throttling state.

## src/cortex_unified/performance/scan_manager.py — Scan management with checkpoint and resume functionality.
- class ScanCheckpoint (L15): Data structure for scan checkpoint information.
- method ScanCheckpoint.to_dict(self) (L26): Convert checkpoint to dictionary for serialization.
- method ScanCheckpoint.from_dict(cls, data: Dict[str, Any]) (L33): from_dict.
- class ScanProgress (L41): Data structure for scan progress information.
- class ScanManager (L51): Manages scan operations with checkpoint and resume capabilities.
- method ScanManager.__init__(self, config: Any=None) (L54): Initialize scan manager with configuration.
- method ScanManager.create_checkpoint(self, scan_state: Dict[str, Any]) (L74): Create a checkpoint of current scan state.
- method ScanManager.load_checkpoint(self, checkpoint_id: str) (L112): Load scan state from checkpoint.
- method ScanManager.pause_scan(self) (L146): Pause current scan operation.
- method ScanManager.resume_scan(self, checkpoint_id: Optional[str]=None) (L151): Resume scan from checkpoint or current state.
- method ScanManager.is_paused(self) (L159): Check if scan is currently paused.
- method ScanManager.wait_if_paused(self) (L164): Wait while scan is paused.
- method ScanManager.start_scan(self, total_items: int=0) (L169): Start a new scan operation.
- method ScanManager.stop_scan(self) (L180): Stop the current scan operation.
- method ScanManager.update_progress(self, current_path: str, increment: int=1) (L186): Update scan progress.
- method ScanManager.get_scan_progress(self) (L194): Get current scan progress information.
- method ScanManager.list_checkpoints(self) (L213): List all available checkpoints.
- method ScanManager.delete_checkpoint(self, checkpoint_id: str) (L231): Delete a specific checkpoint.
- method ScanManager.cleanup_old_checkpoints(self, max_age_days: int=7) (L253): Clean up checkpoints older than specified days.

## src/cortex_unified/performance/settings_integration.py — Settings integration for performance optimization and throttling logic.
- class PerformanceSettingsWidget(QWidget) (L20): Widget for performance capabilities integration.
- method PerformanceSettingsWidget.__init__(self, parent=None) (L25): __init__.
- method PerformanceSettingsWidget.setup_ui(self) (L36): Build the UI structure mirroring old properties natively.
- method PerformanceSettingsWidget.load_settings(self) (L85): Restore properties from persistence.
- method PerformanceSettingsWidget.save_settings(self) (L103): Persist properties and sync natively into systems.
- class PerformanceManager (L127): Singleton context managing throttling endpoints globally.
- method PerformanceManager.__init__(self) (L130): __init__.
- method PerformanceManager.load_saved_settings(self) (L142): load_saved_settings.
- method PerformanceManager.apply_properties(self, properties: dict) (L161): Translates basic dictionary states into core optimization classes natively.
- method PerformanceManager.create_settings_widget(self, parent=None) (L185): create_settings_widget.
- func get_performance_manager() (L194): get_performance_manager.

## src/cortex_unified/reports/__init__.py — Reports and restore module for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/reports/reports.py — Report generation and export: text, HTML, JSON, and CSV.
- class ReportsGenerator (L17): Renders result dicts into report files across four formats.
- method ReportsGenerator.__init__(self, config: Config=None, reports_dir: str=None) (L20): Configure output location and error tracking.
- method ReportsGenerator._get_default_reports_dir(self) (L33): Return ``~/.deepcleaner/reports`` (per-user, no admin needed).
- method ReportsGenerator.generate_text_report(self, data: Dict, report_name: str=None) (L39): Write ``data`` as indented plain text under ``report_name``.
- method ReportsGenerator._format_text_report(self, data: Dict) (L65): Assemble banner, timestamp, and sections into plain text.
- method ReportsGenerator._add_text_section(self, lines: List[str], data: Dict, indent: int) (L83): Recursively append dict/list values as indented lines.
- method ReportsGenerator.generate_html_report(self, data: Dict, report_name: str=None) (L101): Write ``data`` as a styled standalone HTML page.
- method ReportsGenerator._format_html_report(self, data: Dict) (L127): Embed timestamp and rendered sections into the HTML shell.
- method ReportsGenerator._format_html_section(self, data: Dict, level: int) (L156): Recursively render nested dicts/lists as HTML fragments.
- method ReportsGenerator.generate_json_report(self, data: Dict, report_name: str=None) (L190): Write ``data`` as JSON wrapped with a generation timestamp.
- method ReportsGenerator.generate_csv_report(self, data: Dict, report_name: str=None) (L219): Write tabular ``data`` as CSV.
- method ReportsGenerator.get_stats(self) (L249): Return report count, directory, and accumulated error total.
- method ReportsGenerator.list_reports(self) (L268): Enumerate report files with size/mtime metadata.
- method ReportsGenerator.delete_report(self, report_name: str) (L294): Delete a report file by name.

## src/cortex_unified/reports/restore_manager.py — Backup manifests and quarantine-style restoration of deleted files.
- class RestoreManager (L16): Copies files aside before deletion and restores them from manifests.
- method RestoreManager.__init__(self, config: Config=None, backup_dir: str=None) (L19): Set the backup directory and create it eagerly.
- method RestoreManager._get_default_backup_dir(self) (L33): Return ``~/.deepcleaner/backups`` (per-user, no admin needed).
- method RestoreManager.list_manifests(self) (L39): Rescan the backup dir and return manifests newest-first.
- method RestoreManager.get_manifest_details(self, manifest_file: str) (L62): Load one manifest JSON, or ``None`` if missing/unreadable.
- method RestoreManager.restore_from_manifest(self, manifest_file: str, dry_run: bool=True, overwrite_existing: bool=False) (L73): Restore files recorded in a backup manifest to their originals.
- method RestoreManager.create_backup(self, files_to_backup: List[str], backup_name: str=None) (L176): Copy files aside and record them in a manifest.
- method RestoreManager.delete_backup(self, backup_name: str) (L235): Delete a backup's stored files and manifest.
- method RestoreManager.get_stats(self) (L258): Summarize backup counts, stored-file totals, and errors.
- method RestoreManager.filter_manifests_by_date(self, start_date: str=None, end_date: str=None) (L275): Filter manifests by date range.

## src/cortex_unified/scheduler/__init__.py — Task scheduling module for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/scheduler/auto_clean_rules.py — Condition-triggered cleanup rules evaluated against live system state.
- class AutoCleanRules (L19): Registers rules, evaluates their triggers, dispatches actions.
- method AutoCleanRules.__init__(self, config: Config=None) (L22): Build an empty rule set bound to a config.
- method AutoCleanRules.add_disk_usage_rule(self, threshold_percent: float, action: str='clean_empty', clean_params: Dict=None) (L37): Add a rule to clean when disk usage exceeds threshold.
- method AutoCleanRules.add_startup_rule(self, action: str='clean_empty', clean_params: Dict=None) (L61): Add a rule to clean at system startup.
- method AutoCleanRules.add_shutdown_rule(self, action: str='clean_empty', clean_params: Dict=None) (L82): Add a rule to clean at system shutdown.
- method AutoCleanRules.add_scheduled_rule(self, schedule_type: str, schedule_params: Dict, action: str='clean_empty', clean_params: Dict=None) (L103): Add a scheduled rule.
- method AutoCleanRules._check_disk_usage(self, threshold_percent: float) (L130): Check if disk usage exceeds threshold.
- method AutoCleanRules._execute_clean_action(self, action: str, clean_params: Dict) (L149): Dispatch the rule's action to its matching handler.
- method AutoCleanRules._clean_empty_files(self, params: Dict) (L163): _clean_empty_files.
- method AutoCleanRules._clean_temp_files(self, params: Dict) (L182): Sweep low-risk categories through the engine's CleanerService.
- method AutoCleanRules._clean_cache_files(self, params: Dict) (L207): Find cache files, deleting them through Deleter unless dry-run.
- method AutoCleanRules._custom_clean_action(self, params: Dict) (L238): Run a caller-supplied command with the shell disabled.
- method AutoCleanRules.evaluate_rules(self) (L277): Fire every active rule whose trigger currently holds.
- method AutoCleanRules.start_monitoring(self, interval_seconds: int=60) (L307): Start monitoring disk usage in a background thread.
- method AutoCleanRules.stop_monitoring(self) (L324): stop_monitoring.
- method AutoCleanRules._monitor_loop(self, interval_seconds: int) (L332): Poll evaluate_rules until stopped; errors never kill the loop.
- method AutoCleanRules.get_stats(self) (L342): Summarize rule counts, monitor state, and error total.
- method AutoCleanRules.enable_rule(self, rule_index: int) (L355): enable_rule.
- method AutoCleanRules.disable_rule(self, rule_index: int) (L362): Disable rule.
- method AutoCleanRules.remove_rule(self, rule_index: int) (L368): Remove rule.

## src/cortex_unified/scheduler/scheduler.py — OS-native scheduling for cleanup jobs: schtasks, launchd, cron.
- class TaskScheduler (L18): Creates, lists, and removes cleanup jobs in the OS-native scheduler.
- method TaskScheduler.__init__(self, config: Config=None) (L21): Detect the host OS and prepare task tracking.
- method TaskScheduler.create_scheduled_task(self, name: str, command: str, schedule_type: str, schedule_params: Dict=None) (L32): Register ``command`` under ``name`` with the platform scheduler.
- method TaskScheduler._create_windows_task(self, name: str, command: str, schedule_type: str, schedule_params: Dict=None) (L64): Create a Windows scheduled task using schtasks.
- method TaskScheduler._create_macos_task(self, name: str, command: str, schedule_type: str, schedule_params: Dict=None) (L105): Create a macOS scheduled task using launchd.
- method TaskScheduler._generate_launchd_plist(self, name: str, command: str, schedule_type: str, schedule_params: Dict=None) (L130): Render schedule params as a launchd property-list string.
- method TaskScheduler._create_linux_task(self, name: str, command: str, schedule_type: str, schedule_params: Dict=None) (L209): Create a Linux scheduled task using cron.
- method TaskScheduler._generate_cron_expression(self, schedule_type: str, schedule_params: Dict=None) (L239): Translate schedule type/params into five cron fields.
- method TaskScheduler.list_scheduled_tasks(self) (L260): List tasks from the platform scheduler in normalized dicts.
- method TaskScheduler._list_windows_tasks(self) (L276): List Windows scheduled tasks.
- method TaskScheduler._list_macos_tasks(self) (L301): List macOS scheduled tasks.
- method TaskScheduler._list_linux_tasks(self) (L325): List Linux scheduled tasks.
- method TaskScheduler.delete_scheduled_task(self, name: str) (L347): delete_scheduled_task.
- method TaskScheduler.get_stats(self) (L379): Summarize task count, platform, and error total.

## src/cortex_unified/system_tools/__init__.py — System tools module for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/system_tools/adaptive_sanitizer.py — Adaptive privacy-preserving sanitization (PL0-PL3).
- class PrivacyLevel(str, enum.Enum) (L73): PL0-PL3 per Ahn & Lee §4.
- class SanitizeResult (L89): Outcome of one sanitization attempt.
- method SanitizeResult.to_dict(self) (L103): To dict.
- func _is_hot(path: Path) (L118): Heuristic hotness (WAS-Deletion §3): recent mtime + small I/O size.
- class AdaptiveSanitizer (L140): Graduated sanitizer.
- method AdaptiveSanitizer.__init__(self, guard: PathGuard | None=None, probe: StorageProbe | None=None) (L150): Initialize Adaptive Sanitizer.
- method AdaptiveSanitizer.auto_level(self, path: Path, requested: PrivacyLevel | None=None) (L161): Pick PL if caller did not request one.
- method AdaptiveSanitizer.sanitize(self, path: Path | str, level: PrivacyLevel | None=None, verify: bool=True, force: bool=False, timeout: int=120) (L186): Sanitize *path* at *level* (auto if None).
- method AdaptiveSanitizer._execute(self, p: Path, lvl: PrivacyLevel, kind: StorageKind, verify: bool, force: bool, timeout: int) (L250): Dispatch PL.
- method AdaptiveSanitizer._pl0(self, p: Path, kind: StorageKind, verify: bool, force: bool, timeout: int) (L267): _pl0.
- method AdaptiveSanitizer._pl1(self, p: Path, kind: StorageKind, verify: bool, force: bool, timeout: int) (L301): _pl1.
- method AdaptiveSanitizer._pl2(self, p: Path, kind: StorageKind, verify: bool, timeout: int) (L380): _pl2.
- method AdaptiveSanitizer._pl3(self, p: Path, kind: StorageKind, verify: bool, timeout: int) (L435): _pl3.
- method AdaptiveSanitizer._trim_parent(self, p: Path) (L458): Best-effort TRIM hint for the parent filesystem.

## src/cortex_unified/system_tools/ai_telemetry_cleaner.py — Windows 11 AI, Copilot, Recall & Semantic Telemetry Cleaner.
- class AiArtifactInfo (L35): Detailed metadata for a discovered AI or Copilot local storage artifact.
- method AiArtifactInfo.to_dict(self) (L45): To dict.
- class AiTelemetryReport (L59): Comprehensive analysis report of Windows AI and generative telemetry artifacts.
- method AiTelemetryReport.to_dict(self) (L68): To dict.
- class AiCleanResult (L81): Results of AI cache cleaning and SQLite WAL checkpoint operations.
- method AiCleanResult.to_dict(self) (L89): To dict.
- class AiTelemetryCleaner (L100): Forensic inspector and optimizer for Windows 11 AI and Recall caches.
- method AiTelemetryCleaner.__init__(self) (L103): Initialize Ai Telemetry Cleaner.
- method AiTelemetryCleaner._get_search_roots(self) (L107): Resolve candidate search locations dynamically from active user and system environments.
- method AiTelemetryCleaner.scan(self) (L157): Examine local disk for AI artifacts, Recall databases, and inflated WAL files.
- method AiTelemetryCleaner._record_artifact(self, report: AiTelemetryReport, name: str, category: str, path: Path, description: str, is_wal: bool=False) (L183): _record_artifact.
- method AiTelemetryCleaner.checkpoint_wal_journal(self, wal_path: Path) (L216): Safely truncate a SQLite WAL file by connecting to its parent DB and executing PRAGMA wal_checkpoint(TRUNCATE).
- method AiTelemetryCleaner.clean(self, checkpoint_wal: bool=True, dry_run: bool=False) (L246): Purge temporary AI caches and truncate uncheckpointed SQLite WAL journals.

## src/cortex_unified/system_tools/app_uninstaller.py — Windows Application Uninstaller for Cortex Cleaner.
- class AppUninstaller (L12): Lists and uninstalls Windows applications via the Registry.
- method AppUninstaller.__init__(self) (L22): Initialize App Uninstaller.
- method AppUninstaller.get_installed_apps(self) (L30): Return a deduplicated, sorted list of installed applications.
- method AppUninstaller.uninstall_app(self, app_info: Dict[str, Any], silent: bool=False) (L79): Execute the uninstall string for an application.
- method AppUninstaller.get_app_size_mb(self, app_info: Dict[str, Any]) (L119): Return estimated size in MB from the registry's EstimatedSize (KB) value.
- method AppUninstaller._read_app_entry(winreg, hive, parent_path: str, subkey_name: str) (L131): Read a single Uninstall subkey and return an app dict, or None.
- func AppUninstaller._read_app_entry._val(name: str, default='') (L139): _val.

## src/cortex_unified/system_tools/app_updater.py — Software Updater - a safe GUI-friendly wrapper over Windows Package Manager.
- class UpgradableApp (L32): Upgradable App data container.
- method UpgradableApp.to_dict(self) (L40): To dict.
- class AppUpdater (L51): List and apply application updates via winget.
- method AppUpdater.__init__(self) (L54): Initialize App Updater.
- method AppUpdater.is_available() (L59): True if winget is installed and usable.
- method AppUpdater.list_upgradable(self) (L63): Return apps with available updates. Empty list if winget is absent.
- method AppUpdater.upgrade(self, package_id: str) (L72): Upgrade a single package by its winget Id.
- method AppUpdater.upgrade_all(self) (L91): Upgrade every upgradable package (caller must confirm first).
- method AppUpdater.parse_upgrade_output(text: str) (L105): Parse winget's fixed-width upgrade table into structured rows.
- method AppUpdater._run(self, cmd: list[str], timeout: int) (L153): _run.

## src/cortex_unified/system_tools/bitlocker_auditor.py — Cortex Cleaner — BitLocker & Drive Encryption Auditor.
- class EncryptedVolumeInfo (L23): Encrypted Volume Info data container.
- method EncryptedVolumeInfo.is_protected(self) (L37): Is protected.
- method EncryptedVolumeInfo.is_fully_encrypted(self) (L42): Is fully encrypted.
- class BitLockerAuditReport (L48): Bit Locker Audit Report data container.
- class BitLockerAuditor (L58): Enterprise BitLocker Drive Encryption Auditor.
- method BitLockerAuditor.__init__(self) (L61): Initialize Bit Locker Auditor.
- method BitLockerAuditor.audit(self) (L65): Run complete BitLocker audit across all physical and logical volumes.
- method BitLockerAuditor._query_manage_bde(self) (L99): Query BitLocker status via manage-bde command line.
- method BitLockerAuditor._query_wmi_powershell(self) (L185): Fallback querying Get-BitLockerVolume via PowerShell.

## src/cortex_unified/system_tools/bitrot_scrubber.py — Cortex Cleaner — Silent BitRot & File Integrity Scrubber.
- class ScrubberRecord (L25): Scrubber Record data container.
- class BitRotIssue (L35): Bit Rot Issue data container.
- class BitRotScrubReport (L45): Bit Rot Scrub Report data container.
- class BitRotScrubber (L57): Enterprise BitRot Scrubber & Integrity Baseline Manager.
- method BitRotScrubber.__init__(self, db_path: Optional[str]=None) (L60): Initialize Bit Rot Scrubber.
- method BitRotScrubber._init_db(self) (L71): Initialize integrity database schema.
- method BitRotScrubber._compute_sha256(path: Path) (L88): Stream SHA-256 calculation for arbitrary file sizes.
- method BitRotScrubber.scrub(self, target_dir: str, max_files: int=5000) (L100): Perform a cryptographic integrity scrub on target directory.
- method BitRotScrubber.reset_baseline(self, target_dir: Optional[str]=None) (L188): Reset records in integrity database.

## src/cortex_unified/system_tools/boot_performance.py — Boot performance analysis - using Windows' OWN boot measurements.
- class BootRecord (L45): Boot Record data container.
- method BootRecord.boot_seconds(self) (L52): Boot seconds.
- method BootRecord.to_dict(self) (L56): To dict.
- class BootIssue (L63): Boot Issue data container.
- method BootIssue.impact_seconds(self) (L71): Impact seconds.
- method BootIssue.to_dict(self) (L75): To dict.
- class BootPerformanceMonitor (L81): Reads Windows boot diagnostics (read-only).
- method BootPerformanceMonitor.is_supported() (L85): Is supported.
- method BootPerformanceMonitor.analyze(self, max_boots: int=10, max_issues: int=40) (L89): Analyze.
- method BootPerformanceMonitor._script(max_boots: int, max_issues: int) (L105): _script.
- method BootPerformanceMonitor._parse(out: str | None) (L126): _parse.
- func BootPerformanceMonitor._parse._int(v) (L135): _int.
- func BootPerformanceMonitor._parse._as_list(v) (L144): _as_list.
- method BootPerformanceMonitor._run(self, script: str) (L180): _run.

## src/cortex_unified/system_tools/browser_cleaner.py — Deep Browser Cleaner — IndexedDB, Service Workers, Code Cache, GPU cache, cookies.
- class Cleanable (L75): Cleanable data container.
- func _discover_chromium_profiles(base_names: List[str]) (L89): _discover_chromium_profiles.
- func _discover_firefox_profiles() (L125): _discover_firefox_profiles.
- class DeepBrowserCleaner (L156): Deep Browser Cleaner.
- method DeepBrowserCleaner.__init__(self, keep_cookies: List[str] | None=None, progress: Callable[[str], None] | None=None, cancel: threading.Event | None=None) (L158): Initialize Deep Browser Cleaner.
- method DeepBrowserCleaner.scan(self) (L167): Scan.
- method DeepBrowserCleaner._scan_chromium_profile(self, profile: Path, browser: str) (L183): _scan_chromium_profile.
- method DeepBrowserCleaner._scan_firefox_profile(self, profile: Path) (L225): _scan_firefox_profile.
- method DeepBrowserCleaner.clean(self, paths: List[Path], shred: bool=False) (L257): Clean.
- method DeepBrowserCleaner.clean_cookies_keep_list(self, cookies_db: Path) (L285): Delete cookies not matching keep-list, return removed count.
- method DeepBrowserCleaner.vacuum_databases(self, dbs: List[Path]) (L309): VACUUM SQLite DBs, return saved bytes per DB.

## src/cortex_unified/system_tools/browser_deep_cleaner.py — Cortex Cleaner — Forensic Multi-Browser Deep Privacy & Cache Sanitizer.
- class BrowserTarget (L20): Browser Target data container.
- class BrowserCleanResult (L30): Browser Clean Result data container.
- method BrowserCleanResult.__post_init__(self) (L37): __post_init__.
- class BrowserDeepCleaner (L45): Production Multi-Browser cache and forensic artifact sanitizer.
- method BrowserDeepCleaner._dir_stats(cls, path: Path) (L49): Compute size in bytes and file count for directory.
- method BrowserDeepCleaner.scan_browser_caches(cls) (L69): Scan all detected web browsers for non-essential cache and transient stores.
- method BrowserDeepCleaner.clean_targets(cls, targets: List[BrowserTarget]) (L145): Purge selected browser cache directories.

## src/cortex_unified/system_tools/browser_extensions.py — Browser-extension audit - read-only inventory of installed extensions.
- class BrowserExtension (L27): Browser Extension data container.
- method BrowserExtension.broad_permissions(self) (L36): True if the extension requests notably powerful permissions.
- method BrowserExtension.to_dict(self) (L43): To dict.
- class BrowserExtensionAuditor (L55): Read-only inventory of installed browser extensions.
- method BrowserExtensionAuditor.__init__(self, home: Path | None=None) (L66): Initialize Browser Extension Auditor.
- method BrowserExtensionAuditor._localappdata(self) (L70): _localappdata.
- method BrowserExtensionAuditor.audit(self) (L79): Audit.
- method BrowserExtensionAuditor._scan_chromium(self) (L88): _scan_chromium.
- method BrowserExtensionAuditor._scan_chromium_ext_root(self, browser: str, ext_root: Path) (L106): _scan_chromium_ext_root.
- method BrowserExtensionAuditor._from_chromium_manifest(browser: str, ext_id: str, manifest: dict) (L130): _from_chromium_manifest.
- method BrowserExtensionAuditor._firefox_root(self) (L147): _firefox_root.
- method BrowserExtensionAuditor._scan_firefox(self) (L156): _scan_firefox.
- method BrowserExtensionAuditor._safe_iterdir(path: Path) (L189): _safe_iterdir.
- method BrowserExtensionAuditor._read_manifest(path: Path) (L199): _read_manifest.

## src/cortex_unified/system_tools/checksum_matrix.py — Forensic Checksum Matrix & Integrity Manifest Generator/Verifier.
- class FileChecksumResult (L37): Calculated cryptographic and cyclic redundancy hashes for a file.
- method FileChecksumResult.to_dict(self) (L48): To dict.
- class ManifestVerifyItem (L63): Individual verification status of a file against its manifest entry.
- method ManifestVerifyItem.to_dict(self) (L71): To dict.
- class ManifestVerificationReport (L83): Consolidated outcome of verifying a manifest file against on-disk files.
- method ManifestVerificationReport.is_all_valid(self) (L96): Is all valid.
- method ManifestVerificationReport.to_dict(self) (L100): To dict.
- class ChecksumMatrix (L116): Production file hashing, manifest generation, and integrity verification engine.
- method ChecksumMatrix.__init__(self) (L119): Initialize Checksum Matrix.
- method ChecksumMatrix.hash_file(self, file_path: Path, algorithms: Optional[List[str]]=None) (L123): Stream a file through selected hash algorithms in parallel.
- method ChecksumMatrix.generate_manifest(self, directory: Path, output_file: Path, algorithm: str='sha256', recursive: bool=True) (L173): Scan directory and write standard checksum manifest file (.sha256, .md5, or .sfv).
- method ChecksumMatrix.verify_manifest(self, manifest_file: Path) (L216): Parse manifest (.sha256, .md5, .sfv) and verify all referenced files.

## src/cortex_unified/system_tools/compact_os.py — NTFS CompactOS / per-folder NTFS compression support.
- class FolderEstimate (L97): Folder Estimate data container.
- method FolderEstimate.to_dict(self) (L106): To dict.
- class CompressionResult (L119): Compression Result data container.
- class CompactOSManager (L128): Read-first NTFS compaction support (estimate + explicit action).
- method CompactOSManager.__init__(self) (L131): Initialize Compact O S Manager.
- method CompactOSManager.is_supported() (L139): Is supported.
- method CompactOSManager.is_admin(self) (L143): Whether the current process can run elevated ``compact`` commands.
- method CompactOSManager.compactos_query(self) (L157): Return CompactOS status for the OS volume.
- method CompactOSManager.drive_compression_state(self, drive: str='C:') (L177): Per-drive compression state via ``fsutil volume compression``.
- method CompactOSManager.find_compressible_folders(self, root: str | os.PathLike, min_size_mb: float=100.0, cancel_event: 'threading.Event | None'=None, progress_callback=None) (L192): Scan *root* (1 level of subdirectories) for compressible folders.
- method CompactOSManager._estimate_folder(self, folder: Path, cancel_event: 'threading.Event | None'=None, progress_callback=None) (L234): Walk *folder* and estimate compressible bytes + savings.
- method CompactOSManager._check_compression_attribute(self, folder: Path) (L292): Best-effort: is the folder already flagged compressed on NTFS?
- method CompactOSManager.compact_folder(self, path: str | os.PathLike, recursive: bool=True, cancel_event: 'threading.Event | None'=None) (L308): Compress an NTFS folder (and optionally its subtree).
- method CompactOSManager._parse_failure(out: Optional[str]) (L349): _parse_failure.
- method CompactOSManager._run(self, args: List[str], timeout: int, cancel_event: 'threading.Event | None'=None) (L364): _run.

## src/cortex_unified/system_tools/component_store.py — Component store (WinSxS) analysis and Windows upgrade leftovers.
- class LeftoverRisk(str, enum.Enum) (L39): What you give up by removing a leftover.
- class StoreAnalysis (L48): Result of ``DISM /AnalyzeComponentStore`` - all figures from Windows.
- method StoreAnalysis.explorer_gap_note(self) (L65): Why Explorer's WinSxS figure exceeds the actual on-disk size.
- method StoreAnalysis.reclaimable_estimate(self) (L79): Upper bound on what a cleanup could return.
- method StoreAnalysis.to_dict(self) (L88): To dict.
- class Leftover (L107): One upgrade/servicing leftover on disk.
- method Leftover.removable_here(self) (L120): True when Cortex may delete this itself.
- method Leftover.rollback_expired(self) (L125): True once Windows' own rollback window has passed.
- method Leftover.to_dict(self) (L129): To dict.
- class CleanupOutcome (L145): Result of a component-store cleanup, with measured before/after.
- method CleanupOutcome.freed_bytes(self) (L157): Freed bytes.
- method CleanupOutcome.to_dict(self) (L161): To dict.
- class ComponentStore (L174): Analyze and clean the WinSxS component store; inventory leftovers.
- method ComponentStore.__init__(self) (L177): Initialize Component Store.
- method ComponentStore.is_supported() (L182): Is supported.
- method ComponentStore.is_elevated() (L187): True when running as Administrator (required for every cleanup).
- method ComponentStore.analyze(self, timeout: int=900, cancel_event: 'threading.Event | None'=None) (L199): Run ``DISM /AnalyzeComponentStore`` and parse Windows' own figures.
- method ComponentStore._parse_analysis(out: str) (L216): Parse DISM's human-readable report into numbers.
- func ComponentStore._parse_analysis._bytes_after(label: str) (L227): _bytes_after.
- method ComponentStore.find_leftovers(self, progress: Callable[[str], None] | None=None, cancel_event=None, analysis: StoreAnalysis | None=None) (L281): Inventory upgrade/servicing leftovers with size, age and cost.
- method ComponentStore._try_remove_spurious_package(self, timeout: int=600) (L425): Attempt to remove the deeply-superseded 24H2 rollup fix package.
- method ComponentStore.cleanup(self, reset_base: bool=False, timeout: int=3600, progress: Callable[[str], None] | None=None, cancel_event: 'threading.Event | None'=None, auto_fix_spurious: bool=True) (L443): Run ``DISM /StartComponentCleanup``, optionally with ``/ResetBase``.
- method ComponentStore.run_servicing_task(self, timeout: int=3600) (L574): Trigger Windows' own scheduled StartComponentCleanup task.
- method ComponentStore._run_dism(self, args: list[str], timeout: int, cancel_event: 'threading.Event | None'=None) (L601): _run_dism.
- method ComponentStore._decode(raw: bytes | str | None) (L624): Decode DISM output, which is UTF-16LE with NULs on many consoles.
- method ComponentStore._dir_size(path: Path) (L638): Sum a directory tree, skipping what we cannot read (never raises).
- method ComponentStore._age_days(path: Path) (L659): _age_days.

## src/cortex_unified/system_tools/component_store_cleaner.py — Component Store / WinSxS Cleaner — DISM-based analysis and cleanup.
- class ComponentStoreInfo (L93): Parsed output of `DISM /AnalyzeComponentStore`.
- method ComponentStoreInfo.reclaimable_gb(self) (L106): Reclaimable gb.
- class CleanupResult (L115): Cleanup Result data container.
- class PackageInfo (L127): Single package from `dism /get-packages`.
- class ComponentStoreCleaner (L139): DISM-based Component Store analyzer and cleaner.
- method ComponentStoreCleaner.__init__(self, dism_path: str='Dism.exe', create_restore_point: bool=True, progress_callback: Optional[Callable[[str], None]]=None, cancel_event: Optional[threading.Event]=None) (L142): Initialize Component Store Cleaner.
- method ComponentStoreCleaner._run_dism(self, args: List[str], timeout: int=1800) (L164): Run DISM command, return (returncode, stdout, stderr).
- method ComponentStoreCleaner._parse_analyze(self, output: str) (L181): Parse `DISM /AnalyzeComponentStore` output.
- method ComponentStoreCleaner._parse_packages(self, output: str) (L227): Parse `dism /get-packages` table output.
- method ComponentStoreCleaner.analyze(self) (L250): Run `DISM /Online /Cleanup-Image /AnalyzeComponentStore`.
- method ComponentStoreCleaner.cleanup(self, reset_base: bool=False, sp_superseded: bool=False) (L260): Run component store cleanup.
- method ComponentStoreCleaner.fix_staged_packages(self) (L305): Fix Windows 11 24H2 stuck 'Staged' packages (26100.1742).
- method ComponentStoreCleaner.analyze_offline(self, wim_path: str, index: int=1) (L349): Analyze component store in offline WIM/VHD/VHDX.
- method ComponentStoreCleaner.cleanup_offline(self, wim_path: str, index: int=1, reset_base: bool=False) (L359): Cleanup component store in offline image.
- method ComponentStoreCleaner.schedule_cleanup(self, task_name: str='CortexComponentStoreCleanup', frequency_days: int=30, reset_base: bool=False) (L388): Register a scheduled task for automatic cleanup (admin required).

## src/cortex_unified/system_tools/context_menu_manager.py — Cortex Cleaner — Windows Context Menu & Shell Extension Manager.
- class ContextMenuItem (L25): Context Menu Item data container.
- class ContextMenuReport (L38): Context Menu Report data container.
- class ContextMenuManager (L45): Production Windows shell context menu inspector and cleaner.
- method ContextMenuManager._extract_command(cls, key_path: str) (L59): Read the command value from a shell key.
- method ContextMenuManager._check_program_exists(cls, command: str) (L72): Check if the executable referenced in the command actually exists.
- method ContextMenuManager.enumerate_context_menu(cls) (L91): Enumerate all right-click context menu entries from the registry.
- method ContextMenuManager.analyze(cls) (L156): Generate analysis report of context menu entries.
- method ContextMenuManager.disable_entry(cls, registry_path: str) (L167): Disable a context menu entry by setting LegacyDisable.
- method ContextMenuManager.enable_entry(cls, registry_path: str) (L182): Re-enable a disabled context menu entry.

## src/cortex_unified/system_tools/crash_dump_cleaner.py — Cortex Cleaner — Windows Crash Dump & Error Reporting (WER) Cleaner.
- class CrashDumpItem (L18): Crash Dump Item data container.
- class CrashDumpCleanReport (L28): Crash Dump Clean Report data container.
- method CrashDumpCleanReport.__post_init__(self) (L36): __post_init__.
- class CrashDumpCleaner (L44): Production Windows crash dump and WER queue sanitizer.
- method CrashDumpCleaner.scan_dumps(cls) (L48): Scan all known Windows crash dump and error reporting locations.
- method CrashDumpCleaner.clean_dumps(cls, items_to_delete: Optional[List[CrashDumpItem]]=None) (L120): Purge selected or all discovered crash dumps and WER files.

## src/cortex_unified/system_tools/defender.py — Windows Security (Defender) status + quick scan trigger.
- class DefenderStatus (L27): Defender Status data container.
- method DefenderStatus.healthy(self) (L40): Healthy.
- method DefenderStatus.to_dict(self) (L45): To dict.
- class WindowsDefender (L61): Read Defender status, list recent detections, start a quick scan.
- method WindowsDefender.is_supported() (L65): Is supported.
- method WindowsDefender.status(self) (L69): Status.
- method WindowsDefender._parse_status(out: str | None) (L83): _parse_status.
- func WindowsDefender._parse_status._int(v) (L94): _int.
- method WindowsDefender.recent_threats(self, limit: int=20) (L117): Recent threats.
- method WindowsDefender._parse_threats(out: str | None) (L132): _parse_threats.
- method WindowsDefender.start_quick_scan(self) (L154): Kick off a Defender quick scan (harmless; scans, doesn't delete data).
- method WindowsDefender._clean_date(raw: Any) (L165): _clean_date.
- method WindowsDefender._run(self, script: str, timeout: int, want_returncode: bool=False) (L181): _run.

## src/cortex_unified/system_tools/delivery_optimization_cleaner.py — Cortex Cleaner — Windows Delivery Optimization (WUDO) Cache Cleaner.
- class DeliveryOptimizationStatus (L18): Delivery Optimization Status data container.
- class DeliveryOptimizationCleanReport (L27): Delivery Optimization Clean Report data container.
- method DeliveryOptimizationCleanReport.__post_init__(self) (L33): __post_init__.
- class DeliveryOptimizationCleaner (L41): Production Delivery Optimization cache sanitizer.
- method DeliveryOptimizationCleaner.get_status(cls) (L45): Query total cache size and file count in Delivery Optimization stores.
- method DeliveryOptimizationCleaner.clean_cache(cls) (L81): Purge all Delivery Optimization cache files.

## src/cortex_unified/system_tools/dev_cleaner.py — Cortex Cleaner — Developer Ecosystem & Build Artifacts Purger.
- class DevCacheItem (L24): Dev Cache Item data container.
- class DevCleanResult (L36): Dev Clean Result data container.
- method DevCleanResult.__post_init__(self) (L42): __post_init__.
- class DevCleaner (L50): Production Developer Ecosystem build artifact and cache purge engine.
- method DevCleaner._dir_metrics(cls, dir_path: Path) (L54): Compute directory size and file count.
- method DevCleaner.scan_dev_caches(cls) (L74): Scan system for all developer ecosystem build caches and artifacts.
- method DevCleaner.clean_items(cls, items: List[DevCacheItem]) (L172): Purge selected developer cache locations.

## src/cortex_unified/system_tools/dev_drive_optimizer.py — Cortex Cleaner — ReFS Dev Drive & Block-Cloning Optimizer.
- class DevDriveInfo (L28): Dev Drive Info data container.
- class DevDriveAuditReport (L42): Dev Drive Audit Report data container.
- class DevDriveOptimizer (L50): Enterprise ReFS Dev Drive & Block Cloning Optimizer.
- method DevDriveOptimizer.__init__(self) (L53): Initialize Dev Drive Optimizer.
- method DevDriveOptimizer.audit(self) (L57): Audit all mounted volumes for ReFS, Dev Drive status, and Block Cloning.
- method DevDriveOptimizer._get_logical_drives(self) (L89): Get all valid local drive letters.
- method DevDriveOptimizer._inspect_drive(self, drive_letter: str) (L98): Inspect a single drive for ReFS, Dev Drive, and Block Cloning.
- method DevDriveOptimizer.test_block_cloning(self, source_path: str, target_path: str) (L173): Test instant CoW block cloning between two paths via FSCTL_DUPLICATE_EXTENTS_TO_FILE.

## src/cortex_unified/system_tools/dev_package_cache_cleaner.py — Developer Package Caches (Winget, Cargo, Vcpkg, NuGet, Pip) Deep Cleaner.
- class DevPackageStoreInfo (L36): Status and storage consumption of a specific developer package cache.
- method DevPackageStoreInfo.to_dict(self) (L46): To dict.
- class DevPackageReport (L60): Consolidated storage consumption across all developer package ecosystems.
- method DevPackageReport.to_dict(self) (L67): To dict.
- class DevPackageCleanResult (L78): Outcome of a developer package cache purge.
- method DevPackageCleanResult.to_dict(self) (L86): To dict.
- class DevPackageCacheCleaner (L97): Production developer environment cache detection and cleanup engine.
- method DevPackageCacheCleaner.__init__(self) (L100): Initialize Dev Package Cache Cleaner.
- method DevPackageCacheCleaner.get_candidate_stores(self) (L104): Resolve candidate developer cache roots dynamically from active user profiles.
- method DevPackageCacheCleaner.scan(self) (L168): Analyze developer package stores and measure disk space consumption.
- method DevPackageCacheCleaner.clean(self, selected_ecosystems: Optional[List[str]]=None, dry_run: bool=False) (L204): Purge developer package cache archives.

## src/cortex_unified/system_tools/device_fingerprint.py — Pure, conservative device fingerprinting from observed LAN evidence.
- class FingerprintEvidence (L13): Fingerprint Evidence data container.
- method FingerprintEvidence.to_dict(self) (L21): To dict.
- class DeviceFingerprint (L33): Device Fingerprint data container.
- method DeviceFingerprint.to_dict(self) (L43): To dict.
- func _get(value: Any, name: str, default: Any=None) (L74): _get.
- func _observations(device: Any) (L81): _observations.
- func _add(evidence: list[FingerprintEvidence], source: str, value: Any, strength: str, weight: float, detail: str) (L101): _add.
- func _collect(device: Any, observations: list[ServiceObservation]) (L119): _collect.
- func _rank(text: str, rules: tuple[tuple[tuple[str, ...], str], ...]) (L156): _rank.
- func _product_version(evidence: Iterable[FingerprintEvidence]) (L169): _product_version.
- func fingerprint_device(device: Any) (L189): Combine duck-typed discovery data and observations without certainty from ports.

## src/cortex_unified/system_tools/diagnostic_data_manager.py — Cortex Cleaner — Windows Telemetry & Diagnostic Data Manager.
- class TelemetrySetting (L25): Telemetry Setting data container.
- class TelemetryAuditReport (L39): Telemetry Audit Report data container.
- class DiagnosticDataManager (L48): Production Windows Telemetry & Diagnostic Data level management engine.
- method DiagnosticDataManager._read_dword(cls, hive, subkey: str, name: str) (L132): _read_dword.
- method DiagnosticDataManager._write_dword(cls, hive, subkey: str, name: str, value: int) (L146): _write_dword.
- method DiagnosticDataManager.audit_telemetry(cls) (L162): Inspect all diagnostic telemetry settings and calculate score.
- method DiagnosticDataManager.apply_maximum_privacy(cls) (L199): Harden all telemetry settings to maximum privacy values.

## src/cortex_unified/system_tools/directstorage_optimizer.py — Windows 11 DirectStorage & BypassIO Hardware Acceleration Auditor.
- class BypassIoVolumeReport (L23): BypassIO and DirectStorage status for a single storage volume.
- method BypassIoVolumeReport.to_dict(self) (L34): To dict.
- class DirectStorageAuditReport (L47): Comprehensive system-wide DirectStorage readiness report.
- method DirectStorageAuditReport.to_dict(self) (L56): To dict.
- class DirectStorageOptimizer (L67): Audits and provides diagnostics for Windows DirectStorage and BypassIO.
- method DirectStorageOptimizer.__init__(self) (L70): Initialize Direct Storage Optimizer.
- method DirectStorageOptimizer.parse_bypassio_output(cls, volume: str, text: str) (L75): Parse the standard stdout of 'fsutil bypassio state <volume> /v'.
- method DirectStorageOptimizer._get_active_drives(self) (L114): Detect all mounted active drive letters on Windows.
- method DirectStorageOptimizer.audit(self) (L130): Audit all mounted volumes for DirectStorage BypassIO readiness.

## src/cortex_unified/system_tools/disk_benchmark.py — Cortex Cleaner — Storage Performance & IOPS Disk Benchmark.
- class DiskBenchmarkMetric (L23): Disk Benchmark Metric data container.
- class DiskBenchmarkReport (L32): Disk Benchmark Report data container.
- class DiskBenchmarkEngine (L45): Production non-destructive disk throughput and IOPS storage benchmark.
- method DiskBenchmarkEngine.run_benchmark(cls, target_directory: str | Path, file_size_mb: int=64, progress_cb: Optional[Callable[[str, float], None]]=None, cancel_check: Optional[Callable[[], bool]]=None) (L49): Execute full benchmark suite on the specified storage location.

## src/cortex_unified/system_tools/disk_health.py — Disk health (S.M.A.R.T.) reporting - read-only, honest.
- class DiskHealth (L27): Disk Health data container.
- method DiskHealth.is_healthy(self) (L40): Is healthy.
- method DiskHealth.to_dict(self) (L44): To dict.
- class DiskHealthMonitor (L59): Reads S.M.A.R.T. / physical-disk health information.
- method DiskHealthMonitor.is_supported() (L63): Is supported.
- method DiskHealthMonitor.get_health(self) (L67): Get health.
- method DiskHealthMonitor._parse(out: str | None) (L92): _parse.
- func DiskHealthMonitor._parse._int(v) (L103): _int.
- method DiskHealthMonitor._run(self, script: str) (L129): _run.

## src/cortex_unified/system_tools/dns_benchmark.py — Cortex Cleaner — Multi-Threaded DNS Latency Benchmark & Optimizer.
- class DnsServerSpec (L21): Dns Server Spec data container.
- class DnsBenchmarkResult (L44): Dns Benchmark Result data container.
- class DnsBenchmarkEngine (L57): Production DNS query benchmarking and network configuration engine.
- method DnsBenchmarkEngine._build_dns_query(domain: str) (L63): Construct raw DNS wire format query for an A record.
- method DnsBenchmarkEngine._query_dns(cls, server_ip: str, domain: str, timeout_seconds: float=1.5) (L83): Send a direct UDP DNS query and measure round-trip latency in milliseconds.
- method DnsBenchmarkEngine.benchmark_server(cls, server: DnsServerSpec, domains: Optional[List[str]]=None, timeout_seconds: float=1.5) (L101): Benchmark a DNS provider across multiple test domains.
- method DnsBenchmarkEngine.run_full_benchmark(cls, servers: Optional[List[DnsServerSpec]]=None, progress_cb: Optional[Callable[[int, int, str], None]]=None, cancel_check: Optional[Callable[[], bool]]=None) (L145): Concurrently benchmark all known DNS providers.
- method DnsBenchmarkEngine.apply_dns_servers(cls, interface_name: str, primary_ip: str, secondary_ip: Optional[str]=None) (L180): Configure DNS servers on the specified network adapter via netsh.

## src/cortex_unified/system_tools/drive_optimizer.py — Media-aware drive optimization - the honest way.
- class OptimizeOp(str, enum.Enum) (L33): Optimize Op enumeration.
- class DriveInfo (L41): Drive Info data container.
- method DriveInfo.to_dict(self) (L48): To dict.
- class OptimizeResult (L59): Optimize Result data container.
- class DriveOptimizer (L67): List fixed drives, recommend the correct op per medium, and run it safely.
- method DriveOptimizer.__init__(self) (L70): Initialize Drive Optimizer.
- method DriveOptimizer.is_supported() (L75): Is supported.
- method DriveOptimizer.list_drives(self) (L79): Return fixed drives with the medium-correct recommended operation.
- method DriveOptimizer._recommend(kind: StorageKind) (L91): _recommend.
- method DriveOptimizer.optimize(self, letter: str, op: OptimizeOp | None=None, cancel_event: 'threading.Event | None'=None) (L103): Run the correct optimization for *letter*. If *op* is None, auto-pick.
- method DriveOptimizer._fixed_drive_letters(self) (L146): Return fixed (non-removable, non-network) drive letters.
- method DriveOptimizer._run_ps(self, script: str, timeout: int, cancel_event: 'threading.Event | None'=None) (L161): _run_ps.

## src/cortex_unified/system_tools/driver_inventory.py — Driver inventory - READ-ONLY listing of installed device drivers.
- class DriverInfo (L28): Driver Info data container.
- method DriverInfo.to_dict(self) (L36): To dict.
- class DriverInventory (L47): Read-only inventory of signed device drivers (Windows).
- method DriverInventory.is_supported() (L51): Is supported.
- method DriverInventory.list_drivers(self) (L55): List drivers.
- method DriverInventory._parse(out: str | None) (L68): _parse.
- method DriverInventory._clean_date(raw: Any) (L105): _clean_date.
- method DriverInventory._run(self, script: str) (L124): _run.

## src/cortex_unified/system_tools/driver_manager.py — Driver Cleaner & Updater — offline-capable, WHQL-verified, restore points.
- class DriverInfo (L78): Single device driver information.
- method DriverInfo.to_dict(self) (L98): To dict.
- class DriverPack (L105): Driver pack metadata (SDIO-compatible).
- class ScanResult (L119): Scan Result data container.
- method ScanResult.to_json(self) (L127): To json.
- class DriverManager (L142): Detect, update, and clean device drivers.
- method DriverManager.__init__(self, create_restore_point: bool=True, progress_callback: Optional[Callable[[str], None]]=None, cancel_event: Optional[threading.Event]=None, offline_mode: bool=False, driverpack_index: Optional[str]=None) (L145): Initialize Driver Manager.
- method DriverManager._run(self, cmd: List[str], timeout: int=120) (L166): _run.
- method DriverManager._run_ps(self, script: str, timeout: int=120) (L183): _run_ps.
- method DriverManager._load_index(self, path: str) (L189): _load_index.
- method DriverManager._save_index(self, path: str) (L204): _save_index.
- method DriverManager._pack_to_dict(self, pack: DriverPack) (L215): _pack_to_dict.
- method DriverManager._enumerate_pnp(self) (L224): Use WMI/PowerShell to get all PnP devices with driver info.
- method DriverManager._check_updates_online(self, drivers: List[DriverInfo]) (L311): Search Windows Update for driver updates for this machine's hardware.
- method DriverManager._wua_driver_updates(self) (L411): Driver updates WUA currently offers, or None when unavailable.
- method DriverManager._check_updates_offline(self, drivers: List[DriverInfo]) (L435): Match against local driverpack index.
- method DriverManager._version_newer(self, v1: str, v2: str) (L459): Compare version strings (handles multi-part versions).
- func DriverManager._version_newer.parse(v: str) (L461): Parse.
- method DriverManager.scan(self) (L472): Scan all devices and check for outdated/missing drivers.
- method DriverManager.update_selected(self, hardware_ids: List[str], force: bool=False) (L496): Install driver updates for specified hardware IDs.
- method DriverManager._download_and_install(self, drv: DriverInfo, force: bool) (L529): Download driver package and install via pnputil.
- method DriverManager._install_from_store(self, inf_name: str, force: bool) (L549): Install driver already in driver store.
- method DriverManager.cleanup_driver_store(self, dry_run: bool=True) (L557): Remove orphaned/duplicate drivers from Driver Store.
- method DriverManager.export_driverpack_index(self, path: str) (L610): Export current index to JSON for offline use.
- method DriverManager.get_stats(self) (L615): Get stats.

## src/cortex_unified/system_tools/driver_store_cleaner.py — Cortex Cleaner — Driver Store Explorer & Superseded Driver Purger.
- class DriverPackage (L22): Driver Package data container.
- class DriverCleanResult (L36): Driver Clean Result data container.
- method DriverCleanResult.__post_init__(self) (L42): __post_init__.
- class DriverStoreCleaner (L50): Production Driver Store Explorer (RAPR) and superseded INF driver purger.
- method DriverStoreCleaner.enumerate_drivers(cls) (L54): Query and parse all third-party driver packages via pnputil /enum-drivers.
- method DriverStoreCleaner.delete_driver(cls, published_name: str, force: bool=True) (L116): Delete a single third-party driver package from the Windows Driver Store.
- method DriverStoreCleaner.export_all_drivers(cls, backup_dir: str | Path) (L138): Export and backup all installed third-party drivers to directory.

## src/cortex_unified/system_tools/env_variable_manager.py — Cortex Cleaner — Windows Environment Variable & PATH Optimizer.
- class PathEntry (L26): Path Entry data container.
- class EnvVariable (L36): Env Variable data container.
- class PathAnalysisReport (L45): Path Analysis Report data container.
- class CleanupResult (L56): Cleanup Result data container.
- class EnvironmentVariableManager (L65): Production Windows environment variable and PATH optimizer.
- method EnvironmentVariableManager._read_registry_value(cls, hive, subkey: str, name: str) (L72): Read a single registry value and its type.
- method EnvironmentVariableManager._write_registry_value(cls, hive, subkey: str, name: str, value: str, reg_type: int) (L84): Write a registry value.
- method EnvironmentVariableManager.enumerate_variables(cls, scope: str='User') (L96): List all environment variables for the specified scope.
- method EnvironmentVariableManager.analyze_path(cls) (L123): Analyze both User and System PATH for dead links, duplicates, and empty entries.
- method EnvironmentVariableManager.clean_path(cls, scope: str='User', remove_dead: bool=True, remove_duplicates: bool=True, remove_empty: bool=True) (L176): Clean PATH variable by removing dead links, duplicates, and empty entries.
- method EnvironmentVariableManager.export_env_to_file(cls, output_path: str | Path, scope: str='User', fmt: str='env') (L238): Export environment variables to .env or .bat file.

## src/cortex_unified/system_tools/event_log_cleaner.py — Cortex Cleaner — Enterprise Windows Event Log Sweeper.
- class EventLogChannel (L20): Event Log Channel data container.
- class EventLogCleanResult (L31): Event Log Clean Result data container.
- class EventLogCleaner (L41): Production Windows Event Log manager and sweeper.
- method EventLogCleaner.list_all_logs(cls, progress_cb: Optional[Callable[[int, int, str], None]]=None) (L63): Enumerate all available Windows event log channels and their metrics.
- method EventLogCleaner.clear_log(cls, channel_name: str, backup_directory: Optional[str | Path]=None) (L105): Clear a specific Windows event log with optional backup export.
- method EventLogCleaner.clear_all_logs(cls, backup_directory: Optional[str | Path]=None, progress_cb: Optional[Callable[[int, int, str], None]]=None) (L148): Clean all active Windows event log channels.

## src/cortex_unified/system_tools/event_log_monitor.py — Cortex Cleaner — Windows Event Log Anomaly & Hardware Error Monitor.
- class LogAnomalyEvent (L22): Log Anomaly Event data container.
- class AnomalyScanReport (L34): Anomaly Scan Report data container.
- class EventLogMonitor (L45): Production Windows Event Log hardware and crash anomaly detector.
- method EventLogMonitor.query_anomalies(cls, max_events_per_category: int=15) (L57): Query Event Log channels for recent critical errors and hardware warnings.

## src/cortex_unified/system_tools/external_exposure.py — Explicit, read-only exposure lookup for a router-reported public IPv4.
- class ExposureLookupError(RuntimeError) (L18): Raised for invalid consent, target, credentials, or provider output.
- class ExternalService (L23): External Service data container.
- method ExternalService.to_dict(self) (L32): To dict.
- class ExposureResult (L42): Exposure Result data container.
- method ExposureResult.to_dict(self) (L49): To dict.
- func _public_ipv4(value: str) (L62): _public_ipv4.
- func _default_transport(url: str, headers: Mapping[str, str], timeout: float) (L77): _default_transport.
- class ExternalExposureClient (L105): Opt-in Shodan/Censys host lookup with an injectable transport.
- method ExternalExposureClient.__init__(self, provider: str, api_key: str, api_secret: str='', transport: Transport | None=None) (L108): Initialize External Exposure Client.
- method ExternalExposureClient.lookup(self, public_ip: str, *, consent: bool=False, timeout: float=10.0) (L124): Lookup.
- method ExternalExposureClient._parse_shodan(payload: Mapping[str, Any]) (L154): _parse_shodan.
- method ExternalExposureClient._parse_censys(payload: Mapping[str, Any]) (L180): _parse_censys.
- func _deduplicate(values: list[ExternalService]) (L217): _deduplicate.

## src/cortex_unified/system_tools/firewall_manager.py — Windows Firewall control - block/allow programs and remote addresses.
- class FirewallRule (L35): Firewall Rule data container.
- method FirewallRule.to_dict(self) (L47): To dict.
- class FirewallManager (L62): Create, list, toggle and remove Windows Firewall rules (Cortex-scoped).
- method FirewallManager.is_supported() (L66): Is supported.
- method FirewallManager.block_program(self, program_path: str, direction: str='Outbound', label: str='') (L72): Block a program's traffic. Reversible via remove_rule/toggle.
- method FirewallManager.allow_program(self, program_path: str, direction: str='Outbound', label: str='') (L78): Allow program.
- method FirewallManager.block_remote_address(self, address: str, direction: str='Outbound', label: str='') (L84): Block traffic to/from a remote IP or range.
- method FirewallManager._new_rule(self, action: str, direction: str, label: str, program: str='', remote_address: str='') (L92): _new_rule.
- method FirewallManager.list_rules(self, cortex_only: bool=True) (L120): List rules.
- method FirewallManager.set_enabled(self, name: str, enabled: bool) (L142): Set enabled.
- method FirewallManager.remove_rule(self, name: str) (L150): Remove rule.
- method FirewallManager._parse_rules(out: str | None) (L160): _parse_rules.
- method FirewallManager._valid_address(addr: str) (L192): _valid_address.
- method FirewallManager._ps_quote(value: str) (L214): Single-quote a value for PowerShell, escaping embedded quotes.
- method FirewallManager._run(self, script: str, want_output: bool=False) (L218): _run.

## src/cortex_unified/system_tools/font_cache_manager.py — Cortex Cleaner — Windows Font Cache Inspector & Optimizer.
- class FontEntry (L26): Font Entry data container.
- class FontAnalysisReport (L39): Font Analysis Report data container.
- class FontCleanResult (L51): Font Clean Result data container.
- class FontCacheManager (L58): Production Windows font inventory and orphan cleanup engine.
- method FontCacheManager._get_fonts_dir(cls) (L64): Return the system fonts directory.
- method FontCacheManager._detect_format(cls, file_name: str) (L70): Detect font format from file extension.
- method FontCacheManager.enumerate_fonts(cls) (L81): Enumerate all registered system fonts from the registry.
- method FontCacheManager.analyze(cls) (L135): Produce full analysis report of installed font set.
- method FontCacheManager.clean_orphaned_entries(cls) (L157): Remove orphaned font registry entries (fonts pointing to missing files).

## src/cortex_unified/system_tools/free_space_wipe.py — Free-space wipe - overwrite the unused space on a volume.
- class WipeResult (L32): Wipe Result data container.
- class FreeSpaceWiper (L40): Overwrite a volume's free space (Windows ``cipher /w``).
- method FreeSpaceWiper.is_supported() (L44): Is supported.
- method FreeSpaceWiper.medium_for(self, drive_letter: str) (L48): Return (medium_kind, overwrite_effective) for the drive.
- method FreeSpaceWiper.wipe(self, drive_letter: str, cancel_event: 'threading.Event | None'=None) (L56): Wipe free space on *drive_letter* (e.g. 'C'). Blocking; can be slow.

## src/cortex_unified/system_tools/game_mode.py — Gaming Mode - one-click, fully reversible PC boost for game sessions.
- class BoostReport (L64): Outcome of starting or stopping a boosted session.
- method BoostReport.to_dict(self) (L77): To dict.
- class GameMode (L92): Apply and revert a gaming-session performance profile.
- method GameMode.__init__(self, extra_suspend: tuple[str, ...]=(), dry_run: bool=False) (L95): Initialize Game Mode.
- method GameMode.is_supported() (L112): Boost needs Windows power plans + psutil.
- method GameMode._candidates(self) (L116): Running processes matching the suspend lists (protected excluded).
- method GameMode.preview(self) (L133): Read-only view of exactly what ``start()`` would change.
- method GameMode.start(self) (L149): Apply the boost profile (idempotent; safe while already active).
- method GameMode.stop(self) (L195): Restore power plan and resume everything this session suspended.
- method GameMode.__enter__(self) (L222): __enter__.
- method GameMode.__exit__(self, exc_type, exc, tb) (L229): __exit__.
- method GameMode._pick_boost_plan(self, plans) (L240): Choose the highest-performance scheme available, else None.
- func run_proc_checked(args: list[str]) (L252): Convenience wrapper used by diagnostics; True when exit code is 0.

## src/cortex_unified/system_tools/health_check.py — One-click PC health check - aggregates the fast, read-only diagnostics.
- class HealthCheck (L31): Health Check data container.
- method HealthCheck.to_dict(self) (L39): To dict.
- class HealthReport (L46): Health Report data container.
- method HealthReport.to_dict(self) (L52): To dict.
- class HealthChecker (L61): Runs the read-only health checks and scores them.
- method HealthChecker.run(self, progress: ProgressCB | None=None) (L64): Run.
- method HealthChecker._score(checks: list[HealthCheck]) (L90): _score.
- method HealthChecker._check_disk_space() (L113): _check_disk_space.
- method HealthChecker._check_memory() (L133): _check_memory.
- method HealthChecker._check_disk_health() (L150): _check_disk_health.
- method HealthChecker._check_boot() (L172): _check_boot.
- method HealthChecker._check_security() (L197): _check_security.
- method HealthChecker._check_updates() (L220): _check_updates.

## src/cortex_unified/system_tools/hosts_file_manager.py — Cortex Cleaner — Windows Hosts File Editor & Anti-Telemetry DNS Shield.
- class HostEntry (L22): Host Entry data container.
- class HostsOperationResult (L51): Hosts Operation Result data container.
- class HostsFileManager (L59): Production Windows Hosts file and Anti-Telemetry DNS manager.
- method HostsFileManager.get_hosts_path(cls) (L63): Locate hosts file path across platforms.
- method HostsFileManager.parse_hosts_file(cls, hosts_path: Optional[Path]=None) (L71): Parse hosts file into structured entries.
- method HostsFileManager._create_backup(cls, hosts_path: Path) (L112): Create a timestamped backup before modifying the hosts file.
- method HostsFileManager.save_hosts_entries(cls, entries: List[HostEntry], hosts_path: Optional[Path]=None) (L125): Write modified host entries back to the hosts file.
- method HostsFileManager.apply_anti_telemetry_shield(cls, hosts_path: Optional[Path]=None) (L160): Inject anti-telemetry blocklist rules into hosts file.

## src/cortex_unified/system_tools/junction_auditor.py — Cortex Cleaner — NTFS Hard Link, Junction & Reparse Point Auditor.
- class ReparseItem (L28): Reparse Item data container.
- class JunctionAuditReport (L39): Junction Audit Report data container.
- class JunctionAuditor (L50): Enterprise NTFS Junction Point & Reparse Tag Auditor.
- method JunctionAuditor.__init__(self) (L53): Initialize Junction Auditor.
- method JunctionAuditor.audit(self, root_path: Optional[str]=None, max_depth: int=4) (L57): Audit a folder hierarchy or default system profile for reparse links.
- func JunctionAuditor.audit._scan(dir_path: Path, depth: int) (L77): _scan.
- method JunctionAuditor.remove_dead_junction(self, link_path: str) (L167): Safely unlink a dead junction or symlink without touching target files.

## src/cortex_unified/system_tools/lan_scanner.py — LAN device discovery - see what else is on your local network.
- class LanDevice (L37): Lan Device data container.
- method LanDevice.to_dict(self) (L44): To dict.
- class LanScanner (L49): Enumerate LAN devices from the OS ARP cache (read-only).
- method LanScanner.scan(self) (L52): Scan.
- method LanScanner._vendor_for(mac: str) (L58): Vendor from the authoritative IEEE registry (empty when unknown).
- method LanScanner._parse(cls, out: str | None) (L69): _parse.
- method LanScanner._run(self) (L96): _run.

## src/cortex_unified/system_tools/leftover_cleaner.py — Leftover Cleaner - find and safely remove what an uninstaller leaves behind.
- func edit_distance(a: str, b: str, max_distance: int | None=None) (L64): Exact Levenshtein distance; early-exits once *max_distance* is exceeded
- func match_string_to_product(candidate: str, product_name: str) (L91): Decide whether *candidate* (a folder/key name) names *product_name*.
- func build_tokens(display_name: str, publisher: str='') (L138): Extract specific-enough search tokens from an app's display name.
- func confidence_level(raw: int) (L179): Map a raw signed score to a human review tier (BCU mapping).
- class SafetyPolicy (L222): Paths the scanner/cleaner must never propose or touch.
- method SafetyPolicy.__post_init__(self) (L230): Normalize stored paths to case-folded absolute form for matching.
- method SafetyPolicy.build(cls, extra_protected: Iterable[str]=()) (L238): Build a policy protecting known-folder roots plus *extra_protected*.
- method SafetyPolicy.is_prohibited(self, path: str | Path) (L258): True when *path* IS a protected root (its children are allowed).
- func _has_system_attribute(path: str) (L272): Windows System attribute means 'not a leftover candidate'.
- func _is_reparse_point(path: str) (L283): Junction/symlink check - such entries are recorded, never descended.
- class InstalledApp (L313): One entry from an Uninstall registry branch.
- method InstalledApp.to_dict(self) (L325): Return a plain-dict view of this app entry (for journals/reports).
- func detect_installer_type(key_name: str, uninstall_string: str) (L335): Classify the installer family from registry fingerprints.
- func read_installed_apps() (L347): Enumerate installed apps from all Uninstall branches (read-only).
- func _read_uninstall_entry(hive, hive_name: str, branch: str, subkey: str) (L381): Read one Uninstall subkey (DisplayName, Publisher, ...) via winreg.
- func _clean_registry_path(value: str) (L421): Strip quotes/arguments/icon-index suffixes from a registry path value.
- func _tasks_root() (L433): The Windows scheduled-tasks definition folder.
- class LeftoverFinding (L439): One reviewed-able leftover candidate with its evidence.
- method LeftoverFinding.to_dict(self) (L450): Return a plain-dict view of this finding (for journals/reports).
- func _add(f: LeftoverFinding, points: int, reason: str) (L460): Add *points* for *reason* to a finding and refresh its confidence level.
- class ExclusionsStore (L471): Persisted list of paths the user chose to keep.
- method ExclusionsStore.__init__(self, path: str | Path | None=None) (L481): Initialize the store, loading from *path* (default
- method ExclusionsStore._load(self) (L491): Load the JSON exclusion list; unreadable/corrupt file means empty.
- method ExclusionsStore.save(self) (L506): Atomically persist the exclusion list (tmp file + replace).
- method ExclusionsStore._norm(path: str | Path) (L526): Normalize a path (case + separators) for exclusion matching.
- method ExclusionsStore.add(self, path: str | Path) (L533): Exclude *path* (and everything beneath it). Persists immediately.
- method ExclusionsStore.discard(self, path: str | Path) (L541): Remove *path* from the exclusions and persist immediately.
- method ExclusionsStore.paths(self) (L549): Sorted tuple of all excluded (normalized) paths.
- method ExclusionsStore.__len__(self) (L553): Number of excluded paths.
- method ExclusionsStore.is_excluded(self, path: str | Path) (L557): True when *path* IS an excluded entry or lives beneath one.
- class LeftoverScanner (L594): Finds leftovers for one uninstalled app, or orphaned folders generally.
- method LeftoverScanner.__init__(self, installed_apps: Sequence[InstalledApp] | None=None, policy: SafetyPolicy | None=None, exclusions: ExclusionsStore | None=None, cancel_event=None) (L605): Initialize the scanner; the app inventory loads lazily on first scan.
- method LeftoverScanner._cancelled(self) (L619): True when the caller's cancel_event (if any) has been set.
- method LeftoverScanner._allowed(self, f: LeftoverFinding) (L623): True when the finding is not under a user exclusion.
- method LeftoverScanner._ensure_inventory(self) (L629): Lazily load installed apps and build name/publisher/location sets.
- method LeftoverScanner._load_live_inventory(self) (L645): Return a copy of the installed-app list (loading it if needed).
- method LeftoverScanner.scan_app(self, app: InstalledApp) (L653): Full leftover sweep for one uninstalled application.
- method LeftoverScanner.scan_orphans(self) (L685): Find Program Files orphan folders (no live app claims them).
- method LeftoverScanner._disambiguate_similar(self, app: InstalledApp, findings: dict[str, LeftoverFinding]) (L715): Penalise weaker name matches when several folders compete.
- method LeftoverScanner._sweep_roots(self) (L745): Sweep roots: Program Files (both), ProgramData, AppData variants.
- method LeftoverScanner._program_dir_roots(self) (L773): Program-directories only (Program Files x2, LocalAppData\Programs).
- method LeftoverScanner._sweep_filesystem(self, app: InstalledApp, tokens: tuple[str, ...], findings: dict[str, LeftoverFinding]) (L785): Walk every sweep root (max 2 levels) matching folder names to tokens.
- method LeftoverScanner._walk_fs_level(self, app: InstalledApp, tokens: tuple[str, ...], directory: str, depth: int, findings: dict[str, LeftoverFinding]) (L791): Depth-limited directory walk collecting token-matching folders.
- method LeftoverScanner._score_folder_content(self, path: str, f: LeftoverFinding, app: InstalledApp) (L838): Score a matched folder by walking its contents (read-only).
- method LeftoverScanner._score_orphan_folder(self, path: str, f: LeftoverFinding) (L886): Score an orphan folder: emptiness, executables, file count, name.
- method LeftoverScanner._claimed_by_live_app(self, path: str, name_lower: str) (L919): True when a currently-installed app claims this name/location.
- method LeftoverScanner._folder_identity(self, name: str) (L931): Strip trailing version numbers/decorations from a folder name.
- method LeftoverScanner._sweep_registry(self, app: InstalledApp, tokens: tuple[str, ...], findings: dict[str, LeftoverFinding]) (L945): Walk HKLM/HKCU SOFTWARE branches (read-only) matching keys to tokens.
- method LeftoverScanner._walk_reg_level(self, app: InstalledApp, tokens: tuple[str, ...], hive, hive_name: str, key, display_path: str, depth: int, findings: dict[str, LeftoverFinding]) (L970): Recursive registry walk: matches subkey names or explicit pointers.
- method LeftoverScanner._explicit_pointer(self, key, app: InstalledApp) (L1018): True when a value under *key* references the app's install dir.
- method LeftoverScanner.find_residual_uninstall_keys(self, app: InstalledApp) (L1040): Uninstall keys still present after the app was removed.
- method LeftoverScanner._same_product(a: InstalledApp, b: InstalledApp) (L1068): True when two uninstall entries denote the same product.
- method LeftoverScanner._start_menu_dirs(self) (L1085): Existing user and common Start Menu directories, if present.
- method LeftoverScanner._sweep_shortcuts(self, app: InstalledApp, findings: dict[str, LeftoverFinding]) (L1096): Flag .lnk files whose target lives in the dead install location.
- method LeftoverScanner._com_branches(self) (L1133): Registry branches searched for orphaned COM registrations.
- method LeftoverScanner._sweep_com(self, app: InstalledApp, findings: dict[str, LeftoverFinding]) (L1143): Flag CLSID/TypeLib registrations whose server binary is gone.
- method LeftoverScanner._com_server_path(key, branch: str) (L1199): Default value naming the server binary under a COM key.
- method LeftoverScanner._sweep_inno_log(self, app: InstalledApp, findings: dict[str, LeftoverFinding]) (L1240): Files the installer wrote that its own uninstaller failed to remove.
- method LeftoverScanner._sweep_services(self, app: InstalledApp, findings: dict[str, LeftoverFinding]) (L1284): Services whose ImagePath binary lives in the dead install dir.
- method LeftoverScanner._sweep_tasks(self, app: InstalledApp, findings: dict[str, LeftoverFinding]) (L1333): Scheduled tasks whose <Command> points into the dead install dir.
- method LeftoverScanner._cross_check(self, app: InstalledApp, findings: dict[str, LeftoverFinding]) (L1365): Penalize findings that a still-installed sibling app claims.
- class CleanOutcome (L1400): What happened to one finding during cleanup.
- method CleanOutcome.to_dict(self) (L1409): Return a plain-dict view of this outcome (for journals).
- class LeftoverCleaner (L1415): Removes reviewed findings with Recycle Bin + registry backups + journal.
- method LeftoverCleaner.__init__(self, backup_root: str | Path | None=None, policy: SafetyPolicy | None=None) (L1434): Initialize with a safety policy and session-backup root
- method LeftoverCleaner.clean(self, findings: Sequence[LeftoverFinding], create_restore_point: bool=False, exclusions: ExclusionsStore | None=None, cancel_event=None) (L1442): Remove reviewed findings, one per disposition, with undo layers.
- method LeftoverCleaner._restore_point() (L1493): Best-effort System Restore checkpoint; returns an honest note.
- method LeftoverCleaner._recycle(self, f: LeftoverFinding) (L1508): Move a file/folder/shortcut to the Recycle Bin via send2trash.
- method LeftoverCleaner._clean_registry(self, f: LeftoverFinding, session: Path | None) (L1527): Export a registry key with ``reg export``, then delete it.
- method LeftoverCleaner._clean_service(self, f: LeftoverFinding, session: Path | None) (L1566): Stop + delete a Windows service, with a .reg backup first.
- method LeftoverCleaner._clean_task(self, f: LeftoverFinding, session: Path | None) (L1601): Delete a scheduled task; its XML definition is backed up first.
- method LeftoverCleaner._tasks_root_for(self, task_name: str) (L1633): On-disk XML for a task: Tasks stores '<name>.xml' per task.
- method LeftoverCleaner._write_journal(self, session: Path, journal: list[dict], outcomes: list[CleanOutcome], restore_note: str='') (L1639): Write the session journal.json atomically (tmp file + os.replace).
- func stamp_now() (L1664): Current local time as an ISO-like ``YYYY-MM-DDTHH:MM:SS`` string.

## src/cortex_unified/system_tools/load_tester.py — Load / resilience tester - measure how much YOUR OWN service can take.
- class Authorization (L52): Authorization data container.
- method Authorization.to_dict(self) (L60): To dict.
- class TargetAuthorizer (L68): Decides whether a target may be load-tested. Private = yours = allowed.
- method TargetAuthorizer.classify(host: str) (L72): Return (category, resolved_ip) for *host* without any network calls
- method TargetAuthorizer.authorize(self, host: str, ownership_token: str | None=None, verify_public: bool=True) (L99): Authorize.
- method TargetAuthorizer._verify_ownership(host: str, token: str) (L124): Fetch the token file the user placed on their server and compare.
- method TargetAuthorizer.new_token() (L139): Generate a random token for the user to host on their server.
- class HttpLoadConfig (L150): Http Load Config data container.
- class TcpLoadConfig (L162): Tcp Load Config data container.
- class LoadResult (L172): Load Result data container.
- method LoadResult.rps(self) (L185): Rps.
- method LoadResult.error_rate(self) (L190): Error rate.
- method LoadResult.percentile(self, p: float) (L194): Percentile.
- method LoadResult.summary(self) (L202): Summary.
- class LoadTester (L227): Runs authorized load tests and reports resilience metrics.
- method LoadTester.__init__(self) (L230): Initialize Load Tester.
- method LoadTester.run_http(self, cfg: HttpLoadConfig, auth: Authorization, progress: ProgressCB | None=None, cancel_event: threading.Event | None=None, confirm: bool=False, safe_mode: bool=False) (L236): Run http.
- func LoadTester.run_http.worker(idx: int) (L261): Worker.
- method LoadTester.run_tcp(self, cfg: TcpLoadConfig, auth: Authorization, progress: ProgressCB | None=None, cancel_event: threading.Event | None=None, confirm: bool=False, safe_mode: bool=False) (L308): Run tcp.
- func LoadTester.run_tcp.worker(idx: int) (L332): Worker.
- method LoadTester._run_pool(worker, conc, deadline, cancel, progress, result, start) (L366): _run_pool.
- method LoadTester._progress_snapshot(result: LoadResult, start: float, final: bool=False) (L384): _progress_snapshot.
- method LoadTester._audit(kind: str, target: str, auth: Authorization, conc: int, dur: int) (L399): _audit.

## src/cortex_unified/system_tools/memory_compression_tuner.py — Cortex Cleaner — Windows Memory Compression & SysMain Optimizer.
- class MemoryCompressionStatus (L25): Memory Compression Status data container.
- method MemoryCompressionStatus.compressed_mb(self) (L38): Compressed mb.
- method MemoryCompressionStatus.total_ram_gb(self) (L43): Total ram gb.
- method MemoryCompressionStatus.available_ram_gb(self) (L48): Available ram gb.
- class MemoryTunerReport (L54): Memory Tuner Report data container.
- class MemoryCompressionTuner (L60): Enterprise Windows Memory Compression & MMAgent Optimizer.
- method MemoryCompressionTuner.__init__(self) (L63): Initialize Memory Compression Tuner.
- method MemoryCompressionTuner.audit(self) (L67): Query memory compression configuration and memory pressure.
- class MEMORYSTATUSEX(ctypes.Structure) (L113): M E M O R Y S T A T U S E X.
- method MemoryCompressionTuner.set_memory_compression(self, enable: bool) (L157): Enable or disable Windows memory compression via MMAgent.

## src/cortex_unified/system_tools/memory_optimizer.py — Cortex Cleaner — Working Set & System RAM Memory Optimizer.
- class SystemRamMetrics (L22): System Ram Metrics data container.
- class ProcessMemoryItem (L34): Process Memory Item data container.
- class MemoryOptimizeResult (L44): Memory Optimize Result data container.
- method MemoryOptimizeResult.__post_init__(self) (L51): __post_init__.
- method MemoryOptimizeResult.ok(self) (L59): Ok.
- method MemoryOptimizeResult.message(self) (L64): Message.
- method MemoryOptimizeResult.to_dict(self) (L70): To dict.
- class MemoryOptimizer (L82): Production Windows RAM composition inspector and process working set optimizer.
- method MemoryOptimizer.get_system_ram_metrics(cls) (L92): Query physical RAM metrics using psutil and Win32 GlobalMemoryStatusEx.
- method MemoryOptimizer.scan_process_memory(cls, limit: int=30) (L112): Scan active processes and sort by Working Set (physical RAM consumption).
- method MemoryOptimizer.trim_process_working_set(cls, pid: int) (L143): Trim the working set of a specific process via Win32 EmptyWorkingSet.
- method MemoryOptimizer.optimize_all_background_working_sets(cls, pids: Optional[List[int]]=None) (L179): Trim working sets of non-critical processes.
- func memory_stats() (L204): Query current system RAM statistics and top consumer processes.
- func optimize(min_rss_mb: int=50, dry_run: bool=True) (L229): Optimize working sets of non-critical background processes.

## src/cortex_unified/system_tools/memory_standby_purger.py — Windows NT Kernel RAM Standby List & Working Set Purger.
- class LUID(ctypes.Structure) (L39): L U I D.
- class LUID_AND_ATTRIBUTES(ctypes.Structure) (L47): L U I D_ A N D_ A T T R I B U T E S.
- class TOKEN_PRIVILEGES(ctypes.Structure) (L55): T O K E N_ P R I V I L E G E S.
- class MEMORYSTATUSEX(ctypes.Structure) (L63): M E M O R Y S T A T U S E X.
- class MemorySnapshot (L79): Current system memory status.
- method MemorySnapshot.to_dict(self) (L89): To dict.
- class PurgeResult (L102): Outcome of kernel memory purge operations.
- class MemoryStandbyPurger (L112): Manages kernel memory standby list purging and working set trimming.
- method MemoryStandbyPurger.__init__(self) (L115): Initialize Memory Standby Purger.
- method MemoryStandbyPurger.get_memory_snapshot(self) (L129): Query real-time physical and virtual memory allocation.
- method MemoryStandbyPurger.enable_privilege(self, priv_name: str) (L149): Enable specified security privilege in current process token.
- method MemoryStandbyPurger.purge_standby_list(self) (L177): Purge system standby list cache (MemoryPurgeStandbyList = 4).
- method MemoryStandbyPurger.purge_working_sets(self) (L181): Flush working sets across processes (MemoryEmptyWorkingSets = 2).
- method MemoryStandbyPurger.purge_modified_page_list(self) (L185): Flush modified page list to storage (MemoryPurgeModifiedPageList = 3).
- method MemoryStandbyPurger._send_memory_command(self, cmd_val: int, label: str) (L189): Issue command to NtSetSystemInformation.

## src/cortex_unified/system_tools/mft_slack_scrubber.py — NTFS Master File Table ($MFT) & Directory Index Slack Scrubber.
- class NtfsMftGeometry (L24): NTFS volume geometry and MFT allocation metadata.
- method NtfsMftGeometry.to_dict(self) (L39): To dict.
- class MftScrubReport (L55): Report on MFT slack and index allocation sanitization.
- method MftScrubReport.to_dict(self) (L65): To dict.
- class MftSlackScrubber (L77): Auditor and scrubber for NTFS Master File Table and directory slack space.
- method MftSlackScrubber.__init__(self, volume: str='C:') (L80): Initialize Mft Slack Scrubber.
- method MftSlackScrubber.query_geometry(self) (L87): Query volume geometry using fsutil fsinfo ntfsinfo.
- method MftSlackScrubber.parse_ntfsinfo_output(cls, volume: str, text: str) (L109): Parse stdout of 'fsutil fsinfo ntfsinfo <volume>'.
- func MftSlackScrubber.parse_ntfsinfo_output._parse_int(s: str) (L120): _parse_int.
- method MftSlackScrubber.audit(self) (L149): Perform non-destructive audit of MFT record slack.
- method MftSlackScrubber.scrub(self) (L160): Execute sanitization of unallocated MFT slack records and index slack.

## src/cortex_unified/system_tools/model_cache_manager.py — Model cache manager – hardlink-aware HF hub, Ollama, LM Studio, ComfyUI.
- func _verify_path(path: Path, allowed_roots: List[Path]) (L61): Clearmodel-style path traversal guard – path must be inside allowed_roots.
- class ModelStore (L81): One cache store (HF hub, Ollama, etc.).
- method ModelStore.to_dict(self) (L95): To dict.
- func _hardlink_aware_size(root: Path) (L111): Return (logical, actual, count, inode_map) for root.
- class ModelCacheManager (L150): Scan and safely clean model caches.
- method ModelCacheManager._get_comfyui_candidates(cls) (L174): _get_comfyui_candidates.
- method ModelCacheManager.COMFYUI_CANDIDATES(self) (L199): COMFYUI CANDIDATES.
- method ModelCacheManager._first_existing(self, candidates: List[Path | None] | None) (L208): _first_existing.
- method ModelCacheManager.scan_hf_hub(self, progress=None, cancel_event=None) (L226): Measure HF hub cache, hardlink-aware, and count orphan blobs.
- method ModelCacheManager.scan_ollama(self) (L284): Scan ollama.
- method ModelCacheManager.scan_all(self, progress=None, cancel_event=None) (L296): Scan all.
- method ModelCacheManager.clean_hf_orphans(self, dry_run: bool=True, timeout: int=600) (L321): Run ``huggingface-cli delete-cache --orphans`` safely.
- method ModelCacheManager.delete_hf_revision(self, repo: str, revision: str, dry_run: bool=True, timeout: int=300) (L349): Delete a specific HF revision via ``huggingface-cli delete-cache`` (verified).
- method ModelCacheManager.explain_quantization_saving(model_bytes: int, quant: str='Q4_K_M') (L370): Quantization saving estimate per Interconnectd table (FP16 2B/param).
- method ModelCacheManager.read_safetensors_metadata(path: Path | str) (L383): Zero-copy SafeTensors metadata parser.
- method ModelCacheManager.read_gguf_metadata(path: Path | str) (L435): Zero-copy GGUF binary metadata parser (extracts arch, quantization, context size).
- method ModelCacheManager.summarize(self) (L461): Summarize.

## src/cortex_unified/system_tools/network_automation.py — Safe Windows scheduling for unattended private-LAN inventory scans.
- class NetworkSchedule (L26): Network Schedule data container.
- class NetworkScheduleError(RuntimeError) (L38): Raised when schedule validation or OS task creation fails.
- func _validated(spec: NetworkSchedule) (L42): _validated.
- func build_scan_command(spec: NetworkSchedule) (L72): Build the fixed CLI command; no user-provided executable is accepted.
- func build_windows_arguments(spec: NetworkSchedule) (L89): Build windows arguments.
- class NetworkScanScheduler (L106): Purpose-built adapter that can only schedule Cortex LAN scans.
- method NetworkScanScheduler.supported() (L110): Supported.
- method NetworkScanScheduler.create(self, spec: NetworkSchedule) (L114): Create.
- method NetworkScanScheduler.delete(self) (L127): Delete.
- method NetworkScanScheduler.status(self) (L136): Status.

## src/cortex_unified/system_tools/network_discovery.py — Deep LAN device discovery - find everything actually on your network.
- class Device (L177): One discovered device, with the evidence that found it.
- method Device.randomized_mac(self) (L200): True when the device is using a privacy/randomized MAC.
- method Device.label(self) (L205): Best available human name for the device, never empty.
- method Device._looks_like_uuid(text: str) (L232): True for machine-generated identifiers not worth showing as a name.
- method Device.kind(self) (L239): Best-effort device category, derived only from observed evidence.
- method Device.evidence(self) (L292): Plain description of how we know this device is there.
- method Device.merge(self, other: 'Device') (L307): Fold another observation of the same device into this one.
- method Device.to_dict(self) (L336): To dict.
- class Interface (L372): A local IPv4 interface worth scanning.
- method Interface.network(self) (L380): Network.
- class DiscoveryResult (L389): Everything a scan found, plus evidence-backed audit results.
- method DiscoveryResult.to_dict(self) (L403): To dict.
- class NetworkDiscovery (L431): Multi-protocol LAN discovery. Probes only this PC's own subnets.
- method NetworkDiscovery.__init__(self, timeout_s: float=4.0, workers: int=128) (L434): Initialize Network Discovery.
- method NetworkDiscovery.scan(self, progress: ProgressFn | None=None, cancel_event: threading.Event | None=None, deep: bool=True, rounds: int=2, audit_profile: str='targeted', include_upnp_wan: bool=False, record_history: bool=False, requested_networks: Iterable[str] | None=None, custom_ports: Iterable[int] | None=None, nmap_modes: Iterable[str] | str | None=None, advisory_catalog_path: str | None=None) (L442): Discover devices, then run the selected defensive audit tier.
- func NetworkDiscovery.scan._say(msg: str) (L482): _say.
- func NetworkDiscovery.scan._cancelled() (L489): _cancelled.
- method NetworkDiscovery.local_interfaces() (L663): Return this PC's up, private IPv4 interfaces.
- method NetworkDiscovery._local_devices(interfaces: list[Interface]) (L693): Represent this PC itself, one entry per active interface.
- method NetworkDiscovery.default_gateways(self) (L726): Return default-gateway IPs (used to label the router).
- method NetworkDiscovery._read_neighbors(self) (L753): Read the OS neighbour cache (ARP for IPv4, NDP for IPv6).
- method NetworkDiscovery._read_neighbors_windows(self) (L761): Use ``Get-NetNeighbor``, which exposes reachability state too.
- method NetworkDiscovery._read_arp_command(self) (L786): Fallback: parse ``arp -a`` (works on every platform).
- method NetworkDiscovery._broadcast_ping(targets: list[ipaddress.IPv4Network]) (L813): Send a UDP datagram to each subnet's broadcast address.
- method NetworkDiscovery._arp_sweep(self, hosts: Iterable[str], cancel_event: threading.Event | None, settle_s: float=2.0) (L829): Send one cheap UDP datagram per host to force ARP resolution.
- func NetworkDiscovery._arp_sweep._poke(ip: str) (L846): _poke.
- method NetworkDiscovery._is_ipv4(value: str) (L872): _is_ipv4.
- method NetworkDiscovery._usable_host(cls, ip: str, mac: str) (L883): Filter out entries that are not a real, present device.
- method NetworkDiscovery._ip_sort_key(ip: str) (L906): _ip_sort_key.
- method NetworkDiscovery._merge(into: dict[str, Device], found: Iterable[Device]) (L916): _merge.
- method NetworkDiscovery._run_ps(self, script: str, timeout: int=45) (L927): _run_ps.
- method NetworkDiscovery._discover_mdns(self, cancel_event: threading.Event | None) (L943): Query mDNS for common service types and collect names + addresses.
- method NetworkDiscovery._absorb_mdns(self, found: dict[str, Device], data: bytes, src_ip: str) (L998): Parse an mDNS response and record names/services for the sender.
- method NetworkDiscovery._split_service_instance(value: str) (L1046): Split ``Living Room._googlecast._tcp.local`` into (type, instance).
- method NetworkDiscovery._build_dns_query(name: str, qtype: int=12) (L1059): Build a minimal DNS query packet (PTR by default) for *name*.
- method NetworkDiscovery._parse_dns_records(cls, data: bytes) (L1069): Parse answer/authority/additional records out of a DNS message.
- method NetworkDiscovery._read_name(data: bytes, offset: int) (L1114): Read a (possibly compressed) DNS name; returns (name, next_offset).
- method NetworkDiscovery._discover_ssdp(self, cancel_event: threading.Event | None) (L1144): Send an SSDP M-SEARCH and record every responder.
- method NetworkDiscovery._discover_wsd(self, cancel_event: threading.Event | None) (L1206): Send a WS-Discovery Probe - the way Windows itself finds PCs/printers.
- method NetworkDiscovery._pseudo_uuid() (L1270): _pseudo_uuid.
- method NetworkDiscovery._parse_http_headers(data: bytes) (L1278): Parse SSDP's HTTP-style headers into a lower-cased dict.
- method NetworkDiscovery._resolve_names(self, devices: dict[str, Device], cancel_event: threading.Event | None) (L1289): Fill in hostnames via reverse DNS and NetBIOS, in parallel.
- func NetworkDiscovery._resolve_names._resolve(device: Device) (L1296): _resolve.
- method NetworkDiscovery._netbios_name(self, ip: str, timeout: float=0.6) (L1319): Send a NetBIOS node-status query (UDP 137) and read the name.
- method NetworkDiscovery._fingerprint(self, devices: dict[str, Device], cancel_event: threading.Event | None) (L1357): Enumerate services only on discovered, in-scope private hosts.
- method NetworkDiscovery._build_notes(devices: list[Device], targets: list[ipaddress.IPv4Network], gateways: set[str]) (L1428): Explain the scan's limits, so gaps read as facts not failures.

## src/cortex_unified/system_tools/network_inventory.py — Persistent, point-in-time network inventory with typed change reporting.
- func _text(value: Any, limit: int=512) (L32): Coerce to a trimmed, length-capped string; empty values become "".
- func _json_safe(value: Any, depth: int=0) (L39): Recursively convert a value into JSON-serializable primitives with depth/size caps.
- class InventoryService (L60): Inventory Service data container.
- method InventoryService.key(self) (L68): Stable dedup key of protocol, port, and lowercase name.
- method InventoryService.to_dict(self) (L72): Serialize the service with details made JSON-safe.
- class InventoryFinding (L83): Inventory Finding data container.
- method InventoryFinding.key(self) (L91): Dedup key: the code, falling back to the title.
- method InventoryFinding.to_dict(self) (L95): Serialize the finding with details made JSON-safe.
- class InventoryDevice (L106): Inventory Device data container.
- method InventoryDevice.to_dict(self) (L117): Serialize the device, expanding services and findings.
- class DeviceMetadata (L132): Device Metadata data container.
- method DeviceMetadata.to_dict(self) (L141): Serialize metadata (custom name, trust state, tags, notes).
- class InventoryChange (L154): Inventory Change data container.
- method InventoryChange.to_dict(self) (L164): Serialize the change, JSON-sanitizing previous/current values.
- class InventoryChanges (L173): Inventory Changes data container.
- method InventoryChanges.to_dict(self) (L183): Serialize the change groups as lists of change dicts.
- class InventorySnapshot (L198): Inventory Snapshot data container.
- method InventorySnapshot.to_dict(self) (L211): Serialize the snapshot: devices, changes, gateway MAC, identity notice.
- func _normalize_mac(value: Any) (L223): Return a lowercase colon-separated MAC, or "" when malformed.
- func _randomized_mac(mac: str) (L231): Detect a locally-administered (randomized/privacy) MAC via OUI bits.
- func _identity(device: InventoryDevice) (L241): Pick the best identity key (device_id > stable MAC > IP) plus confidence.
- func _service(value: Any) (L254): Coerce a string/int/mapping/object into a validated InventoryService.
- func _finding(value: Any) (L297): Coerce a mapping or finding object into a validated InventoryFinding.
- func _get(value: Any, name: str, default: Any=None) (L322): Read an attribute mapping-style or object-style, with a default.
- func normalize_device(value: Any) (L330): Normalize mappings or discovery objects into a validated observation.
- func identity_key_for(value: Any) (L373): Return the same stable/best-effort identity key used by inventory.
- class NetworkInventory (L378): SQLite inventory with all writes in explicit transactions.
- method NetworkInventory.__init__(self, path: str | Path | None=None, retention: int=50) (L381): Open (creating parent dirs) the SQLite store, bound retention, and migrate.
- method NetworkInventory.close(self) (L403): Close the in-memory connection, if any; file DBs close per use.
- method NetworkInventory.__enter__(self) (L410): Return self for context-manager use.
- method NetworkInventory.__exit__(self, *_args: Any) (L414): Close the inventory on context exit.
- method NetworkInventory._new_connection(self) (L418): Open a SQLite connection with row access and FK/busy-timeout pragmas.
- method NetworkInventory._connect(self) (L429): Reuse the memory connection, or open a fresh file connection.
- method NetworkInventory._release(self, connection: sqlite3.Connection) (L435): Close a file connection; keep the shared memory connection open.
- method NetworkInventory._migrate(self) (L440): Create or upgrade the schema version in a transaction (v0 -> v2).
- method NetworkInventory.record_snapshot(self, devices: Iterable[Any], observed_at: dt.datetime | str | None=None, gateway_mac: str='') (L558): Thread-safe compatibility API for complete point-in-time snapshots.
- method NetworkInventory._record_snapshot(self, devices: Iterable[Any], observed_at: dt.datetime | str | None=None, gateway_mac: str='') (L568): Atomically store a snapshot and compare it with the prior one.
- method NetworkInventory.update(self, devices: Iterable[Any], findings: Iterable[Any]=()) (L629): Persist current devices and return the requested focused change groups.
- method NetworkInventory._load_previous(connection: sqlite3.Connection) (L675): Load the newest snapshot's observations, services, findings, and gateway.
- method NetworkInventory._compare(current: Mapping[str, tuple[InventoryDevice, str]], previous: Mapping[str, dict[str, Any]], previous_gateway: str, gateway_mac: str) (L724): Diff current vs previous observations, flagging identity/service/severity changes.
- method NetworkInventory._store_device(connection: sqlite3.Connection, snapshot_id: int, timestamp: str, identity_key: str, confidence: str, device: InventoryDevice) (L848): Upsert device, observation, service, and finding rows for one snapshot.
- method NetworkInventory._enforce_retention(self, connection: sqlite3.Connection) (L913): Delete snapshots beyond the retention limit and orphaned catalog rows.
- method NetworkInventory._metadata_identity(value: Any) (L934): Validate an ``id:/mac:/ip:`` key, or derive one from a device.
- method NetworkInventory._metadata_values(custom_name: str, trust_state: str, tags: Iterable[str] | str, notes: str) (L949): Validate and normalize custom name, trust state, tags, and notes.
- method NetworkInventory.set_metadata(self, identity: Any, *, custom_name: str='', trust_state: str='unknown', tags: Iterable[str] | str=(), notes: str='') (L971): Atomically create or replace user-owned device metadata.
- method NetworkInventory.get_metadata(self, identity: Any) (L1008): Fetch one device's user metadata, or ``None``.
- method NetworkInventory.list_metadata(self) (L1022): Return all device metadata records ordered by identity key.
- method NetworkInventory._metadata_from_row(row: sqlite3.Row) (L1035): Rebuild DeviceMetadata from a database row, tolerating bad tag JSON.
- method NetworkInventory.exposure_trends(self, limit: int=50) (L1055): Return bounded per-snapshot device/service/finding aggregates.
- method NetworkInventory._csv_cell(value: Any) (L1083): Escape CSV cells that would parse as spreadsheet formulas.
- method NetworkInventory._csv_value(value: Any) (L1091): Strip the formula-escape apostrophe when importing CSV cells.
- method NetworkInventory.export_inventory_csv(self, path: str | Path) (L1100): Export the latest inventory plus metadata with formula escaping.
- method NetworkInventory.import_inventory_csv(self, path: str | Path, *, dry_run: bool=True, overwrite: bool=False) (L1144): Validate and optionally import metadata in one transaction.
- method NetworkInventory.snapshot_count(self) (L1216): Number of retained snapshots in the store.
- method NetworkInventory.device_lifetimes(self) (L1226): Return retained first/last-seen metadata for display or export.
- func _timestamp(value: dt.datetime | str | None) (L1240): Coerce None/str/datetime to a UTC ISO-8601 timestamp ending in ``Z``.

## src/cortex_unified/system_tools/network_monitor.py — Network connection monitor - see what's talking to your machine and out.
- class Connection (L50): Connection data container.
- method Connection.listening_public(self) (L65): Listening public.
- method Connection.remote_external(self) (L71): Remote external.
- method Connection.to_dict(self) (L77): To dict.
- func _is_private(addr: str) (L95): _is_private.
- class NetworkMonitor (L106): Read-only listing of active network connections and their owners.
- method NetworkMonitor.connections(self) (L109): Connections.
- method NetworkMonitor._meta_for(psutil, pid: int) (L156): Return (name, exe_path, friendly_description) for a PID.
- method NetworkMonitor.summarize(conns: list[Connection]) (L176): Summarize.

## src/cortex_unified/system_tools/network_scan_cli.py — Noninteractive entry point for scheduled private-LAN inventory scans.
- func _parser() (L17): _parser.
- func _write_atomic(path: str, payload: dict) (L31): _write_atomic.
- func main(argv: list[str] | None=None) (L50): Main.

## src/cortex_unified/system_tools/network_security_audit.py — Evidence-backed analysis for authorized private-LAN observations.
- class SecurityFinding (L15): Security Finding data container.
- method SecurityFinding.__post_init__(self) (L28): __post_init__.
- method SecurityFinding.to_dict(self) (L37): To dict.
- method SecurityFinding.finding_id(self) (L54): Finding id.
- method SecurityFinding.description(self) (L59): Description.
- method SecurityFinding.recommendation(self) (L64): Recommendation.
- method SecurityFinding.cve(self) (L69): Cve.
- func _evidence(observation: ServiceObservation, extra: str='') (L74): _evidence.
- func _finding(observation: ServiceObservation, code: str, severity: str, title: str, detail: str, remediation: str, confidence: float, extra: str='') (L86): _finding.
- func _observation_findings(observation: ServiceObservation) (L112): _observation_findings.
- func analyze_services(services: Iterable[ServiceObservation], catalog: Any | None=None) (L221): Compatibility analysis entry point returning fingerprint and findings.
- func _get(value: Any, name: str, default: Any=None) (L241): _get.
- func _device_observations(device: Any) (L248): _device_observations.
- func _deduplicate(findings: Iterable[SecurityFinding]) (L262): _deduplicate.
- func audit_devices(devices: Iterable[Any], vulnerability_catalog: Any | None=None) (L276): Analyze supplied evidence only; this function performs no network I/O.
- func audit_wan(wan_status: Any) (L349): Report enabled IGD mappings as exposure observations, never connectivity tests.

## src/cortex_unified/system_tools/network_service_scanner.py — Bounded, non-destructive service observation on authorized private LANs.
- class ScanProfile(Enum) (L33): Probe breadth for a scan.
- func _json_safe(value: Any) (L47): Return a deterministic JSON-native representation.
- class ServiceObservation (L63): One observed service endpoint on an authorized host.
- method ServiceObservation.to_dict(self) (L94): Serialize the observation with NaN/Inf-safe latency and confidence.
- method ServiceObservation.target(self) (L117): Alias for the observed IP.
- method ServiceObservation.service(self) (L122): Alias for the service name.
- method ServiceObservation.details(self) (L127): Alias for the metadata dict.
- method ServiceObservation.evidence(self) (L132): Evidence strings from metadata, always as a list.
- func parse_allowed_networks(values: Iterable[str | ipaddress.IPv4Network]) (L192): Validate explicit private IPv4 scopes.
- func parse_network_scope_spec(value: str) (L209): Parse private IPv4 hosts, CIDRs, or inclusive address ranges.
- func is_authorized_target(value: object, allowed_networks: Iterable[str | ipaddress.IPv4Network]) (L240): Pure scope check used immediately before every active probe.
- func ports_for_profile(profile: ScanProfile) (L262): Return the TCP ports a profile covers; DEEP means every port.
- func normalize_custom_ports(values: Iterable[int] | None) (L273): Validate a bounded custom TCP-port set without opening sockets.
- func parse_custom_port_spec(value: str) (L294): Parse comma-separated ports/ranges into the bounded validator.
- func _clean(data: bytes) (L319): Decode response bytes to printable, length-capped text.
- func _recv(sock: socket.socket, limit: int=_MAX_RESPONSE) (L330): Bounded non-blocking-ish receive loop capped at ``_MAX_RESPONSE`` bytes.
- func _product_version(text: str) (L350): Extract product/version from SSH, FTP, or HTTP banner patterns.
- func _service_from_banner(text: str) (L365): Identify only unambiguous protocol greetings.
- class _RateLimiter (L388): Spaces probe starts at most ``rate`` per second across worker threads.
- method _RateLimiter.__init__(self, rate: float) (L391): Compute the per-probe interval for the given probes-per-second rate.
- method _RateLimiter.acquire(self, cancel: threading.Event) (L397): Wait for the next slot; return False if cancelled while waiting.
- class NetworkServiceScanner (L406): Scan explicit, authorized private IPv4 hosts with bounded resources.
- method NetworkServiceScanner.__init__(self, timeout: float=0.6, workers: int=32, rate_limit: float=160.0) (L409): Clamp socket timeout, worker count, and rate limit into safe bounds.
- method NetworkServiceScanner.scan(self, hosts: Iterable[str], allowed_networks: Iterable[str | ipaddress.IPv4Network], profile: ScanProfile, progress: ProgressFn | None=None, cancel_event: threading.Event | None=None, custom_ports: Iterable[int] | None=None) (L420): Return observations for authorized hosts and optional extra ports.
- method NetworkServiceScanner._progress(progress: ProgressFn | None, message: str) (L464): Invoke the progress callback, swallowing callback exceptions.
- method NetworkServiceScanner._jobs(addresses: Iterable[ipaddress.IPv4Address], ports: Iterable[int]) (L475): Yield (ip, port) jobs for every address/port combination.
- method NetworkServiceScanner._scan_tcp(self, addresses: list[ipaddress.IPv4Address], profile: ScanProfile, ports: Iterable[int], limiter: _RateLimiter, cancel: threading.Event, observations: list[ServiceObservation], progress: ProgressFn | None) (L486): Probe all (address, port) TCP jobs on a bounded thread pool.
- method NetworkServiceScanner._probe_tcp(self, ip: str, port: int, profile: ScanProfile, limiter: _RateLimiter, cancel: threading.Event) (L533): Rate-limited TCP connect plus passive banner read for one port.
- method NetworkServiceScanner._connect(self, observation: ServiceObservation) (L583): Open a TCP socket to the observed endpoint with the scan timeout.
- method NetworkServiceScanner._identify(self, observation: ServiceObservation, profile: ScanProfile, cancel: threading.Event) (L592): Deepen identification via TLS, HTTP, MQTT, or Redis probes by port.
- method NetworkServiceScanner._probe_tls(self, observation: ServiceObservation) (L617): TLS handshake (cert unverified) recording version, cipher, and cert hash.
- method NetworkServiceScanner._probe_http(self, observation: ServiceObservation, path: str) (L641): Bounded HEAD/GET request to fingerprint HTTP servers (Docker, ES).
- method NetworkServiceScanner._probe_mqtt(self, observation: ServiceObservation) (L707): Credential-free MQTT CONNECT; flags brokers that accept it (CONNACK 0).
- method NetworkServiceScanner._probe_redis(self, observation: ServiceObservation) (L731): Redis PING probe detecting unauthenticated access (+PONG vs NOAUTH).
- method NetworkServiceScanner._scan_udp(self, addresses: Iterable[ipaddress.IPv4Address], profile: ScanProfile, limiter: _RateLimiter, cancel: threading.Event, observations: list[ServiceObservation]) (L753): Send bounded UDP discovery probes (plus SNMP for advanced/deep).
- method NetworkServiceScanner._probe_udp(self, ip: str, port: int, name: str, payload: bytes) (L775): One UDP probe requiring a unicast reply from the same scoped host.
- func validate_private_target(target: str) (L816): Validate a private IPv4 address against standard LAN ranges.
- func observation_json(observation: ServiceObservation) (L824): Stable compact JSON, useful for inventory snapshots and tests.

## src/cortex_unified/system_tools/network_stack_optimizer.py — Cortex Cleaner — Enterprise Network Stack & DNS Optimizer.
- class TcpGlobalSettings (L17): Tcp Global Settings data container.
- class NetworkResetReport (L28): Network Reset Report data container.
- method NetworkResetReport.__post_init__(self) (L36): __post_init__.
- class NetworkStackOptimizer (L44): Production Windows network stack diagnostic and optimization engine.
- method NetworkStackOptimizer.flush_dns(cls) (L48): Flush the Windows DNS Resolver cache (ipconfig /flushdns).
- method NetworkStackOptimizer.clear_arp_cache(cls) (L62): Purge ARP cache tables (netsh interface ip delete arpcache).
- method NetworkStackOptimizer.reset_winsock(cls) (L76): Reset the Winsock catalog back to default configuration.
- method NetworkStackOptimizer.reset_tcp_ip_stack(cls) (L90): Reset the TCP/IP stack configuration.
- method NetworkStackOptimizer.get_tcp_settings(cls) (L104): Query active Windows TCP global parameters.
- method NetworkStackOptimizer.set_tcp_autotuning(cls, level: str='normal') (L132): Configure TCP Window Auto-Tuning (disabled, highlyrestricted, restricted, normal, experimental).
- method NetworkStackOptimizer.set_ecn_capability(cls, state: str='enabled') (L150): Configure Explicit Congestion Notification (enabled / disabled).
- method NetworkStackOptimizer.execute_complete_network_repair(cls) (L164): Perform a complete flush and reset of DNS, ARP, Winsock, and TCP/IP.

## src/cortex_unified/system_tools/network_tools.py — Network diagnostic utilities: ping, traceroute, DNS, port & IP checks.
- class PingResult (L47): Ping Result data container.
- method PingResult.to_dict(self) (L59): To dict.
- class Hop (L70): Hop data container.
- method Hop.to_dict(self) (L76): To dict.
- class NetworkTools (L83): Stateless collection of network diagnostics.
- method NetworkTools.ping(self, host: str, count: int=4, timeout_s: int=4, cancel_event: threading.Event | None=None) (L88): Ping.
- method NetworkTools._parse_ping(host: str, out: str) (L114): _parse_ping.
- method NetworkTools.traceroute(self, host: str, max_hops: int=30) (L147): Traceroute.
- method NetworkTools._parse_traceroute(out: str) (L161): _parse_traceroute.
- method NetworkTools.dns_lookup(host: str) (L183): Dns lookup.
- method NetworkTools.reverse_dns(ip: str) (L195): Reverse dns.
- method NetworkTools.check_port(host: str, port: int, timeout: float=1.0) (L206): True if a TCP connection to host:port succeeds (reachability).
- method NetworkTools.scan_common_ports(self, host: str, timeout: float=0.6) (L214): Check the COMMON_PORTS on *host* (self-audit when host is this PC).
- method NetworkTools.ip_info(address: str) (L227): Classify an IP entirely offline - no external lookups, no guesses.
- method NetworkTools._category(ip) (L249): _category.
- method NetworkTools._run(self, args: list[str], timeout: int=30, cancel_event: threading.Event | None=None) (L269): _run.

## src/cortex_unified/system_tools/network_traffic.py — Live network throughput monitor - system-wide and per-interface.
- class NicSample (L25): Counters and derived rates (bytes/sec) for one network interface.
- method NicSample.to_dict(self) (L34): To dict.
- class TrafficSample (L46): System-wide rates plus per-NIC breakdown, sorted by total activity.
- method TrafficSample.to_dict(self) (L57): To dict.
- class TrafficMonitor (L70): Stateful throughput sampler. Reuse ONE instance for correct rates.
- method TrafficMonitor.instance(cls) (L81): Instance.
- method TrafficMonitor.__init__(self) (L89): Initialize Traffic Monitor.
- method TrafficMonitor.sample(self) (L97): Read psutil I/O counters once and derive rates from the previous sample.

## src/cortex_unified/system_tools/nmap_adapter.py — Optional Nmap integration, bounded to explicitly authorized private LANs.
- class NmapError(RuntimeError) (L40): Base exception for adapter failures.
- class NmapUnavailableError(NmapError) (L44): Raised when the optional Nmap executable cannot be found.
- class NmapAuthorizationError(NmapError) (L48): Raised when any requested target is not explicitly authorized.
- class NmapPrivilegeError(NmapError) (L52): Raised when an expert mode is requested without Windows elevation.
- class NmapExecutionError(NmapError) (L56): Raised when Nmap exits unsuccessfully.
- class NmapOutputError(NmapError) (L60): Raised when Nmap XML is malformed, unsafe, or exceeds a bound.
- class NmapStatus (L65): Side-effect-free optional executable status.
- func _is_windows_admin() (L73): Return true only when Windows confirms this process is elevated.
- func _local_name(tag: str) (L83): _local_name.
- func _children(element: ET.Element, name: str) (L90): _children.
- func _descendants(element: ET.Element, name: str) (L97): _descendants.
- func _bounded_root(payload: bytes | str) (L104): _bounded_root.
- func _normalize_targets(targets: Iterable[str], allowed_networks: Iterable[str | ipaddress.IPv4Network]) (L138): _normalize_targets.
- func _normalize_ports(ports: Iterable[int]) (L169): _normalize_ports.
- func _normalize_modes(modes: Iterable[str] | str | None) (L192): _normalize_modes.
- func parse_nmap_xml(payload: bytes | str, allowed_networks: Iterable[str | ipaddress.IPv4Network]) (L219): Parse bounded Nmap XML into deterministic service observations.
- class NmapAdapter (L324): Discover and invoke optional Nmap without shell or script support.
- method NmapAdapter.__init__(self, executable: str='nmap') (L327): Initialize Nmap Adapter.
- method NmapAdapter._executable(self) (L331): _executable.
- method NmapAdapter.available(self) (L338): Available.
- method NmapAdapter.status(self) (L342): Status.
- method NmapAdapter.build_arguments(self, targets: Iterable[str], allowed_networks: Iterable[str | ipaddress.IPv4Network], ports: Iterable[int], modes: Iterable[str] | str | None=None) (L352): Build the nmap argv for one scan; no shell interpolation involved.
- method NmapAdapter.scan(self, targets: Iterable[str], allowed_networks: Iterable[str | ipaddress.IPv4Network], ports: Iterable[int], modes: Iterable[str] | str | None=None, *, timeout: float=120.0, cancel_event: threading.Event | None=None) (L388): Run one bounded scan and return parsed observations.
- func nmap_status(executable: str='nmap') (L428): Return side-effect-free Nmap availability information.
- func is_nmap_available(executable: str='nmap') (L433): Return whether the optional executable can be resolved.
- func scan_nmap(targets: Iterable[str], allowed_networks: Iterable[str | ipaddress.IPv4Network], ports: Iterable[int], modes: Iterable[str] | str | None=None, *, timeout: float=120.0, cancel_event: threading.Event | None=None, executable: str='nmap') (L438): Explicit function API for a bounded optional Nmap scan.

## src/cortex_unified/system_tools/notification_cleaner.py — Cortex Cleaner — Windows Action Center & Push Notification Database Cleaner.
- class NotificationDatabaseStatus (L20): Notification Database Status data container.
- class NotificationCleanResult (L30): Notification Clean Result data container.
- method NotificationCleanResult.__post_init__(self) (L37): __post_init__.
- class NotificationCleaner (L45): Production Windows Notification database (wpndatabase.db) sanitizer.
- method NotificationCleaner.get_status(cls) (L49): Query notification database paths and sizes.
- method NotificationCleaner.clean_notification_database(cls) (L72): Stop WpnService, purge notification database files, and restart service.

## src/cortex_unified/system_tools/oui.py — MAC address identity: IEEE-backed vendor lookup and privacy detection.
- func normalize(mac: str) (L62): Return *mac* lower-cased and colon-separated, or ``""`` if unusable.
- func _first_octet(mac: str) (L73): _first_octet.
- func is_randomized(mac: str) (L88): True when *mac* is a locally-administered (typically privacy) address.
- func is_multicast(mac: str) (L101): True for a multicast/broadcast MAC (not a real device address).
- func lookup(mac: str) (L109): Return the registered organisation for *mac*, or ``""`` if unknown.
- func shorten(vendor: str) (L141): Trim corporate boilerplate for display, keeping the recognisable name.
- func describe_vendor(mac: str) (L163): Human-facing vendor text that explains an absent vendor honestly.
- func cache_dir() (L179): Directory holding the downloaded IEEE registry.
- func cached_registry_path() (L184): Where a downloaded IEEE registry is kept between runs.
- func load_ieee_registry(path: str | os.PathLike[str]) (L189): Merge an IEEE registry CSV into the lookup tables.
- func load_cached_registry() (L229): Load the previously downloaded registry, if present. Never raises.
- func ensure_registry_loaded() (L237): Load the cached IEEE registry once, on first use.
- func has_full_registry() (L251): True when a real IEEE registry is loaded (not just the LA conventions).
- func registry_age_days() (L257): Age of the cached registry in days, or ``None`` when absent.
- func registry_status() (L266): Describe the vendor database for display in the UI.
- func refresh_from_ieee(timeout: int=60, cancel_event=None) (L287): Download the official IEEE registries and cache them locally.
- func prefix_count() (L352): Number of known assignment prefixes (useful for diagnostics/tests).

## src/cortex_unified/system_tools/pagefile_optimizer.py — Cortex Cleaner — Windows Pagefile & Virtual Memory Optimizer.
- class MEMORYSTATUSEX(ctypes.Structure) (L27): M E M O R Y S T A T U S E X.
- class PagefileConfig (L43): Pagefile Config data container.
- class VirtualMemoryStatus (L53): Virtual Memory Status data container.
- class PagefileOptimizer (L66): Production Windows Virtual Memory and Paging File management engine.
- method PagefileOptimizer.get_memory_metrics(cls) (L72): Query physical and pagefile memory sizes via GlobalMemoryStatusEx.
- method PagefileOptimizer.get_pagefile_config(cls) (L92): Read active pagefile registry configuration.
- method PagefileOptimizer.get_status(cls) (L148): Analyze virtual memory and compute hardware-tailored recommendations.
- method PagefileOptimizer.set_custom_pagefile(cls, drive_letter: str, initial_mb: int, maximum_mb: int) (L189): Configure custom min/max pagefile size in Windows registry.
- method PagefileOptimizer.set_automatic_pagefile(cls) (L210): Revert paging file to Windows system-managed automatic mode.

## src/cortex_unified/system_tools/performance_tuner.py — Windows power-plan tuner - safe, reversible performance control.
- class PowerPlan (L34): One Windows power scheme as reported by ``powercfg /list``.
- method PowerPlan.to_dict(self) (L41): To dict.
- class PerformanceTuner (L46): List and switch Windows power plans via powercfg.
- method PerformanceTuner.is_supported() (L50): powercfg-based control only exists on Windows.
- method PerformanceTuner.list_plans(self) (L54): Return available schemes; empty off-Windows or if powercfg fails.
- method PerformanceTuner._parse(out: str | None) (L61): _parse.
- method PerformanceTuner.active_plan(self) (L75): Return the scheme powercfg marks active, or ``None`` if unknown.
- method PerformanceTuner.set_active(self, guid: str) (L82): Switch the active power plan. Reversible; returns (ok, message).
- method PerformanceTuner._run(self, args: list[str], want_returncode: bool=False) (L97): _run.

## src/cortex_unified/system_tools/power_plan_optimizer.py — Cortex Cleaner — Windows Power Scheme & CPU Throttle Optimizer.
- class PowerScheme (L22): Power Scheme data container.
- class PowerPlanStatus (L31): Power Plan Status data container.
- class PowerPlanOptimizer (L40): Production Windows Power Scheme and CPU performance optimization engine.
- method PowerPlanOptimizer.get_status(cls) (L46): Query all installed power schemes and active configuration.
- method PowerPlanOptimizer.set_active_scheme(cls, scheme_guid: str) (L97): Activate the specified power plan GUID.
- method PowerPlanOptimizer.unlock_ultimate_performance_plan(cls) (L111): Duplicate and unlock the hidden Ultimate Performance power plan.
- method PowerPlanOptimizer.set_reduced_hibernation(cls) (L133): Reduce hiberfil.sys size to 40% of RAM (enables Fast Startup without full RAM snapshot).
- method PowerPlanOptimizer.disable_hibernation(cls) (L147): Disable hibernation entirely and delete hiberfil.sys to reclaim gigabytes of disk space.

## src/cortex_unified/system_tools/prefetch_analyzer.py — Cortex Cleaner — Windows Prefetch & SysMain (SuperFetch) Trace Analyzer.
- class PrefetchEntry (L24): Prefetch Entry data container.
- class PrefetchStatus (L36): Prefetch Status data container.
- class PrefetchCleanResult (L46): Prefetch Clean Result data container.
- method PrefetchCleanResult.__post_init__(self) (L52): __post_init__.
- class PrefetchAnalyzer (L60): Production Windows Prefetch and SuperFetch diagnostic engine.
- method PrefetchAnalyzer.get_status(cls) (L64): Query Prefetch directory metrics and SysMain service status.
- method PrefetchAnalyzer.scan_prefetch_files(cls) (L115): Scan and parse all .pf files in the Windows Prefetch directory.
- method PrefetchAnalyzer.clean_prefetch(cls, file_paths: Optional[List[str]]=None) (L156): Purge selected or all prefetch files.

## src/cortex_unified/system_tools/privacy_blocker.py — Privacy & Telemetry Blocker — 300+ settings, IFEO persistence, profiles.
- class TweakDef (L92): Single privacy tweak definition.
- method TweakDef.applies_to_current_os(self) (L129): Applies to current os.
- class PrivacyBlocker (L459): Declarative privacy tweak engine with profiles and persistence.
- method PrivacyBlocker.__init__(self, tweaks: Optional[List[TweakDef]]=None, create_restore_point: bool=True, progress_callback: Optional[Callable[[str], None]]=None, cancel_event: Optional[threading.Event]=None, dry_run: bool=False) (L462): Initialize Privacy Blocker.
- method PrivacyBlocker._reg_set(self, path: str, value: str, data: Any, dtype: int) (L482): _reg_set.
- method PrivacyBlocker._reg_get(self, path: str, value: str) (L499): _reg_get.
- method PrivacyBlocker._reg_backup(self, path: str) (L512): Export registry key to .reg file.
- method PrivacyBlocker._svc_set_start(self, name: str, start_type: int) (L526): _svc_set_start.
- method PrivacyBlocker._svc_get_start(self, name: str) (L542): _svc_get_start.
- method PrivacyBlocker._task_set_enabled(self, path: str, enabled: bool) (L557): _task_set_enabled.
- method PrivacyBlocker._fw_add_block(self, name: str, direction: str, program: str) (L571): _fw_add_block.
- method PrivacyBlocker._ifeo_set(self, target: str, debugger: str) (L585): _ifeo_set.
- method PrivacyBlocker._ifeo_remove(self, target: str) (L595): _ifeo_remove.
- method PrivacyBlocker.apply(self, tweak_ids: List[str]) (L611): Apply tweaks by ID list.
- method PrivacyBlocker.remove(self, tweak_ids: List[str]) (L651): Remove/revert tweaks by ID list.
- method PrivacyBlocker.status(self, tweak_ids: List[str]) (L694): Check current status of tweaks.
- method PrivacyBlocker.apply_profile(self, profile_name: str) (L722): Apply all tweaks tagged with a profile.
- method PrivacyBlocker.audit(self) (L728): Full privacy audit — returns JSON-serializable report.
- method PrivacyBlocker.list_profiles(self) (L755): Return profile -> tweak IDs mapping.
- method PrivacyBlocker.export_config(self, path: str) (L763): Export current applied tweaks as JSON config.
- method PrivacyBlocker.import_config(self, path: str) (L775): Import and apply tweaks from JSON config.
- method PrivacyBlocker.enable_auto_enforcement(self, interval_minutes: int=60) (L780): Register scheduled task for periodic re-application (Premium feature).

## src/cortex_unified/system_tools/process_analyzer.py — Process and service enumeration via platform CLI tools.
- class ProcessAnalyzer (L16): Enumerate running processes/services and flag high-resource consumers.
- method ProcessAnalyzer.__init__(self, config: Config=None) (L19): Use *config* or a default Config; the OS decides which backends run.
- method ProcessAnalyzer.list_processes(self) (L29): Populate ``processes`` from the platform's process listing.
- method ProcessAnalyzer._list_windows_processes(self) (L46): _list_windows_processes.
- method ProcessAnalyzer._list_macos_processes(self) (L74): _list_macos_processes.
- method ProcessAnalyzer._list_linux_processes(self) (L104): _list_linux_processes.
- method ProcessAnalyzer.list_services(self) (L134): Populate ``services`` from the platform's service listing.
- method ProcessAnalyzer._list_windows_services(self) (L151): List Windows services using sc query.
- method ProcessAnalyzer._list_macos_services(self) (L182): _list_macos_services.
- method ProcessAnalyzer._list_linux_services(self) (L204): List Linux services using systemctl, falling back to ``service``.
- method ProcessAnalyzer.find_high_resource_processes(self, cpu_threshold: float=50.0, mem_threshold: float=50.0) (L238): Flag processes at or above the CPU/memory percentage thresholds.
- method ProcessAnalyzer.get_stats(self) (L277): Snapshot counts for UI display.
- method ProcessAnalyzer.filter_processes_by_name(self, name_pattern: str) (L291): Case-insensitive substring match on process name.
- method ProcessAnalyzer.filter_services_by_state(self, state: str) (L299): Case-insensitive substring match on service state.

## src/cortex_unified/system_tools/process_meta.py — Human-friendly process identity: what a running program actually is.
- func known_description(name: str) (L91): Return the curated description for a process *name*, or ''.
- func file_description(exe_path: str) (L96): Read the vendor's embedded FileDescription for *exe_path* (cached).
- func describe(name: str, exe_path: str='') (L118): Best available human description for a process.

## src/cortex_unified/system_tools/process_token_auditor.py — Cortex Cleaner — Process Security Token & Integrity Forensics.
- class ProcessTokenInfo (L38): Process Token Info data container.
- class ProcessTokenAuditReport (L51): Process Token Audit Report data container.
- class ProcessTokenAuditor (L63): Enterprise Process Security Token & Privilege Auditor.
- method ProcessTokenAuditor.__init__(self) (L66): Initialize Process Token Auditor.
- method ProcessTokenAuditor.audit(self, max_processes: int=150) (L70): Audit active running processes and decode their security tokens.
- method ProcessTokenAuditor._inspect_token(self, pid: int) (L132): Inspect a single process token via Win32 APIs.
- method ProcessTokenAuditor._get_integrity_level(self, h_token) (L153): Query TokenIntegrityLevel.
- method ProcessTokenAuditor._get_elevation_type(self, h_token) (L200): Query TokenElevationType.
- method ProcessTokenAuditor._get_privileges(self, h_token) (L221): Query enabled privileges on the token.
- class LUID(ctypes.Structure) (L250): L U I D.

## src/cortex_unified/system_tools/registry_cleaner.py — Orphaned Windows registry entry detection with export-before-delete safety.
- class RegistryCleaner (L21): Find and remove registry entries that reference files no longer on disk.
- method RegistryCleaner.__init__(self, config: Config=None) (L24): Initialize Registry Cleaner.
- method RegistryCleaner.scan(self) (L40): Alias used by SmartScanner.
- method RegistryCleaner.scan_orphaned_entries(self) (L44): Run all category scans and return the accumulated orphans.
- method RegistryCleaner._scan_uninstall_entries(self, hive) (L66): _scan_uninstall_entries.
- method RegistryCleaner._check_uninstall_entry(self, hive, hive_name, full_path, subkey_name) (L99): _check_uninstall_entry.
- method RegistryCleaner._scan_startup_entries(self) (L140): Check Run/RunOnce keys for entries that reference missing executables.
- method RegistryCleaner._scan_file_associations(self) (L180): Check HKCR (via HKLM\Software\Classes) for associations pointing to missing executables.
- method RegistryCleaner._scan_shared_dlls(self) (L221): Check SharedDLLs registry for entries with reference count = 0.
- method RegistryCleaner.backup_registry(self, backup_dir: str=None) (L255): Export the HKCU Uninstall key to a .reg file for safety.
- method RegistryCleaner.backup_entry(self, entry: Dict, backup_dir: Optional[str]=None) (L286): Export a specific registry entry to a .reg file before deletion for instant rollback.
- method RegistryCleaner.remove_orphaned_entry(self, entry: Dict, auto_backup: bool=True) (L321): Delete an orphaned registry entry with auto-backup for rollback.
- method RegistryCleaner.get_stats(self) (L368): Get stats.
- method RegistryCleaner.filter_by_type(self, entry_type: str) (L376): Filter by type.
- method RegistryCleaner._reg_val(winreg, key, name, default='') (L385): _reg_val.
- method RegistryCleaner._extract_exe_path(raw: str) (L395): Extract a file path from a registry value string like:

## src/cortex_unified/system_tools/restart_manager_unlocker.py — Windows Native Restart Manager File Unlocker & Process Lock Auditor.
- class RM_UNIQUE_PROCESS(ctypes.Structure) (L41): R M_ U N I Q U E_ P R O C E S S.
- class RM_PROCESS_INFO(ctypes.Structure) (L49): R M_ P R O C E S S_ I N F O.
- class LockingProcessInfo (L63): Identity and telemetry of a process holding an exclusive file lock.
- method LockingProcessInfo.to_dict(self) (L70): To dict.
- class FileLockReport (L81): Forensic report detailing whether a file is locked and which processes lock it.
- method FileLockReport.to_dict(self) (L89): To dict.
- class UnlockResult (L101): Outcome of an unlock or process termination attempt.
- method UnlockResult.to_dict(self) (L108): To dict.
- class RestartManagerUnlocker (L118): Native Windows Restart Manager file lock analyzer and process unlocker.
- method RestartManagerUnlocker.__init__(self) (L121): Initialize Restart Manager Unlocker.
- method RestartManagerUnlocker.inspect_locks(self, file_path: str) (L131): Query which processes currently lock the given file using Windows Restart Manager.
- method RestartManagerUnlocker._get_locking_processes_native(self, abs_path: str) (L155): Query rstrtmgr.dll for processes locking abs_path.
- method RestartManagerUnlocker._get_locking_processes_psutil(self, abs_path: str) (L238): Fallback process inspection via psutil open file handle auditing.
- method RestartManagerUnlocker.unlock_file(self, file_path: str, force_terminate: bool=False) (L261): Release locks on a file by gracefully or forcefully terminating the locking processes.

## src/cortex_unified/system_tools/restore_point.py — Windows System Restore point management - the trust/safety foundation.
- class RestoreStatus(str, enum.Enum) (L47): Outcome of a restore-point create attempt - each is honest & distinct.
- class RestorePointResult (L59): Result of a create attempt.
- method RestorePointResult.created(self) (L66): Created.
- method RestorePointResult.ok_to_proceed(self) (L71): True if it's reasonable to continue a risky op after this attempt.
- method RestorePointResult.to_dict(self) (L79): To dict.
- class RestorePointManager (L84): Create and list Windows System Restore points, honestly.
- method RestorePointManager.__init__(self) (L87): Initialize Restore Point Manager.
- method RestorePointManager.is_supported() (L94): Is supported.
- method RestorePointManager.is_elevated() (L99): True if running as Administrator (required to create a point).
- method RestorePointManager.create(self, description: str='Cortex Cleaner', restore_point_type: str='MODIFY_SETTINGS') (L111): Attempt to create a restore point and report the verified outcome.
- method RestorePointManager._parse_create_output(out: str | None) (L156): _parse_create_output.
- method RestorePointManager.list_points(self, limit: int=50) (L186): Return existing restore points (most recent first). Empty on failure.
- method RestorePointManager._parse_wmi_time(value: Any) (L220): Best-effort parse of a WMI CreationTime into an ISO-ish string.
- method RestorePointManager._run_ps(self, script: str, timeout: int) (L230): _run_ps.

## src/cortex_unified/system_tools/s3_fifo.py — S3-FIFO cache eviction — "FIFO queues are all you need" (SOSP'23).
- class _Entry (L73): _Entry.
- class S3FIFOStats (L83): S3 F I F O Stats data container.
- method S3FIFOStats.to_dict(self) (L93): To dict.
- class S3FIFO (L111): S3-FIFO cache (SOSP'23) – three static FIFO queues.
- method S3FIFO.__init__(self, capacity: int=256, small_ratio: float=0.1) (L122): Initialize S3 F I F O.
- method S3FIFO._ghost_contains(self, key: Hashable) (L150): _ghost_contains.
- method S3FIFO._ghost_add(self, key: Hashable) (L156): _ghost_add.
- method S3FIFO._ghost_remove(self, key: Hashable) (L172): _ghost_remove.
- method S3FIFO._evict_small_if_needed(self) (L183): _evict_small_if_needed.
- method S3FIFO._evict_main_if_needed(self) (L203): _evict_main_if_needed.
- method S3FIFO.get(self, key: Hashable) (L222): Return value or ``None`` on miss; bumps frequency on hit.
- method S3FIFO.put(self, key: Hashable, value: Any) (L235): Insert or update ``key``.
- method S3FIFO.delete(self, key: Hashable) (L265): Remove ``key`` if present; returns True if removed.
- method S3FIFO.contains(self, key: Hashable) (L281): Contains.
- method S3FIFO.__contains__(self, key: object) (L292): __contains__.
- method S3FIFO.__len__(self) (L298): __len__.
- method S3FIFO.clear(self) (L305): Clear.
- method S3FIFO.stats(self) (L315): Stats.
- method S3FIFO.keys(self) (L337): Keys.
- method S3FIFO.snapshot(self) (L345): Return a JSON-serialisable snapshot of queue states (ordered).

## src/cortex_unified/system_tools/sandbox_cleaner.py — Cortex Cleaner — Windows Sandbox & Virtual Environment Artifact Purger.
- class VirtualArtifact (L23): Virtual Artifact data container.
- method VirtualArtifact.size_mb(self) (L33): Size mb.
- method VirtualArtifact.size_gb(self) (L38): Size gb.
- class SandboxCleanReport (L44): Sandbox Clean Report data container.
- class SandboxCleaner (L53): Enterprise Virtual Environment & Sandbox Artifact Purger.
- method SandboxCleaner.__init__(self) (L56): Initialize Sandbox Cleaner.
- method SandboxCleaner.scan(self) (L60): Scan system for virtual environment leftovers and sandbox files.
- method SandboxCleaner.clean(self, target_paths: list[str]) (L145): Safely clean selected virtual artifacts.

## src/cortex_unified/system_tools/search_index_optimizer.py — Cortex Cleaner — Windows Search Index Database (Windows.edb) Optimizer.
- class SearchIndexStatus (L22): Search Index Status data container.
- class SearchIndexOperationResult (L33): Search Index Operation Result data container.
- method SearchIndexOperationResult.__post_init__(self) (L41): __post_init__.
- class SearchIndexOptimizer (L49): Production Windows Search Index database diagnostic and compaction toolkit.
- method SearchIndexOptimizer.get_status(cls) (L53): Query Windows Search Index database metrics and service status.
- method SearchIndexOptimizer.compact_database(cls) (L100): Stop WSearch service, perform offline ESENT compaction (esentutl /d), and restart service.
- method SearchIndexOptimizer.rebuild_index(cls) (L157): Trigger an official Windows Search index catalog rebuild.

## src/cortex_unified/system_tools/secrets_scanner.py — Filesystem secrets scanner with live credential validation.
- class DetectionPattern (L120): Detection Pattern data container.
- class Finding (L132): Finding data container.
- method Finding.to_dict(self) (L150): To dict.
- method Finding.severity_rank(self) (L155): Severity rank.
- method Finding.fingerprint(self) (L160): Fingerprint.
- class ScanStats (L167): Scan Stats data container.
- method ScanStats.critical(self) (L185): Critical.
- method ScanStats.high(self) (L189): High.
- method ScanStats.medium(self) (L193): Medium.
- method ScanStats.low(self) (L197): Low.
- method ScanStats.unique_files(self) (L201): Unique files.
- method ScanStats.live_credentials(self) (L205): Live credentials.
- method ScanStats.to_dict(self) (L209): To dict.
- class VerificationResult (L221): Verification Result data container.
- method VerificationResult.status_emoji(self) (L232): Status emoji.
- func _p(pattern: str, flags: int=0) (L240): _p.
- func _shannon_entropy(data: bytes) (L892): _shannon_entropy.
- func _check_high_entropy(line: bytes, file_path: str) (L907): Detect high-entropy strings that look like secrets but don't match known patterns.
- func compute_confidence(file_path: str, match_preview: str, entropy: float, category: str, line_raw: str='') (L929): Compute confidence.
- func _luhn_valid(s: str) (L951): _luhn_valid.
- func _redact(match: bytes) (L963): _redact.
- func scan_file_bytes(data: bytes, file_path: str, patterns: List[DetectionPattern]) (L972): Scan file bytes.
- func scan_single_file(file_path: str, patterns: List[DetectionPattern]) (L1005): Scan single file.
- func walk_files(directory: str, ignores: List[str]) (L1034): Walk directory, returning (file_paths, skipped_count).
- func compute_risk_score(findings: List[Finding]) (L1063): Compute risk score.
- func run_scan(directory: str, ignores: List[str]=None, max_workers: int=8, severity_filter: List[str]=None, quiet: bool=False) (L1072): Run scan.
- func _scan_archive_member(data: bytes, virtual_path: str) (L1123): _scan_archive_member.
- func scan_zip(archive_path: str) (L1131): Scan zip.
- func scan_tar(archive_path: str) (L1154): Scan tar.
- func scan_archives(directory: str, quiet: bool=False) (L1184): Scan archives.
- func scan_git_history(directory: str, max_commits: int=500, quiet: bool=False) (L1202): Walk git commit history and scan each diff for secrets.
- func _http(url: str, headers: dict, data: bytes=None, method: str='GET', timeout: int=8) (L1250): _http.
- func _vr(finding_id: str, name: str, live: Optional[bool], identity: Optional[str], blast: str, err: Optional[str]=None) (L1267): _vr.
- func verify_aws(key_id: str, secret: str) (L1273): Verify aws.
- func verify_aws.sign(key, msg) (L1289): Sign.
- func verify_github(token: str) (L1313): Verify github.
- func verify_stripe(key: str) (L1325): Verify stripe.
- func verify_slack(token: str) (L1340): Verify slack.
- func verify_npm(token: str) (L1351): Verify npm.
- func verify_openai(key: str) (L1363): Verify openai.
- func verify_all_findings(findings: List[Finding], quiet: bool=False) (L1386): Verify all findings.
- func _truncate_secret(value: str) (L1412): _truncate_secret.
- func save_baseline(findings: List[Finding], directory: str) (L1422): Save baseline.
- func load_baseline(directory: str) (L1434): Load baseline.
- func compute_delta(findings: List[Finding], baseline: Dict) (L1442): Compute delta.
- func _fp_path(directory: str) (L1451): _fp_path.
- func load_fp_db(directory: str) (L1457): Load fp db.
- func save_fp_db(db: Dict, directory: str) (L1465): Save fp db.
- func add_fp(fingerprint: str, directory: str, reason: str='') (L1470): Add fp.
- func apply_fp_filter(findings: List[Finding], directory: str) (L1477): Apply fp filter.
- func save_to_history(stats: ScanStats, live_count: int=0) (L1491): Save to history.
- func load_history(limit: int=20) (L1506): Load history.
- func create_jira_ticket(finding: Finding, jira_url: str, jira_user: str, jira_token: str, project_key: str) (L1522): Create a Jira issue from a finding. Returns issue key or None.
- func create_github_issue(finding: Finding, github_token: str, repo: str) (L1558): Create a GitHub issue from a finding. Returns issue URL or None.
- func export_json(stats: ScanStats, path: str) (L1591): Export json.
- func export_csv(stats: ScanStats, path: str) (L1596): Export csv.
- func export_sarif(stats: ScanStats, path: str) (L1609): Export sarif.
- func send_slack(stats: ScanStats, webhook_url: str) (L1639): Send slack.
- func generate_html_report(stats: ScanStats, output_path: str) (L1669): Generate html report.
- func print_terminal_report(stats: ScanStats) (L1977): Print terminal report.
- class DashboardHandler(http.server.BaseHTTPRequestHandler) (L2145): Dashboard Handler.
- method DashboardHandler.log_message(self, format, *args) (L2147): Log message.
- method DashboardHandler.do_GET(self) (L2150): Do GET.
- func serve_dashboard(port: int=8080) (L2166): Serve dashboard.
- func cmd_scan(args) (L2178): Cmd scan.
- func cmd_baseline(args) (L2313): Cmd baseline.
- func cmd_fp(args) (L2341): Cmd fp.
- func cmd_verify(args) (L2363): Cmd verify.
- func cmd_serve(args) (L2383): Cmd serve.
- func cmd_patterns(args) (L2389): Cmd patterns.
- func build_parser() (L2408): Build parser.
- func main() (L2470): Main.

## src/cortex_unified/system_tools/secure_shredder.py — Secure File Shredder — DoD 5220.22-M, Gutmann, NIST 800-88, SSD TRIM.
- class StorageType(Enum) (L112): Storage Type enumeration.
- class ShredStandard(Enum) (L121): Software-executable sanitization standards.
- method ShredStandard.passes(self) (L158): Passes.
- method ShredStandard.name(self) (L239): Name.
- method ShredStandard.pass_count(self) (L244): Pass count.
- method ShredStandard.recommended_for(self, storage: StorageType) (L248): Recommended for.
- class ShredResult (L260): Shred Result data container.
- method ShredResult.to_dict(self) (L271): To dict.
- func _pattern_bytes(pattern: Any, size: int) (L283): Generate bytes for a pass pattern.
- func _verify_pattern(file_path: str, pattern: Any, size: int, sample_pct: float=0.1) (L299): Verify written pattern by reading back (full or sampled).
- func detect_storage_type(path: str) (L347): Detect storage type for a given path.
- class SecureShredder (L392): Multi-standard secure file shredder with verification.
- method SecureShredder.__init__(self, progress_callback: Optional[Callable[[str, int, int], None]]=None, cancel_event: Optional[threading.Event]=None, verify_passes: bool=True, sample_verification_pct: float=0.1, dry_run: bool=False) (L395): Initialize Secure Shredder.
- method SecureShredder._write_pass(self, f: BinaryIO, offset: int, size: int, pattern: Any) (L411): Write a single pass pattern at offset.
- method SecureShredder.shred_file(self, file_path: str, standard: Optional[ShredStandard]=None, auto_detect: bool=True) (L428): Shred a single file according to standard.
- method SecureShredder._shred_ssd_firmware(self, path: Path, standard: ShredStandard) (L505): Use firmware Secure Erase for SSD (requires admin).
- method SecureShredder.shred_files(self, file_paths: List[str], standard: Optional[ShredStandard]=None, auto_detect: bool=True) (L536): Shred multiple files.
- method SecureShredder.wipe_free_space(self, drive: str, standard: Optional[ShredStandard]=None) (L550): Wipe free space on a drive.
- method SecureShredder.get_smart_default(self, path: str) (L582): Get recommended standard for a path.

## src/cortex_unified/system_tools/service_manager.py — Cortex Cleaner — Windows Service Manager & Profile Optimizer.
- class ServiceInfo (L21): Service Info data container.
- class ServiceProfileResult (L72): Service Profile Result data container.
- class WindowsServiceManager (L81): Production Windows Service profiler and optimizer.
- method WindowsServiceManager.enumerate_services(cls) (L85): List all Windows services with status, startup type, and safety classification.
- method WindowsServiceManager.stop_service(cls, service_name: str) (L138): Stop a running Windows service.
- method WindowsServiceManager.set_startup_type(cls, service_name: str, startup_type: str) (L155): Set service startup type (Auto, Manual, Disabled).
- method WindowsServiceManager.apply_profile(cls, profile: str='Gaming') (L175): Apply a named service optimization profile.

## src/cortex_unified/system_tools/shader_cache_cleaner.py — GPU & DirectX Shader Cache Forensics & Cleanup Engine.
- class ShaderLocationInfo (L35): Metadata and size analysis for a specific shader cache target location.
- method ShaderLocationInfo.to_dict(self) (L46): To dict.
- class ShaderCacheReport (L61): Consolidated inventory of GPU shader caches across all hardware vendors.
- method ShaderCacheReport.to_dict(self) (L70): To dict.
- class ShaderCleanResult (L83): Outcome of a shader cache purge operation.
- method ShaderCleanResult.to_dict(self) (L91): To dict.
- class ShaderCacheCleaner (L102): Production GPU shader cache detection, forensics, and cleanup engine.
- method ShaderCacheCleaner.__init__(self) (L105): Initialize Shader Cache Cleaner.
- method ShaderCacheCleaner.get_known_locations(self) (L109): Resolve standard shader cache paths dynamically from current user profile.
- method ShaderCacheCleaner.scan(self, min_age_days: int=0) (L135): Scan all GPU shader cache locations and analyze disk consumption.
- method ShaderCacheCleaner.clean(self, min_age_days: int=0, dry_run: bool=False) (L179): Purge stale or orphaned shader cache files across all detected locations.

## src/cortex_unified/system_tools/shellbags_privacy_cleaner.py — Cortex Cleaner — Windows Shellbags & JumpLists Activity Forensics Purger.
- class ShellbagsTarget (L26): Shellbags Target data container.
- class ShellbagsCleanResult (L36): Shellbags Clean Result data container.
- method ShellbagsCleanResult.__post_init__(self) (L43): __post_init__.
- class ShellbagsPrivacyCleaner (L51): Production Windows Shellbags and JumpLists activity forensics sanitizer.
- method ShellbagsPrivacyCleaner._count_reg_keys(cls, subkey: str) (L64): Count subkeys and values in a registry key.
- method ShellbagsPrivacyCleaner._delete_reg_tree(cls, subkey: str) (L76): Recursively delete a registry key tree.
- method ShellbagsPrivacyCleaner.scan_shell_activity(cls) (L96): Scan system for all Shellbag and Explorer activity artifacts.
- method ShellbagsPrivacyCleaner.clean_shell_activity(cls, targets: Optional[List[ShellbagsTarget]]=None) (L154): Purge selected or all Explorer activity and Shellbag targets.

## src/cortex_unified/system_tools/sieve_cache.py — SIEVE Cache Eviction Algorithm.
- class SieveNode(Generic[K, V]) (L23): Internal doubly-linked list node for SIEVE cache.
- method SieveNode.__init__(self, key: K, value: V) (L27): Initialize Sieve Node.
- method SieveNode.__repr__(self) (L35): __repr__.
- class SieveCache(Generic[K, V]) (L42): Production thread-safe implementation of the NSDI 2024 SIEVE Cache Algorithm.
- method SieveCache.__init__(self, capacity: int) (L45): Initialize Sieve Cache.
- method SieveCache.get(self, key: K, default: Optional[V]=None) (L61): Lookup key in cache. On hit, flips `visited = True` without linked-list mutation.
- method SieveCache.contains(self, key: K) (L72): Check if key exists in cache without mutating hit counters or visited bit.
- method SieveCache.put(self, key: K, value: V) (L77): Insert or update a key-value pair. Evicts using SIEVE algorithm if full.
- method SieveCache._insert_head(self, node: SieveNode[K, V]) (L93): Insert node at head (most recent insertion point).
- method SieveCache._remove_node(self, node: SieveNode[K, V]) (L103): Remove node from doubly linked list and advance hand if pointing to it.
- method SieveCache._evict(self) (L121): Run SIEVE eviction loop. Returns (evicted_key, evicted_value) or None.
- method SieveCache.delete(self, key: K) (L136): Explicitly remove a key from cache.
- method SieveCache.clear(self) (L145): Purge all entries and reset hand.
- method SieveCache.size(self) (L154): Size.
- method SieveCache.hit_ratio(self) (L160): Hit ratio.
- method SieveCache.stats(self) (L166): Return operational cache statistics.
- method SieveCache.keys(self) (L179): Return snapshot of currently cached keys.

## src/cortex_unified/system_tools/slack_space_analyzer.py — Cortex Cleaner — NTFS Disk Cluster & Slack Space Forensics Analyzer.
- class DirectorySlackStat (L23): Directory Slack Stat data container.
- class VolumeSlackReport (L34): Volume Slack Report data container.
- class SlackSpaceAnalyzer (L46): Production NTFS cluster geometry and slack space forensics analyzer.
- method SlackSpaceAnalyzer.get_cluster_size(cls, drive_path: Optional[str]=None) (L50): Query physical volume cluster allocation size in bytes via Win32 GetDiskFreeSpaceW.
- method SlackSpaceAnalyzer.analyze_directory(cls, target_dir: str | Path, max_depth: int=3, progress_cb: Optional[Callable[[int, str], None]]=None, cancel_check: Optional[Callable[[], bool]]=None) (L78): Scan directory and calculate logical vs physical cluster slack space.

## src/cortex_unified/system_tools/smb_share_auditor.py — Cortex Cleaner — Network Share & SMB Exposure Auditor.
- class SmbShareInfo (L24): Smb Share Info data container.
- class SmbSecurityReport (L36): Smb Security Report data container.
- class SmbShareAuditor (L47): Enterprise Network Share & SMB Security Auditor.
- method SmbShareAuditor.__init__(self) (L50): Initialize Smb Share Auditor.
- method SmbShareAuditor.audit(self) (L54): Run comprehensive SMB and network share audit.
- method SmbShareAuditor._list_shares(self) (L86): List active shares via PowerShell Get-SmbShare or net share.
- method SmbShareAuditor._check_smbv1(self) (L162): Check if SMBv1 protocol is enabled on the server.
- method SmbShareAuditor._check_smb_signing(self) (L177): Check if SMB signing is required.

## src/cortex_unified/system_tools/srum_bam_cleaner.py — Windows BAM/DAM & SRUM Forensic Privacy Cleaner.
- class BamExecutionEntry (L32): Represents an execution record captured by BAM/DAM.
- method BamExecutionEntry.to_dict(self) (L41): To dict.
- class SrumDatabaseInfo (L53): Status of the Windows SRUM forensic database.
- method SrumDatabaseInfo.to_dict(self) (L62): To dict.
- class SrumBamReport (L74): Forensic report containing BAM/DAM execution traces and SRUM metrics.
- method SrumBamReport.to_dict(self) (L82): To dict.
- class SrumBamCleaner (L93): Forensic scanner and cleaner for Windows BAM/DAM and SRUM stores.
- method SrumBamCleaner._filetime_to_datetime(cls, ft_bytes: bytes) (L99): Convert an 8-byte Windows FILETIME structure to ISO timestamp and UNIX epoch.
- method SrumBamCleaner.query_srum(self) (L116): Inspect the presence, size, and status of Windows SRUM database.
- method SrumBamCleaner.scan(self) (L153): Scan BAM, DAM, and SRUM execution traces.
- method SrumBamCleaner.clean_bam_entries(self, entries: Optional[List[BamExecutionEntry]]=None) (L204): Sanitize specified or all BAM/DAM registry execution records.

## src/cortex_unified/system_tools/ssd_trim_optimizer.py — Solid-State Drive (SSD) NVMe TRIM & Flash Wear-Leveling Optimizer.
- class VolumeTrimStatus (L39): Storage volume status, media classification, and TRIM capability.
- method VolumeTrimStatus.to_dict(self) (L49): To dict.
- class TrimAuditReport (L63): Comprehensive inspection report of storage drives and filesystem TRIM readiness.
- method TrimAuditReport.to_dict(self) (L70): To dict.
- class TrimExecutionResult (L81): Outcome of an SSD NVMe block deallocation operation.
- method TrimExecutionResult.to_dict(self) (L89): To dict.
- class SsdTrimOptimizer (L100): Production SSD / NVMe TRIM auditing and block deallocation engine.
- method SsdTrimOptimizer.__init__(self) (L103): Initialize Ssd Trim Optimizer.
- method SsdTrimOptimizer.query_global_trim_enabled(self) (L107): Query NTFS and ReFS DisableDeleteNotify values via fsutil.
- method SsdTrimOptimizer.audit_volumes(self) (L143): Inspect all mounted logical drives, detect SSD media types, and evaluate TRIM status.
- method SsdTrimOptimizer.retrim_volume(self, drive_letter: str) (L215): Trigger an immediate, non-destructive flash block deallocation on the target volume.

## src/cortex_unified/system_tools/startup_impact_analyzer.py — Cortex Cleaner — Windows Startup Impact Analyzer & Delayed Launch Sequencer.
- class StartupAppItem (L27): Startup App Item data container.
- class StartupImpactReport (L41): Startup Impact Report data container.
- class StartupImpactAnalyzer (L51): Production Windows Startup Impact analyzer and optimizer.
- method StartupImpactAnalyzer._extract_exe_path(cls, command: str) (L63): _extract_exe_path.
- method StartupImpactAnalyzer._read_startup_approved_state(cls, hive, approved_key: str, item_name: str) (L78): Decode Windows StartupApproved 12-byte binary blob. Byte 0: 0x02=Enabled, 0x03=Disabled.
- method StartupImpactAnalyzer._calculate_impact(cls, file_size: int, exe_name: str) (L93): Calculate startup impact based on binary size and application profile.
- method StartupImpactAnalyzer.analyze_startup(cls) (L112): Enumerate and assess startup impact of all registered startup items.
- method StartupImpactAnalyzer.toggle_item_state(cls, item_name: str, enable: bool, is_user: bool=True) (L170): Toggle startup item enabled/disabled state via StartupApproved registry binary key.

## src/cortex_unified/system_tools/startup_manager.py — Startup item enumeration and disabling across platforms.
- class StartupManager (L16): Enumerate autostart entries; disable them on Windows.
- method StartupManager.__init__(self, config: Config=None) (L19): Use *config* or a default Config; the OS decides which backends run.
- method StartupManager.list_startup_items(self) (L27): Populate ``startup_items`` from every autostart location for this OS.
- method StartupManager._list_windows_startup_items(self) (L44): Collect registry Run/RunOnce values plus Startup-folder files.
- method StartupManager._read_registry_startup_items(self, hive, key_path) (L86): Append every value under one Run/RunOnce key.
- method StartupManager._read_startup_folder_items(self, folder_path: Path) (L109): Append each file in one Startup folder.
- method StartupManager._list_macos_startup_items(self) (L125): _list_macos_startup_items.
- method StartupManager._read_plist_items(self, folder_path: Path) (L144): Append each launchd plist in one folder (name only, no parsing).
- method StartupManager._list_linux_startup_items(self) (L163): _list_linux_startup_items.
- method StartupManager._read_desktop_items(self, folder_path: Path) (L179): Read startup items from Linux .desktop files.
- method StartupManager._registry_backup_path(self) (L198): JSON sidecar where disabled Run/RunOnce values are preserved.
- method StartupManager._load_registry_backup(self) (L202): _load_registry_backup.
- method StartupManager._save_registry_backup(self, backup: Dict[str, dict]) (L214): _save_registry_backup.
- method StartupManager.enable_startup_item(self, item_name: str) (L226): Re-enable a previously disabled startup item.
- method StartupManager.disable_startup_item(self, name: str, item_type: str) (L311): Disable a specific startup item.
- method StartupManager._disable_registry_item(self, name: str) (L329): Disable a registry-based startup item (values backed up first).
- func StartupManager._disable_registry_item.capture(hive_name, hive, key_path) (L338): Capture.
- func StartupManager._disable_registry_item.delete_value(hive, key_path, value_name) (L372): Delete value.
- method StartupManager._disable_startup_folder_item(self, name: str) (L395): Disable a file-based startup item.
- func StartupManager._disable_startup_folder_item.move_to_backup(item_path) (L399): Move to backup.
- method StartupManager.get_stats(self) (L431): Get statistics about startup items.
- method StartupManager.filter_by_type(self, item_type: str) (L444): Filter startup items by type.

## src/cortex_unified/system_tools/startup_optimizer.py — Startup Optimizer — stagger/delay engine with resource-aware gating.
- class AppType(enum.Enum) (L69): High-level classification for startup entries used by the UI filter.
- class StartupEntry (L79): Startup Entry data container.
- method StartupEntry.to_dict(self) (L95): To dict.
- func _enumerate_registry() (L117): _enumerate_registry.
- func _enumerate_startup_folders() (L157): _enumerate_startup_folders.
- func _enumerate_scheduled_tasks() (L183): _enumerate_scheduled_tasks.
- func _classify_entry(entry: StartupEntry) (L211): _classify_entry.
- func _config_path() (L237): _config_path.
- class StartupOptimizer (L250): Startup Optimizer.
- method StartupOptimizer.__init__(self, progress: Callable[[str], None] | None=None, cancel: threading.Event | None=None) (L252): Initialize Startup Optimizer.
- method StartupOptimizer.enumerate(self) (L258): Enumerate.
- method StartupOptimizer._load_delays(self) (L289): _load_delays.
- method StartupOptimizer._save_delays(self, delays: Dict[str, dict]) (L301): _save_delays.
- method StartupOptimizer.set_delay(self, entry_id: str, delay_seconds: int, conditions: Dict[str, object] | None=None) (L308): Set delay.
- method StartupOptimizer.remove_delay(self, entry_id: str) (L316): Remove delay.
- method StartupOptimizer.launch_delayed(self, entries: List[StartupEntry] | None=None) (L322): Launch delayed.
- method StartupOptimizer._jitter(self) (L387): _jitter.
- method StartupOptimizer.backup(self) (L394): Backup.
- method StartupOptimizer.restore(self, backup: Path) (L402): Restore.

## src/cortex_unified/system_tools/storage_growth_tracker.py — Cortex Cleaner — Storage Growth Tracker & Timeline Differ.
- class SnapshotSummary (L25): Snapshot Summary data container.
- method SnapshotSummary.formatted_time(self) (L36): Formatted time.
- method SnapshotSummary.total_gb(self) (L41): Total gb.
- class DirectoryDelta (L47): Directory Delta data container.
- method DirectoryDelta.growth_mb(self) (L56): Growth mb.
- method DirectoryDelta.growth_gb(self) (L61): Growth gb.
- class StorageGrowthDiffReport (L67): Storage Growth Diff Report data container.
- method StorageGrowthDiffReport.net_growth_gb(self) (L79): Net growth gb.
- class StorageGrowthTracker (L84): Enterprise Storage Growth Tracker & Snapshot Differ.
- method StorageGrowthTracker.__init__(self, db_path: Optional[str]=None) (L87): Initialize Storage Growth Tracker.
- method StorageGrowthTracker._init_db(self) (L98): Create sqlite schema for snapshot metadata and items.
- method StorageGrowthTracker.take_snapshot(self, root_path: str, label: str='Manual Scan', max_depth: int=5) (L130): Scan directory and capture persistent snapshot.
- method StorageGrowthTracker.list_snapshots(self) (L202): List all captured snapshots.
- method StorageGrowthTracker.compare_snapshots(self, base_id: int, target_id: int) (L221): Calculate differential storage growth between two snapshots.

## src/cortex_unified/system_tools/storage_sense.py — Storage Sense - surface and configure Windows' built-in auto-cleanup.
- class StorageSense (L31): Read and configure Windows Storage Sense (per-user, reversible).
- method StorageSense.is_supported() (L35): Is supported.
- method StorageSense.get_status(self) (L41): Get status.
- method StorageSense._read_values(self) (L47): _read_values.
- method StorageSense._interpret(v: dict[str, int]) (L71): Pure mapping of raw DWORD values -> a friendly status dict.
- method StorageSense._write(self, name: str, value: int) (L92): _write.
- method StorageSense.set_enabled(self, enabled: bool) (L107): Set enabled.
- method StorageSense.set_cadence(self, days: int) (L116): Set cadence.
- method StorageSense.set_recycle_bin_days(self, days: int) (L124): Set recycle bin days.

## src/cortex_unified/system_tools/system_cache_rebuilder.py — Cortex Cleaner — Windows Font, Icon & Thumbnail Cache Rebuilder.
- class CacheRebuildReport (L22): Cache Rebuild Report data container.
- method CacheRebuildReport.__post_init__(self) (L32): __post_init__.
- class SystemCacheRebuilder (L40): Production Windows system cache recovery and rebuilding toolkit.
- method SystemCacheRebuilder.rebuild_font_cache(cls) (L44): Stop FontCache service, delete cached .dat files, and restart service.
- method SystemCacheRebuilder.rebuild_icon_thumbnail_cache(cls) (L91): Purge IconCache.db, iconcache_*.db, and thumbcache_*.db files.
- method SystemCacheRebuilder.notify_shell_refresh(cls) (L122): Issue Windows Shell change notification to reload icons without killing explorer.
- method SystemCacheRebuilder.restart_explorer(cls) (L136): Gracefully terminate and restart Windows Explorer.
- method SystemCacheRebuilder.execute_full_cache_rebuild(cls, restart_shell: bool=False) (L150): Run a full system cache rebuild across fonts, icons, thumbnails, and shell.

## src/cortex_unified/system_tools/system_info.py — System information & diagnostics - lightweight, offline, read-only.
- func _fmt_bytes(n: int | float | None) (L23): _fmt_bytes.
- class SystemInfo (L37): Collect a snapshot of system facts and live metrics.
- method SystemInfo.platform_info(self) (L40): Platform info.
- method SystemInfo.cpu_info(self) (L53): Cpu info.
- method SystemInfo.memory_info(self) (L69): Memory info.
- method SystemInfo.disk_info(self) (L85): Disk info.
- method SystemInfo.battery_info(self) (L107): Battery info.
- method SystemInfo.boot_time(self) (L123): Boot time.
- method SystemInfo.snapshot(self) (L132): Full read-only snapshot for the dashboard/report.

## src/cortex_unified/system_tools/system_repair.py — System file health & repair - orchestrating Windows' own repair tools.
- class RepairResult (L37): Repair Result data container.
- method RepairResult.to_dict(self) (L46): To dict.
- class SystemRepair (L55): Runs SFC / DISM / CHKDSK and interprets their results honestly.
- method SystemRepair.is_supported() (L59): Is supported.
- method SystemRepair.is_elevated() (L64): Is elevated.
- method SystemRepair.run_sfc(self, cancel_event: 'threading.Event | None'=None) (L76): Run sfc.
- method SystemRepair._parse_sfc(out: str | None) (L84): _parse_sfc.
- method SystemRepair.run_dism(self, action: str='CheckHealth', cancel_event: 'threading.Event | None'=None) (L112): Run dism.
- method SystemRepair._parse_dism(out: str | None, action: str) (L125): _parse_dism.
- method SystemRepair.run_chkdsk_scan(self, drive: str='C', cancel_event: 'threading.Event | None'=None) (L157): Run chkdsk scan.
- method SystemRepair._parse_chkdsk(out: str | None, letter: str) (L169): _parse_chkdsk.
- method SystemRepair._run(self, args: list[str], timeout: int, cancel_event: 'threading.Event | None'=None) (L191): _run.
- method SystemRepair._decode(raw: bytes) (L222): _decode.

## src/cortex_unified/system_tools/task_manager.py — Task manager backend - live process + resource monitor with honest totals.
- func _describe(name: str, exe: str) (L29): Friendly description via process_meta; never raises.
- class TaskManager (L38): Stateful monitor. Reuse ONE instance so CPU deltas are meaningful.
- method TaskManager.instance(cls) (L48): Instance.
- method TaskManager.__init__(self) (L54): Initialize Task Manager.
- method TaskManager.snapshot(self, sample_interval: float=0.3) (L65): Return {'cpu':..., 'memory':..., 'processes':[...]} or {'error':...}.
- method TaskManager._refresh_handles(self, psutil) (L106): Return {pid: Process} reusing cached handles; drop dead ones.
- method TaskManager.end_process(self, pid: int, force: bool=False) (L118): Terminate (or kill) a process by PID. Returns (ok, message).
- method TaskManager._collect_processes(self, psutil, cores: int, handles: dict[int, Any]) (L141): _collect_processes.
- method TaskManager._collect_memory(self, psutil, processes: list[dict]) (L182): _collect_memory.
- method TaskManager._installed_ram(self, psutil) (L216): Physically-installed RAM (may exceed OS-usable due to reservations).

## src/cortex_unified/system_tools/telemetry_blocker.py — Telemetry Blocker — comprehensive Windows privacy hardening via Registry.
- func _get_windows_build() (L29): _get_windows_build.
- func _is_win11_24h2_plus() (L43): _is_win11_24h2_plus.
- class TelemetryBlocker (L51): Disables OS telemetry and diagnostic tracking via Windows Registry.
- method TelemetryBlocker.__init__(self) (L54): Initialize Telemetry Blocker.
- method TelemetryBlocker.rules(self) (L60): Rules.
- method TelemetryBlocker._build_rules() (L65): Define all telemetry registry rules.
- method TelemetryBlocker._backup_key(self, rule: dict) (L229): _backup_key.
- method TelemetryBlocker._save_backup(self, entries: List[dict]) (L248): _save_backup.
- method TelemetryBlocker.backup_telemetry(self) (L259): Backup telemetry.
- method TelemetryBlocker.restore_from_backup(self, backup_path: Optional[Path]=None) (L284): Restore from backup.
- method TelemetryBlocker.check_status(self) (L336): Return {label: is_blocked} for every rule.
- method TelemetryBlocker.block_telemetry(self) (L360): Apply all rules. Returns True if ALL succeeded.
- method TelemetryBlocker.restore_defaults(self) (L400): Remove all custom telemetry registry values (restore OS defaults).

## src/cortex_unified/system_tools/temp_folder_cleaner.py — Cortex Cleaner — Windows Temp Folder Deep Scanner & Auto-Cleaner.
- class TempLocation (L22): Temp Location data container.
- class TempScanReport (L34): Temp Scan Report data container.
- class TempCleanResult (L45): Temp Clean Result data container.
- class TempFolderCleaner (L53): Production Windows temp directory deep scanner and auto-cleaner.
- method TempFolderCleaner._get_temp_locations(cls) (L57): Discover all known temp directories on the system.
- method TempFolderCleaner.scan(cls, stale_hours: int=24) (L94): Scan all temp locations and categorize files by age.
- method TempFolderCleaner.clean(cls, stale_hours: int=24, locations_filter: Optional[List[str]]=None, progress_cb: Optional[Callable[[int, str], None]]=None) (L139): Delete stale temp files across all discovered temp locations.

## src/cortex_unified/system_tools/update_checker.py — Release update checker - informational only.
- func parse_version(tag: str) (L27): 'v1.2.3' / '1.2.3' -> (1, 2, 3); anything else -> None.
- func current_version() (L35): The installed package version, from package metadata.
- func fetch_latest_tag(api_url: str=RELEASES_API, timeout: float=_TIMEOUT_S) (L44): Latest release tag from GitHub, or None when offline/blocked.
- func check_for_update(api_url: str=RELEASES_API, timeout: float=_TIMEOUT_S, installed: str | None=None) (L63): Compare installed version against the latest published release.

## src/cortex_unified/system_tools/vhdx_manager.py — Virtual disk (VHDX) reclaim for WSL2, Docker Desktop and Hyper-V.
- class DiskKind(str, enum.Enum) (L44): Which runtime owns a virtual disk (drives the shutdown advice).
- class VirtualDisk (L54): One discovered ``.vhdx`` plus what we honestly know about it.
- method VirtualDisk.potential_saving_bytes(self) (L70): Best-case reclaim, or ``None`` when it cannot be known yet.
- method VirtualDisk.can_compact(self) (L83): True when compaction can be attempted right now.
- method VirtualDisk.status_note(self) (L88): Plain explanation of the current state, always safe to display.
- method VirtualDisk.to_dict(self) (L100): To dict.
- class CompactResult (L118): Outcome of one compaction, measured rather than estimated.
- method CompactResult.freed_bytes(self) (L130): Actual bytes returned to the host (never negative).
- method CompactResult.to_dict(self) (L134): To dict.
- class VhdxManager (L147): Discover and compact WSL / Docker / Hyper-V virtual disks.
- method VhdxManager.__init__(self) (L150): Initialize Vhdx Manager.
- method VhdxManager.is_supported() (L155): Virtual-disk compaction is a Windows-only concern.
- method VhdxManager.list_disks(self) (L161): Return every virtual disk we can account for, largest first.
- method VhdxManager._wsl_disks(self) (L184): Read WSL distributions straight from the registry (no wsl.exe start).
- method VhdxManager._docker_disks(self) (L233): Find Docker Desktop data disks outside the WSL registry entries.
- method VhdxManager._hyperv_disks(self) (L255): List Hyper-V VM disks, but only when the role is actually installed.
- method VhdxManager._measure(self, disk: VirtualDisk) (L277): Fill in host sizes, using the engine's sparse-aware measurement.
- method VhdxManager.measure_guest_usage(self, disk: VirtualDisk, timeout: int=60) (L294): Return bytes used inside a WSL distribution, or ``None``.
- method VhdxManager.shutdown_wsl(self, timeout: int=120) (L322): Run ``wsl --shutdown`` so the virtual disks can be detached.
- method VhdxManager.compact(self, disk: VirtualDisk, timeout: int=3600, cancel_event: 'threading.Event | None'=None) (L343): Compact one virtual disk and report the measured space returned.
- method VhdxManager.set_sparse(self, disk: VirtualDisk, enabled: bool=True, timeout: int=300) (L418): Ask WSL to keep a distribution's disk sparse (WSL 2.3+ only).
- method VhdxManager._explain_failure(out: str | None) (L451): Translate diskpart's output into something actionable.
- method VhdxManager._run_diskpart(self, script: str, timeout: int, cancel_event: 'threading.Event | None'=None) (L467): Run a diskpart script from a temp file; return (looks_ok, output).
- method VhdxManager._run_ps(self, script: str, timeout: int) (L509): Run a PowerShell snippet with a hidden window; None on any failure.
- method VhdxManager._running_processes() (L523): Lower-cased names of running processes (empty set if unavailable).
- method VhdxManager._decode(raw: bytes | str | None) (L540): _decode.
- method VhdxManager._reg_str(key, name: str) (L556): _reg_str.
- method VhdxManager._reg_int(key, name: str) (L568): _reg_int.

## src/cortex_unified/system_tools/vss_health_analyzer.py — Volume Shadow Copy (VSS) Writer Health, Shadow Storage & State Recovery Engine.
- class VssWriterStatus (L39): Status, state code, and error condition of an NT VSS Writer.
- method VssWriterStatus.to_dict(self) (L48): To dict.
- class VssStorageAllocation (L61): Volume shadow copy storage allocation and limit metrics.
- method VssStorageAllocation.to_dict(self) (L69): To dict.
- class VssHealthReport (L81): Comprehensive health and storage report of the Windows VSS subsystem.
- method VssHealthReport.to_dict(self) (L90): To dict.
- class VssResetResult (L103): Outcome of a VSS service and writer state reset operation.
- method VssResetResult.to_dict(self) (L109): To dict.
- class VssHealthAnalyzer (L118): Production Volume Shadow Copy diagnostics and state recovery engine.
- method VssHealthAnalyzer.__init__(self) (L121): Initialize Vss Health Analyzer.
- method VssHealthAnalyzer.inspect_health(self) (L125): Query vssadmin for active writers and volume shadow storage bounds.
- method VssHealthAnalyzer._parse_writers(self, text: str) (L170): _parse_writers.
- method VssHealthAnalyzer._build_writer_status(self, d: Dict[str, str]) (L202): _build_writer_status.
- method VssHealthAnalyzer._parse_shadowstorage(self, text: str) (L227): _parse_shadowstorage.
- method VssHealthAnalyzer._build_storage_allocation(self, d: Dict[str, str]) (L258): _build_storage_allocation.
- func VssHealthAnalyzer._build_storage_allocation._parse_bytes(s: str) (L260): _parse_bytes.
- method VssHealthAnalyzer.reset_vss_writers(self) (L280): Reset stalled VSS writers by cycling dependent Windows services.

## src/cortex_unified/system_tools/vss_manager.py — Cortex Cleaner — Volume Shadow Copy (VSS) & Snapshot Manager.
- class ShadowCopyInfo (L25): Shadow Copy Info data container.
- class ShadowStorageInfo (L36): Shadow Storage Info data container.
- method ShadowStorageInfo.used_gb(self) (L45): Used gb.
- method ShadowStorageInfo.allocated_gb(self) (L50): Allocated gb.
- method ShadowStorageInfo.max_gb(self) (L55): Max gb.
- class VssAuditReport (L61): Vss Audit Report data container.
- class VssManager (L70): Enterprise Volume Shadow Copy (VSS) Manager.
- method VssManager.__init__(self) (L73): Initialize Vss Manager.
- method VssManager.audit(self) (L77): Audit all shadow copies and storage allocations across volumes.
- method VssManager.list_shadows(self) (L95): List all active shadow copies via vssadmin.
- method VssManager.list_shadow_storage(self) (L162): List shadow copy storage space allocations.
- func VssManager.list_shadow_storage._parse_bytes(text: str) (L189): _parse_bytes.
- method VssManager.create_shadow_copy(self, volume: str='C:') (L243): Create an on-demand volume shadow copy.
- method VssManager.delete_oldest_shadow(self, volume: str='C:') (L269): Delete the oldest shadow copy on a given volume to reclaim space.

## src/cortex_unified/system_tools/vulnerability_catalog.py — Versioned, local-only advisory catalog with exact product/version matching.
- class CatalogError(ValueError) (L17): Catalog Error error.
- class VersionConstraint (L23): Version Constraint data container.
- method VersionConstraint.to_dict(self) (L28): To dict.
- class Advisory (L34): Advisory data container.
- method Advisory.to_dict(self) (L45): To dict.
- method Advisory.to_finding(self, device_ip: str, evidence: Iterable[str]) (L58): To finding.
- func normalize_product(value: str) (L77): Normalize product.
- func _parse_version(value: str) (L82): _parse_version.
- func _compare(left: str, right: str) (L93): _compare.
- func _satisfies(version: str, constraint: VersionConstraint) (L115): _satisfies.
- func _constraints(raw: Any) (L131): _constraints.
- func _advisory(raw: Any) (L149): _advisory.
- class VulnerabilityCatalog (L176): Immutable catalog loaded explicitly from a bounded local JSON file.
- method VulnerabilityCatalog.__init__(self, advisories: Iterable[Advisory]=(), catalog_version: int=1) (L179): Initialize Vulnerability Catalog.
- method VulnerabilityCatalog.to_dict(self) (L190): To dict.
- method VulnerabilityCatalog.load(cls, path: str | Path) (L198): Load.
- method VulnerabilityCatalog.match(self, product: str, version: str) (L223): Match normalized product equality plus an explicit parseable version.
- method VulnerabilityCatalog.correlate(self, product: str, version: str, evidence: Iterable[str]) (L234): Compatibility helper that emits findings only with observation evidence.

## src/cortex_unified/system_tools/wake_on_lan.py — Strict, scope-bound Wake-on-LAN packet construction and transmission.
- class WakeOnLanError(RuntimeError) (L24): Base exception for Wake-on-LAN failures.
- class InvalidMacAddress(ValueError, WakeOnLanError) (L28): Raised when a MAC is malformed or unsafe for a unicast device.
- class InvalidBroadcastAddress(ValueError, WakeOnLanError) (L32): Raised when a broadcast is outside supplied active LAN scopes.
- class WakeOnLanSendError(WakeOnLanError) (L36): Raised when the bounded UDP send fails.
- func validate_mac(mac: str | bytes) (L40): Return a strict six-byte globally administered unicast MAC.
- func _active_private_networks(active_networks: Iterable[str | ipaddress.IPv4Network | ipaddress.IPv4Interface]) (L65): _active_private_networks.
- func validate_broadcast(broadcast: str, active_networks: Iterable[str | ipaddress.IPv4Network | ipaddress.IPv4Interface]) (L110): Return a subnet-directed broadcast in a supplied active private LAN.
- func build_magic_packet(mac: str | bytes) (L140): Build the standard 102-byte Wake-on-LAN magic packet.
- func send_magic_packet(mac: str | bytes, broadcast: str, active_networks: Iterable[str | ipaddress.IPv4Network | ipaddress.IPv4Interface], *, port: int=9, timeout: float=1.0) (L149): Send one bounded UDP broadcast and return the transmitted byte count.

## src/cortex_unified/system_tools/wan_audit.py — Read-only, local-only WAN and UPnP IGD audit.
- class InterfaceStatus (L42): A local IPv4 interface used to establish the audit trust boundary.
- method InterfaceStatus.to_dict(self) (L50): To dict.
- class PortMapping (L56): One port mapping returned by ``GetGenericPortMappingEntry``.
- method PortMapping.to_dict(self) (L69): To dict.
- class WanStatus (L75): JSON-safe outcome of a WAN audit.
- method WanStatus.public_ip_classification(self) (L83): Compatibility classification used by the earlier WAN UI.
- method WanStatus.to_dict(self) (L101): To dict.
- func classify_external_ip(value: str | None) (L122): Classify an IGD-reported address without making an external request.
- func classify_public_ip(value: str | None) (L141): Compatibility wrapper using the previous labels.
- func _local_name(tag: str) (L150): _local_name.
- func _safe_xml(data: bytes) (L157): Parse size-capped XML after rejecting DTD/entity declarations.
- func _child_text(root: ET.Element, name: str) (L179): _child_text.
- func _is_trusted_url(url: str, networks: Iterable[ipaddress.IPv4Network]) (L189): Return whether *url* is an HTTP(S) IPv4 literal on a local LAN.
- func _parse_headers(payload: bytes) (L214): _parse_headers.
- func _bounded_int(value: str, minimum: int, maximum: int) (L227): _bounded_int.
- class WanAuditor (L238): Perform a synchronous, cancellable, read-only local WAN audit.
- method WanAuditor.__init__(self, timeout: float=2.0, max_response_bytes: int=_MAX_HTTP_BYTES, max_mappings: int=_MAX_MAPPINGS) (L241): Initialize Wan Auditor.
- method WanAuditor.audit(self, gateway_ips: Iterable[str]=(), include_upnp: bool=False, progress: ProgressFn | None=None, cancel_event: threading.Event | None=None) (L254): Audit.
- method WanAuditor._cancelled(cancel_event: threading.Event | None) (L332): _cancelled.
- method WanAuditor._progress(progress: ProgressFn | None, message: str) (L339): _progress.
- method WanAuditor.local_interfaces() (L347): Return private IPv4 addresses using only standard-library lookups.
- method WanAuditor.discover_locations(self, networks: Iterable[ipaddress.IPv4Network], cancel_event: threading.Event | None=None) (L380): Issue bounded SSDP searches; return trusted LOCATION URLs.
- method WanAuditor._load_igd(self, location: str, networks: Iterable[ipaddress.IPv4Network]) (L418): _load_igd.
- method WanAuditor._read_soap_status(self, status: WanStatus, service_type: str, control_url: str, networks: Iterable[ipaddress.IPv4Network], cancel_event: threading.Event | None, progress: ProgressFn | None) (L453): _read_soap_status.
- method WanAuditor._soap(self, url: str, service_type: str, action: str, arguments: Mapping[str, str] | None=None) (L509): _soap.
- method WanAuditor._mapping_from_xml(index: int, root: ET.Element) (L557): _mapping_from_xml.
- method WanAuditor._http_request(self, method: str, url: str, body: bytes | None=None, headers: Mapping[str, str] | None=None) (L581): Perform one no-redirect request with a hard response-size cap.
- method WanAuditor.default_gateway() (L634): Read the local default IPv4 route without network traffic.
- method WanAuditor.dns_servers() (L665): Read locally configured DNS server addresses.
- class _NoMoreMappings(Exception) (L699): Internal sentinel for the normal end of mapping enumeration.
- func _xml_escape(value: str) (L703): _xml_escape.
- func audit_wan(gateway_ips: Iterable[str]=(), include_upnp: bool=False, progress: ProgressFn | None=None, cancel_event: threading.Event | None=None) (L712): Return route-only status unless optional local UPnP reads are authorized.

## src/cortex_unified/system_tools/winapp2_cleaner.py — Declarative Community & Third-Party Application Cleaner (Winapp2.ini Engine).
- class Winapp2Rule (L137): Represents a single parsed Winapp2 application cleaning rule.
- class AppCleanTarget (L152): Target item identified for removal.
- class Winapp2Report (L163): Scan and cleanup report from the Winapp2 engine.
- method Winapp2Report.to_dict(self) (L174): To dict.
- class Winapp2Cleaner (L197): High-throughput declarative cleaner engine for Windows applications.
- method Winapp2Cleaner.__init__(self, custom_ini_content: Optional[str]=None) (L210): Initialize Winapp2 Cleaner.
- method Winapp2Cleaner.expand_vars(cls, path_str: str) (L216): Dynamically expand Windows environment variables and handle variations.
- method Winapp2Cleaner._load_rules(self, ini_content: str) (L243): Parse winapp2.ini declarative syntax into rule definitions.
- method Winapp2Cleaner._is_app_installed(self, rule: Winapp2Rule) (L285): Determine if target application exists via filesystem or registry.
- method Winapp2Cleaner.is_safe_path(self, path: Path) (L318): Enforce strict safety boundary check preventing deletion of OS/system roots.
- method Winapp2Cleaner.scan(self, progress_cb: Optional[Callable[[int, int, str], None]]=None, cancel_event: Optional[Any]=None) (L335): Scan candidate application targets matching detected software rules.
- method Winapp2Cleaner.clean(self, targets: Optional[List[AppCleanTarget]]=None, dry_run: bool=False, progress_cb: Optional[Callable[[int, int, str], None]]=None) (L425): Execute safe removal of identified cache targets. Returns (cleaned_bytes, cleaned_items).

## src/cortex_unified/system_tools/windows_update.py — Windows Update status - what's pending and when you last updated.
- class PendingUpdate (L36): Pending Update data container.
- method PendingUpdate.to_dict(self) (L43): To dict.
- class WindowsUpdate (L49): Read Windows Update state (read-only).
- method WindowsUpdate.is_supported() (L53): Is supported.
- method WindowsUpdate.last_activity(self) (L59): Last activity.
- method WindowsUpdate._read_result_time(sub: str) (L69): _read_result_time.
- method WindowsUpdate.check_pending(self) (L86): Check pending.
- method WindowsUpdate._parse_pending(out: str | None) (L100): _parse_pending.
- func WindowsUpdate._parse_pending._int(v) (L111): _int.
- method WindowsUpdate.recent_history(self, limit: int=15) (L139): Recent history.
- method WindowsUpdate._parse_history(out: str | None) (L154): _parse_history.
- method WindowsUpdate._run(self, script: str, timeout: int) (L185): _run.

## src/cortex_unified/system_tools/windows_update_repair.py — Windows Update Repair Toolkit — comprehensive component reset and repair.
- class PhaseResult (L95): Phase Result data container.
- class DiagnosticReport (L106): Diagnostic Report data container.
- method DiagnosticReport.to_json(self) (L118): To json.
- class RepairResult (L125): Repair Result data container.
- method RepairResult.summary(self) (L133): Summary.
- class WindowsUpdateRepair (L185): Comprehensive Windows Update component repair.
- method WindowsUpdateRepair.__init__(self, create_restore_point: bool=True, progress_callback: Optional[Callable[[str], None]]=None, cancel_event: Optional[threading.Event]=None, dry_run: bool=False) (L188): Initialize Windows Update Repair.
- method WindowsUpdateRepair._run(self, cmd: List[str], timeout: int=120, shell: bool=False) (L211): _run.
- method WindowsUpdateRepair._run_ps(self, script: str, timeout: int=180) (L231): _run_ps.
- method WindowsUpdateRepair._sc_query(self, name: str) (L237): _sc_query.
- method WindowsUpdateRepair._service_status(self, name: str) (L244): _service_status.
- method WindowsUpdateRepair._stop_service(self, name: str, retries: int=3) (L254): _stop_service.
- method WindowsUpdateRepair._start_service(self, name: str) (L267): _start_service.
- method WindowsUpdateRepair.preflight(self) (L276): Run diagnostic pre-checks.
- method WindowsUpdateRepair._phase_stop_services(self) (L354): _phase_stop_services.
- method WindowsUpdateRepair._phase_clear_caches(self) (L370): _phase_clear_caches.
- method WindowsUpdateRepair._phase_reset_registry_policies(self) (L410): _phase_reset_registry_policies.
- method WindowsUpdateRepair._phase_reset_security_descriptors(self) (L437): _phase_reset_security_descriptors.
- method WindowsUpdateRepair._phase_reregister_dlls(self) (L452): _phase_reregister_dlls.
- method WindowsUpdateRepair._phase_reset_network(self) (L467): _phase_reset_network.
- method WindowsUpdateRepair._phase_dism_repair(self) (L493): _phase_dism_repair.
- method WindowsUpdateRepair._phase_sfc(self) (L508): _phase_sfc.
- method WindowsUpdateRepair._phase_component_store(self) (L517): Analyze and optionally cleanup component store.
- method WindowsUpdateRepair._phase_start_services(self) (L528): _phase_start_services.
- method WindowsUpdateRepair._phase_verify(self) (L544): _phase_verify.
- method WindowsUpdateRepair.repair_all(self, phases: Optional[List[str]]=None) (L564): Run all repair phases (or specified subset).
- method WindowsUpdateRepair.repair_selective(self, phase_names: List[str]) (L606): Run only specified phases.
- method WindowsUpdateRepair.quick_reset(self) (L610): Minimal reset: services, caches, DLLs, network, restart.

## src/cortex_unified/system_tools/wsl_cleaner.py — WSL distro cleanup: size reporting, shutdown + vhdx compaction.
- class WslDistro (L33): One WSL distribution with its vhdx estimate.
- method WslDistro.to_dict(self) (L42): To dict.
- func _fmt_bytes(n: int) (L56): _fmt_bytes.
- func _decode(raw: bytes | str | None) (L68): _decode.
- class WslCleaner (L84): Discover and clean WSL distro disks (Windows-only).
- method WslCleaner.is_supported() (L88): Is supported.
- method WslCleaner.is_wsl_available(self) (L92): Is wsl available.
- method WslCleaner.list_distros(self) (L111): Enumerate distros via ``wsl --list --verbose`` + vhdx size probe.
- method WslCleaner.shutdown(self, timeout: int=120) (L204): Run ``wsl --shutdown`` so vhdx files can be detached for compaction.
- method WslCleaner.compact_vhdx(self, vhdx_path: Path, timeout: int=3600, cancel_event=None) (L220): Compact a single vhdx via VhdxManager.diskpart path (read-only attach).
- method WslCleaner.get_total_vhdx_size(self) (L245): Total (logical, on-disk) bytes across all distro vhdx files.
- method WslCleaner._reg_str(key, name: str) (L251): _reg_str.
- method WslCleaner._reg_int(key, name: str) (L263): _reg_int.

## src/cortex_unified/translations/__init__.py — Internationalization module for Cortex Cleaner.
- func get_available_locales() (L28): Get available locales from default translator.
- func set_locale(locale: str) (L33): Set active locale.

## src/cortex_unified/translations/settings_integration.py — Qt settings surface for i18n and accessibility preferences.
- class I18nSettingsWidget(QWidget) (L24): Editor widget persisting i18n/accessibility choices to QSettings.
- method I18nSettingsWidget.__init__(self, parent=None) (L31): Build the controls and restore persisted values.
- method I18nSettingsWidget.setup_ui(self) (L42): Assemble language and accessibility groups; no-op without Qt.
- method I18nSettingsWidget.populate_languages(self) (L87): Fill the combo with native names, storing locale as item data.
- method I18nSettingsWidget.populate_themes(self) (L100): Mirror theme_manager.get_available_themes() into the combo.
- method I18nSettingsWidget.load_settings(self) (L111): Restore persisted values; absent keys fall back to defaults.
- method I18nSettingsWidget.save_settings(self) (L142): Write current control state to QSettings and sync.
- method I18nSettingsWidget.on_language_changed(self, language_name) (L162): Apply the picked locale globally and persist it.
- method I18nSettingsWidget.on_theme_changed(self, theme_name) (L171): Apply the picked theme and persist its id.
- method I18nSettingsWidget.on_accessibility_changed(self) (L180): Push the combined a11y state to the theme manager and persist it.
- class I18nManager (L197): Startup glue: replays persisted locale/theme and hands out the widget.
- method I18nManager.__init__(self) (L200): No-op without PySide6; otherwise restores saved preferences.
- method I18nManager.load_saved_settings(self) (L209): Replay persisted locale/theme; failures are logged, not raised.
- method I18nManager.create_settings_widget(self, parent=None) (L226): Return an I18nSettingsWidget, or None without PySide6.
- method I18nManager.get_current_locale(self) (L232): Currently active locale code.
- method I18nManager.get_current_theme(self) (L236): Currently active theme id.
- method I18nManager.is_rtl_layout(self) (L240): True when the active locale renders right-to-left.
- func get_i18n_manager() (L247): Return the shared I18nManager, creating it on first call.

## src/cortex_unified/translations/translator.py — Translation and internationalization management.
- class Translator (L14): Resolves translation keys against cached JSON locale catalogs.
- method Translator.__init__(self, locale: str='en') (L22): Create the translator and load ``locale`` immediately.
- method Translator.load_translations(self, locale: str) (L37): Load and cache a catalog, recursing into the fallback on failure.
- method Translator.translate(self, key: str, **kwargs) (L69): Resolve ``key`` in the active locale, then the fallback.
- method Translator._get_translation(self, key: str, locale: str) (L95): Walk a dotted key through one locale's cached catalog.
- method Translator.get_available_locales(self) (L113): Locale codes present on disk; always contains the fallback.
- method Translator.set_locale(self, locale: str) (L129): Set current locale for translations.
- method Translator.get_locale_info(self, locale: str) (L138): Display metadata from the locale file's ``_meta`` block.
- method Translator.is_rtl_locale(self, locale: str=None) (L167): True when the locale metadata declares RTL direction.
- func get_translator() (L178): Return the shared Translator, creating it on first call.
- func set_global_locale(locale: str) (L185): Point the shared Translator at a new locale.
- func translate(key: str, **kwargs) (L190): Module-level shorthand delegating to the shared Translator.

## src/cortex_unified/ui/__init__.py — Cortex Workstation User Interface and Presentation Subsystems.
- (no classes/functions — constants/imports only)

## src/cortex_unified/ui/launcher.py — GUI entry point for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/ui/main_window.py — Main window for Cortex Cleaner GUI.
- class ScanWorker(QObject) (L67): Runs a filesystem scan off the GUI thread.
- method ScanWorker.__init__(self, config: Config, path: str, enable_checkpoints: bool=False, enable_throttling: bool=False, checkpoint_id: str='') (L83): Store scan config, target path, checkpoint/throttle flags, and the cancel flag.
- method ScanWorker.run(self) (L96): Run the scanner (emits finished with (files, dirs), or error); relays checkpoint progress from a poller thread.
- func progress_monitor() (L107): Poll scanner progress every 0.5s and relay it via progress_updated until stopped.
- method ScanWorker.pause(self) (L126): Pause the scanner via its scan manager.
- method ScanWorker.resume(self) (L133): Resume a paused scanner.
- method ScanWorker.stop(self) (L140): Request abort and create a resumable checkpoint (returns its id or None).
- class DeleteWorker(QObject) (L154): Deletes scanned empty files/dirs off the GUI thread.
- method DeleteWorker.__init__(self, deleter: Deleter, empty_files: List[Path], empty_dirs: List[Path]) (L159): Store the deleter and the file/dir lists to remove.
- method DeleteWorker.run(self) (L168): Run the deletion (emits finished with the result dict, or error).
- class MultiDriveScanWorker(QObject) (L179): Scans several drives sequentially, aggregating their results.
- method MultiDriveScanWorker.__init__(self, config: Config, paths: List[str], enable_checkpoints: bool=False, enable_throttling: bool=False) (L185): Store config, drive paths, checkpoint/throttle flags, and pause/stop flags.
- method MultiDriveScanWorker.run(self) (L197): Scan each configured drive and emit the combined result lists.
- func progress_monitor() (L208): Poll overall multi-drive progress every 0.5s unless paused/stopped.
- method MultiDriveScanWorker.pause(self) (L237): Set the paused flag so the scan loop waits.
- method MultiDriveScanWorker.resume(self) (L243): Clear the paused flag so scanning continues.
- method MultiDriveScanWorker.stop(self) (L249): Set the stop flag to break the per-drive scan loop.
- class DeepCleanerGUI(QMainWindow) (L256): Main window for Cortex Cleaner GUI application.
- method DeepCleanerGUI.__init__(self) (L259): Set up config, safety manager, workers, and the UI; schedule tray/tabs on timers.
- method DeepCleanerGUI.init_tray_icon(self) (L308): Attach the tray icon; failure is logged and otherwise ignored.
- method DeepCleanerGUI.__getattr__(self, name) (L316): Proxy missing widget access to child tabs.
- method DeepCleanerGUI._safe_widget(self, name, default=None) (L333): Safely get a widget attribute, returning default if not found.
- method DeepCleanerGUI.init_ui(self) (L340): Build the base tabs and status bar; advanced tabs attach later.
- method DeepCleanerGUI.add_advanced_tabs(self) (L382): Attach lazily imported tabs once the window is fully initialized.
- method DeepCleanerGUI.browse_path(self) (L423): Open file dialog to select target path.
- method DeepCleanerGUI.browse_path_for_widget(self, widget) (L429): Open file dialog to select target path for a specific widget.
- method DeepCleanerGUI.add_activity(self, message) (L435): Append a timestamped message to the activity list, if present.
- method DeepCleanerGUI.get_current_time(self) (L443): Return the current local time as HH:MM:SS.
- method DeepCleanerGUI.quick_scan(self) (L450): Point the path input at the home folder, switch to the scan tab, and scan.
- method DeepCleanerGUI.start_scan(self) (L462): Validate targets and dispatch scanning to a worker thread.
- method DeepCleanerGUI.scan_finished(self, empty_files: List[Path], empty_dirs: List[Path]) (L581): Handle scan completion (runs on the UI thread via signal).
- method DeepCleanerGUI.scan_error(self, error: str) (L615): Reset the scan controls and report the error to the user.
- method DeepCleanerGUI.update_scan_progress(self, progress) (L632): Render a worker progress report in the progress bar.
- method DeepCleanerGUI.start_delete(self) (L642): Confirm options with the user and run Deleter on a worker thread.
- method DeepCleanerGUI.pause_scan(self) (L686): Pause the active scan worker.
- method DeepCleanerGUI.resume_scan(self) (L714): Resume a paused scan worker.
- method DeepCleanerGUI.delete_finished(self, result: Dict[str, Any]) (L742): Handle deletion completion.
- method DeepCleanerGUI.delete_error(self, error: str) (L768): Handle deletion error.
- method DeepCleanerGUI.show_treemap_visualization(self) (L778): Export the current analysis as a Plotly treemap and open it in a browser.
- method DeepCleanerGUI.show_sunburst_visualization(self) (L802): Export the current analysis as a Plotly sunburst chart and open it in a browser.
- method DeepCleanerGUI.show_interactive_dashboard(self) (L826): Export the current analysis as a Plotly dashboard and open it in a browser.
- method DeepCleanerGUI.export_visualization_dialog(self) (L856): Show a modal dialog choosing visualization type and export format.
- method DeepCleanerGUI.perform_visualization_export(self, dialog) (L898): Write the visualization chosen in the export dialog to disk.
- method DeepCleanerGUI.refresh_startup_items(self) (L948): Load startup items into the table via StartupManager, handling errors.
- method DeepCleanerGUI.disable_selected_startup_items(self) (L985): Disable the selected startup rows via StartupManager and refresh.
- method DeepCleanerGUI.refresh_processes(self) (L1030): Load running processes and services into their tables via ProcessAnalyzer.
- method DeepCleanerGUI.quick_temp_clean(self) (L1089): Activate the temp-cleaning tab and start its scan immediately.
- method DeepCleanerGUI.start_temp_scan(self) (L1098): Start a temp file scan and report findings.
- method DeepCleanerGUI.scan_registry(self) (L1115): Scan for orphaned registry entries and show them; enables the clean button.
- method DeepCleanerGUI.clean_registry(self) (L1174): Back up the registry, then remove the scanned orphaned entries after confirmation.
- method DeepCleanerGUI.refresh_manifests(self) (L1217): Refresh backup manifests.
- method DeepCleanerGUI.restore_selected(self) (L1250): Restore from selected manifest.
- method DeepCleanerGUI.save_settings(self) (L1285): Persist log-file/verbose settings to QSettings and the YAML config file.
- method DeepCleanerGUI.load_settings(self) (L1307): Load persisted UI settings, then overlay config-file values.
- method DeepCleanerGUI.format_bytes(self, bytes_value: Union[int, float]) (L1324): Format bytes to human readable format.
- method DeepCleanerGUI.closeEvent(self, event) (L1333): Stop worker threads before accepting the close.
- method DeepCleanerGUI.switch_to_tab(self, index: int) (L1366): Switch the legacy tab widget to the given index, if present.
- method DeepCleanerGUI.create_heuristics_tab(self) (L1374): Build the heuristics tab: options, scan path, and leftovers results table.
- method DeepCleanerGUI.detect_package_managers(self) (L1432): Detect available package managers.
- method DeepCleanerGUI.start_pm_scan(self) (L1449): Start package manager cache scan.
- method DeepCleanerGUI.start_pm_cleanup(self) (L1483): Start package manager cleanup.
- method DeepCleanerGUI.browse_heuristics_path(self) (L1519): Browse for heuristics scan path.
- method DeepCleanerGUI.start_heuristics_scan(self) (L1525): Scan for app leftovers at/above the confidence threshold and store the results.
- method DeepCleanerGUI.start_heuristics_cleanup(self) (L1560): Confirm, then trash the high-confidence leftover paths via Deleter.
- method DeepCleanerGUI.repair_selected_links(self) (L1593): Repair selected broken links.
- method DeepCleanerGUI.on_path_mode_changed(self) (L1629): Handle path mode radio button changes.
- method DeepCleanerGUI.detect_available_drives(self) (L1640): List all disk partitions with free/total space into the drives list.
- method DeepCleanerGUI.add_network_drive(self) (L1664): Show a dialog to enter a network path with optional credentials.
- method DeepCleanerGUI.test_network_connection(self, path, username, password) (L1698): Test network drive connection.
- method DeepCleanerGUI.add_network_path(self, dialog, path, username, password) (L1713): Add the entered network path (with credentials) to the drives list.
- method DeepCleanerGUI.remove_selected_drives(self) (L1733): Remove the selected drives from the multi-drive scan list.
- method DeepCleanerGUI.on_checkpoint_selection_changed(self) (L1746): Handle checkpoint selection changes.
- method DeepCleanerGUI.list_checkpoints(self) (L1752): List available checkpoints.
- method DeepCleanerGUI.resume_from_checkpoint(self) (L1774): Resume scanning from selected checkpoint.
- method DeepCleanerGUI.start_scan_with_checkpoint(self, checkpoint_id) (L1803): Start scan with a specific checkpoint.
- method DeepCleanerGUI.delete_checkpoint(self) (L1836): Delete selected checkpoint.
- method DeepCleanerGUI.cleanup_old_checkpoints(self) (L1862): Prompt for an age and delete checkpoints older than that many days.
- method DeepCleanerGUI.create_file_shredder_tab(self) (L1881): Build the file shredder tab: warning banner, file list, options, and actions.
- method DeepCleanerGUI.add_files_to_shred(self) (L1945): Append chosen files to the shred list, skipping duplicates.
- method DeepCleanerGUI.add_folder_to_shred(self) (L1954): Add folder contents to the shredding list.
- method DeepCleanerGUI.remove_files_from_shred(self) (L1969): Remove selected files from the shredding list.
- method DeepCleanerGUI.clear_shred_list(self) (L1976): Clear all files from the shredding list.
- method DeepCleanerGUI.start_file_shredding(self) (L1980): Confirm, then shred every listed file with the chosen method/passes.
- method DeepCleanerGUI.create_scheduler_tab(self) (L2047): Create the task scheduler tab.
- method DeepCleanerGUI.create_tasks_subtab(self) (L2059): Create the tasks sub-tab.
- method DeepCleanerGUI.create_auto_clean_rules_subtab(self) (L2142): Create the auto-clean rules sub-tab.
- method DeepCleanerGUI.on_task_selection_changed(self) (L2219): Handle task selection changes.
- method DeepCleanerGUI.create_scheduled_task(self) (L2228): Create a new scheduled task.
- method DeepCleanerGUI.refresh_scheduled_tasks(self) (L2271): Refresh the list of scheduled tasks.
- method DeepCleanerGUI.run_selected_task(self) (L2301): Execute the selected scheduled task immediately via TaskScheduler.
- method DeepCleanerGUI.delete_selected_task(self) (L2327): Confirm and delete the selected scheduled task.
- method DeepCleanerGUI.create_reports_tab(self) (L2356): Build the reports tab: generation options, recent reports, and templates.
- method DeepCleanerGUI.generate_report(self) (L2431): Generate a report based on current settings.
- method DeepCleanerGUI.preview_report(self) (L2458): Generate an HTML preview and show it in a web-engine dialog (or a summary fallback).
- method DeepCleanerGUI.schedule_report(self) (L2487): Schedule automatic report generation.
- method DeepCleanerGUI.refresh_reports_list(self) (L2504): Refresh the list of generated reports.
- method DeepCleanerGUI.view_report(self, report_path) (L2534): View a generated report.
- method DeepCleanerGUI.delete_report(self, report_path) (L2547): Delete a generated report.
- method DeepCleanerGUI.save_report_template(self) (L2563): Save current report settings as a template.
- method DeepCleanerGUI.load_report_template(self) (L2575): Report loading the selected template (UI-level confirmation only).
- method DeepCleanerGUI.create_resource_monitor_tab(self) (L2590): Build the resource monitor tab: controls, metric gauges, process table, alerts.
- method DeepCleanerGUI.start_resource_monitoring(self) (L2687): Start real-time resource monitoring.
- method DeepCleanerGUI.stop_resource_monitoring(self) (L2702): Stop real-time resource monitoring.
- method DeepCleanerGUI.update_resource_metrics(self) (L2712): Refresh all CPU/memory/disk/network displays and the top-process table from the monitor.
- method DeepCleanerGUI.check_performance_alerts(self, cpu_percent, memory_percent) (L2746): Append timestamped alerts when CPU/memory usage exceeds the thresholds.
- method DeepCleanerGUI.on_rule_selection_changed(self) (L2762): Handle auto-clean rule selection changes.
- method DeepCleanerGUI.create_auto_clean_rule(self) (L2771): Create a new auto-clean rule.
- method DeepCleanerGUI.refresh_auto_clean_rules(self) (L2799): Refresh the list of auto-clean rules.
- method DeepCleanerGUI.test_selected_rule(self) (L2827): Test the selected auto-clean rule.
- method DeepCleanerGUI.delete_selected_rule(self) (L2851): Delete the selected auto-clean rule.
- func main() (L2878): Main entry point for the GUI application.

## src/cortex_unified/ui/navigation/__init__.py — Navigation framework for Cortex Cleaner GUI.
- (no classes/functions — constants/imports only)

## src/cortex_unified/ui/navigation/icon_helper.py — Icon helper for navigation system.
- class IconHelper (L8): Helper class for creating and managing navigation icons.
- method IconHelper.create_text_icon(text: str, size: QSize=QSize(16, 16), color: str='#495057') (L12): Create an icon from text (useful for simple text-based icons).
- method IconHelper.get_standard_icon(icon_type: QStyle.StandardPixmap) (L46): Get a standard Qt icon.
- method IconHelper.get_navigation_icons() (L62): Get a dictionary of icons for common navigation items.
- method IconHelper.create_colored_circle_icon(color: str, size: QSize=QSize(16, 16)) (L101): Create a simple colored circle icon.

## src/cortex_unified/ui/navigation/navigation_controller.py — Navigation controller for Cortex Cleaner GUI.
- class NavigationController(QWidget) (L13): Modern side-panel navigation controller that replaces QTabWidget.
- method NavigationController.__init__(self, parent=None) (L20): __init__.
- method NavigationController.setup_ui(self) (L34): Set up the navigation UI components.
- method NavigationController.create_navigation_panel(self) (L52): Create the left navigation panel.
- method NavigationController.setup_styling(self) (L83): Apply professional styling to the navigation components.
- method NavigationController.add_tab(self, widget: QWidget, name: str, icon: Optional[QIcon]=None) (L130): Add a new tab to the navigation system.
- method NavigationController.remove_tab(self, name: str) (L167): Remove a tab from the navigation system.
- method NavigationController.set_current_tab(self, index: int) (L196): Set the current tab by index.
- method NavigationController.set_current_tab_by_name(self, name: str) (L214): Set the current tab by name.
- method NavigationController.get_current_tab_name(self) (L229): Get the name of the currently selected tab.
- method NavigationController.get_current_widget(self) (L237): Get the currently displayed widget.
- method NavigationController.get_tab_count(self) (L241): Get the total number of tabs.
- method NavigationController.get_tab_names(self) (L245): Get a list of all tab names.
- method NavigationController.on_navigation_changed(self, current_row: int) (L249): Handle navigation selection changes.
- method NavigationController.clear_tabs(self) (L261): Remove all tabs from the navigation system.
- method NavigationController.update_tab_icon(self, name: str, icon: QIcon) (L272): Update the icon for a specific tab.
- method NavigationController.update_tab_name(self, old_name: str, new_name: str) (L290): Update the display name for a specific tab.
- method NavigationController.setup_default_icons(self) (L311): Set up default icons for all tabs using the IconHelper.
- method NavigationController.add_tab_with_default_icon(self, widget: QWidget, name: str) (L319): Add a tab with a default icon from the IconHelper.

## src/cortex_unified/ui/premium/__init__.py — Cortex Cleaner - premium GUI.
- (no classes/functions — constants/imports only)

## src/cortex_unified/ui/premium/advanced_uninstaller_page.py — Advanced Uninstaller — multi-source app removal with forced uninstall and leftover scanning.
- class _UninstallWorker(QObject) (L40): _UninstallWorker class.
- method _UninstallWorker.__init__(self, app_ids: list[str], force: bool, scan_leftovers: bool, max_leftovers_mb: int, sources: list[str]) (L46): Initialize worker.
- method _UninstallWorker.cancel(self) (L63): cancel.
- method _UninstallWorker.run(self) (L67): run.
- class AdvancedUninstallerPage(_Page) (L111): Multi-source uninstaller with forced removal and leftover detection.
- method AdvancedUninstallerPage.__init__(self, win) (L114): __init__.
- method AdvancedUninstallerPage._pick_root(self) (L243): _pick_root.
- method AdvancedUninstallerPage._scan(self) (L253): _scan.
- method AdvancedUninstallerPage._on_progress(self, msg: str) (L277): _on_progress.
- method AdvancedUninstallerPage._on_scan_done(self, apps: list[AppInfo]) (L281): _on_scan_done.
- method AdvancedUninstallerPage._confirm_uninstall(self) (L308): _confirm_uninstall.
- method AdvancedUninstallerPage._run_uninstall(self, apps: list[AppInfo]) (L370): _run_uninstall.
- method AdvancedUninstallerPage._on_uninstall_done(self, results: list[UninstallResult]) (L392): _on_uninstall_done.
- method AdvancedUninstallerPage._on_fail(self, msg: str) (L443): _on_fail.
- method AdvancedUninstallerPage._selected_apps(self) (L452): _selected_apps.
- method AdvancedUninstallerPage._fail(self, msg: str) (L466): _fail.

## src/cortex_unified/ui/premium/analysis_pages.py — Analysis & system pages: Disk Analyzer, Disk Health (S.M.A.R.T.), Scheduled Tasks.
- class DiskAnalyzeWorker(QObject) (L44): DiskAnalyzeWorker class.
- method DiskAnalyzeWorker.__init__(self, root: str) (L49): __init__.
- method DiskAnalyzeWorker.run(self) (L54): run.
- class DiskHealthWorker(QObject) (L67): DiskHealthWorker class.
- method DiskHealthWorker.run(self) (L72): run.
- class ScheduledTasksWorker(QObject) (L81): ScheduledTasksWorker class.
- method ScheduledTasksWorker.run(self) (L86): run.
- class BootPerfWorker(QObject) (L95): BootPerfWorker class.
- method BootPerfWorker.run(self) (L100): run.
- class SystemRepairWorker(QObject) (L109): SystemRepairWorker class.
- method SystemRepairWorker.__init__(self, action: str, drive: str='C') (L114): __init__.
- method SystemRepairWorker.run(self) (L120): run.
- class DeleteTaskWorker(QObject) (L140): DeleteTaskWorker class.
- method DeleteTaskWorker.__init__(self, name: str) (L145): __init__.
- method DeleteTaskWorker.run(self) (L150): run.
- class DiskAnalyzerPage(_Page) (L164): Break down where space goes: file types + largest directories.
- method DiskAnalyzerPage.__init__(self, win) (L167): __init__.
- method DiskAnalyzerPage._pick(self) (L244): _pick.
- method DiskAnalyzerPage._run(self) (L251): _run.
- method DiskAnalyzerPage._on_done(self, stats: dict) (L258): _on_done.
- method DiskAnalyzerPage._fail(self, msg: str) (L304): _fail.
- class DiskHealthPage(_Page) (L314): Read-only physical-disk health (S.M.A.R.T.) overview.
- method DiskHealthPage.__init__(self, win) (L317): __init__.
- method DiskHealthPage._load(self) (L369): _load.
- method DiskHealthPage._dash(v) (L377): _dash.
- method DiskHealthPage._on_done(self, disks: list) (L381): _on_done.
- method DiskHealthPage._fail(self, msg: str) (L416): _fail.
- class ScheduledTasksPage(_Page) (L426): View OS scheduled tasks; delete Cortex-created cleanup tasks.
- method ScheduledTasksPage.__init__(self, win) (L429): __init__.
- method ScheduledTasksPage._load(self) (L485): _load.
- method ScheduledTasksPage._on_done(self, tasks: list) (L492): _on_done.
- method ScheduledTasksPage._delete(self) (L507): _delete.
- method ScheduledTasksPage._on_deleted(self, ok: bool, name: str) (L526): _on_deleted.
- method ScheduledTasksPage._fail(self, msg: str) (L537): _fail.
- class BootPerformancePage(_Page) (L547): Why your PC is slow to start - using Windows' own boot measurements.
- method BootPerformancePage.__init__(self, win) (L550): __init__.
- method BootPerformancePage._load(self) (L613): _load.
- method BootPerformancePage._on_done(self, data: dict) (L620): _on_done.
- method BootPerformancePage._fail(self, msg: str) (L668): _fail.
- class SystemRepairPage(_Page) (L678): Run Windows' built-in SFC / DISM / CHKDSK repair tools, explained.
- method SystemRepairPage.__init__(self, win) (L681): __init__.
- method SystemRepairPage._tool_row(self, layout, title, desc, handler) (L754): _tool_row.
- method SystemRepairPage._run(self, action: str, title: str, prompt: str) (L771): _run.
- method SystemRepairPage._on_done(self, r: dict) (L789): _on_done.
- method SystemRepairPage._fail(self, msg: str) (L819): _fail.
- class StorageSenseWorker(QObject) (L834): StorageSenseWorker class.
- method StorageSenseWorker.__init__(self, action: str='status', value: int=0) (L839): __init__.
- method StorageSenseWorker.run(self) (L845): run.
- class StorageSensePage(_Page) (L861): Turn on and schedule Windows' built-in automatic cleanup.
- method StorageSensePage.__init__(self, win) (L868): __init__.
- method StorageSensePage._load(self) (L923): _load.
- method StorageSensePage._on_status(self, s: dict) (L927): _on_status.
- method StorageSensePage._toggle_enable(self, on: bool) (L952): _toggle_enable.
- method StorageSensePage._set_cadence(self, idx: int) (L959): _set_cadence.
- method StorageSensePage._set_recycle(self, idx: int) (L966): _set_recycle.
- method StorageSensePage._fail(self, msg: str) (L973): _fail.
- class DefenderStatusWorker(QObject) (L982): DefenderStatusWorker class.
- method DefenderStatusWorker.run(self) (L987): run.
- class DefenderScanWorker(QObject) (L997): DefenderScanWorker class.
- method DefenderScanWorker.run(self) (L1002): run.
- class SecurityPage(_Page) (L1012): Windows Security (Defender) status + quick scan.
- method SecurityPage.__init__(self, win) (L1015): __init__.
- method SecurityPage._load(self) (L1076): _load.
- method SecurityPage._on_status(self, s: dict, threats: list) (L1082): _on_status.
- method SecurityPage._scan(self) (L1126): _scan.
- method SecurityPage._on_scanned(self, ok: bool, msg: str) (L1143): _on_scanned.
- method SecurityPage._fail(self, msg: str) (L1153): _fail.
- class HealthCheckWorker(QObject) (L1164): HealthCheckWorker class.
- method HealthCheckWorker.run(self) (L1170): run.
- class HealthCheckPage(_Page) (L1180): One click to assess overall PC health across the fast diagnostics.
- method HealthCheckPage.__init__(self, win) (L1194): __init__.
- method HealthCheckPage._run(self) (L1272): _run.
- method HealthCheckPage._on_progress(self, msg: str) (L1286): _on_progress.
- method HealthCheckPage._on_done(self, report: dict) (L1290): _on_done.
- method HealthCheckPage._fail(self, msg: str) (L1341): _fail.
- class WUActivityWorker(QObject) (L1356): WUActivityWorker class.
- method WUActivityWorker.run(self) (L1361): run.
- class WUPendingWorker(QObject) (L1371): WUPendingWorker class.
- method WUPendingWorker.run(self) (L1376): run.
- class WindowsUpdatePage(_Page) (L1385): See when Windows last updated, what's pending, and recent update history.
- method WindowsUpdatePage.__init__(self, win) (L1388): __init__.
- method WindowsUpdatePage._load(self) (L1464): _load.
- method WindowsUpdatePage._on_activity(self, activity: dict, history: list) (L1469): _on_activity.
- method WindowsUpdatePage._check_pending(self) (L1483): _check_pending.
- method WindowsUpdatePage._on_pending(self, updates: list) (L1490): _on_pending.
- method WindowsUpdatePage._open_settings(self) (L1504): _open_settings.
- method WindowsUpdatePage._fail(self, msg: str) (L1512): _fail.
- class ComponentStorePage(_Page) (L1522): Shrink WinSxS the supported way, and clear upgrade leftovers.
- method ComponentStorePage.__init__(self, win) (L1532): __init__.
- method ComponentStorePage._selected_leftovers(self) (L1650): _selected_leftovers.
- method ComponentStorePage._on_select(self) (L1655): _on_select.
- method ComponentStorePage._analyze(self) (L1663): _analyze.
- method ComponentStorePage._on_analyzed(self, analysis, leftovers: list) (L1672): _on_analyzed.
- method ComponentStorePage._clean(self) (L1727): _clean.
- method ComponentStorePage._on_cleaned(self, outcome) (L1753): _on_cleaned.
- method ComponentStorePage._run_task(self) (L1777): _run_task.
- method ComponentStorePage._on_task(self, ok: bool, message: str) (L1794): _on_task.
- method ComponentStorePage._delete_leftovers(self) (L1805): _delete_leftovers.
- method ComponentStorePage._on_deleted(self, freed: int, removed: int, blocked: int) (L1837): _on_deleted.
- method ComponentStorePage._fail(self, msg: str) (L1849): _fail.

## src/cortex_unified/ui/premium/apex_tools_pages.py — Cortex Cleaner & NexusExplorer — Apex Enterprise Power Tools Pages.
- func _fmt_bytes(b: int) (L61): Format a byte count into a human-readable B/KB/MB/GB string.
- func _PrimaryButton(text: str, parent=None) (L72): Create a QPushButton styled as the primary (accented) action button.
- func _SecondaryButton(text: str, parent=None) (L80): Create a QPushButton styled as a secondary action button with a pointing-hand cursor.
- class DriverStoreCleanerPage(_Page) (L91): Page for enumerating, exporting, and deleting superseded driver packages.
- method DriverStoreCleanerPage.__init__(self, win: PremiumMainWindow) (L93): Build the Driver Store page with enumerate/export/delete buttons and a drivers table.
- method DriverStoreCleanerPage._on_scan(self) (L135): Enumerate driver packages on the worker runtime.
- func DriverStoreCleanerPage._on_scan._work() (L140): Enumerate third-party driver packages.
- func DriverStoreCleanerPage._on_scan._done(drivers: List[DriverPackage]) (L144): Fill the drivers table and flag superseded packages.
- method DriverStoreCleanerPage._on_export(self) (L162): Pick a folder and export all drivers into it.
- method DriverStoreCleanerPage._on_delete_superseded(self) (L172): Confirm and force-delete all superseded driver packages, then rescan.
- class ShellbagsCleanerPage(_Page) (L198): Page for purging Shellbags, Recent Items, and JumpLists activity traces.
- method ShellbagsCleanerPage.__init__(self, win: PremiumMainWindow) (L200): Build the Shellbags page with scan/clean buttons and a traces table.
- method ShellbagsCleanerPage._on_scan(self) (L236): Scan shell activity traces on the worker runtime.
- func ShellbagsCleanerPage._on_scan._work() (L241): Scan Shellbag, Recent Items, and JumpLists activity.
- func ShellbagsCleanerPage._on_scan._done(targets: List[ShellbagsTarget]) (L245): Fill the traces table with category, location, count, and size.
- method ShellbagsCleanerPage._on_clean(self) (L258): Confirm and purge all discovered activity traces, then rescan.
- class PowerPlanOptimizerPage(_Page) (L279): Page for unlocking Ultimate Performance and reducing the hibernation footprint.
- method PowerPlanOptimizerPage.__init__(self, win: PremiumMainWindow) (L281): Build the Power Plan page with status line, refresh/unlock/hibernate buttons, and a schemes table.
- method PowerPlanOptimizerPage._refresh(self) (L323): Refresh the active scheme status and the power plans table.
- method PowerPlanOptimizerPage._on_unlock_ultimate(self) (L340): Unlock the hidden Ultimate Performance power plan, then refresh.
- method PowerPlanOptimizerPage._on_reduce_hiber(self) (L349): Shrink the hibernation file to 40% of RAM, then refresh.
- class HostsFileManagerPage(_Page) (L363): Page for inspecting the hosts file and applying an anti-telemetry shield.
- method HostsFileManagerPage.__init__(self, win: PremiumMainWindow) (L365): Build the Hosts page with reload/shield buttons and an entries table.
- method HostsFileManagerPage._on_load(self) (L400): Parse the hosts file and list its entries.
- method HostsFileManagerPage._on_apply_shield(self) (L410): Confirm and add telemetry blocking entries to the hosts file, then reload.
- class NotificationCleanerPage(_Page) (L430): Page for purging the Action Center notification database and badge caches.
- method NotificationCleanerPage.__init__(self, win: PremiumMainWindow) (L432): Build the Notification Cleaner page with status line and refresh/clean buttons.
- method NotificationCleanerPage._refresh(self) (L461): Refresh the notification database paths and sizes.
- method NotificationCleanerPage._on_clean(self) (L471): Confirm and purge notification history and badges, then refresh.
- class FileSignatureSnifferPage(_Page) (L491): Page for detecting spoofed file extensions via magic-byte sniffing.
- method FileSignatureSnifferPage.__init__(self, win: PremiumMainWindow) (L493): Build the Signature Sniffer page with folder picker, spoof filter, and results table.
- method FileSignatureSnifferPage._on_choose_folder(self) (L533): Pick the directory to sniff.
- method FileSignatureSnifferPage._on_scan(self) (L539): Scan the chosen folder recursively for spoofed files.
- func FileSignatureSnifferPage._on_scan._work() (L544): Sniff file headers against known magic bytes.
- func FileSignatureSnifferPage._on_scan._done(results: List[SniffResult]) (L552): Fill the results table and flag spoofed extensions.
- class BinaryDifferPage(_Page) (L573): Page for byte-level comparison of two binary files.
- method BinaryDifferPage.__init__(self, win: PremiumMainWindow) (L575): Build the Binary Differ page with File A/B pickers, compare button, and a hex diff table.
- method BinaryDifferPage._on_select_a(self) (L628): Pick the first file to compare.
- method BinaryDifferPage._on_select_b(self) (L635): Pick the second file to compare.
- method BinaryDifferPage._on_diff(self) (L642): Compare the two chosen files in the background.
- func BinaryDifferPage._on_diff._work() (L651): Run the byte-level binary comparison.
- func BinaryDifferPage._on_diff._done(rep: BinaryDiffReport) (L655): Show similarity stats and list differing byte chunks.
- class UsnJournalPage(_Page) (L683): Page for querying the NTFS USN change journal of a volume.
- method UsnJournalPage.__init__(self, win: PremiumMainWindow) (L685): Build the USN Journal page with volume combo, query button, and an info label.
- method UsnJournalPage._on_query(self) (L716): Query the selected volume's USN journal and show its state.
- class Par2RecoveryPage(_Page) (L737): Page for inspecting PAR2 recovery sets and their protected files.
- method Par2RecoveryPage.__init__(self, win: PremiumMainWindow) (L739): Build the PAR2 page with an open button, summary label, and protected-files table.
- method Par2RecoveryPage._on_open_par2(self) (L772): Open and parse a .par2 file, listing its recovery set and protected files.
- class ImageOptimizerPage(_Page) (L800): Page for batch-compressing images and transcoding to WebP.
- method ImageOptimizerPage.__init__(self, win: PremiumMainWindow) (L802): Build the Image Optimizer page with picker, format/quality controls, and results table.
- method ImageOptimizerPage._on_add_images(self) (L858): Pick images to optimize and show the selection count.
- method ImageOptimizerPage._on_start(self) (L865): Run batch optimization with the chosen format and quality.
- func ImageOptimizerPage._on_start._work() (L877): Optimize the selected images in batch.
- func ImageOptimizerPage._on_start._done(summary: BatchOptimizeSummary) (L885): Fill the results table and report total bytes saved.

## src/cortex_unified/ui/premium/app.py — Premium GUI entry point (installed as the ``cortex-gui`` command).
- func log_dir() (L20): Return application log directory.
- func setup_logging(debug: bool=False) (L27): Configure root logging: console + rotating file. Returns the log path.
- func _install_qt_message_handler() (L60): Route Qt's internal warnings/errors into Python logging.
- func _install_qt_message_handler.handler(mode, context, message) (L76): handler.
- func _install_excepthook() (L83): _install_excepthook.
- func _install_excepthook.hook(exc_type, exc_value, exc_tb) (L85): hook.
- func _install_threading_excepthook() (L110): Log exceptions that kill worker threads.
- func _install_threading_excepthook.hook(args: threading.ExceptHookArgs) (L120): hook.
- func _schedule_update_check(win, settings=None) (L133): One background update check after the window settles - opt-in only.
- func _schedule_update_check._done() (L145): _done.
- func _set_windows_dpi_awareness() (L166): Make the process Per-Monitor-V2 DPI aware on Windows (no-op elsewhere).
- func _configure_high_dpi() (L224): Configure Qt high-DPI behaviour before the QApplication is constructed.
- func main() (L263): main.

## src/cortex_unified/ui/premium/audio_duplicates_page.py — Audio duplicate detection page – Chromaprint-inspired acoustic fingerprinting.
- class _AudioWorker(QObject) (L26): _AudioWorker class.
- method _AudioWorker.__init__(self, root: str, threshold: float=0.75) (L32): __init__.
- method _AudioWorker.cancel(self) (L41): cancel.
- method _AudioWorker.run(self) (L45): run.
- class AudioDuplicatesPage(_Page) (L60): Find acoustically-identical audio files (same recording, any encoding).
- method AudioDuplicatesPage.__init__(self, win) (L63): __init__.
- method AudioDuplicatesPage._pick(self) (L120): _pick.
- method AudioDuplicatesPage._run(self) (L129): _run.
- method AudioDuplicatesPage._on_progress(self, msg: str) (L140): _on_progress.
- method AudioDuplicatesPage._on_done(self, groups: dict) (L144): _on_done.
- method AudioDuplicatesPage._fail(self, msg) (L177): _fail.

## src/cortex_unified/ui/premium/backdrop.py — Optional native window backdrop (Windows 11 Mica/Acrylic).
- func _windows_build() (L46): Return the Windows build number, or 0 if it cannot be determined.
- func apply_backdrop(win) (L59): Apply a best-effort native system backdrop behind ``win``.

## src/cortex_unified/ui/premium/cdc_page.py — Content-Defined Chunking page – FastCDC / VectorCDC (FAST'25).
- class _CdcWorker(QObject) (L25): _CdcWorker class.
- method _CdcWorker.__init__(self, root: str, threshold: float=0.5) (L31): __init__.
- method _CdcWorker.cancel(self) (L40): cancel.
- method _CdcWorker.run(self) (L44): run.
- class CdcPage(_Page) (L59): Find shift-resistant near-duplicates via CDC chunk sets.
- method CdcPage.__init__(self, win) (L62): __init__.
- method CdcPage._pick(self) (L119): _pick.
- method CdcPage._run(self) (L128): _run.
- method CdcPage._on_progress(self, msg: str) (L139): _on_progress.
- method CdcPage._on_done(self, groups: dict) (L143): _on_done.
- method CdcPage._fail(self, msg) (L176): _fail.

## src/cortex_unified/ui/premium/cleanup_hub_page.py — Cleanup Hub: unified Storage Sense-style view of all cleanup categories.
- class HubScanWorker(QObject) (L48): Scans all cleanup categories via CleanerService.
- method HubScanWorker.__init__(self, max_risk: str='medium', include_disabled: bool=True) (L58): Store max-risk level, disabled-category flag, and a cancel event.
- method HubScanWorker.cancel(self) (L66): Request cooperative cancellation of the running scan.
- method HubScanWorker.run(self) (L70): Run the category scan and emit the report or a failure.
- func _risk_label(risk: RiskLevel) (L96): Return the display label ("LOW"/"MEDIUM"/"HIGH") for a risk level.
- func _risk_color(risk: RiskLevel) (L101): Return the badge hex color for a risk level.
- class CleanupHubPage(_Page) (L106): Storage Sense-style hub: every CleanupCategory as a card with estimates.
- method CleanupHubPage.__init__(self, win) (L109): Build the Cleanup Hub: scan controls, summary cards, and a card grid.
- method CleanupHubPage._scan(self) (L246): Disable buttons and start a HubScanWorker (risk level from opt-in checkbox).
- method CleanupHubPage._on_progress(self, msg: str) (L258): Show worker progress text in the scan status label.
- method CleanupHubPage._on_scanned(self, report) (L262): Update summary cards and rebuild the category card grid from the scan report.
- method CleanupHubPage._make_card(self, cat: CleanupCategory, est_bytes: int, est_files: int) (L315): Build one category card: risk/reversible badges, paths, globs, estimate, and select checkbox.
- func CleanupHubPage._make_card._on_toggled(checked, _cid=cid) (L372): Record the card's selection state and refresh the Clean button.
- method CleanupHubPage._select_all_cards(self, state: bool) (L382): Check or uncheck every category card checkbox at once.
- method CleanupHubPage._update_clean_enabled(self) (L389): Enable the Clean button only when something is selected and a scan has files.
- method CleanupHubPage._fail(self, msg: str) (L395): Reset UI state after a failed scan/clean and offer retry.
- method CleanupHubPage._pick_custom_folder(self) (L405): Add a chosen directory to the scan roots and rescan.
- method CleanupHubPage._pick_custom_file(self) (L415): Add the parent folder of a chosen file to the scan roots and rescan.
- method CleanupHubPage._clear_custom_roots(self) (L425): Remove all custom scan roots (back to system defaults) and rescan.
- method CleanupHubPage._update_roots_status(self) (L431): Refresh the active-scan-roots label and Reset Roots button visibility.
- method CleanupHubPage._clean(self) (L443): Confirm selection, then run CleanWorker on the selected categories (Recycle-Bin-safe delete).
- method CleanupHubPage._on_cleaned(self, freed: int, items: int, skipped: int) (L477): Report freed bytes and item counts after cleanup finishes.

## src/cortex_unified/ui/premium/cloud_storage_page.py — Cloud Storage Analyzer — S3, Azure, Google Drive, OneDrive, rclone.
- class _WorkerResult (L43): _WorkerResult class.
- class _CloudWorker(QObject) (L50): _CloudWorker class.
- method _CloudWorker.__init__(self, target: str, max_objects: int, include_versions: bool, include_delete_markers: bool) (L56): Initialize worker.
- method _CloudWorker.cancel(self) (L71): cancel.
- method _CloudWorker.run(self) (L75): run.
- class CloudStoragePage(_Page) (L90): Analyze cloud storage (S3, Azure, GDrive, OneDrive, rclone).
- method CloudStoragePage.__init__(self, win) (L93): __init__.
- method CloudStoragePage._build_summary_tab(self) (L182): _build_summary_tab.
- method CloudStoragePage._build_by_provider_tab(self) (L217): _build_by_provider_tab.
- method CloudStoragePage._build_by_class_tab(self) (L233): _build_by_class_tab.
- method CloudStoragePage._build_duplicates_tab(self) (L249): _build_duplicates_tab.
- method CloudStoragePage._refresh_targets(self) (L272): _refresh_targets.
- method CloudStoragePage._run(self) (L294): _run.
- method CloudStoragePage._on_progress(self, msg: str) (L323): _on_progress.
- method CloudStoragePage._on_done(self, result: _WorkerResult) (L327): _on_done.
- method CloudStoragePage._fail(self, msg: str) (L362): _fail.
- method CloudStoragePage._populate_summary(self, stats: CloudScanStats) (L369): _populate_summary.
- method CloudStoragePage._populate_by_provider(self, stats: CloudScanStats) (L399): _populate_by_provider.
- method CloudStoragePage._populate_by_class(self, stats: CloudScanStats) (L414): _populate_by_class.
- method CloudStoragePage._populate_duplicates(self, duplicates: list[DuplicateGroup]) (L456): _populate_duplicates.

## src/cortex_unified/ui/premium/compact_os_page.py — CompactOS / NTFS compression page – estimate, then compress only on demand.
- class _ScanWorker(QObject) (L35): _ScanWorker class.
- method _ScanWorker.__init__(self, root: str, min_mb: float) (L41): __init__.
- method _ScanWorker.cancel(self) (L50): cancel.
- method _ScanWorker.run(self) (L54): run.
- class _CompactWorker(QObject) (L67): _CompactWorker class.
- method _CompactWorker.__init__(self, path: str) (L72): __init__.
- method _CompactWorker.run(self) (L77): run.
- class _QueryWorker(QObject) (L88): _QueryWorker class.
- method _QueryWorker.run(self) (L93): run.
- class CompactOsPage(_Page) (L106): Estimate and apply NTFS compression to reclaim storage.
- method CompactOsPage.__init__(self, win) (L109): __init__.
- method CompactOsPage._pick(self) (L190): _pick.
- method CompactOsPage._query(self) (L199): _query.
- method CompactOsPage._on_query(self, info: dict) (L205): _on_query.
- method CompactOsPage._scan(self) (L213): _scan.
- method CompactOsPage._on_progress(self, msg: str) (L223): _on_progress.
- method CompactOsPage._on_done(self, ests: list) (L227): _on_done.
- method CompactOsPage._compress(self) (L251): _compress.
- method CompactOsPage._compact_done(self, success: bool, message: str) (L273): _compact_done.
- method CompactOsPage._fail(self, msg: str) (L283): _fail.

## src/cortex_unified/ui/premium/device_window.py — Per-device deep scan worker and the premium device detail window.
- func _severity_badge_kind(severity: str) (L68): Map a finding severity string to its badge kind.
- class DeviceDeepScanWorker(QObject) (L73): Audit one authorized private host and gather its evidence.
- method DeviceDeepScanWorker.__init__(self, device, networks, profile='advanced', custom_ports=(), nmap_modes=None, catalog_path=None) (L80): Store the device snapshot, authorized networks, and scan options for the worker.
- method DeviceDeepScanWorker.cancel(self) (L107): Request cancellation of the running scan.
- method DeviceDeepScanWorker._say(self, message: str) (L111): Emit a progress message.
- method DeviceDeepScanWorker.run(self) (L115): Re-check authorization, scan services, fingerprint, audit, and emit the evidence payload.
- method DeviceDeepScanWorker._run_nmap(self, observations, notes) (L219): Optionally verify observed TCP ports with local Nmap; merge new observations.
- method DeviceDeepScanWorker._ping(self) (L273): Ping the device twice and return the reachability dict.
- method DeviceDeepScanWorker._reverse_dns(self) (L287): Resolve the device IP to a hostname.
- method DeviceDeepScanWorker._history(self, device) (L295): Load inventory metadata, lifetime, and exposure trends for the device.
- class DevicePingWorker(QObject) (L327): Run only a scope-checked ICMP reachability check for one device.
- method DevicePingWorker.__init__(self, ip: str, networks) (L334): Store the target IP, authorized networks, and cancel event.
- method DevicePingWorker.cancel(self) (L341): Request cancellation of the ping check.
- method DevicePingWorker.run(self) (L345): Re-check authorization and emit an ICMP reachability result.
- class DeviceDetailWindow(QDialog) (L379): One premium window with every observation Cortex has for one device.
- method DeviceDetailWindow.__init__(self, win, device, networks, catalog_path=None, parent=None) (L384): Build the non-modal device window with header, actions, stat cards, and evidence tabs.
- method DeviceDetailWindow._build_header(self) (L431): Create the device header card with name, identity line, and badges.
- method DeviceDetailWindow._header_badges(self) (L458): Derive header badges for router/self/randomized-MAC/kind flags.
- method DeviceDetailWindow._build_actions(self) (L473): Create the primary action row and the collapsible More Actions panel.
- method DeviceDetailWindow._toggle_more_actions(self, visible: bool) (L561): Show or hide the secondary action panel and restyle the disclosure button.
- method DeviceDetailWindow._build_cards(self) (L571): Create the five stat cards (services, findings, risk, latency, identity).
- method DeviceDetailWindow._build_tabs(self) (L592): Create the tab widget with overview, services, findings, identity, discovery, history, labels, and raw evidence.
- method DeviceDetailWindow._table(self, headers: list[str], stretch: tuple[int, ...]=()) (L669): Create styled table widget.
- method DeviceDetailWindow.start_scan(self, profile: str='advanced') (L691): Launch a DeviceDeepScanWorker with the chosen Nmap mode and profile.
- method DeviceDetailWindow._confirm_all_ports(self) (L716): Confirm a deep 1-65535 TCP scan before starting it.
- method DeviceDetailWindow._cancel(self) (L729): Ask the active worker to cancel and show a cancelling note.
- method DeviceDetailWindow._busy(self, busy: bool) (L735): Track busy state and refresh action availability.
- method DeviceDetailWindow._refresh_action_states(self) (L740): Derive every action from worker, evidence, and device capability.
- method DeviceDetailWindow._on_failed(self, message: str) (L787): Clear the worker, handle a pending close, and show the failure.
- method DeviceDetailWindow._ping_only(self) (L797): Launch a DevicePingWorker for a quick reachability check.
- method DeviceDetailWindow._on_pinged(self, ping: dict) (L811): Fold the ping result into the payload and describe the outcome.
- method DeviceDetailWindow._finish_pending_close(self) (L834): Close the window now that the worker has finished.
- method DeviceDetailWindow._render_known(self) (L841): Show what discovery already observed, before any focused scan.
- method DeviceDetailWindow._on_scanned(self, payload) (L874): Store the scan payload, render it, and summarize the results.
- method DeviceDetailWindow._render(self, payload: dict, scanned: bool) (L892): Populate every tab, the raw JSON view, and action states from the payload.
- method DeviceDetailWindow._render_cards(self, payload, services, findings, scanned) (L907): Update the stat cards for services, findings, severity, latency, and identity.
- method DeviceDetailWindow._render_overview(self, payload, services, findings, scanned) (L930): Rebuild the overview grid rows and the evidence caveat.
- method DeviceDetailWindow._render_services(self, services) (L1001): Fill the ports/services table sorted by port and transport.
- method DeviceDetailWindow._render_findings(self, findings, scanned) (L1036): Fill the security findings table with severity badges and remediation.
- method DeviceDetailWindow._render_identity(self, fingerprint) (L1068): Fill the identity evidence table from the fingerprint.
- method DeviceDetailWindow._render_discovery(self, payload) (L1085): Write discovery methods and self-advertised services to the Discovery tab.
- method DeviceDetailWindow._render_history(self, payload) (L1115): Write lifetime, history, and exposure-trend lines to the History tab.
- method DeviceDetailWindow._load_metadata(self) (L1157): Load saved labels and notes for the device into the form and overview.
- method DeviceDetailWindow._save_metadata(self) (L1179): Save the edited name, trust, tags, and notes to the inventory.
- method DeviceDetailWindow._wake(self) (L1203): Send a Wake-on-LAN magic packet to the device's subnet broadcast.
- method DeviceDetailWindow._open_service(self) (L1229): Open the best http/https/ssh/rdp service in the system handler.
- method DeviceDetailWindow._copy_identity(self) (L1251): Copy the device IP and MAC to the clipboard.
- method DeviceDetailWindow._export(self) (L1260): Export the current payload as a JSON, HTML, or PDF report.
- method DeviceDetailWindow._html_report(self, payload: dict) (L1301): Build the printable HTML report for the payload.
- method DeviceDetailWindow.closeEvent(self, event) (L1353): Hide now, then delete only after an active worker finishes.

## src/cortex_unified/ui/premium/directstorage_page.py — Windows 11 DirectStorage & BypassIO Hardware Acceleration Page.
- class _DirectStorageWorker(QObject) (L34): _DirectStorageWorker class.
- method _DirectStorageWorker.__init__(self, optimizer: DirectStorageOptimizer) (L38): __init__.
- method _DirectStorageWorker.run_audit(self) (L43): run_audit.
- class DirectStorageOptimizerPage(_Page) (L49): UI diagnostics page for DirectStorage BypassIO hardware acceleration.
- method DirectStorageOptimizerPage.__init__(self, win) (L52): __init__.
- method DirectStorageOptimizerPage._start_audit(self) (L117): _start_audit.
- method DirectStorageOptimizerPage._on_audit_finished(self, report: DirectStorageAuditReport) (L130): _on_audit_finished.

## src/cortex_unified/ui/premium/disk_analyzer_page.py — Advanced Disk Analyzer page — MFT fast scan, treemap, deep folder breakdown.
- class _ScanWorker(QObject) (L42): Background worker: scans a path via AdvancedDiskAnalyzer.scan_sync.
- method _ScanWorker.__init__(self, root: str, max_depth: int=3) (L49): __init__.
- method _ScanWorker.cancel(self) (L56): cancel.
- method _ScanWorker.run(self) (L60): run.
- func _ScanWorker.run._cb(scanned_files: int, scanned_bytes: int, current: str) (L68): _cb.
- func _discover_fixed_drives() (L100): Return ``[(letter, label)]`` for every existing fixed drive letter.
- func _compute_depth(node, target_path: str) (L127): Walk the tree to find the depth of *target_path*.
- class DiskAnalyzerPage(_Page) (L138): Advanced disk analyzer: fast scan, treemap, folder breakdown by size.
- method DiskAnalyzerPage.__init__(self, win) (L141): __init__.
- method DiskAnalyzerPage._populate_drives(self) (L261): _populate_drives.
- method DiskAnalyzerPage._on_drive_changed(self, idx: int) (L270): _on_drive_changed.
- method DiskAnalyzerPage._browse(self) (L277): _browse.
- method DiskAnalyzerPage._run(self) (L290): _run.
- method DiskAnalyzerPage._on_progress(self, msg: str) (L309): _on_progress.
- method DiskAnalyzerPage._on_done(self, result) (L313): _on_done.
- method DiskAnalyzerPage._fail(self, msg: str) (L399): _fail.

## src/cortex_unified/ui/premium/driver_manager_page.py — Driver Manager page — scan, update, backup and clean device drivers.
- class _ScanWorker(QObject) (L56): Enumerate devices and check for driver updates.
- method _ScanWorker.__init__(self, offline_mode: bool=False, index_path: str | None=None) (L63): Store offline-mode flag, optional index path, and a cancel event.
- method _ScanWorker.cancel(self) (L70): Request cooperative cancellation of the running scan.
- method _ScanWorker.run(self) (L74): Enumerate PnP devices via DriverManager and emit the driver list.
- class _InstallWorker(QObject) (L92): Install driver updates for selected hardware IDs.
- method _InstallWorker.__init__(self, hardware_ids: list[str], offline_mode: bool=False) (L99): Store target hardware IDs, offline flag, and a cancel event.
- method _InstallWorker.cancel(self) (L106): Request cooperative cancellation of the running install.
- method _InstallWorker.run(self) (L110): Install updates for the stored hardware IDs (restore point first).
- class _BackupWorker(QObject) (L127): Back up all current drivers via DISM export.
- method _BackupWorker.__init__(self) (L134): Create the backup worker with a fresh cancel event.
- method _BackupWorker.cancel(self) (L139): No-op cancel hook (DISM export cannot be interrupted).
- method _BackupWorker.run(self) (L143): Export all drivers via DISM into ~/CortexBackups/drivers.
- class DriverManagerPage(_Page) (L175): Scan, update, backup and manage device drivers.
- method DriverManagerPage.__init__(self, win) (L178): Build the Driver Manager page: filter, action buttons, progress, and results table.
- method DriverManagerPage._selected_hwids(self) (L268): Return hardware IDs of the currently selected table rows.
- method DriverManagerPage._populate_table(self, drivers: list) (L273): Fill the results table (class-filtered), flag outdated/missing, and enable Install if any outdated.
- method DriverManagerPage._scan(self) (L310): Clear the table and start a _ScanWorker for devices and update checks.
- method DriverManagerPage._on_progress(self, msg: str) (L327): Show worker progress text in the status label.
- method DriverManagerPage._on_scan_done(self, drivers: list) (L331): Populate the table with scan results and summarize outdated/missing counts.
- method DriverManagerPage._on_scan_fail(self, msg: str) (L356): Reset buttons and show the scan error with a retry option.
- method DriverManagerPage._install(self) (L363): Confirm selection, then run _InstallWorker for the selected hardware IDs.
- method DriverManagerPage._on_install_done(self, results: dict) (L399): Report per-ID success/failure counts and show errors if any install failed.
- method DriverManagerPage._on_install_fail(self, msg: str) (L420): Reset buttons and show the install error with a retry option.
- method DriverManagerPage._backup(self) (L428): Disable Backup and run _BackupWorker to DISM-export all drivers.
- method DriverManagerPage._on_backup_done(self, path: str) (L440): Re-enable Backup and report the export directory.
- method DriverManagerPage._on_backup_fail(self, msg: str) (L448): Re-enable Backup and show the export error with a retry option.

## src/cortex_unified/ui/premium/enterprise_suite_pages.py — Cortex Cleaner & NexusExplorer — Enterprise Next-Gen Suite GUI Pages.
- func _fmt_bytes(b: int) (L53): Format a byte count into a human-readable B/KB/MB/GB string.
- func _PrimaryButton(text: str, parent=None) (L64): Create a QPushButton styled as the primary (accented) action button.
- func _SecondaryButton(text: str, parent=None) (L72): Create a QPushButton styled as a secondary action button with a pointing-hand cursor.
- func _run_task(win: PremiumMainWindow, work_fn, done_fn, err_fn=None) (L79): Run work_fn on the window's worker runtime, or inline as a fallback, dispatching to done_fn / err_fn.
- class VssManagerPage(_Page) (L96): Page for auditing VSS shadow copies, creating snapshots, and purging the oldest shadow.
- method VssManagerPage.__init__(self, win: PremiumMainWindow) (L98): Build the VSS page with audit/create/purge buttons, summary label, and shadows table.
- method VssManagerPage._on_audit(self) (L138): Start an asynchronous VSS audit and show a busy message in the summary label.
- method VssManagerPage._on_audit_done(self, rep: VssAuditReport) (L143): Populate the shadows table and summary from a VssAuditReport.
- method VssManagerPage._on_create(self) (L159): Kick off creation of a recovery shadow copy on C: in the background.
- method VssManagerPage._on_purge(self) (L164): Kick off deletion of the oldest shadow copy on C: in the background.
- method VssManagerPage._on_action_done(self, res: tuple[bool, str]) (L169): Show the result message of a create/purge action, then refresh the audit.
- method VssManagerPage._on_err(self, exc) (L175): Show an error message from a failed worker in the summary label.
- class DevDriveOptimizerPage(_Page) (L184): Page for auditing ReFS Dev Drives, block-cloning support, and Defender performance mode.
- method DevDriveOptimizerPage.__init__(self, win: PremiumMainWindow) (L186): Build the Dev Drive page with an audit button, summary label, and drives table.
- method DevDriveOptimizerPage._on_audit(self) (L220): Start an asynchronous storage-drive audit and update the summary label.
- method DevDriveOptimizerPage._on_audit_done(self, rep: DevDriveAuditReport) (L225): Fill the drives table and summary from a DevDriveAuditReport.
- method DevDriveOptimizerPage._on_err(self, exc) (L244): Show an error message from a failed worker in the summary label.
- class BitLockerAuditorPage(_Page) (L253): Page for auditing volume BitLocker protection, cipher strength, and key protectors.
- method BitLockerAuditorPage.__init__(self, win: PremiumMainWindow) (L255): Build the BitLocker page with an audit button, summary label, and volumes table.
- method BitLockerAuditorPage._on_audit(self) (L289): Start an asynchronous BitLocker audit and update the summary label.
- method BitLockerAuditorPage._on_audit_done(self, rep: BitLockerAuditReport) (L294): Fill the volumes table and compliance summary from a BitLockerAuditReport.
- method BitLockerAuditorPage._on_err(self, exc) (L312): Show an error message from a failed worker in the summary label.
- class JunctionAuditorPage(_Page) (L321): Page for scanning NTFS junctions, symlinks, dead links, and circular reparse traps.
- method JunctionAuditorPage.__init__(self, win: PremiumMainWindow) (L323): Build the Junction Auditor page with scan/custom/unlink buttons and a links table.
- method JunctionAuditorPage._on_scan(self) (L364): Scan reparse points across the user profile in the background.
- method JunctionAuditorPage._on_custom(self) (L369): Prompt for a folder and scan its reparse points in the background.
- method JunctionAuditorPage._on_scan_done(self, rep: JunctionAuditReport) (L376): Fill the links table and counters from a JunctionAuditReport.
- method JunctionAuditorPage._on_clean_dead(self) (L394): Unlink the dead junction selected in the table, then rescan.
- method JunctionAuditorPage._on_err(self, exc) (L405): Show an error message from a failed worker in the summary label.
- class BitRotScrubberPage(_Page) (L414): Page for detecting silent bit-rot by comparing files against a SHA-256 baseline.
- method BitRotScrubberPage.__init__(self, win: PremiumMainWindow) (L416): Build the BitRot page with a target picker, scrub button, and corrupted-files table.
- method BitRotScrubberPage._on_browse(self) (L454): Open a directory picker and set it as the scrub target.
- method BitRotScrubberPage._on_scrub(self) (L460): Hash and scrub the chosen folder in the background.
- method BitRotScrubberPage._on_scrub_done(self, rep: BitRotScrubReport) (L468): Show scrub statistics and list corrupted files from a BitRotScrubReport.
- method BitRotScrubberPage._on_err(self, exc) (L484): Show an error message from a failed worker in the summary label.
- class MemoryCompressionPage(_Page) (L493): Page for auditing Windows memory compression and toggling it on or off.
- method MemoryCompressionPage.__init__(self, win: PremiumMainWindow) (L495): Build the Memory Compression page with audit/toggle buttons and a metrics table.
- method MemoryCompressionPage._on_audit(self) (L530): Query MMAgent memory status in the background.
- method MemoryCompressionPage._on_audit_done(self, rep: MemoryTunerReport) (L535): Fill the metrics table from a MemoryTunerReport and remember the current status.
- method MemoryCompressionPage._on_toggle(self) (L561): Flip the memory-compression state to the opposite of the audited status.
- method MemoryCompressionPage._on_toggle_done(self, res: tuple[bool, str]) (L569): Report the toggle result, then re-run the audit.
- method MemoryCompressionPage._on_err(self, exc) (L575): Show an error message from a failed worker in the summary label.
- class SandboxCleanerPage(_Page) (L584): Page for finding and purging Windows Sandbox, Hyper-V, and WSL2 artifacts.
- method SandboxCleanerPage.__init__(self, win: PremiumMainWindow) (L586): Build the Sandbox Cleaner page with scan/clean buttons and an artifacts table.
- method SandboxCleanerPage._on_scan(self) (L624): Scan for discarded virtualization artifacts in the background.
- method SandboxCleanerPage._on_scan_done(self, rep: SandboxCleanReport) (L629): Cache the artifact list and fill the table from a SandboxCleanReport.
- method SandboxCleanerPage._on_clean(self) (L643): Purge every artifact flagged safe to clean; warn when none exist.
- method SandboxCleanerPage._on_clean_done(self, res: tuple[int, list[str]]) (L653): Report reclaimed bytes, then rescan for remaining artifacts.
- method SandboxCleanerPage._on_err(self, exc) (L659): Show an error message from a failed worker in the summary label.
- class SmbShareAuditorPage(_Page) (L668): Page for auditing local SMB shares, admin shares, and SMBv1 exposure.
- method SmbShareAuditorPage.__init__(self, win: PremiumMainWindow) (L670): Build the SMB Auditor page with an audit button, summary label, and shares table.
- method SmbShareAuditorPage._on_audit(self) (L703): Start an asynchronous SMB share audit and update the summary label.
- method SmbShareAuditorPage._on_audit_done(self, rep: SmbSecurityReport) (L708): Fill the shares table and risk summary from a SmbSecurityReport.
- method SmbShareAuditorPage._on_err(self, exc) (L726): Show an error message from a failed worker in the summary label.
- class ProcessTokenPage(_Page) (L735): Page for inspecting process token integrity levels, elevation, and privileges.
- method ProcessTokenPage.__init__(self, win: PremiumMainWindow) (L737): Build the Process Token page with an audit button, summary label, and processes table.
- method ProcessTokenPage._on_audit(self) (L771): Start an asynchronous process token audit and update the summary label.
- method ProcessTokenPage._on_audit_done(self, rep: ProcessTokenAuditReport) (L776): Fill the processes table and privilege summary from a ProcessTokenAuditReport.
- method ProcessTokenPage._on_err(self, exc) (L794): Show an error message from a failed worker in the summary label.
- class StorageGrowthTrackerPage(_Page) (L803): Page for taking directory snapshots and diffing storage growth between them.
- method StorageGrowthTrackerPage.__init__(self, win: PremiumMainWindow) (L805): Build the Growth Tracker page with path picker, snapshot/diff buttons, and a growth table.
- method StorageGrowthTrackerPage._on_browse(self) (L848): Open a directory picker and set it as the snapshot target.
- method StorageGrowthTrackerPage._on_snapshot(self) (L854): Capture a storage snapshot of the entered path in the background.
- method StorageGrowthTrackerPage._on_snapshot_done(self, s: SnapshotSummary) (L862): Show the captured snapshot id, label, and total footprint.
- method StorageGrowthTrackerPage._on_diff(self) (L868): Compare the two most recent snapshots, or prompt if fewer exist.
- method StorageGrowthTrackerPage._on_diff_done(self, rep: StorageGrowthDiffReport) (L880): Show net growth between snapshots and list the fastest-growing directories.
- method StorageGrowthTrackerPage._on_err(self, exc) (L898): Show an error message from a failed worker in the summary label.

## src/cortex_unified/ui/premium/expanded_tools_pages.py — Cortex Cleaner & NexusExplorer — Expanded Enterprise Power Tools Pages.
- func PrimaryButton(text: str, parent=None) (L48): Create a QPushButton styled as the primary (accented) action button.
- func SecondaryButton(text: str, parent=None) (L55): Create a QPushButton styled as a secondary action button with a pointing-hand cursor.
- func _fmt_bytes(b: int) (L74): Format bytes into human-readable string.
- class LinksManagerPage(_Page) (L89): Page for scanning and safely removing NTFS junctions, symlinks, and hardlinks.
- method LinksManagerPage.__init__(self, win: PremiumMainWindow) (L91): Build the Links Manager page with folder picker, recursive option, and links table.
- method LinksManagerPage._on_choose_folder(self) (L142): Open a directory picker and remember it as the scan target.
- method LinksManagerPage._on_scan(self) (L149): Scan the chosen directory (or home) for links on the worker runtime.
- func LinksManagerPage._on_scan._work() (L155): Scan the target directory for links, optionally recursive.
- func LinksManagerPage._on_scan._done(items: List[LinkItem]) (L159): Fill the links table with name, type, target, validity, and size.
- method LinksManagerPage._on_remove_link(self) (L176): Confirm and remove the selected link without touching its target files.
- class FastCopierPage(_Page) (L202): Page for high-throughput multi-threaded file transfer with verification modes.
- method FastCopierPage.__init__(self, win: PremiumMainWindow) (L204): Build the Fast Copier page with source/destination pickers, mode combo, and progress bar.
- method FastCopierPage._on_add_source(self) (L273): Append a picked source directory to the copy list.
- method FastCopierPage._on_choose_dest(self) (L280): Pick the destination directory for the batch copy.
- method FastCopierPage._on_start_copy(self) (L287): Run the batch copy in the background with the chosen mode and speed limit.
- func FastCopierPage._on_start_copy._work() (L304): Copy all selected sources to the destination via FastCopier.copy_batch.
- func FastCopierPage._on_start_copy._done(summary: CopySummary) (L313): Report transfer statistics or the first copy errors.
- class TimestampTouchPage(_Page) (L333): Page for inspecting and stomping MACB timestamps and Win32 file attributes.
- method TimestampTouchPage.__init__(self, win: PremiumMainWindow) (L335): Build the Timestamp Touch page with file picker, datetime editors, and attribute checkboxes.
- method TimestampTouchPage._on_choose_files(self) (L417): Pick files and preload the first file's timestamps and attributes into the editors.
- method TimestampTouchPage._on_apply(self) (L434): Apply the chosen timestamps and attributes to every selected file.
- class ArchiveManagerPage(_Page) (L460): Page for creating, inspecting, testing, and extracting multi-format archives.
- method ArchiveManagerPage.__init__(self, win: PremiumMainWindow) (L462): Build the Archive Studio page with open/test/extract/create buttons and a contents table.
- method ArchiveManagerPage._on_open_archive(self) (L511): Open an archive and list its entries in the table.
- method ArchiveManagerPage._on_test_archive(self) (L525): Run an integrity test on the currently opened archive.
- method ArchiveManagerPage._on_extract_archive(self) (L537): Extract the opened archive into a chosen destination folder.
- method ArchiveManagerPage._on_create_archive(self) (L551): Pick files and a target name, then build a new archive.
- class PrefetchAnalyzerPage(_Page) (L571): Page for analyzing and flushing Windows Prefetch execution traces.
- method PrefetchAnalyzerPage.__init__(self, win: PremiumMainWindow) (L573): Build the Prefetch page with status line, scan/clean buttons, and a traces table.
- method PrefetchAnalyzerPage._refresh_status(self) (L613): Refresh the prefetch cache size, SysMain state, and privilege line.
- method PrefetchAnalyzerPage._on_scan(self) (L622): Scan prefetch trace files on the worker runtime.
- func PrefetchAnalyzerPage._on_scan._work() (L627): Scan the Prefetch directory for trace entries.
- func PrefetchAnalyzerPage._on_scan._done(entries: List[PrefetchEntry]) (L631): Fill the traces table with executables, hashes, sizes, and last-run times.
- method PrefetchAnalyzerPage._on_clean(self) (L645): Confirm and flush all prefetch traces, then rescan.
- class SearchIndexOptimizerPage(_Page) (L662): Page for compacting and rebuilding the Windows Search index database.
- method SearchIndexOptimizerPage.__init__(self, win: PremiumMainWindow) (L664): Build the Search Index page with status card and compact/rebuild buttons.
- method SearchIndexOptimizerPage._refresh(self) (L699): Refresh the database path, size, item estimate, and service status.
- method SearchIndexOptimizerPage._on_compact(self) (L710): Confirm and run offline ESENT compaction in the background.
- func SearchIndexOptimizerPage._on_compact._work() (L720): Stop WSearch and compact the Windows.edb database.
- func SearchIndexOptimizerPage._on_compact._done(res) (L724): Report compaction outcome and refresh the metrics.
- method SearchIndexOptimizerPage._on_rebuild(self) (L735): Confirm and trigger a full search-index rebuild.
- class DnsBenchmarkPage(_Page) (L752): Page for benchmarking DNS provider latency and applying the chosen resolver.
- method DnsBenchmarkPage.__init__(self, win: PremiumMainWindow) (L754): Build the DNS Benchmark page with run/apply buttons and a results table.
- method DnsBenchmarkPage._on_benchmark(self) (L792): Run the full DNS benchmark on the worker runtime.
- func DnsBenchmarkPage._on_benchmark._work() (L797): Benchmark all known DNS providers.
- func DnsBenchmarkPage._on_benchmark._done(results: List[DnsBenchmarkResult]) (L801): Fill the results table and highlight the fastest provider.
- method DnsBenchmarkPage._on_apply_dns(self) (L820): Apply the selected provider's DNS servers to Wi-Fi, falling back to Ethernet.
- class DiskBenchmarkPage(_Page) (L843): Page for measuring sequential throughput and 4K random IOPS.
- method DiskBenchmarkPage.__init__(self, win: PremiumMainWindow) (L845): Build the Disk Benchmark page with target picker, progress label, and results table.
- method DiskBenchmarkPage._on_select_target(self) (L895): Pick the drive or folder to benchmark.
- method DiskBenchmarkPage._on_start_bench(self) (L902): Run a 64 MB storage benchmark on the target in the background.
- func DiskBenchmarkPage._on_start_bench._work() (L907): Run the disk benchmark engine on the target path.
- func DiskBenchmarkPage._on_start_bench._done(report: DiskBenchmarkReport) (L911): Populate throughput and IOPS results for the four test profiles.
- class MemoryOptimizerPage(_Page) (L929): Page for inspecting RAM usage and trimming process working sets.
- method MemoryOptimizerPage.__init__(self, win: PremiumMainWindow) (L931): Build the RAM Optimizer page with summary line, process table, and trim button.
- method MemoryOptimizerPage._on_refresh(self) (L969): Refresh the RAM summary and top-30 process memory table.
- method MemoryOptimizerPage._on_trim(self) (L986): Trim background process working sets, then refresh.
- class DevCleanerPage(_Page) (L997): Page for scanning and purging developer ecosystem build caches.
- method DevCleanerPage.__init__(self, win: PremiumMainWindow) (L999): Build the Dev Cleaner page with scan/clean buttons and a caches table.
- method DevCleanerPage._on_scan(self) (L1035): Scan developer caches on the worker runtime.
- func DevCleanerPage._on_scan._work() (L1040): Scan for Docker, Python, Node, Rust, Gradle, Go, and NuGet caches.
- func DevCleanerPage._on_scan._done(items: List[DevCacheItem]) (L1044): Fill the caches table with ecosystem, name, size, and description.
- method DevCleanerPage._on_clean(self) (L1057): Confirm and purge all discovered caches, then rescan.
- class BrowserDeepCleanerPage(_Page) (L1078): Page for scanning and purging caches across installed browsers.
- method BrowserDeepCleanerPage.__init__(self, win: PremiumMainWindow) (L1080): Build the Browser Cleaner page with scan/clean buttons and a targets table.
- method BrowserDeepCleanerPage._on_scan(self) (L1116): Scan browser caches on the worker runtime.
- func BrowserDeepCleanerPage._on_scan._work() (L1121): Scan installed browser profiles for cache and storage sizes.
- func BrowserDeepCleanerPage._on_scan._done(targets: List[BrowserTarget]) (L1125): Fill the targets table with browser, category, size, and path.
- method BrowserDeepCleanerPage._on_clean(self) (L1138): Confirm and purge transient browser caches (logins preserved), then rescan.

## src/cortex_unified/ui/premium/focus.py — Focus-visible: show keyboard focus rings only for keyboard navigation.
- class FocusVisibleFilter(QObject) (L43): App-level filter that gates focus rings on the input modality.
- method FocusVisibleFilter.__init__(self, app: QApplication) (L46): __init__.
- method FocusVisibleFilter.eventFilter(self, obj, event) (L52): eventFilter.
- method FocusVisibleFilter._set_visible(obj, visible: bool) (L76): _set_visible.
- func install_focus_visible(app: QApplication) (L91): Install the focus-visible filter on *app* once (idempotent).

## src/cortex_unified/ui/premium/fuzzy_hash_page.py — Fuzzy hash page – ssdeep-style CTPH for *close-but-different* binaries.
- class _FuzzyWorker(QObject) (L26): _FuzzyWorker class.
- method _FuzzyWorker.__init__(self, root: str, threshold: float=60.0) (L32): __init__.
- method _FuzzyWorker.cancel(self) (L41): cancel.
- method _FuzzyWorker.run(self) (L45): run.
- class FuzzyHashPage(_Page) (L60): Find near-identical binaries via context-triggered piecewise hashing.
- method FuzzyHashPage.__init__(self, win) (L63): __init__.
- method FuzzyHashPage._pick(self) (L119): _pick.
- method FuzzyHashPage._run(self) (L128): _run.
- method FuzzyHashPage._on_progress(self, msg: str) (L139): _on_progress.
- method FuzzyHashPage._on_done(self, groups: dict) (L143): _on_done.
- method FuzzyHashPage._fail(self, msg) (L176): _fail.

## src/cortex_unified/ui/premium/icons.py — Crisp, theme-tinted SVG icons.
- func _svg_source(name: str) (L56): Read an icon's SVG markup, or ``None`` when it is not shipped.
- func _render(name: str, size: int, color: str, dpr_x100: int) (L67): Rasterise *name* at *size* logical px for a given device pixel ratio.
- func _device_pixel_ratio() (L119): Best-effort device pixel ratio of the active screen.
- func pixmap(name: str, size: int=DESIGN_SIZE, color: str='#FFFFFF') (L133): Return a crisp pixmap for *name*, or an empty one when unavailable.
- func icon(name: str, size: int=DESIGN_SIZE, color: str='#FFFFFF') (L140): Return a :class:`QIcon` for *name* tinted to *color*.
- func available() (L160): Every icon name shipped with the application.
- func has_icon(name: str) (L168): True when *name* is shipped, without rendering it.
- func icon_size(size: int) (L173): Convenience square :class:`QSize` for ``setIconSize``.
- func clear_cache() (L178): Drop cached pixmaps - call after a theme or DPI change.
- func tinted_color(palette, *, muted: bool=False) (L184): Pick the right stroke colour for *palette* (a ``theme.Palette``).

## src/cortex_unified/ui/premium/license_page.py — License & Tiers page: current entitlement, offline activation, trial.
- class LicensePage(_Page) (L47): Show this machine's license state and manage its lifecycle.
- method LicensePage.__init__(self, win) (L50): __init__.
- method LicensePage._refresh(self) (L145): Project the live license state onto every control.
- method LicensePage._fill_table(self, state) (L180): One row per feature, grouped by minimum tier then name.
- method LicensePage._activate(self) (L198): Install the entered key. Bad input warns instead of crashing.
- method LicensePage._start_trial(self) (L219): Start the once-per-machine PRO trial.
- method LicensePage._deactivate(self) (L234): Remove the local license after an explicit confirmation.

## src/cortex_unified/ui/premium/log_sweeper_page.py — Log Sweeper: find huge *.log/*.txt across user-selected roots (D:\code).
- class _LogWorker(QObject) (L36): _LogWorker class.
- method _LogWorker.__init__(self, roots, min_mb=100.0) (L42): __init__.
- method _LogWorker.cancel(self) (L51): cancel.
- method _LogWorker.run(self) (L55): run.
- class LogSweeperPage(_Page) (L73): Find large logs outside the default cache roots.
- method LogSweeperPage.__init__(self, win) (L76): __init__.
- method LogSweeperPage._add_root(self) (L176): _add_root.
- method LogSweeperPage._discover_code_roots(self) (L186): Discover common code root directories across all fixed drives.
- method LogSweeperPage._select_code_root(self) (L214): Open folder picker to select a code root directory.
- method LogSweeperPage._rm_root(self) (L225): _rm_root.
- method LogSweeperPage._scan(self) (L231): _scan.
- method LogSweeperPage._on_progress(self, msg: str) (L247): _on_progress.
- method LogSweeperPage._on_done(self, results: list) (L251): _on_done.
- method LogSweeperPage._delete(self) (L279): _delete.
- method LogSweeperPage._on_deleted(self, freed: int, ok: int, blocked: int) (L309): _on_deleted.
- method LogSweeperPage._fail(self, msg: str) (L320): _fail.

## src/cortex_unified/ui/premium/memory_standby_page.py — Windows RAM Standby List & Working Set Kernel Purger Page.
- class MemoryStandbyPurgerPage(_Page) (L34): UI studio for Standby List and working set kernel optimization.
- method MemoryStandbyPurgerPage.__init__(self, win) (L37): __init__.
- method MemoryStandbyPurgerPage._refresh_stats(self) (L113): _refresh_stats.
- method MemoryStandbyPurgerPage._on_purge_standby(self) (L121): _on_purge_standby.
- method MemoryStandbyPurgerPage._on_empty_working_sets(self) (L126): _on_empty_working_sets.
- method MemoryStandbyPurgerPage._on_purge_modified(self) (L131): _on_purge_modified.
- method MemoryStandbyPurgerPage._on_purge_all(self) (L136): _on_purge_all.
- method MemoryStandbyPurgerPage._handle_result(self, res: PurgeResult) (L152): _handle_result.

## src/cortex_unified/ui/premium/mft_slack_page.py — NTFS Master File Table ($MFT) & Directory Index Slack Scrubber Page.
- class _MftScrubWorker(QObject) (L36): _MftScrubWorker class.
- method _MftScrubWorker.__init__(self, scrubber: MftSlackScrubber) (L41): __init__.
- method _MftScrubWorker.run_audit(self) (L46): run_audit.
- method _MftScrubWorker.run_scrub(self) (L51): run_scrub.
- class MftSlackScrubberPage(_Page) (L57): UI page for NTFS MFT record slack auditing and sanitization.
- method MftSlackScrubberPage.__init__(self, win) (L60): __init__.
- method MftSlackScrubberPage._on_volume_changed(self, vol: str) (L145): _on_volume_changed.
- method MftSlackScrubberPage._start_audit(self) (L154): _start_audit.
- method MftSlackScrubberPage._on_audit_finished(self, report: MftScrubReport) (L168): _on_audit_finished.
- method MftSlackScrubberPage._start_scrub(self) (L194): _start_scrub.
- method MftSlackScrubberPage._on_scrub_finished(self, report: MftScrubReport) (L218): _on_scrub_finished.

## src/cortex_unified/ui/premium/model_cache_page.py — Model Cache page – hardlink-aware HF hub / Ollama / LM Studio.
- class _ScanWorker(QObject) (L35): _ScanWorker class.
- method _ScanWorker.run(self) (L40): run.
- class _CleanOrphansWorker(QObject) (L50): _CleanOrphansWorker class.
- method _CleanOrphansWorker.__init__(self, dry_run: bool=True) (L55): __init__.
- method _CleanOrphansWorker.run(self) (L60): run.
- class ModelCachePage(_Page) (L71): Hardlink-aware model cache inventory + safe orphan cleanup.
- method ModelCachePage.__init__(self, win) (L74): __init__.
- method ModelCachePage._scan(self) (L145): _scan.
- method ModelCachePage._on_scan(self, stores) (L153): _on_scan.
- method ModelCachePage._clean(self, dry_run: bool) (L200): _clean.
- method ModelCachePage._on_clean(self, ok: bool, msg: str, freed: int) (L222): _on_clean.
- method ModelCachePage._fail(self, msg: str) (L233): _fail.

## src/cortex_unified/ui/premium/more_pages.py — Additional premium pages: Software Updater, Drive Optimizer, System Info.
- func _windows_only(page: _Page, feature: str) (L58): Return True (after showing a notice on *page*) unless on Windows.
- func _allow_multi_select(table: QTableWidget) (L77): Configure *table* for multi-row selection.
- func _selected_records(table: QTableWidget) (L87): Return the dicts stored in UserRole(0) for every selected row.
- class UpdaterListWorker(QObject) (L110): Worker that lists available app updates via AppUpdater.
- method UpdaterListWorker.run(self) (L115): Execute the listing operation and emit results or failure.
- class UpgradeWorker(QObject) (L124): Worker that applies upgrades for the given package IDs.
- method UpgradeWorker.__init__(self, package_ids: list[str]) (L129): Store the package IDs to upgrade.
- method UpgradeWorker.run(self) (L134): Execute upgrades for all package IDs and emit results.
- class DriveListWorker(QObject) (L148): Worker that lists drives via DriveOptimizer.
- method DriveListWorker.run(self) (L153): Execute the drive listing operation and emit results.
- class DriveOptimizeWorker(QObject) (L162): Worker that optimizes a specific drive.
- method DriveOptimizeWorker.__init__(self, letter: str) (L167): __init__.
- method DriveOptimizeWorker.run(self) (L172): Execute drive optimization and emit success status and message.
- class SystemInfoWorker(QObject) (L182): Worker that collects system information via SystemInfo.
- method SystemInfoWorker.run(self) (L187): Execute system info collection and emit the snapshot dict.
- class SoftwareUpdaterPage(_Page) (L200): List and apply app updates via winget.
- method SoftwareUpdaterPage.__init__(self, win) (L203): Initialize the Software Updater page.
- method SoftwareUpdaterPage._load(self) (L265): Load and display available app updates.
- method SoftwareUpdaterPage._on_listed(self, apps: list) (L274): Handle the list of available updates from the worker.
- method SoftwareUpdaterPage._selected_ids(self) (L300): Return the package IDs of selected rows in the table.
- method SoftwareUpdaterPage._update_selected(self) (L309): Handle the 'Update Selected' button click.
- method SoftwareUpdaterPage._update_all(self) (L317): Handle the 'Update All' button click.
- method SoftwareUpdaterPage._run_updates(self, ids: list[str], prompt: str) (L322): Run upgrades for the given package IDs after user confirmation.
- method SoftwareUpdaterPage._on_updated(self, ok: int, total: int) (L344): Handle completion of the upgrade operation.
- method SoftwareUpdaterPage._fail(self, msg: str) (L357): _fail.
- class DriveOptimizerPage(_Page) (L367): Media-aware TRIM (SSD) / defrag (HDD) - never defragments an SSD.
- method DriveOptimizerPage.__init__(self, win) (L370): Initialize the Drive Optimizer page.
- method DriveOptimizerPage._load(self) (L428): Load and display drive information.
- method DriveOptimizerPage._on_listed(self, drives: list) (L434): Handle the list of drives from the worker.
- method DriveOptimizerPage._optimize(self) (L456): Handle the 'Optimize Selected' button click.
- method DriveOptimizerPage._on_done(self, success: bool, message: str) (L478): Handle completion of the drive optimization.
- method DriveOptimizerPage._fail(self, msg: str) (L493): Handle worker failure.
- class SystemInfoPage(_Page) (L507): Read-only system facts + live metrics.
- method SystemInfoPage.__init__(self, win) (L510): Initialize the System Info page.
- method SystemInfoPage._load(self) (L551): Load and display system information.
- method SystemInfoPage._on_info(self, info: dict) (L557): Handle the system info from the worker.
- method SystemInfoPage._fail(self, msg: str) (L590): Handle worker failure.
- class BrokenLinksWorker(QObject) (L604): Worker that scans for broken shortcuts/links.
- method BrokenLinksWorker.__init__(self, root: str) (L610): __init__.
- method BrokenLinksWorker.cancel(self) (L617): Request cancellation of the scan.
- method BrokenLinksWorker.run(self) (L621): Execute the broken link scan and emit results.
- class DuplicateFoldersWorker(QObject) (L635): Worker that finds duplicate folders.
- method DuplicateFoldersWorker.__init__(self, root: str) (L641): __init__.
- method DuplicateFoldersWorker.cancel(self) (L648): Request cancellation of the scan.
- method DuplicateFoldersWorker.run(self) (L652): Execute the duplicate folder scan and emit results.
- class PackageCacheWorker(QObject) (L664): Worker that lists package manager cache sizes.
- method PackageCacheWorker.run(self) (L669): Execute the cache scan and emit results.
- class PackageCleanWorker(QObject) (L689): PackageCleanWorker class.
- method PackageCleanWorker.__init__(self, manager: str) (L694): __init__.
- method PackageCleanWorker.run(self) (L699): run.
- class _SimpleFolderPage(_Page) (L721): Minimal folder-pick + scan page (no fake Cancel affordance).
- method _SimpleFolderPage.__init__(self, win) (L731): __init__.
- method _SimpleFolderPage._build_results(self) (L820): Subclasses construct and return their specific QTableWidget.
- method _SimpleFolderPage._pick(self) (L826): _pick.
- method _SimpleFolderPage._toggle_run(self) (L838): _toggle_run.
- method _SimpleFolderPage._start(self, worker, on_done) (L848): Start a scan worker with live progress + cancel support.
- method _SimpleFolderPage._on_progress(self, text: str) (L861): _on_progress.
- method _SimpleFolderPage._finish(self) (L865): _finish.
- method _SimpleFolderPage._busy(self, on: bool) (L874): _busy.
- method _SimpleFolderPage._selected_paths(self) (L881): _selected_paths.
- method _SimpleFolderPage._delete_selected(self) (L887): _delete_selected.
- method _SimpleFolderPage._on_deleted(self, freed: int, ok: int, blocked: int) (L905): _on_deleted.
- method _SimpleFolderPage._run(self) (L913): Subclasses launch their specific scan worker.
- method _SimpleFolderPage._fail(self, msg: str) (L919): _fail.
- class BrokenLinksPage(_SimpleFolderPage) (L930): BrokenLinksPage class.
- method BrokenLinksPage._build_results(self) (L936): _build_results.
- method BrokenLinksPage._run(self) (L946): _run.
- method BrokenLinksPage._on_done(self, links: list) (L950): _on_done.
- class DuplicateFoldersPage(_SimpleFolderPage) (L966): DuplicateFoldersPage class.
- method DuplicateFoldersPage._build_results(self) (L972): _build_results.
- method DuplicateFoldersPage._run(self) (L982): _run.
- method DuplicateFoldersPage._on_done(self, groups: dict) (L986): _on_done.
- class PackageCachePage(_Page) (L1006): Detect system package managers (pip/npm/conda/...) and clear their caches.
- method PackageCachePage.__init__(self, win) (L1012): __init__.
- method PackageCachePage._browse_pm_directory(self) (L1204): _browse_pm_directory.
- method PackageCachePage._browse_pm_file(self) (L1213): _browse_pm_file.
- method PackageCachePage._add_custom_pm_location(self) (L1223): _add_custom_pm_location.
- method PackageCachePage.detect_package_managers(self) (L1231): detect_package_managers.
- method PackageCachePage.start_pm_scan(self) (L1268): start_pm_scan.
- method PackageCachePage._display_scan_results(self, resources) (L1298): _display_scan_results.
- method PackageCachePage.start_pm_cleanup(self) (L1339): start_pm_cleanup.
- method PackageCachePage._handle_cleanup_results(self, results, dry_run=True) (L1383): _handle_cleanup_results.
- method PackageCachePage._fail(self, msg: str) (L1397): _fail.
- method PackageCachePage._fmt_bytes(size_bytes: int) (L1402): _fmt_bytes.
- class SortableTreeWidgetItem(QTreeWidgetItem) (L1418): SortableTreeWidgetItem class.
- method SortableTreeWidgetItem.__lt__(self, other: QTreeWidgetItem) (L1420): __lt__.
- class ProjectCachesPage(_Page) (L1436): Clean multi-ecosystem project development caches (__pycache__, node_modules, target, build, etc.).
- method ProjectCachesPage.__init__(self, win) (L1439): __init__.
- method ProjectCachesPage._toggle_settings_panel(self, checked: bool) (L1822): Show or hide the settings card.
- method ProjectCachesPage._update_target_count_badge(self) (L1826): _update_target_count_badge.
- method ProjectCachesPage._add_typed_target_folder(self) (L1831): _add_typed_target_folder.
- method ProjectCachesPage.select_file_location_to_scan(self) (L1840): select_file_location_to_scan.
- method ProjectCachesPage.auto_detect_code_folders(self) (L1853): auto_detect_code_folders.
- method ProjectCachesPage.add_current_workspace(self) (L1881): add_current_workspace.
- method ProjectCachesPage.add_folder_to_scan(self) (L1893): add_folder_to_scan.
- method ProjectCachesPage.remove_selected_folder(self) (L1905): remove_selected_folder.
- method ProjectCachesPage.clear_all_folders(self) (L1916): clear_all_folders.
- method ProjectCachesPage.select_all_categories(self) (L1930): select_all_categories.
- method ProjectCachesPage.clear_all_categories(self) (L1939): clear_all_categories.
- method ProjectCachesPage._get_enabled_categories(self) (L1948): _get_enabled_categories.
- method ProjectCachesPage.start_project_scan(self) (L1965): start_project_scan.
- method ProjectCachesPage._on_scan_progress(self, status_text: str, items_found: int, total_bytes: int) (L2008): _on_scan_progress.
- method ProjectCachesPage._on_proj_scan_finished(self, resources: list) (L2014): _on_proj_scan_finished.
- method ProjectCachesPage.start_auto_scan(self) (L2021): Auto-discover across all fixed drives (no folder pick needed).
- method ProjectCachesPage._on_scan_failed(self, err_msg: str) (L2050): _on_scan_failed.
- method ProjectCachesPage._cleanup_scan_thread(self) (L2055): _cleanup_scan_thread.
- method ProjectCachesPage.cancel_project_operation(self) (L2070): cancel_project_operation.
- method ProjectCachesPage._display_project_scan_results(self, resources: list) (L2079): _display_project_scan_results.
- method ProjectCachesPage._on_tree_item_expanded(self, item: QTreeWidgetItem) (L2151): _on_tree_item_expanded.
- method ProjectCachesPage.on_sort_combo_changed(self, index: int) (L2196): on_sort_combo_changed.
- method ProjectCachesPage.filter_by_chip(self, cat_key: str) (L2213): filter_by_chip.
- method ProjectCachesPage._on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int) (L2220): _on_tree_item_double_clicked.
- method ProjectCachesPage._on_tree_item_changed(self, item: QTreeWidgetItem, column: int) (L2232): _on_tree_item_changed.
- method ProjectCachesPage.filter_results_table(self, query: str) (L2245): filter_results_table.
- method ProjectCachesPage.toggle_all_table_items(self, checked: bool) (L2282): toggle_all_table_items.
- method ProjectCachesPage.export_report(self) (L2293): export_report.
- method ProjectCachesPage._get_selected_resources(self) (L2333): _get_selected_resources.
- method ProjectCachesPage.start_project_cleanup(self) (L2344): start_project_cleanup.
- method ProjectCachesPage._on_clean_progress(self, done_count: int, total_count: int, freed_bytes: int) (L2383): _on_clean_progress.
- method ProjectCachesPage._on_proj_clean_finished(self, results: dict, dry_run: bool) (L2388): _on_proj_clean_finished.
- method ProjectCachesPage._handle_project_cleanup_results(self, results: dict, dry_run: bool=True) (L2413): _handle_project_cleanup_results.
- method ProjectCachesPage._on_clean_failed(self, err_msg: str) (L2417): _on_clean_failed.
- method ProjectCachesPage._cleanup_clean_thread(self) (L2422): _cleanup_clean_thread.
- method ProjectCachesPage._fail(self, msg: str) (L2436): _fail.
- method ProjectCachesPage._fmt_bytes(size_bytes: int) (L2441): _fmt_bytes.
- class SecretsScanWorker(QObject) (L2457): SecretsScanWorker class.
- method SecretsScanWorker.__init__(self, directory: str) (L2462): __init__.
- method SecretsScanWorker.run(self) (L2467): run.
- func _severity_rank(finding: dict) (L2495): _severity_rank.
- func _line_sort_key(finding: dict) (L2500): _line_sort_key.
- class SecretsScannerPage(_Page) (L2509): Scan a project folder for exposed secrets/credentials - fully offline.
- method SecretsScannerPage.__init__(self, win) (L2512): __init__.
- method SecretsScannerPage._pick(self) (L2558): _pick.
- method SecretsScannerPage._run(self) (L2567): _run.
- method SecretsScannerPage._on_done(self, findings: list, risk: int) (L2575): _on_done.
- method SecretsScannerPage._fail(self, msg: str) (L2594): _fail.
- class VirtualDisksPage(_Page) (L2605): Reclaim space from WSL / Docker / Hyper-V virtual disks.
- method VirtualDisksPage.__init__(self, win) (L2614): __init__.
- method VirtualDisksPage._selected_disks(self) (L2711): _selected_disks.
- method VirtualDisksPage._on_select(self) (L2716): _on_select.
- method VirtualDisksPage._load(self) (L2725): _load.
- method VirtualDisksPage._on_listed(self, disks: list) (L2733): _on_listed.
- method VirtualDisksPage._shutdown(self) (L2769): _shutdown.
- method VirtualDisksPage._on_shutdown(self, ok: bool, message: str) (L2786): _on_shutdown.
- method VirtualDisksPage._compact(self) (L2796): _compact.
- method VirtualDisksPage._on_compacted(self, results: list) (L2820): _on_compacted.
- method VirtualDisksPage._set_sparse(self) (L2849): _set_sparse.
- method VirtualDisksPage._on_sparse(self, ok: bool, message: str) (L2871): _on_sparse.
- method VirtualDisksPage._fail(self, msg: str) (L2881): _fail.

## src/cortex_unified/ui/premium/motion.py — Motion system: a single shared set of animation durations and easing curves
- func prefers_reduced_motion() (L29): Return True when non-essential animation should be suppressed.
- func set_reduced_motion(value: bool) (L34): Enable/disable the app-wide reduced-motion preference.
- class Duration (L40): Named animation durations, in milliseconds.
- func fade_in(widget: QWidget, duration: int=Duration.NORMAL, on_done: Callable[[], None] | None=None) (L62): Fade ``widget`` in from transparent to fully opaque.
- func fade_in._teardown() (L86): _teardown.
- func reveal(widget: QWidget, duration: int=Duration.NORMAL, rise: int=12, on_done: Callable[[], None] | None=None) (L101): Reveal ``widget`` with a combined fade + gentle upward rise.
- func reveal._teardown() (L153): _teardown.
- func press_feedback(widget, sink: int=2) (L169): Give a clickable widget a subtle tactile "sink" on press.
- func press_feedback._anim_to(point: QPoint) (L185): _anim_to.
- func press_feedback._down() (L195): _down.
- func press_feedback._up() (L207): _up.
- func animate_property(target, prop: bytes, start, end, duration: int=Duration.SLOW, easing: QEasingCurve.Type=EASING_STANDARD) (L222): Animate a Qt property ``prop`` on ``target`` from ``start`` to ``end``.

## src/cortex_unified/ui/premium/near_duplicates_page.py — Near-duplicate finder page – MinHash LSH + Bloom (SEDD/LSHBloom/SemHash).
- class _NearDupWorker(QObject) (L29): _NearDupWorker class.
- method _NearDupWorker.__init__(self, root: str, threshold: float=0.8) (L35): __init__.
- method _NearDupWorker.cancel(self) (L44): cancel.
- method _NearDupWorker.run(self) (L48): run.
- class NearDuplicatesPage(_Page) (L63): Find near-duplicate files (80%+ Jaccard) via MinHash LSH + Bloom.
- method NearDuplicatesPage.__init__(self, win) (L66): __init__.
- method NearDuplicatesPage._pick(self) (L117): _pick.
- method NearDuplicatesPage._run(self) (L127): _run.
- method NearDuplicatesPage._on_progress(self, msg: str) (L138): _on_progress.
- method NearDuplicatesPage._on_done(self, groups: dict) (L142): _on_done.
- method NearDuplicatesPage._fail(self, msg) (L168): _fail.

## src/cortex_unified/ui/premium/network_pages.py — Network suite pages: live Traffic Monitor and Firewall control.
- func _ip_sort_key(device) (L57): Sort IPv4 addresses numerically rather than as dotted strings.
- func _fmt_rate(bps: float) (L75): _fmt_rate.
- class TrafficMonitorPage(_Page) (L89): Live network throughput graph + per-interface breakdown.
- method TrafficMonitorPage.__init__(self, win) (L92): __init__.
- method TrafficMonitorPage._start(self) (L142): _start.
- method TrafficMonitorPage._tick(self) (L150): _tick.
- class FirewallListWorker(QObject) (L177): FirewallListWorker class.
- method FirewallListWorker.__init__(self, cortex_only: bool=True) (L182): __init__.
- method FirewallListWorker.run(self) (L187): run.
- class FirewallActionWorker(QObject) (L197): FirewallActionWorker class.
- method FirewallActionWorker.__init__(self, action: str, **kwargs) (L202): __init__.
- method FirewallActionWorker.run(self) (L208): run.
- class FirewallPage(_Page) (L235): Block/allow programs and IPs via Windows Firewall (Cortex-scoped).
- method FirewallPage.__init__(self, win) (L238): __init__.
- method FirewallPage._browse(self) (L337): _browse.
- method FirewallPage._busy(self, on: bool) (L344): _busy.
- method FirewallPage._create(self, action: str) (L349): _create.
- method FirewallPage._on_action(self, ok: bool, msg: str) (L378): _on_action.
- method FirewallPage._load(self) (L387): _load.
- method FirewallPage._on_listed(self, rules: list) (L393): _on_listed.
- method FirewallPage._on_sel(self) (L414): _on_sel.
- method FirewallPage._selected(self) (L420): _selected.
- method FirewallPage._toggle(self) (L430): _toggle.
- method FirewallPage._remove(self) (L441): _remove.
- method FirewallPage._fail(self, msg: str) (L458): _fail.
- class _MapCanvas(QWidget) (L469): Draws an offline connection graph: This PC -> apps -> remote endpoints.
- method _MapCanvas.__init__(self, palette, parent=None) (L472): __init__.
- method _MapCanvas.set_edges(self, edges: list[tuple[str, str, bool]]) (L479): set_edges.
- method _MapCanvas.paintEvent(self, event) (L485): paintEvent.
- func _MapCanvas.paintEvent._ys(n: int) (L514): _ys.
- method _MapCanvas._curve(self, painter, x1, y1, x2, y2, color: QColor) (L552): _curve.
- method _MapCanvas._node(self, painter, cx, cy, label, color: QColor, big=False, small=False) (L563): _node.
- class NetworkMapPage(_Page) (L584): Visual, offline map of which apps connect to which remote hosts.
- method NetworkMapPage.__init__(self, win) (L587): __init__.
- method NetworkMapPage._load(self) (L627): _load.
- method NetworkMapPage._on_loaded(self, conns: list, summary: dict) (L634): _on_loaded.
- method NetworkMapPage._render(self) (L641): _render.
- method NetworkMapPage._fail(self, msg: str) (L659): _fail.
- class LanScanWorker(QObject) (L669): Deep multi-protocol LAN discovery on the worker runtime.
- method LanScanWorker.__init__(self, deep: bool=True, rounds: int=2, audit_profile: str='targeted', include_upnp_wan: bool=False, requested_networks=None, custom_ports=None, nmap_modes=None, advisory_catalog_path=None) (L681): Initialize discovery worker.
- method LanScanWorker.cancel(self) (L698): cancel.
- method LanScanWorker.run(self) (L702): run.
- class VendorDatabaseWorker(QObject) (L724): Explicit IEEE registry refresh; never runs automatically.
- method VendorDatabaseWorker.__init__(self) (L730): __init__.
- method VendorDatabaseWorker.cancel(self) (L735): cancel.
- method VendorDatabaseWorker.run(self) (L739): run.
- class NetworkScheduleWorker(QObject) (L750): NetworkScheduleWorker class.
- method NetworkScheduleWorker.__init__(self, action: str, spec=None) (L755): __init__.
- method NetworkScheduleWorker.run(self) (L761): run.
- class ExposureLookupWorker(QObject) (L779): ExposureLookupWorker class.
- method ExposureLookupWorker.__init__(self, provider: str, public_ip: str, api_key: str, api_secret: str) (L784): Initialize worker.
- method ExposureLookupWorker.run(self) (L793): run.
- class DeviceActionWorker(QObject) (L807): Run an explicit selected-device ping or Wake-on-LAN action.
- method DeviceActionWorker.__init__(self, action: str, device, networks) (L813): __init__.
- method DeviceActionWorker.run(self) (L820): run.
- class LanDevicesPage(_Page) (L857): Everything actually on your local network, not just the ARP cache.
- method LanDevicesPage.__init__(self, win) (L872): __init__.
- method LanDevicesPage._toggle_more_controls(self, visible: bool) (L1281): _toggle_more_controls.
- method LanDevicesPage._load(self, deep: bool=True, rounds: int=2, audit_profile: str='targeted', include_upnp_wan: bool=False, requested_networks=None, custom_ports=None, nmap_modes=None, advisory_catalog_path=None) (L1291): Load network audit data.
- method LanDevicesPage._run_expert_scan(self) (L1308): _run_expert_scan.
- method LanDevicesPage._browse_advisory_catalog(self) (L1348): _browse_advisory_catalog.
- method LanDevicesPage._device_columns(self) (L1358): Declare the device columns once instead of filling cells per row.
- method LanDevicesPage._device_name(self, dev) (L1378): _device_name.
- method LanDevicesPage._device_type(self, dev) (L1388): _device_type.
- method LanDevicesPage._device_services(dev) (L1403): _device_services.
- method LanDevicesPage._device_findings(self, dev) (L1415): _device_findings.
- method LanDevicesPage._device_security(self, dev) (L1421): _device_security.
- method LanDevicesPage._device_security_rank(self, dev) (L1431): Sort worst-first: a device with a critical finding outranks a clean one.
- method LanDevicesPage._identity_of(self, dev) (L1438): _identity_of.
- method LanDevicesPage._open_device_window(self, *_args) (L1443): Open the selected device in its own full-detail premium window.
- method LanDevicesPage._forget_device_window(self, window) (L1464): _forget_device_window.
- method LanDevicesPage._selected_device(self) (L1470): The selected ``Device``, resolved through the proxy.
- method LanDevicesPage._device_action(self, action: str) (L1479): _device_action.
- method LanDevicesPage._device_action_done(self, action: str, payload) (L1501): _device_action_done.
- method LanDevicesPage._device_action_failed(self, message: str) (L1517): _device_action_failed.
- method LanDevicesPage._open_selected_service(self) (L1524): _open_selected_service.
- method LanDevicesPage._load_selected_metadata(self, device) (L1545): _load_selected_metadata.
- method LanDevicesPage._save_selected_metadata(self) (L1563): _save_selected_metadata.
- method LanDevicesPage._export_inventory_csv(self) (L1592): _export_inventory_csv.
- method LanDevicesPage._import_inventory_csv(self) (L1610): _import_inventory_csv.
- method LanDevicesPage._lookup_external_exposure(self) (L1645): _lookup_external_exposure.
- method LanDevicesPage._exposure_done(self, result) (L1683): _exposure_done.
- method LanDevicesPage._exposure_failed(self, message: str) (L1690): _exposure_failed.
- method LanDevicesPage._create_schedule(self) (L1696): _create_schedule.
- method LanDevicesPage._delete_schedule(self) (L1726): _delete_schedule.
- method LanDevicesPage._run_schedule_action(self, action: str, spec=None) (L1737): _run_schedule_action.
- method LanDevicesPage._schedule_done(self, action: str, payload) (L1746): _schedule_done.
- method LanDevicesPage._schedule_failed(self, message: str) (L1753): _schedule_failed.
- method LanDevicesPage._confirm_deep_audit(self) (L1758): _confirm_deep_audit.
- method LanDevicesPage._update_vendors(self) (L1774): _update_vendors.
- method LanDevicesPage._vendors_updated(self, ok: bool, message: str) (L1782): _vendors_updated.
- method LanDevicesPage._vendor_update_failed(self, message: str) (L1794): _vendor_update_failed.
- method LanDevicesPage._export_report(self) (L1799): _export_report.
- method LanDevicesPage._show_device_details(self, *_args) (L1881): _show_device_details.
- method LanDevicesPage._cancel(self) (L1945): _cancel.
- method LanDevicesPage._busy(self, busy: bool) (L1955): _busy.
- method LanDevicesPage._on_loaded(self, result) (L1975): _on_loaded.
- func LanDevicesPage._on_loaded._ip_key(dev) (L1981): _ip_key.
- method LanDevicesPage._fail(self, msg: str) (L2167): _fail.
- class _ToolWorker(QObject) (L2177): Runs one network-tool call off the UI thread.
- method _ToolWorker.__init__(self, tool: str, target: str) (L2183): __init__.
- method _ToolWorker.run(self) (L2189): run.
- class NetworkToolsPage(_Page) (L2222): Classic diagnostics: ping, traceroute, DNS, port check, IP info.
- method NetworkToolsPage.__init__(self, win) (L2225): __init__.
- method NetworkToolsPage._run(self, tool: str) (L2287): _run.
- method NetworkToolsPage._on_result(self, tool: str, result) (L2301): _on_result.
- method NetworkToolsPage._show_ping(self, r: dict) (L2316): _show_ping.
- method NetworkToolsPage._show_traceroute(self, hops: list) (L2329): _show_traceroute.
- method NetworkToolsPage._show_dns(self, r: dict) (L2341): _show_dns.
- method NetworkToolsPage._show_ports(self, res: dict) (L2357): _show_ports.
- method NetworkToolsPage._show_ipinfo(self, info: dict) (L2378): _show_ipinfo.
- method NetworkToolsPage._fail(self, msg: str) (L2394): _fail.
- class AuthorizeWorker(QObject) (L2407): AuthorizeWorker class.
- method AuthorizeWorker.__init__(self, host: str, token: str='') (L2412): __init__.
- method AuthorizeWorker.run(self) (L2418): run.
- class LoadTestWorker(QObject) (L2428): LoadTestWorker class.
- method LoadTestWorker.__init__(self, mode: str, cfg: dict, auth_dict: dict) (L2434): __init__.
- method LoadTestWorker.cancel(self) (L2443): cancel.
- method LoadTestWorker.run(self) (L2447): run.
- class LoadTesterPage(_Page) (L2470): Measure how much load YOUR OWN service can take before it degrades.
- method LoadTesterPage.__init__(self, win) (L2473): __init__.
- method LoadTesterPage._mode_changed(self) (L2574): _mode_changed.
- method LoadTesterPage._check(self) (L2580): _check.
- method LoadTesterPage._on_auth(self, auth: dict) (L2590): _on_auth.
- method LoadTesterPage._offer_token(self, auth: dict) (L2608): _offer_token.
- method LoadTesterPage._auth_fail(self, msg: str) (L2624): _auth_fail.
- method LoadTesterPage._toggle(self) (L2630): _toggle.
- method LoadTesterPage._start(self) (L2639): _start.
- method LoadTesterPage._on_progress(self, snap: dict) (L2677): _on_progress.
- method LoadTesterPage._on_done(self, s: dict) (L2683): _on_done.
- method LoadTesterPage._verdict(s: dict) (L2707): _verdict.
- method LoadTesterPage._run_fail(self, msg: str) (L2721): _run_fail.

## src/cortex_unified/ui/premium/nextgen_suite_pages.py — Cortex Cleaner & NexusExplorer — Next-Generation Enterprise Suite GUI Pages.
- func _fmt_bytes(b: int) (L50): Format a byte count into a human-readable B/KB/MB/GB string.
- func _PrimaryButton(text: str) (L61): Create a QPushButton styled as the primary (accented) action button.
- func _SecondaryButton(text: str) (L69): Create a QPushButton styled as a secondary action button with a pointing-hand cursor.
- func _run_task(win, work_fn, done_fn, err_fn=None) (L76): Run work_fn on the window's worker runtime, or inline as a fallback, dispatching to done_fn / err_fn.
- class ShaderCachePage(_Page) (L93): Page for auditing and purging stale GPU shader caches by age.
- method ShaderCachePage.__init__(self, win: PremiumMainWindow) (L95): Build the Shader Cache page with scan/clean buttons, a min-age spinner, and a table.
- method ShaderCachePage._on_scan(self) (L142): Scan shader cache locations with the configured minimum age.
- func ShaderCachePage._on_scan.work() (L147): Scan shader caches for files older than the minimum age.
- func ShaderCachePage._on_scan.done(report: ShaderCacheReport) (L151): List discovered cache locations and stale-file totals.
- method ShaderCachePage._on_clean(self) (L170): Purge shader binaries older than the minimum age.
- func ShaderCachePage._on_clean.work() (L175): Clean stale shader caches (not a dry run).
- func ShaderCachePage._on_clean.done(result: ShaderCleanResult) (L179): Report cleaned files, freed bytes, and any locked files, then rescan.
- class AiTelemetryCleanerPage(_Page) (L195): Page for auditing Copilot/Recall caches and truncating SQLite WAL logs.
- method AiTelemetryCleanerPage.__init__(self, win: PremiumMainWindow) (L197): Build the AI Telemetry page with scan/clean buttons and an artifacts table.
- method AiTelemetryCleanerPage._on_scan(self) (L237): Scan local AI and Recall stores in the background.
- func AiTelemetryCleanerPage._on_scan.work() (L241): Scan AI telemetry artifacts.
- func AiTelemetryCleanerPage._on_scan.done(report: AiTelemetryReport) (L245): List AI artifacts, sizes, and WAL journal usage.
- method AiTelemetryCleanerPage._on_clean(self) (L263): Clean transient AI caches and checkpoint WAL databases.
- func AiTelemetryCleanerPage._on_clean.work() (L267): Clean AI caches and truncate SQLite WAL journals.
- func AiTelemetryCleanerPage._on_clean.done(result: AiCleanResult) (L271): Report cleaned items and checkpointed WALs, then rescan.
- class SsdTrimOptimizerPage(_Page) (L288): Page for auditing volume TRIM state and running a ReTrim on a chosen drive.
- method SsdTrimOptimizerPage.__init__(self, win: PremiumMainWindow) (L290): Build the SSD TRIM page with audit/trim buttons and a volumes table.
- method SsdTrimOptimizerPage._on_audit(self) (L327): Audit volumes and filesystem TRIM status in the background.
- func SsdTrimOptimizerPage._on_audit.work() (L331): Audit volume media types and TRIM enablement.
- func SsdTrimOptimizerPage._on_audit.done(report: TrimAuditReport) (L335): Fill the volumes table and filesystem TRIM summary.
- method SsdTrimOptimizerPage._on_trim(self) (L356): ReTrim the drive selected in the table.
- func SsdTrimOptimizerPage._on_trim.work() (L368): Execute a non-destructive ReTrim on the chosen volume.
- func SsdTrimOptimizerPage._on_trim.done(result: TrimExecutionResult) (L372): Report the ReTrim result, then re-audit.
- class RestartManagerUnlockerPage(_Page) (L388): Page for finding and killing processes that lock a file via Restart Manager.
- method RestartManagerUnlockerPage.__init__(self, win: PremiumMainWindow) (L390): Build the Unlocker page with path input, inspect/unlock buttons, and a processes table.
- method RestartManagerUnlockerPage._on_browse(self) (L433): Pick a file, fill the path input, and inspect it immediately.
- method RestartManagerUnlockerPage._on_inspect(self) (L440): Query Restart Manager for processes locking the entered path.
- func RestartManagerUnlockerPage._on_inspect.work() (L448): Inspect which processes lock the file.
- func RestartManagerUnlockerPage._on_inspect.done(report: FileLockReport) (L452): List locking processes or report the file as unlocked/missing.
- method RestartManagerUnlockerPage._on_unlock(self) (L474): Force-terminate the processes locking the entered file.
- func RestartManagerUnlockerPage._on_unlock.work() (L480): Unlock the file by terminating locking processes.
- func RestartManagerUnlockerPage._on_unlock.done(result: UnlockResult) (L484): Report the unlock result, then re-inspect.
- class VssHealthAnalyzerPage(_Page) (L497): Page for diagnosing VSS writers and shadow copy storage usage.
- method VssHealthAnalyzerPage.__init__(self, win: PremiumMainWindow) (L499): Build the VSS Health page with scan/reset buttons and a writers table.
- method VssHealthAnalyzerPage._on_scan(self) (L539): Inspect VSS writers and shadow storage in the background.
- func VssHealthAnalyzerPage._on_scan.work() (L543): Inspect VSS writer health.
- func VssHealthAnalyzerPage._on_scan.done(report: VssHealthReport) (L547): List writer states and summarize healthy vs failed writers.
- method VssHealthAnalyzerPage._on_reset(self) (L567): Restart VSS services to clear stalled writer states.
- func VssHealthAnalyzerPage._on_reset.work() (L571): Reset stalled VSS writers.
- func VssHealthAnalyzerPage._on_reset.done(result: VssResetResult) (L575): Report the reset result, then re-scan.
- class DevPackageCachePage(_Page) (L588): Page for auditing and purging Winget, Cargo, vcpkg, NuGet, and Pip caches.
- method DevPackageCachePage.__init__(self, win: PremiumMainWindow) (L590): Build the Dev Package Cache page with scan/clean buttons and a stores table.
- method DevPackageCachePage._on_scan(self) (L631): Scan developer package stores in the background.
- func DevPackageCachePage._on_scan.work() (L635): Scan developer package caches.
- func DevPackageCachePage._on_scan.done(report: DevPackageReport) (L639): List package stores, counts, sizes, and locations.
- method DevPackageCachePage._on_clean(self) (L658): Purge all discovered developer package stores.
- func DevPackageCachePage._on_clean.work() (L662): Clean developer package stores (not a dry run).
- func DevPackageCachePage._on_clean.done(result: DevPackageCleanResult) (L666): Report stores cleaned and bytes freed, then rescan.
- class ChecksumMatrixPage(_Page) (L680): Page for batch hashing files and generating .sha256 manifests.
- method ChecksumMatrixPage.__init__(self, win: PremiumMainWindow) (L682): Build the Checksum Matrix page with target input, hash/manifest buttons, and a digests table.
- method ChecksumMatrixPage._on_browse_file(self) (L731): Pick a file, fill the target input, and hash it immediately.
- method ChecksumMatrixPage._on_browse_dir(self) (L738): Pick a directory to use for manifest generation.
- method ChecksumMatrixPage._on_hash(self) (L744): Compute CRC32, MD5, SHA-1, SHA-256, and SHA-512 for the chosen file.
- func ChecksumMatrixPage._on_hash.work() (L753): Compute all five checksum digests for the file.
- func ChecksumMatrixPage._on_hash.done(res: FileChecksumResult) (L757): Show every computed digest and the hashing duration.
- method ChecksumMatrixPage._on_generate_manifest(self) (L780): Write a checksums.sha256 manifest for the chosen directory.
- func ChecksumMatrixPage._on_generate_manifest.work() (L790): Generate a SHA-256 manifest for the directory.
- func ChecksumMatrixPage._on_generate_manifest.done(count: int) (L794): Report the number of entries written to the manifest.

## src/cortex_unified/ui/premium/nexus_page.py — Nexus File Manager page.
- func _load_nexus_module() (L38): Lazily import the explorer widget when QApplication is running.
- class _ErrorCard(QWidget) (L58): _ErrorCard class.
- method _ErrorCard.__init__(self, message: str, parent=None) (L60): __init__.
- class NexusExplorerPage(_Page) (L78): The embedded native explorer (in-process Qt6 widget).
- method NexusExplorerPage.__init__(self, win) (L88): __init__.
- method NexusExplorerPage._build_explorer(self) (L97): _build_explorer.

## src/cortex_unified/ui/premium/perceptual_duplicates_page.py — Perceptual duplicate photos page – pHash / dHash / aHash.
- class _PerceptualWorker(QObject) (L26): _PerceptualWorker class.
- method _PerceptualWorker.__init__(self, root: str, max_distance: int=10) (L32): __init__.
- method _PerceptualWorker.cancel(self) (L41): cancel.
- method _PerceptualWorker.run(self) (L45): run.
- class PerceptualDuplicatesPage(_Page) (L63): Find visually-similar photos via perceptual hashing (pHash).
- method PerceptualDuplicatesPage.__init__(self, win) (L66): __init__.
- method PerceptualDuplicatesPage._pick(self) (L121): _pick.
- method PerceptualDuplicatesPage._run(self) (L130): _run.
- method PerceptualDuplicatesPage._on_progress(self, msg: str) (L141): _on_progress.
- method PerceptualDuplicatesPage._on_done(self, groups: dict) (L145): _on_done.
- method PerceptualDuplicatesPage._fail(self, msg) (L178): _fail.

## src/cortex_unified/ui/premium/portable_manager_page.py — Portable App Manager page — scan, track, and update portable apps.
- class _PortableWorker(QObject) (L41): _PortableWorker class.
- method _PortableWorker.__init__(self, roots: list[str], target_apps: list[str] | None=None) (L47): __init__.
- method _PortableWorker.cancel(self) (L54): cancel.
- method _PortableWorker.run(self) (L58): run.
- class _UpdateWorker(QObject) (L78): _UpdateWorker class.
- method _UpdateWorker.__init__(self, apps: list) (L84): __init__.
- method _UpdateWorker.cancel(self) (L90): cancel.
- method _UpdateWorker.run(self) (L94): run.
- class PortableManagerPage(_Page) (L121): Scan, track, and update portable apps on removable and local drives.
- method PortableManagerPage.__init__(self, win) (L124): __init__.
- method PortableManagerPage._add_root(self) (L206): _add_root.
- method PortableManagerPage._parse_roots(self) (L218): _parse_roots.
- method PortableManagerPage._get_target_apps(self) (L225): _get_target_apps.
- method PortableManagerPage._run(self) (L232): _run.
- method PortableManagerPage._on_progress(self, msg: str) (L247): _on_progress.
- method PortableManagerPage._on_done(self, apps: list) (L251): _on_done.
- method PortableManagerPage._auto_update(self, apps: list) (L290): _auto_update.
- method PortableManagerPage._on_update_done(self, result) (L318): _on_update_done.
- method PortableManagerPage._on_update_fail(self, msg) (L327): _on_update_fail.
- method PortableManagerPage._fail(self, msg) (L334): _fail.

## src/cortex_unified/ui/premium/power_suite_pages.py — Cortex Cleaner & NexusExplorer — Enterprise Power Suite GUI Pages.
- func _fmt_bytes(b: int) (L56): Format a byte count into a human-readable B/KB/MB/GB string.
- func _PrimaryButton(text: str, parent=None) (L67): Create a QPushButton styled as the primary (accented) action button.
- func _SecondaryButton(text: str, parent=None) (L75): Create a QPushButton styled as a secondary action button with a pointing-hand cursor.
- func _run_task(win, work_fn, done_fn, err_fn=None) (L82): Run work_fn on the window's worker runtime, or inline as a fallback, dispatching to done_fn / err_fn.
- class EnvVariableManagerPage(_Page) (L99): Page for auditing PATH entries and cleaning dead links or duplicates.
- method EnvVariableManagerPage.__init__(self, win: PremiumMainWindow) (L101): Build the PATH Optimizer page with analyze/clean/export buttons and an entries table.
- method EnvVariableManagerPage._on_analyze(self) (L144): Analyze PATH and list entries with dead-link and duplicate flags.
- method EnvVariableManagerPage._on_clean(self) (L166): Confirm and remove dead/duplicate User PATH entries, then re-analyze.
- method EnvVariableManagerPage._on_export(self) (L181): Export environment variables to a .env or .bat file.
- class WindowsServiceManagerPage(_Page) (L195): Page for profiling services and applying preset optimization profiles.
- method WindowsServiceManagerPage.__init__(self, win: PremiumMainWindow) (L197): Build the Service Manager page with scan button, profile combo, and services table.
- method WindowsServiceManagerPage._on_scan(self) (L236): Enumerate Windows services on the worker runtime.
- func WindowsServiceManagerPage._on_scan._work() (L241): Enumerate services with status, startup type, and category.
- func WindowsServiceManagerPage._on_scan._done(services: List[ServiceInfo]) (L245): Fill the services table and highlight safe-to-disable entries.
- method WindowsServiceManagerPage._on_apply_profile(self) (L264): Confirm and apply the selected service profile, then rescan.
- class FontCacheManagerPage(_Page) (L285): Page for inspecting installed fonts and removing orphaned registry entries.
- method FontCacheManagerPage.__init__(self, win: PremiumMainWindow) (L287): Build the Font Cache page with scan/clean buttons and a fonts table.
- method FontCacheManagerPage._on_scan(self) (L327): Analyze installed fonts and flag orphans and duplicates.
- method FontCacheManagerPage._on_clean(self) (L347): Confirm and remove orphaned font entries, then rescan.
- class TempFolderCleanerPage(_Page) (L364): Page for scanning and purging stale temp files across many locations.
- method TempFolderCleanerPage.__init__(self, win: PremiumMainWindow) (L366): Build the Temp Cleaner page with age spinner, scan/clean buttons, and a locations table.
- method TempFolderCleanerPage._on_scan(self) (L412): Scan all temp locations and show stale-file totals.
- method TempFolderCleanerPage._on_clean(self) (L431): Confirm and delete temp files older than the chosen age, then rescan.
- class ContextMenuManagerPage(_Page) (L452): Page for enabling and disabling Explorer context-menu handlers.
- method ContextMenuManagerPage.__init__(self, win: PremiumMainWindow) (L454): Build the Context Menu page with scan button, enable/disable actions, and an entries table.
- method ContextMenuManagerPage._on_scan(self) (L500): Analyze context-menu entries and flag orphaned handlers.
- method ContextMenuManagerPage._on_disable_selected(self) (L522): Disable the context-menu entry selected in the table.
- method ContextMenuManagerPage._on_enable_selected(self) (L534): Enable the context-menu entry selected in the table.
- class PagefileOptimizerPage(_Page) (L551): Page for configuring fixed or system-managed pagefile allocation.
- method PagefileOptimizerPage.__init__(self, win: PremiumMainWindow) (L553): Build the Pagefile page with status labels, drive/size controls, and apply/reset buttons.
- method PagefileOptimizerPage._refresh(self) (L604): Refresh RAM/pagefile status and prefill recommended sizes.
- method PagefileOptimizerPage._on_apply(self) (L616): Confirm and set a fixed pagefile on the chosen drive, then refresh.
- method PagefileOptimizerPage._on_reset_auto(self) (L634): Reset the pagefile to system-managed, then refresh.
- class DiagnosticDataManagerPage(_Page) (L648): Page for auditing telemetry settings and enforcing maximum privacy.
- method DiagnosticDataManagerPage.__init__(self, win: PremiumMainWindow) (L650): Build the Telemetry page with audit/harden buttons, score label, and settings table.
- method DiagnosticDataManagerPage._on_audit(self) (L688): Audit telemetry settings and show the privacy hardening score.
- method DiagnosticDataManagerPage._on_harden(self) (L708): Confirm and apply maximum-privacy telemetry policies, then re-audit.
- class StartupImpactPage(_Page) (L728): Page for analyzing startup impact and toggling startup items.
- method StartupImpactPage.__init__(self, win: PremiumMainWindow) (L730): Build the Startup Impact page with scan/toggle buttons and an items table.
- method StartupImpactPage._on_scan(self) (L772): Analyze startup items and show impact levels and boot delay.
- method StartupImpactPage._on_toggle(self) (L798): Enable or disable the startup item selected in the table.
- class SlackSpaceAnalyzerPage(_Page) (L817): Page for measuring NTFS cluster slack waste per directory.
- method SlackSpaceAnalyzerPage.__init__(self, win: PremiumMainWindow) (L819): Build the Slack Space page with folder picker, analyze button, and offenders table.
- method SlackSpaceAnalyzerPage._on_choose(self) (L859): Pick a directory and immediately analyze it.
- method SlackSpaceAnalyzerPage._on_scan(self) (L866): Analyze cluster slack waste on the worker runtime.
- func SlackSpaceAnalyzerPage._on_scan._work() (L871): Analyze directory slack space to depth two.
- func SlackSpaceAnalyzerPage._on_scan._done(rep: VolumeSlackReport) (L875): Show totals and list the worst slack-waste directories.
- class EventLogMonitorPage(_Page) (L903): Page for scanning event logs for hardware faults and crashes.
- method EventLogMonitorPage.__init__(self, win: PremiumMainWindow) (L905): Build the Event Monitor page with scan button and an events table.
- method EventLogMonitorPage._on_scan(self) (L940): Query event-log anomalies on the worker runtime.
- func EventLogMonitorPage._on_scan._work() (L945): Query event logs for hardware faults and crashes.
- func EventLogMonitorPage._on_scan._done(rep: AnomalyScanReport) (L949): Summarize faults and fill the events table with severity colors.

## src/cortex_unified/ui/premium/power_tools_pages.py — Premium GUI pages for Enterprise Power Tools & System Maintainers.
- class HashVerifierPage(_Page) (L60): File checksum calculator and manifest validator.
- method HashVerifierPage.__init__(self, win) (L63): Build the Hash Verifier page with file picker, digests table, and manifest actions.
- method HashVerifierPage._pick_file(self) (L118): Pick a file to hash and enable computation.
- method HashVerifierPage._compute_hashes(self) (L128): Compute MD5, SHA-1, SHA-256, SHA-512, and CRC32 for the chosen file.
- method HashVerifierPage._copy_to_clip(self, text: str) (L151): Copy a checksum digest to the clipboard and confirm.
- method HashVerifierPage._verify_manifest(self) (L157): Verify a .sfv/.md5/.sha256/.sha512 manifest and summarize match results.
- class BatchRenamerPage(_Page) (L183): Regex, token template, and EXIF batch multi-renamer.
- method BatchRenamerPage.__init__(self, win) (L186): Build the Batch Renamer page with pattern form, preview table, and apply/undo buttons.
- method BatchRenamerPage._pick_files(self) (L267): Pick files to rename and refresh the preview.
- method BatchRenamerPage._update_preview(self) (L275): Recompute the rename plan and show per-file status in the table.
- method BatchRenamerPage._apply_rename(self) (L318): Execute the previewed rename plan and report the outcome.
- method BatchRenamerPage._undo_rename(self) (L330): Revert the last executed rename.
- class FolderSyncPage(_Page) (L344): Side-by-side folder comparison matrix and 1-click sync engine.
- method FolderSyncPage.__init__(self, win) (L347): Build the Folder Sync page with folder pickers, compare controls, diff table, and sync mode.
- method FolderSyncPage._pick_left(self) (L425): Pick the left folder to compare.
- method FolderSyncPage._pick_right(self) (L434): Pick the right folder to compare.
- method FolderSyncPage._run_compare(self) (L443): Compare the two folders and fill the diff table; enable sync.
- method FolderSyncPage._run_sync(self) (L476): Confirm and execute the selected sync mode, then re-compare.
- class FileSplitterPage(_Page) (L512): File chunk splitter and reconstructor with SHA256 integrity check.
- method FileSplitterPage.__init__(self, win) (L515): Build the Splitter/Joiner page with split and join tabs.
- method FileSplitterPage._pick_split_src(self) (L588): Pick the file to split and enable the split button.
- method FileSplitterPage._execute_split(self) (L598): Split the source file into preset-sized chunks with a manifest.
- method FileSplitterPage._pick_join_src(self) (L624): Pick the first part or manifest to join and enable the join button.
- method FileSplitterPage._execute_join(self) (L634): Reassemble the split parts into the original file.
- class FileUnlockerPage(_Page) (L655): File handle inspector and process unlocker.
- method FileUnlockerPage.__init__(self, win) (L658): Build the File Unlocker page with a picker, lock table, and per-process kill actions.
- method FileUnlockerPage._pick_file(self) (L697): Pick the locked file and immediately inspect its locks.
- method FileUnlockerPage._inspect_locks(self) (L708): List processes holding locks on the chosen file.
- method FileUnlockerPage._terminate_proc(self, pid: int) (L732): Force-terminate a locking process, then re-inspect locks.
- class AdsManagerPage(_Page) (L747): NTFS Alternate Data Stream inspector and Zone.Identifier unblocker.
- method AdsManagerPage.__init__(self, win) (L750): Build the ADS Manager page with a file picker, unblock button, and streams table.
- method AdsManagerPage._pick_file(self) (L787): Pick a file and list its alternate data streams.
- method AdsManagerPage._refresh_streams(self) (L797): List the file's NTFS streams and enable unblocking when a Zone.Identifier exists.
- method AdsManagerPage._unblock_file(self) (L818): Remove the Zone.Identifier stream to unblock the file.
- method AdsManagerPage._delete_stream(self, stream_name: str) (L830): Delete the named alternate data stream, then refresh.
- class EventLogCleanerPage(_Page) (L847): Windows Event Log manager and cleaner.
- method EventLogCleanerPage.__init__(self, win) (L850): Build the Event Log page with stat cards, log table, and refresh/clear actions.
- method EventLogCleanerPage._load_logs(self) (L897): Load all event log channels into the table and stat cards.
- method EventLogCleanerPage._clear_all_logs(self) (L916): Confirm and clear every event log channel, then reload.
- class SystemCacheRebuilderPage(_Page) (L937): Font, Icon, and Thumbnail cache rebuilder and Shell restarter.
- method SystemCacheRebuilderPage.__init__(self, win) (L940): Build the Cache Rebuilder page with restart-shell option and rebuild button.
- method SystemCacheRebuilderPage._execute_rebuild(self) (L970): Rebuild font and icon caches and report the outcome.
- class NetworkOptimizerPage(_Page) (L985): DNS Resolver and TCP/IP stack tuning toolkit.
- method NetworkOptimizerPage.__init__(self, win) (L988): Build the Network Optimizer page with TCP status form, tuning buttons, and repair actions.
- method NetworkOptimizerPage._load_tcp_status(self) (L1055): Show current TCP autotuning, RSS, and ECN status.
- method NetworkOptimizerPage._set_autotuning(self, level: str) (L1063): Set the TCP autotuning level, then refresh status.
- method NetworkOptimizerPage._flush_dns(self) (L1070): Flush the DNS resolver cache and report.
- method NetworkOptimizerPage._clear_arp(self) (L1076): Clear the ARP cache and report.
- method NetworkOptimizerPage._reset_winsock(self) (L1082): Reset the Winsock catalog and report.
- method NetworkOptimizerPage._repair_all(self) (L1088): Run the complete network repair sequence, then refresh status.
- class CrashDumpCleanerPage(_Page) (L1100): Windows Kernel & User Memory Dump and WER Sanitizer.
- method CrashDumpCleanerPage.__init__(self, win) (L1103): Build the Crash Dump page with stat cards, dumps table, and scan/clean actions.
- method CrashDumpCleanerPage._scan_dumps(self) (L1149): Scan crash dumps and WER reports, updating table and stat cards.
- method CrashDumpCleanerPage._clean_dumps(self) (L1166): Delete all discovered crash dumps, then rescan.

## src/cortex_unified/ui/premium/privacy_blocker_page.py — Privacy & Telemetry Blocker page — profile-based telemetry control.
- class _PrivacyWorker(QObject) (L33): Apply or revert privacy tweaks on a background thread.
- method _PrivacyWorker.__init__(self, mode: str, profile: str | None=None, tweak_ids: list[str] | None=None) (L40): Initialize worker.
- method _PrivacyWorker.cancel(self) (L52): cancel.
- method _PrivacyWorker.run(self) (L56): run.
- class PrivacyBlockerPage(_Page) (L106): Block Windows telemetry via profiles and per-category tweak control.
- method PrivacyBlockerPage.__init__(self, win) (L109): __init__.
- method PrivacyBlockerPage._discover_categories() (L216): Extract unique categories from the tweak catalog.
- method PrivacyBlockerPage._selected_tweak_ids(self) (L222): Return tweak IDs matching the chosen profile and checked categories.
- method PrivacyBlockerPage._apply(self) (L236): _apply.
- method PrivacyBlockerPage._revert(self) (L254): _revert.
- method PrivacyBlockerPage._set_busy(self, busy: bool) (L264): _set_busy.
- method PrivacyBlockerPage._on_progress(self, msg: str) (L273): _on_progress.
- method PrivacyBlockerPage._on_done(self, rows: list) (L277): _on_done.
- method PrivacyBlockerPage._fail(self, msg: str) (L302): _fail.

## src/cortex_unified/ui/premium/registry.py — The single source of truth for every tool page in the premium shell.
- class NavGroup (L44): A collapsible sidebar section.
- class PageSpec (L52): Everything the shell needs to know about one tool page.
- method PageSpec.load(self) (L71): Import and return the page class this spec points at.
- func _validate() (L912): Reject a malformed registry at import time rather than on first click.
- func ordered_ids() (L944): Every page id, grouped by sidebar section then declaration order.
- func ordered_specs() (L949): Every spec in sidebar order (group order, then declaration order).
- func grouped() (L954): Yield ``(group, pages)`` for each section in display order.
- func group_of(page_id: str) (L960): Return the group id owning *page_id*.

## src/cortex_unified/ui/premium/registry_ai_page.py — AI Registry Cleaner page — ML-powered risk scoring for registry cleanup.
- class _RegistryWorker(QObject) (L39): _RegistryWorker class.
- method _RegistryWorker.__init__(self, root: str, categories: list[str], risk_threshold: float, create_restore_point: bool=True) (L45): Initialize worker.
- method _RegistryWorker.cancel(self) (L60): cancel.
- method _RegistryWorker.run(self) (L64): run.
- class RegistryAICleanerPage(_Page) (L92): AI-enhanced registry cleaner with ML risk scoring.
- method RegistryAICleanerPage.__init__(self, win) (L97): __init__.
- method RegistryAICleanerPage._pick(self) (L179): _pick.
- method RegistryAICleanerPage._run(self) (L188): _run.
- method RegistryAICleanerPage._all_categories(self) (L216): _all_categories.
- method RegistryAICleanerPage._on_progress(self, msg: str) (L222): _on_progress.
- method RegistryAICleanerPage._on_done(self, data: dict) (L226): _on_done.
- method RegistryAICleanerPage._fail(self, msg) (L270): _fail.

## src/cortex_unified/ui/premium/report_pages.py — Reporting & recovery pages: exportable PC Health Report, Backups/Restore.
- class HealthReportWorker(QObject) (L37): Collects read-only diagnostics and writes a report in the chosen format.
- method HealthReportWorker.__init__(self, fmt: str) (L43): Store the report output format ("html", "json", or "text").
- method HealthReportWorker._collect(self) (L48): Gather system snapshot and disk health data, capturing per-section errors.
- method HealthReportWorker.run(self) (L64): Collect diagnostics, generate the report file, and emit its path and data.
- class ManifestListWorker(QObject) (L81): List cleanup backups: operation manifests + leftover-clean journals.
- method ManifestListWorker._leftover_sessions() (L94): Build read-only history rows from leftover-cleanup journals (newest first).
- method ManifestListWorker.run(self) (L124): List restore manifests plus leftover sessions and emit the combined rows.
- class RestoreWorker(QObject) (L137): Restores files from a backup manifest (dry-run or real, optional overwrite).
- method RestoreWorker.__init__(self, manifest_file: str, dry_run: bool, overwrite: bool) (L145): Store the manifest path plus dry-run and overwrite flags.
- method RestoreWorker.run(self) (L152): Run the manifest restore via RestoreManager and emit the result.
- class HealthReportPage(_Page) (L167): Generate an exportable, shareable PC health report.
- method HealthReportPage.__init__(self, win) (L170): Build the PC Health Report page: export buttons, progress, and preview card.
- method HealthReportPage._generate(self, fmt: str) (L217): Disable export buttons and run HealthReportWorker for the given format.
- method HealthReportPage._on_done(self, path: str, data: dict) (L225): Show a summary preview of the saved report and enable opening it.
- method HealthReportPage._open_last(self) (L250): Open the most recently generated report with the OS default viewer.
- method HealthReportPage._fail(self, msg: str) (L265): Re-enable export buttons and show the report error.
- class BackupsPage(_Page) (L276): List backup manifests and restore files from them.
- method BackupsPage.__init__(self, win) (L279): Build the Backups & Restore page: refresh/preview/restore buttons and a manifests table.
- method BackupsPage._on_sel(self) (L337): Enable Preview/Restore buttons based on table selection.
- method BackupsPage._load(self) (L343): Refresh the manifest list via ManifestListWorker.
- method BackupsPage._on_listed(self, manifests: list) (L349): Populate the backups table and show an empty state when none exist.
- method BackupsPage._selected_manifest(self) (L371): Return the file path of the currently selected backup row.
- method BackupsPage._preview(self) (L379): Dry-run the restore of the selected manifest and report what would happen.
- method BackupsPage._on_preview(self, res: dict) (L387): Show dry-run counts (would-restore / skipped / errors) in the status line.
- method BackupsPage._restore(self) (L395): Confirm overwrite choice, then run the real restore via RestoreWorker.
- method BackupsPage._on_restored(self, res: dict) (L418): Report restore results (restored / skipped / errors) in a dialog and status line.
- method BackupsPage._busy(self, on: bool) (L427): Toggle progress bar and action buttons while a worker runs.
- method BackupsPage._fail(self, msg: str) (L434): Clear the busy state and show the worker error with a reload retry.

## src/cortex_unified/ui/premium/s3_fifo_page.py — S3-FIFO cache policy demo – FIFO queues are all you need (SOSP'23).
- class _BenchWorker(QObject) (L28): _BenchWorker class.
- method _BenchWorker.__init__(self, capacity: int, trace_len: int=5000) (L33): __init__.
- method _BenchWorker.run(self) (L39): run.
- class S3FifoPage(_Page) (L79): Visualise and benchmark the S3-FIFO eviction policy.
- method S3FifoPage.__init__(self, win) (L82): __init__.
- method S3FifoPage._run(self) (L135): _run.
- method S3FifoPage._on_done(self, stats: dict) (L143): _on_done.
- method S3FifoPage._fail(self, msg: str) (L171): _fail.

## src/cortex_unified/ui/premium/search_optimizer_page.py — Windows Search Index Database (Windows.edb) Optimizer Page.
- class _SearchWorker(QObject) (L33): _SearchWorker class.
- method _SearchWorker.run_status(self) (L38): run_status.
- method _SearchWorker.run_compact(self) (L43): run_compact.
- method _SearchWorker.run_rebuild(self) (L48): run_rebuild.
- class SearchIndexOptimizerPage(_Page) (L54): UI page for Windows Search Index (Windows.edb) compaction and catalog reset.
- method SearchIndexOptimizerPage.__init__(self, win) (L57): __init__.
- method SearchIndexOptimizerPage._start_status_query(self) (L135): _start_status_query.
- method SearchIndexOptimizerPage._on_status_ready(self, status: SearchIndexStatus) (L149): _on_status_ready.
- method SearchIndexOptimizerPage._start_compact(self) (L167): _start_compact.
- method SearchIndexOptimizerPage._start_rebuild(self) (L181): _start_rebuild.
- method SearchIndexOptimizerPage._run_async_op(self, call_fn, status_text: str) (L195): _run_async_op.
- method SearchIndexOptimizerPage._on_op_finished(self, res: SearchIndexOperationResult) (L210): _on_op_finished.

## src/cortex_unified/ui/premium/secure_shredder_page.py — Secure File Shredder — multi-standard sanitization with verification.
- class _ShredWorker(QObject) (L39): Background worker that shreds a list of files.
- method _ShredWorker.__init__(self, file_paths: list[str], standard: ShredStandard, verify: bool) (L46): Initialize worker.
- method _ShredWorker.cancel(self) (L59): cancel.
- method _ShredWorker.run(self) (L63): run.
- class SecureShredderPage(_Page) (L117): Production-grade secure file shredder with multi-standard support.
- method SecureShredderPage.__init__(self, win) (L120): __init__.
- method SecureShredderPage._add_files(self) (L262): _add_files.
- method SecureShredderPage._add_folder(self) (L273): _add_folder.
- method SecureShredderPage._clear_list(self) (L292): _clear_list.
- method SecureShredderPage._update_file_count(self) (L299): _update_file_count.
- method SecureShredderPage._confirm_shred(self) (L320): _confirm_shred.
- method SecureShredderPage._run_shred(self, standard: ShredStandard, verify: bool) (L350): _run_shred.
- method SecureShredderPage._on_progress(self, msg: str) (L366): _on_progress.
- method SecureShredderPage._on_done(self, results: list) (L370): _on_done.
- method SecureShredderPage._fail(self, msg: str) (L407): _fail.

## src/cortex_unified/ui/premium/settings_store.py — Durable, atomically-written user settings for the premium GUI.
- func settings_path() (L46): Return the settings file path (``~/.cortex_cleaner/settings.json``).
- class SettingsStore (L51): A tiny, corruption-tolerant key/value store persisted as JSON.
- method SettingsStore.__init__(self, path: Path | None=None) (L61): __init__.
- method SettingsStore._load(self) (L69): _load.
- method SettingsStore._sanitize(self) (L87): _sanitize.
- method SettingsStore.save(self) (L98): Persist all settings atomically. Returns True on success.
- method SettingsStore.get(self, key: str, default: Any=None) (L113): get.
- method SettingsStore.set(self, key: str, value: Any) (L117): Set *key* to *value*, sanitise, and write through to disk.
- method SettingsStore.theme(self) (L126): theme.
- method SettingsStore.theme(self, value: str) (L131): theme.
- method SettingsStore.close_to_tray(self) (L136): close_to_tray.
- method SettingsStore.close_to_tray(self, value: bool) (L141): close_to_tray.
- method SettingsStore.reduced_motion(self) (L146): reduced_motion.
- method SettingsStore.reduced_motion(self, value: bool) (L151): reduced_motion.
- method SettingsStore.update_check(self) (L156): update_check.
- method SettingsStore.update_check(self, value: bool) (L161): update_check.
- method SettingsStore.leftover_restore_point(self) (L166): leftover_restore_point.
- method SettingsStore.leftover_restore_point(self, value: bool) (L171): leftover_restore_point.

## src/cortex_unified/ui/premium/skeleton.py — Skeleton shimmer: a reassuring "loading" placeholder for premium feel.
- class ShimmerSkeleton(QWidget) (L25): Animated placeholder bars used as a loading state.
- method ShimmerSkeleton.__init__(self, palette: Palette, rows: int=5, row_height: int=20, parent: QWidget | None=None) (L33): Initialize skeleton.
- method ShimmerSkeleton._get_phase(self) (L51): _get_phase.
- method ShimmerSkeleton._set_phase(self, v: float) (L55): _set_phase.
- method ShimmerSkeleton.start(self) (L63): Begin shimmering (static bars only under reduced motion).
- method ShimmerSkeleton.stop(self) (L71): stop.
- method ShimmerSkeleton.set_palette(self, palette: Palette) (L75): set_palette.
- method ShimmerSkeleton.paintEvent(self, event) (L81): paintEvent.

## src/cortex_unified/ui/premium/smoothscroll.py — Smooth momentum scrolling for a premium, non-janky scroll feel.
- class SmoothScroller(QObject) (L45): Animate a scroll area's vertical scrollbar for an eased wheel glide.
- method SmoothScroller.__init__(self, area: QAbstractScrollArea, parent: QObject | None=None) (L48): __init__.
- method SmoothScroller.eventFilter(self, obj, event) (L64): eventFilter.
- method SmoothScroller._on_wheel(self, event) (L74): _on_wheel.
- func install_smooth_scroll(area: QAbstractScrollArea) (L114): Attach smooth wheel scrolling to *area* once (idempotent). Never raises.

## src/cortex_unified/ui/premium/srum_bam_page.py — Windows BAM/DAM & SRUM Forensic Privacy Studio Page.
- class _SrumBamWorker(QObject) (L35): _SrumBamWorker class.
- method _SrumBamWorker.__init__(self, cleaner: SrumBamCleaner, entries: Optional[List[BamExecutionEntry]]=None) (L40): __init__.
- method _SrumBamWorker.run_scan(self) (L46): run_scan.
- method _SrumBamWorker.run_clean(self) (L51): run_clean.
- class SrumBamCleanerPage(_Page) (L57): UI page for BAM/DAM execution traces and SRUM metrics.
- method SrumBamCleanerPage.__init__(self, win) (L60): __init__.
- method SrumBamCleanerPage._start_scan(self) (L117): _start_scan.
- method SrumBamCleanerPage._on_scan_finished(self, report: SrumBamReport) (L131): _on_scan_finished.
- method SrumBamCleanerPage._start_clean(self) (L157): _start_clean.
- method SrumBamCleanerPage._on_clean_finished(self, cleaned_count: int) (L184): _on_clean_finished.

## src/cortex_unified/ui/premium/startup_optimizer_page.py — Startup Optimizer page — stagger/delay engine with resource-aware gating.
- class _StartupScanWorker(QObject) (L42): Background worker: enumerate all startup entries.
- method _StartupScanWorker.__init__(self) (L49): Create the scan worker with a fresh cancel event.
- method _StartupScanWorker.cancel(self) (L54): Request cooperative cancellation of the running scan.
- method _StartupScanWorker.run(self) (L58): Enumerate startup entries via StartupOptimizer and emit the list.
- class _DisableWorker(QObject) (L73): Disable selected startup entries by toggling registry values.
- method _DisableWorker.__init__(self, entries: list) (L80): Store the entries to disable and a cancel event.
- method _DisableWorker.cancel(self) (L86): Request cooperative cancellation of the disable loop.
- method _DisableWorker.run(self) (L90): Move each registry Run value into the CortexBackup subkey, emitting disabled entries.
- class _EnableWorker(QObject) (L135): Re-enable startup entries from the Cortex backup registry location.
- method _EnableWorker.__init__(self, entries: list) (L142): Store the entries to re-enable and a cancel event.
- method _EnableWorker.cancel(self) (L148): Request cooperative cancellation of the enable loop.
- method _EnableWorker.run(self) (L152): Restore each backed-up Run value to its original key, emitting re-enabled entries.
- func _entry_type_label(entry) (L209): Classify an entry as GUI, Network, Service, or Background from its flags/category.
- func _entry_matches_filter(entry, type_filter: str) (L223): Return True when the entry's type label equals the filter (or filter is "All").
- func _sort_entries(entries: list, sort_key: str) (L230): Sort entries by Name, Type, or Impact (high → low); unknown impact sorts last.
- class StartupOptimizerPage(_Page) (L251): Manage Windows startup entries — enable, disable, and inspect resource impact.
- method StartupOptimizerPage.__init__(self, win) (L254): Build the Startup Optimizer page: filter/sort bar, summary cards, and results table; auto-scans.
- method StartupOptimizerPage._run_scan(self) (L412): Disable buttons, clear the table, and start a _StartupScanWorker.
- method StartupOptimizerPage._on_scan_progress(self, msg: str) (L430): Show worker progress text in the status label.
- method StartupOptimizerPage._on_scan_done(self, entries: list) (L434): Store results, refresh table/filters, and show an empty state when nothing found.
- method StartupOptimizerPage._on_scan_fail(self, msg: str) (L453): Reset buttons and show the scan error with a retry option.
- method StartupOptimizerPage._apply_filters(self, *_args) (L462): Filter entries by type combo, sort by sort combo, and repopulate the table.
- method StartupOptimizerPage._populate_table(self, entries: list) (L474): Fill the table rows with name/type/path/command and color-coded impact status.
- method StartupOptimizerPage._update_summary(self) (L498): Refresh the Total / Enabled / Disabled / High Impact metric cards.
- method StartupOptimizerPage._selected_entries(self) (L511): Return the entries behind the currently selected table rows.
- method StartupOptimizerPage._update_buttons(self) (L518): Enable Disable/Enable buttons only when rows are selected.
- method StartupOptimizerPage._disable_selected(self) (L526): Run _DisableWorker on the selected startup entries.
- method StartupOptimizerPage._on_disable_done(self, disabled: list) (L545): Report disabled count and rescan to refresh the table.
- method StartupOptimizerPage._on_disable_fail(self, msg: str) (L555): Show the disable error with a retry option.
- method StartupOptimizerPage._enable_selected(self) (L563): Run _EnableWorker on the selected startup entries.
- method StartupOptimizerPage._on_enable_done(self, enabled: list) (L582): Report re-enabled count and rescan to refresh the table.
- method StartupOptimizerPage._on_enable_fail(self, msg: str) (L592): Show the enable error with a retry option.
- method StartupOptimizerPage._on_action_progress(self, msg: str) (L600): Show enable/disable worker progress in the status label.

## src/cortex_unified/ui/premium/states.py — Reusable loading / empty / error state panels for data-backed pages.
- class StatePanel(QWidget) (L65): Inline panel with mutually-exclusive loading / empty / error states.
- method StatePanel.__init__(self, palette: Palette, parent: QWidget | None=None) (L86): Build the panel's widgets and start hidden.
- method StatePanel.bind_content(self, *widgets: QWidget) (L102): Register the page's result widget(s) this panel stands in for.
- method StatePanel._sync_content(self) (L116): Show bound result widgets only when the panel itself is hidden.
- method StatePanel._build_ui(self) (L126): Construct the glyph, kicker, message, progress bar and retry button.
- method StatePanel.mode(self) (L189): Return the current state: loading / empty / error / hidden.
- method StatePanel.show_loading(self, text: str='Working…', current: int | None=None, total: int | None=None) (L198): Enter the Loading_State (Req 7.1).
- method StatePanel.show_empty(self, text: str) (L223): Enter the Empty_State describing the absence of results (Req 7.2).
- method StatePanel.show_error(self, message: str, on_retry: Callable[[], None] | None=None) (L228): Enter the Error_State showing ``message`` verbatim (Req 7.3, 7.5).
- method StatePanel.clear(self) (L248): Return to the hidden state so real results can be revealed (Req 7.4).
- method StatePanel._handle_retry(self) (L258): Emit retryRequested and invoke the stored retry callback, swallowing callback errors.
- method StatePanel._set_mode(self, mode: str) (L269): Apply ``mode`` as the single active state and update visibility.
- method StatePanel._tint(self, color: str) (L317): Recolor the glyph + kicker to ``color`` for the active state.
- class _HoverLift(QObject) (L345): Event filter that gently lifts its target widget upward on hover.
- method _HoverLift.__init__(self, widget: QWidget, dy: int, duration: int) (L355): Store lift distance/duration and install the hover filter on the widget.
- method _HoverLift.eventFilter(self, obj: QObject, event: QEvent) (L365): Animate upward on pointer enter and back down on leave; never consume the event.
- method _HoverLift._animate_to(self, offset: int) (L378): Animate the widget's pos to the given offset from its resting position (instant move on failure).
- class _FocusRing(QObject) (L402): Event filter that blooms an accent glow around a focused widget.
- method _FocusRing.__init__(self, widget: QWidget, accent: str) (L412): Store the accent color and install the focus filter on the widget.
- method _FocusRing.eventFilter(self, obj: QObject, event: QEvent) (L420): Apply the glow on FocusIn and remove it on FocusOut; never consume the event.
- method _FocusRing._apply(self, on: bool) (L432): Set the focusRing property (repolishing styles) and add/remove the accent drop-shadow glow.
- func install_hover_lift(widget: QWidget, dy: int=1, duration: int=motion.Duration.INSTANT) (L471): Attach a subtle upward hover-lift Micro_Interaction to ``widget`` (Req 12.5).
- func focus_ring(widget: QWidget, accent: str | None=None) (L497): Ensure ``widget`` shows a visible focus-ring affordance (Req 12.5).
- func _default_accent() (L520): Best-effort accent color for the focus ring when none is supplied.

## src/cortex_unified/ui/premium/system_pages.py — Premium GUI pages for the real system-tool backends.
- func _windows_only(page: _Page, feature: str) (L54): Return True (after showing a notice on *page*) unless on Windows.
- class PrivacyScanWorker(QObject) (L69): Background worker scanning browsers and system traces for privacy data.
- method PrivacyScanWorker.run(self) (L74): Scan browser data and system traces; emit both results.
- class PrivacyCleanWorker(QObject) (L84): Background worker deleting selected browser items and system traces.
- method PrivacyCleanWorker.__init__(self, to_clean: dict, clean_system: bool) (L89): Store the per-browser item map and the system-traces flag.
- method PrivacyCleanWorker.run(self) (L95): Clean the selected browser items (and system traces if requested).
- class StartupListWorker(QObject) (L111): Background worker listing startup items from the startup manager.
- method StartupListWorker.run(self) (L116): Fetch the startup item list; emit it as a list of dicts.
- class TaskSnapshotWorker(QObject) (L125): Full task-manager snapshot: CPU, memory reconciliation + process list.
- method TaskSnapshotWorker.run(self) (L131): Take a task-manager snapshot; emit the error or the snapshot dict.
- class NetworkWorker(QObject) (L144): Read-only snapshot of active network connections + a summary.
- method NetworkWorker.run(self) (L150): Snapshot active connections and emit them with a summary dict.
- class PrivacyPage(_Page) (L165): Scan and sweep browser data + system privacy traces.
- method PrivacyPage.__init__(self, win) (L168): Build the scan/sweep buttons, results tree and state panel.
- method PrivacyPage._scan(self) (L208): Launch the privacy scan worker with buttons disabled.
- method PrivacyPage._on_scan(self, browsers: dict, traces: dict) (L216): Populate the checkable results tree from the scan results.
- method PrivacyPage._sweep(self) (L255): Confirm and delete the checked browser/system items via a worker.
- method PrivacyPage._on_swept(self, ok: bool) (L285): Report the sweep result, then re-scan.
- method PrivacyPage._fail(self, msg: str) (L293): Re-enable the scan button and show the error with a retry.
- class StartupPage(_Page) (L299): List startup items and disable selected ones.
- method StartupPage.__init__(self, win) (L302): Build the startup table with refresh/disable controls.
- method StartupPage._load(self) (L346): Kick off the startup-items listing worker.
- method StartupPage._on_loaded(self, items: list) (L352): Fill the table with the fetched startup items.
- method StartupPage._disable(self) (L369): Confirm and disable each selected startup item, then reload.
- method StartupPage._fail(self, msg: str) (L398): Re-enable refresh and show the error with a retry.
- class ProcessesPage(_Page) (L404): Live task-manager page: CPU/memory monitor plus a sortable, searchable
- method ProcessesPage.__init__(self, win) (L408): Build summary cards, per-core bars, search/live controls and the
- method ProcessesPage._columns(self) (L533): Declare the eight process columns once, instead of filling cells.
- func ProcessesPage._columns.name_icon(p: dict) (L543): Return the process's native exe icon, or a placeholder glyph.
- method ProcessesPage._start_live(self) (L566): Load once and start the live timer if "Live" is checked.
- method ProcessesPage._toggle_live(self, on: bool) (L572): Start or stop the live refresh timer.
- method ProcessesPage._tick(self) (L580): Reload the snapshot when visible and no load is in flight.
- method ProcessesPage._load(self) (L585): Launch a snapshot worker, skipping if one is already running.
- method ProcessesPage._on_snapshot(self, snap: dict) (L596): Update cards, core bars, memory breakdown and the process model
- method ProcessesPage._render_breakdown(self, mem: dict) (L622): Set the memory one-liner and cache the detailed HTML, pushing it
- method ProcessesPage._build_breakdown_html(self, mem: dict) (L638): Build the explanatory HTML about hardware-reserved memory and why
- method ProcessesPage._toggle_why(self, on: bool) (L663): Expand/collapse the detailed memory explanation.
- method ProcessesPage._apply_filter(self) (L674): Forward the search box text to the model's proxy filter.
- method ProcessesPage._on_select(self, *_) (L683): Enable End Task when a row is selected; remember its PID.
- method ProcessesPage._restore_selection(self) (L692): Reselect the previously selected PID after model/filter changes.
- method ProcessesPage._kill(self) (L698): Confirm and end the selected process's task, then reload.
- method ProcessesPage._fail(self, msg: str) (L721): Show the snapshot error with retry, or a transient status message
- class NetworkPage(_Page) (L732): Security-minded view of active network connections and their owners.
- method NetworkPage.__init__(self, win) (L735): Build summary cards, search/live controls and the risk-coloured
- method NetworkPage._start_live(self) (L824): Load once and start the live timer if "Live" is checked.
- method NetworkPage._toggle_live(self, on: bool) (L830): Start or stop the live refresh timer.
- method NetworkPage._tick(self) (L838): Reload when visible and no load is in flight.
- method NetworkPage._load(self) (L843): Launch a connections snapshot worker, skipping if one is running.
- method NetworkPage._on_loaded(self, conns: list, summary: dict) (L853): Update the summary cards and hint, then reapply the filter.
- method NetworkPage._apply_filter(self) (L877): Filter the connections by search term and the risky-only checkbox,
- method NetworkPage._risk(c: dict) (L907): ``"external"``, ``"public"`` or ``""`` for a connection.
- method NetworkPage._risk_colour(self, c: dict) (L920): _risk_colour.
- method NetworkPage._risk_tooltip(self, c: dict) (L924): _risk_tooltip.
- method NetworkPage._process_icon(self, c: dict) (L928): Real native icon where available, else a token placeholder glyph, so
- method NetworkPage._columns(self) (L934): _columns.
- method NetworkPage._local_text(self, c: dict) (L959): _local_text.
- method NetworkPage._remote_text(self, c: dict) (L965): _remote_text.
- method NetworkPage._fill(self, rows: list[dict]) (L971): _fill.
- method NetworkPage._socket_key(c: dict) (L985): Identity of a connection, stable across refreshes.
- method NetworkPage._kill(self) (L989): _kill.
- method NetworkPage._fail(self, msg: str) (L1016): _fail.
- class UninstallerListWorker(QObject) (L1030): UninstallerListWorker class.
- method UninstallerListWorker.run(self) (L1035): run.
- class LeftoverScanWorker(QObject) (L1044): Sweep standard locations for the recently uninstalled apps' leftovers.
- method LeftoverScanWorker.__init__(self, apps: list[dict], exclusions=None) (L1050): __init__.
- method LeftoverScanWorker.cancel(self) (L1058): Cooperative stop: checked between apps and inside every sweep.
- method LeftoverScanWorker.run(self) (L1062): run.
- class OrphanScanWorker(QObject) (L1092): Find orphaned Program Files folders no installed app claims.
- method OrphanScanWorker.__init__(self, exclusions=None) (L1098): __init__.
- method OrphanScanWorker.cancel(self) (L1105): cancel.
- method OrphanScanWorker.run(self) (L1109): run.
- class LeftoverCleanWorker(QObject) (L1124): Clean a reviewed batch: one journal, one restore point, cancellable.
- method LeftoverCleanWorker.__init__(self, findings: list[dict], create_restore_point: bool=False, exclusions=None) (L1130): Initialize worker.
- method LeftoverCleanWorker.cancel(self) (L1140): Stop before the next item; items already cleaned stay cleaned.
- method LeftoverCleanWorker.run(self) (L1144): run.
- class TelemetryStatusWorker(QObject) (L1163): TelemetryStatusWorker class.
- method TelemetryStatusWorker.run(self) (L1168): run.
- class TelemetryApplyWorker(QObject) (L1177): TelemetryApplyWorker class.
- method TelemetryApplyWorker.__init__(self, restore: bool) (L1182): __init__.
- method TelemetryApplyWorker.run(self) (L1187): run.
- class RegistryScanWorker(QObject) (L1198): RegistryScanWorker class.
- method RegistryScanWorker.run(self) (L1203): run.
- class RegistryCleanWorker(QObject) (L1212): RegistryCleanWorker class.
- method RegistryCleanWorker.__init__(self, entries: list) (L1217): __init__.
- method RegistryCleanWorker.run(self) (L1222): run.
- func _level_label(level: str) (L1256): _level_label.
- func _level_color(level: str) (L1261): Traffic-light the confidence tier so review is instant.
- class _LeftoverSection (L1268): Mixin wiring the leftover scan/clean UI into UninstallerPage.
- method _LeftoverSection._build_leftover_section(self) (L1271): _build_leftover_section.
- method _LeftoverSection._persist_restore_pref(self, checked: bool) (L1345): _persist_restore_pref.
- method _LeftoverSection._exclusions_store() (L1352): _exclusions_store.
- method _LeftoverSection._keep_selected(self) (L1357): Exclude the selected findings from every future scan.
- method _LeftoverSection._pending_apps(self) (L1378): The window-level buffer of recently-uninstalled apps.
- method _LeftoverSection._scan_leftovers(self) (L1392): _scan_leftovers.
- method _LeftoverSection._scan_orphans(self) (L1411): _scan_orphans.
- method _LeftoverSection._on_leftovers(self, findings: list) (L1418): _on_leftovers.
- method _LeftoverSection._leftover_fail(self, msg: str) (L1432): _leftover_fail.
- method _LeftoverSection._selected_findings(self) (L1439): _selected_findings.
- method _LeftoverSection._on_leftover_select(self, *_) (L1454): _on_leftover_select.
- method _LeftoverSection._clean_leftovers(self) (L1460): _clean_leftovers.
- method _LeftoverSection._on_cleaned(self, outcomes: list) (L1491): _on_cleaned.
- class UninstallerPage(_Page) (L1524): List installed apps and launch their official uninstallers.
- method UninstallerPage.__init__(self, win) (L1529): __init__.
- method UninstallerPage._columns(self) (L1597): Declare the three app columns once, instead of filling cells.
- method UninstallerPage._load(self) (L1614): _load.
- method UninstallerPage._on_loaded(self, apps: list) (L1620): _on_loaded.
- method UninstallerPage._filter(self, text: str) (L1633): _filter.
- method UninstallerPage._selected_apps(self) (L1640): Every selected app record, resolved through the proxy.
- method UninstallerPage._on_select(self, *_) (L1661): _on_select.
- method UninstallerPage._uninstall(self) (L1665): _uninstall.
- method UninstallerPage._fail(self, msg: str) (L1707): _fail.
- class LeftoverScannerPage(_Page, _LeftoverSection) (L1712): Dedicated sidebar page for the post-uninstall leftover scanner.
- method LeftoverScannerPage.__init__(self, win) (L1719): __init__.
- class TelemetryPage(_Page) (L1729): Block / restore Windows telemetry (Windows, admin required to apply).
- method TelemetryPage.__init__(self, win) (L1732): __init__.
- method TelemetryPage._refresh(self) (L1772): _refresh.
- method TelemetryPage._on_status(self, status: dict) (L1777): _on_status.
- method TelemetryPage._apply(self, restore: bool) (L1787): _apply.
- method TelemetryPage._on_applied(self, ok: bool) (L1805): _on_applied.
- method TelemetryPage._fail(self, msg: str) (L1813): _fail.
- class RegistryPage(_Page) (L1820): Scan for orphaned registry entries and remove them with a backup first.
- method RegistryPage.__init__(self, win) (L1823): __init__.
- method RegistryPage._columns(self) (L1881): Declare the three entry columns once, instead of filling cells.
- method RegistryPage._scan(self) (L1889): _scan.
- method RegistryPage._on_scan(self, entries: list) (L1899): _on_scan.
- method RegistryPage._clean(self) (L1914): _clean.
- method RegistryPage._on_clean(self, removed: int, backup: str) (L1933): _on_clean.
- method RegistryPage._fail(self, msg: str) (L1941): _fail.

## src/cortex_unified/ui/premium/tablemodel.py — A reusable model/view foundation for the data-dense tables.
- func _read(record: Any, name: str) (L57): Read *name* from a dict-like or attribute-like record.
- class Column (L65): Declarative description of one table column.
- method Column.display(self, record: Any) (L96): Format a record's raw value as display text (empty string when None).
- method Column.sort_value(self, record: Any) (L101): Typed sort key for a record: sort_key if given, else the raw value.
- class RecordTableModel(QAbstractTableModel) (L109): Renders a sequence of records through a list of :class:`Column`.
- method RecordTableModel.__init__(self, columns: Sequence[Column], parent: QObject | None=None) (L116): Store the column definitions and start with zero records.
- method RecordTableModel.set_records(self, records: Sequence[Any]) (L124): Replace every row in one reset - no per-cell allocation.
- method RecordTableModel.clear(self) (L130): Remove all rows via a model reset.
- method RecordTableModel.records(self) (L135): Snapshot of the current row records as a tuple.
- method RecordTableModel.record_at(self, row: int) (L139): The record behind *row*, or ``None`` when out of range.
- method RecordTableModel.columns(self) (L146): The model's column definitions.
- method RecordTableModel.rowCount(self, parent: QModelIndex | None=None) (L152): Number of rows; 0 for any valid parent index (flat model).
- method RecordTableModel.columnCount(self, parent: QModelIndex | None=None) (L158): Number of columns; 0 for any valid parent index (flat model).
- method RecordTableModel.headerData(self, section: int, orientation: Qt.Orientation, role: int=Qt.ItemDataRole.DisplayRole) (L164): Return header data.
- method RecordTableModel.data(self, index: QModelIndex, role: int=Qt.ItemDataRole.DisplayRole) (L177): Serve display, sort, record, icon, tooltip, alignment and foreground roles per column.
- method RecordTableModel.flags(self, index: QModelIndex) (L211): Read-only enabled+selectable flags for valid indexes.
- class RecordFilterProxy(QSortFilterProxyModel) (L220): Sorts on :data:`SORT_ROLE` and filters across searchable columns.
- method RecordFilterProxy.__init__(self, parent: QObject | None=None) (L227): Sort on SORT_ROLE with dynamic sort/filter and an empty filter term.
- method RecordFilterProxy.set_filter_text(self, text: str) (L234): Set the case-folded filter term, keeping selection stable across the change.
- method RecordFilterProxy.filter_text(self) (L254): The active case-folded filter term.
- method RecordFilterProxy.filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) (L258): Filter accepts row.
- method RecordFilterProxy.lessThan(self, left: QModelIndex, right: QModelIndex) (L279): Compare typed sort-role values, falling back to string comparison on TypeError.
- class TableBinding (L299): The objects created by :func:`bind_table`, kept together.
- method TableBinding.set_records(self, records: Sequence[Any]) (L311): Replace the underlying model's rows.
- method TableBinding.set_filter_text(self, text: str) (L315): Apply filter text to the proxy.
- method TableBinding.visible_count(self) (L320): Rows passing the current filter.
- method TableBinding.selected_record(self) (L324): The record behind the current selection, sort-order safe.
- method TableBinding.select_where(self, predicate: Callable[[Any], bool]) (L338): Re-select the row whose record satisfies *predicate*.
- func bind_table(view: Any, columns: Sequence[Column], *, sort_column: int | None=None, sort_order: Qt.SortOrder=Qt.SortOrder.DescendingOrder, sortable: bool=True) (L353): Wire *view* to a model + proxy built from *columns*.

## src/cortex_unified/ui/premium/theme.py — Premium design system: color tokens, typography, and a full QSS builder.
- func _hex_to_rgb(color: str) (L43): Parse ``#RGB`` / ``#RRGGBB`` into an ``(r, g, b)`` triple, else ``None``.
- func _shade(color: str, factor: float) (L62): Return ``color`` lightened (``factor > 1``) or darkened (``factor < 1``).
- class Palette (L78): A complete set of design tokens for one theme.
- method Palette.accent_gradient(self) (L121): accent_gradient.
- method Palette.glass(self, level: 'Elevation | int') (L126): Return an ``rgba(...)`` surface fill for the given elevation ``level``.
- func build_stylesheet(p: Palette) (L202): Return a complete application QSS for the given palette.
- func load_fonts() (L810): Register any font shipped in ``resources/fonts`` with Qt.
- func apply_theme(app: 'QApplication', theme: str='dark') (L849): Apply a named theme ('dark'|'light') to the whole application.

## src/cortex_unified/ui/premium/tokens.py — Qt-free design tokens for the premium UI/UX design system.
- class Spacing (L27): Single shared spacing scale on an 8pt base unit (Req 3.4).
- class Radius (L46): Single shared corner-radius scale (Req 3.5).
- class Elevation(IntEnum) (L80): Ordered surface-depth levels, lowest (furthest) to highest (closest).
- class ElevationStyle (L96): Resolved visual treatment for a single :class:`Elevation` level.
- func _parse_hex(color: str) (L119): Parse ``#RGB`` / ``#RRGGBB`` into an ``(r, g, b)`` triple, else ``None``.
- func _rel_luminance(color: str) (L134): WCAG 2.1 relative luminance of a hex color in ``[0.0, 1.0]``.
- func _rel_luminance._lin(channel: int) (L144): _lin.
- func contrast_ratio(fg_hex: str, bg_hex: str) (L153): WCAG 2.1 contrast ratio between a foreground and background color.
- func elevation_style(palette: object, level: 'Elevation | int') (L172): Resolve the :class:`ElevationStyle` for ``level`` from a theme ``palette``.

## src/cortex_unified/ui/premium/tools_pages.py — Tool pages: Performance (power plans), Browser Extensions, Driver inventory.
- func _windows_only(page: _Page, feature: str) (L33): _windows_only.
- class PowerPlanListWorker(QObject) (L48): PowerPlanListWorker class.
- method PowerPlanListWorker.run(self) (L53): run.
- class PowerPlanSetWorker(QObject) (L62): PowerPlanSetWorker class.
- method PowerPlanSetWorker.__init__(self, guid: str) (L67): __init__.
- method PowerPlanSetWorker.run(self) (L72): run.
- class ExtensionAuditWorker(QObject) (L82): ExtensionAuditWorker class.
- method ExtensionAuditWorker.run(self) (L87): run.
- func _permissions_display(ext: dict) (L96): The permission list, trimmed to six entries with an ellipsis.
- func _version_sort_key(driver: dict) (L107): Driver versions as a zero-padded string, so 10.0.1 sorts above 9.9.9.
- func _date_sort_key(driver: dict) (L128): Driver dates as the raw ISO string the inventory already produces.
- class DriverListWorker(QObject) (L138): DriverListWorker class.
- method DriverListWorker.run(self) (L143): run.
- class PerformancePage(_Page) (L156): Switch Windows power plans - reversible, low-risk performance control.
- method PerformancePage.__init__(self, win) (L159): __init__.
- method PerformancePage._load(self) (L236): _load.
- method PerformancePage._on_listed(self, plans: list) (L242): _on_listed.
- method PerformancePage._apply(self) (L256): _apply.
- method PerformancePage._on_applied(self, ok: bool, msg: str) (L279): _on_applied.
- method PerformancePage._fail(self, msg: str) (L288): _fail.
- class BrowserExtensionsPage(_Page) (L298): Read-only inventory of installed browser extensions and permissions.
- method BrowserExtensionsPage.__init__(self, win) (L301): __init__.
- method BrowserExtensionsPage._load(self) (L372): _load.
- method BrowserExtensionsPage._on_done(self, exts: list) (L378): _on_done.
- method BrowserExtensionsPage._fail(self, msg: str) (L399): _fail.
- class DriverInventoryPage(_Page) (L409): Read-only device-driver inventory (Cortex never auto-installs drivers).
- method DriverInventoryPage.__init__(self, win) (L412): __init__.
- method DriverInventoryPage._load(self) (L476): _load.
- method DriverInventoryPage._on_done(self, drivers: list) (L483): _on_done.
- method DriverInventoryPage._fail(self, msg: str) (L495): _fail.

## src/cortex_unified/ui/premium/tray.py — Premium system tray: a background presence with a live resource monitor.
- func _render_tray_icon(palette: Palette, size: int=64) (L51): Paint a token-styled tray glyph from the palette (DPR-aware).
- class PremiumTray(QObject) (L106): A system-tray presence with a live, GUI-thread resource monitor.
- method PremiumTray.__init__(self, window, settings) (L114): __init__.
- method PremiumTray._tray_supported() (L153): _tray_supported.
- method PremiumTray.available(self) (L161): True when a tray icon is actually installed and usable.
- method PremiumTray._build_menu(self) (L167): _build_menu.
- method PremiumTray._on_activated(self, reason) (L184): _on_activated.
- method PremiumTray._restore_window(self) (L197): _restore_window.
- method PremiumTray._run_health_check(self) (L210): _run_health_check.
- method PremiumTray._quit_app(self) (L224): _quit_app.
- method PremiumTray._start_monitor(self) (L239): _start_monitor.
- method PremiumTray._sample(self) (L258): Sample CPU/RAM/disk (non-blocking) and raise cooled-down alerts.
- method PremiumTray._start_network_alert_monitor(self) (L288): Poll only the bounded outcome written by the fixed scheduled CLI.
- method PremiumTray._poll_network_outcome(self) (L295): _poll_network_outcome.
- method PremiumTray._alert(self, title: str, message: str) (L318): _alert.
- method PremiumTray.show_message(self, title: str, message: str, msecs: int=6000) (L322): Show a tray balloon notification (best-effort, never raises).
- method PremiumTray.notify_network_changes(self, changes) (L333): Show cooled-down local alerts for evidence-backed scan changes.
- method PremiumTray.refresh_theme(self, palette: Palette) (L381): Re-render the tray glyph so it matches a newly-applied theme.
- method PremiumTray.stop(self) (L390): Stop the monitor and remove the tray icon (idempotent).

## src/cortex_unified/ui/premium/video_duplicates_page.py — Video near-duplicate detection page – keyframe pHash + temporal consistence.
- class _VideoWorker(QObject) (L25): _VideoWorker class.
- method _VideoWorker.__init__(self, root: str, threshold: float=0.55) (L31): __init__.
- method _VideoWorker.cancel(self) (L40): cancel.
- method _VideoWorker.run(self) (L44): run.
- class VideoDuplicatesPage(_Page) (L59): Find temporally-similar videos (re-encodes, trims, watermarked copies).
- method VideoDuplicatesPage.__init__(self, win) (L62): __init__.
- method VideoDuplicatesPage._pick(self) (L119): _pick.
- method VideoDuplicatesPage._run(self) (L128): _run.
- method VideoDuplicatesPage._on_progress(self, msg: str) (L139): _on_progress.
- method VideoDuplicatesPage._on_done(self, groups: dict) (L143): _on_done.
- method VideoDuplicatesPage._fail(self, msg) (L176): _fail.

## src/cortex_unified/ui/premium/widgets.py — Reusable premium widgets: elevated cards, a custom circular gauge, stat
- class Card(QFrame) (L39): An elevated, rounded surface.
- method Card.__init__(self, palette: Palette, object_name: str='Card', parent=None) (L65): Resolve and store the token elevation treatment for the card's surface level.
- class StatCard(Card) (L83): A small metric tile: big number + caption.
- method StatCard.__init__(self, palette: Palette, label: str, value: str='—', parent=None) (L86): Build the tile: a big Metric value label above an uppercased caption.
- method StatCard.value(self) (L99): Return the current displayed text value.
- method StatCard.set_value(self, text: str, animate: bool=False) (L103): Set the displayed value, optionally pulsing the fade-in animation on change.
- method StatCard._pulse(self) (L110): A quick fade-in on the value - a subtle premium 'it updated' cue.
- class Badge(QLabel) (L133): A small pill for risk/status labels.
- method Badge._rgb(hex_color: str) (L143): Parse ``#RRGGBB`` -> (r, g, b); degrade to the accent blue on error.
- method Badge.__init__(self, palette: Palette, kind: str='low', text: str | None=None, parent=None) (L153): Build a pill styled from the palette's semantic color for ``kind``.
- class CircularGauge(QWidget) (L174): Animated circular progress ring with a centered value + caption.
- method CircularGauge.__init__(self, palette: Palette, caption: str='', parent=None) (L180): Initialize value/caption/glow state and the shared-motion sweep animation.
- method CircularGauge._get_value(self) (L200): Return the current animated value (0..100).
- method CircularGauge._set_value(self, v: float) (L204): Set the animated value property and repaint.
- method CircularGauge.animate_to(self, target: float, display: str | None=None) (L211): Animate the ring to a clamped target, updating the center display text.
- method CircularGauge.set_center_text(self, text: str) (L219): Replace the gauge's center readout text and repaint.
- method CircularGauge.set_glow(self, color_hex: str, radius: int=34, alpha: int=55) (L224): Enable a crisp accent glow around the progress arc.
- method CircularGauge.paintEvent(self, event) (L239): Paint the track ring, glow, gradient progress arc, and centered text.
- class CoreBars(QWidget) (L320): A compact strip of per-CPU-core usage bars, colour-coded by load.
- method CoreBars.__init__(self, palette: Palette, parent=None) (L327): Initialize with an empty per-core value list and fixed minimum height.
- method CoreBars.set_values(self, values: list[float]) (L335): Store a clamped list of per-core percentages and repaint.
- method CoreBars._bar_color(self, pct: float) (L340): Return the load color: red at 80%+, amber at 50%+, accent below.
- method CoreBars.paintEvent(self, event) (L348): Paint the per-core track/fill bars and core-number labels.
- class TrafficGraph(QWidget) (L381): A lightweight dual-line time-series graph (download + upload rates).
- method TrafficGraph.__init__(self, palette: Palette, capacity: int=120, parent=None) (L389): Initialize empty rolling download/upload sample lists with the given capacity.
- method TrafficGraph.add_sample(self, down_rate: float, up_rate: float) (L399): Append a (down, up) rate sample, trimming to the rolling window.
- method TrafficGraph.clear(self) (L408): Drop all samples and repaint.
- method TrafficGraph._fmt_rate(bps: float) (L415): Format a bytes/sec rate with the largest fitting unit.
- method TrafficGraph.paintEvent(self, event) (L424): Paint the graph: grid lines, both filled series, and the peak label.
- func TrafficGraph.paintEvent._draw(series: list[float], color: str) (L442): Draw one filled+stroked series line scaled to the window peak.
- func attach_glow(widget, color_hex: str, radius: int=26, alpha: int=130) (L481): Give ``widget`` a crisp accent glow that reads as a lit-from-within cue.
- func icon_for_exe(exe_path: str) (L521): Return a QIcon for a program's real icon (cached), or ``None``.
- func placeholder_icon(palette: Palette | None=None, size: int=32) (L557): Return a token-styled placeholder glyph for items lacking a native icon.
- func hline(palette: Palette) (L628): A thin horizontal divider.
- func status_note(palette: Palette, status: str, text: str) (L645): An icon + message row for platform notes, warnings and results.
- func title_block(title: str, subtitle: str='') (L684): A page header (title + subtitle).
- func require_feature(page_or_parent, feature) (L700): Gate a UI action behind *feature*; offer the trial when denied.

## src/cortex_unified/ui/premium/win_update_repair_page.py — Windows Update Repair page — comprehensive component reset and repair.
- class _RepairWorker(QObject) (L36): Background worker for Windows Update repair phases.
- method _RepairWorker.__init__(self, phases: list[str]) (L43): __init__.
- method _RepairWorker.cancel(self) (L49): cancel.
- method _RepairWorker.run(self) (L53): run.
- class _PreflightWorker(QObject) (L91): Run preflight diagnostics in background.
- method _PreflightWorker.run(self) (L97): run.
- class WinUpdateRepairPage(_Page) (L143): Comprehensive Windows Update component repair with phase-based control.
- method WinUpdateRepairPage.__init__(self, win) (L146): __init__.
- method WinUpdateRepairPage._run_preflight(self) (L265): _run_preflight.
- method WinUpdateRepairPage._pf_done(self, data: dict) (L274): _pf_done.
- method WinUpdateRepairPage._pf_fail(self, msg: str) (L310): _pf_fail.
- method WinUpdateRepairPage._run_repair(self) (L318): _run_repair.
- method WinUpdateRepairPage._on_progress(self, msg: str) (L352): _on_progress.
- method WinUpdateRepairPage._on_done(self, data: dict) (L356): _on_done.
- method WinUpdateRepairPage._on_fail(self, msg: str) (L388): _on_fail.

## src/cortex_unified/ui/premium/winapp2_page.py — Winapp2 Community Declarative Application Cleaner Page.
- class _Winapp2Worker(QObject) (L31): _Winapp2Worker class.
- method _Winapp2Worker.__init__(self, cleaner: Winapp2Cleaner, targets: Optional[List[AppCleanTarget]]=None) (L37): __init__.
- method _Winapp2Worker.run_scan(self) (L43): run_scan.
- method _Winapp2Worker.run_clean(self) (L48): run_clean.
- class Winapp2CleanerPage(_Page) (L58): UI page for Winapp2 community third-party application cleaning.
- method Winapp2CleanerPage.__init__(self, win) (L61): __init__.
- method Winapp2CleanerPage._start_scan(self) (L122): _start_scan.
- method Winapp2CleanerPage._on_progress(self, current: int, total: int, name: str) (L138): _on_progress.
- method Winapp2CleanerPage._on_scan_finished(self, report: Winapp2Report) (L144): _on_scan_finished.
- method Winapp2CleanerPage._start_clean(self) (L166): _start_clean.
- method Winapp2CleanerPage._on_clean_finished(self, cleaned_bytes: int, cleaned_count: int) (L194): _on_clean_finished.

## src/cortex_unified/ui/premium/window.py — The premium main window: sidebar navigation + engine-backed pages.
- func fmt_bytes(n: int) (L54): Format a byte count with the largest fitting binary unit.
- class _TitleBarChrome (L97): Read-only handle to the window's chrome: brand mark + window controls.
- method _TitleBarChrome.__init__(self, brand, min_btn, max_btn, close_btn) (L109): Store the brand mark and the three window-control buttons.
- class _LazyPageRegistry(Mapping) (L117): A ``dict[str, QWidget]``-compatible view that builds pages on demand.
- method _LazyPageRegistry.__init__(self, win: 'PremiumMainWindow') (L130): Keep the owning window and the cache of already-built pages.
- method _LazyPageRegistry.__getitem__(self, page_id: str) (L137): Build (or return cached) the page widget and add it to the stack.
- method _LazyPageRegistry.__iter__(self) (L152): Iterate page ids in sidebar/navigation order.
- method _LazyPageRegistry.__len__(self) (L157): Total number of registered pages.
- method _LazyPageRegistry.__contains__(self, page_id: object) (L161): Whether a page id exists in the registry.
- method _LazyPageRegistry.is_built(self, page_id: str) (L167): True when *page_id* has actually been constructed.
- method _LazyPageRegistry.built_ids(self) (L172): The pages constructed so far - useful for tests and diagnostics.
- class PremiumMainWindow(QMainWindow) (L179): Shell hosting all engine-backed pages.
- method PremiumMainWindow.__init__(self, theme: str='dark', settings=None) (L182): Build the frameless shell: sidebar, title bar, page stack, tray, and lazy page registry.
- method PremiumMainWindow._build_sidebar(self) (L335): Build the sidebar: brand, search box, grouped nav buttons, and status labels.
- method PremiumMainWindow.eventFilter(self, obj, event) (L518): Detect mouse enter/leave on sidebar for hover-expand.
- method PremiumMainWindow._sidebar_hover_expand(self) (L529): Temporarily expand sidebar on hover (when collapsed & not pinned).
- method PremiumMainWindow._sidebar_hover_collapse(self) (L565): Collapse sidebar after mouse leaves (when not pinned).
- method PremiumMainWindow._stop_sidebar_anim(self) (L590): Stop any running sidebar animations.
- method PremiumMainWindow._toggle_max(self) (L597): Switch between maximized and normal, updating the title-bar icon.
- method PremiumMainWindow._toggle_sidebar(self) (L609): Toggle sidebar pin: pinned = always expanded, unpinned = collapsed + hover-expand.
- method PremiumMainWindow._collapse_sidebar_content(self) (L675): Hide sidebar text content after collapse animation.
- method PremiumMainWindow._retint_nav_icons(self) (L709): Re-render sidebar icons for the active palette.
- method PremiumMainWindow._update_nav_header(self, group_id: str, expanded: bool) (L737): Set a nav group header's chevron, escaped title, and expanded style.
- method PremiumMainWindow._set_nav_section(self, group_id: str, expanded: bool) (L752): Open one nav group exclusively (accordion) and show/hide its page buttons.
- method PremiumMainWindow._filter_navigation(self, text: str) (L770): Show only nav buttons matching the search text, revealing their groups.
- method PremiumMainWindow.set_titlebar_tab_widget(self, widget: QWidget | None) (L789): Mount or unmount an external tab bar (e.g. NexusExplorer) in the top window title bar row.
- method PremiumMainWindow._select(self, page_id: str) (L801): Select a page: expand its nav group, switch the stack, fade in, and run first-visit autoload.
- method PremiumMainWindow._fade_in(self, widget: QWidget | None) (L841): Animated fade/rise when a page becomes visible.
- method PremiumMainWindow.run_worker(self, worker, on_done, on_fail=None, on_progress=None) (L860): Move *worker* to a fresh QThread and wire signals safely.
- method PremiumMainWindow._reap_threads(self) (L914): Remove and delete any finished worker threads (runs on GUI thread).
- method PremiumMainWindow._default_fail(self, msg: str) (L921): Report a worker failure via the status bar and a warning dialog.
- method PremiumMainWindow.set_theme(self, theme: str) (L926): Apply a theme app-wide, retint icons, persist the choice, and refresh the tray.
- method PremiumMainWindow.eventFilter(self, obj, event) (L944): App-level filter that turns the 6px window edge into a resize grip.
- method PremiumMainWindow._edge_at(self, gpos) (L977): Return the window edges within the resize margin of a global position.
- method PremiumMainWindow._update_edge_cursor(self, edges) (L1000): Set the resize cursor matching the hovered window edges.
- method PremiumMainWindow.resizeEvent(self, event) (L1020): Scale content margins to the window width so the layout breathes on
- method PremiumMainWindow.mousePressEvent(self, event) (L1039): Start a native window drag from the title-bar area.
- method PremiumMainWindow.mouseDoubleClickEvent(self, event) (L1049): Toggle maximize/restore on a title-bar double click.
- method PremiumMainWindow.closeEvent(self, event) (L1062): Close to tray if enabled, else stop the tray and shut down all workers.
- method PremiumMainWindow._shutdown_workers(self) (L1092): Stop every worker thread without ever destroying one mid-run.
- func PremiumMainWindow._shutdown_workers._running(t: QThread) (L1128): Whether a thread still runs; reaped/dangling wrappers count as stopped.
- class SingleScrollFilter(QObject) (L1176): Route a wheel gesture to a single Scroll_Container (Req 5.5).
- method SingleScrollFilter.__init__(self, inner: QWidget, outer: QScrollArea | None=None, parent: QObject | None=None) (L1198): Store the inner scrollable view and the outer page scroll area.
- method SingleScrollFilter.eventFilter(self, obj, event) (L1205): Route wheel events to the inner view until it hits a boundary, then to the outer area.
- method SingleScrollFilter._forward_to_outer(self, event) (L1229): Send the wheel event to the outer Scroll_Container and consume it
- func set_tab_order(parent: QWidget | None, widgets) (L1242): Chain keyboard Tab traversal across *widgets* in a predictable order.
- func ensure_focusable(*widgets) (L1266): Guarantee primary action controls can receive keyboard focus (Req 10.1).
- func run_modal(dialog, trigger: QWidget | None=None) (L1286): Show *dialog* modally and return keyboard focus to *trigger* on close.
- class _Page(QWidget) (L1315): Base page with access to the window + palette and a vertical layout.
- method _Page.__init__(self, win: PremiumMainWindow) (L1344): Set up the page: window/palette refs and an outer momentum-scrolling vertical layout.
- method _Page.pin_footer(self, widget: QWidget) (L1376): Pin *widget* below the scroll area so it is ALWAYS fully visible.
- method _Page.attach_single_scroll(self, inner: QWidget) (L1391): Route wheel gestures over ``inner`` to a single ``Scroll_Container``.
- method _Page.add_scrolling_list(self, inner: QWidget, *, stretch: int=1, minimum_height: int | None=None) (L1409): Add a list/tree/table under the page's scroll policy (Req 5.2, 5.5).
- class DashboardPage(_Page) (L1425): 1-click hero scan + reclaimable overview + category table.
- method DashboardPage.__init__(self, win: PremiumMainWindow) (L1428): Build the hero gauge, metric tiles, category tree, and pinned Clean action.
- method DashboardPage._toggle_scan(self) (L1577): Start or cancel the scan depending on current state.
- method DashboardPage._scan(self) (L1584): Launch the ScanWorker and flip the hero into scanning UI.
- method DashboardPage._cancel_scan(self) (L1598): Cancel the running scan worker and show Cancelling state.
- method DashboardPage._on_progress(self, text: str) (L1605): Show live scan progress text in the status label.
- method DashboardPage._on_scanned(self, report) (L1609): Render the CleanupReport: metrics, auto-checked category tree, risk badges, gauge.
- method DashboardPage._selected_bytes(self) (L1673): Sum of what's currently checked, respecting per-app/folder exclusions.
- method DashboardPage._update_selection(self) (L1691): Refresh the gauge + Clean button to show the live selected size.
- method DashboardPage._expand_category(self, item: QTreeWidgetItem) (L1709): Lazily populate a node's contents off the UI thread when expanded.
- method DashboardPage._apply_preview(self, nid: int, children: list) (L1759): Replace a node's placeholder with worker-computed children as checkable rows.
- method DashboardPage._preview_fail(self, msg: str) (L1797): Report a preview failure briefly in the status bar.
- method DashboardPage._on_item_changed(self, item: QTreeWidgetItem, column: int) (L1802): Track per-app / per-folder selection so cleaning respects it.
- method DashboardPage._set_subtree_check(self, item: QTreeWidgetItem, state) (L1826): Recursively apply a check state to a node's loaded checkable descendants.
- method DashboardPage._filtered_entries(self, scan, scan_idx: int) (L1836): Entries for *scan* minus any the user deselected in the preview.
- method DashboardPage._clean(self, method: str) (L1849): Clean the checked (and not excluded) categories after a confirm dialog, via CleanWorker.
- method DashboardPage._on_clean_progress(self, text: str) (L1907): Show live cleaning progress text.
- method DashboardPage._on_cleaned(self, freed: int, items: int, skipped: int) (L1911): Report freed space and skipped files, then rescan to refresh the report.
- method DashboardPage._on_fail(self, msg: str) (L1924): Reset the scan UI and surface the error via the window's default handler.
- class _FolderScanPage(_Page) (L1936): Shared scaffold for pages that pick a folder and list results.
- method _FolderScanPage.__init__(self, win: PremiumMainWindow) (L1947): Build the shared scaffold: picker card, metric strip, results table, and delete action row.
- method _FolderScanPage._build_results(self) (L2055): Subclasses construct and return their specific results widget.
- method _FolderScanPage._pick(self) (L2061): Open a folder dialog and enable the run button on selection.
- method _FolderScanPage._run(self) (L2072): Subclasses launch their specific scan worker.
- method _FolderScanPage._start(self, worker, on_done, on_fail) (L2078): Start a scan worker with live progress + cancel support.
- method _FolderScanPage._toggle_run(self) (L2093): Cancel the running worker, or start the subclass's scan.
- method _FolderScanPage._on_progress(self, text: str) (L2103): Show live scan progress text.
- method _FolderScanPage._finish(self) (L2107): Reset the run button and hide progress after a worker ends.
- method _FolderScanPage._busy(self, on: bool) (L2116): Toggle the progress indicator and run-button enablement.
- method _FolderScanPage._enable_actions(self, has_rows: bool) (L2121): Enable or disable the delete action based on whether rows exist.
- method _FolderScanPage._selected_paths(self) (L2128): Return the paths in column 0 of the currently selected table rows.
- method _FolderScanPage._delete_selected(self) (L2140): Confirm and recycle the selected rows via DeleteSelectedWorker.
- method _FolderScanPage._on_deleted(self, freed: int, ok: int, blocked: int) (L2162): Report the recycle result and rescan the folder.
- method _FolderScanPage._del_fail(self, msg: str) (L2174): Reset busy state and surface the deletion error.
- class DuplicatesPage(_FolderScanPage) (L2181): Finds byte-identical duplicate files under a chosen folder.
- method DuplicatesPage._build_results(self) (L2187): Build the two-column duplicate file / group table.
- method DuplicatesPage._run(self) (L2197): Launch the DuplicateWorker for the chosen folder.
- method DuplicatesPage._done(self, groups: dict) (L2202): Fill the table with grouped duplicates and update the metric cards.
- method DuplicatesPage._fail(self, msg) (L2223): Reset the run state and surface the error.
- class DuplicatePhotosPage(_FolderScanPage) (L2229): Finds duplicate image files under a chosen folder.
- method DuplicatePhotosPage._build_results(self) (L2236): Build the two-column duplicate photo / group table.
- method DuplicatePhotosPage._run(self) (L2245): Launch the DuplicatePhotosWorker for the chosen folder.
- method DuplicatePhotosPage._done(self, groups: dict) (L2251): Fill the table with grouped duplicate photos and update the metric cards.
- method DuplicatePhotosPage._fail(self, msg) (L2277): Reset the run state and surface the error.
- class LargeFilesPage(_FolderScanPage) (L2283): Finds large files (50 MB+) under a chosen folder, flagging AI models.
- method LargeFilesPage._build_results(self) (L2289): Build the file / size / tag results table.
- method LargeFilesPage._run(self) (L2301): Launch the LargeFilesWorker for the chosen folder.
- method LargeFilesPage._done(self, entries: list) (L2306): Fill the table, tag AI-model files as high-risk, and update metric cards.
- method LargeFilesPage._fail(self, msg) (L2343): Reset the run state and surface the error.
- class EmptyPage(_FolderScanPage) (L2349): Finds empty files and empty directories under a chosen folder.
- method EmptyPage._build_results(self) (L2355): Build the two-column path / type results table.
- method EmptyPage._run(self) (L2364): Launch the EmptyWorker for the chosen folder.
- method EmptyPage._done(self, files: list, dirs: list) (L2369): Fill the table with empty files and directories and update metric cards.
- method EmptyPage._fail(self, msg) (L2386): Reset the run state and surface the error.
- class ShredPage(_Page) (L2392): Storage-aware secure deletion, honest about SSD limitations.
- method ShredPage.__init__(self, win: PremiumMainWindow) (L2395): Build the shredder card (target picker, passes, privacy level) and the free-space wipe card.
- method ShredPage._populate_drives(self) (L2511): Fill the wipe drive combo with all existing drive letters.
- method ShredPage._wipe_free_space(self) (L2519): License-gate, confirm, and start a FreeSpaceWipeWorker on the chosen drive.
- method ShredPage._on_wiped(self, success: bool, message: str) (L2542): Report the free-space wipe result and reset the button.
- method ShredPage._on_wipe_fail(self, msg: str) (L2552): Reset the wipe UI and surface the error.
- method ShredPage._pick(self) (L2558): Choose a file, then detect its storage medium via StorageWorker.
- method ShredPage._on_medium(self, kind: str, overwrite_effective: bool) (L2570): Show the detected medium and whether overwriting is reliable on it.
- method ShredPage._shred(self) (L2579): Confirm, then shred via AdaptiveShredWorker (explicit PL / flash) or ShredWorker.
- method ShredPage._on_adaptive_done(self, outcome: str, message: str, detail: str) (L2628): Report the adaptive shred outcome and reset the picker.
- method ShredPage._on_done(self, outcome: str, reason: str) (L2639): Report the shred outcome and reset the picker.
- method ShredPage._on_refused(self, kind: str, guidance: str) (L2650): Explain why overwriting was refused for this medium and offer guidance.
- method ShredPage._fail(self, msg: str) (L2661): Reset the shred UI and surface the error.
- class SettingsPage(_Page) (L2668): Settings page: theme, tray, motion, update-check, smart suggestions, restore points.
- method SettingsPage.__init__(self, win: PremiumMainWindow) (L2670): Build the appearance/preference card plus the smart-suggestion and safety cards.
- method SettingsPage._choose_theme(self, theme: str) (L2748): Apply the chosen theme and refresh the button highlight.
- method SettingsPage._sync_theme_buttons(self) (L2753): Give the active theme's button the accent (Primary) styling.
- method SettingsPage._on_close_to_tray_toggled(self, checked: bool) (L2768): Persist the close-to-tray preference.
- method SettingsPage._on_reduced_motion_toggled(self, checked: bool) (L2772): Apply and persist the reduce-motion preference.
- method SettingsPage._on_update_check_toggled(self, checked: bool) (L2778): Persist the opt-in startup release-check preference.
- method SettingsPage._build_smart_card(self) (L2782): Build the Smart Suggestions card showing learning stats and a reset button.
- method SettingsPage._reset_smart(self) (L2808): Confirm, then wipe and reload the offline learning model.
- method SettingsPage._build_safety_card(self) (L2827): Build the restore-point card (Windows-only) with create/refresh actions and list.
- method SettingsPage._create_restore_point(self) (L2894): Start a RestorePointWorker to create a restore point.
- method SettingsPage._on_rp_created(self, status: str, message: str) (L2903): Report the create outcome per status and refresh the list.
- method SettingsPage._on_rp_fail(self, msg: str) (L2920): Reset the restore-point UI and surface the error.
- method SettingsPage._refresh_restore_points(self) (L2926): Load existing restore points via RestorePointListWorker.
- method SettingsPage._on_rp_listed(self, points: list) (L2931): Fill the restore-point table from the listed points.

## src/cortex_unified/ui/premium/workers.py — Background workers bridging the GUI to the engine.
- class ScanWorker(QObject) (L25): Runs a full category scan and emits the resulting ``CleanupReport``.
- method ScanWorker.__init__(self, max_risk: str='medium', include_disabled: bool=False) (L37): Store the risk ceiling, disabled-category flag and a shared cancel event.
- method ScanWorker.cancel(self) (L44): Signal the engine to abort the in-flight scan via the shared event.
- method ScanWorker.run(self) (L48): Run the category scan (emits finished with the CleanupReport, or failed).
- class CleanWorker(QObject) (L62): Executes deletion for a previously produced report (batched + cancellable).
- method CleanWorker.__init__(self, report: CleanupReport, method: str) (L69): Hold the report to clean, the deletion method, and a cancel event.
- method CleanWorker.cancel(self) (L76): Signal the engine to abort the in-flight clean via the shared event.
- method CleanWorker.run(self) (L80): Clean the report's categories, emitting finished (freed, cleaned, skipped) or failed.
- func CleanWorker.run._prog(done: int, total: int) (L85): Forward (done, total) counts as a human-readable progress message.
- class DuplicateWorker(QObject) (L102): Finds byte-identical duplicate files under the given roots.
- method DuplicateWorker.__init__(self, roots: list[str]) (L108): Store the root folders to scan and a cancel event.
- method DuplicateWorker.cancel(self) (L114): Signal the engine to abort the duplicate scan via the shared event.
- method DuplicateWorker.run(self) (L118): Find duplicates (emits finished with {hash: [Path, ...]} groups, or failed).
- func _norm(p) (L131): Normalize a path to Windows backslash form for prefix matching.
- func aggregate_roots(entries, roots) (L136): Aggregate scanned entries under each root folder (for a category node).
- func children_under(entries, prefix: str) (L157): Immediate files + aggregated subfolders directly under *prefix*.
- func group_by_app(entries, bases) (L205): Group scanned cache entries by their owning app (first folder after a
- class DirPreviewWorker(QObject) (L232): Compute a tree node's children off the UI thread (keeps expand snappy).
- method DirPreviewWorker.__init__(self, node_id: int, entries, mode: str, roots=None, prefix: str | None=None) (L238): Initialize worker.
- method DirPreviewWorker.run(self) (L248): Compute the node's children per mode, emitting finished (node_id, up to 400 children) or failed.
- class DuplicatePhotosWorker(QObject) (L262): Find duplicate image files only (byte-for-byte, extension-filtered).
- method DuplicatePhotosWorker.__init__(self, roots: list[str]) (L274): Store the root folders to scan and a cancel event.
- method DuplicatePhotosWorker.cancel(self) (L280): Signal the engine to abort the photo-duplicate scan via the shared event.
- method DuplicatePhotosWorker.run(self) (L284): Find duplicate images (emits finished with {hash: [Path, ...]} groups, or failed).
- class LargeFilesWorker(QObject) (L298): Finds the largest files under a root path.
- method LargeFilesWorker.__init__(self, root: str, min_mb: float) (L304): Store the scan root, minimum size in MB, and a cancel event.
- method LargeFilesWorker.cancel(self) (L311): Signal the engine to abort the large-file scan via the shared event.
- method LargeFilesWorker.run(self) (L315): Find up to 200 large files (emits finished with FileEntry list, or failed).
- class EmptyWorker(QObject) (L327): Finds empty files and empty directories under a root path.
- method EmptyWorker.__init__(self, root: str) (L333): Store the scan root and a cancel event.
- method EmptyWorker.cancel(self) (L339): Signal the engine to abort the empty-file scan via the shared event.
- method EmptyWorker.run(self) (L343): Find empty files/dirs (emits finished with both lists, or failed).
- class DeleteSelectedWorker(QObject) (L352): Delete an arbitrary list of paths via the safe SecureDeleter.
- method DeleteSelectedWorker.__init__(self, paths: list[str], method: str) (L358): Store the paths to delete and the deletion method.
- method DeleteSelectedWorker.run(self) (L364): Delete the given paths (emits finished with (freed, succeeded, blocked), or failed).
- class RestorePointWorker(QObject) (L380): Create a Windows System Restore point (PowerShell-backed, so threaded).
- method RestorePointWorker.__init__(self, description: str='Cortex Cleaner') (L386): Store the restore-point description text.
- method RestorePointWorker.run(self) (L391): Create a restore point (emits finished with (status, message), or failed).
- class RestorePointListWorker(QObject) (L401): List existing restore points (read-only).
- method RestorePointListWorker.run(self) (L407): List restore points (emits finished with the list, or failed).
- class StorageWorker(QObject) (L416): Detect the storage medium behind a path (subprocess-backed, so threaded).
- method StorageWorker.__init__(self, path: str) (L422): Store the path whose storage medium to detect.
- method StorageWorker.run(self) (L427): Detect the storage kind (emits finished with (kind, overwrite_effective), or failed).
- class FreeSpaceWipeWorker(QObject) (L437): Overwrite a volume's free space (Windows cipher /w). Long-running.
- method FreeSpaceWipeWorker.__init__(self, drive_letter: str) (L443): Store the drive letter to wipe and a cancel event.
- method FreeSpaceWipeWorker.cancel(self) (L449): Signal cancellation; kills the cipher /w process tree promptly.
- method FreeSpaceWipeWorker.run(self) (L457): Wipe the volume's free space (emits finished with (success, message), or failed).
- class ShredWorker(QObject) (L467): Storage-aware secure deletion of a single target.
- method ShredWorker.__init__(self, target: str, passes: int, force_flash: bool) (L474): Store the target, overwrite pass count, and flash-overwrite override.
- method ShredWorker.run(self) (L481): Shred one target (emits finished (outcome, reason), refused, or failed).
- class AdaptiveShredWorker(QObject) (L501): Adaptive PL0-PL3 shred (HolePunch/PULSE/WAS-Deletion).
- method AdaptiveShredWorker.__init__(self, target: str, level: str | None=None, verify: bool=True) (L511): Store the target, privacy level (None/auto or pl0-pl3), and verify flag.
- method AdaptiveShredWorker.run(self) (L518): Adaptive shred (emits finished with (outcome, message, detail), or failed).
- class VhdxListWorker(QObject) (L545): Discovers WSL / Docker / Hyper-V virtual disks (read-only).
- method VhdxListWorker.__init__(self) (L552): Create the shared cancel event for the discovery run.
- method VhdxListWorker.cancel(self) (L557): Signal cancellation of the virtual-disk discovery.
- method VhdxListWorker.run(self) (L561): Discover virtual disks (emits finished with VirtualDisk list, or failed).
- class WslShutdownWorker(QObject) (L576): Runs ``wsl --shutdown`` so virtual disks can be detached and compacted.
- method WslShutdownWorker.run(self) (L583): Shut down WSL (emits finished with (ok, message), or failed).
- class VhdxCompactWorker(QObject) (L594): Compacts one or more virtual disks, reporting measured space returned.
- method VhdxCompactWorker.__init__(self, disks: list) (L606): Store the disks to compact and a cancel event.
- method VhdxCompactWorker.cancel(self) (L612): Signal cancellation; stops between disks, not mid-compaction.
- method VhdxCompactWorker.run(self) (L616): Compact each disk (emits finished with CompactResult list, or failed).
- class VhdxSparseWorker(QObject) (L635): Turns on WSL sparse mode so the bloat doesn't come back.
- method VhdxSparseWorker.__init__(self, disk, enabled: bool=True) (L642): Store the disk and whether sparse mode should be enabled.
- method VhdxSparseWorker.run(self) (L648): Toggle WSL sparse mode (emits finished with (ok, message), or failed).
- class ComponentStoreAnalyzeWorker(QObject) (L663): Runs DISM /AnalyzeComponentStore and inventories upgrade leftovers.
- method ComponentStoreAnalyzeWorker.__init__(self) (L674): Create the cancel event for the analysis run.
- method ComponentStoreAnalyzeWorker.cancel(self) (L679): Signal cancellation of the component-store analysis.
- method ComponentStoreAnalyzeWorker.run(self) (L683): Analyze the component store (emits finished with (analysis, leftovers), or failed).
- class ComponentStoreCleanWorker(QObject) (L705): Runs DISM /StartComponentCleanup (optionally /ResetBase).
- method ComponentStoreCleanWorker.__init__(self, reset_base: bool=False) (L712): Store whether ResetBase should be included in the cleanup.
- method ComponentStoreCleanWorker.run(self) (L717): Run component-store cleanup (emits finished with CleanupOutcome, or failed).
- class ServicingTaskWorker(QObject) (L728): Triggers Windows' own scheduled component-cleanup task.
- method ServicingTaskWorker.run(self) (L735): Trigger the servicing task (emits finished with (ok, message), or failed).
- class LeftoverDeleteWorker(QObject) (L746): Deletes selected upgrade leftovers through the engine's guarded deleter.
- method LeftoverDeleteWorker.__init__(self, paths: list[str], sizes: dict[str, int] | None=None) (L757): Store the leftover paths, optional size map, and a cancel event.
- method LeftoverDeleteWorker.cancel(self) (L764): Signal cancellation of the leftover deletion run.
- method LeftoverDeleteWorker.run(self) (L768): Delete leftovers (emits finished with (freed, removed, blocked), or failed).
- class ProjectCacheScanWorker(QObject) (L790): Scans target folders for developer project caches across enabled categories.
- method ProjectCacheScanWorker.__init__(self, target_folders: list[str], keep_recent_days: int=7, enabled_categories: list[str] | None=None) (L797): Store target folders, retention days, categories, and a cancel event.
- method ProjectCacheScanWorker.cancel(self) (L805): Signal cancellation of the project-cache scan.
- method ProjectCacheScanWorker.run(self) (L809): Scan project caches (emits finished with resources, or failed).
- func ProjectCacheScanWorker.run._prog(status: str, items: int, size: int) (L817): Relay the scanner's (status, items, bytes) progress to the signal.
- class ProjectCacheCleanWorker(QObject) (L833): Cleans selected project caches off-thread; dry run by default.
- method ProjectCacheCleanWorker.__init__(self, resources: list[dict], dry_run: bool=True) (L840): Store the resources to clean, the dry-run flag, and a cancel event.
- method ProjectCacheCleanWorker.cancel(self) (L847): Signal cancellation of the cache cleanup run.
- method ProjectCacheCleanWorker.run(self) (L851): Clean project caches (emits finished with a results dict, or failed).
- func ProjectCacheCleanWorker.run._prog(done: int, total: int, freed: int) (L859): Relay (done, total, freed) cleanup progress to the signal.
- class AutoProjectCacheWorker(QObject) (L878): Walks all fixed drives (or known D:\code) for PROJECT_CACHE_CATEGORIES.
- method AutoProjectCacheWorker.__init__(self, enabled_categories: list[str] | None=None, keep_recent_days: int=7) (L885): Store enabled categories, retention days, and a cancel event.
- method AutoProjectCacheWorker.cancel(self) (L892): Signal cancellation of the auto-discovery scan.
- method AutoProjectCacheWorker.run(self) (L896): Auto-discover project caches (emits finished with resources, or failed).
- func AutoProjectCacheWorker.run._prog(msg: str, items: int, size: int) (L903): Relay the discovery progress (message, items, bytes) to the signal.
- class CacheLogSweepWorker(QObject) (L918): Finds large logs (*.log/*.txt) across user-selected roots (D:\code).
- method CacheLogSweepWorker.__init__(self, roots: list[str], min_size_mb: float=100.0) (L925): Store the roots to sweep, minimum log size, and a cancel event.
- method CacheLogSweepWorker.cancel(self) (L932): Signal cancellation of the log sweep.
- method CacheLogSweepWorker.run(self) (L936): Find large logs (emits finished with (Path, size) pairs, or failed).
- class DockerFsCacheWorker(QObject) (L949): Measures Docker Desktop filesystem cache (AppData\Local\Docker).
- method DockerFsCacheWorker.run(self) (L955): Measure Docker's filesystem cache (emits finished with a size dict, or failed).
- class WslListWorker(QObject) (L964): Lists WSL distros + their ext4.vhdx sizes.
- method WslListWorker.run(self) (L970): List WSL distros (emits finished with distro dicts, or failed).
- class LargeFileAiWorker(QObject) (L979): Finds large files and tags AI models vs other.
- method LargeFileAiWorker.__init__(self, root: str, min_mb: float=100.0) (L986): Store the scan root, minimum size in MB, and a cancel event.
- method LargeFileAiWorker.cancel(self) (L993): Signal cancellation of the large-file scan.
- method LargeFileAiWorker.run(self) (L997): Split large files into non-AI and AI-model lists, emitting finished with both.

## src/cortex_unified/ui/premium/wsl_page.py — WSL Cleaner page: list distros + compact ext4.vhdx.
- class _WslListWorker(QObject) (L35): _WslListWorker class.
- method _WslListWorker.run(self) (L39): run.
- class _WslShutdownWorker(QObject) (L48): _WslShutdownWorker class.
- method _WslShutdownWorker.run(self) (L52): run.
- class WslPage(_Page) (L62): List WSL distros, show ext4.vhdx sizes, shutdown + compact.
- method WslPage.__init__(self, win) (L65): __init__.
- method WslPage._load(self) (L124): _load.
- method WslPage._on_list(self, distros) (L136): _on_list.
- method WslPage._shutdown(self) (L171): _shutdown.
- method WslPage._on_shutdown(self, ok: bool, msg: str) (L187): _on_shutdown.
- method WslPage._compact(self) (L198): _compact.
- class _Compact(QObject) (L231): _Compact class.
- func WslPage._compact.__init__(self, paths) (L235): __init__.
- func WslPage._compact.run(self) (L239): run.
- method WslPage._on_compact(self, results) (L252): _on_compact.
- method WslPage._fail(self, msg: str) (L266): _fail.

## src/cortex_unified/ui/safety/__init__.py — Safety infrastructure for Cortex Cleaner GUI operations.
- (no classes/functions — constants/imports only)

## src/cortex_unified/ui/safety/manifest_system.py — Atomic manifest creation and operation logging system.
- class ManifestError(DeepCleanerError) (L15): Exception raised for manifest system errors.
- class ManifestSystem (L19): Manages atomic manifest creation and operation logging.
- method ManifestSystem.__init__(self, manifest_dir: Optional[str]=None, logger: Optional[logging.Logger]=None) (L22): Initialize manifest system.
- method ManifestSystem._get_default_manifest_dir(self) (L40): _get_default_manifest_dir.
- method ManifestSystem.create_operation_manifest(self, operation_type: str, parameters: Dict[str, Any]=None) (L47): Create atomic manifest with unique operation ID.
- method ManifestSystem._get_user_info(self) (L96): Get current user information.
- method ManifestSystem._get_os_info(self) (L113): _get_os_info.
- method ManifestSystem.log_file_action(self, op_id: str, action_type: str, file_path: Path, action: str, **kwargs) (L123): Log individual file operation.
- method ManifestSystem._calculate_file_hash(self, file_path: Path) (L189): Calculate SHA256 hash of a file.
- method ManifestSystem.log_error(self, op_id: str, error: Exception, context: Dict[str, Any]=None) (L200): Log an error for an operation.
- method ManifestSystem.finalize_manifest(self, op_id: str, success: bool=True) (L233): Finalize and atomically write manifest to disk.
- method ManifestSystem.get_restore_operations(self, manifest_path: Path) (L293): Generate restore actions from manifest.
- method ManifestSystem.list_manifests(self, limit: int=None) (L342): List available manifests.
- method ManifestSystem.get_manifest_details(self, manifest_path: Path) (L391): Get full details of a specific manifest.
- method ManifestSystem.cleanup_old_manifests(self, keep_days: int=30) (L407): Clean up old manifest files.

## src/cortex_unified/ui/safety/path_validator.py — Path validation with OS-specific safety rules and symlink protection.
- class PathValidationError(DeepCleanerError) (L12): Exception raised for path validation errors.
- class PathValidator (L16): Validates file paths for safe operations with OS-specific rules.
- method PathValidator.__init__(self, logger: Optional[logging.Logger]=None) (L19): Initialize path validator.
- method PathValidator._get_critical_directories(self) (L33): Get OS-specific critical directories that should never be deleted.
- method PathValidator.add_user_whitelist(self, path: str) (L72): Add a path to user whitelist (allows deletion even if normally protected).
- method PathValidator.add_blacklist(self, path: str) (L82): Add a path to additional blacklist (prevents deletion).
- method PathValidator.is_safe_to_delete(self, path: Path) (L92): Check if a path is safe to delete.
- method PathValidator._is_critical_directory(self, path: Path) (L142): Check if path is a critical system directory.
- method PathValidator._is_under_critical_directory(self, path: Path) (L159): Check if path is under a critical system directory.
- method PathValidator.check_symlink_safety(self, path: Path) (L177): Check if symlink operations are safe (prevents symlink attacks).
- method PathValidator.validate_user_permissions(self, path: Path) (L229): Check if user has appropriate permissions for the operation.
- method PathValidator.validate_operation_paths(self, paths: List[Path]) (L288): Validate multiple paths for safe operations.
- method PathValidator.get_validation_summary(self, paths: List[Path]) (L323): Get a summary of path validation results.
- method PathValidator._get_blocking_reason(self, path: Path) (L354): Get the reason why a path is blocked.

## src/cortex_unified/ui/safety/process_manager.py — Safe external command execution manager.
- class ProcessError(DeepCleanerError) (L16): Exception raised for process execution errors.
- class ProcessTimeoutError(ProcessError) (L20): Exception raised when process execution times out.
- class ExecutableNotFoundError(ProcessError) (L24): Exception raised when executable is not found.
- class ProcessResult (L29): Result of a process execution.
- class ProcessManager (L38): Manages safe external command execution.
- method ProcessManager.__init__(self, logger: Optional[logging.Logger]=None) (L41): Initialize process manager.
- method ProcessManager.set_security_policy(self, allowed_executables: List[str]=None, blocked_executables: List[str]=None, max_execution_time: int=None, max_output_size: int=None) (L63): Set security policy for process execution.
- method ProcessManager.validate_executable(self, executable: str) (L87): Validate and locate executable.
- method ProcessManager.sanitize_command_args(self, args: List[str]) (L137): Sanitize command arguments for safe execution.
- method ProcessManager.execute_safe_command(self, cmd: List[str], timeout: int=None, cwd: Union[str, Path]=None, env: Dict[str, str]=None, capture_output: bool=True) (L172): Safely execute external command with validation and monitoring.
- method ProcessManager.execute_with_progress(self, cmd: List[str], progress_callback=None, **kwargs) (L319): Execute command with progress monitoring.
- method ProcessManager.kill_all_processes(self) (L346): Kill all running processes managed by this instance.
- method ProcessManager.get_running_processes(self) (L376): Get information about currently running processes.
- method ProcessManager.cleanup(self) (L399): Clean up all resources and kill running processes.
- method ProcessManager.__del__(self) (L408): Destructor to ensure cleanup.

## src/cortex_unified/ui/safety/safety_manager.py — Central safety manager that coordinates all safety components.
- class OperationType(Enum) (L18): Types of operations that can be performed.
- class ValidationResult(Enum) (L26): Result of operation validation.
- class Operation (L33): Represents a file system operation.
- class OperationResult (L47): Result of an operation execution.
- class SafetyError(DeepCleanerError) (L59): Exception raised for safety-related errors.
- class SafetyManager (L63): Central safety manager that coordinates all safety components.
- method SafetyManager.__init__(self, config: Config=None, logger: Optional[logging.Logger]=None) (L66): Initialize safety manager.
- method SafetyManager._setup_system_blacklists(self) (L99): Setup enhanced system directory blacklists.
- method SafetyManager.configure_safety_settings(self, require_confirmation: bool=None, default_dry_run: bool=None, enforce_dry_run_first: bool=None, max_batch_size: int=None, max_file_size_mb: int=None, validation_timeout: int=None) (L135): Configure safety settings.
- method SafetyManager.add_validation_callback(self, callback: Callable[[Operation], bool]) (L168): Add custom validation callback.
- method SafetyManager.create_operation(self, operation_type: OperationType, paths: List[Union[str, Path]], description: str='', **parameters) (L177): Create a new operation with automatic ID generation.
- method SafetyManager.add_path_whitelist(self, path: Union[str, Path]) (L210): Add path to safety whitelist.
- method SafetyManager.add_path_blacklist(self, path: Union[str, Path]) (L218): Add path to safety blacklist.
- method SafetyManager.validate_operation(self, operation: Operation) (L226): Enhanced operation validation pipeline with comprehensive safety checks.
- method SafetyManager._validate_basic_requirements(self, operation: Operation) (L295): Phase 1: Basic validation requirements.
- method SafetyManager._requires_dry_run_enforcement(self, operation: Operation) (L308): Check if operation requires dry-run enforcement.
- method SafetyManager._enforce_dry_run_policy(self, operation: Operation) (L315): Phase 2: Enforce dry-run policy for destructive operations.
- method SafetyManager._get_dry_run_key(self, operation: Operation) (L335): Generate a key for tracking dry-run results.
- method SafetyManager._validate_path_safety(self, operation: Operation) (L342): Phase 3: Enhanced path safety validation.
- method SafetyManager._validate_resource_limits(self, operation: Operation) (L372): Phase 4: Validate resource limits and file sizes.
- method SafetyManager._run_custom_validations(self, operation: Operation) (L406): Phase 5: Run custom validation callbacks.
- method SafetyManager._validate_operation_specific(self, operation: Operation) (L419): Phase 6: Operation-specific validation.
- method SafetyManager._validate_delete_operation(self, operation: Operation) (L434): _validate_delete_operation.
- method SafetyManager._validate_clean_operation(self, operation: Operation) (L442): _validate_clean_operation.
- method SafetyManager._validate_move_operation(self, operation: Operation) (L449): _validate_move_operation.
- method SafetyManager._validate_analyze_operation(self, operation: Operation) (L466): _validate_analyze_operation.
- method SafetyManager._validate_restore_operation_enhanced(self, operation: Operation) (L473): Enhanced validation for restore operations.
- method SafetyManager._validate_restore_operation(self, operation: Operation) (L500): Validate restore operation specifics.
- method SafetyManager.execute_safe_operation(self, operation: Operation) (L520): Execute operation with enhanced safety protocols and dry-run enforcement.
- method SafetyManager._should_enforce_dry_run(self, operation: Operation) (L604): Check if we should enforce a dry-run before actual execution.
- method SafetyManager._execute_mandatory_dry_run(self, operation: Operation) (L619): Execute a mandatory dry-run before the actual operation.
- method SafetyManager._execute_operation_with_monitoring(self, operation: Operation, manifest_id: str) (L646): Execute operation with enhanced monitoring and error handling.
- method SafetyManager._finalize_operation_execution(self, operation: Operation, manifest_id: str, execution_result: Dict[str, Any], execution_start: datetime) (L680): Finalize operation execution with comprehensive result generation.
- method SafetyManager._store_dry_run_result(self, operation: Operation, result: OperationResult) (L725): _store_dry_run_result.
- method SafetyManager.get_dry_run_result(self, operation: Operation) (L734): Get stored dry-run result for an operation pattern.
- method SafetyManager.clear_dry_run_cache(self, max_age_hours: int=24) (L746): Clear old dry-run results from cache.
- method SafetyManager._execute_delete_operation(self, operation: Operation, manifest_id: str) (L773): Execute delete operation.
- method SafetyManager._execute_clean_operation(self, operation: Operation, manifest_id: str) (L825): Execute clean operation (similar to delete but with additional safety checks).
- method SafetyManager._execute_move_operation(self, operation: Operation, manifest_id: str) (L838): Execute move operation.
- method SafetyManager._execute_analyze_operation(self, operation: Operation, manifest_id: str) (L892): Execute analyze operation (read-only analysis).
- method SafetyManager._execute_restore_operation(self, operation: Operation, manifest_id: str) (L924): Execute restore operation.
- method SafetyManager.get_operation_history(self, limit: int=50) (L982): Get history of operations.
- method SafetyManager.get_restore_candidates(self) (L993): Get operations that can be restored.
- method SafetyManager.get_pending_operations(self) (L1011): Get list of pending operations.
- method SafetyManager.get_operation_by_id(self, operation_id: str) (L1019): Get operation by ID.
- method SafetyManager.cancel_operation(self, operation_id: str) (L1030): Cancel a pending operation.
- method SafetyManager.get_safety_status(self) (L1045): Get comprehensive safety manager status.
- method SafetyManager.validate_system_safety(self) (L1072): Perform system-wide safety validation.
- method SafetyManager.cleanup_resources(self) (L1121): Clean up all safety manager resources.
- method SafetyManager.__del__(self) (L1158): Destructor to ensure cleanup.

## src/cortex_unified/ui/tabs/__init__.py — GUI tabs module for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/ui/tabs/base_tab.py — Base tab class for Cortex Cleaner GUI tabs with safety manager integration.
- class BaseTab(QWidget) (L16): Base class for all GUI tabs with safety manager integration and internationalization support.
- method BaseTab.__init__(self, config: Config, logger: logging.Logger, safety_manager: SafetyManager) (L25): Initialize base tab with safety manager integration.
- method BaseTab.__getattr__(self, name) (L48): Proxy missing logic methods to the main window.
- func BaseTab.__getattr__.lazy_call(*args, **kwargs) (L61): Defer the proxied call to the main window attribute, logging any failure.
- method BaseTab.set_status(self, text: str) (L71): Update the main window's status bar text safely.
- method BaseTab._initialize_tab(self) (L85): Initialize the tab with proper setup sequence.
- method BaseTab.setup_ui(self) (L100): Set up the user interface. Must be implemented by subclasses.
- method BaseTab.setup_connections(self) (L104): Set up signal connections. Can be overridden by subclasses.
- method BaseTab.setup_tooltips(self) (L109): Set up tooltips. Can be overridden by subclasses.
- method BaseTab.update_translations(self) (L113): Update UI text for internationalization. Can be overridden by subclasses.
- method BaseTab.tr(self, key: str, **kwargs) (L117): Translate text key with optional parameters.
- method BaseTab.request_operation(self, operation_type: OperationType, paths: List[Path], description: str='', **parameters) (L129): Request an operation through the safety layer.
- method BaseTab._handle_operation_request(self, operation: Operation) (L163): Handle operation request with validation and execution.
- method BaseTab._execute_operation(self, operation: Operation) (L197): Execute validated operation.
- method BaseTab.confirm_and_execute_operation(self, operation: Operation) (L223): Confirm and execute an operation that requires user confirmation.
- method BaseTab.get_current_operation(self) (L250): Get the current operation being processed.
- method BaseTab.cleanup(self) (L258): Clean up resources when tab is closed.
- method BaseTab.add_worker_thread(self, thread: QThread) (L296): Add a worker thread to be managed.
- method BaseTab.remove_worker_thread(self, thread: QThread) (L306): Remove a worker thread from management.
- method BaseTab.format_bytes(self, bytes_value: int) (L317): Format bytes to human readable format.
- method BaseTab.get_tab_info(self) (L335): Get information about this tab.
- method BaseTab.validate_paths(self, paths: List[Path]) (L349): Validate paths using the safety manager.
- method BaseTab.is_path_safe(self, path: Path) (L364): Check if a single path is safe for operations.
- method BaseTab.get_operation_history(self, limit: int=10) (L379): Get recent operation history.
- method BaseTab.__del__(self) (L394): Destructor to ensure cleanup.

## src/cortex_unified/ui/tabs/broken_links_tab.py — Tab for broken links tab in Cortex Cleaner GUI.
- class BrokenLinksWorker(QThread) (L25): Scans for broken symlinks/shortcuts/registry refs off the GUI thread.
- method BrokenLinksWorker.__init__(self, scan_path, scan_symlinks, scan_shortcuts, scan_registry) (L30): Store the scan path and the three scan-type flags.
- method BrokenLinksWorker.run(self) (L40): Run the broken links scan.
- class LinkRepairWorker(QThread) (L60): Runs safe repair (recycle shortcuts / remove dangling links) in background.
- method LinkRepairWorker.__init__(self, items, use_trash=True, dry_run=False, create_backups=False) (L65): Store the link items plus trash/dry-run/backup options.
- method LinkRepairWorker.run(self) (L75): Back up shortcuts if asked, then repair (emits finished with outcomes, or error).
- class BrokenLinksTab(BaseTab) (L94): Tab for broken links tab functionality.
- method BrokenLinksTab.__init__(self, config, logger, safety_manager) (L97): Initialize the tab and call setup_ui.
- method BrokenLinksTab.setup_ui(self) (L103): Set up the user interface.
- method BrokenLinksTab.select_all(self) (L203): Select every row in the broken-links table.
- method BrokenLinksTab.deselect_all(self) (L209): Clear the table's selection.
- method BrokenLinksTab.browse_broken_links_path(self) (L215): Browse for broken links scan path.
- method BrokenLinksTab.on_broken_links_selection_changed(self) (L221): Handle broken links table selection changes.
- method BrokenLinksTab.start_broken_links_scan(self) (L226): Start broken links scan via worker thread.
- method BrokenLinksTab._on_worker_finished(self, worker) (L255): Unregister a finished worker thread and delete it.
- method BrokenLinksTab.on_broken_links_scan_finished(self, results) (L262): Handle broken links scan completion.
- method BrokenLinksTab.on_broken_links_scan_error(self, error_message) (L305): Reset the scan controls and report the scan error.
- method BrokenLinksTab.repair_selected_links(self) (L313): Repair the selected broken links (safe actions only).
- method BrokenLinksTab.on_repair_finished(self, outcomes) (L378): Handle repair completion and report per-item outcomes.
- method BrokenLinksTab.on_repair_error(self, error_message) (L395): Reset the repair controls and report the repair error.
- method BrokenLinksTab.export_broken_links_results(self) (L403): Export the last scan's broken links to a JSON file.

## src/cortex_unified/ui/tabs/dashboard_tab.py — Dashboard tab — the command center for Cortex Cleaner.
- class OptimizerWorker(QObject) (L27): Deletes junk files discovered by SmartScan.
- method OptimizerWorker.__init__(self) (L34): Create the optimizer with a dedicated logger and a clear stop flag.
- method OptimizerWorker.run(self) (L40): Delete temp files, Prefetch contents, and thumbnail caches.
- method OptimizerWorker.stop(self) (L118): Request a cooperative stop by setting the cancel flag.
- class DashboardTab(BaseTab) (L127): Modern dashboard with Smart Scan and real Optimize Now.
- method DashboardTab.__init__(self, config, logger, safety_manager, parent=None) (L130): Initialize the tab and track the scan/optimizer threads and last report.
- method DashboardTab.setup_ui(self) (L142): Build the dashboard layout.
- method DashboardTab.setup_tooltips(self) (L254): Set the Smart Scan button tooltip.
- method DashboardTab.run_smart_scan(self) (L260): Run SmartScannerWorker on a background QThread.
- method DashboardTab._on_progress(self, msg, pct) (L288): Forward scanner progress to the status label and progress bar.
- method DashboardTab._on_scan_finished(self, report: SmartScanReport) (L293): Display the finished SmartScanReport.
- method DashboardTab._on_scan_error(self, msg) (L332): Re-enable the scan button and show a critical error dialog.
- method DashboardTab.run_optimization(self) (L341): Clean junk found by the last scan using OptimizerWorker.
- method DashboardTab._on_optimize_done(self, result: dict) (L386): Show freed space and skipped-file counts after optimization.
- method DashboardTab._on_optimize_error(self, msg) (L403): Re-enable the optimize button and show the failure dialog.
- method DashboardTab.navigate_to(self, tab_name) (L412): Switch to the named tab via the parent window's navigation controller.

## src/cortex_unified/ui/tabs/deep_cleaner_tab.py — Tab for deep disk cleaning in Cortex Cleaner GUI.
- class DeepCleanerWorker(QThread) (L22): Runs the deep junk scan (temp/cache/logs/orphans) off the GUI thread.
- method DeepCleanerWorker.__init__(self, config: Config) (L29): Store the config and the run flag for the progress poller.
- method DeepCleanerWorker.run(self) (L37): Find junk and emit finished_scan with [items, stats] (or error_occurred).
- func DeepCleanerWorker.run.poll_progress() (L43): Pulse the indeterminate progress bar every 0.1s while scanning.
- func DeepCleanerWorker.run.update_status(msg) (L54): Relay the cleaner's status text via status_updated.
- class DeepCleanerTab(BaseTab) (L72): Tab for deep cleaner functionality (Temp, Cache, Logs, Orphans).
- method DeepCleanerTab.__init__(self, config, logger, safety_manager) (L75): Initialize the tab and call setup_ui.
- method DeepCleanerTab.setup_ui(self) (L81): Build the tab: action buttons, progress bar, and the 4-column junk tree.
- method DeepCleanerTab.start_scan(self) (L153): Disable actions and launch the DeepCleanerWorker.
- method DeepCleanerTab.format_bytes(self, bytes_count: int) (L173): Format a byte count with the largest fitting binary unit.
- method DeepCleanerTab.scan_finished(self, result) (L183): Fill the tree with categorized junk items (orphans highlighted) and stats.
- method DeepCleanerTab._on_item_changed(self, item, column) (L234): Handle cascade checking/unchecking logic
- method DeepCleanerTab.update_selection_summary(self) (L266): Update the Clean button label with the checked item count.
- method DeepCleanerTab.scan_error(self, error) (L283): Show the scan error in the status label and a dialog.
- method DeepCleanerTab.start_clean(self) (L290): Confirm, then recycle the checked items via Deleter and rescan.
- method DeepCleanerTab.select_all(self) (L347): Check every item in the tree.
- method DeepCleanerTab.deselect_all(self) (L353): Uncheck every item in the tree.
- method DeepCleanerTab._toggle_checkboxes(self, state) (L359): Set all parent and child check states without firing change signals.
- method DeepCleanerTab.operation_finished(self, worker) (L373): Hide progress, re-enable scanning, and reap the finished worker.

## src/cortex_unified/ui/tabs/disk_analyzer_tab.py — Tab for disk analyzer tab in Cortex Cleaner GUI.
- class DiskAnalyzerWorker(QThread) (L31): Runs disk usage/type/largest-dir analysis off the GUI thread.
- method DiskAnalyzerWorker.__init__(self, config: Config, path: str) (L36): Store the config and the target path to analyze.
- method DiskAnalyzerWorker.run(self) (L45): Run the disk analysis process.
- class DiskAnalyzerTab(BaseTab) (L67): Tab for disk analyzer tab functionality.
- method DiskAnalyzerTab.__init__(self, config, logger, safety_manager) (L70): Initialize the tab and call setup_ui.
- method DiskAnalyzerTab.setup_ui(self) (L76): Set up the user interface.
- method DiskAnalyzerTab.start_disk_analysis(self) (L166): Start disk analysis running safely in a background worker.
- method DiskAnalyzerTab._on_worker_finished(self, worker) (L198): Unregister a finished worker thread and delete it.
- method DiskAnalyzerTab.disk_analysis_complete(self, result: dict) (L205): Handle disk analysis completion.
- method DiskAnalyzerTab.disk_analysis_error(self, error: str) (L246): Reset the analyze button and report the analysis error.
- method DiskAnalyzerTab.quick_disk_analysis(self) (L257): Point the path input at the home folder and start analysis.
- method DiskAnalyzerTab.show_treemap_visualization(self) (L267): Write the analysis as a Plotly treemap HTML file and open it in a browser.
- method DiskAnalyzerTab.show_sunburst_visualization(self) (L281): Write the analysis as a Plotly sunburst HTML file and open it in a browser.
- method DiskAnalyzerTab.show_interactive_dashboard(self) (L295): Export the interactive dashboard HTML to a temp file and open it in a browser.
- method DiskAnalyzerTab.export_visualization_dialog(self) (L310): Choose a save path and export the dashboard as HTML/PNG/SVG.

## src/cortex_unified/ui/tabs/docker_tab.py — Tab for docker tab in Cortex Cleaner GUI.
- class DockerCleaner (L27): DockerCleaner fallback class.
- func is_docker_available(self) (L29): Check if Docker is available.
- class DockerScanWorker(QThread) (L33): Scans unused Docker images/containers/volumes/networks off the GUI thread.
- method DockerScanWorker.__init__(self, scan_images: bool, scan_containers: bool, scan_volumes: bool, scan_networks: bool) (L38): Store the four resource-type scan flags.
- method DockerScanWorker.run(self) (L47): Run Docker resource scanning.
- class DockerCleanupWorker(QThread) (L73): Cleans selected Docker resources (optionally dry-run) off the GUI thread.
- method DockerCleanupWorker.__init__(self, resources: list, dry_run: bool) (L78): Store the resources to clean and the dry-run flag.
- method DockerCleanupWorker.run(self) (L85): Run Docker resource cleanup.
- class DockerTab(BaseTab) (L98): Tab for docker tab functionality.
- method DockerTab.__init__(self, config, logger, safety_manager) (L101): Initialize the tab and call setup_ui.
- method DockerTab.setup_ui(self) (L106): Set up the user interface.
- method DockerTab.check_docker_availability(self) (L168): Check if Docker is available.
- method DockerTab.start_docker_scan(self) (L185): Start Docker resource scan dynamically linked to worker threads.
- method DockerTab._on_worker_finished(self, worker) (L209): Unregister a finished worker thread and delete it.
- method DockerTab.docker_scan_finished(self, result: dict) (L215): Handle Docker scan completion.
- method DockerTab.docker_scan_error(self, error: str) (L255): Reset the scan controls and report the Docker scan error.
- method DockerTab.start_docker_cleanup(self) (L265): Start Docker resource cleanup.
- method DockerTab.docker_cleanup_finished(self, result) (L301): Handle Docker cleanup completion.
- method DockerTab.docker_cleanup_error(self, error: str) (L328): Reset the cleanup controls and report the Docker cleanup error.

## src/cortex_unified/ui/tabs/duplicates_tab.py — Tab for duplicates tab in Cortex Cleaner GUI.
- class DuplicateFinderWorker(QThread) (L27): Runs duplicate-file detection (size grouping + hashing) off the GUI thread.
- method DuplicateFinderWorker.__init__(self, config: Config, path: str, hash_algorithm: str='md5') (L34): Store config, path, hash algorithm, and the poller run flag.
- method DuplicateFinderWorker.run(self) (L44): Find duplicates and emit finished_scan with {duplicates, stats} (or error_occurred).
- func DuplicateFinderWorker.run.poll_progress() (L52): Emit file-count status every 0.1s while the scan runs.
- class DuplicatesTab(BaseTab) (L83): Tab for finding and deleting duplicate files.
- method DuplicatesTab.__init__(self, config, logger, safety_manager) (L85): Initialize the tab and empty the current duplicates cache.
- method DuplicatesTab.setup_ui(self) (L92): Build the tab: path picker, hash/strategy options, and group/details splitter.
- method DuplicatesTab.start_find_duplicates(self) (L181): Validate the path and launch the DuplicateFinderWorker.
- method DuplicatesTab.duplicates_found(self, result) (L207): Populate the groups tree, pre-checking files per the chosen strategy.
- method DuplicatesTab.select_all_duplicates(self) (L261): Check every file row across all duplicate groups.
- method DuplicatesTab.deselect_all_duplicates(self) (L267): Uncheck every file row across all duplicate groups.
- method DuplicatesTab._set_tree_states(self, state) (L273): Apply a check state to every child row in the groups tree.
- method DuplicatesTab.duplicates_error(self, error) (L285): Log and report the duplicate-scan error.
- method DuplicatesTab.delete_selected_duplicates(self) (L293): Confirm, then recycle the checked duplicates via Deleter and rescan.
- method DuplicatesTab.progress_bar_start_delete(self) (L341): Show Deleting status and the indeterminate progress bar.
- method DuplicatesTab.operation_finished(self, worker) (L349): Hide progress, re-enable the find button, and reap the worker.

## src/cortex_unified/ui/tabs/empty_files_tab.py — Empty files cleaner tab for Cortex Cleaner GUI.
- class EmptyFilesWorker(QThread) (L24): Worker thread for empty files operations.
- method EmptyFilesWorker.__init__(self, config, path, operation='scan', files_to_delete=None, dirs_to_delete=None) (L33): Store config, path, operation type, and the delete file/dir lists.
- method EmptyFilesWorker.run(self) (L44): Scan for or delete empty items (emits scan_completed/delete_completed, or error_occurred).
- func poll_progress() (L56): Relay scanner percentage and current path every 0.1s until the scan ends.
- class EmptyFilesTab(BaseTab) (L94): Tab for empty files cleaning functionality.
- method EmptyFilesTab.__init__(self, config, logger, safety_manager) (L97): Initialize the tab and clear the empty file/dir caches.
- method EmptyFilesTab.setup_ui(self) (L105): Set up the user interface.
- method EmptyFilesTab.setup_tooltips(self) (L214): Set up tooltips.
- method EmptyFilesTab.browse_path(self) (L229): Browse for directory to scan.
- method EmptyFilesTab.start_scan(self) (L236): Validate the path and launch the scan worker.
- method EmptyFilesTab.start_delete(self) (L266): Start deleting selected items.
- method EmptyFilesTab.scan_completed(self, empty_files, empty_dirs, stats) (L316): Handle scan completion.
- method EmptyFilesTab.select_all_items(self) (L355): Check every row checkbox in the results table.
- method EmptyFilesTab.deselect_all_items(self) (L364): Uncheck every row checkbox in the results table.
- method EmptyFilesTab.delete_completed(self, result) (L373): Handle deletion completion.
- method EmptyFilesTab.handle_error(self, error_message) (L388): Show the error in a dialog and the status label.
- method EmptyFilesTab.operation_finished(self, worker) (L396): Handle operation completion.

## src/cortex_unified/ui/tabs/file_shredder_tab.py — Tab for file shredder tab in Cortex Cleaner GUI.
- class FileShredderWorker(QThread) (L26): Runs DoD 5220.22-M multi-pass overwrite shredding in background.
- method FileShredderWorker.__init__(self, config: Config, target_paths: List[str], passes: int, method: str, wipe_drive: Optional[str]=None) (L32): Store config, target paths, passes/method, and optional wipe drive.
- method FileShredderWorker.run(self) (L44): Shred each path (file or directory) and optionally wipe free space, emitting progress and finished/error.
- class FileShredderTab(BaseTab) (L95): Tab for file shredder tab functionality.
- method FileShredderTab.__init__(self, config, logger, safety_manager) (L98): Initialize the tab and its empty shred-set.
- method FileShredderTab.setup_ui(self) (L105): Create the file shredder tab.
- method FileShredderTab._sync_list(self) (L201): Rebuild the list widget from the shred set and toggle the start button.
- method FileShredderTab.add_files_to_shred(self) (L210): Add chosen files to the shred set and refresh the list.
- method FileShredderTab.add_folder_to_shred(self) (L220): Add a chosen folder to the shred set and refresh the list.
- method FileShredderTab.remove_files_from_shred(self) (L229): Discard the selected entries from the shred set.
- method FileShredderTab.clear_shred_list(self) (L238): Empty the shred set and refresh the list.
- method FileShredderTab._resolve_passes(self) (L245): Entitlement-checked pass count; never exceeds the licensed cap.
- method FileShredderTab._derive_drive_letter(paths) (L255): Single drive letter shared by all target paths, else None.
- method FileShredderTab.start_file_shredding(self) (L263): Confirm destructiveness, resolve passes/wipe drive, and launch the worker.
- method FileShredderTab._on_shred_progress(self, msg, pct) (L321): Show the current shredding message and percentage.
- method FileShredderTab._on_worker_finished(self, worker) (L328): Unregister a finished worker thread and delete it.
- method FileShredderTab._on_shred_complete(self, results) (L335): Report shredded/failed paths and the free-space wipe result, then clear the list.
- method FileShredderTab._on_shred_error(self, error) (L364): Re-enable shredding and report the fatal error.

## src/cortex_unified/ui/tabs/heuristics_tab.py — Tab for heuristics tab in Cortex Cleaner GUI.
- class HeuristicsTab(BaseTab) (L25): Tab for heuristics tab functionality.
- method HeuristicsTab.__init__(self, config, logger, safety_manager) (L28): Initialize the tab and build its detection options, scan path, and leftovers table.

## src/cortex_unified/ui/tabs/large_files_tab.py — Tab for large files tab in Cortex Cleaner GUI.
- class LargeFileFinderWorker(QThread) (L26): Finds large files above a size threshold off the GUI thread.
- method LargeFileFinderWorker.__init__(self, config: Config, path: str, min_size_mb: int=100) (L31): Store the config, scan path, and minimum size in MB.
- method LargeFileFinderWorker.run(self) (L40): Run the large file finding process.
- class LargeFilesTab(BaseTab) (L52): Tab for large files tab functionality.
- method LargeFilesTab.__init__(self, config, logger, safety_manager) (L55): Initialize the tab and call setup_ui.
- method LargeFilesTab.setup_ui(self) (L61): Set up the user interface.
- method LargeFilesTab._on_selection_changed(self) (L137): Enable the delete button when table rows are selected.
- method LargeFilesTab.select_all(self) (L144): Select all rows in the large-files table.
- method LargeFilesTab.deselect_all(self) (L150): Clear the table's selection.
- method LargeFilesTab.start_find_large_files(self) (L156): Start finding large files natively via Thread manager.
- method LargeFilesTab._on_worker_finished(self, worker) (L193): Unregister a finished worker thread and delete it.
- method LargeFilesTab.large_files_found(self, result: list) (L200): Fill the table with path/size/modified-time rows and enable actions.
- method LargeFilesTab.large_files_error(self, error: str) (L228): Reset the find button and report the error.
- method LargeFilesTab.delete_selected_large_files(self) (L237): Confirm, then trash the selected large files via Deleter and rescan.

## src/cortex_unified/ui/tabs/package_manager_tab.py — Tab for package manager tab in Cortex Cleaner GUI.
- class PackageManagerCleaner (L26): PackageManagerCleaner fallback class.
- func __init__(self, *args, **kwargs) (L28): Accept any arguments; fallback stub does nothing.
- func detect_package_managers(self) (L31): Report no package managers (fallback stub).
- func scan_caches(self) (L34): Report no caches found (fallback stub).
- func cleanup_caches(self) (L37): Report no cleanup results (fallback stub).
- class PMSearchWorker(QThread) (L41): Detects installed package managers off the GUI thread.
- method PMSearchWorker.__init__(self, config: Config) (L46): Store the config used to build the cleaner.
- method PMSearchWorker.run(self) (L52): Detect package managers (emits finished with them, or error).
- class PMScanWorker(QThread) (L63): Scans package-manager/project caches off the GUI thread.
- method PMScanWorker.__init__(self, config: Config, managers: dict, target_folders: List[str], keep_recent: int, orphaned: bool, include_python: bool) (L68): Store config, manager flags, target folders, retention, and scope flags.
- method PMScanWorker.run(self) (L80): Scan system or project caches (emits finished with {resources, stats}, or error).
- class PMCleanWorker(QThread) (L106): Cleans scanned cache resources (optionally dry-run) off the GUI thread.
- method PMCleanWorker.__init__(self, config: Config, resources: list, dry_run: bool) (L111): Store the config, resources to clean, and dry-run flag.
- method PMCleanWorker.run(self) (L119): Clean the caches (emits finished with a results dict, or error).
- class PackageManagerTab(BaseTab) (L130): Tab for package manager tab functionality.
- method PackageManagerTab.__init__(self, config, logger, safety_manager) (L133): Initialize the tab and call setup_ui.
- method PackageManagerTab.setup_ui(self) (L138): Create the Package Manager tab with tabs for different scan modes.
- method PackageManagerTab.detect_package_managers(self) (L327): Launch the detection worker and show busy state.
- method PackageManagerTab._on_detect_finished(self, managers) (L343): List detected manager names, or report none found.
- method PackageManagerTab._on_detect_error(self, err) (L363): Reset the detect button and warn about the failure.
- method PackageManagerTab.add_folder_to_scan(self) (L370): Append a chosen folder to the scan list if not already present.
- method PackageManagerTab.remove_selected_folder(self) (L381): Remove the selected folder from the scan list.
- method PackageManagerTab.clear_all_folders(self) (L388): Clear all folders from the scan list.
- method PackageManagerTab.start_pm_scan(self) (L400): Collect mode/manager options and launch the cache scan worker.
- method PackageManagerTab._on_scan_finished(self, data) (L441): Fill the results table and enable cleanup when caches were found.
- method PackageManagerTab._on_scan_error(self, err) (L478): Reset the scan button and warn about the scan failure.
- method PackageManagerTab.start_pm_cleanup(self) (L485): Confirm, then launch the cleanup worker (dry-run aware).
- method PackageManagerTab._on_clean_finished(self, data) (L519): Report freed space and errors; clear results unless dry run.
- method PackageManagerTab._on_clean_error(self, err) (L545): Reset the buttons and warn about the cleanup failure.
- method PackageManagerTab._on_worker_finished(self, worker) (L553): Unregister a finished worker thread and delete it.

## src/cortex_unified/ui/tabs/privacy_tab.py — Privacy Shield tab — comprehensive browser and system privacy management.
- class BrowserScanWorker(QObject) (L27): Scan browsers + system traces in a background thread.
- method BrowserScanWorker.run(self) (L31): Scan browsers and system traces via PrivacyCleaner.
- class PrivacyTab(BaseTab) (L47): Privacy Shield — telemetry blocking and browser data management.
- method PrivacyTab.__init__(self, config, logger, safety_manager, parent=None) (L50): Create the PrivacyCleaner/TelemetryBlocker backends and scan state.
- method PrivacyTab.setup_ui(self) (L59): Build the Privacy Shield layout.
- method PrivacyTab.setup_tooltips(self) (L140): Set tooltips for the telemetry block/restore buttons.
- method PrivacyTab._refresh_telemetry(self) (L147): Reload the per-rule telemetry tree from TelemetryBlocker status.
- method PrivacyTab._apply_block(self) (L181): Confirm, then apply all telemetry blocks via TelemetryBlocker.
- method PrivacyTab._restore_telemetry(self) (L206): Confirm, then restore default telemetry settings via TelemetryBlocker.
- method PrivacyTab._scan_browsers(self) (L227): Run BrowserScanWorker on a background thread.
- method PrivacyTab._on_scan_done(self, browser_results: dict, system_traces: dict) (L250): Build the checkable results tree from the scan.
- method PrivacyTab._clean_browsers(self) (L317): Delete the checked browser categories and system traces.

## src/cortex_unified/ui/tabs/process_analyzer_tab.py — Tab for process analyzer tab in Cortex Cleaner GUI.
- class ProcessAnalyzerWorker(QThread) (L14): Worker that lists processes and services off the UI thread.
- method ProcessAnalyzerWorker.__init__(self, config) (L23): Create the ProcessAnalyzer backend used for listing.
- method ProcessAnalyzerWorker.run(self) (L28): List processes and services, emitting both lists or an error.
- class ProcessAnalyzerTab(BaseTab) (L38): Tab for process analyzer tab functionality.
- method ProcessAnalyzerTab.__init__(self, config, logger, safety_manager) (L41): Initialize with a null worker reference.
- method ProcessAnalyzerTab.setup_ui(self) (L46): Create the process analyzer tab.
- method ProcessAnalyzerTab.refresh_processes(self) (L98): Reload processes and services on a background ProcessAnalyzerWorker.
- method ProcessAnalyzerTab._on_scan_finished(self, processes: List[Dict], services: List[Dict]) (L117): Populate both tables with the scanned processes and services.
- method ProcessAnalyzerTab._on_scan_error(self, err_msg) (L142): Log and recover the UI when the process analysis fails.

## src/cortex_unified/ui/tabs/registry_cleaner_tab.py — Tab for registry cleaner tab in Cortex Cleaner GUI.
- class RegistryScanWorker(QThread) (L15): Worker that scans for orphaned registry entries off the UI thread.
- method RegistryScanWorker.__init__(self, config) (L24): Create the RegistryCleaner backend used for scanning.
- method RegistryScanWorker.run(self) (L29): Scan for orphaned entries, emitting the item list or an error.
- class RegistryCleanWorker(QThread) (L37): Worker that removes orphaned registry entries after a backup.
- method RegistryCleanWorker.__init__(self, config, paths_to_remove: List[str]) (L46): Create the cleaner and store the registry paths to remove.
- method RegistryCleanWorker.run(self) (L52): Back up the registry, then remove each listed orphaned entry.
- class RegistryCleanerTab(BaseTab) (L70): Tab for registry cleaner tab functionality.
- method RegistryCleanerTab.__init__(self, config, logger, safety_manager) (L73): Create the RegistryCleaner backend and a null worker reference.
- method RegistryCleanerTab.setup_ui(self) (L79): Create the registry cleaner tab.
- method RegistryCleanerTab.scan_registry(self) (L130): Run a RegistryScanWorker to find orphaned entries.
- method RegistryCleanerTab._on_scan_finished(self, items: List[Dict]) (L150): Fill the table with scanned orphaned entries.
- method RegistryCleanerTab._on_error(self, err_msg) (L168): Re-enable buttons and show a critical dialog for registry errors.
- method RegistryCleanerTab.clean_registry(self) (L180): Remove all scanned orphaned entries via RegistryCleanWorker.
- method RegistryCleanerTab._on_clean_finished(self, count) (L207): Report the number of cleaned entries, clear the table, and disable Clean.

## src/cortex_unified/ui/tabs/reports_tab.py — Tab for reports tab in Cortex Cleaner GUI.
- class ReportsTab(BaseTab) (L29): Tab for reports functionality.
- method ReportsTab.__init__(self, config, logger, safety_manager) (L32): Create the ReportsGenerator backend used for report output.
- method ReportsTab.setup_ui(self) (L37): Create the reports tab.
- method ReportsTab._zoom_in(self) (L203): Increase the embedded web view's zoom factor by 0.15.
- method ReportsTab._zoom_out(self) (L208): Decrease the web view's zoom factor by 0.15 (floor of 0.2).
- method ReportsTab._zoom_reset(self) (L213): Restore the web view's zoom factor to 1.0.
- method ReportsTab.format_bytes(self, size) (L218): Format a byte count as a human-readable string (B up to PB).
- method ReportsTab._on_table_selection(self) (L226): Enable/disable preview based on selection.
- method ReportsTab.get_live_analytics_data(self) (L231): Collect live dynamic system analytics and telemetry for report generation.
- method ReportsTab.get_dummy_data(self) (L290): Backward-compatible alias for get_live_analytics_data.
- method ReportsTab.generate_report(self) (L294): Generate dynamic analytical report from live system telemetry.
- method ReportsTab.preview_report(self) (L330): Open the highlighted report file manually.
- method ReportsTab.schedule_report(self) (L366): Register a recurring HTML report job with the OS scheduler (Pro).
- method ReportsTab.refresh_reports_list(self) (L419): Update reports from directory polling.
- method ReportsTab.save_report_template(self) (L447): Save current reporting settings to a reusable JSON template.
- method ReportsTab.load_report_template(self) (L478): Load and apply saved report template settings.

## src/cortex_unified/ui/tabs/resource_monitor_tab.py — Tab for resource monitor tab in Cortex Cleaner GUI.
- class ResourceMonitorTab(BaseTab) (L22): Tab for resource monitor tab functionality.
- method ResourceMonitorTab.__init__(self, config, logger, safety_manager) (L25): Initialize with a null ResourceMonitor before UI setup.
- method ResourceMonitorTab.setup_ui(self) (L30): Create the resource monitor tab.
- method ResourceMonitorTab.start_resource_monitoring(self) (L142): Start real-time resource monitoring.
- method ResourceMonitorTab.stop_resource_monitoring(self) (L158): Stop real-time resource monitoring.
- method ResourceMonitorTab.update_resource_metrics(self) (L170): Poll the backend's latest metrics and refresh every display.
- method ResourceMonitorTab.check_performance_alerts(self, cpu_percent, memory_percent) (L228): Append timestamped alerts when CPU or memory exceed their thresholds.
- method ResourceMonitorTab._show_process_context_menu(self, position) (L242): Show context menu to kill a selected process.
- method ResourceMonitorTab._kill_process(self, pid: int, name: str) (L271): Force-kill the process via psutil, reporting access/not-found errors.

## src/cortex_unified/ui/tabs/restore_tab.py — Tab for restore tab in Cortex Cleaner GUI.
- class RestoreWorker(QThread) (L25): Worker that restores a backup manifest off the UI thread.
- method RestoreWorker.__init__(self, manager: RestoreManager, target_path: str) (L35): Store the RestoreManager and the manifest path to restore from.
- method RestoreWorker.run(self) (L41): Restore files from the manifest, emitting results or errors.
- class RestoreTab(BaseTab) (L50): Tab for restore functionality and recovery.
- method RestoreTab.__init__(self, config, logger, safety_manager) (L53): Create the RestoreManager backend used for manifest operations.
- method RestoreTab.setup_ui(self) (L58): Create the restore tab.
- method RestoreTab._on_table_selection(self) (L122): Enable the Restore and Delete buttons when a snapshot is selected.
- method RestoreTab.refresh_manifests(self) (L128): Update items in the lists dynamically using the backend.
- method RestoreTab.start_restore(self) (L171): Pass the targeted manifest to the restore procedure logic!
- method RestoreTab._on_restore_completed(self, results) (L208): Report the restore outcome (restored count, warnings) and refresh.
- method RestoreTab._on_restore_error(self, err_string) (L221): Log and show a fatal error dialog when the restore worker crashes.
- method RestoreTab._on_worker_finished(self, worker) (L226): Hide the busy bar, re-enable refresh, and dispose the worker.
- method RestoreTab.delete_snapshot(self) (L233): Permanently delete the selected backup after confirmation.

## src/cortex_unified/ui/tabs/scheduler_tab.py — Tab for scheduler tab in Cortex Cleaner GUI.
- class AddTaskDialog(QDialog) (L26): Dialog collecting a task name, frequency (daily/weekly/monthly/once), and time.
- method AddTaskDialog.__init__(self, parent=None) (L28): Build the schedule form with name, frequency combo, time edit, and Ok/Cancel.
- class SchedulerTab(BaseTab) (L57): Tab for scheduler tab functionality.
- method SchedulerTab.__init__(self, config, logger, safety_manager) (L60): Create the TaskScheduler and AutoCleanRules backends.
- method SchedulerTab.setup_ui(self) (L66): Create the task scheduler tab.
- method SchedulerTab.create_tasks_subtab(self) (L87): Build the Scheduled Tasks sub-tab.
- method SchedulerTab._refresh_tasks(self) (L126): Reload the task table from TaskScheduler.list_scheduled_tasks.
- method SchedulerTab._add_task(self) (L147): Register a new scheduled cleanup task from the AddTaskDialog.
- method SchedulerTab._remove_task(self) (L183): Delete the selected scheduled task after confirmation.
- method SchedulerTab.create_auto_clean_rules_subtab(self) (L204): Build the Auto-Clean Rules sub-tab.
- method SchedulerTab._apply_rules(self) (L246): Apply the auto-clean rules and start the monitoring daemon.

## src/cortex_unified/ui/tabs/security_scanner_tab.py — Tab for Sentinel Pro security scanner in Cortex Cleaner GUI.
- class SentinelScanWorker(QThread) (L20): Background worker for Sentinel Pro security scanning.
- method SentinelScanWorker.__init__(self, directory: str, scan_archives: bool=False, scan_git: bool=False, max_workers: int=8) (L26): Store the scan target, archive/git options, and thread budget.
- method SentinelScanWorker.run(self) (L35): Run the secrets scan via system_tools.secrets_scanner.
- class SecurityScannerTab(BaseTab) (L78): Tab for Sentinel Pro security & secrets scanner.
- method SecurityScannerTab.__init__(self, config, logger, safety_manager) (L81): Initialize with a null scan-stats holder before UI setup.
- method SecurityScannerTab.setup_ui(self) (L86): Set up the security scanner UI.
- method SecurityScannerTab._browse_path(self) (L190): Choose a scan directory and put it in the path input.
- method SecurityScannerTab.start_scan(self) (L196): Validate the path and run SentinelScanWorker on a background thread.
- method SecurityScannerTab._cleanup_worker(self, worker) (L230): Untrack and schedule deletion of the finished scan worker.
- method SecurityScannerTab._scan_complete(self, stats) (L235): Render the finished ScanStats.
- method SecurityScannerTab._scan_error(self, error_msg) (L289): Re-enable the scan button and show the scan failure dialog.
- method SecurityScannerTab._on_finding_selected(self, row, col, prev_row, prev_col) (L296): Show the selected finding's full details in the detail pane.
- method SecurityScannerTab.export_report(self) (L322): Export the last scan's stats to a JSON file via a save dialog.

## src/cortex_unified/ui/tabs/settings_tab.py — Tab for settings tab in Cortex Cleaner GUI.
- class SettingsTab(BaseTab) (L32): Tab for settings tab functionality.
- method SettingsTab.__init__(self, config, logger, safety_manager) (L35): Initialize the settings tab via the base class.
- method SettingsTab.setup_ui(self) (L39): Create the settings tab natively hooking I18n modules.
- method SettingsTab.save_settings(self) (L105): Invoke global configuration application parameters.

## src/cortex_unified/ui/tabs/startup_manager_tab.py — Tab for startup manager tab in Cortex Cleaner GUI.
- class StartupScanWorker(QThread) (L14): Worker that enumerates startup items off the UI thread.
- method StartupScanWorker.__init__(self, config) (L23): Create the StartupManager backend used for listing items.
- method StartupScanWorker.run(self) (L28): List startup items via StartupManager, emitting results or errors.
- class StartupManagerTab(BaseTab) (L36): Tab for startup manager tab functionality.
- method StartupManagerTab.__init__(self, config, logger, safety_manager) (L39): Create the StartupManager backend and a null worker reference.
- method StartupManagerTab.setup_ui(self) (L45): Create the startup manager tab.
- method StartupManagerTab._on_selection(self) (L84): Enable the Disable button only when a table row is selected.
- method StartupManagerTab.refresh_startup_items(self) (L88): Reload startup items on a background StartupScanWorker.
- method StartupManagerTab._on_scan_finished(self, items: List[Dict]) (L107): Fill the table with the scanned startup items.
- method StartupManagerTab._on_scan_error(self, err_msg) (L123): Log and show a critical dialog when the startup scan fails.
- method StartupManagerTab.disable_selected_startup_items(self) (L130): Disable the selected startup item after confirmation.

## src/cortex_unified/ui/tabs/system_tools_tab.py — Tab for system tools tab in Cortex Cleaner GUI.
- class SystemToolsTab(BaseTab) (L18): Container Tab mapping System Tools sub-tabs dynamically.
- method SystemToolsTab.__init__(self, config, logger, safety_manager) (L21): Initialize the container tab via the base class.
- method SystemToolsTab.setup_ui(self) (L25): Create the system tools tab natively injecting components.

## src/cortex_unified/ui/tabs/uninstaller_tab.py — Deep Uninstaller tab — safe app removal + residual cleanup.
- class AppListWorker(QObject) (L33): Worker that enumerates installed applications off the UI thread.
- method AppListWorker.run(self) (L39): Query AppUninstaller for installed apps and emit them as a list.
- class ResidualScanWorker(QObject) (L44): Confidence-scored leftover sweep for one app (read-only).
- method ResidualScanWorker.__init__(self, app_name: str, publisher: str, install_location: str='') (L50): Store the app identity used to build the InstalledApp scan target.
- method ResidualScanWorker.run(self) (L57): Scan for the app's leftovers via LeftoverScanner.
- class ResidualCleanWorker(QObject) (L74): Recycle reviewed findings; registry keys are backed up first.
- method ResidualCleanWorker.__init__(self, findings: list[dict], create_restore_point: bool=False) (L80): Store the selected finding dicts and restore-point preference.
- method ResidualCleanWorker.run(self) (L86): Clean the selected leftovers via LeftoverCleaner.
- class UninstallerTab(BaseTab) (L112): Deep Uninstaller with residual hunting.
- method UninstallerTab.__init__(self, config, logger, safety_manager, parent=None) (L115): Create the AppUninstaller backend and thread/worker refs before UI setup.
- method UninstallerTab.setup_ui(self) (L125): Build the uninstaller layout.
- method UninstallerTab.setup_tooltips(self) (L250): Set tooltips for the uninstall and leftover-scan buttons.
- method UninstallerTab._load_apps(self) (L257): Load installed apps on a background thread via AppListWorker.
- method UninstallerTab._on_apps_loaded(self, apps) (L281): Cache the full app list, repopulate the table, and reset the controls.
- method UninstallerTab._populate_table(self, apps) (L289): Fill the app table rows, storing the full app dict on each name item.
- method UninstallerTab._filter_apps(self, text) (L319): Repopulate the table with apps matching the text in name or publisher.
- method UninstallerTab._on_app_selected(self) (L331): Show the selected app's details and reset the residual panel.
- method UninstallerTab._run_uninstall(self) (L357): Confirm, then launch the selected app's official uninstaller.
- method UninstallerTab._scan_residuals(self) (L391): Run ResidualScanWorker on a background thread for the selected app.
- method UninstallerTab._on_residuals_failed(self, message: str) (L422): Re-enable the scan button and warn about the failed scan.
- method UninstallerTab._confidence_label(level: str) (L429): Map a scanner confidence level to a human-friendly label.
- method UninstallerTab._on_residuals_done(self, leftovers) (L435): Populate the residual table from scan results.
- method UninstallerTab._clean_residuals(self) (L471): Clean the selected leftovers on a background ResidualCleanWorker.
- method UninstallerTab._on_clean_failed(self, message: str) (L517): Re-enable the clean button and warn about the failed cleanup.
- method UninstallerTab._on_clean_done(self, outcomes) (L523): Summarize cleanup outcomes and keep failed items for review.

## src/cortex_unified/ui/tooltips.py — Comprehensive tooltip and help system for Cortex Cleaner GUI.
- class TooltipManager (L8): Manages tooltips and help text for GUI components.
- method TooltipManager.apply_tooltip(cls, widget: QWidget, tooltip_key: str, include_help: bool=False) (L373): Apply tooltip to a widget.
- method TooltipManager.apply_tooltips_to_window(cls, window) (L397): Apply tooltips to all widgets in a window.
- method TooltipManager.get_keyboard_shortcuts_text(cls) (L410): Get formatted keyboard shortcuts help text.
- method TooltipManager.show_help_dialog(cls, parent=None) (L423): Show comprehensive help dialog.
- func setup_tooltips_and_help(main_window) (L498): Set up comprehensive tooltips and help system for the main window.
- func add_contextual_help(widget: QWidget, help_text: str) (L520): Add contextual help to a widget.
- func create_help_button(parent, help_text: str) (L532): Create a help button that shows contextual help.
- func create_help_button.show_help() (L548): show_help.

## src/cortex_unified/ui/tray_icon.py — System Tray Manager — manages the tray icon, background agent, and notifications.
- class SystemTrayManager(QObject) (L11): Manages the system tray icon, context menu, and background monitoring alerts.
- method SystemTrayManager.__init__(self, main_window, app) (L14): __init__.
- method SystemTrayManager._setup_menu(self) (L50): _setup_menu.
- method SystemTrayManager._on_tray_activated(self, reason) (L77): _on_tray_activated.
- method SystemTrayManager._show_main_window(self) (L84): _show_main_window.
- method SystemTrayManager._run_instant_scan(self) (L92): _run_instant_scan.
- method SystemTrayManager._quit_app(self) (L104): _quit_app.
- method SystemTrayManager._on_high_ram(self, value) (L116): _on_high_ram.
- method SystemTrayManager._on_high_cpu(self, value) (L127): _on_high_cpu.
- method SystemTrayManager._on_low_disk(self, free_gb) (L138): _on_low_disk.

## src/cortex_unified/visualization/__init__.py — Visualization module for Cortex Cleaner.
- (no classes/functions — constants/imports only)

## src/cortex_unified/visualization/interactive_dashboard.py — Interactive dashboard for comprehensive data visualization.
- class go (L20): go.
- class Figure (L22): Figure.
- func __init__(self, *args, **kwargs) (L24): __init__.
- func add_trace(self, *args, **kwargs) (L29): add_trace.
- func update_layout(self, *args, **kwargs) (L34): update_layout.
- class px (L41): px.
- func bar(*args, **kwargs) (L44): bar.
- func pie(*args, **kwargs) (L50): pie.
- func make_subplots(*args, **kwargs) (L56): make_subplots.
- func plot(*args, **kwargs) (L61): plot.
- class InteractiveDashboard (L70): Composes analyzer output into interactive Plotly dashboards.
- method InteractiveDashboard.__init__(self, analyzer: Any=None) (L78): Store the analyzer; generators defer until first render.
- method InteractiveDashboard._initialize_generators(self) (L90): (Re)build tree generators from the current analyzer.
- method InteractiveDashboard.create_dashboard(self, layout_type: str='combined') (L96): Render the requested layout.
- method InteractiveDashboard._create_empty_dashboard(self) (L120): Empty state figure prompting the user to run an analysis.
- method InteractiveDashboard._create_treemap_dashboard(self) (L138): Full-height treemap alone.
- method InteractiveDashboard._create_sunburst_dashboard(self) (L150): Full-height sunburst alone.
- method InteractiveDashboard._create_side_by_side_dashboard(self) (L162): Treemap and sunburst sharing one row.
- method InteractiveDashboard._create_combined_dashboard(self) (L192): Pie + bar overview on row 1, full-width treemap on row 2.
- method InteractiveDashboard._add_disk_usage_pie(self, fig: go.Figure, row: int, col: int) (L229): Pie of used vs free bytes; silently skipped when data absent.
- method InteractiveDashboard._add_file_type_bar(self, fig: go.Figure, row: int, col: int) (L252): Bar chart of the ten largest extensions by total bytes.
- method InteractiveDashboard.handle_drill_down(self, path: str) (L279): Re-root the analysis at ``path`` and rebuild the dashboard.
- method InteractiveDashboard.handle_drill_up(self) (L308): Pop the last drilled path; walk to the filesystem parent if empty.
- method InteractiveDashboard.handle_context_menu(self, path: str) (L321): Action descriptors offered for a right-clicked path.
- method InteractiveDashboard.export_visualization(self, format: str, filepath: str, visualization_type: str='dashboard') (L348): Export a figure to image or HTML.
- method InteractiveDashboard.export_batch(self, base_path: str, formats: List[str]) (L405): Export the dashboard once per format; per-format success map.
- method InteractiveDashboard.refresh_data(self) (L420): Re-run all analyses and rebuild; empty figure without analyzer.
- method InteractiveDashboard.get_dashboard_stats(self) (L433): Snapshot of current path, drill depth, size, and counts.

## src/cortex_unified/visualization/sunburst_generator.py — Plotly sunburst renderer for hierarchical disk usage trees.
- class go (L20): go.
- class Figure (L22): Figure.
- func __init__(self, *args, **kwargs) (L24): __init__.
- func add_trace(self, *args, **kwargs) (L29): add_trace.
- func update_layout(self, *args, **kwargs) (L34): update_layout.
- class px (L41): px.
- func sunburst(*args, **kwargs) (L44): sunburst.
- func plot(*args, **kwargs) (L50): plot.
- class SunburstSegment (L58): One ring slice: hierarchy identity plus precomputed polar extents.
- class SunburstGenerator (L71): Builds sunburst figures colored by file type, shaded by size share.
- method SunburstGenerator.__init__(self, data: Any=None) (L74): Store data; ``segments`` stays empty on the Plotly path.
- method SunburstGenerator._setup_color_scheme(self) (L80): Palette per hierarchy depth plus per-extension overrides.
- method SunburstGenerator._get_file_type_from_path(self, path: str) (L111): Extension tag for a path; 'directory'/'unknown' sentinels.
- method SunburstGenerator._get_color_for_level_and_type(self, level: int, file_type: str, size_ratio: float=0.5) (L118): Base hue by extension (else depth ring), darkened for larger
- method SunburstGenerator._convert_directory_tree_to_sunburst_data(self, tree_data: Dict, max_depth: int=4) (L135): Flatten a tree into parallel id/label/parent/value arrays.
- func SunburstGenerator._convert_directory_tree_to_sunburst_data.add_node(node_data: Dict, parent_id: str='', level: int=0) (L160): add_node.
- method SunburstGenerator.generate_sunburst(self, max_depth: int=4) (L218): Render the sunburst figure, or a "No Data" empty state.
- method SunburstGenerator.export_as_image(self, format: str='svg', width: int=800, height: int=800) (L288): Rasterize via the kaleido engine.
- method SunburstGenerator.export_as_html(self, interactive: bool=True, include_plotlyjs: str='cdn') (L316): Serialize to a standalone HTML <div>.
- method SunburstGenerator._format_bytes(self, bytes_count: int) (L349): Human-readable size using binary (1024-step) units.

## src/cortex_unified/visualization/treemap_generator.py — TreeMap visualization generator for disk usage analysis.
- class go (L16): go.
- class Figure (L18): Figure.
- func __init__(self, *args, **kwargs) (L20): __init__.
- func add_trace(self, *args, **kwargs) (L25): add_trace.
- func update_layout(self, *args, **kwargs) (L30): update_layout.
- class px (L37): px.
- func treemap(*args, **kwargs) (L40): treemap.
- func plot(*args, **kwargs) (L46): plot.
- class TreeMapNode (L55): Tree cell carrying size, depth, and its resolved display color.
- class TreeMapGenerator (L66): Renders disk trees as treemaps; larger nodes darken within their hue.
- method TreeMapGenerator.__init__(self, data: Any=None) (L69): Warn once without Plotly; color scale is sized lazily at flatten.
- method TreeMapGenerator._setup_color_scheme(self) (L79): Per-extension base hues; 'unknown' catches unlisted types.
- method TreeMapGenerator._get_file_type_from_path(self, path: str) (L99): Extension tag for a path; 'directory'/'unknown' sentinels.
- method TreeMapGenerator._get_color_for_item(self, node: TreeMapNode) (L106): Base hue by type, darkened proportionally to size share.
- method TreeMapGenerator._convert_directory_tree_to_nodes(self, tree_data: Dict, max_depth: int=3, current_depth: int=0) (L129): Recursively materialize TreeMapNodes up to max_depth.
- method TreeMapGenerator._flatten_nodes_for_plotly(self, nodes: List[TreeMapNode]) (L176): Depth-first flatten into parallel arrays for go.Treemap.
- func TreeMapGenerator._flatten_nodes_for_plotly.add_node(node: TreeMapNode, parent_id: str='') (L189): add_node.
- func TreeMapGenerator._flatten_nodes_for_plotly.collect_sizes(nodes_list) (L209): collect_sizes.
- method TreeMapGenerator.generate_treemap(self, max_depth: int=3) (L232): Render the treemap figure, or a "No Data" empty state.
- method TreeMapGenerator.export_as_image(self, format: str='png', width: int=1200, height: int=800) (L296): Rasterize via the kaleido engine.
- method TreeMapGenerator.export_as_html(self, interactive: bool=True, include_plotlyjs: str='cdn') (L324): Serialize to a standalone HTML <div>.
- method TreeMapGenerator._format_bytes(self, bytes_count: int) (L357): Human-readable size using binary (1024-step) units.

---
Totals: 316 files, 909 classes, 4554 functions/methods.
