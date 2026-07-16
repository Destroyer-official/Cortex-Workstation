"""Auto-clean rules for Cortex Cleaner."""

import os
import platform
import subprocess
from pathlib import Path
from typing import List, Dict, Callable
from datetime import datetime, timedelta
import json
import threading
import time

from ..core.utils import normalize_path
from ..core.config import Config
from ..core.scanner import Scanner
from ..core.deleter import Deleter

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
        """Clean temporary files via the safe engine category scanner.

        Previously imported a non-existent ``temp_cleaner`` module and, even in
        non-dry-run mode, deleted nothing (``pass``). Now it uses the real
        engine ``CleanerService`` so the action actually functions and stays
        guarded/storage-aware.
        """
        try:
            from ..engine import CleanerService, DeletionMethod, RiskLevel

            dry_run = params.get("dry_run", True)
            svc = CleanerService()
            report = svc.scan_categories(max_risk=RiskLevel.LOW)
            method = DeletionMethod.DRY_RUN if dry_run else DeletionMethod.RECYCLE
            results = svc.clean_categories(report, method)
            freed = sum(r.size for r in results
                        if r.succeeded and r.method is not DeletionMethod.DRY_RUN)
            return {
                "temp_files_found": report.total_files,
                "bytes_freed": freed,
                "dry_run": dry_run,
            }
        except Exception:
            self.error_count += 1
            return None

    def _clean_cache_files(self, params: Dict):
        """Clean cache files - now actually deletes via Deleter when not dry-run.

        The previous implementation found cache files but left a ``pass`` in the
        delete branch, so nothing was ever removed even outside dry-run mode.
        """
        try:
            from ..analyzers.cache_cleaner import CacheCleaner

            cleaner = CacheCleaner(self.config)
            cache_files, cache_dirs = cleaner.find_cache_files()

            dry_run = params.get("dry_run", True)
            use_trash = params.get("use_trash", True)  # default to reversible

            freed = 0
            if not dry_run:
                deleter = Deleter(dry_run=False, use_trash=use_trash)
                result = deleter.delete(cache_files, cache_dirs)
                freed = result.get("total_deleted", 0)

            return {
                "cache_files_found": len(cache_files),
                "cache_dirs_found": len(cache_dirs),
                "deleted": freed,
                "dry_run": dry_run,
            }
        except Exception:
            self.error_count += 1
            return None

    def _custom_clean_action(self, params: Dict):
        """Execute a custom cleaning command WITHOUT a shell.

        Security fix: the old implementation used ``subprocess.run(command,
        shell=True)`` on a caller-supplied string, which allowed shell
        metacharacter injection (``&``, ``|``, ``;``, ``$()`` ...). We now:
          * require an explicit ``allow_command`` opt-in flag;
          * accept an argument *list* (preferred) or split a string safely with
            ``shlex`` (no shell), so metacharacters are treated literally;
          * enforce a timeout.
        """
        try:
            if not params.get("allow_command", False):
                return {"error": "custom command execution is disabled "
                                 "(set allow_command=True to enable)"}

            command = params.get("command")
            if not command:
                return None

            if isinstance(command, (list, tuple)):
                argv = list(command)
            else:
                import shlex
                # posix=False keeps Windows path backslashes intact.
                argv = shlex.split(str(command), posix=(self.system != "windows"))
            if not argv:
                return None

            result = subprocess.run(
                argv, shell=False, capture_output=True, text=True,
                timeout=params.get("timeout", 120),
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
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