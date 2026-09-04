//! Resumable, conflict-aware copy/move/delete engine.
//!
//! Runs entirely on a blocking worker thread. All user-facing feedback flows
//! through a `sink` callback so the same core can serve Tauri IPC and the CLI.

use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
#[cfg(windows)]
use std::os::windows::ffi::OsStrExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::Ordering;
use std::sync::Arc;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use xxhash_rust::xxh3::Xxh3;

#[cfg(windows)]
use windows::core::PCWSTR;
#[cfg(windows)]
use windows::Win32::Foundation::{CloseHandle, FILETIME};
#[cfg(windows)]
use windows::Win32::Storage::FileSystem::{
    CreateFileW, SetFileTime, FILE_ATTRIBUTE_NORMAL, FILE_FLAG_BACKUP_SEMANTICS,
    FILE_SHARE_READ, FILE_SHARE_WRITE, FILE_WRITE_ATTRIBUTES, OPEN_EXISTING,
};

use crate::engine::job_manager::JobControl;
use crate::models::JobEvent;

/// Transfer mode for a blocking transfer job: copy keeps the source, move removes it after copy.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum JobKind {
    Copy,
    Move,
}

impl JobKind {
    /// Returns the stable lowercase job-kind name (`"copy"` or `"move"`) used in events and the journal.
    pub fn as_str(self) -> &'static str {
        match self {
            JobKind::Copy => "copy",
            JobKind::Move => "move",
        }
    }
}

const BUFFER_SIZE: usize = 1024 * 1024;
const CHECKPOINT_INTERVAL: u64 = 256 * 1024 * 1024;
const CHECKPOINT_INTERVAL_BYTES: u64 = CHECKPOINT_INTERVAL;
const PROGRESS_MIN_INTERVAL_MS: u128 = 100;
/// Files at or below this size use the fast path: no per-file fsync and
/// verification deferred to an end-of-job batch.
pub(crate) const SMALL_FILE_FAST_MAX: u64 = 1024 * 1024;
const RETRY_DELAYS_MS: [u64; 4] = [250, 1_000, 3_000, 10_000];

#[derive(Serialize, Deserialize)]
struct Checkpoint {
    job_id: String,
    src: String,
    dst: String,
    src_size: u64,
    src_mtime_ms: u64,
    offset: u64,
}

struct PlannedItem {
    src: PathBuf,
    dst: PathBuf,
    size: u64,
    mtime_ms: u64,
    ctime_ms: u64,
    is_dir: bool,
}

fn now_ms(t: SystemTime) -> u64 {
    t.duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

fn is_busy_error(err: &io::Error) -> bool {
    matches!(err.raw_os_error(), Some(32) | Some(33))
}

fn retry_io<T>(mut op: impl FnMut() -> io::Result<T>) -> io::Result<T> {
    let mut attempt = 0usize;
    loop {
        match op() {
            Ok(v) => return Ok(v),
            Err(err) if is_busy_error(&err) && attempt < RETRY_DELAYS_MS.len() => {
                std::thread::sleep(Duration::from_millis(RETRY_DELAYS_MS[attempt]));
                attempt += 1;
            }
            Err(err) => return Err(err),
        }
    }
}

fn clear_readonly(path: &Path) {
    if let Ok(meta) = fs::metadata(path) {
        if meta.is_file() {
            let _ = fs::set_permissions(path, meta.permissions());
            #[cfg(windows)]
            {
                let _ = path.metadata().map(|m| {
                    let mut perms = m.permissions();
                    #[allow(clippy::permissions_set_readonly_false)]
                    perms.set_readonly(false);
                    fs::set_permissions(path, perms)
                });
            }
        }
    }
}

fn remove_with_retry(path: &Path) -> io::Result<()> {
    clear_readonly(path);
    retry_io(|| fs::remove_file(path))
}

fn unique_sibling(dst: &Path) -> PathBuf {
    let parent = dst.parent().unwrap_or_else(|| Path::new("."));
    let stem = dst
        .file_stem()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "file".to_string());
    let ext = dst
        .extension()
        .map(|e| e.to_string_lossy().to_string())
        .unwrap_or_default();
    let mut n = 2usize;
    loop {
        let candidate = if ext.is_empty() {
            parent.join(format!("{stem} ({n})"))
        } else {
            parent.join(format!("{stem} ({n}).{ext}"))
        };
        if !candidate.exists() {
            return candidate;
        }
        n += 1;
    }
}

fn checkpoint_path(dst: &Path) -> PathBuf {
    let mut s = dst.as_os_str().to_os_string();
    s.push(".nexuscp");
    PathBuf::from(s)
}

fn part_path(dst: &Path) -> PathBuf {
    let mut s = dst.as_os_str().to_os_string();
    s.push(".nexuspart");
    PathBuf::from(s)
}

fn write_checkpoint_atomic(cp: &Checkpoint, path: &Path) {
    if let Ok(json) = serde_json::to_vec(cp) {
        let tmp = part_path(path);
        if fs::File::create(&tmp)
            .and_then(|mut f| f.write_all(&json))
            .is_ok()
        {
            let _ = fs::rename(&tmp, path);
        }
    }
}

fn plan_walk(
    dir: &Path,
    dst_root: &Path,
    out: &mut Vec<PlannedItem>,
    total_files: &mut u64,
    total_bytes: &mut u64,
) {
    let entries = match fs::read_dir(dir) {
        Ok(e) => e,
        Err(_) => return,
    };
    for entry in entries.flatten() {
        let Ok(meta) = entry.metadata() else { continue };
        let Ok(ft) = entry.file_type() else { continue };
        if ft.is_symlink() {
            continue;
        }
        let src = entry.path();
        let Some(name) = src.file_name() else { continue };
        let dst = dst_root.join(name);
        if ft.is_dir() {
            out.push(PlannedItem {
                dst,
                is_dir: true,
                size: 0,
                mtime_ms: now_ms(meta.modified().unwrap_or(UNIX_EPOCH)),
                ctime_ms: now_ms(meta.created().unwrap_or(UNIX_EPOCH)),
                src,
            });
            let src_ref = out.last().unwrap().src.clone();
            let dst_ref = out.last().unwrap().dst.clone();
            plan_walk(&src_ref, &dst_ref, out, total_files, total_bytes);
        } else {
            let size = meta.len();
            *total_files += 1;
            *total_bytes += size;
            out.push(PlannedItem {
                src,
                dst,
                size,
                is_dir: false,
                mtime_ms: now_ms(meta.modified().unwrap_or(UNIX_EPOCH)),
                ctime_ms: now_ms(meta.created().unwrap_or(UNIX_EPOCH)),
            });
        }
    }
}

fn plan_transfer(
    sources: &[String],
    dest_dir: &str,
) -> (Vec<PlannedItem>, u64, u64, Vec<(PathBuf, String)>) {
    let mut items = Vec::new();
    let mut total_files = 0u64;
    let mut total_bytes = 0u64;
    let mut errors: Vec<(PathBuf, String)> = Vec::new();
    for source in sources {
        let p = PathBuf::from(source);
        // A missing/unreadable source must surface as a per-item error,
        // never a silent skip (failure-matrix R3 finding).
        let meta = match fs::metadata(&p) {
            Ok(m) => m,
            Err(e) => {
                errors.push((p.clone(), format!("source unavailable: {e}")));
                continue;
            }
        };
        let Some(name) = p.file_name() else {
            errors.push((p.clone(), "source has no file name".to_string()));
            continue;
        };
        let dst = Path::new(dest_dir).join(name);
        if meta.is_dir() {
            items.push(PlannedItem {
                src: p.clone(),
                dst,
                size: 0,
                is_dir: true,
                mtime_ms: now_ms(meta.modified().unwrap_or(UNIX_EPOCH)),
                ctime_ms: now_ms(meta.created().unwrap_or(UNIX_EPOCH)),
            });
            let dst_for_children = Path::new(dest_dir).join(name);
            plan_walk(
                &p,
                &dst_for_children,
                &mut items,
                &mut total_files,
                &mut total_bytes,
            );
        } else {
            let size = meta.len();
            total_files += 1;
            total_bytes += size;
            items.push(PlannedItem {
                src: p,
                dst,
                size,
                is_dir: false,
                mtime_ms: now_ms(meta.modified().unwrap_or(UNIX_EPOCH)),
                ctime_ms: now_ms(meta.created().unwrap_or(UNIX_EPOCH)),
            });
        }
    }
    (items, total_files, total_bytes, errors)
}

/// Waits for a conflict resolution; returns None when skipped or cancelled.
///
/// `emit_conflict` is invoked only AFTER the resolution channel is
/// registered in `pending_conflicts`, so a resolver that answers
/// synchronously (e.g. an in-process FFI callback) can never race the
/// registration.
fn await_conflict_resolution(
    control: &Arc<JobControl>,
    conflict_id: &str,
    emit_conflict: &mut dyn FnMut(&str),
) -> Option<String> {
    let (tx, mut rx) = tokio::sync::oneshot::channel::<String>();
    control
        .pending_conflicts
        .lock()
        .push((conflict_id.to_string(), tx));
    emit_conflict(conflict_id);
    loop {
        match rx.try_recv() {
            Ok(resolution) => return Some(resolution),
            Err(tokio::sync::oneshot::error::TryRecvError::Closed) => return None,
            Err(_) => {}
        }
        if control.cancel.load(Ordering::Relaxed) {
            return None;
        }
        std::thread::sleep(Duration::from_millis(80));
    }
}

#[cfg(windows)]
fn preserve_windows_times(path: &Path, created_ms: u64, modified_ms: u64) {
    const EPOCH_DIFF_100NS: u64 = 11_644_473_600_000_000;
    let to_ft = |ms: u64| {
        let ticks = ms.saturating_mul(10_000).saturating_add(EPOCH_DIFF_100NS);
        FILETIME {
            dwLowDateTime: ticks as u32,
            dwHighDateTime: (ticks >> 32) as u32,
        }
    };
    let mut wide: Vec<u16> = path.as_os_str().encode_wide().collect();
    wide.push(0);
    unsafe {
        let opened = CreateFileW(
            PCWSTR(wide.as_ptr()),
            FILE_WRITE_ATTRIBUTES.0,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_BACKUP_SEMANTICS,
            None,
        );
        if let Ok(handle) = opened {
            if !handle.is_invalid() {
                let created = to_ft(created_ms);
                let modified = to_ft(modified_ms);
                let _ = SetFileTime(handle, Some(&created), None, Some(&modified));
                let _ = CloseHandle(handle);
            }
        }
    }
}

fn small_fast_enabled() -> bool {
    std::env::var("NEXUS_SMALL_FAST").ok().as_deref() != Some("0")
}

#[allow(clippy::too_many_arguments)]
fn copy_one_file(
    control: &Arc<JobControl>,
    sink: &mut dyn FnMut(JobEvent),
    job_id: &str,
    item: &PlannedItem,
    final_dst: &Path,
    completed_bytes_base: u64,
    speed_ema: &mut f64,
    last_emit: &mut Instant,
) -> Result<(), String> {
    let cp_path = checkpoint_path(final_dst);
    let part = part_path(final_dst);

    let mut offset: u64 = 0;
    let mut resumed = false;

    if cp_path.exists() && part.exists() {
        if let Ok(bytes) = fs::read(&cp_path) {
            if let Ok(cp) = serde_json::from_slice::<Checkpoint>(&bytes) {
                let fingerprint_ok =
                    cp.src_size == item.size && cp.src_mtime_ms.abs_diff(item.mtime_ms) <= 2_000;
                if fingerprint_ok {
                    offset = cp.offset.min(item.size);
                    resumed = offset > 0;
                }
            }
        }
    }

    if !resumed {
        let _ = fs::remove_file(&cp_path);
        let _ = fs::remove_file(&part);
    }

    let mut src_file = retry_io(|| File::open(&item.src)).map_err(|e| e.to_string())?;
    if resumed {
        src_file
            .seek(SeekFrom::Start(offset))
            .map_err(|e| e.to_string())?;
    }

    let mut dst_file = retry_io(|| {
        OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(!resumed)
            .open(&part)
    })
    .map_err(|e| e.to_string())?;
    if resumed {
        dst_file
            .seek(SeekFrom::Start(offset))
            .map_err(|e| e.to_string())?;
    }

    let mut hasher = Xxh3::new();
    let mut buffer = vec![0u8; BUFFER_SIZE];
    let mut copied_this_session: u64 = 0;
    let mut since_checkpoint: u64 = 0;

    loop {
        if control.cancel.load(Ordering::Relaxed) {
            let cp = Checkpoint {
                job_id: job_id.to_string(),
                src: item.src.to_string_lossy().to_string(),
                dst: final_dst.to_string_lossy().to_string(),
                src_size: item.size,
                src_mtime_ms: item.mtime_ms,
                offset,
            };
            write_checkpoint_atomic(&cp, &cp_path);
            return Err("__cancelled__".to_string());
        }
        if !control.wait_while_paused() {
            return Err("__cancelled__".to_string());
        }

        let n = match src_file.read(&mut buffer) {
            Ok(0) => break,
            Ok(n) => n,
            Err(err) => {
                let msg = format!("{}: read failed: {}", item.src.display(), err);
                return Err(msg);
            }
        };

        let mut chunk = &buffer[..n];
        while !chunk.is_empty() {
            match dst_file.write(chunk) {
                Ok(written) => {
                    chunk = &chunk[written..];
                }
                Err(err) => {
                    let msg = format!("{}: write failed: {}", final_dst.display(), err);
                    return Err(msg);
                }
            }
        }

        if !resumed {
            hasher.update(&buffer[..n]);
        }
        offset += n as u64;
        copied_this_session += n as u64;
        since_checkpoint += n as u64;

        control.processed_bytes.store(
            completed_bytes_base + copied_this_session,
            Ordering::Relaxed,
        );

        let elapsed = last_emit.elapsed().as_millis();
        if elapsed >= PROGRESS_MIN_INTERVAL_MS {
            let instant_rate =
                n as f64 / (elapsed.max(1) as f64 / 1000.0);
            *speed_ema = 0.15 * instant_rate + 0.85 * *speed_ema;
            let total = control.total_bytes.load(Ordering::Relaxed);
            let done = completed_bytes_base + copied_this_session;
            let eta = if *speed_ema > 1.0 {
                (total.saturating_sub(done)) as f64 / *speed_ema
            } else {
                0.0
            };
            *control.speed_bps.lock() = *speed_ema;
            *control.eta_secs.lock() = eta;
            sink(JobEvent::Progress {
                job_id: job_id.to_string(),
                processed_bytes: done,
                processed_files: control.processed_files.load(Ordering::Relaxed),
                total_bytes: total,
                total_files: control.total_files.load(Ordering::Relaxed),
                speed_bps: *speed_ema,
                eta_secs: eta,
                current_file: Some(item.src.display().to_string()),
            });
            *last_emit = Instant::now();
        }

        if since_checkpoint >= CHECKPOINT_INTERVAL_BYTES {
            let cp = Checkpoint {
                job_id: job_id.to_string(),
                src: item.src.to_string_lossy().to_string(),
                dst: final_dst.to_string_lossy().to_string(),
                src_size: item.size,
                src_mtime_ms: item.mtime_ms,
                offset,
            };
            write_checkpoint_atomic(&cp, &cp_path);
            since_checkpoint = 0;
        }
    }

    let _ = dst_file.flush();
    // Fast path (small files): skip the per-file fsync. Crash safety is
    // preserved because content lands in `.nexuspart` and only reaches the
    // final name via atomic rename — a power cut can leave a junk part file
    // but never a torn final file.
    if !(small_fast_enabled() && item.size <= SMALL_FILE_FAST_MAX && !resumed) {
        let _ = dst_file.sync_data();
    }
    drop(dst_file);
    drop(src_file);
    #[cfg(windows)]
    preserve_windows_times(final_dst, item.ctime_ms, item.mtime_ms);

    if final_dst.exists() {
        let _ = remove_with_retry(final_dst);
    }
    retry_io(|| fs::rename(&part, final_dst)).map_err(|e| {
        format!("finalize {}: {}", final_dst.display(), e)
    })?;
    let _ = fs::remove_file(&cp_path);

    // Integrity verification (audit B10 fix): re-read both files and
    // compare streaming xxh3 digests. Runs for every completed file,
    // including resumed ones, unless NEXUS_NO_VERIFY=1 is set.
    if std::env::var("NEXUS_NO_VERIFY").ok().as_deref() != Some("1") {
        if small_fast_enabled() && item.size <= SMALL_FILE_FAST_MAX && !resumed {
            // Batched: verified together at end of job for better IO patterns.
            control
                .deferred_verify
                .lock()
                .push((item.src.to_path_buf(), final_dst.to_path_buf()));
            return Ok(());
        }
        if let Err(msg) = verify_copy(&item.src, final_dst) {
            return Err(msg);
        }
        sink(JobEvent::FileDone {
            job_id: job_id.to_string(),
            path: format!("{} [verified]", final_dst.display()),
            ok: true,
            error: None,
        });
        return Ok(());
    }

    if copied_this_session > 0 || resumed {
        sink(JobEvent::FileDone {
            job_id: job_id.to_string(),
            path: item.src.display().to_string(),
            ok: true,
            error: None,
        });
    }
    Ok(())
}

/// Streaming xxHash3-64 of a whole file (1 MiB chunks).
fn hash_file(path: &Path) -> io::Result<u64> {
    use std::io::Read;
    let mut f = File::open(path)?;
    let mut hasher = Xxh3::new();
    let mut buf = vec![0u8; 1024 * 1024];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hasher.digest())
}

// ─── Job journal (crash-recovery bookkeeping) ───────────────────────────────

#[derive(serde::Serialize, Clone)]
struct JournalRecord<'a> {
    ts_ms: u64,
    job_id: &'a str,
    kind: &'a str,
    state: &'a str,
    #[serde(skip_serializing_if = "Vec::is_empty")]
    sources: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    dest_dir: Option<&'a str>,
    pid: u32,
}

pub(crate) fn journal_dir() -> Option<std::path::PathBuf> {
    if let Ok(dir) = std::env::var("NEXUS_DATA_DIR") {
        if !dir.is_empty() {
            return Some(std::path::PathBuf::from(dir));
        }
    }
    std::env::var("LOCALAPPDATA")
        .ok()
        .map(|d| std::path::PathBuf::from(d).join("NexusExplorer"))
}

fn journal_append(
    job_id: &str,
    kind: &str,
    state: &str,
    sources: &[String],
    dest_dir: Option<&str>,
) {
    use std::io::Write;

    let Some(dir) = journal_dir() else { return };
    let _ = std::fs::create_dir_all(&dir);
    let rec = JournalRecord {
        ts_ms: now_ms(SystemTime::now()),
        job_id,
        kind,
        state,
        sources: sources.to_vec(),
        dest_dir,
        pid: std::process::id(),
    };
    let line = match serde_json::to_string(&rec) {
        Ok(l) => l,
        Err(_) => return,
    };
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("jobs.jsonl"))
    {
        let _ = writeln!(f, "{line}");
    }
}

/// One interrupted transfer artifact discovered via the journal.
#[derive(serde::Serialize, Clone)]
pub struct OrphanPart {
    pub job_id: String,
    pub kind: String,
    pub dst_dir: String,
    pub part_file: String,
    pub bytes: u64,
    pub last_state: String,
}

/// Scans the journal for non-completed transfers whose destination still
/// contains `.nexuspart` leftovers. Last record per job_id wins.
pub fn list_orphan_parts() -> Vec<OrphanPart> {
    use std::collections::HashMap;

    let Some(dir) = journal_dir() else { return Vec::new() };
    let Ok(text) = std::fs::read_to_string(dir.join("jobs.jsonl")) else {
        return Vec::new();
    };

    #[derive(serde::Deserialize)]
    struct Line {
        job_id: String,
        kind: String,
        state: String,
        #[serde(default)]
        dest_dir: Option<String>,
        #[serde(default)]
        pid: u32,
        #[serde(default)]
        ts_ms: u64,
    }

    let now = now_ms(SystemTime::now());
    let mut last_by_job: HashMap<String, Line> = HashMap::new();
    for line in text.lines() {
        if let Ok(rec) = serde_json::from_str::<Line>(line) {
            last_by_job.insert(rec.job_id.clone(), rec);
        }
    }

    let mut out = Vec::new();
    for (_id, rec) in last_by_job {
        if rec.state == "completed" {
            continue;
        }
        if rec.state == "running"
            && rec.pid == std::process::id()
            && now.saturating_sub(rec.ts_ms) < 120_000
        {
            // A job this process started recently: treat as live, not orphan.
            continue;
        }
        let Some(dst) = rec.dest_dir.clone() else { continue };
        let entries = match std::fs::read_dir(&dst) {
            Ok(e) => e,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let name = entry.file_name().to_string_lossy().into_owned();
            if name.ends_with(".nexuspart") {
                let bytes = entry.metadata().map(|m| m.len()).unwrap_or(0);
                out.push(OrphanPart {
                    job_id: rec.job_id.clone(),
                    kind: rec.kind.clone(),
                    dst_dir: dst.clone(),
                    part_file: entry.path().to_string_lossy().into_owned(),
                    bytes,
                    last_state: rec.state.clone(),
                });
            }
        }
    }
    out
}

/// Post-copy integrity check: source and destination must hash identically.
pub(crate) fn verify_copy(src: &Path, dst: &Path) -> Result<(), String> {
    let src_digest =
        hash_file(src).map_err(|e| format!("verify {}: {}", src.display(), e))?;
    let dst_digest =
        hash_file(dst).map_err(|e| format!("verify {}: {}", dst.display(), e))?;
    if src_digest != dst_digest {
        return Err(format!(
            "VERIFY_FAILED: {} (src xxh3 {:016x} != dst xxh3 {:016x}); \
             destination kept for inspection",
            dst.display(),
            src_digest,
            dst_digest
        ));
    }
    Ok(())
}

#[cfg(test)]
mod verify_tests {
    use super::*;

    #[test]
    fn verify_copy_accepts_identical_files() {
        let dir = std::env::temp_dir().join(format!(
            "nx_verify_ok_{}",
            uuid::Uuid::new_v4().simple()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let a = dir.join("a.bin");
        let b = dir.join("b.bin");
        let data: Vec<u8> = (0..256u32).map(|i| (i * 7 % 251) as u8).collect();
        for _ in 0..17 {
            std::fs::write(&a, &data).unwrap(); // > 4 MiB total
            let mut prev = std::fs::read(&a).unwrap();
            prev.extend_from_slice(&data);
            std::fs::write(&a, &prev).unwrap();
        }
        std::fs::copy(&a, &b).unwrap();
        assert!(verify_copy(&a, &b).is_ok());
        std::fs::remove_dir_all(&dir).ok();
    }

    #[test]
    fn verify_copy_rejects_corruption() {
        let dir = std::env::temp_dir().join(format!(
            "nx_verify_bad_{}",
            uuid::Uuid::new_v4().simple()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        let a = dir.join("a.bin");
        let b = dir.join("b.bin");
        let data = vec![0x5Au8; 5 * 1024 * 1024];
        std::fs::write(&a, &data).unwrap();
        std::fs::write(&b, &data).unwrap();
        // corrupt one byte deep inside the destination
        let mut bytes = std::fs::read(&b).unwrap();
        bytes[3 * 1024 * 1024] ^= 0xFF;
        std::fs::write(&b, &bytes).unwrap();
        let err = verify_copy(&a, &b).unwrap_err();
        assert!(err.starts_with("VERIFY_FAILED"), "got: {err}");
        std::fs::remove_dir_all(&dir).ok();
    }
}

fn transfer_one(
    kind: JobKind,
    control: &Arc<JobControl>,
    sink: &mut dyn FnMut(JobEvent),
    job_id: &str,
    item: &PlannedItem,
    completed_bytes_base: u64,
    speed_ema: &mut f64,
    last_emit: &mut Instant,
) -> Result<u64, bool> {
    // Returns Ok(bytes_added) or Err(cancelled)
    if item.is_dir {
        let _ = fs::create_dir_all(&item.dst);
        return Ok(0);
    }

    let mut dst = item.dst.clone();

    if dst.exists() {
        let existing = fs::metadata(&dst).ok();
        let (dest_size, dest_mtime) = existing
            .map(|m| (m.len(), now_ms(m.modified().unwrap_or(UNIX_EPOCH))))
            .unwrap_or((0, 0));

        let resolution = if let Some(applied) = control.apply_all.lock().clone() {
            applied
        } else {
            let conflict_id = uuid::Uuid::new_v4().to_string();
            let mut emit_conflict = |cid: &str| {
                sink(JobEvent::Conflict {
                    job_id: job_id.to_string(),
                    conflict_id: cid.to_string(),
                    source: item.src.display().to_string(),
                    destination: dst.display().to_string(),
                    source_size: item.size,
                    dest_size,
                    source_modified_ms: item.mtime_ms,
                    dest_modified_ms: dest_mtime,
                    is_dir: false,
                });
            };
            match await_conflict_resolution(control, &conflict_id, &mut emit_conflict)
            {
                Some(r) => r,
                None => return Err(true),
            }
        };

        match resolution.as_str() {
            "skip" => return Ok(0),
            "keepBoth" => dst = unique_sibling(&dst),
            _ => {}
        }
    }

    if kind == JobKind::Move {
        if fs::rename(&item.src, &dst).is_ok() {
            control.processed_bytes.store(
                completed_bytes_base + item.size,
                Ordering::Relaxed,
            );
            control.processed_files.fetch_add(1, Ordering::Relaxed);
            sink(JobEvent::FileDone {
                job_id: job_id.to_string(),
                path: item.src.display().to_string(),
                ok: true,
                error: None,
            });
            return Ok(item.size);
        }
    }

    match copy_one_file(
        control,
        sink,
        job_id,
        item,
        &dst,
        completed_bytes_base,
        speed_ema,
        last_emit,
    ) {
        Ok(()) => {
            if kind == JobKind::Move {
                if let Err(err) = remove_with_retry(&item.src) {
                    let msg = format!("{}: could not delete source: {}", item.src.display(), err);
                    control.errors.lock().push(msg.clone());
                    sink(JobEvent::Error {
                        job_id: job_id.to_string(),
                        message: msg,
                        path: Some(item.src.display().to_string()),
                    });
                }
            }
            Ok(item.size)
        }
        Err(msg) => {
            if msg == "__cancelled__" {
                return Err(true);
            }
            control.errors.lock().push(msg.clone());
            sink(JobEvent::Error {
                job_id: job_id.to_string(),
                message: msg.clone(),
                path: Some(item.src.display().to_string()),
            });
            sink(JobEvent::FileDone {
                job_id: job_id.to_string(),
                path: item.src.display().to_string(),
                ok: false,
                error: Some(msg),
            });
            Ok(0)
        }
    }
}

/// Runs a copy/move transfer to completion on the calling blocking thread, emitting progress via `sink`.
pub fn run_transfer_blocking(
    kind: JobKind,
    sources: Vec<String>,
    dest_dir: String,
    control: Arc<JobControl>,
    job_id: String,
    sink: &mut dyn FnMut(JobEvent),
) {
    journal_append(&job_id, kind.as_str(), "running", &sources, Some(&dest_dir));
    let (items, total_files, total_bytes, plan_errors) =
        plan_transfer(&sources, &dest_dir);
    control.total_files.store(total_files, Ordering::Relaxed);
    control.total_bytes.store(total_bytes, Ordering::Relaxed);
    sink(JobEvent::Started {
        job_id: job_id.clone(),
        kind: kind.as_str().to_string(),
        total_files,
        total_bytes,
    });

    for (path, message) in plan_errors {
        let msg = format!("{}: {}", path.display(), message);
        control.errors.lock().push(msg.clone());
        sink(JobEvent::Error {
            job_id: job_id.clone(),
            message: msg,
            path: Some(path.display().to_string()),
        });
    }

    if let Err(err) = fs::create_dir_all(&dest_dir) {
        control.set_state("failed");
        sink(JobEvent::Error {
            job_id: job_id.clone(),
            message: format!("cannot create destination {}: {}", dest_dir, err),
            path: Some(dest_dir),
        });
        sink(JobEvent::State {
            job_id: job_id.clone(),
            state: "failed".to_string(),
        });
        return;
    }

    let mut completed_bytes: u64 = 0;
    let mut speed_ema: f64 = 0.0;
    let mut last_emit = Instant::now() - Duration::from_millis(PROGRESS_MIN_INTERVAL_MS as u64);
    let mut cancelled = false;

    for item in &items {
        if control.cancel.load(Ordering::Relaxed) {
            cancelled = true;
            break;
        }
        *control.current_file.lock() = Some(item.src.display().to_string());

        if item.is_dir {
            let _ = fs::create_dir_all(&item.dst);
            continue;
        }

        match transfer_one(
            kind,
            &control,
            sink,
            &job_id,
            item,
            completed_bytes,
            &mut speed_ema,
            &mut last_emit,
        ) {
            Ok(added) => {
                completed_bytes += added;
                control.processed_files.fetch_add(1, Ordering::Relaxed);
                control
                    .processed_bytes
                    .store(completed_bytes, Ordering::Relaxed);
            }
            Err(was_cancelled) => {
                if was_cancelled {
                    cancelled = true;
                    break;
                }
            }
        }
    }

    // Batched verification for small-file fast-path copies.
    let deferred = std::mem::take(&mut *control.deferred_verify.lock());
    for (src_path, dst_path) in deferred {
        match verify_copy(&src_path, &dst_path) {
            Ok(()) => sink(JobEvent::FileDone {
                job_id: job_id.clone(),
                path: format!("{} [verified]", dst_path.display()),
                ok: true,
                error: None,
            }),
            Err(msg) => {
                control.errors.lock().push(msg.clone());
                sink(JobEvent::Error {
                    job_id: job_id.clone(),
                    message: msg.clone(),
                    path: Some(dst_path.display().to_string()),
                });
                sink(JobEvent::FileDone {
                    job_id: job_id.clone(),
                    path: dst_path.display().to_string(),
                    ok: false,
                    error: Some(msg),
                });
            }
        }
    }

    if cancelled {
        control.set_state("cancelled");
        journal_append(&job_id, kind.as_str(), "cancelled", &sources, Some(&dest_dir));
        sink(JobEvent::State {
            job_id: job_id.clone(),
            state: "cancelled".to_string(),
        });
    } else {
        let had_errors = !control.errors.lock().is_empty();
        let succeeded_any = control.processed_files.load(Ordering::Relaxed) > 0;
        let state = if had_errors && !succeeded_any {
            "failed"
        } else {
            "completed"
        };
        control.set_state(state);
        journal_append(&job_id, kind.as_str(), state, &sources, Some(&dest_dir));
        sink(JobEvent::State {
            job_id: job_id.clone(),
            state: state.to_string(),
        });
    }
}

fn remove_tree_progressive(
    root: &Path,
    control: &Arc<JobControl>,
    sink: &mut dyn FnMut(JobEvent),
    job_id: &str,
) -> io::Result<()> {
    if root.is_dir() {
        for entry in fs::read_dir(root)?.flatten() {
            if control.cancel.load(Ordering::Relaxed) {
                return Err(io::Error::new(io::ErrorKind::Interrupted, "cancelled"));
            }
            let path = entry.path();
            if path.is_dir() {
                remove_tree_progressive(&path, control, sink, job_id)?;
            } else {
                remove_with_retry(&path)?;
                control.processed_files.fetch_add(1, Ordering::Relaxed);
                sink(JobEvent::Progress {
                    job_id: job_id.to_string(),
                    processed_bytes: 0,
                    processed_files: control.processed_files.load(Ordering::Relaxed),
                    total_bytes: 0,
                    total_files: control.total_files.load(Ordering::Relaxed),
                    speed_bps: 0.0,
                    eta_secs: 0.0,
                    current_file: Some(path.display().to_string()),
                });
            }
        }
        clear_readonly(root);
        fs::remove_dir(root)
    } else {
        remove_with_retry(root)?;
        control.processed_files.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }
}

fn count_paths(paths: &[String]) -> (u64, u64) {
    let mut files = 0u64;
    let mut bytes = 0u64;
    for p in paths {
        let Ok(meta) = fs::metadata(p) else { continue };
        if meta.is_dir() {
            let walker = jwalk::WalkDir::new(p).skip_hidden(false);
            for entry in walker.into_iter().flatten() {
                if entry.file_type().is_file() {
                    files += 1;
                    bytes += entry
                        .metadata()
                        .ok()
                        .map(|m| m.len())
                        .unwrap_or(0);
                }
            }
        } else {
            files += 1;
            bytes += meta.len();
        }
    }
    (files, bytes)
}

/// Runs a delete (permanent or to-trash) over `paths` on the calling blocking thread, emitting progress via `sink`.
pub fn run_delete_blocking(
    paths: Vec<String>,
    to_trash: bool,
    control: Arc<JobControl>,
    job_id: String,
    sink: &mut dyn FnMut(JobEvent),
) {
    let (total_files, total_bytes) = count_paths(&paths);
    control.total_files.store(total_files, Ordering::Relaxed);
    control.total_bytes.store(total_bytes, Ordering::Relaxed);
    sink(JobEvent::Started {
        job_id: job_id.clone(),
        kind: "delete".to_string(),
        total_files,
        total_bytes,
    });

    let mut had_errors = false;
    let mut was_cancelled = false;

    if to_trash {
        let targets: Vec<PathBuf> = paths.iter().map(PathBuf::from).collect();
        for target in targets {
            if control.cancel.load(Ordering::Relaxed) {
                was_cancelled = true;
                break;
            }
            match trash::delete(&target) {
                Ok(()) => {
                    control.processed_files.fetch_add(1, Ordering::Relaxed);
                    sink(JobEvent::FileDone {
                        job_id: job_id.clone(),
                        path: target.display().to_string(),
                        ok: true,
                        error: None,
                    });
                }
                Err(err) => {
                    had_errors = true;
                    let msg = format!("{}: {}", target.display(), err);
                    control.errors.lock().push(msg.clone());
                    sink(JobEvent::Error {
                        job_id: job_id.clone(),
                        message: msg,
                        path: Some(target.display().to_string()),
                    });
                }
            }
        }
    } else {
        for raw in paths {
            if control.cancel.load(Ordering::Relaxed) {
                was_cancelled = true;
                break;
            }
            let path = PathBuf::from(raw);
            if let Err(err) = remove_tree_progressive(&path, &control, sink, &job_id) {
                if err.kind() == io::ErrorKind::Interrupted {
                    was_cancelled = true;
                    break;
                }
                had_errors = true;
                let msg = format!("{}: {}", path.display(), err);
                control.errors.lock().push(msg.clone());
                sink(JobEvent::Error {
                    job_id: job_id.clone(),
                    message: msg,
                    path: Some(path.display().to_string()),
                });
            }
        }
    }

    if was_cancelled {
        control.set_state("cancelled");
        sink(JobEvent::State {
            job_id: job_id.clone(),
            state: "cancelled".to_string(),
        });
    } else {
        let succeeded_any = control.processed_files.load(Ordering::Relaxed) > 0;
        let state = if had_errors && !succeeded_any {
            "failed"
        } else {
            "completed"
        };
        control.set_state(state);
        sink(JobEvent::State {
            job_id: job_id.clone(),
            state: state.to_string(),
        });
    }
}
