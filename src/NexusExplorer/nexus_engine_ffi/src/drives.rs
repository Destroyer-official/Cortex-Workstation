use super::*;
use libc::{c_char, c_int, c_void, size_t};
use std::ffi::{CStr, CString};
use std::ptr;
use std::os::windows::ffi::OsStrExt;
use windows::core::PCWSTR;
use windows::Win32::Storage::FileSystem::{
    GetDiskFreeSpaceExW, GetDriveTypeW, GetLogicalDrives, GetVolumeInformationW,
};
use windows::Win32::System::Diagnostics::Debug::{SetErrorMode, SEM_FAILCRITICALERRORS};

struct ErrorModeGuard(windows::Win32::System::Diagnostics::Debug::THREAD_ERROR_MODE);

impl Drop for ErrorModeGuard {
    fn drop(&mut self) {
        unsafe { SetErrorMode(self.0) };
    }
}

#[no_mangle]
pub unsafe extern "C" fn nexus_get_drives(
    ctx: *mut c_void,
    out_drives: *mut *mut DriveInfo,
    out_count: *mut size_t,
) -> c_int {
    if ctx.is_null() || out_drives.is_null() || out_count.is_null() {
        return -1;
    }
    let _ctx = borrow_ctx(ctx);

    let _error_mode = ErrorModeGuard(unsafe { SetErrorMode(SEM_FAILCRITICALERRORS) });

    let letters_mask = unsafe { GetLogicalDrives() };
    if letters_mask == 0 {
        *out_count = 0;
        *out_drives = ptr::null_mut();
        return 0;
    }

    let mut drives_vec = Vec::new();

    for index in 0..26u32 {
        if letters_mask & (1 << index) == 0 {
            continue;
        }
        let letter = (b'A' + index as u8) as char;
        let root = format!("{}:\\", letter);
        let root_wide = to_wide_null_terminated(&root);
        let root_ptr = PCWSTR(root_wide.as_ptr());

        let drive_type = match unsafe { GetDriveTypeW(root_ptr) } {
            3 => "fixed",
            2 => "removable",
            4 => "network",
            5 => "cdrom",
            6 => "ramdisk",
            _ => "unknown",
        };

        let mut info = DriveInfo::default();
        info.path = CString::new(root).unwrap_or_default().into_raw();
        info.drive_type = CString::new(drive_type).unwrap_or_default().into_raw();
        info.label = ptr::null_mut();
        info.filesystem = ptr::null_mut();
        info.free_bytes = 0;
        info.total_bytes = 0;
        info.is_ready = 0;

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
            info.is_ready = 1;
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

        drives_vec.push(info);
    }

    let count = drives_vec.len();
    let boxed = drives_vec.into_boxed_slice();
    let ptr = Box::into_raw(boxed) as *mut DriveInfo;
    *out_drives = ptr;
    *out_count = count;

    0
}

#[no_mangle]
pub unsafe extern "C" fn nexus_free_drives(drives: *mut DriveInfo, count: size_t) {
    if drives.is_null() || count == 0 {
        return;
    }
    let slice = std::slice::from_raw_parts_mut(drives, count);
    for drive in slice {
        if !drive.path.is_null() { drop(CString::from_raw(drive.path)); }
        if !drive.label.is_null() { drop(CString::from_raw(drive.label)); }
        if !drive.drive_type.is_null() { drop(CString::from_raw(drive.drive_type)); }
        if !drive.filesystem.is_null() { drop(CString::from_raw(drive.filesystem)); }
    }
    let _ = Box::from_raw(std::slice::from_raw_parts_mut(drives, count) as *mut [DriveInfo]);
}

fn to_wide_null_terminated(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}

fn wide_to_string(buf: &[u16]) -> *mut c_char {
    let len = buf.iter().position(|&c| c == 0).unwrap_or(buf.len());
    let s = String::from_utf16_lossy(&buf[..len]);
    CString::new(s).unwrap_or_default().into_raw()
}

#[no_mangle]
pub unsafe extern "C" fn nexus_home_dir(
    ctx: *mut c_void,
    out_path: *mut *mut c_char,
) -> c_int {
    let _ctx = &*(ctx as *mut NexusContext);
    if out_path.is_null() {
        return -1;
    }
    let home = std::env::var("USERPROFILE").unwrap_or_else(|_| "C:\\".to_string());
    *out_path = CString::new(home).unwrap_or_default().into_raw();
    0
}

#[no_mangle]
pub unsafe extern "C" fn nexus_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        drop(CString::from_raw(ptr));
    }
}