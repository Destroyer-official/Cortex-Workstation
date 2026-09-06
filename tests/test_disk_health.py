"""Tests for the read-only S.M.A.R.T. / disk-health monitor.

We never touch a real drive's controller here; instead we exercise the JSON
parser with representative ``Get-PhysicalDisk`` output and verify the honest
platform gating. Real ``get_health()`` is only meaningful on Windows.
"""

from __future__ import annotations

import platform

from cortex_unified.system_tools.disk_health import DiskHealth, DiskHealthMonitor

IS_WINDOWS = platform.system() == "Windows"


class TestParse:
    """Group testparse tests covering empty returns empty list; invalid json returns empty; single object becomes one disk; array of disks; missing reliability counters stay none; garbage numeric fields coerce to none."""
    def test_empty_returns_empty_list(self):
        """Verify empty returns empty list via DiskHealthMonitor._parse."""
        assert DiskHealthMonitor._parse(None) == []
        assert DiskHealthMonitor._parse("") == []

    def test_invalid_json_returns_empty(self):
        """Verify invalid json returns empty via DiskHealthMonitor._parse."""
        assert DiskHealthMonitor._parse("not json {{{") == []

    def test_single_object_becomes_one_disk(self):
        """Verify single object becomes one disk via DiskHealthMonitor._parse."""
        payload = (
            '{"Name":"Samsung SSD 980","MediaType":"SSD","Health":"Healthy",'
            '"Op":"OK","Size":1000204886016,"Wear":3,"Temp":41,'
            '"Realloc":0,"Hours":1200}'
        )
        disks = DiskHealthMonitor._parse(payload)
        assert len(disks) == 1
        d = disks[0]
        assert isinstance(d, DiskHealth)
        assert d.name == "Samsung SSD 980"
        assert d.media_type == "SSD"
        assert d.health_status == "Healthy"
        assert d.is_healthy is True
        assert d.size_bytes == 1000204886016
        assert d.wear_percent == 3
        assert d.temperature_c == 41
        assert d.reallocated_sectors == 0
        assert d.power_on_hours == 1200

    def test_array_of_disks(self):
        """Verify array of disks via DiskHealthMonitor._parse."""
        payload = (
            '[{"Name":"Disk A","MediaType":"HDD","Health":"Healthy","Op":"OK","Size":500},'
            '{"Name":"Disk B","MediaType":"SSD","Health":"Warning","Op":"Degraded","Size":250}]'
        )
        disks = DiskHealthMonitor._parse(payload)
        assert len(disks) == 2
        assert disks[0].media_type == "HDD"
        assert disks[1].health_status == "Warning"
        assert disks[1].is_healthy is False

    def test_missing_reliability_counters_stay_none(self):
        """Verify missing reliability counters stay none via DiskHealthMonitor._parse."""
        payload = (
            '{"Name":"Old Disk","MediaType":"HDD","Health":"Healthy","Op":"OK",'
            '"Size":320072933376,"Wear":null,"Temp":null,"Realloc":null,"Hours":null}'
        )
        d = DiskHealthMonitor._parse(payload)[0]
        assert d.wear_percent is None
        assert d.temperature_c is None
        assert d.reallocated_sectors is None
        assert d.power_on_hours is None

    def test_garbage_numeric_fields_coerce_to_none(self):
        """Verify garbage numeric fields coerce to none via DiskHealthMonitor._parse."""
        payload = (
            '{"Name":"X","MediaType":"SSD","Health":"Healthy","Op":"OK",'
            '"Size":"notanumber","Wear":"n/a"}'
        )
        d = DiskHealthMonitor._parse(payload)[0]
        assert d.size_bytes == 0        # size falls back to 0
        assert d.wear_percent is None

    def test_defaults_for_absent_keys(self):
        """Verify defaults for absent keys via DiskHealthMonitor._parse."""
        d = DiskHealthMonitor._parse('{}')[0]
        assert d.name == "Unknown"
        assert d.media_type == "Unspecified"
        assert d.health_status == "Unknown"
        assert d.is_healthy is False


class TestToDict:
    """Group testtodict tests covering to dict roundtrip keys."""
    def test_to_dict_roundtrip_keys(self):
        """Verify to dict roundtrip keys via DiskHealth, d.to_dict."""
        d = DiskHealth(
            name="N", media_type="SSD", health_status="Healthy",
            operational_status="OK", size_bytes=1024, wear_percent=1,
            temperature_c=40, reallocated_sectors=0, power_on_hours=10,
        )
        out = d.to_dict()
        assert out["name"] == "N"
        assert out["health_status"] == "Healthy"
        assert out["wear_percent"] == 1
        assert set(out) == {
            "name", "media_type", "health_status", "operational_status",
            "size_bytes", "wear_percent", "temperature_c",
            "reallocated_sectors", "power_on_hours",
        }


class TestSupport:
    """Group testsupport tests covering is supported matches platform; get health returns list."""
    def test_is_supported_matches_platform(self):
        """Verify is supported matches platform via DiskHealthMonitor.is_supported."""
        assert DiskHealthMonitor.is_supported() == IS_WINDOWS

    def test_get_health_returns_list(self):
        # Never raises; returns [] off-Windows, a list of DiskHealth on Windows.
        """Verify get health returns list via DiskHealthMonitor, get_health."""
        result = DiskHealthMonitor().get_health()
        assert isinstance(result, list)
        assert all(isinstance(d, DiskHealth) for d in result)
        if not IS_WINDOWS:
            assert result == []
