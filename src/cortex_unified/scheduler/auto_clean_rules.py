"""Condition-triggered cleanup rules evaluated against live system state.

Each rule pairs a trigger (disk-usage threshold, lifecycle hook, schedule)
with a cleaning action; :meth:`AutoCleanRules.evaluate_rules` fires active
rules whose condition currently holds.
"""

import os
import platform
import subprocess
from typing import Dict
import threading
import time

from ..core.config import Config
from ..core.scanner import Scanner
from ..core.deleter import Deleter

class AutoCleanRules:
    """Registers rules, evaluates their triggers, dispatches actions."""
    
    def __init__(self, config: Config = None):
        """Build an empty rule set bound to a config.

        Args:
            config: Application config; defaults are built when omitted.
        """
        self.config = config or Config()
        self._lock = threading.Lock()
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            self.rules.append(rule)
            return len(self.rules) - 1
    
    def _check_disk_usage(self, threshold_percent: float) -> bool:
        """Check if disk usage exceeds threshold."""
        try:
            if self.system == "windows":
                # os.statvfs does not exist on Windows
                import shutil
                total, used, free = shutil.disk_usage("/")
            else:
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
        """Dispatch the rule's action to its matching handler."""
        try:
            if action == "clean_empty":
                self._clean_empty_files(clean_params)
            elif action == "clean_temp":
                self._clean_temp_files(clean_params)
            elif action == "clean_cache":
                self._clean_cache_files(clean_params)
            elif action == "custom":
                self._custom_clean_action(clean_params)
        except Exception:
            self.error_count += 1
    
    def _clean_empty_files(self, params: Dict):
        """_clean_empty_files."""
        try:
            path = params.get("path", ".")
            dry_run = params.get("dry_run", True)
            use_trash = params.get("use_trash", False)

            scanner = Scanner(self.config, path)
            empty_files, empty_dirs = scanner.scan()
            
            deleter = Deleter(dry_run, use_trash)
            result = deleter.delete(empty_files, empty_dirs)
            
            return result
        except Exception:
            self.error_count += 1
            return None
        """_clean_empty_files."""
    
    def _clean_temp_files(self, params: Dict):
        """Sweep low-risk categories through the engine's CleanerService.

        Uses the guarded, storage-aware engine scan rather than ad hoc
        deletion; dry runs only report what would be freed.
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
        """Find cache files, deleting them through Deleter unless dry-run.

        Discovery always runs; deletion defaults to trash so live runs remain
        reversible.
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
        """Run a caller-supplied command with the shell disabled.

        Requires explicit ``allow_command=True`` opt-in; arguments go through
        as a list (or shlex-split without a shell, so metacharacters stay
        literal) under a hard timeout. This closes the shell-injection hole of
        the former ``shell=True`` implementation.
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
        """Fire every active rule whose trigger currently holds.

        Only disk-usage rules are conditional. Startup/shutdown/scheduled rules
        have no OS event hooks here and run on every call; gate them by choosing
        when evaluate_rules is invoked (e.g. from TaskScheduler-created jobs).
        """
        with self._lock:
            rules_copy = list(self.rules)
        for rule in rules_copy:
            if not rule.get("active", False):
                continue
            
            try:
                if rule["type"] == "disk_usage":
                    if self._check_disk_usage(rule["threshold"]):
                        self._execute_clean_action(rule["action"], rule["clean_params"])
                
                elif rule["type"] == "startup":
                    self._execute_clean_action(rule["action"], rule["clean_params"])
                
                elif rule["type"] == "shutdown":
                    self._execute_clean_action(rule["action"], rule["clean_params"])
                
                elif rule["type"] == "scheduled":
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
        """stop_monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            self.monitor_thread = None
        """stop_monitoring."""
    
    def _monitor_loop(self, interval_seconds: int):
        """Poll evaluate_rules until stopped; errors never kill the loop."""
        while self.monitoring:
            try:
                self.evaluate_rules()
                time.sleep(interval_seconds)
            except Exception:
                self.error_count += 1
                time.sleep(interval_seconds)
    
    def get_stats(self) -> dict:
        """Summarize rule counts, monitor state, and error total."""
        with self._lock:
            rules_copy = list(self.rules)
        active_count = sum(1 for rule in rules_copy if rule.get("active", False))
        
        return {
            "total_rules": len(rules_copy),
            "active_rules": active_count,
            "monitoring": self.monitoring,
            "errors": self.error_count
        }
    
    def enable_rule(self, rule_index: int):
        """enable_rule."""
        with self._lock:
            if 0 <= rule_index < len(self.rules):
                self.rules[rule_index]["active"] = True
        """enable_rule."""
    
    def disable_rule(self, rule_index: int):
        """Disable rule."""
        with self._lock:
            if 0 <= rule_index < len(self.rules):
                self.rules[rule_index]["active"] = False
    
    def remove_rule(self, rule_index: int):
        """Remove rule."""
        with self._lock:
            if 0 <= rule_index < len(self.rules):
                del self.rules[rule_index]
