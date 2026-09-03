"""Comprehensive tooltip and help system for Cortex Cleaner GUI."""

from typing import Dict, Any
from PySide6.QtWidgets import QToolTip, QWidget, QAbstractButton, QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton
from PySide6.QtGui import QCursor, QFont
from PySide6.QtCore import Qt, QPoint

class TooltipManager:
    """Manages tooltips and help text for GUI components."""
    
    # Comprehensive tooltip definitions
    TOOLTIPS = {
        # Main Window Actions
        'scan_button': {
            'text': 'Start scanning for empty files and directories',
            'help': 'Begins the scanning process to find empty files and directories in the selected path. '
                   'This operation is safe and does not modify any files.'
        },
        'pause_button': {
            'text': 'Pause the current scanning operation',
            'help': 'Temporarily stops the scanning process. You can resume from where it left off. '
                   'Useful for managing system resources or handling interruptions.'
        },
        'resume_button': {
            'text': 'Resume the paused scanning operation',
            'help': 'Continues scanning from where it was paused. The scan state is preserved '
                   'and no progress is lost.'
        },
        'delete_button': {
            'text': 'Delete the selected empty files and directories',
            'help': 'Permanently removes the selected empty files and directories. '
                   'A backup manifest is created for potential restoration. Use with caution.'
        },
        
        # Path and Options
        'path_input': {
            'text': 'Enter the directory path to scan',
            'help': 'Specify the root directory where scanning should begin. '
                   'The scan will include all subdirectories unless excluded.'
        },
        'browse_button': {
            'text': 'Browse for directory to scan',
            'help': 'Opens a file dialog to select the directory you want to scan. '
                   'Navigate to your desired location and select it.'
        },
        'dry_run_checkbox': {
            'text': 'Preview mode - show what would be deleted without actually deleting',
            'help': 'When enabled, operations will only show what would be affected without '
                   'making any actual changes. This is the safest way to test operations.'
        },
        'trash_checkbox': {
            'text': 'Move files to system trash instead of permanent deletion',
            'help': 'When enabled, files are moved to the system trash/recycle bin instead '
                   'of being permanently deleted. Allows for easy recovery if needed.'
        },
        'pattern_input': {
            'text': 'Filter files by pattern (e.g., *.tmp, *.log)',
            'help': 'Use glob patterns to filter which files to consider. Examples: '
                   '*.tmp (temporary files), *.log (log files), test* (files starting with "test")'
        },
        'age_spinbox': {
            'text': 'Only consider files older than specified days',
            'help': 'Set minimum age in days for files to be considered. '
                   '0 means all files, 30 means only files older than 30 days.'
        },
        
        # Performance Options
        'enable_checkpoints_checkbox': {
            'text': 'Enable checkpoint system for resumable operations',
            'help': 'Allows pausing and resuming long-running operations. '
                   'Checkpoints are saved periodically to preserve progress.'
        },
        'enable_throttling_checkbox': {
            'text': 'Limit resource usage to prevent system slowdown',
            'help': 'Automatically adjusts CPU and memory usage to maintain system responsiveness. '
                   'Recommended for background operations.'
        },
        'cpu_limit_spinbox': {
            'text': 'Maximum CPU usage percentage',
            'help': 'Limits CPU usage to prevent system overload. Lower values make operations '
                   'slower but keep the system more responsive.'
        },
        'memory_limit_spinbox': {
            'text': 'Maximum memory usage percentage',
            'help': 'Limits memory usage to prevent system slowdown. Useful when scanning '
                   'very large directory structures.'
        },
        
        # Duplicate Finder
        'find_duplicates_button': {
            'text': 'Find duplicate files in the selected directory',
            'help': 'Scans for files with identical content using hash comparison. '
                   'This process may take time for large directories.'
        },
        'delete_duplicates_button': {
            'text': 'Delete selected duplicate files',
            'help': 'Removes the selected duplicate files based on the chosen strategy. '
                   'The original file (as determined by strategy) is preserved.'
        },
        'hash_algorithm_combo': {
            'text': 'Algorithm used for duplicate detection',
            'help': 'MD5: Fast but less secure. SHA1: Good balance. SHA256: Most secure but slower. '
                   'For most purposes, MD5 is sufficient and fastest.'
        },
        'strategy_combo': {
            'text': 'Strategy for selecting which duplicates to keep',
            'help': 'Keep Newest: Preserves most recently modified file. '
                   'Keep Oldest: Preserves oldest file. '
                   'Keep Largest/Smallest: Based on file size.'
        },
        
        # Large Files
        'find_large_files_button': {
            'text': 'Find files larger than the specified size',
            'help': 'Scans for files exceeding the minimum size threshold. '
                   'Useful for identifying space-consuming files.'
        },
        'delete_large_files_button': {
            'text': 'Delete selected large files',
            'help': 'Permanently removes the selected large files. '
                   'Review the list carefully before deletion.'
        },
        'min_size_spinbox': {
            'text': 'Minimum file size in megabytes',
            'help': 'Files smaller than this size will be ignored. '
                   'Set higher values to find only very large files.'
        },
        
        # Disk Analyzer
        'analyze_disk_button': {
            'text': 'Analyze disk usage and generate reports',
            'help': 'Performs comprehensive disk usage analysis including directory sizes, '
                   'file type breakdown, and largest directories.'
        },
        'show_treemap_button': {
            'text': 'Display interactive TreeMap visualization',
            'help': 'Shows disk usage as a TreeMap where larger rectangles represent '
                   'larger directories. Click to drill down into subdirectories.'
        },
        'show_sunburst_button': {
            'text': 'Display interactive Sunburst chart',
            'help': 'Shows directory hierarchy as a circular chart with nested rings. '
                   'Each ring represents a directory level.'
        },
        'export_visualization_button': {
            'text': 'Export visualization to file',
            'help': 'Saves the current visualization as HTML, PNG, or SVG file. '
                   'HTML files are interactive, images are static.'
        },
        
        # Docker Cleanup
        'docker_scan_button': {
            'text': 'Scan for unused Docker resources',
            'help': 'Finds unused Docker images, stopped containers, unused volumes, '
                   'and unused networks that can be safely removed.'
        },
        'docker_clean_button': {
            'text': 'Clean selected Docker resources',
            'help': 'Removes the selected Docker resources to free up disk space. '
                   'A backup manifest is created for safety.'
        },
        'docker_images_checkbox': {
            'text': 'Include unused Docker images in scan',
            'help': 'Scans for dangling and unused Docker images. These often consume '
                   'significant disk space and can usually be safely removed.'
        },
        'docker_containers_checkbox': {
            'text': 'Include stopped containers in scan',
            'help': 'Finds containers that have stopped running. These can usually '
                   'be removed unless you plan to restart them.'
        },
        'docker_volumes_checkbox': {
            'text': 'Include unused volumes in scan',
            'help': 'Finds Docker volumes not attached to any container. '
                   'Be careful as these may contain important data.'
        },
        'docker_networks_checkbox': {
            'text': 'Include unused networks in scan',
            'help': 'Finds Docker networks not used by any container. '
                   'These are usually safe to remove.'
        },
        
        # Package Manager Cleanup
        'package_scan_button': {
            'text': 'Scan package manager caches and orphaned packages',
            'help': 'Finds cached files and orphaned packages from various package managers '
                   'like pip, npm, conda, and system package managers.'
        },
        'package_clean_button': {
            'text': 'Clean selected package manager resources',
            'help': 'Removes cached files and orphaned packages. Package lists are '
                   'backed up before making changes.'
        },
        'pip_checkbox': {
            'text': 'Include pip cache in scan',
            'help': 'Scans Python pip package manager cache. Safe to clean as '
                   'packages can be re-downloaded when needed.'
        },
        'npm_checkbox': {
            'text': 'Include npm cache in scan',
            'help': 'Scans Node.js npm package manager cache. Includes integrity '
                   'verification to ensure cache consistency.'
        },
        'conda_checkbox': {
            'text': 'Include conda cache in scan',
            'help': 'Scans Anaconda/Miniconda package manager cache. Includes both '
                   'package cache and tarballs.'
        },
        'system_packages_checkbox': {
            'text': 'Include system package manager cache',
            'help': 'Scans system package managers (apt, dnf, pacman, brew, chocolatey) '
                   'for cached packages and orphaned dependencies.'
        },
        'keep_recent_days_spinbox': {
            'text': 'Keep cache files newer than specified days',
            'help': 'Preserves recently downloaded packages to avoid re-downloading. '
                   '7 days is usually a good balance between space and convenience.'
        },
        
        # Heuristics Scan
        'heuristics_scan_button': {
            'text': 'Scan for application leftovers using AI patterns',
            'help': 'Uses machine learning and pattern recognition to detect leftover '
                   'files from uninstalled applications. Review results carefully.'
        },
        'heuristics_clean_button': {
            'text': 'Clean detected application leftovers',
            'help': 'Removes files identified as application leftovers. Only high-confidence '
                   'detections are recommended for automatic cleaning.'
        },
        'confidence_threshold_spinbox': {
            'text': 'Minimum confidence score for detections (0.0-1.0)',
            'help': 'Higher values show only high-confidence detections. 0.7 is recommended '
                   'for manual review, 0.9 for automatic cleaning.'
        },
        'ml_patterns_checkbox': {
            'text': 'Use machine learning patterns for detection',
            'help': 'Enables AI-powered pattern recognition for better leftover detection. '
                   'Improves accuracy but may be slower.'
        },
        'scan_registry_checkbox': {
            'text': 'Include Windows registry analysis (Windows only)',
            'help': 'Analyzes Windows registry for orphaned entries that correspond '
                   'to missing files. Requires administrator privileges.'
        },
        
        # Broken Links
        'broken_links_scan_button': {
            'text': 'Scan for broken symlinks and shortcuts',
            'help': 'Finds broken symbolic links, Windows shortcuts (.lnk), and '
                   'registry references to non-existent files.'
        },
        'broken_links_repair_button': {
            'text': 'Attempt to repair broken links',
            'help': 'Tries to fix broken links by searching for moved targets. '
                   'Creates backups before making changes.'
        },
        'scan_symlinks_checkbox': {
            'text': 'Include symbolic links in scan',
            'help': 'Scans for broken symbolic links on all platforms. '
                   'These are usually safe to remove or repair.'
        },
        'scan_shortcuts_checkbox': {
            'text': 'Include Windows shortcuts in scan',
            'help': 'Scans for broken Windows .lnk shortcut files. '
                   'Can attempt to find moved targets automatically.'
        },
        
        # Multi-Drive Scanning
        'multi_drive_scan_button': {
            'text': 'Scan multiple drives simultaneously',
            'help': 'Scans multiple drives or network locations in parallel. '
                   'Useful for comprehensive system cleanup.'
        },
        'drive_selection_list': {
            'text': 'Select drives to scan',
            'help': 'Choose which drives to include in the scan. Network drives '
                   'may require credentials and have longer timeouts.'
        },
        'parallel_scanning_checkbox': {
            'text': 'Enable parallel drive scanning',
            'help': 'Scans multiple drives simultaneously for faster completion. '
                   'May increase system load but reduces total time.'
        },
        'network_timeout_spinbox': {
            'text': 'Network drive timeout in seconds',
            'help': 'How long to wait for network drive responses. Increase for '
                   'slow networks, decrease for faster failure detection.'
        },
        
        # Settings and Preferences
        'language_combo': {
            'text': 'Select interface language',
            'help': 'Changes the language of all interface text. Restart may be '
                   'required for all changes to take effect.'
        },
        'theme_combo': {
            'text': 'Select visual theme',
            'help': 'Changes the appearance of the interface. High contrast themes '
                   'improve accessibility for users with visual impairments.'
        },
        'enable_keyboard_shortcuts_checkbox': {
            'text': 'Enable keyboard shortcuts for accessibility',
            'help': 'Allows navigation and operation using keyboard only. '
                   'Essential for accessibility and power users.'
        },
        'enable_screen_reader_checkbox': {
            'text': 'Enable screen reader support',
            'help': 'Provides additional information for screen reader software. '
                   'Improves accessibility for visually impaired users.'
        },
        'announce_changes_checkbox': {
            'text': 'Announce changes to screen readers',
            'help': 'Automatically announces important changes and progress updates '
                   'to screen reader software.'
        },
        
        # Progress and Status
        'progress_bar': {
            'text': 'Shows current operation progress',
            'help': 'Displays the progress of the current operation. The percentage '
                   'and estimated time remaining are shown when available.'
        },
        'status_label': {
            'text': 'Current operation status',
            'help': 'Shows what operation is currently running and any important '
                   'status messages or warnings.'
        },
        'results_table': {
            'text': 'Results of the current operation',
            'help': 'Shows detailed results including file paths, sizes, and other '
                   'relevant information. Use checkboxes to select items for action.'
        },
        
        # Export and Reporting
        'export_json_button': {
            'text': 'Export results to JSON file',
            'help': 'Saves the current results in JSON format for analysis or '
                   'integration with other tools.'
        },
        'export_csv_button': {
            'text': 'Export results to CSV file',
            'help': 'Saves the current results in CSV format for analysis in '
                   'spreadsheet applications.'
        },
        'generate_report_button': {
            'text': 'Generate comprehensive HTML report',
            'help': 'Creates a detailed HTML report with charts, statistics, and '
                   'recommendations based on the analysis results.'
        },
    }
    
    # Keyboard shortcuts help
    KEYBOARD_SHORTCUTS = {
        'Ctrl+S': 'Start Scan',
        'Ctrl+D': 'Delete/Clean Selected Items',
        'Ctrl+P': 'Pause Operation',
        'Ctrl+R': 'Resume Operation',
        'Ctrl+E': 'Export Results',
        'Ctrl+,': 'Open Settings',
        'F1': 'Show Help',
        'F5': 'Refresh View',
        'Ctrl+A': 'Select All Items',
        'Ctrl+Q': 'Quit Application',
        'Tab': 'Next Control',
        'Shift+Tab': 'Previous Control',
        'Space': 'Toggle Selection',
        'Enter': 'Activate Button/Confirm',
        'Escape': 'Cancel Operation',
    }
    
    @classmethod
    def apply_tooltip(cls, widget: QWidget, tooltip_key: str, 
                     include_help: bool = False) -> None:
        """Apply tooltip to a widget.
        
        Args:
            widget: Widget to apply tooltip to
            tooltip_key: Key in TOOLTIPS dictionary
            include_help: Whether to include extended help text
        """
        if tooltip_key not in cls.TOOLTIPS:
            return
        
        tooltip_data = cls.TOOLTIPS[tooltip_key]
        tooltip_text = tooltip_data['text']
        
        if include_help and 'help' in tooltip_data:
            tooltip_text += f"\n\n{tooltip_data['help']}"
        
        widget.setToolTip(tooltip_text)
        
        # Set accessible description for screen readers
        widget.setAccessibleDescription(tooltip_data.get('help', tooltip_text))
    
    @classmethod
    def apply_tooltips_to_window(cls, window) -> None:
        """Apply tooltips to all widgets in a window.
        
        Args:
            window: Main window or dialog to process
        """
        # Find all widgets with object names that match tooltip keys
        for tooltip_key in cls.TOOLTIPS:
            widget = window.findChild(QWidget, tooltip_key)
            if widget:
                cls.apply_tooltip(widget, tooltip_key, include_help=True)
    
    @classmethod
    def get_keyboard_shortcuts_text(cls) -> str:
        """Get formatted keyboard shortcuts help text.
        
        Returns:
            Formatted help text for keyboard shortcuts
        """
        shortcuts_text = "Keyboard Shortcuts:\n\n"
        for shortcut, description in cls.KEYBOARD_SHORTCUTS.items():
            shortcuts_text += f"{shortcut:<15} {description}\n"
        
        return shortcuts_text
    
    @classmethod
    def show_help_dialog(cls, parent=None) -> None:
        """Show comprehensive help dialog.
        
        Args:
            parent: Parent widget for the dialog
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("Cortex Cleaner Help")
        dialog.setModal(True)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout(dialog)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        
        # Add comprehensive help content
        content = """
        <h2>Cortex Cleaner Help</h2>
        
        <h3>Overview</h3>
        <p>Cortex Cleaner is a comprehensive utility for finding and removing unnecessary files, 
        analyzing disk usage, and maintaining system cleanliness. It provides multiple specialized 
        tools for different cleanup tasks.</p>
        
        <h3>Main Features</h3>
        <ul>
        <li><b>Empty Files Cleanup:</b> Find and remove empty files and directories safely</li>
        <li><b>Duplicate Detection:</b> Locate and manage duplicate files using hash comparison</li>
        <li><b>Large File Analysis:</b> Identify space-consuming files for review</li>
        <li><b>Disk Usage Analysis:</b> Comprehensive disk usage analysis with interactive visualizations</li>
        <li><b>Docker Cleanup:</b> Clean unused Docker resources (images, containers, volumes, networks)</li>
        <li><b>Package Manager Cleanup:</b> Clean caches and orphaned packages from various package managers</li>
        <li><b>Heuristics Scanning:</b> AI-powered detection of application leftovers</li>
        <li><b>Broken Link Detection:</b> Find and repair broken symlinks and shortcuts</li>
        </ul>
        
        <h3>Safety Features</h3>
        <ul>
        <li><b>Dry Run Mode:</b> Preview operations without making changes</li>
        <li><b>Backup Manifests:</b> Automatic backup creation for restoration</li>
        <li><b>Trash Support:</b> Move files to trash instead of permanent deletion</li>
        <li><b>Confirmation Prompts:</b> Require confirmation for destructive operations</li>
        <li><b>Comprehensive Logging:</b> Detailed logs of all operations</li>
        </ul>
        
        <h3>Performance Features</h3>
        <ul>
        <li><b>Checkpoint System:</b> Pause and resume long-running operations</li>
        <li><b>Resource Throttling:</b> Control CPU and memory usage</li>
        <li><b>Parallel Processing:</b> Multi-threaded operations for speed</li>
        <li><b>Progress Tracking:</b> Real-time progress updates</li>
        </ul>
        
        <h3>Accessibility</h3>
        <ul>
        <li><b>Keyboard Navigation:</b> Full keyboard support for all functions</li>
        <li><b>Screen Reader Support:</b> Compatible with screen reader software</li>
        <li><b>High Contrast Themes:</b> Improved visibility options</li>
        <li><b>Multiple Languages:</b> Interface available in multiple languages</li>
        </ul>
        
        """ + f"<h3>Keyboard Shortcuts</h3><pre>{cls.get_keyboard_shortcuts_text()}</pre>"
        
        help_text.setHtml(content)
        layout.addWidget(help_text)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.exec()

def setup_tooltips_and_help(main_window) -> None:
    """Set up comprehensive tooltips and help system for the main window.
    
    Args:
        main_window: Main application window
    """
    # Apply tooltips to all matching widgets
    TooltipManager.apply_tooltips_to_window(main_window)
    
    if hasattr(main_window, 'help_action'):
        main_window.help_action.triggered.connect(
            lambda: TooltipManager.show_help_dialog(main_window)
        )
    
    # Configure tooltip display settings
    QToolTip.setFont(QFont('Arial', 9))
    
    main_window.setWhatsThis(
        "Cortex Cleaner main window. Use the tabs to access different cleanup tools. "
        "Hover over controls for detailed tooltips, or press F1 for comprehensive help."
    )

def add_contextual_help(widget: QWidget, help_text: str) -> None:
    """Add contextual help to a widget.
    
    Args:
        widget: Widget to add help to
        help_text: Help text to display
    """
    widget.setWhatsThis(help_text)
    
    # Also set as accessible description for screen readers
    widget.setAccessibleDescription(help_text)

def create_help_button(parent, help_text: str) -> 'QPushButton':
    """Create a help button that shows contextual help.
    
    Args:
        parent: Parent widget
        help_text: Help text to display
    
    Returns:
        Configured help button
    """
    from PySide6.QtWidgets import QPushButton, QMessageBox
    
    help_button = QPushButton("?", parent)
    help_button.setMaximumSize(25, 25)
    help_button.setToolTip("Click for help")
    
    def show_help():
        QMessageBox.information(parent, "Help", help_text)
        """show_help."""
        """show_help."""
    
    help_button.clicked.connect(show_help)
    return help_button