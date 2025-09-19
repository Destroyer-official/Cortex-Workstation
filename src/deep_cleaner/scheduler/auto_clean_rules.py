"""Auto-clean rules for Deep Cleaner."""

import os
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Callable
from datetime import datetime, timedelta
import json
import threading
import time

from ..utils import normalize_path
from ..config import Config
from ..scanner import Scanner
from ..deleter import Deleter


class AutoCleanRules:
    """Auto-clean rules engine for automatic cleanup."""
    
    def __init__(self, config: Config = None):
        """Initialize auto-clean rules engine."""
        self.config = config or Config()
        self.rules = []
        self.active_rules = []
        self.system = platform.system().lower()
        self.monitoring = False
        self.monitor_thread = None
        self.error_count = 0
    
    def add_disk_usage_rule(
        self, 
        threshold_percent: float, 
        action: str = "clean_empty",
        clean_params: Dict = None
    ):
        """Add a rule to clean when disk usage exceeds threshold.
        
        Args:
            threshold_percent: Disk usage percentage threshold (0-100)
            action: Action to take ("clean_empty", "clean_temp", "clean_cache", "custom")
            clean_params: Parameters for the cleaning action
        """
        rule = {
            "type": "disk_usage",
            "threshold": threshold_percent,
            "action": action,
            "clean_params": clean_params or {},
            "active": True
        }
        self.rules.append(rule)
        return len(self.rules) - 1
    
    def add_startup_rule(
        self, 
        action: str = "clean_empty",
        clean_params: Dict = None
    ):
        """Add a rule to clean at system startup.
        
        Args:
            action: Action to take ("clean_empty", "clean_temp", "clean_cache", "custom")
            clean_params: Parameters for the cleaning action
        """
        rule = {
            "type": "startup",
            "action": action,
            "clean_params": clean_params or {},
            "active": True
        }
        self.rules.append(rule)
        return len(self.rules) - 1
    
    def add_shutdown_rule(
        self, 
        action: str = "clean_empty",
        clean_params: Dict = None
    ):
        """Add a rule to clean at system shutdown.
        
        Args:
            action: Action to take ("clean_empty", "clean_temp", "clean_cache", "custom")
            clean_params: Parameters for the cleaning action
        """
        rule = {
            "type": "shutdown",
            "action": action,
            "clean_params": clean_params or {},
            "active": True
        }
        self.rules.append(rule)
        return len(self.rules) - 1
    
    def add_scheduled_rule(
        self, 
        schedule_type: str,
        schedule_params: Dict,
        action: str = "clean_empty",
        clean_params: Dict = None
    ):
        """Add a scheduled rule.
        
        Args:
            schedule_type: Type of schedule ("daily", "weekly", "monthly")
            schedule_params: Schedule parameters
            action: Action to take ("clean_empty", "clean_temp", "clean_cache", "custom")
            clean_params: Parameters for the cleaning action
        """
        rule = {
            "type": "scheduled",
            "schedule_type": schedule_type,
            "schedule_params": schedule_params,
            "action": action,
            "clean_params": clean_params or {},
            "active": True
        }
        self.rules.append(rule)
        return len(self.rules) - 1
    
    def _check_disk_usage(self, threshold_percent: float) -> bool:
        """Check if disk usage exceeds threshold."""
        try:
            # Get disk usage
            if self.system == "windows":
                # Use Windows-specific method
                import shutil
                total, used, free = shutil.disk_usage("/")
            else:
                # Use POSIX method
                statvfs = os.statvfs("/")
                total = statvfs.f_frsize * statvfs.f_blocks
                free = statvfs.f_frsize * statvfs.f_bavail
                used = total - free
            
            used_percent = (used / total * 100) if total > 0 else 0
            return used_percent >= threshold_percent
        except Exception:
            self.error_count += 1
            return False
    
    def _execute_clean_action(self, action: str, clean_params: Dict):
        """Execute a cleaning action."""
        try:
            if action == "clean_empty":
                # Clean empty files and folders
                self._clean_empty_files(clean_params)
            elif action == "clean_temp":
                # Clean temporary files
                self._clean_temp_files(clean_params)
            elif action == "clean_cache":
                # Clean cache files
                self._clean_cache_files(clean_params)
            elif action == "custom":
                # Custom cleaning action
                self._custom_clean_action(clean_params)
        except Exception:
            self.error_count += 1
    
    def _clean_empty_files(self, params: Dict):
        """Clean empty files and folders."""
        try:
            # Get parameters
            path = params.get("path", ".")
            dry_run = params.get("dry_run", True)
            use_trash = params.get("use_trash", False)
            
            # Create scanner and deleter
            scanner = Scanner(self.config, path)
            empty_files, empty_dirs = scanner.scan()
            
            deleter = Deleter(dry_run, use_trash)
            result = deleter.delete(empty_files, empty_dirs)
            
            return result
        except Exception:
            self.error_count += 1
            return None
    
    def _clean_temp_files(self, params: Dict):
        """Clean temporary files."""
        # This would integrate with the temp cleaner
        try:
            from ..analyzers.temp_cleaner import TempCleaner
            cleaner = TempCleaner(self.config)
            temp_files = cleaner.find_temp_files()
            
            # Delete files if not in dry run mode
            dry_run = params.get("dry_run", True)
            use_trash = params.get("use_trash", False)
            
            if not dry_run:
                deleter = Deleter(dry_run, use_trash)
                # For temp files, we would need to adapt the deleter interface
                # This is a simplified implementation
                pass
            
            return {"temp_files_found": len(temp_files)}
        except Exception:
            self.error_count += 1
            return None
    
    def _clean_cache_files(self, params: Dict):
        """Clean cache files."""
        # This would integrate with the cache cleaner
        try:
            from ..analyzers.cache_cleaner import CacheCleaner
            cleaner = CacheCleaner(self.config)
            cache_files, cache_dirs = cleaner.find_cache_files()
            
            # Delete files if not in dry run mode
            dry_run = params.get("dry_run", True)
            use_trash = params.get("use_trash", False)
            
            if not dry_run:
                deleter = Deleter(dry_run, use_trash)
                # For cache files, we would need to adapt the deleter interface
                # This is a simplified implementation
                pass
            
            return {"cache_files_found": len(cache_files), "cache_dirs_found": len(cache_dirs)}
        except Exception:
            self.error_count += 1
            return None
    
    def _custom_clean_action(self, params: Dict):
        """Execute a custom cleaning action."""
        # This would execute a custom command or script
        try:
            command = params.get("command")
            if command:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                return {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
        except Exception:
            self.error_count += 1
            return None
    
    def evaluate_rules(self):
        """Evaluate all active rules and execute actions if conditions are met."""
        for rule in self.rules:
            if not rule.get("active", False):
                continue
            
            try:
                # Evaluate rule based on type
                if rule["type"] == "disk_usage":
                    if self._check_disk_usage(rule["threshold"]):
                        self._execute_clean_action(rule["action"], rule["clean_params"])
                
                elif rule["type"] == "startup":
                    # This would be triggered at startup
                    # For now, we'll just execute it if called
                    self._execute_clean_action(rule["action"], rule["clean_params"])
                
                elif rule["type"] == "shutdown":
                    # This would be triggered at shutdown
                    # For now, we'll just execute it if called
                    self._execute_clean_action(rule["action"], rule["clean_params"])
                
                elif rule["type"] == "scheduled":
                    # Scheduled rules would be handled by the scheduler
                    # For now, we'll just execute it if called
                    self._execute_clean_action(rule["action"], rule["clean_params"])
                    
            except Exception:
                self.error_count += 1
    
    def start_monitoring(self, interval_seconds: int = 60):
        """Start monitoring disk usage in a background thread.
        
        Args:
            interval_seconds: Check interval in seconds
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring disk usage."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.monitor_thread = None
    
    def _monitor_loop(self, interval_seconds: int):
        """Monitoring loop that runs in a background thread."""
        while self.monitoring:
            try:
                self.evaluate_rules()
                time.sleep(interval_seconds)
            except Exception:
                self.error_count += 1
                # Continue monitoring even if there's an error
                time.sleep(interval_seconds)
    
    def get_stats(self) -> dict:
        """Get statistics about auto-clean rules."""
        active_count = sum(1 for rule in self.rules if rule.get("active", False))
        
        return {
            "total_rules": len(self.rules),
            "active_rules": active_count,
            "monitoring": self.monitoring,
            "errors": self.error_count
        }
    
    def enable_rule(self, rule_index: int):
        """Enable a rule."""
        if 0 <= rule_index < len(self.rules):
            self.rules[rule_index]["active"] = True
    
    def disable_rule(self, rule_index: int):
        """Disable a rule."""
        if 0 <= rule_index < len(self.rules):
            self.rules[rule_index]["active"] = False
    
    def remove_rule(self, rule_index: int):
        """Remove a rule."""
        if 0 <= rule_index < len(self.rules):
            del self.rules[rule_index]