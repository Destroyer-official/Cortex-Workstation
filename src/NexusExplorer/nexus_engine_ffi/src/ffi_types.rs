use libc::{c_char, c_int, c_uint, c_ulonglong, c_void, size_t};
use std::ptr;

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct FileEntry {
    pub name: *mut c_char,
    pub path: *mut c_char,
    pub parent_path: *mut c_char,
    pub is_dir: c_int,
    pub size: c_ulonglong,
    pub modified_ms: c_ulonglong,
    pub created_ms: c_ulonglong,
    pub is_hidden: c_int,
    pub is_system: c_int,
    pub is_readonly: c_int,
    pub ext: *mut c_char,
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct DriveInfo {
    pub path: *mut c_char,
    pub label: *mut c_char,
    pub drive_type: *mut c_char,
    pub filesystem: *mut c_char,
    pub free_bytes: c_ulonglong,
    pub total_bytes: c_ulonglong,
    pub is_ready: c_int,
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct SearchOptions {
    pub recursive: c_int,
    pub max_results: c_uint,
    pub include_hidden: c_int,
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct TextPreview {
    pub content: *mut c_char,
    pub truncated: c_int,
    pub size: c_ulonglong,
}

#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct JobSummary {
    pub job_id: *mut c_char,
    pub kind: *mut c_char,
    pub state: *mut c_char,
    pub total_files: c_ulonglong,
    pub processed_files: c_ulonglong,
    pub total_bytes: c_ulonglong,
    pub processed_bytes: c_ulonglong,
    pub speed_bps: c_double,
    pub eta_seconds: c_double,
    pub current_file: *mut c_char,
    pub conflicts_pending: c_uint,
}

type c_double = f64;

impl Default for FileEntry {
    fn default() -> Self {
        Self {
            name: ptr::null_mut(),
            path: ptr::null_mut(),
            parent_path: ptr::null_mut(),
            is_dir: 0,
            size: 0,
            modified_ms: 0,
            created_ms: 0,
            is_hidden: 0,
            is_system: 0,
            is_readonly: 0,
            ext: ptr::null_mut(),
        }
    }
}

impl Default for DriveInfo {
    fn default() -> Self {
        Self {
            path: ptr::null_mut(),
            label: ptr::null_mut(),
            drive_type: ptr::null_mut(),
            filesystem: ptr::null_mut(),
            free_bytes: 0,
            total_bytes: 0,
            is_ready: 0,
        }
    }
}

impl Default for SearchOptions {
    fn default() -> Self {
        Self {
            recursive: 1,
            max_results: 10000,
            include_hidden: 0,
        }
    }
}

impl Default for TextPreview {
    fn default() -> Self {
        Self {
            content: ptr::null_mut(),
            truncated: 0,
            size: 0,
        }
    }
}

impl Default for JobSummary {
    fn default() -> Self {
        Self {
            job_id: ptr::null_mut(),
            kind: ptr::null_mut(),
            state: ptr::null_mut(),
            total_files: 0,
            processed_files: 0,
            total_bytes: 0,
            processed_bytes: 0,
            speed_bps: 0.0,
            eta_seconds: 0.0,
            current_file: ptr::null_mut(),
            conflicts_pending: 0,
        }
    }
}