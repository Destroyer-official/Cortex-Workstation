"""Tests for the Qt-free premium design tokens (`tokens.py`).

These run without PySide6: `tokens.py` is pure Python by design so the token
scales and the elevation resolver can be asserted headlessly.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from cortex_unified.ui.premium import tokens
from cortex_unified.ui.premium.tokens import (
    Elevation,
    ElevationStyle,
    elevation_style,
)
from cortex_unified.ui.premium.theme import MIDNIGHT, DAYLIGHT, Palette

ALL_LEVELS = list(Elevation)
THEME_PALETTES = [MIDNIGHT, DAYLIGHT]


# ---------------------------------------------------------------------------
# Elevation enum shape
# ---------------------------------------------------------------------------


def test_elevation_has_four_ordered_levels():
    """Req 12.1: at least four ordered elevation levels, lowest -> highest.

    Manages test elevation has four ordered levels operations and coordinates related state changes for the component.
    """
    assert [lv.value for lv in ALL_LEVELS] == [0, 1, 2, 3]
    assert Elevation.BACKGROUND < Elevation.SURFACE < Elevation.RAISED < Elevation.OVERLAY


def test_elevation_named_levels_present():
    """test_elevation_named_levels_present.

    Manages test elevation named levels present operations and coordinates related state changes for the component.
    """
    for name in ("BACKGROUND", "SURFACE", "RAISED", "OVERLAY"):
        assert hasattr(Elevation, name)


# ---------------------------------------------------------------------------
# elevation_style resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("palette", THEME_PALETTES, ids=lambda p: p.name)
@pytest.mark.parametrize("level", ALL_LEVELS, ids=lambda lv: lv.name)
def test_elevation_style_returns_valid_style(palette, level):
    """test_elevation_style_returns_valid_style.

    Manages test elevation style returns valid style operations and coordinates related state changes for the component.

    Args:
        palette: The palette parameter.
        level: The level parameter.
    """
    style = elevation_style(palette, level)
    assert isinstance(style, ElevationStyle)
    assert isinstance(style.surface, str) and style.surface
    assert isinstance(style.border, str) and style.border
    assert style.shadow_blur >= 0
    assert 0 <= style.shadow_alpha <= 255
    assert 0 <= style.surface_alpha <= 255


@pytest.mark.parametrize("palette", THEME_PALETTES, ids=lambda p: p.name)
def test_elevation_style_accepts_int_level(palette):
    """Callers may pass a raw int; it resolves to the matching level.

    Manages test elevation style accepts int level operations and coordinates related state changes for the component.

    Args:
        palette: The palette parameter.
    """
    assert elevation_style(palette, 2) == elevation_style(palette, Elevation.RAISED)


@pytest.mark.parametrize("palette", THEME_PALETTES, ids=lambda p: p.name)
def test_glass_translucency_only_at_higher_levels(palette):
    """Base levels stay opaque; raised/overlay use a translucent glass fill.

    Manages test glass translucency only at higher levels operations and coordinates related state changes for the component.

    Args:
        palette: The palette parameter.
    """
    assert elevation_style(palette, Elevation.BACKGROUND).surface_alpha == 255
    assert elevation_style(palette, Elevation.SURFACE).surface_alpha == 255
    assert elevation_style(palette, Elevation.RAISED).surface_alpha < 255
    assert elevation_style(palette, Elevation.OVERLAY).surface_alpha < 255


# ---------------------------------------------------------------------------
# Depth monotonicity (Req 12.2) - the core invariant
# ---------------------------------------------------------------------------


def _assert_monotonic_depth(palette) -> None:
    """_assert_monotonic_depth.

    Manages assert monotonic depth operations and coordinates related state changes for the component.

    Args:
        palette: The palette parameter.
    """
    styles = [elevation_style(palette, lv) for lv in ALL_LEVELS]
    for lower, higher in zip(styles, styles[1:]):
        # Surface never gets darker as elevation rises.
        assert tokens._rel_luminance(higher.surface) >= tokens._rel_luminance(lower.surface)
        # ...and the shadow is strictly stronger (blur AND alpha increase),
        # so the depth cue is always perceivable.
        assert higher.shadow_blur > lower.shadow_blur
        assert higher.shadow_alpha > lower.shadow_alpha


@pytest.mark.parametrize("palette", THEME_PALETTES, ids=lambda p: p.name)
def test_depth_monotonic_for_builtin_themes(palette):
    """Req 12.2: higher levels are a visibly stronger depth cue.

    Manages test depth monotonic for builtin themes operations and coordinates related state changes for the component.

    Args:
        palette: The palette parameter.
    """
    _assert_monotonic_depth(palette)


# A generator that constrains to the real input space: valid theme palettes
# built from arbitrary hex colors, so the invariant is checked broadly.
_hex_color = st.from_regex(r"#[0-9a-fA-F]{6}", fullmatch=True)


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(
    bg=_hex_color,
    surface=_hex_color,
    surface_alt=_hex_color,
    border=_hex_color,
)
def test_depth_monotonic_for_arbitrary_palettes(bg, surface, surface_alt, border):
    """Validates: Requirements 12.1, 12.2

    For any palette and ascending levels, the surface is never darker and the
    shadow is strictly greater - the elevation-monotonicity property.
    """
    palette = Palette(
        name="Generated", is_dark=True,
        bg=bg, surface=surface, surface_alt=surface_alt, sidebar=bg, border=border,
        text="#FFFFFF", text_muted="#AAAAAA", text_faint="#777777",
        accent="#6E8BFF", accent_2="#9B7CFF", accent_press="#5A78F0", on_accent="#000000",
        success="#48D19B", warning="#E9B45A", danger="#EF6F84", info="#68B6F0",
    )
    _assert_monotonic_depth(palette)


# ---------------------------------------------------------------------------
# Defensive palette-field access (fields added by a later task)
# ---------------------------------------------------------------------------


def test_elevation_style_tolerates_minimal_palette():
    """Missing optional fields (surface_raised/overlay/glass_*) fall back safely.

    Manages test elevation style tolerates minimal palette operations and coordinates related state changes for the component.
    """

    class Bare:
        """Bare.

        Manages Bare operations and coordinates related state changes for the component.
        """
        bg = "#101010"
        surface = "#202020"
        surface_alt = "#303030"
        border = "#404040"

    styles = [elevation_style(Bare(), lv) for lv in ALL_LEVELS]
    assert all(isinstance(s, ElevationStyle) for s in styles)
    _assert_monotonic_depth(Bare())


# ---------------------------------------------------------------------------
# WCAG contrast utility (Req 10.3, 10.4)
# ---------------------------------------------------------------------------


from cortex_unified.ui.premium.tokens import contrast_ratio


def test_contrast_ratio_black_on_white_is_maximum():
    """Pure black vs pure white is the WCAG maximum of 21:1.

    Manages test contrast ratio black on white is maximum operations and coordinates related state changes for the component.
    """
    assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_identical_colors_is_minimum():
    """A color against itself has no contrast: the 1:1 floor.

    Manages test contrast ratio identical colors is minimum operations and coordinates related state changes for the component.
    """
    assert contrast_ratio("#6E8BFF", "#6E8BFF") == pytest.approx(1.0, abs=1e-9)


def test_contrast_ratio_is_symmetric():
    """Swapping foreground/background does not change the ratio.

    Manages test contrast ratio is symmetric operations and coordinates related state changes for the component.
    """
    assert contrast_ratio("#123456", "#abcdef") == pytest.approx(
        contrast_ratio("#abcdef", "#123456")
    )


def test_contrast_ratio_handles_shorthand_hex():
    """#RGB shorthand expands to #RRGGBB (so #FFF == #FFFFFF).

    Manages test contrast ratio handles shorthand hex operations and coordinates related state changes for the component.
    """
    assert contrast_ratio("#000", "#FFF") == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_unparseable_treated_as_darkest():
    """Bad input degrades to luminance 0.0 rather than raising.

    Manages test contrast ratio unparseable treated as darkest operations and coordinates related state changes for the component.
    """
    assert contrast_ratio("not-a-color", "#FFFFFF") == pytest.approx(21.0, abs=0.01)


@given(fg=_hex_color, bg=_hex_color)
def test_contrast_ratio_bounds_and_symmetry(fg, bg):
    """Validates: Requirements 10.3, 10.4

    For any two colors the ratio stays within WCAG bounds [1.0, 21.0] and is
    symmetric in its arguments - the primitive behind the theme contrast floors.
    """
    r = contrast_ratio(fg, bg)
    assert 1.0 <= r <= 21.0 + 1e-9
    assert r == pytest.approx(contrast_ratio(bg, fg))
