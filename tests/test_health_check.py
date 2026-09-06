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
    """C using HealthCheck.

    Args:
        sev: The sev parameter.
    """
    return HealthCheck("x", "X", sev, "detail")


class TestScoring:
    """Group testscoring tests covering all good is a; info does not deduct; one warning; one critical; multiple criticals floor at zero; grade boundaries."""
    def test_all_good_is_a(self):
        """Verify all good is a via HealthChecker._score, _c."""
        score, grade = HealthChecker._score([_c("good"), _c("good"), _c("good")])
        assert score == 100 and grade == "A"

    def test_info_does_not_deduct(self):
        """Verify info does not deduct via HealthChecker._score, _c."""
        score, grade = HealthChecker._score([_c("info"), _c("info")])
        assert score == 100 and grade == "A"

    def test_one_warning(self):
        """Verify one warning via HealthChecker._score, _c."""
        score, _ = HealthChecker._score([_c("warning")])
        assert score == 88  # 100 - 12

    def test_one_critical(self):
        """Verify one critical via HealthChecker._score, _c."""
        score, grade = HealthChecker._score([_c("critical")])
        assert score == 70 and grade == "C"

    def test_multiple_criticals_floor_at_zero(self):
        """Verify multiple criticals floor at zero via HealthChecker._score, _c."""
        score, grade = HealthChecker._score([_c("critical")] * 10)
        assert score == 0 and grade == "F"

    def test_grade_boundaries(self):
        """Verify grade boundaries via HealthChecker._score, _c."""
        assert HealthChecker._score([])[1] == "A"
        # 100 - 12 - 12 = 76 -> B
        assert HealthChecker._score([_c("warning"), _c("warning")])[1] == "B"
        # 100 - 12*3 = 64 -> C
        assert HealthChecker._score([_c("warning")] * 3)[1] == "C"


class TestRun:
    """Group testrun tests covering run returns report; progress called; checks have valid severity; to dict."""
    def test_run_returns_report(self):
        """Verify run returns report via HealthChecker, run."""
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
        """Verify checks have valid severity via HealthChecker, run."""
        report = HealthChecker().run()
        for c in report.checks:
            assert c.severity in {"good", "warning", "critical", "info"}

    def test_to_dict(self):
        """Verify to dict via report.to_dict, HealthChecker, run."""
        report = HealthChecker().run()
        d = report.to_dict()
        assert set(d) == {"checks", "score", "grade"}
        assert isinstance(d["checks"], list)


class TestDiskSpaceCheck:
    """Group testdiskspacecheck tests covering disk space check runs."""
    def test_disk_space_check_runs(self):
        """Verify disk space check runs via HealthChecker._check_disk_space."""
        c = HealthChecker._check_disk_space()
        assert c.id == "disk_space"
        assert c.severity in {"good", "warning", "critical"}
        assert c.action_page == "dashboard"
