"""Unit tests for Windows MemoryStandbyPurger NTDLL engine."""

import sys
import pytest

from cortex_unified.system_tools.memory_standby_purger import (
    MemorySnapshot,
    MemoryStandbyPurger,
    PurgeResult,
)


def test_memory_snapshot():
    """test_memory_snapshot.

    Manages test memory snapshot operations and coordinates related state changes for the component.
    """
    purger = MemoryStandbyPurger()
    snap = purger.get_memory_snapshot()
    assert isinstance(snap, MemorySnapshot)
    if sys.platform == "win32":
        assert snap.total_phys_bytes > 0
        assert 0 <= snap.memory_load_percent <= 100
    d = snap.to_dict()
    assert "total_phys" in d
    assert "load_percent" in d


def test_privilege_enable():
    """test_privilege_enable.

    Manages test privilege enable operations and coordinates related state changes for the component.
    """
    purger = MemoryStandbyPurger()
    if sys.platform == "win32":
        # Does not crash regardless of whether process is elevated or not
        res = purger.enable_privilege("SeProfileSingleProcessPrivilege")
        assert isinstance(res, bool)


def test_purge_actions_safe():
    """test_purge_actions_safe.

    Manages test purge actions safe operations and coordinates related state changes for the component.
    """
    purger = MemoryStandbyPurger()
    res1 = purger.purge_standby_list()
    assert isinstance(res1, PurgeResult)
    assert res1.action == "Purge Standby List"

    res2 = purger.purge_working_sets()
    assert isinstance(res2, PurgeResult)

    res3 = purger.purge_modified_page_list()
    assert isinstance(res3, PurgeResult)
