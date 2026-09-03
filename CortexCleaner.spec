# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Cortex Cleaner premium GUI.

Build (from the repo root):
    pyinstaller CortexCleaner.spec --noconfirm

Notes
-----
* ``upx`` is deliberately OFF everywhere: UPX-packed Qt plugin DLLs are known
  to corrupt at load time, and packed executables are a strong antivirus
  heuristic trigger for cleaner-type tools.
* ``pathex=['src']`` lets Analysis trace the ``cortex_unified`` package so its
  modules are compiled into the bundle; the raw ``datas`` copy of ``src`` is
  kept only as a fallback for resources discovered at runtime (icons/locales).
* Sibling Qt bindings are excluded explicitly - PyInstaller >= 6.5 aborts a
  bundle containing more than one binding.
"""

a = Analysis(
    ['run_gui.py'],
    pathex=['src'],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'PyQt5', 'PyQt6',          # sibling bindings: never bundle twice
        'tkinter',
        'pytest', '_pytest',
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
    name='CortexCleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # The GUI runs asInvoker and elevates only specific operations through
    # UAC dialogs; a fully-admin process is unnecessary attack surface.
    uac_admin=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CortexCleaner',
)
