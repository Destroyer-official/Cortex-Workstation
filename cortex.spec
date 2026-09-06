# -*- mode: python ; coding: utf-8 -*-
"""Unified PyInstaller spec file for Cortex Workstation.

Dynamically resolves version metadata from cortex_unified.__version__ or CORTEX_VERSION.
Enforces UAC administrator execution level and bundles all required assets.
"""
import os
import sys

src_dir = os.path.abspath("src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    import cortex_unified
    app_version = getattr(cortex_unified, "__version__", "1.2.0")
except Exception:
    app_version = "1.2.0"

app_version = os.environ.get("CORTEX_VERSION", app_version)
app_name = os.environ.get("CORTEX_APP_NAME", "CortexCleaner")

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

cortex_submodules = collect_submodules("cortex_unified")
cortex_datas = collect_data_files("cortex_unified")
nexus_submodules = collect_submodules("NexusExplorer")

a = Analysis(
    ["run_gui.py"],
    pathex=[src_dir],
    binaries=[],
    datas=[
        ("assets/icons", "assets/icons"),
        ("src/cortex_unified/resources", "src/cortex_unified/resources"),
    ] + cortex_datas,
    hiddenimports=[
        "logging.handlers",
        "sqlite3",
        "ctypes",
        "ctypes.wintypes",
        "winreg",
        "wmi",
        "psutil",
        "queue",
        "concurrent.futures",
        "dataclasses",
        "uuid",
        "shutil",
        "tempfile",
        "hashlib",
        "inspect",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
    ] + cortex_submodules + nexus_submodules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "numpy", "scipy", "pandas", "PyQt5", "PyQt6",
        "torch", "torchvision", "torchaudio", "sympy", "IPython",
        "jupyter", "notebook", "tensorboard"
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon="assets/icons/cortex.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)
