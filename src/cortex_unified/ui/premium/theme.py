"""Premium design system: color tokens, typography, and a full QSS builder.

Why QSS and not QPalette: a genuinely premium look needs rounded surfaces,
gradient accents, custom scrollbars, pill badges, and hover/pressed states -
none of which QPalette can express. This module centralizes all of that into
two cohesive themes ("Cortex Midnight" dark and "Cortex Daylight" light) driven
by a single :class:`Palette` token set, so the entire app restyles from one
place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only, keeps runtime Qt-free
    from .tokens import Elevation

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont, QFontDatabase
    _HAS_QT = True
except ImportError:  # pragma: no cover
    _HAS_QT = False


def _hex_to_rgb(color: str) -> tuple[int, int, int] | None:
    """Parse ``#RGB`` / ``#RRGGBB`` into an ``(r, g, b)`` triple, else ``None``.

    Kept local (rather than importing the equivalent helper from ``tokens``) so
    this module has no import-time dependency on ``tokens``.
    """
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


def _shade(color: str, factor: float) -> str:
    """Return ``color`` lightened (``factor > 1``) or darkened (``factor < 1``).

    Used to derive distinct ``:hover`` / ``:pressed`` shades for filled controls
    directly from the active :class:`Palette` colors, so interactive states stay
    token-derived rather than introducing hard-coded literals (Req 3.2). If the
    color can't be parsed the original string is returned unchanged.
    """
    rgb = _hex_to_rgb(color)
    if rgb is None:
        return color
    scaled = tuple(max(0, min(255, round(channel * factor))) for channel in rgb)
    return "#{:02X}{:02X}{:02X}".format(*scaled)


@dataclass(frozen=True)
class Palette:
    """A complete set of design tokens for one theme."""

    name: str
    is_dark: bool
    # surfaces
    bg: str            # app background
    surface: str       # cards / panels
    surface_alt: str   # inputs / elevated rows
    sidebar: str       # navigation rail
    border: str
    # text
    text: str
    text_muted: str
    text_faint: str
    # brand / accent
    accent: str
    accent_2: str      # gradient partner
    accent_press: str
    on_accent: str
    # semantic
    success: str
    warning: str
    danger: str
    info: str

    # ---- modern visual language tokens (Req 12) ----
    # These carry defaults so existing construction sites and tests that build
    # a Palette without them keep working; MIDNIGHT/DAYLIGHT set real values.
    #
    # Elevation surfaces (Req 12.1): fills for the RAISED and OVERLAY levels
    # above the base ``surface``. Consumed by ``tokens.elevation_style``.
    surface_raised: str = ""   # RAISED level fill (hero cards, popovers)
    overlay: str = ""          # OVERLAY level fill (modals, menus, tooltips)
    # Glass treatment (Req 12.3): translucency + a subtle top-edge highlight.
    glass_alpha: int = 235     # 0-255 surface opacity for glass surfaces
    glass_border: str = ""     # subtle highlight border for glass surfaces
    # Accent gradient stops (Req 12.6): (position 0.0-1.0, color) pairs used to
    # build token-defined gradients for CTAs and the gauge arc.
    accent_grad_stops: tuple[tuple[float, str], ...] = ()

    # convenience gradients
    @property
    def accent_gradient(self) -> str:
        return (f"qlineargradient(x1:0, y1:0, x2:1, y2:1, "
                f"stop:0 {self.accent}, stop:1 {self.accent_2})")

    def glass(self, level: "Elevation | int") -> str:
        """Return an ``rgba(...)`` surface fill for the given elevation ``level``.

        Resolves the level's surface color and translucency from the active
        elevation scale (``tokens.elevation_style``) and expresses it as a Qt
        stylesheet ``rgba()`` string so higher levels read as translucent
        "glass" over whatever sits beneath them (Req 12.3). Falls back to the
        opaque resolved surface when the color cannot be parsed.
        """
        from .tokens import elevation_style  # local import keeps tokens Qt-free

        style = elevation_style(self, level)
        rgb = _hex_to_rgb(style.surface)
        if rgb is None:
            return style.surface
        r, g, b = rgb
        return f"rgba({r}, {g}, {b}, {style.surface_alpha})"


MIDNIGHT = Palette(
    name="Cortex Midnight",
    is_dark=True,
    bg="#12141C",           # lifted charcoal - easier on the eyes than pure black
    surface="#1A1D27",
    surface_alt="#222733",
    sidebar="#161922",
    border="#2A2F3D",
    text="#D9DFEA",         # soft off-white (not harsh pure white)
    text_muted="#8A91A3",
    text_faint="#5B6273",
    accent="#6E8BFF",       # soft indigo-blue - premium, not piercing
    accent_2="#9B7CFF",     # gentle violet gradient partner
    accent_press="#5A78F0",
    on_accent="#0B0E16",
    success="#48D19B",
    warning="#E9B45A",
    danger="#EF6F84",
    info="#68B6F0",
    # modern visual language (Req 12.1, 12.3, 12.6, 12.7)
    surface_raised="#252A38",   # lifted above surface for hero/popovers
    overlay="#2E3446",          # highest level for modals/menus/tooltips
    glass_alpha=228,            # slightly translucent frosted surfaces
    glass_border="rgba(255, 255, 255, 0.10)",  # subtle top-edge highlight
    accent_grad_stops=((0.0, "#6E8BFF"), (1.0, "#9B7CFF")),
)

DAYLIGHT = Palette(
    name="Cortex Daylight",
    is_dark=False,
    bg="#F4F6FB",
    surface="#FFFFFF",
    surface_alt="#EEF2F8",
    sidebar="#FFFFFF",
    border="#E2E8F2",
    text="#161B26",
    text_muted="#5A6576",
    text_faint="#9AA4B6",
    accent="#4F7CFF",
    accent_2="#7C5CFF",
    accent_press="#3A66E6",
    on_accent="#FFFFFF",
    success="#0F9D63",
    warning="#B45309",
    danger="#DC2626",
    info="#0284C7",
    # modern visual language (Req 12.1, 12.3, 12.6, 12.7)
    surface_raised="#FFFFFF",   # stays bright; depth carried by shadow/border
    overlay="#FFFFFF",          # modals/menus sit brightest over the page
    glass_alpha=240,            # near-opaque frosted white on light theme
    glass_border="rgba(255, 255, 255, 0.65)",  # bright top-edge highlight
    accent_grad_stops=((0.0, "#4F7CFF"), (1.0, "#7C5CFF")),
)

THEMES: dict[str, Palette] = {"dark": MIDNIGHT, "light": DAYLIGHT}


def build_stylesheet(p: Palette) -> str:
    """Return a complete application QSS for the given palette.

    Every spacing, corner-radius, typographic, and color value is sourced from
    the shared design tokens (``tokens.Spacing`` / ``Radius`` / ``TYPE_ROLES`` /
    ``Elevation``) and the active :class:`Palette` rather than scattered
    literals (Req 3.1, 3.2). Surfaces are elevation-aware: ``QFrame#Card`` sits
    at the SURFACE level while ``QFrame#HeroCard``/``#Glass`` sit at the RAISED
    level with a translucent glass fill and a subtle top-edge highlight border
    (Req 12.3). Scrollbars are drawn entirely from token colors and radii
    (Req 5.3).

    Every standard Interactive_Control carries the complete state matrix
    (Req 6.1-6.5): a distinct ``:hover`` treatment, a ``:pressed`` treatment, a
    ``:disabled`` treatment that suppresses hover/press feedback, and a
    ``:focus`` ring that is *visually distinct from both the normal and hover
    styles* (Req 6.3, 6.5). Hover and pressed feedback are expressed by shading
    the base token color (``_shade``), while focus is expressed as an accent
    outline plus accent border — a different mechanism, so keyboard focus can
    never be confused with a hover (Req 6.5). This matrix is applied to the base
    ``QPushButton`` and the ``#Primary`` / ``#Ghost`` / ``#Danger`` variants, to
    ``QPushButton#NavItem``, to ``QLineEdit`` / ``QComboBox`` / ``QSpinBox`` /
    ``QDoubleSpinBox``, to ``QCheckBox`` (and item-view indicators), and to
    ``QTreeView`` / ``QTableView`` / ``QListWidget`` rows.
    """
    from .tokens import (  # local import keeps module import-time Qt-free
        Elevation,
        Radius,
        Spacing,
        TYPE_ROLES,
        elevation_style,
    )

    # --- typography roles (Req 3.3) ---
    pt_size, pt_weight, pt_ls = TYPE_ROLES["page_title"]
    st_size, st_weight, st_ls = TYPE_ROLES["section_title"]
    mt_size, mt_weight, mt_ls = TYPE_ROLES["metric"]
    body_size, body_weight, _body_ls = TYPE_ROLES["body"]
    cap_size, cap_weight, cap_ls = TYPE_ROLES["caption"]

    # --- elevation-resolved surfaces (Req 12.1, 12.2, 12.3) ---
    surface = elevation_style(p, Elevation.SURFACE)
    raised = elevation_style(p, Elevation.RAISED)
    overlay = elevation_style(p, Elevation.OVERLAY)
    glass_raised = p.glass(Elevation.RAISED)     # rgba(...) glass fill
    glass_overlay = p.glass(Elevation.OVERLAY)   # rgba(...) glass fill

    return f"""
    /* ---------- base ---------- */
    QWidget {{
        background-color: {p.bg};
        color: {p.text};
        font-family: "Segoe UI", "Inter", "SF Pro Display", system-ui, sans-serif;
        font-size: {body_size}px;
    }}
    QToolTip {{
        background-color: {glass_overlay};
        color: {p.text};
        border: 1px solid {overlay.border};
        border-radius: {Radius.SM}px;
        padding: {Spacing.XS}px {Spacing.SM}px;
    }}

    /* ---------- content backdrop (subtle depth) ---------- */
    QWidget#ContentArea {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {p.bg}, stop:0.55 {p.bg}, stop:1 {p.sidebar});
    }}

    /* ---------- custom title bar ---------- */
    QWidget#TitleBar {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p.sidebar}, stop:1 {p.bg});
        border-bottom: 1px solid {p.border};
    }}
    QLabel#TitleGlyph {{ color: {p.accent}; font-size: {st_size}px; }}
    QLabel#TitleText {{ color: {p.text}; font-size: {body_size - 1}px; font-weight: 700;
                        letter-spacing: 1.5px; }}
    QPushButton#WinBtn, QPushButton#CloseBtn {{
        background: transparent; border: none; border-radius: 0;
        color: {p.text_muted}; font-size: {body_size}px; padding: 0;
    }}
    QPushButton#WinBtn:hover {{ background: {p.surface_alt}; color: {p.text}; }}
    QPushButton#CloseBtn:hover {{ background: {p.danger}; color: {p.on_accent}; }}

    /* ---------- cards / panels (elevation-aware) ---------- */
    /* Base surface card sits at the SURFACE elevation level. A subtle top-edge
       highlight gives a crisp "raised" cue (painted by QSS at native DPI) so
       cards read as elevated without a blur-prone drop-shadow graphics effect. */
    QFrame#Card {{
        background-color: {surface.surface};
        border: 1px solid {surface.border};
        border-top: 1px solid {p.glass_border};
        border-radius: {Radius.MD}px;
    }}
    /* Hero / glass surfaces sit at the RAISED level: a translucent glass fill
       with a subtle top-edge highlight border reading over what's beneath. */
    QFrame#HeroCard, QFrame#Glass {{
        background-color: {glass_raised};
        border: 1px solid {raised.border};
        border-top: 1px solid {p.glass_border};
        border-radius: {Radius.LG}px;
    }}

    /* ---------- sidebar ---------- */
    QWidget#Sidebar {{
        background-color: {p.sidebar};
        border-right: 1px solid {p.border};
    }}
    QLabel#Brand {{
        color: {p.text};
        font-size: {st_size + 3}px;
        font-weight: 800;
        letter-spacing: 0.5px;
        padding: {Spacing.XS}px {Spacing.SM}px;
    }}
    QLabel#BrandSub {{
        color: {p.accent};
        font-size: {cap_size - 1}px;
        font-weight: {cap_weight};
        letter-spacing: 2.5px;
    }}
    QPushButton#NavItem {{
        text-align: left;
        padding: {Spacing.MD}px {Spacing.LG}px;
        border: none;
        border-left: 3px solid transparent;
        border-radius: {Radius.SM}px;
        color: {p.text_muted};
        font-size: {body_size}px;
        font-weight: 600;
        background: transparent;
    }}
    QPushButton#NavItem:hover {{
        background-color: {p.surface_alt};
        color: {p.text};
    }}
    QPushButton#NavItem:pressed {{
        background-color: {_shade(p.surface_alt, 0.90)};
        color: {p.text};
        border-left: 3px solid {p.accent_press};
    }}
    /* Focus ring differs from hover: an accent left-marker + accent outline,
       so keyboard focus on a nav item reads distinctly from a mouse hover
       (Req 6.3, 6.5). */
    QPushButton#NavItem:focus {{
        color: {p.text};
        border-left: 3px solid {p.accent};
        outline: 2px solid {p.accent};
    }}
    QPushButton#NavItem:checked {{
        background: {p.accent_gradient};
        color: {p.on_accent};
        border-left: 3px solid {p.on_accent};
    }}
    QPushButton#NavItem:disabled {{
        color: {p.text_faint};
        background: transparent;
        border-left: 3px solid transparent;
    }}

    /* ---------- headings ---------- */
    QLabel#PageTitle {{ font-size: {pt_size}px; font-weight: {pt_weight}; color: {p.text};
                        letter-spacing: {pt_ls}px; }}
    QLabel#PageSubtitle {{ font-size: {body_size - 1}px; color: {p.text_muted}; }}
    QLabel#SectionTitle {{ font-size: {st_size}px; font-weight: {st_weight}; color: {p.text};
                           padding-left: {Spacing.MD}px; border-left: 3px solid {p.accent};
                           letter-spacing: {st_ls}px; }}
    QLabel#Metric {{ font-size: {mt_size}px; font-weight: {mt_weight}; color: {p.text};
                     letter-spacing: {mt_ls}px; }}
    QLabel#MetricLabel {{ font-size: {cap_size}px; font-weight: {cap_weight}; color: {p.accent};
                          letter-spacing: {cap_ls}px; }}
    QLabel#Muted {{ color: {p.text_muted}; }}

    /* ---------- buttons (complete state matrix - Req 6.1-6.5) ---------- */
    /* Base button: hover/pressed shade the surface; focus adds a distinct
       accent ring + border (a different mechanism than hover, so keyboard
       focus is never mistaken for a hover - Req 6.3, 6.5); disabled suppresses
       all hover/press feedback (Req 6.4). */
    QPushButton {{
        background-color: {p.surface_alt};
        color: {p.text};
        border: 1px solid {p.border};
        border-radius: {Radius.MD}px;
        padding: {Spacing.SM}px {Spacing.LG}px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {_shade(p.surface_alt, 1.14)};
        border-color: {p.text_faint};
    }}
    QPushButton:pressed {{
        background-color: {_shade(p.surface_alt, 0.88)};
        border-color: {p.accent_press};
    }}
    QPushButton:focus {{
        border: 1px solid {p.accent};
        outline: 2px solid {p.accent};
    }}
    QPushButton:disabled {{
        background-color: {p.surface_alt};
        color: {p.text_faint};
        border-color: {p.border};
    }}

    QPushButton#Primary {{
        background: {p.accent_gradient};
        color: {p.on_accent};
        border: 1px solid transparent;
        border-radius: {Radius.MD}px;
        padding: {Spacing.MD}px {Spacing.XL}px;
        font-size: {st_size}px;
        font-weight: 700;
    }}
    QPushButton#Primary:hover {{ background-color: {_shade(p.accent, 1.12)}; }}
    QPushButton#Primary:pressed {{ background-color: {p.accent_press}; }}
    QPushButton#Primary:focus {{
        border: 1px solid {p.on_accent};
        outline: 2px solid {p.accent_2};
    }}
    QPushButton#Primary:disabled {{ background: {p.surface_alt}; color: {p.text_faint}; }}

    QPushButton#Danger {{
        background-color: {p.danger}; color: {p.on_accent};
        border: 1px solid transparent;
        border-radius: {Radius.MD}px; padding: {Spacing.MD}px {Spacing.LG}px; font-weight: 700;
    }}
    QPushButton#Danger:hover {{ background-color: {_shade(p.danger, 1.12)}; }}
    QPushButton#Danger:pressed {{ background-color: {_shade(p.danger, 0.86)}; }}
    QPushButton#Danger:focus {{
        border: 1px solid {p.on_accent};
        outline: 2px solid {p.danger};
    }}
    QPushButton#Danger:disabled {{ background: {p.surface_alt}; color: {p.text_faint}; }}

    QPushButton#Ghost {{
        background: transparent; border: 1px solid {p.border};
        color: {p.text_muted};
        border-radius: {Radius.MD}px;
    }}
    QPushButton#Ghost:hover {{
        color: {p.text}; border-color: {p.text_faint};
        background-color: {_shade(p.surface_alt, 1.08)};
    }}
    QPushButton#Ghost:pressed {{
        color: {p.text}; background-color: {_shade(p.surface_alt, 0.90)};
        border-color: {p.accent_press};
    }}
    QPushButton#Ghost:focus {{
        color: {p.text};
        border: 1px solid {p.accent};
        outline: 2px solid {p.accent};
    }}
    QPushButton#Ghost:disabled {{ color: {p.text_faint}; border-color: {p.border}; background: transparent; }}

    /* ---------- inputs (complete state matrix - Req 6.1-6.5) ---------- */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: {Radius.MD}px;
        padding: {Spacing.SM}px {Spacing.MD}px;
        color: {p.text};
        selection-background-color: {p.accent};
        selection-color: {p.on_accent};
    }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: {p.text_faint};
        background-color: {_shade(p.surface_alt, 1.06)};
    }}
    /* Focus ring: accent border + accent outline, distinct from the muted
       hover border above (Req 6.3, 6.5). */
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {p.accent};
        outline: 2px solid {p.accent};
        background-color: {p.surface_alt};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        color: {p.text_faint};
        border-color: {p.border};
        background-color: {_shade(p.surface_alt, 0.94)};
    }}
    QComboBox::drop-down {{ border: none; width: {Spacing.XL}px; }}
    QComboBox QAbstractItemView {{
        background-color: {overlay.surface};
        border: 1px solid {overlay.border};
        border-radius: {Radius.SM}px;
        selection-background-color: {p.accent};
        selection-color: {p.on_accent};
        outline: none;
    }}

    /* ---------- progress ---------- */
    QProgressBar {{
        background-color: {p.surface_alt};
        border: none; border-radius: {Radius.SM}px;
        height: {Spacing.MD - 2}px; text-align: center; color: transparent;
    }}
    QProgressBar::chunk {{ background: {p.accent_gradient}; border-radius: {Radius.SM}px; }}

    /* ---------- tables / trees / lists ---------- */
    QTableWidget, QTreeWidget, QListWidget {{
        background-color: {surface.surface};
        border: 1px solid {surface.border};
        border-radius: {Radius.MD}px;
        gridline-color: {p.border};
        outline: none;
        alternate-background-color: {p.surface_alt};
    }}
    /* Item-view focus ring: the whole view gets an accent border when it holds
       keyboard focus, distinct from the row hover treatment below (Req 6.3). */
    QTableWidget:focus, QTreeWidget:focus, QListWidget:focus,
    QTableView:focus, QTreeView:focus {{
        border: 1px solid {p.accent};
    }}
    QHeaderView::section {{
        background-color: {surface.surface};
        color: {p.text_muted};
        border: none;
        border-bottom: 1px solid {p.border};
        padding: {Spacing.MD}px {Spacing.MD}px;
        font-weight: 700;
    }}
    QTableWidget::item, QTreeWidget::item, QListWidget::item {{ padding: {Spacing.MD}px {Spacing.XS}px; }}
    QTreeWidget::branch {{ background: transparent; }}
    QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {{
        background-color: {p.surface_alt};
    }}
    QTableWidget::item:pressed, QTreeWidget::item:pressed, QListWidget::item:pressed {{
        background-color: {_shade(p.surface_alt, 0.90)};
    }}
    QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
        background-color: {p.accent}; color: {p.on_accent};
    }}
    QTableWidget::item:disabled, QTreeWidget::item:disabled, QListWidget::item:disabled {{
        color: {p.text_faint};
    }}
    QTableWidget {{ selection-background-color: {p.accent}; }}

    /* ---------- checkboxes (complete state matrix - Req 6.1-6.5) ---------- */
    QCheckBox {{ spacing: {Spacing.SM}px; color: {p.text}; }}
    QCheckBox:disabled {{ color: {p.text_faint}; }}
    QCheckBox::indicator {{
        width: {Spacing.LG + 2}px; height: {Spacing.LG + 2}px; border-radius: {Radius.SM - 2}px;
        border: 1px solid {p.border}; background: {p.surface_alt};
    }}
    QCheckBox::indicator:hover {{
        border: 1px solid {p.text_faint};
        background: {_shade(p.surface_alt, 1.10)};
    }}
    QCheckBox::indicator:pressed {{
        border: 1px solid {p.accent_press};
        background: {_shade(p.surface_alt, 0.88)};
    }}
    /* Focus ring on the box differs from hover: accent border + accent outline. */
    QCheckBox:focus {{ outline: none; }}
    QCheckBox::indicator:focus {{
        border: 1px solid {p.accent};
        outline: 2px solid {p.accent};
    }}
    QCheckBox::indicator:checked {{ background: {p.accent_gradient}; border: none; }}
    QCheckBox::indicator:checked:hover {{ background: {_shade(p.accent, 1.12)}; border: none; }}
    QCheckBox::indicator:disabled {{
        border: 1px solid {p.border};
        background: {_shade(p.surface_alt, 0.94)};
    }}

    /* item-view (tree/table) checkboxes - styled explicitly so the platform
       style never draws its own (odd-coloured) default indicator */
    QTreeView::indicator, QTreeWidget::indicator,
    QTableView::indicator, QTableWidget::indicator, QListWidget::indicator {{
        width: {Spacing.LG}px; height: {Spacing.LG}px; border-radius: {Radius.SM - 3}px;
        border: 1px solid {p.border}; background: {p.surface_alt};
    }}
    QTreeView::indicator:hover, QTreeWidget::indicator:hover,
    QTableView::indicator:hover, QTableWidget::indicator:hover,
    QListWidget::indicator:hover {{
        border: 1px solid {p.text_faint};
        background: {_shade(p.surface_alt, 1.10)};
    }}
    QTreeView::indicator:checked, QTreeWidget::indicator:checked,
    QTableView::indicator:checked, QTableWidget::indicator:checked,
    QListWidget::indicator:checked {{
        background: {p.accent}; border: 1px solid {p.accent};
    }}
    QTreeView::indicator:checked:hover, QTreeWidget::indicator:checked:hover,
    QTableView::indicator:checked:hover, QTableWidget::indicator:checked:hover,
    QListWidget::indicator:checked:hover {{
        background: {_shade(p.accent, 1.12)}; border: 1px solid {_shade(p.accent, 1.12)};
    }}
    QTreeView::indicator:disabled, QTreeWidget::indicator:disabled,
    QTableView::indicator:disabled, QTableWidget::indicator:disabled,
    QListWidget::indicator:disabled {{
        border: 1px solid {p.border};
        background: {_shade(p.surface_alt, 0.94)};
    }}
    QTreeView::indicator:indeterminate, QTreeWidget::indicator:indeterminate {{
        background: {p.warning}; border: 1px solid {p.warning};
    }}

    /* ---------- scrollbars (token-styled: thin, transparent track, rounded handle) ---------- */
    QScrollBar:vertical {{ background: transparent; width: {Spacing.MD}px; margin: {Spacing.XS}px; }}
    QScrollBar::handle:vertical {{
        background: {p.border}; border-radius: {Radius.SM - 3}px; min-height: {Spacing.XXL - 2}px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_faint}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QScrollBar:horizontal {{ background: transparent; height: {Spacing.MD}px; margin: {Spacing.XS}px; }}
    QScrollBar::handle:horizontal {{
        background: {p.border}; border-radius: {Radius.SM - 3}px; min-width: {Spacing.XXL - 2}px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {p.text_faint}; }}

    /* ---------- status bar ---------- */
    QStatusBar {{ background: {p.sidebar}; color: {p.text_muted};
                  border-top: 1px solid {p.border}; }}
    """


def load_fonts() -> None:
    """Best-effort load of a bundled premium font; silently no-op if absent."""
    if not _HAS_QT:
        return
    # We rely on system "Segoe UI"/"SF Pro"/"Inter" via the QSS font stack.
    # Hook retained so a bundled .ttf can be registered later without API churn.


def apply_theme(app: "QApplication", theme: str = "dark") -> Palette:
    """Apply a named theme ('dark'|'light') to the whole application."""
    palette = THEMES.get(theme, MIDNIGHT)
    if _HAS_QT and app is not None:
        load_fonts()
        base = QFont("Segoe UI", 10)
        app.setFont(base)
        app.setStyle("Fusion")  # consistent cross-platform base for QSS
        app.setStyleSheet(build_stylesheet(palette))
    return palette
