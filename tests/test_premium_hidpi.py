"""High-DPI crispness regression tests for the premium GUI.

Root cause these guard against: attaching a ``QGraphicsEffect`` (drop shadow /
glow) to a widget forces Qt to rasterize that widget - *including its text* -
into an offscreen ARGB pixmap before compositing. On high-DPI / scaled Windows
displays that offscreen path (a) drops subpixel/ClearType text antialiasing and
(b) on Qt < 6.4 is generated at 1x then upscaled, which made cards, the hero
call-to-action buttons, and the gauge look soft / "pixelated" - most visibly
when the window was maximized on a 125%/150% display.

The fix renders elevation and glow crisply (token QSS surfaces/borders + a
painted gauge halo) instead of via persistent blurring effects. These tests
assert that the primary always-on surfaces carry NO persistent QGraphicsEffect,
so their content is drawn straight to the window at the display's native
device-pixel ratio, while the transient one-shot animations (stat-card pulse,
page fade-in) still tear their temporary effect down so nothing is left soft.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app):
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow
    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    win.resize(1180, 760)
    yield win
    win.close()


def test_card_has_no_persistent_graphics_effect(app):
    """A Card must render its surface via QSS, not a blur-prone effect."""
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import Card

    for name in ("Card", "HeroCard", "Glass"):
        card = Card(THEMES["dark"], name)
        assert card.graphicsEffect() is None, (
            f"{name} must not carry a persistent QGraphicsEffect (it would "
            f"rasterize the card + its text to a 1x offscreen pixmap and blur "
            f"it on scaled displays)"
        )
        # The token elevation treatment is still resolved for depth cues.
        assert card._elevation is not None


def test_hero_buttons_and_gauge_have_no_persistent_effect(window):
    """The Scan/Clean CTAs and the dashboard gauge must stay crisp: no effect."""
    dash = window._pages["dashboard"]
    assert dash.scan_btn.graphicsEffect() is None
    assert dash.recycle_btn.graphicsEffect() is None
    assert dash.gauge.graphicsEffect() is None


def test_attach_glow_does_not_attach_blurring_effect(app):
    """attach_glow must never install a QGraphicsEffect (which would blur)."""
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import CircularGauge, attach_glow
    from PySide6.QtWidgets import QPushButton

    btn = QPushButton("Scan Now")
    attach_glow(btn, THEMES["dark"].accent, 22, 80)
    assert btn.graphicsEffect() is None

    gauge = CircularGauge(THEMES["dark"])
    attach_glow(gauge, THEMES["dark"].accent, 34, 55)
    # The gauge keeps its glow, but painted crisply (no graphics effect).
    assert gauge.graphicsEffect() is None
    assert gauge._glow_color == THEMES["dark"].accent
    assert gauge._glow_radius == 34


def test_gauge_paints_with_glow_enabled(app):
    """With a glow set, the gauge must still paint without error at any value."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QPixmap
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import CircularGauge

    gauge = CircularGauge(THEMES["dark"])
    gauge.set_glow(THEMES["dark"].accent, 34, 55)
    gauge.resize(200, 200)
    gauge._set_value(72.0)
    pm = QPixmap(200, 200)
    pm.fill()
    gauge.render(pm, QPoint(0, 0))  # exercises paintEvent incl. the glow layers
    assert not pm.isNull()


def test_statcard_pulse_effect_is_torn_down(app):
    """The one-shot pulse uses a transient opacity effect that must be removed
    when the animation finishes, so it never leaves the value label soft."""
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import StatCard

    card = StatCard(THEMES["dark"], "Reclaimable", "0")
    card.set_value("42", animate=True)
    anim = getattr(card, "_value_anim", None)
    assert anim is not None
    # Drive the animation to completion, then let queued finished slots run.
    anim.setCurrentTime(anim.duration())
    QApplication.processEvents()
    assert card._value.graphicsEffect() is None


def test_page_fade_leaves_no_permanent_effect(window):
    """Navigating pages uses a transient fade; once complete the page must have
    no lingering opacity effect (which would keep its text soft)."""
    window._select("duplicates")
    page = window._pages["duplicates"]
    anim = getattr(window, "_page_anim", None)
    if anim is not None:
        anim.setCurrentTime(anim.duration())
        QApplication.processEvents()
    assert page.graphicsEffect() is None
