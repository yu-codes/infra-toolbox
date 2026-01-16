"""
Resource Monitoring API
從 node_exporter 和 cAdvisor 取得系統與容器監控指標
以及監控系統日誌檔案以判斷服務運作狀態
"""

import asyncio
import json
import os
import re
import threading
import time
import platform
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# === 配置 ===
NODE_EXPORTER_URL = os.getenv("NODE_EXPORTER_URL", "http://node_exporter:9100")
CADVISOR_URL = os.getenv("CADVISOR_URL", "http://cadvisor:8080")


# 自動檢測作業系統並設定預設日誌路徑
def _get_default_log_paths() -> List[str]:
    """根據作業系統自動檢測日誌路徑"""
    system = platform.system()
    paths = []

    if system == "Linux":
        # Linux: 優先檢查 /var/log/docker, /var/log, /app/data
        candidates = ["/var/log/docker", "/var/log", "/app/data"]
    elif system == "Darwin":
        # macOS: 檢查系統日誌和應用日誌
        candidates = [
            "/var/log",
            "/var/log/system.log",
            f"{Path.home()}/Library/Logs",
            "/app/data",
        ]
    elif system == "Windows":
        # Windows: 檢查 Windows 事件日誌目錄或應用資料
        candidates = [
            "C:\\logs",
            "C:\\ProgramData\\logs",
            f"{os.environ.get('APPDATA')}\\logs",
            "/app/data",
        ]
    else:
        # 其他系統
        candidates = ["/app/data"]

    # 檢查哪些路徑實際存在
    for path in candidates:
        path_obj = Path(path)
        if path_obj.exists():
            paths.append(str(path))

    # 如果沒有找到任何存在的路徑，使用 /app/data 作為後備（容器環境）
    if not paths and Path("/app/data").exists():
        paths.append("/app/data")

    return paths


# Log 監控配置
_configured_paths = (
    os.getenv("LOG_MONITOR_PATHS", "").split(";")
    if os.getenv("LOG_MONITOR_PATHS")
    else []
)
LOG_MONITOR_PATHS = [
    p.strip() for p in _configured_paths if p.strip()
] or _get_default_log_paths()
LOG_MONITOR_ENABLED = os.getenv("LOG_MONITOR_ENABLED", "true").lower() == "true"
# 活躍閾值：檔案在此時間內修改則視為活躍（分鐘）
LOG_ACTIVITY_THRESHOLD_MINUTES = int(os.getenv("LOG_ACTIVITY_THRESHOLD_MINUTES", "5"))

# 啟動時印出設定
print(f"[INIT] OS: {platform.system()}")
print(f"[INIT] Log Monitor Enabled: {LOG_MONITOR_ENABLED}")
print(f"[INIT] Log Monitor Paths: {LOG_MONITOR_PATHS}")

# CPU 使用率計算間隔 (分鐘)
CPU_SAMPLE_INTERVAL_MINUTES = int(os.getenv("CPU_SAMPLE_INTERVAL_MINUTES", "1"))

# 資料儲存檔案路徑
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
CPU_METRICS_FILE = DATA_DIR / "cpu_metrics.json"
CONTAINER_CPU_METRICS_FILE = DATA_DIR / "container_cpu_metrics.json"

# 確保資料目錄存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 全局變數：存儲宿主機資訊 (用於容器沒有限制時的計算)
_host_metrics_cache: Dict[str, Any] = {}


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


# === CPU 定時採樣相關函數 ===


def load_cpu_metrics_file() -> Dict[str, Any]:
    """讀取 CPU metrics 檔案"""
    if CPU_METRICS_FILE.exists():
        try:
            with open(CPU_METRICS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_cpu_metrics_file(data: Dict[str, Any]) -> None:
    """儲存 CPU metrics 檔案"""
    try:
        with open(CPU_METRICS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving CPU metrics file: {e}")


def load_container_cpu_metrics_file() -> Dict[str, Any]:
    """讀取容器 CPU metrics 檔案"""
    if CONTAINER_CPU_METRICS_FILE.exists():
        try:
            with open(CONTAINER_CPU_METRICS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_container_cpu_metrics_file(data: Dict[str, Any]) -> None:
    """儲存容器 CPU metrics 檔案"""
    try:
        with open(CONTAINER_CPU_METRICS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving container CPU metrics file: {e}")


async def collect_host_cpu_metrics() -> Dict[str, Any]:
    """收集宿主機 CPU 指標"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{NODE_EXPORTER_URL}/metrics")
            response.raise_for_status()
            metrics = parse_prometheus_metrics(response.text)

            cpu_metrics = metrics.get("node_cpu_seconds_total", [])
            cpu_count = get_cpu_core_count(cpu_metrics)

            # 同時收集 RAM 和 Storage 資訊供容器計算使用
            mem_total = metrics.get("node_memory_MemTotal_bytes", 0)
            mem_available = metrics.get("node_memory_MemAvailable_bytes", 0)

            fs_size_metrics = metrics.get("node_filesystem_size_bytes", [])
            fs_avail_metrics = metrics.get("node_filesystem_avail_bytes", [])
            storage_info = select_primary_storage(fs_size_metrics, fs_avail_metrics)

            # 更新宿主機快取
            global _host_metrics_cache
            _host_metrics_cache = {
                "mem_total_bytes": mem_total,
                "mem_available_bytes": mem_available,
                "storage_total_bytes": storage_info["total_bytes"],
                "storage_used_bytes": storage_info["used_bytes"],
                "storage_available_bytes": storage_info["available_bytes"],
                "timestamp": time.time(),
            }

            return {
                "cpu_metrics": cpu_metrics,
                "cpu_count": cpu_count,
                "timestamp": time.time(),
            }
    except Exception as e:
        print(f"Error collecting host CPU metrics: {e}")
        return {}


async def collect_container_cpu_metrics() -> Dict[str, Any]:
    """收集容器 CPU 指標"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{CADVISOR_URL}/api/v1.3/docker")
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
                    timestamp = parse_iso8601_timestamp(
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


async def cpu_sample_task():
    """CPU 定時採樣任務"""
    interval_seconds = CPU_SAMPLE_INTERVAL_MINUTES * 60

    print(
        f"CPU sampling task started. Interval: {CPU_SAMPLE_INTERVAL_MINUTES} minute(s)"
    )

    while True:
        try:
            # 收集宿主機 CPU
            current_host_cpu = await collect_host_cpu_metrics()
            if current_host_cpu:
                cpu_data = load_cpu_metrics_file()
                previous_data = cpu_data.get("current", {})

                # 計算 CPU 使用率
                cpu_usage = None
                if previous_data.get("cpu_metrics") and previous_data.get("timestamp"):
                    time_delta = (
                        current_host_cpu["timestamp"] - previous_data["timestamp"]
                    )
                    cpu_usage = calculate_cpu_usage_from_delta(
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
                        "sample_interval_minutes": CPU_SAMPLE_INTERVAL_MINUTES,
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
                save_cpu_metrics_file(cpu_data)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Host CPU sampled: {cpu_usage}%"
                )

            # 收集容器 CPU
            current_container_cpu = await collect_container_cpu_metrics()
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
                    "sample_interval_minutes": CPU_SAMPLE_INTERVAL_MINUTES,
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                save_container_cpu_metrics_file(container_cpu_data)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Container CPU sampled: {len(calculated_containers)} containers"
                )

        except Exception as e:
            print(f"Error in CPU sample task: {e}")

        await asyncio.sleep(interval_seconds)


# === Log 監控函數 ===


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

        # 如果是目錄則掃描所有檔案，如果是檔案則直接檢查
        if path.is_dir():
            entries = list(path.iterdir())
            if not entries:
                return {
                    "status": "error",
                    "message": "Directory is empty",
                    "latest_time": None,
                    "latest_file": None,
                    "is_active": False,
                    "activity_status": "empty_directory",
                    "file_count": 0,
                }

            for entry in entries:
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

        # 判斷活躍狀態：最後修改時間是否在閾值內
        current_time = time.time()
        time_diff_minutes = (current_time - latest_time) / 60
        threshold_minutes = LOG_ACTIVITY_THRESHOLD_MINUTES
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
    if not LOG_MONITOR_ENABLED:
        return {
            "status": "disabled",
            "message": "Log monitoring is disabled",
            "paths": [],
        }

    if not LOG_MONITOR_PATHS:
        return {
            "status": "error",
            "message": "No LOG_MONITOR_PATHS configured",
            "paths": [],
        }

    results = []
    all_active = True

    for log_path in LOG_MONITOR_PATHS:
        log_path = log_path.strip()
        if not log_path:
            continue

        info = get_latest_log_file_info(log_path)
        info["path"] = log_path
        results.append(info)

        # 如果任何路徑不活躍，則整體狀態為不完全活躍
        if not info.get("is_active", False):
            all_active = False

    overall_status = "success" if all_active else "partial"

    return {
        "status": overall_status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "monitoring_enabled": LOG_MONITOR_ENABLED,
        "activity_threshold_minutes": LOG_ACTIVITY_THRESHOLD_MINUTES,
        "total_paths": len(results),
        "active_paths": sum(1 for r in results if r.get("is_active", False)),
        "paths": results,
    }


# === FastAPI Lifespan ===


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時開始 CPU 採樣任務
    task = asyncio.create_task(cpu_sample_task())
    print("Resource Monitoring API started with CPU sampling task")
    print(f"OS: {platform.system()}")
    print(f"Log Monitor Enabled: {LOG_MONITOR_ENABLED}")
    print(f"Log Monitor Paths: {LOG_MONITOR_PATHS}")
    yield
    # 關閉時取消任務
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("CPU sampling task cancelled")


app = FastAPI(
    title="Resource Monitoring API",
    description="系統與容器資源監控 API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            "/cpu-config": "CPU sampling configuration",
            "/log-status": "Log file monitoring status",
        },
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}


@app.get("/cpu-config")
async def get_cpu_config():
    """取得 CPU 採樣配置"""
    cpu_data = load_cpu_metrics_file()
    container_cpu_data = load_container_cpu_metrics_file()

    return {
        "cpu_sample_interval_minutes": CPU_SAMPLE_INTERVAL_MINUTES,
        "host_cpu": {
            "last_updated": cpu_data.get("last_updated"),
            "has_data": bool(cpu_data.get("calculated_usage")),
        },
        "container_cpu": {
            "last_updated": container_cpu_data.get("last_updated"),
            "container_count": len(container_cpu_data.get("calculated_usage", {})),
        },
    }


@app.get("/system-metrics")
async def get_system_metrics() -> dict:
    """
    取得系統監控指標

    從 node_exporter 取得宿主機 CPU、RAM、Storage 使用量
    從 cAdvisor 取得容器 CPU、Memory、Storage 使用量

    CPU 使用率從定時採樣計算結果讀取 (n 分鐘區間內的使用率)
    容器 RAM 若無限制，使用宿主機總 RAM 計算比例
    容器 Storage 若無限制，使用宿主機總 Storage 計算比例
    """
    result = {
        "status": "success",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_sample_interval_minutes": CPU_SAMPLE_INTERVAL_MINUTES,
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
            cpu_usage_note = f"Calculated from {CPU_SAMPLE_INTERVAL_MINUTES} minute(s) interval (actual: {time_delta_seconds:.1f}s)"
        else:
            cpu_usage_note = f"Waiting for second sample. Interval: {CPU_SAMPLE_INTERVAL_MINUTES} minute(s)"

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
        global _host_metrics_cache
        _host_metrics_cache = {
            "mem_total_bytes": mem_total,
            "mem_available_bytes": mem_available,
            "storage_total_bytes": storage_info["total_bytes"],
            "storage_used_bytes": storage_info["used_bytes"],
            "storage_available_bytes": storage_info["available_bytes"],
            "timestamp": time.time(),
        }

        result["server_metrics"] = {
            "cpu": {
                "usage_percent": cpu_usage_percent,
                "cpu_count": cpu_count,
                "usage_note": cpu_usage_note,
                "sample_interval_minutes": CPU_SAMPLE_INTERVAL_MINUTES,
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
        host_mem_total = _host_metrics_cache.get("mem_total_bytes", 0)
        host_storage_total = _host_metrics_cache.get("storage_total_bytes", 0)
        host_storage_used = _host_metrics_cache.get("storage_used_bytes", 0)

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
            "cpu_sample_interval_minutes": CPU_SAMPLE_INTERVAL_MINUTES,
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


@app.get("/log-status")
async def get_log_status() -> Dict[str, Any]:
    """
    監控日誌檔案狀態

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


@app.get("/log-status/{path_index}")
async def get_specific_log_status(path_index: int) -> Dict[str, Any]:
    """
    取得特定日誌路徑的詳細狀態

    Args:
        path_index: 日誌路徑在 LOG_MONITOR_PATHS 中的索引 (0-based)

    Returns:
        該路徑的詳細狀況，包括最後修改時間、檔案名稱等
    """
    if not LOG_MONITOR_ENABLED:
        raise HTTPException(status_code=503, detail="Log monitoring is disabled")

    if not LOG_MONITOR_PATHS or path_index < 0 or path_index >= len(LOG_MONITOR_PATHS):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid path index. Available paths: {len(LOG_MONITOR_PATHS)}",
        )

    log_path = LOG_MONITOR_PATHS[path_index].strip()
    info = get_latest_log_file_info(log_path)
    info["path"] = log_path
    info["path_index"] = path_index

    return info


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
