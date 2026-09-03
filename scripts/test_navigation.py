import os
import sys

sys.path.insert(0, 'src')
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from cortex_unified.ui.premium.window import PremiumMainWindow
from cortex_unified.ui.premium.theme import apply_theme

app = QApplication.instance() or QApplication([])
apply_theme(app, "dark")
win = PremiumMainWindow("dark")

print(f"Total pages: {len(win._pages)}")
for i, pid in enumerate(list(win._pages)):
    print(f"[{i+1}/{len(win._pages)}] Selecting '{pid}'...", end=" ", flush=True)
    try:
        win._select(pid)
        current = win._stack.currentWidget()
        page = win._pages[pid]
        app.processEvents()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")

print("Done!")
win.close()
app.processEvents()
os._exit(0)
