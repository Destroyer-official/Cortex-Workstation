"""Deep LAN discovery: parsing, filtering and honest identification.

The bug this module exists to fix: ``arp -a`` only lists devices this PC talked
to recently, so phones, TVs and IoT boards were routinely missing. The bug the
first working version introduced: after an ARP sweep Windows keeps a neighbour
entry for *every* probed address, and the ones that never answered carry a
``00-00-00-00-00-00`` MAC - reporting those invented a device for every unused
IP in the subnet. Both behaviours are locked down here.

Network I/O is not performed by these tests; the protocol parsers and filters
are pure functions and are tested directly.
"""

from __future__ import annotations

import socket
import struct
import threading

import pytest

from cortex_unified.system_tools import oui
from cortex_unified.system_tools.network_discovery import (
    Device,
    DiscoveryResult,
    Interface,
    NetworkDiscovery,
)


# ---------------------------------------------------------------------------
# The phantom-device regression
# ---------------------------------------------------------------------------

class TestUsableHost:
    """TestUsableHost."""
    def test_zero_mac_is_absence_not_presence(self):
        """An all-zero MAC means the ARP probe got no reply."""
        assert NetworkDiscovery._usable_host("192.168.1.50", "00:00:00:00:00:00") is False

    def test_broadcast_mac_rejected(self):
        """test_broadcast_mac_rejected."""
        assert NetworkDiscovery._usable_host("192.168.1.50", "ff:ff:ff:ff:ff:ff") is False

    def test_multicast_mac_rejected(self):
        """test_multicast_mac_rejected."""
        assert NetworkDiscovery._usable_host("224.0.0.22", "01:00:5e:00:00:16") is False

    def test_broadcast_ip_rejected(self):
        """test_broadcast_ip_rejected."""
        assert NetworkDiscovery._usable_host("192.168.1.255", "aa:bb:cc:dd:ee:ff") is False

    def test_multicast_ip_rejected(self):
        """test_multicast_ip_rejected."""
        assert NetworkDiscovery._usable_host("239.255.255.250", "aa:bb:cc:dd:ee:ff") is False

    def test_real_device_accepted(self):
        """test_real_device_accepted."""
        assert NetworkDiscovery._usable_host("192.168.1.50", "20:51:f5:61:77:60") is True

    def test_missing_mac_rejected(self):
        """test_missing_mac_rejected."""
        assert NetworkDiscovery._usable_host("192.168.1.50", "") is False

    def test_garbage_ip_rejected(self):
        """test_garbage_ip_rejected."""
        assert NetworkDiscovery._usable_host("not-an-ip", "20:51:f5:61:77:60") is False


def test_windows_neighbor_query_excludes_incomplete_states():
    """The PowerShell filter itself must exclude the phantom states.

    Guards the fix at the source: if the state filter is loosened, a sweep of a
    /24 would again report ~254 non-existent devices.
    """
    import inspect
    source = inspect.getsource(NetworkDiscovery._read_neighbors_windows)
    assert "00-00-00-00-00-00" in source
    for state in ("Reachable", "Stale", "Permanent"):
        assert state in source
    # Incomplete/Unreachable must NOT be in the allow-list.
    allow_list = source.split("-in", 1)[1] if "-in" in source else source
    assert "'Incomplete'" not in allow_list
    assert "'Unreachable'" not in allow_list


# ---------------------------------------------------------------------------
# MAC identity: vendor vs deliberately private
# ---------------------------------------------------------------------------

class TestMacIdentity:
    """Vendor resolution must be authoritative, never a hardcoded guess.

    These tests assert *properties* of the lookup rather than specific vendor
    strings. Asserting "this prefix is TP-Link" is exactly the mistake that put
    43 wrong entries into an earlier hardcoded table; the registry is the only
    thing entitled to decide a name.
    """

    @pytest.mark.skipif(not oui.has_full_registry(),
                        reason="IEEE registry not downloaded on this machine")
    def test_real_assignments_resolve_from_the_registry(self):
        # Espressif is the ESP32/ESP8266 maker - the classic "mystery device".
        """test_real_assignments_resolve_from_the_registry."""
        assert "espressif" in oui.lookup("fc:e8:c0:11:22:33").lower()
        # A Raspberry Pi Foundation block.
        assert oui.lookup("b8:27:eb:00:00:01") != ""

    def test_lookup_never_invents_a_vendor(self):
        """Unassigned/locally-administered addresses must return empty."""
        assert oui.lookup("aa:aa:aa:aa:aa:aa") == ""
        assert oui.lookup("not-a-mac") == ""
        assert oui.lookup("") == ""

    def test_longer_assignments_win_over_the_containing_block(self):
        """MA-S/MA-M blocks are more specific than the 24-bit OUI they sit in."""
        oui.ensure_registry_loaded()
        oui._OUI["11:22:33"] = "Broad Block Owner"
        oui._LONG_ASSIGNMENTS["1122334"] = "Specific Sub-Block Owner"
        try:
            assert oui.lookup("11:22:33:44:55:66") == "Specific Sub-Block Owner"
            assert oui.lookup("11:22:33:04:55:66") == "Broad Block Owner"
        finally:
            oui._OUI.pop("11:22:33", None)
            oui._LONG_ASSIGNMENTS.pop("1122334", None)

    def test_ieee_placeholder_org_is_not_recorded_as_a_vendor(self, tmp_path):
        """'IEEE Registration Authority' names no vendor - recording it lies."""
        csv_file = tmp_path / "reg.csv"
        csv_file.write_text(
            "Registry,Assignment,Organization Name,Organization Address\n"
            "MA-L,ABCDEF,IEEE Registration Authority,x\n"
            "MA-L,ABCDE0,Real Vendor Inc.,y\n",
            encoding="utf-8")
        oui.load_ieee_registry(csv_file)
        assert oui.lookup("ab:cd:ef:00:00:01") == ""
        assert oui.lookup("ab:cd:e0:00:00:01") == "Real Vendor Inc."

    def test_shorten_is_cosmetic_only(self):
        """test_shorten_is_cosmetic_only."""
        assert oui.shorten("Espressif Inc.") == "Espressif"
        assert oui.shorten("TP-LINK TECHNOLOGIES CO.,LTD.") == "TP-LINK"
        assert oui.shorten("") == ""
        # Never returns empty for a real input.
        assert oui.shorten("Ltd") == "Ltd"

    def test_randomized_mac_detected(self):
        # Locally-administered bit (0x02) set -> a privacy address.
        """test_randomized_mac_detected."""
        for mac in ("36:fe:fa:8b:25:6b", "96:e7:e1:46:92:5f", "b2:04:d2:38:db:00"):
            assert oui.is_randomized(mac), mac

    def test_real_vendor_mac_is_not_randomized(self):
        """test_real_vendor_mac_is_not_randomized."""
        for mac in ("20:51:f5:61:77:60", "84:28:d6:14:54:e3", "24:0a:c4:11:22:33"):
            assert not oui.is_randomized(mac), mac

    def test_multicast_is_not_treated_as_randomized(self):
        """test_multicast_is_not_treated_as_randomized."""
        assert oui.is_multicast("01:00:5e:00:00:16")
        assert not oui.is_randomized("01:00:5e:00:00:16")

    def test_private_address_explained_not_called_unknown(self):
        """The honest answer to 'why is my phone unnamed?'."""
        described = oui.describe_vendor("36:fe:fa:8b:25:6b")
        assert "private" in described.lower()
        assert "randomiz" in described.lower()

    def test_missing_registry_is_distinguished_from_unknown_vendor(self):
        """'We couldn't look it up' must not masquerade as 'no such vendor'."""
        described = oui.describe_vendor("10:11:22:33:44:55")
        if oui.has_full_registry():
            # Either a real name, or genuinely unassigned -> empty.
            assert "database not downloaded" not in described
        else:
            assert "database not downloaded" in described

    def test_normalize_handles_formats(self):
        """test_normalize_handles_formats."""
        assert oui.normalize("84-28-D6-14-54-E3") == "84:28:d6:14:54:e3"
        assert oui.normalize("8428.d614.54e3") == ""      # not 6 groups
        assert oui.normalize("garbage") == ""
        assert oui.normalize("") == ""


# ---------------------------------------------------------------------------
# Device naming and classification
# ---------------------------------------------------------------------------

class TestDeviceLabelling:
    """TestDeviceLabelling."""
    def test_friendly_name_beats_uuid_hostname(self):
        """Chromecasts use a raw UUID as hostname; the user's own name wins."""
        dev = Device(
            ip="192.168.31.134",
            hostname="fd722296-10f6-0827-0c2e-1684fd064082",
            services={"friendly": "Family Room TV", "model": "JMSB200A"},
        )
        assert dev.label == "Family Room TV"

    def test_model_used_when_no_friendly_name(self):
        """test_model_used_when_no_friendly_name."""
        dev = Device(ip="192.168.31.138", hostname="67334274-6f36-cd6c-16e2-66e0b3178c34",
                     services={"model": "R3G"})
        assert dev.label == "R3G"

    def test_real_hostname_is_used(self):
        """test_real_hostname_is_used."""
        dev = Device(ip="192.168.31.182", hostname="destroyer")
        assert dev.label == "destroyer"

    def test_uuid_detection(self):
        """test_uuid_detection."""
        assert Device._looks_like_uuid("fd722296-10f6-0827-0c2e-1684fd064082")
        assert not Device._looks_like_uuid("destroyer")
        assert not Device._looks_like_uuid("Family Room TV")

    def test_gateway_without_a_name_reads_as_router(self):
        """test_gateway_without_a_name_reads_as_router."""
        dev = Device(ip="192.168.31.1", is_gateway=True)
        assert dev.label == "Router"

    def test_private_address_is_not_used_as_a_name(self):
        """test_private_address_is_not_used_as_a_name."""
        dev = Device(ip="192.168.31.246", mac="36:fe:fa:8b:25:6b",
                     vendor="private address (randomized by the device)")
        # Falling back to the IP is more useful than repeating the caveat.
        assert dev.label == "192.168.31.246"

    def test_label_never_empty(self):
        """test_label_never_empty."""
        assert Device(ip="10.0.0.5").label == "10.0.0.5"


class TestDeviceKind:
    """TestDeviceKind."""
    def test_chromecast_classified_from_service_and_port(self):
        """test_chromecast_classified_from_service_and_port."""
        dev = Device(ip="1.1.1.1", services={"_googlecast._tcp": ""}, open_ports=[8009])
        assert dev.kind == "TV / streaming device"

    def test_esp_board_classified_from_the_registry_vendor_name(self):
        """Classification keys off the authoritative vendor string, so any
        Espressif block - including ones no hardcoded table ever listed -
        is categorised."""
        dev = Device(ip="1.1.1.1", vendor="Espressif")
        assert "IoT board" in dev.kind
        assert "IoT board" in Device(ip="1.1.1.2", vendor="Espressif Inc.").kind
        assert Device(ip="1.1.1.3", services={"_esphomelib._tcp": ""}).kind.startswith("IoT")

    def test_classified_from_self_reported_model(self):
        """A device's own UPnP/mDNS model text is enough, with no MAC at all."""
        dev = Device(ip="1.1.1.1", services={"model": "Hikvision DS-2CD"})
        assert dev.kind == "Camera"

    def test_unknown_vendor_is_not_guessed_into_a_category(self):
        """test_unknown_vendor_is_not_guessed_into_a_category."""
        dev = Device(ip="1.1.1.1", vendor="Totally Unheard Of Gmbh")
        assert dev.kind == "Unknown"

    def test_printer_classified(self):
        """test_printer_classified."""
        assert Device(ip="1.1.1.1", open_ports=[9100]).kind == "Printer"
        assert Device(ip="1.1.1.2", services={"_ipp._tcp": ""}).kind == "Printer"

    def test_randomized_mac_reads_as_phone_or_laptop(self):
        """test_randomized_mac_reads_as_phone_or_laptop."""
        dev = Device(ip="1.1.1.1", mac="36:fe:fa:8b:25:6b")
        assert "private address" in dev.kind

    def test_gateway_and_self_win(self):
        """test_gateway_and_self_win."""
        assert Device(ip="1.1.1.1", is_gateway=True, open_ports=[80]).kind == "Router / gateway"
        assert Device(ip="1.1.1.2", is_self=True, open_ports=[445]).kind == "This PC"

    def test_unknown_stays_unknown(self):
        """test_unknown_stays_unknown."""
        assert Device(ip="1.1.1.1", mac="20:51:f5:00:00:01").kind == "Unknown"


class TestEvidence:
    """TestEvidence."""
    def test_evidence_lists_every_source(self):
        """test_evidence_lists_every_source."""
        dev = Device(ip="1.1.1.1", sources={"neighbor", "mdns", "ssdp"})
        text = dev.evidence
        assert "ARP" in text and "mDNS" in text and "UPnP" in text

    def test_evidence_never_empty(self):
        """test_evidence_never_empty."""
        assert Device(ip="1.1.1.1").evidence


class TestMerge:
    """TestMerge."""
    def test_observations_combine_without_losing_data(self):
        """test_observations_combine_without_losing_data."""
        first = Device(ip="1.1.1.1", mac="20:51:f5:61:77:60", sources={"neighbor"},
                       open_ports=[8009])
        second = Device(ip="1.1.1.1", hostname="tv", sources={"mdns"},
                        services={"friendly": "Family Room TV"}, open_ports=[8008])
        first.merge(second)
        assert first.mac == "20:51:f5:61:77:60"
        assert first.hostname == "tv"
        assert first.sources == {"neighbor", "mdns"}
        assert sorted(first.open_ports) == [8008, 8009]
        assert first.services["friendly"] == "Family Room TV"

    def test_merge_does_not_overwrite_existing_values(self):
        """test_merge_does_not_overwrite_existing_values."""
        first = Device(ip="1.1.1.1", hostname="real-name")
        first.merge(Device(ip="1.1.1.1", hostname="other"))
        assert first.hostname == "real-name"


# ---------------------------------------------------------------------------
# DNS / mDNS parsing
# ---------------------------------------------------------------------------

class TestDnsParsing:
    """TestDnsParsing."""
    def test_query_is_well_formed(self):
        """test_query_is_well_formed."""
        query = NetworkDiscovery._build_dns_query("_googlecast._tcp.local")
        # Header is 12 bytes, one question, PTR type, IN class.
        qdcount = struct.unpack(">H", query[4:6])[0]
        assert qdcount == 1
        assert query.endswith(struct.pack(">HH", 12, 1))
        assert b"_googlecast" in query

    def test_parses_an_a_record(self):
        # name: esp32.local -> A 192.168.31.77
        """test_parses_an_a_record."""
        payload = (
            struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0)
            + b"\x05esp32\x05local\x00"
            + struct.pack(">HHIH", 1, 1, 120, 4)
            + socket.inet_aton("192.168.31.77")
        )
        records = NetworkDiscovery._parse_dns_records(payload)
        assert ("esp32.local", 1, "192.168.31.77") in records

    def test_handles_name_compression(self):
        """mDNS responders rely on compression pointers; without support for
        them most real packets are unreadable."""
        header = struct.pack(">HHHHHH", 0, 0x8400, 0, 2, 0, 0)
        name = b"\x05local\x00"
        first = name + struct.pack(">HHIH", 1, 1, 120, 4) + socket.inet_aton("10.0.0.1")
        # Second record's name is a pointer back to offset 12 (the first name).
        pointer = struct.pack(">H", 0xC000 | 12)
        second = pointer + struct.pack(">HHIH", 1, 1, 120, 4) + socket.inet_aton("10.0.0.2")
        records = NetworkDiscovery._parse_dns_records(header + first + second)
        assert len(records) == 2
        assert records[1][0] == "local"
        assert records[1][2] == "10.0.0.2"

    def test_malformed_packet_does_not_raise(self):
        """test_malformed_packet_does_not_raise."""
        assert NetworkDiscovery._parse_dns_records(b"") == []
        assert NetworkDiscovery._parse_dns_records(b"\x00\x01\x02") == []
        # Truncated mid-record.
        assert isinstance(
            NetworkDiscovery._parse_dns_records(
                struct.pack(">HHHHHH", 0, 0x8400, 0, 5, 0, 0) + b"\x05esp32"),
            list)

    def test_compression_loop_is_bounded(self):
        """A pointer cycle must terminate instead of hanging the scan."""
        # A name at offset 12 that points at itself.
        payload = struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0) + struct.pack(">H", 0xC000 | 12)
        name, _ = NetworkDiscovery._read_name(payload, 12)
        assert isinstance(name, str)

    def test_txt_record_decoded(self):
        """test_txt_record_decoded."""
        txt = b"\x0bfn=Bedroom\x0bmd=Chromecast"
        payload = (
            struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0)
            + b"\x04test\x05local\x00"
            + struct.pack(">HHIH", 16, 1, 120, len(txt))
            + txt
        )
        records = NetworkDiscovery._parse_dns_records(payload)
        assert any("fn=Bedroom" in str(v) for _, t, v in records if t == 16)


class TestServiceSplitting:
    """TestServiceSplitting."""
    def test_splits_instance_and_type(self):
        """test_splits_instance_and_type."""
        service, instance = NetworkDiscovery._split_service_instance(
            "Family Room._googlecast._tcp.local")
        assert service == "_googlecast._tcp"
        assert instance == "Family Room"

    def test_bare_service_type(self):
        """test_bare_service_type."""
        service, instance = NetworkDiscovery._split_service_instance("_ipp._tcp.local")
        assert service == "_ipp._tcp"
        assert instance == ""

    def test_non_service_name(self):
        """test_non_service_name."""
        assert NetworkDiscovery._split_service_instance("host.local") == ("", "")
        assert NetworkDiscovery._split_service_instance("") == ("", "")


def test_ssdp_headers_parsed_case_insensitively():
    """test_ssdp_headers_parsed_case_insensitively."""
    raw = (b"HTTP/1.1 200 OK\r\n"
           b"SERVER: Linux/4.14 UPnP/1.0 Chromecast/1.6\r\n"
           b"ST: urn:dial-multiscreen-org:service:dial:1\r\n\r\n")
    headers = NetworkDiscovery._parse_http_headers(raw)
    assert "Chromecast" in headers["server"]
    assert headers["st"].startswith("urn:dial")


# ---------------------------------------------------------------------------
# Safety: only ever probe our own private subnets
# ---------------------------------------------------------------------------

class TestScanScope:
    """TestScanScope."""
    def test_interface_network_computed(self):
        """test_interface_network_computed."""
        iface = Interface("Wi-Fi", "192.168.31.182", "255.255.255.0")
        assert str(iface.network) == "192.168.31.0/24"

    def test_bad_netmask_is_survivable(self):
        """test_bad_netmask_is_survivable."""
        assert Interface("x", "192.168.1.1", "not-a-mask").network is None

    def test_real_interfaces_are_private_only(self):
        """Whatever this machine has, we must never target public space."""
        import ipaddress
        for iface in NetworkDiscovery.local_interfaces():
            addr = ipaddress.IPv4Address(iface.ip)
            assert addr.is_private
            assert not addr.is_loopback

    def test_oversized_subnet_is_skipped_with_an_explanation(self, monkeypatch):
        """A /8 must not be swept host-by-host; say so rather than hang."""
        disco = NetworkDiscovery()
        monkeypatch.setattr(
            NetworkDiscovery, "local_interfaces",
            staticmethod(lambda: [Interface("huge", "10.0.0.5", "255.0.0.0")]))
        monkeypatch.setattr(disco, "default_gateways", lambda: set())
        monkeypatch.setattr(disco, "_read_neighbors", lambda: [])
        monkeypatch.setattr(disco, "_discover_mdns", lambda c: [])
        monkeypatch.setattr(disco, "_discover_ssdp", lambda c: [])
        monkeypatch.setattr(disco, "_discover_wsd", lambda c: [])
        monkeypatch.setattr(disco, "_resolve_names", lambda d, c: None)
        monkeypatch.setattr(disco, "_fingerprint", lambda d, c: None)

        def _no_sweep(*_a, **_k):
            """_no_sweep."""
            raise AssertionError("a /8 must never be swept host-by-host")

        monkeypatch.setattr(disco, "_arp_sweep", _no_sweep)

        result = disco.scan()
        assert result.networks == []
        assert any("too large" in note for note in result.notes)

    def test_manual_scope_can_only_narrow_active_interface(self, monkeypatch):
        """test_manual_scope_can_only_narrow_active_interface."""
        disco = NetworkDiscovery()
        monkeypatch.setattr(
            NetworkDiscovery, "local_interfaces",
            staticmethod(lambda: [
                Interface("lan", "192.168.50.20", "255.255.255.0")]))
        monkeypatch.setattr(disco, "default_gateways", lambda: set())
        monkeypatch.setattr(disco, "_read_neighbors", lambda: [
            Device("192.168.50.10", sources={"neighbor"}),
            Device("192.168.50.200", sources={"neighbor"}),
        ])
        monkeypatch.setattr(disco, "_discover_mdns", lambda _cancel: [])
        monkeypatch.setattr(disco, "_discover_ssdp", lambda _cancel: [])
        monkeypatch.setattr(disco, "_discover_wsd", lambda _cancel: [])
        monkeypatch.setattr(disco, "_resolve_names", lambda *_args: None)
        result = disco.scan(
            deep=False, requested_networks=["192.168.50.0/25"])
        assert result.networks == ["192.168.50.0/25"]
        assert "192.168.50.10" in {item.ip for item in result.devices}
        assert "192.168.50.200" not in {item.ip for item in result.devices}

        with pytest.raises(ValueError, match="active local interface"):
            disco.scan(
                deep=False, requested_networks=["192.168.51.0/24"])

    def test_no_interfaces_reports_clearly(self, monkeypatch):
        """test_no_interfaces_reports_clearly."""
        disco = NetworkDiscovery()
        monkeypatch.setattr(NetworkDiscovery, "local_interfaces",
                            staticmethod(lambda: []))
        result = disco.scan()
        assert result.devices == []
        assert any("nothing to scan" in n.lower() for n in result.notes)


class TestCancellation:
    """TestCancellation."""
    def test_already_cancelled_scan_does_almost_nothing(self, monkeypatch):
        """test_already_cancelled_scan_does_almost_nothing."""
        disco = NetworkDiscovery()
        event = threading.Event()
        event.set()
        monkeypatch.setattr(
            NetworkDiscovery, "local_interfaces",
            staticmethod(lambda: [Interface("eth", "192.168.31.182", "255.255.255.0")]))
        monkeypatch.setattr(disco, "default_gateways", lambda: set())
        monkeypatch.setattr(disco, "_read_neighbors", lambda: [])

        def _boom(*_a, **_k):
            """_boom."""
            raise AssertionError("no probing after cancellation")

        monkeypatch.setattr(disco, "_arp_sweep", _boom)
        monkeypatch.setattr(disco, "_discover_mdns", _boom)

        result = disco.scan(cancel_event=event)
        assert result.cancelled is True


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

class TestNotes:
    """TestNotes."""
    def test_randomized_macs_are_explained(self):
        """test_randomized_macs_are_explained."""
        devices = [Device(ip="1.1.1.1", mac="36:fe:fa:8b:25:6b")]
        notes = NetworkDiscovery._build_notes(devices, [], set())
        assert any("randomized" in n for n in notes)

    def test_client_isolation_suggested_when_only_router_answers(self):
        """test_client_isolation_suggested_when_only_router_answers."""
        import ipaddress
        devices = [Device(ip="192.168.1.1", mac="84:28:d6:14:54:e3", is_gateway=True)]
        notes = NetworkDiscovery._build_notes(
            devices, [ipaddress.IPv4Network("192.168.1.0/24")], {"192.168.1.1"})
        assert any("isolation" in n for n in notes)

    def test_no_spurious_notes_for_a_healthy_scan(self):
        """test_no_spurious_notes_for_a_healthy_scan."""
        import ipaddress
        # All globally-assigned MACs, so no privacy-address note is expected.
        devices = [
            Device(ip="192.168.1.1", mac="84:28:d6:14:54:e3", is_gateway=True),
            Device(ip="192.168.1.5", mac="20:51:f5:61:77:60"),
            Device(ip="192.168.1.6", mac="24:0a:c4:11:22:33"),
        ]
        notes = NetworkDiscovery._build_notes(
            devices, [ipaddress.IPv4Network("192.168.1.0/24")], {"192.168.1.1"})
        assert notes == []


def test_result_serializes_to_json():
    """test_result_serializes_to_json."""
    import json
    result = DiscoveryResult(
        devices=[Device(ip="192.168.1.5", mac="24:0a:c4:11:22:33",
                        sources={"neighbor"})],
        networks=["192.168.1.0/24"],
        duration_seconds=3.14159,
    )
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["device_count"] == 1
    assert payload["duration_seconds"] == 3.14
    device = payload["devices"][0]
    assert "Espressif" in device["vendor"] or device["vendor"] == ""
    assert device["randomized_mac"] is False


def test_ip_sort_key_orders_numerically():
    """test_ip_sort_key_orders_numerically."""
    ips = ["192.168.1.100", "192.168.1.2", "192.168.1.20"]
    assert sorted(ips, key=NetworkDiscovery._ip_sort_key) == [
        "192.168.1.2", "192.168.1.20", "192.168.1.100"]


@pytest.mark.parametrize("bad", ["", "not-an-ip", "999.1.1.1"])
def test_ip_validation_rejects_garbage(bad):
    """test_ip_validation_rejects_garbage."""
    assert NetworkDiscovery._is_ipv4(bad) is False
