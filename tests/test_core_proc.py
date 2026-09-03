"""Cancellable, tree-safe subprocess execution (``core.proc``).

The property under test is the one that made the app hang: every external
tool must be killable *without* the caller's thread being touched, because the
old fallback (``QThread.terminate()``, i.e. Windows' ``TerminateThread``) can
fire while a thread holds a CRT/heap lock during a blocked pipe read and wedge
the whole process. ``proc.run`` fixes that by polling and killing the actual
OS process tree.
"""

from __future__ import annotations

import platform
import subprocess
import threading
import time

import pytest

from cortex_unified.core import proc

IS_WINDOWS = platform.system() == "Windows"


def test_normal_completion_returns_output():
    result = proc.run(["cmd", "/c", "echo hello"] if IS_WINDOWS else ["echo", "hello"],
                      timeout=10)
    assert result.returncode == 0
    assert b"hello" in result.stdout


def test_nonzero_exit_is_reported_not_raised():
    result = proc.run(["cmd", "/c", "exit 3"] if IS_WINDOWS else ["sh", "-c", "exit 3"],
                      timeout=10)
    assert result.returncode == 3


def test_real_timeout_raises_and_is_prompt():
    cmd = (["ping", "-n", "10", "127.0.0.1"] if IS_WINDOWS
           else ["sleep", "10"])
    t0 = time.perf_counter()
    with pytest.raises(subprocess.TimeoutExpired):
        proc.run(cmd, timeout=1)
    elapsed = time.perf_counter() - t0
    # Bounded by the poll interval, not by the process's own duration - this is
    # the whole point: a 10s ping must not hold up a 1s timeout.
    assert elapsed < 3.0


def test_cancel_event_raises_and_is_prompt():
    cmd = (["ping", "-n", "10", "127.0.0.1"] if IS_WINDOWS
           else ["sleep", "10"])
    event = threading.Event()

    def _cancel_soon():
        time.sleep(0.5)
        event.set()

    threading.Thread(target=_cancel_soon).start()
    t0 = time.perf_counter()
    with pytest.raises(proc.ProcessCancelled):
        proc.run(cmd, cancel_event=event)
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0


def test_cancel_takes_priority_even_with_a_long_timeout():
    """A cancel_event must not wait for a generous timeout to take effect."""
    cmd = (["ping", "-n", "30", "127.0.0.1"] if IS_WINDOWS else ["sleep", "30"])
    event = threading.Event()
    event.set()  # already cancelled before the process even starts polling
    t0 = time.perf_counter()
    with pytest.raises(proc.ProcessCancelled):
        proc.run(cmd, timeout=300, cancel_event=event)
    assert time.perf_counter() - t0 < 3.0


@pytest.mark.skipif(not IS_WINDOWS, reason="tree-kill verification uses Windows tools")
def test_timeout_kills_the_whole_process_tree(tmp_path):
    """The property that matters: children of the killed process must die too.

    Simulates the app's real call pattern (``powershell -Command dism ...``): a
    wrapper process spawns a child, and only killing the wrapper would leave
    the child as an orphan consuming resources indefinitely.
    """
    pid_file = tmp_path / "child_pid.txt"
    script = (
        'Start-Process ping -ArgumentList "-n","30","127.0.0.1" -PassThru '
        f'| Select-Object -ExpandProperty Id | Out-File "{pid_file}"; '
        "Start-Sleep -Seconds 30"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        proc.run(["powershell", "-NoProfile", "-Command", script], timeout=2)

    # Give the filesystem a moment and read the child's PID (UTF-16 via Out-File).
    time.sleep(0.5)
    child_pid = int(pid_file.read_text(encoding="utf-16").strip())

    check = subprocess.run(["tasklist", "/FI", f"PID eq {child_pid}"],
                           capture_output=True, text=True, timeout=10)
    still_alive = str(child_pid) in check.stdout
    if still_alive:
        subprocess.run(["taskkill", "/F", "/PID", str(child_pid)], timeout=10)
    assert not still_alive, "the child process survived killing its parent"


def test_process_cancelled_is_a_subprocess_error():
    """Existing ``except (OSError, subprocess.SubprocessError)`` call sites
    across the codebase must keep working without modification."""
    assert issubclass(proc.ProcessCancelled, subprocess.SubprocessError)


def test_run_never_leaves_output_unread_on_success():
    """A normal fast command must not be affected by the polling loop at all."""
    result = proc.run(["cmd", "/c", "echo ok"] if IS_WINDOWS else ["echo", "ok"],
                      timeout=5)
    assert b"ok" in result.stdout
    assert result.stderr == b""


def test_text_mode_decodes_output():
    result = proc.run(["cmd", "/c", "echo hi"] if IS_WINDOWS else ["echo", "hi"],
                      timeout=5, text=True)
    assert isinstance(result.stdout, str)
    assert "hi" in result.stdout


def test_missing_executable_raises_oserror():
    with pytest.raises(OSError):
        proc.run(["this-binary-does-not-exist-cortex-test"], timeout=5)
