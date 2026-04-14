# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-14

### Added
- **Core Engine:**
  - Parallel multi-threaded scanning capability
  - Resource throttling (CPU/RAM limits)
  - Pause/resume scanning with checkpoint persistence
- **New Analyzers:**
  - Duplicate file finder (MD5, SHA1)
  - Duplicate folder finder
  - Docker cleaner (images, containers, volumes, networks)
  - Windows registry broken link detector
  - Large file and old file finders
  - Broken symlink/shortcut detector
  - System temp and cache cleaners
  - Package manager cleaner (npm, pip, yarn cache)
  - Comprehensive disk space analyzer
- **System Tools:**
  - Startup manager and process analyzer
  - File shredder with configurable passes
  - Automated job scheduling
  - Exportable system reports
- **User Interfaces:**
  - Refined PySide6 GUI with comprehensive multi-tab dashboard
  - Extensive Click-based command line interface
- **Production CI/CD:**
  - automated testing pipeline with pytest
  - type hinting, linting checks via Github Actions
- **Safety Features:**
  - Interactive "dry run" defaults across all tools
  - Integration with OS recycle bin (`send2trash`)
  - Exclusions lists and custom heuristics filters

### Fixed
- Duplicate Click command definitions crashing CLI imports.
- Bare `raise` block error tracking in utilities module.
- Package module export misalignments.
