"""Compile run_gui.py into a distributable Windows executable via PyInstaller.

Must be launched from the project root: 'build', 'dist', 'src' and 'run_gui.py'
are all resolved against the current working directory, not this script's location.
"""
import os
import subprocess
import sys
import shutil

def build_app():
    """Compile CortexCleaner standalone package using CortexCleaner.spec."""
    print("=" * 60)
    print("Cortex Workstation - Release Compiler")
    print("=" * 60)
    
    # Ensure brand icon exists
    if not os.path.exists("assets/icons/cortex.ico"):
        print("[*] Generating brand icon assets...")
        subprocess.run([sys.executable, "scripts/generate_app_icon.py"], check=True)

    # Wipe leftovers from prior runs so dist/ reflects only this build
    if os.path.exists("build"):
        print("[*] Cleaning old build directory...")
        shutil.rmtree("build", ignore_errors=True)
    if os.path.exists("dist/CortexCleaner"):
        print("[*] Cleaning old dist/CortexCleaner directory...")
        shutil.rmtree("dist/CortexCleaner", ignore_errors=True)
        
    print("[*] Invoking PyInstaller with CortexCleaner.spec...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--log-level", "WARN",
        "CortexCleaner.spec"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        out_dir = os.path.abspath("dist/CortexCleaner")
        print(f"Location: {out_dir}")
        print("Note: The executable 'CortexCleaner.exe' inside embeds the custom brand icon and UAC manifest.")
        
        # Package into distributable zip archive
        zip_base = os.path.join("dist", "Cortex-Workstation-v1.2.0-Windows-x64")
        if os.path.exists(zip_base + ".zip"):
            os.remove(zip_base + ".zip")
        print(f"[*] Packaging standalone distribution zip: {zip_base}.zip ...")
        shutil.make_archive(zip_base, "zip", "dist", "CortexCleaner")
        print(f"[✓] Distribution package created: {os.path.abspath(zip_base + '.zip')}")
    except subprocess.CalledProcessError as e:
        print("\nBuild failed! Consult the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    build_app()
