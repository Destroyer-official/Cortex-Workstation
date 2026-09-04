"""Nexus File Manager page.

The FULL native Qt6 file explorer runs directly inside this page —
same process, same window as Cortex Cleaner. No extra window, no
localhost, no web view.

Production hardening:
- A failure here degrades to an in-page error card; it can never crash
  the main window (all construction is guarded).
- The explorer is a fixed-fill widget: the outer page scroll area stays
  quiet and only the explorer's inner views scroll.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .window import _Page

log = logging.getLogger("cortex.ui.nexus")

_NEXUS_SEARCH_PATHS = [
    Path(__file__).resolve().parents[3] / "NexusExplorer" / "native",  # src/NexusExplorer/native
    Path(__file__).resolve().parents[4] / "src" / "NexusExplorer" / "native",
    Path(__file__).resolve().parents[4] / "NexusExplorer" / "native",
    Path(os.environ.get("CORTEX_NEXUS_DIR", "")) if os.environ.get("CORTEX_NEXUS_DIR") else None,
    Path.home() / "NexusExplorer" / "native",
]
NATIVE_DIR = next((p for p in _NEXUS_SEARCH_PATHS if p and p.is_dir()), _NEXUS_SEARCH_PATHS[0])


def _load_nexus_module():
    """Lazily import the explorer widget when QApplication is running.

    Manages load nexus module operations and coordinates related state changes for the component.
    """
    try:
        from cortex_unified.explorer.widget import DARK_QSS, ExplorerWidget
        if ExplorerWidget is not None:
            return ExplorerWidget, DARK_QSS, None
    except Exception as _exc:
        log.debug("cortex_unified.explorer import fallback: %s", _exc)

    if str(NATIVE_DIR) not in sys.path:
        sys.path.insert(0, str(NATIVE_DIR))
    try:
        from nexus_explorer import DARK_QSS, ExplorerWidget  # type: ignore
        return ExplorerWidget, DARK_QSS, None
    except Exception as _exc:  # pragma: no cover - surfaced in-page
        err = f"{type(_exc).__name__}: {_exc}"
        log.warning("Nexus explorer import failed: %s", err)
        return None, "", err


class _ErrorCard(QWidget):
    """Errorcard.

    Manages ErrorCard operations and coordinates related state changes for the component.
    """
    def __init__(self, message: str, parent=None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            message (str): Informational or progress status message.
            parent: Parent window or shell controller instance.
        """
        super().__init__(parent)
        from PySide6.QtCore import Qt

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Nexus File Manager")
        title.setStyleSheet("font-size:16pt; font-weight:600; color:#e5e9f0;")
        body = QLabel(message)
        body.setWordWrap(True)
        body.setStyleSheet("color:#fbbf24;")
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(title)
        lay.addWidget(body)
        lay.addStretch(1)


class NexusExplorerPage(_Page):
    """The embedded native explorer (in-process Qt6 widget).

    The explorer is heavy (models, timers, native DPI queries), so it is
    constructed lazily on first visit - the same lazy-page discipline every
    other page follows - and never under ``QT_QPA_PLATFORM=offscreen`` (CI),
    where a native explorer cannot function and its timers only produce
    event-loop noise that poisons later tests.
    """

    def __init__(self, win):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            win: Parent window or shell controller instance.
        """
        super().__init__(win)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(0)
        self._built = False
        self._autoload = self._build_explorer
        self._loaded = False

    def _build_explorer(self):
        """_build_explorer.

        Manages build explorer operations and coordinates related state changes for the component.
        """
        if self._built:
            return
        self._built = True
        self._loaded = True

        if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
            self.v.addWidget(_ErrorCard(
                "The native file explorer requires a real display server.\n"
                "It is unavailable in headless (offscreen) mode."
            ))
            self.v.addStretch(1)
            return

        ExplorerWidget, dark_qss, import_error = _load_nexus_module()

        if ExplorerWidget is None:
            self.v.addWidget(_ErrorCard(
                "The native explorer module could not be loaded.\n\n"
                f"{import_error}\n\nExpected module at:\n"
                f"{NATIVE_DIR / 'nexus_explorer.py'}"
            ))
            self.v.addStretch(1)
            return

        try:
            self.explorer = ExplorerWidget(str(Path.home()))
            self.explorer.setStyleSheet(self.explorer.styleSheet() + dark_qss)
            self.explorer.mount_tabs_to_window(self.win)
            self.v.addWidget(self.explorer, 1)
        except Exception:
            log.exception("Nexus explorer failed to build")
            detail = traceback.format_exc(limit=3)
            self.v.addWidget(_ErrorCard(
                "The explorer failed to start:\n" + detail))
            self.v.addStretch(1)
