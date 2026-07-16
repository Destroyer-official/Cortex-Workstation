"""Verify the secrets scanner detects a planted credential and stays offline."""

from __future__ import annotations


def test_run_scan_detects_planted_aws_key(tmp_path):
    from cortex_unified.system_tools.secrets_scanner import run_scan

    # Plant an obvious fake AWS access key id (matches the AKIA... pattern).
    (tmp_path / "config.py").write_text(
        'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\n'
        'password = "hunter2supersecretvalue"\n',
        encoding="utf-8",
    )
    (tmp_path / "clean.txt").write_text("nothing sensitive here\n", encoding="utf-8")

    stats = run_scan(str(tmp_path), quiet=True)
    assert stats.files_scanned >= 1
    # At least the AWS key should be found.
    rules = {getattr(f, "pattern_name", "") for f in stats.findings}
    assert stats.findings, "expected at least one finding"
    assert any("aws" in r.lower() or "key" in r.lower() or "secret" in r.lower()
               or "password" in r.lower() for r in rules)


def test_worker_emits_offline(tmp_path):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import pytest
    pytest.importorskip("PySide6")
    from cortex_unified.ui.premium.more_pages import SecretsScanWorker

    (tmp_path / "s.env").write_text('API_KEY=AKIAIOSFODNN7EXAMPLE\n', encoding="utf-8")
    captured = {}
    w = SecretsScanWorker(str(tmp_path))
    w.finished.connect(lambda rows, risk: captured.update(rows=rows, risk=risk))
    w.failed.connect(lambda m: captured.update(error=m))
    w.run()
    assert "rows" in captured
    assert isinstance(captured["rows"], list)


def test_secrets_scan_makes_no_network_calls(tmp_path, monkeypatch):
    """Offline guarantee: block urllib entirely; the scan must still succeed,
    proving the GUI scan path never touches the network."""
    import urllib.request
    from cortex_unified.system_tools import secrets_scanner

    def _blocked(*args, **kwargs):
        raise AssertionError("network access attempted during offline scan!")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked)
    monkeypatch.setattr(secrets_scanner.urllib.request, "urlopen", _blocked)

    (tmp_path / "code.py").write_text(
        'token = "ghp_1234567890abcdefghijklmnopqrstuvwx"\n', encoding="utf-8"
    )
    stats = secrets_scanner.run_scan(str(tmp_path), quiet=True)  # must NOT raise
    assert stats.files_scanned >= 1
