"""Cortex Cleaner - safe, fast cleanup and system-care toolkit.

Import cost policy
------------------
This package is the import root for *every* entry point: the ``cortex`` CLI,
the ``cortex-gui`` desktop app, the legacy commands, and the test suite. It
therefore imports **nothing expensive at module scope**.

The legacy convenience exports (:class:`Scanner`, :class:`Deleter`,
:class:`Config`) are resolved lazily through :pep:`562` module ``__getattr__``.
They stay importable exactly as before, unchanged::

    from cortex_unified import Scanner        # still works
    import cortex_unified; cortex_unified.Config()

but the underlying modules - and their heavy third-party dependencies
(``send2trash`` -> ``pywin32``/``pythoncom``, ``psutil``, ``pyyaml``) - load
only when one of those names is actually touched. Printing ``cortex --help``
no longer pays for the Windows COM recycle-bin stack.

New code should prefer the modern engine (:mod:`cortex_unified.engine`), which
supersedes the legacy scanner/deleter/config trio.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "1.0.0"
__author__ = "Cortex Cleaner Team"
__email__ = "team@deepcleaner.com"
__license__ = "MIT"
__description__ = (
    "A comprehensive utility to find and remove unnecessary files and folders"
)

# Public name -> submodule that defines it. Kept as data so ``__getattr__``,
# ``__dir__`` and the test suite all agree on one source of truth.
_LAZY_EXPORTS: dict[str, str] = {
    "Scanner": ".core.scanner",
    "Deleter": ".core.deleter",
    "Config": ".core.config",
}

if TYPE_CHECKING:  # pragma: no cover - type-checker only, never executed
    from .core.config import Config
    from .core.deleter import Deleter
    from .core.scanner import Scanner

__all__ = [
    "Scanner",
    "Deleter",
    "Config",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
]


def __getattr__(name: str) -> Any:
    """Resolve the legacy convenience exports on first use (:pep:`562`).

    Raises :class:`AttributeError` for unknown names so ``hasattr`` and normal
    attribute probing keep working. An :class:`ImportError` from a genuinely
    broken/missing optional dependency is allowed to propagate unchanged - it
    would be actively harmful to mask a real installation problem here.
    """
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    value = getattr(import_module(module_path, __name__), name)
    # Cache on the module so subsequent lookups skip __getattr__ entirely.
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
    """__dir__."""
