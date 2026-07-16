"""System Tray Manager — manages the tray icon, background agent, and notifications."""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QStyle
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, QThread
import os

from cortex_unified.core.background_agent import BackgroundAgent


class SystemTrayManager(QObject):
    """Manages the system tray icon, context menu, and background monitoring alerts."""

    def __init__(self, main_window, app):
        super().__init__()
        self.main_window = main_window
        self.app = app

        self.tray_icon = QSystemTrayIcon(self)

        # Icon — use bundled icon or fall back to a standard OS icon
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            style = QApplication.style()
            self.tray_icon.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))

        self.tray_icon.setToolTip("Cortex Cleaner — System Monitor")
        self._setup_menu()
        self.tray_icon.show()

        # Background agent
        self.agent = BackgroundAgent(check_interval=15)
        self.agent_thread = QThread()
        self.agent.moveToThread(self.agent_thread)

        self.agent_thread.started.connect(self.agent.start_monitoring)
        self.agent.alert_high_ram.connect(self._on_high_ram)
        self.agent.alert_high_cpu.connect(self._on_high_cpu)
        self.agent.alert_low_disk.connect(self._on_low_disk)

        self.agent_thread.start()

    # ── Menu ──────────────────────────────────────────────────────────

    def _setup_menu(self):
        menu = QMenu()

        show_action = QAction("Open Cortex Cleaner", self)
        show_action.triggered.connect(self._show_main_window)
        menu.addAction(show_action)

        menu.addSeparator()

        smart_clean = QAction("Instant Smart Scan", self)
        smart_clean.triggered.connect(self._run_instant_scan)
        menu.addAction(smart_clean)

        menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._quit_app)
        menu.addAction(exit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_main_window()

    def _show_main_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _run_instant_scan(self):
        self._show_main_window()
        if hasattr(self.main_window, "navigation_controller"):
            nc = self.main_window.navigation_controller
            nc.set_current_tab_by_name("Dashboard")
            dashboard = nc.get_tab_by_name("Dashboard")
            if dashboard and hasattr(dashboard, "run_smart_scan"):
                dashboard.run_smart_scan()

    def _quit_app(self):
        self.agent.stop()
        self.agent_thread.quit()
        self.agent_thread.wait(3000)
        self.tray_icon.hide()
        self.app.quit()

    # ── Alert notifications ───────────────────────────────────────────

    def _on_high_ram(self, value):
        self.tray_icon.showMessage(
            "High Memory Usage",
            f"System RAM is at {value:.0f}%.  Click the tray icon to launch Cortex Cleaner and free resources.",
            QSystemTrayIcon.Warning,
            8000,
        )

    def _on_high_cpu(self, value):
        self.tray_icon.showMessage(
            "High CPU Usage",
            f"CPU is at {value:.0f}%.  Consider disabling startup programs via Cortex Cleaner.",
            QSystemTrayIcon.Information,
            8000,
        )

    def _on_low_disk(self, free_gb):
        self.tray_icon.showMessage(
            "Low Disk Space ⚠️",
            f"Only {free_gb:.1f} GB free on your system drive.  "
            f"Open Cortex Cleaner to clean junk files.",
            QSystemTrayIcon.Critical,
            10000,
        )
