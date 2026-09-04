//! Fast parallel filename search with streamed results.

use std::collections::HashMap;
use std::os::windows::fs::MetadataExt as _;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;

use parking_lot::Mutex;

use crate::models::{FileEntry, SearchEvent, SearchOptions};

/// Registry of running searches mapped to their cancellation flags.
#[derive(Clone, Default)]
pub struct SearchRegistry {
    flags: Arc<Mutex<HashMap<String, Arc<AtomicBool>>>>,
}

impl SearchRegistry {
    /// Creates an empty search registry with no active searches.
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers a running search id with its cancellation flag.
    pub fn register(&self, id: String, flag: Arc<AtomicBool>) {
        self.flags.lock().insert(id, flag);
    }

    /// Signals cancellation for the given search id; returns false when the id is unknown.
    pub fn cancel(&self, id: &str) -> bool {
        match self.flags.lock().get(id) {
            Some(flag) => {
                flag.store(true, Ordering::SeqCst);
                true
            }
            None => false,
        }
    }

    /// Removes and returns the cancellation flag for a finished search id.
    pub fn remove(&self, id: &str) -> Option<Arc<AtomicBool>> {
        self.flags.lock().remove(id)
    }
}

struct Matcher {
    segments: Vec<String>,
    substring: Option<String>,
}

impl Matcher {
    fn new(query: &str) -> Self {
        let lowered = query.trim().to_lowercase();
        if lowered.contains('*') {
            let segments: Vec<String> = lowered
                .split('*')
                .filter(|s| !s.is_empty())
                .map(|s| s.to_string())
                .collect();
            Matcher {
                segments,
                substring: None,
            }
        } else if lowered.is_empty() {
            Matcher {
                segments: Vec::new(),
                substring: None,
            }
        } else {
            Matcher {
                segments: Vec::new(),
                substring: Some(lowered),
            }
        }
    }

    fn matches(&self, name: &str) -> bool {
        let lowered = name.to_lowercase();
        if let Some(sub) = &self.substring {
            return lowered.contains(sub);
        }
        if self.segments.is_empty() {
            return true;
        }
        let mut cursor = 0usize;
        for (i, seg) in self.segments.iter().enumerate() {
            match lowered[cursor..].find(seg.as_str()) {
                Some(pos) => {
                    let absolute = cursor + pos;
                    if i == 0 && absolute != 0 && lowered.starts_with(self.segments[0].as_str()) {
                        continue;
                    }
                    cursor = absolute + seg.len();
                }
                None => return false,
            }
        }
        true
    }
}

fn build_entry(entry: &jwalk::DirEntry<((), ())>) -> Option<FileEntry> {
    let path = entry.path();
    let meta = entry.metadata().ok()?;
    let ft = meta.file_type();
    let name = entry.file_name().to_string_lossy().to_string();
    let parent = path
        .parent()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();
    let ext = Path::new(&name)
        .extension()
        .map(|e| e.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    let attrs = meta.file_attributes();

    Some(FileEntry {
        name,
        path: path.to_string_lossy().to_string(),
        parent_path: parent,
        is_dir: ft.is_dir(),
        size: meta.len(),
        modified_ms: meta
            .modified()
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0),
        created_ms: meta
            .created()
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0),
        is_hidden: attrs & 0x2 != 0,
        is_system: attrs & 0x4 != 0,
        is_readonly: meta.permissions().readonly(),
        ext,
    })
}

/// Walks `root` matching file names against `query` on the calling thread, streaming batches via `sink`.
pub fn run_search_blocking(
    root: String,
    query: String,
    opts: SearchOptions,
    cancel: Arc<AtomicBool>,
    sink: &mut dyn FnMut(SearchEvent),
) {
    let started = Instant::now();
    let root_path = std::path::PathBuf::from(&root);
    if !root_path.exists() {
        sink(SearchEvent::Error {
            message: format!("root does not exist: {root}"),
        });
        return;
    }

    let matcher = Matcher::new(&query);
    let mut walker = jwalk::WalkDir::new(&root_path).skip_hidden(!opts.include_hidden);
    if !opts.recursive {
        walker = walker.min_depth(1).max_depth(1);
    }

    const BATCH_SIZE: usize = 200;
    let max_results = opts.max_results.max(1) as u64;

    let mut batch: Vec<FileEntry> = Vec::with_capacity(BATCH_SIZE);
    let mut total: u64 = 0;
    let mut cancelled = false;

    for entry in walker.into_iter() {
        if cancel.load(Ordering::Relaxed) {
            cancelled = true;
            break;
        }
        let Ok(entry) = entry else { continue };
        if entry.depth() == 0 {
            continue;
        }
        let name = entry.file_name().to_string_lossy().to_string();
        if !matcher.matches(&name) {
            continue;
        }
        let Some(file_entry) = build_entry(&entry) else { continue };
        batch.push(file_entry);
        total += 1;
        if batch.len() >= BATCH_SIZE {
            sink(SearchEvent::Batch {
                entries: std::mem::take(&mut batch),
            });
            batch = Vec::with_capacity(BATCH_SIZE);
        }
        if total >= max_results {
            break;
        }
    }

    if !batch.is_empty() {
        sink(SearchEvent::Batch { entries: batch });
    }

    if cancelled {
        sink(SearchEvent::Error {
            message: "cancelled".to_string(),
        });
        return;
    }

    sink(SearchEvent::Done {
        total,
        duration_ms: started.elapsed().as_millis() as u64,
    });
}
