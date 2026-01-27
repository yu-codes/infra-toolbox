"""
Domain layer - Domain Events

領域事件：記錄領域中發生的重要事件
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .value_objects import JobId, RecordId, ErrorInfo


@dataclass(frozen=True)
class DomainEvent:
    """領域事件基類"""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class BackupStarted(DomainEvent):
    """備份開始事件"""
    job_id: JobId
    trigger_type: str
    
    @classmethod
    def create(cls, job_id: JobId, trigger_type: str) -> 'BackupStarted':
        return cls(job_id=job_id, trigger_type=trigger_type)


@dataclass(frozen=True)
class BackupCompleted(DomainEvent):
    """備份完成事件"""
    record_id: RecordId
    job_id: JobId
    file_name: str
    size: int
    duration: timedelta
    
    @classmethod
    def from_record(cls, record) -> 'BackupCompleted':
        """從 BackupRecord 建立事件"""
        return cls(
            record_id=record.id,
            job_id=record.job_id,
            file_name=record.file.filename if record.file else "",
            size=record.file.size if record.file else 0,
            duration=record.calculate_duration() or timedelta(0)
        )


@dataclass(frozen=True)
class BackupFailed(DomainEvent):
    """備份失敗事件"""
    job_id: JobId
    error_info: ErrorInfo
    retry_count: int = 0


@dataclass(frozen=True)
class RestoreStarted(DomainEvent):
    """還原開始事件"""
    job_id: JobId
    source_backup_id: RecordId


@dataclass(frozen=True)
class RestoreCompleted(DomainEvent):
    """還原完成事件"""
    record_id: RecordId
    duration: timedelta
    is_valid: bool
    key_count: int


@dataclass(frozen=True)
class RestoreFailed(DomainEvent):
    """還原失敗事件"""
    job_id: JobId
    error_info: ErrorInfo
    rollback_status: str


@dataclass(frozen=True)
class CleanupExecuted(DomainEvent):
    """清理執行完成事件"""
    deleted_count: int
    freed_space: int


@dataclass(frozen=True)
class StorageSpaceLow(DomainEvent):
    """儲存空間不足事件"""
    available_space: int
    usage_percent: float


@dataclass(frozen=True)
class RedisConnectionLost(DomainEvent):
    """Redis 連線中斷事件"""
    last_connected_time: Optional[datetime]
    error_message: str
