"""Unit tests for the Cyberpunk Setup Installer UI and InstallWorker."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from scripts.installer import InstallerApp, InstallWorker, DEFAULT_INSTALL_DIR, APP_NAME, APP_VERSION


@pytest.fixture(scope="module")
def app():
    """Provide shared QApplication for installer testing."""
    application = QApplication.instance() or QApplication([])
    yield application


class TestInstallerUI:
    """Tests for InstallerApp UI and components."""

    def test_installer_window_initializes(self, app):
        """Installer window builds correctly with title, destination, and options."""
        installer = InstallerApp()
        assert installer.windowTitle() == f"{APP_NAME} Setup v{APP_VERSION}"
        assert installer.dest_edit.text() == DEFAULT_INSTALL_DIR
        assert installer.chk_desktop.isChecked()
        assert installer.chk_start_menu.isChecked()
        assert installer.chk_launch.isChecked()
        assert installer.status_lbl.text() == "Ready to install."

    def test_html_content_loads(self, app):
        """Cyberpunk Infiltration progress bar HTML content loads with custom checkpoints."""
        installer = InstallerApp()
        html = installer._load_html_content()
        assert "CORTEX // SYSTEM INFILTRATION" in html
        assert "REGISTRY" in html
        assert "APPDATA" in html
        assert "START MENU" in html
        assert "SYSTEM" in html
        assert "WINDOWS DEFENDER" in html
        assert "window.CORTEX_FEED" in html

    def test_progress_update_signal(self, app):
        """_on_progress updates the status label text accurately."""
        installer = InstallerApp()
        installer._on_progress(45.5, "Extracting (45%): test.dll")
        assert "Extracting (45%): test.dll" in installer.status_lbl.text()


class TestInstallWorker:
    """Tests for InstallWorker thread configuration."""

    def test_worker_initialization(self, tmp_path: Path):
        """InstallWorker holds target directory and shortcut options."""
        worker = InstallWorker(
            target_dir=str(tmp_path),
            desktop_shortcut=True,
            start_menu_shortcut=False,
            launch_after=True,
        )
        assert worker.target_dir == str(tmp_path)
        assert worker.desktop_shortcut is True
        assert worker.start_menu_shortcut is False
        assert worker.launch_after is True
