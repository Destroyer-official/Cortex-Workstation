# 🔬 File & Deduplication Analyzers Reference

Technical interface specifications for the **23 advanced file, media, and deduplication analyzers** in `cortex_unified.analyzers`.

---

## ⚡ Core Analyzer Classes

### 1. `CzkawkaDuplicateFinder`
* **Module:** `cortex_unified.analyzers.czkawka_duplicate_finder`
* **Algorithm:** 3-stage validation (File Size $\rightarrow$ Header Hash $\rightarrow$ Full BLAKE3 digest).
* **Methods:**
  * `find_duplicates(directories: list[str]) -> list[DuplicateGroup]`
  * `set_exclude_dirs(paths: list[str])`
  * `cancel()`: Immediately halts multi-threaded file walking.

### 2. `PerceptualDuplicateFinder`
* **Module:** `cortex_unified.analyzers.perceptual_duplicate_finder`
* **Algorithm:** Difference Hash (dHash) and Discrete Cosine Transform Perceptual Hash (pHash).
* **Methods:**
  * `compute_hash(image_path: str, kind: str = "phash") -> int`
  * `hamming_distance(hash1: int, hash2: int) -> int`
  * `find_similar(gallery_dir: str, threshold: int = 5) -> list[ImageGroup]`

### 3. `ContentDefinedChunker`
* **Module:** `cortex_unified.analyzers.content_defined_chunker`
* **Algorithm:** FastCDC (Fast Content-Defined Chunking) with Gear hashing and Jaccard similarity index.
* **Methods:**
  * `chunk_file(file_path: str, min_size: int = 2048, avg_size: int = 8192, max_size: int = 32768) -> list[Chunk]`
  * `jaccard_similarity(chunks_a: list[Chunk], chunks_b: list[Chunk]) -> float`

### 4. `FuzzyFinder`
* **Module:** `cortex_unified.analyzers.fuzzy_finder`
* **Algorithm:** Context-Triggered Piecewise Hashing (CTPH / Ssdeep).
* **Methods:**
  * `fuzzy_hash(file_path: str) -> str`
  * `compare_fuzzy(hash1: str, hash2: str) -> int`: Returns similarity score from 0 to 100.
