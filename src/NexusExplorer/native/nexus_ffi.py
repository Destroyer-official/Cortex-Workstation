"""ctypes bridge to the NexusExplorer Rust engine (nexus_engine.dll).

Contract notes:
- All C strings are UTF-8; decoded lossily on the Python side.
- Pointers handed to callbacks are valid only during the callback: data is
  copied immediately, then freed via nexus_free_entries.
- CDLL calls release the GIL for their duration (Python docs), so blocking
  engine calls do not stall the Qt event loop when invoked from workers.
"""

from __future__ import annotations

__all__ = ["NexusFfi", "find_dll"]

import atexit
import ctypes
import json
import logging
import threading
from ctypes import (
    POINTER,
    byref,
    c_char_p,
    c_int,
    c_size_t,
    c_uint,
    c_uint64,
    c_void_p,
    cast,
    string_at,
)
from pathlib import Path
from typing import Any

log = logging.getLogger("nexus")

_LIB_NAME = "nexus_engine.dll"


def _dll_candidates() -> list[Path]:
    """Return candidate nexus_engine.dll paths: release then debug builds
    under the repo's target/ and src-tauri/target/ directories."""
    repo = Path(__file__).resolve().parent.parent
    return [
        repo / "target" / "release" / _LIB_NAME,
        repo / "target" / "debug" / _LIB_NAME,
        repo / "src-tauri" / "target" / "release" / _LIB_NAME,
        repo / "src-tauri" / "target" / "debug" / _LIB_NAME,
    ]
    """Return candidate nexus_engine.dll paths: release then debug builds
    under the repo's target/ and src-tauri/target/ directories."""


def find_dll() -> Path:
    """Return the first existing nexus_engine.dll candidate path.

    Raises FileNotFoundError listing all searched locations otherwise."""
    for p in _dll_candidates():
        if p.is_file():
            return p
    searched = ", ".join(str(p) for p in _dll_candidates())
    raise FileNotFoundError(f"{_LIB_NAME} not found (searched: {searched})")
    """Return the first existing nexus_engine.dll candidate path.

    Raises FileNotFoundError listing all searched locations otherwise."""


class _FileEntry(ctypes.Structure):
    """Mirrors the Rust FFI FileEntry struct: one directory row with
    name/path/parent/ext UTF-8 pointers plus size, timestamps, and
    hidden/system/readonly flags."""
    _fields_ = [
        ("name", c_void_p),
        ("path", c_void_p),
        ("parent_path", c_void_p),
        ("is_dir", c_int),
        ("size", c_uint64),
        ("modified_ms", c_uint64),
        ("created_ms", c_uint64),
        ("is_hidden", c_int),
        ("is_system", c_int),
        ("is_readonly", c_int),
        ("ext", c_void_p),
    ]
    """Mirrors the Rust FFI FileEntry struct: one directory row with
    name/path/parent/ext UTF-8 pointers plus size, timestamps, and
    hidden/system/readonly flags."""


class _DriveInfo(ctypes.Structure):
    """Mirrors the Rust FFI DriveInfo struct: drive path/label/type/filesystem
    strings, free/total bytes, and is_ready flag."""
    _fields_ = [
        ("path", c_void_p),
        ("label", c_void_p),
        ("drive_type", c_void_p),
        ("filesystem", c_void_p),
        ("free_bytes", c_uint64),
        ("total_bytes", c_uint64),
        ("is_ready", c_int),
    ]
    """Mirrors the Rust FFI DriveInfo struct: drive path/label/type/filesystem
    strings, free/total bytes, and is_ready flag."""


class _SearchOptions(ctypes.Structure):
    """Mirrors the Rust FFI SearchOptions struct: recursive and
    include_hidden flags plus max_results bound."""
    _fields_ = [("recursive", c_int), ("max_results", c_uint), ("include_hidden", c_int)]
    """Mirrors the Rust FFI SearchOptions struct: recursive and
    include_hidden flags plus max_results bound."""


SEARCH_CALLBACK = ctypes.CFUNCTYPE(
    None, c_void_p, c_void_p, c_size_t, c_int, c_char_p
)

PROGRESS_CALLBACK = ctypes.CFUNCTYPE(
    None, c_void_p, c_char_p, c_uint64, c_uint64, ctypes.c_double,
    ctypes.c_double, c_char_p,
)
COMPLETION_CALLBACK = ctypes.CFUNCTYPE(
    None, c_void_p, c_char_p, c_int, c_char_p,
)
CONFLICT_CALLBACK = ctypes.CFUNCTYPE(
    ctypes.c_int, c_void_p, c_char_p, c_char_p, c_char_p, c_char_p,
    c_uint64, c_uint64, c_uint64, c_uint64, c_int,
)


def _decode(ptr: int | None) -> str:
    """Read a NUL-terminated UTF-8 string from a raw engine pointer,
    lossily; returns '' for null pointers or read failures."""
    if not ptr:
        return ""
    try:
        return string_at(ptr).decode("utf-8", "replace")
    except (OSError, ValueError, UnicodeDecodeError):
        return ""
    """Read a NUL-terminated UTF-8 string from a raw engine pointer,
    lossily; returns '' for null pointers or read failures."""


def _row_from_entry(e: _FileEntry) -> dict:
    """Convert an FFI FileEntry into the UI row dict (name, path, isDir,
    size, modifiedMs/createdMs, isHidden/isSystem/isReadonly, dotless ext)."""
    ext = _decode(e.ext).lstrip(".").lower()
    return {
        "name": _decode(e.name),
        "path": _decode(e.path),
        "isDir": bool(e.is_dir),
        "size": int(e.size),
        "modifiedMs": int(e.modified_ms),
        "createdMs": int(e.created_ms),
        "isHidden": bool(e.is_hidden),
        "isSystem": bool(e.is_system),
        "isReadonly": bool(e.is_readonly),
        "ext": ext,
    }
    """Convert an FFI FileEntry into the UI row dict (name, path, isDir,
    size, modifiedMs/createdMs, isHidden/isSystem/isReadonly, dotless ext)."""


class NexusFfi:
    """Owns the DLL context; one instance per process is enough."""

    def __init__(self) -> None:
        """Locate and load nexus_engine.dll, marshal all exports, acquire an
        engine handle via nexus_init, and register with the atexit cleanup
        weak-set."""
        self._dll_path = find_dll()
        self._lock = threading.Lock()
        self._handle: int | None = None
        self._timeout: float | None = None
        self._dll = ctypes.CDLL(str(self._dll_path))
        self._bind()
        self._handle = self._dll.nexus_init()
        _ffi_instances.add(self)
        """Locate and load nexus_engine.dll, marshal all exports, acquire an
        engine handle via nexus_init, and register with the atexit cleanup
        weak-set."""

    # ------------------------------------------------------------------ bind
    def _bind(self) -> None:
        """Declare restype/argtypes for every engine export: init/free,
        version, read_dir (JSON + struct-array), free_entries, drives,
        home_dir, free_string, search (+cancel/last-id), rename,
        create_folder, read_text_file, orphans_json, copy/move/delete with
        progress/completion/conflict callbacks, pause/resume/cancel job,
        and free_job_handle."""
        d = self._dll
        d.nexus_init.restype = c_void_p
        d.nexus_init.argtypes = []
        d.nexus_free.restype = None
        d.nexus_free.argtypes = [c_void_p]
        d.nexus_version.restype = c_void_p
        d.nexus_version.argtypes = []

        d.nexus_read_dir_sync.restype = c_int
        d.nexus_read_dir_sync.argtypes = [
            c_void_p, c_char_p, POINTER(POINTER(_FileEntry)), POINTER(c_size_t),
        ]
        d.nexus_free_entries.restype = None
        d.nexus_free_entries.argtypes = [POINTER(_FileEntry), c_size_t]

        d.nexus_read_dir_sync_json.restype = c_int
        d.nexus_read_dir_sync_json.argtypes = [c_void_p, c_char_p, POINTER(c_void_p)]

        d.nexus_get_drives.restype = c_int
        d.nexus_get_drives.argtypes = [
            c_void_p, POINTER(POINTER(_DriveInfo)), POINTER(c_size_t),
        ]
        d.nexus_free_drives.restype = None
        d.nexus_free_drives.argtypes = [POINTER(_DriveInfo), c_size_t]

        d.nexus_home_dir.restype = c_int
        d.nexus_home_dir.argtypes = [c_void_p, POINTER(c_void_p)]
        d.nexus_free_string.restype = None
        d.nexus_free_string.argtypes = [c_void_p]

        d.nexus_search_files.restype = c_int
        d.nexus_search_files.argtypes = [
            c_void_p, c_char_p, c_char_p, POINTER(_SearchOptions),
            SEARCH_CALLBACK, c_void_p,
        ]
        d.nexus_cancel_search.restype = c_int
        d.nexus_cancel_search.argtypes = [c_void_p, c_char_p]
        d.nexus_last_search_id.restype = c_int
        d.nexus_last_search_id.argtypes = [c_void_p, POINTER(c_void_p)]

        d.nexus_rename.restype = c_int
        d.nexus_rename.argtypes = [c_void_p, c_char_p, c_char_p]
        d.nexus_create_folder.restype = c_int
        d.nexus_create_folder.argtypes = [c_void_p, c_char_p, c_char_p]
        d.nexus_read_text_file.restype = c_int
        d.nexus_read_text_file.argtypes = [
            c_void_p, c_char_p, c_uint, POINTER(c_void_p), POINTER(c_int),
            POINTER(c_uint64),
        ]

        d.nexus_orphans_json.restype = c_int
        d.nexus_orphans_json.argtypes = [POINTER(c_void_p)]

        d.nexus_copy.restype = c_void_p
        d.nexus_copy.argtypes = [
            c_void_p, POINTER(c_char_p), c_size_t, c_char_p,
            PROGRESS_CALLBACK, COMPLETION_CALLBACK, CONFLICT_CALLBACK, c_void_p,
        ]
        d.nexus_move.restype = c_void_p
        d.nexus_move.argtypes = d.nexus_copy.argtypes
        d.nexus_delete.restype = c_void_p
        d.nexus_delete.argtypes = [
            c_void_p, POINTER(c_char_p), c_size_t, c_int,
            PROGRESS_CALLBACK, COMPLETION_CALLBACK, c_void_p,
        ]
        for name in ("nexus_pause_job", "nexus_resume_job", "nexus_cancel_job"):
            fn = getattr(d, name)
            fn.restype = c_int
            fn.argtypes = [c_void_p]
        d.nexus_free_job_handle.restype = None
        d.nexus_free_job_handle.argtypes = [c_void_p]
        """Declare restype/argtypes for every engine export: init/free,
        version, read_dir (JSON + struct-array), free_entries, drives,
        home_dir, free_string, search (+cancel/last-id), rename,
        create_folder, read_text_file, orphans_json, copy/move/delete with
        progress/completion/conflict callbacks, pause/resume/cancel job,
        and free_job_handle."""

    # ------------------------------------------------------------- lifecycle
    @property
    def dll_path(self) -> Path:
        """Return the resolved path of the loaded engine DLL."""
        return self._dll_path
        """Return the resolved path of the loaded engine DLL."""

    def version(self) -> str:
        # NOTE: nexus_version returns a static string -- do NOT free it.
        """Return the engine version string from nexus_version (statically
        allocated by the DLL — never freed)."""
        p = self._dll.nexus_version()
        return _decode(p)
        """Return the engine version string from nexus_version (statically
        allocated by the DLL — never freed)."""

    def close(self) -> None:
        """Release the engine handle via nexus_free under the instance lock
        (idempotent: no-op when already closed)."""
        with self._lock:
            if getattr(self, "_handle", None):
                self._dll.nexus_free(self._handle)
                self._handle = None
        """Release the engine handle via nexus_free under the instance lock
        (idempotent: no-op when already closed)."""

    def set_timeout(self, timeout: float | None) -> None:
        """Set the transfer-job wait timeout in seconds (None restores the
        1-hour default used by _run_job)."""
        self._timeout = timeout
        """Set the transfer-job wait timeout in seconds (None restores the
        1-hour default used by _run_job)."""

    # NOTE: deliberately no __del__ — invoking into the DLL during
    # interpreter finalization risks use-after-free ordering crashes
    # (observed STATUS_HEAP_CORRUPTION). Instances must be close()d
    # explicitly or left to process teardown.

    # ------------------------------------------------------------------- fs
    def read_dir_sync(self, path: str) -> list[dict]:
        """Fast path: engine serializes JSON natively (one C-speed
        json.loads on our side). Falls back to per-row struct marshaling if
        the engine export is unavailable."""
        out = c_void_p(0)
        code = self._dll.nexus_read_dir_sync_json(
            self._handle, path.encode("utf-8"), byref(out)
        )
        if code == 0 and out:
            try:
                raw = string_at(out)
            finally:
                self._dll.nexus_free_string(out)
            # Engine already emits lowercase dotless ext and real booleans.
            return json.loads(raw.decode("utf-8", "replace"))

        out_entries = POINTER(_FileEntry)()
        out_count = c_size_t(0)
        code = self._dll.nexus_read_dir_sync(
            self._handle, path.encode("utf-8"), byref(out_entries), byref(out_count)
        )
        if code != 0:
            raise OSError(f"nexus_read_dir_sync failed ({code}) for {path!r}")
        n = out_count.value
        rows = [_row_from_entry(out_entries[i]) for i in range(n)]
        self._dll.nexus_free_entries(out_entries, n)
        return rows

    def get_drives(self) -> list[dict]:
        """Fetch drive information via nexus_get_drives and marshal each
        _DriveInfo into a dict (path, label, driveType, filesystem,
        freeBytes, totalBytes, isReady); frees the engine array."""
        out = POINTER(_DriveInfo)()
        count = c_size_t(0)
        code = self._dll.nexus_get_drives(self._handle, byref(out), byref(count))
        if code != 0:
            raise OSError(f"nexus_get_drives failed ({code})")
        drives = []
        for i in range(count.value):
            d = out[i]
            drives.append({
                "path": _decode(d.path),
                "label": _decode(d.label),
                "driveType": _decode(d.drive_type),
                "filesystem": _decode(d.filesystem),
                "freeBytes": int(d.free_bytes),
                "totalBytes": int(d.total_bytes),
                "isReady": bool(d.is_ready),
            })
        self._dll.nexus_free_drives(out, count.value)
        return drives
        """Fetch drive information via nexus_get_drives and marshal each
        _DriveInfo into a dict (path, label, driveType, filesystem,
        freeBytes, totalBytes, isReady); frees the engine array."""

    def home_dir(self) -> str:
        """Return the user's home directory from nexus_home_dir,
        freeing the engine-allocated string."""
        out = c_void_p(0)
        code = self._dll.nexus_home_dir(self._handle, byref(out))
        if code != 0 or not out:
            raise OSError("nexus_home_dir failed")
        s = _decode(out)
        self._dll.nexus_free_string(out)
        return s
        """Return the user's home directory from nexus_home_dir,
        freeing the engine-allocated string."""

    # --------------------------------------------------------------- search
    def search(
        self,
        root: str,
        query: str,
        max_results: int = 10000,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> tuple[str, list[dict]]:
        """Blocking search; returns (search_id, rows). Safe to call from a
        worker thread — waits on an Event (GIL released while waiting)."""
        opts = _SearchOptions(
            recursive=1 if recursive else 0,
            max_results=max(int(max_results), 1),
            include_hidden=1 if include_hidden else 0,
        )
        rows: list[dict] = []
        rows_lock = threading.Lock()
        finished = threading.Event()
        holder: list = []  # keeps callback trampoline alive during the call

        def on_batch(_ud, entries_ptr, count, done, err_ptr) -> None:
            """Search callback: copy the entry batch to dicts, free the
            engine array, record errors, and signal completion; always sets
            'finished' so the waiter never hangs."""
            try:
                if entries_ptr and count:
                    arr = cast(entries_ptr, POINTER(_FileEntry))
                    try:
                        batch = [_row_from_entry(arr[i]) for i in range(count)]
                    finally:
                        self._dll.nexus_free_entries(arr, count)
                    with rows_lock:
                        rows.extend(batch)
                if err_ptr:
                    log.warning("engine search error: %s", _decode(err_ptr))
                if done:
                    finished.set()
            except Exception:
                finished.set()
            """Search callback: copy the entry batch to dicts, free the
            engine array, record errors, and signal completion; always sets
            'finished' so the waiter never hangs."""

        cb = SEARCH_CALLBACK(on_batch)
        holder.append(cb)
        code = self._dll.nexus_search_files(
            self._handle,
            root.encode("utf-8"),
            query.encode("utf-8"),
            byref(opts),
            cb,
            None,
        )
        if code != 0:
            raise OSError(f"nexus_search_files failed to start ({code})")
        finished.wait(timeout=600.0)
        sid = self.last_search_id()
        return sid or "", rows

    def cancel_search(self, search_id: str | None = None) -> bool:
        """Request engine cancellation of a search (by id, or the last one
        when None); returns True on code 0."""
        raw = search_id.encode("utf-8") if search_id else None
        return self._dll.nexus_cancel_search(self._handle, raw) == 0
        """Request engine cancellation of a search (by id, or the last one
        when None); returns True on code 0."""

    def last_search_id(self) -> str | None:
        """Return the id string of the most recent engine search, or None;
        the engine string is freed after decoding."""
        out = c_void_p(0)
        code = self._dll.nexus_last_search_id(self._handle, byref(out))
        if code != 0 or not out:
            return None
        s = _decode(out)
        self._dll.nexus_free_string(out)
        return s or None
        """Return the id string of the most recent engine search, or None;
        the engine string is freed after decoding."""

    # -------------------------------------------------------------- helpers
    def rename(self, path: str, new_name: str) -> bool:
        """Rename a file or directory via nexus_rename; True on code 0."""
        return self._dll.nexus_rename(
            self._handle, path.encode("utf-8"), new_name.encode("utf-8")
        ) == 0
        """Rename a file or directory via nexus_rename; True on code 0."""

    def create_folder(self, parent: str, name: str) -> bool:
        """Create a folder under parent via nexus_create_folder; True on
        code 0."""
        return self._dll.nexus_create_folder(
            self._handle, parent.encode("utf-8"), name.encode("utf-8")
        ) == 0
        """Create a folder under parent via nexus_create_folder; True on
        code 0."""

    def read_text_file(self, path: str, max_bytes: int = 65536) -> tuple[str, bool, int]:
        """Read up to max_bytes of a text file via nexus_read_text_file.

        Returns (content, truncated_flag, total_file_size); the engine
        string is freed after decoding; non-zero codes raise OSError."""
        out = c_void_p(0)
        truncated = c_int(0)
        size = c_uint64(0)
        code = self._dll.nexus_read_text_file(
            self._handle,
            path.encode("utf-8"),
            c_uint(max_bytes),
            byref(out),
            byref(truncated),
            byref(size),
        )
        if code != 0:
            raise OSError(f"nexus_read_text_file failed ({code}) for {path!r}")
        content = _decode(out) if out else ""
        if out:
            self._dll.nexus_free_string(out)
        return content, bool(truncated.value), int(size.value)
        """Read up to max_bytes of a text file via nexus_read_text_file.

        Returns (content, truncated_flag, total_file_size); the engine
        string is freed after decoding; non-zero codes raise OSError."""


    # ------------------------------------------------------------ transfers
    @staticmethod
    def _cstr_array(items: list[str]) -> ctypes.Array[c_char_p]:
        """Build a NUL-terminated c_char_p array from Python strings
        (keeps the encoded bytes alive for the duration of the call)."""
        encoded = [s.encode("utf-8") for s in items]
        return (ctypes.c_char_p * len(encoded))(*encoded)
        """Build a NUL-terminated c_char_p array from Python strings
        (keeps the encoded bytes alive for the duration of the call)."""

    def _run_job(self, starter: Any, keep_alive: list, hooks: dict | None = None,
                 control: dict | None = None) -> dict:
        """Common plumbing: fire callbacks from the Rust worker thread,
        block on a threading.Event (GIL released), return a result dict.

        hooks:  {'progress': fn(done,total)|None,
                 'conflict': fn(info_dict)->int policy|None (default overwrite),
                 'started': fn(handle)|None}
        control: optional dict receiving {'handle': handle}.
        """
        hooks = hooks or {}
        result = {"ok": False, "error": "", "progress": [], "conflicts": []}
        done = threading.Event()
        lock = threading.Lock()

        def on_progress(_ud, _jid, done_b, total_b, speed, eta, cur):
            """Progress callback: store the latest (bytes, speed, ETA)
            snapshot under lock and forward to the hooks['progress'] fn."""
            d_b, t_b = int(done_b), int(total_b)
            sp, et = float(speed), float(eta)
            with lock:
                result["progress"] = (d_b, t_b, sp, et)
            h = hooks.get("progress")
            if h is not None:
                try:
                    h(d_b, t_b, sp, et)
                except Exception:
                    pass
            """Progress callback: store the latest (bytes, speed, ETA)
            snapshot under lock and forward to the hooks['progress'] fn."""

        def on_complete(_ud, _jid, success, err_ptr):
            """Completion callback: record ok/error and set the event that
            unblocks _run_job's waiter."""
            result["ok"] = bool(success)
            if err_ptr:
                result["error"] = err_ptr.decode("utf-8", "replace")
            done.set()
            """Completion callback: record ok/error and set the event that
            unblocks _run_job's waiter."""

        def on_conflict(_ud, _jid, cid, src, dst, ss, ds, sm, dm, is_dir):
            """Conflict callback: append a decoded info dict to the result
            and return the policy from hooks['conflict'] clamped to 0..2;
            defaults to 1 (overwrite) when no hook or hook failure."""
            dec = lambda p: p.decode("utf-8", "replace") if p else ""
            info = {"id": dec(cid), "source": dec(src),
                    "destination": dec(dst), "is_dir": bool(is_dir)}
            with lock:
                result["conflicts"].append(info)
            h = hooks.get("conflict")
            if h is not None:
                try:
                    return max(0, min(2, int(h(info))))
                except Exception:
                    pass
            return 1  # overwrite
            """Conflict callback: append a decoded info dict to the result
            and return the policy from hooks['conflict'] clamped to 0..2;
            defaults to 1 (overwrite) when no hook or hook failure."""

        progress_cb = PROGRESS_CALLBACK(on_progress)
        complete_cb = COMPLETION_CALLBACK(on_complete)
        conflict_cb = CONFLICT_CALLBACK(on_conflict)
        keep_alive.extend([progress_cb, complete_cb, conflict_cb])
        handle = starter(progress_cb, complete_cb, conflict_cb)
        if not handle:
            raise OSError("engine refused to start transfer job")
        if control is not None:
            control["handle"] = handle
        started = hooks.get("started")
        if started is not None:
            try:
                started(handle)
            except Exception:
                pass
        finished_in_time = done.wait(timeout=self._timeout or 3600.0)
        try:
            self._dll.nexus_free_job_handle(handle)
        except Exception:
            pass
        if not finished_in_time:
            raise TimeoutError("transfer job did not finish within 1h")
        return result

    def copy(
        self,
        sources: list[str],
        dest_dir: str,
        track: list | None = None,
        hooks: dict | None = None,
        control: dict | None = None,
    ) -> dict:
        """Copy sources into dest_dir via nexus_copy, reusing _run_job's
        callback plumbing and timeout; returns the job result dict."""
        arr = self._cstr_array(sources)
        dest_b = dest_dir.encode("utf-8")
        keep = list(track or [])
        return self._run_job(
            lambda pc, cc, xc: self._dll.nexus_copy(
                self._handle, arr, len(sources), dest_b, pc, cc, xc, None
            ),
            keep, hooks, control,
        )
        """Copy sources into dest_dir via nexus_copy, reusing _run_job's
        callback plumbing and timeout; returns the job result dict."""

    def move(
        self,
        sources: list[str],
        dest_dir: str,
        track: list | None = None,
        hooks: dict | None = None,
        control: dict | None = None,
    ) -> dict:
        """Move sources into dest_dir via nexus_move, reusing _run_job's
        callback plumbing and timeout; returns the job result dict."""
        arr = self._cstr_array(sources)
        dest_b = dest_dir.encode("utf-8")
        keep = list(track or [])
        return self._run_job(
            lambda pc, cc, xc: self._dll.nexus_move(
                self._handle, arr, len(sources), dest_b, pc, cc, xc, None
            ),
            keep, hooks, control,
        )
        """Move sources into dest_dir via nexus_move, reusing _run_job's
        callback plumbing and timeout; returns the job result dict."""

    def delete_paths(
        self,
        paths: list[str],
        to_trash: bool = True,
        track: list | None = None,
        hooks: dict | None = None,
        control: dict | None = None,
    ) -> dict:
        """Delete paths via nexus_delete (recycle bin when to_trash, else
        permanent); runs through _run_job but passes no conflict callback."""
        arr = self._cstr_array(paths)
        keep = list(track or [])
        return self._run_job(
            lambda pc, cc, _xc: self._dll.nexus_delete(
                self._handle, arr, len(paths), 1 if to_trash else 0,
                pc, cc, None,
            ),
            keep, hooks, control,
        )
        """Delete paths via nexus_delete (recycle bin when to_trash, else
        permanent); runs through _run_job but passes no conflict callback."""

    def orphans(self) -> list[dict]:
        """Interrupted transfers (journal-driven .nexuspart leftovers)."""
        out = c_void_p(0)
        code = self._dll.nexus_orphans_json(byref(out))
        if code != 0 or not out:
            return []
        try:
            raw = string_at(out)
        finally:
            self._dll.nexus_free_string(out)
        return json.loads(raw.decode("utf-8", "replace"))

    def pause_job(self, handle: int) -> int:
        """Request engine pause of a running job; returns the engine code."""
        return self._dll.nexus_pause_job(handle)
        """Request engine pause of a running job; returns the engine code."""

    def resume_job(self, handle: int) -> int:
        """Request engine resume of a paused job; returns the engine code."""
        return self._dll.nexus_resume_job(handle)
        """Request engine resume of a paused job; returns the engine code."""

    def cancel_job(self, handle: int) -> int:
        """Request engine cancellation of a job; returns the engine code."""
        return self._dll.nexus_cancel_job(handle)
        """Request engine cancellation of a job; returns the engine code."""


import weakref
_ffi_instances: set = weakref.WeakSet()

def _atexit_cleanup() -> None:
    """Close every still-alive NexusFfi instance at interpreter exit so
    engine handles are released deterministically before the DLL unloads."""
    for inst in list(_ffi_instances):
        try:
            inst.close()
        except Exception:
            pass
    """Close every still-alive NexusFfi instance at interpreter exit so
    engine handles are released deterministically before the DLL unloads."""

atexit.register(_atexit_cleanup)
