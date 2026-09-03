//! Recursive filesystem watchers with debounced change notifications.

use std::collections::HashMap;
use std::path::Path;
use std::time::Duration;

use notify_debouncer_full::{
    new_debouncer, DebouncedEvent, Debouncer,
    notify::{RecommendedWatcher, RecursiveMode},
};
use parking_lot::Mutex;
use serde::Serialize;
use tauri::{AppHandle, Emitter};

const DEBOUNCE_TIMEOUT_MS: u64 = 250;
const DEBOUNCE_TICK_MS: u64 = 250;
pub const FS_CHANGE_EVENT: &str = "fs-change";

type WatcherHandle = Debouncer<RecommendedWatcher, notify_debouncer_full::RecommendedCache>;

/// Payload emitted on the "fs-change" event; `path` is the watched root.
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FsChangePayload {
    pub path: String,
}

/// Manages per-directory recursive watchers, emitting one coalesced
/// "fs-change" event per debounced batch of filesystem modifications.
pub struct WatchManager {
    watchers: Mutex<HashMap<String, WatcherHandle>>,
}

impl WatchManager {
    pub fn new() -> Self {
        Self {
            watchers: Mutex::new(HashMap::new()),
        }
    }

    /// Starts recursively watching `path`; no-op if already watched.
    pub fn watch(&self, app: AppHandle, path: String) -> Result<(), String> {
        if path.trim().is_empty() {
            return Err("path must not be empty".to_string());
        }
        let key = path.to_lowercase();
        let mut watchers = self.watchers.lock();
        if watchers.contains_key(&key) {
            return Ok(());
        }
        let app_handle = app.clone();
        let root = path.clone();
        let mut debouncer = new_debouncer(
            Duration::from_millis(DEBOUNCE_TIMEOUT_MS),
            Some(Duration::from_millis(DEBOUNCE_TICK_MS)),
            move |result: Result<Vec<DebouncedEvent>, Vec<notify_debouncer_full::notify::Error>>| {
                if result.is_ok() {
                    let _ = app_handle.emit(
                        FS_CHANGE_EVENT,
                        FsChangePayload {
                            path: root.clone(),
                        },
                    );
                }
            },
        )
        .map_err(|e| e.to_string())?;
        debouncer
            .watch(Path::new(&path), RecursiveMode::Recursive)
            .map_err(|e| e.to_string())?;
        watchers.insert(key, debouncer);
        Ok(())
    }

    /// Stops watching `path`, dropping its watcher instance.
    pub fn unwatch(&self, path: String) -> Result<(), String> {
        self.watchers
            .lock()
            .remove(&path.to_lowercase())
            .map(|_| ())
            .ok_or_else(|| "not watched".to_string())
    }
}
