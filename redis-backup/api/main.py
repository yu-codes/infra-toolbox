"""
Redis Backup Service - Main Application

此服務使用 BDD-DDD-TDD 方法論開發
詳細設計文件請參考 docs/ 目錄
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from src.config import Settings
from src.domain.entities import BackupRecord, BackupStatus, TriggerType
from src.domain.value_objects import Schedule, JobId, RecordId
from src.domain.aggregates import BackupJob, RetentionPolicy
from src.domain.events import BackupCompleted, BackupFailed
from src.application.backup_service import BackupApplicationService
from src.application.health_service import HealthApplicationService
from src.infrastructure.redis_client import RedisClientAdapter
from src.infrastructure.file_storage import FileStorageAdapter
from src.infrastructure.scheduler import BackupScheduler
from src.infrastructure.metrics import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load settings
settings = Settings()

# Initialize infrastructure components
redis_client = RedisClientAdapter(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password
)

file_storage = FileStorageAdapter(
    backup_path=settings.backup_path,
    redis_data_path=settings.redis_data_path
)

metrics_collector = MetricsCollector()

# Initialize domain objects
schedule = Schedule(expression=settings.backup_schedule)
retention_policy = RetentionPolicy(
    retention_days=settings.retention_days,
    max_backups=settings.max_backups,
    min_backups=settings.min_backups
)

# Initialize application services
backup_service = BackupApplicationService(
    redis_client=redis_client,
    file_storage=file_storage,
    schedule=schedule,
    retention_policy=retention_policy,
    metrics=metrics_collector
)

health_service = HealthApplicationService(
    redis_client=redis_client,
    file_storage=file_storage,
    backup_service=backup_service
)

# Initialize scheduler
scheduler = BackupScheduler(
    backup_service=backup_service,
    schedule=schedule
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Redis Backup Service...")
    logger.info(f"Backup schedule: {settings.backup_schedule}")
    logger.info(f"Retention policy: {settings.retention_days} days, max {settings.max_backups} backups")
    
    # Start scheduler
    scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Redis Backup Service...")
    scheduler.shutdown()


app = FastAPI(
    title="Redis Backup Service",
    description="自動化 Redis 備份服務，支援排程備份、手動備份、還原和保留策略",
    version="1.0.0",
    lifespan=lifespan
)


# ============ Request/Response Models ============

class TriggerBackupRequest(BaseModel):
    label: Optional[str] = None


class TriggerBackupResponse(BaseModel):
    task_id: str
    message: str
    status: str


class BackupStatusResponse(BaseModel):
    task_id: str
    status: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    progress: Optional[int] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None


class BackupListItem(BaseModel):
    id: str
    filename: str
    size: int
    created_at: str
    checksum: str
    label: Optional[str] = None
    is_important: bool = False


class BackupListResponse(BaseModel):
    backups: list[BackupListItem]
    total: int


class RestoreRequest(BaseModel):
    backup_file: str
    create_snapshot: bool = True
    validate_after: bool = True


class RestoreResponse(BaseModel):
    task_id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    redis_connected: bool
    storage_available: str
    storage_usage_percent: float
    last_backup_time: Optional[str] = None
    next_backup_time: Optional[str] = None
    backup_count: int


# ============ API Endpoints ============

@app.post("/api/v1/backup/trigger", response_model=TriggerBackupResponse, status_code=202)
async def trigger_backup(
    request: TriggerBackupRequest,
    background_tasks: BackgroundTasks
):
    """
    觸發手動備份
    
    - **label**: 可選的備份標籤（如 pre-migration）
    """
    if backup_service.is_running():
        raise HTTPException(
            status_code=409,
            detail="另一個備份任務正在執行中"
        )
    
    task_id = backup_service.create_task_id()
    
    # Run backup in background
    background_tasks.add_task(
        backup_service.execute_backup,
        task_id=task_id,
        label=request.label,
        trigger_type=TriggerType.MANUAL
    )
    
    return TriggerBackupResponse(
        task_id=task_id,
        message="備份任務已開始",
        status="STARTED"
    )


@app.get("/api/v1/backup/status/{task_id}", response_model=BackupStatusResponse)
async def get_backup_status(task_id: str):
    """查詢備份任務狀態"""
    record = backup_service.get_task_status(task_id)
    
    if record is None:
        raise HTTPException(status_code=404, detail="任務不存在")
    
    return BackupStatusResponse(
        task_id=task_id,
        status=record.status.value,
        start_time=record.start_time.isoformat() if record.start_time else None,
        end_time=record.end_time.isoformat() if record.end_time else None,
        progress=record.progress,
        file_name=record.file.filename if record.file else None,
        file_size=record.file.size if record.file else None,
        error=record.error_info.message if record.error_info else None
    )


@app.get("/api/v1/backups", response_model=BackupListResponse)
async def list_backups():
    """列出所有備份"""
    backups = backup_service.list_backups()
    
    items = [
        BackupListItem(
            id=str(b.id),
            filename=b.file.filename,
            size=b.file.size,
            created_at=b.start_time.isoformat(),
            checksum=b.file.checksum,
            label=b.metadata.label if b.metadata else None,
            is_important=b.metadata.is_important if b.metadata else False
        )
        for b in backups
    ]
    
    return BackupListResponse(backups=items, total=len(items))


@app.post("/api/v1/restore", response_model=RestoreResponse)
async def restore_backup(
    request: RestoreRequest,
    background_tasks: BackgroundTasks
):
    """
    從備份還原 Redis 資料
    
    - **backup_file**: 備份檔案名稱
    - **create_snapshot**: 還原前是否建立快照（預設 True）
    - **validate_after**: 還原後是否驗證（預設 True）
    """
    # Verify backup file exists
    if not backup_service.backup_exists(request.backup_file):
        raise HTTPException(status_code=404, detail="備份檔案不存在")
    
    task_id = backup_service.create_task_id()
    
    background_tasks.add_task(
        backup_service.execute_restore,
        task_id=task_id,
        backup_file=request.backup_file,
        create_snapshot=request.create_snapshot,
        validate_after=request.validate_after
    )
    
    return RestoreResponse(
        task_id=task_id,
        status="STARTED",
        message="還原任務已開始"
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康檢查端點"""
    health = health_service.check_health()
    
    status_code = 200 if health.status == "healthy" else 503
    
    response = HealthResponse(
        status=health.status,
        redis_connected=health.redis_connected,
        storage_available=health.storage_available,
        storage_usage_percent=health.storage_usage_percent,
        last_backup_time=health.last_backup_time.isoformat() if health.last_backup_time else None,
        next_backup_time=health.next_backup_time.isoformat() if health.next_backup_time else None,
        backup_count=health.backup_count
    )
    
    if status_code == 503:
        raise HTTPException(status_code=503, detail=response.model_dump())
    
    return response


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus 指標端點"""
    return PlainTextResponse(
        generate_latest(metrics_collector.registry),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/")
async def root():
    """根路徑 - 顯示服務資訊"""
    return {
        "service": "Redis Backup Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }
