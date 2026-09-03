import os
import sys
import pytest

sys.path.insert(0, 'src')

class FailureCollector:
    def __init__(self):
        self.failed = []
        self.passed = 0
        self.skipped = 0

    def pytest_runtest_logreport(self, report):
        if report.when == 'call':
            if report.failed:
                self.failed.append((report.nodeid, str(report.longrepr)))
            elif report.passed:
                self.passed += 1
            elif report.skipped:
                self.skipped += 1

collector = FailureCollector()
print("Running full test suite...")
ret = pytest.main(['-q', '-o', 'addopts=', 'tests'], plugins=[collector])

print(f"\n==========================================")
print(f"Test Suite Summary: Passed={collector.passed}, Failed={len(collector.failed)}, Skipped={collector.skipped}")
print(f"==========================================")

if collector.failed:
    print("\nFailed Tests:")
    for nodeid, err in collector.failed:
        print(f"\n--- FAILED: {nodeid} ---")
        # print first few lines of error
        err_lines = err.splitlines()
        print("\n".join(err_lines[-10:]))
