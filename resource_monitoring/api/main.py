"""
Resource Monitoring API

系統與容器資源監控 API
- 從 node_exporter 和 cAdvisor 取得系統與容器監控指標
- 監控系統日誌檔案以判斷服務運作狀態
- 支援 JWT 認證 (可配置啟用/關閉)
"""

import asyncio
import platform
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 匯入核心模組
from core.config import settings
from core.jwt_auth import initialize_jwt, jwt_manager

# 匯入路由模組
from routers import log_router, resource_router

# 匯入服務模組
from services.resource_monitor import cpu_sample_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 確保資料目錄存在
    settings.ensure_data_dir()

    # 列印初始化資訊
    settings.print_init_info()

    # 初始化 JWT (若啟用)
    sys.stderr.write("[APP] Calling initialize_jwt...\n")
    sys.stderr.flush()
    initialize_jwt()
    sys.stderr.write("[APP] JWT initialization completed\n")
    sys.stderr.flush()

    # 啟動 CPU 採樣任務
    task = asyncio.create_task(cpu_sample_task())
    sys.stderr.write("[APP] Resource Monitoring API started with CPU sampling task\n")
    sys.stderr.flush()

    yield

    # 關閉時取消任務
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("[APP] CPU sampling task cancelled")


app = FastAPI(
    title="Resource Monitoring API",
    description="系統與容器資源監控 API",
    version="2.1.0",
    lifespan=lifespan,
)

# CORS 中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(resource_router.router)
app.include_router(log_router.router)


@app.get("/")
async def root():
    """API 根路徑 (無需認證)"""
    auth_mode = (
        "Enabled (Bearer token required)"
        if jwt_manager.is_enabled
        else "Disabled (all endpoints open)"
    )
    return {
        "service": "Resource Monitoring API",
        "version": "2.1.0",
        "authentication": auth_mode,
        "jwt_enabled": jwt_manager.is_enabled,
        "endpoints": {
            "/health": "Health check (no auth required)",
            "/system-metrics": (
                "System and container metrics"
                + (" (JWT required)" if jwt_manager.is_enabled else "")
            ),
            "/cpu-config": (
                "CPU sampling configuration"
                + (" (JWT required)" if jwt_manager.is_enabled else "")
            ),
            "/log-status": (
                "Log file monitoring status"
                + (" (JWT required)" if jwt_manager.is_enabled else "")
            ),
        },
    }


@app.get("/health")
async def health_check():
    """健康檢查端點 (無需認證)"""
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "jwt_enabled": jwt_manager.is_enabled,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
