"""Shared utilities: logging setup, formatting, path helpers, error types.

Everything here is dependency-light and safe to import from any layer of
the application -- analyzers, UI and CLI all pull from this module rather
than re-implementing their own variants.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Set
from datetime import datetime

def get_system_excludes() -> Set[str]:
    """System directories that must never be scanned or cleaned.

    Returned as bare directory names so scanners can match them cheaply
    at any depth without resolving each path.
    """
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
    """True if *path* names one of the platform's protected directories.

    Manages is system directory operations and coordinates related state changes for the component.

    Args:
        path (Path): Filesystem path to the target file or directory.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
    system_excludes = get_system_excludes()
    return path.name in system_excludes

def setup_logging(verbose: bool = False, log_file: str = None, json_logging: bool = False, 
                 component: str = None, log_level: str = None) -> logging.Logger:
    """Configure and return an application logger.

    Handlers are rebuilt on every call (existing ones are cleared first),
    so calling this twice with different settings replaces the previous
    configuration instead of duplicating output lines.

    Args:
        verbose: Enable verbose logging
        log_file: Path to log file
        json_logging: Use JSON format for structured logging
        component: Specific component name for targeted logging
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger_name = f"{component}" if component else "cortex_cleaner"
    logger = logging.getLogger(logger_name)

    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    else:
        level = logging.DEBUG if verbose else logging.INFO

    logger.setLevel(level)

    # Replacing handlers prevents duplicate lines when this runs more than
    # once per process (e.g. CLI reconfiguration after config load).
    logger.handlers.clear()

    if json_logging:
        import json
        class JSONFormatter(logging.Formatter):
            """JSONFormatter.

            Converts raw numeric values into formatted, localized, and human-readable string representations.
            """
            def format(self, record):
                """format.

                Converts raw numeric values into formatted, localized, and human-readable string representations.

                Args:
                    record: The record parameter.
                """
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "component": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                # Optional structured fields; emitters attach these via
                # the logging ``extra`` mapping.
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
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s'
        )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Colors only on an interactive TTY and only for text output; colorlog
    # is optional and its absence must not break logging.
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
            pass

    logger.addHandler(console_handler)

    # Rotating file log: DEBUG always, regardless of console level, so a
    # support bundle contains the full story even when the console is quiet.
    if log_file:
        try:
            from logging.handlers import RotatingFileHandler

            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        except Exception as e:
            # File logging is an enhancement; console logging keeps working.
            logger.warning(f"Could not set up file logging: {e}")

    if verbose:
        class PerformanceFilter(logging.Filter):
            """Performancefilter.

            Manages PerformanceFilter operations and coordinates related state changes for the component.
            """
            def filter(self, record):
                """Filter.

                Manages filter operations and coordinates related state changes for the component.

                Args:
                    record: The record parameter.
                """
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
    """Generate a timestamped filename for the manifest file.

    Manages generate manifest filename operations and coordinates related state changes for the component.

    Returns:
        str: Formatted string or path.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"cortex_cleaner_manifest_{timestamp}.json"

def normalize_path(path: str) -> Path:
    """Normalize a path string to a Path object.

    Manages normalize path operations and coordinates related state changes for the component.

    Args:
        path (str): Filesystem path to the target file or directory.

    Returns:
        Path: Result of the operation.
    """
    return Path(os.path.expanduser(path)).resolve()

def get_file_age_days(filepath: Path) -> int:
    """Get the age of a file in days.

    Manages get file age days operations and coordinates related state changes for the component.

    Args:
        filepath (Path): Filesystem path to the target file or directory.

    Returns:
        int: Result of the operation.
    """
    try:
        mtime = filepath.stat().st_mtime
        mtime_dt = datetime.fromtimestamp(mtime)
        now = datetime.now()
        return (now - mtime_dt).days
    except (OSError, ValueError):
        # If we can't get the file age, return 0 (assume it's new)
        return 0

class DeepCleanerError(Exception):
    """Base exception for Cortex Cleaner operations.

    Carries structured context (operation, component, error_code, details)
    so callers can branch on failure modes without parsing message text.
    """

    def __init__(self, message: str, operation: str = None, component: str = None, 
                 error_code: str = None, details: dict = None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            message (str): Informational or progress status message.
            operation (str): The operation parameter.
            component (str): The component parameter.
            error_code (str): Error message string or exception instance.
            details (dict): The details parameter.
        """
        super().__init__(message)
        self.operation = operation
        self.component = component
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()

class DockerError(DeepCleanerError):
    """Dockererror.

    Manages DockerError operations and coordinates related state changes for the component.
    """
    pass

class VisualizationError(DeepCleanerError):
    """Visualizationerror.

    Manages VisualizationError operations and coordinates related state changes for the component.
    """
    pass

class HeuristicsError(DeepCleanerError):
    """Heuristicserror.

    Manages HeuristicsError operations and coordinates related state changes for the component.
    """
    pass

class PackageManagerError(DeepCleanerError):
    """Packagemanagererror.

    Manages PackageManagerError operations and coordinates related state changes for the component.
    """
    pass

class PerformanceError(DeepCleanerError):
    """Performanceerror.

    Manages PerformanceError operations and coordinates related state changes for the component.
    """
    pass

class AccessibilityError(DeepCleanerError):
    """Accessibilityerror.

    Manages AccessibilityError operations and coordinates related state changes for the component.
    """
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

    if isinstance(error, DeepCleanerError):
        error_context.update({
            'error_code': error.error_code,
            'details': error.details
        })

    logger.error(f"Error in {operation or 'unknown operation'}: {error}", 
                extra=error_context, exc_info=True)
    
    if reraise:
        raise error

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
    """Resourcemanager.

    Manages ResourceManager operations and coordinates related state changes for the component.
    """
    
    def __init__(self, logger: logging.Logger, operation: str = None):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            logger (logging.Logger): The logger parameter.
            operation (str): The operation parameter.
        """
        self.logger = logger
        self.operation = operation
        self.resources = []
        self.start_time = None
        self.context = {}
    
    def __enter__(self):
        """Manage context lifecycle and resource acquisition or cleanup.

        Acquires necessary lock or file resources on entry and guarantees safe release and error propagation on exit.
        """
        self.start_time = datetime.now()
        self.context = log_operation_start(self.logger, self.operation or "resource_operation")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Release in reverse registration order, mirroring how nested
        # resources were acquired. Cleanup failures are logged, never raised.
        """Manage context lifecycle and resource acquisition or cleanup.

        Acquires necessary lock or file resources on entry and guarantees safe release and error propagation on exit.

        Args:
            exc_type: Error message string or exception instance.
            exc_val: Error message string or exception instance.
            exc_tb: Error message string or exception instance.
        """
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

        success = exc_type is None
        log_operation_end(self.logger, self.context, success, exc_val)

        return False  # never suppress the caller's exception
    
    def add_resource(self, resource):
        """Add a resource to be cleaned up.

        Manages add resource operations and coordinates related state changes for the component.

        Args:
            resource: The resource parameter.
        """
        self.resources.append(resource)
    
    def add_cleanup_function(self, func, *args, **kwargs):
        """add_cleanup_function.

        Manages add cleanup function operations and coordinates related state changes for the component.

        Args:
            func: The func parameter.
        """
        self.resources.append(lambda: func(*args, **kwargs))

def format_bytes(bytes_value: int) -> str:
    """Format a byte count for display.

    Precision shrinks as magnitude grows (100+ -> whole numbers) so table
    columns stay aligned without losing resolution on small values.
    """
    if bytes_value == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(bytes_value)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if size >= 100:
        precision = 0
    elif size >= 10:
        precision = 1
    else:
        precision = 2
    
    return f"{size:.{precision}f} {units[unit_index]}"

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        seconds (float): The seconds parameter.

    Returns:
        str: Formatted string or path.
    """
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
    """Get comprehensive system information for diagnostics.

    Manages get system info operations and coordinates related state changes for the component.

    Returns:
        dict: Dictionary mapping identifiers to status or values.
    """
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

    if isinstance(error, DeepCleanerError):
        report['error'].update({
            'operation': error.operation,
            'component': error.component,
            'error_code': error.error_code,
            'details': error.details
        })
    
    return report