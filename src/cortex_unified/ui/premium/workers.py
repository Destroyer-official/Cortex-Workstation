"""Background workers bridging the GUI to the engine.

All potentially slow filesystem work (scanning, hashing, deleting) runs here on
QThreads so the UI thread stays responsive. Each worker is a plain ``QObject``
moved onto a ``QThread`` and communicates purely via signals.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from cortex_unified.engine import (
    CleanerService,
    CleanupReport,
    DeletionMethod,
    RiskLevel,
)


import threading


class ScanWorker(QObject):
    """Runs a full category scan and emits the resulting ``CleanupReport``.

    :attr:`progress` streams live status text; :meth:`cancel` sets a shared
    event the engine checks during its walk, so an in-flight scan stops
    early rather than running to completion.
    """

    finished = Signal(object)   # CleanupReport
    progress = Signal(str)      # live status text
    failed = Signal(str)

    def __init__(self, max_risk: str = "medium", include_disabled: bool = False):
        """__init__."""
        super().__init__()
        self._max_risk = max_risk
        self._include_disabled = include_disabled
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            report = CleanerService().scan_categories(
                max_risk=RiskLevel(self._max_risk),
                include_disabled=self._include_disabled,
                progress=self.progress.emit,
                cancel_event=self._cancel,
            )
            self.finished.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class CleanWorker(QObject):
    """Executes deletion for a previously produced report (batched + cancellable)."""

    finished = Signal(object, int, int)   # (bytes_freed, items_cleaned, items_skipped)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, report: CleanupReport, method: str):
        """__init__."""
        super().__init__()
        self._report = report
        self._method = method
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            svc = CleanerService()

            def _prog(done: int, total: int) -> None:
                """_prog."""
                self.progress.emit(f"Cleaning\u2026 {done:,} / {total:,}")

            results = svc.clean_categories(
                self._report, DeletionMethod(self._method),
                progress=_prog, cancel_event=self._cancel,
            )
            freed = sum(r.size for r in results
                        if r.succeeded and r.method is not DeletionMethod.DRY_RUN)
            items = sum(1 for r in results if r.succeeded)
            skipped = sum(1 for r in results if not r.succeeded)
            self.finished.emit(freed, items, skipped)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DuplicateWorker(QObject):
    """DuplicateWorker class."""
    finished = Signal(dict)       # {hash: [Path, ...]}
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, roots: list[str]):
        """__init__."""
        super().__init__()
        self._roots = roots
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            groups = CleanerService().find_duplicates(
                [Path(r) for r in self._roots],
                progress=self.progress.emit,
                cancel_event=self._cancel,
            )
            self.finished.emit(groups)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


def _norm(p) -> str:
    """_norm."""
    return str(p).replace("/", "\\")


def aggregate_roots(entries, roots) -> list[dict]:
    """Aggregate scanned entries under each root folder (for a category node)."""
    roots_n = [(_norm(r), r) for r in roots]
    buckets: dict[str, list] = {rn: [0, 0] for rn, _ in roots_n}
    for e in entries:
        ep = _norm(e.path)
        for rn, _ in roots_n:
            if ep == rn or ep.startswith(rn + "\\"):
                buckets[rn][0] += e.size
                buckets[rn][1] += 1
                break
    out = []
    for rn, orig in roots_n:
        size, count = buckets[rn]
        if count:
            out.append({"name": Path(orig).name or str(orig), "path": rn,
                        "size": size, "count": count, "is_dir": True, "expandable": True})
    out.sort(key=lambda x: x["size"], reverse=True)
    return out


def children_under(entries, prefix: str) -> list[dict]:
    """Immediate files + aggregated subfolders directly under *prefix*.

    Pure computation over the already-scanned entries - supports drilling to any
    depth without re-walking the filesystem.
    """
    pn = _norm(prefix)
    folders: dict[str, dict] = {}
    files: list[dict] = []
    plen = len(pn)
    for e in entries:
        ep = _norm(e.path)
        if not (ep == pn or ep.startswith(pn + "\\")):
            continue
        rest = ep[plen:].lstrip("\\")
        if not rest:
            continue
        parts = rest.split("\\")
        if len(parts) == 1:
            files.append({"name": parts[0], "path": ep, "size": e.size,
                          "count": 1, "is_dir": False, "expandable": False})
        else:
            key = parts[0]
            f = folders.get(key)
            if f is None:
                f = {"name": key, "path": pn + "\\" + key, "size": 0,
                     "count": 0, "is_dir": True, "expandable": True}
                folders[key] = f
            f["size"] += e.size
            f["count"] += 1
    out = list(folders.values()) + files
    out.sort(key=lambda x: x["size"], reverse=True)
    return out


# Friendly names for common vendor/app folders (so "Google" reads "Google Chrome").
_APP_FRIENDLY = {
    "google": "Google Chrome", "microsoft": "Microsoft", "mozilla": "Mozilla Firefox",
    "bravesoftware": "Brave", "vivaldi": "Vivaldi", "opera software": "Opera",
    "discord": "Discord", "slack": "Slack", "spotify": "Spotify", "code": "VS Code",
    "code - insiders": "VS Code Insiders", "nvidia": "NVIDIA", "amd": "AMD",
    "steam": "Steam", "epic games": "Epic Games", "zoom": "Zoom",
    "adobe": "Adobe", "jetbrains": "JetBrains", "postman": "Postman",
    "docker": "Docker", "kiro": "Kiro", "packages": "Windows Store apps",
    "temp": "Temp", "d3dscache": "DirectX shader cache",
}


def group_by_app(entries, bases) -> list[dict]:
    """Group scanned cache entries by their owning app (first folder after a
    base root like %LOCALAPPDATA%). Returns friendly, selectable app nodes."""
    bases_n = [_norm(b) for b in bases]
    groups: dict[str, list] = {}   # prefix -> [size, count, app_name]
    for e in entries:
        ep = _norm(e.path)
        for bn in bases_n:
            if ep.startswith(bn + "\\"):
                rest = ep[len(bn):].lstrip("\\")
                if not rest:
                    break
                app = rest.split("\\")[0]
                prefix = bn + "\\" + app
                g = groups.get(prefix)
                if g is None:
                    g = [0, 0, _APP_FRIENDLY.get(app.lower(), app)]
                    groups[prefix] = g
                g[0] += e.size
                g[1] += 1
                break
    out = [{"name": g[2], "path": prefix, "size": g[0], "count": g[1],
            "is_dir": True, "expandable": True} for prefix, g in groups.items()]
    out.sort(key=lambda x: x["size"], reverse=True)
    return out


class DirPreviewWorker(QObject):
    """Compute a tree node's children off the UI thread (keeps expand snappy)."""

    finished = Signal(int, list)   # (node_id, children)
    failed = Signal(str)

    def __init__(self, node_id: int, entries, mode: str,
                 roots=None, prefix: str | None = None):
        """Initialize worker."""
        super().__init__()
        self._nid = node_id
        self._entries = entries
        self._mode = mode
        self._roots = roots or []
        self._prefix = prefix

    def run(self) -> None:
        """run."""
        try:
            if self._mode == "appwise":
                children = group_by_app(self._entries, self._roots)
            elif self._mode == "category":
                children = aggregate_roots(self._entries, self._roots)
            else:
                children = children_under(self._entries, self._prefix or "")
            self.finished.emit(self._nid, children[:400])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DuplicatePhotosWorker(QObject):
    """Find duplicate image files only (byte-for-byte, extension-filtered)."""

    finished = Signal(dict)       # {hash: [Path, ...]}
    progress = Signal(str)
    failed = Signal(str)

    IMAGE_EXTS = {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
        ".webp", ".heic", ".heif", ".raw", ".cr2", ".nef", ".arw", ".dng",
    }

    def __init__(self, roots: list[str]):
        """__init__."""
        super().__init__()
        self._roots = roots
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            groups = CleanerService().find_duplicates(
                [Path(r) for r in self._roots],
                progress=self.progress.emit,
                cancel_event=self._cancel,
                extensions=self.IMAGE_EXTS,
            )
            self.finished.emit(groups)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LargeFilesWorker(QObject):
    """LargeFilesWorker class."""
    finished = Signal(list)       # [FileEntry, ...]
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, min_mb: float):
        """__init__."""
        super().__init__()
        self._root = root
        self._min_mb = min_mb
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            entries = CleanerService().find_large_files(
                self._root, min_mb=self._min_mb, limit=200,
                progress=self.progress.emit, cancel_event=self._cancel,
            )
            self.finished.emit(entries)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class EmptyWorker(QObject):
    """EmptyWorker class."""
    finished = Signal(list, list)  # (empty_files, empty_dirs)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str):
        """__init__."""
        super().__init__()
        self._root = root
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            files, dirs = CleanerService().find_empty(self._root, cancel_event=self._cancel)
            self.finished.emit(files, dirs)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DeleteSelectedWorker(QObject):
    """Delete an arbitrary list of paths via the safe SecureDeleter."""

    finished = Signal(object, int, int)   # (bytes_freed, succeeded, blocked)
    failed = Signal(str)

    def __init__(self, paths: list[str], method: str):
        """__init__."""
        super().__init__()
        self._paths = paths
        self._method = method

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.engine import SecureDeleter

            deleter = SecureDeleter()
            results = deleter.delete_many(self._paths, DeletionMethod(self._method))
            freed = sum(r.size for r in results
                        if r.succeeded and r.method is not DeletionMethod.DRY_RUN)
            ok = sum(1 for r in results if r.succeeded)
            blocked = sum(1 for r in results if not r.succeeded)
            self.finished.emit(freed, ok, blocked)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RestorePointWorker(QObject):
    """Create a Windows System Restore point (PowerShell-backed, so threaded)."""

    finished = Signal(str, str)   # (status, message)
    failed = Signal(str)

    def __init__(self, description: str = "Cortex Cleaner"):
        """__init__."""
        super().__init__()
        self._description = description

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.restore_point import RestorePointManager
            res = RestorePointManager().create(self._description)
            self.finished.emit(res.status.value, res.message)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class RestorePointListWorker(QObject):
    """List existing restore points (read-only)."""

    finished = Signal(list)
    failed = Signal(str)

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.restore_point import RestorePointManager
            self.finished.emit(RestorePointManager().list_points())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class StorageWorker(QObject):
    """Detect the storage medium behind a path (subprocess-backed, so threaded)."""

    finished = Signal(str, bool)   # (kind, overwrite_effective)
    failed = Signal(str)

    def __init__(self, path: str):
        """__init__."""
        super().__init__()
        self._path = path

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.engine import detect_storage
            info = detect_storage(self._path)
            self.finished.emit(info.kind.value, info.kind.overwrite_effective)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class FreeSpaceWipeWorker(QObject):
    """Overwrite a volume's free space (Windows cipher /w). Long-running."""

    finished = Signal(bool, str)   # (success, message)
    failed = Signal(str)

    def __init__(self, drive_letter: str):
        """__init__."""
        super().__init__()
        self._letter = drive_letter
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        # cipher /w can run up to an hour; this reaches all the way down to
        # core.proc.run(), which kills the process tree within one poll
        # interval instead of leaving it to finish or abandoning it as an
        # orphan when the app closes.
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.free_space_wipe import FreeSpaceWiper
            res = FreeSpaceWiper().wipe(self._letter, cancel_event=self._cancel)
            self.finished.emit(res.success, res.message)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ShredWorker(QObject):
    """Storage-aware secure deletion of a single target."""

    finished = Signal(str, str)   # (outcome, reason)
    refused = Signal(str, str)    # (medium_kind, guidance)
    failed = Signal(str)

    def __init__(self, target: str, passes: int, force_flash: bool):
        """__init__."""
        super().__init__()
        self._target = target
        self._passes = passes
        self._force_flash = force_flash

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.engine import SecureDeleter
            from cortex_unified.engine.secure_delete import OverwriteNotEffective

            deleter = SecureDeleter(overwrite_passes=self._passes)
            try:
                res = deleter.delete(
                    self._target,
                    DeletionMethod.OVERWRITE,
                    force_overwrite_on_flash=self._force_flash,
                )
                self.finished.emit(res.outcome.value, res.reason)
            except OverwriteNotEffective as exc:
                self.refused.emit(exc.kind.value, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class AdaptiveShredWorker(QObject):
    """Adaptive PL0-PL3 shred (HolePunch/PULSE/WAS-Deletion).

    Picks PL by storage kind + file hotness when level is 'auto', otherwise
    uses the requested PL0-PL3. Verifies and reports wear/latency costs.
    """

    finished = Signal(str, str, str)  # (outcome, message, detail)
    failed = Signal(str)

    def __init__(self, target: str, level: str | None = None, verify: bool = True):
        """__init__."""
        super().__init__()
        self._target = target
        self._level = level  # None = auto, else "pl0"/"pl1"/"pl2"/"pl3"
        self._verify = verify

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.adaptive_sanitizer import AdaptiveSanitizer
            from pathlib import Path

            san = AdaptiveSanitizer()
            lvl = None
            if self._level and self._level != "auto":
                from cortex_unified.system_tools.adaptive_sanitizer import PrivacyLevel

                try:
                    lvl = PrivacyLevel(self._level)
                except ValueError:
                    lvl = None
            res = san.sanitize(Path(self._target), level=lvl, verify=self._verify)
            status = "shredded" if res.success else "failed"
            detail = f"PL={res.level.value} {res.method} wear={res.wear_cost} verified={res.verified} {res.detail}"
            self.finished.emit(status, res.message, detail)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Virtual disks (WSL / Docker / Hyper-V VHDX reclaim)
# ---------------------------------------------------------------------------

class VhdxListWorker(QObject):
    """Discovers WSL / Docker / Hyper-V virtual disks (read-only)."""

    finished = Signal(list)     # list[VirtualDisk]
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self):
        """__init__."""
        super().__init__()
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.vhdx_manager import VhdxManager
            self.progress.emit("Looking for virtual disks\u2026")
            disks = VhdxManager().list_disks()
            # The Hyper-V probe shells out to PowerShell, so a page closed
            # mid-scan would otherwise leave the thread to be terminated.
            if self._cancel.is_set():
                return
            self.finished.emit(disks)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WslShutdownWorker(QObject):
    """Runs ``wsl --shutdown`` so virtual disks can be detached and compacted."""

    finished = Signal(bool, str)   # (ok, message)
    progress = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.vhdx_manager import VhdxManager
            self.progress.emit("Stopping WSL distributions\u2026")
            ok, msg = VhdxManager().shutdown_wsl()
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class VhdxCompactWorker(QObject):
    """Compacts one or more virtual disks, reporting measured space returned.

    Compaction is not interruptible once diskpart owns the file - cancelling
    stops the run *between* disks rather than mid-disk, which is the only safe
    place to stop.
    """

    finished = Signal(list)        # list[CompactResult]
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, disks: list):
        """__init__."""
        super().__init__()
        self._disks = disks
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.vhdx_manager import VhdxManager
            mgr = VhdxManager()
            results = []
            total = len(self._disks)
            for i, disk in enumerate(self._disks, start=1):
                if self._cancel.is_set():
                    break
                self.progress.emit(
                    f"Compacting {disk.label} ({i} of {total})\u2026 this can take "
                    f"several minutes")
                results.append(mgr.compact(disk))
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class VhdxSparseWorker(QObject):
    """Turns on WSL sparse mode so the bloat doesn't come back."""

    finished = Signal(bool, str)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, disk, enabled: bool = True):
        """__init__."""
        super().__init__()
        self._disk = disk
        self._enabled = enabled

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.vhdx_manager import VhdxManager
            self.progress.emit("Updating sparse mode\u2026")
            ok, msg = VhdxManager().set_sparse(self._disk, self._enabled)
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Component store (WinSxS) + Windows upgrade leftovers
# ---------------------------------------------------------------------------

class ComponentStoreAnalyzeWorker(QObject):
    """Runs DISM /AnalyzeComponentStore and inventories upgrade leftovers.

    Both halves are read-only. Analysis can take a few minutes on a machine
    with a long update history, so it never blocks the UI thread.
    """

    finished = Signal(object, list)   # (StoreAnalysis, list[Leftover])
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self):
        """__init__."""
        super().__init__()
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.component_store import ComponentStore
            store = ComponentStore()
            self.progress.emit("Asking Windows to measure the component store\u2026")
            analysis = store.analyze()
            if self._cancel.is_set():
                return
            self.progress.emit("Looking for upgrade leftovers\u2026")
            # Hand the analysis over so WinSxS is sized from DISM rather than by
            # walking a folder of several hundred thousand hard links.
            leftovers = store.find_leftovers(
                progress=self.progress.emit, cancel_event=self._cancel,
                analysis=analysis)
            if self._cancel.is_set():
                return
            self.finished.emit(analysis, leftovers)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ComponentStoreCleanWorker(QObject):
    """Runs DISM /StartComponentCleanup (optionally /ResetBase)."""

    finished = Signal(object)   # CleanupOutcome
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, reset_base: bool = False):
        """__init__."""
        super().__init__()
        self._reset_base = reset_base

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.component_store import ComponentStore
            outcome = ComponentStore().cleanup(
                reset_base=self._reset_base, progress=self.progress.emit)
            self.finished.emit(outcome)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ServicingTaskWorker(QObject):
    """Triggers Windows' own scheduled component-cleanup task."""

    finished = Signal(bool, str)
    progress = Signal(str)
    failed = Signal(str)

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.component_store import ComponentStore
            self.progress.emit("Starting Windows' cleanup task\u2026")
            ok, msg = ComponentStore().run_servicing_task()
            self.finished.emit(ok, msg)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LeftoverDeleteWorker(QObject):
    """Deletes selected upgrade leftovers through the engine's guarded deleter.

    Routing through ``SecureDeleter`` means the path guard still applies, so a
    mistake in the leftover list cannot turn into a destructive delete.
    """

    finished = Signal(object, int, int)   # (bytes_freed, removed, blocked)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, paths: list[str], sizes: dict[str, int] | None = None):
        """__init__."""
        super().__init__()
        self._paths = paths
        self._sizes = sizes or {}
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.engine.secure_delete import SecureDeleter

            deleter = SecureDeleter()
            results = deleter.delete_many(
                [Path(p) for p in self._paths],
                method=DeletionMethod.DELETE,   # system dirs can't go to Recycle Bin
                progress=lambda done, total: self.progress.emit(
                    f"Removing\u2026 {done:,} / {total:,}"),
                cancel_event=self._cancel,
                sizes=self._sizes or None,
            )
            freed = sum(r.size for r in results if r.succeeded)
            removed = sum(1 for r in results if r.succeeded)
            blocked = sum(1 for r in results if not r.succeeded)
            self.finished.emit(freed, removed, blocked)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ProjectCacheScanWorker(QObject):
    """Scans target folders for developer project caches across enabled categories."""

    finished = Signal(list)            # List[Dict] resources
    progress = Signal(str, int, object)   # status_text, items_found, total_bytes
    failed = Signal(str)

    def __init__(self, target_folders: list[str], keep_recent_days: int = 7, enabled_categories: list[str] | None = None):
        """__init__."""
        super().__init__()
        self._target_folders = target_folders
        self._keep_recent_days = keep_recent_days
        self._enabled_categories = enabled_categories
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            from cortex_unified.core.config import Config

            cleaner = PackageManagerCleaner(Config())
            
            def _prog(status: str, items: int, size: int) -> None:
                """_prog."""
                self.progress.emit(status, items, size)

            resources = cleaner.scan_caches(
                target_folders=self._target_folders,
                keep_recent_days=self._keep_recent_days,
                enabled_categories=self._enabled_categories,
                progress_callback=_prog,
                cancel_event=self._cancel,
            )
            self.finished.emit(resources or [])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ProjectCacheCleanWorker(QObject):
    """Cleans selected project caches off-thread; dry run by default."""

    finished = Signal(dict)            # results dict
    progress = Signal(int, int, object)   # done_count, total_count, freed_bytes
    failed = Signal(str)

    def __init__(self, resources: list[dict], dry_run: bool = True):
        """__init__."""
        super().__init__()
        self._resources = resources
        self._dry_run = dry_run
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            from cortex_unified.core.config import Config

            cleaner = PackageManagerCleaner(Config())

            def _prog(done: int, total: int, freed: int) -> None:
                """_prog."""
                self.progress.emit(done, total, freed)

            results = cleaner.cleanup_caches(
                resources=self._resources,
                dry_run=self._dry_run,
                progress_callback=_prog,
                cancel_event=self._cancel,
            )
            self.finished.emit(results or {})
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ---------------------------------------------------------------------------
# Auto-discovery of project caches across fixed drives (no manual folder pick)
# ---------------------------------------------------------------------------

class AutoProjectCacheWorker(QObject):
    """Walks all fixed drives (or known D:\\code) for PROJECT_CACHE_CATEGORIES."""

    finished = Signal(list)  # resources
    progress = Signal(str, int, object)
    failed = Signal(str)

    def __init__(self, enabled_categories: list[str] | None = None, keep_recent_days: int = 7):
        """__init__."""
        super().__init__()
        self._enabled = enabled_categories
        self._keep = keep_recent_days
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
            from cortex_unified.core.config import Config
            cleaner = PackageManagerCleaner(Config())

            def _prog(msg: str, items: int, size: int) -> None:
                """_prog."""
                self.progress.emit(msg, items, size)

            resources = cleaner.auto_discover_project_caches(
                enabled_categories=self._enabled,
                keep_recent_days=self._keep,
                progress_callback=_prog,
                cancel_event=self._cancel,
            )
            self.finished.emit(resources or [])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class CacheLogSweepWorker(QObject):
    """Finds large logs (*.log/*.txt) across user-selected roots (D:\\code)."""

    finished = Signal(list)  # [(Path, size), ...]
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, roots: list[str], min_size_mb: float = 100.0):
        """__init__."""
        super().__init__()
        self._roots = roots
        self._min = min_size_mb
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.analyzers.cache_cleaner import CacheCleaner
            cc = CacheCleaner()
            results = cc.find_large_logs(
                self._roots, min_size_mb=self._min, exclude_archives=True,
                progress_callback=self.progress.emit, cancel_event=self._cancel)
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DockerFsCacheWorker(QObject):
    """Measures Docker Desktop filesystem cache (AppData\\Local\\Docker)."""

    finished = Signal(dict)
    failed = Signal(str)

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.analyzers.docker_cleaner import DockerCleaner
            self.finished.emit(DockerCleaner().get_filesystem_cache_size())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class WslListWorker(QObject):
    """Lists WSL distros + their ext4.vhdx sizes."""

    finished = Signal(list)
    failed = Signal(str)

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.system_tools.wsl_cleaner import WslCleaner
            self.finished.emit([d.to_dict() for d in WslCleaner().list_distros()])
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class LargeFileAiWorker(QObject):
    """Finds large files and tags AI models vs other."""

    finished = Signal(list, list)  # (other_files, ai_model_files)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, min_mb: float = 100.0):
        """__init__."""
        super().__init__()
        self._root = root
        self._min_mb = min_mb
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        try:
            from cortex_unified.analyzers.large_file_finder import LargeFileFinder, is_ai_model
            finder = LargeFileFinder(root_path=self._root)
            all_files = finder.find_large_files(min_size_mb=self._min_mb)
            other = [(p, s) for p, s in all_files if not is_ai_model(p)]
            ai_models = [(p, s) for p, s in all_files if is_ai_model(p)]
            self.finished.emit(other, ai_models)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))

