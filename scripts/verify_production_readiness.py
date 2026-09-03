"""Comprehensive Production Readiness & Diagnostics Verification Suite.

Runs deep structural, runtime, and functional diagnostics across:
1. Unified Vector SVG Icons & multi-DPI renderers (1,002 icons)
2. All 55 System Maintenance Tools
3. All 23 Advanced File & Data Analyzers & Dedup Engines
4. Core Engine, FastWalk, Cloud Detection & Path Safety Guards
5. Algorithmic Performance Caching Engines (SIEVE, S3-FIFO, FastCDC Chunker)
6. Nexus File Manager Native Subsystem & 3-Tier Fluent Windows 11 Header
7. All 119 Registered UI Pages in Shell (lazy loading, widget trees, signals)
"""

import os
import sys
from pathlib import Path

# Ensure repo root and src are on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cortex_unified.debug.runner import main

if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
