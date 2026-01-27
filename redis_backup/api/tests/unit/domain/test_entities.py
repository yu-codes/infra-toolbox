"""
Unit tests for Domain Entities
"""

import pytest
from datetime import datetime, timedelta

from src.domain.entities import (
    BackupRecord, RestoreRecord, BackupStatus, 
    TriggerType, RestoreStatus, InvalidStateTransitionError
)
from src.domain.value_objects import (
    JobId, BackupFile, ErrorInfo, BackupMetadata, ValidationResult
)


class TestBackupRecord:
    """BackupRecord 實體測試"""
    
    def test_should_create_record_with_in_progress_status(self):
        """建立時應該是 IN_PROGRESS 狀態"""
        record = BackupRecord.create(
            job_id=JobId("job-1"),
            trigger_type=TriggerType.SCHEDULED
        )
        assert record.status == BackupStatus.IN_PROGRESS
        assert record.start_time is not None
    
    def test_should_update_progress(self):
        """應該更新進度"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        record.update_progress(50)
        assert record.progress == 50
    
    def test_should_clamp_progress_to_valid_range(self):
        """進度應該限制在有效範圍內"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        record.update_progress(150)
        assert record.progress == 100
        
        record2 = BackupRecord.create(job_id=JobId("job-2"))
        record2.update_progress(-10)
        assert record2.progress == 0
    
    def test_should_complete_record_with_file_info(self):
        """完成時應該包含檔案資訊"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        file = BackupFile(
            filename="backup.rdb",
            path="/backups/backup.rdb",
            size=1024,
            checksum="abc123"
        )
        
        record.complete(file=file)
        
        assert record.status == BackupStatus.COMPLETED
        assert record.file == file
        assert record.end_time is not None
        assert record.progress == 100
    
    def test_should_fail_record_with_error_info(self):
        """失敗時應該包含錯誤資訊"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        error = ErrorInfo(
            code="REDIS_CONNECTION_ERROR",
            message="Cannot connect to Redis"
        )
        
        record.fail(error=error)
        
        assert record.status == BackupStatus.FAILED
        assert record.error_info == error
        assert record.end_time is not None
    
    def test_should_not_change_completed_status(self):
        """已完成的記錄不應該再變更狀態"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        file = BackupFile(
            filename="backup.rdb",
            path="/backups/backup.rdb",
            size=1024,
            checksum="abc123"
        )
        record.complete(file=file)
        
        with pytest.raises(InvalidStateTransitionError):
            record.fail(error=ErrorInfo(code="ERROR", message="error"))
    
    def test_should_not_update_progress_after_completion(self):
        """完成後不應該更新進度"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        file = BackupFile(
            filename="backup.rdb",
            path="/backups/backup.rdb",
            size=1024,
            checksum="abc123"
        )
        record.complete(file=file)
        
        with pytest.raises(InvalidStateTransitionError):
            record.update_progress(50)
    
    def test_should_calculate_duration(self):
        """應該計算備份持續時間"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        record.start_time = datetime(2024, 1, 1, 2, 0, 0)
        record.end_time = datetime(2024, 1, 1, 2, 5, 30)
        
        duration = record.calculate_duration()
        
        assert duration == timedelta(minutes=5, seconds=30)
    
    def test_should_return_none_duration_when_not_completed(self):
        """未完成時 duration 應該為 None"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        assert record.calculate_duration() is None
    
    def test_should_mark_as_important(self):
        """應該標記為重要"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        file = BackupFile(
            filename="backup.rdb",
            path="/backups/backup.rdb",
            size=1024,
            checksum="abc123"
        )
        record.complete(file=file)
        
        record.mark_as_important()
        
        assert record.metadata.is_important is True
    
    def test_should_check_if_expired(self):
        """應該檢查是否過期"""
        record = BackupRecord.create(job_id=JobId("job-1"))
        record.start_time = datetime(2024, 1, 1, 0, 0, 0)
        
        current = datetime(2024, 1, 10, 0, 0, 0)
        
        assert record.is_expired(retention_days=7, current_time=current) is True
        assert record.is_expired(retention_days=14, current_time=current) is False


class TestRestoreRecord:
    """RestoreRecord 實體測試"""
    
    def test_should_create_restore_record(self):
        """應該建立還原記錄"""
        from src.domain.value_objects import RecordId
        
        record = RestoreRecord.create(
            job_id=JobId("job-1"),
            source_backup_id=RecordId("backup-1")
        )
        
        assert record.status == RestoreStatus.PENDING
        assert record.start_time is not None
    
    def test_should_update_status(self):
        """應該更新狀態"""
        from src.domain.value_objects import RecordId
        
        record = RestoreRecord.create(
            job_id=JobId("job-1"),
            source_backup_id=RecordId("backup-1")
        )
        
        record.update_status(RestoreStatus.COPYING_FILE)
        
        assert record.status == RestoreStatus.COPYING_FILE
    
    def test_should_complete_with_validation(self):
        """應該帶驗證結果完成"""
        from src.domain.value_objects import RecordId
        
        record = RestoreRecord.create(
            job_id=JobId("job-1"),
            source_backup_id=RecordId("backup-1")
        )
        
        validation = ValidationResult(
            is_valid=True,
            key_count=1000,
            memory_usage=1024 * 1024
        )
        
        record.complete(validation=validation)
        
        assert record.status == RestoreStatus.COMPLETED
        assert record.validation == validation
        assert record.end_time is not None
