"""Central safety manager that coordinates all safety components."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid
from datetime import datetime, timedelta
import os

from cortex_unified.core.config import Config
from cortex_unified.core.utils import DeepCleanerError
from .path_validator import PathValidator
from .manifest_system import ManifestSystem
from .process_manager import ProcessManager

class OperationType(Enum):
    """Operationtype.

    Manages OperationType operations and coordinates related state changes for the component.
    """
    DELETE = "delete"
    MOVE = "move"
    CLEAN = "clean"
    ANALYZE = "analyze"
    RESTORE = "restore"

class ValidationResult(Enum):
    """Validationresult.

    Manages ValidationResult operations and coordinates related state changes for the component.
    """
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_CONFIRMATION = "requires_confirmation"

@dataclass
class Operation:
    """Operation.

    Manages Operation operations and coordinates related state changes for the component.
    """
    id: str
    type: OperationType
    paths: List[Path]
    parameters: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    user_confirmed: bool = False
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    validation_result: Optional[ValidationResult] = None
    safety_checks_passed: bool = False

@dataclass
class OperationResult:
    """Operationresult.

    Manages OperationResult operations and coordinates related state changes for the component.
    """
    success: bool
    operation_id: str
    manifest_path: Optional[Path] = None
    processed_items: int = 0
    errors: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    validation_summary: Optional[Dict[str, Any]] = None
    dry_run_performed: bool = False

class SafetyError(DeepCleanerError):
    """Safetyerror.

    Manages SafetyError operations and coordinates related state changes for the component.
    """
    pass

class SafetyManager:
    """Safetymanager.

    Manages SafetyManager operations and coordinates related state changes for the component.
    """
    
    def __init__(self, config: Config = None, logger: Optional[logging.Logger] = None):
        """Initialize safety manager.
        
        Args:
            config: Configuration instance
            logger: Optional logger instance
        """
        self.config = config or Config()
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize safety components
        self.path_validator = PathValidator(logger=self.logger)
        self.manifest_system = ManifestSystem(logger=self.logger)
        self.process_manager = ProcessManager(logger=self.logger)
        try:
            from cortex_unified.engine.guard import PathGuard
            self.path_guard = PathGuard()
        except Exception:
            self.path_guard = None
        
        # Safety settings with enhanced defaults
        self.require_confirmation = True
        self.default_dry_run = True
        self.enforce_dry_run_first = True  # Always require dry-run before actual execution
        self.max_batch_size = 1000  # Maximum files to process in one operation
        self.max_file_size_mb = 1024  # Maximum individual file size to process (MB)
        self.validation_timeout = 30  # Timeout for validation operations (seconds)
        
        # Operation tracking
        self._pending_operations: Dict[str, Operation] = {}
        self._completed_dry_runs: Dict[str, OperationResult] = {}
        self._validation_callbacks: List[Callable[[Operation], bool]] = []
        
        # System directory blacklists (enhanced from path_validator)
        self._setup_system_blacklists()
        
        self.logger.info("SafetyManager initialized with enhanced safety components and validation pipeline")
    
    def _setup_system_blacklists(self) -> None:
        """Setup enhanced system directory blacklists.

        Manages setup system blacklists operations and coordinates related state changes for the component.
        """
        # Add critical system paths to path validator
        import sys
        
        if sys.platform.startswith("win"):
            sys_drive = os.environ.get("SystemDrive", "C:").rstrip("\\/")
            windir = os.environ.get("SystemRoot", os.environ.get("WINDIR", f"{sys_drive}\\Windows"))
            progdata = os.environ.get("PROGRAMDATA", f"{sys_drive}\\ProgramData")
            critical_paths = [
                os.path.join(windir, "System32"),
                os.path.join(windir, "SysWOW64"), 
                os.path.join(windir, "Boot"),
                os.path.join(windir, "Fonts"),
                os.path.join(windir, "inf"),
                os.path.join(windir, "Logs"),
                os.path.join(windir, "servicing"),
                os.path.join(windir, "WinSxS"),
                os.path.join(progdata, "Microsoft", "Windows", "Start Menu"),
                os.path.join(sys_drive, "Users", "All Users"),
                os.path.join(sys_drive, "Users", "Default User"),
            ]
        else:
            critical_paths = [
                "/boot", "/etc", "/lib", "/lib64", "/sbin", "/usr/sbin",
                "/var/log", "/var/lib", "/var/cache", "/var/spool",
                "/usr/lib", "/usr/lib64", "/usr/share", "/usr/include",
                "/opt/local", "/System", "/Library"  # macOS specific
            ]
        
        for path in critical_paths:
            try:
                self.path_validator.add_blacklist(path)
            except Exception as e:
                self.logger.debug(f"Could not add system blacklist path {path}: {e}")
    
    def configure_safety_settings(self, require_confirmation: bool = None,
                                default_dry_run: bool = None,
                                enforce_dry_run_first: bool = None,
                                max_batch_size: int = None,
                                max_file_size_mb: int = None,
                                validation_timeout: int = None) -> None:
        """Configure safety settings.
        
        Args:
            require_confirmation: Whether to require user confirmation for destructive operations
            default_dry_run: Whether operations default to dry-run mode
            enforce_dry_run_first: Whether to enforce dry-run before actual execution
            max_batch_size: Maximum number of files to process in one batch
            max_file_size_mb: Maximum individual file size to process (MB)
            validation_timeout: Timeout for validation operations (seconds)
        """
        if require_confirmation is not None:
            self.require_confirmation = require_confirmation
        if default_dry_run is not None:
            self.default_dry_run = default_dry_run
        if enforce_dry_run_first is not None:
            self.enforce_dry_run_first = enforce_dry_run_first
        if max_batch_size is not None:
            self.max_batch_size = max_batch_size
        if max_file_size_mb is not None:
            self.max_file_size_mb = max_file_size_mb
        if validation_timeout is not None:
            self.validation_timeout = validation_timeout
        
        self.logger.info(f"Updated safety settings: confirmation={self.require_confirmation}, "
                        f"dry_run={self.default_dry_run}, enforce_dry_run={self.enforce_dry_run_first}, "
                        f"batch_size={self.max_batch_size}, max_file_size={self.max_file_size_mb}MB")
    
    def add_validation_callback(self, callback: Callable[[Operation], bool]) -> None:
        """Add custom validation callback.
        
        Args:
            callback: Function that takes Operation and returns bool (True = approved)
        """
        self._validation_callbacks.append(callback)
        self.logger.debug(f"Added validation callback: {callback.__name__}")
    
    def create_operation(self, operation_type: OperationType, paths: List[Union[str, Path]], 
                        description: str = "", **parameters) -> Operation:
        """Create a new operation with automatic ID generation.
        
        Args:
            operation_type: Type of operation
            paths: List of file/directory paths
            description: Human-readable description
            **parameters: Additional operation parameters
            
        Returns:
            Created Operation instance
        """
        # Generate unique operation ID
        op_id = f"{operation_type.value}_{uuid.uuid4().hex[:8]}"
        
        # Convert paths to Path objects
        path_objects = [Path(p) if isinstance(p, str) else p for p in paths]
        
        operation = Operation(
            id=op_id,
            type=operation_type,
            paths=path_objects,
            parameters=parameters,
            dry_run=self.default_dry_run,
            description=description or f"{operation_type.value.title()} operation on {len(path_objects)} items"
        )
        
        self._pending_operations[op_id] = operation
        
        self.logger.info(f"Created operation {op_id}: {operation.description}")
        return operation
    
    def add_path_whitelist(self, path: Union[str, Path]) -> None:
        """Add path to safety whitelist.

        Manages add path whitelist operations and coordinates related state changes for the component.

        Args:
            path (Union[str, Path]): Filesystem path to the target file or directory.
        """
        self.path_validator.add_user_whitelist(str(path))
    
    def add_path_blacklist(self, path: Union[str, Path]) -> None:
        """Add path to safety blacklist.

        Manages add path blacklist operations and coordinates related state changes for the component.

        Args:
            path (Union[str, Path]): Filesystem path to the target file or directory.
        """
        self.path_validator.add_blacklist(str(path))
    
    def can_delete(self, path: Union[str, Path]) -> tuple[bool, str]:
        """Check if a path can be safely deleted against PathGuard and path validator.

        Validates the specified file or folder path against system blacklists,
        whitelists, and PathGuard engine rules to prevent accidental system damage.

        Args:
            path: Target file or directory path to check.

        Returns:
            tuple[bool, str]: (is_allowed, denial_reason). If allowed, reason is empty.
        """
        if not path:
            return False, "Path is empty"
        p_str = str(path)
        if getattr(self, "path_guard", None):
            verdict = self.path_guard.check(p_str)
            if not verdict.safe:
                return False, f"PathGuard blocked: {verdict.reason}"
        if getattr(self, "path_validator", None):
            is_valid, reason = self.path_validator.validate_path(p_str)
            if not is_valid:
                return False, f"Safety check blocked: {reason}"
        return True, ""
    
    def validate_operation(self, operation: Operation) -> ValidationResult:
        """Enhanced operation validation pipeline with comprehensive safety checks.
        
        Args:
            operation: Operation to validate
            
        Returns:
            ValidationResult indicating approval status
            
        Raises:
            SafetyError: If validation fails critically
        """
        try:
            self.logger.info(f"Starting validation pipeline for operation {operation.id}: {operation.type.value}")
            validation_start = datetime.now()
            
            # Phase 1: Basic validation checks
            validation_result = self._validate_basic_requirements(operation)
            if validation_result != ValidationResult.APPROVED:
                operation.validation_result = validation_result
                return validation_result
            
            # Phase 2: Dry-run enforcement for destructive operations
            if self._requires_dry_run_enforcement(operation):
                validation_result = self._enforce_dry_run_policy(operation)
                if validation_result != ValidationResult.APPROVED:
                    operation.validation_result = validation_result
                    return validation_result
            
            # Phase 3: Path safety validation with detailed analysis
            validation_result = self._validate_path_safety(operation)
            if validation_result != ValidationResult.APPROVED:
                operation.validation_result = validation_result
                return validation_result
            
            # Phase 4: File size and resource validation
            validation_result = self._validate_resource_limits(operation)
            if validation_result != ValidationResult.APPROVED:
                operation.validation_result = validation_result
                return validation_result
            
            # Phase 5: Custom validation callbacks
            validation_result = self._run_custom_validations(operation)
            if validation_result != ValidationResult.APPROVED:
                operation.validation_result = validation_result
                return validation_result
            
            # Phase 6: Operation-specific validation
            validation_result = self._validate_operation_specific(operation)
            if validation_result != ValidationResult.APPROVED:
                operation.validation_result = validation_result
                return validation_result
            
            # All validations passed
            operation.safety_checks_passed = True
            operation.validation_result = ValidationResult.APPROVED
            
            validation_time = (datetime.now() - validation_start).total_seconds()
            self.logger.info(f"Operation {operation.id} validation completed successfully in {validation_time:.2f}s")
            
            return ValidationResult.APPROVED
            
        except SafetyError:
            raise
        except Exception as e:
            raise SafetyError(f"Operation validation pipeline failed: {e}", 
                            operation="validate_operation",
                            details={"operation_id": operation.id})
    
    def _validate_basic_requirements(self, operation: Operation) -> ValidationResult:
        """Phase 1: Basic validation requirements.

        Manages validate basic requirements operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        if len(operation.paths) > self.max_batch_size:
            raise SafetyError(f"Batch size {len(operation.paths)} exceeds maximum {self.max_batch_size}")
        
        if not operation.paths:
            raise SafetyError("Operation contains no paths to process")
        
        if not isinstance(operation.type, OperationType):
            raise SafetyError(f"Invalid operation type: {operation.type}")
        
        return ValidationResult.APPROVED
    
    def _requires_dry_run_enforcement(self, operation: Operation) -> bool:
        """Check if operation requires dry-run enforcement.

        Manages requires dry run enforcement operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        destructive_operations = [OperationType.DELETE, OperationType.CLEAN, OperationType.MOVE]
        return (operation.type in destructive_operations and 
                self.enforce_dry_run_first and 
                not operation.dry_run)
    
    def _enforce_dry_run_policy(self, operation: Operation) -> ValidationResult:
        """Phase 2: Enforce dry-run policy for destructive operations.

        Manages enforce dry run policy operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        if not operation.dry_run:
            dry_run_key = self._get_dry_run_key(operation)
            
            if dry_run_key not in self._completed_dry_runs:
                self.logger.warning(f"Operation {operation.id} requires dry-run execution first")
                return ValidationResult.REQUIRES_CONFIRMATION
            
            # Verify dry-run results are still valid (not too old)
            dry_run_result = self._completed_dry_runs[dry_run_key]
            age_hours = (datetime.now() - dry_run_result.summary.get('completed_at', datetime.now())).total_seconds() / 3600
            
            if age_hours > 24:  # Dry-run results expire after 24 hours
                self.logger.warning(f"Dry-run results for operation {operation.id} are too old ({age_hours:.1f}h)")
                del self._completed_dry_runs[dry_run_key]
                return ValidationResult.REQUIRES_CONFIRMATION
        
        return ValidationResult.APPROVED
    
    def _get_dry_run_key(self, operation: Operation) -> str:
        """Generate a key for tracking dry-run results.

        Manages get dry run key operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            str: Formatted string or path.
        """
        # Paths are resolved + sorted (capped at 10) so the same logical
        # operation maps to one key even if the caller lists paths differently.
        path_signatures = sorted([str(p.resolve()) for p in operation.paths[:10]])  # Limit to first 10 paths
        return f"{operation.type.value}_{hash(tuple(path_signatures))}"
    
    def _validate_path_safety(self, operation: Operation) -> ValidationResult:
        """Phase 3: Enhanced path safety validation.

        Manages validate path safety operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        validation_summary = self.path_validator.get_validation_summary(operation.paths)
        
        operation.parameters['validation_summary'] = validation_summary
        
        if validation_summary['blocked_paths'] > 0:
            self.logger.warning(f"Operation {operation.id}: {validation_summary['blocked_paths']} paths blocked")
            
            # Log blocking reasons
            for reason, count in validation_summary['blocked_reasons'].items():
                self.logger.warning(f"  {reason}: {count} paths")
            
            # If all paths are blocked, reject
            if validation_summary['safe_paths'] == 0:
                self.logger.error(f"Operation {operation.id} rejected: all paths blocked by safety rules")
                return ValidationResult.REJECTED
            
            # Update operation with only safe paths
            safe_paths = self.path_validator.validate_operation_paths(operation.paths)
            operation.paths = safe_paths
            
            # If too many paths were blocked, require confirmation
            blocked_percentage = (validation_summary['blocked_paths'] / validation_summary['total_paths']) * 100
            if blocked_percentage > 25:  # More than 25% blocked
                self.logger.warning(f"High percentage of paths blocked ({blocked_percentage:.1f}%), requiring confirmation")
                return ValidationResult.REQUIRES_CONFIRMATION

        # Cross-check using PathGuard
        if getattr(self, "path_guard", None):
            guarded_paths = []
            guard_blocked = 0
            denials = []
            for p in operation.paths:
                verdict = self.path_guard.check(p)
                if not verdict.safe:
                    guard_blocked += 1
                    msg = f"PathGuard blocked {p}: {verdict.reason}"
                    denials.append(msg)
                    self.logger.warning(f"Operation {operation.id}: {msg}")
                else:
                    guarded_paths.append(p)
            if guard_blocked > 0:
                operation.parameters['guard_denials'] = denials
                operation.paths = guarded_paths
                if not operation.paths:
                    self.logger.error(f"Operation {operation.id} rejected: all paths blocked by PathGuard")
                    return ValidationResult.REJECTED
                return ValidationResult.REQUIRES_CONFIRMATION

        return ValidationResult.APPROVED
    
    def _validate_resource_limits(self, operation: Operation) -> ValidationResult:
        """Phase 4: Validate resource limits and file sizes.

        Manages validate resource limits operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        total_size_mb = 0
        large_files = []
        
        for path in operation.paths:
            try:
                if path.exists() and path.is_file():
                    size_bytes = path.stat().st_size
                    size_mb = size_bytes / (1024 * 1024)
                    total_size_mb += size_mb
                    
                    if size_mb > self.max_file_size_mb:
                        large_files.append((path, size_mb))
            except Exception as e:
                self.logger.debug(f"Could not get size for {path}: {e}")
        
        # Log resource usage
        self.logger.debug(f"Operation {operation.id} total size: {total_size_mb:.1f}MB")
        
        # Handle large files
        if large_files:
            self.logger.warning(f"Operation {operation.id} contains {len(large_files)} files exceeding size limit")
            for path, size_mb in large_files[:5]:  # Log first 5
                self.logger.warning(f"  Large file: {path} ({size_mb:.1f}MB)")
            
            operation.parameters['large_files'] = [(str(p), s) for p, s in large_files]
            
            # Require confirmation for operations with large files
            if not operation.dry_run:
                return ValidationResult.REQUIRES_CONFIRMATION
        
        return ValidationResult.APPROVED
    
    def _run_custom_validations(self, operation: Operation) -> ValidationResult:
        """Phase 5: Run custom validation callbacks.

        Manages run custom validations operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        for callback in self._validation_callbacks:
            try:
                if not callback(operation):
                    self.logger.warning(f"Custom validation failed for operation {operation.id}: {callback.__name__}")
                    return ValidationResult.REJECTED
            except Exception as e:
                self.logger.error(f"Custom validation callback error: {e}")
                return ValidationResult.REJECTED
        
        return ValidationResult.APPROVED
    
    def _validate_operation_specific(self, operation: Operation) -> ValidationResult:
        """Phase 6: Operation-specific validation.

        Manages validate operation specific operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        if operation.type == OperationType.DELETE:
            return self._validate_delete_operation(operation)
        elif operation.type == OperationType.CLEAN:
            return self._validate_clean_operation(operation)
        elif operation.type == OperationType.MOVE:
            return self._validate_move_operation(operation)
        elif operation.type == OperationType.RESTORE:
            return self._validate_restore_operation_enhanced(operation)
        elif operation.type == OperationType.ANALYZE:
            return self._validate_analyze_operation(operation)
        
        return ValidationResult.APPROVED
    
    def _validate_delete_operation(self, operation: Operation) -> ValidationResult:
        """_validate_delete_operation.

        Manages validate delete operation operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        if not operation.dry_run and self.require_confirmation and not operation.user_confirmed:
            return ValidationResult.REQUIRES_CONFIRMATION
        return ValidationResult.APPROVED
    
    def _validate_clean_operation(self, operation: Operation) -> ValidationResult:
        # Clean and delete share safety requirements; clean just logs more
        """_validate_clean_operation.

        Manages validate clean operation operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        return self._validate_delete_operation(operation)
    
    def _validate_move_operation(self, operation: Operation) -> ValidationResult:
        """_validate_move_operation.

        Manages validate move operation operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        destination = operation.parameters.get("destination")
        if not destination:
            raise SafetyError("Move operation requires destination parameter")
        
        dest_path = Path(destination)
        if not dest_path.exists():
            raise SafetyError(f"Move destination does not exist: {destination}")
        
        if not dest_path.is_dir():
            raise SafetyError(f"Move destination is not a directory: {destination}")
        
        return ValidationResult.APPROVED
    
    def _validate_analyze_operation(self, operation: Operation) -> ValidationResult:
        # Analyze operations are generally safe (read-only)
        """_validate_analyze_operation.

        Manages validate analyze operation operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        return ValidationResult.APPROVED
    
    def _validate_restore_operation_enhanced(self, operation: Operation) -> ValidationResult:
        """Enhanced validation for restore operations.

        Manages validate restore operation enhanced operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            ValidationResult: Result of the operation.
        """
        manifest_path = operation.parameters.get("manifest_path")
        if not manifest_path:
            raise SafetyError("Restore operation requires manifest_path parameter")
        
        manifest_file = Path(manifest_path)
        if not manifest_file.exists():
            raise SafetyError(f"Restore manifest not found: {manifest_path}")
        
        # Validate manifest content
        try:
            manifest_details = self.manifest_system.get_manifest_details(manifest_file)
            if not manifest_details:
                raise SafetyError(f"Could not read manifest: {manifest_path}")
            
            if manifest_details.get("status") != "completed":
                raise SafetyError("Can only restore from completed operations")
            
            if manifest_details.get("options", {}).get("dry_run", True):
                raise SafetyError("Cannot restore from dry-run operations")
            
        except Exception as e:
            raise SafetyError(f"Manifest validation failed: {e}")
        
        return ValidationResult.APPROVED
    
    def _validate_restore_operation(self, operation: Operation) -> bool:
        """Validate restore operation specifics.
        
        Args:
            operation: Restore operation to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            manifest_path = operation.parameters.get("manifest_path")
            if manifest_path and not Path(manifest_path).exists():
                self.logger.error(f"Restore manifest not found: {manifest_path}")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating restore operation: {e}")
            return False
    
    def execute_safe_operation(self, operation: Operation) -> OperationResult:
        """Execute operation with enhanced safety protocols and dry-run enforcement.
        
        Args:
            operation: Operation to execute
            
        Returns:
            OperationResult with execution details
            
        Raises:
            SafetyError: If operation execution fails
        """
        execution_start = datetime.now()
        
        try:
            self.logger.info(f"Starting safe execution of operation {operation.id}")
            
            # Phase 1: Pre-execution validation
            validation_result = self.validate_operation(operation)
            
            if validation_result == ValidationResult.REJECTED:
                raise SafetyError(f"Operation {operation.id} rejected by safety validation")
            
            if validation_result == ValidationResult.REQUIRES_CONFIRMATION:
                raise SafetyError(f"Operation {operation.id} requires user confirmation")
            
            # Phase 2: Dry-run enforcement check
            if self._should_enforce_dry_run(operation):
                return self._execute_mandatory_dry_run(operation)
            
            # Phase 3: Create operation manifest with enhanced metadata
            manifest_id = self.manifest_system.create_operation_manifest(
                operation_type=operation.type.value,
                parameters={
                    "dry_run": operation.dry_run,
                    "user_confirmed": operation.user_confirmed,
                    "description": operation.description,
                    "safety_checks_passed": operation.safety_checks_passed,
                    "validation_summary": operation.parameters.get('validation_summary', {}),
                    **operation.parameters
                }
            )
            
            self.logger.info(f"Executing operation {operation.id} with manifest {manifest_id} (dry_run={operation.dry_run})")
            
            try:
                # Phase 4: Execute the operation with monitoring
                execution_result = self._execute_operation_with_monitoring(operation, manifest_id)
                
                # Phase 5: Post-execution processing
                result = self._finalize_operation_execution(operation, manifest_id, execution_result, execution_start)
                
                # Phase 6: Store dry-run results for future reference
                if operation.dry_run:
                    self._store_dry_run_result(operation, result)
                
                return result
                
            except Exception as e:
                # Enhanced error handling with manifest logging
                self.manifest_system.log_error(manifest_id, e, {
                    "operation_id": operation.id,
                    "execution_phase": "operation_execution",
                    "dry_run": operation.dry_run
                })
                
                # Finalize manifest as failed
                try:
                    manifest_path = self.manifest_system.finalize_manifest(manifest_id, success=False)
                except Exception as finalize_error:
                    self.logger.error(f"Failed to finalize failed manifest: {finalize_error}")
                    manifest_path = None
                
                raise SafetyError(f"Operation execution failed: {e}",
                                operation="execute_operation",
                                details={"operation_id": operation.id, "manifest_id": manifest_id})
        
        except SafetyError:
            raise
        except Exception as e:
            raise SafetyError(f"Unexpected error during safe operation execution: {e}",
                            operation="execute_safe_operation",
                            details={"operation_id": operation.id})
    
    def _should_enforce_dry_run(self, operation: Operation) -> bool:
        """Check if we should enforce a dry-run before actual execution.

        Manages should enforce dry run operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        if operation.dry_run:
            return False  # Already a dry-run
        
        if not self.enforce_dry_run_first:
            return False  # Dry-run enforcement disabled
        
        destructive_ops = [OperationType.DELETE, OperationType.CLEAN, OperationType.MOVE]
        if operation.type not in destructive_ops:
            return False  # Non-destructive operations don't need dry-run
        
        dry_run_key = self._get_dry_run_key(operation)
        return dry_run_key not in self._completed_dry_runs
    
    def _execute_mandatory_dry_run(self, operation: Operation) -> OperationResult:
        """Execute a mandatory dry-run before the actual operation.

        Manages execute mandatory dry run operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.

        Returns:
            OperationResult: Result of the operation.
        """
        self.logger.info(f"Executing mandatory dry-run for operation {operation.id}")
        
        # Create a dry-run version of the operation
        dry_run_operation = Operation(
            id=f"{operation.id}_dryrun",
            type=operation.type,
            paths=operation.paths.copy(),
            parameters=operation.parameters.copy(),
            dry_run=True,
            user_confirmed=True,  # Dry-runs don't need confirmation
            description=f"Dry-run: {operation.description}",
            created_at=operation.created_at,
            validation_result=operation.validation_result,
            safety_checks_passed=operation.safety_checks_passed
        )
        
        # Execute the dry-run
        result = self.execute_safe_operation(dry_run_operation)
        result.dry_run_performed = True
        
        # Store the dry-run result
        self._store_dry_run_result(operation, result)
        
        return result
    
    def _execute_operation_with_monitoring(self, operation: Operation, manifest_id: str) -> Dict[str, Any]:
        """Execute operation with enhanced monitoring and error handling.

        Manages execute operation with monitoring operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.
            manifest_id (str): The manifest id parameter.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        processed_items = 0
        errors = []
        
        try:
            if operation.type == OperationType.DELETE:
                processed_items, errors = self._execute_delete_operation(operation, manifest_id)
            
            elif operation.type == OperationType.CLEAN:
                processed_items, errors = self._execute_clean_operation(operation, manifest_id)
            
            elif operation.type == OperationType.MOVE:
                processed_items, errors = self._execute_move_operation(operation, manifest_id)
            
            elif operation.type == OperationType.ANALYZE:
                processed_items, errors = self._execute_analyze_operation(operation, manifest_id)
            
            elif operation.type == OperationType.RESTORE:
                processed_items, errors = self._execute_restore_operation(operation, manifest_id)
            
            else:
                raise SafetyError(f"Unsupported operation type: {operation.type}")
            
            return {
                "processed_items": processed_items,
                "errors": errors,
                "success": len(errors) == 0
            }
            
        except Exception as e:
            self.logger.error(f"Error during operation execution: {e}")
            raise
    
    def _finalize_operation_execution(self, operation: Operation, manifest_id: str, 
                                   execution_result: Dict[str, Any], execution_start: datetime) -> OperationResult:
        """Finalize operation execution with comprehensive result generation.

        Manages finalize operation execution operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.
            manifest_id (str): The manifest id parameter.
            execution_result (Dict[str, Any]): The execution result parameter.
            execution_start (datetime): The execution start parameter.

        Returns:
            OperationResult: Result of the operation.
        """
        execution_time = (datetime.now() - execution_start).total_seconds()
        success = execution_result["success"]
        
        # Finalize manifest
        manifest_path = self.manifest_system.finalize_manifest(manifest_id, success=success)
        
        # Create comprehensive result
        result = OperationResult(
            success=success,
            operation_id=operation.id,
            manifest_path=manifest_path,
            processed_items=execution_result["processed_items"],
            errors=execution_result["errors"],
            execution_time=execution_time,
            validation_summary=operation.parameters.get('validation_summary'),
            dry_run_performed=operation.dry_run,
            summary={
                "operation_type": operation.type.value,
                "dry_run": operation.dry_run,
                "total_paths": len(operation.paths),
                "processed_items": execution_result["processed_items"],
                "error_count": len(execution_result["errors"]),
                "execution_time": execution_time,
                "completed_at": datetime.now(),
                "safety_checks_passed": operation.safety_checks_passed,
                "manifest_id": manifest_id
            }
        )
        
        # Log completion
        if success:
            self.logger.info(f"Operation {operation.id} completed successfully: "
                           f"{execution_result['processed_items']} items processed in {execution_time:.2f}s")
        else:
            self.logger.warning(f"Operation {operation.id} completed with {len(execution_result['errors'])} errors "
                              f"in {execution_time:.2f}s")
        
        # Remove from pending operations
        self._pending_operations.pop(operation.id, None)
        
        return result
    
    def _store_dry_run_result(self, operation: Operation, result: OperationResult) -> None:
        """_store_dry_run_result.

        Manages store dry run result operations and coordinates related state changes for the component.

        Args:
            operation (Operation): The operation parameter.
            result (OperationResult): Collection or dictionary holding operation results.
        """
        if operation.dry_run or result.dry_run_performed:
            dry_run_key = self._get_dry_run_key(operation)
            self._completed_dry_runs[dry_run_key] = result
            self.logger.debug(f"Stored dry-run result for key: {dry_run_key}")
    
    def get_dry_run_result(self, operation: Operation) -> Optional[OperationResult]:
        """Get stored dry-run result for an operation pattern.
        
        Args:
            operation: Operation to check for dry-run results
            
        Returns:
            OperationResult if dry-run exists, None otherwise
        """
        dry_run_key = self._get_dry_run_key(operation)
        return self._completed_dry_runs.get(dry_run_key)
    
    def clear_dry_run_cache(self, max_age_hours: int = 24) -> int:
        """Clear old dry-run results from cache.
        
        Args:
            max_age_hours: Maximum age of dry-run results to keep
            
        Returns:
            Number of entries cleared
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleared_count = 0
        
        keys_to_remove = []
        for key, result in self._completed_dry_runs.items():
            completed_at = result.summary.get('completed_at', datetime.now())
            if completed_at < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._completed_dry_runs[key]
            cleared_count += 1
        
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} old dry-run results from cache")
        
        return cleared_count
    
    def _execute_delete_operation(self, operation: Operation, manifest_id: str) -> tuple[int, List[str]]:
        """Execute delete operation.
        
        Args:
            operation: Delete operation
            manifest_id: Manifest ID for logging
            
        Returns:
            Tuple of (processed_items, errors)
        """
        processed_items = 0
        errors = []
        
        for path in operation.paths:
            try:
                allowed, denial = self.can_delete(path)
                if not allowed:
                    error_msg = f"Deletion blocked by safety guard: {path} ({denial})"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
                    self.manifest_system.log_file_action(
                        manifest_id,
                        "file" if path.is_file() else "directory",
                        path,
                        f"blocked: {denial}"
                    )
                    continue

                if operation.dry_run:
                    # Dry run - just log what would be deleted
                    self.manifest_system.log_file_action(
                        manifest_id, 
                        "file" if path.is_file() else "directory",
                        path, 
                        "would_delete"
                    )
                else:
                    # Actual deletion
                    if path.is_file():
                        path.unlink()
                        action = "deleted"
                    elif path.is_dir():
                        import shutil
                        shutil.rmtree(path)
                        action = "deleted"
                    else:
                        continue  # Skip non-existent paths
                    
                    self.manifest_system.log_file_action(
                        manifest_id,
                        "file" if path.was_file else "directory",  # Note: path no longer exists
                        path,
                        action
                    )
                
                processed_items += 1
                
            except Exception as e:
                error_msg = f"Failed to delete {path}: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                self.manifest_system.log_error(manifest_id, e, {"path": str(path)})
        
        return processed_items, errors
    
    def _execute_clean_operation(self, operation: Operation, manifest_id: str) -> tuple[int, List[str]]:
        """Execute clean operation (similar to delete but with additional safety checks).
        
        Args:
            operation: Clean operation
            manifest_id: Manifest ID for logging
            
        Returns:
            Tuple of (processed_items, errors)
        """
        # Clean operations are essentially delete operations with extra validation
        return self._execute_delete_operation(operation, manifest_id)
    
    def _execute_move_operation(self, operation: Operation, manifest_id: str) -> tuple[int, List[str]]:
        """Execute move operation.
        
        Args:
            operation: Move operation
            manifest_id: Manifest ID for logging
            
        Returns:
            Tuple of (processed_items, errors)
        """
        processed_items = 0
        errors = []
        
        destination = operation.parameters.get("destination")
        if not destination:
            errors.append("No destination specified for move operation")
            return processed_items, errors
        
        dest_path = Path(destination)
        
        for path in operation.paths:
            try:
                if operation.dry_run:
                    # Dry run - just log what would be moved
                    self.manifest_system.log_file_action(
                        manifest_id,
                        "file" if path.is_file() else "directory",
                        path,
                        "would_move",
                        destination=str(dest_path / path.name)
                    )
                else:
                    # Actual move
                    new_path = dest_path / path.name
                    path.rename(new_path)
                    
                    self.manifest_system.log_file_action(
                        manifest_id,
                        "file" if new_path.is_file() else "directory",
                        path,
                        "moved",
                        new_path=str(new_path)
                    )
                
                processed_items += 1
                
            except Exception as e:
                error_msg = f"Failed to move {path}: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                self.manifest_system.log_error(manifest_id, e, {"path": str(path)})
        
        return processed_items, errors
    
    def _execute_analyze_operation(self, operation: Operation, manifest_id: str) -> tuple[int, List[str]]:
        """Execute analyze operation (read-only analysis).
        
        Args:
            operation: Analyze operation
            manifest_id: Manifest ID for logging
            
        Returns:
            Tuple of (processed_items, errors)
        """
        processed_items = 0
        errors = []
        
        for path in operation.paths:
            try:
                # Analyze operation - just log file information
                self.manifest_system.log_file_action(
                    manifest_id,
                    "file" if path.is_file() else "directory",
                    path,
                    "analyzed"
                )
                processed_items += 1
                
            except Exception as e:
                error_msg = f"Failed to analyze {path}: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                self.manifest_system.log_error(manifest_id, e, {"path": str(path)})
        
        return processed_items, errors
    
    def _execute_restore_operation(self, operation: Operation, manifest_id: str) -> tuple[int, List[str]]:
        """Execute restore operation.
        
        Args:
            operation: Restore operation
            manifest_id: Manifest ID for logging
            
        Returns:
            Tuple of (processed_items, errors)
        """
        processed_items = 0
        errors = []
        
        try:
            # Get restore actions from manifest
            source_manifest_path = Path(operation.parameters["manifest_path"])
            restore_actions = self.manifest_system.get_restore_operations(source_manifest_path)
            
            for action in restore_actions:
                try:
                    if action["type"] == "create_directory":
                        if not operation.dry_run:
                            Path(action["path"]).mkdir(parents=True, exist_ok=True)
                        
                        self.manifest_system.log_file_action(
                            manifest_id,
                            "directory",
                            Path(action["path"]),
                            "would_create_directory" if operation.dry_run else "created_directory"
                        )
                    
                    elif action["type"] == "restore":
                        if not operation.dry_run:
                            pass
                        
                        self.manifest_system.log_file_action(
                            manifest_id,
                            action["item_type"],
                            Path(action["original_path"]),
                            "would_restore" if operation.dry_run else "restored"
                        )
                    
                    processed_items += 1
                    
                except Exception as e:
                    error_msg = f"Failed to restore {action.get('original_path', 'unknown')}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    self.manifest_system.log_error(manifest_id, e, {"action": action})
        
        except Exception as e:
            error_msg = f"Failed to process restore manifest: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            self.manifest_system.log_error(manifest_id, e)
        
        return processed_items, errors
    
    def get_operation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get history of operations.
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of operation summaries
        """
        return self.manifest_system.list_manifests(limit=limit)
    
    def get_restore_candidates(self) -> List[Dict[str, Any]]:
        """Get operations that can be restored.
        
        Returns:
            List of restorable operations
        """
        manifests = self.manifest_system.list_manifests()
        
        restore_candidates = []
        for manifest in manifests:
            # Only operations with actual deletions can be restored
            if (manifest.get("operation") in ["delete", "clean"] and 
                manifest.get("status") == "completed" and
                not manifest.get("options", {}).get("dry_run", True)):
                restore_candidates.append(manifest)
        
        return restore_candidates
    
    def get_pending_operations(self) -> List[Operation]:
        """Get list of pending operations.
        
        Returns:
            List of pending Operation objects
        """
        return list(self._pending_operations.values())
    
    def get_operation_by_id(self, operation_id: str) -> Optional[Operation]:
        """Get operation by ID.
        
        Args:
            operation_id: Operation ID to lookup
            
        Returns:
            Operation if found, None otherwise
        """
        return self._pending_operations.get(operation_id)
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a pending operation.
        
        Args:
            operation_id: Operation ID to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        if operation_id in self._pending_operations:
            operation = self._pending_operations.pop(operation_id)
            self.logger.info(f"Cancelled operation {operation_id}: {operation.description}")
            return True
        return False
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Get comprehensive safety manager status.
        
        Returns:
            Dictionary with safety manager status information
        """
        return {
            "safety_settings": {
                "require_confirmation": self.require_confirmation,
                "default_dry_run": self.default_dry_run,
                "enforce_dry_run_first": self.enforce_dry_run_first,
                "max_batch_size": self.max_batch_size,
                "max_file_size_mb": self.max_file_size_mb,
                "validation_timeout": self.validation_timeout
            },
            "pending_operations": len(self._pending_operations),
            "cached_dry_runs": len(self._completed_dry_runs),
            "validation_callbacks": len(self._validation_callbacks),
            "running_processes": len(self.process_manager.get_running_processes()),
            "manifest_directory": str(self.manifest_system.manifest_dir),
            "components_status": {
                "path_validator": "active",
                "manifest_system": "active", 
                "process_manager": "active"
            }
        }
    
    def validate_system_safety(self) -> Dict[str, Any]:
        """Perform system-wide safety validation.
        
        Returns:
            Dictionary with system safety validation results
        """
        validation_results = {
            "overall_status": "safe",
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check manifest directory
            if not self.manifest_system.manifest_dir.exists():
                validation_results["warnings"].append("Manifest directory does not exist")
            elif not os.access(self.manifest_system.manifest_dir, os.W_OK):
                validation_results["errors"].append("No write access to manifest directory")
            
            validation_results["checks"]["manifest_directory"] = "ok"
            
            # Check process manager
            running_processes = self.process_manager.get_running_processes()
            if len(running_processes) > 10:
                validation_results["warnings"].append(f"Many running processes: {len(running_processes)}")
            
            validation_results["checks"]["process_manager"] = "ok"
            
            # Check path validator
            try:
                test_paths = [Path.home(), Path.cwd()]
                self.path_validator.validate_operation_paths(test_paths)
                validation_results["checks"]["path_validator"] = "ok"
            except Exception as e:
                validation_results["errors"].append(f"Path validator error: {e}")
            
            # Set overall status
            if validation_results["errors"]:
                validation_results["overall_status"] = "error"
            elif validation_results["warnings"]:
                validation_results["overall_status"] = "warning"
            
        except Exception as e:
            validation_results["errors"].append(f"System validation error: {e}")
            validation_results["overall_status"] = "error"
        
        return validation_results
    
    def cleanup_resources(self) -> None:
        """Clean up all safety manager resources.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.
        """
        try:
            self.logger.info("Starting SafetyManager cleanup")
            
            # Cancel all pending operations
            cancelled_count = 0
            for op_id in list(self._pending_operations.keys()):
                if self.cancel_operation(op_id):
                    cancelled_count += 1
            
            if cancelled_count > 0:
                self.logger.info(f"Cancelled {cancelled_count} pending operations")
            
            # Kill any running processes
            killed_count = self.process_manager.kill_all_processes()
            if killed_count > 0:
                self.logger.info(f"Killed {killed_count} running processes")
            
            # Clear dry-run cache
            cleared_count = self.clear_dry_run_cache(max_age_hours=0)  # Clear all
            if cleared_count > 0:
                self.logger.info(f"Cleared {cleared_count} cached dry-run results")
            
            # Clean up old manifests (optional - keep last 30 days)
            try:
                cleaned_manifests = self.manifest_system.cleanup_old_manifests(keep_days=30)
                if cleaned_manifests > 0:
                    self.logger.info(f"Cleaned up {cleaned_manifests} old manifest files")
            except Exception as e:
                self.logger.warning(f"Could not clean up old manifests: {e}")
            
            self.logger.info("SafetyManager cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during SafetyManager cleanup: {e}")
    
    def __del__(self):
        """Del.

        Manages del operations and coordinates related state changes for the component.
        """
        try:
            self.cleanup_resources()
        except Exception:
            pass  # Ignore errors during destruction