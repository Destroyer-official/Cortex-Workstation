//! Scan registry tracking active directory scans and their cancellation flags.

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use parking_lot::Mutex;

/// Shared registry mapping scan ids to their cancellation flags.
#[derive(Clone, Default)]
pub struct ScanRegistry {
    flags: Arc<Mutex<HashMap<String, Arc<AtomicBool>>>>,
}

impl ScanRegistry {
    /// Creates an empty registry.
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers a cancellation flag under `id`.
    pub fn insert(&self, id: String, flag: Arc<AtomicBool>) {
        self.flags.lock().insert(id, flag);
    }

    /// Signals cancellation for `id`; returns true if the scan was registered.
    pub fn cancel(&self, id: &str) -> bool {
        match self.flags.lock().get(id) {
            Some(flag) => {
                flag.store(true, Ordering::SeqCst);
                true
            }
            None => false,
        }
    }

    /// Removes and returns the flag registered under `id`.
    pub fn remove(&self, id: &str) -> Option<Arc<AtomicBool>> {
        self.flags.lock().remove(id)
    }
}
