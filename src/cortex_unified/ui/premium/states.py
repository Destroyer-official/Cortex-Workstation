"""Reusable loading / empty / error state panels for data-backed pages.

Every page that fetches or computes data through the Worker_Runtime needs the
same three honest feedback states: a Loading_State while work runs (Req 7.1), an
Empty_State when a completed operation produced no results (Req 7.2), and an
Error_State carrying a human-readable message when something fails (Req 7.3).
Rather than each of the 41+ pages reinventing these, :class:`StatePanel` gives
them a single, token-styled, offscreen-safe widget that behaves identically
everywhere.

The panel is deliberately built so its current state is *assertable* from a
headless test via :meth:`StatePanel.mode`, which returns exactly one of
``"loading"`` / ``"empty"`` / ``"error"`` / ``"hidden"`` (Req 11.4). The three
``show_*`` methods are mutually exclusive and :meth:`clear` returns the panel to
the hidden state so the real results content can be revealed (Req 7.4).

Honesty rules baked in:

* Loading shows an **indeterminate** indicator by default and only becomes a
  determinate percentage when the caller passes real work-unit counts from the
  worker (Req 2.4) - never a synthetic/fabricated percentage.
* Error shows the worker's failure ``message`` **verbatim** and offers a retry
  affordance; it never fabricates a success outcome (Req 7.3, 7.5).

This module depends on ``tokens``, ``motion``, and ``theme`` - the shared design
system - so its styling and (optional) entrance motion stay consistent with the
rest of the app.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import motion
from .theme import Palette
from .tokens import Spacing, TYPE_ROLES

# The four mutually-exclusive states the panel can be in. ``mode()`` always
# returns exactly one of these (Req 11.4).
MODE_HIDDEN = "hidden"
MODE_LOADING = "loading"
MODE_EMPTY = "empty"
MODE_ERROR = "error"

# Non-color-coded glyphs per state. Semantic meaning is carried by the adjacent
# text kicker as well as color, so the state never depends on color alone.
_GLYPH = {
    MODE_LOADING: "⟳",
    MODE_EMPTY: "∅",
    MODE_ERROR: "⚠",
}


class StatePanel(QWidget):
    """Inline panel with mutually-exclusive loading / empty / error states.

    Construct one per data-backed region and place it where the results will
    appear. Drive it from the page's worker lifecycle::

        panel.show_loading()            # on worker start (Req 7.1)
        ...                             # worker runs on the Worker_Runtime
        panel.show_empty("No results")  # completed with zero results (Req 7.2)
        panel.show_error(msg)           # failed - verbatim message (Req 7.3)
        panel.clear()                   # results ready - reveal them (Req 7.4)

    The panel styles itself from the active :class:`Palette` and the shared
    spacing/radius/typography tokens, and hides itself entirely in the hidden
    state so it never occupies space over real content.
    """

    #: Emitted when the user activates the retry affordance shown in the error
    #: state. Pages connect this to re-run the failed operation.
    retryRequested = Signal()

    def __init__(self, palette: Palette, parent: QWidget | None = None) -> None:
        """__init__."""
        super().__init__(parent)
        self.setObjectName("StatePanel")
        self._palette = palette
        self._mode = MODE_HIDDEN
        self._on_retry: Callable[[], None] | None = None
        self._anim = None  # retain the fade so it isn't garbage-collected mid-run
        # Result widgets to hide while a state is shown and reveal on clear().
        self._content: list[QWidget] = []

        self._build_ui()
        # Start hidden: no state is shown until a page asks for one.
        self.clear()

    # ---------------------------------------------------------- content --
    def bind_content(self, *widgets: QWidget) -> None:
        """Register the page's result widget(s) this panel stands in for.

        While the panel is in any visible state (loading / empty / error) the
        bound widgets are hidden, and :meth:`clear` reveals them again - so the
        Loading_State is *replaced* by the results content when data arrives
        (Req 7.4) and the panel never sits on top of a stale table. Pass the
        primary results view(s) for the page (a table, tree, or card). ``None``
        entries are ignored. Safe to call after construction; it immediately
        syncs visibility to the current mode.
        """
        self._content = [w for w in widgets if w is not None]
        self._sync_content()

    def _sync_content(self) -> None:
        """Show bound result widgets only when the panel itself is hidden."""
        reveal = self._mode == MODE_HIDDEN
        for w in self._content:
            try:
                w.setVisible(reveal)
            except Exception:  # noqa: BLE001 - visibility sync must never crash
                pass

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        """_build_ui."""
        p = self._palette
        cap_size, cap_weight, cap_ls = TYPE_ROLES["caption"]
        title_size, title_weight, _ = TYPE_ROLES["section_title"]
        body_size = TYPE_ROLES["body"][0]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(Spacing.XL, Spacing.XL, Spacing.XL, Spacing.XL)
        outer.setSpacing(Spacing.MD)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Large state glyph (updated per mode). Sized well above body text so it
        # reads as the focal point of the panel.
        self._glyph = QLabel()
        self._glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._glyph.setStyleSheet(
            f"color: {p.text_muted}; font-size: {title_size * 2}px; font-weight: 800;"
        )

        # A short kicker naming the state ("LOADING" / "NOTHING HERE" / "ERROR").
        # It conveys the state through text (not color alone) so the meaning is
        # accessible regardless of the semantic color used (Req 10.5).
        self._kicker = QLabel()
        self._kicker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._kicker.setStyleSheet(
            f"color: {p.text_muted}; font-size: {cap_size}px; "
            f"font-weight: {cap_weight}; letter-spacing: {cap_ls}px;"
        )

        # The main human-readable message. For the error state this holds the
        # worker's failure text verbatim (Req 7.3), so it must wrap and be
        # selectable for copy/paste when a user reports an issue.
        self._message = QLabel()
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setWordWrap(True)
        self._message.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._message.setStyleSheet(
            f"color: {p.text}; font-size: {body_size}px; font-weight: 600;"
        )

        # Loading indicator. Defaults to indeterminate (range 0..0) so an
        # unmeasurable operation never shows a synthetic percentage (Req 2.4);
        # a determinate range is only set when real counts are supplied.
        self._progress = QProgressBar()
        self._progress.setObjectName("StateProgress")
        self._progress.setTextVisible(False)
        self._progress.setRange(0, 0)
        self._progress.setFixedWidth(220)
        self._progress.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Retry affordance for the error state (Req 7.3). Hidden otherwise.
        self._retry = QPushButton("Retry")
        self._retry.setObjectName("Ghost")
        self._retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self._retry.clicked.connect(self._handle_retry)

        for w in (self._glyph, self._kicker, self._message, self._progress, self._retry):
            outer.addWidget(w, 0, Qt.AlignmentFlag.AlignHCenter)

    # -------------------------------------------------------------- public --
    def mode(self) -> str:
        """Return the current state: loading / empty / error / hidden.

        This is the assertable state hook headless tests use to verify that the
        panel is in exactly the expected state (Req 11.4). It always reflects
        the last ``show_*`` / :meth:`clear` call.
        """
        return self._mode

    def show_loading(
        self,
        text: str = "Working…",
        current: int | None = None,
        total: int | None = None,
    ) -> None:
        """Enter the Loading_State (Req 7.1).

        By default the progress indicator is **indeterminate** - honest for an
        operation whose remaining work isn't measurable (Req 2.4). When the
        caller passes real work-unit counts (``current`` and a positive
        ``total``) from the worker's progress signal, the indicator becomes
        determinate and reflects those actual counts (Req 2.3); the value is
        never a fabricated/synthetic percentage.
        """
        self._message.setText(text)
        if total is not None and total > 0:
            # Determinate: derived from real work-unit counts (Req 2.3).
            self._progress.setRange(0, int(total))
            self._progress.setValue(int(max(0, min(total, current or 0))))
        else:
            # Indeterminate busy indicator (Req 2.4).
            self._progress.setRange(0, 0)
        self._set_mode(MODE_LOADING)

    def show_empty(self, text: str) -> None:
        """Enter the Empty_State describing the absence of results (Req 7.2)."""
        self._message.setText(text)
        self._set_mode(MODE_EMPTY)

    def show_error(
        self,
        message: str,
        on_retry: Callable[[], None] | None = None,
    ) -> None:
        """Enter the Error_State showing ``message`` verbatim (Req 7.3, 7.5).

        The message is displayed exactly as provided by the worker's ``failed``
        signal - never reworded or replaced with a fabricated success. An
        optional ``on_retry`` callback is invoked (in addition to the
        :attr:`retryRequested` signal) when the user activates the retry
        affordance, letting the page return to an interactive idle state and
        re-run the operation.
        """
        # Preserve the exact text; only guard against a None so the label is
        # always a string.
        self._message.setText("" if message is None else str(message))
        self._on_retry = on_retry
        self._set_mode(MODE_ERROR)

    def clear(self) -> None:
        """Return to the hidden state so real results can be revealed (Req 7.4).

        Hides the panel entirely (it stops occupying layout space) and drops any
        pending retry callback.
        """
        self._on_retry = None
        self._set_mode(MODE_HIDDEN)

    # ------------------------------------------------------------- private --
    def _handle_retry(self) -> None:
        """_handle_retry."""
        cb = self._on_retry
        # Emit for any listeners first, then invoke the direct callback.
        self.retryRequested.emit()
        if cb is not None:
            try:
                cb()
            except Exception:  # noqa: BLE001 - a bad callback must not crash the UI
                pass

    def _set_mode(self, mode: str) -> None:
        """Apply ``mode`` as the single active state and update visibility.

        Enforces mutual exclusivity: exactly the widgets relevant to ``mode``
        are shown, all others hidden, and the whole panel is hidden when the
        mode is ``hidden``. A subtle entrance fade is played on becoming
        visible, wrapped so a motion failure never blocks the state change.
        """
        was_visible = self._mode != MODE_HIDDEN
        self._mode = mode

        if mode == MODE_HIDDEN:
            self.setVisible(False)
            self._sync_content()
            return

        # Per-mode widget visibility (mutually exclusive content).
        self._glyph.setText(_GLYPH.get(mode, ""))
        self._glyph.setVisible(True)
        self._message.setVisible(True)
        self._progress.setVisible(mode == MODE_LOADING)
        self._retry.setVisible(mode == MODE_ERROR)

        # Kicker text + semantic tint per state (text carries the meaning; the
        # color is a secondary cue - Req 10.5).
        if mode == MODE_LOADING:
            self._kicker.setText("LOADING")
            self._tint(self._palette.text_muted)
        elif mode == MODE_EMPTY:
            self._kicker.setText("NOTHING HERE")
            self._tint(self._palette.text_muted)
        else:  # MODE_ERROR
            self._kicker.setText("ERROR")
            self._tint(self._palette.danger)
        self._kicker.setVisible(True)

        self.setVisible(True)
        # Hide the real results while a state is shown (revealed again on clear).
        self._sync_content()

        # Subtle entrance fade only when transitioning from hidden -> visible,
        # so switching between visible states doesn't re-flash. Fail soft.
        if not was_visible:
            try:
                self._anim = motion.fade_in(self, duration=motion.Duration.FAST)
            except Exception:  # noqa: BLE001 - motion is decorative
                self._anim = None

    def _tint(self, color: str) -> None:
        """Recolor the glyph + kicker to ``color`` for the active state."""
        cap_size, cap_weight, cap_ls = TYPE_ROLES["caption"]
        title_size = TYPE_ROLES["section_title"][0]
        self._glyph.setStyleSheet(
            f"color: {color}; font-size: {title_size * 2}px; font-weight: 800;"
        )
        self._kicker.setStyleSheet(
            f"color: {color}; font-size: {cap_size}px; "
            f"font-weight: {cap_weight}; letter-spacing: {cap_ls}px;"
        )


# ============================================================================
# Micro-interaction helpers (Req 12.5)
# ============================================================================
#
# These add the small, tactile feedback animations that make Interactive_Controls
# feel alive when hovered or focused. They are governed entirely by the shared
# Motion_System timings so their feel stays consistent with the rest of the app,
# and every hover-feedback duration stays inside the 120 ms micro-interaction
# budget (``motion.Duration.INSTANT`` is 90 ms).
#
# Both helpers are *decorative*: a failure to install or play an effect must
# never raise or leave the target widget broken. Every entry point is wrapped so
# any exception is swallowed and the widget simply renders without the nicety.


class _HoverLift(QObject):
    """Event filter that gently lifts its target widget upward on hover.

    On the pointer entering the widget it animates the widget's position up by
    ``dy`` pixels using a Motion_System duration, and returns it to rest on
    leave. The animation runs on the widget's ``pos`` property (no graphics
    effect), so it composes cleanly with other decoration such as a focus ring
    glow. All work is guarded so a motion failure never disrupts input handling.
    """

    def __init__(self, widget: QWidget, dy: int, duration: int) -> None:
        """__init__."""
        super().__init__(widget)
        self._widget = widget
        self._dy = int(dy)
        self._duration = int(duration)
        self._base_pos: QPoint | None = None
        self._anim = None  # retain the animation so it isn't garbage-collected mid-run
        widget.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        """eventFilter."""
        try:
            et = event.type()
            if et == QEvent.Type.Enter:
                self._animate_to(-self._dy)
            elif et == QEvent.Type.Leave:
                self._animate_to(0)
        except Exception:  # noqa: BLE001 - decoration must never break input
            pass
        # Never consume the event: hover styling / clicks must still work.
        return False

    def _animate_to(self, offset: int) -> None:
        """_animate_to."""
        w = self._widget
        # Capture the layout-assigned resting position lazily, the first time we
        # are hovered, so we always return exactly to where the layout put us.
        if self._base_pos is None:
            self._base_pos = QPoint(w.pos())
        target = QPoint(self._base_pos.x(), self._base_pos.y() + offset)
        try:
            self._anim = motion.animate_property(
                w,
                b"pos",
                w.pos(),
                target,
                duration=self._duration,
                easing=motion.EASING_STANDARD,
            )
        except Exception:  # noqa: BLE001 - fall back to an instant move
            try:
                w.move(target)
            except Exception:  # noqa: BLE001
                pass


class _FocusRing(QObject):
    """Event filter that blooms an accent glow around a focused widget.

    Complements the QSS ``:focus`` rules with a soft accent-colored drop shadow
    so keyboard focus is unmistakable even on surfaces where a border alone is
    subtle. The glow is only applied when the widget has no other graphics
    effect, so it never clobbers an existing decoration (e.g. an attached glow);
    it is removed again on focus-out. Fully guarded to fail soft.
    """

    def __init__(self, widget: QWidget, accent: str) -> None:
        """__init__."""
        super().__init__(widget)
        self._widget = widget
        self._accent = accent
        self._effect: QGraphicsDropShadowEffect | None = None
        widget.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        """eventFilter."""
        try:
            et = event.type()
            if et == QEvent.Type.FocusIn:
                self._apply(True)
            elif et == QEvent.Type.FocusOut:
                self._apply(False)
        except Exception:  # noqa: BLE001 - decoration must never break focus
            pass
        return False

    def _apply(self, on: bool) -> None:
        """_apply."""
        w = self._widget
        # Also expose focus as a dynamic property so QSS ``[focusRing="true"]``
        # rules (or a repolish of the standard ``:focus`` rules) can react.
        try:
            w.setProperty("focusRing", bool(on))
            style = w.style()
            if style is not None:
                style.unpolish(w)
                style.polish(w)
        except Exception:  # noqa: BLE001
            pass

        if on:
            # Don't overwrite an existing effect owned by someone else.
            if w.graphicsEffect() is not None:
                return
            try:
                eff = QGraphicsDropShadowEffect(w)
                eff.setBlurRadius(18)
                eff.setOffset(0, 0)
                col = QColor(self._accent)
                col.setAlpha(180)
                eff.setColor(col)
                w.setGraphicsEffect(eff)
                self._effect = eff
            except Exception:  # noqa: BLE001
                self._effect = None
        else:
            # Only remove the glow we installed ourselves.
            if self._effect is not None and w.graphicsEffect() is self._effect:
                try:
                    w.setGraphicsEffect(None)
                except RuntimeError:
                    pass
            self._effect = None


def install_hover_lift(
    widget: QWidget,
    dy: int = 1,
    duration: int = motion.Duration.INSTANT,
) -> None:
    """Attach a subtle upward hover-lift Micro_Interaction to ``widget`` (Req 12.5).

    On hover the widget rises by ``dy`` pixels over ``duration`` milliseconds
    (defaulting to ``motion.Duration.INSTANT`` = 90 ms, comfortably inside the
    120 ms hover-feedback budget) and settles back on leave, using the shared
    Motion_System easing. Reserved for hero call-to-action buttons and cards to
    keep the concurrent-animation count low.

    Fails soft: if the effect cannot be installed for any reason the widget is
    left untouched and no exception propagates.
    """
    if widget is None:
        return
    try:
        # The filter parents itself to the widget, so it lives as long as the
        # widget and is cleaned up with it.
        _HoverLift(widget, dy=dy, duration=duration)
    except Exception:  # noqa: BLE001 - decoration must never break the widget
        pass


def focus_ring(widget: QWidget, accent: str | None = None) -> None:
    """Ensure ``widget`` shows a visible focus-ring affordance (Req 12.5).

    Guarantees the widget can receive keyboard focus (promoting a ``NoFocus``
    policy to ``StrongFocus``) and blooms a soft accent glow while focused, so
    keyboard focus is always unmistakable. ``accent`` defaults to the active
    theme's accent color when a :class:`Palette` isn't threaded through.

    Fails soft: any failure leaves the widget untouched without raising.
    """
    if widget is None:
        return
    try:
        # A focus ring is meaningless if the widget can't take focus; make sure
        # it can (without downgrading a stronger existing policy).
        if widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
            widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        col = accent if accent is not None else _default_accent()
        _FocusRing(widget, accent=col)
    except Exception:  # noqa: BLE001 - decoration must never break the widget
        pass


def _default_accent() -> str:
    """Best-effort accent color for the focus ring when none is supplied."""
    try:
        from .theme import MIDNIGHT

        return MIDNIGHT.accent
    except Exception:  # noqa: BLE001
        return "#6E8BFF"
