import os
import pytest
from pathlib import Path
from cortex_unified.core.deleter import Deleter

def test_deleter_dry_run(test_env):
    """Test that Deleter does not remove files in dry-run mode."""
    files = [Path(test_env) / "empty1.txt"]
    dirs = [Path(test_env) / "empty_dir1"]
    
    deleter = Deleter(dry_run=True, use_trash=False)
    result = deleter.delete(files, dirs)
    
    assert result["files_deleted"] == 1
    assert result["dirs_deleted"] == 1
    assert result["errors"] == []
    
    # Verify items still exist
    assert files[0].exists()
    assert dirs[0].exists()

def test_deleter_real_deletion(test_env):
    """Test that Deleter actually removes files when dry-run is False."""
    files = [Path(test_env) / "empty1.txt"]
    dirs = [Path(test_env) / "empty_dir1"]
    
    deleter = Deleter(dry_run=False, use_trash=False)
    result = deleter.delete(files, dirs)
    
    assert result["files_deleted"] == 1
    assert result["dirs_deleted"] == 1
    assert result["errors"] == []
    
    # Verify items were removed
    assert not files[0].exists()
    assert not dirs[0].exists()

def test_deleter_handles_missing_files(test_env):
    """Test that Deleter gracefully handles files that are already deleted."""
    fake_file = Path(test_env) / "does_not_exist.txt"
    files = [fake_file]
    
    deleter = Deleter(dry_run=False)
    result = deleter.delete(files, [])
    
    assert result["files_deleted"] == 0
    assert len(result["errors"]) == 1
    assert result["errors"][0]["path"] == str(fake_file)
