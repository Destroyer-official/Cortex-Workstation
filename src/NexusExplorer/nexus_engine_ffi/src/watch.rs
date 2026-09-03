use super::*;
use libc::{c_char, c_int, c_void};
use std::ffi::{CStr, CString};
use std::sync::Mutex;
use std::collections::HashMap;
use std::time::Duration;
use notify::{RecommendedWatcher, RecursiveMode};
use notify_debouncer_full::{
    new_debouncer, DebouncedEvent, Debouncer, RecommendedCache,
};

pub struct WatcherMap(Mutex<HashMap<String, Debouncer<RecommendedWatcher, RecommendedCache>>>);

impl WatcherMap {
    pub fn new() -> Self {
        Self(Mutex::new(HashMap::new()))
    }
}

fn lock_ignore_poison<T>(
    mutex: &Mutex<HashMap<String, T>>,
) -> std::sync::MutexGuard<'_, HashMap<String, T>> {
    match mutex.lock() {
        Ok(guard) => guard,
        Err(poisoned) => poisoned.into_inner(),
    }
}

const WATCH_DEBOUNCE_MS: u64 = 250;

#[no_mangle]
pub unsafe extern "C" fn nexus_watch_dir(
    ctx: *mut c_void,
    path: *const c_char,
    callback: FsEventCallback,
    user_data: *mut c_void,
) -> c_int {
    if ctx.is_null() || path.is_null() || callback as usize == 0 {
        return -1;
    }
    let ctx = borrow_ctx(ctx);
    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };

    let path_lower = path_str.to_lowercase();

    let mut map = lock_ignore_poison(&ctx.watchers.0);
    if map.contains_key(&path_lower) {
        return 0;
    }

    let path_for_cb = path_str.to_string();
    let ud = SendPtr(user_data);

    let (tx, rx) = std::sync::mpsc::channel::<(
        Result<Vec<DebouncedEvent>, Vec<notify::Error>>,
        String,
    )>();

    let mut debouncer = match new_debouncer(
        Duration::from_millis(WATCH_DEBOUNCE_MS),
        Some(Duration::from_millis(WATCH_DEBOUNCE_MS)),
        move |result: Result<Vec<DebouncedEvent>, Vec<notify::Error>>| {
            let _ = tx.send((result, path_for_cb.clone()));
        },
    ) {
        Ok(d) => d,
        Err(_) => return -1,
    };

    if debouncer
        .watch(std::path::Path::new(path_str), RecursiveMode::Recursive)
        .is_err()
    {
        return -1;
    }

    map.insert(path_lower, debouncer);
    drop(map);

    std::thread::spawn(move || {
        while let Ok((result, watched_path)) = rx.recv() {
            match result {
                Ok(events) => {
                    let relevant = events.iter().any(|event| {
                        matches!(
                            event.kind,
                            notify::EventKind::Create(_)
                                | notify::EventKind::Modify(_)
                                | notify::EventKind::Remove(_)
                        )
                    });
                    if relevant {
                        if let Ok(c_path) = CString::new(watched_path.as_str()) {
                            callback(ud.get(), c_path.as_ptr());
                        }
                    }
                }
                Err(errors) => {
                    for e in errors {
                        eprintln!("watch error: {e}");
                    }
                }
            }
        }
    });

    0
}

#[no_mangle]
pub unsafe extern "C" fn nexus_unwatch_dir(ctx: *mut c_void, path: *const c_char) -> c_int {
    if ctx.is_null() || path.is_null() {
        return -1;
    }
    let ctx = borrow_ctx(ctx);
    let path_str = match CStr::from_ptr(path).to_str() {
        Ok(p) => p,
        Err(_) => return -1,
    };
    let path_lower = path_str.to_lowercase();

    let mut map = lock_ignore_poison(&ctx.watchers.0);
    if map.remove(&path_lower).is_some() {
        0
    } else {
        -1
    }
}
