"""
TreeMap visualization generator for disk usage analysis.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.offline import plot
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    # No-op stand-ins keep method bodies runnable without Plotly
    class go:
        """Go.

        Manages go operations and coordinates related state changes for the component.
        """
        class Figure:
            """Figure.

            Manages Figure operations and coordinates related state changes for the component.
            """
            def __init__(self, *args, **kwargs):
                """Initialize the instance and configure internal state.

                Sets up sub-widgets, event signal connections, and default options.
                """
                pass
            def add_trace(self, *args, **kwargs):
                """add_trace.

                Manages add trace operations and coordinates related state changes for the component.
                """
                pass
            def update_layout(self, *args, **kwargs):
                """update_layout.

                Manages update layout operations and coordinates related state changes for the component.
                """
                pass
    class px:
        """Px.

        Manages px operations and coordinates related state changes for the component.
        """
        @staticmethod
        def treemap(*args, **kwargs):
            """Treemap.

            Manages treemap operations and coordinates related state changes for the component.
            """
            return go.Figure()
    def plot(*args, **kwargs):
        """Plot.

        Manages plot operations and coordinates related state changes for the component.
        """
        pass

import colorsys

@dataclass
class TreeMapNode:
    """Treemapnode.

    Manages TreeMapNode operations and coordinates related state changes for the component.
    """
    name: str
    size: int
    path: str
    children: List['TreeMapNode']
    color: str
    depth: int
    file_type: Optional[str] = None
    modified_time: Optional[float] = None

class TreeMapGenerator:
    """Treemapgenerator.

    Manages TreeMapGenerator operations and coordinates related state changes for the component.
    """
    
    def __init__(self, data: Any = None):
        """Warn once without Plotly; color scale is sized lazily at flatten.

        Initializes the instance and configures internal state.

        Args:
            data (Any): The data parameter.
        """
        self.data = data
        self.color_map = {}
        self.has_plotly = HAS_PLOTLY
        if not self.has_plotly:
            import warnings
            warnings.warn("Plotly not available. Visualization features will be limited.")
        self._setup_color_scheme()
    
    def _setup_color_scheme(self):
        """Per-extension base hues; 'unknown' catches unlisted types.

        Manages setup color scheme operations and coordinates related state changes for the component.
        """
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
        """Extension tag for a path; 'directory'/'unknown' sentinels.

        Manages get file type from path operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.

        Returns:
            str: Formatted string or path.
        """
        if os.path.isdir(path):
            return 'directory'
        ext = os.path.splitext(path)[1].lower()
        return ext if ext else 'unknown'
    
    def _get_color_for_item(self, node: TreeMapNode) -> str:
        """Base hue by type, darkened proportionally to size share.

        Depends on ``self._max_size``, which
        ``_flatten_nodes_for_plotly`` populates before any coloring.
        """
        file_type = node.file_type or self._get_file_type_from_path(node.path)
        
        base_color = self.file_type_colors.get(file_type, self.file_type_colors['unknown'])
        
        if hasattr(self, '_max_size') and self._max_size > 0:
            size_ratio = node.size / self._max_size
            base_color = base_color.lstrip('#')
            r, g, b = tuple(int(base_color[i:i+2], 16) for i in (0, 2, 4))
            
            h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            v = max(0.3, v * (0.5 + 0.5 * size_ratio))  # legibility floor
            
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        
        return base_color
    
    def _convert_directory_tree_to_nodes(self, tree_data: Dict, max_depth: int = 3, current_depth: int = 0) -> List[TreeMapNode]:
        """Recursively materialize TreeMapNodes up to max_depth.

        Accepts a rooted dict, a dict of trees, or a list of trees;
        non-dict entries are skipped.
        """
        nodes = []
        
        if current_depth >= max_depth:
            return nodes
        
        if isinstance(tree_data, dict):
            if 'children' in tree_data:
                # Rooted tree vs mapping of trees
                trees = [tree_data]
            else:
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
            
            # Descend only if another level is allowed
            children_data = tree.get('children', [])
            if children_data and current_depth < max_depth - 1:
                node.children = self._convert_directory_tree_to_nodes(
                    children_data, max_depth, current_depth + 1
                )
            
            nodes.append(node)
        
        return nodes
    
    def _flatten_nodes_for_plotly(self, nodes: List[TreeMapNode]) -> Dict[str, List]:
        """Depth-first flatten into parallel arrays for go.Treemap.

        Also computes ``_max_size`` (consumed by ``_get_color_for_item``),
        so this must run before color resolution.
        """
        ids = []
        labels = []
        parents = []
        values = []
        colors = []
        hover_texts = []
        
        def add_node(node: TreeMapNode, parent_id: str = ""):
            """add_node.

            Manages add node operations and coordinates related state changes for the component.

            Args:
                node (TreeMapNode): The node parameter.
                parent_id (str): The parent id parameter.
            """
            node_id = f"{parent_id}/{node.name}" if parent_id else node.name
            
            ids.append(node_id)
            labels.append(node.name)
            parents.append(parent_id)
            values.append(node.size)
            colors.append(self._get_color_for_item(node))
            
            size_mb = node.size / (1024 * 1024) if node.size > 0 else 0
            hover_text = f"{node.name}<br>Size: {self._format_bytes(node.size)}<br>Path: {node.path}"
            hover_texts.append(hover_text)
            
            for child in node.children:
                add_node(child, node_id)
        
        all_sizes = []
        def collect_sizes(nodes_list):
            """collect_sizes.

            Manages collect sizes operations and coordinates related state changes for the component.

            Args:
                nodes_list: The nodes list parameter.
            """
            for node in nodes_list:
                all_sizes.append(node.size)
                collect_sizes(node.children)
        
        collect_sizes(nodes)
        self._max_size = max(all_sizes) if all_sizes else 1
        
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
        """Render the treemap figure, or a "No Data" empty state.

        Args:
            max_depth: Maximum nesting depth passed through to Plotly.
        """
        if not self.data:
            fig = go.Figure(go.Treemap(
                labels=["No Data"],
                parents=[""],
                values=[1],
                textinfo="label"
            ))
            fig.update_layout(title="No Data Available")
            return fig
        
        if hasattr(self.data, 'directory_tree') and self.data.directory_tree:
            nodes = self._convert_directory_tree_to_nodes(self.data.directory_tree, max_depth)
        elif isinstance(self.data, dict):
            nodes = self._convert_directory_tree_to_nodes(self.data, max_depth)
        else:
            nodes = []
        
        if not nodes:
            fig = go.Figure(go.Treemap(
                labels=["No Data"],
                parents=[""],
                values=[1],
                textinfo="label"
            ))
            fig.update_layout(title="No Data Available")
            return fig
        
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
        """Rasterize via the kaleido engine.

        Args:
            format: Image format, e.g. "png" or "svg".
            width: Output width in pixels.
            height: Output height in pixels.

        Returns:
            Encoded image bytes.

        Raises:
            RuntimeError: If generation or rasterization fails.
        """
        try:
            fig = self.generate_treemap()
            
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
        """Serialize to a standalone HTML <div>.

        Args:
            interactive: When False, strip pan/lasso/select mode-bar tools.
            include_plotlyjs: Passed to plot(): 'cdn', True, False, etc.

        Returns:
            HTML fragment string.

        Raises:
            RuntimeError: On serialization failure.
        """
        try:
            fig = self.generate_treemap()
            
            config = {
                'displayModeBar': interactive,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'] if not interactive else []
            }
            
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
        """Human-readable size using binary (1024-step) units.

        Converts raw numeric values into formatted, localized, and human-readable string representations.

        Args:
            bytes_count (int): The bytes count parameter.

        Returns:
            str: Formatted string or path.
        """
        if bytes_count == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"