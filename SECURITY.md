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
When auditing NTFS reparse points, directory junctions, and symlinks, Cortex Cleaner:
1. Detects circular loops to prevent infinite recursive traversal.
2. Unlinks directory junctions using `os.rmdir` (which removes only the mount point link without deleting files within the target folder).

### Safe Cryptographic Hashing
File integrity and duplicate detection modules use non-destructive streaming SHA-256 and BLAKE3 hash algorithms with bounded buffer sizes (256 KB) to prevent memory exhaustion on multi-gigabyte files.

---

## 3. Reporting a Vulnerability

If you discover a security vulnerability or critical privilege escalation flaw within Cortex Cleaner, please report it responsibly:

1. **Do not open a public GitHub issue.**
2. Send an email to the security response team: `security@cortexcleaner.dev` (or open a confidential GitHub Security Advisory via the repository's **Security** tab).
3. Include:
   - Detailed description of the vulnerability.
   - Steps to reproduce or proof-of-concept script.
   - Impact assessment (e.g., privilege escalation, unexpected data loss).
4. Our team will acknowledge receipt within 48 hours and coordinate a patch release prior to public disclosure.
