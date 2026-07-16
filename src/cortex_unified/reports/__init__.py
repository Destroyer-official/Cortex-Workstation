"""
Reports and restore module for Cortex Cleaner.

Provides reporting and backup/restore capabilities:
- ReportsGenerator: Multi-format report generation (text, HTML, JSON, CSV)
- RestoreManager: Backup creation and file restoration from manifests
"""

from .reports import ReportsGenerator
from .restore_manager import RestoreManager

__all__ = [
    "ReportsGenerator",
    "RestoreManager",
]
