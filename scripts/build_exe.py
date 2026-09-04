"""Compile run_gui.py into a distributable Windows executable via PyInstaller.

Must be launched from the project root: 'build', 'dist', 'src' and 'run_gui.py'
are all resolved against the current working directory, not this script's location.
"""
import os
import subprocess
import sys
import shutil

def build_app():
    """build_app.

    Manages build app operations and coordinates related state changes for the component.
    """
    print("=" * 60)
    print("Cortex Cleaner Suite - Release Compiler")
    print("=" * 60)
    
    # Wipe leftovers from prior runs so dist/ reflects only this build
    if os.path.exists("build"):
        print("[*] Cleaning old build directory...")
        shutil.rmtree("build", ignore_errors=True)
    if os.path.exists("dist"):
        print("[*] Cleaning old dist directory...")
        shutil.rmtree("dist", ignore_errors=True)
        
    print("[*] Invoking PyInstaller...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CortexCleaner",
        "--windowed",           # GUI product: end users must never see a console
        "--noconfirm",          # never stall an unattended build on the overwrite prompt
        "--clean",              # stale cache can resurrect modules deleted from src/
        "--uac-admin",          # registry/system cleanup needs elevation; prompt once at launch
        "--add-data", f"src{os.pathsep}src",  # Safely include entire module tree to catch dynamic refs
        "--log-level", "WARN",
        # Explicit module exclusions to drastically reduce final file size (Exclude data science packages)
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
        "run_gui.py"            # entry script PyInstaller crawls for dependencies
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        out_dir = os.path.abspath("dist/CortexCleaner")
        print(f"Location: {out_dir}")
        print("Note: The executable 'CortexCleaner.exe' inside will automatically prompt UAC for Admin Rights.")
        
        # Package into distributable zip archive
        zip_base = os.path.join("dist", "Cortex-Workstation-v1.2.0-Windows-x64")
        print(f"[*] Packaging standalone distribution zip: {zip_base}.zip ...")
        shutil.make_archive(zip_base, "zip", "dist", "CortexCleaner")
        print(f"[✓] Distribution package created: {os.path.abspath(zip_base + '.zip')}")
    except subprocess.CalledProcessError as e:
        print("\nBuild failed! Consult the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    build_app()
