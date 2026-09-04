"""Static import health audit for the cortex_unified package.

Parses every module under src/cortex_unified with ast and reports:
syntax errors, internal imports that point at nonexistent modules, and
names imported from internal modules that don't define them (star imports
from internal modules are resolved one level deep).

MUST run from the project root -- SRC is the relative path 'src'.
"""
import ast, sys, os
from pathlib import Path

SRC = Path("src")
PKG = "cortex_unified"
pkg_root = SRC / PKG

# Build module map: dotted name -> file path
modules = {}
for p in pkg_root.rglob("*.py"):
    rel = p.relative_to(SRC).with_suffix("")
    dotted = ".".join(rel.parts)
    modules[dotted] = p
    if p.name == "__init__.py":
        modules[".".join(rel.parts[:-1])] = p

# Collect top-level symbols per module (classes, functions, assignments, imports-as)
def module_symbols(path):
    """module_symbols.

    Manages module symbols operations and coordinates related state changes for the component.

    Args:
        path: Filesystem path to the target file or directory.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None
    syms = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            syms.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    syms.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            syms.add(node.target.id)
        elif isinstance(node, ast.Import):
            for a in node.names:
                syms.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name != "*":
                    syms.add(a.asname or a.name)
        elif isinstance(node, (ast.If, ast.Try)):  # conditional defs and constants
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    syms.add(sub.name)
                elif isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            syms.add(t.id)
                elif isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                    syms.add(sub.target.id)
                elif isinstance(sub, ast.ImportFrom):
                    for a in sub.names:
                        if a.name != "*":
                            syms.add(a.asname or a.name)
    # star imports from internal modules
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            if node.module and node.module.startswith(PKG):
                tgt = modules.get(node.module)
                if tgt:
                    s = module_symbols(tgt)
                    if s:
                        syms |= s
    return syms

sym_cache = {}
def get_syms(modname):
    """get_syms.

    Manages get syms operations and coordinates related state changes for the component.

    Args:
        modname: The modname parameter.
    """
    if modname not in sym_cache:
        path = modules.get(modname)
        sym_cache[modname] = module_symbols(path) if path else None
    return sym_cache[modname]

syntax_errors = []
missing_modules = []
missing_symbols = []

for dotted, path in sorted(modules.items()):
    if path.name == "__init__.py" and dotted.count(".") < PKG.count("."):
        continue
    try:
        src_text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src_text)
    except SyntaxError as e:
        syntax_errors.append(f"{path}:{e.lineno}: {e.msg}")
        continue
    # absolute dotted name of the importing module's package:
    # anchor for resolving level-N relative imports below
    pkg_parts = path.relative_to(SRC).with_suffix("").parts
    if path.name == "__init__.py":
        base = list(pkg_parts[:-1])
    else:
        base = list(pkg_parts[:-1])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == PKG or a.name.startswith(PKG + "."):
                    if a.name not in modules:
                        missing_modules.append(f"{path}:{node.lineno}: import {a.name} -> module not found")
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # relative import
                anchor = base[: len(base) - (node.level - 1)]
                mod = ".".join(anchor + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            if mod == PKG or mod.startswith(PKG + "."):
                if mod not in modules:
                    missing_modules.append(f"{path}:{node.lineno}: from {mod} import ... -> module not found")
                else:
                    syms = get_syms(mod)
                    if syms is not None:
                        for a in node.names:
                            if a.name == "*":
                                continue
                            if a.name not in syms:
                                # might be a submodule import: from pkg import submod
                                sub = mod + "." + a.name
                                if sub not in modules:
                                    missing_symbols.append(f"{path}:{node.lineno}: from {mod} import {a.name} -> not found in {modules[mod]}")

print("=== SYNTAX ERRORS ===")
print("\n".join(syntax_errors) or "(none)")
print("\n=== MISSING MODULES ===")
print("\n".join(missing_modules) or "(none)")
print("\n=== MISSING SYMBOLS ===")
print("\n".join(missing_symbols) or "(none)")
