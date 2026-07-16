"""Task scheduler for Cortex Cleaner."""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

from ..core.utils import normalize_path
from ..core.config import Config

class TaskScheduler:
    """Scheduler for automatic cleanup tasks."""
    
    def __init__(self, config: Config = None):
        """Initialize task scheduler."""
        self.config = config or Config()
        self.system = platform.system().lower()
        self.scheduled_tasks = []
        self.error_count = 0
    
    def create_scheduled_task(
        self, 
        name: str, 
        command: str, 
        schedule_type: str, 
        schedule_params: Dict = None
    ) -> bool:
        """Create a scheduled task.
        
        Args:
            name: Name of the task
            command: Command to execute
            schedule_type: Type of schedule ("once", "daily", "weekly", "monthly")
            schedule_params: Additional parameters for scheduling
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.system == "windows":
                return self._create_windows_task(name, command, schedule_type, schedule_params)
            elif self.system == "darwin":  # macOS
                return self._create_macos_task(name, command, schedule_type, schedule_params)
            elif self.system == "linux":
                return self._create_linux_task(name, command, schedule_type, schedule_params)
            else:
                self.error_count += 1
                return False
        except Exception:
            self.error_count += 1
            return False
    
    def _create_windows_task(
        self, 
        name: str, 
        command: str, 
        schedule_type: str, 
        schedule_params: Dict = None
    ) -> bool:
        """Create a Windows scheduled task using schtasks."""
        try:
            schedule_params = schedule_params or {}
            
            # Build schtasks command
            cmd = ["schtasks", "/create", "/tn", name, "/tr", command]
            
            # Add schedule parameters
            if schedule_type == "once":
                run_time = schedule_params.get("time", "02:00")
                cmd.extend(["/sc", "once", "/st", run_time])
            elif schedule_type == "daily":
                run_time = schedule_params.get("time", "02:00")
                cmd.extend(["/sc", "daily", "/st", run_time])
            elif schedule_type == "weekly":
                run_time = schedule_params.get("time", "02:00")
                days = schedule_params.get("days", "MON")
                cmd.extend(["/sc", "weekly", "/d", days, "/st", run_time])
            elif schedule_type == "monthly":
                run_time = schedule_params.get("time", "02:00")
                days = schedule_params.get("days", "1")
                cmd.extend(["/sc", "monthly", "/d", days, "/st", run_time])
            else:
                self.error_count += 1
                return False
            
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            self.error_count += 1
            return False
    
    def _create_macos_task(
        self, 
        name: str, 
        command: str, 
        schedule_type: str, 
        schedule_params: Dict = None
    ) -> bool:
        """Create a macOS scheduled task using launchd."""
        try:
            # Create a plist file for launchd
            plist_content = self._generate_launchd_plist(name, command, schedule_type, schedule_params)
            
            # Write plist to ~/Library/LaunchAgents
            plist_dir = Path.home() / "Library" / "LaunchAgents"
            plist_dir.mkdir(parents=True, exist_ok=True)
            
            plist_file = plist_dir / f"com.deepcleaner.{name}.plist"
            with open(plist_file, 'w') as f:
                f.write(plist_content)
            
            # Load the job
            cmd = ["launchctl", "load", str(plist_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            self.error_count += 1
            return False
    
    def _generate_launchd_plist(
        self, 
        name: str, 
        command: str, 
        schedule_type: str, 
        schedule_params: Dict = None
    ) -> str:
        """Generate a launchd plist file."""
        schedule_params = schedule_params or {}
        
        # Start building the plist
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.deepcleaner.{name}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>{command}</string>
    </array>
    
    <key>RunAtLoad</key>
    <false/>"""
        
        # Add scheduling information
        if schedule_type == "daily":
            hour = schedule_params.get("hour", 2)
            minute = schedule_params.get("minute", 0)
            plist += f"""
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>"""
        elif schedule_type == "weekly":
            hour = schedule_params.get("hour", 2)
            minute = schedule_params.get("minute", 0)
            weekday = schedule_params.get("weekday", 1)  # 1=Sunday, 2=Monday, etc.
            plist += f"""
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
        <key>Weekday</key>
        <integer>{weekday}</integer>
    </dict>"""
        elif schedule_type == "monthly":
            hour = schedule_params.get("hour", 2)
            minute = schedule_params.get("minute", 0)
            day = schedule_params.get("day", 1)
            plist += f"""
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
        <key>Day</key>
        <integer>{day}</integer>
    </dict>"""
        
        # End the plist
        plist += """
</dict>
</plist>"""
        
        return plist
    
    def _create_linux_task(
        self, 
        name: str, 
        command: str, 
        schedule_type: str, 
        schedule_params: Dict = None
    ) -> bool:
        """Create a Linux scheduled task using cron."""
        try:
            # Generate cron expression
            cron_expression = self._generate_cron_expression(schedule_type, schedule_params)
            
            # Create the full cron entry
            cron_entry = f"{cron_expression} {command} # DeepCleaner task: {name}"
            
            # First, get current crontab
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            
            # Add our entry
            current_crontab = result.stdout if result.returncode == 0 else ""
            new_crontab = current_crontab + "\n" + cron_entry + "\n"
            
            # Write back to crontab
            cmd = ["crontab", "-"]
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_crontab)
            
            return process.returncode == 0
        except Exception:
            self.error_count += 1
            return False
    
    def _generate_cron_expression(self, schedule_type: str, schedule_params: Dict = None) -> str:
        """Generate a cron expression."""
        schedule_params = schedule_params or {}
        
        if schedule_type == "daily":
            hour = schedule_params.get("hour", 2)
            minute = schedule_params.get("minute", 0)
            return f"{minute} {hour} * * *"
        elif schedule_type == "weekly":
            hour = schedule_params.get("hour", 2)
            minute = schedule_params.get("minute", 0)
            weekday = schedule_params.get("weekday", 1)  # 1=Monday, 0=Sunday
            return f"{minute} {hour} * * {weekday}"
        elif schedule_type == "monthly":
            hour = schedule_params.get("hour", 2)
            minute = schedule_params.get("minute", 0)
            day = schedule_params.get("day", 1)
            return f"{minute} {hour} {day} * *"
        else:  # once (run at next opportunity)
            return f"* * * * *"
    
    def list_scheduled_tasks(self) -> List[Dict]:
        """List all scheduled tasks."""
        try:
            if self.system == "windows":
                return self._list_windows_tasks()
            elif self.system == "darwin":  # macOS
                return self._list_macos_tasks()
            elif self.system == "linux":
                return self._list_linux_tasks()
            else:
                self.error_count += 1
                return []
        except Exception:
            self.error_count += 1
            return []
    
    def _list_windows_tasks(self) -> List[Dict]:
        """List Windows scheduled tasks."""
        try:
            cmd = ["schtasks", "/query", "/fo", "csv"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    tasks = []
                    for line in lines[1:]:  # Skip header
                        parts = [part.strip('"') for part in line.split('","')]
                        if len(parts) >= 3:
                            tasks.append({
                                "name": parts[0],
                                "next_run_time": parts[1],
                                "status": parts[2]
                            })
                    return tasks
            return []
        except Exception:
            self.error_count += 1
            return []
    
    def _list_macos_tasks(self) -> List[Dict]:
        """List macOS scheduled tasks."""
        try:
            cmd = ["launchctl", "list"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    tasks = []
                    for line in lines[1:]:  # Skip header
                        parts = line.split()
                        if len(parts) >= 3:
                            tasks.append({
                                "pid": parts[0],
                                "last_exit_code": parts[1],
                                "label": parts[2]
                            })
                    return tasks
            return []
        except Exception:
            self.error_count += 1
            return []
    
    def _list_linux_tasks(self) -> List[Dict]:
        """List Linux scheduled tasks."""
        try:
            cmd = ["crontab", "-l"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                tasks = []
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        # This is a crude parsing - in reality, you'd want to parse the cron expression
                        tasks.append({
                            "schedule": line.split(' ', 5)[0:5],
                            "command": line.split(' ', 5)[5] if len(line.split(' ', 5)) > 5 else line
                        })
                return tasks
            return []
        except Exception:
            self.error_count += 1
            return []
    
    def delete_scheduled_task(self, name: str) -> bool:
        """Delete a scheduled task."""
        try:
            if self.system == "windows":
                cmd = ["schtasks", "/delete", "/tn", name, "/f"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            elif self.system == "darwin":  # macOS
                # Remove the plist file
                plist_file = Path.home() / "Library" / "LaunchAgents" / f"com.deepcleaner.{name}.plist"
                if plist_file.exists():
                    plist_file.unlink()
                    # Unload the job
                    cmd = ["launchctl", "unload", str(plist_file)]
                    subprocess.run(cmd, capture_output=True, text=True)
                return True
            elif self.system == "linux":
                # Remove from crontab
                result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    new_lines = [line for line in lines if f"DeepCleaner task: {name}" not in line]
                    new_crontab = "\n".join(new_lines) + ("\n" if new_lines else "")
                    cmd = ["crontab", "-"]
                    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, text=True)
                    process.communicate(input=new_crontab)
                    return process.returncode == 0
                return False
            else:
                self.error_count += 1
                return False
        except Exception:
            self.error_count += 1
            return False
    
    def get_stats(self) -> dict:
        """Get statistics about scheduled tasks."""
        tasks = self.list_scheduled_tasks()
        
        return {
            "total_scheduled_tasks": len(tasks),
            "system_type": self.system,
            "errors": self.error_count
        }