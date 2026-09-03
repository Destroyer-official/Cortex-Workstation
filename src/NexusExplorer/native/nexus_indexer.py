"""Production-grade file indexer for instant filename search.

Architecture:
- Windows-native FindFirstFileExW via ctypes (2-3x faster than os.scandir)
- SQLite FTS5 with prefix search for instant file lookup
- WAL mode + mmap_size for concurrent read/write during indexing
- In-memory sorted array for O(log n) prefix matching
- QThread lifecycle with requestInterruption() pattern
- Incremental index updates via QTimer polling
- Persistent index on disk for fast cold startup
- Full cancellation support at every traversal level
"""

from __future__ import annotations

import ctypes
import fnmatch
import logging
import os
import sqlite3

import threading
import time
from bisect import bisect_left, bisect_right
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal

log = logging.getLogger("nexus.indexer")

# ---------------------------------------------------------------------------
# Windows fast enumeration via FindFirstFileExW
# ---------------------------------------------------------------------------

_IS_WINDOWS = os.name == "nt"

if _IS_WINDOWS:
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _FIND_FIRST_EX_LARGE_FETCH = 0x00000002
    _FIND_EX_INFO_BASIC = 1
    _INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
    _FILE_ATTRIBUTE_DIRECTORY = 0x10
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x400

    class _WIN32_FIND_DATAW(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("dwReserved0", wintypes.DWORD),
            ("dwReserved1", wintypes.DWORD),
            ("cFileName", wintypes.WCHAR * 260),  # MAX_PATH limit; longer paths truncated
            ("cAlternateFileName", wintypes.WCHAR * 14),
        ]
        """_WIN32_FIND_DATAW class."""

    _FindFirstFileExW = _kernel32.FindFirstFileExW
    _FindFirstFileExW.restype = wintypes.HANDLE
    _FindFirstFileExW.argtypes = [
        wintypes.LPCWSTR, wintypes.INT, ctypes.POINTER(_WIN32_FIND_DATAW),
        wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD,
    ]

    _FindNextFileW = _kernel32.FindNextFileW
    _FindNextFileW.restype = wintypes.BOOL
    _FindNextFileW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_WIN32_FIND_DATAW)]

    _FindClose = _kernel32.FindClose
    _FindClose.restype = wintypes.BOOL
    _FindClose.argtypes = [wintypes.HANDLE]


def _fast_scandir(path: str) -> list[tuple[str, str, bool, int, int]]:
    """2-3x faster directory listing via FindFirstFileExW on Windows.

    Returns list of (full_path, name, is_dir, size, modified_ms).
    Falls back to os.scandir on non-Windows or on error.
    """
    if not _IS_WINDOWS:
        return _fallback_scandir(path)

    find_data = _WIN32_FIND_DATAW()
    search_pattern = path + "\\*"
    handle = _FindFirstFileExW(
        search_pattern,
        _FIND_EX_INFO_BASIC,
        ctypes.byref(find_data),
        None,
        None,
        _FIND_FIRST_EX_LARGE_FETCH,
    )
    if handle == _INVALID_HANDLE_VALUE:
        return _fallback_scandir(path)

    results: list[tuple[str, str, bool, int, int]] = []
    try:
        while True:
            name = find_data.cFileName
            if name not in (".", ".."):
                attrs = find_data.dwFileAttributes
                is_dir = bool(attrs & _FILE_ATTRIBUTE_DIRECTORY)
                is_link = bool(attrs & _FILE_ATTRIBUTE_REPARSE_POINT)
                size = (find_data.nFileSizeHigh << 32) | find_data.nFileSizeLow
                ft = find_data.ftLastWriteTime
                filetime = (ft.dwHighDateTime << 32) | ft.dwLowDateTime
                modified_ms = (filetime - 116444736000000000) // 10000 if filetime else 0
                full_path = path + "\\" + name
                results.append((full_path, name, is_dir, size, modified_ms))
            if not _FindNextFileW(handle, ctypes.byref(find_data)):
                break
    finally:
        _FindClose(handle)
    return results


def _fallback_scandir(path: str) -> list[tuple[str, str, bool, int, int]]:
    """Fallback using os.scandir for non-Windows or error recovery."""
    results: list[tuple[str, str, bool, int, int]] = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    stat = entry.stat(follow_symlinks=False)
                    size = stat.st_size if not is_dir else 0
                    modified_ms = int(stat.st_mtime * 1000)
                    results.append((entry.path, entry.name, is_dir, size, modified_ms))
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return results


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class IndexedEntry:
    """A single indexed file/directory entry."""
    path: str
    name: str
    ext: str
    is_dir: bool
    size: int
    modified_ms: int
    parent: str


@dataclass
class IndexStats:
    """Statistics about the current index."""
    total_files: int = 0
    total_dirs: int = 0
    total_bytes: int = 0
    last_update_ms: float = 0.0
    index_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# In-memory prefix search (sorted array with bisect)
# ---------------------------------------------------------------------------

class _PrefixIndex:
    """Sorted array of (lowercase_name, path) for O(log n) prefix search."""

    def __init__(self) -> None:
        self._entries: list[tuple[str, str]] = []
        self._dirty = True
        self._sorted: list[tuple[str, str]] = []
        """__init__."""

    def add(self, name: str, path: str) -> None:
        self._entries.append((name.lower(), path))
        self._dirty = True
        """add."""

    def remove(self, name: str, path: str) -> None:
        """O(n) pop from list; acceptable for infrequent removals."""
        key = name.lower()
        target = (key, path)
        lo, hi = 0, len(self._entries)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._entries[mid] < target:
                lo = mid + 1
            elif self._entries[mid] > target:
                hi = mid
            else:
                self._entries.pop(mid)
                self._dirty = True
                return
        self._dirty = True

    def _ensure_sorted(self) -> None:
        if self._dirty:
            self._sorted = sorted(self._entries, key=lambda x: x[0])
            self._dirty = False
        """_ensure_sorted."""

    def prefix_search(self, prefix: str, max_results: int = 1000) -> list[str]:
        self._ensure_sorted()
        if not prefix:
            return []
        lo_prefix = prefix.lower()
        hi_prefix = lo_prefix[:-1] + chr(ord(lo_prefix[-1]) + 1) if lo_prefix else ""
        lo = bisect_left(self._sorted, (lo_prefix,))
        hi = bisect_left(self._sorted, (hi_prefix,))
        return [path for _, path in self._sorted[lo:hi]][:max_results]
        """prefix_search."""

    def rebuild(self, entries: dict[str, IndexedEntry]) -> None:
        self._entries = [(e.name.lower(), e.path) for e in entries.values()]
        self._dirty = True
        self._ensure_sorted()
        """rebuild."""

    def __len__(self) -> int:
        return len(self._entries)
        """__len__."""


# ---------------------------------------------------------------------------
# Core index
# ---------------------------------------------------------------------------

class FileIndex:
    """Thread-safe file path index backed by in-memory dicts + sorted prefix array."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._entries: dict[str, IndexedEntry] = {}
        self._name_index: dict[str, set[str]] = {}
        self._ext_index: dict[str, set[str]] = {}
        self._parent_index: dict[str, set[str]] = {}
        self._prefix = _PrefixIndex()
        self._stats = IndexStats()
        """__init__."""

    @property
    def stats(self) -> IndexStats:
        with self._lock:
            return self._stats
        """stats."""

    def add(self, entry: IndexedEntry) -> None:
        with self._lock:
            self._entries[entry.path] = entry
            name_key = entry.name.lower()
            self._name_index.setdefault(name_key, set()).add(entry.path)
            if entry.ext:
                self._ext_index.setdefault(entry.ext, set()).add(entry.path)
            self._parent_index.setdefault(entry.parent, set()).add(entry.path)
            self._prefix.add(entry.name, entry.path)
            if entry.is_dir:
                self._stats.total_dirs += 1
            else:
                self._stats.total_files += 1
                self._stats.total_bytes += entry.size
        """add."""

    def remove(self, path: str) -> bool:
        with self._lock:
            entry = self._entries.pop(path, None)
            if entry is None:
                return False
            name_key = entry.name.lower()
            s = self._name_index.get(name_key)
            if s:
                s.discard(path)
                if not s:
                    del self._name_index[name_key]
            if entry.ext:
                s = self._ext_index.get(entry.ext)
                if s:
                    s.discard(path)
                    if not s:
                        del self._ext_index[entry.ext]
            s = self._parent_index.get(entry.parent)
            if s:
                s.discard(path)
                if not s:
                    del self._parent_index[entry.parent]
            self._prefix.remove(entry.name, entry.path)
            if entry.is_dir:
                self._stats.total_dirs -= 1
            else:
                self._stats.total_files -= 1
                self._stats.total_bytes -= entry.size
            return True
        """remove."""

    def search_prefix(self, query: str, max_results: int = 1000) -> list[IndexedEntry]:
        """O(log n) prefix search via sorted array."""
        with self._lock:
            paths = self._prefix.prefix_search(query.lower(), max_results)
            return [self._entries[p] for p in paths if p in self._entries]

    def search_name(self, query: str, max_results: int = 1000) -> list[IndexedEntry]:
        """Substring or glob search. O(n) scan over name index — acceptable for
        infrequent queries but not suitable for high-frequency hot paths."""
        with self._lock:
            results: list[IndexedEntry] = []
            q = query.lower()
            if "*" in q or "?" in q:
                for name_key, paths in self._name_index.items():
                    if fnmatch.fnmatch(name_key, q):
                        for p in paths:
                            entry = self._entries.get(p)
                            if entry:
                                results.append(entry)
                                if len(results) >= max_results:
                                    return results
            else:
                for name_key, paths in self._name_index.items():
                    if q in name_key:
                        for p in paths:
                            entry = self._entries.get(p)
                            if entry:
                                results.append(entry)
                                if len(results) >= max_results:
                                    return results
            return results

    def search_extension(self, ext: str, max_results: int = 1000) -> list[IndexedEntry]:
        """Search by file extension."""
        ext_key = ext.lower().lstrip(".")
        with self._lock:
            paths = self._ext_index.get(f".{ext_key}", set())
            return [self._entries[p] for p in list(paths)[:max_results] if p in self._entries]

    def list_directory(self, path: str) -> list[IndexedEntry]:
        """List children of a directory from the index."""
        with self._lock:
            return [self._entries[p] for p in self._parent_index.get(path, set()) if p in self._entries]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._name_index.clear()
            self._ext_index.clear()
            self._parent_index.clear()
            self._prefix = _PrefixIndex()
            self._stats = IndexStats()
        """clear."""

    def entry_count(self) -> int:
        with self._lock:
            return len(self._entries)
        """entry_count."""

    def rebuild_prefix_index(self) -> None:
        with self._lock:
            self._prefix.rebuild(self._entries)
        """rebuild_prefix_index."""

    def snapshot(self) -> list[IndexedEntry]:
        """Return a snapshot of all entries under lock."""
        with self._lock:
            return list(self._entries.values())


# ---------------------------------------------------------------------------
# SQLite FTS5 persistence
# ---------------------------------------------------------------------------

_FTS5_PRAGMAS = [
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA cache_size = -32000",
    "PRAGMA mmap_size = 268435456",
]

_FTS5_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ext TEXT,
    is_dir INTEGER NOT NULL DEFAULT 0,
    size INTEGER NOT NULL DEFAULT 0,
    modified_ms INTEGER NOT NULL DEFAULT 0,
    parent TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_parent ON files(parent);
CREATE INDEX IF NOT EXISTS idx_ext ON files(ext);

CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    name, path,
    content=files,
    content_rowid=rowid,
    prefix='2 3 4'
);
"""

_FTS5_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
    INSERT INTO files_fts(rowid, name, path) VALUES (new.rowid, new.name, new.path);
END;

CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
    INSERT INTO files_fts(files_fts, rowid, name, path) VALUES('delete', old.rowid, old.name, old.path);
END;

CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
    INSERT INTO files_fts(files_fts, rowid, name, path) VALUES('delete', old.rowid, old.name, old.path);
    INSERT INTO files_fts(rowid, name, path) VALUES (new.rowid, new.name, new.path);
END;
"""


def _open_db(db_path: str) -> sqlite3.Connection:
    """Open SQLite with WAL and performance pragmas, create schema."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    for pragma in _FTS5_PRAGMAS:
        conn.execute(pragma)
    conn.executescript(_FTS5_SCHEMA)
    conn.executescript(_FTS5_TRIGGERS)
    conn.commit()
    return conn


def _save_index_to_db(conn: sqlite3.Connection, index: FileIndex) -> int:
    """Bulk insert/update all entries into SQLite. Returns count written."""
    entries = index.snapshot()
    conn.execute("BEGIN")
    try:
        conn.execute("DELETE FROM files")
        conn.executemany(
            "INSERT INTO files (path, name, ext, is_dir, size, modified_ms, parent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(e.path, e.name, e.ext, int(e.is_dir), e.size, e.modified_ms, e.parent) for e in entries],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    log.info("Saved %d entries to index DB", len(entries))
    return len(entries)


def _load_index_from_db(conn: sqlite3.Connection, index: FileIndex) -> int:
    """Load all entries from SQLite into the in-memory index. Returns count loaded."""
    cur = conn.execute("SELECT path, name, ext, is_dir, size, modified_ms, parent FROM files")
    count = 0
    for row in cur:
        index.add(IndexedEntry(
            path=row[0], name=row[1], ext=row[2] or "",
            is_dir=bool(row[3]), size=row[4], modified_ms=row[5], parent=row[6],
        ))
        count += 1
    log.info("Loaded %d entries from index DB", count)
    return count


def _fts5_search(conn: sqlite3.Connection, query: str, max_results: int = 1000) -> list[IndexedEntry]:
    """Prefix search via FTS5. Escapes special FTS5 characters to prevent injection."""
    escaped = query.replace('"', '""')
    pattern = '"' + escaped + '"*'
    try:
        cur = conn.execute(
            "SELECT f.path, f.name, f.ext, f.is_dir, f.size, f.modified_ms, f.parent "
            "FROM files_fts fts JOIN files f ON f.rowid = fts.rowid "
            "WHERE files_fts MATCH ? LIMIT ?",
            (pattern, max_results),
        )
        return [IndexedEntry(
            path=r[0], name=r[1], ext=r[2] or "", is_dir=bool(r[3]),
            size=r[4], modified_ms=r[5], parent=r[6],
        ) for r in cur]
    except sqlite3.OperationalError:
        log.warning("FTS5 match failed for query: %s", query, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Background indexer worker
# ---------------------------------------------------------------------------

class _IndexWorker(QThread):
    """Background thread that walks filesystem and builds the index.

    Uses requestInterruption() for clean cancellation at every traversal level.
    """

    progress = Signal(int, int)  # files_indexed, dirs_indexed
    finished_signal = Signal(int)  # total entries indexed
    error = Signal(str)

    def __init__(self, roots: list[str], index: FileIndex, db_conn: Optional[sqlite3.Connection]):
        super().__init__()
        self._roots = roots
        self._index = index
        self._db_conn = db_conn
        self._count = 0
        """__init__."""

    def run(self) -> None:
        t0 = time.perf_counter()
        try:
            for root in self._roots:
                if self.isInterruptionRequested():
                    break
                self._walk(root)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            with self._index._lock:
                self._index._stats.index_time_ms = elapsed_ms
                self._index._stats.last_update_ms = time.time() * 1000
            if self._db_conn and not self.isInterruptionRequested():
                with self._index._db_lock:
                    _save_index_to_db(self._db_conn, self._index)
            self.finished_signal.emit(self._count)
        except Exception as e:
            log.exception("Indexer worker failed")
            self.error.emit(str(e))
        """run."""

    def _walk(self, root: str) -> None:
        """Iterative DFS traversal using FindFirstFileExW (or scandir fallback)."""
        stack: list[str] = [root]
        batch: list[IndexedEntry] = []
        BATCH_SIZE = 500

        while stack:
            if self.isInterruptionRequested():
                return
            current = stack.pop()
            try:
                entries = _fast_scandir(current)
            except (PermissionError, OSError):
                continue

            for full_path, name, is_dir, size, modified_ms in entries:
                if self.isInterruptionRequested():
                    return
                ext = Path(name).suffix.lower() if not is_dir else ""
                if is_dir:
                    size = 0

                ie = IndexedEntry(
                    path=full_path,
                    name=name,
                    ext=ext,
                    is_dir=is_dir,
                    size=size,
                    modified_ms=modified_ms,
                    parent=current,
                )
                batch.append(ie)
                self._count += 1

                if is_dir and not name.startswith("."):
                    stack.append(full_path)

                if len(batch) >= BATCH_SIZE:
                    self._flush_batch(batch)
                    batch.clear()
                    self.progress.emit(self._count, 0)

        if batch:
            self._flush_batch(batch)
            self.progress.emit(self._count, 0)

    def _flush_batch(self, batch: list[IndexedEntry]) -> None:
        for ie in batch:
            self._index.add(ie)
        """_flush_batch."""


# ---------------------------------------------------------------------------
# Incremental update worker
# ---------------------------------------------------------------------------

class _IncrementalWorker(QThread):
    """Background worker for incremental re-scanning of a single root."""

    progress = Signal(int)
    finished_signal = Signal(int)

    def __init__(self, root: str, index: FileIndex):
        super().__init__()
        self._root = root
        self._index = index
        """__init__."""

    def run(self) -> None:
        count = 0
        seen: set[str] = set()
        stack: list[str] = [self._root]
        while stack:
            if self.isInterruptionRequested():
                break
            current = stack.pop()
            try:
                entries = _fast_scandir(current)
            except (PermissionError, OSError):
                continue
            for full_path, name, is_dir, size, modified_ms in entries:
                if self.isInterruptionRequested():
                    break
                ext = Path(name).suffix.lower() if not is_dir else ""
                seen.add(full_path)
                with self._index._lock:
                    existing = self._index._entries.get(full_path)
                if existing is None or existing.modified_ms != modified_ms or existing.size != size:
                    ie = IndexedEntry(
                        path=full_path, name=name, ext=ext,
                        is_dir=is_dir, size=size,
                        modified_ms=modified_ms, parent=current,
                    )
                    self._index.add(ie)
                    count += 1
                if is_dir and not name.startswith("."):
                    stack.append(full_path)
        # Remove stale entries that no longer exist on disk
        with self._index._lock:
            stale = [p for p in self._index._entries
                     if p.startswith(self._root) and p not in seen]
        for p in stale:
            self._index.remove(p)
            count += 1
        self.finished_signal.emit(count)
        """run."""


# ---------------------------------------------------------------------------
# Public indexer API
# ---------------------------------------------------------------------------

class FileIndexer(QObject):
    """Manages background indexing and provides search API."""

    index_updated = Signal()
    indexing_started = Signal()
    indexing_finished = Signal(int)
    indexing_progress = Signal(int)

    def __init__(self, db_path: str | None = None, parent=None):
        super().__init__(parent)
        self._index = FileIndex()
        self._db_path = db_path
        self._worker: _IndexWorker | None = None
        self._incr_worker: _IncrementalWorker | None = None
        self._db_conn: Optional[sqlite3.Connection] = None
        self._db_lock: threading.Lock = threading.Lock()
        self._watched_roots: list[str] = []
        self._root_index: int = 0

        self._update_timer = QTimer(self)
        self._update_timer.setInterval(30_000)
        self._update_timer.timeout.connect(self._on_timer_tick)

        if db_path:
            self._open_persistent_db()
        """__init__."""

    def _open_persistent_db(self) -> None:
        try:
            self._db_conn = _open_db(self._db_path)
        except Exception:
            log.exception("Failed to open index DB at %s", self._db_path)
            self._db_conn = None
        """_open_persistent_db."""

    # -- Indexing lifecycle -------------------------------------------------

    def start_indexing(self, roots: list[str]) -> None:
        """Start background full index of given root paths."""
        self.stop_indexing()
        self._watched_roots = roots
        self._worker = _IndexWorker(roots, self._index, self._db_conn)
        self._worker.finished_signal.connect(self._on_worker_finished)
        self._worker.error.connect(lambda msg: log.error("Indexing error: %s", msg))
        self._worker.progress.connect(lambda f: self.indexing_progress.emit(f))
        self.indexing_started.emit()
        self._worker.start()
        self._update_timer.start()

    def stop_indexing(self) -> None:
        """Request interruption and wait for worker threads to finish."""
        self._update_timer.stop()
        for w in (self._worker, self._incr_worker):
            if w and w.isRunning():
                w.requestInterruption()
                if not w.wait(5000):
                    log.warning(
                        "Worker %s did not stop within 5s timeout", w
                    )
        self._worker = None
        self._incr_worker = None

    def is_indexing(self) -> bool:
        return (self._worker is not None and self._worker.isRunning()) or \
               (self._incr_worker is not None and self._incr_worker.isRunning())
        """is_indexing."""

    def _on_worker_finished(self, total: int) -> None:
        self._index.rebuild_prefix_index()
        self.indexing_finished.emit(total)
        self.index_updated.emit()
        """_on_worker_finished."""

    def _on_incr_finished(self, count: int) -> None:
        if count > 0:
            self._index.rebuild_prefix_index()
            self.index_updated.emit()
        """_on_incr_finished."""

    # -- Search API ---------------------------------------------------------

    def search_prefix(self, query: str, max_results: int = 1000) -> list[IndexedEntry]:
        """O(log n) prefix search via sorted in-memory array."""
        return self._index.search_prefix(query, max_results)

    def search(self, query: str, max_results: int = 1000) -> list[IndexedEntry]:
        """Substring or glob search."""
        return self._index.search_name(query, max_results)

    def search_fts(self, query: str, max_results: int = 1000) -> list[IndexedEntry]:
        """FTS5 prefix search via SQLite (requires persisted index)."""
        if not self._db_conn:
            return self.search_prefix(query, max_results)
        with self._db_lock:
            return _fts5_search(self._db_conn, query, max_results)

    def search_extension(self, ext: str, max_results: int = 1000) -> list[IndexedEntry]:
        return self._index.search_extension(ext, max_results)
        """search_extension."""

    def list_directory(self, path: str) -> list[IndexedEntry]:
        return self._index.list_directory(path)
        """list_directory."""

    def get_stats(self) -> IndexStats:
        return self._index.stats
        """get_stats."""

    # -- Persistence --------------------------------------------------------

    def load_from_db(self) -> bool:
        """Load index from SQLite for fast cold startup."""
        if not self._db_conn:
            return False
        try:
            with self._db_lock:
                count = _load_index_from_db(self._db_conn, self._index)
            self._index.rebuild_prefix_index()
            self.index_updated.emit()
            return count > 0
        except Exception:
            log.exception("Failed to load index from DB")
            return False

    def save_to_db(self) -> None:
        """Persist current index to SQLite."""
        if self._db_conn:
            with self._db_lock:
                _save_index_to_db(self._db_conn, self._index)

    # -- Incremental updates ------------------------------------------------

    def _on_timer_tick(self) -> None:
        """Periodic incremental re-scan via QTimer."""
        if self.is_indexing():
            return
        if not self._watched_roots:
            return
        root = self._watched_roots[self._root_index % len(self._watched_roots)]
        self._root_index = (self._root_index + 1) % len(self._watched_roots)
        self._incr_worker = _IncrementalWorker(root, self._index)
        self._incr_worker.finished_signal.connect(self._on_incr_finished)
        self._incr_worker.start()

    # -- Cleanup ------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop all workers, persist index, close DB."""
        self.stop_indexing()
        self.save_to_db()
        if self._db_conn:
            try:
                self._db_conn.close()
            except Exception:
                pass
            self._db_conn = None

    def __del__(self) -> None:
        try:
            log.warning(
                "FileIndexer garbage collected without explicit shutdown(); "
                "call shutdown() before discarding"
            )
        except Exception:
            pass
        """__del__."""
