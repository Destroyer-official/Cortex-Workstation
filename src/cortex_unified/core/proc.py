"""Cancellable, tree-safe subprocess execution.

Why this exists
---------------
Every external tool Cortex drives (SFC, DISM, winget, diskpart, PowerShell...)
is launched with plain ``subprocess.run()`` and a timeout. That leaves two real
problems once the app has to shut down while one of those calls is still
blocked inside ``communicate()``:

1. **The Python-level "cancel"** a worker exposes cannot do anything: it can
   only set a ``threading.Event``, and nothing is polling it while the thread
   is stuck inside a blocking C call.
2. The previous fallback - ``QThread.terminate()`` (Windows'
   ``TerminateThread``) - is unsafe *by design*. If the thread is forcibly
   killed while it holds a CRT/heap lock (which pipe I/O routinely does), that
   lock is never released, and any other thread that later needs it hangs
   forever. That is a corrupted-process bug, not a slow test: it explains
   unrelated, seemingly-random hangs appearing later in the same run.

:func:`run` fixes both: it polls a ``timeout`` *and* an optional
``cancel_event`` by repeatedly calling ``Popen.communicate(timeout=...)`` -
the officially documented pattern for polling a subprocess without losing
output (see the stdlib docs for ``Popen.communicate``: calling it again after
a ``TimeoutExpired`` is safe and keeps the same reader threads). On a real
timeout or cancellation it kills the **whole process tree** (a PowerShell
wrapper spawning dism.exe, for example) via ``taskkill /T /F`` on Windows or a
process-group signal on POSIX, then reaps the process - never the calling
Python thread.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time

_LOG = logging.getLogger("cortex.core.proc")
# ``sys.platform`` is an interned constant; ``platform.system()`` costs ~49 ms
# on its first call (it populates ``uname()`` via WMI on Windows). This module
# is imported by nearly every system tool, so it must stay import-cheap.
_IS_WINDOWS = sys.platform == "win32"
NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0
_CREATE_NEW_PROCESS_GROUP = 0x00000200 if _IS_WINDOWS else 0

#: How often the poll loop re-checks the deadline and cancel event. Short
#: enough that a cancelled operation feels immediate, long enough to be free.
_POLL_INTERVAL_S = 0.2

#: Grace period to collect output after killing the tree, before giving up.
_REAP_TIMEOUT_S = 5.0

#: Processes never eligible for termination or suspension under any circumstances.
PROTECTED_SYSTEM_PROCESSES: frozenset[str] = frozenset({
    "system", "system idle process", "registry", "memory compression", "idle",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "svchost.exe", "dwm.exe", "winmgmt.exe", "audiodg.exe",
    "explorer.exe", "sihost.exe", "taskhostw.exe", "runtimebroker.exe",
    "fontdrvhost.exe", "conhost.exe", "ctfmon.exe", "shellexperiencehost.exe",
    "searchapp.exe", "startmenuexperiencehost.exe",
    "python.exe", "pythonw.exe", "python3.exe", "cortex.exe",
})


def is_protected_process(name_or_pid: str | int) -> bool:
    """Check whether a process name or PID is an OS-critical protected process.

    Prevents accidental termination of critical Windows services, desktop shell
    (explorer.exe), or compositor (dwm.exe).

    Args:
        name_or_pid: Process name string (e.g. 'explorer.exe') or integer PID.

    Returns:
        bool: True if protected, False otherwise.
    """
    if isinstance(name_or_pid, int):
        if name_or_pid in (0, 4):
            return True
        try:
            import psutil
            p = psutil.Process(name_or_pid)
            n = (p.name() or "").lower()
            return n in PROTECTED_SYSTEM_PROCESSES or n.rstrip(".exe") in PROTECTED_SYSTEM_PROCESSES
        except Exception:
            return False
    name_clean = str(name_or_pid).strip().lower()
    name_clean_exe = name_clean if name_clean.endswith(".exe") else f"{name_clean}.exe"
    return name_clean in PROTECTED_SYSTEM_PROCESSES or name_clean_exe in PROTECTED_SYSTEM_PROCESSES


class ProcessCancelled(subprocess.SubprocessError):
    """Raised when ``cancel_event`` fired before the process finished.

    Subclasses ``SubprocessError`` so existing ``except (OSError,
    subprocess.SubprocessError)`` call sites keep working without changes.
    """

    def __init__(self, args):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            args: The args parameter.
        """
        super().__init__(f"process cancelled: {args!r}")
        self.args_ = args


def run(
    args: list[str],
    *,
    timeout: float | None = None,
    cancel_event: "threading.Event | None" = None,
    text: bool = False,
    encoding: str | None = None,
    errors: str | None = None,
    input: str | bytes | None = None,  # noqa: A002 - matches subprocess.run's name
    creationflags: int = 0,
    cwd: str | None = None,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Drop-in replacement for ``subprocess.run`` that never leaves an orphan.

    Behaves like ``subprocess.run(args, capture_output=True, timeout=timeout)``
    on success. On a real timeout it raises ``subprocess.TimeoutExpired`` (same
    as the stdlib). On cancellation it raises :class:`ProcessCancelled`. In both
    cases the *entire process tree* rooted at the spawned process is killed
    before the exception propagates - callers never need their own cleanup, and
    the calling thread is never touched, so it is always safe to abandon (e.g.
    a QThread whose owner is closing) without corrupting the process.
    """
    popen_flags = creationflags
    if _IS_WINDOWS:
        # Lets us signal/kill the group as a unit instead of only the direct
        # child (a "powershell -Command dism ..." wrapper, for instance).
        popen_flags |= _CREATE_NEW_PROCESS_GROUP
    kwargs: dict = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=popen_flags,
        cwd=cwd,
        env=env,
    )
    if input is not None:
        kwargs["stdin"] = subprocess.PIPE
    if text or encoding or errors:
        kwargs["text"] = True
        if encoding:
            kwargs["encoding"] = encoding
        if errors:
            kwargs["errors"] = errors
    if not _IS_WINDOWS:
        # POSIX equivalent of a process group so os.killpg can reach children.
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(args, **kwargs)
    deadline = None if timeout is None else time.monotonic() + timeout

    try:
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            slice_timeout = _POLL_INTERVAL_S if remaining is None else min(_POLL_INTERVAL_S, remaining)
            try:
                stdout, stderr = proc.communicate(input=input, timeout=slice_timeout)
                return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                input = None  # already delivered on the first iteration
                if cancel_event is not None and cancel_event.is_set():
                    _kill_tree(proc)
                    _reap_quietly(proc)
                    raise ProcessCancelled(args) from None
                if deadline is not None and time.monotonic() >= deadline:
                    _kill_tree(proc)
                    _reap_quietly(proc)
                    raise subprocess.TimeoutExpired(args, timeout) from None
                continue
    except (ProcessCancelled, subprocess.TimeoutExpired):
        raise
    except BaseException:
        # Any other failure (including KeyboardInterrupt) must still not leak
        # a running child - kill the tree, then let the original error surface.
        _kill_tree(proc)
        _reap_quietly(proc)
        raise


def _kill_tree(proc: subprocess.Popen) -> None:
    """Best-effort kill of *proc* and every descendant it spawned.

    Manages kill tree operations and coordinates related state changes for the component.

    Args:
        proc (subprocess.Popen): The proc parameter.
    """
    if proc.poll() is not None:
        return  # already exited
    if _IS_WINDOWS:
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=10, creationflags=NO_WINDOW,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("taskkill failed for pid %s: %s", proc.pid, exc)
        # Belt-and-suspenders: taskkill can itself fail (e.g. race where the
        # process just exited); proc.kill() is a no-op if it's already gone.
        try:
            proc.kill()
        except OSError:
            pass
    else:
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError) as exc:
            _LOG.debug("killpg failed for pid %s: %s", proc.pid, exc)
            try:
                proc.kill()
            except OSError:
                pass


def _reap_quietly(proc: subprocess.Popen) -> None:
    """Collect the exit status after a kill so no zombie/handle is left.

    Failure here must never raise: the caller is already unwinding to report
    a timeout or cancellation, and reaping is best-effort cleanup.
    """
    try:
        proc.communicate(timeout=_REAP_TIMEOUT_S)
    except Exception:  # noqa: BLE001 - cleanup must not mask the real error
        try:
            proc.wait(timeout=_REAP_TIMEOUT_S)
        except Exception:  # noqa: BLE001
            pass


def kill_process_tree(pid: int) -> bool:
    """Kill an entire process tree rooted at `pid` using taskkill /T /F on Windows or SIGKILL on POSIX.

    Refuses to kill OS-critical protected processes like explorer.exe, dwm.exe, system.

    Args:
        pid (int): The pid parameter.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    if is_protected_process(pid):
        _LOG.warning("kill_process_tree refused for protected process PID %s", pid)
        return False

    if _IS_WINDOWS:
        try:
            res = subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=10, creationflags=NO_WINDOW,
            )
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError) as exc:
            _LOG.debug("taskkill failed for pid %s: %s", pid, exc)
            return False
    else:
        import signal
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
            return True
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGKILL)
                return True
            except OSError:
                return False
