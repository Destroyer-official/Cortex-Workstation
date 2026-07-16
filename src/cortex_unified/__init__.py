"""
Cortex Cleaner - A comprehensive utility to find and remove unnecessary files and folders.

Cortex Cleaner is a powerful, cross-platform application designed to help users
clean up their systems by identifying and removing various types of unnecessary
files including empty files, temporary files, duplicates, large files, and more.

Features:
- Empty files and directories detection
- Duplicate file finding with multiple algorithms
- Temporary file cleanup
- Large file identification
- Disk usage analysis with visualizations
- System tools integration
- Docker resource cleanup
- Package manager cache cleaning
- Broken link detection and repair
- File shredding with military-grade security
- Task scheduling and automation
- Comprehensive reporting
- Multi-language support
- Accessibility features

Author: Cortex Cleaner Team
License: MIT
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Cortex Cleaner Team"
__email__ = "team@deepcleaner.com"
__license__ = "MIT"
__description__ = "A comprehensive utility to find and remove unnecessary files and folders"

# Import main classes for easy access
from .core.scanner import Scanner
from .core.deleter import Deleter
from .core.config import Config

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