"""GUI entry point for Cortex Cleaner."""

# Handle both direct execution and module import
try:
    # When running as a module
    from cortex_unified.ui.main_window import main
except ImportError:
    # When running directly
    import sys
    import os
    # Add the parent directory to the path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from cortex_unified.ui.main_window import main

if __name__ == "__main__":
    main()