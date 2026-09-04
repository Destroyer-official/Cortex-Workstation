# Rust Public API Audit — NexusExplorer (`src-tauri`) + `nexus_engine_ffi` + C Header

Base: `D:\code\Main_projects\Cortex_Cleaner`
Scope: `src/NexusExplorer/src-tauri/src/**` (lib.rs, bin/nexus-cli.rs, engine/, commands/, models/) + `src/NexusExplorer/nexus_engine_ffi/src/**` (*.rs) + `nexus_engine_ffi/include/nexus_engine.h`
Method: read source; one line purpose per item. `L<n>` = definition line in that file.

## src/NexusExplorer/src-tauri/src/lib.rs
- `pub mod commands` (L1): re-exports Tauri IPC command modules.
- `pub mod engine` (L2): re-exports copy/search/listing/job/watch core.
- `pub mod models` (L3): re-exports FileEntry/event DTOs.
- `pub fn run()` (L29): builds Tauri app, registers state/plugins and invoke_handler, runs event loop.

## src/NexusExplorer/src-tauri/src/main.rs
- (no `pub` items) private `fn main()` (L3): delegates to `nexus_explorer_lib::run()`.

## src/NexusExplorer/src-tauri/src/bin/nexus-cli.rs
- (no `pub` items; binary crate) private helpers `print_usage` (L26), `fmt_bytes` (L40), `file_mtime_ms` (L58), `ms_to_string` (L67), `entries_to_json` (L88), `cmd_list` (L94), `cmd_search` (L143), `render_progress` (L190), `truncate` (L215), `format_eta` (L223), `cmd_transfer` (L234), `cmd_delete` (L316), `cmd_drives` (L351), `cmd_drives_json` (L549), `cmd_hash` (L473), `cmd_rename` (L511), `cmd_mkdir` (L535), `cmd_gui` (L582), `fn main` (L610): CLI frontend reusing `nexus_explorer_lib::engine::{copy_engine,search_engine}` + `commands::fs_cmds::__cli_read_dir`.
- `#[cfg(windows)] fn with_wide / struct ErrorModeGuard / fs_free_total / drive_type_name / fs_name / volume_label` (L388–471): Windows drive-probe helpers with SEM_FAILCRITICALERRORS guard.

## src/NexusExplorer/src-tauri/src/engine/mod.rs
- `pub mod copy_engine` (L1): transfer/delete engine.
- `pub mod job_manager` (L2): job registry/control plane.
- `pub mod listing` (L3): scan cancellation registry.
- `pub mod search_engine` (L4): parallel filename search.
- `pub mod watch` (L5): recursive fs watchers.

## src/NexusExplorer/src-tauri/src/engine/listing.rs
- `pub struct ScanRegistry { flags: Arc<Mutex<HashMap<String, Arc<AtomicBool>>>> }` (L11): maps scan-id → cancel flag.
- `pub fn ScanRegistry::new() -> Self` (L17): creates empty registry.
- `pub fn ScanRegistry::insert(&self, id: String, flag: Arc<AtomicBool>)` (L22): registers cancel flag under id.
- `pub fn ScanRegistry::cancel(&self, id: &str) -> bool` (L27): sets cancel flag; true if id was registered.
- `pub fn ScanRegistry::remove(&self, id: &str) -> Option<Arc<AtomicBool>>` (L38): unregisters and returns flag.

## src/NexusExplorer/src-tauri/src/engine/search_engine.rs
- `pub struct SearchRegistry { flags: Arc<Mutex<HashMap<String, Arc<AtomicBool>>>> }` (L16): maps search-id → cancel flag.
- `pub fn SearchRegistry::new() -> Self` (L21): creates empty registry.
- `pub fn SearchRegistry::register(&self, id: String, flag: Arc<AtomicBool>)` (L25): registers search cancel flag.
- `pub fn SearchRegistry::cancel(&self, id: &str) -> bool` (L29): signals cancellation for id.
- `pub fn SearchRegistry::remove(&self, id: &str) -> Option<Arc<AtomicBool>>` (L39): unregisters search flag.
- `pub fn run_search_blocking(root: String, query: String, opts: SearchOptions, cancel: Arc<AtomicBool>, sink: &mut dyn FnMut(SearchEvent))` (L140): jwalk parallel walk with wildcard/substring matcher, streams Batch/Done/Error via sink.

## src/NexusExplorer/src-tauri/src/engine/copy_engine.rs
- `pub enum JobKind { Copy, Move }` (L32): transfer operation discriminator.
- `pub fn JobKind::as_str(self) -> &'static str` (L38): maps variant to "copy"/"move".
- `pub struct OrphanPart { job_id, kind, dst_dir, part_file, bytes, last_state }` (L627): one interrupted-transfer `.nexuspart` leftover found via journal.
- `pub fn list_orphan_parts() -> Vec<OrphanPart>` (L638): scans `jobs.jsonl` for non-completed jobs with residual `.nexuspart` files.
- `pub fn run_transfer_blocking(kind: JobKind, sources: Vec<String>, dest_dir: String, control: Arc<JobControl>, job_id: String, sink: &mut dyn FnMut(JobEvent))` (L884): plans, copies/moves with resume/checkpoint/verify/conflict flow, emits Started/Progress/Conflict/FileDone/Error/State.
- `pub fn run_delete_blocking(paths: Vec<String>, to_trash: bool, control: Arc<JobControl>, job_id: String, sink: &mut dyn FnMut(JobEvent))` (L1085): deletes to trash or permanently with progress events.
- Note (non-`pub`, excluded from count): `pub(crate) const SMALL_FILE_FAST_MAX` (L52), `pub(crate) fn journal_dir()` (L581), `pub(crate) fn verify_copy()` (L703) — internal fast-path threshold, journal path, xxh3 verify helper.

## src/NexusExplorer/src-tauri/src/engine/job_manager.rs
- `pub struct JobControl { kind, cancel, paused, resume_notify, state, total_files, processed_files, total_bytes, processed_bytes, speed_bps, eta_secs, current_file, errors, pending_conflicts, apply_all, deferred_verify }` (L12): shared per-job flags, counters, conflict channels.
- `pub fn JobControl::new(kind: &str) -> Self` (L33): initializes running-state control block.
- `pub fn JobControl::wait_while_paused(&self) -> bool` (L55): sleeps while paused; false if cancelled.
- `pub fn JobControl::set_state(&self, state: &str)` (L65): updates terminal/running state string.
- `pub fn JobControl::snapshot(&self, job_id: &str) -> JobSummary` (L69): builds immutable status summary for IPC.
- `pub struct JobManager { jobs: Arc<Mutex<HashMap<String, Arc<JobControl>>>> }` (L88): registry of all jobs keyed by id.
- `pub fn JobManager::new() -> Self` (L93): creates empty registry.
- `pub fn JobManager::register(&self, id: String, control: Arc<JobControl>)` (L97): inserts job control handle.
- `pub fn JobManager::get(&self, id: &str) -> Option<Arc<JobControl>>` (L101): clones handle for id if present.
- `pub fn JobManager::list_summaries(&self) -> Vec<JobSummary>` (L105): snapshots every known job.
- `pub fn JobManager::resolve(&self, job_id: &str, conflict_id: &str, resolution: String, apply_to_all: bool) -> Result<(), String>` (L113): delivers conflict answer to waiting engine thread.

## src/NexusExplorer/src-tauri/src/engine/watch.rs
- `pub const FS_CHANGE_EVENT: &str` (L17): Tauri event name `"fs-change"`.
- `pub struct FsChangePayload { pub path: String }` (L24): watched-root payload emitted on debounced batch.
- `pub struct WatchManager { watchers: Mutex<HashMap<String, WatcherHandle>> }` (L30): per-directory recursive debounced watchers.
- `pub fn WatchManager::new() -> Self` (L35): creates empty manager.
- `pub fn WatchManager::watch(&self, app: AppHandle, path: String) -> Result<(), String>` (L42): starts recursive watch; no-op if already watched.
- `pub fn WatchManager::unwatch(&self, path: String) -> Result<(), String>` (L76): drops watcher for path.

## src/NexusExplorer/src-tauri/src/commands/mod.rs
- `pub mod fs_cmds` (L1): scan/list/drives/file-op commands.
- `pub mod ops_cmds` (L2): copy/move/delete job commands.
- `pub mod search_cmds` (L3): search commands.

## src/NexusExplorer/src-tauri/src/commands/fs_cmds.rs
- `pub async fn scan_dir(path: String, on_event: Channel<ScanEvent>, registry: State<'_, ScanRegistry>) -> Result<ScanStart, String>` (L32): spawns async batched sorted scan streaming over channel.
- `pub async fn cancel_scan(scan_id: String, registry: State<'_, ScanRegistry>) -> Result<(), String>` (L66): cancels active scan by id.
- `pub async fn read_dir_sync(path: String) -> Result<Vec<FileEntry>, String>` (L76): synchronous dirs-first sorted listing.
- `pub fn __cli_read_dir(path: &str) -> Result<Vec<FileEntry>, String>` (L84): sync listing shared with `nexus-cli` binary.
- `pub async fn stat_path(path: String) -> Result<Option<FileEntry>, String>` (L93): metadata for path, None if missing.
- `pub async fn get_drives() -> Result<Vec<DriveInfo>, String>` (L118): enumerates Windows volumes with label/fs/space.
- `pub async fn home_dir() -> Result<String, String>` (L124): returns USERPROFILE or error.
- `pub async fn rename_entry(path: String, new_name: String) -> Result<FileEntry, String>` (L131): validates name, renames, returns refreshed entry.
- `pub async fn create_folder(parent: String, name: String) -> Result<FileEntry, String>` (L152): validates and creates folder, returns entry.
- `pub async fn read_text_file(path: String, max_bytes: u32) -> Result<TextPreview, String>` (L167): reads up-to-limit preview, rejects NUL-prefixed binary.
- `pub async fn open_path(app: AppHandle, path: String) -> Result<(), String>` (L198): opens path with default app via opener plugin.
- `pub async fn reveal_in_shell(path: String) -> Result<(), String>` (L207): selects path in Explorer via `explorer /select,`.
- `pub async fn watch_dir(app: AppHandle, path: String, watcher: State<'_, WatchManager>) -> Result<(), String>` (L217): starts watching directory.
- `pub async fn unwatch_dir(path: String, watcher: State<'_, WatchManager>) -> Result<(), String>` (L227): stops watching directory.

## src/NexusExplorer/src-tauri/src/commands/ops_cmds.rs
- `pub async fn copy_entries(sources: Vec<String>, dest_dir: String, on_event: Channel<JobEvent>, jobs: State<'_, JobManager>) -> Result<String, String>` (L52): starts copy job, returns job_id.
- `pub async fn move_entries(sources: Vec<String>, dest_dir: String, on_event: Channel<JobEvent>, jobs: State<'_, JobManager>) -> Result<String, String>` (L62): starts move job, returns job_id.
- `pub async fn delete_entries(paths: Vec<String>, to_trash: bool, on_event: Channel<JobEvent>, jobs: State<'_, JobManager>) -> Result<String, String>` (L72): starts delete/trash job, returns job_id.
- `pub async fn pause_job(job_id: String, jobs: State<'_, JobManager>) -> Result<JobSummary, String>` (L104): sets paused flag/state, returns snapshot.
- `pub async fn resume_job(job_id: String, jobs: State<'_, JobManager>) -> Result<JobSummary, String>` (L115): clears paused flag, notifies, returns snapshot.
- `pub async fn cancel_job(job_id: String, jobs: State<'_, JobManager>) -> Result<JobSummary, String>` (L129): sets cancel flag, returns snapshot.
- `pub async fn resolve_conflict(job_id: String, conflict_id: String, resolution: String, apply_to_all: bool, jobs: State<'_, JobManager>) -> Result<(), String>` (L140): validates skip/overwrite/keepBoth and delivers resolution.
- `pub async fn get_active_jobs(jobs: State<'_, JobManager>) -> Result<Vec<JobSummary>, String>` (L154): lists all job snapshots.

## src/NexusExplorer/src-tauri/src/commands/search_cmds.rs
- `pub async fn search_files(root: String, query: String, opts: SearchOptions, on_event: Channel<SearchEvent>, registry: State<'_, SearchRegistry>) -> Result<String, String>` (L14): spawns blocking search streaming batches, returns search_id.
- `pub async fn cancel_search(search_id: String, registry: State<'_, SearchRegistry>) -> Result<(), String>` (L51): cancels active search.

## src/NexusExplorer/src-tauri/src/models/mod.rs
- `pub mod events` (L1): Scan/Search/Job event enums.
- `pub mod file_entry` (L2): FileEntry/DriveInfo/JobSummary DTOs.
- Re-exports (L4–5): `pub use events::{JobEvent, ScanEvent, SearchEvent}`; `pub use file_entry::{DriveInfo, FileEntry, JobSummary, ScanStart, SearchOptions, TextPreview}`.

## src/NexusExplorer/src-tauri/src/models/file_entry.rs
- `pub struct FileEntry { name, path, parent_path, is_dir, size, modified_ms, created_ms, is_hidden, is_system, is_readonly, ext }` (L5): serializable file row (camelCase).
- `pub struct DriveInfo { path, label, drive_type, filesystem, free_bytes, total_bytes, is_ready }` (L21): volume descriptor.
- `pub struct ScanStart { scan_id, root_path }` (L33): scan handshake return.
- `pub struct TextPreview { content, truncated, size }` (L40): bounded text preview.
- `pub struct JobSummary { job_id, kind, state, total_files, processed_files, total_bytes, processed_bytes, speed_bps, eta_secs, current_file, conflicts_pending }` (L48): job status snapshot.
- `pub struct SearchOptions { recursive, max_results, include_hidden }` (L64): search flags (Serialize+Deserialize).

## src/NexusExplorer/src-tauri/src/models/events.rs
- `pub enum ScanEvent { Batch{entries}, Done{total,duration_ms}, Error{message} }` (L7): streamed scan batches/completion.
- `pub enum SearchEvent { Batch{entries}, Done{total,duration_ms}, Error{message} }` (L15): streamed search batches/completion.
- `pub enum JobEvent { Started, Progress, FileDone, Conflict, State, Error }` (L23): transfer lifecycle incl. conflict request and per-file/error reports.

## src/NexusExplorer/nexus_engine_ffi/src/lib.rs
- `pub type NexusHandle = *mut c_void` (L25): opaque async-operation handle alias.
- `pub type ListCallback = extern "C" fn(user_data, entries, count, done, error)` (L28): directory batch callback.
- `pub type ProgressCallback = extern "C" fn(user_data, job_id, processed_bytes, total_bytes, speed_bps, eta_seconds, current_file)` (L37): transfer progress callback.
- `pub type CompletionCallback = extern "C" fn(user_data, job_id, success, error)` (L48): terminal job callback.
- `pub type ConflictCallback = extern "C" fn(user_data, job_id, conflict_id, source, destination, source_size, dest_size, source_mtime, dest_mtime, is_dir) -> c_int` (L56): returns 0=skip,1=overwrite,2=keep_both,-1=cancel.
- `pub type SearchCallback = extern "C" fn(user_data, entries, count, done, error)` (L70): search batch callback.
- `pub type FsEventCallback = extern "C" fn(user_data, path)` (L79): fs-change notification callback.
- `pub unsafe extern "C" fn nexus_init() -> *mut c_void` (L89): creates Arc-wrapped NexusContext, returns opaque handle.
- `pub unsafe extern "C" fn nexus_free(ctx: *mut c_void)` (L96): drops context Arc for handle.
- `pub extern "C" fn nexus_version() -> *const c_char` (L103): returns static CARGO_PKG_VERSION string.
- Re-exports (L16–22): `pub use ffi_types::*; listing::*; copy::*; search::*; watch::*; drives::*; utils::*`.
- Internal (non-`pub`): `pub(crate) struct NexusContext` (L109), `pub(crate) struct SendPtr` (L143) — shared registries + Send user-data wrapper.

## src/NexusExplorer/nexus_engine_ffi/src/ffi_types.rs
- `pub struct FileEntry { name, path, parent_path, is_dir, size, modified_ms, created_ms, is_hidden, is_system, is_readonly, ext }` (L6): #[repr(C)] file row with owned C strings.
- `pub struct DriveInfo { path, label, drive_type, filesystem, free_bytes, total_bytes, is_ready }` (L22): #[repr(C)] volume descriptor.
- `pub struct SearchOptions { recursive, max_results, include_hidden }` (L34): #[repr(C)] search flags (defaults recursive=1, max=10000).
- `pub struct TextPreview { content, truncated, size }` (L42): #[repr(C)] text preview out-param shape.
- `pub struct JobSummary { job_id, kind, state, total_files, processed_files, total_bytes, processed_bytes, speed_bps, eta_seconds, current_file, conflicts_pending }` (L50): #[repr(C)] job snapshot.
- `impl Default` for each (L66,84,98,108,118): zero/null defaults for FFI construction.

## src/NexusExplorer/nexus_engine_ffi/src/listing.rs
- `pub unsafe extern "C" fn nexus_scan_dir(ctx: *mut c_void, path: *const c_char, callback: ListCallback, user_data: *mut c_void) -> c_int` (L15): spawns thread scanning dir in 500-entry batches, final done callback.
- `pub unsafe extern "C" fn nexus_cancel_scan(ctx: *mut c_void, scan_id: *const c_char) -> c_int` (L130): cancels scan id (0 ok, -1 missing/invalid).
- `pub unsafe extern "C" fn nexus_read_dir_sync(ctx: *mut c_void, path: *const c_char, out_entries: *mut *mut FileEntry, out_count: *mut size_t) -> c_int` (L147): sync listing into malloc-style boxed slice for caller + `nexus_free_entries`.
- `pub unsafe extern "C" fn nexus_read_dir_sync_json(ctx: *mut c_void, path: *const c_char, out_json: *mut *mut c_char) -> c_int` (L219): sync listing serialized to JSON string (free with `nexus_free_string`); **not declared in header**.
- `pub unsafe extern "C" fn nexus_free_entries(entries: *mut FileEntry, count: size_t)` (L289): frees per-row C strings and entry slice.

## src/NexusExplorer/nexus_engine_ffi/src/search.rs
- `pub unsafe extern "C" fn nexus_search_files(ctx: *mut c_void, root: *const c_char, query: *const c_char, options: *const SearchOptions, callback: SearchCallback, user_data: *mut c_void) -> c_int` (L11): threaded jwalk search with 200-entry batches + done; records thread-local last-search-id.
- `pub unsafe extern "C" fn nexus_cancel_search(ctx: *mut c_void, search_id: *const c_char) -> c_int` (L163): cancels by id, or thread-local last id when NULL.
- `pub unsafe extern "C" fn nexus_last_search_id(ctx: *mut c_void, out_id: *mut *mut c_char) -> c_int` (L182): copies thread-local last search id to caller-owned string.

## src/NexusExplorer/nexus_engine_ffi/src/copy.rs
- `pub unsafe extern "C" fn nexus_copy(ctx, sources, sources_count, dest_dir, progress_cb, complete_cb, conflict_cb, user_data) -> *mut c_void` (L190): starts copy thread via `run_transfer_blocking(Copy)`, returns job handle.
- `pub unsafe extern "C" fn nexus_move(ctx, sources, sources_count, dest_dir, progress_cb, complete_cb, conflict_cb, user_data) -> *mut c_void` (L255): starts move thread via `run_transfer_blocking(Move)`, returns job handle.
- `pub unsafe extern "C" fn nexus_delete(ctx, paths, paths_count, to_trash, progress_cb, complete_cb, user_data) -> *mut c_void` (L319): starts delete thread via `run_delete_blocking`, returns job handle.
- `pub unsafe extern "C" fn nexus_pause_job(handle: *mut c_void) -> c_int` (L392): sets paused flags/state on job handle.
- `pub unsafe extern "C" fn nexus_resume_job(handle: *mut c_void) -> c_int` (L402): clears paused flags, resumes job.
- `pub unsafe extern "C" fn nexus_cancel_job(handle: *mut c_void) -> c_int` (L412): sets cancel flags/state on job handle.
- `pub unsafe extern "C" fn nexus_free_job_handle(handle: *mut c_void)` (L423): drops boxed job handle triple.

## src/NexusExplorer/nexus_engine_ffi/src/drives.rs
- `pub unsafe extern "C" fn nexus_get_drives(ctx, out_drives: *mut *mut DriveInfo, out_count: *mut size_t) -> c_int` (L21): enumerates A–Z via GetLogicalDrives/Volume/Space, suppressing critical-error dialogs.
- `pub unsafe extern "C" fn nexus_free_drives(drives: *mut DriveInfo, count: size_t)` (L117): frees per-drive strings and slice.
- `pub unsafe extern "C" fn nexus_home_dir(ctx, out_path: *mut *mut c_char) -> c_int` (L142): returns USERPROFILE (fallback C:\) as owned string.
- `pub unsafe extern "C" fn nexus_free_string(ptr: *mut c_char)` (L156): frees any engine-allocated C string.

## src/NexusExplorer/nexus_engine_ffi/src/watch.rs
- `pub struct WatcherMap(Mutex<HashMap<String, Debouncer<RecommendedWatcher, RecommendedCache>>>)` (L12): path-lowercased debouncer registry.
- `pub fn WatcherMap::new() -> Self` (L15): creates empty watcher map.
- `pub unsafe extern "C" fn nexus_watch_dir(ctx, path, callback, user_data) -> c_int` (L32): installs recursive 250ms debounced watcher + dispatch thread filtering to create/modify/remove.
- `pub unsafe extern "C" fn nexus_unwatch_dir(ctx, path) -> c_int` (L114): removes watcher for path.

## src/NexusExplorer/nexus_engine_ffi/src/utils.rs
- `pub unsafe extern "C" fn nexus_rename(ctx, path, new_name) -> c_int` (L7): renames path into sibling `parent/new_name`.
- `pub unsafe extern "C" fn nexus_create_folder(ctx, parent, name) -> c_int` (L36): creates single-level directory `parent/name`.
- `pub unsafe extern "C" fn nexus_read_text_file(ctx, path, max_bytes: u32, out_content, out_truncated, out_size) -> c_int` (L62): bounded read with NUL-truncation handling for binary safety.
- `pub unsafe extern "C" fn nexus_open_path(ctx, path) -> c_int` (L121): opens path via explorer.exe (detached) or xdg-open.
- `pub unsafe extern "C" fn nexus_reveal_in_shell(ctx, path) -> c_int` (L150): reveals in Explorer via `explorer.exe /select,` (Windows only, -1 elsewhere).
- `pub unsafe extern "C" fn nexus_orphans_json(out_json: *mut *mut c_char) -> c_int` (L174): serializes `list_orphan_parts()` to JSON string; **not declared in header**.

## src/NexusExplorer/nexus_engine_ffi/include/nexus_engine.h
- `typedef void* NexusHandle` (L12) / `typedef void* NexusJobHandle` (L13): opaque context/job handles matching `*mut c_void` / boxed triple.
- `typedef struct NexusFileEntry { char*,int,uint64_t... }` (L16): mirrors FFI `FileEntry` field-for-field.
- `typedef struct NexusDriveInfo {...}` (L31): mirrors FFI `DriveInfo`.
- `typedef struct NexusSearchOptions { int recursive; unsigned max_results; int include_hidden; }` (L42): mirrors FFI `SearchOptions`.
- `typedef struct NexusTextPreview {...}` (L49): mirrors FFI `TextPreview` (no Rust producer; consumed via `nexus_read_text_file` out-params).
- `typedef struct NexusJobSummary {...}` (L56): mirrors FFI `JobSummary` (defined but no `nexus_get_job_summary` accessor exists).
- Callbacks `NexusListCallback` (L71), `NexusProgressCallback` (L79), `NexusCompletionCallback` (L89), `NexusConflictCallback` (L96), `NexusSearchCallback` (L109), `NexusFsEventCallback` (L117): match Rust `*Callback` aliases.
- Lifecycle `nexus_init` (L123), `nexus_free` (L124), `nexus_version` (L125): match lib.rs L89/96/103.
- Dir ops `nexus_scan_dir` (L128), `nexus_cancel_scan` (L135), `nexus_read_dir_sync` (L137), `nexus_free_entries` (L144): match listing.rs L15/130/147/289.
- File ops `nexus_copy` (L149), `nexus_move` (L160), `nexus_delete` (L171), `nexus_pause_job` (L181), `nexus_resume_job` (L182), `nexus_cancel_job` (L183), `nexus_free_job_handle` (L184): match copy.rs L190/255/319/392/402/412/423.
- Search `nexus_search_files` (L187), `nexus_cancel_search` (L199), `nexus_last_search_id` (L203): match search.rs L11/163/182 (NULL-id fallback documented in header).
- Watch `nexus_watch_dir` (L206), `nexus_unwatch_dir` (L213): match watch.rs L32/114.
- Drives `nexus_get_drives` (L216), `nexus_free_drives` (L222): match drives.rs L21/117.
- Utils `nexus_home_dir` (L225), `nexus_free_string` (L226), `nexus_rename` (L227), `nexus_create_folder` (L228), `nexus_read_text_file` (L229), `nexus_open_path` (L237), `nexus_reveal_in_shell` (L238): match drives.rs L142/156 + utils.rs L7/36/62/121/150.
- Mismatches: header **omits** `nexus_read_dir_sync_json` (listing.rs:219) and `nexus_orphans_json` (utils.rs:174); header declares no extras — every header function exists in Rust.
