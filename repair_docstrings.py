"""Remove auto-generated docstring artifacts left by earlier passes.

Strips lines matching the generated one-word docstring patterns (standalone
lines or docstrings appended to a code line), then verifies the cleaned file
still parses. Files that would not parse after cleanup are left untouched
and reported so they can be fixed manually.
"""
import ast
import pathlib
import re
import sys

STANDALONE = re.compile(r'^\s*"""[A-Za-z_][A-Za-z0-9_]*\.( class)?\."""\s*$')
APPENDED = re.compile(r'^(.*\S)\s{2,}"""[A-Za-z_][A-Za-z0-9_]*\.( class)?\."""\s*$')


def repair_file(fp: pathlib.Path):
    """Strip generated docstring artifacts from one file.

    Returns (removed_count, ok). ok is False when cleanup would leave the
    file unparseable; the original content is then preserved.
    """
    src = fp.read_text(encoding="utf-8", errors="replace")
    out = []
    removed = 0
    for ln in src.splitlines(keepends=True):
        body = ln.rstrip("\r\n")
        eol = ln[len(body):]
        if STANDALONE.match(body):
            removed += 1
            continue
        m = APPENDED.match(body)
        if m:
            out.append(m.group(1) + eol)
            removed += 1
            continue
        out.append(ln)
    if not removed:
        return 0, True
    cleaned = "".join(out)
    try:
        ast.parse(cleaned)
    except SyntaxError:
        return 0, False
    fp.write_text(cleaned, encoding="utf-8")
    return removed, True


def collect(target: str):
    p = pathlib.Path(target)
    if p.is_file() and p.suffix == ".py":
        return [p]
    if p.is_dir():
        return [f for f in p.rglob("*.py") if "__pycache__" not in str(f)]
    return []


def main():
    total = 0
    broken = []
    for t in sys.argv[1:]:
        for f in collect(t):
            try:
                n, ok = repair_file(f)
                total += n
                if not ok:
                    broken.append(str(f))
            except Exception as exc:  # noqa: BLE001
                broken.append(f"{f}: {exc}")
    print(f"artifacts removed: {total}")
    if broken:
        print("UNREPAIRABLE:")
        for b in broken:
            print("  " + b)


if __name__ == "__main__":
    main()
