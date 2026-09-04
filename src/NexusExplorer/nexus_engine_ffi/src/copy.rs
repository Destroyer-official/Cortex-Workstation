use super::*;
use libc::{c_char, c_int, c_void, size_t};
use std::ffi::{CStr, CString};
use std::ptr;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use nexus_explorer_lib::engine::copy_engine::{
    run_transfer_blocking, run_delete_blocking, JobKind,
};
use nexus_explorer_lib::engine::job_manager::JobControl;
use nexus_explorer_lib::models::JobEvent;

type JobHandleInner = (Arc<JobControl>, Arc<AtomicBool>, Arc<AtomicBool>);

fn collect_strings(
    items: *const *const c_char,
    count: size_t,
) -> Vec<String> {
    if items.is_null() || count == 0 {
        return Vec::new();
    }
    let slice = unsafe { std::slice::from_raw_parts(items, count) };
    let mut out = Vec::with_capacity(count);
    for &item in slice {
        if item.is_null() {
            continue;
        }
        if let Ok(s) = unsafe { CStr::from_ptr(item).to_str() } {
            out.push(s.to_string());
        }
    }
    out
}

fn start_job_thread<F: FnOnce() + Send + 'static>(worker: F) {
    std::thread::spawn(move || {
        let result =
            std::panic::catch_unwind(std::panic::AssertUnwindSafe(worker));
        if let Err(payload) = result {
            let msg = payload
                .downcast_ref::<String>()
                .cloned()
                .or_else(|| payload.downcast_ref::<&str>().map(|s| s.to_string()))
                .unwrap_or_else(|| "unknown panic".to_string());
            eprintln!("nexus_engine ffi job panicked: {msg}");
        }
    });
}

struct FfiSink {
    job_id: String,
    progress_cb: ProgressCallback,
    complete_cb: CompletionCallback,
    conflict_cb: ConflictCallback,
    user_data: SendPtr,
    control: Arc<JobControl>,
}

impl FfiSink {
    fn emit(&mut self, event: JobEvent) {
        match event {
            JobEvent::Started { .. } => {}

            JobEvent::Progress {
                processed_bytes,
                total_bytes,
                speed_bps,
                eta_secs,
                current_file,
                ..
            } => {
                let cf = current_file
                    .as_deref()
                    .and_then(|f| CString::new(f.to_string()).ok());
                let cf_ptr = cf.as_ref().map(|c| c.as_ptr()).unwrap_or(ptr::null());
                (self.progress_cb)(
                    self.user_data.0,
                    self.job_id_cstr(),
                    processed_bytes,
                    total_bytes,
                    speed_bps,
                    eta_secs,
                    cf_ptr,
                );
            }

            JobEvent::FileDone { ok, .. } => {
                if ok {
                    self.control.processed_files.fetch_add(1, Ordering::Relaxed);
                }
            }

            JobEvent::Conflict {
                conflict_id,
                source,
                destination,
                source_size,
                dest_size,
                source_modified_ms,
                dest_modified_ms,
                is_dir,
                ..
            } => {
                let cid = CString::new(conflict_id.as_str()).unwrap_or_default();
                let src = CString::new(source.as_str()).unwrap_or_default();
                let dst = CString::new(destination.as_str()).unwrap_or_default();
                let resolution = (self.conflict_cb)(
                    self.user_data.0,
                    self.job_id_cstr(),
                    cid.as_ptr(),
                    src.as_ptr(),
                    dst.as_ptr(),
                    source_size,
                    dest_size,
                    source_modified_ms,
                    dest_modified_ms,
                    if is_dir { 1 } else { 0 },
                );
                // ConflictCallback resolution (actual behavior):
                // 0=skip, 1=overwrite, anything else (including 2 and -1)=keepBoth (no cancel)
                // Known limitation: -1 does NOT cancel the job despite older
                // docs suggesting so; it falls through to keepBoth.
                let resolved = match resolution {
                    0 => "skip".to_string(),
                    1 => "overwrite".to_string(),
                    _ => "keepBoth".to_string(),
                };
                // Deliver straight to this job's pending-conflict oneshot.
                // Registration normally precedes the callback (engine fix),
                // but tolerate late registration defensively.
                let mut delivered = false;
                for attempt in 0..50 {
                    {
                        let mut pending =
                            self.control.pending_conflicts.lock();
                        if let Some(pos) = pending
                            .iter()
                            .position(|(id, _)| id == &conflict_id)
                        {
                            let (_, tx) = pending.remove(pos);
                            let _ = tx.send(resolved.clone());
                            delivered = true;
                            break;
                        }
                    }
                    std::thread::sleep(Duration::from_millis(20));
                }

            }

            JobEvent::State { state, .. } => {
                if state == "completed" || state == "failed" || state == "cancelled" {
                    let success = if state == "completed" { 1 } else { 0 };
                    let err = if state == "completed" {
                        CString::default()
                    } else {
                        let errors = self.control.errors.lock();
                        let msg = errors.first().map(|s| s.as_str()).unwrap_or("unknown error");
                        CString::new(msg).unwrap_or_default()
                    };
                    (self.complete_cb)(
                        self.user_data.0,
                        self.job_id_cstr(),
                        success,
                        err.as_ptr(),
                    );
                }
            }

            JobEvent::Error { message, .. } => {
                self.control.errors.lock().push(message);
            }
        }
    }

    fn job_id_cstr(&self) -> *const c_char {
        // Leak a CString for the duration of the callback; the C caller does not own it.
        // We store it in a thread-local to prevent leaks.
        thread_local! {
            static LAST_ID: std::cell::RefCell<Option<CString>> = std::cell::RefCell::new(None);
        }
        LAST_ID.with(|cell| {
            let c = CString::new(self.job_id.as_str()).unwrap_or_default();
            let ptr = c.as_ptr();
            *cell.borrow_mut() = Some(c);
            ptr
        })
    }
}

/// Starts an async copy job to `dest_dir`, reporting progress/completion/conflicts via callbacks.
#[no_mangle]
pub unsafe extern "C" fn nexus_copy(
    ctx: *mut c_void,
    sources: *const *const c_char,
    sources_count: size_t,
    dest_dir: *const c_char,
    progress_cb: ProgressCallback,
    complete_cb: CompletionCallback,
    conflict_cb: ConflictCallback,
    user_data: *mut c_void,
) -> *mut c_void {
    if ctx.is_null() || sources.is_null() || dest_dir.is_null() || sources_count == 0 {
        return ptr::null_mut();
    }
    let _ctx = borrow_ctx(ctx);
    let dest = match CStr::from_ptr(dest_dir).to_str() {
        Ok(d) => d,
        Err(_) => return ptr::null_mut(),
    };
    let srcs = collect_strings(sources, sources_count);
    if srcs.is_empty() || dest.is_empty() {
        return ptr::null_mut();
    }

    let job_id = uuid::Uuid::new_v4().to_string();
    let control = Arc::new(JobControl::new("copy"));
    let cancel = Arc::new(AtomicBool::new(false));
    let paused = Arc::new(AtomicBool::new(false));

    let handle = Box::new((
        Arc::clone(&control),
        Arc::clone(&cancel),
        Arc::clone(&paused),
    ));

    let job_id_thread = job_id.clone();
    let ud = SendPtr(user_data);
    let ctrl = Arc::clone(&control);

    start_job_thread(move || {
        let mut sink = FfiSink {
            job_id: job_id_thread.clone(),
            progress_cb,
            complete_cb,
            conflict_cb,
            user_data: ud,
            control: Arc::clone(&ctrl),
        };
        // Wire pause/cancel from FFI handle into the engine's JobControl
        ctrl.paused.store(paused.load(Ordering::Relaxed), Ordering::Relaxed);
        ctrl.cancel.store(cancel.load(Ordering::Relaxed), Ordering::Relaxed);

        run_transfer_blocking(
            JobKind::Copy,
            srcs,
            dest.to_string(),
            ctrl,
            job_id_thread,
            &mut |event| sink.emit(event),
        );
    });

    Box::into_raw(handle) as *mut c_void
}

/// Starts an async move job to `dest_dir`, reporting progress/completion/conflicts via callbacks.
#[no_mangle]
pub unsafe extern "C" fn nexus_move(
    ctx: *mut c_void,
    sources: *const *const c_char,
    sources_count: size_t,
    dest_dir: *const c_char,
    progress_cb: ProgressCallback,
    complete_cb: CompletionCallback,
    conflict_cb: ConflictCallback,
    user_data: *mut c_void,
) -> *mut c_void {
    if ctx.is_null() || sources.is_null() || dest_dir.is_null() || sources_count == 0 {
        return ptr::null_mut();
    }
    let _ctx = borrow_ctx(ctx);
    let dest = match CStr::from_ptr(dest_dir).to_str() {
        Ok(d) => d,
        Err(_) => return ptr::null_mut(),
    };
    let srcs = collect_strings(sources, sources_count);
    if srcs.is_empty() || dest.is_empty() {
        return ptr::null_mut();
    }

    let job_id = uuid::Uuid::new_v4().to_string();
    let control = Arc::new(JobControl::new("move"));
    let cancel = Arc::new(AtomicBool::new(false));
    let paused = Arc::new(AtomicBool::new(false));

    let handle = Box::new((
        Arc::clone(&control),
        Arc::clone(&cancel),
        Arc::clone(&paused),
    ));

    let job_id_thread = job_id.clone();
    let ud = SendPtr(user_data);
    let ctrl = Arc::clone(&control);

    start_job_thread(move || {
        let mut sink = FfiSink {
            job_id: job_id_thread.clone(),
            progress_cb,
            complete_cb,
            conflict_cb,
            user_data: ud,
            control: Arc::clone(&ctrl),
        };
        ctrl.paused.store(paused.load(Ordering::Relaxed), Ordering::Relaxed);
        ctrl.cancel.store(cancel.load(Ordering::Relaxed), Ordering::Relaxed);

        run_transfer_blocking(
            JobKind::Move,
            srcs,
            dest.to_string(),
            ctrl,
            job_id_thread,
            &mut |event| sink.emit(event),
        );
    });

    Box::into_raw(handle) as *mut c_void
}

/// Starts an async delete job (to trash when `to_trash` is nonzero), reporting progress/completion via callbacks.
#[no_mangle]
pub unsafe extern "C" fn nexus_delete(
    ctx: *mut c_void,
    paths: *const *const c_char,
    paths_count: size_t,
    to_trash: c_int,
    progress_cb: ProgressCallback,
    complete_cb: CompletionCallback,
    user_data: *mut c_void,
) -> *mut c_void {
    if ctx.is_null() || paths.is_null() || paths_count == 0 {
        return ptr::null_mut();
    }
    let _ctx = borrow_ctx(ctx);
    let paths_vec = collect_strings(paths, paths_count);
    if paths_vec.is_empty() {
        return ptr::null_mut();
    }

    let job_id = uuid::Uuid::new_v4().to_string();
    let control = Arc::new(JobControl::new("delete"));
    let cancel = Arc::new(AtomicBool::new(false));
    let paused = Arc::new(AtomicBool::new(false));

    let handle = Box::new((
        Arc::clone(&control),
        Arc::clone(&cancel),
        Arc::clone(&paused),
    ));

    let job_id_thread = job_id.clone();
    let ud = SendPtr(user_data);
    let ctrl = Arc::clone(&control);

    // Delete doesn't need conflict callback; use a no-op
    extern "C" fn noop_conflict(
        _ud: *mut c_void,
        _jid: *const c_char,
        _cid: *const c_char,
        _src: *const c_char,
        _dst: *const c_char,
        _ss: u64,
        _ds: u64,
        _sm: u64,
        _dm: u64,
        _is_dir: c_int,
    ) -> c_int {
        0 // skip
    }

    start_job_thread(move || {
        let mut sink = FfiSink {
            job_id: job_id_thread.clone(),
            progress_cb,
            complete_cb,
            conflict_cb: noop_conflict,
            user_data: ud,
            control: Arc::clone(&ctrl),
        };
        ctrl.cancel.store(cancel.load(Ordering::Relaxed), Ordering::Relaxed);

        run_delete_blocking(
            paths_vec,
            to_trash != 0,
            ctrl,
            job_id_thread,
            &mut |event| sink.emit(event),
        );
    });

    Box::into_raw(handle) as *mut c_void
}

/// Pauses a running job handle; the worker thread blocks until resumed or cancelled.
#[no_mangle]
pub unsafe extern "C" fn nexus_pause_job(handle: *mut c_void) -> c_int {
    if handle.is_null() { return -1; }
    let job = &*(handle as *const JobHandleInner);
    job.2.store(true, Ordering::Relaxed);
    job.0.paused.store(true, Ordering::Relaxed);
    job.0.set_state("paused");
    0
}

/// Resumes a paused job handle and marks it running again.
#[no_mangle]
pub unsafe extern "C" fn nexus_resume_job(handle: *mut c_void) -> c_int {
    if handle.is_null() { return -1; }
    let job = &*(handle as *const JobHandleInner);
    job.2.store(false, Ordering::Relaxed);
    job.0.paused.store(false, Ordering::Relaxed);
    job.0.set_state("running");
    0
}

/// Requests cancellation of a job handle; the worker thread exits at the next checkpoint.
#[no_mangle]
pub unsafe extern "C" fn nexus_cancel_job(handle: *mut c_void) -> c_int {
    if handle.is_null() { return -1; }
    let job = &*(handle as *const JobHandleInner);
    job.1.store(true, Ordering::Relaxed);
    job.2.store(false, Ordering::Relaxed);
    job.0.cancel.store(true, Ordering::Relaxed);
    job.0.set_state("cancelling");
    0
}

/// Destroys a job handle previously returned by `nexus_copy`/`nexus_move`/`nexus_delete`.
#[no_mangle]
pub unsafe extern "C" fn nexus_free_job_handle(handle: *mut c_void) {
    if !handle.is_null() {
        drop(Box::from_raw(handle as *mut JobHandleInner));
    }
}
