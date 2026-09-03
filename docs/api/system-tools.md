# 🛠️ System Tools & Forensics Reference

Technical interface specifications for the **62 standalone Windows NT diagnostic and optimization modules** in `cortex_unified.system_tools`.

---

## 🌟 Featured Next-Gen System Tools

### 1. `DirectStorageOptimizer`
* **Module:** `cortex_unified.system_tools.directstorage_optimizer`
* **Key Methods:**
  * `audit_volume(volume_letter: str) -> BypassIOAudit`: Queries Windows `fsutil bypassIo state` to verify hardware NVMe and storage stack support.
  * `inspect_filter_drivers() -> list[FilterDriver]`: Audits filesystem minifilter drivers that may block GPU asset streaming.

### 2. `MemoryStandbyPurger`
* **Module:** `cortex_unified.system_tools.memory_standby_purger`
* **Key Methods:**
  * `get_memory_snapshot() -> MemorySnapshot`: Retrieves detailed working set, standby list, and modified page counts via `NtQuerySystemInformation`.
  * `purge_standby_list() -> OperationResult`: Invokes `NtSetSystemInformation` with `SystemMemoryListInformation` to purge inactive standby cache pages safely.

### 3. `MftSlackScrubber`
* **Module:** `cortex_unified.system_tools.mft_slack_scrubber`
* **Key Methods:**
  * `audit_mft(drive_letter: str) -> MftAuditResult`: Scans NTFS Master File Table record slack space for lingering residual metadata.
  * `scrub_slack(drive_letter: str, dry_run: bool = True) -> OperationResult`: Overwrites slack space in unallocated MFT clusters.

### 4. `SrumBamCleaner`
* **Module:** `cortex_unified.system_tools.srum_bam_cleaner`
* **Key Methods:**
  * `query_bam_entries() -> list[BamEntry]`: Parses Background Activity Moderator (BAM) registry hives for execution history.
  * `query_srum_records() -> list[SrumRecord]`: Reads System Resource Usage Monitor ESE database statistics.

### 5. `WinApp2Cleaner`
* **Module:** `cortex_unified.system_tools.winapp2_cleaner`
* **Key Methods:**
  * `load_definitions(path: str) -> int`: Parses multi-thousand community WinApp2.ini definitions.
  * `scan(dry_run: bool = True) -> list[CleanFinding]`: Safely audits third-party application caches.
