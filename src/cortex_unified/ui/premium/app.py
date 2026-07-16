"""Premium GUI entry point (installed as the ``cortex-gui`` command).

Sets up full debug logging (rotating file + console), routes Qt's own log
messages into Python logging, and installs a global exception hook so nothing
fails silently. Enable verbose debug with the ``CORTEX_DEBUG=1`` env var or the
``--debug`` flag.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

_LOG = logging.getLogger("cortex")


def log_dir() -> Path:
    d = Path.home() / ".cortex_cleaner" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def setup_logging(debug: bool = False) -> Path:
    """Configure root logging: console + rotating file. Returns the log path."""
    level = logging.DEBUG if debug else logging.INFO
    log_file = log_dir() / "cortex.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # handlers filter; capture everything to file
    # Clear any pre-existing handlers (avoids duplicate lines on re-entry).
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    fileh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    fileh.setLevel(logging.DEBUG)  # always full detail in the file
    fileh.setFormatter(fmt)
    root.addHandler(fileh)

    _LOG.info("=== Cortex Cleaner GUI starting (debug=%s) ===", debug)
    _LOG.info("log file: %s", log_file)
    return log_file


def _install_qt_message_handler() -> None:
    """Route Qt's internal warnings/errors into Python logging."""
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:  # pragma: no cover
        return

    qlog = logging.getLogger("cortex.qt")
    level_map = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def handler(mode, context, message):  # noqa: ANN001
        qlog.log(level_map.get(mode, logging.INFO), "%s", message)

    qInstallMessageHandler(handler)


def _install_excepthook() -> None:
    def hook(exc_type, exc_value, exc_tb):
        _LOG.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


def _set_windows_dpi_awareness() -> None:
    """Make the process Per-Monitor-V2 DPI aware on Windows (no-op elsewhere).

    Windows will otherwise bitmap-scale (blur) the whole window when it is
    maximized onto, or moved to, a display running at a fractional scale factor
    (125% / 150% / ...). Declaring Per-Monitor-V2 awareness tells Windows to
    stop virtualizing and let Qt render crisply at the display's real scale.

    This MUST run before any QApplication/QGuiApplication instance exists (once
    Qt has created one it has already told Windows its awareness and this call
    becomes a no-op). Every call is wrapped so a failure can NEVER crash startup
    and so it degrades cleanly on non-Windows / headless environments.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        # 1) Preferred: Per-Monitor-V2 (Win 10 1703+). The awareness *context*
        #    is a pseudo-handle; the documented value for PER_MONITOR_AWARE_V2
        #    is -4 passed as an HANDLE-sized value.
        try:
            user32 = ctypes.windll.user32
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
            if hasattr(user32, "SetProcessDpiAwarenessContext"):
                # Declare the signature explicitly: the context is an
                # HANDLE-sized value and the function returns BOOL. Without this
                # ctypes assumes a C int return, which can misreport success on
                # some builds and make the truthiness check below unreliable.
                fn = user32.SetProcessDpiAwarenessContext
                fn.argtypes = [ctypes.c_void_p]
                fn.restype = ctypes.c_bool
                if fn(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
                    _LOG.debug("DPI awareness: Per-Monitor-V2 (SetProcessDpiAwarenessContext)")
                    return
        except Exception:  # noqa: BLE001 - fall through to older APIs
            pass

        # 2) Fallback: PROCESS_PER_MONITOR_DPI_AWARE (Win 8.1+, shcore.dll).
        try:
            shcore = ctypes.windll.shcore
            PROCESS_PER_MONITOR_DPI_AWARE = 2
            shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
            _LOG.debug("DPI awareness: per-monitor (shcore.SetProcessDpiAwareness)")
            return
        except Exception:  # noqa: BLE001 - fall through to the system-DPI API
            pass

        # 3) Last resort: system-DPI aware (Vista+). Better than virtualized.
        try:
            ctypes.windll.user32.SetProcessDPIAware()
            _LOG.debug("DPI awareness: system (user32.SetProcessDPIAware)")
        except Exception:  # noqa: BLE001 - cosmetic only, never break startup
            pass
    except Exception:  # noqa: BLE001 - ctypes import / windll access failed
        _LOG.debug("DPI awareness setup skipped (unavailable)", exc_info=True)


def _configure_high_dpi() -> None:
    """Configure Qt high-DPI behaviour before the QApplication is constructed.

    Only meaningful when NO QApplication/QGuiApplication instance exists yet:
    the rounding policy and application attributes must be set before
    construction, otherwise Qt ignores them and emits warnings. Each step is
    guarded so it can never crash startup.
    """
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001 - PySide6 unavailable; nothing to do
        return

    # Only touch global policy/attributes when we're the ones creating the app.
    if QApplication.instance() is not None:
        return

    # Don't round the display scale factor down to the nearest integer - pass
    # the real fractional factor (1.25 / 1.5 / ...) through so Qt renders at the
    # display's native scale instead of scaling a rounded bitmap.
    try:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:  # noqa: BLE001 - older/newer Qt without this enum
        pass

    # High-DPI pixmaps are default-on in Qt6/PySide6; set defensively only if
    # the (deprecated) attribute still exists on this build.
    try:
        attr = getattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps", None)
        if attr is not None:
            QApplication.setAttribute(attr, True)
    except Exception:  # noqa: BLE001 - attribute removed/renamed; ignore
        pass


def main() -> int:
    debug = ("--debug" in sys.argv) or os.environ.get("CORTEX_DEBUG") in ("1", "true", "True")
    log_file = setup_logging(debug)

    # Declare DPI awareness to Windows *first*, before Qt is even imported, so
    # the process is never bitmap-scaled (blurred) on high-DPI / scaled
    # displays. No-ops on non-Windows and never raises.
    _set_windows_dpi_awareness()

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        sys.stderr.write(
            "Cortex Cleaner GUI requires PySide6.\n"
            "Install it with:  pip install PySide6\n"
        )
        return 1

    _install_excepthook()

    from .theme import apply_theme
    from .window import PremiumMainWindow

    # Configure Qt's high-DPI scaling policy/attributes before we construct the
    # QApplication (only applied when we're creating a fresh instance).
    _configure_high_dpi()

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Cortex Cleaner")
    app.setOrganizationName("Cortex")
    _install_qt_message_handler()

    apply_theme(app, "dark")

    window = PremiumMainWindow(theme="dark")
    window.show()
    _LOG.info("main window shown; entering event loop")
    try:
        return app.exec()
    finally:
        _LOG.info("event loop exited; log at %s", log_file)


if __name__ == "__main__":
    raise SystemExit(main())
