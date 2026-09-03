"""Audit script to inspect classes and functions across all system tools."""

import os
import inspect
import importlib
import sys

sys.path.insert(0, 'src')

tools_dir = 'src/cortex_unified/system_tools'
print("=== System Tools Audit ===")
for f in sorted(os.listdir(tools_dir)):
    if f.endswith('.py') and not f.startswith('__'):
        mod_name = f[:-3]
        p = os.path.join(tools_dir, f)
        size = os.path.getsize(p)
        try:
            mod = importlib.import_module(f'cortex_unified.system_tools.{mod_name}')
            classes = [c for c in dir(mod) if isinstance(getattr(mod, c), type) and not c.startswith('_')]
            funcs = [fn for fn in dir(mod) if inspect.isfunction(getattr(mod, fn)) and not fn.startswith('_')]
            print(f"{mod_name:25s} | {size:6d}B | Classes: {len(classes):2d} ({', '.join(classes[:4])}) | Funcs: {len(funcs):2d}")
        except Exception as e:
            print(f"{mod_name:25s} | {size:6d}B | FAILED IMPORT: {e}")
