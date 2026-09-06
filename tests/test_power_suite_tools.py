"""Unit tests for the 10 Enterprise Power Suite system tools and utilities."""

import os
from pathlib import Path

from cortex_unified.system_tools.env_variable_manager import EnvironmentVariableManager, PathAnalysisReport
from cortex_unified.system_tools.service_manager import WindowsServiceManager, ServiceInfo
from cortex_unified.system_tools.font_cache_manager import FontCacheManager, FontAnalysisReport
from cortex_unified.system_tools.temp_folder_cleaner import TempFolderCleaner, TempScanReport
from cortex_unified.system_tools.context_menu_manager import ContextMenuManager, ContextMenuReport
from cortex_unified.system_tools.pagefile_optimizer import PagefileOptimizer, VirtualMemoryStatus
from cortex_unified.system_tools.diagnostic_data_manager import DiagnosticDataManager, TelemetryAuditReport
from cortex_unified.system_tools.startup_impact_analyzer import StartupImpactAnalyzer, StartupImpactReport
from cortex_unified.system_tools.slack_space_analyzer import SlackSpaceAnalyzer, VolumeSlackReport
from cortex_unified.system_tools.event_log_monitor import EventLogMonitor, AnomalyScanReport


def test_env_variable_manager():
    """Verify env variable manager via EnvironmentVariableManager.analyze_path."""
    rep = EnvironmentVariableManager.analyze_path()
    assert isinstance(rep, PathAnalysisReport)
    assert rep.total_entries >= 0
    assert rep.valid_entries >= 0


def test_service_manager():
    """Verify service manager via WindowsServiceManager.enumerate_services, bool."""
    services = WindowsServiceManager.enumerate_services()
    assert isinstance(services, list)
    if services:
        s = services[0]
        assert isinstance(s, ServiceInfo)
        assert bool(s.name)


def test_font_cache_manager():
    """Verify font cache manager via FontCacheManager.analyze."""
    rep = FontCacheManager.analyze()
    assert isinstance(rep, FontAnalysisReport)
    assert rep.total_fonts >= 0
    assert rep.total_size_bytes >= 0


def test_temp_folder_cleaner():
    """Verify temp folder cleaner via TempFolderCleaner.scan."""
    rep = TempFolderCleaner.scan(stale_hours=48)
    assert isinstance(rep, TempScanReport)
    assert len(rep.locations) > 0
    assert rep.total_files >= 0


def test_context_menu_manager():
    """Verify context menu manager via ContextMenuManager.analyze."""
    rep = ContextMenuManager.analyze()
    assert isinstance(rep, ContextMenuReport)
    assert rep.total_entries >= 0


def test_pagefile_optimizer():
    """Verify pagefile optimizer via PagefileOptimizer.get_status."""
    st = PagefileOptimizer.get_status()
    assert isinstance(st, VirtualMemoryStatus)
    assert st.total_physical_bytes > 0
    assert st.recommended_min_mb > 0
    assert st.recommended_max_mb >= st.recommended_min_mb


def test_diagnostic_data_manager():
    """Verify diagnostic data manager via DiagnosticDataManager.audit_telemetry."""
    rep = DiagnosticDataManager.audit_telemetry()
    assert isinstance(rep, TelemetryAuditReport)
    assert rep.total_settings > 0
    assert 0.0 <= rep.privacy_score_percent <= 100.0


def test_startup_impact_analyzer():
    """Verify startup impact analyzer via StartupImpactAnalyzer.analyze_startup."""
    rep = StartupImpactAnalyzer.analyze_startup()
    assert isinstance(rep, StartupImpactReport)
    assert rep.total_startup_items >= 0
    assert rep.estimated_boot_delay_seconds >= 0.0


def test_slack_space_analyzer(tmp_path):
    # Create test files with distinct sizes
    """Verify slack space analyzer via SlackSpaceAnalyzer.analyze_directory.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    f1 = tmp_path / "small.txt"
    f1.write_bytes(b"A" * 100)
    f2 = tmp_path / "medium.txt"
    f2.write_bytes(b"B" * 5000)

    rep = SlackSpaceAnalyzer.analyze_directory(tmp_path, max_depth=1)
    assert isinstance(rep, VolumeSlackReport)
    assert rep.total_files_scanned >= 2
    assert rep.cluster_size_bytes > 0
    assert rep.total_physical_bytes >= rep.total_logical_bytes
    assert rep.total_slack_waste_bytes >= 0


def test_event_log_monitor():
    """Verify event log monitor via EventLogMonitor.query_anomalies."""
    rep = EventLogMonitor.query_anomalies(max_events_per_category=2)
    assert isinstance(rep, AnomalyScanReport)
    assert rep.total_anomalies >= 0
