"""Legacy YAML configuration management for Cortex Cleaner.

.. deprecated::
   New code should use :mod:`cortex_unified.core.config_v2`, which validates
   its input and reports problems instead of silently falling back to defaults.
   This module is retained because 42 call sites still depend on it; see
   ``config_v2`` for the migration status.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any
import yaml

_LOG = logging.getLogger("cortex.core.config")

class Config:
    """Configuration class for Cortex Cleaner.

    ``DEFAULT_CONFIG`` is the baseline; values loaded from the user's YAML file
    are layered on top of it. This matters for safety: the defaults protect
    ``.git``, ``node_modules`` and ``__pycache__`` from cleanup, and before
    this baseline was applied every property fell back to an *empty* list, so
    those directories were not actually protected. See :data:`DEFAULT_CONFIG`.
    """

    def __init__(self, config_path: str = None):
        """__init__."""
        self.config_path = config_path or self._get_default_config_path()
        self.config_data = self._load_config()
        """__init__."""

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        home = Path.home()
        return str(home / ".deepcleaner.yaml")
    
    def _load_config(self) -> Dict[str, Any]:
        """Return ``DEFAULT_CONFIG`` overlaid with the user's YAML file.

        A missing file is normal and silent. A file that exists but cannot be
        read or parsed is *not* normal: we still fall back to defaults (so the
        app stays usable) but the reason is logged at WARNING with the specific
        failure, because silently ignoring a user's misconfigured file is how
        "my settings do nothing" bugs go undiagnosed for months.

        The defaults are always the baseline. Previously they were not applied
        at all, so with no config file every exclusion list resolved to ``[]``
        and ``.git``/``node_modules``/``__pycache__`` were left unprotected -
        inconsistently, since two CLI commands merged ``DEFAULT_CONFIG`` by
        hand while the other seven (and every analyzer) did not.
        """
        if not os.path.exists(self.config_path):
            return self._defaults()

        try:
            # Explicit UTF-8: the default encoding is locale-dependent, so a
            # config containing non-ASCII paths would fail to load on some
            # Windows systems and silently revert to defaults.
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, UnicodeDecodeError) as exc:
            _LOG.warning("could not read config %s: %s; using defaults",
                         self.config_path, exc)
            return self._defaults()
        except yaml.YAMLError as exc:
            _LOG.warning("config %s is not valid YAML: %s; using defaults",
                         self.config_path, exc)
            return self._defaults()

        if not isinstance(data, dict):
            _LOG.warning("config %s must contain a mapping at the top level, "
                         "got %s; using defaults",
                         self.config_path, type(data).__name__)
            return self._defaults()

        # User settings win over the defaults, key by key.
        merged = self._defaults()
        merged.update(data)
        return merged

    @staticmethod
    def _defaults() -> Dict[str, Any]:
        """A deep-enough copy of ``DEFAULT_CONFIG`` for safe mutation.

        Callers (notably the CLI, which applies ``--exclude-pattern`` overrides
        by assigning into ``config_data``) mutate the result, so the nested
        lists must not be shared with the module-level constant.
        """
        return {
            key: list(value) if isinstance(value, list) else value
            for key, value in DEFAULT_CONFIG.items()
        }
    
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
        """default_action."""
        return self.config_data.get("default_action", "dry_run")
        """default_action."""
    
    @property
    def log_file(self) -> str:
        """log_file."""
        return self.config_data.get("log_file", "")
        """log_file."""
    
    @property
    def json_logging(self) -> bool:
        """json_logging."""
        return self.config_data.get("json_logging", False)
        """json_logging."""
    
    @property
    def threads(self) -> int:
        """threads."""
        return self.config_data.get("threads", 0)  # 0 means use CPU count
        """threads."""
    
    @property
    def follow_symlinks(self) -> bool:
        """follow_symlinks."""
        return self.config_data.get("follow_symlinks", False)
        """follow_symlinks."""
    
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

#: Baseline configuration. Applied by :meth:`Config._load_config` as the
#: starting point, with any user YAML settings layered on top. The exclusion
#: entries are a safety feature: they keep cleanup out of ``.git``,
#: ``node_modules`` and ``__pycache__``.
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
        # Editor/IDE state. Previously these were protected only by
        # ``config_v2.ScanConfig`` - which nothing used - so in practice a
        # cleanup run could reach into a project's ``.vscode``/``.idea``.
        # ``config_v2`` now derives its defaults from this dict, so the two
        # can no longer drift apart.
        ".vscode",
        ".idea",
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