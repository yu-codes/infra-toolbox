"""
Application layer - Backup Application Service

應用服務：協調領域物件完成用例
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.domain.entities import BackupRecord, BackupStatus, TriggerType
from src.domain.value_objects import JobId, BackupFile, ErrorInfo, Schedule, RecordId
from src.domain.aggregates import RetentionPolicy
from src.domain.events import BackupCompleted, BackupFailed
from src.infrastructure.redis_client import RedisClientAdapter
from src.infrastructure.file_storage import FileStorageAdapter
from src.infrastructure.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class BackupApplicationService:
    """備份應用服務"""
    
    def __init__(
        self,
        redis_client: RedisClientAdapter,
        file_storage: FileStorageAdapter,
        schedule: Schedule,
        retention_policy: RetentionPolicy,
        metrics: MetricsCollector
    ):
        self.redis_client = redis_client
        self.file_storage = file_storage
        self.schedule = schedule
        self.retention_policy = retention_policy
        self.metrics = metrics
        
        # In-memory task store (in production, use a database)
        self._tasks: Dict[str, BackupRecord] = {}
        self._backups: List[BackupRecord] = []
        self._is_running = False
    
    def create_task_id(self) -> str:
        """建立新的任務 ID"""
        return str(uuid.uuid4())
    
    def is_running(self) -> bool:
        """檢查是否有任務正在執行"""
        return self._is_running
    
    def get_task_status(self, task_id: str) -> Optional[BackupRecord]:
        """取得任務狀態"""
        return self._tasks.get(task_id)
    
    def list_backups(self) -> List[BackupRecord]:
        """列出所有備份"""
        # Also scan file system for backups
        files = self.file_storage.list_backups()
        
        # Merge with in-memory records
        existing_files = {b.file.filename for b in self._backups if b.file}
        
        for f in files:
            if f['filename'] not in existing_files:
                # Create a record for existing file
                record = BackupRecord(
                    id=RecordId.generate(),
                    job_id=JobId.generate(),
                    metadata=None,
                    status=BackupStatus.COMPLETED,
                    start_time=f['created_at'],
                    file=BackupFile(
                        filename=f['filename'],
                        path=f['path'],
                        size=f['size'],
                        checksum=f.get('checksum', '')
                    )
                )
                self._backups.append(record)
        
        return sorted(
            [b for b in self._backups if b.status == BackupStatus.COMPLETED],
            key=lambda b: b.start_time,
            reverse=True
        )
    
    def backup_exists(self, filename: str) -> bool:
        """檢查備份檔案是否存在"""
        return self.file_storage.backup_exists(filename)
    
    def execute_backup(
        self,
        task_id: str,
        label: Optional[str] = None,
        trigger_type: TriggerType = TriggerType.SCHEDULED
    ) -> None:
        """
        執行備份
        
        這是主要的備份工作流程
        """
        logger.info(f"Starting backup task: {task_id}")
        self._is_running = True
        
        # Create backup record
        job_id = JobId.generate()
        record = BackupRecord.create(
            job_id=job_id,
            trigger_type=trigger_type,
            label=label
        )
        self._tasks[task_id] = record
        
        try:
            # Step 1: Check Redis connection
            logger.info("Checking Redis connection...")
            record.update_progress(10)
            
            if not self.redis_client.test_connection():
                raise Exception("Redis connection failed")
            
            # Step 2: Execute BGSAVE
            logger.info("Executing BGSAVE...")
            record.update_progress(20)
            
            self.redis_client.bgsave()
            
            # Step 3: Wait for RDB completion
            logger.info("Waiting for RDB file completion...")
            record.update_progress(40)
            
            self.redis_client.wait_for_bgsave(timeout=300)
            
            # Step 4: Copy RDB file
            logger.info("Copying RDB file to backup location...")
            record.update_progress(60)
            
            timestamp = datetime.now()
            backup_file = BackupFile.create(timestamp=timestamp, label=label)
            
            # Get RDB path and copy
            rdb_path = self.redis_client.get_rdb_path()
            self.file_storage.copy_backup(rdb_path, backup_file.filename)
            
            # Step 5: Calculate checksum and get size
            logger.info("Calculating checksum...")
            record.update_progress(80)
            
            file_info = self.file_storage.get_file_info(backup_file.filename)
            final_file = backup_file.with_metadata(
                size=file_info['size'],
                checksum=file_info['checksum']
            )
            
            # Step 6: Complete
            record.complete(file=final_file)
            record.update_progress(100)
            self._backups.append(record)
            
            # Update metrics
            self.metrics.record_backup_success(
                duration=record.calculate_duration().total_seconds(),
                size=final_file.size
            )
            
            logger.info(f"Backup completed: {final_file.filename}")
            
            # Step 7: Run cleanup if needed
            self._run_cleanup()
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            error = ErrorInfo(
                code="BACKUP_FAILED",
                message=str(e)
            )
            record.fail(error=error)
            
            # Update metrics
            self.metrics.record_backup_failure()
            
        finally:
            self._is_running = False
    
    def execute_restore(
        self,
        task_id: str,
        backup_file: str,
        create_snapshot: bool = True,
        validate_after: bool = True
    ) -> None:
        """
        執行還原
        """
        logger.info(f"Starting restore task: {task_id}, file: {backup_file}")
        
        try:
            # Step 1: Create pre-restore snapshot if requested
            if create_snapshot:
                logger.info("Creating pre-restore snapshot...")
                snapshot_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.rdb"
                self.execute_backup(
                    task_id=f"snapshot_{task_id}",
                    label="pre-restore",
                    trigger_type=TriggerType.PRE_RESTORE
                )
            
            # Step 2: Copy backup file to Redis data directory
            logger.info("Restoring backup file...")
            self.file_storage.restore_backup(backup_file)
            
            # Step 3: Restart Redis (in Docker, this would trigger container restart)
            # For now, we just reload the data
            logger.info("Reloading Redis data...")
            
            # Step 4: Validate if requested
            if validate_after:
                logger.info("Validating restored data...")
                info = self.redis_client.get_info()
                logger.info(f"Redis info after restore: keys={info.get('db0', {}).get('keys', 0)}")
            
            logger.info("Restore completed successfully")
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            raise
    
    def _run_cleanup(self) -> None:
        """執行清理"""
        try:
            completed_backups = [
                b for b in self._backups 
                if b.status == BackupStatus.COMPLETED
            ]
            
            plan = self.retention_policy.evaluate(completed_backups)
            
            if plan.to_delete:
                logger.info(f"Cleaning up {len(plan.to_delete)} expired backups")
                
                for record_id in plan.to_delete:
                    # Find the record
                    record = next(
                        (b for b in self._backups if b.id == record_id),
                        None
                    )
                    if record and record.file:
                        self.file_storage.delete_backup(record.file.filename)
                        self._backups.remove(record)
                        logger.info(f"Deleted backup: {record.file.filename}")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
    
    def get_last_backup_time(self) -> Optional[datetime]:
        """取得最後備份時間"""
        completed = [b for b in self._backups if b.status == BackupStatus.COMPLETED]
        if not completed:
            return None
        return max(b.start_time for b in completed)
    
    def get_next_backup_time(self) -> datetime:
        """取得下次備份時間"""
        return self.schedule.get_next_trigger_time()
