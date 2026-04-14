"""
TreeMap visualization generator for disk usage analysis.
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
        def treemap(*args, **kwargs):
            return go.Figure()
    def plot(*args, **kwargs):
        pass

import colorsys


@dataclass
class TreeMapNode:
    """Data structure for TreeMap visualization nodes."""
    name: str
    size: int
    path: str
    children: List['TreeMapNode']
    color: str
    depth: int
    file_type: Optional[str] = None
    modified_time: Optional[float] = None


class TreeMapGenerator:
    """Generates TreeMap visualizations for disk usage data."""
    
    def __init__(self, data: Any = None):
        """Initialize TreeMap generator with disk analysis data."""
        self.data = data
        self.color_map = {}
        self.has_plotly = HAS_PLOTLY
        if not self.has_plotly:
            import warnings
            warnings.warn("Plotly not available. Visualization features will be limited.")
        self._setup_color_scheme()
    
    def _setup_color_scheme(self):
        """Setup color scheme for different file types and sizes."""
        # File type colors
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
    
    def _get_color_for_item(self, node: TreeMapNode) -> str:
        """Get color for a tree map item based on type and size."""
        file_type = node.file_type or self._get_file_type_from_path(node.path)
        
        # Base color from file type
        base_color = self.file_type_colors.get(file_type, self.file_type_colors['unknown'])
        
        # Adjust brightness based on size (larger = darker)
        if hasattr(self, '_max_size') and self._max_size > 0:
            size_ratio = node.size / self._max_size
            # Convert hex to RGB
            base_color = base_color.lstrip('#')
            r, g, b = tuple(int(base_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Convert to HSV and adjust brightness
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            v = max(0.3, v * (0.5 + 0.5 * size_ratio))  # Ensure minimum brightness
            
            # Convert back to RGB and hex
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        return base_color
    
    def _convert_directory_tree_to_nodes(self, tree_data: Dict, max_depth: int = 3, current_depth: int = 0) -> List[TreeMapNode]:
        """Convert directory tree data to TreeMapNode objects."""
        nodes = []
        
        if current_depth >= max_depth:
            return nodes
        
        # Handle both single tree and list of trees
        if isinstance(tree_data, dict):
            if 'children' in tree_data:
                # Single tree structure
                trees = [tree_data]
            else:
                # Dictionary of trees
                trees = list(tree_data.values()) if tree_data else []
        elif isinstance(tree_data, list):
            trees = tree_data
        else:
            return nodes
        
        for tree in trees:
            if not isinstance(tree, dict):
                continue
                
            node = TreeMapNode(
                name=tree.get('name', 'Unknown'),
                size=tree.get('size_bytes', 0),
                path=tree.get('path', ''),
                children=[],
                color='',
                depth=current_depth,
                file_type=self._get_file_type_from_path(tree.get('path', ''))
            )
            
            # Recursively process children
            children_data = tree.get('children', [])
            if children_data and current_depth < max_depth - 1:
                node.children = self._convert_directory_tree_to_nodes(
                    children_data, max_depth, current_depth + 1
                )
            
            nodes.append(node)
        
        return nodes
    
    def _flatten_nodes_for_plotly(self, nodes: List[TreeMapNode]) -> Dict[str, List]:
        """Flatten tree nodes for Plotly treemap format."""
        ids = []
        labels = []
        parents = []
        values = []
        colors = []
        hover_texts = []
        
        def add_node(node: TreeMapNode, parent_id: str = ""):
            node_id = f"{parent_id}/{node.name}" if parent_id else node.name
            
            ids.append(node_id)
            labels.append(node.name)
            parents.append(parent_id)
            values.append(node.size)
            colors.append(self._get_color_for_item(node))
            
            # Create hover text with size information
            size_mb = node.size / (1024 * 1024) if node.size > 0 else 0
            hover_text = f"{node.name}<br>Size: {self._format_bytes(node.size)}<br>Path: {node.path}"
            hover_texts.append(hover_text)
            
            # Add children
            for child in node.children:
                add_node(child, node_id)
        
        # Calculate max size for color scaling
        all_sizes = []
        def collect_sizes(nodes_list):
            for node in nodes_list:
                all_sizes.append(node.size)
                collect_sizes(node.children)
        
        collect_sizes(nodes)
        self._max_size = max(all_sizes) if all_sizes else 1
        
        # Add all nodes
        for node in nodes:
            add_node(node)
        
        return {
            'ids': ids,
            'labels': labels,
            'parents': parents,
            'values': values,
            'colors': colors,
            'hover_texts': hover_texts
        }
    
    def generate_treemap(self, max_depth: int = 3) -> go.Figure:
        """Generate TreeMap visualization data."""
        if not self.data:
            # Create empty treemap
            fig = go.Figure(go.Treemap(
                labels=["No Data"],
                parents=[""],
                values=[1],
                textinfo="label"
            ))
            fig.update_layout(title="No Data Available")
            return fig
        
        # Convert data to nodes
        if hasattr(self.data, 'directory_tree') and self.data.directory_tree:
            nodes = self._convert_directory_tree_to_nodes(self.data.directory_tree, max_depth)
        elif isinstance(self.data, dict):
            nodes = self._convert_directory_tree_to_nodes(self.data, max_depth)
        else:
            # Fallback for other data formats
            nodes = []
        
        if not nodes:
            # Create empty treemap
            fig = go.Figure(go.Treemap(
                labels=["No Data"],
                parents=[""],
                values=[1],
                textinfo="label"
            ))
            fig.update_layout(title="No Data Available")
            return fig
        
        # Flatten nodes for Plotly
        plotly_data = self._flatten_nodes_for_plotly(nodes)
        fig = go.Figure(go.Treemap(
            ids=plotly_data['ids'],
            labels=plotly_data['labels'],
            parents=plotly_data['parents'],
            values=plotly_data['values'],
            textinfo="label+value+percent parent",
            hovertext=plotly_data['hover_texts'],
            hovertemplate='%{hovertext}<extra></extra>',
            marker=dict(
                colors=plotly_data['colors'],
                line=dict(width=2, color='white')
            ),
            maxdepth=max_depth,
            branchvalues="total"
        ))
        
        # Update layout
        fig.update_layout(
            title={
                'text': "Disk Usage TreeMap",
                'x': 0.5,
                'xanchor': 'center'
            },
            font=dict(size=12),
            margin=dict(t=50, l=25, r=25, b=25),
            height=600
        )
        
        return fig
    
    def export_as_image(self, format: str = "png", width: int = 1200, height: int = 800) -> bytes:
        """Export TreeMap as image."""
        try:
            fig = self.generate_treemap()
            
            # Export as image
            img_bytes = fig.to_image(
                format=format.lower(),
                width=width,
                height=height,
                engine="kaleido"
            )
            
            return img_bytes
        except Exception as e:
            raise RuntimeError(f"Failed to export treemap as {format}: {str(e)}")
    
    def export_as_html(self, interactive: bool = True, include_plotlyjs: str = 'cdn') -> str:
        """Export TreeMap as HTML."""
        try:
            fig = self.generate_treemap()
            
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
            raise RuntimeError(f"Failed to export treemap as HTML: {str(e)}")
    
    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes into human-readable format."""
        if bytes_count == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"