"""Unit tests for NTFS MFT & Directory Index slack scrubber."""

import pytest

from cortex_unified.system_tools.mft_slack_scrubber import (
    MftScrubReport,
    MftSlackScrubber,
    NtfsMftGeometry,
)


def test_parse_ntfsinfo():
    """test_parse_ntfsinfo.

    Manages test parse ntfsinfo operations and coordinates related state changes for the component.
    """
    sample = """
NTFS Volume Serial Number :       0x7e89ddb1
Bytes Per Sector  :                512
Bytes Per Cluster :                4096
Bytes Per FileRecordSegment :      1024
Clusters Per FileRecordSegment :   0
Mft Valid Data Length :            262144000
Mft Start Lcn :                    0x00000000000c0000
Total Clusters :                   10000000
Free Clusters :                    4000000
"""
    geom = MftSlackScrubber.parse_ntfsinfo_output("C:", sample)
    assert geom.volume_letter == "C:"
    assert geom.bytes_per_sector == 512
    assert geom.bytes_per_cluster == 4096
    assert geom.bytes_per_file_record_segment == 1024
    assert geom.mft_valid_data_length == 262144000
    assert geom.total_clusters == 10000000
    assert geom.estimated_mft_records == (262144000 // 1024)
    assert geom.estimated_free_mft_records > 0


def test_audit_structure():
    """test_audit_structure.

    Manages test audit structure operations and coordinates related state changes for the component.
    """
    scrubber = MftSlackScrubber("C:")
    report = scrubber.audit()
    assert isinstance(report, MftScrubReport)
    d = report.to_dict()
    assert "volume" in d
    assert "slack_bytes" in d


def test_scrub_structure():
    """test_scrub_structure.

    Manages test scrub structure operations and coordinates related state changes for the component.
    """
    scrubber = MftSlackScrubber("C:")
    report = scrubber.scrub()
    assert isinstance(report, MftScrubReport)
