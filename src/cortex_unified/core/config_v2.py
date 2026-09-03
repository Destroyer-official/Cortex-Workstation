"""
Pydantic-based configuration management for Cortex Cleaner.

This replaces the old YAML-based config with full type safety, validation,
and support for environment variables and CLI overrides.

Adoption status (read this before choosing a config module)
-----------------------------------------------------------
This module is the **intended** configuration layer and is fully covered by
``tests/test_config_v2.py``, but it currently has **zero production callers**.
Every module that reads configuration still imports the legacy
:mod:`cortex_unified.core.config`.

Do not add new callers to the legacy module; new code should import from here.

What already matches
~~~~~~~~~~~~~~~~~~~~
The read-only surface is deliberately identical (``exclude_patterns``,
``exclude_dirs``, ``exclude_regex_patterns``, ``min_age_days``,
``default_action``, ``log_file``, ``json_logging``, ``threads``,
``follow_symlinks``, ``matches_exclude_patterns``), and the **default exclusion
values now agree**: the legacy loader was fixed to use its own
``DEFAULT_CONFIG`` as the baseline, which it previously declared but never
applied.

What still blocks a mechanical migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These are real incompatibilities, not cosmetic ones. Each needs a decision:

1. **Mutable ``config_data``.** The CLI applies ``--exclude-pattern`` and
   friends by assigning into ``Config.config_data[...]`` - roughly 48 sites.
   A pydantic model has no such dict. A typed override API (or an explicit
   ``model_copy(update=...)`` call per site) has to replace it.
2. **Constructor shape.** Legacy accepts a positional path,
   ``Config(config_path)``, and 8 CLI sites use it. This class takes keyword
   data only, so those calls would raise ``TypeError``.
3. **No ``DEFAULT_CONFIG`` export.** ``cli/cli.py`` and ``ui/main_window.py``
   import that dict from the legacy module.
4. **Different config file and key layout.** Legacy reads a flat
   ``~/.deepcleaner.yaml``; this class reads a *sectioned*
   ``~/.cortex_cleaner.yaml`` (``scan:``, ``performance:``, ...). Existing user
   files would need migrating, or a compatibility reader.

Until those are addressed, swapping the import in place would break the CLI
rather than improve it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource
import yaml

# Single source of truth for the safety-critical exclusion defaults. Imported
# (rather than restated) so this module and the legacy config can never disagree
# about which directories cleanup must stay out of. ``core.config`` is
# deliberately import-cheap - stdlib plus pyyaml - so this adds no real cost.
from cortex_unified.core.config import DEFAULT_CONFIG as _DEFAULTS


def _read_yaml_file(path: Path) -> dict:
    """Load a YAML config file into a dict, warning (not raising) on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception as e:
        import warnings
        warnings.warn(f"Failed to load config from {path}: {e}")
        return {}


class _YamlConfigSource(PydanticBaseSettingsSource):
    """A pydantic-settings source that reads from an optional YAML file.

    Slotted into the source chain by ``Config.settings_customise_sources`` at
    lower priority than init kwargs and environment variables, so YAML only
    fills in values nothing more specific already provided.
    """

    def __init__(self, settings_cls, config_file):
        super().__init__(settings_cls)
        self._data = _read_yaml_file(Path(config_file)) if config_file else {}
        """__init__."""

    def get_field_value(self, field, field_name):  # pragma: no cover - trivial
        return self._data.get(field_name), field_name, False
        """get_field_value."""

    def __call__(self) -> dict:
        return dict(self._data)
        """__call__."""


class ScanConfig(BaseModel):
    """Configuration for scan operations.

    The exclusion defaults are *derived* from
    :data:`cortex_unified.core.config.DEFAULT_CONFIG` rather than restated
    here. They are safety-critical (they keep cleanup out of ``.git``,
    ``node_modules``, ``__pycache__`` and editor state), and having two
    independent copies meant they silently drifted: this class protected
    ``.vscode``/``.idea`` while the legacy config that every module actually
    uses did not. One source of truth makes that drift impossible.
    """

    exclude_patterns: List[str] = Field(
        default_factory=lambda: list(_DEFAULTS["exclude_patterns"]),
        description="Glob patterns for files/folders to exclude"
    )

    exclude_dirs: List[str] = Field(
        default_factory=lambda: list(_DEFAULTS["exclude_dirs"]),
        description="Directory names to always exclude"
    )

    exclude_regex_patterns: List[str] = Field(
        default_factory=lambda: list(_DEFAULTS["exclude_regex_patterns"]),
        description="Regex patterns for exclusion"
    )

    follow_symlinks: bool = Field(
        default_factory=lambda: bool(_DEFAULTS["follow_symlinks"]),
        description="Whether to follow symbolic links during scanning"
    )

    min_age_days: int = Field(
        default_factory=lambda: int(_DEFAULTS["min_age_days"]),
        ge=0,
        le=3650,
        description="Minimum age in days for files to be considered for deletion"
    )
    
    max_depth: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Maximum directory depth to scan (None = unlimited)"
    )


class PerformanceConfig(BaseModel):
    """Configuration for performance settings."""

    # Needed so the `clamp_threads` validator actually runs for the *default*
    # value (threads=0) and not only for explicitly-passed values - otherwise
    # "0 = auto-detect" never gets resolved to a real CPU count.
    model_config = ConfigDict(validate_default=True)

    threads: int = Field(
        default=0,
        ge=0,
        le=256,
        description="Number of threads (0 = auto-detect)"
    )
    
    enable_checkpoints: bool = Field(
        default=True,
        description="Enable scan checkpointing for resume capability"
    )
    
    enable_throttling: bool = Field(
        default=True,
        description="Enable resource throttling to prevent system overload"
    )
    
    chunk_size: int = Field(
        default=65536,
        ge=4096,
        le=1048576,
        description="Chunk size for file operations in bytes"
    )
    
    @field_validator("threads")
    @classmethod
    def clamp_threads(cls, v: int) -> int:
        """Clamp thread count to reasonable limits."""
        if v == 0:
            return min(os.cpu_count() or 4, 64)
        return min(v, 64)


class SecurityConfig(BaseModel):
    """Configuration for security and safety settings."""
    
    default_action: Literal["dry_run", "trash", "delete", "shred"] = Field(
        default="dry_run",
        description="Default action for file deletion"
    )
    
    require_confirmation: bool = Field(
        default=True,
        description="Require user confirmation before deletion"
    )
    
    enable_quarantine: bool = Field(
        default=True,
        description="Move files to quarantine before permanent deletion"
    )
    
    quarantine_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to keep files in quarantine"
    )
    
    allow_system_paths: bool = Field(
        default=False,
        description="Allow operations on system directories (dangerous!)"
    )
    
    shred_passes: int = Field(
        default=3,
        ge=1,
        le=35,
        description="Number of overwrite passes for secure deletion"
    )


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    
    log_file: Optional[Path] = Field(
        default=None,
        description="Path to log file (None = console only)"
    )
    
    json_logging: bool = Field(
        default=False,
        description="Use JSON format for logs (for production)"
    )
    
    enable_file_logging: bool = Field(
        default=True,
        description="Enable logging to file"
    )


class DatabaseConfig(BaseModel):
    """Configuration for database persistence."""
    
    db_path: Path = Field(
        default_factory=lambda: Path.home() / ".cortex_cleaner" / "history.db",
        description="Path to SQLite database"
    )
    
    backup_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cortex_cleaner" / "backups",
        description="Directory for backup files"
    )
    
    enable_history: bool = Field(
        default=True,
        description="Enable scan history tracking"
    )
    
    max_history_entries: int = Field(
        default=1000,
        ge=10,
        le=100000,
        description="Maximum number of history entries to keep"
    )


class UIConfig(BaseModel):
    """Configuration for UI settings."""
    
    theme: Literal["auto", "light", "dark"] = Field(
        default="auto",
        description="UI theme (auto = follow system)"
    )
    
    language: str = Field(
        default="en",
        description="UI language code"
    )
    
    show_onboarding: bool = Field(
        default=True,
        description="Show onboarding wizard on first launch"
    )
    
    enable_notifications: bool = Field(
        default=True,
        description="Enable system notifications"
    )


class Config(BaseSettings):
    """
    Main configuration class for Cortex Cleaner.
    
    Supports loading from:
    1. YAML config file
    2. Environment variables (prefix: CORTEX_)
    3. Direct parameter overrides
    
    Example:
        # Load from default location
        config = Config()
        
        # Load from specific file
        config = Config(config_file="~/.cortex_cleaner.yaml")
        
        # Override via environment
        # CORTEX_SCAN__MIN_AGE_DAYS=7
        # CORTEX_LOGGING__LOG_LEVEL=DEBUG
    """
    
    model_config = SettingsConfigDict(
        env_prefix="CORTEX_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        # Without this, field_validator hooks (e.g. PerformanceConfig's
        # thread-count auto-detection) never run on *default* values - only
        # on values explicitly passed in. That left `threads=0` as the actual
        # runtime default instead of the intended CPU-count auto-detection.
        validate_default=True,
    )
    
    # Configuration sections
    scan: ScanConfig = Field(default_factory=ScanConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    
    # Config file path (not loaded from env)
    config_file: Optional[Path] = Field(
        default=None,
        description="Path to YAML config file",
        exclude=True
    )
    
    def __init__(self, **data):
        """Initialize config, resolving the YAML file path (if any).

        The actual precedence between explicit kwargs, environment variables,
        and the YAML file is handled by :meth:`settings_customise_sources`
        below - NOT by manually merging dicts here. Manually merging (the
        previous implementation) made YAML values behave like directly-passed
        init kwargs, which incorrectly let a config file silently override
        environment variable overrides.
        """
        config_file = data.get("config_file")
        if config_file is None:
            default_path = Path.home() / ".cortex_cleaner.yaml"
            if default_path.exists():
                config_file = default_path
                data["config_file"] = default_path
        super().__init__(**data)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Define source precedence, highest priority first:

        1. Explicit constructor kwargs (``init_settings``)
        2. Environment variables (``CORTEX_...``)
        3. YAML config file
        4. Field defaults (implicit / handled by pydantic itself)
        """
        yaml_source = _YamlConfigSource(settings_cls, init_settings.init_kwargs.get("config_file"))
        return (init_settings, env_settings, yaml_source, dotenv_settings, file_secret_settings)

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        """Load configuration from YAML file. Kept as a public-ish helper for
        backward compatibility with any external callers/tests."""
        return _read_yaml_file(path)
    
    def save_to_yaml(self, path: Optional[Path] = None) -> None:
        """Save current configuration to YAML file."""
        if path is None:
            path = self.config_file or (Path.home() / ".cortex_cleaner.yaml")
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # mode="json" coerces Path/enum/etc. into plain str/primitives so the
        # output is valid *safe* YAML - `model_dump()`'s default python mode
        # left real Path objects in the dict, which yaml.dump serialized with
        # unsafe `!!python/object/apply:pathlib.WindowsPath` tags that
        # yaml.safe_load (used by _load_yaml) cannot parse. That silently
        # discarded the entire file on the next load.
        data = self.model_dump(exclude_none=True, exclude={"config_file"}, mode="json")

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def matches_exclude_patterns(self, path: str) -> bool:
        """
        Check if a path matches any exclude patterns (glob or regex).
        
        This method maintains backward compatibility with the old Config class.
        """
        from fnmatch import fnmatch
        import re
        
        path_obj = Path(path)
        
        # Check glob patterns
        for pattern in self.scan.exclude_patterns:
            if fnmatch(path, pattern) or fnmatch(path_obj.name, pattern):
                return True
        
        # Check directory exclusions
        if path_obj.name in self.scan.exclude_dirs:
            return True
        
        # Check regex patterns
        for regex_pattern in self.scan.exclude_regex_patterns:
            try:
                if re.search(regex_pattern, path):
                    return True
            except re.error:
                continue
        
        return False
    
    # Backward compatibility properties
    @property
    def exclude_patterns(self) -> List[str]:
        """Backward compatibility: get exclude patterns."""
        return self.scan.exclude_patterns
    
    @property
    def exclude_dirs(self) -> List[str]:
        """Backward compatibility: get exclude directories."""
        return self.scan.exclude_dirs
    
    @property
    def exclude_regex_patterns(self) -> List[str]:
        """Backward compatibility: get exclude regex patterns."""
        return self.scan.exclude_regex_patterns
    
    @property
    def min_age_days(self) -> int:
        """Backward compatibility: get minimum age in days."""
        return self.scan.min_age_days
    
    @property
    def default_action(self) -> str:
        """Backward compatibility: get default action."""
        return self.security.default_action
    
    @property
    def log_file(self) -> Optional[str]:
        """Backward compatibility: get log file path."""
        return str(self.logging.log_file) if self.logging.log_file else None
    
    @property
    def json_logging(self) -> bool:
        """Backward compatibility: get JSON logging flag."""
        return self.logging.json_logging
    
    @property
    def threads(self) -> int:
        """Backward compatibility: get number of threads."""
        return self.performance.threads
    
    @property
    def follow_symlinks(self) -> bool:
        """Backward compatibility: get follow symlinks flag."""
        return self.scan.follow_symlinks


# Example configuration file
# NOTE: must be a raw string (r"""...""") - it contains literal backslashes
# for the YAML regex patterns below, and a non-raw string would treat "\."
# as a Python escape sequence rather than the two literal characters "\" and
# ".", corrupting the regex before it's even written to disk.
EXAMPLE_CONFIG_YAML = r"""
# Cortex Cleaner Configuration File
# All settings are optional - defaults will be used if not specified

scan:
  exclude_patterns:
    - "*.log"
    - "node_modules"
    - ".git"
    - "__pycache__"
    - "*.tmp"
    - "*.temp"
  
  exclude_dirs:
    - ".git"
    - "__pycache__"
    - "node_modules"
    - ".vscode"
    - ".idea"
  
  exclude_regex_patterns:
    - '.*\.log\.\d+$'  # Log files with numbers (single-quoted: no YAML escaping)
    - '.*~$'           # Backup files
  
  follow_symlinks: false
  min_age_days: 0
  max_depth: null  # null = unlimited

performance:
  threads: 0  # 0 = auto-detect
  enable_checkpoints: true
  enable_throttling: true
  chunk_size: 65536

security:
  default_action: "dry_run"  # dry_run, trash, delete, shred
  require_confirmation: true
  enable_quarantine: true
  quarantine_days: 30
  allow_system_paths: false
  shred_passes: 3

logging:
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  log_file: null  # null = console only
  json_logging: false
  enable_file_logging: true

database:
  db_path: "~/.cortex_cleaner/history.db"
  backup_dir: "~/.cortex_cleaner/backups"
  enable_history: true
  max_history_entries: 1000

ui:
  theme: "auto"  # auto, light, dark
  language: "en"
  show_onboarding: true
  enable_notifications: true
"""


def create_default_config(path: Optional[Path] = None) -> Config:
    """Create and save a default configuration file."""
    if path is None:
        path = Path.home() / ".cortex_cleaner.yaml"
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(EXAMPLE_CONFIG_YAML)
    
    return Config(config_file=path)


if __name__ == "__main__":
    # Example usage and validation
    print("Creating example configuration...")
    config = Config()
    print(f"✓ Config loaded successfully")
    print(f"  - Threads: {config.performance.threads}")
    print(f"  - Log level: {config.logging.log_level}")
    print(f"  - Default action: {config.security.default_action}")
    print(f"  - DB path: {config.database.db_path}")
    
    # Test validation
    try:
        bad_config = Config(scan={"min_age_days": 5000})  # Should fail
    except Exception as e:
        print(f"✓ Validation working: {e}")
    
    # Test environment variable override
    os.environ["CORTEX_LOGGING__LOG_LEVEL"] = "DEBUG"
    config2 = Config()
    print(f"✓ Env override working: log_level = {config2.logging.log_level}")
