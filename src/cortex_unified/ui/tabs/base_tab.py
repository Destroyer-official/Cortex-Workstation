"""Base tab class for Cortex Cleaner GUI tabs with safety manager integration."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union
import logging
from pathlib import Path

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QThread, Signal, QObject

from cortex_unified.core.config import Config
from cortex_unified.translations.translator import get_translator
from cortex_unified.ui.safety import SafetyManager, Operation, OperationType, ValidationResult, OperationResult


class BaseTab(QWidget):
    """Base class for all GUI tabs with safety manager integration and internationalization support."""

    # Signals for operation requests and status updates
    operation_requested = Signal(Operation)
    status_changed = Signal(str)
    operation_completed = Signal(OperationResult)
    validation_failed = Signal(str, ValidationResult)

    def __init__(self, config: Config, logger: logging.Logger, safety_manager: SafetyManager):
        """Initialize base tab with safety manager integration.

        Args:
            config: Configuration instance
            logger: Logger instance
            safety_manager: Safety manager for secure operations
        """
        super().__init__()
        self.config = config
        self.logger = logger
        self.safety_manager = safety_manager
        self.translator = get_translator()

        # Worker thread management
        self.worker_threads: List[QThread] = []

        # Tab state
        self._is_initialized = False
        self._current_operation: Optional[Operation] = None

        self._initialize_tab()

    def __getattr__(self, name):
        """Proxy missing logic methods to the main window."""
        if name.startswith('_') or name == '_in_getattr':
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        if getattr(self, '_in_getattr', False):
            raise AttributeError(name)
            
        self._in_getattr = True
        try:
            top_window = self.window()
            if not hasattr(top_window, name):
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
                
            def lazy_call(*args, **kwargs):
                """Defer the proxied call to the main window attribute, logging any failure."""
                try:
                    return getattr(top_window, name)(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Error in lazy proxy {name}: {e}")
            return lazy_call
        finally:
            self._in_getattr = False

    def set_status(self, text: str):
        """Update the main window's status bar text safely.
        
        This avoids the __getattr__ proxy issue where status_bar
        resolves to a callable wrapper instead of the QLabel.
        """
        try:
            top_window = self.window()
            if hasattr(top_window, 'status_bar') and hasattr(top_window.status_bar, 'setText'):
                top_window.status_bar.setText(text)
        except Exception:
            pass


    def _initialize_tab(self):
        """Initialize the tab with proper setup sequence."""
        try:
            self.setup_ui()
            self.setup_connections()
            self.setup_tooltips()
            self.update_translations()
            self._is_initialized = True
            self.logger.debug(f"Initialized tab: {self.__class__.__name__}")
        except Exception as e:
            self.logger.error(
                f"Failed to initialize tab {self.__class__.__name__}: {e}")
            raise

    @abstractmethod
    def setup_ui(self):
        """Set up the user interface. Must be implemented by subclasses."""
        pass

    def setup_connections(self):
        """Set up signal connections. Can be overridden by subclasses."""
        # Connect operation signals to safety manager
        self.operation_requested.connect(self._handle_operation_request)

    def setup_tooltips(self):
        """Set up tooltips. Can be overridden by subclasses."""
        pass

    def update_translations(self):
        """Update UI text for internationalization. Can be overridden by subclasses."""
        pass

    def tr(self, key: str, **kwargs) -> str:
        """Translate text key with optional parameters.

        Args:
            key: Translation key
            **kwargs: Optional parameters for string formatting

        Returns:
            Translated text
        """
        return self.translator.translate(key, **kwargs)

    def request_operation(self, operation_type: OperationType, paths: List[Path],
                          description: str = "", **parameters) -> Operation:
        """Request an operation through the safety layer.

        Args:
            operation_type: Type of operation to perform
            paths: List of file/directory paths
            description: Human-readable description
            **parameters: Additional operation parameters

        Returns:
            Created Operation instance
        """
        try:
            operation = self.safety_manager.create_operation(
                operation_type=operation_type,
                paths=paths,
                description=description,
                **parameters
            )

            # Store current operation
            self._current_operation = operation

            self.operation_requested.emit(operation)

            return operation

        except Exception as e:
            self.logger.error(f"Failed to create operation: {e}")
            self.status_changed.emit(
                self.tr("error.operation_creation_failed", error=str(e)))
            raise

    def can_delete(self, path: Union[str, Path]) -> tuple[bool, str]:
        """Check if a path can be safely deleted using the safety manager.

        Args:
            path: Target file or directory path to check.

        Returns:
            tuple[bool, str]: (is_allowed, denial_reason). If allowed, reason is empty.
        """
        if self.safety_manager and hasattr(self.safety_manager, "can_delete"):
            return self.safety_manager.can_delete(path)
        return True, ""

    def _handle_operation_request(self, operation: Operation):
        """Handle operation request with validation and execution.

        Args:
            operation: Operation to handle
        """
        try:
            self.logger.info(f"Handling operation request: {operation.id}")

            # Validate operation
            validation_result = self.safety_manager.validate_operation(
                operation)

            if validation_result == ValidationResult.REJECTED:
                denials = operation.parameters.get("guard_denials", [])
                if denials:
                    error_msg = f"{self.tr('error.operation_rejected')}:\n" + "\n".join(denials[:5])
                else:
                    error_msg = self.tr("error.operation_rejected")
                self.validation_failed.emit(error_msg, validation_result)
                try:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "Safety Guard Denial", f"Operation blocked by Cortex PathGuard safety rules:\n\n{error_msg}")
                except Exception:
                    pass
                return

            if validation_result == ValidationResult.REQUIRES_CONFIRMATION:
                # Emit signal for UI to handle confirmation
                denials = operation.parameters.get("guard_denials", [])
                msg = self.tr("warning.operation_requires_confirmation")
                if denials:
                    msg += f"\nNote: {len(denials)} protected item(s) were excluded by PathGuard."
                self.validation_failed.emit(
                    msg,
                    validation_result
                )
                return

            if validation_result == ValidationResult.APPROVED:
                self._execute_operation(operation)

        except Exception as e:
            self.logger.error(f"Error handling operation request: {e}")
            self.status_changed.emit(
                self.tr("error.operation_handling_failed", error=str(e)))

    def _execute_operation(self, operation: Operation):
        """Execute validated operation.

        Args:
            operation: Operation to execute
        """
        try:
            self.status_changed.emit(self.tr("status.executing_operation",
                                             operation_type=operation.type.value))

            result = self.safety_manager.execute_safe_operation(operation)

            self.operation_completed.emit(result)

            if result.success:
                self.status_changed.emit(self.tr("status.operation_completed_successfully",
                                                 processed_items=result.processed_items))
            else:
                self.status_changed.emit(self.tr("status.operation_completed_with_errors",
                                                 error_count=len(result.errors)))

        except Exception as e:
            self.logger.error(f"Error executing operation: {e}")
            self.status_changed.emit(
                self.tr("error.operation_execution_failed", error=str(e)))

    def confirm_and_execute_operation(self, operation: Operation):
        """Confirm and execute an operation that requires user confirmation.

        Args:
            operation: Operation to confirm and execute
        """
        try:
            # Mark as user confirmed
            operation.user_confirmed = True

            # Re-validate and execute
            validation_result = self.safety_manager.validate_operation(
                operation)

            if validation_result == ValidationResult.APPROVED:
                self._execute_operation(operation)
            else:
                self.validation_failed.emit(
                    self.tr("error.operation_still_rejected_after_confirmation"),
                    validation_result
                )

        except Exception as e:
            self.logger.error(f"Error confirming operation: {e}")
            self.status_changed.emit(
                self.tr("error.operation_confirmation_failed", error=str(e)))

    def get_current_operation(self) -> Optional[Operation]:
        """Get the current operation being processed.

        Returns:
            Current Operation instance or None
        """
        return self._current_operation

    def cleanup(self):
        """Clean up resources when tab is closed."""
        try:
            self.logger.debug(f"Cleaning up tab: {self.__class__.__name__}")

            # Cancel current operation if any
            if self._current_operation:
                self.safety_manager.cancel_operation(
                    self._current_operation.id)
                self._current_operation = None

            # Stop all worker threads (never use QThread.terminate — it
            # can corrupt the process if the thread holds CRT/heap locks).
            stuck = []
            for thread in self.worker_threads:
                if thread and thread.isRunning():
                    try:
                        thread.quit()
                        thread.wait(3000)
                    except RuntimeError:
                        pass
                    if thread.isRunning():
                        stuck.append(thread)
                        thread.setParent(None)  # detach so destructor won't fire

            if stuck:
                self.logger.warning(
                    "%d worker thread(s) did not stop within grace period; "
                    "detaching to avoid process corruption", len(stuck))

            self.worker_threads.clear()

            self.logger.debug(
                f"Tab cleanup completed: {self.__class__.__name__}")

        except Exception as e:
            self.logger.error(f"Error during tab cleanup: {e}")

    def add_worker_thread(self, thread: QThread):
        """Add a worker thread to be managed.

        Args:
            thread: QThread instance to manage
        """
        self.worker_threads.append(thread)
        self.logger.debug(
            f"Added worker thread to tab: {self.__class__.__name__}")

    def remove_worker_thread(self, thread: QThread):
        """Remove a worker thread from management.

        Args:
            thread: QThread instance to remove
        """
        if thread in self.worker_threads:
            self.worker_threads.remove(thread)
            self.logger.debug(
                f"Removed worker thread from tab: {self.__class__.__name__}")

    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format.

        Args:
            bytes_value: Number of bytes

        Returns:
            Formatted string with appropriate unit
        """
        if bytes_value == 0:
            return "0 B"

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    def get_tab_info(self) -> Dict[str, Any]:
        """Get information about this tab.

        Returns:
            Dictionary with tab information
        """
        return {
            "class_name": self.__class__.__name__,
            "is_initialized": self._is_initialized,
            "worker_threads": len(self.worker_threads),
            "current_operation": self._current_operation.id if self._current_operation else None,
            "safety_manager_available": self.safety_manager is not None
        }

    def validate_paths(self, paths: List[Path]) -> List[Path]:
        """Validate paths using the safety manager.

        Args:
            paths: List of paths to validate

        Returns:
            List of safe paths
        """
        try:
            return self.safety_manager.path_validator.validate_operation_paths(paths)
        except Exception as e:
            self.logger.error(f"Error validating paths: {e}")
            return []

    def is_path_safe(self, path: Path) -> bool:
        """Check if a single path is safe for operations.

        Args:
            path: Path to check

        Returns:
            True if path is safe, False otherwise
        """
        try:
            return self.safety_manager.path_validator.is_safe_to_delete(path)
        except Exception as e:
            self.logger.error(f"Error checking path safety: {e}")
            return False

    def get_operation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent operation history.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of operation summaries
        """
        try:
            return self.safety_manager.get_operation_history(limit=limit)
        except Exception as e:
            self.logger.error(f"Error getting operation history: {e}")
            return []

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction
