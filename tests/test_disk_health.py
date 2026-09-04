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
    """Testparse.

    Manages TestParse operations and coordinates related state changes for the component.
    """
    def test_empty_returns_empty_list(self):
        """test_empty_returns_empty_list.

        Manages test empty returns empty list operations and coordinates related state changes for the component.
        """
        assert DiskHealthMonitor._parse(None) == []
        assert DiskHealthMonitor._parse("") == []

    def test_invalid_json_returns_empty(self):
        """test_invalid_json_returns_empty.

        Manages test invalid json returns empty operations and coordinates related state changes for the component.
        """
        assert DiskHealthMonitor._parse("not json {{{") == []

    def test_single_object_becomes_one_disk(self):
        """test_single_object_becomes_one_disk.

        Manages test single object becomes one disk operations and coordinates related state changes for the component.
        """
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
        """test_array_of_disks.

        Manages test array of disks operations and coordinates related state changes for the component.
        """
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
        """test_missing_reliability_counters_stay_none.

        Manages test missing reliability counters stay none operations and coordinates related state changes for the component.
        """
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
        """test_garbage_numeric_fields_coerce_to_none.

        Manages test garbage numeric fields coerce to none operations and coordinates related state changes for the component.
        """
        payload = (
            '{"Name":"X","MediaType":"SSD","Health":"Healthy","Op":"OK",'
            '"Size":"notanumber","Wear":"n/a"}'
        )
        d = DiskHealthMonitor._parse(payload)[0]
        assert d.size_bytes == 0        # size falls back to 0
        assert d.wear_percent is None

    def test_defaults_for_absent_keys(self):
        """test_defaults_for_absent_keys.

        Manages test defaults for absent keys operations and coordinates related state changes for the component.
        """
        d = DiskHealthMonitor._parse('{}')[0]
        assert d.name == "Unknown"
        assert d.media_type == "Unspecified"
        assert d.health_status == "Unknown"
        assert d.is_healthy is False


class TestToDict:
    """Testtodict.

    Manages TestToDict operations and coordinates related state changes for the component.
    """
    def test_to_dict_roundtrip_keys(self):
        """test_to_dict_roundtrip_keys.

        Manages test to dict roundtrip keys operations and coordinates related state changes for the component.
        """
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
    """Testsupport.

    Manages TestSupport operations and coordinates related state changes for the component.
    """
    def test_is_supported_matches_platform(self):
        """test_is_supported_matches_platform.

        Manages test is supported matches platform operations and coordinates related state changes for the component.
        """
        assert DiskHealthMonitor.is_supported() == IS_WINDOWS

    def test_get_health_returns_list(self):
        # Never raises; returns [] off-Windows, a list of DiskHealth on Windows.
        """test_get_health_returns_list.

        Manages test get health returns list operations and coordinates related state changes for the component.
        """
        result = DiskHealthMonitor().get_health()
        assert isinstance(result, list)
        assert all(isinstance(d, DiskHealth) for d in result)
        if not IS_WINDOWS:
            assert result == []
