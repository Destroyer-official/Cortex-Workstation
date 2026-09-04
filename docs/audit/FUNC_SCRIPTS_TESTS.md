# Function inventory — scripts / tests / run_gui / NexusExplorer test

_Base: D:/code/Main_projects/Cortex_Cleaner · files: 124 · generated from AST + body reads_

## scripts/audit_all_page_functions.py — Deep Functional & UI Inspection across all 59 Pages.
- audit_all_pages() (L28): Audit all pages: build PremiumMainWindow, via findChildren; loop over enumerate(PAGES, 1)

## scripts/audit_imports.py — Static import health audit for the cortex_unified package.
- module_symbols(path) (L27): Module symbols via parse, read_text, any; loop over tree.body; return result
- get_syms(modname) (L76): Get syms via module_symbols; return result

## scripts/audit_pages.py — Audit script to verify that all registered pages load their factory classes.
- (no function definitions)

## scripts/audit_system_tools.py — Audit script to inspect classes and functions across all system tools.
- (no function definitions)

## scripts/build_exe.py — Compile run_gui.py into a distributable Windows executable via PyInstaller.
- build_app() (L11): Build app via rmtree, run

## scripts/check_all_structure_files.py — Deep, exhaustive, file-by-file verification of every program file in structure.txt.
- find_all_python_files() (L21): Find all actual Python files in the repository.
- verify_file(p: Path) (L30): Deeply verify a single python program file.
- main() (L102): Main via find_all_python_files, perf_counter, write_text; loop over enumerate(py_files, 1); return result

## scripts/check_hardcoded_paths.py — Diagnostic script to check for hardcoded Windows paths.
- analyze_paths() (L7): Analyze paths via compile, endswith, findall; loop over os.walk('src')

## scripts/check_lint_issues.py — Diagnostic script to check for undefined names and lint anomalies.
- check_undefined_names_in_file(filepath) (L8): Check undefined names in file via parse; return result
- Reporter.__init__(self) (L28): Initialize errors
- Reporter.unexpectedError(self, filename, msg) (L31): UnexpectedError via append
- Reporter.syntaxError(self, filename, msg, lineno, offset, text) (L34): SyntaxError via append
- Reporter.flake(self, msg) (L37): Flake via append, str

## scripts/deep_codebase_inspection.py — Deep exhaustive codebase inspector.
- scan_file(filepath: Path) -> dict (L28): Scan file via relative_to, splitlines, read_text; loop over enumerate(lines, 1); return result
- main() (L95): Main: build Path, via scan_file, dump; loop over os.walk(ROOT)

## scripts/deep_inspect_placeholders.py — Deep inspector for placeholders, TODOs, stubs, and mocks across all src/ files.
- (no function definitions)

## scripts/generate_complete_features.py — Generate the master exhaustive COMPLETE_FEATURES_CHECKLIST.md covering every feature and module.
- get_module_info(p: Path) (L9): Get module info via read_text, parse, get_docstring; return result

## scripts/generate_feature_directory.py — Generate docs/FEATURE_DIRECTORY.md listing all 118 UI pages across all groups.
- (no function definitions)

## scripts/generate_program_checklist.py — Generate an exhaustive, program-file-by-program-file verification checklist.
- parse_file(p: Path) (L8): Parse file via read_text, parse, get_docstring; loop over tree.body; return result

## scripts/run_all_tests.py — Runner script to execute all unit tests and collect failure reports.
- FailureCollector.__init__(self) (L11): Initialize failed, passed, skipped
- FailureCollector.pytest_runtest_logreport(self, report) (L17): Pytest runtest logreport via append, str

## scripts/scan_codebase.py — Scanner script to detect placeholders, TODOs, and mock patterns.
- (no function definitions)

## scripts/stress_test_gui_all_actions.py — Deep interactive action stress-test for Cortex Cleaner GUI.
- pump_events(app: QApplication, duration_ms: int=150) -> None (L40): Pump events via monotonic, processEvents
- main() (L48): Main: build Path, via apply_theme, mkdtemp; loop over enumerate(ordered_specs, 1)

## scripts/test_all_pages.py — Diagnostic script to verify offscreen instantiation of all UI pages.
- (no function definitions)

## scripts/test_navigation.py — Diagnostic script to test UI navigation and theme application.
- (no function definitions)

## scripts/update_structure_txt.py — Generate an up-to-date, clean structure.txt of the entire repository.
- build_tree(dir_path: Path, prefix: str='') -> list[str] (L28): Build tree via is_dir, is_file, iterdir; loop over entries; return result
- main() (L58): Main via build_tree

## scripts/verify_modules.py — Quick functional verification of core system modules.
- (no function definitions)

## scripts/verify_production_readiness.py — Comprehensive Production Readiness & Diagnostics Verification Suite.
- (no function definitions)

## run_gui.py — Launch the Cortex Workstation GUI from a source checkout.
- main() -> int (L26): Entry point: run the premium GUI.

## tests/test_advanced_disk_analyzer.py — Tests for cortex_unified.analyzers.advanced_disk_analyzer.
- TestFileEntry.test_default_values(self) (L34): Construct FileEntry; assert path, size, is_dir, extension, attributes
- TestFileEntry.test_cloud_provider_field(self) (L55): Construct FileEntry; assert cloud_provider, etag
- TestFileEntry.test_is_dir_flag(self) (L71): Construct FileEntry; assert is_dir
- TestFolderNode.test_empty_node(self) (L92): Construct FolderNode; assert size, file_count, folder_count, children, extension_stats
- TestFolderNode.test_add_single_file(self) (L101): Construct FolderNode; assert size, file_count, extension_stats, children
- TestFolderNode.test_add_file_in_subdirectory(self) (L110): Construct FolderNode; assert size, file_count, children, folder_count
- TestFolderNode.test_add_multiple_files_accumulates_sizes(self) (L122): Construct FolderNode; assert size, file_count, extension_stats
- TestFolderNode.test_add_file_with_empty_relpath(self) (L133): Construct FolderNode; assert size, file_count
- TestFolderNode.test_add_file_root_only_parts(self) (L140): Construct FolderNode; assert size, file_count
- TestFolderNode.test_top_extensions_sorted_desc(self) (L147): Construct FolderNode; assert len(...)
- TestFolderNode.test_top_extensions_limit(self) (L158): Construct FolderNode; assert len(...)
- TestFolderNodeTreemap.test_single_file_produces_root_entry(self) (L175): Construct FolderNode; assert len(...)
- TestFolderNodeTreemap.test_children_listed_in_parent(self) (L185): Construct FolderNode
- TestFolderNodeTreemap.test_max_depth_truncation(self) (L195): Construct FolderNode; assert max(...)
- TestFolderNodeTreemap.test_file_count_and_folder_count(self) (L203): Construct FolderNode; assert len(...)
- TestFolderNodeSunburst.test_root_has_empty_parent(self) (L222): Construct FolderNode; assert len(...)
- TestFolderNodeSunburst.test_child_references_parent_path(self) (L231): Construct FolderNode; assert len(...)
- TestFolderNodeSunburst.test_max_depth_truncation(self) (L240): Construct FolderNode; assert max(...)
- TestFolderNodeSunburst.test_value_matches_size(self) (L248): Construct FolderNode
- TestFolderNodeBarChart.test_excludes_root_from_bar(self) (L264): Construct FolderNode; assert all(...)
- TestFolderNodeBarChart.test_top_n_limit(self) (L271): Construct FolderNode; assert len(...)
- TestFolderNodeBarChart.test_sorted_largest_first(self) (L280): Construct FolderNode; assert sorted(...)
- TestFolderNodeBarChart.test_bar_chart_with_no_children(self) (L290): Construct FolderNode; assert len(...)
- TestCloudScanner.test_default_providers(self) (L305): Construct CloudScanner; assert providers
- TestCloudScanner.test_custom_providers(self) (L312): Construct CloudScanner; assert providers
- TestCloudScanner.test_scan_local_path_no_colon_skips(self) (L317): Construct CloudScanner
- TestCloudScanner.test_rclone_not_available_yields_nothing(self, monkeypatch) (L324): Construct CloudScanner; assert _rclone_available
- TestAdvancedDiskAnalyzerInit.test_default_init(self) (L342): Construct AdvancedDiskAnalyzer; assert _scanner, _root_node, cancel_event, Event
- TestAdvancedDiskAnalyzerInit.test_custom_cancel_event(self) (L349): Construct AdvancedDiskAnalyzer; assert cancel_event
- TestAdvancedDiskAnalyzerInit.test_progress_callback_stored(self) (L355): Construct MagicMock; assert progress_cb
- TestAdvancedDiskAnalyzerInit.test_include_cloud_false_uses_local_scanner(self) (L361): Construct AdvancedDiskAnalyzer; assert _scanner
- TestAdvancedDiskAnalyzerInit.test_include_cloud_true_without_deps_uses_local(self) (L366): Construct AdvancedDiskAnalyzer; assert _scanner
- TestBuildTree.test_build_tree_from_entries(self) (L384): Construct AdvancedDiskAnalyzer; assert size, file_count, extension_stats
- TestBuildTree.test_build_tree_skips_directories(self) (L398): Construct AdvancedDiskAnalyzer; assert file_count, size
- TestBuildTree.test_build_tree_handles_missing_extension(self) (L409): Construct AdvancedDiskAnalyzer; assert extension_stats
- TestBuildTree.test_build_tree_nested_paths(self) (L418): Construct AdvancedDiskAnalyzer; assert size, children
- TestBuildTree.test_size_accuracy_sum_matches(self) (L432): Construct AdvancedDiskAnalyzer; assert size, file_count
- TestGetVisualizations.test_returns_empty_dict_before_build(self) (L452): Construct AdvancedDiskAnalyzer
- TestGetVisualizations.test_returns_all_keys_after_build(self) (L458): Construct AdvancedDiskAnalyzer
- TestGetVisualizations.test_total_size_matches_tree(self) (L474): Construct AdvancedDiskAnalyzer
- TestGetVisualizations.test_extension_breakdown_is_dict(self) (L485): Construct AdvancedDiskAnalyzer; assert isinstance(...)
- TestGetStats.test_initial_stats_are_zero(self) (L506): Construct AdvancedDiskAnalyzer
- TestGetStats.test_stats_after_manual_scan_increment(self) (L513): Construct AdvancedDiskAnalyzer
- TestScanRealDirectory.test_scan_finds_files(self, tmp_path) (L530): Construct PosixScanner
- TestScanRealDirectory.test_scan_builds_correct_tree(self, tmp_path) (L545): Construct PosixScanner; assert size, file_count
- TestScanRealDirectory.test_scan_respects_cancellation(self, tmp_path) (L560): Construct PosixScanner; assert len(...)
- TestScanRealDirectory.test_scan_respects_cancellation._cancel_on_progress(files, bytez, path) (L567): cancel on progress via set
- TestScanRealDirectory.test_scan_cancelled_before_start(self, tmp_path) (L578): Construct PosixScanner; assert len(...)
- TestScanRealDirectory.test_scan_progress_callback(self, tmp_path) (L587): Construct PosixScanner; assert len, isinstance(...)
- TestScanRealDirectory.test_scan_progress_callback.capture(files, bytez, path) (L594): Capture via append
- TestScanRealDirectory.test_scan_progress_callback_fires_at_interval(self, tmp_path) (L606): Construct MagicMock
- TestScanSync._scan_and_build(self, root, **kwargs) (L624): Helper: scan synchronously and build tree, bypassing broken async wrapper.
- TestScanSync.test_returns_entries_and_tree(self, tmp_path) (L632): Exercise write_text; assert size
- TestScanSync.test_real_scan_sync(self, tmp_path) (L640): Exercise write_text; assert size
- TestScanSync.test_collects_all_files(self, tmp_path) (L648): Exercise write_text; assert file_count
- TestScanSync.test_with_progress_cb(self, tmp_path) (L660): Construct MagicMock; assert len(...)
- TestScannerBaseHelpers.test_check_cancel_default_not_set(self) (L677): Construct PosixScanner; assert _check_cancel
- TestScannerBaseHelpers.test_check_cancel_when_set(self) (L682): Construct PosixScanner; assert _check_cancel
- TestScannerBaseHelpers.test_report_increments_counter(self) (L689): Construct PosixScanner; assert _scanned_files
- TestScannerBaseHelpers.test_report_calls_callback_at_interval(self) (L695): Construct PosixScanner; assert len(...)
- TestScannerBaseHelpers.test_report_does_not_call_below_interval(self) (L706): Construct PosixScanner

## tests/test_apex_power_tools.py — Unit tests for the 10 Apex Enterprise Power Tools and Forensic Modules.
- test_file_signature_sniffer(tmp_path) (L19): Construct FileSignatureSniffer.sniff_file; assert is_spoofed, detected_format, lower, detected_mime
- test_binary_differ(tmp_path) (L36): Construct BinaryDiffer.compare_binary_files; assert is_identical, matching_percentage, total_differences_bytes, first_difference_offset, diff_chunks
- test_usn_journal_scanner() (L52): Construct UsnJournalScanner.query_volume_journal; assert drive_letter, is_supported, error
- test_par2_recovery(tmp_path) (L61): Construct Par2RecoveryEngine.inspect_par2_file; assert is_valid_par2, packets
- test_image_optimizer(tmp_path) (L77): Construct QImage; assert success, exists, output_path, compressed_size_bytes
- test_driver_store_cleaner() (L93): Construct DriverStoreCleaner.enumerate_drivers; assert published_name
- test_power_plan_optimizer() (L103): Construct PowerPlanOptimizer.get_status; assert active_scheme_name
- test_shellbags_privacy_cleaner() (L110): Construct ShellbagsPrivacyCleaner.scan_shell_activity; assert category, items_count
- test_hosts_file_manager(tmp_path) (L120): Construct HostsFileManager.parse_hosts_file; assert hostname, is_enabled, success
- test_notification_cleaner() (L145): Construct NotificationCleaner.get_status; assert total_size_bytes

## tests/test_app_updater.py — Tests for the Software Updater (winget wrapper).
- TestParser.test_parses_all_rows(self) (L26): Construct AppUpdater.parse_upgrade_output; assert len, all, isinstance(...)
- TestParser.test_fields_extracted(self) (L32): Construct AppUpdater.parse_upgrade_output; assert name, current, available, source
- TestParser.test_handles_unknown_version(self) (L41): Construct AppUpdater.parse_upgrade_output; assert current, available
- TestParser.test_skips_spinner_and_footer(self) (L47): Construct AppUpdater.parse_upgrade_output
- TestParser.test_empty_or_garbage_returns_empty(self) (L53): Construct AppUpdater.parse_upgrade_output; assert parse_upgrade_output
- TestParser.test_to_dict(self) (L58): Construct AppUpdater.parse_upgrade_output; assert set(...)
- TestCapability.test_is_available_returns_bool(self) (L67): Construct AppUpdater.is_available; assert is_available
- TestCapability.test_upgrade_requires_id(self) (L71): Construct AppUpdater; assert lower

## tests/test_audio_duplicate_finder.py — Tests for Chromaprint-inspired audio duplicate detection.
- _make_wav(path: Path, freq: float=440.0, duration: float=1.0, sr: int=11025) (L19): make wav via setnchannels, setsampwidth, setframerate
- _make_noise_wav(path: Path, duration: float=1.0, sr: int=11025) (L33): make noise wav via Random, setnchannels, setsampwidth
- test_fingerprint_is_list_of_ints(tmp_path: Path) (L48): Exercise _make_wav; assert isinstance, all, len(...)
- test_identical_wavs_compare_high(tmp_path: Path) (L58): Exercise _make_wav; assert audio_compare(...)
- test_different_tones_compare_low(tmp_path: Path) (L69): Exercise _make_wav; assert audio_compare(...)
- test_audio_compare_empty() (L85): Exercise audio_compare; assert audio_compare(...)
- test_finder_groups_identical_audio(tmp_path: Path) (L93): Construct AudioDuplicateFinder
- test_finder_excludes_non_audio(tmp_path: Path) (L111): Construct AudioDuplicateFinder; assert find_audio_duplicates
- test_finder_respects_exclude_dirs(tmp_path: Path) (L120): Construct Config; assert intersection
- test_finder_stats(tmp_path: Path) (L138): Construct AudioDuplicateFinder
- test_fallback_raw_fingerprint_for_mp3(tmp_path: Path) (L149): Exercise write_bytes; assert isinstance, len(...)

## tests/test_boot_performance.py — Tests for boot-performance analysis (parsing Windows' own diagnostics).
- TestParse.test_empty(self) (L18): Construct BootPerformanceMonitor._parse; assert _parse
- TestParse.test_parses_boots_and_issues(self) (L24): Construct BootPerformanceMonitor._parse; assert boot_ms, boot_seconds, name, kind, impact_seconds
- TestParse.test_single_object_not_list(self) (L44): Construct BootPerformanceMonitor._parse; assert boot_ms, kind
- TestParse.test_nameless_issue_skipped(self) (L53): Construct BootPerformanceMonitor._parse
- TestParse.test_bad_numbers_coerce_zero(self) (L59): Construct BootPerformanceMonitor._parse; assert boot_ms
- TestDataclasses.test_boot_seconds(self) (L68): Construct BootRecord; assert boot_seconds
- TestDataclasses.test_issue_to_dict(self) (L72): Construct BootIssue; assert set(...)
- TestSupport.test_is_supported_matches_platform(self) (L81): Construct BootPerformanceMonitor.is_supported; assert is_supported
- TestSupport.test_analyze_shape(self) (L85): Construct BootPerformanceMonitor; assert set, isinstance(...)

## tests/test_browser_cleaner.py — Tests for :mod:`cortex_unified.system_tools.browser_cleaner`.
- _make_sqlite(path: Path, table: str='cookies', rows: list | None=None, populate: bool=True) -> Path (L30): Create a tiny SQLite DB at *path* and return the path.
- _make_cache_dir(base: Path, category: str, *, count: int=3, file_size: int=100) -> Path (L59): Populate a cache sub-directory with dummy files.
- _make_chromium_profile(root: Path, *, browser: str='chrome') -> Path (L70): Build a realistic Chromium profile tree under *root*.
- _make_firefox_profile(base: Path) -> Path (L107): Build a realistic Firefox profile tree under *base*.
- fake_chromium_home(tmp_path, monkeypatch) (L144): Redirect LOCALAPPDATA so Chromium discovery hits our fake profiles.
- fake_firefox_home(tmp_path, monkeypatch) (L155): Redirect APPDATA so Firefox discovery hits our fake profiles.
- fake_multi_browser(tmp_path, monkeypatch) (L167): A single LOCALAPPDATA tree with Chrome, Edge, and Brave profiles.
- TestDeepBrowserCleanerInit.test_default_init(self) (L189): Construct DeepBrowserCleaner; assert keep_cookies, progress, cancel, Event, is_set
- TestDeepBrowserCleanerInit.test_keep_cookies_compiled(self) (L198): Construct DeepBrowserCleaner; assert keep_cookies, Pattern
- TestDeepBrowserCleanerInit.test_progress_callback_stored(self) (L204): Construct DeepBrowserCleaner
- TestDeepBrowserCleanerInit.test_custom_cancel_event(self) (L211): Construct DeepBrowserCleaner; assert is_set, cancel
- TestDeepBrowserCleanerInit.test_expert_mode_default_off(self) (L218): Construct DeepBrowserCleaner; assert expert_mode
- TestProfileDiscovery.test_chromium_discovers_default_profile(self, fake_chromium_home) (L230): Exercise _discover_chromium_profiles; assert any, str(...)
- TestProfileDiscovery.test_chromium_skips_nonexistent_root(self, fake_chromium_home, monkeypatch) (L236): Exercise _discover_chromium_profiles
- TestProfileDiscovery.test_firefox_discovers_profile(self, fake_firefox_home) (L241): Exercise _discover_firefox_profiles; assert any, str(...)
- TestProfileDiscovery.test_firefox_profiles_ini_parsing(self, fake_firefox_home, monkeypatch) (L247): Exercise write_text; assert any, str(...)
- TestProfileDiscovery.test_firefox_absolute_profile_in_ini(self, fake_firefox_home, tmp_path) (L264): Exercise mkdir; assert any, str(...)
- TestCookieCleaning.test_delete_non_matching_cookies(self, fake_chromium_home) (L283): Construct DeepBrowserCleaner
- TestCookieCleaning.test_keep_all_matching_cookies(self, fake_chromium_home) (L299): Construct DeepBrowserCleaner
- TestCookieCleaning.test_missing_db_returns_zero(self, fake_chromium_home) (L312): Construct DeepBrowserCleaner; assert clean_cookies_keep_list
- TestCookieCleaning.test_keep_list_regex_case_insensitive(self, fake_chromium_home) (L319): Construct DeepBrowserCleaner
- TestCookieCleaning.test_empty_keep_list_deletes_all(self, fake_chromium_home) (L331): Construct DeepBrowserCleaner
- TestClean.test_clean_removes_file(self, tmp_path) (L352): Construct DeepBrowserCleaner; assert exists
- TestClean.test_clean_removes_directory(self, tmp_path) (L361): Construct DeepBrowserCleaner; assert exists
- TestClean.test_clean_multiple_paths(self, tmp_path) (L371): Construct DeepBrowserCleaner; assert exists
- TestClean.test_clean_missing_path_handled_gracefully(self, tmp_path) (L381): Construct DeepBrowserCleaner
- TestClean.test_clean_shred_overwrites(self, tmp_path) (L390): Construct DeepBrowserCleaner; assert exists
- TestClean.test_clean_respects_cancel(self, tmp_path) (L399): Construct DeepBrowserCleaner
- TestClean.test_clean_progress_callback(self, tmp_path) (L410): Construct DeepBrowserCleaner; assert any(...)
- TestClean.test_clean_permission_error(self, tmp_path) (L419): Construct DeepBrowserCleaner; assert any(...)
- TestVacuum.test_vacuum_runs_without_error(self, tmp_path) (L442): Construct DeepBrowserCleaner
- TestVacuum.test_vacuum_missing_db_no_crash(self, tmp_path) (L454): Construct DeepBrowserCleaner
- TestVacuum.test_vacuum_progress_callback(self, tmp_path) (L461): Construct DeepBrowserCleaner; assert any(...)
- TestVacuum.test_vacuum_multiple_dbs(self, tmp_path) (L469): Construct DeepBrowserCleaner; assert len(...)
- TestBrowserDetection.test_scan_chromium_profile(self, fake_chromium_home) (L487): Construct DeepBrowserCleaner
- TestBrowserDetection.test_scan_firefox_profile(self, fake_firefox_home) (L499): Construct DeepBrowserCleaner
- TestBrowserDetection.test_all_browsers_detected(self, fake_multi_browser) (L511): Construct DeepBrowserCleaner
- TestBrowserDetection.test_firefox_browser_label(self, fake_firefox_home) (L520): Construct DeepBrowserCleaner; assert len(...)
- TestBrowserDetection.test_vivaldi_not_in_scope(self, fake_multi_browser) (L527): Construct DeepBrowserCleaner
- TestProgressCallback.test_progress_called_during_clean(self, tmp_path) (L542): Construct DeepBrowserCleaner; assert len(...)
- TestProgressCallback.test_progress_called_during_vacuum(self, tmp_path) (L551): Construct DeepBrowserCleaner; assert len(...)
- TestCancellation.test_cancel_stops_scan(self, fake_chromium_home) (L567): Construct DeepBrowserCleaner
- TestCancellation.test_cancel_stops_clean(self, tmp_path) (L575): Construct DeepBrowserCleaner
- TestCancellation.test_default_cancel_not_set(self) (L586): Construct DeepBrowserCleaner; assert is_set, cancel
- TestCancellation.test_cancel_event_prevents_scan_iteration(self, fake_chromium_home) (L591): Construct DeepBrowserCleaner
- TestCancellation.test_cancel_event_prevents_scan_iteration.interrupting_scan() (L598): Interrupting scan via original_scan; return result
- TestExpertMode.test_passwords_excluded_by_default(self, fake_chromium_home) (L615): Construct DeepBrowserCleaner; assert len(...)
- TestExpertMode.test_passwords_included_with_expert_mode(self, fake_chromium_home) (L625): Construct DeepBrowserCleaner; assert risk
- TestExpertMode.test_forms_always_included(self, fake_chromium_home) (L637): Construct DeepBrowserCleaner; assert len(...)
- TestExpertMode.test_passwords_risk_is_high(self, fake_chromium_home) (L647): Construct DeepBrowserCleaner; assert risk, can_vacuum
- TestSizeCalculation.test_file_size_reported(self, tmp_path) (L667): Construct Cleanable; assert size
- TestSizeCalculation.test_directory_size_summed(self, tmp_path) (L674): Exercise mkdir
- TestSizeCalculation.test_scan_returns_sizes(self, fake_chromium_home) (L683): Construct DeepBrowserCleaner; assert size
- TestSizeCalculation.test_nonexistent_profile_returns_empty(self, tmp_path) (L690): Construct DeepBrowserCleaner
- TestSizeCalculation.test_cleanable_dataclass_fields(self, tmp_path) (L696): Construct Cleanable; assert path, size, category, browser, description
- TestSizeCalculation.test_zero_size_item(self) (L708): Construct Cleanable; assert size
- TestScanIntegration.test_scan_returns_list(self, fake_chromium_home) (L721): Construct DeepBrowserCleaner; assert isinstance, len(...)
- TestScanIntegration.test_all_items_are_cleanable(self, fake_chromium_home) (L728): Construct DeepBrowserCleaner; assert isinstance(...)
- TestScanIntegration.test_no_duplicate_paths_in_scan(self, fake_chromium_home) (L735): Construct DeepBrowserCleaner; assert len, set(...)
- TestScanIntegration.test_cookie_risk_medium(self, fake_chromium_home) (L742): Construct DeepBrowserCleaner; assert risk
- TestScanIntegration.test_cache_risk_low(self, fake_chromium_home) (L749): Construct DeepBrowserCleaner; assert risk
- TestScanIntegration.test_vacuumable_items_flagged(self, fake_chromium_home) (L760): Construct DeepBrowserCleaner; assert category

## tests/test_browser_extensions.py — Tests for the read-only browser-extension auditor.
- TestPermissionRisk.test_broad_permissions_flagged(self) (L25): Construct BrowserExtension; assert broad_permissions
- TestPermissionRisk.test_narrow_permissions_not_flagged(self) (L30): Construct BrowserExtension; assert broad_permissions
- TestPermissionRisk.test_to_dict_includes_flag(self) (L35): Construct BrowserExtension
- _make_chrome_ext(base, browser_parts, ext_id, manifest) (L43): make chrome ext via joinpath, mkdir, write_text
- fake_home(tmp_path, monkeypatch) (L51): Fake home via mkdir, setenv; return result
- TestChromiumScan.test_finds_extension_with_permissions(self, fake_home) (L66): Construct BrowserExtensionAuditor; assert name, version, broad_permissions
- TestChromiumScan.test_host_permissions_merged(self, fake_home) (L81): Construct BrowserExtensionAuditor; assert broad_permissions
- TestChromiumScan.test_no_browsers_returns_empty(self, tmp_path, monkeypatch) (L92): Construct BrowserExtensionAuditor; assert audit
- TestChromiumScan.test_bad_manifest_skipped(self, fake_home) (L99): Construct BrowserExtensionAuditor; assert ext_id
- TestAuditNeverRaises.test_audit_returns_list(self) (L113): Construct BrowserExtensionAuditor; assert audit

## tests/test_cli.py — Tests for the Cortex Workstation CLI commands.
- test_cli_help() (L6): Test that the CLI root command displays help output.
- test_cli_version() (L13): Test that the CLI version command works.
- test_cli_clean_empty_help() (L20): Test the help output for the clean-empty subcommand.

## tests/test_cli_leftovers.py — Tests for the `cortex leftovers` command group (engine CLI).
- fake_scan(monkeypatch) (L19): Patch LeftoverScanner inside the engine CLI's lazy import target.
- fake_scan._make(findings) (L23): make via setattr; return result
- fake_scan._make.FakeScanner.__init__(self, *a, **k) (L27): init  : '__init__.'
- fake_scan._make.FakeScanner.scan_app(self, app) (L31): Scan app: 'scan_app.'; return result
- fake_scan._make.FakeScanner.scan_orphans(self) (L36): Scan orphans: 'scan_orphans.'; return result
- TestLeftoversScan.test_scan_json_emits_dicts(self, fake_scan) (L48): Construct LeftoverFinding; assert exit_code
- TestLeftoversScan.test_scan_human_output_shows_confidence(self, fake_scan) (L62): Construct LeftoverFinding; assert exit_code, output, count
- TestLeftoversScan.test_scan_clean_system_reports_nothing(self, fake_scan) (L73): Construct CliRunner; assert exit_code, output
- TestLeftoversClean.test_dry_run_is_default_and_deletes_nothing(self, fake_scan, tmp_path) (L83): Construct LeftoverFinding; assert exit_code, output, exists
- TestLeftoversClean.test_min_level_filters_questionable_by_default(self, fake_scan, tmp_path) (L95): Construct LeftoverFinding; assert str(...)
- TestLeftoversClean.test_apply_recycles_and_reports_freed_bytes(self, fake_scan, tmp_path, monkeypatch) (L116): Construct LeftoverFinding
- TestLeftoversClean.test_apply_recycles_and_reports_freed_bytes.FakeCleaner.clean(self, models, create_restore_point=False) (L129): Clean via CleanOutcome; return result
- TestLeftoversClean.test_apply_failure_exits_nonzero(self, fake_scan, tmp_path, monkeypatch) (L142): Construct LeftoverFinding; assert exit_code
- TestLeftoversClean.test_apply_failure_exits_nonzero.FailingCleaner.clean(self, models, create_restore_point=False) (L153): Clean via CleanOutcome; return result
- TestLeftoversOrphans.test_orphans_lists_findings(self, fake_scan) (L168): Construct LeftoverFinding; assert exit_code, output

## tests/test_cloud_aware_scan.py — Cloud-placeholder / reparse-point awareness in the scan engine.
- _mark_as_online(path: Path) -> None (L28): mark as online via utime
- cloud_attrs(monkeypatch) (L34): Make the walker see mtime-marked files as dehydrated placeholders.
- test_dehydrated_detects_all_recall_flags() (L44): Exercise is_dehydrated; assert is_dehydrated, FILE_ATTRIBUTE_REPARSE_POINT
- test_cloud_tag_covers_the_provider_range() (L55): Exercise is_cloud_tag; assert is_cloud_tag, IO_REPARSE_TAG_SYMLINK
- test_junction_is_distinct_from_symlink() (L63): Python reports junctions as non-symlinks, so they need their own check.
- test_attribute_readers_tolerate_a_posix_stat(tmp_path) (L69): Exercise write_text; assert attrs_of, reparse_tag_of
- test_describe_explains_special_entries() (L79): Exercise describe; assert describe, IO_REPARSE_TAG_MOUNT_POINT
- test_placeholder_entry_reclaims_nothing() (L88): Construct FileEntry; assert is_cloud_placeholder, reclaimable_size
- test_measured_on_disk_size_wins_over_logical() (L96): Construct FileEntry; assert reclaimable_size
- test_to_dict_reports_cloud_state() (L105): Construct FileEntry
- test_walker_skips_placeholders_and_reports_the_omission(tmp_path, cloud_attrs) (L114): Construct FastWalker; assert cloud_skipped, cloud_skipped_bytes, total_bytes
- test_placeholders_can_be_included_on_request(tmp_path, cloud_attrs) (L132): Construct FastWalker; assert name, path, files, cloud_skipped
- test_find_empty_never_offers_a_placeholder_for_deletion(tmp_path, cloud_attrs) (L146): Construct FastWalker
- test_walker_still_reports_plain_trees_unchanged(tmp_path) (L161): Construct FastWalker; assert files_scanned, cloud_skipped, junctions_skipped, total_bytes
- test_on_disk_size_for_a_plain_file(tmp_path) (L176): Exercise skipif; assert on_disk_size
- test_on_disk_size_falls_back_when_the_path_is_gone() (L183): Exercise on_disk_size; assert on_disk_size
- test_shredder_refuses_to_overwrite_a_placeholder(tmp_path, monkeypatch) (L190): Construct SecureDeleter; assert outcome, SKIPPED_UNSAFE, reason, exists

## tests/test_compact_os.py — Tests for NTFS CompactOS / compaction estimation logic.
- _write_text(folder: Path, name: str, size_kb: int=64) (L22): write text via encode, write_bytes, max
- _write_fill(folder: Path, name: str, size_kb: int=64) (L29): write fill via seed, write_bytes, bytes
- test_is_supported_reflects_platform() (L38): Construct CompactOSManager; assert is_supported
- test_system_folder_names_are_blocked() (L44): Exercise lower; assert _SYSTEM_TREES, _BLOCKED_NAMES
- test_estimate_text_heavy_folder(tmp_path) (L55): Construct CompactOSManager; assert size_bytes, compressible_ratio, estimated_savings
- test_estimate_incompressible_folder(tmp_path) (L67): Construct CompactOSManager; assert compressible_ratio
- test_find_compressible_folders_respects_min_size(tmp_path) (L77): Construct CompactOSManager
- test_find_skips_blocked_and_system_subfolders(tmp_path) (L94): Construct CompactOSManager
- test_compact_folder_refuses_system_tree(tmp_path) (L106): Construct CompactOSManager; assert success, message
- test_compact_folder_refuses_drive_root(tmp_path) (L115): Construct CompactOSManager; assert success, message

## tests/test_component_store.py — Component store (WinSxS) analysis, cleanup and leftover inventory.
- test_parses_windows_own_figures() (L89): Construct ComponentStore._parse_analysis; assert ok, actual_size, approx, reported_size, shared_with_windows
- test_reclaimable_estimate_excludes_shared_bytes() (L103): Space shared with Windows can never be reclaimed - don't promise it.
- test_explains_the_explorer_size_gap() (L111): Construct ComponentStore._parse_analysis; assert explorer_gap_note
- test_no_cleanup_needed_is_stated_plainly() (L121): Construct ComponentStore._parse_analysis; assert ok, cleanup_recommended, reclaimable_packages, message
- test_dism_error_is_surfaced_with_its_code() (L130): Construct ComponentStore._parse_analysis; assert ok, message
- test_unreadable_report_yields_zero_not_a_guess() (L137): Construct ComponentStore._parse_analysis; assert actual_size, reclaimable_estimate, ok
- test_analysis_to_dict_is_json_ready() (L145): Construct ComponentStore._parse_analysis
- test_unsupported_platform_is_reported(monkeypatch) (L154): Construct ComponentStore; assert supported, find_leftovers, run_servicing_task
- test_windows_managed_items_are_never_removable_here(tmp_path) (L168): Construct Leftover; assert removable_here, supported_removal
- test_safe_and_rollback_items_are_removable(tmp_path) (L180): Construct Leftover; assert removable_here, SAFE, LOSES_ROLLBACK
- test_rollback_window_is_computed_from_age(tmp_path) (L187): Construct Leftover; assert rollback_expired
- test_real_leftover_scan_is_readonly_and_sorted() (L201): Construct ComponentStore; assert exists, path, explanation, supported_removal
- test_winsxs_size_comes_from_dism_not_a_folder_walk() (L215): Walking WinSxS counts each hard link separately - the inflated figure
- test_installer_cache_is_flagged_managed_when_present() (L233): Construct ComponentStore; assert risk, MANAGED, removable_here
- test_leftover_scan_is_cancellable(tmp_path, monkeypatch) (L241): Construct ComponentStore
- test_cleanup_refuses_without_administrator(monkeypatch) (L255): Construct ComponentStore; assert success, lower, message
- test_cleanup_refuses_without_administrator._boom(*_a, **_k) (L260): boom: build/parse AssertionError
- test_cleanup_reports_measured_delta(monkeypatch) (L272): Construct ComponentStore; assert success, before_bytes, after_bytes, freed_bytes, reset_base
- test_cleanup_reports_measured_delta._fake_dism(args, timeout, cancel_event=None) (L278): fake dism via append, len; return result
- test_reset_base_is_passed_only_when_requested(monkeypatch) (L299): Construct ComponentStore; assert reset_base
- test_reset_base_is_passed_only_when_requested._fake_dism(args, timeout, cancel_event=None) (L305): fake dism via append; return result
- test_cleanup_is_honest_when_nothing_shrank(monkeypatch) (L321): Construct ComponentStore; assert success, freed_bytes, message
- test_cleanup_failure_explains_pending_servicing(monkeypatch) (L336): Construct ComponentStore; assert success, message, lower, freed_bytes
- test_decode_handles_dism_utf16_output() (L351): Construct ComponentStore._decode; assert _decode
- test_dir_size_never_raises_on_unreadable_paths(tmp_path) (L358): Construct ComponentStore._dir_size; assert _dir_size

## tests/test_config.py — Tests for the Cortex Workstation configuration loader.
- test_config_initialization_defaults() (L8): Test that Config initializes with defaults when no file is present.
- test_config_loading_from_file(temp_dir) (L14): Test that Config can load from a yaml file.

## tests/test_config_defaults_unified.py — The two config implementations must agree on safety-critical defaults.
- test_scan_defaults_match_the_legacy_baseline() (L29): A drift here means two different answers to "what is protected?".
- test_editor_state_directories_are_protected() (L39): Regression: these were protected only by the unused config.
- test_v2_defaults_do_not_alias_the_shared_constant() (L48): Deriving must copy: a mutation must not corrupt the shared baseline.
- test_legacy_config_does_not_alias_the_shared_constant() (L59): The CLI mutates ``config_data``; that must stay instance-local.
- test_both_configs_expose_the_same_flat_accessors() (L67): ``config_v2`` must stay a drop-in for the legacy attribute surface.

## tests/test_config_legacy_loading.py — Failure-reporting contracts for the legacy YAML config loader.
- test_missing_file_is_silent_and_yields_defaults(tmp_path, caplog) (L20): An absent config is the normal case - defaults apply, no warning.
- test_valid_yaml_is_loaded_over_the_defaults(tmp_path) (L29): Construct Config; assert exclude_dirs, config_data
- test_malformed_yaml_warns_and_falls_back(tmp_path, caplog) (L40): A syntax error must be reported, not silently ignored.
- test_non_mapping_top_level_warns_and_falls_back(tmp_path, caplog) (L50): A YAML list/scalar at the top level is a user mistake worth reporting.
- test_empty_file_is_treated_as_no_settings(tmp_path, caplog) (L60): An empty file parses to None; that is defaults, not an error.
- test_non_utf8_bytes_warn_and_fall_back(tmp_path, caplog) (L70): Explicit UTF-8 decoding means bad bytes are reported, not locale-luck.
- test_unicode_paths_load_correctly(tmp_path) (L81): Non-ASCII config content must load regardless of system locale.
- test_protected_directories_are_excluded_by_default(tmp_path, name) (L100): With no config file, the safety exclusions must still apply.
- test_defaults_are_the_baseline_when_no_file_exists(tmp_path) (L109): Construct Config; assert exclude_dirs, exclude_patterns, exclude_regex_patterns
- test_defaults_still_apply_when_the_file_is_broken(tmp_path, caplog) (L117): A malformed file must not silently drop the safety exclusions.
- test_user_settings_override_defaults_key_by_key(tmp_path) (L127): An explicit list replaces the default; untouched keys are inherited.
- test_config_data_is_mutable_without_corrupting_other_instances(tmp_path) (L140): The CLI applies overrides by assigning into ``config_data``.

## tests/test_config_v2.py — Tests for the new Pydantic-based configuration system.
- TestScanConfig.test_default_values(self) (L27): Test that default values are set correctly.
- TestScanConfig.test_min_age_validation(self) (L37): Test that min_age_days is validated.
- TestScanConfig.test_max_depth_validation(self) (L51): Test that max_depth is validated.
- TestPerformanceConfig.test_thread_clamping(self) (L69): Test that thread count is clamped to reasonable limits.
- TestPerformanceConfig.test_chunk_size_validation(self) (L80): Test that chunk_size is validated.
- TestSecurityConfig.test_default_action_validation(self) (L98): Test that default_action only accepts valid values.
- TestSecurityConfig.test_shred_passes_validation(self) (L110): Test that shred_passes is validated.
- TestLoggingConfig.test_log_level_validation(self) (L128): Test that log_level only accepts valid values.
- TestConfig.test_default_initialization(self) (L142): Test that Config initializes with defaults.
- TestConfig.test_nested_configuration(self) (L152): Test that nested configuration works.
- TestConfig.test_environment_variable_override(self) (L164): Test that environment variables override defaults.
- TestConfig.test_yaml_loading(self, tmp_path) (L180): Test loading configuration from YAML file.
- TestConfig.test_save_to_yaml(self, tmp_path) (L207): Test saving configuration to YAML file.
- TestConfig.test_backward_compatibility_properties(self) (L224): Test that backward compatibility properties work.
- TestConfig.test_matches_exclude_patterns(self) (L242): Test the matches_exclude_patterns method.
- TestConfig.test_validation_error_messages(self) (L268): Test that validation errors provide helpful messages.
- TestCreateDefaultConfig.test_creates_config_file(self, tmp_path) (L281): Test that create_default_config creates a valid file.
- TestConfigPropertyBased.test_min_age_days_always_valid_in_range(self, days) (L306): Test that any valid min_age_days value works.
- TestConfigPropertyBased.test_thread_count_always_clamped(self, threads) (L312): Test that thread count is always clamped to valid range.
- TestConfigPropertyBased.test_exclude_patterns_accept_any_string(self, pattern) (L318): Test that exclude patterns accept any string.
- TestConfigIntegration.test_full_workflow(self, tmp_path) (L331): Test complete workflow: create, save, load, modify, save.
- TestConfigIntegration.test_environment_overrides_yaml(self, tmp_path) (L356): Test that environment variables override YAML values.

## tests/test_content_defined_chunker.py — Tests for FastCDC / VectorCDC content-defined chunking.
- test_gear_chunk_deterministic() (L20): Exercise gear_chunk; assert length
- test_gear_chunk_shift_resistant() (L30): Exercise Random; assert fingerprint
- test_gear_chunk_empty() (L44): Exercise gear_chunk; assert gear_chunk(...)
- test_gear_chunk_invalid_params() (L49): Exercise raises
- test_jaccard_basic() (L55): Exercise jaccard; assert approx
- test_chunk_similarity_identical_is_one() (L63): Exercise chunk_similarity; assert chunk_similarity(...)
- test_chunk_similarity_different_is_low() (L69): Exercise chunk_similarity; assert chunk_similarity(...)
- test_file_chunks_reads_file(tmp_path: Path) (L76): Exercise write_bytes; assert st_size, length, stat
- test_file_chunks_missing_raises(tmp_path: Path) (L85): Exercise raises
- test_finder_groups_shifted_duplicates(tmp_path: Path) (L93): Construct ContentDefinedChunker
- test_finder_excludes_non_eligible_or_empty(tmp_path: Path) (L115): Construct ContentDefinedChunker; assert find_cdc_duplicates
- test_finder_respects_exclude_dirs(tmp_path: Path) (L123): Construct Config; assert intersection
- test_finder_stats(tmp_path: Path) (L142): Construct ContentDefinedChunker
- test_vector_cdc_chunk_produces_valid_chunks() (L154): Exercise vector_cdc_chunk; assert length
- test_idea_inverted_index() (L164): Construct Path

## tests/test_core_proc.py — Cancellable, tree-safe subprocess execution (``core.proc``).
- test_normal_completion_returns_output() (L25): Exercise run; assert returncode, stdout
- test_nonzero_exit_is_reported_not_raised() (L33): Exercise run; assert returncode
- test_real_timeout_raises_and_is_prompt() (L40): Exercise perf_counter
- test_cancel_event_raises_and_is_prompt() (L53): Exercise Event
- test_cancel_event_raises_and_is_prompt._cancel_soon() (L59): cancel soon via sleep, set
- test_cancel_takes_priority_even_with_a_long_timeout() (L72): A cancel_event must not wait for a generous timeout to take effect.
- test_timeout_kills_the_whole_process_tree(tmp_path) (L84): The property that matters: children of the killed process must die too.
- test_process_cancelled_is_a_subprocess_error() (L112): Existing ``except (OSError, subprocess.SubprocessError)`` call sites
- test_run_never_leaves_output_unread_on_success() (L118): A normal fast command must not be affected by the polling loop at all.
- test_text_mode_decodes_output() (L126): Exercise run; assert stdout
- test_missing_executable_raises_oserror() (L134): Exercise raises

## tests/test_czkawka_tools.py — Tests for czkawka multi-tool suite — empty, broken, bad-ext, bad-names, exif, temp, video-optimizer.
- _touch_empty(path: Path) -> Path (L41): touch empty via mkdir, write_bytes; return result
- _touch_file(path: Path, content: bytes=b'hello') -> Path (L48): touch file via mkdir, write_bytes; return result
- _make_minimal_png(path: Path) -> Path (L55): Create a minimal valid PNG with a 1x1 white pixel.
- _make_minimal_png._chunk(ctype: bytes, data: bytes) -> bytes (L62): chunk via to_bytes, crc32; return result
- _make_minimal_jpg(path: Path) -> Path (L76): Create a minimal JPEG file.
- _make_minimal_pdf(path: Path) -> Path (L83): make minimal pdf via mkdir, write_bytes; return result
- _make_minimal_zip(path: Path) -> Path (L90): make minimal zip via mkdir, ZipFile, writestr; return result
- TestEmptyFinder.test_finds_empty_files(self, tmp_path: Path) (L105): Construct EmptyFinder
- TestEmptyFinder.test_finds_empty_dirs(self, tmp_path: Path) (L114): Construct EmptyFinder
- TestEmptyFinder.test_returns_empty_when_nothing_empty(self, tmp_path: Path) (L126): Construct EmptyFinder; assert empty_files, empty_folders
- TestEmptyFinder.test_scanned_count(self, tmp_path: Path) (L134): Construct EmptyFinder; assert scanned
- TestEmptyFinder.test_duration_is_non_negative(self, tmp_path: Path) (L142): Construct EmptyFinder; assert duration
- TestEmptyFinder.test_cancel_stops_early(self, tmp_path: Path) (L148): Construct EmptyFinder; assert scanned
- TestEmptyFinder.test_progress_callback_invoked(self, tmp_path: Path) (L156): Construct EmptyFinder; assert len(...)
- TestEmptyFinder.test_exclude_dirs(self, tmp_path: Path) (L164): Construct Config
- TestEmptyFinder.test_nested_empty_files(self, tmp_path: Path) (L177): Construct EmptyFinder; assert empty_files
- TestInvalidSymlinkFinder.test_finds_broken_symlink(self, tmp_path: Path) (L194): Construct InvalidSymlinkFinder; assert broken
- TestInvalidSymlinkFinder.test_ignores_valid_symlink(self, tmp_path: Path) (L202): Construct InvalidSymlinkFinder; assert broken
- TestInvalidSymlinkFinder.test_empty_when_no_symlinks(self, tmp_path: Path) (L211): Construct InvalidSymlinkFinder; assert broken, scanned
- TestInvalidSymlinkFinder.test_scanned_count(self, tmp_path: Path) (L218): Construct InvalidSymlinkFinder; assert scanned
- TestInvalidSymlinkFinder.test_relative_symlink_broken(self, tmp_path: Path) (L229): Construct InvalidSymlinkFinder; assert broken
- TestInvalidSymlinkFinder.test_relative_symlink_valid(self, tmp_path: Path) (L236): Construct InvalidSymlinkFinder; assert broken
- TestInvalidSymlinkFinder.test_cancel_stops_early(self, tmp_path: Path) (L245): Construct InvalidSymlinkFinder; assert scanned
- TestInvalidSymlinkFinder.test_exclude_dirs(self, tmp_path: Path) (L253): Construct Config; assert broken
- TestBrokenFileFinder.test_finds_corrupted_zip(self, tmp_path: Path) (L272): Construct BrokenFileFinder
- TestBrokenFileFinder.test_ignores_valid_zip(self, tmp_path: Path) (L279): Construct BrokenFileFinder
- TestBrokenFileFinder.test_finds_bad_pdf(self, tmp_path: Path) (L286): Construct BrokenFileFinder
- TestBrokenFileFinder.test_ignores_valid_pdf(self, tmp_path: Path) (L293): Construct BrokenFileFinder
- TestBrokenFileFinder.test_finds_corrupted_png(self, tmp_path: Path) (L300): Construct BrokenFileFinder
- TestBrokenFileFinder.test_ignores_valid_png(self, tmp_path: Path) (L310): Construct BrokenFileFinder
- TestBrokenFileFinder.test_ignores_non_supported_extension(self, tmp_path: Path) (L317): Construct BrokenFileFinder
- TestBrokenFileFinder.test_empty_returns_nothing(self, tmp_path: Path) (L324): Construct BrokenFileFinder
- TestBrokenFileFinder.test_cancel_stops_early(self, tmp_path: Path) (L329): Construct BrokenFileFinder
- TestBrokenFileFinder.test_exclude_dirs(self, tmp_path: Path) (L337): Construct Config
- TestBadExtensionFinder.test_finds_png_with_wrong_ext(self, tmp_path: Path) (L356): Construct BadExtensionFinder; assert path, actual, claimed
- TestBadExtensionFinder.test_finds_jpg_with_wrong_ext(self, tmp_path: Path) (L366): Construct BadExtensionFinder; assert actual
- TestBadExtensionFinder.test_ignores_correct_extension(self, tmp_path: Path) (L374): Construct BadExtensionFinder
- TestBadExtensionFinder.test_ignores_extensionless_files(self, tmp_path: Path) (L381): Construct BadExtensionFinder
- TestBadExtensionFinder.test_allows_jpg_jpeg_alias(self, tmp_path: Path) (L388): Construct BadExtensionFinder
- TestBadExtensionFinder.test_empty_dir(self, tmp_path: Path) (L395): Construct BadExtensionFinder
- TestBadExtensionFinder.test_cancel_stops_early(self, tmp_path: Path) (L400): Construct BadExtensionFinder
- TestBadExtensionFinder.test_exclude_dirs(self, tmp_path: Path) (L409): Construct Config; assert name, parent, path
- TestBadNamesFinder.test_finds_control_chars(self, tmp_path: Path) (L432): Construct BadNamesFinder; assert name
- TestBadNamesFinder.test_finds_windows_reserved_chars(self, tmp_path: Path) (L442): Construct BadNamesFinder; assert len(...)
- TestBadNamesFinder.test_finds_leading_space(self, tmp_path: Path) (L451): Construct BadNamesFinder; assert name
- TestBadNamesFinder.test_finds_trailing_space(self, tmp_path: Path) (L459): Construct BadNamesFinder; assert name
- TestBadNamesFinder.test_finds_trailing_dot(self, tmp_path: Path) (L467): Construct BadNamesFinder; assert name
- TestBadNamesFinder.test_finds_reserved_windows_names(self, tmp_path: Path) (L474): Construct BadNamesFinder; assert len(...)
- TestBadNamesFinder.test_ignores_good_names(self, tmp_path: Path) (L488): Construct BadNamesFinder
- TestBadNamesFinder.test_finds_bad_dir_names(self, tmp_path: Path) (L498): Construct BadNamesFinder; assert name
- TestBadNamesFinder.test_cancel_stops_early(self, tmp_path: Path) (L505): Construct BadNamesFinder
- TestBadNamesFinder.test_exclude_dirs(self, tmp_path: Path) (L517): Construct Config; assert name, parent
- TestExifCleaner.test_scan_finds_exif_if_pil_available(self, tmp_path: Path) (L537): Construct Image.new; assert isinstance(...)
- TestExifCleaner.test_scan_skips_non_image_files(self, tmp_path: Path) (L551): Construct ExifCleaner
- TestExifCleaner.test_scan_empty_dir(self, tmp_path: Path) (L558): Construct ExifCleaner
- TestExifCleaner.test_strip_returns_dict_for_empty_list(self, tmp_path: Path) (L564): Construct ExifCleaner
- TestExifCleaner.test_cancel_stops_scan_early(self, tmp_path: Path) (L570): Construct ExifCleaner
- TestExifCleaner.test_exclude_dirs(self, tmp_path: Path) (L578): Construct Config; assert name, parent
- TestTempFileFinder.test_finds_tmp_extension(self, tmp_path: Path) (L598): Construct TempFileFinder
- TestTempFileFinder.test_finds_temp_extension(self, tmp_path: Path) (L607): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_log_files(self, tmp_path: Path) (L613): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_bak_files(self, tmp_path: Path) (L619): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_old_files(self, tmp_path: Path) (L625): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_swap_files(self, tmp_path: Path) (L631): Construct TempFileFinder
- TestTempFileFinder.test_finds_tilde_backup_files(self, tmp_path: Path) (L640): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_thumbs_db(self, tmp_path: Path) (L646): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_ds_store(self, tmp_path: Path) (L652): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_desktop_ini(self, tmp_path: Path) (L658): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_dmp_files(self, tmp_path: Path) (L664): Construct TempFileFinder; assert name
- TestTempFileFinder.test_ignores_normal_files(self, tmp_path: Path) (L670): Construct TempFileFinder
- TestTempFileFinder.test_empty_dir(self, tmp_path: Path) (L676): Construct TempFileFinder
- TestTempFileFinder.test_cancel_stops_early(self, tmp_path: Path) (L681): Construct TempFileFinder
- TestTempFileFinder.test_exclude_dirs(self, tmp_path: Path) (L689): Construct Config; assert name, parent
- TestTempFileFinder.test_lock_files(self, tmp_path: Path) (L700): Construct TempFileFinder; assert name
- TestTempFileFinder.test_finds_nested_temp_files(self, tmp_path: Path) (L706): Construct TempFileFinder; assert name
- TestVideoOptimizer.test_find_static_borders_returns_none_on_missing_ffprobe(self, tmp_path: Path) (L720): Construct VideoOptimizer
- TestVideoOptimizer.test_find_static_borders_returns_none_on_nonzero_exit(self, tmp_path: Path) (L729): Construct MagicMock
- TestVideoOptimizer.test_find_static_borders_parses_json(self, tmp_path: Path) (L739): Construct MagicMock; assert width, height, codec, bitrate, duration
- TestVideoOptimizer.test_optimize_returns_false_on_ffmpeg_error(self, tmp_path: Path) (L770): Construct MagicMock
- TestVideoOptimizer.test_optimize_returns_false_on_exception(self, tmp_path: Path) (L780): Construct VideoOptimizer
- TestVideoOptimizer.test_video_info_dataclass(self) (L789): Construct VideoInfo; assert width, has_static_borders, border_pixels
- TestSniffExtension.test_sniff_png(self, tmp_path: Path) (L813): Exercise _make_minimal_png; assert _sniff_extension(...)
- TestSniffExtension.test_sniff_jpg(self, tmp_path: Path) (L818): Exercise _make_minimal_jpg; assert _sniff_extension(...)
- TestSniffExtension.test_sniff_pdf(self, tmp_path: Path) (L823): Exercise _make_minimal_pdf; assert _sniff_extension(...)
- TestSniffExtension.test_sniff_zip(self, tmp_path: Path) (L828): Exercise _make_minimal_zip; assert _sniff_extension(...)
- TestSniffExtension.test_sniff_unknown_returns_none(self, tmp_path: Path) (L833): Exercise _touch_file
- TestExports.test_all_exports_present(self) (L847): Verify all exports present
- TestExports.test_magic_headers_completeness(self) (L868): Exercise values; assert values

## tests/test_defender.py — Tests for the Windows Defender status reader (parsing + gating).
- TestStatusParse.test_empty(self) (L14): Construct WindowsDefender._parse_status; assert available, _parse_status
- TestStatusParse.test_healthy(self) (L19): Construct WindowsDefender._parse_status; assert available, realtime_protection, antivirus_enabled, signature_age_days, healthy
- TestStatusParse.test_unhealthy_old_signatures(self) (L32): Construct WindowsDefender._parse_status; assert healthy
- TestStatusParse.test_unhealthy_rtp_off(self) (L39): Construct WindowsDefender._parse_status; assert healthy, _parse_status
- TestStatusParse.test_list_payload(self) (L44): Construct WindowsDefender._parse_status; assert available, _parse_status
- TestStatusParse.test_wmi_date(self) (L49): Construct WindowsDefender._parse_status; assert last_quick_scan
- TestThreatsParse.test_empty(self) (L58): Construct WindowsDefender._parse_threats; assert _parse_threats
- TestThreatsParse.test_single_and_list(self) (L62): Construct WindowsDefender._parse_threats; assert _parse_threats
- TestThreatsParse.test_threat_fields(self) (L69): Construct WindowsDefender._parse_threats
- TestDataclassAndSupport.test_to_dict(self) (L79): Construct DefenderStatus; assert set(...)
- TestDataclassAndSupport.test_is_supported(self) (L87): Construct WindowsDefender.is_supported; assert is_supported
- TestDataclassAndSupport.test_status_never_raises(self) (L91): Construct WindowsDefender; assert status

## tests/test_deleter.py — Tests for the safe Deleter component and dry-run safety modes.
- test_deleter_dry_run(test_env) (L8): Test that Deleter does not remove files in dry-run mode.
- test_deleter_real_deletion(test_env) (L24): Test that Deleter actually removes files when dry-run is False.
- test_deleter_handles_missing_files(test_env) (L40): Test that Deleter gracefully handles files that are already deleted.

## tests/test_directstorage_optimizer.py — Unit tests for DirectStorage & BypassIO hardware optimizer.
- test_parse_bypassio_supported() (L12): Construct DirectStorageOptimizer.parse_bypassio_output; assert volume_letter, is_supported, storage_type, driver_name, blocking_minifilters
- test_parse_bypassio_blocked() (L27): Construct DirectStorageOptimizer.parse_bypassio_output; assert volume_letter, is_supported, blocking_minifilters, storage_type
- test_audit_structure() (L42): Construct DirectStorageOptimizer; assert isinstance(...)

## tests/test_disk_health.py — Tests for the read-only S.M.A.R.T. / disk-health monitor.
- TestParse.test_empty_returns_empty_list(self) (L19): Construct DiskHealthMonitor._parse; assert _parse
- TestParse.test_invalid_json_returns_empty(self) (L24): Construct DiskHealthMonitor._parse; assert _parse
- TestParse.test_single_object_becomes_one_disk(self) (L28): Construct DiskHealthMonitor._parse; assert name, media_type, health_status, is_healthy, size_bytes
- TestParse.test_array_of_disks(self) (L49): Construct DiskHealthMonitor._parse; assert media_type, health_status, is_healthy
- TestParse.test_missing_reliability_counters_stay_none(self) (L61): Construct DiskHealthMonitor._parse; assert wear_percent, temperature_c, reallocated_sectors, power_on_hours
- TestParse.test_garbage_numeric_fields_coerce_to_none(self) (L73): Construct DiskHealthMonitor._parse; assert size_bytes, wear_percent
- TestParse.test_defaults_for_absent_keys(self) (L83): Construct DiskHealthMonitor._parse; assert name, media_type, health_status, is_healthy
- TestToDict.test_to_dict_roundtrip_keys(self) (L94): Construct DiskHealth; assert set(...)
- TestSupport.test_is_supported_matches_platform(self) (L114): Construct DiskHealthMonitor.is_supported; assert is_supported
- TestSupport.test_get_health_returns_list(self) (L118): Construct DiskHealthMonitor; assert isinstance, all(...)

## tests/test_drive_optimizer.py — Tests for the media-aware Drive Optimizer.
- TestRecommendation.test_hdd_recommends_defrag(self) (L24): Construct DriveOptimizer._recommend; assert DEFRAG
- TestRecommendation.test_ssd_recommends_trim(self) (L29): Construct DriveOptimizer._recommend; assert TRIM, lower
- TestRecommendation.test_nvme_recommends_trim(self) (L35): Construct DriveOptimizer._recommend; assert TRIM, _recommend, NVME
- TestRecommendation.test_unknown_recommends_none(self) (L39): Construct DriveOptimizer._recommend; assert NONE, _recommend, UNKNOWN
- TestSafety.test_is_supported_matches_platform(self) (L46): Construct DriveOptimizer.is_supported; assert is_supported
- TestSafety.test_list_drives_returns_list(self) (L50): Construct DriveOptimizer; assert list_drives
- TestSafety.test_refuses_defrag_on_ssd(self, monkeypatch) (L54): Even if the caller explicitly asks to DEFRAG an SSD, it must refuse.
- TestSafety.test_non_windows_returns_unsupported(self) (L72): Construct DriveOptimizer; assert success

## tests/test_driver_inventory.py — Tests for the read-only driver inventory (parsing + platform gating).
- TestParse.test_empty(self) (L14): Construct DriverInventory._parse; assert _parse
- TestParse.test_single_object(self) (L20): Construct DriverInventory._parse; assert device_name, provider, version, device_class, date
- TestParse.test_dedupes_identical_name_version(self) (L37): Construct DriverInventory._parse; assert len(...)
- TestParse.test_skips_nameless(self) (L47): Construct DriverInventory._parse; assert _parse
- TestParse.test_yyyymmdd_date(self) (L52): Construct DriverInventory._parse; assert date
- TestSupport.test_is_supported_matches_platform(self) (L61): Construct DriverInventory.is_supported; assert is_supported
- TestSupport.test_list_drivers_returns_list(self) (L65): Construct DriverInventory; assert isinstance(...)
- TestSupport.test_to_dict(self) (L72): Construct DriverInfo; assert set(...)

## tests/test_engine.py — Tests for the cortex_unified.engine package.
- tree(tmp_path: Path) -> Path (L37): A small mixed tree: files of various sizes, empties, nested dirs.
- TestFastWalker.test_scan_counts_and_bytes(self, tree: Path) (L63): Construct FastWalker; assert total_bytes, files_scanned, files
- TestFastWalker.test_min_size_filter(self, tree: Path) (L72): Construct FastWalker; assert size, files, name, path
- TestFastWalker.test_excludes_glob(self, tree: Path) (L79): Construct FastWalker; assert suffix, files, path
- TestFastWalker.test_find_empty(self, tree: Path) (L85): Construct FastWalker
- TestFastWalker.test_symlinks_not_followed_by_default(self, tmp_path: Path) (L95): Construct FastWalker; assert files, name, path
- TestFastWalker.test_cancel_stops_iteration(self, tree: Path) (L111): Construct FastWalker; assert len(...)
- TestPathGuard.test_sibling_name_not_falsely_protected(self, tmp_path: Path) (L128): The legacy prefix matcher blocked '/usrdata' because it startswith
- TestPathGuard.test_blocks_home_root(self) (L137): Construct PathGuard; assert safe, lower, reason
- TestPathGuard.test_blocks_windows_system_dirs(self) (L145): Construct PathGuard; assert safe, check, get, environ
- TestPathGuard.test_blocks_posix_system_dirs(self) (L152): Construct PathGuard; assert safe, check
- TestPathGuard.test_sandbox_confinement(self, tmp_path: Path) (L158): Construct PathGuard; assert safe, check
- TestDuplicates.test_hash_file_stable_and_none_on_missing(self, tmp_path: Path) (L177): Exercise write_bytes; assert hash_file(...)
- TestDuplicates.test_finds_content_duplicates(self, tree: Path) (L186): Construct DuplicateFinderEngine.wasted_bytes; assert issubset, wasted_bytes
- TestDuplicates.test_unique_sizes_not_flagged(self, tmp_path: Path) (L196): Construct DuplicateFinderEngine; assert find
- TestStorage.test_detect_returns_storageinfo(self, tmp_path: Path) (L213): Exercise detect_storage; assert kind
- TestStorage.test_overwrite_effective_only_for_hdd(self) (L219): Verify overwrite effective only for hdd (overwrite_effective, HDD, SSD, NVME)
- TestStorage.test_probe_caches(self, tmp_path: Path) (L226): Construct StorageProbe
- _FakeProbe.__init__(self, kind: StorageKind) (L240): Initialize _forced
- _FakeProbe.probe(self, path) (L245): Probe: build/parse StorageInfo; return result
- TestSecureDeleter.test_dry_run_touches_nothing(self, tmp_path: Path) (L252): Construct SecureDeleter; assert outcome, WOULD_DELETE, exists
- TestSecureDeleter.test_plain_delete_file(self, tmp_path: Path) (L261): Construct SecureDeleter; assert outcome, DELETED, exists
- TestSecureDeleter.test_plain_delete_directory_is_guarded(self, tmp_path: Path) (L269): Directory deletion must pass through the guard (legacy bug: it did not).
- TestSecureDeleter.test_guard_blocks_unsafe(self) (L278): Construct Path.home; assert outcome, SKIPPED_UNSAFE, exists, home
- TestSecureDeleter.test_overwrite_on_hdd_wipes(self, tmp_path: Path) (L284): Construct SecureDeleter; assert outcome, OVERWRITTEN, exists
- TestSecureDeleter.test_overwrite_on_ssd_refuses_honestly(self, tmp_path: Path) (L293): Construct SecureDeleter; assert kind, SSD, value, exists
- TestSecureDeleter.test_overwrite_on_ssd_forced_best_effort(self, tmp_path: Path) (L303): Construct SecureDeleter; assert outcome, OVERWRITTEN, reason, exists
- TestSecureDeleter.test_summary_aggregates(self, tmp_path: Path) (L313): Construct SecureDeleter; assert get

## tests/test_engine_cloud_safety.py — Cloud-placeholder and reparse-point safety in the scan engine.
- test_recall_attributes_mean_dehydrated() (L35): Exercise is_dehydrated; assert is_dehydrated, FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS, FILE_ATTRIBUTE_RECALL_ON_OPEN, FILE_ATTRIBUTE_OFFLINE, FILE_ATTRIBUTE_REPARSE_POINT
- test_cloud_tag_family_is_matched() (L45): Exercise is_cloud_tag; assert is_cloud_tag, IO_REPARSE_TAG_CLOUD, IO_REPARSE_TAG_MOUNT_POINT
- test_junction_detected_by_tag_only() (L55): Exercise is_junction; assert is_junction, IO_REPARSE_TAG_MOUNT_POINT, IO_REPARSE_TAG_SYMLINK
- test_describe_explains_each_special_case() (L62): Exercise describe; assert describe, FILE_ATTRIBUTE_OFFLINE, FILE_ATTRIBUTE_REPARSE_POINT, IO_REPARSE_TAG_MOUNT_POINT, FILE_ATTRIBUTE_SPARSE_FILE
- test_pure_helpers_never_raise_on_missing_attributes() (L72): Non-Windows stat results have no attribute fields; that must be fine.
- _mark_offline(path) -> bool (L86): Flag *path* with FILE_ATTRIBUTE_OFFLINE; False if the OS refused.
- cloud_tree(tmp_path) (L97): A folder with one local file, one simulated placeholder, one junction.
- test_placeholder_excluded_and_reported(cloud_tree) (L116): Construct FastWalker; assert total_bytes, cloud_skipped, cloud_skipped_bytes
- test_junction_not_descended(cloud_tree) (L131): Construct FastWalker; assert junctions_skipped, files_scanned
- test_placeholder_skip_is_opt_out(cloud_tree) (L141): Read-only inventory callers can still see placeholders.
- test_placeholder_is_not_reported_as_empty(cloud_tree) (L155): find_empty must not offer a placeholder as a deletable empty file.
- test_shredder_refuses_cloud_placeholder(cloud_tree) (L163): Overwriting a placeholder would download it first - refuse instead.
- test_on_disk_size_matches_a_plain_file(tmp_path) (L183): Exercise write_bytes
- test_on_disk_size_returns_none_for_missing_path(tmp_path) (L193): Exercise on_disk_size; assert on_disk_size
- test_entry_falls_back_to_logical_size_when_unmeasured(tmp_path) (L198): reclaimable_size must never under-report an ordinary file.

## tests/test_engine_service.py — Tests for the engine's category registry and CleanerService orchestration.
- TestCategories.test_default_registry_nonempty_and_typed(self) (L24): Exercise default_categories; assert risk
- TestCategories.test_ids_unique(self) (L31): Exercise len; assert len, set(...)
- TestCategories.test_risk_ranking(self) (L36): Verify risk ranking (rank, LOW, MEDIUM, HIGH)
- TestDeepDiscovery.test_discovers_nested_cache_dirs(self, tmp_path, monkeypatch) (L43): Exercise mkdir; assert endswith
- TestDeepDiscovery.test_does_not_recurse_into_matched_cache(self, tmp_path) (L58): Exercise mkdir; assert sum, str(...)
- TestDeepDiscovery.test_discovery_is_cached(self, tmp_path) (L67): Exercise mkdir
- TestBreakdown.test_groups_files_into_top_folders(self, tmp_path) (L79): Construct CleanupCategory; assert len(...)
- TestBreakdown.test_limit_respected(self, tmp_path) (L100): Construct CleanupCategory; assert breakdown
- TestBreakdown.test_empty(self) (L110): Construct CleanupCategory; assert breakdown
- TestCleanerServiceCategories._make_category(self, tmp_path: Path) -> CleanupCategory (L119): make category: build CleanupCategory, via mkdir, write_bytes; return result
- TestCleanerServiceCategories.test_scan_and_clean_dry_run_then_real(self, tmp_path: Path, monkeypatch) (L134): Construct CleanerService; assert file_count, total_bytes, total_reclaimable_bytes, total_files, outcome
- TestCleanerServiceCategories.test_scan_categories_respects_max_risk(self) (L159): Construct CleanerService; assert total_reclaimable_bytes
- TestCleanerServiceCategories.test_report_to_dict(self, tmp_path: Path) (L167): Construct CleanerService
- TestScanProgressAndCancel.test_progress_callback_fires(self, tmp_path) (L180): Construct CleanupCategory; assert isinstance(...)
- TestScanProgressAndCancel.test_cancel_event_stops_scan(self) (L199): Construct CleanerService; assert total_files
- TestScanProgressAndCancel.test_find_duplicates_accepts_progress_and_cancel(self, tmp_path) (L207): Construct CleanerService; assert values
- TestCleanerServiceAnalysis.tree(self, tmp_path: Path) -> Path (L219): Tree via write_text, write_bytes, touch; return result
- TestCleanerServiceAnalysis.test_find_duplicates(self, tree: Path) (L228): Construct CleanerService; assert issubset
- TestCleanerServiceAnalysis.test_find_large_files(self, tree: Path) (L234): Construct CleanerService; assert name, path, size
- TestCleanerServiceAnalysis.test_find_empty(self, tree: Path) (L241): Construct CleanerService; assert name

## tests/test_enterprise_suite_tools.py — Tests for Enterprise Next-Gen Storage, Security & Forensics Suite tools.
- test_vss_manager() (L22): Construct VssManager; assert total_used_bytes, total_allocated_bytes, shadows, storages
- test_dev_drive_optimizer() (L33): Construct DevDriveOptimizer; assert drives, endswith, drive_letter, total_space_bytes
- test_bitlocker_auditor() (L45): Construct BitLockerAuditor; assert fully_protected_count, unprotected_count, warnings
- test_junction_auditor() (L55): Construct Path; assert total_reparse_points
- test_bitrot_scrubber(tmp_path) (L70): Construct BitRotScrubber; assert total_files_scanned, new_files_indexed, corrupted_count, clean_files_count, path
- test_memory_compression_tuner() (L104): Construct MemoryCompressionTuner; assert total_physical_ram_bytes, status, available_physical_ram_bytes, compression_ratio
- test_sandbox_cleaner() (L115): Construct SandboxCleaner; assert total_reclaimable_bytes, artifacts
- test_smb_share_auditor() (L124): Construct SmbShareAuditor; assert total_shares, shares
- test_process_token_auditor() (L133): Construct ProcessTokenAuditor; assert processes, pid, integrity_level
- test_storage_growth_tracker(tmp_path) (L144): Construct StorageGrowthTracker; assert total_bytes, total_files, net_growth_bytes, top_growing_dirs

## tests/test_expanded_power_tools.py — Tests for Expanded Enterprise Power Tools & System Modules.
- test_links_manager(tmp_path) (L41): Test NTFS Links & Junctions manager capabilities.
- test_fast_copier(tmp_path) (L73): Test fast asynchronous chunked copier with SHA-256 validation.
- test_timestamp_touch(tmp_path) (L103): Test forensic MACB timestamp stomper and file attributes.
- test_archive_manager(tmp_path) (L127): Test archive creation, entry listing, testing, and extraction across ZIP and TAR.GZ.
- test_prefetch_analyzer() (L174): Test Prefetch & SysMain analyzer metrics.
- test_search_index_optimizer() (L185): Test Windows Search Index optimizer diagnostics.
- test_dns_benchmark() (L193): Test DNS query builder and latency benchmarking.
- test_disk_benchmark(tmp_path) (L209): Test disk benchmark throughput and IOPS measurement on sandbox directory.
- test_memory_optimizer() (L220): Test system RAM metrics and process memory inspection.
- test_dev_cleaner() (L234): Test developer ecosystem build artifact scanner.
- test_browser_deep_cleaner() (L244): Test multi-browser deep privacy and cache scanner.

## tests/test_external_exposure.py — No-network tests for explicit public-IP exposure lookups.
- test_lookup_requires_consent_and_global_public_ip() (L13): Construct ExternalExposureClient
- test_shodan_sends_only_selected_ip_and_normalizes_services() (L24): Construct ExternalExposureClient; assert services, product, to_dict
- test_shodan_sends_only_selected_ip_and_normalizes_services.transport(url, headers, timeout) (L28): Transport via append; return result
- test_censys_credentials_use_header_not_url() (L51): Construct ExternalExposureClient; assert version, services, startswith
- test_censys_credentials_use_header_not_url.transport(url, headers, _timeout) (L55): Transport via append; return result

## tests/test_feature_matrix_audit.py — Comprehensive Feature Matrix & Production-Grade Verification Suite.
- test_fm_core_and_power_features(qapp) (L34): Construct Path; assert count, tabbar, preview, _dual_pane, rowCount
- test_disk_and_storage_analyzers() (L77): Construct Path; assert hasattr(...)
- test_system_maintenance_and_repair() (L120): Construct ComponentStore; assert hasattr(...)
- test_security_and_sanitization_standards() (L166): Construct Path; assert exists
- test_privacy_and_telemetry() (L233): Construct TelemetryBlocker; assert hasattr(...)
- test_process_and_performance_optimization() (L256): Construct ProcessAnalyzer; assert MemoryOptimizer
- test_network_tools_and_defense() (L295): Construct NetworkMonitor; assert hasattr(...)
- test_apps_and_extension_management() (L349): Construct AppUninstaller; assert hasattr(...)
- test_registry_and_startup_tools() (L384): Construct RegistryCleaner; assert hasattr(...)
- test_specialized_dedup_and_cache_analyzers() (L409): Construct Path; assert get
- test_ui_page_registry_all_pages_loadable(qapp) (L522): Exercise processEvents; assert len(...)

## tests/test_firewall_manager.py — Tests for the Windows Firewall manager (validation, parsing, safety).
- TestGating.test_is_supported_matches_platform(self) (L19): Construct FirewallManager.is_supported; assert is_supported
- TestGating.test_list_returns_list(self) (L23): Construct FirewallManager; assert list_rules
- TestAddressValidation.test_valid_ipv4(self) (L30): Construct FirewallManager._valid_address; assert _valid_address
- TestAddressValidation.test_valid_cidr(self) (L34): Construct FirewallManager._valid_address; assert _valid_address
- TestAddressValidation.test_valid_range(self) (L38): Construct FirewallManager._valid_address; assert _valid_address
- TestAddressValidation.test_valid_ipv6(self) (L42): Construct FirewallManager._valid_address; assert _valid_address
- TestAddressValidation.test_invalid_rejected(self) (L46): Construct FirewallManager._valid_address; assert _valid_address
- TestAddressValidation.test_block_bad_address_refused(self) (L51): Construct FirewallManager; assert lower
- TestQuoting.test_escapes_single_quotes(self) (L60): Construct FirewallManager._ps_quote; assert startswith, endswith
- TestQuoting.test_simple_value(self) (L67): Construct FirewallManager._ps_quote; assert _ps_quote
- TestParsing.test_empty(self) (L74): Construct FirewallManager._parse_rules; assert _parse_rules
- TestParsing.test_single_rule(self) (L80): Construct FirewallManager._parse_rules; assert action, enabled, managed_by_cortex, remote_address
- TestParsing.test_non_cortex_rule_flagged_false(self) (L95): Construct FirewallManager._parse_rules; assert managed_by_cortex
- TestParsing.test_array(self) (L101): Construct FirewallManager._parse_rules; assert enabled
- TestDirectionGuard.test_bad_direction_rejected(self) (L114): Construct FirewallManager

## tests/test_free_space_wipe.py — Tests for the free-space wiper (validation + platform gating).
- TestGating.test_is_supported_matches_platform(self) (L19): Construct FreeSpaceWiper.is_supported; assert is_supported
- TestGating.test_non_windows_refuses(self) (L23): Construct FreeSpaceWiper; assert success
- TestValidation.test_rejects_bad_letter(self) (L35): Construct FreeSpaceWiper; assert success, lower, message
- TestValidation.test_rejects_empty(self) (L44): Construct FreeSpaceWiper; assert success, wipe
- TestMediumHonesty.test_medium_for_reports_effectiveness(self, monkeypatch) (L54): Construct StorageInfo; assert value, SSD, overwrite_effective

## tests/test_fuzzy_finder.py — Tests for CTPH fuzzy (similarity) hashing.
- _text(n=4000) (L17): text via encode; return result
- _noise(n=4000, seed=7) (L23): noise via Random, bytes, getrandbits; return result
- test_fuzzy_hash_is_deterministic() (L33): Exercise _text; assert fuzzy_hash_bytes(...)
- test_identical_content_matches_at_100() (L39): Exercise _text; assert fuzzy_compare, fuzzy_hash_bytes(...)
- test_similar_content_scores_high_pairs() (L45): Exercise _text
- test_unrelated_content_scores_low() (L56): Exercise _text
- test_empty_signature() (L64): Exercise fuzzy_compare; assert fuzzy_compare(...)
- test_finder_groups_near_identical_binaries(tmp_path) (L71): Construct FuzzyDuplicateFinder
- test_finder_skips_incompressible_and_small(tmp_path) (L87): Construct FuzzyDuplicateFinder; assert find_fuzzy_duplicates
- test_finder_stats(tmp_path) (L95): Construct FuzzyDuplicateFinder
- test_fuzzy_hash_file_reads(tmp_path) (L107): Exercise write_bytes

## tests/test_game_mode_memory.py — Tests for Gaming Mode and the memory optimizer.
- TestGameModeLogic.test_protected_never_in_candidates(self) (L31): Exercise set; assert set(...)
- TestGameModeLogic.test_boost_report_serializes(self) (L37): Construct BoostReport
- TestGameModeLogic.test_unsupported_reports_cleanly(self, monkeypatch) (L46): Construct GameMode; assert ok, message
- TestGameModeLogic.test_stop_without_start_is_safe(self) (L58): Construct GameMode; assert ok, phase
- TestGameModeWindows.test_preview_is_read_only(self) (L71): Construct GameMode
- TestGameModeWindows.test_dry_run_changes_nothing(self) (L77): Construct GameMode; assert ok, _suspended_pids, _boosted_plan_guid
- TestGameModeWindows.test_pick_prefers_high_performance(self, tmp_path_factory) (L88): Construct GameMode; assert name
- TestGameModeWindows.test_candidates_exclude_protected_and_self(self) (L102): Construct GameMode; assert isdisjoint
- TestMemoryOptimizer.test_stats_shape(self) (L114): Construct MemoryOptimizer; assert total_bytes, percent_used
- TestMemoryOptimizer.test_optimize_returns_result(self) (L123): Construct MemoryOptimizer; assert processes_trimmed, bytes_freed_estimate, errors
- TestMemoryOptimizer.test_optimize_off_platform_no_crash(self) (L132): Construct MemoryOptimizer; assert isinstance(...)

## tests/test_gui_device_window.py — Offscreen tests for the per-device deep scan window (no live network).
- app() (L30): App: build QApplication.instance, via fixture; return result
- window(app) (L36): Window: build PremiumMainWindow, via apply_theme
- _observation(port=443, name='https', **kwargs) (L48): observation: build ServiceObservation, via pop; return result
- _device(**kwargs) (L59): device: build Device, via _observation; return result
- test_window_renders_discovery_evidence_before_any_scan(window) (L75): Exercise DeviceDetailWindow; assert windowTitle, text, _value, card_ports, card_findings
- test_window_renders_completed_scan_payload_with_severity_badge(window) (L92): Construct SecurityFinding; assert text, _value, card_findings, card_risk, card_latency
- test_worker_refuses_target_outside_authorized_scope(monkeypatch) (L159): Construct AssertionError; expect exception
- test_worker_refuses_target_outside_authorized_scope.fail_scan(*_args, **_kwargs) (L161): Fail scan: build/parse AssertionError
- test_worker_collects_services_findings_and_history(monkeypatch) (L177): Exercise setattr; assert all(...)
- test_worker_reports_missing_nmap_without_failing(monkeypatch) (L218): Exercise setattr; assert any(...)
- test_worker_does_not_claim_port_source_without_observation(monkeypatch) (L252): Exercise setattr
- test_ping_worker_is_scope_checked_and_does_not_scan_ports(monkeypatch) (L295): Construct AssertionError; expect exception
- test_ping_worker_is_scope_checked_and_does_not_scan_ports.fail_scan(*_args, **_kwargs) (L302): Fail scan: build/parse AssertionError
- test_failed_scan_restores_capability_based_actions(window, monkeypatch) (L332): Exercise _device; assert isEnabled, scan_btn, ping_btn, wake_btn, open_btn
- test_lan_page_opens_retains_and_safely_closes_device_window(app, window, monkeypatch) (L354): Construct FakeWorker; assert isEnabled, device_btn, _device_windows, cancelled, isVisible
- test_lan_page_opens_retains_and_safely_closes_device_window.FakeWorker.__init__(self) (L364): Initialize cancelled
- test_lan_page_opens_retains_and_safely_closes_device_window.FakeWorker.cancel(self) (L368): Cancel: 'cancel.'
- test_lan_page_opens_retains_and_safely_closes_device_window.fake_start_scan(detail_window, profile='advanced') (L374): Fake start scan: build FakeWorker, via _busy

## tests/test_gui_pages_e2e.py — End-to-end, page-by-page GUI tests for the premium interface.
- app() (L31): App: build QApplication.instance, via fixture; return result
- window(app) (L37): Window: build PremiumMainWindow, via apply_theme, show
- pro_license(monkeypatch, tmp_path) (L49): Grant PRO entitlement so gated handlers run headlessly.
- pump_until(app, predicate, timeout_ms=45000, interval=25) -> bool (L68): Spin the event loop until predicate() is true or timeout. Returns final.
- data_tree(tmp_path) (L84): Folder with duplicates, a >50MB file, and empty items for scan pages.
- test_page_dashboard_scan(app, window) (L100): Exercise _scan; assert _scanning, _report, text, scan_btn, topLevelItemCount
- _drive_folder_page(app, window, page_id, data_tree) (L115): drive folder page via _select, setEnabled, _run; return result
- test_page_duplicates(app, window, data_tree) (L126): Exercise _drive_folder_page; assert any(...)
- test_page_large_files(app, window, data_tree) (L133): Exercise _drive_folder_page; assert rowCount, tbl, text, item
- test_page_empty_items(app, window, data_tree) (L140): Exercise _drive_folder_page; assert any(...)
- test_page_privacy_scan(app, window) (L152): Exercise _select; assert mode, state, isEnabled, scan_btn, isVisible
- test_page_startup_list(app, window) (L170): Exercise _select; assert isEnabled, refresh_btn, isVisible, progress, rowCount
- test_page_traffic_monitor(app, window) (L183): Exercise _select; assert _down, graph, text, _value, card_down
- test_page_windows_update(app, window) (L196): Exercise skipif; assert text, rowCount, _value, hist_tbl, card_check
- test_page_health_check(app, window) (L207): Exercise _select; assert isEnabled, run_btn, isVisible, progress, text
- test_page_security_status(app, window) (L219): Exercise skipif; assert isEnabled, refresh_btn, isVisible, progress, text
- test_page_storage_sense(app, window) (L229): Exercise skipif; assert _loading, text, enable_chk
- test_page_boot_performance(app, window) (L240): Exercise skipif; assert isEnabled, refresh_btn, isVisible, progress, text
- test_page_system_repair_constructs(app, window) (L251): Exercise skipif; assert hasattr(...)
- test_page_load_tester_authorization(app, window) (L260): Exercise _select; assert isEnabled, run_btn, _auth, text, auth_label
- test_load_tester_refuses_public_in_ui(app, window) (L273): A public target must NOT enable the run button (safety gate in the UI).
- test_page_network_tools(app, window) (L288): Exercise _select; assert text, summary, lower
- test_page_network_map(app, window) (L303): Exercise _select; assert isEnabled, refresh_btn, text, summary
- test_page_lan_devices(app, window, monkeypatch) (L313): Construct DiscoveryResult; assert isEnabled, refresh_btn, isVisible, progress, columnCount
- test_page_firewall_list(app, window) (L339): Construct FirewallManager._valid_address; assert isEnabled, refresh_btn, isVisible, progress, _valid_address
- test_page_network_monitor(app, window) (L350): Exercise _select; assert isEnabled, refresh_btn, text, _value, card_listen
- test_page_processes_list(app, window) (L364): Exercise _select; assert isEnabled, _procs, refresh_btn, visible_count, table
- test_page_uninstaller_list(app, window) (L422): Exercise skipif; assert isEnabled, refresh_btn, isVisible, progress, visible_count
- test_page_telemetry_status(app, window) (L433): Exercise skipif; assert topLevelItemCount, tree, lower, text, status_lbl
- test_page_registry_scan(app, window, pro_license) (L442): Exercise skipif; assert isEnabled, scan_btn, isVisible, progress, visible_count
- test_page_software_updater_list(app, window) (L458): Construct AppUpdater.is_available; assert isEnabled, refresh_btn, isVisible, progress, rowCount
- test_page_drive_optimizer_list(app, window) (L472): Exercise skipif; assert isEnabled, refresh_btn, isVisible, progress, rowCount
- _drive_action_text(drive: dict) -> str (L484): drive action text via _drive_action; return result
- test_page_virtual_disks(app, window) (L491): Discovery is read-only, so it runs here; compaction is worker-tested.
- test_page_component_store_construct(app, window) (L513): Analysis runs real DISM (minutes); just verify the page builds and the
- test_page_system_info_load(app, window) (L536): Exercise _select; assert text, info_label
- test_page_package_caches_load(app, window) (L545): Exercise _select; assert isEnabled, refresh_btn
- test_dashboard_smart_learning_loop(app, window, tmp_path) (L555): Selecting/deselecting categories must feed the offline learner and it
- test_page_broken_links_and_dupfolders_construct(app, window) (L588): Exercise _select; assert isEnabled, run_btn
- test_page_shred_storage_detection(app, window, tmp_path) (L602): Construct StorageWorker; assert pump_until(...)
- test_page_settings_theme_toggle(app, window) (L623): Exercise _select; assert theme_name
- test_page_settings_restore_point_list(app, window) (L634): The safety card must list restore points (read-only) without hanging.
- test_restore_point_worker_reports_honest_status(app) (L644): The create worker must return one of the honest status strings, and must
- test_page_lan_devices_renders_synthetic_advanced_audit(window) (L663): Exercise the premium audit UI without touching the live network.
- test_page_lan_devices_renders_synthetic_advanced_audit.cell(row, col) (L697): Cell via data, index; return result
- test_page_winapp2_e2e(app, window) (L720): Exercise _start_scan; assert stat_apps, isVisible, progress_bar
- test_page_srum_bam_e2e(app, window) (L729): Exercise _start_scan; assert stat_bam_records, isVisible, progress_bar
- test_page_directstorage_e2e(app, window) (L738): Exercise _start_audit; assert stat_status, isVisible, progress_bar
- test_page_standby_purger_e2e(app, window) (L747): Exercise _refresh_stats; assert stat_phys_total, value
- test_page_mft_slack_e2e(app, window) (L756): Exercise _start_audit; assert stat_total_records, isVisible, progress_bar
- test_page_search_optimizer_e2e(app, window) (L765): Exercise _start_status_query; assert stat_size, isVisible, progress_bar
- test_page_disk_analyzer_e2e(app, window, tmp_path) (L774): Exercise mkdir; assert _worker, rowCount, _tbl

## tests/test_health_check.py — Tests for the one-click health check (scoring logic + resilient run).
- _c(sev) (L16): c: build/parse HealthCheck; return result
- TestScoring.test_all_good_is_a(self) (L23): Construct HealthChecker._score
- TestScoring.test_info_does_not_deduct(self) (L28): Construct HealthChecker._score
- TestScoring.test_one_warning(self) (L33): Construct HealthChecker._score
- TestScoring.test_one_critical(self) (L38): Construct HealthChecker._score
- TestScoring.test_multiple_criticals_floor_at_zero(self) (L43): Construct HealthChecker._score
- TestScoring.test_grade_boundaries(self) (L48): Construct HealthChecker._score; assert _score
- TestRun.test_run_returns_report(self) (L59): Construct HealthChecker; assert score, grade
- TestRun.test_progress_called(self) (L70): Construct HealthChecker; assert len(...)
- TestRun.test_checks_have_valid_severity(self) (L76): Construct HealthChecker; assert severity
- TestRun.test_to_dict(self) (L82): Construct HealthChecker; assert set, isinstance(...)
- TestDiskSpaceCheck.test_disk_space_check_runs(self) (L92): Construct HealthChecker._check_disk_space; assert id, severity, action_page

## tests/test_icons.py — Contracts for the SVG icon system.
- app() (L29): App: build QApplication.instance, via fixture; return result
- test_every_page_has_its_own_icon_asset() (L36): Exercise has_icon
- test_no_two_pages_share_an_icon() (L42): Regression: five glyphs were previously reused across tools.
- test_registry_icons_are_asset_names_not_glyphs() (L49): An icon field must never contain a raw symbol codepoint again.
- test_window_chrome_and_status_icons_are_shipped() (L57): Exercise has_icon; assert has_icon
- test_every_shipped_icon_renders(app) (L66): Exercise sorted
- test_rasterises_at_device_resolution(app, dpr_x100, expected) (L75): Physical pixels must scale with DPI while logical size stays fixed.
- test_icons_are_tinted_to_the_requested_colour(app) (L89): Exercise toImage
- test_icon_exposes_a_larger_variant_so_qt_never_upscales(app) (L102): Exercise availableSizes; assert width
- test_missing_icon_degrades_to_empty_without_raising(app) (L111): A missing decoration must never stop a tool from opening.
- test_clear_cache_allows_retinting(app) (L117): Exercise pixmap; assert isNull, toImage
- test_navigation_uses_real_icons_and_clean_labels(app) (L128): Construct PremiumMainWindow; assert PAGES, title, strip, BY_ID, text
- test_theme_switch_retints_navigation_icons(app) (L147): Construct PremiumMainWindow; assert isNull, values, _nav_buttons_by_page, icon
- test_title_bar_controls_have_icons_and_accessible_names(app) (L165): Construct PremiumMainWindow; assert isNull, pixmap, _brand, icon, text
- test_no_symbol_glyphs_remain_in_the_premium_ui() (L185): Guard: icons must be assets, never Unicode codepoints.
- test_status_note_pairs_an_icon_with_accessible_text(app) (L227): Exercise status_note; assert accessibleName

## tests/test_lan_scanner.py — Tests for the ARP-based LAN device scanner (parsing + vendor lookup).
- TestParse.test_empty(self) (L27): Construct LanScanner._parse; assert _parse
- TestParse.test_windows_parse_and_filter(self) (L32): Construct LanScanner._parse
- TestParse.test_vendor_comes_from_the_ieee_registry(self) (L41): Vendor names must be authoritative, never hand-maintained guesses.
- TestParse.test_sorted_by_ip(self) (L63): Construct LanScanner._parse; assert sorted(...)
- TestParse.test_dedupes(self) (L69): Construct LanScanner._parse; assert count, ip
- TestParse.test_type_captured(self) (L75): Construct LanScanner._parse; assert kind
- TestVendorHelper.test_normalizes_dashes(self) (L83): Dash-separated input must resolve identically to colon-separated.
- TestVendorHelper.test_unassigned_prefix_is_empty_not_a_guess(self) (L88): Construct LanScanner._vendor_for; assert _vendor_for
- TestVendorHelper.test_garbage_input(self) (L93): Construct LanScanner._vendor_for; assert _vendor_for
- TestScan.test_scan_returns_list(self) (L101): Construct LanScanner; assert isinstance, all(...)
- TestScan.test_to_dict(self) (L107): Construct LanDevice; assert to_dict

## tests/test_lazy_pages.py — Contracts for on-demand page construction in the premium shell.
- app() (L27): App: build QApplication.instance, via fixture; return result
- window(app) (L33): Window: build PremiumMainWindow, via apply_theme
- test_only_the_initial_page_is_built_at_startup(window) (L43): Startup must construct the landing page and nothing else.
- test_registry_reports_every_page_without_building_them(window) (L50): ``len``/iteration/``in`` must describe all pages, not just built ones.
- test_getitem_builds_on_demand_and_caches(window) (L66): Indexing behaves like a dict and returns a stable widget instance.
- test_selecting_a_page_builds_it_and_shows_it(window) (L76): Navigation must build the target page and make it current.
- test_navigation_works_for_every_page(window) (L84): Every page must build and become current when selected.
- test_unknown_page_id_raises_key_error(window) (L93): A typo must fail loudly rather than silently build nothing.
- test_selecting_unknown_page_is_ignored(window) (L99): ``_select`` guards on the nav registry and must not raise.
- test_page_factory_registry_matches_navigation() (L106): A page in navigation without a factory would fail only on click.
- test_lazily_built_page_is_added_to_the_stack(window) (L114): A page must be parented into the stack, or it would never display.

## tests/test_leftover_cleaner.py — Tests for the production leftover cleaner (post-uninstall residuals).
- TestEditDistance.test_identical_strings_cost_zero(self) (L41): Exercise edit_distance; assert edit_distance(...)
- TestEditDistance.test_empty_inputs(self) (L45): Exercise edit_distance; assert edit_distance(...)
- TestEditDistance.test_known_distances(self, a, b, expected) (L58): Exercise parametrize; assert edit_distance(...)
- TestEditDistance.test_early_exit_exceeds_bound(self) (L62): Exercise edit_distance; assert edit_distance(...)
- TestMatchStringToProduct.test_perfect_match(self) (L69): Exercise match_string_to_product; assert match_string_to_product(...)
- TestMatchStringToProduct.test_near_match_off_by_one(self) (L73): Exercise match_string_to_product; assert match_string_to_product(...)
- TestMatchStringToProduct.test_substring_containment(self) (L77): Exercise match_string_to_product; assert match_string_to_product(...)
- TestMatchStringToProduct.test_short_names_never_match(self) (L81): Exercise match_string_to_product; assert match_string_to_product(...)
- TestMatchStringToProduct.test_unrelated_names_rejected(self) (L87): Exercise match_string_to_product; assert match_string_to_product(...)
- TestMatchStringToProduct.test_distance_beyond_one_third_cutoff(self) (L91): Exercise match_string_to_product; assert match_string_to_product(...)
- TestBuildTokens.test_noise_suffixes_removed(self) (L98): Exercise build_tokens; assert any(...)
- TestBuildTokens.test_generic_publishers_excluded(self) (L104): Exercise build_tokens
- TestBuildTokens.test_specific_publisher_included(self) (L110): Exercise build_tokens
- TestBuildTokens.test_short_tokens_dropped(self) (L115): Exercise build_tokens
- TestConfidenceLevels.test_mapping(self) (L126): Exercise confidence_level; assert confidence_level(...)
- test_detect_installer_type() (L137): Exercise detect_installer_type; assert detect_installer_type(...)
- TestSafetyPolicy.test_known_folder_roots_are_prohibited_but_children_allowed(self, monkeypatch, tmp_path) (L152): Construct SafetyPolicy.build; assert is_prohibited
- TestSafetyPolicy.test_own_paths_protected(self, tmp_path) (L162): Construct SafetyPolicy; assert is_prohibited
- fake_env(monkeypatch, tmp_path) (L175): Redirect every sweep root into a throwaway directory tree.
- _scanner(apps=()) (L194): scanner: build LeftoverScanner, via list; return result
- TestFilesystemSweep.test_empty_leftover_folder_scores_very_good(self, fake_env) (L201): Construct InstalledApp; assert lower, level, reasons
- TestFilesystemSweep.test_blacklisted_directory_never_flagged(self, fake_env) (L216): Construct InstalledApp; assert lower, kind, name, path
- TestFilesystemSweep.test_executables_present_penalized(self, fake_env) (L225): Construct InstalledApp; assert reasons, score
- TestFilesystemSweep.test_product_still_installed_penalized(self, fake_env) (L239): Construct InstalledApp; assert reasons, level
- TestFilesystemSweep.test_live_sibling_app_claiming_name_penalized(self, fake_env) (L254): Construct InstalledApp; assert reasons
- TestFilesystemSweep.test_nested_cache_inside_matched_vendor_found(self, fake_env) (L267): Construct InstalledApp
- TestFilesystemSweep.test_reparse_point_not_descended(self, fake_env) (L277): Construct InstalledApp; assert isinstance(...)
- TestFilesystemSweep.test_orphan_scan_reports_empty_unclaimed_folder(self, fake_env) (L301): Construct InstalledApp
- FakeRegKey.__init__(self, subkeys=None, values=None) (L321): Initialize _subkeys, _values
- FakeRegKey.children(self) (L326): Children: 'children.'; return result
- fake_registry(monkeypatch) (L332): Install a fake winreg module driving LeftoverScanner's registry walk.
- fake_registry.FakeWinreg.OpenKey(key, path, reserved=0, access=0) (L358): OpenKey: build OSError, via children; return result
- fake_registry.FakeWinreg.QueryInfoKey(key) (L371): QueryInfoKey via children; return result
- fake_registry.FakeWinreg.EnumKey(key, index) (L376): EnumKey: build OSError, via children; return result
- fake_registry.FakeWinreg.CloseKey(key) (L384): CloseKey: 'CloseKey.'
- fake_registry.FakeWinreg.EnumValue(key, index) (L389): EnumValue: build OSError, via list, items; return result
- TestRegistrySweep.test_matching_software_key_found_with_explicit_pointer(self, fake_env, fake_registry) (L405): Construct InstalledApp; assert endswith, path, reasons, level
- TestRegistrySweep.test_walk_skips_blacklisted_branches(self, fake_env, fake_registry) (L417): Construct InstalledApp; assert endswith, kind, path
- TestCleaner.test_recycle_via_send2trash_and_journal(self, fake_env, tmp_path, monkeypatch) (L431): Construct LeftoverCleaner; assert ok, disposition
- TestCleaner.test_recycle_via_send2trash_and_journal.fake_send2trash(path) (L438): Fake send2trash via append
- TestCleaner.test_recycle_failure_surfaced_not_hidden(self, fake_env, tmp_path, monkeypatch) (L455): Construct LeftoverCleaner; assert ok, detail
- TestCleaner.test_recycle_failure_surfaced_not_hidden.boom(_path) (L461): Boom: build/parse PermissionError
- TestCleaner.test_registry_clean_exports_backup_then_deletes(self, tmp_path, monkeypatch) (L472): Construct LeftoverCleaner; assert ok, disposition
- TestCleaner.test_registry_clean_exports_backup_then_deletes.fake_run(cmd, **_kwargs) (L477): Fake run: build R, via write_text; return result
- TestCleaner.test_protected_paths_are_skipped(self, tmp_path) (L501): Construct SafetyPolicy.build; assert disposition
- TestCleaner.test_empty_clean_writes_no_journal(self, tmp_path) (L509): Construct LeftoverCleaner; assert clean, exists
- TestComSweep.test_clsid_pointing_into_dead_install_is_flagged(self, fake_env, monkeypatch) (L522): A CLSID whose InprocServer32 lives in the dead install location
- TestComSweep.test_clsid_pointing_into_dead_install_is_flagged.clsid_key(server_path) (L533): Clsid key: build FakeRegKey, via str; return result
- TestComSweep.test_clsid_pointing_into_dead_install_is_flagged.ComWinreg.OpenKey(key, path, reserved=0, access=0) (L560): OpenKey: build OSError, via children; return result
- TestComSweep.test_clsid_pointing_into_dead_install_is_flagged.ComWinreg.QueryInfoKey(key) (L576): QueryInfoKey via children; return result
- TestComSweep.test_clsid_pointing_into_dead_install_is_flagged.ComWinreg.EnumKey(key, index) (L581): EnumKey: build OSError, via children; return result
- TestComSweep.test_clsid_pointing_into_dead_install_is_flagged.ComWinreg.CloseKey(key) (L589): CloseKey: 'CloseKey.'
- TestComSweep.test_clsid_pointing_into_dead_install_is_flagged.ComWinreg.QueryValueEx(key, name) (L594): QueryValueEx: build/parse OSError; return result
- TestInnoLog.test_paths_from_unins000_dat_that_still_exist_are_flagged(self, fake_env) (L620): Construct InstalledApp; assert reasons
- TestServiceAndTaskClean.test_service_clean_backs_up_then_sc_deletes(self, tmp_path, monkeypatch) (L651): Construct LeftoverCleaner; assert ok, disposition
- TestServiceAndTaskClean.test_service_clean_backs_up_then_sc_deletes.fake_run(cmd, **_kw) (L656): Fake run: build R, via write_text; return result
- TestServiceAndTaskClean.test_task_clean_backs_up_xml_then_schtasks_deletes(self, fake_env, tmp_path, monkeypatch) (L681): Construct LeftoverCleaner; assert ok, disposition
- TestServiceAndTaskClean.test_task_clean_backs_up_xml_then_schtasks_deletes.fake_run(cmd, **_kw) (L694): Fake run: build R, via append, list; return result
- TestServiceAndTaskClean.test_task_sweep_finds_command_in_dead_install(self, fake_env, monkeypatch) (L715): Construct InstalledApp; assert path
- TestTokenStopwords.test_generic_words_never_become_tokens(self) (L736): Exercise build_tokens
- TestTokenStopwords.test_product_identity_survives(self) (L742): Exercise build_tokens
- TestInventory.test_read_installed_apps_runs_without_error(self) (L753): Exercise read_installed_apps; assert name, installer_type
- TestInventory.test_find_residual_keys_api_exists(self) (L765): Construct InstalledApp; assert find_residual_uninstall_keys

## tests/test_license_gui.py — Headless tests for the license GUI: LicensePage + require_feature gating.
- app() (L22): App: build QApplication.instance, via fixture
- isolated_license(monkeypatch, tmp_path) (L29): Point the process-wide manager at a temp-path LicenseManager.
- window(app, isolated_license) (L41): Window: build PremiumMainWindow, via apply_theme, resize
- _click_trial_buttons(monkeypatch) (L58): Route every dialog through 'the user clicked Start Free Trial'.
- test_license_page_shows_free_when_unlicensed(window) (L76): Exercise isEnabled; assert text, tier_label, key_label, lower, status_label
- test_activate_with_empty_key_warns_and_stays_free(window, monkeypatch) (L95): Exercise setattr; assert text, tier_label
- test_page_shows_pro_after_activation_and_refresh(window, isolated_license) (L108): Exercise activate; assert text, tier_label, lower, status_label, startswith
- test_require_feature_allows_licensed_feature(window, isolated_license) (L137): Exercise activate; assert SENTINEL_PRO
- test_require_feature_denied_offers_trial_then_refuses_second_time(window, isolated_license, monkeypatch) (L146): Denied -> dialog offers the trial; starting it unlocks PRO; afterwards
- test_require_feature_reports_refused_trial(window, isolated_license, monkeypatch) (L166): If start_trial refuses anyway (raced/exhausted), the user sees an
- test_require_feature_reports_refused_trial.refused() (L177): Refused: build/parse RuntimeError
- test_registry_declares_the_license_page() (L191): Mirrors test_page_registry.py: one declaration wires everything.
- test_window_nav_reaches_the_license_page(window) (L204): Exercise _select; assert get, _nav_sections_by_page, currentWidget, _pages, _stack

## tests/test_licensing.py — Tests for the offline licensing / entitlement system.
- manager(tmp_path: Path) -> LicenseManager (L38): LicenseManager isolated to a temp file (real license untouched).
- TestFingerprint.test_stable_across_calls(self) (L48): Exercise compute_fingerprint; assert compute_fingerprint(...)
- TestFingerprint.test_memoised_matches_direct(self) (L52): Exercise get_fingerprint; assert get_fingerprint, compute_fingerprint(...)
- TestFingerprint.test_shape(self) (L56): Exercise get_fingerprint; assert len(...)
- TestFingerprint.test_identifiers_never_empty(self) (L62): Exercise collect_identifiers; assert collect_identifiers
- TestTiers.test_rank_ordering(self) (L74): Exercise sorted; assert sorted(...)
- TestTiers.test_includes_is_cumulative(self) (L80): Construct Tier.ENTERPRISE.includes; assert includes, FREE, ENTERPRISE, PREMIUM, PRO
- TestTiers.test_parse_defaults_to_free_on_garbage(self) (L86): Construct Tier.parse; assert PRO, parse, FREE
- TestTiers.test_feature_matrix_cumulative(self) (L92): Exercise features_for_tier; assert ENGINE_CLEAN, GAMING_MODE
- TestLicenseLifecycle.test_fresh_machine_is_free(self, manager: LicenseManager) (L109): Exercise validate; assert tier, FREE, licensed, trial
- TestLicenseLifecycle.test_activate_and_validate(self, manager: LicenseManager) (L116): Exercise activate; assert tier, PRO, licensed, key, SENTINEL_PRO
- TestLicenseLifecycle.test_key_masked_in_status(self, manager: LicenseManager) (L124): Exercise activate
- TestLicenseLifecycle.test_signature_tamper_rejected(self, manager: LicenseManager) (L130): Exercise activate; assert tier, FREE, reason
- TestLicenseLifecycle.test_payload_tamper_rejected(self, manager: LicenseManager) (L140): Exercise activate; assert tier, FREE, validate
- TestLicenseLifecycle.test_corrupt_file_degrades_to_free(self, manager: LicenseManager) (L148): Exercise activate; assert tier, FREE, reason
- TestLicenseLifecycle.test_wrong_machine_rejected(self, manager: LicenseManager) (L156): Exercise activate; assert tier, FREE, reason
- TestLicenseLifecycle.test_expiry_freezes_after_grace(self, tmp_path: Path) (L170): Construct LicenseManager; assert licensed, tier, FREE, reason
- TestLicenseLifecycle.test_grace_period_keeps_access(self, tmp_path: Path) (L196): Construct LicenseManager; assert grace_active, licensed, SENTINEL_PRO, features
- TestLicenseLifecycle.test_trial_once_only(self, manager: LicenseManager) (L218): Exercise start_trial; assert trial, tier, PRO
- TestLicenseLifecycle.test_trial_refused_when_licensed(self, manager: LicenseManager) (L225): Exercise activate
- TestLicenseLifecycle.test_deactivate_returns_to_free(self, manager: LicenseManager) (L231): Exercise activate; assert tier, FREE, exists, _path
- TestLicenseLifecycle.test_activate_rejects_bad_input(self, manager: LicenseManager) (L239): Exercise raises
- TestLicenseLifecycle.test_singleton_resettable(self) (L246): Exercise get_license_manager
- TestGating._licensed_pro(self, monkeypatch, tmp_path) (L265): Point the singleton at a temp PRO license for every test here.
- TestGating.test_current_tier_and_features(self) (L275): Exercise effective_features; assert PRO, SENTINEL_PRO, POLICY_FILES
- TestGating.test_allowed_and_require(self) (L282): Exercise allowed; assert SENTINEL_PRO
- TestGating.test_entitlement_error_details(self) (L292): Exercise __import__; assert required, ENTERPRISE, value, current, PRO
- TestGating.test_gate_decorator_blocks_and_passes(self) (L302): Exercise gate; assert pro_tool(...)
- TestGating.test_gate_decorator_blocks_and_passes.pro_tool() (L305): Pro tool via gate; return result
- TestGating.test_gate_decorator_blocks_and_passes.enterprise_tool() (L310): Enterprise tool via gate; return result

## tests/test_load_tester.py — Tests for the authorized load/resilience tester.
- TestAuthorization.test_loopback_authorized(self) (L32): Construct TargetAuthorizer; assert authorized, category
- TestAuthorization.test_localhost_authorized(self) (L38): Construct TargetAuthorizer; assert authorized
- TestAuthorization.test_private_lan_authorized(self) (L43): Construct TargetAuthorizer; assert authorized, authorize
- TestAuthorization.test_public_denied_without_token(self) (L49): Construct TargetAuthorizer; assert authorized, category, lower, reason
- TestAuthorization.test_public_denied_with_unverifiable_token(self) (L56): Construct TargetAuthorizer; assert authorized
- TestAuthorization.test_unresolvable_denied(self) (L64): Construct TargetAuthorizer; assert authorized
- TestAuthorization.test_classify_loopback(self) (L69): Construct TargetAuthorizer.classify
- TestAuthorization.test_token_generation_unique(self) (L74): Construct TargetAuthorizer.new_token; assert startswith
- TestRefusesUnauthorized.test_run_http_refuses_unauthorized(self) (L82): Construct Authorization
- TestRefusesUnauthorized.test_run_tcp_refuses_unauthorized(self) (L88): Construct Authorization
- TestMetrics.test_percentiles(self) (L101): Construct LoadResult; assert percentile
- TestMetrics.test_rps_and_error_rate(self) (L109): Construct LoadResult; assert rps, error_rate
- TestMetrics.test_empty_latencies_safe(self) (L116): Construct LoadResult; assert percentile, rps, error_rate
- TestMetrics.test_summary_keys(self) (L123): Construct LoadResult; assert set(...)
- TestLocalRun.test_http_against_local_server(self) (L139): Construct HttpLoadConfig; assert authorized, total, succeeded, rps, error_rate
- TestLocalRun.test_http_against_local_server.Quiet.log_message(self, *a) (L146): Log message: 'log_message.'
- TestLocalRun.test_http_against_local_server.Quiet.do_GET(self) (L150): Do GET via send_response, send_header, end_headers
- TestLocalRun.test_cancel_stops_run(self) (L176): Construct HttpLoadConfig; assert monotonic

## tests/test_memory_standby_purger.py — Unit tests for Windows MemoryStandbyPurger NTDLL engine.
- test_memory_snapshot() (L13): Construct MemoryStandbyPurger; assert total_phys_bytes, memory_load_percent
- test_privilege_enable() (L26): Construct MemoryStandbyPurger; assert isinstance(...)
- test_purge_actions_safe() (L35): Construct MemoryStandbyPurger; assert action

## tests/test_mft_slack_scrubber.py — Unit tests for NTFS MFT & Directory Index slack scrubber.
- test_parse_ntfsinfo() (L12): Construct MftSlackScrubber.parse_ntfsinfo_output; assert volume_letter, bytes_per_sector, bytes_per_cluster, bytes_per_file_record_segment, mft_valid_data_length
- test_audit_structure() (L36): Construct MftSlackScrubber; assert isinstance(...)
- test_scrub_structure() (L46): Construct MftSlackScrubber; assert isinstance(...)

## tests/test_network_audit.py — Focused synthetic tests for the private-LAN audit foundation.
- observation(port=22, name='ssh', **kwargs) (L43): Observation: build ServiceObservation, via pop; return result
- test_scope_rejects_public_special_and_out_of_scope_without_sockets(monkeypatch) (L57): Construct NetworkServiceScanner; assert ADVANCED, start, stop
- test_private_scope_spec_supports_host_cidr_and_range() (L80): Exercise parse_network_scope_spec
- test_custom_port_spec_is_bounded_and_deterministic() (L93): Exercise parse_custom_port_spec; assert parse_custom_port_spec(...)
- test_custom_ports_are_validated_before_any_socket(monkeypatch) (L102): Construct NetworkServiceScanner
- test_observation_serialization_is_json_safe_and_deterministic() (L118): Exercise observation
- test_ports_and_banners_never_create_cve_claims() (L135): Construct SyntheticDevice; assert cve_ids
- test_catalog_exact_product_version_and_no_version_false_positive(tmp_path) (L150): Construct VulnerabilityCatalog.load; assert advisory_id, match, cve_ids, device_ip, join
- test_fingerprint_combines_device_and_protocol_evidence() (L187): Construct SyntheticDevice; assert os_family, device_type, confidence, evidence, product
- test_wan_classification(address, expected) (L219): Exercise parametrize; assert classify_external_ip(...)
- test_wan_url_scope_and_route_only_default(monkeypatch) (L224): Construct WanAuditor; assert gateway, igd_found, to_dict
- test_inventory_reports_new_address_service_and_gateway_changes(tmp_path) (L247): Construct NetworkInventory; assert new_devices, changed_addresses, previous, new_services, gateway_mac_changes

## tests/test_network_automation.py — Offline tests for fixed-command recurring network scans.
- test_schedule_builds_only_fixed_private_scan_command(monkeypatch) (L12): Exercise setattr; assert list2cmdline
- test_schedule_rejects_public_scope_and_arbitrary_frequency() (L35): Exercise raises
- test_scheduler_uses_process_runner_without_shell(monkeypatch) (L45): Exercise setattr; assert isinstance(...)
- test_scheduler_uses_process_runner_without_shell.fake_run(arguments, **kwargs) (L50): Fake run via CompletedProcess; return result

## tests/test_network_discovery.py — Deep LAN discovery: parsing, filtering and honest identification.
- TestUsableHost.test_zero_mac_is_absence_not_presence(self) (L37): An all-zero MAC means the ARP probe got no reply.
- TestUsableHost.test_broadcast_mac_rejected(self) (L41): Construct NetworkDiscovery._usable_host; assert _usable_host
- TestUsableHost.test_multicast_mac_rejected(self) (L45): Construct NetworkDiscovery._usable_host; assert _usable_host
- TestUsableHost.test_broadcast_ip_rejected(self) (L49): Construct NetworkDiscovery._usable_host; assert _usable_host
- TestUsableHost.test_multicast_ip_rejected(self) (L53): Construct NetworkDiscovery._usable_host; assert _usable_host
- TestUsableHost.test_real_device_accepted(self) (L57): Construct NetworkDiscovery._usable_host; assert _usable_host
- TestUsableHost.test_missing_mac_rejected(self) (L61): Construct NetworkDiscovery._usable_host; assert _usable_host
- TestUsableHost.test_garbage_ip_rejected(self) (L65): Construct NetworkDiscovery._usable_host; assert _usable_host
- test_windows_neighbor_query_excludes_incomplete_states() (L70): The PowerShell filter itself must exclude the phantom states.
- TestMacIdentity.test_real_assignments_resolve_from_the_registry(self) (L102): Exercise skipif; assert lower, lookup
- TestMacIdentity.test_lookup_never_invents_a_vendor(self) (L109): Unassigned/locally-administered addresses must return empty.
- TestMacIdentity.test_longer_assignments_win_over_the_containing_block(self) (L115): MA-S/MA-M blocks are more specific than the 24-bit OUI they sit in.
- TestMacIdentity.test_ieee_placeholder_org_is_not_recorded_as_a_vendor(self, tmp_path) (L127): 'IEEE Registration Authority' names no vendor - recording it lies.
- TestMacIdentity.test_shorten_is_cosmetic_only(self) (L139): Exercise shorten; assert shorten
- TestMacIdentity.test_randomized_mac_detected(self) (L147): Exercise is_randomized; assert is_randomized
- TestMacIdentity.test_real_vendor_mac_is_not_randomized(self) (L153): Exercise is_randomized; assert is_randomized
- TestMacIdentity.test_multicast_is_not_treated_as_randomized(self) (L158): Exercise is_multicast; assert is_multicast, is_randomized
- TestMacIdentity.test_private_address_explained_not_called_unknown(self) (L163): The honest answer to 'why is my phone unnamed?'.
- TestMacIdentity.test_missing_registry_is_distinguished_from_unknown_vendor(self) (L169): 'We couldn't look it up' must not masquerade as 'no such vendor'.
- TestMacIdentity.test_normalize_handles_formats(self) (L178): Exercise normalize; assert normalize
- TestDeviceLabelling.test_friendly_name_beats_uuid_hostname(self) (L192): Chromecasts use a raw UUID as hostname; the user's own name wins.
- TestDeviceLabelling.test_model_used_when_no_friendly_name(self) (L201): Construct Device; assert label
- TestDeviceLabelling.test_real_hostname_is_used(self) (L207): Construct Device; assert label
- TestDeviceLabelling.test_uuid_detection(self) (L212): Construct Device._looks_like_uuid; assert _looks_like_uuid
- TestDeviceLabelling.test_gateway_without_a_name_reads_as_router(self) (L218): Construct Device; assert label
- TestDeviceLabelling.test_private_address_is_not_used_as_a_name(self) (L223): Construct Device; assert label
- TestDeviceLabelling.test_label_never_empty(self) (L230): Construct Device; assert label
- TestDeviceKind.test_chromecast_classified_from_service_and_port(self) (L237): Construct Device; assert kind
- TestDeviceKind.test_esp_board_classified_from_the_registry_vendor_name(self) (L242): Classification keys off the authoritative vendor string, so any
- TestDeviceKind.test_classified_from_self_reported_model(self) (L251): A device's own UPnP/mDNS model text is enough, with no MAC at all.
- TestDeviceKind.test_unknown_vendor_is_not_guessed_into_a_category(self) (L256): Construct Device; assert kind
- TestDeviceKind.test_printer_classified(self) (L261): Construct Device; assert kind
- TestDeviceKind.test_randomized_mac_reads_as_phone_or_laptop(self) (L266): Construct Device; assert kind
- TestDeviceKind.test_gateway_and_self_win(self) (L271): Construct Device; assert kind
- TestDeviceKind.test_unknown_stays_unknown(self) (L276): Construct Device; assert kind
- TestEvidence.test_evidence_lists_every_source(self) (L283): Construct Device
- TestEvidence.test_evidence_never_empty(self) (L289): Construct Device; assert evidence
- TestMerge.test_observations_combine_without_losing_data(self) (L296): Construct Device; assert mac, hostname, sources, open_ports, services
- TestMerge.test_merge_does_not_overwrite_existing_values(self) (L309): Construct Device; assert hostname
- TestDnsParsing.test_query_is_well_formed(self) (L322): Construct NetworkDiscovery._build_dns_query; assert endswith, pack
- TestDnsParsing.test_parses_an_a_record(self) (L331): Construct NetworkDiscovery._parse_dns_records
- TestDnsParsing.test_handles_name_compression(self) (L343): mDNS responders rely on compression pointers; without support for
- TestDnsParsing.test_malformed_packet_does_not_raise(self) (L357): Construct NetworkDiscovery._parse_dns_records; assert _parse_dns_records, pack
- TestDnsParsing.test_compression_loop_is_bounded(self) (L367): A pointer cycle must terminate instead of hanging the scan.
- TestDnsParsing.test_txt_record_decoded(self) (L374): Construct NetworkDiscovery._parse_dns_records; assert any, str(...)
- TestServiceSplitting.test_splits_instance_and_type(self) (L389): Construct NetworkDiscovery._split_service_instance
- TestServiceSplitting.test_bare_service_type(self) (L396): Construct NetworkDiscovery._split_service_instance
- TestServiceSplitting.test_non_service_name(self) (L402): Construct NetworkDiscovery._split_service_instance; assert _split_service_instance
- test_ssdp_headers_parsed_case_insensitively() (L408): Construct NetworkDiscovery._parse_http_headers; assert startswith
- TestScanScope.test_interface_network_computed(self) (L424): Construct Interface; assert network
- TestScanScope.test_bad_netmask_is_survivable(self) (L429): Construct Interface; assert network
- TestScanScope.test_real_interfaces_are_private_only(self) (L433): Whatever this machine has, we must never target public space.
- TestScanScope.test_oversized_subnet_is_skipped_with_an_explanation(self, monkeypatch) (L441): A /8 must not be swept host-by-host; say so rather than hang.
- TestScanScope.test_oversized_subnet_is_skipped_with_an_explanation._no_sweep(*_a, **_k) (L455): no sweep: build/parse AssertionError
- TestScanScope.test_manual_scope_can_only_narrow_active_interface(self, monkeypatch) (L465): Construct NetworkDiscovery; assert networks, ip, devices
- TestScanScope.test_no_interfaces_reports_clearly(self, monkeypatch) (L491): Construct NetworkDiscovery; assert devices, notes, lower
- TestCancellation.test_already_cancelled_scan_does_almost_nothing(self, monkeypatch) (L503): Construct NetworkDiscovery; assert cancelled
- TestCancellation.test_already_cancelled_scan_does_almost_nothing._boom(*_a, **_k) (L514): boom: build/parse AssertionError
- TestNotes.test_randomized_macs_are_explained(self) (L531): Construct NetworkDiscovery._build_notes; assert any(...)
- TestNotes.test_client_isolation_suggested_when_only_router_answers(self) (L537): Construct NetworkDiscovery._build_notes; assert any(...)
- TestNotes.test_no_spurious_notes_for_a_healthy_scan(self) (L545): Construct NetworkDiscovery._build_notes
- test_result_serializes_to_json() (L559): Construct DiscoveryResult
- test_ip_sort_key_orders_numerically() (L576): Exercise sorted; assert _ip_sort_key
- test_ip_validation_rejects_garbage(bad) (L584): Construct NetworkDiscovery._is_ipv4; assert _is_ipv4

## tests/test_network_expert_tools.py — Offline tests for the optional Nmap adapter and strict Wake-on-LAN API.
- _available(monkeypatch: pytest.MonkeyPatch) -> nmap_adapter.NmapAdapter (L23): available via NmapAdapter; return result
- test_nmap_status_does_not_execute(monkeypatch: pytest.MonkeyPatch) -> None (L31): Exercise _available; assert available, executable
- test_nmap_missing_executable_has_clear_error(monkeypatch: pytest.MonkeyPatch) -> None (L43): Exercise setattr; assert available
- test_nmap_builds_safe_deterministic_argument_list(monkeypatch: pytest.MonkeyPatch) -> None (L58): Exercise _available
- test_nmap_rejects_every_unauthorized_target(monkeypatch: pytest.MonkeyPatch, target: str) -> None (L77): Exercise parametrize
- test_nmap_expert_modes_require_windows_admin(monkeypatch: pytest.MonkeyPatch) -> None (L86): Exercise _available
- test_nmap_scan_uses_proc_and_parses_observation(monkeypatch: pytest.MonkeyPatch) -> None (L101): Exercise _available; assert source, ip, port, name, product
- test_nmap_scan_uses_proc_and_parses_observation.fake_run(arguments, **kwargs) (L108): Fake run via CompletedProcess; return result
- test_nmap_cancellation_before_launch_skips_proc(monkeypatch: pytest.MonkeyPatch) -> None (L131): Exercise _available
- test_nmap_xml_rejects_dtd_and_entities(declaration: bytes) -> None (L149): Exercise parametrize
- test_nmap_xml_enforces_depth_limit() -> None (L156): Exercise raises
- test_nmap_xml_rejects_public_result() -> None (L163): Construct NMAP_XML.replace
- test_wol_rejects_invalid_or_non_unicast_mac(mac: str) -> None (L174): Exercise parametrize
- test_wol_builds_standard_magic_packet() -> None (L180): Exercise fromhex; assert len(...)
- test_wol_rejects_broadcast_outside_active_private_lan(broadcast: str, networks: tuple[str, ...]) -> None (L195): Exercise parametrize
- _Socket.__init__(self) -> None (L205): Initialize timeout, options, sent, closed
- _Socket.settimeout(self, value: float) -> None (L212): Settimeout: 'settimeout.'
- _Socket.setsockopt(self, *value) -> None (L216): Setsockopt via append
- _Socket.sendto(self, payload: bytes, destination: tuple[str, int]) -> int (L220): Sendto via append, len; return result
- _Socket.close(self) -> None (L225): Close: 'close.'
- test_wol_sends_one_bounded_udp_broadcast(monkeypatch: pytest.MonkeyPatch) -> None (L230): Exercise _Socket; assert timeout, options, SOL_SOCKET, SO_BROADCAST, socket
- test_wol_rejects_nonpositive_or_nonfinite_timeout() -> None (L249): Exercise float
- test_wol_wraps_socket_error_and_closes(monkeypatch: pytest.MonkeyPatch) -> None (L259): Construct OSError; assert closed
- test_wol_wraps_socket_error_and_closes.fail_send(_payload, _destination) (L265): Fail send: build/parse OSError

## tests/test_network_inventory.py — Synthetic tests for transactional network snapshot inventory.
- device(ip='192.168.1.10', mac='00:11:22:33:44:55', services=(), findings=(), **kwargs) (L19): Device: build InventoryDevice, via tuple; return result
- kinds(snapshot) (L36): Kinds: 'kinds.'; return result
- test_first_snapshot_reports_new_device_and_is_json_safe(tmp_path) (L41): Construct NetworkInventory; assert kinds(...)
- test_emits_new_service_and_severity_change(tmp_path) (L54): Construct NetworkInventory; assert previous, current, severity
- test_mac_and_gateway_mac_changes_are_distinct(tmp_path) (L79): Construct NetworkInventory; assert identity_confidence
- test_disappearance_is_relative_to_previous_snapshot(tmp_path) (L96): Construct NetworkInventory; assert previous, changes
- test_randomized_mac_uses_low_confidence_ip_identity(tmp_path) (L108): Construct NetworkInventory; assert device_id, changes, identity_confidence
- test_first_last_seen_and_catalogs_are_persisted(tmp_path) (L118): Construct NetworkInventory
- test_retention_removes_old_snapshots_and_orphan_catalogs(tmp_path) (L140): Construct NetworkInventory; assert snapshot_count
- test_duplicate_identity_rejected_without_partial_snapshot(tmp_path) (L152): Construct NetworkInventory; assert snapshot_count
- test_normalizes_discovery_style_mapping_and_validates_ip() (L164): Exercise normalize_device; assert mac, services, severity, findings
- test_schema_version_and_future_version_guard(tmp_path) (L180): Construct NetworkInventory; assert fetchone, execute
- test_memory_database_supported() (L194): Construct NetworkInventory; assert snapshot_count
- test_schema_v1_migrates_metadata_table_atomically(tmp_path) (L201): Construct NetworkInventory; assert list_metadata, fetchone, execute
- test_metadata_trends_and_csv_round_trip_are_safe(tmp_path) (L214): Construct NetworkInventory; assert tags, get_metadata, export_inventory_csv, custom_name, notes
- test_invalid_csv_rolls_back_all_metadata(tmp_path) (L255): Construct NetworkInventory; assert list_metadata

## tests/test_network_monitor.py — Tests for the read-only network connection monitor.
- TestClassification.test_loopback_is_private(self) (L18): Exercise _is_private; assert _is_private(...)
- TestClassification.test_lan_is_private(self) (L23): Exercise _is_private; assert _is_private(...)
- TestClassification.test_public_is_not_private(self) (L29): Exercise _is_private; assert _is_private(...)
- TestClassification.test_unparseable_defaults_private(self) (L34): Exercise _is_private; assert _is_private(...)
- TestConnectionFlags.test_public_listener_flagged(self) (L42): Construct Connection; assert listening_public, remote_external
- TestConnectionFlags.test_localhost_listener_not_public(self) (L48): Construct Connection; assert listening_public
- TestConnectionFlags.test_external_established_flagged(self) (L53): Construct Connection; assert remote_external
- TestConnectionFlags.test_internal_established_not_external(self) (L59): Construct Connection; assert remote_external
- TestConnectionFlags.test_to_dict_shape(self) (L65): Construct Connection; assert set(...)
- TestMonitor.test_connections_returns_list(self) (L79): Construct NetworkMonitor; assert isinstance, all(...)
- TestMonitor.test_summarize_counts(self) (L85): Construct NetworkMonitor.summarize

## tests/test_network_security_audit.py — Safety-guard tests for defensive private-LAN scanning (no live network).
- test_guard_accepts_rfc1918_lan_addresses(target: str) -> None (L37): The three RFC 1918 private ranges are the only allowed scan scope.
- test_guard_rejects_every_out_of_scope_address(target: str) -> None (L56): Public, special-use and near-miss addresses must all be refused.
- test_guard_rejects_malformed_and_non_ipv4_input(target: str) -> None (L73): Anything that is not a bare, valid IPv4 host address is refused.
- test_guard_rejects_leading_zero_octets() -> None (L79): Ambiguous octal-looking octets must be refused, not reinterpreted.
- test_guard_returns_address_usable_for_socket_operations() -> None (L91): The returned value is what callers feed straight into sockets.

## tests/test_network_tools.py — Tests for the network diagnostic utilities (parsers + offline logic).
- TestPingParse.test_windows_success(self) (L49): Construct NetworkTools._parse_ping; assert reachable, sent, received, loss_percent, min_ms
- TestPingParse.test_nix_success(self) (L58): Construct NetworkTools._parse_ping; assert reachable, received, avg_ms
- TestPingParse.test_loss(self) (L65): Construct NetworkTools._parse_ping; assert loss_percent, received, reachable
- TestPingParse.test_unreachable(self) (L71): Construct NetworkTools._parse_ping; assert reachable
- TestTracerouteParse.test_parses_hops(self) (L79): Construct NetworkTools._parse_traceroute; assert number, host, times_ms
- TestTracerouteParse.test_timeout_hop(self) (L86): Construct NetworkTools._parse_traceroute; assert host, times_ms
- TestTracerouteParse.test_hop_to_dict_avg(self) (L92): Construct NetworkTools._parse_traceroute
- TestDNS.test_localhost_resolves(self) (L101): Construct NetworkTools.dns_lookup; assert startswith
- TestDNS.test_bad_host_empty(self) (L106): Construct NetworkTools.dns_lookup; assert dns_lookup
- TestDNS.test_reverse_loopback(self) (L110): Construct NetworkTools.reverse_dns; assert reverse_dns
- TestPorts.test_closed_high_port_false(self) (L118): Construct NetworkTools.check_port; assert check_port
- TestPorts.test_invalid_port(self) (L123): Construct NetworkTools.check_port; assert check_port
- TestPorts.test_scan_returns_all_common_ports(self) (L127): Construct NetworkTools; assert keys, values
- TestIpInfo.test_public(self) (L137): Construct NetworkTools.ip_info
- TestIpInfo.test_private(self) (L143): Construct NetworkTools.ip_info
- TestIpInfo.test_loopback(self) (L148): Construct NetworkTools.ip_info; assert ip_info
- TestIpInfo.test_ipv6(self) (L152): Construct NetworkTools.ip_info
- TestIpInfo.test_invalid(self) (L157): Construct NetworkTools.ip_info; assert ip_info

## tests/test_network_traffic.py — Tests for the live throughput monitor (rate math + shape).
- TestSample.test_first_sample_zero_rate(self) (L18): Construct TrafficMonitor; assert send_rate, recv_rate, total_sent, total_recv
- TestSample.test_since_start_starts_zero(self) (L27): Construct TrafficMonitor; assert sent_since_start, recv_since_start
- TestSample.test_second_sample_has_nonnegative_rates(self) (L33): Construct TrafficMonitor; assert send_rate, recv_rate, sent_since_start, recv_since_start
- TestSample.test_per_nic_present_and_sorted(self) (L44): Construct TrafficMonitor; assert per_nic
- TestSample.test_to_dict_shape(self) (L54): Construct TrafficMonitor; assert set(...)
- test_singleton() (L62): Construct TrafficMonitor.instance; assert instance

## tests/test_nextgen_tools.py — Comprehensive test suite for Next-Generation Enterprise System Tools & Forensics.
- test_shader_cache_cleaner_scan_and_clean() (L31): Test ShaderCacheCleaner scan, age filtering, and dry-run cleanup.
- test_ai_telemetry_cleaner_wal_checkpoint() (L62): Test AiTelemetryCleaner SQLite WAL checkpointing and truncation.
- test_ssd_trim_optimizer() (L96): Test SsdTrimOptimizer volume auditing and retrim execution.
- test_restart_manager_unlocker() (L113): Test RestartManagerUnlocker lock inspection and safe unlock.
- test_vss_health_analyzer() (L134): Test VssHealthAnalyzer status parsing and reset logic.
- test_dev_package_cache_cleaner() (L161): Test DevPackageCacheCleaner store analysis and dry-run purging.
- test_checksum_matrix_manifest_flow() (L185): Test ChecksumMatrix hashing, manifest generation, and verification.

## tests/test_nexus_exhaustive_audit.py — Exhaustive End-to-End Audit & Edge-Case Verification Suite for NexusExplorer.
- qapp() (L29): Qapp: build QApplication.instance, via fixture; return result
- test_audit_in_place_copy_protection(qapp) (L37): Test copying a file into the same directory generates a duplicate safely without data loss.
- test_audit_circular_directory_protection(qapp) (L71): Test that copying a folder into its own subfolder is prevented safely.
- test_audit_empty_directory_preservation_on_copy(qapp) (L103): Test copying nested directory tree preserves empty subdirectories.
- test_audit_tab_management_and_closing(qapp) (L136): Test creating multiple tabs and closing specific tabs without index corruption.
- test_audit_engine_python_simple_and_delete(qapp) (L168): Test Python fallback implementations for rename, delete, mkdir, and hash.
- test_audit_bulk_rename_modes(qapp) (L202): Test BulkRenameDialog rename transformations.

## tests/test_page_registry.py — Contracts for the declarative page registry.
- test_registry_is_internally_consistent() (L26): Ids unique, groups known, factories well formed.
- test_every_declared_factory_actually_resolves() (L37): A typo must fail here, not when a user clicks the tool.
- test_malformed_factory_is_rejected_with_a_clear_message() (L45): Exercise PageSpec
- test_ordering_is_group_order_then_declaration_order() (L52): Sidebar order must be predictable and total.
- test_grouped_covers_every_page_exactly_once() (L62): Exercise grouped; assert id, PAGES
- test_by_id_and_group_of_agree_with_pages() (L71): Exercise group_of; assert BY_ID, id, group, group_of
- test_default_page_exists_and_is_reachable() (L78): Verify default page exists and is reachable (DEFAULT_PAGE_ID, BY_ID)
- test_window_aliases_are_derived_from_the_registry() (L85): ``_NAV``/``_NAV_GROUPS``/``_PAGE_FACTORIES`` are views, not sources.
- test_adding_one_spec_wires_nav_group_search_and_stack(monkeypatch) (L97): A single declaration must be sufficient to add a working tool.

## tests/test_perceptual_duplicate_finder.py — Tests for perceptual image duplicate detection (pHash/dHash/aHash).
- _make_image(path: Path, size: int=128) (L23): make image: build Image.new, via putdata, save
- _make_plain(path: Path, size: int=128, color: str='red') (L33): make plain: build Image.new, via save
- test_hashes_are_int(tmp_path) (L40): Exercise _make_image; assert isinstance(...)
- test_hashes_deterministic_on_identical_image(tmp_path) (L48): Exercise _make_image; assert compute_hash(...)
- test_hamming_distance_basic() (L58): Exercise hamming_distance; assert hamming_distance(...)
- test_perceptual_hashes_agree_across_rescales(tmp_path) (L65): Construct Image.open; assert hamming_distance, compute_hash(...)
- test_different_images_are_far_apart_in_phash(tmp_path) (L77): Exercise _make_image; assert hamming_distance, perceptual_hash(...)
- test_unknown_kind_raises(tmp_path) (L89): Construct Path
- test_finder_groups_rescaled_identical_images(tmp_path) (L97): Construct PerceptualDuplicateFinder
- test_finder_excludes_non_images(tmp_path) (L112): Construct PerceptualDuplicateFinder; assert find_perceptual_duplicates
- test_finder_respects_exclude_dirs(tmp_path) (L120): Construct Config; assert intersection
- test_finder_stats(tmp_path) (L140): Construct PerceptualDuplicateFinder
- test_finder_error_handling_skips_corrupt(tmp_path) (L153): Construct PerceptualDuplicateFinder; assert error_count

## tests/test_performance_tuner.py — Tests for the power-plan tuner (parsing + safety gating).
- TestParse.test_parses_all_plans(self) (L22): Construct PerformanceTuner._parse; assert len, all, isinstance(...)
- TestParse.test_marks_active_plan(self) (L30): Construct PerformanceTuner._parse; assert name, guid
- TestParse.test_empty_input(self) (L38): Construct PerformanceTuner._parse; assert _parse
- TestSafety.test_is_supported_matches_platform(self) (L46): Construct PerformanceTuner.is_supported; assert is_supported
- TestSafety.test_set_active_rejects_bad_guid(self) (L50): Construct PerformanceTuner
- TestSafety.test_list_plans_returns_list(self) (L55): Construct PerformanceTuner; assert list_plans
- TestSafety.test_to_dict(self) (L59): Construct PowerPlan; assert to_dict

## tests/test_portable_manager.py — Tests for portable_manager — PortableApps.com / LiberKey catalog, USB toolkit.
- TestPortableApp.test_basic_construction(self, tmp_path) (L29): Construct PortableApp; assert id, version, update_available, latest_version, is_portable_format
- TestPortableApp.test_to_dict_slots_incompatibility(self, tmp_path) (L47): Construct PortableApp
- TestParseAppinfo._write_appinfo(self, root: Path, content: str) -> Path (L70): write appinfo via write_text; return result
- TestParseAppinfo.test_valid_appinfo(self, tmp_path) (L76): Exercise _write_appinfo; assert name, version, category, launch_exe
- TestParseAppinfo.test_missing_ini_returns_none(self, tmp_path) (L95): Exercise _parse_appinfo; assert _parse_appinfo(...)
- TestParseAppinfo.test_garbage_ini_returns_none(self, tmp_path) (L99): Exercise write_text; assert _parse_appinfo(...)
- TestParseAppinfo.test_launch_exe_fallback_to_first_exe(self, tmp_path) (L105): Exercise _write_appinfo; assert launch_exe
- TestParseAppinfo.test_no_exe(self, tmp_path) (L115): Exercise _write_appinfo; assert launch_exe
- TestParseAppinfo.test_fallback_to_first_section(self, tmp_path) (L123): Exercise _write_appinfo; assert name
- TestPortableManagerInit.test_default_init(self) (L141): Construct PortableManager; assert progress, cancel, Event, is_set
- TestPortableManagerInit.test_custom_progress(self) (L148): Construct PortableManager
- TestPortableManagerInit.test_custom_cancel_event(self) (L155): Construct PortableManager; assert is_set, cancel
- TestScanPortableRoots._build_paf_app(self, root: Path, name: str, version: str='1.0') (L170): build paf app via mkdir, write_text, touch; return result
- TestScanPortableRoots.test_scan_paf_apps(self, tmp_path) (L182): Construct PortableManager
- TestScanPortableRoots.test_scan_empty_root(self, tmp_path) (L193): Construct PortableManager; assert scan_portable_roots
- TestScanPortableRoots.test_scan_nonexistent_root(self, tmp_path) (L198): Construct PortableManager; assert scan_portable_roots
- TestScanPortableRoots.test_scan_liberkey_heuristic(self, tmp_path) (L203): Construct PortableManager; assert name, category, version
- TestScanPortableRoots.test_scan_skips_files(self, tmp_path) (L216): Construct PortableManager; assert scan_portable_roots
- TestScanPortableRoots.test_scan_cancellation(self, tmp_path) (L222): Construct PortableManager
- TestCheckUpdates._make_app_with_ini(self, root: Path, name: str, version: str, update_url: str | None=None) (L239): make app with ini: build PortableApp, via mkdir, write_text; return result
- TestCheckUpdates.test_no_update_url_skipped(self, tmp_path) (L267): Construct PortableManager; assert update_available
- TestCheckUpdates.test_update_available(self, tmp_path) (L275): Construct MagicMock; assert update_available, latest_version
- TestCheckUpdates.test_no_update_when_current(self, tmp_path) (L297): Construct MagicMock; assert update_available
- TestCheckUpdates.test_network_failure_continues(self, tmp_path) (L318): Construct PortableManager; assert lower
- TestCheckUpdates.test_non_ini_response_skipped(self, tmp_path) (L334): Construct MagicMock
- TestCheckUpdates.test_empty_version_no_update(self, tmp_path) (L353): Construct MagicMock
- TestUpdateApp.test_update_no_installer_returns_false(self, tmp_path) (L396): Construct PortableApp; assert update_app
- TestUpdateApp.test_update_with_installer(self, tmp_path) (L414): Construct PortableApp; assert str(...)
- TestUpdateApp.test_update_installer_failure(self, tmp_path) (L445): Construct PortableApp; assert update_app
- TestUpdateApp.test_update_subprocess_exception(self, tmp_path) (L470): Construct PortableApp; assert update_app, lower
- TestSysinternalsDownload.test_download_success(self, tmp_path) (L503): Construct MagicMock; assert exists, read_bytes
- TestSysinternalsDownload.test_download_not_pe_rejected(self, tmp_path) (L524): Construct FakeResp
- TestSysinternalsDownload.test_download_not_pe_rejected.FakeResp.__init__(self, data) (L535): Initialize _data, _read
- TestSysinternalsDownload.test_download_not_pe_rejected.FakeResp.read(self, n=-1) (L540): Read: 'read.'; return result
- TestSysinternalsDownload.test_download_not_pe_rejected.FakeResp.__enter__(self) (L547): enter  : '__enter__.'; return result
- TestSysinternalsDownload.test_download_not_pe_rejected.FakeResp.__exit__(self, *a) (L551): exit  : '__exit__.'; return result
- TestSysinternalsDownload.test_download_network_error(self, tmp_path) (L564): Construct PortableManager; assert exists, lower
- TestExportToolkit._build_paf_app(self, root: Path, name: str) (L588): build paf app via mkdir, write_text, touch
- TestExportToolkit.test_export_copies_paf_apps(self, mock_roots, tmp_path) (L597): Construct PortableManager; assert exists
- TestExportToolkit.test_export_skips_existing(self, mock_roots, tmp_path) (L612): Construct PortableManager; assert read_text
- TestExportToolkit.test_export_sysinternals(self, mock_dl, mock_roots, tmp_path) (L630): Construct PortableManager; assert exists, call_count
- TestExportToolkit.test_export_sysinternals_custom_tools(self, mock_dl, mock_roots, tmp_path) (L645): Construct PortableManager; assert call_count
- TestExportToolkit.test_export_skips_existing_sysinternals(self, mock_dl, mock_roots, tmp_path) (L665): Construct PortableManager
- TestProgressCallback.test_progress_called_on_update_failure(self, tmp_path) (L689): Construct PortableApp; assert lower
- TestProgressCallback.test_progress_called_on_export(self, mock_find_roots=None) (L719): Construct PortableManager
- TestCancellation._build_paf_app(self, root: Path, name: str) (L734): build paf app via mkdir, write_text, touch
- TestCancellation.test_scan_respects_cancel(self, tmp_path) (L742): Construct PortableManager
- TestCancellation.test_scan_respects_cancel.counting_iterdir(self_inner) (L750): Counting iterdir via original_iterdir; loop over original_iterdir(self_inner)
- TestCancellation.test_scan_respects_cancel.set_cancel_after_one(*a, **kw) (L761): Set cancel after one via set; return result
- TestPAFSilentFlag.test_silent_flag_value(self) (L781): Verify silent flag value (_PAF_SILENT_FLAG)
- TestPAFSilentFlag.test_sysinternals_live_url(self) (L785): Verify sysinternals live url (_SYSINTERNALS_LIVE)
- TestExportToolkitIntegration.test_export_creates_directory(self, mock_roots, tmp_path) (L798): Construct PortableManager; assert exists
- TestExportToolkitIntegration.test_export_returns_true(self, mock_roots, tmp_path) (L808): Construct PortableManager; assert export_toolkit
- TestExportToolkitIntegration.test_export_failure_returns_false(self, mock_roots, tmp_path) (L818): Construct PortableManager; assert lower

## tests/test_power_suite_tools.py — Unit tests for the 10 Enterprise Power Suite system tools and utilities.
- test_env_variable_manager() (L18): Construct EnvironmentVariableManager.analyze_path; assert total_entries, valid_entries
- test_service_manager() (L26): Construct WindowsServiceManager.enumerate_services; assert name
- test_font_cache_manager() (L36): Construct FontCacheManager.analyze; assert total_fonts, total_size_bytes
- test_temp_folder_cleaner() (L44): Construct TempFolderCleaner.scan; assert locations, total_files
- test_context_menu_manager() (L52): Construct ContextMenuManager.analyze; assert total_entries
- test_pagefile_optimizer() (L59): Construct PagefileOptimizer.get_status; assert total_physical_bytes, recommended_min_mb, recommended_max_mb
- test_diagnostic_data_manager() (L68): Construct DiagnosticDataManager.audit_telemetry; assert total_settings, privacy_score_percent
- test_startup_impact_analyzer() (L76): Construct StartupImpactAnalyzer.analyze_startup; assert total_startup_items, estimated_boot_delay_seconds
- test_slack_space_analyzer(tmp_path) (L84): Construct SlackSpaceAnalyzer.analyze_directory; assert total_files_scanned, cluster_size_bytes, total_physical_bytes, total_logical_bytes, total_slack_waste_bytes
- test_event_log_monitor() (L100): Construct EventLogMonitor.query_anomalies; assert total_anomalies

## tests/test_power_tools_production.py — Comprehensive Production Unit Tests for Enterprise Power Tools & Pages.
- test_hash_computation(tmp_path: Path) (L88): Construct HashTool.compute_all_hashes; assert MD5, SHA1, SHA256, SHA512, CRC32
- test_checksum_manifest_creation_and_verify(tmp_path: Path) (L105): Construct HashTool.create_manifest; assert exists, status, path, resolve
- test_batch_renamer_tokens_and_case(tmp_path: Path) (L142): Construct BatchRenamer; assert new_name, exists
- test_directory_diff_and_sync(tmp_path: Path) (L183): Construct DirectoryDiffEngine.compare_directories; assert IDENTICAL, get, LEFT_ONLY, RIGHT_ONLY, NEWER_LEFT
- test_file_splitter_and_joiner(tmp_path: Path) (L231): Construct FileSplitterJoiner.split_file; assert success, parts_created, exists, manifest_path, hash_verified
- test_file_unlocker_inspect(tmp_path: Path) (L267): Construct FileUnlocker.get_locking_processes; assert isinstance(...)
- test_alternate_data_streams_list(tmp_path: Path) (L280): Construct AlternateDataStreamsManager.list_streams; assert isinstance(...)
- test_event_log_cleaner_scan() (L297): Construct EventLogCleaner.list_all_logs; assert name
- test_system_cache_rebuilder_scan() (L310): Construct SystemCacheRebuilder.notify_shell_refresh; assert isinstance(...)
- test_network_stack_optimizer_status() (L320): Construct NetworkStackOptimizer.get_tcp_settings; assert hasattr(...)
- test_crash_dump_cleaner_scan() (L332): Construct CrashDumpCleaner.scan_dumps; assert isinstance(...)
- test_delivery_optimization_cleaner_scan() (L342): Construct DeliveryOptimizationCleaner.get_status; assert file_count, size_bytes

## tests/test_premium_gui.py — Headless smoke tests for the premium GUI.
- app() (L21): App: build QApplication.instance, via fixture
- window(app) (L28): Window: build PremiumMainWindow, via resize, deleteLater
- test_stylesheet_builds_for_both_themes(app) (L46): Construct THEMES.items; assert accent
- test_all_pages_present(window) (L55): Exercise set; assert _pages, id, PAGES
- test_navigate_every_page(window) (L61): Selecting each page must switch the stack without error.
- test_theme_toggle_does_not_crash(window) (L68): Exercise set_theme; assert theme_name
- test_navigation_switches_pages(window) (L76): Exercise _select; assert currentWidget, _pages, _stack
- test_dashboard_populates_from_report(window) (L84): Construct CategoryScan; assert topLevelItemCount, tree, isEnabled, recycle_btn, text
- test_dashboard_preview_expands(window) (L104): Expanding a category must lazily reveal its contents (preview).
- test_preview_helpers(app) (L147): The drill-down grouping helpers must aggregate correctly and fast.
- test_group_by_app(app) (L175): App caches must group by their owning app with friendly names.
- test_dashboard_selection_excludes(window) (L195): Unchecking an app/folder in the preview must exclude it from cleaning.
- test_circular_gauge_animates(window) (L238): Exercise animate_to; assert value, gauge
- test_render_to_pixmap(window) (L246): The window must render to a non-empty pixmap (catches paint crashes).
- test_responsive_resize(window) (L253): Content must adapt (and render) across small and large window sizes.
- test_core_bars_widget_renders(app) (L277): The per-core CPU bar widget must accept values and paint without error.
- test_stat_card_animate_value(app) (L291): Construct StatCard; assert text, _value
- test_shred_page_present_and_wired(window) (L302): Exercise hasattr; assert isEnabled, shred_btn
- test_recycle_worker_actually_removes(app, tmp_path) (L310): DeleteSelectedWorker (recycle) must remove a real file, run synchronously.
- test_dashboard_live_scan_completes(app, window) (L324): The real 'Scan Now' flow must run on a worker thread and populate results.
- test_shred_worker_overwrites_and_removes(app, tmp_path) (L350): ShredWorker with force_flash must overwrite+delete regardless of medium.
- _CoopWorker.__new__(cls) (L373): new  : build W, via __init__, Event; loop over range(300); return result
- _CoopWorker.__new__.W.__init__(self) (L383): Initialize _cancel
- _CoopWorker.__new__.W.cancel(self) (L388): Cancel via set
- _CoopWorker.__new__.W.run(self) (L392): Run via is_set; loop over range(300)
- test_close_with_cooperative_worker_is_fast_and_clean(app, window) (L403): A cancellable worker must stop within the close grace, leave nothing
- test_close_with_unkillable_worker_detaches_instead_of_crashing(app, window) (L418): A worker that ignores cancel/quit/terminate must be detached + recorded
- test_close_with_unkillable_worker_detaches_instead_of_crashing.StuckWorker.run(self) (L430): Run via Event, wait
- test_run_worker_refused_after_close(app, window) (L455): Once shutdown begins, no new worker may start (it would outlive the
- test_run_worker_refused_after_close.Probe.run(self) (L464): Run via append
- temp_window(app, tmp_path) (L480): A real window backed by a throwaway settings file so persistence tests
- _fake_qobject_window(app) (L496): A minimal QObject that quacks like the window for tray-action tests.
- _fake_qobject_window.FakeWin.__init__(self) (L503): Initialize palette_tokens, _force_quit, _pages, calls
- _fake_qobject_window.FakeWin.isMinimized(self) (L511): IsMinimized: 'isMinimized.'; return result
- _fake_qobject_window.FakeWin.show(self) (L515): Show via append
- _fake_qobject_window.FakeWin.showNormal(self) (L519): ShowNormal via append
- _fake_qobject_window.FakeWin.raise_(self) (L523): Raise  via append
- _fake_qobject_window.FakeWin.activateWindow(self) (L527): ActivateWindow via append
- _fake_qobject_window.FakeWin._select(self, pid) (L531): select via append
- _fake_qobject_window.FakeWin.close(self) (L535): Close via append
- test_settings_store_defaults_and_roundtrip(tmp_path) (L542): Construct SettingsStore; assert theme, close_to_tray
- test_settings_store_tolerates_corrupt_file(tmp_path) (L556): Construct SettingsStore; assert theme, close_to_tray
- test_settings_store_sanitizes_bad_values(tmp_path) (L566): Construct SettingsStore; assert theme, close_to_tray
- test_theme_choice_persists_across_restart(temp_window) (L579): Construct SettingsStore; assert theme, _path
- test_settings_page_marks_active_theme(temp_window) (L589): Exercise _choose_theme; assert objectName, dark_btn, light_btn, theme
- test_tray_icon_renders_for_both_themes(app) (L602): Construct THEMES.values; assert isNull
- test_tray_is_inert_when_unavailable(app, tmp_path) (L610): Offscreen has no system tray, so PremiumTray must construct cleanly and
- test_tray_menu_actions_drive_window(app, tmp_path) (L624): Construct PremiumTray; assert calls, _force_quit
- test_close_to_tray_hides_instead_of_quitting(temp_window) (L639): With close-to-tray on and a tray available, closing the window hides it
- test_close_to_tray_hides_instead_of_quitting.FakeTray.__init__(self) (L646): Initialize available, msgs, stopped
- test_close_to_tray_hides_instead_of_quitting.FakeTray.show_message(self, title, message, msecs=6000) (L652): Show message via append
- test_close_to_tray_hides_instead_of_quitting.FakeTray.stop(self) (L656): Stop: 'stop.'
- test_close_to_tray_hides_instead_of_quitting.FakeTray.refresh_theme(self, palette) (L660): Refresh theme: 'refresh_theme.'
- test_close_to_tray_only_hints_once(temp_window) (L681): Construct FakeTray; assert msgs, _tray
- test_close_to_tray_only_hints_once.FakeTray.__init__(self) (L687): Initialize available, msgs
- test_close_to_tray_only_hints_once.FakeTray.show_message(self, title, message, msecs=6000) (L692): Show message via append
- test_close_to_tray_only_hints_once.FakeTray.stop(self) (L696): Stop: 'stop.'
- test_focus_ring_is_clean_border_not_boxy_outline(app) (L713): Both themes must draw focus as a clean border, never a boxy 'outline'
- test_focus_visible_ring_only_for_keyboard(app) (L725): The ring (focusVisible=true) appears when focus arrives via the keyboard
- test_install_focus_visible_is_idempotent(app) (L754): Exercise install_focus_visible; assert getattr(...)
- _scroll_area(app, rng: int=1000) (L768): A scroll area with a deterministic vertical range for wheel tests.
- _wheel(down: bool=True, pixel: bool=False) (L779): wheel: build/parse QPoint; return result
- test_smooth_scroll_glides_on_mouse_wheel(app) (L790): Exercise _scroll_area; assert _target, endValue, _anim
- test_smooth_scroll_ignores_touchpad(app) (L802): Exercise _scroll_area; assert eventFilter, viewport
- test_smooth_scroll_hands_off_at_boundary(app) (L811): Exercise _scroll_area; assert eventFilter, viewport
- test_smooth_scroll_respects_reduced_motion(app) (L822): Exercise _scroll_area; assert eventFilter, viewport
- test_install_smooth_scroll_is_idempotent(app) (L836): Exercise _scroll_area
- test_pages_have_smooth_scroll_installed(window) (L845): Every page's outer scroll area gets the premium glide.
- test_reveal_respects_reduced_motion(app) (L855): Construct QWidget
- test_settings_store_reduced_motion_roundtrip(tmp_path) (L874): Construct SettingsStore; assert reduced_motion
- test_shimmer_skeleton_start_stop(app) (L884): Construct ShimmerSkeleton; assert phase
- test_settings_page_reduced_motion_toggle(temp_window) (L902): Exercise hasattr; assert prefers_reduced_motion, reduced_motion
- test_health_page_has_shimmer_skeleton(window) (L916): Exercise isinstance; assert isinstance, getattr(...)
- test_press_feedback_sinks_and_restores(app) (L927): Construct QPushButton; assert _press_active, endValue, _press_anim
- test_press_feedback_respects_reduced_motion(app) (L942): Construct QPushButton; assert getattr(...)
- test_bento_tile_hover_in_stylesheet(app) (L956): Construct THEMES.values
- test_dashboard_uses_bento_tiles(window) (L965): Exercise hasattr; assert text, _value, card_space, objectName
- test_badge_uses_rgba_not_ambiguous_hex(app) (L981): Badges must build their translucent fill from rgba() - an 8-digit
- test_processes_memory_details_collapsed_by_default(window) (L993): The long memory explanation must be collapsed (progressive disclosure)
- test_health_check_columns_size_to_content(window) (L1005): The Check + Fix columns size to content so "Fix ->" is never clipped,
- test_uninstaller_page_has_leftover_section(window) (L1020): Exercise hasattr; assert isEnabled, clean_leftover_btn
- test_leftover_findings_populate_table_and_status(window) (L1030): Exercise _on_leftovers; assert rowCount, model, leftover_table, isHidden, leftover_state
- test_leftover_clean_button_needs_selection(window) (L1046): Exercise _on_leftovers; assert isEnabled, clean_leftover_btn
- test_leftover_scan_without_pending_shows_hint(window, monkeypatch) (L1058): Clicking Scan with no recorded uninstall must hint, never crash.
- test_leftover_clean_worker_recycles_and_reports(tmp_path, monkeypatch) (L1070): LeftoverCleanWorker routes findings through LeftoverCleaner.
- test_leftover_clean_worker_recycles_and_reports.FakeCleaner.__init__(self) (L1077): init  : '__init__.'
- test_leftover_clean_worker_recycles_and_reports.FakeCleaner.clean(self, models, create_restore_point=False, exclusions=None, cancel_event=None) (L1081): Clean: build/parse CleanOutcome; return result
- test_leftover_clean_worker_requests_restore_point_when_asked(tmp_path, monkeypatch) (L1104): The checkbox's choice reaches the cleaner as create_restore_point.
- test_leftover_clean_worker_requests_restore_point_when_asked.FakeCleaner.__init__(self) (L1112): init  : '__init__.'
- test_leftover_clean_worker_requests_restore_point_when_asked.FakeCleaner.clean(self, models, create_restore_point=False, exclusions=None, cancel_event=None) (L1116): Clean: build/parse CleanOutcome; return result
- test_leftover_scan_worker_emits_sorted_findings(monkeypatch) (L1137): Findings come back as plain dicts sorted by score descending.
- test_leftover_scan_worker_emits_sorted_findings.FakeScanner.__init__(self, installed_apps=None, exclusions=None, cancel_event=None, policy=None) (L1144): Initialize _calls
- test_leftover_scan_worker_emits_sorted_findings.FakeScanner.scan_app(self, app) (L1150): Scan app via LeftoverFinding; return result
- test_leftover_workers_support_cooperative_cancel() (L1172): cancel() must exist on all three workers (window shutdown calls it).
- test_uninstall_hands_off_metadata_to_leftover_page(window, monkeypatch) (L1189): Uninstaller page captures app metadata; Leftover Scanner consumes it.
- test_uninstall_hands_off_metadata_to_leftover_page.fake_worker_init(self, apps, exclusions=None) (L1221): Fake worker init: build QObject.__init__, via list, append
- test_uninstall_hands_off_metadata_to_leftover_page.fake_worker_run(self) (L1230): Fake worker run via emit

## tests/test_premium_hidpi.py — High-DPI crispness regression tests for the premium GUI.
- app() (L32): App: build QApplication.instance, via fixture
- window(app) (L39): Window: build PremiumMainWindow, via apply_theme, resize
- test_card_has_no_persistent_graphics_effect(app) (L50): A Card must render its surface via QSS, not a blur-prone effect.
- test_hero_buttons_and_gauge_have_no_persistent_effect(window) (L66): The Scan/Clean CTAs and the dashboard gauge must stay crisp: no effect.
- test_attach_glow_does_not_attach_blurring_effect(app) (L74): attach_glow must never install a QGraphicsEffect (which would blur).
- test_gauge_paints_with_glow_enabled(app) (L92): With a glow set, the gauge must still paint without error at any value.
- test_statcard_pulse_effect_is_torn_down(app) (L109): The one-shot pulse uses a transient opacity effect that must be removed
- test_page_fade_leaves_no_permanent_effect(window) (L125): Navigating pages uses a transient fade; once complete the page must have

## tests/test_premium_tokens.py — Tests for the Qt-free premium design tokens (`tokens.py`).
- test_elevation_has_four_ordered_levels() (L29): Req 12.1: at least four ordered elevation levels, lowest -> highest.
- test_elevation_named_levels_present() (L35): Exercise hasattr; assert hasattr(...)
- test_elevation_style_returns_valid_style(palette, level) (L48): Exercise parametrize; assert surface, border, shadow_blur, shadow_alpha, surface_alpha
- test_elevation_style_accepts_int_level(palette) (L60): Callers may pass a raw int; it resolves to the matching level.
- test_glass_translucency_only_at_higher_levels(palette) (L66): Base levels stay opaque; raised/overlay use a translucent glass fill.
- _assert_monotonic_depth(palette) -> None (L79): assert monotonic depth via zip, elevation_style, _rel_luminance; loop over zip(styles, styles[1:])
- test_depth_monotonic_for_builtin_themes(palette) (L92): Req 12.2: higher levels are a visibly stronger depth cue.
- test_depth_monotonic_for_arbitrary_palettes(bg, surface, surface_alt, border) (L109): Validates: Requirements 12.1, 12.2
- test_elevation_style_tolerates_minimal_palette() (L130): Missing optional fields (surface_raised/overlay/glass_*) fall back safely.
- test_contrast_ratio_black_on_white_is_maximum() (L153): Pure black vs pure white is the WCAG maximum of 21:1.
- test_contrast_ratio_identical_colors_is_minimum() (L158): A color against itself has no contrast: the 1:1 floor.
- test_contrast_ratio_is_symmetric() (L163): Swapping foreground/background does not change the ratio.
- test_contrast_ratio_handles_shorthand_hex() (L170): #RGB shorthand expands to #RRGGBB (so #FFF == #FFFFFF).
- test_contrast_ratio_unparseable_treated_as_darkest() (L175): Bad input degrades to luminance 0.0 rather than raising.
- test_contrast_ratio_bounds_and_symmetry(fg, bg) (L181): Validates: Requirements 10.3, 10.4

## tests/test_process_meta.py — Tests for human-friendly process descriptions (honest, cached).
- TestKnown.test_common_system_processes(self) (L14): Exercise known_description; assert known_description
- TestKnown.test_idle_labeled_as_not_real(self) (L20): Exercise known_description; assert lower
- TestKnown.test_unknown_returns_empty(self) (L25): Exercise known_description; assert known_description
- TestDescribe.test_describe_prefers_known(self) (L32): Exercise describe; assert describe
- TestDescribe.test_describe_unknown_no_path_is_empty(self) (L38): Exercise describe; assert describe
- TestDescribe.test_describe_never_fabricates(self) (L42): Exercise describe; assert describe
- TestFileDescriptionCache.test_cache_used(self) (L50): Exercise clear; assert _desc_cache
- TestFileDescriptionCache.test_empty_path(self) (L58): Exercise file_description; assert file_description
- TestRealSystemExeIfWindows.test_reads_a_real_description(self) (L65): Exercise join; assert isinstance(...)

## tests/test_production_hardening.py — Tests for the production-hardening round:
- fake_env(monkeypatch, tmp_path) (L20): Redirect every sweep root into a throwaway directory tree.
- TestExclusionsStore.test_add_is_persisted_and_prefix_matched(self, tmp_path) (L45): Construct ExclusionsStore; assert add, is_excluded
- TestExclusionsStore.test_discard_removes_and_persists(self, tmp_path) (L59): Construct ExclusionsStore; assert discard
- TestExclusionsStore.test_corrupt_file_degrades_to_empty(self, tmp_path) (L68): Construct ExclusionsStore; assert add
- TestScannerExclusions.test_scan_app_skips_excluded_folders(self, fake_env) (L80): Construct ExclusionsStore; assert lower, path
- TestScannerExclusions.test_clean_refuses_excluded_paths_even_when_asked(self, tmp_path, monkeypatch) (L97): Defense in depth: a stale caller cannot delete an excluded path.
- TestScannerExclusions.test_clean_refuses_excluded_paths_even_when_asked.fake_send2trash(path) (L108): Fake send2trash via append
- TestCleanCancel.test_cancel_event_stops_between_items(self, tmp_path, monkeypatch) (L130): Construct Event; assert exists
- TestCleanCancel.test_cancel_event_stops_between_items.fake_send2trash(path) (L140): Fake send2trash via append, len, set
- TestDisambiguation.test_weaker_name_match_penalised(self, fake_env) (L170): For app 'ZetaEditor', folder 'ZetaEditor' outranks 'ZetaEditorSuite'
- TestSettingsConsent.test_update_check_defaults_off(self, tmp_path) (L204): Construct SettingsStore; assert update_check
- TestSettingsConsent.test_leftover_restore_point_defaults_on(self, tmp_path) (L210): Construct SettingsStore; assert leftover_restore_point
- TestSettingsConsent.test_fields_roundtrip(self, tmp_path) (L216): Construct SettingsStore; assert update_check, leftover_restore_point
- TestSettingsConsent.test_corrupt_file_uses_safe_defaults(self, tmp_path) (L226): Construct SettingsStore; assert update_check, leftover_restore_point
- TestUpdateCheckGate.test_scheduler_noops_without_consent(self, monkeypatch) (L238): No network call may happen unless the user opted in.
- TestUpdateCheckGate.test_scheduler_noops_without_consent.FakeWin.statusBar(self) (L249): StatusBar: build/parse SB; return result
- TestUpdateCheckGate.test_scheduler_noops_without_consent.FakeWin.statusBar.SB.showMessage(self, *a, **k) (L253): ShowMessage: 'showMessage.'
- TestBackupsLeftoverJournals.test_worker_lists_journal_sessions(self, tmp_path, monkeypatch) (L269): Construct FakeRestoreManager; assert len(...)
- TestBackupsLeftoverJournals.test_worker_lists_journal_sessions.FakeRestoreManager.list_manifests(self) (L283): List manifests: 'list_manifests.'; return result

## tests/test_registry_cleaner_ai.py — Tests for the AI registry cleaner's detectors and path resolution.
- test_resolve_target_keeps_unquoted_path_with_spaces() (L47): Exercise _resolve_target; assert _resolve_target(...)
- test_resolve_target_strips_quotes_and_keeps_args_out() (L53): Exercise _resolve_target; assert _resolve_target(...)
- test_resolve_target_expands_system_root_prefix() (L59): Exercise _resolve_target; assert startswith
- test_target_candidates_includes_full_path_first_then_prefixes() (L68): Exercise _target_candidates; assert index
- test_target_candidates_anchors_relative_paths_at_system_roots() (L78): Construct Path; assert is_absolute
- test_verifiable_true_for_missing_but_listable_parent(tmp_path) (L92): Exercise _verifiable; assert _verifiable, str(...)
- test_verifiable_true_for_existing_file(tmp_path) (L97): Exercise write_bytes; assert _verifiable, str(...)
- test_verifiable_false_when_ancestor_listing_denied(tmp_path, monkeypatch) (L104): Construct PermissionError; assert _verifiable, str(...)
- test_verifiable_false_when_ancestor_listing_denied.fake_stat(p, *a, **k) (L110): Fake stat: build PermissionError, via endswith, real_stat; return result
- test_target_exists_treats_unprovable_as_present(tmp_path, monkeypatch) (L122): Construct PermissionError; assert _target_exists, str(...)
- test_target_exists_treats_unprovable_as_present.fake_stat(p, *a, **k) (L128): Fake stat: build PermissionError, via endswith, real_stat; return result
- test_target_exists_false_only_when_provably_missing(tmp_path) (L138): Exercise _target_exists; assert _target_exists, str(...)
- test_font_candidates_anchor_relative_names_at_fonts_dir() (L143): Exercise _font_candidates; assert endswith, lower
- test_font_candidates_keep_absolute_paths() (L150): Exercise _font_candidates
- test_split_returns_64bit_view_for_hklm() (L160): Exercise _split; assert KEY_WOW64_64KEY
- test_split32_returns_32bit_view_for_hklm() (L166): Exercise _split32; assert KEY_WOW64_32KEY
- test_split32_is_none_for_hkcu() (L173): Exercise _split32; assert _split32(...)
- test_split_rejects_unknown_hive() (L178): Exercise raises
- test_detect_missing_path_true_when_target_gone(tmp_path) (L188): Exercise _detect_missing_path; assert _detect_missing_path(...)
- test_detect_missing_path_false_when_target_exists(tmp_path) (L194): Exercise write_bytes; assert _detect_missing_path(...)
- test_detect_missing_path_false_when_default_value_empty() (L202): Exercise _detect_missing_path; assert _detect_missing_path(...)
- test_detect_orphaned_service_skips_boot_and_system_start() (L208): Exercise _detect_orphaned_service; assert REG_DWORD, REG_SZ
- test_detect_orphaned_service_true_when_verifiably_missing(tmp_path) (L219): Exercise str; assert REG_DWORD, REG_SZ
- test_detect_orphaned_service_false_when_image_missing_but_dll_alive(tmp_path) (L227): Exercise write_bytes; assert REG_DWORD, REG_EXPAND_SZ
- test_detect_orphaned_service_true_when_dll_verifiably_missing(tmp_path) (L236): Exercise str; assert REG_DWORD, REG_EXPAND_SZ
- test_detect_orphaned_service_never_guesses_with_no_targets() (L244): Exercise _detect_orphaned_service; assert _detect_orphaned_service(...)
- test_detect_shared_dll_uses_value_names_as_paths(tmp_path) (L249): Exercise write_bytes; assert REG_DWORD
- test_scan_targets_offending_value() (L265): The reported value is the one that proves the orphan.
- test_scan_service_category_never_flags_boot_drivers() (L280): Construct AIRegistryCleaner; assert key_path, value_name
- throwaway_key() (L298): A test key under HKCU removed after each test.
- _cleaner(tmp_path) (L309): cleaner: build AIRegistryCleaner, via _P; return result
- test_clean_deletes_value_level_orphan(throwaway_key, tmp_path) (L318): Construct RegistryIssue; assert cleaned
- test_clean_deletes_key_level_orphan(throwaway_key, tmp_path) (L337): Construct RegistryIssue; assert cleaned
- test_clean_backs_up_before_deleting(throwaway_key, tmp_path) (L352): Construct RegistryIssue; assert cleaned, backup_path
- test_clean_refuses_delete_when_subkeys_present(throwaway_key, tmp_path) (L372): Construct RegistryIssue; assert cleaned, failed
- test_clean_keep_recommendation_is_not_deleted(throwaway_key, tmp_path) (L389): Construct RegistryIssue; assert cleaned, QueryValueEx

## tests/test_release_infra.py — Tests for the release infrastructure helpers.
- TestParseVersion.test_plain_and_v_prefixed(self) (L18): Exercise parse_version; assert parse_version(...)
- TestParseVersion.test_unparseable_tags_return_none(self, bad) (L27): Exercise parametrize; assert parse_version(...)
- TestCheckForUpdate._patch_fetch(self, monkeypatch, tag) (L35): patch fetch via setattr
- TestCheckForUpdate.test_update_available_when_latest_is_newer(self, monkeypatch) (L41): Exercise _patch_fetch
- TestCheckForUpdate.test_up_to_date_when_equal_or_older(self, monkeypatch) (L50): Exercise _patch_fetch; assert check_for_update(...)
- TestCheckForUpdate.test_offline_reports_unknown_never_raises(self, monkeypatch) (L58): Exercise _patch_fetch
- TestCheckForUpdate.test_unparseable_remote_tag_is_unknown(self, monkeypatch) (L65): Exercise _patch_fetch; assert check_for_update(...)
- TestCrashReport.test_excepthook_writes_crash_file(self, tmp_path, monkeypatch) (L74): The excepthook persists a redact-flagged crash report file.

## tests/test_restore_point.py — Tests for the Windows restore-point safety module.
- TestResultSemantics.test_created_flags(self) (L23): Construct RestorePointResult; assert created, ok_to_proceed
- TestResultSemantics.test_throttled_is_ok_to_proceed(self) (L29): Construct RestorePointResult; assert created, ok_to_proceed
- TestResultSemantics.test_disabled_and_not_elevated_block_proceed(self) (L36): Construct RestorePointResult; assert ok_to_proceed, PROTECTION_DISABLED, NOT_ELEVATED, FAILED
- TestResultSemantics.test_to_dict(self) (L42): Construct RestorePointResult
- TestOutputParsing.test_parse_created(self) (L50): Construct RestorePointManager._parse_create_output; assert status, CREATED
- TestOutputParsing.test_parse_throttled(self) (L55): Construct RestorePointManager._parse_create_output; assert status, THROTTLED
- TestOutputParsing.test_parse_protection_disabled(self) (L60): Construct RestorePointManager._parse_create_output; assert status, PROTECTION_DISABLED
- TestOutputParsing.test_parse_failed_with_message(self) (L65): Construct RestorePointManager._parse_create_output; assert status, FAILED, message
- TestOutputParsing.test_parse_empty_is_failed(self) (L71): Construct RestorePointManager._parse_create_output; assert status, FAILED, _parse_create_output
- TestOutputParsing.test_parse_garbage_is_failed(self) (L76): Construct RestorePointManager._parse_create_output; assert status, FAILED, _parse_create_output
- TestWmiTimeParsing.test_wmi_datetime(self) (L83): Construct RestorePointManager._parse_wmi_time; assert _parse_wmi_time
- TestWmiTimeParsing.test_empty(self) (L87): Construct RestorePointManager._parse_wmi_time; assert _parse_wmi_time
- TestWmiTimeParsing.test_passthrough_non_wmi(self) (L92): Construct RestorePointManager._parse_wmi_time; assert _parse_wmi_time
- TestCapabilities.test_is_supported_matches_platform(self) (L99): Construct RestorePointManager.is_supported; assert is_supported
- TestCapabilities.test_is_elevated_returns_bool(self) (L103): Construct RestorePointManager.is_elevated; assert is_elevated
- TestCapabilities.test_list_points_returns_list(self) (L107): Construct RestorePointManager; assert list_points
- TestCapabilities.test_create_non_windows_is_not_supported(self) (L112): Construct RestorePointManager; assert status, NOT_SUPPORTED
- TestCapabilities.test_create_without_admin_reports_not_elevated(self) (L120): Construct RestorePointManager; assert status, NOT_ELEVATED, created

## tests/test_s3_fifo.py — Tests for S3-FIFO cache (SOSP'23).
- test_basic_put_get() (L10): Construct S3FIFO; assert get
- test_update_existing_increments_freq() (L18): Construct S3FIFO; assert get
- test_ghost_promotion() (L27): Construct S3FIFO; assert contains, _ghost_contains, stats
- test_freq_bumps_and_main_reinsertion() (L44): Construct S3FIFO
- test_capacity_respected() (L63): Construct S3FIFO; assert stats
- test_delete_and_clear() (L72): Construct S3FIFO; assert contains, delete, stats
- test_stats_hit_ratio() (L87): Construct S3FIFO; assert approx
- test_invalid_capacity() (L99): Construct S3FIFO
- test_quick_demotion_one_hit_wonders_evicted_early() (L107): One-hit wonders (freq 0) inserted to Small should go to Ghost, not Main.
- test_two_hits_promoted_to_main() (L122): Construct S3FIFO; assert contains, _ghost_contains

## tests/test_scanner.py — Tests for the filesystem Scanner component.
- test_scanner_finds_empty_files(test_env, clean_config) (L7): Test that scanner identifies empty files correctly.
- test_scanner_finds_empty_dirs(test_env, clean_config) (L18): Test that scanner identifies empty directories correctly.
- test_scanner_exclude_patterns(test_env, clean_config) (L29): Test that scanner respects exclude patterns.
- test_scanner_stats(test_env, clean_config) (L40): Test that scanner calculates statistics correctly.

## tests/test_search_index_optimizer.py — Unit tests for Windows SearchIndexOptimizer.
- test_search_index_get_status() (L12): Construct SearchIndexOptimizer.get_status; assert service_status
- test_operation_result_structure() (L19): Construct SearchIndexOperationResult; assert success, bytes_freed, errors

## tests/test_secrets_page.py — Verify the secrets scanner detects a planted credential and stays offline.
- test_run_scan_detects_planted_aws_key(tmp_path) (L6): Exercise write_text; assert files_scanned, findings, lower
- test_worker_emits_offline(tmp_path) (L27): Construct SecretsScanWorker; assert isinstance(...)
- test_secrets_scan_makes_no_network_calls(tmp_path, monkeypatch) (L45): Offline guarantee: block urllib entirely; the scan must still succeed,
- test_secrets_scan_makes_no_network_calls._blocked(*args, **kwargs) (L51): blocked: build/parse AssertionError

## tests/test_secure_delete_batch.py — Tests for the batched recycle path (production performance + correctness).
- _make_files(base, n) (L17): make files via write_bytes; loop over range(n); return result
- test_batch_recycle_removes_all_and_reports_progress(tmp_path) (L28): Construct SecureDeleter; assert outcome, RECYCLED, exists
- test_batch_recycle_cancel_stops_early(tmp_path) (L43): Construct SecureDeleter; assert exists
- test_batch_recycle_reports_freed_bytes(tmp_path) (L56): Construct SecureDeleter
- test_fast_delete_batch_uses_known_sizes_and_removes_files(tmp_path) (L64): The optimized DELETE path deletes files, reports freed bytes from the
- test_fast_delete_batch_cancel_stops_early(tmp_path) (L82): Construct SecureDeleter; assert exists
- test_fast_delete_batch_dry_run_deletes_nothing(tmp_path) (L93): Construct SecureDeleter; assert outcome, WOULD_DELETE, exists

## tests/test_secure_shredder.py — Tests for the secure file shredder (DoD, Gutmann, NIST, etc.).
- _make_file(base, name: str, content: bytes=b'secret data 12345') -> str (L34): make file via write_bytes; return result
- _read_all(path: str) -> bytes (L41): read all via open, read; return result
- _patch_storage(monkeypatch) (L49): Always report HDD so auto-detect chooses DoD 3-pass.
- TestShredStandard.test_all_expected_standards_exist(self) (L64): Verify all expected standards exist
- TestShredStandard.test_member_count_at_least_17(self) (L88): Exercise len; assert len(...)
- TestShredStandard.test_pass_count_varies(self) (L92): Verify pass count varies (GUTMANN, NIST_CLEAR, DOD_5220_22_M, DOD_5220_22_M_ECE)
- TestShredStandard.test_gutmann_has_exactly_35_passes(self) (L111): Exercise len; assert len(...)
- TestShredStandard.test_name_property_returns_human_readable(self) (L118): Verify name property returns human readable (name, NIST_CLEAR, DOD_5220_22_M, GUTMANN)
- TestShredStandard.test_recommended_for_ssd(self) (L124): Construct ShredStandard.NIST_CLEAR.recommended_for; assert recommended_for, SSD_NVME, NIST_CLEAR, SSD_SATA, RANDOM_1PASS
- TestShredStandard.test_recommended_for_hdd(self) (L130): Construct ShredStandard.DOD_5220_22_M.recommended_for; assert recommended_for, HDD, DOD_5220_22_M, NIST_CLEAR, GUTMANN
- TestShredStandard.test_recommended_for_unknown_always_true(self) (L136): Exercise recommended_for; assert recommended_for, UNKNOWN
- TestShredStandard.test_all_passes_have_pattern_and_verify_keys(self) (L141): Verify all passes have pattern and verify keys
- TestShredStandard.test_last_pass_always_verifies(self) (L148): Every standard's final pass should verify so failures are detected.
- TestStorageType.test_all_values(self) (L163): Verify all values (value)
- TestStorageType.test_member_count(self) (L168): Exercise len; assert len(...)
- TestShredResult.test_success_result_fields(self) (L180): Construct ShredResult; assert success, passes_completed, error
- TestShredResult.test_failure_result_with_error(self) (L195): Construct ShredResult; assert error
- TestShredResult.test_to_dict_serializes_standard(self) (L209): Construct ShredResult
- TestShredResult.test_to_dict_all_expected_keys(self) (L225): Construct ShredResult; assert keys
- TestShredResult.test_frozen_dataclass(self) (L248): Construct ShredResult
- TestSecureShredderInit.test_default_init(self) (L270): Construct SecureShredder; assert verify_passes, dry_run, sample_pct, cancel_event
- TestSecureShredderInit.test_custom_init(self) (L278): Construct SecureShredder; assert verify_passes, dry_run, sample_pct, cancel_event
- TestShredFileBasic.test_shred_nonexistent_file_returns_failure(self) (L301): Construct SecureShredder; assert success, lower, error
- TestShredFileBasic.test_shred_zero_byte_file(self, tmp_path) (L308): Construct SecureShredder; assert success, passes_completed, bytes_shredded, exists, path
- TestShredFileBasic.test_shred_reports_correct_byte_count(self, tmp_path) (L318): Construct SecureShredder; assert bytes_shredded
- TestShredFileBasic.test_shred_duration_non_negative(self, tmp_path) (L325): Construct SecureShredder; assert duration_seconds
- TestShredFileBasic.test_shred_random_1pass_removes_file(self, tmp_path) (L331): Construct SecureShredder; assert success, exists, path
- TestShredFileBasic.test_shred_nist_clear_removes_file(self, tmp_path) (L338): Construct SecureShredder; assert success, exists, path
- TestShredFileBasic.test_shred_random_3pass_removes_file(self, tmp_path) (L345): Construct SecureShredder; assert success, exists, path
- TestShredRandomOnlyStandards.test_nist_clear_1_pass(self, tmp_path) (L361): Construct SecureShredder; assert passes_completed, success
- TestShredRandomOnlyStandards.test_random_1pass(self, tmp_path) (L368): Construct SecureShredder; assert passes_completed, success
- TestShredRandomOnlyStandards.test_random_3pass(self, tmp_path) (L377): Construct SecureShredder; assert passes_completed, success
- TestBytePatternStandards.test_shred_fails_with_type_error(self, tmp_path, standard) (L410): Construct SecureShredder; assert success, error
- TestGutmannPartialProgress.test_gutmann_fails_after_4_random_passes(self, tmp_path) (L425): Gutmann has 4 random passes before first byte pattern.
- TestVerifyOption.test_verify_disabled_random_1pass_succeeds(self, tmp_path) (L441): Construct SecureShredder; assert success
- TestVerifyOption.test_verify_enabled_random_1pass_fails_verification(self, tmp_path) (L449): Random verification regenerates different bytes, so always fails on small files.
- TestVerifyOption.test_verify_disabled_prevents_crash_on_byte_patterns(self, tmp_path) (L456): With verify off, byte-pattern standards still crash in _write_pass.
- TestProgressCallback.test_progress_called_for_random_1pass(self, tmp_path) (L470): Construct SecureShredder; assert len(...)
- TestProgressCallback.test_progress_called_for_random_3pass(self, tmp_path) (L482): Construct SecureShredder; assert len(...)
- TestProgressCallback.test_progress_totals_match_standard(self, tmp_path) (L496): Construct SecureShredder; assert all(...)
- TestProgressCallback.test_progress_called_once_for_byte_standard_before_crash(self, tmp_path) (L507): Byte-pattern standard calls progress once then crashes in _write_pass.
- TestCancellation.test_cancel_before_start_prevents_shred(self, tmp_path) (L525): Construct SecureShredder; assert success, lower, error
- TestCancellation.test_cancel_during_shred_stops_early(self, tmp_path) (L536): Construct SecureShredder; assert success, lower, error, passes_completed
- TestCancellation.test_cancel_during_shred_stops_early.progress_fn(msg, cur, total) (L542): Progress fn via set
- TestCancellation.test_cancel_in_shred_files_stops_batch(self, tmp_path) (L558): Construct SecureShredder; assert exists, path
- TestShredFilesBatch.test_batch_shreds_all_random_1pass(self, tmp_path) (L576): Construct SecureShredder; assert success, exists, path
- TestShredFilesBatch.test_batch_empty_list(self) (L586): Construct SecureShredder
- TestShredFilesBatch.test_batch_cancelled_event_returns_empty(self, tmp_path) (L591): Construct SecureShredder; assert exists, path
- TestDryRun.test_dry_run_does_not_remove_random_standard(self, tmp_path) (L610): Construct SecureShredder; assert success, exists, path
- TestDryRun.test_dry_run_zero_byte_file_not_removed(self, tmp_path) (L620): Zero-byte files are only unlinked when dry_run is False.
- TestDryRun.test_dry_run_nonzero_byte_file_size_unchanged(self, tmp_path) (L627): Construct SecureShredder; assert getsize, path
- TestAutoDetect.test_auto_detect_uses_hdd_standard(self, tmp_path) (L644): With HDD monkeypatched, auto-detect should pick DoD 3-pass.
- TestAutoDetect.test_auto_detect_disabled_defaults_to_nist_clear(self, tmp_path) (L651): Construct SecureShredder; assert standard, NIST_CLEAR, success
- TestPatternBytes.test_random_returns_correct_length(self) (L668): Exercise _pattern_bytes; assert len(...)
- TestPatternBytes.test_random_returns_different_bytes(self) (L673): Exercise _pattern_bytes
- TestPatternBytes.test_int_pattern(self) (L679): Exercise _pattern_bytes
- TestPatternBytes.test_int_pattern_0xff(self) (L684): Exercise _pattern_bytes
- TestPatternBytes.test_crypto_erase_returns_empty(self) (L689): Exercise _pattern_bytes; assert _pattern_bytes(...)
- TestPatternBytes.test_block_erase_returns_empty(self) (L693): Exercise _pattern_bytes; assert _pattern_bytes(...)
- TestPatternBytes.test_random_prefix_pattern(self) (L697): Exercise _pattern_bytes; assert len(...)
- TestPatternBytes.test_bytes_pattern_raises_type_error(self) (L702): Known bug: operator precedence on line 288 slices the int, not bytes.
- TestPatternBytes.test_bytes_multibyte_pattern_raises_type_error(self) (L707): Exercise raises
- TestPatternBytes.test_bytes_pattern_single_byte_also_raises(self) (L712): Exercise raises
- TestVerifyPattern.test_crypto_erase_always_true(self, tmp_path) (L725): Exercise _verify_pattern; assert _verify_pattern(...)
- TestVerifyPattern.test_block_erase_always_true(self, tmp_path) (L729): Exercise _verify_pattern; assert _verify_pattern(...)
- TestVerifyPattern.test_random_on_small_file_returns_false(self, tmp_path) (L733): Random verify regenerates different bytes → always False for small files.
- TestVerifyPattern.test_nonexistent_file_returns_false(self) (L739): Exercise _verify_pattern; assert _verify_pattern(...)
- TestVerifyPattern.test_byte_pattern_verify_returns_false(self, tmp_path) (L743): Byte patterns hit _pattern_bytes bug; verify catches it and returns False.
- TestFileSizeEdgeCases.test_single_byte_file_random(self, tmp_path) (L756): Construct SecureShredder; assert success, bytes_shredded
- TestFileSizeEdgeCases.test_64k_file_random_3pass(self, tmp_path) (L765): Construct SecureShredder; assert success, bytes_shredded, passes_completed
- TestFileSizeEdgeCases.test_1mb_file_nist_clear(self, tmp_path) (L775): Construct SecureShredder; assert success, bytes_shredded
- TestGutmannStructure.test_first_four_passes_are_random(self) (L790): Exercise range; assert passes, GUTMANN
- TestGutmannStructure.test_passes_5_to_31_are_deterministic_bytes(self) (L795): Exercise range; assert isinstance(...)
- TestGutmannStructure.test_last_four_passes_are_random(self) (L801): Exercise range; assert passes, GUTMANN
- TestGutmannStructure.test_only_final_pass_verifies(self) (L806): Exercise all; assert all(...)

## tests/test_security_fixes.py — Regression tests for the shell-injection and no-op-stub fixes.
- TestCustomCommandHardening.test_disabled_by_default(self) (L14): Construct AutoCleanRules; assert get
- TestCustomCommandHardening.test_runs_without_shell_when_allowed(self) (L21): Construct AutoCleanRules; assert get
- TestCustomCommandHardening.test_metacharacters_not_interpreted(self, tmp_path) (L33): With shell=False, a chained '&& <malicious>' cannot execute.
- TestAppUninstallerImportSafe.test_import_and_construct(self) (L49): Construct AppUninstaller; assert isinstance(...)
- TestAppUninstallerImportSafe.test_uninstall_missing_string_returns_false(self) (L58): Construct AppUninstaller; assert uninstall_app

## tests/test_shutdown_safety.py — Worker-shutdown safety: never call ``QThread.terminate()``.
- app() (L35): App: build QApplication.instance, via fixture; return result
- window(app) (L41): Window: build PremiumMainWindow, via apply_theme
- _CooperativeWorker.__init__(self, poll_s: float=0.05) (L61): Initialize _cancel, _poll_s
- _CooperativeWorker.cancel(self) -> None (L67): Cancel via set
- _CooperativeWorker.run(self) -> None (L71): Run via emit, is_set; loop over range(200)
- _StubbornWorker.__init__(self, sleep_s: float=30.0) (L90): Initialize cancel_called, _sleep_s
- _StubbornWorker.cancel(self) -> None (L96): Cancel via set
- _StubbornWorker.run(self) -> None (L100): Run via emit
- test_cooperative_worker_lets_close_return_promptly(app, window) (L106): Exercise _CooperativeWorker; assert _CLOSE_GRACE_S
- _wait_for_natural_completion(thread, timeout_s: float=15.0) -> None (L120): Let a detached-but-still-running QThread finish on its own.
- test_uncooperative_worker_is_detached_not_terminated(app, window) (L136): Exercise _StubbornWorker; assert is_set, cancel_called, _CLOSE_GRACE_S, _threads
- test_shutdown_workers_never_calls_terminate(app, window, monkeypatch) (L163): Guard against the unsafe fallback ever being reintroduced.
- test_shutdown_workers_never_calls_terminate._tracking_terminate(self) (L170): tracking terminate via original; return result
- test_multiple_workers_shut_down_within_one_shared_deadline(app, window) (L188): Several workers must be waited on concurrently, not N times serially.

## tests/test_sidebar_chevrons_and_icons.py — Regression tests for sidebar navigation expand/collapse chevrons and icon color consistency.
- app() (L17): App: build QApplication.instance, via fixture; return result
- test_sidebar_group_headers_have_valid_chevrons_and_escaped_titles(app) (L22): Every group header must have a valid SVG chevron and no raw underscore mnemonics.
- test_sidebar_expand_collapse_preserves_chevrons(app) (L49): Expanding and collapsing the sidebar must never erase header chevrons or text.
- test_all_132_pages_have_unique_icons_with_uniform_palette_tint(app) (L74): All 132 page icons must be distinct and uniformly tinted to the theme color.

## tests/test_sieve_cache.py — Unit tests for the NSDI 2024 SIEVE Cache Algorithm.
- test_sieve_basic_put_get() (L8): Exercise put; assert get, size
- test_sieve_eviction_order() (L22): Verify SIEVE eviction semantics:
- test_sieve_stats_and_hit_ratio() (L46): Exercise put
- test_sieve_delete_and_clear() (L66): Exercise put; assert delete, size, get
- test_sieve_concurrency_safety() (L80): Exercise range; assert size
- test_sieve_concurrency_safety.worker(offset: int) (L84): Worker via put; loop over range(100)

## tests/test_smart_suggest.py — Tests for the offline Smart Suggestions learning engine.
- _ctx(category='user_temp', ext='tmp', size=5000000, age=40, path='C:/Users/x/AppData/Local/Temp/f.tmp') (L13): ctx: '_ctx.'; return result
- TestFeaturize.test_includes_bias_and_known_features(self) (L20): Exercise featurize; assert startswith
- TestFeaturize.test_handles_sparse_context(self) (L30): Exercise featurize; assert featurize(...)
- TestLearning.test_score_in_unit_interval(self, tmp_path) (L38): Construct SmartSuggester; assert score
- TestLearning.test_learns_to_favor_accepted_pattern(self, tmp_path) (L43): Construct SmartSuggester
- TestLearning.test_learns_to_avoid_skipped_pattern(self, tmp_path) (L55): Construct SmartSuggester; assert score
- TestLearning.test_recommend_defaults_true_until_trained(self, tmp_path) (L63): Construct SmartSuggester; assert recommend
- TestLearning.test_rank_orders_by_score(self, tmp_path) (L69): Construct SmartSuggester
- TestBoundsAndPersistence.test_model_size_is_capped(self, tmp_path) (L83): Construct SmartSuggester; assert _MAX_FEATURES, stats
- TestBoundsAndPersistence.test_save_and_reload_roundtrip(self, tmp_path) (L92): Construct SmartSuggester; assert save, exists, score, stats
- TestBoundsAndPersistence.test_corrupt_model_does_not_crash(self, tmp_path) (L106): Construct SmartSuggester; assert stats
- TestBoundsAndPersistence.test_reset(self, tmp_path) (L113): Construct SmartSuggester; assert stats

## tests/test_srum_bam_cleaner.py — Unit and integration tests for Windows BAM/DAM and SRUM forensic cleaner.
- test_filetime_conversion() (L15): Construct SrumBamCleaner._filetime_to_datetime
- test_srum_query() (L34): Construct SrumBamCleaner; assert endswith, db_path
- test_srum_bam_scan() (L42): Construct SrumBamCleaner; assert isinstance(...)
- test_clean_bam_empty() (L52): Construct SrumBamCleaner

## tests/test_staging_shelf.py — Tests for the Interactive Staging Shelf & Clipboard Dock in NexusExplorer.
- qapp() (L15): Qapp: build QApplication.instance, via fixture; return result
- test_nexus_clipboard_cut_copy_clear(qapp) (L23): Construct NexusClipboard; assert has_data, paste
- test_staging_shelf_widget_basic(qapp) (L50): Construct StagingShelfWidget; assert _staged_paths, isHidden, empty_card, list_widget, isEnabled
- test_staging_shelf_paste_requested_signal(qapp) (L101): Construct StagingShelfWidget; assert _norm
- test_preview_pane_with_staging_shelf(qapp) (L125): Construct PreviewPane; assert _current_dir, staging_shelf, text, name_lbl, _staged_paths
- test_file_table_model_drag_mime_data(qapp) (L146): Construct FileTableModel; assert ItemIsDragEnabled, ItemFlag, hasUrls
- test_staged_item_row_attributes_and_drag(qapp) (L167): Construct StagedItemRow; assert text, name_lbl, testAttribute, WA_TransparentForMouseEvents, WidgetAttribute
- test_python_transfer_fallback_copy_and_move(qapp) (L185): Construct TransferQueue; assert exists, read_text
- test_context_menu_paste_option(qapp) (L220): Construct ExplorerWidget; assert has_data
- test_python_transfer_locked_file_handling(qapp) (L247): Construct TransferQueue; assert exists
- test_python_transfer_locked_file_handling._mock_open(file, *args, **kwargs) (L273): mock open: build PermissionError, via orig_open; return result
- test_preview_pane_transfer_dock_integration(qapp) (L294): Construct PreviewPane; assert isHidden, transfer_dock, text, badge_lbl, value
- test_read_only_delete_retry(qapp) (L332): Construct TransferQueue; assert exists
- test_transfer_queue_is_busy_property(qapp) (L366): Construct TransferQueue; assert is_busy
- test_staging_shelf_drag_and_drop_onto_empty_state(qapp) (L380): Construct ExplorerWidget; assert isAccepted
- test_file_checksum_dialog(qapp) (L416): Construct FileChecksumDialog; assert _hashes, text, match_lbl

## tests/test_startup_imports.py — Startup-cost and public-API contracts for the package import root.
- _run(code: str) -> str (L32): Execute *code* in a clean interpreter and return its stdout.
- test_package_import_does_not_load_heavy_dependencies() (L50): ``import cortex_unified`` must stay cheap for every entry point.
- test_engine_import_does_not_load_recycle_bin_stack() (L62): A read-only engine import must not load the recycle-bin COM stack.
- test_engine_public_api_still_imports() (L74): The lazy-import work must not break the engine's public surface.
- test_legacy_convenience_exports_still_resolve() (L83): ``from cortex_unified import Scanner`` must keep working (PEP 562).
- test_version_is_importable_without_side_effects() (L92): ``__version__`` is read by the CLI and logging setup at import time.
- test_unknown_attribute_still_raises_attribute_error() (L102): Lazy resolution must not turn typos into ImportError or hangs.
- test_has_trash_flag_contract_preserved() (L114): ``_HAS_TRASH`` is imported directly by tests; keep it resolvable.
- test_legacy_cli_import_does_not_load_optional_heavy_sdks() (L133): Building the command tree must not import per-command dependencies.
- test_legacy_cli_still_exposes_every_command() (L145): Deferring imports must not drop or rename any command.
- test_legacy_cli_registry_flag_contract_preserved() (L161): ``HAS_REGISTRY_CLEANER`` was a module constant; keep it readable.
- test_legacy_cli_unknown_attribute_raises_attribute_error() (L170): The module ``__getattr__`` must not mask typos.

## tests/test_startup_optimizer.py — Tests for the startup optimizer — enumeration, delays, persistence, cancel.
- TestAppType.test_all_members(self) (L32): Verify all members
- TestAppType.test_member_count(self) (L37): Exercise len; assert len(...)
- TestStartupEntry.test_required_fields_exist(self) (L65): Exercise fields; assert REQUIRED_FIELDS
- TestStartupEntry.test_optional_fields_exist(self) (L70): Exercise fields; assert OPTIONAL_FIELDS
- TestStartupEntry.test_defaults(self) (L75): Construct StartupEntry; assert publisher, delay_seconds, launch_conditions, is_gui_heavy, is_network_bound
- TestStartupEntry.test_to_dict_round_trip(self) (L93): Construct StartupEntry; assert isinstance(...)
- TestStartupEntry.test_slots_prevents_arbitrary_attr(self) (L112): Construct StartupEntry
- TestInit.test_default_progress_and_cancel(self) (L132): Construct StartupOptimizer; assert progress, cancel, Event, is_set
- TestInit.test_custom_progress_and_cancel(self) (L139): Construct StartupOptimizer; assert is_set, cancel
- TestConfigPath.test_config_path_is_json(self, tmp_path, monkeypatch) (L155): Exercise setenv; assert suffix, exists, parent
- TestConfigPath.test_config_path_creates_dirs(self, tmp_path, monkeypatch) (L162): Exercise setenv; assert exists, parent
- TestPersistence.test_load_delays_missing_file(self, tmp_path, monkeypatch) (L174): Construct StartupOptimizer; assert _load_delays
- TestPersistence.test_save_and_load_round_trip(self, tmp_path, monkeypatch) (L180): Construct StartupOptimizer
- TestPersistence.test_load_corrupt_json_returns_empty(self, tmp_path, monkeypatch) (L189): Construct StartupOptimizer; assert _load_delays
- TestDelayOperations.test_set_delay_persists(self, tmp_path, monkeypatch) (L203): Construct StartupOptimizer
- TestDelayOperations.test_set_delay_clamps_to_0_120(self, tmp_path, monkeypatch) (L211): Construct StartupOptimizer; assert _load_delays
- TestDelayOperations.test_set_delay_with_conditions(self, tmp_path, monkeypatch) (L220): Construct StartupOptimizer
- TestDelayOperations.test_remove_delay(self, tmp_path, monkeypatch) (L229): Construct StartupOptimizer; assert _load_delays
- TestDelayOperations.test_remove_delay_nonexistent_is_noop(self, tmp_path, monkeypatch) (L237): Construct StartupOptimizer; assert _load_delays
- TestRegistryEnumeration.test_empty_on_no_keys(self, monkeypatch) (L250): Construct FileNotFoundError; expect exception
- TestRegistryEnumeration.test_empty_on_no_keys.fake_open(hive, sub, reserved, access) (L254): Fake open: build/parse FileNotFoundError
- TestRegistryEnumeration.test_returns_entries(self, monkeypatch) (L262): Construct StartupOptimizer; assert name, enabled
- TestRegistryEnumeration.test_returns_entries.FakeKey.__enter__(self) (L270): enter  : '__enter__.'; return result
- TestRegistryEnumeration.test_returns_entries.FakeKey.__exit__(self, *a) (L274): exit  : '__exit__.'
- TestRegistryEnumeration.test_returns_entries.fake_open(hive, sub, reserved, access) (L278): Fake open: build/parse FakeKey; return result
- TestRegistryEnumeration.test_returns_entries.fake_enum(key, i) (L282): Fake enum: build/parse OSError; return result
- TestRegistryEnumeration.test_returns_entries.patched_reg() (L308): Patched reg: build StartupEntry, via hash; return result
- TestStartupFolderEnumeration.test_no_env_vars_returns_empty(self, monkeypatch) (L335): Exercise delenv
- TestStartupFolderEnumeration.test_finds_lnk_files(self, tmp_path, monkeypatch) (L342): Construct StartupEntry; assert name
- TestStartupFolderEnumeration.test_finds_lnk_files.patched() (L352): Patched: build StartupEntry, via iterdir, is_file; loop over startup.iterdir(); return result
- TestClassifyEntry.test_nonexistent_exe_no_change(self, tmp_path) (L381): Construct StartupEntry; assert is_gui_heavy, is_network_bound, is_service_dependent
- TestClassifyEntry.test_pe_with_gui_symbols(self, tmp_path) (L397): Construct StartupEntry; assert is_gui_heavy
- TestClassifyEntry.test_pe_with_network_symbols(self, tmp_path) (L414): Construct StartupEntry; assert is_network_bound
- TestClassifyEntry.test_pe_with_service_symbols(self, tmp_path) (L430): Construct StartupEntry; assert is_service_dependent
- TestImpactRating._make_opt_with_mock_enumerate(self, tmp_path, monkeypatch) (L459): make opt with mock enumerate: build StartupOptimizer, via setenv; return result
- TestImpactRating.test_impact_low_for_small_exe(self, tmp_path, monkeypatch) (L476): Construct StartupOptimizer; assert impact
- TestImpactRating.test_impact_low_for_small_exe.fake_reg() (L481): Fake reg: build/parse StartupEntry; return result
- TestImpactRating.test_impact_high_for_large_exe(self, tmp_path, monkeypatch) (L512): Construct StartupOptimizer; assert impact
- TestImpactRating.test_impact_high_for_large_exe.fake_reg() (L518): Fake reg: build StartupEntry, via str; return result
- TestBackupRestore.test_backup_creates_file(self, tmp_path, monkeypatch) (L555): Construct StartupOptimizer; assert exists
- TestBackupRestore.test_restore_overwrites_current(self, tmp_path, monkeypatch) (L566): Construct StartupOptimizer
- TestProgressCallback.test_progress_called_on_enumerate_error(self, tmp_path, monkeypatch) (L583): Construct StartupOptimizer; assert any(...)
- TestProgressCallback.test_progress_called_on_enumerate_error.boom() (L588): Boom: build/parse RuntimeError
- TestCancellation.test_cancel_stops_launch(self, tmp_path, monkeypatch) (L614): Construct StartupOptimizer
- TestCancellation.test_cancel_mid_loop(self, tmp_path, monkeypatch) (L638): Construct StartupOptimizer
- TestCancellation.test_cancel_mid_loop.cancel_soon() (L643): Cancel soon via set
- TestStartupLocations.test_locations_list_not_empty(self) (L680): Exercise len; assert len(...)
- TestStartupLocations.test_all_entries_have_valid_prefix(self) (L684): Exercise startswith; assert startswith
- TestStartupLocations.test_categories_are_known(self) (L689): Verify categories are known
- TestExports.test_all_contains_expected(self) (L701): Exercise set; assert __all__

## tests/test_storage_sense.py — Tests for the Storage Sense config reader (interpretation + gating).
- TestInterpret.test_unconfigured(self) (L14): Construct StorageSense._interpret
- TestInterpret.test_enabled_weekly(self) (L20): Construct StorageSense._interpret
- TestInterpret.test_recycle_bin_config(self) (L27): Construct StorageSense._interpret
- TestInterpret.test_downloads_config(self) (L34): Construct StorageSense._interpret
- TestInterpret.test_low_space_cadence(self) (L40): Construct StorageSense._interpret
- TestInterpret.test_unknown_cadence_is_custom(self) (L45): Construct StorageSense._interpret
- TestValidation.test_set_cadence_rejects_bad(self) (L53): Construct StorageSense; assert lower
- TestValidation.test_set_recycle_days_rejects_bad(self) (L58): Construct StorageSense
- TestSupport.test_is_supported(self) (L66): Construct StorageSense.is_supported; assert is_supported
- TestSupport.test_get_status_shape(self) (L70): Construct StorageSense

## tests/test_system_info.py — Tests for the read-only System Information collector.
- test_platform_info_has_core_fields() (L8): Construct SystemInfo
- test_snapshot_structure() (L16): Construct SystemInfo; assert isinstance(...)
- test_memory_info_sane() (L24): Construct SystemInfo
- test_disk_info_entries_sane() (L33): Construct SystemInfo
- test_cpu_info_sane() (L41): Construct SystemInfo

## tests/test_system_repair.py — Tests for the SFC/DISM/CHKDSK repair orchestrator (parsers + gating).
- TestSfcParse.test_clean(self) (L19): Construct SystemRepair._parse_sfc; assert success, status
- TestSfcParse.test_repaired(self) (L25): Construct SystemRepair._parse_sfc; assert success, needs_reboot, status
- TestSfcParse.test_partial(self) (L32): Construct SystemRepair._parse_sfc; assert success, status, lower, message
- TestSfcParse.test_error_when_none(self) (L40): Construct SystemRepair._parse_sfc; assert success, lower, message
- TestDismParse.test_clean(self) (L48): Construct SystemRepair._parse_dism; assert success, status
- TestDismParse.test_repairable(self) (L53): Construct SystemRepair._parse_dism; assert success, status, lower, message
- TestDismParse.test_repaired(self) (L59): Construct SystemRepair._parse_dism; assert success, needs_reboot, status
- TestDismParse.test_error_code(self) (L65): Construct SystemRepair._parse_dism; assert success, message
- TestChkdskParse.test_clean(self) (L74): Construct SystemRepair._parse_chkdsk; assert success, status
- TestChkdskParse.test_errors(self) (L80): Construct SystemRepair._parse_chkdsk; assert needs_reboot, status
- TestChkdskParse.test_invalid_drive(self) (L86): Construct SystemRepair; assert success
- TestGating.test_is_supported(self) (L94): Construct SystemRepair.is_supported; assert is_supported
- TestGating.test_is_elevated_bool(self) (L98): Construct SystemRepair.is_elevated; assert is_elevated
- TestGating.test_dism_invalid_action_defaults(self) (L102): Construct SystemRepair._parse_dism; assert isinstance(...)
- TestDecode.test_utf16_with_nuls(self) (L113): Construct SystemRepair._decode
- TestDecode.test_plain_utf8(self) (L119): Construct SystemRepair._decode; assert _decode
- TestDecode.test_empty(self) (L123): Construct SystemRepair._decode; assert _decode

## tests/test_tablemodel.py — Contracts for the model/view table foundation.
- app() (L37): App: build QApplication.instance, via fixture; return result
- _records(count=6) (L42): records: '_records.'; return result
- _columns() (L50): columns: build/parse Column; return result
- binding(app) (L65): Binding: build QTableView, via bind_table, set_records; return result
- test_model_reports_shape_from_records_and_columns(binding) (L78): Exercise rowCount; assert rowCount, proxy, columnCount, headerData, Horizontal
- test_display_supports_field_names_and_callables(binding) (L89): Exercise data; assert data, DisplayRole, index, ItemDataRole
- test_missing_field_renders_empty_not_none(app) (L98): Construct RecordTableModel; assert data, DisplayRole, index, ItemDataRole
- test_cells_are_read_only(binding) (L105): Exercise flags; assert ItemIsEditable, ItemFlag, ItemIsSelectable
- test_sorting_uses_the_typed_key_not_the_display_string(binding) (L115): ``"9.0 MB"`` must not sort above ``"100.0 MB"``.
- test_sort_role_exposes_the_raw_value(binding) (L125): Exercise data; assert isinstance(...)
- test_filter_matches_searchable_columns_only(binding) (L135): Exercise set_filter_text; assert rowCount, proxy
- test_filter_is_case_insensitive_and_clearable(binding) (L148): Exercise set_filter_text; assert rowCount, proxy
- test_filtering_does_not_discard_the_records(binding) (L156): Exercise set_filter_text; assert rowCount, proxy, records, model
- test_selected_record_is_correct_under_sorting(binding) (L166): The bug this design prevents: indexing a list by the view's row.
- test_selected_record_is_none_without_selection(binding) (L177): Exercise clearSelection; assert selected_record
- test_select_where_reselects_by_identity(binding) (L183): Exercise select_where; assert select_where, selected_record
- test_select_where_returns_false_when_absent(binding) (L193): Exercise select_where; assert select_where
- test_record_role_returns_the_object_itself(binding) (L198): Exercise data; assert records
- test_set_records_replaces_everything(binding) (L208): Exercise set_records; assert rowCount, proxy, data, index
- test_clear_empties_the_model(binding) (L215): Exercise clear; assert rowCount, proxy, selected_record
- test_record_at_is_bounds_safe(binding) (L222): Exercise record_at; assert record_at, model
- test_works_with_attribute_records_not_just_dicts(app) (L229): Construct RecordTableModel; assert data, DisplayRole, index, ItemDataRole
- test_works_with_attribute_records_not_just_dicts.Device.__init__(self, ip) (L233): Initialize ip
- test_large_result_set_costs_no_per_cell_objects(binding) (L245): 10,000 rows must be accepted without building 30,000 cell objects.

## tests/test_tabs_gating.py — Headless gating + repair tests for legacy GUI tabs.
- app() (L42): App: build QApplication.instance, via fixture; return result
- make_tab(app) (L48): Factory building a tab without touching the real license manager.
- make_tab._make(tab_cls) (L54): make via tab_cls; return result
- _link_item(path: Path) -> BrokenSymlink (L61): link item: build BrokenSymlink, via now; return result
- _registry_item(tmp_path: Path) -> BrokenRegistryRef (L74): registry item: build BrokenRegistryRef, via now; return result
- test_free_space_checkbox_disabled_on_free_tier(app, make_tab, monkeypatch) (L93): Exercise setattr; assert isEnabled, shred_free_space_checkbox, lower
- test_free_space_checkbox_enabled_when_entitled(app, make_tab, monkeypatch) (L103): Exercise setattr; assert isEnabled, shred_free_space_checkbox
- test_multipass_spinbox_capped_without_entitlement(app, make_tab, monkeypatch) (L113): Exercise setattr; assert maximum, shred_passes_spinbox, value, _resolve_passes, lower
- test_multipass_allowed_keeps_full_range(app, make_tab, monkeypatch) (L128): Exercise setattr; assert maximum, shred_passes_spinbox
- _make_broken_symlink(tmp_path: Path) (L142): make broken symlink via symlink, skip; return result
- test_repair_dry_run_changes_nothing(app, tmp_path) (L153): Exercise _make_broken_symlink; assert lexists, path, ok, lower, detail
- test_repair_removes_only_the_link(app, tmp_path, monkeypatch) (L174): Exercise _make_broken_symlink; assert ok, lexists, path, exists, read_text
- test_repair_dry_run_plans_without_touching_fs(app, tmp_path, monkeypatch) (L189): Planning path covered without needing OS link privileges.
- test_repair_removes_dangling_junction_link_only(app, tmp_path) (L208): Junctions need no admin rights; removal must take the link only.
- test_repair_excludes_registry_refs(app, tmp_path) (L233): Exercise repair; assert action, ok, lower, detail
- test_repair_recycles_shortcut_via_send2trash(app, tmp_path, monkeypatch) (L244): Construct BrokenShortcut; assert ok, lower, detail, exists, action
- test_repair_recycles_shortcut_via_send2trash.fake_trash(p) (L260): Fake trash via remove
- test_repair_refuses_real_directory(app, tmp_path) (L279): Exercise mkdir; assert ok, exists
- _silence_message_boxes(monkeypatch, module) (L297): Replace modal QMessageBox calls so headless tests never block.
- _silence_message_boxes.FakeBoxes.information(self, *a, **k) (L302): Information: 'information.'; return result
- _silence_message_boxes.FakeBoxes.warning(self, *a, **k) (L306): Warning: 'warning.'; return result
- _silence_message_boxes.FakeBoxes.critical(self, *a, **k) (L310): Critical: 'critical.'; return result
- test_schedule_button_disabled_on_free_tier(app, make_tab, monkeypatch) (L317): Exercise setattr; assert isEnabled, schedule_report_button, lower
- test_schedule_button_enabled_and_creates_task(app, make_tab, monkeypatch) (L327): Exercise setattr; assert isEnabled, schedule_report_button
- test_schedule_button_enabled_and_creates_task.FakeScheduler.__init__(self, config=None) (L333): init  : '__init__.'
- test_schedule_button_enabled_and_creates_task.FakeScheduler.create_scheduled_task(self, name, command, schedule_type, schedule_params=None) (L337): Create scheduled task via append; return result
- test_schedule_dialog_cancel_creates_nothing(app, make_tab, monkeypatch) (L368): Exercise setattr
- test_schedule_dialog_cancel_creates_nothing.FakeScheduler.__init__(self, config=None) (L374): init  : '__init__.'
- test_schedule_dialog_cancel_creates_nothing.FakeScheduler.create_scheduled_task(self, *args, **kwargs) (L378): Create scheduled task via append; return result

## tests/test_task_manager.py — Tests for the task-manager backend (live snapshot + honest reconciliation).
- tm() (L13): Tm: build/parse TaskManager; return result
- TestSnapshot.test_snapshot_shape(self, tm) (L21): Exercise snapshot; assert set(...)
- TestSnapshot.test_cpu_block(self, tm) (L27): Exercise isinstance; assert isinstance, len(...)
- TestSnapshot.test_processes_have_fields(self, tm) (L35): Exercise any; assert getpid
- TestSnapshot.test_processes_sorted_by_memory_desc(self, tm) (L45): Exercise snapshot; assert sorted(...)
- TestSnapshot.test_idle_process_excluded(self, tm) (L51): The idle process (unused CPU) must never appear as a real process.
- TestSnapshot.test_total_cpu_in_range(self, tm) (L58): Exercise snapshot
- TestSnapshot.test_per_process_cpu_normalized(self, tm) (L63): Exercise snapshot; assert all(...)
- TestMemoryReconciliation.test_core_fields_present(self, tm) (L74): Exercise snapshot
- TestMemoryReconciliation.test_used_is_total_minus_available(self, tm) (L81): Exercise snapshot
- TestMemoryReconciliation.test_no_false_equation(self, tm) (L86): We must NOT pretend process working sets sum to 'in use'.
- TestMemoryReconciliation.test_hardware_reserved_consistent_if_present(self, tm) (L96): Exercise snapshot
- TestEndProcess.test_end_nonexistent_pid(self, tm) (L106): Exercise end_process; assert isinstance(...)
- TestEndProcess.test_end_returns_tuple(self, tm) (L113): Exercise end_process; assert isinstance, len(...)
- test_singleton_instance() (L119): Construct TaskManager.instance

## tests/test_temp_cleaner.py — Tests for :mod:`cortex_unified.core.temp_cleaner` and the ``clean-temp`` CLI.
- _backdate(path: Path, ts: float=OLD_TS) -> None (L24): backdate via utime
- _make_old(path: Path, size: int=32, ts: float=OLD_TS) -> Path (L29): make old via mkdir, write_bytes, _backdate; return result
- temp_roots(tmp_path, monkeypatch) (L38): Two fake temp roots; TempCleaner.LOCATIONS is pointed at them.
- _cleaner(**kwargs) -> TempCleaner (L51): cleaner: build TempCleaner, via setdefault; return result
- TestScan.test_finds_old_files_with_sizes_and_locations(self, temp_roots) (L59): Exercise _make_old; assert size_bytes, location
- TestScan.test_skips_fresh_files(self, temp_roots) (L76): Exercise _make_old; assert path, exists
- TestScan.test_min_age_zero_includes_fresh_files(self, temp_roots) (L88): Exercise write_bytes; assert path, size_bytes
- TestScan.test_exclude_patterns_honored(self, temp_roots) (L98): Exercise _make_old; assert exists
- TestScan.test_unreadable_and_missing_roots_are_ignored(self, tmp_path, monkeypatch) (L111): Construct Path; assert name, path
- TestScan.test_symlinked_directory_is_never_traversed(self, temp_roots) (L129): Construct Path; assert exists, is_relative_to
- TestScan.test_junctioned_directory_is_never_traversed(self, temp_roots) (L151): Construct Path; assert exists, is_relative_to
- TestTotals.test_total_reclaimable_before_scan_is_zero(self) (L178): Exercise total_reclaimable; assert total_reclaimable
- TestTotals.test_total_reclaimable_sums_scan_results(self, temp_roots) (L182): Exercise _make_old; assert total_reclaimable
- TestClean.test_dry_run_touches_nothing(self, temp_roots) (L195): Exercise _make_old; assert exists
- TestClean.test_use_trash_removes_files_from_scan_results(self, temp_roots, monkeypatch) (L210): Exercise _make_old; assert exists, scan
- TestClean.test_use_trash_removes_files_from_scan_results.fake_send2trash(path) (L216): Fake send2trash via unlink
- TestClean.test_without_trash_files_are_unlinked(self, temp_roots) (L236): Exercise _make_old; assert exists
- TestClean.test_refuses_paths_outside_discovered_roots(self, temp_roots) (L247): Construct TempFinding; assert exists
- TestClean.test_never_deletes_files_modified_within_min_age(self, temp_roots) (L265): Construct TempFinding; assert exists
- TestCleanTempCLI.test_help_lists_command(self) (L286): Construct CliRunner; assert exit_code, lower, output
- TestCleanTempCLI.test_dry_run_lists_findings_and_deletes_nothing(self, temp_roots) (L292): Construct CliRunner; assert exit_code, exists
- TestCleanTempCLI.test_delete_flag_cleans_after_confirmation_skip(self, temp_roots) (L307): Construct CliRunner; assert exit_code, exists
- TestCleanTempCLI.test_trash_flag_routes_through_send2trash(self, temp_roots, monkeypatch) (L319): Construct CliRunner; assert exit_code, exists
- TestCleanTempCLI.test_trash_flag_routes_through_send2trash.fake_send2trash(path) (L324): Fake send2trash via unlink

## tests/test_utils.py — Tests for core filesystem utility helpers.
- test_normalize_path() (L7): Test path normalization.

## tests/test_vhdx_manager.py — Virtual-disk (VHDX) discovery and compaction safety.
- fake_vhdx(tmp_path) (L33): A stand-in .vhdx file of a known size.
- test_saving_is_unknown_without_a_guest_measurement(fake_vhdx) (L44): Construct VirtualDisk; assert used_inside_bytes, potential_saving_bytes, status_note
- test_saving_is_host_size_minus_guest_usage(fake_vhdx) (L53): Construct VirtualDisk; assert potential_saving_bytes, status_note
- test_saving_never_goes_negative(fake_vhdx) (L61): Guest usage can exceed the host file for a sparse disk; clamp at zero.
- test_running_disk_names_the_blocking_process(fake_vhdx) (L68): Construct VirtualDisk; assert can_compact, status_note
- test_missing_file_is_reported_not_offered(tmp_path) (L77): Construct VirtualDisk; assert can_compact, status_note
- test_disk_to_dict_is_json_ready(fake_vhdx) (L84): Construct VirtualDisk
- test_list_disks_dedupes_sorts_and_flags_blockers(monkeypatch, tmp_path) (L99): Construct VhdxManager; assert path, on_disk_bytes, running, blockers, can_compact
- test_real_discovery_never_raises() (L133): On a machine with no WSL/Docker/Hyper-V this must return [], not blow up.
- test_unsupported_platform_returns_empty(monkeypatch) (L141): Construct VhdxManager; assert list_disks, shutdown_wsl
- test_compact_refuses_while_runtime_holds_the_disk(monkeypatch, fake_vhdx) (L154): The whole point: never touch a disk that is still attached.
- test_compact_refuses_while_runtime_holds_the_disk._boom(*_a, **_k) (L160): boom: build/parse AssertionError
- test_compact_reports_measured_delta(monkeypatch, fake_vhdx) (L174): Construct VhdxManager; assert success, before_bytes, after_bytes, freed_bytes
- test_compact_reports_measured_delta._shrink(script, timeout, cancel_event=None) (L179): shrink via write_bytes; return result
- test_compact_is_honest_when_nothing_was_reclaimed(monkeypatch, fake_vhdx) (L197): Construct VhdxManager; assert success, freed_bytes, message
- test_compact_surfaces_permission_failure(monkeypatch, fake_vhdx) (L211): Construct VhdxManager; assert success, lower, message, freed_bytes
- test_compact_missing_file_fails_clearly(tmp_path) (L224): Construct VirtualDisk; assert success, message
- test_failure_messages_are_actionable() (L232): Exercise explain; assert lower
- test_compact_result_freed_bytes_never_negative(tmp_path) (L240): A disk that grew during the run must not report negative savings.
- test_decode_handles_utf16_console_output() (L247): diskpart emits UTF-16LE with embedded NULs on some consoles.
- test_sparse_mode_is_wsl_only(fake_vhdx) (L254): Construct VirtualDisk; assert lower

## tests/test_video_duplicate_finder.py — Tests for video near-duplicate detection (keyframe pHash + temporal).
- _make_fake_video(path: Path, payload: bytes, size_kb: int=128) (L16): make fake video via write_bytes, max
- test_fingerprint_is_list(tmp_path: Path) (L26): Exercise _make_fake_video; assert isinstance, all(...)
- test_identical_videos_compare_high(tmp_path: Path) (L35): Exercise _make_fake_video; assert video_compare(...)
- test_different_videos_compare_low(tmp_path: Path) (L46): Exercise _make_fake_video; assert video_compare(...)
- test_video_compare_empty() (L61): Exercise video_compare; assert video_compare(...)
- test_video_compare_identity() (L67): Exercise video_compare; assert video_compare(...)
- test_finder_groups_identical_videos(tmp_path: Path) (L75): Construct VideoDuplicateFinder
- test_finder_excludes_non_video(tmp_path: Path) (L90): Construct VideoDuplicateFinder; assert find_video_duplicates
- test_finder_respects_exclude_dirs(tmp_path: Path) (L98): Construct Config; assert intersection
- test_finder_stats(tmp_path: Path) (L116): Construct VideoDuplicateFinder

## tests/test_wan_audit.py — Synthetic tests for the local-only, read-only WAN auditor.
- test_public_ip_classification(address, expected) (L36): Exercise parametrize; assert classify_public_ip(...)
- test_ssrf_guard_requires_literal_private_host_on_local_network() (L41): Exercise _is_trusted_url; assert _is_trusted_url, all(...)
- test_xml_rejects_entities_and_excessive_depth() (L59): Exercise encode
- test_igd_control_url_is_resolved_and_kept_local(monkeypatch) (L68): Construct WanAuditor; assert endswith
- test_igd_rejects_control_url_to_other_network(monkeypatch) (L86): Construct WanAuditor
- _soap_response(action: str, content: str) -> bytes (L102): soap response via encode; return result
- test_soap_allowlist_and_mapping_parser(monkeypatch) (L111): Construct WanAuditor; assert PortMapping(...)
- SyntheticAuditor.local_interfaces() (L137): Local interfaces: build/parse InterfaceStatus; return result
- SyntheticAuditor.default_gateway() (L142): Default gateway: 'default_gateway.'; return result
- SyntheticAuditor.dns_servers() (L147): Dns servers: 'dns_servers.'; return result
- SyntheticAuditor.discover_locations(self, networks, cancel_event=None) (L151): Discover locations: 'discover_locations.'; return result
- SyntheticAuditor._load_igd(self, location, networks) (L155): load igd: '_load_igd.'; return result
- SyntheticAuditor._soap(self, url, service_type, action, arguments=None) (L159): soap: build ValueError, via _safe_xml, _soap_response; return result
- test_audit_is_json_safe_and_contains_local_context() (L168): Construct SyntheticAuditor
- test_pre_cancelled_audit_does_not_discover(monkeypatch) (L179): Construct SyntheticAuditor; assert cancelled, audit

## tests/test_winapp2_cleaner.py — Unit and integration tests for Winapp2Cleaner engine.
- test_winapp2_cleaner_initialization() (L16): Construct Winapp2Cleaner; assert rules
- test_winapp2_expand_vars(monkeypatch) (L25): Construct Winapp2Cleaner.expand_vars
- test_winapp2_path_safety() (L37): Construct Winapp2Cleaner; assert is_safe_path
- test_winapp2_scan_and_clean(tmp_path, monkeypatch) (L49): Construct Winapp2Cleaner; assert rules, name, installed_apps_count, targets, total_bytes

## tests/test_windows_update.py — Tests for Windows Update surfacing (parsers + gating).
- TestPendingParse.test_empty(self) (L14): Construct WindowsUpdate._parse_pending; assert _parse_pending
- TestPendingParse.test_single(self) (L19): Construct WindowsUpdate._parse_pending; assert kb, severity, size_bytes
- TestPendingParse.test_array(self) (L31): Construct WindowsUpdate._parse_pending; assert _parse_pending
- TestPendingParse.test_titleless_skipped(self) (L37): Construct WindowsUpdate._parse_pending; assert _parse_pending
- TestPendingParse.test_no_kb(self) (L41): Construct WindowsUpdate._parse_pending; assert kb
- TestHistoryParse.test_success_and_fail(self) (L49): Construct WindowsUpdate._parse_history; assert len(...)
- TestHistoryParse.test_date_formatted(self) (L58): Construct WindowsUpdate._parse_history
- TestHistoryParse.test_empty(self) (L63): Construct WindowsUpdate._parse_history; assert _parse_history
- TestGating.test_is_supported(self) (L71): Construct WindowsUpdate.is_supported; assert is_supported
- TestGating.test_last_activity_shape(self) (L75): Construct WindowsUpdate; assert set(...)
- TestGating.test_check_pending_returns_list(self) (L80): Construct WindowsUpdate; assert isinstance(...)
- TestGating.test_to_dict(self) (L86): Construct PendingUpdate; assert set(...)

## src/NexusExplorer/test_explorer.py — NexusExplorer comprehensive offscreen smoke test.
- run_smoke_test() -> int (L12): Run smoke test: build ExplorerWidget, via test, resize; loop over results; return result
- run_smoke_test.test(name, fn) (L36): Test via fn

<!-- totals: files=124 defs=1759 -->