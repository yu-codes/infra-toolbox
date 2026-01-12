# PostgreSQL Physical Backup Service

基於 Docker 的 PostgreSQL **物理備份**服務，使用 WAL (Write-Ahead Log) 實現真正的增量備份和 PITR。

## 備份方式

| 特性 | 說明 |
|------|------|
| 備份工具 | pg_basebackup / WAL Archive |
| 備份類型 | 二進制資料檔案 |
| 完整備份 | ✓ Base Backup |
| 增量備份 | ✓ WAL Archive (真正增量) |
| 跨版本還原 | ✗ 僅支援同版本 |
| Point-in-Time Recovery | ✓ 支援 (PITR) |
| 選擇性還原 | ✗ 僅全庫還原 |

## 適用場景

- ✓ 大型資料庫 (> 100GB)
- ✓ 需要 PITR (還原到任意時間點)
- ✓ 生產環境
- ✓ 最小化資料遺失 (RPO 近乎零)
- ✓ 需要真正的增量備份
- ✗ 需要跨版本還原 (請使用邏輯備份)
- ✗ 需要選擇性備份/還原

## WAL 原理

```
[Transaction] → [WAL Buffer] → [WAL File] → [Archive]
                                    ↓
                              [Data Files]

還原流程:
[Base Backup] + [WAL Replay] = [Any Point in Time]
```

## 快速開始

### 1. 配置 PostgreSQL

PostgreSQL 需要啟用 WAL 歸檔模式。在 `postgres/docker-compose.yml` 中：

```yaml
services:
  postgres:
    image: postgres:14-alpine
    command:
      - postgres
      - -c
      - wal_level=replica
      - -c
      - archive_mode=on
      - -c
      - archive_command=cp %p /backups/wal/%f
    volumes:
      - ./data:/var/lib/postgresql/data
      - ./backups:/backups
```

### 2. 啟動備份服務

```bash
# 配置環境變數
cp .env.example .env

# 建立網路
docker network create infra-toolbox-network

# 啟動服務
docker-compose up -d
```

### 3. 執行備份

```bash
# 完整備份 (Base Backup)
docker exec postgres-backup-physical /scripts/backup.sh base

# 同步 WAL 歸檔 (增量)
docker exec postgres-backup-physical /scripts/backup.sh wal

# 強制切換 WAL 段 (確保最新資料被歸檔)
docker exec postgres-backup-physical /scripts/backup.sh switch
```

## 備份命令

```bash
# Base Backup (完整物理備份，建議每週)
docker exec postgres-backup-physical /scripts/backup.sh base

# WAL Archive (增量備份，建議每小時)
docker exec postgres-backup-physical /scripts/backup.sh wal

# WAL Switch (強制切換 WAL，觸發歸檔)
docker exec postgres-backup-physical /scripts/backup.sh switch

# 異地備份 (建議每月)
docker exec postgres-backup-physical /scripts/backup.sh remote

# 查看備份狀態
docker exec postgres-backup-physical /scripts/backup.sh status

# 列出可用備份
docker exec postgres-backup-physical /scripts/backup.sh list
```

## 還原命令 (PITR)

```bash
# 列出可用備份和 WAL 範圍
docker exec postgres-backup-physical /scripts/restore.sh list

# 還原到最新狀態
docker exec postgres-backup-physical /scripts/restore.sh prepare base_20260110_120000

# 還原到指定時間點 (PITR)
docker exec postgres-backup-physical /scripts/restore.sh pitr base_20260110_120000 '2026-01-10 15:30:00'

# 驗證備份完整性
docker exec postgres-backup-physical /scripts/restore.sh verify base_20260110_120000
```

## 排程建議

使用 Cron 設定排程：

```bash
# 編輯 crontab
crontab -e

# PostgreSQL 物理備份排程
# 每週日凌晨 2:00 Base Backup
0 2 * * 0 docker exec postgres-backup-physical /scripts/backup.sh base >> /var/log/pg_physical_backup.log 2>&1

# 每小時同步 WAL (真正增量)
0 * * * * docker exec postgres-backup-physical /scripts/backup.sh switch >> /var/log/pg_physical_backup.log 2>&1

# 每月 1 日凌晨 4:00 異地備份
0 4 1 * * docker exec postgres-backup-physical /scripts/backup.sh remote >> /var/log/pg_physical_backup.log 2>&1
```

## 配置說明

詳見 [.env.example](.env.example)

### 主要配置項

| 配置項 | 預設值 | 說明 |
|--------|--------|------|
| `POSTGRES_HOST` | postgres | PostgreSQL 主機 |
| `POSTGRES_PORT` | 5432 | PostgreSQL 端口 |
| `BASE_BACKUP_RETENTION_DAYS` | 7 | Base Backup 保留天數 |
| `WAL_RETENTION_DAYS` | 14 | WAL 歸檔保留天數 |
| `BASE_BACKUP_COMPRESSION` | true | Base Backup 壓縮 |
| `WAL_COMPRESSION` | true | WAL 壓縮 |

## 目錄結構

```
backups/
├── base/                    # Base Backup
│   └── base_YYYYMMDD_HHMMSS/
│       ├── base.tar.gz      # 資料檔案
│       ├── pg_wal.tar.gz    # WAL 檔案
│       └── backup_info      # 備份資訊
├── wal/                     # WAL 歸檔
│   ├── 000000010000000000000001.gz
│   ├── 000000010000000000000002.gz
│   └── ...
├── remote/                  # 異地備份暫存
│   └── remote_YYYYMMDD_HHMMSS.tar.gz
├── restore_staging/         # PITR 還原暫存區
│   ├── pgdata/              # 還原的資料目錄
│   └── wal_restore/         # WAL 還原目錄
└── logs/                    # 備份日誌
```

## PostgreSQL 配置要求

| 配置項 | 值 | 說明 |
|--------|-----|------|
| `wal_level` | `replica` 或 `logical` | WAL 完整記錄 |
| `archive_mode` | `on` | 啟用歸檔 |
| `archive_command` | `cp %p /path/to/wal/%f` | WAL 歸檔命令 |
| `max_wal_senders` | ≥ 2 | WAL 發送連接數 |

## 注意事項

- 物理備份僅支援同版本 PostgreSQL 還原
- 使用者需要 `REPLICATION` 權限才能執行 `pg_basebackup`
- WAL 歸檔目錄需要足夠的磁碟空間
- PITR 只能還原到 Base Backup 之後的時間點
- 還原過程需要停止目標 PostgreSQL 服務
