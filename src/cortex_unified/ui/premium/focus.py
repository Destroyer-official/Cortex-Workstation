"""Focus-visible: show keyboard focus rings only for keyboard navigation.

A premium desktop app should not flash a focus rectangle around a button just
because it was clicked with the mouse (that boxy outline is what makes a UI feel
unpolished), yet keyboard users still need a clear, visible focus indicator to
navigate (Req 10.1). This mirrors the web platform's ``:focus-visible`` rule.

How it works: a single application-level event filter tracks the most recent
input modality - a navigation key press (Tab/Backtab/arrows/Home/End) switches
to "keyboard", any mouse button press switches to "mouse". When a widget gains
focus, a ``focusVisible`` dynamic property is set on it to reflect that modality
and the widget is re-polished so the stylesheet's ``[focusVisible="true"]``
focus rules apply. On focus-out the property is cleared. The theme's button
focus rings are therefore drawn only when focus arrived via the keyboard;
clicking a button shows no ring at all.

Everything is guarded so a stray event can never crash the UI, and installation
is idempotent so re-applying the theme (a theme switch) never stacks filters.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QApplication, QWidget

_LOG = logging.getLogger("cortex.ui.premium.focus")

#: Keys that count as keyboard navigation (arriving focus should show a ring).
_NAV_KEYS = frozenset({
    Qt.Key.Key_Tab,
    Qt.Key.Key_Backtab,
    Qt.Key.Key_Up,
    Qt.Key.Key_Down,
    Qt.Key.Key_Left,
    Qt.Key.Key_Right,
    Qt.Key.Key_Home,
    Qt.Key.Key_End,
})


class FocusVisibleFilter(QObject):
    """App-level filter that gates focus rings on the input modality."""

    def __init__(self, app: QApplication):
        """__init__."""
        super().__init__(app)
        self._keyboard = False
        self._in_event_filter = False

    def eventFilter(self, obj, event):  # noqa: N802
        """eventFilter."""
        if self._in_event_filter:
            return False
        self._in_event_filter = True
        try:
            et = event.type()
            if et == QEvent.Type.KeyPress:
                if event.key() in _NAV_KEYS:
                    self._keyboard = True
            elif et in (QEvent.Type.MouseButtonPress,
                        QEvent.Type.MouseButtonDblClick):
                self._keyboard = False
            elif et == QEvent.Type.FocusIn:
                self._set_visible(obj, self._keyboard)
            elif et == QEvent.Type.FocusOut:
                self._set_visible(obj, False)
        except Exception:  # noqa: BLE001 - focus assist must never crash the UI
            pass
        finally:
            self._in_event_filter = False
        return False

    @staticmethod
    def _set_visible(obj, visible: bool) -> None:
        """_set_visible."""
        if not isinstance(obj, QWidget):
            return
        if bool(obj.property("focusVisible")) == bool(visible):
            return
        obj.setProperty("focusVisible", bool(visible))
        # A dynamic property used in a QSS selector only takes effect after the
        # widget is re-polished by its style.
        style = obj.style()
        if style is not None:
            style.unpolish(obj)
            style.polish(obj)


def install_focus_visible(app: QApplication) -> None:
    """Install the focus-visible filter on *app* once (idempotent)."""
    if app is None:
        return
    if getattr(app, "_cortex_focus_filter", None) is not None:
        return
    try:
        flt = FocusVisibleFilter(app)
        app.installEventFilter(flt)
        app._cortex_focus_filter = flt  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - never break theming if this fails
        _LOG.debug("could not install focus-visible filter", exc_info=True)
