"""Motion system: a single shared set of animation durations and easing curves
plus a couple of thin ``QPropertyAnimation`` factory helpers used by every
animation in the app.

Centralizing motion here means page fade-ins, stat-card pulses, and gauge
sweeps all share the same timing language, so transitions feel intentional and
consistent rather than abrupt or random. This module depends only on
``PySide6.QtCore`` (and ``QtWidgets`` for the opacity effect) so its timing
constants stay easy to assert against under Qt's ``offscreen`` platform.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class Duration:
    """Named animation durations, in milliseconds.

    ``INSTANT`` is reserved for micro-interaction feedback and stays under the
    120 ms hover-feedback budget; ``NORMAL`` is the page-appearance duration and
    sits inside the 150-300 ms window; ``SLOW`` drives one-shot metric/gauge
    updates.
    """

    INSTANT = 90
    FAST = 160
    NORMAL = 220
    SLOW = 320


# Shared easing curves. ``STANDARD`` is the default decelerating curve used for
# most entrances and value changes; ``EMPHASIS`` is a symmetric ease used where
# a change should feel more deliberate.
EASING_STANDARD = QEasingCurve.Type.OutCubic
EASING_EMPHASIS = QEasingCurve.Type.InOutCubic


def fade_in(
    widget: QWidget,
    duration: int = Duration.NORMAL,
    on_done: Callable[[], None] | None = None,
) -> QPropertyAnimation:
    """Fade ``widget`` in from transparent to fully opaque.

    A temporary ``QGraphicsOpacityEffect`` drives the animation and is removed
    when the animation finishes, so the widget returns to its normal rendering
    path (drop shadows on child cards are never suppressed once the fade
    completes). The optional ``on_done`` callback runs after teardown.

    The returned animation is started immediately; callers should keep a
    reference to it so it is not garbage-collected before it finishes.
    """
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(EASING_STANDARD)

    def _teardown() -> None:
        # Guard against the widget having been deleted mid-animation.
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
        if on_done is not None:
            on_done()

    anim.finished.connect(_teardown)
    anim.start()
    return anim


def animate_property(
    target,
    prop: bytes,
    start,
    end,
    duration: int = Duration.SLOW,
    easing: QEasingCurve.Type = EASING_STANDARD,
) -> QPropertyAnimation:
    """Animate a Qt property ``prop`` on ``target`` from ``start`` to ``end``.

    Used for one-shot result updates (metric/gauge sweeps). The animation is
    parented to ``target`` and started immediately; the caller should retain a
    reference so it survives until ``finished``.
    """
    anim = QPropertyAnimation(target, prop, target)
    anim.setDuration(duration)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setEasingCurve(easing)
    anim.start()
    return anim
