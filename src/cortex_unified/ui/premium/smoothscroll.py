"""Smooth momentum scrolling for a premium, non-janky scroll feel.

The single biggest thing that makes a desktop UI feel "cheap" is the mouse
wheel jumping the view in coarse, instant steps. Premium apps glide: a wheel
notch eases the content to its new position, and rapid notches accumulate into
one continuous, decelerating motion. This module adds exactly that to any
``QAbstractScrollArea`` (the pages' outer scroll area and the sidebar nav).

Design decisions that keep it feeling *fast*, not floaty, and never fighting the
rest of the app:

* **Mouse wheel only.** Touchpads/precise devices already emit smooth
  pixel-delta scrolling; intercepting those would make them worse, so events
  carrying a pixel delta are passed straight through.
* **Retargeting.** Each notch adds to a running *target* and restarts the ease
  from the current position, so spinning the wheel feels continuous instead of
  resetting.
* **Boundary hand-off.** When the view can't move further in the wheel's
  direction the event is not consumed, so the existing single-container scroll
  policy (``SingleScrollFilter``) can still forward the gesture to the page.
* **Reduced-motion aware.** When :func:`motion.prefers_reduced_motion` is on,
  the filter does nothing and native (instant) scrolling is used.

Everything is guarded so a stray event can never crash the UI.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation
from PySide6.QtWidgets import QAbstractScrollArea

from . import motion

_LOG = logging.getLogger("cortex.ui.premium.smoothscroll")

#: Logical pixels travelled per standard wheel notch (120 angle-delta units).
#: Tuned so one notch moves a comfortable few lines and chained notches glide.
_PIXELS_PER_NOTCH = 92
#: Glide duration - long enough to read as smooth, short enough to feel snappy.
_DURATION_MS = 360


class SmoothScroller(QObject):
    """Animate a scroll area's vertical scrollbar for an eased wheel glide."""

    def __init__(self, area: QAbstractScrollArea, parent: QObject | None = None):
        """__init__."""
        super().__init__(parent or area)
        self._area = area
        self._bar = area.verticalScrollBar()
        self._target = self._bar.value() if self._bar is not None else 0
        self._anim = QPropertyAnimation(self._bar, b"value", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(_DURATION_MS)
        # Filter wheel events on the scroll area's viewport (this is also the
        # object SingleScrollFilter forwards page-scroll gestures to, so those
        # forwarded scrolls get smoothed too).
        vp = area.viewport()
        if vp is not None:
            vp.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        """eventFilter."""
        if event.type() != QEvent.Type.Wheel:
            return False
        try:
            return self._on_wheel(event)
        except Exception:  # noqa: BLE001 - scrolling must never crash the UI
            _LOG.debug("smooth scroll wheel handling failed", exc_info=True)
            return False

    def _on_wheel(self, event) -> bool:
        """_on_wheel."""
        bar = self._bar
        if bar is None:
            return False
        # Reduced-motion: don't animate; let native (instant) scrolling run.
        if motion.prefers_reduced_motion():
            return False
        # Touchpads / high-precision devices emit a pixel delta and are already
        # smooth - leave them entirely alone.
        pixel = event.pixelDelta()
        if pixel is not None and not pixel.isNull():
            return False
        delta = event.angleDelta().y()
        if delta == 0:
            return False
        low, high = bar.minimum(), bar.maximum()
        if low >= high:
            return False  # nothing to scroll: let the gesture propagate/hand off

        # If a glide isn't already running, start accumulating from where the
        # bar actually is (so a fresh gesture responds from the current spot).
        if self._anim.state() != QPropertyAnimation.State.Running:
            self._target = bar.value()

        step = int(round(-delta / 120.0 * _PIXELS_PER_NOTCH))
        new_target = max(low, min(high, self._target + step))
        # Already pinned at the boundary in this direction: don't consume, so
        # SingleScrollFilter can forward the gesture to the outer page.
        if new_target == self._target and bar.value() == new_target:
            return False

        self._target = new_target
        self._anim.stop()
        self._anim.setStartValue(bar.value())
        self._anim.setEndValue(self._target)
        self._anim.start()
        return True  # consumed: we own this scroll


def install_smooth_scroll(area: QAbstractScrollArea) -> SmoothScroller | None:
    """Attach smooth wheel scrolling to *area* once (idempotent). Never raises."""
    if area is None:
        return None
    existing = getattr(area, "_cortex_smooth_scroller", None)
    if existing is not None:
        return existing
    try:
        scroller = SmoothScroller(area)
        area._cortex_smooth_scroller = scroller  # type: ignore[attr-defined]
        return scroller
    except Exception:  # noqa: BLE001 - a failure here must never break the page
        _LOG.debug("could not install smooth scroll", exc_info=True)
        return None
