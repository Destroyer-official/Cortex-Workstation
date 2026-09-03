"""Qt-free design tokens for the premium UI/UX design system.

This module is intentionally pure Python with **no Qt import** so that its
values can be asserted directly by headless tests and reused by any layer
(``theme.py``, ``widgets.py``, ``states.py``) without pulling in PySide6.

It defines the shared primitives that give every one of the app's 41+ pages a
single, cohesive visual language:

* :class:`Spacing` - one 8pt-based spacing scale used between and within
  surfaces so margins/padding stay consistent everywhere.
* :class:`Radius` - one corner-radius scale for cards, inputs, buttons, and
  list surfaces.
* :data:`TYPE_ROLES` - a fixed set of named typographic roles (page title,
  section title, metric, body, caption) with consistent size and weight.

Later tasks extend this module with an elevation scale and a WCAG contrast
utility; those additions live alongside these scales without changing them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Spacing:
    """Single shared spacing scale on an 8pt base unit (Req 3.4).

    All inter- and intra-surface spacing is chosen from these named steps so
    layout rhythm stays consistent across the whole app. ``BASE`` is the unit
    the scale is derived from; the named steps are the values used in code.
    """

    BASE = 8

    XXS = 2
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


class Radius:
    """Single shared corner-radius scale (Req 3.5).

    Applied consistently to cards, inputs, buttons, and list surfaces.
    ``PILL`` is a deliberately large value so fully-rounded ("pill") shapes
    stay pill-shaped regardless of the widget's height.
    """

    SM = 8
    MD = 12
    LG = 18
    PILL = 999


# Typography roles: name -> (px_size, weight, letter_spacing) (Req 3.3).
#
# A single shared typographic scale defining a fixed set of named text roles
# with consistent size and weight across all pages. ``weight`` uses CSS/Qt
# numeric font weights (400 = normal, 700 = bold, 800 = extra-bold) and
# ``letter_spacing`` is expressed in pixels.
TYPE_ROLES: dict[str, tuple[int, int, float]] = {
    "page_title": (25, 800, 0.3),
    "section_title": (15, 800, 0.4),
    "metric": (27, 800, 0.5),
    "body": (14, 400, 0.0),
    "caption": (11, 700, 1.6),
}


# ---------------------------------------------------------------------------
# Elevation scale (Req 12.1, 12.2)
# ---------------------------------------------------------------------------


class Elevation(IntEnum):
    """Ordered surface-depth levels, lowest (furthest) to highest (closest).

    Every surface derives its background, border, and shadow from its assigned
    level so that depth order is perceivable (Req 12.1). Because it is an
    ``IntEnum`` the levels compare and sort like plain integers, which makes the
    monotonic-depth invariant (Req 12.2) trivial to assert in headless tests.
    """

    BACKGROUND = 0  # app / window backdrop
    SURFACE = 1     # base cards / panels
    RAISED = 2      # hero cards, popovers, hovered rows
    OVERLAY = 3     # modals, menus, tooltips


@dataclass(frozen=True)
class ElevationStyle:
    """Resolved visual treatment for a single :class:`Elevation` level.

    * ``surface`` / ``border`` are color strings (hex or ``rgba(...)``).
    * ``shadow_blur`` is the drop-shadow blur radius in pixels.
    * ``shadow_alpha`` / ``surface_alpha`` are 0-255 opacities; a
      ``surface_alpha`` below 255 marks a translucent ("glass") surface.
    """

    surface: str
    border: str
    shadow_blur: int
    shadow_alpha: int
    surface_alpha: int


# Depth cues per level. Both grow strictly with the level so that a higher
# surface always casts a larger, stronger shadow than the one beneath it
# (Req 12.2). Indexed by the Elevation integer value.
_SHADOW_BLUR: tuple[int, ...] = (0, 12, 24, 40)
_SHADOW_ALPHA: tuple[int, ...] = (0, 45, 80, 120)


def _parse_hex(color: str) -> tuple[int, int, int] | None:
    """Parse ``#RGB`` / ``#RRGGBB`` into an ``(r, g, b)`` triple, else ``None``."""
    if not isinstance(color, str):
        return None
    s = color.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return None
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except ValueError:
        return None


def _rel_luminance(color: str) -> float:
    """WCAG 2.1 relative luminance of a hex color in ``[0.0, 1.0]``.

    Unparseable colors return ``0.0`` (treated as darkest) so the monotonic
    resolver below degrades safely rather than raising.
    """
    rgb = _parse_hex(color)
    if rgb is None:
        return 0.0

    def _lin(channel: int) -> float:
        """_lin."""
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (_lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG 2.1 contrast ratio between a foreground and background color.

    Returns a value in ``[1.0, 21.0]`` computed as
    ``(L_lighter + 0.05) / (L_darker + 0.05)`` where ``L_*`` are the WCAG 2.1
    relative luminances of the two colors (see :func:`_rel_luminance`). The
    formula is symmetric, so the argument order does not affect the result.

    This is the assertable primitive behind the theme's contrast floors
    (Req 10.3: body text/background ≥ 4.5:1; Req 10.4: large-text and
    essential-UI pairs ≥ 3:1). Unparseable colors are treated as darkest
    (luminance ``0.0``) so the function never raises.
    """
    l1 = _rel_luminance(fg_hex)
    l2 = _rel_luminance(bg_hex)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def elevation_style(palette: object, level: "Elevation | int") -> ElevationStyle:
    """Resolve the :class:`ElevationStyle` for ``level`` from a theme ``palette``.

    ``palette`` is the active ``theme.Palette`` (imported lazily by callers to
    keep this module Qt-free). Its fields are read defensively via
    :func:`getattr` so this resolver works both before and after the palette
    gains the ``surface_raised``/``overlay``/``glass_*`` fields added by a later
    task; missing fields fall back to existing surfaces.

    The returned styles satisfy the depth-monotonicity invariant (Req 12.2):
    for ascending levels the surface is never darker (its relative luminance is
    non-decreasing) and the shadow (blur and alpha) is strictly greater.
    """
    lvl = Elevation(int(level))

    bg = getattr(palette, "bg", "#000000")
    surface = getattr(palette, "surface", bg)
    surface_alt = getattr(palette, "surface_alt", surface)
    border = getattr(palette, "border", surface)

    # Fields introduced by the later theme task; fall back gracefully.
    raised = getattr(palette, "surface_raised", None) or surface_alt
    overlay = getattr(palette, "overlay", None) or raised
    glass_border = getattr(palette, "glass_border", None) or border
    glass_alpha = getattr(palette, "glass_alpha", None)
    if not isinstance(glass_alpha, int):
        glass_alpha = 235

    # Candidate surface + border per level, ordered from background to overlay.
    candidates: list[tuple[str, str]] = [
        (bg, border),                 # BACKGROUND
        (surface, border),            # SURFACE
        (raised, glass_border),       # RAISED
        (overlay, glass_border),      # OVERLAY
    ]

    # Enforce "surface never darker as level rises": clamp each candidate's
    # luminance to be at least that of the level beneath it. In light themes a
    # nominally "raised" token can be darker than the base surface, so this
    # guarantees the invariant holds for every palette.
    resolved_surfaces: list[str] = []
    prev_surface: str | None = None
    for surf, _brd in candidates:
        if prev_surface is not None and _rel_luminance(surf) < _rel_luminance(prev_surface):
            surf = prev_surface
        resolved_surfaces.append(surf)
        prev_surface = surf

    idx = int(lvl)
    surface_color = resolved_surfaces[idx]
    border_color = candidates[idx][1]

    # Higher levels use a translucent glass fill; base levels stay opaque.
    surface_alpha = 255 if lvl <= Elevation.SURFACE else glass_alpha

    return ElevationStyle(
        surface=surface_color,
        border=border_color,
        shadow_blur=_SHADOW_BLUR[idx],
        shadow_alpha=_SHADOW_ALPHA[idx],
        surface_alpha=surface_alpha,
    )
