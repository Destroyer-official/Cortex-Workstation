"""Exhaustive End-to-End Audit & Edge-Case Verification Suite for NexusExplorer."""
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from cortex_unified.explorer.widget import ExplorerWidget
from cortex_unified.explorer.transfers import TransferQueue
from cortex_unified.explorer.core import Engine
from NexusExplorer.native.nexus_explorer import (
    _nexus_clipboard,
    BulkRenameDialog,
    NestedFolderDialog,
    SearchDialog,
)


@pytest.fixture(scope="session")
def qapp():
    """Qapp.

    Manages qapp operations and coordinates related state changes for the component.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_audit_in_place_copy_protection(qapp):
    """Test copying a file into the same directory generates a duplicate safely without data loss.

    Manages test audit in place copy protection operations and coordinates related state changes for the component.

    Args:
        qapp: The qapp parameter.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "document.pdf"
        src.write_text("critical document contents", encoding="utf-8")

        class _DummyEngine:
            """Dummyengine.

            Manages DummyEngine operations and coordinates related state changes for the component.
            """
            ffi = None
            cli = ""

        tq = TransferQueue(_DummyEngine())
        completed = []
        tq.job_completed.connect(lambda jid, ok, msg: completed.append((jid, ok, msg)))

        # Copy in-place
        tq.enqueue("copy", [str(src)], dest=tmpdir)

        start = time.time()
        while not completed and time.time() - start < 5:
            qapp.processEvents()
            time.sleep(0.05)

        assert len(completed) == 1
        assert completed[0][1] is True
        # Verify original wasn't truncated
        assert src.read_text(encoding="utf-8") == "critical document contents"
        # Verify duplicate was created
        copy_file = Path(tmpdir) / "document - Copy.pdf"
        assert copy_file.exists()
        assert copy_file.read_text(encoding="utf-8") == "critical document contents"
        tq.stop()


def test_audit_circular_directory_protection(qapp):
    """Test that copying a folder into its own subfolder is prevented safely.

    Manages test audit circular directory protection operations and coordinates related state changes for the component.

    Args:
        qapp: The qapp parameter.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        parent_dir = Path(tmpdir) / "ParentDir"
        sub_dir = parent_dir / "SubDir"
        sub_dir.mkdir(parents=True)
        f = parent_dir / "test.txt"
        f.write_text("data", encoding="utf-8")

        class _DummyEngine:
            """Dummyengine.

            Manages DummyEngine operations and coordinates related state changes for the component.
            """
            ffi = None
            cli = ""

        tq = TransferQueue(_DummyEngine())
        completed = []
        tq.job_completed.connect(lambda jid, ok, msg: completed.append((jid, ok, msg)))

        # Attempt circular copy
        tq.enqueue("copy", [str(parent_dir)], dest=str(sub_dir))

        start = time.time()
        while not completed and time.time() - start < 5:
            qapp.processEvents()
            time.sleep(0.05)

        assert len(completed) == 1
        assert completed[0][1] is False
        assert "subfolder of itself" in completed[0][2]
        tq.stop()


def test_audit_empty_directory_preservation_on_copy(qapp):
    """Test copying nested directory tree preserves empty subdirectories.

    Manages test audit empty directory preservation on copy operations and coordinates related state changes for the component.

    Args:
        qapp: The qapp parameter.
    """
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        d1 = Path(src_dir) / "Tree" / "EmptyFolder1"
        d2 = Path(src_dir) / "Tree" / "EmptyFolder2"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        (Path(src_dir) / "Tree" / "file.txt").write_text("content", encoding="utf-8")

        class _DummyEngine:
            """Dummyengine.

            Manages DummyEngine operations and coordinates related state changes for the component.
            """
            ffi = None
            cli = ""

        tq = TransferQueue(_DummyEngine())
        completed = []
        tq.job_completed.connect(lambda jid, ok, msg: completed.append((jid, ok, msg)))

        tq.enqueue("copy", [str(Path(src_dir) / "Tree")], dest=dst_dir)

        start = time.time()
        while not completed and time.time() - start < 5:
            qapp.processEvents()
            time.sleep(0.05)

        assert len(completed) == 1
        assert completed[0][1] is True
        assert (Path(dst_dir) / "Tree" / "EmptyFolder1").is_dir()
        assert (Path(dst_dir) / "Tree" / "EmptyFolder2").is_dir()
        assert (Path(dst_dir) / "Tree" / "file.txt").is_file()
        tq.stop()


def test_audit_tab_management_and_closing(qapp):
    """Test creating multiple tabs and closing specific tabs without index corruption.

    Manages test audit tab management and closing operations and coordinates related state changes for the component.

    Args:
        qapp: The qapp parameter.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        d1 = Path(tmpdir) / "Tab1"
        d2 = Path(tmpdir) / "Tab2"
        d3 = Path(tmpdir) / "Tab3"
        d1.mkdir(); d2.mkdir(); d3.mkdir()

        w = ExplorerWidget(str(d1))
        initial_count = w.tabbar.count()
        w.add_tab(str(d2))
        w.add_tab(str(d3))
        assert w.tabbar.count() == initial_count + 2

        # Close the middle tab
        w._close_tab(1)
        assert w.tabbar.count() == initial_count + 1

        # Close tabs down to 1
        while w.tabbar.count() > 1:
            w._close_tab(0)
        assert w.tabbar.count() == 1

        # Closing last remaining tab should be ignored (keep at least 1)
        w._close_tab(0)
        assert w.tabbar.count() == 1

        w._transfer_queue.stop()
        w.deleteLater()
        qapp.processEvents()


def test_audit_engine_python_simple_and_delete(qapp):
    """Test Python fallback implementations for rename, delete, mkdir, and hash.

    Manages test audit engine python simple and delete operations and coordinates related state changes for the component.

    Args:
        qapp: The qapp parameter.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = Engine()
        test_f = Path(tmpdir) / "rename_me.txt"
        test_f.write_text("hashable content", encoding="utf-8")

        # 1. Rename
        done_results = []
        engine.simple(["rename", str(test_f), "renamed.txt"], lambda ok, out, err: done_results.append((ok, out, err)))
        assert len(done_results) == 1
        assert done_results[0][0] is True
        assert (Path(tmpdir) / "renamed.txt").exists()
        assert not test_f.exists()

        # 2. Hash
        hash_results = []
        engine.simple(["hash", str(Path(tmpdir) / "renamed.txt")], lambda ok, out, err: hash_results.append((ok, out, err)))
        assert len(hash_results) == 1
        assert hash_results[0][0] is True
        assert len(hash_results[0][1]) == 64  # SHA256 hex string

        # 3. Delete
        del_results = []
        engine.delete([str(Path(tmpdir) / "renamed.txt")], permanent=True, parent=None, on_done=lambda ok, msg: del_results.append((ok, msg)))
        start = time.time()
        while not del_results and time.time() - start < 3:
            qapp.processEvents()
            time.sleep(0.02)
        assert len(del_results) == 1
        assert del_results[0][0] is True
        assert not (Path(tmpdir) / "renamed.txt").exists()


def test_audit_bulk_rename_modes(qapp):
    """Test BulkRenameDialog rename transformations.

    Manages test audit bulk rename modes operations and coordinates related state changes for the component.

    Args:
        qapp: The qapp parameter.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = Path(tmpdir) / "IMG_101.jpg"
        f2 = Path(tmpdir) / "IMG_102.jpg"
        f1.write_text("img1", encoding="utf-8")
        f2.write_text("img2", encoding="utf-8")

        dlg = BulkRenameDialog([str(f1), str(f2)])

        # Mode 0: Find & Replace
        dlg.mode_combo.setCurrentIndex(0)
        dlg.fr_find.setText("IMG_")
        dlg.fr_replace.setText("Holiday_")
        assert dlg._rename_for_mode("IMG_101.jpg", 0) == "Holiday_101.jpg"

        # Mode 1: Sequential Numbering
        dlg.mode_combo.setCurrentIndex(1)
        dlg.sn_prefix.setText("Photo_")
        dlg.sn_start.setValue(1)
        dlg.sn_pad.setValue(3)
        assert dlg._rename_for_mode("IMG_101.jpg", 0) == "Photo_001.jpg"
        assert dlg._rename_for_mode("IMG_102.jpg", 1) == "Photo_002.jpg"

        # Mode 3: Case Transform (Upper/Lower)
        dlg.mode_combo.setCurrentIndex(3)
        dlg.ct_combo.setCurrentIndex(0)  # UPPER
        assert dlg._rename_for_mode("img_test.txt", 0) == "IMG_TEST.txt"
        dlg.ct_combo.setCurrentIndex(1)  # lower
        assert dlg._rename_for_mode("IMG_TEST.txt", 0) == "img_test.txt"

        dlg.close()
