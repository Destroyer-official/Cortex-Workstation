"""Standalone launcher for the native Nexus explorer (Qt6).

The explorer itself lives in nexus_explorer.ExplorerWidget so it can also be
embedded directly inside Cortex Cleaner. This file only wraps it in a window
and restores last session via QSettings.

Run:  python native/nexus_native_app.py [path]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: E402

from nexus_explorer import DARK_QSS  # noqa: E402


def main() -> int:
    """Main.

    Manages main operations and coordinates related state changes for the component.

    Returns:
        int: Result of the operation.
    """
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    app = QApplication(sys.argv)
    app.setApplicationName("Nexus Explorer")
    app.setStyleSheet(DARK_QSS)

    settings = QSettings("Nexus", "NexusExplorer")
    start = args[0] if args else str(
        settings.value("lastPath", os.path.expanduser("~")))

    from nexus_explorer import ExplorerWidget
    win = QMainWindow()
    win.setWindowTitle("Nexus Explorer")

    # Restore window geometry
    geom = settings.value("windowGeometry")
    if geom:
        win.restoreGeometry(geom)
    else:
        win.resize(1240, 760)

    widget = ExplorerWidget(start)
    win.setCentralWidget(widget)

    # Restore sidebar visibility
    sidebar_vis = settings.value("sidebarVisible", True, type=bool)
    if not sidebar_vis:
        widget._toggle_sidebar()

    def on_quit():
        """on_quit.

        Manages on quit operations and coordinates related state changes for the component.
        """
        settings.setValue("lastPath", widget._tab()["path"])
        settings.setValue("windowGeometry", win.saveGeometry())
        settings.setValue("sidebarVisible", widget._sidebar_visible)

    app.aboutToQuit.connect(on_quit)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
