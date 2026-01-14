# infra-toolbox

[![CI/CD Pipeline](https://github.com/yu-codes/infra-toolbox/actions/workflows/ci.yml/badge.svg)](https://github.com/yu-codes/infra-toolbox/actions/workflows/ci.yml)

模組化基礎設施服務工具箱，每個服務獨立封裝為 Docker Compose 堆疊，支援 Windows 和 Linux 環境。

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

## 備份演練指南

### PostgreSQL 邏輯備份演練

```bash
# 1. 啟動 PostgreSQL
cd postgres
cp .env.example .env
docker compose up -d

# 2. 啟動備份服務
cd ../postgres_backup_logical
cp .env.example .env
docker compose up -d

# 3. 建立備份
docker exec postgres-backup-logical sh /scripts/backup.sh full

# 4. 模擬災難 (刪除資料)
docker exec postgres psql -U postgres -c "DELETE FROM your_table;"

# 5. 還原備份
docker exec postgres-backup-logical sh /scripts/restore.sh restore /backups/full/full_YYYYMMDD_HHMMSS.sql.gz

# 6. 驗證資料已還原
docker exec postgres psql -U postgres -c "SELECT COUNT(*) FROM your_table;"
```

### PostgreSQL 物理備份演練 (PITR)

```bash
# 1. 確保 PostgreSQL 運行中
cd postgres && docker compose up -d

# 2. 啟動物理備份服務
cd ../postgres_backup_physical
cp .env.example .env
docker compose up -d

# 3. 建立 Base Backup
docker exec postgres-backup-physical sh /scripts/backup.sh base

# 4. 查看可用備份
docker exec postgres-backup-physical sh /scripts/restore.sh list

# 5. 還原到指定時間點 (PITR)
docker exec postgres-backup-physical sh /scripts/restore.sh pitr base_YYYYMMDD_HHMMSS "2024-01-15 10:30:00"
```

### MinIO 備份演練

```bash
# 1. 啟動 MinIO
cd minio
cp .env.example .env
docker compose up -d

# 2. 啟動備份服務
cd ../minio_backup
cp .env.example .env
docker compose up -d

# 3. 等待 mc 安裝完成 (約 30-60 秒)
docker exec minio-backup mc --version

# 4. 執行備份
docker exec minio-backup sh /scripts/backup.sh

# 5. 模擬災難 (刪除 bucket 資料)
docker exec minio mc rm --recursive --force local/your-bucket/

# 6. 還原備份
docker exec minio-backup sh /scripts/restore.sh restore /backups/minio_backup_YYYYMMDD_HHMMSS.tar.gz

# 7. 驗證資料已還原
docker exec minio mc ls local/your-bucket/
```

## 測試

### 測試命令

```bash
# 執行單元測試 (檔案結構、語法檢查)
./tests/run_tests.sh unit

# 執行整合測試 (Docker 服務啟動)
./tests/run_tests.sh integration

# 執行備份還原演練測試 (使用實際服務腳本)
./tests/run_tests.sh drill

# 執行所有測試
./tests/run_tests.sh all

# 強制清理測試環境
./tests/run_tests.sh clean
```

### 測試涵蓋範圍

| 測試類型 | 涵蓋內容 |
|---------|---------|
| 單元測試 | docker-compose.yml 語法、shell 腳本語法、.env.example 存在性、README 文檔 |
| 整合測試 | PostgreSQL 服務啟動、resource_monitoring API 健康檢查 |
| 演練測試 | PostgreSQL 邏輯備份/還原、PostgreSQL 物理備份、MinIO 備份/還原、加密功能 |

## CI/CD

專案使用 GitHub Actions 進行持續整合，每次 push 或 PR 會自動執行：

### Pipeline 階段

1. **Unit Tests** - 語法檢查、檔案結構驗證
2. **Docker Compose Validation** - 所有 docker-compose.yml 語法驗證
3. **ShellCheck** - Shell 腳本 Lint 檢查
4. **Integration Tests** - Docker 服務啟動測試
5. **PostgreSQL Logical Drill** - 邏輯備份演練 (備份→刪除→還原→驗證)
6. **PostgreSQL Physical Drill** - 物理備份服務測試
7. **MinIO Drill** - MinIO 備份演練 (備份→刪除→還原→驗證)
8. **Encryption Test** - 加密/解密功能驗證
9. **Documentation Check** - README 和 .env.example 存在性檢查

## 新增服務開發流程

當您需要在此專案新增服務時，請遵循以下步驟：

### 1. 建立服務目錄結構

```
new_service/
├── docker-compose.yml    # Docker 配置 (必須)
├── .env.example          # 環境變數範本 (必須)
├── README.md             # 服務文檔 (必須)
├── scripts/              # 腳本目錄 (若需要)
│   ├── backup.sh
│   └── restore.sh
└── data/                 # 資料目錄 (若需要)
```

### 2. 服務要求

- **docker-compose.yml**: 必須使用 `infra-toolbox-network` 網路
- **.env.example**: 必須包含所有環境變數的範例值和說明
- **README.md**: 必須包含服務說明、使用方法、技術原理
- **Shell 腳本**: 使用 `#!/bin/sh` (POSIX 相容)，確保 Windows/Linux 都能執行

### 3. 更新測試

編輯 `tests/run_tests.sh`，新增對應的測試函數：

```bash
# 單元測試
test_new_service() {
    log_section "Testing: new_service"
    
    test_file_exists "new_service/docker-compose.yml" "new_service"
    test_file_exists "new_service/.env.example" "new_service"
    test_file_exists "new_service/README.md" "new_service"
    test_docker_compose_syntax "new_service/docker-compose.yml" "new_service"
    
    # 如果有腳本
    test_file_exists "new_service/scripts/backup.sh" "new_service"
    test_shell_syntax "new_service/scripts/backup.sh" "new_service/backup.sh"
}

# 在 run_unit_tests() 中加入
run_unit_tests() {
    ...
    test_new_service
}
```

### 4. 更新 CI/CD

編輯 `.github/workflows/ci.yml`：

1. 在 `docker-compose-validate` job 中新增驗證
2. 如果有備份還原功能，新增對應的 drill test job
3. 在 `documentation-check` 的服務列表中加入新服務

### 5. 更新專案 README

在本 README 中：

1. 在服務列表表格中加入新服務
2. 如有需要，在端口分配中加入對應端口

### 6. 本地測試

```bash
# 確保單元測試通過
./tests/run_tests.sh unit

# 如果有 Docker 測試
./tests/run_tests.sh integration

# 執行所有測試
./tests/run_tests.sh all
```

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
│   ├── run_tests.sh            # 測試框架
│   └── .gitignore              # 忽略臨時測試檔案
└── .github/
    └── workflows/
        └── ci.yml               # GitHub Actions CI/CD
```

### 服務目錄結構

```
service_name/
├── docker-compose.yml    # Docker 配置
├── .env.example          # 環境變數範本
├── .env                  # 環境變數 (實際使用，git 忽略)
├── scripts/              # 腳本 (若有)
│   ├── backup.sh
│   └── restore.sh
├── backups/              # 備份目錄 (若有，git 忽略)
└── README.md             # 服務文檔
```

## 跨平台支援

本專案支援 Windows (Docker Desktop + Git Bash/WSL) 和 Linux 環境：

- 所有 Shell 腳本使用 `#!/bin/sh` (POSIX shell)
- 測試腳本自動設定 `MSYS_NO_PATHCONV=1` 避免 Windows 路徑轉換問題
- 使用 `tr -d '\r\n'` 處理換行符差異

## 授權

MIT License
