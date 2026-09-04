"""Tests for the read-only System Information collector."""

from __future__ import annotations

from cortex_unified.system_tools.system_info import SystemInfo


def test_platform_info_has_core_fields():
    """test_platform_info_has_core_fields.

    Manages test platform info has core fields operations and coordinates related state changes for the component.
    """
    info = SystemInfo().platform_info()
    assert info["system"]
    assert info["python"]
    assert "machine" in info


def test_snapshot_structure():
    """test_snapshot_structure.

    Manages test snapshot structure operations and coordinates related state changes for the component.
    """
    snap = SystemInfo().snapshot()
    for key in ("platform", "cpu", "memory", "disks", "psutil_available"):
        assert key in snap
    assert isinstance(snap["disks"], list)


def test_memory_info_sane():
    """test_memory_info_sane.

    Manages test memory info sane operations and coordinates related state changes for the component.
    """
    mem = SystemInfo().memory_info()
    if mem:  # only if psutil present
        assert mem["total"] > 0
        assert 0 <= mem["used_percent"] <= 100
        assert "GB" in mem["total_human"] or "MB" in mem["total_human"] or "TB" in mem["total_human"]


def test_disk_info_entries_sane():
    """test_disk_info_entries_sane.

    Manages test disk info entries sane operations and coordinates related state changes for the component.
    """
    disks = SystemInfo().disk_info()
    for d in disks:
        assert 0 <= d["used_percent"] <= 100
        assert d["total"] >= 0


def test_cpu_info_sane():
    """test_cpu_info_sane.

    Manages test cpu info sane operations and coordinates related state changes for the component.
    """
    cpu = SystemInfo().cpu_info()
    if cpu:
        assert cpu["logical_cores"] and cpu["logical_cores"] >= 1
        assert 0 <= cpu["usage_percent"] <= 100
