//! Job registry and control plane for long-running file operations.

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;

use parking_lot::Mutex;

use crate::models::JobSummary;

/// Shared per-job control flags and live counters.
pub struct JobControl {
    pub kind: String,
    pub cancel: AtomicBool,
    pub paused: AtomicBool,
    pub resume_notify: tokio::sync::Notify,
    pub state: Mutex<String>,
    pub total_files: AtomicU64,
    pub processed_files: AtomicU64,
    pub total_bytes: AtomicU64,
    pub processed_bytes: AtomicU64,
    pub speed_bps: Mutex<f64>,
    pub eta_secs: Mutex<f64>,
    pub current_file: Mutex<Option<String>>,
    pub errors: Mutex<Vec<String>>,
    pub pending_conflicts: Mutex<Vec<(String, tokio::sync::oneshot::Sender<String>)>>,
    pub apply_all: Mutex<Option<String>>,
    /// Small files whose integrity check is deferred to end-of-job batching.
    pub deferred_verify: Mutex<Vec<(std::path::PathBuf, std::path::PathBuf)>>,
}

impl JobControl {
    /// Creates a new job control in the `running` state for the given job kind.
    pub fn new(kind: &str) -> Self {
        Self {
            kind: kind.to_string(),
            cancel: AtomicBool::new(false),
            paused: AtomicBool::new(false),
            resume_notify: tokio::sync::Notify::new(),
            state: Mutex::new("running".to_string()),
            total_files: AtomicU64::new(0),
            processed_files: AtomicU64::new(0),
            total_bytes: AtomicU64::new(0),
            processed_bytes: AtomicU64::new(0),
            speed_bps: Mutex::new(0.0),
            eta_secs: Mutex::new(0.0),
            current_file: Mutex::new(None),
            errors: Mutex::new(Vec::new()),
            pending_conflicts: Mutex::new(Vec::new()),
            apply_all: Mutex::new(None),
            deferred_verify: Mutex::new(Vec::new()),
        }
    }

    /// Blocks while the job is paused; returns false if cancellation was requested.
    pub fn wait_while_paused(&self) -> bool {
        while self.paused.load(Ordering::Relaxed) {
            if self.cancel.load(Ordering::Relaxed) {
                return false;
            }
            std::thread::sleep(std::time::Duration::from_millis(120));
        }
        !self.cancel.load(Ordering::Relaxed)
    }

    /// Stores the new terminal/transient job state string.
    pub fn set_state(&self, state: &str) {
        *self.state.lock() = state.to_string();
    }

    /// Builds a point-in-time `JobSummary` snapshot for the given job id.
    pub fn snapshot(&self, job_id: &str) -> JobSummary {
        JobSummary {
            job_id: job_id.to_string(),
            kind: self.kind.clone(),
            state: self.state.lock().clone(),
            total_files: self.total_files.load(Ordering::Relaxed),
            processed_files: self.processed_files.load(Ordering::Relaxed),
            total_bytes: self.total_bytes.load(Ordering::Relaxed),
            processed_bytes: self.processed_bytes.load(Ordering::Relaxed),
            speed_bps: *self.speed_bps.lock(),
            eta_secs: *self.eta_secs.lock(),
            current_file: self.current_file.lock().clone(),
            conflicts_pending: self.pending_conflicts.lock().len() as u32,
        }
    }
}

/// Registry of all known jobs (terminal jobs remain until app exits).
#[derive(Clone, Default)]
pub struct JobManager {
    jobs: Arc<Mutex<HashMap<String, Arc<JobControl>>>>,
}

impl JobManager {
    /// Creates an empty job registry with no tracked jobs.
    pub fn new() -> Self {
        Self::default()
    }

    /// Inserts a job control under the given job id, replacing any existing entry.
    pub fn register(&self, id: String, control: Arc<JobControl>) {
        self.jobs.lock().insert(id, control);
    }

    /// Returns the job control for the given job id, if still tracked.
    pub fn get(&self, id: &str) -> Option<Arc<JobControl>> {
        self.jobs.lock().get(id).cloned()
    }

    /// Collects a snapshot summary for every tracked job.
    pub fn list_summaries(&self) -> Vec<JobSummary> {
        self.jobs
            .lock()
            .iter()
            .map(|(id, c)| c.snapshot(id))
            .collect()
    }

    /// Delivers a conflict resolution to the waiting engine thread.
    pub fn resolve(
        &self,
        job_id: &str,
        conflict_id: &str,
        resolution: String,
        apply_to_all: bool,
    ) -> Result<(), String> {
        let control = self.get(job_id).ok_or_else(|| "job not found".to_string())?;
        if apply_to_all {
            *control.apply_all.lock() = Some(resolution.clone());
        }
        let mut pending = control.pending_conflicts.lock();
        if let Some(pos) = pending.iter().position(|(id, _)| id == conflict_id) {
            let (_, tx) = pending.remove(pos);
            let _ = tx.send(resolution);
            Ok(())
        } else {
            Err("conflict not found".to_string())
        }
    }
}
