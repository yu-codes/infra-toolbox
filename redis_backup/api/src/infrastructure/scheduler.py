"""
Infrastructure layer - Backup Scheduler

備份排程器
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.domain.value_objects import Schedule
from src.domain.entities import TriggerType

logger = logging.getLogger(__name__)


class BackupScheduler:
    """備份排程器"""
    
    def __init__(self, backup_service, schedule: Schedule):
        self.backup_service = backup_service
        self.schedule = schedule
        self._scheduler = BackgroundScheduler()
        self._job_id = "backup_job"
    
    def start(self) -> None:
        """啟動排程器"""
        # Parse cron expression
        cron_parts = self.schedule.expression.split()
        
        if len(cron_parts) == 5:
            minute, hour, day, month, day_of_week = cron_parts
        else:
            # Default to daily at 2 AM
            minute, hour, day, month, day_of_week = "0", "2", "*", "*", "*"
        
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        )
        
        self._scheduler.add_job(
            self._execute_scheduled_backup,
            trigger=trigger,
            id=self._job_id,
            name="Scheduled Backup",
            replace_existing=True
        )
        
        self._scheduler.start()
        
        next_run = self.schedule.get_next_trigger_time()
        logger.info(f"Scheduler started. Next backup at: {next_run}")
    
    def shutdown(self) -> None:
        """關閉排程器"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown")
    
    def _execute_scheduled_backup(self) -> None:
        """執行排程備份"""
        logger.info("Scheduled backup triggered")
        
        if self.backup_service.is_running():
            logger.warning("Skipping scheduled backup: another backup is running")
            return
        
        task_id = self.backup_service.create_task_id()
        self.backup_service.execute_backup(
            task_id=task_id,
            trigger_type=TriggerType.SCHEDULED
        )
    
    def get_next_run_time(self) -> datetime:
        """取得下次執行時間"""
        job = self._scheduler.get_job(self._job_id)
        if job and job.next_run_time:
            return job.next_run_time
        return self.schedule.get_next_trigger_time()
