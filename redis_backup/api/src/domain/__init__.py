"""
Domain layer initialization
"""

from .value_objects import (
    JobId, RecordId, Schedule, RedisConnection, 
    StorageConfig, BackupFile, ErrorInfo, BackupMetadata,
    StorageStatus, ValidationResult,
    InvalidCronExpressionError, InvalidPortError
)

from .entities import (
    BackupRecord, RestoreRecord, BackupStatus, 
    TriggerType, RestoreStatus, InvalidStateTransitionError
)

from .aggregates import (
    BackupJob, RetentionPolicy, CleanupPlan,
    JobStatus, JobAlreadyRunningError, 
    RedisConnectionError, InsufficientStorageError, InvalidPolicyError
)

from .events import (
    DomainEvent, BackupStarted, BackupCompleted, BackupFailed,
    RestoreStarted, RestoreCompleted, RestoreFailed,
    CleanupExecuted, StorageSpaceLow, RedisConnectionLost
)

__all__ = [
    # Value Objects
    'JobId', 'RecordId', 'Schedule', 'RedisConnection',
    'StorageConfig', 'BackupFile', 'ErrorInfo', 'BackupMetadata',
    'StorageStatus', 'ValidationResult',
    
    # Entities
    'BackupRecord', 'RestoreRecord', 'BackupStatus',
    'TriggerType', 'RestoreStatus',
    
    # Aggregates
    'BackupJob', 'RetentionPolicy', 'CleanupPlan', 'JobStatus',
    
    # Events
    'DomainEvent', 'BackupStarted', 'BackupCompleted', 'BackupFailed',
    'RestoreStarted', 'RestoreCompleted', 'RestoreFailed',
    'CleanupExecuted', 'StorageSpaceLow', 'RedisConnectionLost',
    
    # Exceptions
    'InvalidCronExpressionError', 'InvalidPortError',
    'InvalidStateTransitionError', 'JobAlreadyRunningError',
    'RedisConnectionError', 'InsufficientStorageError', 'InvalidPolicyError',
]
