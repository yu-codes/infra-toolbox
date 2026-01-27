"""
Domain layer - Entities

實體：具有唯一識別符，生命週期內身份不變，可變狀態
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from .value_objects import (
    RecordId, JobId, BackupFile, BackupMetadata, 
    ErrorInfo, ValidationResult
)


class BackupStatus(Enum):
    """備份狀態"""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DELETED = "DELETED"


class TriggerType(Enum):
    """觸發類型"""
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"
    PRE_RESTORE = "PRE_RESTORE"


class RestoreStatus(Enum):
    """還原狀態"""
    PENDING = "PENDING"
    CREATING_SNAPSHOT = "CREATING_SNAPSHOT"
    STOPPING_REDIS = "STOPPING_REDIS"
    COPYING_FILE = "COPYING_FILE"
    STARTING_REDIS = "STARTING_REDIS"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class InvalidStateTransitionError(Exception):
    """無效的狀態轉換"""
    pass


@dataclass
class BackupRecord:
    """
    備份記錄實體
    
    記錄每次備份操作的詳細資訊
    """
    id: RecordId
    job_id: JobId
    metadata: BackupMetadata
    status: BackupStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    file: Optional[BackupFile] = None
    error_info: Optional[ErrorInfo] = None
    progress: int = 0
    
    @classmethod
    def create(
        cls,
        job_id: JobId,
        trigger_type: TriggerType = TriggerType.SCHEDULED,
        label: Optional[str] = None
    ) -> 'BackupRecord':
        """建立新的備份記錄"""
        return cls(
            id=RecordId.generate(),
            job_id=job_id,
            metadata=BackupMetadata(
                label=label,
                trigger_type=trigger_type.value
            ),
            status=BackupStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
    
    def update_progress(self, progress: int) -> None:
        """更新進度"""
        if self.status != BackupStatus.IN_PROGRESS:
            raise InvalidStateTransitionError(
                f"Cannot update progress in {self.status} state"
            )
        self.progress = min(100, max(0, progress))
    
    def complete(self, file: BackupFile) -> None:
        """完成備份"""
        if self.status != BackupStatus.IN_PROGRESS:
            raise InvalidStateTransitionError(
                f"Cannot complete from {self.status} state"
            )
        self.status = BackupStatus.COMPLETED
        self.end_time = datetime.now()
        self.file = file
        self.progress = 100
    
    def fail(self, error: ErrorInfo) -> None:
        """標記失敗"""
        if self.status not in (BackupStatus.IN_PROGRESS,):
            raise InvalidStateTransitionError(
                f"Cannot fail from {self.status} state"
            )
        self.status = BackupStatus.FAILED
        self.end_time = datetime.now()
        self.error_info = error
    
    def mark_as_important(self) -> None:
        """標記為重要"""
        self.metadata = self.metadata.mark_important()
    
    def calculate_duration(self) -> Optional[timedelta]:
        """計算持續時間"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None
    
    def is_expired(self, retention_days: int, current_time: Optional[datetime] = None) -> bool:
        """檢查是否過期"""
        now = current_time or datetime.now()
        age = now - self.start_time
        return age.days > retention_days


@dataclass
class RestoreRecord:
    """
    還原記錄實體
    """
    id: RecordId
    job_id: JobId
    source_backup_id: RecordId
    pre_restore_snapshot_id: Optional[RecordId] = None
    status: RestoreStatus = RestoreStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    validation: Optional[ValidationResult] = None
    error_info: Optional[ErrorInfo] = None
    
    @classmethod
    def create(
        cls,
        job_id: JobId,
        source_backup_id: RecordId
    ) -> 'RestoreRecord':
        """建立新的還原記錄"""
        return cls(
            id=RecordId.generate(),
            job_id=job_id,
            source_backup_id=source_backup_id,
            start_time=datetime.now()
        )
    
    def update_status(self, status: RestoreStatus) -> None:
        """更新狀態"""
        self.status = status
    
    def set_pre_restore_snapshot(self, snapshot_id: RecordId) -> None:
        """設定還原前快照"""
        self.pre_restore_snapshot_id = snapshot_id
    
    def complete(self, validation: ValidationResult) -> None:
        """完成還原"""
        self.status = RestoreStatus.COMPLETED
        self.end_time = datetime.now()
        self.validation = validation
    
    def fail(self, error: ErrorInfo) -> None:
        """標記失敗"""
        self.status = RestoreStatus.FAILED
        self.end_time = datetime.now()
        self.error_info = error
    
    def rollback(self) -> None:
        """標記已回滾"""
        self.status = RestoreStatus.ROLLED_BACK
        self.end_time = datetime.now()
