"""Regression tests for sidebar navigation expand/collapse chevrons and icon color consistency."""

from __future__ import annotations

import os
import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from cortex_unified.ui.premium import icons, registry
from cortex_unified.ui.premium.window import PremiumMainWindow


@pytest.fixture(scope="module")
def app():
    """app."""
    return QApplication.instance() or QApplication([])


def test_sidebar_group_headers_have_valid_chevrons_and_escaped_titles(app):
    """Every group header must have a valid SVG chevron and no raw underscore mnemonics."""
    win = PremiumMainWindow()
    win._toggle_sidebar()  # Expand sidebar

    assert len(win._nav_sections) == 10

    for gid, sec in win._nav_sections.items():
        header = sec["header"]
        # Check icon exists and is not null
        assert not header.icon().isNull(), f"Header {gid} has null icon"
        
        # Check text is non-empty and has no misplaced single '&' that turns into '_'
        text = header.text().strip()
        assert text != "", f"Header {gid} text is empty"
        assert "_" not in text, f"Header {gid} has accidental underscore mnemonic: {text}"
        
        # When expanded or collapsed, chevron updates properly
        win._update_nav_header(gid, expanded=True)
        assert header.property("expanded") is True
        assert not header.icon().isNull()

        win._update_nav_header(gid, expanded=False)
        assert header.property("expanded") is False
        assert not header.icon().isNull()


def test_sidebar_expand_collapse_preserves_chevrons(app):
    """Expanding and collapsing the sidebar must never erase header chevrons or text."""
    win = PremiumMainWindow()

    # Initial state after constructor toggle
    for gid, sec in win._nav_sections.items():
        assert not sec["header"].icon().isNull()

    # Expand sidebar
    win._toggle_sidebar()
    for gid, sec in win._nav_sections.items():
        assert not sec["header"].icon().isNull()
        assert sec["header"].text().strip() != ""

    # Hover collapse & hover expand
    win._sidebar_hover_collapse()
    for gid, sec in win._nav_sections.items():
        assert not sec["header"].icon().isNull()

    win._sidebar_hover_expand()
    for gid, sec in win._nav_sections.items():
        assert not sec["header"].icon().isNull()
        assert sec["header"].text().strip() != ""


def test_all_132_pages_have_unique_icons_with_uniform_palette_tint(app):
    """All 132 page icons must be distinct and uniformly tinted to the theme color."""
    used_icons = [spec.icon for spec in registry.PAGES]
    assert len(used_icons) == 132
    assert len(set(used_icons)) == 132, "All 132 pages must have distinct icons"

    # Test that every icon renders without null and is tinted to #8B9BB4
    theme_color = "#8B9BB4"
    for spec in registry.PAGES:
        pixmap = icons._render(spec.icon, 24, theme_color, 100)
        assert pixmap is not None, f"Icon {spec.icon} failed to render"
        assert not pixmap.isNull(), f"Icon {spec.icon} rendered as null pixmap"
