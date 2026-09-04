"""Stage-2b tests: job journal + orphan .nexuspart discovery."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "native"))

nexus_ffi = pytest.importorskip("nexus_ffi")
try:
    nexus_ffi.find_dll()
except FileNotFoundError:
    pytest.skip("nexus_engine.dll not built", allow_module_level=True)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """data_dir.

    Manages data dir operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
        monkeypatch: The monkeypatch parameter.
    """
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setenv("NEXUS_DATA_DIR", str(d))
    return d


@pytest.fixture
def ffi():
    """Ffi.

    Manages ffi operations and coordinates related state changes for the component.
    """
    f = nexus_ffi.NexusFfi()
    yield f
    f.close()


def _journal_lines(data_dir: Path) -> list[dict]:
    """_journal_lines.

    Manages journal lines operations and coordinates related state changes for the component.

    Args:
        data_dir (Path): The data dir parameter.

    Returns:
        list[dict]: List of processed items or identifiers.
    """
    p = data_dir / "jobs.jsonl"
    assert p.is_file(), "journal must be created"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_journal_records_lifecycle(data_dir, ffi, tmp_path):
    """test_journal_records_lifecycle.

    Manages test journal records lifecycle operations and coordinates related state changes for the component.

    Args:
        data_dir: The data dir parameter.
        ffi: The ffi parameter.
        tmp_path: Filesystem path to the target file or directory.
    """
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "j.txt").write_bytes(b"J" * 512)

    r = ffi.copy([str(src / "j.txt")], str(dst))
    assert r["ok"], r["error"]

    lines = _journal_lines(data_dir)
    states = [l["state"] for l in lines if l["kind"] == "copy"]
    assert states[0] == "running"
    assert states[-1] == "completed"
    rec = lines[-1]
    assert rec["job_id"] and rec["dest_dir"] == str(dst)
    assert rec["ts_ms"] > 0


def test_orphans_detects_interrupted_and_ignores_completed(data_dir, ffi, tmp_path):
    # a real completed copy must NOT appear as orphan
    """test_orphans_detects_interrupted_and_ignores_completed.

    Manages test orphans detects interrupted and ignores completed operations and coordinates related state changes for the component.

    Args:
        data_dir: The data dir parameter.
        ffi: The ffi parameter.
        tmp_path: Filesystem path to the target file or directory.
    """
    src = tmp_path / "src"
    dst_ok = tmp_path / "dst_ok"
    src.mkdir()
    dst_ok.mkdir()
    (src / "ok.txt").write_bytes(b"K")
    assert ffi.copy([str(src / "ok.txt")], str(dst_ok))["ok"]
    assert ffi.orphans() == []

    # fabricate an interrupted job: running-state record + leftover part file
    dst_bad = tmp_path / "dst_bad"
    dst_bad.mkdir()
    part = dst_bad / "orphan.bin.nexuspart"
    part.write_bytes(b"P" * 4096)

    jid = "11111111-2222-3333-4444-555555555555"
    line = {
        "ts_ms": int(time.time() * 1000) - 600_000,  # 10 min old
        "job_id": jid,
        "kind": "copy",
        "state": "running","pid": 999999,
        "sources": [str(src)],
        "dest_dir": str(dst_bad),
    }
    with open(data_dir / "jobs.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")

    orphans = ffi.orphans()
    match = [o for o in orphans if o["job_id"] == jid]
    assert len(match) == 1
    o = match[0]
    assert Path(o["part_file"]).name == "orphan.bin.nexuspart"
    assert o["bytes"] == 4096
    assert o["last_state"] == "running"
    assert o["kind"] == "copy"


def test_orphan_scan_tolerates_missing_journal(ffi):
    # default LOCALAPPDATA may or may not have a journal; call must not raise
    """test_orphan_scan_tolerates_missing_journal.

    Manages test orphan scan tolerates missing journal operations and coordinates related state changes for the component.

    Args:
        ffi: The ffi parameter.
    """
    assert isinstance(ffi.orphans(), list)
