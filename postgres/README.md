# PostgreSQL

開發用 PostgreSQL 14 資料庫服務。

## 服務端口

| 服務 | 端口 |
|------|------|
| PostgreSQL | 5432 |

## 快速開始

```bash
# 1. 配置環境變數 (可選)
cp .env.example .env
# 編輯 .env 調整設定

# 2. 建立網路 (首次)
docker network create infra-toolbox-network

# 3. 啟動服務
docker-compose up -d

# 4. 進入 PostgreSQL 命令行
docker-compose exec postgres psql -U postgres
```

## 管理命令

```bash
# 查看日誌
docker-compose logs -f postgres

# 停止服務
docker-compose down

# 查看 volume
docker volume ls

# 清除所有數據
docker-compose down -v
```

## 配置

| 項目 | 預設值 |
|------|--------|
| 用戶名 | postgres |
| 密碼 | postgres |
| 預設資料庫 | mydb |
| 端口 | 5432 |

設定詳見 [.env](.env)

## WAL 歸檔模式

此服務已預設啟用 WAL (Write-Ahead Log) 歸檔模式，支援 Point-in-Time Recovery (PITR)。

| 配置 | 值 | 說明 |
|------|-----|------|
| wal_level | replica | WAL 完整記錄 |
| archive_mode | on | 啟用歸檔 |
| archive_command | cp %p /backups/wal/%f | WAL 歸檔命令 |
| max_wal_senders | 3 | 最大 WAL 發送連接數 |

WAL 檔案會自動歸檔到 `./backups/wal/` 目錄。

## 數據持久化

數據存儲在 `./data` 目錄，WAL 備份存儲在 `./backups` 目錄，即使容器被刪除，數據也會被保留。
