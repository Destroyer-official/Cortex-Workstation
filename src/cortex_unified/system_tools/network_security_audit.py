"""Evidence-backed analysis for authorized private-LAN observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from cortex_unified.system_tools.network_service_scanner import ServiceObservation

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_VALID_SEVERITIES = frozenset(_SEVERITY_ORDER)


@dataclass(slots=True)
class SecurityFinding:
    """Security Finding data container."""
    code: str
    severity: str
    title: str
    detail: str
    remediation: str
    device_ip: str = ""
    evidence: list[str] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)
    confidence: float = 0.5
    port: int | None = None

    def __post_init__(self) -> None:
        self.severity = self.severity.lower()
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"unsupported finding severity: {self.severity!r}")
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        """__post_init__."""
        """__post_init__."""

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "code": self.code,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "remediation": self.remediation,
            "device_ip": self.device_ip,
            "evidence": list(self.evidence),
            "cve_ids": list(self.cve_ids),
            "confidence": round(self.confidence, 3),
            "port": self.port,
        }

    # Read-only compatibility properties for the previous audit API.
    @property
    def finding_id(self) -> str:
        """Finding id."""
        return self.code

    @property
    def description(self) -> str:
        """Description."""
        return self.detail

    @property
    def recommendation(self) -> str:
        """Recommendation."""
        return self.remediation

    @property
    def cve(self) -> str:
        """Cve."""
        return self.cve_ids[0] if self.cve_ids else ""


def _evidence(observation: ServiceObservation, extra: str = "") -> list[str]:
    values = observation.evidence
    if observation.banner:
        values.append(f"Bounded banner: {observation.banner[:300]}")
    if extra:
        values.append(extra)
    return list(dict.fromkeys(values))
    """_evidence."""
    """_evidence."""


def _finding(
    observation: ServiceObservation,
    code: str,
    severity: str,
    title: str,
    detail: str,
    remediation: str,
    confidence: float,
    extra: str = "",
) -> SecurityFinding:
    return SecurityFinding(
        code=code,
        severity=severity,
        title=title,
        detail=detail,
        remediation=remediation,
        device_ip=observation.ip,
        evidence=_evidence(observation, extra),
        confidence=confidence,
        port=observation.port,
    )
    """_finding."""
    """_finding."""


def _observation_findings(observation: ServiceObservation) -> list[SecurityFinding]:
    # ACK/firewall-map output and filtered/closed states are evidence, not an
    # open application service and must never trigger service-risk findings.
    if observation.state != "open":
        return []
    findings: list[SecurityFinding] = []
    name = observation.name.casefold()
    metadata = observation.metadata
    if name == "telnet" and observation.banner:
        findings.append(_finding(
            observation, "reachable-telnet", "high", "Reachable Telnet service",
            "A Telnet greeting was observed. Telnet does not encrypt credentials or sessions.",
            "Disable Telnet and use a protected management protocol such as SSH.", 0.9))
    if name == "ftp" and observation.banner.startswith("220"):
        findings.append(_finding(
            observation, "reachable-ftp", "medium", "Reachable cleartext FTP service",
            "An FTP greeting was observed; standard FTP does not protect credentials or content.",
            "Disable FTP or replace it with SFTP or correctly configured FTPS.", 0.9))

    http = metadata.get("http")
    if name == "http" and isinstance(http, Mapping):
        headers = http.get("headers", {})
        title = str(http.get("title", ""))
        server = str(headers.get("server", "")) if isinstance(headers, Mapping) else ""
        indicators = sorted({
            word for word in ("admin", "management", "configuration", "router", "gateway")
            if word in f"{title} {server}".casefold()
        })
        if indicators:
            findings.append(_finding(
                observation, "unencrypted-web-admin", "medium",
                "Unencrypted web administration interface",
                "Observed HTTP metadata identifies an administrative interface without TLS.",
                "Enable HTTPS-only management and restrict access to trusted hosts.", 0.85,
                f"Administrative indicators: {', '.join(indicators)}"))

    if name == "rdp":
        findings.append(_finding(
            observation, "reachable-rdp", "medium", "RDP port reachable on the LAN",
            "A TCP connection was accepted on the conventional RDP endpoint; "
            "this records exposure, not a vulnerability.",
            "Restrict RDP to trusted management hosts and require strong authentication.", 0.6))
    if name == "smb":
        findings.append(_finding(
            observation, "reachable-smb", "medium", "SMB port reachable on the LAN",
            "A TCP connection was accepted on the conventional SMB endpoint; no SMB weakness was inferred.",
            "Restrict SMB to trusted segments and disable obsolete dialects.", 0.6))

    advertised = metadata.get("services", ())
    adb_advertised = isinstance(advertised, (list, tuple, set)) and any(
        "_adb-tls-connect" in str(item).casefold() for item in advertised)
    if metadata.get("adb_cnxn_response") is True or adb_advertised:
        findings.append(_finding(
            observation, "wireless-adb", "high", "Wireless ADB advertised or reachable",
            "The device explicitly responded as ADB or advertised _adb-tls-connect over mDNS.",
            "Disable wireless debugging when not in use and revoke unneeded paired hosts.", 0.95,
            "mDNS _adb-tls-connect advertisement" if adb_advertised else "ADB CNXN response"))

    if (metadata.get("mqtt_connack") is True
            and metadata.get("mqtt_anonymous_accepted") is True
            and metadata.get("mqtt_return_code") == 0):
        findings.append(_finding(
            observation, "anonymous-mqtt", "high", "MQTT accepted an anonymous connection",
            "A credential-free MQTT CONNECT received a successful CONNACK; no publish or subscribe was attempted.",
            "Require authenticated clients, least-privilege ACLs, and TLS.", 0.99,
            "MQTT CONNACK return code 0 for credential-free CONNECT"))
    elif name == "mqtt" and observation.transport == "tcp" and observation.port == 1883:
        findings.append(_finding(
            observation, "cleartext-mqtt", "medium", "Cleartext MQTT endpoint reachable",
            "An MQTT protocol response was observed without transport encryption.",
            "Use MQTT over TLS and require client authentication.", 0.85))

    if metadata.get("redis_unauthenticated") is True:
        findings.append(_finding(
            observation, "unauthenticated-redis", "critical", "Redis accepted PING without authentication",
            "Redis returned PONG to a credential-free PING.",
            "Require authentication, bind to trusted interfaces, and enforce network access controls.", 0.99))
    if metadata.get("docker_api_unauthenticated") is True:
        findings.append(_finding(
            observation, "exposed-docker-api", "critical", "Docker API responded without authentication",
            "The Docker HTTP API returned a non-authentication response to a read-only version request.",
            "Disable unauthenticated TCP access and use mutually authenticated TLS or a local socket.", 0.98))
    if metadata.get("snmp_public_response") is True:
        findings.append(_finding(
            observation, "snmp-public-response", "high", "SNMP public community responded",
            "The endpoint answered a read-only SNMP GET using the public community string.",
            "Change the community, restrict source addresses, or migrate to authenticated SNMPv3.", 0.99))

    tls = metadata.get("tls")
    if isinstance(tls, Mapping):
        version = str(tls.get("version", "")).upper()
        cipher = str(tls.get("cipher", "")).upper()
        weak_reasons = []
        if version in {"SSLV2", "SSLV3", "TLSV1", "TLSV1.0", "TLSV1.1"}:
            weak_reasons.append(f"legacy protocol {version}")
        if any(marker in cipher for marker in ("RC4", "3DES", "DES-", "NULL", "EXPORT", "MD5")):
            weak_reasons.append(f"weak cipher {cipher}")
        if weak_reasons:
            findings.append(_finding(
                observation, "weak-tls", "high", "Weak TLS negotiation observed",
                "A completed TLS handshake negotiated a legacy protocol or weak cipher.",
                "Disable legacy TLS versions and weak ciphers.", 0.98,
                "; ".join(weak_reasons)))
    return findings
    """_observation_findings."""
    """_observation_findings."""


def analyze_services(
    services: Iterable[ServiceObservation],
    catalog: Any | None = None,
) -> tuple[Any, list[SecurityFinding]]:
    """Compatibility analysis entry point returning fingerprint and findings."""
    from cortex_unified.system_tools.device_fingerprint import fingerprint_device

    observations = list(services)
    fingerprint = fingerprint_device(observations)
    findings = [item for observation in observations for item in _observation_findings(observation)]
    if catalog is not None and fingerprint.product and fingerprint.version:
        matches = catalog.match(fingerprint.product, fingerprint.version)
        for advisory in matches:
            findings.append(advisory.to_finding(
                observations[0].ip if observations else "",
                [f"Observed product/version: {fingerprint.product} {fingerprint.version}"],
            ))
    return fingerprint, _deduplicate(findings)


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)
    """_get."""
    """_get."""


def _device_observations(device: Any) -> list[ServiceObservation]:
    for name in ("service_observations", "observations", "scanned_services"):
        values = _get(device, name, None)
        if values is not None:
            return [item for item in values if isinstance(item, ServiceObservation)]
    services = _get(device, "services", ())
    if isinstance(services, Iterable) and not isinstance(services, (str, bytes, Mapping)):
        return [item for item in services if isinstance(item, ServiceObservation)]
    return []
    """_device_observations."""
    """_device_observations."""


def _deduplicate(findings: Iterable[SecurityFinding]) -> list[SecurityFinding]:
    unique: dict[tuple[str, str, int | None], SecurityFinding] = {}
    for finding in findings:
        key = (finding.code, finding.device_ip, finding.port)
        current = unique.get(key)
        if current is None or finding.confidence > current.confidence:
            unique[key] = finding
    return sorted(unique.values(), key=lambda item: (
        _SEVERITY_ORDER[item.severity], item.device_ip, item.code, item.port or 0))
    """_deduplicate."""
    """_deduplicate."""


def audit_devices(
    devices: Iterable[Any], vulnerability_catalog: Any | None = None,
) -> list[SecurityFinding]:
    """Analyze supplied evidence only; this function performs no network I/O."""
    findings: list[SecurityFinding] = []
    for device in devices:
        observations = _device_observations(device)
        device_ip = str(_get(device, "ip", ""))
        services = _get(device, "services", {})
        if isinstance(services, Mapping) and any(
            "_adb-tls-connect" in str(name).casefold() for name in services
        ):
            observations.append(ServiceObservation(
                ip=device_ip,
                port=5353,
                transport="udp",
                name="mdns",
                source="device_discovery",
                metadata={
                    "services": [name for name in services if "_adb-tls-connect" in str(name).casefold()],
                    "evidence": ["mDNS service advertisement recorded by discovery"],
                },
                confidence=0.95,
            ))
        device_kind = str(_get(device, "kind", "")).casefold()
        has_web_admin = any(
            item.name in {"http", "https"}
            and isinstance(item.metadata.get("http"), Mapping)
            for item in observations)
        credential_review_types = (
            "router", "gateway", "camera", "printer", "iot",
            "smart home", "network equipment",
        )
        if has_web_admin and any(
                label in device_kind for label in credential_review_types):
            findings.append(SecurityFinding(
                code="default-credential-review",
                severity="info",
                title="Review factory/default administrative credentials",
                detail=(
                    "A management-capable interface was observed on a device "
                    "type commonly shipped with initial credentials. No login "
                    "or credential attempt was made."),
                remediation=(
                    "Confirm the device uses a unique strong administrator "
                    "credential and disable unused remote administration."),
                device_ip=device_ip,
                evidence=[
                    f"Evidence-based device classification: {device_kind}",
                    "Observed HTTP(S) response from the device",
                    "No authentication attempt was performed",
                ],
                confidence=0.65,
            ))
        if vulnerability_catalog is not None:
            for observation in observations:
                if not observation.product or not observation.version:
                    continue
                evidence = list(observation.evidence) + [
                    "Exact observed product/version string: "
                    f"{observation.product} {observation.version}",
                    "Potential advisory match; exploitability was not tested",
                ]
                matches = vulnerability_catalog.correlate(
                    observation.product, observation.version, evidence)
                for match in matches:
                    match.device_ip = device_ip
                findings.extend(matches)
        findings.extend(
            item for observation in observations for item in _observation_findings(observation))
    return _deduplicate(findings)


def audit_wan(wan_status: Any) -> list[SecurityFinding]:
    """Report enabled IGD mappings as exposure observations, never connectivity tests."""
    findings: list[SecurityFinding] = []
    gateway = str(_get(wan_status, "gateway", ""))
    for mapping in (_get(wan_status, "port_mappings", ()) or ()):
        enabled = bool(_get(mapping, "enabled", False))
        if not enabled:
            continue
        external = _get(mapping, "external_port", 0)
        protocol = str(_get(mapping, "protocol", "unknown"))
        findings.append(SecurityFinding(
            code="enabled-wan-port-mapping",
            severity="info",
            title="Enabled WAN port mapping reported by gateway",
            detail=(
                f"The local IGD reports an enabled {protocol} mapping on external port "
                f"{external}. Connectivity from the Internet was not tested."
            ),
            remediation="Confirm the mapping is expected and remove it through the router if unnecessary.",
            device_ip=gateway,
            evidence=["Read-only UPnP GetGenericPortMappingEntry response"],
            confidence=0.9,
            port=int(external) if str(external).isdigit() else None,
        ))
    return _deduplicate(findings)


__all__ = ["SecurityFinding", "analyze_services", "audit_devices", "audit_wan"]
