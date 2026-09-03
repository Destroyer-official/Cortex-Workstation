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


def main() -> int:
    """Entry point: run the premium GUI."""
    try:
        from cortex_unified.ui.premium.app import main as gui_main
    except ImportError as exc:
        sys.stderr.write(
            f"Could not load the Cortex Workstation GUI: {exc}\n"
            "The GUI requires PySide6. Install it with:\n"
            "    pip install PySide6\n"
        )
        return 1

    try:
        return gui_main() or 0
    except Exception:  # noqa: BLE001 - outermost boundary; logged then converted
        # Log through the app's configured handlers if logging is already set
        # up, so the failure lands in the rotating log file as well as stderr.
        try:
            import logging

            logging.getLogger("cortex").critical(
                "GUI failed to start", exc_info=True)
        except Exception:  # noqa: BLE001 - never mask the original failure
            pass
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
