"""Launch the Cortex Workstation GUI from a source checkout.

Defaults to the modern premium interface (engine-backed, storage-aware). The
legacy multi-tab GUI is still available via
``python -m cortex_unified.ui.launcher`` or the ``cortex-workstation-gui`` console
script.

This is the outermost application boundary, so it converts a startup failure
into an exit code - but it logs the full traceback first (via the GUI's own
logging setup when available, and always to stderr) so a crash on launch stays
diagnosable instead of collapsing into a single printed line.
"""

from __future__ import annotations

import os
import sys
import traceback

# Support running this file directly from a source checkout (no install).
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if os.path.isdir(_SRC) and _SRC not in sys.path:
    sys.path.insert(0, _SRC)


class _SafeStream:
    """Safe stream fallback for Windows GUI executables where stdout/stderr are None."""

    def write(self, text: str) -> int:
        return len(text)

    def flush(self) -> None:
        pass


if sys.stdout is None:
    sys.stdout = _SafeStream()
if sys.stderr is None:
    sys.stderr = _SafeStream()


def _show_crash_dialog(title: str, message: str) -> None:
    """Show a native Windows error dialog if running in GUI mode."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
    except Exception:
        pass


def main() -> int:
    """Entry point: run the premium GUI."""
    try:
        from cortex_unified.ui.premium.app import main as gui_main
    except ImportError as exc:
        msg = (
            f"Could not load the Cortex Workstation GUI: {exc}\n\n"
            "Please ensure all required dependencies are installed.\n"
            "If using source code: pip install -r requirements.txt\n"
        )
        if sys.stderr is not None:
            sys.stderr.write(msg)
        _show_crash_dialog("Cortex Workstation - Startup Error", msg)
        return 1

    try:
        return gui_main() or 0
    except Exception as exc:  # noqa: BLE001 - outermost boundary; logged then converted
        # Log through the app's configured handlers if logging is already set up.
        try:
            import logging
            logging.getLogger("cortex").critical("GUI failed to start", exc_info=True)
        except Exception:
            pass

        tb_str = traceback.format_exc()
        try:
            log_dir = os.path.join(os.path.expanduser("~"), ".cortex_workstation", "logs")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "startup_crash.log"), "a", encoding="utf-8") as f:
                f.write(f"\n--- Crash at startup ---\n{tb_str}\n")
        except Exception:
            pass

        if sys.stderr is not None:
            traceback.print_exc()
        _show_crash_dialog("Cortex Workstation - Application Crash", f"An unexpected error occurred during startup:\n\n{exc}\n\nDetailed traceback logged to ~/.cortex_workstation/logs/startup_crash.log")
        return 1


if __name__ == "__main__":
    sys.exit(main())
