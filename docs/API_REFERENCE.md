# Cortex Workstation — Core API Reference

This document provides a comprehensive API reference for the core backend modules, system tools, and VFS transport abstractions within the Cortex Workstation codebase.

---

## Table of Contents
1. [Enterprise System Tools (`cortex_unified.system_tools`)](#1-enterprise-system-tools)
2. [Core Engines (`cortex_unified.core`)](#2-core-engines)
3. [Nexus Explorer Native VFS (`NexusExplorer.native`)](#3-nexus-explorer-native-vfs)
4. [UI Registry & Presentation Contracts (`cortex_unified.ui.premium`)](#4-ui-registry--presentation-contracts)

---

## 1. Enterprise System Tools

### `vss_manager.VssManager`
Manages Volume Shadow Copy (VSS) snapshots and shadow storage allocations.

```python
class VssManager:
    def audit(self) -> VssAuditReport:
        """Discovers all active VSS snapshots and storage metrics across volumes."""

    def create_shadow_copy(self, volume: str = "C:") -> tuple[bool, str]:
        """Creates an on-demand volume shadow copy snapshot."""

    def delete_oldest_shadow(self, volume: str = "C:") -> tuple[bool, str]:
        """Safely removes the oldest shadow snapshot on the specified volume."""

    def resize_shadow_storage(self, volume: str, max_size_bytes: int) -> tuple[bool, str]:
        """Configures the maximum shadow copy allocation limit for a volume."""
```

### `dev_drive_optimizer.DevDriveOptimizer`
Inspects ReFS Dev Drives, verifies Copy-on-Write (CoW) block cloning, and monitors Defender Performance Mode.

```python
class DevDriveOptimizer:
    def audit(self) -> DevDriveAuditReport:
        """Audits all volumes for ReFS, Dev Drive flags, and block cloning support."""

    def verify_block_cloning(self, test_dir: str) -> tuple[bool, str]:
        """Executes FSCTL_DUPLICATE_EXTENTS_TO_FILE to verify zero-copy CoW speed."""
```

### `bitlocker_auditor.BitLockerAuditor`
Forensic hardware and volume encryption auditor.

```python
class BitLockerAuditor:
    def audit(self) -> BitLockerAuditReport:
        """Audits encryption status, cipher algorithm (XTS-AES), and key protectors."""
```

### `junction_auditor.JunctionAuditor`
Forensic auditor for NTFS junctions, symbolic links, and reparse tags.

```python
class JunctionAuditor:
    def audit(self, root_path: Optional[str] = None, max_depth: int = 4) -> JunctionAuditReport:
        """Scans directory trees for directory junctions, dead links, and circular loops."""

    def remove_dead_junction(self, link_path: str) -> tuple[bool, str]:
        """Safely unlinks orphaned junction points without deleting target directory."""
```

### `bitrot_scrubber.BitRotScrubber`
Silent bitrot and cryptographic file integrity manager.

```python
class BitRotScrubber:
    def __init__(self, db_path: Optional[str] = None):
        """Initializes SQLite cryptographic integrity baseline database."""

    def scrub(self, target_dir: str, max_files: int = 5000) -> BitRotScrubReport:
        """Compares live SHA-256 hashes against baseline, flagging silent bit mutations."""

    def reset_baseline(self, target_dir: Optional[str] = None):
        """Purges historical hash baselines for the specified directory."""
```

### `memory_compression_tuner.MemoryCompressionTuner`
Windows Memory Compression (MMAgent) and RAM working set optimizer.

```python
class MemoryCompressionTuner:
    def audit(self) -> MemoryTunerReport:
        """Measures compressed memory store size, commit ratios, and MMAgent flags."""

    def set_memory_compression(self, enable: bool) -> tuple[bool, str]:
        """Enables or disables Windows memory compression via Enable-MMAgent/Disable-MMAgent."""
```

### `sandbox_cleaner.SandboxCleaner`
Purger for Windows Sandbox, Hyper-V saved states, and WSL2 swap containers.

```python
class SandboxCleaner:
    def scan(self) -> SandboxCleanReport:
        """Discovers leftover sandbox containers, differencing disks, and checkpoint files."""

    def clean(self, target_paths: list[str]) -> tuple[int, list[str]]:
        """Removes specified virtual artifacts, returning reclaimed byte count."""
```

### `smb_share_auditor.SmbShareAuditor`
Network share and SMB protocol exposure auditor.

```python
class SmbShareAuditor:
    def audit(self) -> SmbSecurityReport:
        """Discovers local SMB shares, admin shares, and audits SMBv1 vulnerability status."""
```

### `process_token_auditor.ProcessTokenAuditor`
Win32 process security token and privilege inspector.

```python
class ProcessTokenAuditor:
    def audit(self, max_processes: int = 150) -> ProcessTokenAuditReport:
        """Inspects process TokenIntegrityLevels, elevation types, and dangerous privileges."""
```

### `storage_growth_tracker.StorageGrowthTracker`
Storage growth snapshot and timeline differ.

```python
class StorageGrowthTracker:
    def take_snapshot(self, root_path: str, label: str = "Manual Scan") -> SnapshotSummary:
        """Records persistent folder footprint and file counts into SQLite."""

    def list_snapshots(self) -> list[SnapshotSummary]:
        """Lists historical snapshots ordered by timestamp descending."""

    def compare_snapshots(self, base_id: int, target_id: int) -> StorageGrowthDiffReport:
        """Calculates differential growth deltas (+GB/-GB) between any two snapshots."""
```

### `winapp2_cleaner.Winapp2Cleaner`
Declarative deep cleaner for 500+ desktop applications, gaming platforms, and development tools via Winapp2.ini.

```python
class Winapp2Cleaner:
    def scan(self, on_progress=None) -> Winapp2Report:
        """Evaluates declarative rules against installed software on the system."""

    def clean(self, entries: list[Winapp2Entry], on_progress=None) -> tuple[int, int]:
        """Safely removes discovered cache entries, returning (bytes_freed, files_removed)."""
```

### `srum_bam_cleaner.SrumBamCleaner`
Windows BAM/DAM kernel execution forensics auditor and SRUM database manager.

```python
class SrumBamCleaner:
    def audit(self) -> SrumBamReport:
        """Parses BAM/DAM registry entries and inspects SRUDB.dat metrics."""

    def clean_bam_traces(self) -> tuple[bool, str]:
        """Sanitizes user and system BAM/DAM application execution history."""
```

### `directstorage_optimizer.DirectStorageOptimizer`
Windows 11 BypassIO and NVMe-to-GPU DirectStorage acceleration validator.

```python
class DirectStorageOptimizer:
    def audit(self, volume: str = "C:") -> DirectStorageAuditReport:
        """Queries fsutil bypassio state and identifies blocking storage minifilters."""
```

### `memory_standby_purger.MemoryStandbyPurger`
Native Windows NT kernel memory standby list and process working set compactor.

```python
class MemoryStandbyPurger:
    def purge_standby_list(self) -> tuple[bool, str]:
        """Invokes NtSetSystemInformation (Class 80) with MemoryPurgeStandbyList."""

    def empty_working_sets(self) -> tuple[bool, str]:
        """Flushes all process working sets to physical memory via MemoryEmptyWorkingSets."""
```

### `mft_slack_scrubber.MftSlackScrubber`
NTFS Master File Table ($MFT) record slack space and directory index scrubber.

```python
class MftSlackScrubber:
    def audit(self) -> MftScrubReport:
        """Audits NTFS cluster geometry and estimates unallocated MFT slack records."""

    def scrub(self) -> MftScrubReport:
        """Sanitizes resident deleted filename and data slack in accordance with NIST 800-88."""
```

### `search_index_optimizer.SearchIndexOptimizer`
Windows Search service (WSearch) and `Windows.edb` ESENT database optimizer.

```python
class SearchIndexOptimizer:
    def get_status(self) -> SearchIndexStatus:
        """Inspects Windows.edb file size, indexed item count, and service state."""

    def compact_database(self) -> tuple[bool, str]:
        """Performs offline ESENT B-tree defragmentation via esentutl /d."""

    def rebuild_index(self) -> tuple[bool, str]:
        """Forces a clean reset and full catalog rebuild of the Windows search index."""
```

---

## 2. Core Engines

### `smart_scanner.SmartScanner`
The central orchestrator for 1-click system diagnostic and cleanup passes.

```python
class SmartScanner:
    def run_full_scan(self, on_progress=None) -> ScanResultReport:
        """Orchestrates system cache, temp folder, browser, and registry scans."""
```

### `deleter.Deleter`
Safe file and directory removal subsystem supporting Recycle Bin and permanent shredding.

```python
class Deleter:
    @staticmethod
    def safe_delete(path: Path | str, to_recycle_bin: bool = True) -> tuple[bool, str]:
        """Safely removes file, routing to Windows Recycle Bin via Shell API by default."""
```

---

## 3. Nexus Explorer Native VFS

### `usn_journal_scanner.UsnJournalScanner`
NTFS Change Journal reader for lightning-fast volume indexing.

```python
class UsnJournalScanner:
    def read_journal_records(self, volume: str = "C:") -> list[UsnRecord]:
        """Reads NTFS USN Change Journal records directly using DeviceIoControl."""
```

### `par2_recovery.Par2Recovery`
PAR2 Reed-Solomon packet error correction codec.

```python
class Par2Recovery:
    def create_recovery_set(self, source_file: str, redundancy_percent: int = 10) -> list[str]:
        """Generates parity volumes (.par2) for archival file corruption protection."""

    def verify_and_repair(self, par2_file: str) -> bool:
        """Verifies cryptographic block checksums and repairs corrupted sectors."""
```

---

## 4. UI Registry & Presentation Contracts

### `registry.PageSpec`
```python
@dataclass(frozen=True)
class PageSpec:
    id: str           # Unique alphanumeric page identifier
    title: str        # Display label rendered in navigation sidebar
    icon: str         # Basename of the SVG icon in resources/icons/
    group: str        # Target navigation section ID
    factory: str      # Import specifier in 'module.path:ClassName' format
```
