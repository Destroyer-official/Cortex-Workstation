"""Command-line interface for Cortex Cleaner."""

from cortex_unified._version import __version__

import os
import sys
from pathlib import Path
import click

from cortex_unified.core.scanner import Scanner
from cortex_unified.core.deleter import Deleter
from cortex_unified.core.config import Config, DEFAULT_CONFIG
from cortex_unified.core.utils import setup_logging, normalize_path

# Import new modules
from cortex_unified.analyzers.duplicate_finder import DuplicateFinder
from cortex_unified.analyzers.large_file_finder import LargeFileFinder
# from cortex_unified.analyzers.temp_cleaner import TempCleaner  # TODO: Create this module
from cortex_unified.analyzers.cache_cleaner import CacheCleaner
from cortex_unified.analyzers.old_file_cleaner import OldFileCleaner
from cortex_unified.analyzers.file_shredder import FileShredder
from cortex_unified.analyzers.disk_analyzer import DiskAnalyzer
from cortex_unified.analyzers.duplicate_folder_finder import DuplicateFolderFinder
from cortex_unified.analyzers.docker_cleaner import DockerCleaner
from cortex_unified.analyzers.broken_link_detector import BrokenLinkDetector

from cortex_unified.system_tools.startup_manager import StartupManager
from cortex_unified.system_tools.process_analyzer import ProcessAnalyzer

try:
    from cortex_unified.system_tools.registry_cleaner import RegistryCleaner
    HAS_REGISTRY_CLEANER = True
except ImportError:
    HAS_REGISTRY_CLEANER = False

from cortex_unified.scheduler.scheduler import TaskScheduler
from cortex_unified.scheduler.auto_clean_rules import AutoCleanRules
from cortex_unified.reports.restore_manager import RestoreManager
from cortex_unified.reports.reports import ReportsGenerator

@click.group()
@click.version_option(version=__version__)
def main():
    """Cortex Cleaner - A comprehensive utility to find and remove unnecessary files and folders."""
    pass

@main.command()
@click.option('--dry-run', is_flag=True, default=None, help='Show what would be deleted without actually deleting (default)')
@click.option('--delete', is_flag=True, default=False, help='Permanently delete empty files and folders')
@click.option('--trash', is_flag=True, default=False, help='Move empty files and folders to trash/recycle bin')
@click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)')
@click.option('--older-than', type=int, default=None, help='Only consider files older than N days')
@click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--quiet', is_flag=True, default=False, help='Suppress all output except errors')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)')
@click.option('--cpu-priority', type=click.Choice(['low', 'normal', 'high']), default='normal', help='CPU priority for scanning')
@click.option('--io-priority', type=click.Choice(['low', 'normal', 'high']), default='low', help='I/O priority for scanning')
@click.option('--checkpoint-interval', type=int, default=1000, help='Save checkpoint every N directories')
@click.option('--resume-from', type=click.Path(), help='Resume from checkpoint file')
@click.argument('path', type=click.Path(exists=True), default='.')
def clean_empty(
    dry_run,
    delete,
    trash,
    pattern,
    older_than,
    exclude_pattern,
    config,
    no_config,
    yes,
    verbose,
    quiet,
    log_file,
    json_log,
    threads,
    cpu_priority,
    io_priority,
    checkpoint_interval,
    resume_from,
    path
):
    """Find and remove empty files and folders safely."""
    
    # Set up logging first
    if quiet:
        verbose = False
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
        # Apply defaults
        for key, value in DEFAULT_CONFIG.items():
            if not hasattr(config_obj, key):
                setattr(config_obj, key, value)
    else:
        config_path = config
        config_obj = Config(config_path)
    
    # Override config with command line options
    if pattern:
        config_obj.config_data["exclude_patterns"] = list(pattern)
    
    if older_than is not None:
        config_obj.config_data["min_age_days"] = older_than
    
    if exclude_pattern:
        config_obj.config_data["exclude_dirs"] = list(exclude_pattern)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Determine action mode
    if dry_run is None and not delete and not trash:
        # No action specified, use default from config or dry_run
        action = config_obj.default_action
    elif dry_run:
        action = "dry_run"
    elif delete:
        action = "delete"
    elif trash:
        action = "trash"
    else:
        action = "dry_run"  # fallback
    
    dry_run_mode = action == "dry_run"
    trash_mode = action == "trash"
    
    # Normalize path
    target_path = normalize_path(path)
    
    # Log startup info
    logger.info(f"Cortex Cleaner starting...")
    logger.info(f"Target path: {target_path}")
    logger.info(f"Action mode: {action}")
    if dry_run_mode:
        logger.info("DRY RUN MODE - No files will be deleted")
    
    # Set up performance management
    try:
        from cortex_unified.performance.resource_throttler import ResourceThrottler
        from cortex_unified.performance.scan_manager import ScanManager
        
        throttler = ResourceThrottler()
        throttler.set_process_priority(cpu_priority)
        
        # Set up scan manager for checkpoints
        scan_manager = ScanManager(config_obj)
        
        # Resume from checkpoint if specified
        if resume_from:
            logger.info(f"Resuming from checkpoint: {resume_from}")
            scan_state = scan_manager.load_checkpoint(resume_from)
            if scan_state:
                logger.info("Successfully loaded checkpoint")
            else:
                logger.warning("Failed to load checkpoint, starting fresh scan")
    except ImportError:
        logger.warning("Performance features not available, using basic scanning")
    
    # Create scanner and scan
    scanner = Scanner(config_obj, str(target_path))
    logger.info("Scanning for empty files and directories...")
    
    try:
        empty_files, empty_dirs = scanner.scan(threads)
        stats = scanner.get_stats()
        
        logger.info(f"Found {stats['empty_files_count']} empty files and {stats['empty_dirs_count']} empty directories")
        
        if stats['total_empty_count'] == 0:
            logger.info("No empty files or directories found")
            return
        
        # Show what would be deleted in dry run mode or when verbose
        if dry_run_mode or verbose:
            if empty_files:
                logger.info("Empty files:")
                for f in empty_files:
                    logger.info(f"  {f}")
            
            if empty_dirs:
                logger.info("Empty directories:")
                for d in empty_dirs:
                    logger.info(f"  {d}")
        
        # If not in dry run mode, confirm before deleting
        if not dry_run_mode:
            if not yes:
                click.confirm(f"Delete {stats['total_empty_count']} empty items? This action cannot be undone.", abort=True)
            else:
                logger.info("Skipping confirmation due to --yes flag")
        
        # Create deleter and delete
        deleter = Deleter(dry_run_mode, trash_mode)
        result = deleter.delete(empty_files, empty_dirs)
        
        # Generate manifest
        try:
            manifest_path = deleter.generate_manifest()
            logger.info(f"Manifest saved to: {manifest_path}")
        except Exception as e:
            logger.error(f"Failed to generate manifest: {e}")
        
        # Log results
        if dry_run_mode:
            logger.info(f"Would delete {result['files_deleted']} files and {result['dirs_deleted']} directories")
        else:
            logger.info(f"Deleted {result['files_deleted']} files and {result['dirs_deleted']} directories")
        
        if result['errors']:
            logger.error(f"Encountered {len(result['errors'])} errors:")
            for error in result['errors']:
                logger.error(f"  {error['type']} {error['path']}: {error['error']}")
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--min-size', type=int, default=100, help='Minimum file size in MB (default: 100)')
@click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)')
@click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)')
@click.option('--export', type=click.Path(), help='Export results to JSON file')
@click.argument('path', type=click.Path(exists=True), default='.')
def find_large_files(
    min_size,
    pattern,
    exclude_pattern,
    config,
    no_config,
    verbose,
    log_file,
    json_log,
    threads,
    export,
    path
):
    """Find large files."""
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
    else:
        config_path = config
        config_obj = Config(config_path)
    
    # Override config with command line options
    if pattern:
        config_obj.config_data["exclude_patterns"] = list(pattern)
    
    if exclude_pattern:
        config_obj.config_data["exclude_dirs"] = list(exclude_pattern)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Normalize path
    target_path = normalize_path(path)
    
    # Log startup info
    logger.info(f"Finding large files...")
    logger.info(f"Target path: {target_path}")
    logger.info(f"Minimum size: {min_size} MB")
    
    try:
        # Create finder and find large files
        finder = LargeFileFinder(config_obj, str(target_path))
        large_files = finder.find_large_files(min_size_mb=min_size, threads=threads)
        stats = finder.get_stats()
        
        logger.info(f"Found {stats['large_files_found']} large files")
        logger.info(f"Total size: {stats['total_size_human']}")
        
        if large_files:
            logger.info("Large files:")
            for filepath, size in large_files:
                size_human = finder._format_bytes(size)
                logger.info(f"  {size_human:>10}  {filepath}")
        
        # Export results if requested
        if export:
            import json
            export_data = {
                "large_files": [{"path": str(path), "size_bytes": size} for path, size in large_files],
                "stats": stats
            }
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Results exported to: {export}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--strategy', type=click.Choice(['keep_newest', 'keep_oldest', 'keep_largest', 'keep_smallest']), 
              default='keep_newest', help='Strategy for auto-selecting duplicates')
@click.option('--hash-algorithm', type=click.Choice(['md5', 'sha1', 'sha256']), default='md5', 
              help='Hash algorithm for duplicate detection')
@click.option('--preview', is_flag=True, default=False, help='Preview duplicates without deleting')
@click.option('--delete', is_flag=True, default=False, help='Delete duplicates (requires confirmation)')
@click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)')
@click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)')
@click.option('--export', type=click.Path(), help='Export results to JSON file')
@click.argument('path', type=click.Path(exists=True), default='.')
def find_duplicates(
    strategy,
    hash_algorithm,
    preview,
    delete,
    pattern,
    exclude_pattern,
    config,
    no_config,
    yes,
    verbose,
    log_file,
    json_log,
    threads,
    export,
    path
):
    """Find duplicate files."""
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
    else:
        config_path = config
        config_obj = Config(config_path)
    
    # Override config with command line options
    if pattern:
        config_obj.config_data["exclude_patterns"] = list(pattern)
    
    if exclude_pattern:
        config_obj.config_data["exclude_dirs"] = list(exclude_pattern)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Normalize path
    target_path = normalize_path(path)
    
    # Log startup info
    logger.info(f"Finding duplicate files...")
    logger.info(f"Target path: {target_path}")
    logger.info(f"Hash algorithm: {hash_algorithm}")
    logger.info(f"Selection strategy: {strategy}")
    
    try:
        # Create finder and find duplicates
        finder = DuplicateFinder(config_obj, str(target_path))
        finder.hash_algorithm = hash_algorithm
        duplicates = finder.find_duplicates(threads=threads)
        stats = finder.get_stats()
        
        logger.info(f"Found {stats['duplicate_groups']} groups of duplicates")
        logger.info(f"Total duplicates: {stats['total_duplicates']}")
        logger.info(f"Potential space savings: {finder._format_bytes(stats['bytes_saved_if_deleted'])}")
        
        if duplicates:
            logger.info("Duplicate groups:")
            for hash_val, paths in duplicates.items():
                logger.info(f"  Hash: {hash_val}")
                for path in paths:
                    logger.info(f"    {path}")
                logger.info("")
        
        # Export results if requested
        if export:
            import json
            export_data = {
                "duplicates": {hash_val: [str(path) for path in paths] for hash_val, paths in duplicates.items()},
                "stats": stats
            }
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Results exported to: {export}")
        
        # Handle deletion if requested
        if delete and duplicates:
            files_to_delete = finder.auto_select_duplicates(strategy)
            
            if not files_to_delete:
                logger.info("No files selected for deletion")
                return
            
            logger.info(f"Selected {len(files_to_delete)} files for deletion")
            
            if not yes:
                click.confirm(f"Delete {len(files_to_delete)} duplicate files? This action cannot be undone.", abort=True)
            else:
                logger.info("Skipping confirmation due to --yes flag")
            
            # Delete files
            deleter = Deleter(dry_run=False, use_trash=True)
            result = deleter.delete(files_to_delete, [])
            
            logger.info(f"Deleted {result['files_deleted']} files")
            if result['errors']:
                logger.error(f"Encountered {len(result['errors'])} errors:")
                for error in result['errors']:
                    logger.error(f"  {error['type']} {error['path']}: {error['error']}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

# TODO: Create TempCleaner module and re-enable clean-temp command
# The clean_temp command has been temporarily disabled because TempCleaner module doesn't exist yet

@main.command()
@click.option('--analyze', is_flag=True, default=False, help='Analyze disk usage')
@click.option('--export-json', type=click.Path(), help='Export analysis to JSON file')
@click.option('--export-treemap', type=click.Path(), help='Export TreeMap visualization (HTML/PNG/SVG) - hierarchical disk usage map')
@click.option('--export-sunburst', type=click.Path(), help='Export Sunburst visualization (HTML/PNG/SVG) - circular directory tree')
@click.option('--export-dashboard', type=click.Path(), help='Export Interactive Dashboard (HTML/PNG/SVG) - comprehensive analysis view')
@click.option('--max-depth', type=int, default=3, help='Maximum directory depth for visualization analysis (deeper = more detail)')
@click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)')
@click.option('--cpu-priority', type=click.Choice(['low', 'normal', 'high']), default='normal', help='CPU priority for scanning process')
@click.option('--io-priority', type=click.Choice(['low', 'normal', 'high']), default='low', help='I/O priority for disk operations')
@click.option('--memory-limit', type=int, default=0, help='Memory limit in MB (0 = no limit, prevents system overload)')
@click.option('--checkpoint-interval', type=int, default=1000, help='Save checkpoint every N directories (for resumable scans)')
@click.option('--resume-from', type=click.Path(), help='Resume from checkpoint file (continue interrupted scan)')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.argument('path', type=click.Path(exists=True), default='.')
def analyze_disk(
    analyze,
    export_json,
    export_treemap,
    export_sunburst,
    export_dashboard,
    max_depth,
    threads,
    cpu_priority,
    io_priority,
    memory_limit,
    checkpoint_interval,
    resume_from,
    config,
    no_config,
    verbose,
    log_file,
    json_log,
    path
):
    """Analyze disk usage with interactive visualizations.
    
    This command provides comprehensive disk usage analysis with support for
    interactive visualizations including TreeMaps, Sunburst charts, and dashboards.
    
    Examples:
      cortex-cleaner analyze-disk                              # Basic analysis
      cortex-cleaner analyze-disk --export-treemap tree.html  # Interactive TreeMap
      cortex-cleaner analyze-disk --export-sunburst sun.html  # Sunburst chart
      cortex-cleaner analyze-disk --max-depth 5               # Deeper analysis
      cortex-cleaner analyze-disk --resume-from checkpoint.json  # Resume scan
    
    Performance: Use --cpu-priority and --memory-limit to control resource usage.
    """
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
    else:
        config_path = config
        config_obj = Config(config_path)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Normalize path
    target_path = normalize_path(path)
    
    # Log startup info
    logger.info(f"Analyzing disk usage...")
    logger.info(f"Target path: {target_path}")
    
    try:
        # Set up performance management
        from cortex_unified.performance.resource_throttler import ResourceThrottler
        from cortex_unified.performance.scan_manager import ScanManager
        
        throttler = ResourceThrottler()
        throttler.set_process_priority(cpu_priority)
        
        # Set up scan manager for checkpoints
        scan_manager = ScanManager(config_obj)
        
        # Resume from checkpoint if specified
        if resume_from:
            logger.info(f"Resuming from checkpoint: {resume_from}")
            scan_state = scan_manager.load_checkpoint(resume_from)
            if scan_state:
                logger.info("Successfully loaded checkpoint")
            else:
                logger.warning("Failed to load checkpoint, starting fresh scan")
        
        # Create analyzer and analyze disk
        analyzer = DiskAnalyzer(config_obj, str(target_path))
        
        # Configure performance settings
        if threads > 0:
            analyzer.set_thread_count(threads)
        if memory_limit > 0:
            analyzer.set_memory_limit(memory_limit * 1024 * 1024)  # Convert MB to bytes
        
        # Analyze disk usage with performance monitoring
        disk_usage = analyzer.analyze_disk_usage()
        
        # Monitor system load during analysis
        system_load = throttler.get_system_load()
        logger.info(f"System load: CPU {system_load.cpu_percent:.1f}%, Memory {system_load.memory_percent:.1f}%")
        
        # Format disk usage for display
        if "total_bytes" in disk_usage:
            disk_usage["total_human"] = analyzer._format_bytes(disk_usage["total_bytes"])
            disk_usage["used_human"] = analyzer._format_bytes(disk_usage["used_bytes"])
            disk_usage["free_human"] = analyzer._format_bytes(disk_usage["free_bytes"])
        
        logger.info(f"Disk usage: {disk_usage['used_human']} used of {disk_usage['total_human']} ({disk_usage['used_percent']:.1f}%)")
        
        # Analyze directory tree for visualizations
        if export_treemap or export_sunburst or export_dashboard:
            analyzer.analyze_directory_tree(max_depth=max_depth)
        
        # Analyze file types
        file_types = analyzer.analyze_file_types()
        logger.info("File type breakdown:")
        for ext, info in list(file_types.items())[:10]:  # Show top 10
            size_human = analyzer._format_bytes(info['size_bytes'])
            logger.info(f"  {ext:>10}: {info['count']:>5} files, {size_human}")
        
        # Find largest directories
        largest_dirs = analyzer.find_largest_directories(limit=10)
        logger.info("Largest directories:")
        for path, size in largest_dirs:
            size_human = analyzer._format_bytes(size)
            logger.info(f"  {size_human:>10}  {path}")
        
        # Export results if requested
        if export_json:
            if analyzer.export_to_json(export_json):
                logger.info(f"Analysis exported to: {export_json}")
            else:
                logger.error(f"Failed to export analysis to: {export_json}")
        
        # Export visualizations if requested
        if export_treemap:
            try:
                from cortex_unified.visualization import TreeMapGenerator
                generator = TreeMapGenerator(analyzer)
                
                # Determine format from file extension
                ext = Path(export_treemap).suffix.lower()
                if ext == '.html':
                    content = generator.export_as_html()
                    with open(export_treemap, 'w', encoding='utf-8') as f:
                        f.write(content)
                elif ext in ['.png', '.svg', '.jpg', '.jpeg']:
                    img_data = generator.export_as_image(ext[1:])  # Remove the dot
                    with open(export_treemap, 'wb') as f:
                        f.write(img_data)
                else:
                    # Default to HTML
                    content = generator.export_as_html()
                    with open(export_treemap, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                logger.info(f"TreeMap visualization exported to: {export_treemap}")
            except Exception as e:
                logger.error(f"Failed to export TreeMap: {e}")
        
        if export_sunburst:
            try:
                from cortex_unified.visualization import SunburstGenerator
                generator = SunburstGenerator(analyzer)
                
                # Determine format from file extension
                ext = Path(export_sunburst).suffix.lower()
                if ext == '.html':
                    content = generator.export_as_html()
                    with open(export_sunburst, 'w', encoding='utf-8') as f:
                        f.write(content)
                elif ext in ['.png', '.svg', '.jpg', '.jpeg']:
                    img_data = generator.export_as_image(ext[1:])  # Remove the dot
                    with open(export_sunburst, 'wb') as f:
                        f.write(img_data)
                else:
                    # Default to HTML
                    content = generator.export_as_html()
                    with open(export_sunburst, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                logger.info(f"Sunburst visualization exported to: {export_sunburst}")
            except Exception as e:
                logger.error(f"Failed to export Sunburst: {e}")
        
        if export_dashboard:
            try:
                from cortex_unified.visualization import InteractiveDashboard
                dashboard = InteractiveDashboard(analyzer)
                
                # Determine format from file extension
                ext = Path(export_dashboard).suffix.lower()
                format_type = ext[1:] if ext else 'html'
                
                success = dashboard.export_visualization(format_type, export_dashboard)
                if success:
                    logger.info(f"Interactive dashboard exported to: {export_dashboard}")
                else:
                    logger.error(f"Failed to export dashboard to: {export_dashboard}")
            except Exception as e:
                logger.error(f"Failed to export dashboard: {e}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
def list_startup_items():
    """List system startup items."""
    
    # Set up logging
    logger = setup_logging()
    
    try:
        # Create manager and list startup items
        manager = StartupManager()
        items = manager.list_startup_items()
        stats = manager.get_stats()
        
        logger.info(f"Found {stats['total_startup_items']} startup items")
        logger.info(f"Enabled: {stats['enabled_items']}, Disabled: {stats['disabled_items']}")
        
        if items:
            logger.info("Startup items:")
            for item in items:
                status = "ENABLED" if item.get("enabled", True) else "DISABLED"
                logger.info(f"  [{status}] {item['name']} - {item['location']}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--export', type=click.Path(), help='Export results to JSON file')
def analyze_processes(export):
    """Analyze system processes."""
    
    # Set up logging
    logger = setup_logging()
    
    try:
        # Create analyzer and analyze processes
        analyzer = ProcessAnalyzer()
        processes = analyzer.list_processes()
        services = analyzer.list_services()
        stats = analyzer.get_stats()
        
        logger.info(f"System analysis:")
        logger.info(f"  Processes: {stats['total_processes']}")
        logger.info(f"  Services: {stats['total_services']}")
        
        # Export results if requested
        if export:
            import json
            export_data = {
                "processes": processes,
                "services": services,
                "stats": stats
            }
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Results exported to: {export}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--dry-run', is_flag=True, default=True, help='Show what would be cleaned without actually cleaning (default)')
@click.option('--clean', is_flag=True, default=False, help='Actually clean Docker resources')
@click.option('--images', is_flag=True, default=False, help='Clean unused Docker images (dangling and untagged)')
@click.option('--containers', is_flag=True, default=False, help='Clean stopped containers and their associated data')
@click.option('--volumes', is_flag=True, default=False, help='Clean unused volumes (not attached to any container)')
@click.option('--networks', is_flag=True, default=False, help='Clean unused networks (not used by any container)')
@click.option('--all', 'clean_all', is_flag=True, default=False, help='Clean all Docker resources (images, containers, volumes, networks)')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts (use with caution)')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output with detailed resource information')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.option('--export', type=click.Path(), help='Export results to JSON file for analysis')
def docker_cleanup(
    dry_run,
    clean,
    images,
    containers,
    volumes,
    networks,
    clean_all,
    config,
    no_config,
    yes,
    verbose,
    log_file,
    json_log,
    export
):
    """Clean Docker resources (images, containers, volumes, networks).
    
    This command helps free up disk space by removing unused Docker resources.
    By default, it performs a dry run to show what would be cleaned.
    
    Examples:
      cortex-cleaner docker-cleanup                    # Show what would be cleaned
      cortex-cleaner docker-cleanup --clean --all     # Clean all Docker resources
      cortex-cleaner docker-cleanup --images --clean  # Clean only unused images
      cortex-cleaner docker-cleanup --export report.json  # Export findings to JSON
    
    Safety: Creates backup manifests for potential restoration.
    """
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
    else:
        config_path = config
        config_obj = Config(config_path)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Determine what to clean
    if clean_all:
        images = containers = volumes = networks = True
    elif not any([images, containers, volumes, networks]):
        # Default to all if nothing specified
        images = containers = volumes = networks = True
    
    # Determine action mode
    if clean:
        dry_run = False
    
    # Log startup info
    logger.info(f"Docker cleanup starting...")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'CLEANUP'}")
    
    try:
        # Create Docker cleaner
        docker_cleaner = DockerCleaner(config_obj)
        
        # Check if Docker is available
        if not docker_cleaner.is_docker_available():
            logger.error("Docker is not available. Please ensure Docker is installed and running.")
            sys.exit(1)
        
        resources_to_clean = []
        
        # Scan for resources
        if images:
            logger.info("Scanning for unused Docker images...")
            unused_images = docker_cleaner.scan_unused_images()
            resources_to_clean.extend(unused_images)
            logger.info(f"Found {len(unused_images)} unused images")
        
        if containers:
            logger.info("Scanning for stopped containers...")
            stopped_containers = docker_cleaner.scan_stopped_containers()
            resources_to_clean.extend(stopped_containers)
            logger.info(f"Found {len(stopped_containers)} stopped containers")
        
        if volumes:
            logger.info("Scanning for unused volumes...")
            unused_volumes = docker_cleaner.scan_unused_volumes()
            resources_to_clean.extend(unused_volumes)
            logger.info(f"Found {len(unused_volumes)} unused volumes")
        
        if networks:
            logger.info("Scanning for unused networks...")
            unused_networks = docker_cleaner.scan_unused_networks()
            resources_to_clean.extend(unused_networks)
            logger.info(f"Found {len(unused_networks)} unused networks")
        
        if not resources_to_clean:
            logger.info("No Docker resources found for cleanup")
            return
        
        # Show what would be cleaned
        logger.info(f"Found {len(resources_to_clean)} Docker resources for cleanup")
        if verbose or dry_run:
            for resource in resources_to_clean:
                logger.info(f"  {resource}")
        
        # Export results if requested
        if export:
            import json
            export_data = {
                "resources": [str(resource) for resource in resources_to_clean],
                "stats": docker_cleaner.get_stats()
            }
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Results exported to: {export}")
        
        # Cleanup if not dry run
        if not dry_run:
            if not yes:
                click.confirm(f"Clean {len(resources_to_clean)} Docker resources? This action cannot be undone.", abort=True)
            else:
                logger.info("Skipping confirmation due to --yes flag")
            
            result = docker_cleaner.cleanup_resources(resources_to_clean, dry_run=False)
            
            logger.info(f"Cleaned {result['resources_cleaned']} Docker resources")
            logger.info(f"Space freed: {result['space_freed_human']}")
            
            if result['errors']:
                logger.error(f"Encountered {len(result['errors'])} errors:")
                for error in result['errors']:
                    logger.error(f"  {error}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--pip', is_flag=True, default=False, help='Clean pip cache (Python package manager)')
@click.option('--npm', is_flag=True, default=False, help='Clean npm cache (Node.js package manager)')
@click.option('--yarn', is_flag=True, default=False, help='Clean yarn cache (Alternative Node.js package manager)')
@click.option('--conda', is_flag=True, default=False, help='Clean conda cache (Python/R package manager)')
@click.option('--system', is_flag=True, default=False, help='Clean system package manager cache (apt, dnf, pacman, brew, chocolatey)')
@click.option('--all', 'clean_all', is_flag=True, default=False, help='Clean all detected package managers automatically')
@click.option('--orphaned', is_flag=True, default=False, help='Find and clean orphaned packages (packages no longer needed)')
@click.option('--keep-recent-days', type=int, default=7, help='Keep cache files newer than N days (preserves recent downloads)')
@click.option('--dry-run', is_flag=True, default=True, help='Show what would be cleaned without actually cleaning (default)')
@click.option('--clean', is_flag=True, default=False, help='Actually clean package manager resources')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts (use with caution)')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output with detailed package information')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.option('--export', type=click.Path(), help='Export results to JSON file for analysis')
def package_cleanup(
    pip,
    npm,
    yarn,
    conda,
    system,
    clean_all,
    orphaned,
    keep_recent_days,
    dry_run,
    clean,
    config,
    no_config,
    yes,
    verbose,
    log_file,
    json_log,
    export
):
    """Clean package manager caches and orphaned packages.
    
    This command helps free up disk space by cleaning package manager caches
    and removing orphaned packages that are no longer needed.
    
    Examples:
      cortex-cleaner package-cleanup                    # Show what would be cleaned
      cortex-cleaner package-cleanup --clean --all     # Clean all package managers
      cortex-cleaner package-cleanup --pip --clean     # Clean only pip cache
      cortex-cleaner package-cleanup --orphaned        # Find orphaned packages
    
    Safety: Creates backups of package lists before making changes.
    """
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
    else:
        config_path = config
        config_obj = Config(config_path)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Determine what to clean
    if clean_all:
        pip = npm = yarn = conda = system = True
    elif not any([pip, npm, yarn, conda, system]):
        # Default to detecting all available package managers
        clean_all = True
    
    # Determine action mode
    if clean:
        dry_run = False
    
    # Log startup info
    logger.info(f"Package manager cleanup starting...")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'CLEANUP'}")
    
    try:
        # Import package manager cleaner
        from cortex_unified.analyzers.package_manager_cleaner import PackageManagerCleaner
        
        # Create package manager cleaner
        pm_cleaner = PackageManagerCleaner(config_obj)
        
        # Detect available package managers
        available_managers = pm_cleaner.detect_package_managers()
        logger.info(f"Detected package managers: {[pm.name for pm in available_managers]}")
        
        cleanup_results = []
        
        # Clean specific package managers
        for manager in available_managers:
            should_clean = (
                clean_all or
                (pip and manager.name == 'pip') or
                (npm and manager.name == 'npm') or
                (yarn and manager.name == 'yarn') or
                (conda and manager.name == 'conda') or
                (system and manager.name in ['apt', 'dnf', 'pacman', 'brew', 'chocolatey'])
            )
            
            if should_clean:
                logger.info(f"Cleaning {manager.name} cache...")
                
                if manager.name == 'pip':
                    result = pm_cleaner.clean_pip_cache(keep_recent_days=keep_recent_days)
                elif manager.name == 'npm':
                    result = pm_cleaner.clean_npm_cache(verify_integrity=True)
                else:
                    result = pm_cleaner.clean_system_packages(manager.name)
                
                cleanup_results.append(result)
                logger.info(f"  {manager.name}: {result['files_cleaned']} files, {result['space_freed_human']} freed")
        
        # Handle orphaned packages
        if orphaned:
            logger.info("Scanning for orphaned packages...")
            for manager in available_managers:
                orphaned_packages = pm_cleaner.find_orphaned_packages(manager.name)
                if orphaned_packages:
                    logger.info(f"Found {len(orphaned_packages)} orphaned packages in {manager.name}")
                    if verbose:
                        for package in orphaned_packages:
                            logger.info(f"  {package}")
        
        # Export results if requested
        if export:
            import json
            export_data = {
                "cleanup_results": cleanup_results,
                "available_managers": [pm.name for pm in available_managers],
                "stats": pm_cleaner.get_stats()
            }
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Results exported to: {export}")
        
        # Summary
        total_files = sum(result['files_cleaned'] for result in cleanup_results)
        total_space = sum(result['space_freed_bytes'] for result in cleanup_results)
        
        if dry_run:
            logger.info(f"Would clean {total_files} files, freeing {pm_cleaner._format_bytes(total_space)}")
        else:
            logger.info(f"Cleaned {total_files} files, freed {pm_cleaner._format_bytes(total_space)}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--confidence-threshold', type=float, default=0.7, help='Minimum confidence score for leftover detection (0.0-1.0, higher = more certain)')
@click.option('--scan-registry', is_flag=True, default=False, help='Include Windows registry analysis for orphaned entries (Windows only)')
@click.option('--ml-patterns', is_flag=True, default=True, help='Use machine learning patterns for intelligent leftover detection')
@click.option('--dry-run', is_flag=True, default=True, help='Show what would be cleaned without actually cleaning (default)')
@click.option('--clean', is_flag=True, default=False, help='Actually clean detected leftovers (use with caution)')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts (use with extreme caution)')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output with confidence scores and reasoning')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.option('--export', type=click.Path(), help='Export results to JSON file with confidence scores')
@click.argument('path', type=click.Path(exists=True), default='.')
def heuristics_scan(
    confidence_threshold,
    scan_registry,
    ml_patterns,
    dry_run,
    clean,
    config,
    no_config,
    yes,
    verbose,
    log_file,
    json_log,
    export,
    path
):
    """Scan for application leftovers using advanced heuristics.
    
    This command uses machine learning and pattern recognition to detect
    leftover files and folders from uninstalled applications.
    
    Examples:
      cortex-cleaner heuristics-scan                           # Scan current directory
      cortex-cleaner heuristics-scan --confidence-threshold 0.9  # High confidence only
      cortex-cleaner heuristics-scan --scan-registry          # Include registry analysis (Windows)
      cortex-cleaner heuristics-scan /path/to/scan            # Scan specific directory
    
    Warning: This feature uses heuristics and may flag legitimate files.
    Always review results carefully before cleaning.
    """
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
    else:
        config_path = config
        config_obj = Config(config_path)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Determine action mode
    if clean:
        dry_run = False
    
    # Normalize path
    target_path = normalize_path(path)
    
    # Log startup info
    logger.info(f"Heuristics scan starting...")
    logger.info(f"Target path: {target_path}")
    logger.info(f"Confidence threshold: {confidence_threshold}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'CLEANUP'}")
    
    try:
        # Import leftover detector
        from cortex_unified.analyzers.leftover_detector import LeftoverDetector
        
        # Create leftover detector
        detector = LeftoverDetector(config_obj)
        
        # Scan for orphaned folders
        logger.info("Scanning for orphaned application folders...")
        orphaned_folders = detector.scan_orphaned_folders([
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            os.path.expanduser("~\\AppData\\Local"),
            os.path.expanduser("~\\AppData\\Roaming")
        ])
        
        # Scan for installer files
        logger.info("Scanning for installer files...")
        installer_files = detector.detect_installer_files()
        
        # Registry analysis (Windows only)
        registry_orphans = []
        if scan_registry and os.name == 'nt':
            logger.info("Analyzing Windows registry...")
            registry_orphans = detector.analyze_registry_orphans()
        
        # Combine all detected items
        all_items = orphaned_folders + installer_files + registry_orphans
        
        # Apply ML patterns if enabled
        if ml_patterns and all_items:
            logger.info("Applying machine learning patterns...")
            all_items = detector.apply_ml_patterns(all_items)
        
        # Filter by confidence threshold
        high_confidence_items = [
            item for item in all_items 
            if detector.calculate_confidence_score(item) >= confidence_threshold
        ]
        
        logger.info(f"Found {len(all_items)} potential leftovers")
        logger.info(f"High confidence items (>= {confidence_threshold}): {len(high_confidence_items)}")
        
        # Show results
        if high_confidence_items:
            logger.info("High confidence leftovers:")
            for item in high_confidence_items:
                confidence = detector.calculate_confidence_score(item)
                logger.info(f"  [{confidence:.2f}] {item}")
        
        # Export results if requested
        if export:
            import json
            export_data = {
                "all_items": [str(item) for item in all_items],
                "high_confidence_items": [str(item) for item in high_confidence_items],
                "confidence_threshold": confidence_threshold,
                "stats": detector.get_stats()
            }
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2)
            logger.info(f"Results exported to: {export}")
        
        # Cleanup if not dry run
        if not dry_run and high_confidence_items:
            if not yes:
                click.confirm(f"Clean {len(high_confidence_items)} high-confidence leftovers? This action cannot be undone.", abort=True)
            else:
                logger.info("Skipping confirmation due to --yes flag")
            
            # Generate cleanup recommendations
            recommendations = detector.generate_cleanup_recommendations()
            
            # Execute cleanup
            deleter = Deleter(dry_run=False, use_trash=True)
            files_to_delete = [item for item in high_confidence_items if hasattr(item, 'path')]
            result = deleter.delete(files_to_delete, [])
            
            logger.info(f"Cleaned {result['files_deleted']} leftover items")
            if result['errors']:
                logger.error(f"Encountered {len(result['errors'])} errors:")
                for error in result['errors']:
                    logger.error(f"  {error}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--shred', is_flag=True, default=False, help='Shred files securely')
@click.option('--passes', type=int, default=3, help='Number of overwrite passes for shredding')
@click.option('--verify', is_flag=True, default=True, help='Verify deletion after shredding')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.argument('files', type=click.Path(exists=True), nargs=-1)
def secure_delete(
    shred,
    passes,
    verify,
    yes,
    verbose,
    log_file,
    json_log,
    files
):
    """Securely delete files."""
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    if not files:
        logger.error("No files specified for deletion")
        sys.exit(1)
    
    # Log startup info
    logger.info(f"Securely deleting {len(files)} files...")
    logger.info(f"Overwrite passes: {passes}")
    
    try:
        # Create shredder and shred files
        shredder = FileShredder()
        shredder.set_passes(passes)
        shredder.verify_deletion(verify)
        
        if shred:
            if not yes:
                click.confirm(f"Securely delete {len(files)} files with {passes} passes? This action cannot be undone.", abort=True)
            else:
                logger.info("Skipping confirmation due to --yes flag")
            
            # Shred files
            results = shredder.shred_files([Path(f) for f in files], passes)
            
            logger.info(f"Shredded {results['shredded']} files")
            if results['errors']:
                logger.error(f"Encountered {results['errors']} errors")
        else:
            logger.info("Preview mode - files would be shredded with the above settings")
            logger.info("Use --shred flag to actually delete files")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--restore', type=click.Path(exists=True), help='Restore from manifest file')
@click.option('--dry-run', is_flag=True, default=True, help='Preview restore without actually restoring')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
def restore(
    restore,
    dry_run,
    yes,
    verbose,
    log_file,
    json_log
):
    """Restore files from backup."""
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    try:
        # Create restore manager
        manager = RestoreManager()
        
        if restore:
            # Restore from specific manifest
            logger.info(f"Restoring from manifest: {restore}")
            
            if not dry_run:
                if not yes:
                    click.confirm(f"Restore files from {restore}? This action cannot be undone.", abort=True)
                else:
                    logger.info("Skipping confirmation due to --yes flag")
            
            result = manager.restore_from_manifest(restore, dry_run)
            
            if dry_run:
                logger.info(f"Would restore {result['restored']} files")
            else:
                logger.info(f"Restored {result['restored']} files")
            
            if result['errors']:
                logger.error(f"Encountered {result['errors']} errors:")
                for error in result['error_details']:
                    logger.error(f"  {error}")
        else:
            # List available manifests
            manifests = manager.list_manifests()
            
            logger.info(f"Found {len(manifests)} backup manifests:")
            for manifest in manifests:
                logger.info(f"  {manifest.get('timestamp', 'Unknown')} - {manifest.get('backup_name', 'Unnamed')}")
                logger.info(f"    Files: {manifest.get('files_backed_up', 0)}")
                logger.info(f"    Path: {manifest.get('file_path', 'Unknown')}")
                logger.info("")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--type', type=click.Choice(['text', 'html', 'json', 'csv']), default='text', help='Report type')
@click.option('--export', type=click.Path(), help='Export report to file')
@click.option('--name', type=str, help='Report name')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
def generate_report(
    type,
    export,
    name,
    verbose,
    log_file,
    json_log
):
    """Generate system reports."""
    
    # Set up logging
    logger = setup_logging(verbose, log_file, json_log)
    
    try:
        # Create reports generator
        generator = ReportsGenerator()
        
        # Sample data for report
        data = {
            "system_info": {
                "platform": sys.platform,
                "python_version": sys.version,
                "timestamp": str(Path().stat().st_mtime) if Path().exists() else "Unknown"
            },
            "summary": {
                "reports_generated": len(generator.list_reports()) + 1,
                "report_type": type
            }
        }
        
        # Generate report
        if type == "text":
            report_file = generator.generate_text_report(data, name)
        elif type == "html":
            report_file = generator.generate_html_report(data, name)
        elif type == "json":
            report_file = generator.generate_json_report(data, name)
        elif type == "csv":
            # CSV needs tabular data
            csv_data = {
                "headers": ["Metric", "Value"],
                "rows": [
                    ["Platform", sys.platform],
                    ["Python Version", sys.version.split()[0]],
                    ["Reports Generated", str(len(generator.list_reports()) + 1)]
                ]
            }
            report_file = generator.generate_csv_report(csv_data, name)
        
        logger.info(f"Generated {type} report: {report_file}")
        
        # Export to specific file if requested
        if export:
            import shutil
            shutil.copy2(report_file, export)
            logger.info(f"Report exported to: {export}")
    
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.group()
def checkpoint():
    """Manage scan checkpoints."""
    pass

@checkpoint.command(name='list')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
def list_checkpoints(config, verbose):
    """List all available checkpoints."""
    from cortex_unified.performance import ScanManager
    
    logger = setup_logging(verbose)
    
    try:
        scan_manager = ScanManager()
        checkpoints = scan_manager.list_checkpoints()
        
        if not checkpoints:
            logger.info("No checkpoints found")
            return
        
        logger.info(f"Found {len(checkpoints)} checkpoints:")
        for checkpoint in checkpoints:
            logger.info(f"  ID: {checkpoint.id}")
            logger.info(f"    Created: {checkpoint.timestamp}")
            logger.info(f"    Path: {checkpoint.current_path}")
            logger.info(f"    Progress: {checkpoint.progress_percentage:.1f}%")
            logger.info(f"    Items: {checkpoint.processed_items}/{checkpoint.total_items}")
            logger.info("")
    
    except Exception as e:
        logger.error(f"Failed to list checkpoints: {e}")
        sys.exit(1)

@checkpoint.command()
@click.argument('checkpoint_id')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
def delete(checkpoint_id, verbose):
    """Delete a specific checkpoint."""
    from cortex_unified.performance import ScanManager
    
    logger = setup_logging(verbose)
    
    try:
        scan_manager = ScanManager()
        
        if scan_manager.delete_checkpoint(checkpoint_id):
            logger.info(f"Checkpoint {checkpoint_id} deleted successfully")
        else:
            logger.error(f"Checkpoint {checkpoint_id} not found")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Failed to delete checkpoint: {e}")
        sys.exit(1)

@checkpoint.command()
@click.option('--max-age', type=int, default=7, help='Maximum age in days (default: 7)')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
def cleanup(max_age, verbose):
    """Clean up old checkpoints."""
    from cortex_unified.performance import ScanManager
    
    logger = setup_logging(verbose)
    
    try:
        scan_manager = ScanManager()
        deleted_count = scan_manager.cleanup_old_checkpoints(max_age)
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old checkpoints")
        else:
            logger.info("No old checkpoints to clean up")
    
    except Exception as e:
        logger.error(f"Failed to cleanup checkpoints: {e}")
        sys.exit(1)

@main.command()
@click.option('--checkpoint-id', help='Resume from specific checkpoint')
@click.option('--enable-checkpoints', is_flag=True, default=False, help='Enable checkpoint functionality')
@click.option('--enable-throttling', is_flag=True, default=False, help='Enable resource throttling')
@click.option('--cpu-limit', type=float, default=0.8, help='CPU usage limit (0.0-1.0, default: 0.8)')
@click.option('--memory-limit', type=float, default=0.85, help='Memory usage limit (0.0-1.0, default: 0.85)')
@click.option('--dry-run', is_flag=True, default=None, help='Show what would be deleted without actually deleting (default)')
@click.option('--delete', is_flag=True, default=False, help='Permanently delete empty files and folders')
@click.option('--trash', is_flag=True, default=False, help='Move empty files and folders to trash/recycle bin')
@click.option('--pattern', multiple=True, help='Only consider files matching this glob pattern (can be used multiple times)')
@click.option('--older-than', type=int, default=None, help='Only consider files older than N days')
@click.option('--exclude-pattern', multiple=True, help='Exclude files/directories matching this pattern (can be used multiple times)')
@click.option('--config', type=click.Path(exists=False), help='Path to configuration file')
@click.option('--no-config', is_flag=True, default=False, help='Don\'t load any configuration file')
@click.option('--yes', is_flag=True, default=False, help='Skip confirmation prompts')
@click.option('--verbose', is_flag=True, default=False, help='Enable verbose output')
@click.option('--quiet', is_flag=True, default=False, help='Suppress all output except errors')
@click.option('--log-file', type=click.Path(), help='Write logs to file')
@click.option('--json-log', is_flag=True, default=False, help='Output logs in JSON format')
@click.option('--threads', type=int, default=0, help='Number of threads to use for scanning (default: CPU count)')
@click.argument('path', type=click.Path(exists=True), default='.')
def scan_enhanced(
    checkpoint_id,
    enable_checkpoints,
    enable_throttling,
    cpu_limit,
    memory_limit,
    dry_run,
    delete,
    trash,
    pattern,
    older_than,
    exclude_pattern,
    config,
    no_config,
    yes,
    verbose,
    quiet,
    log_file,
    json_log,
    threads,
    path
):
    """Enhanced scan with checkpoint and performance features."""
    
    # Set up logging first
    if quiet:
        verbose = False
    logger = setup_logging(verbose, log_file, json_log)
    
    # Load configuration
    if no_config:
        config_obj = Config()  # Empty config
        # Apply defaults
        for key, value in DEFAULT_CONFIG.items():
            if not hasattr(config_obj, key):
                setattr(config_obj, key, value)
    else:
        config_path = config
        config_obj = Config(config_path)
    
    # Override config with command line options
    if pattern:
        config_obj.config_data["exclude_patterns"] = list(pattern)
    
    if older_than is not None:
        config_obj.config_data["min_age_days"] = older_than
    
    if exclude_pattern:
        config_obj.config_data["exclude_dirs"] = list(exclude_pattern)
    
    if log_file:
        config_obj.config_data["log_file"] = log_file
    
    if json_log:
        config_obj.config_data["json_logging"] = json_log
    
    # Determine action mode
    if dry_run is None and not delete and not trash:
        # No action specified, use default from config or dry_run
        action = config_obj.default_action
    elif dry_run:
        action = "dry_run"
    elif delete:
        action = "delete"
    elif trash:
        action = "trash"
    else:
        action = "dry_run"  # fallback
    
    dry_run_mode = action == "dry_run"
    trash_mode = action == "trash"
    
    # Normalize path
    target_path = normalize_path(path)
    
    # Log startup info
    logger.info(f"Cortex Cleaner Enhanced Scan starting...")
    logger.info(f"Target path: {target_path}")
    logger.info(f"Action mode: {action}")
    if enable_checkpoints:
        logger.info("Checkpoint functionality enabled")
    if enable_throttling:
        logger.info(f"Resource throttling enabled (CPU: {cpu_limit*100}%, Memory: {memory_limit*100}%)")
    if checkpoint_id:
        logger.info(f"Resuming from checkpoint: {checkpoint_id}")
    if dry_run_mode:
        logger.info("DRY RUN MODE - No files will be deleted")
    
    # Create enhanced scanner
    scanner = Scanner(
        config_obj, 
        str(target_path),
        enable_checkpoints=enable_checkpoints,
        enable_throttling=enable_throttling
    )
    
    # Configure resource throttling if enabled
    if enable_throttling and scanner._resource_throttler:
        scanner._resource_throttler.cpu_limit = cpu_limit * 100
        scanner._resource_throttler.memory_limit = memory_limit * 100
    
    logger.info("Scanning for empty files and directories...")
    
    try:
        # Perform enhanced scan
        empty_files, empty_dirs = scanner.scan(threads, checkpoint_id)
        stats = scanner.get_stats()
        
        logger.info(f"Found {stats['empty_files_count']} empty files and {stats['empty_dirs_count']} empty directories")
        
        # Show progress information if available
        if enable_checkpoints:
            progress = scanner.get_scan_progress()
            if progress:
                logger.info(f"Scan completed in {progress.elapsed_time:.2f} seconds")
                if progress.is_completed:
                    logger.info("Scan completed successfully")
        
        if stats['total_empty_count'] == 0:
            logger.info("No empty files or directories found")
            return
        
        # Show what would be deleted in dry run mode or when verbose
        if dry_run_mode or verbose:
            if empty_files:
                logger.info("Empty files:")
                for f in empty_files:
                    logger.info(f"  {f}")
            
            if empty_dirs:
                logger.info("Empty directories:")
                for d in empty_dirs:
                    logger.info(f"  {d}")
        
        # If not in dry run mode, confirm before deleting
        if not dry_run_mode:
            if not yes:
                click.confirm(f"Delete {stats['total_empty_count']} empty items? This action cannot be undone.", abort=True)
            else:
                logger.info("Skipping confirmation due to --yes flag")
        
        # Create deleter and delete
        deleter = Deleter(dry_run_mode, trash_mode)
        result = deleter.delete(empty_files, empty_dirs)
        
        # Generate manifest
        try:
            manifest_path = deleter.generate_manifest()
            logger.info(f"Manifest saved to: {manifest_path}")
        except Exception as e:
            logger.error(f"Failed to generate manifest: {e}")
        
        # Log results
        if dry_run_mode:
            logger.info(f"Would delete {result['files_deleted']} files and {result['dirs_deleted']} directories")
        else:
            logger.info(f"Deleted {result['files_deleted']} files and {result['dirs_deleted']} directories")
        
        if result['errors']:
            logger.error(f"Encountered {len(result['errors'])} errors:")
            for error in result['errors']:
                logger.error(f"  {error['type']} {error['path']}: {error['error']}")
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        
        # Create checkpoint if enabled
        if enable_checkpoints:
            try:
                checkpoint_id = scanner.create_checkpoint()
                if checkpoint_id:
                    logger.info(f"Checkpoint saved: {checkpoint_id}")
                    logger.info("Use --checkpoint-id to resume from this point")
            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")
        
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

@main.command()
@click.option('--scan-symlinks', is_flag=True, default=True, help='Scan for broken symlinks')
@click.option('--scan-shortcuts', is_flag=True, default=True, help='Scan for broken Windows shortcuts (.lnk files)')
@click.option('--scan-registry', is_flag=True, default=False, help='Scan for broken registry references (Windows only)')
@click.option('--repair', is_flag=True, default=False, help='Attempt to repair broken links')
@click.option('--backup', is_flag=True, default=True, help='Create backups before repair')
@click.option('--confidence-threshold', type=float, default=0.7, help='Minimum confidence score for repairs (0.0-1.0)')
@click.option('--export', type=click.Path(), help='Export results to JSON file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.argument('path', type=click.Path(exists=True), default='.')
def scan_broken_links(scan_symlinks, scan_shortcuts, scan_registry, repair, backup, 
                     confidence_threshold, export, verbose, path):
    """Scan for and optionally repair broken symlinks, shortcuts, and registry references."""
    
    # Set up logging
    logger = setup_logging(verbose=verbose)
    
    try:
        # Initialize detector
        config = Config()
        detector = BrokenLinkDetector(config)
        
        logger.info(f"Scanning for broken links in: {path}")
        
        all_broken_links = []
        
        # Scan for symlinks
        if scan_symlinks:
            logger.info("Scanning for broken symlinks...")
            symlinks = detector.scan_symlinks(path)
            all_broken_links.extend(symlinks)
            logger.info(f"Found {len(symlinks)} broken symlinks")
        
        # Scan for Windows shortcuts
        if scan_shortcuts and detector.is_windows:
            logger.info("Scanning for broken Windows shortcuts...")
            shortcuts = detector.scan_windows_shortcuts(path)
            all_broken_links.extend(shortcuts)
            logger.info(f"Found {len(shortcuts)} broken shortcuts")
        elif scan_shortcuts and not detector.is_windows:
            logger.info("Skipping shortcut scan (not on Windows)")
        
        # Scan for registry references
        if scan_registry and detector.is_windows and detector.has_winreg:
            logger.info("Scanning for broken registry references...")
            registry_refs = detector.scan_registry_references()
            all_broken_links.extend(registry_refs)
            logger.info(f"Found {len(registry_refs)} broken registry references")
        elif scan_registry and not detector.is_windows:
            logger.info("Skipping registry scan (not on Windows)")
        elif scan_registry and not detector.has_winreg:
            logger.warning("Registry scanning not available (winreg module not found)")
        
        # Display results
        if all_broken_links:
            categories = detector.categorize_broken_links(all_broken_links)
            
            click.echo(f"\nFound {len(all_broken_links)} broken links:")
            click.echo(f"  Symlinks: {len(categories['symlinks'])}")
            click.echo(f"  Shortcuts: {len(categories['shortcuts'])}")
            click.echo(f"  Registry refs: {len(categories['registry_refs'])}")
            click.echo(f"  Repairable: {len(categories['repairable'])}")
            click.echo(f"  High confidence: {len(categories['high_confidence'])}")
            
            # Show details
            for link in all_broken_links:
                status = "✓" if link.is_repairable else "✗"
                confidence = f"{link.confidence_score:.2f}"
                click.echo(f"{status} [{confidence}] {link.link_type}: {link.path} -> {link.target}")
            
            # Attempt repairs if requested
            if repair:
                repairable_links = [link for link in all_broken_links 
                                  if link.is_repairable and link.confidence_score >= confidence_threshold]
                
                if repairable_links:
                    click.echo(f"\nAttempting to repair {len(repairable_links)} links...")
                    
                    repaired_count = 0
                    for link in repairable_links:
                        try:
                            result = detector.attempt_repair(link)
                            if result.success:
                                repaired_count += 1
                                click.echo(f"✓ Repaired: {link.path} -> {result.new_target}")
                                if result.backup_created:
                                    click.echo(f"  Backup: {result.backup_path}")
                            else:
                                click.echo(f"✗ Failed to repair: {link.path} - {result.error_message}")
                        except Exception as e:
                            click.echo(f"✗ Error repairing {link.path}: {e}")
                    
                    click.echo(f"\nRepaired {repaired_count} out of {len(repairable_links)} links")
                else:
                    click.echo("\nNo links meet the confidence threshold for repair")
        else:
            click.echo("No broken links found!")
        
        # Export results if requested
        if export and all_broken_links:
            import json
            from datetime import datetime
            
            export_data = {
                'scan_date': datetime.now().isoformat(),
                'scan_path': str(path),
                'statistics': detector.get_scan_statistics(),
                'broken_links': []
            }
            
            for link in all_broken_links:
                link_data = {
                    'path': str(link.path),
                    'target': link.target,
                    'type': link.link_type,
                    'size': link.size,
                    'created': link.created.isoformat(),
                    'last_accessed': link.last_accessed.isoformat(),
                    'is_repairable': link.is_repairable,
                    'confidence_score': link.confidence_score,
                    'error_message': link.error_message
                }
                
                # Add type-specific fields
                if hasattr(link, 'is_absolute'):
                    link_data['is_absolute'] = link.is_absolute
                if hasattr(link, 'working_directory'):
                    link_data['working_directory'] = link.working_directory
                if hasattr(link, 'registry_key'):
                    link_data['registry_key'] = link.registry_key
                
                export_data['broken_links'].append(link_data)
            
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            click.echo(f"\nResults exported to: {export}")
        
        # Display statistics
        stats = detector.get_scan_statistics()
        click.echo(f"\nScan Statistics:")
        click.echo(f"  Items scanned: {stats['total_scanned']}")
        click.echo(f"  Errors encountered: {stats['errors']}")
        
    except Exception as e:
        logger.error(f"Error during broken link scan: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()