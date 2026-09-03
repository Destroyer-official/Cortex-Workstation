use libc::{c_char, c_int, c_void, c_double, size_t};
use std::sync::Arc;

use nexus_explorer_lib::engine::job_manager::{JobControl, JobManager};
use nexus_explorer_lib::engine::listing::ScanRegistry;
use nexus_explorer_lib::engine::search_engine::SearchRegistry;

mod ffi_types;
mod listing;
mod copy;
mod search;
mod watch;
mod drives;
mod utils;

pub use ffi_types::*;
pub use listing::*;
pub use copy::*;
pub use search::*;
pub use watch::*;
pub use drives::*;
pub use utils::*;

/// Opaque handle for async operations
pub type NexusHandle = *mut c_void;

/// Callback for directory listing batches
pub type ListCallback = extern "C" fn(
    user_data: *mut c_void,
    entries: *const FileEntry,
    count: size_t,
    done: c_int,
    error: *const c_char,
);

/// Callback for copy/move progress
pub type ProgressCallback = extern "C" fn(
    user_data: *mut c_void,
    job_id: *const c_char,
    processed_bytes: u64,
    total_bytes: u64,
    speed_bps: c_double,
    eta_seconds: c_double,
    current_file: *const c_char,
);

/// Callback for copy/move completion
pub type CompletionCallback = extern "C" fn(
    user_data: *mut c_void,
    job_id: *const c_char,
    success: c_int,
    error: *const c_char,
);

/// Callback for conflict resolution
pub type ConflictCallback = extern "C" fn(
    user_data: *mut c_void,
    job_id: *const c_char,
    conflict_id: *const c_char,
    source: *const c_char,
    destination: *const c_char,
    source_size: u64,
    dest_size: u64,
    source_mtime: u64,
    dest_mtime: u64,
    is_dir: c_int,
) -> c_int; // 0=skip, 1=overwrite, 2=keep_both, -1=cancel

/// Callback for search results
pub type SearchCallback = extern "C" fn(
    user_data: *mut c_void,
    entries: *const FileEntry,
    count: size_t,
    done: c_int,
    error: *const c_char,
);

/// Callback for filesystem events
pub type FsEventCallback = extern "C" fn(
    user_data: *mut c_void,
    path: *const c_char,
);

/// Initialize the engine, returns a context handle.
///
/// The returned handle must stay valid while any scan, search, watch or job
/// started from it may still invoke callbacks; free it with [`nexus_free`].
#[no_mangle]
pub unsafe extern "C" fn nexus_init() -> *mut c_void {
    let ctx = Arc::new(NexusContext::new());
    Arc::into_raw(ctx) as *mut c_void
}

/// Free the context handle
#[no_mangle]
pub unsafe extern "C" fn nexus_free(ctx: *mut c_void) {
    if !ctx.is_null() {
        drop(Arc::from_raw(ctx as *const NexusContext));
    }
}

/// Get version string
#[no_mangle]
pub extern "C" fn nexus_version() -> *const c_char {
    static VERSION: &str = concat!(env!("CARGO_PKG_VERSION"), "\0");
    VERSION.as_ptr() as *const c_char
}

pub(crate) struct NexusContext {
    pub job_manager: JobManager,
    pub scan_registry: ScanRegistry,
    pub search_registry: SearchRegistry,
    pub watchers: watch::WatcherMap,
}

impl NexusContext {
    fn new() -> Self {
        Self {
            job_manager: JobManager::new(),
            scan_registry: ScanRegistry::new(),
            search_registry: SearchRegistry::new(),
            watchers: watch::WatcherMap::new(),
        }
    }
}

/// Borrow the shared context behind a raw handle without touching the refcount.
///
/// The returned guard must not outlive the caller's use of `ctx`, and `ctx`
/// must have been produced by [`nexus_init`].
#[inline]
unsafe fn borrow_ctx(ctx: *mut c_void) -> std::mem::ManuallyDrop<Arc<NexusContext>> {
    debug_assert!(!ctx.is_null(), "null NexusContext handle");
    std::mem::ManuallyDrop::new(Arc::from_raw(ctx as *const NexusContext))
}

/// Wrapper making an opaque user-data pointer transferable across threads.
///
/// Safety contract: the caller guarantees the pointer stays valid for the
/// lifetime of every callback that may receive it (same rule as any C API).
#[repr(transparent)]
#[derive(Clone, Copy)]
pub(crate) struct SendPtr(pub *mut c_void);
unsafe impl Send for SendPtr {}

impl SendPtr {
    /// Whole-value accessor: closures must capture `SendPtr`, not its raw
    /// interior (Rust 2021 disjoint captures would otherwise grab `.0`).
    #[inline]
    pub(crate) fn get(self) -> *mut c_void {
        self.0
    }
}
