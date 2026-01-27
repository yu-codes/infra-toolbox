"""
Infrastructure layer - File Storage Adapter

檔案儲存適配器
"""

import hashlib
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.domain.value_objects import StorageStatus

logger = logging.getLogger(__name__)


class FileStorageAdapter:
    """檔案儲存適配器"""
    
    def __init__(
        self,
        backup_path: str = "/backups",
        redis_data_path: str = "/redis-data"
    ):
        self.backup_path = Path(backup_path)
        self.redis_data_path = Path(redis_data_path)
        
        # Ensure backup directory exists
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有備份檔案"""
        backups = []
        
        for file_path in self.backup_path.glob("*.rdb"):
            stat = file_path.stat()
            backups.append({
                'filename': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime),
                'checksum': self._calculate_checksum(file_path)
            })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def backup_exists(self, filename: str) -> bool:
        """檢查備份檔案是否存在"""
        return (self.backup_path / filename).exists()
    
    def copy_backup(self, source: str, dest_filename: str) -> str:
        """複製備份檔案"""
        source_path = Path(source)
        dest_path = self.backup_path / dest_filename
        
        # Handle case where source is in Redis data path
        if not source_path.exists():
            # Try looking in redis data path
            redis_rdb = self.redis_data_path / "dump.rdb"
            if redis_rdb.exists():
                source_path = redis_rdb
            else:
                raise FileNotFoundError(f"Source file not found: {source}")
        
        logger.info(f"Copying {source_path} to {dest_path}")
        shutil.copy2(source_path, dest_path)
        
        return str(dest_path)
    
    def restore_backup(self, filename: str) -> None:
        """還原備份檔案到 Redis 資料目錄"""
        source_path = self.backup_path / filename
        dest_path = self.redis_data_path / "dump.rdb"
        
        if not source_path.exists():
            raise FileNotFoundError(f"Backup file not found: {filename}")
        
        logger.info(f"Restoring {source_path} to {dest_path}")
        shutil.copy2(source_path, dest_path)
    
    def delete_backup(self, filename: str) -> bool:
        """刪除備份檔案"""
        file_path = self.backup_path / filename
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted backup: {filename}")
            return True
        
        return False
    
    def get_file_info(self, filename: str) -> Dict[str, Any]:
        """取得檔案資訊"""
        file_path = self.backup_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        
        stat = file_path.stat()
        
        return {
            'filename': filename,
            'path': str(file_path),
            'size': stat.st_size,
            'checksum': self._calculate_checksum(file_path),
            'created_at': datetime.fromtimestamp(stat.st_mtime)
        }
    
    def get_storage_status(self) -> StorageStatus:
        """取得儲存狀態"""
        stat = shutil.disk_usage(self.backup_path)
        
        return StorageStatus(
            total_space=stat.total,
            used_space=stat.used,
            available_space=stat.free
        )
    
    def get_available_space(self) -> int:
        """取得可用空間"""
        stat = shutil.disk_usage(self.backup_path)
        return stat.free
    
    def _calculate_checksum(self, file_path: Path, algorithm: str = 'md5') -> str:
        """計算檔案校驗碼"""
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
