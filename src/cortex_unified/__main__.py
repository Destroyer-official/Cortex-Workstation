#!/usr/bin/env python3
"""``python -m cortex_unified`` entry point.

Delegates to the legacy Click CLI (:mod:`cortex_unified.cli.cli`), which is the
same command installed as ``cortex-cleaner``. This is kept for backwards
compatibility; the modern, dry-run-first CLI is ``cortex``
(:mod:`cortex_unified.engine.cli`).

Error handling policy
---------------------
This is an application boundary, so it is the right place to convert an
exception into an exit code - but it must not *hide* the failure. A missing
dependency reports the actionable hint and exits 1; anything unexpected keeps
its traceback so the bug is diagnosable, rather than being reduced to a
one-line message. The previous version swallowed every exception (including
``KeyboardInterrupt``-adjacent flows) and discarded the CLI's own exit code.
"""

from __future__ import annotations

import sys


def main() -> int:
    """Run the legacy CLI and return its process exit code."""
    try:
        from cortex_unified.cli.cli import main as cli_main
    except ImportError as exc:
        sys.stderr.write(
            f"Could not load the Cortex Cleaner CLI: {exc}\n"
            "Ensure the package and its dependencies are installed:\n"
            "    pip install -e .\n"
        )
        return 1

    # Click commands normally raise SystemExit; honour whatever they return or
    # raise instead of assuming success.
    try:
        result = cli_main()
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    return 0 if result is None else int(result)


if __name__ == "__main__":
    sys.exit(main())
