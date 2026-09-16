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

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

log = logging.getLogger("cortex.ui.nexus")

# Dynamically locate native directory across dev, frozen, and custom install paths
NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[3] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


def _load_nexus_module():
    """Dynamically load the Nexus ExplorerWidget module regardless of install location."""
    ensure_nexus_in_sys_path()

    # 1. Try unified explorer wrapper
    try:
        from cortex_unified.explorer.widget import DARK_QSS, ExplorerWidget

        if ExplorerWidget is not None:
            return ExplorerWidget, DARK_QSS, None
    except Exception as _exc:
        log.debug("cortex_unified.explorer import fallback: %s", _exc)

    # 2. Try direct import from sys.path (ensured via ensure_nexus_in_sys_path)
    try:
        from nexus_explorer import DARK_QSS, ExplorerWidget  # type: ignore

        if ExplorerWidget is not None:
            return ExplorerWidget, DARK_QSS, None
    except Exception as _exc:
        log.debug("nexus_explorer direct import fallback: %s", _exc)

    # 3. Try package-qualified import
    try:
        from NexusExplorer.native.nexus_explorer import DARK_QSS, ExplorerWidget  # type: ignore

        if ExplorerWidget is not None:
            return ExplorerWidget, DARK_QSS, None
    except Exception as _exc:
        err = f"{type(_exc).__name__}: {_exc}"
        log.warning("Nexus explorer import failed: %s", err)
        return None, "", err

    return None, "", "ExplorerWidget could not be resolved from any candidate source"


class _ErrorCard(QWidget):
    """_ErrorCard (QWidget) implementing ErrorCard. Methods include __init__()."""

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
        """Build the build explorer widget tree for the page."""
        if self._built:
            return
        self._built = True
        self._loaded = True

        if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
            self.v.addWidget(
                _ErrorCard(
                    "The native file explorer requires a real display server.\n"
                    "It is unavailable in headless (offscreen) mode."
                )
            )
            self.v.addStretch(1)
            return

        ExplorerWidget, dark_qss, import_error = _load_nexus_module()

        if ExplorerWidget is None:
            self.v.addWidget(
                _ErrorCard(
                    "The native explorer module could not be loaded.\n\n"
                    f"{import_error}\n\nExpected module at:\n"
                    f"{NATIVE_DIR / 'nexus_explorer.py'}"
                )
            )
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
            self.v.addWidget(_ErrorCard("The explorer failed to start:\n" + detail))
            self.v.addStretch(1)
