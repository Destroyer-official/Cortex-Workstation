"""Analyzers module for Deep Cleaner."""

from .cache_cleaner import CacheCleaner
from .disk_analyzer import DiskAnalyzer
from .docker_cleaner import DockerCleaner
from .duplicate_finder import DuplicateFinder
from .duplicate_folder_finder import DuplicateFolderFinder
from .file_shredder import FileShredder
from .large_file_finder import LargeFileFinder
from .old_file_cleaner import OldFileCleaner
from .package_manager_cleaner import PackageManagerCleaner, Package, PackageManager, CleanupResult, HealthStatus
from .temp_cleaner import TempCleaner
from .broken_link_detector import BrokenLinkDetector, BrokenLink, BrokenSymlink, BrokenShortcut, BrokenRegistryRef, RepairResult

__all__ = [
    'BrokenLinkDetector',
    'BrokenLink',
    'BrokenSymlink', 
    'BrokenShortcut',
    'BrokenRegistryRef',
    'CacheCleaner',
    'DiskAnalyzer', 
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
    'TempCleaner'
]