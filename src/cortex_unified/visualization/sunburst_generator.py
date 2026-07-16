"""
Sunburst chart generator for hierarchical disk usage visualization.
"""

import os
import math
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.offline import plot
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    # Create dummy classes for when plotly is not available
    class go:
        class Figure:
            def __init__(self, *args, **kwargs):
                pass
            def add_trace(self, *args, **kwargs):
                pass
            def update_layout(self, *args, **kwargs):
                pass
    class px:
        @staticmethod
        def sunburst(*args, **kwargs):
            return go.Figure()
    def plot(*args, **kwargs):
        pass
import colorsys

@dataclass
class SunburstSegment:
    """Data structure for Sunburst chart segments."""
    name: str
    size: int
    path: str
    parent: str
    angle_start: float
    angle_end: float
    radius_inner: float
    radius_outer: float
    color: Optional[str] = None
    file_type: Optional[str] = None

class SunburstGenerator:
    """Generates Sunburst chart visualizations for hierarchical data."""
    
    def __init__(self, data: Any = None):
        """Initialize Sunburst generator with disk analysis data."""
        self.data = data
        self.segments = []
        self._setup_color_scheme()
    
    def _setup_color_scheme(self):
        """Setup color scheme for different file types and directory levels."""
        # Color palette for different levels
        self.level_colors = [
            '#3498db',  # Level 0 - Blue
            '#2ecc71',  # Level 1 - Green  
            '#f1c40f',  # Level 2 - Yellow
            '#e74c3c',  # Level 3 - Red
            '#9b59b6',  # Level 4 - Purple
            '#34495e',  # Level 5 - Dark gray
            '#e67e22',  # Level 6 - Orange
            '#1abc9c',  # Level 7 - Turquoise
        ]
        
        # File type specific colors
        self.file_type_colors = {
            '.txt': '#3498db',    # Blue
            '.py': '#2ecc71',     # Green
            '.js': '#f1c40f',     # Yellow
            '.html': '#e74c3c',   # Red
            '.css': '#9b59b6',    # Purple
            '.json': '#34495e',   # Dark gray
            '.xml': '#e67e22',    # Orange
            '.log': '#95a5a6',    # Light gray
            '.md': '#1abc9c',     # Turquoise
            '.jpg': '#ff6b6b',    # Light red
            '.png': '#4ecdc4',    # Light blue
            '.pdf': '#d63031',    # Dark red
            '.zip': '#fdcb6e',    # Light orange
            'directory': '#74b9ff', # Light blue
            'unknown': '#ddd'     # Light gray
        }
    
    def _get_file_type_from_path(self, path: str) -> str:
        """Get file type from path."""
        if os.path.isdir(path):
            return 'directory'
        ext = os.path.splitext(path)[1].lower()
        return ext if ext else 'unknown'
    
    def _get_color_for_level_and_type(self, level: int, file_type: str, size_ratio: float = 0.5) -> str:
        """Get color based on level, file type, and size."""
        # Use file type color if available, otherwise use level color
        if file_type in self.file_type_colors:
            base_color = self.file_type_colors[file_type]
        else:
            base_color = self.level_colors[level % len(self.level_colors)]
        
        # Adjust brightness based on size
        base_color = base_color.lstrip('#')
        r, g, b = tuple(int(base_color[i:i+2], 16) for i in (0, 2, 4))
        
        # Convert to HSV and adjust brightness
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        v = max(0.3, v * (0.4 + 0.6 * size_ratio))  # Ensure minimum brightness
        
        # Convert back to RGB and hex
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    
    def _convert_directory_tree_to_sunburst_data(self, tree_data: Dict, max_depth: int = 4) -> Dict[str, List]:
        """Convert directory tree data to Plotly sunburst format."""
        ids = []
        labels = []
        parents = []
        values = []
        colors = []
        hover_texts = []
        
        # Calculate total size for percentage calculations
        total_size = 0
        if isinstance(tree_data, dict):
            if 'size_bytes' in tree_data:
                total_size = tree_data['size_bytes']
            elif 'children' in tree_data:
                total_size = sum(child.get('size_bytes', 0) for child in tree_data['children'])
        
        def add_node(node_data: Dict, parent_id: str = "", level: int = 0):
            if level >= max_depth:
                return
            
            node_name = node_data.get('name', 'Unknown')
            node_size = node_data.get('size_bytes', 0)
            node_path = node_data.get('path', '')
            
            # Create unique ID
            node_id = f"{parent_id}/{node_name}" if parent_id else node_name
            
            # Calculate size ratio for color scaling
            size_ratio = node_size / total_size if total_size > 0 else 0
            
            # Get file type and color
            file_type = self._get_file_type_from_path(node_path)
            color = self._get_color_for_level_and_type(level, file_type, size_ratio)
            
            # Add to lists
            ids.append(node_id)
            labels.append(node_name)
            parents.append(parent_id)
            values.append(node_size)
            colors.append(color)
            
            # Create hover text
            percentage = (node_size / total_size * 100) if total_size > 0 else 0
            hover_text = (f"{node_name}<br>"
                         f"Size: {self._format_bytes(node_size)}<br>"
                         f"Percentage: {percentage:.1f}%<br>"
                         f"Path: {node_path}")
            hover_texts.append(hover_text)
            
            # Process children
            children = node_data.get('children', [])
            for child in children:
                if isinstance(child, dict):
                    add_node(child, node_id, level + 1)
        
        # Process the tree data
        if isinstance(tree_data, dict):
            if 'children' in tree_data:
                # Single tree with children
                add_node(tree_data)
            else:
                # Dictionary of trees
                for key, subtree in tree_data.items():
                    if isinstance(subtree, dict):
                        add_node(subtree)
        elif isinstance(tree_data, list):
            # List of trees
            for subtree in tree_data:
                if isinstance(subtree, dict):
                    add_node(subtree)
        
        return {
            'ids': ids,
            'labels': labels,
            'parents': parents,
            'values': values,
            'colors': colors,
            'hover_texts': hover_texts
        }
    
    def generate_sunburst(self, max_depth: int = 4) -> go.Figure:
        """Generate Sunburst chart visualization data."""
        if not self.data:
            # Create empty sunburst
            fig = go.Figure(go.Sunburst(
                labels=["No Data"],
                parents=[""],
                values=[1],
            ))
            fig.update_layout(title="No Data Available")
            return fig
        
        # Convert data to sunburst format
        if hasattr(self.data, 'directory_tree') and self.data.directory_tree:
            sunburst_data = self._convert_directory_tree_to_sunburst_data(
                self.data.directory_tree, max_depth
            )
        elif isinstance(self.data, dict):
            sunburst_data = self._convert_directory_tree_to_sunburst_data(
                self.data, max_depth
            )
        else:
            # Create empty sunburst for unsupported data
            fig = go.Figure(go.Sunburst(
                labels=["No Data"],
                parents=[""],
                values=[1],
            ))
            fig.update_layout(title="No Data Available")
            return fig
        
        if not sunburst_data['ids']:
            # Create empty sunburst
            fig = go.Figure(go.Sunburst(
                labels=["No Data"],
                parents=[""],
                values=[1],
            ))
            fig.update_layout(title="No Data Available")
            return fig
        
        # Create sunburst chart
        fig = go.Figure(go.Sunburst(
            ids=sunburst_data['ids'],
            labels=sunburst_data['labels'],
            parents=sunburst_data['parents'],
            values=sunburst_data['values'],
            branchvalues="total",
            hovertext=sunburst_data['hover_texts'],
            hovertemplate='%{hovertext}<extra></extra>',
            marker=dict(
                colors=sunburst_data['colors'],
                line=dict(color="white", width=2)
            ),
            maxdepth=max_depth,
        ))
        
        # Update layout
        fig.update_layout(
            title={
                'text': "Disk Usage Sunburst Chart",
                'x': 0.5,
                'xanchor': 'center'
            },
            font=dict(size=12),
            margin=dict(t=50, l=25, r=25, b=25),
            height=600,
            width=600
        )
        
        return fig
    
    def export_as_image(self, format: str = "svg", width: int = 800, height: int = 800) -> bytes:
        """Export Sunburst chart as image."""
        try:
            fig = self.generate_sunburst()
            
            # Export as image
            img_bytes = fig.to_image(
                format=format.lower(),
                width=width,
                height=height,
                engine="kaleido"
            )
            
            return img_bytes
        except Exception as e:
            raise RuntimeError(f"Failed to export sunburst as {format}: {str(e)}")
    
    def export_as_html(self, interactive: bool = True, include_plotlyjs: str = 'cdn') -> str:
        """Export Sunburst chart as HTML."""
        try:
            fig = self.generate_sunburst()
            
            # Configure interactivity
            config = {
                'displayModeBar': interactive,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'] if not interactive else []
            }
            
            # Generate HTML
            html_str = plot(
                fig,
                output_type='div',
                include_plotlyjs=include_plotlyjs,
                config=config
            )
            
            return html_str
        except Exception as e:
            raise RuntimeError(f"Failed to export sunburst as HTML: {str(e)}")
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        if bytes_count == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"