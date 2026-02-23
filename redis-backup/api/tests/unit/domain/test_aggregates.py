"""
Unit tests for Domain Aggregates
"""

import pytest
from datetime import datetime

from src.domain.aggregates import (
    BackupJob, RetentionPolicy, CleanupPlan,
    JobStatus, JobAlreadyRunningError, InvalidPolicyError
)
from src.domain.value_objects import (
    Schedule, RedisConnection, StorageConfig, JobId
)
from src.domain.entities import BackupRecord, BackupStatus, TriggerType


def create_backup_record(
    created_at: datetime = None,
    label: str = None,
    is_important: bool = False
) -> BackupRecord:
    """建立測試用 BackupRecord"""
    from src.domain.value_objects import BackupFile, BackupMetadata
    
    record = BackupRecord.create(
        job_id=JobId.generate(),
        trigger_type=TriggerType.SCHEDULED,
        label=label
    )
    
    if created_at:
        record.start_time = created_at
    
    # Complete the record
    file = BackupFile(
        filename=f"backup_{record.id}.rdb",
        path=f"/backups/backup_{record.id}.rdb",
        size=1024,
        checksum="abc123"
    )
    record.complete(file=file)
    
    if is_important:
        record.mark_as_important()
    
    return record


class TestBackupJob:
    """BackupJob 聚合根測試"""
    
    @pytest.fixture
    def valid_schedule(self):
        return Schedule(expression="0 2 * * *")
    
    @pytest.fixture
    def valid_connection(self):
        return RedisConnection(host="localhost", port=6379)
    
    @pytest.fixture
    def valid_storage(self):
        return StorageConfig(backup_path="/backups")
    
    def test_should_create_job_with_idle_status(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """建立時應該是 IDLE 狀態"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        assert job.status == JobStatus.IDLE
    
    def test_should_start_job(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """應該可以啟動任務"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        
        job.start()
        
        assert job.status == JobStatus.RUNNING
    
    def test_should_not_start_when_already_running(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """已在執行時不應該再次啟動"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        job.start()
        
        with pytest.raises(JobAlreadyRunningError):
            job.start()
    
    def test_should_complete_job(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """應該可以完成任務"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        job.start()
        job.complete()
        
        assert job.status == JobStatus.IDLE
    
    def test_should_check_execution_conditions(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """應該檢查執行條件"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        
        # All conditions met
        can_exec, reason = job.can_execute(
            redis_connected=True,
            available_space=1024 * 1024 * 1024
        )
        assert can_exec is True
        
        # Redis not connected
        can_exec, reason = job.can_execute(
            redis_connected=False,
            available_space=1024 * 1024 * 1024
        )
        assert can_exec is False
        assert "not connected" in reason
    
    def test_should_trigger_at_scheduled_time(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """應該在排程時間觸發"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        
        check_time = datetime(2024, 1, 1, 2, 0, 0)
        assert job.should_execute_at(check_time) is True
        
        check_time = datetime(2024, 1, 1, 3, 0, 0)
        assert job.should_execute_at(check_time) is False
    
    def test_should_not_trigger_when_running(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """執行中時不應該觸發"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        job.start()
        
        check_time = datetime(2024, 1, 1, 2, 0, 0)
        assert job.should_execute_at(check_time) is False
    
    def test_should_reschedule(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """應該可以重新設定排程"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        
        new_schedule = Schedule(expression="0 */6 * * *")
        job.reschedule(new_schedule)
        
        assert job.schedule == new_schedule
    
    def test_should_get_next_backup_time(
        self, valid_schedule, valid_connection, valid_storage
    ):
        """應該取得下次備份時間"""
        job = BackupJob.create(
            schedule=valid_schedule,
            connection=valid_connection,
            storage=valid_storage
        )
        
        next_time = job.get_next_backup_time()
        assert next_time is not None


class TestRetentionPolicy:
    """RetentionPolicy 聚合根測試"""
    
    def test_should_create_policy_with_valid_config(self):
        """應該使用有效配置建立策略"""
        policy = RetentionPolicy.create(
            retention_days=7,
            max_backups=30,
            min_backups=3
        )
        
        assert policy.retention_days == 7
        assert policy.max_backups == 30
        assert policy.min_backups == 3
    
    def test_should_reject_min_backups_greater_than_max(self):
        """min_backups 不應該大於 max_backups"""
        with pytest.raises(InvalidPolicyError):
            RetentionPolicy.create(
                retention_days=7,
                max_backups=3,
                min_backups=5
            )
    
    def test_should_reject_min_backups_less_than_one(self):
        """min_backups 不應該小於 1"""
        with pytest.raises(InvalidPolicyError):
            RetentionPolicy.create(
                retention_days=7,
                max_backups=30,
                min_backups=0
            )
    
    def test_should_identify_expired_backups(self):
        """應該識別過期備份"""
        policy = RetentionPolicy.create(
            retention_days=7,
            max_backups=30,
            min_backups=1
        )
        now = datetime(2024, 1, 15)
        
        backups = [
            create_backup_record(created_at=datetime(2024, 1, 1)),   # 過期
            create_backup_record(created_at=datetime(2024, 1, 5)),   # 過期
            create_backup_record(created_at=datetime(2024, 1, 10)),  # 有效
            create_backup_record(created_at=datetime(2024, 1, 14)),  # 有效
        ]
        
        plan = policy.evaluate(backups, current_time=now)
        
        assert len(plan.to_delete) == 2
        assert len(plan.to_keep) == 2
    
    def test_should_keep_minimum_backups(self):
        """應該保留最少數量的備份"""
        policy = RetentionPolicy.create(
            retention_days=7,
            max_backups=30,
            min_backups=3
        )
        now = datetime(2024, 1, 15)
        
        # 所有備份都過期，但只有 3 個
        backups = [
            create_backup_record(created_at=datetime(2024, 1, 1)),
            create_backup_record(created_at=datetime(2024, 1, 2)),
            create_backup_record(created_at=datetime(2024, 1, 3)),
        ]
        
        plan = policy.evaluate(backups, current_time=now)
        
        # 不刪除任何備份（保持最小數量）
        assert len(plan.to_delete) == 0
        assert len(plan.to_keep) == 3
    
    def test_should_delete_oldest_when_exceeds_max(self):
        """超過最大數量時應該刪除最舊的"""
        policy = RetentionPolicy.create(
            retention_days=30,  # 長保留期
            max_backups=3,
            min_backups=1
        )
        
        backups = [
            create_backup_record(created_at=datetime(2024, 1, 1)),  # 最舊 - 刪除
            create_backup_record(created_at=datetime(2024, 1, 2)),  # 刪除
            create_backup_record(created_at=datetime(2024, 1, 3)),
            create_backup_record(created_at=datetime(2024, 1, 4)),
            create_backup_record(created_at=datetime(2024, 1, 5)),  # 最新
        ]
        
        plan = policy.evaluate(backups, current_time=datetime(2024, 1, 6))
        
        assert len(plan.to_delete) == 2
        assert len(plan.to_keep) == 3
    
    def test_should_protect_important_backups(self):
        """應該保護重要備份"""
        policy = RetentionPolicy.create(
            retention_days=7,
            max_backups=30,
            min_backups=1,
            protected_labels=["important", "pre-migration"]
        )
        now = datetime(2024, 1, 15)
        
        important_backup = create_backup_record(
            created_at=datetime(2024, 1, 1),  # 過期
            is_important=True
        )
        
        plan = policy.evaluate([important_backup], current_time=now)
        
        assert len(plan.to_delete) == 0
        assert important_backup.id in plan.to_keep
    
    def test_should_protect_labeled_backups(self):
        """應該保護帶有受保護標籤的備份"""
        policy = RetentionPolicy.create(
            retention_days=7,
            max_backups=30,
            min_backups=1,
            protected_labels=["pre-migration"]
        )
        now = datetime(2024, 1, 15)
        
        labeled_backup = create_backup_record(
            created_at=datetime(2024, 1, 1),  # 過期
            label="pre-migration"
        )
        
        plan = policy.evaluate([labeled_backup], current_time=now)
        
        assert len(plan.to_delete) == 0
