"""
Visualization module for Cortex Cleaner.

This module provides interactive visualization capabilities including:
- TreeMap visualizations for disk usage
- Sunburst charts for hierarchical data
- Interactive dashboards for data exploration
"""

from .treemap_generator import TreeMapGenerator, TreeMapNode
from .sunburst_generator import SunburstGenerator, SunburstSegment
from .interactive_dashboard import InteractiveDashboard

__version__ = "1.0.0"
__all__ = [
    "TreeMapGenerator",
    "TreeMapNode",
    "SunburstGenerator", 
    "SunburstSegment",
    "InteractiveDashboard"
]