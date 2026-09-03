"""Nexus native core: engine bridge, native icons/thumbnails, table model."""

from __future__ import annotations

__all__ = [
    "Engine",
    "FileTableModel",
    "IconThumbs",
    "SortProxy",
    "find_cli",
    "human",
    "fmt_ms",
    "CLI_CANDIDATES",
    "IMAGE_EXTS",
    "MAX_THUMB_SOURCE_BYTES",
    "create_nested_folder",
    "create_nested_file",
    "scaffold_hierarchy",
    "FILE_TEMPLATES",
    "PROJECT_SCAFFOLD_PRESETS",
]

import ctypes
import ctypes.wintypes as wintypes
import json
import logging
import math
import os
import re
import shutil
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QMimeData,
    QModelIndex,
    QObject,
    QProcess,
    QRunnable,
    QSortFilterProxyModel,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QColor, QIcon, QImage, QImageReader, QPixmap
from PySide6.QtWidgets import QFileIconProvider

log = logging.getLogger("nexus")

_REPO = Path(os.environ.get(
    "NEXUS_EXPLORER_ROOT",
    str(Path(__file__).resolve().parent.parent),
))
CLI_CANDIDATES = (
    _REPO / "target" / "release" / "nexus-cli.exe",
    _REPO / "target" / "debug" / "nexus-cli.exe",
    _REPO / "src-tauri" / "target" / "release" / "nexus-cli.exe",
    _REPO / "src-tauri" / "target" / "debug" / "nexus-cli.exe",
)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico"}
MAX_THUMB_SOURCE_BYTES = 50 * 1024 * 1024


def find_cli() -> Path:
    """Locate the nexus-cli.exe binary in known build directories."""
    for p in CLI_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError(
        f"nexus-cli.exe not found in any of: {', '.join(str(p) for p in CLI_CANDIDATES)}"
        " (cargo build --release)"
    )


def human(n: int | float) -> str:
    """Format a byte count into a human-readable string (e.g. '1.2 MB')."""
    n = float(n)
    if not math.isfinite(n):
        return "?"
    if n < 0:
        return ""
    if n == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" or n >= 100 else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def fmt_ms(ms: int) -> str:
    """Format epoch-milliseconds as 'YYYY-MM-DD HH:MM'."""
    if not ms:
        return ""
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return "?"


def _parse_json(proc: QProcess) -> list[dict]:
    """_parse_json."""
    raw = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as exc:
        log.warning("JSON decode error: %s", exc)
        return []
    """_parse_json."""


def _parse_search_chunk(proc: QProcess) -> list[dict]:
    """_parse_search_chunk."""
    raw = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
    rows = []
    for line in raw.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            name_part = parts[1]
            last_sep = max(name_part.rfind("/"), name_part.rfind("\\"))
            name = name_part[last_sep + 1:] if last_sep >= 0 else name_part
            dot_idx = name.rfind(".")
            ext = name[dot_idx + 1:].lower() if dot_idx > 0 else ""
            rows.append({
                "isDir": parts[0] == "DIR", "path": parts[1], "name": name,
                "ext": ext, "size": 0, "modifiedMs": 0,
            })
    return rows
    """_parse_search_chunk."""


def _guarded(fn):
    """Wrap a QProcess callback so app-exit teardown never raises."""
    def run(*a):
        """run."""
        try:
            fn(*a)
        except RuntimeError:
            if not _SHUTTING_DOWN.is_set():
                raise
        """run."""
    return run


class _CallMarshal(QObject):
    """Delivers worker-thread results onto the thread that created Engine."""

    result_ready = Signal(object, int, list)
    dispatch = Signal(object)


_marshal: _CallMarshal | None = None
_marshal_lock = threading.Lock()
_SHUTTING_DOWN = threading.Event()


def _get_marshal() -> _CallMarshal | None:
    """_get_marshal."""
    global _marshal
    with _marshal_lock:
        if _marshal is None:
            try:
                from PySide6.QtWidgets import QApplication
                m = _CallMarshal(QApplication.instance())
                m.result_ready.connect(lambda done, code, rows: done(code, rows))
                m.dispatch.connect(lambda fn: fn())
                _marshal = m
            except (ImportError, RuntimeError):
                return None
        return _marshal
    """_get_marshal."""


def _mark_shutdown() -> None:
    """_mark_shutdown."""
    _SHUTTING_DOWN.set()
    """_mark_shutdown."""


def marshal_call(fn) -> None:
    """Run zero-arg callable on the Engine's home thread (best effort).

    Silently no-ops once shutdown began or if the Qt bridge object was
    destroyed ahead of a still-draining worker thread — the classic
    source of interpreter-teardown aborts."""
    if _SHUTTING_DOWN.is_set():
        return
    m = _get_marshal()
    if m is not None:
        try:
            m.dispatch.emit(fn)
        except RuntimeError:
            pass
    else:
        try:
            fn()
        except (RuntimeError, OSError) as exc:
            log.debug("marshal_call fallback failed: %s", exc)


class _FfiJob(QRunnable):
    """_FfiJob."""
    def __init__(self, fn, done) -> None:
        """__init__."""
        super().__init__()
        self._fn = fn
        self._done = done
        """__init__."""

    def run(self) -> None:  # runs on QThreadPool thread
        """run."""
        try:
            code, rows = self._fn()
        except Exception as exc:
            log.warning("ffi job failed: %s", exc)
            code, rows = 1, []
        if self._done is None or _SHUTTING_DOWN.is_set():
            return
        try:
            m = _get_marshal()
            if m is not None:
                m.result_ready.emit(self._done, code, rows)
            else:
                self._done(code, rows)
        except Exception as exc:
            if not _SHUTTING_DOWN.is_set():
                log.warning("ffi job callback failed: %s", exc)
        """run."""
    """_FfiJob class."""


class Engine:
    """Async engine bridge. Transport: in-process FFI when available,
    otherwise the nexus-cli.exe subprocess. Callbacks always fire on the
    thread that constructed the Engine (GUI), preserving CLI-era semantics."""

    def shutdown(self, wait_ms: int = 1500) -> None:
        """Deterministic teardown: stop dispatching results and drain the
        shared pool so no worker emits into a dying Qt/Python runtime."""
        _mark_shutdown()
        try:
            pool = QThreadPool.globalInstance()
            pool.clear()
            pool.waitForDone(int(wait_ms))
        except RuntimeError:
            pass

    def __init__(self) -> None:
        """__init__."""
        try:
            self.cli = str(find_cli())
        except FileNotFoundError as exc:
            log.debug("CLI not found: %s", exc)
            self.cli = ""
        self.transport = "cli" if self.cli else "python"
        self.ffi = None
        mode = os.environ.get("NEXUS_TRANSPORT", "auto").strip().lower()
        if mode in ("auto", "ffi"):
            try:
                from nexus_ffi import NexusFfi  # local import: optional dep

                self.ffi = NexusFfi()
                self.transport = "ffi"
                log.info("engine transport = ffi (%s)", self.ffi.dll_path.name)
            except Exception as exc:
                if mode == "ffi":
                    raise
                log.debug("FFI transport unavailable (%s); fallback to %s", exc, self.transport)
        """__init__."""

    def list_dir(self, path: str, done):
        """List directory contents asynchronously. Calls done(code, rows)."""
        if self.ffi is not None:
            return self._run_ffi(lambda: (0, self.ffi.read_dir_sync(path)), done)
        if not self.cli:
            return self._run_ffi(lambda: (0, self._python_list_dir(path)), done)
        proc = QProcess()
        proc.finished.connect(_guarded(lambda code, _s: done(code, _parse_json(proc))))
        proc.finished.connect(proc.deleteLater)
        proc.start(self.cli, ["list", path, "--json"])
        return proc

    def search(self, root: str, pattern: str, done):
        """Search for files matching pattern under root. Calls done(code, rows)."""
        if self.ffi is not None:
            return self._run_ffi(
                lambda: (0, self.ffi.search(root, pattern, max_results=5000)[1]),
                done,
            )
        if not self.cli:
            return self._run_ffi(lambda: (0, self._python_search(root, pattern)), done)
        proc = QProcess()
        rows: list[dict] = []
        proc.readyReadStandardOutput.connect(
            lambda: rows.extend(_parse_search_chunk(proc)))
        proc.finished.connect(_guarded(lambda code, _s: done(code, rows)))
        proc.finished.connect(proc.deleteLater)
        proc.start(self.cli, ["search", root, pattern, "5000"])
        return proc

    @staticmethod
    def _python_list_dir(path: str) -> list[dict]:
        """_python_list_dir."""
        rows = []
        try:
            with os.scandir(path) as it:
                for entry in it:
                    try:
                        st = entry.stat(follow_symlinks=False)
                        is_dir = entry.is_dir(follow_symlinks=False)
                        rows.append({
                            "name": entry.name,
                            "path": entry.path,
                            "isDir": is_dir,
                            "size": 0 if is_dir else st.st_size,
                            "modifiedMs": int(st.st_mtime * 1000),
                        })
                    except OSError:
                        continue
        except OSError:
            pass
        return rows
        """_python_list_dir."""

    def list_flat_branch(self, path: str, done, max_results: int = 10000):
        """Recursively list all files under path in a single flat view (Total Commander Ctrl+B style)."""
        return self._run_ffi(lambda: (0, self._python_flat_branch(path, max_results=max_results)), done)

    @staticmethod
    def _python_flat_branch(path: str, max_results: int = 10000) -> list[dict]:
        """_python_flat_branch."""
        rows = []
        try:
            for root, _, files in os.walk(path):
                for f in files:
                    full_p = os.path.join(root, f)
                    try:
                        st = os.stat(full_p, follow_symlinks=False)
                        rel = os.path.relpath(full_p, path)
                        rows.append({
                            "name": f,
                            "path": full_p,
                            "relPath": rel,
                            "isDir": False,
                            "size": st.st_size,
                            "modifiedMs": int(st.st_mtime * 1000),
                        })
                        if len(rows) >= max_results:
                            return rows
                    except OSError:
                        continue
        except OSError:
            pass
        return rows
        """_python_flat_branch."""

    @staticmethod
    def _python_search(root: str, pattern: str, max_results: int = 5000) -> list[dict]:
        """_python_search."""
        rows = []
        import fnmatch
        pat = f"*{pattern}*" if not any(c in pattern for c in "*?[]") else pattern
        roots = [r.strip() for r in root.split(";") if r.strip() and os.path.exists(r.strip())]
        if not roots and os.path.exists(root):
            roots = [root]

        for r_dir in roots:
            try:
                for dirpath, dirnames, filenames in os.walk(r_dir):
                    # Check matching directories
                    for dn in list(dirnames):
                        if fnmatch.fnmatch(dn.lower(), pat.lower()):
                            dp = os.path.join(dirpath, dn)
                            try:
                                st = os.stat(dp)
                                rows.append({
                                    "name": dn, "path": dp, "isDir": True,
                                    "size": 0, "modifiedMs": int(st.st_mtime * 1000)
                                })
                                if len(rows) >= max_results:
                                    return rows
                            except OSError:
                                pass
                    # Check matching files
                    for fn in filenames:
                        if fnmatch.fnmatch(fn.lower(), pat.lower()):
                            fp = os.path.join(dirpath, fn)
                            try:
                                st = os.stat(fp)
                                rows.append({
                                    "name": fn, "path": fp, "isDir": False,
                                    "size": st.st_size, "modifiedMs": int(st.st_mtime * 1000)
                                })
                                if len(rows) >= max_results:
                                    return rows
                            except OSError:
                                continue
            except OSError:
                pass
        return rows
        """_python_search."""

    def _run_ffi(self, job, done):
        """_run_ffi."""
        QThreadPool.globalInstance().start(_FfiJob(job, done))
        return None
        """_run_ffi."""

    def transfer(self, kind: str, sources: list[str], dest: str, parent,
                 on_done) -> object:
        """Copy or move files. Returns a QProcess or dialog handle."""
        if self.ffi is not None:
            return self._transfer_ffi(kind, sources, dest, parent, on_done)
        return self._transfer_cli(kind, sources, dest, parent, on_done)

    def _transfer_ffi(self, kind, sources, dest, parent, on_done):
        """_transfer_ffi."""
        from PySide6.QtWidgets import QLabel, QProgressBar, QProgressDialog

        dlg = QProgressDialog(f"{kind}\u2026", "Cancel", 0, 100, parent)
        dlg.setWindowTitle("Nexus Explorer")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setMinimumWidth(440)
        bar = QProgressBar()
        bar.setRange(0, 100)
        label = QLabel(f"{kind}\u2026")
        dlg.setBar(bar)
        dlg.setLabel(label)

        control: dict = {}
        state = {"cancelled": False}

        def on_progress(done_b: int, total_b: int, speed: float = 0.0,
                        eta: float = 0.0) -> None:
            """on_progress."""
            def apply():
                """apply."""
                if total_b > 0:
                    pct = min(100, int(done_b * 100 / total_b))
                    bar.setValue(pct)
                    label.setText(
                        f"{kind}: {human(done_b)} / {human(total_b)}"
                    )
                """apply."""
            try:
                marshal_call(apply)
            except RuntimeError:
                pass
            """on_progress."""

        def hooks_conflict(info) -> int:
            # default policy until the conflict dialog port lands (Stage-2b UI):
            # overwrite, matching the CLI-era silent behavior users saw least.
            """hooks_conflict."""
            _log = logging.getLogger("nexus")
            dest = info.get("destination", "")
            _log.info("conflict during %s: overwriting %s", kind, dest)
            return 1
            """hooks_conflict."""

        def start(h):
            """start."""
            control["handle"] = h
            if state["cancelled"]:
                self.ffi.cancel_job(h)
            """start."""

        def cancel_clicked():
            """cancel_clicked."""
            state["cancelled"] = True
            h = control.get("handle")
            if h:
                try:
                    self.ffi.cancel_job(h)
                except (RuntimeError, OSError) as exc:
                    log.warning("cancel_job (transfer) failed: %s", exc)
            """cancel_clicked."""

        dlg.canceled.connect(cancel_clicked)

        def job():
            """job."""
            hooks = {"progress": on_progress, "conflict": hooks_conflict,
                     "started": start}
            fn = (self.ffi.move if kind == "move"
                  else self.ffi.copy if kind == "copy" else None)
            if fn is None:
                raise ValueError(f"unsupported transfer kind {kind!r}")
            r = fn(sources, dest, hooks=hooks, control=control)
            ok = bool(r.get("ok"))
            err = r.get("error", "")
            marshal_call(lambda: (dlg.cancel(), on_done(ok, err)))
            return 0, []
            """job."""

        QThreadPool.globalInstance().start(_FfiJob(job, lambda *_: None))
        return dlg
        """_transfer_ffi."""

    def _transfer_cli(self, kind, sources, dest, parent, on_done):
        """_transfer_cli."""
        from PySide6.QtWidgets import QLabel, QProgressBar, QProgressDialog

        dlg = QProgressDialog(f"{kind}\u2026", "Cancel", 0, 100, parent)
        dlg.setWindowTitle("Nexus Explorer")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setMinimumWidth(440)
        bar = QProgressBar()
        bar.setRange(0, 100)
        label = QLabel(f"{kind}\u2026")
        dlg.setBar(bar)
        dlg.setLabel(label)

        proc = QProcess()

        def on_ready():
            """on_ready."""
            data = bytes(proc.readAllStandardError()).decode("utf-8", "replace")
            for chunk in data.split("\r"):
                m = re.search(r"\[#+-+\]\s+(\d+)%", chunk)
                if m:
                    bar.setValue(int(m.group(2)))
                fm = re.search(r"(\d+) files? \(([^)]+)\) ->", chunk)
                if fm:
                    label.setText(f"{kind}: {fm.group(1)} files ({fm.group(2)})")
                cm = re.search(r"ETA (\S+)", chunk)
                if cm:
                    dlg.setLabelText(f"{label.text()}    ETA {cm.group(1)}")
            """on_ready."""

        def on_finished(code, _s):
            """on_finished."""
            dlg.cancel()
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            on_done("completed" in out and code == 0, out.strip()[:800])
            """on_finished."""

        proc.readyReadStandardOutput.connect(on_ready)
        proc.finished.connect(_guarded(on_finished))
        if not self.cli or not os.path.exists(self.cli):
            return self._transfer_python(kind, sources, dest, dlg, on_done)
        proc.start(self.cli, [kind, *sources, "--to", dest])
        return proc
        """_transfer_cli."""

    def _transfer_python(self, kind, sources, dest, dlg, on_done):
        """_transfer_python."""
        class _TransJob(QRunnable):
            """_TransJob."""
            def run(self):
                """run."""
                dest_dir = Path(dest)
                dest_dir.mkdir(parents=True, exist_ok=True)
                errs = []
                for s in sources:
                    sp = Path(s)
                    if not sp.exists():
                        continue
                    dp = dest_dir / sp.name
                    try:
                        if sp.is_dir():
                            if kind == "move":
                                shutil.move(str(sp), str(dp))
                            else:
                                shutil.copytree(str(sp), str(dp), dirs_exist_ok=True)
                        else:
                            if kind == "move":
                                shutil.move(str(sp), str(dp))
                            else:
                                shutil.copy2(str(sp), str(dp))
                    except Exception as e:
                        errs.append(str(e))
                ok = len(errs) == 0
                msg = "; ".join(errs) if errs else "completed"
                marshal_call(lambda: (dlg.cancel(), on_done(ok, msg)))
                """run."""
            """_TransJob class."""

        QThreadPool.globalInstance().start(_TransJob())
        return dlg
        """_transfer_python."""

    def delete(self, paths: list[str], permanent: bool, parent, on_done) -> object:
        """Delete files (to trash or permanently). Returns a QProcess or dialog handle."""
        if self.ffi is not None:
            return self._delete_ffi(paths, permanent, parent, on_done)
        if not self.cli or not os.path.exists(self.cli):
            return self._delete_python(paths, permanent, on_done)
        return self._delete_cli(paths, permanent, parent, on_done)

    def _delete_python(self, paths, permanent, on_done):
        """_delete_python."""
        class _DelJob(QRunnable):
            """_DelJob."""
            def run(self):
                """run."""
                errs = []
                for p in paths:
                    try:
                        if not permanent:
                            try:
                                import send2trash
                                send2trash.send2trash(p)
                            except Exception:
                                if os.path.isdir(p):
                                    shutil.rmtree(p, ignore_errors=True)
                                else:
                                    os.remove(p)
                        else:
                            if os.path.isdir(p):
                                shutil.rmtree(p, ignore_errors=True)
                            else:
                                os.remove(p)
                    except Exception as e:
                        errs.append(str(e))
                ok = len(errs) == 0
                msg = "; ".join(errs) if errs else f"Deleted {len(paths)} item(s)"
                marshal_call(lambda: on_done(ok, msg))
                """run."""
            """_DelJob class."""

        QThreadPool.globalInstance().start(_DelJob())
        return None
        """_delete_python."""

    def _delete_ffi(self, paths, permanent, parent, on_done):
        """_delete_ffi."""
        from PySide6.QtWidgets import QProgressDialog

        dlg = QProgressDialog("Deleting\u2026", "Cancel", 0, 0, parent)
        dlg.setWindowTitle("Nexus Explorer")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        control: dict = {}
        state = {"cancelled": False}

        def cancel_clicked():
            """cancel_clicked."""
            state["cancelled"] = True
            h = control.get("handle")
            if h:
                try:
                    self.ffi.cancel_job(h)
                except (RuntimeError, OSError) as exc:
                    log.warning("cancel_job (delete) failed: %s", exc)
            """cancel_clicked."""

        dlg.canceled.connect(cancel_clicked)

        def job():
            """job."""
            r = self.ffi.delete_paths(
                paths, to_trash=not permanent,
                control=control,
            )
            ok = bool(r.get("ok"))
            err = r.get("error", "")
            marshal_call(lambda: (dlg.cancel(), on_done(ok, err)))
            return 0, []
            """job."""

        QThreadPool.globalInstance().start(_FfiJob(job, lambda *_: None))
        return dlg
        """_delete_ffi."""

    def _delete_cli(self, paths, permanent, parent, on_done):
        """_delete_cli."""
        from PySide6.QtWidgets import QProgressDialog

        dlg = QProgressDialog("Deleting\u2026", "Cancel", 0, 0, parent)
        dlg.setWindowTitle("Nexus Explorer")
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        proc = QProcess()

        def fin(code, _s):
            """fin."""
            dlg.cancel()
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            on_done(code == 0, out)
            """fin."""

        proc.finished.connect(_guarded(fin))
        proc.finished.connect(proc.deleteLater)
        dlg.canceled.connect(proc.kill)
        args = ["delete"] + (["--permanent"] if permanent else []) + paths
        proc.start(self.cli, args)
        return proc
        """_delete_cli."""

    def simple(self, args: list[str], on_done):
        """Run a simple CLI command and call on_done(ok, stdout, stderr)."""
        if not self.cli or not os.path.exists(self.cli):
            return self._simple_python(args, on_done)
        proc = QProcess()
        proc.finished.connect(_guarded(lambda code, _s: on_done(
            code == 0,
            bytes(proc.readAllStandardOutput()).decode("utf-8", "replace").strip(),
            bytes(proc.readAllStandardError()).decode("utf-8", "replace").strip(),
        )))
        proc.finished.connect(proc.deleteLater)
        proc.start(self.cli, args)
        return proc

    @staticmethod
    def _simple_python(args: list[str], on_done):
        """_simple_python."""
        if not args:
            on_done(True, "", "")
            return None
        cmd = args[0]
        if cmd == "rename" and len(args) >= 3:
            old_path = args[1]
            new_name_or_path = args[2]
            try:
                old_p = Path(old_path)
                if os.path.isabs(new_name_or_path):
                    new_p = Path(new_name_or_path)
                else:
                    new_p = old_p.parent / new_name_or_path
                # Check for same name or existing target
                if old_p.resolve() != new_p.resolve() and new_p.exists():
                    on_done(False, "", f"Target '{new_p.name}' already exists.")
                    return None
                old_p.rename(new_p)
                on_done(True, f"Renamed to {new_p.name}", "")
            except Exception as e:
                on_done(False, "", str(e))
        elif cmd == "mkdir" and len(args) > 1:
            try:
                os.makedirs(args[1], exist_ok=True)
                on_done(True, "", "")
            except OSError as e:
                on_done(False, "", str(e))
        elif cmd == "delete" and len(args) > 1:
            permanent = "--permanent" in args
            paths = [a for a in args[1:] if a != "--permanent"]
            errs = []
            for p in paths:
                try:
                    if not permanent:
                        try:
                            import send2trash
                            send2trash.send2trash(p)
                        except Exception:
                            if os.path.isdir(p):
                                shutil.rmtree(p, ignore_errors=True)
                            else:
                                os.remove(p)
                    else:
                        if os.path.isdir(p):
                            shutil.rmtree(p, ignore_errors=True)
                        else:
                            os.remove(p)
                except Exception as e:
                    errs.append(str(e))
            if errs:
                on_done(False, "", "; ".join(errs))
            else:
                on_done(True, f"Deleted {len(paths)} item(s)", "")
        elif cmd == "drives":
            drives = []
            import string
            for letter in string.ascii_uppercase:
                dp = f"{letter}:\\"
                if os.path.exists(dp):
                    try:
                        import shutil
                        usage = shutil.disk_usage(dp)
                        drives.append({
                            "path": f"{letter}:",
                            "totalBytes": usage.total,
                            "freeBytes": usage.free,
                        })
                    except OSError:
                        drives.append({"path": f"{letter}:", "totalBytes": 0, "freeBytes": 0})
            on_done(True, json.dumps(drives), "")
        elif cmd == "hash" and len(args) > 1:
            p = args[1]
            try:
                import hashlib
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    while chunk := f.read(65536):
                        h.update(chunk)
                on_done(True, h.hexdigest(), "")
            except Exception as e:
                on_done(False, "", str(e))
        else:
            on_done(True, "", "")
        return None
        """_simple_python."""


# ---------------------------------------------------------------------------
# Native Windows icons + image thumbnails
# ---------------------------------------------------------------------------
class _SHFILEINFO(ctypes.Structure):
    """_SHFILEINFO."""
    _fields_ = [("hIcon", ctypes.c_void_p), ("iIcon", ctypes.c_int),
                ("dwAttributes", ctypes.c_uint32),
                ("szDisplayName", ctypes.c_wchar * 260),
                ("szTypeName", ctypes.c_wchar * 80)]
    """_SHFILEINFO class."""


class _ICONINFO(ctypes.Structure):
    """_ICONINFO."""
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]
    """_ICONINFO class."""


class _BMIH(ctypes.Structure):
    """_BMIH."""
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]
    """_BMIH class."""


def _hicon_to_qicon(hicon, size: int = 32) -> QIcon:
    """_hicon_to_qicon."""
    info = _ICONINFO()
    if not ctypes.windll.user32.GetIconInfo(hicon, ctypes.byref(info)):
        return QIcon()
    try:
        bmi = _BMIH()
        bmi.biSize = ctypes.sizeof(bmi)
        bmi.biWidth, bmi.biHeight = size, -size
        bmi.biPlanes, bmi.biBitCount = 1, 32
        buf = ctypes.create_string_buffer(size * size * 4)
        hdc = ctypes.windll.user32.GetDC(0)
        try:
            ctypes.windll.gdi32.GetDIBits(hdc, info.hbmColor, 0, size, buf,
                                          ctypes.byref(bmi), 0)
        finally:
            ctypes.windll.user32.ReleaseDC(0, hdc)
        img = QImage(buf, size, size, size * 4, QImage.Format.Format_ARGB32)
        return QIcon(QPixmap.fromImage(img.copy()))
    finally:
        if info.hbmMask:
            ctypes.windll.gdi32.DeleteObject(info.hbmMask)
        if info.hbmColor:
            ctypes.windll.gdi32.DeleteObject(info.hbmColor)
        ctypes.windll.user32.DestroyIcon(info.hIcon)
    """_hicon_to_qicon."""


class IconThumbs:
    """Manages file/folder icons and image thumbnails with an LRU cache."""
    THUMB = 96
    _MAX_THUMBS = 2000
    _SHGFI_ICON = 0x100
    _SHGFI_SMALLICON = 0x1

    def __init__(self) -> None:
        """__init__."""
        self.provider = QFileIconProvider()
        self._dir: QIcon | None = None
        self._file: QIcon | None = None
        self._ext: dict[str, QIcon] = {}
        self._thumbs: OrderedDict[str, QIcon] = OrderedDict()
        self._fluent_ext_fn = None  # set by ExplorerWidget for Fluent icons
        """__init__."""

    def set_fluent_ext_icon(self, fn):
        """Set a callable ext -> QIcon for Fluent Design file-type icons."""
        self._fluent_ext_fn = fn

    def dir_icon(self, name: str = "") -> QIcon:
        """dir_icon."""
        try:
            from nexus_icons import folder_icon
            ico = folder_icon(name, 32)
            if not ico.isNull():
                return ico
        except Exception as exc:
            log.debug("folder_icon failed: %s", exc)
        # Fallback to OS shell folder icon
        if self._dir is None:
            self._dir = self.provider.icon(QFileIconProvider.IconType.Folder)
        return self._dir
        """dir_icon."""

    def _file_icon(self) -> QIcon:
        """_file_icon."""
        if self._file is None:
            self._file = self.provider.icon(QFileIconProvider.IconType.File)
        return self._file
        """_file_icon."""

    def ext_icon(self, ext: str) -> QIcon:
        """ext_icon."""
        key = ext.lower().lstrip(".")
        ico = self._ext.get(key)
        if ico is None:
            try:
                from nexus_icons import icon_for_ext
                ico = icon_for_ext(f".{key}" if key else "", 32)
            except Exception as exc:
                log.debug("icon_for_ext failed for %s: %s", ext, exc)
                ico = None
            if ico is None or ico.isNull():
                if self._fluent_ext_fn is not None:
                    try:
                        ico = self._fluent_ext_fn(ext)
                    except Exception:
                        ico = None
            # Fall back to Windows shell icon
            if ico is None or ico.isNull():
                sh = _SHFILEINFO()
                ctypes.windll.shell32.SHGetFileInfoW(
                    f"a.{key}" if key else "a", 0, ctypes.byref(sh),
                    ctypes.sizeof(sh), self._SHGFI_ICON | self._SHGFI_SMALLICON)
                if sh.hIcon:
                    ico = _hicon_to_qicon(sh.hIcon, 32)
                    ctypes.windll.user32.DestroyIcon(sh.hIcon)
                else:
                    ico = self._file_icon()
            self._ext[key] = ico
        return ico
        """ext_icon."""

    def icon_for(self, row: dict) -> QIcon:
        """icon_for."""
        if row.get("isDir"):
            return self.dir_icon(row.get("name", ""))
        path = row.get("path", "")
        ext = "." + (row.get("ext") or "").lower()
        norm_path = os.path.normcase(path).lower()
        hit = self._thumbs.get(norm_path)
        if hit is not None:
            self._thumbs.move_to_end(norm_path)
            return hit
        if ext in IMAGE_EXTS and path and self._thumb_source_ok(path):
            reader = QImageReader(path)
            reader.setAutoTransform(True)
            try:
                src = reader.size()
                if src.isValid() and src.width() > 0 and src.height() > 0:
                    scaled = src.scaled(
                        self.THUMB, self.THUMB,
                        Qt.AspectRatioMode.KeepAspectRatio,
                    )
                    reader.setScaledSize(scaled)
            except (RuntimeError, ValueError) as exc:
                log.debug("thumbnail scale failed for %s: %s", path, exc)
            img = reader.read()
            if img.isNull():
                return self.ext_icon(ext)
            if (img.width() > self.THUMB or img.height() > self.THUMB):
                img = img.scaled(self.THUMB, self.THUMB,
                                 Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
            ico = QIcon(QPixmap.fromImage(img))
            if len(self._thumbs) >= self._MAX_THUMBS:
                self._thumbs.popitem(last=False)
            self._thumbs[norm_path] = ico
            return ico
        return self.ext_icon(ext)
        """icon_for."""

    @staticmethod
    def _thumb_source_ok(path: str) -> bool:
        """_thumb_source_ok."""
        try:
            return os.path.getsize(path) <= MAX_THUMB_SOURCE_BYTES
        except OSError:
            return False
        """_thumb_source_ok."""


# ---------------------------------------------------------------------------
# Model + proxy
# ---------------------------------------------------------------------------
class FileTableModel(QAbstractTableModel):
    """Table model for file/directory listings with icon, name, date, type, size columns."""
    HEADERS = ["Name", "Modified", "Type", "Size"]

    # Cached Qt enums for hot-path performance (avoids repeated attribute lookup)
    _ROLE_DISPLAY = Qt.ItemDataRole.DisplayRole
    _ROLE_DECORATION = Qt.ItemDataRole.DecorationRole
    _ROLE_USER = Qt.ItemDataRole.UserRole
    _ROLE_FOREGROUND = Qt.ItemDataRole.ForegroundRole
    _ROLE_CHECKSTATE = Qt.ItemDataRole.CheckStateRole
    _ORIENT_HORIZONTAL = Qt.Orientation.Horizontal

    def __init__(self, icons: IconThumbs) -> None:
        """__init__."""
        super().__init__()
        self.rows: list[dict] = []
        self.icons = icons
        self._tags = None  # ColorTagManager set by ExplorerWidget
        """__init__."""

    def set_tags_manager(self, tags):
        """Set the ColorTagManager for color tag indicators."""
        self._tags = tags

    @staticmethod
    def _precompute(rows: list[dict]) -> None:
        """_precompute."""
        for row in rows:
            row["modifiedStr"] = fmt_ms(int(row.get("modifiedMs", 0) or 0))
            row["sizeStr"] = human(row.get("size", 0))
        """_precompute."""

    def set_rows(self, rows: list[dict]) -> None:
        """set_rows."""
        self.beginResetModel()
        self._precompute(rows)
        self.rows = rows
        self.endResetModel()
        """set_rows."""

    _DIFF_KEYS = ("name", "size", "modifiedMs", "isDir", "folderSize")

    def update_rows(self, rows: list[dict]) -> None:
        """Hybrid refresh.

        Pure metadata changes (same path set) are applied incrementally via
        dataChanged — the hot path for watcher-driven refreshes. Structural
        changes (additions/removals) currently take the atomic-reset path:
        emitting begin/end* around live mutations raced with the attached
        QSortFilterProxyModel's lessThan() (stale-index crashes), and correct
        position-aware sorted insertion is deferred to the Stage-2 model
        redesign.
        """
        self._precompute(rows)
        old_paths = {r.get("path") for r in self.rows}
        new_paths = {r.get("path") for r in rows}

        if old_paths == new_paths:
            changed: list[int] = []
            for i, r in enumerate(rows):
                old = self.rows[i]
                if any(old.get(k) != r.get(k) for k in self._DIFF_KEYS):
                    self.rows[i] = r
                    changed.append(i)
            if changed:
                changed.sort()
                start = prev = changed[0]
                for i in changed[1:]:
                    if i == prev + 1:
                        prev = i
                        continue
                    self._emit_changed(start, prev)
                    start = prev = i
                self._emit_changed(start, prev)
            return

        self.set_rows(rows)

    def _emit_changed(self, row_a: int, row_b: int) -> None:
        """_emit_changed."""
        top = self.index(min(row_a, row_b), 0)
        bottom = self.index(max(row_a, row_b), self.columnCount() - 1)
        self.dataChanged.emit(top, bottom)
        """_emit_changed."""

    def rowCount(self, parent=QModelIndex()):
        """rowCount."""
        return 0 if parent.isValid() else len(self.rows)
        """rowCount."""

    def columnCount(self, parent=QModelIndex()):
        """columnCount."""
        return 4
        """columnCount."""

    def headerData(self, section, orient, role=Qt.ItemDataRole.DisplayRole):
        """headerData."""
        if role == self._ROLE_DISPLAY and orient == self._ORIENT_HORIZONTAL:
            return self.HEADERS[section]
        return None
        """headerData."""

    def index(self, r, c, parent=QModelIndex()):
        """index."""
        return self.createIndex(r, c)
        """index."""

    def parent(self, _child=None):
        """parent."""
        return QModelIndex()
        """parent."""

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        """data."""
        if not idx.isValid():
            return None
        row = self.rows[idx.row()]
        col = idx.column()
        if role == self._ROLE_DISPLAY:
            if col == 0:
                return row.get("name", "")
            if col == 1:
                return row.get("modifiedStr", "")
            if col == 2:
                return "Folder" if row.get("isDir") else (row.get("ext") or "File").upper()
            if col == 3:
                if row.get("isDir"):
                    sz = row.get("folderSize")
                    return human(sz) if sz is not None else ""
                return row.get("sizeStr", "")
        if role == self._ROLE_DECORATION and col == 0:
            return self.icons.icon_for(row)
        if role == self._ROLE_USER:
            return row
        # Color tag indicator — small colored circle before name
        if role == self._ROLE_FOREGROUND and col == 0:
            if self._tags:
                path = row.get("path", "")
                tag = self._tags.get_tag(path)
                if tag:
                    return QColor(self._tags.TAG_COLORS.get(tag, "#ffffff"))
        return None
        """data."""

    def flags(self, index):
        """flags."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        """flags."""

    def mimeTypes(self) -> list[str]:
        """mimeTypes."""
        return ["text/uri-list", "text/plain"]
        """mimeTypes."""

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        """mimeData."""
        mime = QMimeData()
        urls = []
        paths = []
        seen_rows = set()
        for idx in indexes:
            r = idx.row()
            if r not in seen_rows:
                seen_rows.add(r)
                if 0 <= r < len(self.rows):
                    p = self.rows[r].get("path")
                    if p:
                        paths.append(p)
                        urls.append(QUrl.fromLocalFile(p))
        mime.setUrls(urls)
        mime.setText("\n".join(paths))
        return mime
        """mimeData."""

    def supportedDragActions(self) -> Qt.DropAction:
        """supportedDragActions."""
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        """supportedDragActions."""


class SortProxy(QSortFilterProxyModel):
    """Sort proxy that keeps directories first and sorts by column-specific logic."""
    def __init__(self) -> None:
        """__init__."""
        super().__init__()
        self.setFilterKeyColumn(0)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        """__init__."""

    def flags(self, index):
        """flags."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        """flags."""

    def supportedDragActions(self) -> Qt.DropAction:
        """supportedDragActions."""
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
        """supportedDragActions."""

    def lessThan(self, left, right):
        """lessThan."""
        m: FileTableModel = self.sourceModel()  # type: ignore[assignment]
        lr, rr = left.row(), right.row()
        if lr >= len(m.rows) or rr >= len(m.rows) or lr < 0 or rr < 0:
            return False
        a, b = m.rows[lr], m.rows[rr]
        if a.get("isDir") != b.get("isDir"):
            return bool(a.get("isDir"))
        col = left.column()
        if col == 1:
            return (a.get("modifiedMs", 0) or 0) < (b.get("modifiedMs", 0) or 0)
        if col == 3:
            sa = a.get("folderSize") if a.get("isDir") else a.get("size", 0)
            sb = b.get("folderSize") if b.get("isDir") else b.get("size", 0)
            return (sa or 0) < (sb or 0)
        return a.get("name", "").lower() < b.get("name", "").lower()
        """lessThan."""


# ---------------------------------------------------------------------------
# UI helpers — imported by explorer UI modules
# ---------------------------------------------------------------------------

def _draw_transfer(painter, rect, active: bool):
    """Draw transfer indicator icon for painter-based buttons."""
    from PySide6.QtGui import QPen
    painter.save()
    painter.setRenderHint(painter.RenderHint.Antialiasing)
    color = QColor("#3daee9") if active else QColor("#888888")
    painter.setPen(QPen(color, 2))
    painter.setBrush(color)
    cx, cy = rect.center().x(), rect.center().y()
    painter.drawEllipse(cx - 4, cy - 4, 8, 8)
    painter.restore()


# ---------------------------------------------------------------------------
# Templates & Scaffolding Engine
# ---------------------------------------------------------------------------

FILE_TEMPLATES = {
    ".py": {
        "label": "Python Module (.py)",
        "content": '"""\nModule Description\n"""\n\n\ndef main():\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
    },
    ".ts": {
        "label": "TypeScript File (.ts)",
        "content": 'export interface Config {\n  id: string;\n  enabled: boolean;\n}\n\nexport function initialize(): void {\n  console.log("Initialized");\n}\n',
    },
    ".tsx": {
        "label": "React Component (.tsx)",
        "content": "import React from 'react';\n\nexport interface Props {\n  title?: string;\n}\n\nexport const Component: React.FC<Props> = ({ title }) => {\n  return (\n    <div>\n      <h2>{title || 'Component'}</h2>\n    </div>\n  );\n};\n",
    },
    ".js": {
        "label": "JavaScript File (.js)",
        "content": "'use strict';\n\nfunction main() {\n  // Code here\n}\n\nmodule.exports = { main };\n",
    },
    ".json": {
        "label": "JSON Document (.json)",
        "content": '{\n  "$schema": "http://json-schema.org/draft-07/schema#",\n  "version": "1.0.0",\n  "name": "project",\n  "data": {}\n}\n',
    },
    ".md": {
        "label": "Markdown Document (.md)",
        "content": "# Document Title\n\n## Overview\n\nDescribe your document here.\n\n## Features\n\n- Feature 1\n- Feature 2\n",
    },
    ".html": {
        "label": "HTML5 Document (.html)",
        "content": '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>Document</title>\n</head>\n<body>\n  <h1>Hello World</h1>\n</body>\n</html>\n',
    },
    ".css": {
        "label": "CSS Stylesheet (.css)",
        "content": "/* Modern CSS Reset & Baseline */\n*,\n*::before,\n*::after {\n  box-sizing: border-box;\n  margin: 0;\n  padding: 0;\n}\n\nbody {\n  font-family: system-ui, -apple-system, sans-serif;\n  line-height: 1.5;\n}\n",
    },
    ".yaml": {
        "label": "YAML Configuration (.yaml)",
        "content": "version: '1.0'\nservices:\n  app:\n    image: node:alpine\n    ports:\n      - '3000:3000'\n",
    },
    ".yml": {
        "label": "YAML Configuration (.yml)",
        "content": "version: '1.0'\nsettings:\n  enabled: true\n",
    },
    ".txt": {
        "label": "Text Document (.txt)",
        "content": "",
    },
    ".sh": {
        "label": "Shell Script (.sh)",
        "content": "#!/usr/bin/env bash\nset -euo pipefail\n\necho 'Starting execution...'\n",
    },
}

PROJECT_SCAFFOLD_PRESETS = {
    "FastAPI Microservice": (
        "app/\n"
        "  api/\n"
        "    v1/\n"
        "      endpoints/\n"
        "        __init__.py\n"
        "        auth.py\n"
        "        users.py\n"
        "      __init__.py\n"
        "      router.py\n"
        "    __init__.py\n"
        "  core/\n"
        "    __init__.py\n"
        "    config.py\n"
        "    security.py\n"
        "  models/\n"
        "    __init__.py\n"
        "    user.py\n"
        "  services/\n"
        "    __init__.py\n"
        "  main.py\n"
        "tests/\n"
        "  __init__.py\n"
        "  test_main.py\n"
        "requirements.txt\n"
        "README.md\n"
        ".env.example"
    ),
    "React + Vite Frontend": (
        "src/\n"
        "  assets/\n"
        "  components/\n"
        "    ui/\n"
        "      Button.tsx\n"
        "      Card.tsx\n"
        "    Header.tsx\n"
        "  hooks/\n"
        "    useAuth.ts\n"
        "  pages/\n"
        "    Home.tsx\n"
        "    Dashboard.tsx\n"
        "  services/\n"
        "    api.ts\n"
        "  types/\n"
        "    index.ts\n"
        "  App.tsx\n"
        "  main.tsx\n"
        "  index.css\n"
        "public/\n"
        "package.json\n"
        "tsconfig.json\n"
        "README.md"
    ),
    "Python Production Package": (
        "src/\n"
        "  my_package/\n"
        "    __init__.py\n"
        "    core.py\n"
        "    utils.py\n"
        "tests/\n"
        "  __init__.py\n"
        "  test_core.py\n"
        "pyproject.toml\n"
        "README.md\n"
        "LICENSE"
    ),
    "Clean Architecture Monorepo": (
        "domain/\n"
        "  entities/\n"
        "  repositories/\n"
        "usecases/\n"
        "  auth/\n"
        "  users/\n"
        "infrastructure/\n"
        "  database/\n"
        "  http/\n"
        "presentation/\n"
        "  controllers/\n"
        "  presenters/\n"
        "config/\n"
        "README.md"
    ),
}


def create_nested_folder(base_path: str | Path, rel_path: str) -> tuple[Path, list[str]]:
    """Create a nested folder path under base_path (mkdir -p).

    Returns (target_folder_path, list_of_newly_created_parent_dirs_for_undo).
    """
    base = Path(base_path).resolve()
    clean_rel = rel_path.strip().lstrip("/\\")
    target = (base / clean_rel).resolve()

    # Identify intermediate directories that do not yet exist
    created_dirs: list[str] = []
    curr = target
    while curr != base and not curr.exists() and curr != curr.parent:
        created_dirs.append(str(curr))
        curr = curr.parent

    created_dirs.reverse()
    target.mkdir(parents=True, exist_ok=True)
    return target, created_dirs


def create_nested_file(
    base_path: str | Path,
    rel_path: str,
    content: str = "",
    encoding: str = "utf-8",
) -> tuple[Path, list[str]]:
    """Create a nested file path under base_path, automatically creating missing intermediate parent directories.

    Returns (target_file_path, list_of_newly_created_parent_dirs_for_undo).
    """
    base = Path(base_path).resolve()
    clean_rel = rel_path.strip().lstrip("/\\")
    target = (base / clean_rel).resolve()

    # Track non-existent parent directories
    created_dirs: list[str] = []
    curr = target.parent
    while curr != base and not curr.exists() and curr != curr.parent:
        created_dirs.append(str(curr))
        curr = curr.parent

    created_dirs.reverse()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding=encoding)
    return target, created_dirs


def scaffold_hierarchy(
    base_path: str | Path,
    spec_text: str,
    default_content: str = "",
) -> dict:
    """Parse a multi-line project scaffold specification and create folders & files.

    Supports:
      1. Indented tree format (spaces or tabs):
         app/
           api/
             v1/
               endpoints.py
           main.py
      2. Slash-separated path list:
         src/components/Button.tsx
         src/utils/math.ts
         docs/README.md

    Returns {
        "created_files": list of (path_str, content),
        "created_dirs": list of dir_path_str,
        "errors": list of err_str
    }
    """
    base = Path(base_path).resolve()
    created_files: list[tuple[str, str]] = []
    created_dirs: list[str] = []
    errors: list[str] = []

    lines = [line.rstrip() for line in spec_text.strip().splitlines() if line.strip()]
    if not lines:
        return {
            "created_files": created_files,
            "created_dirs": created_dirs,
            "errors": errors,
        }

    is_indented = any(line.startswith("  ") or line.startswith("\t") for line in lines)

    if is_indented:
        stack: list[tuple[int, Path]] = [(-1, base)]
        for raw_line in lines:
            indent = len(raw_line) - len(raw_line.lstrip())
            name = raw_line.strip()
            if not name or name.startswith("#"):
                continue

            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()

            parent_dir = stack[-1][1]
            is_dir = (
                name.endswith("/")
                or name.endswith("\\")
                or ("." not in name and not name.startswith("."))
            )
            clean_name = name.rstrip("/\\")
            target_path = parent_dir / clean_name

            try:
                if is_dir:
                    if not target_path.exists():
                        target_path.mkdir(parents=True, exist_ok=True)
                        created_dirs.append(str(target_path))
                    stack.append((indent, target_path))
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    ext = target_path.suffix.lower()
                    content = FILE_TEMPLATES.get(ext, {}).get("content", default_content)
                    target_path.write_text(content, encoding="utf-8")
                    created_files.append((str(target_path), content))
            except Exception as exc:
                errors.append(f"Failed to create {target_path}: {exc}")
    else:
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            clean_path = line.lstrip("/\\")
            target_path = (base / clean_path).resolve()
            is_dir = (
                line.endswith("/")
                or line.endswith("\\")
                or ("." not in target_path.name and not target_path.name.startswith("."))
            )
            try:
                if is_dir:
                    if not target_path.exists():
                        target_path.mkdir(parents=True, exist_ok=True)
                        created_dirs.append(str(target_path))
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    ext = target_path.suffix.lower()
                    content = FILE_TEMPLATES.get(ext, {}).get("content", default_content)
                    target_path.write_text(content, encoding="utf-8")
                    created_files.append((str(target_path), content))
            except Exception as exc:
                errors.append(f"Failed to create {target_path}: {exc}")

    return {
        "created_files": created_files,
        "created_dirs": created_dirs,
        "errors": errors,
    }

