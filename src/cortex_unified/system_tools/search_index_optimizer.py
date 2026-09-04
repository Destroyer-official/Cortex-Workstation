"""Cortex Cleaner — Windows Search Index Database (Windows.edb) Optimizer.

Inspects, compacts, and rebuilds the Windows Search Catalog database:
1. Queries database size and index locations (%ProgramData%\\Microsoft\\Search\\Data\\Applications\\Windows).
2. Inspects and manages WSearch (Windows Search) service state.
3. Performs database compaction via ESENT utility (esentutl.exe /d).
4. Provides full search catalog index rebuild reset.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class SearchIndexStatus:
    """Searchindexstatus.

    Manages SearchIndexStatus operations and coordinates related state changes for the component.
    """
    database_path: str
    database_size_bytes: int
    service_status: str  # "Running", "Stopped", "Disabled", "Unknown"
    is_admin: bool
    is_bloated: bool  # True if > 1 GB
    indexed_items_estimate: int = 0


@dataclass
class SearchIndexOperationResult:
    """Searchindexoperationresult.

    Manages SearchIndexOperationResult operations and coordinates related state changes for the component.
    """
    success: bool
    message: str
    bytes_freed: int = 0
    new_size_bytes: int = 0
    errors: List[str] = None

    def __post_init__(self):
        """__post_init__.

        Manages post init operations and coordinates related state changes for the component.
        """
        if self.errors is None:
            self.errors = []


class SearchIndexOptimizer:
    """Searchindexoptimizer.

    Manages SearchIndexOptimizer operations and coordinates related state changes for the component.
    """

    @classmethod
    def get_status(cls) -> SearchIndexStatus:
        """Query Windows Search Index database metrics and service status.

        Manages get status operations and coordinates related state changes for the component.

        Returns:
            SearchIndexStatus: Result of the operation.
        """
        if platform.system() != "Windows":
            return SearchIndexStatus("", 0, "Non-Windows", False, False)

        prog_data = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        edb_path = prog_data / "Microsoft" / "Search" / "Data" / "Applications" / "Windows" / "Windows.edb"

        db_size = 0
        if edb_path.is_file():
            try:
                db_size = edb_path.stat().st_size
            except Exception:
                pass

        # Query WSearch service
        service_state = "Unknown"
        try:
            res = subprocess.run(["sc", "query", "WSearch"], capture_output=True, text=True, timeout=5)
            if "RUNNING" in res.stdout:
                service_state = "Running"
            elif "STOPPED" in res.stdout:
                service_state = "Stopped"
        except Exception:
            pass

        # Check Admin
        is_admin = False
        try:
            import ctypes
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            pass

        # Estimate items (typically ~2-4 KB per indexed item record in ESE database)
        est_items = max(0, db_size // 4096) if db_size > 0 else 0

        return SearchIndexStatus(
            database_path=str(edb_path),
            database_size_bytes=db_size,
            service_status=service_state,
            is_admin=is_admin,
            is_bloated=db_size > (1024 * 1024 * 1024),  # > 1GB
            indexed_items_estimate=est_items,
        )

    @classmethod
    def compact_database(cls) -> SearchIndexOperationResult:
        """Stop WSearch service, perform offline ESENT compaction (esentutl /d), and restart service.

        Manages compact database operations and coordinates related state changes for the component.

        Returns:
            SearchIndexOperationResult: Result of the operation.
        """
        if platform.system() != "Windows":
            return SearchIndexOperationResult(False, "Windows only")

        status = cls.get_status()
        edb_path = Path(status.database_path)
        if not edb_path.is_file():
            return SearchIndexOperationResult(False, "Search database Windows.edb not found")

        initial_size = status.database_size_bytes
        errors: List[str] = []

        # 1. Stop WSearch service
        try:
            subprocess.run(["net", "stop", "WSearch", "/y"], capture_output=True, timeout=15)
        except Exception as exc:
            errors.append(f"Failed to stop WSearch service: {exc}")

        # 2. Run esentutl /d Windows.edb
        compact_ok = False
        try:
            cmd = ["esentutl.exe", "/d", str(edb_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 or "Operation completed successfully" in res.stdout:
                compact_ok = True
            else:
                errors.append(f"esentutl returned code {res.returncode}: {res.stderr.strip() or res.stdout.strip()}")
        except Exception as exc:
            errors.append(f"Compaction error: {exc}")

        # 3. Restart WSearch service
        try:
            subprocess.run(["net", "start", "WSearch"], capture_output=True, timeout=15)
        except Exception as exc:
            errors.append(f"Failed to restart WSearch: {exc}")

        # 4. Measure new size
        new_size = initial_size
        try:
            if edb_path.is_file():
                new_size = edb_path.stat().st_size
        except Exception:
            pass

        bytes_freed = max(0, initial_size - new_size)
        msg = f"Database compacted successfully. Freed {bytes_freed / (1024 * 1024):.1f} MB." if compact_ok else "Compaction encountered issues."

        return SearchIndexOperationResult(
            success=compact_ok,
            message=msg,
            bytes_freed=bytes_freed,
            new_size_bytes=new_size,
            errors=errors,
        )

    @classmethod
    def rebuild_index(cls) -> SearchIndexOperationResult:
        """Trigger an official Windows Search index catalog rebuild.

        Manages rebuild index operations and coordinates related state changes for the component.

        Returns:
            SearchIndexOperationResult: Result of the operation.
        """
        if platform.system() != "Windows":
            return SearchIndexOperationResult(False, "Windows only")

        errors: List[str] = []
        try:
            # Stopping service and deleting catalog forces clean rebuild
            subprocess.run(["net", "stop", "WSearch", "/y"], capture_output=True, timeout=15)
            time.sleep(1)

            status = cls.get_status()
            edb_path = Path(status.database_path)
            freed = 0
            if edb_path.is_file():
                freed = edb_path.stat().st_size
                edb_path.unlink()

            subprocess.run(["net", "start", "WSearch"], capture_output=True, timeout=15)
            return SearchIndexOperationResult(True, "Search index rebuild initiated. Windows is re-indexing in the background.", freed, 0)
        except Exception as exc:
            return SearchIndexOperationResult(False, f"Rebuild failed: {exc}", 0, 0, [str(exc)])
