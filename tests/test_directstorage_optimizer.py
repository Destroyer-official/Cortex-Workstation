"""Unit tests for DirectStorage & BypassIO hardware optimizer."""

import pytest

from cortex_unified.system_tools.directstorage_optimizer import (
    BypassIoVolumeReport,
    DirectStorageAuditReport,
    DirectStorageOptimizer,
)


def test_parse_bypassio_supported():
    """test_parse_bypassio_supported.

    Manages test parse bypassio supported operations and coordinates related state changes for the component.
    """
    sample_out = """
BypassIo is supported on C:
Storage Type: NVMe
Volume Driver: stornvme.sys
"""
    rep = DirectStorageOptimizer.parse_bypassio_output("C:", sample_out)
    assert rep.volume_letter == "C:"
    assert rep.is_supported is True
    assert rep.storage_type == "NVMe"
    assert rep.driver_name == "stornvme.sys"
    assert len(rep.blocking_minifilters) == 0


def test_parse_bypassio_blocked():
    """test_parse_bypassio_blocked.

    Manages test parse bypassio blocked operations and coordinates related state changes for the component.
    """
    sample_out = """
BypassIo is not supported on D:
Reason: Incompatible driver detected
Incompatible Driver: legacyfilter.sys
Storage Type: SATA
"""
    rep = DirectStorageOptimizer.parse_bypassio_output("D:", sample_out)
    assert rep.volume_letter == "D:"
    assert rep.is_supported is False
    assert "legacyfilter.sys" in rep.blocking_minifilters
    assert rep.storage_type == "SATA"


def test_audit_structure():
    """test_audit_structure.

    Manages test audit structure operations and coordinates related state changes for the component.
    """
    opt = DirectStorageOptimizer()
    report = opt.audit()
    assert isinstance(report, DirectStorageAuditReport)
    d = report.to_dict()
    assert "total_volumes" in d
    assert "ready_volumes" in d
    assert "recommendations" in d
