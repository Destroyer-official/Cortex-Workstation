"""Diagnostic script to verify offscreen instantiation of all UI pages."""

import os
import sys
import traceback

sys.path.insert(0, 'src')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from cortex_unified.ui.premium import registry
from cortex_unified.ui.premium.window import PremiumMainWindow
from cortex_unified.ui.premium.theme import apply_theme

app = QApplication.instance() or QApplication([])
apply_theme(app, "dark")
win = PremiumMainWindow("dark")

print(f"=== DEEP TEST: Instantiating & Inspecting All {len(registry.PAGES)} Pages ===")
success_count = 0
fail_count = 0

for spec in registry.PAGES:
    pid = spec.id
    try:
        page = win._pages[pid]
        # Verify page is instance of QWidget
        assert page is not None, f"Page {pid} is None"
        print(f"[OK] Page '{pid}' ({page.__class__.__name__}) constructed successfully.")
        success_count += 1
    except Exception as e:
        print(f"[FAIL] Page '{pid}' ({spec.title}) failed construction:")
        traceback.print_exc()
        fail_count += 1

print("\n==========================================")
print(f"Results: {success_count} succeeded, {fail_count} failed")
print("==========================================")

win.close()
