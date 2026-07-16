"""Regression tests for the shell-injection and no-op-stub fixes."""

from __future__ import annotations

import sys

import pytest

from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules


class TestCustomCommandHardening:
    def test_disabled_by_default(self):
        rules = AutoCleanRules()
        out = rules._custom_clean_action({"command": "echo hi"})
        assert out is not None
        assert "disabled" in out.get("error", "")

    def test_runs_without_shell_when_allowed(self):
        rules = AutoCleanRules()
        # A benign, cross-platform command via the interpreter itself.
        out = rules._custom_clean_action({
            "command": [sys.executable, "-c", "print('ok')"],
            "allow_command": True,
        })
        assert out is not None
        assert out.get("returncode") == 0
        assert "ok" in out.get("stdout", "")

    def test_metacharacters_not_interpreted(self, tmp_path):
        """With shell=False, a chained '&& <malicious>' cannot execute.

        We pass a string whose shell-injection portion would create a file if a
        shell interpreted it. It must NOT be created.
        """
        rules = AutoCleanRules()
        marker = tmp_path / "pwned.txt"
        # If a shell ran this, it would touch the marker after echo.
        payload = f'{sys.executable} -c "print(1)" & echo x > "{marker}"'
        rules._custom_clean_action({"command": payload, "allow_command": True})
        assert not marker.exists()


class TestAppUninstallerImportSafe:
    def test_import_and_construct(self):
        from cortex_unified.system_tools.app_uninstaller import AppUninstaller
        u = AppUninstaller()
        # get_installed_apps is safe/read-only; returns a list (possibly empty
        # on non-Windows where winreg is absent).
        apps = u.get_installed_apps()
        assert isinstance(apps, list)

    def test_uninstall_missing_string_returns_false(self):
        from cortex_unified.system_tools.app_uninstaller import AppUninstaller
        u = AppUninstaller()
        assert u.uninstall_app({"name": "Nope"}) is False
