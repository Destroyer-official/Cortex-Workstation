"""Discovery and safe removal of stale files from operating-system temp locations.

Why a dedicated module
----------------------
Temporary directories are the highest-value, highest-risk cleanup target in
the application: they accumulate large amounts of cruft, yet almost any file
inside them may be *in use right now* by a running process. ``clean-temp``
therefore operates under stricter rules than the generic empty-file scanner
(:mod:`cortex_unified.core.scanner`):

1. Confinement -- only files beneath the temp roots reported by
   :meth:`TempCleaner.LOCATIONS` are ever considered. ``clean()`` re-verifies
   containment for every path before touching it; anything not provably
   inside a discovered root is refused. This is the same allowlist idea as
   :class:`cortex_unified.engine.guard.PathGuard`, applied per-root.
2. Age floor -- a file modified within ``min_age_days`` is invisible to both
   scanning *and* deletion. The age is re-checked at deletion time, so a file
   touched between ``scan()`` and ``clean()`` is never removed.
3. No link traversal -- symbolic links and Windows junctions/reparse points
   are never descended into, so a planted link cannot steer the cleaner onto
   arbitrary filesystem locations.
4. Locked means skipped -- files held open by other processes (common in
   live temp directories) fail removal on Windows; such failures are
   recorded per-path instead of aborting the batch or spamming warnings.
   During the read-only scan, entries that cannot even be ``stat``-ed are
   skipped silently at DEBUG level.

Deletion itself is routed through :class:`~cortex_unified.core.deleter.Deleter`
so temp cleanup honours the same dry-run/recycle-bin semantics (send2trash)
as every other cleaner in the application.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from cortex_unified.core.config import Config
from cortex_unified.core.deleter import Deleter

_LOG = logging.getLogger("cortex.core.temp_cleaner")

#: Traversal depth cap below each temp root. Temp trees are shallow; the cap
#: only exists so a pathological nesting (or a link loop that somehow slipped
#: past the link filters) cannot make the walk unbounded.
_MAX_DEPTH = 10

_SECS_PER_DAY = 86400


@dataclass(slots=True)
class TempFinding:
    """One deletable temp file discovered by :meth:`TempCleaner.scan`."""

    path: str
    size_bytes: int
    #: Which discovered root the file belongs to (e.g. ``"user_temp"``).
    location: str


def _normalize(path: os.PathLike[str] | str) -> str:
    """Case- and separator-normalised absolute form, for containment tests."""
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _is_junction(entry: os.DirEntry) -> bool:
    """True for Windows junctions/mount points (:mod:`os` reparse points).

    ``os.DirEntry.is_junction`` only exists on Windows (Python >= 3.12); on
    other platforms this is always False. An entry whose metadata cannot be
    probed is assumed to be a junction -- failing closed keeps links
    untraversed even when the OS refuses to describe them.
    """
    probe = getattr(entry, "is_junction", None)
    if not callable(probe):
        return False
    try:
        return bool(probe())
    except OSError:
        return True


class TempCleaner:
    """Finds and removes stale files under the platform's temp roots."""

    def __init__(
        self,
        min_age_days: int = 1,
        exclude_patterns: list[str] | None = None,
        follow_symlinks: bool = False,
    ):
        """Create a temp cleaner.

        Args:
            min_age_days: Files modified more recently than this are
                invisible to both scan and clean. Never lowered implicitly;
                ``0`` disables the age floor entirely.
            exclude_patterns: fnmatch patterns for files/directories to leave
                alone. When ``None``, the app-wide baseline from
                :class:`~cortex_unified.core.config.Config` is reused so
                protected names (``.git``, ``node_modules``, ...) stay
                untouchable even if they appear under a temp root.
            follow_symlinks: Retained for parity with
                :class:`~cortex_unified.core.scanner.Scanner`. It can never
                cause link *traversal*: directories reached through a link or
                junction are never entered. When True, a symlink pointing at
                a regular file may itself be reported; its target's metadata
                (including mtime, hence the age floor) is what gets checked.
        """
        self.min_age_days = max(0, int(min_age_days))
        if exclude_patterns is None:
            config = Config()
            self.exclude_patterns = list(config.exclude_patterns) + [
                d for d in config.exclude_dirs
            ]
        else:
            self.exclude_patterns = list(exclude_patterns)
        self.follow_symlinks = follow_symlinks

        #: Results of the most recent :meth:`scan`.
        self.findings: list[TempFinding] = []
        #: Normalised roots discovered by the most recent scan; used by
        #: :meth:`clean` to enforce confinement without re-walking.
        self._roots: list[str] = []

    @classmethod
    def LOCATIONS(cls) -> list[tuple[str, Path]]:
        """Discover the temp roots for the current platform.

        Returns:
            List of ``(label, path)`` pairs. Roots that do not exist or are
            not readable are dropped, duplicates (e.g. ``%TEMP%`` usually
            being ``%LOCALAPPDATA%\\Temp``) are collapsed, and on Windows the
            system temp is only offered when it is readable at all, so
            off-Windows and restricted hosts degrade gracefully.
        """
        candidates: list[tuple[str, Path]] = []

        if sys.platform.startswith("win"):
            user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
            if user_temp:
                candidates.append(("user_temp", Path(user_temp)))
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                candidates.append(
                    ("user_localappdata_temp", Path(local_appdata) / "Temp")
                )
            system_root = os.environ.get("SystemRoot") or r"C:\Windows"
            candidates.append(("system_temp", Path(system_root) / "Temp"))
        else:
            candidates.append(("system_tmp", Path("/tmp")))
            tmpdir = os.environ.get("TMPDIR")
            if tmpdir:
                candidates.append(("user_tmpdir", Path(tmpdir)))

        locations: list[tuple[str, Path]] = []
        seen: set[str] = set()

        def _usable(label: str, path: Path) -> bool:
            try:
                key = _normalize(path)
                if key in seen:
                    return False
                if not path.is_dir():
                    return False
                if not os.access(path, os.R_OK):
                    return False
            except OSError:
                return False
            seen.add(key)
            locations.append((label, path))
            return True
            """_usable."""

        for label, path in candidates:
            _usable(label, path)

        if sys.platform.startswith("win"):
            return locations

        # POSIX fallbacks: only reach into ~/.cache when none of the proper
        # temp roots above turned out to be usable.
        if not locations:
            _usable("user_cache", Path.home() / ".cache")
        return locations

    def _discover_locations(self) -> list[tuple[str, Path]]:
        """Resolve the temp roots for this run.

        Split from :meth:`LOCATIONS` so callers (and tests) can point the
        cleaner at scratch directories by monkeypatching either method.
        """
        return self.LOCATIONS()

    def _is_excluded(self, path: str, name: str) -> bool:
        """True when *path*/*name* hits a configured fnmatch pattern."""
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _is_old_enough(self, path: Path) -> bool:
        """True when *path*'s mtime clears the ``min_age_days`` floor.

        A file whose age cannot be determined counts as *too young*: the
        cleaner never deletes something it could not inspect.
        """
        if self.min_age_days <= 0:
            return True
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            _LOG.debug("cannot stat %s; treating as too young", path)
            return False
        return (time.time() - mtime) >= self.min_age_days * _SECS_PER_DAY

    def _walk(
        self,
        root: Path,
        label: str,
        cutoff: float,
        findings: list[TempFinding],
    ) -> None:
        """Iteratively collect eligible files under *root* (read-only)."""
        stack: list[tuple[Path, int]] = [(root, 0)]
        while stack:
            directory, depth = stack.pop()
            try:
                entries = list(os.scandir(directory))
            except OSError as exc:
                # Unreadable subtree (locked dir, permissions): skip quietly.
                _LOG.debug("skipping unreadable temp directory %s: %s",
                           directory, exc)
                continue

            for entry in entries:
                try:
                    if entry.is_symlink():
                        # Links are never traversed. Only when explicitly
                        # enabled may a link to a plain file be reported --
                        # and then the *target's* mtime enforces the age
                        # floor, so a fresh-looking link cannot sneak an old
                        # path past ``min_age_days``.
                        if not self.follow_symlinks:
                            continue
                        if not entry.is_file(follow_symlinks=True):
                            continue
                        st = entry.stat(follow_symlinks=True)
                    elif _is_junction(entry):
                        # Windows junction/mount point: never enter.
                        continue
                    elif entry.is_dir(follow_symlinks=False):
                        if depth < _MAX_DEPTH:
                            stack.append((Path(entry.path), depth + 1))
                        continue
                    elif entry.is_file(follow_symlinks=False):
                        st = entry.stat(follow_symlinks=False)
                    else:
                        # Sockets, devices, ... are never temp-cleanable.
                        continue
                except OSError as exc:
                    # In-use/locked or access-denied entries are normal in
                    # live temp directories: skip silently (DEBUG only).
                    _LOG.debug("skipping %s: %s", entry.path, exc)
                    continue

                if self.min_age_days > 0 and st.st_mtime > cutoff:
                    continue
                if self._is_excluded(entry.path, entry.name):
                    continue
                findings.append(
                    TempFinding(
                        path=entry.path,
                        size_bytes=int(st.st_size),
                        location=label,
                    )
                )

    def scan(self) -> list[TempFinding]:
        """Scan all discovered temp roots. Read-only; never raises on IO issues.

        Fresh files, excluded files, links/junctions and anything unreadable
        are skipped. Results are cached on :attr:`findings` and returned
        sorted largest-first.
        """
        findings: list[TempFinding] = []
        self._roots = []
        cutoff = time.time() - self.min_age_days * _SECS_PER_DAY

        for label, root in self._discover_locations():
            self._roots.append(_normalize(root))
            self._walk(root, label, cutoff, findings)

        findings.sort(key=lambda f: (-f.size_bytes, f.path))
        self.findings = findings
        return findings

    def total_reclaimable(self) -> int:
        """Total bytes across the most recent scan (0 before any scan)."""
        return sum(f.size_bytes for f in self.findings)

    def clean(
        self,
        findings: list[TempFinding],
        use_trash: bool = True,
        dry_run: bool = True,
    ) -> dict:
        """Delete the given findings via :class:`Deleter`.

        Every path is re-checked immediately before deletion:

        * containment -- paths outside the discovered temp roots are refused
          and counted in ``errors``;
        * age -- paths modified within ``min_age_days`` are skipped without
          counting as a failure.

        Args:
            findings: Findings from :meth:`scan` (or hand-built ones; they
                get the same scrutiny).
            use_trash: Route real deletions through send2trash.
            dry_run: Record what would happen without touching disk.

        Returns:
            ``{"deleted": n, "failed": n, "bytes_freed": b, "errors": [...]}``
            where ``deleted`` counts successful operations (in dry-run mode
            the operations that *would* run) and ``bytes_freed`` mirrors
            those operations, so dry-run totals preview the real run.
        """
        if self._roots:
            roots = self._roots
        else:
            # No scan ran in this session: derive roots on demand so the
            # confinement guarantee holds either way.
            roots = [_normalize(root) for _, root in self._discover_locations()]

        paths: list[Path] = []
        size_by_path: dict[str, int] = {}
        errors: list[dict] = []

        for finding in findings:
            path = Path(finding.path)
            normalized = _normalize(path)
            if not any(
                normalized == root or normalized.startswith(root + os.sep)
                for root in roots
            ):
                errors.append({
                    "type": "file",
                    "path": finding.path,
                    "error": "outside discovered temp roots; refused",
                })
                continue
            if not self._is_old_enough(path):
                _LOG.debug(
                    "skipping %s: modified within min_age_days=%d",
                    path, self.min_age_days,
                )
                continue
            paths.append(path)
            size_by_path[finding.path] = int(finding.size_bytes)

        deleter = Deleter(dry_run=dry_run, use_trash=use_trash)
        result = deleter.delete(paths, [])

        bytes_freed = sum(
            size_by_path.get(item["path"], 0)
            for item in deleter.deleted_items
            if item.get("action") in ("would_delete", "moved_to_trash", "deleted")
        )
        all_errors = errors + list(result["errors"])

        return {
            "deleted": int(result["files_deleted"]),
            "failed": len(all_errors),
            "bytes_freed": bytes_freed,
            "errors": all_errors,
        }
