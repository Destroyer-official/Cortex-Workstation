import os
from pathlib import Path
from deep_cleaner.utils import normalize_path

def test_normalize_path():
    """Test path normalization."""
    # Test valid path
    current_dir = os.getcwd()
    normalized = normalize_path(current_dir)
    assert str(normalized) == current_dir
    
    # Test home directory expansion
    home_dir = normalize_path("~")
    assert str(home_dir) == os.path.expanduser("~")
