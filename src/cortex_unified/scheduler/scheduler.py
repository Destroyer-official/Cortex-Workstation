"""OS-native scheduling for cleanup jobs: schtasks, launchd, cron.

Jobs are registered with whatever scheduler the host OS provides, so they run
without this process being alive and survive reboots.
"""

import csv
import io
import platform
import re
import xml.sax.saxutils
from pathlib import Path
from typing import List, Dict

from ..core import proc as _proc
from ..core.config import Config

class TaskScheduler:
    """Creates, lists, and removes cleanup jobs in the OS-native scheduler."""
    
    def __init__(self, config: Config = None):
        """Detect the host OS and prepare task tracking.

        Args:
            config: Application config; defaults are built when omitted.
        """
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
        """Register ``command`` under ``name`` with the platform scheduler.
        
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
            
            if not re.match(r'^[A-Za-z0-9_\- ]+$', name):
                self.error_count += 1
                return False

            cmd = ["schtasks", "/create", "/tn", name, "/tr", command]

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
            
            result = _proc.run(cmd, text=True, timeout=30)
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
            plist_content = self._generate_launchd_plist(name, command, schedule_type, schedule_params)

            plist_dir = Path.home() / "Library" / "LaunchAgents"
            plist_dir.mkdir(parents=True, exist_ok=True)
            
            plist_file = plist_dir / f"com.deepcleaner.{name}.plist"
            with open(plist_file, 'w', encoding='utf-8') as f:
                f.write(plist_content)
            
            cmd = ["launchctl", "load", str(plist_file)]
            result = _proc.run(cmd, text=True, timeout=30)
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
        """Render schedule params as a launchd property-list string."""
        schedule_params = schedule_params or {}
        
        escaped_name = xml.sax.saxutils.escape(name)
        escaped_command = xml.sax.saxutils.escape(command)

        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.deepcleaner.{escaped_name}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>{escaped_command}</string>
    </array>
    
    <key>RunAtLoad</key>
    <false/>"""
        
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
            command = command.replace('\n', '').replace('\r', '')

            cron_expression = self._generate_cron_expression(schedule_type, schedule_params)

            cron_entry = f"{cron_expression} {command} # DeepCleaner task: {name}"

            # crontab installs wholesale, so start from the existing table
            result = _proc.run(["crontab", "-l"], text=True, timeout=15)

            current_crontab = result.stdout if result.returncode == 0 else ""
            new_crontab = current_crontab + "\n" + cron_entry + "\n"

            # "-" reads the replacement table from stdin
            cmd = ["crontab", "-"]
            result = _proc.run(cmd, text=True, timeout=15, input=new_crontab)
            
            return result.returncode == 0
        except Exception:
            self.error_count += 1
            return False
    
    def _generate_cron_expression(self, schedule_type: str, schedule_params: Dict = None) -> str:
        """Translate schedule type/params into five cron fields."""
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
        """List tasks from the platform scheduler in normalized dicts."""
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
            result = _proc.run(cmd, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    tasks = []
                    reader = csv.reader(io.StringIO(result.stdout))
                    next(reader)
                    for row in reader:
                        if len(row) >= 3:
                            tasks.append({
                                "name": row[0],
                                "next_run_time": row[1],
                                "status": row[2]
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
            result = _proc.run(cmd, text=True, timeout=30)
            
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
            result = _proc.run(cmd, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                tasks = []
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        # Fields only; cron expressions are not interpreted
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
        try:
            if self.system == "windows":
                cmd = ["schtasks", "/delete", "/tn", name, "/f"]
                result = _proc.run(cmd, text=True, timeout=30)
                return result.returncode == 0
            elif self.system == "darwin":  # macOS
                plist_file = Path.home() / "Library" / "LaunchAgents" / f"com.deepcleaner.{name}.plist"
                if plist_file.exists():
                    cmd = ["launchctl", "unload", str(plist_file)]
                    _proc.run(cmd, text=True, timeout=15)
                    plist_file.unlink()
                return True
            elif self.system == "linux":
                result = _proc.run(["crontab", "-l"], text=True, timeout=15)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    new_lines = [line for line in lines if f"DeepCleaner task: {name}" not in line]
                    new_crontab = "\n".join(new_lines) + ("\n" if new_lines else "")
                    cmd = ["crontab", "-"]
                    result = _proc.run(cmd, text=True, timeout=15, input=new_crontab)
                    return result.returncode == 0
                return False
            else:
                self.error_count += 1
                return False
        except Exception:
            self.error_count += 1
            return False
        """delete_scheduled_task."""
    
    def get_stats(self) -> dict:
        """Summarize task count, platform, and error total."""
        tasks = self.list_scheduled_tasks()
        
        return {
            "total_scheduled_tasks": len(tasks),
            "system_type": self.system,
            "errors": self.error_count
        }