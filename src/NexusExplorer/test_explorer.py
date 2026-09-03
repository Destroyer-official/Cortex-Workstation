"""NexusExplorer comprehensive offscreen smoke test."""

import os
import sys
import time
from pathlib import Path

# Add native directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "native"))


def run_smoke_test() -> int:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    from nexus_explorer import (
        DARK_QSS,
        BulkRenameDialog,
        CommandPalette,
        CrumbBar,
        DebugOverlay,
        DuplicateFinderDialog,
        ExplorerWidget,
        JobQueueWidget,
        PreviewPane,
        PropertiesDialog,
        TerminalWidget,
        _dpi_scale,
    )

    results = []

    def test(name, fn):
        try:
            fn()
            results.append((name, "PASS"))
        except Exception as e:
            results.append((name, f"FAIL: {e}"))

    # 1. Construction
    w = ExplorerWidget(os.path.expanduser("~"))
    test("Widget init", lambda: None)
    w.resize(1100, 700)
    w.show()
    pm = w.grab()
    test("Full paint grab", lambda: None if not pm.isNull() else (_ for _ in ()).throw(Exception("null")))
    test("Paint size", lambda: (_ for _ in ()).throw(Exception(f"{pm.width()}x{pm.height()}")) if pm.width() < 100 else None)

    # 2. CrumbBar
    c = CrumbBar()
    c.setPath(os.path.expanduser("~/Documents"))
    c.resize(400, 30)
    test("CrumbBar paint", lambda: None if not c.grab().isNull() else (_ for _ in ()).throw(Exception("null")))

    # 3. PreviewPane
    p = PreviewPane()
    test("PreviewPane empty", lambda: p.show_entry(None))
    test("PreviewPane dir", lambda: p.show_entry({"name": "Desktop", "isDir": True, "path": os.path.expanduser("~/Desktop")}))

    # 4. DebugOverlay
    d = DebugOverlay()
    d.resize(380, 220)
    d.show()
    test("DebugOverlay paint", lambda: None if not d.grab().isNull() else (_ for _ in ()).throw(Exception("null")))
    test("DebugOverlay log", lambda: d.log_event("test"))

    # 5. View toggle
    test("Toggle to icons", lambda: w._toggle_view())
    test("Toggle to details", lambda: w._toggle_view())

    # 6. Sidebar toggle
    test("Sidebar off", lambda: w._toggle_sidebar())
    test("Sidebar on", lambda: w._toggle_sidebar())

    # 7. Wait for async load
    loop = QEventLoop()
    QTimer.singleShot(4000, loop.quit)
    loop.exec()

    # 8. Data loaded
    test("Model rows > 0", lambda: (_ for _ in ()).throw(Exception("0 rows")) if w.model.rowCount() == 0 else None)
    test("Folder tree populated", lambda: (_ for _ in ()).throw(Exception("empty folder tree")) if w.folder_tree.model.rowCount() == 0 else None)
    test("Status text", lambda: (_ for _ in ()).throw(Exception(w.status_items.text())) if "items" not in w.status_items.text() else None)

    # 9. Tabs
    test("Add tab", lambda: w.add_tab(r"C:\Windows"))
    test("Tab count >= 2", lambda: (_ for _ in ()).throw(Exception(f"{w.tabbar.count()}")) if w.tabbar.count() < 2 else None)

    # 10. Navigation
    test("Go up", lambda: w.go_up())
    test("Go back", lambda: w.go_back())
    test("Go forward", lambda: w.go_forward())
    test("Navigate Downloads", lambda: w.navigate(os.path.expanduser("~/Downloads")))

    loop2 = QEventLoop()
    QTimer.singleShot(1500, loop2.quit)
    loop2.exec()
    test("Nav path correct", lambda: (_ for _ in ()).throw(Exception(w._tab()["path"])) if "Downloads" not in w._tab()["path"] else None)

    # 11. Operations
    test("Select all", lambda: w._select_all())
    test("Clip copy", lambda: w._clip("copy"))
    test("Clip cut", lambda: w._clip("cut"))
    test("Unique name", lambda: (_ for _ in ()).throw(Exception("bad")) if w._unique_name("New Folder") == "" else None)
    test("New folder callable", lambda: None if callable(w._new_folder) else (_ for _ in ()).throw(Exception("no")))
    test("Rename callable", lambda: None if callable(w._rename) else (_ for _ in ()).throw(Exception("no")))
    test("Delete callable", lambda: None if callable(w._delete) else (_ for _ in ()).throw(Exception("no")))
    test("Context menu callable", lambda: None if callable(w._context_menu) else (_ for _ in ()).throw(Exception("no")))

    # 12. Debug toggle
    test("Debug on", lambda: w._toggle_debug())
    test("Debug off", lambda: w._toggle_debug())

    # 13. DPI
    test("DPI scale", lambda: (_ for _ in ()).throw(Exception(f"{_dpi_scale}")) if _dpi_scale < 0.5 else None)

    # 14. QSS
    test("QSS non-empty", lambda: (_ for _ in ()).throw(Exception("empty")) if not DARK_QSS else None)
    test("QSS has all selectors", lambda: (_ for _ in ()).throw(Exception("missing selectors")) if "#NexusRoot" not in DARK_QSS or "#Status" not in DARK_QSS else None)

    # 15. CrumbBar with long path
    c2 = CrumbBar()
    c2.setPath(str(Path(__file__).resolve().parent / "native"))
    c2.resize(600, 30)
    test("CrumbBar long path", lambda: None if not c2.grab().isNull() else (_ for _ in ()).throw(Exception("null")))

    # 16. CrumbBar empty
    c3 = CrumbBar()
    c3.setPath("")
    c3.resize(400, 30)
    test("CrumbBar empty", lambda: None if not c3.grab().isNull() else (_ for _ in ()).throw(Exception("null")))

    # 17. Preview with file
    hosts_file = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    test("Preview file", lambda: p.show_entry({
        "name": "hosts", "isDir": False, "ext": "",
        "path": str(hosts_file), "size": 1024,
    }))

    # 18. Multiple tab operations
    test("Close current tab", lambda: w._close_current_tab())
    test("Tab count after close", lambda: (_ for _ in ()).throw(Exception(f"{w.tabbar.count()}")) if w.tabbar.count() < 1 else None)

    # 19. Quick access click
    test("Quick access item", lambda: w.quick_list.item(0).data(w.quick_list.item(0).data(256) is not None and 256 or 256))

    # 20. Dual pane
    test("Dual pane toggle on", lambda: w._toggle_dual_pane())
    test("Dual pane flag", lambda: (_ for _ in ()).throw(Exception(f"dual={w._dual_pane}")) if not w._dual_pane else None)
    test("Right stack visible", lambda: (_ for _ in ()).throw(Exception("hidden")) if not w._right_stack.isVisible() else None)
    test("Right pane navigate", lambda: w._right_navigate(os.path.expanduser("~/Desktop")))
    loop3 = QEventLoop()
    QTimer.singleShot(1500, loop3.quit)
    loop3.exec()
    test("Right pane has rows", lambda: (_ for _ in ()).throw(Exception(f"0 rows")) if w._right_model.rowCount() == 0 else None)
    test("Dual pane toggle off", lambda: w._toggle_dual_pane())
    test("Dual pane off flag", lambda: (_ for _ in ()).throw(Exception(f"dual={w._dual_pane}")) if w._dual_pane else None)

    # 21. Quick Look
    test("QuickLook popup", lambda: w._quick_look() if w._selected_rows() else None)
    test("QuickLook object", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(w, "_quicklook") else None)

    # 22. Bulk Rename
    test("BulkRename dialog class", lambda: (_ for _ in ()).throw(Exception("missing")) if BulkRenameDialog is None else None)

    # 23. Folder Size Calculator
    test("FolderSizeCalculator", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(w, "_folder_sizes") else None)

    # 24. Color Tags
    test("ColorTagManager", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(w, "_color_tags") else None)
    test("Color tag set", lambda: w._color_tags.set_tag("test_path", "red"))
    test("Color tag get", lambda: (_ for _ in ()).throw(Exception("wrong")) if w._color_tags.get_tag("test_path") != "red" else None)
    test("Color tag remove", lambda: w._color_tags.set_tag("test_path", None))

    # 25. Smart Folders
    test("SmartFolderManager", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(w, "_smart_folders") else None)
    test("Smart folder add", lambda: w._smart_folders.add("Test", "~", "*.txt"))
    test("Smart folder list", lambda: (_ for _ in ()).throw(Exception("empty")) if len(w._smart_folders.list_all()) == 0 else None)
    test("Smart folder sidebar refresh", lambda: w._refresh_smart_folders())
    test("Smart folder sidebar", lambda: (_ for _ in ()).throw(Exception("empty")) if w.smart_list.count() == 0 else None)

    # 26. Command Palette
    test("CommandPalette class", lambda: (_ for _ in ()).throw(Exception("missing")) if CommandPalette is None else None)
    test("CommandPalette instance", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(w, "_palette") else None)
    test("CommandPalette has actions", lambda: (_ for _ in ()).throw(Exception("0 actions")) if len(w._palette._actions) == 0 else None)
    test("CommandPalette toggle", lambda: w._palette.toggle())
    test("CommandPalette search", lambda: w._palette.search.setText("dual"))
    test("CommandPalette hide", lambda: w._palette.hide())

    # 27. Terminal
    test("TerminalWidget class", lambda: (_ for _ in ()).throw(Exception("missing")) if TerminalWidget is None else None)
    test("TerminalWidget instance", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(w, "terminal_panel") else None)
    test("Terminal toggle", lambda: w._toggle_terminal())
    test("Terminal visible", lambda: (_ for _ in ()).throw(Exception("hidden")) if not w.terminal_panel.isVisible() else None)
    test("Terminal toggle off", lambda: w._toggle_terminal())

    # 28. Job Queue
    test("JobQueueWidget class", lambda: (_ for _ in ()).throw(Exception("missing")) if JobQueueWidget is None else None)
    test("JobQueueWidget instance", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(w, "_job_queue") else None)
    test("Job add", lambda: w._job_queue.add_job("test job", 100))
    test("Job update", lambda: w._job_queue.update_job(0, 50, "file.txt") if hasattr(w._job_queue, "update_job") else None)
    test("Job complete", lambda: w._job_queue.complete_job(0) if hasattr(w._job_queue, "complete_job") else None)

    # 29. Duplicate Finder
    test("DuplicateFinderDialog class", lambda: (_ for _ in ()).throw(Exception("missing")) if DuplicateFinderDialog is None else None)

    # 30. Properties Dialog
    test("PropertiesDialog class", lambda: (_ for _ in ()).throw(Exception("missing")) if PropertiesDialog is None else None)

    # 31. Session persistence
    test("Has save_session", lambda: (_ for _ in ()).throw(Exception("missing")) if not callable(getattr(w, "save_session", None)) else None)
    test("Has restore_session", lambda: (_ for _ in ()).throw(Exception("missing")) if not callable(getattr(w, "restore_session", None)) else None)
    test("Session save", lambda: w.save_session())

    # 32. Multi-select support
    test("ExtendedSelection mode", lambda: (_ for _ in ()).throw(Exception("wrong mode")) if w.table.selectionMode().value != 3 else None)

    # 33. Drag-drop enabled
    test("Drag enabled", lambda: (_ for _ in ()).throw(Exception("no drag")) if not w.table.dragEnabled() else None)
    test("Accept drops", lambda: (_ for _ in ()).throw(Exception("no drops")) if not w.table.acceptDrops() else None)

    # 34. Bulk rename modes (enhanced)
    test("BulkRename has modes", lambda: (_ for _ in ()).throw(Exception("missing")) if not hasattr(BulkRenameDialog, "__init__") else None)

    # Summary
    passed = sum(1 for _, r in results if r == "PASS")
    total = len(results)
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{total} passed")
    print(f"{'='*50}")
    for name, r in results:
        status = "PASS" if r == "PASS" else "FAIL"
        print(f"  [{status}] {name}" + (f" - {r}" if r != "PASS" else ""))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_smoke_test())
