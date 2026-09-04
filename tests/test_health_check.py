"""Tests for the one-click health check (scoring logic + resilient run)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.health_check import (
    HealthCheck,
    HealthChecker,
    HealthReport,
)

IS_WINDOWS = platform.system() == "Windows"


def _c(sev):
    """C.

    Manages c operations and coordinates related state changes for the component.

    Args:
        sev: The sev parameter.
    """
    return HealthCheck("x", "X", sev, "detail")


class TestScoring:
    """Testscoring.

    Manages TestScoring operations and coordinates related state changes for the component.
    """
    def test_all_good_is_a(self):
        """test_all_good_is_a.

        Manages test all good is a operations and coordinates related state changes for the component.
        """
        score, grade = HealthChecker._score([_c("good"), _c("good"), _c("good")])
        assert score == 100 and grade == "A"

    def test_info_does_not_deduct(self):
        """test_info_does_not_deduct.

        Manages test info does not deduct operations and coordinates related state changes for the component.
        """
        score, grade = HealthChecker._score([_c("info"), _c("info")])
        assert score == 100 and grade == "A"

    def test_one_warning(self):
        """test_one_warning.

        Manages test one warning operations and coordinates related state changes for the component.
        """
        score, _ = HealthChecker._score([_c("warning")])
        assert score == 88  # 100 - 12

    def test_one_critical(self):
        """test_one_critical.

        Manages test one critical operations and coordinates related state changes for the component.
        """
        score, grade = HealthChecker._score([_c("critical")])
        assert score == 70 and grade == "C"

    def test_multiple_criticals_floor_at_zero(self):
        """test_multiple_criticals_floor_at_zero.

        Manages test multiple criticals floor at zero operations and coordinates related state changes for the component.
        """
        score, grade = HealthChecker._score([_c("critical")] * 10)
        assert score == 0 and grade == "F"

    def test_grade_boundaries(self):
        """test_grade_boundaries.

        Manages test grade boundaries operations and coordinates related state changes for the component.
        """
        assert HealthChecker._score([])[1] == "A"
        # 100 - 12 - 12 = 76 -> B
        assert HealthChecker._score([_c("warning"), _c("warning")])[1] == "B"
        # 100 - 12*3 = 64 -> C
        assert HealthChecker._score([_c("warning")] * 3)[1] == "C"


class TestRun:
    """Testrun.

    Manages TestRun operations and coordinates related state changes for the component.
    """
    def test_run_returns_report(self):
        """test_run_returns_report.

        Manages test run returns report operations and coordinates related state changes for the component.
        """
        report = HealthChecker().run()
        assert isinstance(report, HealthReport)
        assert 0 <= report.score <= 100
        assert report.grade in {"A", "B", "C", "D", "F"}
        # At least the cross-platform checks (disk space, memory) always run.
        ids = {c.id for c in report.checks}
        assert "disk_space" in ids
        assert "memory" in ids

    def test_progress_called(self):
        """test_progress_called.

        Updates progress bar widgets, percentage counters, and status indicators with streaming status updates from the running worker.
        """
        msgs = []
        HealthChecker().run(progress=msgs.append)
        assert len(msgs) >= 2

    def test_checks_have_valid_severity(self):
        """test_checks_have_valid_severity.

        Manages test checks have valid severity operations and coordinates related state changes for the component.
        """
        report = HealthChecker().run()
        for c in report.checks:
            assert c.severity in {"good", "warning", "critical", "info"}

    def test_to_dict(self):
        """test_to_dict.

        Manages test to dict operations and coordinates related state changes for the component.
        """
        report = HealthChecker().run()
        d = report.to_dict()
        assert set(d) == {"checks", "score", "grade"}
        assert isinstance(d["checks"], list)


class TestDiskSpaceCheck:
    """Testdiskspacecheck.

    Manages TestDiskSpaceCheck operations and coordinates related state changes for the component.
    """
    def test_disk_space_check_runs(self):
        """test_disk_space_check_runs.

        Manages test disk space check runs operations and coordinates related state changes for the component.
        """
        c = HealthChecker._check_disk_space()
        assert c.id == "disk_space"
        assert c.severity in {"good", "warning", "critical"}
        assert c.action_page == "dashboard"
