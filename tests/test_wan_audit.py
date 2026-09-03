"""Synthetic tests for the local-only, read-only WAN auditor."""

from __future__ import annotations

import ipaddress
import json
import threading

import pytest

from cortex_unified.system_tools.wan_audit import (
    InterfaceStatus,
    PortMapping,
    WanAuditor,
    _is_trusted_url,
    _safe_xml,
    classify_public_ip,
)


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("8.8.8.8", "globally_routable"),
        ("192.168.1.2", "rfc1918"),
        ("172.31.2.3", "rfc1918"),
        ("10.0.0.1", "rfc1918"),
        ("100.64.0.1", "cgnat"),
        ("100.127.255.254", "cgnat"),
        ("127.0.0.1", "invalid_or_unknown"),
        ("2001:4860:4860::8888", "invalid_or_unknown"),
        ("garbage", "invalid_or_unknown"),
        ("", "invalid_or_unknown"),
    ],
)
def test_public_ip_classification(address, expected):
    assert classify_public_ip(address) == expected


def test_ssrf_guard_requires_literal_private_host_on_local_network():
    networks = [ipaddress.IPv4Network("192.168.50.0/24")]
    assert _is_trusted_url("http://192.168.50.1:1900/root.xml", networks)
    assert _is_trusted_url("https://192.168.50.2/igd", networks)
    rejected = [
        "http://192.168.51.1/root.xml",
        "http://8.8.8.8/root.xml",
        "http://localhost/root.xml",
        "http://router.local/root.xml",
        "file:///etc/passwd",
        "http://user@192.168.50.1/root.xml",
        "http://192.168.50.1/root.xml#fragment",
        "http://[::1]/root.xml",
    ]
    assert all(not _is_trusted_url(url, networks) for url in rejected)


def test_xml_rejects_entities_and_excessive_depth():
    with pytest.raises(ValueError, match="DTD"):
        _safe_xml(b'<!DOCTYPE x [<!ENTITY y "z">]><x>&y;</x>')
    deep = ("<x>" * 30 + "ok" + "</x>" * 30).encode()
    with pytest.raises(ValueError, match="complexity"):
        _safe_xml(deep)


def test_igd_control_url_is_resolved_and_kept_local(monkeypatch):
    description = b"""<root xmlns="urn:schemas-upnp-org:device-1-0">
      <device><serviceList><service>
        <serviceType>urn:schemas-upnp-org:service:WANIPConnection:1</serviceType>
        <controlURL>/upnp/control/wanip</controlURL>
      </service></serviceList></device></root>"""
    auditor = WanAuditor()
    monkeypatch.setattr(
        auditor, "_http_request", lambda *args, **kwargs: (200, {}, description))
    service, control = auditor._load_igd(
        "http://192.168.50.1:5000/root.xml",
        [ipaddress.IPv4Network("192.168.50.0/24")],
    )
    assert service.endswith("WANIPConnection:1")
    assert control == "http://192.168.50.1:5000/upnp/control/wanip"


def test_igd_rejects_control_url_to_other_network(monkeypatch):
    description = b"""<root><service>
      <serviceType>urn:schemas-upnp-org:service:WANIPConnection:1</serviceType>
      <controlURL>http://10.0.0.1/admin</controlURL>
      </service></root>"""
    auditor = WanAuditor()
    monkeypatch.setattr(
        auditor, "_http_request", lambda *args, **kwargs: (200, {}, description))
    with pytest.raises(ValueError, match="control URL"):
        auditor._load_igd(
            "http://192.168.50.1/root.xml",
            [ipaddress.IPv4Network("192.168.50.0/24")],
        )


def _soap_response(action: str, content: str) -> bytes:
    return (
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<s:Body><u:{action} xmlns:u=\"urn:test\">{content}"
        f"</u:{action}></s:Body></s:Envelope>"
    ).encode()


def test_soap_allowlist_and_mapping_parser(monkeypatch):
    auditor = WanAuditor()
    payload = _soap_response(
        "GetGenericPortMappingEntryResponse",
        "<NewRemoteHost></NewRemoteHost><NewExternalPort>8443</NewExternalPort>"
        "<NewProtocol>TCP</NewProtocol><NewInternalPort>443</NewInternalPort>"
        "<NewInternalClient>192.168.50.10</NewInternalClient>"
        "<NewEnabled>1</NewEnabled><NewPortMappingDescription>HTTPS</NewPortMappingDescription>"
        "<NewLeaseDuration>3600</NewLeaseDuration>",
    )
    monkeypatch.setattr(
        auditor, "_http_request", lambda *args, **kwargs: (200, {}, payload))
    root = auditor._soap(
        "http://192.168.50.1/control", "urn:test",
        "GetGenericPortMappingEntry", {"NewPortMappingIndex": "0"})
    mapping = auditor._mapping_from_xml(0, root)
    assert mapping == PortMapping(
        0, "", 8443, "TCP", 443, "192.168.50.10", True, "HTTPS", 3600)
    with pytest.raises(ValueError, match="unsupported"):
        auditor._soap("http://192.168.50.1/control", "urn:test", "AddPortMapping")


class SyntheticAuditor(WanAuditor):
    @staticmethod
    def local_interfaces():
        return [InterfaceStatus("test", "192.168.50.20", "255.255.255.0", "192.168.50.0/24")]

    @staticmethod
    def default_gateway():
        return "192.168.50.1"

    @staticmethod
    def dns_servers():
        return ["192.168.50.1"]

    def discover_locations(self, networks, cancel_event=None):
        return ["http://192.168.50.1/root.xml"]

    def _load_igd(self, location, networks):
        return "urn:schemas-upnp-org:service:WANIPConnection:1", "http://192.168.50.1/control"

    def _soap(self, url, service_type, action, arguments=None):
        if action == "GetExternalIPAddress":
            return _safe_xml(_soap_response(
                "GetExternalIPAddressResponse",
                "<NewExternalIPAddress>100.64.2.3</NewExternalIPAddress>"))
        raise ValueError("synthetic end")


def test_audit_is_json_safe_and_contains_local_context():
    status = SyntheticAuditor(max_mappings=2).audit(include_upnp=True)
    payload = json.loads(json.dumps(status.to_dict()))
    assert payload["external_ip"] == "100.64.2.3"
    assert payload["public_ip_classification"] == "cgnat"
    assert payload["gateway"] == "192.168.50.1"
    assert payload["dns_servers"] == ["192.168.50.1"]
    assert payload["igd_found"] is True


def test_pre_cancelled_audit_does_not_discover(monkeypatch):
    event = threading.Event()
    event.set()
    auditor = SyntheticAuditor()
    monkeypatch.setattr(
        auditor, "discover_locations",
        lambda *args, **kwargs: pytest.fail("discovery must not run"),
    )
    assert auditor.audit(cancel_event=event).cancelled is True
