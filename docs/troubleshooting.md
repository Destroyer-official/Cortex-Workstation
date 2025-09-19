# Deep Cleaner Troubleshooting Guide

## Common Issues and Solutions

### Docker Cleanup Issues

#### Docker Not Available
**Problem**: Error message "Docker is not available"
**Solutions**:
1. Ensure Docker Desktop is installed and running
2. Check Docker daemon status: `docker info`
3. Verify user permissions for Docker access
4. On Linux, add user to docker group: `sudo usermod -aG docker $USER`

#### Permission Denied Errors
**Problem**: Cannot access Docker resources
**Solutions**:
1. Run with administrator/sudo privileges
2. Check Docker daemon permissions
3. Verify Docker API version compatibility

#### Large Docker Images Not Detected
**Problem**: Known unused images not showing up
**Solutions**:
1. Use `--verbose` flag to see detailed scanning
2. Check if images are actually unused with `docker image ls`
3. Verify image tags and references

### Package Manager Cleanup Issues

#### Package Manager Not Detected
**Problem**: Known package manager not found
**Solutions**:
1. Ensure package manager is in system PATH
2. Check if package manager is properly installed
3. Use `--verbose` to see detection process
4. Manually specify with individual flags (--pip, --npm, etc.)

#### Cache Cleaning Fails
**Problem**: Cannot clean package manager cache
**Solutions**:
1. Check disk space and permissions
2. Close applications using the package manager
3. Run with elevated privileges if needed
4. Verify package manager is not corrupted

#### Orphaned Package Detection Issues
**Problem**: No orphaned packages found when expected
**Solutions**:
1. Update package manager databases first
2. Check if dependency analysis is working correctly
3. Some package managers may not support orphan detection

### Visualization and Analysis Issues

#### Visualization Export Fails
**Problem**: Cannot export TreeMap or Sunburst charts
**Solutions**:
1. Check available disk space for export
2. Ensure output directory is writable
3. Install required dependencies: `pip install plotly kaleido`
4. Try different export formats (HTML vs PNG/SVG)

#### Large Dataset Performance
**Problem**: Analysis is slow or runs out of memory
**Solutions**:
1. Use `--memory-limit` to control memory usage
2. Reduce `--max-depth` for visualization
3. Use `--checkpoint-interval` for resumable scans
4. Increase `--threads` for faster processing

#### Interactive Dashboard Not Loading
**Problem**: Dashboard HTML file doesn't work in browser
**Solutions**:
1. Check browser JavaScript is enabled
2. Try opening in different browser
3. Check for browser security restrictions on local files
4. Use a local web server to serve the file

### Performance and Scalability Issues

#### Scan Checkpoints Not Working
**Problem**: Cannot resume from checkpoint
**Solutions**:
1. Verify checkpoint file exists and is readable
2. Check checkpoint file is not corrupted
3. Ensure same configuration is used for resume
4. Clear old checkpoints and start fresh

#### High CPU/Memory Usage
**Problem**: Deep Cleaner consuming too many resources
**Solutions**:
1. Use `--cpu-priority low` and `--io-priority low`
2. Set `--memory-limit` to reasonable value
3. Reduce `--threads` count
4. Use `--checkpoint-interval` to save progress frequently

#### Multi-Drive Scanning Issues
**Problem**: Cannot scan multiple drives or network locations
**Solutions**:
1. Check drive permissions and accessibility
2. Ensure network drives are properly mounted
3. Use appropriate credentials for network access
4. Check for drive disconnections during scan

### Heuristics and Machine Learning Issues

#### Low Confidence Scores
**Problem**: All detections have low confidence scores
**Solutions**:
1. Lower `--confidence-threshold` to see more results
2. Ensure ML patterns are properly loaded
3. Check if training data is available
4. Use `--verbose` to see confidence calculation details

#### False Positives in Detection
**Problem**: Legitimate files flagged as leftovers
**Solutions**:
1. Increase `--confidence-threshold` for higher accuracy
2. Review results carefully before cleaning
3. Use exclude patterns for known good directories
4. Disable `--ml-patterns` if causing issues

#### Registry Analysis Fails (Windows)
**Problem**: Cannot analyze Windows registry
**Solutions**:
1. Run with administrator privileges
2. Check Windows registry permissions
3. Ensure registry backup is created first
4. Disable registry scanning if problematic

### Internationalization and Accessibility Issues

#### Language Not Changing
**Problem**: Interface remains in English despite language setting
**Solutions**:
1. Check if translation files are installed
2. Verify locale setting in configuration
3. Restart application after language change
4. Check system locale settings

#### Keyboard Shortcuts Not Working
**Problem**: Accessibility shortcuts don't respond
**Solutions**:
1. Check if keyboard navigation is enabled
2. Verify no conflicting shortcuts in system
3. Try different key combinations
4. Check focus is on correct widget

#### Screen Reader Compatibility
**Problem**: Screen reader not announcing changes
**Solutions**:
1. Ensure screen reader is running and configured
2. Check accessibility features are enabled
3. Verify ARIA labels are properly set
4. Test with different screen reader software

### File System and Permission Issues

#### Access Denied Errors
**Problem**: Cannot access certain directories or files
**Solutions**:
1. Run with administrator/sudo privileges
2. Check file and directory permissions
3. Ensure files are not in use by other applications
4. Use exclude patterns for inaccessible locations

#### Symlink and Shortcut Issues
**Problem**: Broken link detection not working properly
**Solutions**:
1. Check if symlinks are supported on file system
2. Verify shortcut file formats (.lnk on Windows)
3. Ensure target paths are accessible
4. Check for circular symlink references

#### Network Drive Problems
**Problem**: Cannot scan network drives
**Solutions**:
1. Ensure network drives are properly mounted
2. Check network connectivity and credentials
3. Use UNC paths instead of mapped drives
4. Handle timeouts with appropriate settings

## Diagnostic Commands

### Enable Debug Logging
```bash
# Enable verbose logging for troubleshooting
deep-cleaner <command> --verbose --log-file debug.log

# Enable JSON logging for structured analysis
deep-cleaner <command> --json-log --log-file debug.json
```

### System Information
```bash
# Check system processes and services
deep-cleaner analyze-processes --export system-info.json

# List startup items
deep-cleaner list-startup-items

# Generate comprehensive report
deep-cleaner generate-report --type html --export system-report.html
```

### Performance Testing
```bash
# Test with different thread counts
deep-cleaner clean-empty --threads 1 --verbose
deep-cleaner clean-empty --threads 4 --verbose
deep-cleaner clean-empty --threads 8 --verbose

# Test memory usage
deep-cleaner analyze-disk --memory-limit 512 --verbose

# Test checkpoint functionality
deep-cleaner analyze-disk --checkpoint-interval 100 --verbose
```

## Getting Help

### Command-Specific Help
```bash
# Get help for specific commands
deep-cleaner docker-cleanup --help
deep-cleaner package-cleanup --help
deep-cleaner heuristics-scan --help
```

### Configuration Validation
```bash
# Test configuration file
deep-cleaner clean-empty --config ~/.deepcleaner.yaml --dry-run --verbose

# Test without configuration
deep-cleaner clean-empty --no-config --dry-run --verbose
```

### Export Diagnostic Information
```bash
# Export comprehensive diagnostic report
deep-cleaner generate-report --type json --export diagnostic-report.json

# Export system analysis
deep-cleaner analyze-processes --export process-analysis.json

# Export disk analysis
deep-cleaner analyze-disk --export-json disk-analysis.json
```

## Performance Optimization Tips

### For Large Datasets
1. Use checkpoints for resumable operations
2. Limit memory usage with `--memory-limit`
3. Reduce visualization depth with `--max-depth`
4. Use appropriate thread counts for your system

### For Network Drives
1. Use local caching when possible
2. Handle timeouts gracefully
3. Use appropriate I/O priority settings
4. Consider excluding network locations for performance

### For Resource-Constrained Systems
1. Use low CPU and I/O priority
2. Limit concurrent operations
3. Use streaming processing for large files
4. Enable garbage collection optimizations

## Reporting Issues

When reporting issues, please include:

1. **System Information**: OS, Python version, Deep Cleaner version
2. **Command Used**: Exact command line with options
3. **Error Messages**: Complete error output
4. **Log Files**: Debug logs with `--verbose --log-file`
5. **Configuration**: Your configuration file (remove sensitive data)
6. **Expected vs Actual**: What you expected vs what happened

### Example Bug Report Template
```
**System**: Windows 11, Python 3.11, Deep Cleaner 2.0.0
**Command**: deep-cleaner docker-cleanup --clean --all --verbose
**Error**: Docker API connection failed
**Logs**: [Attach debug.log file]
**Config**: [Attach sanitized config file]
**Expected**: Should clean Docker resources
**Actual**: Connection error to Docker daemon
```

## Advanced Troubleshooting

### Memory Profiling
```python
# Add to your Python environment for memory debugging
import tracemalloc
tracemalloc.start()

# Run Deep Cleaner operations
# ...

# Get memory statistics
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
```

### Performance Profiling
```bash
# Profile with cProfile
python -m cProfile -o profile.stats -m deep_cleaner.cli clean-empty

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### Network Debugging
```bash
# Test network connectivity
ping target-server
telnet target-server 445  # SMB
telnet target-server 22   # SSH

# Test drive mounting
net use  # Windows
mount    # Linux/macOS
```

This troubleshooting guide should help resolve most common issues with Deep Cleaner's advanced features.