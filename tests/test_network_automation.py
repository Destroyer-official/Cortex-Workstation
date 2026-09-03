"""Offline tests for fixed-command recurring network scans."""

from __future__ import annotations

import subprocess

import pytest

from cortex_unified.system_tools import network_automation as automation


def test_schedule_builds_only_fixed_private_scan_command(monkeypatch):
    """test_schedule_builds_only_fixed_private_scan_command."""
    monkeypatch.setattr(automation.sys, "executable", "C:/Python/python.exe")
    spec = automation.NetworkSchedule(
        frequency="weekly", time="21:30", weekday="FRI",
        profile="advanced", scopes=("192.168.50.0/24",),
        ports="22,80,8000-8002")
    command = automation.build_scan_command(spec)
    assert command[:4] == [
        "C:/Python/python.exe", "-m",
        "cortex_unified.system_tools.network_scan_cli", "--profile"]
    port_index = command.index("--ports")
    assert command[port_index:port_index + 2] == [
        "--ports", "22,80,8000,8001,8002"]
    assert "--output" in command
    arguments = automation.build_windows_arguments(spec)
    assert arguments[:6] == [
        "schtasks", "/create", "/f", "/tn",
        r"\Cortex Cleaner\Network Security Audit", "/tr"]
    assert arguments[-4:] == ["/d", "FRI", "/st", "21:30"]
    assert subprocess.list2cmdline(command) in arguments


def test_schedule_rejects_public_scope_and_arbitrary_frequency():
    """test_schedule_rejects_public_scope_and_arbitrary_frequency."""
    with pytest.raises(ValueError, match="private LAN"):
        automation.build_scan_command(automation.NetworkSchedule(
            scopes=("8.8.8.0/24",)))
    with pytest.raises(ValueError, match="frequency"):
        automation.build_scan_command(automation.NetworkSchedule(
            frequency="startup"))


def test_scheduler_uses_process_runner_without_shell(monkeypatch):
    """test_scheduler_uses_process_runner_without_shell."""
    calls = []
    monkeypatch.setattr(automation.platform, "system", lambda: "Windows")

    def fake_run(arguments, **kwargs):
        """fake_run."""
        calls.append((arguments, kwargs))
        return subprocess.CompletedProcess(arguments, 0, "ok", "")

    monkeypatch.setattr(automation.proc, "run", fake_run)
    automation.NetworkScanScheduler().create(automation.NetworkSchedule())
    assert calls and isinstance(calls[0][0], list)
    assert calls[0][0][0] == "schtasks"
    assert calls[0][1] == {"text": True, "timeout": 30}
