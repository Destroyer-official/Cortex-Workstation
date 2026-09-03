"""Tests for the Interactive Staging Shelf & Clipboard Dock in NexusExplorer."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QUrl, QMimeData
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    """qapp."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_nexus_clipboard_cut_copy_clear(qapp):
    """test_nexus_clipboard_cut_copy_clear."""
    from cortex_unified.explorer.widget import NexusClipboard

    clip = NexusClipboard()
    received = []
    clip.changed.connect(lambda mode, paths: received.append((mode, paths)))

    # Test copy
    clip.copy(["/tmp/file1.txt", "/tmp/file2.txt"])
    assert clip.has_data is True
    assert clip.paste() == ("copy", ["/tmp/file1.txt", "/tmp/file2.txt"])
    assert len(received) == 1
    assert received[-1] == ("copy", ["/tmp/file1.txt", "/tmp/file2.txt"])

    # Test cut
    clip.cut(["/tmp/file3.txt"])
    assert clip.paste() == ("cut", ["/tmp/file3.txt"])
    assert received[-1] == ("cut", ["/tmp/file3.txt"])

    # Test clear
    clip.clear()
    assert clip.has_data is False
    assert clip.paste() is None
    assert received[-1] == ("", [])


def test_staging_shelf_widget_basic(qapp):
    """test_staging_shelf_widget_basic."""
    from cortex_unified.explorer.widget import StagingShelfWidget

    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = Path(tmpdir) / "test1.txt"
        f2 = Path(tmpdir) / "test2.txt"
        f1.write_text("hello 1", encoding="utf-8")
        f2.write_text("hello 2", encoding="utf-8")

        shelf = StagingShelfWidget()
        shelf.set_current_folder(tmpdir)

        # Initial state: empty
        assert len(shelf._staged_paths) == 0
        assert not shelf.empty_card.isHidden()
        assert shelf.list_widget.isHidden()
        assert shelf.btn_paste.isEnabled() is False

        # Add paths
        shelf.add_paths([str(f1), str(f2)], mode="copy")
        assert len(shelf._staged_paths) == 2
        assert shelf.empty_card.isHidden()
        assert not shelf.list_widget.isHidden()
        assert shelf.btn_paste.isEnabled() is True
        assert shelf.list_widget.count() == 2
        assert "test1.txt" in shelf._staged_paths[0]
        assert "test2.txt" in shelf._staged_paths[1]

        # Mode toggle
        assert shelf._mode == "copy"
        assert shelf.mode_btn.text() == "COPY"
        shelf._toggle_mode()
        assert shelf._mode == "cut"
        assert shelf.mode_btn.text() == "MOVE"
        assert "Move 2 items to:" in shelf.btn_paste.text()

        # Remove single path
        shelf.remove_path(str(f1))
        assert len(shelf._staged_paths) == 1
        assert str(f1) not in shelf._staged_paths
        assert shelf.list_widget.count() == 1

        # Clear staged
        shelf.clear_staged()
        assert len(shelf._staged_paths) == 0
        assert shelf.list_widget.count() == 0
        assert shelf.btn_paste.isEnabled() is False
        assert not shelf.empty_card.isHidden()


def test_staging_shelf_paste_requested_signal(qapp):
    """test_staging_shelf_paste_requested_signal."""
    from cortex_unified.explorer.widget import StagingShelfWidget

    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = Path(tmpdir) / "alpha.txt"
        f1.write_text("alpha", encoding="utf-8")

        shelf = StagingShelfWidget()
        shelf.set_current_folder(tmpdir)
        shelf.add_paths([str(f1)], mode="copy")

        captured = []
        shelf.paste_requested.connect(lambda mode, paths, dest: captured.append((mode, paths, dest)))

        # Trigger paste
        shelf._on_paste_clicked()
        assert len(captured) == 1
        mode, paths, dest = captured[0]
        assert mode == "copy"
        assert paths == [shelf._norm(str(f1))]
        assert dest == tmpdir


def test_preview_pane_with_staging_shelf(qapp):
    """test_preview_pane_with_staging_shelf."""
    from cortex_unified.explorer.widget import PreviewPane

    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = Path(tmpdir) / "doc.txt"
        f1.write_text("preview text", encoding="utf-8")

        preview = PreviewPane()
        assert hasattr(preview, "staging_shelf")

        preview.set_current_folder(tmpdir)
        assert preview.staging_shelf._current_dir == tmpdir

        preview.show_entry({"name": "doc.txt", "path": str(f1), "isDir": False, "size": 12})
        assert preview.name_lbl.text() == "doc.txt"

        preview.sync_clipboard("copy", [str(f1)])
        assert preview.staging_shelf._norm(str(f1)) in preview.staging_shelf._staged_paths


def test_file_table_model_drag_mime_data(qapp):
    """test_file_table_model_drag_mime_data."""
    from cortex_unified.explorer.core import FileTableModel, IconThumbs

    model = FileTableModel(IconThumbs())
    rows = [
        {"name": "a.txt", "path": "/path/to/a.txt", "isDir": False, "size": 100},
        {"name": "b.txt", "path": "/path/to/b.txt", "isDir": False, "size": 200},
    ]
    model.set_rows(rows)

    idx0 = model.index(0, 0)
    flags = model.flags(idx0)
    assert bool(flags & Qt.ItemFlag.ItemIsDragEnabled) is True

    mime = model.mimeData([idx0])
    assert mime.hasUrls() is True
    urls = [u.toLocalFile() for u in mime.urls()]
    assert urls == ["/path/to/a.txt"]


def test_staged_item_row_attributes_and_drag(qapp):
    """test_staged_item_row_attributes_and_drag."""
    from cortex_unified.explorer.widget import StagedItemRow, StagingShelfWidget

    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = Path(tmpdir) / "sample.txt"
        f1.write_text("content", encoding="utf-8")

        row = StagedItemRow(str(f1))
        assert row.name_lbl.text() == "sample.txt"
        assert row.name_lbl.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) is True
        assert row.icon_lbl.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) is True

        shelf = StagingShelfWidget()
        shelf.add_paths([str(f1)])
        assert shelf.list_widget.count() == 1


def test_python_transfer_fallback_copy_and_move(qapp):
    """test_python_transfer_fallback_copy_and_move."""
    from cortex_unified.explorer.transfers import TransferQueue
    import time

    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src_file = Path(src_dir) / "test_copy.txt"
        src_file.write_text("hello python copy", encoding="utf-8")

        # Fake engine without FFI and without CLI
        class _DummyEngine:
            """_DummyEngine."""
            ffi = None
            cli = ""

        tq = TransferQueue(_DummyEngine())
        completed = []
        tq.job_completed.connect(lambda jid, ok, msg: completed.append((jid, ok, msg)))

        job_id = tq.enqueue("copy", [str(src_file)], dest=dst_dir)

        # Wait for background thread to complete
        start = time.time()
        while not completed and time.time() - start < 5:
            qapp.processEvents()
            time.sleep(0.05)

        assert len(completed) == 1
        assert completed[0][1] is True
        dst_file = Path(dst_dir) / "test_copy.txt"
        assert dst_file.exists()
        assert dst_file.read_text(encoding="utf-8") == "hello python copy"
        tq.stop()


def test_context_menu_paste_option(qapp):
    """test_context_menu_paste_option."""
    import time
    from cortex_unified.explorer.widget import ExplorerWidget
    from NexusExplorer.native.nexus_explorer import _nexus_clipboard
    from PySide6.QtCore import QPoint

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        f1 = Path(tmpdir) / "file1.txt"
        f1.write_text("file1", encoding="utf-8")

        widget = ExplorerWidget(tmpdir)
        _nexus_clipboard.copy([str(f1)])

        # Verify paste in context menu
        assert _nexus_clipboard.has_data is True
        widget._clip("copy")
        widget._paste()
        start = time.time()
        while widget._transfer_queue.is_busy and time.time() - start < 3:
            qapp.processEvents()
            time.sleep(0.05)
        widget._transfer_queue.stop()
        widget.deleteLater()
        qapp.processEvents()


def test_python_transfer_locked_file_handling(qapp):
    """test_python_transfer_locked_file_handling."""
    from cortex_unified.explorer.transfers import TransferQueue
    import time
    import unittest.mock as mock

    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        f_good = Path(src_dir) / "good.txt"
        f_good.write_text("good content", encoding="utf-8")
        f_locked = Path(src_dir) / "pagefile.sys"
        f_locked.write_text("locked content", encoding="utf-8")

        class _DummyEngine:
            """_DummyEngine."""
            ffi = None
            cli = ""

        tq = TransferQueue(_DummyEngine())
        completed = []
        progress_msgs = []
        tq.job_completed.connect(lambda jid, ok, msg: completed.append((jid, ok, msg)))
        tq.job_progress.connect(lambda jid, p, s: progress_msgs.append(s))

        # Mock open so pagefile.sys raises PermissionError like Windows does
        orig_open = open

        def _mock_open(file, *args, **kwargs):
            """_mock_open."""
            if "pagefile.sys" in str(file):
                raise PermissionError(13, "Permission denied: 'pagefile.sys'")
            return orig_open(file, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=_mock_open):
            tq.enqueue("copy", [str(f_good), str(f_locked)], dest=dst_dir)

            start = time.time()
            while not completed and time.time() - start < 5:
                qapp.processEvents()
                time.sleep(0.05)

        assert len(completed) == 1
        assert completed[0][1] is True  # Partial success, doesn't crash
        assert (Path(dst_dir) / "good.txt").exists()
        assert "Skipped locked: pagefile.sys" in completed[0][2]
        tq.stop()


def test_preview_pane_transfer_dock_integration(qapp):
    """test_preview_pane_transfer_dock_integration."""
    from cortex_unified.explorer.widget import PreviewPane
    from cortex_unified.explorer.transfers import TransferQueue

    preview = PreviewPane()
    preview.show()
    class _DummyEngine:
        """_DummyEngine."""
        ffi = None
        cli = ""

    tq = TransferQueue(_DummyEngine())
    preview.set_transfer_queue(tq)

    # Initial state
    assert preview.transfer_dock.isHidden() is True

    # Simulate job started & progress
    tq.job_added.emit("job_test_1")
    qapp.processEvents()
    assert preview.transfer_dock.isHidden() is False
    assert preview.transfer_dock.badge_lbl.text() == "COPY"

    tq.job_progress.emit("job_test_1", 45, "45% · 12 MB/s · ETA 5s")
    qapp.processEvents()
    assert preview.transfer_dock.bar.value() == 45
    assert "45%" in preview.transfer_dock.stats_lbl.text()

    tq.job_completed.emit("job_test_1", True, "All files transferred")
    qapp.processEvents()
    assert preview.transfer_dock.badge_lbl.text() == "DONE"
    assert preview.transfer_dock.bar.value() == 100

    tq.stop()
    preview.close()


def test_read_only_delete_retry(qapp):
    """test_read_only_delete_retry."""
    import stat
    import time
    from cortex_unified.explorer.transfers import TransferQueue

    with tempfile.TemporaryDirectory() as tmpdir:
        ro_file = Path(tmpdir) / "readonly_video.mp4"
        ro_file.write_text("video binary data", encoding="utf-8")
        # Make read-only on disk
        os.chmod(str(ro_file), stat.S_IREAD)

        class _DummyEngine:
            """_DummyEngine."""
            ffi = None
            cli = ""

        tq = TransferQueue(_DummyEngine())
        completed = []
        tq.job_completed.connect(lambda jid, ok, msg: completed.append((jid, ok, msg)))

        tq.enqueue("delete", [str(ro_file)], permanent=True)

        start = time.time()
        while not completed and time.time() - start < 5:
            qapp.processEvents()
            time.sleep(0.05)

        assert len(completed) == 1
        assert completed[0][1] is True
        assert not ro_file.exists()
        tq.stop()


def test_transfer_queue_is_busy_property(qapp):
    """test_transfer_queue_is_busy_property."""
    from cortex_unified.explorer.transfers import TransferQueue
    class _DummyEngine:
        """_DummyEngine."""
        ffi = None
        cli = ""

    tq = TransferQueue(_DummyEngine())
    assert hasattr(tq, "is_busy")
    assert tq.is_busy is False
    tq.stop()


def test_staging_shelf_drag_and_drop_onto_empty_state(qapp):
    """test_staging_shelf_drag_and_drop_onto_empty_state."""
    from PySide6.QtCore import QMimeData, QUrl, QPointF
    from PySide6.QtGui import QDropEvent
    from cortex_unified.explorer.widget import ExplorerWidget

    with tempfile.TemporaryDirectory() as tmpdir:
        src_dir = Path(tmpdir) / "source"
        dst_dir = Path(tmpdir) / "target_empty"
        src_dir.mkdir()
        dst_dir.mkdir()
        file_to_drag = src_dir / "sample_video.mp4"
        file_to_drag.write_text("dummy payload", encoding="utf-8")

        explorer = ExplorerWidget(str(dst_dir))
        qapp.processEvents()

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(file_to_drag))])
        mime.setText(str(file_to_drag))

        # Simulate drop event on explorer / empty state
        ev = QDropEvent(
            QPointF(50, 50),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        explorer.dropEvent(ev)
        assert ev.isAccepted() is True

        explorer._transfer_queue.stop()
        explorer.deleteLater()


def test_file_checksum_dialog(qapp):
    """test_file_checksum_dialog."""
    import time
    from NexusExplorer.native.nexus_explorer import FileChecksumDialog

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_data.bin"
        test_file.write_bytes(b"hello world integrity test 12345")

        dlg = FileChecksumDialog(str(test_file))
        start = time.time()
        while not dlg._hashes and time.time() - start < 5:
            qapp.processEvents()
            time.sleep(0.05)

        assert "MD5" in dlg._hashes
        assert "SHA-256" in dlg._hashes
        assert len(dlg._hashes["SHA-256"]) == 64

        # Test verification comparison
        dlg.verify_input.setText(dlg._hashes["SHA-256"])
        assert "Checksum Matches (SHA-256)" in dlg.match_lbl.text()

        dlg.verify_input.setText("invalid_hash_123")
        assert "No algorithm matches" in dlg.match_lbl.text()

        dlg.deleteLater()
        qapp.processEvents()

