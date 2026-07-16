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
    return HealthCheck("x", "X", sev, "detail")


class TestScoring:
    def test_all_good_is_a(self):
        score, grade = HealthChecker._score([_c("good"), _c("good"), _c("good")])
        assert score == 100 and grade == "A"

    def test_info_does_not_deduct(self):
        score, grade = HealthChecker._score([_c("info"), _c("info")])
        assert score == 100 and grade == "A"

    def test_one_warning(self):
        score, _ = HealthChecker._score([_c("warning")])
        assert score == 88  # 100 - 12

    def test_one_critical(self):
        score, grade = HealthChecker._score([_c("critical")])
        assert score == 70 and grade == "C"

    def test_multiple_criticals_floor_at_zero(self):
        score, grade = HealthChecker._score([_c("critical")] * 10)
        assert score == 0 and grade == "F"

    def test_grade_boundaries(self):
        assert HealthChecker._score([])[1] == "A"
        # 100 - 12 - 12 = 76 -> B
        assert HealthChecker._score([_c("warning"), _c("warning")])[1] == "B"
        # 100 - 12*3 = 64 -> C
        assert HealthChecker._score([_c("warning")] * 3)[1] == "C"


class TestRun:
    def test_run_returns_report(self):
        report = HealthChecker().run()
        assert isinstance(report, HealthReport)
        assert 0 <= report.score <= 100
        assert report.grade in {"A", "B", "C", "D", "F"}
        # At least the cross-platform checks (disk space, memory) always run.
        ids = {c.id for c in report.checks}
        assert "disk_space" in ids
        assert "memory" in ids

    def test_progress_called(self):
        msgs = []
        HealthChecker().run(progress=msgs.append)
        assert len(msgs) >= 2

    def test_checks_have_valid_severity(self):
        report = HealthChecker().run()
        for c in report.checks:
            assert c.severity in {"good", "warning", "critical", "info"}

    def test_to_dict(self):
        report = HealthChecker().run()
        d = report.to_dict()
        assert set(d) == {"checks", "score", "grade"}
        assert isinstance(d["checks"], list)


class TestDiskSpaceCheck:
    def test_disk_space_check_runs(self):
        c = HealthChecker._check_disk_space()
        assert c.id == "disk_space"
        assert c.severity in {"good", "warning", "critical"}
        assert c.action_page == "dashboard"
