"""
Interactive dashboard for comprehensive data visualization.
"""

import logging
import os
from typing import Any, Dict, List
from pathlib import Path

log = logging.getLogger(__name__)
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from plotly.offline import plot
    import plotly.express as px
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
        def bar(*args, **kwargs):
            """Bar.

            Manages bar operations and coordinates related state changes for the component.
            """
            return go.Figure()
        @staticmethod
        def pie(*args, **kwargs):
            """Pie.

            Manages pie operations and coordinates related state changes for the component.
            """
            return go.Figure()
    def make_subplots(*args, **kwargs):
        """make_subplots.

        Manages make subplots operations and coordinates related state changes for the component.
        """
        return go.Figure()
    def plot(*args, **kwargs):
        """Plot.

        Manages plot operations and coordinates related state changes for the component.
        """
        pass

from cortex_unified.visualization.treemap_generator import TreeMapGenerator
from cortex_unified.visualization.sunburst_generator import SunburstGenerator

class InteractiveDashboard:
    """Composes analyzer output into interactive Plotly dashboards.

    Offers treemap-only, sunburst-only, side-by-side, and combined
    layouts; drill-down swaps in a fresh analyzer rooted at the
    clicked path so the caller's original analyzer is untouched.
    """
    
    def __init__(self, analyzer: Any = None):
        """Store the analyzer; generators defer until first render.

        Initializes the instance and configures internal state.

        Args:
            analyzer (Any): The analyzer parameter.
        """
        self.analyzer = analyzer
        self.has_plotly = HAS_PLOTLY
        if not self.has_plotly:
            import warnings
            warnings.warn("Plotly not available. Dashboard features will be limited.")
        self.treemap_generator = None
        self.sunburst_generator = None
        self.current_path = None
        self.drill_down_history = []
        
    def _initialize_generators(self):
        """(Re)build tree generators from the current analyzer.

        Manages initialize generators operations and coordinates related state changes for the component.
        """
        if self.analyzer:
            self.treemap_generator = TreeMapGenerator(self.analyzer)
            self.sunburst_generator = SunburstGenerator(self.analyzer)
    
    def create_dashboard(self, layout_type: str = "combined") -> go.Figure:
        """Render the requested layout.

        Args:
            layout_type: "treemap_only", "sunburst_only",
                "side_by_side", or "combined" (default).

        Returns:
            Plotly figure; annotation-only figure when no data exists.
        """
        if not self.analyzer:
            return self._create_empty_dashboard()
        
        self._initialize_generators()
        
        if layout_type == "treemap_only":
            return self._create_treemap_dashboard()
        elif layout_type == "sunburst_only":
            return self._create_sunburst_dashboard()
        elif layout_type == "side_by_side":
            return self._create_side_by_side_dashboard()
        else:  # combined
            return self._create_combined_dashboard()
    
    def _create_empty_dashboard(self) -> go.Figure:
        """Empty state figure prompting the user to run an analysis.

        Manages create empty dashboard operations and coordinates related state changes for the component.

        Returns:
            go.Figure: Result of the operation.
        """
        fig = go.Figure()
        fig.add_annotation(
            text="No data available. Please run disk analysis first.",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title="Interactive Disk Usage Dashboard",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=600
        )
        return fig
    
    def _create_treemap_dashboard(self) -> go.Figure:
        """Full-height treemap alone.

        Manages create treemap dashboard operations and coordinates related state changes for the component.

        Returns:
            go.Figure: Result of the operation.
        """
        if not self.treemap_generator:
            return self._create_empty_dashboard()
        
        fig = self.treemap_generator.generate_treemap()
        fig.update_layout(
            title="Interactive Disk Usage TreeMap",
            height=700
        )
        return fig
    
    def _create_sunburst_dashboard(self) -> go.Figure:
        """Full-height sunburst alone.

        Manages create sunburst dashboard operations and coordinates related state changes for the component.

        Returns:
            go.Figure: Result of the operation.
        """
        if not self.sunburst_generator:
            return self._create_empty_dashboard()
        
        fig = self.sunburst_generator.generate_sunburst()
        fig.update_layout(
            title="Interactive Disk Usage Sunburst",
            height=700
        )
        return fig
    
    def _create_side_by_side_dashboard(self) -> go.Figure:
        """Treemap and sunburst sharing one row.

        Manages create side by side dashboard operations and coordinates related state changes for the component.

        Returns:
            go.Figure: Result of the operation.
        """
        if not self.treemap_generator or not self.sunburst_generator:
            return self._create_empty_dashboard()
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("TreeMap View", "Sunburst View"),
            specs=[[{"type": "treemap"}, {"type": "sunburst"}]],
            horizontal_spacing=0.05
        )
        
        # Subplots cannot nest figures; copy traces over grid slot by slot
        treemap_fig = self.treemap_generator.generate_treemap()
        sunburst_fig = self.sunburst_generator.generate_sunburst()
        
        for trace in treemap_fig.data:
            fig.add_trace(trace, row=1, col=1)
        
        for trace in sunburst_fig.data:
            fig.add_trace(trace, row=1, col=2)
        
        fig.update_layout(
            title="Interactive Disk Usage Dashboard",
            height=700,
            showlegend=False
        )
        
        return fig
    
    def _create_combined_dashboard(self) -> go.Figure:
        """Pie + bar overview on row 1, full-width treemap on row 2.

        Manages create combined dashboard operations and coordinates related state changes for the component.

        Returns:
            go.Figure: Result of the operation.
        """
        if not self.analyzer:
            return self._create_empty_dashboard()
        
        # Treemap spans both columns; the trailing None pads the spec grid
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Disk Usage Overview", "File Type Distribution",
                "Directory TreeMap", "Size Distribution"
            ),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "treemap", "colspan": 2}, None]
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.05
        )
        
        self._add_disk_usage_pie(fig, row=1, col=1)
        
        self._add_file_type_bar(fig, row=1, col=2)
        
        if self.treemap_generator:
            treemap_fig = self.treemap_generator.generate_treemap()
            for trace in treemap_fig.data:
                fig.add_trace(trace, row=2, col=1)
        
        fig.update_layout(
            title="Comprehensive Disk Usage Dashboard",
            height=800,
            showlegend=True
        )
        
        return fig
    
    def _add_disk_usage_pie(self, fig: go.Figure, row: int, col: int):
        """Pie of used vs free bytes; silently skipped when data absent.

        Manages add disk usage pie operations and coordinates related state changes for the component.

        Args:
            fig (go.Figure): The fig parameter.
            row (int): Table row index or list of row indices.
            col (int): The col parameter.
        """
        if hasattr(self.analyzer, 'disk_usage') and self.analyzer.disk_usage:
            disk_data = self.analyzer.disk_usage
            
            labels = ['Used Space', 'Free Space']
            values = [
                disk_data.get('used_bytes', 0),
                disk_data.get('free_bytes', 0)
            ]
            colors = ['#e74c3c', '#2ecc71']
            
            fig.add_trace(
                go.Pie(
                    labels=labels,
                    values=values,
                    marker_colors=colors,
                    textinfo='label+percent',
                    hovertemplate='%{label}<br>%{value:,.0f} bytes<br>%{percent}<extra></extra>'
                ),
                row=row, col=col
            )
    
    def _add_file_type_bar(self, fig: go.Figure, row: int, col: int):
        """Bar chart of the ten largest extensions by total bytes.

        Manages add file type bar operations and coordinates related state changes for the component.

        Args:
            fig (go.Figure): The fig parameter.
            row (int): Table row index or list of row indices.
            col (int): The col parameter.
        """
        if hasattr(self.analyzer, 'file_type_breakdown') and self.analyzer.file_type_breakdown:
            file_types = self.analyzer.file_type_breakdown
            
            sorted_types = sorted(
                file_types.items(),
                key=lambda x: x[1].get('size_bytes', 0),
                reverse=True
            )[:10]
            
            extensions = [item[0] for item in sorted_types]
            sizes = [item[1].get('size_bytes', 0) for item in sorted_types]
            
            fig.add_trace(
                go.Bar(
                    x=extensions,
                    y=sizes,
                    marker_color='#3498db',
                    hovertemplate='%{x}<br>Size: %{y:,.0f} bytes<extra></extra>'
                ),
                row=row, col=col
            )
            
            fig.update_xaxes(title_text="File Extension", row=row, col=col)
            fig.update_yaxes(title_text="Size (bytes)", row=row, col=col)
    
    def handle_drill_down(self, path: str) -> go.Figure:
        """Re-root the analysis at ``path`` and rebuild the dashboard.

        Uses a fresh DiskAnalyzer rather than mutating the existing one,
        preserving the caller's original analyzer object.
        """
        if self.current_path:
            self.drill_down_history.append(self.current_path)
        
        self.current_path = path
        
        if self.analyzer and hasattr(self.analyzer, '__class__'):
            from cortex_unified.analyzers.disk_analyzer import DiskAnalyzer
            
            drill_analyzer = DiskAnalyzer(
                config=getattr(self.analyzer, 'config', None),
                root_path=path
            )
            
            drill_analyzer.analyze_disk_usage()
            drill_analyzer.analyze_directory_tree()
            drill_analyzer.analyze_file_types()
            
            self.analyzer = drill_analyzer
            
            return self.create_dashboard()
        
        return self._create_empty_dashboard()
    
    def handle_drill_up(self) -> go.Figure:
        """Pop the last drilled path; walk to the filesystem parent if empty.

        Manages handle drill up operations and coordinates related state changes for the component.

        Returns:
            go.Figure: Result of the operation.
        """
        if self.drill_down_history:
            previous_path = self.drill_down_history.pop()
            return self.handle_drill_down(previous_path)
        else:
            # No history: climb one directory instead
            if self.current_path:
                parent_path = str(Path(self.current_path).parent)
                return self.handle_drill_down(parent_path)
        
        return self.create_dashboard()
    
    def handle_context_menu(self, path: str) -> Dict[str, Any]:
        """Action descriptors offered for a right-clicked path.

        Manages handle context menu operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        context_actions = {
            'open_in_explorer': {
                'label': 'Open in File Explorer',
                'action': 'open_explorer',
                'path': path
            },
            'drill_down': {
                'label': 'Drill Down',
                'action': 'drill_down',
                'path': path
            },
            'exclude_from_scan': {
                'label': 'Exclude from Future Scans',
                'action': 'exclude',
                'path': path
            },
            'analyze_separately': {
                'label': 'Analyze Separately',
                'action': 'analyze',
                'path': path
            }
        }
        
        return context_actions
    
    def export_visualization(self, format: str, filepath: str, visualization_type: str = "dashboard") -> bool:
        """Export a figure to image or HTML.

        Args:
            format: "png"/"jpg"/"jpeg"/"svg" for raster, "html" for a div.
            filepath: Destination file path.
            visualization_type: "treemap", "sunburst", or "dashboard".

        Returns:
            True on success; False on unsupported format or failure.
        """
        try:
            if visualization_type == "treemap" and self.treemap_generator:
                if format.lower() in ['png', 'jpg', 'jpeg', 'svg']:
                    img_data = self.treemap_generator.export_as_image(format)
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                elif format.lower() == 'html':
                    html_data = self.treemap_generator.export_as_html()
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_data)
                else:
                    return False
                    
            elif visualization_type == "sunburst" and self.sunburst_generator:
                if format.lower() in ['png', 'jpg', 'jpeg', 'svg']:
                    img_data = self.sunburst_generator.export_as_image(format)
                    with open(filepath, 'wb') as f:
                        f.write(img_data)
                elif format.lower() == 'html':
                    html_data = self.sunburst_generator.export_as_html()
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_data)
                else:
                    return False
                    
            else:  # dashboard
                fig = self.create_dashboard()
                if format.lower() in ['png', 'jpg', 'jpeg', 'svg']:
                    fig.write_image(filepath, format=format.lower())
                elif format.lower() == 'html':
                    html_str = plot(
                        fig,
                        output_type='div',
                        include_plotlyjs='cdn'
                    )
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_str)
                else:
                    return False
            
            return True
            
        except Exception as e:
            log.warning("Dashboard export failed: %s", e)
            return False
    
    def export_batch(self, base_path: str, formats: List[str]) -> Dict[str, bool]:
        """Export the dashboard once per format; per-format success map.

        Manages export batch operations and coordinates related state changes for the component.

        Args:
            base_path (str): Filesystem path to the target file or directory.
            formats (List[str]): The formats parameter.

        Returns:
            Dict[str, bool]: Dictionary mapping identifiers to status or values.
        """
        results = {}
        
        for format_type in formats:
            try:
                filename = f"dashboard.{format_type.lower()}"
                filepath = os.path.join(base_path, filename)
                success = self.export_visualization(format_type, filepath)
                results[format_type] = success
            except Exception as e:
                results[format_type] = False
        
        return results
    
    def refresh_data(self) -> go.Figure:
        """Re-run all analyses and rebuild; empty figure without analyzer.

        Manages refresh data operations and coordinates related state changes for the component.

        Returns:
            go.Figure: Result of the operation.
        """
        if self.analyzer and hasattr(self.analyzer, 'analyze_disk_usage'):
            self.analyzer.analyze_disk_usage()
            self.analyzer.analyze_directory_tree()
            self.analyzer.analyze_file_types()
            
            self._initialize_generators()
            
            return self.create_dashboard()
        
        return self._create_empty_dashboard()
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Snapshot of current path, drill depth, size, and counts.

        Manages get dashboard stats operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        if not self.analyzer:
            return {}
        
        stats = {
            'current_path': self.current_path or getattr(self.analyzer, 'root_path', 'Unknown'),
            'drill_down_depth': len(self.drill_down_history),
            'total_size': 0,
            'file_count': 0,
            'directory_count': 0
        }
        
        if hasattr(self.analyzer, 'disk_usage') and self.analyzer.disk_usage:
            stats['total_size'] = self.analyzer.disk_usage.get('used_bytes', 0)
        
        if hasattr(self.analyzer, 'directory_tree') and self.analyzer.directory_tree:
            tree = self.analyzer.directory_tree
            if isinstance(tree, dict):
                stats['file_count'] = tree.get('file_count', 0)
                stats['directory_count'] = tree.get('dir_count', 0)
        
        return stats