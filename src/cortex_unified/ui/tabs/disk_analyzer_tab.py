"""Tab for disk analyzer tab in Cortex Cleaner GUI."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QCheckBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QHeaderView, QListWidget, QRadioButton,
    QComboBox, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QSpinBox, QTabWidget, QAbstractItemView, QSizePolicy, QListWidgetItem
)
from PySide6.QtCore import QThread, Signal, Qt, QObject, QTimer
from PySide6.QtGui import QIcon, QFont, QTextCursor

from .base_tab import BaseTab
from cortex_unified.core.config import Config
from cortex_unified.core.scanner import Scanner
from cortex_unified.core.deleter import Deleter
from cortex_unified.analyzers.disk_analyzer import DiskAnalyzer
from cortex_unified.core.utils import normalize_path
import webbrowser
import tempfile
from cortex_unified.visualization.treemap_generator import TreeMapGenerator
from cortex_unified.visualization.sunburst_generator import SunburstGenerator
from cortex_unified.visualization.interactive_dashboard import InteractiveDashboard

class DiskAnalyzerWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, config: Config, path: str):
        super().__init__()
        self.config = config
        self.path = path
        self.logger = logging.getLogger('disk_analyzer')
        """__init__."""
        """__init__."""

    def run(self):
        """Run the disk analysis process."""
        try:
            analyzer = DiskAnalyzer(self.config, self.path)
            disk_usage = analyzer.analyze_disk_usage()
            analyzer.analyze_directory_tree()
            file_types = analyzer.analyze_file_types()
            largest_dirs = analyzer.find_largest_directories()
            stats = analyzer.get_stats()
            formatted_disk_usage = stats.get('disk_usage', disk_usage)
            self.finished.emit({
                'disk_usage': formatted_disk_usage, 
                'file_types': file_types,
                'largest_dirs': largest_dirs, 
                'analyzer': analyzer
            })
        except Exception as e:
            self.logger.error('Error in disk analysis: {}'.format(str(e)))
            self.error.emit(str(e))
    """DiskAnalyzerWorker class."""
    """DiskAnalyzerWorker class."""

class DiskAnalyzerTab(BaseTab):
    """Tab for disk analyzer tab functionality."""

    def __init__(self, config, logger, safety_manager):
        super().__init__(config, logger, safety_manager)
        """__init__."""
        """__init__."""

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        path_group = QGroupBox('Target Path')
        path_layout = QHBoxLayout(path_group)
        path_layout.setContentsMargins(10, 10, 10, 10)
        
        self.disk_analyzer_path_input = QLineEdit()
        self.disk_analyzer_path_input.setPlaceholderText('Select directory to analyze...')
        self.disk_analyzer_path_input.setMinimumHeight(30)
        path_layout.addWidget(self.disk_analyzer_path_input)
        
        browse_button = QPushButton('Browse')
        browse_button.clicked.connect(lambda: self.browse_path_for_widget(self.disk_analyzer_path_input))
        browse_button.setMinimumHeight(30)
        browse_button.setStyleSheet('QPushButton { padding: 5px 15px; }')
        path_layout.addWidget(browse_button)
        layout.addWidget(path_group)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.analyze_disk_button = QPushButton('Analyze Disk')
        self.analyze_disk_button.clicked.connect(self.start_disk_analysis)
        self.analyze_disk_button.setMinimumHeight(35)
        self.analyze_disk_button.setStyleSheet('QPushButton { font-weight: bold; padding: 5px 20px; }')
        buttons_layout.addWidget(self.analyze_disk_button)
        
        self.show_treemap_button = QPushButton('TreeMap View')
        self.show_treemap_button.clicked.connect(self.show_treemap_visualization)
        self.show_treemap_button.setMinimumHeight(35)
        self.show_treemap_button.setEnabled(False)
        buttons_layout.addWidget(self.show_treemap_button)
        
        self.show_sunburst_button = QPushButton('Sunburst View')
        self.show_sunburst_button.clicked.connect(self.show_sunburst_visualization)
        self.show_sunburst_button.setMinimumHeight(35)
        self.show_sunburst_button.setEnabled(False)
        buttons_layout.addWidget(self.show_sunburst_button)
        
        self.show_dashboard_button = QPushButton('Interactive Dashboard')
        self.show_dashboard_button.clicked.connect(self.show_interactive_dashboard)
        self.show_dashboard_button.setMinimumHeight(35)
        self.show_dashboard_button.setEnabled(False)
        buttons_layout.addWidget(self.show_dashboard_button)
        
        self.export_visualization_button = QPushButton('Export Visualization')
        self.export_visualization_button.clicked.connect(self.export_visualization_dialog)
        self.export_visualization_button.setMinimumHeight(35)
        self.export_visualization_button.setEnabled(False)
        buttons_layout.addWidget(self.export_visualization_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        self.disk_analyzer_progress_bar = QProgressBar()
        self.disk_analyzer_progress_bar.setVisible(False)
        self.disk_analyzer_progress_bar.setMinimumHeight(25)
        layout.addWidget(self.disk_analyzer_progress_bar)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.disk_usage_label = QLabel('Disk usage information will appear here')
        self.disk_usage_label.setStyleSheet('QLabel { font-family: Consolas, Monaco, monospace; font-size: 14px; padding: 10px; }')
        self.disk_usage_label.setWordWrap(True)
        splitter.addWidget(self.disk_usage_label)
        
        file_types_group = QGroupBox('File Types Distribution')
        file_types_layout = QVBoxLayout(file_types_group)
        self.file_types_table = QTableWidget()
        self.file_types_table.setColumnCount(3)
        self.file_types_table.setHorizontalHeaderLabels(['Extension', 'Count', 'Size'])
        self.file_types_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        file_types_layout.addWidget(self.file_types_table)
        splitter.addWidget(file_types_group)
        
        largest_dirs_group = QGroupBox('Largest Directories')
        largest_dirs_layout = QVBoxLayout(largest_dirs_group)
        self.largest_dirs_table = QTableWidget()
        self.largest_dirs_table.setColumnCount(2)
        self.largest_dirs_table.setHorizontalHeaderLabels(['Directory', 'Size'])
        self.largest_dirs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        largest_dirs_layout.addWidget(self.largest_dirs_table)
        splitter.addWidget(largest_dirs_group)
        
        splitter.setSizes([100, 200, 200])
        layout.addWidget(splitter)

    def start_disk_analysis(self):
        """Start disk analysis running safely in a background worker."""
        path = self.disk_analyzer_path_input.text().strip()
        if not path:
            QMessageBox.warning(self, 'Warning', 'Please select a directory to analyze.')
            return
            
        try:
            normalized_path = normalize_path(path)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Invalid path: {str(e)}')
            return
            
        if not normalized_path.exists():
            QMessageBox.critical(self, 'Error', 'Selected path does not exist.')
            return
            
        self.analyze_disk_button.setEnabled(False)
        self.disk_analyzer_progress_bar.setVisible(True)
        self.disk_analyzer_progress_bar.setRange(0, 0)
        self.set_status('Analyzing disk...')
        self.add_activity('Analyzing disk...')
        
        worker = DiskAnalyzerWorker(self.config, str(normalized_path))
        self.add_worker_thread(worker)
        
        worker.finished.connect(self.disk_analysis_complete)
        worker.error.connect(self.disk_analysis_error)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        worker.error.connect(lambda: self._on_worker_finished(worker))
        worker.start()

    def _on_worker_finished(self, worker):
        self.remove_worker_thread(worker)
        worker.deleteLater()
        """_on_worker_finished."""
        """_on_worker_finished."""

    def disk_analysis_complete(self, result: dict):
        """Handle disk analysis completion."""
        disk_usage = result['disk_usage']
        file_types = result['file_types']
        largest_dirs = result['largest_dirs']
        analyzer = result.get('analyzer')
        
        self.current_analyzer = analyzer
        self.analyze_disk_button.setEnabled(True)
        self.disk_analyzer_progress_bar.setVisible(False)
        self.set_status('Disk analysis complete')
        self.add_activity('Disk analysis complete')
        
        if analyzer:
            self.show_treemap_button.setEnabled(True)
            self.show_sunburst_button.setEnabled(True)
            self.show_dashboard_button.setEnabled(True)
            self.export_visualization_button.setEnabled(True)
            
        usage_text = f"Disk Usage: {disk_usage.get('used_human_str', 'Unknown')} used of {disk_usage.get('total_human_str', 'Unknown')} ({disk_usage.get('used_percent', 0):.1f}%)"
        self.disk_usage_label.setText(usage_text)
        
        self.file_types_table.setRowCount(min(len(file_types), 20))
        for i, (ext, info) in enumerate(list(file_types.items())[:20]):
            self.file_types_table.setItem(i, 0, QTableWidgetItem(ext if ext else '(no extension)'))
            self.file_types_table.setItem(i, 1, QTableWidgetItem(str(info['count'])))
            
            if 'size_human' in info:
                size_human = info['size_human']
            elif 'size_bytes' in info:
                size_human = self.format_bytes(info['size_bytes'])
            else:
                size_human = 'Unknown'
            self.file_types_table.setItem(i, 2, QTableWidgetItem(size_human))
            
        self.largest_dirs_table.setRowCount(len(largest_dirs))
        for i, (path, size) in enumerate(largest_dirs):
            size_str = self.format_bytes(size)
            self.largest_dirs_table.setItem(i, 0, QTableWidgetItem(str(path)))
            self.largest_dirs_table.setItem(i, 1, QTableWidgetItem(size_str))

    def disk_analysis_error(self, error: str):
        self.logger.error(f'Disk analysis error: {error}')
        self.analyze_disk_button.setEnabled(True)
        self.disk_analyzer_progress_bar.setVisible(False)
        self.set_status('Disk analysis failed')
        self.add_activity(f'Disk analysis failed: {error}')
        QMessageBox.critical(self, 'Error', f'An error occurred during disk analysis:\n{error}')
        """disk_analysis_error."""
        """disk_analysis_error."""

    def quick_disk_analysis(self):
        self.logger.info('=== Quick disk analysis initiated ===')
        home_dir = str(Path.home())
        self.disk_analyzer_path_input.setText(home_dir)
        self.start_disk_analysis()
        """quick_disk_analysis."""
        """quick_disk_analysis."""

    # Methods for rendering visualizations natively inside PyQt layout maps
    def show_treemap_visualization(self):
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Error", "No analysis data available. Run scan first.")
            return
        generator = TreeMapGenerator(self.current_analyzer)
        html_str = generator.export_as_html()
        fd, temp_path = tempfile.mkstemp(suffix='.html', prefix='cortex_treemap_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_str)
        webbrowser.open('file://' + temp_path)
        """show_treemap_visualization."""
        """show_treemap_visualization."""

    def show_sunburst_visualization(self):
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Error", "No analysis data available. Run scan first.")
            return
        generator = SunburstGenerator(self.current_analyzer)
        html_str = generator.export_as_html()
        fd, temp_path = tempfile.mkstemp(suffix='.html', prefix='cortex_sunburst_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_str)
        webbrowser.open('file://' + temp_path)
        """show_sunburst_visualization."""
        """show_sunburst_visualization."""

    def show_interactive_dashboard(self):
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Error", "No analysis data available. Run scan first.")
            return
        dashboard = InteractiveDashboard(self.current_analyzer)
        fd, temp_path = tempfile.mkstemp(suffix='.html', prefix='cortex_dashboard_')
        os.close(fd)
        if dashboard.export_visualization('html', temp_path, 'dashboard'):
            webbrowser.open('file://' + temp_path)
        else:
            QMessageBox.critical(self, "Error", "Failed to generate dashboard.")
        """show_interactive_dashboard."""
        """show_interactive_dashboard."""

    def export_visualization_dialog(self):
        if not hasattr(self, 'current_analyzer') or not self.current_analyzer:
            QMessageBox.warning(self, "Error", "No analysis data available. Run scan first.")
            return
            
        file_path, filter = QFileDialog.getSaveFileName(
            self, "Export Dashboard", "", 
            "HTML File (*.html);;PNG Image (*.png);;SVG Image (*.svg)"
        )
        if not file_path:
            return
            
        format_type = file_path.split('.')[-1].lower() if '.' in file_path else 'html'
        dashboard = InteractiveDashboard(self.current_analyzer)
        
        self.add_activity(f"Exporting dashboard to {file_path}")
        success = dashboard.export_visualization(format_type, file_path, 'dashboard')
        if success:
            QMessageBox.information(self, "Success", f"Dashboard exported successfully to:\n{file_path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to export visualization. Make sure Kaleido and Plotly are installed for image export.")
        """export_visualization_dialog."""
        """export_visualization_dialog."""
