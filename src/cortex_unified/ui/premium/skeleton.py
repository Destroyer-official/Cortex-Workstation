"""Skeleton shimmer: a reassuring "loading" placeholder for premium feel.

Blank space or a bare spinner while a scan runs reads as "stuck / cheap".
Premium apps show a *skeleton* - grey placeholder bars shaped like the content
that's coming - with a soft highlight sweeping across, so the wait feels
intentional and fast. This module provides one self-contained widget that any
page can drop in while a worker runs and hide when results arrive.

The sweep is driven by an animated float property (0..1, looping) and painted at
the display's native resolution, so it stays crisp on high-DPI/scaled displays.
It honors :func:`motion.prefers_reduced_motion`: when reduced motion is on the
bars are drawn statically (still communicating "loading") with no sweep.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import motion
from .theme import Palette
from .tokens import Radius

class ShimmerSkeleton(QWidget):
    """Animated placeholder bars used as a loading state.

    ``rows`` grey bars are drawn with a soft accent-tinted highlight sweeping
    left-to-right on a loop. Call :meth:`start` when a load begins and
    :meth:`stop` when it ends (typically paired with ``setVisible``).
    """

    def __init__(self, palette: Palette, rows: int = 5, row_height: int = 20,
                 parent: QWidget | None = None):
        """Initialize skeleton.

        Initializes the instance and configures internal state.

        Args:
            palette (Palette): The palette parameter.
            rows (int): Table row index or list of row indices.
            row_height (int): The row height parameter.
            parent (QWidget | None): Parent window or shell controller instance.
        """
        super().__init__(parent)
        self._p = palette
        self._rows = max(1, int(rows))
        self._row_h = max(6, int(row_height))
        self._gap = 14
        self._phase = 0.0
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(self._rows * (self._row_h + self._gap))
        self._anim = QPropertyAnimation(self, b"phase", self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1150)
        self._anim.setLoopCount(-1)

    # animatable sweep phase ------------------------------------------------
    def _get_phase(self) -> float:
        """_get_phase.

        Manages get phase operations and coordinates related state changes for the component.

        Returns:
            float: Result of the operation.
        """
        return self._phase

    def _set_phase(self, v: float) -> None:
        """_set_phase.

        Manages set phase operations and coordinates related state changes for the component.

        Args:
            v (float): The v parameter.
        """
        self._phase = v
        self.update()

    phase = Property(float, _get_phase, _set_phase)

    # lifecycle -------------------------------------------------------------
    def start(self) -> None:
        """Start active background operations.

        Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.
        """
        if motion.prefers_reduced_motion():
            self.update()
            return
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._anim.start()

    def stop(self) -> None:
        """Stop active background operations.

        Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.
        """
        self._anim.stop()

    def set_palette(self, palette: Palette) -> None:
        """set_palette.

        Manages set palette operations and coordinates related state changes for the component.

        Args:
            palette (Palette): The palette parameter.
        """
        self._p = palette
        self.update()

    # painting --------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        """Render custom visual elements and borders for the widget.

        Uses QPainter with active theme colors, gradients, and font metrics to draw specialized UI graphics.

        Args:
            event: The Qt event object.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        base = QColor(getattr(self._p, "surface_alt", "#1A1F2B"))
        # A soft highlight tinted toward the accent so it feels on-brand.
        hi = QColor(getattr(self._p, "accent", "#35D0EE"))
        hi.setAlpha(46)

        w = self.width()
        radius = float(Radius.SM)
        y = 0.0
        # The sweep centre travels a bit beyond the edges so the band fully
        # enters and exits rather than popping at the boundaries.
        centre = (self._phase * 1.4 - 0.2) * w
        band = max(80.0, w * 0.28)

        for i in range(self._rows):
            # Vary bar width slightly so it reads as content, not a solid block.
            frac = 1.0 if i % 3 else 0.72
            bar = QRectF(0.0, y, max(1.0, w * frac), float(self._row_h))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(base)
            painter.drawRoundedRect(bar, radius, radius)

            # Moving highlight band, clipped to this bar.
            if not motion.prefers_reduced_motion():
                grad = QLinearGradient(centre - band, 0, centre + band, 0)
                transparent = QColor(hi)
                transparent.setAlpha(0)
                grad.setColorAt(0.0, transparent)
                grad.setColorAt(0.5, hi)
                grad.setColorAt(1.0, transparent)
                painter.setBrush(grad)
                painter.drawRoundedRect(bar, radius, radius)
            y += self._row_h + self._gap
        painter.end()
