# 🏗️ Cortex Workstation — Architectural Overview

This hub centralizes the technical specifications, data structures, Windows NT kernel integration interfaces, and invariant authorities across Cortex Workstation.

---

## 🏛️ Core Architectural Principles: One Authority Per Invariant

To ensure fail-closed safety and eliminate technical debt across destructive operations and configuration, Cortex Workstation adheres to strict authority boundaries:

| Concern | Authoritative Subsystem | Implementation File | Invariants Enforced |
| :--- | :--- | :--- | :--- |
| **Destructive File Operations** | Engine PathGuard & SecureDeleter | [`cortex_unified.engine.guard`](api/core-engine.md) & [`secure_delete`](api/core-engine.md) | Mandatory path vetting, reparse point & directory junction rejection, dual-phase TOCTOU reduction, non-rotational media honesty. |
| **Destructive Registry Mutations** | RegistryCleaner Rollback Engine | `cortex_unified.system_tools.registry_cleaner` | Protected subsystem key blacklist (`Winlogon`, `Services`, `Lsa`), fail-closed pre-mutation `.reg` export verification, transactional restoration via `restore_backup`. |
| **Configuration** | Modern Config Layer | `cortex_unified.engine.config` | Single source of truth for runtime settings, thresholds, and engine parameters. |
| **Version & Packaging** | Package Metadata & Dynamic Specs | `cortex_unified.__version__` & `cortex.spec` | Canonical version source driving PyInstaller bundles, setup installer, and release checksums. |
| **Inventory & Auditing** | Machine-Generated Artifacts | `scripts/check_all_structure_files.py` | Generates `docs/audit/program_files_inventory.json` directly from repository AST parse, preventing documentation drift. |

---

## 📚 Architectural Guides & Specifications

- **[Windows NT Kernel & Low-Level Spec](ARCHITECTURE.md)**: Deep dive into NTFS/ReFS filesystems, USN Change Journal, kernel memory management, and Win32 tokens.
- **[Repository Architecture Map](dev/architecture.md)**: Layered breakdown from PySide6 presentation to low-level hardware adapters.
- **[State Management & Thread Safety](dev/threading-safety.md)**: Concurrency models, QThreadPool workers, mutex boundaries, and PathGuard policies.
- **[Symbol & Function Inventory](FUNCTION_INVENTORY.md)**: Index of exported classes, methods, and dataclass schemas.
- **[Audit & Verification Hub](audit/ONE_BY_ONE_VERIFICATION_REPORT.md)**: Exhaustive AST syntax, compilation, and import audit reports for all program files.
