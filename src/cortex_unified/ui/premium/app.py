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
    """Return application log directory.

    Manages log dir operations and coordinates related state changes for the component.

    Returns:
        Path: Result of the operation.
    """
    d = Path.home() / ".cortex_workstation" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def setup_logging(debug: bool = False) -> Path:
    """Configure root logging: console + rotating file. Returns the log path.

    Manages setup logging operations and coordinates related state changes for the component.

    Args:
        debug (bool): The debug parameter.

    Returns:
        Path: Result of the operation.
    """
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

    if sys.stderr is not None:
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

    _LOG.info("=== Cortex Workstation starting (debug=%s) ===", debug)
    _LOG.info("log file: %s", log_file)
    return log_file


def _install_qt_message_handler() -> None:
    """Route Qt's internal warnings/errors into Python logging.

    Initiates the package or update installation workflow in the background, monitoring execution progress.
    """
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
        """Handler.

        Manages handler operations and coordinates related state changes for the component.

        Args:
            mode: The mode parameter.
            context: The context parameter.
            message: Informational or progress status message.
        """
        qlog.log(level_map.get(mode, logging.INFO), "%s", message)

    qInstallMessageHandler(handler)


def _install_excepthook() -> None:
    """_install_excepthook.

    Initiates the package or update installation workflow in the background, monitoring execution progress.
    """
    def hook(exc_type, exc_value, exc_tb):
        """Hook.

        Manages hook operations and coordinates related state changes for the component.

        Args:
            exc_type: Error message string or exception instance.
            exc_value: Error message string or exception instance.
            exc_tb: Error message string or exception instance.
        """
        _LOG.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        # Persist a user-submittable crash report next to the logs. Paths in
        # the traceback can contain user filenames - anyone sharing this file
        # should review it first (noted in installer/README.md).
        try:
            import time
            import traceback
            target_dir = Path(log_dir())
            target_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d_%H%M%S")
            report = target_dir / f"crash_{stamp}.txt"
            report.write_text(
                "Cortex Cleaner crash report\n"
                "NOTE: paths below may contain personal filenames.\n\n"
                + "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
                encoding="utf-8")
        except Exception:  # noqa: BLE001 - logging already captured it
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hook


def _install_threading_excepthook() -> None:
    """Log exceptions that kill worker threads.

    ``sys.excepthook`` never fires for threads; without this, a crash in a
    QThread worker (e.g. inside a native widget's loader) vanishes with no
    traceback - exactly the kind of failure that is then impossible to
    diagnose from the logs.
    """
    import threading

    def hook(args: threading.ExceptHookArgs) -> None:
        """Hook.

        Manages hook operations and coordinates related state changes for the component.

        Args:
            args (threading.ExceptHookArgs): The args parameter.
        """
        if args.exc_type is SystemExit:
            return
        _LOG.critical(
            "Uncaught exception in thread %r",
            args.thread.name if args.thread is not None else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = hook


def _schedule_update_check(win, settings=None) -> None:
    """One background update check after the window settles - opt-in only.

    Runs solely when the user enabled ``update_check`` in Settings: a cleaner
    that knows the user's software inventory must not phone home without
    consent. Strictly informational - the result appears in the status bar;
    nothing is downloaded or installed (installer/README.md documents the
    path to a verified auto-update channel). Never opens a modal dialog.
    """
    if settings is not None and not settings.update_check:
        return

    def _done():
        """Handle completion of the asynchronous task.

        Processes the returned result payload, updates corresponding tables or UI views, and restores interactive controls.
        """
        try:
            from cortex_unified.system_tools.update_checker import check_for_update
            result = check_for_update()
        except Exception:  # noqa: BLE001 - never disturb startup
            return
        if result.get("status") == "update_available":
            win.statusBar().showMessage(
                f"Update available: version {result.get('latest')} is "
                "published (you are on "
                f"{result.get('installed')}). Download from the project "
                "releases page.", 15000)

    try:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(20000, _done)
    except ImportError:
        pass


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
    """Main.

    Manages main operations and coordinates related state changes for the component.

    Returns:
        int: Result of the operation.
    """
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
    _install_threading_excepthook()

    from .settings_store import SettingsStore
    from .theme import apply_theme
    from .window import PremiumMainWindow

    # Configure Qt's high-DPI scaling policy/attributes before we construct the
    # QApplication (only applied when we're creating a fresh instance).
    _configure_high_dpi()

    # Set AppUserModelID so Windows taskbar uses Cortex Workstation identity and icon
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Destroyer.CortexWorkstation.App.1.2.0")
    except Exception:
        pass

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Cortex Workstation")
    app.setApplicationDisplayName("Cortex Workstation")
    app.setOrganizationName("Cortex")
    _install_qt_message_handler()

    # Apply application icon
    from PySide6.QtGui import QIcon
    icon_candidates = [
        Path(__file__).resolve().parents[2] / "resources" / "icons" / "cortex.ico",
        Path(__file__).resolve().parents[2] / "resources" / "icons" / "cortex.png",
        Path(__file__).resolve().parents[4] / "assets" / "icons" / "cortex.ico",
        Path(__file__).resolve().parents[4] / "assets" / "icons" / "cortex.png",
        Path(getattr(sys, "_MEIPASS", "")) / "assets" / "icons" / "cortex.ico",
        Path(getattr(sys, "_MEIPASS", "")) / "src" / "cortex_unified" / "resources" / "icons" / "cortex.ico",
    ]
    app_icon = None
    for icp in icon_candidates:
        if icp.is_file():
            app_icon = QIcon(str(icp))
            break
    if app_icon and not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Restore the user's saved theme (defaults to dark). The store is shared
    # with the window so a theme change made in Settings persists to one file.
    settings = SettingsStore()
    # Apply the saved reduced-motion preference before any UI animates.
    from . import motion
    motion.set_reduced_motion(settings.reduced_motion)
    theme = settings.theme
    apply_theme(app, theme)

    window = PremiumMainWindow(theme=theme, settings=settings)
    if app_icon and not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.show()
    _LOG.info("main window shown; entering event loop")
    _schedule_update_check(window, settings)
    try:
        code = app.exec()
    finally:
        _LOG.info("event loop exited; log at %s", log_file)
    stuck = getattr(window, "_workers_stuck", None)
    if stuck:
        # A worker thread did not honour cancel + quit within the shutdown
        # grace period. Those QThreads were detached + leaked on purpose
        # rather than force-killed: destroying a running QThread aborts the
        # process ("QThread: Destroyed while thread is still running",
        # 0xC0000409), and QThread.terminate() is not a safe substitute either
        # - it can fire while the thread holds a CRT/heap lock (as it does
        # inside a blocked subprocess pipe read), wedging the whole process.
        # Normal interpreter finalization would still delete the wrappers, so
        # exit hard here - after flushing logs - to guarantee a clean exit
        # code instead of a crash-on-quit. This path never runs in tests (they
        # don't call main) and only when a background operation truly could
        # not be stopped - which should now be rare, since every long-running
        # external-tool call routes its cancellation through core.proc, which
        # kills the process tree rather than relying on the thread noticing.
        _LOG.error("%d worker thread(s) could not be stopped; exiting hard to "
                   "avoid a teardown crash", len(stuck))
        logging.shutdown()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
