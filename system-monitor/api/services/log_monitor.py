"""
Log 監控服務

監控指定日誌檔案/目錄的修改時間，判斷服務是否正常運作
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.config import settings


def get_latest_log_file_info(log_path: str) -> Dict[str, Any]:
    """
    取得日誌檔案的最新修改時間和其他資訊

    Args:
        log_path: 日誌目錄或單一檔案路徑

    Returns:
        包含 latest_time, latest_file, activity_status 的 dict
    """
    path = Path(log_path)

    if not path.exists():
        return {
            "status": "error",
            "message": f"Path not found: {log_path}",
            "latest_time": None,
            "latest_file": None,
            "is_active": False,
            "activity_status": "path_not_found",
        }

    try:
        latest_time = 0
        latest_file = None
        file_count = 0

        if path.is_dir():
            for entry in path.rglob("*"):
                if entry.is_file():
                    file_count += 1
                    file_time = entry.stat().st_mtime
                    if file_time > latest_time:
                        latest_time = file_time
                        latest_file = entry.name
        elif path.is_file():
            file_count = 1
            latest_time = path.stat().st_mtime
            latest_file = path.name

        if latest_time == 0:
            return {
                "status": "error",
                "message": "No files found in directory",
                "latest_time": None,
                "latest_file": None,
                "is_active": False,
                "activity_status": "no_files",
                "file_count": file_count,
            }

        # 判斷活躍狀態
        current_time = time.time()
        time_diff_minutes = (current_time - latest_time) / 60
        threshold_minutes = settings.LOG_ACTIVITY_THRESHOLD_MINUTES
        is_active = time_diff_minutes <= threshold_minutes

        if is_active:
            activity_status = "active"
        elif time_diff_minutes < 60:
            activity_status = "recently_inactive"
        else:
            activity_status = "inactive"

        latest_time_str = datetime.fromtimestamp(latest_time).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        return {
            "status": "success",
            "latest_time": latest_time_str,
            "latest_time_unix": latest_time,
            "latest_file": latest_file,
            "is_active": is_active,
            "activity_status": activity_status,
            "time_diff_minutes": round(time_diff_minutes, 2),
            "activity_threshold_minutes": threshold_minutes,
            "file_count": file_count,
        }

    except PermissionError:
        return {
            "status": "error",
            "message": f"Permission denied accessing: {log_path}",
            "latest_time": None,
            "latest_file": None,
            "is_active": False,
            "activity_status": "permission_denied",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error scanning directory: {str(e)}",
            "latest_time": None,
            "latest_file": None,
            "is_active": False,
            "activity_status": "error",
        }


def check_all_log_paths() -> Dict[str, Any]:
    """
    檢查所有配置的 log 路徑

    Returns:
        包含所有路徑檢查結果的 dict
    """
    if not settings.LOG_MONITOR_ENABLED:
        return {
            "status": "disabled",
            "message": "Log monitoring is disabled",
            "paths": [],
        }

    log_paths = settings.LOG_MONITOR_PATHS
    if not log_paths:
        return {
            "status": "error",
            "message": "No LOG_MONITOR_PATHS configured",
            "paths": [],
        }

    results = []
    all_active = True

    for log_path in log_paths:
        log_path = log_path.strip()
        if not log_path:
            continue

        info = get_latest_log_file_info(log_path)
        info["path"] = log_path
        results.append(info)

        if not info.get("is_active", False):
            all_active = False

    overall_status = "success" if all_active else "partial"

    return {
        "status": overall_status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "monitoring_enabled": settings.LOG_MONITOR_ENABLED,
        "activity_threshold_minutes": settings.LOG_ACTIVITY_THRESHOLD_MINUTES,
        "total_paths": len(results),
        "active_paths": sum(1 for r in results if r.get("is_active", False)),
        "paths": results,
    }


def get_specific_log_status(path_index: int) -> Dict[str, Any]:
    """
    取得特定日誌路徑的詳細狀態

    Args:
        path_index: 日誌路徑的索引 (0-based)

    Returns:
        該路徑的詳細狀況
    """
    log_paths = settings.LOG_MONITOR_PATHS

    if path_index < 0 or path_index >= len(log_paths):
        return {
            "status": "error",
            "message": f"Invalid path index. Available paths: {len(log_paths)}",
        }

    log_path = log_paths[path_index].strip()
    info = get_latest_log_file_info(log_path)
    info["path"] = log_path
    info["path_index"] = path_index

    return info
