"""Stage-2 tests: end-to-end FFI transfers (copy/move/delete/pause/conflicts).

These execute the real Rust transfer engine through nexus_engine.dll —
the same code path the product will ship.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "native"))

nexus_ffi = pytest.importorskip("nexus_ffi")
try:
    nexus_ffi.find_dll()
except FileNotFoundError:
    pytest.skip("nexus_engine.dll not built", allow_module_level=True)


@pytest.fixture(scope="module")
def ffi():
    """ffi."""
    f = nexus_ffi.NexusFfi()
    yield f
    f.close()


@pytest.fixture
def dirs(tmp_path):
    """dirs."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    return src, dst


def _payload(n: int, byte: bytes = b"A") -> bytes:
    """_payload."""
    return byte * n


class TestBasicTransfers:
    """TestBasicTransfers."""
    def test_copy_multi_unicode(self, ffi, dirs):
        """test_copy_multi_unicode."""
        src, dst = dirs
        names = ["one.txt", "emoji_\U0001F4C1.dat", "sub space.md"]
        for i, n in enumerate(names):
            (src / n).write_bytes(_payload(1024 * (i + 1)))
        r = ffi.copy([str(src / n) for n in names], str(dst))
        assert r["ok"], r["error"]
        for i, n in enumerate(names):
            assert (dst / n).read_bytes() == _payload(1024 * (i + 1))

    def test_move_removes_source(self, ffi, dirs):
        """test_move_removes_source."""
        src, dst = dirs
        p = src / "mv.txt"
        p.write_bytes(_payload(2048, b"M"))
        r = ffi.move([str(p)], str(dst))
        assert r["ok"], r["error"]
        assert (dst / "mv.txt").read_bytes() == _payload(2048, b"M")
        assert not p.exists()

    def test_delete_permanent(self, ffi, dirs):
        """test_delete_permanent."""
        src, _ = dirs
        v = src / "gone.bin"
        v.write_bytes(b"Z" * 10)
        r = ffi.delete_paths([str(v)], to_trash=False)
        assert r["ok"], r["error"]
        assert not v.exists()

    def test_delete_to_trash(self, ffi, dirs):
        """test_delete_to_trash."""
        src, _ = dirs
        v = src / "trashed.bin"
        v.write_bytes(b"T" * 10)
        r = ffi.delete_paths([str(v)], to_trash=True)
        assert r["ok"], r["error"]
        assert not v.exists()


def _run_with_policy(ffi, src_file, dst_dir, policy: int) -> dict:
    """copy() with a custom conflict policy answer."""
    import ctypes

    keep: list = []
    result = {"ok": False, "error": "", "conflicts": 0}
    done = threading.Event()

    def on_conflict(_ud, _j, cid, s, d, ss, ds, sm, dm, is_dir):
        """on_conflict."""
        result["conflicts"] += 1
        return policy

    starter_arr = ffi._cstr_array([str(src_file)])
    dest_b = str(dst_dir).encode()

    pc = nexus_ffi.PROGRESS_CALLBACK(lambda *a: None)
    cc = nexus_ffi.COMPLETION_CALLBACK(
        lambda _ud, _j, s, e: (
            result.__setitem__("ok", bool(s)),
            result.__setitem__("error", e.decode("utf-8", "replace") if e else ""),
            done.set(),
        )
    )
    xc = nexus_ffi.CONFLICT_CALLBACK(on_conflict)
    keep.extend([pc, cc, xc])
    h = ffi._dll.nexus_copy(ffi._handle, starter_arr, 1, dest_b, pc, cc, xc, None)
    assert h
    assert done.wait(timeout=60), "transfer timed out"
    ffi._dll.nexus_free_job_handle(h)
    return result


class TestConflictPolicies:
    """TestConflictPolicies."""
    def test_overwrite_replaces_content(self, ffi, dirs):
        """test_overwrite_replaces_content."""
        src, dst = dirs
        (src / "c.txt").write_bytes(b"S" * 400)
        (dst / "c.txt").write_bytes(b"D" * 100)
        r = _run_with_policy(ffi, src / "c.txt", dst, 1)
        assert r["ok"], r["error"]
        assert r["conflicts"] == 1
        assert (dst / "c.txt").read_bytes() == b"S" * 400

    def test_skip_preserves_destination(self, ffi, dirs):
        """test_skip_preserves_destination."""
        src, dst = dirs
        (src / "s.txt").write_bytes(b"S" * 400)
        (dst / "s.txt").write_bytes(b"D" * 100)
        r = _run_with_policy(ffi, src / "s.txt", dst, 0)
        assert r["ok"], r["error"]
        assert (dst / "s.txt").read_bytes() == b"D" * 100

    def test_keep_both_creates_sibling(self, ffi, dirs):
        """test_keep_both_creates_sibling."""
        src, dst = dirs
        (src / "k.txt").write_bytes(b"S" * 300)
        (dst / "k.txt").write_bytes(b"D" * 50)
        r = _run_with_policy(ffi, src / "k.txt", dst, 2)
        assert r["ok"], r["error"]
        assert (dst / "k.txt").read_bytes() == b"D" * 50
        siblings = [p for p in dst.iterdir() if p.name.startswith("k")]
        assert len(siblings) == 2


class TestPauseResumeCancel:
    """TestPauseResumeCancel."""
    @pytest.fixture(scope="class")
    def big_src(self, tmp_path_factory):
        """big_src."""
        d = tmp_path_factory.mktemp("big")
        p = d / "big.bin"
        chunk = os.urandom(1024 * 1024)
        with open(p, "wb") as fh:
            for _ in range(192):  # 192 MB
                fh.write(chunk)
        return p

    def _copy_big_with_control(self, ffi, big_src, dst_dir, action):
        """action(progress_cb_handle_holder, done_bytes) -> None, called from
        the worker callback thread."""
        keep: list = []
        result = {"ok": False, "error": "", "progress": []}
        done = threading.Event()
        holder = {}

        arr = ffi._cstr_array([str(big_src)])
        dest_b = str(dst_dir).encode()

        def on_progress(_ud, _j, db, tb, sp, eta, cur):
            """on_progress."""
            result["progress"].append(int(db))
            if holder.get("handle") and not holder.get("acted"):
                action(holder, int(db))
            # cap unbounded growth
            if len(result["progress"]) > 200000:
                result["progress"].clear()

        def on_complete(_ud, _j, s, e):
            """on_complete."""
            result["ok"] = bool(s)
            result["error"] = e.decode("utf-8", "replace") if e else ""
            done.set()

        pc = nexus_ffi.PROGRESS_CALLBACK(on_progress)
        cc = nexus_ffi.COMPLETION_CALLBACK(on_complete)
        xc = nexus_ffi.CONFLICT_CALLBACK(lambda *a: 0)
        keep.extend([pc, cc, xc])
        h = ffi._dll.nexus_copy(ffi._handle, arr, 1, dest_b, pc, cc, xc, None)
        holder["handle"] = h
        assert h
        assert done.wait(timeout=600), "big copy timed out"
        ffi._dll.nexus_free_job_handle(h)
        return result

    def test_pause_resume_completes(self, ffi, big_src, tmp_path):
        """test_pause_resume_completes."""
        dst = tmp_path / "pr_out"
        dst.mkdir()
        state = {"paused": False}

        def act(holder, _db):
            """act."""
            if not state["paused"]:
                state["paused"] = True
                assert ffi.pause_job(holder["handle"]) == 0
                holder["pause_at"] = _db
                threading.Timer(0.7, lambda: ffi.resume_job(holder["handle"])).start()

        r = self._copy_big_with_control(ffi, big_src, dst, act)
        assert r["ok"], r["error"]
        assert state["paused"], "pause must have been exercised"
        out = dst / "big.bin"
        assert out.stat().st_size == big_src.stat().st_size

    def test_cancel_reports_not_ok(self, ffi, big_src, tmp_path):
        """test_cancel_reports_not_ok."""
        dst = tmp_path / "cx_out"
        dst.mkdir()
        state = {"cancelled": False}

        def act(holder, _db):
            """act."""
            if not state["cancelled"]:
                state["cancelled"] = True
                ffi.cancel_job(holder["handle"])

        r = self._copy_big_with_control(ffi, big_src, dst, act)
        assert not r["ok"], "cancelled job must not report success"
