"""Tests for portable_manager — PortableApps.com / LiberKey catalog, USB toolkit.

We do NOT create real network requests or touch real USB drives. All external
I/O (HTTP downloads, drive detection) is mocked. Filesystem tests use tmp_path.
"""

from __future__ import annotations

import configparser
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cortex_unified.analyzers.portable_manager import (
    PortableApp,
    PortableManager,
    _parse_appinfo,
)

# ---------------------------------------------------------------------------
# PortableApp dataclass
# ---------------------------------------------------------------------------


class TestPortableApp:
    def test_basic_construction(self, tmp_path):
        app = PortableApp(
            id="notepad-plus-plus",
            name="Notepad++",
            version="8.7.1",
            category="Utilities",
            publisher="Don Ho",
            size_mb=4.2,
            path=tmp_path,
        )
        assert app.id == "notepad-plus-plus"
        assert app.version == "8.7.1"
        assert app.update_available is False
        assert app.latest_version is None
        assert app.is_portable_format is True
        assert app.launch_exe is None

    def test_to_dict_slots_incompatibility(self, tmp_path):
        app = PortableApp(
            id="7zip",
            name="7-Zip",
            version="24.09",
            category="Utilities",
            publisher="Igor Pavlov",
            size_mb=1.5,
            path=tmp_path,
            launch_exe=tmp_path / "7-Zip.exe",
        )
        with pytest.raises(AttributeError, match="__dict__"):
            app.to_dict()


# ---------------------------------------------------------------------------
# _parse_appinfo helper
# ---------------------------------------------------------------------------


class TestParseAppinfo:
    def _write_appinfo(self, root: Path, content: str) -> Path:
        ini = root / "appinfo.ini"
        ini.write_text(content, encoding="utf-8")
        return ini

    def test_valid_appinfo(self, tmp_path):
        content = (
            "[Details]\n"
            "Name=MyTool\n"
            "DisplayVersion=2.3.0\n"
            "Category=Security\n"
            "Publisher=TestCo\n"
        )
        self._write_appinfo(tmp_path, content)
        (tmp_path / "MyTool.exe").touch()

        app = _parse_appinfo(tmp_path / "appinfo.ini")
        assert app is not None
        assert app.name == "MyTool"
        assert app.version == "2.3.0"
        assert app.category == "Security"
        assert app.launch_exe == tmp_path / "MyTool.exe"

    def test_missing_ini_returns_none(self, tmp_path):
        assert _parse_appinfo(tmp_path / "nope.ini") is None

    def test_garbage_ini_returns_none(self, tmp_path):
        ini = tmp_path / "appinfo.ini"
        ini.write_text("this is not an ini", encoding="utf-8")
        assert _parse_appinfo(ini) is None

    def test_launch_exe_fallback_to_first_exe(self, tmp_path):
        content = "[Details]\nName=Tool\nDisplayVersion=1.0\n"
        self._write_appinfo(tmp_path, content)
        (tmp_path / "something_else.exe").touch()

        app = _parse_appinfo(tmp_path / "appinfo.ini")
        assert app is not None
        assert app.launch_exe == tmp_path / "something_else.exe"

    def test_no_exe(self, tmp_path):
        content = "[Details]\nName=Tool\nDisplayVersion=1.0\n"
        self._write_appinfo(tmp_path, content)
        app = _parse_appinfo(tmp_path / "appinfo.ini")
        assert app is not None
        assert app.launch_exe is None

    def test_fallback_to_first_section(self, tmp_path):
        content = "[MySection]\nName=Fallback\nDisplayVersion=0.5\n"
        self._write_appinfo(tmp_path, content)
        (tmp_path / "Fallback.exe").touch()

        app = _parse_appinfo(tmp_path / "appinfo.ini")
        assert app is not None
        assert app.name == "Fallback"


# ---------------------------------------------------------------------------
# PortableManager initialization
# ---------------------------------------------------------------------------


class TestPortableManagerInit:
    def test_default_init(self):
        mgr = PortableManager()
        assert callable(mgr.progress)
        assert isinstance(mgr.cancel, threading.Event)
        assert not mgr.cancel.is_set()

    def test_custom_progress(self):
        log = []
        mgr = PortableManager(progress=log.append)
        mgr.progress("hello")
        assert log == ["hello"]

    def test_custom_cancel_event(self):
        evt = threading.Event()
        evt.set()
        mgr = PortableManager(cancel=evt)
        assert mgr.cancel.is_set()


# ---------------------------------------------------------------------------
# Scan for portable apps
# ---------------------------------------------------------------------------


class TestScanPortableRoots:
    def _build_paf_app(self, root: Path, name: str, version: str = "1.0"):
        app_dir = root / name
        app_dir.mkdir()
        ini = (
            f"[Details]\nName={name}\n"
            f"DisplayVersion={version}\nCategory=Utilities\nPublisher=Test\n"
        )
        (app_dir / "appinfo.ini").write_text(ini, encoding="utf-8")
        (app_dir / f"{name}.exe").touch()
        return app_dir

    def test_scan_paf_apps(self, tmp_path):
        self._build_paf_app(tmp_path, "ToolA", "2.0")
        self._build_paf_app(tmp_path, "ToolB", "3.1")

        mgr = PortableManager()
        apps = mgr.scan_portable_roots([tmp_path])
        ids = {a.id for a in apps}
        assert "toola" in ids
        assert "toolb" in ids

    def test_scan_empty_root(self, tmp_path):
        mgr = PortableManager()
        assert mgr.scan_portable_roots([tmp_path]) == []

    def test_scan_nonexistent_root(self, tmp_path):
        mgr = PortableManager()
        assert mgr.scan_portable_roots([tmp_path / "nope"]) == []

    def test_scan_liberkey_heuristic(self, tmp_path):
        app_dir = tmp_path / "MyLiberApp"
        app_dir.mkdir()
        (app_dir / "app.exe").touch()

        mgr = PortableManager()
        apps = mgr.scan_portable_roots([tmp_path])
        assert len(apps) == 1
        assert apps[0].name == "MyLiberApp"
        assert apps[0].category == "Unknown"
        assert apps[0].version == ""

    def test_scan_skips_files(self, tmp_path):
        (tmp_path / "readme.txt").write_text("hello")
        mgr = PortableManager()
        assert mgr.scan_portable_roots([tmp_path]) == []

    def test_scan_cancellation(self, tmp_path):
        self._build_paf_app(tmp_path, "ToolA")
        evt = threading.Event()
        evt.set()
        mgr = PortableManager(cancel=evt)
        apps = mgr.scan_portable_roots([tmp_path])
        assert apps == []


# ---------------------------------------------------------------------------
# Update checking
# ---------------------------------------------------------------------------


class TestCheckUpdates:
    def _make_app_with_ini(
        self, root: Path, name: str, version: str, update_url: str | None = None
    ):
        app_dir = root / name
        app_dir.mkdir()
        lines = [
            "[Details]",
            f"Name={name}",
            f"DisplayVersion={version}",
        ]
        if update_url:
            lines.append(f"UpdateURL={update_url}")
        (app_dir / "appinfo.ini").write_text("\n".join(lines), encoding="utf-8")
        (app_dir / f"{name}.exe").touch()
        ini = app_dir / "appinfo.ini"
        cfg = configparser.ConfigParser()
        cfg.read(ini, encoding="utf-8")
        return PortableApp(
            id=name.lower(),
            name=name,
            version=version,
            category="Cat",
            publisher="Pub",
            size_mb=0.1,
            path=app_dir,
        )

    def test_no_update_url_skipped(self, tmp_path):
        app = self._make_app_with_ini(tmp_path, "Tool", "1.0")
        mgr = PortableManager()
        updated = mgr.check_updates([app])
        assert updated == []
        assert app.update_available is False

    def test_update_available(self, tmp_path):
        remote_ini = "[Details]\nDisplayVersion=2.0\n"
        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen"
        ) as mock_urlopen:
            resp = MagicMock()
            resp.read.return_value = remote_ini.encode("utf-8")
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = resp

            app = self._make_app_with_ini(
                tmp_path, "Tool", "1.0", update_url="https://example.com/appinfo.ini"
            )
            mgr = PortableManager()
            updated = mgr.check_updates([app])

            assert len(updated) == 1
            assert updated[0].update_available is True
            assert updated[0].latest_version == "2.0"

    def test_no_update_when_current(self, tmp_path):
        remote_ini = "[Details]\nDisplayVersion=1.0\n"
        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen"
        ) as mock_urlopen:
            resp = MagicMock()
            resp.read.return_value = remote_ini.encode("utf-8")
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = resp

            app = self._make_app_with_ini(
                tmp_path, "Tool", "1.0", update_url="https://example.com/appinfo.ini"
            )
            mgr = PortableManager()
            updated = mgr.check_updates([app])

            assert updated == []
            assert app.update_available is False

    def test_network_failure_continues(self, tmp_path):
        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen",
            side_effect=Exception("network down"),
        ):
            app = self._make_app_with_ini(
                tmp_path, "Tool", "1.0", update_url="https://example.com/appinfo.ini"
            )
            log = []
            mgr = PortableManager(progress=log.append)
            updated = mgr.check_updates([app])

            assert updated == []
            assert any("failed" in msg.lower() for msg in log)

    def test_non_ini_response_skipped(self, tmp_path):
        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen"
        ) as mock_urlopen:
            resp = MagicMock()
            resp.read.return_value = b"<html>404 Not Found</html>"
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = resp

            app = self._make_app_with_ini(
                tmp_path, "Tool", "1.0", update_url="https://example.com/appinfo.ini"
            )
            mgr = PortableManager()
            updated = mgr.check_updates([app])

            assert updated == []

    def test_empty_version_no_update(self, tmp_path):
        remote_ini = "[Details]\nDisplayVersion=2.0\n"
        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen"
        ) as mock_urlopen:
            resp = MagicMock()
            resp.read.return_value = remote_ini.encode("utf-8")
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = resp

            app_dir = tmp_path / "Tool"
            app_dir.mkdir()
            ini = (
                "[Details]\nName=Tool\nDisplayVersion=\n"
                "UpdateURL=https://example.com/appinfo.ini\n"
            )
            (app_dir / "appinfo.ini").write_text(ini, encoding="utf-8")
            (app_dir / "Tool.exe").touch()

            app = PortableApp(
                id="tool",
                name="Tool",
                version="",
                category="Cat",
                publisher="Pub",
                size_mb=0.1,
                path=app_dir,
            )
            mgr = PortableManager()
            updated = mgr.check_updates([app])

            assert updated == []


# ---------------------------------------------------------------------------
# Update app (PAF installer)
# ---------------------------------------------------------------------------


class TestUpdateApp:
    def test_update_no_installer_returns_false(self, tmp_path):
        app_dir = tmp_path / "Tool"
        app_dir.mkdir()
        app = PortableApp(
            id="tool",
            name="Tool",
            version="1.0",
            category="Cat",
            publisher="Pub",
            size_mb=0.1,
            path=app_dir,
        )
        log = []
        mgr = PortableManager(progress=log.append)
        assert mgr.update_app(app) is False
        assert any("no bundled installer" in m for m in log)

    def test_update_with_installer(self, tmp_path):
        app_dir = tmp_path / "Tool"
        app_dir.mkdir()
        installer = app_dir / "PortableApps.comInstaller.exe"
        installer.touch()
        app = PortableApp(
            id="tool",
            name="Tool",
            version="1.0",
            category="Cat",
            publisher="Pub",
            size_mb=0.1,
            path=app_dir,
        )

        mock_proc = MagicMock(returncode=0)
        with patch(
            "cortex_unified.analyzers.portable_manager.subprocess.run",
            return_value=mock_proc,
        ) as mock_run:
            log = []
            mgr = PortableManager(progress=log.append)
            result = mgr.update_app(app)

            assert result is True
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "/SILENT" in args
            assert str(installer) in args

    def test_update_installer_failure(self, tmp_path):
        app_dir = tmp_path / "Tool"
        app_dir.mkdir()
        installer = app_dir / "App" / "AppInfo" / "installer.exe"
        installer.parent.mkdir(parents=True)
        installer.touch()
        app = PortableApp(
            id="tool",
            name="Tool",
            version="1.0",
            category="Cat",
            publisher="Pub",
            size_mb=0.1,
            path=app_dir,
        )

        mock_proc = MagicMock(returncode=1)
        with patch(
            "cortex_unified.analyzers.portable_manager.subprocess.run",
            return_value=mock_proc,
        ):
            mgr = PortableManager()
            assert mgr.update_app(app) is False

    def test_update_subprocess_exception(self, tmp_path):
        app_dir = tmp_path / "Tool"
        app_dir.mkdir()
        installer = app_dir / "ToolInstaller.exe"
        installer.touch()
        app = PortableApp(
            id="tool",
            name="Tool",
            version="1.0",
            category="Cat",
            publisher="Pub",
            size_mb=0.1,
            path=app_dir,
        )

        with patch(
            "cortex_unified.analyzers.portable_manager.subprocess.run",
            side_effect=OSError("permission denied"),
        ):
            log = []
            mgr = PortableManager(progress=log.append)
            assert mgr.update_app(app) is False
            assert any("failed" in m.lower() for m in log)


# ---------------------------------------------------------------------------
# Sysinternals Live downloads
# ---------------------------------------------------------------------------


class TestSysinternalsDownload:
    def test_download_success(self, tmp_path):
        dest = tmp_path / "Autoruns.exe"
        fake_pe = b"MZ" + b"\x00" * 200

        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen"
        ) as mock_urlopen:
            resp = MagicMock()
            resp.read = MagicMock(side_effect=[fake_pe, b""])
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = resp

            mgr = PortableManager()
            result = mgr._download_sysinternals("Autoruns.exe", dest, 30)

            assert result is True
            assert dest.exists()
            assert dest.read_bytes()[:2] == b"MZ"

    def test_download_not_pe_rejected(self, tmp_path):
        dest = tmp_path / "bad.exe"
        fake_html = b"<html>Error 404</html>"

        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen"
        ) as mock_urlopen:

            class FakeResp:
                def __init__(self, data):
                    self._data = data
                    self._read = False

                def read(self, n=-1):
                    if self._read:
                        return b""
                    self._read = True
                    return self._data

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            mock_urlopen.return_value = FakeResp(fake_html)

            mgr = PortableManager()
            log = []
            mgr.progress = log.append
            result = mgr._download_sysinternals("bad.exe", dest, 30)

            assert result is False

    def test_download_network_error(self, tmp_path):
        dest = tmp_path / "procmon.exe"

        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen",
            side_effect=Exception("connection refused"),
        ):
            log = []
            mgr = PortableManager(progress=log.append)
            result = mgr._download_sysinternals("procmon.exe", dest, 30)

            assert result is False
            assert not dest.exists()
            assert any("failed" in m.lower() for m in log)


# ---------------------------------------------------------------------------
# Export toolkit (Sysinternals integration)
# ---------------------------------------------------------------------------


class TestExportToolkit:
    def _build_paf_app(self, root: Path, name: str):
        app_dir = root / name
        app_dir.mkdir()
        ini = "[Details]\nName=" + name + "\nDisplayVersion=1.0\n"
        (app_dir / "appinfo.ini").write_text(ini, encoding="utf-8")
        (app_dir / f"{name}.exe").touch()

    @patch("cortex_unified.analyzers.portable_manager._find_portable_roots")
    def test_export_copies_paf_apps(self, mock_roots, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        self._build_paf_app(source, "ToolA")
        mock_roots.return_value = [source]

        target = tmp_path / "usb"
        mgr = PortableManager()
        result = mgr.export_toolkit(target, include_sysinternals=False)

        assert result is True
        assert (target / "ToolA" / "appinfo.ini").exists()

    @patch("cortex_unified.analyzers.portable_manager._find_portable_roots")
    def test_export_skips_existing(self, mock_roots, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        self._build_paf_app(source, "ToolA")
        mock_roots.return_value = [source]

        target = tmp_path / "usb"
        (target / "ToolA").mkdir(parents=True)
        (target / "ToolA" / "appinfo.ini").write_text("existing", encoding="utf-8")

        mgr = PortableManager()
        mgr.export_toolkit(target, include_sysinternals=False)

        assert (target / "ToolA" / "appinfo.ini").read_text() == "existing"

    @patch("cortex_unified.analyzers.portable_manager._find_portable_roots")
    @patch.object(PortableManager, "_download_sysinternals")
    def test_export_sysinternals(self, mock_dl, mock_roots, tmp_path):
        mock_roots.return_value = []
        mock_dl.return_value = True

        target = tmp_path / "usb"
        mgr = PortableManager()
        mgr.export_toolkit(target, include_sysinternals=True)

        syn = target / "Sysinternals"
        assert syn.exists()
        assert mock_dl.call_count == 4

    @patch("cortex_unified.analyzers.portable_manager._find_portable_roots")
    @patch.object(PortableManager, "_download_sysinternals")
    def test_export_sysinternals_custom_tools(self, mock_dl, mock_roots, tmp_path):
        mock_roots.return_value = []
        mock_dl.return_value = True

        target = tmp_path / "usb"
        mgr = PortableManager()
        mgr.export_toolkit(
            target,
            include_sysinternals=True,
            sysinternals_tools=["PsExec.exe", "handle.exe"],
        )

        assert mock_dl.call_count == 2
        calls = [c[0][0] for c in mock_dl.call_args_list]
        assert "PsExec.exe" in calls
        assert "handle.exe" in calls

    @patch("cortex_unified.analyzers.portable_manager._find_portable_roots")
    @patch.object(PortableManager, "_download_sysinternals")
    def test_export_skips_existing_sysinternals(self, mock_dl, mock_roots, tmp_path):
        mock_roots.return_value = []

        target = tmp_path / "usb"
        syn = target / "Sysinternals"
        syn.mkdir(parents=True)
        (syn / "Autoruns.exe").write_bytes(b"MZ" + b"\x00" * 10)

        mgr = PortableManager()
        mgr.export_toolkit(
            target, include_sysinternals=True, sysinternals_tools=["Autoruns.exe"]
        )

        mock_dl.assert_not_called()


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    def test_progress_called_on_update_failure(self, tmp_path):
        app_dir = tmp_path / "Tool"
        app_dir.mkdir()
        ini = (
            "[Details]\nName=Tool\nDisplayVersion=1.0\n"
            "UpdateURL=https://example.com/appinfo.ini\n"
        )
        (app_dir / "appinfo.ini").write_text(ini, encoding="utf-8")

        app = PortableApp(
            id="tool",
            name="Tool",
            version="1.0",
            category="Cat",
            publisher="Pub",
            size_mb=0.1,
            path=app_dir,
        )

        with patch(
            "cortex_unified.analyzers.portable_manager.urllib.request.urlopen",
            side_effect=Exception("timeout"),
        ):
            log = []
            mgr = PortableManager(progress=log.append)
            mgr.check_updates([app])
            assert len(log) >= 1
            assert "failed" in log[0].lower()

    def test_progress_called_on_export(self, mock_find_roots=None):
        log = []
        mgr = PortableManager(progress=log.append)
        mgr.progress("test message")
        assert log == ["test message"]


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


class TestCancellation:
    def _build_paf_app(self, root: Path, name: str):
        app_dir = root / name
        app_dir.mkdir()
        ini = "[Details]\nName=" + name + "\nDisplayVersion=1.0\n"
        (app_dir / "appinfo.ini").write_text(ini, encoding="utf-8")
        (app_dir / f"{name}.exe").touch()

    def test_scan_respects_cancel(self, tmp_path):
        self._build_paf_app(tmp_path, "ToolA")
        self._build_paf_app(tmp_path, "ToolB")

        call_count = 0
        original_iterdir = Path.iterdir

        def counting_iterdir(self_inner):
            nonlocal call_count
            for item in original_iterdir(self_inner):
                call_count += 1
                yield item

        evt = threading.Event()
        with patch.object(Path, "iterdir", counting_iterdir):
            mgr = PortableManager(cancel=evt)

            def set_cancel_after_one(*a, **kw):
                evt.set()
                return []

            with patch.object(
                mgr, "scan_portable_roots", wraps=mgr.scan_portable_roots
            ) as mock_scan:
                mock_scan.side_effect = set_cancel_after_one
                apps = mgr.scan_portable_roots([tmp_path])
                assert apps == []


# ---------------------------------------------------------------------------
# PAF silent flag constant
# ---------------------------------------------------------------------------


class TestPAFSilentFlag:
    def test_silent_flag_value(self):
        assert PortableManager._PAF_SILENT_FLAG == "/SILENT"

    def test_sysinternals_live_url(self):
        assert PortableManager._SYSINTERNALS_LIVE == "https://live.sysinternals.com"


# ---------------------------------------------------------------------------
# Registry persistence (export_toolkit integration)
# ---------------------------------------------------------------------------


class TestExportToolkitIntegration:
    @patch("cortex_unified.analyzers.portable_manager._find_portable_roots")
    def test_export_creates_directory(self, mock_roots, tmp_path):
        mock_roots.return_value = []
        target = tmp_path / "new_usb"
        mgr = PortableManager()
        result = mgr.export_toolkit(target, include_sysinternals=False)
        assert result is True
        assert target.exists()

    @patch("cortex_unified.analyzers.portable_manager._find_portable_roots")
    def test_export_returns_true(self, mock_roots, tmp_path):
        mock_roots.return_value = []
        mgr = PortableManager()
        assert mgr.export_toolkit(tmp_path / "x", include_sysinternals=False) is True

    @patch(
        "cortex_unified.analyzers.portable_manager._find_portable_roots",
        side_effect=Exception("disk full"),
    )
    def test_export_failure_returns_false(self, mock_roots, tmp_path):
        log = []
        mgr = PortableManager(progress=log.append)
        result = mgr.export_toolkit(tmp_path / "x", include_sysinternals=False)
        assert result is False
        assert any("failed" in m.lower() for m in log)
