"""Strict, scope-bound Wake-on-LAN packet construction and transmission."""

from __future__ import annotations

import ipaddress
import math
import re
import socket
from typing import Iterable

_MAGIC_REPEAT = 16
_PACKET_SIZE = 102
_MIN_TIMEOUT = 0.05
_MAX_TIMEOUT = 5.0
_PRIVATE_NETWORKS = tuple(
    ipaddress.IPv4Network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
_MAC_PATTERN = re.compile(
    r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
)


class WakeOnLanError(RuntimeError):
    """Base exception for Wake-on-LAN failures."""


class InvalidMacAddress(ValueError, WakeOnLanError):
    """Raised when a MAC is malformed or unsafe for a unicast device."""


class InvalidBroadcastAddress(ValueError, WakeOnLanError):
    """Raised when a broadcast is outside supplied active LAN scopes."""


class WakeOnLanSendError(WakeOnLanError):
    """Raised when the bounded UDP send fails."""


def validate_mac(mac: str | bytes) -> bytes:
    """Return a strict six-byte globally administered unicast MAC."""
    if isinstance(mac, bytes):
        raw = mac
    elif isinstance(mac, str) and _MAC_PATTERN.fullmatch(mac):
        raw = bytes.fromhex(mac.replace(":", ""))
    else:
        raise InvalidMacAddress(
            "MAC must contain exactly six colon-separated hexadecimal octets"
        )
    if len(raw) != 6:
        raise InvalidMacAddress("MAC must contain exactly six bytes")
    if raw == b"\x00" * 6:
        raise InvalidMacAddress("all-zero MAC addresses are not valid devices")
    if raw == b"\xff" * 6:
        raise InvalidMacAddress("the broadcast MAC is not a unicast device")
    if raw[0] & 0x01:
        raise InvalidMacAddress("multicast MAC addresses are not supported")
    if raw[0] & 0x02:
        raise InvalidMacAddress(
            "locally administered/randomized MAC addresses are unsupported"
        )
    return raw


def _active_private_networks(
    active_networks: Iterable[
        str | ipaddress.IPv4Network | ipaddress.IPv4Interface
    ],
) -> tuple[ipaddress.IPv4Network, ...]:
    """_active_private_networks."""
    networks: list[ipaddress.IPv4Network] = []
    for value in active_networks:
        try:
            if isinstance(value, ipaddress.IPv4Interface):
                network = value.network
            else:
                network = ipaddress.ip_network(str(value), strict=False)
        except ValueError as exc:
            raise InvalidBroadcastAddress(
                f"invalid active IPv4 network: {value!r}"
            ) from exc
        if not isinstance(network, ipaddress.IPv4Network):
            raise InvalidBroadcastAddress(
                f"active network is not IPv4: {value!r}"
            )
        if (
            not any(network.subnet_of(scope) for scope in _PRIVATE_NETWORKS)
            or network.is_loopback
            or network.is_link_local
            or network.is_multicast
            or network.prefixlen > 30
        ):
            raise InvalidBroadcastAddress(
                f"active network is not a usable private LAN: {value!r}"
            )
        networks.append(network)
    unique = tuple(sorted(
        set(networks),
        key=lambda item: (int(item.network_address), item.prefixlen),
    ))
    if not unique:
        raise InvalidBroadcastAddress(
            "at least one active private IPv4 network is required"
        )
    return unique
    """_active_private_networks."""
    """_active_private_networks."""


def validate_broadcast(
    broadcast: str,
    active_networks: Iterable[
        str | ipaddress.IPv4Network | ipaddress.IPv4Interface
    ],
) -> str:
    """Return a subnet-directed broadcast in a supplied active private LAN."""
    try:
        address = ipaddress.ip_address(str(broadcast))
    except ValueError as exc:
        raise InvalidBroadcastAddress(
            f"invalid IPv4 broadcast address: {broadcast!r}"
        ) from exc
    if not isinstance(address, ipaddress.IPv4Address):
        raise InvalidBroadcastAddress("broadcast address must be IPv4")
    networks = _active_private_networks(active_networks)
    if address == ipaddress.IPv4Address("255.255.255.255"):
        raise InvalidBroadcastAddress(
            "the limited broadcast address is not allowed"
        )
    if not any(
        address == network.broadcast_address and address in network
        for network in networks
    ):
        raise InvalidBroadcastAddress(
            "broadcast is not the directed broadcast of a supplied active LAN"
        )
    return str(address)


def build_magic_packet(mac: str | bytes) -> bytes:
    """Build the standard 102-byte Wake-on-LAN magic packet."""
    hardware_address = validate_mac(mac)
    packet = b"\xff" * 6 + hardware_address * _MAGIC_REPEAT
    if len(packet) != _PACKET_SIZE:  # Defensive invariant.
        raise WakeOnLanError("internal magic packet size error")
    return packet


def send_magic_packet(
    mac: str | bytes,
    broadcast: str,
    active_networks: Iterable[
        str | ipaddress.IPv4Network | ipaddress.IPv4Interface
    ],
    *,
    port: int = 9,
    timeout: float = 1.0,
) -> int:
    """Send one bounded UDP broadcast and return the transmitted byte count."""
    valid_port = (
        isinstance(port, int)
        and not isinstance(port, bool)
        and 1 <= port <= 65535
    )
    if not valid_port:
        raise ValueError("UDP port must be an integer from 1 through 65535")
    try:
        requested_timeout = float(timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout must be a finite positive number") from exc
    if not math.isfinite(requested_timeout) or requested_timeout <= 0:
        raise ValueError("timeout must be a finite positive number")
    bounded_timeout = min(
        _MAX_TIMEOUT, max(_MIN_TIMEOUT, requested_timeout)
    )
    packet = build_magic_packet(mac)
    destination = validate_broadcast(broadcast, active_networks)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(bounded_timeout)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sent = sock.sendto(packet, (destination, port))
    except (OSError, TimeoutError) as exc:
        raise WakeOnLanSendError(
            f"could not send Wake-on-LAN packet to {destination}:{port}: {exc}"
        ) from exc
    finally:
        sock.close()
    if sent != len(packet):
        raise WakeOnLanSendError(
            f"partial Wake-on-LAN datagram send ({sent}/{len(packet)} bytes)"
        )
    return sent


__all__ = [
    "InvalidBroadcastAddress", "InvalidMacAddress", "WakeOnLanError",
    "WakeOnLanSendError", "build_magic_packet", "send_magic_packet",
    "validate_broadcast", "validate_mac",
]
