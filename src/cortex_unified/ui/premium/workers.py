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
    """Runs a category scan and returns a CleanupReport."""

    finished = Signal(object)   # CleanupReport
    progress = Signal(str)      # live status text
    failed = Signal(str)

    def __init__(self, max_risk: str = "medium", include_disabled: bool = False):
        super().__init__()
        self._max_risk = max_risk
        self._include_disabled = include_disabled
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
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

    finished = Signal(int, int, int)   # (bytes_freed, items_cleaned, items_skipped)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, report: CleanupReport, method: str):
        super().__init__()
        self._report = report
        self._method = method
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            svc = CleanerService()

            def _prog(done: int, total: int) -> None:
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
    finished = Signal(dict)       # {hash: [Path, ...]}
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, roots: list[str]):
        super().__init__()
        self._roots = roots
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
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
        super().__init__()
        self._nid = node_id
        self._entries = entries
        self._mode = mode
        self._roots = roots or []
        self._prefix = prefix

    def run(self) -> None:
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
        super().__init__()
        self._roots = roots
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
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
    finished = Signal(list)       # [FileEntry, ...]
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str, min_mb: float):
        super().__init__()
        self._root = root
        self._min_mb = min_mb
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            entries = CleanerService().find_large_files(
                self._root, min_mb=self._min_mb, limit=200,
                progress=self.progress.emit, cancel_event=self._cancel,
            )
            self.finished.emit(entries)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class EmptyWorker(QObject):
    finished = Signal(list, list)  # (empty_files, empty_dirs)
    progress = Signal(str)
    failed = Signal(str)

    def __init__(self, root: str):
        super().__init__()
        self._root = root
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            files, dirs = CleanerService().find_empty(self._root, cancel_event=self._cancel)
            self.finished.emit(files, dirs)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DeleteSelectedWorker(QObject):
    """Delete an arbitrary list of paths via the safe SecureDeleter."""

    finished = Signal(int, int, int)   # (bytes_freed, succeeded, blocked)
    failed = Signal(str)

    def __init__(self, paths: list[str], method: str):
        super().__init__()
        self._paths = paths
        self._method = method

    def run(self) -> None:
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
        super().__init__()
        self._description = description

    def run(self) -> None:
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
        super().__init__()
        self._path = path

    def run(self) -> None:
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
        super().__init__()
        self._letter = drive_letter

    def run(self) -> None:
        try:
            from cortex_unified.system_tools.free_space_wipe import FreeSpaceWiper
            res = FreeSpaceWiper().wipe(self._letter)
            self.finished.emit(res.success, res.message)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class ShredWorker(QObject):
    """Storage-aware secure deletion of a single target."""

    finished = Signal(str, str)   # (outcome, reason)
    refused = Signal(str, str)    # (medium_kind, guidance)
    failed = Signal(str)

    def __init__(self, target: str, passes: int, force_flash: bool):
        super().__init__()
        self._target = target
        self._passes = passes
        self._force_flash = force_flash

    def run(self) -> None:
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
