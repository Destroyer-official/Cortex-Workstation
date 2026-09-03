"""Insert docstrings for every undocumented function, method, and class.

Placement rules:
- Multi-line bodies: the docstring is inserted immediately before the first
  body statement (after the signature and any decorators on that statement).
- One-liner definitions (``def f(): return x``) are expanded to multi-line
  so a real docstring fits; the body is preserved exactly by splitting the
  line at the first statement's column offset.

Every rewritten file is re-parsed; on any failure the original content is
restored and the file is reported instead of being left broken.
"""
import ast
import pathlib
import sys


def _insert_line_for_first_stmt(first):
    """Return the 1-indexed line a docstring must precede.

    If the first body statement is itself decorated, the docstring has to
    go above its first decorator, not between decorator and def.
    """
    if isinstance(first, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
            and first.decorator_list:
        return min(d.lineno for d in first.decorator_list)
    return first.lineno


def build_ops(tree, lines):
    """Collect line-level insertion operations for undocumented nodes.

    Returns (ops, count) where ops maps a 0-indexed line number to
    {'inserts': [docstring lines], 'expand': (sig, doc, body) or None}.
    """
    ops = {}
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if ast.get_docstring(node):
            continue
        first = node.body[0]
        def_line = lines[node.lineno - 1]
        indent = len(def_line) - len(def_line.lstrip(" "))
        pad = " " * (indent + 4)
        doc = pad + f'"""{node.name}."""'
        if first.lineno == node.lineno:
            # One-liner definition: expand so the docstring fits.
            col = first.col_offset
            sig = def_line[:col].rstrip()
            body = def_line[col:].rstrip("\r\n")
            entry = ops.setdefault(node.lineno - 1, {"inserts": [], "expand": None})
            entry["expand"] = (sig, doc, pad + body)
        else:
            target = _insert_line_for_first_stmt(first)
            entry = ops.setdefault(target - 1, {"inserts": [], "expand": None})
            entry["inserts"].append(doc)
        count += 1
    return ops, count


def process_file(fp: pathlib.Path) -> int:
    """Add docstrings to one file. Returns the number of nodes documented."""
    src = fp.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        print(f"  SKIP (parse error) {fp.name}: {exc}")
        return 0
    eol = "\r\n" if "\r\n" in src[:2000] else "\n"
    lines = src.splitlines(keepends=True)
    ops, count = build_ops(tree, lines)
    if not count:
        return 0
    for k in sorted(ops, reverse=True):
        entry = ops[k]
        exp = entry["expand"]
        if exp:
            sig, doc, body = exp
            pieces = entry["inserts"] + [sig, doc, body]
        else:
            pieces = entry["inserts"] + [lines[k].rstrip("\r\n")]
        lines[k:k + 1] = [p + eol for p in pieces]
    new_src = "".join(lines)
    try:
        ast.parse(new_src)
    except SyntaxError as exc:
        print(f"  RESTORED {fp.name} (insert would break: {exc})")
        return 0
    fp.write_text(new_src, encoding="utf-8")
    return count


def collect(target: str):
    p = pathlib.Path(target)
    if p.is_file() and p.suffix == ".py":
        return [p]
    if p.is_dir():
        return [f for f in p.rglob("*.py") if "__pycache__" not in str(f)]
    return []


def main():
    total = 0
    for t in sys.argv[1:]:
        for f in collect(t):
            n = process_file(f)
            if n:
                print(f"  +{n} {f.name}")
                total += n
    print(f"Total docstrings added: {total}")


if __name__ == "__main__":
    main()
