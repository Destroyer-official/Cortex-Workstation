"""GUI entry point for Deep Cleaner."""

# Handle both direct execution and module import
try:
    # When running as a module
    from .gui.main_window import main
except ImportError:
    # When running directly
    import sys
    import os
    # Add the parent directory to the path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from deep_cleaner.gui.main_window import main

if __name__ == "__main__":
    main()