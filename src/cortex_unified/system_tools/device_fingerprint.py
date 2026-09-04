"""Pure, conservative device fingerprinting from observed LAN evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from cortex_unified.system_tools.network_service_scanner import ServiceObservation


@dataclass(frozen=True, slots=True)
class FingerprintEvidence:
    """Fingerprintevidence.

    Manages FingerprintEvidence operations and coordinates related state changes for the component.
    """
    source: str
    value: str
    strength: str = "weak"
    weight: float = 0.2
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "source": self.source,
            "value": self.value,
            "strength": self.strength,
            "weight": round(max(0.0, min(1.0, self.weight)), 3),
            "detail": self.detail,
        }


@dataclass(slots=True)
class DeviceFingerprint:
    """Devicefingerprint.

    Manages DeviceFingerprint operations and coordinates related state changes for the component.
    """
    os_family: str = "unknown"
    device_type: str = "unknown"
    confidence: float = 0.0
    evidence: list[FingerprintEvidence] = field(default_factory=list)
    product: str = ""
    version: str = ""
    alternatives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "os_family": self.os_family,
            "device_type": self.device_type,
            "confidence": round(max(0.0, min(1.0, self.confidence)), 3),
            "evidence": [item.to_dict() for item in self.evidence],
            "product": self.product,
            "version": self.version,
            "alternatives": list(self.alternatives),
        }


_VERSION_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+){1,3}(?:[-+._a-zA-Z0-9]*)?)")
_TYPE_TERMS = (
    (("printer", "_ipp", "jetdirect"), "printer"),
    (("camera", "hikvision", "onvif"), "camera"),
    (("android", "_adb"), "mobile device"),
    (("router", "gateway", "openwrt"), "router / gateway"),
    (("nas", "synology", "qnap"), "NAS"),
    (("chromecast", "googlecast", "roku"), "TV / streaming device"),
    (("mqtt", "espressif", "home assistant"), "IoT device"),
)
_OS_TERMS = (
    (("windows", "microsoft-httpapi", "rdp"), "Windows"),
    (("android", "_adb"), "Android"),
    (("darwin", "macos", "airplay"), "Apple"),
    (("linux", "ubuntu", "debian", "openwrt"), "Linux"),
)


def _get(value: Any, name: str, default: Any = None) -> Any:
    """Get.

    Manages get operations and coordinates related state changes for the component.

    Args:
        value (Any): The value parameter.
        name (str): The name parameter.
        default (Any): The default parameter.

    Returns:
        Any: Result of the operation.
    """
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _observations(device: Any) -> list[ServiceObservation]:
    """Observations.

    Manages observations operations and coordinates related state changes for the component.

    Args:
        device (Any): The device parameter.

    Returns:
        list[ServiceObservation]: List of processed items or identifiers.
    """
    if isinstance(device, ServiceObservation):
        return [device]
    if isinstance(device, Iterable) and not isinstance(device, (str, bytes, Mapping)):
        values = list(device)
        if all(isinstance(item, ServiceObservation) for item in values):
            return values
    for name in ("service_observations", "observations", "scanned_services"):
        values = _get(device, name, None)
        if values is not None:
            return [item for item in values if isinstance(item, ServiceObservation)]
    raw = _get(device, "services", ())
    if isinstance(raw, Iterable) and not isinstance(raw, (str, bytes, Mapping)):
        return [item for item in raw if isinstance(item, ServiceObservation)]
    return []


def _add(
    evidence: list[FingerprintEvidence],
    source: str,
    value: Any,
    strength: str,
    weight: float,
    detail: str,
) -> None:
    """Add.

    Manages add operations and coordinates related state changes for the component.

    Args:
        evidence (list[FingerprintEvidence]): The evidence parameter.
        source (str): Filesystem path to the target file or directory.
        value (Any): The value parameter.
        strength (str): The strength parameter.
        weight (float): The weight parameter.
        detail (str): The detail parameter.
    """
    text = str(value or "").strip()
    if text:
        evidence.append(FingerprintEvidence(
            source=source[:200], value=text[:512], strength=strength,
            weight=weight, detail=detail[:512]))


def _collect(device: Any, observations: list[ServiceObservation]) -> list[FingerprintEvidence]:
    """Aggregate discovered files or telemetry metrics into collections.

    Iterates over raw subsystem records, filters excluded paths, and collates findings into a structured report list.

    Args:
        device (Any): The device parameter.
        observations (list[ServiceObservation]): The observations parameter.

    Returns:
        list[FingerprintEvidence]: List of processed items or identifiers.
    """
    evidence: list[FingerprintEvidence] = []
    _add(evidence, "vendor", _get(device, "vendor", ""), "medium", 0.5,
         "Vendor was resolved or reported by discovery")
    _add(evidence, "hostname", _get(device, "hostname", ""), "weak", 0.2,
         "Hostnames can be user-controlled")
    services = _get(device, "services", {})
    if isinstance(services, Mapping):
        for key, value in sorted(services.items(), key=lambda item: str(item[0])):
            _add(evidence, f"advertised service {key}", f"{key} {value}".strip(),
                 "medium", 0.55, "Service was advertised by the device")
    for observation in observations:
        prefix = f"{observation.transport}/{observation.port}"
        if observation.banner:
            _add(evidence, f"{prefix} banner", observation.banner, "strong", 0.75,
                 "Protocol peer supplied a bounded banner")
        if observation.product:
            value = f"{observation.product} {observation.version}".strip()
            _add(evidence, f"{prefix} product", value, "strong", 0.85,
                 "Protocol metadata identified a product")
        http = observation.metadata.get("http")
        if isinstance(http, Mapping):
            headers = http.get("headers", {})
            server = headers.get("server", "") if isinstance(headers, Mapping) else ""
            _add(evidence, f"{prefix} HTTP Server", server, "medium", 0.5,
                 "Self-reported HTTP Server header")
        advertised = observation.metadata.get("services", ())
        if isinstance(advertised, (list, tuple, set)):
            for item in advertised:
                _add(evidence, f"{prefix} advertisement", item, "medium", 0.6,
                     "Service advertisement was observed")
    return evidence


def _rank(text: str, rules: tuple[tuple[tuple[str, ...], str], ...]) -> list[tuple[str, float]]:
    """Rank.

    Manages rank operations and coordinates related state changes for the component.

    Args:
        text (str): Display text string.
        rules (tuple[tuple[tuple[str, ...], str], ...]): The rules parameter.

    Returns:
        list[tuple[str, float]]: List of processed items or identifiers.
    """
    scores: dict[str, float] = {}
    lowered = text.casefold()
    for terms, label in rules:
        matches = sum(term in lowered for term in terms)
        if matches:
            scores[label] = min(1.0, 0.35 + 0.2 * matches)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def _product_version(evidence: Iterable[FingerprintEvidence]) -> tuple[str, str]:
    """_product_version.

    Manages product version operations and coordinates related state changes for the component.

    Args:
        evidence (Iterable[FingerprintEvidence]): The evidence parameter.

    Returns:
        tuple[str, str]: Formatted string or path.
    """
    candidates = sorted(
        (item for item in evidence if item.strength in {"strong", "medium"}),
        key=lambda item: item.weight,
        reverse=True,
    )
    for item in candidates:
        match = _VERSION_RE.search(item.value)
        if match:
            product = item.value[:match.start()].strip(" /_-")
            product = re.sub(r"^(SSH-[\d.]+-|220\s*)", "", product,
                             flags=re.IGNORECASE).strip()
            if product:
                return product[:200], match.group(1)[:100]
    return "", ""


def fingerprint_device(device: Any) -> DeviceFingerprint:
    """Combine duck-typed discovery data and observations without certainty from ports.

    Manages fingerprint device operations and coordinates related state changes for the component.

    Args:
        device (Any): The device parameter.

    Returns:
        DeviceFingerprint: Result of the operation.
    """
    observations = _observations(device)
    evidence = _collect(device, observations)
    evidence_text = " ".join(item.value for item in evidence)
    type_rank = _rank(evidence_text, _TYPE_TERMS)
    os_rank = _rank(evidence_text, _OS_TERMS)

    # Open-port-only hints are intentionally weak and never establish certainty.
    open_ports = set(_get(device, "open_ports", ()) or ())
    open_ports.update(item.port for item in observations)
    weak_type = ""
    if _get(device, "is_gateway", False):
        weak_type = "router / gateway"
        _add(evidence, "discovery role", "default gateway", "strong", 0.9,
             "Discovery identified this address as the default gateway")
        type_rank = [(weak_type, 0.9)] + [item for item in type_rank if item[0] != weak_type]
    elif {631, 9100} & open_ports:
        weak_type = "printer"
    elif 5555 in open_ports:
        weak_type = "mobile device"
    elif {445, 3389} & open_ports:
        weak_type = "computer"

    device_type = type_rank[0][0] if type_rank else weak_type or "unknown"
    os_family = os_rank[0][0] if os_rank else "unknown"
    independent = len({item.source for item in evidence})
    evidence_weight = sum(item.weight for item in evidence)
    confidence = min(0.95, evidence_weight / (evidence_weight + 1.25)) if evidence else 0.0
    if independent < 2:
        confidence = min(confidence, 0.65)
    if not evidence and weak_type:
        confidence = 0.2
    product, version = _product_version(evidence)
    alternatives = [label for label, _score in type_rank[1:4]]
    return DeviceFingerprint(
        os_family=os_family,
        device_type=device_type,
        confidence=round(confidence, 3),
        evidence=evidence,
        product=product,
        version=version,
        alternatives=alternatives,
    )


__all__ = ["DeviceFingerprint", "FingerprintEvidence", "fingerprint_device"]
