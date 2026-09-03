"""Persistent, point-in-time network inventory with typed change reporting.

This module performs no discovery and starts no background work.  Callers pass
completed observations explicitly; each call is committed atomically to a
bounded SQLite history.  Device identity is necessarily probabilistic because
DHCP can move addresses and modern clients intentionally randomize MACs.
"""

from __future__ import annotations

import csv
import datetime as dt
import ipaddress
import json
import math
import re
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

_SCHEMA_VERSION = 2
_SEVERITIES = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_TRUST_STATES = {"unknown", "trusted", "guest", "blocked"}
_FORMULA_PREFIXES = ("=", "+", "-", "@")
_MAC_RE = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")
_MAX_DEVICES = 4096
_MAX_ITEMS_PER_DEVICE = 1024


def _text(value: Any, limit: int = 512) -> str:
    return str(value or "").strip()[:limit]
    """_text."""
    """_text."""


def _json_safe(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "<depth-limit>"
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {
            _text(key, 128): _json_safe(item, depth + 1)
            for key, item in list(value.items())[:256]
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item, depth + 1) for item in list(value)[:256]]
    return _text(value, 1024)
    """_json_safe."""
    """_json_safe."""


@dataclass(slots=True, frozen=True)
class InventoryService:
    """Inventory Service data container."""
    name: str
    port: int | None = None
    protocol: str = "tcp"
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Key."""
        return f"{self.protocol.lower()}:{self.port or 0}:{self.name.lower()}"

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "name": self.name,
            "port": self.port,
            "protocol": self.protocol,
            "details": _json_safe(self.details),
        }


@dataclass(slots=True, frozen=True)
class InventoryFinding:
    """Inventory Finding data container."""
    code: str
    title: str
    severity: str = "info"
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Key."""
        return self.code.lower() or self.title.lower()

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "code": self.code,
            "title": self.title,
            "severity": self.severity,
            "details": _json_safe(self.details),
        }


@dataclass(slots=True, frozen=True)
class InventoryDevice:
    """Inventory Device data container."""
    ip: str
    mac: str = ""
    hostname: str = ""
    vendor: str = ""
    services: tuple[InventoryService, ...] = ()
    findings: tuple[InventoryFinding, ...] = ()
    device_id: str = ""
    is_gateway: bool = False

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "ip": self.ip,
            "mac": self.mac,
            "hostname": self.hostname,
            "vendor": self.vendor,
            "services": [item.to_dict() for item in self.services],
            "findings": [item.to_dict() for item in self.findings],
            "device_id": self.device_id,
            "is_gateway": self.is_gateway,
        }


@dataclass(slots=True, frozen=True)
class DeviceMetadata:
    """Device Metadata data container."""
    identity_key: str
    custom_name: str = ""
    trust_state: str = "unknown"
    tags: tuple[str, ...] = ()
    notes: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "identity_key": self.identity_key,
            "custom_name": self.custom_name,
            "trust_state": self.trust_state,
            "tags": list(self.tags),
            "notes": self.notes,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True, frozen=True)
class InventoryChange:
    """Inventory Change data container."""
    kind: str
    device_id: str
    severity: str
    message: str
    previous: Any = None
    current: Any = None
    identity_confidence: str = "high"

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        result = asdict(self)
        result["previous"] = _json_safe(self.previous)
        result["current"] = _json_safe(self.current)
        return result


@dataclass(slots=True)
class InventoryChanges:
    """Inventory Changes data container."""
    new_devices: list[InventoryChange] = field(default_factory=list)
    changed_addresses: list[InventoryChange] = field(default_factory=list)
    new_services: list[InventoryChange] = field(default_factory=list)
    new_findings: list[InventoryChange] = field(default_factory=list)
    severity_changes: list[InventoryChange] = field(default_factory=list)
    disappeared_devices: list[InventoryChange] = field(default_factory=list)
    gateway_mac_changes: list[InventoryChange] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "new_devices": [item.to_dict() for item in self.new_devices],
            "changed_addresses": [item.to_dict() for item in self.changed_addresses],
            "new_services": [item.to_dict() for item in self.new_services],
            "new_findings": [item.to_dict() for item in self.new_findings],
            "severity_changes": [item.to_dict() for item in self.severity_changes],
            "disappeared_devices": [
                item.to_dict() for item in self.disappeared_devices],
            "gateway_mac_changes": [item.to_dict() for item in self.gateway_mac_changes],
        }


@dataclass(slots=True)
class InventorySnapshot:
    """Inventory Snapshot data container."""
    snapshot_id: int
    observed_at: str
    devices: list[InventoryDevice]
    changes: list[InventoryChange]
    gateway_mac: str = ""
    identity_notice: str = (
        "Identity is best-effort: DHCP can change IP addresses and privacy "
        "features can randomize MAC addresses, so low-confidence changes may "
        "represent the same physical device."
    )

    def to_dict(self) -> dict[str, Any]:
        """To dict."""
        return {
            "snapshot_id": self.snapshot_id,
            "observed_at": self.observed_at,
            "devices": [device.to_dict() for device in self.devices],
            "changes": [change.to_dict() for change in self.changes],
            "gateway_mac": self.gateway_mac,
            "identity_notice": self.identity_notice,
        }


def _normalize_mac(value: Any) -> str:
    mac = _text(value, 32).lower().replace("-", ":")
    return mac if _MAC_RE.fullmatch(mac) else ""
    """_normalize_mac."""
    """_normalize_mac."""


def _randomized_mac(mac: str) -> bool:
    if not mac:
        return False
    first = int(mac.split(":", 1)[0], 16)
    return bool(first & 0x02) and not bool(first & 0x01)
    """_randomized_mac."""
    """_randomized_mac."""


def _identity(device: InventoryDevice) -> tuple[str, str]:
    if device.device_id:
        return f"id:{device.device_id}", "high"
    if device.mac and not _randomized_mac(device.mac):
        return f"mac:{device.mac}", "high"
    # IP identity is deliberately labelled low confidence: DHCP leases move,
    # and a randomized MAC may change each time the client joins.
    return f"ip:{device.ip}", "low"
    """_identity."""
    """_identity."""


def _service(value: Any) -> InventoryService:
    if isinstance(value, InventoryService):
        return value
    if isinstance(value, int):
        return InventoryService(name=f"port-{value}", port=value)
    if isinstance(value, str):
        return InventoryService(name=_text(value, 256))
    if isinstance(value, Mapping):
        raw_port = value.get("port")
        try:
            port = int(raw_port) if raw_port is not None else None
        except (TypeError, ValueError):
            port = None
        if port is not None and not 1 <= port <= 65535:
            port = None
        return InventoryService(
            name=_text(value.get("name") or value.get(
                "service") or "service", 256),
            port=port,
            protocol=_text(value.get("protocol") or value.get("transport") or "tcp", 16).lower(),
            details=_json_safe(value.get("details") or value.get("metadata") or {}),
        )
    raw_port = getattr(value, "port", None)
    name = getattr(value, "name", getattr(value, "service", ""))
    if name:
        try:
            port = int(raw_port) if raw_port is not None else None
        except (TypeError, ValueError):
            port = None
        return InventoryService(
            name=_text(name, 256),
            port=port if port is not None and 1 <= port <= 65535 else None,
            protocol=_text(getattr(value, "transport", "tcp"), 16).lower(),
            details=_json_safe(getattr(value, "metadata", {})),
        )
    raise TypeError(
        "service entries must be strings, integers, mappings, observations, or InventoryService"
    )
    """_service."""
    """_service."""


def _finding(value: Any) -> InventoryFinding:
    if isinstance(value, InventoryFinding):
        return value
    if (not isinstance(value, Mapping)
            and not _get(value, "code", "")
            and not _get(value, "title", "")):
        raise TypeError("finding entries must be mappings or finding objects")
    severity = _text(_get(value, "severity", "info") or "info", 16).lower()
    if severity not in _SEVERITIES:
        severity = "info"
    title = _text(_get(value, "title", "") or _get(value, "message", "") or "Finding", 512)
    details = _get(value, "details", None)
    if details is None and hasattr(value, "to_dict"):
        details = value.to_dict()
    return InventoryFinding(
        code=_text(_get(value, "code", "") or title, 128),
        title=title,
        severity=severity,
        details=_json_safe(details or {}),
    )
    """_finding."""
    """_finding."""


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(
        value, Mapping) else getattr(value, name, default)
    """_get."""
    """_get."""


def normalize_device(value: Any) -> InventoryDevice:
    """Normalize mappings or discovery objects into a validated observation."""
    if isinstance(value, InventoryDevice):
        return value
    ip = _text(_get(value, "ip"), 64)
    try:
        ip = str(ipaddress.ip_address(ip))
    except ValueError as exc:
        raise ValueError(f"invalid device IP address: {ip!r}") from exc
    raw_services = _get(value, "services", ()) or ()
    services: list[InventoryService] = []
    if isinstance(raw_services, Mapping):
        services.extend(
            InventoryService(
                name=_text(
                    name, 256), details={
                    "value": _json_safe(detail)})
            for name, detail in raw_services.items())
    else:
        services.extend(_service(item) for item in raw_services)
    for attribute in ("service_observations", "observations", "scanned_services"):
        for item in (_get(value, attribute, ()) or ()):
            services.append(_service(item))
    for port in (_get(value, "open_ports", ()) or ()):
        services.append(_service(port))
    findings = tuple(_finding(item)
                     for item in (_get(value, "findings", ()) or ()))
    unique_services = {
        item.key: item for item in services[:_MAX_ITEMS_PER_DEVICE]}
    unique_findings = {
        item.key: item for item in findings[:_MAX_ITEMS_PER_DEVICE]}
    return InventoryDevice(
        ip=ip,
        mac=_normalize_mac(_get(value, "mac")),
        hostname=_text(_get(value, "hostname"), 255),
        vendor=_text(_get(value, "vendor"), 255),
        services=tuple(unique_services.values()),
        findings=tuple(unique_findings.values()),
        device_id=_text(_get(value, "device_id"), 255),
        is_gateway=bool(_get(value, "is_gateway", False)),
    )


def identity_key_for(value: Any) -> str:
    """Return the same stable/best-effort identity key used by inventory."""
    return _identity(normalize_device(value))[0]


class NetworkInventory:
    """SQLite inventory with all writes in explicit transactions."""

    def __init__(
        self,
        path: str | Path | None = None,
        retention: int = 50,
    ) -> None:
        """Initialize Network Inventory."""
        if path is None:
            path = Path.home() / ".cortex_cleaner" / "netdata" / "network-inventory.sqlite3"
        if str(path) != ":memory:":
            self.path = Path(path).expanduser()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._database = str(self.path)
        else:
            self.path = Path(":memory:")
            self._database = ":memory:"
        self.retention = min(10_000, max(1, int(retention)))
        self._lock = threading.RLock()
        self._memory_connection: sqlite3.Connection | None = None
        if self._database == ":memory:":
            self._memory_connection = self._new_connection()
        self._migrate()

    def close(self) -> None:
        """Close."""
        with self._lock:
            if self._memory_connection is not None:
                self._memory_connection.close()
                self._memory_connection = None

    def __enter__(self) -> "NetworkInventory":
        return self
        """__enter__."""
        """__enter__."""

    def __exit__(self, *_args: Any) -> None:
        self.close()
        """__exit__."""
        """__exit__."""

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database, timeout=5.0, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
        """_new_connection."""
        """_new_connection."""

    def _connect(self) -> sqlite3.Connection:
        if self._memory_connection is not None:
            return self._memory_connection
        return self._new_connection()
        """_connect."""
        """_connect."""

    def _release(self, connection: sqlite3.Connection) -> None:
        if connection is not self._memory_connection:
            connection.close()
        """_release."""
        """_release."""

    def _migrate(self) -> None:
        connection = self._connect()
        try:
            version = int(connection.execute(
                "PRAGMA user_version").fetchone()[0])
            if version > _SCHEMA_VERSION:
                message = (
                    f"inventory schema {version} is newer than supported "
                    f"{_SCHEMA_VERSION}"
                )
                raise RuntimeError(message)
            if version == 0:
                connection.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE snapshots (
                        id INTEGER PRIMARY KEY,
                        observed_at TEXT NOT NULL,
                        gateway_mac TEXT NOT NULL DEFAULT ''
                    );
                    CREATE TABLE devices (
                        identity_key TEXT PRIMARY KEY,
                        first_seen TEXT NOT NULL,
                        last_seen TEXT NOT NULL,
                        identity_confidence TEXT NOT NULL
                    );
                    CREATE TABLE observations (
                        snapshot_id INTEGER NOT NULL
                            REFERENCES snapshots(id) ON DELETE CASCADE,
                        identity_key TEXT NOT NULL,
                        ip TEXT NOT NULL,
                        mac TEXT NOT NULL,
                        hostname TEXT NOT NULL,
                        vendor TEXT NOT NULL,
                        is_gateway INTEGER NOT NULL,
                        identity_confidence TEXT NOT NULL,
                        PRIMARY KEY (snapshot_id, identity_key)
                    );
                    CREATE TABLE services (
                        identity_key TEXT NOT NULL,
                        service_key TEXT NOT NULL,
                        first_seen TEXT NOT NULL,
                        last_seen TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        PRIMARY KEY (identity_key, service_key)
                    );
                    CREATE TABLE snapshot_services (
                        snapshot_id INTEGER NOT NULL,
                        identity_key TEXT NOT NULL,
                        service_key TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        FOREIGN KEY (snapshot_id, identity_key)
                            REFERENCES observations(
                                snapshot_id, identity_key
                            ) ON DELETE CASCADE,
                        PRIMARY KEY (
                            snapshot_id, identity_key, service_key
                        )
                    );
                    CREATE TABLE findings (
                        identity_key TEXT NOT NULL,
                        finding_key TEXT NOT NULL,
                        first_seen TEXT NOT NULL,
                        last_seen TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        PRIMARY KEY (identity_key, finding_key)
                    );
                    CREATE TABLE snapshot_findings (
                        snapshot_id INTEGER NOT NULL,
                        identity_key TEXT NOT NULL,
                        finding_key TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        FOREIGN KEY (snapshot_id, identity_key)
                            REFERENCES observations(
                                snapshot_id, identity_key
                            ) ON DELETE CASCADE,
                        PRIMARY KEY (
                            snapshot_id, identity_key, finding_key
                        )
                    );
                    CREATE TABLE device_metadata (
                        identity_key TEXT PRIMARY KEY,
                        custom_name TEXT NOT NULL DEFAULT '',
                        trust_state TEXT NOT NULL DEFAULT 'unknown',
                        tags_json TEXT NOT NULL DEFAULT '[]',
                        notes TEXT NOT NULL DEFAULT '',
                        updated_at TEXT NOT NULL
                    );
                    CREATE INDEX observations_ip_idx
                        ON observations(snapshot_id, ip);
                    PRAGMA user_version = 2;
                    COMMIT;
                """)
            elif version == 1:
                connection.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE device_metadata (
                        identity_key TEXT PRIMARY KEY,
                        custom_name TEXT NOT NULL DEFAULT '',
                        trust_state TEXT NOT NULL DEFAULT 'unknown',
                        tags_json TEXT NOT NULL DEFAULT '[]',
                        notes TEXT NOT NULL DEFAULT '',
                        updated_at TEXT NOT NULL
                    );
                    PRAGMA user_version = 2;
                    COMMIT;
                """)
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            self._release(connection)
        """_migrate."""
        """_migrate."""

    def record_snapshot(
        self,
        devices: Iterable[Any],
        observed_at: dt.datetime | str | None = None,
        gateway_mac: str = "",
    ) -> InventorySnapshot:
        """Thread-safe compatibility API for complete point-in-time snapshots."""
        with self._lock:
            return self._record_snapshot(devices, observed_at, gateway_mac)

    def _record_snapshot(
        self,
        devices: Iterable[Any],
        observed_at: dt.datetime | str | None = None,
        gateway_mac: str = "",
    ) -> InventorySnapshot:
        """Atomically store a snapshot and compare it with the prior one."""
        normalized = [normalize_device(item) for item in devices]
        if len(normalized) > _MAX_DEVICES:
            raise ValueError(f"snapshot exceeds {_MAX_DEVICES} device limit")
        current: dict[str, tuple[InventoryDevice, str]] = {}
        for device in normalized:
            key, confidence = _identity(device)
            if key in current:
                raise ValueError(
                    f"duplicate device identity in snapshot: {key}")
            current[key] = (device, confidence)
        timestamp = _timestamp(observed_at)
        gateway_mac = _normalize_mac(gateway_mac)
        if not gateway_mac:
            gateway_mac = next(
                (
                    device.mac
                    for device in normalized
                    if device.is_gateway and device.mac
                ),
                "",
            )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            previous_id, previous_gateway, previous = self._load_previous(
                connection)
            changes = self._compare(
                current, previous, previous_gateway, gateway_mac)
            cursor = connection.execute(
                "INSERT INTO snapshots(observed_at, gateway_mac) "
                "VALUES (?, ?)",
                (timestamp, gateway_mac),
            )
            snapshot_id = int(cursor.lastrowid)
            for identity_key, (device, confidence) in current.items():
                self._store_device(
                    connection, snapshot_id, timestamp, identity_key,
                    confidence, device)
            self._enforce_retention(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self._release(connection)
        return InventorySnapshot(
            snapshot_id=snapshot_id,
            observed_at=timestamp,
            devices=normalized,
            changes=changes,
            gateway_mac=gateway_mac,
        )

    def update(
        self,
        devices: Iterable[Any],
        findings: Iterable[Any] = (),
    ) -> InventoryChanges:
        """Persist current devices and return the requested focused change groups."""
        normalized = [normalize_device(item) for item in devices]
        by_ip: dict[str, list[InventoryFinding]] = {}
        for item in findings:
            device_ip = _text(_get(item, "device_ip", ""), 64)
            by_ip.setdefault(device_ip, []).append(_finding(item))
        enriched: list[InventoryDevice] = []
        for device in normalized:
            combined = {item.key: item for item in device.findings}
            for item in by_ip.get(device.ip, ()):
                combined[item.key] = item
            enriched.append(InventoryDevice(
                ip=device.ip,
                mac=device.mac,
                hostname=device.hostname,
                vendor=device.vendor,
                services=device.services,
                findings=tuple(combined.values()),
                device_id=device.device_id,
                is_gateway=device.is_gateway,
            ))
        snapshot = self.record_snapshot(enriched)
        return InventoryChanges(
            new_devices=[item for item in snapshot.changes if item.kind == "new_device"],
            changed_addresses=[item for item in snapshot.changes if item.kind == "address_changed"],
            new_services=[item for item in snapshot.changes if item.kind == "new_service"],
            new_findings=[item for item in snapshot.changes if item.kind == "new_finding"],
            severity_changes=[
                item for item in snapshot.changes
                if item.kind == "severity_changed"
            ],
            disappeared_devices=[
                item for item in snapshot.changes
                if item.kind == "device_disappeared"
            ],
            gateway_mac_changes=[
                item for item in snapshot.changes if item.kind == "gateway_mac_changed"
            ],
        )

    @staticmethod
    def _load_previous(
        connection: sqlite3.Connection,
    ) -> tuple[int | None, str, dict[str, dict[str, Any]]]:
        row = connection.execute(
            "SELECT id, gateway_mac FROM snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None, "", {}
        snapshot_id = int(row["id"])
        result: dict[str, dict[str, Any]] = {}
        for observation in connection.execute(
            "SELECT * FROM observations WHERE snapshot_id = ?", (snapshot_id,)
        ):
            key = str(observation["identity_key"])
            result[key] = {
                "ip": str(observation["ip"]),
                "mac": str(observation["mac"]),
                "hostname": str(observation["hostname"]),
                "confidence": str(observation["identity_confidence"]),
                "services": {},
                "findings": {},
            }
        for service in connection.execute(
            "SELECT identity_key, service_key, data_json "
            "FROM snapshot_services WHERE snapshot_id = ?",
            (snapshot_id,),
        ):
            key = str(service["identity_key"])
            if key in result:
                service_key = str(service["service_key"])
                result[key]["services"][service_key] = json.loads(
                    str(service["data_json"])
                )
        for finding in connection.execute(
            "SELECT identity_key, finding_key, severity, data_json "
            "FROM snapshot_findings WHERE snapshot_id = ?", (snapshot_id,)
        ):
            key = str(finding["identity_key"])
            if key in result:
                result[key]["findings"][str(finding["finding_key"])] = {
                    "severity": str(finding["severity"]),
                    "data": json.loads(str(finding["data_json"])),
                }
        return snapshot_id, str(row["gateway_mac"]), result
        """_load_previous."""
        """_load_previous."""

    @staticmethod
    def _compare(
        current: Mapping[str, tuple[InventoryDevice, str]],
        previous: Mapping[str, dict[str, Any]],
        previous_gateway: str,
        gateway_mac: str,
    ) -> list[InventoryChange]:
        changes: list[InventoryChange] = []
        unmatched = set(previous)
        for identity_key, (device, confidence) in current.items():
            matched_key = identity_key if identity_key in previous else None
            if matched_key is None:
                # A same-IP fallback is useful for detecting hardware/MAC
                # replacement, but is explicitly low confidence due to DHCP.
                matches = [
                    key for key in unmatched
                    if previous[key]["ip"] == device.ip
                ]
                if len(matches) == 1:
                    matched_key = matches[0]
                    confidence = "low"
            if matched_key is None:
                changes.append(InventoryChange(
                    kind="new_device",
                    device_id=identity_key,
                    severity="info",
                    message=f"New device observed at {device.ip}",
                    current=device.to_dict(),
                    identity_confidence=confidence,
                ))
                continue
            unmatched.discard(matched_key)
            old = previous[matched_key]
            if old["ip"] != device.ip:
                changes.append(InventoryChange(
                    kind="address_changed",
                    device_id=identity_key,
                    severity="info",
                    message=f"Device address changed from {old['ip']} to {device.ip}",
                    previous=old["ip"],
                    current=device.ip,
                    identity_confidence=confidence,
                ))
            if old["mac"] != device.mac and (old["mac"] or device.mac):
                changes.append(InventoryChange(
                    kind="mac_changed",
                    device_id=identity_key,
                    severity="medium",
                    message=(
                        "MAC address changed for the device at "
                        f"{device.ip}"
                    ),
                    previous=old["mac"],
                    current=device.mac,
                    identity_confidence=confidence,
                ))
            old_services = old["services"]
            for service in device.services:
                if service.key not in old_services:
                    changes.append(InventoryChange(
                        kind="new_service",
                        device_id=identity_key,
                        severity="low",
                        message=f"New service observed: {service.name}",
                        current=service.to_dict(),
                        identity_confidence=confidence,
                    ))
            old_findings = old["findings"]
            for finding in device.findings:
                prior = old_findings.get(finding.key)
                if prior is None:
                    changes.append(InventoryChange(
                        kind="new_finding",
                        device_id=identity_key,
                        severity=finding.severity,
                        message=f"New security finding: {finding.title}",
                        current=finding.to_dict(),
                        identity_confidence=confidence,
                    ))
                elif prior["severity"] != finding.severity:
                    direction = (
                        "increased" if _SEVERITIES[finding.severity] >
                        _SEVERITIES.get(prior["severity"], 0) else "decreased"
                    )
                    changes.append(InventoryChange(
                        kind="severity_changed",
                        device_id=identity_key,
                        severity=finding.severity,
                        message=(
                            f"Finding severity {direction}: "
                            f"{finding.title}"
                        ),
                        previous=prior["severity"],
                        current=finding.severity,
                        identity_confidence=confidence,
                    ))
        for identity_key in sorted(unmatched):
            old = previous[identity_key]
            changes.append(InventoryChange(
                kind="device_disappeared",
                device_id=identity_key,
                severity="info",
                message=(
                    "Previously observed device disappeared from "
                    f"{old['ip']}"
                ),
                previous={"ip": old["ip"], "mac": old["mac"]},
                identity_confidence=old["confidence"],
            ))
        if previous and previous_gateway and gateway_mac != previous_gateway:
            changes.append(InventoryChange(
                kind="gateway_mac_changed",
                device_id="gateway",
                severity="high",
                message="The default gateway MAC address changed",
                previous=previous_gateway,
                current=gateway_mac,
                identity_confidence="high" if gateway_mac else "low",
            ))
        return changes
        """_compare."""
        """_compare."""

    @staticmethod
    def _store_device(
        connection: sqlite3.Connection,
        snapshot_id: int,
        timestamp: str,
        identity_key: str,
        confidence: str,
        device: InventoryDevice,
    ) -> None:
        connection.execute(
            "INSERT INTO devices(identity_key, first_seen, last_seen, "
            "identity_confidence) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(identity_key) DO UPDATE SET "
            "last_seen=excluded.last_seen, "
            "identity_confidence=excluded.identity_confidence",
            (identity_key, timestamp, timestamp, confidence),
        )
        connection.execute(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (snapshot_id, identity_key, device.ip, device.mac, device.hostname,
             device.vendor, int(device.is_gateway), confidence),
        )
        for service in device.services:
            data = json.dumps(
                service.to_dict(),
                sort_keys=True,
                separators=(
                    ",",
                    ":"))
            connection.execute(
                "INSERT INTO services VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(identity_key, service_key) DO UPDATE SET "
                "last_seen=excluded.last_seen, data_json=excluded.data_json",
                (identity_key, service.key, timestamp, timestamp, data),
            )
            connection.execute(
                "INSERT INTO snapshot_services VALUES (?, ?, ?, ?)",
                (snapshot_id, identity_key, service.key, data),
            )
        for finding in device.findings:
            data = json.dumps(
                finding.to_dict(),
                sort_keys=True,
                separators=(
                    ",",
                    ":"))
            connection.execute(
                "INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(identity_key, finding_key) DO UPDATE SET "
                "last_seen=excluded.last_seen, severity=excluded.severity, "
                "data_json=excluded.data_json",
                (identity_key, finding.key, timestamp, timestamp,
                 finding.severity, data),
            )
            connection.execute(
                "INSERT INTO snapshot_findings VALUES (?, ?, ?, ?, ?)",
                (snapshot_id,
                 identity_key,
                 finding.key,
                 finding.severity,
                 data),
            )
        """_store_device."""
        """_store_device."""

    def _enforce_retention(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "DELETE FROM snapshots WHERE id NOT IN "
            "(SELECT id FROM snapshots ORDER BY id DESC LIMIT ?)",
            (self.retention,),
        )
        # Catalog rows are useful only while their device has retained history.
        connection.execute(
            "DELETE FROM services WHERE identity_key NOT IN "
            "(SELECT DISTINCT identity_key FROM observations)")
        connection.execute(
            "DELETE FROM findings WHERE identity_key NOT IN "
            "(SELECT DISTINCT identity_key FROM observations)")
        connection.execute(
            "DELETE FROM devices WHERE identity_key NOT IN "
            "(SELECT DISTINCT identity_key FROM observations)")
        """_enforce_retention."""
        """_enforce_retention."""

    @staticmethod
    def _metadata_identity(value: Any) -> str:
        if isinstance(value, str):
            key = value.strip()
            if (key.startswith(("id:", "mac:", "ip:"))
                    and len(key) <= 320 and not any(
                        ord(char) < 32 for char in key)):
                return key
            raise ValueError("invalid inventory identity key")
        device = normalize_device(value)
        return _identity(device)[0]
        """_metadata_identity."""
        """_metadata_identity."""

    @staticmethod
    def _metadata_values(
        custom_name: str,
        trust_state: str,
        tags: Iterable[str] | str,
        notes: str,
    ) -> tuple[str, str, tuple[str, ...], str]:
        name = _text(custom_name, 255)
        trust = _text(trust_state, 16).lower() or "unknown"
        if trust not in _TRUST_STATES:
            raise ValueError(
                "trust_state must be unknown, trusted, guest, or blocked")
        raw_tags = tags.split(",") if isinstance(tags, str) else tags
        normalized_tags = tuple(sorted({
            _text(tag, 64) for tag in raw_tags if _text(tag, 64)
        }))
        if len(normalized_tags) > 32:
            raise ValueError("device metadata supports at most 32 tags")
        return name, trust, normalized_tags, _text(notes, 4096)
        """_metadata_values."""
        """_metadata_values."""

    def set_metadata(
        self,
        identity: Any,
        *,
        custom_name: str = "",
        trust_state: str = "unknown",
        tags: Iterable[str] | str = (),
        notes: str = "",
    ) -> DeviceMetadata:
        """Atomically create or replace user-owned device metadata."""
        key = self._metadata_identity(identity)
        name, trust, normalized_tags, clean_notes = self._metadata_values(
            custom_name, trust_state, tags, notes)
        updated_at = _timestamp(None)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO device_metadata VALUES (?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(identity_key) DO UPDATE SET "
                    "custom_name=excluded.custom_name, "
                    "trust_state=excluded.trust_state, "
                    "tags_json=excluded.tags_json, notes=excluded.notes, "
                    "updated_at=excluded.updated_at",
                    (key, name, trust, json.dumps(normalized_tags),
                     clean_notes, updated_at),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                self._release(connection)
        return DeviceMetadata(
            key, name, trust, normalized_tags, clean_notes, updated_at)

    def get_metadata(self, identity: Any) -> DeviceMetadata | None:
        """Get metadata."""
        key = self._metadata_identity(identity)
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    "SELECT * FROM device_metadata WHERE identity_key = ?",
                    (key,),
                ).fetchone()
            finally:
                self._release(connection)
        return self._metadata_from_row(row) if row is not None else None

    def list_metadata(self) -> list[DeviceMetadata]:
        """List metadata."""
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT * FROM device_metadata ORDER BY identity_key"
                ).fetchall()
            finally:
                self._release(connection)
        return [self._metadata_from_row(row) for row in rows]

    @staticmethod
    def _metadata_from_row(row: sqlite3.Row) -> DeviceMetadata:
        try:
            raw_tags = json.loads(str(row["tags_json"]))
        except (json.JSONDecodeError, TypeError):
            raw_tags = []
        tags = tuple(
            _text(tag, 64) for tag in raw_tags[:32]
            if isinstance(tag, str) and _text(tag, 64))
        return DeviceMetadata(
            identity_key=str(row["identity_key"]),
            custom_name=str(row["custom_name"]),
            trust_state=str(row["trust_state"]),
            tags=tags,
            notes=str(row["notes"]),
            updated_at=str(row["updated_at"]),
        )
        """_metadata_from_row."""
        """_metadata_from_row."""

    def exposure_trends(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return bounded per-snapshot device/service/finding aggregates."""
        bounded = min(1000, max(1, int(limit)))
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute("""
                    SELECT s.id AS snapshot_id, s.observed_at,
                           (SELECT COUNT(*) FROM observations o
                            WHERE o.snapshot_id = s.id) AS device_count,
                           (SELECT COUNT(*) FROM snapshot_services ss
                            WHERE ss.snapshot_id = s.id) AS service_count,
                           (SELECT COUNT(*) FROM snapshot_findings sf
                            WHERE sf.snapshot_id = s.id) AS finding_count,
                           (SELECT COALESCE(SUM(CASE sf.severity
                               WHEN 'critical' THEN 10 WHEN 'high' THEN 7
                               WHEN 'medium' THEN 4 WHEN 'low' THEN 1
                               ELSE 0 END), 0)
                            FROM snapshot_findings sf
                            WHERE sf.snapshot_id = s.id) AS risk_score
                    FROM snapshots s
                    ORDER BY s.id DESC LIMIT ?
                """, (bounded,)).fetchall()
            finally:
                self._release(connection)
        return [dict(row) for row in reversed(rows)]

    @staticmethod
    def _csv_cell(value: Any) -> str:
        text = str(value or "")
        return "'" + text if text.startswith(_FORMULA_PREFIXES) else text
        """_csv_cell."""
        """_csv_cell."""

    @staticmethod
    def _csv_value(value: Any) -> str:
        text = str(value or "")
        if len(text) > 1 and text[0] == "'" and text[1] in _FORMULA_PREFIXES:
            return text[1:]
        return text
        """_csv_value."""
        """_csv_value."""

    def export_inventory_csv(self, path: str | Path) -> int:
        """Export the latest inventory plus metadata with formula escaping."""
        target = Path(path)
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute("""
                    SELECT o.identity_key, o.ip, o.mac, o.hostname, o.vendor,
                           COALESCE(m.custom_name, '') AS custom_name,
                           COALESCE(m.trust_state, 'unknown') AS trust_state,
                           COALESCE(m.tags_json, '[]') AS tags_json,
                           COALESCE(m.notes, '') AS notes
                    FROM observations o
                    JOIN (SELECT identity_key, MAX(snapshot_id) AS latest
                          FROM observations GROUP BY identity_key) current
                      ON current.identity_key = o.identity_key
                     AND current.latest = o.snapshot_id
                    LEFT JOIN device_metadata m
                      ON m.identity_key = o.identity_key
                    ORDER BY o.identity_key
                """).fetchall()
            finally:
                self._release(connection)
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "schema", "identity_key", "ip", "mac", "hostname",
                "vendor", "custom_name", "trust_state", "tags", "notes",
            ])
            for row in rows:
                try:
                    tags = ",".join(json.loads(str(row["tags_json"])))
                except (json.JSONDecodeError, TypeError):
                    tags = ""
                writer.writerow([
                    "cortex-network-inventory-v2",
                    *[self._csv_cell(value) for value in (
                        row["identity_key"], row["ip"], row["mac"],
                        row["hostname"], row["vendor"], row["custom_name"],
                        row["trust_state"], tags, row["notes"],
                    )],
                ])
        return len(rows)

    def import_inventory_csv(
        self,
        path: str | Path,
        *,
        dry_run: bool = True,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Validate and optionally import metadata in one transaction."""
        source = Path(path)
        if source.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("inventory CSV exceeds the 2 MiB limit")
        with source.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {"schema", "identity_key", "custom_name",
                        "trust_state", "tags", "notes"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError("inventory CSV is missing required columns")
            records = []
            for row in reader:
                if len(records) >= _MAX_DEVICES:
                    raise ValueError("inventory CSV exceeds the device limit")
                if row.get("schema") != "cortex-network-inventory-v2":
                    raise ValueError("unsupported inventory CSV schema")
                key = self._metadata_identity(
                    self._csv_value(row.get("identity_key", "")))
                values = self._metadata_values(
                    self._csv_value(row.get("custom_name", "")),
                    self._csv_value(row.get("trust_state", "unknown")),
                    self._csv_value(row.get("tags", "")),
                    self._csv_value(row.get("notes", "")),
                )
                records.append((key, values))
        if len({item[0] for item in records}) != len(records):
            raise ValueError("inventory CSV contains duplicate identities")

        existing = {item.identity_key for item in self.list_metadata()}
        conflicts = sorted(key for key, _values in records if key in existing)
        report = {
            "rows": len(records),
            "created": len(records) - len(conflicts),
            "updated": len(conflicts) if overwrite else 0,
            "conflicts": conflicts,
            "dry_run": bool(dry_run),
        }
        if dry_run:
            return report
        timestamp = _timestamp(None)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                for key, values in records:
                    if key in existing and not overwrite:
                        continue
                    name, trust, tags, notes = values
                    connection.execute(
                        "INSERT INTO device_metadata VALUES (?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(identity_key) DO UPDATE SET "
                        "custom_name=excluded.custom_name, "
                        "trust_state=excluded.trust_state, "
                        "tags_json=excluded.tags_json, notes=excluded.notes, "
                        "updated_at=excluded.updated_at",
                        (key, name, trust, json.dumps(tags), notes, timestamp),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                self._release(connection)
        return report

    def snapshot_count(self) -> int:
        """Snapshot count."""
        with self._lock:
            connection = self._connect()
            try:
                return int(connection.execute(
                    "SELECT COUNT(*) FROM snapshots").fetchone()[0])
            finally:
                self._release(connection)

    def device_lifetimes(self) -> list[dict[str, str]]:
        """Return retained first/last-seen metadata for display or export."""
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    "SELECT identity_key, first_seen, last_seen, "
                    "identity_confidence FROM devices ORDER BY identity_key"
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                self._release(connection)


def _timestamp(value: dt.datetime | str | None) -> str:
    if value is None:
        current = dt.datetime.now(dt.timezone.utc)
    elif isinstance(value, str):
        try:
            current = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                "observed_at must be an ISO-8601 timestamp") from exc
    elif isinstance(value, dt.datetime):
        current = value
    else:
        raise TypeError("observed_at must be datetime, ISO string, or None")
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    return current.astimezone(
        dt.timezone.utc).isoformat().replace("+00:00", "Z")
    """_timestamp."""
    """_timestamp."""


__all__ = [
    "InventoryChange",
    "InventoryChanges",
    "InventoryDevice",
    "InventoryFinding",
    "InventoryService",
    "InventorySnapshot",
    "NetworkInventory",
    "normalize_device",
]
