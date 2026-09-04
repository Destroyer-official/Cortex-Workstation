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
| `dashboard` | **System Overview Dashboard** | `dashboard.svg` | [`DashboardPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/window.py) | Forensic execution via `DashboardPage` |
| `health` | **PC Health Check** | `health.svg` | [`HealthCheckPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `HealthCheckPage` |

## Cleanup & Storage (`cleanup`)
*Contains 32 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `cleanuphub` | **One-Click Cleanup Hub** | `cleanuphub.svg` | [`CleanupHubPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/cleanup_hub_page.py) | Forensic execution via `CleanupHubPage` |
| `duplicates` | **Duplicate Files Finder** | `duplicates.svg` | [`DuplicatesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/window.py) | Forensic execution via `DuplicatesPage` |
| `photos` | **Similar & Duplicate Photos** | `photos.svg` | [`DuplicatePhotosPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/window.py) | Forensic execution via `DuplicatePhotosPage` |
| `dupfolders` | **Duplicate Folders Finder** | `dupfolders.svg` | [`DuplicateFoldersPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `DuplicateFoldersPage` |
| `large` | **Large Files Finder** | `large.svg` | [`LargeFilesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/window.py) | Forensic execution via `LargeFilesPage` |
| `empty` | **Empty Files & Folders** | `empty.svg` | [`EmptyPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/window.py) | Forensic execution via `EmptyPage` |
| `analyzer` | **Visual Disk Space Map** | `analyzer.svg` | [`DiskAnalyzerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `DiskAnalyzerPage` |
| `brokenlinks` | **Broken Shortcuts & Links** | `brokenlinks.svg` | [`BrokenLinksPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `BrokenLinksPage` |
| `logsweep` | **System & App Log Sweeper** | `logsweep.svg` | [`LogSweeperPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/log_sweeper_page.py) | Forensic execution via `LogSweeperPage` |
| `packages` | **Developer Package Caches** | `packages.svg` | [`PackageCachePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `PackageCachePage` |
| `projcaches` | **Project Build Caches** | `projcaches.svg` | [`ProjectCachesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `ProjectCachesPage` |
| `modelcache` | **AI Model Cache Cleaner** | `modelcache.svg` | [`ModelCachePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/model_cache_page.py) | Forensic execution via `ModelCachePage` |
| `neardup` | **Similar Text Documents** | `neardup.svg` | [`NearDuplicatesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/near_duplicates_page.py) | Forensic execution via `NearDuplicatesPage` |
| `perceptual` | **Similar Photo Matching** | `perceptual.svg` | [`PerceptualDuplicatesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/perceptual_duplicates_page.py) | Forensic execution via `PerceptualDuplicatesPage` |
| `registryai` | **Intelligent Registry Cleaner** | `registry_ai.svg` | [`RegistryAICleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/registry_ai_page.py) | Forensic execution via `RegistryAICleanerPage` |
| `fuzzyhash` | **Fuzzy Duplicate Finder** | `fuzzyhash.svg` | [`FuzzyHashPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/fuzzy_hash_page.py) | Forensic execution via `FuzzyHashPage` |
| `audio` | **Duplicate Music & Audio** | `audio.svg` | [`AudioDuplicatesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/audio_duplicates_page.py) | Forensic execution via `AudioDuplicatesPage` |
| `video` | **Duplicate Video Files** | `video.svg` | [`VideoDuplicatesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/video_duplicates_page.py) | Forensic execution via `VideoDuplicatesPage` |
| `cdc` | **Block-Level Deduplicator** | `cdc.svg` | [`CdcPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/cdc_page.py) | Forensic execution via `CdcPage` |
| `cloud` | **Cloud Storage Cache Cleaner** | `cloud_storage.svg` | [`CloudStoragePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/cloud_storage_page.py) | Forensic execution via `CloudStoragePage` |
| `portable` | **Portable Applications Manager** | `portable_manager.svg` | [`PortableManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/portable_manager_page.py) | Forensic execution via `PortableManagerPage` |
| `crashdumps` | **Crash Dumps & Error Reports** | `folder-dump.svg` | [`CrashDumpCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `CrashDumpCleanerPage` |
| `eventlogs` | **Windows Event Log Cleaner** | `log.svg` | [`EventLogCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `EventLogCleanerPage` |
| `devcleaner` | **Software Development Artifacts** | `folder-code.svg` | [`DevCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `DevCleanerPage` |
| `browserdeep` | **Deep Web Browser Cleaner** | `folder-shared.svg` | [`BrowserDeepCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `BrowserDeepCleanerPage` |
| `imgopt` | **Image Compressor & Optimizer** | `folder-images.svg` | [`ImageOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `ImageOptimizerPage` |
| `fonts` | **Font Cache & Registry Optimizer** | `font.svg` | [`FontCacheManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `FontCacheManagerPage` |
| `tempcleaner` | **Deep System Temp Cleaner** | `folder-trash.svg` | [`TempFolderCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `TempFolderCleanerPage` |
| `sandbox` | **Windows Sandbox Cleaner** | `sandbox.svg` | [`SandboxCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `SandboxCleanerPage` |
| `shadercache` | **DirectX & GPU Shader Caches** | `shadercache.svg` | [`ShaderCachePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `ShaderCachePage` |
| `devpackage` | **Language Package Caches (npm/pip/cargo)** | `devpackage.svg` | [`DevPackageCachePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `DevPackageCachePage` |
| `winapp2` | **Extended Third-Party App Caches** | `winapp2.svg` | [`Winapp2CleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/winapp2_page.py) | Forensic execution via `Winapp2CleanerPage` |

## Files & Explorer (`files`)
*Contains 21 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `nexus` | **Nexus File Explorer** | `folder.svg` | [`NexusExplorerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nexus_page.py) | Forensic execution via `NexusExplorerPage` |
| `hasher` | **File Hash & Checksum Verifier** | `verified.svg` | [`HashVerifierPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `HashVerifierPage` |
| `renamer` | **Batch File Renamer** | `label.svg` | [`BatchRenamerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `BatchRenamerPage` |
| `foldersync` | **Folder Compare & Sync** | `diff.svg` | [`FolderSyncPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `FolderSyncPage` |
| `splitter` | **Large File Splitter & Joiner** | `binary.svg` | [`FileSplitterPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `FileSplitterPage` |
| `unlocker` | **Locked File Unlocker** | `lock.svg` | [`FileUnlockerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `FileUnlockerPage` |
| `adsmanager` | **NTFS Alternate Data Streams (ADS)** | `document.svg` | [`AdsManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `AdsManagerPage` |
| `linksmanager` | **Symbolic Links & Junctions** | `folder-link.svg` | [`LinksManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `LinksManagerPage` |
| `fastcopier` | **High-Speed File Copier** | `rocket.svg` | [`FastCopierPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `FastCopierPage` |
| `timestamptouch` | **File Date & Timestamp Editor** | `folder-constant.svg` | [`TimestampTouchPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `TimestampTouchPage` |
| `archivemanager` | **Archive Studio (Zip/7z/Tar)** | `zip.svg` | [`ArchiveManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `ArchiveManagerPage` |
| `sniffer` | **File Type & Header Inspector** | `folder-syntax.svg` | [`FileSignatureSnifferPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `FileSignatureSnifferPage` |
| `binarydiff` | **Binary & Hex File Compare** | `folder-delta.svg` | [`BinaryDifferPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `BinaryDifferPage` |
| `usnjournal` | **NTFS Change Journal (USN) Viewer** | `folder-log.svg` | [`UsnJournalPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `UsnJournalPage` |
| `par2` | **PAR2 Archive Parity & Repair** | `certificate.svg` | [`Par2RecoveryPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `Par2RecoveryPage` |
| `slackspace` | **NTFS Cluster Slack Analyzer** | `disc.svg` | [`SlackSpaceAnalyzerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `SlackSpaceAnalyzerPage` |
| `junctions` | **NTFS Junction Points Explorer** | `junctions.svg` | [`JunctionAuditorPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `JunctionAuditorPage` |
| `growthtracker` | **Folder Storage Growth Tracker** | `growth.svg` | [`StorageGrowthTrackerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `StorageGrowthTrackerPage` |
| `rmunlocker` | **Process Restart Manager Unlocker** | `rmunlocker.svg` | [`RestartManagerUnlockerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `RestartManagerUnlockerPage` |
| `checksummatrix` | **Multi-Hash Integrity Matrix** | `checksummatrix.svg` | [`ChecksumMatrixPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `ChecksumMatrixPage` |
| `mftslack` | **MFT File Record Slack Scrubber** | `mftslack.svg` | [`MftSlackScrubberPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/mft_slack_page.py) | Forensic execution via `MftSlackScrubberPage` |

## System Performance (`system`)
*Contains 29 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `updater` | **Software Updater** | `updater.svg` | [`SoftwareUpdaterPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `SoftwareUpdaterPage` |
| `drives` | **Drive Optimizer (TRIM & Defrag)** | `drives.svg` | [`DriveOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `DriveOptimizerPage` |
| `vdisks` | **Virtual Hard Disks (VHD/VHDX)** | `vdisks.svg` | [`VirtualDisksPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `VirtualDisksPage` |
| `wsl` | **Linux Subsystem (WSL) Cleaner** | `wsl.svg` | [`WslPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/wsl_page.py) | Forensic execution via `WslPage` |
| `compactos` | **CompactOS System Compression** | `compactos.svg` | [`CompactOsPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/compact_os_page.py) | Forensic execution via `CompactOsPage` |
| `s3fifo` | **Cache Algorithm Benchmark (S3-FIFO)** | `s3fifo.svg` | [`S3FifoPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/s3_fifo_page.py) | Forensic execution via `S3FifoPage` |
| `diskhealth` | **Disk S.M.A.R.T. Health Monitor** | `diskhealth.svg` | [`DiskHealthPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `DiskHealthPage` |
| `bootperf` | **Windows Boot Diagnostics** | `bootperf.svg` | [`BootPerformancePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `BootPerformancePage` |
| `repair` | **System File Integrity (SFC & DISM)** | `repair.svg` | [`SystemRepairPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `SystemRepairPage` |
| `compstore` | **WinSxS Component Store Cleaner** | `compstore.svg` | [`ComponentStorePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `ComponentStorePage` |
| `schedule` | **Windows Scheduled Tasks** | `schedule.svg` | [`ScheduledTasksPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `ScheduledTasksPage` |
| `performance` | **Power Plan & Performance** | `performance.svg` | [`PerformancePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/tools_pages.py) | Forensic execution via `PerformancePage` |
| `systemcache` | **Icon & Thumbnail Cache Rebuilder** | `tune.svg` | [`SystemCacheRebuilderPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `SystemCacheRebuilderPage` |
| `netoptimizer` | **TCP/IP & Network Optimizer** | `routing.svg` | [`NetworkOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_tools_pages.py) | Forensic execution via `NetworkOptimizerPage` |
| `startupopt` | **Startup Programs Optimizer** | `startup_optimizer.svg` | [`StartupOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/startup_optimizer_page.py) | Forensic execution via `StartupOptimizerPage` |
| `prefetch` | **Prefetch & SysMain Cache** | `pipeline.svg` | [`PrefetchAnalyzerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `PrefetchAnalyzerPage` |
| `searchoptimizer` | **Windows Search Index Optimizer** | `search.svg` | [`SearchIndexOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `SearchIndexOptimizerPage` |
| `diskbenchmark` | **Storage Speed Benchmark** | `folder-benchmark.svg` | [`DiskBenchmarkPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `DiskBenchmarkPage` |
| `memoryoptimizer` | **Memory & Working Set Optimizer** | `folder-cluster.svg` | [`MemoryOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `MemoryOptimizerPage` |
| `powerplan` | **Power Plan & CPU Tuning** | `flash.svg` | [`PowerPlanOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `PowerPlanOptimizerPage` |
| `envvars` | **Environment Variables Manager** | `terminal.svg` | [`EnvVariableManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `EnvVariableManagerPage` |
| `services` | **Windows Services Optimizer** | `folder-server.svg` | [`WindowsServiceManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `WindowsServiceManagerPage` |
| `pagefile` | **Virtual Memory (Pagefile) Tuning** | `folder-resource.svg` | [`PagefileOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `PagefileOptimizerPage` |
| `devdrive` | **Dev Drive & Copy-on-Write** | `devdrive.svg` | [`DevDriveOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `DevDriveOptimizerPage` |
| `memcompress` | **RAM Compression Monitor** | `memcompress.svg` | [`MemoryCompressionPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `MemoryCompressionPage` |
| `ssdtrim` | **SSD & NVMe TRIM Optimizer** | `ssdtrim.svg` | [`SsdTrimOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `SsdTrimOptimizerPage` |
| `directstorage` | **DirectStorage & BypassIO Gaming Acceleration** | `directstorage.svg` | [`DirectStorageOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/directstorage_page.py) | Forensic execution via `DirectStorageOptimizerPage` |
| `standbymem` | **Kernel Memory Standby List Purger** | `standbymem.svg` | [`MemoryStandbyPurgerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/memory_standby_page.py) | Forensic execution via `MemoryStandbyPurgerPage` |
| `searchopt` | **Windows Search Catalog Compactor** | `searchopt.svg` | [`SearchIndexOptimizerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/search_optimizer_page.py) | Forensic execution via `SearchIndexOptimizerPage` |

## Privacy & Activity (`activity`)
*Contains 9 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `privacy` | **Privacy & Tracking Shield** | `privacy.svg` | [`PrivacyPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `PrivacyPage` |
| `startup` | **Startup Applications** | `startup.svg` | [`StartupPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `StartupPage` |
| `processes` | **Active Running Processes** | `processes.svg` | [`ProcessesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `ProcessesPage` |
| `shellbags` | **Folder View History (Shellbags)** | `folder-secure.svg` | [`ShellbagsCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `ShellbagsCleanerPage` |
| `diagdata` | **Diagnostic Data & Telemetry** | `folder-core.svg` | [`DiagnosticDataManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `DiagnosticDataManagerPage` |
| `startupimpact` | **Startup Boot Delay Impact** | `console.svg` | [`StartupImpactPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `StartupImpactPage` |
| `eventmon` | **Hardware Fault & BSOD Monitor** | `folder-database.svg` | [`EventLogMonitorPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `EventLogMonitorPage` |
| `aitelemetry` | **AI Features & Recall Sanitizer** | `aitelemetry.svg` | [`AiTelemetryCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `AiTelemetryCleanerPage` |
| `srumbam` | **Application Execution Forensics (BAM & SRUM)** | `srumbam.svg` | [`SrumBamCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/srum_bam_page.py) | Forensic execution via `SrumBamCleanerPage` |

## Network & Defense (`network`)
*Contains 10 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `network` | **Active Connections Monitor** | `network.svg` | [`NetworkPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `NetworkPage` |
| `traffic` | **Network Throughput Monitor** | `traffic.svg` | [`TrafficMonitorPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `TrafficMonitorPage` |
| `netmap` | **Local Network Map** | `netmap.svg` | [`NetworkMapPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `NetworkMapPage` |
| `landevices` | **Connected LAN Devices** | `landevices.svg` | [`LanDevicesPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `LanDevicesPage` |
| `nettools` | **Network Diagnostic Toolkit** | `nettools.svg` | [`NetworkToolsPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `NetworkToolsPage` |
| `loadtest` | **Network Load & Ping Tester** | `loadtest.svg` | [`LoadTesterPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `LoadTesterPage` |
| `firewall` | **Windows Firewall Rules** | `firewall.svg` | [`FirewallPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/network_pages.py) | Forensic execution via `FirewallPage` |
| `dnsbenchmark` | **DNS Speed Benchmark** | `folder-connection.svg` | [`DnsBenchmarkPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/expanded_tools_pages.py) | Forensic execution via `DnsBenchmarkPage` |
| `hostsfile` | **Hosts File & Domain Shield** | `hosts.svg` | [`HostsFileManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `HostsFileManagerPage` |
| `smbshares` | **Network File Shares (SMB)** | `smbshares.svg` | [`SmbShareAuditorPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `SmbShareAuditorPage` |

## Apps & Security (`apps`)
*Contains 14 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `extensions` | **Browser Extensions Manager** | `extensions.svg` | [`BrowserExtensionsPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/tools_pages.py) | Forensic execution via `BrowserExtensionsPage` |
| `drivers` | **Device Driver Inventory** | `drivers.svg` | [`DriverInventoryPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/tools_pages.py) | Forensic execution via `DriverInventoryPage` |
| `drivermanager` | **Device Driver Manager** | `driver_manager.svg` | [`DriverManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/driver_manager_page.py) | Forensic execution via `DriverManagerPage` |
| `driverstore` | **Outdated Driver Store Cleaner** | `folder-tools.svg` | [`DriverStoreCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `DriverStoreCleanerPage` |
| `uninstaller` | **Applications Uninstaller** | `uninstaller.svg` | [`UninstallerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `UninstallerPage` |
| `advanced_uninstaller` | **Deep Software Uninstaller** | `advanced_uninstaller.svg` | [`AdvancedUninstallerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/advanced_uninstaller_page.py) | Forensic execution via `AdvancedUninstallerPage` |
| `leftovers` | **Uninstalled Software Leftovers** | `leftovers.svg` | [`LeftoverScannerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `LeftoverScannerPage` |
| `telemetry` | **Windows Telemetry Settings** | `telemetry.svg` | [`TelemetryPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `TelemetryPage` |
| `registry` | **Registry Issues & Backups** | `registry.svg` | [`RegistryPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/system_pages.py) | Forensic execution via `RegistryPage` |
| `security` | **Windows Defender Security** | `security.svg` | [`SecurityPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `SecurityPage` |
| `storagesense` | **Windows Storage Sense** | `storagesense.svg` | [`StorageSensePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `StorageSensePage` |
| `secrets` | **API Keys & Secrets Scanner** | `secrets.svg` | [`SecretsScannerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `SecretsScannerPage` |
| `notifications` | **Windows Notification Cleaner** | `folder-messages.svg` | [`NotificationCleanerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/apex_tools_pages.py) | Forensic execution via `NotificationCleanerPage` |
| `contextmenu` | **Right-Click Context Menu Manager** | `menu.svg` | [`ContextMenuManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/power_suite_pages.py) | Forensic execution via `ContextMenuManagerPage` |

## Security Tools (`security`)
*Contains 5 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `privacyblock` | **Windows Privacy Blocker** | `privacy_blocker.svg` | [`PrivacyBlockerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/privacy_blocker_page.py) | Forensic execution via `PrivacyBlockerPage` |
| `shred` | **Secure File Shredder** | `secure_shredder.svg` | [`SecureShredderPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/secure_shredder_page.py) | Forensic execution via `SecureShredderPage` |
| `bitlocker` | **BitLocker Drive Encryption** | `bitlocker.svg` | [`BitLockerAuditorPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `BitLockerAuditorPage` |
| `bitrot` | **Data Integrity & Bitrot Scrubber** | `bitrot.svg` | [`BitRotScrubberPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `BitRotScrubberPage` |
| `processtokens` | **Process Security Tokens & Privileges** | `tokens.svg` | [`ProcessTokenPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `ProcessTokenPage` |

## Recovery & Reports (`recovery`)
*Contains 5 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `backups` | **System Restore & Backups** | `backups.svg` | [`BackupsPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/report_pages.py) | Forensic execution via `BackupsPage` |
| `report` | **Comprehensive Health Report** | `report.svg` | [`HealthReportPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/report_pages.py) | Forensic execution via `HealthReportPage` |
| `sysinfo` | **Hardware & OS Specifications** | `sysinfo.svg` | [`SystemInfoPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/more_pages.py) | Forensic execution via `SystemInfoPage` |
| `license` | **License & Tiers** | `check.svg` | [`LicensePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/license_page.py) | Forensic execution via `LicensePage` |
| `settings` | **Settings & Preferences** | `settings.svg` | [`SettingsPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/window.py) | Forensic execution via `SettingsPage` |

## Maintenance & Repair (`maintenance`)
*Contains 5 interactive pages.*

| Page ID | Display Title | Icon Asset | Factory Target | Capabilities & Operations |
| :--- | :--- | :--- | :--- | :--- |
| `winupdate` | **Windows Update Cleaner** | `winupdate.svg` | [`WindowsUpdatePage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/analysis_pages.py) | Forensic execution via `WindowsUpdatePage` |
| `winrepair` | **Windows Update Reset & Repair** | `win_update_repair.svg` | [`WinUpdateRepairPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/win_update_repair_page.py) | Forensic execution via `WinUpdateRepairPage` |
| `diskanalyzer` | **Deep Disk Space Scanner** | `disk_analyzer.svg` | [`DiskAnalyzerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/disk_analyzer_page.py) | Forensic execution via `DiskAnalyzerPage` |
| `vssmanager` | **Volume Shadow Copies (VSS)** | `vss.svg` | [`VssManagerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/enterprise_suite_pages.py) | Forensic execution via `VssManagerPage` |
| `vsshealth` | **Volume Shadow Copy (VSS) Health** | `vsshealth.svg` | [`VssHealthAnalyzerPage`](https://github.com/Destroyer-official/Cortex-Workstation/blob/main/src/cortex_unified/ui/premium/nextgen_suite_pages.py) | Forensic execution via `VssHealthAnalyzerPage` |
