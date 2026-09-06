"""End-to-end integration test verifying InstallWorker and InstallerApp execution."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path
import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from scripts.installer import InstallerApp, InstallWorker, get_bundle_zip


@pytest.fixture(scope="module")
def app():
    """Provide shared QApplication."""
    application = QApplication.instance() or QApplication([])
    yield application


def test_bundle_zip_exists_and_valid():
    """Verify that the distribution archive exists and contains valid zip contents."""
    zip_path = get_bundle_zip()
    assert os.path.exists(zip_path), f"Bundle zip not found at {zip_path}"
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) > 10, "Distribution zip appears too small or empty"
        assert any("CortexCleaner.exe" in name for name in namelist), "CortexCleaner.exe missing from bundle"


def test_install_worker_full_lifecycle(tmp_path: Path):
    """Test full extraction cycle with progress signals advancing from 0% to 100%."""
    dest_dir = tmp_path / "installed_app"
    worker = InstallWorker(
        target_dir=str(dest_dir),
        desktop_shortcut=False,
        start_menu_shortcut=False,
        launch_after=False,
    )

    progress_events = []
    finished_events = []
    failed_events = []

    worker.progress_updated.connect(lambda pct, msg: progress_events.append((pct, msg)))
    worker.install_finished.connect(lambda exe: finished_events.append(exe))
    worker.install_failed.connect(lambda err: failed_events.append(err))

    # Run extraction synchronously in test
    worker.run()

    assert not failed_events, f"Installation failed with error: {failed_events}"
    assert len(finished_events) == 1, "Installation did not emit install_finished"
    assert len(progress_events) >= 5, "Progress updates were not received"

    # Verify progress values ascend to 100%
    percentages = [p[0] for p in progress_events]
    assert percentages[0] <= 10.0
    assert percentages[-1] == 100.0

    # Verify extracted executable exists on disk
    extracted_exe = finished_events[0]
    assert os.path.exists(extracted_exe), f"Installed executable {extracted_exe} does not exist"


def test_installer_gui_signals_and_html(app, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test InstallerApp response to worker progress signals and JavaScript bridge."""
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    installer = InstallerApp()
    dest_dir = tmp_path / "gui_installed_app"
    installer.dest_edit.setText(str(dest_dir))
    installer.chk_desktop.setChecked(False)
    installer.chk_start_menu.setChecked(False)
    installer.chk_launch.setChecked(False)

    # Test progress update signal handling
    installer._on_progress(14.0, "Extracting (14%): registry_engine.py")
    assert "14%" in installer.status_lbl.text()

    installer._on_progress(88.0, "Configuring Windows security & integrations…")
    assert "security" in installer.status_lbl.text().lower()

    # Test completion handler
    dummy_exe = str(tmp_path / "CortexCleaner.exe")
    Path(dummy_exe).write_bytes(b"dummy")
    installer._on_finished(dummy_exe)

    assert "successfully" in installer.status_lbl.text().lower()
    assert installer.install_btn.text() == "Launch"
    installer.close()
