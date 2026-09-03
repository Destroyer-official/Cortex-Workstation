"""Worker-shutdown safety: never call ``QThread.terminate()``.

Background: closing the window while a worker was still blocked inside a
subprocess call used to fall back to ``QThread.terminate()`` (Windows'
``TerminateThread``). If that fires while the thread holds a CRT/heap lock -
exactly what happens mid-pipe-read inside ``subprocess.communicate()``, which
is where most of this app's workers spend their time - the lock is never
released and any other thread that later needs it hangs forever. That is a
corrupted-process bug, and it can surface as an apparently unrelated hang much
later in the same process.

These tests exercise ``_shutdown_workers`` directly against synthetic workers
so they run in a few seconds without needing a real multi-minute DISM/SFC call,
and assert the property that matters: a worker that honours cancellation lets
the window close promptly, and a worker that does not is *detached*, never
force-killed.
"""

from __future__ import annotations

import os
import threading
import time

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """app."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    """window."""
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    yield win
    # Best-effort: the window may already be closed by the test itself.
    try:
        win.close()
    except Exception:  # noqa: BLE001
        pass


class _CooperativeWorker(QObject):
    """Simulates a proc.run()-style call: polls cancel_event in small slices."""

    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, poll_s: float = 0.05):
        """__init__."""
        super().__init__()
        self._cancel = threading.Event()
        self._poll_s = poll_s

    def cancel(self) -> None:
        """cancel."""
        self._cancel.set()

    def run(self) -> None:
        """run."""
        for _ in range(200):  # up to 10s if never cancelled
            if self._cancel.is_set():
                return
            time.sleep(self._poll_s)
        self.finished.emit("timed out waiting to be cancelled")


class _StubbornWorker(QObject):
    """Simulates a bug: cancel() is called but run() never checks it.

    This is the scenario ``terminate()`` used to "fix" unsafely; the shutdown
    path must now detach it instead.
    """

    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, sleep_s: float = 30.0):
        """__init__."""
        super().__init__()
        self.cancel_called = threading.Event()
        self._sleep_s = sleep_s

    def cancel(self) -> None:
        """cancel."""
        self.cancel_called.set()

    def run(self) -> None:
        """run."""
        time.sleep(self._sleep_s)
        self.finished.emit("done")


def test_cooperative_worker_lets_close_return_promptly(app, window):
    """test_cooperative_worker_lets_close_return_promptly."""
    worker = _CooperativeWorker()
    window.run_worker(worker, lambda *_: None)

    t0 = time.perf_counter()
    window.close()
    elapsed = time.perf_counter() - t0

    assert elapsed < window._CLOSE_GRACE_S, \
        "a cancellable worker must not need the full grace period"
    assert not getattr(window, "_workers_stuck", None)


def _wait_for_natural_completion(thread, timeout_s: float = 15.0) -> None:
    """Let a detached-but-still-running QThread finish on its own.

    The production app never needs this: a truly stuck worker means
    ``os._exit()`` ends the process before Python ever tries to delete the
    dangling wrapper. This test has no such escape hatch, so it must let the
    real background thread run to completion before returning - otherwise
    interpreter shutdown deletes a still-running QThread and the process
    aborts with the exact 0xC0000409 this fix exists to prevent, which would
    make the test process crash even though every assertion passed.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline and thread.isRunning():
        time.sleep(0.05)


def test_uncooperative_worker_is_detached_not_terminated(app, window):
    # Long enough that it is still running at the end of the grace period,
    # short enough that the test doesn't hang waiting for it to finish.
    """test_uncooperative_worker_is_detached_not_terminated."""
    stub_sleep = window._CLOSE_GRACE_S + 1.0
    worker = _StubbornWorker(sleep_s=stub_sleep)
    window.run_worker(worker, lambda *_: None)

    t0 = time.perf_counter()
    window.close()
    elapsed = time.perf_counter() - t0

    # cancel() must still have been called (best-effort cooperative signal)...
    assert worker.cancel_called.is_set()
    # ...but since the worker ignores it, shutdown must wait out the full grace
    # period and then give up by detaching - never crash, never hang forever.
    assert elapsed >= window._CLOSE_GRACE_S - 0.5
    assert elapsed < window._CLOSE_GRACE_S + 5.0, "detach must not hang past the deadline"
    stuck = getattr(window, "_workers_stuck", None)
    assert stuck and len(stuck) == 1
    # The detached thread must be removed from the window's tracked list, so
    # nothing later in the app's lifetime tries to wait on or delete it.
    assert stuck[0] not in window._threads

    _wait_for_natural_completion(stuck[0])


def test_shutdown_workers_never_calls_terminate(app, window, monkeypatch):
    """Guard against the unsafe fallback ever being reintroduced."""
    from PySide6.QtCore import QThread

    calls = []
    original = QThread.terminate

    def _tracking_terminate(self):
        """_tracking_terminate."""
        calls.append(self)
        return original(self)

    monkeypatch.setattr(QThread, "terminate", _tracking_terminate)

    stub_sleep = window._CLOSE_GRACE_S + 1.0
    worker = _StubbornWorker(sleep_s=stub_sleep)
    window.run_worker(worker, lambda *_: None)
    window.close()

    assert calls == [], "QThread.terminate() must never be called during shutdown"

    for thread in getattr(window, "_workers_stuck", []) or []:
        _wait_for_natural_completion(thread)


def test_multiple_workers_shut_down_within_one_shared_deadline(app, window):
    """Several workers must be waited on concurrently, not N times serially."""
    workers = [_CooperativeWorker() for _ in range(5)]
    for w in workers:
        window.run_worker(w, lambda *_: None)

    t0 = time.perf_counter()
    window.close()
    elapsed = time.perf_counter() - t0

    # If shutdown waited per-thread instead of on one shared deadline, this
    # would take 5x as long as a single cooperative worker.
    assert elapsed < window._CLOSE_GRACE_S
    assert not getattr(window, "_workers_stuck", None)
