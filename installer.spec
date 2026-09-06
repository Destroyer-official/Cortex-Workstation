# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for the Cortex Workstation Cyberpunk Setup Installer."""
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

app_name = f"Cortex-Workstation-v{app_version}-Setup"

a = Analysis(
    ['scripts/installer.py'],
    pathex=[src_dir],
    binaries=[],
    datas=[
        ('dist/Cortex-Workstation-v1.2.0-Windows-x64.zip', '.'),
        ('assets/icons/cortex.ico', 'assets/icons'),
        ('assets/icons/cortex.png', 'assets/icons'),
        ('assets/installer/infiltration_bar.html', 'assets/installer'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'subprocess',
        'zipfile',
        'shutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas', 'PyQt5', 'PyQt6',
        'torch', 'torchvision', 'torchaudio', 'sympy', 'IPython',
        'jupyter', 'notebook'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon='assets/icons/cortex.ico',
)
