"""Launch the Cortex Cleaner GUI.

Defaults to the modern premium interface (engine-backed, storage-aware). The
legacy multi-tab GUI is still available via ``python -m cortex_unified.ui.launcher``
or the ``cortex-cleaner-gui`` console script.
"""

import os
import sys

# Support running this file directly from a source checkout (no install).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def main() -> int:
    """Entry point: run the premium GUI."""
    try:
        from cortex_unified.ui.premium.app import main as gui_main
        return gui_main() or 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error running GUI: {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
