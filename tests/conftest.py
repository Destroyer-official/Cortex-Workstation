import os
import shutil
import pytest
from pathlib import Path
from deep_cleaner.config import Config

@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for testing."""
    return tmp_path

@pytest.fixture
def test_env(temp_dir):
    """Create a test directory structure with mock files."""
    # Create empty files
    (temp_dir / "empty1.txt").touch()
    (temp_dir / "empty2.log").touch()
    
    # Create empty directories
    (temp_dir / "empty_dir1").mkdir()
    (temp_dir / "empty_dir2").mkdir()
    
    # Create non-empty files
    with open(temp_dir / "nonempty.txt", "w") as f:
        f.write("test data")
        
    # Create non-empty directory
    nonempty_dir = temp_dir / "nonempty_dir"
    nonempty_dir.mkdir()
    with open(nonempty_dir / "file.txt", "w") as f:
        f.write("more test data")
        
    return temp_dir

@pytest.fixture
def clean_config():
    """Return a default clean Configuration."""
    config = Config()
    # Ensure test-safe defaults
    config.config_data["exclude_patterns"] = []
    config.config_data["exclude_dirs"] = []
    config.config_data["min_age_days"] = 0
    return config
