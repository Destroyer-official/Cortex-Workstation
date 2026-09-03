"""Explicit, read-only exposure lookup for a router-reported public IPv4."""

from __future__ import annotations

import base64
import ipaddress
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

_MAX_RESPONSE = 2 * 1024 * 1024
Transport = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]


class ExposureLookupError(RuntimeError):
    """Raised for invalid consent, target, credentials, or provider output."""


@dataclass(frozen=True, slots=True)
class ExternalService:
    """External Service data container."""
    port: int
    transport: str = "tcp"
    product: str = ""
    version: str = ""
    source: str = ""
    evidence: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "port": self.port, "transport": self.transport,
            "product": self.product, "version": self.version,
            "source": self.source, "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class ExposureResult:
    """Exposure Result data container."""
    provider: str
    public_ip: str
    services: tuple[ExternalService, ...]
    last_observed: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "provider": self.provider, "public_ip": self.public_ip,
            "services": [item.to_dict() for item in self.services],
            "last_observed": self.last_observed,
            "connectivity_tested": False,
            "notice": (
                "Provider index data is historical observation, not a live "
                "reachability or vulnerability test."),
        }


def _public_ipv4(value: str) -> str:
    """_public_ipv4."""
    try:
        address = ipaddress.ip_address(str(value))
    except ValueError as exc:
        raise ExposureLookupError(
            "external exposure target is not an IP") from exc
    if not isinstance(address, ipaddress.IPv4Address) or not address.is_global:
        raise ExposureLookupError(
            "external exposure lookup requires a globally routable IPv4")
    return str(address)
    """_public_ipv4."""
    """_public_ipv4."""


def _default_transport(
    url: str, headers: Mapping[str, str], timeout: float,
) -> Mapping[str, Any]:
    """_default_transport."""
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > _MAX_RESPONSE:
                raise ExposureLookupError(
                    "provider response exceeds size limit")
            payload = response.read(_MAX_RESPONSE + 1)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise ExposureLookupError(
            "external exposure provider request failed") from exc
    if len(payload) > _MAX_RESPONSE:
        raise ExposureLookupError("provider response exceeds size limit")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ExposureLookupError("provider returned invalid JSON") from exc
    if not isinstance(value, Mapping):
        raise ExposureLookupError("provider response must be an object")
    return value
    """_default_transport."""
    """_default_transport."""


class ExternalExposureClient:
    """Opt-in Shodan/Censys host lookup with an injectable transport."""

    def __init__(
        self, provider: str, api_key: str, api_secret: str = "",
        transport: Transport | None = None,
    ) -> None:
        """Initialize External Exposure Client."""
        self.provider = provider.strip().lower()
        if self.provider not in {"shodan", "censys"}:
            raise ValueError("provider must be shodan or censys")
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        if not self.api_key:
            raise ValueError("provider API credentials are required")
        if self.provider == "censys" and not self.api_secret:
            raise ValueError("Censys API ID and secret are required")
        self._transport = transport or _default_transport

    def lookup(
        self, public_ip: str, *, consent: bool = False, timeout: float = 10.0,
    ) -> ExposureResult:
        """Lookup."""
        if not consent:
            raise ExposureLookupError(
                "explicit external lookup consent is required")
        address = _public_ipv4(public_ip)
        timeout = min(30.0, max(1.0, float(timeout)))
        if self.provider == "shodan":
            encoded = urllib.parse.quote(address, safe="")
            key = urllib.parse.quote(self.api_key, safe="")
            url = f"https://api.shodan.io/shodan/host/{encoded}?key={key}"
            payload = self._transport(
                url, {"Accept": "application/json"}, timeout)
            services = self._parse_shodan(payload)
            last_observed = str(payload.get("last_update", ""))[:64]
        else:
            encoded = urllib.parse.quote(address, safe="")
            url = f"https://search.censys.io/api/v2/hosts/{encoded}"
            token = base64.b64encode(
                f"{self.api_key}:{self.api_secret}".encode()).decode("ascii")
            payload = self._transport(
                url, {"Accept": "application/json",
                      "Authorization": f"Basic {token}"}, timeout)
            services, last_observed = self._parse_censys(payload)
        return ExposureResult(
            self.provider, address, tuple(services), last_observed)

    @staticmethod
    def _parse_shodan(payload: Mapping[str, Any]) -> list[ExternalService]:
        """_parse_shodan."""
        services = []
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise ExposureLookupError("invalid Shodan host response")
        for item in data[:4096]:
            if not isinstance(item, Mapping):
                continue
            try:
                port = int(item.get("port"))
            except (TypeError, ValueError):
                continue
            if not 1 <= port <= 65535:
                continue
            transport = str(item.get("transport", "tcp"))[:8].lower()
            product = str(item.get("product", ""))[:160]
            version = str(item.get("version", ""))[:80]
            services.append(ExternalService(
                port, transport, product, version, "shodan",
                ("Shodan host-index observation",)))
        return _deduplicate(services)
        """_parse_shodan."""
        """_parse_shodan."""

    @staticmethod
    def _parse_censys(
        payload: Mapping[str, Any],
    ) -> tuple[list[ExternalService], str]:
        """_parse_censys."""
        result = payload.get("result", {})
        if not isinstance(result, Mapping):
            raise ExposureLookupError("invalid Censys host response")
        raw_services = result.get("services", [])
        if not isinstance(raw_services, list):
            raise ExposureLookupError("invalid Censys services response")
        services = []
        for item in raw_services[:4096]:
            if not isinstance(item, Mapping):
                continue
            try:
                port = int(item.get("port"))
            except (TypeError, ValueError):
                continue
            if not 1 <= port <= 65535:
                continue
            software = item.get("software", [])
            product = version = ""
            if isinstance(software, list) and software:
                first = software[0]
                if isinstance(first, Mapping):
                    product = str(first.get("product", ""))[:160]
                    version = str(first.get("version", ""))[:80]
            services.append(ExternalService(
                port, str(item.get("transport_protocol", "tcp"))[:8].lower(),
                product, version, "censys",
                ("Censys host-index observation",)))
        observed = str(result.get("last_updated_at", ""))[:64]
        return _deduplicate(services), observed
        """_parse_censys."""
        """_parse_censys."""


def _deduplicate(values: list[ExternalService]) -> list[ExternalService]:
    """_deduplicate."""
    unique = {
        (item.port, item.transport, item.product, item.version): item
        for item in values
    }
    return sorted(unique.values(), key=lambda item: (
        item.port, item.transport, item.product, item.version))
    """_deduplicate."""
    """_deduplicate."""


__all__ = [
    "ExposureLookupError", "ExposureResult", "ExternalExposureClient",
    "ExternalService",
]
