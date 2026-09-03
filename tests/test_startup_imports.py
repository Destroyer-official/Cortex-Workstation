"""Startup-cost and public-API contracts for the package import root.

Every entry point (``cortex``, ``cortex-gui``, the legacy commands and this
test suite) imports :mod:`cortex_unified` first. These tests pin two properties
so the import cost cannot silently regress:

1. Importing the package - or the modern engine - must NOT drag in heavy
   third-party dependencies that only specific features need.
2. The historical lazy exports and flags must still resolve, so the refactor
   stays backwards compatible.

Each check runs in a fresh subprocess, because import side effects are global
and process-wide: an already-imported module would make the assertions
meaningless inside the shared pytest process.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Dependencies that must never be pulled in by a bare package/engine import.
# ``send2trash`` is the expensive one: it loads the Windows COM shell stack
# (pywin32 -> pythoncom -> win32com.shell).
_HEAVY = ("send2trash", "psutil", "yaml")

_SRC = str(Path(__file__).resolve().parent.parent / "src")


def _run(code: str) -> str:
    """Execute *code* in a clean interpreter and return its stdout."""
    env = os.environ.copy()
    env["PYTHONPATH"] = _SRC + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert result.returncode == 0, (
        f"subprocess failed ({result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return result.stdout.strip()


def test_package_import_does_not_load_heavy_dependencies():
    """``import cortex_unified`` must stay cheap for every entry point."""
    loaded = _run(
        "import sys, cortex_unified\n"
        f"print(','.join(m for m in {_HEAVY!r} if m in sys.modules))"
    )
    assert loaded == "", (
        f"importing cortex_unified eagerly loaded: {loaded}. Keep the package "
        "root free of expensive imports (see cortex_unified/__init__.py)."
    )


def test_engine_import_does_not_load_recycle_bin_stack():
    """A read-only engine import must not load the recycle-bin COM stack."""
    loaded = _run(
        "import sys, cortex_unified.engine.service\n"
        "print('send2trash' if 'send2trash' in sys.modules else '')"
    )
    assert loaded == "", (
        "importing the engine loaded send2trash; recycling must resolve it "
        "lazily (see engine/secure_delete.py::_resolve_send2trash)."
    )


def test_engine_public_api_still_imports():
    """The lazy-import work must not break the engine's public surface."""
    out = _run(
        "from cortex_unified.engine import CleanerService, SecureDeleter\n"
        "print(CleanerService.__name__, SecureDeleter.__name__)"
    )
    assert out == "CleanerService SecureDeleter"


def test_legacy_convenience_exports_still_resolve():
    """``from cortex_unified import Scanner`` must keep working (PEP 562)."""
    out = _run(
        "from cortex_unified import Config, Deleter, Scanner\n"
        "print(Scanner.__name__, Deleter.__name__, Config.__name__)"
    )
    assert out == "Scanner Deleter Config"


def test_version_is_importable_without_side_effects():
    """``__version__`` is read by the CLI and logging setup at import time."""
    out = _run(
        "import sys, cortex_unified\n"
        "print(cortex_unified.__version__, 'send2trash' in sys.modules)"
    )
    version, heavy = out.split()
    assert version and heavy == "False"


def test_unknown_attribute_still_raises_attribute_error():
    """Lazy resolution must not turn typos into ImportError or hangs."""
    out = _run(
        "import cortex_unified\n"
        "try:\n"
        "    cortex_unified.NoSuchThing\n"
        "except AttributeError:\n"
        "    print('AttributeError')\n"
    )
    assert out == "AttributeError"


def test_has_trash_flag_contract_preserved():
    """``_HAS_TRASH`` is imported directly by tests; keep it resolvable."""
    out = _run(
        "from cortex_unified.engine.secure_delete import _HAS_TRASH\n"
        "print(isinstance(_HAS_TRASH, bool))"
    )
    assert out == "True"


# --- legacy CLI (``cortex-cleaner``) import cost -------------------------
#
# Click builds its whole command tree at import time, so a module-scope import
# in cli/cli.py is paid by every invocation - including ``--help``. Importing
# the analyzers eagerly loaded 718 modules (~1.1 s), including the Docker SDK.

#: Dependencies no command needs merely to print help.
_CLI_FORBIDDEN = ("docker", "send2trash", "psutil")


def test_legacy_cli_import_does_not_load_optional_heavy_sdks():
    """Building the command tree must not import per-command dependencies."""
    loaded = _run(
        "import sys, cortex_unified.cli.cli\n"
        f"print(','.join(m for m in {_CLI_FORBIDDEN!r} if m in sys.modules))"
    )
    assert loaded == "", (
        f"importing the legacy CLI eagerly loaded: {loaded}. Import "
        "per-command dependencies inside the command that uses them."
    )


def test_legacy_cli_still_exposes_every_command():
    """Deferring imports must not drop or rename any command."""
    out = _run(
        "from cortex_unified.cli.cli import main\n"
        "print(len(main.commands), ','.join(sorted(main.commands)))"
    )
    count, names = out.split(" ", 1)
    # 16 commands since clean-temp was re-enabled (TempCleaner now exists).
    assert int(count) == 16, f"expected 16 commands, got {count}: {names}"
    # Spot-check the commands whose dependencies are now deferred.
    for expected in ("docker-cleanup", "secure-delete", "generate-report",
                     "restore", "scan-broken-links", "analyze-disk",
                     "clean-temp"):
        assert expected in names


def test_legacy_cli_registry_flag_contract_preserved():
    """``HAS_REGISTRY_CLEANER`` was a module constant; keep it readable."""
    out = _run(
        "import cortex_unified.cli.cli as c\n"
        "print(isinstance(c.HAS_REGISTRY_CLEANER, bool))"
    )
    assert out == "True"


def test_legacy_cli_unknown_attribute_raises_attribute_error():
    """The module ``__getattr__`` must not mask typos."""
    out = _run(
        "import cortex_unified.cli.cli as c\n"
        "try:\n"
        "    c.NoSuchFlag\n"
        "except AttributeError:\n"
        "    print('AttributeError')\n"
    )
    assert out == "AttributeError"
