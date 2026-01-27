"""
Application layer - Health Application Service

健康檢查應用服務
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.infrastructure.redis_client import RedisClientAdapter
from src.infrastructure.file_storage import FileStorageAdapter

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """健康狀態"""
    status: str  # healthy, degraded, unhealthy
    redis_connected: bool
    storage_available: str
    storage_usage_percent: float
    last_backup_time: Optional[datetime]
    next_backup_time: Optional[datetime]
    backup_count: int


class HealthApplicationService:
    """健康檢查應用服務"""
    
    def __init__(
        self,
        redis_client: RedisClientAdapter,
        file_storage: FileStorageAdapter,
        backup_service  # Avoid circular import
    ):
        self.redis_client = redis_client
        self.file_storage = file_storage
        self.backup_service = backup_service
    
    def check_health(self) -> HealthStatus:
        """執行健康檢查"""
        # Check Redis connection
        redis_connected = self.redis_client.test_connection()
        
        # Check storage
        storage_status = self.file_storage.get_storage_status()
        
        # Get backup info
        backups = self.backup_service.list_backups()
        backup_count = len(backups)
        last_backup_time = self.backup_service.get_last_backup_time()
        next_backup_time = self.backup_service.get_next_backup_time()
        
        # Determine overall status
        if not redis_connected:
            status = "unhealthy"
        elif storage_status.is_low():
            status = "degraded"
        else:
            status = "healthy"
        
        return HealthStatus(
            status=status,
            redis_connected=redis_connected,
            storage_available=storage_status.format_available(),
            storage_usage_percent=storage_status.usage_percent,
            last_backup_time=last_backup_time,
            next_backup_time=next_backup_time,
            backup_count=backup_count
        )
