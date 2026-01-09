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

## 快速開始

```bash
# 1. 建立網路 (首次)
docker network create infra-toolbox-network

# 2. 啟動服務
docker-compose up -d

# 3. 訪問 API
curl http://localhost:10003/system-metrics
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

## 注意事項

- CPU 使用率需要兩次採樣才能計算，首次查詢會回傳 `null`
- 在 Windows Docker Desktop 環境下顯示的是 WSL2 VM 的資源資訊
