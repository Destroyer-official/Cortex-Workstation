"""Headless gating + repair tests for legacy GUI tabs.

Covers the licensing gates on the file shredder (free-space wipe, multi-pass)
and reports tabs (scheduled reporting), plus the safe broken-link repair added
to ``cortex_unified.analyzers.broken_link_detector.repair``.

Setup pattern mirrors ``tests/test_gui_pages_e2e.py``: offscreen Qt platform,
module-scoped QApplication, whole module skipped when PySide6 is missing.
Licensing is always monkeypatched so no real license file is read and the
scheduler is faked, so no OS task is ever created.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from cortex_unified.core.config import Config  # noqa: E402
from cortex_unified.licensing.tiers import Feature  # noqa: E402
from cortex_unified.ui.tabs import file_shredder_tab, reports_tab  # noqa: E402
from cortex_unified.ui.tabs.file_shredder_tab import FileShredderTab  # noqa: E402
from cortex_unified.ui.tabs.reports_tab import ReportsTab  # noqa: E402
from cortex_unified.analyzers.broken_link_detector import (  # noqa: E402
    BrokenRegistryRef,
    BrokenShortcut,
    BrokenSymlink,
    repair,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def make_tab(app):
    """Factory building a tab without touching the real license manager."""
    logger = logging.getLogger("test-tabs-gating")
    config = Config()
    holder = type("SafetyManagerStub", (), {})()

    def _make(tab_cls):
        return tab_cls(config, logger, holder)

    return _make


def _link_item(path: Path) -> BrokenSymlink:
    return BrokenSymlink(
        path=path,
        target=str(path.parent / "missing_target.bin"),
        link_type="symlink",
        size=0,
        created=datetime.now(),
        last_accessed=datetime.now(),
        error_message="Target does not exist",
    )


def _registry_item(tmp_path: Path) -> BrokenRegistryRef:
    return BrokenRegistryRef(
        path=tmp_path / "Registry:HKCU\\Run\\Ghost",
        target="C:\\nope\\ghost.exe",
        link_type="registry_ref",
        size=0,
        created=datetime.now(),
        last_accessed=datetime.now(),
        registry_key=r"Software\Microsoft\Windows\CurrentVersion\Run",
        registry_value="Ghost",
        error_message="Referenced file does not exist",
    )


# ---------------------------------------------------------------------------
# 1. File shredder gating
# ---------------------------------------------------------------------------

def test_free_space_checkbox_disabled_on_free_tier(app, make_tab, monkeypatch):
    monkeypatch.setattr(file_shredder_tab, "allowed", lambda feature: False)
    tab = make_tab(FileShredderTab)

    assert not tab.shred_free_space_checkbox.isEnabled()
    tooltip = tab.shred_free_space_checkbox.toolTip() or ""
    assert "premium" in tooltip.lower()


def test_free_space_checkbox_enabled_when_entitled(app, make_tab, monkeypatch):
    monkeypatch.setattr(
        file_shredder_tab, "allowed",
        lambda feature: feature == Feature.FREE_SPACE_WIPE)
    tab = make_tab(FileShredderTab)

    assert tab.shred_free_space_checkbox.isEnabled()


def test_multipass_spinbox_capped_without_entitlement(app, make_tab, monkeypatch):
    monkeypatch.setattr(file_shredder_tab, "allowed", lambda feature: False)
    tab = make_tab(FileShredderTab)

    assert tab.shred_passes_spinbox.maximum() == 1
    assert tab.shred_passes_spinbox.value() == 1

    # Defensive runtime fallback: >1 requested without entitlement -> 1 pass.
    tab.shred_passes_spinbox.setRange(1, 35)
    tab.shred_passes_spinbox.setValue(7)
    assert tab._resolve_passes() == 1
    assert "capped" in tab.shred_results.toPlainText().lower()


def test_multipass_allowed_keeps_full_range(app, make_tab, monkeypatch):
    monkeypatch.setattr(
        file_shredder_tab, "allowed",
        lambda feature: feature == Feature.SHRED_MULTIPASS)
    tab = make_tab(FileShredderTab)

    assert tab.shred_passes_spinbox.maximum() == 35


# ---------------------------------------------------------------------------
# 2. Broken-link repair
# ---------------------------------------------------------------------------

def _make_broken_symlink(tmp_path: Path):
    target = tmp_path / "gone.bin"
    link = tmp_path / "dangling.link"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError, AttributeError):
        pytest.skip("cannot create symlinks on this platform/user")
    return link, target


def test_repair_dry_run_changes_nothing(app, tmp_path):
    link, _target = _make_broken_symlink(tmp_path)
    items = [_link_item(link), _registry_item(tmp_path)]

    outcomes = repair(items, use_trash=True, dry_run=True)

    assert len(outcomes) == 2
    assert os.path.lexists(link), "dry_run must not remove the link"

    link_out = outcomes[0]
    assert link_out.path == link
    assert link_out.ok
    assert "planned" in link_out.detail.lower()

    reg_out = outcomes[1]
    assert not reg_out.ok
    assert reg_out.action == "excluded"
    assert "manual review" in reg_out.detail.lower()


def test_repair_removes_only_the_link(app, tmp_path, monkeypatch):
    link, target = _make_broken_symlink(tmp_path)
    keep_me = tmp_path / "keep.txt"
    keep_me.write_text("precious data")

    outcomes = repair([_link_item(link)], use_trash=True, dry_run=False)

    assert len(outcomes) == 1
    assert outcomes[0].ok
    assert not os.path.lexists(link), "the broken symlink must be gone"
    assert not target.exists(), "nothing should be created at the dead target"
    assert keep_me.read_text() == "precious data", "real files must survive"


def test_repair_dry_run_plans_without_touching_fs(app, tmp_path, monkeypatch):
    """Planning path covered without needing OS link privileges."""
    ghost = tmp_path / "ghost.link"
    monkeypatch.setattr(
        "cortex_unified.analyzers.broken_link_detector._is_reparse_link",
        lambda p: Path(p) == ghost)

    outcomes = repair([_link_item(ghost)], use_trash=True, dry_run=True)

    assert len(outcomes) == 1
    out = outcomes[0]
    assert out.ok
    assert out.action == "remove symlink"
    assert "planned" in out.detail.lower()
    assert not ghost.exists()


@pytest.mark.skipif(not sys.platform.startswith("win"),
                    reason="NTFS junctions")
def test_repair_removes_dangling_junction_link_only(app, tmp_path):
    """Junctions need no admin rights; removal must take the link only."""
    import _winapi

    target_dir = tmp_path / "vanished_target"
    target_dir.mkdir()
    junction = tmp_path / "dangling_junc"
    try:
        _winapi.CreateJunction(str(target_dir), str(junction))
    except OSError:
        pytest.skip("cannot create junctions on this volume")
    # Now make it dangling.
    target_dir.rmdir()
    payload = tmp_path / "payload.txt"
    payload.write_text("must survive")

    outcomes = repair([_link_item(junction)], use_trash=True, dry_run=False)

    assert len(outcomes) == 1
    assert outcomes[0].ok
    assert not os.path.lexists(junction), "junction entry must be removed"
    assert not target_dir.exists(), "dead target must stay dead"
    assert payload.read_text() == "must survive"


def test_repair_excludes_registry_refs(app, tmp_path):
    outcomes = repair([_registry_item(tmp_path)], use_trash=True, dry_run=False)

    assert len(outcomes) == 1
    out = outcomes[0]
    assert out.action == "excluded"
    assert not out.ok
    assert "manual review" in out.detail.lower()


def test_repair_recycles_shortcut_via_send2trash(app, tmp_path, monkeypatch):
    lnk = tmp_path / "broken.lnk"
    lnk.write_bytes(b"\x00" * 128)
    item = BrokenShortcut(
        path=lnk,
        target="C:\\nope\\app.exe",
        link_type="shortcut",
        size=lnk.stat().st_size,
        created=datetime.now(),
        last_accessed=datetime.now(),
        error_message="Target does not exist",
    )

    sent = []

    def fake_trash(p):
        sent.append(p)
        os.remove(p)  # same contract as real send2trash

    monkeypatch.setattr(
        "cortex_unified.analyzers.broken_link_detector._resolve_send2trash",
        lambda: fake_trash)

    dry = repair([item], use_trash=True, dry_run=True)
    assert dry[0].ok and "planned" in dry[0].detail.lower()
    assert lnk.exists(), "dry_run must leave the .lnk in place"

    done = repair([item], use_trash=True, dry_run=False)
    assert done[0].ok and done[0].action == "recycle shortcut"
    assert sent == [str(lnk)]
    assert not lnk.exists()


def test_repair_refuses_real_directory(app, tmp_path):
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "data.txt").write_text("not a link")

    outcomes = repair([_link_item(real_dir)], use_trash=False, dry_run=False)

    assert len(outcomes) == 1
    out = outcomes[0]
    assert not out.ok
    assert real_dir.exists() and (real_dir / "data.txt").exists()


# ---------------------------------------------------------------------------
# 3. Reports scheduling gate + dialog flow
# ---------------------------------------------------------------------------

def _silence_message_boxes(monkeypatch, module):
    """Replace modal QMessageBox calls so headless tests never block."""

    class FakeBoxes:
        def information(self, *a, **k):
            return None

        def warning(self, *a, **k):
            return None

        def critical(self, *a, **k):
            return None

    monkeypatch.setattr(module, "QMessageBox", FakeBoxes())


def test_schedule_button_disabled_on_free_tier(app, make_tab, monkeypatch):
    monkeypatch.setattr(reports_tab, "allowed", lambda feature: False)
    tab = make_tab(ReportsTab)

    assert not tab.schedule_report_button.isEnabled()
    tooltip = tab.schedule_report_button.toolTip() or ""
    assert "pro" in tooltip.lower()


def test_schedule_button_enabled_and_creates_task(app, make_tab, monkeypatch):
    calls = []

    class FakeScheduler:
        def __init__(self, config=None):
            pass

        def create_scheduled_task(self, name, command, schedule_type,
                                  schedule_params=None):
            calls.append({
                "name": name,
                "command": command,
                "schedule_type": schedule_type,
                "schedule_params": schedule_params,
            })
            return True

    monkeypatch.setattr(
        reports_tab, "allowed",
        lambda feature: feature == Feature.AUTO_CLEAN_RULES)
    monkeypatch.setattr(reports_tab, "TaskScheduler", FakeScheduler)
    monkeypatch.setattr(QDialog, "exec",
                        lambda self: QDialog.DialogCode.Accepted)
    _silence_message_boxes(monkeypatch, reports_tab)

    tab = make_tab(ReportsTab)
    assert tab.schedule_report_button.isEnabled()

    tab.schedule_report()

    assert len(calls) == 1
    call = calls[0]
    assert call["schedule_type"] in {"daily", "weekly", "monthly"}
    assert "generate-report" in call["command"]
    assert "--type html" in call["command"]


def test_schedule_dialog_cancel_creates_nothing(app, make_tab, monkeypatch):
    calls = []

    class FakeScheduler:
        def __init__(self, config=None):
            pass

        def create_scheduled_task(self, *args, **kwargs):
            calls.append(args)
            return True

    monkeypatch.setattr(
        reports_tab, "allowed",
        lambda feature: feature == Feature.AUTO_CLEAN_RULES)
    monkeypatch.setattr(reports_tab, "TaskScheduler", FakeScheduler)
    monkeypatch.setattr(QDialog, "exec",
                        lambda self: QDialog.DialogCode.Rejected)
    _silence_message_boxes(monkeypatch, reports_tab)

    tab = make_tab(ReportsTab)
    tab.schedule_report()

    assert calls == [], "cancelling the dialog must not touch the scheduler"
