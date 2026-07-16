"""Script to run the Cortex Cleaner CLI."""

import sys
import os

# Add the current directory to the path so it can find src
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Main entry point."""
    try:
        from cortex_unified.cli.cli import main as cli_main
        cli_main()
    except Exception as e:
        print(f"Error running CLI: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
