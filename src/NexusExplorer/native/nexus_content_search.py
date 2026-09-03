"""Content search engine for searching inside file contents.

Supports:
- Plain text search (case-sensitive/insensitive)
- Regex pattern search
- Binary file skipping
- Large file handling (streams, doesn't load entire file)
- Searchable file type detection
- Parallel search across multiple files
- Line number reporting
"""

from __future__ import annotations

import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal

log = logging.getLogger("nexus.content_search")

# File extensions that are safe to search as text
TEXT_EXTENSIONS = {
    '.txt', '.md', '.rst', '.log', '.csv', '.tsv',
    '.py', '.pyw', '.pyx', '.pxd',
    '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
    '.html', '.htm', '.css', '.scss', '.less',
    '.java', '.kt', '.scala', '.groovy',
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
    '.cs', '.fs', '.vb',
    '.go', '.rs', '.swift', '.m', '.mm',
    '.rb', '.php', '.pl', '.pm', '.r', '.R',
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    '.sql', '.graphql', '.gql',
    '.json', '.jsonl', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.xml', '.svg', '.xhtml',
    '.dockerfile', '.makefile', '.cmake',
    '.gitignore', '.gitattributes',
    '.env', '.editorconfig',
    '.lua', '.dart', '.ex', '.exs', '.erl', '.hrl',
    '.hs', '.elm', '.clj', '.cljs', '.lisp', '.el',
    '.vue', '.svelte',
}

# Skip files larger than this for content search (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Read chunk size
CHUNK_SIZE = 8192

# Maximum directory traversal depth to prevent symlink loops
MAX_DIR_DEPTH = 50


@dataclass
class ContentMatch:
    """A single content search match."""
    path: str
    line_number: int
    line_text: str
    match_start: int
    match_end: int


@dataclass
class ContentSearchResult:
    """Aggregated content search results for a file."""
    path: str
    matches: list[ContentMatch]
    truncated: bool = False


def is_searchable(path: str | Path) -> bool:
    """Check if a file is safe to search as text."""
    ext = Path(path).suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return True
    # Check files without extension (Makefile, Dockerfile, etc.)
    name = Path(path).name.lower()
    if not ext and name in ('makefile', 'dockerfile', 'gemfile', 'rakefile', 'vagrantfile'):
        return True
    return False


def search_file_content(
    path: str | Path,
    pattern: re.Pattern[str] | None = None,
    query: str = "",
    case_sensitive: bool = False,
    use_regex: bool = False,
    max_matches_per_file: int = 100,
) -> ContentSearchResult | None:
    """Search inside a single file for content matches.

    If *pattern* is provided it is used directly (pre-compiled).  Otherwise
    a pattern is compiled from *query* for backward compatibility.
    """
    try:
        file_size = os.path.getsize(path)
        if file_size > MAX_FILE_SIZE or file_size == 0:
            return None

        if not is_searchable(path):
            return None

        matches = []
        truncated = False

        if pattern is None:
            flags = 0 if case_sensitive else re.IGNORECASE
            if use_regex:
                try:
                    if len(query) > 256:
                        return None
                    pattern = re.compile(query, flags)
                except re.error as exc:
                    log.warning("Regex compilation failed for %r: %s", query, exc)
                    return None
            else:
                escaped = re.escape(query)
                pattern = re.compile(escaped, flags)

        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            line_num = 0
            for line in f:
                line_num += 1
                for m in pattern.finditer(line):
                    matches.append(ContentMatch(
                        path=str(path),
                        line_number=line_num,
                        line_text=line.rstrip('\n\r'),
                        match_start=m.start(),
                        match_end=m.end(),
                    ))
                    if len(matches) >= max_matches_per_file:
                        truncated = True
                        break
                if truncated:
                    break

        if matches:
            return ContentSearchResult(path=str(path), matches=matches, truncated=truncated)
        return None

    except (PermissionError, OSError, UnicodeDecodeError):
        return None


class _ContentSearchWorker(QThread):
    """Background thread for parallel content search."""

    result_found = Signal(ContentSearchResult)
    progress = Signal(int, int)    # files_searched, total_files
    finished_signal = Signal(int)  # total matches
    error = Signal(str)

    def __init__(
        self,
        root: str,
        query: str,
        case_sensitive: bool = False,
        use_regex: bool = False,
        max_results: int = 1000,
        file_filter: Callable[[str], bool] | None = None,
        cancel_event: threading.Event | None = None,
    ):
        """__init__."""
        super().__init__()
        self._root = root
        self._query = query
        self._case_sensitive = case_sensitive
        self._use_regex = use_regex
        self._max_results = max_results
        self._file_filter = file_filter
        self._cancel = cancel_event or threading.Event()
        """__init__."""

    def run(self):
        """run."""
        total_matches = 0
        files_searched = 0

        try:
            # Compile regex once for the entire search
            flags = 0 if self._case_sensitive else re.IGNORECASE
            if self._use_regex:
                try:
                    compiled_re = re.compile(self._query, flags)
                except re.error as exc:
                    log.warning("Regex compilation failed for %r: %s", self._query, exc)
                    self.finished_signal.emit(0)
                    return
            else:
                compiled_re = re.compile(re.escape(self._query), flags)

            total_files = 0
            BATCH_SIZE = 100
            batch: list[str] = []
            seen_dirs: set[str] = set()

            with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as executor:
                for dirpath, dirnames, filenames in os.walk(
                    self._root, onerror=lambda e: log.debug("os.walk error: %s", e)
                ):
                    if self._cancel.is_set():
                        break

                    real_path = os.path.realpath(dirpath)
                    if real_path in seen_dirs:
                        dirnames.clear()
                        continue
                    seen_dirs.add(real_path)

                    depth = len(Path(dirpath).relative_to(self._root).parts)
                    if depth > MAX_DIR_DEPTH:
                        dirnames.clear()
                        continue

                    dirnames[:] = [d for d in dirnames if not d.startswith('.')]
                    for fname in filenames:
                        if self._cancel.is_set():
                            break
                        fpath = os.path.join(dirpath, fname)
                        if self._file_filter and not self._file_filter(fpath):
                            continue
                        if is_searchable(fpath):
                            batch.append(fpath)
                            total_files += 1
                            if len(batch) >= BATCH_SIZE:
                                total_matches = self._process_batch(
                                    executor, batch, compiled_re,
                                    total_matches, files_searched, total_files,
                                )
                                files_searched += len(batch)
                                batch = []
                                if total_matches >= self._max_results:
                                    break

                    if total_matches >= self._max_results:
                        break

                if batch and total_matches < self._max_results:
                    total_matches = self._process_batch(
                        executor, batch, compiled_re,
                        total_matches, files_searched, total_files,
                    )

            self.finished_signal.emit(total_matches)

        except Exception as e:
            self.error.emit(str(e))
        """run."""

    def _process_batch(self, executor, batch, compiled_re, total_matches, files_searched, total_files):
        """_process_batch."""
        futures = {}
        for fpath in batch:
            future = executor.submit(
                search_file_content,
                fpath, compiled_re,
            )
            futures[future] = fpath

        for future in as_completed(futures):
            if self._cancel.is_set():
                break
            try:
                result = future.result()
                if result and result.matches:
                    total_matches += len(result.matches)
                    self.result_found.emit(result)
                    if total_matches >= self._max_results:
                        break
            except Exception as exc:
                log.debug("Search future failed for %s: %s",
                          futures[future], exc)

        if files_searched % 100 == 0:
            self.progress.emit(files_searched, total_files)

        return total_matches
        """_process_batch."""


class ContentSearchEngine(QObject):
    """Content search engine with background execution."""

    result_found = Signal(ContentSearchResult)
    search_started = Signal()
    search_finished = Signal(int)  # total matches
    search_progress = Signal(int, int)
    search_error = Signal(str)

    def __init__(self, parent=None):
        """__init__."""
        super().__init__(parent)
        self._worker: _ContentSearchWorker | None = None
        self._cancel = threading.Event()
        """__init__."""

    def search(
        self,
        root: str,
        query: str,
        case_sensitive: bool = False,
        use_regex: bool = False,
        max_results: int = 1000,
        file_filter: Callable[[str], bool] | None = None,
    ):
        """Start a content search."""
        self.stop()
        self._cancel.clear()

        self._worker = _ContentSearchWorker(
            root=root,
            query=query,
            case_sensitive=case_sensitive,
            use_regex=use_regex,
            max_results=max_results,
            file_filter=file_filter,
            cancel_event=self._cancel,
        )
        self._worker.result_found.connect(self.result_found.emit)
        self._worker.finished_signal.connect(self.search_finished.emit)
        self._worker.progress.connect(self.search_progress.emit)
        self._worker.error.connect(self.search_error.emit)
        self.search_started.emit()
        self._worker.start()

    def stop(self):
        """stop."""
        self._cancel.set()
        if self._worker and self._worker.isRunning():
            self._worker.wait(5000)
        self._worker = None
        """stop."""

    def is_searching(self) -> bool:
        """is_searching."""
        return self._worker is not None and self._worker.isRunning()
        """is_searching."""
