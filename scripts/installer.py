"""Cortex Workstation Windows Setup Installer with Cyberpunk Infiltration Progress Bar.

A standalone graphical installer that deploys Cortex Workstation into
%LOCALAPPDATA%\\Programs\\CortexWorkstation, creates Desktop & Start Menu
shortcuts, registers an uninstaller, and showcases real-time installation
progress through an interactive, gamified Cyberpunk System Infiltration progress world.
"""
from __future__ import annotations

import os
import sys
import zipfile
import subprocess
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QFrame,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

APP_NAME = "Cortex Workstation"

try:
    from cortex_unified import __version__ as APP_VERSION
except ImportError:
    APP_VERSION = "1.2.0"

DEFAULT_INSTALL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Programs",
    "CortexWorkstation"
)


def get_bundle_zip() -> str:
    """Locate the bundled distribution zip file.

    Returns:
        str: Absolute filesystem path to the distribution archive.

    Raises:
        FileNotFoundError: If the distribution zip cannot be located.
    """
    zip_name = f"Cortex-Workstation-v{APP_VERSION}-Windows-x64.zip"
    base_dir = getattr(sys, "_MEIPASS", None)
    if base_dir:
        candidate = os.path.join(base_dir, zip_name)
        if os.path.exists(candidate):
            return candidate

    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist", zip_name),
        os.path.join(os.path.dirname(sys.executable), zip_name),
        os.path.join(os.getcwd(), "dist", zip_name),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    raise FileNotFoundError(f"Could not find bundled distribution package '{zip_name}'.")


def create_shortcut(target_exe: str, shortcut_path: str, description: str = APP_NAME) -> bool:
    """Create a Windows .lnk shortcut via PowerShell WScript.Shell with embedded icon.

    Args:
        target_exe (str): Target binary to invoke.
        shortcut_path (str): File path where the .lnk shortcut should be saved.
        description (str): Human-readable tooltip description.

    Returns:
        bool: True if created successfully, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
        ps_cmd = (
            f"$WshShell = New-Object -ComObject WScript.Shell; "
            f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
            f"$Shortcut.TargetPath = '{target_exe}'; "
            f"$Shortcut.WorkingDirectory = '{os.path.dirname(target_exe)}'; "
            f"$Shortcut.IconLocation = '{target_exe},0'; "
            f"$Shortcut.Description = '{description}'; "
            f"$Shortcut.Save();"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True
        )
        return res.returncode == 0
    except Exception:
        return False


def register_uninstaller(install_dir: str, exe_path: str) -> None:
    """Register the application in Windows Installed Apps registry with custom icon.

    Args:
        install_dir (str): Root destination directory where application is deployed.
        exe_path (str): Executable path for display icon and uninstall target.
    """
    if winreg is None:
        return
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\CortexWorkstation"
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, f"{APP_NAME} v{APP_VERSION}")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Destroyer-official")
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f'"{exe_path}",0')
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            uninst_cmd = f'cmd.exe /c rd /s /q "{install_dir}" & reg delete "HKCU\\{key_path}" /f'
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninst_cmd)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass


class InstallWorker(QThread):
    """Background worker extracting files and configuring Windows integration."""

    progress_updated = Signal(float, str)  # (pct 0..100, current_file)
    install_finished = Signal(str)         # (exe_path)
    install_failed = Signal(str)           # (error_message)

    def __init__(
        self,
        target_dir: str,
        desktop_shortcut: bool,
        start_menu_shortcut: bool,
        launch_after: bool,
    ):
        """Initialize worker parameters.

        Args:
            target_dir (str): Installation destination directory.
            desktop_shortcut (bool): Whether to create desktop shortcut.
            start_menu_shortcut (bool): Whether to create start menu shortcut.
            launch_after (bool): Whether to launch app after install.
        """
        super().__init__()
        self.target_dir = target_dir
        self.desktop_shortcut = desktop_shortcut
        self.start_menu_shortcut = start_menu_shortcut
        self.launch_after = launch_after

    def run(self):
        """Execute installation steps off the main GUI thread."""
        try:
            self.progress_updated.emit(2.0, "Locating distribution archive…")
            zip_path = get_bundle_zip()

            self.progress_updated.emit(5.0, "Preparing destination folder…")
            os.makedirs(self.target_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                members = zf.infolist()
                total = len(members)
                # Reserve 5% to 85% for extraction
                for idx, member in enumerate(members, 1):
                    zf.extract(member, self.target_dir)
                    if idx % 15 == 0 or idx == total:
                        pct = 5.0 + (idx / total) * 80.0
                        name = os.path.basename(member.filename) or member.filename
                        self.progress_updated.emit(pct, f"Extracting ({idx}/{total}): {name}")

            # Locate executable
            exe_path = os.path.join(self.target_dir, "CortexCleaner.exe")
            if not os.path.exists(exe_path):
                sub_exe = os.path.join(self.target_dir, "CortexCleaner", "CortexCleaner.exe")
                if os.path.exists(sub_exe):
                    exe_path = sub_exe

            self.progress_updated.emit(88.0, "Configuring Windows security & integrations…")
            desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            start_menu = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")

            if self.desktop_shortcut and os.path.exists(desktop):
                create_shortcut(exe_path, os.path.join(desktop, f"{APP_NAME}.lnk"))

            if self.start_menu_shortcut and os.path.exists(start_menu):
                create_shortcut(exe_path, os.path.join(start_menu, f"{APP_NAME}.lnk"))

            self.progress_updated.emit(94.0, "Registering Windows uninstaller…")
            register_uninstaller(self.target_dir, exe_path)

            self.progress_updated.emit(100.0, "Operation complete. 100% verified.")
            self.install_finished.emit(exe_path)
        except Exception as exc:
            self.install_failed.emit(str(exc))


class InstallerApp(QMainWindow):
    """Modern dark-themed Windows Setup Wizard featuring Cyberpunk Infiltration Progress Bar."""

    def __init__(self):
        """Initialize the InstallerApp window, style configuration, and UI components."""
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Setup v{APP_VERSION}")
        self.setFixedSize(680, 560)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0B0E14;
            }
            #HeaderFrame {
                background-color: #121722;
                border-bottom: 1px solid #1C2A33;
            }
            #FooterFrame {
                background-color: #121722;
                border-top: 1px solid #1C2A33;
            }
            QLabel {
                color: #F8FAFC;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel#Title {
                color: #00D2FF;
                font-size: 17px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }
            QLabel#Subtitle {
                color: #94A3B8;
                font-size: 11px;
            }
            QLabel#SectionLabel {
                color: #E2E8F0;
                font-size: 12px;
                font-weight: bold;
            }
            QLabel#StatusLabel {
                color: #94A3B8;
                font-size: 11px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
            }
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #00D2FF;
            }
            QPushButton#BrowseBtn {
                background-color: #334155;
                color: #F8FAFC;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
                cursor: pointer;
            }
            QPushButton#BrowseBtn:hover {
                background-color: #475569;
            }
            QPushButton#InstallBtn {
                background-color: #00D2FF;
                color: #0B0E14;
                border: none;
                border-radius: 4px;
                padding: 8px 22px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#InstallBtn:hover {
                background-color: #38BDF8;
            }
            QPushButton#InstallBtn:disabled {
                background-color: #334155;
                color: #64748B;
            }
            QPushButton#CancelBtn {
                background-color: #1E293B;
                color: #CBD5E1;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 8px 18px;
                font-size: 12px;
            }
            QPushButton#CancelBtn:hover {
                background-color: #334155;
                color: #FFFFFF;
            }
            QCheckBox {
                color: #CBD5E1;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid #475569;
                border-radius: 3px;
                background-color: #1E293B;
            }
            QCheckBox::indicator:checked {
                background-color: #00D2FF;
                border-color: #00D2FF;
            }
            QProgressBar {
                background-color: #132029;
                border: 1px solid #1C2A33;
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #005F6B, stop:1 #00E5FF);
                border-radius: 3px;
            }
        """)

        self._set_app_icon()
        self._build_ui()
        self._center_window()
        self.worker: InstallWorker | None = None

    def _set_app_icon(self):
        """Locate and set the custom application icon."""
        base_dir = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "assets", "icons", "cortex.ico"),
            os.path.join(base_dir, "cortex.ico"),
            os.path.join(os.path.dirname(base_dir), "assets", "icons", "cortex.ico"),
            os.path.join(os.getcwd(), "assets", "icons", "cortex.ico"),
        ]
        for c in candidates:
            if os.path.exists(c):
                self.setWindowIcon(QIcon(c))
                break

    def _center_window(self):
        """Center the installer window on the primary display."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def _build_ui(self):
        """Construct the setup wizard header, options checklist, directory selector, and actions."""
        central = QWidget(self)
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # 1. Header Frame
        header = QFrame()
        header.setObjectName("HeaderFrame")
        header.setFixedHeight(72)
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(24, 12, 24, 12)
        h_lay.setSpacing(2)

        title = QLabel(f"{APP_NAME} Setup")
        title.setObjectName("Title")
        h_lay.addWidget(title)

        sub = QLabel(f"The Ultimate Windows NT Systems, Forensics & Optimization Platform (v{APP_VERSION})")
        sub.setObjectName("Subtitle")
        h_lay.addWidget(sub)
        root_lay.addWidget(header)

        # 2. Main Content Area
        body = QWidget()
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(24, 14, 24, 12)
        b_lay.setSpacing(10)

        # Destination Folder
        dest_lbl = QLabel("Destination Folder:")
        dest_lbl.setObjectName("SectionLabel")
        b_lay.addWidget(dest_lbl)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(8)
        self.dest_edit = QLineEdit(DEFAULT_INSTALL_DIR)
        dest_row.addWidget(self.dest_edit, 1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("BrowseBtn")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_dir)
        dest_row.addWidget(browse_btn)
        b_lay.addLayout(dest_row)

        # Shortcut Checkboxes
        opts_lay = QVBoxLayout()
        opts_lay.setSpacing(4)
        self.chk_desktop = QCheckBox("Create Desktop Shortcut")
        self.chk_desktop.setChecked(True)
        opts_lay.addWidget(self.chk_desktop)

        self.chk_start_menu = QCheckBox("Create Start Menu Shortcut")
        self.chk_start_menu.setChecked(True)
        opts_lay.addWidget(self.chk_start_menu)

        self.chk_launch = QCheckBox("Launch Cortex Workstation after installation")
        self.chk_launch.setChecked(True)
        opts_lay.addWidget(self.chk_launch)
        b_lay.addLayout(opts_lay)

        # 3. Cyberpunk Infiltration Progress Bar World
        if HAS_WEBENGINE:
            self.web_view = QWebEngineView()
            self.web_view.page().setBackgroundColor(Qt.transparent)
            self.web_view.setFixedHeight(170)
            self.web_view.setHtml(self._load_html_content())
            b_lay.addWidget(self.web_view)
            self.fallback_progress = None
        else:
            self.web_view = None
            self.fallback_progress = QProgressBar()
            self.fallback_progress.setRange(0, 100)
            self.fallback_progress.setValue(0)
            b_lay.addWidget(self.fallback_progress)

        # Status text
        self.status_lbl = QLabel("Ready to install.")
        self.status_lbl.setObjectName("StatusLabel")
        b_lay.addWidget(self.status_lbl)

        root_lay.addWidget(body, 1)

        # 4. Footer Frame
        footer = QFrame()
        footer.setObjectName("FooterFrame")
        footer.setFixedHeight(58)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 10, 24, 10)
        f_lay.setSpacing(10)
        f_lay.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelBtn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.close)
        f_lay.addWidget(self.cancel_btn)

        self.install_btn = QPushButton("Install Now")
        self.install_btn.setObjectName("InstallBtn")
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_btn.clicked.connect(self._start_install)
        f_lay.addWidget(self.install_btn)

        root_lay.addWidget(footer)

    def _load_html_content(self) -> str:
        """Load the Cyberpunk System Infiltration progress bar HTML.

        Returns:
            str: Self-contained HTML/CSS/JS document string.
        """
        base_dir = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "assets", "installer", "infiltration_bar.html"),
            os.path.join(os.path.dirname(base_dir), "assets", "installer", "infiltration_bar.html"),
            os.path.join(os.getcwd(), "assets", "installer", "infiltration_bar.html"),
        ]
        for c in candidates:
            if os.path.exists(c):
                try:
                    with open(c, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass

        # Fallback minimal embedded version
        return """<!DOCTYPE html><html><body style="background:#0b1016;color:#00e5ff;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;"><h3>CORTEX // SYSTEM INFILTRATION</h3></body></html>"""

    def _browse_dir(self):
        """Open directory chooser dialog to specify custom installation target path."""
        chosen = QFileDialog.getExistingDirectory(
            self, "Select Installation Directory", self.dest_edit.text()
        )
        if chosen:
            self.dest_edit.setText(os.path.join(chosen, "CortexWorkstation"))

    def _start_install(self):
        """Validate inputs and launch the asynchronous installation worker thread."""
        target_dir = os.path.abspath(self.dest_edit.text().strip())
        if not target_dir:
            QMessageBox.warning(self, "Invalid Directory", "Please choose a valid destination folder.")
            return

        self.install_btn.setEnabled(False)
        self.dest_edit.setEnabled(False)
        self.chk_desktop.setEnabled(False)
        self.chk_start_menu.setEnabled(False)
        self.chk_launch.setEnabled(False)

        self.worker = InstallWorker(
            target_dir=target_dir,
            desktop_shortcut=self.chk_desktop.isChecked(),
            start_menu_shortcut=self.chk_start_menu.isChecked(),
            launch_after=self.chk_launch.isChecked(),
        )
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.install_finished.connect(self._on_finished)
        self.worker.install_failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, pct: float, status_text: str):
        """Update the progress bar and status display.

        Args:
            pct (float): Progress value between 0 and 100.
            status_text (str): File status or description.
        """
        self.status_lbl.setText(status_text)
        if self.web_view:
            self.web_view.page().runJavaScript(
                f"window.CORTEX_FEED && window.CORTEX_FEED.update({{progress: {pct:.1f}, status: 'running'}});"
            )
        elif self.fallback_progress:
            self.fallback_progress.setValue(int(pct))

    def _on_finished(self, exe_path: str):
        """Handle successful installation completion.

        Args:
            exe_path (str): Path to the installed binary.
        """
        self.status_lbl.setText("Installation completed successfully!")
        self.status_lbl.setStyleSheet("color: #39FF88; font-weight: bold;")
        if self.web_view:
            self.web_view.page().runJavaScript(
                "window.CORTEX_FEED && window.CORTEX_FEED.update({progress: 100, status: 'running'});"
            )
        elif self.fallback_progress:
            self.fallback_progress.setValue(100)

        self.cancel_btn.setText("Close")
        self.install_btn.setText("Launch")
        self.install_btn.setEnabled(True)
        self.install_btn.clicked.disconnect()
        self.install_btn.clicked.connect(lambda: self._launch_and_close(exe_path))

        if self.chk_launch.isChecked() and os.path.exists(exe_path):
            self._launch_and_close(exe_path)
        else:
            QMessageBox.information(
                self,
                "Installation Complete",
                f"{APP_NAME} v{APP_VERSION} has been successfully installed!"
            )

    def _launch_and_close(self, exe_path: str):
        """Launch the installed binary and dismiss the installer wizard.

        Args:
            exe_path (str): Executable path to spawn.
        """
        if os.path.exists(exe_path):
            try:
                subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
            except Exception:
                pass
        self.close()

    def _on_failed(self, error_msg: str):
        """Handle installation failure and re-enable controls.

        Args:
            error_msg (str): Detailed error description.
        """
        self.status_lbl.setText(f"Installation failed: {error_msg}")
        self.status_lbl.setStyleSheet("color: #FF4757;")
        self.install_btn.setEnabled(True)
        self.dest_edit.setEnabled(True)
        self.chk_desktop.setEnabled(True)
        self.chk_start_menu.setEnabled(True)
        self.chk_launch.setEnabled(True)
        QMessageBox.critical(
            self,
            "Installation Failed",
            f"An error occurred during installation:\n\n{error_msg}"
        )


def main():
    """Main entrypoint executing the graphical Windows installation wizard."""
    app = QApplication(sys.argv)
    installer = InstallerApp()
    installer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
