"""Analyzers module for Cortex Cleaner."""

from .cache_cleaner import CacheCleaner
from .disk_analyzer import DiskAnalyzer
from .docker_cleaner import DockerCleaner
from .duplicate_finder import DuplicateFinder
from .duplicate_folder_finder import DuplicateFolderFinder
from .file_shredder import FileShredder
from .large_file_finder import LargeFileFinder
from .old_file_cleaner import OldFileCleaner
from .package_manager_cleaner import PackageManagerCleaner, Package, PackageManager, CleanupResult, HealthStatus
from .deep_cleaner import DeepCleaner
from .broken_link_detector import BrokenLinkDetector, BrokenLink, BrokenSymlink, BrokenShortcut, BrokenRegistryRef, RepairResult
from .perceptual_duplicate_finder import PerceptualDuplicateFinder
from .fuzzy_finder import FuzzyDuplicateFinder
from .audio_duplicate_finder import AudioDuplicateFinder
from .video_duplicate_finder import VideoDuplicateFinder
from .content_defined_chunker import ContentDefinedChunker
from .advanced_disk_analyzer import AdvancedDiskAnalyzer
from .cloud_storage_analyzer import CloudStorageAnalyzer
from .czkawka_tools import (
    EmptyFinder, InvalidSymlinkFinder, BrokenFileFinder,
    BadExtensionFinder, BadNamesFinder, ExifCleaner, TempFileFinder, VideoOptimizer,
)
from .portable_manager import PortableManager

# Windows-only modules — catch only ImportError (winreg missing on non-Windows)
try:
    from .registry_cleaner_ai import AIRegistryCleaner
except ImportError:
    AIRegistryCleaner = None  # type: ignore

try:
    from .advanced_uninstaller import AdvancedUninstaller
except ImportError:
    AdvancedUninstaller = None  # type: ignore

try:
    from cortex_unified.system_tools.startup_optimizer import StartupOptimizer
except ImportError:
    StartupOptimizer = None  # type: ignore

try:
    from cortex_unified.system_tools.privacy_blocker import PrivacyBlocker
except ImportError:
    PrivacyBlocker = None  # type: ignore

try:
    from cortex_unified.system_tools.windows_update_repair import WindowsUpdateRepair
except ImportError:
    WindowsUpdateRepair = None  # type: ignore

try:
    from cortex_unified.system_tools.component_store_cleaner import ComponentStoreCleaner
except ImportError:
    ComponentStoreCleaner = None  # type: ignore

__all__ = [
    'BrokenLinkDetector',
    'BrokenLink',
    'BrokenSymlink',
    'BrokenShortcut',
    'BrokenRegistryRef',
    'CacheCleaner',
    'DiskAnalyzer',
    'AdvancedDiskAnalyzer',
    'CloudStorageAnalyzer',
    'DockerCleaner',
    'DuplicateFinder',
    'DuplicateFolderFinder',
    'FileShredder',
    'LargeFileFinder',
    'OldFileCleaner',
    'PackageManagerCleaner',
    'Package',
    'PackageManager',
    'CleanupResult',
    'HealthStatus',
    'RepairResult',
    'DeepCleaner',
    'PerceptualDuplicateFinder',
    'FuzzyDuplicateFinder',
    'AudioDuplicateFinder',
    'VideoDuplicateFinder',
    'ContentDefinedChunker',
    'EmptyFinder',
    'InvalidSymlinkFinder',
    'BrokenFileFinder',
    'BadExtensionFinder',
    'BadNamesFinder',
    'ExifCleaner',
    'TempFileFinder',
    'VideoOptimizer',
    'PortableManager',
    'AIRegistryCleaner',
    'AdvancedUninstaller',
]