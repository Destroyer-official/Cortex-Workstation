"""Stage-0 unit tests for the NexusExplorer native Python layer.

Run from repo root:  python -m pytest tests/native -v
GUI-dependent smoke coverage intentionally excluded here (see SPECIFICATION
Stage 0 DoD); these tests are pure/headless by design.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[2]
NATIVE = REPO / "native"
sys.path.insert(0, str(NATIVE))

from nexus_core import CLI_CANDIDATES, find_cli, fmt_ms, human  # noqa: E402


class TestFormatters:
    def test_human_bytes_scale(self):
        assert human(0) == "0 B"
        assert human(-1) == ""
        assert human(512).endswith("B")
        assert "KB" in human(2048)
        assert "MB" in human(5 * 1024 * 1024)
        assert "GB" in human(3 * 1024**3)

    def test_fmt_ms_empty(self):
        assert fmt_ms(0) == ""


@pytest.mark.skipif(not any(p.is_file() for p in CLI_CANDIDATES), reason="nexus-cli.exe not built")
def test_find_cli_locates_built_binary():
    cli = find_cli()
    assert cli.is_file(), f"nexus-cli.exe not found at {cli}"


class TestOpenWithQuotingRegression:
    """Regression for audit finding B8: os.startfile with embedded quotes."""

    def test_open_with_uses_argument_list(self, monkeypatch):
        import nexus_explorer  # noqa: PLC0415

        captured = {}
        fake_exe = str(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "FakeApp" / "app.exe")
        fake_path = str(Path.home() / "doc with space.txt")

        def fake_popen(args, **kwargs):
            captured["args"] = args
            return SimpleNamespace(pid=0)

        monkeypatch.setattr(nexus_explorer.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(
            nexus_explorer.QFileDialog,
            "getOpenFileName",
            lambda *a, **k: (fake_exe, ""),
        )

        stub_self = SimpleNamespace()
        nexus_explorer.ExplorerWidget._open_with(stub_self, fake_path)

        args = captured["args"]
        assert isinstance(args, list), "must pass an argument LIST, not a string"
        assert args[0] == fake_exe
        assert args[1] == fake_path
        assert '"' not in "".join(args), "no literal quotes may be embedded"


@pytest.mark.skipif(
    os.name != "nt" or not any(p.is_file() for p in CLI_CANDIDATES),
    reason="Windows-only engine binary required"
)
class TestCliJsonContract:
    """Mirror of the Rust-side entries_to_json tests, end-to-end via CLI."""

    @pytest.fixture
    def hostile_dir(self):
        with tempfile.TemporaryDirectory(prefix="nexus_test_") as tmp:
            names = ["emoji_📁.txt", "unicode_é中文.txt", "plain.md", "spaced  name.txt"]
            for n in names:
                Path(tmp, n).write_text("", encoding="utf-8")
            yield tmp, names

    def test_list_json_round_trip(self, hostile_dir):
        tmp, names = hostile_dir
        out = subprocess.run(
            [str(find_cli()), "list", tmp, "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=True,
        )
        rows = json.loads(out.stdout)
        got = {r["name"] for r in rows}
        missing = [n for n in names if n not in got]
        assert not missing, f"files vanished from JSON output: {missing}"

    def test_list_json_consumer_keys(self, hostile_dir):
        tmp, _ = hostile_dir
        out = subprocess.run(
            [str(find_cli()), "list", tmp, "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=True,
        )
        row = json.loads(out.stdout)[0]
        for key in ("name", "path", "isDir", "size", "modifiedMs"):
            assert key in row, f"consumer contract key missing: {key}"
