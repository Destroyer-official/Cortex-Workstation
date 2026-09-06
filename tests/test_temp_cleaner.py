"""Tests for :mod:`cortex_unified.core.temp_cleaner` and the ``clean-temp`` CLI.

Temp roots are never hit for real: ``TempCleaner.LOCATIONS`` is monkeypatched
onto scratch directories under ``tmp_path``, and old files are backdated via
``os.utime`` so they clear the ``min_age_days`` floor.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from cortex_unified.cli.cli import main
from cortex_unified.core.temp_cleaner import TempCleaner, TempFinding

OLD_TS = time.time() - 45 * 86400


def _backdate(path: Path, ts: float = OLD_TS) -> None:
    """Backdate using os.utime.

    Args:
        path (Path): Filesystem path to the target file or directory.
        ts (float): The ts parameter.
    """
    os.utime(path, (ts, ts))


def _make_old(path: Path, size: int = 32, ts: float = OLD_TS) -> Path:
    """Make old using _backdate.

    Args:
        path (Path): Filesystem path to the target file or directory.
        size (int): Integer number of bytes to format or process.
        ts (float): The ts parameter.

    Returns:
        Path: Result of the operation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    _backdate(path, ts)
    return path


@pytest.fixture
def temp_roots(tmp_path, monkeypatch):
    """Two fake temp roots; TempCleaner.LOCATIONS is pointed at them.

    Args:
        tmp_path: Filesystem path to the target file or directory.
        monkeypatch: The monkeypatch parameter.
    """
    user = tmp_path / "user_temp"
    system = tmp_path / "system_temp"
    user.mkdir()
    system.mkdir()
    locations = [("user_temp", user), ("system_temp", system)]
    monkeypatch.setattr(
        TempCleaner, "LOCATIONS", classmethod(lambda cls: list(locations))
    )
    return {"tmp": tmp_path, "user": user, "system": system}


def _cleaner(**kwargs) -> TempCleaner:
    """_cleaner.

    Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

    Returns:
        TempCleaner: Result of the operation.
    """
    kwargs.setdefault("exclude_patterns", [])
    return TempCleaner(**kwargs)


class TestScan:
    """Group testscan tests covering finds old files with sizes and locations; skips fresh files; min age zero includes fresh files; exclude patterns honored; unreadable and missing roots are ignored; symlinked directory is never traversed."""
    def test_finds_old_files_with_sizes_and_locations(self, temp_roots):
        """Verify finds old files with sizes and locations via cleaner.scan, _make_old, _cleaner.

        Args:
            temp_roots: The temp roots parameter.
        """
        a = _make_old(temp_roots["user"] / "stale_a.dat", size=100)
        b = _make_old(temp_roots["system"] / "nested" / "stale_b.bin", size=50)

        cleaner = _cleaner(min_age_days=1)
        findings = cleaner.scan()

        by_path = {f.path: f for f in findings}
        assert str(a) in by_path
        assert str(b) in by_path
        assert by_path[str(a)].size_bytes == 100
        assert by_path[str(a)].location == "user_temp"
        assert by_path[str(b)].location == "system_temp"
        # Nested files are found (subdirectories are traversed).
        assert len(findings) == 2

    def test_skips_fresh_files(self, temp_roots):
        """Verify skips fresh files via cleaner.scan, _make_old, _cleaner.

        Args:
            temp_roots: The temp roots parameter.
        """
        old = _make_old(temp_roots["user"] / "old.dat")
        fresh = temp_roots["user"] / "fresh.dat"
        fresh.write_bytes(b"new")

        cleaner = _cleaner(min_age_days=1)
        findings = cleaner.scan()

        assert [f.path for f in findings] == [str(old)]
        assert fresh.exists()

    def test_min_age_zero_includes_fresh_files(self, temp_roots):
        """Verify min age zero includes fresh files via scan, _cleaner.

        Args:
            temp_roots: The temp roots parameter.
        """
        fresh = temp_roots["user"] / "fresh.dat"
        fresh.write_bytes(b"n" * 7)

        findings = _cleaner(min_age_days=0).scan()

        assert [f.path for f in findings] == [str(fresh)]
        assert findings[0].size_bytes == 7

    def test_exclude_patterns_honored(self, temp_roots):
        """Verify exclude patterns honored via cleaner.scan, _make_old, _cleaner.

        Args:
            temp_roots: The temp roots parameter.
        """
        keep = _make_old(temp_roots["user"] / "keepme.dat")
        drop = _make_old(temp_roots["system"] / "drop-me.skip")

        cleaner = _cleaner(min_age_days=1, exclude_patterns=["*.skip"])
        findings = cleaner.scan()
        paths = {f.path for f in findings}

        assert paths == {str(keep)}
        assert str(drop) not in paths
        assert drop.exists()

    def test_unreadable_and_missing_roots_are_ignored(self, tmp_path, monkeypatch):
        """Verify unreadable and missing roots are ignored via monkeypatch.setattr, Path, scan.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        missing = tmp_path / "does_not_exist"
        usable = tmp_path / "usable"
        usable.mkdir()
        _make_old(usable / "old.dat")
        monkeypatch.setattr(
            TempCleaner,
            "LOCATIONS",
            classmethod(
                lambda cls: [("missing", missing), ("usable", usable)]
            ),
        )

        findings = _cleaner(min_age_days=1).scan()

        assert [Path(f.path).name for f in findings] == ["old.dat"]

    def test_symlinked_directory_is_never_traversed(self, temp_roots):
        """Verify symlinked directory is never traversed via link.symlink_to, pytest.skip, Path.

        Args:
            temp_roots: The temp roots parameter.
        """
        target = temp_roots["tmp"] / "real_target"
        target.mkdir()
        secret = _make_old(target / "payload.dat", size=64)

        link = temp_roots["user"] / "linked"
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlink creation not supported on this platform")

        findings = _cleaner(min_age_days=1).scan()
        found_paths = {f.path for f in findings}

        assert secret.exists()
        assert all(not Path(p).is_relative_to(link) for p in found_paths)
        assert str(secret) not in found_paths

    @pytest.mark.skipif(
        not sys.platform.startswith("win"), reason="junctions are Windows-only"
    )
    def test_junctioned_directory_is_never_traversed(self, temp_roots):
        """Verify junctioned directory is never traversed via pytest.mark.skipif, subprocess.run, pytest.skip.

        Args:
            temp_roots: The temp roots parameter.
        """
        import subprocess

        target = temp_roots["tmp"] / "junction_target"
        target.mkdir()
        secret = _make_old(target / "payload_j.dat", size=48)

        link = temp_roots["user"] / "jlinked"
        # Junctions need no elevation, unlike directory symlinks.
        proc = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
        )
        if proc.returncode != 0:
            pytest.skip("junction creation not supported on this platform")

        findings = _cleaner(min_age_days=1).scan()
        found_paths = {f.path for f in findings}

        assert secret.exists()
        assert all(not Path(p).is_relative_to(link) for p in found_paths)
        assert str(secret) not in found_paths


class TestTotals:
    """Group testtotals tests covering total reclaimable before scan is zero; total reclaimable sums scan results."""
    def test_total_reclaimable_before_scan_is_zero(self):
        """Verify total reclaimable before scan is zero via total_reclaimable, _cleaner."""
        assert _cleaner().total_reclaimable() == 0

    def test_total_reclaimable_sums_scan_results(self, temp_roots):
        """Verify total reclaimable sums scan results via cleaner.scan, cleaner.total_reclaimable, _make_old.

        Args:
            temp_roots: The temp roots parameter.
        """
        _make_old(temp_roots["user"] / "a.dat", size=10)
        _make_old(temp_roots["system"] / "b.dat", size=25)

        cleaner = _cleaner(min_age_days=1)
        cleaner.scan()

        assert cleaner.total_reclaimable() == 35


class TestClean:
    """Group testclean tests covering dry run touches nothing; use trash removes files from scan results; without trash files are unlinked; refuses paths outside discovered roots; never deletes files modified within min age."""
    def test_dry_run_touches_nothing(self, temp_roots):
        """Verify dry run touches nothing via cleaner.scan, cleaner.clean, _make_old.

        Args:
            temp_roots: The temp roots parameter.
        """
        a = _make_old(temp_roots["user"] / "a.dat", size=100)
        b = _make_old(temp_roots["system"] / "b.dat", size=40)

        cleaner = _cleaner(min_age_days=1)
        findings = cleaner.scan()
        result = cleaner.clean(findings, use_trash=True, dry_run=True)

        assert result["deleted"] == len(findings) == 2
        assert result["failed"] == 0
        assert result["errors"] == []
        assert result["bytes_freed"] == 140
        assert a.exists() and b.exists()

    def test_use_trash_removes_files_from_scan_results(self, temp_roots, monkeypatch):
        """Verify use trash removes files from scan results via cleaner.scan, monkeypatch.setattr, cleaner.clean.

        Args:
            temp_roots: The temp roots parameter.
            monkeypatch: The monkeypatch parameter.
        """
        a = _make_old(temp_roots["user"] / "a.dat", size=100)
        b = _make_old(temp_roots["system"] / "b.dat", size=40)
        trashed = []

        def fake_send2trash(path):
            """Fake send2trash using trashed.append, os.unlink.

            Args:
                path: Filesystem path to the target file or directory.
            """
            trashed.append(str(path))
            os.unlink(path)

        monkeypatch.setattr(
            "cortex_unified.core.deleter.send2trash", fake_send2trash
        )

        cleaner = _cleaner(min_age_days=1)
        findings = cleaner.scan()
        result = cleaner.clean(findings, use_trash=True, dry_run=False)

        assert result["deleted"] == 2
        assert result["failed"] == 0
        assert sorted(trashed) == sorted([str(a), str(b)])
        assert not a.exists() and not b.exists()
        # A re-scan finds nothing afterwards.
        assert cleaner.scan() == []

    def test_without_trash_files_are_unlinked(self, temp_roots):
        """Verify without trash files are unlinked via cleaner.scan, cleaner.clean, _make_old.

        Args:
            temp_roots: The temp roots parameter.
        """
        a = _make_old(temp_roots["user"] / "gone.dat")

        cleaner = _cleaner(min_age_days=1)
        findings = cleaner.scan()
        result = cleaner.clean(findings, use_trash=False, dry_run=False)

        assert result["deleted"] == 1
        assert not a.exists()

    def test_refuses_paths_outside_discovered_roots(self, temp_roots):
        """Verify refuses paths outside discovered roots via cleaner.scan, TempFinding, cleaner.clean.

        Args:
            temp_roots: The temp roots parameter.
        """
        outside = _make_old(temp_roots["tmp"] / "outside.dat")

        cleaner = _cleaner(min_age_days=1)
        cleaner.scan()  # establishes the known roots
        finding = TempFinding(
            path=str(outside),
            size_bytes=outside.stat().st_size,
            location="nowhere",
        )
        result = cleaner.clean([finding], use_trash=False, dry_run=False)

        assert result["deleted"] == 0
        assert result["failed"] == 1
        assert "outside discovered temp roots" in result["errors"][0]["error"]
        assert outside.exists()

    def test_never_deletes_files_modified_within_min_age(self, temp_roots):
        """Verify never deletes files modified within min age via cleaner.scan, TempFinding, cleaner.clean.

        Args:
            temp_roots: The temp roots parameter.
        """
        fresh = temp_roots["user"] / "touched_lately.dat"
        fresh.write_bytes(b"hot")

        cleaner = _cleaner(min_age_days=1)
        cleaner.scan()
        finding = TempFinding(
            path=str(fresh),
            size_bytes=fresh.stat().st_size,
            location="user_temp",
        )
        result = cleaner.clean([finding], use_trash=False, dry_run=False)

        assert result["deleted"] == 0
        assert result["failed"] == 0
        assert fresh.exists()


class TestCleanTempCLI:
    """Group testcleantempcli tests covering help lists command; dry run lists findings and deletes nothing; delete flag cleans after confirmation skip; trash flag routes through send2trash."""
    def test_help_lists_command(self):
        """Verify help lists command via result.output.lower, CliRunner, invoke."""
        result = CliRunner().invoke(main, ["clean-temp", "--help"])
        assert result.exit_code == 0
        assert "clean-temp" in result.output.lower()

    def test_dry_run_lists_findings_and_deletes_nothing(self, temp_roots):
        """Verify dry run lists findings and deletes nothing via CliRunner, runner.invoke, _make_old.

        Args:
            temp_roots: The temp roots parameter.
        """
        old = _make_old(temp_roots["user"] / "cli_old.dat", size=128)
        fresh = temp_roots["user"] / "cli_new.dat"
        fresh.write_bytes(b"n" * 4)

        runner = CliRunner()
        result = runner.invoke(main, ["clean-temp"])

        assert result.exit_code == 0
        output = result.output + str(result.stderr or "")
        assert "cli_old.dat" in output
        assert "Would delete" in output
        assert old.exists() and fresh.exists()

    def test_delete_flag_cleans_after_confirmation_skip(self, temp_roots):
        """Verify delete flag cleans after confirmation skip via CliRunner, runner.invoke, _make_old.

        Args:
            temp_roots: The temp roots parameter.
        """
        old = _make_old(temp_roots["system"] / "cli_del.dat", size=200)

        runner = CliRunner()
        result = runner.invoke(main, ["clean-temp", "--delete", "--yes"])

        assert result.exit_code == 0
        output = result.output + str(result.stderr or "")
        assert not old.exists()
        assert "Deleted 1" in output

    def test_trash_flag_routes_through_send2trash(self, temp_roots, monkeypatch):
        """Verify trash flag routes through send2trash via monkeypatch.setattr, CliRunner, runner.invoke.

        Args:
            temp_roots: The temp roots parameter.
            monkeypatch: The monkeypatch parameter.
        """
        old = _make_old(temp_roots["user"] / "cli_trash.dat", size=64)
        trashed = []

        def fake_send2trash(path):
            """Fake send2trash using trashed.append, os.unlink.

            Args:
                path: Filesystem path to the target file or directory.
            """
            trashed.append(str(path))
            os.unlink(path)

        monkeypatch.setattr(
            "cortex_unified.core.deleter.send2trash", fake_send2trash
        )

        runner = CliRunner()
        result = runner.invoke(main, ["clean-temp", "--trash", "--yes"])

        assert result.exit_code == 0
        assert trashed == [str(old)]
        assert not old.exists()
