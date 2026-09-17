# Complete Program-File-Wise Inventory & Checklist

This document provides an exhaustive, **program-file-by-program-file verification checklist** covering every single source file in the repository.
> **Total Program Files Audited**: 372 files | **Total Analyzed Lines of Code**: 171,722 LOC

Each entry details the file path, total lines of code, core architectural purpose, defined classes, and key exported methods.

## System Maintenance & Optimization Tools

- [ ] **001. [`src/cortex_unified/system_tools/__init__.py`](src/cortex_unified/system_tools/__init__.py)** (74 LOC)
  - **Purpose**: System tools module for Cortex Cleaner.

- [ ] **002. [`src/cortex_unified/system_tools/adaptive_sanitizer.py`](src/cortex_unified/system_tools/adaptive_sanitizer.py)** (598 LOC)
  - **Purpose**: Adaptive privacy-preserving sanitization (PL0-PL3).
  - **Classes (3)**: `PrivacyLevel`, `SanitizeResult` (1 methods: `to_dict`), `AdaptiveSanitizer` (8 methods: `auto_level`, `sanitize`, `_execute`, `_pl0`)

- [ ] **003. [`src/cortex_unified/system_tools/ai_telemetry_cleaner.py`](src/cortex_unified/system_tools/ai_telemetry_cleaner.py)** (376 LOC)
  - **Purpose**: Windows 11 AI, Copilot, Recall & Semantic Telemetry Cleaner.
  - **Classes (4)**: `AiArtifactInfo` (1 methods: `to_dict`), `AiTelemetryReport` (1 methods: `to_dict`), `AiCleanResult` (1 methods: `to_dict`), `AiTelemetryCleaner` (5 methods: `_get_search_roots`, `scan`, `_record_artifact`, `checkpoint_wal_journal`)

- [ ] **004. [`src/cortex_unified/system_tools/app_uninstaller.py`](src/cortex_unified/system_tools/app_uninstaller.py)** (214 LOC)
  - **Purpose**: Windows Application Uninstaller for Cortex Cleaner.
  - **Classes (1)**: `AppUninstaller` (4 methods: `get_installed_apps`, `uninstall_app`, `get_app_size_mb`, `_read_app_entry`)

- [ ] **005. [`src/cortex_unified/system_tools/app_updater.py`](src/cortex_unified/system_tools/app_updater.py)** (249 LOC)
  - **Purpose**: Software Updater - a safe GUI-friendly wrapper over Windows Package Manager.
  - **Classes (2)**: `UpgradableApp` (1 methods: `to_dict`), `AppUpdater` (6 methods: `is_available`, `list_upgradable`, `upgrade`, `upgrade_all`)

- [ ] **006. [`src/cortex_unified/system_tools/bitlocker_auditor.py`](src/cortex_unified/system_tools/bitlocker_auditor.py)** (230 LOC)
  - **Purpose**: Cortex Cleaner — BitLocker & Drive Encryption Auditor.
  - **Classes (3)**: `EncryptedVolumeInfo` (2 methods: `is_protected`, `is_fully_encrypted`), `BitLockerAuditReport`, `BitLockerAuditor` (3 methods: `audit`, `_query_manage_bde`, `_query_wmi_powershell`)

- [ ] **007. [`src/cortex_unified/system_tools/bitrot_scrubber.py`](src/cortex_unified/system_tools/bitrot_scrubber.py)** (197 LOC)
  - **Purpose**: Cortex Cleaner — Silent BitRot & File Integrity Scrubber.
  - **Classes (4)**: `ScrubberRecord`, `BitRotIssue`, `BitRotScrubReport`, `BitRotScrubber` (4 methods: `_init_db`, `_compute_sha256`, `scrub`, `reset_baseline`)

- [ ] **008. [`src/cortex_unified/system_tools/boot_performance.py`](src/cortex_unified/system_tools/boot_performance.py)** (273 LOC)
  - **Purpose**: Boot performance analysis - using Windows' OWN boot measurements.
  - **Classes (3)**: `BootRecord` (2 methods: `boot_seconds`, `to_dict`), `BootIssue` (2 methods: `impact_seconds`, `to_dict`), `BootPerformanceMonitor` (5 methods: `is_supported`, `analyze`, `_script`, `_parse`)

- [ ] **009. [`src/cortex_unified/system_tools/browser_cleaner.py`](src/cortex_unified/system_tools/browser_cleaner.py)** (420 LOC)
  - **Purpose**: Deep Browser Cleaner — IndexedDB, Service Workers, Code Cache, GPU cache, cookies.
  - **Classes (2)**: `Cleanable`, `DeepBrowserCleaner` (6 methods: `scan`, `_scan_chromium_profile`, `_scan_firefox_profile`, `clean`)

- [ ] **010. [`src/cortex_unified/system_tools/browser_deep_cleaner.py`](src/cortex_unified/system_tools/browser_deep_cleaner.py)** (211 LOC)
  - **Purpose**: Cortex Cleaner — Forensic Multi-Browser Deep Privacy & Cache Sanitizer.
  - **Classes (3)**: `BrowserTarget`, `BrowserCleanResult`, `BrowserDeepCleaner` (3 methods: `_dir_stats`, `scan_browser_caches`, `clean_targets`)

- [ ] **011. [`src/cortex_unified/system_tools/browser_extensions.py`](src/cortex_unified/system_tools/browser_extensions.py)** (302 LOC)
  - **Purpose**: Browser-extension audit - read-only inventory of installed extensions.
  - **Classes (2)**: `BrowserExtension` (2 methods: `broad_permissions`, `to_dict`), `BrowserExtensionAuditor` (9 methods: `_localappdata`, `audit`, `_scan_chromium`, `_scan_chromium_ext_root`)

- [ ] **012. [`src/cortex_unified/system_tools/checksum_matrix.py`](src/cortex_unified/system_tools/checksum_matrix.py)** (310 LOC)
  - **Purpose**: Forensic Checksum Matrix & Integrity Manifest Generator/Verifier.
  - **Classes (4)**: `FileChecksumResult` (1 methods: `to_dict`), `ManifestVerifyItem` (1 methods: `to_dict`), `ManifestVerificationReport` (2 methods: `is_all_valid`, `to_dict`), `ChecksumMatrix` (3 methods: `hash_file`, `generate_manifest`, `verify_manifest`)

- [ ] **013. [`src/cortex_unified/system_tools/compact_os.py`](src/cortex_unified/system_tools/compact_os.py)** (541 LOC)
  - **Purpose**: NTFS CompactOS / per-folder NTFS compression support.
  - **Classes (3)**: `FolderEstimate` (1 methods: `to_dict`), `CompressionResult`, `CompactOSManager` (10 methods: `is_supported`, `is_admin`, `compactos_query`, `drive_compression_state`)

- [ ] **014. [`src/cortex_unified/system_tools/component_store.py`](src/cortex_unified/system_tools/component_store.py)** (818 LOC)
  - **Purpose**: Component store (WinSxS) analysis and Windows upgrade leftovers.
  - **Classes (5)**: `LeftoverRisk`, `StoreAnalysis` (3 methods: `explorer_gap_note`, `reclaimable_estimate`, `to_dict`), `Leftover` (3 methods: `removable_here`, `rollback_expired`, `to_dict`), `CleanupOutcome` (2 methods: `freed_bytes`, `to_dict`), `ComponentStore` (12 methods: `is_supported`, `is_elevated`, `analyze`, `_parse_analysis`)

- [ ] **015. [`src/cortex_unified/system_tools/component_store_cleaner.py`](src/cortex_unified/system_tools/component_store_cleaner.py)** (420 LOC)
  - **Purpose**: Component Store / WinSxS Cleaner — DISM-based analysis and cleanup.
  - **Classes (4)**: `ComponentStoreInfo` (1 methods: `reclaimable_gb`), `CleanupResult`, `PackageInfo`, `ComponentStoreCleaner` (9 methods: `_run_dism`, `_parse_analyze`, `_parse_packages`, `analyze`)

- [ ] **016. [`src/cortex_unified/system_tools/context_menu_manager.py`](src/cortex_unified/system_tools/context_menu_manager.py)** (198 LOC)
  - **Purpose**: Cortex Cleaner — Windows Context Menu & Shell Extension Manager.
  - **Classes (3)**: `ContextMenuItem`, `ContextMenuReport`, `ContextMenuManager` (6 methods: `_extract_command`, `_check_program_exists`, `enumerate_context_menu`, `analyze`)

- [ ] **017. [`src/cortex_unified/system_tools/crash_dump_cleaner.py`](src/cortex_unified/system_tools/crash_dump_cleaner.py)** (168 LOC)
  - **Purpose**: Cortex Cleaner — Windows Crash Dump & Error Reporting (WER) Cleaner.
  - **Classes (3)**: `CrashDumpItem`, `CrashDumpCleanReport`, `CrashDumpCleaner` (2 methods: `scan_dumps`, `clean_dumps`)

- [ ] **018. [`src/cortex_unified/system_tools/defender.py`](src/cortex_unified/system_tools/defender.py)** (283 LOC)
  - **Purpose**: Windows Security (Defender) status + quick scan trigger.
  - **Classes (2)**: `DefenderStatus` (2 methods: `healthy`, `to_dict`), `WindowsDefender` (8 methods: `is_supported`, `status`, `_parse_status`, `recent_threats`)

- [ ] **019. [`src/cortex_unified/system_tools/delivery_optimization_cleaner.py`](src/cortex_unified/system_tools/delivery_optimization_cleaner.py)** (134 LOC)
  - **Purpose**: Cortex Cleaner — Windows Delivery Optimization (WUDO) Cache Cleaner.
  - **Classes (3)**: `DeliveryOptimizationStatus`, `DeliveryOptimizationCleanReport`, `DeliveryOptimizationCleaner` (2 methods: `get_status`, `clean_cache`)

- [ ] **020. [`src/cortex_unified/system_tools/dev_cleaner.py`](src/cortex_unified/system_tools/dev_cleaner.py)** (245 LOC)
  - **Purpose**: Cortex Cleaner — Developer Ecosystem & Build Artifacts Purger.
  - **Classes (3)**: `DevCacheItem`, `DevCleanResult`, `DevCleaner` (3 methods: `_dir_metrics`, `scan_dev_caches`, `clean_items`)

- [ ] **021. [`src/cortex_unified/system_tools/dev_drive_optimizer.py`](src/cortex_unified/system_tools/dev_drive_optimizer.py)** (206 LOC)
  - **Purpose**: Cortex Cleaner — ReFS Dev Drive & Block-Cloning Optimizer.
  - **Classes (3)**: `DevDriveInfo`, `DevDriveAuditReport`, `DevDriveOptimizer` (4 methods: `audit`, `_get_logical_drives`, `_inspect_drive`, `test_block_cloning`)

- [ ] **022. [`src/cortex_unified/system_tools/dev_package_cache_cleaner.py`](src/cortex_unified/system_tools/dev_package_cache_cleaner.py)** (264 LOC)
  - **Purpose**: Developer Package Caches (Winget, Cargo, Vcpkg, NuGet, Pip) Deep Cleaner.
  - **Classes (4)**: `DevPackageStoreInfo` (1 methods: `to_dict`), `DevPackageReport` (1 methods: `to_dict`), `DevPackageCleanResult` (1 methods: `to_dict`), `DevPackageCacheCleaner` (3 methods: `get_candidate_stores`, `scan`, `clean`)

- [ ] **023. [`src/cortex_unified/system_tools/device_fingerprint.py`](src/cortex_unified/system_tools/device_fingerprint.py)** (326 LOC)
  - **Purpose**: Pure, conservative device fingerprinting from observed LAN evidence.
  - **Classes (2)**: `FingerprintEvidence` (1 methods: `to_dict`), `DeviceFingerprint` (1 methods: `to_dict`)
  - **Exported Functions (1)**: `fingerprint_device`

- [ ] **024. [`src/cortex_unified/system_tools/diagnostic_data_manager.py`](src/cortex_unified/system_tools/diagnostic_data_manager.py)** (263 LOC)
  - **Purpose**: Cortex Cleaner — Windows Telemetry & Diagnostic Data Manager.
  - **Classes (3)**: `TelemetrySetting`, `TelemetryAuditReport`, `DiagnosticDataManager` (4 methods: `_read_dword`, `_write_dword`, `audit_telemetry`, `apply_maximum_privacy`)

- [ ] **025. [`src/cortex_unified/system_tools/directstorage_optimizer.py`](src/cortex_unified/system_tools/directstorage_optimizer.py)** (185 LOC)
  - **Purpose**: Windows 11 DirectStorage & BypassIO Hardware Acceleration Auditor.
  - **Classes (3)**: `BypassIoVolumeReport` (1 methods: `to_dict`), `DirectStorageAuditReport` (1 methods: `to_dict`), `DirectStorageOptimizer` (3 methods: `parse_bypassio_output`, `_get_active_drives`, `audit`)

- [ ] **026. [`src/cortex_unified/system_tools/disk_benchmark.py`](src/cortex_unified/system_tools/disk_benchmark.py)** (198 LOC)
  - **Purpose**: Cortex Cleaner — Storage Performance & IOPS Disk Benchmark.
  - **Classes (3)**: `DiskBenchmarkMetric`, `DiskBenchmarkReport`, `DiskBenchmarkEngine` (1 methods: `run_benchmark`)

- [ ] **027. [`src/cortex_unified/system_tools/disk_health.py`](src/cortex_unified/system_tools/disk_health.py)** (194 LOC)
  - **Purpose**: Disk health (S.M.A.R.T.) reporting - read-only, honest.
  - **Classes (2)**: `DiskHealth` (2 methods: `is_healthy`, `to_dict`), `DiskHealthMonitor` (4 methods: `is_supported`, `get_health`, `_parse`, `_run`)

- [ ] **028. [`src/cortex_unified/system_tools/dns_benchmark.py`](src/cortex_unified/system_tools/dns_benchmark.py)** (264 LOC)
  - **Purpose**: Cortex Cleaner — Multi-Threaded DNS Latency Benchmark & Optimizer.
  - **Classes (3)**: `DnsServerSpec`, `DnsBenchmarkResult`, `DnsBenchmarkEngine` (5 methods: `_build_dns_query`, `_query_dns`, `benchmark_server`, `run_full_benchmark`)

- [ ] **029. [`src/cortex_unified/system_tools/drive_optimizer.py`](src/cortex_unified/system_tools/drive_optimizer.py)** (234 LOC)
  - **Purpose**: Media-aware drive optimization - the honest way.
  - **Classes (4)**: `OptimizeOp`, `DriveInfo` (1 methods: `to_dict`), `OptimizeResult`, `DriveOptimizer` (6 methods: `is_supported`, `list_drives`, `_recommend`, `optimize`)

- [ ] **030. [`src/cortex_unified/system_tools/driver_inventory.py`](src/cortex_unified/system_tools/driver_inventory.py)** (187 LOC)
  - **Purpose**: Driver inventory - READ-ONLY listing of installed device drivers.
  - **Classes (2)**: `DriverInfo` (1 methods: `to_dict`), `DriverInventory` (5 methods: `is_supported`, `list_drivers`, `_parse`, `_clean_date`)

- [ ] **031. [`src/cortex_unified/system_tools/driver_manager.py`](src/cortex_unified/system_tools/driver_manager.py)** (822 LOC)
  - **Purpose**: Driver Cleaner & Updater — offline-capable, WHQL-verified, restore points.
  - **Classes (4)**: `DriverInfo` (1 methods: `to_dict`), `DriverPack`, `ScanResult` (1 methods: `to_json`), `DriverManager` (17 methods: `_run`, `_run_ps`, `_load_index`, `_save_index`)

- [ ] **032. [`src/cortex_unified/system_tools/driver_store_cleaner.py`](src/cortex_unified/system_tools/driver_store_cleaner.py)** (194 LOC)
  - **Purpose**: Cortex Cleaner — Driver Store Explorer & Superseded Driver Purger.
  - **Classes (3)**: `DriverPackage`, `DriverCleanResult`, `DriverStoreCleaner` (3 methods: `enumerate_drivers`, `delete_driver`, `export_all_drivers`)

- [ ] **033. [`src/cortex_unified/system_tools/env_variable_manager.py`](src/cortex_unified/system_tools/env_variable_manager.py)** (276 LOC)
  - **Purpose**: Cortex Cleaner — Windows Environment Variable & PATH Optimizer.
  - **Classes (5)**: `PathEntry`, `EnvVariable`, `PathAnalysisReport`, `CleanupResult`, `EnvironmentVariableManager` (6 methods: `_read_registry_value`, `_write_registry_value`, `enumerate_variables`, `analyze_path`)

- [ ] **034. [`src/cortex_unified/system_tools/event_log_cleaner.py`](src/cortex_unified/system_tools/event_log_cleaner.py)** (175 LOC)
  - **Purpose**: Cortex Cleaner — Enterprise Windows Event Log Sweeper.
  - **Classes (3)**: `EventLogChannel`, `EventLogCleanResult`, `EventLogCleaner` (3 methods: `list_all_logs`, `clear_log`, `clear_all_logs`)

- [ ] **035. [`src/cortex_unified/system_tools/event_log_monitor.py`](src/cortex_unified/system_tools/event_log_monitor.py)** (154 LOC)
  - **Purpose**: Cortex Cleaner — Windows Event Log Anomaly & Hardware Error Monitor.
  - **Classes (3)**: `LogAnomalyEvent`, `AnomalyScanReport`, `EventLogMonitor` (1 methods: `query_anomalies`)

- [ ] **036. [`src/cortex_unified/system_tools/external_exposure.py`](src/cortex_unified/system_tools/external_exposure.py)** (320 LOC)
  - **Purpose**: Explicit, read-only exposure lookup for a router-reported public IPv4.
  - **Classes (4)**: `ExposureLookupError`, `ExternalService` (1 methods: `to_dict`), `ExposureResult` (1 methods: `to_dict`), `ExternalExposureClient` (3 methods: `lookup`, `_parse_shodan`, `_parse_censys`)

- [ ] **037. [`src/cortex_unified/system_tools/firewall_manager.py`](src/cortex_unified/system_tools/firewall_manager.py)** (356 LOC)
  - **Purpose**: Windows Firewall control - block/allow programs and remote addresses.
  - **Classes (2)**: `FirewallRule` (1 methods: `to_dict`), `FirewallManager` (12 methods: `is_supported`, `block_program`, `allow_program`, `block_remote_address`)

- [ ] **038. [`src/cortex_unified/system_tools/font_cache_manager.py`](src/cortex_unified/system_tools/font_cache_manager.py)** (190 LOC)
  - **Purpose**: Cortex Cleaner — Windows Font Cache Inspector & Optimizer.
  - **Classes (4)**: `FontEntry`, `FontAnalysisReport`, `FontCleanResult`, `FontCacheManager` (5 methods: `_get_fonts_dir`, `_detect_format`, `enumerate_fonts`, `analyze`)

- [ ] **039. [`src/cortex_unified/system_tools/free_space_wipe.py`](src/cortex_unified/system_tools/free_space_wipe.py)** (91 LOC)
  - **Purpose**: Free-space wipe - overwrite the unused space on a volume.
  - **Classes (2)**: `WipeResult`, `FreeSpaceWiper` (3 methods: `is_supported`, `medium_for`, `wipe`)

- [ ] **040. [`src/cortex_unified/system_tools/game_mode.py`](src/cortex_unified/system_tools/game_mode.py)** (354 LOC)
  - **Purpose**: Gaming Mode - one-click, fully reversible PC boost for game sessions.
  - **Classes (2)**: `BoostReport` (1 methods: `to_dict`), `GameMode` (6 methods: `is_supported`, `_candidates`, `preview`, `start`)
  - **Exported Functions (1)**: `run_proc_checked`

- [ ] **041. [`src/cortex_unified/system_tools/health_check.py`](src/cortex_unified/system_tools/health_check.py)** (304 LOC)
  - **Purpose**: One-click PC health check - aggregates the fast, read-only diagnostics.
  - **Classes (3)**: `HealthCheck` (1 methods: `to_dict`), `HealthReport` (1 methods: `to_dict`), `HealthChecker` (8 methods: `run`, `_score`, `_check_disk_space`, `_check_memory`)

- [ ] **042. [`src/cortex_unified/system_tools/hosts_file_manager.py`](src/cortex_unified/system_tools/hosts_file_manager.py)** (185 LOC)
  - **Purpose**: Cortex Cleaner — Windows Hosts File Editor & Anti-Telemetry DNS Shield.
  - **Classes (3)**: `HostEntry`, `HostsOperationResult`, `HostsFileManager` (5 methods: `get_hosts_path`, `parse_hosts_file`, `_create_backup`, `save_hosts_entries`)

- [ ] **043. [`src/cortex_unified/system_tools/junction_auditor.py`](src/cortex_unified/system_tools/junction_auditor.py)** (205 LOC)
  - **Purpose**: Cortex Cleaner — NTFS Hard Link, Junction & Reparse Point Auditor.
  - **Classes (3)**: `ReparseItem`, `JunctionAuditReport`, `JunctionAuditor` (2 methods: `audit`, `remove_dead_junction`)

- [ ] **044. [`src/cortex_unified/system_tools/lan_scanner.py`](src/cortex_unified/system_tools/lan_scanner.py)** (132 LOC)
  - **Purpose**: LAN device discovery - see what else is on your local network.
  - **Classes (2)**: `LanDevice` (1 methods: `to_dict`), `LanScanner` (4 methods: `scan`, `_vendor_for`, `_parse`, `_run`)

- [ ] **045. [`src/cortex_unified/system_tools/leftover_cleaner.py`](src/cortex_unified/system_tools/leftover_cleaner.py)** (1771 LOC)
  - **Purpose**: Leftover Cleaner - find and safely remove what an uninstaller leaves behind.
  - **Classes (7)**: `SafetyPolicy` (2 methods: `build`, `is_prohibited`), `InstalledApp` (1 methods: `to_dict`), `LeftoverFinding` (1 methods: `to_dict`), `ExclusionsStore` (7 methods: `_load`, `save`, `_norm`, `add`), `LeftoverScanner` (29 methods: `_cancelled`, `_allowed`, `_ensure_inventory`, `_load_live_inventory`)
  - **Exported Functions (7)**: `edit_distance`, `match_string_to_product`, `build_tokens`, `confidence_level`, `detect_installer_type`, `read_installed_apps`, `stamp_now`

- [ ] **046. [`src/cortex_unified/system_tools/load_tester.py`](src/cortex_unified/system_tools/load_tester.py)** (543 LOC)
  - **Purpose**: Load / resilience tester - measure how much YOUR OWN service can take.
  - **Classes (6)**: `Authorization` (1 methods: `to_dict`), `TargetAuthorizer` (4 methods: `classify`, `authorize`, `_verify_ownership`, `new_token`), `HttpLoadConfig`, `TcpLoadConfig`, `LoadResult` (4 methods: `rps`, `error_rate`, `percentile`, `summary`)

- [ ] **047. [`src/cortex_unified/system_tools/memory_compression_tuner.py`](src/cortex_unified/system_tools/memory_compression_tuner.py)** (179 LOC)
  - **Purpose**: Cortex Cleaner — Windows Memory Compression & SysMain Optimizer.
  - **Classes (3)**: `MemoryCompressionStatus` (3 methods: `compressed_mb`, `total_ram_gb`, `available_ram_gb`), `MemoryTunerReport`, `MemoryCompressionTuner` (2 methods: `audit`, `set_memory_compression`)

- [ ] **048. [`src/cortex_unified/system_tools/memory_optimizer.py`](src/cortex_unified/system_tools/memory_optimizer.py)** (320 LOC)
  - **Purpose**: Cortex Cleaner — Working Set & System RAM Memory Optimizer.
  - **Classes (4)**: `SystemRamMetrics`, `ProcessMemoryItem`, `MemoryOptimizeResult` (3 methods: `ok`, `message`, `to_dict`), `MemoryOptimizer` (4 methods: `get_system_ram_metrics`, `scan_process_memory`, `trim_process_working_set`, `optimize_all_background_working_sets`)
  - **Exported Functions (2)**: `memory_stats`, `optimize`

- [ ] **049. [`src/cortex_unified/system_tools/memory_standby_purger.py`](src/cortex_unified/system_tools/memory_standby_purger.py)** (234 LOC)
  - **Purpose**: Windows NT Kernel RAM Standby List & Working Set Purger.
  - **Classes (7)**: `LUID`, `LUID_AND_ATTRIBUTES`, `TOKEN_PRIVILEGES`, `MEMORYSTATUSEX`, `MemorySnapshot` (1 methods: `to_dict`)

- [ ] **050. [`src/cortex_unified/system_tools/mft_slack_scrubber.py`](src/cortex_unified/system_tools/mft_slack_scrubber.py)** (242 LOC)
  - **Purpose**: NTFS Master File Table ($MFT) & Directory Index Slack Scrubber.
  - **Classes (3)**: `NtfsMftGeometry` (1 methods: `to_dict`), `MftScrubReport` (1 methods: `to_dict`), `MftSlackScrubber` (4 methods: `query_geometry`, `parse_ntfsinfo_output`, `audit`, `scrub`)

- [ ] **051. [`src/cortex_unified/system_tools/model_cache_manager.py`](src/cortex_unified/system_tools/model_cache_manager.py)** (588 LOC)
  - **Purpose**: Model cache manager – hardlink-aware HF hub, Ollama, LM Studio, ComfyUI.
  - **Classes (2)**: `ModelStore` (1 methods: `to_dict`), `ModelCacheManager` (12 methods: `_get_comfyui_candidates`, `COMFYUI_CANDIDATES`, `_first_existing`, `scan_hf_hub`)

- [ ] **052. [`src/cortex_unified/system_tools/network_automation.py`](src/cortex_unified/system_tools/network_automation.py)** (225 LOC)
  - **Purpose**: Safe Windows scheduling for unattended private-LAN inventory scans.
  - **Classes (3)**: `NetworkSchedule`, `NetworkScheduleError`, `NetworkScanScheduler` (4 methods: `supported`, `create`, `delete`, `status`)
  - **Exported Functions (2)**: `build_scan_command`, `build_windows_arguments`

- [ ] **053. [`src/cortex_unified/system_tools/network_discovery.py`](src/cortex_unified/system_tools/network_discovery.py)** (1692 LOC)
  - **Purpose**: Deep LAN device discovery - find everything actually on your network.
  - **Classes (4)**: `Device` (7 methods: `randomized_mac`, `label`, `_looks_like_uuid`, `kind`), `Interface` (1 methods: `network`), `DiscoveryResult` (1 methods: `to_dict`), `NetworkDiscovery` (28 methods: `scan`, `local_interfaces`, `_local_devices`, `default_gateways`)

- [ ] **054. [`src/cortex_unified/system_tools/network_inventory.py`](src/cortex_unified/system_tools/network_inventory.py)** (1199 LOC)
  - **Purpose**: Persistent, point-in-time network inventory with typed change reporting.
  - **Classes (8)**: `InventoryService` (2 methods: `key`, `to_dict`), `InventoryFinding` (2 methods: `key`, `to_dict`), `InventoryDevice` (1 methods: `to_dict`), `DeviceMetadata` (1 methods: `to_dict`), `InventoryChange` (1 methods: `to_dict`)
  - **Exported Functions (2)**: `normalize_device`, `identity_key_for`

- [ ] **055. [`src/cortex_unified/system_tools/network_monitor.py`](src/cortex_unified/system_tools/network_monitor.py)** (268 LOC)
  - **Purpose**: Network connection monitor - see what's talking to your machine and out.
  - **Classes (2)**: `Connection` (3 methods: `listening_public`, `remote_external`, `to_dict`), `NetworkMonitor` (3 methods: `connections`, `_meta_for`, `summarize`)

- [ ] **056. [`src/cortex_unified/system_tools/network_scan_cli.py`](src/cortex_unified/system_tools/network_scan_cli.py)** (82 LOC)
  - **Purpose**: Noninteractive entry point for scheduled private-LAN inventory scans.
  - **Exported Functions (1)**: `main`

- [ ] **057. [`src/cortex_unified/system_tools/network_security_audit.py`](src/cortex_unified/system_tools/network_security_audit.py)** (557 LOC)
  - **Purpose**: Evidence-backed analysis for authorized private-LAN observations.
  - **Classes (1)**: `SecurityFinding` (5 methods: `to_dict`, `finding_id`, `description`, `recommendation`)
  - **Exported Functions (3)**: `analyze_services`, `audit_devices`, `audit_wan`

- [ ] **058. [`src/cortex_unified/system_tools/network_service_scanner.py`](src/cortex_unified/system_tools/network_service_scanner.py)** (925 LOC)
  - **Purpose**: Bounded, non-destructive service observation on authorized private LANs.
  - **Classes (4)**: `ScanProfile`, `ServiceObservation` (5 methods: `to_dict`, `target`, `service`, `details`), `_RateLimiter` (1 methods: `acquire`), `NetworkServiceScanner` (13 methods: `scan`, `_progress`, `_jobs`, `_scan_tcp`)
  - **Exported Functions (8)**: `parse_allowed_networks`, `parse_network_scope_spec`, `is_authorized_target`, `ports_for_profile`, `normalize_custom_ports`, `parse_custom_port_spec`, `validate_private_target`, `observation_json`

- [ ] **059. [`src/cortex_unified/system_tools/network_stack_optimizer.py`](src/cortex_unified/system_tools/network_stack_optimizer.py)** (234 LOC)
  - **Purpose**: Cortex Cleaner — Enterprise Network Stack & DNS Optimizer.
  - **Classes (3)**: `TcpGlobalSettings`, `NetworkResetReport`, `NetworkStackOptimizer` (8 methods: `flush_dns`, `clear_arp_cache`, `reset_winsock`, `reset_tcp_ip_stack`)

- [ ] **060. [`src/cortex_unified/system_tools/network_tools.py`](src/cortex_unified/system_tools/network_tools.py)** (412 LOC)
  - **Purpose**: Network diagnostic utilities: ping, traceroute, DNS, port & IP checks.
  - **Classes (3)**: `PingResult` (1 methods: `to_dict`), `Hop` (1 methods: `to_dict`), `NetworkTools` (11 methods: `ping`, `_parse_ping`, `traceroute`, `_parse_traceroute`)

- [ ] **061. [`src/cortex_unified/system_tools/network_traffic.py`](src/cortex_unified/system_tools/network_traffic.py)** (169 LOC)
  - **Purpose**: Live network throughput monitor - system-wide and per-interface.
  - **Classes (3)**: `NicSample` (1 methods: `to_dict`), `TrafficSample` (1 methods: `to_dict`), `TrafficMonitor` (2 methods: `instance`, `sample`)

- [ ] **062. [`src/cortex_unified/system_tools/nmap_adapter.py`](src/cortex_unified/system_tools/nmap_adapter.py)** (545 LOC)
  - **Purpose**: Optional Nmap integration, bounded to explicitly authorized private LANs.
  - **Classes (8)**: `NmapError`, `NmapUnavailableError`, `NmapAuthorizationError`, `NmapPrivilegeError`, `NmapExecutionError`
  - **Exported Functions (4)**: `parse_nmap_xml`, `nmap_status`, `is_nmap_available`, `scan_nmap`

- [ ] **063. [`src/cortex_unified/system_tools/notification_cleaner.py`](src/cortex_unified/system_tools/notification_cleaner.py)** (126 LOC)
  - **Purpose**: Cortex Cleaner — Windows Action Center & Push Notification Database Cleaner.
  - **Classes (3)**: `NotificationDatabaseStatus`, `NotificationCleanResult`, `NotificationCleaner` (2 methods: `get_status`, `clean_notification_database`)

- [ ] **064. [`src/cortex_unified/system_tools/oui.py`](src/cortex_unified/system_tools/oui.py)** (432 LOC)
  - **Purpose**: MAC address identity: IEEE-backed vendor lookup and privacy detection.
  - **Exported Functions (16)**: `normalize`, `is_randomized`, `is_multicast`, `lookup`, `shorten`, `describe_vendor`, `cache_dir`, `cached_registry_path`

- [ ] **065. [`src/cortex_unified/system_tools/pagefile_optimizer.py`](src/cortex_unified/system_tools/pagefile_optimizer.py)** (230 LOC)
  - **Purpose**: Cortex Cleaner — Windows Pagefile & Virtual Memory Optimizer.
  - **Classes (4)**: `MEMORYSTATUSEX`, `PagefileConfig`, `VirtualMemoryStatus`, `PagefileOptimizer` (5 methods: `get_memory_metrics`, `get_pagefile_config`, `get_status`, `set_custom_pagefile`)

- [ ] **066. [`src/cortex_unified/system_tools/performance_tuner.py`](src/cortex_unified/system_tools/performance_tuner.py)** (132 LOC)
  - **Purpose**: Windows power-plan tuner - safe, reversible performance control.
  - **Classes (2)**: `PowerPlan` (1 methods: `to_dict`), `PerformanceTuner` (6 methods: `is_supported`, `list_plans`, `_parse`, `active_plan`)

- [ ] **067. [`src/cortex_unified/system_tools/power_plan_optimizer.py`](src/cortex_unified/system_tools/power_plan_optimizer.py)** (163 LOC)
  - **Purpose**: Cortex Cleaner — Windows Power Scheme & CPU Throttle Optimizer.
  - **Classes (3)**: `PowerScheme`, `PowerPlanStatus`, `PowerPlanOptimizer` (5 methods: `get_status`, `set_active_scheme`, `unlock_ultimate_performance_plan`, `set_reduced_hibernation`)

- [ ] **068. [`src/cortex_unified/system_tools/prefetch_analyzer.py`](src/cortex_unified/system_tools/prefetch_analyzer.py)** (201 LOC)
  - **Purpose**: Cortex Cleaner — Windows Prefetch & SysMain (SuperFetch) Trace Analyzer.
  - **Classes (4)**: `PrefetchEntry`, `PrefetchStatus`, `PrefetchCleanResult`, `PrefetchAnalyzer` (3 methods: `get_status`, `scan_prefetch_files`, `clean_prefetch`)

- [ ] **069. [`src/cortex_unified/system_tools/privacy_blocker.py`](src/cortex_unified/system_tools/privacy_blocker.py)** (989 LOC)
  - **Purpose**: Privacy & Telemetry Blocker — 300+ settings, IFEO persistence, profiles.
  - **Classes (2)**: `TweakDef` (1 methods: `applies_to_current_os`), `PrivacyBlocker` (18 methods: `_reg_set`, `_reg_get`, `_reg_backup`, `_svc_set_start`)

- [ ] **070. [`src/cortex_unified/system_tools/process_analyzer.py`](src/cortex_unified/system_tools/process_analyzer.py)** (340 LOC)
  - **Purpose**: Process and service enumeration via platform CLI tools.
  - **Classes (1)**: `ProcessAnalyzer` (12 methods: `list_processes`, `_list_windows_processes`, `_list_macos_processes`, `_list_linux_processes`)

- [ ] **071. [`src/cortex_unified/system_tools/process_meta.py`](src/cortex_unified/system_tools/process_meta.py)** (127 LOC)
  - **Purpose**: Human-friendly process identity: what a running program actually is.
  - **Exported Functions (3)**: `known_description`, `file_description`, `describe`

- [ ] **072. [`src/cortex_unified/system_tools/process_token_auditor.py`](src/cortex_unified/system_tools/process_token_auditor.py)** (264 LOC)
  - **Purpose**: Cortex Cleaner — Process Security Token & Integrity Forensics.
  - **Classes (3)**: `ProcessTokenInfo`, `ProcessTokenAuditReport`, `ProcessTokenAuditor` (5 methods: `audit`, `_inspect_token`, `_get_integrity_level`, `_get_elevation_type`)

- [ ] **073. [`src/cortex_unified/system_tools/registry_cleaner.py`](src/cortex_unified/system_tools/registry_cleaner.py)** (571 LOC)
  - **Purpose**: Orphaned Windows registry entry detection with export-before-delete safety.
  - **Classes (1)**: `RegistryCleaner` (15 methods: `scan`, `scan_orphaned_entries`, `_scan_uninstall_entries`, `_check_uninstall_entry`)

- [ ] **074. [`src/cortex_unified/system_tools/restart_manager_unlocker.py`](src/cortex_unified/system_tools/restart_manager_unlocker.py)** (311 LOC)
  - **Purpose**: Windows Native Restart Manager File Unlocker & Process Lock Auditor.
  - **Classes (6)**: `RM_UNIQUE_PROCESS`, `RM_PROCESS_INFO`, `LockingProcessInfo` (1 methods: `to_dict`), `FileLockReport` (1 methods: `to_dict`), `UnlockResult` (1 methods: `to_dict`)

- [ ] **075. [`src/cortex_unified/system_tools/restore_point.py`](src/cortex_unified/system_tools/restore_point.py)** (303 LOC)
  - **Purpose**: Windows System Restore point management - the trust/safety foundation.
  - **Classes (3)**: `RestoreStatus`, `RestorePointResult` (3 methods: `created`, `ok_to_proceed`, `to_dict`), `RestorePointManager` (7 methods: `is_supported`, `is_elevated`, `create`, `_parse_create_output`)

- [ ] **076. [`src/cortex_unified/system_tools/s3_fifo.py`](src/cortex_unified/system_tools/s3_fifo.py)** (389 LOC)
  - **Purpose**: S3-FIFO cache eviction — "FIFO queues are all you need" (SOSP'23).
  - **Classes (3)**: `_Entry`, `S3FIFOStats` (1 methods: `to_dict`), `S3FIFO` (13 methods: `_ghost_contains`, `_ghost_add`, `_ghost_remove`, `_evict_small_if_needed`)

- [ ] **077. [`src/cortex_unified/system_tools/sandbox_cleaner.py`](src/cortex_unified/system_tools/sandbox_cleaner.py)** (166 LOC)
  - **Purpose**: Cortex Cleaner — Windows Sandbox & Virtual Environment Artifact Purger.
  - **Classes (3)**: `VirtualArtifact` (2 methods: `size_mb`, `size_gb`), `SandboxCleanReport`, `SandboxCleaner` (2 methods: `scan`, `clean`)

- [ ] **078. [`src/cortex_unified/system_tools/search_index_optimizer.py`](src/cortex_unified/system_tools/search_index_optimizer.py)** (197 LOC)
  - **Purpose**: Cortex Cleaner — Windows Search Index Database (Windows.edb) Optimizer.
  - **Classes (3)**: `SearchIndexStatus`, `SearchIndexOperationResult`, `SearchIndexOptimizer` (3 methods: `get_status`, `compact_database`, `rebuild_index`)

- [ ] **079. [`src/cortex_unified/system_tools/secrets_scanner.py`](src/cortex_unified/system_tools/secrets_scanner.py)** (3378 LOC)
  - **Purpose**: Filesystem secrets scanner with live credential validation.
  - **Classes (5)**: `DetectionPattern`, `Finding` (3 methods: `to_dict`, `severity_rank`, `fingerprint`), `ScanStats` (7 methods: `critical`, `high`, `medium`, `low`), `VerificationResult` (1 methods: `status_emoji`), `DashboardHandler` (2 methods: `log_message`, `do_GET`)
  - **Exported Functions (43)**: `compute_confidence`, `scan_file_bytes`, `scan_single_file`, `walk_files`, `compute_risk_score`, `run_scan`, `scan_zip`, `scan_tar`

- [ ] **080. [`src/cortex_unified/system_tools/secure_shredder.py`](src/cortex_unified/system_tools/secure_shredder.py)** (739 LOC)
  - **Purpose**: Secure File Shredder — DoD 5220.22-M, Gutmann, NIST 800-88, SSD TRIM.
  - **Classes (4)**: `StorageType`, `ShredStandard` (4 methods: `passes`, `name`, `pass_count`, `recommended_for`), `ShredResult` (1 methods: `to_dict`), `SecureShredder` (6 methods: `_write_pass`, `shred_file`, `_shred_ssd_firmware`, `shred_files`)
  - **Exported Functions (1)**: `detect_storage_type`

- [ ] **081. [`src/cortex_unified/system_tools/service_manager.py`](src/cortex_unified/system_tools/service_manager.py)** (277 LOC)
  - **Purpose**: Cortex Cleaner — Windows Service Manager & Profile Optimizer.
  - **Classes (3)**: `ServiceInfo`, `ServiceProfileResult`, `WindowsServiceManager` (4 methods: `enumerate_services`, `stop_service`, `set_startup_type`, `apply_profile`)

- [ ] **082. [`src/cortex_unified/system_tools/shader_cache_cleaner.py`](src/cortex_unified/system_tools/shader_cache_cleaner.py)** (218 LOC)
  - **Purpose**: GPU & DirectX Shader Cache Forensics & Cleanup Engine.
  - **Classes (4)**: `ShaderLocationInfo` (1 methods: `to_dict`), `ShaderCacheReport` (1 methods: `to_dict`), `ShaderCleanResult` (1 methods: `to_dict`), `ShaderCacheCleaner` (3 methods: `get_known_locations`, `scan`, `clean`)

- [ ] **083. [`src/cortex_unified/system_tools/shellbags_privacy_cleaner.py`](src/cortex_unified/system_tools/shellbags_privacy_cleaner.py)** (215 LOC)
  - **Purpose**: Cortex Cleaner — Windows Shellbags & JumpLists Activity Forensics Purger.
  - **Classes (3)**: `ShellbagsTarget`, `ShellbagsCleanResult`, `ShellbagsPrivacyCleaner` (4 methods: `_count_reg_keys`, `_delete_reg_tree`, `scan_shell_activity`, `clean_shell_activity`)

- [ ] **084. [`src/cortex_unified/system_tools/sieve_cache.py`](src/cortex_unified/system_tools/sieve_cache.py)** (255 LOC)
  - **Purpose**: SIEVE Cache Eviction Algorithm.
  - **Classes (2)**: `SieveNode`, `SieveCache` (12 methods: `get`, `contains`, `put`, `_insert_head`)

- [ ] **085. [`src/cortex_unified/system_tools/slack_space_analyzer.py`](src/cortex_unified/system_tools/slack_space_analyzer.py)** (159 LOC)
  - **Purpose**: Cortex Cleaner — NTFS Disk Cluster & Slack Space Forensics Analyzer.
  - **Classes (3)**: `DirectorySlackStat`, `VolumeSlackReport`, `SlackSpaceAnalyzer` (2 methods: `get_cluster_size`, `analyze_directory`)

- [ ] **086. [`src/cortex_unified/system_tools/smb_share_auditor.py`](src/cortex_unified/system_tools/smb_share_auditor.py)** (190 LOC)
  - **Purpose**: Cortex Cleaner — Network Share & SMB Exposure Auditor.
  - **Classes (3)**: `SmbShareInfo`, `SmbSecurityReport`, `SmbShareAuditor` (4 methods: `audit`, `_list_shares`, `_check_smbv1`, `_check_smb_signing`)

- [ ] **087. [`src/cortex_unified/system_tools/srum_bam_cleaner.py`](src/cortex_unified/system_tools/srum_bam_cleaner.py)** (237 LOC)
  - **Purpose**: Windows BAM/DAM & SRUM Forensic Privacy Cleaner.
  - **Classes (4)**: `BamExecutionEntry` (1 methods: `to_dict`), `SrumDatabaseInfo` (1 methods: `to_dict`), `SrumBamReport` (1 methods: `to_dict`), `SrumBamCleaner` (4 methods: `_filetime_to_datetime`, `query_srum`, `scan`, `clean_bam_entries`)

- [ ] **088. [`src/cortex_unified/system_tools/ssd_trim_optimizer.py`](src/cortex_unified/system_tools/ssd_trim_optimizer.py)** (276 LOC)
  - **Purpose**: Solid-State Drive (SSD) NVMe TRIM & Flash Wear-Leveling Optimizer.
  - **Classes (4)**: `VolumeTrimStatus` (1 methods: `to_dict`), `TrimAuditReport` (1 methods: `to_dict`), `TrimExecutionResult` (1 methods: `to_dict`), `SsdTrimOptimizer` (3 methods: `query_global_trim_enabled`, `audit_volumes`, `retrim_volume`)

- [ ] **089. [`src/cortex_unified/system_tools/startup_impact_analyzer.py`](src/cortex_unified/system_tools/startup_impact_analyzer.py)** (250 LOC)
  - **Purpose**: Cortex Cleaner — Windows Startup Impact Analyzer & Delayed Launch Sequencer.
  - **Classes (3)**: `StartupAppItem`, `StartupImpactReport`, `StartupImpactAnalyzer` (5 methods: `_extract_exe_path`, `_read_startup_approved_state`, `_calculate_impact`, `analyze_startup`)

- [ ] **090. [`src/cortex_unified/system_tools/startup_manager.py`](src/cortex_unified/system_tools/startup_manager.py)** (534 LOC)
  - **Purpose**: Startup item enumeration and disabling across platforms.
  - **Classes (1)**: `StartupManager` (17 methods: `list_startup_items`, `_list_windows_startup_items`, `_read_registry_startup_items`, `_read_startup_folder_items`)

- [ ] **091. [`src/cortex_unified/system_tools/startup_optimizer.py`](src/cortex_unified/system_tools/startup_optimizer.py)** (500 LOC)
  - **Purpose**: Startup Optimizer — stagger/delay engine with resource-aware gating.
  - **Classes (3)**: `AppType`, `StartupEntry` (1 methods: `to_dict`), `StartupOptimizer` (9 methods: `enumerate`, `_load_delays`, `_save_delays`, `set_delay`)

- [ ] **092. [`src/cortex_unified/system_tools/storage_growth_tracker.py`](src/cortex_unified/system_tools/storage_growth_tracker.py)** (273 LOC)
  - **Purpose**: Cortex Cleaner — Storage Growth Tracker & Timeline Differ.
  - **Classes (4)**: `SnapshotSummary` (2 methods: `formatted_time`, `total_gb`), `DirectoryDelta` (2 methods: `growth_mb`, `growth_gb`), `StorageGrowthDiffReport` (1 methods: `net_growth_gb`), `StorageGrowthTracker` (4 methods: `_init_db`, `take_snapshot`, `list_snapshots`, `compare_snapshots`)

- [ ] **093. [`src/cortex_unified/system_tools/storage_sense.py`](src/cortex_unified/system_tools/storage_sense.py)** (177 LOC)
  - **Purpose**: Storage Sense - surface and configure Windows' built-in auto-cleanup.
  - **Classes (1)**: `StorageSense` (8 methods: `is_supported`, `get_status`, `_read_values`, `_interpret`)

- [ ] **094. [`src/cortex_unified/system_tools/system_cache_rebuilder.py`](src/cortex_unified/system_tools/system_cache_rebuilder.py)** (249 LOC)
  - **Purpose**: Cortex Cleaner — Windows Font, Icon & Thumbnail Cache Rebuilder.
  - **Classes (2)**: `CacheRebuildReport`, `SystemCacheRebuilder` (5 methods: `rebuild_font_cache`, `rebuild_icon_thumbnail_cache`, `notify_shell_refresh`, `restart_explorer`)

- [ ] **095. [`src/cortex_unified/system_tools/system_info.py`](src/cortex_unified/system_tools/system_info.py)** (180 LOC)
  - **Purpose**: System information & diagnostics - lightweight, offline, read-only.
  - **Classes (1)**: `SystemInfo` (7 methods: `platform_info`, `cpu_info`, `memory_info`, `disk_info`)

- [ ] **096. [`src/cortex_unified/system_tools/system_repair.py`](src/cortex_unified/system_tools/system_repair.py)** (331 LOC)
  - **Purpose**: System file health & repair - orchestrating Windows' own repair tools.
  - **Classes (2)**: `RepairResult` (1 methods: `to_dict`), `SystemRepair` (10 methods: `is_supported`, `is_elevated`, `run_sfc`, `_parse_sfc`)

- [ ] **097. [`src/cortex_unified/system_tools/task_manager.py`](src/cortex_unified/system_tools/task_manager.py)** (299 LOC)
  - **Purpose**: Task manager backend - live process + resource monitor with honest totals.
  - **Classes (1)**: `TaskManager` (7 methods: `instance`, `snapshot`, `_refresh_handles`, `end_process`)

- [ ] **098. [`src/cortex_unified/system_tools/telemetry_blocker.py`](src/cortex_unified/system_tools/telemetry_blocker.py)** (470 LOC)
  - **Purpose**: Telemetry Blocker — comprehensive Windows privacy hardening via Registry.
  - **Classes (1)**: `TelemetryBlocker` (9 methods: `rules`, `_build_rules`, `_backup_key`, `_save_backup`)

- [ ] **099. [`src/cortex_unified/system_tools/temp_folder_cleaner.py`](src/cortex_unified/system_tools/temp_folder_cleaner.py)** (194 LOC)
  - **Purpose**: Cortex Cleaner — Windows Temp Folder Deep Scanner & Auto-Cleaner.
  - **Classes (4)**: `TempLocation`, `TempScanReport`, `TempCleanResult`, `TempFolderCleaner` (3 methods: `_get_temp_locations`, `scan`, `clean`)

- [ ] **100. [`src/cortex_unified/system_tools/update_checker.py`](src/cortex_unified/system_tools/update_checker.py)** (78 LOC)
  - **Purpose**: Release update checker - informational only.
  - **Exported Functions (4)**: `parse_version`, `current_version`, `fetch_latest_tag`, `check_for_update`

- [ ] **101. [`src/cortex_unified/system_tools/vhdx_manager.py`](src/cortex_unified/system_tools/vhdx_manager.py)** (680 LOC)
  - **Purpose**: Virtual disk (VHDX) reclaim for WSL2, Docker Desktop and Hyper-V.
  - **Classes (4)**: `DiskKind`, `VirtualDisk` (4 methods: `potential_saving_bytes`, `can_compact`, `status_note`, `to_dict`), `CompactResult` (2 methods: `freed_bytes`, `to_dict`), `VhdxManager` (17 methods: `is_supported`, `list_disks`, `_wsl_disks`, `_docker_disks`)

- [ ] **102. [`src/cortex_unified/system_tools/vss_health_analyzer.py`](src/cortex_unified/system_tools/vss_health_analyzer.py)** (360 LOC)
  - **Purpose**: Volume Shadow Copy (VSS) Writer Health, Shadow Storage & State Recovery Engine.
  - **Classes (5)**: `VssWriterStatus` (1 methods: `to_dict`), `VssStorageAllocation` (1 methods: `to_dict`), `VssHealthReport` (1 methods: `to_dict`), `VssResetResult` (1 methods: `to_dict`), `VssHealthAnalyzer` (6 methods: `inspect_health`, `_parse_writers`, `_build_writer_status`, `_parse_shadowstorage`)

- [ ] **103. [`src/cortex_unified/system_tools/vss_manager.py`](src/cortex_unified/system_tools/vss_manager.py)** (340 LOC)
  - **Purpose**: Cortex Cleaner — Volume Shadow Copy (VSS) & Snapshot Manager.
  - **Classes (4)**: `ShadowCopyInfo`, `ShadowStorageInfo` (3 methods: `used_gb`, `allocated_gb`, `max_gb`), `VssAuditReport`, `VssManager` (5 methods: `audit`, `list_shadows`, `list_shadow_storage`, `create_shadow_copy`)

- [ ] **104. [`src/cortex_unified/system_tools/vulnerability_catalog.py`](src/cortex_unified/system_tools/vulnerability_catalog.py)** (344 LOC)
  - **Purpose**: Versioned, local-only advisory catalog with exact product/version matching.
  - **Classes (4)**: `CatalogError`, `VersionConstraint` (1 methods: `to_dict`), `Advisory` (2 methods: `to_dict`, `to_finding`), `VulnerabilityCatalog` (4 methods: `to_dict`, `load`, `match`, `correlate`)
  - **Exported Functions (1)**: `normalize_product`

- [ ] **105. [`src/cortex_unified/system_tools/wake_on_lan.py`](src/cortex_unified/system_tools/wake_on_lan.py)** (201 LOC)
  - **Purpose**: Strict, scope-bound Wake-on-LAN packet construction and transmission.
  - **Classes (4)**: `WakeOnLanError`, `InvalidMacAddress`, `InvalidBroadcastAddress`, `WakeOnLanSendError`
  - **Exported Functions (4)**: `validate_mac`, `validate_broadcast`, `build_magic_packet`, `send_magic_packet`

- [ ] **106. [`src/cortex_unified/system_tools/wan_audit.py`](src/cortex_unified/system_tools/wan_audit.py)** (871 LOC)
  - **Purpose**: Read-only, local-only WAN and UPnP IGD audit.
  - **Classes (5)**: `InterfaceStatus` (1 methods: `to_dict`), `PortMapping` (1 methods: `to_dict`), `WanStatus` (2 methods: `public_ip_classification`, `to_dict`), `WanAuditor` (12 methods: `audit`, `_cancelled`, `_progress`, `local_interfaces`), `_NoMoreMappings`
  - **Exported Functions (3)**: `classify_external_ip`, `classify_public_ip`, `audit_wan`

- [ ] **107. [`src/cortex_unified/system_tools/winapp2_cleaner.py`](src/cortex_unified/system_tools/winapp2_cleaner.py)** (465 LOC)
  - **Purpose**: Declarative Community & Third-Party Application Cleaner (Winapp2.ini Engine).
  - **Classes (4)**: `Winapp2Rule`, `AppCleanTarget`, `Winapp2Report` (1 methods: `to_dict`), `Winapp2Cleaner` (6 methods: `expand_vars`, `_load_rules`, `_is_app_installed`, `is_safe_path`)

- [ ] **108. [`src/cortex_unified/system_tools/windows_update.py`](src/cortex_unified/system_tools/windows_update.py)** (249 LOC)
  - **Purpose**: Windows Update status - what's pending and when you last updated.
  - **Classes (2)**: `PendingUpdate` (1 methods: `to_dict`), `WindowsUpdate` (8 methods: `is_supported`, `last_activity`, `_read_result_time`, `check_pending`)

- [ ] **109. [`src/cortex_unified/system_tools/windows_update_repair.py`](src/cortex_unified/system_tools/windows_update_repair.py)** (827 LOC)
  - **Purpose**: Windows Update Repair Toolkit — comprehensive component reset and repair.
  - **Classes (4)**: `PhaseResult`, `DiagnosticReport` (1 methods: `to_json`), `RepairResult` (1 methods: `summary`), `WindowsUpdateRepair` (21 methods: `_run`, `_run_ps`, `_sc_query`, `_service_status`)

- [ ] **110. [`src/cortex_unified/system_tools/wsl_cleaner.py`](src/cortex_unified/system_tools/wsl_cleaner.py)** (345 LOC)
  - **Purpose**: WSL distro cleanup: size reporting, shutdown + vhdx compaction.
  - **Classes (2)**: `WslDistro` (1 methods: `to_dict`), `WslCleaner` (8 methods: `is_supported`, `is_wsl_available`, `list_distros`, `shutdown`)

## File & Deduplication Analyzers

- [ ] **111. [`src/cortex_unified/analyzers/__init__.py`](src/cortex_unified/analyzers/__init__.py)** (110 LOC)
  - **Purpose**: Analyzers module for Cortex Cleaner.

- [ ] **112. [`src/cortex_unified/analyzers/advanced_disk_analyzer.py`](src/cortex_unified/analyzers/advanced_disk_analyzer.py)** (803 LOC)
  - **Purpose**: Advanced Disk Analyzer — scandir walk, treemap/sunburst, cloud targets.
  - **Classes (7)**: `FileEntry`, `FolderNode` (5 methods: `add_file`, `to_treemap`, `to_sunburst`, `to_bar_chart`), `Scanner` (3 methods: `scan`, `_check_cancel`, `_report`), `NTFSScanner` (4 methods: `_check_mft_access`, `scan`, `_scan_mft`, `_scan_walk`), `PosixScanner` (1 methods: `scan`)
  - **Exported Functions (1)**: `scan_sync`

- [ ] **113. [`src/cortex_unified/analyzers/advanced_shredder.py`](src/cortex_unified/analyzers/advanced_shredder.py)** (266 LOC)
  - **Purpose**: Advanced multi-pattern overwrite disk sanitization (DoD 5220.22-M style pass sequence).
  - **Classes (2)**: `ShredMethod`, `AdvancedShredder` (3 methods: `_generate_pass_data`, `shred_file`, `shred_directory`)

- [ ] **114. [`src/cortex_unified/analyzers/advanced_uninstaller.py`](src/cortex_unified/analyzers/advanced_uninstaller.py)** (1229 LOC)
  - **Purpose**: Advanced Uninstaller — Steam, Chocolatey, Winget, Store, portable, orphaned.
  - **Classes (4)**: `AppInfo` (1 methods: `to_dict`), `LeftoverScanResult` (1 methods: `to_dict`), `UninstallResult`, `AdvancedUninstaller` (11 methods: `enumerate_all`, `uninstall_batch`, `_uninstall_one`, `_split_command`)

- [ ] **115. [`src/cortex_unified/analyzers/audio_duplicate_finder.py`](src/cortex_unified/analyzers/audio_duplicate_finder.py)** (869 LOC)
  - **Purpose**: Audio duplicate detection via acoustic fingerprinting (Chromaprint-inspired).
  - **Classes (1)**: `AudioDuplicateFinder` (4 methods: `_should_exclude`, `_is_audio`, `find_audio_duplicates`, `get_stats`)
  - **Exported Functions (2)**: `compute_audio_fingerprint`, `audio_compare`

- [ ] **116. [`src/cortex_unified/analyzers/broken_link_detector.py`](src/cortex_unified/analyzers/broken_link_detector.py)** (1184 LOC)
  - **Purpose**: Enhanced broken link detector for Cortex Cleaner.
  - **Classes (7)**: `BrokenLink`, `BrokenSymlink`, `BrokenShortcut`, `BrokenRegistryRef`, `RepairResult`
  - **Exported Functions (1)**: `repair`

- [ ] **117. [`src/cortex_unified/analyzers/cache_cleaner.py`](src/cortex_unified/analyzers/cache_cleaner.py)** (456 LOC)
  - **Purpose**: Discovery of application caches and log files.
  - **Classes (1)**: `CacheCleaner` (11 methods: `_get_platform_cache_paths`, `get_custom_scan_roots`, `is_archive`, `_should_exclude_path`)

- [ ] **118. [`src/cortex_unified/analyzers/cloud_storage_analyzer.py`](src/cortex_unified/analyzers/cloud_storage_analyzer.py)** (1484 LOC)
  - **Purpose**: Cloud Storage Analyzer — rclone, S3, Azure, Google Drive, OneDrive, SharePoint.
  - **Classes (11)**: `CloudFileEntry` (1 methods: `to_dict`), `CloudScanStats`, `DuplicateGroup` (1 methods: `wasted_bytes`), `PricingCatalog` (8 methods: `_cache_file`, `_read_cache`, `_write_cache`, `_http_json`), `CloudProvider` (4 methods: `list_objects`, `region`, `estimate_cost`, `validate_config`)

- [ ] **119. [`src/cortex_unified/analyzers/content_defined_chunker.py`](src/cortex_unified/analyzers/content_defined_chunker.py)** (712 LOC)
  - **Purpose**: Content-Defined Chunking (FastCDC / VectorCDC) for deduplication acceleration.
  - **Classes (4)**: `Chunk` (1 methods: `to_dict`), `ChunkStats`, `ContentDefinedChunker` (3 methods: `_should_exclude`, `find_cdc_duplicates`, `get_stats`), `IdeaInvertedIndex` (2 methods: `insert`, `find_similar`)
  - **Exported Functions (5)**: `gear_chunk`, `file_chunks`, `jaccard`, `chunk_similarity`, `vector_cdc_chunk`

- [ ] **120. [`src/cortex_unified/analyzers/czkawka_tools.py`](src/cortex_unified/analyzers/czkawka_tools.py)** (878 LOC)
  - **Purpose**: Czkawka multi-tool suite — empty, broken, bad-ext, bad-names, exif, video-optimizer.
  - **Classes (12)**: `EmptyResult`, `EmptyFinder` (1 methods: `find`), `SymlinkResult`, `InvalidSymlinkFinder` (1 methods: `find`), `BrokenFileFinder` (2 methods: `_is_broken`, `find`)

- [ ] **121. [`src/cortex_unified/analyzers/deep_cleaner.py`](src/cortex_unified/analyzers/deep_cleaner.py)** (496 LOC)
  - **Purpose**: Cross-platform "deep clean" discovery over per-OS target tables.
  - **Classes (1)**: `DeepCleaner` (5 methods: `_find_orphaned_app_data`, `_get_scan_targets`, `find_junk`, `get_stats`)
  - **Exported Functions (1)**: `get_path_size_safe`

- [ ] **122. [`src/cortex_unified/analyzers/disk_analyzer.py`](src/cortex_unified/analyzers/disk_analyzer.py)** (282 LOC)
  - **Purpose**: Disk space analysis: volume usage, tree breakdown, per-extension stats.
  - **Classes (1)**: `DiskAnalyzer` (9 methods: `_should_exclude_path`, `analyze_disk_usage`, `analyze_directory_tree`, `_analyze_directory_recursive`)

- [ ] **123. [`src/cortex_unified/analyzers/docker_cleaner.py`](src/cortex_unified/analyzers/docker_cleaner.py)** (667 LOC)
  - **Purpose**: Scans a local Docker daemon for reclaimable resources (images, stopped
  - **Classes (6)**: `DockerImage`, `DockerContainer`, `DockerVolume`, `DockerNetwork`, `CleanupResult` (1 methods: `total_removed`)

- [ ] **124. [`src/cortex_unified/analyzers/duplicate_finder.py`](src/cortex_unified/analyzers/duplicate_finder.py)** (598 LOC)
  - **Purpose**: Hash-based duplicate file detection.
  - **Classes (1)**: `DuplicateFinder` (14 methods: `_should_exclude_path`, `_get_file_hash`, `_get_file_size`, `_find_files_by_size`)
  - **Exported Functions (1)**: `fastcdc_chunk`

- [ ] **125. [`src/cortex_unified/analyzers/duplicate_folder_finder.py`](src/cortex_unified/analyzers/duplicate_folder_finder.py)** (248 LOC)
  - **Purpose**: Content-identical folder detection.
  - **Classes (1)**: `DuplicateFolderFinder` (5 methods: `_should_exclude_path`, `_get_folder_hash`, `find_duplicate_folders`, `get_stats`)

- [ ] **126. [`src/cortex_unified/analyzers/file_shredder.py`](src/cortex_unified/analyzers/file_shredder.py)** (170 LOC)
  - **Purpose**: Overwrite-based file shredding.
  - **Classes (1)**: `FileShredder` (7 methods: `_generate_random_data`, `_generate_pattern_data`, `shred_file`, `shred_files`)

- [ ] **127. [`src/cortex_unified/analyzers/fuzzy_finder.py`](src/cortex_unified/analyzers/fuzzy_finder.py)** (600 LOC)
  - **Purpose**: Fuzzy (similarity, not exact) file hashing via CTPH / TLSH-style digests.
  - **Classes (1)**: `FuzzyDuplicateFinder` (4 methods: `_should_exclude`, `_eligible`, `find_fuzzy_duplicates`, `get_stats`)
  - **Exported Functions (3)**: `fuzzy_hash_bytes`, `fuzzy_hash_file`, `fuzzy_compare`

- [ ] **128. [`src/cortex_unified/analyzers/large_file_finder.py`](src/cortex_unified/analyzers/large_file_finder.py)** (223 LOC)
  - **Purpose**: Discovery of files above a configurable size threshold.
  - **Classes (1)**: `LargeFileFinder` (10 methods: `_should_exclude_path`, `_get_file_size`, `find_large_files`, `get_stats`)
  - **Exported Functions (1)**: `is_ai_model`

- [ ] **129. [`src/cortex_unified/analyzers/leftover_detector.py`](src/cortex_unified/analyzers/leftover_detector.py)** (1069 LOC)
  - **Purpose**: Advanced heuristics and leftover detection for Cortex Cleaner.
  - **Classes (6)**: `DetectedItem` (1 methods: `to_dict`), `OrphanedFolder`, `InstallerFile`, `RegistryOrphan`, `CleanupRecommendation`

- [ ] **130. [`src/cortex_unified/analyzers/near_duplicate_finder.py`](src/cortex_unified/analyzers/near_duplicate_finder.py)** (627 LOC)
  - **Purpose**: Near-duplicate detection via MinHash LSH + Bloom filtering.
  - **Classes (2)**: `BloomFilter` (3 methods: `_hashes`, `add`, `fpr`), `NearDuplicateFinder` (8 methods: `_should_exclude`, `_is_text`, `_minhash`, `_lsh_candidates`)

- [ ] **131. [`src/cortex_unified/analyzers/old_file_cleaner.py`](src/cortex_unified/analyzers/old_file_cleaner.py)** (167 LOC)
  - **Purpose**: Discovery of files untouched for a configurable number of days.
  - **Classes (1)**: `OldFileCleaner` (6 methods: `_should_exclude_path`, `find_old_files`, `get_stats`, `_format_bytes`)

- [ ] **132. [`src/cortex_unified/analyzers/package_manager_cleaner.py`](src/cortex_unified/analyzers/package_manager_cleaner.py)** (1611 LOC)
  - **Purpose**: Detects installed package managers and clears their regenerable caches.
  - **Classes (5)**: `Package`, `PackageManager`, `CleanupResult`, `HealthStatus`, `PackageManagerCleaner` (29 methods: `detect_package_managers`, `_get_package_manager_version`, `_get_cache_path`, `clean_pip_cache`)

- [ ] **133. [`src/cortex_unified/analyzers/perceptual_duplicate_finder.py`](src/cortex_unified/analyzers/perceptual_duplicate_finder.py)** (677 LOC)
  - **Purpose**: Perceptual image/photo duplicate detection via pHash / aHash / dHash.
  - **Classes (1)**: `PerceptualDuplicateFinder` (5 methods: `_should_exclude`, `_is_image`, `find_perceptual_duplicates`, `_window_size`)
  - **Exported Functions (6)**: `average_hash`, `difference_hash`, `perceptual_hash`, `wavelet_hash`, `compute_hash`, `hamming_distance`

- [ ] **134. [`src/cortex_unified/analyzers/portable_manager.py`](src/cortex_unified/analyzers/portable_manager.py)** (472 LOC)
  - **Purpose**: Portable Manager — PortableApps.com / LiberKey catalog, USB toolkit.
  - **Classes (2)**: `PortableApp` (1 methods: `to_dict`), `PortableManager` (5 methods: `scan_portable_roots`, `check_updates`, `update_app`, `export_toolkit`)

- [ ] **135. [`src/cortex_unified/analyzers/privacy_cleaner.py`](src/cortex_unified/analyzers/privacy_cleaner.py)** (372 LOC)
  - **Purpose**: Detects and removes browser traces (cache, cookies, history, sessions)
  - **Classes (1)**: `PrivacyCleaner` (13 methods: `scan_browsers`, `scan_system_traces`, `clean_browser`, `clean_system_traces`)

- [ ] **136. [`src/cortex_unified/analyzers/project_cache_scanner.py`](src/cortex_unified/analyzers/project_cache_scanner.py)** (502 LOC)
  - **Purpose**: Auto-discovery of project cache folders across fixed drives and user directories.
  - **Classes (1)**: `ProjectCacheScanner` (4 methods: `scan_fixed_drives`, `_scan_root`, `_get_dir_size`, `_format_bytes`)

- [ ] **137. [`src/cortex_unified/analyzers/registry_cleaner_ai.py`](src/cortex_unified/analyzers/registry_cleaner_ai.py)** (1506 LOC)
  - **Purpose**: AI/ML-Enhanced Registry Cleaner — learned safety, contextual risk scoring.
  - **Classes (5)**: `RegistryIssue` (1 methods: `to_dict`), `ScanResult` (1 methods: `to_json`), `CleanResult`, `_MLModel` (2 methods: `predict`, `_heuristic_score`), `AIRegistryCleaner` (18 methods: `_run_ps`, `_key_exists`, `_get_parent`, `_values_map`)

- [ ] **138. [`src/cortex_unified/analyzers/residual_cleaner.py`](src/cortex_unified/analyzers/residual_cleaner.py)** (183 LOC)
  - **Purpose**: Residual Cleaner — finds leftover folders after application uninstall.
  - **Classes (1)**: `ResidualCleaner` (4 methods: `scan_for_app`, `_build_search_tokens`, `_matches_tokens`, `_get_size`)

- [ ] **139. [`src/cortex_unified/analyzers/residual_hunter.py`](src/cortex_unified/analyzers/residual_hunter.py)** (5 LOC)
  - **Purpose**: Backward-compatibility alias for ResidualCleaner.

- [ ] **140. [`src/cortex_unified/analyzers/video_duplicate_finder.py`](src/cortex_unified/analyzers/video_duplicate_finder.py)** (763 LOC)
  - **Purpose**: Video near-duplicate detection via keyframe perceptual hashing + temporal consistency.
  - **Classes (1)**: `VideoDuplicateFinder` (4 methods: `_should_exclude`, `_is_video`, `find_video_duplicates`, `get_stats`)
  - **Exported Functions (2)**: `compute_video_fingerprint`, `video_compare`

## Nexus Native Explorer Engine

- [ ] **141. [`src/NexusExplorer/native/__init__.py`](src/NexusExplorer/native/__init__.py)** (12 LOC)
  - **Purpose**: NexusExplorer native Qt package.

- [ ] **142. [`src/NexusExplorer/native/binary_differ.py`](src/NexusExplorer/native/binary_differ.py)** (191 LOC)
  - **Purpose**: Nexus Explorer — Binary & Hex File Differ Engine.
  - **Classes (3)**: `HexDiffChunk`, `BinaryDiffReport`, `BinaryDiffer` (2 methods: `_to_ascii`, `compare_binary_files`)

- [ ] **143. [`src/NexusExplorer/native/file_signature_sniffer.py`](src/NexusExplorer/native/file_signature_sniffer.py)** (222 LOC)
  - **Purpose**: File type detection via magic bytes: ~38 signatures (JPEG, PNG, PDF, ZIP, RAR, 7z, etc.).
  - **Classes (3)**: `FileSignature`, `SniffResult`, `FileSignatureSniffer` (2 methods: `sniff_file`, `scan_directory`)

- [ ] **144. [`src/NexusExplorer/native/image_optimizer.py`](src/NexusExplorer/native/image_optimizer.py)** (199 LOC)
  - **Purpose**: Nexus Explorer — High-Throughput Batch Image Optimizer & WebP Transcoder.
  - **Classes (3)**: `ImageOptimizeResult`, `BatchOptimizeSummary`, `ImageOptimizer` (2 methods: `optimize_image`, `optimize_batch`)

- [ ] **145. [`src/NexusExplorer/native/nexus_ads_manager.py`](src/NexusExplorer/native/nexus_ads_manager.py)** (224 LOC)
  - **Purpose**: Nexus Explorer — NTFS Alternate Data Streams (ADS) & Zone.Identifier Manager.
  - **Classes (2)**: `AlternateDataStream`, `AlternateDataStreamsManager` (5 methods: `list_streams`, `read_stream_text`, `delete_stream`, `unblock_file`)

- [ ] **146. [`src/NexusExplorer/native/nexus_archive.py`](src/NexusExplorer/native/nexus_archive.py)** (875 LOC)
  - **Purpose**: Archive support via native 7-Zip CLI — multithreaded extraction.
  - **Classes (7)**: `ArchiveSecurityError`, `ArchiveType`, `ArchiveEntry`, `ArchiveInfo`, `SevenZipCLIReader` (6 methods: `list_entries`, `extract_entry`, `extract_all`, `read_entry`)
  - **Exported Functions (5)**: `is_7z_available`, `validate_extract_path`, `detect_archive_type`, `is_archive`, `open_archive`

- [ ] **147. [`src/NexusExplorer/native/nexus_archive_manager.py`](src/NexusExplorer/native/nexus_archive_manager.py)** (354 LOC)
  - **Purpose**: Archive creation: STORED and DEFLATED only; no BZIP2/LZMA, no password support.
  - **Classes (5)**: `ArchiveFormat`, `CompressionLevel`, `ArchiveEntryInfo`, `ArchiveOperationResult`, `ArchiveManager` (5 methods: `detect_format`, `list_entries`, `test_archive`, `extract_archive`)

- [ ] **148. [`src/NexusExplorer/native/nexus_batch_renamer.py`](src/NexusExplorer/native/nexus_batch_renamer.py)** (441 LOC)
  - **Purpose**: Nexus Explorer — Enterprise Batch Multi-Rename Engine.
  - **Classes (4)**: `CaseTransformation`, `RenamePlanItem`, `RenameTransaction`, `BatchRenamer` (6 methods: `_apply_case`, `_extract_exif_metadata`, `_extract_id3_metadata`, `preview_rename`)

- [ ] **149. [`src/NexusExplorer/native/nexus_cloud.py`](src/NexusExplorer/native/nexus_cloud.py)** (1382 LOC)
  - **Purpose**: Cloud storage integration module.
  - **Classes (10)**: `CloudProviderType`, `SyncStatus`, `CloudFile`, `CloudAccount`, `CloudProvider` (11 methods: `provider_type`, `authenticate`, `is_authenticated`, `disconnect`)
  - **Exported Functions (1)**: `retry_on_rate_limit`

- [ ] **150. [`src/NexusExplorer/native/nexus_content_search.py`](src/NexusExplorer/native/nexus_content_search.py)** (495 LOC)
  - **Purpose**: Content search engine for searching inside file contents.
  - **Classes (4)**: `ContentMatch`, `ContentSearchResult`, `_ContentSearchWorker` (2 methods: `run`, `_process_batch`), `ContentSearchEngine` (3 methods: `search`, `stop`, `is_searching`)
  - **Exported Functions (2)**: `is_searchable`, `search_file_content`

- [ ] **151. [`src/NexusExplorer/native/nexus_core.py`](src/NexusExplorer/native/nexus_core.py)** (1640 LOC)
  - **Purpose**: Nexus native core: engine bridge, native icons/thumbnails, table model.
  - **Classes (9)**: `_CallMarshal`, `_FfiJob` (1 methods: `run`), `Engine` (18 methods: `shutdown`, `list_dir`, `search`, `_python_list_dir`), `_SHFILEINFO`, `_ICONINFO`
  - **Exported Functions (7)**: `find_cli`, `human`, `fmt_ms`, `marshal_call`, `create_nested_folder`, `create_nested_file`, `scaffold_hierarchy`

- [ ] **152. [`src/NexusExplorer/native/nexus_dir_diff.py`](src/NexusExplorer/native/nexus_dir_diff.py)** (377 LOC)
  - **Purpose**: Nexus Explorer — Directory Comparison & Folder Synchronization Engine.
  - **Classes (5)**: `DiffStatus`, `SyncMode`, `DiffEntry`, `SyncStats`, `DirectoryDiffEngine` (3 methods: `_quick_hash`, `compare_directories`, `execute_sync`)

- [ ] **153. [`src/NexusExplorer/native/nexus_explorer.py`](src/NexusExplorer/native/nexus_explorer.py)** (9531 LOC)
  - **Purpose**: NexusExplorerWidget — premium native Qt6 file explorer.
  - **Classes (39)**: `DebugOverlay` (3 methods: `log_event`, `tick_fps`, `paintEvent`), `CrumbBar` (7 methods: `setPath`, `_segments`, `mouseMoveEvent`, `leaveEvent`), `QuickLookPopup` (2 methods: `show_file`, `_show_at`), `BulkRenameDialog` (4 methods: `_on_mode_changed`, `_rename_for_mode`, `_update_preview`, `_apply`), `SearchDialog` (5 methods: `_start_search`, `_cancel_search`, `_on_search_done`, `_open_result`)

- [ ] **154. [`src/NexusExplorer/native/nexus_fast_copier.py`](src/NexusExplorer/native/nexus_fast_copier.py)** (305 LOC)
  - **Purpose**: Fast file copier: fixed 512KB buffer, buffered Python I/O, sequential single-threaded copy.
  - **Classes (4)**: `CopyMode`, `CopyItemProgress`, `CopySummary`, `FastCopier` (2 methods: `_copy_single_file`, `copy_batch`)

- [ ] **155. [`src/NexusExplorer/native/nexus_ffi.py`](src/NexusExplorer/native/nexus_ffi.py)** (686 LOC)
  - **Purpose**: ctypes bridge to the NexusExplorer Rust engine (nexus_engine.dll).
  - **Classes (4)**: `_FileEntry`, `_DriveInfo`, `_SearchOptions`, `NexusFfi` (23 methods: `_bind`, `dll_path`, `version`, `close`)
  - **Exported Functions (1)**: `find_dll`

- [ ] **156. [`src/NexusExplorer/native/nexus_file_splitter.py`](src/NexusExplorer/native/nexus_file_splitter.py)** (302 LOC)
  - **Purpose**: Split/merge files with a single JSON manifest (<name>.split.json only; no .crc files).
  - **Classes (5)**: `SplitPreset`, `SplitManifest`, `SplitResult`, `JoinResult`, `FileSplitterJoiner` (2 methods: `split_file`, `join_files`)

- [ ] **157. [`src/NexusExplorer/native/nexus_folder_tree.py`](src/NexusExplorer/native/nexus_folder_tree.py)** (342 LOC)
  - **Purpose**: Folder tree widget for hierarchical filesystem navigation.
  - **Classes (2)**: `FolderTreeModel` (6 methods: `populate_drives`, `_get_drives`, `_setup_children`, `hasChildren`), `FolderTreeWidget` (4 methods: `_on_clicked`, `select_path`, `refresh`, `cleanup`)

- [ ] **158. [`src/NexusExplorer/native/nexus_hash_tool.py`](src/NexusExplorer/native/nexus_hash_tool.py)** (483 LOC)
  - **Purpose**: Nexus Explorer — High-Performance File Checksum & Integrity Utility.
  - **Classes (4)**: `HashAlgorithm`, `HashResult`, `VerifyItem`, `HashTool` (4 methods: `compute_hash`, `compute_all_hashes`, `create_manifest`, `verify_manifest`)

- [ ] **159. [`src/NexusExplorer/native/nexus_icons.py`](src/NexusExplorer/native/nexus_icons.py)** (1747 LOC)
  - **Purpose**: Icon system using Material Design SVGs loaded from disk (MATERIAL_DIR) with inline Fluent fallback.
  - **Classes (1)**: `_LRUCache` (2 methods: `get`, `set`)
  - **Exported Functions (5)**: `icon`, `icon_for_ext`, `action_icon`, `folder_icon`, `sidebar_icon`

- [ ] **160. [`src/NexusExplorer/native/nexus_indexer.py`](src/NexusExplorer/native/nexus_indexer.py)** (853 LOC)
  - **Purpose**: Production-grade file indexer for instant filename search.
  - **Classes (7)**: `IndexedEntry`, `IndexStats`, `_PrefixIndex` (5 methods: `add`, `remove`, `_ensure_sorted`, `prefix_search`), `FileIndex` (11 methods: `stats`, `add`, `remove`, `search_prefix`), `_IndexWorker` (3 methods: `run`, `_walk`, `_flush_batch`)

- [ ] **161. [`src/NexusExplorer/native/nexus_links_manager.py`](src/NexusExplorer/native/nexus_links_manager.py)** (372 LOC)
  - **Purpose**: Nexus Explorer — NTFS Links, Junctions & Reparse Points Manager.
  - **Classes (4)**: `LinkType`, `LinkItem`, `LinkOperationResult`, `LinksManager` (7 methods: `is_junction`, `get_link_info`, `scan_links_in_directory`, `create_junction`)

- [ ] **162. [`src/NexusExplorer/native/nexus_native_app.py`](src/NexusExplorer/native/nexus_native_app.py)** (75 LOC)
  - **Purpose**: Standalone launcher for the native Nexus explorer (Qt6).
  - **Exported Functions (1)**: `main`

- [ ] **163. [`src/NexusExplorer/native/nexus_network.py`](src/NexusExplorer/native/nexus_network.py)** (1027 LOC)
  - **Purpose**: Network file systems: SMB via smbclient, FTP via ftplib, SFTP via paramiko, WebDAV via webdav3.
  - **Classes (10)**: `NetworkProtocol`, `NetworkFile`, `NetworkConnection`, `NetworkFS` (10 methods: `protocol`, `connect`, `disconnect`, `is_connected`), `SMBProvider` (10 methods: `protocol`, `connect`, `disconnect`, `is_connected`)
  - **Exported Functions (2)**: `store_credential`, `get_credential`

- [ ] **164. [`src/NexusExplorer/native/nexus_plugins.py`](src/NexusExplorer/native/nexus_plugins.py)** (978 LOC)
  - **Purpose**: Production-grade plugin system for NexusExplorer.
  - **Classes (12)**: `PluginManifest` (1 methods: `from_dict`), `PluginState`, `PluginLifecycle` (2 methods: `transition_to`, `is_active`), `ScopedConfig` (3 methods: `get`, `set`, `all`), `EventBridge` (3 methods: `emit`, `subscribe`, `unsubscribe`)

- [ ] **165. [`src/NexusExplorer/native/nexus_timestamp_touch.py`](src/NexusExplorer/native/nexus_timestamp_touch.py)** (324 LOC)
  - **Purpose**: Nexus Explorer — Forensic File Timestamp & Attribute Modifier (MACB Touch).
  - **Classes (4)**: `FileAttributeFlags`, `TimestampInfo`, `TimestampUpdateResult`, `TimestampTouchEngine` (5 methods: `get_file_metadata`, `set_timestamps`, `_set_windows_timestamps`, `set_attributes`)

- [ ] **166. [`src/NexusExplorer/native/nexus_transfer_monitor.py`](src/NexusExplorer/native/nexus_transfer_monitor.py)** (372 LOC)
  - **Purpose**: Transfer Monitor — non-modal window showing the live transfer queue.
  - **Classes (2)**: `_JobRow` (4 methods: `_describe`, `_refresh`, `_toggle_pause`, `_cancel`), `TransferMonitorDialog` (8 methods: `_on_job_added`, `_on_progress`, `_tick`, `_update_summary`)

- [ ] **167. [`src/NexusExplorer/native/nexus_transfer_queue.py`](src/NexusExplorer/native/nexus_transfer_queue.py)** (806 LOC)
  - **Purpose**: Transfer queue for serialized file operations.
  - **Classes (3)**: `JobState`, `TransferJob`, `TransferQueue` (20 methods: `max_concurrent`, `max_concurrent`, `is_busy`, `stop`)
  - **Exported Functions (2)**: `human_bytes`, `fmt_eta`

- [ ] **168. [`src/NexusExplorer/native/nexus_undo.py`](src/NexusExplorer/native/nexus_undo.py)** (450 LOC)
  - **Purpose**: Undo/redo stack for file operations.
  - **Classes (10)**: `OpKind`, `UndoEntry` (2 methods: `undo`, `redo`), `RenameEntry` (2 methods: `undo`, `redo`), `MoveEntry` (2 methods: `undo`, `redo`), `CopyEntry` (2 methods: `undo`, `redo`)

- [ ] **169. [`src/NexusExplorer/native/nexus_unlocker.py`](src/NexusExplorer/native/nexus_unlocker.py)** (303 LOC)
  - **Purpose**: Nexus Explorer — Process Unlocker & File Handle Inspector.
  - **Classes (2)**: `LockingProcessInfo`, `FileUnlocker` (4 methods: `get_locking_processes`, `_query_restart_manager`, `_query_psutil_handles`, `unlock_and_terminate`)

- [ ] **170. [`src/NexusExplorer/native/par2_recovery.py`](src/NexusExplorer/native/par2_recovery.py)** (180 LOC)
  - **Purpose**: Nexus Explorer — PAR2 (Parchive) Parity Checksum & Packet Integrity Engine.
  - **Classes (4)**: `Par2FileInfo`, `Par2PacketInfo`, `Par2ValidationReport`, `Par2RecoveryEngine` (1 methods: `inspect_par2_file`)

- [ ] **171. [`src/NexusExplorer/native/usn_journal_scanner.py`](src/NexusExplorer/native/usn_journal_scanner.py)** (155 LOC)
  - **Purpose**: USN Journal status query only; no change enumeration or sub-millisecond tracking.
  - **Classes (3)**: `UsnJournalStatus`, `USN_JOURNAL_DATA_V0`, `UsnJournalScanner` (1 methods: `query_volume_journal`)

## Core Framework & Safety PathGuards

- [ ] **172. [`src/cortex_unified/core/__init__.py`](src/cortex_unified/core/__init__.py)** (1 LOC)
  - **Purpose**: Cortex Workstation Core Engine and Orchestration Framework.

- [ ] **173. [`src/cortex_unified/core/background_agent.py`](src/cortex_unified/core/background_agent.py)** (112 LOC)
  - **Purpose**: Background Agent — lightweight real-time system monitor.
  - **Classes (1)**: `BackgroundAgent` (2 methods: `start_monitoring`, `stop`)

- [ ] **174. [`src/cortex_unified/core/config.py`](src/cortex_unified/core/config.py)** (276 LOC)
  - **Purpose**: Legacy YAML configuration management for Cortex Cleaner.
  - **Classes (1)**: `Config` (13 methods: `_get_default_config_path`, `_load_config`, `_defaults`, `exclude_patterns`)

- [ ] **175. [`src/cortex_unified/core/config_v2.py`](src/cortex_unified/core/config_v2.py)** (634 LOC)
  - **Purpose**: Pydantic-based configuration management for Cortex Cleaner.
  - **Classes (8)**: `_YamlConfigSource` (1 methods: `get_field_value`), `ScanConfig`, `PerformanceConfig` (1 methods: `clamp_threads`), `SecurityConfig`, `LoggingConfig`
  - **Exported Functions (1)**: `create_default_config`

- [ ] **176. [`src/cortex_unified/core/database.py`](src/cortex_unified/core/database.py)** (809 LOC)
  - **Purpose**: SQLite persistence layer for Cortex Cleaner.
  - **Classes (7)**: `Base`, `ScanRun` (2 methods: `duration_seconds`, `to_dict`), `DeletedItem` (1 methods: `to_dict`), `ScheduledJob`, `SystemMetric`
  - **Exported Functions (2)**: `get_database`, `db_session`

- [ ] **177. [`src/cortex_unified/core/deleter.py`](src/cortex_unified/core/deleter.py)** (234 LOC)
  - **Purpose**: File and directory deletion functionality for Cortex Cleaner.
  - **Classes (1)**: `Deleter` (4 methods: `_delete_file`, `_delete_directory`, `delete`, `generate_manifest`)

- [ ] **178. [`src/cortex_unified/core/logging_setup.py`](src/cortex_unified/core/logging_setup.py)** (440 LOC)
  - **Purpose**: Structured logging configuration for Cortex Cleaner.
  - **Classes (1)**: `LogContext`
  - **Exported Functions (12)**: `add_correlation_id`, `add_app_context`, `censor_sensitive_data`, `configure_logging`, `get_logger`, `set_correlation_id`, `clear_correlation_id`, `log_scan_start`

- [ ] **179. [`src/cortex_unified/core/proc.py`](src/cortex_unified/core/proc.py)** (310 LOC)
  - **Purpose**: Cancellable, tree-safe subprocess execution.
  - **Classes (1)**: `ProcessCancelled`
  - **Exported Functions (3)**: `is_protected_process`, `run`, `kill_process_tree`

- [ ] **180. [`src/cortex_unified/core/scanner.py`](src/cortex_unified/core/scanner.py)** (483 LOC)
  - **Purpose**: Discovery of empty files and directories under a configured root.
  - **Classes (1)**: `Scanner` (14 methods: `_should_exclude_path`, `_is_file_empty`, `_is_file_old_enough`, `_scan_file`)

- [ ] **181. [`src/cortex_unified/core/security.py`](src/cortex_unified/core/security.py)** (345 LOC)
  - **Purpose**: Security utilities for Cortex Cleaner.
  - **Exported Functions (6)**: `is_safe_path`, `is_system_file`, `validate_paths`, `is_path_writable`, `get_safe_temp_dir`, `check_deletion_safety`

- [ ] **182. [`src/cortex_unified/core/smart_scanner.py`](src/cortex_unified/core/smart_scanner.py)** (315 LOC)
  - **Purpose**: Smart Scanner — orchestrates parallel system analysis and produces a Health Score.
  - **Classes (2)**: `SmartScanReport` (2 methods: `total_cleanable_mb`, `calculate_score`), `SmartScannerWorker` (6 methods: `run`, `stop`, `_scan_temp_dirs`, `_scan_browser_caches`)

- [ ] **183. [`src/cortex_unified/core/smart_suggest.py`](src/cortex_unified/core/smart_suggest.py)** (313 LOC)
  - **Purpose**: Smart Suggestions - a tiny, fully-offline, on-device learning engine.
  - **Classes (1)**: `SmartSuggester` (10 methods: `score`, `recommend`, `rank`, `observe`)
  - **Exported Functions (1)**: `featurize`

- [ ] **184. [`src/cortex_unified/core/temp_cleaner.py`](src/cortex_unified/core/temp_cleaner.py)** (441 LOC)
  - **Purpose**: Discovery and safe removal of stale files from operating-system temp locations.
  - **Classes (2)**: `TempFinding`, `TempCleaner` (8 methods: `LOCATIONS`, `_discover_locations`, `_is_excluded`, `_is_old_enough`)

- [ ] **185. [`src/cortex_unified/core/utils.py`](src/cortex_unified/core/utils.py)** (889 LOC)
  - **Purpose**: Shared utilities: logging setup, formatting, path helpers, error types.
  - **Classes (8)**: `DeepCleanerError`, `DockerError`, `VisualizationError`, `HeuristicsError`, `PackageManagerError`
  - **Exported Functions (23)**: `get_system_excludes`, `is_system_directory`, `setup_logging`, `get_component_logger`, `log_operation_start`, `log_operation_end`, `log_performance_metrics`, `generate_manifest_filename`

## Processing & Algorithmic Engines

- [ ] **186. [`src/cortex_unified/engine/__init__.py`](src/cortex_unified/engine/__init__.py)** (74 LOC)
  - **Purpose**: Cortex Cleaner high-performance engine.

- [ ] **187. [`src/cortex_unified/engine/__main__.py`](src/cortex_unified/engine/__main__.py)** (8 LOC)
  - **Purpose**: Engine CLI module execution entrypoint: python -m cortex_unified.engine.

- [ ] **188. [`src/cortex_unified/engine/categories.py`](src/cortex_unified/engine/categories.py)** (976 LOC)
  - **Purpose**: Data-driven, risk-annotated registry of cleanable locations.
  - **Classes (2)**: `RiskLevel` (1 methods: `rank`), `CleanupCategory` (1 methods: `existing_paths`)
  - **Exported Functions (2)**: `default_categories`, `categories_by_id`

- [ ] **189. [`src/cortex_unified/engine/cli.py`](src/cortex_unified/engine/cli.py)** (721 LOC)
  - **Purpose**: Modern, safe CLI for the Cortex engine.

- [ ] **190. [`src/cortex_unified/engine/fastwalk.py`](src/cortex_unified/engine/fastwalk.py)** (402 LOC)
  - **Purpose**: High-performance filesystem traversal built on ``os.scandir``.
  - **Classes (2)**: `WalkOptions`, `FastWalker` (8 methods: `cancel`, `reset`, `_excluded_dir`, `_matches_patterns`)

- [ ] **191. [`src/cortex_unified/engine/guard.py`](src/cortex_unified/engine/guard.py)** (204 LOC)
  - **Purpose**: Path safety guard for destructive operations.
  - **Classes (2)**: `GuardVerdict`, `PathGuard` (3 methods: `check`, `is_writable`, `_is_within`)

- [ ] **192. [`src/cortex_unified/engine/hashing.py`](src/cortex_unified/engine/hashing.py)** (194 LOC)
  - **Purpose**: Fast content hashing and duplicate detection.
  - **Classes (1)**: `DuplicateFinderEngine` (3 methods: `find`, `_group_by_hash`, `wasted_bytes`)
  - **Exported Functions (1)**: `hash_file`

- [ ] **193. [`src/cortex_unified/engine/models.py`](src/cortex_unified/engine/models.py)** (274 LOC)
  - **Purpose**: Immutable-ish data models shared across the engine.
  - **Classes (6)**: `StorageKind` (1 methods: `overwrite_effective`), `DeletionMethod`, `DeletionOutcome`, `FileEntry` (6 methods: `age_days`, `reclaimable_size`, `is_cloud_placeholder`, `is_junction`), `ScanResult` (2 methods: `error_count`, `to_dict`)

- [ ] **194. [`src/cortex_unified/engine/secure_delete.py`](src/cortex_unified/engine/secure_delete.py)** (706 LOC)
  - **Purpose**: Storage-aware deletion with honest guarantees.
  - **Classes (2)**: `OverwriteNotEffective`, `SecureDeleter` (15 methods: `delete`, `delete_many`, `_fast_safe`, `_delete_batch`)
  - **Exported Functions (1)**: `recycle_path`

- [ ] **195. [`src/cortex_unified/engine/service.py`](src/cortex_unified/engine/service.py)** (807 LOC)
  - **Purpose**: High-level cleaner service - the single orchestration entry point.
  - **Classes (3)**: `CategoryScan` (3 methods: `file_count`, `breakdown`, `to_dict`), `CleanupReport` (6 methods: `total_reclaimable_bytes`, `total_files`, `cloud_skipped`, `cloud_skipped_bytes`), `CleanerService` (8 methods: `scan_categories`, `scan_custom_roots`, `clean_categories`, `find_duplicates`)

- [ ] **196. [`src/cortex_unified/engine/storage.py`](src/cortex_unified/engine/storage.py)** (296 LOC)
  - **Purpose**: Cross-platform storage-medium detection.
  - **Classes (2)**: `StorageInfo` (1 methods: `overwrite_effective`), `StorageProbe` (7 methods: `probe`, `_mount_key`, `_probe_uncached`, `_probe_windows`)
  - **Exported Functions (1)**: `detect_storage`

- [ ] **197. [`src/cortex_unified/engine/winattrs.py`](src/cortex_unified/engine/winattrs.py)** (195 LOC)
  - **Purpose**: Windows file-attribute and reparse-point classification.
  - **Exported Functions (10)**: `attrs_of`, `reparse_tag_of`, `is_reparse_point`, `is_cloud_tag`, `is_dehydrated`, `is_cloud`, `is_junction`, `size_may_be_misleading`

## Unified Explorer & File Systems

- [ ] **198. [`src/cortex_unified/explorer/__init__.py`](src/cortex_unified/explorer/__init__.py)** (75 LOC)
  - **Purpose**: Cortex Cleaner Explorer Subsystem.

- [ ] **199. [`src/cortex_unified/explorer/archive.py`](src/cortex_unified/explorer/archive.py)** (19 LOC)
  - **Purpose**: Archive inspector and extraction module.

- [ ] **200. [`src/cortex_unified/explorer/cloud.py`](src/cortex_unified/explorer/cloud.py)** (56 LOC)
  - **Purpose**: Cloud integration module.

- [ ] **201. [`src/cortex_unified/explorer/content_search.py`](src/cortex_unified/explorer/content_search.py)** (21 LOC)
  - **Purpose**: File content search and ripgrep integration.

- [ ] **202. [`src/cortex_unified/explorer/core.py`](src/cortex_unified/explorer/core.py)** (47 LOC)
  - **Purpose**: Native core file engine and table model.

- [ ] **203. [`src/cortex_unified/explorer/ffi.py`](src/cortex_unified/explorer/ffi.py)** (21 LOC)
  - **Purpose**: Rust FFI bridge for high-performance filesystem operations.

- [ ] **204. [`src/cortex_unified/explorer/folder_tree.py`](src/cortex_unified/explorer/folder_tree.py)** (21 LOC)
  - **Purpose**: Filesystem tree view navigation widget.

- [ ] **205. [`src/cortex_unified/explorer/icons.py`](src/cortex_unified/explorer/icons.py)** (40 LOC)
  - **Purpose**: Vector icon pipeline for Explorer subsystem.

- [ ] **206. [`src/cortex_unified/explorer/indexer.py`](src/cortex_unified/explorer/indexer.py)** (21 LOC)
  - **Purpose**: Fast background filesystem indexing engine.

- [ ] **207. [`src/cortex_unified/explorer/network.py`](src/cortex_unified/explorer/network.py)** (47 LOC)
  - **Purpose**: Network filesystem and remote share explorer.

- [ ] **208. [`src/cortex_unified/explorer/plugins.py`](src/cortex_unified/explorer/plugins.py)** (21 LOC)
  - **Purpose**: Plugin architecture and extension manager.

- [ ] **209. [`src/cortex_unified/explorer/transfers.py`](src/cortex_unified/explorer/transfers.py)** (32 LOC)
  - **Purpose**: File transfer queue and progress monitoring module.

- [ ] **210. [`src/cortex_unified/explorer/undo.py`](src/cortex_unified/explorer/undo.py)** (34 LOC)
  - **Purpose**: Undo and redo file operation history stack.

- [ ] **211. [`src/cortex_unified/explorer/widget.py`](src/cortex_unified/explorer/widget.py)** (56 LOC)
  - **Purpose**: Fluent Qt6 File Explorer Widget module.

## Performance & Hardware Acceleration

- [ ] **212. [`src/cortex_unified/performance/__init__.py`](src/cortex_unified/performance/__init__.py)** (18 LOC)
  - **Purpose**: Performance optimization and monitoring module for Cortex Cleaner.

- [ ] **213. [`src/cortex_unified/performance/multi_drive_scanner.py`](src/cortex_unified/performance/multi_drive_scanner.py)** (1599 LOC)
  - **Purpose**: Parallel scanning across multiple drives, volumes, and user profiles.
  - **Classes (8)**: `DriveInfo` (2 methods: `used_size`, `usage_percent`), `NetworkDrive`, `UserProfile`, `ScanProgress` (1 methods: `overall_progress`), `AggregatedResult`

- [ ] **214. [`src/cortex_unified/performance/optimization.py`](src/cortex_unified/performance/optimization.py)** (453 LOC)
  - **Purpose**: Performance optimization utilities for Cortex Cleaner operations.
  - **Classes (2)**: `OptimizationSettings`, `PerformanceOptimizer` (14 methods: `start_optimization`, `stop_optimization`, `_optimize_garbage_collection`, `_start_memory_monitoring`)

- [ ] **215. [`src/cortex_unified/performance/profiler.py`](src/cortex_unified/performance/profiler.py)** (168 LOC)
  - **Purpose**: Performance profiling and monitoring for Cortex Cleaner operations.
  - **Classes (2)**: `ProfileReport` (1 methods: `to_dict`), `OperationProfiler` (7 methods: `profile_operation`, `start_operation`, `end_operation`, `get_reports`)

- [ ] **216. [`src/cortex_unified/performance/resource_monitor.py`](src/cortex_unified/performance/resource_monitor.py)** (377 LOC)
  - **Purpose**: Resource monitoring and management for Cortex Cleaner operations.
  - **Classes (2)**: `SystemMetrics`, `ResourceMonitor` (13 methods: `start_monitoring`, `stop_monitoring`, `add_callback`, `remove_callback`)

- [ ] **217. [`src/cortex_unified/performance/resource_throttler.py`](src/cortex_unified/performance/resource_throttler.py)** (353 LOC)
  - **Purpose**: Resource throttling and system performance management.
  - **Classes (2)**: `SystemLoad` (1 methods: `is_high_load`), `ResourceThrottler` (11 methods: `set_process_priority`, `set_eco_qos`, `get_system_load`, `throttle_if_needed`)

- [ ] **218. [`src/cortex_unified/performance/scan_manager.py`](src/cortex_unified/performance/scan_manager.py)** (376 LOC)
  - **Purpose**: Scan management with checkpoint and resume functionality.
  - **Classes (3)**: `ScanCheckpoint` (2 methods: `to_dict`, `from_dict`), `ScanProgress`, `ScanManager` (13 methods: `create_checkpoint`, `load_checkpoint`, `pause_scan`, `resume_scan`)

- [ ] **219. [`src/cortex_unified/performance/settings_integration.py`](src/cortex_unified/performance/settings_integration.py)** (246 LOC)
  - **Purpose**: Settings integration for performance optimization and throttling logic.
  - **Classes (2)**: `PerformanceSettingsWidget` (3 methods: `setup_ui`, `load_settings`, `save_settings`), `PerformanceManager` (3 methods: `load_saved_settings`, `apply_properties`, `create_settings_widget`)
  - **Exported Functions (1)**: `get_performance_manager`

## Licensing, Reports, Scheduler & i18n

- [ ] **220. [`src/cortex_unified/licensing/__init__.py`](src/cortex_unified/licensing/__init__.py)** (42 LOC)
  - **Purpose**: Offline-first licensing and entitlement system.

- [ ] **221. [`src/cortex_unified/licensing/fingerprint.py`](src/cortex_unified/licensing/fingerprint.py)** (163 LOC)
  - **Purpose**: Stable, privacy-preserving machine fingerprint for license binding.
  - **Exported Functions (4)**: `collect_identifiers`, `compute_fingerprint`, `get_fingerprint`, `reset_cache`

- [ ] **222. [`src/cortex_unified/licensing/gating.py`](src/cortex_unified/licensing/gating.py)** (167 LOC)
  - **Purpose**: Entitlement checks: the single gateway every gated feature goes through.
  - **Classes (1)**: `EntitlementError`
  - **Exported Functions (6)**: `current_tier`, `effective_features`, `allowed`, `require`, `gate`, `reset_cache`

- [ ] **223. [`src/cortex_unified/licensing/license_manager.py`](src/cortex_unified/licensing/license_manager.py)** (492 LOC)
  - **Purpose**: Offline license activation, validation and trial management.
  - **Classes (3)**: `LicensePayload` (4 methods: `canonical`, `sign`, `verify_signature`, `from_dict`), `LicenseState` (4 methods: `features`, `allows`, `to_dict`, `_masked_key`), `LicenseManager` (10 methods: `_file_signature`, `invalidate`, `_save`, `_load_document`)
  - **Exported Functions (3)**: `license_path`, `get_license_manager`, `reset_singleton`

- [ ] **224. [`src/cortex_unified/licensing/tiers.py`](src/cortex_unified/licensing/tiers.py)** (132 LOC)
  - **Purpose**: Tier and feature definitions for Cortex Cleaner.
  - **Classes (2)**: `Tier` (3 methods: `rank`, `includes`, `parse`), `Feature`
  - **Exported Functions (1)**: `features_for_tier`

- [ ] **225. [`src/cortex_unified/reports/__init__.py`](src/cortex_unified/reports/__init__.py)** (15 LOC)
  - **Purpose**: Reports and restore module for Cortex Cleaner.

- [ ] **226. [`src/cortex_unified/reports/reports.py`](src/cortex_unified/reports/reports.py)** (307 LOC)
  - **Purpose**: Report generation and export: text, HTML, JSON, and CSV.
  - **Classes (1)**: `ReportsGenerator` (12 methods: `_get_default_reports_dir`, `generate_text_report`, `_format_text_report`, `_add_text_section`)

- [ ] **227. [`src/cortex_unified/reports/restore_manager.py`](src/cortex_unified/reports/restore_manager.py)** (311 LOC)
  - **Purpose**: Backup manifests and quarantine-style restoration of deleted files.
  - **Classes (1)**: `RestoreManager` (8 methods: `_get_default_backup_dir`, `list_manifests`, `get_manifest_details`, `restore_from_manifest`)

- [ ] **228. [`src/cortex_unified/scheduler/__init__.py`](src/cortex_unified/scheduler/__init__.py)** (15 LOC)
  - **Purpose**: Task scheduling module for Cortex Cleaner.

- [ ] **229. [`src/cortex_unified/scheduler/auto_clean_rules.py`](src/cortex_unified/scheduler/auto_clean_rules.py)** (387 LOC)
  - **Purpose**: Condition-triggered cleanup rules evaluated against live system state.
  - **Classes (1)**: `AutoCleanRules` (18 methods: `add_disk_usage_rule`, `add_startup_rule`, `add_shutdown_rule`, `add_scheduled_rule`)

- [ ] **230. [`src/cortex_unified/scheduler/scheduler.py`](src/cortex_unified/scheduler/scheduler.py)** (433 LOC)
  - **Purpose**: OS-native scheduling for cleanup jobs: schtasks, launchd, cron.
  - **Classes (1)**: `TaskScheduler` (12 methods: `create_scheduled_task`, `_create_windows_task`, `_create_macos_task`, `_generate_launchd_plist`)

- [ ] **231. [`src/cortex_unified/i18n/__init__.py`](src/cortex_unified/i18n/__init__.py)** (17 LOC)
  - **Purpose**: Backwards-compatibility alias for cortex_unified.translations.

## Accessibility, Visualization & UI Safety

- [ ] **232. [`src/cortex_unified/accessibility/__init__.py`](src/cortex_unified/accessibility/__init__.py)** (53 LOC)
  - **Purpose**: Accessibility module for Cortex Cleaner.
  - **Exported Functions (2)**: `setup_accessibility`, `setup_full_accessibility`

- [ ] **233. [`src/cortex_unified/accessibility/keyboard_handler.py`](src/cortex_unified/accessibility/keyboard_handler.py)** (375 LOC)
  - **Purpose**: Keyboard-only navigation: focus cycling, tab order, and app shortcuts.
  - **Classes (1)**: `KeyboardHandler` (22 methods: `setup_keyboard_navigation`, `_find_focusable_widgets`, `_setup_tab_order`, `handle_tab_navigation`)

- [ ] **234. [`src/cortex_unified/accessibility/screen_reader.py`](src/cortex_unified/accessibility/screen_reader.py)** (436 LOC)
  - **Purpose**: Screen-reader affordances for Qt widget hierarchies.
  - **Classes (1)**: `ScreenReaderSupport` (19 methods: `_init_platform_accessibility`, `add_aria_labels`, `_generate_accessible_name`, `_generate_accessible_description`)

- [ ] **235. [`src/cortex_unified/accessibility/themes.py`](src/cortex_unified/accessibility/themes.py)** (236 LOC)
  - **Purpose**: High contrast and accessibility themes for Cortex Cleaner.
  - **Classes (1)**: `AccessibilityThemes` (8 methods: `apply_high_contrast_theme`, `apply_dark_theme`, `apply_light_theme`, `restore_default_theme`)
  - **Exported Functions (2)**: `get_theme_manager`, `apply_accessibility_theme`

- [ ] **236. [`src/cortex_unified/visualization/__init__.py`](src/cortex_unified/visualization/__init__.py)** (15 LOC)
  - **Purpose**: Visualization module for Cortex Cleaner.

- [ ] **237. [`src/cortex_unified/visualization/interactive_dashboard.py`](src/cortex_unified/visualization/interactive_dashboard.py)** (485 LOC)
  - **Purpose**: Interactive dashboard for comprehensive data visualization.
  - **Classes (1)**: `InteractiveDashboard` (16 methods: `_initialize_generators`, `create_dashboard`, `_create_empty_dashboard`, `_create_treemap_dashboard`)

- [ ] **238. [`src/cortex_unified/visualization/sunburst_generator.py`](src/cortex_unified/visualization/sunburst_generator.py)** (380 LOC)
  - **Purpose**: Plotly sunburst renderer for hierarchical disk usage trees.
  - **Classes (2)**: `SunburstSegment`, `SunburstGenerator` (8 methods: `_setup_color_scheme`, `_get_file_type_from_path`, `_get_color_for_level_and_type`, `_convert_directory_tree_to_sunburst_data`)

- [ ] **239. [`src/cortex_unified/visualization/treemap_generator.py`](src/cortex_unified/visualization/treemap_generator.py)** (377 LOC)
  - **Purpose**: TreeMap visualization generator for disk usage analysis.
  - **Classes (2)**: `TreeMapNode`, `TreeMapGenerator` (9 methods: `_setup_color_scheme`, `_get_file_type_from_path`, `_get_color_for_item`, `_convert_directory_tree_to_nodes`)

- [ ] **240. [`src/cortex_unified/ui/safety/__init__.py`](src/cortex_unified/ui/safety/__init__.py)** (23 LOC)
  - **Purpose**: Safety infrastructure for Cortex Cleaner GUI operations.

- [ ] **241. [`src/cortex_unified/ui/safety/manifest_system.py`](src/cortex_unified/ui/safety/manifest_system.py)** (446 LOC)
  - **Purpose**: Atomic manifest creation and operation logging system.
  - **Classes (2)**: `ManifestError`, `ManifestSystem` (12 methods: `_get_default_manifest_dir`, `create_operation_manifest`, `_get_user_info`, `_get_os_info`)

- [ ] **242. [`src/cortex_unified/ui/safety/path_validator.py`](src/cortex_unified/ui/safety/path_validator.py)** (392 LOC)
  - **Purpose**: Path validation with OS-specific safety rules and symlink protection.
  - **Classes (2)**: `PathValidationError`, `PathValidator` (11 methods: `_get_critical_directories`, `add_user_whitelist`, `add_blacklist`, `is_safe_to_delete`)

- [ ] **243. [`src/cortex_unified/ui/safety/process_manager.py`](src/cortex_unified/ui/safety/process_manager.py)** (458 LOC)
  - **Purpose**: Safe external command execution manager.
  - **Classes (5)**: `ProcessError`, `ProcessTimeoutError`, `ExecutableNotFoundError`, `ProcessResult`, `ProcessManager` (8 methods: `set_security_policy`, `validate_executable`, `sanitize_command_args`, `execute_safe_command`)

- [ ] **244. [`src/cortex_unified/ui/safety/safety_manager.py`](src/cortex_unified/ui/safety/safety_manager.py)** (1400 LOC)
  - **Purpose**: Central safety manager that coordinates all safety components.
  - **Classes (6)**: `OperationType`, `ValidationResult`, `Operation`, `OperationResult`, `SafetyError`

- [ ] **245. [`src/cortex_unified/ui/navigation/__init__.py`](src/cortex_unified/ui/navigation/__init__.py)** (6 LOC)
  - **Purpose**: Navigation framework for Cortex Cleaner GUI.

- [ ] **246. [`src/cortex_unified/ui/navigation/icon_helper.py`](src/cortex_unified/ui/navigation/icon_helper.py)** (127 LOC)
  - **Purpose**: Icon helper for navigation system.
  - **Classes (1)**: `IconHelper` (4 methods: `create_text_icon`, `get_standard_icon`, `get_navigation_icons`, `create_colored_circle_icon`)

- [ ] **247. [`src/cortex_unified/ui/navigation/navigation_controller.py`](src/cortex_unified/ui/navigation/navigation_controller.py)** (390 LOC)
  - **Purpose**: Navigation controller for Cortex Cleaner GUI.
  - **Classes (1)**: `NavigationController` (17 methods: `setup_ui`, `create_navigation_panel`, `setup_styling`, `add_tab`)

- [ ] **248. [`src/cortex_unified/cli/__init__.py`](src/cortex_unified/cli/__init__.py)** (3 LOC)
  - **Purpose**: Command Line Interface (CLI) module for Cortex Workstation.

- [ ] **249. [`src/cortex_unified/cli/__main__.py`](src/cortex_unified/cli/__main__.py)** (8 LOC)
  - **Purpose**: CLI module execution entrypoint: python -m cortex_unified.cli.

- [ ] **250. [`src/cortex_unified/cli/cli.py`](src/cortex_unified/cli/cli.py)** (2185 LOC)
  - **Purpose**: Command-line interface for Cortex Cleaner (legacy ``cortex-cleaner``).
  - **Exported Functions (25)**: `main`, `clean_empty`, `find_large_files`, `find_duplicates`, `clean_temp`, `analyze_disk`, `list_startup_items`, `analyze_processes`

- [ ] **251. [`src/cortex_unified/debug/__init__.py`](src/cortex_unified/debug/__init__.py)** (15 LOC)
  - **Purpose**: Cortex Cleaner Production Debugging & Diagnostics Engine.

- [ ] **252. [`src/cortex_unified/debug/__main__.py`](src/cortex_unified/debug/__main__.py)** (14 LOC)
  - **Purpose**: CLI entry point for python -m cortex_unified.debug.

- [ ] **253. [`src/cortex_unified/debug/runner.py`](src/cortex_unified/debug/runner.py)** (918 LOC)
  - **Purpose**: Production-Grade Diagnostics and Debugging Runner.
  - **Classes (4)**: `DiagnosticItem`, `DiagnosticSection` (2 methods: `total`, `is_success`), `DiagnosticReport` (1 methods: `to_dict`), `DiagnosticRunner` (10 methods: `run_section`, `check_icons`, `check_system_tools`, `check_analyzers`)
  - **Exported Functions (7)**: `green`, `red`, `yellow`, `cyan`, `bold`, `run_all_diagnostics`, `main`

## Premium UI Navigation Shell & Pages

- [ ] **254. [`src/cortex_unified/ui/premium/__init__.py`](src/cortex_unified/ui/premium/__init__.py)** (13 LOC)
  - **Purpose**: Cortex Cleaner - premium GUI.

- [ ] **255. [`src/cortex_unified/ui/premium/__main__.py`](src/cortex_unified/ui/premium/__main__.py)** (10 LOC)
  - **Purpose**: Entry point for python -m cortex_unified.ui.premium.

- [ ] **256. [`src/cortex_unified/ui/premium/advanced_uninstaller_page.py`](src/cortex_unified/ui/premium/advanced_uninstaller_page.py)** (514 LOC)
  - **Purpose**: Advanced Uninstaller — multi-source app removal with forced uninstall and leftover scanning.
  - **Classes (2)**: `_UninstallWorker` (2 methods: `cancel`, `run`), `AdvancedUninstallerPage` (10 methods: `_pick_root`, `_scan`, `_on_progress`, `_on_scan_done`)

- [ ] **257. [`src/cortex_unified/ui/premium/analysis_pages.py`](src/cortex_unified/ui/premium/analysis_pages.py)** (2329 LOC)
  - **Purpose**: Analysis & system pages: Disk Analyzer, Disk Health (S.M.A.R.T.), Scheduled Tasks.
  - **Classes (22)**: `DiskAnalyzeWorker` (1 methods: `run`), `DiskHealthWorker` (1 methods: `run`), `ScheduledTasksWorker` (1 methods: `run`), `BootPerfWorker` (1 methods: `run`), `SystemRepairWorker` (1 methods: `run`)

- [ ] **258. [`src/cortex_unified/ui/premium/apex_tools_pages.py`](src/cortex_unified/ui/premium/apex_tools_pages.py)** (1213 LOC)
  - **Purpose**: Cortex Cleaner & NexusExplorer — Apex Enterprise Power Tools Pages.
  - **Classes (10)**: `DriverStoreCleanerPage` (3 methods: `_on_scan`, `_on_export`, `_on_delete_superseded`), `ShellbagsCleanerPage` (2 methods: `_on_scan`, `_on_clean`), `PowerPlanOptimizerPage` (3 methods: `_refresh`, `_on_unlock_ultimate`, `_on_reduce_hiber`), `HostsFileManagerPage` (2 methods: `_on_load`, `_on_apply_shield`), `NotificationCleanerPage` (2 methods: `_refresh`, `_on_clean`)

- [ ] **259. [`src/cortex_unified/ui/premium/app.py`](src/cortex_unified/ui/premium/app.py)** (422 LOC)
  - **Purpose**: Premium GUI entry point (installed as the ``cortex-gui`` command).
  - **Exported Functions (3)**: `log_dir`, `setup_logging`, `main`

- [ ] **260. [`src/cortex_unified/ui/premium/audio_duplicates_page.py`](src/cortex_unified/ui/premium/audio_duplicates_page.py)** (226 LOC)
  - **Purpose**: Audio duplicate detection page – Chromaprint-inspired acoustic fingerprinting.
  - **Classes (2)**: `_AudioWorker` (2 methods: `cancel`, `run`), `AudioDuplicatesPage` (5 methods: `_pick`, `_run`, `_on_progress`, `_on_done`)

- [ ] **261. [`src/cortex_unified/ui/premium/backdrop.py`](src/cortex_unified/ui/premium/backdrop.py)** (118 LOC)
  - **Purpose**: Optional native window backdrop (Windows 11 Mica/Acrylic).
  - **Exported Functions (1)**: `apply_backdrop`

- [ ] **262. [`src/cortex_unified/ui/premium/bad_files_studio_page.py`](src/cortex_unified/ui/premium/bad_files_studio_page.py)** (300 LOC)
  - **Purpose**: Bad Extensions, File Names & EXIF Studio Page.
  - **Classes (2)**: `_BadFilesScanWorker` (1 methods: `run`), `BadFilesStudioPage` (6 methods: `_on_tool_changed`, `_pick_folder`, `_scan`, `_on_done`)

- [ ] **263. [`src/cortex_unified/ui/premium/cdc_page.py`](src/cortex_unified/ui/premium/cdc_page.py)** (223 LOC)
  - **Purpose**: Content-Defined Chunking page – FastCDC / VectorCDC (FAST'25).
  - **Classes (2)**: `_CdcWorker` (2 methods: `cancel`, `run`), `CdcPage` (5 methods: `_pick`, `_run`, `_on_progress`, `_on_done`)

- [ ] **264. [`src/cortex_unified/ui/premium/cleanup_hub_page.py`](src/cortex_unified/ui/premium/cleanup_hub_page.py)** (725 LOC)
  - **Purpose**: Cleanup Hub: unified Storage Sense-style view of all cleanup categories.
  - **Classes (3)**: `HubScanWorker` (2 methods: `cancel`, `run`), `TempScanWorker` (2 methods: `cancel`, `run`), `CleanupHubPage` (17 methods: `_on_scan_all_clicked`, `_scan`, `_on_progress`, `_on_scanned`)

- [ ] **265. [`src/cortex_unified/ui/premium/cloud_storage_page.py`](src/cortex_unified/ui/premium/cloud_storage_page.py)** (768 LOC)
  - **Purpose**: Cloud Storage Analyzer — S3, Azure, Google Drive, OneDrive, rclone.
  - **Classes (3)**: `_WorkerResult`, `_CloudWorker` (2 methods: `cancel`, `run`), `CloudStoragePage` (21 methods: `_build_summary_tab`, `_build_by_provider_tab`, `_build_by_class_tab`, `_build_duplicates_tab`)

- [ ] **266. [`src/cortex_unified/ui/premium/compact_os_page.py`](src/cortex_unified/ui/premium/compact_os_page.py)** (365 LOC)
  - **Purpose**: CompactOS / NTFS compression page – estimate, then compress only on demand.
  - **Classes (4)**: `_ScanWorker` (2 methods: `cancel`, `run`), `_CompactWorker` (1 methods: `run`), `_QueryWorker` (1 methods: `run`), `CompactOsPage` (9 methods: `_pick`, `_query`, `_on_query`, `_scan`)

- [ ] **267. [`src/cortex_unified/ui/premium/delivery_optimization_page.py`](src/cortex_unified/ui/premium/delivery_optimization_page.py)** (257 LOC)
  - **Purpose**: Delivery Optimization (WUDO) Peer Cache Cleaner Page.
  - **Classes (3)**: `_DeliveryScanWorker` (1 methods: `run`), `_DeliveryCleanWorker` (1 methods: `run`), `DeliveryOptimizationPage` (6 methods: `_scan`, `_on_scan_done`, `_confirm_clean`, `_clean`)

- [ ] **268. [`src/cortex_unified/ui/premium/device_window.py`](src/cortex_unified/ui/premium/device_window.py)** (1695 LOC)
  - **Purpose**: Per-device deep scan worker and the premium device detail window.
  - **Classes (3)**: `DeviceDeepScanWorker` (7 methods: `cancel`, `_say`, `run`, `_run_nmap`), `DevicePingWorker` (2 methods: `cancel`, `run`), `DeviceDetailWindow` (34 methods: `_build_header`, `_header_badges`, `_build_actions`, `_toggle_more_actions`)

- [ ] **269. [`src/cortex_unified/ui/premium/directstorage_page.py`](src/cortex_unified/ui/premium/directstorage_page.py)** (177 LOC)
  - **Purpose**: Windows 11 DirectStorage & BypassIO Hardware Acceleration Page.
  - **Classes (2)**: `_DirectStorageWorker` (1 methods: `run_audit`), `DirectStorageOptimizerPage` (2 methods: `_start_audit`, `_on_audit_finished`)

- [ ] **270. [`src/cortex_unified/ui/premium/disk_analyzer_page.py`](src/cortex_unified/ui/premium/disk_analyzer_page.py)** (502 LOC)
  - **Purpose**: Advanced Disk Analyzer page — MFT fast scan, treemap, deep folder breakdown.
  - **Classes (2)**: `_ScanWorker` (2 methods: `cancel`, `run`), `DiskAnalyzerPage` (9 methods: `_populate_drives`, `_on_drive_changed`, `_browse`, `_run`)

- [ ] **271. [`src/cortex_unified/ui/premium/driver_manager_page.py`](src/cortex_unified/ui/premium/driver_manager_page.py)** (545 LOC)
  - **Purpose**: Driver Manager page — scan, update, backup and clean device drivers.
  - **Classes (4)**: `_ScanWorker` (2 methods: `cancel`, `run`), `_InstallWorker` (2 methods: `cancel`, `run`), `_BackupWorker` (2 methods: `cancel`, `run`), `DriverManagerPage` (12 methods: `_selected_hwids`, `_populate_table`, `_scan`, `_on_progress`)

- [ ] **272. [`src/cortex_unified/ui/premium/enterprise_suite_pages.py`](src/cortex_unified/ui/premium/enterprise_suite_pages.py)** (1329 LOC)
  - **Purpose**: Cortex Cleaner & NexusExplorer — Enterprise Next-Gen Suite GUI Pages.
  - **Classes (10)**: `VssManagerPage` (6 methods: `_on_audit`, `_on_audit_done`, `_on_create`, `_on_purge`), `DevDriveOptimizerPage` (3 methods: `_on_audit`, `_on_audit_done`, `_on_err`), `BitLockerAuditorPage` (3 methods: `_on_audit`, `_on_audit_done`, `_on_err`), `JunctionAuditorPage` (5 methods: `_on_scan`, `_on_custom`, `_on_scan_done`, `_on_clean_dead`), `BitRotScrubberPage` (4 methods: `_on_browse`, `_on_scrub`, `_on_scrub_done`, `_on_err`)

- [ ] **273. [`src/cortex_unified/ui/premium/expanded_tools_pages.py`](src/cortex_unified/ui/premium/expanded_tools_pages.py)** (1622 LOC)
  - **Purpose**: Cortex Cleaner & NexusExplorer — Expanded Enterprise Power Tools Pages.
  - **Classes (11)**: `LinksManagerPage` (3 methods: `_on_choose_folder`, `_on_scan`, `_on_remove_link`), `FastCopierPage` (3 methods: `_on_add_source`, `_on_choose_dest`, `_on_start_copy`), `TimestampTouchPage` (2 methods: `_on_choose_files`, `_on_apply`), `ArchiveManagerPage` (4 methods: `_on_open_archive`, `_on_test_archive`, `_on_extract_archive`, `_on_create_archive`), `PrefetchAnalyzerPage` (3 methods: `_refresh_status`, `_on_scan`, `_on_clean`)
  - **Exported Functions (2)**: `PrimaryButton`, `SecondaryButton`

- [ ] **274. [`src/cortex_unified/ui/premium/focus.py`](src/cortex_unified/ui/premium/focus.py)** (144 LOC)
  - **Purpose**: Focus-visible: show keyboard focus rings only for keyboard navigation.
  - **Classes (1)**: `FocusVisibleFilter` (2 methods: `eventFilter`, `_set_visible`)
  - **Exported Functions (1)**: `install_focus_visible`

- [ ] **275. [`src/cortex_unified/ui/premium/fuzzy_hash_page.py`](src/cortex_unified/ui/premium/fuzzy_hash_page.py)** (222 LOC)
  - **Purpose**: Fuzzy hash page – ssdeep-style CTPH for *close-but-different* binaries.
  - **Classes (2)**: `_FuzzyWorker` (2 methods: `cancel`, `run`), `FuzzyHashPage` (5 methods: `_pick`, `_run`, `_on_progress`, `_on_done`)

- [ ] **276. [`src/cortex_unified/ui/premium/game_mode_page.py`](src/cortex_unified/ui/premium/game_mode_page.py)** (286 LOC)
  - **Purpose**: Gaming Session & FPS Booster Page — one-click reversible PC optimization.
  - **Classes (3)**: `_GameModeQueryWorker` (1 methods: `run`), `_GameModeActionWorker` (1 methods: `run`), `GameModePage` (8 methods: `_query`, `_on_query_done`, `_toggle_boost`, `_start_boost`)

- [ ] **277. [`src/cortex_unified/ui/premium/icons.py`](src/cortex_unified/ui/premium/icons.py)** (238 LOC)
  - **Purpose**: Crisp, theme-tinted SVG icons.
  - **Exported Functions (7)**: `pixmap`, `icon`, `available`, `has_icon`, `icon_size`, `clear_cache`, `tinted_color`

- [ ] **278. [`src/cortex_unified/ui/premium/license_page.py`](src/cortex_unified/ui/premium/license_page.py)** (250 LOC)
  - **Purpose**: License & Tiers page: current entitlement, offline activation, trial.
  - **Classes (1)**: `LicensePage` (5 methods: `_refresh`, `_fill_table`, `_activate`, `_start_trial`)

- [ ] **279. [`src/cortex_unified/ui/premium/log_sweeper_page.py`](src/cortex_unified/ui/premium/log_sweeper_page.py)** (362 LOC)
  - **Purpose**: Log Sweeper: find large *.log/*.txt files across user-selected and detected roots.
  - **Classes (2)**: `_LogWorker` (2 methods: `cancel`, `run`), `LogSweeperPage` (10 methods: `_add_root`, `_discover_code_roots`, `_select_code_root`, `_rm_root`)

- [ ] **280. [`src/cortex_unified/ui/premium/memory_standby_page.py`](src/cortex_unified/ui/premium/memory_standby_page.py)** (173 LOC)
  - **Purpose**: Windows RAM Standby List & Working Set Kernel Purger Page.
  - **Classes (1)**: `MemoryStandbyPurgerPage` (6 methods: `_refresh_stats`, `_on_purge_standby`, `_on_empty_working_sets`, `_on_purge_modified`)

- [ ] **281. [`src/cortex_unified/ui/premium/mft_slack_page.py`](src/cortex_unified/ui/premium/mft_slack_page.py)** (261 LOC)
  - **Purpose**: NTFS Master File Table ($MFT) & Directory Index Slack Scrubber Page.
  - **Classes (2)**: `_MftScrubWorker` (2 methods: `run_audit`, `run_scrub`), `MftSlackScrubberPage` (5 methods: `_on_volume_changed`, `_start_audit`, `_on_audit_finished`, `_start_scrub`)

- [ ] **282. [`src/cortex_unified/ui/premium/model_cache_page.py`](src/cortex_unified/ui/premium/model_cache_page.py)** (303 LOC)
  - **Purpose**: Model Cache page – hardlink-aware HF hub / Ollama / LM Studio.
  - **Classes (3)**: `_ScanWorker` (1 methods: `run`), `_CleanOrphansWorker` (1 methods: `run`), `ModelCachePage` (5 methods: `_scan`, `_on_scan`, `_clean`, `_on_clean`)

- [ ] **283. [`src/cortex_unified/ui/premium/more_pages.py`](src/cortex_unified/ui/premium/more_pages.py)** (3413 LOC)
  - **Purpose**: Additional premium pages: Software Updater, Drive Optimizer, System Info.
  - **Classes (21)**: `UpdaterListWorker` (1 methods: `run`), `UpgradeWorker` (1 methods: `run`), `DriveListWorker` (1 methods: `run`), `DriveOptimizeWorker` (1 methods: `run`), `SystemInfoWorker` (1 methods: `run`)

- [ ] **284. [`src/cortex_unified/ui/premium/motion.py`](src/cortex_unified/ui/premium/motion.py)** (256 LOC)
  - **Purpose**: Motion system: a single shared set of animation durations and easing curves
  - **Classes (1)**: `Duration`
  - **Exported Functions (6)**: `prefers_reduced_motion`, `set_reduced_motion`, `fade_in`, `reveal`, `press_feedback`, `animate_property`

- [ ] **285. [`src/cortex_unified/ui/premium/near_duplicates_page.py`](src/cortex_unified/ui/premium/near_duplicates_page.py)** (226 LOC)
  - **Purpose**: Near-duplicate finder page – MinHash LSH + Bloom (SEDD/LSHBloom/SemHash).
  - **Classes (2)**: `_NearDupWorker` (2 methods: `cancel`, `run`), `NearDuplicatesPage` (5 methods: `_pick`, `_run`, `_on_progress`, `_on_done`)

- [ ] **286. [`src/cortex_unified/ui/premium/network_pages.py`](src/cortex_unified/ui/premium/network_pages.py)** (3635 LOC)
  - **Purpose**: Network suite pages: live Traffic Monitor and Firewall control.
  - **Classes (18)**: `TrafficMonitorPage` (2 methods: `_start`, `_tick`), `FirewallListWorker` (1 methods: `run`), `FirewallActionWorker` (1 methods: `run`), `FirewallPage` (11 methods: `_browse`, `_busy`, `_create`, `_on_action`), `_MapCanvas` (4 methods: `set_edges`, `paintEvent`, `_curve`, `_node`)

- [ ] **287. [`src/cortex_unified/ui/premium/nextgen_suite_pages.py`](src/cortex_unified/ui/premium/nextgen_suite_pages.py)** (1115 LOC)
  - **Purpose**: Cortex Cleaner & NexusExplorer — Next-Generation Enterprise Suite GUI Pages.
  - **Classes (7)**: `ShaderCachePage` (2 methods: `_on_scan`, `_on_clean`), `AiTelemetryCleanerPage` (2 methods: `_on_scan`, `_on_clean`), `SsdTrimOptimizerPage` (2 methods: `_on_audit`, `_on_trim`), `RestartManagerUnlockerPage` (3 methods: `_on_browse`, `_on_inspect`, `_on_unlock`), `VssHealthAnalyzerPage` (2 methods: `_on_scan`, `_on_reset`)

- [ ] **288. [`src/cortex_unified/ui/premium/nexus_page.py`](src/cortex_unified/ui/premium/nexus_page.py)** (163 LOC)
  - **Purpose**: Nexus File Manager page.
  - **Classes (2)**: `_ErrorCard`, `NexusExplorerPage` (1 methods: `_build_explorer`)

- [ ] **289. [`src/cortex_unified/ui/premium/old_files_page.py`](src/cortex_unified/ui/premium/old_files_page.py)** (267 LOC)
  - **Purpose**: Old & Inactive Files Finder Page.
  - **Classes (2)**: `_OldFilesScanWorker` (1 methods: `run`), `OldFilesPage` (5 methods: `_pick_folder`, `_scan`, `_on_done`, `_delete_selected`)

- [ ] **290. [`src/cortex_unified/ui/premium/perceptual_duplicates_page.py`](src/cortex_unified/ui/premium/perceptual_duplicates_page.py)** (228 LOC)
  - **Purpose**: Perceptual duplicate photos page – pHash / dHash / aHash.
  - **Classes (2)**: `_PerceptualWorker` (2 methods: `cancel`, `run`), `PerceptualDuplicatesPage` (5 methods: `_pick`, `_run`, `_on_progress`, `_on_done`)

- [ ] **291. [`src/cortex_unified/ui/premium/portable_manager_page.py`](src/cortex_unified/ui/premium/portable_manager_page.py)** (397 LOC)
  - **Purpose**: Portable App Manager page — scan, track, and update portable apps.
  - **Classes (3)**: `_PortableWorker` (2 methods: `cancel`, `run`), `_UpdateWorker` (2 methods: `cancel`, `run`), `PortableManagerPage` (10 methods: `_add_root`, `_parse_roots`, `_get_target_apps`, `_run`)

- [ ] **292. [`src/cortex_unified/ui/premium/power_suite_pages.py`](src/cortex_unified/ui/premium/power_suite_pages.py)** (1288 LOC)
  - **Purpose**: Cortex Cleaner & NexusExplorer — Enterprise Power Suite GUI Pages.
  - **Classes (10)**: `EnvVariableManagerPage` (3 methods: `_on_analyze`, `_on_clean`, `_on_export`), `WindowsServiceManagerPage` (2 methods: `_on_scan`, `_on_apply_profile`), `FontCacheManagerPage` (2 methods: `_on_scan`, `_on_clean`), `TempFolderCleanerPage` (2 methods: `_on_scan`, `_on_clean`), `ContextMenuManagerPage` (3 methods: `_on_scan`, `_on_disable_selected`, `_on_enable_selected`)

- [ ] **293. [`src/cortex_unified/ui/premium/power_tools_pages.py`](src/cortex_unified/ui/premium/power_tools_pages.py)** (1464 LOC)
  - **Purpose**: Premium GUI pages for Enterprise Power Tools & System Maintainers.
  - **Classes (10)**: `HashVerifierPage` (4 methods: `_pick_file`, `_compute_hashes`, `_copy_to_clip`, `_verify_manifest`), `BatchRenamerPage` (4 methods: `_pick_files`, `_update_preview`, `_apply_rename`, `_undo_rename`), `FolderSyncPage` (4 methods: `_pick_left`, `_pick_right`, `_run_compare`, `_run_sync`), `FileSplitterPage` (4 methods: `_pick_split_src`, `_execute_split`, `_pick_join_src`, `_execute_join`), `FileUnlockerPage` (3 methods: `_pick_file`, `_inspect_locks`, `_terminate_proc`)

- [ ] **294. [`src/cortex_unified/ui/premium/privacy_blocker_page.py`](src/cortex_unified/ui/premium/privacy_blocker_page.py)** (346 LOC)
  - **Purpose**: Privacy & Telemetry Blocker page — profile-based telemetry control.
  - **Classes (2)**: `_PrivacyWorker` (2 methods: `cancel`, `run`), `PrivacyBlockerPage` (8 methods: `_discover_categories`, `_selected_tweak_ids`, `_apply`, `_revert`)

- [ ] **295. [`src/cortex_unified/ui/premium/process_studio_page.py`](src/cortex_unified/ui/premium/process_studio_page.py)** (250 LOC)
  - **Purpose**: Advanced Process & Threat Studio Page.
  - **Classes (2)**: `_ProcessScanWorker` (1 methods: `run`), `ProcessStudioPage` (5 methods: `_scan`, `_on_done`, `_apply_filter`, `_kill_selected`)

- [ ] **296. [`src/cortex_unified/ui/premium/registry.py`](src/cortex_unified/ui/premium/registry.py)** (977 LOC)
  - **Purpose**: The single source of truth for every tool page in the premium shell.
  - **Classes (2)**: `NavGroup`, `PageSpec` (1 methods: `load`)
  - **Exported Functions (4)**: `ordered_ids`, `ordered_specs`, `grouped`, `group_of`

- [ ] **297. [`src/cortex_unified/ui/premium/registry_ai_page.py`](src/cortex_unified/ui/premium/registry_ai_page.py)** (307 LOC)
  - **Purpose**: AI Registry Cleaner page — ML-powered risk scoring for registry cleanup.
  - **Classes (2)**: `_RegistryWorker` (2 methods: `cancel`, `run`), `RegistryAICleanerPage` (6 methods: `_pick`, `_run`, `_all_categories`, `_on_progress`)

- [ ] **298. [`src/cortex_unified/ui/premium/report_pages.py`](src/cortex_unified/ui/premium/report_pages.py)** (558 LOC)
  - **Purpose**: Reporting & recovery pages: exportable PC Health Report, Backups/Restore.
  - **Classes (5)**: `HealthReportWorker` (2 methods: `_collect`, `run`), `ManifestListWorker` (2 methods: `_leftover_sessions`, `run`), `RestoreWorker` (1 methods: `run`), `HealthReportPage` (4 methods: `_generate`, `_on_done`, `_open_last`, `_fail`), `BackupsPage` (10 methods: `_on_sel`, `_load`, `_on_listed`, `_selected_manifest`)

- [ ] **299. [`src/cortex_unified/ui/premium/residual_cleaner_page.py`](src/cortex_unified/ui/premium/residual_cleaner_page.py)** (276 LOC)
  - **Purpose**: Uninstalled Software Residual Hunter Page.
  - **Classes (2)**: `_ResidualScanWorker` (1 methods: `run`), `ResidualCleanerPage` (4 methods: `_scan`, `_on_done`, `_clean_selected`, `_fail`)

- [ ] **300. [`src/cortex_unified/ui/premium/s3_fifo_page.py`](src/cortex_unified/ui/premium/s3_fifo_page.py)** (201 LOC)
  - **Purpose**: S3-FIFO cache policy benchmark – FIFO queues are all you need (SOSP'23).
  - **Classes (2)**: `_BenchWorker` (1 methods: `run`), `S3FifoPage` (3 methods: `_run`, `_on_done`, `_fail`)

- [ ] **301. [`src/cortex_unified/ui/premium/search_optimizer_page.py`](src/cortex_unified/ui/premium/search_optimizer_page.py)** (249 LOC)
  - **Purpose**: Windows Search Index Database (Windows.edb) Optimizer Page.
  - **Classes (2)**: `_SearchWorker` (3 methods: `run_status`, `run_compact`, `run_rebuild`), `SearchIndexOptimizerPage` (6 methods: `_start_status_query`, `_on_status_ready`, `_start_compact`, `_start_rebuild`)

- [ ] **302. [`src/cortex_unified/ui/premium/secure_shredder_page.py`](src/cortex_unified/ui/premium/secure_shredder_page.py)** (448 LOC)
  - **Purpose**: Secure File Shredder — multi-standard sanitization with verification.
  - **Classes (2)**: `_ShredWorker` (2 methods: `cancel`, `run`), `SecureShredderPage` (9 methods: `_add_files`, `_add_folder`, `_clear_list`, `_update_file_count`)

- [ ] **303. [`src/cortex_unified/ui/premium/settings_store.py`](src/cortex_unified/ui/premium/settings_store.py)** (244 LOC)
  - **Purpose**: Durable, atomically-written user settings for the premium GUI.
  - **Classes (1)**: `SettingsStore` (15 methods: `_load`, `_sanitize`, `save`, `get`)
  - **Exported Functions (1)**: `settings_path`

- [ ] **304. [`src/cortex_unified/ui/premium/skeleton.py`](src/cortex_unified/ui/premium/skeleton.py)** (151 LOC)
  - **Purpose**: Skeleton shimmer: a reassuring "loading" placeholder for premium feel.
  - **Classes (1)**: `ShimmerSkeleton` (6 methods: `_get_phase`, `_set_phase`, `start`, `stop`)

- [ ] **305. [`src/cortex_unified/ui/premium/smoothscroll.py`](src/cortex_unified/ui/premium/smoothscroll.py)** (157 LOC)
  - **Purpose**: Smooth momentum scrolling for a premium, non-janky scroll feel.
  - **Classes (1)**: `SmoothScroller` (2 methods: `eventFilter`, `_on_wheel`)
  - **Exported Functions (1)**: `install_smooth_scroll`

- [ ] **306. [`src/cortex_unified/ui/premium/srum_bam_page.py`](src/cortex_unified/ui/premium/srum_bam_page.py)** (224 LOC)
  - **Purpose**: Windows BAM/DAM & SRUM Forensic Privacy Studio Page.
  - **Classes (2)**: `_SrumBamWorker` (2 methods: `run_scan`, `run_clean`), `SrumBamCleanerPage` (4 methods: `_start_scan`, `_on_scan_finished`, `_start_clean`, `_on_clean_finished`)

- [ ] **307. [`src/cortex_unified/ui/premium/startup_optimizer_page.py`](src/cortex_unified/ui/premium/startup_optimizer_page.py)** (711 LOC)
  - **Purpose**: Startup Optimizer page — stagger/delay engine with resource-aware gating.
  - **Classes (4)**: `_StartupScanWorker` (2 methods: `cancel`, `run`), `_DisableWorker` (2 methods: `cancel`, `run`), `_EnableWorker` (2 methods: `cancel`, `run`), `StartupOptimizerPage` (16 methods: `_run_scan`, `_on_scan_progress`, `_on_scan_done`, `_on_scan_fail`)

- [ ] **308. [`src/cortex_unified/ui/premium/states.py`](src/cortex_unified/ui/premium/states.py)** (518 LOC)
  - **Purpose**: Reusable loading / empty / error state panels for data-backed pages.
  - **Classes (3)**: `StatePanel` (11 methods: `bind_content`, `_sync_content`, `_build_ui`, `mode`), `_HoverLift` (2 methods: `eventFilter`, `_animate_to`), `_FocusRing` (2 methods: `eventFilter`, `_apply`)
  - **Exported Functions (2)**: `install_hover_lift`, `focus_ring`

- [ ] **309. [`src/cortex_unified/ui/premium/system_pages.py`](src/cortex_unified/ui/premium/system_pages.py)** (2358 LOC)
  - **Purpose**: Premium GUI pages for the real system-tool backends.
  - **Classes (22)**: `PrivacyScanWorker` (1 methods: `run`), `PrivacyCleanWorker` (1 methods: `run`), `StartupListWorker` (1 methods: `run`), `TaskSnapshotWorker` (1 methods: `run`), `NetworkWorker` (1 methods: `run`)

- [ ] **310. [`src/cortex_unified/ui/premium/tablemodel.py`](src/cortex_unified/ui/premium/tablemodel.py)** (403 LOC)
  - **Purpose**: A reusable model/view foundation for the data-dense tables.
  - **Classes (4)**: `Column` (2 methods: `display`, `sort_value`), `RecordTableModel` (10 methods: `set_records`, `clear`, `records`, `record_at`), `RecordFilterProxy` (4 methods: `set_filter_text`, `filter_text`, `filterAcceptsRow`, `lessThan`), `TableBinding` (5 methods: `set_records`, `set_filter_text`, `visible_count`, `selected_record`)
  - **Exported Functions (1)**: `bind_table`

- [ ] **311. [`src/cortex_unified/ui/premium/theme.py`](src/cortex_unified/ui/premium/theme.py)** (880 LOC)
  - **Purpose**: Premium design system: color tokens, typography, and a full QSS builder.
  - **Classes (1)**: `Palette` (2 methods: `accent_gradient`, `glass`)
  - **Exported Functions (3)**: `build_stylesheet`, `load_fonts`, `apply_theme`

- [ ] **312. [`src/cortex_unified/ui/premium/tokens.py`](src/cortex_unified/ui/premium/tokens.py)** (247 LOC)
  - **Purpose**: Qt-free design tokens for the premium UI/UX design system.
  - **Classes (4)**: `Spacing`, `Radius`, `Elevation`, `ElevationStyle`
  - **Exported Functions (2)**: `contrast_ratio`, `elevation_style`

- [ ] **313. [`src/cortex_unified/ui/premium/tools_pages.py`](src/cortex_unified/ui/premium/tools_pages.py)** (606 LOC)
  - **Purpose**: Tool pages: Performance (power plans), Browser Extensions, Driver inventory.
  - **Classes (7)**: `PowerPlanListWorker` (1 methods: `run`), `PowerPlanSetWorker` (1 methods: `run`), `ExtensionAuditWorker` (1 methods: `run`), `DriverListWorker` (1 methods: `run`), `PerformancePage` (5 methods: `_load`, `_on_listed`, `_apply`, `_on_applied`)

- [ ] **314. [`src/cortex_unified/ui/premium/tray.py`](src/cortex_unified/ui/premium/tray.py)** (445 LOC)
  - **Purpose**: Premium system tray: a background presence with a live resource monitor.
  - **Classes (1)**: `PremiumTray` (16 methods: `_tray_supported`, `available`, `_build_menu`, `_on_activated`)

- [ ] **315. [`src/cortex_unified/ui/premium/video_duplicates_page.py`](src/cortex_unified/ui/premium/video_duplicates_page.py)** (314 LOC)
  - **Purpose**: Video near-duplicate detection page – keyframe pHash + temporal consistence.
  - **Classes (2)**: `_VideoWorker` (2 methods: `cancel`, `run`), `VideoDuplicatesPage` (6 methods: `_pick`, `_run`, `_on_progress`, `_on_done`)

- [ ] **316. [`src/cortex_unified/ui/premium/wan_audit_page.py`](src/cortex_unified/ui/premium/wan_audit_page.py)** (259 LOC)
  - **Purpose**: WAN & UPnP IGD Security Auditor Page.
  - **Classes (2)**: `_WanAuditWorker` (2 methods: `cancel`, `run`), `WanAuditPage` (5 methods: `_scan`, `_on_progress`, `_on_done`, `_export`)

- [ ] **317. [`src/cortex_unified/ui/premium/widgets.py`](src/cortex_unified/ui/premium/widgets.py)** (776 LOC)
  - **Purpose**: Reusable premium widgets: elevated cards, a custom circular gauge, stat
  - **Classes (6)**: `Card`, `StatCard` (3 methods: `value`, `set_value`, `_pulse`), `Badge` (1 methods: `_rgb`), `CircularGauge` (6 methods: `_get_value`, `_set_value`, `animate_to`, `set_center_text`), `CoreBars` (3 methods: `set_values`, `_bar_color`, `paintEvent`)
  - **Exported Functions (7)**: `attach_glow`, `icon_for_exe`, `placeholder_icon`, `hline`, `status_note`, `title_block`, `require_feature`

- [ ] **318. [`src/cortex_unified/ui/premium/win_update_repair_page.py`](src/cortex_unified/ui/premium/win_update_repair_page.py)** (429 LOC)
  - **Purpose**: Windows Update Repair page — comprehensive component reset and repair.
  - **Classes (3)**: `_RepairWorker` (2 methods: `cancel`, `run`), `_PreflightWorker` (1 methods: `run`), `WinUpdateRepairPage` (7 methods: `_run_preflight`, `_pf_done`, `_pf_fail`, `_run_repair`)

- [ ] **319. [`src/cortex_unified/ui/premium/winapp2_page.py`](src/cortex_unified/ui/premium/winapp2_page.py)** (241 LOC)
  - **Purpose**: Winapp2 Community Declarative Application Cleaner Page.
  - **Classes (2)**: `_Winapp2Worker` (2 methods: `run_scan`, `run_clean`), `Winapp2CleanerPage` (5 methods: `_start_scan`, `_on_progress`, `_on_scan_finished`, `_start_clean`)

- [ ] **320. [`src/cortex_unified/ui/premium/window.py`](src/cortex_unified/ui/premium/window.py)** (3300 LOC)
  - **Purpose**: The premium main window: sidebar navigation + engine-backed pages.
  - **Classes (16)**: `_TitleBarChrome`, `_LazyPageRegistry` (3 methods: `is_built`, `built_ids`, `clear`), `_WorkerTaskSignals`, `_WorkerTaskRunnable` (1 methods: `run`), `WorkerRuntime` (1 methods: `run`)
  - **Exported Functions (4)**: `fmt_bytes`, `set_tab_order`, `ensure_focusable`, `run_modal`

- [ ] **321. [`src/cortex_unified/ui/premium/workers.py`](src/cortex_unified/ui/premium/workers.py)** (1070 LOC)
  - **Purpose**: Background workers bridging the GUI to the engine.
  - **Classes (29)**: `ScanWorker` (2 methods: `cancel`, `run`), `CleanWorker` (2 methods: `cancel`, `run`), `DuplicateWorker` (2 methods: `cancel`, `run`), `DirPreviewWorker` (1 methods: `run`), `DuplicatePhotosWorker` (2 methods: `cancel`, `run`)
  - **Exported Functions (3)**: `aggregate_roots`, `children_under`, `group_by_app`

- [ ] **322. [`src/cortex_unified/ui/premium/wsl_page.py`](src/cortex_unified/ui/premium/wsl_page.py)** (334 LOC)
  - **Purpose**: WSL Cleaner page: list distros + compact ext4.vhdx.
  - **Classes (3)**: `_WslListWorker` (1 methods: `run`), `_WslShutdownWorker` (1 methods: `run`), `WslPage` (7 methods: `_load`, `_on_list`, `_shutdown`, `_on_shutdown`)

## Classic UI Tabs & Panels

- [ ] **323. [`src/cortex_unified/ui/tabs/__init__.py`](src/cortex_unified/ui/tabs/__init__.py)** (5 LOC)
  - **Purpose**: GUI tabs module for Cortex Cleaner.

- [ ] **324. [`src/cortex_unified/ui/tabs/base_tab.py`](src/cortex_unified/ui/tabs/base_tab.py)** (415 LOC)
  - **Purpose**: Base tab class for Cortex Cleaner GUI tabs with safety manager integration.
  - **Classes (1)**: `BaseTab` (21 methods: `set_status`, `_initialize_tab`, `setup_ui`, `setup_connections`)

- [ ] **325. [`src/cortex_unified/ui/tabs/broken_links_tab.py`](src/cortex_unified/ui/tabs/broken_links_tab.py)** (649 LOC)
  - **Purpose**: Tab for broken links tab in Cortex Cleaner GUI.
  - **Classes (4)**: `BrokenLinksWorker` (1 methods: `run`), `LinkRepairWorker` (1 methods: `run`), `BrokenFilesWorker` (1 methods: `run`), `BrokenLinksTab` (16 methods: `setup_ui`, `select_all`, `deselect_all`, `browse_broken_links_path`)

- [ ] **326. [`src/cortex_unified/ui/tabs/dashboard_tab.py`](src/cortex_unified/ui/tabs/dashboard_tab.py)** (431 LOC)
  - **Purpose**: Dashboard tab — the command center for Cortex Cleaner.
  - **Classes (2)**: `OptimizerWorker` (2 methods: `run`, `stop`), `DashboardTab` (10 methods: `setup_ui`, `setup_tooltips`, `run_smart_scan`, `_on_progress`)

- [ ] **327. [`src/cortex_unified/ui/tabs/deep_cleaner_tab.py`](src/cortex_unified/ui/tabs/deep_cleaner_tab.py)** (553 LOC)
  - **Purpose**: Tab for deep disk cleaning in Cortex Cleaner GUI.
  - **Classes (3)**: `VideoOptimizeWorker` (1 methods: `run`), `DeepCleanerWorker` (1 methods: `run`), `DeepCleanerTab` (15 methods: `setup_ui`, `start_scan`, `format_bytes`, `scan_finished`)

- [ ] **328. [`src/cortex_unified/ui/tabs/disk_analyzer_tab.py`](src/cortex_unified/ui/tabs/disk_analyzer_tab.py)** (383 LOC)
  - **Purpose**: Tab for disk analyzer tab in Cortex Cleaner GUI.
  - **Classes (2)**: `DiskAnalyzerWorker` (1 methods: `run`), `DiskAnalyzerTab` (10 methods: `setup_ui`, `start_disk_analysis`, `_on_worker_finished`, `disk_analysis_complete`)

- [ ] **329. [`src/cortex_unified/ui/tabs/docker_tab.py`](src/cortex_unified/ui/tabs/docker_tab.py)** (430 LOC)
  - **Purpose**: Tab for docker tab in Cortex Cleaner GUI.
  - **Classes (3)**: `DockerScanWorker` (1 methods: `run`), `DockerCleanupWorker` (1 methods: `run`), `DockerTab` (9 methods: `setup_ui`, `check_docker_availability`, `start_docker_scan`, `_on_worker_finished`)

- [ ] **330. [`src/cortex_unified/ui/tabs/duplicates_tab.py`](src/cortex_unified/ui/tabs/duplicates_tab.py)** (407 LOC)
  - **Purpose**: Tab for duplicates tab in Cortex Cleaner GUI.
  - **Classes (2)**: `DuplicateFinderWorker` (1 methods: `run`), `DuplicatesTab` (10 methods: `setup_ui`, `start_find_duplicates`, `duplicates_found`, `select_all_duplicates`)

- [ ] **331. [`src/cortex_unified/ui/tabs/empty_files_tab.py`](src/cortex_unified/ui/tabs/empty_files_tab.py)** (520 LOC)
  - **Purpose**: Empty files cleaner tab for Cortex Cleaner GUI.
  - **Classes (3)**: `EmptyFinderWorker` (1 methods: `run`), `EmptyFilesWorker` (1 methods: `run`), `EmptyFilesTab` (12 methods: `setup_ui`, `setup_tooltips`, `browse_path`, `start_scan`)

- [ ] **332. [`src/cortex_unified/ui/tabs/file_shredder_tab.py`](src/cortex_unified/ui/tabs/file_shredder_tab.py)** (421 LOC)
  - **Purpose**: Tab for file shredder tab in Cortex Cleaner GUI.
  - **Classes (2)**: `FileShredderWorker` (1 methods: `run`), `FileShredderTab` (13 methods: `setup_ui`, `_sync_list`, `add_files_to_shred`, `add_folder_to_shred`)

- [ ] **333. [`src/cortex_unified/ui/tabs/heuristics_tab.py`](src/cortex_unified/ui/tabs/heuristics_tab.py)** (382 LOC)
  - **Purpose**: Tab for heuristics tab in Cortex Cleaner GUI.
  - **Classes (3)**: `BadFilesWorker` (1 methods: `run`), `HeuristicsScanWorker` (1 methods: `run`), `HeuristicsTab` (7 methods: `browse_heuristics_path`, `start_heuristics_scan`, `start_bad_files_scan`, `_teardown_worker`)

- [ ] **334. [`src/cortex_unified/ui/tabs/large_files_tab.py`](src/cortex_unified/ui/tabs/large_files_tab.py)** (329 LOC)
  - **Purpose**: Tab for large files tab in Cortex Cleaner GUI.
  - **Classes (2)**: `LargeFileFinderWorker` (1 methods: `run`), `LargeFilesTab` (9 methods: `setup_ui`, `_on_selection_changed`, `select_all`, `deselect_all`)

- [ ] **335. [`src/cortex_unified/ui/tabs/package_manager_tab.py`](src/cortex_unified/ui/tabs/package_manager_tab.py)** (684 LOC)
  - **Purpose**: Tab for package manager tab in Cortex Cleaner GUI.
  - **Classes (4)**: `PMSearchWorker` (1 methods: `run`), `PMScanWorker` (1 methods: `run`), `PMCleanWorker` (1 methods: `run`), `PackageManagerTab` (14 methods: `setup_ui`, `detect_package_managers`, `_on_detect_finished`, `_on_detect_error`)

- [ ] **336. [`src/cortex_unified/ui/tabs/privacy_tab.py`](src/cortex_unified/ui/tabs/privacy_tab.py)** (615 LOC)
  - **Purpose**: Privacy Shield tab — comprehensive browser and system privacy management.
  - **Classes (3)**: `BrowserScanWorker` (1 methods: `run`), `ExifScanWorker` (1 methods: `run`), `PrivacyTab` (15 methods: `setup_ui`, `setup_tooltips`, `_refresh_telemetry`, `_apply_block`)

- [ ] **337. [`src/cortex_unified/ui/tabs/process_analyzer_tab.py`](src/cortex_unified/ui/tabs/process_analyzer_tab.py)** (159 LOC)
  - **Purpose**: Tab for process analyzer tab in Cortex Cleaner GUI.
  - **Classes (2)**: `ProcessAnalyzerWorker` (1 methods: `run`), `ProcessAnalyzerTab` (4 methods: `setup_ui`, `refresh_processes`, `_on_scan_finished`, `_on_scan_error`)

- [ ] **338. [`src/cortex_unified/ui/tabs/registry_cleaner_tab.py`](src/cortex_unified/ui/tabs/registry_cleaner_tab.py)** (236 LOC)
  - **Purpose**: Tab for registry cleaner tab in Cortex Cleaner GUI.
  - **Classes (3)**: `RegistryScanWorker` (1 methods: `run`), `RegistryCleanWorker` (1 methods: `run`), `RegistryCleanerTab` (6 methods: `setup_ui`, `scan_registry`, `_on_scan_finished`, `_on_error`)

- [ ] **339. [`src/cortex_unified/ui/tabs/reports_tab.py`](src/cortex_unified/ui/tabs/reports_tab.py)** (640 LOC)
  - **Purpose**: Tab for reports tab in Cortex Cleaner GUI.
  - **Classes (1)**: `ReportsTab` (16 methods: `setup_ui`, `_zoom_in`, `_zoom_out`, `_zoom_reset`)

- [ ] **340. [`src/cortex_unified/ui/tabs/resource_monitor_tab.py`](src/cortex_unified/ui/tabs/resource_monitor_tab.py)** (339 LOC)
  - **Purpose**: Tab for resource monitor tab in Cortex Cleaner GUI.
  - **Classes (1)**: `ResourceMonitorTab` (7 methods: `setup_ui`, `start_resource_monitoring`, `stop_resource_monitoring`, `update_resource_metrics`)

- [ ] **341. [`src/cortex_unified/ui/tabs/restore_tab.py`](src/cortex_unified/ui/tabs/restore_tab.py)** (535 LOC)
  - **Purpose**: Tab for restore tab in Cortex Cleaner GUI.
  - **Classes (2)**: `RestoreWorker` (1 methods: `run`), `RestoreTab` (13 methods: `setup_ui`, `_on_table_selection`, `refresh_manifests`, `refresh_vss`)

- [ ] **342. [`src/cortex_unified/ui/tabs/scheduler_tab.py`](src/cortex_unified/ui/tabs/scheduler_tab.py)** (562 LOC)
  - **Purpose**: Tab for scheduler tab in Cortex Cleaner GUI.
  - **Classes (2)**: `AddTaskDialog`, `SchedulerTab` (15 methods: `setup_ui`, `create_tasks_subtab`, `_refresh_tasks`, `_add_task`)

- [ ] **343. [`src/cortex_unified/ui/tabs/security_scanner_tab.py`](src/cortex_unified/ui/tabs/security_scanner_tab.py)** (875 LOC)
  - **Purpose**: Tab for Sentinel Pro security scanner in Cortex Cleaner GUI.
  - **Classes (6)**: `SentinelScanWorker` (1 methods: `run`), `VerifyWorker` (1 methods: `run`), `BaselineWorker` (1 methods: `run`), `ExportWorker` (1 methods: `run`), `DashboardWorker` (1 methods: `run`)

- [ ] **344. [`src/cortex_unified/ui/tabs/settings_tab.py`](src/cortex_unified/ui/tabs/settings_tab.py)** (137 LOC)
  - **Purpose**: Tab for settings tab in Cortex Cleaner GUI.
  - **Classes (1)**: `SettingsTab` (2 methods: `setup_ui`, `save_settings`)

- [ ] **345. [`src/cortex_unified/ui/tabs/startup_manager_tab.py`](src/cortex_unified/ui/tabs/startup_manager_tab.py)** (163 LOC)
  - **Purpose**: Tab for startup manager tab in Cortex Cleaner GUI.
  - **Classes (2)**: `StartupScanWorker` (1 methods: `run`), `StartupManagerTab` (6 methods: `setup_ui`, `_on_selection`, `refresh_startup_items`, `_on_scan_finished`)

- [ ] **346. [`src/cortex_unified/ui/tabs/system_tools_tab.py`](src/cortex_unified/ui/tabs/system_tools_tab.py)** (315 LOC)
  - **Purpose**: Tab for system tools tab in Cortex Cleaner GUI.
  - **Classes (3)**: `LanScanWorker` (1 methods: `run`), `WanAuditWorker` (1 methods: `run`), `SystemToolsTab` (6 methods: `setup_ui`, `create_network_tools_subtab`, `_run_lan_scan`, `_run_wan_audit`)

- [ ] **347. [`src/cortex_unified/ui/tabs/uninstaller_tab.py`](src/cortex_unified/ui/tabs/uninstaller_tab.py)** (568 LOC)
  - **Purpose**: Deep Uninstaller tab — safe app removal + residual cleanup.
  - **Classes (4)**: `AppListWorker` (1 methods: `run`), `ResidualScanWorker` (1 methods: `run`), `ResidualCleanWorker` (1 methods: `run`), `UninstallerTab` (15 methods: `setup_ui`, `setup_tooltips`, `_load_apps`, `_on_apps_loaded`)

## Diagnostics & Automation Scripts

- [ ] **348. [`scripts/audit_all_page_functions.py`](scripts/audit_all_page_functions.py)** (91 LOC)
  - **Purpose**: Deep Functional & UI Inspection across all 59 Pages.
  - **Exported Functions (1)**: `audit_all_pages`

- [ ] **349. [`scripts/audit_imports.py`](scripts/audit_imports.py)** (144 LOC)
  - **Purpose**: Static import health audit for the cortex_unified package.
  - **Exported Functions (2)**: `module_symbols`, `get_syms`

- [ ] **350. [`scripts/audit_pages.py`](scripts/audit_pages.py)** (27 LOC)
  - **Purpose**: Audit script to verify that all registered pages load their factory classes.

- [ ] **351. [`scripts/audit_system_tools.py`](scripts/audit_system_tools.py)** (23 LOC)
  - **Purpose**: Audit script to inspect classes and functions across all system tools.

- [ ] **352. [`scripts/build_exe.py`](scripts/build_exe.py)** (96 LOC)
  - **Purpose**: Compile run_gui.py into a distributable Windows executable via PyInstaller.
  - **Exported Functions (2)**: `calculate_sha256`, `build_app`

- [ ] **353. [`scripts/check_all_structure_files.py`](scripts/check_all_structure_files.py)** (186 LOC)
  - **Purpose**: Deep, exhaustive, file-by-file verification of every program file in structure.txt.
  - **Exported Functions (3)**: `find_all_python_files`, `verify_file`, `main`

- [ ] **354. [`scripts/check_hardcoded_paths.py`](scripts/check_hardcoded_paths.py)** (29 LOC)
  - **Purpose**: Diagnostic script to check for hardcoded Windows paths.
  - **Exported Functions (1)**: `analyze_paths`

- [ ] **355. [`scripts/check_lint_issues.py`](scripts/check_lint_issues.py)** (88 LOC)
  - **Purpose**: Diagnostic script to check for undefined names and lint anomalies.
  - **Exported Functions (1)**: `check_undefined_names_in_file`

- [ ] **356. [`scripts/deep_codebase_inspection.py`](scripts/deep_codebase_inspection.py)** (174 LOC)
  - **Purpose**: Deep exhaustive codebase inspector.
  - **Exported Functions (2)**: `scan_file`, `main`

- [ ] **357. [`scripts/deep_inspect_placeholders.py`](scripts/deep_inspect_placeholders.py)** (56 LOC)
  - **Purpose**: Deep inspector for placeholders, TODOs, stubs, and mocks across all src/ files.

- [ ] **358. [`scripts/generate_app_icon.py`](scripts/generate_app_icon.py)** (114 LOC)
  - **Purpose**: Generate a high-resolution, multi-layer Windows .ico and .png brand icon.
  - **Exported Functions (2)**: `create_cortex_icon`, `main`

- [ ] **359. [`scripts/generate_complete_features.py`](scripts/generate_complete_features.py)** (218 LOC)
  - **Purpose**: Generate the master exhaustive COMPLETE_FEATURES_CHECKLIST.md covering every feature and module.
  - **Exported Functions (1)**: `get_module_info`

- [ ] **360. [`scripts/generate_feature_directory.py`](scripts/generate_feature_directory.py)** (55 LOC)
  - **Purpose**: Generate docs/FEATURE_DIRECTORY.md listing all 118 UI pages across all groups.

- [ ] **361. [`scripts/generate_master_inventory_and_docs.py`](scripts/generate_master_inventory_and_docs.py)** (443 LOC)
  - **Purpose**: Master Codebase Auditor & Documentation Generator.
  - **Exported Functions (7)**: `parse_py_file`, `gather_all_codebase`, `get_registered_gui_pages`, `generate_inventory_markdown`, `generate_master_reference_markdown`, `generate_comprehensive_documentation`, `main`

- [ ] **362. [`scripts/generate_program_checklist.py`](scripts/generate_program_checklist.py)** (130 LOC)
  - **Purpose**: Generate an exhaustive, program-file-by-program-file verification checklist.
  - **Exported Functions (1)**: `parse_file`

- [ ] **363. [`scripts/generate_sbom.py`](scripts/generate_sbom.py)** (121 LOC)
  - **Purpose**: Generate an SPDX 2.3 compliant Software Bill of Materials (SBOM) for Cortex Workstation.
  - **Exported Functions (3)**: `get_file_sha256`, `generate_sbom`, `main`

- [ ] **364. [`scripts/installer.py`](scripts/installer.py)** (654 LOC)
  - **Purpose**: Cortex Workstation Windows Setup Installer with Cyberpunk Infiltration Progress Bar.
  - **Classes (2)**: `InstallWorker` (1 methods: `run`), `InstallerApp` (10 methods: `_set_app_icon`, `_center_window`, `_build_ui`, `_load_html_content`)
  - **Exported Functions (4)**: `get_bundle_zip`, `create_shortcut`, `register_uninstaller`, `main`

- [ ] **365. [`scripts/scan_codebase.py`](scripts/scan_codebase.py)** (40 LOC)
  - **Purpose**: Scanner script to detect placeholders, TODOs, and mock patterns.

- [ ] **366. [`scripts/stress_test_gui_all_actions.py`](scripts/stress_test_gui_all_actions.py)** (215 LOC)
  - **Purpose**: Deep interactive action stress-test for Cortex Cleaner GUI.
  - **Exported Functions (2)**: `pump_events`, `main`

- [ ] **367. [`scripts/test_all_pages.py`](scripts/test_all_pages.py)** (40 LOC)
  - **Purpose**: Diagnostic script to verify offscreen instantiation of all UI pages.

- [ ] **368. [`scripts/test_navigation.py`](scripts/test_navigation.py)** (32 LOC)
  - **Purpose**: Diagnostic script to test UI navigation and theme application.

- [ ] **369. [`scripts/update_structure_txt.py`](scripts/update_structure_txt.py)** (84 LOC)
  - **Purpose**: Generate an up-to-date, clean structure.txt of the entire repository.
  - **Exported Functions (2)**: `build_tree`, `main`

- [ ] **370. [`scripts/verify_modules.py`](scripts/verify_modules.py)** (96 LOC)
  - **Purpose**: Quick functional verification of core system modules.

- [ ] **371. [`scripts/verify_production_readiness.py`](scripts/verify_production_readiness.py)** (29 LOC)
  - **Purpose**: Comprehensive Production Readiness & Diagnostics Verification Suite.

## Root Launchers & Application Entrypoints

- [ ] **372. [`run_gui.py`](run_gui.py)** (119 LOC)
  - **Purpose**: Launch the Cortex Workstation GUI from a source checkout.
  - **Classes (1)**: `_SafeStream` (2 methods: `write`, `flush`)
  - **Exported Functions (1)**: `main`
