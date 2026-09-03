"""Tests for the read-only driver inventory (parsing + platform gating)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.driver_inventory import DriverInfo, DriverInventory

IS_WINDOWS = platform.system() == "Windows"


class TestParse:
    """TestParse."""
    def test_empty(self):
        """test_empty."""
        assert DriverInventory._parse(None) == []
        assert DriverInventory._parse("") == []
        assert DriverInventory._parse("garbage{{") == []

    def test_single_object(self):
        """test_single_object."""
        payload = (
            '{"DeviceName":"NVIDIA GeForce","DriverProviderName":"NVIDIA",'
            '"DriverVersion":"31.0.15.3623","DriverDate":"/Date(1690000000000)/",'
            '"DeviceClass":"DISPLAY"}'
        )
        drivers = DriverInventory._parse(payload)
        assert len(drivers) == 1
        d = drivers[0]
        assert isinstance(d, DriverInfo)
        assert d.device_name == "NVIDIA GeForce"
        assert d.provider == "NVIDIA"
        assert d.version == "31.0.15.3623"
        assert d.device_class == "DISPLAY"
        assert d.date  # date parsed to some YYYY-MM-DD

    def test_dedupes_identical_name_version(self):
        """test_dedupes_identical_name_version."""
        payload = (
            '[{"DeviceName":"USB Hub","DriverVersion":"1.0","DriverProviderName":"MS"},'
            '{"DeviceName":"USB Hub","DriverVersion":"1.0","DriverProviderName":"MS"},'
            '{"DeviceName":"USB Hub","DriverVersion":"2.0","DriverProviderName":"MS"}]'
        )
        drivers = DriverInventory._parse(payload)
        assert len(drivers) == 2

    def test_skips_nameless(self):
        """test_skips_nameless."""
        payload = '[{"DriverVersion":"1.0"},{"DeviceName":"","DriverVersion":"2"}]'
        assert DriverInventory._parse(payload) == []

    def test_yyyymmdd_date(self):
        """test_yyyymmdd_date."""
        payload = '{"DeviceName":"X","DriverDate":"20230115000000.000000-000"}'
        d = DriverInventory._parse(payload)[0]
        assert d.date == "2023-01-15"


class TestSupport:
    """TestSupport."""
    def test_is_supported_matches_platform(self):
        """test_is_supported_matches_platform."""
        assert DriverInventory.is_supported() == IS_WINDOWS

    def test_list_drivers_returns_list(self):
        """test_list_drivers_returns_list."""
        result = DriverInventory().list_drivers()
        assert isinstance(result, list)
        if not IS_WINDOWS:
            assert result == []

    def test_to_dict(self):
        """test_to_dict."""
        d = DriverInfo("Dev", "Prov", "1.0", "2023-01-01", "NET")
        out = d.to_dict()
        assert out["device_name"] == "Dev"
        assert set(out) == {"device_name", "provider", "version", "date", "device_class"}
