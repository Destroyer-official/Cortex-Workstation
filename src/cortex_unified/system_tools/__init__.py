"""
System tools module for Cortex Cleaner.

Provides system-level utilities including:
- Process analysis and monitoring
- Windows registry cleanup
- Startup program management
"""

from .process_analyzer import ProcessAnalyzer
from .startup_manager import StartupManager

# RegistryCleaner is Windows-only; import conditionally
try:
    from .registry_cleaner import RegistryCleaner
    _HAS_REGISTRY = True
except (ImportError, RuntimeError):
    _HAS_REGISTRY = False

__all__ = [
    "ProcessAnalyzer",
    "StartupManager",
]

if _HAS_REGISTRY:
    __all__.append("RegistryCleaner")
