"""Read-only, local-only WAN and UPnP IGD audit.

The auditor never contacts an Internet service and never invokes a mutating
UPnP action.  Every HTTP target must be an IPv4 literal inside one of the
machine's active private interface networks, preventing DNS rebinding and
SSRF through malicious SSDP replies.
"""

from __future__ import annotations

import http.client
import ipaddress
import logging
import os
import re
import socket
import ssl
import subprocess
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable, Mapping

_LOG = logging.getLogger("cortex.system_tools.wan_audit")
_SSDP_ADDRESS = ("239.255.255.250", 1900)
_MAX_HTTP_BYTES = 256 * 1024
_MAX_XML_DEPTH = 24
_MAX_XML_NODES = 4096
_MAX_MAPPINGS = 128
_RFC1918 = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)
_CGNAT = ipaddress.IPv4Network("100.64.0.0/10")
ProgressFn = Callable[[str], None]


@dataclass(slots=True, frozen=True)
class InterfaceStatus:
    """Interfacestatus.

    Manages InterfaceStatus operations and coordinates related state changes for the component.
    """

    name: str
    address: str
    netmask: str
    network: str

    def to_dict(self) -> dict[str, str]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, str]: Dictionary mapping identifiers to status or values.
        """
        return asdict(self)


@dataclass(slots=True, frozen=True)
class PortMapping:
    """Portmapping.

    Manages PortMapping operations and coordinates related state changes for the component.
    """

    index: int
    remote_host: str
    external_port: int
    protocol: str
    internal_port: int
    internal_client: str
    enabled: bool
    description: str
    lease_duration: int

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return asdict(self)


@dataclass(slots=True)
class WanStatus:
    """Wanstatus.

    Manages WanStatus operations and coordinates related state changes for the component.
    """

    external_ip: str = ""
    external_ip_classification: str = "unknown"
    gateway: str = ""

    @property
    def public_ip_classification(self) -> str:
        """Compatibility classification used by the earlier WAN UI.

        Manages public ip classification operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        return {
            "public": "globally_routable",
            "private_upstream": "rfc1918",
            "unknown": "invalid_or_unknown",
        }.get(self.external_ip_classification, self.external_ip_classification)
    dns_servers: list[str] = field(default_factory=list)
    interfaces: list[InterfaceStatus] = field(default_factory=list)
    port_mappings: list[PortMapping] = field(default_factory=list)
    igd_found: bool = False
    location: str = ""
    control_url: str = ""
    cancelled: bool = False
    mapping_limit_reached: bool = False
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "external_ip": self.external_ip,
            "external_ip_classification": self.external_ip_classification,
            "public_ip_classification": self.public_ip_classification,
            "connectivity_tested": False,
            "gateway": self.gateway,
            "dns_servers": list(self.dns_servers),
            "interfaces": [item.to_dict() for item in self.interfaces],
            "port_mappings": [item.to_dict() for item in self.port_mappings],
            "igd_found": self.igd_found,
            "location": self.location,
            "control_url": self.control_url,
            "cancelled": self.cancelled,
            "mapping_limit_reached": self.mapping_limit_reached,
            "warnings": list(self.warnings),
            "duration_seconds": round(self.duration_seconds, 3),
        }


def classify_external_ip(value: str | None) -> str:
    """Classify an IGD-reported address without making an external request.

    Manages classify external ip operations and coordinates related state changes for the component.

    Args:
        value (str | None): The value parameter.

    Returns:
        str: Formatted string or path.
    """
    if not value:
        return "unknown"
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return "unknown"
    if not isinstance(address, ipaddress.IPv4Address):
        return "unknown"
    if address in _CGNAT:
        return "cgnat"
    if any(address in network for network in _RFC1918):
        return "private_upstream"
    if address.is_global:
        return "public"
    return "unknown"


def classify_public_ip(value: str | None) -> str:
    """Compatibility wrapper using the previous labels.

    Manages classify public ip operations and coordinates related state changes for the component.

    Args:
        value (str | None): The value parameter.

    Returns:
        str: Formatted string or path.
    """
    return {
        "public": "globally_routable",
        "private_upstream": "rfc1918",
        "unknown": "invalid_or_unknown",
    }.get(classify_external_ip(value), classify_external_ip(value))


def _local_name(tag: str) -> str:
    """_local_name.

    Manages local name operations and coordinates related state changes for the component.

    Args:
        tag (str): The tag parameter.

    Returns:
        str: Formatted string or path.
    """
    return tag.rsplit("}", 1)[-1]


def _safe_xml(data: bytes) -> ET.Element:
    """Parse size-capped XML after rejecting DTD/entity declarations.

    Manages safe xml operations and coordinates related state changes for the component.

    Args:
        data (bytes): The data parameter.

    Returns:
        ET.Element: Result of the operation.
    """
    if len(data) > _MAX_HTTP_BYTES:
        raise ValueError("XML response exceeds size limit")
    lowered = data.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ValueError("DTD and entity declarations are not accepted")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("invalid XML response") from exc
    stack: list[tuple[ET.Element, int]] = [(root, 1)]
    nodes = 0
    while stack:
        element, depth = stack.pop()
        nodes += 1
        if depth > _MAX_XML_DEPTH or nodes > _MAX_XML_NODES:
            raise ValueError("XML structure exceeds complexity limit")
        stack.extend((child, depth + 1) for child in element)
    return root


def _child_text(root: ET.Element, name: str) -> str:
    """_child_text.

    Manages child text operations and coordinates related state changes for the component.

    Args:
        root (ET.Element): Filesystem path to the target file or directory.
        name (str): The name parameter.

    Returns:
        str: Formatted string or path.
    """
    for element in root.iter():
        if _local_name(element.tag) == name:
            return (element.text or "").strip()
    return ""


def _is_trusted_url(
        url: str, networks: Iterable[ipaddress.IPv4Network]) -> bool:
    """Return whether *url* is an HTTP(S) IPv4 literal on a local LAN.

    Manages is trusted url operations and coordinates related state changes for the component.

    Args:
        url (str): The url parameter.
        networks (Iterable[ipaddress.IPv4Network]): The networks parameter.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"}:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if parsed.fragment or not parsed.hostname:
            return False
        # Accessing .port also validates malformed/out-of-range ports.
        port = parsed.port
        if port is not None and not 1 <= port <= 65535:
            return False
        address = ipaddress.ip_address(parsed.hostname)
    except (ValueError, UnicodeError):
        return False
    if not isinstance(address, ipaddress.IPv4Address):
        return False
    if not any(address in private for private in _RFC1918):
        return False
    return any(address in network for network in networks)


def _parse_headers(payload: bytes) -> dict[str, str]:
    """_parse_headers.

    Manages parse headers operations and coordinates related state changes for the component.

    Args:
        payload (bytes): The payload parameter.

    Returns:
        dict[str, str]: Dictionary mapping identifiers to status or values.
    """
    text = payload.decode("iso-8859-1", errors="replace")
    headers: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        name, separator, value = line.partition(":")
        if separator:
            headers[name.strip().lower()] = value.strip()
    return headers


def _bounded_int(value: str, minimum: int, maximum: int) -> int:
    """_bounded_int.

    Manages bounded int operations and coordinates related state changes for the component.

    Args:
        value (str): The value parameter.
        minimum (int): The minimum parameter.
        maximum (int): The maximum parameter.

    Returns:
        int: Result of the operation.
    """
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return minimum
    return min(maximum, max(minimum, parsed))


class WanAuditor:
    """Wanauditor.

    Manages WanAuditor operations and coordinates related state changes for the component.
    """

    def __init__(
        self,
        timeout: float = 2.0,
        max_response_bytes: int = _MAX_HTTP_BYTES,
        max_mappings: int = _MAX_MAPPINGS,
    ) -> None:
        """Initialize Wan Auditor.

        Initializes the instance and configures internal state.

        Args:
            timeout (float): The timeout parameter.
            max_response_bytes (int): The max response bytes parameter.
            max_mappings (int): The max mappings parameter.
        """
        self.timeout = min(10.0, max(0.1, float(timeout)))
        self.max_response_bytes = min(
            _MAX_HTTP_BYTES, max(4096, int(max_response_bytes)))
        self.max_mappings = min(
            _MAX_MAPPINGS, max(0, int(max_mappings)))

    def audit(
        self,
        gateway_ips: Iterable[str] = (),
        include_upnp: bool = False,
        progress: ProgressFn | None = None,
        cancel_event: threading.Event | None = None,
    ) -> WanStatus:
        """Audit.

        Manages audit operations and coordinates related state changes for the component.

        Args:
            gateway_ips (Iterable[str]): The gateway ips parameter.
            include_upnp (bool): The include upnp parameter.
            progress (ProgressFn | None): The progress parameter.
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.

        Returns:
            WanStatus: Result of the operation.
        """
        started = time.monotonic()
        interfaces = self.local_interfaces()
        networks = [
            ipaddress.IPv4Network(item.network, strict=False)
            for item in interfaces
        ]
        gateways: list[str] = []
        for raw in gateway_ips:
            try:
                gateway = ipaddress.IPv4Address(str(raw))
            except ValueError:
                continue
            if (any(gateway in private for private in _RFC1918)
                    and not gateway.is_loopback and not gateway.is_multicast):
                gateways.append(str(gateway))
                candidate = ipaddress.IPv4Network(f"{gateway}/24", strict=False)
                if candidate not in networks:
                    networks.append(candidate)
        route_gateway = gateways[0] if gateways else self.default_gateway()
        status = WanStatus(
            gateway=route_gateway,
            dns_servers=self.dns_servers(),
            interfaces=interfaces,
        )
        try:
            if self._cancelled(cancel_event):
                status.cancelled = True
                return status
            if not include_upnp:
                return status
            if not networks:
                status.warnings.append(
                    "No active private IPv4 interface or gateway scope was found.")
                return status
            self._progress(
                progress,
                "Discovering a local UPnP Internet Gateway Device")
            locations = self.discover_locations(networks, cancel_event)
            for location in locations:
                if self._cancelled(cancel_event):
                    status.cancelled = True
                    break
                try:
                    service_type, control_url = self._load_igd(
                        location, networks)
                    status.igd_found = True
                    status.location = location
                    status.control_url = control_url
                    self._read_soap_status(
                        status, service_type, control_url, networks,
                        cancel_event, progress)
                    break
                except (OSError, ValueError, http.client.HTTPException) as exc:
                    _LOG.debug(
                        "rejected or unreadable IGD at %s: %s", location, exc)
            if locations and not status.igd_found and not status.cancelled:
                status.warnings.append(
                    "UPnP replies were received, but no safe IGD service "
                    "was readable."
                )
            elif not locations and not status.cancelled:
                status.warnings.append(
                    "No local UPnP Internet Gateway Device replied.")
        finally:
            status.cancelled = status.cancelled or self._cancelled(
                cancel_event)
            status.duration_seconds = time.monotonic() - started
        return status

    @staticmethod
    def _cancelled(cancel_event: threading.Event | None) -> bool:
        """Cancelled.

        Manages cancelled operations and coordinates related state changes for the component.

        Args:
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return cancel_event is not None and cancel_event.is_set()

    @staticmethod
    def _progress(progress: ProgressFn | None, message: str) -> None:
        """_progress.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            progress (ProgressFn | None): The progress parameter.
            message (str): Informational or progress status message.
        """
        if progress is not None:
            progress(message)

    @staticmethod
    def local_interfaces() -> list[InterfaceStatus]:
        """Return private IPv4 addresses using only standard-library lookups.

        Netmasks are not exposed portably by the standard library, so inferred
        /24 networks are used only as a narrow trust boundary for optional
        local IGD reads. Explicit gateway scopes are added separately.
        """
        result: list[InterfaceStatus] = []
        try:
            records = socket.getaddrinfo(
                socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM)
        except OSError:
            return result
        seen: set[str] = set()
        for record in records:
            candidate = record[4][0]
            try:
                address = ipaddress.IPv4Address(candidate)
            except ValueError:
                continue
            if (candidate in seen or address.is_loopback
                    or not any(address in private for private in _RFC1918)):
                continue
            seen.add(candidate)
            network = ipaddress.IPv4Network(f"{address}/24", strict=False)
            result.append(InterfaceStatus(
                name="local",
                address=str(address),
                netmask="255.255.255.0",
                network=str(network),
            ))
        return result

    def discover_locations(
        self,
        networks: Iterable[ipaddress.IPv4Network],
        cancel_event: threading.Event | None = None,
    ) -> list[str]:
        """Issue bounded SSDP searches; return trusted LOCATION URLs.

        Manages discover locations operations and coordinates related state changes for the component.

        Args:
            networks (Iterable[ipaddress.IPv4Network]): The networks parameter.
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.

        Returns:
            list[str]: List of processed items or identifiers.
        """
        trusted_networks = tuple(networks)
        request = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 1\r\n"
            "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n"
            "\r\n"
        ).encode("ascii")
        locations: list[str] = []
        deadline = time.monotonic() + self.timeout
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(min(0.2, self.timeout))
                sock.sendto(request, _SSDP_ADDRESS)
                while (
                    time.monotonic() < deadline
                    and not self._cancelled(cancel_event)
                ):
                    try:
                        payload, _peer = sock.recvfrom(16 * 1024)
                    except socket.timeout:
                        continue
                    headers = _parse_headers(payload)
                    location = headers.get("location", "")
                    if (location and location not in locations
                            and _is_trusted_url(location, trusted_networks)):
                        locations.append(location)
        except OSError as exc:
            _LOG.debug("SSDP discovery failed: %s", exc)
        return locations

    def _load_igd(
        self,
        location: str,
        networks: Iterable[ipaddress.IPv4Network],
    ) -> tuple[str, str]:
        """_load_igd.

        Manages load igd operations and coordinates related state changes for the component.

        Args:
            location (str): The location parameter.
            networks (Iterable[ipaddress.IPv4Network]): The networks parameter.

        Returns:
            tuple[str, str]: Formatted string or path.
        """
        trusted_networks = tuple(networks)
        if not _is_trusted_url(location, trusted_networks):
            raise ValueError("untrusted IGD location")
        _status, _headers, payload = self._http_request("GET", location)
        root = _safe_xml(payload)
        for service in root.iter():
            if _local_name(service.tag) != "service":
                continue
            values = {
                _local_name(child.tag): (child.text or "").strip()
                for child in service
            }
            service_type = values.get("serviceType", "")
            if not (service_type.startswith(
                    "urn:schemas-upnp-org:service:WANIPConnection:") or
                    service_type.startswith(
                    "urn:schemas-upnp-org:service:WANPPPConnection:")):
                continue
            raw_control = values.get("controlURL", "")
            if not raw_control:
                continue
            control_url = urllib.parse.urljoin(location, raw_control)
            if not _is_trusted_url(control_url, trusted_networks):
                raise ValueError("untrusted IGD control URL")
            return service_type, control_url
        raise ValueError("IGD WAN connection service not found")

    def _read_soap_status(
        self,
        status: WanStatus,
        service_type: str,
        control_url: str,
        networks: Iterable[ipaddress.IPv4Network],
        cancel_event: threading.Event | None,
        progress: ProgressFn | None,
    ) -> None:
        """_read_soap_status.

        Manages read soap status operations and coordinates related state changes for the component.

        Args:
            status (WanStatus): The status parameter.
            service_type (str): The service type parameter.
            control_url (str): The control url parameter.
            networks (Iterable[ipaddress.IPv4Network]): The networks parameter.
            cancel_event (threading.Event | None): Threading event or callable to check for cancellation.
            progress (ProgressFn | None): The progress parameter.
        """
        if not _is_trusted_url(control_url, networks):
            raise ValueError("untrusted SOAP target")
        self._progress(progress, "Reading the IGD-reported external address")
        try:
            root = self._soap(
                control_url,
                service_type,
                "GetExternalIPAddress")
            status.external_ip = _child_text(root, "NewExternalIPAddress")
            status.external_ip_classification = classify_external_ip(
                status.external_ip)
        except (OSError, ValueError, http.client.HTTPException) as exc:
            status.warnings.append(
                f"The IGD external address could not be read: {exc}")

        self._progress(progress, "Enumerating read-only IGD port mappings")
        for index in range(self.max_mappings):
            if self._cancelled(cancel_event):
                status.cancelled = True
                return
            try:
                root = self._soap(
                    control_url,
                    service_type,
                    "GetGenericPortMappingEntry",
                    {"NewPortMappingIndex": str(index)},
                )
                status.port_mappings.append(
                    self._mapping_from_xml(index, root))
            except _NoMoreMappings:
                return
            except (OSError, ValueError, http.client.HTTPException) as exc:
                status.warnings.append(
                    "Port mapping enumeration stopped at index "
                    f"{index}: {exc}"
                )
                return
        if self.max_mappings:
            status.mapping_limit_reached = True
            status.warnings.append(
                "Port mapping enumeration was capped at "
                f"{self.max_mappings} entries."
            )

    def _soap(
        self,
        url: str,
        service_type: str,
        action: str,
        arguments: Mapping[str, str] | None = None,
    ) -> ET.Element:
        # Only these two read-only actions are intentionally reachable.
        """Soap.

        Manages soap operations and coordinates related state changes for the component.

        Args:
            url (str): The url parameter.
            service_type (str): The service type parameter.
            action (str): The action parameter.
            arguments (Mapping[str, str] | None): The arguments parameter.

        Returns:
            ET.Element: Result of the operation.
        """
        if action not in {"GetExternalIPAddress",
                          "GetGenericPortMappingEntry"}:
            raise ValueError("unsupported SOAP action")
        argument_xml = "".join(
            f"<{name}>{_xml_escape(value)}</{name}>"
            for name, value in (arguments or {}).items()
        )
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{action} xmlns:u="{service_type}">'
            f"{argument_xml}</u:{action}></s:Body></s:Envelope>"
        ).encode("utf-8")
        http_status, _headers, payload = self._http_request(
            "POST",
            url,
            body=body,
            headers={
                "Content-Type": 'text/xml; charset="utf-8"',
                "SOAPAction": f'"{service_type}#{action}"',
            },
        )
        root = _safe_xml(payload)
        if http_status >= 400 or _child_text(root, "errorCode"):
            error_code = _child_text(root, "errorCode")
            description = _child_text(root, "errorDescription")
            if action == "GetGenericPortMappingEntry" and error_code in {
                    "713", "714"}:
                raise _NoMoreMappings
            raise ValueError(
                f"SOAP fault {error_code or http_status}: "
                f"{description or 'unknown error'}"
            )
        return root

    @staticmethod
    def _mapping_from_xml(index: int, root: ET.Element) -> PortMapping:
        """_mapping_from_xml.

        Manages mapping from xml operations and coordinates related state changes for the component.

        Args:
            index (int): The index parameter.
            root (ET.Element): Filesystem path to the target file or directory.

        Returns:
            PortMapping: Result of the operation.
        """
        protocol = _child_text(root, "NewProtocol").upper()
        if protocol not in {"TCP", "UDP"}:
            protocol = "UNKNOWN"
        return PortMapping(
            index=index,
            remote_host=_child_text(root, "NewRemoteHost"),
            external_port=_bounded_int(
                _child_text(root, "NewExternalPort"), 0, 65535),
            protocol=protocol,
            internal_port=_bounded_int(
                _child_text(root, "NewInternalPort"), 0, 65535),
            internal_client=_child_text(root, "NewInternalClient"),
            enabled=_child_text(
                root, "NewEnabled").lower() in {
                "1", "true", "yes"},
            description=_child_text(root, "NewPortMappingDescription")[:512],
            lease_duration=_bounded_int(
                _child_text(root, "NewLeaseDuration"), 0, 2**31 - 1),
        )

    def _http_request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        """Perform one no-redirect request with a hard response-size cap.

        Manages http request operations and coordinates related state changes for the component.

        Args:
            method (str): The method parameter.
            url (str): The url parameter.
            body (bytes | None): The body parameter.
            headers (Mapping[str, str] | None): The headers parameter.

        Returns:
            tuple[int, dict[str, str], bytes]: Dictionary mapping identifiers to status or values.
        """
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname
        if host is None:
            raise ValueError("URL has no host")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = urllib.parse.urlunsplit(
            ("", "", parsed.path or "/", parsed.query, ""))
        connection: http.client.HTTPConnection
        if parsed.scheme == "https":
            connection = http.client.HTTPSConnection(
                host, port, timeout=self.timeout,
                context=ssl.create_default_context())
        else:
            connection = http.client.HTTPConnection(
                host, port, timeout=self.timeout)
        try:
            connection.request(
                method, path, body=body, headers=dict(
                    headers or {}))
            response = connection.getresponse()
            content_length = response.getheader("Content-Length")
            if content_length is not None:
                try:
                    if int(content_length) > self.max_response_bytes:
                        raise ValueError("HTTP response exceeds size limit")
                except ValueError as exc:
                    if "exceeds" in str(exc):
                        raise
            payload = response.read(self.max_response_bytes + 1)
            if len(payload) > self.max_response_bytes:
                raise ValueError("HTTP response exceeds size limit")
            if 300 <= response.status < 400:
                raise ValueError("HTTP redirects are not followed")
            if response.status >= 400 and method == "GET":
                raise ValueError(
                    f"HTTP request failed with status {response.status}"
                )
            response_headers = {
                name.lower(): value for name,
                value in response.getheaders()}
            return response.status, response_headers, payload
        finally:
            connection.close()

    @staticmethod
    def default_gateway() -> str:
        """Read the local default IPv4 route without network traffic.

        Manages default gateway operations and coordinates related state changes for the component.

        Returns:
            str: Formatted string or path.
        """
        commands = (
            ["route", "print", "-4"] if os.name == "nt"
            else ["ip", "-4", "route", "show", "default"]
        )
        try:
            completed = subprocess.run(
                commands,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
                creationflags=0x08000000 if os.name == "nt" else 0)
        except (OSError, subprocess.SubprocessError):
            return ""
        patterns = (
            r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+(?:\.\d+){3})"
            if os.name == "nt" else
            r"\bdefault\s+via\s+(\d+(?:\.\d+){3})"
        )
        match = re.search(patterns, completed.stdout or "", re.MULTILINE)
        if not match:
            return ""
        try:
            address = ipaddress.IPv4Address(match.group(1))
        except ValueError:
            return ""
        return str(address)

    @staticmethod
    def dns_servers() -> list[str]:
        """Read locally configured DNS server addresses.

        Manages dns servers operations and coordinates related state changes for the component.

        Returns:
            list[str]: List of processed items or identifiers.
        """
        text = ""
        if os.name == "nt":
            try:
                completed = subprocess.run(
                    ["ipconfig", "/all"], capture_output=True, text=True,
                    timeout=4, check=False, creationflags=0x08000000)
                text = completed.stdout or ""
            except (OSError, subprocess.SubprocessError):
                return []
        else:
            try:
                with open(
                    "/etc/resolv.conf",
                    encoding="utf-8",
                    errors="replace",
                ) as handle:
                    text = handle.read(64 * 1024)
            except OSError:
                return []
        candidates = re.findall(
            r"(?<![\w:])\d{1,3}(?:\.\d{1,3}){3}(?![\w:])", text)
        result: list[str] = []
        for candidate in candidates:
            try:
                value = str(ipaddress.IPv4Address(candidate))
            except ValueError:
                continue
            if value not in result:
                result.append(value)
        return result[:16]


class _NoMoreMappings(Exception):
    """Nomoremappings.

    Manages NoMoreMappings operations and coordinates related state changes for the component.
    """


def _xml_escape(value: str) -> str:
    """_xml_escape.

    Manages xml escape operations and coordinates related state changes for the component.

    Args:
        value (str): The value parameter.

    Returns:
        str: Formatted string or path.
    """
    return (value.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")
            .replace("'", "&apos;"))


def audit_wan(
    gateway_ips: Iterable[str] = (),
    include_upnp: bool = False,
    progress: ProgressFn | None = None,
    cancel_event: threading.Event | None = None,
) -> WanStatus:
    """Return route-only status unless optional local UPnP reads are authorized.

    Manages audit wan operations and coordinates related state changes for the component.

    Args:
        gateway_ips (Iterable[str]): The gateway ips parameter.
        include_upnp (bool): The include upnp parameter.
        progress (ProgressFn | None): The progress parameter.
        cancel_event (threading.Event | None): Threading event or callable to check for cancellation.

    Returns:
        WanStatus: Result of the operation.
    """
    return WanAuditor().audit(
        gateway_ips=gateway_ips,
        include_upnp=include_upnp,
        progress=progress,
        cancel_event=cancel_event,
    )


__all__ = [
    "InterfaceStatus", "PortMapping", "WanAuditor", "WanStatus", "audit_wan",
    "classify_external_ip", "classify_public_ip",
]
