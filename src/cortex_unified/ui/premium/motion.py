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

import os
from typing import Callable

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


# Reduced-motion preference (accessibility / inclusivity). When enabled, callers
# should skip or shorten non-essential motion (page fades, smooth scrolling,
# gauge sweeps) - premium motion must never exclude users who are sensitive to
# it. Defaults from the ``CORTEX_REDUCED_MOTION`` env var and can be toggled at
# runtime (e.g. from a settings switch or an OS query).
_REDUCED_MOTION = os.environ.get("CORTEX_REDUCED_MOTION") in ("1", "true", "True")


def prefers_reduced_motion() -> bool:
    """Return True when non-essential animation should be suppressed.

    Manages prefers reduced motion operations and coordinates related state changes for the component.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    return _REDUCED_MOTION


def set_reduced_motion(value: bool) -> None:
    """Enable/disable the app-wide reduced-motion preference.

    Manages set reduced motion operations and coordinates related state changes for the component.

    Args:
        value (bool): The value parameter.
    """
    global _REDUCED_MOTION
    _REDUCED_MOTION = bool(value)


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
        """Teardown.

        Manages teardown operations and coordinates related state changes for the component.
        """
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


def reveal(
    widget: QWidget,
    duration: int = Duration.NORMAL,
    rise: int = 12,
    on_done: Callable[[], None] | None = None,
):
    """Reveal ``widget`` with a combined fade + gentle upward rise.

    A premium page transition: instead of snapping in, content fades from
    transparent while sliding up a few pixels so it "settles into place". The
    widget must already sit at its final geometry - it is offset downward by
    ``rise`` px, then both the opacity and position animate back together via a
    :class:`QParallelAnimationGroup`.

    Honors :func:`prefers_reduced_motion`: when reduced motion is requested the
    animation is skipped entirely, the widget is left at its final state, and
    ``on_done`` still runs - so motion-sensitive users get an instant, static
    switch. The temporary opacity effect is removed on completion so child card
    rendering (crisp text, borders) is never left routed through an offscreen
    pixmap. Returns the animation group (retain it) or ``None`` under reduced
    motion. Never raises - a failed transition must never break navigation.
    """
    if prefers_reduced_motion():
        try:
            widget.setGraphicsEffect(None)
        except RuntimeError:
            pass
        if on_done is not None:
            on_done()
        return None

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    fade = QPropertyAnimation(effect, b"opacity", widget)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(EASING_STANDARD)

    end_pos = widget.pos()
    start_pos = QPoint(end_pos.x(), end_pos.y() + int(rise))
    widget.move(start_pos)
    slide = QPropertyAnimation(widget, b"pos", widget)
    slide.setDuration(duration)
    slide.setStartValue(start_pos)
    slide.setEndValue(end_pos)
    slide.setEasingCurve(EASING_STANDARD)

    group = QParallelAnimationGroup(widget)
    group.addAnimation(fade)
    group.addAnimation(slide)

    def _teardown() -> None:
        """Teardown.

        Manages teardown operations and coordinates related state changes for the component.
        """
        try:
            widget.setGraphicsEffect(None)
            # Guarantee the final resting position even if a relayout raced us.
            widget.move(end_pos)
        except RuntimeError:
            pass
        if on_done is not None:
            on_done()

    group.finished.connect(_teardown)
    group.start()
    return group


def press_feedback(widget, sink: int = 2) -> None:
    """Give a clickable widget a subtle tactile "sink" on press.

    On press the control eases down ``sink`` px and on release eases back, for a
    premium, physical click feel (paired with the QSS ``:pressed`` colour shift,
    which is the instant sub-120ms acknowledgement). The resting position is
    (re)captured only when no press animation is already in flight, so rapid
    clicks can never make the control drift from its layout position.

    Honors :func:`prefers_reduced_motion` (no movement at all). Works on any
    object exposing ``pressed``/``released`` signals (e.g. ``QPushButton``) and
    never raises - press feedback is delight, never a dependency.
    """
    if not (hasattr(widget, "pressed") and hasattr(widget, "released")):
        return

    def _anim_to(point: QPoint) -> QPropertyAnimation:
        """_anim_to.

        Manages anim to operations and coordinates related state changes for the component.

        Args:
            point (QPoint): The point parameter.

        Returns:
            QPropertyAnimation: Result of the operation.
        """
        anim = QPropertyAnimation(widget, b"pos", widget)
        anim.setDuration(Duration.INSTANT)
        anim.setEndValue(point)
        anim.setEasingCurve(EASING_STANDARD)
        anim.start()
        widget._press_anim = anim  # retain so it is not GC'd mid-flight
        return anim

    def _down() -> None:
        """Down.

        Manages down operations and coordinates related state changes for the component.
        """
        if prefers_reduced_motion():
            return
        # Capture the resting position only when we're not mid-press, so a
        # burst of clicks reuses one stable baseline and never accumulates.
        if not getattr(widget, "_press_active", False):
            widget._press_home = widget.pos()
        widget._press_active = True
        home = widget._press_home
        _anim_to(QPoint(home.x(), home.y() + int(sink)))

    def _up() -> None:
        """Up.

        Manages up operations and coordinates related state changes for the component.
        """
        home = getattr(widget, "_press_home", None)
        if home is None:
            return
        anim = _anim_to(home)
        anim.finished.connect(lambda: setattr(widget, "_press_active", False))

    try:
        widget.pressed.connect(_down)
        widget.released.connect(_up)
    except Exception:  # noqa: BLE001 - press feedback must never break a control
        pass


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
