"""Offscreen tests for the per-device deep scan window (no live network).

The worker's collaborators are replaced with synthetic doubles, so these tests
exercise the real rendering and safety paths without opening a single socket.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from cortex_unified.system_tools.network_discovery import Device  # noqa: E402
from cortex_unified.system_tools.network_service_scanner import (  # noqa: E402
    ServiceObservation,
)
from cortex_unified.ui.premium import (  # noqa: E402
    device_window as device_window_module,
)

SCOPES = ("192.168.50.0/24",)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import (
        PremiumMainWindow,
    )
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    yield win
    win.close()


def _observation(port=443, name="https", **kwargs):
    metadata = kwargs.pop(
        "metadata",
        {"evidence": ["TCP connection accepted"]},
    )
    return ServiceObservation(
        ip="192.168.50.20", port=port, transport="tcp", name=name,
        source="tcp_connect", metadata=metadata, **kwargs)


def _device(**kwargs):
    payload = dict(
        ip="192.168.50.20",
        mac="00:11:22:33:44:55",
        hostname="test-camera",
        vendor="Synthetic Vendor",
        sources={"neighbor", "mdns"},
        services={"_http._tcp": "Front Door Camera"},
        open_ports=[443],
        service_observations=[_observation()],
    )
    payload.update(kwargs)
    return Device(**payload)


def test_window_renders_discovery_evidence_before_any_scan(window):
    win = device_window_module.DeviceDetailWindow(window, _device(), SCOPES)
    try:
        assert "192.168.50.20" in win.windowTitle()
        assert win.card_ports._value.text() == "1"
        # Nothing has been audited yet, so findings must not claim a verdict.
        assert win.card_findings._value.text() == "\u2014"
        assert win.services_tbl.rowCount() == 1
        assert win.services_tbl.item(0, 0).text() == "443"
        assert "Deep Scan Device" in win.findings_tbl.item(0, 1).text()
        assert "_http._tcp" in win.discovery_view.toPlainText()
        assert win.export_btn.isEnabled() is False
    finally:
        win.close()


def test_window_renders_completed_scan_payload_with_severity_badge(window):
    from cortex_unified.system_tools.device_fingerprint import (
        fingerprint_device,
    )
    from cortex_unified.system_tools.network_security_audit import (
        SecurityFinding,
    )

    device = _device()
    device.fingerprint = fingerprint_device(device)
    finding = SecurityFinding(
        code="reachable-telnet", severity="high",
        title="Reachable Telnet service", detail="Synthetic fixture",
        remediation="Disable Telnet.", device_ip=device.ip,
        evidence=["synthetic"], confidence=0.9, port=23)
    payload = {
        "device": device.to_dict(),
        "services": [
            _observation().to_dict(),
            _observation(23, "telnet").to_dict(),
        ],
        "findings": [finding.to_dict()],
        "fingerprint": device.fingerprint.to_dict(),
        "ping": {"reachable": True, "avg_ms": 4.0},
        "reverse_dns": "camera.lan",
        "profile": "advanced",
        "scanned_networks": list(SCOPES),
        "nmap": {"used": False, "reason": "not requested"},
        "cancelled": False,
        "notes": ["synthetic note"],
        "advertised_services": {"_http._tcp": "Front Door Camera"},
        "discovery_sources": ["mdns", "neighbor"],
        "identity_key": "mac:00:11:22:33:44:55",
        "metadata": {"custom_name": "Front Door", "trust_state": "trusted",
                     "tags": ["camera"], "notes": "", "updated_at": ""},
        "lifetime": {"first_seen": "2026-01-01T00:00:00Z",
                     "last_seen": "2026-02-01T00:00:00Z",
                     "identity_confidence": "high"},
        "trends": [{"observed_at": "2026-02-01T00:00:00Z", "device_count": 4,
                    "service_count": 6, "finding_count": 1, "risk_score": 7,
                    "snapshot_id": 3}],
        "history_error": "",
    }

    win = device_window_module.DeviceDetailWindow(window, device, SCOPES)
    try:
        win._on_scanned(payload)
        assert win.card_findings._value.text() == "1"
        assert win.card_risk._value.text() == "HIGH"
        assert win.card_latency._value.text() == "4 ms"
        assert win.services_tbl.rowCount() == 2
        assert win.findings_tbl.cellWidget(0, 0).text() == "HIGH"
        assert "Disable Telnet." in win.findings_tbl.item(0, 4).text()
        assert win.identity_tbl.rowCount() >= 1
        assert "camera.lan" in win.raw_view.toPlainText()
        assert "2026-01-01T00:00:00Z" in win.history_view.toPlainText()
        assert win.export_btn.isEnabled()
        assert win.open_btn.isEnabled()
        # HTML/PDF report bodies must stay evidence-only and escape content.
        report = win._html_report(payload)
        assert "Reachable Telnet service" in report
        assert "absence of a vulnerability" in report
    finally:
        win.close()


def test_worker_refuses_target_outside_authorized_scope(monkeypatch):
    def fail_scan(*_args, **_kwargs):
        raise AssertionError("an out-of-scope device must never be scanned")

    from cortex_unified.system_tools import network_service_scanner

    monkeypatch.setattr(
        network_service_scanner.NetworkServiceScanner, "scan", fail_scan)
    worker = device_window_module.DeviceDeepScanWorker(
        _device(ip="192.168.99.5", service_observations=[]), SCOPES)
    errors: list[str] = []
    worker.failed.connect(errors.append)
    worker.run()
    assert errors and "authorized private scope" in errors[0]


def test_worker_collects_services_findings_and_history(monkeypatch):
    from cortex_unified.system_tools import (
        network_service_scanner,
        network_tools,
    )

    monkeypatch.setattr(
        network_service_scanner.NetworkServiceScanner, "scan",
        lambda *_args, **_kwargs: [_observation(23, "telnet",
                                                banner="TELNET ready")])
    monkeypatch.setattr(
        network_tools.NetworkTools, "ping",
        lambda *_args, **_kwargs: network_tools.PingResult(
            "192.168.50.20", True, avg_ms=3.0))
    monkeypatch.setattr(
        network_tools.NetworkTools, "reverse_dns",
        staticmethod(lambda _ip: "camera.lan"))
    monkeypatch.setattr(
        device_window_module.DeviceDeepScanWorker, "_history",
        lambda self, _device: {
            "identity_key": "mac:00:11:22:33:44:55", "metadata": None,
            "lifetime": None, "trends": [], "history_error": ""})

    worker = device_window_module.DeviceDeepScanWorker(_device(), SCOPES)
    results: list[dict] = []
    worker.finished.connect(results.append)
    worker.run()

    assert results, "worker emitted no payload"
    payload = results[0]
    assert payload["services"][0]["port"] == 23
    assert payload["device"]["open_ports"] == [23]
    assert payload["ping"]["reachable"] is True
    assert payload["reverse_dns"] == "camera.lan"
    assert payload["nmap"] == {"used": False, "reason": "not requested"}
    codes = {item["code"] for item in payload["findings"]}
    assert "reachable-telnet" in codes
    assert all(item["cve_ids"] == [] for item in payload["findings"])


def test_worker_reports_missing_nmap_without_failing(monkeypatch):
    from cortex_unified.system_tools import (
        network_service_scanner,
        nmap_adapter,
    )

    monkeypatch.setattr(
        network_service_scanner.NetworkServiceScanner, "scan",
        lambda *_args, **_kwargs: [_observation()])
    monkeypatch.setattr(nmap_adapter.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        device_window_module.DeviceDeepScanWorker, "_ping",
        lambda self: {"reachable": False})
    monkeypatch.setattr(
        device_window_module.DeviceDeepScanWorker, "_reverse_dns",
        lambda self: "")
    monkeypatch.setattr(
        device_window_module.DeviceDeepScanWorker, "_history",
        lambda self, _device: {
            "identity_key": "", "metadata": None, "lifetime": None,
            "trends": [], "history_error": ""})

    worker = device_window_module.DeviceDeepScanWorker(
        _device(), SCOPES, nmap_modes=("connect", "version"))
    results: list[dict] = []
    worker.finished.connect(results.append)
    worker.run()

    payload = results[0]
    assert payload["nmap"]["used"] is False
    assert any("not found" in note for note in payload["notes"])


def test_worker_does_not_claim_port_source_without_observation(monkeypatch):
    from cortex_unified.system_tools import network_service_scanner

    monkeypatch.setattr(
        network_service_scanner.NetworkServiceScanner,
        "scan",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        device_window_module.DeviceDeepScanWorker,
        "_ping",
        lambda self: {"reachable": False},
    )
    monkeypatch.setattr(
        device_window_module.DeviceDeepScanWorker,
        "_reverse_dns",
        lambda self: "",
    )
    monkeypatch.setattr(
        device_window_module.DeviceDeepScanWorker,
        "_history",
        lambda self, _device: {
            "identity_key": "",
            "metadata": None,
            "lifetime": None,
            "trends": [],
            "history_error": "",
        },
    )

    worker = device_window_module.DeviceDeepScanWorker(
        _device(open_ports=[], service_observations=[]),
        SCOPES,
    )
    results: list[dict] = []
    worker.finished.connect(results.append)
    worker.run()

    assert results[0]["services"] == []
    assert "ports" not in results[0]["device"]["sources"]


def test_ping_worker_is_scope_checked_and_does_not_scan_ports(monkeypatch):
    from cortex_unified.system_tools import (
        network_service_scanner,
        network_tools,
    )

    def fail_scan(*_args, **_kwargs):
        raise AssertionError("the Ping action must not start a service scan")

    monkeypatch.setattr(
        network_service_scanner.NetworkServiceScanner,
        "scan",
        fail_scan,
    )
    monkeypatch.setattr(
        network_tools.NetworkTools,
        "ping",
        lambda *_args, **_kwargs: network_tools.PingResult(
            "192.168.50.20",
            True,
            avg_ms=2.0,
        ),
    )
    worker = device_window_module.DevicePingWorker(
        "192.168.50.20",
        SCOPES,
    )
    results: list[dict] = []
    worker.finished.connect(results.append)
    worker.run()

    assert results[0]["reachable"] is True
    assert results[0]["avg_ms"] == 2.0


def test_failed_scan_restores_capability_based_actions(window, monkeypatch):
    device = _device(mac="02:11:22:33:44:55")
    win = device_window_module.DeviceDetailWindow(window, device, SCOPES)
    monkeypatch.setattr(
        device_window_module.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: None,
    )
    try:
        win._busy(True)
        win._on_failed("synthetic failure")
        assert win.scan_btn.isEnabled()
        assert win.ping_btn.isEnabled()
        assert not win.wake_btn.isEnabled()
        # Discovery already observed HTTPS, so failure restores that action.
        assert win.open_btn.isEnabled()
        assert not win.export_btn.isEnabled()
    finally:
        win.close()


def test_lan_page_opens_retains_and_safely_closes_device_window(
    app,
    window,
    monkeypatch,
):
    from cortex_unified.system_tools.network_discovery import DiscoveryResult

    class FakeWorker:
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    started: list[tuple[object, str]] = []

    def fake_start_scan(detail_window, profile="advanced"):
        detail_window._worker = FakeWorker()
        detail_window._busy(True)
        started.append((detail_window, profile))

    monkeypatch.setattr(
        device_window_module.DeviceDetailWindow,
        "start_scan",
        fake_start_scan,
    )
    page = window._pages["landevices"]
    page._on_loaded(DiscoveryResult(
        devices=[_device()],
        networks=list(SCOPES),
        duration_seconds=0.1,
        audit_profile="advanced",
    ))
    page.tbl.selectRow(0)
    assert page.device_btn.isEnabled()

    page._open_device_window()
    assert len(page._device_windows) == 1
    detail = page._device_windows[0]
    worker = detail._worker
    assert started == [(detail, "advanced")]

    detail.close()
    assert worker.cancelled is True
    assert not detail.isVisible()
    assert detail in page._device_windows

    detail._on_failed("cancelled")
    app.processEvents()
    assert detail not in page._device_windows
