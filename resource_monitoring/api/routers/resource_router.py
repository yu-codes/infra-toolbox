"""
資源監控路由

提供系統和容器資源監控的 API 端點
"""

import time
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends

from core.config import settings
from core.jwt_auth import verify_jwt_token
from services.resource_monitor import (
    load_cpu_metrics_file,
    load_container_cpu_metrics_file,
    get_node_exporter_metrics,
    get_cadvisor_metrics,
    get_host_metrics_cache,
    update_host_metrics_cache,
    select_primary_storage,
)

router = APIRouter(tags=["Resource Monitoring"])


@router.get("/cpu-config")
async def get_cpu_config(token: dict = Depends(verify_jwt_token)):
    """取得 CPU 採樣配置 (需要 JWT 認證，若啟用)"""
    cpu_data = load_cpu_metrics_file()
    container_cpu_data = load_container_cpu_metrics_file()

    return {
        "cpu_sample_interval_minutes": settings.CPU_SAMPLE_INTERVAL_MINUTES,
        "host_cpu": {
            "last_updated": cpu_data.get("last_updated"),
            "has_data": bool(cpu_data.get("calculated_usage")),
        },
        "container_cpu": {
            "last_updated": container_cpu_data.get("last_updated"),
            "container_count": len(container_cpu_data.get("calculated_usage", {})),
        },
    }


@router.get("/system-metrics")
async def get_system_metrics(token: dict = Depends(verify_jwt_token)) -> dict:
    """
    取得系統監控指標 (需要 JWT 認證，若啟用)

    從 node_exporter 取得宿主機 CPU、RAM、Storage 使用量
    從 cAdvisor 取得容器 CPU、Memory、Storage 使用量

    CPU 使用率從定時採樣計算結果讀取 (n 分鐘區間內的使用率)
    容器 RAM 若無限制，使用宿主機總 RAM 計算比例
    容器 Storage 若無限制，使用宿主機總 Storage 計算比例
    """
    result = {
        "status": "success",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_sample_interval_minutes": settings.CPU_SAMPLE_INTERVAL_MINUTES,
        "server_metrics": None,
        "container_metrics": None,
    }

    # === Server Metrics (from node_exporter) ===
    try:
        metrics = await get_node_exporter_metrics()

        # CPU: 從定時採樣檔案讀取
        cpu_data = load_cpu_metrics_file()
        calculated_cpu = cpu_data.get("calculated_usage", {})

        cpu_usage_percent = calculated_cpu.get("usage_percent")
        cpu_count = calculated_cpu.get("cpu_count", 0)
        time_delta_seconds = calculated_cpu.get("time_delta_seconds", 0)

        if cpu_usage_percent is not None:
            cpu_usage_note = f"Calculated from {settings.CPU_SAMPLE_INTERVAL_MINUTES} minute(s) interval (actual: {time_delta_seconds:.1f}s)"
        else:
            cpu_usage_note = f"Waiting for second sample. Interval: {settings.CPU_SAMPLE_INTERVAL_MINUTES} minute(s)"

        # RAM 計算
        mem_total = metrics.get("node_memory_MemTotal_bytes", 0)
        mem_available = metrics.get("node_memory_MemAvailable_bytes", 0)
        mem_used = mem_total - mem_available
        ram_total_gb = round(mem_total / (1024**3), 2)
        ram_used_gb = round(mem_used / (1024**3), 2)
        ram_available_gb = round(mem_available / (1024**3), 2)
        ram_percent = round((mem_used / mem_total) * 100, 2) if mem_total > 0 else 0

        # Storage 計算
        fs_size_metrics = metrics.get("node_filesystem_size_bytes", [])
        fs_avail_metrics = metrics.get("node_filesystem_avail_bytes", [])

        storage_info = select_primary_storage(fs_size_metrics, fs_avail_metrics)

        storage_total_gb = round(storage_info["total_bytes"] / (1024**3), 2)
        storage_used_gb = round(storage_info["used_bytes"] / (1024**3), 2)
        storage_free_gb = round(storage_info["available_bytes"] / (1024**3), 2)
        storage_percent = (
            round((storage_info["used_bytes"] / storage_info["total_bytes"]) * 100, 2)
            if storage_info["total_bytes"] > 0
            else 0
        )

        # 更新宿主機快取 (供容器計算使用)
        update_host_metrics_cache(
            {
                "mem_total_bytes": mem_total,
                "mem_available_bytes": mem_available,
                "storage_total_bytes": storage_info["total_bytes"],
                "storage_used_bytes": storage_info["used_bytes"],
                "storage_available_bytes": storage_info["available_bytes"],
                "timestamp": time.time(),
            }
        )

        result["server_metrics"] = {
            "cpu": {
                "usage_percent": cpu_usage_percent,
                "cpu_count": cpu_count,
                "usage_note": cpu_usage_note,
                "sample_interval_minutes": settings.CPU_SAMPLE_INTERVAL_MINUTES,
                "last_calculated": calculated_cpu.get("calculated_at"),
            },
            "ram": {
                "total_gb": ram_total_gb,
                "used_gb": ram_used_gb,
                "available_gb": ram_available_gb,
                "usage_percent": ram_percent,
            },
            "storage": {
                "total_gb": storage_total_gb,
                "used_gb": storage_used_gb,
                "free_gb": storage_free_gb,
                "usage_percent": storage_percent,
                "mountpoint": storage_info["mountpoint"],
                "fstype": storage_info["fstype"],
                "selection_note": storage_info["note"],
            },
            "source": "node_exporter",
        }
    except (httpx.RequestError, httpx.HTTPError):
        result["server_metrics"] = {
            "error": "node_exporter not available. Please start docker-compose up -d"
        }
    except Exception as e:
        result["server_metrics"] = {"error": f"Failed to get server metrics: {str(e)}"}

    # === Container Metrics (from cAdvisor) ===
    try:
        cadvisor_data = await get_cadvisor_metrics()

        # 讀取定時採樣的容器 CPU 資料
        container_cpu_data = load_container_cpu_metrics_file()
        calculated_container_cpu = container_cpu_data.get("calculated_usage", {})

        # 取得宿主機資訊 (用於計算無限制容器的比例)
        host_cache = get_host_metrics_cache()
        host_mem_total = host_cache.get("mem_total_bytes", 0)
        host_storage_total = host_cache.get("storage_total_bytes", 0)

        container_metrics = []

        for container_path, container_info in cadvisor_data.items():
            if container_path == "/":
                continue

            try:
                aliases = container_info.get("aliases", [])
                container_name = (
                    aliases[0] if aliases else container_path.split("/")[-1]
                )
                container_id = container_info.get("id", "")[:12]

                stats = container_info.get("stats", [])
                if not stats:
                    continue
                latest_stats = stats[-1]

                # CPU: 從定時採樣結果讀取
                container_cpu_info = calculated_container_cpu.get(container_id, {})
                cpu_usage_percent = container_cpu_info.get("cpu_usage_percent", 0.0)

                # Memory 計算 - 若無限制則使用宿主機總 RAM
                mem_usage = latest_stats.get("memory", {}).get("usage", 0)
                mem_limit = (
                    container_info.get("spec", {}).get("memory", {}).get("limit", 0)
                )

                # 檢查是否有有效的 memory limit
                has_mem_limit = True
                if mem_limit == 0 or mem_limit > 1e18:
                    mem_limit = latest_stats.get("memory", {}).get(
                        "hierarchical_memory_limit", 0
                    )

                # 如果仍然沒有限制或限制過大，使用宿主機總 RAM
                if mem_limit == 0 or mem_limit > 1e18:
                    has_mem_limit = False
                    mem_limit = host_mem_total if host_mem_total > 0 else mem_usage

                mem_usage_mb = round(mem_usage / (1024**2), 2)
                mem_limit_mb = round(mem_limit / (1024**2), 2) if mem_limit > 0 else 0
                mem_percent = (
                    round((mem_usage / mem_limit) * 100, 2) if mem_limit > 0 else 0
                )

                # Storage 計算 - 若無限制則使用宿主機總 Storage
                fs_stats = latest_stats.get("filesystem", [])
                container_storage_used = 0
                container_storage_limit = 0
                has_storage_limit = False

                if fs_stats:
                    # 合計所有 filesystem 使用量
                    for fs in fs_stats:
                        container_storage_used += fs.get("usage", 0)
                        fs_limit = fs.get("limit", 0)
                        if fs_limit > 0 and fs_limit < 1e18:
                            container_storage_limit += fs_limit
                            has_storage_limit = True

                # 如果沒有 storage limit，使用宿主機 storage
                if not has_storage_limit or container_storage_limit == 0:
                    container_storage_limit = (
                        host_storage_total
                        if host_storage_total > 0
                        else container_storage_used
                    )

                storage_usage_mb = round(container_storage_used / (1024**2), 2)
                storage_limit_mb = (
                    round(container_storage_limit / (1024**2), 2)
                    if container_storage_limit > 0
                    else 0
                )
                storage_percent = (
                    round((container_storage_used / container_storage_limit) * 100, 2)
                    if container_storage_limit > 0
                    else 0
                )

                container_metrics.append(
                    {
                        "name": container_name,
                        "id": container_id,
                        "cpu": {
                            "usage_percent": cpu_usage_percent,
                            "source": "scheduled_sample",
                        },
                        "memory": {
                            "usage_mb": mem_usage_mb,
                            "limit_mb": mem_limit_mb,
                            "usage_percent": mem_percent,
                            "has_limit": has_mem_limit,
                            "limit_source": (
                                "container" if has_mem_limit else "host_total"
                            ),
                        },
                        "storage": {
                            "usage_mb": storage_usage_mb,
                            "limit_mb": storage_limit_mb,
                            "usage_percent": storage_percent,
                            "has_limit": has_storage_limit,
                            "limit_source": (
                                "container" if has_storage_limit else "host_total"
                            ),
                        },
                    }
                )
            except Exception as e:
                container_metrics.append({"name": container_path, "error": str(e)})

        result["container_metrics"] = {
            "containers": container_metrics,
            "source": "cadvisor",
            "cpu_sample_interval_minutes": settings.CPU_SAMPLE_INTERVAL_MINUTES,
            "cpu_last_updated": container_cpu_data.get("last_updated"),
        }
    except (httpx.RequestError, httpx.HTTPError):
        result["container_metrics"] = {
            "error": "cadvisor not available. Please start docker-compose up -d"
        }
    except Exception as e:
        result["container_metrics"] = {
            "error": f"Failed to get container metrics: {str(e)}"
        }

    if (
        result["server_metrics"]
        and "error" in result["server_metrics"]
        and result["container_metrics"]
        and "error" in result["container_metrics"]
    ):
        result["status"] = "error"
        result["message"] = (
            "Metrics services not available. Please run: docker-compose up -d"
        )

    return result
