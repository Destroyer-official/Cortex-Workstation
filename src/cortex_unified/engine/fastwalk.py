"""High-performance filesystem traversal built on ``os.scandir``.

Per PEP 471, ``os.scandir`` is 2-20x faster than ``os.walk`` because each
``DirEntry`` caches the ``stat`` result obtained during directory iteration,
avoiding a separate ``stat`` syscall per file. The rest of this codebase used
``os.walk`` + ``Path.stat()`` (two syscalls per file); this module fixes that.

Design goals:
* Iterative (explicit stack) - no recursion limit on deep trees.
* Never follows symlinks by default (avoids cycles and escaping the root).
* Per-entry errors are collected, not fatal (permission denied, races, etc.).
* Rich, composable exclusion rules (dir names, glob patterns, regex).
* Optional cooperative cancellation and progress reporting for GUIs.
"""

from __future__ import annotations

import fnmatch
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from .models import FileEntry, ScanResult

ProgressCallback = Callable[[str, int], None]  # (current_dir, files_seen)


@dataclass(slots=True)
class WalkOptions:
    """Tunable traversal parameters."""

    exclude_dir_names: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {".git", "__pycache__", "node_modules", ".svn", ".hg", "$RECYCLE.BIN",
             "System Volume Information"}
        )
    )
    exclude_globs: tuple[str, ...] = ()
    exclude_regexes: tuple[str, ...] = ()
    follow_symlinks: bool = False
    max_depth: int | None = None
    min_size: int = 0            # only yield files >= this many bytes
    min_age_days: float = 0.0    # only yield files at least this old
    collect_dirs: bool = False   # include directory entries in results


class FastWalker:
    """Streaming, cancellable directory walker.

    Use :meth:`iter_files` for a lazy stream (best for huge trees) or
    :meth:`scan` for a materialized :class:`ScanResult` with aggregates.
    """

    def __init__(self, options: WalkOptions | None = None) -> None:
        self.options = options or WalkOptions()
        self._compiled = [re.compile(r) for r in self.options.exclude_regexes]
        self._cancel = threading.Event()

    def cancel(self) -> None:
        """Request cooperative cancellation of an in-progress walk."""
        self._cancel.set()

    def reset(self) -> None:
        self._cancel.clear()

    # -- exclusion rules ----------------------------------------------------

    def _excluded_dir(self, name: str, full: str) -> bool:
        if name in self.options.exclude_dir_names:
            return True
        return self._matches_patterns(name, full)

    def _matches_patterns(self, name: str, full: str) -> bool:
        for g in self.options.exclude_globs:
            if fnmatch.fnmatch(name, g) or fnmatch.fnmatch(full, g):
                return True
        for rx in self._compiled:
            if rx.search(full):
                return True
        return False

    # -- core traversal -----------------------------------------------------

    def iter_files(
        self,
        root: os.PathLike[str] | str,
        on_error: Callable[[str], None] | None = None,
        progress: ProgressCallback | None = None,
    ) -> Iterator[FileEntry]:
        """Yield :class:`FileEntry` for every matching file under *root*."""
        opts = self.options
        min_mtime_cutoff = (
            time.time() - opts.min_age_days * 86400.0 if opts.min_age_days > 0 else None
        )
        root_path = Path(root)
        # Stack of (dir_path, depth)
        stack: list[tuple[str, int]] = [(os.fspath(root_path), 0)]
        seen = 0

        while stack:
            if self._cancel.is_set():
                return
            current, depth = stack.pop()
            if progress is not None:
                progress(current, seen)
            try:
                it = os.scandir(current)
            except (PermissionError, FileNotFoundError, NotADirectoryError, OSError) as exc:
                if on_error is not None:
                    on_error(f"{current}: {exc}")
                continue

            with it:
                for entry in it:
                    if self._cancel.is_set():
                        return
                    try:
                        is_symlink = entry.is_symlink()
                        if entry.is_dir(follow_symlinks=opts.follow_symlinks):
                            if is_symlink and not opts.follow_symlinks:
                                continue
                            if self._excluded_dir(entry.name, entry.path):
                                continue
                            if opts.max_depth is None or depth < opts.max_depth:
                                stack.append((entry.path, depth + 1))
                            if opts.collect_dirs:
                                st = entry.stat(follow_symlinks=False)
                                yield FileEntry(
                                    Path(entry.path), 0, st.st_mtime,
                                    is_dir=True, is_symlink=is_symlink,
                                )
                            continue

                        # Regular file
                        if is_symlink and not opts.follow_symlinks:
                            continue
                        if self._matches_patterns(entry.name, entry.path):
                            continue
                        st = entry.stat(follow_symlinks=opts.follow_symlinks)
                        seen += 1
                        if st.st_size < opts.min_size:
                            continue
                        if min_mtime_cutoff is not None and st.st_mtime > min_mtime_cutoff:
                            continue
                        yield FileEntry(
                            Path(entry.path), st.st_size, st.st_mtime,
                            is_dir=False, is_symlink=is_symlink,
                        )
                    except (OSError, ValueError) as exc:
                        if on_error is not None:
                            on_error(f"{entry.path}: {exc}")
                        continue

    def scan(
        self,
        root: os.PathLike[str] | str,
        progress: ProgressCallback | None = None,
    ) -> ScanResult:
        """Materialize a full :class:`ScanResult` (files, dirs, totals, errors)."""
        self.reset()
        result = ScanResult()
        start = time.perf_counter()
        errors = result.errors

        for entry in self.iter_files(root, on_error=errors.append, progress=progress):
            if entry.is_dir:
                result.dirs.append(entry)
                result.dirs_scanned += 1
            else:
                result.files.append(entry)
                result.files_scanned += 1
                result.total_bytes += entry.size

        result.duration_seconds = time.perf_counter() - start
        return result

    def find_empty(
        self, root: os.PathLike[str] | str
    ) -> tuple[list[Path], list[Path]]:
        """Return (empty_files, empty_dirs) using a single scandir pass.

        A directory is "empty" when it has no non-excluded children (files or
        subdirs). Computed bottom-up so nested-empty chains collapse correctly.
        """
        self.reset()
        root_path = Path(root)
        empty_files: list[Path] = []
        # child_count[dir] = number of surviving (non-empty / non-excluded) children
        non_empty_children: dict[str, int] = {}
        dirs_post: list[str] = []  # post-order list of directories

        def _visit(dpath: str) -> None:
            try:
                entries = list(os.scandir(dpath))
            except OSError:
                non_empty_children[dpath] = 1  # unreadable => treat as non-empty
                return
            non_empty_children.setdefault(dpath, 0)
            for entry in entries:
                try:
                    if entry.is_symlink() and not self.options.follow_symlinks:
                        non_empty_children[dpath] += 1
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if self._excluded_dir(entry.name, entry.path):
                            continue
                        _visit(entry.path)
                        dirs_post.append(entry.path)
                        if non_empty_children.get(entry.path, 0) > 0:
                            non_empty_children[dpath] += 1
                    else:
                        st = entry.stat(follow_symlinks=False)
                        if st.st_size == 0:
                            empty_files.append(Path(entry.path))
                        else:
                            non_empty_children[dpath] += 1
                except OSError:
                    non_empty_children[dpath] += 1

        _visit(os.fspath(root_path))
        empty_dirs = [Path(d) for d in dirs_post if non_empty_children.get(d, 0) == 0]
        return empty_files, empty_dirs
