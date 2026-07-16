"""Cortex Cleaner high-performance engine.

A cohesive, fully-typed, production-grade core that supersedes the older
scattered scanner/deleter/security modules. Everything here is designed to be:

* **Fast**    - ``os.scandir``-based traversal (2-20x faster than ``os.walk``,
                per PEP 471) with a size-prefilter before any hashing.
* **Honest**  - storage-aware secure deletion. Multi-pass overwrite is only
                meaningful on rotational (HDD) media; on SSD/NVMe it is
                ineffective *and* harmful, so we detect the medium and refuse
                to lie about it.
* **Safe**    - every destructive path passes through :class:`PathGuard`, which
                uses real path-relationship checks (not naive string prefixes).
* **Robust**  - permission errors, races and I/O failures are handled per-item
                without aborting the whole operation.

Public API is intentionally small; import from here rather than the submodules.
"""

from __future__ import annotations

from .models import (
    DeletionMethod,
    DeletionResult,
    DeletionOutcome,
    FileEntry,
    ScanResult,
    StorageKind,
)
from .storage import StorageInfo, StorageProbe, detect_storage
from .guard import GuardVerdict, PathGuard
from .fastwalk import FastWalker, WalkOptions
from .hashing import DuplicateFinderEngine, hash_file, HASH_ALGORITHM
from .secure_delete import SecureDeleter, OverwriteNotEffective
from .categories import CleanupCategory, RiskLevel, default_categories, categories_by_id
from .service import CleanerService, CleanupReport, CategoryScan

__all__ = [
    # models
    "DeletionMethod",
    "DeletionOutcome",
    "DeletionResult",
    "FileEntry",
    "ScanResult",
    "StorageKind",
    # storage
    "StorageInfo",
    "StorageProbe",
    "detect_storage",
    # guard
    "GuardVerdict",
    "PathGuard",
    # traversal
    "FastWalker",
    "WalkOptions",
    # hashing / dedup
    "DuplicateFinderEngine",
    "hash_file",
    "HASH_ALGORITHM",
    # deletion
    "SecureDeleter",
    "OverwriteNotEffective",
    # categories
    "CleanupCategory",
    "RiskLevel",
    "default_categories",
    "categories_by_id",
    # orchestration
    "CleanerService",
    "CleanupReport",
    "CategoryScan",
]

__engine_version__ = "2.1.0"
