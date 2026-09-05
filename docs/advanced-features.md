# Cortex Workstation Advanced Features Guide

## Overview

This guide covers the advanced features of Cortex Workstation, including Docker cleanup, interactive visualizations, performance enhancements, package manager integration, heuristics-based detection, and accessibility features.

## Docker Cleanup

### Overview
The Docker cleanup feature helps free up significant disk space by removing unused Docker resources including images, containers, volumes, and networks.

### Basic Usage

```bash
# Show what would be cleaned (dry run)
cortex-workstation docker-cleanup

# Clean all Docker resources
cortex-workstation docker-cleanup --clean --all

# Clean specific resource types
cortex-workstation docker-cleanup --clean --images --volumes
```

### Resource Types

#### Docker Images
- **Dangling Images**: Images without tags or references
- **Unused Images**: Images not used by any container
- **Old Images**: Images older than specified threshold

```bash
# Clean only unused images
cortex-workstation docker-cleanup --clean --images

# Include verbose output to see image details
cortex-workstation docker-cleanup --clean --images --verbose
```

#### Docker Containers
- **Stopped Containers**: Containers that have exited
- **Failed Containers**: Containers that failed to start
- **Orphaned Containers**: Containers without parent images

```bash
# Clean stopped containers
cortex-workstation docker-cleanup --clean --containers
```

#### Docker Volumes
- **Unused Volumes**: Volumes not attached to any container
- **Orphaned Volumes**: Volumes from removed containers
- **Anonymous Volumes**: Volumes without explicit names

```bash
# Clean unused volumes (use with caution)
cortex-workstation docker-cleanup --clean --volumes
```

#### Docker Networks
- **Unused Networks**: Networks not used by any container
- **Default Networks**: System-created networks (preserved)
- **Custom Networks**: User-created networks

```bash
# Clean unused networks
cortex-workstation docker-cleanup --clean --networks
```

### Advanced Options

```bash
# Export findings to JSON for analysis
cortex-workstation docker-cleanup --export docker-analysis.json

# Skip confirmation prompts (automation)
cortex-workstation docker-cleanup --clean --all --yes

# Detailed logging
cortex-workstation docker-cleanup --clean --verbose --log-file docker-cleanup.log
```

### Safety Features
- Creates backup manifests for restoration
- Dry run mode by default
- Confirmation prompts for destructive actions
- Detailed logging of all operations

## Interactive Visualizations

### Overview
Cortex Workstation provides interactive visualizations to help understand disk usage patterns through TreeMaps, Sunburst charts, and comprehensive dashboards.

### TreeMap Visualization

TreeMaps show hierarchical disk usage where larger rectangles represent larger directories.

```bash
# Generate interactive TreeMap
cortex-workstation analyze-disk --export-treemap disk-usage.html

# Generate static image
cortex-workstation analyze-disk --export-treemap disk-usage.png

# Control depth for performance
cortex-workstation analyze-disk --export-treemap disk-usage.html --max-depth 4
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
cortex-workstation analyze-disk --export-sunburst disk-chart.html

# Export as SVG for scalability
cortex-workstation analyze-disk --export-sunburst disk-chart.svg
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
cortex-workstation analyze-disk --export-dashboard dashboard.html

# Include all analysis types
cortex-workstation analyze-disk --export-dashboard dashboard.html --max-depth 5
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

For large-scale operations, Cortex Workstation supports checkpoints to enable resumable scans.

```bash
# Enable checkpoints (save every 1000 directories)
cortex-workstation analyze-disk --checkpoint-interval 1000

# Resume from checkpoint
cortex-workstation analyze-disk --resume-from checkpoint_20231201_143022.json

# Custom checkpoint location
cortex-workstation analyze-disk --checkpoint-interval 500 --log-file /path/to/logs/
```

### Resource Management

Control system resource usage to prevent overloading.

```bash
# CPU priority control
cortex-workstation clean-empty --cpu-priority low     # Background processing
cortex-workstation clean-empty --cpu-priority normal  # Default
cortex-workstation clean-empty --cpu-priority high    # Foreground processing

# I/O priority control
cortex-workstation clean-empty --io-priority low      # Gentle on disk
cortex-workstation clean-empty --io-priority normal   # Default
cortex-workstation clean-empty --io-priority high     # Fast disk access

# Memory limits
cortex-workstation analyze-disk --memory-limit 512    # Limit to 512MB
cortex-workstation analyze-disk --memory-limit 2048   # Allow up to 2GB

# Thread control
cortex-workstation clean-empty --threads 2            # Limit CPU cores
cortex-workstation clean-empty --threads 8            # Use more cores
```

### Multi-Drive Scanning

Scan drives and directories sequentially or via PowerShell parallel pipelines.

```powershell
# Scan specific drive or mount point
cortex-workstation analyze-disk D:\

# Scan multiple fixed drives via PowerShell pipeline
"C:", "D:", "E:" | ForEach-Object {
    cortex-workstation analyze-disk $_ --export-json "$($_.Substring(0, 1))_analysis.json"
}
```

### Performance Monitoring

```bash
# Monitor system load during operations
cortex-workstation analyze-disk --verbose --cpu-priority low

# Export performance metrics
cortex-workstation analyze-disk --export-json analysis.json --verbose
```

## Package Manager Integration

### Supported Package Managers

Cortex Workstation supports cleaning caches and finding orphaned packages across multiple package managers:

- **Python**: pip, conda
- **Node.js**: npm, yarn
- **System**: apt (Ubuntu/Debian), dnf (Fedora), pacman (Arch), brew (macOS), chocolatey (Windows)

### Basic Usage

```bash
# Auto-detect and clean all package managers
cortex-workstation package-cleanup --clean --all

# Clean specific package managers
cortex-workstation package-cleanup --clean --pip --npm

# Find orphaned packages
cortex-workstation package-cleanup --orphaned --verbose
```

### Cache Management

```bash
# Keep recent cache files (last 30 days)
cortex-workstation package-cleanup --clean --keep-recent-days 30

# Clean with integrity verification
cortex-workstation package-cleanup --clean --npm  # npm includes integrity check

# Export cache analysis
cortex-workstation package-cleanup --export cache-analysis.json
```

### Orphaned Package Detection

```bash
# Find packages no longer needed
cortex-workstation package-cleanup --orphaned

# Clean orphaned packages (with confirmation)
cortex-workstation package-cleanup --orphaned --clean

# Detailed orphan analysis
cortex-workstation package-cleanup --orphaned --verbose --export orphans.json
```

### Safety Features

- **Manifest Backups**: Automatic backup manifests for deleted artifacts
- **Dry Run Safety**: Preview reclaimable space by default
- **Export Reports**: Generate JSON audit logs before deletion

```bash
# Preview pip cache without deleting
cortex-workstation package-cleanup --pip --dry-run

# Export findings to JSON before performing cleanup
cortex-workstation package-cleanup --export package-analysis.json

# Clean verified package caches
cortex-workstation package-cleanup --clean --pip --npm --yes
```

## Advanced Heuristics and Machine Learning

### Overview

The heuristics system uses machine learning and pattern recognition to detect application leftovers that traditional methods might miss.

### Basic Usage

```bash
# Scan with default settings
cortex-workstation heuristics-scan

# High confidence detection only
cortex-workstation heuristics-scan --confidence-threshold 0.9

# Include machine learning patterns
cortex-workstation heuristics-scan --ml-patterns
```

### Confidence Scoring

The system assigns confidence scores (0.0-1.0) to each detection:

- **0.9-1.0**: Very high confidence (likely safe to clean)
- **0.7-0.9**: High confidence (review recommended)
- **0.5-0.7**: Medium confidence (careful review required)
- **0.0-0.5**: Low confidence (manual verification needed)

```bash
# Only show high confidence items
cortex-workstation heuristics-scan --confidence-threshold 0.8

# Show all detections with scores
cortex-workstation heuristics-scan --confidence-threshold 0.0 --verbose
```

### Detection Types

#### Orphaned Application Folders
Detects leftover folders in common installation directories:

```bash
# Scan common installation paths
cortex-workstation heuristics-scan /path/to/programs

# Windows-specific paths
cortex-workstation heuristics-scan "C:\Program Files"
```

#### Installer Files and Duplicates
Finds temporary installer files and duplicate installers:

```bash
# Detect installer files
cortex-workstation heuristics-scan --verbose  # Shows installer detection

# Export findings for review
cortex-workstation heuristics-scan --export installer-analysis.json
```

#### Registry Analysis (Windows)
Correlates filesystem and registry entries to find orphaned references:

```bash
# Include registry analysis (Windows only)
cortex-workstation heuristics-scan --scan-registry

# Registry-only analysis
cortex-workstation heuristics-scan --scan-registry --confidence-threshold 0.8
```

### Machine Learning Patterns

The ML system learns from patterns to improve detection accuracy:

```bash
# Enable ML patterns (default)
cortex-workstation heuristics-scan --ml-patterns

# Disable ML for faster scanning
cortex-workstation heuristics-scan --no-ml-patterns

# Export findings with ML scores
cortex-workstation heuristics-scan --export ml-findings.json
```

### Safety and Review

```bash
# Always review before cleaning
cortex-workstation heuristics-scan --export review.json
# Review the JSON file before proceeding

# Clean with high confidence only
cortex-workstation heuristics-scan --clean --confidence-threshold 0.9

# Dry run with detailed output
cortex-workstation heuristics-scan --dry-run --verbose
```

## Broken Link Detection and Repair

### Overview

Comprehensive detection and repair of broken symlinks, shortcuts, and registry references across platforms.

### Basic Usage

```bash
# Scan for all types of broken links
cortex-workstation scan-broken-links

# Scan specific types
cortex-workstation scan-broken-links --scan-symlinks --scan-shortcuts

# Include repair attempts
cortex-workstation scan-broken-links --repair
```

### Link Types

#### Symlinks and Windows Shortcuts
```bash
# Scan for broken symlinks and shortcuts
cortex-workstation scan-broken-links --scan-symlinks --scan-shortcuts

# Scan registry references on Windows
cortex-workstation scan-broken-links --scan-registry
```

### Repair and Backup Options

```bash
# Repair detected links with confidence threshold
cortex-workstation scan-broken-links --repair --confidence-threshold 0.8

# Create safe backup manifest before repairing
cortex-workstation scan-broken-links --repair --backup

# Export findings to JSON
cortex-workstation scan-broken-links --export broken-links.json
```

## Internationalization and Accessibility

### Language Support

Cortex Workstation supports multiple languages with automatic detection:

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
cortex-workstation docker-cleanup --clean --all --yes --quiet

# JSON output for parsing
cortex-workstation analyze-disk --export-json analysis.json --quiet

# Exit codes for error handling
cortex-workstation clean-empty --delete || echo "Cleanup failed"
```

### Scheduled Operations (Windows Task Scheduler)

Automate routine cleanups using native Windows NT Task Scheduler (`schtasks.exe`):

```powershell
# Register weekly automated dry-run report
schtasks /create /tn "CortexWeeklyReport" /tr "cortex-workstation clean-empty --json-log --log-file C:\Logs\cleanup.log" /sc weekly /d SUN /st 02:00

# Query registered task status
schtasks /query /tn "CortexWeeklyReport"

# Trigger task on demand
schtasks /run /tn "CortexWeeklyReport"
```

### Configuration Management

```bash
# Execute command with custom YAML/JSON configuration
cortex-workstation clean-empty --config custom-settings.yaml

# Execute command ignoring configuration files
cortex-workstation clean-empty --no-config
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

This guide covers the advanced features of Cortex Workstation. For basic usage, see the main usage guide. For troubleshooting, refer to the troubleshooting guide.