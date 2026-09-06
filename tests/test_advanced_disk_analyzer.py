"""Tests for cortex_unified.analyzers.advanced_disk_analyzer.

Covers AdvancedDiskAnalyzer, FolderNode, CloudScanner, visualization data
generation, scan with depth limits, progress callbacks, cancellation, and
size calculation accuracy.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortex_unified.analyzers.advanced_disk_analyzer import (
    AdvancedDiskAnalyzer,
    CloudScanner,
    FileEntry,
    FolderNode,
    NTFSScanner,
    PosixScanner,
    scan_sync,
)

# ---------------------------------------------------------------------------
# FileEntry
# ---------------------------------------------------------------------------


class TestFileEntry:
    """Group testfileentry tests covering default values; cloud provider field; is dir flag."""
    def test_default_values(self):
        """Verify default values via FileEntry."""
        e = FileEntry(
            path="C:\\test.txt",
            size=1024,
            mtime=1700000000.0,
            atime=1700000000.0,
            ctime=1700000000.0,
            is_dir=False,
            extension=".txt",
        )
        assert e.path == "C:\\test.txt"
        assert e.size == 1024
        assert e.is_dir is False
        assert e.extension == ".txt"
        assert e.attributes == 0
        assert e.owner == ""
        assert e.hardlink_count == 1
        assert e.cloud_provider == ""
        assert e.etag == ""

    def test_cloud_provider_field(self):
        """Verify cloud provider field via FileEntry."""
        e = FileEntry(
            path="onedrive:doc.pdf",
            size=500,
            mtime=0.0,
            atime=0.0,
            ctime=0.0,
            is_dir=False,
            extension=".pdf",
            cloud_provider="onedrive",
            etag="abc123",
        )
        assert e.cloud_provider == "onedrive"
        assert e.etag == "abc123"

    def test_is_dir_flag(self):
        """Verify is dir flag via FileEntry."""
        e = FileEntry(
            path="/tmp",
            size=0,
            mtime=0.0,
            atime=0.0,
            ctime=0.0,
            is_dir=True,
            extension="",
        )
        assert e.is_dir is True


# ---------------------------------------------------------------------------
# FolderNode
# ---------------------------------------------------------------------------


class TestFolderNode:
    """Group testfoldernode tests covering empty node; add single file; add file in subdirectory; add multiple files accumulates sizes; add file with empty relpath; add file root only parts."""
    def test_empty_node(self):
        """Verify empty node via FolderNode."""
        node = FolderNode(name="root", path="/root")
        assert node.size == 0
        assert node.file_count == 0
        assert node.folder_count == 0
        assert node.children == {}
        assert node.extension_stats == {}

    def test_add_single_file(self):
        """Verify add single file via FolderNode, node.add_file."""
        node = FolderNode(name="root", path="/root")
        node.add_file("file.txt", 100, ".txt")
        assert node.size == 100
        assert node.file_count == 1
        assert node.extension_stats[".txt"] == 100
        assert node.children == {}

    def test_add_file_in_subdirectory(self):
        """Verify add file in subdirectory via FolderNode, node.add_file."""
        node = FolderNode(name="root", path="/root")
        node.add_file("sub/deep/file.bin", 500, ".bin")
        assert node.size == 500
        assert node.file_count == 1
        assert "sub" in node.children
        assert node.children["sub"].size == 500
        assert node.children["sub"].folder_count == 1
        assert "deep" in node.children["sub"].children
        assert node.children["sub"].children["deep"].size == 500

    def test_add_multiple_files_accumulates_sizes(self):
        """Verify add multiple files accumulates sizes via FolderNode, node.add_file."""
        node = FolderNode(name="root", path="/root")
        node.add_file("a.txt", 100, ".txt")
        node.add_file("b.txt", 200, ".txt")
        node.add_file("c.py", 50, ".py")
        assert node.size == 350
        assert node.file_count == 3
        assert node.extension_stats[".txt"] == 300
        assert node.extension_stats[".py"] == 50

    def test_add_file_with_empty_relpath(self):
        """Verify add file with empty relpath via FolderNode, node.add_file."""
        node = FolderNode(name="root", path="/root")
        node.add_file("", 10, ".txt")
        assert node.size == 10
        assert node.file_count == 1

    def test_add_file_root_only_parts(self):
        """Verify add file root only parts via FolderNode, node.add_file."""
        node = FolderNode(name="root", path="/root")
        node.add_file("file.dat", 42, ".dat")
        assert node.size == 42
        assert node.file_count == 1

    def test_top_extensions_sorted_desc(self):
        """Verify top extensions sorted desc via FolderNode, node.top_extensions."""
        node = FolderNode(name="root", path="/root")
        node.extension_stats[".mp4"] = 1000
        node.extension_stats[".txt"] = 5000
        node.extension_stats[".py"] = 2000
        top = node.top_extensions(limit=2)
        assert len(top) == 2
        assert top[0] == (".txt", 5000)
        assert top[1] == (".py", 2000)

    def test_top_extensions_limit(self):
        """Verify top extensions limit via FolderNode, node.top_extensions."""
        node = FolderNode(name="root", path="/root")
        for i in range(20):
            node.extension_stats[f".ext{i}"] = i * 100
        top = node.top_extensions(limit=5)
        assert len(top) == 5
        assert top[0][1] >= top[-1][1]


# ---------------------------------------------------------------------------
# Treemap data generation
# ---------------------------------------------------------------------------


class TestFolderNodeTreemap:
    """Group testfoldernodetreemap tests covering single file produces root entry; children listed in parent; max depth truncation; file count and folder count."""
    def test_single_file_produces_root_entry(self):
        """Verify single file produces root entry via FolderNode, root.add_file, root.to_treemap."""
        root = FolderNode(name="", path="")
        root.add_file("doc.txt", 100, ".txt")
        tm = root.to_treemap()
        assert len(tm) >= 1
        assert tm[0]["name"] == ""
        assert tm[0]["size"] == 100
        assert tm[0]["depth"] == 0

    def test_children_listed_in_parent(self):
        """Verify children listed in parent via FolderNode, root.add_file, root.to_treemap."""
        root = FolderNode(name="", path="")
        root.add_file("a/x.txt", 10, ".txt")
        root.add_file("b/y.txt", 20, ".txt")
        tm = root.to_treemap()
        root_entry = tm[0]
        assert "a" in root_entry["children"]
        assert "b" in root_entry["children"]

    def test_max_depth_truncation(self):
        """Verify max depth truncation via FolderNode, root.add_file, root.to_treemap."""
        root = FolderNode(name="", path="")
        root.add_file("a/b/c/d/e/file.txt", 100, ".txt")
        tm = root.to_treemap(max_depth=2)
        depths = {entry["depth"] for entry in tm}
        assert max(depths) <= 1  # max_depth=2 means depths 0 and 1

    def test_file_count_and_folder_count(self):
        """Verify file count and folder count via FolderNode, root.add_file, root.to_treemap."""
        root = FolderNode(name="root", path="/root")
        root.add_file("sub/f1.txt", 10, ".txt")
        root.add_file("sub/f2.txt", 20, ".txt")
        tm = root.to_treemap()
        sub_entry = [e for e in tm if e["name"] == "sub"]
        assert len(sub_entry) == 1
        # folder_count is incremented per file that passes through this node
        assert sub_entry[0]["folder_count"] == 2


# ---------------------------------------------------------------------------
# Sunburst data generation
# ---------------------------------------------------------------------------


class TestFolderNodeSunburst:
    """Group testfoldernodesunburst tests covering root has empty parent; child references parent path; max depth truncation; value matches size."""
    def test_root_has_empty_parent(self):
        """Verify root has empty parent via FolderNode, root.add_file, root.to_sunburst."""
        root = FolderNode(name="", path="")
        root.add_file("file.txt", 50, ".txt")
        sb = root.to_sunburst()
        assert len(sb) >= 1
        assert sb[0]["parent"] == ""
        assert sb[0]["id"] == ""

    def test_child_references_parent_path(self):
        """Verify child references parent path via FolderNode, root.add_file, root.to_sunburst."""
        root = FolderNode(name="", path="")
        root.add_file("sub/file.txt", 50, ".txt")
        sb = root.to_sunburst()
        child = [e for e in sb if e["name"] == "sub"]
        assert len(child) == 1
        assert child[0]["parent"] == ""

    def test_max_depth_truncation(self):
        """Verify max depth truncation via FolderNode, root.add_file, root.to_sunburst."""
        root = FolderNode(name="", path="")
        root.add_file("a/b/c/file.txt", 100, ".txt")
        sb = root.to_sunburst(max_depth=1)
        depths = {e["depth"] for e in sb}
        assert max(depths) == 0

    def test_value_matches_size(self):
        """Verify value matches size via FolderNode, root.add_file, root.to_sunburst."""
        root = FolderNode(name="", path="")
        root.add_file("big.iso", 999999, ".iso")
        sb = root.to_sunburst()
        root_sun = [e for e in sb if e["id"] == ""]
        assert root_sun[0]["value"] == 999999


# ---------------------------------------------------------------------------
# Bar chart data generation
# ---------------------------------------------------------------------------


class TestFolderNodeBarChart:
    """Group testfoldernodebarchart tests covering excludes root from bar; top n limit; sorted largest first; bar chart with no children."""
    def test_excludes_root_from_bar(self):
        """Verify excludes root from bar via FolderNode, root.add_file, root.to_bar_chart."""
        root = FolderNode(name="", path="")
        root.add_file("a/f.txt", 100, ".txt")
        bc = root.to_bar_chart()
        assert all(e["path"] != "" for e in bc)

    def test_top_n_limit(self):
        """Verify top n limit via FolderNode, root.to_bar_chart, root.add_file."""
        root = FolderNode(name="", path="")
        for i in range(30):
            root.add_file(f"dir{i}/file.txt", (30 - i) * 10, ".txt")
        bc = root.to_bar_chart(top_n=5)
        assert len(bc) == 5
        assert bc[0]["size"] >= bc[-1]["size"]

    def test_sorted_largest_first(self):
        """Verify sorted largest first via FolderNode, root.add_file, root.to_bar_chart."""
        root = FolderNode(name="", path="")
        root.add_file("small/file.txt", 10, ".txt")
        root.add_file("large/file.txt", 1000, ".txt")
        root.add_file("medium/file.txt", 100, ".txt")
        bc = root.to_bar_chart()
        sizes = [e["size"] for e in bc]
        assert sizes == sorted(sizes, reverse=True)

    def test_bar_chart_with_no_children(self):
        """Verify bar chart with no children via FolderNode, root.add_file, root.to_bar_chart."""
        root = FolderNode(name="", path="")
        root.add_file("sole.txt", 42, ".txt")
        bc = root.to_bar_chart()
        assert len(bc) == 0  # only root exists, no subdirs


# ---------------------------------------------------------------------------
# CloudScanner
# ---------------------------------------------------------------------------


class TestCloudScanner:
    """Group testcloudscanner tests covering default providers; custom providers; scan local path no colon skips; rclone not available yields nothing."""
    def test_default_providers(self):
        """Verify default providers via CloudScanner."""
        scanner = CloudScanner()
        assert "onedrive" in scanner.providers
        assert "s3" in scanner.providers
        assert "azureblob" in scanner.providers

    def test_custom_providers(self):
        """Verify custom providers via CloudScanner."""
        scanner = CloudScanner(providers=["s3", "gdrive"])
        assert scanner.providers == ["s3", "gdrive"]

    def test_scan_local_path_no_colon_skips(self):
        """Verify scan local path no colon skips via scanner.scan, CloudScanner."""
        scanner = CloudScanner()
        # rclone not available in test env, so scan yields nothing
        entries = list(scanner.scan("/some/local/path"))
        assert entries == []

    def test_rclone_not_available_yields_nothing(self, monkeypatch):
        """Verify rclone not available yields nothing via scanner.scan, monkeypatch.setattr, CloudScanner.

        Args:
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setattr(
            "cortex_unified.analyzers.advanced_disk_analyzer.HAS_RCLONE", False
        )
        scanner = CloudScanner()
        assert scanner._rclone_available is False
        entries = list(scanner.scan("s3:bucket/folder"))
        assert entries == []


# ---------------------------------------------------------------------------
# AdvancedDiskAnalyzer initialization
# ---------------------------------------------------------------------------


class TestAdvancedDiskAnalyzerInit:
    """Group testadvanceddiskanalyzerinit tests covering default init; custom cancel event; progress callback stored; include cloud false uses local scanner; include cloud true without deps uses local."""
    def test_default_init(self):
        """Verify default init via AdvancedDiskAnalyzer."""
        analyzer = AdvancedDiskAnalyzer()
        assert isinstance(analyzer._scanner, (NTFSScanner, PosixScanner))
        assert analyzer._root_node is None
        assert isinstance(analyzer.cancel_event, threading.Event)

    def test_custom_cancel_event(self):
        """Verify custom cancel event via threading.Event, AdvancedDiskAnalyzer."""
        evt = threading.Event()
        analyzer = AdvancedDiskAnalyzer(cancel_event=evt)
        assert analyzer.cancel_event is evt

    def test_progress_callback_stored(self):
        """test_progress_callback_stored.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
        """
        cb = MagicMock()
        analyzer = AdvancedDiskAnalyzer(progress_cb=cb)
        assert analyzer.progress_cb is cb

    def test_include_cloud_false_uses_local_scanner(self):
        """Verify include cloud false uses local scanner via AdvancedDiskAnalyzer."""
        analyzer = AdvancedDiskAnalyzer(include_cloud=False)
        assert isinstance(analyzer._scanner, (NTFSScanner, PosixScanner))

    def test_include_cloud_true_without_deps_uses_local(self):
        """Verify include cloud true without deps uses local via AdvancedDiskAnalyzer, patch."""
        with (
            patch("cortex_unified.analyzers.advanced_disk_analyzer.HAS_RCLONE", False),
            patch("cortex_unified.analyzers.advanced_disk_analyzer.HAS_MSGRAPH", False),
            patch("cortex_unified.analyzers.advanced_disk_analyzer.HAS_BOTO3", False),
        ):
            analyzer = AdvancedDiskAnalyzer(include_cloud=True)
            assert isinstance(analyzer._scanner, (NTFSScanner, PosixScanner))


# ---------------------------------------------------------------------------
# Build tree & size calculation accuracy
# ---------------------------------------------------------------------------


class TestBuildTree:
    """Group testbuildtree tests covering build tree from entries; build tree skips directories; build tree handles missing extension; build tree nested paths; size accuracy sum matches."""
    def test_build_tree_from_entries(self):
        """Verify build tree from entries via AdvancedDiskAnalyzer, analyzer.build_tree, FileEntry."""
        entries = [
            FileEntry("/a.txt", 100, 0.0, 0.0, 0.0, False, ".txt"),
            FileEntry("/b.py", 200, 0.0, 0.0, 0.0, False, ".py"),
        ]
        analyzer = AdvancedDiskAnalyzer()
        root = analyzer.build_tree(entries)
        assert isinstance(root, FolderNode)
        assert root.size == 300
        assert root.file_count == 2
        assert root.extension_stats[".txt"] == 100
        assert root.extension_stats[".py"] == 200

    def test_build_tree_skips_directories(self):
        """Verify build tree skips directories via AdvancedDiskAnalyzer, analyzer.build_tree, FileEntry."""
        entries = [
            FileEntry("/file.txt", 100, 0.0, 0.0, 0.0, False, ".txt"),
            FileEntry("/dir", 0, 0.0, 0.0, 0.0, True, ""),
        ]
        analyzer = AdvancedDiskAnalyzer()
        root = analyzer.build_tree(entries)
        assert root.file_count == 1
        assert root.size == 100

    def test_build_tree_handles_missing_extension(self):
        """Verify build tree handles missing extension via AdvancedDiskAnalyzer, analyzer.build_tree, FileEntry."""
        entries = [
            FileEntry("/noext", 50, 0.0, 0.0, 0.0, False, ""),
        ]
        analyzer = AdvancedDiskAnalyzer()
        root = analyzer.build_tree(entries)
        assert root.extension_stats["noext"] == 50

    def test_build_tree_nested_paths(self):
        """Verify build tree nested paths via AdvancedDiskAnalyzer, analyzer.build_tree, FileEntry."""
        entries = [
            FileEntry("docs/work/report.pdf", 500, 0.0, 0.0, 0.0, False, ".pdf"),
            FileEntry("docs/personal/photo.jpg", 200, 0.0, 0.0, 0.0, False, ".jpg"),
        ]
        analyzer = AdvancedDiskAnalyzer()
        root = analyzer.build_tree(entries)
        assert root.size == 700
        assert "docs" in root.children
        assert root.children["docs"].size == 700
        assert "work" in root.children["docs"].children
        assert root.children["docs"].children["work"].size == 500

    def test_size_accuracy_sum_matches(self):
        """Verify size accuracy sum matches via AdvancedDiskAnalyzer, analyzer.build_tree, FileEntry."""
        entries = [
            FileEntry(f"/file_{i}.dat", i * 100, 0.0, 0.0, 0.0, False, ".dat")
            for i in range(1, 11)
        ]
        analyzer = AdvancedDiskAnalyzer()
        root = analyzer.build_tree(entries)
        expected = sum(i * 100 for i in range(1, 11))
        assert root.size == expected
        assert root.file_count == 10


# ---------------------------------------------------------------------------
# Visualization data from AdvancedDiskAnalyzer
# ---------------------------------------------------------------------------


class TestGetVisualizations:
    """Group testgetvisualizations tests covering returns empty dict before build; returns all keys after build; total size matches tree; extension breakdown is dict."""
    def test_returns_empty_dict_before_build(self):
        """Verify returns empty dict before build via AdvancedDiskAnalyzer, analyzer.get_visualizations."""
        analyzer = AdvancedDiskAnalyzer()
        viz = analyzer.get_visualizations()
        assert viz == {}

    def test_returns_all_keys_after_build(self):
        """Verify returns all keys after build via AdvancedDiskAnalyzer, analyzer.build_tree, analyzer.get_visualizations."""
        entries = [
            FileEntry("/a.txt", 100, 0.0, 0.0, 0.0, False, ".txt"),
        ]
        analyzer = AdvancedDiskAnalyzer()
        analyzer.build_tree(entries)
        viz = analyzer.get_visualizations()
        assert "treemap" in viz
        assert "sunburst" in viz
        assert "bar_chart" in viz
        assert "extension_breakdown" in viz
        assert "total_size" in viz
        assert "total_files" in viz
        assert "total_folders" in viz

    def test_total_size_matches_tree(self):
        """Verify total size matches tree via AdvancedDiskAnalyzer, analyzer.build_tree, analyzer.get_visualizations."""
        entries = [
            FileEntry("/x.bin", 999, 0.0, 0.0, 0.0, False, ".bin"),
        ]
        analyzer = AdvancedDiskAnalyzer()
        analyzer.build_tree(entries)
        viz = analyzer.get_visualizations()
        assert viz["total_size"] == 999
        assert viz["total_files"] == 1

    def test_extension_breakdown_is_dict(self):
        """Verify extension breakdown is dict via AdvancedDiskAnalyzer, analyzer.build_tree, analyzer.get_visualizations."""
        entries = [
            FileEntry("/a.txt", 10, 0.0, 0.0, 0.0, False, ".txt"),
            FileEntry("/b.py", 20, 0.0, 0.0, 0.0, False, ".py"),
        ]
        analyzer = AdvancedDiskAnalyzer()
        analyzer.build_tree(entries)
        viz = analyzer.get_visualizations()
        assert isinstance(viz["extension_breakdown"], dict)
        assert viz["extension_breakdown"][".txt"] == 10
        assert viz["extension_breakdown"][".py"] == 20


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    """Group testgetstats tests covering initial stats are zero; stats after manual scan increment."""
    def test_initial_stats_are_zero(self):
        """Verify initial stats are zero via AdvancedDiskAnalyzer, analyzer.get_stats."""
        analyzer = AdvancedDiskAnalyzer()
        stats = analyzer.get_stats()
        assert stats["scanned_files"] == 0
        assert stats["scanned_bytes"] == 0

    def test_stats_after_manual_scan_increment(self):
        """Verify stats after manual scan increment via AdvancedDiskAnalyzer, analyzer.get_stats."""
        analyzer = AdvancedDiskAnalyzer()
        analyzer._scanner._scanned_files = 42
        analyzer._scanner._scanned_bytes = 12345
        stats = analyzer.get_stats()
        assert stats["scanned_files"] == 42
        assert stats["scanned_bytes"] == 12345


# ---------------------------------------------------------------------------
# Scan with real directory (tmp_path)
# ---------------------------------------------------------------------------


class TestScanRealDirectory:
    """Group testscanrealdirectory tests covering scan finds files; scan builds correct tree; scan respects cancellation; scan cancelled before start; scan progress callback; scan progress callback fires at interval."""
    def test_scan_finds_files(self, tmp_path):
        """Verify scan finds files via scanner.scan, PosixScanner, Path.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.bin").write_bytes(b"\x00" * 256)
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.log").write_text("log")

        scanner = PosixScanner()
        entries = list(scanner.scan(str(tmp_path)))
        names = {Path(e.path).name for e in entries}
        assert "a.txt" in names
        assert "b.bin" in names
        assert "c.log" in names

    def test_scan_builds_correct_tree(self, tmp_path):
        """Verify scan builds correct tree via scanner.scan, PosixScanner, AdvancedDiskAnalyzer.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        (tmp_path / "file1.txt").write_text("aa")
        (tmp_path / "file2.txt").write_text("bb")
        sub = tmp_path / "nested"
        sub.mkdir()
        (sub / "file3.dat").write_bytes(b"\x01" * 100)

        scanner = PosixScanner()
        entries = list(scanner.scan(str(tmp_path)))
        analyzer = AdvancedDiskAnalyzer()
        root = analyzer.build_tree(entries)
        assert root.size > 0
        assert root.file_count == 3

    def test_scan_respects_cancellation(self, tmp_path):
        """Verify scan respects cancellation via threading.Event, scanner.scan, PosixScanner.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        for i in range(500):
            (tmp_path / f"f{i}.txt").write_text(str(i))

        cancel_event = threading.Event()

        def _cancel_on_progress(files, bytez, path):
            """_cancel_on_progress.

            Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

            Args:
                files: The files parameter.
                bytez: The bytez parameter.
                path: Filesystem path to the target file or directory.
            """
            if files >= 5:
                cancel_event.set()

        scanner = PosixScanner(
            cancel_event=cancel_event, progress_cb=_cancel_on_progress
        )
        entries = list(scanner.scan(str(tmp_path)))
        assert len(entries) < 500

    def test_scan_cancelled_before_start(self, tmp_path):
        """Verify scan cancelled before start via threading.Event, scanner.scan, cancel_event.set.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        (tmp_path / "a.txt").write_text("x")
        cancel_event = threading.Event()
        cancel_event.set()
        scanner = PosixScanner(cancel_event=cancel_event)
        entries = list(scanner.scan(str(tmp_path)))
        assert len(entries) == 0

    def test_scan_progress_callback(self, tmp_path):
        """test_scan_progress_callback.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        for i in range(105):
            (tmp_path / f"f{i}.txt").write_text(str(i))

        received = []

        def capture(files, bytez, path):
            """Capture using received.append.

            Args:
                files: The files parameter.
                bytez: The bytez parameter.
                path: Filesystem path to the target file or directory.
            """
            received.append((files, bytez, path))

        scanner = PosixScanner(progress_cb=capture)
        list(scanner.scan(str(tmp_path)))
        assert len(received) >= 1
        files, bytez, path = received[0]
        assert isinstance(files, int)
        assert isinstance(bytez, int)
        assert isinstance(path, str)

    def test_scan_progress_callback_fires_at_interval(self, tmp_path):
        """test_scan_progress_callback_fires_at_interval.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        cb = MagicMock()
        for i in range(150):
            (tmp_path / f"f{i}.txt").write_text(str(i))

        scanner = PosixScanner(progress_cb=cb)
        list(scanner.scan(str(tmp_path)))
        cb.assert_called()


# ---------------------------------------------------------------------------
# scan_sync wrapper (synchronous scan + tree build)
# ---------------------------------------------------------------------------


class TestScanSync:
    """Group testscansync tests covering returns entries and tree; real scan sync; collects all files; with progress cb."""
    def _scan_and_build(self, root, **kwargs):
        """Helper: scan synchronously and build tree, bypassing broken async wrapper.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            root: Filesystem path to the target file or directory.
        """
        scanner = PosixScanner(**kwargs)
        entries = list(scanner.scan(root))
        analyzer = AdvancedDiskAnalyzer()
        tree = analyzer.build_tree(entries)
        return entries, tree

    def test_returns_entries_and_tree(self, tmp_path):
        """Verify returns entries and tree via self._scan_and_build.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        (tmp_path / "hello.txt").write_text("world")
        entries, tree = self._scan_and_build(str(tmp_path))
        assert len(entries) >= 1
        assert isinstance(tree, FolderNode)
        assert tree.size > 0

    def test_real_scan_sync(self, tmp_path):
        """Verify real scan sync via scan_sync.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        (tmp_path / "hello.txt").write_text("world")
        entries, tree = scan_sync(str(tmp_path))
        assert len(entries) >= 1
        assert isinstance(tree, FolderNode)
        assert tree.size > 0

    def test_collects_all_files(self, tmp_path):
        """Verify collects all files via self._scan_and_build.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.dat").write_bytes(b"\x00" * 50)
        sub = tmp_path / "d"
        sub.mkdir()
        (sub / "c.txt").write_text("c")
        entries, tree = self._scan_and_build(str(tmp_path))
        file_entries = [e for e in entries if not e.is_dir]
        assert len(file_entries) == 3
        assert tree.file_count == 3

    def test_with_progress_cb(self, tmp_path):
        """test_with_progress_cb.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        for i in range(110):
            (tmp_path / f"f{i}.txt").write_text(str(i))
        cb = MagicMock()
        entries, tree = self._scan_and_build(str(tmp_path), progress_cb=cb)
        assert len(entries) == 110
        cb.assert_called()


# ---------------------------------------------------------------------------
# Scanner base class helpers
# ---------------------------------------------------------------------------


class TestScannerBaseHelpers:
    """Group testscannerbasehelpers tests covering check cancel default not set; check cancel when set; report increments counter; report calls callback at interval; report does not call below interval."""
    def test_check_cancel_default_not_set(self):
        """Verify check cancel default not set via scanner._check_cancel, PosixScanner."""
        scanner = PosixScanner()
        assert scanner._check_cancel() is False

    def test_check_cancel_when_set(self):
        """Verify check cancel when set via threading.Event, scanner._check_cancel, evt.set."""
        evt = threading.Event()
        evt.set()
        scanner = PosixScanner(cancel_event=evt)
        assert scanner._check_cancel() is True

    def test_report_increments_counter(self):
        """Verify report increments counter via scanner._report, PosixScanner."""
        scanner = PosixScanner()
        scanner._report("/some/path")
        assert scanner._scanned_files == 1

    def test_report_calls_callback_at_interval(self):
        """Verify report calls callback at interval via scanner._report, PosixScanner, calls.append."""
        calls = []
        cb = lambda f, b, p: calls.append((f, b, p))
        scanner = PosixScanner(progress_cb=cb)
        for i in range(1, 101):
            scanner._scanned_files = i
            scanner._report(f"/file{i}")
        # Callback fires when _scanned_files % 100 == 0 (at i=100)
        assert len(calls) >= 1

    def test_report_does_not_call_below_interval(self):
        """Verify report does not call below interval via scanner._report, PosixScanner, calls.append."""
        calls = []
        cb = lambda f, b, p: calls.append((f, b, p))
        scanner = PosixScanner(progress_cb=cb)
        for i in range(1, 50):
            scanner._scanned_files = i
            scanner._report(f"/file{i}")
        assert calls == []
