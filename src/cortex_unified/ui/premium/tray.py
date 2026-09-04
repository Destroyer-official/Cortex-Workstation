"""Premium system tray: a background presence with a live resource monitor.

The README advertises "background monitoring" and a tray presence; this brings
that to the premium shell in a way that is safe for the app's staged shutdown.

Two deliberate design choices:

* **GUI-thread sampling, not a worker thread.** ``core.background_agent`` runs a
  ``QThread`` whose loop blocks in ``time.sleep(interval)`` (up to 15s). That is
  hostile to the window's bounded close (a sleeping thread would overrun the
  close grace and force the hard-exit path on every quit). Instead this samples
  with a :class:`QTimer` on the GUI thread using non-blocking ``psutil`` calls,
  so there is no thread to join and closing stays instant.
* **Programmatic icon.** No icon asset ships with the package, so the tray glyph
  is painted from the active :class:`~.theme.Palette` (DPR-aware, like
  ``widgets.placeholder_icon``) and re-rendered when the theme changes, keeping
  the tray consistent with the window with zero external files.

Everything is availability-gated: on a headless/offscreen host or a desktop
without a system tray, :class:`PremiumTray` constructs cleanly and simply does
nothing, so it never breaks startup or tests.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import time
from collections.abc import Mapping
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .theme import Palette

_LOG = logging.getLogger("cortex.ui.premium.tray")

# Resource alert policy (mirrors core.background_agent so behaviour is
# consistent between the legacy and premium shells).
_RAM_THRESHOLD = 90.0          # percent
_CPU_THRESHOLD = 90.0          # percent
_DISK_FREE_THRESHOLD_GB = 5.0  # GB free on the system drive
_ALERT_COOLDOWN_S = 300.0      # 5 min between repeats of the same alert
_SAMPLE_INTERVAL_MS = 5000     # how often the GUI-thread timer samples


def _render_tray_icon(palette: Palette, size: int = 64) -> QIcon:
    """Paint a token-styled tray glyph from the palette (DPR-aware).

    Draws the Cortex brand mark on an accent-gradient rounded badge entirely
    from :class:`~.theme.Palette` colors, so the tray icon matches the active
    theme without shipping any asset. Any failure degrades to an empty
    ``QIcon`` rather than raising - a missing tray glyph must never break
    startup.
    """
    dpr = 1.0
    try:
        app = QApplication.instance()
        val = float(app.devicePixelRatio()) if app is not None else 1.0
        if val and val > 0:
            dpr = val
    except Exception:  # noqa: BLE001 - headless / no app: keep dpr = 1.0
        dpr = 1.0
    try:
        backing = max(1, int(round(size * dpr)))
        pm = QPixmap(backing, backing)
        pm.setDevicePixelRatio(dpr)
        pm.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Accent-gradient rounded badge.
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0.0, QColor(palette.accent))
        grad.setColorAt(1.0, QColor(palette.accent_2))
        radius = size * 0.28
        pad = size * 0.08
        painter.setPen(QPen(QColor(0, 0, 0, 0), 0))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(pad, pad, size - 2 * pad, size - 2 * pad, radius, radius)

        # Brand mark, centered, in the on-accent colour. Drawn from the shipped
        # SVG rather than a text glyph: Qt 6 bundles no fonts, so a codepoint
        # like U+26E8 depended on system font fallback and rendered at a
        # different weight - or as a tofu box - depending on the machine.
        from .icons import pixmap as _icon_pixmap

        mark = int(size * 0.56)
        glyph = _icon_pixmap("brand", mark, palette.on_accent)
        if not glyph.isNull():
            logical = glyph.width() / max(glyph.devicePixelRatio(), 1.0)
            offset = (size - logical) / 2.0
            painter.drawPixmap(int(offset), int(offset), glyph)
        painter.end()
        return QIcon(pm)
    except Exception:  # noqa: BLE001 - cosmetic only
        _LOG.debug("could not render tray icon", exc_info=True)
        return QIcon()


class PremiumTray(QObject):
    """A system-tray presence with a live, GUI-thread resource monitor.

    Constructing this is always safe. When a system tray is unavailable the
    instance is inert (``available`` is ``False``) and every method is a no-op,
    so callers never need to branch on platform support.
    """

    def __init__(self, window, settings):
        """__init__.

        Initializes the instance and configures internal state.

        Args:
            window: Parent window or shell controller instance.
            settings: The settings parameter.
        """
        super().__init__(window)
        self._window = window
        self._settings = settings
        self._tray: QSystemTrayIcon | None = None
        self._timer: QTimer | None = None
        self._network_timer: QTimer | None = None
        self._network_outcome_mtime = 0
        self._psutil = None
        # Alert cooldown bookkeeping (monotonic seconds).
        self._last_ram_alert = 0.0
        self._last_cpu_alert = 0.0
        self._last_disk_alert = 0.0
        self._last_network_alerts: dict[str, float] = {}

        if not self._tray_supported():
            _LOG.info("system tray not available; tray features disabled")
            return

        try:
            self._tray = QSystemTrayIcon(window)
            self._tray.setIcon(_render_tray_icon(window.palette_tokens))
            self._tray.setToolTip("Cortex Cleaner")
            self._tray.setContextMenu(self._build_menu())
            self._tray.activated.connect(self._on_activated)
            self._tray.show()
        except Exception:  # noqa: BLE001 - tray creation must never break startup
            _LOG.debug("failed to create system tray icon", exc_info=True)
            self._tray = None
            return

        self._start_monitor()
        self._start_network_alert_monitor()
        _LOG.info("premium system tray active (resource monitor on)")

    # -- availability -------------------------------------------------------

    @staticmethod
    def _tray_supported() -> bool:
        """_tray_supported.

        Manages tray supported operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        try:
            return bool(QSystemTrayIcon.isSystemTrayAvailable())
        except Exception:  # noqa: BLE001
            return False

    @property
    def available(self) -> bool:
        """Available.

        Manages available operations and coordinates related state changes for the component.

        Returns:
            bool: True if the operation succeeded, False otherwise.
        """
        return self._tray is not None

    # -- menu / activation --------------------------------------------------

    def _build_menu(self) -> QMenu:
        """_build_menu.

        Manages build menu operations and coordinates related state changes for the component.

        Returns:
            QMenu: Result of the operation.
        """
        menu = QMenu()
        open_act = QAction("Open Cortex Cleaner", menu)
        open_act.triggered.connect(self._restore_window)
        menu.addAction(open_act)

        health_act = QAction("Run Health Check", menu)
        health_act.triggered.connect(self._run_health_check)
        menu.addAction(health_act)

        menu.addSeparator()
        quit_act = QAction("Exit", menu)
        quit_act.triggered.connect(self._quit_app)
        menu.addAction(quit_act)
        return menu

    def _on_activated(self, reason) -> None:
        """_on_activated.

        Manages on activated operations and coordinates related state changes for the component.

        Args:
            reason: The reason parameter.
        """
        # A left click / double click on the icon restores the window; the
        # context menu (right click) is handled by Qt itself.
        try:
            trigger = QSystemTrayIcon.ActivationReason.Trigger
            double = QSystemTrayIcon.ActivationReason.DoubleClick
        except Exception:  # noqa: BLE001
            self._restore_window()
            return
        if reason in (trigger, double):
            self._restore_window()

    def _restore_window(self) -> None:
        """_restore_window.

        Manages restore window operations and coordinates related state changes for the component.
        """
        w = self._window
        try:
            if w.isMinimized():
                w.showNormal()
            else:
                w.show()
            w.raise_()
            w.activateWindow()
        except Exception:  # noqa: BLE001 - restoring must never crash the tray
            _LOG.debug("could not restore window from tray", exc_info=True)

    def _run_health_check(self) -> None:
        """_run_health_check.

        Manages run health check operations and coordinates related state changes for the component.
        """
        self._restore_window()
        try:
            self._window._select("health")
            page = self._window._pages.get("health")
            # Only kick a fresh scan if the page isn't mid-run (its run button
            # is disabled while a scan is in flight).
            run_btn = getattr(page, "run_btn", None)
            if page is not None and hasattr(page, "_run") and (run_btn is None or run_btn.isEnabled()):
                page._run()
        except Exception:  # noqa: BLE001
            _LOG.debug("could not start health check from tray", exc_info=True)

    def _quit_app(self) -> None:
        """_quit_app.

        Manages quit app operations and coordinates related state changes for the component.
        """
        # Mark a real quit so the window's close-to-tray guard steps aside, then
        # close normally (runs the staged worker shutdown).
        try:
            self._window._force_quit = True
            self._window.close()
        except Exception:  # noqa: BLE001
            _LOG.debug("tray quit failed; falling back to app.quit", exc_info=True)
            app = QApplication.instance()
            if app is not None:
                app.quit()

    # -- resource monitor (GUI-thread QTimer) -------------------------------

    def _start_monitor(self) -> None:
        """_start_monitor.

        Manages start monitor operations and coordinates related state changes for the component.
        """
        try:
            import psutil
            self._psutil = psutil
        except Exception:  # noqa: BLE001 - no psutil: run without the monitor
            _LOG.info("psutil unavailable; tray resource monitor disabled")
            self._psutil = None
            return
        # Prime cpu_percent so the first real sample isn't a meaningless 0.0.
        try:
            self._psutil.cpu_percent(interval=None)
        except Exception:  # noqa: BLE001
            pass
        self._timer = QTimer(self)
        self._timer.setInterval(_SAMPLE_INTERVAL_MS)
        self._timer.timeout.connect(self._sample)
        self._timer.start()

    def _sample(self) -> None:
        """Sample.

        Manages sample operations and coordinates related state changes for the component.
        """
        ps = self._psutil
        if ps is None or self._tray is None:
            return
        try:
            mem = ps.virtual_memory()
            cpu = ps.cpu_percent(interval=None)  # non-blocking: since last call
            if platform.system() == "Windows":
                disk_path = os.environ.get("SystemDrive", "C:") + "\\"
            else:
                disk_path = "/"
            disk = ps.disk_usage(disk_path)
            free_gb = disk.free / (1024 ** 3)
        except Exception as exc:  # noqa: BLE001 - a bad sample is never fatal
            _LOG.debug("resource sample failed: %s", exc)
            return

        now = time.monotonic()
        pct = getattr(mem, "percent", 0.0)
        if pct > _RAM_THRESHOLD and (now - self._last_ram_alert) > _ALERT_COOLDOWN_S:
            self._alert("High memory usage", f"RAM is at {pct:.0f}%. Consider closing unused apps.")
            self._last_ram_alert = now
        if cpu > _CPU_THRESHOLD and (now - self._last_cpu_alert) > _ALERT_COOLDOWN_S:
            self._alert("High CPU usage", f"CPU is at {cpu:.0f}%. A background process may be busy.")
            self._last_cpu_alert = now
        if free_gb < _DISK_FREE_THRESHOLD_GB and (now - self._last_disk_alert) > _ALERT_COOLDOWN_S:
            self._alert("Low disk space", f"Only {free_gb:.1f} GB free. Run a cleanup to reclaim space.")
            self._last_disk_alert = now

    def _start_network_alert_monitor(self) -> None:
        """Poll only the bounded outcome written by the fixed scheduled CLI.

        Manages start network alert monitor operations and coordinates related state changes for the component.
        """
        self._network_timer = QTimer(self)
        self._network_timer.setInterval(_SAMPLE_INTERVAL_MS)
        self._network_timer.timeout.connect(self._poll_network_outcome)
        self._network_timer.start()

    def _poll_network_outcome(self) -> None:
        """_poll_network_outcome.

        Manages poll network outcome operations and coordinates related state changes for the component.
        """
        path = (
            Path.home() / ".cortex_cleaner" / "netdata" /
            "last-scheduled-network-scan.json")
        try:
            stat = path.stat()
            if stat.st_mtime_ns <= self._network_outcome_mtime:
                return
            self._network_outcome_mtime = stat.st_mtime_ns
            if stat.st_size > 2 * 1024 * 1024:
                return
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return
        if not isinstance(payload, Mapping):
            return
        changes = payload.get("inventory_changes")
        if isinstance(changes, Mapping):
            self.notify_network_changes(changes)

    # -- notifications ------------------------------------------------------

    def _alert(self, title: str, message: str) -> None:
        """Alert.

        Manages alert operations and coordinates related state changes for the component.

        Args:
            title (str): Display text string.
            message (str): Informational or progress status message.
        """
        self.show_message(title, message)

    def show_message(self, title: str, message: str, msecs: int = 6000) -> None:
        """Show a tray balloon notification (best-effort, never raises).

        Manages show message operations and coordinates related state changes for the component.

        Args:
            title (str): Display text string.
            message (str): Informational or progress status message.
            msecs (int): The msecs parameter.
        """
        if self._tray is None:
            return
        try:
            if QSystemTrayIcon.supportsMessages():
                self._tray.showMessage(title, message,
                                       QSystemTrayIcon.MessageIcon.Information, msecs)
        except Exception:  # noqa: BLE001
            _LOG.debug("tray message failed", exc_info=True)

    def notify_network_changes(self, changes) -> None:
        """Show cooled-down local alerts for evidence-backed scan changes.

        Manages notify network changes operations and coordinates related state changes for the component.

        Args:
            changes: The changes parameter.
        """
        if self._tray is None or changes is None:
            return
        events = []
        for attribute, title in (
            ("new_devices", "New network device"),
            ("new_services", "New network service"),
            ("new_findings", "New security finding"),
            ("severity_changes", "Network risk changed"),
            ("disappeared_devices", "Network device went offline"),
            ("gateway_mac_changes", "Gateway identity changed"),
        ):
            items = (
                changes.get(attribute, ()) if isinstance(changes, Mapping)
                else getattr(changes, attribute, ()))
            for item in items:
                if isinstance(item, Mapping):
                    severity = str(item.get("severity", "info")).lower()
                    device_id = item.get("device_id", "")
                    message = str(item.get("message", title))
                else:
                    severity = str(
                        getattr(item, "severity", "info")).lower()
                    device_id = getattr(item, "device_id", "")
                    message = str(getattr(item, "message", title))
                if attribute in {"new_findings", "severity_changes"} and severity not in {
                        "critical", "high", "medium"}:
                    continue
                key = f"{attribute}:{device_id}:{message}"
                events.append((key, title, message))
        now = time.monotonic()
        for key, title, message in events[:8]:
            last = self._last_network_alerts.get(key, 0.0)
            if now - last <= _ALERT_COOLDOWN_S:
                continue
            self._last_network_alerts[key] = now
            self.show_message(title, message)
        # Keep a strict memory bound during long-running tray sessions.
        if len(self._last_network_alerts) > 512:
            cutoff = now - _ALERT_COOLDOWN_S
            self._last_network_alerts = {
                key: seen for key, seen in self._last_network_alerts.items()
                if seen >= cutoff
            }

    # -- theme + lifecycle --------------------------------------------------

    def refresh_theme(self, palette: Palette) -> None:
        """Re-render the tray glyph so it matches a newly-applied theme.

        Manages refresh theme operations and coordinates related state changes for the component.

        Args:
            palette (Palette): The palette parameter.
        """
        if self._tray is None:
            return
        try:
            self._tray.setIcon(_render_tray_icon(palette))
        except Exception:  # noqa: BLE001
            _LOG.debug("could not refresh tray icon", exc_info=True)

    def stop(self) -> None:
        """Stop active background operations.

        Manages worker thread execution states, signaling termination flags or initializing scheduled execution timers.
        """
        if self._timer is not None:
            try:
                self._timer.stop()
            except Exception:  # noqa: BLE001
                pass
            self._timer = None
        if self._network_timer is not None:
            try:
                self._network_timer.stop()
            except Exception:  # noqa: BLE001
                pass
            self._network_timer = None
        if self._tray is not None:
            try:
                self._tray.hide()
            except Exception:  # noqa: BLE001
                pass
            self._tray = None
