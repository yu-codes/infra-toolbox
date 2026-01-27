"""
Infrastructure layer - Redis Client Adapter

Redis 客戶端適配器
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

import redis

logger = logging.getLogger(__name__)


class RedisClientAdapter:
    """Redis 客戶端適配器"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        database: int = 0,
        socket_timeout: int = 5
    ):
        self.host = host
        self.port = port
        self.password = password
        self.database = database
        self.socket_timeout = socket_timeout
        self._client: Optional[redis.Redis] = None
        self._last_connected: Optional[datetime] = None
    
    def _get_client(self) -> redis.Redis:
        """取得 Redis 客戶端"""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.database,
                socket_timeout=self.socket_timeout,
                decode_responses=True
            )
        return self._client
    
    def test_connection(self) -> bool:
        """測試連線"""
        try:
            client = self._get_client()
            result = client.ping()
            if result:
                self._last_connected = datetime.now()
            return result
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Redis error: {e}")
            return False
    
    def bgsave(self) -> bool:
        """執行 BGSAVE 命令"""
        try:
            client = self._get_client()
            client.bgsave()
            logger.info("BGSAVE command executed")
            return True
        except redis.ResponseError as e:
            # BGSAVE already in progress is OK
            if "already in progress" in str(e).lower():
                logger.info("BGSAVE already in progress")
                return True
            raise
    
    def lastsave(self) -> datetime:
        """取得最後儲存時間"""
        client = self._get_client()
        timestamp = client.lastsave()
        return timestamp
    
    def wait_for_bgsave(self, timeout: int = 300, poll_interval: float = 1.0) -> bool:
        """等待 BGSAVE 完成"""
        start_time = time.time()
        initial_lastsave = self.lastsave()
        
        logger.info(f"Waiting for BGSAVE to complete (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            current_lastsave = self.lastsave()
            if current_lastsave > initial_lastsave:
                logger.info("BGSAVE completed")
                return True
            time.sleep(poll_interval)
        
        raise TimeoutError(f"BGSAVE did not complete within {timeout} seconds")
    
    def get_rdb_path(self) -> str:
        """取得 RDB 檔案路徑"""
        client = self._get_client()
        config = client.config_get('dir')
        dbfilename = client.config_get('dbfilename')
        
        dir_path = config.get('dir', '/data')
        filename = dbfilename.get('dbfilename', 'dump.rdb')
        
        return f"{dir_path}/{filename}"
    
    def get_info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """取得 Redis 資訊"""
        client = self._get_client()
        if section:
            return client.info(section)
        return client.info()
    
    def get_dbsize(self) -> int:
        """取得資料庫大小（key 數量）"""
        client = self._get_client()
        return client.dbsize()
    
    def get_memory_usage(self) -> int:
        """取得記憶體使用量"""
        info = self.get_info('memory')
        return info.get('used_memory', 0)
