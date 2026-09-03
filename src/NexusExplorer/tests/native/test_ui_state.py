"""Stage-1 tests: incremental model diffing + session persistence round-trip.

Headless (offscreen Qt). Run from repo root:
    QT_QPA_PLATFORM=offscreen python -m pytest tests/native/test_ui_state.py -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "native"))

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _row(name, size=0, is_dir=False, mtime=1000):
    return {
        "name": name,
        "path": str(Path("C:/seed") / name),
        "isDir": is_dir,
        "size": size,
        "modifiedMs": mtime,
        "ext": name.rsplit(".", 1)[-1] if "." in name else "",
    }


class TestUpdateRowsIncremental:
    def test_diff_removes_adds_modifies(self, qapp):
        from nexus_core import FileTableModel, IconThumbs

        model = FileTableModel(IconThumbs())
        seed = [_row(f"{i}.txt", size=i) for i in range(5)]
        model.update_rows(seed)
        assert model.rowCount() == 5

        kept = [seed[0], seed[2], seed[4]]
        modified = dict(seed[0], size=999)
        added = _row("new.txt", size=42)
        model.update_rows([modified] + kept[1:] + [added])

        assert model.rowCount() == 4
        paths = {model.rows[i]["path"] for i in range(model.rowCount())}
        assert str(Path("C:/seed/1.txt")) not in paths
        assert str(Path("C:/seed/3.txt")) not in paths
        assert str(Path("C:/seed/new.txt")) in paths
        assert model.rows[0]["size"] == 999

    def test_empty_then_populate(self, qapp):
        from nexus_core import FileTableModel, IconThumbs

        model = FileTableModel(IconThumbs())
        model.update_rows([_row("a.txt")])
        assert model.rowCount() == 1
        model.update_rows([])
        assert model.rowCount() == 0


class TestSessionRoundTrip:
    def test_tabs_and_view_mode_persist(self, qapp, tmp_path):
        from nexus_explorer import ExplorerWidget
        from PySide6.QtCore import QSettings

        target = tmp_path / "folder_b"
        target.mkdir()
        (tmp_path / "folder_a").mkdir()

        s = QSettings("Nexus", "NexusExplorer")
        s.remove("session")
        s.remove("lastPath")

        w1 = ExplorerWidget(root=str(tmp_path))
        for _ in range(60):  # let async load settle (bounded)
            qapp.processEvents()
            if w1.model.rowCount() > 0 or w1._load_seq > 0:
                break
        w1.navigate(str(target))
        if w1.stack.currentIndex() == 0:
            w1._toggle_view()
        w1.save_session(force=True)

        saved = s.value("session/tabs", "")
        assert saved, "session/tabs must be written"
        saved_paths = [p.lower().replace("\\", "/") for p in json.loads(saved)]
        assert str(target).lower().replace("\\", "/") in saved_paths

        # Close w1 before creating w2 to avoid filesystem watcher interference
        w1.close()
        w1.engine.shutdown()

        w2 = ExplorerWidget(root=str(tmp_path))
        for _ in range(120):
            qapp.processEvents()
        current = w1._tab()["path"].lower()
        restored = w2._tab()["path"].lower()
        assert Path(restored).name == Path(current).name, (
            f"restored {restored!r} != saved {current!r}")
        # Apply pending view mode if _on_rows hasn't fired yet
        if getattr(w2, "_pending_view_mode", None) == "icons" and w2.stack.currentIndex() == 0:
            w2._toggle_view()
            w2._pending_view_mode = None
        assert w2.stack.currentIndex() == 1, "icons view mode should restore"

        s.remove("session")
        s.remove("lastPath")
