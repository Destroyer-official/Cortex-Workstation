"""Synthetic tests for transactional network snapshot inventory."""

from __future__ import annotations

import json
import sqlite3

import pytest

from cortex_unified.system_tools.network_inventory import (
    InventoryDevice,
    InventoryFinding,
    InventoryService,
    NetworkInventory,
    normalize_device,
)


def device(
    ip="192.168.1.10",
    mac="00:11:22:33:44:55",
    services=(),
    findings=(),
    **kwargs,
):
    return InventoryDevice(
        ip=ip,
        mac=mac,
        services=tuple(services),
        findings=tuple(findings),
        **kwargs,
    )


def kinds(snapshot):
    return [change.kind for change in snapshot.changes]


def test_first_snapshot_reports_new_device_and_is_json_safe(tmp_path):
    inventory = NetworkInventory(tmp_path / "inventory.sqlite3")
    snapshot = inventory.record_snapshot(
        [device(services=[InventoryService("https", 443)])],
        observed_at="2025-01-01T00:00:00Z",
    )
    assert kinds(snapshot) == ["new_device"]
    payload = json.loads(json.dumps(snapshot.to_dict()))
    assert payload["devices"][0]["services"][0]["port"] == 443
    assert "DHCP" in payload["identity_notice"]


def test_emits_new_service_and_severity_change(tmp_path):
    inventory = NetworkInventory(tmp_path / "inventory.db")
    old_finding = InventoryFinding("tls", "Weak TLS", "low")
    inventory.record_snapshot(
        [device(
            services=[InventoryService("http", 80)],
            findings=[old_finding],
        )],
        observed_at="2025-01-01T00:00:00Z",
    )
    snapshot = inventory.record_snapshot(
        [device(
            services=[InventoryService("http", 80), InventoryService("ssh", 22)],
            findings=[InventoryFinding("tls", "Weak TLS", "high")],
        )],
        observed_at="2025-01-02T00:00:00Z",
    )
    assert kinds(snapshot) == ["new_service", "severity_changed"]
    severity = snapshot.changes[1]
    assert severity.previous == "low"
    assert severity.current == "high"
    assert severity.severity == "high"


def test_mac_and_gateway_mac_changes_are_distinct(tmp_path):
    inventory = NetworkInventory(tmp_path / "inventory.db")
    inventory.record_snapshot(
        [device(mac="00:11:22:33:44:55")],
        gateway_mac="00:aa:bb:cc:dd:01",
    )
    snapshot = inventory.record_snapshot(
        [device(mac="00:11:22:33:44:66")],
        gateway_mac="00:aa:bb:cc:dd:02",
    )
    assert set(kinds(snapshot)) == {"mac_changed", "gateway_mac_changed"}
    mac_change = next(change for change in snapshot.changes if change.kind == "mac_changed")
    # Matching a replaced MAC by an unchanged DHCP address is not certainty.
    assert mac_change.identity_confidence == "low"


def test_disappearance_is_relative_to_previous_snapshot(tmp_path):
    inventory = NetworkInventory(tmp_path / "inventory.db")
    inventory.record_snapshot([
        device(),
        device(ip="192.168.1.20", mac="00:11:22:33:44:66"),
    ])
    snapshot = inventory.record_snapshot([device()])
    assert kinds(snapshot) == ["device_disappeared"]
    assert snapshot.changes[0].previous["ip"] == "192.168.1.20"


def test_randomized_mac_uses_low_confidence_ip_identity(tmp_path):
    inventory = NetworkInventory(tmp_path / "inventory.db")
    snapshot = inventory.record_snapshot([
        device(mac="36:fe:fa:8b:25:6b"),
    ])
    assert snapshot.changes[0].device_id == "ip:192.168.1.10"
    assert snapshot.changes[0].identity_confidence == "low"


def test_first_last_seen_and_catalogs_are_persisted(tmp_path):
    path = tmp_path / "inventory.db"
    inventory = NetworkInventory(path)
    observed = device(
        services=[InventoryService("ssh", 22)],
        findings=[InventoryFinding("open-ssh", "SSH exposed", "medium")],
    )
    inventory.record_snapshot([observed], observed_at="2025-01-01T00:00:00Z")
    inventory.record_snapshot([observed], observed_at="2025-01-03T00:00:00Z")
    lifetime = inventory.device_lifetimes()[0]
    assert lifetime["first_seen"] == "2025-01-01T00:00:00Z"
    assert lifetime["last_seen"] == "2025-01-03T00:00:00Z"
    with sqlite3.connect(path) as connection:
        service = connection.execute(
            "SELECT first_seen, last_seen FROM services").fetchone()
        finding = connection.execute(
            "SELECT severity FROM findings").fetchone()
    assert service == ("2025-01-01T00:00:00Z", "2025-01-03T00:00:00Z")
    assert finding == ("medium",)


def test_retention_removes_old_snapshots_and_orphan_catalogs(tmp_path):
    path = tmp_path / "inventory.db"
    inventory = NetworkInventory(path, retention=2)
    inventory.record_snapshot([device(ip="192.168.1.1", mac="00:11:22:33:44:01")])
    inventory.record_snapshot([device(ip="192.168.1.2", mac="00:11:22:33:44:02")])
    inventory.record_snapshot([device(ip="192.168.1.3", mac="00:11:22:33:44:03")])
    assert inventory.snapshot_count() == 2
    identities = {row["identity_key"] for row in inventory.device_lifetimes()}
    assert "mac:00:11:22:33:44:01" not in identities


def test_duplicate_identity_rejected_without_partial_snapshot(tmp_path):
    inventory = NetworkInventory(tmp_path / "inventory.db")
    same_mac = "00:11:22:33:44:55"
    with pytest.raises(ValueError, match="duplicate"):
        inventory.record_snapshot([
            device(ip="192.168.1.10", mac=same_mac),
            device(ip="192.168.1.11", mac=same_mac),
        ])
    assert inventory.snapshot_count() == 0


def test_normalizes_discovery_style_mapping_and_validates_ip():
    observed = normalize_device({
        "ip": "192.168.1.20",
        "mac": "00-11-22-33-44-55",
        "services": {"_http._tcp": "Printer"},
        "open_ports": [80],
        "findings": [{"code": "x", "title": "Example", "severity": "critical"}],
    })
    assert observed.mac == "00:11:22:33:44:55"
    assert len(observed.services) == 2
    assert observed.findings[0].severity == "critical"
    with pytest.raises(ValueError, match="invalid device IP"):
        normalize_device({"ip": "not-an-ip"})


def test_schema_version_and_future_version_guard(tmp_path):
    path = tmp_path / "inventory.db"
    NetworkInventory(path).close()
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert "device_metadata" in tables
        connection.execute("PRAGMA user_version = 999")
    with pytest.raises(RuntimeError, match="newer"):
        NetworkInventory(path)


def test_memory_database_supported():
    with NetworkInventory(":memory:") as inventory:
        inventory.record_snapshot([device()])
        assert inventory.snapshot_count() == 1


def test_schema_v1_migrates_metadata_table_atomically(tmp_path):
    path = tmp_path / "legacy.db"
    NetworkInventory(path).close()
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE device_metadata")
        connection.execute("PRAGMA user_version = 1")
    inventory = NetworkInventory(path)
    assert inventory.list_metadata() == []
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def test_metadata_trends_and_csv_round_trip_are_safe(tmp_path):
    path = tmp_path / "inventory.db"
    inventory = NetworkInventory(path)
    observed = device(
        hostname="=spreadsheet-formula",
        services=[InventoryService("https", 443)],
        findings=[InventoryFinding("tls", "TLS review", "high")],
    )
    inventory.record_snapshot([observed], observed_at="2026-01-01T00:00:00Z")
    metadata = inventory.set_metadata(
        observed, custom_name="+Kitchen camera", trust_state="trusted",
        tags="camera, iot", notes="@review",
    )
    assert metadata.tags == ("camera", "iot")
    assert inventory.get_metadata(observed) == metadata
    trend = inventory.exposure_trends()[0]
    assert trend["device_count"] == 1
    assert trend["service_count"] == 1
    assert trend["finding_count"] == 1
    assert trend["risk_score"] == 7

    exported = tmp_path / "inventory.csv"
    assert inventory.export_inventory_csv(exported) == 1
    text = exported.read_text(encoding="utf-8-sig")
    assert "'=spreadsheet-formula" in text
    assert "'+Kitchen camera" in text
    assert "'@review" in text

    imported = NetworkInventory(tmp_path / "imported.db")
    preview = imported.import_inventory_csv(exported, dry_run=True)
    assert preview == {
        "rows": 1, "created": 1, "updated": 0,
        "conflicts": [], "dry_run": True,
    }
    imported.import_inventory_csv(exported, dry_run=False)
    restored = imported.list_metadata()[0]
    assert restored.custom_name == "+Kitchen camera"
    assert restored.notes == "@review"


def test_invalid_csv_rolls_back_all_metadata(tmp_path):
    inventory = NetworkInventory(tmp_path / "inventory.db")
    path = tmp_path / "bad.csv"
    path.write_text(
        "schema,identity_key,custom_name,trust_state,tags,notes\n"
        "cortex-network-inventory-v2,mac:00:11:22:33:44:55,One,trusted,,ok\n"
        "cortex-network-inventory-v2,not-an-identity,Two,trusted,,bad\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="identity"):
        inventory.import_inventory_csv(path, dry_run=False)
    assert inventory.list_metadata() == []
