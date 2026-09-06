"""GUI entry point for Cortex Workstation."""

from __future__ import annotations

import sys


def main() -> int:
    """Launch Cortex Workstation GUI.

    Defaults to the modern premium workstation UI with all 139 tools.
    If '--legacy' is provided in arguments, the legacy tabbed interface is used.
    """
    if "--legacy" in sys.argv:
        sys.argv.remove("--legacy")
        from cortex_unified.ui.main_window import main as legacy_main

        return legacy_main()

    from cortex_unified.ui.premium.app import main as premium_main

    return premium_main()


if __name__ == "__main__":
    sys.exit(main())