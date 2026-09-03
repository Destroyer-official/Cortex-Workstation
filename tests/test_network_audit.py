"""Focused synthetic tests for the private-LAN audit foundation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from cortex_unified.system_tools import network_service_scanner as scanner_module
from cortex_unified.system_tools.device_fingerprint import fingerprint_device
from cortex_unified.system_tools.network_inventory import NetworkInventory
from cortex_unified.system_tools.network_security_audit import audit_devices
from cortex_unified.system_tools.network_service_scanner import (
    NetworkServiceScanner,
    ScanProfile,
    ServiceObservation,
    is_authorized_target,
    parse_custom_port_spec,
    parse_network_scope_spec,
    ports_for_profile,
)
from cortex_unified.system_tools.vulnerability_catalog import VulnerabilityCatalog
from cortex_unified.system_tools.wan_audit import (
    WanAuditor,
    _is_trusted_url,
    classify_external_ip,
)


@dataclass
class SyntheticDevice:
    ip: str
    mac: str = ""
    vendor: str = ""
    hostname: str = ""
    services: dict = field(default_factory=dict)
    service_observations: list[ServiceObservation] = field(default_factory=list)
    is_gateway: bool = False


def observation(port=22, name="ssh", **kwargs):
    metadata = kwargs.pop("metadata", {"evidence": ["synthetic response"]})
    return ServiceObservation(
        ip="192.168.50.20",
        port=port,
        transport="tcp",
        name=name,
        source="synthetic",
        metadata=metadata,
        **kwargs,
    )


def test_scope_rejects_public_special_and_out_of_scope_without_sockets(monkeypatch):
    calls = []
    monkeypatch.setattr(
        scanner_module.socket,
        "socket",
        lambda *_args, **_kwargs: calls.append(True),
    )
    scanner = NetworkServiceScanner(timeout=0.05, workers=1)
    result = scanner.scan(
        ["8.8.8.8", "127.0.0.1", "169.254.1.2", "192.168.51.2", "bad"],
        ["192.168.50.0/24"],
        ScanProfile.TARGETED,
    )
    assert result == []
    assert calls == []
    assert is_authorized_target("192.168.50.9", ["192.168.50.0/24"])
    assert not is_authorized_target("192.168.51.9", ["192.168.50.0/24"])
    assert len(tuple(ports_for_profile(ScanProfile.ADVANCED))) >= 50
    deep = ports_for_profile(ScanProfile.DEEP)
    assert (deep.start, deep.stop) == (1, 65536)


def test_private_scope_spec_supports_host_cidr_and_range():
    scopes = parse_network_scope_spec(
        "192.168.50.7,192.168.50.16/30,"
        "192.168.50.20-192.168.50.22")
    assert "192.168.50.7/32" in scopes
    assert "192.168.50.16/30" in scopes
    assert "192.168.50.20/31" in scopes
    assert "192.168.50.22/32" in scopes
    with pytest.raises(ValueError):
        parse_network_scope_spec("192.168.50.20-8.8.8.8")


def test_custom_port_spec_is_bounded_and_deterministic():
    assert parse_custom_port_spec("443,80,8000-8002,443") == (
        80, 443, 8000, 8001, 8002)
    for value in ("0", "65536", "90-80", "80,,443", "x"):
        with pytest.raises(ValueError):
            parse_custom_port_spec(value)


def test_custom_ports_are_validated_before_any_socket(monkeypatch):
    calls = []
    monkeypatch.setattr(
        scanner_module.socket, "socket",
        lambda *_args, **_kwargs: calls.append(True),
    )
    scanner = NetworkServiceScanner(timeout=0.05, workers=1)
    with pytest.raises(ValueError):
        scanner.scan(
            ["192.168.50.9"], ["192.168.50.0/24"],
            ScanProfile.TARGETED, custom_ports=[0],
        )
    assert calls == []


def test_observation_serialization_is_json_safe_and_deterministic():
    item = observation(
        banner="SSH-2.0-Synthetic_1.2",
        product="Synthetic",
        version="1.2",
        metadata={"z": {3, 1}, "a": {"nested": (1, True)}},
        confidence=1.4,
    )
    first = json.dumps(item.to_dict(), sort_keys=True)
    second = json.dumps(item.to_dict(), sort_keys=True)
    assert first == second
    payload = json.loads(first)
    assert payload["metadata"]["z"] == [1, 3]
    assert payload["confidence"] == 1.0


def test_ports_and_banners_never_create_cve_claims():
    device = SyntheticDevice(
        "192.168.50.20",
        service_observations=[
            observation(3389, "rdp"),
            observation(445, "smb"),
            observation(23, "telnet", banner="TELNET ready"),
        ],
    )
    findings = audit_devices([device])
    assert findings
    assert all(item.cve_ids == [] for item in findings)


def test_catalog_exact_product_version_and_no_version_false_positive(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({
        "catalog_version": 1,
        "advisories": [{
            "id": "CVE-2099-0001",
            "product": "Acme Router OS",
            "summary": "Synthetic advisory",
            "severity": "high",
            "source": "synthetic fixture",
            "references": ["https://example.invalid/advisory"],
            "constraints": [
                {"operator": ">=", "version": "3.0"},
                {"operator": "<", "version": "3.5"},
            ],
        }],
    }), encoding="utf-8")
    catalog = VulnerabilityCatalog.load(path)
    assert [item.advisory_id for item in catalog.match("Acme-Router OS", "3.4")] == [
        "CVE-2099-0001"
    ]
    assert catalog.match("Acme Router OS Extra", "3.4") == []
    assert catalog.match("Acme Router OS", "") == []
    matched = audit_devices([
        SyntheticDevice(
            "192.168.50.20",
            service_observations=[observation(
                443, "https", product="Acme Router OS", version="3.4")],
        )
    ], vulnerability_catalog=catalog)
    assert matched[0].cve_ids == ["CVE-2099-0001"]
    assert matched[0].device_ip == "192.168.50.20"
    assert "Potential advisory match" in " ".join(matched[0].evidence)
    json.dumps(catalog.to_dict())


def test_fingerprint_combines_device_and_protocol_evidence():
    service = observation(
        banner="SSH-2.0-OpenWrt_23.05",
        product="OpenWrt",
        version="23.05",
        confidence=0.9,
    )
    device = SyntheticDevice(
        "192.168.50.1",
        vendor="Acme Networks",
        hostname="gateway",
        services={"_http._tcp": "Router Administration"},
        service_observations=[service],
        is_gateway=True,
    )
    fingerprint = fingerprint_device(device)
    assert fingerprint.os_family == "Linux"
    assert fingerprint.device_type == "router / gateway"
    assert 0.5 < fingerprint.confidence <= 1.0
    assert len(fingerprint.evidence) >= 3
    assert fingerprint.product == "OpenWrt"
    json.dumps(fingerprint.to_dict())


@pytest.mark.parametrize(("address", "expected"), [
    ("8.8.8.8", "public"),
    ("100.64.0.1", "cgnat"),
    ("192.168.50.1", "private_upstream"),
    ("127.0.0.1", "unknown"),
    ("not-an-ip", "unknown"),
])
def test_wan_classification(address, expected):
    assert classify_external_ip(address) == expected


def test_wan_url_scope_and_route_only_default(monkeypatch):
    import ipaddress

    networks = [ipaddress.IPv4Network("192.168.50.0/24")]
    assert _is_trusted_url("http://192.168.50.1:1900/root.xml", networks)
    assert not _is_trusted_url("http://8.8.8.8/root.xml", networks)
    assert not _is_trusted_url("http://router.local/root.xml", networks)
    auditor = WanAuditor()
    monkeypatch.setattr(auditor, "local_interfaces", lambda: [])
    monkeypatch.setattr(auditor, "default_gateway", lambda: "192.168.50.1")
    monkeypatch.setattr(auditor, "dns_servers", lambda: ["192.168.50.1"])
    monkeypatch.setattr(
        auditor,
        "discover_locations",
        lambda *_args, **_kwargs: pytest.fail("UPnP must be opt-in"),
    )
    status = auditor.audit(["192.168.50.1"])
    assert status.gateway == "192.168.50.1"
    assert status.igd_found is False
    assert status.to_dict()["connectivity_tested"] is False


def test_inventory_reports_new_address_service_and_gateway_changes(tmp_path):
    inventory = NetworkInventory(tmp_path / "network-inventory.sqlite3")
    first = [
        SyntheticDevice("192.168.50.10", "00:11:22:33:44:55"),
        SyntheticDevice("192.168.50.1", "00:aa:bb:cc:dd:01", is_gateway=True),
    ]
    changes = inventory.update(first)
    assert len(changes.new_devices) == 2

    second = [
        SyntheticDevice(
            "192.168.50.20",
            "00:11:22:33:44:55",
            service_observations=[observation(443, "https")],
        ),
        SyntheticDevice("192.168.50.1", "00:aa:bb:cc:dd:02", is_gateway=True),
    ]
    changes = inventory.update(second)
    assert len(changes.changed_addresses) == 1
    assert changes.changed_addresses[0].previous == "192.168.50.10"
    assert len(changes.new_services) == 1
    assert len(changes.gateway_mac_changes) == 1
    json.dumps(changes.to_dict())
