"""Tests for the `cortex leftovers` command group (engine CLI).

The scan/clean paths are exercised against monkeypatched scanners so the
tests never touch the real registry or Recycle Bin.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from cortex_unified.engine.cli import main
from cortex_unified.system_tools.leftover_cleaner import LeftoverFinding


@pytest.fixture
def fake_scan(monkeypatch):
    """Patch LeftoverScanner inside the engine CLI's lazy import target.

    Manages fake scan operations and coordinates related state changes for the component.

    Args:
        monkeypatch: The monkeypatch parameter.
    """
    from cortex_unified.system_tools import leftover_cleaner as lc

    def _make(findings):
        """Make.

        Manages make operations and coordinates related state changes for the component.

        Args:
            findings: The findings parameter.
        """
        class FakeScanner:
            """Fakescanner.

            Manages FakeScanner operations and coordinates related state changes for the component.
            """
            def __init__(self, *a, **k):
                """Initialize the instance and configure internal state.

                Sets up sub-widgets, event signal connections, and default options.
                """
                pass

            def scan_app(self, app):
                """scan_app.

                Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

                Args:
                    app: The app parameter.
                """
                assert app.name
                return findings

            def scan_orphans(self):
                """scan_orphans.

                Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
                """
                return findings

        monkeypatch.setattr(lc, "LeftoverScanner", FakeScanner)
        return findings

    return _make


class TestLeftoversScan:
    """Testleftoversscan.

    Manages TestLeftoversScan operations and coordinates related state changes for the component.
    """
    def test_scan_json_emits_dicts(self, fake_scan):
        """test_scan_json_emits_dicts.

        Manages test scan json emits dicts operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
        """
        findings = fake_scan([
            LeftoverFinding(kind="folder", path=r"C:\x\Zeta",
                            size_bytes=2048, score=8, level="VeryGood",
                            reasons=["+4 empty"]),
        ])
        result = CliRunner().invoke(
            main, ["leftovers", "scan", "ZetaEditor", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload[0]["path"] == r"C:\x\Zeta"
        assert payload[0]["level"] == "VeryGood"

    def test_scan_human_output_shows_confidence(self, fake_scan):
        """test_scan_human_output_shows_confidence.

        Manages test scan human output shows confidence operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
        """
        fake_scan([
            LeftoverFinding(kind="folder", path=r"C:\x\Zeta",
                            size_bytes=1, score=6, level="Good"),
        ])
        result = CliRunner().invoke(main, ["leftovers", "scan", "ZetaEditor"])
        assert result.exit_code == 0
        assert "Good" in result.output
        assert result.output.count("C:\\x\\Zeta") == 1

    def test_scan_clean_system_reports_nothing(self, fake_scan):
        """test_scan_clean_system_reports_nothing.

        Manages test scan clean system reports nothing operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
        """
        fake_scan([])
        result = CliRunner().invoke(main, ["leftovers", "scan", "Ghost"])
        assert result.exit_code == 0
        assert "No leftovers" in result.output


class TestLeftoversClean:
    """Testleftoversclean.

    Manages TestLeftoversClean operations and coordinates related state changes for the component.
    """
    def test_dry_run_is_default_and_deletes_nothing(self, fake_scan,
                                                    tmp_path):
        """test_dry_run_is_default_and_deletes_nothing.

        Manages test dry run is default and deletes nothing operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
            tmp_path: Filesystem path to the target file or directory.
        """
        target = tmp_path / "Zeta"
        target.mkdir()
        fake_scan([LeftoverFinding(kind="folder", path=str(target),
                                   size_bytes=5, score=8, level="VeryGood")])
        result = CliRunner().invoke(main, ["leftovers", "clean", "ZetaEditor"])
        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert target.exists()          # nothing was touched

    def test_min_level_filters_questionable_by_default(self, fake_scan,
                                                       tmp_path):
        """test_min_level_filters_questionable_by_default.

        Manages test min level filters questionable by default operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
            tmp_path: Filesystem path to the target file or directory.
        """
        low = tmp_path / "LowConf"
        low.mkdir()
        high = tmp_path / "HighConf"
        high.mkdir()
        fake_scan([
            LeftoverFinding(kind="folder", path=str(low), size_bytes=1,
                            score=1, level="Questionable"),
            LeftoverFinding(kind="folder", path=str(high), size_bytes=2,
                            score=8, level="VeryGood"),
        ])
        result = CliRunner().invoke(main, ["leftovers", "clean", "App",
                                           "--json"])
        payload = json.loads(result.output)
        assert payload["dry_run"] is True
        # Dry-run JSON lists what WOULD be cleaned: only >= good.
        paths = [o["path"] for o in payload["would_clean"]]
        assert str(high) in paths and str(low) not in paths

    def test_apply_recycles_and_reports_freed_bytes(self, fake_scan,
                                                    tmp_path, monkeypatch):
        """test_apply_recycles_and_reports_freed_bytes.

        Manages test apply recycles and reports freed bytes operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        target = tmp_path / "Gone"
        target.mkdir()
        fake_scan([LeftoverFinding(kind="folder", path=str(target),
                                   size_bytes=4096, score=8,
                                   level="VeryGood")])

        from cortex_unified.system_tools import leftover_cleaner as lc

        class FakeCleaner:
            """Fakecleaner.

            Manages FakeCleaner operations and coordinates related state changes for the component.
            """
            def clean(self, models, create_restore_point=False):
                """clean.

                Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

                Args:
                    models: The models parameter.
                    create_restore_point: The create restore point parameter.
                """
                assert create_restore_point is False
                return [lc.CleanOutcome(models[0].path, models[0].kind, True,
                                        "recycled")]

        monkeypatch.setattr(lc, "LeftoverCleaner", FakeCleaner)
        result = CliRunner().invoke(main, ["leftovers", "clean", "App",
                                           "--apply", "--json"])
        payload = json.loads(result.output)
        assert payload["ok"] == 1
        assert payload["recycled_bytes"] == 4096

    def test_apply_failure_exits_nonzero(self, fake_scan, tmp_path,
                                         monkeypatch):
        """test_apply_failure_exits_nonzero.

        Manages test apply failure exits nonzero operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        target = tmp_path / "Boom"
        target.mkdir()
        fake_scan([LeftoverFinding(kind="folder", path=str(target),
                                   size_bytes=1, level="VeryGood", score=8)])
        from cortex_unified.system_tools import leftover_cleaner as lc

        class FailingCleaner:
            """Failingcleaner.

            Manages FailingCleaner operations and coordinates related state changes for the component.
            """
            def clean(self, models, create_restore_point=False):
                """clean.

                Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

                Args:
                    models: The models parameter.
                    create_restore_point: The create restore point parameter.
                """
                return [lc.CleanOutcome(models[0].path, models[0].kind,
                                        False, "failed", "denied")]

        monkeypatch.setattr(lc, "LeftoverCleaner", FailingCleaner)
        result = CliRunner().invoke(main, ["leftovers", "clean", "App",
                                           "--apply", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["failed"] == 1


class TestLeftoversOrphans:
    """Testleftoversorphans.

    Manages TestLeftoversOrphans operations and coordinates related state changes for the component.
    """
    def test_orphans_lists_findings(self, fake_scan):
        """test_orphans_lists_findings.

        Manages test orphans lists findings operations and coordinates related state changes for the component.

        Args:
            fake_scan: The fake scan parameter.
        """
        fake_scan([LeftoverFinding(kind="folder", path=r"C:\PF\Ghost",
                                   size_bytes=0, score=6, level="Good")])
        result = CliRunner().invoke(main, ["leftovers", "orphans"])
        assert result.exit_code == 0
        assert "Ghost" in result.output
