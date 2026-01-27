"""
Configuration settings for Redis Backup Service
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Redis settings
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_database: int = 0
    redis_data_path: str = "/redis-data"
    
    # Backup settings
    backup_path: str = "/backups"
    backup_schedule: str = "0 2 * * *"  # Daily at 2 AM
    
    # Retention policy
    retention_days: int = 7
    max_backups: int = 30
    min_backups: int = 3
    
    # Notification settings (optional)
    slack_webhook_url: Optional[str] = None
    email_to: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_prefix = ""
        case_sensitive = False
