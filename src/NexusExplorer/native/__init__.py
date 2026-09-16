"""NexusExplorer native Qt package."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the native directory is in sys.path so both direct imports
# (e.g. 'import nexus_transfer_monitor') and package-qualified imports work.
_here = str(Path(__file__).resolve().parent)
if _here not in sys.path:
    sys.path.insert(0, _here)
