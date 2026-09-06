"""Virtual-disk (VHDX) discovery and compaction safety.

WSL2 / Docker / Hyper-V disks grow but never shrink, so compaction is the only
way to give the space back. The rules that must hold:

* never compact a disk whose runtime still holds it open (that is how these
  files get corrupted) - and say which process to close;
* report the *measured* before/after delta, never an estimate;
* when nothing could be reclaimed, say so instead of implying success;
* never invent a "potential saving" figure without a guest measurement.

Discovery is monkeypatched because CI machines have no WSL or Docker installed;
the real registry/PowerShell probes are exercised only for "doesn't crash".
"""

from __future__ import annotations

import platform

import pytest

from cortex_unified.system_tools.vhdx_manager import (
    CompactResult,
    DiskKind,
    VhdxManager,
    VirtualDisk,
)

IS_WINDOWS = platform.system() == "Windows"


@pytest.fixture
def fake_vhdx(tmp_path):
    """A stand-in .vhdx file of a known size.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    p = tmp_path / "ext4.vhdx"
    p.write_bytes(b"\0" * 8192)
    return p


# ---------------------------------------------------------------------------
# VirtualDisk reporting
# ---------------------------------------------------------------------------

def test_saving_is_unknown_without_a_guest_measurement(fake_vhdx):
    """Verify saving is unknown without a guest measurement via VirtualDisk.

    Args:
        fake_vhdx: The fake vhdx parameter.
    """
    disk = VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu", 8192, 8192)
    # No guest df was run, so there is no defensible number to show.
    assert disk.used_inside_bytes is None
    assert disk.potential_saving_bytes is None
    assert "reclaim unknown" in disk.status_note


def test_saving_is_host_size_minus_guest_usage(fake_vhdx):
    """Verify saving is host size minus guest usage via VirtualDisk.

    Args:
        fake_vhdx: The fake vhdx parameter.
    """
    disk = VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu", 8192, 8192,
                       used_inside_bytes=2048)
    assert disk.potential_saving_bytes == 6144
    assert disk.status_note == "ready to compact"


def test_saving_never_goes_negative(fake_vhdx):
    """Guest usage can exceed the host file for a sparse disk; clamp at zero.

    Args:
        fake_vhdx: The fake vhdx parameter.
    """
    disk = VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu", 8192, 1024,
                       used_inside_bytes=99999)
    assert disk.potential_saving_bytes == 0


def test_running_disk_names_the_blocking_process(fake_vhdx):
    """Verify running disk names the blocking process via VirtualDisk.

    Args:
        fake_vhdx: The fake vhdx parameter.
    """
    disk = VirtualDisk(fake_vhdx, DiskKind.DOCKER, "Docker Desktop", 8192, 8192,
                       running=True, blockers=("com.docker.backend.exe",))
    assert disk.can_compact is False
    assert "com.docker.backend.exe" in disk.status_note
    assert "close" in disk.status_note


def test_missing_file_is_reported_not_offered(tmp_path):
    """Verify missing file is reported not offered via VirtualDisk.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    disk = VirtualDisk(tmp_path / "gone.vhdx", DiskKind.WSL, "Ghost")
    assert disk.can_compact is False
    assert "no longer exists" in disk.status_note


def test_disk_to_dict_is_json_ready(fake_vhdx):
    """Verify disk to dict is json ready via VirtualDisk, json.loads, json.dumps.

    Args:
        fake_vhdx: The fake vhdx parameter.
    """
    import json
    disk = VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu", 8192, 8192,
                       used_inside_bytes=1024)
    payload = json.loads(json.dumps(disk.to_dict()))
    assert payload["kind"] == "wsl"
    assert payload["potential_saving_bytes"] == 7168
    assert payload["can_compact"] is True


# ---------------------------------------------------------------------------
# Discovery aggregation
# ---------------------------------------------------------------------------

def test_list_disks_dedupes_sorts_and_flags_blockers(monkeypatch, tmp_path):
    """Verify list disks dedupes sorts and flags blockers via VhdxManager, monkeypatch.setattr, mgr.list_disks.

    Args:
        monkeypatch: The monkeypatch parameter.
        tmp_path: Filesystem path to the target file or directory.
    """
    small = tmp_path / "small.vhdx"
    small.write_bytes(b"\0" * 1024)
    big = tmp_path / "big.vhdx"
    big.write_bytes(b"\0" * 100_000)

    mgr = VhdxManager()
    # The same Docker disk is reachable from both the WSL registry and the
    # Docker folder scan; it must appear once.
    monkeypatch.setattr(mgr, "_wsl_disks", lambda: [
        VirtualDisk(small, DiskKind.WSL, "Ubuntu"),
        VirtualDisk(big, DiskKind.DOCKER, "docker-desktop-data"),
    ])
    monkeypatch.setattr(mgr, "_docker_disks", lambda: [
        VirtualDisk(big, DiskKind.DOCKER, "Docker Desktop (big)"),
    ])
    monkeypatch.setattr(mgr, "_hyperv_disks", lambda: [])
    monkeypatch.setattr(VhdxManager, "_running_processes",
                        staticmethod(lambda: {"com.docker.backend.exe"}))

    disks = mgr.list_disks()
    assert len(disks) == 2, "the duplicate path must be collapsed"
    # Largest first, so the biggest win is at the top of the list.
    assert disks[0].path == big
    assert disks[0].on_disk_bytes >= disks[1].on_disk_bytes
    # Docker is "running", so its disk is blocked and names the process.
    assert disks[0].running is True
    assert disks[0].blockers == ("com.docker.backend.exe",)
    # The WSL disk has no blocker running, so it stays actionable.
    assert disks[1].running is False and disks[1].can_compact is True


@pytest.mark.skipif(not IS_WINDOWS, reason="registry/PowerShell probes are Windows-only")
def test_real_discovery_never_raises():
    """On a machine with no WSL/Docker/Hyper-V this must return [], not blow up."""
    disks = VhdxManager().list_disks()
    assert isinstance(disks, list)
    for d in disks:
        assert d.path.suffix.lower() in (".vhdx", ".vhd")


def test_unsupported_platform_returns_empty(monkeypatch):
    """Verify unsupported platform returns empty via monkeypatch.setattr, VhdxManager, list_disks.

    Args:
        monkeypatch: The monkeypatch parameter.
    """
    import cortex_unified.system_tools.vhdx_manager as mod
    monkeypatch.setattr(mod, "_IS_WINDOWS", False)
    assert VhdxManager().list_disks() == []
    assert VhdxManager().shutdown_wsl()[0] is False


# ---------------------------------------------------------------------------
# Compaction safety
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not IS_WINDOWS, reason="compaction is a Windows operation")
def test_compact_refuses_while_runtime_holds_the_disk(monkeypatch, fake_vhdx):
    """The whole point: never touch a disk that is still attached.

    Args:
        monkeypatch: The monkeypatch parameter.
        fake_vhdx: The fake vhdx parameter.
    """
    mgr = VhdxManager()
    monkeypatch.setattr(VhdxManager, "_running_processes",
                        staticmethod(lambda: {"wslservice.exe"}))

    def _boom(*_a, **_k):
        """Boom using AssertionError."""
        raise AssertionError("diskpart must not run while the disk is in use")

    monkeypatch.setattr(mgr, "_run_diskpart", _boom)

    result = mgr.compact(VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu"))
    assert result.success is False
    assert "wslservice.exe" in result.message
    assert result.freed_bytes == 0
    assert fake_vhdx.exists()


@pytest.mark.skipif(not IS_WINDOWS, reason="compaction is a Windows operation")
def test_compact_reports_measured_delta(monkeypatch, fake_vhdx):
    """Verify compact reports measured delta via pytest.mark.skipif, VhdxManager, monkeypatch.setattr.

    Args:
        monkeypatch: The monkeypatch parameter.
        fake_vhdx: The fake vhdx parameter.
    """
    mgr = VhdxManager()
    monkeypatch.setattr(VhdxManager, "_running_processes", staticmethod(set))

    def _shrink(script, timeout, cancel_event=None):
        """Shrink using fake_vhdx.write_bytes.

        Args:
            script: The script parameter.
            timeout: The timeout parameter.
            cancel_event: Threading event or callable to check for cancellation.
        """
        assert "attach vdisk readonly" in script, "must attach read-only"
        assert "compact vdisk" in script
        assert "detach vdisk" in script
        fake_vhdx.write_bytes(b"\0" * 2048)   # simulate a real compaction
        return True, "DiskPart successfully compacted the virtual disk file."

    monkeypatch.setattr(mgr, "_run_diskpart", _shrink)

    result = mgr.compact(VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu"))
    assert result.success is True
    assert result.before_bytes == 8192
    assert result.after_bytes == 2048
    assert result.freed_bytes == 6144


@pytest.mark.skipif(not IS_WINDOWS, reason="compaction is a Windows operation")
def test_compact_is_honest_when_nothing_was_reclaimed(monkeypatch, fake_vhdx):
    """Verify compact is honest when nothing was reclaimed via pytest.mark.skipif, VhdxManager, monkeypatch.setattr.

    Args:
        monkeypatch: The monkeypatch parameter.
        fake_vhdx: The fake vhdx parameter.
    """
    mgr = VhdxManager()
    monkeypatch.setattr(VhdxManager, "_running_processes", staticmethod(set))
    monkeypatch.setattr(mgr, "_run_diskpart",
                        lambda script, timeout, cancel_event=None: (True, "successfully compacted"))

    result = mgr.compact(VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu"))
    assert result.success is True
    assert result.freed_bytes == 0
    assert "no space was returned" in result.message


@pytest.mark.skipif(not IS_WINDOWS, reason="compaction is a Windows operation")
def test_compact_surfaces_permission_failure(monkeypatch, fake_vhdx):
    """Verify compact surfaces permission failure via pytest.mark.skipif, VhdxManager, monkeypatch.setattr.

    Args:
        monkeypatch: The monkeypatch parameter.
        fake_vhdx: The fake vhdx parameter.
    """
    mgr = VhdxManager()
    monkeypatch.setattr(VhdxManager, "_running_processes", staticmethod(set))
    monkeypatch.setattr(mgr, "_run_diskpart",
                        lambda script, timeout, cancel_event=None: (False, "Access is denied."))

    result = mgr.compact(VirtualDisk(fake_vhdx, DiskKind.WSL, "Ubuntu"))
    assert result.success is False
    assert "administrator" in result.message.lower()
    assert result.freed_bytes == 0


def test_compact_missing_file_fails_clearly(tmp_path):
    """Verify compact missing file fails clearly via VirtualDisk, VhdxManager, compact.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    result = VhdxManager().compact(
        VirtualDisk(tmp_path / "gone.vhdx", DiskKind.WSL, "Ghost"))
    assert result.success is False
    assert "no longer exists" in result.message


def test_failure_messages_are_actionable():
    """Verify failure messages are actionable via explain, lower."""
    explain = VhdxManager._explain_failure
    assert "Administrator" in explain("Access is denied.")
    assert "Stop WSL" in explain("The virtual disk is currently in use.")
    assert "diskpart" in explain("something unexpected").lower()


def test_compact_result_freed_bytes_never_negative(tmp_path):
    """A disk that grew during the run must not report negative savings.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    res = CompactResult(tmp_path / "x.vhdx", "X", True,
                        before_bytes=100, after_bytes=200)
    assert res.freed_bytes == 0


def test_decode_handles_utf16_console_output():
    """diskpart emits UTF-16LE with embedded NULs on some consoles."""
    raw = "successfully compacted".encode("utf-16-le")
    assert "successfully compacted" in VhdxManager._decode(raw)
    assert VhdxManager._decode(None) == ""


def test_sparse_mode_is_wsl_only(fake_vhdx):
    """Verify sparse mode is wsl only via VirtualDisk, msg.lower, VhdxManager.

    Args:
        fake_vhdx: The fake vhdx parameter.
    """
    ok, msg = VhdxManager().set_sparse(
        VirtualDisk(fake_vhdx, DiskKind.HYPERV, "VM"))
    assert ok is False
    assert "wsl" in msg.lower()
