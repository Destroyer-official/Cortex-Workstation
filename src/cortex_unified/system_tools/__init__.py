"""
System tools module for Cortex Cleaner.

Provides system-level utilities including:
- Process analysis and monitoring
- Windows registry cleanup
- Startup program management
"""

from .process_analyzer import ProcessAnalyzer
from .startup_manager import StartupManager
from .compact_os import CompactOSManager
from .s3_fifo import S3FIFO

# Windows-only modules — catch only ImportError
try:
    from .component_store_cleaner import ComponentStoreCleaner
except ImportError:
    ComponentStoreCleaner = None  # type: ignore

try:
    from .windows_update_repair import WindowsUpdateRepair
except ImportError:
    WindowsUpdateRepair = None  # type: ignore

try:
    from .driver_manager import DriverManager
except ImportError:
    DriverManager = None  # type: ignore

try:
    from .privacy_blocker import PrivacyBlocker
except ImportError:
    PrivacyBlocker = None  # type: ignore

try:
    from .secure_shredder import SecureShredder
except ImportError:
    SecureShredder = None  # type: ignore

try:
    from .startup_optimizer import StartupOptimizer
except ImportError:
    StartupOptimizer = None  # type: ignore

try:
    from .browser_cleaner import DeepBrowserCleaner
except ImportError:
    DeepBrowserCleaner = None  # type: ignore

# RegistryCleaner is Windows-only; import conditionally
try:
    from .registry_cleaner import RegistryCleaner
    _HAS_REGISTRY = True
except ImportError:
    _HAS_REGISTRY = False

__all__ = [
    "ProcessAnalyzer",
    "StartupManager",
    "CompactOSManager",
    "S3FIFO",
    "ComponentStoreCleaner",
    "WindowsUpdateRepair",
    "DriverManager",
    "PrivacyBlocker",
    "SecureShredder",
    "StartupOptimizer",
    "DeepBrowserCleaner",
]

if _HAS_REGISTRY:
    __all__.append("RegistryCleaner")
