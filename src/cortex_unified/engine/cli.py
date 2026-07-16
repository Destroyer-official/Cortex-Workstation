"""Modern, safe CLI for the Cortex engine.

Design principles:
* **Dry-run by default.** Nothing is deleted unless ``--apply`` is passed.
* **Honest.** ``shred`` refuses on flash media unless forced, and says why.
* **Scriptable.** ``--json`` emits machine-readable output for automation.
* **Fast.** Backed by the scandir walker + size-prefiltered dedup.

Exposed as ``cortex`` (see pyproject ``[project.scripts]``):

    cortex scan                      # what could be reclaimed (dry, human)
    cortex scan --json               # same, machine-readable
    cortex clean --apply             # actually reclaim (recycle bin)
    cortex clean --apply --method delete
    cortex duplicates PATH [PATH...]
    cortex large PATH --min-mb 200
    cortex empty PATH
    cortex shred FILE --apply        # storage-aware secure delete
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

try:
    import click
except ImportError:  # pragma: no cover
    click = None  # type: ignore

from .categories import RiskLevel
from .models import DeletionMethod
from .secure_delete import OverwriteNotEffective, SecureDeleter
from .service import CleanerService
from .storage import detect_storage


def _fmt_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024 or unit == "PB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


if click is not None:

    @click.group()
    @click.version_option(package_name="cortex-cleaner", message="cortex engine %(version)s")
    def main() -> None:
        """Cortex Cleaner - fast, safe, storage-aware system cleanup."""

    @main.command()
    @click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
    @click.option("--all", "include_disabled", is_flag=True, help="Include opt-in categories.")
    @click.option("--max-risk", type=click.Choice(["low", "medium", "high"]), default="medium")
    def scan(as_json: bool, include_disabled: bool, max_risk: str) -> None:
        """Report reclaimable space by category (read-only)."""
        report = CleanerService().scan_categories(
            max_risk=RiskLevel(max_risk), include_disabled=include_disabled
        )
        if as_json:
            click.echo(_json.dumps(report.to_dict(), indent=2))
            return
        if not report.scans:
            click.echo("Nothing to clean - system looks tidy.")
            return
        click.echo("Reclaimable space by category:\n")
        for s in report.scans:
            click.echo(
                f"  [{s.category.risk.value:^6}] {s.category.label:<28} "
                f"{_fmt_bytes(s.total_bytes):>10}  ({s.file_count} files)"
            )
        click.echo(
            f"\n  Total: {_fmt_bytes(report.total_reclaimable_bytes)} "
            f"across {report.total_files} files "
            f"(scanned in {report.duration_seconds:.2f}s)"
        )

    @main.command()
    @click.option("--apply", "apply", is_flag=True, help="Actually delete (default: dry-run).")
    @click.option("--method", type=click.Choice(["recycle", "delete"]), default="recycle")
    @click.option("--all", "include_disabled", is_flag=True, help="Include opt-in categories.")
    @click.option("--max-risk", type=click.Choice(["low", "medium", "high"]), default="medium")
    def clean(apply: bool, method: str, include_disabled: bool, max_risk: str) -> None:
        """Reclaim space. Dry-run unless --apply is given."""
        service = CleanerService()
        report = service.scan_categories(
            max_risk=RiskLevel(max_risk), include_disabled=include_disabled
        )
        if not report.scans:
            click.echo("Nothing to clean.")
            return

        chosen = (
            DeletionMethod.DRY_RUN if not apply
            else DeletionMethod(method)
        )
        results = service.clean_categories(report, chosen)
        freed = sum(r.size for r in results if r.succeeded and r.method is not DeletionMethod.DRY_RUN)
        ok = sum(1 for r in results if r.succeeded)
        blocked = sum(1 for r in results if not r.succeeded)

        if not apply:
            click.echo(
                f"[DRY-RUN] Would reclaim {_fmt_bytes(report.total_reclaimable_bytes)} "
                f"from {report.total_files} files. Re-run with --apply to act."
            )
        else:
            click.echo(
                f"Reclaimed {_fmt_bytes(freed)} ({ok} items, method={method})."
                + (f" {blocked} blocked by safety guard." if blocked else "")
            )

    @main.command()
    @click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
    @click.option("--json", "as_json", is_flag=True)
    def duplicates(paths: tuple[str, ...], as_json: bool) -> None:
        """Find duplicate files across PATHS."""
        groups = CleanerService().find_duplicates([Path(p) for p in paths])
        if as_json:
            click.echo(_json.dumps({k: [str(p) for p in v] for k, v in groups.items()}, indent=2))
            return
        if not groups:
            click.echo("No duplicates found.")
            return
        for i, (_, members) in enumerate(groups.items(), 1):
            click.echo(f"Group {i} ({len(members)} copies):")
            for p in members:
                click.echo(f"    {p}")

    @main.command()
    @click.argument("path", type=click.Path(exists=True))
    @click.option("--min-mb", type=float, default=100.0, show_default=True)
    @click.option("--limit", type=int, default=50, show_default=True)
    def large(path: str, min_mb: float, limit: int) -> None:
        """List the largest files under PATH."""
        for e in CleanerService().find_large_files(path, min_mb=min_mb, limit=limit):
            click.echo(f"  {_fmt_bytes(e.size):>10}  {e.path}")

    @main.command()
    @click.argument("path", type=click.Path(exists=True))
    def empty(path: str) -> None:
        """List empty files and directories under PATH."""
        files, dirs = CleanerService().find_empty(path)
        click.echo(f"Empty files: {len(files)}, empty dirs: {len(dirs)}")
        for p in files + dirs:
            click.echo(f"    {p}")

    @main.command()
    @click.argument("target", type=click.Path(exists=True))
    @click.option("--apply", "apply", is_flag=True, help="Actually shred (default: preview).")
    @click.option("--passes", type=int, default=3, show_default=True)
    @click.option("--force-flash", is_flag=True, help="Overwrite on SSD anyway (best-effort).")
    def shred(target: str, apply: bool, passes: int, force_flash: bool) -> None:
        """Securely delete TARGET (storage-aware; honest about SSD limits)."""
        info = detect_storage(target)
        click.echo(f"Detected medium: {info.kind.value}"
                   + ("" if info.kind.overwrite_effective else "  (overwrite NOT reliable here)"))
        if not apply:
            click.echo("[PREVIEW] Re-run with --apply to shred.")
            return
        deleter = SecureDeleter(overwrite_passes=passes)
        try:
            res = deleter.delete(target, DeletionMethod.OVERWRITE, force_overwrite_on_flash=force_flash)
            click.echo(f"{res.outcome.value}: {target}" + (f"  ({res.reason})" if res.reason else ""))
        except OverwriteNotEffective as exc:
            click.echo(f"Refused: {exc}", err=True)
            click.echo("Tip: use full-disk encryption + key destruction, or the drive's "
                       "hardware secure-erase; or pass --force-flash to overwrite anyway.", err=True)
            sys.exit(2)

else:  # pragma: no cover

    def main() -> None:
        raise SystemExit("The 'click' package is required for the Cortex CLI. Install it with: pip install click")


if __name__ == "__main__":  # pragma: no cover
    main()
