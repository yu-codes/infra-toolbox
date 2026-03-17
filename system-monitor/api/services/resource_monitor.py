"""
主機與容器資源監控服務

包含 Prometheus 指標解析和 CPU 採樣任務
"""

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Union

import httpx

from core.config import settings


# === Prometheus 指標解析工具 ===


def _parse_prometheus_label_string(label_str: str) -> Dict[str, str]:
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

                labels = _parse_prometheus_label_string(label_str)
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


def _get_cpu_core_count(cpu_metrics: List[Dict[str, Any]]) -> int:
    """從 node_cpu_seconds_total metrics 計算 CPU 核心數"""
    cpu_ids = set()
    for m in cpu_metrics:
        labels = m.get("labels", {})
        cpu_id = labels.get("cpu")
        if cpu_id is not None and cpu_id.lower() != "total":
            cpu_ids.add(cpu_id)
    return len(cpu_ids)


def _calculate_cpu_usage_from_delta(
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


def _filter_valid_filesystems(
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
    valid_size_metrics = _filter_valid_filesystems(fs_size_metrics)
    valid_avail_metrics = _filter_valid_filesystems(fs_avail_metrics)

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


def _parse_iso8601_timestamp(ts_str: str) -> Optional[float]:
    """解析 ISO8601 格式的 timestamp 為 Unix timestamp (秒)"""
    from datetime import datetime

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


# === 全局變數與快取 ===


# 全局變數：存儲宿主機資訊 (用於容器沒有限制時的計算)
_host_metrics_cache: Dict[str, Any] = {}


def get_host_metrics_cache() -> Dict[str, Any]:
    """取得宿主機 metrics 快取"""
    return _host_metrics_cache


def update_host_metrics_cache(data: Dict[str, Any]) -> None:
    """更新宿主機 metrics 快取"""
    global _host_metrics_cache
    _host_metrics_cache = data


# === CPU Metrics 檔案操作 ===


def load_cpu_metrics_file() -> Dict[str, Any]:
    """讀取 CPU metrics 檔案"""
    cpu_file = settings.CPU_METRICS_FILE
    if cpu_file.exists():
        try:
            with open(cpu_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_cpu_metrics_file(data: Dict[str, Any]) -> None:
    """儲存 CPU metrics 檔案"""
    try:
        with open(settings.CPU_METRICS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving CPU metrics file: {e}")


def load_container_cpu_metrics_file() -> Dict[str, Any]:
    """讀取容器 CPU metrics 檔案"""
    container_file = settings.CONTAINER_CPU_METRICS_FILE
    if container_file.exists():
        try:
            with open(container_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_container_cpu_metrics_file(data: Dict[str, Any]) -> None:
    """儲存容器 CPU metrics 檔案"""
    try:
        with open(settings.CONTAINER_CPU_METRICS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving container CPU metrics file: {e}")


# === 資料收集函數 ===


async def get_node_exporter_metrics() -> Dict[str, Any]:
    """從 node_exporter 取得宿主機指標"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{settings.NODE_EXPORTER_URL}/metrics")
        response.raise_for_status()
        return parse_prometheus_metrics(response.text)


async def get_cadvisor_metrics() -> Dict[str, Any]:
    """從 cAdvisor 取得容器指標 (使用 API v1.3)"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{settings.CADVISOR_URL}/api/v1.3/docker")
        response.raise_for_status()
        return response.json()


async def _collect_host_cpu_metrics() -> Dict[str, Any]:
    """收集宿主機 CPU 指標"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.NODE_EXPORTER_URL}/metrics")
            response.raise_for_status()
            metrics = parse_prometheus_metrics(response.text)

            cpu_metrics = metrics.get("node_cpu_seconds_total", [])
            cpu_count = _get_cpu_core_count(cpu_metrics)

            # 同時收集 RAM 和 Storage 資訊供容器計算使用
            mem_total = metrics.get("node_memory_MemTotal_bytes", 0)
            mem_available = metrics.get("node_memory_MemAvailable_bytes", 0)

            fs_size_metrics = metrics.get("node_filesystem_size_bytes", [])
            fs_avail_metrics = metrics.get("node_filesystem_avail_bytes", [])
            storage_info = select_primary_storage(fs_size_metrics, fs_avail_metrics)

            # 更新宿主機快取
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

            return {
                "cpu_metrics": cpu_metrics,
                "cpu_count": cpu_count,
                "timestamp": time.time(),
            }
    except Exception as e:
        print(f"Error collecting host CPU metrics: {e}")
        return {}


async def _collect_container_cpu_metrics() -> Dict[str, Any]:
    """收集容器 CPU 指標"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.CADVISOR_URL}/api/v1.3/docker")
            response.raise_for_status()
            cadvisor_data = response.json()

            container_cpu_data = {}
            for container_path, container_info in cadvisor_data.items():
                if container_path == "/":
                    continue

                aliases = container_info.get("aliases", [])
                container_name = (
                    aliases[0] if aliases else container_path.split("/")[-1]
                )
                container_id = container_info.get("id", "")[:12]

                stats = container_info.get("stats", [])
                if stats:
                    latest_stats = stats[-1]
                    cpu_total = (
                        latest_stats.get("cpu", {}).get("usage", {}).get("total", 0)
                    )
                    timestamp = _parse_iso8601_timestamp(
                        latest_stats.get("timestamp", "")
                    )

                    container_cpu_data[container_id] = {
                        "name": container_name,
                        "cpu_total_ns": cpu_total,
                        "timestamp": timestamp or time.time(),
                    }

            return {
                "containers": container_cpu_data,
                "timestamp": time.time(),
            }
    except Exception as e:
        print(f"Error collecting container CPU metrics: {e}")
        return {}


# === CPU 定時採樣任務 ===


async def cpu_sample_task():
    """CPU 定時採樣任務"""
    interval_seconds = settings.CPU_SAMPLE_INTERVAL_MINUTES * 60

    print(
        f"CPU sampling task started. Interval: {settings.CPU_SAMPLE_INTERVAL_MINUTES} minute(s)"
    )

    while True:
        try:
            # 收集宿主機 CPU
            current_host_cpu = await _collect_host_cpu_metrics()
            if current_host_cpu:
                cpu_data = load_cpu_metrics_file()
                previous_data = cpu_data.get("current", {})

                # 計算 CPU 使用率
                cpu_usage = None
                if previous_data.get("cpu_metrics") and previous_data.get("timestamp"):
                    time_delta = (
                        current_host_cpu["timestamp"] - previous_data["timestamp"]
                    )
                    cpu_usage = _calculate_cpu_usage_from_delta(
                        current_host_cpu["cpu_metrics"],
                        previous_data["cpu_metrics"],
                        time_delta,
                    )

                # 儲存資料
                cpu_data = {
                    "previous": previous_data,
                    "current": current_host_cpu,
                    "calculated_usage": {
                        "usage_percent": cpu_usage,
                        "cpu_count": current_host_cpu.get("cpu_count", 0),
                        "sample_interval_minutes": settings.CPU_SAMPLE_INTERVAL_MINUTES,
                        "calculated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "time_delta_seconds": (
                            (
                                current_host_cpu["timestamp"]
                                - previous_data.get(
                                    "timestamp", current_host_cpu["timestamp"]
                                )
                            )
                            if previous_data.get("timestamp")
                            else 0
                        ),
                    },
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                _save_cpu_metrics_file(cpu_data)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Host CPU sampled: {cpu_usage}%"
                )

            # 收集容器 CPU
            current_container_cpu = await _collect_container_cpu_metrics()
            if current_container_cpu:
                container_cpu_data = load_container_cpu_metrics_file()
                previous_containers = container_cpu_data.get("current", {}).get(
                    "containers", {}
                )

                # 計算各容器 CPU 使用率
                calculated_containers = {}
                for container_id, current_info in current_container_cpu.get(
                    "containers", {}
                ).items():
                    previous_info = previous_containers.get(container_id, {})

                    cpu_usage = 0.0
                    if previous_info.get(
                        "cpu_total_ns"
                    ) is not None and previous_info.get("timestamp"):
                        cpu_delta_ns = (
                            current_info["cpu_total_ns"] - previous_info["cpu_total_ns"]
                        )
                        time_delta_seconds = (
                            current_info["timestamp"] - previous_info["timestamp"]
                        )

                        if time_delta_seconds > 0:
                            time_delta_ns = time_delta_seconds * 1e9
                            cpu_usage = round((cpu_delta_ns / time_delta_ns) * 100, 2)
                            cpu_usage = max(0, cpu_usage)

                    calculated_containers[container_id] = {
                        "name": current_info["name"],
                        "cpu_usage_percent": cpu_usage,
                    }

                # 儲存資料
                container_cpu_data = {
                    "previous": container_cpu_data.get("current", {}),
                    "current": current_container_cpu,
                    "calculated_usage": calculated_containers,
                    "sample_interval_minutes": settings.CPU_SAMPLE_INTERVAL_MINUTES,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                _save_container_cpu_metrics_file(container_cpu_data)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Container CPU sampled: {len(calculated_containers)} containers"
                )

        except Exception as e:
            print(f"Error in CPU sample task: {e}")

        await asyncio.sleep(interval_seconds)
