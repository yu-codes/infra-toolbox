# PostgreSQL Service

基於 Docker 的 PostgreSQL 資料庫服務，預設啟用 WAL (Write-Ahead Log) 歸檔模式以支援完整的備份與還原功能。

## 功能特性

| 功能 | 說明 |
|------|------|
| 資料庫版本 | PostgreSQL 14 (Alpine) |
| WAL 歸檔 | ✓ 預設啟用 |
| 健康檢查 | ✓ 內建 |
| 持久化儲存 | ✓ Volume 掛載 |

## 快速開始

```bash
# 1. 建立網路 (首次)
docker network create infra-toolbox-network

# 2. 配置環境變數
cp .env.example .env
# 編輯 .env 設定密碼等資訊

# 3. 啟動服務
docker-compose up -d
```

---

## WAL 歸檔模式詳解

### 什麼是 WAL (Write-Ahead Log)?

WAL 是 PostgreSQL 的核心持久化機制，所有資料變更在寫入實際資料檔案之前，會先寫入 WAL 日誌。這個機制提供：

1. **資料完整性** - 系統崩潰時可從 WAL 恢復
2. **PITR (Point-in-Time Recovery)** - 還原到任意時間點
3. **串流複製** - 主從複製的基礎
4. **真正的增量備份** - 只需備份新的 WAL 檔案

### WAL 歸檔工作流程

```
[應用程式寫入] → [WAL Buffer] → [WAL 檔案] → [archive_command 觸發]
                                      ↓                    ↓
                                [Data Files]    [歸檔位置 /backups/wal/]
```

### 歸檔相關參數說明

| 參數 | 本專案設定 | 說明 |
|------|-----------|------|
| `wal_level` | `replica` | WAL 記錄等級，支援串流複製 |
| `archive_mode` | `on` | 啟用 WAL 歸檔 |
| `archive_command` | `cp %p /backups/wal/%f` | 歸檔執行命令 |
| `max_wal_senders` | `3` | 最大 WAL 串流連線數 |

---

## Docker 環境啟用 WAL 歸檔 (本專案做法)

本專案透過 `docker-compose.yml` 的 `command` 參數啟用 WAL 歸檔：

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
      - 'archive_command=mkdir -p /backups/wal && cp %p /backups/wal/%f'
      - -c
      - max_wal_senders=3
    volumes:
      - ./data:/var/lib/postgresql/data
      - ./backups:/backups
      - ./wal_archive:/postgres_backups/wal
```

### 驗證 WAL 歸檔是否啟用

```bash
# 連接到 PostgreSQL
docker exec -it postgres psql -U postgres

# 檢查 WAL 設定
SHOW wal_level;          -- 應顯示 'replica'
SHOW archive_mode;       -- 應顯示 'on'
SHOW archive_command;    -- 應顯示設定的歸檔命令

# 檢查歸檔狀態
SELECT * FROM pg_stat_archiver;
```

---

## 非 Docker 環境啟用 WAL 歸檔

如果您的 PostgreSQL 不是透過 Docker 運行（直接安裝在系統上），請依照以下步驟啟用 WAL 歸檔：

### 步驟 1: 找到設定檔位置

```bash
# Linux (套件管理器安裝)
/etc/postgresql/14/main/postgresql.conf

# Linux (原始碼編譯安裝)
/usr/local/pgsql/data/postgresql.conf

# macOS (Homebrew)
/usr/local/var/postgres/postgresql.conf

# Windows
C:\Program Files\PostgreSQL\14\data\postgresql.conf

# 透過 SQL 查詢設定檔位置
psql -U postgres -c "SHOW config_file;"
```

### 步驟 2: 建立歸檔目錄

```bash
# Linux/macOS
sudo mkdir -p /var/lib/postgresql/backups/wal
sudo chown postgres:postgres /var/lib/postgresql/backups/wal
sudo chmod 700 /var/lib/postgresql/backups/wal

# Windows (以管理員身分執行 PowerShell)
New-Item -ItemType Directory -Path "C:\pg_backups\wal" -Force
```

### 步驟 3: 修改 postgresql.conf

```conf
# === WAL 歸檔設定 ===

# WAL 等級：replica 支援串流複製和 PITR
wal_level = replica

# 啟用歸檔模式
archive_mode = on

# 歸檔命令 - 將 WAL 檔案複製到指定目錄
# Linux/macOS:
archive_command = 'cp %p /var/lib/postgresql/backups/wal/%f'

# Windows:
# archive_command = 'copy "%p" "C:\\pg_backups\\wal\\%f"'

# 最大 WAL 串流連線數
max_wal_senders = 3

# WAL 保留設定 (可選)
wal_keep_size = 1GB
```

### 步驟 4: 修改 pg_hba.conf (允許複製連線)

```conf
# 允許本機複製連線 (用於 pg_basebackup)
host    replication     postgres        127.0.0.1/32            scram-sha-256
host    replication     postgres        ::1/128                 scram-sha-256

# 如果需要從其他機器連線 (例如備份伺服器)
host    replication     postgres        10.0.0.0/8              scram-sha-256
```

### 步驟 5: 重啟 PostgreSQL

```bash
# systemd (Ubuntu/Debian/CentOS)
sudo systemctl restart postgresql

# macOS (Homebrew)
brew services restart postgresql

# Windows
net stop postgresql-x64-14
net start postgresql-x64-14

# 或使用 pg_ctl
pg_ctl restart -D /path/to/data
```

### 步驟 6: 驗證設定

```bash
# 連接 PostgreSQL
psql -U postgres

# 驗證參數
SHOW wal_level;          -- 應為 'replica'
SHOW archive_mode;       -- 應為 'on'
SHOW archive_command;    -- 應顯示設定的命令

# 強制切換 WAL (產生歸檔)
SELECT pg_switch_wal();

# 等待幾秒後檢查歸檔目錄
# ls /var/lib/postgresql/backups/wal/
```

### 常見問題排解

| 問題 | 原因 | 解決方案 |
|------|------|----------|
| archive_mode 無法變更 | 需要重啟 PostgreSQL | 確保完整重啟服務 |
| WAL 檔案未歸檔 | 權限問題 | 確保歸檔目錄權限正確 |
| archive_command 失敗 | 路徑不存在 | 確保目錄已建立 |
| pg_basebackup 連線失敗 | pg_hba.conf 未設定 | 添加 replication 授權 |

---

## 目錄結構

```
postgres/
├── docker-compose.yml      # Docker Compose 設定
├── .env.example           # 環境變數範例
├── README.md              # 本文件
├── data/                  # PostgreSQL 資料檔案
├── backups/               # 備份目錄
│   └── wal/              # WAL 歸檔 (自動產生)
└── wal_archive/          # WAL 副本 (供備份服務使用)
```

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `POSTGRES_USER` | postgres | 資料庫使用者 |
| `POSTGRES_PASSWORD` | postgres | 資料庫密碼 (**請修改**) |
| `POSTGRES_DB` | mydb | 預設資料庫名稱 |
| `POSTGRES_PORT` | 5432 | 對外端口 |

## 相關服務

- [postgres_backup_logical](../postgres_backup_logical/) - 邏輯備份 (pg_dump)
- [postgres_backup_physical](../postgres_backup_physical/) - 物理備份 (WAL-based, PITR)
