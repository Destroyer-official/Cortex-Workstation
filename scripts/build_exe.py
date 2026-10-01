"""Compile run_gui.py into a distributable Windows executable and Setup wizard via PyInstaller.

Must be launched from the project root: 'build', 'dist', 'src' and 'run_gui.py'
are all resolved against the current working directory, not this script's location.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add src to sys.path for version lookup
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Console encoding resilience for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _safe_sym(sym: str, fallback: str) -> str:
    """Return symbol if encodable by stdout, else fallback."""
    try:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        sym.encode(enc)
        return sym
    except Exception:
        return fallback


CHECK_SYM = _safe_sym("✓", "[PASS]")

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


def write_checksum_file(target_file: str) -> str:
    """Write .sha256 checksum file alongside target file."""
    sha256_hash = calculate_sha256(target_file)
    sha256_file = target_file + ".sha256"
    with open(sha256_file, "w", encoding="ascii") as f:
        f.write(f"{sha256_hash} *{os.path.basename(target_file)}\n")
    print(f"[{CHECK_SYM}] SHA-256 Checksum: {sha256_hash}")
    print(f"[{CHECK_SYM}] Checksum file saved: {os.path.abspath(sha256_file)}")
    return sha256_hash


def ensure_brand_icons():
    """Ensure brand icon assets exist, generating them if absent."""
    if not os.path.exists("assets/icons/cortex.ico") or not os.path.exists("assets/icons/cortex.png"):
        print("[*] Generating brand icon assets...")
        subprocess.run([sys.executable, "scripts/generate_app_icon.py"], check=True)


def build_portable() -> str:
    """Compile CortexCleaner standalone package using cortex.spec."""
    print("=" * 60)
    print(f"Cortex Workstation v{APP_VERSION} - Standalone Portable Compiler")
    print("=" * 60)

    ensure_brand_icons()

    # Wipe leftovers from prior runs so dist/ reflects only this build
    if os.path.exists("build"):
        print("[*] Cleaning old build directory...")
        shutil.rmtree("build", ignore_errors=True)
    if os.path.exists("dist/CortexCleaner"):
        print("[*] Cleaning old dist/CortexCleaner directory...")
        shutil.rmtree("dist/CortexCleaner", ignore_errors=True)

    print("[*] Invoking PyInstaller with cortex.spec...")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--log-level",
        "WARN",
        "cortex.spec",
    ]

    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("PORTABLE BUILD SUCCESSFUL!")
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
        print(f"[{CHECK_SYM}] Distribution package created: {os.path.abspath(zip_file)}")

        write_checksum_file(zip_file)
        return zip_file

    except subprocess.CalledProcessError:
        print("\nPortable build failed! Consult the logs above.")
        sys.exit(1)


def build_installer() -> str:
    """Compile Cyberpunk Infiltration Setup Wizard using installer.spec."""
    print("\n" + "=" * 60)
    print(f"Cortex Workstation v{APP_VERSION} - Setup Wizard Compiler")
    print("=" * 60)

    ensure_brand_icons()

    zip_file = os.path.join("dist", f"Cortex-Workstation-v{APP_VERSION}-Windows-x64.zip")
    if not os.path.exists(zip_file):
        print("[*] Standalone zip package not found. Building portable distribution first...")
        build_portable()

    print("[*] Invoking PyInstaller with installer.spec...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--log-level",
        "WARN",
        "installer.spec",
    ]

    try:
        subprocess.run(cmd, check=True)
        setup_exe = os.path.join("dist", f"Cortex-Workstation-v{APP_VERSION}-Setup.exe")
        if os.path.exists(setup_exe):
            print("\n" + "=" * 60)
            print("SETUP WIZARD BUILD SUCCESSFUL!")
            print("=" * 60)
            print(f"[{CHECK_SYM}] Setup executable created: {os.path.abspath(setup_exe)}")
            write_checksum_file(setup_exe)
            return setup_exe
        else:
            print(f"[!] Warning: Expected setup binary at {setup_exe} not found.")
            return ""

    except subprocess.CalledProcessError:
        print("\nSetup wizard build failed! Consult the logs above.")
        sys.exit(1)


def main():
    """Parse CLI options and trigger requested build stages."""
    parser = argparse.ArgumentParser(description=f"Cortex Workstation v{APP_VERSION} Release Compiler")
    parser.add_argument(
        "--portable",
        action="store_true",
        help="Build standalone executable folder and portable zip archive",
    )
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Build Cyberpunk Setup Wizard (.exe)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build both portable distribution zip and setup wizard installer",
    )

    args = parser.parse_args()

    if args.all:
        build_portable()
        build_installer()
    elif args.installer:
        build_installer()
    else:
        # Default action: build portable distribution
        build_portable()


if __name__ == "__main__":
    main()
