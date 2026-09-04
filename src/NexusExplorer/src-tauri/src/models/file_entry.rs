use serde::{Deserialize, Serialize};

/// A single file or directory row returned by listing and search.
#[derive(Serialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct FileEntry {
    pub name: String,
    pub path: String,
    pub parent_path: String,
    pub is_dir: bool,
    pub size: u64,
    pub modified_ms: u64,
    pub created_ms: u64,
    pub is_hidden: bool,
    pub is_system: bool,
    pub is_readonly: bool,
    pub ext: String,
}

/// A mounted drive/volume with capacity and readiness info.
#[derive(Serialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct DriveInfo {
    pub path: String,
    pub label: String,
    pub drive_type: String,
    pub filesystem: String,
    pub free_bytes: u64,
    pub total_bytes: u64,
    pub is_ready: bool,
}

/// Identifies a started directory scan and the root it covers.
#[derive(Serialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct ScanStart {
    pub scan_id: String,
    pub root_path: String,
}

/// Bounded text preview of a file with truncation and total-size metadata.
#[derive(Serialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct TextPreview {
    pub content: String,
    pub truncated: bool,
    pub size: u64,
}

/// Point-in-time progress snapshot for a copy/move/delete job.
#[derive(Serialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct JobSummary {
    pub job_id: String,
    pub kind: String,
    pub state: String,
    pub total_files: u64,
    pub processed_files: u64,
    pub total_bytes: u64,
    pub processed_bytes: u64,
    pub speed_bps: f64,
    pub eta_secs: f64,
    pub current_file: Option<String>,
    pub conflicts_pending: u32,
}

/// Filename search options: recursion, result cap, and hidden-file inclusion.
#[derive(Serialize, Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct SearchOptions {
    pub recursive: bool,
    pub max_results: u32,
    pub include_hidden: bool,
}
