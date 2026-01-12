# PostgreSQL Logical Backup Service

基於 Docker 的 PostgreSQL **邏輯備份**服務，使用 `pg_dump` / `pg_restore` 進行備份還原。

## 備份方式

| 特性 | 說明 |
|------|------|
| 備份工具 | pg_dump / pg_restore |
| 備份類型 | SQL 文字檔或自訂格式 |
| 完整備份 | ✓ 支援 |
| 增量備份 | △ 僅時間戳分離 (非真正增量) |
| 跨版本還原 | ✓ 支援 |
| Point-in-Time Recovery | ✗ 不支援 |
| 選擇性還原 | ✓ 支援 (特定資料表) |

## 適用場景

- ✓ 小型到中型資料庫 (< 100GB)
- ✓ 需要跨 PostgreSQL 版本還原
- ✓ 需要選擇性備份/還原特定資料表
- ✓ 開發/測試環境
- △ 大型資料庫 (備份/還原較慢)
- ✗ 需要 PITR (請使用物理備份)

## 快速開始

```bash
# 1. 配置環境變數
cp .env.example .env
# 編輯 .env 設定資料庫連接資訊

# 2. 建立網路 (首次)
docker network create infra-toolbox-network

# 3. 啟動服務
docker-compose up -d

# 4. 執行備份
docker exec postgres-backup-logical /scripts/backup.sh full
```

## 備份命令

```bash
# 完全備份 (建議每週)
docker exec postgres-backup-logical /scripts/backup.sh full

# 增量備份 (建議每日)
docker exec postgres-backup-logical /scripts/backup.sh incremental

# 異地備份 (建議每月)
docker exec postgres-backup-logical /scripts/backup.sh remote

# 列出可用備份
docker exec postgres-backup-logical /scripts/backup.sh list
```

## 還原命令

```bash
# 列出可用備份
docker exec postgres-backup-logical /scripts/restore.sh list

# 驗證備份完整性
docker exec postgres-backup-logical /scripts/restore.sh verify /backups/full/full_XXXXXXXX_XXXXXX.sql.gz

# 還原指定備份
docker exec postgres-backup-logical /scripts/restore.sh restore /backups/full/full_XXXXXXXX_XXXXXX.sql.gz
```

## 排程建議

使用 Cron 設定排程：

```bash
# 編輯 crontab
crontab -e

# PostgreSQL 邏輯備份排程
# 每週日凌晨 2:00 完全備份
0 2 * * 0 docker exec postgres-backup-logical /scripts/backup.sh full >> /var/log/pg_logical_backup.log 2>&1

# 每日凌晨 3:00 增量備份
0 3 * * * docker exec postgres-backup-logical /scripts/backup.sh incremental >> /var/log/pg_logical_backup.log 2>&1

# 每月 1 日凌晨 4:00 異地備份
0 4 1 * * docker exec postgres-backup-logical /scripts/backup.sh remote >> /var/log/pg_logical_backup.log 2>&1
```

## 配置說明

詳見 [.env.example](.env.example)

### 主要配置項

| 配置項 | 預設值 | 說明 |
|--------|--------|------|
| `POSTGRES_HOST` | postgres | PostgreSQL 主機 |
| `POSTGRES_PORT` | 5432 | PostgreSQL 端口 |
| `POSTGRES_DATABASE` | - | 要備份的資料庫 (必填) |
| `FULL_BACKUP_RETENTION_DAYS` | 30 | 完全備份保留天數 |
| `INCREMENTAL_BACKUP_RETENTION_DAYS` | 7 | 增量備份保留天數 |
| `BACKUP_COMPRESSION_ENABLED` | true | 啟用 gzip 壓縮 |
| `BACKUP_ENCRYPTION_ENABLED` | false | 啟用 AES-256 加密 |

## 目錄結構

```
backups/
├── full/           # 完全備份
│   └── full_YYYYMMDD_HHMMSS.sql.gz
├── incremental/    # 增量備份
│   └── incremental_YYYYMMDD_HHMMSS.sql.gz
├── remote/         # 異地備份暫存
│   └── remote_YYYYMMDD_HHMMSS.sql.gz
└── logs/           # 備份日誌
    └── backup_YYYYMMDD_HHMMSS.log
```

## 備份檔案格式

| 壓縮 | 加密 | 副檔名 |
|------|------|--------|
| ✗ | ✗ | `.sql` |
| ✓ | ✗ | `.sql.gz` |
| ✗ | ✓ | `.sql.enc` |
| ✓ | ✓ | `.sql.gz.enc` |

## 注意事項

- 邏輯備份使用 `pg_dump`，大型資料庫備份時間較長
- 「增量備份」實際上是完整 dump，僅以時間區隔 (pg_dump 不支援真正增量)
- 若需要真正的增量備份和 PITR，請使用 [postgres_backup_physical](../postgres_backup_physical/)
- 加密使用 OpenSSL AES-256-CBC，請妥善保管加密密碼
