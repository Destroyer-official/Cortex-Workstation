"""Safety-guard tests for defensive private-LAN scanning (no live network).

History
-------
This module previously tested a superseded scanner API (``AuditResult``,
``ScanConfig``, ``ports_for_mode``, ``analyze_services`` as a public entry
point). That API was replaced by ``ScanProfile`` / ``ports_for_profile`` /
``audit_devices`` during the network-audit rework, so the old tests could not
even be imported. Their behavioural coverage now lives in
``tests/test_network_audit.py``, with one exception: nothing else covered
``validate_private_target``.

That guard is safety-critical - it is the last check before Cortex opens
sockets, and it must refuse anything that is not the user's own private LAN.
It is therefore kept here, rewritten against the current API.
"""

from __future__ import annotations

import ipaddress

import pytest

from cortex_unified.system_tools.network_service_scanner import (
    validate_private_target,
)


@pytest.mark.parametrize("target", [
    "10.0.0.1",
    "10.255.255.254",
    "172.16.0.1",
    "172.31.255.254",
    "192.168.0.1",
    "192.168.50.9",
])
def test_guard_accepts_rfc1918_lan_addresses(target: str) -> None:
    """The three RFC 1918 private ranges are the only allowed scan scope."""
    assert validate_private_target(target) == target


@pytest.mark.parametrize("target", [
    "8.8.8.8",              # public internet - never scanned automatically
    "1.1.1.1",              # public internet
    "192.0.2.1",            # TEST-NET-1 documentation range
    "127.0.0.1",            # loopback
    "0.0.0.0",              # unspecified
    "224.0.0.1",            # multicast
    "255.255.255.255",      # broadcast
    "169.254.12.4",         # link-local: outside the three private ranges
    "172.15.0.1",           # just below the 172.16/12 block
    "172.32.0.1",           # just above the 172.16/12 block
    "11.0.0.1",             # just above the 10/8 block
    "192.169.0.1",          # just above the 192.168/16 block
])
def test_guard_rejects_every_out_of_scope_address(target: str) -> None:
    """Public, special-use and near-miss addresses must all be refused."""
    with pytest.raises(ValueError, match="not a usable private IPv4 address"):
        validate_private_target(target)


@pytest.mark.parametrize("target", [
    "example.test",         # hostnames are not resolved by the guard
    "::1",                  # IPv6 loopback
    "fd00::1",              # IPv6 unique-local
    "not-an-ip",
    "",
    "192.168.1",            # truncated
    "192.168.1.256",        # octet out of range
    "192.168.1.1/24",       # CIDR, not a host address
    " 192.168.1.1 ",        # unstripped input must not sneak through
])
def test_guard_rejects_malformed_and_non_ipv4_input(target: str) -> None:
    """Anything that is not a bare, valid IPv4 host address is refused."""
    with pytest.raises(ValueError):
        validate_private_target(target)


def test_guard_rejects_leading_zero_octets() -> None:
    """Ambiguous octal-looking octets must be refused, not reinterpreted.

    ``ipaddress`` rejects leading zeros (CPython tightened this in 3.9.5)
    because ``0177.0.0.1`` can be read as either decimal or octal, a classic
    access-control bypass vector. The guard inherits that strictness, which is
    the behaviour we want: an ambiguous target is never silently "fixed".
    """
    with pytest.raises(ValueError):
        validate_private_target("192.168.001.009")


def test_guard_returns_address_usable_for_socket_operations() -> None:
    """The returned value is what callers feed straight into sockets."""
    result = validate_private_target("192.168.1.9")
    assert result == "192.168.1.9"
    parsed = ipaddress.IPv4Address(result)
    assert parsed.is_private and not parsed.is_loopback
