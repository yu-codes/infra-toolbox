"""
Infrastructure layer - Metrics Collector

Prometheus 指標收集器
"""

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry


class MetricsCollector:
    """Prometheus 指標收集器"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Counters
        self.backup_total = Counter(
            'redis_backup_total',
            'Total number of backup attempts',
            registry=self.registry
        )
        
        self.backup_success_total = Counter(
            'redis_backup_success_total',
            'Total number of successful backups',
            registry=self.registry
        )
        
        self.backup_failed_total = Counter(
            'redis_backup_failed_total',
            'Total number of failed backups',
            registry=self.registry
        )
        
        # Gauges
        self.backup_last_success_time = Gauge(
            'redis_backup_last_success_timestamp',
            'Timestamp of the last successful backup',
            registry=self.registry
        )
        
        self.backup_last_size = Gauge(
            'redis_backup_last_size_bytes',
            'Size of the last backup in bytes',
            registry=self.registry
        )
        
        self.backup_count = Gauge(
            'redis_backup_count',
            'Current number of backup files',
            registry=self.registry
        )
        
        # Histograms
        self.backup_duration = Histogram(
            'redis_backup_duration_seconds',
            'Duration of backup operations in seconds',
            buckets=[10, 30, 60, 120, 300, 600, 1800],
            registry=self.registry
        )
        
        self.backup_size = Histogram(
            'redis_backup_size_bytes',
            'Size of backup files in bytes',
            buckets=[
                1024 * 1024,        # 1 MB
                10 * 1024 * 1024,   # 10 MB
                100 * 1024 * 1024,  # 100 MB
                1024 * 1024 * 1024, # 1 GB
                10 * 1024 * 1024 * 1024,  # 10 GB
            ],
            registry=self.registry
        )
    
    def record_backup_success(self, duration: float, size: int) -> None:
        """記錄備份成功"""
        import time
        
        self.backup_total.inc()
        self.backup_success_total.inc()
        self.backup_duration.observe(duration)
        self.backup_size.observe(size)
        self.backup_last_success_time.set(time.time())
        self.backup_last_size.set(size)
    
    def record_backup_failure(self) -> None:
        """記錄備份失敗"""
        self.backup_total.inc()
        self.backup_failed_total.inc()
    
    def set_backup_count(self, count: int) -> None:
        """設定備份數量"""
        self.backup_count.set(count)
