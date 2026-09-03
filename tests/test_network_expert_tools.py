"""Offline tests for the optional Nmap adapter and strict Wake-on-LAN API."""

from __future__ import annotations

import subprocess
import threading

import pytest

from cortex_unified.core import proc
from cortex_unified.system_tools import nmap_adapter
from cortex_unified.system_tools import wake_on_lan

SCOPES = ("192.168.50.0/24",)
NMAP_XML = b"""<?xml version='1.0'?>
<nmaprun><host><status state='up'/><address addr='192.168.50.10'
addrtype='ipv4'/><ports><port protocol='tcp' portid='443'>
<state state='open' reason='syn-ack'/><service name='https' product='Caddy'
version='2.7' tunnel='ssl' conf='10'/></port></ports><os>
<osmatch name='Linux 5.x' accuracy='96'/></os></host></nmaprun>"""


def _available(monkeypatch: pytest.MonkeyPatch) -> nmap_adapter.NmapAdapter:
    monkeypatch.setattr(
        nmap_adapter.shutil, "which", lambda _name: "C:/nmap.exe"
    )
    return nmap_adapter.NmapAdapter()


def test_nmap_status_does_not_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = _available(monkeypatch)
    monkeypatch.setattr(
        nmap_adapter.proc, "run",
        lambda *_args, **_kwargs: pytest.fail("status executed Nmap"),
    )
    status = adapter.status()
    assert status.available is True
    assert status.executable == "C:/nmap.exe"


def test_nmap_missing_executable_has_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        nmap_adapter.shutil, "which", lambda _name: None
    )
    adapter = nmap_adapter.NmapAdapter()
    assert adapter.available is False
    with pytest.raises(
        nmap_adapter.NmapUnavailableError, match="not available"
    ):
        adapter.scan(["192.168.50.10"], SCOPES, [443])


def test_nmap_builds_safe_deterministic_argument_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _available(monkeypatch)
    arguments, _scopes = adapter.build_arguments(
        ["192.168.50.10", "192.168.50.2"], SCOPES, [443, 80, 443]
    )
    assert arguments == [
        "C:/nmap.exe", "-n", "-Pn", "-sT", "-sV", "--version-light",
        "--max-retries", "2", "--host-timeout", "30s", "-p", "80,443",
        "-oX", "-", "192.168.50.2", "192.168.50.10",
    ]
    assert "--script" not in arguments


@pytest.mark.parametrize("target", [
    "8.8.8.8", "example.test", "192.168.51.1", "127.0.0.1", "-sC",
])
def test_nmap_rejects_every_unauthorized_target(
    monkeypatch: pytest.MonkeyPatch, target: str,
) -> None:
    adapter = _available(monkeypatch)
    with pytest.raises(nmap_adapter.NmapAuthorizationError):
        adapter.build_arguments(["192.168.50.10", target], SCOPES, [80])


def test_nmap_expert_modes_require_windows_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _available(monkeypatch)
    monkeypatch.setattr(nmap_adapter, "_is_windows_admin", lambda: False)
    with pytest.raises(nmap_adapter.NmapPrivilegeError, match="administrator"):
        adapter.build_arguments(["192.168.50.10"], SCOPES, [80], "syn")
    monkeypatch.setattr(nmap_adapter, "_is_windows_admin", lambda: True)
    arguments, _ = adapter.build_arguments(
        ["192.168.50.10"], SCOPES, [80], ("syn", "version", "os")
    )
    assert "-sS" in arguments and "-O" in arguments and "-sT" not in arguments


def test_nmap_scan_uses_proc_and_parses_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _available(monkeypatch)
    calls = []

    def fake_run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return subprocess.CompletedProcess(arguments, 0, NMAP_XML, b"")

    monkeypatch.setattr(nmap_adapter.proc, "run", fake_run)
    cancel = threading.Event()
    result = adapter.scan(
        ["192.168.50.10"], SCOPES, [443], cancel_event=cancel
    )
    assert calls[0][1]["cancel_event"] is cancel
    assert len(result) == 1
    observation = result[0]
    assert observation.source == "nmap"
    assert (observation.ip, observation.port, observation.name) == (
        "192.168.50.10", 443, "https",
    )
    assert (observation.product, observation.version) == ("Caddy", "2.7")
    assert observation.metadata["os_matches"] == [
        {"name": "Linux 5.x", "accuracy": "96"}
    ]


def test_nmap_cancellation_before_launch_skips_proc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _available(monkeypatch)
    monkeypatch.setattr(
        nmap_adapter.proc, "run",
        lambda *_args, **_kwargs: pytest.fail("cancelled scan launched Nmap"),
    )
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(proc.ProcessCancelled):
        adapter.scan(
            ["192.168.50.10"], SCOPES, [443], cancel_event=cancel
        )


@pytest.mark.parametrize("declaration", [b"<!DOCTYPE x>", b"<!ENTITY x 'y'>"])
def test_nmap_xml_rejects_dtd_and_entities(declaration: bytes) -> None:
    payload = b"<?xml version='1.0'?>" + declaration + b"<nmaprun/>"
    with pytest.raises(nmap_adapter.NmapOutputError, match="forbidden"):
        nmap_adapter.parse_nmap_xml(payload, SCOPES)


def test_nmap_xml_enforces_depth_limit() -> None:
    payload = b"<nmaprun>" + b"<x>" * 40 + b"</x>" * 40 + b"</nmaprun>"
    with pytest.raises(nmap_adapter.NmapOutputError, match="depth"):
        nmap_adapter.parse_nmap_xml(payload, SCOPES)


def test_nmap_xml_rejects_public_result() -> None:
    payload = NMAP_XML.replace(b"192.168.50.10", b"8.8.8.8")
    with pytest.raises(nmap_adapter.NmapOutputError, match="unauthorized"):
        nmap_adapter.parse_nmap_xml(payload, SCOPES)


@pytest.mark.parametrize("mac", [
    "00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff", "01:11:22:33:44:55",
    "02:11:22:33:44:55", "00-11-22-33-44-55", "001122334455",
])
def test_wol_rejects_invalid_or_non_unicast_mac(mac: str) -> None:
    with pytest.raises(wake_on_lan.InvalidMacAddress):
        wake_on_lan.validate_mac(mac)


def test_wol_builds_standard_magic_packet() -> None:
    raw = bytes.fromhex("001122334455")
    packet = wake_on_lan.build_magic_packet("00:11:22:33:44:55")
    assert packet == b"\xff" * 6 + raw * 16
    assert len(packet) == 102


@pytest.mark.parametrize("broadcast, networks", [
    ("255.255.255.255", SCOPES),
    ("192.168.51.255", SCOPES),
    ("192.168.50.1", SCOPES),
    ("8.8.8.8", SCOPES),
    ("192.0.0.255", ("192.0.0.0/24",)),
])
def test_wol_rejects_broadcast_outside_active_private_lan(
    broadcast: str, networks: tuple[str, ...],
) -> None:
    with pytest.raises(wake_on_lan.InvalidBroadcastAddress):
        wake_on_lan.validate_broadcast(broadcast, networks)


class _Socket:
    def __init__(self) -> None:
        self.timeout = None
        self.options = []
        self.sent = []
        self.closed = False

    def settimeout(self, value: float) -> None:
        self.timeout = value

    def setsockopt(self, *value) -> None:
        self.options.append(value)

    def sendto(self, payload: bytes, destination: tuple[str, int]) -> int:
        self.sent.append((payload, destination))
        return len(payload)

    def close(self) -> None:
        self.closed = True


def test_wol_sends_one_bounded_udp_broadcast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _Socket()
    monkeypatch.setattr(wake_on_lan.socket, "socket", lambda *_args: fake)
    sent = wake_on_lan.send_magic_packet(
        "00:11:22:33:44:55", "192.168.50.255", SCOPES,
        port=9, timeout=99,
    )
    assert sent == 102
    assert fake.timeout == 5.0
    assert fake.options == [
        (wake_on_lan.socket.SOL_SOCKET, wake_on_lan.socket.SO_BROADCAST, 1)
    ]
    assert fake.sent[0][1] == ("192.168.50.255", 9)
    assert fake.closed is True


def test_wol_rejects_nonpositive_or_nonfinite_timeout() -> None:
    for timeout in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite positive"):
            wake_on_lan.send_magic_packet(
                "00:11:22:33:44:55", "192.168.50.255", SCOPES,
                timeout=timeout,
            )


def test_wol_wraps_socket_error_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _Socket()

    def fail_send(_payload, _destination):
        raise OSError("synthetic failure")

    fake.sendto = fail_send
    monkeypatch.setattr(wake_on_lan.socket, "socket", lambda *_args: fake)
    with pytest.raises(wake_on_lan.WakeOnLanSendError, match="synthetic"):
        wake_on_lan.send_magic_packet(
            "00:11:22:33:44:55", "192.168.50.255", SCOPES
        )
    assert fake.closed is True
