"""Tests for the Cortex Workstation configuration loader."""

import os
import yaml
import pytest
from cortex_unified.core.config import Config, DEFAULT_CONFIG

def test_config_initialization_defaults():
    """Test that Config initializes with defaults when no file is present."""
    config = Config(config_path="non_existent_config.yaml")    
    assert isinstance(config.exclude_patterns, list)
    assert getattr(config, "default_action", "dry_run") == "dry_run"

def test_config_loading_from_file(temp_dir):
    """Test that Config can load from a yaml file."""
    config_file = temp_dir / "test_config.yaml"
    test_data = {
        "exclude_patterns": ["*.test1", "*.test2"],
        "threads": 4,
        "default_action": "delete"
    }
    
    with open(config_file, "w") as f:
        yaml.dump(test_data, f)
        
    config = Config(config_path=str(config_file))
    
    assert "*.test1" in config.exclude_patterns
    assert config.threads == 4
    assert config.default_action == "delete"

