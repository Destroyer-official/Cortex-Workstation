"""Audit script to verify that all registered pages load their factory classes."""

import sys
import os

sys.path.insert(0, 'src')

from cortex_unified.ui.premium import registry

print("=== Auditing all registered pages in registry.py ===")
print(f"Total registered pages: {len(registry.PAGES)}")

failed_loads = []
loaded_specs = []

for spec in registry.PAGES:
    try:
        cls = spec.load()
        loaded_specs.append((spec, cls))
        print(f"[OK] {spec.id:15s} | Group: {spec.group:10s} | Class: {cls.__name__} in {cls.__module__}")
    except Exception as e:
        failed_loads.append((spec, str(e)))
        print(f"[FAIL] {spec.id:15s} | Group: {spec.group:10s} | ERROR: {e}")

print("\nSummary:")
print(f"  Loaded: {len(loaded_specs)} / {len(registry.PAGES)}")
print(f"  Failed: {len(failed_loads)}")
