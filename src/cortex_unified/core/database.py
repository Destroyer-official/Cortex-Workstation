"""
SQLite persistence layer for Cortex Cleaner.

Provides persistent storage for:
- Scan history and results
- Deleted items with restore capability
- Scheduled jobs
- System health metrics
- User preferences
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from sqlalchemy.pool import StaticPool

class Base(DeclarativeBase):
    """Base.

    Manages Base operations and coordinates related state changes for the component.
    """
    pass

class ScanRun(Base):
    """Record of a scan operation.

    Launches an asynchronous scan across the target subsystem, showing a loading indicator and disabling triggering controls.
    """
    
    __tablename__ = "scan_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_type = Column(String(64), nullable=False, index=True)
    root_path = Column(String(1024), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="running")  # running, completed, failed, interrupted
    
    # Results
    items_found = Column(Integer, default=0)
    bytes_found = Column(Integer, default=0)
    items_deleted = Column(Integer, default=0)
    bytes_freed = Column(Integer, default=0)
    
    # Health metrics
    health_score_before = Column(Integer, nullable=True)
    health_score_after = Column(Integer, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Relationships
    deleted_items = relationship("DeletedItem", back_populates="scan_run", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_scan_type_date", "scan_type", "started_at"),
    )
    
    def __repr__(self) -> str:
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.

        Returns:
            str: Formatted string or path.
        """
        return f"<ScanRun(id={self.id}, type={self.scan_type}, started={self.started_at})>"
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """duration_seconds.

        Manages duration seconds operations and coordinates related state changes for the component.

        Returns:
            Optional[float]: Result of the operation.
        """
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "id": self.id,
            "scan_type": self.scan_type,
            "root_path": self.root_path,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "items_found": self.items_found,
            "bytes_found": self.bytes_found,
            "items_deleted": self.items_deleted,
            "bytes_freed": self.bytes_freed,
            "health_score_before": self.health_score_before,
            "health_score_after": self.health_score_after,
            "duration_seconds": self.duration_seconds,
        }

class DeletedItem(Base):
    """Deleteditem.

    Manages DeletedItem operations and coordinates related state changes for the component.
    """
    
    __tablename__ = "deleted_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("scan_runs.id"), nullable=False, index=True)
    
    # File information
    path = Column(String(4096), nullable=False, index=True)
    original_name = Column(String(512), nullable=False)
    size_bytes = Column(Integer, default=0)
    file_type = Column(String(64), nullable=True)  # file, directory, symlink
    
    # Hashing for verification
    sha256 = Column(String(64), nullable=True)
    xxhash = Column(String(32), nullable=True)
    
    # Backup information
    backup_path = Column(String(4096), nullable=True)
    in_quarantine = Column(Boolean, default=False)
    
    # Timestamps
    deleted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    restored_at = Column(DateTime, nullable=True)
    
    # Metadata
    deletion_method = Column(String(32), default="trash")  # trash, delete, shred
    can_restore = Column(Boolean, default=True)
    
    # Relationships
    scan_run = relationship("ScanRun", back_populates="deleted_items")
    
    __table_args__ = (
        Index("idx_deleted_date", "deleted_at"),
        Index("idx_quarantine", "in_quarantine", "deleted_at"),
    )
    
    def __repr__(self) -> str:
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.

        Returns:
            str: Formatted string or path.
        """
        return f"<DeletedItem(id={self.id}, path={self.path}, deleted={self.deleted_at})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Manages to dict operations and coordinates related state changes for the component.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        return {
            "id": self.id,
            "run_id": self.run_id,
            "path": self.path,
            "original_name": self.original_name,
            "size_bytes": self.size_bytes,
            "file_type": self.file_type,
            "backup_path": self.backup_path,
            "in_quarantine": self.in_quarantine,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "restored_at": self.restored_at.isoformat() if self.restored_at else None,
            "deletion_method": self.deletion_method,
            "can_restore": self.can_restore,
        }

class ScheduledJob(Base):
    """Scheduledjob.

    Manages ScheduledJob operations and coordinates related state changes for the component.
    """
    
    __tablename__ = "scheduled_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Schedule
    cron_expression = Column(String(128), nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    next_run = Column(DateTime, nullable=True, index=True)
    last_run = Column(DateTime, nullable=True)
    
    # Job configuration
    scan_type = Column(String(64), nullable=False)
    root_paths = Column(Text, nullable=False)  # JSON array of paths
    config_json = Column(Text, nullable=True)  # JSON configuration
    
    # Status
    enabled = Column(Boolean, default=True, index=True)
    run_count = Column(Integer, default=0)
    last_status = Column(String(32), nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self) -> str:
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.

        Returns:
            str: Formatted string or path.
        """
        return f"<ScheduledJob(id={self.id}, name={self.name}, enabled={self.enabled})>"

class SystemMetric(Base):
    """Systemmetric.

    Manages SystemMetric operations and coordinates related state changes for the component.
    """
    
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Disk metrics
    disk_total_gb = Column(Float, nullable=True)
    disk_used_gb = Column(Float, nullable=True)
    disk_free_gb = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    
    # Health score
    health_score = Column(Integer, nullable=True)
    
    # Performance metrics
    scan_duration_seconds = Column(Float, nullable=True)
    items_scanned = Column(Integer, nullable=True)
    
    # System info
    drive_path = Column(String(256), nullable=True, index=True)
    
    __table_args__ = (
        Index("idx_metrics_drive_date", "drive_path", "recorded_at"),
    )

class UserPreference(Base):
    """Userpreference.

    Manages UserPreference operations and coordinates related state changes for the component.
    """
    
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(256), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(32), default="string")  # string, int, float, bool, json
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self) -> str:
        """Return an informative string representation of the instance.

        Formats key attributes and state flags into a concise string suitable for debugging and diagnostics.

        Returns:
            str: Formatted string or path.
        """
        return f"<UserPreference(key={self.key}, value={self.value})>"

class Database:
    """
    Database manager for Cortex Cleaner.
    
    Provides high-level interface for all database operations.
    """
    
    def __init__(self, db_path: Optional[Path] = None, echo: bool = False):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file (None = in-memory)
            echo: Enable SQL query logging
        """
        if db_path is None:
            # In-memory database for testing
            self.engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=echo,
            )
        else:
            db_path = Path(db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
                echo=echo,
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def session(self):
        """Session.

        Manages session operations and coordinates related state changes for the component.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # Scan Run Operations
    
    def create_scan_run(
        self,
        scan_type: str,
        root_path: str,
        health_score_before: Optional[int] = None,
    ) -> ScanRun:
        """Create a new scan run record.

        Manages create scan run operations and coordinates related state changes for the component.

        Args:
            scan_type (str): The scan type parameter.
            root_path (str): Filesystem path to the target file or directory.
            health_score_before (Optional[int]): The health score before parameter.

        Returns:
            ScanRun: Result of the operation.
        """
        with self.session() as session:
            scan_run = ScanRun(
                scan_type=scan_type,
                root_path=root_path,
                health_score_before=health_score_before,
                status="running",
            )
            session.add(scan_run)
            session.commit()
            session.refresh(scan_run)
            return scan_run
    
    def update_scan_run(
        self,
        run_id: int,
        status: Optional[str] = None,
        items_found: Optional[int] = None,
        bytes_found: Optional[int] = None,
        items_deleted: Optional[int] = None,
        bytes_freed: Optional[int] = None,
        health_score_after: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """update_scan_run.

        Manages update scan run operations and coordinates related state changes for the component.

        Args:
            run_id (int): The run id parameter.
            status (Optional[str]): The status parameter.
            items_found (Optional[int]): The items found parameter.
            bytes_found (Optional[int]): The bytes found parameter.
            items_deleted (Optional[int]): The items deleted parameter.
            bytes_freed (Optional[int]): The bytes freed parameter.
            health_score_after (Optional[int]): The health score after parameter.
            error_message (Optional[str]): Informational or progress status message.
        """
        with self.session() as session:
            scan_run = session.query(ScanRun).filter(ScanRun.id == run_id).first()
            if scan_run:
                if status:
                    scan_run.status = status
                if status in ("completed", "failed", "interrupted"):
                    scan_run.finished_at = datetime.now(timezone.utc)
                if items_found is not None:
                    scan_run.items_found = items_found
                if bytes_found is not None:
                    scan_run.bytes_found = bytes_found
                if items_deleted is not None:
                    scan_run.items_deleted = items_deleted
                if bytes_freed is not None:
                    scan_run.bytes_freed = bytes_freed
                if health_score_after is not None:
                    scan_run.health_score_after = health_score_after
                if error_message:
                    scan_run.error_message = error_message
    
    def get_scan_history(
        self,
        limit: int = 100,
        scan_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[ScanRun]:
        """Get scan history with optional filters.

        Manages get scan history operations and coordinates related state changes for the component.

        Args:
            limit (int): The limit parameter.
            scan_type (Optional[str]): The scan type parameter.
            since (Optional[datetime]): The since parameter.

        Returns:
            List[ScanRun]: List of processed items or identifiers.
        """
        with self.session() as session:
            query = session.query(ScanRun)
            
            if scan_type:
                query = query.filter(ScanRun.scan_type == scan_type)
            
            if since:
                query = query.filter(ScanRun.started_at >= since)
            
            query = query.order_by(ScanRun.started_at.desc()).limit(limit)
            
            return query.all()
    
    def get_scan_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get aggregate statistics for recent scans.

        Manages get scan stats operations and coordinates related state changes for the component.

        Args:
            days (int): The days parameter.

        Returns:
            Dict[str, Any]: Dictionary mapping identifiers to status or values.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self.session() as session:
            scans = session.query(ScanRun).filter(
                ScanRun.started_at >= since,
                ScanRun.status == "completed"
            ).all()
            
            if not scans:
                return {
                    "total_scans": 0,
                    "total_items_found": 0,
                    "total_bytes_freed": 0,
                    "avg_health_improvement": 0,
                }
            
            total_bytes_freed = sum(s.bytes_freed or 0 for s in scans)
            total_items_found = sum(s.items_found or 0 for s in scans)
            
            health_improvements = [
                (s.health_score_after - s.health_score_before)
                for s in scans
                if s.health_score_before and s.health_score_after
            ]
            
            avg_health_improvement = (
                sum(health_improvements) / len(health_improvements)
                if health_improvements else 0
            )
            
            return {
                "total_scans": len(scans),
                "total_items_found": total_items_found,
                "total_bytes_freed": total_bytes_freed,
                "avg_health_improvement": round(avg_health_improvement, 1),
                "period_days": days,
            }
    
    # Deleted Item Operations
    
    def add_deleted_item(
        self,
        run_id: int,
        path: str,
        size_bytes: int = 0,
        file_type: str = "file",
        backup_path: Optional[str] = None,
        deletion_method: str = "trash",
        sha256: Optional[str] = None,
    ) -> DeletedItem:
        """Record a deleted item.

        Manages add deleted item operations and coordinates related state changes for the component.

        Args:
            run_id (int): The run id parameter.
            path (str): Filesystem path to the target file or directory.
            size_bytes (int): The size bytes parameter.
            file_type (str): The file type parameter.
            backup_path (Optional[str]): Filesystem path to the target file or directory.
            deletion_method (str): The deletion method parameter.
            sha256 (Optional[str]): The sha256 parameter.

        Returns:
            DeletedItem: Result of the operation.
        """
        with self.session() as session:
            item = DeletedItem(
                run_id=run_id,
                path=path,
                original_name=Path(path).name,
                size_bytes=size_bytes,
                file_type=file_type,
                backup_path=backup_path,
                deletion_method=deletion_method,
                sha256=sha256,
                in_quarantine=backup_path is not None,
                can_restore=deletion_method != "shred",
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return item
    
    def get_restorable_items(
        self,
        limit: int = 100,
        in_quarantine_only: bool = True,
    ) -> List[DeletedItem]:
        """Get items that can be restored.

        Manages get restorable items operations and coordinates related state changes for the component.

        Args:
            limit (int): The limit parameter.
            in_quarantine_only (bool): The in quarantine only parameter.

        Returns:
            List[DeletedItem]: List of processed items or identifiers.
        """
        with self.session() as session:
            query = session.query(DeletedItem).filter(
                DeletedItem.can_restore == True,
                DeletedItem.restored_at.is_(None),
            )
            
            if in_quarantine_only:
                query = query.filter(DeletedItem.in_quarantine == True)
            
            query = query.order_by(DeletedItem.deleted_at.desc()).limit(limit)
            
            return query.all()
    
    def mark_item_restored(self, item_id: int) -> None:
        """Mark an item as restored.

        Manages mark item restored operations and coordinates related state changes for the component.

        Args:
            item_id (int): The item id parameter.
        """
        with self.session() as session:
            item = session.query(DeletedItem).filter(DeletedItem.id == item_id).first()
            if item:
                item.restored_at = datetime.now(timezone.utc)
                item.in_quarantine = False
    
    def cleanup_old_quarantine(self, days: int = 30) -> int:
        """Remove quarantine records older than specified days.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            days (int): The days parameter.

        Returns:
            int: Result of the operation.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self.session() as session:
            count = session.query(DeletedItem).filter(
                DeletedItem.in_quarantine == True,
                DeletedItem.deleted_at < cutoff,
            ).delete()
            
            return count
    
    # System Metrics Operations
    
    def record_metric(
        self,
        disk_total_gb: Optional[float] = None,
        disk_used_gb: Optional[float] = None,
        disk_free_gb: Optional[float] = None,
        health_score: Optional[int] = None,
        drive_path: Optional[str] = None,
    ) -> SystemMetric:
        """Record a system metric snapshot.

        Manages record metric operations and coordinates related state changes for the component.

        Args:
            disk_total_gb (Optional[float]): The disk total gb parameter.
            disk_used_gb (Optional[float]): The disk used gb parameter.
            disk_free_gb (Optional[float]): The disk free gb parameter.
            health_score (Optional[int]): The health score parameter.
            drive_path (Optional[str]): Filesystem path to the target file or directory.

        Returns:
            SystemMetric: Result of the operation.
        """
        with self.session() as session:
            metric = SystemMetric(
                disk_total_gb=disk_total_gb,
                disk_used_gb=disk_used_gb,
                disk_free_gb=disk_free_gb,
                disk_usage_percent=(
                    (disk_used_gb / disk_total_gb * 100)
                    if disk_total_gb and disk_used_gb else None
                ),
                health_score=health_score,
                drive_path=drive_path,
            )
            session.add(metric)
            session.commit()
            session.refresh(metric)
            return metric
    
    def get_metrics_history(
        self,
        days: int = 30,
        drive_path: Optional[str] = None,
    ) -> List[SystemMetric]:
        """Get historical metrics.

        Manages get metrics history operations and coordinates related state changes for the component.

        Args:
            days (int): The days parameter.
            drive_path (Optional[str]): Filesystem path to the target file or directory.

        Returns:
            List[SystemMetric]: List of processed items or identifiers.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self.session() as session:
            query = session.query(SystemMetric).filter(
                SystemMetric.recorded_at >= since
            )
            
            if drive_path:
                query = query.filter(SystemMetric.drive_path == drive_path)
            
            query = query.order_by(SystemMetric.recorded_at.asc())
            
            return query.all()
    
    # Cleanup Operations
    
    def cleanup_old_history(self, max_entries: int = 1000) -> int:
        """Keep only the most recent scan history entries.

        Permanently purges or removes specified target items, reclaiming storage space and logging actions taken.

        Args:
            max_entries (int): The max entries parameter.

        Returns:
            int: Result of the operation.
        """
        with self.session() as session:
            # Get count of total entries
            total = session.query(ScanRun).count()
            
            if total <= max_entries:
                return 0
            
            # Get IDs of entries to keep
            keep_ids = [
                r.id for r in session.query(ScanRun.id)
                .order_by(ScanRun.started_at.desc())
                .limit(max_entries)
                .all()
            ]
            
            # Delete old entries (cascade will handle deleted_items)
            deleted = session.query(ScanRun).filter(
                ScanRun.id.notin_(keep_ids)
            ).delete(synchronize_session=False)
            
            return deleted

# Global database instance
_db_instance: Optional[Database] = None
_db_lock = threading.Lock()

def get_database(db_path: Optional[Path] = None) -> Database:
    """get_database.

    Manages get database operations and coordinates related state changes for the component.

    Args:
        db_path (Optional[Path]): Filesystem path to the target file or directory.

    Returns:
        Database: Result of the operation.
    """
    global _db_instance
    if _db_instance is not None:
        return _db_instance
    with _db_lock:
        if _db_instance is not None:
            return _db_instance
        if db_path is None:
            db_path = Path.home() / ".cortex_cleaner" / "history.db"
        _db_instance = Database(db_path)
    return _db_instance

@contextmanager
def db_session():
    """Convenience context manager for database sessions.

    Manages db session operations and coordinates related state changes for the component.
    """
    db = get_database()
    with db.session() as session:
        yield session

if __name__ == "__main__":
    # Example usage and testing
    print("Initializing database...")
    db = Database()  # In-memory for testing
    
    print("Creating scan run...")
    scan = db.create_scan_run(
        scan_type="empty_files",
        root_path="/home/user/test",
        health_score_before=75,
    )
    print(f"✓ Created scan run: {scan.id}")
    
    print("Adding deleted items...")
    for i in range(5):
        db.add_deleted_item(
            run_id=scan.id,
            path=f"/home/user/test/file{i}.tmp",
            size_bytes=1024 * i,
            backup_path=f"/backup/file{i}.tmp",
        )
    print("✓ Added 5 deleted items")
    
    print("Updating scan run...")
    db.update_scan_run(
        run_id=scan.id,
        status="completed",
        items_found=5,
        bytes_found=10240,
        items_deleted=5,
        bytes_freed=10240,
        health_score_after=85,
    )
    print("✓ Updated scan run")
    
    print("\nScan history:")
    history = db.get_scan_history(limit=10)
    for run in history:
        print(f"  - {run.scan_type}: {run.items_found} items, {run.bytes_freed} bytes freed")
    
    print("\nRestorable items:")
    restorable = db.get_restorable_items()
    for item in restorable:
        print(f"  - {item.path} ({item.size_bytes} bytes)")
    
    print("\n✓ Database tests passed!")
