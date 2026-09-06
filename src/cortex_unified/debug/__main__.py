"""CLI entry point for python -m cortex_unified.debug."""

from __future__ import annotations

import os
import sys

from cortex_unified.debug.runner import main

if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
