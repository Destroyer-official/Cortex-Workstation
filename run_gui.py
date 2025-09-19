"""Script to run the Deep Cleaner GUI."""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main entry point."""
    try:
        # Import and run the GUI
        from deep_cleaner.gui.main_window import main as gui_main
        gui_main()
    except Exception as e:
        print(f"Error running GUI: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())