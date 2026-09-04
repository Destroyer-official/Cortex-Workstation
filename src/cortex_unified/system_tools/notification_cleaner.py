"""Cortex Cleaner — Windows Action Center & Push Notification Database Cleaner.

Scans and purges Windows Push Notification service databases:
1. %LocalAppData%\\Microsoft\\Windows\\Notifications\\wpndatabase.db (Notification history).
2. %LocalAppData%\\Microsoft\\Windows\\Notifications\\appmetadata.db (Notification endpoints).
3. Stale push badge caches and transient notification payloads.
"""

from __future__ import annotations

import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class NotificationDatabaseStatus:
    """Notificationdatabasestatus.

    Manages NotificationDatabaseStatus operations and coordinates related state changes for the component.
    """
    database_path: str
    database_size_bytes: int
    appmetadata_size_bytes: int
    total_size_bytes: int
    is_present: bool


@dataclass
class NotificationCleanResult:
    """Notificationcleanresult.

    Manages NotificationCleanResult operations and coordinates related state changes for the component.
    """
    success: bool
    bytes_freed: int
    message: str
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__.

        Manages post init operations and coordinates related state changes for the component.
        """
        if self.errors is None:
            self.errors = []


class NotificationCleaner:
    """Notificationcleaner.

    Manages NotificationCleaner operations and coordinates related state changes for the component.
    """

    @classmethod
    def get_status(cls) -> NotificationDatabaseStatus:
        """Query notification database paths and sizes.

        Manages get status operations and coordinates related state changes for the component.

        Returns:
            NotificationDatabaseStatus: Result of the operation.
        """
        if platform.system() != "Windows":
            return NotificationDatabaseStatus("", 0, 0, 0, False)

        local_app = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        notif_dir = local_app / "Microsoft" / "Windows" / "Notifications"

        wpn_db = notif_dir / "wpndatabase.db"
        app_db = notif_dir / "appmetadata.db"

        wpn_sz = wpn_db.stat().st_size if wpn_db.is_file() else 0
        app_sz = app_db.stat().st_size if app_db.is_file() else 0

        return NotificationDatabaseStatus(
            database_path=str(wpn_db),
            database_size_bytes=wpn_sz,
            appmetadata_size_bytes=app_sz,
            total_size_bytes=wpn_sz + app_sz,
            is_present=wpn_db.is_file() or app_db.is_file(),
        )

    @classmethod
    def clean_notification_database(cls) -> NotificationCleanResult:
        """Stop WpnService, purge notification database files, and restart service.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Returns:
            NotificationCleanResult: Result of the operation.
        """
        if platform.system() != "Windows":
            return NotificationCleanResult(False, 0, "Windows only")

        status = cls.get_status()
        if not status.is_present:
            return NotificationCleanResult(True, 0, "Notification database is clean / not present.")

        initial_freed = status.total_size_bytes
        errors: List[str] = []

        local_app = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        notif_dir = local_app / "Microsoft" / "Windows" / "Notifications"

        # 1. Stop WpnUserService / WpnService if possible
        try:
            subprocess.run(["net", "stop", "WpnService", "/y"], capture_output=True, timeout=5)
        except Exception:
            pass

        # 2. Delete database files
        freed = 0
        for fname in ["wpndatabase.db", "wpndatabase.db-wal", "wpndatabase.db-shm", "appmetadata.db"]:
            fp = notif_dir / fname
            if fp.is_file():
                try:
                    sz = fp.stat().st_size
                    fp.unlink()
                    freed += sz
                except Exception as exc:
                    errors.append(f"Failed to delete {fname}: {exc}")

        # 3. Restart WpnService
        try:
            subprocess.run(["net", "start", "WpnService"], capture_output=True, timeout=5)
        except Exception:
            pass

        return NotificationCleanResult(
            success=len(errors) == 0,
            bytes_freed=freed,
            message=f"Cleaned Action Center notification database ({freed / 1024:.1f} KB freed).",
            errors=errors,
        )
