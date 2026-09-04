# ⚙️ Core Engine & Algorithmic Caches Reference

Technical specifications for Cortex Workstation's algorithmic caching data structures and engine coordination subsystems.

---

## ⚡ High-Throughput Eviction Caches

### 1. `S3FifoCache`
* **Module:** `cortex_unified.system_tools.s3_fifo`
* **Architecture:** State-of-the-art Simple, Scalable, Small (S3-FIFO) cache with small FIFO ($S$), main FIFO ($M$), and ghost FIFO ($G$) queues.
* **Key Properties:**
  * Drastically reduces cache pollution from "one-hit wonder" scan operations.
  * Achieves higher hit-ratios than traditional LRU while requiring zero mutex lock contention during read hits.
* **Methods:**
  * `get(key: str) -> Any | None`
  * `put(key: str, value: Any)`
  * `stats() -> CacheStats`

### 2. `SieveCache`
* **Module:** `cortex_unified.system_tools.sieve_cache`
* **Architecture:** SIEVE cache eviction algorithm using a circular queue hand pointer with visited bits.
* **Key Properties:**
  * Ultra-lightweight with $O(1)$ amortized eviction time.
  * Ideal for rapid metadata indexing in directory walkers.

---

## 🚀 Orchestration Engine

* **Module:** `cortex_unified.core.engine`
* **Class:** `Engine`
* **Key Methods:**
  * `scan(categories: list[str]) -> ScanReport`: Executes asynchronous multi-threaded discovery across all enabled system cleaner plugins.
  * `clean(report: ScanReport, options: CleanOptions) -> CleanReport`: Dispatches safe deletion tasks with automatic manifest recording and rollback checkpoints.
