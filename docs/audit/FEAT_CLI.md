# CLI Audit — Cortex_Cleaner

> Read-only audit of real argparse/click definitions. No code changes.

Entry points (`pyproject.toml` `[project.scripts]`): `cortex` → `engine/cli.py:main`, `cortex-cleaner`/`cortex-workstation` → `cli/cli.py:main`, `cortex-gui` → `ui/premium/app.py:main`, `cortex-workstation-gui`/`cortex-cleaner-gui` → `ui/launcher.py:main`, `cortex-debug` → `debug/runner.py:main`.

## legacy `cortex-cleaner` / `cortex-workstation` (`src/cortex_unified/cli/cli.py`)

Group: `main` — tagline only, plus `--version` (`cli.py:66`).

- `clean-empty [PATH] --dry-run` : preview only, default when no action given (`cli.py:73`)
- `clean-empty --delete` : permanently delete empty files/dirs (`cli.py:74`)
- `clean-empty --trash` : move empties to recycle bin (`cli.py:75`)
- `clean-empty --pattern` (multiple) : only globs matching pattern (`cli.py:76`)
- `clean-empty --older-than N` : only files older than N days (`cli.py:77`)
- `clean-empty --exclude-pattern` (multiple) : skip matching paths (`cli.py:78`)
- `clean-empty --config PATH` : load config file (`cli.py:79`)
- `clean-empty --no-config` : ignore all config files (`cli.py:80`)
- `clean-empty --yes` : skip confirmation (`cli.py:81`)
- `clean-empty --verbose / --quiet / --log-file / --json-log` : logging control (`cli.py:82-85`)
- `clean-empty --threads N` : scan thread count, 0=CPU count (`cli.py:86`)
- `clean-empty --cpu-priority low|normal|high / --io-priority low|normal|high` : throttle scan (`cli.py:87-88`)
- `clean-empty --checkpoint-interval N / --resume-from FILE` : resumable scan (`cli.py:89-90`)
- `find-large-files [PATH] --min-size MB` (def 100) : list files ≥ size, biggest first (`cli.py:264`)
- `find-large-files --pattern / --exclude-pattern` (multiple) : include/exclude globs (`cli.py:265-266`)
- `find-large-files --config / --no-config / --verbose / --log-file / --json-log / --threads / --export FILE` : config, log, threads, JSON export (`cli.py:267-273`)
- `find-duplicates [PATH] --strategy keep_newest|keep_oldest|keep_largest|keep_smallest` : auto-select victim per group (`cli.py:354`)
- `find-duplicates --hash-algorithm md5|sha1|sha256` (def md5) : content hash (`cli.py:356`)
- `find-duplicates --preview` : list only; `--delete` : recycle victims after confirm (`cli.py:358-359`)
- `find-duplicates --pattern / --exclude-pattern / --config / --no-config / --yes / --verbose / --log-file / --json-log / --threads / --export` : filters + JSON export (`cli.py:360-369`)
- `clean-temp --dry-run` (def True) / `--delete` / `--trash` : preview vs act (`cli.py:489-491`)
- `clean-temp --min-age N` (def 1) : only temp files older than N days (`cli.py:492`)
- `clean-temp --exclude-pattern / --config / --no-config / --yes / --verbose / --log-file / --json-log` : filters + logging (`cli.py:493-499`)
- `analyze-disk [PATH] --analyze` : run disk-usage analysis (`cli.py:607`)
- `analyze-disk --export-json / --export-treemap / --export-sunburst / --export-dashboard FILE` : JSON + HTML/PNG/SVG visualizations (`cli.py:608-611`)
- `analyze-disk --max-depth N` (def 3) : tree depth for visualizations (`cli.py:612`)
- `analyze-disk --threads / --cpu-priority / --io-priority / --memory-limit MB / --checkpoint-interval / --resume-from` : perf + resume (`cli.py:613-618`)
- `analyze-disk --config / --no-config / --verbose / --log-file / --json-log` : config + logging (`cli.py:619-623`)
- `list-startup-items` (no flags) : list startup items + enabled status (`cli.py:823`)
- `analyze-processes --export FILE` : JSON dump of process+service listing (`cli.py:852`)
- `docker-cleanup --dry-run` (def True) / `--clean` : preview vs act (`cli.py:894,895`)
- `docker-cleanup --images / --containers / --volumes / --networks / --all` : resource scope (default all) (`cli.py:896-900`)
- `docker-cleanup --config / --no-config / --yes / --verbose / --log-file / --json-log / --export` : config + JSON export (`cli.py:901-907`)
- `package-cleanup --pip / --npm / --yarn / --conda / --system / --all` : manager scope (`cli.py:1050-1055`)
- `package-cleanup --orphaned` : find unneeded packages (`cli.py:1056`)
- `package-cleanup --keep-recent-days N` (def 7) : preserve recent cache (`cli.py:1057`)
- `package-cleanup --dry-run` (def True) / `--clean` : preview vs act (`cli.py:1058-1059`)
- `package-cleanup --config / --no-config / --yes / --verbose / --log-file / --json-log / --export` : config + export (`cli.py:1060-1066`)
- `heuristics-scan [PATH] --confidence-threshold F` (def 0.7) : leftover certainty cutoff (`cli.py:1202`)
- `heuristics-scan --scan-registry` : include registry orphans (Windows) (`cli.py:1203`)
- `heuristics-scan --ml-patterns` (def on) : ML pattern pass (`cli.py:1204`)
- `heuristics-scan --dry-run` (def True) / `--clean` : preview vs act (`cli.py:1205-1206`)
- `heuristics-scan --config / --no-config / --yes / --verbose / --log-file / --json-log / --export` : config + export (`cli.py:1207-1213`)
- `secure-delete FILES... --shred` : without it only previews; with it overwrites (`cli.py:1362`)
- `secure-delete --passes N` (def 3) : overwrite passes (`cli.py:1363`)
- `secure-delete --verify` (def on) : verify after shred (`cli.py:1364`)
- `secure-delete --yes / --verbose / --log-file / --json-log` : confirm + logging (`cli.py:1365-1368`)
- `restore --restore MANIFEST` : replay manifest; bare = list backups (`cli.py:1426`)
- `restore --dry-run` (def True) : preview restore (`cli.py:1427`)
- `restore --yes / --verbose / --log-file / --json-log` : confirm + logging (`cli.py:1428-1431`)
- `generate-report --type text|html|json|csv` (def text) : report format (`cli.py:1493`)
- `generate-report --export FILE / --name NAME` : copy report / set name (`cli.py:1494-1495`)
- `generate-report --verbose / --log-file / --json-log` : logging (`cli.py:1496-1498`)
- `checkpoint list --config / --verbose` : list saved checkpoints (`cli.py:1571-1572`)
- `checkpoint delete CHECKPOINT_ID --verbose` : delete checkpoint by id (`cli.py:1601-1602`)
- `checkpoint cleanup --max-age N` (def 7) : purge checkpoints older than N days (`cli.py:1623`)
- `scan-enhanced [PATH] --checkpoint-id ID / --enable-checkpoints` : resume / enable checkpoints (`cli.py:1645-1646`)
- `scan-enhanced --enable-throttling / --cpu-limit F` (0.8) / `--memory-limit F` (0.85) : resource caps (`cli.py:1647-1649`)
- `scan-enhanced --dry-run / --delete / --trash / --pattern / --older-than / --exclude-pattern / --config / --no-config / --yes / --verbose / --quiet / --log-file / --json-log / --threads` : same semantics as clean-empty (`cli.py:1650-1663`)
- `scan-broken-links [PATH] --scan-symlinks` (on) / `--scan-shortcuts` (on) / `--scan-registry` (off) : link classes to scan (`cli.py:1851-1853`)
- `scan-broken-links --repair` : attempt repair of confident links (`cli.py:1854`)
- `scan-broken-links --backup` (on) : backup before repair (`cli.py:1855`)
- `scan-broken-links --confidence-threshold F` (0.7) : repair cutoff (`cli.py:1856`)
- `scan-broken-links --export FILE / --verbose|-v` : JSON export + verbose (`cli.py:1857-1858`)
- `clean-shaders --min-age-days N` (def 0) : stale DirectX/vendor shader cutoff (`cli.py:2004`)
- `clean-shaders --dry-run` : audit only, no delete (`cli.py:2005`)
- `clean-ai --dry-run` : list Copilot/Recall/WAL artifacts only (`cli.py:2022`)
- `trim-ssd [DRIVE]` (def C) : ReTrim/Optimize-Volume on drive (`cli.py:2037`)
- `vss-health` (no flags) : list VSS writers + healthy/failed counts (`cli.py:2049`)
- `verify-checksums MANIFEST_FILE` : verify .sha256/.md5/.sfv manifest (`cli.py:2062`)

## modern `cortex` engine (`src/cortex_unified/engine/cli.py`)

- `cortex scan --json` : machine-readable reclaim report (`engine/cli.py:145`)
- `cortex scan --all` : include opt-in categories (`engine/cli.py:146`)
- `cortex scan --max-risk low|medium|high` (def medium) : risk ceiling (`engine/cli.py:147`)
- `cortex clean --apply` : actually delete (default dry-run) (`engine/cli.py:176`)
- `cortex clean --method recycle|delete` (def recycle) : deletion method (`engine/cli.py:177`)
- `cortex clean --all / --max-risk` : same scope as scan (`engine/cli.py:178-179`)
- `cortex duplicates PATH... --json` : hash dedup across paths (`engine/cli.py:211-212`)
- `cortex large PATH --min-mb F` (100.0) `--limit N` (50) : top-N large files (`engine/cli.py:229-230`)
- `cortex empty PATH` (no flags) : list empty files+dirs (`engine/cli.py:238`)
- `cortex shred TARGET --apply` : actually shred (default preview) (`engine/cli.py:247`)
- `cortex shred --passes N` (3) / `--force-flash` : passes; allow SSD overwrite (`engine/cli.py:248-249`)
- `cortex leftovers scan APP_NAME --json` : read-only residual scan (`engine/cli.py:277-278`)
- `cortex leftovers orphans --json` : unclaimed Program Files folders (`engine/cli.py:289`)
- `cortex leftovers clean APP_NAME --apply` : recycle (default dry-run) (`engine/cli.py:300`)
- `cortex leftovers clean --min-level questionable|good|verygood` (good) : confidence floor (`engine/cli.py:302`)
- `cortex leftovers clean --restore-point` : system-restore checkpoint first (`engine/cli.py:306`)
- `cortex leftovers clean --json` : JSON outcome payload (`engine/cli.py:308`)
- `cortex license status --json` : tier/features/expiry (`engine/cli.py:371`)
- `cortex license activate --key KEY` (req) `--tier TIER` (pro) `--name/--email/--days/--json` : offline activate (`engine/cli.py:394-402`)
- `cortex license trial --json` : start once-per-machine Pro trial (`engine/cli.py:420`)
- `cortex license deactivate` (no flags) : drop to Free tier (`engine/cli.py:436`)
- `cortex boost status --json` : preview power-plan/suspend changes (`engine/cli.py:448`)
- `cortex boost start --dry-run / --extra-suspend NAME` (repeat) `/ --json` : apply gaming boost (`engine/cli.py:464-467`)
- `cortex boost stop --json` : restore plan + resume apps (`engine/cli.py:483`)
- `cortex debug --json / -v|--verbose` : production diagnostics, JSON or itemized (`engine/cli.py:493-494`)
- `cortex memory --min-rss-mb N` (50) : skip smaller processes (`engine/cli.py:506`)
- `cortex memory --apply` : actually trim (default dry-run) (`engine/cli.py:508`)
- `cortex memory --stats-only / --json` : stats view, optional JSON (`engine/cli.py:510-511`)

## `run_gui.py` switches

- No switches: `run_gui.py` takes no argv (no argparse/click); `main()` launches `cortex_unified.ui.premium.app:main` and returns exit code (`run_gui.py:26-55`).

## `system_tools` argparse CLIs

- `network_scan_cli.py --profile targeted|advanced` (targeted=2 rounds, advanced=3) (`network_scan_cli.py:21-22`)
- `network_scan_cli.py --scope NET` (repeatable) : bound scan to networks (`network_scan_cli.py:23`)
- `network_scan_cli.py --ports SPEC` : custom ports via `parse_custom_port_spec` (`network_scan_cli.py:24`)
- `network_scan_cli.py --output FILE` : atomic JSON write; exit 2 if cancelled, 1 on error (`network_scan_cli.py:25,64-70`)
- `sentinel_pro (secrets_scanner.py) --version` : print version (`secrets_scanner.py:2415`)
- `sentinel_pro scan [DIR] --verify` : live-verify creds vs APIs (`secrets_scanner.py:2420-2421`)
- `sentinel_pro scan --archives` : scan inside .zip/.tar (`secrets_scanner.py:2422`)
- `sentinel_pro scan --git-history` : scan commit history (`secrets_scanner.py:2423`)
- `sentinel_pro scan --diff` : only new findings vs baseline (`secrets_scanner.py:2424`)
- `sentinel_pro scan --report F.html / --json F.json / --csv F.csv / --sarif F.sarif` : exports (`secrets_scanner.py:2425-2428`)
- `sentinel_pro scan --severity LEVELS / --compliance FW` : filter CRITICAL..LOW / GDPR,HIPAA,PCI_DSS,SOC2 (`secrets_scanner.py:2429-2430`)
- `sentinel_pro scan --ignore|-i PAT` (repeat) : skip paths (`secrets_scanner.py:2431`)
- `sentinel_pro scan --workers N` (def min(cpu,16)) : parallelism (`secrets_scanner.py:2432`)
- `sentinel_pro scan --slack-webhook URL / --jira-url URL / --jira-project KEY / --github-repo OWNER/REPO` : notifications/issues (`secrets_scanner.py:2433-2436`)
- `sentinel_pro scan --ci / --fail-on SEV` (HIGH) : CI exit-2 gate (`secrets_scanner.py:2437-2438`)
- `sentinel_pro scan --quiet|-q / --no-terminal` : output control (`secrets_scanner.py:2439-2440`)
- `sentinel_pro baseline save|diff|clear [DIR]` : manage baselines (`secrets_scanner.py:2445-2447`)
- `sentinel_pro fp add FPRINT [--reason] / fp list / fp remove FPRINT` : false-positive suppressions (`secrets_scanner.py:2452-2454`)
- `sentinel_pro verify FILE` : live-verify creds from JSON export (`secrets_scanner.py:2458`)
- `sentinel_pro serve --port N` (8080) : web dashboard (`secrets_scanner.py:2462`)
- `sentinel_pro patterns` (no flags) : list detection patterns (`secrets_scanner.py:2465`)
- `cortex-debug --json / -v|--verbose` : JSON report / itemized logs; exit 1 if not production-ready (`debug/runner.py:805-819`)

## `scripts/*.py` purposes (no argparse CLIs — `__main__` runners only)

- `audit_all_page_functions.py` : deep functional+UI inspection of all 59 pages.
- `audit_imports.py` : static import health audit of `cortex_unified`.
- `audit_pages.py` : verify all registered pages load factory classes.
- `audit_system_tools.py` : inspect classes/functions across system tools.
- `build_exe.py` : PyInstaller build of `run_gui.py` into Windows exe.
- `check_all_structure_files.py` : file-by-file verification vs `structure.txt`.
- `check_hardcoded_paths.py` : detect hardcoded Windows paths.
- `check_lint_issues.py` : undefined-name/lint anomaly check.
- `deep_codebase_inspection.py` : exhaustive per-file codebase scan.
- `deep_inspect_placeholders.py` : placeholder/TODO/stub/mock sweep of `src/`.
- `generate_complete_features.py` : build master `COMPLETE_FEATURES_CHECKLIST.md`.
- `generate_feature_directory.py` : build `docs/FEATURE_DIRECTORY.md` (118 pages).
- `generate_program_checklist.py` : per-program-file verification checklist.
- `run_all_tests.py` : pytest runner with failure collection.
- `scan_codebase.py` : placeholder/TODO/mock detector.
- `stress_test_gui_all_actions.py` : interactive GUI action stress test.
- `test_all_pages.py` : offscreen instantiation check of all UI pages.
- `test_navigation.py` : UI navigation + theme test.
- `update_structure_txt.py` : regenerate repository `structure.txt`.
- `verify_modules.py` : quick functional check of core system modules.
- `verify_production_readiness.py` : production-readiness verification suite.
