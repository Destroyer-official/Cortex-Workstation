"""Tests for boot-performance analysis (parsing Windows' own diagnostics)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.boot_performance import (
    BootIssue,
    BootPerformanceMonitor,
    BootRecord,
)

IS_WINDOWS = platform.system() == "Windows"


class TestParse:
    """Testparse.

    Manages TestParse operations and coordinates related state changes for the component.
    """
    def test_empty(self):
        """test_empty.

        Manages test empty operations and coordinates related state changes for the component.
        """
        boots, issues = BootPerformanceMonitor._parse(None)
        assert boots == [] and issues == []
        assert BootPerformanceMonitor._parse("garbage{") == ([], [])

    def test_parses_boots_and_issues(self):
        """test_parses_boots_and_issues.

        Manages test parses boots and issues operations and coordinates related state changes for the component.
        """
        payload = (
            '{"boots":[{"Time":"2026-07-08T09:00:00","BootTime":"42000","MainPath":"30000"},'
            '{"Time":"2026-07-07T08:00:00","BootTime":"38000","MainPath":"28000"}],'
            '"issues":[{"Id":"101","Name":"OneDrive.exe","TotalTime":"8000","Time":"2026-07-08T09:00:00"},'
            '{"Id":"103","Name":"SomeService","TotalTime":"12000","Time":"2026-07-08T09:00:00"}]}'
        )
        boots, issues = BootPerformanceMonitor._parse(payload)
        assert len(boots) == 2
        assert isinstance(boots[0], BootRecord)
        assert boots[0].boot_ms == 42000
        assert boots[0].boot_seconds == 42.0
        # Issues sorted by impact desc -> service (12s) before app (8s).
        assert len(issues) == 2
        assert issues[0].name == "SomeService"
        assert issues[0].kind == "Service"
        assert issues[0].impact_seconds == 12.0
        assert issues[1].kind == "Application"

    def test_single_object_not_list(self):
        # ConvertTo-Json emits a bare object when there's exactly one item.
        """test_single_object_not_list.

        Manages test single object not list operations and coordinates related state changes for the component.
        """
        payload = ('{"boots":{"Time":"t","BootTime":"50000","MainPath":"40000"},'
                   '"issues":{"Id":"102","Name":"nvlddmkm","TotalTime":"3000","Time":"t"}}')
        boots, issues = BootPerformanceMonitor._parse(payload)
        assert len(boots) == 1 and boots[0].boot_ms == 50000
        assert len(issues) == 1 and issues[0].kind == "Driver"

    def test_nameless_issue_skipped(self):
        """test_nameless_issue_skipped.

        Manages test nameless issue skipped operations and coordinates related state changes for the component.
        """
        payload = '{"boots":[],"issues":[{"Id":"101","Name":"","TotalTime":"1000"}]}'
        _, issues = BootPerformanceMonitor._parse(payload)
        assert issues == []

    def test_bad_numbers_coerce_zero(self):
        """test_bad_numbers_coerce_zero.

        Manages test bad numbers coerce zero operations and coordinates related state changes for the component.
        """
        payload = '{"boots":[{"Time":"t","BootTime":"n/a","MainPath":null}],"issues":[]}'
        boots, _ = BootPerformanceMonitor._parse(payload)
        assert boots[0].boot_ms == 0


class TestDataclasses:
    """Testdataclasses.

    Manages TestDataclasses operations and coordinates related state changes for the component.
    """
    def test_boot_seconds(self):
        """test_boot_seconds.

        Manages test boot seconds operations and coordinates related state changes for the component.
        """
        assert BootRecord("t", 42000, 30000).boot_seconds == 42.0

    def test_issue_to_dict(self):
        """test_issue_to_dict.

        Manages test issue to dict operations and coordinates related state changes for the component.
        """
        d = BootIssue("Application", "app.exe", 8000, "t").to_dict()
        assert d["impact_seconds"] == 8.0
        assert set(d) == {"kind", "name", "impact_ms", "impact_seconds", "when"}


class TestSupport:
    """Testsupport.

    Manages TestSupport operations and coordinates related state changes for the component.
    """
    def test_is_supported_matches_platform(self):
        """test_is_supported_matches_platform.

        Manages test is supported matches platform operations and coordinates related state changes for the component.
        """
        assert BootPerformanceMonitor.is_supported() == IS_WINDOWS

    def test_analyze_shape(self):
        """test_analyze_shape.

        Manages test analyze shape operations and coordinates related state changes for the component.
        """
        result = BootPerformanceMonitor().analyze()
        assert set(result) >= {"supported", "boots", "issues"}
        assert isinstance(result["boots"], list)
        if not IS_WINDOWS:
            assert result["supported"] is False
