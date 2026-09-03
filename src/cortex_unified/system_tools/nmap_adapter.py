"""Optional Nmap integration, bounded to explicitly authorized private LANs.

Invokes a user-installed ``nmap`` executable directly (no shell), parses its
XML under hard resource limits, and rejects any target outside the caller's
authorized private IPv4 scopes. Nmap output is treated as untrusted data:
byte/node/depth caps and DTD/entity rejection bound parser exposure.
"""

from __future__ import annotations

import ctypes
import ipaddress
import shutil
import sys
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Iterable

from cortex_unified.core import proc
from cortex_unified.system_tools.network_service_scanner import (
    ServiceObservation,
    is_authorized_target,
    parse_allowed_networks,
)

# Hard caps on Nmap's XML before parsing: the producer is an external process
# whose output size is unbounded without them.
MAX_XML_BYTES = 4 * 1024 * 1024
MAX_XML_NODES = 50_000
MAX_XML_DEPTH = 32
MAX_TARGETS = 256
MAX_PORTS = 4096
_DEFAULT_MODES = ("connect", "version")
_SCAN_MODES = {"connect", "syn", "ack"}
_EXPERT_MODES = {"syn", "ack", "os"}
_ALL_MODES = _SCAN_MODES | {"version", "os"}


class NmapError(RuntimeError):
    """Base exception for adapter failures."""


class NmapUnavailableError(NmapError):
    """Raised when the optional Nmap executable cannot be found."""


class NmapAuthorizationError(NmapError):
    """Raised when any requested target is not explicitly authorized."""


class NmapPrivilegeError(NmapError):
    """Raised when an expert mode is requested without Windows elevation."""


class NmapExecutionError(NmapError):
    """Raised when Nmap exits unsuccessfully."""


class NmapOutputError(NmapError):
    """Raised when Nmap XML is malformed, unsafe, or exceeds a bound."""


@dataclass(frozen=True, slots=True)
class NmapStatus:
    """Side-effect-free optional executable status."""

    available: bool
    executable: str | None
    reason: str


def _is_windows_admin() -> bool:
    """Return true only when Windows confirms this process is elevated."""
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
    """_local_name."""
    """_local_name."""


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]
    """_children."""
    """_children."""


def _descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [item for item in element.iter() if _local_name(item.tag) == name]
    """_descendants."""
    """_descendants."""


def _bounded_root(payload: bytes | str) -> ET.Element:
    if isinstance(payload, str):
        data = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        data = payload
    else:
        raise NmapOutputError("Nmap XML must be bytes or text")
    if len(data) > MAX_XML_BYTES:
        raise NmapOutputError("Nmap XML exceeds the byte limit")
    upper = data.upper()
    # DTDs/entity declarations enable XXE (file reads, SSRF) during parsing;
    # Nmap never emits them, so their presence means tampered input.
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise NmapOutputError("DTD and entity declarations are forbidden")
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, UnicodeError) as exc:
        raise NmapOutputError(f"invalid Nmap XML: {exc}") from exc
    count = 0
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > MAX_XML_NODES:
            raise NmapOutputError("Nmap XML exceeds the node limit")
        if depth > MAX_XML_DEPTH:
            raise NmapOutputError("Nmap XML exceeds the depth limit")
        stack.extend((child, depth + 1) for child in node)
    return root
    """_bounded_root."""
    """_bounded_root."""


def _normalize_targets(
    targets: Iterable[str],
    allowed_networks: Iterable[str | ipaddress.IPv4Network],
) -> tuple[tuple[str, ...], tuple[ipaddress.IPv4Network, ...]]:
    scopes = parse_allowed_networks(allowed_networks)
    if not scopes:
        raise NmapAuthorizationError(
            "at least one private IPv4 scope is required"
        )
    normalized: list[ipaddress.IPv4Address] = []
    for target in targets:
        if not is_authorized_target(target, scopes):
            raise NmapAuthorizationError(
                f"target is not an authorized private IPv4 host: {target!r}"
            )
        normalized.append(ipaddress.IPv4Address(str(target)))
    unique = sorted(set(normalized), key=int)
    if not unique:
        raise NmapAuthorizationError(
            "at least one explicit target is required"
        )
    if len(unique) > MAX_TARGETS:
        raise NmapAuthorizationError(
            f"target count exceeds the limit of {MAX_TARGETS}"
        )
    return tuple(map(str, unique)), scopes
    """_normalize_targets."""
    """_normalize_targets."""


def _normalize_ports(ports: Iterable[int]) -> tuple[int, ...]:
    normalized: list[int] = []
    for value in ports:
        if isinstance(value, bool):
            raise ValueError(f"invalid TCP port: {value!r}")
        try:
            port = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid TCP port: {value!r}") from exc
        if str(port) != str(value).strip() or not 1 <= port <= 65535:
            raise ValueError(f"invalid TCP port: {value!r}")
        normalized.append(port)
    unique = tuple(sorted(set(normalized)))
    if not unique:
        raise ValueError("at least one explicit TCP port is required")
    if len(unique) > MAX_PORTS:
        raise ValueError(f"port count exceeds the limit of {MAX_PORTS}")
    return unique
    """_normalize_ports."""
    """_normalize_ports."""


def _normalize_modes(modes: Iterable[str] | str | None) -> tuple[str, ...]:
    if modes is None:
        values = _DEFAULT_MODES
    elif isinstance(modes, str):
        values = (modes,)
    else:
        values = tuple(modes)
    normalized = tuple(sorted({str(item).strip().lower() for item in values}))
    unknown = set(normalized) - _ALL_MODES
    if unknown:
        joined = ", ".join(sorted(unknown))
        raise ValueError(f"unsupported Nmap mode(s): {joined}")
    selected_scans = set(normalized) & _SCAN_MODES
    if len(selected_scans) > 1:
        raise ValueError(
            "connect, syn, and ack scan modes are mutually exclusive"
        )
    if set(normalized) & _EXPERT_MODES and not _is_windows_admin():
        raise NmapPrivilegeError(
            "expert modes require explicit Windows administrator access"
        )
    return normalized
    """_normalize_modes."""
    """_normalize_modes."""


def parse_nmap_xml(
    payload: bytes | str,
    allowed_networks: Iterable[str | ipaddress.IPv4Network],
) -> list[ServiceObservation]:
    """Parse bounded Nmap XML into deterministic service observations.

    A host outside *allowed_networks* raises :class:`NmapOutputError` instead
    of being skipped: XML claiming unauthorized hosts is itself evidence of
    tampering, not data to filter.
    """
    scopes = parse_allowed_networks(allowed_networks)
    root = _bounded_root(payload)
    observations: list[ServiceObservation] = []
    for host in _descendants(root, "host"):
        addresses = [
            item.get("addr", "")
            for item in _children(host, "address")
            if item.get("addrtype") == "ipv4"
        ]
        if not addresses:
            continue
        ip = addresses[0]
        if not is_authorized_target(ip, scopes):
            raise NmapOutputError(
                f"Nmap returned an unauthorized or invalid host: {ip!r}"
            )
        ip = str(ipaddress.IPv4Address(ip))
        os_matches = sorted({
            (item.get("name", "")[:160], item.get("accuracy", "")[:3])
            for item in _descendants(host, "osmatch")
            if item.get("name")
        })[:8]
        for port_node in _descendants(host, "port"):
            protocol = port_node.get("protocol", "").lower()
            if protocol not in {"tcp", "udp"}:
                continue
            try:
                port = int(port_node.get("portid", ""))
            except ValueError:
                continue
            if not 1 <= port <= 65535:
                continue
            states = _children(port_node, "state")
            state = states[0].get("state", "unknown") if states else "unknown"
            if state == "closed":
                continue
            reason = states[0].get("reason", "") if states else ""
            services = _children(port_node, "service")
            service = services[0] if services else None
            if service is not None:
                name = service.get("name", "unknown")
                product = service.get("product", "")
                version = service.get("version", "")
            else:
                name, product, version = "unknown", "", ""
            evidence = [f"Nmap reported {protocol}/{port} {state}"]
            if product or version:
                parts = (product, version)
                identified = " ".join(item for item in parts if item)
                evidence.append(f"Nmap service identification: {identified}")
            evidence.extend(
                f"Nmap OS match: {os_name} ({accuracy}% accuracy)"
                for os_name, accuracy in os_matches
            )
            service_data = {}
            if service is not None:
                service_data = {
                    key: service.get(key, "")
                    for key in ("method", "conf", "tunnel", "extrainfo")
                    if service.get(key)
                }
            metadata = {
                "evidence": evidence,
                "state_reason": reason,
                "service": service_data,
                "os_matches": [
                    {"name": item[0], "accuracy": item[1]}
                    for item in os_matches
                ],
            }
            confidence = 0.75
            if service is not None and service.get("conf", "").isdigit():
                confidence = min(1.0, int(service.get("conf", "0")) / 10.0)
            observations.append(ServiceObservation(
                ip=ip,
                port=port,
                transport=protocol,
                name=name or "unknown",
                state=state,
                source="nmap",
                product=product,
                version=version,
                metadata=metadata,
                confidence=confidence,
            ))
    unique = {
        (item.ip, item.port, item.transport, item.name, item.state): item
        for item in observations
    }
    return sorted(unique.values(), key=lambda item: (
        int(ipaddress.IPv4Address(item.ip)), item.port,
        item.transport, item.name, item.state,
    ))


class NmapAdapter:
    """Discover and invoke optional Nmap without shell or script support."""

    def __init__(self, executable: str = "nmap") -> None:
        """Initialize Nmap Adapter."""
        self._requested_executable = executable

    def _executable(self) -> str | None:
        return shutil.which(self._requested_executable)
        """_executable."""
        """_executable."""

    @property
    def available(self) -> bool:
        """Available."""
        return self._executable() is not None

    def status(self) -> NmapStatus:
        """Status."""
        executable = self._executable()
        if executable:
            return NmapStatus(True, executable, "Nmap is available")
        return NmapStatus(
            False, None,
            f"Nmap executable {self._requested_executable!r} is not available",
        )

    def build_arguments(
        self,
        targets: Iterable[str],
        allowed_networks: Iterable[str | ipaddress.IPv4Network],
        ports: Iterable[int],
        modes: Iterable[str] | str | None = None,
    ) -> tuple[list[str], tuple[ipaddress.IPv4Network, ...]]:
        """Build the nmap argv for one scan; no shell interpolation involved.

        ``-n -Pn`` skip DNS resolution and host discovery so every target is
        probed exactly as given; XML is written to stdout via ``-oX -``.
        """
        executable = self._executable()
        if executable is None:
            raise NmapUnavailableError(self.status().reason)
        hosts, scopes = _normalize_targets(targets, allowed_networks)
        selected_ports = _normalize_ports(ports)
        selected_modes = _normalize_modes(modes)
        scan_mode = next(
            (item for item in ("connect", "syn", "ack")
             if item in selected_modes),
            "connect",
        )
        mode_argument = {"connect": "-sT", "syn": "-sS", "ack": "-sA"}
        arguments = [executable, "-n", "-Pn", mode_argument[scan_mode]]
        if "version" in selected_modes:
            arguments.extend(["-sV", "--version-light"])
        if "os" in selected_modes:
            arguments.append("-O")
        arguments.extend([
            "--max-retries", "2", "--host-timeout", "30s",
            "-p", ",".join(map(str, selected_ports)), "-oX", "-",
        ])
        arguments.extend(hosts)
        return arguments, scopes

    def scan(
        self,
        targets: Iterable[str],
        allowed_networks: Iterable[str | ipaddress.IPv4Network],
        ports: Iterable[int],
        modes: Iterable[str] | str | None = None,
        *,
        timeout: float = 120.0,
        cancel_event: threading.Event | None = None,
    ) -> list[ServiceObservation]:
        """Run one bounded scan and return parsed observations.

        *timeout* is clamped to [0.1, 600] seconds. Non-zero exit raises
        :class:`NmapExecutionError` with up to 512 bytes of stderr.
        """
        arguments, scopes = self.build_arguments(
            targets, allowed_networks, ports, modes)
        if cancel_event is not None and cancel_event.is_set():
            raise proc.ProcessCancelled(arguments)
        try:
            result = proc.run(
                arguments,
                timeout=max(0.1, min(float(timeout), 600.0)),
                cancel_event=cancel_event,
            )
        except proc.ProcessCancelled:
            raise
        except OSError as exc:
            raise NmapExecutionError(f"could not start Nmap: {exc}") from exc
        if result.returncode != 0:
            stderr = result.stderr
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            detail = str(stderr or "unknown error").strip()[:512]
            raise NmapExecutionError(
                f"Nmap exited with status {result.returncode}: {detail}"
            )
        return parse_nmap_xml(result.stdout, scopes)


def nmap_status(executable: str = "nmap") -> NmapStatus:
    """Return side-effect-free Nmap availability information."""
    return NmapAdapter(executable).status()


def is_nmap_available(executable: str = "nmap") -> bool:
    """Return whether the optional executable can be resolved."""
    return NmapAdapter(executable).available


def scan_nmap(
    targets: Iterable[str],
    allowed_networks: Iterable[str | ipaddress.IPv4Network],
    ports: Iterable[int],
    modes: Iterable[str] | str | None = None,
    *,
    timeout: float = 120.0,
    cancel_event: threading.Event | None = None,
    executable: str = "nmap",
) -> list[ServiceObservation]:
    """Explicit function API for a bounded optional Nmap scan."""
    return NmapAdapter(executable).scan(
        targets, allowed_networks, ports, modes,
        timeout=timeout, cancel_event=cancel_event,
    )


__all__ = [
    "MAX_XML_BYTES", "MAX_XML_DEPTH", "MAX_XML_NODES", "NmapAdapter",
    "NmapAuthorizationError", "NmapError", "NmapExecutionError",
    "NmapOutputError", "NmapPrivilegeError", "NmapStatus",
    "NmapUnavailableError", "is_nmap_available", "nmap_status",
    "parse_nmap_xml", "scan_nmap",
]
