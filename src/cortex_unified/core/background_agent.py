"""Background Agent — lightweight real-time system monitor.

Runs in a QThread, samples CPU / RAM / Disk every N seconds,
and emits Qt Signals that the SystemTrayManager can display as
balloon notifications.
"""

import os
import time
import logging
import platform
from PySide6.QtCore import QObject, Signal


class BackgroundAgent(QObject):
    """Silently monitors system resources in a background thread."""

    alert_high_ram = Signal(float)
    alert_high_cpu = Signal(float)
    alert_low_disk = Signal(float)          # free GB
    status_update = Signal(dict)

    def __init__(self, check_interval: int = 10):
        super().__init__()
        self.logger = logging.getLogger("background_agent")
        self.check_interval = check_interval
        self._is_running = False

        # Thresholds
        self.ram_threshold = 90.0   # percent
        self.cpu_threshold = 90.0   # percent
        self.disk_free_threshold_gb = 5.0

        # Cooldowns — don't spam the user
        self._last_ram_alert = 0.0
        self._last_cpu_alert = 0.0
        self._last_disk_alert = 0.0
        self._alert_cooldown = 300  # 5 minutes between repeated alerts

    def start_monitoring(self):
        """Main loop — called when the owning QThread starts."""
        try:
            import psutil
        except ImportError:
            self.logger.error("psutil is not installed — background monitor disabled")
            return

        self._is_running = True
        self.logger.info("Background monitoring started (interval=%ds)", self.check_interval)

        while self._is_running:
            try:
                mem = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)

                # Determine the system drive path for disk_usage
                if platform.system() == "Windows":
                    drive = os.environ.get("SystemDrive", "C:")
                    disk_path = drive + "\\"
                else:
                    disk_path = "/"

                disk = psutil.disk_usage(disk_path)

                stats = {
                    "ram_percent": mem.percent,
                    "cpu_percent": cpu,
                    "disk_free_gb": disk.free / (1024 ** 3),
                    "disk_total_gb": disk.total / (1024 ** 3),
                }
                self.status_update.emit(stats)

                now = time.time()

                if mem.percent > self.ram_threshold and (now - self._last_ram_alert) > self._alert_cooldown:
                    self.alert_high_ram.emit(mem.percent)
                    self._last_ram_alert = now

                if cpu > self.cpu_threshold and (now - self._last_cpu_alert) > self._alert_cooldown:
                    self.alert_high_cpu.emit(cpu)
                    self._last_cpu_alert = now

                free_gb = disk.free / (1024 ** 3)
                if free_gb < self.disk_free_threshold_gb and (now - self._last_disk_alert) > self._alert_cooldown:
                    self.alert_low_disk.emit(free_gb)
                    self._last_disk_alert = now

            except Exception as exc:
                self.logger.debug("Monitor tick error: %s", exc)

            time.sleep(self.check_interval)

    def stop(self):
        self._is_running = False
