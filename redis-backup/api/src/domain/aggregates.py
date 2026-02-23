"""
Domain layer - Aggregates

聚合根：維護聚合內部的一致性，是外部存取聚合的唯一入口
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from .value_objects import (
    JobId, Schedule, RedisConnection, StorageConfig, RecordId
)
from .entities import BackupRecord, BackupStatus


class JobStatus(Enum):
    """任務狀態"""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobAlreadyRunningError(Exception):
    """任務已在執行中"""
    pass


class RedisConnectionError(Exception):
    """Redis 連線錯誤"""
    pass


class InsufficientStorageError(Exception):
    """儲存空間不足"""
    pass


class InvalidPolicyError(Exception):
    """無效的策略配置"""
    pass


@dataclass
class CleanupPlan:
    """清理計劃值物件"""
    to_delete: List[RecordId] = field(default_factory=list)
    to_keep: List[RecordId] = field(default_factory=list)
    reason: str = ""


@dataclass
class BackupJob:
    """
    備份任務聚合根
    
    管理備份任務的執行狀態和配置
    """
    id: JobId
    schedule: Schedule
    connection: RedisConnection
    storage: StorageConfig
    status: JobStatus = JobStatus.IDLE
    current_record: Optional[BackupRecord] = None
    
    @classmethod
    def create(
        cls,
        schedule: Schedule,
        connection: RedisConnection,
        storage: StorageConfig
    ) -> 'BackupJob':
        """建立新的備份任務"""
        return cls(
            id=JobId.generate(),
            schedule=schedule,
            connection=connection,
            storage=storage,
            status=JobStatus.IDLE
        )
    
    def should_execute_at(self, check_time: datetime) -> bool:
        """檢查是否應該在指定時間執行"""
        if self.status == JobStatus.RUNNING:
            return False
        return self.schedule.is_triggered_at(check_time)
    
    def can_execute(self, redis_connected: bool, available_space: int) -> tuple[bool, str]:
        """檢查是否可以執行"""
        if self.status == JobStatus.RUNNING:
            return False, "Job is already running"
        
        if not redis_connected:
            return False, "Redis is not connected"
        
        if not self.storage.has_enough_space(available_space):
            return False, "Insufficient storage space"
        
        return True, ""
    
    def start(self) -> None:
        """開始執行"""
        if self.status == JobStatus.RUNNING:
            raise JobAlreadyRunningError("Backup job is already running")
        self.status = JobStatus.RUNNING
    
    def complete(self) -> None:
        """完成執行"""
        self.status = JobStatus.IDLE
        self.current_record = None
    
    def fail(self) -> None:
        """執行失敗"""
        self.status = JobStatus.IDLE
        self.current_record = None
    
    def reschedule(self, new_schedule: Schedule) -> None:
        """重新設定排程"""
        self.schedule = new_schedule
    
    def get_next_backup_time(self) -> datetime:
        """取得下次備份時間"""
        return self.schedule.get_next_trigger_time()


@dataclass
class RetentionPolicy:
    """
    保留策略聚合根
    
    管理備份的保留規則
    """
    retention_days: int
    max_backups: int
    min_backups: int
    protected_labels: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.min_backups > self.max_backups:
            raise InvalidPolicyError(
                f"min_backups ({self.min_backups}) cannot be greater than "
                f"max_backups ({self.max_backups})"
            )
        if self.min_backups < 1:
            raise InvalidPolicyError("min_backups must be at least 1")
    
    @classmethod
    def create(
        cls,
        retention_days: int = 7,
        max_backups: int = 30,
        min_backups: int = 3,
        protected_labels: Optional[List[str]] = None
    ) -> 'RetentionPolicy':
        """建立保留策略"""
        return cls(
            retention_days=retention_days,
            max_backups=max_backups,
            min_backups=min_backups,
            protected_labels=protected_labels or []
        )
    
    def evaluate(
        self,
        backups: List[BackupRecord],
        current_time: Optional[datetime] = None
    ) -> CleanupPlan:
        """
        評估備份並產生清理計劃
        
        規則優先順序：
        1. 保護重要備份和受保護標籤的備份
        2. 確保保留最少數量的備份
        3. 刪除超過保留天數的備份
        4. 如果超過最大數量，刪除最舊的備份
        """
        now = current_time or datetime.now()
        
        # 按建立時間排序（最新的在前）
        sorted_backups = sorted(
            backups,
            key=lambda b: b.start_time,
            reverse=True
        )
        
        to_keep: List[RecordId] = []
        to_delete: List[RecordId] = []
        
        for i, backup in enumerate(sorted_backups):
            # 檢查是否為保護的備份
            is_protected = (
                (backup.metadata and backup.metadata.is_important) or
                (backup.metadata and backup.metadata.label in self.protected_labels)
            )
            
            # 檢查是否過期
            is_expired = backup.is_expired(self.retention_days, now)
            
            # 檢查是否超過最大數量
            exceeds_max = len(to_keep) >= self.max_backups
            
            # 決定是否保留
            if is_protected:
                # 受保護的備份永遠保留
                to_keep.append(backup.id)
            elif len(to_keep) < self.min_backups:
                # 確保最少數量
                to_keep.append(backup.id)
            elif is_expired or exceeds_max:
                # 過期或超過最大數量
                to_delete.append(backup.id)
            else:
                to_keep.append(backup.id)
        
        return CleanupPlan(
            to_delete=to_delete,
            to_keep=to_keep,
            reason=f"Evaluated {len(backups)} backups: keeping {len(to_keep)}, deleting {len(to_delete)}"
        )
