# Resource Monitoring Service

基於 Docker 的系統與容器資源監控服務。

## 功能特性

| 功能 | 說明 |
|------|------|
| 宿主機監控 | CPU、RAM、Storage 使用率 (via node_exporter) |
| 容器監控 | CPU、Memory 使用率 (via cAdvisor) |
| REST API | FastAPI 提供 JSON 格式監控數據 |

## 服務端口

| 服務 | 端口 |
|------|------|
| node_exporter | 10001 |
| cAdvisor | 10002 |
| Monitoring API | 10003 |

## 架構說明

```
┌─────────────────────────────────────────────────────────────┐
│                     Monitoring API (10003)                   │
│                        FastAPI Server                        │
└────────────────────────┬────────────────────┬───────────────┘
                         │                    │
            ┌────────────▼──────┐   ┌────────▼────────────┐
            │  node_exporter    │   │     cAdvisor        │
            │     (10001)       │   │      (10002)        │
            └────────┬──────────┘   └────────┬────────────┘
                     │                       │
            ┌────────▼──────────┐   ┌────────▼────────────┐
            │    Host System    │   │  Docker Containers  │
            │  (CPU/RAM/Disk)   │   │    (CPU/Memory)     │
            └───────────────────┘   └─────────────────────┘
```

---

## node_exporter 說明

### 什麼是 node_exporter？

[node_exporter](https://github.com/prometheus/node_exporter) 是 Prometheus 生態系統中用於收集 **宿主機系統指標** 的官方 exporter。它能夠暴露各種硬體和作業系統相關的指標。

### 監控指標類型

| 收集器 (Collector) | 說明 | 指標範例 |
|-------------------|------|---------|
| `cpu` | CPU 使用統計 | `node_cpu_seconds_total` |
| `meminfo` | 記憶體使用 | `node_memory_MemTotal_bytes` |
| `filesystem` | 檔案系統使用 | `node_filesystem_size_bytes` |
| `diskstats` | 磁碟 I/O 統計 | `node_disk_read_bytes_total` |
| `netdev` | 網路統計 | `node_network_receive_bytes_total` |
| `loadavg` | 系統負載 | `node_load1`, `node_load5` |

### 存取方式

```bash
# 直接存取 Prometheus 格式指標
curl http://localhost:10001/metrics

# 常用指標查詢
# CPU 使用率
curl -s http://localhost:10001/metrics | grep node_cpu_seconds_total

# 記憶體使用
curl -s http://localhost:10001/metrics | grep node_memory

# 磁碟使用
curl -s http://localhost:10001/metrics | grep node_filesystem
```

### 指標格式說明

node_exporter 輸出 Prometheus 格式的指標：

```prometheus
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{cpu="0",mode="idle"} 1234567.89
node_cpu_seconds_total{cpu="0",mode="system"} 12345.67
node_cpu_seconds_total{cpu="0",mode="user"} 23456.78
```

- `# HELP`: 指標說明
- `# TYPE`: 指標類型 (counter, gauge, histogram, summary)
- `{labels}`: 標籤 (區分不同維度)
- 數值: 指標值

---

## cAdvisor 說明

### 什麼是 cAdvisor？

[cAdvisor](https://github.com/google/cadvisor) (Container Advisor) 是 Google 開源的 **容器資源監控** 工具。它能夠自動發現執行中的容器並收集其資源使用資訊。

### 監控功能

| 功能 | 說明 |
|------|------|
| 容器發現 | 自動偵測 Docker 容器 |
| CPU 監控 | 容器 CPU 使用率和限制 |
| 記憶體監控 | 容器記憶體使用、快取、工作集 |
| 網路監控 | 容器網路 I/O |
| 檔案系統 | 容器檔案系統使用 |
| 即時儀表板 | 內建 Web UI |

### 存取方式

```bash
# Web UI (即時監控儀表板)
open http://localhost:10002

# Prometheus 格式指標
curl http://localhost:10002/metrics

# 容器資訊 API (JSON)
curl http://localhost:10002/api/v1.3/containers/

# 特定容器資訊
curl http://localhost:10002/api/v1.3/containers/docker/<container_id>
```

### 主要指標

| 指標 | 說明 |
|------|------|
| `container_cpu_usage_seconds_total` | 容器 CPU 累計使用時間 |
| `container_memory_usage_bytes` | 容器記憶體使用 (含快取) |
| `container_memory_working_set_bytes` | 容器工作集記憶體 (實際使用) |
| `container_network_receive_bytes_total` | 容器接收網路流量 |
| `container_network_transmit_bytes_total` | 容器傳送網路流量 |
| `container_fs_usage_bytes` | 容器檔案系統使用 |

### cAdvisor Web UI

存取 `http://localhost:10002` 可以看到：

- **容器列表**: 所有執行中的容器
- **資源圖表**: CPU、記憶體、網路即時圖表
- **容器詳情**: 點擊容器查看詳細資訊

---

## 快速開始

```bash
# 1. 建立網路 (首次)
docker network create infra-toolbox-network

# 2. 啟動服務
docker-compose up -d

# 3. 訪問服務
# API
curl http://localhost:10003/system-metrics

# node_exporter (Prometheus 格式)
curl http://localhost:10001/metrics

# cAdvisor Web UI
open http://localhost:10002
```

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /` | API 資訊 |
| `GET /health` | 健康檢查 |
| `GET /system-metrics` | 系統與容器監控指標 |

## 回應範例

```json
{
  "status": "success",
  "timestamp": "2026-01-09 12:00:00",
  "server_metrics": {
    "cpu": {"usage_percent": 25.5, "cpu_count": 8},
    "ram": {"total_gb": 16.0, "used_gb": 8.5, "usage_percent": 53.1},
    "storage": {"total_gb": 500.0, "used_gb": 250.0, "usage_percent": 50.0}
  },
  "container_metrics": {
    "containers": [
      {"name": "nginx", "cpu": {"usage_percent": 1.2}, "memory": {"usage_mb": 128.5}}
    ]
  }
}
```

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

# 容器 CPU 使用率
rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100

# 容器記憶體使用
container_memory_working_set_bytes{name!=""}
```

---

## 注意事項

- CPU 使用率需要兩次採樣才能計算，首次查詢會回傳 `null`
- 在 Windows Docker Desktop 環境下顯示的是 WSL2 VM 的資源資訊
- cAdvisor 需要存取 Docker socket 和系統目錄才能正常運作
- node_exporter 在容器中執行時需要掛載宿主機的 `/proc`、`/sys` 等目錄
