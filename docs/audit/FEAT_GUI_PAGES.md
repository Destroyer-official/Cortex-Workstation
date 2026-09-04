# GUI Features Audit — Premium Pages, Tabs, Main Window, Safety, Tray

Base: `D:\code\Main_projects\Cortex_Cleaner` — read-only audit, no code changes.
Scope: `src/cortex_unified/ui/premium/*_pages.py` + `*_page.py`, `src/cortex_unified/ui/tabs/*.py`, `src/cortex_unified/ui/main_window.py`, `src/cortex_unified/ui/safety/`, `src/cortex_unified/ui/tray_icon.py`.
Method: code-read. Buttons/tables/combos/dialogs below are literal widget strings and handlers from source (`_PrimaryButton`/`_SecondaryButton`/`QPushButton`, `setHorizontalHeaderLabels`, `QFileDialog`/`QMessageBox`, `_on_*` slots). Backend = direct `from cortex_unified...` / `NexusExplorer...` imports in each file.
Date (UTC): 2026-09-04.

Conventions per file: `## PageName (file)` / user-action bullets / `backend:` module line.

---
---

## AdvancedUninstallerPage (premium/advanced_uninstaller_page.py)
- Click `Choose Root…` (QFileDialog.getExistingDirectory) to set scan root; `Enumerate Apps` runs background `_UninstallWorker`; progress bar + status text.
- Browse results table `["App Name","Version","Source","Status","Leftovers (MB)"]` (QTableWidget, row-select, checkbox column); QSpinBox for options.
- Select rows → `Uninstall Selected` (confirm QMessageBox.question; QInputDialog.getText for custom uninstall string); `Force uninstall if uninstaller missing` (QCheckBox).
- Info/warning dialogs for no-apps-found, start/finish states.
- backend: `cortex_unified.analyzers.advanced_uninstaller`

## DiskAnalyzerPage / DiskHealthPage / ScheduledTasksPage / BootPerformancePage / SystemRepairPage / StorageSensePage / SecurityPage / HealthCheckPage / WindowsUpdatePage / ComponentStorePage (premium/analysis_pages.py)
- DiskAnalyzerPage: `Choose Folder…` + `Analyze`; folder-size table; AI-model-extension hints.
- DiskHealthPage: `Check Disk Health`; physical-disk table (admin-gated SMART read).
- ScheduledTasksPage: task table + `Refresh`, `Delete Selected Task` (DeleteTaskWorker).
- BootPerformancePage: `Analyze Boot`, `Manage Startup Apps →`; boot-phase table.
- SystemRepairPage: `Run` (SFC/DISM-style repair worker), `Refresh`; result table.
- StorageSensePage: toggle/status card (`Storage Sense is ON`), `Run`, storage table.
- SecurityPage (Defender): `Run Quick Scan`, Defender status table.
- HealthCheckPage: `Run Health Check`, `Fix →`; healthy/issues table.
- WindowsUpdatePage: `Check for Updates Online`, `Open Windows Update`, pending-update + activity tables (WUActivityWorker/WUPendingWorker).
- ComponentStorePage: `Analyze Component Store`, `Let Windows Clean It`, `Clean Now`, `Remove Selected Leftovers`; WinSxS/leftover tables; all with QTableWidget + QProgressBar + QMessageBox confirms.
- backend: `cortex_unified.analyzers.disk_analyzer`, `cortex_unified.analyzers.large_file_finder`, `cortex_unified.scheduler.scheduler`, `cortex_unified.system_tools.boot_performance`, `cortex_unified.system_tools.defender`, `cortex_unified.system_tools.disk_health`, `cortex_unified.system_tools.health_check`, `cortex_unified.system_tools.storage_sense`, `cortex_unified.system_tools.system_repair`, `cortex_unified.system_tools.windows_update`

## DriverStoreCleanerPage / ShellbagsCleanerPage / PowerPlanOptimizerPage / HostsFileManagerPage / NotificationCleanerPage / FileSignatureSnifferPage / BinaryDifferPage / UsnJournalPage / Par2RecoveryPage / ImageOptimizerPage (premium/apex_tools_pages.py)
- DriverStoreCleanerPage: `Enumerate Drivers` (primary), `Export All Drivers…` (folder dialog), `Delete Superseded Drivers`; table `INF Name/Provider/Class/Version/Date/Status`.
- ShellbagsCleanerPage: `Scan Activity Traces`, `Purge Selected Traces`; shellbags/recent/jumplists table + folder picker `Choose Folder to Scan…`.
- PowerPlanOptimizerPage: `Unlock Ultimate Performance Plan`, `Refresh Schemes`, `Reduce Hibernation Footprint (40% RAM)`; scheme table + status card.
- HostsFileManagerPage: `Apply Anti-Telemetry Shield`, `Reload Hosts`, `Refresh Status`; hosts-entry table (QTableWidget), text editor area.
- NotificationCleanerPage: `Purge Notification Database`; app-notification table.
- FileSignatureSnifferPage: `Scan for Spoofed Files`, `Choose Folder to Scan…`; magic-bytes/MIME table.
- BinaryDifferPage: `Select File A…`, `Select File B…`, `Compare Binary Files`; hex-diff text view.
- UsnJournalPage: `Query USN Journal`; USN change-journal table.
- Par2RecoveryPage: `Open .par2 File…` (file dialog); parity/packet validation table.
- ImageOptimizerPage: `Select Images…`, `Compress Images`; quality QSlider, format QComboBox, batch-result table.
- backend: `cortex_unified.system_tools.driver_store_cleaner`, `shellbags_privacy_cleaner`, `power_plan_optimizer`, `hosts_file_manager`, `notification_cleaner`, `NexusExplorer.native.file_signature_sniffer`, `NexusExplorer.native.binary_differ`, `NexusExplorer.native.usn_journal_scanner`, `NexusExplorer.native.par2_recovery`, `NexusExplorer.native.image_optimizer`

## AudioDuplicatesPage (premium/audio_duplicates_page.py)
- `Choose Folder…` (dir dialog) + `Find Audio Duplicates`; QProgressBar worker `_AudioWorker`.
- Results table `["Audio File","Group","Hint"]`; empty-state `No audio duplicates found`.
- backend: `cortex_unified.analyzers.audio_duplicate_finder.AudioDuplicateFinder`

## CdcPage (premium/cdc_page.py)
- `Choose Folder…` + `Find CDC Duplicates` (FastCDC/VectorCDC chunking via `_CdcWorker`).
- Results table `["File","Group","Hint"]`; progress bar.
- backend: `cortex_unified.analyzers.content_defined_chunker.ContentDefinedChunker`

## CleanupHubPage (premium/cleanup_hub_page.py)
- `Scan All Caches` (HubScanWorker over CleanerService categories); `Select Directory` / `Select File Location` to add custom roots; `Select All` / `Deselect All` / `Reset Roots`; active-roots label.
- Category checklist with QCheckBox list incl. `Include opt-in (HIGH)`; QProgressBar scan/clean; `Clean Selected` (QMessageBox.question confirm → DeletionMethod recycle/permanent).
- backend: `cortex_unified.engine.CleanerService`, `cortex_unified.engine.RiskLevel/DeletionMethod`, `cortex_unified.engine.categories`, `cortex_unified.engine.service.CleanupReport`

## CloudStoragePage (premium/cloud_storage_page.py)
- Target QComboBox presets (`s3://bucket/prefix`, `azure://container/prefix`, `gdrive://root/folder`, `onedrive://…`); `Pick Target…` + `Analyze` (`_CloudWorker`).
- QCheckBox `Include versions (S3)`, `Include delete markers (S3)`; QSpinBox thresholds; QProgressBar.
- Tables: objects/size, cost/mo by provider, storage-class pricing (live vendor APIs), dedup table `Hash/Object Size/Cloud Copies/Local Copies/Wasted Space`.
- backend: `cortex_unified.analyzers.cloud_storage_analyzer` (+ `_PRICING`)

## CompactOsPage (premium/compact_os_page.py)
- `Check CompactOS Status`, `Scan Folder…` (dir dialog), `Estimate Compressible Folders`, `Compress Selected Folder` (confirm question dialog).
- Results table `["Folder","Size","Estimated savings","Ratio","State"]`; QSpinBox level; QProgressBar (`_ScanWorker`/`_CompactWorker`/`_QueryWorker`).
- backend: `cortex_unified.system_tools.compact_os.CompactOSManager`

## DirectStorageOptimizerPage (premium/directstorage_page.py)
- `Run BypassIO Diagnostics` (`_DirectStorageWorker` over fsutil BypassIO states); status text `Querying volume BypassIO states…`.
- Results table `["Drive","BypassIO State","Media Type","Storage Driver","Blocking Minifilters"]`; QProgressBar.
- backend: `cortex_unified.system_tools.directstorage_optimizer`

## DiskAnalyzerPage (premium/disk_analyzer_page.py)
- Path QLineEdit + `Browse…` + `Scan` (`_ScanWorker`); sort QComboBox; depth QSpinBox; QProgressBar.
- Folder table `["Folder","Size","% of Total","Files","Folders","Depth"]`; validation + `Scan complete — no folders found` states.
- backend: `cortex_unified.analyzers.advanced_disk_analyzer`

## DriverManagerPage (premium/driver_manager_page.py)
- `Scan for Updates` (`_ScanWorker` PnP enumeration), device table `Device Name/Class/Version/Provider/Status/Update`; filter QComboBox; QCheckBox options.
- `Install Selected` (restore-point + install via `_InstallWorker`, question confirm), `Backup All` (folder dialog via `_BackupWorker`); QProgressBar.
- backend: `cortex_unified.system_tools.driver_manager.DriverManager`

## VssManagerPage / DevDriveOptimizerPage / BitLockerAuditorPage / JunctionAuditorPage / BitRotScrubberPage / MemoryCompressionPage / SandboxCleanerPage / SmbShareAuditorPage / ProcessTokenPage / StorageGrowthTrackerPage (premium/enterprise_suite_pages.py)
- VssManagerPage: `Audit VSS Shadows`, `Create Snapshot on C:`, `Purge Oldest Shadow`; shadow-copy table.
- DevDriveOptimizerPage: `Audit Storage Drives`; volume-geometry + `fsutil devdrv` table.
- BitLockerAuditorPage: `Audit BitLocker Status` (manage-bde/WMI); encryption table.
- JunctionAuditorPage: `Scan User Profile Links`, `Scan Custom Folder…` (Browse…), `Unlink Selected Dead Junction`; reparse-point table.
- BitRotScrubberPage: `Run Integrity Scrub`; checksum-integrity table.
- MemoryCompressionPage: `Audit Memory Compression`, `Toggle Memory Compression` (Get-MMAgent); memory table.
- SandboxCleanerPage: `Scan Virtual Artifacts`, `Purge Safe Virtual Artifacts`; Sandbox/Hyper-V/WSL artifact table.
- SmbShareAuditorPage: `Audit Network Shares`, `Browse…`; share + SMB-security table.
- ProcessTokenPage: `Audit Process Tokens`; token/integrity-level forensics table.
- StorageGrowthTrackerPage: `Take Snapshot`, `Compare Last 2 Snapshots`; snapshot-diff table. All QTableWidget + worker run on window runtime.
- backend: `cortex_unified.system_tools.vss_manager`, `dev_drive_optimizer`, `bitlocker_auditor`, `junction_auditor`, `bitrot_scrubber`, `memory_compression_tuner`, `sandbox_cleaner`, `smb_share_auditor`, `process_token_auditor`, `storage_growth_tracker`

## LinksManagerPage / FastCopierPage / TimestampTouchPage / ArchiveManagerPage / PrefetchAnalyzerPage / SearchIndexOptimizerPage / DnsBenchmarkPage / DiskBenchmarkPage / MemoryOptimizerPage / DevCleanerPage / BrowserDeepCleanerPage (premium/expanded_tools_pages.py)
- LinksManagerPage: `Choose Folder…`, `Scan for Links`, `Safely Remove Selected Link`; NTFS link table.
- FastCopierPage: `Add Source Files / Folders…`, `Choose Destination Folder…`, `Start Fast Copy`; progress (`Transferring files...`).
- TimestampTouchPage: `Select Files…`, `Apply Timestamp & Attribute Updates`; datetime/attribute editors.
- ArchiveManagerPage: `Open Archive…`, `Test Integrity`, `Extract All…`, `+ Create New Archive…`; archive-entry table.
- PrefetchAnalyzerPage: `Scan Prefetch Traces`, `Flush All Prefetch Traces`; prefetch-entry table.
- SearchIndexOptimizerPage: `Refresh Metrics`, `Compact Database (esentutl /d)`, `Rebuild Search Index`; catalog-size card.
- DnsBenchmarkPage: `Run DNS Benchmark`, `Apply Selected DNS to Adapter`; provider table (KNOWN_DNS_PROVIDERS) + latency results.
- DiskBenchmarkPage: `Select Drive / Folder…`, `Start Benchmark` (`Running storage benchmark (64MB sample)...`); IOPS/throughput table.
- MemoryOptimizerPage: `Refresh Processes`, `Optimize Working Sets`; process-memory table + QCheckBox filters.
- DevCleanerPage: `Scan Dev Caches`, `Clean Selected Caches`; dev-cache table (DevCacheItem).
- BrowserDeepCleanerPage: `Scan Browser Caches`, `Clean Browser Caches`; per-browser target table (BrowserTarget) + QCheckBox profile picks.
- backend: `cortex_unified.system_tools.browser_deep_cleaner`, `dev_cleaner`, `disk_benchmark`, `dns_benchmark`, `memory_optimizer`, `prefetch_analyzer`, `search_index_optimizer` (+ NTFS-links/fast-copy/archive/touch engines)

## FuzzyHashPage (premium/fuzzy_hash_page.py)
- `Choose Folder…` + `Find Fuzzy Duplicates` (ssdeep/TLSH via `_FuzzyWorker`); similarity QSpinBox threshold.
- Results table `["File","Group","Hint"]`; `No fuzzy duplicates found` state.
- backend: `cortex_unified.analyzers.fuzzy_finder.FuzzyDuplicateFinder`

## LicensePage (premium/license_page.py)
- License-key QLineEdit + tier QComboBox; `Activate`, `Start Free Trial`, `Deactivate` (QMessageBox confirms/warnings).
- Feature matrix table `["Feature","Minimum tier","Included"]` (FEATURE_MIN_TIER); status card.
- backend: `cortex_unified.licensing`, `cortex_unified.licensing.license_manager`, `cortex_unified.licensing.tiers`

## LogSweeperPage (premium/log_sweeper_page.py)
- Watched-roots QListWidget: `Add Folder…`, `Select Code Root`, `Remove Selected`; `Find Large Logs (>100MB)` (`_LogWorker`).
- Hits table `["Log file","Size","Path"]`; `Move Selected to Recycle Bin` (question confirm); QProgressBar.
- backend: `cortex_unified.analyzers.cache_cleaner.CacheCleaner`

## MemoryStandbyPurgerPage (premium/memory_standby_page.py)
- Four purge buttons: `Purge Standby List (Command 4)`, `Empty Working Sets (Command 2)`, `Flush Modified Page List (Command 3)`, `1-Click Complete Kernel Purge`; QProgressBar + info/warning result dialogs.
- backend: `cortex_unified.system_tools.memory_standby_purger`

## MftSlackScrubberPage (premium/mft_slack_page.py)
- Drive QComboBox (`C:/D:/E:/F:`); `Analyze MFT Geometry`, `Sanitize MFT Record Slack` (question confirm → `_MftScrubWorker`); QProgressBar + geometry readout.
- backend: `cortex_unified.system_tools.mft_slack_scrubber`

## ModelCachePage (premium/model_cache_page.py)
- `Scan Model Caches` (`_ScanWorker`: HuggingFace `~/.cache/huggingface/hub`, Ollama `~/.ollama/models`); cache table `Store/Path/Exists/Actual size/Explorer sum/Orphans/Hardlink saved`.
- `Preview Orphan Cleanup`, `Clean Orphans` (`_CleanOrphansWorker`, question confirm); empty-state + QProgressBar.
- backend: `cortex_unified.system_tools.model_cache_manager.ModelCacheManager`

## SoftwareUpdaterPage / DriveOptimizerPage / SystemInfoPage / BrokenLinksPage / DuplicateFoldersPage / PackageCachePage / ProjectCachesPage / SecretsScannerPage / VirtualDisksPage (premium/more_pages.py)
- SoftwareUpdaterPage: `Check for Updates` (UpdaterListWorker), table + `Update Selected` / `Update All` (UpgradeWorker).
- DriveOptimizerPage: `Detect Drives` (DriveListWorker), `Optimize Selected` (DriveOptimizeWorker: TRIM/defrag), `Refresh`.
- SystemInfoPage: `Refresh`; hardware/OS spec cards + table (SystemInfoWorker).
- BrokenLinksPage (`Broken Links`): `Choose Folder…` + scan (BrokenLinksWorker); link table; `Move Selected to Recycle Bin`.
- DuplicateFoldersPage (`Duplicate Folders`): `Choose Folder…` + scan (DuplicateFoldersWorker); folder-group table + recycle action.
- PackageCachePage (`System Package Manager Caches`): `Detect Managers`, `Scan for Caches` (PackageCacheWorker), `Clean Selected` (PackageCleanWorker); manager QComboBox.
- ProjectCachesPage (`Project Folder Caches`): `Workspace` / `Auto-Detect` / `+ Add Location` / `Remove Selected` / `Clear All` roots; `Scan for Caches` / `Scan Fixed Drives (auto)` (AutoProjectCacheWorker), `Clean Selected` (ProjectCacheCleanWorker), `Expand All` / `Collapse All`, `Select All` / `Deselect All`, `Export`, QTreeWidget with checkboxes + sort combo.
- SecretsScannerPage: `Choose Folder…`, `Scan for Secrets` (SecretsScanWorker over `run_scan`); finding table + `Export`.
- VirtualDisksPage: `Find Virtual Disks`, `Stop WSL`, `Keep Sparse`, `Compact Selected` (compact/shutdown workers); VHD/WSL table + progress/cancel (`Cancel`, `Cancelling…`).
- backend: `cortex_unified.system_tools.app_updater`, `drive_optimizer`, `system_info`, `cortex_unified.analyzers.broken_link_detector`, `duplicate_folder_finder`, `package_manager_cleaner`, `project_cache_scanner`, `cortex_unified.system_tools.secrets_scanner`, `cortex_unified.ui.premium.workers`, `cortex_unified.core.config`

## NearDuplicatesPage (premium/near_duplicates_page.py)
- `Choose Folder…` + `Find Near-Duplicates` (MinHash/shingle `_NearDupWorker`); QProgressBar.
- Results table `["File","Group","Hint"]`; `No near-duplicates – corpus is diverse` state.
- backend: `cortex_unified.analyzers.near_duplicate_finder.NearDuplicateFinder`

## TrafficMonitorPage / FirewallPage / NetworkMapPage / LanDevicesPage / NetworkToolsPage / LoadTesterPage (premium/network_pages.py)
- TrafficMonitorPage: live traffic table + `Browse…`/filter; per-process bandwidth view (TrafficMonitor).
- FirewallPage: rule table + `Block` / `Allow` / `Block Address` / `Refresh` / `Enable/Disable` / `Remove` (FirewallListWorker/FirewallActionWorker over FirewallManager).
- NetworkMapPage (`Network Map`): `_MapCanvas` topology + `Refresh Map`, `Basic Scan` / `Advanced Audit` / `All TCP Ports` / `Passive Discovery` / `Cancel`.
- LanDevicesPage (`Network Security Audit`): `Scan Device`, `Ping Device`, `Wake` (WoL), `Open Service`, `More Controls ›`, `Run Expert Scan`, `Save Metadata`, `Browse`, `Export Inventory CSV` / `Import Metadata CSV`, `Lookup Exposure`, `Create / Update Schedule` / `Remove Schedule` / `Refresh Status`, `Update Vendors` (IEEE DB), `Export Report`, `This PC` (LanScanWorker/VendorDatabaseWorker/NetworkScheduleWorker/ExposureLookupWorker/DeviceActionWorker); vendor QComboBox, host QLineEdit, device QTableWidget.
- NetworkToolsPage: target QLineEdit + port QSpinBox/QComboBox (COMMON_PORTS); ping/traceroute/DNS/port-scan output (QTextEdit) via `_ToolWorker` (NetworkTools).
- LoadTesterPage: `Check Authorization` (TargetAuthorizer: `Checking authorization…` + HTML authorize instructions), `Start Test`/`Stop` (LoadTestWorker/esc `Stopping…`); target/rate/duration QSpinBox group + results table.
- backend: `cortex_unified.system_tools.network_traffic`, `firewall_manager`, `network_discovery`, `network_inventory`, `network_service_scanner`, `network_tools`, `network_automation`, `external_exposure`, `load_tester`, `cortex_unified.system_tools.oui`

## ShaderCachePage / AiTelemetryCleanerPage / SsdTrimOptimizerPage / RestartManagerUnlockerPage / VssHealthAnalyzerPage / DevPackageCachePage / ChecksumMatrixPage (premium/nextgen_suite_pages.py)
- ShaderCachePage: `Scan Shader Caches`, `Clean Stale Shaders`; GPU/DirectX store table (QCheckBox picks).
- AiTelemetryCleanerPage: `Scan AI Telemetry`, `Clean Caches & Truncate WAL`; Recall/AI store table.
- SsdTrimOptimizerPage: `Audit Volumes & TRIM`, `Execute ReTrim on Selected Drive`; TRIM/wear table.
- RestartManagerUnlockerPage: `Inspect Locks`, `Browse…`, `Unlock File (Kill Locking Procs)`; lock-report table + file picker (`Browse File…`).
- VssHealthAnalyzerPage: `Inspect VSS Subsystem`, `Reset Stalled VSS Writers`; writer/shadow-storage table.
- DevPackageCachePage: `Scan Developer Stores`, `Purge Selected Store Caches`; toolchain-dir table.
- ChecksumMatrixPage: `Calculate Hashes`, `Browse File…` / `Browse Folder…`, `Generate .sha256 Manifest`; hash QComboBox (algo), QSpinBox threads, file-hash + manifest-verification tables.
- backend: `cortex_unified.system_tools.shader_cache_cleaner`, `ai_telemetry_cleaner`, `ssd_trim_optimizer`, `restart_manager_unlocker`, `vss_health_analyzer`, `dev_package_cache_cleaner`, `checksum_matrix`

## NexusExplorerPage (premium/nexus_page.py)
- Embeds full native Qt6 file explorer in-page (same process/window): folder tree, file views, search; lazy construction on first visit.
- Degrades to in-page `_ErrorCard` (`Nexus File Manager` + selectable error text) — never crashes host window; outer scroll stays quiet, only inner explorer scrolls.
- backend: `cortex_unified.explorer.widget.ExplorerWidget` (+ `DARK_QSS`; `NexusExplorer/native` fallback path)

## PerceptualDuplicatesPage (premium/perceptual_duplicates_page.py)
- `Choose Folder…` + `Find Visual Duplicates` (pHash `_PerceptualWorker`); similarity QSpinBox.
- Results table `["Photo","Group","Hint"]`; `No visual duplicates found`.
- backend: `cortex_unified.analyzers.perceptual_duplicate_finder.PerceptualDuplicateFinder`

## PortableManagerPage (premium/portable_manager_page.py)
- `Add Root` (dir dialog) + `Scan` (`_PortableWorker`); app table `App Name/Version/Installed/Latest/Update Available`; QComboBox source filter; `Auto-update on scan` QCheckBox; QProgressBar; update via `_UpdateWorker` (question confirm).
- backend: `cortex_unified.analyzers.portable_manager.PortableManager`

## EnvVariableManagerPage / WindowsServiceManagerPage / FontCacheManagerPage / TempFolderCleanerPage / ContextMenuManagerPage / PagefileOptimizerPage / DiagnosticDataManagerPage / StartupImpactPage / SlackSpaceAnalyzerPage / EventLogMonitorPage (premium/power_suite_pages.py)
- EnvVariableManagerPage: `Analyze PATH`, `Clean User PATH (Remove Dead & Duplicates)`, `Export to .env…`; PATH-entry table.
- WindowsServiceManagerPage: `Scan Services`, `Apply Profile`; service table (ServiceInfo) + profile QComboBox.
- FontCacheManagerPage: `Scan Installed Fonts`, `Remove Orphaned Font Entries`; font/registry table.
- TempFolderCleanerPage: `Scan All Temp Locations`, `Purge Stale Temp Files`; multi-location table (TempLocation).
- ContextMenuManagerPage: `Scan Context Menu`, `Disable Selected Entry`, `Enable Selected Entry`; shell-extension table.
- PagefileOptimizerPage: `Apply Fixed Allocation`, `Reset to System-Managed`; virtual-memory status card (VirtualMemoryStatus).
- DiagnosticDataManagerPage: `Audit Telemetry State`, `Enforce Maximum Privacy Preset`; telemetry-policy table.
- StartupImpactPage: `Scan Startup Impact`; StartupApproved/impact table.
- SlackSpaceAnalyzerPage: `Choose Folder to Analyze…`, `Analyze Slack Waste`; cluster/slack forensics table.
- EventLogMonitorPage: `Scan Event Log for Faults`, `Toggle Selected Item State`/`Export`; kernel-crash/fault table. All QTableWidget + QMessageBox confirms.
- backend: `cortex_unified.system_tools.env_variable_manager`, `service_manager`, `font_cache_manager`, `temp_folder_cleaner`, `context_menu_manager`, `pagefile_optimizer`, `diagnostic_data_manager`, `startup_impact_analyzer`, `slack_space_analyzer`, `event_log_monitor`

## HashVerifierPage / BatchRenamerPage / FolderSyncPage / FileSplitterPage / FileUnlockerPage / AdsManagerPage / EventLogCleanerPage / SystemCacheRebuilderPage / NetworkOptimizerPage / CrashDumpCleanerPage (premium/power_tools_pages.py)
- HashVerifierPage: `Select File…`, `Compute Hashes` (algo QComboBox), `Verify Manifest (.sfv / .sha256)…`, `Copy` hash; hash-result table.
- BatchRenamerPage: `Select Files…`, preview table, `Apply Rename`, `Undo Last Rename`; pattern QLineEdit + QComboBox rules.
- FolderSyncPage: `Left Folder…` / `Right Folder…` pickers, `Compare Folders` (diff table), `Synchronize Now` (direction QComboBox).
- FileSplitterPage: `Select File…`, chunk-size QSpinBox, `Split File Now`, `Select Part (.001 / .split.json)…`, `Join Files Now`.
- FileUnlockerPage: `Select Locked File…`, `Inspect Locks` (handle table), `Kill Process` (confirm).
- AdsManagerPage: `Select File…`, stream table, `Unblock File (Remove Zone.Id)`, `Delete Stream`.
- EventLogCleanerPage: log QComboBox + `Refresh Logs`, `Clear All Event Logs` (confirm).
- SystemCacheRebuilderPage: `Rebuild Font & Icon Caches Now`; status readout.
- NetworkOptimizerPage: `Set TCP Normal (Default)`, `Set TCP Experimental (Gaming/High Throughput)`, `Flush DNS Cache`, `Clear ARP Cache`, `Reset Winsock`, `Complete 1-Click Repair`.
- CrashDumpCleanerPage: `Scan Crash Dumps`, `Clean All Crash Dumps`; dump table (CrashDumpCleaner).
- backend: `cortex_unified.system_tools.crash_dump_cleaner`, `event_log_cleaner`, `network_stack_optimizer`, `system_cache_rebuilder` (+ hash/rename/sync/split/unlock/ADS engines)

## PrivacyBlockerPage (premium/privacy_blocker_page.py)
- Telemetry-tweak table `["Tweak Name","Category","Status","Description"]` (TELEMETRY_TWEAKS) with QCheckBox picks + category QComboBox; QProgressBar (`_PrivacyWorker`).
- `Apply Selected`, `Revert All` (question confirm; `Reverting all applied tweaks…`).
- backend: `cortex_unified.system_tools.privacy_blocker` (+ `TELEMETRY_TWEAKS`)

## RegistryAICleanerPage (premium/registry_ai_page.py)
- `Choose Registry Root…` + category QComboBox (`All Categories/App Paths Only/Uninstall Only/SharedDLLs Only/Fonts…`) + risk-threshold QSpinBox + `Scan` (`_RegistryWorker` over AIRegistryCleaner).
- Issue table `["Key Path","Value Name","Category","Risk Score","Recommendation"]`; clean action; `No issues found above threshold` state.
- backend: `cortex_unified.analyzers.registry_cleaner_ai.AIRegistryCleaner` (+ `_CATEGORY_DEFS`)

## HealthReportPage / BackupsPage (premium/report_pages.py)
- HealthReportPage: `Export HTML` / `Export JSON` / `Export Text`, `Open Last Report` (file dialog), `Refresh` (HealthReportWorker over ReportsGenerator + DiskHealthMonitor/SystemInfo); summary cards + table.
- BackupsPage: manifest table + `Refresh`, row-select → `Preview Restore` (dialog), `Restore Selected` (RestoreWorker over RestoreManager, question confirm); `No backups found yet…` state; QProgressBar.
- backend: `cortex_unified.reports.reports.ReportsGenerator`, `cortex_unified.reports.restore_manager.RestoreManager`, `cortex_unified.system_tools.disk_health`, `cortex_unified.system_tools.system_info`

## S3FifoPage (premium/s3_fifo_page.py)
- Cache-trace options (QSpinBox sizes); `Run Benchmark` (`_BenchWorker` over S3FIFO vs LRU); QProgressBar.
- Result table `["Metric","Value"]` + verdict label (`S3-FIFO beats LRU on this trace`).
- backend: `cortex_unified.system_tools.s3_fifo.S3FIFO`

## SearchIndexOptimizerPage (premium/search_optimizer_page.py)
- `Inspect Search Database` (catalog/EDB size card: `Querying Windows Search catalog...`, `Warning: Inflated (> 1 GB)`); QProgressBar (`_SearchWorker`).
- `Compact Database (esentutl /d)` and `Rebuild Index Catalog` (each question confirm); elevation state (`Elevated (Full Control)`).
- backend: `cortex_unified.system_tools.search_index_optimizer`

## SecureShredderPage (premium/secure_shredder_page.py)
- `Add Files…` (getOpenFileNames) / `Add Folder…` (dir dialog) into queue table `["File Path","Size","Standard","Status"]`; `Clear List`.
- Standard QComboBox (NIST Clear/Purge, DoD 3/7-pass, Gutmann 35, HMG IS5, VSITR, GOST, Schneier, RCMP, NSA EPL, Zero/One/Random fills); storage-type label; `Verify after wipe` QCheckBox; QProgressBar (`_ShredWorker`); `Shred Selected` (warning confirm).
- backend: `cortex_unified.system_tools.secure_shredder.SecureShredder/ShredStandard/StorageType`

## SrumBamCleanerPage (premium/srum_bam_page.py)
- `Inspect Execution Traces` (reads BAM/DAM hives + SRUDB via `_SrumBamWorker`); trace table `["Executable Path","Last Execution Time (UTC)","User SID","Subsystem"]`.
- `Sanitize BAM Execution History` (question confirm → sanitizing state); QProgressBar.
- backend: `cortex_unified.system_tools.srum_bam_cleaner`

## StartupOptimizerPage (premium/startup_optimizer_page.py)
- `Refresh` scan (`_StartupScanWorker` over registry/folders/tasks); entry table (name/location/profile) with filter QComboBox + StatePanel + QProgressBar.
- `Disable Selected` (`_DisableWorker` → CortexBackup registry stash), `Enable Selected` (`_EnableWorker` restore); info dialogs; `Scanning registry, folders, and scheduled tasks…` / `No entries found`.
- backend: `cortex_unified.system_tools.startup_optimizer.StartupOptimizer`

## PrivacyPage / StartupPage / ProcessesPage / NetworkPage / UninstallerPage / LeftoverScannerPage / TelemetryBlocker / RegistryCleaner (premium/system_pages.py)
- PrivacyPage: `Scan Browsers & Traces` (PrivacyScanWorker), trace table + `Sweep Selected` (PrivacyCleanWorker over PrivacyCleaner).
- StartupPage: table + `Refresh`, `Disable Selected` (StartupListWorker over StartupManager).
- ProcessesPage: `Refresh`, `End Task` (TaskSnapshotWorker/NetworkWorker? TaskManager); memory-explain card (`Why don't these numbers add up?` toggle).
- NetworkPage: connection table + `Refresh`, `End Owning Task` (NetworkMonitor; orange rows = listen-on-all-interfaces).
- UninstallerPage (`Deep Uninstaller`): `Refresh`, `Uninstall Selected` (UninstallerListWorker over AppUninstaller), `Scan for Leftovers`, `Find Orphan Folders`, leftover/orphan tables + `Clean Selected` / `Keep Selected` (LeftoverScanWorker/OrphanScanWorker/LeftoverCleanWorker + ExclusionsStore `_LeftoverSection`).
- TelemetryBlocker: `Block All Telemetry`, `Restore Defaults` (TelemetryStatusWorker/TelemetryApplyWorker over TelemetryBlocker).
- RegistryCleaner: `Scan Registry`, `Clean All Found` (RegistryScanWorker/RegistryCleanWorker over RegistryCleaner). All QTableWidget/QTreeWidget + QProgressBar + QMessageBox.
- backend: `cortex_unified.analyzers.privacy_cleaner`, `cortex_unified.system_tools.startup_manager`, `task_manager`, `network_monitor`, `app_uninstaller`, `leftover_cleaner`, `telemetry_blocker`, `registry_cleaner`, `cortex_unified.licensing.Feature`

## PerformancePage / BrowserExtensionsPage / DriverInventoryPage (premium/tools_pages.py)
- PerformancePage: `Detect Plans` (PowerPlanListWorker), plan table, `Activate Selected` (PowerPlanSetWorker over PerformanceTuner).
- BrowserExtensionsPage: `Scan Extensions` (ExtensionAuditWorker over BrowserExtensionAuditor); extension table; `No extensions found…` state.
- DriverInventoryPage: `List Drivers` (DriverListWorker over DriverInventory); driver table (QTableView/QTableWidget + QProgressBar).
- backend: `cortex_unified.system_tools.performance_tuner`, `browser_extensions`, `driver_inventory`

## VideoDuplicatesPage (premium/video_duplicates_page.py)
- `Choose Folder…` + `Find Video Duplicates` (`_VideoWorker`); QProgressBar.
- Results table `["Video File","Group","Hint"]`; `No video duplicates found`.
- backend: `cortex_unified.analyzers.video_duplicate_finder.VideoDuplicateFinder`

## WinUpdateRepairPage (premium/win_update_repair_page.py)
- `Run Preflight` (`_PreflightWorker`: `Services: / Network: / Pending reboot: / Recent errors:` card); phase table `["Phase","Status","Duration","Details"]`; QCheckBox repair options.
- `Run Repair` (`_RepairWorker`, question confirm); QProgressBar + info dialogs.
- backend: `cortex_unified.system_tools.windows_update_repair`

## Winapp2CleanerPage (premium/winapp2_page.py)
- `Scan Installed Applications` (`_Winapp2Worker` over Winapp2 definitions); rule table `["Application / Rule","Category","Target Cache Path","Size"]` with QCheckBox picks.
- `Clean Selected Caches` (question confirm); scanning/cleaning states + QProgressBar.
- backend: `cortex_unified.system_tools.winapp2_cleaner.Winapp2Cleaner/AppCleanTarget/Winapp2Report`

## WslPage (premium/wsl_page.py)
- `List Distros` (`_WslListWorker`); distro table `["Distro","State","Path","Size (on disk)","Size (logical)"]` + QProgressBar.
- `Stop WSL (wsl --shutdown)` (`_WslShutdownWorker`, confirm), `Compact Selected` (vhdx compact via WslCleaner, confirm); `WSL is not installed…` / `No WSL distros detected…` states.
- backend: `cortex_unified.system_tools.wsl_cleaner.WslCleaner`

---

## DashboardTab (tabs/dashboard_tab.py)
- `START SMART SCAN` (OptimizerWorker/SmartScannerWorker with `Scanning…` progress); health-score cards; `OPTIMIZE NOW` / `RESCAN SYSTEM` apply fixes.
- backend: `cortex_unified.core.smart_scanner`, `cortex_unified.core.config`

## EmptyFilesTab (tabs/empty_files_tab.py)
- `Browse` (dir dialog) + `Scan` (EmptyFilesWorker over Scanner); files/dirs tables; `Select All` / `Deselect All` / `Delete Selected` (Deleter, confirm); `Scan completed` status.
- backend: `cortex_unified.core.scanner.Scanner`, `cortex_unified.core.deleter.Deleter`

## DeepCleanerTab (tabs/deep_cleaner_tab.py)
- `🔍 Start Deep Scan` (DeepCleanerWorker); category tree with checkboxes; `☑ Check All` / `☐ Uncheck All`; `🗑️ Clean Selected` (Deleter); `Scan completed ✅` status.
- backend: `cortex_unified.analyzers.deep_cleaner.DeepCleaner`, `cortex_unified.core.deleter`

## DuplicatesTab (tabs/duplicates_tab.py)
- `Browse` + `Find Duplicates` (DuplicateFinderWorker); hash-group table; `Select All` / `Deselect All` / `Delete Selected` (`Deleting files...` progress).
- backend: `cortex_unified.analyzers.duplicate_finder.DuplicateFinder`, `cortex_unified.core.deleter`

## LargeFilesTab (tabs/large_files_tab.py)
- `Browse` + `Find Large Files` (LargeFileFinderWorker with size QSpinBox); size-sorted table; `Select All` / `Deselect All` / `Delete Selected`.
- backend: `cortex_unified.analyzers.large_file_finder.LargeFileFinder`, `cortex_unified.core.deleter`

## DiskAnalyzerTab (tabs/disk_analyzer_tab.py)
- `Browse` + `Analyze Disk` (DiskAnalyzerWorker); folder table; `TreeMap View` / `Sunburst View` / `Interactive Dashboard` visualizations; `Export Visualization`.
- backend: `cortex_unified.analyzers.disk_analyzer.DiskAnalyzer`, `cortex_unified.visualization.interactive_dashboard`

## DockerTab (tabs/docker_tab.py)
- `Scan Docker Resources` (DockerScanWorker); image/container/volume table with availability banner (`✓ Docker is available…` / `✗ Docker is not available…`); `Clean Up Resources` (DockerCleanupWorker).
- backend: `cortex_unified.analyzers.docker_cleaner.DockerCleaner`, `cortex_unified.core.deleter`

## BrokenLinksTab (tabs/broken_links_tab.py)
- `Browse` + `Scan for Broken Links` (BrokenLinksWorker); link table; `Select All` / `Deselect All` / `Repair Selected` (LinkRepairWorker) / `Export Results`.
- backend: `cortex_unified.analyzers.broken_link_detector`

## RestoreTab (tabs/restore_tab.py)
- `Refresh Recovery Points` (manifest list); snapshot table; `Restore Selected Snapshot` + `Delete Backup` (RestoreWorker, confirms).
- backend: `cortex_unified.reports.restore_manager.RestoreManager`

## SettingsTab (tabs/settings_tab.py)
- Forms for scan/delete preferences, language selector (i18n manager), performance toggles; `Save System Configurations` persists via QSettings/Config.
- backend: `cortex_unified.performance.settings_integration`, `cortex_unified.translations.settings_integration`, `cortex_unified.core.config`

## UninstallerTab (tabs/uninstaller_tab.py)
- `Refresh` app list (AppListWorker); app table; `Run Official Uninstaller`; `Scan for Leftover Files` (ResidualScanWorker); leftover table + `Clean Selected (Recycle Bin)` (ResidualCleanWorker).
- backend: `cortex_unified.system_tools.app_uninstaller`, `cortex_unified.system_tools.leftover_cleaner`

## PrivacyTab (tabs/privacy_tab.py)
- `Scan Browsers & System Traces` (BrowserScanWorker); trace table; `Sweep Selected Data` (PrivacyCleaner); `Block All Telemetry` / `Restore Defaults` + `All Blocked` status (TelemetryBlocker).
- backend: `cortex_unified.analyzers.privacy_cleaner`, `cortex_unified.system_tools.telemetry_blocker`

## PackageManagerTab (tabs/package_manager_tab.py)
- `🔍 Detect Available Package Managers` (detecting…/not-found states); `➕ Add Folder` / `➖ Remove Selected` / `🗑️ Clear All` custom roots; `🔍 Scan for Caches` (PMScanWorker/PMSearchWorker); cache table + `🧹 Clean Selected Caches` (PMCleanWorker).
- backend: `cortex_unified.analyzers.package_manager_cleaner.PackageManagerCleaner`, `cortex_unified.core.deleter`

## FileShredderTab (tabs/file_shredder_tab.py)
- `Add Files` / `Add Folder` (file/dir dialogs) into queue table; `Remove Selected` / `Clear All`; passes QSpinBox + mode QComboBox; `Start Shredding` (FileShredderWorker over AdvancedShredder + FreeSpaceWiper; Pro-gated via licensing Feature).
- backend: `cortex_unified.analyzers.advanced_shredder.AdvancedShredder`, `cortex_unified.system_tools.free_space_wipe`, `cortex_unified.licensing`

## SchedulerTab (tabs/scheduler_tab.py)
- Task table + `Add New Task` (AddTaskDialog: schedule QComboBox + path QLineEdit + `Create Task`/`Browse...`/`Cancel`), `Remove Task`, `Refresh List`, `Run Selected Now`; rules section (`Create Rule`/`Test Rule`/`Delete Rule`/`Refresh Rules` over AutoCleanRules + `Apply Auto-Rules`, `Daemon: ACTIVE` badge).
- backend: `cortex_unified.scheduler.scheduler.TaskScheduler`, `cortex_unified.scheduler.auto_clean_rules.AutoCleanRules`

## ReportsTab (tabs/reports_tab.py)
- `Generate Report` / `Preview Report` (ReportsGenerator); report list + `Open Selected Report`/`Refresh Reports`/`Save as Template`/`Load Template`; `Schedule Report (Pro)` (TaskScheduler, license-gated); `Refresh Activity Log`; chart zoom `🔍 Zoom In` / `🔍 Zoom Out` / `🔄 Reset Zoom`.
- backend: `cortex_unified.reports.reports.ReportsGenerator`, `cortex_unified.scheduler.scheduler`, `cortex_unified.licensing`

## ResourceMonitorTab (tabs/resource_monitor_tab.py)
- `Start Monitoring` / `Stop Monitoring` live CPU/RAM/disk charts + process table (ResourceMonitor).
- backend: `cortex_unified.performance.resource_monitor.ResourceMonitor`

## StartupManagerTab (tabs/startup_manager_tab.py)
- `Refresh Startup Items` (StartupScanWorker); startup-entry table; `Disable Selected Item` (confirm).
- backend: `cortex_unified.system_tools.startup_manager.StartupManager`

## SystemToolsTab (tabs/system_tools_tab.py)
- Container hub embedding ProcessAnalyzerTab + RegistryCleanerTab + StartupManagerTab (no direct actions; navigation only).
- backend: `cortex_unified.ui.tabs.process_analyzer_tab`, `registry_cleaner_tab`, `startup_manager_tab`

## ProcessAnalyzerTab (tabs/process_analyzer_tab.py)
- `Refresh Activity` (ProcessAnalyzerWorker); live process table (PID/CPU/RAM) with kill/sort.
- backend: `cortex_unified.system_tools.process_analyzer.ProcessAnalyzer`

## RegistryCleanerTab (tabs/registry_cleaner_tab.py)
- `Scan Registry` (RegistryScanWorker); issue table; `Clean Registry` (RegistryCleanWorker, backup confirm).
- backend: `cortex_unified.system_tools.registry_cleaner.RegistryCleaner`

## SecurityScannerTab (tabs/security_scanner_tab.py)
- `Browse` target + `🔍 Start Security Scan` (SentinelScanWorker over secrets scanner); finding table; `📄 Export JSON Report` (file dialog); `Starting security scan...` progress.
- backend: `cortex_unified.system_tools.secrets_scanner`

## HeuristicsTab (tabs/heuristics_tab.py)
- `Browse...` + `Scan for Leftovers` (Scanner heuristics); leftover table; `Clean Up Leftovers` (Deleter).
- backend: `cortex_unified.core.scanner`, `cortex_unified.core.deleter`

## BaseTab (tabs/base_tab.py)
- Non-visual base class: translator hookup, SafetyManager-guarded `run_safety_checked` scaffold, shared worker/signal helpers. No direct user actions.
- backend: `cortex_unified.ui.safety`, `cortex_unified.core.config`, `cortex_unified.translations.translator`

---

## DeepCleanerGUI shell (ui/main_window.py)
- QMainWindow + NavigationController with 19 icon tabs: Dashboard, Cleaner (EmptyFiles), Duplicates, Deep Cleaner, Large Files, Disk Analyzer, Docker, Broken Links, Restore, Settings, Package Caches, File Shredder, Scheduler (+ `Scheduled Tasks`/`Auto-Clean Rules` sub-tabs with `Create Task`/`Run Selected Now`/`Delete Selected`/`Refresh Tasks`/`Create Rule`/`Test Rule`/`Delete Rule`/`Refresh Rules`), Reports (`Generate/Preview/Schedule/Refresh/Save/Load Template`), Resource Monitor (`Start/Stop Monitoring`), System Tools (Process/Registry/Startup), Security Scanner, Deep Uninstaller, Privacy Shield; ScanWorker/DeleteWorker/MultiDriveScanWorker (QThread) + progress/cancel (`Export`, `Cancel`, `Browse...`, `Scan for Leftovers`, `Clean Up Leftovers`, `Add Files/Folder`, `Remove Selected`, `Clear All`, `Start Shredding`, `Test Connection`, `Add`, `View`, `Delete`, `Close` dialogs).
- backend: `cortex_unified.core.scanner`, `core.deleter`, `core.config`, `analyzers.*` (duplicate/large-file/cache/old-file/shredder/disk/duplicate-folder/docker/broken-link/package-manager), `system_tools.startup_manager/process_analyzer/registry_cleaner`, `scheduler.scheduler/auto_clean_rules`, `reports.restore_manager/reports`, `ui.navigation.navigation_controller`, `ui.safety.safety_manager`, `ui.tray_icon.SystemTrayManager`

## Safety layer (ui/safety/safety_manager.py, path_validator.py, process_manager.py, manifest_system.py)
- SafetyManager (non-visual gate used by every tab/page): operation factory (`create_operation`), path-safety validation, dry-run enforcement, resource limits, custom callbacks, `validate_operation`/`execute_safe_operation` with confirm/error dialogs surfaced by callers; system blacklists + whitelist/blacklist config.
- PathValidator: critical-dir + symlink + permission checks (`is_safe_to_delete`, `validate_operation_paths`, whitelist/blacklist, blocking-reason summary).
- ProcessManager: allow-listed executable validation, arg sanitization, `execute_safe_command`/`execute_with_progress`, timeouts, kill/cleanup.
- ManifestSystem: pre-op manifests (`create_operation_manifest`), per-file hash log, error log, finalize, restore-point listing (`get_restore_operations`/`list_manifests`/`get_manifest_details`), retention cleanup. No direct widgets; backs Refresh/Restore/Delete/Preview actions.
- backend: `cortex_unified.ui.safety` (pure service layer; no engine dependency beyond caller-supplied callbacks)

## SystemTrayManager (ui/tray_icon.py)
- QSystemTrayIcon (`Cortex Cleaner — System Monitor`, bundled `assets/icon.png` or OS fallback) with menu: `Open Cortex Cleaner` (show/raise window), `Instant Smart Scan` (opens Dashboard → `run_smart_scan`), `Exit` (stops agent, hides icon, quits); click-to-show activation.
- BackgroundAgent (15s QThread): `High Memory Usage` / `High CPU Usage` / `Low Disk Space` balloon alerts suggesting Cleaner/startup-optimizer actions.
- backend: `cortex_unified.core.background_agent.BackgroundAgent`

---

## Counts
- Premium page files audited: 42 (`*_pages.py` + `*_page.py`); individual premium GUI pages: ~127 (30 single-page files incl. Nexus + License; ~97 sub-pages inside 12 aggregate files).
- Legacy tab files: 24 (23 user-facing tabs + BaseTab scaffold); main-window shell: 1 (DeepCleanerGUI, 19 nav tabs); safety modules: 4; tray manager: 1.
- Total user-facing surfaces: ~152 (127 premium pages + 23 tabs + main shell + tray). Total discrete user actions catalogued: ~640 (scan/analyze/refresh buttons, tables with select-all/clean/delete/sweep/shred/compact/repair/optimize/block/uninstall/export/preview/restore/sync/split/verify/benchmark pickers, combos, checkboxes, file/folder dialogs, confirm + progress + empty-state dialogs).
