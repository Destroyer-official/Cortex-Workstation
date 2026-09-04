pub mod commands;
pub mod engine;
pub mod models;

use commands::{fs_cmds, ops_cmds, search_cmds};
use engine::job_manager::JobManager;
use engine::listing::ScanRegistry;
use engine::search_engine::SearchRegistry;
use engine::watch::WatchManager;
use tauri::{Emitter, Manager};

fn extract_paths(args: &[String]) -> Vec<String> {
    args.iter()
        .filter(|a| !a.starts_with('-') && std::path::Path::new(a).exists())
        .cloned()
        .collect()
}

fn emit_open_paths(app: &tauri::AppHandle, paths: Vec<String>) {
    if paths.is_empty() {
        return;
    }
    if let Some(win) = app.get_webview_window("main") {
        let _ = win.emit("open-paths", serde_json::json!({ "paths": paths }));
    }
}

/// Builds and runs the NexusExplorer Tauri application with all managed state and IPC commands.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // When embedded (e.g. inside Cortex Cleaner via Win32 SetParent), the host
    // sets NEXUS_NO_SINGLETON=1 so this process always creates its own window
    // instead of forwarding args to an already-running instance and exiting.
    let singleton_enabled = std::env::var("NEXUS_NO_SINGLETON").as_deref() != Ok("1");

    let mut builder = tauri::Builder::default();
    if singleton_enabled {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, args, _cwd| {
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.set_focus();
            }
            emit_open_paths(app, extract_paths(&args));
        }));
    }
    builder
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(JobManager::new())
        .manage(ScanRegistry::new())
        .manage(SearchRegistry::new())
        .manage(WatchManager::new())
        .setup(|app| {
            let args: Vec<String> = std::env::args().skip(1).collect();
            emit_open_paths(app.handle(), extract_paths(&args));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            fs_cmds::scan_dir,
            fs_cmds::cancel_scan,
            fs_cmds::read_dir_sync,
            fs_cmds::stat_path,
            fs_cmds::get_drives,
            fs_cmds::home_dir,
            fs_cmds::rename_entry,
            fs_cmds::create_folder,
            fs_cmds::read_text_file,
            fs_cmds::open_path,
            fs_cmds::reveal_in_shell,
            fs_cmds::watch_dir,
            fs_cmds::unwatch_dir,
            ops_cmds::copy_entries,
            ops_cmds::move_entries,
            ops_cmds::delete_entries,
            ops_cmds::pause_job,
            ops_cmds::resume_job,
            ops_cmds::cancel_job,
            ops_cmds::resolve_conflict,
            ops_cmds::get_active_jobs,
            search_cmds::search_files,
            search_cmds::cancel_search,
        ])
        .run(tauri::generate_context!())
        .expect("error while running NexusExplorer");
}
