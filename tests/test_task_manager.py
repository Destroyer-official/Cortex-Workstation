"""Tests for the task-manager backend (live snapshot + honest reconciliation)."""

from __future__ import annotations

import pytest

pytest.importorskip("psutil", reason="psutil not installed")

from cortex_unified.system_tools.task_manager import TaskManager


@pytest.fixture
def tm():
    # Fresh instance so priming state is deterministic per test.
    """tm."""
    return TaskManager()


class TestSnapshot:
    """TestSnapshot."""
    def test_snapshot_shape(self, tm):
        """test_snapshot_shape."""
        snap = tm.snapshot()
        assert "error" not in snap
        assert set(snap) >= {"cpu", "memory", "processes"}

    def test_cpu_block(self, tm):
        """test_cpu_block."""
        cpu = tm.snapshot()["cpu"]
        assert cpu["cores"] >= 1
        assert 0.0 <= cpu["total_percent"] <= 100.0 * cpu["cores"]
        assert isinstance(cpu["per_core"], list)
        assert len(cpu["per_core"]) == cpu["cores"]

    def test_processes_have_fields(self, tm):
        """test_processes_have_fields."""
        procs = tm.snapshot()["processes"]
        assert procs, "expected at least one running process"
        p = procs[0]
        assert set(p) >= {"pid", "name", "cpu", "rss", "threads", "user", "status"}
        # This test process itself must be present.
        import os
        assert any(pr["pid"] == os.getpid() for pr in procs)

    def test_processes_sorted_by_memory_desc(self, tm):
        """test_processes_sorted_by_memory_desc."""
        procs = tm.snapshot()["processes"]
        rss = [p["rss"] for p in procs]
        assert rss == sorted(rss, reverse=True)

    def test_idle_process_excluded(self, tm):
        """The idle process (unused CPU) must never appear as a real process."""
        procs = tm.snapshot()["processes"]
        assert all(p["pid"] != 0 for p in procs)
        assert all(p["name"].lower() not in {"system idle process", "idle"}
                   for p in procs)

    def test_total_cpu_in_range(self, tm):
        """test_total_cpu_in_range."""
        cpu = tm.snapshot()["cpu"]
        assert 0.0 <= cpu["total_percent"] <= 100.0

    def test_per_process_cpu_normalized(self, tm):
        # After priming, a second snapshot yields real deltas; each normalized
        # value should be within a sane 0..100 band (rounding tolerance).
        """test_per_process_cpu_normalized."""
        tm.snapshot()
        procs = tm.snapshot()["processes"]
        assert all(0.0 <= p["cpu"] <= 100.5 for p in procs)


class TestMemoryReconciliation:
    """TestMemoryReconciliation."""
    def test_core_fields_present(self, tm):
        """test_core_fields_present."""
        mem = tm.snapshot()["memory"]
        for key in ("total", "available", "used", "percent",
                    "sum_process_ws", "ws_overlaps"):
            assert key in mem

    def test_used_is_total_minus_available(self, tm):
        """test_used_is_total_minus_available."""
        mem = tm.snapshot()["memory"]
        assert mem["used"] == mem["total"] - mem["available"]

    def test_no_false_equation(self, tm):
        """We must NOT pretend process working sets sum to 'in use'.

        Because working sets double-count shared memory, their sum can even
        exceed 'in use'. The backend flags that honestly rather than clamping.
        """
        mem = tm.snapshot()["memory"]
        assert isinstance(mem["ws_overlaps"], bool)
        assert mem["ws_overlaps"] == (mem["sum_process_ws"] > mem["used"])

    def test_hardware_reserved_consistent_if_present(self, tm):
        """test_hardware_reserved_consistent_if_present."""
        mem = tm.snapshot()["memory"]
        if "installed" in mem:
            assert mem["installed"] >= mem["total"]
            assert mem["hardware_reserved"] == mem["installed"] - mem["total"]


class TestEndProcess:
    """TestEndProcess."""
    def test_end_nonexistent_pid(self, tm):
        # PID 0 / a very high unlikely PID -> graceful failure, never raises.
        """test_end_nonexistent_pid."""
        ok, msg = tm.end_process(999_999_99)
        assert ok is False
        assert isinstance(msg, str) and msg

    def test_end_returns_tuple(self, tm):
        """test_end_returns_tuple."""
        result = tm.end_process(-1)
        assert isinstance(result, tuple) and len(result) == 2


def test_singleton_instance():
    """test_singleton_instance."""
    a = TaskManager.instance()
    b = TaskManager.instance()
    assert a is b
