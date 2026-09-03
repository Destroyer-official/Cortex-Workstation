#ifndef NEXUS_ENGINE_H
#define NEXUS_ENGINE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>
#include <stdint.h>

// Opaque handles
typedef void* NexusHandle;
typedef void* NexusJobHandle;

// File entry structure
typedef struct {
    char* name;
    char* path;
    char* parent_path;
    int is_dir;
    uint64_t size;
    uint64_t modified_ms;
    uint64_t created_ms;
    int is_hidden;
    int is_system;
    int is_readonly;
    char* ext;
} NexusFileEntry;

// Drive info structure
typedef struct {
    char* path;
    char* label;
    char* drive_type;
    char* filesystem;
    uint64_t free_bytes;
    uint64_t total_bytes;
    int is_ready;
} NexusDriveInfo;

// Search options
typedef struct {
    int recursive;
    unsigned int max_results;
    int include_hidden;
} NexusSearchOptions;

// Text preview
typedef struct {
    char* content;
    int truncated;
    uint64_t size;
} NexusTextPreview;

// Job summary
typedef struct {
    char* job_id;
    char* kind;
    char* state;
    uint64_t total_files;
    uint64_t processed_files;
    uint64_t total_bytes;
    uint64_t processed_bytes;
    double speed_bps;
    double eta_seconds;
    char* current_file;
    unsigned int conflicts_pending;
} NexusJobSummary;

// Callback types
typedef void (*NexusListCallback)(
    void* user_data,
    const NexusFileEntry* entries,
    size_t count,
    int done,
    const char* error
);

typedef void (*NexusProgressCallback)(
    void* user_data,
    const char* job_id,
    uint64_t processed_bytes,
    uint64_t total_bytes,
    double speed_bps,
    double eta_seconds,
    const char* current_file
);

typedef void (*NexusCompletionCallback)(
    void* user_data,
    const char* job_id,
    int success,
    const char* error
);

typedef int (*NexusConflictCallback)(
    void* user_data,
    const char* job_id,
    const char* conflict_id,
    const char* source,
    const char* destination,
    uint64_t source_size,
    uint64_t dest_size,
    uint64_t source_mtime,
    uint64_t dest_mtime,
    int is_dir
);

typedef void (*NexusSearchCallback)(
    void* user_data,
    const NexusFileEntry* entries,
    size_t count,
    int done,
    const char* error
);

typedef void (*NexusFsEventCallback)(
    void* user_data,
    const char* path
);

// Lifecycle
NexusHandle nexus_init(void);
void nexus_free(NexusHandle ctx);
const char* nexus_version(void);

// Directory operations
int nexus_scan_dir(
    NexusHandle ctx,
    const char* path,
    NexusListCallback callback,
    void* user_data
);

int nexus_cancel_scan(NexusHandle ctx, const char* scan_id);

int nexus_read_dir_sync(
    NexusHandle ctx,
    const char* path,
    NexusFileEntry** out_entries,
    size_t* out_count
);

void nexus_free_entries(NexusFileEntry* entries, size_t count);

// File operations
/* Contract: NexusHandle must remain valid for as long as any scan, search,
 * watch or job started from it may still invoke callbacks. */
NexusJobHandle nexus_copy(
    NexusHandle ctx,
    const char* const* sources,
    size_t sources_count,
    const char* dest_dir,
    NexusProgressCallback progress_cb,
    NexusCompletionCallback completion_cb,
    NexusConflictCallback conflict_cb,
    void* user_data
);

NexusJobHandle nexus_move(
    NexusHandle ctx,
    const char* const* sources,
    size_t sources_count,
    const char* dest_dir,
    NexusProgressCallback progress_cb,
    NexusCompletionCallback completion_cb,
    NexusConflictCallback conflict_cb,
    void* user_data
);

NexusJobHandle nexus_delete(
    NexusHandle ctx,
    const char* const* paths,
    size_t paths_count,
    int to_trash,
    NexusProgressCallback progress_cb,
    NexusCompletionCallback completion_cb,
    void* user_data
);

int nexus_pause_job(NexusJobHandle handle);
int nexus_resume_job(NexusJobHandle handle);
int nexus_cancel_job(NexusJobHandle handle);
void nexus_free_job_handle(NexusJobHandle handle);

// Search
int nexus_search_files(
    NexusHandle ctx,
    const char* root,
    const char* query,
    const NexusSearchOptions* options,
    NexusSearchCallback callback,
    void* user_data
);

/* Cancels the search identified by search_id; if search_id is NULL, the most
 * recently started search in the calling thread is cancelled.
 * Returns 0 on success, -1 if no matching active search exists. */
int nexus_cancel_search(NexusHandle ctx, const char* search_id);

/* Copies the id of the most recent search started from this thread into
 * *out_id (caller frees with nexus_free_string). Returns 0 or -1 if none. */
int nexus_last_search_id(NexusHandle ctx, char** out_id);

// Filesystem watch
int nexus_watch_dir(
    NexusHandle ctx,
    const char* path,
    NexusFsEventCallback callback,
    void* user_data
);

int nexus_unwatch_dir(NexusHandle ctx, const char* path);

// Drive operations
int nexus_get_drives(
    NexusHandle ctx,
    NexusDriveInfo** out_drives,
    size_t* out_count
);

void nexus_free_drives(NexusDriveInfo* drives, size_t count);

// Utilities
int nexus_home_dir(NexusHandle ctx, char** out_path);
void nexus_free_string(char* str);
int nexus_rename(NexusHandle ctx, const char* path, const char* new_name);
int nexus_create_folder(NexusHandle ctx, const char* parent, const char* name);
int nexus_read_text_file(
    NexusHandle ctx,
    const char* path,
    uint32_t max_bytes,
    char** out_content,
    int* out_truncated,
    uint64_t* out_size
);
int nexus_open_path(NexusHandle ctx, const char* path);
int nexus_reveal_in_shell(NexusHandle ctx, const char* path);

#ifdef __cplusplus
}
#endif

#endif // NEXUS_ENGINE_H