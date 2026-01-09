# infra-toolbox

模組化基礎設施服務工具箱，每個服務獨立封裝為 Docker Compose 堆疊。

## 服務列表

| 服務 | 功能 | 端口 |
|------|------|------|
| [resource_monitoring](resource_monitoring/) | 系統與容器資源監控 (CPU/RAM/Storage) | 10001-10003 |
| [minio](minio/) | S3 相容物件儲存 | 10010-10011 |
| [filebrowser](filebrowser/) | Web 檔案管理器 | 10020 |
| [postgres_backup](postgres_backup/) | PostgreSQL 備份還原 (完全/增量/異地) | - |
| [minio_backup](minio_backup/) | MinIO 備份還原 | - |
| [skills](skills/) | Claude Agent Skills 範例與規範 | - |

## 端口分配

| 範圍 | 用途 |
|------|------|
| 10001-10009 | 監控服務 |
| 10010-10019 | 儲存服務 |
| 10020-10029 | 檔案管理 |

## 快速開始

```bash
# 建立共用網路
docker network create infra-toolbox-network

# 啟動服務 (以 resource_monitoring 為例)
cd resource_monitoring
cp .env.example .env
docker-compose up -d
```

## 目錄結構

```
service_name/
├── docker-compose.yml    # Docker 配置
├── .env.example          # 環境變數範本
├── scripts/              # 腳本 (若有)
└── README.md             # 服務文檔
```
