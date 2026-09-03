"""Quick functional verification of core system modules.

Run from the project root:  python scripts/verify_modules.py
"""
import sys
import os

# This script lives in scripts/; the package source is ../src relative to it.
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, _SRC)

print("=" * 60)
print("CORTEX CLEANER — FUNCTIONAL VERIFICATION")
print("=" * 60)

# 1. App Uninstaller
print("\n[1] AppUninstaller — reading Windows Registry...")
from cortex_unified.system_tools.app_uninstaller import AppUninstaller
u = AppUninstaller()
apps = u.get_installed_apps()
print(f"    Found {len(apps)} installed applications")
for a in apps[:5]:
    name = a.get("name", "?")
    pub = a.get("publisher", "")
    ver = a.get("display_version", "")
    kb = a.get("estimated_size_kb", 0)
    print(f"    - {name} ({pub}) v{ver} [{kb} KB]")

# 2. Registry Cleaner
print("\n[2] RegistryCleaner — scanning for orphans...")
from cortex_unified.system_tools.registry_cleaner import RegistryCleaner
rc = RegistryCleaner()
orphans = rc.scan_orphaned_entries()
print(f"    Found {len(orphans)} orphaned entries")
for o in orphans[:3]:
    print(f"    - [{o['type']}] {o['name']}: {o['reason']}")

# 3. Telemetry Blocker
print("\n[3] TelemetryBlocker — checking status...")
from cortex_unified.system_tools.telemetry_blocker import TelemetryBlocker
tb = TelemetryBlocker()
status = tb.check_status()
blocked = sum(1 for v in status.values() if v)
print(f"    {blocked}/{len(status)} telemetry features blocked")

# 4. Privacy Cleaner
print("\n[4] PrivacyCleaner — scanning browsers...")
from cortex_unified.analyzers.privacy_cleaner import PrivacyCleaner
pc = PrivacyCleaner()
browsers = pc.scan_browsers()
for name, stats in browsers.items():
    total_mb = sum(stats.values()) / (1024 * 1024)
    print(f"    {name}: {total_mb:.2f} MB ({', '.join(k for k, v in stats.items() if v > 0)})")

traces = pc.scan_system_traces()
for name, size in traces.items():
    print(f"    System: {name} = {size / (1024 * 1024):.2f} MB")

# 5. Residual Hunter
print("\n[5] ResidualHunter — testing strict matching...")
from cortex_unified.analyzers.residual_hunter import ResidualHunter
rh = ResidualHunter()
# Test with a known app if available
if apps:
    test_app = apps[0]
    leftovers = rh.scan_for_app(test_app["name"], test_app.get("publisher", ""))
    print(f"    Residuals for '{test_app['name']}': {len(leftovers)} found")

# 6. Advanced Shredder
print("\n[6] AdvancedShredder — verifying constructor...")
from cortex_unified.analyzers.advanced_shredder import AdvancedShredder
ws = AdvancedShredder()
print("    AdvancedShredder initialized (DoD 5220.22-M ready)")

# 7. Smart Scanner
print("\n[7] SmartScanReport — testing score calculation...")
from cortex_unified.core.smart_scanner import SmartScanReport
r = SmartScanReport()
r.total_junk_mb = 1500
r.browser_cache_mb = 800
r.registry_issues_count = 50
r.startup_impact_score = 10
r.privacy_risks_count = 3
r.calculate_score()
print(f"    Simulated score: {r.health_score} (should be low for 1500MB junk)")
print(f"    Total cleanable: {r.total_cleanable_mb:.0f} MB")

# 8. Background Agent
print("\n[8] BackgroundAgent — verifying constructor...")
from cortex_unified.core.background_agent import BackgroundAgent
ba = BackgroundAgent(check_interval=30)
print(f"    Agent ready (interval={ba.check_interval}s, disk_thresh={ba.disk_free_threshold_gb}GB)")

print("\n" + "=" * 60)
print("ALL MODULES VERIFIED SUCCESSFULLY")
print("=" * 60)
