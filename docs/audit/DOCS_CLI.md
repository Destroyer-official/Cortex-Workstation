# Purpose documentation — CLI + selected system_tools

Base: `D:\code\Main_projects\Cortex_Cleaner`. Read-only audit; no code changed.
Each entry: name, signature, file:line, WHAT it does + inputs/outputs, side effects.

---
## src/cortex_unified/cli/cli.py

### `_has_registry_cleaner() -> bool` (L42)
Lazily probes whether `cortex_unified.system_tools.registry_cleaner.RegistryCleaner` imports.
Input: none. Output: cached bool in `_HAS_REGISTRY_CLEANER`.
Side effects: none (import probe only; Windows-only module may fail on non-Windows).

### `__getattr__(name: str)` (L56)
PEP 562 module hook preserving the historical `HAS_REGISTRY_CLEANER` flag.
Input: attribute name. Output: probe result, else raises AttributeError.
Side effects: none beyond the lazy probe above.

### `main()` (L68)
Click group root (`cortex-cleaner`) plus `--version`. Takes no args, returns nothing; only groups subcommands.
Side effects: none.

### `clean_empty(dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, cpu_priority, io_priority, checkpoint_interval, resume_from, path)` (L92)
Finds and removes empty files/dirs under PATH via `Scanner` + `Deleter`. Dry-run by default; `--delete`/`--trash` act after confirm (skipped by `--yes`). Writes manifest via `Deleter.generate_manifest()`.
Side effects: filesystem deletes/trash moves when acting; log/manifest files; process-priority change via ResourceThrottler; checkpoint file read.

### `find_large_files(min_size, pattern, exclude_pattern, config, no_config, verbose, log_file, json_log, threads, export, path)` (L275)
Lists files over `--min-size` MB biggest-first via `LargeFileFinder`; optionally writes JSON export.
Inputs: path + filters. Output: log lines only.
Side effects: filesystem read scan; optional export file write. No deletes, no registry, no network.

### `find_duplicates(strategy, hash_algorithm, preview, delete, pattern, exclude_pattern, config, no_config, yes, verbose, log_file, json_log, threads, export, path)` (L371)
Content-hash duplicate finder (`DuplicateFinder`); reports groups + reclaimable bytes, optional JSON export, optional `--delete` of auto-selected copies (recycle bin) after confirm.
Side effects: heavy filesystem reads/hashing; trash moves only with `--delete`. No registry/network.

### `clean_temp(dry_run, delete, trash, min_age, exclude_pattern, config, no_config, yes, verbose, log_file, json_log)` (L500)
Scans system temp locations via `TempCleaner(min_age_days, exclude_patterns)`, groups by location, dry-runs by default; `--delete`/`--trash` cleans after confirm.
Side effects: filesystem deletes/trash of temp files when acting. No registry/network.

### `analyze_disk(analyze, export_json, export_treemap, export_sunburst, export_dashboard, max_depth, threads, cpu_priority, io_priority, memory_limit, checkpoint_interval, resume_from, config, no_config, verbose, log_file, json_log, path)` (L625)
Disk-usage analysis via `DiskAnalyzer` (volume stats, file-type breakdown, largest dirs) with resource throttling and resumable checkpoints; exports JSON/TreeMap/Sunburst/Dashboard files.
Side effects: filesystem reads + export file writes; process-priority change; checkpoint read. No deletes.

### `list_startup_items()` (L824)
Lists autostart entries via `StartupManager.list_startup_items()` with enabled/disabled status and location; prints stats.
Side effects: registry + startup-folder reads (Windows). No writes.

### `analyze_processes(export)` (L853)
Summarizes running processes/services via `ProcessAnalyzer`; prints totals; `--export` writes JSON.
Side effects: process/service enumeration reads (psutil/WMI); optional export file write.

### `docker_cleanup(dry_run, clean, images, containers, volumes, networks, clean_all, config, no_config, yes, verbose, log_file, json_log, export)` (L908)
Scans unused Docker images/stopped containers/unused volumes/networks via `DockerCleaner`; dry-run default; `--clean` removes after confirm; optional JSON export.
Side effects: Docker daemon queries; container/image/volume/network deletion when cleaning. Needs Docker running. No registry.

### `package_cleanup(pip, npm, yarn, conda, system, clean_all, orphaned, keep_recent_days, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export)` (L1067)
Detects package managers via `PackageManagerCleaner`, cleans pip/npm/system caches, optionally lists orphaned packages; JSON export.
Side effects: subprocess calls to pip/npm/conda/system managers (cache purge); reads package DBs. May need admin for system managers.

### `heuristics_scan(confidence_threshold, scan_registry, ml_patterns, dry_run, clean, config, no_config, yes, verbose, log_file, json_log, export, path)` (L1215)
Heuristic leftover scan via `LeftoverDetector` (orphaned Program Files/AppData folders, installer files, optional registry orphans, ML patterns), filters by confidence, exports JSON, optionally deletes high-confidence items via `Deleter` after confirm.
Side effects: filesystem + registry reads; trash deletes only with `--clean`. Registry scan Windows-only.

### `secure_delete(shred, passes, verify, yes, verbose, log_file, json_log, files)` (L1370)
Preview by default; with `--shred` overwrites each file `--passes` times via `FileShredder` (with `--verify`) after confirm.
Side effects: destructive overwrite + deletion of named files when `--shred`. No registry/network.

### `restore(restore, dry_run, yes, verbose, log_file, json_log)` (L1432)
With `--restore MANIFEST` replays a deletion manifest via `RestoreManager` (preview while `--dry-run`); without it lists saved backup manifests.
Side effects: filesystem writes (restored files) when not dry-run. No registry/network.

### `generate_report(type, export, name, verbose, log_file, json_log)` (L1499)
Generates a text/html/json/csv system report via `ReportsGenerator` from platform/Python-version sample data; `--export` copies it elsewhere.
Side effects: report file writes. Read-only otherwise.

### `checkpoint()` (L1567)
Click group for checkpoint subcommands; no logic itself.
Side effects: none.

### `list_checkpoints(config, verbose)` (L1573)
Lists saved scan checkpoints (id, timestamp, path, progress) via `ScanManager.list_checkpoints()`.
Side effects: checkpoint-store reads only.

### `delete(checkpoint_id, verbose)` (L1603)
Deletes one checkpoint by id via `ScanManager.delete_checkpoint()`; exits 1 if missing.
Side effects: checkpoint file deletion.

### `cleanup(max_age, verbose)` (L1625)
Deletes checkpoints older than `--max-age` days via `ScanManager.cleanup_old_checkpoints()`.
Side effects: checkpoint file deletions.

### `scan_enhanced(checkpoint_id, enable_checkpoints, enable_throttling, cpu_limit, memory_limit, dry_run, delete, trash, pattern, older_than, exclude_pattern, config, no_config, yes, verbose, quiet, log_file, json_log, threads, path)` (L1665)
Empty-file scan like `clean_empty` plus resumable checkpoints and CPU/memory throttling caps; on Ctrl-C saves a checkpoint when enabled.
Side effects: filesystem scan + deletes/trash when acting; checkpoint writes; throttler priority/limit changes; manifest write.

### `scan_broken_links(scan_symlinks, scan_shortcuts, scan_registry, repair, backup, confidence_threshold, export, verbose, path)` (L1860)
Scans broken symlinks/shortcuts/registry refs via `BrokenLinkDetector`, prints categorized counts, optionally repairs high-confidence links, optionally exports JSON.
Side effects: filesystem + registry reads; subprocess/COM reads for shortcuts; filesystem/registry writes only with `--repair`. Registry/shortcut scans Windows-gated.

### `clean_shaders_cmd(min_age_days: int, dry_run: bool)` (L2006)
Audits DirectX/GPU-vendor shader caches via `ShaderCacheCleaner.scan()`; prints per-vendor counts; cleans unless `--dry-run`.
Side effects: filesystem reads; shader-cache file deletions when acting. No registry/network/admin.

### `clean_ai_cmd(dry_run: bool)` (L2023)
Audits Windows 11 Copilot/Recall artifacts and SQLite WAL journals via `AiTelemetryCleaner.scan()`; cleans/checkpoints WAL unless `--dry-run`.
Side effects: filesystem reads; cache-file deletions + SQLite WAL checkpoint writes when acting.

### `trim_ssd_cmd(drive: str)` (L2038)
Triggers SSD TRIM/ReTrim on DRIVE via `SsdTrimOptimizer.retrim_volume()`; prints OK/ERROR.
Side effects: `defrag`/Optimize-Volume subprocess (storage ioctl). Needs admin. No registry/network.

### `vss_health_cmd()` (L2050)
Inspects VSS writers/shadow storage via `VssHealthAnalyzer.inspect_health()`; prints healthy/failed counts.
Side effects: `vssadmin`/WMI subprocess reads. No writes.

### `verify_checksums_cmd(manifest_file: str)` (L2063)
Verifies a `.sha256`/`.md5`/`.sfv` manifest via `ChecksumMatrix.verify_manifest()`; reports matched/mismatched/missing.
Side effects: filesystem hash reads only.

---
## src/cortex_unified/system_tools/leftover_cleaner.py

### `edit_distance(a: str, b: str, max_distance: int | None = None) -> int` (L64)
Bounded Levenshtein distance with early exit; pure string computation.
Inputs: two strings + optional cap. Output: int distance.
Side effects: none.

### `match_string_to_product(candidate: str, product_name: str) -> int` (L91)
Decides whether a folder/key name denotes a product: -1 no match, 0/1 exact/near, 2 containment, else small distance < 1/3 of shorter name; ≤4-char names never match.
Side effects: none (pure).

### `build_tokens(display_name: str, publisher: str = "") -> list[str]` (L138)
Tokenizes app display name + publisher into ≥4-char search tokens, stripping noise words and generic publishers.
Side effects: none.

### `confidence_level(raw: int) -> str` (L179)
Maps signed evidence score to Bad/Questionable/Good/VeryGood tiers.
Side effects: none.

### `SafetyPolicy.__post_init__() -> None` (L230)
Normalizes protected/own paths to case-folded absolute form.
Side effects: none (in-memory).

### `SafetyPolicy.build(extra_protected: Iterable[str] = ()) -> SafetyPolicy` (L238)
Classmethod building a policy protecting known-folder env roots plus extras and this module's own dir (self-protection).
Side effects: env-var reads only.

### `SafetyPolicy.is_prohibited(path: str | Path) -> bool` (L258)
True when path IS a protected root (children allowed). Returns bool.
Side effects: none.

### `_has_system_attribute(path: str) -> bool` (L272)
Checks Windows System file attribute (0x4); non-Windows always False.
Side effects: `os.stat` read only.

### `_is_reparse_point(path: str) -> bool` (L283)
Detects junctions/symlinks (reparse-point attr on Windows, `islink` elsewhere) so walks never descend them.
Side effects: stat read only.

### `InstalledApp.to_dict() -> dict` (L325)
Plain-dict view of an uninstall entry for journals/reports.
Side effects: none.

### `detect_installer_type(key_name: str, uninstall_string: str) -> str` (L335)
Classifies msi (GUID key) / inno (`_is1`) / nsis (uninst hints) / unknown.
Side effects: none.

### `read_installed_apps() -> list[InstalledApp]` (L347)
Enumerates all four Uninstall branches via winreg, dedupes by (name, key).
Side effects: registry reads (Windows). Empty list off-Windows.

### `_read_uninstall_entry(hive, hive_name: str, branch: str, subkey: str) -> InstalledApp | None` (L381)
Reads DisplayName/Publisher/Version/InstallLocation/DisplayIcon/UninstallString from one subkey (read-only 64-bit view); None when missing.
Side effects: registry reads only.

### `_clean_registry_path(value: str) -> str` (L421)
Strips quotes, icon-index suffixes (`,-1`), and trailing args from registry path values. Pure.
Side effects: none.

### `_tasks_root() -> Path` (L433)
Returns `%SystemRoot%\System32\Tasks` path. Pure env read.
Side effects: none.

### `LeftoverFinding.to_dict() -> dict` (L450)
Dict view of a finding (kind/path/size/score/level/reasons/app).
Side effects: none.

### `_add(f: LeftoverFinding, points: int, reason: str) -> None` (L460)
Adds signed evidence points and refreshes confidence level. Mutates finding in place.
Side effects: none (in-memory).

### `ExclusionsStore.__init__(path: str | Path | None = None)` (L481)
Opens user exclusion store (default `~/.cortex_cleaner/exclusions.json`) and loads it.
Side effects: file read.

### `ExclusionsStore._load() -> None` (L491)
Loads JSON list; corrupt/unreadable degrades to empty rather than raising.
Side effects: file read.

### `ExclusionsStore.save() -> bool` (L506)
Atomically persists exclusions (tmp + replace). Returns success bool.
Side effects: file write under `~/.cortex_cleaner/`.

### `ExclusionsStore._norm(path: str | Path) -> str` (L526)
Normalizes a path for matching (normcase+normpath). Pure.
Side effects: none.

### `ExclusionsStore.add(path: str | Path) -> bool` (L533)
Excludes a path + subtree, persisting immediately.
Side effects: exclusions-file write.

### `ExclusionsStore.discard(path: str | Path) -> bool` (L541)
Removes an exclusion, persisting immediately.
Side effects: exclusions-file write.

### `ExclusionsStore.paths() -> tuple[str, ...]` (L549)
Sorted tuple of excluded normalized paths.
Side effects: none.

### `ExclusionsStore.__len__() -> int` (L553)
Count of exclusions.
Side effects: none.

### `ExclusionsStore.is_excluded(path: str | Path) -> bool` (L557)
True when path equals or sits beneath an excluded entry.
Side effects: none.

### `LeftoverScanner.__init__(installed_apps, policy, exclusions, cancel_event)` (L605)
Stores policy/exclusions/cancel flag; inventory loads lazily.
Side effects: none.

### `LeftoverScanner._cancelled() -> bool` (L619)
True when the caller's cancel event is set.
Side effects: none.

### `LeftoverScanner._allowed(f: LeftoverFinding) -> bool` (L623)
True when finding is not under a user exclusion.
Side effects: none.

### `LeftoverScanner._ensure_inventory() -> None` (L629)
Lazily loads installed apps and builds live name/publisher/location sets.
Side effects: registry reads on first call.

### `LeftoverScanner._load_live_inventory() -> list[InstalledApp]` (L645)
Returns a copy of the installed-app list, loading if needed.
Side effects: registry reads on first call.

### `LeftoverScanner.scan_app(app: InstalledApp) -> list[LeftoverFinding]` (L653)
Full pipeline for one uninstalled app: filesystem, registry, shortcuts, COM, Inno log, services, tasks, then cross-check/disambiguation; drops Bad-level and excluded findings.
Side effects: filesystem + registry reads; COM shortcut reads.

### `LeftoverScanner.scan_orphans() -> list[LeftoverFinding]` (L685)
Finds Program-Files orphan folders no live app claims; keeps only Good/VeryGood.
Side effects: filesystem reads.

### `LeftoverScanner._disambiguate_similar(app, findings) -> None` (L715)
Penalizes weaker folder matches when several compete for the same product name (closest edit distance wins).
Side effects: none (mutates scores).

### `LeftoverScanner._sweep_roots() -> list[str]` (L745)
Sweep roots: both Program Files, ProgramData, AppData variants + LocalLow/VirtualStore/Programs; dedupes, drops missing.
Side effects: env reads + `isdir` checks.

### `LeftoverScanner._program_dir_roots() -> list[str]` (L773)
Program-directories subset used by orphan scan.
Side effects: `isdir` checks.

### `LeftoverScanner._sweep_filesystem(app, tokens, findings) -> None` (L785)
Walks every sweep root matching folder names to tokens.
Side effects: filesystem reads.

### `LeftoverScanner._walk_fs_level(app, tokens, directory, depth, findings) -> None` (L791)
Depth-limited (≤2) walk: skips blacklist/prohibited/reparse/system entries, scores token matches, always descends (vendor\App\Cache nesting).
Side effects: filesystem reads.

### `LeftoverScanner._score_folder_content(path, f, app) -> None` (L838)
Scores a matched folder by walking contents: size, empty/leaf/publisher-parent bonuses, executable/>100-files/vendor-name penalties.
Side effects: filesystem reads.

### `LeftoverScanner._score_orphan_folder(path, f) -> None` (L886)
Same content scoring for orphans, plus generic-name penalty.
Side effects: filesystem reads.

### `LeftoverScanner._claimed_by_live_app(path, name_lower) -> bool` (L919)
True when a live app's install location or normalized name claims the path.
Side effects: none (uses loaded inventory).

### `LeftoverScanner._folder_identity(name: str) -> str` (L931)
Strips trailing version numbers/decorations from a folder name. Pure.
Side effects: none.

### `LeftoverScanner._sweep_registry(app, tokens, findings) -> None` (L945)
Walks HKLM/HKCU SOFTWARE (+Wow6432Node, VirtualStore) read-only matching keys to tokens.
Side effects: registry reads (Windows; no-op without winreg).

### `LeftoverScanner._walk_reg_level(app, tokens, hive, hive_name, key, display_path, depth, findings) -> None` (L970)
Recursive registry walk (≤2 levels): scores name/token matches and explicit install-location pointers.
Side effects: registry reads.

### `LeftoverScanner._explicit_pointer(key, app) -> bool` (L1018)
True when an InstallDir/exe-path value under the key resolves into the app's install dir.
Side effects: registry reads.

### `LeftoverScanner.find_residual_uninstall_keys(app) -> list[str]` (L1040)
Lists Uninstall keys still present for the same product after removal.
Side effects: registry reads.

### `LeftoverScanner._same_product(a, b) -> bool` (L1068)
Same-product test: identical name, identical install location, or near-perfect name distance (static, pure).
Side effects: none.

### `LeftoverScanner._start_menu_dirs() -> list[str]` (L1085)
Existing user + common Start Menu dirs. Env reads + isdir checks.
Side effects: none (reads).

### `LeftoverScanner._sweep_shortcuts(app, findings) -> None` (L1096)
Flags `.lnk` files whose COM-resolved target lives in the dead install location.
Side effects: filesystem + COM (`WScript.Shell`) reads; needs pywin32.

### `LeftoverScanner._com_branches() -> list[tuple[str, str]]` (L1133)
CLSID/TypeLib branches searched for orphaned COM registrations.
Side effects: none.

### `LeftoverScanner._sweep_com(app, findings) -> None` (L1143)
Flags CLSID/TypeLib registrations whose server binary resolves into the dead install dir; skips `-0000-` OS GUIDs, caps at 5000 keys.
Side effects: registry reads.

### `LeftoverScanner._com_server_path(key, branch) -> str` (L1199)
Default value naming the COM server binary (InprocServer32/LocalServer32, TypeLib win32 nesting). Static.
Side effects: registry reads.

### `LeftoverScanner._sweep_inno_log(app, findings) -> None` (L1240)
Extracts absolute UTF-16LE paths from InnoSetup `unins000.dat` and flags survivors (cap 500).
Side effects: file read of the uninstall log.

### `LeftoverScanner._sweep_services(app, findings) -> None` (L1284)
Flags services whose ImagePath resolves into the dead install dir.
Side effects: registry reads.

### `LeftoverScanner._sweep_tasks(app, findings) -> None` (L1333)
Flags scheduled tasks whose `<Command>` in the Tasks XML points into the dead install dir.
Side effects: reads `%SystemRoot%\System32\Tasks` XML files.

### `LeftoverScanner._cross_check(app, findings) -> None` (L1365)
Penalizes folder findings claimed by a still-installed sibling (name or path overlap).
Side effects: none (score mutation).

### `CleanOutcome.to_dict() -> dict` (L1409)
Dict view of one cleanup outcome.
Side effects: none.

### `LeftoverCleaner.__init__(backup_root, policy)` (L1434)
Sets safety policy + session backup root (default `~/CortexCleanerBackups/leftovers`).
Side effects: none.

### `LeftoverCleaner.clean(findings, create_restore_point=False, exclusions=None, cancel_event=None) -> list[CleanOutcome]` (L1442)
Dispatches reviewed findings: registry/services via `reg`/`sc` (backed up), tasks via `schtasks` (XML backed up), files via Recycle Bin; honors protected paths + exclusions; always writes a JSON journal. Optional restore point.
Side effects: Recycle Bin moves; `reg delete`, `sc stop/delete`, `schtasks /delete` subprocesses; backup + journal file writes; optional System Restore point. Admin needed for HKLM/services.

### `LeftoverCleaner._restore_point() -> str` (L1493)
Best-effort restore checkpoint; returns honest status note, never raises (static).
Side effects: System Restore point creation attempt (WMI/subprocess).

### `LeftoverCleaner._recycle(f) -> CleanOutcome` (L1508)
Moves a file/folder/shortcut to Recycle Bin via send2trash; fails (never permanent-deletes) when unavailable.
Side effects: Recycle Bin move.

### `LeftoverCleaner._clean_registry(f, session) -> CleanOutcome` (L1527)
`reg export` backup then `reg delete` of one key (30 s timeouts, shell=False).
Side effects: `reg.exe` subprocesses; `.reg` backup write. Admin for HKLM.

### `LeftoverCleaner._clean_service(f, session) -> CleanOutcome` (L1566)
`.reg` backup, best-effort `sc stop`, then `sc delete` of a service.
Side effects: `reg`/`sc.exe` subprocesses; backup write. Admin required.

### `LeftoverCleaner._clean_task(f, session) -> CleanOutcome` (L1601)
Backs up task XML, best-effort `schtasks /end`, then `schtasks /delete /f`.
Side effects: `schtasks` subprocesses; XML backup write. Admin may be needed.

### `LeftoverCleaner._tasks_root_for(task_name) -> Path | None` (L1633)
On-disk Tasks XML path for a task name.
Side effects: none.

### `LeftoverCleaner._write_journal(session, journal, outcomes, restore_note="") -> None` (L1639)
Atomically writes session `journal.json` (timestamp, dispositions, ok/fail counts); logs, never raises.
Side effects: journal file write.

### `stamp_now() -> str` (L1664)
Current local time as `YYYY-MM-DDTHH:MM:SS`. Pure.
Side effects: none.

---
## src/cortex_unified/system_tools/secrets_scanner.py

Module-level `PATTERNS` (L248+) holds 90+ compiled `DetectionPattern`s (cloud keys, DB URLs, private keys, PII, infra config) — data, not functions.

### `Finding.to_dict() -> Dict[str, Any]` (L150)
`asdict` serialization of a finding.
Side effects: none.

### `Finding.severity_rank() -> int` (L155)
Numeric rank via SEVERITY_ORDER. Property, pure.
Side effects: none.

### `Finding.fingerprint() -> str` (L160)
16-hex sha256 of file|pattern|match for baseline/FP identity. Property, pure.
Side effects: none.

### `ScanStats.critical/high/medium/low() -> List[Finding]` (L185–L197)
Severity-filtered views of findings. Properties.
Side effects: none.

### `ScanStats.unique_files() -> int` (L201)
Count of distinct file paths with findings.
Side effects: none.

### `ScanStats.live_credentials() -> List[Finding]` (L205)
Findings verified live (`verified is True`).
Side effects: none.

### `ScanStats.to_dict() -> Dict[str, Any]` (L209)
Full serialization plus severity/live summary counts.
Side effects: none.

### `VerificationResult.status_emoji() -> str` (L232)
LIVE/REVOKED/UNVERIFIED display string. Property.
Side effects: none.

### `_p(pattern: str, flags: int = 0) -> re.Pattern` (L240)
Compiles a bytes case-insensitive regex for pattern table.
Side effects: none.

### `_shannon_entropy(data: bytes) -> float` (L892)
Shannon entropy of a byte string for secret-likeness. Pure.
Side effects: none.

### `_check_high_entropy(line: bytes, file_path: str) -> Optional[Finding]` (L907)
Flags ≥20-char base64-ish tokens with entropy ≥4.5 as generic MEDIUM secrets.
Side effects: none.

### `compute_confidence(file_path, match_preview, entropy, category, line_raw="") -> float` (L929)
Context-aware confidence: down-weights test/fixture paths, placeholders, comments, low-entropy; boosts high-entropy/crypto/PII.
Side effects: none.

### `_luhn_valid(s: str) -> bool` (L951)
Luhn checksum for credit-card candidates. Pure.
Side effects: none.

### `_redact(match: bytes) -> str` (L963)
Keeps first/last 4 chars with `***` middle (or `***` when short). Pure.
Side effects: none.

### `scan_file_bytes(data: bytes, file_path: str, patterns: List[DetectionPattern]) -> List[Finding]` (L972)
Scans byte lines against all patterns (Luhn-gated for cards), redacting previews and scoring confidence.
Side effects: none (in-memory).

### `scan_single_file(file_path: str, patterns: List[DetectionPattern]) -> Tuple[List[Finding], int]` (L1005)
Reads one file via mmap (skips empty, >32 MB, NUL-binary), scans bytes, stamps file size.
Side effects: filesystem reads. Permission errors yield empty.

### `walk_files(directory: str, ignores: List[str]) -> Tuple[List[str], int]` (L1034)
Walks a tree honoring `.sentinelignore` + skip dirs (`.git`, `node_modules`, …) and binary extensions; returns (files, skipped).
Side effects: filesystem reads.

### `compute_risk_score(findings: List[Finding]) -> int` (L1063)
Weighted 0–100 score (CRITICAL 30, HIGH 15, MEDIUM 5, LOW 1, +20 per live credential). Pure.
Side effects: none.

### `run_scan(directory, ignores=None, max_workers=8, severity_filter=None, quiet=False) -> ScanStats` (L1072)
Thread-pool scan of all walked files, sorted by severity, optionally severity-filtered; prints progress to stderr.
Side effects: filesystem reads; stderr progress. No network.

### `_scan_archive_member(data: bytes, virtual_path: str) -> List[Finding]` (L1123)
Scans one archive member's bytes (skips binary); virtual path is `archive::member`.
Side effects: none (in-memory).

### `scan_zip(archive_path: str) -> List[Finding]` (L1131)
Reads zip members (skips binary exts, >8 MB each, 200 MB total cap) and scans them.
Side effects: archive file reads.

### `scan_tar(archive_path: str) -> List[Finding]` (L1154)
Same for tar/tar.gz/bz2 with path-traversal guard (rejects absolute/`..` members).
Side effects: archive file reads.

### `scan_archives(directory: str, quiet=False) -> Tuple[List[Finding], int]` (L1184)
Walks a tree scanning every zip/tar archive; returns (findings, archive count).
Side effects: filesystem + archive reads.

### `scan_git_history(directory: str, max_commits=500, quiet=False) -> Tuple[List[Finding], int]` (L1202)
Runs `git log` + `git show --unified=0` per commit, scanning added lines; findings carry `git:<sha>:<file>` paths.
Side effects: `git` subprocesses (read-only). No network.

### `_http(url, headers, data=None, method="GET", timeout=8) -> Tuple[int, Any]` (L1250)
JSON-aware urllib helper returning (status, parsed body); HTTP errors → (code, {}).
Side effects: outbound HTTPS network.

### `_vr(finding_id, name, live, identity, blast, err=None) -> VerificationResult` (L1267)
Constructs a VerificationResult. Pure.
Side effects: none.

### `verify_aws(key_id, secret) -> VerificationResult` (L1273)
Live-checks AWS keys via SigV4-signed STS `GetCallerIdentity`; nested `sign(key, msg)` builds the HMAC chain.
Side effects: outbound HTTPS to `sts.amazonaws.com`. Network only.

### `verify_github(token) -> VerificationResult` (L1313)
GETs `api.github.com/user`; 200→live identity, 401→revoked.
Side effects: outbound HTTPS to GitHub API.

### `verify_stripe(key) -> VerificationResult` (L1325)
GETs Stripe `/v1/balance` with basic auth; reports balance context when live.
Side effects: outbound HTTPS to Stripe API.

### `verify_slack(token) -> VerificationResult` (L1340)
Calls Slack `auth.test`; live returns user@workspace identity.
Side effects: outbound HTTPS to Slack API.

### `verify_npm(token) -> VerificationResult` (L1351)
GETs npm `/-/whoami`; live returns username (supply-chain relevance).
Side effects: outbound HTTPS to npm registry.

### `verify_openai(key) -> VerificationResult` (L1363)
GETs OpenAI `/v1/models`; live lists sample models/billing exposure.
Side effects: outbound HTTPS to OpenAI API.

### `verify_all_findings(findings, quiet=False) -> Dict[str, VerificationResult]` (L1386)
Dispatches verifiable patterns through `VERIFIER_DISPATCH`, keyed by fingerprint; counts live creds.
Side effects: outbound network per verifiable finding (only when called with `--verify`).

### `_truncate_secret(value: str) -> str` (L1412)
Short 4+`***`+4 truncation for tickets/reports. Pure.
Side effects: none.

### `save_baseline(findings, directory) -> str` (L1422)
Writes `.sentinel-baseline.json` (fingerprints + truncated previews) into the scanned dir; returns path.
Side effects: baseline file write.

### `load_baseline(directory) -> Optional[Dict]` (L1434)
Loads the baseline JSON, or None when absent.
Side effects: file read.

### `compute_delta(findings, baseline) -> Tuple[List[Finding], int]` (L1442)
Splits findings into (new vs baseline) plus resolved count. Pure.
Side effects: none.

### `_fp_path(directory) -> str` (L1451)
Path of `.sentinel-fp.json` suppression DB. Pure.
Side effects: none.

### `load_fp_db(directory) -> Dict` (L1457)
Loads suppression DB or empty default.
Side effects: file read.

### `save_fp_db(db, directory)` (L1465)
Persists suppression DB.
Side effects: file write.

### `add_fp(fingerprint, directory, reason="")` (L1470)
Adds one suppression with timestamp + reason; prints confirmation.
Side effects: FP DB write; stdout.

### `apply_fp_filter(findings, directory) -> Tuple[List[Finding], int]` (L1477)
Drops suppressed fingerprints; returns (kept, suppressed_count). Reads DB.
Side effects: file read.

### `save_to_history(stats, live_count=0)` (L1491)
Appends a scan summary record under `~/.sentinel/history/<scan_id>.json`.
Side effects: history file write.

### `load_history(limit=20) -> List[Dict]` (L1506)
Loads newest history records (tolerates corrupt files).
Side effects: history-dir reads.

### `create_jira_ticket(finding, jira_url, jira_user, jira_token, project_key) -> Optional[str]` (L1522)
POSTs a Bug issue (summary/description/priority/labels) to Jira; returns issue key.
Side effects: outbound HTTPS to the Jira instance. Needs JIRA_USER/JIRA_TOKEN.

### `create_github_issue(finding, github_token, repo) -> Optional[str]` (L1558)
POSTs a labeled security issue to a GitHub repo; returns issue URL.
Side effects: outbound HTTPS to GitHub API. Needs GITHUB_TOKEN.

### `export_json(stats, path)` (L1591)
Dumps full scan dict to JSON file.
Side effects: file write.

### `export_csv(stats, path)` (L1596)
Writes per-finding CSV (severity/category/pattern/file/match/compliance/confidence/…).
Side effects: file write.

### `export_sarif(stats, path)` (L1609)
Writes SARIF 2.1.0 (rules + results) for GitHub/GitLab ingestion.
Side effects: file write.

### `send_slack(stats, webhook_url) -> bool` (L1639)
POSTs a risk-colored attachment summary to a Slack webhook; returns success.
Side effects: outbound HTTPS to webhook URL.

### `generate_html_report(stats, output_path)` (L1669)
Renders the self-contained Sentinel Pro HTML report (gauges, filters, finding cards, embedded findings/history JSON) to file.
Side effects: file write; reads history.

### `print_terminal_report(stats)` (L1977)
Prints rich (or plain fallback) terminal summary: risk panel, top-100 findings table, severity counts.
Side effects: stdout/stderr only.

### `DashboardHandler.log_message(format, *args)` (L2147)
Suppresses BaseHTTPRequestHandler logging. No-op.
Side effects: none.

### `DashboardHandler.do_GET()` (L2150)
Serves `/api/history` JSON or the dashboard HTML page.
Side effects: reads history; localhost HTTP response.

### `serve_dashboard(port=8080)` (L2166)
Starts a 127.0.0.1 HTTP dashboard server until Ctrl-C.
Side effects: localhost socket listen. No outbound network.

### `cmd_scan(args)` (L2178)
Orchestrates scan → archives → git history → FP filter → compliance/delta filters → optional live verify → history save → terminal/report/JSON/CSV/SARIF/Slack/Jira/GitHub outputs → CI exit codes (0 clean, 1 findings, 2 blocking, 3 bad dir).
Side effects: all of the above per flags (reads; writes reports; optional live API network; ticket creation).

### `cmd_baseline(args)` (L2313)
`save` (scan + fingerprint), `diff` (new/resolved vs baseline), or `clear` the baseline file.
Side effects: scan reads; baseline file write/delete.

### `cmd_fp(args)` (L2341)
`add`/`list`/`remove` false-positive suppressions in the CWD suppression DB.
Side effects: FP DB writes (add/remove); stdout.

### `cmd_verify(args)` (L2363)
Loads findings from a `--json` export and live-verifies them, printing live counts.
Side effects: outbound verification network; file read.

### `cmd_serve(args)` (L2383)
Starts the dashboard on the requested port. Returns 0.
Side effects: localhost HTTP listen.

### `cmd_patterns(args)` (L2389)
Lists all detection patterns (rich table or plain). Returns 0.
Side effects: stdout only.

### `build_parser()` (L2408)
Builds the argparse tree (`scan/baseline/fp/verify/serve/patterns` + options). Pure.
Side effects: none.

### `main() -> int` (L2470)
Dispatches subcommands; bare directory arg falls back to `scan`. Returns exit code.
Side effects: those of the chosen subcommand.

---
## src/cortex_unified/system_tools/network_inventory.py

### `_text(value: Any, limit=512) -> str` (L32)
Coerces to trimmed, length-capped string ("" for empty). Pure.
Side effects: none.

### `_json_safe(value: Any, depth=0) -> Any` (L39)
Recursively converts to JSON-safe primitives with depth/size caps. Pure.
Side effects: none.

### `InventoryService.key() -> str` (L68)
Stable dedup key `proto:port:name`. Property.
Side effects: none.

### `InventoryService.to_dict() -> dict` (L72)
Serializes service with JSON-safe details.
Side effects: none.

### `InventoryFinding.key() -> str` (L91)
Dedup key: code, falling back to title. Property.
Side effects: none.

### `InventoryFinding.to_dict() -> dict` (L95)
Serializes finding with JSON-safe details.
Side effects: none.

### `InventoryDevice.to_dict() -> dict` (L117)
Serializes device expanding services + findings.
Side effects: none.

### `DeviceMetadata.to_dict() -> dict` (L141)
Serializes user metadata (name/trust/tags/notes).
Side effects: none.

### `InventoryChange.to_dict() -> dict` (L164)
Serializes a change with JSON-sanitized previous/current.
Side effects: none.

### `InventoryChanges.to_dict() -> dict` (L183)
Serializes all seven change groups.
Side effects: none.

### `InventorySnapshot.to_dict() -> dict` (L211)
Serializes snapshot (devices, changes, gateway MAC, identity notice).
Side effects: none.

### `_normalize_mac(value: Any) -> str` (L223)
Lowercase colon MAC or "" when malformed. Pure.
Side effects: none.

### `_randomized_mac(mac: str) -> bool` (L231)
Detects locally-administered (privacy) MACs via OUI bit 0x02. Pure.
Side effects: none.

### `_identity(device: InventoryDevice) -> tuple[str, str]` (L241)
Best identity key (`id:` > stable `mac:` > `ip:`) plus high/low confidence. Pure.
Side effects: none.

### `_service(value: Any) -> InventoryService` (L254)
Coerces str/int/mapping/object into a validated service (port clamped 1–65535). Pure.
Side effects: none.

### `_finding(value: Any) -> InventoryFinding` (L297)
Coerces mapping/object into a validated finding (unknown severity → info). Pure.
Side effects: none.

### `_get(value: Any, name: str, default=None) -> Any` (L322)
Mapping- or attribute-style read with default. Pure.
Side effects: none.

### `normalize_device(value: Any) -> InventoryDevice` (L330)
Normalizes discovery objects/mappings into a validated observation: strict IP, normalized MAC, merged/deduped service + finding sets (caps enforced).
Side effects: none (raises ValueError on bad IP).

### `identity_key_for(value: Any) -> str` (L373)
Stable identity key for any device-like value (same rule as inventory). Pure.
Side effects: none.

### `NetworkInventory.__init__(path=None, retention=50)` (L381)
Opens/creates the SQLite store (default `~/.cortex_cleaner/netdata/network-inventory.sqlite3`, `:memory:` supported), clamps retention, migrates schema.
Side effects: dir + SQLite file creation/migration.

### `NetworkInventory.close() -> None` (L403)
Closes the in-memory connection (file DBs are per-use).
Side effects: connection close.

### `NetworkInventory.__enter__/__exit__` (L410/L414)
Context-manager passthrough to close().
Side effects: connection close on exit.

### `NetworkInventory._new_connection() -> sqlite3.Connection` (L418)
Opens a SQLite connection with Row factory, FK + busy-timeout pragmas.
Side effects: DB connection open.

### `NetworkInventory._connect() -> sqlite3.Connection` (L429)
Reuses the memory connection or opens a fresh file connection.
Side effects: possible connection open.

### `NetworkInventory._release(connection) -> None` (L435)
Closes file connections; keeps shared memory connection.
Side effects: connection close (file DBs).

### `NetworkInventory._migrate() -> None` (L440)
Creates/upgrades schema v0→v2 (snapshots, devices, observations, services, findings, metadata) in a transaction; refuses newer-than-supported schemas.
Side effects: SQLite DDL transaction.

### `NetworkInventory.record_snapshot(devices, observed_at=None, gateway_mac="") -> InventorySnapshot` (L558)
Thread-safe wrapper completing a point-in-time snapshot. Takes device observations + optional timestamp/gateway.
Side effects: SQLite write transaction.

### `NetworkInventory._record_snapshot(devices, observed_at, gateway_mac="") -> InventorySnapshot` (L568)
Validates/dedupes devices (4096 cap), diffs vs previous, inserts snapshot + observations atomically, enforces retention.
Side effects: SQLite write transaction.

### `NetworkInventory.update(devices, findings=()) -> InventoryChanges` (L629)
Merges IP-keyed extra findings into devices, records a snapshot, returns only the focused change groups (new/changed/services/findings/severity/disappeared/gateway).
Side effects: SQLite write transaction.

### `NetworkInventory._load_previous(connection) -> tuple` (L675)
Loads newest snapshot's observations/services/findings/gateway for diffing. Static.
Side effects: SQLite reads.

### `NetworkInventory._compare(current, previous, previous_gateway, gateway_mac) -> list[InventoryChange]` (L724)
Diffs current vs previous: new/disappeared devices, address/MAC changes, new services/findings, severity direction, gateway-MAC change (high severity); same-IP fallback is low confidence. Static.
Side effects: none.

### `NetworkInventory._store_device(connection, snapshot_id, timestamp, identity_key, confidence, device) -> None` (L848)
Upserts device/observation/service/finding rows for one snapshot. Static.
Side effects: SQLite writes (within caller transaction).

### `NetworkInventory._enforce_retention(connection) -> None` (L913)
Deletes snapshots beyond retention plus orphaned catalog rows.
Side effects: SQLite deletes.

### `NetworkInventory._metadata_identity(value) -> str` (L934)
Validates an `id:/mac:/ip:` key or derives one from a device. Static.
Side effects: none (raises on invalid).

### `NetworkInventory._metadata_values(custom_name, trust_state, tags, notes) -> tuple` (L949)
Validates name/trust (unknown/trusted/guest/blocked)/≤32 tags/notes. Static.
Side effects: none (raises on invalid).

### `NetworkInventory.set_metadata(identity, *, custom_name="", trust_state="unknown", tags=(), notes="") -> DeviceMetadata` (L971)
Atomically creates/replaces user-owned device metadata; returns the record.
Side effects: SQLite write transaction.

### `NetworkInventory.get_metadata(identity) -> DeviceMetadata | None` (L1008)
Fetches one device's metadata or None.
Side effects: SQLite read.

### `NetworkInventory.list_metadata() -> list[DeviceMetadata]` (L1022)
All metadata records ordered by identity key.
Side effects: SQLite read.

### `NetworkInventory._metadata_from_row(row) -> DeviceMetadata` (L1035)
Rebuilds metadata from a DB row, tolerating bad tag JSON. Static.
Side effects: none.

### `NetworkInventory.exposure_trends(limit=50) -> list[dict]` (L1055)
Bounded per-snapshot aggregates (device/service/finding counts + severity-weighted risk) newest-last.
Side effects: SQLite read.

### `NetworkInventory._csv_cell(value) -> str` (L1083)
Prefixes spreadsheet-formula cells (`=+-@`) with `'`. Static.
Side effects: none.

### `NetworkInventory._csv_value(value) -> str` (L1091)
Strips the formula-escape apostrophe on import. Static.
Side effects: none.

### `NetworkInventory.export_inventory_csv(path) -> int` (L1100)
Exports latest inventory + metadata as `cortex-network-inventory-v2` CSV (UTF-8-SIG, formula-escaped); returns row count.
Side effects: CSV file write; SQLite read.

### `NetworkInventory.import_inventory_csv(path, *, dry_run=True, overwrite=False) -> dict` (L1144)
Validates schema/columns/identities/duplicates (2 MiB + device caps), reports created/updated/conflicts; writes only when `dry_run=False` (single transaction, overwrite controls conflicts).
Side effects: CSV read; SQLite writes unless dry-run.

### `NetworkInventory.snapshot_count() -> int` (L1216)
Retained snapshot count.
Side effects: SQLite read.

### `NetworkInventory.device_lifetimes() -> list[dict]` (L1226)
First/last-seen + confidence per device for display/export.
Side effects: SQLite read.

### `_timestamp(value) -> str` (L1240)
Coerces None/str/datetime to UTC ISO-8601 `Z` timestamp (naive assumed UTC). Pure.
Side effects: none.

---
## src/cortex_unified/system_tools/windows_update_repair.py

### `DiagnosticReport.to_json() -> str` (L118)
Serializes the diagnostic report to indented JSON.
Side effects: none.

### `RepairResult.summary() -> str` (L133)
`Windows Update Repair: ok/total phases succeeded`. Pure.
Side effects: none.

### `WindowsUpdateRepair.__init__(create_restore_point=True, progress_callback=None, cancel_event=None, dry_run=False)` (L188)
Stores flags/callbacks, builds RestorePointManager + ComponentStoreCleaner, ensures `%TEMP%\CortexWURepair`.
Side effects: backup-dir creation.

### `WindowsUpdateRepair._run(cmd, timeout=120, shell=False) -> Tuple[int, str, str]` (L211)
Cancellation-checked subprocess runner; dry-run logs and returns 0 without executing.
Side effects: arbitrary child processes unless dry-run. Admin needed for most repairs.

### `WindowsUpdateRepair._run_ps(script, timeout=180)` (L231)
Runs a PowerShell command via `_run`. Same side effects as `_run`.

### `WindowsUpdateRepair._sc_query(name) -> str` (L237)
`sc query <service>` output ("" on failure).
Side effects: `sc.exe` subprocess (read-only).

### `WindowsUpdateRepair._service_status(name) -> str` (L244)
Parses STATE from `sc query` (e.g. RUNNING/STOPPED/UNKNOWN).
Side effects: `sc.exe` subprocess.

### `WindowsUpdateRepair._stop_service(name, retries=3) -> bool` (L254)
`net stop` with retries, verifying STOPPED state.
Side effects: service stop (needs admin).

### `WindowsUpdateRepair._start_service(name) -> bool` (L267)
`net start <service>`; True on rc 0.
Side effects: service start (needs admin).

### `WindowsUpdateRepair.preflight() -> DiagnosticReport` (L276)
Read-mostly diagnostics: OS version, WU service states, free disk, MS connectivity check, DISM CheckHealth, pending-reboot key, recent WU client events.
Side effects: `sc`/`Dism`/PowerShell subprocesses; one outbound HTTP probe (`msftconnecttest`); registry read. No mutations.

### `WindowsUpdateRepair._phase_stop_services() -> PhaseResult` (L354)
Stops wuauserv/bits/cryptsvc/appidsvc/WaaSMedicSvc when running; aborts on first failure.
Side effects: service stops (admin).

### `WindowsUpdateRepair._phase_clear_caches() -> PhaseResult` (L370)
Timestamp-renames SoftwareDistribution, catroot2, DeliveryOptimization and backs up BITS qmgr .dat files (reversible, not delete).
Side effects: filesystem renames under `%SystemRoot%` (admin). Skipped under dry-run.

### `WindowsUpdateRepair._phase_reset_registry_policies() -> PhaseResult` (L410)
`reg export` backups then `reg delete` of the four WindowsUpdate policy keys (HKCU/HKLM).
Side effects: `reg.exe` subprocesses; registry deletes + `.reg` backups (admin for HKLM).

### `WindowsUpdateRepair._phase_reset_security_descriptors() -> PhaseResult` (L437)
Resets BITS + wuauserv security descriptors via `sc sdset`.
Side effects: service ACL mutation (admin).

### `WindowsUpdateRepair._phase_reregister_dlls() -> PhaseResult` (L452)
`regsvr32 /s` for each present WU DLL in System32.
Side effects: COM registration writes (admin).

### `WindowsUpdateRepair._phase_reset_network() -> PhaseResult` (L467)
Winsock/WinHTTP proxy resets + DNS flush; strips telemetry domains from the hosts file (with backup) when present.
Side effects: `netsh`/`ipconfig` subprocesses (network stack reset, admin); hosts-file rewrite + backup.

### `WindowsUpdateRepair._phase_dism_repair() -> PhaseResult` (L493)
DISM ScanHealth, then RestoreHealth when needed (long timeouts).
Side effects: `Dism.exe` subprocess; component-store repair writes (admin, slow).

### `WindowsUpdateRepair._phase_sfc() -> PhaseResult` (L508)
Runs `sfc /scannow` (long timeout); returns truncated output.
Side effects: `sfc.exe` subprocess; system-file repairs (admin, slow).

### `WindowsUpdateRepair._phase_component_store() -> PhaseResult` (L517)
Analyzes the component store and runs cleanup when recommended.
Side effects: DISM/cleanup subprocesses; WinSxS mutation when cleaning (admin).

### `WindowsUpdateRepair._phase_start_services() -> PhaseResult` (L528)
Starts WU services and sets wuauserv/bits/DcomLaunch to auto.
Side effects: service start + `sc config` mutations (admin).

### `WindowsUpdateRepair._phase_verify() -> PhaseResult` (L544)
HTTPS reachability check to microsoft.com plus `wuauclt /detectnow` trigger.
Side effects: outbound HTTPS; WU detection subprocess.

### `WindowsUpdateRepair.repair_all(phases=None) -> RepairResult` (L564)
Creates a restore point, runs preflight, executes selected (default all 11) phases in order (aborts if stop_services/clear_caches fail), then postflight. Returns pre/post + cancel state.
Side effects: restore point + every selected phase's mutations; admin required.

### `WindowsUpdateRepair.repair_selective(phase_names) -> RepairResult` (L606)
Runs only the named phases (delegates to `repair_all`).
Side effects: those phases' mutations + restore point.

### `WindowsUpdateRepair.quick_reset() -> RepairResult` (L610)
Minimal subset: stop_services, clear_caches, reregister_dlls, reset_network, start_services, verify.
Side effects: that subset's mutations + restore point.

---
## src/cortex_unified/system_tools/startup_optimizer.py

### `StartupEntry.to_dict() -> dict` (L95)
`asdict` serialization of a startup entry.
Side effects: none.

### `_enumerate_registry() -> List[StartupEntry]` (L117)
Reads Run/RunOnce, Explorer hooks, Winlogon, Services, BHO keys from HKCU/HKLM into entries.
Side effects: registry reads (Windows; needs winreg).

### `_enumerate_startup_folders() -> List[StartupEntry]` (L157)
Lists files in per-user + common Startup folders under APPDATA/PROGRAMDATA.
Side effects: filesystem reads.

### `_enumerate_scheduled_tasks() -> List[StartupEntry]` (L183)
Parses `schtasks /Query /FO CSV /V`, keeping logon/boot-triggered tasks.
Side effects: `schtasks` subprocess (read-only).

### `_classify_entry(entry) -> StartupEntry` (L211)
Sniffs the target EXE/DLL's first 4 KB for GUI (USER32/GDI32), network (WININET/WS2_32/WINHTTP), service (ADVAPI32+OpenService) hints; mutates flags.
Side effects: binary file reads.

### `_config_path() -> Path` (L237)
`%LOCALAPPDATA%\Cortex\Cleaner\startup_delays.json`, creating dirs.
Side effects: directory creation.

### `StartupOptimizer.__init__(progress=None, cancel=None)` (L252)
Stores progress callback + cancel event.
Side effects: none.

### `StartupOptimizer.enumerate() -> List[StartupEntry]` (L258)
Merges all three enumerations, classifies each, overlays persisted delays, rates impact by target EXE size (>50 MB high, >10 MB medium).
Side effects: registry/filesystem/schtasks reads; delay-file read; EXE stat reads.

### `StartupOptimizer._load_delays() -> Dict[str, dict]` (L289)
Loads persisted delay map; corrupt/missing → {}.
Side effects: JSON file read.

### `StartupOptimizer._save_delays(delays) -> None` (L301)
Persists the delay map as JSON.
Side effects: delay-file write.

### `StartupOptimizer.set_delay(entry_id, delay_seconds, conditions=None) -> None` (L308)
Sets a 0–120 s clamped delay (+ launch conditions) for an entry.
Side effects: delay-file write.

### `StartupOptimizer.remove_delay(entry_id) -> None` (L316)
Removes an entry's delay.
Side effects: delay-file write.

### `StartupOptimizer.launch_delayed(entries=None) -> None` (L322)
Launches delayed entries sorted by delay: scales for battery (+25%) and heat (+40%), gates on CPU<5%/free RAM>1.2 GB, jitters network-bound launches, honors require_internet, spawns via `Popen(shell=True)`.
Side effects: sleeps; psutil sensor reads; socket probe to 8.8.8.8:53 when gated; child-process launches. No registry writes.

### `StartupOptimizer._jitter() -> float` (L387)
Uniform −1.5…+1.5 s jitter for network-bound launches. Pure-ish (random).
Side effects: none.

### `StartupOptimizer.backup() -> Path` (L394)
Copies the delay config to a timestamped `.bak` file; returns its path.
Side effects: backup file write.

### `StartupOptimizer.restore(backup: Path) -> None` (L402)
Restores the delay config from a backup file.
Side effects: config file overwrite.

---
## src/cortex_unified/system_tools/health_check.py

All checks are read-only and fast; failures degrade to `info`/`None`, never fake passes.

### `HealthCheck.to_dict() -> dict` (L39)
Serializes one check (id/title/severity/detail/action_page).
Side effects: none.

### `HealthReport.to_dict() -> dict` (L52)
Serializes checks + score + grade.
Side effects: none.

### `HealthChecker.run(progress=None) -> HealthReport` (L64)
Runs the six checks (disk, memory, SMART, boot, security, updates) with progress callbacks, isolating per-check exceptions, then scores.
Side effects: read-only diagnostics below; no writes.

### `HealthChecker._score(checks) -> tuple[int, str]` (L90)
Deducts 12 per warning / 30 per critical from 100, clamps, grades A (≥90)…F (<40). Static pure.
Side effects: none.

### `HealthChecker._check_disk_space() -> HealthCheck` (L113)
`shutil.disk_usage` on the system root: critical <10% free, warning <20%. Static.
Side effects: filesystem stat read.

### `HealthChecker._check_memory() -> HealthCheck` (L133)
psutil memory percent: warning ≥90%, else good; `info` when psutil missing. Static.
Side effects: process-memory read.

### `HealthChecker._check_disk_health() -> HealthCheck | None` (L150)
SMART via `DiskHealthMonitor`: critical when any disk unhealthy, `info` when unreadable (may need admin); None off-Windows. Static.
Side effects: SMART/WMI subprocess reads.

### `HealthChecker._check_boot() -> HealthCheck | None` (L172)
`BootPerformanceMonitor` latest boot: critical >150 s, warning >75 s; None off-Windows. Static.
Side effects: event-log/WMI reads.

### `HealthChecker._check_security() -> HealthCheck | None` (L197)
Defender status: warning when real-time off or signatures >7 days, good when on+current; None off-Windows. Static.
Side effects: Defender PowerShell read.

### `HealthChecker._check_updates() -> HealthCheck | None` (L220)
Ages `WindowsUpdate.last_activity()["last_install"]`: warning >45 days; None off-Windows. Static.
Side effects: registry read (update timestamp).

---
## src/cortex_unified/system_tools/defender.py

### `DefenderStatus.healthy() -> bool` (L40)
True when available + real-time + AV enabled + signatures ≤7 days (or unknown age). Property.
Side effects: none.

### `DefenderStatus.to_dict() -> dict` (L45)
Serializes status including computed `healthy`.
Side effects: none.

### `WindowsDefender.is_supported() -> bool` (L65)
Windows-only gate (`sys.platform == "win32"`). Static.
Side effects: none.

### `WindowsDefender.status() -> DefenderStatus` (L69)
Runs `Get-MpComputerStatus` (AM mode, real-time, AV, tamper, signature version/age, scan times, engine) and parses it; unavailable off-Windows.
Side effects: PowerShell subprocess (read-only).

### `WindowsDefender._parse_status(out) -> DefenderStatus` (L83)
Parses Get-MpComputerStatus JSON (dict or 1-list) into DefenderStatus; bad/empty → unavailable. Static.
Side effects: none.

### `WindowsDefender._int(v)` (L94)
Safe int-or-None coercion (nested helper). Pure.
Side effects: none.

### `WindowsDefender.recent_threats(limit=20) -> list[dict]` (L117)
`Get-MpThreatDetection` + `Get-MpThreat` names, newest-first, capped at limit; [] off-Windows.
Side effects: PowerShell subprocess (read-only).

### `WindowsDefender._parse_threats(out) -> list[dict]` (L132)
Normalizes threat JSON (dict or list) to time/threat/id rows. Static.
Side effects: none.

### `WindowsDefender.start_quick_scan() -> tuple[bool, str]` (L154)
Starts `Start-MpScan -ScanType QuickScan` (up to 20 min timeout); (False, reason) off-Windows or on failure.
Side effects: Defender scan subprocess (CPU/disk load; harmless, user-triggered).

### `WindowsDefender._clean_date(raw) -> str` (L165)
Normalizes `/Date(ms)/` or ISO dates to `YYYY-MM-DD HH:MM`. Static.
Side effects: none.

### `WindowsDefender._run(script, timeout, want_returncode=False)` (L181)
PowerShell runner via `core.proc` (hidden window, cancellable); returns stdout or rc-bool, None/False on failure.
Side effects: PowerShell subprocess.

---
## src/cortex_unified/system_tools/firewall_manager.py

All created rules are prefixed `Cortex Cleaner:`; creation/removal/toggle need Administrator; listing is read-only.

### `FirewallRule.to_dict() -> dict` (L47)
Serializes a rule (name/display/direction/action/enabled/program/address/protocol/managed flag).
Side effects: none.

### `FirewallManager.is_supported() -> bool` (L66)
Windows-only gate. Static.
Side effects: none.

### `FirewallManager.block_program(program_path, direction="Outbound", label="") -> tuple[bool, str]` (L72)
Creates a Block rule for a program via `_new_rule`.
Side effects: `New-NetFirewallRule` PowerShell (admin).

### `FirewallManager.allow_program(program_path, direction="Outbound", label="") -> tuple[bool, str]` (L78)
Creates an Allow rule for a program.
Side effects: `New-NetFirewallRule` PowerShell (admin).

### `FirewallManager.block_remote_address(address, direction="Outbound", label="") -> tuple[bool, str]` (L84)
Validates the IP/range then creates a Block rule for it; (False, message) when invalid.
Side effects: `New-NetFirewallRule` PowerShell (admin) when valid.

### `FirewallManager._new_rule(action, direction, label, program="", remote_address="") -> tuple[bool, str]` (L92)
Builds/displays the `New-NetFirewallRule` command (Any profile, quoted args) and runs it; validates direction and Windows support.
Side effects: firewall-rule creation subprocess (admin).

### `FirewallManager.list_rules(cortex_only=True) -> list[FirewallRule]` (L120)
Lists firewall rules + app/address/port filters as one JSON blob via Get-NetFirewallRule*; defaults to Cortex-prefixed rules; [] off-Windows.
Side effects: PowerShell subprocess (read-only).

### `FirewallManager.set_enabled(name, enabled) -> tuple[bool, str]` (L142)
Toggles a rule via `Set-NetFirewallRule -Enabled`.
Side effects: firewall-rule mutation (admin).

### `FirewallManager.remove_rule(name) -> tuple[bool, str]` (L150)
Deletes a rule via `Remove-NetFirewallRule`.
Side effects: firewall-rule deletion (admin).

### `FirewallManager._parse_rules(out) -> list[FirewallRule]` (L160)
Parses rule JSON (dict or list) into FirewallRule objects, flagging Cortex-managed display names; bad input → []. Static.
Side effects: none.

### `FirewallManager._valid_address(addr) -> bool` (L192)
Validates single IP, CIDR, or lo-hi range via ipaddress. Static.
Side effects: none.

### `FirewallManager._ps_quote(value) -> str` (L214)
Single-quotes a PowerShell value, doubling embedded quotes. Static pure.
Side effects: none.

### `FirewallManager._run(script, want_output=False)` (L218)
PowerShell runner via `core.proc` (hidden window, 30 s timeout): bool rc or stdout-or-None.
Side effects: PowerShell subprocess.

---
## src/cortex_unified/system_tools/network_discovery.py

Active probing is confined to this PC's own private subnets; never the internet.

### `Device.randomized_mac() -> bool` (L200)
Privacy-MAC test via `oui.is_randomized`. Property.
Side effects: none.

### `Device.label() -> str` (L205)
Best human name: friendly → model → non-UUID hostname → service instance → vendor → Router/IP. Property.
Side effects: none.

### `Device._looks_like_uuid(text) -> bool` (L232)
True for ≥24-hex machine IDs not worth displaying. Static pure.
Side effects: none.

### `Device.kind() -> str` (L239)
Evidence-only category (gateway/self, then mDNS services, open ports, vendor/model keywords, RDP/SMB, randomized-MAC fallback). Property.
Side effects: none.

### `Device.evidence() -> str` (L292)
Human description of observing methods (ARP/mDNS/UPnP/WSD/NBNS/ping/ports). Property.
Side effects: none.

### `Device.merge(other: Device) -> None` (L307)
Folds another observation (MAC/host/vendor/state/sources/services/ports/fingerprint/flags/RTT) into this one, deduping service observations.
Side effects: none (in-memory).

### `Device.to_dict() -> dict` (L336)
Full serialization including label/kind/evidence and nested service observations.
Side effects: none.

### `Interface.network() -> IPv4Network | None` (L380)
`ip/netmask` as a network, or None when invalid. Property.
Side effects: none.

### `DiscoveryResult.to_dict() -> dict` (L403)
Serializes devices/networks/duration/notes/cancel state plus findings/WAN/inventory changes when present.
Side effects: none.

### `NetworkDiscovery.__init__(timeout_s=4.0, workers=128)` (L434)
Stores multicast timeout + ≥8 worker count.
Side effects: none.

### `NetworkDiscovery.scan(progress=None, cancel_event=None, deep=True, rounds=2, audit_profile="targeted", include_upnp_wan=False, record_history=False, requested_networks=None, custom_ports=None, nmap_modes=None, advisory_catalog_path=None) -> DiscoveryResult` (L442)
Full pipeline: local/private interfaces → scope validation (custom scope must sit inside local nets; >1024-host nets skipped) → self + neighbor cache → broadcast ping + N-round ARP sweeps → mDNS/SSDP/WSD → re-read cache → reverse-DNS/NetBIOS names → profiled service audit (+optional Nmap on discovered hosts) → vendor/gateway/self labels → WAN audit + security findings → optional inventory history. Returns devices + notes + findings.
Side effects: UDP/TCP probes confined to own private subnets; ARP/mDNS/SSDP/WSD/NetBIOS/DNS network I/O; `Get-NetNeighbor`/`arp`/PowerShell subprocesses; optional Nmap + WAN UPnP reads; optional SQLite history write. No firewall/registry writes.

### `NetworkDiscovery.local_interfaces() -> list[Interface]` (L663)
Up, private, non-loopback/link-local IPv4 interfaces via psutil. Static.
Side effects: interface enumeration reads.

### `NetworkDiscovery._local_devices(interfaces) -> list[Device]` (L693)
One `is_self` entry per interface (hostname + psutil MACs). Static.
Side effects: hostname + interface reads.

### `NetworkDiscovery.default_gateways() -> set[str]` (L726)
Default-gateway IPs via `Get-NetRoute` (Windows) or `ip route show default`.
Side effects: route subprocess reads.

### `NetworkDiscovery._read_neighbors() -> list[Device]` (L753)
Neighbor cache via Windows path with `arp -a` fallback.
Side effects: subprocess reads.

### `NetworkDiscovery._read_neighbors_windows() -> list[Device]` (L761)
`Get-NetNeighbor` IPv4 entries with real MACs in Reachable/Stale/Permanent/Delay/Probe states only (skips zero-MAC phantoms).
Side effects: PowerShell subprocess read.

### `NetworkDiscovery._read_arp_command() -> list[Device]` (L786)
Parses `arp -a` IP+MAC pairs, filtering unusable hosts.
Side effects: `arp` subprocess read.

### `NetworkDiscovery._broadcast_ping(targets) -> None` (L813)
One discard-port UDP datagram per subnet broadcast to pre-warm ARP; failures ignored. Static.
Side effects: outbound LAN UDP (private subnets only).

### `NetworkDiscovery._arp_sweep(hosts, cancel_event, settle_s=2.0) -> None` (L829)
One discard-port UDP per host (≤48 threads) forcing ARP resolution, then a settle wait; ignores closed ports/unreachables by design.
Side effects: outbound LAN UDP to every swept host (private only).

### `NetworkDiscovery._poke(ip) -> None` (L846)
Single-host UDP poke used by the sweep (nested helper honoring cancel).
Side effects: one LAN UDP datagram.

### `NetworkDiscovery._is_ipv4(value) -> bool` (L872)
IPv4 validation. Static pure.
Side effects: none.

### `NetworkDiscovery._usable_host(ip, mac) -> bool` (L883)
Rejects non-IPv4, zero/broadcast/multicast MACs, multicast/unspecified IPs, `.255`; classmethod pure.
Side effects: none.

### `NetworkDiscovery._ip_sort_key(ip) -> tuple` (L906)
Numeric-octet sort key (unparsable sorts last). Static pure.
Side effects: none.

### `NetworkDiscovery._merge(into, found) -> None` (L916)
Merges discovered devices by IP (insert or fold). Static.
Side effects: none (mutates the passed dict).

### `NetworkDiscovery._run_ps(script, timeout=45) -> str | None` (L927)
Hidden-window PowerShell runner returning stdout or None.
Side effects: PowerShell subprocess.

### `NetworkDiscovery._discover_mdns(cancel_event) -> list[Device]` (L943)
Sends DNS PTR queries for ~22 service types to 224.0.0.251:5353 per interface and parses answers for names/addresses/models.
Side effects: outbound LAN multicast UDP + listen socket; no writes.

### `NetworkDiscovery._absorb_mdns(found, data, src_ip) -> None` (L998)
Parses one mDNS packet (A/PTR/SRV/TXT incl. `fn=`/`md=`) into device names/services.
Side effects: none (mutates `found`).

### `NetworkDiscovery._split_service_instance(value) -> tuple[str, str]` (L1046)
Splits `Instance._type._tcp.local` into (type, instance). Static pure.
Side effects: none.

### `NetworkDiscovery._build_dns_query(name, qtype=12) -> bytes` (L1059)
Minimal DNS query packet builder. Static pure.
Side effects: none.

### `NetworkDiscovery._parse_dns_records(data) -> list[tuple[str, int, Any]]` (L1069)
Parses DNS answers/authorities/additionals incl. 0xC0 compression; decodes A/PTR/CNAME/SRV/TXT. Classmethod pure.
Side effects: none.

### `NetworkDiscovery._read_name(data, offset) -> tuple[str, int]` (L1114)
Reads a possibly-compressed DNS name with loop guard. Static pure.
Side effects: none.

### `NetworkDiscovery._discover_ssdp(cancel_event) -> list[Device]` (L1144)
M-SEARCH to 239.255.255.250:1900 per interface; records SERVER/ST headers.
Side effects: outbound LAN multicast UDP + listen.

### `NetworkDiscovery._discover_wsd(cancel_event) -> list[Device]` (L1206)
WS-Discovery SOAP Probe to 239.255.255.250:3702; classifies printer/computer/device.
Side effects: outbound LAN multicast UDP + listen.

### `NetworkDiscovery._pseudo_uuid() -> str` (L1270)
Random UUID for the WSD MessageID. Static.
Side effects: none.

### `NetworkDiscovery._parse_http_headers(data) -> dict[str, str]` (L1278)
Lower-cased dict of SSDP HTTP-style headers. Static pure.
Side effects: none.

### `NetworkDiscovery._resolve_names(devices, cancel_event) -> None` (L1289)
Parallel reverse-DNS then NetBIOS naming for hostname-less devices (≤64 threads); tags nbns sources.
Side effects: DNS lookups + NetBIOS UDP queries on LAN.

### `NetworkDiscovery._resolve(device) -> None` (L1296)
Per-device reverse-DNS→NetBIOS fallback (nested helper).
Side effects: DNS + NetBIOS LAN queries for one host.

### `NetworkDiscovery._netbios_name(ip, timeout=0.6) -> str` (L1319)
Node-status query over UDP 137; returns first unique (non-group) name.
Side effects: outbound LAN UDP to one host.

### `NetworkDiscovery._fingerprint(devices, cancel_event) -> None` (L1357)
Audits only discovered in-scope private hosts via `NetworkServiceScanner` (targeted/advanced/deep profile + custom ports) and optional explicit Nmap modes; attaches observations/open ports/`ports` source.
Side effects: TCP/UDP service probes to discovered LAN hosts (private only); no internet.

### `NetworkDiscovery._build_notes(devices, targets, gateways) -> list[str]` (L1428)
Explains limits: stale vendor DB, randomized MACs, router-only (client isolation), mDNS-without-ARP (off-subnet). Static.
Side effects: vendor-registry status read.

---
## src/cortex_unified/system_tools/driver_manager.py

### `DriverInfo.to_dict() -> dict` (L98)
`dataclasses.asdict` of one driver record.
Side effects: none.

### `ScanResult.to_json() -> str` (L127)
JSON of totals + per-driver dicts.
Side effects: none.

### `DriverManager.__init__(create_restore_point=True, progress_callback=None, cancel_event=None, offline_mode=False, driverpack_index=None)` (L145)
Stores flags/callbacks, builds RestorePointManager, loads an SDIO-compatible driverpack index when given.
Side effects: index file read when provided.

### `DriverManager._run(cmd, timeout=120) -> Tuple[int, str, str]` (L166)
Cancellation-checked subprocess runner returning (rc, stdout, stderr).
Side effects: arbitrary child processes.

### `DriverManager._run_ps(script, timeout=120) -> Tuple[int, str, str]` (L183)
PowerShell via `_run`.
Side effects: PowerShell subprocess.

### `DriverManager._load_index(path) -> None` (L189)
Loads driverpack JSON into hardware-ID map; reports progress, never raises.
Side effects: index file read.

### `DriverManager._save_index(path) -> None` (L204)
Persists deduplicated driverpack index as JSON.
Side effects: index file write.

### `DriverManager._pack_to_dict(pack) -> dict` (L215)
`asdict` of a DriverPack.
Side effects: none.

### `DriverManager._enumerate_pnp() -> List[DriverInfo]` (L224)
Enumerates present OK PnP devices via Get-PnpDevice + driver properties (version/date/provider/IDs), normalizes dates, resolves store path/INF via `pnputil /enum-drivers`.
Side effects: PowerShell + `pnputil` subprocess reads (Windows; admin helps).

### `DriverManager._check_updates_online(drivers) -> List[DriverInfo]` (L311)
Matches enumerated hardware IDs against Windows Update Agent COM driver offers (`IsInstalled=0, Type='Driver'`), marking newer WHQL versions outdated; unchanged input when WUA unavailable.
Side effects: WUA COM search (needs network for offers; elevation for install rights). Reads only.

### `DriverManager._wua_driver_updates() -> Optional[List[Any]]` (L411)
Returns pending WUA driver COM objects (`ssWindowsUpdate`), or None without pywin32/COM or on search failure.
Side effects: WUA COM search (outbound to Windows Update when available).

### `DriverManager._check_updates_offline(drivers) -> List[DriverInfo]` (L435)
Matches hardware/compatible IDs against the local driverpack index, marking newer versions outdated.
Side effects: none (in-memory index).

### `DriverManager._version_newer(v1, v2) -> bool` (L459)
Multi-part numeric version compare (nested `parse(v)` splits on `.-_`); longer-is-newer on prefix ties.
Side effects: none.

### `DriverManager.scan() -> ScanResult` (L472)
Enumerates devices then checks offline index or online WUA; returns drivers + outdated/missing counts + elapsed time.
Side effects: PnP/WUA subprocess+COM reads; optional network to Windows Update.

### `DriverManager.update_selected(hardware_ids, force=False) -> Dict[str, bool]` (L496)
Re-scans, restores-point per device, then downloads (`urllib`) or installs from store via `pnputil /add-driver /install`; returns per-ID success.
Side effects: restore points; driver downloads (network); `pnputil` installs (admin; may need reboot). Skips IDs without a source.

### `DriverManager._download_and_install(drv, force) -> bool` (L529)
Downloads a driver CAB to temp and installs via `pnputil /add-driver /install` (temp auto-cleaned).
Side effects: outbound download; `pnputil` install (admin).

### `DriverManager._install_from_store(inf_name, force) -> bool` (L549)
Installs an INF already in the driver store via `pnputil`.
Side effects: `pnputil` install (admin).

### `DriverManager.cleanup_driver_store(dry_run=True) -> Tuple[int, int]` (L557)
Groups `pnputil /enum-drivers` by (class, date-version, provider), keeping newest per group; dry-run counts, real run deletes via `pnputil /delete-driver /uninstall`. Returns (removed, freed_mb — currently always 0).
Side effects: `pnputil` reads; driver deletions unless dry-run (admin).

### `DriverManager.export_driverpack_index(path) -> None` (L610)
Exports the current index JSON for offline/air-gapped use.
Side effects: file write.

### `DriverManager.get_stats() -> Dict` (L615)
Fresh scan totals + index size.
Side effects: full scan reads (PnP + update check).
