"""Bounded, non-destructive service observation on authorized private LANs.

Scans explicit private IPv4 hosts via TCP connect plus passive banner reads,
then narrows identification with bounded HTTP/TLS/MQTT/Redis probes and a small
set of read-only UDP discovery requests. Every target is re-checked against the
caller-supplied allow-list immediately before each probe, responses are capped,
and timeouts/rate limits are hard-bounded so a scan stays quiet and finite.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
import socket
import ssl
import struct
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Iterator, Mapping

ProgressFn = Callable[[str], None]
_MAX_RESPONSE = 8192
_MAX_PROBE_TIMEOUT = 2.0
MAX_CUSTOM_PORTS = 4096


class ScanProfile(Enum):
    """Probe breadth for a scan.

    Attributes:
        TARGETED: Common home/lab TCP ports only.
        ADVANCED: Extended TCP list plus UDP discovery probes.
        DEEP: All 65535 TCP ports plus UDP discovery probes.
    """

    TARGETED = "targeted"
    ADVANCED = "advanced"
    DEEP = "deep"


def _json_safe(value: Any) -> Any:
    """Return a deterministic JSON-native representation."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=str)]
    return str(value)


@dataclass(slots=True)
class ServiceObservation:
    """One observed service endpoint on an authorized host.

    Attributes:
        ip: Address that answered.
        port: Port probed.
        transport: ``"tcp"`` or ``"udp"``.
        name: Service label; ``"unknown"`` when unidentified.
        state: Connection outcome; only open ports yield observations.
        source: Probe type that produced the evidence.
        banner: Sanitized, size-capped response text.
        product: Server product parsed from the banner, if any.
        version: Product version parsed from the banner, if any.
        metadata: Probe-specific evidence (TLS details, HTTP status, MQTT/Redis codes).
        latency_ms: Round-trip milliseconds for connect or reply.
        confidence: 0-1 estimate that ``name`` is correct.
    """

    ip: str
    port: int
    transport: str
    name: str
    state: str = "open"
    source: str = ""
    banner: str = ""
    product: str = ""
    version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    latency_ms: float | None = None
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        confidence = self.confidence if math.isfinite(self.confidence) else 0.0
        latency = self.latency_ms
        if latency is not None and not math.isfinite(latency):
            latency = None
        return {
            "ip": self.ip,
            "port": int(self.port),
            "transport": self.transport,
            "name": self.name,
            "state": self.state,
            "source": self.source,
            "banner": self.banner,
            "product": self.product,
            "version": self.version,
            "metadata": _json_safe(self.metadata),
            "latency_ms": latency,
            "confidence": round(max(0.0, min(1.0, confidence)), 3),
        }

    # Compatibility with the earlier audit draft.
    @property
    def target(self) -> str:
        """Target."""
        return self.ip

    @property
    def service(self) -> str:
        """Service."""
        return self.name

    @property
    def details(self) -> dict[str, Any]:
        """Details."""
        return self.metadata

    @property
    def evidence(self) -> list[str]:
        """Evidence."""
        evidence = self.metadata.get("evidence", [])
        if isinstance(evidence, str):
            return [evidence]
        return [str(item) for item in evidence]


_TARGETED_TCP = (
    21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 548, 631, 993,
    995, 1883, 2375, 3389, 5555, 5900, 6379, 8000, 8008, 8009, 8080,
    8081, 8123, 8443, 8883, 9100, 32400, 62078,
)
_ADVANCED_TCP = tuple(sorted(set(_TARGETED_TCP + (
    20, 26, 37, 49, 67, 68, 69, 79, 81, 88, 111, 119, 123, 135, 137,
    138, 161, 389, 427, 465, 500, 514, 515, 554, 587, 636, 873, 902,
    1080, 1433, 1521, 1723, 2049, 2376, 3000, 3128, 3306, 5000, 5060,
    5432, 5672, 5985, 5986, 7001, 8088, 8181, 8888, 9000, 9090, 9200,
    11211, 27017,
))))

_NAMES = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 139: "netbios", 143: "imap",
    443: "https", 445: "smb", 548: "afp", 631: "ipp",
    993: "imaps", 995: "pop3s", 1883: "mqtt", 2375: "docker",
    2376: "docker-tls", 3389: "rdp", 5555: "adb", 5900: "vnc",
    6379: "redis", 8080: "http", 8081: "http", 8443: "https",
    8883: "mqtt-tls", 9100: "printer", 9200: "elasticsearch",
}
_HTTP_PORTS = {80, 81, 631, 2375, 3000, 3128, 5000, 5985, 7001, 8000,
               8008, 8080, 8081, 8088, 8181, 8888, 9000, 9090, 9200}
_TLS_PORTS = {443, 465, 636, 993, 995, 2376, 5986, 8443, 8883}

# All UDP requests are bounded, read-only requests. SNMP is added only for
# advanced/deep profiles and asks for sysDescr.0 using the conventional public
# community; a finding is possible only if the peer actually responds.
_UDP_PROBES = (
    (53, "dns", bytes.fromhex(
        "4352010000010000000000000776657273696f6e0462696e640000100003")),
    (123, "ntp", b"\x23" + b"\x00" * 47),
    (137, "netbios", bytes.fromhex(
        "43520110000100000000000020434b4141414141414141414141414141414141"
        "4141414141414141414141414141410000210001")),
    (1900, "ssdp", (
        b"M-SEARCH * HTTP/1.1\r\nST: upnp:rootdevice\r\n"
        b"MAN: \"ssdp:discover\"\r\nMX: 1\r\n\r\n")),
    (3702, "wsd", (
        b"<?xml version='1.0'?><Probe xmlns='http://schemas.xmlsoap."
        b"org/ws/2005/04/discovery'/>")),
    (5353, "mdns", bytes.fromhex(
        "435200000001000000000000095f7365727669636573075f646e732d736404"
        "5f756470056c6f63616c00000c8001")),
)
_SNMP_PROBE = bytes.fromhex(
    "302602010004067075626c6963a019020143020100020100300e300c06082b0601"
    "020101000500"
)


def parse_allowed_networks(values: Iterable[str | ipaddress.IPv4Network]) -> tuple[ipaddress.IPv4Network, ...]:
    """Validate explicit private IPv4 scopes."""
    networks: list[ipaddress.IPv4Network] = []
    for value in values:
        try:
            network = ipaddress.ip_network(str(value), strict=False)
        except ValueError as exc:
            raise ValueError(f"invalid IPv4 network scope: {value!r}") from exc
        if not isinstance(network, ipaddress.IPv4Network):
            raise ValueError(f"network scope is not IPv4: {value!r}")
        if (not network.is_private or network.is_loopback
                or network.is_link_local or network.is_multicast):
            raise ValueError(f"network scope is not a usable private LAN: {value!r}")
        networks.append(network)
    return tuple(sorted(set(networks), key=lambda item: (int(item.network_address), item.prefixlen)))


def parse_network_scope_spec(value: str) -> tuple[str, ...]:
    """Parse private IPv4 hosts, CIDRs, or inclusive address ranges."""
    text = str(value or "").strip()
    if not text:
        return ()
    networks: list[ipaddress.IPv4Network] = []
    for token in text.split(","):
        part = token.strip()
        if not part:
            raise ValueError("empty item in private network scope")
        if "-" not in part:
            networks.extend(parse_allowed_networks((part,)))
            continue
        start_text, separator, end_text = part.partition("-")
        if not separator:
            raise ValueError(f"invalid IPv4 address range: {part!r}")
        try:
            start = ipaddress.ip_address(start_text.strip())
            end = ipaddress.ip_address(end_text.strip())
        except ValueError as exc:
            raise ValueError(f"invalid IPv4 address range: {part!r}") from exc
        if (not isinstance(start, ipaddress.IPv4Address)
                or not isinstance(end, ipaddress.IPv4Address)
                or int(start) > int(end)):
            raise ValueError(f"invalid IPv4 address range: {part!r}")
        summarized = tuple(ipaddress.summarize_address_range(start, end))
        networks.extend(parse_allowed_networks(summarized))
    normalized = parse_allowed_networks(networks)
    return tuple(map(str, normalized))


def is_authorized_target(
    value: object,
    allowed_networks: Iterable[str | ipaddress.IPv4Network],
) -> bool:
    """Pure scope check used immediately before every active probe."""
    try:
        address = ipaddress.ip_address(str(value))
        networks = parse_allowed_networks(allowed_networks)
    except ValueError:
        return False
    return bool(
        isinstance(address, ipaddress.IPv4Address)
        and address.is_private
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_unspecified
        and not address.is_reserved
        and any(address in network for network in networks)
    )


def ports_for_profile(profile: ScanProfile) -> Iterable[int]:
    """Return the TCP ports a profile covers; DEEP means every port."""
    if not isinstance(profile, ScanProfile):
        profile = ScanProfile(str(profile).lower())
    if profile is ScanProfile.TARGETED:
        return _TARGETED_TCP
    if profile is ScanProfile.ADVANCED:
        return _ADVANCED_TCP
    return range(1, 65536)


def normalize_custom_ports(values: Iterable[int] | None) -> tuple[int, ...]:
    """Validate a bounded custom TCP-port set without opening sockets."""
    if values is None:
        return ()
    ports: set[int] = set()
    for value in values:
        if isinstance(value, bool):
            raise ValueError(f"invalid TCP port: {value!r}")
        try:
            port = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid TCP port: {value!r}") from exc
        if str(port) != str(value).strip() or not 1 <= port <= 65535:
            raise ValueError(f"invalid TCP port: {value!r}")
        ports.add(port)
        if len(ports) > MAX_CUSTOM_PORTS:
            raise ValueError(
                f"custom TCP-port count exceeds {MAX_CUSTOM_PORTS}")
    return tuple(sorted(ports))


def parse_custom_port_spec(value: str) -> tuple[int, ...]:
    """Parse comma-separated ports/ranges into the bounded validator."""
    text = str(value or "").strip()
    if not text:
        return ()
    ports: list[int] = []
    for token in text.split(","):
        part = token.strip()
        if not part:
            raise ValueError("empty item in custom TCP-port list")
        if "-" not in part:
            ports.append(part)
            continue
        start_text, separator, end_text = part.partition("-")
        if not separator or not start_text.isdigit() or not end_text.isdigit():
            raise ValueError(f"invalid TCP-port range: {part!r}")
        start, end = int(start_text), int(end_text)
        if start > end:
            raise ValueError(f"TCP-port range is reversed: {part!r}")
        if end - start + 1 > MAX_CUSTOM_PORTS:
            raise ValueError(f"TCP-port range is too large: {part!r}")
        ports.extend(range(start, end + 1))
    return normalize_custom_ports(ports)


def _clean(data: bytes) -> str:
    """_clean."""
    text = data[:_MAX_RESPONSE].decode("utf-8", "replace")
    return "".join(
        char if char.isprintable() or char in "\r\n\t" else "."
        for char in text
    ).strip()
    """_clean."""
    """_clean."""


def _recv(sock: socket.socket, limit: int = _MAX_RESPONSE) -> bytes:
    """_recv."""
    remaining = min(_MAX_RESPONSE, max(0, int(limit)))
    chunks: list[bytes] = []
    while remaining:
        try:
            chunk = sock.recv(min(2048, remaining))
        except (OSError, TimeoutError):
            break
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
        if len(chunk) < 2048:
            break
    return b"".join(chunks)
    """_recv."""
    """_recv."""


def _product_version(text: str) -> tuple[str, str]:
    """_product_version."""
    for pattern in (
        r"^SSH-[\d.]+-([^\s/_]+)[_/-]?([\w.+-]*)",
        r"^220[- ]([^\s/]+)[ /]?([\w.+-]*)",
        r"^Server:\s*([^\s/]+)(?:/([\w.+-]+))?",
    ):
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1)[:120], (match.group(2) or "")[:80]
    return "", ""
    """_product_version."""
    """_product_version."""


def _service_from_banner(text: str) -> str:
    """Identify only unambiguous protocol greetings."""
    low = text.casefold().lstrip()
    if low.startswith("ssh-"):
        return "ssh"
    if low.startswith("http/"):
        return "http"
    if low.startswith("+pong") or "-noauth authentication" in low:
        return "redis"
    if low.startswith("rfb "):
        return "vnc"
    if low.startswith("220"):
        if "smtp" in low or "esmtp" in low:
            return "smtp"
        if "ftp" in low:
            return "ftp"
    if low.startswith("* ok") and "imap" in low:
        return "imap"
    if low.startswith("+ok") and "pop" in low:
        return "pop3"
    return ""


class _RateLimiter:
    """Spaces probe starts at most ``rate`` per second across worker threads."""

    def __init__(self, rate: float) -> None:
        """Initialize _ Rate Limiter."""
        self.interval = 1.0 / rate
        self.next_at = 0.0
        self.lock = threading.Lock()

    def acquire(self, cancel: threading.Event) -> bool:
        """Acquire."""
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_at - now)
            self.next_at = max(now, self.next_at) + self.interval
        return not cancel.wait(delay) if delay else not cancel.is_set()


class NetworkServiceScanner:
    """Scan explicit, authorized private IPv4 hosts with bounded resources."""

    def __init__(
        self,
        timeout: float = 0.6,
        workers: int = 32,
        rate_limit: float = 160.0,
    ) -> None:
        """Initialize Network Service Scanner."""
        self.timeout = min(_MAX_PROBE_TIMEOUT, max(0.05, float(timeout)))
        self.workers = min(64, max(1, int(workers)))
        self.rate_limit = min(500.0, max(1.0, float(rate_limit)))

    def scan(
        self,
        hosts: Iterable[str],
        allowed_networks: Iterable[str | ipaddress.IPv4Network],
        profile: ScanProfile,
        progress: ProgressFn | None = None,
        cancel_event: threading.Event | None = None,
        custom_ports: Iterable[int] | None = None,
    ) -> list[ServiceObservation]:
        """Return observations for authorized hosts and optional extra ports.

        Custom ports augment (rather than replace) the selected profile and are
        validated before any socket is created.
        """
        scopes = parse_allowed_networks(allowed_networks)
        selected = profile if isinstance(profile, ScanProfile) else ScanProfile(str(profile).lower())
        extra_ports = normalize_custom_ports(custom_ports)
        profile_ports = ports_for_profile(selected)
        if extra_ports and selected is not ScanProfile.DEEP:
            tcp_ports: Iterable[int] = tuple(sorted(
                set(profile_ports).union(extra_ports)))
        else:
            tcp_ports = profile_ports
        addresses: list[ipaddress.IPv4Address] = []
        for value in hosts:
            if is_authorized_target(value, scopes):
                addresses.append(ipaddress.IPv4Address(str(value)))
        addresses = sorted(set(addresses), key=int)
        cancel = cancel_event or threading.Event()
        if cancel.is_set() or not addresses:
            return []
        self._progress(progress, f"Scanning {len(addresses)} authorized private host(s)")
        observations: list[ServiceObservation] = []
        limiter = _RateLimiter(self.rate_limit)
        self._scan_tcp(
            addresses, selected, tcp_ports, limiter, cancel, observations,
            progress)
        if selected in {ScanProfile.ADVANCED, ScanProfile.DEEP} and not cancel.is_set():
            self._scan_udp(addresses, selected, limiter, cancel, observations)
        unique = {(item.ip, item.port, item.transport, item.name): item for item in observations}
        return sorted(unique.values(), key=lambda item: (
            int(ipaddress.IPv4Address(item.ip)), item.port, item.transport, item.name))

    @staticmethod
    def _progress(progress: ProgressFn | None, message: str) -> None:
        """_progress."""
        if progress:
            try:
                progress(message)
            except Exception:
                pass
        """_progress."""
        """_progress."""

    @staticmethod
    def _jobs(
        addresses: Iterable[ipaddress.IPv4Address],
        ports: Iterable[int],
    ) -> Iterator[tuple[str, int]]:
        """_jobs."""
        for address in addresses:
            for port in ports:
                yield str(address), port
        """_jobs."""
        """_jobs."""

    def _scan_tcp(
        self,
        addresses: list[ipaddress.IPv4Address],
        profile: ScanProfile,
        ports: Iterable[int],
        limiter: _RateLimiter,
        cancel: threading.Event,
        observations: list[ServiceObservation],
        progress: ProgressFn | None,
    ) -> None:
        """_scan_tcp."""
        jobs = self._jobs(addresses, ports)
        pending: set[Future[ServiceObservation | None]] = set()
        exhausted = False
        completed = 0
        with ThreadPoolExecutor(
            max_workers=self.workers, thread_name_prefix="cortex-private-lan"
        ) as pool:
            while not cancel.is_set() and (pending or not exhausted):
                while len(pending) < self.workers * 2 and not exhausted:
                    try:
                        ip, port = next(jobs)
                    except StopIteration:
                        exhausted = True
                        break
                    pending.add(pool.submit(
                        self._probe_tcp, ip, port, profile, limiter, cancel))
                if not pending:
                    break
                done, pending = wait(
                    pending, timeout=0.05, return_when=FIRST_COMPLETED)
                for future in done:
                    completed += 1
                    try:
                        item = future.result()
                    except (OSError, ValueError, ssl.SSLError):
                        item = None
                    if item is not None:
                        observations.append(item)
                    if completed % 512 == 0:
                        self._progress(progress, f"Completed {completed} TCP probes")
            if cancel.is_set():
                for future in pending:
                    future.cancel()
        """_scan_tcp."""
        """_scan_tcp."""

    def _probe_tcp(
        self,
        ip: str,
        port: int,
        profile: ScanProfile,
        limiter: _RateLimiter,
        cancel: threading.Event,
    ) -> ServiceObservation | None:
        """_probe_tcp."""
        if not limiter.acquire(cancel):
            return None
        started = time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        banner = b""
        try:
            sock.settimeout(self.timeout)
            if sock.connect_ex((ip, port)) != 0 or cancel.is_set():
                return None
            latency = round((time.monotonic() - started) * 1000, 2)
            # Read only after a connection succeeds. Many services (including
            # SSH, FTP and unknown high-port daemons) identify themselves
            # immediately; the bounded read never sends a command.
            banner = _recv(sock, 2048)
        finally:
            sock.close()
        observation = ServiceObservation(
            ip=ip,
            port=port,
            transport="tcp",
            name=_NAMES.get(port, "unknown"),
            source="tcp_connect",
            banner=_clean(banner),
            metadata={"evidence": ["TCP connection accepted"]},
            latency_ms=latency,
            confidence=0.55,
        )
        if banner:
            observation.metadata["evidence"].append("Passive greeting received")
            observation.product, observation.version = _product_version(observation.banner)
            identified = _service_from_banner(observation.banner)
            if identified:
                observation.name = identified
            observation.confidence = 0.85
        if cancel.is_set():
            return observation
        self._identify(observation, profile, cancel)
        return observation
        """_probe_tcp."""
        """_probe_tcp."""

    def _connect(self, observation: ServiceObservation) -> socket.socket:
        """_connect."""
        sock = socket.create_connection(
            (observation.ip, observation.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        return sock
        """_connect."""
        """_connect."""

    def _identify(
        self,
        observation: ServiceObservation,
        profile: ScanProfile,
        cancel: threading.Event,
    ) -> None:
        """_identify."""
        if observation.port in _TLS_PORTS and not cancel.is_set():
            self._probe_tls(observation)
        if (observation.port in _HTTP_PORTS or observation.port in _TLS_PORTS) and not cancel.is_set():
            self._probe_http(observation, "/version" if observation.port == 2375 else "/")
        elif (observation.name == "unknown"
              and profile in {ScanProfile.ADVANCED, ScanProfile.DEEP}
              and not cancel.is_set()):
            # One bounded HEAD request identifies web consoles on unusual ports.
            # It is attempted only after the port accepted a connection and did
            # not provide an unambiguous passive greeting.
            self._probe_http(observation, "/")
        if observation.port == 1883 and profile is not ScanProfile.TARGETED and not cancel.is_set():
            self._probe_mqtt(observation)
        if observation.port == 6379 and not cancel.is_set():
            self._probe_redis(observation)
        """_identify."""
        """_identify."""

    def _probe_tls(self, observation: ServiceObservation) -> None:
        """_probe_tls."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        try:
            with self._connect(observation) as raw:
                with context.wrap_socket(raw, server_hostname=observation.ip) as stream:
                    certificate = stream.getpeercert(binary_form=True) or b""
                    cipher = stream.cipher()
                    tls = {
                        "version": stream.version() or "",
                        "cipher": cipher[0] if cipher else "",
                        "certificate_sha256": hashlib.sha256(certificate).hexdigest() if certificate else "",
                        "certificate_verified": False,
                    }
                    observation.metadata["tls"] = tls
                    observation.metadata["evidence"].append("TLS handshake completed; certificate not verified")
                    observation.confidence = max(observation.confidence, 0.9)
        except (OSError, ValueError, ssl.SSLError):
            return
        """_probe_tls."""
        """_probe_tls."""

    def _probe_http(self, observation: ServiceObservation, path: str) -> None:
        """_probe_http."""
        try:
            with self._connect(observation) as raw:
                stream: socket.socket = raw
                wrapped: ssl.SSLSocket | None = None
                if observation.port in _TLS_PORTS:
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    wrapped = context.wrap_socket(raw, server_hostname=observation.ip)
                    stream = wrapped
                method = "GET" if observation.port in {2375, 9200} else "HEAD"
                request = (
                    f"{method} {path} HTTP/1.0\r\nHost: {observation.ip}\r\n"
                    "User-Agent: Cortex-Private-LAN-Audit/1\r\nConnection: close\r\n\r\n"
                ).encode("ascii")
                stream.sendall(request)
                data = _recv(stream)
                if wrapped is not None:
                    wrapped.close()
        except (OSError, ValueError, ssl.SSLError):
            return
        if not data:
            return
        text = _clean(data)
        lines = text.splitlines()
        status_line = lines[0] if lines else ""
        headers: dict[str, str] = {}
        for line in lines[1:]:
            key, separator, value = line.partition(":")
            if separator:
                headers[key.strip().lower()] = value.strip()[:512]
        observation.banner = text
        observation.name = "https" if observation.port in _TLS_PORTS else "http"
        docker_identified = (
            observation.port == 2375
            and any(marker in text for marker in ('"ApiVersion"', '"DockerRootDir"', 'Docker/'))
        )
        elasticsearch_identified = (
            observation.port == 9200
            and any(marker in text for marker in ('"cluster_name"', '"tagline"', 'You Know, for Search'))
        )
        if docker_identified:
            observation.name = "docker"
        elif elasticsearch_identified:
            observation.name = "elasticsearch"
        observation.metadata["http"] = {
            "status_line": status_line[:256],
            "headers": headers,
            "method": method,
        }
        observation.metadata["evidence"].append("Bounded HTTP response received")
        if docker_identified:
            observation.metadata["docker_api_unauthenticated"] = (
                status_line.startswith("HTTP/")
                and " 401" not in status_line
                and " 403" not in status_line
            )
        product, version = _product_version(text)
        observation.product = observation.product or product
        observation.version = observation.version or version
        observation.confidence = max(observation.confidence, 0.9)
        """_probe_http."""
        """_probe_http."""

    def _probe_mqtt(self, observation: ServiceObservation) -> None:
        """_probe_mqtt."""
        client_id = b"cortex-audit"
        body = b"\x00\x04MQTT\x04\x02\x00\x05" + struct.pack("!H", len(client_id)) + client_id
        try:
            with self._connect(observation) as sock:
                sock.sendall(bytes((0x10, len(body))) + body)
                reply = _recv(sock, 4)
        except OSError:
            return
        if len(reply) >= 4 and reply[:2] == b"\x20\x02":
            code = reply[3]
            observation.name = "mqtt"
            observation.metadata.update({
                "mqtt_connack": True,
                "mqtt_return_code": code,
                "mqtt_anonymous_accepted": code == 0,
            })
            observation.metadata["evidence"].append(
                f"MQTT CONNACK received for credential-free CONNECT (code {code})")
            observation.confidence = 0.98
        """_probe_mqtt."""
        """_probe_mqtt."""

    def _probe_redis(self, observation: ServiceObservation) -> None:
        """_probe_redis."""
        try:
            with self._connect(observation) as sock:
                sock.sendall(b"*1\r\n$4\r\nPING\r\n")
                reply = _recv(sock, 256)
        except OSError:
            return
        upper = reply.upper()
        if upper.startswith(b"+PONG"):
            observation.name = "redis"
            observation.metadata["redis_unauthenticated"] = True
            observation.metadata["evidence"].append("Redis PING returned PONG without credentials")
            observation.confidence = 0.98
        elif b"NOAUTH" in upper:
            observation.name = "redis"
            observation.metadata["redis_unauthenticated"] = False
            observation.metadata["evidence"].append("Redis required authentication")
            observation.confidence = 0.95
        """_probe_redis."""
        """_probe_redis."""

    def _scan_udp(
        self,
        addresses: Iterable[ipaddress.IPv4Address],
        profile: ScanProfile,
        limiter: _RateLimiter,
        cancel: threading.Event,
        observations: list[ServiceObservation],
    ) -> None:
        """_scan_udp."""
        probes = list(_UDP_PROBES)
        if profile in {ScanProfile.ADVANCED, ScanProfile.DEEP}:
            probes.append((161, "snmp", _SNMP_PROBE))
        for address in addresses:
            for port, name, payload in probes:
                if cancel.is_set() or not limiter.acquire(cancel):
                    return
                item = self._probe_udp(str(address), port, name, payload)
                if item is not None:
                    observations.append(item)
        """_scan_udp."""
        """_scan_udp."""

    def _probe_udp(
        self,
        ip: str,
        port: int,
        name: str,
        payload: bytes,
    ) -> ServiceObservation | None:
        """_probe_udp."""
        started = time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.settimeout(self.timeout)
            sock.sendto(payload, (ip, port))
            data, sender = sock.recvfrom(_MAX_RESPONSE)
        except (OSError, TimeoutError):
            return None
        finally:
            sock.close()
        if sender[0] != ip or not data:
            return None
        evidence = f"Unicast {name.upper()} response received from scoped host"
        metadata: dict[str, Any] = {"evidence": [evidence], "response_bytes": len(data)}
        if name == "snmp":
            metadata["snmp_public_response"] = True
            metadata["evidence"].append("SNMP response received to public-community read-only GET")
        return ServiceObservation(
            ip=ip,
            port=port,
            transport="udp",
            name=name,
            source="udp_response",
            banner=_clean(data),
            metadata=metadata,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
            confidence=0.95,
        )
        """_probe_udp."""
        """_probe_udp."""


# Compatibility name retained for callers that imported this helper directly.
def validate_private_target(target: str) -> str:
    """Validate private target."""
    private_ranges = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    if not is_authorized_target(target, private_ranges):
        raise ValueError(f"target is not a usable private IPv4 address: {target!r}")
    return str(ipaddress.IPv4Address(target))


def observation_json(observation: ServiceObservation) -> str:
    """Stable compact JSON, useful for inventory snapshots and tests."""
    return json.dumps(observation.to_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "NetworkServiceScanner",
    "ScanProfile",
    "ServiceObservation",
    "is_authorized_target",
    "observation_json",
    "parse_allowed_networks",
    "parse_network_scope_spec",
    "parse_custom_port_spec",
    "normalize_custom_ports",
    "ports_for_profile",
    "validate_private_target",
]
