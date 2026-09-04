"""High-level cleaner service - the single orchestration entry point.

This facade ties the low-level engine pieces (FastWalker, PathGuard,
SecureDeleter, StorageProbe, DuplicateFinderEngine) into the workflows a real
cleaner needs, with a consistent, honest, dry-run-first contract:

    service = CleanerService()
    report  = service.scan_categories()          # discover reclaimable space
    result  = service.clean_categories(report)   # act (dry-run by default)

    dupes   = service.find_duplicates([root])
    large   = service.find_large_files(root, min_mb=100)
    empties = service.find_empty(root)

Everything destructive goes through the guard and the storage-aware deleter,
and nothing is removed unless an explicit non-dry-run method is passed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .categories import CleanupCategory, RiskLevel, default_categories
from .fastwalk import FastWalker, WalkOptions
from .guard import PathGuard
from .hashing import DuplicateFinderEngine
from .models import DeletionMethod, DeletionResult, FileEntry
from .secure_delete import SecureDeleter
from .storage import StorageProbe

_LOG = logging.getLogger("cortex.engine.service")


def _throttle(cb: "Callable[[str], None] | None", interval: float = 0.1):
    """Wrap a progress callback so it fires at most every *interval* seconds.

    Directory walks can invoke the callback thousands of times; without this,
    each call posts a queued Qt event and can swamp the GUI thread.
    """
    if cb is None:
        return None
    import time
    last = [0.0]

    def wrapped(msg: str) -> None:
        """Wrapped.

        Manages wrapped operations and coordinates related state changes for the component.

        Args:
            msg (str): Informational or progress status message.
        """
        now = time.monotonic()
        if now - last[0] >= interval:
            last[0] = now
            cb(msg)

    return wrapped


@dataclass(slots=True)
class CategoryScan:
    """Categoryscan.

    Manages CategoryScan operations and coordinates related state changes for the component.
    """

    category: CleanupCategory
    entries: list[FileEntry] = field(default_factory=list)
    total_bytes: int = 0
    #: Cloud placeholders (OneDrive Files On-Demand and friends) left out of
    #: this category. Their bytes are not on this disk, so deleting them would
    #: free nothing while removing cloud data - reported, never silently dropped.
    cloud_skipped: int = 0
    cloud_skipped_bytes: int = 0

    @property
    def file_count(self) -> int:
        """file_count.

        Manages file count operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return len(self.entries)

    def breakdown(self, limit: int = 200) -> list[dict]:
        """Group this category's files into their top folders for preview.

        Returns the biggest folders/files (by size) so the UI can show the user
        *what* is inside a category before they delete it. Grouped by the
        immediate child of each declared category root, so 70k browser files
        collapse into a readable handful of folders.
        """
        from collections import defaultdict
        roots = [str(p) for p in self.category.paths]
        groups: dict[str, list] = defaultdict(lambda: [0, 0, "", False])  # size,count,path,is_dir
        for e in self.entries:
            ep = str(e.path)
            grp_path = None
            for r in roots:
                if ep == r or ep.startswith(r + os.sep) or ep.startswith(r + "/"):
                    rest = ep[len(r):].lstrip("\\/")
                    if rest:
                        first = rest.replace("/", "\\").split("\\")[0]
                        grp_path = str(Path(r) / first)
                        is_dir = "\\" in rest.replace("/", "\\") or "/" in rest
                    else:
                        grp_path, is_dir = ep, False
                    break
            if grp_path is None:
                grp_path = str(Path(ep).parent)
                is_dir = True
            g = groups[grp_path]
            g[0] += e.size
            g[1] += 1
            g[2] = grp_path
            g[3] = g[3] or is_dir
        items = [{"path": p, "name": Path(p).name or p, "size": v[0],
                  "count": v[1], "is_dir": v[3]} for p, v in groups.items()]
        items.sort(key=lambda x: x["size"], reverse=True)
        return items[:limit]

    def to_dict(self) -> dict:
        """to_dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        return {
            "id": self.category.id,
            "label": self.category.label,
            "risk": self.category.risk.value,
            "reversible": self.category.reversible,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "cloud_skipped": self.cloud_skipped,
            "cloud_skipped_bytes": self.cloud_skipped_bytes,
        }


@dataclass(slots=True)
class CleanupReport:
    """Aggregate of all scanned categories.

    Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
    """

    scans: list[CategoryScan] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def total_reclaimable_bytes(self) -> int:
        """total_reclaimable_bytes.

        Manages total reclaimable bytes operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return sum(s.total_bytes for s in self.scans)

    @property
    def total_files(self) -> int:
        """total_files.

        Manages total files operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return sum(s.file_count for s in self.scans)

    @property
    def cloud_skipped(self) -> int:
        """Total cloud placeholders excluded across all categories.

        Manages cloud skipped operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return sum(s.cloud_skipped for s in self.scans)

    @property
    def cloud_skipped_bytes(self) -> int:
        """Logical size of the excluded placeholders (not local, not reclaimable).

        Manages cloud skipped bytes operations and coordinates related state changes for the component.

        Returns:
            int: Result of the operation.
        """
        return sum(s.cloud_skipped_bytes for s in self.scans)

    @property
    def cloud_note(self) -> str:
        """One-line explanation of skipped cloud files, or ``""`` when none.

        Shown so the user understands why a folder they know is large didn't
        contribute to the total, instead of assuming the scan missed it.
        """
        n = self.cloud_skipped
        if not n:
            return ""
        return (f"Skipped {n:,} cloud-only file{'s' if n != 1 else ''}: the content "
                "isn't stored on this PC, so removing it would free no space and "
                "would delete your cloud copy.")

    def to_dict(self) -> dict:
        """to_dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict: Dictionary mapping identifiers to status or values.
        """
        return {
            "total_reclaimable_bytes": self.total_reclaimable_bytes,
            "total_files": self.total_files,
            "duration_seconds": round(self.duration_seconds, 3),
            "cloud_skipped": self.cloud_skipped,
            "cloud_skipped_bytes": self.cloud_skipped_bytes,
            "categories": [s.to_dict() for s in self.scans],
        }


class CleanerService:
    """Unified, safe orchestration of scanning and reclamation.

    Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
    """

    def __init__(
        self,
        guard: PathGuard | None = None,
        probe: StorageProbe | None = None,
    ) -> None:
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            guard (PathGuard | None): The guard parameter.
            probe (StorageProbe | None): The probe parameter.
        """
        self.guard = guard or PathGuard()
        self.probe = probe or StorageProbe()

    # -- category scan / clean ---------------------------------------------

    def scan_categories(
        self,
        category_ids: list[str] | None = None,
        max_risk: RiskLevel = RiskLevel.MEDIUM,
        include_disabled: bool = False,
        progress: "Callable[[str], None] | None" = None,
        cancel_event=None,
    ) -> CleanupReport:
        """Scan cleanup categories and report reclaimable space.

        Args:
            category_ids: restrict to these ids (default: all applicable).
            max_risk: skip categories riskier than this (default: up to MEDIUM;
                HIGH-risk categories are never auto-included).
            include_disabled: include categories flagged ``default_enabled=False``.
            progress: optional callback receiving a human-readable status string.
            cancel_event: optional ``threading.Event``; scanning stops when set.
        """
        import time
        start = time.perf_counter()
        report = CleanupReport()
        _LOG.info("scan_categories start (max_risk=%s)", max_risk.value)
        emit = _throttle(progress)

        wanted = self._select_categories(category_ids, max_risk, include_disabled)
        for cat in wanted:
            if cancel_event is not None and cancel_event.is_set():
                _LOG.info("scan_categories cancelled")
                break
            if progress is not None:
                progress(f"Scanning {cat.label}\u2026")   # category change: always show
            scan = self._scan_category(cat, emit, cancel_event)
            _LOG.debug("category %s: %d files, %d bytes", cat.id, scan.file_count, scan.total_bytes)
            if scan.file_count:
                report.scans.append(scan)

        report.duration_seconds = time.perf_counter() - start
        _LOG.info("scan_categories done in %.2fs: %d files, %d bytes",
                  report.duration_seconds, report.total_files, report.total_reclaimable_bytes)
        return report

    def clean_categories(
        self,
        report: CleanupReport,
        method: DeletionMethod = DeletionMethod.DRY_RUN,
        progress: "Callable[[int, int], None] | None" = None,
        cancel_event=None,
    ) -> list[DeletionResult]:
        """Remove everything discovered in *report* using *method*.

        Defaults to DRY_RUN: you must pass an explicit non-dry-run method to
        actually delete. Every item is still routed through the guard.
        ``progress(done, total)`` reports batch progress; ``cancel_event`` stops
        the run cleanly between batches.
        """
        deleter = SecureDeleter(guard=self.guard, probe=self.probe)
        paths = [e.path for scan in report.scans for e in scan.entries]
        # Reuse sizes already gathered during the scan so deletion doesn't
        # re-stat every file just to report freed bytes.
        sizes = {str(e.path): e.size for scan in report.scans for e in scan.entries}
        return deleter.delete_many(paths, method, progress=progress,
                                   cancel_event=cancel_event, sizes=sizes)

    # -- ad-hoc analysis ----------------------------------------------------

    def find_duplicates(
        self,
        roots: list[str | Path],
        min_size: int = 1,
        progress: "Callable[[str], None] | None" = None,
        cancel_event=None,
        extensions: "set[str] | None" = None,
    ) -> dict[str, list[Path]]:
        """Find duplicate files across one or more root directories.

        If *extensions* is given (lower-case, with leading dot, e.g.
        ``{".jpg", ".png"}``), only files with those extensions are considered -
        used by the duplicate-photo finder.
        """
        walker = FastWalker(WalkOptions(min_size=max(1, min_size)))
        if cancel_event is not None:
            walker._cancel = cancel_event
        emit = _throttle(progress)
        entries: list[tuple[Path, int]] = []
        for root in roots:
            def _rep(cur_dir, seen):
                """Rep.

                Manages rep operations and coordinates related state changes for the component.

                Args:
                    cur_dir: The cur dir parameter.
                    seen: The seen parameter.
                """
                if emit is not None:
                    emit(f"Indexing files: {len(entries) + seen}\u2026")
            for e in walker.iter_files(root, progress=_rep):
                if extensions is not None and e.path.suffix.lower() not in extensions:
                    continue
                entries.append((e.path, e.size))
        if progress is not None:
            progress(f"Hashing {len(entries)} candidates\u2026")

        def _hprog(done, total):
            """Hprog.

            Manages hprog operations and coordinates related state changes for the component.

            Args:
                done: The done parameter.
                total: The total parameter.
            """
            if emit is not None:
                emit(f"Hashing {done}/{total}\u2026")
        return DuplicateFinderEngine().find(entries, progress=_hprog)

    def find_large_files(
        self,
        root: str | Path,
        min_mb: float = 100.0,
        limit: int = 100,
        progress: "Callable[[str], None] | None" = None,
        cancel_event=None,
    ) -> list[FileEntry]:
        """Return the largest files under *root* above *min_mb*, biggest first.

        Manages find large files operations and coordinates related state changes for the component.

        Args:
            root (str | Path): Filesystem path to the target file or directory.
            min_mb (float): The min mb parameter.
            limit (int): The limit parameter.
            progress ('Callable[[str], None] | None'): The progress parameter.
            cancel_event: Threading event or callable to check for cancellation.

        Returns:
            list[FileEntry]: List of processed items or identifiers.
        """
        opts = WalkOptions(min_size=int(min_mb * 1024 * 1024))
        walker = FastWalker(opts)
        if cancel_event is not None:
            walker._cancel = cancel_event
        emit = _throttle(progress)
        entries: list[FileEntry] = []

        def _rep(cur_dir, seen):
            """Rep.

            Manages rep operations and coordinates related state changes for the component.

            Args:
                cur_dir: The cur dir parameter.
                seen: The seen parameter.
            """
            if emit is not None:
                emit(f"Scanning: {seen} files ({len(entries)} large)\u2026")
        for e in walker.iter_files(root, progress=_rep):
            entries.append(e)
        entries.sort(key=lambda e: e.size, reverse=True)
        return entries[:limit]

    def find_empty(
        self,
        root: str | Path,
        cancel_event=None,
    ) -> tuple[list[Path], list[Path]]:
        """Return (empty_files, empty_dirs) under *root*.

        Manages find empty operations and coordinates related state changes for the component.

        Args:
            root (str | Path): Filesystem path to the target file or directory.
            cancel_event: Threading event or callable to check for cancellation.

        Returns:
            tuple[list[Path], list[Path]]: List of processed items or identifiers.
        """
        walker = FastWalker()
        if cancel_event is not None:
            walker._cancel = cancel_event
        return walker.find_empty(root)

    # -- internals ----------------------------------------------------------

    def _select_categories(
        self, ids: list[str] | None, max_risk: RiskLevel, include_disabled: bool
    ) -> list[CleanupCategory]:
        """_select_categories.

        Manages select categories operations and coordinates related state changes for the component.

        Args:
            ids (list[str] | None): The ids parameter.
            max_risk (RiskLevel): The max risk parameter.
            include_disabled (bool): The include disabled parameter.

        Returns:
            list[CleanupCategory]: List of processed items or identifiers.
        """
        cats = default_categories()
        if ids is not None:
            idset = set(ids)
            cats = [c for c in cats if c.id in idset]
        else:
            cats = [c for c in cats if include_disabled or c.default_enabled]
        return [c for c in cats if c.risk.rank <= max_risk.rank or (ids and c.id in set(ids or []))]

    def _scan_category(self, cat: CleanupCategory, progress=None, cancel_event=None) -> CategoryScan:
        """_scan_category.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            cat (CleanupCategory): The cat parameter.
            progress: The progress parameter.
            cancel_event: Threading event or callable to check for cancellation.

        Returns:
            CategoryScan: Result of the operation.
        """
        scan = CategoryScan(category=cat)
        opts = WalkOptions(
            exclude_globs=(),
            follow_symlinks=False,
            min_age_days=cat.min_age_days,
            max_depth=None if cat.recursive else 0,
        )
        walker = FastWalker(opts)
        if cancel_event is not None:
            walker._cancel = cancel_event  # honor external cancellation
        globset = cat.globs

        for base in cat.existing_paths():
            # PERFORMANCE + SAFETY: guard the category *root* once here, instead
            # of resolving every single file (Path.resolve() is a ~0.5ms syscall
            # each - over thousands of temp files that alone cost seconds and made
            # scans feel frozen). Per-item safety is still enforced at deletion
            # time by SecureDeleter/PathGuard, so nothing unsafe can be removed.
            if not self.guard.check(base).safe:
                _LOG.debug("skipping unsafe category root: %s", base)
                continue

            def _report(cur_dir, seen, _label=cat.label):
                """Report.

                Manages report operations and coordinates related state changes for the component.

                Args:
                    cur_dir: The cur dir parameter.
                    seen: The seen parameter.
                    _label: The  label parameter.
                """
                if progress is not None:
                    progress(f"Scanning {_label}: {scan.file_count + seen} files\u2026")

            for entry in walker.iter_files(base, progress=_report):
                if globset != ("*",) and not _matches_any(entry.path.name, globset):
                    continue
                scan.entries.append(entry)
                # reclaimable_size, not the logical size: sparse and compressed
                # files occupy less than they claim, so promising their logical
                # size back would overstate the result.
                scan.total_bytes += entry.reclaimable_size
        scan.cloud_skipped = walker.cloud_skipped
        scan.cloud_skipped_bytes = walker.cloud_skipped_bytes
        return scan


def _matches_any(name: str, globs: tuple[str, ...]) -> bool:
    """_matches_any.

    Manages matches any operations and coordinates related state changes for the component.

    Args:
        name (str): The name parameter.
        globs (tuple[str, ...]): The globs parameter.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    import fnmatch
    return any(fnmatch.fnmatch(name, g) for g in globs)
