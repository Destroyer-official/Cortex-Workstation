"""Configuration management for Deep Cleaner."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Any
import yaml


class Config:
    """Configuration class for Deep Cleaner."""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration."""
        self.config_path = config_path or self._get_default_config_path()
        self.config_data = self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        home = Path.home()
        return str(home / ".deepcleaner.yaml")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            # If we can't load the config, return empty dict
            return {}
    
    @property
    def exclude_patterns(self) -> List[str]:
        """Get exclude patterns from config."""
        return self.config_data.get("exclude_patterns", [])
    
    @property
    def exclude_dirs(self) -> List[str]:
        """Get exclude directories from config."""
        return self.config_data.get("exclude_dirs", [])
    
    @property
    def exclude_regex_patterns(self) -> List[str]:
        """Get exclude regex patterns from config."""
        return self.config_data.get("exclude_regex_patterns", [])
    
    @property
    def min_age_days(self) -> int:
        """Get minimum age in days."""
        return self.config_data.get("min_age_days", 0)
    
    @property
    def default_action(self) -> str:
        """Get default action."""
        return self.config_data.get("default_action", "dry_run")
    
    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self.config_data.get("log_file", "")
    
    @property
    def json_logging(self) -> bool:
        """Get JSON logging flag."""
        return self.config_data.get("json_logging", False)
    
    @property
    def threads(self) -> int:
        """Get number of threads."""
        return self.config_data.get("threads", 0)  # 0 means use CPU count
    
    @property
    def follow_symlinks(self) -> bool:
        """Get follow symlinks flag."""
        return self.config_data.get("follow_symlinks", False)
    
    def matches_exclude_patterns(self, path: str) -> bool:
        """Check if a path matches any exclude patterns (glob or regex)."""
        from fnmatch import fnmatch
        
        path_obj = Path(path)
        
        # Check glob patterns
        for pattern in self.exclude_patterns:
            if fnmatch(path, pattern) or fnmatch(path_obj.name, pattern):
                return True
        
        # Check directory exclusions
        if path_obj.name in self.exclude_dirs:
            return True
        
        # Check regex patterns
        for regex_pattern in self.exclude_regex_patterns:
            try:
                if re.search(regex_pattern, path):
                    return True
            except re.error:
                # Invalid regex, skip it
                continue
        
        return False


# Default configuration
DEFAULT_CONFIG = {
    "exclude_patterns": [
        "*.log",
        "node_modules",
        ".git",
        "__pycache__",
        "*.tmp",
        "*.temp",
    ],
    "exclude_dirs": [
        ".git",
        "__pycache__",
        "node_modules",
    ],
    "exclude_regex_patterns": [
        r".*\.log\.\d+$",  # Log files with numbers (e.g., file.log.1)
        r".*~$",           # Backup files ending with ~
    ],
    "min_age_days": 0,
    "default_action": "dry_run",
    "log_file": "",
    "json_logging": False,
    "threads": 0,
    "follow_symlinks": False,
}