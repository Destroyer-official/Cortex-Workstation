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
    def test_empty(self):
        assert LanScanner._parse(None) == []
        assert LanScanner._parse("") == []

    def test_windows_parse_and_filter(self):
        devices = LanScanner._parse(SAMPLE_WIN)
        ips = [d.ip for d in devices]
        # Broadcast (.255) and multicast (224.x) must be filtered out.
        assert "192.168.1.255" not in ips
        assert "224.0.0.22" not in ips
        assert ips == ["192.168.1.1", "192.168.1.15", "192.168.1.42"]

    def test_vendor_lookup(self):
        devices = {d.ip: d for d in LanScanner._parse(SAMPLE_WIN)}
        assert devices["192.168.1.1"].vendor == "TP-Link"
        assert devices["192.168.1.15"].vendor == "Raspberry Pi"
        # Unknown OUI -> empty, not a guess.
        assert devices["192.168.1.42"].vendor == ""

    def test_sorted_by_ip(self):
        devices = LanScanner._parse(SAMPLE_WIN)
        octets = [tuple(int(x) for x in d.ip.split(".")) for d in devices]
        assert octets == sorted(octets)

    def test_dedupes(self):
        dup = SAMPLE_WIN + "  192.168.1.1           d8-eb-97-11-22-33     dynamic\n"
        devices = LanScanner._parse(dup)
        assert [d.ip for d in devices].count("192.168.1.1") == 1

    def test_type_captured(self):
        devices = {d.ip: d for d in LanScanner._parse(SAMPLE_WIN)}
        assert devices["192.168.1.1"].kind == "dynamic"


class TestVendorHelper:
    def test_normalizes_dashes(self):
        assert LanScanner._vendor_for("08-00-27-AA-BB-CC") == "VirtualBox"

    def test_unknown(self):
        assert LanScanner._vendor_for("aa:aa:aa:aa:aa:aa") == ""


class TestScan:
    def test_scan_returns_list(self):
        result = LanScanner().scan()
        assert isinstance(result, list)
        assert all(isinstance(d, LanDevice) for d in result)

    def test_to_dict(self):
        d = LanDevice("192.168.1.1", "d8:eb:97:11:22:33", "dynamic", "TP-Link")
        assert d.to_dict() == {
            "ip": "192.168.1.1", "mac": "d8:eb:97:11:22:33",
            "kind": "dynamic", "vendor": "TP-Link",
        }
