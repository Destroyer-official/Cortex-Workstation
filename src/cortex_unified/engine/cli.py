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
    cortex leftovers scan "App"      # post-uninstall residual scan (read-only)
    cortex leftovers orphans         # unclaimed Program Files folders
    cortex leftovers clean "App" --apply   # recycle findings (+ .reg backups)
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

try:
    import click
except ImportError:  # pragma: no cover
    click = None  # type: ignore

from cortex_unified import __version__
from .categories import RiskLevel
from .models import DeletionMethod
from .secure_delete import OverwriteNotEffective, SecureDeleter
from .service import CleanerService
from .storage import detect_storage

try:
    from cortex_unified.licensing.license_manager import (
        DEFAULT_TERM_DAYS,
        TRIAL_DAYS,
        get_license_manager,
    )
    from cortex_unified.licensing.tiers import Feature, Tier
except ImportError:  # pragma: no cover - licensing ships with the package
    Feature = Tier = get_license_manager = None  # type: ignore
    TRIAL_DAYS = DEFAULT_TERM_DAYS = 0  # type: ignore

try:
    from cortex_unified.system_tools.game_mode import GameMode
    from cortex_unified.system_tools.memory_optimizer import (
        memory_stats,
        optimize,
    )
except ImportError:  # pragma: no cover - optional heavy deps degrade cleanly
    GameMode = None  # type: ignore
    memory_stats = optimize = None  # type: ignore

_LEVEL_ORDER = {"bad": 0, "questionable": 1, "good": 2, "verygood": 3}


def _require_feature(feature) -> None:
    """Gate a CLI command on a licensing Feature (clean click error if denied).

    Manages require feature operations and coordinates related state changes for the component.

    Args:
        feature: The feature parameter.
    """
    from cortex_unified.licensing.gating import EntitlementError, require
    try:
        require(feature)
    except EntitlementError as exc:
        raise click.UsageError(str(exc)) from exc


def _fmt_memory_stats(stats: dict) -> str:
    """Human rendering for ``cortex memory --stats-only``.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        stats (dict): The stats parameter.

    Returns:
        str: Formatted string or path.
    """
    if not stats.get("supported"):
        return "Memory statistics require psutil."
    lines = [
        f"RAM: {_fmt_bytes(stats['used_bytes'])} / {_fmt_bytes(stats['total_bytes'])} "
        f"({stats['percent_used']}% used), "
        f"{_fmt_bytes(stats['available_bytes'])} available",
        f"Swap: {stats['swap_percent_used']}% used",
        "Top consumers:",
    ]
    for entry in stats.get("top_consumers", []):
        lines.append(
            f"  {_fmt_bytes(entry['rss_bytes']):>10}  "
            f"{entry['name']} (pid {entry['pid']})"
        )
    return "\n".join(lines)


def _find_app_by_name(name: str):
    """Locate an installed/uninstalled app record by display name.

    Manages find app by name operations and coordinates related state changes for the component.

    Args:
        name (str): The name parameter.
    """
    from cortex_unified.system_tools.leftover_cleaner import (
        InstalledApp,
        read_installed_apps,
    )
    wanted = name.strip().lower()
    for app in read_installed_apps():
        if app.name.lower() == wanted:
            return app
    # Fall back to a still-scanable record built from just the name.
    return InstalledApp(name=name.strip())


def _echo_findings(findings, as_json: bool) -> None:
    """_echo_findings.

    Manages echo findings operations and coordinates related state changes for the component.

    Args:
        findings: The findings parameter.
        as_json (bool): The as json parameter.
    """
    if as_json:
        click.echo(_json.dumps([f.to_dict() for f in findings], indent=2))
        return
    if not findings:
        click.echo("No leftovers found - the uninstall was clean.")
        return
    total = sum(f.size_bytes for f in findings)
    for f in findings:
        click.echo(f"  [{f.level:^12}] {_fmt_bytes(f.size_bytes):>10}  "
                   f"{f.kind:<8}  {f.path}")
    click.echo(f"\n  {len(findings)} item(s), {_fmt_bytes(total)} reclaimable. "
               "Review before cleaning: 'Questionable' rows may be shared.")


def _fmt_bytes(n: int) -> str:
    """_fmt_bytes.

    Converts raw numeric values into formatted, localized, and human-readable string representations.

    Args:
        n (int): The n parameter.

    Returns:
        str: Formatted string or path.
    """
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024 or unit == "PB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


if click is not None:

    @click.group()
    @click.version_option(version=__version__, message="cortex engine %(version)s")
    def main() -> None:
        """Main.

        Manages main operations and coordinates related state changes for the component.
        """

    @main.command()
    @click.option("--json", "as_json", is_flag=True, help="Machine-readable output.")
    @click.option("--all", "include_disabled", is_flag=True, help="Include opt-in categories.")
    @click.option("--max-risk", type=click.Choice(["low", "medium", "high"]), default="medium")
    def scan(as_json: bool, include_disabled: bool, max_risk: str) -> None:
        """Report reclaimable space by category (read-only).

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Args:
            as_json (bool): The as json parameter.
            include_disabled (bool): The include disabled parameter.
            max_risk (str): The max risk parameter.
        """
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
        # Say out loud what was deliberately left out, so a large cloud folder
        # missing from the totals reads as a decision, not a failed scan.
        if report.cloud_note:
            click.echo(f"\n  Note: {report.cloud_note}")

    @main.command()
    @click.option("--apply", "apply", is_flag=True, help="Actually delete (default: dry-run).")
    @click.option("--method", type=click.Choice(["recycle", "delete"]), default="recycle")
    @click.option("--all", "include_disabled", is_flag=True, help="Include opt-in categories.")
    @click.option("--max-risk", type=click.Choice(["low", "medium", "high"]), default="medium")
    def clean(apply: bool, method: str, include_disabled: bool, max_risk: str) -> None:
        """Reclaim space. Dry-run unless --apply is given.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            apply (bool): The apply parameter.
            method (str): The method parameter.
            include_disabled (bool): The include disabled parameter.
            max_risk (str): The max risk parameter.
        """
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
        """Duplicates.

        Manages duplicates operations and coordinates related state changes for the component.

        Args:
            paths (tuple[str, ...]): Filesystem path to the target file or directory.
            as_json (bool): The as json parameter.
        """
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
        """Large.

        Manages large operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
            min_mb (float): The min mb parameter.
            limit (int): The limit parameter.
        """
        for e in CleanerService().find_large_files(path, min_mb=min_mb, limit=limit):
            click.echo(f"  {_fmt_bytes(e.size):>10}  {e.path}")

    @main.command()
    @click.argument("path", type=click.Path(exists=True))
    def empty(path: str) -> None:
        """Empty.

        Manages empty operations and coordinates related state changes for the component.

        Args:
            path (str): Filesystem path to the target file or directory.
        """
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
        """Shred.

        Manages shred operations and coordinates related state changes for the component.

        Args:
            target (str): The target parameter.
            apply (bool): The apply parameter.
            passes (int): The passes parameter.
            force_flash (bool): The force flash parameter.
        """
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

    # ------------------------------------------------------------------
    #  Leftovers: post-uninstall residual detection + safe cleanup
    # ------------------------------------------------------------------

    @main.group()
    def leftovers() -> None:
        """Leftovers.

        Manages leftovers operations and coordinates related state changes for the component.
        """

    @leftovers.command("scan")
    @click.argument("app_name")
    @click.option("--json", "as_json", is_flag=True)
    def leftovers_scan(app_name: str, as_json: bool) -> None:
        """Scan APP_NAME's leftovers (read-only; works after uninstall too).

        Manages leftovers scan operations and coordinates related state changes for the component.

        Args:
            app_name (str): The app name parameter.
            as_json (bool): The as json parameter.
        """
        from cortex_unified.system_tools.leftover_cleaner import LeftoverScanner
        app = _find_app_by_name(app_name)
        findings = LeftoverScanner().scan_app(app)
        if not as_json:
            click.echo(f"Scanning leftovers for '{app.name}'...\n")
        _echo_findings(findings, as_json)

    @leftovers.command("orphans")
    @click.option("--json", "as_json", is_flag=True)
    def leftovers_orphans(as_json: bool) -> None:
        """List Program Files folders no installed app claims (read-only).

        Manages leftovers orphans operations and coordinates related state changes for the component.

        Args:
            as_json (bool): The as json parameter.
        """
        from cortex_unified.system_tools.leftover_cleaner import LeftoverScanner
        findings = LeftoverScanner().scan_orphans()
        if not as_json:
            click.echo("Scanning Program Files for orphan folders...\n")
        _echo_findings(findings, as_json)

    @leftovers.command("clean")
    @click.argument("app_name")
    @click.option("--apply", "apply", is_flag=True,
                  help="Actually clean (default: dry-run listing only).")
    @click.option("--min-level",
                  type=click.Choice(["questionable", "good", "verygood"]),
                  default="good",
                  help="Only clean findings at this confidence or higher.")
    @click.option("--restore-point", "restore_point", is_flag=True,
                  help="Attempt a System Restore checkpoint first (admin).")
    @click.option("--json", "as_json", is_flag=True)
    def leftovers_clean(app_name: str, apply: bool, min_level: str,
                        restore_point: bool, as_json: bool) -> None:
        """Clean APP_NAME's leftovers. Dry-run unless --apply.

        Manages leftovers clean operations and coordinates related state changes for the component.

        Args:
            app_name (str): The app name parameter.
            apply (bool): The apply parameter.
            min_level (str): The min level parameter.
            restore_point (bool): The restore point parameter.
            as_json (bool): The as json parameter.
        """
        from cortex_unified.system_tools.leftover_cleaner import (
            LeftoverCleaner,
            LeftoverFinding,
            LeftoverScanner,
        )
        app = _find_app_by_name(app_name)
        findings = [f for f in LeftoverScanner().scan_app(app)
                    if _LEVEL_ORDER.get(f.level.lower(), 0)
                    >= _LEVEL_ORDER[min_level]]
        if not findings:
            click.echo("Nothing to clean at this confidence level.")
            return
        if not apply:
            if as_json:
                click.echo(_json.dumps(
                    {"app": app.name, "dry_run": True,
                     "would_clean": [f.to_dict() for f in findings]}, indent=2))
            else:
                click.echo("[DRY-RUN] Would clean:\n")
                _echo_findings(findings, as_json=False)
                click.echo("\nRe-run with --apply to move files to the Recycle Bin "
                           "(registry keys are backed up as .reg first).")
            return
        outcomes = LeftoverCleaner().clean(
            [LeftoverFinding(kind=f.kind, path=f.path,
                             size_bytes=f.size_bytes, score=f.score,
                             level=f.level, reasons=list(f.reasons),
                             app_name=f.app_name)
             for f in findings],
            create_restore_point=restore_point,
        )
        ok = [o for o in outcomes if o.ok]
        failed = [o for o in outcomes if not o.ok]
        freed = sum(f.size_bytes for f, o in zip(findings, outcomes)
                    if o.disposition == "recycled")
        payload = {
            "app": app.name,
            "ok": len(ok), "failed": len(failed),
            "recycled_bytes": freed,
            "outcomes": [o.to_dict() for o in outcomes],
        }
        if as_json:
            click.echo(_json.dumps(payload, indent=2))
        else:
            click.echo(f"Cleaned '{app.name}': {len(ok)} ok, {len(failed)} failed, "
                       f"{_fmt_bytes(freed)} to the Recycle Bin.")
            for o in failed[:10]:
                click.echo(f"  FAILED [{o.disposition}] {o.path}: {o.detail}",
                           err=True)
        if failed:
            sys.exit(1)

    # -- licensing -------------------------------------------------------------

    @main.group()
    def license() -> None:
        """License.

        Manages license operations and coordinates related state changes for the component.
        """

    @license.command("status")
    @click.option("--json", "as_json", is_flag=True)
    def license_status(as_json: bool) -> None:
        """Show the current tier, features and expiry (works offline).

        Manages license status operations and coordinates related state changes for the component.

        Args:
            as_json (bool): The as json parameter.
        """
        from cortex_unified.licensing import effective_features
        state = get_license_manager().validate()
        if as_json:
            click.echo(_json.dumps(
                {**state.to_dict(),
                 "features": sorted(f.value for f in effective_features())},
                indent=2))
            return
        click.echo(f"Tier:     {state.tier.value.title()}"
                   f"{' (trial)' if state.trial else ''}")
        if state.licensed:
            click.echo(f"Key:      {state._masked_key()}")
            click.echo(f"Expires:  {state.expiry}")
            if state.grace_active:
                click.echo(f"Status:   {state.reason}", err=True)
        else:
            click.echo(f"Status:   {state.reason}")
        click.echo(f"Features: {len(state.features)} unlocked")

    @license.command("activate")
    @click.option("--key", required=True, help="License key from your order.")
    @click.option("--tier",
                  type=click.Choice([t.value for t in Tier]),
                  default="pro", show_default=True)
    @click.option("--name", default="", help="Licensed-to name.")
    @click.option("--email", default="", help="Licensed-to email.")
    @click.option("--days", type=int, default=DEFAULT_TERM_DAYS,
                  help="License term in days.")
    @click.option("--json", "as_json", is_flag=True)
    def license_activate(key: str, tier: str, name: str, email: str,
                         days: int, as_json: bool) -> None:
        """Bind KEY to this machine and activate TIER (fully offline).

        Manages license activate operations and coordinates related state changes for the component.

        Args:
            key (str): The key parameter.
            tier (str): The tier parameter.
            name (str): The name parameter.
            email (str): The email parameter.
            days (int): The days parameter.
            as_json (bool): The as json parameter.
        """
        try:
            state = get_license_manager().activate(
                key=key, tier=Tier(tier), name=name, email=email,
                term_days=days,
            )
        except ValueError as exc:
            raise click.UsageError(str(exc)) from exc
        if as_json:
            click.echo(_json.dumps(state.to_dict(), indent=2))
            return
        click.echo(f"Activated: {state.tier.value.title()} "
                   f"(expires {state.expiry}).")

    @license.command("trial")
    @click.option("--json", "as_json", is_flag=True)
    def license_trial(as_json: bool) -> None:
        """license_trial.

        Manages license trial operations and coordinates related state changes for the component.

        Args:
            as_json (bool): The as json parameter.
        """
        f"""Start the once-per-machine {TRIAL_DAYS}-day Pro trial."""
        try:
            state = get_license_manager().start_trial()
        except RuntimeError as exc:
            raise click.UsageError(str(exc)) from exc
        if as_json:
            click.echo(_json.dumps(state.to_dict(), indent=2))
            return
        click.echo(f"Trial active until {state.expiry}.")

    @license.command("deactivate")
    def license_deactivate() -> None:
        """Remove the license; this machine returns to the Free tier.

        Manages license deactivate operations and coordinates related state changes for the component.
        """
        get_license_manager().deactivate()
        click.echo("License removed. Tier: Free.")

    # -- premium boosts ----------------------------------------------------------

    @main.group()
    def boost() -> None:
        """Boost.

        Manages boost operations and coordinates related state changes for the component.
        """

    @boost.command("status")
    @click.option("--json", "as_json", is_flag=True)
    def boost_status(as_json: bool) -> None:
        """Preview what a boost would change on this machine right now.

        Manages boost status operations and coordinates related state changes for the component.

        Args:
            as_json (bool): The as json parameter.
        """
        _require_feature(Feature.GAMING_MODE)
        preview = GameMode().preview()
        if as_json:
            click.echo(_json.dumps(preview, indent=2))
            return
        click.echo(f"Supported:      {preview['supported']}")
        click.echo(f"Power plan now: {preview['power_now']}")
        click.echo(f"Would switch to: {preview['power_would_switch_to']}")
        click.echo("Would pause:")
        for name in preview["would_suspend"]:
            click.echo(f"  - {name}")

    @boost.command("start")
    @click.option("--dry-run", is_flag=True, help="Report without changing anything.")
    @click.option("--extra-suspend", multiple=True,
                  help="Extra process name to pause (repeatable).")
    @click.option("--json", "as_json", is_flag=True)
    def boost_start(dry_run: bool, extra_suspend: tuple, as_json: bool) -> None:
        """Apply the gaming boost (power plan + background quieting).

        Manages boost start operations and coordinates related state changes for the component.

        Args:
            dry_run (bool): The dry run parameter.
            extra_suspend (tuple): The extra suspend parameter.
            as_json (bool): The as json parameter.
        """
        _require_feature(Feature.GAMING_MODE)
        report = GameMode(extra_suspend=tuple(extra_suspend),
                          dry_run=dry_run).start()
        if as_json:
            click.echo(_json.dumps(report.to_dict(), indent=2))
            return
        click.echo(report.message or ("OK" if report.ok else "Failed"))
        for error in report.errors:
            click.echo(f"  ! {error}", err=True)
        if not report.ok:
            sys.exit(1)

    @boost.command("stop")
    @click.option("--json", "as_json", is_flag=True)
    def boost_stop(as_json: bool) -> None:
        """Restore the pre-boost power plan and resume paused apps.

        Manages boost stop operations and coordinates related state changes for the component.

        Args:
            as_json (bool): The as json parameter.
        """
        report = GameMode().stop()
        if as_json:
            click.echo(_json.dumps(report.to_dict(), indent=2))
            return
        click.echo(report.message)

    @main.command()
    @click.option("--json", "as_json", is_flag=True, help="Machine-readable diagnostic JSON report.")
    @click.option("-v", "--verbose", is_flag=True, help="Verbose itemized diagnostic logs.")
    def debug(as_json: bool, verbose: bool) -> None:
        """Debug.

        Manages debug operations and coordinates related state changes for the component.

        Args:
            as_json (bool): The as json parameter.
            verbose (bool): The verbose parameter.
        """
        from cortex_unified.debug.runner import DiagnosticRunner
        runner = DiagnosticRunner(verbose=verbose)
        report = runner.run_all()
        if as_json:
            click.echo(_json.dumps(report.to_dict(), indent=2))
        if not report.is_production_ready:
            sys.exit(1)

    @main.command()
    @click.option("--min-rss-mb", type=int, default=50, show_default=True,
                  help="Skip processes smaller than this.")
    @click.option("--apply", is_flag=True,
                  help="Actually trim (default: dry run).")
    @click.option("--stats-only", is_flag=True, help="Just show memory stats.")
    @click.option("--json", "as_json", is_flag=True)
    def memory(min_rss_mb: int, apply: bool, stats_only: bool,
               as_json: bool) -> None:
        """Memory.

        Manages memory operations and coordinates related state changes for the component.

        Args:
            min_rss_mb (int): The min rss mb parameter.
            apply (bool): The apply parameter.
            stats_only (bool): The stats only parameter.
            as_json (bool): The as json parameter.
        """
        if stats_only:
            stats = memory_stats()
            click.echo(_json.dumps(stats, indent=2) if as_json
                       else _fmt_memory_stats(stats))
            return
        _require_feature(Feature.MEMORY_OPTIMIZER)
        result = optimize(min_rss_mb=min_rss_mb, dry_run=not apply)
        if as_json:
            click.echo(_json.dumps(result.to_dict(), indent=2))
            return
        click.echo(result.message)

else:  # pragma: no cover

    def main() -> None:
        """Main.

        Manages main operations and coordinates related state changes for the component.
        """
        raise SystemExit("The 'click' package is required for the Cortex CLI. Install it with: pip install click")


if __name__ == "__main__":  # pragma: no cover
    main()
