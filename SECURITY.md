# Security Policy & Safe Execution Model

Cortex Workstation is designed for deep Windows system maintenance, forensic file analysis, and optimization. Because certain modules interact with low-level Windows NT subsystems, kernel drivers, and registry hives, security and stability are fundamental priorities.

---

## 1. Supported Versions

Security patches and bug fixes are actively provided for the following releases:

| Version | Supported | Status |
| :--- | :--- | :--- |
| **1.2.x (Latest)** | :white_check_mark: | Active Development |
| < 1.2.0 | :x: | Deprecated |

---

## 2. Core Security & Safety Principles

### Least Privilege Execution
Cortex Workstation is designed to launch under a standard user account. Most diagnostic, forensic auditing, duplicate detection, and user profile cleanup tools function completely without administrative rights.
When elevated permissions are required (e.g., managing VSS Shadow Copies, cleaning the Windows Driver Store, or modifying system-wide services), the application prompts for standard Windows User Account Control (UAC) elevation.

### Non-Destructive Scanning
All initial scan passes across every module (Temp Cleaner, Registry AI, Junction Auditor, BitRot Scrubber, SMB Share Auditor) are **strictly read-only**. They do not modify files, reconfigure services, or alter registry values during analysis.

### Safe Link Traversal & Unlinking
When auditing NTFS reparse points, directory junctions, and symlinks, Cortex Workstation:
1. Detects circular loops to prevent infinite recursive traversal.
2. Refuses to traverse or follow junction points and directory symlinks during recursive deletion.
3. Unlinks directory junctions using `os.rmdir` (which removes only the reparse mount point link without deleting files within the target folder).

### Safe Cryptographic Hashing
File integrity and duplicate detection modules use non-destructive streaming SHA-256 and BLAKE3 hash algorithms with bounded buffer sizes (256 KB) to prevent memory exhaustion on multi-gigabyte files.

---

## 3. Safe Execution Architecture for Destructive & Kernel Operations

Cortex Workstation enforces concrete, programmatically verified guardrails across all high-risk, kernel-level, and filesystem-modifying operations:

### 3.1 PathGuard Protection Engine (`src/cortex_unified/engine/guard.py:89-155`)
- **Algorithmic Path Confinement**: Discards brittle prefix matching in favor of real path-relationship checks (`Path.is_relative_to`), preventing sibling bypasses (e.g., `/usrdata` vs `/usr`).
- **Protected Windows Subsystem Directories**: Refuses operations targeting filesystem/drive roots (`C:\`), user profile roots (`C:\Users\<user>`), or Windows system directories:
  - `C:\Windows` (and all subdirectories, including `System32`, `SysWOW64`, `WinSxS`)
  - `C:\Program Files` and `C:\Program Files (x86)`
  - `C:\ProgramData`
  - `C:\System Volume Information`
  - `C:\$Recycle.Bin`
  - `C:\Recovery`
  - `C:\Users\Default` and `C:\Users\Public`

### 3.2 Non-Destructive Dry-Run & Safe Deletion (`src/cortex_unified/core/deleter.py:26-96`)
- **Dry-Run by Default**: `Deleter(dry_run=True)` defaults to non-destructive recording. Disk modifications require explicit programmatic or user toggling (`dry_run=False`).
- **Fail-Closed Recycle Bin Guard**: If `use_trash=True` is requested but `send2trash` is missing or fails to load, `Deleter` raises a fail-closed `RuntimeError` immediately, refusing irreversible deletion.
- **Junction & Symlink Barrier**: Deletion operations explicitly refuse reparse points and directory symlinks, preventing unintended deletion of destination targets.

### 3.3 Fail-Closed Registry Backup & Rollback (`src/cortex_unified/system_tools/registry_cleaner.py:20-31, 350-480`)
- **Subsystem Key Exclusions**: Hardcoded blacklist (`PROTECTED_REGISTRY_KEYS`) prevents modification of critical OS hives:
  - `Winlogon`
  - `SYSTEM\CurrentControlSet\Services`
  - `SYSTEM\CurrentControlSet\Control\Lsa`
  - `SYSTEM\CurrentControlSet\Control\Session Manager`
  - `KnownDLLs`
  - `BCD00000000`
  - `SAM` and `SECURITY`
  - `Policies`
- **Mandatory Pre-Mutation Rollback Export**: Every targeted key is exported to a verified, timestamped `.reg` file prior to deletion via `backup_entry()`.
- **Fail-Closed Verification**: If the backup export command fails or produces a zero-byte file, deletion is immediately aborted (`return False`), guaranteeing no orphaned key is removed without an active rollback point.
- **Transactional Restoration**: Full rollback is supported via `restore_backup(backup_file)` using native `reg import`.

### 3.4 Windows NT Kernel Memory Purger (`src/cortex_unified/system_tools/memory_standby_purger.py:177-230`)
- **Native NT System Calls**: Uses `NtSetSystemInformation (Class 80 / SystemMemoryListInformation)` to flush standby pages, working sets, and modified page lists.
- **Privilege Token Adjustment**: Programmatically acquires `SE_PROFILE_SINGLE_PROCESS_NAME` and `SE_INCREASE_QUOTA_NAME` via Win32 token adjustment APIs (`OpenProcessToken`, `AdjustTokenPrivileges`).
- **Pre/Post Memory Snapshot Verification**: Captures `GlobalMemoryStatusEx` before and after invocation to measure reclaimed physical memory safely.
- **NTSTATUS Code Handling**: Validates `STATUS_SUCCESS (0x00000000)` and fails closed with clear diagnostic diagnostics if `STATUS_PRIVILEGE_NOT_HELD (0xC0000061)` is encountered.

### 3.5 Windows Search Index Database Compactor (`src/cortex_unified/system_tools/search_index_optimizer.py:102-160`)
- **Managed Offline Defragmentation**: Safely stops the `WSearch` service before invoking `esentutl.exe /d` on `Windows.edb`, with bounded timeouts (15s for service stop, 120s for defragmentation).
- **Service Recovery Invariant**: Guarantees restarting the `WSearch` service regardless of defragmentation outcome.
- **Explicit User Confirmation**: UI triggers require explicit modal approval dialogs (`Confirm Database Compaction`, `Confirm Index Rebuild`) before executing.

### 3.6 Volume Shadow Copy (VSS) Management (`src/cortex_unified/system_tools/vss_manager.py:275-338`)
- **Non-Destructive Snapshot Creation**: Creates on-demand VSS restore points (`create_shadow_copy`) prior to bulk disk operations.
- **Selective Pruning**: Snapshot reclamation targets only the oldest single shadow copy (`delete_oldest_shadow` with `/oldest /quiet`), preventing mass deletion of backup points.

### 3.7 Automated Safety Regression Suite (`tests/test_audit_safety_hardening.py`)
All safety invariants above are continuously verified by automated tests covering:
- Protected system path refusal (`test_deleter_refuses_protected_path`, `test_advanced_shredder_refuses_protected_path`)
- Directory symlink & junction rejection (`test_deleter_refuses_symlink_directory`, `test_deleter_refuses_mocked_symlink_directory`)
- Protected registry key blocking (`test_registry_cleaner_blocks_protected_keys`)
- Fail-closed registry rollback behavior (`test_registry_cleaner_fail_closed_on_backup_failure`)
- Fail-closed recycle bin behavior (`test_deleter_fail_closed_when_send2trash_missing`)

---

## 4. Reporting a Vulnerability

If you discover a security vulnerability or critical privilege escalation flaw within Cortex Workstation, please report it responsibly:

1. **Do not open a public GitHub issue.**
2. Send an email to the security response team: `security@cortex-workstation.io` (or open a confidential GitHub Security Advisory via the repository's **Security** tab).
3. Include:
   - Detailed description of the vulnerability.
   - Steps to reproduce or proof-of-concept script.
   - Impact assessment (e.g., privilege escalation, unexpected data loss).
4. Our team will acknowledge receipt within 48 hours and coordinate a patch release prior to public disclosure.
