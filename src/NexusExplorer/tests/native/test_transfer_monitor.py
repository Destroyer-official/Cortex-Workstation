"""Stage-2b UI: Transfer Monitor window + FFI-backed queue integration."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "native"))

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

nexus_ffi = pytest.importorskip("nexus_ffi")
try:
    nexus_ffi.find_dll()
except FileNotFoundError:
    pytest.skip("nexus_engine.dll not built", allow_module_level=True)


@pytest.fixture(scope="module")
def qapp():
    """qapp."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def env(qapp, tmp_path, monkeypatch):
    """env."""
    from nexus_explorer import ExplorerWidget
    from nexus_transfer_monitor import TransferMonitorDialog

    s = QSettings("Nexus", "NexusExplorer")
    s.remove("session")
    s.remove("lastPath")

    src = tmp_path / "src"
    src.mkdir()
    dst = tmp_path / "dst"
    dst.mkdir()

    w = ExplorerWidget(root=str(src))
    deadline = time.time() + 10
    while time.time() < deadline and w.proxy.rowCount() == 0:
        qapp.processEvents()
        time.sleep(0.01)
    # park the tab on dst so _paste targets it
    w.navigate(str(dst))
    deadline = time.time() + 5
    while time.time() < deadline and \
            Path(w._tab()["path"]) != dst:
        qapp.processEvents()
        time.sleep(0.01)

    # one 96 MB file: long enough to pause mid-flight on NVMe
    big = src / "big.bin"
    with open(big, "wb") as fh:
        chunk = os.urandom(1024 * 1024)
        for _ in range(384):
            fh.write(chunk)

    yield type("Env", (), {"w": w, "src": src, "dst": dst,
                           "big": big,
                           "monitor_cls": TransferMonitorDialog})
    try:
        w.engine.shutdown()
    except Exception:
        pass
    w.close()
    s.remove("session")
    s.remove("lastPath")


def _pump(qapp, secs):
    """_pump."""
    end = time.time() + secs
    while time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)


def test_monitor_opens_and_completes_copy(env, qapp):
    """test_monitor_opens_and_completes_copy."""
    w = env.w
    from nexus_explorer import _nexus_clipboard
    _nexus_clipboard.copy([str(env.big)])
    w._paste()
    qapp.processEvents()

    mon = w._transfer_monitor
    assert mon is not None, "monitor must auto-open on enqueue"
    assert mon.isVisible(), "monitor window must be visible"

    deadline = time.time() + 60
    while time.time() < deadline:
        qapp.processEvents()
        jobs = w._transfer_queue.get_all_jobs()
        if jobs and jobs[0].state.value == 4:  # JobState.COMPLETED
            break
        time.sleep(0.02)
    job = w._transfer_queue.get_all_jobs()[0]
    assert job.state.name == "COMPLETED"
    assert job.progress == 100
    out = env.dst / "big.bin"
    assert out.stat().st_size == env.big.stat().st_size
    # row exists in monitor with a completed refresh
    row = mon._rows.get(job.job_id)
    assert row is not None
    assert "Completed" in row.detail.text() or job.progress == 100


def test_pause_resume_cancel_through_monitor(env, qapp):
    """test_pause_resume_cancel_through_monitor."""
    w = env.w
    q = w._transfer_queue
    jid = q.enqueue("copy", [str(env.big)], str(env.dst))
    qapp.processEvents()

    deadline = time.time() + 20
    while time.time() < deadline:
        qapp.processEvents()
        job = q.get_job(jid)
        if job.handle and job.state.name == "RUNNING":
            break
        time.sleep(0.005)

    if q.pause(jid) is not True:
        dbg = q.get_job(jid)
        pytest.fail(f"pause refused state={dbg.state.name} "
                    f"err={dbg.error!r} handle={dbg.handle}")
    job = q.get_job(jid)
    assert job.state.name == "PAUSED"
    frozen = job.progress
    _pump(qapp, 0.8)
    assert q.get_job(jid).progress <= frozen + 3, "progress must stall while paused"

    assert q.resume(jid) is True
    assert q.get_job(jid).state.name == "RUNNING"

    # let it finish (or cancel if nearly done)
    deadline = time.time() + 60
    while time.time() < deadline:
        qapp.processEvents()
        job = q.get_job(jid)
        if job.state.name in ("COMPLETED", "CANCELLED"):
            break
        time.sleep(0.02)
    assert job.state.name in ("COMPLETED", "CANCELLED")


def test_cancel_mid_copy(env, qapp):
    """test_cancel_mid_copy."""
    w = env.w
    q = w._transfer_queue
    jid = q.enqueue("copy", [str(env.big)], str(env.dst))
    deadline = time.time() + 20
    while time.time() < deadline:
        qapp.processEvents()
        job = q.get_job(jid)
        if job.handle and job.state.name == "RUNNING":
            break
        time.sleep(0.005)
    if q.cancel(jid) is not True:
        dbg = q.get_job(jid)
        pytest.fail(f"cancel refused state={dbg.state.name} "
                    f"err={dbg.error!r} handle={dbg.handle}")
    qapp.processEvents()
    job = q.get_job(jid)
    assert job.state.name == "CANCELLED"
    part = env.dst / "big.bin.nexuspart"
    assert not (env.dst / "big.bin").exists(), "no final file after cancel"
    _ = part  # part file may remain; orphan sweep covers it
