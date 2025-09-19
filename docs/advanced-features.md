# Deep Cleaner Advanced Features Guide

## Overview

This guide covers the advanced features of Deep Cleaner, including Docker cleanup, interactive visualizations, performance enhancements, package manager integration, heuristics-based detection, and accessibility features.

## Docker Cleanup

### Overview
The Docker cleanup feature helps free up significant disk space by removing unused Docker resources including images, containers, volumes, and networks.

### Basic Usage

```bash
# Show what would be cleaned (dry run)
deep-cleaner docker-cleanup

# Clean all Docker resources
deep-cleaner docker-cleanup --clean --all

# Clean specific resource types
deep-cleaner docker-cleanup --clean --images --volumes
```

### Resource Types

#### Docker Images
- **Dangling Images**: Images without tags or references
- **Unused Images**: Images not used by any container
- **Old Images**: Images older than specified threshold

```bash
# Clean only unused images
deep-cleaner docker-cleanup --clean --images

# Include verbose output to see image details
deep-cleaner docker-cleanup --clean --images --verbose
```

#### Docker Containers
- **Stopped Containers**: Containers that have exited
- **Failed Containers**: Containers that failed to start
- **Orphaned Containers**: Containers without parent images

```bash
# Clean stopped containers
deep-cleaner docker-cleanup --clean --containers
```

#### Docker Volumes
- **Unused Volumes**: Volumes not attached to any container
- **Orphaned Volumes**: Volumes from removed containers
- **Anonymous Volumes**: Volumes without explicit names

```bash
# Clean unused volumes (use with caution)
deep-cleaner docker-cleanup --clean --volumes
```

#### Docker Networks
- **Unused Networks**: Networks not used by any container
- **Default Networks**: System-created networks (preserved)
- **Custom Networks**: User-created networks

```bash
# Clean unused networks
deep-cleaner docker-cleanup --clean --networks
```

### Advanced Options

```bash
# Export findings to JSON for analysis
deep-cleaner docker-cleanup --export docker-analysis.json

# Skip confirmation prompts (automation)
deep-cleaner docker-cleanup --clean --all --yes

# Detailed logging
deep-cleaner docker-cleanup --clean --verbose --log-file docker-cleanup.log
```

### Safety Features
- Creates backup manifests for restoration
- Dry run mode by default
- Confirmation prompts for destructive actions
- Detailed logging of all operations

## Interactive Visualizations

### Overview
Deep Cleaner provides interactive visualizations to help understand disk usage patterns through TreeMaps, Sunburst charts, and comprehensive dashboards.

### TreeMap Visualization

TreeMaps show hierarchical disk usage where larger rectangles represent larger directories.

```bash
# Generate interactive TreeMap
deep-cleaner analyze-disk --export-treemap disk-usage.html

# Generate static image
deep-cleaner analyze-disk --export-treemap disk-usage.png

# Control depth for performance
deep-cleaner analyze-disk --export-treemap disk-usage.html --max-depth 4
```

**Features**:
- Interactive drill-down navigation
- Hover tooltips with size information
- Color coding by file type or age
- Zoom and pan functionality
- Context menus for file operations

### Sunburst Charts

Sunburst charts display directory hierarchies in a circular format with nested rings.

```bash
# Generate Sunburst chart
deep-cleaner analyze-disk --export-sunburst disk-chart.html

# Export as SVG for scalability
deep-cleaner analyze-disk --export-sunburst disk-chart.svg
```

**Features**:
- Radial hierarchy display
- Interactive segment selection
- Proportional sizing by disk usage
- Smooth animations and transitions
- Export in multiple formats

### Interactive Dashboard

The dashboard combines multiple visualization types with real-time data updates.

```bash
# Create comprehensive dashboard
deep-cleaner analyze-disk --export-dashboard dashboard.html

# Include all analysis types
deep-cleaner analyze-disk --export-dashboard dashboard.html --max-depth 5
```

**Dashboard Components**:
- TreeMap and Sunburst views
- File type breakdown charts
- Largest directories listing
- Disk usage statistics
- Real-time data refresh
- Export functionality

### Customization Options

```bash
# Control visualization depth
--max-depth 3          # Shallow analysis (faster)
--max-depth 7          # Deep analysis (more detail)

# Performance tuning
--memory-limit 1024    # Limit memory usage (MB)
--threads 4            # Control CPU usage
```

## Performance and Scalability

### Checkpoint System

For large-scale operations, Deep Cleaner supports checkpoints to enable resumable scans.

```bash
# Enable checkpoints (save every 1000 directories)
deep-cleaner analyze-disk --checkpoint-interval 1000

# Resume from checkpoint
deep-cleaner analyze-disk --resume-from checkpoint_20231201_143022.json

# Custom checkpoint location
deep-cleaner analyze-disk --checkpoint-interval 500 --log-file /path/to/logs/
```

### Resource Management

Control system resource usage to prevent overloading.

```bash
# CPU priority control
deep-cleaner clean-empty --cpu-priority low     # Background processing
deep-cleaner clean-empty --cpu-priority normal  # Default
deep-cleaner clean-empty --cpu-priority high    # Foreground processing

# I/O priority control
deep-cleaner clean-empty --io-priority low      # Gentle on disk
deep-cleaner clean-empty --io-priority normal   # Default
deep-cleaner clean-empty --io-priority high     # Fast disk access

# Memory limits
deep-cleaner analyze-disk --memory-limit 512    # Limit to 512MB
deep-cleaner analyze-disk --memory-limit 2048   # Allow up to 2GB

# Thread control
deep-cleaner clean-empty --threads 2            # Limit CPU cores
deep-cleaner clean-empty --threads 8            # Use more cores
```

### Multi-Drive Scanning

Scan multiple drives and locations simultaneously.

```bash
# Scan multiple drives (Windows)
deep-cleaner scan-multi-drive --drives "C:,D:,E:" --parallel

# Scan with different priorities per drive
deep-cleaner scan-multi-drive --drives "C:,\\server\share" --network-timeout 30

# Handle network drives
deep-cleaner scan-multi-drive --drives "\\server\share" --credentials user:pass
```

### Performance Monitoring

```bash
# Monitor system load during operations
deep-cleaner analyze-disk --verbose --cpu-priority low

# Export performance metrics
deep-cleaner analyze-disk --export-json analysis.json --verbose
```

## Package Manager Integration

### Supported Package Managers

Deep Cleaner supports cleaning caches and finding orphaned packages across multiple package managers:

- **Python**: pip, conda
- **Node.js**: npm, yarn
- **System**: apt (Ubuntu/Debian), dnf (Fedora), pacman (Arch), brew (macOS), chocolatey (Windows)

### Basic Usage

```bash
# Auto-detect and clean all package managers
deep-cleaner package-cleanup --clean --all

# Clean specific package managers
deep-cleaner package-cleanup --clean --pip --npm

# Find orphaned packages
deep-cleaner package-cleanup --orphaned --verbose
```

### Cache Management

```bash
# Keep recent cache files (last 30 days)
deep-cleaner package-cleanup --clean --keep-recent-days 30

# Clean with integrity verification
deep-cleaner package-cleanup --clean --npm  # npm includes integrity check

# Export cache analysis
deep-cleaner package-cleanup --export cache-analysis.json
```

### Orphaned Package Detection

```bash
# Find packages no longer needed
deep-cleaner package-cleanup --orphaned

# Clean orphaned packages (with confirmation)
deep-cleaner package-cleanup --orphaned --clean

# Detailed orphan analysis
deep-cleaner package-cleanup --orphaned --verbose --export orphans.json
```

### Safety Features

- **Package List Backups**: Automatic backup before changes
- **Integrity Verification**: Verify package manager health after cleaning
- **Rollback Support**: Restore from backups if needed
- **Dependency Analysis**: Understand package relationships

```bash
# Create backup before cleaning
deep-cleaner package-cleanup --clean --pip  # Automatic backup

# Verify package manager health
deep-cleaner package-cleanup --verify-health

# Restore from backup (if needed)
deep-cleaner restore-packages --backup package-backup-20231201.json
```

## Advanced Heuristics and Machine Learning

### Overview

The heuristics system uses machine learning and pattern recognition to detect application leftovers that traditional methods might miss.

### Basic Usage

```bash
# Scan with default settings
deep-cleaner heuristics-scan

# High confidence detection only
deep-cleaner heuristics-scan --confidence-threshold 0.9

# Include machine learning patterns
deep-cleaner heuristics-scan --ml-patterns
```

### Confidence Scoring

The system assigns confidence scores (0.0-1.0) to each detection:

- **0.9-1.0**: Very high confidence (likely safe to clean)
- **0.7-0.9**: High confidence (review recommended)
- **0.5-0.7**: Medium confidence (careful review required)
- **0.0-0.5**: Low confidence (manual verification needed)

```bash
# Only show high confidence items
deep-cleaner heuristics-scan --confidence-threshold 0.8

# Show all detections with scores
deep-cleaner heuristics-scan --confidence-threshold 0.0 --verbose
```

### Detection Types

#### Orphaned Application Folders
Detects leftover folders in common installation directories:

```bash
# Scan common installation paths
deep-cleaner heuristics-scan /path/to/programs

# Windows-specific paths
deep-cleaner heuristics-scan "C:\Program Files"
```

#### Installer Files and Duplicates
Finds temporary installer files and duplicate installers:

```bash
# Detect installer files
deep-cleaner heuristics-scan --verbose  # Shows installer detection

# Export findings for review
deep-cleaner heuristics-scan --export installer-analysis.json
```

#### Registry Analysis (Windows)
Correlates filesystem and registry entries to find orphaned references:

```bash
# Include registry analysis (Windows only)
deep-cleaner heuristics-scan --scan-registry

# Registry-only analysis
deep-cleaner heuristics-scan --scan-registry --confidence-threshold 0.8
```

### Machine Learning Patterns

The ML system learns from patterns to improve detection accuracy:

```bash
# Enable ML patterns (default)
deep-cleaner heuristics-scan --ml-patterns

# Disable ML for faster scanning
deep-cleaner heuristics-scan --no-ml-patterns

# Update ML models (if available)
deep-cleaner update-ml-models
```

### Safety and Review

```bash
# Always review before cleaning
deep-cleaner heuristics-scan --export review.json
# Review the JSON file before proceeding

# Clean with high confidence only
deep-cleaner heuristics-scan --clean --confidence-threshold 0.9

# Dry run with detailed output
deep-cleaner heuristics-scan --dry-run --verbose
```

## Broken Link Detection and Repair

### Overview

Comprehensive detection and repair of broken symlinks, shortcuts, and registry references across platforms.

### Basic Usage

```bash
# Scan for all types of broken links
deep-cleaner scan-broken-links

# Scan specific types
deep-cleaner scan-broken-links --scan-symlinks --scan-shortcuts

# Include repair attempts
deep-cleaner scan-broken-links --repair
```

### Link Types

#### Symlinks (All Platforms)
```bash
# Scan for broken symlinks
deep-cleaner scan-broken-links --scan-symlinks

# Attempt repair with target search
deep-cleaner scan-broken-links --scan-symlinks --repair --search-targets
```

#### Windows Shortcuts (.lnk files)
```bash
# Scan Windows shortcuts
deep-cleaner scan-broken-links --scan-shortcuts

# Repair with heuristic target finding
deep-cleaner scan-broken-links --scan-shortcuts --repair --heuristic-search
```

#### Registry References (Windows)
```bash
# Scan registry for broken file references
deep-cleaner scan-broken-links --scan-registry

# Cross-reference with filesystem
deep-cleaner scan-broken-links --scan-registry --cross-reference
```

### Repair Options

```bash
# Automatic repair with confirmation
deep-cleaner scan-broken-links --repair --confidence-threshold 0.8

# Manual repair mode
deep-cleaner scan-broken-links --repair --interactive

# Backup before repair
deep-cleaner scan-broken-links --repair --backup
```

## Internationalization and Accessibility

### Language Support

Deep Cleaner supports multiple languages with automatic detection:

```bash
# Set language in configuration
locale: "es"  # Spanish
locale: "fr"  # French
locale: "de"  # German
locale: "zh"  # Chinese
locale: "auto"  # Auto-detect
```

### Accessibility Features

#### Keyboard Navigation
- Full keyboard navigation support
- Customizable keyboard shortcuts
- Focus management and indicators

#### Screen Reader Support
- ARIA labels and descriptions
- Change announcements
- Accessible table and tree navigation

#### Visual Accessibility
- High contrast themes
- Scalable fonts and UI elements
- Color-blind friendly palettes

### Configuration

```yaml
# Internationalization settings
i18n:
  locale: "auto"
  fallback_locale: "en"
  rtl_support: true

# Accessibility settings
accessibility:
  enable_keyboard_shortcuts: true
  enable_screen_reader: true
  high_contrast_theme: false
  announce_changes: true
  keyboard_shortcuts:
    scan: "Ctrl+S"
    clean: "Ctrl+D"
    settings: "Ctrl+,"
```

## Integration and Automation

### Scripting and Automation

```bash
# Non-interactive mode for scripts
deep-cleaner docker-cleanup --clean --all --yes --quiet

# JSON output for parsing
deep-cleaner analyze-disk --export-json analysis.json --quiet

# Exit codes for error handling
deep-cleaner clean-empty --delete || echo "Cleanup failed"
```

### Scheduled Operations

```bash
# Create scheduled cleanup task
deep-cleaner schedule-task --name "weekly-cleanup" --command "clean-empty --delete" --schedule "weekly"

# List scheduled tasks
deep-cleaner list-scheduled-tasks

# Run scheduled task manually
deep-cleaner run-scheduled-task --name "weekly-cleanup"
```

### Configuration Management

```bash
# Validate configuration
deep-cleaner validate-config --config ~/.deepcleaner.yaml

# Export default configuration
deep-cleaner export-default-config > default-config.yaml

# Merge configurations
deep-cleaner merge-configs --base base.yaml --override custom.yaml --output merged.yaml
```

## Best Practices

### Performance Optimization

1. **Use Appropriate Depth**: Limit `--max-depth` for visualizations
2. **Resource Limits**: Set `--memory-limit` and `--cpu-priority`
3. **Checkpoints**: Use for long-running operations
4. **Parallel Processing**: Enable for multi-drive scans

### Safety Guidelines

1. **Always Test First**: Use dry-run mode before cleaning
2. **Review Heuristics**: Check confidence scores carefully
3. **Backup Important Data**: Enable manifest creation
4. **Incremental Cleaning**: Clean in stages, not all at once

### Maintenance

1. **Regular Updates**: Keep ML models and patterns updated
2. **Configuration Review**: Periodically review and update settings
3. **Log Monitoring**: Check logs for errors and performance issues
4. **Cleanup Validation**: Verify system health after major cleanups

This guide covers the advanced features of Deep Cleaner. For basic usage, see the main usage guide. For troubleshooting, refer to the troubleshooting guide.