"""Cortex Workstation Windows Setup Installer.

A standalone graphical installer that deploys Cortex Workstation into
%LOCALAPPDATA%\\Programs\\CortexWorkstation, creates Desktop & Start Menu
shortcuts, registers an uninstaller, and launches the application.
"""
from __future__ import annotations

import os
import sys
import shutil
import zipfile
import threading
import subprocess
import winreg
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

APP_NAME = "Cortex Workstation"
APP_VERSION = "1.2.0"
DEFAULT_INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "CortexWorkstation")


def get_bundle_zip() -> str:
    """Locate the bundled distribution zip file."""
    # 1. PyInstaller onefile temp folder
    base_dir = getattr(sys, "_MEIPASS", None)
    if base_dir:
        candidate = os.path.join(base_dir, "Cortex-Workstation-v1.2.0-Windows-x64.zip")
        if os.path.exists(candidate):
            return candidate
    # 2. Local dist folder relative to script or exe
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist", "Cortex-Workstation-v1.2.0-Windows-x64.zip"),
        os.path.join(os.path.dirname(sys.executable), "Cortex-Workstation-v1.2.0-Windows-x64.zip"),
        os.path.join(os.getcwd(), "dist", "Cortex-Workstation-v1.2.0-Windows-x64.zip"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    raise FileNotFoundError("Could not find bundled distribution package 'Cortex-Workstation-v1.2.0-Windows-x64.zip'.")


def create_shortcut(target_exe: str, shortcut_path: str, description: str = APP_NAME) -> bool:
    """Create a Windows .lnk shortcut via PowerShell WScript.Shell with embedded icon."""
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
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd], capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def register_uninstaller(install_dir: str, exe_path: str) -> None:
    """Register the application in Windows Installed Apps registry with custom icon."""
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


class InstallerApp(tk.Tk):
    """Modern dark-themed Windows Setup Wizard."""

    def __init__(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Destroyer.CortexWorkstation.Installer.1.2.0")
        except Exception:
            pass

        super().__init__()
        self.title(f"{APP_NAME} Setup v{APP_VERSION}")
        self.geometry("580x420")
        self.resizable(False, False)
        self.configure(bg="#0B0E14")

        # Set custom brand icon on the installer window and all child dialogs
        self._set_app_icon()

        self.install_dir_var = tk.StringVar(value=DEFAULT_INSTALL_DIR)
        self.desktop_shortcut_var = tk.BooleanVar(value=True)
        self.start_menu_var = tk.BooleanVar(value=True)
        self.launch_after_var = tk.BooleanVar(value=True)
        self.is_installing = False

        self._build_ui()
        self._center_window()

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
                try:
                    self.iconbitmap(default=c)
                    break
                except Exception:
                    pass

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#121722", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_lbl = tk.Label(header, text=f"{APP_NAME} Setup", font=("Segoe UI", 16, "bold"), fg="#00D2FF", bg="#121722")
        title_lbl.pack(anchor="w", padx=20, pady=(14, 2))

        sub_lbl = tk.Label(header, text=f"The Ultimate Windows NT Systems, Forensics & Optimization Platform (v{APP_VERSION})",
                           font=("Segoe UI", 9), fg="#94A3B8", bg="#121722")
        sub_lbl.pack(anchor="w", padx=20)

        # Content frame
        content = tk.Frame(self, bg="#0B0E14")
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        # Destination selector
        dest_lbl = tk.Label(content, text="Destination Folder:", font=("Segoe UI", 10, "bold"), fg="#E2E8F0", bg="#0B0E14")
        dest_lbl.pack(anchor="w", pady=(0, 4))

        dest_row = tk.Frame(content, bg="#0B0E14")
        dest_row.pack(fill=tk.X, pady=(0, 14))

        self.dest_entry = tk.Entry(dest_row, textvariable=self.install_dir_var, font=("Segoe UI", 9),
                                   bg="#1E293B", fg="#F8FAFC", insertbackground="#00D2FF", relief=tk.FLAT)
        self.dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))

        browse_btn = tk.Button(dest_row, text="Browse…", font=("Segoe UI", 9), bg="#334155", fg="#F8FAFC",
                               activebackground="#475569", activeforeground="#FFFFFF", relief=tk.FLAT,
                               cursor="hand2", command=self._browse_dir)
        browse_btn.pack(side=tk.RIGHT, ipadx=8, ipady=2)

        # Options frame
        opts_frame = tk.Frame(content, bg="#0B0E14")
        opts_frame.pack(fill=tk.X, pady=(0, 10))

        c1 = tk.Checkbutton(opts_frame, text="Create Desktop Shortcut", variable=self.desktop_shortcut_var,
                            font=("Segoe UI", 9), fg="#CBD5E1", bg="#0B0E14", activebackground="#0B0E14",
                            activeforeground="#00D2FF", selectcolor="#1E293B")
        c1.pack(anchor="w", pady=2)

        c2 = tk.Checkbutton(opts_frame, text="Create Start Menu Shortcut", variable=self.start_menu_var,
                            font=("Segoe UI", 9), fg="#CBD5E1", bg="#0B0E14", activebackground="#0B0E14",
                            activeforeground="#00D2FF", selectcolor="#1E293B")
        c2.pack(anchor="w", pady=2)

        c3 = tk.Checkbutton(opts_frame, text="Launch Cortex Workstation after installation", variable=self.launch_after_var,
                            font=("Segoe UI", 9), fg="#CBD5E1", bg="#0B0E14", activebackground="#0B0E14",
                            activeforeground="#00D2FF", selectcolor="#1E293B")
        c3.pack(anchor="w", pady=2)

        # Progress bar
        self.progress = ttk.Progressbar(content, orient=tk.HORIZONTAL, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(10, 4))

        self.status_lbl = tk.Label(content, text="Ready to install.", font=("Segoe UI", 9), fg="#94A3B8", bg="#0B0E14")
        self.status_lbl.pack(anchor="w")

        # Footer actions
        footer = tk.Frame(self, bg="#121722", height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        cancel_btn = tk.Button(footer, text="Cancel", font=("Segoe UI", 9), bg="#1E293B", fg="#CBD5E1",
                               relief=tk.FLAT, cursor="hand2", command=self.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 20), pady=12, ipadx=12, ipady=3)

        self.install_btn = tk.Button(footer, text="Install Now", font=("Segoe UI", 9, "bold"), bg="#00D2FF", fg="#0B0E14",
                                     activebackground="#38BDF8", activeforeground="#000000", relief=tk.FLAT,
                                     cursor="hand2", command=self._start_install)
        self.install_btn.pack(side=tk.RIGHT, padx=(0, 10), pady=12, ipadx=16, ipady=3)

    def _browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir_var.get(), title="Select Installation Directory")
        if chosen:
            self.install_dir_var.set(os.path.join(chosen, "CortexWorkstation"))

    def _start_install(self):
        if self.is_installing:
            return
        self.is_installing = True
        self.install_btn.config(state=tk.DISABLED, bg="#334155")
        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_install(self):
        target_dir = os.path.abspath(self.install_dir_var.get())
        try:
            self.status_lbl.config(text="Locating distribution archive…")
            zip_path = get_bundle_zip()

            self.status_lbl.config(text="Preparing destination folder…")
            os.makedirs(target_dir, exist_ok=True)

            self.status_lbl.config(text="Extracting application files…")
            with zipfile.ZipFile(zip_path, "r") as zf:
                members = zf.infolist()
                total = len(members)
                self.progress["maximum"] = total
                for idx, member in enumerate(members, 1):
                    zf.extract(member, target_dir)
                    if idx % 20 == 0 or idx == total:
                        self.progress["value"] = idx
                        self.status_lbl.config(text=f"Extracting ({idx}/{total}): {os.path.basename(member.filename)}")

            # Find executable
            exe_path = os.path.join(target_dir, "CortexCleaner.exe")
            if not os.path.exists(exe_path):
                sub_exe = os.path.join(target_dir, "CortexCleaner", "CortexCleaner.exe")
                if os.path.exists(sub_exe):
                    exe_path = sub_exe

            self.status_lbl.config(text="Configuring Windows integration…")
            # Create shortcuts
            desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            start_menu = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")

            if self.desktop_shortcut_var.get() and os.path.exists(desktop):
                create_shortcut(exe_path, os.path.join(desktop, f"{APP_NAME}.lnk"))

            if self.start_menu_var.get() and os.path.exists(start_menu):
                create_shortcut(exe_path, os.path.join(start_menu, f"{APP_NAME}.lnk"))

            # Register in Windows Add/Remove Programs
            register_uninstaller(target_dir, exe_path)

            self.progress["value"] = total
            self.status_lbl.config(text="Installation completed successfully!", fg="#10B981")

            if self.launch_after_var.get() and os.path.exists(exe_path):
                subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))

            self.after(500, self._install_success)
        except Exception as err:
            self.is_installing = False
            self.install_btn.config(state=tk.NORMAL, bg="#00D2FF")
            self.status_lbl.config(text=f"Error: {err}", fg="#EF4444")
            messagebox.showerror("Installation Failed", f"An error occurred during installation:\n\n{err}", parent=self)

    def _install_success(self):
        messagebox.showinfo("Installation Complete", f"{APP_NAME} v{APP_VERSION} has been installed successfully!", parent=self)
        self.destroy()


def main():
    app = InstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
