# 🎛️ Configuration Reference

Cortex Workstation supports flexible configuration via YAML/JSON configuration files, environment variables, and interactive GUI preferences.

---

## 📁 Configuration File Locations

Cortex Workstation searches for configuration files in the following priority order:
1. Custom path specified via CLI: `--config <path>`
2. Working directory: `./cortex_config.yaml`
3. Per-user application data: `~/.cortex_cleaner/config.yaml`

---

## ⚙️ Core Configuration Schema

```yaml
# Global Safety & Operational Defaults
default_action: "dry_run"         # "dry_run" | "recycle" | "delete"
min_age_days: 1                   # Minimum file age in days before eligible for cleanup
follow_symlinks: false            # Never traverse symlinks or NTFS junctions
json_logging: false               # Structured JSON logs for SIEM integration

# Exclusions & Security Boundaries
exclude_patterns:
  - "*.sys"
  - "*.lock"
  - "*.dat"
exclude_dirs:
  - "C:\\Windows"
  - "C:\\Program Files"
  - "C:\\Program Files (x86)"

# Performance & Concurrency Tuning
performance:
  threads: 0                      # 0 = auto-detect CPU cores
  cpu_priority: "normal"          # "idle" | "below_normal" | "normal" | "high"
  io_priority: "low"              # "very_low" | "low" | "normal"
  memory_limit_mb: 2048           # Max memory usage for indexing buffers
  enable_streaming: true          # Stream large directories to reduce RAM pressure

# UI & Display Themes
ui:
  theme: "dark"                   # "dark" (Cortex Midnight) | "light" (Cortex Daylight)
  locale: "en"                    # "en", "de", "es", "fr", "zh", "ja"
  scale_factor: 1.0               # HiDPI scale factor
  show_animations: true
```

---

## 🌐 Environment Variables

Override settings without editing files via environment variables:

| Variable | Type | Description |
| :--- | :--- | :--- |
| `CORTEX_CONFIG` | String | Path to custom YAML/JSON configuration file |
| `CORTEX_THEME` | String | Force theme (`dark` or `light`) |
| `CORTEX_LOCALE` | String | Force UI language (`en`, `de`, `es`, `fr`, `zh`, `ja`) |
| `CORTEX_LOG_LEVEL` | String | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CORTEX_DRY_RUN` | Boolean | `1` to force non-destructive mode everywhere |
| `QT_QPA_PLATFORM` | String | Set to `offscreen` for headless CLI / CI environments |
