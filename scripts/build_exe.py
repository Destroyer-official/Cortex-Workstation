import os
import subprocess
import sys
import shutil

def build_app():
    print("=" * 60)
    print("Cortex Cleaner Suite - Release Compiler")
    print("=" * 60)
    
    # Clean previous builds
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
        "--windowed",           # Suppress terminal window on background
        "--noconfirm",          # Overwrite output dir automatically
        "--clean",              # Clean PyInstaller cache
        "--uac-admin",          # Request Windows Administrator privileges natively
        "--add-data", f"src{os.pathsep}src",  # Safely include entire module tree to catch dynamic refs
        "--log-level", "WARN",
        # Explicit module exclusions to drastically reduce final file size (Exclude data science packages)
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PyQt6",
        "run_gui.py"            # Our main entry point
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        print("Your military-grade standalone application has been compiled.")
        print(f"Location: {os.path.abspath('dist/CortexCleaner')}")
        print("You can zip this 'CortexCleaner' folder and distribute it to your customers!")
        print("Note: The executable 'CortexCleaner.exe' inside will automatically prompt UAC for Admin Rights.")
    except subprocess.CalledProcessError as e:
        print("\nBuild failed! Consult the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    build_app()
