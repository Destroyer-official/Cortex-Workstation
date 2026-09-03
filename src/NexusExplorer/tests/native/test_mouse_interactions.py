"""Regression tests for the mouse-interaction incident (2026-08-25):

1. Context menu must never receive row dicts where path strings are
   expected (TypeError: ... not dict crashed right-click).
2. Mouse XButton1/XButton2 (Back/Forward) route to pane history.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "native"))

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    """qapp."""
    app = QApplication.instance() or QApplication([])
    yield app


class _FakeMenu:
    """Stands in for QMenu so _context_menu can be exercised headless."""

    instances: list = []

    def __init__(self, parent=None):
        """__init__."""
        self.actions_list: list = []
        self.parent = parent
        _FakeMenu.instances.append(self)

    @classmethod
    def last_root_for(cls, widget):
        """last_root_for."""
        roots = [i for i in cls.instances if i.parent is widget]
        return roots[-1] if roots else None

    def addAction(self, text_or_action, slot=None):
        """addAction."""
        from PySide6.QtGui import QAction
        if isinstance(text_or_action, QAction):
            self.actions_list.append((text_or_action.text(), slot))
        else:
            self.actions_list.append((text_or_action, slot))

    def addSeparator(self):
        """addSeparator."""
        self.actions_list.append(("---", None))

    def addMenu(self, title):
        """addMenu."""
        sub = _FakeMenu(self)
        self.actions_list.append((title + " >", sub))
        return sub

    def exec(self, *_a, **_k):
        """exec."""
        return None


@pytest.fixture(scope="module")
def widget(qapp, tmp_path_factory):
    """widget."""
    import time

    from nexus_explorer import ExplorerWidget
    from PySide6.QtCore import QSettings

    # isolate from the user's real saved session
    s = QSettings("Nexus", "NexusExplorer")
    s.remove("session")
    s.remove("lastPath")

    tmp_path = tmp_path_factory.mktemp("mouse")
    (tmp_path / "sub").mkdir()
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")
    w = ExplorerWidget(root=str(tmp_path))
    deadline = time.time() + 15
    while time.time() < deadline and w.proxy.rowCount() == 0:
        qapp.processEvents()
        time.sleep(0.01)
    yield w
    w.close()
    s.remove("session")
    s.remove("lastPath")


def _select_first_data_row(w):
    """_select_first_data_row."""
    if w.proxy.rowCount() == 0:
        pytest.skip("no rows in model")
    w.table.selectRow(0)
    assert w.table.selectionModel().hasSelection()


def test_selected_paths_are_strings(widget):
    """test_selected_paths_are_strings."""
    _select_first_data_row(widget)
    paths = widget._selected_paths(widget.table)
    assert paths and all(isinstance(p, str) and p for p in paths)
    rows = widget._selected_rows(widget.table)
    assert isinstance(rows[0], dict)


def test_context_menu_handles_dict_selection(qapp, widget, monkeypatch):
    """test_context_menu_handles_dict_selection."""
    import nexus_explorer

    monkeypatch.setattr(nexus_explorer, "QMenu", _FakeMenu)
    _FakeMenu.instances.clear()
    _select_first_data_row(widget)
    widget._context_menu(QPoint(5, 5))  # must not raise
    menu = _FakeMenu.last_root_for(widget)
    texts = [t for t, _ in menu.actions_list]
    for expected in ("Open", "Copy Path", "Copy Filename", "Properties"):
        assert expected in texts, f"missing action {expected!r}"


def test_context_menu_empty_selection(qapp, widget, monkeypatch):
    """test_context_menu_empty_selection."""
    import nexus_explorer

    monkeypatch.setattr(nexus_explorer, "QMenu", _FakeMenu)
    _FakeMenu.instances.clear()
    widget.table.clearSelection()
    widget._context_menu(QPoint(5, 5))
    texts = [t for t, _ in _FakeMenu.last_root_for(widget).actions_list]
    assert "New folder" in texts


class _FakeMousePress:
    """_FakeMousePress."""
    def __init__(self, button):
        """__init__."""
        from PySide6.QtCore import QEvent

        self._type = QEvent.Type.MouseButtonPress
        self._button = button

    def type(self):
        """type."""
        return self._type

    def button(self):
        """button."""
        return self._button


def test_mouse_side_buttons_route_history(widget, qapp, tmp_path_factory):
    """test_mouse_side_buttons_route_history."""
    import time

    w = widget
    start = w._tab()["path"]
    target = tmp_path_factory.mktemp("sb") / "sub"
    target.mkdir(parents=True, exist_ok=True)
    w.navigate(str(target))
    deadline = time.time() + 5
    while time.time() < deadline and \
            Path(w._tab()["path"]) != target:
        qapp.processEvents()
        time.sleep(0.01)
    assert Path(w._tab()["path"]) == target

    # BackButton (XButton1) on the table viewport -> main pane goes back
    ev = _FakeMousePress(Qt.MouseButton.BackButton)
    assert w.eventFilter(w.table.viewport(), ev) is True
    deadline = time.time() + 5
    while time.time() < deadline and \
            Path(w._tab()["path"]) != Path(start):
        qapp.processEvents()
        time.sleep(0.01)
    assert Path(w._tab()["path"]) == Path(start)

    # ForwardButton (XButton2) -> forward again
    ev = _FakeMousePress(Qt.MouseButton.ForwardButton)
    assert w.eventFilter(w.table.viewport(), ev) is True
    deadline = time.time() + 5
    while time.time() < deadline and \
            Path(w._tab()["path"]) != target:
        qapp.processEvents()
        time.sleep(0.01)
    assert Path(w._tab()["path"]) == target


def test_show_properties_accepts_dict_and_str(widget, monkeypatch):
    """test_show_properties_accepts_dict_and_str."""
    calls = {}
    from nexus_explorer import PropertiesDialog

    class _FakeDlg:
        """_FakeDlg."""
        def __init__(self, row, parent):
            """__init__."""
            calls["row"] = row

        def exec(self):
            """exec."""
            return 0

    monkeypatch.setattr("nexus_explorer.PropertiesDialog", _FakeDlg)
    row = {"name": "file.txt", "path": str(widget._tab()["path"]),
           "isDir": False}
    widget._show_properties(row)
    assert calls["row"]["name"] == "file.txt"
    widget._show_properties(row["path"])
    assert calls["row"]["path"] == row["path"]
