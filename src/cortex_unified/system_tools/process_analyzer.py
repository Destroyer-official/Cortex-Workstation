"""Process and service enumeration via platform CLI tools.

Wraps ``tasklist``/``sc`` on Windows and ``ps``/``launchctl``/``systemctl``
elsewhere, parsing their text output into plain dicts. Parsing is deliberately
tolerant: per-line failures increment ``error_count`` instead of aborting the
listing, because partial data still serves a diagnostics view.
"""

import csv
import platform
import subprocess
from typing import List, Dict

from ..core.config import Config

class ProcessAnalyzer:
    """Enumerate running processes/services and flag high-resource consumers."""

    def __init__(self, config: Config = None):
        """Use *config* or a default Config; the OS decides which backends run."""
        self.config = config or Config()
        self.system = platform.system().lower()

        self.processes = []
        self.services = []
        self.high_resource_processes = []
        self.error_count = 0

    def list_processes(self) -> List[Dict]:
        """Populate ``processes`` from the platform's process listing."""
        self.processes = []
        self.error_count = 0
        
        try:
            if self.system == "windows":
                self._list_windows_processes()
            elif self.system == "darwin":  # macOS
                self._list_macos_processes()
            elif self.system == "linux":
                self._list_linux_processes()
        except Exception:
            self.error_count += 1
        
        return self.processes
    
    def _list_windows_processes(self):
        try:
            cmd = ["tasklist", "/fo", "csv", "/v"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                reader = csv.reader(result.stdout.splitlines())
                rows = list(reader)
                if len(rows) > 1:
                    for parts in rows[1:]:  # Skip header
                        if len(parts) >= 8:
                            self.processes.append({
                                "pid": parts[1],
                                "name": parts[0],
                                "session_name": parts[2],
                                "session_num": parts[3],
                                "mem_usage": parts[4],
                                "status": parts[5],
                                "username": parts[6],
                                "cpu_time": parts[7],
                                "window_title": parts[8] if len(parts) > 8 else ""
                            })
        except Exception:
            self.error_count += 1
        """_list_windows_processes."""
        """_list_windows_processes."""
    
    def _list_macos_processes(self):
        try:
            cmd = ["ps", "aux"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    for line in lines[1:]:  # Skip header
                        parts = line.split(None, 10)
                        if len(parts) >= 11:
                            self.processes.append({
                                "user": parts[0],
                                "pid": parts[1],
                                "cpu_percent": parts[2],
                                "mem_percent": parts[3],
                                "vsz": parts[4],
                                "rss": parts[5],
                                "tt": parts[6],
                                "stat": parts[7],
                                "started": parts[8],
                                "time": parts[9],
                                "command": parts[10]
                            })
        except Exception:
            self.error_count += 1
        """_list_macos_processes."""
        """_list_macos_processes."""
    
    def _list_linux_processes(self):
        try:
            cmd = ["ps", "aux"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    for line in lines[1:]:  # Skip header
                        parts = line.split(None, 10)
                        if len(parts) >= 11:
                            self.processes.append({
                                "user": parts[0],
                                "pid": parts[1],
                                "cpu_percent": parts[2],
                                "mem_percent": parts[3],
                                "vsz": parts[4],
                                "rss": parts[5],
                                "tty": parts[6],
                                "stat": parts[7],
                                "started": parts[8],
                                "time": parts[9],
                                "command": parts[10]
                            })
        except Exception:
            self.error_count += 1
        """_list_linux_processes."""
        """_list_linux_processes."""
    
    def list_services(self) -> List[Dict]:
        """Populate ``services`` from the platform's service listing."""
        self.services = []
        self.error_count = 0
        
        try:
            if self.system == "windows":
                self._list_windows_services()
            elif self.system == "darwin":  # macOS
                self._list_macos_services()
            elif self.system == "linux":
                self._list_linux_services()
        except Exception:
            self.error_count += 1
        
        return self.services
    
    def _list_windows_services(self):
        """List Windows services using sc query."""
        try:
            cmd = ["sc", "query"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                service_info = {}
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith("SERVICE_NAME:"):
                        if service_info:
                            self.services.append(service_info)
                            service_info = {}
                        service_info["name"] = line.split(":")[1].strip()
                    elif line.startswith("DISPLAY_NAME:"):
                        service_info["display_name"] = line.split(":")[1].strip()
                    elif line.startswith("STATE"):
                        # Extract state from format like "STATE : 1 STOPPED"
                        parts = line.split(":")
                        if len(parts) >= 3:
                            service_info["state"] = parts[2].strip()
                    elif line.startswith("WIN32_EXIT_CODE"):
                        service_info["exit_code"] = line.split(":")[1].strip()
                
                # Flush the final service record after the loop.
                if service_info:
                    self.services.append(service_info)
        except Exception:
            self.error_count += 1
    
    def _list_macos_services(self):
        try:
            cmd = ["launchctl", "list"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    for line in lines[1:]:  # Skip header
                        parts = line.split()
                        if len(parts) >= 3:
                            self.services.append({
                                "pid": parts[0],
                                "last_exit_code": parts[1],
                                "label": parts[2]
                            })
        except Exception:
            self.error_count += 1
        """_list_macos_services."""
        """_list_macos_services."""
    
    def _list_linux_services(self):
        """List Linux services using systemctl, falling back to ``service``."""
        try:
            cmd = ["systemctl", "list-units", "--type=service", "--no-pager"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Drop the header line and systemctl's trailing blank/summary lines.
                for line in lines[1:-6]:
                    parts = line.split(None, 4)
                    if len(parts) >= 5:
                        self.services.append({
                            "unit": parts[0],
                            "load": parts[1],
                            "active": parts[2],
                            "sub": parts[3],
                            "description": parts[4]
                        })
        except Exception:
            # Fallback to service command
            try:
                cmd = ["service", "--status-all"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            self.services.append({
                                "service": line.strip()
                            })
            except Exception:
                self.error_count += 1
    
    def find_high_resource_processes(self, cpu_threshold: float = 50.0, mem_threshold: float = 50.0) -> List[Dict]:
        """Flag processes at or above the CPU/memory percentage thresholds."""
        self.high_resource_processes = []
        
        if not self.processes:
            self.list_processes()
        
        try:
            for process in self.processes:
                high_resource = False
                
                if self.system == "windows":
                    # tasklist /v reports memory strings and CPU time, not
                    # instantaneous percentages, so thresholding here is
                    # impossible without a second sampling source.
                    pass
                elif self.system in ["darwin", "linux"]:
                    try:
                        cpu_percent = float(process.get("cpu_percent", 0))
                        mem_percent = float(process.get("mem_percent", 0))
                        
                        if cpu_percent >= cpu_threshold or mem_percent >= mem_threshold:
                            high_resource = True
                            process["high_resource_reason"] = []
                            if cpu_percent >= cpu_threshold:
                                process["high_resource_reason"].append(f"CPU: {cpu_percent}%")
                            if mem_percent >= mem_threshold:
                                process["high_resource_reason"].append(f"Memory: {mem_percent}%")
                    except ValueError:
                        # ps prints "-" for unavailable percentages.
                        pass
                
                if high_resource:
                    self.high_resource_processes.append(process)
        except Exception:
            self.error_count += 1
        
        return self.high_resource_processes
    
    def get_stats(self) -> dict:
        """Snapshot counts for UI display."""
        total_processes = len(self.processes)
        total_services = len(self.services)
        high_resource_count = len(self.high_resource_processes)
        
        return {
            "total_processes": total_processes,
            "total_services": total_services,
            "high_resource_processes": high_resource_count,
            "system_type": self.system,
            "errors": self.error_count
        }
    
    def filter_processes_by_name(self, name_pattern: str) -> List[Dict]:
        """Case-insensitive substring match on process name."""
        filtered = []
        for process in self.processes:
            if name_pattern.lower() in process.get("name", "").lower():
                filtered.append(process)
        return filtered
    
    def filter_services_by_state(self, state: str) -> List[Dict]:
        """Case-insensitive substring match on service state."""
        filtered = []
        for service in self.services:
            if state.lower() in service.get("state", "").lower():
                filtered.append(service)
        return filtered