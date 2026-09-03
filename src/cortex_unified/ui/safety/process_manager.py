"""Safe external command execution manager."""

import os
import sys
import shutil
import subprocess
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging
import time

from cortex_unified.core.utils import DeepCleanerError

class ProcessError(DeepCleanerError):
    """Exception raised for process execution errors."""
    pass

class ProcessTimeoutError(ProcessError):
    """Exception raised when process execution times out."""
    pass

class ExecutableNotFoundError(ProcessError):
    """Exception raised when executable is not found."""
    pass

@dataclass
class ProcessResult:
    """Result of a process execution."""
    returncode: int
    stdout: str
    stderr: str
    execution_time: float
    command: List[str]
    timed_out: bool = False

class ProcessManager:
    """Manages safe external command execution."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize process manager.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self._running_processes: Dict[int, subprocess.Popen] = {}
        self._process_lock = threading.Lock()
        
        # Default security settings
        self.max_execution_time = 300  # 5 minutes default timeout
        self.max_output_size = 10 * 1024 * 1024  # 10MB max output
        self.allowed_executables: Optional[List[str]] = None  # None = allow all found executables
        self.blocked_executables: List[str] = [
            "rm", "del", "format", "fdisk", "mkfs",  # Dangerous system commands
            "sudo", "su", "runas",  # Privilege escalation
            "nc", "netcat", "telnet", "ssh",  # Network tools
            "wget", "curl", "ftp",  # Download tools
            "python", "python3", "perl", "ruby", "node",  # Interpreters (unless specifically allowed)
        ]
    
    def set_security_policy(self, allowed_executables: List[str] = None, 
                          blocked_executables: List[str] = None,
                          max_execution_time: int = None,
                          max_output_size: int = None) -> None:
        """Set security policy for process execution.
        
        Args:
            allowed_executables: List of allowed executable names (None = allow all found)
            blocked_executables: List of blocked executable names
            max_execution_time: Maximum execution time in seconds
            max_output_size: Maximum output size in bytes
        """
        if allowed_executables is not None:
            self.allowed_executables = allowed_executables
        if blocked_executables is not None:
            self.blocked_executables = blocked_executables
        if max_execution_time is not None:
            self.max_execution_time = max_execution_time
        if max_output_size is not None:
            self.max_output_size = max_output_size
        
        self.logger.info(f"Updated security policy: allowed={self.allowed_executables}, "
                        f"blocked={self.blocked_executables}, timeout={self.max_execution_time}s")
    
    def validate_executable(self, executable: str) -> str:
        """Validate and locate executable.
        
        Args:
            executable: Name or path of executable
            
        Returns:
            Full path to validated executable
            
        Raises:
            ExecutableNotFoundError: If executable not found or not allowed
        """
        try:
            exe_name = Path(executable).name.lower()
            
            if exe_name in [blocked.lower() for blocked in self.blocked_executables]:
                raise ExecutableNotFoundError(f"Executable '{executable}' is blocked by security policy")
            
            if (self.allowed_executables is not None and 
                exe_name not in [allowed.lower() for allowed in self.allowed_executables]):
                raise ExecutableNotFoundError(f"Executable '{executable}' is not in allowed list")
            
            # Find the executable
            exe_path = shutil.which(executable)
            if not exe_path:
                raise ExecutableNotFoundError(f"Executable '{executable}' not found in PATH")
            
            # Additional security checks
            exe_path_obj = Path(exe_path)
            
            if not exe_path_obj.exists():
                raise ExecutableNotFoundError(f"Executable path does not exist: {exe_path}")
            
            if not os.access(exe_path, os.X_OK):
                raise ExecutableNotFoundError(f"No execute permission for: {exe_path}")
            
            # On Unix systems, check if executable is in a safe location
            if not sys.platform.startswith("win"):
                safe_dirs = ["/usr/bin", "/usr/local/bin", "/bin", "/sbin", "/usr/sbin"]
                if not any(str(exe_path_obj).startswith(safe_dir) for safe_dir in safe_dirs):
                    self.logger.warning(f"Executable not in standard system directory: {exe_path}")
            
            self.logger.debug(f"Validated executable: {executable} -> {exe_path}")
            return exe_path
            
        except ExecutableNotFoundError:
            raise
        except Exception as e:
            raise ExecutableNotFoundError(f"Error validating executable '{executable}': {e}")
    
    def sanitize_command_args(self, args: List[str]) -> List[str]:
        """Sanitize command arguments for safe execution.
        
        Args:
            args: List of command arguments
            
        Returns:
            Sanitized arguments list
        """
        sanitized = []
        
        for arg in args:
            # Convert to string and strip whitespace
            arg_str = str(arg).strip()
            
            # Skip empty arguments
            if not arg_str:
                continue
            
            # Check for dangerous patterns
            dangerous_patterns = [
                "|", "&", ";", "`", "$(",  # Shell operators
                "$(", "`",  # Command substitution
                "../", "..\\",  # Directory traversal
            ]
            
            # Log warning for potentially dangerous arguments
            for pattern in dangerous_patterns:
                if pattern in arg_str:
                    self.logger.warning(f"Potentially dangerous argument pattern '{pattern}' in: {arg_str}")
            
            sanitized.append(arg_str)
        
        return sanitized
    
    def execute_safe_command(self, cmd: List[str], timeout: int = None, 
                           cwd: Union[str, Path] = None, env: Dict[str, str] = None,
                           capture_output: bool = True) -> ProcessResult:
        """Safely execute external command with validation and monitoring.
        
        Args:
            cmd: Command and arguments list
            timeout: Execution timeout in seconds (uses default if None)
            cwd: Working directory for command execution
            env: Environment variables (None = inherit current environment)
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            ProcessResult with execution details
            
        Raises:
            ProcessError: If command execution fails
            ProcessTimeoutError: If command times out
            ExecutableNotFoundError: If executable is not found or allowed
        """
        if not cmd:
            raise ProcessError("Empty command list")
        
        start_time = time.time()
        
        try:
            # Validate and locate executable
            executable_path = self.validate_executable(cmd[0])
            
            # Sanitize arguments
            sanitized_args = self.sanitize_command_args(cmd[1:])
            full_cmd = [executable_path] + sanitized_args
            
            # Set timeout
            exec_timeout = timeout or self.max_execution_time
            
            # Prepare environment
            if env is None:
                # Use current environment but remove potentially dangerous variables
                safe_env = os.environ.copy()
                dangerous_env_vars = ["LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "PATH"]
                # Don't remove PATH entirely, but we could sanitize it
            else:
                safe_env = env.copy()
            
            # Validate working directory
            if cwd:
                cwd_path = Path(cwd).resolve()
                if not cwd_path.exists() or not cwd_path.is_dir():
                    raise ProcessError(f"Invalid working directory: {cwd}")
                cwd = str(cwd_path)
            
            self.logger.info(f"Executing command: {' '.join(full_cmd[:3])}{'...' if len(full_cmd) > 3 else ''}")
            
            # Execute command
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                stdin=subprocess.DEVNULL,  # Never allow interactive input
                cwd=cwd,
                env=safe_env,
                shell=False,  # NEVER use shell=True for security
                text=True,
                bufsize=1,  # Line buffered
                # On Windows, prevent new console window
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
            )
            
            # Track running process
            with self._process_lock:
                self._running_processes[process.pid] = process
            
            try:
                # Wait for completion with timeout
                stdout, stderr = process.communicate(timeout=exec_timeout)
                
                # Check output size limits
                if capture_output:
                    if len(stdout) > self.max_output_size:
                        stdout = stdout[:self.max_output_size] + "\n[OUTPUT TRUNCATED]"
                        self.logger.warning("Command output truncated due to size limit")
                    
                    if len(stderr) > self.max_output_size:
                        stderr = stderr[:self.max_output_size] + "\n[ERROR OUTPUT TRUNCATED]"
                        self.logger.warning("Command error output truncated due to size limit")
                
                execution_time = time.time() - start_time
                
                result = ProcessResult(
                    returncode=process.returncode,
                    stdout=stdout or "",
                    stderr=stderr or "",
                    execution_time=execution_time,
                    command=full_cmd,
                    timed_out=False
                )
                
                if process.returncode != 0:
                    self.logger.warning(f"Command failed with return code {process.returncode}: {full_cmd[0]}")
                else:
                    self.logger.debug(f"Command completed successfully in {execution_time:.2f}s")
                
                return result
                
            except subprocess.TimeoutExpired:
                # Handle timeout
                self.logger.error(f"Command timed out after {exec_timeout}s: {full_cmd[0]}")
                
                # Terminate process
                try:
                    process.terminate()
                    # Give it a chance to terminate gracefully
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    process.kill()
                    process.wait()
                
                execution_time = time.time() - start_time
                
                result = ProcessResult(
                    returncode=-1,
                    stdout="",
                    stderr=f"Process timed out after {exec_timeout} seconds",
                    execution_time=execution_time,
                    command=full_cmd,
                    timed_out=True
                )
                
                raise ProcessTimeoutError(f"Command timed out after {exec_timeout}s", 
                                        operation="execute_command", 
                                        details={"command": full_cmd[0], "timeout": exec_timeout})
            
            finally:
                # Remove from tracking
                with self._process_lock:
                    self._running_processes.pop(process.pid, None)
        
        except (ExecutableNotFoundError, ProcessTimeoutError):
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            raise ProcessError(f"Command execution failed: {e}", 
                             operation="execute_command",
                             details={"command": cmd[0] if cmd else "unknown", "error": str(e)})
    
    def execute_with_progress(self, cmd: List[str], progress_callback=None, **kwargs) -> ProcessResult:
        """Execute command with progress monitoring.
        
        Args:
            cmd: Command and arguments list
            progress_callback: Function to call with progress updates
            **kwargs: Additional arguments for execute_safe_command
            
        Returns:
            ProcessResult with execution details
        """
        if not progress_callback:
            return self.execute_safe_command(cmd, **kwargs)
        
        # For now, just execute normally and call progress callback
        # and parse progress information
        
        progress_callback(0, "Starting command execution...")
        
        try:
            result = self.execute_safe_command(cmd, **kwargs)
            progress_callback(100, "Command completed")
            return result
        except Exception as e:
            progress_callback(-1, f"Command failed: {e}")
            raise
    
    def kill_all_processes(self) -> int:
        """Kill all running processes managed by this instance.
        
        Returns:
            Number of processes killed
        """
        killed_count = 0
        
        with self._process_lock:
            processes_to_kill = list(self._running_processes.values())
        
        for process in processes_to_kill:
            try:
                if process.poll() is None:  # Still running
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    killed_count += 1
                    self.logger.info(f"Killed process PID {process.pid}")
            except Exception as e:
                self.logger.error(f"Error killing process PID {process.pid}: {e}")
        
        with self._process_lock:
            self._running_processes.clear()
        
        return killed_count
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get information about currently running processes.
        
        Returns:
            List of process information dictionaries
        """
        process_info = []
        
        with self._process_lock:
            for pid, process in self._running_processes.items():
                try:
                    info = {
                        "pid": pid,
                        "command": " ".join(process.args) if hasattr(process, 'args') else "unknown",
                        "running": process.poll() is None,
                        "returncode": process.returncode
                    }
                    process_info.append(info)
                except Exception as e:
                    self.logger.error(f"Error getting process info for PID {pid}: {e}")
        
        return process_info
    
    def cleanup(self) -> None:
        """Clean up all resources and kill running processes."""
        try:
            killed_count = self.kill_all_processes()
            if killed_count > 0:
                self.logger.info(f"Cleanup: killed {killed_count} running processes")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during destruction