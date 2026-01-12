# infra-toolbox

[![CI](https://github.com/yu-codes/infra-toolbox/actions/workflows/ci.yml/badge.svg)](https://github.com/yu-codes/infra-toolbox/actions/workflows/ci.yml)

模組化基礎設施服務工具箱，每個服務獨立封裝為 Docker Compose 堆疊。

## 服務列表

| 服務 | 功能 | 端口 |
|------|------|------|
| [resource_monitoring](resource_monitoring/) | 系統與容器資源監控 (CPU/RAM/Storage) | 10001-10003 |
| [minio](minio/) | S3 相容物件儲存 | 10010-10011 |
| [filebrowser](filebrowser/) | Web 檔案管理器 | 10020 |
| [postgres](postgres/) | PostgreSQL 14 資料庫 (WAL 啟用) | 5432 |
| [postgres_backup_logical](postgres_backup_logical/) | PostgreSQL 邏輯備份 (pg_dump) | - |
| [postgres_backup_physical](postgres_backup_physical/) | PostgreSQL 物理備份 (WAL/PITR) | - |
| [minio_backup](minio_backup/) | MinIO 備份還原 | - |
| [skills](skills/) | AI Agent Skills 範例 (通用格式) | - |

## PostgreSQL 備份策略比較

| 特性 | 邏輯備份 (pg_dump) | 物理備份 (WAL) |
|------|-------------------|----------------|
| 備份服務 | [postgres_backup_logical](postgres_backup_logical/) | [postgres_backup_physical](postgres_backup_physical/) |
| 完整備份 | ✓ pg_dump | ✓ pg_basebackup |
| 增量備份 | △ 時間戳分離 | ✓ WAL Archive (真正增量) |
| Point-in-Time Recovery | ✗ | ✓ |
| 跨版本還原 | ✓ | ✗ |
| 選擇性還原 | ✓ | ✗ |
| 備份速度 | 慢 | 快 |
| 適用場景 | 小型 DB、跨版本 | 大型 DB、PITR、生產環境 |

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
docker compose up -d
```

## 測試環境

所有服務皆已提供可用的 `.env` 設置檔，可直接用於測試：

```bash
# 啟動 PostgreSQL
cd postgres && docker compose up -d

# 啟動邏輯備份服務
cd ../postgres_backup_logical && docker compose up -d

# 執行邏輯備份
docker exec postgres-backup-logical /scripts/backup.sh full

# 或啟動物理備份服務
cd ../postgres_backup_physical && docker compose up -d

# 執行物理備份
docker exec postgres-backup-physical /scripts/backup.sh base
```

## 本地測試

```bash
# 執行單元測試 (檔案結構、語法檢查)
./tests/run_tests.sh unit

# 執行整合測試 (需要 Docker)
./tests/run_tests.sh integration

# 執行所有測試
./tests/run_tests.sh all
```

## CI/CD

專案使用 GitHub Actions 進行持續整合，每次 push 或 PR 會自動執行：

- 單元測試 (語法檢查、檔案結構)
- Docker Compose 配置驗證
- Shell 腳本 Linting (ShellCheck)
- 整合測試 (PostgreSQL、MinIO、Resource Monitoring)

## 目錄結構

```
infra-toolbox/
├── postgres/                    # PostgreSQL 14 資料庫
├── postgres_backup_logical/     # 邏輯備份服務 (pg_dump)
├── postgres_backup_physical/    # 物理備份服務 (WAL/PITR)
├── minio/                       # MinIO 物件儲存
├── minio_backup/                # MinIO 備份服務
├── resource_monitoring/         # 資源監控服務
├── filebrowser/                 # 檔案管理器
├── skills/                      # AI Agent Skills
├── tests/                       # 測試腳本
│   └── run_tests.sh
└── .github/
    └── workflows/
        └── ci.yml               # GitHub Actions CI
```

### 服務目錄結構

```
service_name/
├── docker-compose.yml    # Docker 配置
├── .env.example          # 環境變數範本
├── .env                  # 環境變數 (測試用)
├── scripts/              # 腳本 (若有)
└── README.md             # 服務文檔
```
