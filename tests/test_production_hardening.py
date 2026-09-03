"""Tests for the production-hardening round:

* ExclusionsStore - persisted "keep this" list honoured by scan AND clean
* Similar-name disambiguation (weaker matches penalised)
* Cooperative cancellation of scans and cleans
* SettingsStore consent fields (update_check opt-in, restore-point default)
* Update check gated behind explicit user consent
* Backups page listing leftover-cleanup journals as read-only rows
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fake_env(monkeypatch, tmp_path):
    """Redirect every sweep root into a throwaway directory tree."""
    roots = {
        "PROGRAMFILES": tmp_path / "pf",
        "ProgramFiles(x86)": tmp_path / "pf86",
        "ProgramData": tmp_path / "programdata",
        "APPDATA": tmp_path / "roaming",
        "LOCALAPPDATA": tmp_path / "local",
    }
    for env, path in roots.items():
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(env, str(path))
    (tmp_path / "local" / "LocalLow").mkdir()
    (tmp_path / "local" / "VirtualStore").mkdir()
    (tmp_path / "local" / "Programs").mkdir()
    (tmp_path / "roaming" / "Programs").mkdir()
    return tmp_path


# =====================================================================
#  ExclusionsStore
# =====================================================================

class TestExclusionsStore:
    """TestExclusionsStore."""
    def test_add_is_persisted_and_prefix_matched(self, tmp_path):
        """test_add_is_persisted_and_prefix_matched."""
        from cortex_unified.system_tools.leftover_cleaner import ExclusionsStore
        store = ExclusionsStore(tmp_path / "ex.json")
        target = tmp_path / "roaming" / "ZetaSoft"
        assert store.add(str(target)) is True
        # Reload from disk: persistence must survive a fresh instance.
        reloaded = ExclusionsStore(tmp_path / "ex.json")
        assert reloaded.is_excluded(str(target))
        child = target / "ZetaEditor" / "Cache"
        assert reloaded.is_excluded(child)          # beneath it -> excluded
        assert not reloaded.is_excluded(tmp_path / "roaming")  # above -> free
        assert not reloaded.is_excluded(tmp_path / "other")

    def test_discard_removes_and_persists(self, tmp_path):
        """test_discard_removes_and_persists."""
        from cortex_unified.system_tools.leftover_cleaner import ExclusionsStore
        p = tmp_path / "ex.json"
        store = ExclusionsStore(p)
        store.add(str(tmp_path / "a"))
        assert store.discard(str(tmp_path / "a")) is True
        assert len(ExclusionsStore(p)) == 0

    def test_corrupt_file_degrades_to_empty(self, tmp_path):
        """test_corrupt_file_degrades_to_empty."""
        from cortex_unified.system_tools.leftover_cleaner import ExclusionsStore
        p = tmp_path / "ex.json"
        p.write_text("{not json", encoding="utf-8")
        store = ExclusionsStore(p)
        assert len(store) == 0
        assert store.add(str(tmp_path / "x")) is True   # still usable


class TestScannerExclusions:
    """TestScannerExclusions."""
    def test_scan_app_skips_excluded_folders(self, fake_env):
        """test_scan_app_skips_excluded_folders."""
        from cortex_unified.system_tools.leftover_cleaner import (
            ExclusionsStore,
            InstalledApp,
            LeftoverScanner,
        )
        target = fake_env / "roaming" / "ZetaSoft ZetaEditor"
        target.mkdir(parents=True)
        store = ExclusionsStore(fake_env / "ex.json")
        store.add(str(target))

        app = InstalledApp(name="ZetaEditor", publisher="ZetaSoft")
        findings = LeftoverScanner(installed_apps=[],
                                   exclusions=store).scan_app(app)
        assert all(f.path.lower() != str(target).lower() for f in findings)

    def test_clean_refuses_excluded_paths_even_when_asked(self, tmp_path,
                                                          monkeypatch):
        """Defense in depth: a stale caller cannot delete an excluded path."""
        from cortex_unified.system_tools.leftover_cleaner import (
            CleanOutcome,
            ExclusionsStore,
            LeftoverCleaner,
            LeftoverFinding,
        )
        calls = []

        def fake_send2trash(path):  # must never be reached
            """fake_send2trash."""
            calls.append(path)

        import send2trash
        monkeypatch.setattr(send2trash, "send2trash", fake_send2trash)
        store = ExclusionsStore(tmp_path / "ex.json")
        protected = tmp_path / "keepme"
        protected.mkdir()
        store.add(str(protected))

        cleaner = LeftoverCleaner(backup_root=tmp_path / "b")
        outcome = cleaner.clean(
            [LeftoverFinding(kind="folder", path=str(protected))],
            exclusions=store)
        assert outcome[0].disposition == "skipped"
        assert outcome[0].ok is False
        assert calls == []                       # recycle never invoked


class TestCleanCancel:
    """TestCleanCancel."""
    def test_cancel_event_stops_between_items(self, tmp_path, monkeypatch):
        """test_cancel_event_stops_between_items."""
        from threading import Event

        from cortex_unified.system_tools.leftover_cleaner import (
            LeftoverCleaner,
            LeftoverFinding,
        )
        processed = []

        def fake_send2trash(path):
            """fake_send2trash."""
            processed.append(path)
            if len(processed) == 1:
                ev.set()                          # cancel after first item

        import send2trash
        monkeypatch.setattr(send2trash, "send2trash", fake_send2trash)

        a = tmp_path / "a"; a.mkdir()
        b = tmp_path / "b"; b.mkdir()
        c = tmp_path / "c"; c.mkdir()
        ev = Event()

        cleaner = LeftoverCleaner(backup_root=tmp_path / "b")
        outcomes = cleaner.clean([
            LeftoverFinding(kind="folder", path=str(a)),
            LeftoverFinding(kind="folder", path=str(b)),
            LeftoverFinding(kind="folder", path=str(c)),
        ], cancel_event=ev)
        assert len(outcomes) == 1                  # stopped after first
        assert b.exists() and c.exists()


# =====================================================================
#  Similar-name disambiguation
# =====================================================================

class TestDisambiguation:
    """TestDisambiguation."""
    def test_weaker_name_match_penalised(self, fake_env):
        """For app 'ZetaEditor', folder 'ZetaEditor' outranks 'ZetaEditorSuite'
        - the suite folder likely belongs to a different product."""
        from cortex_unified.system_tools.leftover_cleaner import (
            InstalledApp,
            LeftoverScanner,
        )
        exact = fake_env / "local" / "ZetaEditor"
        exact.mkdir()
        suite = fake_env / "roaming" / "ZetaEditor Suite"
        suite.mkdir()

        app = InstalledApp(name="ZetaEditor")
        findings = LeftoverScanner(installed_apps=[]).scan_app(app)
        by_base = {Path(f.path).name.lower(): f for f in findings}
        assert "zetaeditor" in by_base
        if "suite" in Path(suite.name).name.lower():
            suite_f = next((f for f in findings
                            if f.path == str(suite)), None)
            exact_f = by_base["zetaeditor"]
            if suite_f is not None:
                # The exact match must score at least as high; the weaker
                # match carries a disambiguation penalty.
                assert exact_f.score >= suite_f.score
                assert any("weaker name match" in r
                           for r in suite_f.reasons)


# =====================================================================
#  Settings: consent fields
# =====================================================================

class TestSettingsConsent:
    """TestSettingsConsent."""
    def test_update_check_defaults_off(self, tmp_path):
        """test_update_check_defaults_off."""
        from cortex_unified.ui.premium.settings_store import SettingsStore
        s = SettingsStore(tmp_path / "s.json")
        assert s.update_check is False          # opt-in ONLY

    def test_leftover_restore_point_defaults_on(self, tmp_path):
        """test_leftover_restore_point_defaults_on."""
        from cortex_unified.ui.premium.settings_store import SettingsStore
        s = SettingsStore(tmp_path / "s.json")
        assert s.leftover_restore_point is True  # safe default

    def test_fields_roundtrip(self, tmp_path):
        """test_fields_roundtrip."""
        from cortex_unified.ui.premium.settings_store import SettingsStore
        s = SettingsStore(tmp_path / "s.json")
        s.update_check = True
        s.leftover_restore_point = False
        reloaded = SettingsStore(tmp_path / "s.json")
        assert reloaded.update_check is True
        assert reloaded.leftover_restore_point is False

    def test_corrupt_file_uses_safe_defaults(self, tmp_path):
        """test_corrupt_file_uses_safe_defaults."""
        from cortex_unified.ui.premium.settings_store import SettingsStore
        p = tmp_path / "s.json"
        p.write_text("garbage{", encoding="utf-8")
        s = SettingsStore(p)
        assert s.update_check is False
        assert s.leftover_restore_point is True


class TestUpdateCheckGate:
    """TestUpdateCheckGate."""
    def test_scheduler_noops_without_consent(self, monkeypatch):
        """No network call may happen unless the user opted in."""
        import cortex_unified.ui.premium.app as app_mod
        from cortex_unified.system_tools import update_checker as uc

        called = []
        monkeypatch.setattr(uc, "check_for_update",
                            lambda *a, **k: called.append(1))

        class FakeWin:
            """FakeWin."""
            def statusBar(self):
                """statusBar."""
                class SB:
                    """SB."""
                    def showMessage(self, *a, **k):
                        """showMessage."""
                        pass
                return SB()

        app_mod._schedule_update_check(FakeWin(), type("S", (), {
            "update_check": False})())
        assert called == []


# =====================================================================
#  Backups page: leftover journals listed read-only
# =====================================================================

class TestBackupsLeftoverJournals:
    """TestBackupsLeftoverJournals."""
    def test_worker_lists_journal_sessions(self, tmp_path, monkeypatch):
        """test_worker_lists_journal_sessions."""
        import cortex_unified.ui.premium.report_pages as rp

        session = tmp_path / "CortexCleanerBackups" / "leftovers" / "20260101_120000"
        session.mkdir(parents=True)
        (session / "journal.json").write_text(json.dumps({
            "timestamp": "2026-01-01T12:00:00",
            "ok_count": 3, "fail_count": 1,
            "items": [],
        }), encoding="utf-8")

        class FakeRestoreManager:
            """FakeRestoreManager."""
            def list_manifests(self):
                """list_manifests."""
                return [{"backup_name": "op-manifest", "_kind": "manifest"}]

        from cortex_unified.reports import restore_manager as rm_mod
        monkeypatch.setattr(rm_mod.RestoreManager, "list_manifests",
                            lambda self: FakeRestoreManager().list_manifests())

        # Point the worker's home-relative path into tmp via monkeypatched home.
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        rows = rp.ManifestListWorker._leftover_sessions.__func__() \
            if hasattr(rp.ManifestListWorker._leftover_sessions, "__func__") \
            else rp.ManifestListWorker._leftover_sessions()

        # The helper reads Path.home(); USERPROFILE drives it on Windows.
        leftover_rows = [r for r in rows if r.get("_kind") == "leftovers"]
        assert len(leftover_rows) == 1
        row = leftover_rows[0]
        assert "20260101_120000" in row["backup_name"]
        assert row["files_backed_up"] == 3
        assert "Recycle Bin" in row["_detail"]
