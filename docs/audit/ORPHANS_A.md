# Orphan Hunt A — backend exists, never called from GUI

Method: enumerated public top-level funcs/classes via AST in `src/NexusExplorer/native/*.py`, `src/cortex_unified/engine/`, `src/cortex_unified/core/`, `src/cortex_unified/performance/` (305 defs). For each name ran word-boundary Grep (`\bNAME\b`) across GUI scope: `src/cortex_unified/ui/` (rglob), `src/cortex_unified/explorer/*.py`, `src/NexusExplorer/native/nexus_explorer.py`, `run_gui.py`. Zero hits outside own file (+tests ignored) = ORPHAN. `nexus_explorer.py` defs excluded (that file IS GUI). Bodies sampled via Read for `does X`. Spot-verified with `Grep` tool: `CloudManager|NetworkManager|PluginHost|ContentSearchEngine|FileIndexer|TempCleaner` → zero hits; `BinaryDiffer|DirectoryDiffEngine|HashTool|FileUnlocker|FileSplitterJoiner|LinksManager|FastCopier|TimestampTouchEngine|TransferQueue|UndoStack|ScanManager` → hits in `premium/*_pages.py` / `explorer/transfers.py` / `explorer/undo.py` / `main_window.py`, correctly EXCLUDED below.

Result: **176 top-level orphans** (DTOs included). Parents that ARE wired (correctly excluded): `BinaryDiffer`, `DirectoryDiffEngine`, `HashTool`, `FileUnlocker`, `FileSplitterJoiner`, `BatchRenamer`, `LinksManager`, `FastCopier`, `TimestampTouchEngine`, `TransferQueue`, `UndoStack`, `Par2RecoveryEngine` (+report), `UsnJournalScanner`, `ImageOptimizer`, `FileSignatureSniffer`, `AlternateDataStreamsManager`, `ScanManager`, `MultiDriveScanner`, `ResourceMonitor`, `Scanner`, `CleanerService`, `SecureDeleter`, `SmartSuggester`.

## src/NexusExplorer/native/binary_differ.py
- `HexDiffChunk()` (src\NexusExplorer\native\binary_differ.py:18): does chunk DTO (offset/bytes) for hex diff — unused by GUI. Suggest: expose via Apex Binary-Diff page detail tooltip (already wires `BinaryDiffer.compare_binary_files`).

## src/NexusExplorer/native/file_signature_sniffer.py
- `FileSignature()` (src\NexusExplorer\native\file_signature_sniffer.py:18): does magic-number signature DTO — unused by GUI. Suggest: expose via Apex Sniffer page "why matched" tooltip.

## src/NexusExplorer/native/nexus_ads_manager.py
- `AlternateDataStream()` (src\NexusExplorer\native\nexus_ads_manager.py:30): does ADS entry DTO — unused by GUI. Suggest: expose via PowerTools ADS list (already wires manager, needs typed rows).

## src/NexusExplorer/native/nexus_archive.py
- `is_7z_available()` (src\NexusExplorer\native\nexus_archive.py:124): does 7z-CLI presence probe — unused by GUI. Suggest: expose via ArchiveBrowser/tools_pages capability badge + fallback notice.
- `ArchiveSecurityError()` (src\NexusExplorer\native\nexus_archive.py:145): does zip-slip guard exception — unused by GUI. Suggest: expose via ArchiveBrowser error dialog (catch → message).
- `validate_extract_path()` (src\NexusExplorer\native\nexus_archive.py:153): does traversal-safe join check — unused by GUI. Suggest: expose via ArchiveBrowser extract path validator.
- `ArchiveType()` (src\NexusExplorer\native\nexus_archive.py:181): does archive-kind enum — unused by GUI. Suggest: expose via ArchiveBrowser filter chips.
- `ArchiveInfo()` (src\NexusExplorer\native\nexus_archive.py:232): does archive summary DTO — unused by GUI. Suggest: expose via ArchiveBrowser header.
- `detect_archive_type()` (src\NexusExplorer\native\nexus_archive.py:245): does magic sniff for archives — unused by GUI. Suggest: expose via ExplorerWidget double-click routing + PreviewPane badge.

## src/NexusExplorer/native/nexus_archive_manager.py
- `ArchiveEntryInfo()` (src\NexusExplorer\native\nexus_archive_manager.py:41): does entry DTO — unused by GUI. Suggest: expose via ArchiveBrowser table model.
- `ArchiveOperationResult()` (src\NexusExplorer\native\nexus_archive_manager.py:53): does op result DTO — unused by GUI. Suggest: expose via ArchiveBrowser status bar.

## src/NexusExplorer/native/nexus_batch_renamer.py
- `RenamePlanItem()` (src\NexusExplorer\native\nexus_batch_renamer.py:34): does rename plan row DTO — unused by GUI. Suggest: expose via BulkRenameDialog preview table (already wires `BatchRenamer`, needs typed rows).
- `RenameTransaction()` (src\NexusExplorer\native\nexus_batch_renamer.py:47): does atomic rename txn — unused by GUI. Suggest: expose via BulkRenameDialog undo support.

## src/NexusExplorer/native/nexus_cloud.py
- `retry_on_rate_limit()` (src\NexusExplorer\native\nexus_cloud.py:134): does 429-backoff decorator — unused by GUI. Suggest: expose via Cloud page (implicit once manager wired).
- `CloudProviderType()` (src\NexusExplorer\native\nexus_cloud.py:185): does provider enum — unused by GUI. Suggest: expose via `premium/cloud_storage_page.py` provider tabs.
- `SyncStatus()` (src\NexusExplorer\native\nexus_cloud.py:193): does sync-state enum — unused by GUI. Suggest: expose via Cloud page status icons.
- `CloudFile()` (src\NexusExplorer\native\nexus_cloud.py:205): does cloud file DTO — unused by GUI. Suggest: expose via Cloud page table.
- `CloudAccount()` (src\NexusExplorer\native\nexus_cloud.py:221): does account DTO — unused by GUI. Suggest: expose via Cloud page account header.
- `CloudProvider()` (src\NexusExplorer\native\nexus_cloud.py:235): does provider ABC — unused by GUI. Suggest: expose via Cloud page (plug OneDrive/Google/Dropbox/S3).
- `OneDriveProvider()` (src\NexusExplorer\native\nexus_cloud.py:306): does OneDrive OAuth+Graph — unused by GUI. Suggest: expose via Cloud page Connect button.
- `GoogleDriveProvider()` (src\NexusExplorer\native\nexus_cloud.py:626): does Google Drive OAuth — unused by GUI. Suggest: expose via Cloud page Connect button.
- `DropboxProvider()` (src\NexusExplorer\native\nexus_cloud.py:932): does Dropbox OAuth — unused by GUI. Suggest: expose via Cloud page Connect button.
- `S3Provider()` (src\NexusExplorer\native\nexus_cloud.py:1197): does S3 key/secret provider — unused by GUI. Suggest: expose via Cloud page Connect button.
- `CloudManager()` (src\NexusExplorer\native\nexus_cloud.py:1349): does 4-provider fan-out (parallel list/search) — unused by GUI. Suggest: expose via `premium/cloud_storage_page.py` + `explorer/cloud.py` shim.

## src/NexusExplorer/native/nexus_content_search.py
- `ContentMatch()` (src\NexusExplorer\native\nexus_content_search.py:62): does single hit DTO — unused by GUI. Suggest: expose via new Find-in-Files panel / SearchDialog content tab.
- `ContentSearchResult()` (src\NexusExplorer\native\nexus_content_search.py:72): does per-file hits DTO — unused by GUI. Suggest: expose via Find-in-Files results model.
- `is_searchable()` (src\NexusExplorer\native\nexus_content_search.py:79): does text-extension gate — unused by GUI. Suggest: expose via Find-in-Files prefilter + `explorer/content_search.py`.
- `search_file_content()` (src\NexusExplorer\native\nexus_content_search.py:91): does regex/plain per-file search — unused by GUI. Suggest: expose via Find-in-Files worker.
- `ContentSearchEngine()` (src\NexusExplorer\native\nexus_content_search.py:291): does cancellable tree search — unused by GUI. Suggest: expose via SearchDialog "content" mode.

## src/NexusExplorer/native/nexus_core.py
- `marshal_call()` (src\NexusExplorer\native\nexus_core.py:209): does FFI/IPC arg marshaller — unused by GUI. Suggest: expose via ExplorerWidget→Engine bridge (internal, no direct UI).

## src/NexusExplorer/native/nexus_dir_diff.py
- `DiffEntry()` (src\NexusExplorer\native\nexus_dir_diff.py:41): does diff-row DTO — unused by GUI. Suggest: expose via DirDiff page table (engine already wired).
- `SyncStats()` (src\NexusExplorer\native\nexus_dir_diff.py:56): does sync-counts DTO — unused by GUI. Suggest: expose via DirDiff result bar.

## src/NexusExplorer/native/nexus_ffi.py
- `find_dll()` (src\NexusExplorer\native\nexus_ffi.py:54): does native DLL locator — unused by GUI. Suggest: expose via ExplorerWidget backend status / `explorer/ffi.py` init.
- `NexusFfi()` (src\NexusExplorer\native\nexus_ffi.py:164): does Rust/DLL fast list/search/transfer bridge — unused by GUI. Suggest: expose via ExplorerWidget engine switch + `explorer/ffi.py`.

## src/NexusExplorer/native/nexus_file_splitter.py
- `SplitManifest()` (src\NexusExplorer\native\nexus_file_splitter.py:43): does split manifest DTO — unused by GUI. Suggest: expose via Split/Join page manifest view.
- `SplitResult()` (src\NexusExplorer\native\nexus_file_splitter.py:56): does split result DTO — unused by GUI. Suggest: expose via Split page status.
- `JoinResult()` (src\NexusExplorer\native\nexus_file_splitter.py:67): does join result DTO — unused by GUI. Suggest: expose via Join page status.

## src/NexusExplorer/native/nexus_folder_tree.py
- `FolderTreeModel()` (src\NexusExplorer\native\nexus_folder_tree.py:23): does lazy drive/tree Qt model — unused by GUI. Suggest: expose via ExplorerWidget sidebar (`explorer/folder_tree.py` shim exists).

## src/NexusExplorer/native/nexus_hash_tool.py
- `HashResult()` (src\NexusExplorer\native\nexus_hash_tool.py:33): does hash DTO — unused by GUI. Suggest: expose via Checksum/Hash page rows.
- `VerifyItem()` (src\NexusExplorer\native\nexus_hash_tool.py:46): does manifest-verify row — unused by GUI. Suggest: expose via Verify-manifest results.

## src/NexusExplorer/native/nexus_indexer.py
- `IndexedEntry()` (src\NexusExplorer\native\nexus_indexer.py:152): does indexed-path DTO — unused by GUI. Suggest: expose via instant-search service (`explorer/indexer.py`).
- `IndexStats()` (src\NexusExplorer\native\nexus_indexer.py:164): does index counters — unused by GUI. Suggest: expose via Explorer status bar.
- `FileIndex()` (src\NexusExplorer\native\nexus_indexer.py:252): does thread-safe name/ext/prefix index — unused by GUI. Suggest: expose via ExplorerWidget quick-open.
- `FileIndexer()` (src\NexusExplorer\native\nexus_indexer.py:689): does background crawler + FTS + DB persist — unused by GUI. Suggest: expose via background service toggled in Settings.

## src/NexusExplorer/native/nexus_links_manager.py
- `LinkOperationResult()` (src\NexusExplorer\native\nexus_links_manager.py:47): does link-op result DTO — unused by GUI. Suggest: expose via Links page status (manager already wired).

## src/NexusExplorer/native/nexus_native_app.py
- `main()` (src\NexusExplorer\native\nexus_native_app.py:24): does standalone explorer entrypoint — unused by GUI. Suggest: expose via `run_gui.py --explorer` flag / launcher.

## src/NexusExplorer/native/nexus_network.py
- `NetworkProtocol()` (src\NexusExplorer\native\nexus_network.py:62): does protocol enum — unused by GUI. Suggest: expose via `premium/network_pages.py` protocol picker.
- `NetworkFile()` (src\NexusExplorer\native\nexus_network.py:72): does remote-file DTO — unused by GUI. Suggest: expose via Network browser table.
- `NetworkConnection()` (src\NexusExplorer\native\nexus_network.py:85): does connection DTO — unused by GUI. Suggest: expose via recent-connections menu.
- `store_credential()` (src\NexusExplorer\native\nexus_network.py:96): does cred-store helper — unused by GUI. Suggest: expose via Connect dialog "remember me".
- `get_credential()` (src\NexusExplorer\native\nexus_network.py:107): does cred-fetch helper — unused by GUI. Suggest: expose via Connect dialog autofill.
- `NetworkFS()` (src\NexusExplorer\native\nexus_network.py:131): does FS ABC — unused by GUI. Suggest: expose via Network browser (plug SMB/FTP/SFTP/WebDAV).
- `SMBProvider()` (src\NexusExplorer\native\nexus_network.py:186): does SMB share client — unused by GUI. Suggest: expose via Network Connect.
- `FTPProvider()` (src\NexusExplorer\native\nexus_network.py:341): does FTP client — unused by GUI. Suggest: expose via Network Connect.
- `SFTPProvider()` (src\NexusExplorer\native\nexus_network.py:533): does SFTP client — unused by GUI. Suggest: expose via Network Connect.
- `WebDAVProvider()` (src\NexusExplorer\native\nexus_network.py:724): does WebDAV client — unused by GUI. Suggest: expose via Network Connect.
- `ConnectionPool()` (src\NexusExplorer\native\nexus_network.py:863): does pooled-connection cache — unused by GUI. Suggest: expose via NetworkManager internals (no direct UI).
- `NetworkManager()` (src\NexusExplorer\native\nexus_network.py:946): does pooled multi-protocol manager + MRU — unused by GUI. Suggest: expose via `premium/network_pages.py` + `explorer/network.py`.

## src/NexusExplorer/native/nexus_plugins.py
- `PluginManifest()` (src\NexusExplorer\native\nexus_plugins.py:45): does plugin manifest DTO — unused by GUI. Suggest: expose via Plugin Manager list.
- `PluginState()` (src\NexusExplorer\native\nexus_plugins.py:103): does lifecycle enum — unused by GUI. Suggest: expose via Plugin Manager badges.
- `PluginLifecycle()` (src\NexusExplorer\native\nexus_plugins.py:123): does state machine — unused by GUI. Suggest: expose via Plugin Manager (internal).
- `ScopedConfig()` (src\NexusExplorer\native\nexus_plugins.py:171): does per-plugin config — unused by GUI. Suggest: expose via Plugin Settings dialog.
- `EventBridge()` (src\NexusExplorer\native\nexus_plugins.py:210): does scoped event bus — unused by GUI. Suggest: expose via plugin API (no direct UI).
- `EventBus()` (src\NexusExplorer\native\nexus_plugins.py:237): does global event bus — unused by GUI. Suggest: expose via plugin API (no direct UI).
- `PluginContext()` (src\NexusExplorer\native\nexus_plugins.py:279): does path/selection/navigate API — unused by GUI. Suggest: expose via ExplorerWidget `set_host_callbacks` wiring.
- `NexusPlugin()` (src\NexusExplorer\native\nexus_plugins.py:353): does plugin ABC — unused by GUI. Suggest: expose via Plugin SDK docs + sample.
- `APIAdapter()` (src\NexusExplorer\native\nexus_plugins.py:395): does compat adapter — unused by GUI. Suggest: expose via Plugin Manager (internal).
- `HotReloadWatcher()` (src\NexusExplorer\native\nexus_plugins.py:434): does plugin file watcher — unused by GUI. Suggest: expose via Plugin Manager dev-mode toggle.
- `PluginHost()` (src\NexusExplorer\native\nexus_plugins.py:542): does discover/load/unload + context-menu/toolbar/preview hooks — unused by GUI. Suggest: expose via Settings → Plugins page + `explorer/plugins.py`, wire `get_all_context_menu_actions` into ExplorerWidget menus.

## src/NexusExplorer/native/nexus_timestamp_touch.py
- `FileAttributeFlags()` (src\NexusExplorer\native\nexus_timestamp_touch.py:24): does attrib-flag enum — unused by GUI. Suggest: expose via Touch page checkboxes.
- `TimestampUpdateResult()` (src\NexusExplorer\native\nexus_timestamp_touch.py:53): does touch result DTO — unused by GUI. Suggest: expose via Touch page status.

## src/NexusExplorer/native/nexus_transfer_queue.py
- `JobState()` (src\NexusExplorer\native\nexus_transfer_queue.py:36): does job-state enum — unused by GUI. Suggest: expose via TransferStatusDock badges (queue already wired via `explorer/transfers.py`).
- `human_bytes()` (src\NexusExplorer\native\nexus_transfer_queue.py:72): does byte formatter — unused by GUI. Suggest: expose via transfer progress labels (replace ad-hoc formatting).
- `fmt_eta()` (src\NexusExplorer\native\nexus_transfer_queue.py:91): does ETA formatter — unused by GUI. Suggest: expose via transfer progress labels.

## src/NexusExplorer/native/nexus_undo.py
- `RenameEntry()` (src\NexusExplorer\native\nexus_undo.py:88): does rename undo-op — unused by GUI. Suggest: expose via Edit→Undo stack view (stack already wired via `explorer/undo.py`).
- `MoveEntry()` (src\NexusExplorer\native\nexus_undo.py:113): does move undo-op — unused by GUI. Suggest: expose via Undo history.
- `CopyEntry()` (src\NexusExplorer\native\nexus_undo.py:138): does copy undo-op — unused by GUI. Suggest: expose via Undo history.
- `DeleteEntry()` (src\NexusExplorer\native\nexus_undo.py:167): does delete+backup undo-op — unused by GUI. Suggest: expose via Undo history.
- `MkdirEntry()` (src\NexusExplorer\native\nexus_undo.py:198): does mkdir undo-op — unused by GUI. Suggest: expose via Undo history.
- `CreateFileEntry()` (src\NexusExplorer\native\nexus_undo.py:232): does create-file undo-op — unused by GUI. Suggest: expose via Undo history.
- `BatchCreateEntry()` (src\NexusExplorer\native\nexus_undo.py:268): does composite undo-op — unused by GUI. Suggest: expose via scaffold-dialog undo.

## src/NexusExplorer/native/nexus_unlocker.py
- `LockingProcessInfo()` (src\NexusExplorer\native\nexus_unlocker.py:53): does locker-process DTO — unused by GUI. Suggest: expose via Unlocker page table (engine `FileUnlocker` already wired).

## src/NexusExplorer/native/par2_recovery.py
- `Par2FileInfo()` (src\NexusExplorer\native\par2_recovery.py:20): does PAR2 file DTO — unused by GUI. Suggest: expose via PAR2 page file list.
- `Par2PacketInfo()` (src\NexusExplorer\native\par2_recovery.py:31): does packet DTO — unused by GUI. Suggest: expose via PAR2 details view.

## src/NexusExplorer/native/usn_journal_scanner.py
- `USN_JOURNAL_DATA_V0()` (src\NexusExplorer\native\usn_journal_scanner.py:38): does journal ctypes struct — unused by GUI. Suggest: internal; expose `UsnJournalStatus` fields in USN page instead.

## src/cortex_unified/engine/categories.py
- `categories_by_id()` (src\cortex_unified\engine\categories.py:855): does id→category map — unused by GUI. Suggest: expose via cleanup_hub/settings category picker (currently calls `default_categories`/`scan_categories` only).

## src/cortex_unified/engine/fastwalk.py
- `WalkOptions()` (src\cortex_unified\engine\fastwalk.py:43): does traversal tuning DTO — unused by GUI. Suggest: expose via Settings → Scan depth/excludes + large/empty tabs.
- `FastWalker()` (src\cortex_unified\engine\fastwalk.py:77): does cancellable streaming walker + USN fast path — unused by GUI. Suggest: expose via workers.py scan backend (replace ad-hoc walk; wire `scan_ntfs_usn` into USN page).

## src/cortex_unified/engine/guard.py
- `GuardVerdict()` (src\cortex_unified\engine\guard.py:26): does safe/blocked verdict — unused by GUI. Suggest: expose via delete-confirm dialog reason line + `safety_manager`.
- `PathGuard()` (src\cortex_unified\engine\guard.py:74): does protected-path/sandbox guard — unused by GUI. Suggest: expose via SafetyManager + all delete/shred entry points.

## src/cortex_unified/engine/hashing.py
- `DuplicateFinderEngine()` (src\cortex_unified\engine\hashing.py:89): does threaded dup finder + wasted-bytes — unused by GUI. Suggest: expose via duplicates_tab/workers (currently routes via `CleanerService.find_duplicates`; switch or add perceptual/fuzzy option).

## src/cortex_unified/engine/models.py
- `StorageKind()` (src\cortex_unified\engine\models.py:17): does HDD/SSD/NVMe enum — unused by GUI. Suggest: expose via Shredder/analyzer medium badge.
- `DeletionOutcome()` (src\cortex_unified\engine\models.py:48): does deletion result enum — unused by GUI. Suggest: expose via results table status.
- `DeletionResult()` (src\cortex_unified\engine\models.py:181): does per-item deletion record — unused by GUI. Suggest: expose via delete results + Reports.

## src/cortex_unified/engine/storage.py
- `StorageInfo()` (src\cortex_unified\engine\storage.py:54): does medium-probe DTO — unused by GUI. Suggest: expose via Disk/Shredder pages.
- `StorageProbe()` (src\cortex_unified\engine\storage.py:69): does per-mount medium cache — unused by GUI. Suggest: expose via `SecureDeleter.adaptive_delete` pre-check + Shredder UI hint.
- `detect_storage()` (src\cortex_unified\engine\storage.py:219): does one-shot probe helper — unused by GUI. Suggest: expose via Shredder "effective?" hint.

## src/cortex_unified/engine/winattrs.py
- `attrs_of()` (src\cortex_unified\engine\winattrs.py:72): does stat→attrs extract — unused by GUI. Suggest: expose via file-table badge pipeline (internal).
- `reparse_tag_of()` (src\cortex_unified\engine\winattrs.py:77): does stat→reparse-tag extract — unused by GUI. Suggest: expose via badge pipeline.
- `is_reparse_point()` (src\cortex_unified\engine\winattrs.py:92): does reparse predicate — unused by GUI. Suggest: expose via Explorer badges.
- `is_cloud_tag()` (src\cortex_unified\engine\winattrs.py:97): does cloud-tag predicate — unused by GUI. Suggest: expose via "cloud-synced" badge.
- `is_dehydrated()` (src\cortex_unified\engine\winattrs.py:102): does recall-on-access predicate — unused by GUI. Suggest: expose via skip-hash guard + "online-only" badge (critical: prevents accidental downloads).
- `is_cloud()` (src\cortex_unified\engine\winattrs.py:113): does cloud-managed predicate — unused by GUI. Suggest: expose via cloud badge.
- `is_junction()` (src\cortex_unified\engine\winattrs.py:122): does junction predicate — unused by GUI. Suggest: expose via "junction, not counted" badge.
- `size_may_be_misleading()` (src\cortex_unified\engine\winattrs.py:132): does sparse/compressed/cloud size-lies check — unused by GUI. Suggest: expose via analyzer "actual vs logical" column.
- `describe()` (src\cortex_unified\engine\winattrs.py:137): does plain-words storage note — unused by GUI. Suggest: expose via tooltips/PreviewPane (`tooltips.py`).
- `on_disk_size()` (src\cortex_unified\engine\winattrs.py:160): does allocated-size probe — unused by GUI. Suggest: expose via Disk Analyzer "on-disk" column.

## src/cortex_unified/core/config_v2.py
- `ScanConfig()` (src\cortex_unified\core\config_v2.py:102): does scan-settings model — unused by GUI. Suggest: expose via settings_tab Scan section.
- `PerformanceConfig()` (src\cortex_unified\core\config_v2.py:149): does perf-settings model — unused by GUI. Suggest: expose via settings_tab Performance section + `PerformanceManager`.
- `SecurityConfig()` (src\cortex_unified\core\config_v2.py:190): does safety-settings model — unused by GUI. Suggest: expose via settings_tab Safety section.
- `LoggingConfig()` (src\cortex_unified\core\config_v2.py:228): does log-settings model — unused by GUI. Suggest: expose via settings_tab Diagnostics.
- `DatabaseConfig()` (src\cortex_unified\core\config_v2.py:252): does DB-settings model — unused by GUI. Suggest: expose via settings_tab History toggle.
- `UIConfig()` (src\cortex_unified\core\config_v2.py:278): does theme/lang model — unused by GUI. Suggest: expose via settings_tab Appearance.
- `create_default_config()` (src\cortex_unified\core\config_v2.py:556): does yaml scaffold writer — unused by GUI. Suggest: expose via Settings "reset to defaults".

## src/cortex_unified/core/database.py
- `ScanRun()` (src\cortex_unified\core\database.py:39): does scan-run ORM row — unused by GUI. Suggest: expose via reports_tab History.
- `DeletedItem()` (src\cortex_unified\core\database.py:102): does deleted-item ORM row — unused by GUI. Suggest: expose via restore_tab quarantine list.
- `ScheduledJob()` (src\cortex_unified\core\database.py:162): does scheduled-job ORM row — unused by GUI. Suggest: expose via scheduler_tab persistence.
- `SystemMetric()` (src\cortex_unified\core\database.py:196): does metrics ORM row — unused by GUI. Suggest: expose via resource_monitor_tab history chart.
- `UserPreference()` (src\cortex_unified\core\database.py:224): does prefs ORM row — unused by GUI. Suggest: expose via settings persistence.
- `Database()` (src\cortex_unified\core\database.py:242): does scan/quarantine/metrics store — unused by GUI. Suggest: expose via Reports/Restore/Scheduler (wire `get_scan_history`, `get_restorable_items`, `record_metric`).
- `get_database()` (src\cortex_unified\core\database.py:559): does singleton accessor — unused by GUI. Suggest: expose via app startup init.
- `db_session()` (src\cortex_unified\core\database.py:574): does session ctx manager — unused by GUI. Suggest: expose via tab data loading (internal).

## src/cortex_unified/core/logging_setup.py
- `add_correlation_id()` (src\cortex_unified\core\logging_setup.py:23): does structlog correlation injector — unused by GUI. Suggest: expose via worker log init (no direct UI).
- `add_app_context()` (src\cortex_unified\core\logging_setup.py:30): does app/version injector — unused by GUI. Suggest: expose via log viewer About.
- `censor_sensitive_data()` (src\cortex_unified\core\logging_setup.py:40): does secret redactor — unused by GUI. Suggest: expose via log export (auto-apply).
- `configure_logging()` (src\cortex_unified\core\logging_setup.py:72): does structlog setup — unused by GUI. Suggest: expose via main_window startup + Diagnostics page level picker.
- `get_logger()` (src\cortex_unified\core\logging_setup.py:170): does component logger factory — unused by GUI. Suggest: internal standardisation (no UI).
- `set_correlation_id()` (src\cortex_unified\core\logging_setup.py:190): does per-scan correlation setter — unused by GUI. Suggest: expose via scan workers (correlate logs per run).
- `clear_correlation_id()` (src\cortex_unified\core\logging_setup.py:207): does correlation reset — unused by GUI. Suggest: expose via worker teardown.
- `LogContext()` (src\cortex_unified\core\logging_setup.py:212): does scoped log ctx — unused by GUI. Suggest: expose via workers (internal).
- `log_scan_start()` (src\cortex_unified\core\logging_setup.py:239): does scan-start event — unused by GUI. Suggest: expose via workers + Reports timeline.
- `log_scan_complete()` (src\cortex_unified\core\logging_setup.py:253): does scan-complete event — unused by GUI. Suggest: expose via Reports timeline.
- `log_scan_error()` (src\cortex_unified\core\logging_setup.py:271): does scan-fail event — unused by GUI. Suggest: expose via error toast + Reports.
- `log_file_operation()` (src\cortex_unified\core\logging_setup.py:287): does per-file op event — unused by GUI. Suggest: expose via Undo/History feed.
- `log_performance_metric()` (src\cortex_unified\core\logging_setup.py:305): does perf event — unused by GUI. Suggest: expose via resource_monitor_tab.

## src/cortex_unified/core/security.py
- `is_safe_path()` (src\cortex_unified\core\security.py:95): does protected-dir/extension gate — unused by GUI. Suggest: expose via safety_manager pre-delete check + confirm dialog.
- `is_system_file()` (src\cortex_unified\core\security.py:168): does system-file predicate — unused by GUI. Suggest: expose via warning badge.
- `is_path_writable()` (src\cortex_unified\core\security.py:256): does writability probe — unused by GUI. Suggest: expose via action enablement (grey out).
- `get_safe_temp_dir()` (src\cortex_unified\core\security.py:280): does safe tmp resolver — unused by GUI. Suggest: expose via export/quarantine paths.
- `check_deletion_safety()` (src\cortex_unified\core\security.py:289): does (safe, reason) verdict — unused by GUI. Suggest: expose via delete-confirm reason line.

## src/cortex_unified/core/smart_suggest.py
- `featurize()` (src\cortex_unified\core\smart_suggest.py:81): does cleanup-item featurizer — unused by GUI. Suggest: expose via SmartSuggester rank explanations ("why suggested") in dashboard.

## src/cortex_unified/core/temp_cleaner.py
- `TempFinding()` (src\cortex_unified\core\temp_cleaner.py:57): does temp-hit DTO — unused by GUI. Suggest: expose via DeepCleaner/Hub temp section table.
- `TempCleaner()` (src\cortex_unified\core\temp_cleaner.py:88): does stale-temp scan+clean — unused by GUI. Suggest: expose via deep_cleaner_tab + cleanup_hub_page (highest ROI cleaner orphan).

## src/cortex_unified/core/utils.py
- `is_system_directory()` (src\cortex_unified\core\utils.py:40): does protected-dir predicate — unused by GUI. Suggest: expose via safety badges.
- `get_component_logger()` (src\cortex_unified\core\utils.py:179): does per-component logger — unused by GUI. Suggest: internal (no UI).
- `log_operation_start()` (src\cortex_unified\core\utils.py:194): does op-start log — unused by GUI. Suggest: expose via workers (internal).
- `log_operation_end()` (src\cortex_unified\core\utils.py:214): does op-end log — unused by GUI. Suggest: expose via workers (internal).
- `log_performance_metrics()` (src\cortex_unified\core\utils.py:241): does perf-dict log — unused by GUI. Suggest: expose via resource tab.
- `generate_manifest_filename()` (src\cortex_unified\core\utils.py:257): does timestamped manifest name — unused by GUI. Suggest: expose via Deleter/export manifest save dialog.
- `get_file_age_days()` (src\cortex_unified\core\utils.py:266): does mtime→age helper — unused by GUI. Suggest: expose via age filter/column.
- `DockerError()` (src\cortex_unified\core\utils.py:295): does docker error type — unused by GUI. Suggest: expose via docker_tab error toast.
- `VisualizationError()` (src\cortex_unified\core\utils.py:299): does viz error type — unused by GUI. Suggest: expose via disk_analyzer_tab error state.
- `HeuristicsError()` (src\cortex_unified\core\utils.py:303): does heuristics error type — unused by GUI. Suggest: expose via heuristics_tab error state.
- `PackageManagerError()` (src\cortex_unified\core\utils.py:307): does pkg error type — unused by GUI. Suggest: expose via package_manager_tab error state.
- `PerformanceError()` (src\cortex_unified\core\utils.py:311): does perf error type — unused by GUI. Suggest: expose via resource tab error state.
- `AccessibilityError()` (src\cortex_unified\core\utils.py:315): does a11y error type — unused by GUI. Suggest: expose via settings a11y check.
- `safe_execute()` (src\cortex_unified\core\utils.py:349): does guarded-call wrapper — unused by GUI. Suggest: expose via tab workers (internal).
- `ResourceManager()` (src\cortex_unified\core\utils.py:373): does resource cleanup ctx — unused by GUI. Suggest: expose via workers (internal).
- `format_duration()` (src\cortex_unified\core\utils.py:448): does ms/s/m/h formatter — unused by GUI. Suggest: expose via scan status labels (transfer_queue has own `fmt_eta`; unify).
- `validate_path()` (src\cortex_unified\core\utils.py:461): does path validator — unused by GUI. Suggest: expose via GoToPathDialog + all path inputs.
- `get_system_info()` (src\cortex_unified\core\utils.py:520): does diagnostics bundle — unused by GUI. Suggest: expose via Settings → Diagnostics "copy info".
- `create_error_report()` (src\cortex_unified\core\utils.py:553): does error+trace bundle — unused by GUI. Suggest: expose via error dialog "Report" button.

## src/cortex_unified/performance/multi_drive_scanner.py
- `DriveInfo()` (src\cortex_unified\performance\multi_drive_scanner.py:34): does drive DTO — unused by GUI. Suggest: expose via disk_analyzer/drive picker.
- `NetworkDrive()` (src\cortex_unified\performance\multi_drive_scanner.py:58): does net-share DTO — unused by GUI. Suggest: expose via Network page (merge with NetworkManager).
- `UserProfile()` (src\cortex_unified\performance\multi_drive_scanner.py:69): does OS-profile DTO — unused by GUI. Suggest: expose via multi-user scan page.
- `ScanProgress()` (src\cortex_unified\performance\multi_drive_scanner.py:81): does multi-loc progress DTO — unused by GUI. Suggest: expose via scan progress bar.
- `AggregatedResult()` (src\cortex_unified\performance\multi_drive_scanner.py:110): does merged-totals DTO — unused by GUI. Suggest: expose via summary cards.
- `MultiUserScanner()` (src\cortex_unified\performance\multi_drive_scanner.py:120): does cross-profile scanner — unused by GUI. Suggest: expose via Settings "include other users" + disk pages.
- `DriveManager()` (src\cortex_unified\performance\multi_drive_scanner.py:490): does drive monitor + net-drive handler — unused by GUI. Suggest: expose via drive-change notifications + disk_analyzer.

## src/cortex_unified/performance/optimization.py
- `OptimizationSettings()` (src\cortex_unified\performance\optimization.py:19): does optimizer tuning DTO — unused by GUI. Suggest: expose via settings_tab Performance.
- `PerformanceOptimizer()` (src\cortex_unified\performance\optimization.py:32): does thread/buffer/GC tuner — unused by GUI. Suggest: expose via `PerformanceManager` + workers auto-tune + settings.

## src/cortex_unified/performance/profiler.py
- `ProfileReport()` (src\cortex_unified\performance\profiler.py:12): does timing DTO — unused by GUI. Suggest: expose via Diagnostics "last scan profile".
- `OperationProfiler()` (src\cortex_unified\performance\profiler.py:34): does profile start/end + reports — unused by GUI. Suggest: expose via workers (`profile_operation` ctx) + Diagnostics.

## src/cortex_unified/performance/resource_monitor.py
- `SystemMetrics()` (src\cortex_unified\performance\resource_monitor.py:17): does CPU/mem/IO snapshot DTO — unused by GUI. Suggest: expose via resource_monitor_tab charts (monitor itself wired; DTO not imported by name).

## src/cortex_unified/performance/resource_throttler.py
- `SystemLoad()` (src\cortex_unified\performance\resource_throttler.py:14): does load DTO — unused by GUI. Suggest: expose via throttling indicator.
- `ResourceThrottler()` (src\cortex_unified\performance\resource_throttler.py:27): does prio/EcoQoS/throttle manager — unused by GUI. Suggest: expose via `PerformanceManager` + settings "low-impact mode" + workers `throttle_if_needed`.

## src/cortex_unified/performance/scan_manager.py
- `ScanCheckpoint()` (src\cortex_unified\performance\scan_manager.py:15): does resume-checkpoint DTO — unused by GUI. Suggest: expose via "resume scan" picker (manager already wired in main_window).
- `ScanProgress()` (src\cortex_unified\performance\scan_manager.py:41): does progress DTO — unused by GUI. Suggest: expose via progress bar model.

## src/cortex_unified/performance/settings_integration.py
- `PerformanceSettingsWidget()` (src\cortex_unified\performance\settings_integration.py:20): does perf settings Qt widget — unused by GUI. Suggest: expose via settings_tab embed (currently builds own controls).
- `PerformanceManager()` (src\cortex_unified\performance\settings_integration.py:127): does optimizer+throttler singleton — unused by GUI. Suggest: expose via app startup + `get_performance_manager` in workers/tabs.

## Notes (method-level, verified via `\.\s*METHOD\s*\(` Grep)
Wired parents with unwired high-value methods (suggest wiring next): `SecureDeleter.adaptive_delete` (SSD-aware delete → file_shredder_tab), `HashTool.create_manifest/verify_manifest` partially wired (verify used; create not surfaced), `TimestampTouchEngine.touch_batch`, `TransferQueue.clear_finished/get_all_jobs`, `UndoStack.can_undo/can_redo` (wire to Edit menu enablement), `Database.*` (all methods above), `SmartSuggester.rank/observe_batch`, `MultiDriveScanner.scan_multiple_drives/get_aggregated_results`, `ResourceMonitor.get_optimization_recommendations/should_throttle_operations/export_metrics`, `ScanManager.load_checkpoint`. Generic Qt/model/dunder methods excluded from counts.
