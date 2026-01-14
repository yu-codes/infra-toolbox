# Resource Monitoring Service

基於 Docker 的系統與容器資源監控服務。

## 功能特性

| 功能 | 說明 |
|------|------|
| 宿主機監控 | CPU、RAM、Storage 使用率 (via node_exporter) |
| 容器監控 | CPU、Memory、Storage 使用率 (via cAdvisor) |
| REST API | FastAPI 提供 JSON 格式監控數據 |
| CPU 定時採樣 | 可配置的 n 分鐘區間 CPU 使用率計算 |

## 服務端口

| 服務 | 端口 | 說明 |
|------|------|------|
| node_exporter | 內部 9100 | 僅內部網路使用 |
| cAdvisor | 內部 8080 | 僅內部網路使用 |
| Monitoring API | 10003 | 對外提供 API |

## 架構說明

```
┌─────────────────────────────────────────────────────────────┐
│                     Monitoring API (10003)                   │
│                        FastAPI Server                        │
│              ┌─────────────────────────────┐                 │
│              │   CPU Sampling Scheduler    │                 │
│              │   (每 n 分鐘定時採樣)        │                 │
│              └─────────────────────────────┘                 │
└────────────────────────┬────────────────────┬───────────────┘
                         │                    │
            ┌────────────▼──────┐   ┌────────▼────────────┐
            │  node_exporter    │   │     cAdvisor        │
            │   (內部 9100)      │   │    (內部 8080)       │
            └────────┬──────────┘   └────────┬────────────┘
                     │                       │
            ┌────────▼──────────┐   ┌────────▼────────────┐
            │    Host System    │   │  Docker Containers  │
            │  (CPU/RAM/Disk)   │   │    (CPU/Memory)     │
            └───────────────────┘   └─────────────────────┘
```

---

## CPU 定時採樣機制

### 設計說明

由於 CPU 使用率的計算需要兩個時間點的數據進行差值運算，本服務實作了定時採樣機制：

1. **定時採樣**：服務啟動時自動開始，每隔 n 分鐘收集一次 CPU 數據
2. **使用率計算**：基於兩次採樣的差值計算該時間區間內的平均 CPU 使用率
3. **資料持久化**：採樣結果存儲在 JSON 檔案中，API 查詢時讀取計算結果

### 配置

| 環境變數 | 預設值 | 說明 |
|---------|--------|------|
| `CPU_SAMPLE_INTERVAL_MINUTES` | 1 | CPU 採樣間隔 (分鐘) |
| `DATA_DIR` | /app/data | 資料儲存目錄 |

### 資料檔案

```
data/
├── cpu_metrics.json           # 宿主機 CPU 採樣資料
└── container_cpu_metrics.json # 容器 CPU 採樣資料
```

---

## 容器資源計算邏輯

### Memory (RAM)

- **有限制**：使用容器設定的 memory limit 計算使用比例
- **無限制**：使用宿主機總 RAM 計算使用比例

```json
{
  "memory": {
    "usage_mb": 128.5,
    "limit_mb": 16384.0,
    "usage_percent": 0.78,
    "has_limit": false,
    "limit_source": "host_total"
  }
}
```

### Storage

- **有限制**：使用容器設定的 storage limit 計算使用比例
- **無限制**：使用宿主機總 Storage 計算使用比例

```json
{
  "storage": {
    "usage_mb": 50.0,
    "limit_mb": 512000.0,
    "usage_percent": 0.01,
    "has_limit": false,
    "limit_source": "host_total"
  }
}
```

---

## 快速開始

```bash
# 1. 建立網路 (首次)
docker network create infra-toolbox-network

# 2. (可選) 配置 CPU 採樣間隔
echo "CPU_SAMPLE_INTERVAL_MINUTES=5" > .env

# 3. 啟動服務
docker-compose up -d

# 4. 訪問 API
curl http://localhost:10003/system-metrics
```

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /` | API 資訊 |
| `GET /health` | 健康檢查 |
| `GET /cpu-config` | CPU 採樣配置與狀態 |
| `GET /system-metrics` | 系統與容器監控指標 |

## 回應範例

```json
{
  "status": "success",
  "timestamp": "2026-01-14 12:00:00",
  "cpu_sample_interval_minutes": 1,
  "server_metrics": {
    "cpu": {
      "usage_percent": 25.5,
      "cpu_count": 8,
      "usage_note": "Calculated from 1 minute(s) interval (actual: 60.0s)",
      "sample_interval_minutes": 1,
      "last_calculated": "2026-01-14 11:59:00"
    },
    "ram": {
      "total_gb": 16.0,
      "used_gb": 8.5,
      "available_gb": 7.5,
      "usage_percent": 53.1
    },
    "storage": {
      "total_gb": 500.0,
      "used_gb": 250.0,
      "free_gb": 250.0,
      "usage_percent": 50.0,
      "mountpoint": "/",
      "fstype": "ext4"
    }
  },
  "container_metrics": {
    "containers": [
      {
        "name": "nginx",
        "id": "abc123def456",
        "cpu": {
          "usage_percent": 1.2,
          "source": "scheduled_sample"
        },
        "memory": {
          "usage_mb": 128.5,
          "limit_mb": 512.0,
          "usage_percent": 25.1,
          "has_limit": true,
          "limit_source": "container"
        },
        "storage": {
          "usage_mb": 50.0,
          "limit_mb": 500000.0,
          "usage_percent": 0.01,
          "has_limit": false,
          "limit_source": "host_total"
        }
      }
    ],
    "source": "cadvisor",
    "cpu_sample_interval_minutes": 1,
    "cpu_last_updated": "2026-01-14 11:59:00"
  }
}
```

---

## node_exporter 說明

### 什麼是 node_exporter？

[node_exporter](https://github.com/prometheus/node_exporter) 是 Prometheus 生態系統中用於收集 **宿主機系統指標** 的官方 exporter。

### 監控指標類型

| 收集器 (Collector) | 說明 | 指標範例 |
|-------------------|------|---------|
| `cpu` | CPU 使用統計 | `node_cpu_seconds_total` |
| `meminfo` | 記憶體使用 | `node_memory_MemTotal_bytes` |
| `filesystem` | 檔案系統使用 | `node_filesystem_size_bytes` |
| `diskstats` | 磁碟 I/O 統計 | `node_disk_read_bytes_total` |
| `netdev` | 網路統計 | `node_network_receive_bytes_total` |

---

## cAdvisor 說明

### 什麼是 cAdvisor？

[cAdvisor](https://github.com/google/cadvisor) (Container Advisor) 是 Google 開源的 **容器資源監控** 工具。

### 監控功能

| 功能 | 說明 |
|------|------|
| 容器發現 | 自動偵測 Docker 容器 |
| CPU 監控 | 容器 CPU 使用率和限制 |
| 記憶體監控 | 容器記憶體使用、快取、工作集 |
| 檔案系統 | 容器檔案系統使用 |

---

## 進階使用

### 整合 Prometheus + Grafana

若要建立完整的監控堆疊，可以加入 Prometheus 和 Grafana：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node_exporter:9100']
  
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

### 常用 PromQL 查詢

```promql
# CPU 使用率 (過去 5 分鐘平均)
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 記憶體使用率
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
```

---

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `NODE_EXPORTER_URL` | http://node_exporter:9100 | node_exporter 連接 URL |
| `CADVISOR_URL` | http://cadvisor:8080 | cAdvisor 連接 URL |
| `CPU_SAMPLE_INTERVAL_MINUTES` | 1 | CPU 採樣間隔 (分鐘) |
| `DATA_DIR` | /app/data | 採樣資料儲存目錄 |

---

## 注意事項

- CPU 使用率基於定時採樣計算，首次啟動需等待一個採樣週期
- node_exporter 和 cAdvisor 僅對內部網路開放，不對外暴露端口
- 容器無 RAM/Storage 限制時，使用宿主機總量計算比例
- 在 Windows Docker Desktop 環境下顯示的是 WSL2 VM 的資源資訊
