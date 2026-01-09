"""
Resource Monitoring API
從 node_exporter 和 cAdvisor 取得系統與容器監控指標
"""

import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Resource Monitoring API",
    description="系統與容器資源監控 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 配置 ===
NODE_EXPORTER_URL = os.getenv("NODE_EXPORTER_URL", "http://node_exporter:9100")
CADVISOR_URL = os.getenv("CADVISOR_URL", "http://cadvisor:8080")

# 用於存儲上一次的 CPU metrics，實現 delta 計算
_previous_cpu_metrics: Dict[str, Any] = {}
_previous_cpu_timestamp: Optional[float] = None


def parse_prometheus_label_string(label_str: str) -> Dict[str, str]:
    """
    將 Prometheus label 字串解析為 dict

    範例輸入: 'cpu="0",mode="idle"'
    範例輸出: {'cpu': '0', 'mode': 'idle'}
    """
    labels = {}
    if not label_str:
        return labels

    pattern = r'(\w+)=["\']([^"\']*)["\']'
    matches = re.findall(pattern, label_str)
    for key, value in matches:
        labels[key] = value

    return labels


def parse_prometheus_metrics(
    text: str,
) -> Dict[str, Union[float, List[Dict[str, Any]]]]:
    """
    解析 Prometheus 格式的 metrics 文字

    回傳格式：
    - 無 labels 的 metric: {metric_name: float_value}
    - 有 labels 的 metric: {metric_name: [{"labels": {dict}, "value": float}, ...]}
    """
    metrics: Dict[str, Any] = {}

    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("#") or not line:
            continue

        try:
            if "{" in line:
                brace_start = line.index("{")
                brace_end = line.rindex("}")

                name = line[:brace_start]
                label_str = line[brace_start + 1 : brace_end]
                value_str = line[brace_end + 1 :].strip()

                labels = parse_prometheus_label_string(label_str)
                value = float(value_str)

                if name not in metrics:
                    metrics[name] = []
                metrics[name].append({"labels": labels, "value": value})
            else:
                parts = line.split()
                if len(parts) >= 2:
                    metrics[parts[0]] = float(parts[1])
        except (ValueError, IndexError):
            continue

    return metrics


def get_cpu_core_count(cpu_metrics: List[Dict[str, Any]]) -> int:
    """從 node_cpu_seconds_total metrics 計算 CPU 核心數"""
    cpu_ids = set()
    for m in cpu_metrics:
        labels = m.get("labels", {})
        cpu_id = labels.get("cpu")
        if cpu_id is not None and cpu_id.lower() != "total":
            cpu_ids.add(cpu_id)
    return len(cpu_ids)


def calculate_cpu_usage_from_delta(
    current_metrics: List[Dict[str, Any]],
    previous_metrics: List[Dict[str, Any]],
    time_delta_seconds: float,
) -> Optional[float]:
    """
    基於兩次採樣的 delta 計算 CPU 使用率

    CPU 使用率 = (delta_total - delta_idle) / delta_total * 100
    """
    if not previous_metrics or time_delta_seconds <= 0:
        return None

    def sum_by_mode(metrics: List[Dict[str, Any]], mode: str) -> float:
        return sum(
            m["value"] for m in metrics if m.get("labels", {}).get("mode") == mode
        )

    def sum_all(metrics: List[Dict[str, Any]]) -> float:
        return sum(m["value"] for m in metrics)

    current_idle = sum_by_mode(current_metrics, "idle")
    previous_idle = sum_by_mode(previous_metrics, "idle")

    current_total = sum_all(current_metrics)
    previous_total = sum_all(previous_metrics)

    delta_idle = current_idle - previous_idle
    delta_total = current_total - previous_total

    if delta_total <= 0:
        return None

    usage_percent = ((delta_total - delta_idle) / delta_total) * 100
    return round(max(0, min(100, usage_percent)), 2)


def filter_valid_filesystems(
    fs_metrics: List[Dict[str, Any]],
    excluded_fstypes: Optional[List[str]] = None,
    excluded_mountpoints: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """過濾有效的 filesystem metrics"""
    default_excluded_fstypes = {
        "tmpfs",
        "overlay",
        "squashfs",
        "devtmpfs",
        "devfs",
        "nsfs",
        "cgroup",
        "cgroup2",
    }
    default_excluded_mountpoint_prefixes = ["/dev", "/sys", "/proc", "/run", "/snap"]

    if excluded_fstypes:
        default_excluded_fstypes.update(excluded_fstypes)
    if excluded_mountpoints:
        default_excluded_mountpoint_prefixes.extend(excluded_mountpoints)

    valid_metrics = []
    for m in fs_metrics:
        labels = m.get("labels", {})
        fstype = labels.get("fstype", "")
        mountpoint = labels.get("mountpoint", "")

        if fstype in default_excluded_fstypes:
            continue

        if any(
            mountpoint.startswith(prefix)
            for prefix in default_excluded_mountpoint_prefixes
        ):
            continue

        valid_metrics.append(m)

    return valid_metrics


def select_primary_storage(
    fs_size_metrics: List[Dict[str, Any]], fs_avail_metrics: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """選擇主要儲存空間並計算使用量"""
    valid_size_metrics = filter_valid_filesystems(fs_size_metrics)
    valid_avail_metrics = filter_valid_filesystems(fs_avail_metrics)

    if not valid_size_metrics:
        return {
            "total_bytes": 0,
            "available_bytes": 0,
            "used_bytes": 0,
            "mountpoint": "",
            "fstype": "",
            "note": "No valid filesystem found",
        }

    avail_lookup = {}
    for m in valid_avail_metrics:
        labels = m.get("labels", {})
        key = (labels.get("mountpoint", ""), labels.get("device", ""))
        avail_lookup[key] = m["value"]

    priority_mountpoints = ["/", "/rootfs"]
    selected = None
    selection_note = ""

    for target_mp in priority_mountpoints:
        for m in valid_size_metrics:
            labels = m.get("labels", {})
            if labels.get("mountpoint") == target_mp:
                selected = m
                selection_note = f"Selected root mountpoint: {target_mp}"
                break
        if selected:
            break

    if not selected:
        selected = max(valid_size_metrics, key=lambda x: x["value"])
        mp = selected.get("labels", {}).get("mountpoint", "unknown")
        selection_note = f"Selected largest filesystem at: {mp}"

    labels = selected.get("labels", {})
    mountpoint = labels.get("mountpoint", "")
    device = labels.get("device", "")
    fstype = labels.get("fstype", "")

    total_bytes = selected["value"]
    avail_bytes = avail_lookup.get((mountpoint, device), 0)
    used_bytes = total_bytes - avail_bytes

    return {
        "total_bytes": int(total_bytes),
        "available_bytes": int(avail_bytes),
        "used_bytes": int(used_bytes),
        "mountpoint": mountpoint,
        "fstype": fstype,
        "note": selection_note,
    }


def parse_iso8601_timestamp(ts_str: str) -> Optional[float]:
    """解析 ISO8601 格式的 timestamp 為 Unix timestamp (秒)"""
    if not ts_str:
        return None

    try:
        ts_str = ts_str.rstrip("Z")

        if "." in ts_str:
            main_part, frac_part = ts_str.split(".")
            frac_part = frac_part[:6].ljust(6, "0")
            ts_str = f"{main_part}.{frac_part}"
            dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")

        return dt.timestamp() - time.timezone
    except (ValueError, AttributeError):
        return None


def calculate_cadvisor_cpu_usage(
    stats: List[Dict[str, Any]], num_cores: int = 1
) -> float:
    """從 cAdvisor stats 計算容器 CPU 使用率"""
    if len(stats) < 2:
        return 0.0

    latest = stats[-1]
    previous = stats[-2]

    try:
        cpu_latest = latest.get("cpu", {}).get("usage", {}).get("total", 0)
        cpu_previous = previous.get("cpu", {}).get("usage", {}).get("total", 0)
        cpu_delta_ns = cpu_latest - cpu_previous

        ts_latest = parse_iso8601_timestamp(latest.get("timestamp", ""))
        ts_previous = parse_iso8601_timestamp(previous.get("timestamp", ""))

        if ts_latest is None or ts_previous is None:
            return 0.0

        time_delta_seconds = ts_latest - ts_previous
        if time_delta_seconds <= 0:
            return 0.0

        time_delta_ns = time_delta_seconds * 1e9

        usage_percent = (cpu_delta_ns / time_delta_ns) * 100

        return round(max(0, usage_percent), 2)
    except (KeyError, TypeError, ZeroDivisionError):
        return 0.0


async def get_node_exporter_metrics() -> Dict[str, Any]:
    """從 node_exporter 取得宿主機指標"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{NODE_EXPORTER_URL}/metrics")
        response.raise_for_status()
        return parse_prometheus_metrics(response.text)


async def get_cadvisor_metrics() -> Dict[str, Any]:
    """從 cAdvisor 取得容器指標 (使用 API v1.3)"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{CADVISOR_URL}/api/v1.3/docker")
        response.raise_for_status()
        return response.json()


@app.get("/")
async def root():
    """API 根路徑"""
    return {
        "service": "Resource Monitoring API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/system-metrics": "System and container metrics",
        },
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}


@app.get("/system-metrics")
async def get_system_metrics() -> dict:
    """
    取得系統監控指標

    從 node_exporter 取得宿主機 CPU、RAM、Storage 使用量
    從 cAdvisor 取得容器 CPU、Memory 使用量
    """
    global _previous_cpu_metrics, _previous_cpu_timestamp

    result = {
        "status": "success",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "server_metrics": None,
        "container_metrics": None,
    }

    # === Server Metrics (from node_exporter) ===
    try:
        metrics = await get_node_exporter_metrics()
        current_time = time.time()

        # CPU 計算
        cpu_metrics = metrics.get("node_cpu_seconds_total", [])
        cpu_count = get_cpu_core_count(cpu_metrics)

        cpu_usage_percent = None
        cpu_usage_note = None

        if _previous_cpu_metrics and _previous_cpu_timestamp:
            time_delta = current_time - _previous_cpu_timestamp
            cpu_usage_percent = calculate_cpu_usage_from_delta(
                cpu_metrics, _previous_cpu_metrics, time_delta
            )
            if cpu_usage_percent is not None:
                cpu_usage_note = f"Calculated from {time_delta:.1f}s delta"

        if cpu_usage_percent is None:
            cpu_usage_note = (
                "First sample collected. CPU usage requires two samples to calculate."
            )

        _previous_cpu_metrics = cpu_metrics
        _previous_cpu_timestamp = current_time

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

        result["server_metrics"] = {
            "cpu": {
                "usage_percent": cpu_usage_percent,
                "cpu_count": cpu_count,
                "usage_note": cpu_usage_note,
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
    except httpx.ConnectError:
        result["server_metrics"] = {
            "error": "node_exporter not available. Please start docker-compose up -d"
        }
    except Exception as e:
        result["server_metrics"] = {"error": f"Failed to get server metrics: {str(e)}"}

    # === Container Metrics (from cAdvisor) ===
    try:
        cadvisor_data = await get_cadvisor_metrics()
        container_metrics = []

        for container_path, container_info in cadvisor_data.items():
            if container_path == "/":
                continue

            try:
                aliases = container_info.get("aliases", [])
                container_name = (
                    aliases[0] if aliases else container_path.split("/")[-1]
                )

                stats = container_info.get("stats", [])
                if not stats:
                    continue
                latest_stats = stats[-1]

                cpu_usage_percent = calculate_cadvisor_cpu_usage(stats)

                mem_usage = latest_stats.get("memory", {}).get("usage", 0)
                mem_limit = (
                    container_info.get("spec", {}).get("memory", {}).get("limit", 0)
                )
                if mem_limit == 0 or mem_limit > 1e18:
                    mem_limit = latest_stats.get("memory", {}).get(
                        "hierarchical_memory_limit", 0
                    )

                mem_usage_mb = round(mem_usage / (1024**2), 2)
                mem_limit_mb = round(mem_limit / (1024**2), 2) if mem_limit > 0 else 0
                mem_percent = (
                    round((mem_usage / mem_limit) * 100, 2) if mem_limit > 0 else 0
                )

                container_metrics.append(
                    {
                        "name": container_name,
                        "id": container_info.get("id", "")[:12],
                        "cpu": {"usage_percent": cpu_usage_percent},
                        "memory": {
                            "usage_mb": mem_usage_mb,
                            "limit_mb": mem_limit_mb,
                            "usage_percent": mem_percent,
                        },
                    }
                )
            except Exception as e:
                container_metrics.append({"name": container_path, "error": str(e)})

        result["container_metrics"] = {
            "containers": container_metrics,
            "source": "cadvisor",
        }
    except httpx.ConnectError:
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
