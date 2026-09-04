# ORPHANS_B - backend symbols never referenced by GUI code

Scope: `src/cortex_unified/analyzers/` (31 files) + `src/cortex_unified/system_tools/` (all) vs GUI dirs `src/cortex_unified/ui/`, `src/cortex_unified/explorer/`, `run_gui.py` (includes `ui/premium/` + `ui/tabs/`).
Method: top-level public `class`/`def` per backend file (AST, skips `_private` and methods); substring name-grep across full GUI corpus. Zero hits outside own file/tests = ORPHAN. Module stem nowhere in corpus = FULLY-ORPHAN module.
Statistics: 550 top-level public symbols; 287 orphans in 107 modules; 13 fully-orphan modules: czkawka_tools, residual_cleaner, residual_hunter, weaponized_shredder, browser_cleaner, component_store_cleaner, delivery_optimization_cleaner, game_mode, lan_scanner, network_scan_cli, process_meta, sieve_cache, wan_audit.
Caveat: substring grep can over-match short/generic names, so generic helpers that DO match are (correctly) not listed; listed items had literally zero GUI hits. `(helper)` marks internal utilities with no direct GUI value; `(verify)` means a GUI page exists but does not reference this symbol - confirm before wiring.
Note: `residual_hunter.py` and `weaponized_shredder.py` are shim/re-export modules with zero own public top-level symbols (docstring + imports + aliases only) and zero GUI references - whole-file orphans, no per-symbol rows. `network_scan_cli.main()` is excluded only because the generic name `main` over-matches; the module itself is never imported by GUI (CLI-only entry point).

## advanced_disk_analyzer.py
Suggest: expose via disk_analyzer_tab.py / premium disk_analyzer_page.py - expose NTFSScanner/PosixScanner/CloudScanner as scan-engine options
- `FolderNode()` (src/cortex_unified/analyzers/advanced_disk_analyzer.py:122) [class]: Aggregated folder node for visualization. - unused by GUI.
- `NTFSScanner()` (src/cortex_unified/analyzers/advanced_disk_analyzer.py:241) [class]: Fast NTFS scanner using direct MFT parsing via Windows API. - unused by GUI.
- `PosixScanner()` (src/cortex_unified/analyzers/advanced_disk_analyzer.py:314) [class]: Linux/macOS scanner using iterative scandir with stat metadata. - unused by GUI.
- `CloudScanner()` (src/cortex_unified/analyzers/advanced_disk_analyzer.py:356) [class]: Cloud target scanner delegating to rclone ``lsf`` per configured remote. - unused by GUI.

## advanced_shredder.py
Suggest: expose via file_shredder_tab.py / secure_shredder_page.py - offer ShredMethod choice in shred dialog
- `ShredMethod()` (src/cortex_unified/analyzers/advanced_shredder.py:23) [class]: Sanitization standards for secure data erasure. - unused by GUI.

## advanced_uninstaller.py
Suggest: expose via uninstaller_tab.py / advanced_uninstaller_page.py - render LeftoverScanResult rows
- `LeftoverScanResult()` (src/cortex_unified/analyzers/advanced_uninstaller.py:115) [class]: LeftoverScanResult. - unused by GUI.

## audio_duplicate_finder.py
Suggest: expose via duplicates_tab.py / audio_duplicates_page.py - wire compute_audio_fingerprint/audio_compare into audio-dup scan
- `compute_audio_fingerprint()` (src/cortex_unified/analyzers/audio_duplicate_finder.py:415) [func]: Compute Chromaprint-inspired acoustic fingerprint (sequence of 32-bit ints). - unused by GUI.
- `audio_compare()` (src/cortex_unified/analyzers/audio_duplicate_finder.py:455) [func]: Similarity 0.0..1.0 between two fingerprints (higher = more similar). - unused by GUI.

## broken_link_detector.py
Suggest: expose via broken_links_tab.py - surface result/outcome types in repair report
- `BrokenSymlink()` (src/cortex_unified/analyzers/broken_link_detector.py:29) [class]: Information about a broken symlink. - unused by GUI.
- `BrokenShortcut()` (src/cortex_unified/analyzers/broken_link_detector.py:40) [class]: Information about a broken Windows shortcut (.lnk file). - unused by GUI.
- `BrokenRegistryRef()` (src/cortex_unified/analyzers/broken_link_detector.py:53) [class]: Information about a broken registry reference (Windows only). - unused by GUI.
- `RepairResult()` (src/cortex_unified/analyzers/broken_link_detector.py:65) [class]: Result of a repair attempt. - unused by GUI.
- `RepairOutcome()` (src/cortex_unified/analyzers/broken_link_detector.py:76) [class]: Per-item outcome of a :func:`repair` run. - unused by GUI.

## cloud_storage_analyzer.py
Suggest: expose via premium cloud_storage_page.py - wire provider classes + PricingCatalog estimate card
- `PricingCatalog()` (src/cortex_unified/analyzers/cloud_storage_analyzer.py:147) [class]: Storage pricing resolved at runtime from the provider's public API. - unused by GUI.
- `CloudProvider()` (src/cortex_unified/analyzers/cloud_storage_analyzer.py:341) [class]: Abstract cloud storage provider. - unused by GUI.
- `S3Provider()` (src/cortex_unified/analyzers/cloud_storage_analyzer.py:406) [class]: AWS S3 backend driven by boto3, listing object versions when available. - unused by GUI.
- `AzureBlobProvider()` (src/cortex_unified/analyzers/cloud_storage_analyzer.py:538) [class]: Azure Blob backend via BlobServiceClient (connection string or token auth). - unused by GUI.
- `GoogleDriveProvider()` (src/cortex_unified/analyzers/cloud_storage_analyzer.py:652) [class]: Google Drive listing via the Drive v3 REST API. - unused by GUI.
- `OneDriveProvider()` (src/cortex_unified/analyzers/cloud_storage_analyzer.py:752) [class]: OneDrive / SharePoint listing via Microsoft Graph ``/children``. - unused by GUI.
- `RcloneProvider()` (src/cortex_unified/analyzers/cloud_storage_analyzer.py:840) [class]: Any of rclone's 40+ backends via ``rclone lsjson``. - unused by GUI.

## content_defined_chunker.py
Suggest: expose via premium cdc_page.py / near_duplicates_page.py - expose chunk/similarity helpers in CDC/near-dup flow
- `ChunkStats()` (src/cortex_unified/analyzers/content_defined_chunker.py:116) [class]: ChunkStats. - unused by GUI.
- `gear_chunk()` (src/cortex_unified/analyzers/content_defined_chunker.py:138) [func]: Content-defined chunking via Gear (FastCDC §3). - unused by GUI.
- `file_chunks()` (src/cortex_unified/analyzers/content_defined_chunker.py:190) [func]: Chunk a file (streamed, bounded). - unused by GUI.
- `jaccard()` (src/cortex_unified/analyzers/content_defined_chunker.py:205) [func]: Jaccard similarity of two fingerprint sets (0..1). - unused by GUI.
- `chunk_similarity()` (src/cortex_unified/analyzers/content_defined_chunker.py:216) [func]: CDC-Jaccard similarity between two byte strings (1.0 = identical). - unused by GUI.
- `vector_cdc_chunk()` (src/cortex_unified/analyzers/content_defined_chunker.py:444) [func]: VectorCDC (FAST'25) accelerated content-defined chunking. - unused by GUI.
- `IdeaInvertedIndex()` (src/cortex_unified/analyzers/content_defined_chunker.py:495) [class]: IDEA: Inverted Deduplication-Aware Index (FAST '24). - unused by GUI.

## czkawka_tools.py
Suggest: expose via EMPTY module - EmptyFinder->empty_files_tab.py; InvalidSymlinkFinder/BrokenFileFinder->broken_links_tab.py; BadExtension/BadNames->heuristics_tab.py; ExifCleaner->privacy_tab.py; TempFileFinder->deep_cleaner_tab.py; VideoOptimizer->new Media page
- `EmptyResult()` (src/cortex_unified/analyzers/czkawka_tools.py:135) [class]: Empty scan result with empty files, folders, and scan stats. - unused by GUI.
- `EmptyFinder()` (src/cortex_unified/analyzers/czkawka_tools.py:142) [class]: Walk a root tree collecting zero-byte files and empty folders. - unused by GUI.
- `SymlinkResult()` (src/cortex_unified/analyzers/czkawka_tools.py:194) [class]: Broken-symlink scan result with link targets and scan stats. - unused by GUI.
- `InvalidSymlinkFinder()` (src/cortex_unified/analyzers/czkawka_tools.py:200) [class]: Walk a root tree collecting symlinks whose targets no longer exist. - unused by GUI.
- `BrokenFileFinder()` (src/cortex_unified/analyzers/czkawka_tools.py:239) [class]: Detect corrupt images, archives, and PDFs via content verification. - unused by GUI.
- `BadExtResult()` (src/cortex_unified/analyzers/czkawka_tools.py:319) [class]: One file whose sniffed content type disagrees with its extension. - unused by GUI.
- `BadExtensionFinder()` (src/cortex_unified/analyzers/czkawka_tools.py:325) [class]: Compare each file's magic-byte type against its claimed extension. - unused by GUI.
- `BadNamesFinder()` (src/cortex_unified/analyzers/czkawka_tools.py:371) [class]: Collect files and folders with illegal, reserved, or overlong names. - unused by GUI.
- `ExifCleaner()` (src/cortex_unified/analyzers/czkawka_tools.py:397) [class]: Scan images for EXIF metadata and strip it to protect privacy. - unused by GUI.
- `TempFileFinder()` (src/cortex_unified/analyzers/czkawka_tools.py:465) [class]: Locate temp/log/backup files under a root or system temp dirs. - unused by GUI.
- `VideoInfo()` (src/cortex_unified/analyzers/czkawka_tools.py:504) [class]: VideoInfo. - unused by GUI.
- `VideoOptimizer()` (src/cortex_unified/analyzers/czkawka_tools.py:517) [class]: VideoOptimizer. - unused by GUI.

## deep_cleaner.py
Suggest: expose via deep_cleaner_tab.py - internal helper get_path_size_safe; no GUI needed
- `get_path_size_safe()` (src/cortex_unified/analyzers/deep_cleaner.py:19) [func]: Recursive byte size of *path*; 0 for anything unreadable. - unused by GUI.

## docker_cleaner.py
Suggest: expose via docker_tab.py - bind dataclasses/CleanupResult to docker clean report
- `DockerImage()` (src/cortex_unified/analyzers/docker_cleaner.py:26) [class]: An image flagged as dangling or referenced by no container. - unused by GUI.
- `DockerContainer()` (src/cortex_unified/analyzers/docker_cleaner.py:42) [class]: A non-running container eligible for removal. - unused by GUI.
- `DockerVolume()` (src/cortex_unified/analyzers/docker_cleaner.py:58) [class]: A volume not mounted by any container. - unused by GUI.
- `DockerNetwork()` (src/cortex_unified/analyzers/docker_cleaner.py:73) [class]: A user-defined network with no attached containers. - unused by GUI.
- `CleanupResult()` (src/cortex_unified/analyzers/docker_cleaner.py:87) [class]: Outcome of a cleanup pass; counts include dry-run simulations. - unused by GUI.

## duplicate_finder.py
Suggest: expose via duplicates_tab.py - internal fastcdc_chunk helper; no direct GUI
- `fastcdc_chunk()` (src/cortex_unified/analyzers/duplicate_finder.py:49) [func]: FastCDC content-defined chunking (paper Algorithm 1). - unused by GUI.

## fuzzy_finder.py
Suggest: expose via premium fuzzy_hash_page.py / duplicates_tab.py - wire fuzzy_hash_*/fuzzy_compare actions
- `fuzzy_hash_bytes()` (src/cortex_unified/analyzers/fuzzy_finder.py:162) [func]: Return an ssdeep-style CTPH signature for *data*. - unused by GUI.
- `fuzzy_hash_file()` (src/cortex_unified/analyzers/fuzzy_finder.py:177) [func]: Fuzzy-hash an entire file (streamed, bounded like ssdeep's 0–64 bases). - unused by GUI.
- `fuzzy_compare()` (src/cortex_unified/analyzers/fuzzy_finder.py:207) [func]: Similarity score 0..100 between two CTPH signatures (higher = closer). - unused by GUI.

## leftover_detector.py
Suggest: expose via uninstaller_tab.py - show DetectedItem/OrphanedFolder/RegistryOrphan/CleanupRecommendation in leftover report
- `DetectedItem()` (src/cortex_unified/analyzers/leftover_detector.py:25) [class]: Base class for detected leftover items. - unused by GUI.
- `OrphanedFolder()` (src/cortex_unified/analyzers/leftover_detector.py:45) [class]: Represents an orphaned application folder. - unused by GUI.
- `InstallerFile()` (src/cortex_unified/analyzers/leftover_detector.py:58) [class]: Represents a detected installer file. - unused by GUI.
- `RegistryOrphan()` (src/cortex_unified/analyzers/leftover_detector.py:70) [class]: Represents an orphaned registry entry (Windows only). - unused by GUI.
- `CleanupRecommendation()` (src/cortex_unified/analyzers/leftover_detector.py:82) [class]: Represents a cleanup recommendation with risk assessment. - unused by GUI.

## near_duplicate_finder.py
Suggest: expose via premium near_duplicates_page.py - expose BloomFilter stats/pre-filter toggle
- `BloomFilter()` (src/cortex_unified/analyzers/near_duplicate_finder.py:72) [class]: Simple Bloom filter with k hash functions. - unused by GUI.

## package_manager_cleaner.py
Suggest: expose via package_manager_tab.py - render CleanupResult/HealthStatus cards
- `CleanupResult()` (src/cortex_unified/analyzers/package_manager_cleaner.py:52) [class]: Outcome of one cache-clean operation (counts, bytes, errors). - unused by GUI.
- `HealthStatus()` (src/cortex_unified/analyzers/package_manager_cleaner.py:68) [class]: Post-cleanup health verdict for a single package manager. - unused by GUI.

## perceptual_duplicate_finder.py
Suggest: expose via premium perceptual_duplicates_page.py - wire *_hash/hamming_distance into image-dup pipeline
- `average_hash()` (src/cortex_unified/analyzers/perceptual_duplicate_finder.py:140) [func]: aHash: 64 bits, bit k set when the k-th 8x8-block mean >= global mean. - unused by GUI.
- `difference_hash()` (src/cortex_unified/analyzers/perceptual_duplicate_finder.py:157) [func]: dHash: 64 bits from horizontal left-vs-right gradients of an 8x9 grid. - unused by GUI.
- `perceptual_hash()` (src/cortex_unified/analyzers/perceptual_duplicate_finder.py:176) [func]: pHash: 64-bit DCT low-frequency hash (the canonical, most robust). - unused by GUI.
- `wavelet_hash()` (src/cortex_unified/analyzers/perceptual_duplicate_finder.py:248) [func]: wHash (Haar wavelet): 64 bits via multi-resolution Haar DWT. - unused by GUI.
- `hamming_distance()` (src/cortex_unified/analyzers/perceptual_duplicate_finder.py:291) [func]: Number of differing bits between two hashes (0..64). - unused by GUI.

## project_cache_scanner.py
Suggest: expose via deep_cleaner_tab.py (Dev caches section) - expose ProjectCacheScanner scan/clean
- `ProjectCacheScanner()` (src/cortex_unified/analyzers/project_cache_scanner.py:119) [class]: Drive-aware scanner for PROJECT_CACHE_CATEGORIES patterns. - unused by GUI.

## registry_cleaner_ai.py
Suggest: expose via registry_cleaner_tab.py / registry_ai_page.py - show RegistryIssue AI verdict column
- `RegistryIssue()` (src/cortex_unified/analyzers/registry_cleaner_ai.py:93) [class]: Single registry issue with ML risk score. - unused by GUI.

## residual_cleaner.py
Suggest: expose via EMPTY module - uninstaller_tab.py leftover/residual sweep section
- `ResidualCleaner()` (src/cortex_unified/analyzers/residual_cleaner.py:15) [class]: Finds leftover files and folders for uninstalled applications. - unused by GUI.

## video_duplicate_finder.py
Suggest: expose via premium video_duplicates_page.py - wire compute_video_fingerprint/video_compare
- `compute_video_fingerprint()` (src/cortex_unified/analyzers/video_duplicate_finder.py:292) [func]: Sequence fingerprint (list of 64-bit pHashes) for a video file. - unused by GUI.
- `video_compare()` (src/cortex_unified/analyzers/video_duplicate_finder.py:312) [func]: Similarity 0.0..1.0 between two video fingerprints. - unused by GUI.

## adaptive_sanitizer.py
Suggest: expose via deep_cleaner_tab.py - SanitizeResult report card
- `SanitizeResult()` (src/cortex_unified/system_tools/adaptive_sanitizer.py:89) [class]: Outcome of one sanitization attempt. - unused by GUI.

## ai_telemetry_cleaner.py
Suggest: expose via privacy_tab.py - AiArtifactInfo list in AI-telemetry section
- `AiArtifactInfo()` (src/cortex_unified/system_tools/ai_telemetry_cleaner.py:35) [class]: Detailed metadata for a discovered AI or Copilot local storage artifact. - unused by GUI.

## app_updater.py
Suggest: expose via system_tools_tab.py / dashboard - UpgradableApp update list
- `UpgradableApp()` (src/cortex_unified/system_tools/app_updater.py:32) [class]: Upgradable App data container. - unused by GUI.

## bitlocker_auditor.py
Suggest: expose via system_tools_tab.py (Security) - EncryptedVolumeInfo volume list
- `EncryptedVolumeInfo()` (src/cortex_unified/system_tools/bitlocker_auditor.py:23) [class]: Encrypted Volume Info data container. - unused by GUI.

## bitrot_scrubber.py
Suggest: expose via system_tools_tab.py (Disk health) - ScrubberRecord/BitRotIssue report
- `ScrubberRecord()` (src/cortex_unified/system_tools/bitrot_scrubber.py:25) [class]: Scrubber Record data container. - unused by GUI.
- `BitRotIssue()` (src/cortex_unified/system_tools/bitrot_scrubber.py:35) [class]: Bit Rot Issue data container. - unused by GUI.

## boot_performance.py
Suggest: expose via startup_manager_tab.py - BootRecord/BootIssue boot-time cards
- `BootRecord()` (src/cortex_unified/system_tools/boot_performance.py:45) [class]: Boot Record data container. - unused by GUI.
- `BootIssue()` (src/cortex_unified/system_tools/boot_performance.py:63) [class]: Boot Issue data container. - unused by GUI.

## browser_cleaner.py
Suggest: expose via EMPTY module - privacy_tab.py deep-browser section (DeepBrowserCleaner/Cleanable)
- `Cleanable()` (src/cortex_unified/system_tools/browser_cleaner.py:75) [class]: Cleanable data container. - unused by GUI.
- `DeepBrowserCleaner()` (src/cortex_unified/system_tools/browser_cleaner.py:156) [class]: Deep Browser Cleaner. - unused by GUI.

## browser_deep_cleaner.py
Suggest: expose via privacy_tab.py - BrowserCleanResult summary
- `BrowserCleanResult()` (src/cortex_unified/system_tools/browser_deep_cleaner.py:30) [class]: Browser Clean Result data container. - unused by GUI.

## checksum_matrix.py
Suggest: expose via system_tools_tab.py - ManifestVerifyItem integrity table
- `ManifestVerifyItem()` (src/cortex_unified/system_tools/checksum_matrix.py:63) [class]: Individual verification status of a file against its manifest entry. - unused by GUI.

## compact_os.py
Suggest: expose via premium compact_os_page.py - FolderEstimate/CompressionResult cards
- `FolderEstimate()` (src/cortex_unified/system_tools/compact_os.py:97) [class]: Folder Estimate data container. - unused by GUI.
- `CompressionResult()` (src/cortex_unified/system_tools/compact_os.py:119) [class]: Compression Result data container. - unused by GUI.

## component_store.py
Suggest: expose via system_tools_tab.py - LeftoverRisk WinSxS rows
- `LeftoverRisk()` (src/cortex_unified/system_tools/component_store.py:39) [class]: What you give up by removing a leftover. - unused by GUI.

## component_store_cleaner.py
Suggest: expose via EMPTY module - deep_cleaner_tab.py / system_tools_tab.py WinSxS clean section
- `ComponentStoreInfo()` (src/cortex_unified/system_tools/component_store_cleaner.py:93) [class]: Parsed output of `DISM /AnalyzeComponentStore`. - unused by GUI.
- `CleanupResult()` (src/cortex_unified/system_tools/component_store_cleaner.py:115) [class]: Cleanup Result data container. - unused by GUI.
- `PackageInfo()` (src/cortex_unified/system_tools/component_store_cleaner.py:127) [class]: Single package from `dism /get-packages`. - unused by GUI.
- `ComponentStoreCleaner()` (src/cortex_unified/system_tools/component_store_cleaner.py:139) [class]: DISM-based Component Store analyzer and cleaner. - unused by GUI.

## crash_dump_cleaner.py
Suggest: expose via deep_cleaner_tab.py - CrashDumpItem/CrashDumpCleanReport section
- `CrashDumpItem()` (src/cortex_unified/system_tools/crash_dump_cleaner.py:18) [class]: Crash Dump Item data container. - unused by GUI.
- `CrashDumpCleanReport()` (src/cortex_unified/system_tools/crash_dump_cleaner.py:28) [class]: Crash Dump Clean Report data container. - unused by GUI.

## delivery_optimization_cleaner.py
Suggest: expose via EMPTY module - system_tools_tab.py Windows-Update section
- `DeliveryOptimizationStatus()` (src/cortex_unified/system_tools/delivery_optimization_cleaner.py:18) [class]: Delivery Optimization Status data container. - unused by GUI.
- `DeliveryOptimizationCleanReport()` (src/cortex_unified/system_tools/delivery_optimization_cleaner.py:27) [class]: Delivery Optimization Clean Report data container. - unused by GUI.
- `DeliveryOptimizationCleaner()` (src/cortex_unified/system_tools/delivery_optimization_cleaner.py:41) [class]: Production Delivery Optimization cache sanitizer. - unused by GUI.

## dev_cleaner.py
Suggest: expose via deep_cleaner_tab.py (Dev) - DevCleanResult card
- `DevCleanResult()` (src/cortex_unified/system_tools/dev_cleaner.py:36) [class]: Dev Clean Result data container. - unused by GUI.

## dev_drive_optimizer.py
Suggest: expose via premium directstorage_page.py / system_tools_tab.py - DevDriveInfo card
- `DevDriveInfo()` (src/cortex_unified/system_tools/dev_drive_optimizer.py:28) [class]: Dev Drive Info data container. - unused by GUI.

## dev_package_cache_cleaner.py
Suggest: expose via deep_cleaner_tab.py (Dev) - DevPackageStoreInfo section
- `DevPackageStoreInfo()` (src/cortex_unified/system_tools/dev_package_cache_cleaner.py:36) [class]: Status and storage consumption of a specific developer package cache. - unused by GUI.

## device_fingerprint.py
Suggest: expose via system_pages / settings - DeviceFingerprint/FingerprintEvidence identity card
- `FingerprintEvidence()` (src/cortex_unified/system_tools/device_fingerprint.py:13) [class]: Fingerprint Evidence data container. - unused by GUI.
- `DeviceFingerprint()` (src/cortex_unified/system_tools/device_fingerprint.py:33) [class]: Device Fingerprint data container. - unused by GUI.

## diagnostic_data_manager.py
Suggest: expose via privacy_tab.py - TelemetrySetting toggles
- `TelemetrySetting()` (src/cortex_unified/system_tools/diagnostic_data_manager.py:25) [class]: Telemetry Setting data container. - unused by GUI.

## directstorage_optimizer.py
Suggest: expose via premium directstorage_page.py - BypassIoVolumeReport card
- `BypassIoVolumeReport()` (src/cortex_unified/system_tools/directstorage_optimizer.py:23) [class]: BypassIO and DirectStorage status for a single storage volume. - unused by GUI.

## disk_benchmark.py
Suggest: expose via system_tools_tab.py - DiskBenchmarkMetric chart
- `DiskBenchmarkMetric()` (src/cortex_unified/system_tools/disk_benchmark.py:23) [class]: Disk Benchmark Metric data container. - unused by GUI.

## dns_benchmark.py
Suggest: expose via system_tools_tab.py (Network) - DnsServerSpec benchmark table
- `DnsServerSpec()` (src/cortex_unified/system_tools/dns_benchmark.py:21) [class]: Dns Server Spec data container. - unused by GUI.

## drive_optimizer.py
Suggest: expose via system_tools_tab.py - OptimizeOp/DriveInfo optimize actions
- `OptimizeOp()` (src/cortex_unified/system_tools/drive_optimizer.py:33) [class]: Optimize Op enumeration. - unused by GUI.
- `DriveInfo()` (src/cortex_unified/system_tools/drive_optimizer.py:41) [class]: Drive Info data container. - unused by GUI.

## driver_inventory.py
Suggest: expose via premium driver_manager_page.py - DriverInfo table
- `DriverInfo()` (src/cortex_unified/system_tools/driver_inventory.py:28) [class]: Driver Info data container. - unused by GUI.

## driver_manager.py
Suggest: expose via premium driver_manager_page.py - DriverInfo detail rows
- `DriverInfo()` (src/cortex_unified/system_tools/driver_manager.py:78) [class]: Single device driver information. - unused by GUI.

## driver_store_cleaner.py
Suggest: expose via premium driver_manager_page.py - DriverCleanResult report
- `DriverCleanResult()` (src/cortex_unified/system_tools/driver_store_cleaner.py:36) [class]: Driver Clean Result data container. - unused by GUI.

## env_variable_manager.py
Suggest: expose via system_tools_tab.py - CleanupResult env-var clean report
- `CleanupResult()` (src/cortex_unified/system_tools/env_variable_manager.py:56) [class]: Cleanup Result data container. - unused by GUI.

## event_log_cleaner.py
Suggest: expose via system_tools_tab.py - EventLogChannel/CleanResult section
- `EventLogChannel()` (src/cortex_unified/system_tools/event_log_cleaner.py:20) [class]: Event Log Channel data container. - unused by GUI.
- `EventLogCleanResult()` (src/cortex_unified/system_tools/event_log_cleaner.py:31) [class]: Event Log Clean Result data container. - unused by GUI.

## event_log_monitor.py
Suggest: expose via resource_monitor_tab.py - LogAnomalyEvent alert feed
- `LogAnomalyEvent()` (src/cortex_unified/system_tools/event_log_monitor.py:22) [class]: Log Anomaly Event data container. - unused by GUI.

## external_exposure.py
Suggest: expose via security_scanner_tab.py - ExternalService/ExposureResult exposure card
- `ExposureLookupError()` (src/cortex_unified/system_tools/external_exposure.py:18) [class]: Raised for invalid consent, target, credentials, or provider output. - unused by GUI.
- `ExternalService()` (src/cortex_unified/system_tools/external_exposure.py:23) [class]: External Service data container. - unused by GUI.
- `ExposureResult()` (src/cortex_unified/system_tools/external_exposure.py:42) [class]: Exposure Result data container. - unused by GUI.

## firewall_manager.py
Suggest: expose via system_tools_tab.py - FirewallRule rule list
- `FirewallRule()` (src/cortex_unified/system_tools/firewall_manager.py:35) [class]: Firewall Rule data container. - unused by GUI.

## font_cache_manager.py
Suggest: expose via system_tools_tab.py - FontCleanResult card
- `FontCleanResult()` (src/cortex_unified/system_tools/font_cache_manager.py:51) [class]: Font Clean Result data container. - unused by GUI.

## free_space_wipe.py
Suggest: expose via file_shredder_tab.py - WipeResult free-space wipe action
- `WipeResult()` (src/cortex_unified/system_tools/free_space_wipe.py:32) [class]: Wipe Result data container. - unused by GUI.

## game_mode.py
Suggest: expose via EMPTY module - system_tools_tab.py or tray menu GameMode toggle (gate behind safety confirm)
- `BoostReport()` (src/cortex_unified/system_tools/game_mode.py:64) [class]: Outcome of starting or stopping a boosted session. - unused by GUI.
- `GameMode()` (src/cortex_unified/system_tools/game_mode.py:92) [class]: Apply and revert a gaming-session performance profile. - unused by GUI.
- `run_proc_checked()` (src/cortex_unified/system_tools/game_mode.py:252) [func]: Convenience wrapper used by diagnostics; True when exit code is 0. - unused by GUI.

## hosts_file_manager.py
Suggest: expose via system_tools_tab.py (Network) - HostsOperationResult editor feedback
- `HostsOperationResult()` (src/cortex_unified/system_tools/hosts_file_manager.py:51) [class]: Hosts Operation Result data container. - unused by GUI.

## junction_auditor.py
Suggest: expose via disk_analyzer_tab.py - ReparseItem junction list
- `ReparseItem()` (src/cortex_unified/system_tools/junction_auditor.py:28) [class]: Reparse Item data container. - unused by GUI.

## lan_scanner.py
Suggest: expose via EMPTY module - system_tools_tab.py Network section / explorer network.py (LanScanner scan view)
- `LanScanner()` (src/cortex_unified/system_tools/lan_scanner.py:49) [class]: Enumerate LAN devices from the OS ARP cache (read-only). - unused by GUI.

## leftover_cleaner.py
Suggest: expose via uninstaller_tab.py - SafetyPolicy/confidence + CleanOutcome report; string helpers are internal
- `edit_distance()` (src/cortex_unified/system_tools/leftover_cleaner.py:64) [func]: Exact Levenshtein distance; early-exits once *max_distance* is exceeded - unused by GUI.
- `match_string_to_product()` (src/cortex_unified/system_tools/leftover_cleaner.py:91) [func]: Decide whether *candidate* (a folder/key name) names *product_name*. - unused by GUI.
- `build_tokens()` (src/cortex_unified/system_tools/leftover_cleaner.py:138) [func]: Extract specific-enough search tokens from an app's display name. - unused by GUI.
- `confidence_level()` (src/cortex_unified/system_tools/leftover_cleaner.py:179) [func]: Map a raw signed score to a human review tier (BCU mapping). - unused by GUI.
- `SafetyPolicy()` (src/cortex_unified/system_tools/leftover_cleaner.py:222) [class]: Paths the scanner/cleaner must never propose or touch. - unused by GUI.
- `detect_installer_type()` (src/cortex_unified/system_tools/leftover_cleaner.py:335) [func]: Classify the installer family from registry fingerprints. - unused by GUI.
- `read_installed_apps()` (src/cortex_unified/system_tools/leftover_cleaner.py:347) [func]: Enumerate installed apps from all Uninstall branches (read-only). - unused by GUI.
- `CleanOutcome()` (src/cortex_unified/system_tools/leftover_cleaner.py:1400) [class]: What happened to one finding during cleanup. - unused by GUI.
- `stamp_now()` (src/cortex_unified/system_tools/leftover_cleaner.py:1664) [func]: Current local time as an ISO-like ``YYYY-MM-DDTHH:MM:SS`` string. - unused by GUI.

## load_tester.py
Suggest: expose via system_tools_tab.py (Network diag, expert) - LoadResult cards; gate behind explicit consent
- `LoadResult()` (src/cortex_unified/system_tools/load_tester.py:172) [class]: Load Result data container. - unused by GUI.

## memory_compression_tuner.py
Suggest: expose via resource_monitor_tab.py - MemoryCompressionStatus card
- `MemoryCompressionStatus()` (src/cortex_unified/system_tools/memory_compression_tuner.py:25) [class]: Memory Compression Status data container. - unused by GUI.

## memory_optimizer.py
Suggest: expose via resource_monitor_tab.py - SystemRamMetrics/MemoryOptimizeResult + memory_stats action
- `SystemRamMetrics()` (src/cortex_unified/system_tools/memory_optimizer.py:22) [class]: System Ram Metrics data container. - unused by GUI.
- `MemoryOptimizeResult()` (src/cortex_unified/system_tools/memory_optimizer.py:44) [class]: Memory Optimize Result data container. - unused by GUI.
- `memory_stats()` (src/cortex_unified/system_tools/memory_optimizer.py:204) [func]: Query current system RAM statistics and top consumer processes. - unused by GUI.

## memory_standby_purger.py
Suggest: expose via premium memory_standby_page.py - wire LUID*/MEMORYSTATUSEX result display (page exists; verify wiring)
- `LUID()` (src/cortex_unified/system_tools/memory_standby_purger.py:39) [class]: L U I D. - unused by GUI.
- `LUID_AND_ATTRIBUTES()` (src/cortex_unified/system_tools/memory_standby_purger.py:47) [class]: L U I D_ A N D_ A T T R I B U T E S. - unused by GUI.
- `TOKEN_PRIVILEGES()` (src/cortex_unified/system_tools/memory_standby_purger.py:55) [class]: T O K E N_ P R I V I L E G E S. - unused by GUI.
- `MEMORYSTATUSEX()` (src/cortex_unified/system_tools/memory_standby_purger.py:63) [class]: M E M O R Y S T A T U S E X. - unused by GUI.

## network_automation.py
Suggest: expose via scheduler_tab.py - NetworkSchedule/NetworkScanScheduler scheduled-scan CRUD
- `NetworkScheduleError()` (src/cortex_unified/system_tools/network_automation.py:38) [class]: Raised when schedule validation or OS task creation fails. - unused by GUI.
- `build_scan_command()` (src/cortex_unified/system_tools/network_automation.py:72) [func]: Build the fixed CLI command; no user-provided executable is accepted. - unused by GUI.
- `build_windows_arguments()` (src/cortex_unified/system_tools/network_automation.py:89) [func]: Build windows arguments. - unused by GUI.

## network_inventory.py
Suggest: expose via premium network_pages.py - Inventory*/normalize/record/export actions (history + CSV)
- `InventoryService()` (src/cortex_unified/system_tools/network_inventory.py:60) [class]: Inventory Service data container. - unused by GUI.
- `InventoryFinding()` (src/cortex_unified/system_tools/network_inventory.py:83) [class]: Inventory Finding data container. - unused by GUI.
- `InventoryDevice()` (src/cortex_unified/system_tools/network_inventory.py:106) [class]: Inventory Device data container. - unused by GUI.
- `DeviceMetadata()` (src/cortex_unified/system_tools/network_inventory.py:132) [class]: Device Metadata data container. - unused by GUI.
- `InventoryChange()` (src/cortex_unified/system_tools/network_inventory.py:154) [class]: Inventory Change data container. - unused by GUI.
- `InventoryChanges()` (src/cortex_unified/system_tools/network_inventory.py:173) [class]: Inventory Changes data container. - unused by GUI.
- `InventorySnapshot()` (src/cortex_unified/system_tools/network_inventory.py:198) [class]: Inventory Snapshot data container. - unused by GUI.
- `normalize_device()` (src/cortex_unified/system_tools/network_inventory.py:330) [func]: Normalize mappings or discovery objects into a validated observation. - unused by GUI.

## network_security_audit.py
Suggest: expose via security_scanner_tab.py - SecurityFinding cards + analyze_services/audit_devices/audit_wan actions
- `SecurityFinding()` (src/cortex_unified/system_tools/network_security_audit.py:15) [class]: Security Finding data container. - unused by GUI.
- `analyze_services()` (src/cortex_unified/system_tools/network_security_audit.py:221) [func]: Compatibility analysis entry point returning fingerprint and findings. - unused by GUI.
- `audit_wan()` (src/cortex_unified/system_tools/network_security_audit.py:349) [func]: Report enabled IGD mappings as exposure observations, never connectivity tests. - unused by GUI.

## network_service_scanner.py
Suggest: expose via system_tools_tab.py Network - ServiceObservation/parse/ports actions + observation_json export
- `ServiceObservation()` (src/cortex_unified/system_tools/network_service_scanner.py:63) [class]: One observed service endpoint on an authorized host. - unused by GUI.
- `parse_allowed_networks()` (src/cortex_unified/system_tools/network_service_scanner.py:192) [func]: Validate explicit private IPv4 scopes. - unused by GUI.
- `ports_for_profile()` (src/cortex_unified/system_tools/network_service_scanner.py:262) [func]: Return the TCP ports a profile covers; DEEP means every port. - unused by GUI.
- `normalize_custom_ports()` (src/cortex_unified/system_tools/network_service_scanner.py:273) [func]: Validate a bounded custom TCP-port set without opening sockets. - unused by GUI.
- `validate_private_target()` (src/cortex_unified/system_tools/network_service_scanner.py:816) [func]: Validate a private IPv4 address against standard LAN ranges. - unused by GUI.
- `observation_json()` (src/cortex_unified/system_tools/network_service_scanner.py:824) [func]: Stable compact JSON, useful for inventory snapshots and tests. - unused by GUI.

## network_stack_optimizer.py
Suggest: expose via system_tools_tab.py Network - TcpGlobalSettings/NetworkResetReport repair actions
- `TcpGlobalSettings()` (src/cortex_unified/system_tools/network_stack_optimizer.py:17) [class]: Tcp Global Settings data container. - unused by GUI.
- `NetworkResetReport()` (src/cortex_unified/system_tools/network_stack_optimizer.py:28) [class]: Network Reset Report data container. - unused by GUI.

## network_tools.py
Suggest: expose via system_tools_tab.py Network - PingResult/Hop ping/traceroute/dns/port/ip tools
- `PingResult()` (src/cortex_unified/system_tools/network_tools.py:47) [class]: Ping Result data container. - unused by GUI.
- `Hop()` (src/cortex_unified/system_tools/network_tools.py:70) [class]: Hop data container. - unused by GUI.

## network_traffic.py
Suggest: expose via resource_monitor_tab.py - NicSample/TrafficSample throughput cards
- `NicSample()` (src/cortex_unified/system_tools/network_traffic.py:25) [class]: Counters and derived rates (bytes/sec) for one network interface. - unused by GUI.
- `TrafficSample()` (src/cortex_unified/system_tools/network_traffic.py:46) [class]: System-wide rates plus per-NIC breakdown, sorted by total activity. - unused by GUI.

## nmap_adapter.py
Suggest: expose via system_tools_tab.py Network - parse_nmap_xml/is_nmap_available/scan_nmap + NmapStatus card
- `NmapUnavailableError()` (src/cortex_unified/system_tools/nmap_adapter.py:44) [class]: Raised when the optional Nmap executable cannot be found. - unused by GUI.
- `NmapAuthorizationError()` (src/cortex_unified/system_tools/nmap_adapter.py:48) [class]: Raised when any requested target is not explicitly authorized. - unused by GUI.
- `NmapPrivilegeError()` (src/cortex_unified/system_tools/nmap_adapter.py:52) [class]: Raised when an expert mode is requested without Windows elevation. - unused by GUI.
- `NmapExecutionError()` (src/cortex_unified/system_tools/nmap_adapter.py:56) [class]: Raised when Nmap exits unsuccessfully. - unused by GUI.
- `NmapOutputError()` (src/cortex_unified/system_tools/nmap_adapter.py:60) [class]: Raised when Nmap XML is malformed, unsafe, or exceeds a bound. - unused by GUI.
- `NmapStatus()` (src/cortex_unified/system_tools/nmap_adapter.py:65) [class]: Side-effect-free optional executable status. - unused by GUI.
- `parse_nmap_xml()` (src/cortex_unified/system_tools/nmap_adapter.py:219) [func]: Parse bounded Nmap XML into deterministic service observations. - unused by GUI.
- `is_nmap_available()` (src/cortex_unified/system_tools/nmap_adapter.py:433) [func]: Return whether the optional executable can be resolved. - unused by GUI.
- `scan_nmap()` (src/cortex_unified/system_tools/nmap_adapter.py:438) [func]: Explicit function API for a bounded optional Nmap scan. - unused by GUI.

## notification_cleaner.py
Suggest: expose via privacy_tab.py / deep_cleaner_tab.py - Notification* status + clean action
- `NotificationDatabaseStatus()` (src/cortex_unified/system_tools/notification_cleaner.py:20) [class]: Notification Database Status data container. - unused by GUI.
- `NotificationCleanResult()` (src/cortex_unified/system_tools/notification_cleaner.py:30) [class]: Notification Clean Result data container. - unused by GUI.

## oui.py
Suggest: expose via system_tools_tab.py Network - vendor lookup display + registry refresh/status actions
- `is_randomized()` (src/cortex_unified/system_tools/oui.py:88) [func]: True when *mac* is a locally-administered (typically privacy) address. - unused by GUI.
- `is_multicast()` (src/cortex_unified/system_tools/oui.py:101) [func]: True for a multicast/broadcast MAC (not a real device address). - unused by GUI.
- `cached_registry_path()` (src/cortex_unified/system_tools/oui.py:184) [func]: Where a downloaded IEEE registry is kept between runs. - unused by GUI.
- `load_ieee_registry()` (src/cortex_unified/system_tools/oui.py:189) [func]: Merge an IEEE registry CSV into the lookup tables. - unused by GUI.
- `load_cached_registry()` (src/cortex_unified/system_tools/oui.py:229) [func]: Load the previously downloaded registry, if present. Never raises. - unused by GUI.
- `ensure_registry_loaded()` (src/cortex_unified/system_tools/oui.py:237) [func]: Load the cached IEEE registry once, on first use. - unused by GUI.
- `has_full_registry()` (src/cortex_unified/system_tools/oui.py:251) [func]: True when a real IEEE registry is loaded (not just the LA conventions). - unused by GUI.
- `registry_age_days()` (src/cortex_unified/system_tools/oui.py:257) [func]: Age of the cached registry in days, or ``None`` when absent. - unused by GUI.
- `registry_status()` (src/cortex_unified/system_tools/oui.py:266) [func]: Describe the vendor database for display in the UI. - unused by GUI.
- `prefix_count()` (src/cortex_unified/system_tools/oui.py:352) [func]: Number of known assignment prefixes (useful for diagnostics/tests). - unused by GUI.

## pagefile_optimizer.py
Suggest: expose via system_tools_tab.py - PagefileConfig/VirtualMemoryStatus cards
- `MEMORYSTATUSEX()` (src/cortex_unified/system_tools/pagefile_optimizer.py:27) [class]: M E M O R Y S T A T U S E X. - unused by GUI.
- `PagefileConfig()` (src/cortex_unified/system_tools/pagefile_optimizer.py:43) [class]: Pagefile Config data container. - unused by GUI.

## power_plan_optimizer.py
Suggest: expose via power_suite_pages / system_tools_tab.py - PowerScheme plan switch UI
- `PowerScheme()` (src/cortex_unified/system_tools/power_plan_optimizer.py:22) [class]: Power Scheme data container. - unused by GUI.

## prefetch_analyzer.py
Suggest: expose via system_tools_tab.py - PrefetchStatus/CleanResult prefetch section
- `PrefetchStatus()` (src/cortex_unified/system_tools/prefetch_analyzer.py:36) [class]: Prefetch Status data container. - unused by GUI.
- `PrefetchCleanResult()` (src/cortex_unified/system_tools/prefetch_analyzer.py:46) [class]: Prefetch Clean Result data container. - unused by GUI.

## privacy_blocker.py
Suggest: expose via premium privacy_blocker_page.py - TweakDef list rendering (verify)
- `TweakDef()` (src/cortex_unified/system_tools/privacy_blocker.py:92) [class]: Single privacy tweak definition. - unused by GUI.

## process_meta.py
Suggest: expose via EMPTY module - process_analyzer_tab.py description column (internal helpers known_description/file_description)
- `known_description()` (src/cortex_unified/system_tools/process_meta.py:91) [func]: Return the curated description for a process *name*, or ''. - unused by GUI.
- `file_description()` (src/cortex_unified/system_tools/process_meta.py:96) [func]: Read the vendor's embedded FileDescription for *exe_path* (cached). - unused by GUI.

## process_token_auditor.py
Suggest: expose via security_scanner_tab.py - ProcessTokenInfo audit report
- `ProcessTokenInfo()` (src/cortex_unified/system_tools/process_token_auditor.py:38) [class]: Process Token Info data container. - unused by GUI.

## restart_manager_unlocker.py
Suggest: expose via system_tools_tab.py / file_shredder_tab.py unlock flow - LockingProcessInfo/FileLockReport display
- `RM_UNIQUE_PROCESS()` (src/cortex_unified/system_tools/restart_manager_unlocker.py:41) [class]: R M_ U N I Q U E_ P R O C E S S. - unused by GUI.
- `RM_PROCESS_INFO()` (src/cortex_unified/system_tools/restart_manager_unlocker.py:49) [class]: R M_ P R O C E S S_ I N F O. - unused by GUI.
- `LockingProcessInfo()` (src/cortex_unified/system_tools/restart_manager_unlocker.py:63) [class]: Identity and telemetry of a process holding an exclusive file lock. - unused by GUI.

## restore_point.py
Suggest: expose via restore_tab.py - RestoreStatus/RestorePointResult cards (verify)
- `RestoreStatus()` (src/cortex_unified/system_tools/restore_point.py:47) [class]: Outcome of a restore-point create attempt - each is honest & distinct. - unused by GUI.
- `RestorePointResult()` (src/cortex_unified/system_tools/restore_point.py:59) [class]: Result of a create attempt. - unused by GUI.

## s3_fifo.py
Suggest: expose via premium s3_fifo_page.py - internal cache; verify page wiring, else no GUI needed
- `S3FIFOStats()` (src/cortex_unified/system_tools/s3_fifo.py:83) [class]: S3 F I F O Stats data container. - unused by GUI.

## sandbox_cleaner.py
Suggest: expose via deep_cleaner_tab.py - VirtualArtifact scan/clean section
- `VirtualArtifact()` (src/cortex_unified/system_tools/sandbox_cleaner.py:23) [class]: Virtual Artifact data container. - unused by GUI.

## secrets_scanner.py
Suggest: expose via security_scanner_tab.py - verify_* buttons, baseline/delta, FP manager, export SARIF/JSON/CSV, HTML via reports_tab.py, serve_dashboard via premium
- `DetectionPattern()` (src/cortex_unified/system_tools/secrets_scanner.py:120) [class]: Detection Pattern data container. - unused by GUI.
- `VerificationResult()` (src/cortex_unified/system_tools/secrets_scanner.py:221) [class]: Verification Result data container. - unused by GUI.
- `compute_confidence()` (src/cortex_unified/system_tools/secrets_scanner.py:929) [func]: Compute confidence. - unused by GUI.
- `scan_file_bytes()` (src/cortex_unified/system_tools/secrets_scanner.py:972) [func]: Scan file bytes. - unused by GUI.
- `scan_single_file()` (src/cortex_unified/system_tools/secrets_scanner.py:1005) [func]: Scan single file. - unused by GUI.
- `walk_files()` (src/cortex_unified/system_tools/secrets_scanner.py:1034) [func]: Walk directory, returning (file_paths, skipped_count). - unused by GUI.
- `compute_risk_score()` (src/cortex_unified/system_tools/secrets_scanner.py:1063) [func]: Compute risk score. - unused by GUI.
- `scan_zip()` (src/cortex_unified/system_tools/secrets_scanner.py:1131) [func]: Scan zip. - unused by GUI.
- `scan_tar()` (src/cortex_unified/system_tools/secrets_scanner.py:1154) [func]: Scan tar. - unused by GUI.
- `verify_aws()` (src/cortex_unified/system_tools/secrets_scanner.py:1273) [func]: Verify aws. - unused by GUI.
- `verify_github()` (src/cortex_unified/system_tools/secrets_scanner.py:1313) [func]: Verify github. - unused by GUI.
- `verify_stripe()` (src/cortex_unified/system_tools/secrets_scanner.py:1325) [func]: Verify stripe. - unused by GUI.
- `verify_slack()` (src/cortex_unified/system_tools/secrets_scanner.py:1340) [func]: Verify slack. - unused by GUI.
- `verify_npm()` (src/cortex_unified/system_tools/secrets_scanner.py:1351) [func]: Verify npm. - unused by GUI.
- `verify_openai()` (src/cortex_unified/system_tools/secrets_scanner.py:1363) [func]: Verify openai. - unused by GUI.
- `verify_all_findings()` (src/cortex_unified/system_tools/secrets_scanner.py:1386) [func]: Verify all findings. - unused by GUI.
- `save_baseline()` (src/cortex_unified/system_tools/secrets_scanner.py:1422) [func]: Save baseline. - unused by GUI.
- `load_baseline()` (src/cortex_unified/system_tools/secrets_scanner.py:1434) [func]: Load baseline. - unused by GUI.
- `compute_delta()` (src/cortex_unified/system_tools/secrets_scanner.py:1442) [func]: Compute delta. - unused by GUI.
- `load_fp_db()` (src/cortex_unified/system_tools/secrets_scanner.py:1457) [func]: Load fp db. - unused by GUI.
- `save_fp_db()` (src/cortex_unified/system_tools/secrets_scanner.py:1465) [func]: Save fp db. - unused by GUI.
- `add_fp()` (src/cortex_unified/system_tools/secrets_scanner.py:1470) [func]: Add fp. - unused by GUI.
- `apply_fp_filter()` (src/cortex_unified/system_tools/secrets_scanner.py:1477) [func]: Apply fp filter. - unused by GUI.
- `save_to_history()` (src/cortex_unified/system_tools/secrets_scanner.py:1491) [func]: Save to history. - unused by GUI.
- `load_history()` (src/cortex_unified/system_tools/secrets_scanner.py:1506) [func]: Load history. - unused by GUI.
- `create_jira_ticket()` (src/cortex_unified/system_tools/secrets_scanner.py:1522) [func]: Create a Jira issue from a finding. Returns issue key or None. - unused by GUI.
- `create_github_issue()` (src/cortex_unified/system_tools/secrets_scanner.py:1558) [func]: Create a GitHub issue from a finding. Returns issue URL or None. - unused by GUI.
- `export_sarif()` (src/cortex_unified/system_tools/secrets_scanner.py:1609) [func]: Export sarif. - unused by GUI.
- `send_slack()` (src/cortex_unified/system_tools/secrets_scanner.py:1639) [func]: Send slack. - unused by GUI.
- `print_terminal_report()` (src/cortex_unified/system_tools/secrets_scanner.py:1977) [func]: Print terminal report. - unused by GUI.
- `DashboardHandler()` (src/cortex_unified/system_tools/secrets_scanner.py:2145) [class]: Dashboard Handler. - unused by GUI.
- `serve_dashboard()` (src/cortex_unified/system_tools/secrets_scanner.py:2166) [func]: Serve dashboard. - unused by GUI.
- `cmd_scan()` (src/cortex_unified/system_tools/secrets_scanner.py:2178) [func]: Cmd scan. - unused by GUI.
- `cmd_baseline()` (src/cortex_unified/system_tools/secrets_scanner.py:2313) [func]: Cmd baseline. - unused by GUI.
- `cmd_fp()` (src/cortex_unified/system_tools/secrets_scanner.py:2341) [func]: Cmd fp. - unused by GUI.
- `cmd_verify()` (src/cortex_unified/system_tools/secrets_scanner.py:2363) [func]: Cmd verify. - unused by GUI.
- `cmd_serve()` (src/cortex_unified/system_tools/secrets_scanner.py:2383) [func]: Cmd serve. - unused by GUI.
- `cmd_patterns()` (src/cortex_unified/system_tools/secrets_scanner.py:2389) [func]: Cmd patterns. - unused by GUI.
- `build_parser()` (src/cortex_unified/system_tools/secrets_scanner.py:2408) [func]: Build parser. - unused by GUI.

## secure_shredder.py
Suggest: expose via premium secure_shredder_page.py - ShredResult/detect_storage_type/smart default (verify)
- `ShredResult()` (src/cortex_unified/system_tools/secure_shredder.py:260) [class]: Shred Result data container. - unused by GUI.
- `detect_storage_type()` (src/cortex_unified/system_tools/secure_shredder.py:347) [func]: Detect storage type for a given path. - unused by GUI.

## shader_cache_cleaner.py
Suggest: expose via deep_cleaner_tab.py (Gaming) - ShaderLocationInfo scan/clean
- `ShaderLocationInfo()` (src/cortex_unified/system_tools/shader_cache_cleaner.py:35) [class]: Metadata and size analysis for a specific shader cache target location. - unused by GUI.

## shellbags_privacy_cleaner.py
Suggest: expose via premium srum_bam_page.py / privacy_tab.py - ShellbagsCleanResult card
- `ShellbagsCleanResult()` (src/cortex_unified/system_tools/shellbags_privacy_cleaner.py:36) [class]: Shellbags Clean Result data container. - unused by GUI.

## sieve_cache.py
Suggest: expose via EMPTY module - internal cache infra (SieveCache/SieveNode); no GUI needed
- `SieveNode()` (src/cortex_unified/system_tools/sieve_cache.py:23) [class]: Internal doubly-linked list node for SIEVE cache. - unused by GUI.
- `SieveCache()` (src/cortex_unified/system_tools/sieve_cache.py:42) [class]: Production thread-safe implementation of the NSDI 2024 SIEVE Cache Algorithm. - unused by GUI.

## slack_space_analyzer.py
Suggest: expose via disk_analyzer_tab.py - DirectorySlackStat/VolumeSlackReport slack view
- `DirectorySlackStat()` (src/cortex_unified/system_tools/slack_space_analyzer.py:23) [class]: Directory Slack Stat data container. - unused by GUI.

## smb_share_auditor.py
Suggest: expose via security_scanner_tab.py - SmbShareInfo/SmbSecurityReport share audit
- `SmbShareInfo()` (src/cortex_unified/system_tools/smb_share_auditor.py:24) [class]: Smb Share Info data container. - unused by GUI.

## srum_bam_cleaner.py
Suggest: expose via premium srum_bam_page.py - SrumDatabaseInfo card (verify)
- `SrumDatabaseInfo()` (src/cortex_unified/system_tools/srum_bam_cleaner.py:53) [class]: Status of the Windows SRUM forensic database. - unused by GUI.

## ssd_trim_optimizer.py
Suggest: expose via system_tools_tab.py - VolumeTrimStatus/TrimAudit/TrimExecution cards
- `VolumeTrimStatus()` (src/cortex_unified/system_tools/ssd_trim_optimizer.py:39) [class]: Storage volume status, media classification, and TRIM capability. - unused by GUI.

## startup_impact_analyzer.py
Suggest: expose via startup_manager_tab.py - StartupAppItem impact list
- `StartupAppItem()` (src/cortex_unified/system_tools/startup_impact_analyzer.py:27) [class]: Startup App Item data container. - unused by GUI.

## startup_optimizer.py
Suggest: expose via premium startup_optimizer_page.py - AppType/StartupEntry delay feature (verify)
- `AppType()` (src/cortex_unified/system_tools/startup_optimizer.py:69) [class]: High-level classification for startup entries used by the UI filter. - unused by GUI.
- `StartupEntry()` (src/cortex_unified/system_tools/startup_optimizer.py:79) [class]: Startup Entry data container. - unused by GUI.

## storage_growth_tracker.py
Suggest: expose via disk_analyzer_tab.py - DirectoryDelta snapshot-compare view
- `DirectoryDelta()` (src/cortex_unified/system_tools/storage_growth_tracker.py:47) [class]: Directory Delta data container. - unused by GUI.

## system_cache_rebuilder.py
Suggest: expose via system_tools_tab.py - CacheRebuildReport rebuild actions
- `CacheRebuildReport()` (src/cortex_unified/system_tools/system_cache_rebuilder.py:22) [class]: Cache Rebuild Report data container. - unused by GUI.

## system_repair.py
Suggest: expose via system_tools_tab.py - RepairResult SFC/DISM/CHKDSK actions
- `RepairResult()` (src/cortex_unified/system_tools/system_repair.py:37) [class]: Repair Result data container. - unused by GUI.

## temp_folder_cleaner.py
Suggest: expose via deep_cleaner_tab.py - TempCleanResult card (verify scan/clean)
- `TempCleanResult()` (src/cortex_unified/system_tools/temp_folder_cleaner.py:45) [class]: Temp Clean Result data container. - unused by GUI.

## update_checker.py
Suggest: expose via settings_tab.py / dashboard - parse_version/fetch_latest_tag auto-check wiring
- `parse_version()` (src/cortex_unified/system_tools/update_checker.py:27) [func]: 'v1.2.3' / '1.2.3' -> (1, 2, 3); anything else -> None. - unused by GUI.
- `fetch_latest_tag()` (src/cortex_unified/system_tools/update_checker.py:44) [func]: Latest release tag from GitHub, or None when offline/blocked. - unused by GUI.

## vhdx_manager.py
Suggest: expose via premium wsl_page.py / disk_analyzer_tab.py - DiskKind/VirtualDisk/CompactResult cards
- `DiskKind()` (src/cortex_unified/system_tools/vhdx_manager.py:44) [class]: Which runtime owns a virtual disk (drives the shutdown advice). - unused by GUI.

## vss_health_analyzer.py
Suggest: expose via restore_tab.py - VssWriterStatus/StorageAllocation/HealthReport cards
- `VssWriterStatus()` (src/cortex_unified/system_tools/vss_health_analyzer.py:39) [class]: Status, state code, and error condition of an NT VSS Writer. - unused by GUI.
- `VssStorageAllocation()` (src/cortex_unified/system_tools/vss_health_analyzer.py:61) [class]: Volume shadow copy storage allocation and limit metrics. - unused by GUI.

## vss_manager.py
Suggest: expose via restore_tab.py - ShadowCopyInfo/ShadowStorageInfo/audit list view
- `ShadowCopyInfo()` (src/cortex_unified/system_tools/vss_manager.py:25) [class]: Shadow Copy Info data container. - unused by GUI.
- `ShadowStorageInfo()` (src/cortex_unified/system_tools/vss_manager.py:36) [class]: Shadow Storage Info data container. - unused by GUI.

## vulnerability_catalog.py
Suggest: expose via security_scanner_tab.py - CatalogError/VersionConstraint/Advisory correlate/match + scheduler refresh
- `CatalogError()` (src/cortex_unified/system_tools/vulnerability_catalog.py:17) [class]: Catalog Error error. - unused by GUI.
- `VersionConstraint()` (src/cortex_unified/system_tools/vulnerability_catalog.py:23) [class]: Version Constraint data container. - unused by GUI.
- `Advisory()` (src/cortex_unified/system_tools/vulnerability_catalog.py:34) [class]: Advisory data container. - unused by GUI.
- `normalize_product()` (src/cortex_unified/system_tools/vulnerability_catalog.py:77) [func]: Normalize product. - unused by GUI.

## wake_on_lan.py
Suggest: expose via system_tools_tab.py Network - validate/build/send magic-packet action + error display
- `WakeOnLanError()` (src/cortex_unified/system_tools/wake_on_lan.py:24) [class]: Base exception for Wake-on-LAN failures. - unused by GUI.
- `InvalidMacAddress()` (src/cortex_unified/system_tools/wake_on_lan.py:28) [class]: Raised when a MAC is malformed or unsafe for a unicast device. - unused by GUI.
- `InvalidBroadcastAddress()` (src/cortex_unified/system_tools/wake_on_lan.py:32) [class]: Raised when a broadcast is outside supplied active LAN scopes. - unused by GUI.
- `WakeOnLanSendError()` (src/cortex_unified/system_tools/wake_on_lan.py:36) [class]: Raised when the bounded UDP send fails. - unused by GUI.
- `validate_broadcast()` (src/cortex_unified/system_tools/wake_on_lan.py:110) [func]: Return a subnet-directed broadcast in a supplied active private LAN. - unused by GUI.
- `build_magic_packet()` (src/cortex_unified/system_tools/wake_on_lan.py:140) [func]: Build the standard 102-byte Wake-on-LAN magic packet. - unused by GUI.

## wan_audit.py
Suggest: expose via EMPTY module - system_tools_tab.py Network / security_scanner_tab.py WAN exposure card (WanAuditor/audit/audit_wan/classify_*)
- `InterfaceStatus()` (src/cortex_unified/system_tools/wan_audit.py:42) [class]: A local IPv4 interface used to establish the audit trust boundary. - unused by GUI.
- `PortMapping()` (src/cortex_unified/system_tools/wan_audit.py:56) [class]: One port mapping returned by ``GetGenericPortMappingEntry``. - unused by GUI.
- `WanStatus()` (src/cortex_unified/system_tools/wan_audit.py:75) [class]: JSON-safe outcome of a WAN audit. - unused by GUI.
- `classify_external_ip()` (src/cortex_unified/system_tools/wan_audit.py:122) [func]: Classify an IGD-reported address without making an external request. - unused by GUI.
- `classify_public_ip()` (src/cortex_unified/system_tools/wan_audit.py:141) [func]: Compatibility wrapper using the previous labels. - unused by GUI.
- `WanAuditor()` (src/cortex_unified/system_tools/wan_audit.py:238) [class]: Perform a synchronous, cancellable, read-only local WAN audit. - unused by GUI.
- `audit_wan()` (src/cortex_unified/system_tools/wan_audit.py:712) [func]: Return route-only status unless optional local UPnP reads are authorized. - unused by GUI.

## winapp2_cleaner.py
Suggest: expose via premium winapp2_page.py - Winapp2Rule target list (verify)
- `Winapp2Rule()` (src/cortex_unified/system_tools/winapp2_cleaner.py:137) [class]: Represents a single parsed Winapp2 application cleaning rule. - unused by GUI.

## windows_update.py
Suggest: expose via premium win_update_repair_page.py - PendingUpdate list (verify)
- `PendingUpdate()` (src/cortex_unified/system_tools/windows_update.py:36) [class]: Pending Update data container. - unused by GUI.

## windows_update_repair.py
Suggest: expose via premium win_update_repair_page.py - PhaseResult/DiagnosticReport/RepairResult flows (verify)
- `PhaseResult()` (src/cortex_unified/system_tools/windows_update_repair.py:95) [class]: Phase Result data container. - unused by GUI.
- `DiagnosticReport()` (src/cortex_unified/system_tools/windows_update_repair.py:106) [class]: Diagnostic Report data container. - unused by GUI.
- `RepairResult()` (src/cortex_unified/system_tools/windows_update_repair.py:125) [class]: Repair Result data container. - unused by GUI.
