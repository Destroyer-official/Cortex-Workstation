"""Generate an up-to-date, clean structure.txt of the entire repository."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "structure.txt"

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".hypothesis",
    ".mypy_cache",
    ".venv",
    "venv",
    "build",
    "dist",
    ".eggs",
    "*.egg-info",
}

EXCLUDE_FILES = {
    ".coverage",
}


def build_tree(dir_path: Path, prefix: str = "") -> list[str]:
    """build_tree."""
    lines = []
    try:
        entries = sorted(list(dir_path.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
    except (PermissionError, OSError):
        return lines

    filtered = []
    for e in entries:
        if e.is_dir() and e.name in EXCLUDE_DIRS:
            continue
        if e.is_file() and (e.name in EXCLUDE_FILES or e.suffix == ".pyc"):
            continue
        filtered.append(e)

    for i, entry in enumerate(filtered):
        is_last = i == (len(filtered) - 1)
        connector = "+-- " if is_last else "|-- "

        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            extension = "    " if is_last else "|   "
            lines.extend(build_tree(entry, prefix + extension))
        else:
            lines.append(f"{prefix}{connector}{entry.name}")

    return lines


def main():
    """main."""
    header = [
        "CORTEX CLEANER SUITE — PROJECT DIRECTORY STRUCTURE",
        "==================================================",
        f"Root: {ROOT.name}",
        "",
    ]
    tree_lines = build_tree(ROOT)
    full_text = "\n".join(header + tree_lines) + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"Updated {OUTPUT_FILE} with {len(tree_lines)} entries.")


if __name__ == "__main__":
    main()
