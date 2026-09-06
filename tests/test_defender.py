"""Tests for the Windows Defender status reader (parsing + gating)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.defender import DefenderStatus, WindowsDefender

IS_WINDOWS = platform.system() == "Windows"


class TestStatusParse:
    """Group teststatusparse tests covering empty; healthy; unhealthy old signatures; unhealthy rtp off; list payload; wmi date."""
    def test_empty(self):
        """Verify empty via WindowsDefender._parse_status."""
        assert WindowsDefender._parse_status(None).available is False
        assert WindowsDefender._parse_status("bad{").available is False

    def test_healthy(self):
        """Verify healthy via WindowsDefender._parse_status."""
        payload = (
            '{"RealTimeProtectionEnabled":true,"AntivirusEnabled":true,'
            '"IsTamperProtected":true,"AntivirusSignatureVersion":"1.400.1.0",'
            '"AntivirusSignatureAge":1,"QuickScanEndTime":"2026-07-08T09:00:00",'
            '"AMEngineVersion":"1.1.24000.1"}'
        )
        s = WindowsDefender._parse_status(payload)
        assert s.available and s.realtime_protection and s.antivirus_enabled
        assert s.signature_age_days == 1
        assert s.healthy is True

    def test_unhealthy_old_signatures(self):
        """Verify unhealthy old signatures via WindowsDefender._parse_status."""
        payload = ('{"RealTimeProtectionEnabled":true,"AntivirusEnabled":true,'
                   '"AntivirusSignatureAge":30}')
        s = WindowsDefender._parse_status(payload)
        assert s.healthy is False  # signatures too old

    def test_unhealthy_rtp_off(self):
        """Verify unhealthy rtp off via WindowsDefender._parse_status."""
        payload = '{"RealTimeProtectionEnabled":false,"AntivirusEnabled":true}'
        assert WindowsDefender._parse_status(payload).healthy is False

    def test_list_payload(self):
        """Verify list payload via WindowsDefender._parse_status."""
        payload = '[{"RealTimeProtectionEnabled":true,"AntivirusEnabled":true}]'
        assert WindowsDefender._parse_status(payload).available is True

    def test_wmi_date(self):
        """Verify wmi date via WindowsDefender._parse_status."""
        payload = '{"QuickScanEndTime":"/Date(1690000000000)/"}'
        s = WindowsDefender._parse_status(payload)
        assert s.last_quick_scan  # parsed to a date string


class TestThreatsParse:
    """Group testthreatsparse tests covering empty; single and list; threat fields."""
    def test_empty(self):
        """Verify empty via WindowsDefender._parse_threats."""
        assert WindowsDefender._parse_threats(None) == []

    def test_single_and_list(self):
        """Verify single and list via WindowsDefender._parse_threats."""
        one = '{"Time":"2026-07-08T09:00:00","Threat":"Trojan:Win32/X","ThreatID":42}'
        assert len(WindowsDefender._parse_threats(one)) == 1
        many = f'[{one},{one}]'
        assert len(WindowsDefender._parse_threats(many)) == 2

    def test_threat_fields(self):
        """Verify threat fields via WindowsDefender._parse_threats."""
        t = WindowsDefender._parse_threats(
            '{"Time":"t","Threat":"EICAR_Test","ThreatID":1}')[0]
        assert t["threat"] == "EICAR_Test"
        assert t["id"] == 1


class TestDataclassAndSupport:
    """Group testdataclassandsupport tests covering to dict; is supported; status never raises."""
    def test_to_dict(self):
        """Verify to dict via DefenderStatus, to_dict."""
        d = DefenderStatus(available=True, realtime_protection=True,
                           antivirus_enabled=True, signature_age_days=2).to_dict()
        assert d["healthy"] is True
        assert set(d) >= {"available", "realtime_protection", "healthy",
                          "signature_version", "last_quick_scan"}

    def test_is_supported(self):
        """Verify is supported via WindowsDefender.is_supported."""
        assert WindowsDefender.is_supported() == IS_WINDOWS

    def test_status_never_raises(self):
        """Verify status never raises via WindowsDefender, status."""
        assert isinstance(WindowsDefender().status(), DefenderStatus)
