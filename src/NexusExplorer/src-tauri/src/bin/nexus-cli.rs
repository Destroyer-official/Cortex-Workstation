//! nexus-cli — command-line interface for the NexusExplorer engine.
//!
//! Examples:
//!   nexus-cli list "C:\Windows" [--json]
//!   nexus-cli search "C:\Users" "*.pdf" [maxResults]
//!   nexus-cli copy <src...> --to <destDir>
//!   nexus-cli move <src...> --to <destDir>
//!   nexus-cli delete [--permanent] <path...>
//!   nexus-cli drives
//!   nexus-cli hash <file>
//!   nexus-cli gui [<path>]

use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::exit;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;

use nexus_explorer_lib::engine::copy_engine::{self, JobKind};
use nexus_explorer_lib::engine::job_manager::JobControl;
use nexus_explorer_lib::engine::search_engine;

const PROGRESS_BAR_WIDTH: usize = 28;

fn print_usage() {
    println!("nexus-cli — NexusExplorer command line");
    println!();
    println!("USAGE:");
    println!("  nexus-cli list <path> [--json]");
    println!("  nexus-cli search <root> <query> [maxResults]");
    println!("  nexus-cli copy <src...> --to <destDir>");
    println!("  nexus-cli move <src...> --to <destDir>");
    println!("  nexus-cli delete [--permanent] <path>...");
    println!("  nexus-cli drives");
    println!("  nexus-cli hash <file>");
    println!("  nexus-cli gui [<folder>]");
}

fn fmt_bytes(n: u64) -> String {
    const UNITS: [&str; 6] = ["B", "KB", "MB", "GB", "TB", "PB"];
    if n == 0 {
        return "0 B".into();
    }
    let mut value = n as f64;
    let mut unit = 0usize;
    while value >= 1024.0 && unit < UNITS.len() - 1 {
        value /= 1024.0;
        unit += 1;
    }
    if unit == 0 || value >= 100.0 {
        format!("{:.0} {}", value, UNITS[unit])
    } else {
        format!("{value:.1} {}", UNITS[unit])
    }
}

fn file_mtime_ms(p: &Path) -> u64 {
    p.metadata()
        .ok()
        .and_then(|m| m.modified().ok())
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

fn ms_to_string(ms: u64) -> String {
    if ms == 0 {
        return "-".into();
    }
    let secs = (ms / 1000) as i64;
    let days = secs.div_euclid(86_400);
    let rem = secs.rem_euclid(86_400);
    let (h, mi, s) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{y:04}-{m:02}-{d:02} {h:02}:{mi:02}:{s:02}")
}

fn entries_to_json(
    entries: &[nexus_explorer_lib::models::FileEntry],
) -> Result<String, serde_json::Error> {
    serde_json::to_string(entries)
}

fn cmd_list(args: &[String]) {
    let json = args.iter().any(|a| a == "--json");
    let path = args.iter().find(|a| !a.starts_with("--"));
    let Some(path) = path else {
        eprintln!("error: list requires a path");
        exit(2);
    };

    let started = Instant::now();
    let entries = match nexus_explorer_lib::commands::fs_cmds::__cli_read_dir(path) {
        Ok(list) => list,
        Err(err) => {
            eprintln!("error: {err}");
            exit(1);
        }
    };
    let elapsed = started.elapsed();

    if json {
        match entries_to_json(&entries) {
            Ok(out) => println!("{out}"),
            Err(err) => {
                eprintln!("error: json encode failed: {err}");
                exit(1);
            }
        }
    } else {
        println!(
            "{:<6}  {:>12}  {:<19}  NAME",
            "TYPE", "SIZE", "MODIFIED"
        );
        for e in &entries {
            let kind = if e.is_dir { "<DIR>" } else { "" };
            println!(
                "{:<6}  {:>12}  {:<19}  {}",
                kind,
                if e.is_dir { String::new() } else { fmt_bytes(e.size) },
                ms_to_string(e.modified_ms),
                e.name
            );
        }
        println!(
            "\n{} items in {:.1} ms",
            entries.len(),
            elapsed.as_secs_f64() * 1000.0
        );
    }
}

fn cmd_search(root: Option<&String>, query: Option<&String>, max: Option<&String>) {
    let Some(root) = root else {
        eprintln!("error: search requires <root> <query>");
        exit(2);
    };
    let query = query.cloned().unwrap_or_default();
    let max_results: u32 = max.and_then(|m| m.parse().ok()).unwrap_or(10_000);

    let opts = nexus_explorer_lib::models::SearchOptions {
        recursive: true,
        max_results,
        include_hidden: false,
    };
    let cancel = Arc::new(AtomicBool::new(false));
    let started = Instant::now();
    let stdout = std::io::stdout();
    let mut total = 0u64;

    let mut sink = |event: nexus_explorer_lib::models::SearchEvent| match event {
        nexus_explorer_lib::models::SearchEvent::Batch { entries } => {
            let mut out = stdout.lock();
            for e in entries {
                let _ = writeln!(out, "{}\t{}", if e.is_dir { "DIR" } else { "FILE" }, e.path);
            }
            drop(out);
        }
        nexus_explorer_lib::models::SearchEvent::Done { total: t, .. } => total = t,
        nexus_explorer_lib::models::SearchEvent::Error { message } => {
            eprintln!("error: {message}");
        }
    };

    search_engine::run_search_blocking(
        root.clone(),
        query,
        opts,
        cancel.clone(),
        &mut sink,
    );

    eprintln!(
        "\n{} results in {:.0} ms",
        total,
        started.elapsed().as_secs_f64() * 1000.0
    );
}

fn render_progress(processed: u64, total: u64, speed_bps: f64, eta: f64, current: &str) {
    let pct = if total > 0 {
        processed as f64 / total as f64
    } else {
        0.0
    };
    let filled = (pct * PROGRESS_BAR_WIDTH as f64).round() as usize;
    let bar: String = "#".repeat(filled.min(PROGRESS_BAR_WIDTH))
        + &"-".repeat(PROGRESS_BAR_WIDTH.saturating_sub(filled));
    let eta_txt = if speed_bps > 1.0 && eta.is_finite() && eta >= 0.0 {
        format_eta(eta)
    } else {
        "--".into()
    };
    eprint!(
        "\r[{}] {:>3}%  {:>9}/s  ETA {}  {}",
        bar,
        (pct * 100.0).min(99.9) as u64,
        fmt_bytes(speed_bps as u64),
        eta_txt,
        truncate(current, 40)
    );
    let _ = std::io::stderr().flush();
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("…{}", &s[s.len() - max + 1..])
    }
}

fn format_eta(secs: f64) -> String {
    let s = secs.round() as u64;
    if s < 60 {
        format!("{s}s")
    } else if s < 3600 {
        format!("{}m{}s", s / 60, s % 60)
    } else {
        format!("{}h{}m", s / 3600, (s % 3600) / 60)
    }
}

fn cmd_transfer(kind_label: &str, args: &[String]) {
    let to_pos = args.iter().position(|a| a == "--to");
    let Some(to_pos) = to_pos else {
        eprintln!("error: {kind_label} requires --to <destDir>");
        exit(2);
    };
    let sources: Vec<String> = args[..to_pos].to_vec();
    let dest = args.get(to_pos + 1).cloned().unwrap_or_default();
    if sources.is_empty() || dest.is_empty() {
        eprintln!("error: {kind_label} needs at least one source and a --to destination");
        exit(2);
    }

    let kind = if kind_label == "copy" {
        JobKind::Copy
    } else {
        JobKind::Move
    };
    let job_id = uuid::Uuid::new_v4().to_string();
    let control = Arc::new(JobControl::new(kind.as_str()));
    let started = Instant::now();
    let label = kind_label.to_string();
    let dest_for_log = dest.clone();
    let job_id_for_sink = job_id.clone();

    let mut last_render = Instant::now();
    let mut sink = |event: nexus_explorer_lib::models::JobEvent| {
        use nexus_explorer_lib::models::JobEvent as E;
        match event {
            E::Started { total_files, total_bytes, .. } => {
                control.total_files.store(total_files, Ordering::Relaxed);
                control.total_bytes.store(total_bytes, Ordering::Relaxed);
                println!("{label}: {total_files} files ({}) -> {dest_for_log}", fmt_bytes(total_bytes));
            }
            E::Progress { processed_bytes, speed_bps, eta_secs, current_file, .. } => {
                let now = Instant::now();
                if now.duration_since(last_render).as_millis() >= 120 {
                    last_render = now;
                    let snapshot = control.snapshot(&job_id_for_sink);
                    render_progress(
                        processed_bytes,
                        snapshot.total_bytes,
                        speed_bps,
                        eta_secs,
                        current_file.as_deref().unwrap_or(""),
                    );
                }
            }
            E::FileDone { ok, error, path, .. } => {
                if !ok {
                    eprintln!("\nFAILED: {path}: {}", error.unwrap_or_default());
                }
            }
            E::Error { message, .. } => {
                eprintln!("\nERROR: {message}");
            }
            E::State { state, .. } => {
                let secs = started.elapsed().as_secs_f64();
                eprint!("\r{}", " ".repeat(110));
                eprint!("\r");
                println!(
                    "{state} in {:.2}s  ({})",
                    secs,
                    fmt_bytes(control.processed_bytes.load(Ordering::Relaxed)),
                );
                let errors = control.errors.lock();
                if !errors.is_empty() {
                    eprintln!("{} error(s):", errors.len());
                    for err in errors.iter() {
                        eprintln!("  - {err}");
                    }
                }
            }
            _ => {}
        }
    };

    copy_engine::run_transfer_blocking(kind, sources, dest, control.clone(), job_id, &mut sink);

    exit(if control.errors.lock().is_empty() { 0 } else { 1 });
}

fn cmd_delete(args: &[String]) {
    let permanent = args.iter().any(|a| a == "--permanent");
    let paths: Vec<String> = args
        .iter()
        .filter(|a| !a.starts_with("--"))
        .cloned()
        .collect();
    if paths.is_empty() {
        eprintln!("error: delete requires paths (or --permanent flag before them)");
        exit(2);
    }

    let job_id = uuid::Uuid::new_v4().to_string();
    let control = Arc::new(JobControl::new("delete"));
    let mode = if permanent { "permanently deleting" } else { "recycling" };
    println!("{mode} {} item(s)…", paths.len());

    let mut sink = |event: nexus_explorer_lib::models::JobEvent| {
        use nexus_explorer_lib::models::JobEvent as E;
        match event {
            E::FileDone { ok, path, error, .. } => {
                if ok {
                    println!("  removed {}", path);
                } else {
                    eprintln!("  FAILED {}: {}", path, error.unwrap_or_default());
                }
            }
            E::State { state, .. } => println!("done: {state}"),
            _ => {}
        }
    };

    copy_engine::run_delete_blocking(paths, !permanent, control, job_id, &mut sink);
}

fn cmd_drives() {
    #[cfg(windows)]
    let _error_mode = ErrorModeGuard(unsafe {
        windows::Win32::System::Diagnostics::Debug::SetErrorMode(
            windows::Win32::System::Diagnostics::Debug::SEM_FAILCRITICALERRORS,
        )
    });

    println!("{:<5} {:<10} {:<8} {:>10} {:>10}  LABEL", "DRIVE", "TYPE", "FS", "FREE", "TOTAL");
    for letter in b'A'..=b'Z' {
        let root = format!("{}:\\", letter as char);
        let p = PathBuf::from(&root);
        if !p.is_dir() {
            continue;
        }
        let meta = fs_free_total(&root);
        let drive_type = drive_type_name(&root);
        match meta {
            Some((free, total)) => println!(
                "{:<5} {:<10} {:<8} {:>10} {:>10}  {}",
                format!("{}:", letter as char),
                drive_type,
                fs_name(&root),
                fmt_bytes(free),
                fmt_bytes(total),
                volume_label(&root)
            ),
            None => println!(
                "{:<5} {:<10}",
                format!("{}:", letter as char),
                drive_type
            ),
        }
    }
}

#[cfg(windows)]
fn with_wide(p: &str) -> Vec<u16> {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    let mut v: Vec<u16> = OsStr::new(p).encode_wide().collect();
    v.push(0);
    v
}

#[cfg(windows)]
struct ErrorModeGuard(windows::Win32::System::Diagnostics::Debug::THREAD_ERROR_MODE);

#[cfg(windows)]
impl Drop for ErrorModeGuard {
    fn drop(&mut self) {
        unsafe {
            windows::Win32::System::Diagnostics::Debug::SetErrorMode(self.0);
        }
    }
}

#[cfg(windows)]
fn fs_free_total(root: &str) -> Option<(u64, u64)> {
    use windows::core::PCWSTR;
    use windows::Win32::Storage::FileSystem::GetDiskFreeSpaceExW;
    let wide = with_wide(root);
    let mut free_to_caller: u64 = 0;
    let mut total: u64 = 0;
    let mut free: u64 = 0;
    unsafe {
        GetDiskFreeSpaceExW(
            PCWSTR(wide.as_ptr()),
            Some(&mut free_to_caller),
            Some(&mut total),
            Some(&mut free),
        )
        .ok()?;
    }
    Some((free, total))
}

#[cfg(not(windows))]
fn fs_free_total(_root: &str) -> Option<(u64, u64)> {
    None
}

#[cfg(windows)]
fn drive_type_name(root: &str) -> &'static str {
    use windows::core::PCWSTR;
    use windows::Win32::Storage::FileSystem::GetDriveTypeW;
    let wide = with_wide(root);
    match unsafe { GetDriveTypeW(PCWSTR(wide.as_ptr())) } {
        3 => "fixed",
        2 => "removable",
        4 => "network",
        5 => "cdrom",
        6 => "ramdisk",
        _ => "unknown",
    }
}

#[cfg(not(windows))]
fn drive_type_name(_root: &str) -> &'static str {
    "unknown"
}

#[cfg(windows)]
fn fs_name(_root: &str) -> String {
    "-".into()
}

#[cfg(not(windows))]
fn fs_name(_root: &str) -> String {
    "-".into()
}

#[cfg(windows)]
fn volume_label(_root: &str) -> String {
    String::new()
}

#[cfg(not(windows))]
fn volume_label(_root: &str) -> String {
    String::new()
}

fn cmd_hash(path: &[String]) {
    let Some(path) = path.first() else {
        eprintln!("error: hash requires a file path");
        exit(2);
    };
    let file = match std::fs::File::open(path) {
        Ok(f) => f,
        Err(err) => {
            eprintln!("error: cannot open {path}: {err}");
            exit(1);
        }
    };
    let started = Instant::now();
    let mut reader = std::io::BufReader::with_capacity(1024 * 1024, file);
    let mut hasher = xxhash_rust::xxh3::Xxh3::new();
    let mut buf = vec![0u8; 1024 * 1024];
    loop {
        match reader.read(&mut buf) {
            Ok(0) => break,
            Ok(n) => hasher.update(&buf[..n]),
            Err(err) => {
                eprintln!("error reading: {err}");
                exit(1);
            }
        }
    }
    let digest = hasher.digest128();
    println!(
        "xxh3-128:{}  {}  ({}) in {:.2}s",
        format!("{digest:032x}"),
        path,
        fmt_bytes(Path::new(path).metadata().map(|m| m.len()).unwrap_or(0)),
        started.elapsed().as_secs_f64()
    );
}

use std::io::Read;

fn cmd_rename(args: &[String]) {
    if args.len() < 2 {
        eprintln!("error: rename requires <path> <new_name>");
        exit(2);
    }
    let src = PathBuf::from(&args[0]);
    let new_name = args[1].trim();
    if new_name.is_empty() || new_name.contains(['\\', '/']) {
        eprintln!("error: invalid new name");
        exit(2);
    }
    let dest = match src.parent() {
        Some(p) => p.join(new_name),
        None => PathBuf::from(new_name),
    };
    match std::fs::rename(&src, &dest) {
        Ok(()) => println!("renamed -> {}", dest.display()),
        Err(err) => {
            eprintln!("error: {}", err);
            exit(1);
        }
    }
}

fn cmd_mkdir(args: &[String]) {
    let Some(path) = args.first() else {
        eprintln!("error: mkdir requires a path");
        exit(2);
    };
    match std::fs::create_dir(path) {
        Ok(()) => println!("created {}", path),
        Err(err) => {
            eprintln!("error: {}", err);
            exit(1);
        }
    }
}

fn cmd_drives_json() {
    #[cfg(windows)]
    let _error_mode = ErrorModeGuard(unsafe {
        windows::Win32::System::Diagnostics::Debug::SetErrorMode(
            windows::Win32::System::Diagnostics::Debug::SEM_FAILCRITICALERRORS,
        )
    });

    let mut items: Vec<serde_json::Value> = Vec::new();
    for letter in b'A'..=b'Z' {
        let root = format!("{}:\\\\", letter as char);
        if !Path::new(&root).is_dir() {
            continue;
        }
        let (free, total) = fs_free_total(&root).unwrap_or((0, 0));
        let dtype = drive_type_name(&root);
        items.push(serde_json::json!({
            "path": root,
            "driveType": dtype,
            "freeBytes": free,
            "totalBytes": total,
            "isReady": total > 0
        }));
    }
    match serde_json::to_string(&items) {
        Ok(out) => println!("{out}"),
        Err(err) => {
            eprintln!("error: json encode failed: {err}");
            exit(1);
        }
    }
}

fn cmd_gui(args: &[String]) {
    let exe = std::env::current_exe().expect("current exe");
    let main_exe = exe
        .parent()
        .map(|dir| dir.join("nexus-explorer.exe"))
        .unwrap_or_else(|| PathBuf::from("nexus-explorer.exe"));
    if !main_exe.exists() {
        eprintln!("error: GUI binary not found next to nexus-cli (looked for {})", main_exe.display());
        exit(1);
    }
    let mut cmd = std::process::Command::new(main_exe);
    for arg in args {
        cmd.arg(arg);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x00000008); // DETACHED_PROCESS
    }
    match cmd.spawn() {
        Ok(_) => {}
        Err(err) => {
            eprintln!("error launching GUI: {err}");
            exit(1);
        }
    }
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    if raw.is_empty() {
        print_usage();
        return;
    }
    match raw[0].as_str() {
        "list" => cmd_list(&raw[1..]),
        "search" => cmd_search(raw.get(1), raw.get(2), raw.get(3)),
        "copy" | "move" => cmd_transfer(raw[0].as_str(), &raw[1..]),
        "delete" => cmd_delete(&raw[1..]),
        "drives" => {
            if std::env::args().any(|a| a == "--json") { cmd_drives_json() } else { cmd_drives() }
        }
        "rename" => cmd_rename(&raw[1..]),
        "mkdir" => cmd_mkdir(&raw[1..]),
        "hash" => cmd_hash(&raw[1..]),
        "gui" => cmd_gui(&raw[1..]),
        "help" | "--help" | "-h" => print_usage(),
        other => {
            eprintln!("unknown command: {other}\n");
            print_usage();
            exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::entries_to_json;
    use nexus_explorer_lib::models::FileEntry;

    fn entry(name: &str, path: &str) -> FileEntry {
        FileEntry {
            name: name.to_string(),
            path: path.to_string(),
            parent_path: "C:\\base".to_string(),
            is_dir: false,
            size: 42,
            modified_ms: 1_700_000_000_000,
            created_ms: 0,
            is_hidden: false,
            is_system: false,
            is_readonly: false,
            ext: "txt".to_string(),
        }
    }

    #[test]
    fn json_survives_hostile_filenames() {
        let hostile = [
            r#"quote"name"#,
            r"back\slash",
            "new\nline",
            "tab\tchar",
            "unicode_é中__",
            "ctrlchar",
        ];
        let entries: Vec<FileEntry> = hostile
            .iter()
            .enumerate()
            .map(|(i, n)| entry(n, &format!(r"C:\dir\{i}\{n}")))
            .collect();
        let out = entries_to_json(&entries).expect("serialize must succeed");
        let parsed: Vec<serde_json::Value> =
            serde_json::from_str(&out).expect("output must be valid JSON");
        assert_eq!(parsed.len(), hostile.len());
        for (want, got) in hostile.iter().zip(parsed.iter()) {
            assert_eq!(got["name"].as_str().unwrap(), *want, "name round-trip");
        }
    }

    #[test]
    fn json_matches_python_consumer_contract() {
        let entries = vec![entry("a.txt", r"C:\dir\a.txt")];
        let out = entries_to_json(&entries).unwrap();
        let v: serde_json::Value = serde_json::from_str(&out).unwrap();
        let first = v.as_array().unwrap()[0].as_object().unwrap();
        for key in ["name", "path", "isDir", "size", "modifiedMs"] {
            assert!(first.contains_key(key), "missing consumer key {key}");
        }
    }
}
