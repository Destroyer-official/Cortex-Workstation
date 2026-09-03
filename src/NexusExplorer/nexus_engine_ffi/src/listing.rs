use super::*;
use libc::{c_char, c_int, c_void, size_t};
use std::ffi::{CStr, CString};
use std::ptr;
use std::slice;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use std::os::windows::fs::MetadataExt;
use uuid::Uuid;

/// Start a directory scan
#[no_mangle]
pub unsafe extern "C" fn nexus_scan_dir(
    ctx: *mut c_void,
    path: *const c_char,
    callback: ListCallback,
    user_data: *mut c_void,
) -> c_int {
    if ctx.is_null() {
        return -1;
    }
    let ctx = borrow_ctx(ctx);
    if path.is_null() {
        return -1;
    }
    let path = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };

    let scan_id = Uuid::new_v4().to_string();
    let cancel_flag = Arc::new(AtomicBool::new(false));
    ctx.scan_registry.insert(scan_id.clone(), cancel_flag.clone());

    let cancel = cancel_flag.clone();
    let cb = callback;
    let ud = SendPtr(user_data);
    let ctx_thread = Arc::clone(&ctx);

    let started = Instant::now();

    thread::spawn(move || {
        let result = std::panic::catch_unwind(move || {
            let mut entries_buffer = Vec::new();
            let mut local_count = 0u64;

            let read_dir = match std::fs::read_dir(path) {
                Ok(rd) => rd,
                Err(e) => {
                    let err = CString::new(e.to_string()).unwrap_or_default();
                    cb(ud.get(), ptr::null(), 0, 1, err.as_ptr());
                    return;
                }
            };

            for entry in read_dir {
                if cancel.load(Ordering::Relaxed) {
                    break;
                }
                let Ok(entry) = entry else { continue };
                let Ok(meta) = entry.metadata() else { continue };
                let Ok(ft) = entry.file_type() else { continue };

                let name = entry.file_name().to_string_lossy().into_owned();
                let entry_path = entry.path().to_string_lossy().into_owned();
                let parent = entry.path().parent()
                    .map(|p| p.to_string_lossy().into_owned())
                    .unwrap_or_default();

                let ext = std::path::Path::new(&name)
                    .extension()
                    .map(|e| e.to_string_lossy().to_lowercase())
                    .unwrap_or_default();

                let attrs = meta.file_attributes();
                let entry_ffi = FileEntry {
                    name: CString::new(name).unwrap_or_default().into_raw(),
                    path: CString::new(entry_path).unwrap_or_default().into_raw(),
                    parent_path: CString::new(parent).unwrap_or_default().into_raw(),
                    is_dir: if ft.is_dir() { 1 } else { 0 },
                    size: meta.len(),
                    modified_ms: meta.modified()
                        .ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                        .map(|d| d.as_millis() as u64).unwrap_or(0),
                    created_ms: meta.created()
                        .ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                        .map(|d| d.as_millis() as u64).unwrap_or(0),
                    is_hidden: if attrs & 0x2 != 0 { 1 } else { 0 },
                    is_system: if attrs & 0x4 != 0 { 1 } else { 0 },
                    is_readonly: if meta.permissions().readonly() { 1 } else { 0 },
                    ext: CString::new(ext).unwrap_or_default().into_raw(),
                };

                entries_buffer.push(entry_ffi);
                local_count += 1;

                if entries_buffer.len() >= 500 {
                    let batch = std::mem::take(&mut entries_buffer);
                    let count = batch.len();
                    let ptr = Box::into_raw(batch.into_boxed_slice()) as *const FileEntry;
                    cb(ud.get(), ptr, count, 0, ptr::null());
                }
            }

            // Send remaining
            if !entries_buffer.is_empty() {
                let count = entries_buffer.len();
                let ptr =
                    Box::into_raw(entries_buffer.into_boxed_slice()) as *const FileEntry;
                cb(ud.get(), ptr, count, 0, ptr::null());
            }

            let _ = local_count;
            cb(ud.get(), ptr::null(), 0, 1, ptr::null());
        });

        if let Err(_) = result {
            let err = CString::new("scan panicked").unwrap_or_default();
            cb(ud.get(), ptr::null(), 0, 1, err.as_ptr());
        }
        ctx_thread.scan_registry.remove(&scan_id);
    });

    0
}

#[no_mangle]
pub unsafe extern "C" fn nexus_cancel_scan(ctx: *mut c_void, scan_id: *const c_char) -> c_int {
    if ctx.is_null() || scan_id.is_null() {
        return -1;
    }
    let ctx = borrow_ctx(ctx);
    let id = match CStr::from_ptr(scan_id).to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };
    if ctx.scan_registry.cancel(id) {
        0
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn nexus_read_dir_sync(
    ctx: *mut c_void,
    path: *const c_char,
    out_entries: *mut *mut FileEntry,
    out_count: *mut size_t,
) -> c_int {
    if ctx.is_null() || path.is_null() || out_entries.is_null() || out_count.is_null() {
        return -1;
    }
    let _ctx = borrow_ctx(ctx);
    let path = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };

    let entries = match std::fs::read_dir(path) {
        Ok(rd) => rd,
        Err(_) => return -1,
    };

    let mut vec = Vec::new();
    for entry in entries.flatten() {
        let Ok(meta) = entry.metadata() else { continue };
        let Ok(ft) = entry.file_type() else { continue };

        let name = entry.file_name().to_string_lossy().into_owned();
        let entry_path = entry.path().to_string_lossy().into_owned();
        let parent = entry.path().parent()
            .map(|p| p.to_string_lossy().into_owned())
            .unwrap_or_default();

        let ext = std::path::Path::new(&name)
            .extension()
            .map(|e| e.to_string_lossy().to_lowercase())
            .unwrap_or_default();

        let attrs = meta.file_attributes();

        vec.push(FileEntry {
            name: CString::new(name).unwrap_or_default().into_raw(),
            path: CString::new(entry_path).unwrap_or_default().into_raw(),
            parent_path: CString::new(parent).unwrap_or_default().into_raw(),
            is_dir: if ft.is_dir() { 1 } else { 0 },
            size: meta.len(),
            modified_ms: meta.modified()
                .ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_millis() as u64).unwrap_or(0),
            created_ms: meta.created()
                .ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_millis() as u64).unwrap_or(0),
            is_hidden: if attrs & 0x2 != 0 { 1 } else { 0 },
            is_system: if attrs & 0x4 != 0 { 1 } else { 0 },
            is_readonly: if meta.permissions().readonly() { 1 } else { 0 },
            ext: CString::new(ext).unwrap_or_default().into_raw(),
        });
    }

    let count = vec.len();
    let boxed = vec.into_boxed_slice();
    let ptr = Box::into_raw(boxed) as *mut FileEntry;
    *out_entries = ptr;
    *out_count = count;

    0
}

/// Synchronous directory listing serialized to JSON by the engine itself.
///
/// Avoids per-row FFI struct marshaling on the consumer side: one UTF-8
/// JSON array is returned (same shape as the CLI --json output). The
/// returned string must be freed with nexus_free_string.
#[no_mangle]
pub unsafe extern "C" fn nexus_read_dir_sync_json(
    ctx: *mut c_void,
    path: *const c_char,
    out_json: *mut *mut c_char,
) -> c_int {
    if ctx.is_null() || path.is_null() || out_json.is_null() {
        return -1;
    }
    let _ctx = borrow_ctx(ctx);
    let path = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };

    let read_dir = match std::fs::read_dir(path) {
        Ok(rd) => rd,
        Err(_) => return -1,
    };

    let mut entries: Vec<nexus_explorer_lib::models::FileEntry> = Vec::new();
    for entry in read_dir.flatten() {
        let Ok(meta) = entry.metadata() else { continue };
        let Ok(ft) = entry.file_type() else { continue };
        let name = entry.file_name().to_string_lossy().into_owned();
        let entry_path = entry.path().to_string_lossy().into_owned();
        let parent = entry
            .path()
            .parent()
            .map(|p| p.to_string_lossy().into_owned())
            .unwrap_or_default();
        let attrs = meta.file_attributes();
        let ext = std::path::Path::new(&name)
            .extension()
            .map(|e| e.to_string_lossy().to_lowercase())
            .unwrap_or_default();
        entries.push(nexus_explorer_lib::models::FileEntry {
            name,
            path: entry_path,
            parent_path: parent,
            is_dir: ft.is_dir(),
            size: meta.len(),
            modified_ms: meta
                .modified()
                .ok()
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0),
            created_ms: meta
                .created()
                .ok()
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0),
            is_hidden: attrs & 0x2 != 0,
            is_system: attrs & 0x4 != 0,
            is_readonly: meta.permissions().readonly(),
            ext,
        });
    }

    match serde_json::to_string(&entries) {
        Ok(json) => {
            *out_json = CString::new(json).unwrap_or_default().into_raw();
            0
        }
        Err(_) => -1,
    }
}

#[no_mangle]
pub unsafe extern "C" fn nexus_free_entries(entries: *mut FileEntry, count: size_t) {
    if entries.is_null() || count == 0 {
        return;
    }
    let slice = std::slice::from_raw_parts_mut(entries, count);
    for entry in slice.iter() {
        if !entry.name.is_null() { drop(CString::from_raw(entry.name)); }
        if !entry.path.is_null() { drop(CString::from_raw(entry.path)); }
        if !entry.parent_path.is_null() { drop(CString::from_raw(entry.parent_path)); }
        if !entry.ext.is_null() { drop(CString::from_raw(entry.ext)); }
    }
    drop(Box::from_raw(slice as *mut [FileEntry]));
}