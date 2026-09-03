"""Storage-aware deletion with honest guarantees.

The critical correctness point (backed by current research): **overwriting a
file to "securely erase" it only works on rotational HDDs.** On SSD/NVMe/USB
flash, the controller's wear-leveling and copy-on-write mean an overwrite is
written to a *different* physical block, leaving the original recoverable. So a
responsible tool must:

* default to the OS recycle bin (reversible) when possible;
* only perform overwrite passes when the medium is a real HDD;
* when asked to "securely wipe" on flash media, **refuse to pretend** and tell
  the caller the truth (use full-disk encryption / hardware secure-erase / TRIM
  instead), rather than doing counterproductive write cycles that wear the
  drive without providing the promised guarantee.

Every operation is routed through :class:`PathGuard` first - including
directory deletion, which the legacy ``Deleter`` skipped.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from .guard import PathGuard
from .models import DeletionMethod, DeletionOutcome, DeletionResult, StorageKind
from .storage import StorageProbe

_LOG = logging.getLogger("cortex.engine.secure_delete")

_OVERWRITE_CHUNK = 1024 * 1024  # 1 MiB

# ``send2trash`` drags in the whole Windows COM shell stack
# (pywin32 -> pythoncom -> win32com.shell), which measured ~113 ms of import
# time. Recycling is the only feature that needs it, so it is resolved on first
# use instead of at import time: a read-only ``cortex scan`` must not pay for
# the recycle-bin machinery it never calls.
_trash_fn: Any = None          # cached callable once successfully imported
_trash_probed: bool = False    # True once we've attempted the import


def _resolve_send2trash() -> Any:
    """Import ``send2trash`` once and cache the result (``None`` if absent)."""
    global _trash_fn, _trash_probed
    if not _trash_probed:
        _trash_probed = True
        try:
            from send2trash import send2trash as _fn  # type: ignore
        except ImportError:
            _LOG.debug("send2trash unavailable; recycle will be reported as "
                       "unsupported rather than silently hard-deleting")
            _trash_fn = None
        else:
            _trash_fn = _fn
    return _trash_fn


def _has_trash() -> bool:
    """True when reversible recycle-to-trash is actually available."""
    return _resolve_send2trash() is not None


def __getattr__(name: str) -> Any:
    """Keep the historical module-level names working (:pep:`562`).

    ``_HAS_TRASH`` was a module constant that callers and tests import
    directly (for example ``@pytest.mark.skipif(not _HAS_TRASH, ...)``).
    Exposing it here preserves that contract while keeping the import lazy:
    reading the flag probes for the dependency, which is exactly what the old
    eager constant did - just deferred to the moment someone asks.
    """
    if name == "_HAS_TRASH":
        return _has_trash()
    if name == "send2trash":
        fn = _resolve_send2trash()
        if fn is None:
            raise AttributeError("send2trash is not installed")
        return fn
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class OverwriteNotEffective(RuntimeError):
    """Raised when an overwrite wipe is requested on non-rotational media.

    Carries the detected :class:`StorageKind` so callers can present accurate
    guidance to the user instead of silently doing something ineffective.
    """

    def __init__(self, kind: StorageKind, path: Path) -> None:
        """__init__."""
        self.kind = kind
        self.path = path
        super().__init__(
            f"Overwrite-based secure deletion is not effective on {kind.value} "
            f"media ({path}). On flash storage, use full-disk encryption + key "
            f"destruction or the drive's hardware secure-erase instead."
        )
        """__init__."""
        """__init__."""


class SecureDeleter:
    """Deletes files/directories with a chosen :class:`DeletionMethod`."""

    def __init__(
        self,
        guard: PathGuard | None = None,
        probe: StorageProbe | None = None,
        overwrite_passes: int = 3,
    ) -> None:
        """__init__."""
        self.guard = guard or PathGuard()
        self.probe = probe or StorageProbe()
        self.overwrite_passes = max(1, overwrite_passes)
        self.results: list[DeletionResult] = []
        """__init__."""
        """__init__."""

    # -- public API ---------------------------------------------------------

    def delete(
        self,
        path: os.PathLike[str] | str,
        method: DeletionMethod = DeletionMethod.RECYCLE,
        force_overwrite_on_flash: bool = False,
    ) -> DeletionResult:
        """Delete a single file or directory and record the result.

        ``force_overwrite_on_flash`` lets an informed caller proceed with
        overwrite passes on SSD/NVMe anyway (e.g. as a best-effort layer on top
        of TRIM). It does not change the honesty of the reported outcome.
        """
        p = Path(path)

        verdict = self.guard.check(p)
        if not verdict.safe:
            res = DeletionResult(p, DeletionOutcome.SKIPPED_UNSAFE, method, reason=verdict.reason)
            self.results.append(res)
            _LOG.warning("blocked unsafe deletion: %s (%s)", p, verdict.reason)
            return res

        try:
            _open_flags = os.O_RDONLY
            if hasattr(os, "O_NONBLOCK"):
                _open_flags |= os.O_NONBLOCK
            fd = os.open(str(p), _open_flags)
        except OSError:
            fd = -1

        if fd >= 0:
            os.close(fd)
            recheck = self.guard.check(p)
            if not recheck.safe:
                res = DeletionResult(p, DeletionOutcome.SKIPPED_UNSAFE, method,
                                     reason="TOCTOU: path changed between check and delete")
                self.results.append(res)
                return res

        size = self._size_of(p)

        if method is DeletionMethod.DRY_RUN:
            return self._record(p, DeletionOutcome.WOULD_DELETE, method, size)

        try:
            if method is DeletionMethod.RECYCLE:
                return self._recycle(p, size)
            if method is DeletionMethod.OVERWRITE:
                return self._overwrite_delete(p, size, force_overwrite_on_flash)
            return self._plain_delete(p, size)
        except OverwriteNotEffective:
            raise
        except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
            _LOG.error("deletion failed for %s: %s", p, exc)
            return self._record(p, DeletionOutcome.FAILED, method, size, reason=str(exc))

    def delete_many(
        self,
        paths: list[os.PathLike[str] | str],
        method: DeletionMethod = DeletionMethod.RECYCLE,
        progress=None,
        cancel_event=None,
        sizes: "dict[str, int] | None" = None,
    ) -> list[DeletionResult]:
        """Delete many paths efficiently.

        For RECYCLE (the common case, e.g. clearing tens of thousands of cache
        files) items are recycled in **batches** - one shell operation per batch
        instead of one per file - which is dramatically faster and lets the OS
        skip locked/in-use files without a per-file stall. ``progress(done,
        total)`` is called periodically and ``cancel_event`` stops the run.

        ``sizes`` optionally maps ``str(path) -> byte size`` (as produced by the
        scan) so we don't re-``stat`` every file just to report freed bytes.
        """
        items = [Path(p) for p in paths]
        files = [p for p in items if not p.is_dir()]
        dirs = sorted((p for p in items if p.is_dir()),
                      key=lambda d: len(d.parts), reverse=True)
        ordered = files + dirs   # files first, then deepest dirs

        if method is DeletionMethod.RECYCLE and _has_trash():
            return self._recycle_batch(ordered, progress, cancel_event, sizes=sizes)

        if method in (DeletionMethod.DELETE, DeletionMethod.DRY_RUN):
            return self._delete_batch(files, dirs, method, progress,
                                      cancel_event, sizes)

        # OVERWRITE / other: fall back to the careful per-item path.
        out: list[DeletionResult] = []
        total = len(ordered)
        for i, p in enumerate(ordered):
            if cancel_event is not None and cancel_event.is_set():
                break
            out.append(self.delete(p, method))
            if progress is not None and (i % 200 == 0 or i == total - 1):
                progress(i + 1, total)
        return out

    def _fast_safe(self, p: Path, approved: dict[str, bool]) -> bool:
        """Guard-check *p* cheaply by caching the verdict of its parent dir.

        Cache files live in huge numbers under a handful of directories, so we
        run the expensive ``resolve()``+protected-set check **once per parent
        directory** instead of once per file. Checking the parent is a valid
        proxy: if the containing directory is safe to touch, so is a file inside
        it - and for DELETE we ``unlink`` the entry itself (never following a
        symlink to its target).
        """
        parent = str(p.parent)
        verdict = approved.get(parent)
        if verdict is None:
            verdict = self.guard.check(p.parent).safe
            approved[parent] = verdict
        if not verdict:
            return False
        if p.is_symlink():
            return self.guard.check(p).safe
        return True

    def _delete_batch(self, files: list[Path], dirs: list[Path],
                      method: DeletionMethod, progress=None, cancel_event=None,
                      sizes: "dict[str, int] | None" = None) -> list[DeletionResult]:
        """Fast permanent-delete path: one guard check per directory, known
        sizes reused from the scan, direct ``unlink`` without per-file stats."""
        out: list[DeletionResult] = []
        approved: dict[str, bool] = {}
        total = len(files) + len(dirs)
        dry = method is DeletionMethod.DRY_RUN

        def _size(p: Path) -> int:
            """_size."""
            if sizes is not None:
                s = sizes.get(str(p))
                if s is not None:
                    return s
            return self._size_of(p)
            """_size."""
            """_size."""

        done = 0
        for p in files:
            if cancel_event is not None and cancel_event.is_set():
                break
            done += 1
            if not self._fast_safe(p, approved):
                out.append(self._record(p, DeletionOutcome.SKIPPED_UNSAFE, method,
                                        0, reason=self.guard.check(p).reason))
            elif dry:
                out.append(self._record(p, DeletionOutcome.WOULD_DELETE, method, _size(p)))
            else:
                size = _size(p)
                try:
                    os.unlink(p)
                    out.append(self._record(p, DeletionOutcome.DELETED,
                                            DeletionMethod.DELETE, size))
                except PermissionError:
                    out.append(self._record(p, DeletionOutcome.FAILED,
                                            DeletionMethod.DELETE, size,
                                            reason="in use / locked"))
                except OSError as exc:
                    out.append(self._record(p, DeletionOutcome.FAILED,
                                            DeletionMethod.DELETE, size, reason=str(exc)))
            if progress is not None and (done % 200 == 0 or done == total):
                progress(done, total)

        for p in dirs:   # deepest-first (already sorted by caller)
            if cancel_event is not None and cancel_event.is_set():
                break
            done += 1
            out.append(self.delete(p, method))   # dirs are few; use the safe path
            if progress is not None and (done % 50 == 0 or done == total):
                progress(done, total)
        return out

    def _recycle_batch(self, items: list[Path], progress=None,
                       cancel_event=None, chunk: int = 40,
                       sizes: "dict[str, int] | None" = None) -> list[DeletionResult]:
        """Recycle *items* in chunks; fall back to per-file only for chunks that
        contain a locked/failed item (so success stays fast)."""
        out: list[DeletionResult] = []
        total = len(items)
        done = 0
        approved: dict[str, bool] = {}
        # Resolved once for the whole batch. Callers reach this method only
        # after ``_has_trash()`` confirmed availability.
        trash = _resolve_send2trash()
        if trash is None:  # defensive: keep the honest per-item failure path
            return [self._recycle(p, self._size_of(p)) for p in items]

        def _size(p: Path) -> int:
            """_size."""
            if sizes is not None:
                s = sizes.get(str(p))
                if s is not None:
                    return s
            return self._size_of(p)
            """_size."""
            """_size."""

        for start in range(0, total, chunk):
            if cancel_event is not None and cancel_event.is_set():
                break
            group = items[start:start + chunk]
            safe: list[tuple[Path, int]] = []
            for p in group:
                if self._fast_safe(p, approved):
                    safe.append((p, _size(p)))
                else:
                    verdict = self.guard.check(p)
                    out.append(self._record(p, DeletionOutcome.SKIPPED_UNSAFE,
                                            DeletionMethod.RECYCLE, 0, reason=verdict.reason))
            if safe:
                try:
                    trash([str(p) for p, _ in safe])   # one shell op for the batch
                    for p, size in safe:
                        out.append(self._record(p, DeletionOutcome.RECYCLED,
                                                DeletionMethod.RECYCLE, size))
                except Exception:  # noqa: BLE001 - isolate which items failed
                    for p, size in safe:
                        # Fast lock pre-check (microseconds) avoids the ~1s shell
                        # error a locked file otherwise costs.
                        if self._quick_locked(p):
                            out.append(self._record(p, DeletionOutcome.FAILED,
                                                    DeletionMethod.RECYCLE, size,
                                                    reason="in use / locked"))
                            continue
                        try:
                            trash(str(p))
                            out.append(self._record(p, DeletionOutcome.RECYCLED,
                                                    DeletionMethod.RECYCLE, size))
                        except Exception as exc:  # noqa: BLE001
                            out.append(self._record(p, DeletionOutcome.FAILED,
                                                    DeletionMethod.RECYCLE, size,
                                                    reason="in use / locked"))
                            _LOG.debug("recycle failed for %s: %s", p, exc)
            done += len(group)
            if progress is not None:
                progress(min(done, total), total)
        return out

    # -- method implementations --------------------------------------------

    def _recycle(self, p: Path, size: int) -> DeletionResult:
        """_recycle."""
        trash = _resolve_send2trash()
        if trash is None:
            # Honest fallback: don't silently hard-delete when the user asked
            # for a reversible recycle. Surface it.
            return self._record(
                p, DeletionOutcome.FAILED, DeletionMethod.RECYCLE, size,
                reason="send2trash not installed; recycle unavailable "
                       "(install 'send2trash' or choose DELETE explicitly)",
            )
        trash(str(p))
        return self._record(p, DeletionOutcome.RECYCLED, DeletionMethod.RECYCLE, size)
        """_recycle."""
        """_recycle."""

    def _plain_delete(self, p: Path, size: int) -> DeletionResult:
        """_plain_delete."""
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
        return self._record(p, DeletionOutcome.DELETED, DeletionMethod.DELETE, size)
        """_plain_delete."""
        """_plain_delete."""

    @staticmethod
    def _is_cloud_placeholder(p: Path) -> bool:
        """True when *p* is a dehydrated cloud file (OneDrive Files On-Demand).

        Overwriting one is worse than useless: opening it for write forces the
        provider to download the whole file first, so we'd burn bandwidth and
        disk to shred bytes that were never here - and the cloud copy survives.
        """
        try:
            from . import winattrs
            return winattrs.is_dehydrated(winattrs.attrs_of(p.lstat()))
        except OSError:
            return False

    def _overwrite_delete(self, p: Path, size: int, force: bool) -> DeletionResult:
        """_overwrite_delete."""
        if self._is_cloud_placeholder(p):
            # Refuse rather than pretend the shred was meaningful.
            return self._record(
                p, DeletionOutcome.SKIPPED_UNSAFE, DeletionMethod.OVERWRITE, size,
                reason="cloud placeholder: the file's content is not stored on "
                       "this disk, so overwriting it would download it first and "
                       "still leave the cloud copy. Delete it from the cloud "
                       "service instead.",
            )
        kind = self.probe.probe(p).kind
        if not kind.overwrite_effective and not force:
            # Do NOT pretend. Refuse and let the caller decide.
            raise OverwriteNotEffective(kind, p)

        if p.is_dir() and not p.is_symlink():
            for child in sorted(p.rglob("*"), key=lambda c: len(c.parts), reverse=True):
                try:
                    if child.is_file() and not child.is_symlink():
                        self._overwrite_file(child)
                        child.unlink()
                    elif child.is_dir():
                        child.rmdir()
                except OSError as exc:
                    _LOG.debug("overwrite child failed %s: %s", child, exc)
            p.rmdir()
        else:
            self._overwrite_file(p)
            p.unlink()

        note = "" if kind.overwrite_effective else f"best-effort on {kind.value} (see docs)"
        return self._record(p, DeletionOutcome.OVERWRITTEN, DeletionMethod.OVERWRITE, size, reason=note)
        """_overwrite_delete."""
        """_overwrite_delete."""

    def _overwrite_file(self, p: Path) -> None:
        """Overwrite file contents in place, then flush to the physical device.

        Passes: random -> random -> zeros (final zero pass leaves no telltale
        pattern). Effective only on HDD (see module docstring).
        """
        length = p.stat().st_size
        if length == 0:
            return
        passes = self.overwrite_passes
        with open(p, "r+b", buffering=0) as fh:
            for i in range(passes):
                fh.seek(0)
                use_zero = i == passes - 1
                written = 0
                while written < length:
                    n = min(_OVERWRITE_CHUNK, length - written)
                    fh.write(b"\x00" * n if use_zero else os.urandom(n))
                    written += n
                fh.flush()
                os.fsync(fh.fileno())

    # -- helpers ------------------------------------------------------------

    def _record(self, p: Path, outcome: DeletionOutcome, method: DeletionMethod,
                size: int, reason: str = "") -> DeletionResult:
        """_record."""
        res = DeletionResult(p, outcome, method, size=size, reason=reason)
        self.results.append(res)
        return res
        """_record."""
        """_record."""

    @staticmethod
    def _quick_locked(p: Path) -> bool:
        """Cheap check: is this file exclusively locked (in use)?

        Opening for read+write fails fast (microseconds) when another process
        holds a share-deny lock (e.g. a running browser's cache), letting us
        skip it without paying the ~1s cost of a failing shell recycle call.
        """
        try:
            if not p.is_file():
                return False
            with open(p, "r+b"):
                return False
        except PermissionError:
            return True
        except OSError:
            return False   # other errors: let the real delete attempt decide

    @staticmethod
    def _size_of(p: Path) -> int:
        """_size_of."""
        try:
            if p.is_file():
                return p.stat().st_size
            total = 0
            for child in p.rglob("*"):
                try:
                    if child.is_file():
                        total += child.stat().st_size
                except OSError:
                    continue
            return total
        except OSError:
            return 0
        """_size_of."""
        """_size_of."""

    def adaptive_delete(
        self,
        path: os.PathLike[str] | str,
        level: str | None = None,
        verify: bool = True,
    ) -> DeletionResult:
        """Adaptive sanitization (PL0-PL3) per 2025 research.

        Wraps :class:`system_tools.adaptive_sanitizer.AdaptiveSanitizer`
        and maps its :class:`SanitizeResult` back into a :class:`DeletionResult`
        so callers can use the same batch accounting. Auto-picks PL when
        *level* is None (WAS-Deletion hot/cold, PULSE).
        """
        p = Path(path)
        try:
            from cortex_unified.system_tools.adaptive_sanitizer import (
                AdaptiveSanitizer,
                PrivacyLevel,
            )
            san = AdaptiveSanitizer(guard=self.guard, probe=self.probe)
            lvl = PrivacyLevel(level) if level else None
            sres = san.sanitize(p, level=lvl, verify=verify)
            outcome = DeletionOutcome.DELETED if sres.success else DeletionOutcome.FAILED
            if sres.level.value == "pl3":
                outcome = DeletionOutcome.DELETED if sres.success else DeletionOutcome.FAILED
            method = DeletionMethod.OVERWRITE if sres.level in (PrivacyLevel.PL0, PrivacyLevel.PL1) else DeletionMethod.DELETE
            return self._record(p, outcome, method, self._size_of(p),
                                reason=f"{sres.method}: {sres.message} (wear={sres.wear_cost})")
        except Exception as exc:  # noqa: BLE001
            return self._record(p, DeletionOutcome.FAILED, DeletionMethod.OVERWRITE,
                                self._size_of(p), reason=str(exc))

    def summary(self) -> dict[str, int]:
        """Aggregate counters over all recorded results."""
        agg: dict[str, int] = {"total": len(self.results), "bytes": 0}
        for r in self.results:
            agg[r.outcome.value] = agg.get(r.outcome.value, 0) + 1
            if r.succeeded and r.outcome is not DeletionOutcome.WOULD_DELETE:
                agg["bytes"] += r.size
        return agg
