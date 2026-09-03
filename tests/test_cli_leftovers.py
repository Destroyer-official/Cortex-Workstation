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
    """Patch LeftoverScanner inside the engine CLI's lazy import target."""
    from cortex_unified.system_tools import leftover_cleaner as lc

    def _make(findings):
        class FakeScanner:
            def __init__(self, *a, **k):
                pass

            def scan_app(self, app):
                assert app.name
                return findings

            def scan_orphans(self):
                return findings

        monkeypatch.setattr(lc, "LeftoverScanner", FakeScanner)
        return findings

    return _make


class TestLeftoversScan:
    def test_scan_json_emits_dicts(self, fake_scan):
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
        fake_scan([
            LeftoverFinding(kind="folder", path=r"C:\x\Zeta",
                            size_bytes=1, score=6, level="Good"),
        ])
        result = CliRunner().invoke(main, ["leftovers", "scan", "ZetaEditor"])
        assert result.exit_code == 0
        assert "Good" in result.output
        assert result.output.count("C:\\x\\Zeta") == 1

    def test_scan_clean_system_reports_nothing(self, fake_scan):
        fake_scan([])
        result = CliRunner().invoke(main, ["leftovers", "scan", "Ghost"])
        assert result.exit_code == 0
        assert "No leftovers" in result.output


class TestLeftoversClean:
    def test_dry_run_is_default_and_deletes_nothing(self, fake_scan,
                                                    tmp_path):
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
        target = tmp_path / "Gone"
        target.mkdir()
        fake_scan([LeftoverFinding(kind="folder", path=str(target),
                                   size_bytes=4096, score=8,
                                   level="VeryGood")])

        from cortex_unified.system_tools import leftover_cleaner as lc

        class FakeCleaner:
            def clean(self, models, create_restore_point=False):
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
        target = tmp_path / "Boom"
        target.mkdir()
        fake_scan([LeftoverFinding(kind="folder", path=str(target),
                                   size_bytes=1, level="VeryGood", score=8)])
        from cortex_unified.system_tools import leftover_cleaner as lc

        class FailingCleaner:
            def clean(self, models, create_restore_point=False):
                return [lc.CleanOutcome(models[0].path, models[0].kind,
                                        False, "failed", "denied")]

        monkeypatch.setattr(lc, "LeftoverCleaner", FailingCleaner)
        result = CliRunner().invoke(main, ["leftovers", "clean", "App",
                                           "--apply", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["failed"] == 1


class TestLeftoversOrphans:
    def test_orphans_lists_findings(self, fake_scan):
        fake_scan([LeftoverFinding(kind="folder", path=r"C:\PF\Ghost",
                                   size_bytes=0, score=6, level="Good")])
        result = CliRunner().invoke(main, ["leftovers", "orphans"])
        assert result.exit_code == 0
        assert "Ghost" in result.output
