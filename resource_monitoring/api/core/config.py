"""
設定模組 - 集中管理所有環境變數和設定
"""

import os
import platform
from pathlib import Path
from typing import List


def _get_default_log_paths() -> List[str]:
    """根據作業系統自動檢測日誌路徑"""
    system = platform.system()
    paths = []

    if system == "Linux":
        candidates = ["/var/log/docker", "/var/log", "/app/data"]
    elif system == "Darwin":
        candidates = [
            "/var/log",
            "/var/log/system.log",
            f"{Path.home()}/Library/Logs",
            "/app/data",
        ]
    elif system == "Windows":
        candidates = [
            "C:\\logs",
            "C:\\ProgramData\\logs",
            f"{os.environ.get('APPDATA')}\\logs",
            "/app/data",
        ]
    else:
        candidates = ["/app/data"]

    for path in candidates:
        path_obj = Path(path)
        if path_obj.exists():
            paths.append(str(path))

    if not paths and Path("/app/data").exists():
        paths.append("/app/data")

    return paths


class Settings:
    """應用程式設定"""

    # === 服務連線設定 ===
    NODE_EXPORTER_URL: str = os.getenv("NODE_EXPORTER_URL", "http://node_exporter:9100")
    CADVISOR_URL: str = os.getenv("CADVISOR_URL", "http://cadvisor:9101")

    # === JWT 設定 ===
    JWT_ENABLED: bool = os.getenv("JWT_ENABLED", "true").lower() in ("true", "1", "yes")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_YEARS: int = int(os.getenv("JWT_EXPIRATION_YEARS", "3"))

    # === CPU 採樣設定 ===
    CPU_SAMPLE_INTERVAL_MINUTES: int = int(
        os.getenv("CPU_SAMPLE_INTERVAL_MINUTES", "1")
    )

    # === 資料儲存設定 ===
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "/app/data"))

    @property
    def CPU_METRICS_FILE(self) -> Path:
        return self.DATA_DIR / "cpu_metrics.json"

    @property
    def CONTAINER_CPU_METRICS_FILE(self) -> Path:
        return self.DATA_DIR / "container_cpu_metrics.json"

    @property
    def JWT_SECRET_FILE(self) -> Path:
        return self.DATA_DIR / ".jwt_secret"

    @property
    def JWT_TOKEN_INFO_FILE(self) -> Path:
        return self.DATA_DIR / ".jwt_token_info.json"

    # === Log 監控設定 ===
    LOG_MONITOR_ENABLED: bool = (
        os.getenv("LOG_MONITOR_ENABLED", "true").lower() == "true"
    )
    LOG_ACTIVITY_THRESHOLD_MINUTES: int = int(
        os.getenv("LOG_ACTIVITY_THRESHOLD_MINUTES", "5")
    )

    @property
    def LOG_MONITOR_PATHS(self) -> List[str]:
        """取得 log 監控路徑列表"""
        configured = os.getenv("LOG_MONITOR_PATHS", "")
        if configured:
            return [p.strip() for p in configured.split(";") if p.strip()]
        return _get_default_log_paths()

    def ensure_data_dir(self) -> None:
        """確保資料目錄存在"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def print_init_info(self) -> None:
        """列印初始化資訊"""
        print(f"[INIT] OS: {platform.system()}")
        print(f"[INIT] Log Monitor Enabled: {self.LOG_MONITOR_ENABLED}")
        print(f"[INIT] Log Monitor Paths: {self.LOG_MONITOR_PATHS}")
        print(f"[INIT] JWT Authentication Enabled: {self.JWT_ENABLED}")
        print(
            f"[INIT] CPU Sample Interval: {self.CPU_SAMPLE_INTERVAL_MINUTES} minute(s)"
        )


# 單例設定物件
settings = Settings()
