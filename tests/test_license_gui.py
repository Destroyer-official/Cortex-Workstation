"""Headless tests for the license GUI: LicensePage + require_feature gating.

Follows test_premium_gui.py's offscreen-window approach. The licensing
singleton is pointed at a temp-path ``LicenseManager`` (the isolation pattern
from test_licensing.py's TestGating fixture) so the developer's real
``~/.cortex_cleaner/license.json`` is never read or written.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def isolated_license(monkeypatch, tmp_path):
    """Point the process-wide manager at a temp-path LicenseManager."""
    from cortex_unified.licensing import license_manager as lm_module
    from cortex_unified.licensing.license_manager import LicenseManager

    manager = LicenseManager(path=tmp_path / "license.json")
    monkeypatch.setattr(lm_module, "_MANAGER", manager, raising=False)
    yield manager
    lm_module.reset_singleton()


@pytest.fixture
def window(app, isolated_license):
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow

    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    win.resize(1180, 760)
    yield win
    win._force_quit = True
    win.close()
    # Release native handles promptly; dozens of live top-level windows across
    # a module exhaust GDI resources on Windows.
    win.deleteLater()
    app.processEvents()


def _click_trial_buttons(monkeypatch):
    """Route every dialog through 'the user clicked Start Free Trial'.

    require_feature() stores its trial button on the box (None when no trial
    was offered), so a fake exec/clickedButton pair drives the accept path
    without showing anything on screen.
    """
    boxes: list = []
    monkeypatch.setattr(
        QMessageBox, "exec", lambda self: boxes.append(self) or 0)
    monkeypatch.setattr(
        QMessageBox, "clickedButton",
        lambda self: getattr(self, "_trial_button", None))
    return boxes


# -- 1. page loads; Free tier when unlicensed ---------------------------------

def test_license_page_shows_free_when_unlicensed(window):
    page = window._pages["license"]
    assert page.tier_label.text() == "Free"
    assert page.key_label.text() == "No key installed"
    assert "no license" in page.status_label.text().lower()
    # Fresh machine: the once-per-machine trial is still available...
    assert page.trial_btn.isEnabled()
    assert page.deactivate_btn.isEnabled() is False
    # ...and only the free core reads as included in the comparison table.
    included = {
        page.table.item(r, 0).text(): page.table.item(r, 2).text()
        for r in range(page.table.rowCount())
    }
    assert included["engine.clean"] == "Yes"
    assert included["security.sentinel_pro"] == "\u2014"
    assert included["enterprise.audit_export"] == "\u2014"


def test_activate_with_empty_key_warns_and_stays_free(window, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warnings.append(a)))
    page = window._pages["license"]
    page._activate()
    assert warnings, "expected the empty-key warning dialog"
    assert page.tier_label.text() == "Free"


# -- 2. activation flows into the UI ------------------------------------------

def test_page_shows_pro_after_activation_and_refresh(window, isolated_license):
    from cortex_unified.licensing import Tier

    isolated_license.activate("PROK-1234-ABCD", Tier.PRO,
                              "Tester", "tester@example.dev")
    page = window._pages["license"]
    page._refresh()

    assert page.tier_label.text() == "Pro"
    assert "expires" in page.status_label.text().lower()
    # Masked key, never the full secret.
    assert page.key_label.text().startswith("Key: PROK")
    assert "1234-ABCD" not in page.key_label.text()
    # PRO unlocks 16 of the matrix rows; the table agrees with the manager.
    assert f"{len(isolated_license.validate().features)} of" \
        in page.features_label.text()
    included = {
        page.table.item(r, 0).text(): page.table.item(r, 2).text()
        for r in range(page.table.rowCount())
    }
    assert included["security.sentinel_pro"] == "Yes"
    assert included["enterprise.audit_export"] == "\u2014"
    # A paid license means the trial button has no reason to exist.
    assert page.trial_btn.isEnabled() is False


# -- 3. require_feature -------------------------------------------------------

def test_require_feature_allows_licensed_feature(window, isolated_license):
    from cortex_unified.licensing import Feature, Tier
    from cortex_unified.ui.premium.widgets import require_feature

    isolated_license.activate("K", Tier.PRO)
    assert require_feature(window, Feature.SENTINEL_PRO) is True


def test_require_feature_denied_offers_trial_then_refuses_second_time(
        window, isolated_license, monkeypatch):
    """Denied -> dialog offers the trial; starting it unlocks PRO; afterwards
    the offer is gone, so a second gated call simply returns False."""
    from cortex_unified.licensing import Feature
    from cortex_unified.ui.premium.widgets import require_feature

    boxes = _click_trial_buttons(monkeypatch)

    assert require_feature(window, Feature.REGISTRY_CLEANER) is True
    assert len(boxes) == 1
    assert boxes[0]._trial_button is not None, "trial should have been offered"
    assert isolated_license.validate().tier.value == "pro"

    # Trial consumed: no second offer, enterprise-only feature stays locked.
    assert require_feature(window, Feature.AUDIT_EXPORT) is False
    assert len(boxes) == 2
    assert boxes[1]._trial_button is None


def test_require_feature_reports_refused_trial(window, isolated_license,
                                               monkeypatch):
    """If start_trial refuses anyway (raced/exhausted), the user sees an
    honest info dialog instead of a silent no-op or a crash."""
    from cortex_unified.licensing import Feature
    from cortex_unified.ui.premium.widgets import require_feature

    infos = []
    monkeypatch.setattr(QMessageBox, "information",
                        staticmethod(lambda *a, **k: infos.append(a)))

    def refused():
        raise RuntimeError("Trial already used.")

    monkeypatch.setattr(isolated_license, "start_trial", refused)
    _click_trial_buttons(monkeypatch)

    assert require_feature(window, Feature.SENTINEL_PRO) is False
    assert infos, "expected the 'trial unavailable' dialog"
    assert not isolated_license.validate().licensed


# -- 4. registry --------------------------------------------------------------

def test_registry_declares_the_license_page():
    """Mirrors test_page_registry.py: one declaration wires everything."""
    from cortex_unified.ui.premium import registry

    spec = registry.BY_ID["license"]
    assert spec.title == "License & Tiers"
    assert spec.icon == "check"
    assert spec.group in {g.id for g in registry.GROUPS}
    cls = spec.load()
    assert isinstance(cls, type)
    assert cls.__name__.endswith("Page")


def test_window_nav_reaches_the_license_page(window):
    assert window._nav_sections_by_page.get("license") == "recovery"
    window._select("license")
    assert window._stack.currentWidget() is window._pages["license"]
