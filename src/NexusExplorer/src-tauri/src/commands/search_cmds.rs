//! Tauri IPC commands for file search.

use std::sync::atomic::AtomicBool;
use std::sync::Arc;

use tauri::ipc::Channel;
use tauri::State;
use uuid::Uuid;

use crate::engine::search_engine::{run_search_blocking, SearchRegistry};
use crate::models::{SearchEvent, SearchOptions};

/// Starts a filename search under `root`, streaming `SearchEvent` batches over `on_event`.
#[tauri::command]
pub async fn search_files(
    root: String,
    query: String,
    opts: SearchOptions,
    on_event: Channel<SearchEvent>,
    registry: State<'_, SearchRegistry>,
) -> Result<String, String> {
    if root.trim().is_empty() {
        return Err("root path required".to_string());
    }

    let search_id = Uuid::new_v4().to_string();
    let cancel = Arc::new(AtomicBool::new(false));
    registry.register(search_id.clone(), cancel.clone());

    let channel = on_event.clone();
    let sid_for_task = search_id.clone();
    let registry_inner = registry.inner().clone();

    tauri::async_runtime::spawn_blocking(move || {
        let mut sink = move |event: SearchEvent| {
            let done = matches!(
                &event,
                SearchEvent::Done { .. } | SearchEvent::Error { .. }
            );
            let _ = channel.send(event);
            if done {
                registry_inner.remove(&sid_for_task);
            }
        };
        run_search_blocking(root, query, opts, cancel, &mut sink);
    });

    Ok(search_id)
}

/// Signals cancellation for the given search id.
#[tauri::command]
pub async fn cancel_search(
    search_id: String,
    registry: State<'_, SearchRegistry>,
) -> Result<(), String> {
    if registry.cancel(&search_id) {
        Ok(())
    } else {
        Err("search not found".to_string())
    }
}
