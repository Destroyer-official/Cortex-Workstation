"""Contracts for the SVG icon system.

Navigation, window chrome and status indicators used to be Unicode codepoints
baked into Python strings. Qt 6 ships no fonts, so each glyph resolved through
whatever system font happened to contain it - stroke weights and optical sizes
varied per icon, colour-emoji substitution happened for some codepoints, and
five symbols were reused across different tools (Privacy, Firewall and Security
all showed the same shield).

These tests pin the replacement: real assets, unique per tool, crisp at
fractional DPI, tintable, safe when missing, and actually shipped in the wheel.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from cortex_unified.ui.premium import icons, registry  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """app."""
    return QApplication.instance() or QApplication([])


# --- asset coverage --------------------------------------------------------

def test_every_page_has_its_own_icon_asset():
    """test_every_page_has_its_own_icon_asset."""
    missing = [s.id for s in registry.PAGES if not icons.has_icon(s.icon)]
    assert missing == [], f"pages without an icon asset: {missing}"


def test_no_two_pages_share_an_icon():
    """Regression: five glyphs were previously reused across tools."""
    used = [spec.icon for spec in registry.PAGES]
    duplicates = {name for name in used if used.count(name) > 1}
    assert duplicates == set(), f"icons reused across pages: {duplicates}"


def test_registry_icons_are_asset_names_not_glyphs():
    """An icon field must never contain a raw symbol codepoint again."""
    for spec in registry.PAGES:
        assert spec.icon.isascii(), f"{spec.id} icon is not an asset name"
        assert not spec.icon.startswith("\\u"), spec.id
        assert len(spec.icon) > 1, f"{spec.id} icon looks like a glyph"


def test_window_chrome_and_status_icons_are_shipped():
    """test_window_chrome_and_status_icons_are_shipped."""
    for name in ("brand", "win-minimize", "win-maximize", "win-restore",
                 "win-close", "info", "warning", "success", "error"):
        assert icons.has_icon(name), name


# --- rendering quality -----------------------------------------------------

def test_every_shipped_icon_renders(app):
    """test_every_shipped_icon_renders."""
    failed = [n for n in sorted(icons.available())
              if icons.pixmap(n, 18, "#DCE3F0").isNull()]
    assert failed == [], f"icons that failed to render: {failed}"


@pytest.mark.parametrize("dpr_x100,expected", [(100, 18), (125, 22),
                                               (150, 27), (200, 36)])
def test_rasterises_at_device_resolution(app, dpr_x100, expected):
    """Physical pixels must scale with DPI while logical size stays fixed.

    This is what keeps 1.6px strokes sharp at 125%/150% scaling; rendering once
    at 1x and letting Qt upscale is what produced the soft, pixelated look.
    """
    pixmap = icons._render("firewall", 18, "#DCE3F0", dpr_x100)
    assert pixmap is not None
    assert pixmap.width() == pixmap.height() == expected
    assert pixmap.devicePixelRatio() == pytest.approx(dpr_x100 / 100.0)
    logical = pixmap.width() / pixmap.devicePixelRatio()
    assert logical == pytest.approx(18, abs=0.51)


def test_icons_are_tinted_to_the_requested_colour(app):
    """test_icons_are_tinted_to_the_requested_colour."""
    image = icons.pixmap("firewall", 32, "#FF0000").toImage()
    opaque = {
        image.pixelColor(x, y).name()
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() > 200
    }
    assert opaque, "icon rendered fully transparent"
    assert opaque == {"#ff0000"}, f"unexpected colours: {sorted(opaque)[:5]}"


def test_icon_exposes_a_larger_variant_so_qt_never_upscales(app):
    """test_icon_exposes_a_larger_variant_so_qt_never_upscales."""
    sizes = icons.icon("dashboard", 18, "#FFFFFF").availableSizes()
    assert sizes, "QIcon carries no pixmaps"
    assert max(s.width() for s in sizes) >= 36


# --- robustness ------------------------------------------------------------

def test_missing_icon_degrades_to_empty_without_raising(app):
    """A missing decoration must never stop a tool from opening."""
    assert icons.icon("no_such_icon_exists").isNull()
    assert icons.pixmap("no_such_icon_exists").isNull()


def test_clear_cache_allows_retinting(app):
    """test_clear_cache_allows_retinting."""
    first = icons.pixmap("settings", 16, "#112233")
    icons.clear_cache()
    second = icons.pixmap("settings", 16, "#445566")
    assert not first.isNull() and not second.isNull()
    assert first.toImage() != second.toImage()


# --- integration with the shell -------------------------------------------

def test_navigation_uses_real_icons_and_clean_labels(app):
    """test_navigation_uses_real_icons_and_clean_labels."""
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow

    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    try:
        buttons = win._nav_buttons_by_page
        assert len(buttons) == len(registry.PAGES)
        blank = [pid for pid, b in buttons.items() if b.icon().isNull()]
        assert blank == [], f"nav buttons without an icon: {blank}"
        # The glyph must no longer live inside the label text.
        for pid, button in buttons.items():
            assert button.text().strip() == registry.BY_ID[pid].title
    finally:
        win.close()


def test_theme_switch_retints_navigation_icons(app):
    """test_theme_switch_retints_navigation_icons."""
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow

    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    try:
        win.set_theme("light")
        assert all(not b.icon().isNull()
                   for b in win._nav_buttons_by_page.values())
        win.set_theme("dark")
        assert all(not b.icon().isNull()
                   for b in win._nav_buttons_by_page.values())
    finally:
        win.close()


def test_title_bar_controls_have_icons_and_accessible_names(app):
    """test_title_bar_controls_have_icons_and_accessible_names."""
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow

    apply_theme(app, "dark")
    win = PremiumMainWindow("dark")
    try:
        bar = win._titlebar
        assert not bar._brand.pixmap().isNull()
        for button, name in ((bar._min, "Minimize"),
                             (bar._max, "Maximize"),
                             (bar._close, "Close")):
            assert not button.icon().isNull(), name
            assert button.text() == "", "chrome must not carry glyph text"
            assert button.accessibleName() == name
    finally:
        win.close()


def test_no_symbol_glyphs_remain_in_the_premium_ui():
    """Guard: icons must be assets, never Unicode codepoints.

    Qt 6 ships no fonts, so a codepoint used as an icon renders through system
    font fallback - inconsistent weights and baselines, and for emoji-presentation
    codepoints (U+2705, U+26D4, ...) a full-colour pictograph inside an otherwise
    monochrome UI. Typographic characters (dashes, ellipses, bullets, box drawing
    used for text art) are legitimate and stay.
    """
    import re
    from pathlib import Path

    allowed = set(
        "\u2014\u2026\u2022\u00b7\u2192\u2264\u2265\u00d7\u00b1\u2248"
        "\u2304\u203a\u25cf\u201c\u201d\u2500\u2514\u251c"
    )
    pattern = re.compile(r"\\u([0-9A-Fa-f]{4})")
    # These modules describe the historical glyphs in their docstrings.
    documented = {"icons.py", "registry.py", "widgets.py"}

    offenders: list[str] = []
    root = Path(icons.__file__).parent
    for path in sorted(root.rglob("*.py")):
        if path.name in documented:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for m in pattern.finditer(line):
                code = int(m.group(1), 16)
                in_symbol_block = (0x2000 <= code <= 0x2BFF
                                   or 0x1F000 <= code <= 0x1FAFF)
                if in_symbol_block and chr(code) not in allowed:
                    offenders.append(
                        f"{path.name}:{lineno} U+{code:04X} -> {line.strip()[:70]}")

    assert offenders == [], (
        "symbol glyphs used as icons; add an SVG to resources/icons and use "
        "icons.icon()/status_note() instead:\n  " + "\n  ".join(offenders)
    )


def test_status_note_pairs_an_icon_with_accessible_text(app):
    """test_status_note_pairs_an_icon_with_accessible_text."""
    from cortex_unified.ui.premium.theme import THEMES
    from cortex_unified.ui.premium.widgets import status_note

    for status in ("info", "warning", "success", "error"):
        note = status_note(THEMES["dark"], status, "Windows only.")
        # Meaning must not be carried by colour alone.
        assert note.accessibleName() == f"{status}: Windows only."
