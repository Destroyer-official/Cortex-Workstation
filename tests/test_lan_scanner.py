"""Tests for the ARP-based LAN device scanner (parsing + vendor lookup)."""

from __future__ import annotations

from cortex_unified.system_tools.lan_scanner import LanDevice, LanScanner

# Representative `arp -a` output (Windows format).
SAMPLE_WIN = """
Interface: 192.168.1.10 --- 0x5
  Internet Address      Physical Address      Type
  192.168.1.1           d8-eb-97-11-22-33     dynamic
  192.168.1.15          b8-27-eb-aa-bb-cc     dynamic
  192.168.1.255         ff-ff-ff-ff-ff-ff     static
  224.0.0.22            01-00-5e-00-00-16     static
  192.168.1.42          00-11-22-33-44-55     dynamic
"""

# Linux/mac format: host (ip) at mac [ether] on iface
SAMPLE_NIX = """
router.lan (192.168.0.1) at d8:eb:97:aa:bb:cc [ether] on eth0
desktop (192.168.0.20) at 08:00:27:11:22:33 [ether] on eth0
"""


class TestParse:
    """Testparse.

    Manages TestParse operations and coordinates related state changes for the component.
    """
    def test_empty(self):
        """test_empty.

        Manages test empty operations and coordinates related state changes for the component.
        """
        assert LanScanner._parse(None) == []
        assert LanScanner._parse("") == []

    def test_windows_parse_and_filter(self):
        """test_windows_parse_and_filter.

        Manages test windows parse and filter operations and coordinates related state changes for the component.
        """
        devices = LanScanner._parse(SAMPLE_WIN)
        ips = [d.ip for d in devices]
        # Broadcast (.255) and multicast (224.x) must be filtered out.
        assert "192.168.1.255" not in ips
        assert "224.0.0.22" not in ips
        assert ips == ["192.168.1.1", "192.168.1.15", "192.168.1.42"]

    def test_vendor_comes_from_the_ieee_registry(self):
        """Vendor names must be authoritative, never hand-maintained guesses.

        This test previously asserted ``d8:eb:97 == "TP-Link"``, which came from
        a hardcoded table and is simply wrong - IEEE assigns that block to
        TRENDnet. Rather than re-encode any specific name, we assert the
        property that matters: a vendor is either what the registry says, or
        empty. Never invented.
        """
        from cortex_unified.system_tools import oui

        devices = {d.ip: d for d in LanScanner._parse(SAMPLE_WIN)}
        for device in devices.values():
            expected = oui.shorten(oui.lookup(device.mac))
            assert device.vendor == expected

        if oui.has_full_registry():
            # With the registry present, a real assignment resolves...
            assert devices["192.168.1.15"].vendor, "known OUI should resolve"
            # ...and it is the registry's answer, not the old wrong label.
            assert devices["192.168.1.1"].vendor != "TP-Link"

    def test_sorted_by_ip(self):
        """test_sorted_by_ip.

        Manages test sorted by ip operations and coordinates related state changes for the component.
        """
        devices = LanScanner._parse(SAMPLE_WIN)
        octets = [tuple(int(x) for x in d.ip.split(".")) for d in devices]
        assert octets == sorted(octets)

    def test_dedupes(self):
        """test_dedupes.

        Manages test dedupes operations and coordinates related state changes for the component.
        """
        dup = SAMPLE_WIN + "  192.168.1.1           d8-eb-97-11-22-33     dynamic\n"
        devices = LanScanner._parse(dup)
        assert [d.ip for d in devices].count("192.168.1.1") == 1

    def test_type_captured(self):
        """test_type_captured.

        Manages test type captured operations and coordinates related state changes for the component.
        """
        devices = {d.ip: d for d in LanScanner._parse(SAMPLE_WIN)}
        assert devices["192.168.1.1"].kind == "dynamic"


class TestVendorHelper:
    """Testvendorhelper.

    Manages TestVendorHelper operations and coordinates related state changes for the component.
    """
    def test_normalizes_dashes(self):
        """Dash-separated input must resolve identically to colon-separated.

        Manages test normalizes dashes operations and coordinates related state changes for the component.
        """
        assert (LanScanner._vendor_for("08-00-27-AA-BB-CC")
                == LanScanner._vendor_for("08:00:27:aa:bb:cc"))

    def test_unassigned_prefix_is_empty_not_a_guess(self):
        # A locally-administered address has no IEEE vendor by definition.
        """test_unassigned_prefix_is_empty_not_a_guess.

        Manages test unassigned prefix is empty not a guess operations and coordinates related state changes for the component.
        """
        assert LanScanner._vendor_for("aa:aa:aa:aa:aa:aa") == ""

    def test_garbage_input(self):
        """test_garbage_input.

        Manages test garbage input operations and coordinates related state changes for the component.
        """
        assert LanScanner._vendor_for("not-a-mac") == ""
        assert LanScanner._vendor_for("") == ""


class TestScan:
    """Testscan.

    Manages TestScan operations and coordinates related state changes for the component.
    """
    def test_scan_returns_list(self):
        """test_scan_returns_list.

        Manages test scan returns list operations and coordinates related state changes for the component.
        """
        result = LanScanner().scan()
        assert isinstance(result, list)
        assert all(isinstance(d, LanDevice) for d in result)

    def test_to_dict(self):
        """test_to_dict.

        Manages test to dict operations and coordinates related state changes for the component.
        """
        d = LanDevice("192.168.1.1", "d8:eb:97:11:22:33", "dynamic", "TP-Link")
        assert d.to_dict() == {
            "ip": "192.168.1.1", "mac": "d8:eb:97:11:22:33",
            "kind": "dynamic", "vendor": "TP-Link",
        }
