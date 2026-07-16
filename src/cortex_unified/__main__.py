#!/usr/bin/env python3
"""
Cortex Cleaner CLI Entry Point

This module provides the command-line interface entry point for Cortex Cleaner.
"""

import sys
import os

# Add the project root to the path to ensure imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    """Main entry point for the CLI."""
    try:
        from cortex_unified.cli.cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"Error importing CLI module: {e}")
        print("Please ensure Cortex Cleaner is properly installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running Cortex Cleaner: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()