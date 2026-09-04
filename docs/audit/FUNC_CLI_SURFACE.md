# CLI Surface Audit — Cortex_Cleaner

> Base: `D:\code\Main_projects\Cortex_Cleaner`. READ-ONLY audit (no code changed).
> Sources read: `src/cortex_unified/cli/cli.py` (2076 lines), `src/cortex_unified/engine/cli.py` (537 lines),
> `run_gui.py`, `src/cortex_unified/__main__.py`, `src/cortex_unified/system_tools/network_scan_cli.py`,
> `src/cortex_unified/system_tools/secrets_scanner.py` (head + tail), `src/cortex_unified/debug/runner.py` (tail),
> `src/cortex_unified/ui/premium/app.py` (main), `src/cortex_unified/ui/launcher.py`, `pyproject.toml` `[project.scripts]`,
> all 21 `scripts/*.py` (headers + `__main__` tails), `gen_inventory.py`; analyzers verified library-only via content search.

## legacy Click CLI (`cortex-cleaner` / `cortex-workstation` / `python -m cortex_unified`)
- `cortex-cleaner [--version]` (src/cortex_unified/cli/cli.py:66) : root Click group, version flag, dry-run-first legacy CLI.
- `cortex-cleaner clean-empty [PATH] --dry-run --delete --trash --pattern* --older-than N --exclude-pattern* --config --no-config --yes --verbose --quiet --log-file --json-log --threads --cpu-priority --io-priority --checkpoint-interval --resume-from` (src/cortex_unified/cli/cli.py:92) : find/remove empty files+folders, dry-run default, resumable scan.
- `cortex-cleaner find-large-files [PATH] --min-size --pattern* --exclude-pattern* --config --no-config --verbose --log-file --json-log --threads --export` (src/cortex_unified/cli/cli.py:275) : list files over --min-size MB, biggest first, optional JSON export.
- `cortex-cleaner find-duplicates [PATH] --strategy --hash-algorithm --preview --delete --pattern* --exclude-pattern* --config --no-config --yes --verbose --log-file --json-log --threads --export` (src/cortex_unified/cli/cli.py:371) : content-hash duplicate groups with space-savings, optional strategy-based recycle.
- `cortex-cleaner clean-temp --dry-run --delete --trash --min-age --exclude-pattern* --config --no-config --yes --verbose --log-file --json-log` (src/cortex_unified/cli/cli.py:500) : purge stale system temp files older than --min-age days.
- `cortex-cleaner analyze-disk [PATH] --analyze --export-json --export-treemap --export-sunburst --export-dashboard --max-depth --threads --cpu-priority --io-priority --memory-limit --checkpoint-interval --resume-from --config --no-config --verbose --log-file --json-log` (src/cortex_unified/cli/cli.py:625) : disk-usage analysis with TreeMap/Sunburst/dashboard exports.
- `cortex-cleaner list-startup-items` (src/cortex_unified/cli/cli.py:824) : list system startup items with enabled/disabled status.
- `cortex-cleaner analyze-processes --export` (src/cortex_unified/cli/cli.py:853) : summarize running processes+services, optional JSON export.
- `cortex-cleaner docker-cleanup --dry-run --clean --images --containers --volumes --networks --all --config --no-config --yes --verbose --log-file --json-log --export` (src/cortex_unified/cli/cli.py:908) : dry-run-first cleanup of unused Docker resources with backup manifests.
- `cortex-cleaner package-cleanup --pip --npm --yarn --conda --system --all --orphaned --keep-recent-days --dry-run --clean --config --no-config --yes --verbose --log-file --json-log --export` (src/cortex_unified/cli/cli.py:1067) : clean pip/npm/yarn/conda/system caches and orphaned packages.
- `cortex-cleaner heuristics-scan [PATH] --confidence-threshold --scan-registry --ml-patterns --dry-run --clean --config --no-config --yes --verbose --log-file --json-log --export` (src/cortex_unified/cli/cli.py:1215) : ML/pattern leftover scan of orphaned app folders, installers, registry.
- `cortex-cleaner secure-delete FILES... --shred --passes --verify --yes --verbose --log-file --json-log` (src/cortex_unified/cli/cli.py:1370) : preview by default, optionally multi-pass secure shred with verification.
- `cortex-cleaner restore [--restore MANIFEST] --dry-run --yes --verbose --log-file --json-log` (src/cortex_unified/cli/cli.py:1432) : preview-restore a deletion manifest or list saved backup manifests.
- `cortex-cleaner generate-report --type --export --name --verbose --log-file --json-log` (src/cortex_unified/cli/cli.py:1499) : generate system report as text/html/json/csv.
- `cortex-cleaner checkpoint` (src/cortex_unified/cli/cli.py:1567) : parent group for scan-checkpoint management.
- `cortex-cleaner checkpoint list --config --verbose` (src/cortex_unified/cli/cli.py:1573) : list saved scan checkpoints with progress.
- `cortex-cleaner checkpoint delete CHECKPOINT_ID --verbose` (src/cortex_unified/cli/cli.py:1603) : delete one checkpoint by id.
- `cortex-cleaner checkpoint cleanup --max-age --verbose` (src/cortex_unified/cli/cli.py:1625) : delete checkpoints older than --max-age days.
- `cortex-cleaner scan-enhanced [PATH] --checkpoint-id --enable-checkpoints --enable-throttling --cpu-limit --memory-limit --dry-run --delete --trash --pattern* --older-than --exclude-pattern* --config --no-config --yes --verbose --quiet --log-file --json-log --threads` (src/cortex_unified/cli/cli.py:1665) : empty-file scan with checkpoints and CPU/memory throttling.
- `cortex-cleaner scan-broken-links [PATH] --scan-symlinks --scan-shortcuts --scan-registry --repair --backup --confidence-threshold --export --verbose/-v` (src/cortex_unified/cli/cli.py:1860) : find and optionally repair broken symlinks/shortcuts/registry refs.
- `cortex-cleaner clean-shaders --min-age-days --dry-run` (src/cortex_unified/cli/cli.py:2006) : audit/purge DirectX and GPU-vendor shader caches.
- `cortex-cleaner clean-ai --dry-run` (src/cortex_unified/cli/cli.py:2023) : audit/clean Win11 Copilot, Recall, SQLite WAL journals.
- `cortex-cleaner trim-ssd [DRIVE]` (src/cortex_unified/cli/cli.py:2038) : trigger SSD NVMe TRIM/ReTrim on a volume.
- `cortex-cleaner vss-health` (src/cortex_unified/cli/cli.py:2050) : inspect VSS writers and shadow-storage health.
- `cortex-cleaner verify-checksums MANIFEST_FILE` (src/cortex_unified/cli/cli.py:2063) : verify .sha256/.md5/.sfv manifest against disk.

## modern engine CLI (`cortex` — src/cortex_unified/engine/cli.py)
- `cortex [--version]` (src/cortex_unified/engine/cli.py:141) : root Click group, modern dry-run-first engine CLI.
- `cortex scan --json --all --max-risk` (src/cortex_unified/engine/cli.py:148) : report reclaimable space by category (dry, human or JSON).
- `cortex clean --apply --method --all --max-risk` (src/cortex_unified/engine/cli.py:180) : actually reclaim (recycle/delete), dry-run unless --apply.
- `cortex duplicates PATH... --json` (src/cortex_unified/engine/cli.py:213) : size-prefiltered dedup scan over one or more paths.
- `cortex large PATH --min-mb --limit` (src/cortex_unified/engine/cli.py:231) : top-N files over --min-mb megabytes.
- `cortex empty PATH` (src/cortex_unified/engine/cli.py:238) : count/list empty files and dirs under PATH.
- `cortex shred TARGET --apply --passes --force-flash` (src/cortex_unified/engine/cli.py:250) : storage-aware secure delete, refuses on flash unless forced.
- `cortex leftovers` (src/cortex_unified/engine/cli.py:273) : parent group for post-uninstall residual scans.
- `cortex leftovers scan APP_NAME --json` (src/cortex_unified/engine/cli.py:279) : read-only leftover scan for one app name.
- `cortex leftovers orphans --json` (src/cortex_unified/engine/cli.py:290) : list unclaimed Program Files orphan folders.
- `cortex leftovers clean APP_NAME --apply --min-level --restore-point --json` (src/cortex_unified/engine/cli.py:309) : recycle findings above confidence level with .reg backups.
- `cortex license` (src/cortex_unified/engine/cli.py:367) : parent group for license management.
- `cortex license status --json` (src/cortex_unified/engine/cli.py:372) : show tier, features, expiry (offline).
- `cortex license activate --key --tier --name --email --days --json` (src/cortex_unified/engine/cli.py:403) : bind key to machine, activate tier offline.
- `cortex license trial --json` (src/cortex_unified/engine/cli.py:421) : start once-per-machine Pro trial.
- `cortex license deactivate` (src/cortex_unified/engine/cli.py:436) : remove license, return to Free tier.
- `cortex boost` (src/cortex_unified/engine/cli.py:444) : parent group for gaming/session boosts (Premium).
- `cortex boost status --json` (src/cortex_unified/engine/cli.py:449) : preview power-plan/background-quieting changes.
- `cortex boost start --dry-run --extra-suspend* --json` (src/cortex_unified/engine/cli.py:468) : apply gaming boost (power plan + pause background).
- `cortex boost stop --json` (src/cortex_unified/engine/cli.py:484) : restore power plan, resume paused apps.
- `cortex debug --json -v/--verbose` (src/cortex_unified/engine/cli.py:495) : run system+codebase production diagnostics.
- `cortex memory --min-rss-mb --apply --stats-only --json` (src/cortex_unified/engine/cli.py:512) : memory stats + working-set trim, dry-run default.

## installed console scripts + module/GUI launchers (pyproject.toml:65-72)
- `cortex` (pyproject.toml:66 → src/cortex_unified/engine/cli.py:141) : modern engine CLI entry.
- `cortex-gui` (pyproject.toml:67 → src/cortex_unified/ui/premium/app.py:263) : premium GUI; `--debug` flag or `CORTEX_DEBUG=1` env for verbose logging.
- `cortex-workstation` (pyproject.toml:68 → src/cortex_unified/cli/cli.py:68) : legacy CLI alias.
- `cortex-workstation-gui` (pyproject.toml:69 → src/cortex_unified/ui/launcher.py) : legacy multi-tab GUI launcher.
- `cortex-cleaner` (pyproject.toml:70 → src/cortex_unified/cli/cli.py:68) : legacy CLI primary name.
- `cortex-cleaner-gui` (pyproject.toml:71 → src/cortex_unified/ui/launcher.py) : legacy GUI alias.
- `cortex-debug` (pyproject.toml:72 → src/cortex_unified/debug/runner.py:800) : production diagnostics runner CLI.
- `python -m cortex_unified` (src/cortex_unified/__main__.py) : delegates to legacy Click CLI `cli:main`, preserves exit code.
- `python run_gui.py` (run_gui.py:26, run_gui.py:54) : source-checkout premium GUI launcher, no CLI flags, exit-code boundary.
- `python -m cortex_unified.ui.launcher` (src/cortex_unified/ui/launcher.py) : legacy GUI main, no CLI flags.

## system_tools standalone entries (argparse `main()` + `__main__`)
- `python -m cortex_unified.system_tools.network_scan_cli --profile --scope* --ports --output` (src/cortex_unified/system_tools/network_scan_cli.py:50, parser:17, guard:73) : bounded noninteractive private-LAN inventory scan for scheduling, atomic JSON output.
- `sentinel_pro scan [DIRECTORY] --verify --archives --git-history --diff --report --json --csv --sarif --severity --compliance --ignore/-i* --workers --slack-webhook --jira-url --jira-project --github-repo --ci --fail-on --quiet/-q --no-terminal` (src/cortex_unified/system_tools/secrets_scanner.py:2470, parser:2408, guard:2497) : filesystem secrets scan with optional live credential verification.
- `sentinel_pro baseline save|diff|clear [DIRECTORY]` (src/cortex_unified/system_tools/secrets_scanner.py:2445) : save/diff/clear scan baselines for delta reporting.
- `sentinel_pro fp add FINGERPRINT [--reason] | fp list | fp remove FINGERPRINT` (src/cortex_unified/system_tools/secrets_scanner.py:2452) : manage false-positive suppression database.
- `sentinel_pro verify FILE` (src/cortex_unified/system_tools/secrets_scanner.py:2458) : live-verify credentials from a `--json` findings file.
- `sentinel_pro serve --port` (src/cortex_unified/system_tools/secrets_scanner.py:2462) : start web dashboard (default port 8080).
- `sentinel_pro patterns` (src/cortex_unified/system_tools/secrets_scanner.py:2465) : list all 90+ detection patterns.
- NOTE: all other `src/cortex_unified/system_tools/*.py` (~130 files) expose NO `main()`/argparse/`__main__`/Click entry — library-only, invoked via CLIs/GUI.

## analyzers `__main__` demos
- (none) : all 30 `src/cortex_unified/analyzers/*.py` files verified with zero `__main__`/argparse/Click matches — library-only, surfaced via `cortex-cleaner` and `cortex` commands above.

## scripts/*.py entry points (run from repo root)
- `python scripts/audit_all_page_functions.py` (scripts/audit_all_page_functions.py:88) : offscreen audit of all 59 pages' buttons/workers/tables, no flags.
- `python scripts/audit_imports.py` (scripts/audit_imports.py) : AST import-health audit of `src/cortex_unified`, runs on import, no flags/guard.
- `python scripts/audit_pages.py` (scripts/audit_pages.py) : verify all registered pages load factory classes, runs on import, no flags/guard.
- `python scripts/audit_system_tools.py` (scripts/audit_system_tools.py) : import every system_tool, report classes/funcs, runs on import, no flags/guard.
- `python scripts/build_exe.py` (scripts/build_exe.py:59) : PyInstaller build of `run_gui.py` into `dist/CortexCleaner`, no flags.
- `python scripts/check_all_structure_files.py` (scripts/check_all_structure_files.py:102, guard:167) : exhaustive per-file verification vs `structure.txt`, writes `ONE_BY_ONE_VERIFICATION_REPORT.md`.
- `python scripts/check_hardcoded_paths.py` (scripts/check_hardcoded_paths.py:28) : report hardcoded `C:` paths across `src/`, no flags.
- `python scripts/check_lint_issues.py` (scripts/check_lint_issues.py) : pyflakes-based undefined-name/lint check, runs on import, no flags/guard.
- `python scripts/deep_codebase_inspection.py` (scripts/deep_codebase_inspection.py:95, guard:164) : scan for TODOs/stubs/bare-excepts/paths/docstrings, writes JSON report.
- `python scripts/deep_inspect_placeholders.py` (scripts/deep_inspect_placeholders.py) : placeholder/TODO/stub grep over `src/`, runs on import, no flags/guard.
- `python scripts/generate_complete_features.py` (scripts/generate_complete_features.py) : regenerate `COMPLETE_FEATURES_CHECKLIST.md`, runs on import.
- `python scripts/generate_feature_directory.py` (scripts/generate_feature_directory.py) : regenerate `docs/FEATURE_DIRECTORY.md`, runs on import.
- `python scripts/generate_program_checklist.py` (scripts/generate_program_checklist.py) : regenerate program-file verification checklist, runs on import.
- `python scripts/run_all_tests.py` (scripts/run_all_tests.py) : run full pytest suite with failure collector, runs on import.
- `python scripts/scan_codebase.py` (scripts/scan_codebase.py) : placeholder/mock/hardcoded-path pattern scan, runs on import.
- `python scripts/stress_test_gui_all_actions.py` (scripts/stress_test_gui_all_actions.py:48, guard:209) : headless click-through of all safe GUI actions on all pages.
- `python scripts/test_all_pages.py` (scripts/test_all_pages.py) : offscreen instantiate every UI page, runs on import.
- `python scripts/test_navigation.py` (scripts/test_navigation.py) : offscreen page-selection + theme test, runs on import.
- `python scripts/update_structure_txt.py` (scripts/update_structure_txt.py:58, guard:75) : regenerate repo `structure.txt` tree.
- `python scripts/verify_modules.py` (scripts/verify_modules.py) : live functional check of core tools (registry/uninstaller/telemetry), runs on import.
- `python scripts/verify_production_readiness.py [--json] [-v/--verbose]` (scripts/verify_production_readiness.py:25 → src/cortex_unified/debug/runner.py:800) : thin wrapper delegating to diagnostics `main()`.
- `python gen_inventory.py` (gen_inventory.py) : AST ground-truth pass writing `docs/FUNCTION_INVENTORY.md`, `main()` + `__main__` guard.

## diagnostics runner
- `cortex-debug [--json] [-v/--verbose]` / `cortex debug [--json] [-v/--verbose]` (src/cortex_unified/debug/runner.py:800, parser:802, guard:824) : full production diagnostics (icons, tools, analyzers, engine, caches, UI pages, licensing); exit 1 when not production-ready.
