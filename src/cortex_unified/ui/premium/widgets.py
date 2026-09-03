"""Reusable premium widgets: elevated cards, a custom circular gauge, stat
cards, and risk badges. These provide the visual polish (rounded elevation,
smooth animated gauge) that plain QSS cannot.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import motion
from .theme import MONO_FAMILIES, Palette
from .tokens import Elevation, Radius, Spacing, elevation_style

_LOG = logging.getLogger("cortex.ui.premium")


class Card(QFrame):
    """An elevated, rounded surface.

    Depth is conveyed by the elevation-aware QSS treatment (a lighter surface
    than the backdrop, a token border, and - for hero/glass surfaces - a subtle
    top-edge highlight), all of which paint directly onto the window at the
    display's native device-pixel ratio and therefore stay crisp at any size or
    scale factor.

    Why no ``QGraphicsDropShadowEffect``: attaching any ``QGraphicsEffect``
    forces Qt to rasterize the whole widget - *including its text* - into an
    offscreen ARGB pixmap and then composite that pixmap. That offscreen path
    has two crispness costs on high-DPI / scaled Windows displays:

    * it cannot use the platform's subpixel (ClearType) text antialiasing (a
      translucent pixmap has no known background to blend against), so all text
      on the card renders with softer greyscale antialiasing; and
    * on Qt < 6.4 the source pixmap is generated at 1x and upscaled by the scale
      factor, so the entire card looks blurry/"pixelated" when maximized.

    Rendering the surface via QSS instead keeps every card - and the text on it -
    sharp, while the elevation scale still makes depth order perceivable
    (Req 12.1, 12.2). ``_elevation`` is retained for callers/tests that read the
    resolved treatment.
    """

    def __init__(self, palette: Palette, object_name: str = "Card", parent=None):
        """Resolve and store the token elevation treatment for the card's surface level."""
        super().__init__(parent)
        self.setObjectName(object_name)
        # Resolve the token elevation treatment (surface/border/shadow metrics)
        # so depth stays token-driven and monotonic (Req 12.1, 12.2). Hero/glass
        # surfaces sit at the RAISED level; plain cards at the SURFACE level. The
        # visible fill/border/top-highlight are applied by the elevation-aware
        # QSS selectors (#Card / #HeroCard / #Glass) - no blurring graphics
        # effect is used, so the card and its text render crisply on any display.
        level = (
            Elevation.RAISED
            if object_name in ("HeroCard", "Glass")
            else Elevation.SURFACE
        )
        self._elevation = elevation_style(palette, level)


class StatCard(Card):
    """A small metric tile: big number + caption."""

    def __init__(self, palette: Palette, label: str, value: str = "—", parent=None):
        """Build the tile: a big Metric value label above an uppercased caption."""
        super().__init__(palette, parent=parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        self._value = QLabel(value)
        self._value.setObjectName("Metric")
        self._caption = QLabel(label.upper())
        self._caption.setObjectName("MetricLabel")
        lay.addWidget(self._value)
        lay.addWidget(self._caption)

    def value(self) -> str:
        """Return the current displayed text value."""
        return self._value.text()

    def set_value(self, text: str, animate: bool = False) -> None:
        """Set the displayed value, optionally pulsing the fade-in animation on change."""
        changed = text != self._value.text()
        self._value.setText(text)
        if animate and changed:
            self._pulse()

    def _pulse(self) -> None:
        """A quick fade-in on the value - a subtle premium 'it updated' cue.

        Opt-in (animate=True) so live cards that refresh every second don't
        flicker. Used for one-shot results like a completed scan.
        """
        try:
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            eff = QGraphicsOpacityEffect(self._value)
            self._value.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", self)
            # One-shot result cue driven by the shared motion system (Req 4.4).
            anim.setDuration(motion.Duration.SLOW)
            anim.setStartValue(0.25)
            anim.setEndValue(1.0)
            anim.setEasingCurve(motion.EASING_STANDARD)
            anim.finished.connect(lambda: self._value.setGraphicsEffect(None))
            self._value_anim = anim
            anim.start()
        except Exception:  # noqa: BLE001 - cosmetic only
            pass


class Badge(QLabel):
    """A small pill for risk/status labels."""

    _COLORS = {
        "low": ("success", "SAFE"),
        "medium": ("warning", "REVIEW"),
        "high": ("danger", "CAUTION"),
    }

    @staticmethod
    def _rgb(hex_color: str) -> tuple[int, int, int]:
        """Parse ``#RRGGBB`` -> (r, g, b); degrade to the accent blue on error."""
        s = str(hex_color).strip().lstrip("#")
        if len(s) == 3:
            s = "".join(ch * 2 for ch in s)
        try:
            return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        except Exception:  # noqa: BLE001
            return 110, 139, 255

    def __init__(self, palette: Palette, kind: str = "low", text: str | None = None, parent=None):
        """Build a pill styled from the palette's semantic color for ``kind``."""
        super().__init__(parent)
        color_attr, default_text = self._COLORS.get(kind, ("info", kind.upper()))
        color = getattr(palette, color_attr)
        # Build the translucent fill/border from explicit rgba() rather than an
        # 8-digit ``#RRGGBBAA`` hex: Qt style sheets don't reliably parse the
        # alpha-hex form (it can be mis-read as #AARRGGBB, giving a muddy,
        # wrong-coloured pill), which is what made the badges look distorted.
        r, g, b = self._rgb(color)
        self.setText(text or default_text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"background-color: rgba({r}, {g}, {b}, 0.16); color: {color}; "
            f"border: 1px solid rgba({r}, {g}, {b}, 0.48); "
            f"border-radius: 9px; padding: 2px 10px; font-size: 11px; font-weight: 700;"
        )
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)


class CircularGauge(QWidget):
    """Animated circular progress ring with a centered value + caption.

    Used for the dashboard "health / reclaimable" hero. Value is 0..100.
    """

    def __init__(self, palette: Palette, caption: str = "", parent=None):
        """Initialize value/caption/glow state and the shared-motion sweep animation."""
        super().__init__(parent)
        self._p = palette
        self._value = 0.0
        self._display = "0"
        self._caption = caption
        # Optional accent glow around the progress arc, painted directly in
        # paintEvent (see set_glow) so it stays crisp on high-DPI displays.
        self._glow_color: str | None = None
        self._glow_radius = 0
        self._glow_alpha = 0
        self.setMinimumSize(168, 168)
        self.setMaximumHeight(210)
        self._anim = QPropertyAnimation(self, b"value", self)
        # One-shot gauge sweep uses the shared motion timings/easing (Req 4.4).
        self._anim.setDuration(motion.Duration.SLOW)
        self._anim.setEasingCurve(motion.EASING_STANDARD)

    # animatable property -------------------------------------------------
    def _get_value(self) -> float:
        """Return the current animated value (0..100)."""
        return self._value

    def _set_value(self, v: float) -> None:
        """Set the animated value property and repaint."""
        self._value = v
        self.update()

    value = Property(float, _get_value, _set_value)

    def animate_to(self, target: float, display: str | None = None) -> None:
        """Animate the ring to a clamped target, updating the center display text."""
        self._display = display if display is not None else f"{int(target)}"
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(max(0.0, min(100.0, target)))
        self._anim.start()

    def set_center_text(self, text: str) -> None:
        """Replace the gauge's center readout text and repaint."""
        self._display = text
        self.update()

    def set_glow(self, color_hex: str, radius: int = 34, alpha: int = 55) -> None:
        """Enable a crisp accent glow around the progress arc.

        Called by :func:`attach_glow`. The glow is rendered inside
        :meth:`paintEvent` as a few concentric, fading arc strokes at the
        display's native resolution, so it reads as a soft "lit" halo while
        staying perfectly sharp on high-DPI / scaled displays - unlike a
        ``QGraphicsDropShadowEffect``, which would rasterize the whole gauge
        (and its centered text) into a 1x offscreen pixmap and blur it.
        """
        self._glow_color = color_hex
        self._glow_radius = max(0, int(radius))
        self._glow_alpha = max(0, min(255, int(alpha)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        """Paint the track ring, glow, gradient progress arc, and centered text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        margin = 14
        rect = QRectF(
            (self.width() - side) / 2 + margin,
            (self.height() - side) / 2 + margin,
            side - 2 * margin,
            side - 2 * margin,
        )
        thickness = max(10, side // 14)

        # track - the ring background is a raised surface derived from the
        # elevation scale so its depth cue stays token-driven (Req 12.1, 12.2).
        track_style = elevation_style(self._p, Elevation.RAISED)
        track = QPen(QColor(track_style.surface), thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.drawArc(rect, 0, 360 * 16)

        # progress arc (start at top, clockwise) - token-defined accent gradient
        # (Req 12.6). Prefer the palette's gradient stops; fall back to the
        # accent/accent_2 pair when no stops are defined.
        span = int(-self._value / 100.0 * 360 * 16)

        # Crisp accent glow: a few concentric, fading strokes drawn under the
        # progress arc at device resolution (see set_glow). This gives the arc a
        # soft "lit" halo without routing the widget through a blurring offscreen
        # graphics effect, so it stays sharp when the window is maximized on a
        # scaled display.
        if self._glow_color and self._glow_radius > 0 and self._value > 0:
            layers = 4
            for i in range(layers, 0, -1):
                frac = i / layers
                gcol = QColor(self._glow_color)
                gcol.setAlpha(max(0, int(self._glow_alpha * (1.0 - frac) + 6)))
                gw = thickness + int(self._glow_radius * frac)
                gpen = QPen(gcol, gw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(gpen)
                painter.drawArc(rect, 90 * 16, span)

        grad = QConicalGradient(rect.center(), 90.0)
        stops = tuple(getattr(self._p, "accent_grad_stops", ()) or ())
        if stops:
            for pos, color in stops:
                grad.setColorAt(max(0.0, min(1.0, float(pos))), QColor(color))
        else:
            grad.setColorAt(0.0, QColor(self._p.accent))
            grad.setColorAt(1.0, QColor(self._p.accent_2))
        arc = QPen(QBrush(grad), thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(arc)
        painter.drawArc(rect, 90 * 16, span)

        # center value - a tabular monospace "HUD" readout; auto-fit the font so
        # long text (e.g. "102.9 MB") never overflows or gets clipped by the ring.
        painter.setPen(QColor(self._p.text))
        inner_w = rect.width() - 2 * thickness - 6
        size = max(10, int(side * 0.16))
        f = QFont()
        f.setFamilies(MONO_FAMILIES)
        f.setWeight(QFont.Weight.ExtraBold)
        while size > 9:
            f.setPointSize(size)
            if QFontMetrics(f).horizontalAdvance(self._display) <= inner_w:
                break
            size -= 1
        painter.setFont(f)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._display)

        # caption below center
        if self._caption:
            painter.setPen(QColor(self._p.text_muted))
            cf = QFont("Segoe UI", max(9, int(side * 0.055)), QFont.Weight.DemiBold)
            painter.setFont(cf)
            cap_rect = QRectF(rect.x(), rect.center().y() + side * 0.14, rect.width(), side * 0.14)
            painter.drawText(cap_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._caption)
        painter.end()


class CoreBars(QWidget):
    """A compact strip of per-CPU-core usage bars, colour-coded by load.

    Green under 50%, amber under 80%, red at/above 80% - an at-a-glance read of
    which cores are busy. Pure QPainter, no dependency.
    """

    def __init__(self, palette: Palette, parent=None):
        """Initialize with an empty per-core value list and fixed minimum height."""
        super().__init__(parent)
        self._p = palette
        self._values: list[float] = []
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_values(self, values: list[float]) -> None:
        """Store a clamped list of per-core percentages and repaint."""
        self._values = [max(0.0, min(100.0, float(v))) for v in values]
        self.update()

    def _bar_color(self, pct: float) -> QColor:
        """Return the load color: red at 80%+, amber at 50%+, accent below."""
        if pct >= 80:
            return QColor(getattr(self._p, "danger", "#FB7185"))
        if pct >= 50:
            return QColor(getattr(self._p, "warning", "#FBBF24"))
        return QColor(self._p.accent)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Paint the per-core track/fill bars and core-number labels."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self._values)
        if n == 0:
            painter.end()
            return
        w, h = self.width(), self.height()
        top_pad, bottom_pad = 6, 16
        usable_h = h - top_pad - bottom_pad
        gap = 6
        bar_w = max(6.0, (w - gap * (n + 1)) / n)
        painter.setFont(QFont("Segoe UI", 8))
        for i, pct in enumerate(self._values):
            x = gap + i * (bar_w + gap)
            # track
            track = QColor(self._p.surface_alt)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(track)
            painter.drawRoundedRect(QRectF(x, top_pad, bar_w, usable_h), 4, 4)
            # fill
            fill_h = usable_h * pct / 100.0
            painter.setBrush(self._bar_color(pct))
            painter.drawRoundedRect(
                QRectF(x, top_pad + (usable_h - fill_h), bar_w, fill_h), 4, 4)
            # label
            painter.setPen(QColor(self._p.text_muted))
            painter.drawText(QRectF(x, h - bottom_pad, bar_w, bottom_pad),
                             Qt.AlignmentFlag.AlignCenter, str(i))
        painter.end()


class TrafficGraph(QWidget):
    """A lightweight dual-line time-series graph (download + upload rates).

    Keeps a rolling window of samples and draws two filled lines. Values are in
    bytes/sec; the widget autoscales to the peak in the current window and
    labels the peak. No external plotting dependency - pure QPainter, cheap.
    """

    def __init__(self, palette: Palette, capacity: int = 120, parent=None):
        """Initialize empty rolling download/upload sample lists with the given capacity."""
        super().__init__(parent)
        self._p = palette
        self._cap = capacity
        self._down: list[float] = []
        self._up: list[float] = []
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def add_sample(self, down_rate: float, up_rate: float) -> None:
        """Append a (down, up) rate sample, trimming to the rolling window."""
        self._down.append(max(0.0, down_rate))
        self._up.append(max(0.0, up_rate))
        if len(self._down) > self._cap:
            self._down.pop(0)
            self._up.pop(0)
        self.update()

    def clear(self) -> None:
        """Drop all samples and repaint."""
        self._down.clear()
        self._up.clear()
        self.update()

    @staticmethod
    def _fmt_rate(bps: float) -> str:
        """Format a bytes/sec rate with the largest fitting unit."""
        v = float(bps)
        for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
            if v < 1024 or unit == "GB/s":
                return f"{v:.1f} {unit}"
            v /= 1024
        return f"{bps} B/s"

    def paintEvent(self, event) -> None:  # noqa: N802
        """Paint the graph: grid lines, both filled series, and the peak label."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad = 8

        painter.fillRect(self.rect(), QColor(self._p.surface_alt))

        # grid lines
        grid = QPen(QColor(self._p.border), 1, Qt.PenStyle.DotLine)
        painter.setPen(grid)
        for i in range(1, 4):
            y = pad + (h - 2 * pad) * i / 4
            painter.drawLine(pad, int(y), w - pad, int(y))

        peak = max([1.0] + self._down + self._up)

        def _draw(series: list[float], color: str):
            """Draw one filled+stroked series line scaled to the window peak."""
            if len(series) < 2:
                return
            from PySide6.QtGui import QPainterPath
            n = len(series)
            step = (w - 2 * pad) / max(1, self._cap - 1)
            x0 = w - pad - (n - 1) * step
            path = QPainterPath()
            path.moveTo(x0, h - pad)
            for i, val in enumerate(series):
                x = x0 + i * step
                y = (h - pad) - (val / peak) * (h - 2 * pad)
                path.lineTo(x, y)
            path.lineTo(x0 + (n - 1) * step, h - pad)
            path.closeSubpath()
            c = QColor(color)
            fill = QColor(color)
            fill.setAlpha(60)
            painter.fillPath(path, fill)
            painter.setPen(QPen(c, 2))
            prev = None
            for i, val in enumerate(series):
                x = x0 + i * step
                y = (h - pad) - (val / peak) * (h - 2 * pad)
                if prev is not None:
                    painter.drawLine(int(prev[0]), int(prev[1]), int(x), int(y))
                prev = (x, y)

        _draw(self._down, self._p.accent)
        _draw(self._up, getattr(self._p, "warning", "#e0a000"))

        # peak label
        painter.setPen(QColor(self._p.text_muted))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(pad + 2, pad + 12, f"peak {self._fmt_rate(peak)}")
        painter.end()


def attach_glow(widget, color_hex: str, radius: int = 26, alpha: int = 130) -> None:
    """Give ``widget`` a crisp accent glow that reads as a lit-from-within cue.

    Historically this attached an offset-0 coloured ``QGraphicsDropShadowEffect``.
    That is avoided now because any ``QGraphicsEffect`` makes Qt rasterize the
    widget - *and the text on it* - into an offscreen ARGB pixmap before
    compositing. On high-DPI / scaled Windows displays that offscreen path drops
    subpixel (ClearType) text antialiasing and, on Qt < 6.4, is generated at 1x
    then upscaled, which is exactly what made the buttons and gauge look soft /
    "pixelated" when the window was maximized.

    Instead the glow is rendered crisply where it can be:

    * Widgets that own their painting (e.g. :class:`CircularGauge`, which exposes
      ``set_glow``) draw the halo themselves at the display's native resolution.
    * For other controls (the hero call-to-action buttons) no blurring effect is
      applied; their token accent-gradient fill and focus ring already convey a
      premium, "lit" look and stay perfectly sharp at any scale.

    The signature is unchanged so existing call sites keep working. Never raises.
    """
    try:
        set_glow = getattr(widget, "set_glow", None)
        if callable(set_glow):
            set_glow(color_hex, radius, alpha)
    except Exception:  # noqa: BLE001 - a glow is purely cosmetic, never fatal
        pass


# Cache of resolved native icons keyed by source path (Req 8.2). A path maps to
# either a QIcon or ``None`` (icon unavailable); crucially the ``None`` result is
# cached too, so a path that has no native icon is looked up at most once and is
# never re-fetched during the app's 1s live refreshes (Property 11).
_ICON_CACHE: dict[str, "object"] = {}
_ICON_PROVIDER = None
# Token-styled placeholder glyphs, keyed by the palette colors + size they were
# drawn from so each theme reuses a single shared icon instance.
_PLACEHOLDER_CACHE: dict[str, "QIcon"] = {}


def icon_for_exe(exe_path: str):
    """Return a QIcon for a program's real icon (cached), or ``None``.

    Uses only the local system's native icon provider (Qt's
    ``QFileIconProvider``) so it works without extra dependencies, matches the
    icon Windows Explorer shows, and never issues a network request (Req 8.1,
    8.4).

    The result is cached by source ``exe_path`` so repeated live refreshes reuse
    the same object and perform at most one provider lookup per path (Req 8.2).
    A ``None`` result (no native icon, or any lookup failure) is cached as well,
    so unavailable icons are not retried on every refresh; callers render a
    token placeholder in that case (see :func:`placeholder_icon`, Req 8.3).
    """
    global _ICON_PROVIDER
    if not exe_path:
        return None
    # Membership test (not truthiness) so a cached ``None`` short-circuits and no
    # second provider lookup ever happens for the same path (Property 11).
    if exe_path in _ICON_CACHE:
        return _ICON_CACHE[exe_path]
    try:
        from PySide6.QtCore import QFileInfo
        from PySide6.QtWidgets import QFileIconProvider
        if _ICON_PROVIDER is None:
            _ICON_PROVIDER = QFileIconProvider()
        info = QFileInfo(exe_path)
        icon = _ICON_PROVIDER.icon(info)
        if icon.isNull():
            icon = None
    except Exception:  # noqa: BLE001 - any failure degrades to the placeholder
        icon = None
    _ICON_CACHE[exe_path] = icon
    return icon


def placeholder_icon(palette: Palette | None = None, size: int = 32) -> QIcon:
    """Return a token-styled placeholder glyph for items lacking a native icon.

    When :func:`icon_for_exe` resolves to ``None`` (Req 8.3) a row must still
    show *something* rather than a blank cell. This draws a small generic
    "application" glyph entirely from Design_Tokens - the palette's surface,
    border, and accent colors plus the shared corner-radius scale - so the
    fallback stays visually consistent with the active theme and requires no
    external asset or network access (Req 8.4).

    The rendered icon is cached by the token colors + size + device-pixel
    ratio, so a live list refresh reuses one shared placeholder per theme
    instead of repainting it per row, and monitors at different scale factors
    don't collide on the same cache entry. The pixmap is rendered into a backing
    store scaled by the display's device-pixel ratio (and tagged via
    ``setDevicePixelRatio``) so the glyph stays crisp on high-DPI / scaled
    displays instead of being bitmap-upscaled. Any failure degrades to an empty
    ``QIcon`` rather than raising.
    """
    surface = getattr(palette, "surface_alt", None) or getattr(palette, "surface", "#2A2E37")
    border = getattr(palette, "border", "#3A3F4B")
    accent = getattr(palette, "accent", "#6EA8FE")
    # Resolve the target device-pixel ratio so the icon is rendered at the
    # display's real resolution. Fail soft to 1.0 (headless / no app instance).
    dpr = 1.0
    try:
        from PySide6.QtGui import QGuiApplication
        _app = QGuiApplication.instance()
        val = float(_app.devicePixelRatio()) if _app is not None else 1.0
        if val and val > 0:
            dpr = val
    except Exception:  # noqa: BLE001 - no app / headless: keep dpr = 1.0
        dpr = 1.0
    # Cache key includes the dpr so a 1.0 and a 1.5 monitor keep distinct icons.
    key = f"{surface}|{border}|{accent}|{size}|{dpr:.3f}"
    cached = _PLACEHOLDER_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        # Paint into a backing store scaled by the device-pixel ratio, then tag
        # the pixmap with that ratio so Qt draws it at `size` logical px while
        # keeping the extra device pixels for crispness on scaled displays.
        backing = max(1, int(round(size * dpr)))
        pm = QPixmap(backing, backing)
        pm.setDevicePixelRatio(dpr)
        pm.fill(QColor(0, 0, 0, 0))  # transparent canvas
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Draw in logical coordinates: the painter honours the pixmap's DPR, so
        # all geometry stays in `size`-based units and simply renders sharper.
        radius = float(Radius.SM)
        pad = 3.0
        body = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)
        painter.setBrush(QColor(surface))
        painter.setPen(QPen(QColor(border), 1.5))
        painter.drawRoundedRect(body, radius, radius)
        # A simple generic glyph: a smaller accent-tinted rounded square, enough
        # to read as "an app/file with no icon" without implying any real brand.
        inner = size * 0.30
        glyph = QRectF(inner, inner, size - 2 * inner, size - 2 * inner)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(accent))
        painter.drawRoundedRect(glyph, radius * 0.5, radius * 0.5)
        painter.end()
        icon = QIcon(pm)
    except Exception:  # noqa: BLE001 - cosmetic only, never break a list fill
        icon = QIcon()
    _PLACEHOLDER_CACHE[key] = icon
    return icon


def hline(palette: Palette) -> QFrame:
    """A thin horizontal divider."""
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background-color: {palette.border}; border: none;")
    return line


#: Status name -> (icon asset, palette attribute holding its colour).
_STATUS_STYLE = {
    "info": ("info", "info"),
    "warning": ("warning", "warning"),
    "success": ("success", "success"),
    "error": ("error", "danger"),
}


def status_note(palette: Palette, status: str, text: str) -> QWidget:
    """An icon + message row for platform notes, warnings and results.

    Replaces the older pattern of prefixing a label with a symbol codepoint
    (``QLabel("\\u2139  ... only available on Windows.")``). That embedded an
    icon inside a user-facing string and relied on system font fallback, which
    Qt 6 does not guarantee - the same note could render as a thin outline, a
    colour emoji, or a missing-glyph box depending on the machine.

    Here the icon is a crisp SVG tinted from the palette's semantic colour, and
    the message stays a clean string. The status is also carried in the
    accessible name, so meaning is never conveyed by colour alone.
    """
    from .icons import icon_size, pixmap

    asset, color_attr = _STATUS_STYLE.get(status, _STATUS_STYLE["info"])
    color = getattr(palette, color_attr, palette.text_muted)

    row = QWidget()
    row.setObjectName("StatusNote")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(Spacing.SM)

    glyph = QLabel()
    glyph.setPixmap(pixmap(asset, 15, color))
    glyph.setFixedSize(icon_size(15))
    glyph.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    lay.addWidget(glyph, 0, Qt.AlignmentFlag.AlignTop)

    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(True)
    lay.addWidget(label, 1)

    row.setAccessibleName(f"{status}: {text}")
    return row


def title_block(title: str, subtitle: str = "") -> QWidget:
    """A page header (title + subtitle)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    lay.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("PageSubtitle")
        lay.addWidget(s)
    return w


def require_feature(page_or_parent, feature) -> bool:
    """Gate a UI action behind *feature*; offer the trial when denied.

    Why here and not in :mod:`cortex_unified.licensing.gating`: the licensing
    package is GUI-agnostic (the CLI and engine call it too) and must never
    open dialogs or know about widgets. This is the UI-side counterpart: when
    the action's tier is not licensed it explains the upgrade path (needed
    tier vs. current tier) and - when this machine has never used its trial -
    offers a one-click "Start Free Trial" button, so a gated click becomes a
    conversion moment instead of a dead end.

    Usage at the top of an action handler::

        if not require_feature(self, Feature.SENTINEL_PRO):
            return

    Returns True when the action may proceed (already allowed, or the user
    started the trial right from the dialog, which activates it immediately).
    Returns False when denied and nothing was started. The dialog is parented
    to *page_or_parent* so it stays modal to the window, and any failure to
    read the license fails closed (denied) exactly like ``gating.allowed``.
    Never raises.
    """
    # Imported lazily so importing the widget module costs nothing and never
    # drags the licensing stack into processes that only want paint helpers.
    from cortex_unified.licensing import Tier
    from cortex_unified.licensing.license_manager import (
        TRIAL_DAYS,
        get_license_manager,
    )
    from cortex_unified.licensing.tiers import FEATURE_MIN_TIER

    try:
        manager = get_license_manager()
        state = manager.validate()
    except Exception as exc:  # noqa: BLE001 - gating must never break callers
        _LOG.debug("license validation failed; denying %s: %s", feature.value, exc)
        return False

    if state.allows(feature):
        return True

    required = FEATURE_MIN_TIER.get(feature, Tier.FREE)
    _LOG.info(
        "gated action blocked: %s needs %s, machine is on %s",
        feature.value, required.value, state.tier.value,
    )
    box = QMessageBox(page_or_parent)
    box.setWindowTitle("Upgrade required")
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(
        f"{feature.value.replace('.', ' ').title()} requires the "
        f"{required.value.title()} edition."
    )
    box.setInformativeText(f"Your current tier: {state.tier.value.title()}.")

    # The trial is available until first used - mirror start_trial()'s own
    # preconditions so the button is only offered when clicking it can work.
    # Kept on the box for tests (and honest introspection): None means "no
    # trial was offered".
    trial_btn: QWidget | None = None
    if not state.licensed and not state.trial:
        trial_btn = box.addButton("Start Free Trial", QMessageBox.ButtonRole.AcceptRole)
    box.addButton(QMessageBox.StandardButton.Close)
    box.setDefaultButton(QMessageBox.StandardButton.Close)
    box._trial_button = trial_btn
    box.exec()

    if trial_btn is None or box.clickedButton() is not trial_btn:
        return False
    try:
        manager.start_trial()
    except RuntimeError as exc:
        # Raced/exhausted between showing the dialog and clicking; say so
        # honestly instead of pretending the trial started.
        _LOG.info("trial refused from upgrade dialog: %s", exc)
        QMessageBox.information(page_or_parent, "Trial unavailable", str(exc))
        return False
    _LOG.info("trial started from upgrade dialog (%s days, PRO)", TRIAL_DAYS)
    return True
