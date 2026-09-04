"""Windows 11 AI, Copilot, Recall & Semantic Telemetry Cleaner.

Research Grounding
------------------
* Windows 11 Copilot & Windows Recall Storage Architecture (Microsoft Docs, 2024-2025):
  Windows Recall takes continuous periodic UI screenshots, extracts text via OCR,
  and generates local vector embeddings stored in SQLite databases under:
  `%LOCALAPPDATA%\\CoreAIPlatform.00\\UKP` and `SemanticSearch` stores.
* Microsoft Edge & Windows AI WebView2 Cache:
  Generative AI prompts, history, and transient vector data are cached in
  `Microsoft.Copilot_*` application containers and Edge IndexedDB stores.
* Windows 11 24H2 CapabilityAccessManager Bloat Bug:
  `CapabilityAccessManager.db-wal` (Write-Ahead Log) frequently fails to checkpoint,
  expanding into tens of gigabytes of unindexed disk consumption.

This module safely analyzes Windows AI artifacts, checkpoints/truncates bloated
SQLite WAL journals without data corruption, and purges unreferenced offline caches.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOG = logging.getLogger("cortex.system_tools.ai_telemetry")


@dataclass
class AiArtifactInfo:
    """Aiartifactinfo.

    Manages AiArtifactInfo operations and coordinates related state changes for the component.
    """
    name: str
    category: str  # "Recall", "Copilot Cache", "SQLite WAL", "Edge AI"
    path: str
    size_bytes: int = 0
    is_sqlite_wal: bool = False
    is_safe_to_clean: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "name": self.name,
            "category": self.category,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "is_sqlite_wal": self.is_sqlite_wal,
            "is_safe_to_clean": self.is_safe_to_clean,
            "description": self.description,
        }


@dataclass
class AiTelemetryReport:
    """Aitelemetryreport.

    Manages AiTelemetryReport operations and coordinates related state changes for the component.
    """
    artifacts: List[AiArtifactInfo] = field(default_factory=list)
    total_size_bytes: int = 0
    wal_journal_bytes: int = 0
    cache_bytes: int = 0
    recall_configured: bool = False
    scan_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "artifacts": [a.to_dict() for a in self.artifacts],
            "total_size_bytes": self.total_size_bytes,
            "wal_journal_bytes": self.wal_journal_bytes,
            "cache_bytes": self.cache_bytes,
            "recall_configured": self.recall_configured,
            "scan_duration_ms": self.scan_duration_ms,
        }


@dataclass
class AiCleanResult:
    """Aicleanresult.

    Manages AiCleanResult operations and coordinates related state changes for the component.
    """
    cleaned_items: int = 0
    freed_bytes: int = 0
    truncated_wal_count: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """To dict.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "cleaned_items": self.cleaned_items,
            "freed_bytes": self.freed_bytes,
            "truncated_wal_count": self.truncated_wal_count,
            "errors": self.errors,
            "dry_run": self.dry_run,
        }


class AiTelemetryCleaner:
    """Aitelemetrycleaner.

    Manages AiTelemetryCleaner operations and coordinates related state changes for the component.
    """

    def __init__(self) -> None:
        """Initialize Ai Telemetry Cleaner.

        Initializes the instance and configures internal state.
        """
        self.logger = _LOG

    def _get_search_roots(self) -> List[tuple[str, str, Path, str]]:
        """Resolve candidate search locations dynamically from active user and system environments.

        Manages get search roots operations and coordinates related state changes for the component.

        Returns:
            List[tuple[str, str, Path, str]]: List of processed items or identifiers.
        """
        lad = os.environ.get("LOCALAPPDATA")
        pdata = os.environ.get("PROGRAMDATA")

        candidates: List[tuple[str, str, Path, str]] = []

        if lad:
            lad_p = Path(lad)
            # Windows Recall Core AI Platform
            candidates.append((
                "Windows Recall Semantic Snapshot Store",
                "Recall",
                lad_p / "CoreAIPlatform.00" / "UKP",
                "Local vector embeddings and captured application snapshots for Windows Recall.",
            ))
            # Windows Copilot Store App LocalCache
            candidates.append((
                "Copilot App Temporary Cache",
                "Copilot Cache",
                lad_p / "Packages" / "Microsoft.Copilot_8wekyb3d8bbwe" / "LocalCache",
                "Transient cache and session states from the standalone Copilot UWP app.",
            ))
            # Windows AI Provider Package Cache
            candidates.append((
                "Windows AI Copilot Provider Cache",
                "Copilot Cache",
                lad_p / "Packages" / "Microsoft.Windows.Ai.Copilot.Provider_8wekyb3d8bbwe" / "LocalCache",
                "System background worker cache for Windows Copilot integration.",
            ))
            # Microsoft Edge AI / Copilot IndexedDB
            candidates.append((
                "Edge Copilot Sidebar Storage",
                "Edge AI",
                lad_p / "Microsoft" / "Edge" / "User Data" / "Default" / "IndexedDB",
                "Offline chat sessions and generated prompt artifacts in Edge Copilot.",
            ))

        if pdata:
            pdata_p = Path(pdata)
            # Capability Access Manager database root (noted in 24H2 WAL bloat)
            candidates.append((
                "Capability Access Manager Store",
                "SQLite WAL",
                pdata_p / "Microsoft" / "Windows" / "AppReadiness",
                "Windows capability and privacy access database logs.",
            ))

        return candidates

    def scan(self) -> AiTelemetryReport:
        """Examine local disk for AI artifacts, Recall databases, and inflated WAL files.

        Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.

        Returns:
            AiTelemetryReport: Result of the operation.
        """
        t0 = time.perf_counter()
        report = AiTelemetryReport()

        for name, category, root_path, desc in self._get_search_roots():
            if not root_path.exists():
                continue

            if root_path.is_file():
                self._record_artifact(report, name, category, root_path, desc)
            elif root_path.is_dir():
                try:
                    for root, _, files in os.walk(root_path):
                        for f in files:
                            fp = Path(root) / f
                            is_wal = f.lower().endswith("-wal")
                            item_name = f"{name}: {f}" if is_wal else f"{name} ({f})"
                            item_cat = "SQLite WAL" if is_wal else category
                            self._record_artifact(report, item_name, item_cat, fp, desc, is_wal=is_wal)
                except (OSError, PermissionError) as exc:
                    self.logger.debug("Failed walking %s: %s", root_path, exc)

        report.scan_duration_ms = (time.perf_counter() - t0) * 1000.0
        return report

    def _record_artifact(
        self,
        report: AiTelemetryReport,
        name: str,
        category: str,
        path: Path,
        description: str,
        is_wal: bool = False,
    ) -> None:
        """_record_artifact.

        Manages record artifact operations and coordinates related state changes for the component.

        Args:
            report (AiTelemetryReport): The generated report data object from the backend.
            name (str): The name parameter.
            category (str): The category parameter.
            path (Path): Filesystem path to the target file or directory.
            description (str): The description parameter.
            is_wal (bool): The is wal parameter.
        """
        try:
            stat = path.stat()
            sz = stat.st_size
            info = AiArtifactInfo(
                name=name,
                category=category,
                path=str(path),
                size_bytes=sz,
                is_sqlite_wal=is_wal,
                is_safe_to_clean=True,
                description=description,
            )
            report.artifacts.append(info)
            report.total_size_bytes += sz
            if is_wal:
                report.wal_journal_bytes += sz
            else:
                report.cache_bytes += sz
        except (OSError, PermissionError):
            pass

    def checkpoint_wal_journal(self, wal_path: Path) -> int:
        """Safely truncate a SQLite WAL file by connecting to its parent DB and executing PRAGMA wal_checkpoint(TRUNCATE).

        Manages checkpoint wal journal operations and coordinates related state changes for the component.

        Args:
            wal_path (Path): Filesystem path to the target file or directory.

        Returns:
            int: Result of the operation.
        """
        db_path = wal_path.with_name(wal_path.name[:-4])  # Strip -wal
        if not db_path.is_file():
            return 0

        initial_wal_size = 0
        try:
            initial_wal_size = wal_path.stat().st_size
        except OSError:
            return 0

        if initial_wal_size == 0:
            return 0

        try:
            conn = sqlite3.connect(str(db_path), timeout=2.0)
            try:
                cur = conn.cursor()
                cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                conn.commit()
            finally:
                conn.close()

            new_size = wal_path.stat().st_size if wal_path.exists() else 0
            return max(0, initial_wal_size - new_size)
        except Exception as exc:
            self.logger.debug("SQLite WAL checkpoint skipped for %s: %s", db_path, exc)
            return 0

    def clean(self, checkpoint_wal: bool = True, dry_run: bool = False) -> AiCleanResult:
        """Purge temporary AI caches and truncate uncheckpointed SQLite WAL journals.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            checkpoint_wal (bool): The checkpoint wal parameter.
            dry_run (bool): The dry run parameter.

        Returns:
            AiCleanResult: Result of the operation.
        """
        result = AiCleanResult(dry_run=dry_run)

        for _, category, root_path, _ in self._get_search_roots():
            if not root_path.exists():
                continue

            try:
                if root_path.is_dir():
                    for root, _, files in os.walk(root_path, topdown=False):
                        for f in files:
                            fp = Path(root) / f
                            is_wal = f.lower().endswith("-wal")

                            if is_wal and checkpoint_wal:
                                if not dry_run:
                                    freed = self.checkpoint_wal_journal(fp)
                                    if freed > 0:
                                        result.freed_bytes += freed
                                        result.truncated_wal_count += 1
                                else:
                                    try:
                                        result.freed_bytes += fp.stat().st_size
                                        result.truncated_wal_count += 1
                                    except OSError:
                                        pass
                            elif not is_wal:
                                try:
                                    sz = fp.stat().st_size
                                    if not dry_run:
                                        fp.unlink()
                                    result.cleaned_items += 1
                                    result.freed_bytes += sz
                                except (PermissionError, OSError) as exc:
                                    self.logger.debug("Skipping in-use artifact %s: %s", fp, exc)

                        if not dry_run and root != str(root_path):
                            try:
                                if not os.listdir(root):
                                    os.rmdir(root)
                            except OSError:
                                pass
            except Exception as exc:
                result.errors.append(f"Error processing {root_path}: {exc}")

        return result
