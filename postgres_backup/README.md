# PostgreSQL Backup Service

基於 Docker 的 PostgreSQL 備份與還原服務。

## 功能特性

| 功能 | 說明 |
|------|------|
| 完全備份 | 每週完整資料庫備份 |
| 增量備份 | 每日差異備份 |
| 異地備份 | 每月異地備份 (SSH/SCP) |
| 壓縮 | gzip (DEFLATE 無損壓縮) |
| 加密 | OpenSSL AES-256-CBC |
| 可選機制 | 每個備份類型可獨立啟用/禁用 |

## 快速開始

```bash
# 1. 配置環境變數
cp .env.example .env
# 編輯 .env，根據需要調整備份機制

# 2. 建立網路 (首次)
docker network create infra-toolbox-network

# 3. 啟動服務
docker-compose up -d

# 4. 執行備份
docker exec postgres-backup /scripts/backup.sh full
docker exec postgres-backup /scripts/backup.sh incremental
docker exec postgres-backup /scripts/backup.sh remote

# 5. 還原備份
docker exec postgres-backup /scripts/restore.sh list
docker exec postgres-backup /scripts/restore.sh restore /backups/full/full_XXXXXXXX_XXXXXX.sql.gz.enc
```

## 備份機制配置

| 機制 | 環境變數 | 說明 |
|------|---------|------|
| 完全備份 | `BACKUP_FULL_ENABLED` | true/false，每週完整備份 |
| 增量備份 | `BACKUP_INCREMENTAL_ENABLED` | true/false，每日備份 |
| 異地備份 | `BACKUP_REMOTE_ENABLED` | true/false，每月遠端備份 |

**範例：僅啟用完全備份**
```env
BACKUP_FULL_ENABLED=true
BACKUP_INCREMENTAL_ENABLED=false
BACKUP_REMOTE_ENABLED=false
```

## 排程建議

| 類型 | 頻率 | Cron 表達式 | 啟用開關 |
|------|------|-------------|---------|
| 完全備份 | 每週日凌晨 2 點 | `0 2 * * 0` | BACKUP_FULL_ENABLED |
| 增量備份 | 每日凌晨 3 點 | `0 3 * * *` | BACKUP_INCREMENTAL_ENABLED |
| 異地備份 | 每月 1 日凌晨 4 點 | `0 4 1 * *` | BACKUP_REMOTE_ENABLED |

## 配置說明

詳見 [.env.example](.env.example)

### 主要配置項

**連接設定**
- `POSTGRES_HOST`: PostgreSQL 主機
- `POSTGRES_USERNAME`: 連接帳號
- `POSTGRES_PASSWORD`: 連接密碼
- `POSTGRES_DATABASE`: 要備份的資料庫

**備份選項**
- `BACKUP_COMPRESSION_ENABLED`: 是否壓縮 (gzip)
- `BACKUP_ENCRYPTION_ENABLED`: 是否加密 (AES-256-CBC)
- `BACKUP_ENCRYPTION_PASSWORD`: 加密密碼 (若啟用加密)

**異地備份** (設定 `BACKUP_REMOTE_ENABLED=true` 時)
- `REMOTE_BACKUP_HOST`: 遠端主機
- `REMOTE_BACKUP_USER`: 遠端帳號
- `REMOTE_BACKUP_PATH`: 遠端路徑

## 目錄結構

```
backups/
├── full/           # 完全備份
├── incremental/    # 增量備份
├── remote/         # 異地備份
└── logs/           # 備份日誌
```
