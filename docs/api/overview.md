# 🔌 Subsystem Core Overview & Architecture

Authoritative breakdown of Cortex Workstation's core subsystem architecture, lifecycle methods, and module contracts.

---

## 🏛️ Subsystem Core Matrix

| Subsystem Module | Primary Interface Classes | Core Lifecycle Functions | Extension & Safety Rules |
| :--- | :--- | :--- | :--- |
| **`cortex_unified.core.engine`** | `Engine`, `SmartScanner` | `scan()`, `clean()`, `cancel()` | Strict non-blocking async execution. All filesystem deletions must route through `PathGuard`. |
| **`cortex_unified.system_tools`** | `DirectStorageOptimizer`,<br>`VssHealthAnalyzer`,<br>`MftSlackScrubber` | `scan()`, `audit()`, `optimize()` | Pure read-only discovery by default. System mutations require explicit confirmation. |
| **`cortex_unified.analyzers`** | `PerceptualDuplicateFinder`,<br>`FuzzyFinder`,<br>`ContentDefinedChunker` | `find_duplicates()`, `hash_file()` | Low-memory streaming algorithms with cooperative thread cancellation checkpoints. |
| **`NexusExplorer.native`** | `NexusCore`, `UndoStack`,<br>`USNJournalScanner` | `read_directory()`, `copy_batch()`,<br>`record_undo()` | Fully transactional operations with persistent undo/redo history. |
| **`cortex_unified.ui.premium`** | `PremiumMainWindow`,<br>`PageSpec`, `TableBinding` | `load()`, `_refresh()`, `_run()` | Zero eager imports during bootstrap. All 139 tools load lazily on navigation. |

---

## 🧭 Subsystem Deep-Dives
* **[System Tools Reference](system-tools.md):** 62 standalone OS optimization and forensic modules.
* **[Analyzers Reference](analyzers.md):** 23 deduplication, perceptual hashing, and similarity engines.
* **[Core Engine & Algorithmic Caches](core-engine.md):** S3-FIFO, SIEVE cache, FastCDC, and process orchestrator.
