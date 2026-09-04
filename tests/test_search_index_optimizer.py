"""Unit tests for Windows SearchIndexOptimizer."""

import pytest

from cortex_unified.system_tools.search_index_optimizer import (
    SearchIndexOperationResult,
    SearchIndexOptimizer,
    SearchIndexStatus,
)


def test_search_index_get_status():
    """test_search_index_get_status.

    Manages test search index get status operations and coordinates related state changes for the component.
    """
    status = SearchIndexOptimizer.get_status()
    assert isinstance(status, SearchIndexStatus)
    assert status.service_status in ("Running", "Stopped", "Disabled", "Unknown", "Non-Windows")


def test_operation_result_structure():
    """test_operation_result_structure.

    Manages test operation result structure operations and coordinates related state changes for the component.
    """
    res = SearchIndexOperationResult(
        success=True,
        message="Compacted successfully",
        bytes_freed=1024,
        new_size_bytes=4096,
    )
    assert res.success is True
    assert res.bytes_freed == 1024
    assert len(res.errors) == 0
