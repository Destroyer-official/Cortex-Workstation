"""No-network tests for explicit public-IP exposure lookups."""

from __future__ import annotations

import pytest

from cortex_unified.system_tools.external_exposure import (
    ExposureLookupError,
    ExternalExposureClient,
)


def test_lookup_requires_consent_and_global_public_ip():
    client = ExternalExposureClient(
        "shodan", "secret", transport=lambda *_args: {})
    with pytest.raises(ExposureLookupError, match="consent"):
        client.lookup("8.8.8.8")
    for address in ("192.168.1.1", "100.64.0.1", "127.0.0.1"):
        with pytest.raises(ExposureLookupError, match="globally routable"):
            client.lookup(address, consent=True)


def test_shodan_sends_only_selected_ip_and_normalizes_services():
    calls = []

    def transport(url, headers, timeout):
        calls.append((url, headers, timeout))
        return {
            "last_update": "2026-01-01T00:00:00Z",
            "data": [
                {"port": 443, "transport": "tcp", "product": "Caddy",
                 "version": "2.7"},
                {"port": 443, "transport": "tcp", "product": "Caddy",
                 "version": "2.7"},
            ],
        }

    result = ExternalExposureClient(
        "shodan", "api-key", transport=transport).lookup(
            "8.8.8.8", consent=True)
    assert len(result.services) == 1
    assert result.services[0].product == "Caddy"
    assert "/8.8.8.8?" in calls[0][0]
    assert "192.168" not in calls[0][0]
    assert result.to_dict()["connectivity_tested"] is False


def test_censys_credentials_use_header_not_url():
    calls = []

    def transport(url, headers, _timeout):
        calls.append((url, headers))
        return {"result": {
            "last_updated_at": "2026-01-01",
            "services": [{
                "port": 22, "transport_protocol": "tcp",
                "software": [{"product": "OpenSSH", "version": "9.1"}],
            }],
        }}

    result = ExternalExposureClient(
        "censys", "id", "secret", transport).lookup(
            "1.1.1.1", consent=True)
    assert result.services[0].version == "9.1"
    assert "id" not in calls[0][0] and "secret" not in calls[0][0]
    assert calls[0][1]["Authorization"].startswith("Basic ")
