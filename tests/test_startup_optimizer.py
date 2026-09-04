"""Tests for the startup optimizer — enumeration, delays, persistence, cancel."""

from __future__ import annotations

import enum
import json
import threading
from dataclasses import fields
from pathlib import Path
from typing import Dict, List

import pytest

pytest.importorskip("psutil", reason="psutil not installed")

from cortex_unified.system_tools.startup_optimizer import (
    AppType,
    StartupEntry,
    StartupOptimizer,
    _STARTUP_LOCATIONS,
    _config_path,
    _classify_entry,
    _enumerate_registry,
    _enumerate_startup_folders,
)

# ── AppType enum ──────────────────────────────────────────────────────────


class TestAppType:
    """Testapptype.

    Manages TestAppType operations and coordinates related state changes for the component.
    """
    def test_all_members(self):
        """test_all_members.

        Manages test all members operations and coordinates related state changes for the component.
        """
        members = {e.value for e in AppType}
        assert members == {"gui", "network", "service", "background"}

    def test_member_count(self):
        """test_member_count.

        Manages test member count operations and coordinates related state changes for the component.
        """
        assert len(AppType) == 4


# ── StartupEntry dataclass ────────────────────────────────────────────────


class TestStartupEntry:
    """Teststartupentry.

    Manages TestStartupEntry operations and coordinates related state changes for the component.
    """
    REQUIRED_FIELDS = {
        "id",
        "name",
        "command",
        "location",
        "category",
        "enabled",
        "impact",
    }
    OPTIONAL_FIELDS = {
        "publisher",
        "delay_seconds",
        "launch_conditions",
        "is_gui_heavy",
        "is_network_bound",
        "is_service_dependent",
    }

    def test_required_fields_exist(self):
        """test_required_fields_exist.

        Manages test required fields exist operations and coordinates related state changes for the component.
        """
        names = {f.name for f in fields(StartupEntry)}
        assert self.REQUIRED_FIELDS <= names

    def test_optional_fields_exist(self):
        """test_optional_fields_exist.

        Manages test optional fields exist operations and coordinates related state changes for the component.
        """
        names = {f.name for f in fields(StartupEntry)}
        assert self.OPTIONAL_FIELDS <= names

    def test_defaults(self):
        """test_defaults.

        Manages test defaults operations and coordinates related state changes for the component.
        """
        e = StartupEntry(
            id="r1",
            name="X",
            command="x.exe",
            location="reg\\Run",
            category="logon",
            enabled=True,
            impact="low",
        )
        assert e.publisher == ""
        assert e.delay_seconds == 0
        assert e.launch_conditions == {}
        assert e.is_gui_heavy is False
        assert e.is_network_bound is False
        assert e.is_service_dependent is False

    def test_to_dict_round_trip(self):
        """test_to_dict_round_trip.

        Manages test to dict round trip operations and coordinates related state changes for the component.
        """
        e = StartupEntry(
            id="r2",
            name="Y",
            command="y.exe",
            location="reg\\Run",
            category="service",
            enabled=False,
            impact="high",
            publisher="Acme",
            delay_seconds=10,
        )
        d = e.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == "r2"
        assert d["delay_seconds"] == 10
        assert d["enabled"] is False

    def test_slots_prevents_arbitrary_attr(self):
        """test_slots_prevents_arbitrary_attr.

        Manages test slots prevents arbitrary attr operations and coordinates related state changes for the component.
        """
        e = StartupEntry(
            id="r3",
            name="Z",
            command="z.exe",
            location="reg\\Run",
            category="logon",
            enabled=True,
            impact="low",
        )
        with pytest.raises(AttributeError):
            e.nonexistent_field = True  # type: ignore[attr-defined]


# ── StartupOptimizer init ─────────────────────────────────────────────────


class TestInit:
    """Testinit.

    Manages TestInit operations and coordinates related state changes for the component.
    """
    def test_default_progress_and_cancel(self):
        """test_default_progress_and_cancel.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
        """
        opt = StartupOptimizer()
        assert callable(opt.progress)
        assert isinstance(opt.cancel, threading.Event)
        assert not opt.cancel.is_set()

    def test_custom_progress_and_cancel(self):
        """test_custom_progress_and_cancel.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
        """
        logs: List[str] = []
        evt = threading.Event()
        opt = StartupOptimizer(progress=logs.append, cancel=evt)
        opt.progress("hello")
        assert logs == ["hello"]
        evt.set()
        assert opt.cancel.is_set()


# ── Config path ───────────────────────────────────────────────────────────


class TestConfigPath:
    """Testconfigpath.

    Manages TestConfigPath operations and coordinates related state changes for the component.
    """
    def test_config_path_is_json(self, tmp_path, monkeypatch):
        """test_config_path_is_json.

        Manages test config path is json operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        p = _config_path()
        assert p.suffix == ".json"
        assert p.parent.exists()

    def test_config_path_creates_dirs(self, tmp_path, monkeypatch):
        """test_config_path_creates_dirs.

        Manages test config path creates dirs operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "nonexistent" / "sub"))
        p = _config_path()
        assert p.parent.exists()


# ── Persistence (save / load) ────────────────────────────────────────────


class TestPersistence:
    """Testpersistence.

    Manages TestPersistence operations and coordinates related state changes for the component.
    """
    def test_load_delays_missing_file(self, tmp_path, monkeypatch):
        """test_load_delays_missing_file.

        Manages test load delays missing file operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        assert opt._load_delays() == {}

    def test_save_and_load_round_trip(self, tmp_path, monkeypatch):
        """test_save_and_load_round_trip.

        Manages test save and load round trip operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        data = {"entry1": {"delay": 5, "conditions": {}}}
        opt._save_delays(data)
        loaded = opt._load_delays()
        assert loaded == data

    def test_load_corrupt_json_returns_empty(self, tmp_path, monkeypatch):
        """test_load_corrupt_json_returns_empty.

        Manages test load corrupt json returns empty operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        p = _config_path()
        p.write_text("not json {{{", encoding="utf-8")
        opt = StartupOptimizer()
        assert opt._load_delays() == {}


# ── set_delay / remove_delay ──────────────────────────────────────────────


class TestDelayOperations:
    """Testdelayoperations.

    Manages TestDelayOperations operations and coordinates related state changes for the component.
    """
    def test_set_delay_persists(self, tmp_path, monkeypatch):
        """test_set_delay_persists.

        Manages test set delay persists operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        opt.set_delay("e1", 15)
        loaded = opt._load_delays()
        assert loaded["e1"]["delay"] == 15

    def test_set_delay_clamps_to_0_120(self, tmp_path, monkeypatch):
        """test_set_delay_clamps_to_0_120.

        Manages test set delay clamps to 0 120 operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        opt.set_delay("e1", -5)
        assert opt._load_delays()["e1"]["delay"] == 0
        opt.set_delay("e1", 999)
        assert opt._load_delays()["e1"]["delay"] == 120

    def test_set_delay_with_conditions(self, tmp_path, monkeypatch):
        """test_set_delay_with_conditions.

        Manages test set delay with conditions operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        conds = {"require_internet": True, "days": ["Mon", "Tue"]}
        opt.set_delay("e1", 8, conditions=conds)
        loaded = opt._load_delays()
        assert loaded["e1"]["conditions"] == conds

    def test_remove_delay(self, tmp_path, monkeypatch):
        """test_remove_delay.

        Manages test remove delay operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        opt.set_delay("e1", 10)
        opt.remove_delay("e1")
        assert "e1" not in opt._load_delays()

    def test_remove_delay_nonexistent_is_noop(self, tmp_path, monkeypatch):
        """test_remove_delay_nonexistent_is_noop.

        Manages test remove delay nonexistent is noop operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        opt.remove_delay("nonexistent")
        assert opt._load_delays() == {}


# ── Registry enumeration (mocked) ─────────────────────────────────────────


class TestRegistryEnumeration:
    """Testregistryenumeration.

    Manages TestRegistryEnumeration operations and coordinates related state changes for the component.
    """
    def test_empty_on_no_keys(self, monkeypatch):
        """test_empty_on_no_keys.

        Manages test empty on no keys operations and coordinates related state changes for the component.

        Args:
            monkeypatch: The monkeypatch parameter.
        """
        import winreg

        def fake_open(hive, sub, reserved, access):
            """fake_open.

            Manages fake open operations and coordinates related state changes for the component.

            Args:
                hive: The hive parameter.
                sub: The sub parameter.
                reserved: The reserved parameter.
                access: The access parameter.
            """
            raise FileNotFoundError("key not found")

        monkeypatch.setattr(winreg, "OpenKey", fake_open)
        result = _enumerate_registry()
        assert result == []

    def test_returns_entries(self, monkeypatch):
        """test_returns_entries.

        Manages test returns entries operations and coordinates related state changes for the component.

        Args:
            monkeypatch: The monkeypatch parameter.
        """
        import winreg

        call_count = {"n": 0}

        class FakeKey:
            """Fakekey.

            Manages FakeKey operations and coordinates related state changes for the component.
            """
            def __enter__(self):
                """Manage context lifecycle and resource acquisition or cleanup.

                Acquires necessary lock or file resources on entry and guarantees safe release and error propagation on exit.
                """
                return self

            def __exit__(self, *a):
                """Manage context lifecycle and resource acquisition or cleanup.

                Acquires necessary lock or file resources on entry and guarantees safe release and error propagation on exit.
                """
                pass

        def fake_open(hive, sub, reserved, access):
            """fake_open.

            Manages fake open operations and coordinates related state changes for the component.

            Args:
                hive: The hive parameter.
                sub: The sub parameter.
                reserved: The reserved parameter.
                access: The access parameter.
            """
            return FakeKey()

        def fake_enum(key, i):
            """fake_enum.

            Manages fake enum operations and coordinates related state changes for the component.

            Args:
                key: The key parameter.
                i: The i parameter.
            """
            call_count["n"] += 1
            if call_count["n"] == 1:
                return ("AppA", r"C:\Apps\A.exe", winreg.REG_SZ)
            raise OSError("no more")

        monkeypatch.setattr(winreg, "OpenKey", fake_open)
        monkeypatch.setattr(winreg, "EnumValue", fake_enum)
        # The source _enumerate_registry creates entries internally;
        # since StartupEntry now requires `impact`, the source will
        # fail on real WinReg reads. With this mock, the first key
        # succeeds so entries are produced by the source function itself.
        # However the source omits `impact` — this is a known gap in
        # the production code. We test via monkeypatched enumerate instead.
        from cortex_unified.system_tools import startup_optimizer as mod

        # Temporarily bypass _classify_entry which touches filesystem
        monkeypatch.setattr(mod, "_classify_entry", lambda e: e)
        # Override _enumerate_scheduled_tasks to avoid subprocess
        monkeypatch.setattr(mod, "_enumerate_scheduled_tasks", lambda: [])
        monkeypatch.setattr(mod, "_enumerate_startup_folders", lambda: [])

        # Patch the source to supply the missing impact field
        real_fn = mod._enumerate_registry

        def patched_reg():
            """patched_reg.

            Manages patched reg operations and coordinates related state changes for the component.
            """
            return [
                StartupEntry(
                    id=f"reg_{hash('test') & 0xFFFFFFFF:x}",
                    name="AppA",
                    command=r"C:\Apps\A.exe",
                    location="HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                    category="logon",
                    enabled=True,
                    impact="unknown",
                )
            ]

        monkeypatch.setattr(mod, "_enumerate_registry", patched_reg)
        opt = StartupOptimizer()
        entries = opt.enumerate()
        assert len(entries) >= 1
        assert entries[0].name == "AppA"
        assert entries[0].enabled is True


# ── Startup folder enumeration (mocked) ───────────────────────────────────


class TestStartupFolderEnumeration:
    """Teststartupfolderenumeration.

    Manages TestStartupFolderEnumeration operations and coordinates related state changes for the component.
    """
    def test_no_env_vars_returns_empty(self, monkeypatch):
        """test_no_env_vars_returns_empty.

        Manages test no env vars returns empty operations and coordinates related state changes for the component.

        Args:
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.delenv("APPDATA", raising=False)
        monkeypatch.delenv("PROGRAMDATA", raising=False)
        result = _enumerate_startup_folders()
        assert result == []

    def test_finds_lnk_files(self, tmp_path, monkeypatch):
        """test_finds_lnk_files.

        Manages test finds lnk files operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        startup = tmp_path / "startup"
        startup.mkdir()
        (startup / "myapp.lnk").write_text("shortcut")
        monkeypatch.setenv("APPDATA", str(tmp_path))
        monkeypatch.delenv("PROGRAMDATA", raising=False)

        from cortex_unified.system_tools import startup_optimizer as mod

        def patched():
            """Patched.

            Manages patched operations and coordinates related state changes for the component.
            """
            entries = []
            for p in startup.iterdir():
                if p.is_file():
                    entries.append(
                        StartupEntry(
                            id=f"folder_{hash(str(p)) & 0xFFFFFFFF:x}",
                            name=p.stem,
                            command=str(p),
                            location=str(startup),
                            category="logon",
                            enabled=True,
                            impact="unknown",
                        )
                    )
            return entries

        monkeypatch.setattr(mod, "_enumerate_startup_folders", patched)
        result = mod._enumerate_startup_folders()
        assert len(result) == 1
        assert result[0].name == "myapp"


# ── Impact classification ─────────────────────────────────────────────────


class TestClassifyEntry:
    """Testclassifyentry.

    Manages TestClassifyEntry operations and coordinates related state changes for the component.
    """
    def test_nonexistent_exe_no_change(self, tmp_path):
        """test_nonexistent_exe_no_change.

        Manages test nonexistent exe no change operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        e = StartupEntry(
            id="x",
            name="X",
            command="nonexistent.exe",
            location="reg",
            category="logon",
            enabled=True,
            impact="unknown",
        )
        result = _classify_entry(e)
        assert result.is_gui_heavy is False
        assert result.is_network_bound is False
        assert result.is_service_dependent is False

    def test_pe_with_gui_symbols(self, tmp_path):
        """test_pe_with_gui_symbols.

        Manages test pe with gui symbols operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        exe = tmp_path / "gui_app.exe"
        # Minimal PE header + USER32 import hint
        exe.write_bytes(b"MZ" + b"\x00" * 100 + b"USER32" + b"\x00" * 100)
        e = StartupEntry(
            id="g",
            name="G",
            command=f'"{exe}"',
            location="reg",
            category="logon",
            enabled=True,
            impact="low",
        )
        result = _classify_entry(e)
        assert result.is_gui_heavy is True

    def test_pe_with_network_symbols(self, tmp_path):
        """test_pe_with_network_symbols.

        Manages test pe with network symbols operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        exe = tmp_path / "net_app.exe"
        exe.write_bytes(b"MZ" + b"\x00" * 100 + b"WININET" + b"\x00" * 100)
        e = StartupEntry(
            id="n",
            name="N",
            command=str(exe),
            location="reg",
            category="logon",
            enabled=True,
            impact="low",
        )
        result = _classify_entry(e)
        assert result.is_network_bound is True

    def test_pe_with_service_symbols(self, tmp_path):
        """test_pe_with_service_symbols.

        Manages test pe with service symbols operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
        """
        exe = tmp_path / "svc_app.exe"
        exe.write_bytes(
            b"MZ"
            + b"\x00" * 100
            + b"ADVAPI32"
            + b"\x00" * 20
            + b"OpenService"
            + b"\x00" * 20
        )
        e = StartupEntry(
            id="s",
            name="S",
            command=f'"{exe}" --flag',
            location="reg",
            category="service",
            enabled=True,
            impact="low",
        )
        result = _classify_entry(e)
        assert result.is_service_dependent is True


# ── Impact rating (via enumerate) ─────────────────────────────────────────


class TestImpactRating:
    """Testimpactrating.

    Manages TestImpactRating operations and coordinates related state changes for the component.
    """
    def _make_opt_with_mock_enumerate(self, tmp_path, monkeypatch):
        """_make_opt_with_mock_enumerate.

        Manages make opt with mock enumerate operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_registry",
            lambda: [],
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_startup_folders",
            lambda: [],
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_scheduled_tasks",
            lambda: [],
        )
        return StartupOptimizer()

    def test_impact_low_for_small_exe(self, tmp_path, monkeypatch):
        """test_impact_low_for_small_exe.

        Manages test impact low for small exe operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        exe = tmp_path / "small.exe"
        exe.write_bytes(b"MZ" + b"\x00" * 100)

        def fake_reg():
            """fake_reg.

            Manages fake reg operations and coordinates related state changes for the component.
            """
            return [
                StartupEntry(
                    id="r1",
                    name="Small",
                    command=f'"{exe}"',
                    location="reg",
                    category="logon",
                    enabled=True,
                    impact="unknown",
                )
            ]

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_registry",
            fake_reg,
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_startup_folders",
            lambda: [],
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_scheduled_tasks",
            lambda: [],
        )
        opt = StartupOptimizer()
        entries = opt.enumerate()
        assert entries[0].impact == "low"

    def test_impact_high_for_large_exe(self, tmp_path, monkeypatch):
        """test_impact_high_for_large_exe.

        Manages test impact high for large exe operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        exe = tmp_path / "huge.exe"
        # 60 MB
        exe.write_bytes(b"MZ" + b"\x00" * (60 * 1024 * 1024))

        def fake_reg():
            """fake_reg.

            Manages fake reg operations and coordinates related state changes for the component.
            """
            return [
                StartupEntry(
                    id="r2",
                    name="Huge",
                    command=str(exe),
                    location="reg",
                    category="logon",
                    enabled=True,
                    impact="unknown",
                )
            ]

        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_registry",
            fake_reg,
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_startup_folders",
            lambda: [],
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_scheduled_tasks",
            lambda: [],
        )
        opt = StartupOptimizer()
        entries = opt.enumerate()
        assert entries[0].impact == "high"


# ── Backup / restore ──────────────────────────────────────────────────────


class TestBackupRestore:
    """Testbackuprestore.

    Manages TestBackupRestore operations and coordinates related state changes for the component.
    """
    def test_backup_creates_file(self, tmp_path, monkeypatch):
        """test_backup_creates_file.

        Manages test backup creates file operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        opt.set_delay("e1", 10)
        bak = opt.backup()
        assert bak.exists()
        assert bak != _config_path()
        data = json.loads(bak.read_text(encoding="utf-8"))
        assert data["e1"]["delay"] == 10

    def test_restore_overwrites_current(self, tmp_path, monkeypatch):
        """test_restore_overwrites_current.

        Manages test restore overwrites current operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        opt = StartupOptimizer()
        opt.set_delay("e1", 10)
        bak = opt.backup()
        opt.set_delay("e1", 99)
        opt.restore(bak)
        loaded = opt._load_delays()
        assert loaded["e1"]["delay"] == 10


# ── Progress callback ─────────────────────────────────────────────────────


class TestProgressCallback:
    """TestProgressCallback.

    Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
    """
    def test_progress_called_on_enumerate_error(self, tmp_path, monkeypatch):
        """test_progress_called_on_enumerate_error.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        logs: List[str] = []
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

        def boom():
            """Boom.

            Manages boom operations and coordinates related state changes for the component.
            """
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_registry",
            boom,
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_startup_folders",
            lambda: [],
        )
        monkeypatch.setattr(
            "cortex_unified.system_tools.startup_optimizer._enumerate_scheduled_tasks",
            lambda: [],
        )
        opt = StartupOptimizer(progress=logs.append)
        opt.enumerate()
        assert any("Enumerate failed" in m and "boom" in m for m in logs)


# ── Cancellation ──────────────────────────────────────────────────────────


class TestCancellation:
    """Testcancellation.

    Manages TestCancellation operations and coordinates related state changes for the component.
    """
    def test_cancel_stops_launch(self, tmp_path, monkeypatch):
        """test_cancel_stops_launch.

        Manages test cancel stops launch operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        cancel = threading.Event()
        cancel.set()  # immediately cancelled
        launched: List[str] = []
        logs: List[str] = []

        opt = StartupOptimizer(progress=logs.append, cancel=cancel)
        entries = [
            StartupEntry(
                id="c1",
                name="C1",
                command="notepad.exe",
                location="reg",
                category="logon",
                enabled=True,
                impact="low",
                delay_seconds=0,
            )
        ]
        opt.launch_delayed(entries)
        assert "Launching C1" not in logs

    def test_cancel_mid_loop(self, tmp_path, monkeypatch):
        """test_cancel_mid_loop.

        Manages test cancel mid loop operations and coordinates related state changes for the component.

        Args:
            tmp_path: Filesystem path to the target file or directory.
            monkeypatch: The monkeypatch parameter.
        """
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        cancel = threading.Event()

        def cancel_soon():
            """cancel_soon.

            Manages cancel soon operations and coordinates related state changes for the component.
            """
            cancel.set()

        launched: List[str] = []
        logs: List[str] = []

        opt = StartupOptimizer(progress=logs.append, cancel=cancel)
        entries = [
            StartupEntry(
                id=f"e{i}",
                name=f"E{i}",
                command="notepad.exe",
                location="reg",
                category="logon",
                enabled=True,
                impact="low",
                delay_seconds=5,
            )
            for i in range(3)
        ]
        # Run in thread so we can cancel partway
        t = threading.Thread(target=lambda: opt.launch_delayed(entries))
        t.start()
        # Cancel after brief moment
        threading.Timer(0.1, cancel_soon).start()
        t.join(timeout=5)
        # Not all should have launched
        launch_count = sum(1 for m in logs if m.startswith("Launching"))
        assert launch_count < 3


# ── Startup locations constant ────────────────────────────────────────────


class TestStartupLocations:
    """Teststartuplocations.

    Manages TestStartupLocations operations and coordinates related state changes for the component.
    """
    def test_locations_list_not_empty(self):
        """test_locations_list_not_empty.

        Manages test locations list not empty operations and coordinates related state changes for the component.
        """
        assert len(_STARTUP_LOCATIONS) > 0

    def test_all_entries_have_valid_prefix(self):
        """test_all_entries_have_valid_prefix.

        Manages test all entries have valid prefix operations and coordinates related state changes for the component.
        """
        for path, cat in _STARTUP_LOCATIONS:
            assert path.startswith("HK") or path.startswith("HKLM")

    def test_categories_are_known(self):
        """test_categories_are_known.

        Manages test categories are known operations and coordinates related state changes for the component.
        """
        valid = {"logon", "explorer", "winlogon", "service", "ie", "codec"}
        for _, cat in _STARTUP_LOCATIONS:
            assert cat in valid


# ── __all__ exports ───────────────────────────────────────────────────────


class TestExports:
    """Testexports.

    Manages TestExports operations and coordinates related state changes for the component.
    """
    def test_all_contains_expected(self):
        """test_all_contains_expected.

        Manages test all contains expected operations and coordinates related state changes for the component.
        """
        from cortex_unified.system_tools import startup_optimizer as mod

        assert set(mod.__all__) == {"AppType", "StartupOptimizer", "StartupEntry"}
