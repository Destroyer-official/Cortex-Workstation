# Cortex Workstation — Complete Feature & UI Directory

This directory documents all **132 interactive pages** across the **10 navigation groups** in Cortex Workstation.
Every page is backed by real Windows NT subsystem tools and asynchronous worker threads.

---

## Summary of Navigation Groups

| Group ID | Section Name | Page Count | Primary Scope |
| :--- | :--- | :--- | :--- |
| `overview` | **Command Center** | 2 | Overview tools and management |
| `cleanup` | **Cleanup & Storage** | 32 | Cleanup tools and management |
| `files` | **Files & Explorer** | 21 | Files tools and management |
| `system` | **System Performance** | 29 | System tools and management |
| `activity` | **Privacy & Activity** | 9 | Activity tools and management |
| `network` | **Network & Defense** | 10 | Network tools and management |
| `apps` | **Apps & Security** | 14 | Apps tools and management |
| `security` | **Security Tools** | 5 | Security tools and management |
| `recovery` | **Recovery & Reports** | 5 | Recovery tools and management |
| `maintenance` | **Maintenance & Repair** | 5 | Maintenance tools and management |

---

## Command Center (`overview`)
*Contains 2 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `dashboard` | **System Overview Dashboard** | `dashboard.svg` | [`DashboardPage`](../src/cortex_unified/ui/premium/window.py) | Forensic execution via `DashboardPage` |
| `health` | **PC Health Check** | `health.svg` | [`HealthCheckPage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `HealthCheckPage` |

## Cleanup & Storage (`cleanup`)
*Contains 32 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `cleanuphub` | **One-Click Cleanup Hub** | `cleanuphub.svg` | [`CleanupHubPage`](../src/cortex_unified/ui/premium/cleanup_hub_page.py) | Forensic execution via `CleanupHubPage` |
| `duplicates` | **Duplicate Files Finder** | `duplicates.svg` | [`DuplicatesPage`](../src/cortex_unified/ui/premium/window.py) | Forensic execution via `DuplicatesPage` |
| `photos` | **Similar & Duplicate Photos** | `photos.svg` | [`DuplicatePhotosPage`](../src/cortex_unified/ui/premium/window.py) | Forensic execution via `DuplicatePhotosPage` |
| `dupfolders` | **Duplicate Folders Finder** | `dupfolders.svg` | [`DuplicateFoldersPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `DuplicateFoldersPage` |
| `large` | **Large Files Finder** | `large.svg` | [`LargeFilesPage`](../src/cortex_unified/ui/premium/window.py) | Forensic execution via `LargeFilesPage` |
| `empty` | **Empty Files & Folders** | `empty.svg` | [`EmptyPage`](../src/cortex_unified/ui/premium/window.py) | Forensic execution via `EmptyPage` |
| `analyzer` | **Visual Disk Space Map** | `analyzer.svg` | [`DiskAnalyzerPage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `DiskAnalyzerPage` |
| `brokenlinks` | **Broken Shortcuts & Links** | `brokenlinks.svg` | [`BrokenLinksPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `BrokenLinksPage` |
| `logsweep` | **System & App Log Sweeper** | `logsweep.svg` | [`LogSweeperPage`](../src/cortex_unified/ui/premium/log_sweeper_page.py) | Forensic execution via `LogSweeperPage` |
| `packages` | **Developer Package Caches** | `packages.svg` | [`PackageCachePage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `PackageCachePage` |
| `projcaches` | **Project Build Caches** | `projcaches.svg` | [`ProjectCachesPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `ProjectCachesPage` |
| `modelcache` | **AI Model Cache Cleaner** | `modelcache.svg` | [`ModelCachePage`](../src/cortex_unified/ui/premium/model_cache_page.py) | Forensic execution via `ModelCachePage` |
| `neardup` | **Similar Text Documents** | `neardup.svg` | [`NearDuplicatesPage`](../src/cortex_unified/ui/premium/near_duplicates_page.py) | Forensic execution via `NearDuplicatesPage` |
| `perceptual` | **Similar Photo Matching** | `perceptual.svg` | [`PerceptualDuplicatesPage`](../src/cortex_unified/ui/premium/perceptual_duplicates_page.py) | Forensic execution via `PerceptualDuplicatesPage` |
| `registryai` | **Intelligent Registry Cleaner** | `registry_ai.svg` | [`RegistryAICleanerPage`](../src/cortex_unified/ui/premium/registry_ai_page.py) | Forensic execution via `RegistryAICleanerPage` |
| `fuzzyhash` | **Fuzzy Duplicate Finder** | `fuzzyhash.svg` | [`FuzzyHashPage`](../src/cortex_unified/ui/premium/fuzzy_hash_page.py) | Forensic execution via `FuzzyHashPage` |
| `audio` | **Duplicate Music & Audio** | `audio.svg` | [`AudioDuplicatesPage`](../src/cortex_unified/ui/premium/audio_duplicates_page.py) | Forensic execution via `AudioDuplicatesPage` |
| `video` | **Duplicate Video Files** | `video.svg` | [`VideoDuplicatesPage`](../src/cortex_unified/ui/premium/video_duplicates_page.py) | Forensic execution via `VideoDuplicatesPage` |
| `cdc` | **Block-Level Deduplicator** | `cdc.svg` | [`CdcPage`](../src/cortex_unified/ui/premium/cdc_page.py) | Forensic execution via `CdcPage` |
| `cloud` | **Cloud Storage Cache Cleaner** | `cloud_storage.svg` | [`CloudStoragePage`](../src/cortex_unified/ui/premium/cloud_storage_page.py) | Forensic execution via `CloudStoragePage` |
| `portable` | **Portable Applications Manager** | `portable_manager.svg` | [`PortableManagerPage`](../src/cortex_unified/ui/premium/portable_manager_page.py) | Forensic execution via `PortableManagerPage` |
| `crashdumps` | **Crash Dumps & Error Reports** | `folder-dump.svg` | [`CrashDumpCleanerPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `CrashDumpCleanerPage` |
| `eventlogs` | **Windows Event Log Cleaner** | `log.svg` | [`EventLogCleanerPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `EventLogCleanerPage` |
| `devcleaner` | **Software Development Artifacts** | `folder-code.svg` | [`DevCleanerPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `DevCleanerPage` |
| `browserdeep` | **Deep Web Browser Cleaner** | `folder-shared.svg` | [`BrowserDeepCleanerPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `BrowserDeepCleanerPage` |
| `imgopt` | **Image Compressor & Optimizer** | `folder-images.svg` | [`ImageOptimizerPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `ImageOptimizerPage` |
| `fonts` | **Font Cache & Registry Optimizer** | `font.svg` | [`FontCacheManagerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `FontCacheManagerPage` |
| `tempcleaner` | **Deep System Temp Cleaner** | `folder-trash.svg` | [`TempFolderCleanerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `TempFolderCleanerPage` |
| `sandbox` | **Windows Sandbox Cleaner** | `sandbox.svg` | [`SandboxCleanerPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `SandboxCleanerPage` |
| `shadercache` | **DirectX & GPU Shader Caches** | `shadercache.svg` | [`ShaderCachePage`](../src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `ShaderCachePage` |
| `devpackage` | **Language Package Caches (npm/pip/cargo)** | `devpackage.svg` | [`DevPackageCachePage`](../src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `DevPackageCachePage` |
| `winapp2` | **Extended Third-Party App Caches** | `winapp2.svg` | [`Winapp2CleanerPage`](../src/cortex_unified/ui/premium/winapp2_page.py) | Forensic execution via `Winapp2CleanerPage` |

## Files & Explorer (`files`)
*Contains 21 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `nexus` | **Nexus File Explorer** | `folder.svg` | [`NexusExplorerPage`](../src/cortex_unified/ui/premium/nexus_page.py) | Forensic execution via `NexusExplorerPage` |
| `hasher` | **File Hash & Checksum Verifier** | `verified.svg` | [`HashVerifierPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `HashVerifierPage` |
| `renamer` | **Batch File Renamer** | `label.svg` | [`BatchRenamerPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `BatchRenamerPage` |
| `foldersync` | **Folder Compare & Sync** | `diff.svg` | [`FolderSyncPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `FolderSyncPage` |
| `splitter` | **Large File Splitter & Joiner** | `binary.svg` | [`FileSplitterPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `FileSplitterPage` |
| `unlocker` | **Locked File Unlocker** | `lock.svg` | [`FileUnlockerPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `FileUnlockerPage` |
| `adsmanager` | **NTFS Alternate Data Streams (ADS)** | `document.svg` | [`AdsManagerPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `AdsManagerPage` |
| `linksmanager` | **Symbolic Links & Junctions** | `folder-link.svg` | [`LinksManagerPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `LinksManagerPage` |
| `fastcopier` | **High-Speed File Copier** | `rocket.svg` | [`FastCopierPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `FastCopierPage` |
| `timestamptouch` | **File Date & Timestamp Editor** | `folder-constant.svg` | [`TimestampTouchPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `TimestampTouchPage` |
| `archivemanager` | **Archive Studio (Zip/7z/Tar)** | `zip.svg` | [`ArchiveManagerPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `ArchiveManagerPage` |
| `sniffer` | **File Type & Header Inspector** | `folder-syntax.svg` | [`FileSignatureSnifferPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `FileSignatureSnifferPage` |
| `binarydiff` | **Binary & Hex File Compare** | `folder-delta.svg` | [`BinaryDifferPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `BinaryDifferPage` |
| `usnjournal` | **NTFS Change Journal (USN) Viewer** | `folder-log.svg` | [`UsnJournalPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `UsnJournalPage` |
| `par2` | **PAR2 Archive Parity & Repair** | `certificate.svg` | [`Par2RecoveryPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `Par2RecoveryPage` |
| `slackspace` | **NTFS Cluster Slack Analyzer** | `disc.svg` | [`SlackSpaceAnalyzerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `SlackSpaceAnalyzerPage` |
| `junctions` | **NTFS Junction Points Explorer** | `junctions.svg` | [`JunctionAuditorPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `JunctionAuditorPage` |
| `growthtracker` | **Folder Storage Growth Tracker** | `growth.svg` | [`StorageGrowthTrackerPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `StorageGrowthTrackerPage` |
| `rmunlocker` | **Process Restart Manager Unlocker** | `rmunlocker.svg` | [`RestartManagerUnlockerPage`](../src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `RestartManagerUnlockerPage` |
| `checksummatrix` | **Multi-Hash Integrity Matrix** | `checksummatrix.svg` | [`ChecksumMatrixPage`](../src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `ChecksumMatrixPage` |
| `mftslack` | **MFT File Record Slack Scrubber** | `mftslack.svg` | [`MftSlackScrubberPage`](../src/cortex_unified/ui/premium/mft_slack_page.py) | Forensic execution via `MftSlackScrubberPage` |

## System Performance (`system`)
*Contains 29 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `updater` | **Software Updater** | `updater.svg` | [`SoftwareUpdaterPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `SoftwareUpdaterPage` |
| `drives` | **Drive Optimizer (TRIM & Defrag)** | `drives.svg` | [`DriveOptimizerPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `DriveOptimizerPage` |
| `vdisks` | **Virtual Hard Disks (VHD/VHDX)** | `vdisks.svg` | [`VirtualDisksPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `VirtualDisksPage` |
| `wsl` | **Linux Subsystem (WSL) Cleaner** | `wsl.svg` | [`WslPage`](../src/cortex_unified/ui/premium/wsl_page.py) | Forensic execution via `WslPage` |
| `compactos` | **CompactOS System Compression** | `compactos.svg` | [`CompactOsPage`](../src/cortex_unified/ui/premium/compact_os_page.py) | Forensic execution via `CompactOsPage` |
| `s3fifo` | **Cache Algorithm Benchmark (S3-FIFO)** | `s3fifo.svg` | [`S3FifoPage`](../src/cortex_unified/ui/premium/s3_fifo_page.py) | Forensic execution via `S3FifoPage` |
| `diskhealth` | **Disk S.M.A.R.T. Health Monitor** | `diskhealth.svg` | [`DiskHealthPage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `DiskHealthPage` |
| `bootperf` | **Windows Boot Diagnostics** | `bootperf.svg` | [`BootPerformancePage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `BootPerformancePage` |
| `repair` | **System File Integrity (SFC & DISM)** | `repair.svg` | [`SystemRepairPage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `SystemRepairPage` |
| `compstore` | **WinSxS Component Store Cleaner** | `compstore.svg` | [`ComponentStorePage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `ComponentStorePage` |
| `schedule` | **Windows Scheduled Tasks** | `schedule.svg` | [`ScheduledTasksPage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `ScheduledTasksPage` |
| `performance` | **Power Plan & Performance** | `performance.svg` | [`PerformancePage`](../src/cortex_unified/ui/premium/tools_pages.py) | Forensic execution via `PerformancePage` |
| `systemcache` | **Icon & Thumbnail Cache Rebuilder** | `tune.svg` | [`SystemCacheRebuilderPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `SystemCacheRebuilderPage` |
| `netoptimizer` | **TCP/IP & Network Optimizer** | `routing.svg` | [`NetworkOptimizerPage`](../src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `NetworkOptimizerPage` |
| `startupopt` | **Startup Programs Optimizer** | `startup_optimizer.svg` | [`StartupOptimizerPage`](../src/cortex_unified/ui/premium/startup_optimizer_page.py) | Forensic execution via `StartupOptimizerPage` |
| `prefetch` | **Prefetch & SysMain Cache** | `pipeline.svg` | [`PrefetchAnalyzerPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `PrefetchAnalyzerPage` |
| `searchoptimizer` | **Windows Search Index Optimizer** | `search.svg` | [`SearchIndexOptimizerPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `SearchIndexOptimizerPage` |
| `diskbenchmark` | **Storage Speed Benchmark** | `folder-benchmark.svg` | [`DiskBenchmarkPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `DiskBenchmarkPage` |
| `memoryoptimizer` | **Memory & Working Set Optimizer** | `folder-cluster.svg` | [`MemoryOptimizerPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `MemoryOptimizerPage` |
| `powerplan` | **Power Plan & CPU Tuning** | `flash.svg` | [`PowerPlanOptimizerPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `PowerPlanOptimizerPage` |
| `envvars` | **Environment Variables Manager** | `terminal.svg` | [`EnvVariableManagerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `EnvVariableManagerPage` |
| `services` | **Windows Services Optimizer** | `folder-server.svg` | [`WindowsServiceManagerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `WindowsServiceManagerPage` |
| `pagefile` | **Virtual Memory (Pagefile) Tuning** | `folder-resource.svg` | [`PagefileOptimizerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `PagefileOptimizerPage` |
| `devdrive` | **Dev Drive & Copy-on-Write** | `devdrive.svg` | [`DevDriveOptimizerPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `DevDriveOptimizerPage` |
| `memcompress` | **RAM Compression Monitor** | `memcompress.svg` | [`MemoryCompressionPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `MemoryCompressionPage` |
| `ssdtrim` | **SSD & NVMe TRIM Optimizer** | `ssdtrim.svg` | [`SsdTrimOptimizerPage`](../src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `SsdTrimOptimizerPage` |
| `directstorage` | **DirectStorage & BypassIO Gaming Acceleration** | `directstorage.svg` | [`DirectStorageOptimizerPage`](../src/cortex_unified/ui/premium/directstorage_page.py) | Forensic execution via `DirectStorageOptimizerPage` |
| `standbymem` | **Kernel Memory Standby List Purger** | `standbymem.svg` | [`MemoryStandbyPurgerPage`](../src/cortex_unified/ui/premium/memory_standby_page.py) | Forensic execution via `MemoryStandbyPurgerPage` |
| `searchopt` | **Windows Search Catalog Compactor** | `searchopt.svg` | [`SearchIndexOptimizerPage`](../src/cortex_unified/ui/premium/search_optimizer_page.py) | Forensic execution via `SearchIndexOptimizerPage` |

## Privacy & Activity (`activity`)
*Contains 9 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `privacy` | **Privacy & Tracking Shield** | `privacy.svg` | [`PrivacyPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `PrivacyPage` |
| `startup` | **Startup Applications** | `startup.svg` | [`StartupPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `StartupPage` |
| `processes` | **Active Running Processes** | `processes.svg` | [`ProcessesPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `ProcessesPage` |
| `shellbags` | **Folder View History (Shellbags)** | `folder-secure.svg` | [`ShellbagsCleanerPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `ShellbagsCleanerPage` |
| `diagdata` | **Diagnostic Data & Telemetry** | `folder-core.svg` | [`DiagnosticDataManagerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `DiagnosticDataManagerPage` |
| `startupimpact` | **Startup Boot Delay Impact** | `console.svg` | [`StartupImpactPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `StartupImpactPage` |
| `eventmon` | **Hardware Fault & BSOD Monitor** | `folder-database.svg` | [`EventLogMonitorPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `EventLogMonitorPage` |
| `aitelemetry` | **AI Features & Recall Sanitizer** | `aitelemetry.svg` | [`AiTelemetryCleanerPage`](../src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `AiTelemetryCleanerPage` |
| `srumbam` | **Application Execution Forensics (BAM & SRUM)** | `srumbam.svg` | [`SrumBamCleanerPage`](../src/cortex_unified/ui/premium/srum_bam_page.py) | Forensic execution via `SrumBamCleanerPage` |

## Network & Defense (`network`)
*Contains 10 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `network` | **Active Connections Monitor** | `network.svg` | [`NetworkPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `NetworkPage` |
| `traffic` | **Network Throughput Monitor** | `traffic.svg` | [`TrafficMonitorPage`](../src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `TrafficMonitorPage` |
| `netmap` | **Local Network Map** | `netmap.svg` | [`NetworkMapPage`](../src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `NetworkMapPage` |
| `landevices` | **Connected LAN Devices** | `landevices.svg` | [`LanDevicesPage`](../src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `LanDevicesPage` |
| `nettools` | **Network Diagnostic Toolkit** | `nettools.svg` | [`NetworkToolsPage`](../src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `NetworkToolsPage` |
| `loadtest` | **Network Load & Ping Tester** | `loadtest.svg` | [`LoadTesterPage`](../src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `LoadTesterPage` |
| `firewall` | **Windows Firewall Rules** | `firewall.svg` | [`FirewallPage`](../src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `FirewallPage` |
| `dnsbenchmark` | **DNS Speed Benchmark** | `folder-connection.svg` | [`DnsBenchmarkPage`](../src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `DnsBenchmarkPage` |
| `hostsfile` | **Hosts File & Domain Shield** | `hosts.svg` | [`HostsFileManagerPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `HostsFileManagerPage` |
| `smbshares` | **Network File Shares (SMB)** | `smbshares.svg` | [`SmbShareAuditorPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `SmbShareAuditorPage` |

## Apps & Security (`apps`)
*Contains 14 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `extensions` | **Browser Extensions Manager** | `extensions.svg` | [`BrowserExtensionsPage`](../src/cortex_unified/ui/premium/tools_pages.py) | Forensic execution via `BrowserExtensionsPage` |
| `drivers` | **Device Driver Inventory** | `drivers.svg` | [`DriverInventoryPage`](../src/cortex_unified/ui/premium/tools_pages.py) | Forensic execution via `DriverInventoryPage` |
| `drivermanager` | **Device Driver Manager** | `driver_manager.svg` | [`DriverManagerPage`](../src/cortex_unified/ui/premium/driver_manager_page.py) | Forensic execution via `DriverManagerPage` |
| `driverstore` | **Outdated Driver Store Cleaner** | `folder-tools.svg` | [`DriverStoreCleanerPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `DriverStoreCleanerPage` |
| `uninstaller` | **Applications Uninstaller** | `uninstaller.svg` | [`UninstallerPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `UninstallerPage` |
| `advanced_uninstaller` | **Deep Software Uninstaller** | `advanced_uninstaller.svg` | [`AdvancedUninstallerPage`](../src/cortex_unified/ui/premium/advanced_uninstaller_page.py) | Forensic execution via `AdvancedUninstallerPage` |
| `leftovers` | **Uninstalled Software Leftovers** | `leftovers.svg` | [`LeftoverScannerPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `LeftoverScannerPage` |
| `telemetry` | **Windows Telemetry Settings** | `telemetry.svg` | [`TelemetryPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `TelemetryPage` |
| `registry` | **Registry Issues & Backups** | `registry.svg` | [`RegistryPage`](../src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `RegistryPage` |
| `security` | **Windows Defender Security** | `security.svg` | [`SecurityPage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `SecurityPage` |
| `storagesense` | **Windows Storage Sense** | `storagesense.svg` | [`StorageSensePage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `StorageSensePage` |
| `secrets` | **API Keys & Secrets Scanner** | `secrets.svg` | [`SecretsScannerPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `SecretsScannerPage` |
| `notifications` | **Windows Notification Cleaner** | `folder-messages.svg` | [`NotificationCleanerPage`](../src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `NotificationCleanerPage` |
| `contextmenu` | **Right-Click Context Menu Manager** | `menu.svg` | [`ContextMenuManagerPage`](../src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `ContextMenuManagerPage` |

## Security Tools (`security`)
*Contains 5 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `privacyblock` | **Windows Privacy Blocker** | `privacy_blocker.svg` | [`PrivacyBlockerPage`](../src/cortex_unified/ui/premium/privacy_blocker_page.py) | Forensic execution via `PrivacyBlockerPage` |
| `shred` | **Secure File Shredder** | `secure_shredder.svg` | [`SecureShredderPage`](../src/cortex_unified/ui/premium/secure_shredder_page.py) | Forensic execution via `SecureShredderPage` |
| `bitlocker` | **BitLocker Drive Encryption** | `bitlocker.svg` | [`BitLockerAuditorPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `BitLockerAuditorPage` |
| `bitrot` | **Data Integrity & Bitrot Scrubber** | `bitrot.svg` | [`BitRotScrubberPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `BitRotScrubberPage` |
| `processtokens` | **Process Security Tokens & Privileges** | `tokens.svg` | [`ProcessTokenPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `ProcessTokenPage` |

## Recovery & Reports (`recovery`)
*Contains 5 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `backups` | **System Restore & Backups** | `backups.svg` | [`BackupsPage`](../src/cortex_unified/ui/premium/report_pages.py) | Forensic execution via `BackupsPage` |
| `report` | **Comprehensive Health Report** | `report.svg` | [`HealthReportPage`](../src/cortex_unified/ui/premium/report_pages.py) | Forensic execution via `HealthReportPage` |
| `sysinfo` | **Hardware & OS Specifications** | `sysinfo.svg` | [`SystemInfoPage`](../src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `SystemInfoPage` |
| `license` | **License & Tiers** | `check.svg` | [`LicensePage`](../src/cortex_unified/ui/premium/license_page.py) | Forensic execution via `LicensePage` |
| `settings` | **Settings & Preferences** | `settings.svg` | [`SettingsPage`](../src/cortex_unified/ui/premium/window.py) | Forensic execution via `SettingsPage` |

## Maintenance & Repair (`maintenance`)
*Contains 5 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `winupdate` | **Windows Update Cleaner** | `winupdate.svg` | [`WindowsUpdatePage`](../src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `WindowsUpdatePage` |
| `winrepair` | **Windows Update Reset & Repair** | `win_update_repair.svg` | [`WinUpdateRepairPage`](../src/cortex_unified/ui/premium/win_update_repair_page.py) | Forensic execution via `WinUpdateRepairPage` |
| `diskanalyzer` | **Deep Disk Space Scanner** | `disk_analyzer.svg` | [`DiskAnalyzerPage`](../src/cortex_unified/ui/premium/disk_analyzer_page.py) | Forensic execution via `DiskAnalyzerPage` |
| `vssmanager` | **Volume Shadow Copies (VSS)** | `vss.svg` | [`VssManagerPage`](../src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `VssManagerPage` |
| `vsshealth` | **Volume Shadow Copy (VSS) Health** | `vsshealth.svg` | [`VssHealthAnalyzerPage`](../src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `VssHealthAnalyzerPage` |
