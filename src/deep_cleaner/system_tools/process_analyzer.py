"""Process and service analyzer for Deep Cleaner."""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import time

from ..utils import normalize_path
from ..config import Config


class ProcessAnalyzer:
    """Analyzer for system processes and services."""
    
    def __init__(self, config: Config = None):
        """Initialize process analyzer."""
        self.config = config or Config()
        self.system = platform.system().lower()
        
        # Results
        self.processes = []
        self.services = []
        self.high_resource_processes = []
        self.error_count = 0
    
    def list_processes(self) -> List[Dict]:
        """List all running processes."""
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
        """List Windows processes using tasklist."""
        try:
            # Use tasklist command to get process information
            cmd = ["tasklist", "/fo", "csv", "/v"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Parse CSV output
                    for line in lines[1:]:  # Skip header
                        # Remove quotes and split by comma
                        parts = [part.strip('"') for part in line.split('","')]
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
    
    def _list_macos_processes(self):
        """List macOS processes using ps."""
        try:
            # Use ps command to get process information
            cmd = ["ps", "aux"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Parse ps output
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
    
    def _list_linux_processes(self):
        """List Linux processes using ps."""
        try:
            # Use ps command to get process information
            cmd = ["ps", "aux"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Parse ps output
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
    
    def list_services(self) -> List[Dict]:
        """List system services."""
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
            # Use sc query command to get service information
            cmd = ["sc", "query"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse service information
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
                
                # Add last service
                if service_info:
                    self.services.append(service_info)
        except Exception:
            self.error_count += 1
    
    def _list_macos_services(self):
        """List macOS services using launchctl."""
        try:
            # Use launchctl list command to get service information
            cmd = ["launchctl", "list"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    # Parse launchctl output
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
    
    def _list_linux_services(self):
        """List Linux services using systemctl."""
        try:
            # Use systemctl list-units command to get service information
            cmd = ["systemctl", "list-units", "--type=service", "--no-pager"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Skip header lines and footer
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
        """Find processes with high CPU or memory usage."""
        self.high_resource_processes = []
        
        # First get all processes
        if not self.processes:
            self.list_processes()
        
        try:
            for process in self.processes:
                high_resource = False
                
                if self.system == "windows":
                    # Windows uses different format
                    # For simplicity, we'll skip detailed analysis on Windows
                    pass
                elif self.system in ["darwin", "linux"]:
                    # Check CPU and memory usage
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
                        # Skip if we can't parse percentages
                        pass
                
                if high_resource:
                    self.high_resource_processes.append(process)
        except Exception:
            self.error_count += 1
        
        return self.high_resource_processes
    
    def get_stats(self) -> dict:
        """Get statistics about processes and services."""
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
        """Filter processes by name pattern."""
        filtered = []
        for process in self.processes:
            if name_pattern.lower() in process.get("name", "").lower():
                filtered.append(process)
        return filtered
    
    def filter_services_by_state(self, state: str) -> List[Dict]:
        """Filter services by state."""
        filtered = []
        for service in self.services:
            if state.lower() in service.get("state", "").lower():
                filtered.append(service)
        return filtered