"""Utility functions for Deep Cleaner."""

import os
import sys
import logging
from pathlib import Path
from typing import List, Set, Tuple
from datetime import datetime


def get_system_excludes() -> Set[str]:
    """Get platform-specific system directories to exclude by default."""
    if sys.platform.startswith("win"):
        return {
            "System Volume Information",
            "$RECYCLE.BIN",
            "Windows",
            "Program Files",
            "Program Files (x86)",
        }
    else:  # POSIX systems (Linux, macOS)
        return {
            "proc",
            "sys",
            "dev",
            "run",
            "tmp",
            "var/run",
            "var/tmp",
        }


def is_system_directory(path: Path) -> bool:
    """Check if a path is a system directory that should be excluded."""
    system_excludes = get_system_excludes()
    return path.name in system_excludes


def setup_logging(verbose: bool = False, log_file: str = None, json_logging: bool = False, 
                 component: str = None, log_level: str = None) -> logging.Logger:
    """Set up comprehensive logging for the application with enhanced features.
    
    Args:
        verbose: Enable verbose logging
        log_file: Path to log file
        json_logging: Use JSON format for structured logging
        component: Specific component name for targeted logging
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger_name = f"deep_cleaner.{component}" if component else "deep_cleaner"
    logger = logging.getLogger(logger_name)
    
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level = logging.DEBUG if verbose else logging.INFO
    
    logger.setLevel(level)
    
    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create enhanced formatters
    if json_logging:
        import json
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "component": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                # Add extra fields if present
                if hasattr(record, 'operation'):
                    log_entry["operation"] = record.operation
                if hasattr(record, 'duration'):
                    log_entry["duration_ms"] = record.duration
                if hasattr(record, 'file_count'):
                    log_entry["file_count"] = record.file_count
                if hasattr(record, 'bytes_processed'):
                    log_entry["bytes_processed"] = record.bytes_processed
                
                return json.dumps(log_entry)
        
        formatter = JSONFormatter()
    else:
        # Enhanced text formatter with more context
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s'
        )
    
    # Console handler with color support
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Add color support for console output (if not JSON)
    if not json_logging and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
        try:
            import colorlog
            color_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_formatter)
        except ImportError:
            # colorlog not available, use standard formatter
            pass
    
    logger.addHandler(console_handler)
    
    # File handler with rotation support
    if log_file:
        try:
            from logging.handlers import RotatingFileHandler
            
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create rotating file handler (10MB max, 5 backups)
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)  # Always debug level for files
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    # Add performance monitoring handler
    if verbose:
        class PerformanceFilter(logging.Filter):
            def filter(self, record):
                # Add performance context to log records
                if not hasattr(record, 'start_time'):
                    record.start_time = datetime.now()
                return True
        
        logger.addFilter(PerformanceFilter())
    
    return logger


def get_component_logger(component: str, verbose: bool = False, 
                        log_file: str = None, json_logging: bool = False) -> logging.Logger:
    """Get a logger for a specific component with consistent configuration.
    
    Args:
        component: Component name (e.g., 'docker', 'visualization', 'heuristics')
        verbose: Enable verbose logging
        log_file: Path to log file
        json_logging: Use JSON format
    
    Returns:
        Component-specific logger
    """
    return setup_logging(verbose, log_file, json_logging, component)


def log_operation_start(logger: logging.Logger, operation: str, **kwargs) -> dict:
    """Log the start of an operation with context.
    
    Args:
        logger: Logger instance
        operation: Operation name
        **kwargs: Additional context
    
    Returns:
        Context dictionary for operation tracking
    """
    context = {
        'operation': operation,
        'start_time': datetime.now(),
        **kwargs
    }
    
    logger.info(f"Starting {operation}", extra=context)
    return context


def log_operation_end(logger: logging.Logger, context: dict, success: bool = True, 
                     error: Exception = None, **kwargs) -> None:
    """Log the end of an operation with results.
    
    Args:
        logger: Logger instance
        context: Context from log_operation_start
        success: Whether operation succeeded
        error: Exception if operation failed
        **kwargs: Additional results
    """
    end_time = datetime.now()
    duration = (end_time - context['start_time']).total_seconds() * 1000  # milliseconds
    
    result_context = {
        **context,
        'duration': duration,
        'success': success,
        **kwargs
    }
    
    if success:
        logger.info(f"Completed {context['operation']} in {duration:.1f}ms", extra=result_context)
    else:
        logger.error(f"Failed {context['operation']} after {duration:.1f}ms: {error}", 
                    extra=result_context, exc_info=error)


def log_performance_metrics(logger: logging.Logger, operation: str, metrics: dict) -> None:
    """Log performance metrics for an operation.
    
    Args:
        logger: Logger instance
        operation: Operation name
        metrics: Performance metrics dictionary
    """
    context = {
        'operation': operation,
        'metrics': True,
        **metrics
    }
    
    logger.info(f"Performance metrics for {operation}: {metrics}", extra=context)


def generate_manifest_filename() -> str:
    """Generate a timestamped filename for the manifest file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"deep_cleaner_manifest_{timestamp}.json"


def normalize_path(path: str) -> Path:
    """Normalize a path string to a Path object."""
    return Path(os.path.expanduser(path)).resolve()


def get_file_age_days(filepath: Path) -> int:
    """Get the age of a file in days."""
    try:
        mtime = filepath.stat().st_mtime
        mtime_dt = datetime.fromtimestamp(mtime)
        now = datetime.now()
        return (now - mtime_dt).days
    except (OSError, ValueError):
        # If we can't get the file age, return 0 (assume it's new)
        return 0


# Enhanced Error Handling and Resource Management

class DeepCleanerError(Exception):
    """Base exception for Deep Cleaner operations."""
    
    def __init__(self, message: str, operation: str = None, component: str = None, 
                 error_code: str = None, details: dict = None):
        super().__init__(message)
        self.operation = operation
        self.component = component
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()


class DockerError(DeepCleanerError):
    """Docker-specific errors."""
    pass


class VisualizationError(DeepCleanerError):
    """Visualization-specific errors."""
    pass


class HeuristicsError(DeepCleanerError):
    """Heuristics and ML-specific errors."""
    pass


class PackageManagerError(DeepCleanerError):
    """Package manager-specific errors."""
    pass


class PerformanceError(DeepCleanerError):
    """Performance and resource-specific errors."""
    pass


class AccessibilityError(DeepCleanerError):
    """Accessibility-specific errors."""
    pass


def handle_error(logger: logging.Logger, error: Exception, operation: str = None, 
                component: str = None, reraise: bool = True) -> None:
    """Centralized error handling with comprehensive logging.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation being performed
        component: Component where error occurred
        reraise: Whether to reraise the exception
    """
    error_context = {
        'operation': operation,
        'component': component,
        'error_type': type(error).__name__,
        'error_message': str(error)
    }
    
    # Add specific error details for known error types
    if isinstance(error, DeepCleanerError):
        error_context.update({
            'error_code': error.error_code,
            'details': error.details
        })
    
    # Log the error with full context
    logger.error(f"Error in {operation or 'unknown operation'}: {error}", 
                extra=error_context, exc_info=True)
    
    if reraise:
        raise


def safe_execute(func, logger: logging.Logger, operation: str = None, 
                default_return=None, **kwargs):
    """Safely execute a function with comprehensive error handling.
    
    Args:
        func: Function to execute
        logger: Logger instance
        operation: Operation description
        default_return: Value to return on error
        **kwargs: Arguments to pass to function
    
    Returns:
        Function result or default_return on error
    """
    try:
        context = log_operation_start(logger, operation or func.__name__)
        result = func(**kwargs)
        log_operation_end(logger, context, success=True)
        return result
    
    except Exception as e:
        handle_error(logger, e, operation, reraise=False)
        return default_return


class ResourceManager:
    """Context manager for resource cleanup and monitoring."""
    
    def __init__(self, logger: logging.Logger, operation: str = None):
        self.logger = logger
        self.operation = operation
        self.resources = []
        self.start_time = None
        self.context = {}
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.context = log_operation_start(self.logger, self.operation or "resource_operation")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up resources
        for resource in reversed(self.resources):
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
                elif callable(resource):
                    resource()
            except Exception as e:
                self.logger.warning(f"Error cleaning up resource: {e}")
        
        # Log operation completion
        success = exc_type is None
        log_operation_end(self.logger, self.context, success, exc_val)
        
        return False  # Don't suppress exceptions
    
    def add_resource(self, resource):
        """Add a resource to be cleaned up."""
        self.resources.append(resource)
    
    def add_cleanup_function(self, func, *args, **kwargs):
        """Add a cleanup function to be called."""
        self.resources.append(lambda: func(*args, **kwargs))


def format_bytes(bytes_value: int) -> str:
    """Format bytes in human-readable format with enhanced precision."""
    if bytes_value == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(bytes_value)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    # Use appropriate precision based on size
    if size >= 100:
        precision = 0
    elif size >= 10:
        precision = 1
    else:
        precision = 2
    
    return f"{size:.{precision}f} {units[unit_index]}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def validate_path(path: str, must_exist: bool = True, must_be_dir: bool = False, 
                 must_be_file: bool = False) -> Path:
    """Validate and normalize a path with comprehensive checks.
    
    Args:
        path: Path string to validate
        must_exist: Whether path must exist
        must_be_dir: Whether path must be a directory
        must_be_file: Whether path must be a file
    
    Returns:
        Validated Path object
    
    Raises:
        ValueError: If validation fails
    """
    try:
        normalized_path = normalize_path(path)
        
        if must_exist and not normalized_path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        if must_be_dir and normalized_path.exists() and not normalized_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        if must_be_file and normalized_path.exists() and not normalized_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        return normalized_path
    
    except Exception as e:
        raise ValueError(f"Invalid path '{path}': {e}")


def ensure_directory(path: Path, create: bool = True) -> Path:
    """Ensure a directory exists, optionally creating it.
    
    Args:
        path: Directory path
        create: Whether to create if it doesn't exist
    
    Returns:
        Directory path
    
    Raises:
        OSError: If directory cannot be created or accessed
    """
    try:
        if not path.exists() and create:
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            raise OSError(f"Directory does not exist: {path}")
        elif not path.is_dir():
            raise OSError(f"Path is not a directory: {path}")
        
        return path
    
    except Exception as e:
        raise OSError(f"Cannot ensure directory '{path}': {e}")


def get_system_info() -> dict:
    """Get comprehensive system information for diagnostics."""
    import platform
    import psutil
    
    try:
        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
            },
            'resources': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': {
                    str(path): {
                        'total': psutil.disk_usage(str(path)).total,
                        'free': psutil.disk_usage(str(path)).free,
                        'used': psutil.disk_usage(str(path)).used
                    }
                    for path in [Path.cwd()]  # Add more paths as needed
                }
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'error': f"Could not gather system info: {e}"}


def create_error_report(error: Exception, context: dict = None) -> dict:
    """Create a comprehensive error report for debugging.
    
    Args:
        error: Exception that occurred
        context: Additional context information
    
    Returns:
        Error report dictionary
    """
    import traceback
    
    report = {
        'error': {
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc()
        },
        'context': context or {},
        'system_info': get_system_info(),
        'timestamp': datetime.now().isoformat()
    }
    
    # Add specific error details for known error types
    if isinstance(error, DeepCleanerError):
        report['error'].update({
            'operation': error.operation,
            'component': error.component,
            'error_code': error.error_code,
            'details': error.details
        })
    
    return report