"""
Tests for the new Pydantic-based configuration system.

This demonstrates the testing approach for Phase 1.
"""

import os
import pytest
from pathlib import Path
from pydantic import ValidationError

from cortex_unified.core.config_v2 import (
    Config,
    ScanConfig,
    PerformanceConfig,
    SecurityConfig,
    LoggingConfig,
    DatabaseConfig,
    UIConfig,
    create_default_config,
)


class TestScanConfig:
    """Tests for ScanConfig model."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        config = ScanConfig()
        
        assert "*.log" in config.exclude_patterns
        assert ".git" in config.exclude_dirs
        assert config.follow_symlinks is False
        assert config.min_age_days == 0
        assert config.max_depth is None
    
    def test_min_age_validation(self):
        """Test that min_age_days is validated."""
        # Valid values
        ScanConfig(min_age_days=0)
        ScanConfig(min_age_days=30)
        ScanConfig(min_age_days=3650)
        
        # Invalid values
        with pytest.raises(ValidationError):
            ScanConfig(min_age_days=-1)
        
        with pytest.raises(ValidationError):
            ScanConfig(min_age_days=5000)
    
    def test_max_depth_validation(self):
        """Test that max_depth is validated."""
        # Valid values
        ScanConfig(max_depth=None)
        ScanConfig(max_depth=1)
        ScanConfig(max_depth=100)
        
        # Invalid values
        with pytest.raises(ValidationError):
            ScanConfig(max_depth=0)
        
        with pytest.raises(ValidationError):
            ScanConfig(max_depth=200)


class TestPerformanceConfig:
    """Tests for PerformanceConfig model."""
    
    def test_thread_clamping(self):
        """Test that thread count is clamped to reasonable limits."""
        config = PerformanceConfig(threads=0)
        assert 1 <= config.threads <= 64
        
        config = PerformanceConfig(threads=100)
        assert config.threads == 64
        
        config = PerformanceConfig(threads=8)
        assert config.threads == 8
    
    def test_chunk_size_validation(self):
        """Test that chunk_size is validated."""
        # Valid values
        PerformanceConfig(chunk_size=4096)
        PerformanceConfig(chunk_size=65536)
        PerformanceConfig(chunk_size=1048576)
        
        # Invalid values
        with pytest.raises(ValidationError):
            PerformanceConfig(chunk_size=1000)  # Too small
        
        with pytest.raises(ValidationError):
            PerformanceConfig(chunk_size=2000000)  # Too large


class TestSecurityConfig:
    """Tests for SecurityConfig model."""
    
    def test_default_action_validation(self):
        """Test that default_action only accepts valid values."""
        # Valid values
        SecurityConfig(default_action="dry_run")
        SecurityConfig(default_action="trash")
        SecurityConfig(default_action="delete")
        SecurityConfig(default_action="shred")
        
        # Invalid value
        with pytest.raises(ValidationError):
            SecurityConfig(default_action="invalid")
    
    def test_shred_passes_validation(self):
        """Test that shred_passes is validated."""
        # Valid values
        SecurityConfig(shred_passes=1)
        SecurityConfig(shred_passes=3)
        SecurityConfig(shred_passes=35)
        
        # Invalid values
        with pytest.raises(ValidationError):
            SecurityConfig(shred_passes=0)
        
        with pytest.raises(ValidationError):
            SecurityConfig(shred_passes=50)


class TestLoggingConfig:
    """Tests for LoggingConfig model."""
    
    def test_log_level_validation(self):
        """Test that log_level only accepts valid values."""
        # Valid values
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            LoggingConfig(log_level=level)
        
        # Invalid value
        with pytest.raises(ValidationError):
            LoggingConfig(log_level="TRACE")


class TestConfig:
    """Tests for main Config class."""
    
    def test_default_initialization(self):
        """Test that Config initializes with defaults."""
        config = Config()
        
        assert config.scan.min_age_days == 0
        assert config.performance.threads >= 1
        assert config.security.default_action == "dry_run"
        assert config.logging.log_level == "INFO"
        assert config.ui.theme == "auto"
    
    def test_nested_configuration(self):
        """Test that nested configuration works."""
        config = Config(
            scan={"min_age_days": 7},
            security={"default_action": "trash"},
            logging={"log_level": "DEBUG"}
        )
        
        assert config.scan.min_age_days == 7
        assert config.security.default_action == "trash"
        assert config.logging.log_level == "DEBUG"
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        # Set environment variables
        os.environ["CORTEX_SCAN__MIN_AGE_DAYS"] = "14"
        os.environ["CORTEX_LOGGING__LOG_LEVEL"] = "WARNING"
        
        try:
            config = Config()
            
            assert config.scan.min_age_days == 14
            assert config.logging.log_level == "WARNING"
        finally:
            # Clean up
            del os.environ["CORTEX_SCAN__MIN_AGE_DAYS"]
            del os.environ["CORTEX_LOGGING__LOG_LEVEL"]
    
    def test_yaml_loading(self, tmp_path):
        """Test loading configuration from YAML file."""
        # Create a test YAML file
        yaml_content = """
scan:
  min_age_days: 30
  follow_symlinks: true

security:
  default_action: "trash"
  require_confirmation: false

logging:
  log_level: "DEBUG"
"""
        yaml_file = tmp_path / "test_config.yaml"
        yaml_file.write_text(yaml_content)
        
        # Load config from file
        config = Config(config_file=yaml_file)
        
        assert config.scan.min_age_days == 30
        assert config.scan.follow_symlinks is True
        assert config.security.default_action == "trash"
        assert config.security.require_confirmation is False
        assert config.logging.log_level == "DEBUG"
    
    def test_save_to_yaml(self, tmp_path):
        """Test saving configuration to YAML file."""
        config = Config(
            scan={"min_age_days": 7},
            security={"default_action": "trash"}
        )
        
        yaml_file = tmp_path / "saved_config.yaml"
        config.save_to_yaml(yaml_file)
        
        assert yaml_file.exists()
        
        # Load it back and verify
        loaded_config = Config(config_file=yaml_file)
        assert loaded_config.scan.min_age_days == 7
        assert loaded_config.security.default_action == "trash"
    
    def test_backward_compatibility_properties(self):
        """Test that backward compatibility properties work."""
        config = Config(
            scan={"min_age_days": 7, "exclude_patterns": ["*.tmp"]},
            security={"default_action": "trash"},
            logging={"log_level": "DEBUG", "json_logging": True},
            performance={"threads": 8}
        )
        
        # Old-style access should still work
        assert config.min_age_days == 7
        assert config.exclude_patterns == ["*.tmp"]
        assert config.default_action == "trash"
        assert config.log_file is None
        assert config.json_logging is True
        assert config.threads == 8
        assert config.follow_symlinks is False
    
    def test_matches_exclude_patterns(self):
        """Test the matches_exclude_patterns method."""
        config = Config(
            scan={
                "exclude_patterns": ["*.log", "*.tmp"],
                "exclude_dirs": [".git", "__pycache__"],
                "exclude_regex_patterns": [r".*\.log\.\d+$"]
            }
        )
        
        # Should match glob patterns
        assert config.matches_exclude_patterns("/path/to/file.log")
        assert config.matches_exclude_patterns("/path/to/file.tmp")
        
        # Should match directory names
        assert config.matches_exclude_patterns("/path/to/.git")
        assert config.matches_exclude_patterns("/path/to/__pycache__")
        
        # Should match regex patterns
        assert config.matches_exclude_patterns("/path/to/file.log.1")
        assert config.matches_exclude_patterns("/path/to/file.log.123")
        
        # Should not match non-excluded paths
        assert not config.matches_exclude_patterns("/path/to/file.txt")
        assert not config.matches_exclude_patterns("/path/to/normal_dir")
    
    def test_validation_error_messages(self):
        """Test that validation errors provide helpful messages."""
        with pytest.raises(ValidationError) as exc_info:
            Config(scan={"min_age_days": 5000})
        
        error_msg = str(exc_info.value)
        assert "min_age_days" in error_msg
        assert "less than or equal to 3650" in error_msg


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""
    
    def test_creates_config_file(self, tmp_path):
        """Test that create_default_config creates a valid file."""
        config_path = tmp_path / "default_config.yaml"
        
        config = create_default_config(config_path)
        
        assert config_path.exists()
        assert isinstance(config, Config)
        
        # Verify the file can be loaded
        loaded_config = Config(config_file=config_path)
        assert loaded_config.scan.min_age_days == 0


# ============================================================================
# Property-Based Tests (using Hypothesis)
# ============================================================================

from hypothesis import given, strategies as st


class TestConfigPropertyBased:
    """Property-based tests for configuration."""
    
    @given(st.integers(min_value=0, max_value=3650))
    def test_min_age_days_always_valid_in_range(self, days):
        """Test that any valid min_age_days value works."""
        config = ScanConfig(min_age_days=days)
        assert config.min_age_days == days
    
    @given(st.integers(min_value=1, max_value=256))
    def test_thread_count_always_clamped(self, threads):
        """Test that thread count is always clamped to valid range."""
        config = PerformanceConfig(threads=threads)
        assert 1 <= config.threads <= 64
    
    @given(st.text(min_size=1, max_size=100))
    def test_exclude_patterns_accept_any_string(self, pattern):
        """Test that exclude patterns accept any string."""
        config = ScanConfig(exclude_patterns=[pattern])
        assert pattern in config.exclude_patterns


# ============================================================================
# Integration Tests
# ============================================================================

class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_full_workflow(self, tmp_path):
        """Test complete workflow: create, save, load, modify, save."""
        config_file = tmp_path / "workflow_config.yaml"
        
        # 1. Create config with custom values
        config1 = Config(
            scan={"min_age_days": 7},
            security={"default_action": "trash"}
        )
        
        # 2. Save to file
        config1.save_to_yaml(config_file)
        
        # 3. Load from file
        config2 = Config(config_file=config_file)
        assert config2.scan.min_age_days == 7
        
        # 4. Modify and save again
        config2.scan.min_age_days = 14
        config2.save_to_yaml(config_file)
        
        # 5. Load again and verify
        config3 = Config(config_file=config_file)
        assert config3.scan.min_age_days == 14
    
    def test_environment_overrides_yaml(self, tmp_path):
        """Test that environment variables override YAML values."""
        # Create YAML file
        yaml_content = """
scan:
  min_age_days: 7

logging:
  log_level: "INFO"
"""
        yaml_file = tmp_path / "env_test.yaml"
        yaml_file.write_text(yaml_content)
        
        # Set environment variable
        os.environ["CORTEX_SCAN__MIN_AGE_DAYS"] = "30"
        
        try:
            config = Config(config_file=yaml_file)
            
            # Environment should override YAML
            assert config.scan.min_age_days == 30
            
            # Non-overridden values should come from YAML
            assert config.logging.log_level == "INFO"
        finally:
            del os.environ["CORTEX_SCAN__MIN_AGE_DAYS"]


if __name__ == "__main__":
    # Run tests with: pytest test_config_v2.py -v
    pytest.main([__file__, "-v", "--cov=cortex_unified.core.config_v2"])
