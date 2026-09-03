use super::*;
use libc::{c_char, c_int, c_uint, c_void, size_t};
use std::ffi::{CStr, CString};
use std::os::windows::fs::MetadataExt as _;
use std::ptr;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Instant, UNIX_EPOCH};

#[no_mangle]
pub unsafe extern "C" fn nexus_search_files(
    ctx: *mut c_void,
    root: *const c_char,
    query: *const c_char,
    options: *const SearchOptions,
    callback: SearchCallback,
    user_data: *mut c_void,
) -> c_int {
    if ctx.is_null() || root.is_null() || query.is_null() {
        return -1;
    }
    let _ctx = borrow_ctx(ctx);

    let root_str = match CStr::from_ptr(root).to_str() {
        Ok(r) => r,
        Err(_) => return -1,
    };
    let query_str = match CStr::from_ptr(query).to_str() {
        Ok(q) => q,
        Err(_) => return -1,
    };

    let opts = if options.is_null() {
        SearchOptions::default()
    } else {
        let opts = &*options;
        SearchOptions {
            recursive: opts.recursive,
            max_results: opts.max_results,
            include_hidden: opts.include_hidden,
        }
    };

    let search_id = uuid::Uuid::new_v4().to_string();
    let cancel = Arc::new(AtomicBool::new(false));
    {
        let ctx_ref = borrow_ctx(ctx);
        ctx_ref
            .search_registry
            .register(search_id.clone(), Arc::clone(&cancel));
        LAST_SEARCH_ID.with(|slot| *slot.borrow_mut() = Some(search_id.clone()));
    }

    let started = Instant::now();
    let total = Arc::new(std::sync::atomic::AtomicU64::new(0));
    let cb = callback;
    let ud = SendPtr(user_data);
    let registry_cleanup_ctx = borrow_ctx(ctx);
    let cleanup_id = search_id.clone();

    std::thread::spawn(move || {
        let result = std::panic::catch_unwind(move || {
            let root_path = std::path::PathBuf::from(root_str);
            if !root_path.exists() {
                let err = CString::new("root does not exist").unwrap_or_default();
                callback(ud.get(), ptr::null(), 0, 1, err.as_ptr());
                return;
            }

            let matcher = Matcher::new(query_str);
            let mut walker = jwalk::WalkDir::new(&root_path)
                .skip_hidden(opts.include_hidden == 0);
            if opts.recursive == 0 {
                walker = walker.min_depth(1).max_depth(1);
            }

            const BATCH_SIZE: usize = 200;
            let max_results = opts.max_results.max(1) as u64;
            let mut batch: Vec<FileEntry> = Vec::with_capacity(BATCH_SIZE);
            let mut total: u64 = 0;

            for entry in walker {
                if total >= max_results || cancel.load(Ordering::Relaxed) {
                    break;
                }
                let Ok(entry) = entry else { continue };
                if entry.depth() == 0 { continue; }
                let name = entry.file_name().to_string_lossy().to_string();
                if !matcher.matches(&name) { continue; }

                let meta = match entry.metadata() {
                    Ok(m) => m,
                    Err(_) => continue,
                };
                let ft = meta.file_type();
                let path = entry.path();
                let parent = path.parent()
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_default();
                let ext = std::path::Path::new(&name)
                    .extension()
                    .map(|e| e.to_string_lossy().to_lowercase())
                    .unwrap_or_default();
                let attrs = meta.file_attributes();

                let file_entry = FileEntry {
                    name: CString::new(name).unwrap_or_default().into_raw(),
                    path: CString::new(path.to_string_lossy().to_string())
                        .unwrap_or_default()
                        .into_raw(),
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

                batch.push(file_entry);
                total += 1;

                if batch.len() >= BATCH_SIZE {
                    let count = batch.len();
                    let ptr = Box::into_raw(batch.into_boxed_slice()) as *const FileEntry;
                    callback(ud.get(), ptr, count, 0, ptr::null());
                    batch = Vec::with_capacity(BATCH_SIZE);
                }
            }

            if !batch.is_empty() {
                let count = batch.len();
                let ptr = Box::into_raw(batch.into_boxed_slice()) as *const FileEntry;
                callback(ud.get(), ptr, count, 0, ptr::null());
            }

            let duration_ms = Instant::now().duration_since(started).as_millis() as u64;
            callback(ud.get(), ptr::null(), 0, 1, ptr::null());
        });

        if let Err(_) = result {
            let err = CString::new("search panicked").unwrap_or_default();
            callback(ud.get(), ptr::null(), 0, 1, err.as_ptr());
        }
        registry_cleanup_ctx.search_registry.remove(&cleanup_id);
    });

    0
}

thread_local! {
    static LAST_SEARCH_ID: std::cell::RefCell<Option<String>> =
        const { std::cell::RefCell::new(None) };
}

#[no_mangle]
pub unsafe extern "C" fn nexus_cancel_search(ctx: *mut c_void, search_id: *const c_char) -> c_int {
    if ctx.is_null() {
        return -1;
    }
    let ctx = borrow_ctx(ctx);
    if search_id.is_null() {
        let last = LAST_SEARCH_ID.with(|slot| slot.borrow().clone());
        return match last {
            Some(id) if ctx.search_registry.cancel(&id) => 0,
            _ => -1,
        };
    }
    let Ok(id) = CStr::from_ptr(search_id).to_str() else {
        return -1;
    };
    if ctx.search_registry.cancel(id) { 0 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn nexus_last_search_id(ctx: *mut c_void, out_id: *mut *mut c_char) -> c_int {
    if ctx.is_null() || out_id.is_null() {
        return -1;
    }
    match LAST_SEARCH_ID.with(|slot| slot.borrow().clone()) {
        Some(id) => {
            *out_id = CString::new(id).unwrap_or_default().into_raw();
            0
        }
        None => -1,
    }
}

struct Matcher {
    segments: Vec<String>,
    substring: Option<String>,
}

impl Matcher {
    fn new(query: &str) -> Self {
        let lowered = query.trim().to_lowercase();
        if lowered.contains('*') {
            let segments: Vec<String> = lowered
                .split('*')
                .filter(|s| !s.is_empty())
                .map(|s| s.to_string())
                .collect();
            Matcher { segments, substring: None }
        } else if lowered.is_empty() {
            Matcher { segments: Vec::new(), substring: None }
        } else {
            Matcher { segments: Vec::new(), substring: Some(lowered) }
        }
    }

    fn matches(&self, name: &str) -> bool {
        let lowered = name.to_lowercase();
        if let Some(sub) = &self.substring {
            return lowered.contains(sub);
        }
        if self.segments.is_empty() {
            return true;
        }
        let mut cursor = 0usize;
        for seg in &self.segments {
            match lowered[cursor..].find(seg) {
                Some(pos) => cursor = cursor + pos + seg.len(),
                None => return false,
            }
        }
        true
    }
}