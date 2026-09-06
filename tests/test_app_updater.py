"""Tests for the Software Updater (winget wrapper).

The parser is tested against a realistic captured winget table so it works
without invoking winget (which needs network + is slow).
"""

from __future__ import annotations

from cortex_unified.system_tools.app_updater import AppUpdater, UpgradableApp

# A realistic winget 'upgrade' table (column-aligned like the real output).
SAMPLE = (
    "   - \n"
    "   \\ \n"
    "Name                     Id                Version    Available   Source\n"
    "-----------------------------------------------------------------------\n"
    "Git                      Git.Git           2.53.0.2   2.55.0.2    winget\n"
    "GitHub CLI               GitHub.cli        2.95.0     2.96.0      winget\n"
    "Google Cloud SDK         Google.CloudSDK   Unknown    575.0.0     winget\n"
    "3 upgrades available.\n"
)


class TestParser:
    """Group testparser tests covering parses all rows; fields extracted; handles unknown version; skips spinner and footer; empty or garbage returns empty; to dict."""
    def test_parses_all_rows(self):
        """Verify parses all rows via AppUpdater.parse_upgrade_output."""
        apps = AppUpdater.parse_upgrade_output(SAMPLE)
        assert len(apps) == 3
        assert all(isinstance(a, UpgradableApp) for a in apps)

    def test_fields_extracted(self):
        """Verify fields extracted via AppUpdater.parse_upgrade_output."""
        apps = {a.package_id: a for a in AppUpdater.parse_upgrade_output(SAMPLE)}
        git = apps["Git.Git"]
        assert git.name == "Git"
        assert git.current == "2.53.0.2"
        assert git.available == "2.55.0.2"
        assert git.source == "winget"

    def test_handles_unknown_version(self):
        """Verify handles unknown version via AppUpdater.parse_upgrade_output."""
        apps = {a.package_id: a for a in AppUpdater.parse_upgrade_output(SAMPLE)}
        assert apps["Google.CloudSDK"].current == "Unknown"
        assert apps["Google.CloudSDK"].available == "575.0.0"

    def test_skips_spinner_and_footer(self):
        """Verify skips spinner and footer via AppUpdater.parse_upgrade_output."""
        apps = AppUpdater.parse_upgrade_output(SAMPLE)
        ids = {a.package_id for a in apps}
        assert "" not in ids  # no spinner/footer rows leaked in

    def test_empty_or_garbage_returns_empty(self):
        """Verify empty or garbage returns empty via AppUpdater.parse_upgrade_output."""
        assert AppUpdater.parse_upgrade_output("") == []
        assert AppUpdater.parse_upgrade_output("no table here\njust text") == []

    def test_to_dict(self):
        """Verify to dict via AppUpdater.parse_upgrade_output, app.to_dict."""
        app = AppUpdater.parse_upgrade_output(SAMPLE)[0]
        d = app.to_dict()
        assert set(d) == {"name", "id", "current", "available", "source"}


class TestCapability:
    """Group testcapability tests covering is available returns bool; upgrade requires id."""
    def test_is_available_returns_bool(self):
        """Verify is available returns bool via AppUpdater.is_available."""
        assert isinstance(AppUpdater.is_available(), bool)

    def test_upgrade_requires_id(self):
        # Empty id must fail fast without invoking winget.
        """Verify upgrade requires id via AppUpdater.is_available, AppUpdater, updater.upgrade."""
        updater = AppUpdater()
        if not AppUpdater.is_available():
            ok, msg = updater.upgrade("")
            assert ok is False
        else:
            ok, msg = updater.upgrade("")
            assert ok is False and "id" in msg.lower()
