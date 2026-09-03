"""Crisp, theme-tinted SVG icons.

Why this exists
---------------
Navigation icons used to be Unicode codepoints baked into Python strings
(``\\u25C9``, ``\\u26E8``, ...). That looked amateur for three reasons:

1. **Qt 6 ships no fonts.** Each glyph resolved through whatever system font
   happened to contain that codepoint - on Windows usually a Segoe UI Symbol /
   Segoe UI Emoji fallback - so stroke weights, optical sizes and baselines
   varied per icon, and some machines rendered colour emoji or a tofu box.
2. **They were not distinct.** Five codepoints were reused across pages, so
   Privacy, Firewall and Security all showed the same shield.
3. **They could not be tinted or sized** as part of the design system.

Here every icon is a real SVG rendered through :class:`QSvgRenderer` directly at
the target device pixel ratio, so it is sharp at 100%, 125%, 150% and 200%
scaling - rasterising once at 1x and letting Qt upscale is what produces the
soft, "pixelated" look.

Usage::

    from .icons import icon
    button.setIcon(icon("firewall", 18, palette.text_muted))

Rendered pixmaps are cached per (name, size, colour, dpr). Failures degrade to
an empty :class:`QIcon` rather than raising, because a missing decoration must
never prevent a tool from opening.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap

_LOG = logging.getLogger("cortex.ui.icons")

#: Candidate directories holding the shipped icon set.
_CANDIDATE_ICON_DIRS = [
    Path(__file__).resolve().parents[2] / "resources" / "icons",  # src/cortex_unified/resources/icons
    Path(__file__).resolve().parents[3] / "resources" / "icons",  # src/resources/icons or root
    Path(__file__).parent / "resources" / "icons",
]
#: Canonical directory holding the shipped icon set.
ICON_DIR = next((p for p in _CANDIDATE_ICON_DIRS if p.is_dir()), _CANDIDATE_ICON_DIRS[0])

#: Nominal design size of every icon in the set.
DESIGN_SIZE = 24


@lru_cache(maxsize=256)
def _svg_source(name: str) -> bytes | None:
    """Read an icon's SVG markup, or ``None`` when it is not shipped."""
    path = ICON_DIR / f"{name}.svg"
    try:
        return path.read_bytes()
    except OSError:
        _LOG.warning("icon %r not found at %s", name, path)
        return None


@lru_cache(maxsize=1024)
def _render(name: str, size: int, color: str, dpr_x100: int) -> QPixmap | None:
    """Rasterise *name* at *size* logical px for a given device pixel ratio.

    ``dpr_x100`` is the ratio times 100 so it stays hashable for the cache
    (1.0 -> 100, 1.25 -> 125, 1.5 -> 150).
    """
    source = _svg_source(name)
    if source is None:
        return None

    # ``currentColor`` in the asset is substituted here, so one file serves
    # every theme colour and state without duplicating assets.
    markup = source.replace(b"currentColor", color.encode("ascii", "replace"))

    try:
        from PySide6.QtSvg import QSvgRenderer
    except ImportError:  # pragma: no cover - QtSvg missing from the build
        _LOG.warning("QtSvg unavailable; icons will be blank")
        return None

    renderer = QSvgRenderer(markup)
    if not renderer.isValid():
        _LOG.warning("icon %r contains invalid SVG", name)
        return None

    ratio = max(1.0, dpr_x100 / 100.0)
    # Render at physical resolution, then declare the ratio: Qt then draws it
    # at the right logical size *without* resampling, which is what keeps
    # edges and 1.6px strokes sharp on fractional-scaled displays.
    physical = max(1, round(size * ratio))
    pixmap = QPixmap(physical, physical)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        renderer.render(painter, QRectF(0, 0, physical, physical))
        # Uniform theme tinting: if color is specified and the asset contained
        # hardcoded colors or non-currentColor styling, ensure the rendered
        # shape is uniformly tinted with the target theme palette color.
        if color and (b"#" in source or b"rgb" in source or b"currentColor" not in source):
            from PySide6.QtGui import QColor
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor(color))
    finally:
        painter.end()

    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def _device_pixel_ratio() -> float:
    """Best-effort device pixel ratio of the active screen."""
    try:
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is None:
            return 1.0
        screen = app.primaryScreen()
        return float(screen.devicePixelRatio()) if screen is not None else 1.0
    except Exception:  # noqa: BLE001 - decoration must never break the UI
        return 1.0


def pixmap(name: str, size: int = DESIGN_SIZE, color: str = "#FFFFFF") -> QPixmap:
    """Return a crisp pixmap for *name*, or an empty one when unavailable."""
    ratio = _device_pixel_ratio()
    result = _render(name, int(size), str(color), int(round(ratio * 100)))
    return QPixmap() if result is None else result


def icon(name: str, size: int = DESIGN_SIZE, color: str = "#FFFFFF") -> QIcon:
    """Return a :class:`QIcon` for *name* tinted to *color*.

    The icon carries pixmaps for the requested size plus the common larger
    steps, so Qt never has to upscale when a widget asks for a bigger variant.
    """
    result = QIcon()
    base = pixmap(name, size, color)
    if base.isNull():
        return result
    result.addPixmap(base)
    # Pre-render the sizes Qt is most likely to ask for (toolbars, lists,
    # tray). Cheap thanks to the cache, and avoids any runtime upscaling.
    for step in (size, size * 2):
        extra = pixmap(name, step, color)
        if not extra.isNull():
            result.addPixmap(extra)
    return result


def available() -> frozenset[str]:
    """Every icon name shipped with the application."""
    try:
        return frozenset(p.stem for p in ICON_DIR.glob("*.svg"))
    except OSError:  # pragma: no cover - unreadable install
        return frozenset()


def has_icon(name: str) -> bool:
    """True when *name* is shipped, without rendering it."""
    return (ICON_DIR / f"{name}.svg").is_file()


def icon_size(size: int) -> QSize:
    """Convenience square :class:`QSize` for ``setIconSize``."""
    return QSize(int(size), int(size))


def clear_cache() -> None:
    """Drop cached pixmaps - call after a theme or DPI change."""
    _render.cache_clear()
    _svg_source.cache_clear()


def tinted_color(palette, *, muted: bool = False) -> str:
    """Pick the right stroke colour for *palette* (a ``theme.Palette``)."""
    return palette.text_muted if muted else palette.text


__all__ = [
    "DESIGN_SIZE",
    "ICON_DIR",
    "available",
    "clear_cache",
    "has_icon",
    "icon",
    "icon_size",
    "pixmap",
    "tinted_color",
]
