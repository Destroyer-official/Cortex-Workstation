"""Compile run_gui.py into a distributable Windows executable via PyInstaller.

Must be launched from the project root: 'build', 'dist', 'src' and 'run_gui.py'
are all resolved against the current working directory, not this script's location.
"""
import os
import subprocess
import sys
import shutil
import hashlib
from pathlib import Path

# Add src to sys.path for version lookup
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    import cortex_unified
    APP_VERSION = getattr(cortex_unified, "__version__", "1.2.0")
except Exception:
    APP_VERSION = "1.2.0"


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_app():
    """Compile CortexCleaner standalone package using cortex.spec."""
    print("=" * 60)
    print(f"Cortex Workstation v{APP_VERSION} - Release Compiler")
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

    print("[*] Invoking PyInstaller with cortex.spec...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--log-level", "WARN",
        "cortex.spec"
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
        zip_base = os.path.join("dist", f"Cortex-Workstation-v{APP_VERSION}-Windows-x64")
        zip_file = zip_base + ".zip"
        if os.path.exists(zip_file):
            os.remove(zip_file)
        print(f"[*] Packaging standalone distribution zip: {zip_file} ...")
        shutil.make_archive(zip_base, "zip", "dist", "CortexCleaner")
        print(f"[✓] Distribution package created: {os.path.abspath(zip_file)}")

        # Calculate and write SHA-256 checksum
        sha256_hash = calculate_sha256(zip_file)
        sha256_file = zip_file + ".sha256"
        with open(sha256_file, "w", encoding="ascii") as f:
            f.write(f"{sha256_hash} *{os.path.basename(zip_file)}\n")
        print(f"[✓] SHA-256 Checksum: {sha256_hash}")
        print(f"[✓] Checksum file saved: {os.path.abspath(sha256_file)}")

    except subprocess.CalledProcessError:
        print("\nBuild failed! Consult the logs above.")
        sys.exit(1)


if __name__ == "__main__":
    build_app()
