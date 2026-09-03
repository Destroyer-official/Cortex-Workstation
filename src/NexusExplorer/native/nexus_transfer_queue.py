"""Transfer queue for serialized file operations.

FFI-first: jobs run through the in-process Rust engine (real pause/resume/
cancel via job handles, speed/ETA from engine events). Falls back to the
nexus-cli subprocess when the DLL is unavailable.

Public API (unchanged from the CLI era):
    enqueue(kind, sources, dest="", permanent=False, priority=0) -> job_id
    cancel / pause / resume / get_job / get_all_jobs / clear_finished
Signals:
    job_added(job_id) job_started(job_id)
    job_progress(job_id, percent, status_text)
    job_completed(job_id, success, message)
    job_cancelled(job_id) queue_empty()
"""

from __future__ import annotations

import bisect
import logging
import math
import os
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QRunnable, QThreadPool, QTimer, Signal

log = logging.getLogger("nexus.transfer")


class JobState(Enum):
    """Lifecycle states of a queued transfer job."""
    QUEUED = 0
    RUNNING = 1
    PAUSED = 2
    COMPLETED = 3
    FAILED = 4
    CANCELLED = 5
    """Lifecycle states of a queued transfer job."""


@dataclass
class TransferJob:
    """State record for one queued copy/move/delete job (progress, priority,
    and the active FFI handle or CLI QProcess driving it)."""
    job_id: str = ""
    kind: str = ""  # "copy", "move", "delete"
    sources: list[str] = field(default_factory=list)
    dest: str = ""
    permanent: bool = False
    state: JobState = JobState.QUEUED
    progress: int = 0
    total_files: int = 0
    processed_files: int = 0
    speed_bps: float = 0.0
    eta_secs: float = 0.0
    current_file: str = ""
    error: str = ""
    error_full: str = ""
    priority: int = 0  # higher = runs first
    handle: int | None = None      # FFI job handle when running
    proc: QProcess | None = None   # CLI fallback process
    """State record for one queued copy/move/delete job (progress, priority,
    and the active FFI handle or CLI QProcess driving it)."""


def human_bytes(n: float) -> str:
    """Format a byte count as a human-readable string ('1.2 MB', '847 B'),
    '' for negatives and PB overflow."""
    n = float(n)
    if n < 0:
        return ""
    if n == 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            if unit == "B":
                return f"{n:.0f} B"
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
    """Format a byte count as a human-readable string ('1.2 MB', '847 B'),
    '' for negatives and PB overflow."""


def fmt_eta(secs: float) -> str:
    """Format seconds as a compact ETA ('2h05m', '3m12s', '45s'); '' for
    non-positive or NaN inputs."""
    if secs <= 0 or math.isnan(secs):
        return ""
    secs = int(secs)
    if secs >= 3600:
        return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"
    if secs >= 60:
        return f"{secs // 60}m{secs % 60:02d}s"
    return f"{secs}s"
    """Format seconds as a compact ETA ('2h05m', '3m12s', '45s'); '' for
    non-positive or NaN inputs."""


class TransferQueue(QObject):
    """Manages queued file transfers with progress and control."""

    job_added = Signal(str)       # job_id
    job_started = Signal(str)     # job_id
    job_progress = Signal(str, int, str)  # job_id, percent, status_text
    job_completed = Signal(str, bool, str)  # job_id, success, message
    job_cancelled = Signal(str)   # job_id
    queue_empty = Signal()

    def __init__(self, engine, parent=None, max_concurrent: int = 1):
        """Store the engine (FFI handle + CLI path), the job/order/active
        maps guarded by an RLock, and start the 500 ms progress re-emit
        QTimer that keeps running jobs visible."""
        super().__init__(parent)
        self._engine = engine
        self._cli = getattr(engine, "cli", "")
        self._max_concurrent = max_concurrent
        self._jobs: dict[str, TransferJob] = {}
        self._order: list[str] = []
        self._active: list[str] = []
        self._lock = threading.RLock()
        self._id_counter = 0
        self._pending_count = 0

        self._poll = QTimer(self)
        self._poll.setInterval(500)
        self._poll.timeout.connect(self._refresh_running)
        self._poll.start()
        """Store the engine (FFI handle + CLI path), the job/order/active
        maps guarded by an RLock, and start the 500 ms progress re-emit
        QTimer that keeps running jobs visible."""

    @property
    def max_concurrent(self) -> int:
        """Return the configured maximum number of concurrently running jobs."""
        return self._max_concurrent
        """Return the configured maximum number of concurrently running jobs."""

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        """Clamp the concurrency limit to at least 1 and immediately try to
        start queued jobs freed up by the new limit."""
        self._max_concurrent = max(1, value)
        self._try_start_next()
        """Clamp the concurrency limit to at least 1 and immediately try to
        start queued jobs freed up by the new limit."""

    @property
    def is_busy(self) -> bool:
        """True if there are active transfer jobs running."""
        return bool(self._active)

    # ------------------------------------------------------------------ API
    def stop(self) -> None:
        """Stop the polling timer. Call during shutdown to avoid dangling timers."""
        self._poll.stop()

    def enqueue(
        self,
        kind: str,
        sources: list[str],
        dest: str = "",
        permanent: bool = False,
        priority: int = 0,
        parent_widget=None,
    ) -> str:
        """Register a new job ('copy'/'move'/'delete') with a fresh job_N id,
        insert it into priority order (bisect on descending priority), emit
        job_added, and kick the scheduler; returns the job id."""
        with self._lock:
            self._id_counter += 1
            job_id = f"job_{self._id_counter}"
            job = TransferJob(
                job_id=job_id,
                kind=kind,
                sources=sources,
                dest=dest,
                permanent=permanent,
                priority=priority,
            )
            self._jobs[job_id] = job
            bisect.insort(self._order, job_id,
                          key=lambda jid: -self._jobs[jid].priority)
            self._pending_count += 1
        self.job_added.emit(job_id)
        self._try_start_next()
        return job_id
        """Register a new job ('copy'/'move'/'delete') with a fresh job_N id,
        insert it into priority order (bisect on descending priority), emit
        job_added, and kick the scheduler; returns the job id."""

    def cancel(self, job_id: str) -> bool:
        """Cancel a queued or running job. Running jobs are cancelled via
        ffi.cancel_job or by killing the CLI QProcess. Emits job_cancelled,
        schedules the next job, and emits queue_empty when drained."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.state is JobState.QUEUED:
                job.state = JobState.CANCELLED
                self._order.remove(job_id)
                self._pending_count = max(0, self._pending_count - 1)
            elif job.state in (JobState.RUNNING, JobState.PAUSED):
                job.state = JobState.CANCELLED
                if job.handle is not None:
                    try:
                        self._engine.ffi.cancel_job(job.handle)
                    except Exception as exc:
                        log.warning("cancel_job FFI failed: %s", exc)
                elif job.proc and job.proc.state() == QProcess.ProcessState.Running:
                    job.proc.kill()
                if job.job_id in self._active:
                    self._active.remove(job_id)
                self._pending_count = max(0, self._pending_count - 1)
            else:
                return False
        self.job_cancelled.emit(job_id)
        self._try_start_next()
        self._maybe_queue_empty()
        return True
        """Cancel a queued or running job. Running jobs are cancelled via
        ffi.cancel_job or by killing the CLI QProcess. Emits job_cancelled,
        schedules the next job, and emits queue_empty when drained."""

    def pause(self, job_id: str) -> bool:
        """Pause a RUNNING job via ffi.pause_job (state flips to PAUSED;
        only True when the job exists and was running)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.state == JobState.RUNNING:
                job.state = JobState.PAUSED
                if job.handle:
                    try:
                        self._engine.ffi.pause_job(job.handle)
                    except Exception:
                        log.exception("pause_job failed")
                return True
        return False
        """Pause a RUNNING job via ffi.pause_job (state flips to PAUSED;
        only True when the job exists and was running)."""

    def resume(self, job_id: str) -> bool:
        """Resume a PAUSED job via ffi.resume_job and re-emit its last
        progress as '<kind>: resumed N%'."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.state == JobState.PAUSED:
                job.state = JobState.RUNNING
                if job.handle:
                    try:
                        self._engine.ffi.resume_job(job.handle)
                    except Exception:
                        log.exception("resume_job failed")
                progress = job.progress
                kind = job.kind
                jid = job.job_id
            else:
                return False
        self.job_progress.emit(
            jid, progress,
            f"{kind}: resumed {progress}%",
        )
        return True
        """Resume a PAUSED job via ffi.resume_job and re-emit its last
        progress as '<kind>: resumed N%'."""

    def get_job(self, job_id: str) -> TransferJob | None:
        """Return the TransferJob for job_id, or None if unknown."""
        return self._jobs.get(job_id)
        """Return the TransferJob for job_id, or None if unknown."""

    def get_all_jobs(self) -> list[TransferJob]:
        """Return all known jobs in priority (_order) sequence."""
        return [self._jobs[jid] for jid in self._order if jid in self._jobs]
        """Return all known jobs in priority (_order) sequence."""

    def clear_finished(self) -> int:
        """Drop COMPLETED/FAILED/CANCELLED jobs (cancelling stray FFI handles
        and killing/disposing leftover CLI processes); returns how many were
        removed."""
        with self._lock:
            finished = [
                jid for jid, j in self._jobs.items()
                if j.state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED)
            ]
            for jid in finished:
                job = self._jobs[jid]
                if job.handle:
                    try:
                        self._engine.ffi.cancel_job(job.handle)
                    except Exception as exc:
                        log.warning("clear_finished cancel_job failed: %s", exc)
                    job.handle = None
                if job.proc:
                    if job.proc.state() == QProcess.ProcessState.Running:
                        job.proc.kill()
                    job.proc.waitForFinished(1000)
                    job.proc.deleteLater()
                    job.proc = None
                del self._jobs[jid]
                if jid in self._order:
                    self._order.remove(jid)
        return len(finished)
        """Drop COMPLETED/FAILED/CANCELLED jobs (cancelling stray FFI handles
        and killing/disposing leftover CLI processes); returns how many were
        removed."""

    # --------------------------------------------------------------- engine
    def _try_start_next(self):
        """Scheduler: while below the concurrency limit, move the highest
        priority QUEUED job to RUNNING, mark it active, launch it, and emit
        job_started (one per call)."""
        with self._lock:
            if len(self._active) >= self._max_concurrent:
                return
            for jid in self._order:
                job = self._jobs.get(jid)
                if job and job.state == JobState.QUEUED:
                    job.state = JobState.RUNNING
                    self._active.append(jid)
                    self._start_job(job)
                    self.job_started.emit(jid)
                    break
        """Scheduler: while below the concurrency limit, move the highest
        priority QUEUED job to RUNNING, mark it active, launch it, and emit
        job_started (one per call)."""

    def _start_job(self, job: TransferJob):
        """Dispatch the job to the best backend: FFI engine when available,
        otherwise the CLI subprocess, otherwise the pure-Python runner."""
        if getattr(self._engine, "ffi", None) is not None:
            self._start_job_ffi(job)
        elif self._cli and os.path.exists(self._cli):
            self._start_job_cli(job)
        else:
            self._start_job_python(job)
        """Dispatch the job to the best backend: FFI engine when available,
        otherwise the CLI subprocess, otherwise the pure-Python runner."""

    def _start_job_ffi(self, job: TransferJob):
        """Launch the job on the Rust engine via a QThreadPool worker:
        wires progress/conflict/started hooks into the TransferJob record,
        chooses ffi.delete_paths or ffi.copy/move by kind, and finishes
        through _finish on the pool thread."""
        ffi = self._engine.ffi
        control: dict = {}

        def on_progress(done_b: int, total_b: int, speed: float = 0.0,
                        eta: float = 0.0, cur: str = "") -> None:
            """Engine progress hook: update job percent/speed/ETA/current
            file and re-emit job_progress on the GUI thread via a
            QTimer.singleShot(0, ...) hop."""
            if job.state is JobState.CANCELLED:
                return
            job.current_file = cur or ""
            if total_b > 0:
                job.progress = min(100, int(done_b * 100 / total_b))
            job.speed_bps = speed
            job.eta_secs = eta
            status = (
                f"{job.kind}: {human_bytes(done_b)} / {human_bytes(total_b)}"
                f"  ·  {human_bytes(speed)}/s"
                + (f"  ·  ETA {fmt_eta(eta)}" if eta else "")
            )
            QTimer.singleShot(0, lambda j=job, p=job.progress, s=status:
                              self.job_progress.emit(j.job_id, p, s))
            """Engine progress hook: update job percent/speed/ETA/current
            file and re-emit job_progress on the GUI thread via a
            QTimer.singleShot(0, ...) hop."""

        def on_started(handle: int) -> None:
            """Record the engine job handle for pause/resume/cancel."""
            job.handle = handle
            """Record the engine job handle for pause/resume/cancel."""

        def _conflict_hook(info):
            """Default conflict: ask user or skip."""
            return 1  # overwrite for now; dialog pending

        hooks = {"progress": on_progress, "started": on_started,
                 "conflict": _conflict_hook}

        def job_fn():
            """Backend selector: run ffi.delete_paths for 'delete',
            ffi.copy/ffi.move for transfers; unknown kinds yield an error
            result dict."""
            if job.kind == "delete":
                r = ffi.delete_paths(job.sources, to_trash=not job.permanent,
                                     control=control, hooks=hooks)
            elif job.kind in ("copy", "move"):
                fn = ffi.copy if job.kind == "copy" else ffi.move
                r = fn(job.sources, job.dest, control=control, hooks=hooks)
            else:
                r = {"ok": False, "error": f"unknown kind {job.kind!r}"}
            return r
            """Backend selector: run ffi.delete_paths for 'delete',
            ffi.copy/ffi.move for transfers; unknown kinds yield an error
            result dict."""

        class _Job(QRunnable):
            """Pool worker that executes job_fn and reports the result
            through _finish (exceptions become a failure result)."""
            def run(self_inner):
                """Run the FFI job, log exceptions, and finish the
                TransferJob with the ok/error outcome."""
                try:
                    r = job_fn()
                except Exception as exc:
                    log.exception("queue job failed")
                    r = {"ok": False, "error": str(exc)}
                self._finish(job, bool(r.get("ok")), r.get("error", ""))
                """Run the FFI job, log exceptions, and finish the
                TransferJob with the ok/error outcome."""
            """Pool worker that executes job_fn and reports the result
            through _finish (exceptions become a failure result)."""

        QThreadPool.globalInstance().start(_Job())
        """Launch the job on the Rust engine via a QThreadPool worker:
        wires progress/conflict/started hooks into the TransferJob record,
        chooses ffi.delete_paths or ffi.copy/move by kind, and finishes
        through _finish on the pool thread."""

    def _start_job_python(self, job: TransferJob):
        """Pure-Python asynchronous transfer runner with live progress and cancel support."""
        def _get_copy_target(target_path: Path) -> Path:
            """Return target_path, or a non-colliding 'name - Copy [ (N)]'
            sibling when a copy destination would overwrite itself."""
            if not target_path.exists():
                return target_path
            parent = target_path.parent
            stem = target_path.stem
            ext = target_path.suffix
            candidate = parent / f"{stem} - Copy{ext}"
            counter = 1
            while candidate.exists():
                counter += 1
                candidate = parent / f"{stem} - Copy ({counter}){ext}"
            return candidate
            """Return target_path, or a non-colliding 'name - Copy [ (N)]'
            sibling when a copy destination would overwrite itself."""

        def run_transfer():
            """Plan all (src, dst, size, is_dir) pairs — walking directory
            trees, enforcing the circular-copy check, choosing copy-target
            names — then execute with 256 KB chunks, pause/cancel polling,
            10 Hz throttled progress, and Windows lock-aware error tagging;
            finally finish via _finish with a success/skip summary."""
            t_start = time.time()
            bytes_done = 0
            file_pairs = []  # list of (src, dst, size, is_dir)
            total_bytes = 0
            successful_files = 0
            failed_files: list[tuple[str, str]] = []  # (path, error_reason)

            dest_dir = Path(job.dest) if job.dest else Path()
            if job.kind in ("copy", "move"):
                dest_dir.mkdir(parents=True, exist_ok=True)
                for src in job.sources:
                    src_p = Path(src)
                    if not src_p.exists():
                        continue
                    if src_p.is_dir():
                        # Circular move/copy check
                        try:
                            if dest_dir.resolve() == src_p.resolve() or dest_dir.resolve().is_relative_to(src_p.resolve()):
                                log.warning("Cannot %s directory '%s' into a subfolder of itself", job.kind, src_p)
                                failed_files.append((str(src_p), "Cannot copy/move folder into a subfolder of itself"))
                                continue
                        except Exception:
                            pass

                        dest_root_folder = dest_dir / src_p.name
                        if job.kind == "copy" and dest_root_folder.resolve() == src_p.resolve():
                            dest_root_folder = _get_copy_target(dest_root_folder)

                        file_pairs.append((str(src_p), str(dest_root_folder), 0, True))
                        for root, dirs, files in os.walk(src_p):
                            root_p = Path(root)
                            rel = root_p.relative_to(src_p)
                            for d in dirs:
                                sub_src = root_p / d
                                sub_dst = dest_root_folder / rel / d
                                file_pairs.append((str(sub_src), str(sub_dst), 0, True))
                            for f in files:
                                f_path = root_p / f
                                target_f = dest_root_folder / rel / f
                                try:
                                    sz = f_path.stat().st_size
                                except Exception:
                                    sz = 0
                                file_pairs.append((str(f_path), str(target_f), sz, False))
                                total_bytes += sz
                    else:
                        target_f = dest_dir / src_p.name
                        if job.kind == "copy" and target_f.resolve() == src_p.resolve():
                            target_f = _get_copy_target(target_f)
                        try:
                            sz = src_p.stat().st_size
                        except Exception:
                            sz = 0
                        file_pairs.append((str(src_p), str(target_f), sz, False))
                        total_bytes += sz
            elif job.kind == "delete":
                for src in job.sources:
                    src_p = Path(src)
                    if src_p.exists():
                        try:
                            sz = src_p.stat().st_size if src_p.is_file() else 0
                        except Exception:
                            sz = 0
                        file_pairs.append((str(src_p), "", sz, src_p.is_dir()))
                        total_bytes += sz

            job.total_files = len(file_pairs)
            job.processed_files = 0
            chunk_size = 1024 * 256  # 256 KB
            last_update = time.time()
            last_bytes = 0
            t_start = time.time()

            for src_str, dst_str, sz, is_dir in file_pairs:
                if job.state == JobState.CANCELLED:
                    return

                while job.state == JobState.PAUSED:
                    time.sleep(0.1)
                    if job.state == JobState.CANCELLED:
                        return

                job.current_file = Path(src_str).name
                if job.kind == "delete":
                    try:
                        import stat
                        import ctypes

                        deleted = False
                        if not job.permanent:
                            try:
                                import send2trash
                                send2trash.send2trash(src_str)
                                deleted = True
                            except Exception:
                                deleted = False

                        if not deleted:
                            if is_dir:
                                def _onerror(func, path, exc_info):
                                    """rmtree error handler: clear the
                                    read-only/system file attributes and
                                    retry the failing operation once."""
                                    try:
                                        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                                        try:
                                            ctypes.windll.kernel32.SetFileAttributesW(path, 128)
                                        except Exception:
                                            pass
                                        func(path)
                                    except Exception:
                                        pass
                                    """rmtree error handler: clear the
                                    read-only/system file attributes and
                                    retry the failing operation once."""
                                shutil.rmtree(src_str, onerror=_onerror)
                                if os.path.exists(src_str):
                                    time.sleep(0.1)
                                    shutil.rmtree(src_str, ignore_errors=True)
                            else:
                                for attempt in range(5):
                                    try:
                                        os.chmod(src_str, stat.S_IWRITE | stat.S_IREAD)
                                        try:
                                            ctypes.windll.kernel32.SetFileAttributesW(src_str, 128)
                                        except Exception:
                                            pass
                                        os.remove(src_str)
                                        break
                                    except Exception:
                                        try:
                                            if ctypes.windll.kernel32.DeleteFileW(src_str):
                                                break
                                        except Exception:
                                            pass
                                        if attempt < 4:
                                            time.sleep(0.08)
                                        else:
                                            raise
                    except Exception as e:
                        log.warning(f"Delete failed for {src_str}: {e}")
                        failed_files.append((src_str, str(e)))
                    bytes_done += sz
                    continue
                elif job.kind in ("copy", "move"):
                    if is_dir:
                        try:
                            os.makedirs(dst_str, exist_ok=True)
                            successful_files += 1
                        except Exception as exc:
                            log.warning("Could not create directory '%s': %s", dst_str, exc)
                            failed_files.append((dst_str, str(exc)))
                        continue

                    try:
                        # Copy file with chunked progress
                        os.makedirs(os.path.dirname(dst_str), exist_ok=True)
                        with open(src_str, "rb") as fsrc, open(dst_str, "wb") as fdst:
                            try:
                                while True:
                                    if job.state == JobState.CANCELLED:
                                        break
                                    while job.state == JobState.PAUSED:
                                        time.sleep(0.1)
                                        if job.state == JobState.CANCELLED:
                                            break

                                    if job.state == JobState.CANCELLED:
                                        break

                                    chunk = fsrc.read(chunk_size)
                                    if not chunk:
                                        break
                                    fdst.write(chunk)
                                    bytes_done += len(chunk)

                                    now = time.time()
                                    dt = now - last_update
                                    if dt >= 0.1:  # 10Hz throttle
                                        speed = (bytes_done - last_bytes) / dt
                                        last_bytes = bytes_done
                                        last_update = now

                                        if total_bytes > 0:
                                            job.progress = min(99, int(bytes_done * 100 / total_bytes))
                                            rem_bytes = max(0, total_bytes - bytes_done)
                                            job.eta_secs = rem_bytes / speed if speed > 0 else 0
                                        else:
                                            job.progress = 50
                                        status = (
                                            f"{job.kind}: {human_bytes(bytes_done)} / {human_bytes(total_bytes)}"
                                            f" · {human_bytes(speed)}/s"
                                            f" · ETA {fmt_eta(job.eta_secs)}"
                                        )
                                        self.job_progress.emit(job.job_id, job.progress, status)
                            finally:
                                fdst.flush()

                        if job.state == JobState.CANCELLED:
                            # Clean up partial destination file on cancel
                            try:
                                if os.path.exists(dst_str):
                                    import stat, ctypes
                                    os.chmod(dst_str, stat.S_IWRITE | stat.S_IREAD)
                                    try:
                                        ctypes.windll.kernel32.SetFileAttributesW(dst_str, 128)
                                    except Exception:
                                        pass
                                    os.remove(dst_str)
                            except Exception:
                                pass
                            return

                        # Preserve metadata
                        try:
                            shutil.copystat(src_str, dst_str)
                        except Exception:
                            pass

                        # Delete source if moving
                        if job.kind == "move":
                            try:
                                import stat
                                os.chmod(src_str, stat.S_IWRITE | stat.S_IREAD)
                                try:
                                    ctypes.windll.kernel32.SetFileAttributesW(src_str, 128)
                                except Exception:
                                    pass
                                os.remove(src_str)
                            except Exception as exc:
                                try:
                                    if not ctypes.windll.kernel32.DeleteFileW(src_str):
                                        log.warning("Could not remove source file '%s' after move: %s", src_str, exc)
                                except Exception:
                                    pass

                        successful_files += 1

                    except (PermissionError, OSError) as exc:
                        log.warning("Skipped locked or inaccessible file '%s': %s", src_str, exc)
                        failed_files.append((src_str, str(exc)))
                        try:
                            if os.path.exists(dst_str) and os.path.getsize(dst_str) == 0:
                                os.remove(dst_str)
                        except Exception:
                            pass
                        file_name = Path(src_str).name
                        err_tag = "In use by Windows" if "Permission denied" in str(exc) or "used by another process" in str(exc) else "Access denied"
                        status = f"{job.kind}: Skipped '{file_name}' ({err_tag})"
                        self.job_progress.emit(job.job_id, job.progress, status)

                job.processed_files += 1

            if job.kind == "move":
                for src in job.sources:
                    if os.path.isdir(src):
                        try:
                            shutil.rmtree(src, ignore_errors=True)
                        except Exception:
                            pass

            if failed_files and successful_files == 0:
                first_name = Path(failed_files[0][0]).name
                first_err = failed_files[0][1]
                if "Permission denied" in first_err or "used by another process" in first_err:
                    summary = f"Cannot {job.kind} '{first_name}': Locked by Windows (in use by OS/process)."
                else:
                    summary = f"Cannot {job.kind} '{first_name}': {first_err}"
                self._finish(job, False, summary)
            elif failed_files and successful_files > 0:
                skipped_names = ", ".join(Path(f[0]).name for f in failed_files[:3])
                if len(failed_files) > 3:
                    skipped_names += f" and {len(failed_files) - 3} more"
                summary = f"Completed ({successful_files} items). Skipped locked: {skipped_names}."
                self._finish(job, True, summary)
            else:
                self._finish(job, True, "")
            """Plan all (src, dst, size, is_dir) pairs — walking directory
            trees, enforcing the circular-copy check, choosing copy-target
            names — then execute with 256 KB chunks, pause/cancel polling,
            10 Hz throttled progress, and Windows lock-aware error tagging;
            finally finish via _finish with a success/skip summary."""

        class _PyJob(QRunnable):
            """Pool worker wrapper: names its thread after the job and
            funnels any exception into a failed _finish."""
            def run(self_inner):
                """Run run_transfer on a pool thread under a job-specific
                thread name; exceptions report failure via _finish."""
                import threading
                threading.current_thread().name = f"NexusTransfer-{job.job_id}"
                try:
                    run_transfer()
                except Exception as exc:
                    log.exception("Python transfer job failed: %s", exc)
                    self._finish(job, False, str(exc))
                """Run run_transfer on a pool thread under a job-specific
                thread name; exceptions report failure via _finish."""
            """Pool worker wrapper: names its thread after the job and
            funnels any exception into a failed _finish."""

        log.info("Starting transfer (python): %s %s (%d items)", job.kind, job.job_id, len(job.sources))
        QThreadPool.globalInstance().start(_PyJob())

    def _finish(self, job: TransferJob, success: bool, error: str):
        """Mark a job COMPLETED/FAILED (skipping already-cancelled ones),
        cap the short error at 500 chars while keeping the full text, drop
        it from the active list, decrement pending, and emit completion."""
        with self._lock:
            if job.state is JobState.CANCELLED:
                return
            job.state = JobState.COMPLETED if success else JobState.FAILED
            job.progress = 100 if success else job.progress
            job.error = (error or "")[:500]
            job.error_full = error or ""
            if job.job_id in self._active:
                self._active.remove(job.job_id)
            self._pending_count = max(0, self._pending_count - 1)
        self._finish_emit(job, success)
        """Mark a job COMPLETED/FAILED (skipping already-cancelled ones),
        cap the short error at 500 chars while keeping the full text, drop
        it from the active list, decrement pending, and emit completion."""

    def _finish_emit(self, job: TransferJob, success: bool):
        """Emit job_completed, then schedule the next queued job and emit
        queue_empty when nothing remains pending."""
        self.job_completed.emit(job.job_id, success, job.error)
        self._try_start_next()
        self._maybe_queue_empty()
        """Emit job_completed, then schedule the next queued job and emit
        queue_empty when nothing remains pending."""

    def _maybe_queue_empty(self):
        """Emit queue_empty when the pending count has dropped to zero."""
        with self._lock:
            pending = self._pending_count > 0
        if not pending:
            self.queue_empty.emit()
        """Emit queue_empty when the pending count has dropped to zero."""

    def _refresh_running(self):
        """Periodic re-emit so monitor speed/ETA/current-file stay live."""
        with self._lock:
            running = [self._jobs[jid] for jid in self._active]
        for job in running:
            if job.state is JobState.RUNNING:
                self.job_progress.emit(
                    job.job_id, job.progress,
                    f"{job.kind}: {job.current_file or ''} {job.progress}%",
                )

    # ---------------------------------------------------------- CLI fallback
    def _start_job_cli(self, job: TransferJob):
        """Run the job as a nexus-cli QProcess ('copy/move srcs --to dest'
        or 'delete [--permanent] paths'); parse stderr progress bars and
        file counts into job_progress, and finish on process exit."""
        proc = QProcess()
        job.proc = proc

        def on_ready():
            """Parse stderr chunks for '[#+-+] N%' progress and 'N files
            (…) ->' counts, re-emitting job_progress with the current file
            and percent."""
            data = bytes(proc.readAllStandardError()).decode("utf-8", "replace")
            for chunk in data.split("\r"):
                m = re.search(r"\[(#*-*)\]\s+(\d+)%", chunk)
                if m:
                    job.progress = int(m.group(2))
                fm = re.search(r"(\d+) files? \(([^)]+)\) ->", chunk)
                if fm:
                    job.current_file = fm.group(1)
                if not m and not fm and chunk.strip():
                    log.debug("CLI progress (unparsed): %s", chunk.strip())
                self.job_progress.emit(
                    job.job_id,
                    job.progress,
                    f"{job.kind}: {job.current_file or ''} {job.progress}%",
                )
            """Parse stderr chunks for '[#+-+] N%' progress and 'N files
            (…) ->' counts, re-emitting job_progress with the current file
            and percent."""

        def on_finished(code, _s):
            """CLI exit handler: skip when already cancelled; success
            requires exit code 0 and 'completed' in stdout."""
            out = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
            if job.state == JobState.CANCELLED:
                return
            success = code == 0 and "completed" in out
            self._finish(job, success, out.strip() if not success else "")
            """CLI exit handler: skip when already cancelled; success
            requires exit code 0 and 'completed' in stdout."""

        proc.readyReadStandardError.connect(on_ready)
        proc.finished.connect(on_finished)

        if job.kind == "delete":
            args = ["delete"] + (["--permanent"] if job.permanent else []) + job.sources
        else:
            args = [job.kind, *job.sources, "--to", job.dest]

        log.info("Starting transfer (cli): %s %s", job.kind, job.job_id)
        proc.start(self._cli, args)
        """Run the job as a nexus-cli QProcess ('copy/move srcs --to dest'
        or 'delete [--permanent] paths'); parse stderr progress bars and
        file counts into job_progress, and finish on process exit."""
