"""
Log 監控路由

提供日誌監控相關的 API 端點
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from core.config import settings
from core.jwt_auth import verify_jwt_token
from services.log_monitor import check_all_log_paths, get_specific_log_status

router = APIRouter(prefix="/log-status", tags=["Log Monitoring"])


@router.get("")
async def get_log_status(token: dict = Depends(verify_jwt_token)) -> Dict[str, Any]:
    """
    監控日誌檔案狀態 (需要 JWT 認證，若啟用)

    根據 LOG_MONITOR_PATHS 環境變數監控指定日誌檔案/目錄的修改時間，
    以判斷相應服務是否在正常運作。

    返回:
    - status: success/partial/error/disabled
    - paths: 每個路徑的詳細狀況
    - is_active: 所有路徑是否都在活躍狀態
    - activity_threshold_minutes: 活躍判定的時間閾值
    """
    result = check_all_log_paths()

    # 增加整體活躍狀態判定
    if result["status"] == "disabled":
        result["is_active"] = False
        result["overall_status"] = "Log monitoring not enabled"
    elif result["status"] == "error":
        result["is_active"] = False
        result["overall_status"] = "No valid log paths to monitor"
    else:
        result["is_active"] = (
            result["active_paths"] > 0
            and result["active_paths"] == result["total_paths"]
        )
        if result["is_active"]:
            result["overall_status"] = "All services are active"
        else:
            result["overall_status"] = (
                f"{result['active_paths']}/{result['total_paths']} services are active"
            )

    return result


@router.get("/{path_index}")
async def get_log_status_by_index(
    path_index: int, token: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """
    取得特定日誌路徑的詳細狀態

    Args:
        path_index: 日誌路徑在 LOG_MONITOR_PATHS 中的索引 (0-based)

    Returns:
        該路徑的詳細狀況，包括最後修改時間、檔案名稱等
    """
    if not settings.LOG_MONITOR_ENABLED:
        raise HTTPException(status_code=503, detail="Log monitoring is disabled")

    log_paths = settings.LOG_MONITOR_PATHS
    if not log_paths or path_index < 0 or path_index >= len(log_paths):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid path index. Available paths: {len(log_paths)}",
        )

    result = get_specific_log_status(path_index)
    return result
