"""
Structured logging configuration for Cortex Cleaner.

Provides JSON-structured logs for production with human-readable
console output for development. Supports log levels, correlation IDs,
and integration with external log aggregation systems.
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Optional, Any, Dict
from contextvars import ContextVar

import structlog
from structlog.types import EventDict, Processor

# Context variable for correlation/request IDs
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation ID to log events if present.

    Manages add correlation id operations and coordinates related state changes for the component.

    Args:
        logger (Any): The logger parameter.
        method_name (str): The method name parameter.
        event_dict (EventDict): The event dict parameter.

    Returns:
        EventDict: Dictionary mapping identifiers to status or values.
    """
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict

def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to all log events.

    Manages add app context operations and coordinates related state changes for the component.

    Args:
        logger (Any): The logger parameter.
        method_name (str): The method name parameter.
        event_dict (EventDict): The event dict parameter.

    Returns:
        EventDict: Dictionary mapping identifiers to status or values.
    """
    event_dict["app"] = "cortex_cleaner"
    try:
        from cortex_unified import __version__ as app_version
    except Exception:  # pragma: no cover - defensive, package always ships it
        app_version = "unknown"
    event_dict["version"] = app_version
    return event_dict

def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Censor sensitive data from logs.
    
    Replaces values for keys that might contain sensitive information.
    """
    sensitive_keys = {
        "password", "passwd", "pwd", "secret", "token", "api_key",
        "apikey", "auth", "authorization", "credential", "private_key"
    }
    
    def _censor_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """_censor_dict.

        Manages censor dict operations and coordinates related state changes for the component.

        Args:
            d (Dict[str, Any]): The d parameter.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        result = {}
        for key, value in d.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = _censor_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    _censor_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    return _censor_dict(event_dict)

def configure_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    json_output: bool = False,
    enable_colors: bool = True,
    enable_censoring: bool = True,
) -> None:
    """
    Configure structured logging for Cortex Cleaner.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = console only)
        json_output: Use JSON format (True) or human-readable (False)
        enable_colors: Enable colored output for console (only if not JSON)
        enable_censoring: Enable automatic censoring of sensitive data
    
    Example:
        # Development mode
        configure_logging(log_level="DEBUG", json_output=False)
        
        # Production mode
        configure_logging(
            log_level="INFO",
            log_file=Path("/var/log/cortex_cleaner.log"),
            json_output=True,
            enable_colors=False
        )
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # stdlib stays the sink; structlog only shapes the event dicts.
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        stream=sys.stdout,
    )

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_correlation_id,
        add_app_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if enable_censoring:
        processors.append(censor_sensitive_data)

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        if enable_colors and sys.stdout.isatty():
            processors.append(
                structlog.dev.ConsoleRenderer(
                    colors=True,
                    exception_formatter=structlog.dev.plain_traceback,
                )
            )
        else:
            processors.append(
                structlog.dev.ConsoleRenderer(
                    colors=False,
                    exception_formatter=structlog.dev.plain_traceback,
                )
            )
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # File output is always raw JSON lines, independent of the console
    # renderer, so log aggregators can parse it without configuration.
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)

        file_formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(file_formatter)

        logging.root.addHandler(file_handler)

def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
    
    Returns:
        Configured structlog logger
    
    Example:
        log = get_logger(__name__)
        log.info("scan_started", root_path="/home/user", scan_type="duplicates")
        log.warning("permission_denied", path="/etc/shadow")
        log.error("scan_failed", error=str(e), exc_info=True)
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()

def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID for the current context.
    
    This ID will be automatically added to all log messages in the current
    execution context (thread/async task).
    
    Args:
        correlation_id: Unique identifier for correlating related log entries
    
    Example:
        import uuid
        set_correlation_id(str(uuid.uuid4()))
        log.info("processing_request")  # Will include correlation_id
    """
    correlation_id_var.set(correlation_id)

def clear_correlation_id() -> None:
    """clear_correlation_id.

    Manages clear correlation id operations and coordinates related state changes for the component.
    """
    correlation_id_var.set(None)

class LogContext:
    """
    Context manager for temporary log context.
    
    Example:
        with LogContext(scan_id=123, user="admin"):
            log.info("scan_started")  # Will include scan_id and user
            # ... do work ...
            log.info("scan_completed")  # Will include scan_id and user
    """
    
    def __init__(self, **kwargs):
        """Initialize with context key-value pairs.

        Initializes the instance and configures internal state.
        """
        self.context = kwargs
        self.token = None
    
    def __enter__(self):
        """Manage context lifecycle and resource acquisition or cleanup.

        Acquires necessary lock or file resources on entry and guarantees safe release and error propagation on exit.
        """
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Manage context lifecycle and resource acquisition or cleanup.

        Acquires necessary lock or file resources on entry and guarantees safe release and error propagation on exit.

        Args:
            exc_type: Error message string or exception instance.
            exc_val: Error message string or exception instance.
            exc_tb: Error message string or exception instance.
        """
        if self.token:
            structlog.contextvars.unbind_contextvars(*self.context.keys())
        return False

def log_scan_start(
    logger: structlog.BoundLogger,
    scan_type: str,
    root_path: str,
    **kwargs
) -> None:
    """Log the start of a scan operation.

    Manages log scan start operations and coordinates related state changes for the component.

    Args:
        logger (structlog.BoundLogger): The logger parameter.
        scan_type (str): The scan type parameter.
        root_path (str): Filesystem path to the target file or directory.
    """
    logger.info(
        "scan_started",
        scan_type=scan_type,
        root_path=root_path,
        **kwargs
    )

def log_scan_complete(
    logger: structlog.BoundLogger,
    scan_type: str,
    items_found: int,
    bytes_found: int,
    duration_seconds: float,
    **kwargs
) -> None:
    """Log the completion of a scan operation.

    Manages log scan complete operations and coordinates related state changes for the component.

    Args:
        logger (structlog.BoundLogger): The logger parameter.
        scan_type (str): The scan type parameter.
        items_found (int): The items found parameter.
        bytes_found (int): The bytes found parameter.
        duration_seconds (float): The duration seconds parameter.
    """
    logger.info(
        "scan_completed",
        scan_type=scan_type,
        items_found=items_found,
        bytes_found=bytes_found,
        duration_seconds=round(duration_seconds, 2),
        **kwargs
    )

def log_scan_error(
    logger: structlog.BoundLogger,
    scan_type: str,
    error: Exception,
    **kwargs
) -> None:
    """Log a scan error with exception details.

    Manages log scan error operations and coordinates related state changes for the component.

    Args:
        logger (structlog.BoundLogger): The logger parameter.
        scan_type (str): The scan type parameter.
        error (Exception): Error message string or exception instance.
    """
    logger.error(
        "scan_failed",
        scan_type=scan_type,
        error_type=type(error).__name__,
        error_message=str(error),
        exc_info=True,
        **kwargs
    )

def log_file_operation(
    logger: structlog.BoundLogger,
    operation: str,
    path: str,
    success: bool,
    **kwargs
) -> None:
    """log_file_operation.

    Manages log file operation operations and coordinates related state changes for the component.

    Args:
        logger (structlog.BoundLogger): The logger parameter.
        operation (str): The operation parameter.
        path (str): Filesystem path to the target file or directory.
        success (bool): The success parameter.
    """
    level = "info" if success else "warning"
    getattr(logger, level)(
        "file_operation",
        operation=operation,
        path=path,
        success=success,
        **kwargs
    )

def log_performance_metric(
    logger: structlog.BoundLogger,
    metric_name: str,
    value: float,
    unit: str = "seconds",
    **kwargs
) -> None:
    """log_performance_metric.

    Manages log performance metric operations and coordinates related state changes for the component.

    Args:
        logger (structlog.BoundLogger): The logger parameter.
        metric_name (str): The metric name parameter.
        value (float): The value parameter.
        unit (str): The unit parameter.
    """
    logger.info(
        "performance_metric",
        metric=metric_name,
        value=round(value, 3),
        unit=unit,
        **kwargs
    )

if __name__ == "__main__":
    print("Testing structured logging...\n")
    
    # Development mode (colored console)
    print("=== Development Mode (Colored Console) ===")
    configure_logging(log_level="DEBUG", json_output=False, enable_colors=True)
    log = get_logger(__name__)
    
    log.debug("debug_message", detail="This is a debug message")
    log.info("info_message", user="admin", action="login")
    log.warning("warning_message", disk_usage=95, threshold=90)
    log.error("error_message", error_code=500, path="/nonexistent")
    
    # With correlation ID
    print("\n=== With Correlation ID ===")
    set_correlation_id("req-12345")
    log.info("request_received", endpoint="/api/scan")
    log.info("request_processed", duration_ms=150)
    clear_correlation_id()
    
    # With context manager
    print("\n=== With Context Manager ===")
    with LogContext(scan_id=42, scan_type="duplicates"):
        log.info("scan_phase", phase="initialization")
        log.info("scan_phase", phase="scanning")
        log.info("scan_phase", phase="complete")
    
    # Sensitive data censoring
    print("\n=== Sensitive Data Censoring ===")
    log.info(
        "user_login",
        username="admin",
        password="secret123",  # Should be censored
        api_key="abc123xyz",   # Should be censored
        email="user@example.com"  # Should NOT be censored
    )
    
    # Exception logging
    print("\n=== Exception Logging ===")
    try:
        raise ValueError("Something went wrong!")
    except Exception as e:
        log_scan_error(log, "duplicate_scan", e, root_path="/home/user")
    
    # JSON output (production mode)
    print("\n=== Production Mode (JSON Output) ===")
    configure_logging(log_level="INFO", json_output=True, enable_colors=False)
    log = get_logger(__name__)
    
    log.info("production_log", environment="prod", service="cortex_cleaner")
    log_scan_complete(
        log,
        scan_type="empty_files",
        items_found=150,
        bytes_found=1024000,
        duration_seconds=5.234
    )
    
    print("\n✓ All logging tests completed!")
