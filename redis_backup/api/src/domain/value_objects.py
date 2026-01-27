"""
Domain layer - Value Objects

值物件：無唯一識別符，不可變，通過屬性判斷相等性
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import uuid
import re

from croniter import croniter


class InvalidCronExpressionError(Exception):
    """無效的 Cron 表達式"""
    pass


class InvalidPortError(Exception):
    """無效的 Port"""
    pass


@dataclass(frozen=True)
class JobId:
    """任務 ID 值物件"""
    value: str
    
    @classmethod
    def generate(cls) -> 'JobId':
        return cls(value=str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RecordId:
    """記錄 ID 值物件"""
    value: str
    
    @classmethod
    def generate(cls) -> 'RecordId':
        return cls(value=str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Schedule:
    """排程值物件 - 使用 Cron 表達式"""
    expression: str
    timezone: str = "UTC"
    
    def __post_init__(self):
        if not self._is_valid_cron(self.expression):
            raise InvalidCronExpressionError(
                f"Invalid cron expression: {self.expression}"
            )
    
    def _is_valid_cron(self, expr: str) -> bool:
        try:
            croniter(expr)
            return True
        except (ValueError, KeyError):
            return False
    
    def is_triggered_at(self, check_time: datetime) -> bool:
        """檢查指定時間是否符合排程"""
        cron = croniter(self.expression, check_time - timedelta(minutes=1))
        next_time = cron.get_next(datetime)
        return (
            next_time.year == check_time.year and
            next_time.month == check_time.month and
            next_time.day == check_time.day and
            next_time.hour == check_time.hour and
            next_time.minute == check_time.minute
        )
    
    def get_next_trigger_time(self, after: Optional[datetime] = None) -> datetime:
        """取得下一次觸發時間"""
        base_time = after or datetime.now()
        cron = croniter(self.expression, base_time)
        return cron.get_next(datetime)


@dataclass(frozen=True)
class RedisConnection:
    """Redis 連線配置值物件"""
    host: str
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    
    def __post_init__(self):
        if not (0 < self.port < 65536):
            raise InvalidPortError(f"Invalid port: {self.port}")
    
    def to_connection_string(self) -> str:
        """生成連線字串"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class StorageConfig:
    """儲存配置值物件"""
    backup_path: str
    min_free_space: int = 1024 * 1024 * 100  # 100 MB
    
    def has_enough_space(self, available_space: int) -> bool:
        """檢查是否有足夠空間"""
        return available_space >= self.min_free_space


@dataclass(frozen=True)
class BackupFile:
    """備份檔案值物件"""
    filename: str
    path: str
    size: int
    checksum: str
    
    @classmethod
    def create(
        cls,
        timestamp: Optional[datetime] = None,
        label: Optional[str] = None,
        path: str = "/backups"
    ) -> 'BackupFile':
        """建立備份檔案（初始狀態，需要後續填入 size 和 checksum）"""
        ts = timestamp or datetime.now()
        date_str = ts.strftime("%Y%m%d_%H%M%S")
        
        if label:
            filename = f"redis_backup_{date_str}_{label}.rdb"
        else:
            filename = f"redis_backup_{date_str}.rdb"
        
        return cls(
            filename=filename,
            path=f"{path}/{filename}",
            size=0,
            checksum=""
        )
    
    def with_metadata(self, size: int, checksum: str) -> 'BackupFile':
        """返回帶有 size 和 checksum 的新實例"""
        return BackupFile(
            filename=self.filename,
            path=self.path,
            size=size,
            checksum=checksum
        )
    
    def validate_checksum(self, expected: str) -> bool:
        """驗證校驗碼"""
        return self.checksum == expected


@dataclass(frozen=True)
class ErrorInfo:
    """錯誤資訊值物件"""
    code: str
    message: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    
    def with_retry(self) -> 'ErrorInfo':
        """返回增加重試計數的新實例"""
        return ErrorInfo(
            code=self.code,
            message=self.message,
            stack_trace=self.stack_trace,
            retry_count=self.retry_count + 1
        )


@dataclass(frozen=True)
class BackupMetadata:
    """備份元資料值物件"""
    label: Optional[str] = None
    trigger_type: str = "SCHEDULED"
    is_important: bool = False
    tags: dict = field(default_factory=dict)
    
    def mark_important(self) -> 'BackupMetadata':
        """標記為重要"""
        return BackupMetadata(
            label=self.label,
            trigger_type=self.trigger_type,
            is_important=True,
            tags=self.tags
        )


@dataclass(frozen=True)
class StorageStatus:
    """儲存狀態值物件"""
    total_space: int
    used_space: int
    available_space: int
    
    @property
    def usage_percent(self) -> float:
        """使用率百分比"""
        if self.total_space == 0:
            return 0.0
        return (self.used_space / self.total_space) * 100
    
    def is_low(self, threshold_percent: float = 85.0) -> bool:
        """檢查空間是否不足"""
        return self.usage_percent >= threshold_percent
    
    def format_available(self) -> str:
        """格式化可用空間"""
        gb = self.available_space / (1024 ** 3)
        if gb >= 1:
            return f"{gb:.2f} GB"
        mb = self.available_space / (1024 ** 2)
        return f"{mb:.2f} MB"


@dataclass(frozen=True)
class ValidationResult:
    """驗證結果值物件"""
    is_valid: bool
    key_count: int = 0
    memory_usage: int = 0
    errors: tuple = field(default_factory=tuple)
