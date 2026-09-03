"""
Resource throttling and system performance management.
"""

import os
import platform
import psutil
import threading
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class SystemLoad:
    """Data structure for system load information."""
    cpu_percent: float
    memory_percent: float
    disk_io_percent: float
    network_io_percent: float
    load_average: Optional[float] = None  # Unix systems only
    
    def is_high_load(self, cpu_threshold: float = 80.0, memory_threshold: float = 85.0) -> bool:
        """Check if system is under high load."""
        return (self.cpu_percent > cpu_threshold or 
                self.memory_percent > memory_threshold)

class ResourceThrottler:
    """Manages system resource usage and throttling."""
    
    def __init__(self, cpu_limit: float = 0.8, io_priority: str = "low", memory_limit: float = 0.85):
        """Initialize resource throttler with limits."""
        self.cpu_limit = cpu_limit * 100  # Convert to percentage
        self.memory_limit = memory_limit * 100  # Convert to percentage
        self.io_priority = io_priority
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_load: Optional[SystemLoad] = None
        self._load_lock = threading.Lock()
        
        # Throttling state
        self._throttle_active = False
        self._throttle_delay = 0.0
        
        # Process reference
        self._process = psutil.Process()
        
        # Set initial process priority
        self.set_process_priority(io_priority)
    
    def set_process_priority(self, priority: str) -> None:
        """Set process priority for CPU and I/O operations."""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                # Windows priority classes
                priority_map = {
                    "low": psutil.BELOW_NORMAL_PRIORITY_CLASS,
                    "normal": psutil.NORMAL_PRIORITY_CLASS,
                    "high": psutil.HIGH_PRIORITY_CLASS,
                    "realtime": psutil.REALTIME_PRIORITY_CLASS
                }
                if priority in priority_map:
                    self._process.nice(priority_map[priority])
            else:
                # Unix-like systems (Linux, macOS)
                priority_map = {
                    "low": 10,
                    "normal": 0,
                    "high": -5,
                    "realtime": -10
                }
                if priority in priority_map:
                    self._process.nice(priority_map[priority])
            
            # Set I/O priority if available
            if hasattr(self._process, "ionice"):
                if system == "linux":
                    io_priority_map = {
                        "low": (psutil.IOPRIO_CLASS_IDLE, 0),
                        "normal": (psutil.IOPRIO_CLASS_BE, 4),
                        "high": (psutil.IOPRIO_CLASS_BE, 1)
                    }
                    if priority in io_priority_map:
                        ioclass, value = io_priority_map[priority]
                        self._process.ionice(ioclass, value)
                        
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            # Ignore if we can't set priority (insufficient permissions)
            pass

    def set_eco_qos(self, enable: bool = True) -> bool:
        """Enable Windows 11 EcoQoS (Efficiency Mode) to schedule background
        tasks on energy-efficient E-cores and prevent UI frame drops.
        """
        if platform.system().lower() != "windows":
            return False
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
                """PROCESS_POWER_THROTTLING_STATE."""
                _fields_ = [
                    ("Version", wintypes.ULONG),
                    ("ControlMask", wintypes.ULONG),
                    ("StateMask", wintypes.ULONG),
                ]
                """PROCESS_POWER_THROTTLING_STATE class."""

            ProcessPowerThrottling = 4
            PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
            PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1

            state = PROCESS_POWER_THROTTLING_STATE()
            state.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
            state.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            state.StateMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED if enable else 0

            PROCESS_SET_INFORMATION = 0x0200
            h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, os.getpid())
            if not h_proc:
                return False
            try:
                res = ctypes.windll.kernel32.SetProcessInformation(
                    h_proc,
                    ProcessPowerThrottling,
                    ctypes.byref(state),
                    ctypes.sizeof(state),
                )
                return bool(res)
            finally:
                ctypes.windll.kernel32.CloseHandle(h_proc)
        except Exception:
            return False
    
    def get_system_load(self) -> SystemLoad:
        """Get current system load information."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk I/O (approximate based on current process)
            disk_io = psutil.disk_io_counters()
            disk_io_percent = 0.0
            if disk_io:
                # Simple heuristic based on disk usage
                disk_usage = psutil.disk_usage('/')
                disk_io_percent = min(100.0, (disk_usage.used / disk_usage.total) * 100)
            
            # Network I/O (approximate)
            network_io = psutil.net_io_counters()
            network_io_percent = 0.0  # Simplified for now
            
            # Load average (Unix systems only)
            load_average = None
            if hasattr(os, 'getloadavg'):
                try:
                    load_average = os.getloadavg()[0]  # 1-minute load average
                except OSError:
                    pass
            
            load = SystemLoad(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_io_percent=disk_io_percent,
                network_io_percent=network_io_percent,
                load_average=load_average
            )
            
            with self._load_lock:
                self._last_load = load
            
            return load
            
        except Exception:
            # Return safe defaults if monitoring fails
            return SystemLoad(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_io_percent=0.0,
                network_io_percent=0.0
            )
    
    def throttle_if_needed(self) -> None:
        """Apply throttling if system resources are constrained."""
        load = self.get_system_load()
        
        should_throttle = (
            load.cpu_percent > self.cpu_limit or
            load.memory_percent > self.memory_limit
        )
        
        if should_throttle:
            if not self._throttle_active:
                self._throttle_active = True
                # Start with a small delay and increase if needed
                self._throttle_delay = 0.1
            else:
                # Increase throttle delay up to a maximum
                self._throttle_delay = min(1.0, self._throttle_delay * 1.2)
            
            # Apply throttling delay
            time.sleep(self._throttle_delay)
        else:
            if self._throttle_active:
                self._throttle_active = False
                self._throttle_delay = 0.0
    
    def adjust_thread_count(self, current_threads: int) -> int:
        """Adjust thread count based on system load."""
        load = self.get_system_load()
        
        # Get optimal thread count based on CPU cores
        cpu_count = psutil.cpu_count(logical=True)
        optimal_threads = min(cpu_count * 2, 32)  # Cap at 32 threads
        
        # Adjust based on system load
        if load.cpu_percent > self.cpu_limit:
            # High CPU load - reduce threads
            new_threads = max(1, current_threads - 1)
        elif load.memory_percent > self.memory_limit:
            # High memory load - reduce threads
            new_threads = max(1, current_threads - 2)
        elif load.cpu_percent < self.cpu_limit * 0.5 and load.memory_percent < self.memory_limit * 0.5:
            # Low load - can increase threads
            new_threads = min(optimal_threads, current_threads + 1)
        else:
            # Maintain current thread count
            new_threads = current_threads
        
        return new_threads
    
    def start_monitoring(self, interval: float = 1.0) -> None:
        """Start continuous system monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        
        def monitor_loop():
            """monitor_loop."""
            while self._monitoring:
                try:
                    self.get_system_load()
                    time.sleep(interval)
                except Exception:
                    # Continue monitoring even if individual checks fail
                    time.sleep(interval)
            """monitor_loop."""
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop continuous system monitoring."""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
    
    def get_cached_load(self) -> Optional[SystemLoad]:
        """Get the last cached system load without new measurement."""
        with self._load_lock:
            return self._last_load
    
    def is_throttling_active(self) -> bool:
        """Check if throttling is currently active."""
        return self._throttle_active
    
    def get_throttle_delay(self) -> float:
        """Get current throttling delay."""
        return self._throttle_delay
    
    def reset_throttling(self) -> None:
        """Reset throttling state."""
        self._throttle_active = False
        self._throttle_delay = 0.0
