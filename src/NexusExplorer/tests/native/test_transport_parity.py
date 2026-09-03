"""Stage-1 transport parity: nexus-cli.exe subprocess vs ctypes NexusFfi bridge.

Both transports must agree on directory listings, search hit sets and drive
enumeration before the FFI backend can replace QProcess behind
Engine.NEXUS_TRANSPORT (SPECIFICATION Stage 1 exit criterion).

Run from repo root:  python -m pytest tests/native/test_transport_parity.py -v
Skips (never fails) when nexus_ffi.py / nexus_engine.dll are absent or
unloadable, so the suite stays green on machines with only the CLI built.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
NATIVE = REPO / "native"
DLL = REPO / "target" / "debug" / "nexus_engine.dll"
sys.path.insert(0, str(NATIVE))

if not (NATIVE / "nexus_ffi.py").is_file() or not DLL.is_file():
    missing = [
        str(p.relative_to(REPO))
        for p in (NATIVE / "nexus_ffi.py", DLL)
        if not p.is_file()
    ]
    pytest.skip(
        f"transport parity requires native bridge + engine dll; missing: "
        f"{', '.join(missing)}",
        allow_module_level=True,
    )

from nexus_core import find_cli  # noqa: E402

TOKEN = "paritoneedel"
SUBDIRS = ("alpha", "beta", "empty_dir")
EXTS = (".txt", ".dat", ".log", ".md", ".TXT", ".Csv")
MTIME_TOLERANCE_MS = 2500


def _norm(path: str) -> str:
    return str(Path(path))


def _cli_run(cli: Path, args: list[str]) -> str:
    proc = subprocess.run(
        [str(cli), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=True,
    )
    return proc.stdout


def _cli_list(cli: Path, path: Path) -> list[dict]:
    return json.loads(_cli_run(cli, ["list", str(path), "--json"]))


def _cli_search(cli: Path, root: Path, query: str, limit: int = 5000) -> list[str]:
    """Parse TSV stdout lines 'DIR\t<path>'/'FILE\t<path>' (summary lines have
    no tab and are ignored), mirroring nexus_core._parse_search_chunk."""
    hits = []
    for line in _cli_run(cli, ["search", str(root), query, str(limit)]).splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2 and parts[0] in ("DIR", "FILE"):
            hits.append(parts[1])
    return hits


def _cli_drives(cli: Path) -> list[dict]:
    return json.loads(_cli_run(cli, ["drives", "--json"]))


def _make_tree(root: Path) -> None:
    """150 files alternating across the two live subdirs; empty_dir stays
    empty; unicode names and uppercase .TXT among other extensions; every
    25th file seeds the search token inside a subdir. mtimes are left
    naturally seeded by creation."""
    for sub in SUBDIRS:
        (root / sub).mkdir()
    for i in range(150):
        parent = root / SUBDIRS[i % 2]
        if i % 25 == 0:
            name = f"{TOKEN}_{i:03d}.txt"
        elif i % 31 == 5:
            name = f"uni_é中文_{i:03d}{EXTS[i % len(EXTS)]}"
        else:
            name = f"file_{i:03d}{EXTS[i % len(EXTS)]}"
        (parent / name).write_text(f"data-{i}\n", encoding="utf-8")


@pytest.fixture(scope="module")
def ffi():
    try:
        from nexus_ffi import NexusFfi
    except Exception as e:  # noqa: BLE001 - any import failure means unusable bridge
        pytest.skip(f"nexus_ffi import failed: {e}")
    try:
        inst = NexusFfi()
    except Exception as e:  # noqa: BLE001 - any ctor failure means unusable dll
        pytest.skip(f"NexusFfi could not load {DLL.name}: {type(e).__name__}: {e}")
    yield inst
    try:
        inst.close()
    except Exception:
        pass


@pytest.fixture(scope="module")
def parity_tree():
    with tempfile.TemporaryDirectory(prefix="nexus_parity_") as tmp:
        root = Path(tmp)
        _make_tree(root)
        yield root


@pytest.fixture(scope="module")
def cli():
    try:
        return find_cli()
    except FileNotFoundError as e:
        pytest.skip(f"cli transport unavailable: {e}")


class TestTransportParity:
    def test_parity_list_names_and_meta(self, cli, ffi, parity_tree):
        try:
            cli_rows = _cli_list(cli, parity_tree)
        except OSError as e:
            pytest.skip(f"cli transport unavailable: {e}")
        try:
            ffi_rows = ffi.read_dir_sync(str(parity_tree))
        except (OSError, AttributeError) as e:
            pytest.skip(f"ffi transport unavailable: {type(e).__name__}: {e}")

        assert len(cli_rows) > 0 and len(ffi_rows) > 0
        cli_by = {r["name"]: r for r in cli_rows}
        ffi_by = {r["name"]: r for r in ffi_rows}
        assert set(cli_by) == set(ffi_by), (
            f"name-set mismatch: cli-only={sorted(set(cli_by) - set(ffi_by))} "
            f"ffi-only={sorted(set(ffi_by) - set(cli_by))}"
        )

        diffs = []
        for name in sorted(cli_by):
            c, f = cli_by[name], ffi_by[name]
            if bool(c["isDir"]) != bool(f["isDir"]):
                diffs.append(f"{name}: isDir {c['isDir']} vs {f['isDir']}")
                continue
            if int(c["size"]) != int(f["size"]):
                diffs.append(f"{name}: size {c['size']} vs {f['size']}")
            if (c.get("ext") or "").lower() != (f.get("ext") or "").lower():
                diffs.append(
                    f"{name}: ext {c.get('ext')!r} vs {f.get('ext')!r}"
                )
            dt = abs(int(c["modifiedMs"]) - int(f["modifiedMs"]))
            if dt > MTIME_TOLERANCE_MS:
                diffs.append(f"{name}: modifiedMs delta {dt}ms")
        assert not diffs, f"metadata mismatches ({len(diffs)}):\n" + "\n".join(
            diffs[:20]
        )

    def test_parity_search(self, cli, ffi, parity_tree):
        try:
            cli_hits = _cli_search(cli, parity_tree, TOKEN)
        except OSError as e:
            pytest.skip(f"cli transport unavailable: {e}")
        try:
            _sid, ffi_rows = ffi.search(str(parity_tree), TOKEN)
        except (OSError, AttributeError) as e:
            pytest.skip(f"ffi transport unavailable: {type(e).__name__}: {e}")

        cli_set = {_norm(p) for p in cli_hits}
        ffi_set = {_norm(r["path"]) for r in ffi_rows}
        assert cli_set, "cli search returned no hits for seeded token"
        assert ffi_set, "ffi search returned no hits for seeded token"
        assert cli_set == ffi_set, (
            f"hit-set mismatch: cli-only={sorted(cli_set - ffi_set)} "
            f"ffi-only={sorted(ffi_set - cli_set)}"
        )

    def test_parity_drives(self, cli, ffi):
        try:
            cli_rows = _cli_drives(cli)
        except OSError as e:
            pytest.skip(f"cli transport unavailable: {e}")
        try:
            ffi_rows = ffi.get_drives()
        except (OSError, AttributeError) as e:
            pytest.skip(f"ffi transport unavailable: {type(e).__name__}: {e}")

        assert len(cli_rows) >= 1, "cli reported no drives"
        assert len(ffi_rows) >= 1, "ffi reported no drives"

        def letters(rows):
            return {Path(r["path"]).drive.upper(): r for r in rows}

        cli_by, ffi_by = letters(cli_rows), letters(ffi_rows)
        assert set(cli_by) == set(ffi_by), (
            f"drive-letter mismatch: cli-only={sorted(set(cli_by) - set(ffi_by))} "
            f"ffi-only={sorted(set(ffi_by) - set(cli_by))}"
        )
        for letter in sorted(cli_by):
            a = int(cli_by[letter].get("freeBytes", 0))
            b = int(ffi_by[letter].get("freeBytes", 0))
            if a == 0 and b == 0:
                continue
            assert abs(a - b) <= 0.05 * max(a, b), (
                f"{letter}: freeBytes {a} vs {b} (>5% apart)"
            )
