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
    """Testparser.

    Manages TestParser operations and coordinates related state changes for the component.
    """
    def test_parses_all_rows(self):
        """test_parses_all_rows.

        Manages test parses all rows operations and coordinates related state changes for the component.
        """
        apps = AppUpdater.parse_upgrade_output(SAMPLE)
        assert len(apps) == 3
        assert all(isinstance(a, UpgradableApp) for a in apps)

    def test_fields_extracted(self):
        """test_fields_extracted.

        Manages test fields extracted operations and coordinates related state changes for the component.
        """
        apps = {a.package_id: a for a in AppUpdater.parse_upgrade_output(SAMPLE)}
        git = apps["Git.Git"]
        assert git.name == "Git"
        assert git.current == "2.53.0.2"
        assert git.available == "2.55.0.2"
        assert git.source == "winget"

    def test_handles_unknown_version(self):
        """test_handles_unknown_version.

        Manages test handles unknown version operations and coordinates related state changes for the component.
        """
        apps = {a.package_id: a for a in AppUpdater.parse_upgrade_output(SAMPLE)}
        assert apps["Google.CloudSDK"].current == "Unknown"
        assert apps["Google.CloudSDK"].available == "575.0.0"

    def test_skips_spinner_and_footer(self):
        """test_skips_spinner_and_footer.

        Manages test skips spinner and footer operations and coordinates related state changes for the component.
        """
        apps = AppUpdater.parse_upgrade_output(SAMPLE)
        ids = {a.package_id for a in apps}
        assert "" not in ids  # no spinner/footer rows leaked in

    def test_empty_or_garbage_returns_empty(self):
        """test_empty_or_garbage_returns_empty.

        Manages test empty or garbage returns empty operations and coordinates related state changes for the component.
        """
        assert AppUpdater.parse_upgrade_output("") == []
        assert AppUpdater.parse_upgrade_output("no table here\njust text") == []

    def test_to_dict(self):
        """test_to_dict.

        Manages test to dict operations and coordinates related state changes for the component.
        """
        app = AppUpdater.parse_upgrade_output(SAMPLE)[0]
        d = app.to_dict()
        assert set(d) == {"name", "id", "current", "available", "source"}


class TestCapability:
    """Testcapability.

    Manages TestCapability operations and coordinates related state changes for the component.
    """
    def test_is_available_returns_bool(self):
        """test_is_available_returns_bool.

        Manages test is available returns bool operations and coordinates related state changes for the component.
        """
        assert isinstance(AppUpdater.is_available(), bool)

    def test_upgrade_requires_id(self):
        # Empty id must fail fast without invoking winget.
        """test_upgrade_requires_id.

        Manages test upgrade requires id operations and coordinates related state changes for the component.
        """
        updater = AppUpdater()
        if not AppUpdater.is_available():
            ok, msg = updater.upgrade("")
            assert ok is False
        else:
            ok, msg = updater.upgrade("")
            assert ok is False and "id" in msg.lower()
