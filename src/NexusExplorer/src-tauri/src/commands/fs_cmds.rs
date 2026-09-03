//! Filesystem commands: directory scanning, listing, drives, and misc file operations.

use std::fs;
use std::io::{self, Read};
use std::os::windows::fs::MetadataExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Instant, UNIX_EPOCH};

use tauri::ipc::Channel;
use tauri::{AppHandle, State};
use tauri_plugin_opener::OpenerExt;
use windows::core::PCWSTR;
use windows::Win32::Storage::FileSystem::{
    GetDiskFreeSpaceExW, GetDriveTypeW, GetLogicalDrives, GetVolumeInformationW,
};
use windows::Win32::System::Diagnostics::Debug::{SetErrorMode, SEM_FAILCRITICALERRORS};

use crate::engine::listing::ScanRegistry;
use crate::engine::watch::WatchManager;
use crate::models::{DriveInfo, FileEntry, ScanEvent, ScanStart, TextPreview};

const BATCH_SIZE: usize = 500;
const BINARY_PROBE_LEN: usize = 8 * 1024;
const FILE_ATTRIBUTE_HIDDEN: u32 = 0x2;
const FILE_ATTRIBUTE_SYSTEM: u32 = 0x4;
const INVALID_NAME_CHARS: &[char] = &['<', '>', ':', '"', '/', '\\', '|', '?', '*'];

/// Starts an asynchronous directory scan, streaming sorted batches over `on_event`.
#[tauri::command]
pub async fn scan_dir(
    path: String,
    on_event: Channel<ScanEvent>,
    registry: State<'_, ScanRegistry>,
) -> Result<ScanStart, String> {
    if path.trim().is_empty() {
        return Err("path must not be empty".to_string());
    }
    let scan_id = uuid::Uuid::new_v4().to_string();
    let flag = Arc::new(AtomicBool::new(false));
    registry.insert(scan_id.clone(), Arc::clone(&flag));
    let reg = registry.inner().clone();
    let channel = on_event.clone();
    let root = path.clone();
    let id_for_task = scan_id.clone();
    tokio::task::spawn(async move {
        let channel_inner = channel.clone();
        let result =
            tokio::task::spawn_blocking(move || run_scan(&root, &channel_inner, &flag)).await;
        reg.remove(&id_for_task);
        if let Err(join_err) = result {
            let _ = channel.send(ScanEvent::Error {
                message: format!("scan task failed: {}", join_err),
            });
        }
    });
    Ok(ScanStart {
        scan_id,
        root_path: path,
    })
}

/// Cancels a previously started scan by id.
#[tauri::command]
pub async fn cancel_scan(scan_id: String, registry: State<'_, ScanRegistry>) -> Result<(), String> {
    if registry.cancel(&scan_id) {
        Ok(())
    } else {
        Err(format!("no active scan with id '{}'", scan_id))
    }
}

/// Lists a directory synchronously, sorted dirs-first then by name.
#[tauri::command]
pub async fn read_dir_sync(path: String) -> Result<Vec<FileEntry>, String> {
    if path.trim().is_empty() {
        return Err("path must not be empty".to_string());
    }
    collect_sorted_entries(&path).map_err(|e| format!("failed to list '{}': {}", path, e))
}

/// Synchronous directory listing shared with the nexus-cli binary.
pub fn __cli_read_dir(path: &str) -> Result<Vec<FileEntry>, String> {
    if path.trim().is_empty() {
        return Err("path must not be empty".to_string());
    }
    collect_sorted_entries(path).map_err(|e| format!("failed to list '{}': {}", path, e))
}

/// Returns metadata for a path, or None if it does not exist.
#[tauri::command]
pub async fn stat_path(path: String) -> Result<Option<FileEntry>, String> {
    if path.trim().is_empty() {
        return Err("path must not be empty".to_string());
    }
    let target = PathBuf::from(&path);
    match fs::metadata(&target) {
        Ok(metadata) => {
            let name = target
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_else(|| path.clone());
            Ok(Some(build_file_entry(
                name,
                path,
                parent_of(&target),
                &metadata,
            )))
        }
        Err(err) if err.kind() == io::ErrorKind::NotFound => Ok(None),
        Err(err) => Err(format!("failed to stat '{}': {}", path, err)),
    }
}

/// Enumerates all available Windows drive letters with volume details.
#[tauri::command]
pub async fn get_drives() -> Result<Vec<DriveInfo>, String> {
    Ok(enumerate_drives())
}

/// Returns the current user's home directory.
#[tauri::command]
pub async fn home_dir() -> Result<String, String> {
    std::env::var("USERPROFILE")
        .map_err(|_| "USERPROFILE environment variable not found".to_string())
}

/// Renames a filesystem entry and returns its refreshed metadata.
#[tauri::command]
pub async fn rename_entry(path: String, new_name: String) -> Result<FileEntry, String> {
    validate_name(&new_name)?;
    let source = PathBuf::from(&path);
    let parent = source
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| format!("cannot determine parent of '{}'", path))?;
    let destination = parent.join(&new_name);
    fs::rename(&source, &destination).map_err(|e| {
        format!(
            "failed to rename '{}' to '{}': {}",
            path,
            destination.display(),
            e
        )
    })?;
    stat_existing(&destination)
}

/// Creates a folder and returns its entry.
#[tauri::command]
pub async fn create_folder(parent: String, name: String) -> Result<FileEntry, String> {
    validate_name(&name)?;
    let target = PathBuf::from(&parent).join(&name);
    fs::create_dir(&target).map_err(|e| {
        format!(
            "failed to create folder '{}': {}",
            target.display(),
            e
        )
    })?;
    stat_existing(&target)
}

/// Reads up to `max_bytes` of a text file for preview purposes.
#[tauri::command]
pub async fn read_text_file(path: String, max_bytes: u32) -> Result<TextPreview, String> {
    let metadata = fs::metadata(&path).map_err(|e| format!("failed to stat '{}': {}", path, e))?;
    let size = metadata.len();
    let limit = (max_bytes as u64).min(size) as usize;
    let mut file =
        fs::File::open(&path).map_err(|e| format!("failed to open '{}': {}", path, e))?;
    let mut buffer = vec![0u8; limit];
    let mut read_total = 0usize;
    while read_total < limit {
        let read_now = file
            .read(&mut buffer[read_total..])
            .map_err(|e| format!("failed to read '{}': {}", path, e))?;
        if read_now == 0 {
            break;
        }
        read_total += read_now;
    }
    buffer.truncate(read_total);
    let probe_end = buffer.len().min(BINARY_PROBE_LEN);
    if buffer[..probe_end].contains(&0) {
        return Err("binary file".to_string());
    }
    Ok(TextPreview {
        content: String::from_utf8_lossy(&buffer).into_owned(),
        truncated: size > max_bytes as u64,
        size,
    })
}

/// Opens a path with the system default application.
#[tauri::command]
pub async fn open_path(app: AppHandle, path: String) -> Result<(), String> {
    let display = path.clone();
    app.opener()
        .open_path(path, None::<&str>)
        .map_err(|e| format!("failed to open '{}': {}", display, e))
}

/// Reveals a path in Windows Explorer, selecting the item.
#[tauri::command]
pub async fn reveal_in_shell(path: String) -> Result<(), String> {
    std::process::Command::new("explorer")
        .arg(format!("/select,{}", path))
        .spawn()
        .map_err(|e| format!("failed to launch explorer: {}", e))?;
    Ok(())
}

/// Starts watching a directory for changes.
#[tauri::command]
pub async fn watch_dir(
    app: AppHandle,
    path: String,
    watcher: State<'_, WatchManager>,
) -> Result<(), String> {
    watcher.watch(app, path)
}

/// Stops watching a previously watched directory.
#[tauri::command]
pub async fn unwatch_dir(path: String, watcher: State<'_, WatchManager>) -> Result<(), String> {
    watcher.unwatch(path)
}

fn run_scan(root: &str, channel: &Channel<ScanEvent>, cancel: &AtomicBool) {
    let started = Instant::now();
    let entries = match collect_sorted_entries(root) {
        Ok(entries) => entries,
        Err(err) => {
            let _ = channel.send(ScanEvent::Error {
                message: format!("scan failed for '{}': {}", root, err),
            });
            return;
        }
    };
    let total = entries.len() as u64;
    for chunk in entries.chunks(BATCH_SIZE) {
        if cancel.load(Ordering::SeqCst) {
            return;
        }
        if channel
            .send(ScanEvent::Batch {
                entries: chunk.to_vec(),
            })
            .is_err()
        {
            return;
        }
    }
    let _ = channel.send(ScanEvent::Done {
        total,
        duration_ms: started.elapsed().as_millis() as u64,
    });
}

fn collect_sorted_entries(root: &str) -> io::Result<Vec<FileEntry>> {
    let mut entries = Vec::new();
    for item in fs::read_dir(root)? {
        match item {
            Ok(de) => {
                if let Ok(entry) = dir_entry_to_file_entry(&de) {
                    entries.push(entry);
                }
            }
            Err(err) => return Err(err),
        }
    }
    sort_entries_dirs_first(&mut entries);
    Ok(entries)
}

fn dir_entry_to_file_entry(de: &fs::DirEntry) -> io::Result<FileEntry> {
    let metadata = de.metadata()?;
    let name = de.file_name().to_string_lossy().into_owned();
    let full_path = de.path();
    let path = full_path.to_string_lossy().into_owned();
    let parent_path = full_path
        .parent()
        .map(|p| p.to_string_lossy().into_owned())
        .unwrap_or_else(|| path.clone());
    Ok(build_file_entry(name, path, parent_path, &metadata))
}

fn build_file_entry(
    name: String,
    path: String,
    parent_path: String,
    metadata: &fs::Metadata,
) -> FileEntry {
    let attributes = metadata.file_attributes();
    let ext = Path::new(&name)
        .extension()
        .map(|e| e.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    FileEntry {
        is_dir: metadata.is_dir(),
        size: metadata.len(),
        modified_ms: system_time_to_epoch_ms(metadata.modified()),
        created_ms: system_time_to_epoch_ms(metadata.created()),
        is_hidden: attributes & FILE_ATTRIBUTE_HIDDEN != 0,
        is_system: attributes & FILE_ATTRIBUTE_SYSTEM != 0,
        is_readonly: metadata.permissions().readonly(),
        name,
        path,
        parent_path,
        ext,
    }
}

fn sort_entries_dirs_first(entries: &mut [FileEntry]) {
    entries.sort_by(|a, b| {
        b.is_dir
            .cmp(&a.is_dir)
            .then_with(|| a.name.to_lowercase().cmp(&b.name.to_lowercase()))
    });
}

fn system_time_to_epoch_ms(time: io::Result<std::time::SystemTime>) -> u64 {
    time.ok()
        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

fn parent_of(path: &Path) -> String {
    path.parent()
        .map(|p| p.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn stat_existing(target: &Path) -> Result<FileEntry, String> {
    let metadata = fs::metadata(target)
        .map_err(|e| format!("failed to stat '{}': {}", target.display(), e))?;
    let name = target
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .ok_or_else(|| format!("path '{}' has no file name component", target.display()))?;
    Ok(build_file_entry(
        name,
        target.to_string_lossy().into_owned(),
        parent_of(target),
        &metadata,
    ))
}

fn validate_name(name: &str) -> Result<(), String> {
    if name.is_empty() {
        return Err("name must not be empty".to_string());
    }
    if name == "." || name == ".." {
        return Err(format!("invalid name '{}'", name));
    }
    if name
        .chars()
        .any(|c| INVALID_NAME_CHARS.contains(&c) || c.is_control())
    {
        return Err(format!("name contains invalid characters: '{}'", name));
    }
    if name.ends_with('.') || name.ends_with(' ') {
        return Err(format!(
            "name must not end with a dot or space: '{}'",
            name
        ));
    }
    Ok(())
}

/// Restores the previous process error mode when dropped.
struct ErrorModeGuard(windows::Win32::System::Diagnostics::Debug::THREAD_ERROR_MODE);

impl Drop for ErrorModeGuard {
    fn drop(&mut self) {
        unsafe {
            SetErrorMode(self.0);
        }
    }
}

fn enumerate_drives() -> Vec<DriveInfo> {
    let mut drives = Vec::new();
    // Suppress the system modal "no disk"/"insert media" dialogs: without this,
    // probing an empty card reader or CD drive can freeze the whole app behind
    // a hidden blocking dialog.
    let _error_mode_guard = ErrorModeGuard(unsafe { SetErrorMode(SEM_FAILCRITICALERRORS) });
    let letters_mask = unsafe { GetLogicalDrives() };
    if letters_mask == 0 {
        return drives;
    }
    for index in 0..26u32 {
        if letters_mask & (1 << index) == 0 {
            continue;
        }
        let letter = (b'A' + index as u8) as char;
        let root = format!("{}:\\", letter);
        let root_wide = to_wide_null_terminated(&root);
        let root_ptr = PCWSTR(root_wide.as_ptr());
        let Some(drive_type) = map_drive_type(unsafe { GetDriveTypeW(root_ptr) }) else {
            continue;
        };
        let mut info = DriveInfo {
            path: root,
            label: String::new(),
            drive_type: drive_type.to_string(),
            filesystem: String::new(),
            free_bytes: 0,
            total_bytes: 0,
            is_ready: false,
        };
        let mut label_buf = [0u16; 261];
        let mut fs_buf = [0u16; 65];
        let volume_ok = unsafe {
            GetVolumeInformationW(
                root_ptr,
                Some(&mut label_buf),
                None,
                None,
                None,
                Some(&mut fs_buf),
            )
        };
        if volume_ok.is_ok() {
            info.is_ready = true;
            info.label = wide_to_string(&label_buf);
            info.filesystem = wide_to_string(&fs_buf);
            let mut free_available: u64 = 0;
            let mut total_bytes: u64 = 0;
            let mut free_bytes: u64 = 0;
            let space_ok = unsafe {
                GetDiskFreeSpaceExW(
                    root_ptr,
                    Some(&mut free_available),
                    Some(&mut total_bytes),
                    Some(&mut free_bytes),
                )
            };
            if space_ok.is_ok() {
                info.free_bytes = free_bytes;
                info.total_bytes = total_bytes;
            }
        }
        drives.push(info);
    }
    drives
}

fn map_drive_type(kind: u32) -> Option<&'static str> {
    match kind {
        2 => Some("removable"),
        3 => Some("fixed"),
        4 => Some("network"),
        5 => Some("cdrom"),
        6 => Some("ramdisk"),
        0 | 1 => None,
        _ => Some("unknown"),
    }
}

fn to_wide_null_terminated(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}

fn wide_to_string(buf: &[u16]) -> String {
    let len = buf.iter().position(|&c| c == 0).unwrap_or(buf.len());
    String::from_utf16_lossy(&buf[..len])
}
