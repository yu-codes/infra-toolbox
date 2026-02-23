"""
Unit tests for Domain Value Objects
"""

import pytest
from datetime import datetime, timedelta

from src.domain.value_objects import (
    Schedule, RedisConnection, BackupFile, ErrorInfo,
    BackupMetadata, StorageStatus, JobId, RecordId,
    InvalidCronExpressionError, InvalidPortError
)


class TestSchedule:
    """Schedule 值物件測試"""
    
    def test_should_create_schedule_with_valid_cron_expression(self):
        """應該使用有效的 Cron 表達式建立 Schedule"""
        cron_expr = "0 2 * * *"
        schedule = Schedule(expression=cron_expr)
        assert schedule.expression == cron_expr
    
    def test_should_reject_invalid_cron_expression(self):
        """應該拒絕無效的 Cron 表達式"""
        with pytest.raises(InvalidCronExpressionError):
            Schedule(expression="invalid")
    
    def test_should_return_true_when_time_matches_schedule(self):
        """當時間符合排程時應該返回 True"""
        schedule = Schedule(expression="0 2 * * *")
        check_time = datetime(2024, 1, 1, 2, 0, 0)
        assert schedule.is_triggered_at(check_time) is True
    
    def test_should_return_false_when_time_not_matches(self):
        """當時間不符合排程時應該返回 False"""
        schedule = Schedule(expression="0 2 * * *")
        check_time = datetime(2024, 1, 1, 3, 0, 0)
        assert schedule.is_triggered_at(check_time) is False
    
    def test_should_calculate_next_trigger_time(self):
        """應該計算下一次觸發時間"""
        schedule = Schedule(expression="0 2 * * *")
        current_time = datetime(2024, 1, 1, 10, 0, 0)
        next_time = schedule.get_next_trigger_time(after=current_time)
        assert next_time == datetime(2024, 1, 2, 2, 0, 0)


class TestRedisConnection:
    """RedisConnection 值物件測試"""
    
    def test_should_create_connection_with_valid_config(self):
        """應該使用有效配置建立連線"""
        conn = RedisConnection(
            host="localhost",
            port=6379,
            password="secret",
            database=0
        )
        assert conn.host == "localhost"
        assert conn.port == 6379
    
    def test_should_reject_invalid_port(self):
        """應該拒絕無效的 port"""
        with pytest.raises(InvalidPortError):
            RedisConnection(host="localhost", port=-1)
    
    def test_should_create_connection_string(self):
        """應該生成正確的連線字串"""
        conn = RedisConnection(host="localhost", port=6379, database=0)
        assert conn.to_connection_string() == "redis://localhost:6379/0"
    
    def test_should_include_password_in_connection_string(self):
        """連線字串應該包含密碼"""
        conn = RedisConnection(
            host="localhost", 
            port=6379, 
            password="secret",
            database=0
        )
        assert "secret" in conn.to_connection_string()


class TestBackupFile:
    """BackupFile 值物件測試"""
    
    def test_should_generate_filename_with_timestamp(self):
        """應該生成帶時間戳的檔案名稱"""
        timestamp = datetime(2024, 1, 15, 2, 30, 45)
        file = BackupFile.create(timestamp=timestamp)
        assert file.filename == "redis_backup_20240115_023045.rdb"
    
    def test_should_include_label_in_filename(self):
        """應該在檔案名稱中包含標籤"""
        timestamp = datetime(2024, 1, 15, 2, 30, 45)
        file = BackupFile.create(timestamp=timestamp, label="pre-migration")
        assert file.filename == "redis_backup_20240115_023045_pre-migration.rdb"
    
    def test_should_validate_checksum(self):
        """應該驗證校驗碼"""
        file = BackupFile(
            filename="test.rdb",
            path="/backups/test.rdb",
            size=1024,
            checksum="abc123"
        )
        assert file.validate_checksum("abc123") is True
        assert file.validate_checksum("wrong") is False
    
    def test_should_create_new_instance_with_metadata(self):
        """應該返回帶有 size 和 checksum 的新實例"""
        file = BackupFile.create(timestamp=datetime.now())
        updated = file.with_metadata(size=1024, checksum="abc123")
        
        assert updated.size == 1024
        assert updated.checksum == "abc123"
        assert file.size == 0  # Original unchanged


class TestErrorInfo:
    """ErrorInfo 值物件測試"""
    
    def test_should_create_error_info(self):
        """應該建立錯誤資訊"""
        error = ErrorInfo(
            code="REDIS_ERROR",
            message="Connection failed"
        )
        assert error.code == "REDIS_ERROR"
        assert error.message == "Connection failed"
        assert error.retry_count == 0
    
    def test_should_increment_retry_count(self):
        """應該增加重試計數"""
        error = ErrorInfo(code="ERROR", message="test")
        error2 = error.with_retry()
        
        assert error2.retry_count == 1
        assert error.retry_count == 0  # Original unchanged


class TestBackupMetadata:
    """BackupMetadata 值物件測試"""
    
    def test_should_create_metadata(self):
        """應該建立元資料"""
        metadata = BackupMetadata(
            label="daily",
            trigger_type="SCHEDULED"
        )
        assert metadata.label == "daily"
        assert metadata.is_important is False
    
    def test_should_mark_important(self):
        """應該標記為重要"""
        metadata = BackupMetadata(label="daily")
        marked = metadata.mark_important()
        
        assert marked.is_important is True
        assert metadata.is_important is False  # Original unchanged


class TestStorageStatus:
    """StorageStatus 值物件測試"""
    
    def test_should_calculate_usage_percent(self):
        """應該計算使用率百分比"""
        status = StorageStatus(
            total_space=100 * 1024 * 1024 * 1024,  # 100 GB
            used_space=50 * 1024 * 1024 * 1024,    # 50 GB
            available_space=50 * 1024 * 1024 * 1024
        )
        assert status.usage_percent == 50.0
    
    def test_should_detect_low_space(self):
        """應該偵測空間不足"""
        status = StorageStatus(
            total_space=100,
            used_space=90,
            available_space=10
        )
        assert status.is_low(threshold_percent=85.0) is True
    
    def test_should_format_available_space(self):
        """應該格式化可用空間"""
        status = StorageStatus(
            total_space=100 * 1024 * 1024 * 1024,
            used_space=50 * 1024 * 1024 * 1024,
            available_space=50 * 1024 * 1024 * 1024
        )
        assert "GB" in status.format_available()


class TestJobId:
    """JobId 值物件測試"""
    
    def test_should_generate_unique_id(self):
        """應該生成唯一 ID"""
        id1 = JobId.generate()
        id2 = JobId.generate()
        assert id1.value != id2.value


class TestRecordId:
    """RecordId 值物件測試"""
    
    def test_should_generate_unique_id(self):
        """應該生成唯一 ID"""
        id1 = RecordId.generate()
        id2 = RecordId.generate()
        assert id1.value != id2.value
