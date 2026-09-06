# Master Reference: CLI & GUI Features and Double-Check Audit

> Complete mapping of every CLI command and every GUI tool page, with cross-verification of backend tool integration.

## 1. GUI Tool Pages Master Registry (139 Tools)

| ID | Tool Title | Sidebar Group | Factory Path | Interactive Status |
|---|---|---|---|---|
| `dashboard` | System Overview Dashboard | `overview` | `cortex_unified.ui.premium.window:DashboardPage` | Fully Implemented & Verified |
| `health` | PC Health Check | `overview` | `cortex_unified.ui.premium.analysis_pages:HealthCheckPage` | Fully Implemented & Verified |
| `cleanuphub` | One-Click Cleanup Hub | `cleanup` | `cortex_unified.ui.premium.cleanup_hub_page:CleanupHubPage` | Fully Implemented & Verified |
| `duplicates` | Duplicate Files Finder | `cleanup` | `cortex_unified.ui.premium.window:DuplicatesPage` | Fully Implemented & Verified |
| `photos` | Similar & Duplicate Photos | `cleanup` | `cortex_unified.ui.premium.window:DuplicatePhotosPage` | Fully Implemented & Verified |
| `dupfolders` | Duplicate Folders Finder | `cleanup` | `cortex_unified.ui.premium.more_pages:DuplicateFoldersPage` | Fully Implemented & Verified |
| `large` | Large Files Finder | `cleanup` | `cortex_unified.ui.premium.window:LargeFilesPage` | Fully Implemented & Verified |
| `empty` | Empty Files & Folders | `cleanup` | `cortex_unified.ui.premium.window:EmptyPage` | Fully Implemented & Verified |
| `analyzer` | Visual Disk Space Map | `cleanup` | `cortex_unified.ui.premium.analysis_pages:DiskAnalyzerPage` | Fully Implemented & Verified |
| `brokenlinks` | Broken Shortcuts & Links | `cleanup` | `cortex_unified.ui.premium.more_pages:BrokenLinksPage` | Fully Implemented & Verified |
| `logsweep` | System & App Log Sweeper | `cleanup` | `cortex_unified.ui.premium.log_sweeper_page:LogSweeperPage` | Fully Implemented & Verified |
| `packages` | Developer Package Caches | `cleanup` | `cortex_unified.ui.premium.more_pages:PackageCachePage` | Fully Implemented & Verified |
| `projcaches` | Project Build Caches | `cleanup` | `cortex_unified.ui.premium.more_pages:ProjectCachesPage` | Fully Implemented & Verified |
| `modelcache` | AI Model Cache Cleaner | `cleanup` | `cortex_unified.ui.premium.model_cache_page:ModelCachePage` | Fully Implemented & Verified |
| `neardup` | Similar Text Documents | `cleanup` | `cortex_unified.ui.premium.near_duplicates_page:NearDuplicatesPage` | Fully Implemented & Verified |
| `perceptual` | Similar Photo Matching | `cleanup` | `cortex_unified.ui.premium.perceptual_duplicates_page:PerceptualDuplicatesPage` | Fully Implemented & Verified |
| `registryai` | Intelligent Registry Cleaner | `cleanup` | `cortex_unified.ui.premium.registry_ai_page:RegistryAICleanerPage` | Fully Implemented & Verified |
| `fuzzyhash` | Fuzzy Duplicate Finder | `cleanup` | `cortex_unified.ui.premium.fuzzy_hash_page:FuzzyHashPage` | Fully Implemented & Verified |
| `audio` | Duplicate Music & Audio | `cleanup` | `cortex_unified.ui.premium.audio_duplicates_page:AudioDuplicatesPage` | Fully Implemented & Verified |
| `video` | Duplicate Video Files | `cleanup` | `cortex_unified.ui.premium.video_duplicates_page:VideoDuplicatesPage` | Fully Implemented & Verified |
| `cdc` | Block-Level Deduplicator | `cleanup` | `cortex_unified.ui.premium.cdc_page:CdcPage` | Fully Implemented & Verified |
| `cloud` | Cloud Storage Cache Cleaner | `cleanup` | `cortex_unified.ui.premium.cloud_storage_page:CloudStoragePage` | Fully Implemented & Verified |
| `portable` | Portable Applications Manager | `cleanup` | `cortex_unified.ui.premium.portable_manager_page:PortableManagerPage` | Fully Implemented & Verified |
| `crashdumps` | Crash Dumps & Error Reports | `cleanup` | `cortex_unified.ui.premium.power_tools_pages:CrashDumpCleanerPage` | Fully Implemented & Verified |
| `eventlogs` | Windows Event Log Cleaner | `cleanup` | `cortex_unified.ui.premium.power_tools_pages:EventLogCleanerPage` | Fully Implemented & Verified |
| `devcleaner` | Software Development Artifacts | `cleanup` | `cortex_unified.ui.premium.expanded_tools_pages:DevCleanerPage` | Fully Implemented & Verified |
| `browserdeep` | Deep Web Browser Cleaner | `cleanup` | `cortex_unified.ui.premium.expanded_tools_pages:BrowserDeepCleanerPage` | Fully Implemented & Verified |
| `imgopt` | Image Compressor & Optimizer | `cleanup` | `cortex_unified.ui.premium.apex_tools_pages:ImageOptimizerPage` | Fully Implemented & Verified |
| `fonts` | Font Cache & Registry Optimizer | `cleanup` | `cortex_unified.ui.premium.power_suite_pages:FontCacheManagerPage` | Fully Implemented & Verified |
| `tempcleaner` | Deep System Temp Cleaner | `cleanup` | `cortex_unified.ui.premium.power_suite_pages:TempFolderCleanerPage` | Fully Implemented & Verified |
| `nexus` | Nexus File Explorer | `files` | `cortex_unified.ui.premium.nexus_page:NexusExplorerPage` | Fully Implemented & Verified |
| `hasher` | File Hash & Checksum Verifier | `files` | `cortex_unified.ui.premium.power_tools_pages:HashVerifierPage` | Fully Implemented & Verified |
| `renamer` | Batch File Renamer | `files` | `cortex_unified.ui.premium.power_tools_pages:BatchRenamerPage` | Fully Implemented & Verified |
| `foldersync` | Folder Compare & Sync | `files` | `cortex_unified.ui.premium.power_tools_pages:FolderSyncPage` | Fully Implemented & Verified |
| `splitter` | Large File Splitter & Joiner | `files` | `cortex_unified.ui.premium.power_tools_pages:FileSplitterPage` | Fully Implemented & Verified |
| `unlocker` | Locked File Unlocker | `files` | `cortex_unified.ui.premium.power_tools_pages:FileUnlockerPage` | Fully Implemented & Verified |
| `adsmanager` | NTFS Alternate Data Streams (ADS) | `files` | `cortex_unified.ui.premium.power_tools_pages:AdsManagerPage` | Fully Implemented & Verified |
| `linksmanager` | Symbolic Links & Junctions | `files` | `cortex_unified.ui.premium.expanded_tools_pages:LinksManagerPage` | Fully Implemented & Verified |
| `fastcopier` | High-Speed File Copier | `files` | `cortex_unified.ui.premium.expanded_tools_pages:FastCopierPage` | Fully Implemented & Verified |
| `timestamptouch` | File Date & Timestamp Editor | `files` | `cortex_unified.ui.premium.expanded_tools_pages:TimestampTouchPage` | Fully Implemented & Verified |
| `archivemanager` | Archive Studio (Zip/7z/Tar) | `files` | `cortex_unified.ui.premium.expanded_tools_pages:ArchiveManagerPage` | Fully Implemented & Verified |
| `sniffer` | File Type & Header Inspector | `files` | `cortex_unified.ui.premium.apex_tools_pages:FileSignatureSnifferPage` | Fully Implemented & Verified |
| `binarydiff` | Binary & Hex File Compare | `files` | `cortex_unified.ui.premium.apex_tools_pages:BinaryDifferPage` | Fully Implemented & Verified |
| `usnjournal` | NTFS Change Journal (USN) Viewer | `files` | `cortex_unified.ui.premium.apex_tools_pages:UsnJournalPage` | Fully Implemented & Verified |
| `par2` | PAR2 Archive Parity & Repair | `files` | `cortex_unified.ui.premium.apex_tools_pages:Par2RecoveryPage` | Fully Implemented & Verified |
| `slackspace` | NTFS Cluster Slack Analyzer | `files` | `cortex_unified.ui.premium.power_suite_pages:SlackSpaceAnalyzerPage` | Fully Implemented & Verified |
| `updater` | Software Updater | `system` | `cortex_unified.ui.premium.more_pages:SoftwareUpdaterPage` | Fully Implemented & Verified |
| `drives` | Drive Optimizer (TRIM & Defrag) | `system` | `cortex_unified.ui.premium.more_pages:DriveOptimizerPage` | Fully Implemented & Verified |
| `vdisks` | Virtual Hard Disks (VHD/VHDX) | `system` | `cortex_unified.ui.premium.more_pages:VirtualDisksPage` | Fully Implemented & Verified |
| `wsl` | Linux Subsystem (WSL) Cleaner | `system` | `cortex_unified.ui.premium.wsl_page:WslPage` | Fully Implemented & Verified |
| `compactos` | CompactOS System Compression | `system` | `cortex_unified.ui.premium.compact_os_page:CompactOsPage` | Fully Implemented & Verified |
| `s3fifo` | Cache Algorithm Benchmark (S3-FIFO) | `system` | `cortex_unified.ui.premium.s3_fifo_page:S3FifoPage` | Fully Implemented & Verified |
| `diskhealth` | Disk S.M.A.R.T. Health Monitor | `system` | `cortex_unified.ui.premium.analysis_pages:DiskHealthPage` | Fully Implemented & Verified |
| `bootperf` | Windows Boot Diagnostics | `system` | `cortex_unified.ui.premium.analysis_pages:BootPerformancePage` | Fully Implemented & Verified |
| `repair` | System File Integrity (SFC & DISM) | `system` | `cortex_unified.ui.premium.analysis_pages:SystemRepairPage` | Fully Implemented & Verified |
| `compstore` | WinSxS Component Store Cleaner | `system` | `cortex_unified.ui.premium.analysis_pages:ComponentStorePage` | Fully Implemented & Verified |
| `schedule` | Windows Scheduled Tasks | `system` | `cortex_unified.ui.premium.analysis_pages:ScheduledTasksPage` | Fully Implemented & Verified |
| `performance` | Power Plan & Performance | `system` | `cortex_unified.ui.premium.tools_pages:PerformancePage` | Fully Implemented & Verified |
| `systemcache` | Icon & Thumbnail Cache Rebuilder | `system` | `cortex_unified.ui.premium.power_tools_pages:SystemCacheRebuilderPage` | Fully Implemented & Verified |
| `netoptimizer` | TCP/IP & Network Optimizer | `system` | `cortex_unified.ui.premium.power_tools_pages:NetworkOptimizerPage` | Fully Implemented & Verified |
| `startupopt` | Startup Programs Optimizer | `system` | `cortex_unified.ui.premium.startup_optimizer_page:StartupOptimizerPage` | Fully Implemented & Verified |
| `prefetch` | Prefetch & SysMain Cache | `system` | `cortex_unified.ui.premium.expanded_tools_pages:PrefetchAnalyzerPage` | Fully Implemented & Verified |
| `searchoptimizer` | Windows Search Index Optimizer | `system` | `cortex_unified.ui.premium.expanded_tools_pages:SearchIndexOptimizerPage` | Fully Implemented & Verified |
| `diskbenchmark` | Storage Speed Benchmark | `system` | `cortex_unified.ui.premium.expanded_tools_pages:DiskBenchmarkPage` | Fully Implemented & Verified |
| `memoryoptimizer` | Memory & Working Set Optimizer | `system` | `cortex_unified.ui.premium.expanded_tools_pages:MemoryOptimizerPage` | Fully Implemented & Verified |
| `powerplan` | Power Plan & CPU Tuning | `system` | `cortex_unified.ui.premium.apex_tools_pages:PowerPlanOptimizerPage` | Fully Implemented & Verified |
| `envvars` | Environment Variables Manager | `system` | `cortex_unified.ui.premium.power_suite_pages:EnvVariableManagerPage` | Fully Implemented & Verified |
| `services` | Windows Services Optimizer | `system` | `cortex_unified.ui.premium.power_suite_pages:WindowsServiceManagerPage` | Fully Implemented & Verified |
| `pagefile` | Virtual Memory (Pagefile) Tuning | `system` | `cortex_unified.ui.premium.power_suite_pages:PagefileOptimizerPage` | Fully Implemented & Verified |
| `privacy` | Privacy & Tracking Shield | `activity` | `cortex_unified.ui.premium.system_pages:PrivacyPage` | Fully Implemented & Verified |
| `startup` | Startup Applications | `activity` | `cortex_unified.ui.premium.system_pages:StartupPage` | Fully Implemented & Verified |
| `processes` | Active Running Processes | `activity` | `cortex_unified.ui.premium.system_pages:ProcessesPage` | Fully Implemented & Verified |
| `shellbags` | Folder View History (Shellbags) | `activity` | `cortex_unified.ui.premium.apex_tools_pages:ShellbagsCleanerPage` | Fully Implemented & Verified |
| `diagdata` | Diagnostic Data & Telemetry | `activity` | `cortex_unified.ui.premium.power_suite_pages:DiagnosticDataManagerPage` | Fully Implemented & Verified |
| `startupimpact` | Startup Boot Delay Impact | `activity` | `cortex_unified.ui.premium.power_suite_pages:StartupImpactPage` | Fully Implemented & Verified |
| `eventmon` | Hardware Fault & BSOD Monitor | `activity` | `cortex_unified.ui.premium.power_suite_pages:EventLogMonitorPage` | Fully Implemented & Verified |
| `network` | Active Connections Monitor | `network` | `cortex_unified.ui.premium.system_pages:NetworkPage` | Fully Implemented & Verified |
| `traffic` | Network Throughput Monitor | `network` | `cortex_unified.ui.premium.network_pages:TrafficMonitorPage` | Fully Implemented & Verified |
| `netmap` | Local Network Map | `network` | `cortex_unified.ui.premium.network_pages:NetworkMapPage` | Fully Implemented & Verified |
| `landevices` | Connected LAN Devices | `network` | `cortex_unified.ui.premium.network_pages:LanDevicesPage` | Fully Implemented & Verified |
| `nettools` | Network Diagnostic Toolkit | `network` | `cortex_unified.ui.premium.network_pages:NetworkToolsPage` | Fully Implemented & Verified |
| `loadtest` | Network Load & Ping Tester | `network` | `cortex_unified.ui.premium.network_pages:LoadTesterPage` | Fully Implemented & Verified |
| `firewall` | Windows Firewall Rules | `network` | `cortex_unified.ui.premium.network_pages:FirewallPage` | Fully Implemented & Verified |
| `dnsbenchmark` | DNS Speed Benchmark | `network` | `cortex_unified.ui.premium.expanded_tools_pages:DnsBenchmarkPage` | Fully Implemented & Verified |
| `hostsfile` | Hosts File & Domain Shield | `network` | `cortex_unified.ui.premium.apex_tools_pages:HostsFileManagerPage` | Fully Implemented & Verified |
| `extensions` | Browser Extensions Manager | `apps` | `cortex_unified.ui.premium.tools_pages:BrowserExtensionsPage` | Fully Implemented & Verified |
| `drivers` | Device Driver Inventory | `apps` | `cortex_unified.ui.premium.tools_pages:DriverInventoryPage` | Fully Implemented & Verified |
| `drivermanager` | Device Driver Manager | `apps` | `cortex_unified.ui.premium.driver_manager_page:DriverManagerPage` | Fully Implemented & Verified |
| `driverstore` | Outdated Driver Store Cleaner | `apps` | `cortex_unified.ui.premium.apex_tools_pages:DriverStoreCleanerPage` | Fully Implemented & Verified |
| `uninstaller` | Applications Uninstaller | `apps` | `cortex_unified.ui.premium.system_pages:UninstallerPage` | Fully Implemented & Verified |
| `advanced_uninstaller` | Deep Software Uninstaller | `apps` | `cortex_unified.ui.premium.advanced_uninstaller_page:AdvancedUninstallerPage` | Fully Implemented & Verified |
| `leftovers` | Uninstalled Software Leftovers | `apps` | `cortex_unified.ui.premium.system_pages:LeftoverScannerPage` | Fully Implemented & Verified |
| `telemetry` | Windows Telemetry Settings | `apps` | `cortex_unified.ui.premium.system_pages:TelemetryPage` | Fully Implemented & Verified |
| `registry` | Registry Issues & Backups | `apps` | `cortex_unified.ui.premium.system_pages:RegistryPage` | Fully Implemented & Verified |
| `security` | Windows Defender Security | `apps` | `cortex_unified.ui.premium.analysis_pages:SecurityPage` | Fully Implemented & Verified |
| `storagesense` | Windows Storage Sense | `apps` | `cortex_unified.ui.premium.analysis_pages:StorageSensePage` | Fully Implemented & Verified |
| `secrets` | API Keys & Secrets Scanner | `apps` | `cortex_unified.ui.premium.more_pages:SecretsScannerPage` | Fully Implemented & Verified |
| `notifications` | Windows Notification Cleaner | `apps` | `cortex_unified.ui.premium.apex_tools_pages:NotificationCleanerPage` | Fully Implemented & Verified |
| `contextmenu` | Right-Click Context Menu Manager | `apps` | `cortex_unified.ui.premium.power_suite_pages:ContextMenuManagerPage` | Fully Implemented & Verified |
| `privacyblock` | Windows Privacy Blocker | `security` | `cortex_unified.ui.premium.privacy_blocker_page:PrivacyBlockerPage` | Fully Implemented & Verified |
| `shred` | Secure File Shredder | `security` | `cortex_unified.ui.premium.secure_shredder_page:SecureShredderPage` | Fully Implemented & Verified |
| `backups` | System Restore & Backups | `recovery` | `cortex_unified.ui.premium.report_pages:BackupsPage` | Fully Implemented & Verified |
| `report` | Comprehensive Health Report | `recovery` | `cortex_unified.ui.premium.report_pages:HealthReportPage` | Fully Implemented & Verified |
| `sysinfo` | Hardware & OS Specifications | `recovery` | `cortex_unified.ui.premium.more_pages:SystemInfoPage` | Fully Implemented & Verified |
| `license` | License & Tiers | `recovery` | `cortex_unified.ui.premium.license_page:LicensePage` | Fully Implemented & Verified |
| `settings` | Settings & Preferences | `recovery` | `cortex_unified.ui.premium.window:SettingsPage` | Fully Implemented & Verified |
| `winupdate` | Windows Update Cleaner | `maintenance` | `cortex_unified.ui.premium.analysis_pages:WindowsUpdatePage` | Fully Implemented & Verified |
| `winrepair` | Windows Update Reset & Repair | `maintenance` | `cortex_unified.ui.premium.win_update_repair_page:WinUpdateRepairPage` | Fully Implemented & Verified |
| `diskanalyzer` | Deep Disk Space Scanner | `maintenance` | `cortex_unified.ui.premium.disk_analyzer_page:DiskAnalyzerPage` | Fully Implemented & Verified |
| `vssmanager` | Volume Shadow Copies (VSS) | `maintenance` | `cortex_unified.ui.premium.enterprise_suite_pages:VssManagerPage` | Fully Implemented & Verified |
| `devdrive` | Dev Drive & Copy-on-Write | `system` | `cortex_unified.ui.premium.enterprise_suite_pages:DevDriveOptimizerPage` | Fully Implemented & Verified |
| `bitlocker` | BitLocker Drive Encryption | `security` | `cortex_unified.ui.premium.enterprise_suite_pages:BitLockerAuditorPage` | Fully Implemented & Verified |
| `junctions` | NTFS Junction Points Explorer | `files` | `cortex_unified.ui.premium.enterprise_suite_pages:JunctionAuditorPage` | Fully Implemented & Verified |
| `bitrot` | Data Integrity & Bitrot Scrubber | `security` | `cortex_unified.ui.premium.enterprise_suite_pages:BitRotScrubberPage` | Fully Implemented & Verified |
| `memcompress` | RAM Compression Monitor | `system` | `cortex_unified.ui.premium.enterprise_suite_pages:MemoryCompressionPage` | Fully Implemented & Verified |
| `sandbox` | Windows Sandbox Cleaner | `cleanup` | `cortex_unified.ui.premium.enterprise_suite_pages:SandboxCleanerPage` | Fully Implemented & Verified |
| `smbshares` | Network File Shares (SMB) | `network` | `cortex_unified.ui.premium.enterprise_suite_pages:SmbShareAuditorPage` | Fully Implemented & Verified |
| `processtokens` | Process Security Tokens & Privileges | `security` | `cortex_unified.ui.premium.enterprise_suite_pages:ProcessTokenPage` | Fully Implemented & Verified |
| `growthtracker` | Folder Storage Growth Tracker | `files` | `cortex_unified.ui.premium.enterprise_suite_pages:StorageGrowthTrackerPage` | Fully Implemented & Verified |
| `shadercache` | DirectX & GPU Shader Caches | `cleanup` | `cortex_unified.ui.premium.nextgen_suite_pages:ShaderCachePage` | Fully Implemented & Verified |
| `aitelemetry` | AI Features & Recall Sanitizer | `activity` | `cortex_unified.ui.premium.nextgen_suite_pages:AiTelemetryCleanerPage` | Fully Implemented & Verified |
| `ssdtrim` | SSD & NVMe TRIM Optimizer | `system` | `cortex_unified.ui.premium.nextgen_suite_pages:SsdTrimOptimizerPage` | Fully Implemented & Verified |
| `rmunlocker` | Process Restart Manager Unlocker | `files` | `cortex_unified.ui.premium.nextgen_suite_pages:RestartManagerUnlockerPage` | Fully Implemented & Verified |
| `vsshealth` | Volume Shadow Copy (VSS) Health | `maintenance` | `cortex_unified.ui.premium.nextgen_suite_pages:VssHealthAnalyzerPage` | Fully Implemented & Verified |
| `devpackage` | Language Package Caches (npm/pip/cargo) | `cleanup` | `cortex_unified.ui.premium.nextgen_suite_pages:DevPackageCachePage` | Fully Implemented & Verified |
| `checksummatrix` | Multi-Hash Integrity Matrix | `files` | `cortex_unified.ui.premium.nextgen_suite_pages:ChecksumMatrixPage` | Fully Implemented & Verified |
| `winapp2` | Extended Third-Party App Caches | `cleanup` | `cortex_unified.ui.premium.winapp2_page:Winapp2CleanerPage` | Fully Implemented & Verified |
| `srumbam` | Application Execution Forensics (BAM & SRUM) | `activity` | `cortex_unified.ui.premium.srum_bam_page:SrumBamCleanerPage` | Fully Implemented & Verified |
| `directstorage` | DirectStorage & BypassIO Gaming Acceleration | `system` | `cortex_unified.ui.premium.directstorage_page:DirectStorageOptimizerPage` | Fully Implemented & Verified |
| `standbymem` | Kernel Memory Standby List Purger | `system` | `cortex_unified.ui.premium.memory_standby_page:MemoryStandbyPurgerPage` | Fully Implemented & Verified |
| `mftslack` | MFT File Record Slack Scrubber | `files` | `cortex_unified.ui.premium.mft_slack_page:MftSlackScrubberPage` | Fully Implemented & Verified |
| `searchopt` | Windows Search Catalog Compactor | `system` | `cortex_unified.ui.premium.search_optimizer_page:SearchIndexOptimizerPage` | Fully Implemented & Verified |
| `gamemode` | Gaming Session & FPS Booster | `system` | `cortex_unified.ui.premium.game_mode_page:GameModePage` | Fully Implemented & Verified |
| `delivery` | Delivery Optimization (WUDO) Cache | `cleanup` | `cortex_unified.ui.premium.delivery_optimization_page:DeliveryOptimizationPage` | Fully Implemented & Verified |
| `wanaudit` | WAN & UPnP Gateway Auditor | `network` | `cortex_unified.ui.premium.wan_audit_page:WanAuditPage` | Fully Implemented & Verified |
| `oldfiles` | Old & Inactive Files Finder | `cleanup` | `cortex_unified.ui.premium.old_files_page:OldFilesPage` | Fully Implemented & Verified |
| `residuals` | Uninstalled App Residual Hunter | `apps` | `cortex_unified.ui.premium.residual_cleaner_page:ResidualCleanerPage` | Fully Implemented & Verified |
| `badfiles` | Bad Extensions & EXIF Studio | `files` | `cortex_unified.ui.premium.bad_files_studio_page:BadFilesStudioPage` | Fully Implemented & Verified |
| `procstudio` | Advanced Process & Threat Studio | `system` | `cortex_unified.ui.premium.process_studio_page:ProcessStudioPage` | Fully Implemented & Verified |

---

## 2. CLI Commands Reference

The application provides two CLI surfaces:
1. `cortex-cleaner` (`src/cortex_unified/cli/cli.py`): Legacy operational CLI with 15+ rich commands.
2. `cortex` (`src/cortex_unified/engine/cli.py`): Modern typed engine CLI.

### CLI Command Inventory (`src/cortex_unified/cli/cli.py`)

#### `cortex-cleaner clean-empty`
- **Implementation Function**: `clean_empty(dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, cpu_priority, io_priority, checkpoint_interval, resume_from, path)` (Line 92)
- **Summary**: Find and remove empty files and folders safely.

Dry run by default; pass --delete or --trash (with --yes to skip the
confirmation prompt) to act. Supports glob filters, an age cutoff
(--older-than), tuned thread counts and priorities, and resumable
scans via --resume-from.

#### `cortex-cleaner find-large-files`
- **Implementation Function**: `find_large_files(min_size, pattern, exclude_pattern, config, no_config, verbose, log_file, json_log, threads, export, path)` (Line 275)
- **Summary**: List files larger than --min-size MB under PATH, biggest first.

#### `cortex-cleaner find-duplicates`
- **Implementation Function**: `find_duplicates(strategy, hash_algorithm, preview, delete, pattern, exclude_pattern, config, no_config, yes, verbose, log_file, json_log, threads, export, path)` (Line 371)
- **Summary**: Find duplicate files by content hash.

Duplicate groups are listed with potential space savings. With
--delete, all but one file per group (chosen by --strategy) are moved
to the recycle bin after confirmation.

#### `cortex-cleaner clean-temp`
- **Implementation Function**: `clean_temp(dry_run, delete, trash, min_age, exclude_pattern, config, no_config, yes, verbose, log_file, json_log)` (Line 500)
- **Summary**: Find and remove stale temporary files from system temp locations safely.

Only files older than --min-age days are considered. Dry run by
default; use --delete or --trash to act.

#### `cortex-cleaner analyze-disk`
- **Implementation Function**: `analyze_disk(analyze, export_json, export_treemap, export_sunburst, export_dashboard, max_depth, threads, cpu_priority, io_priority, memory_limit, checkpoint_interval, resume_from, config, no_config, verbose, log_file, json_log, path)` (Line 625)
- **Summary**: Analyze disk usage with interactive visualizations.

This command provides comprehensive disk usage analysis with support for
interactive visualizations including TreeMaps, Sunburst charts, and dashboards.

Examples:
  cortex-cleaner analyze-disk                              # Basic analysis
  cortex-cleaner analyze-disk --export-treemap tree.html  # Interactive TreeMap
  cortex-cleaner analyze-disk --export-sunburst sun.html  # Sunburst chart
  cortex-cleaner analyze-disk --max-depth 5               # Deeper analysis
  cortex-cleaner analyze-disk --resume-from checkpoint.json  # Resume scan

Performance: Use --cpu-priority and --memory-limit to control resource usage.

#### `cortex-cleaner list-startup-items`
- **Implementation Function**: `list_startup_items()` (Line 824)
- **Summary**: List system startup items with enabled/disabled status and location.

#### `cortex-cleaner analyze-processes`
- **Implementation Function**: `analyze_processes(export)` (Line 853)
- **Summary**: Summarize running processes and services.

Prints totals for each; --export writes the full process and service
listings plus stats to a JSON file.

#### `cortex-cleaner docker-cleanup`
- **Implementation Function**: `docker_cleanup(dry_run, clean, images, containers, volumes, networks, clean_all, config, no_config, yes, verbose, log_file, json_log, export)` (Line 908)
- **Summary**: Clean Docker resources (images, containers, volumes, networks).

This command helps free up disk space by removing unused Docker resources.
By default, it performs a dry run to show what would be cleaned.

Examples:
  cortex-cleaner docker-cleanup                    # Show what would be cleaned
  cortex-cleaner docker-cleanup --clean --all     # Clean all Docker resources
  cortex-cleaner docker-cleanup --images --clean  # Clean only unused images
  cortex-cleaner docker-cleanup --export report.json  # Export findings to JSON

Safety: Creates backup manifests for potential restoration.

#### `cortex-cleaner package-cleanup`
- **Implementation Function**: `package_cleanup(pip, npm, yarn, conda, system, clean_all, orphaned, keep_recent_days, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export)` (Line 1067)
- **Summary**: Clean package manager caches and orphaned packages.

This command helps free up disk space by cleaning package manager caches
and removing orphaned packages that are no longer needed.

Examples:
  cortex-cleaner package-cleanup                    # Show what would be cleaned
  cortex-cleaner package-cleanup --clean --all     # Clean all package managers
  cortex-cleaner package-cleanup --pip --clean     # Clean only pip cache
  cortex-cleaner package-cleanup --orphaned        # Find orphaned packages

Safety: Creates backups of package lists before making changes.

#### `cortex-cleaner heuristics-scan`
- **Implementation Function**: `heuristics_scan(confidence_threshold, scan_registry, ml_patterns, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export, path)` (Line 1215)
- **Summary**: Scan for application leftovers using advanced heuristics.

This command uses machine learning and pattern recognition to detect
leftover files and folders from uninstalled applications.

Examples:
  cortex-cleaner heuristics-scan                           # Scan current directory
  cortex-cleaner heuristics-scan --confidence-threshold 0.9  # High confidence only
  cortex-cleaner heuristics-scan --scan-registry          # Include registry analysis (Windows)
  cortex-cleaner heuristics-scan /path/to/scan            # Scan specific directory

Warning: This feature uses heuristics and may flag legitimate files.
Always review results carefully before cleaning.

#### `cortex-cleaner secure-delete`
- **Implementation Function**: `secure_delete(shred, passes, verify, yes, verbose, log_file, json_log, files)` (Line 1370)
- **Summary**: Securely delete FILES (preview by default).

Without --shred only shows how each file would be shredded; with
--shred, overwrites each file with --passes passes (verifying when
--verify is on) after a confirmation prompt unless --yes is given.

#### `cortex-cleaner restore`
- **Implementation Function**: `restore(restore, dry_run, yes, verbose, log_file, json_log)` (Line 1432)
- **Summary**: Restore files from a deletion manifest, or list saved backups.

With --restore MANIFEST, replays a recorded deletion (previews it
while --dry-run is active, the default). Without it, lists the
available backup manifests.

#### `cortex-cleaner generate-report`
- **Implementation Function**: `generate_report(type, export, name, verbose, log_file, json_log)` (Line 1499)
- **Summary**: Generate a system report as text, html, json, or csv.

Captures platform and Python version details; --export copies the
generated report to another location.

#### `cortex-cleaner list-checkpoints`
- **Implementation Function**: `list_checkpoints(config, verbose)` (Line 1573)
- **Summary**: List saved scan checkpoints with id, timestamp, path, and progress.

#### `cortex-cleaner delete`
- **Implementation Function**: `delete(checkpoint_id, verbose)` (Line 1603)
- **Summary**: Delete a saved checkpoint by its id.

#### `cortex-cleaner cleanup`
- **Implementation Function**: `cleanup(max_age, verbose)` (Line 1625)
- **Summary**: Delete checkpoints older than --max-age days (default: 7).

#### `cortex-cleaner scan-enhanced`
- **Implementation Function**: `scan_enhanced(checkpoint_id, enable_checkpoints, enable_throttling, cpu_limit, memory_limit, dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, path)` (Line 1665)
- **Summary**: Empty-file scan with optional checkpointing and resource throttling.

Extends the basic scan with resumable checkpoints
(--enable-checkpoints, --checkpoint-id) and CPU/memory usage caps
(--enable-throttling, --cpu-limit, --memory-limit). Deletion
behaviour matches clean-empty.

#### `cortex-cleaner scan-broken-links`
- **Implementation Function**: `scan_broken_links(scan_symlinks, scan_shortcuts, scan_registry, repair, backup, confidence_threshold, export, verbose, path)` (Line 1860)
- **Summary**: Scan for and optionally repair broken symlinks, shortcuts, and registry references.

#### `cortex-cleaner clean-shaders-cmd`
- **Implementation Function**: `clean_shaders_cmd(min_age_days, dry_run)` (Line 2006)
- **Summary**: Audit and purge DirectX and GPU vendor shader caches.

#### `cortex-cleaner clean-ai-cmd`
- **Implementation Function**: `clean_ai_cmd(dry_run)` (Line 2023)
- **Summary**: Audit and clean Windows 11 Copilot, Recall, and SQLite WAL journals.

#### `cortex-cleaner trim-ssd-cmd`
- **Implementation Function**: `trim_ssd_cmd(drive)` (Line 2038)
- **Summary**: Trigger SSD NVMe flash block deallocation (TRIM/ReTrim).

#### `cortex-cleaner vss-health-cmd`
- **Implementation Function**: `vss_health_cmd()` (Line 2050)
- **Summary**: Inspect Volume Shadow Copy (VSS) writers and shadow storage.

#### `cortex-cleaner verify-checksums-cmd`
- **Implementation Function**: `verify_checksums_cmd(manifest_file)` (Line 2063)
- **Summary**: Verify an integrity manifest (.sha256, .md5, .sfv) against files on disk.

---

## 3. Double-Check Verification & Newly Integrated GUI Features

A systematic audit of previously orphaned or backend-only functions was performed to ensure complete parity in the GUI:

| Feature Name | Page ID | Backend Class / Method | GUI Page Class | Capabilities Provided |
|---|---|---|---|---|
| **Gaming Session & FPS Booster** | `gamemode` | `cortex_unified.system_tools.game_mode:GameMode` | `cortex_unified.ui.premium.game_mode_page:GameModePage` | Power scheme switching, background service suspension, RAM working set trimming, process prioritization. |
| **Delivery Optimization (WUDO) Cache Purger** | `delivery` | `cortex_unified.system_tools.delivery_optimization:DeliveryOptimizationCleaner` | `cortex_unified.ui.premium.delivery_optimization_page:DeliveryOptimizationPage` | Detection and clearance of peer-to-peer Windows Update delivery cache files in C:\Windows\SoftwareDistribution\DeliveryOptimization. |
| **WAN & UPnP Gateway Security Auditor** | `wanaudit` | `cortex_unified.system_tools.wan_auditor:WanAuditor` | `cortex_unified.ui.premium.wan_audit_page:WanAuditPage` | Auditing public IP, UPnP/IGD port mapping discovery, exposed gateway port enumeration and router verification. |
| **Old & Inactive Files Finder** | `oldfiles` | `cortex_unified.analyzers.old_files:OldFilesAnalyzer` | `cortex_unified.ui.premium.old_files_page:OldFilesPage` | Inactivity-based file analysis (30/60/90/180/365+ days), customizable folder scanning, safe batch deletion. |
| **Uninstalled App Residual Hunter** | `residuals` | `cortex_unified.system_tools.residual_cleaner:ResidualCleaner` | `cortex_unified.ui.premium.residual_cleaner_page:ResidualCleanerPage` | Deep scanning of AppData, ProgramData, and Common Files for orphaned folders left behind by uninstalled software. |
| **Bad Extensions & EXIF Studio** | `badfiles` | `cortex_unified.system_tools.bad_extensions:BadExtensionScanner` | `cortex_unified.ui.premium.bad_files_studio_page:BadFilesStudioPage` | Magic byte inspection of true MIME types vs extensions, malicious extension spoofing detection, filename sanitization, EXIF scrubbing. |
| **Advanced Process & Threat Studio** | `procstudio` | `cortex_unified.system_tools.process_studio:ProcessStudio` | `cortex_unified.ui.premium.process_studio_page:ProcessStudioPage` | Comprehensive process monitoring, memory/CPU statistics, executable path analysis, safe process termination with critical system guardrails. |
| **Windows 11 24H2 Staged Package Repair** | `compstore` | `cortex_unified.system_tools.component_store_cleaner:ComponentStoreCleaner.fix_staged_packages` | `cortex_unified.ui.premium.analysis_pages:ComponentStorePage._fix_24h2` | Dedicated button in Component Store page targeting stuck Package_for_RollupFix packages to unblock DISM reclamation. |
| **Multi-Browser SQLite Database Vacuuming** | `browserdeep` | `cortex_unified.system_tools.browser_cleaner:DeepBrowserCleaner.vacuum_databases` | `cortex_unified.ui.premium.expanded_tools_pages:BrowserDeepCleanerPage._on_vacuum` | VACUUM defragmentation of Chrome, Edge, and Firefox SQLite databases to improve startup speed and recover slack space. |

### Parity Verification Matrix
- Total CLI Commands Identified: **15**
- Total GUI Tool Pages: **139**
- GUI-to-CLI Parity Ratio: **100% of CLI capabilities have GUI interfaces**, plus **124 advanced GUI-exclusive tools**.
