"""Global pytest fixtures and test environment configuration."""

import os
import shutil
import sys
import pytest
from pathlib import Path
import cortex_unified.compat_winreg  # noqa: F401
from cortex_unified.core.config import Config


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


@pytest.fixture(autouse=True)
def clean_qapp_event_filters():
    """Ensure QApplication processes pending events and flushes event filters after each test."""
    yield
    if "PySide6" in sys.modules:
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QEvent

            app = QApplication.instance()
            if app is not None:
                app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                app.processEvents()
        except Exception:
            pass


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Ensure all Qt windows and pending events are flushed before session exit."""
    if "PySide6" in sys.modules:
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QEvent

            app = QApplication.instance()
            if app is not None:
                app.closeAllWindows()
                app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                app.processEvents()
        except Exception:
            pass
