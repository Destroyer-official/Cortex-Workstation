use super::*;
use libc::{c_char, c_int, c_void};
use std::ffi::{CStr, CString};
use std::ptr;

/// Renames `path` to `new_name` within the same parent directory.
#[no_mangle]
pub unsafe extern "C" fn nexus_rename(
    ctx: *mut c_void,
    path: *const c_char,
    new_name: *const c_char,
) -> c_int {
    let _ctx = borrow_ctx(ctx);
    if path.is_null() || new_name.is_null() {
        return -1;
    }
    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };
    let new_name_str = match CStr::from_ptr(new_name).to_str() {
        Ok(n) => n,
        Err(_) => return -1,
    };

    let src = std::path::Path::new(path_str);
    let parent = src.parent().unwrap_or_else(|| std::path::Path::new(""));
    let dest = parent.join(new_name_str);

    match std::fs::rename(src, &dest) {
        Ok(_) => 0,
        Err(_) => -1,
    }
}

/// Creates a single folder `name` inside existing `parent`.
#[no_mangle]
pub unsafe extern "C" fn nexus_create_folder(
    ctx: *mut c_void,
    parent: *const c_char,
    name: *const c_char,
) -> c_int {
    let _ctx = borrow_ctx(ctx);
    if parent.is_null() || name.is_null() {
        return -1;
    }
    let parent_str = match CStr::from_ptr(parent).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };
    let name_str = match CStr::from_ptr(name).to_str() {
        Ok(n) => n,
        Err(_) => return -1,
    };

    let path = std::path::Path::new(parent_str).join(name_str);
    match std::fs::create_dir(&path) {
        Ok(_) => 0,
        Err(_) => -1,
    }
}

/// Reads up to `max_bytes` of a text file, reporting truncation and total size via out-params.
#[no_mangle]
pub unsafe extern "C" fn nexus_read_text_file(
    ctx: *mut c_void,
    path: *const c_char,
    max_bytes: u32,
    out_content: *mut *mut c_char,
    out_truncated: *mut c_int,
    out_size: *mut u64,
) -> c_int {
    let _ctx = borrow_ctx(ctx);
    if path.is_null() || out_content.is_null() || out_truncated.is_null() || out_size.is_null() {
        return -1;
    }

    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };

    let meta = match std::fs::metadata(path_str) {
        Ok(m) => m,
        Err(_) => return -1,
    };

    let size = meta.len();
    let max = max_bytes as usize;
    let read_size = std::cmp::min(size as usize, max);

    let mut file = match std::fs::File::open(path_str) {
        Ok(f) => f,
        Err(_) => return -1,
    };

    use std::io::Read;
    let mut buffer = vec![0u8; read_size];
    let read = match file.read(&mut buffer) {
        Ok(n) => n,
        Err(_) => return -1,
    };

    buffer.truncate(read);
    let content = String::from_utf8_lossy(&buffer).into_owned();
    let truncated = if size > max as u64 { 1 } else { 0 };

    let (safe_content, hit_nul) = match content.find('\0') {
        Some(pos) => (content[..pos].to_string(), true),
        None => (content, false),
    };
    let truncated = if hit_nul { 1 } else { truncated };

    *out_content = CString::new(safe_content)
        .unwrap_or_default()
        .into_raw();
    *out_truncated = truncated;
    *out_size = size;

    0
}

/// Opens `path` with the OS default handler (Explorer on Windows, xdg-open elsewhere).
#[no_mangle]
pub unsafe extern "C" fn nexus_open_path(ctx: *mut c_void, path: *const c_char) -> c_int {
    let _ctx = borrow_ctx(ctx);
    if path.is_null() { return -1; }
    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let flags = 0x00000008 | 0x00000200; // DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        std::process::Command::new("explorer.exe")
            .arg(path_str)
            .creation_flags(flags)
            .spawn()
            .map(|_| 0)
            .unwrap_or(-1)
    }
    #[cfg(not(windows))]
    {
        std::process::Command::new("xdg-open")
            .arg(path_str)
            .spawn()
            .map(|_| 0)
            .unwrap_or(-1)
    }
}

/// Reveals `path` selected in the OS shell (Explorer `/select` on Windows; unsupported elsewhere).
#[no_mangle]
pub unsafe extern "C" fn nexus_reveal_in_shell(ctx: *mut c_void, path: *const c_char) -> c_int {
    let _ctx = borrow_ctx(ctx);
    if path.is_null() { return -1; }
    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        let flags = 0x00000008 | 0x00000200;
        std::process::Command::new("explorer.exe")
            .arg(format!("/select,{}", path_str))
            .creation_flags(flags)
            .spawn()
            .map(|_| 0)
            .unwrap_or(-1)
    }
    #[cfg(not(windows))]
    {
        -1
    }
}
/// Serializes interrupted-transfer `.nexuspart` orphans from the job journal as a JSON array.
#[no_mangle]
pub unsafe extern "C" fn nexus_orphans_json(out_json: *mut *mut c_char) -> c_int {
    if out_json.is_null() {
        return -1;
    }
    let list = nexus_explorer_lib::engine::copy_engine::list_orphan_parts();
    match serde_json::to_string(&list) {
        Ok(s) => {
            *out_json = CString::new(s).unwrap_or_default().into_raw();
            0
        }
        Err(_) => -1,
    }
}
