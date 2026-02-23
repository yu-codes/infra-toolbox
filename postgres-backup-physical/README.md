# PostgreSQL Physical Backup Service

基於 Docker 的 PostgreSQL **物理備份**服務，使用 WAL (Write-Ahead Log) 實現真正的增量備份和 PITR (Point-in-Time Recovery)。

---

## 🔍 為什麼使用 Shell 腳本而非 SQL？

> **這是業界標準做法，非自創方案。**

### 核心概念：pg_basebackup 是 PostgreSQL 官方備份工具

物理備份使用 PostgreSQL 官方提供的 `pg_basebackup` 工具，這是一個**獨立的命令列程式**，不是 SQL 語句。它直接複製資料庫的二進制檔案，是 PostgreSQL 官方推薦的生產環境備份方式。

### 物理備份 vs 邏輯備份

| 特性 | 物理備份 (pg_basebackup) | 邏輯備份 (pg_dump) |
|------|------------------------|-------------------|
| 備份內容 | 二進制資料檔案 | SQL 語句 |
| 備份速度 | ⚡ 快 (直接複製檔案) | 較慢 (需解析資料) |
| 還原速度 | ⚡ 快 (直接還原檔案) | 較慢 (需執行 SQL) |
| 增量備份 | ✓ WAL 真正增量 | ✗ 每次完整備份 |
| PITR | ✓ 支援任意時間點 | ✗ 不支援 |
| 跨版本還原 | ✗ 僅同版本 | ✓ 可跨版本 |

### 為什麼不使用 SQL？

物理備份操作的是 PostgreSQL 的**底層資料檔案**，這些是二進制格式，無法用 SQL 語句表示：

```
PostgreSQL Data Directory:
├── base/           # 資料庫檔案 (二進制)
├── global/         # 共享系統表 (二進制)
├── pg_wal/         # WAL 日誌 (二進制)
├── pg_xact/        # 交易狀態 (二進制)
└── ...
```

### 官方文獻參考

- [PostgreSQL pg_basebackup 官方文件](https://www.postgresql.org/docs/current/app-pgbasebackup.html)
- [PostgreSQL Continuous Archiving and PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)

> *"pg_basebackup is used to take base backups of a running PostgreSQL database cluster. The backup is taken without affecting other clients of the database."* — PostgreSQL Documentation

### 業界實踐

| 服務/公司 | 物理備份方式 |
|-----------|-------------|
| AWS RDS | 使用 pg_basebackup + WAL 進行自動備份 |
| Google Cloud SQL | 連續備份使用 WAL 串流 |
| Azure Database | 支援 pg_basebackup 進行備份 |
| Patroni (Zalando) | 使用 pg_basebackup 進行叢集初始化 |

---

## 📋 備份方式

| 特性 | 說明 |
|------|------|
| 備份工具 | pg_basebackup / WAL Archive |
| 備份類型 | 二進制資料檔案 |
| 完整備份 | ✓ Base Backup |
| 增量備份 | ✓ WAL Archive (真正增量) |
| 跨版本還原 | ✗ 僅支援同版本 |
| Point-in-Time Recovery | ✓ 支援 (PITR) |
| 選擇性還原 | ✗ 僅全庫還原 |
| 加密備份 | ✓ 支援 (多種算法可選) |
| 非 Docker PostgreSQL | ✓ 支援 |

## 適用場景

- ✓ 大型資料庫 (> 100GB)
- ✓ 需要 PITR (還原到任意時間點)
- ✓ 生產環境
- ✓ 最小化資料遺失 (RPO 近乎零)
- ✓ 需要真正的增量備份
- ✓ Docker 或非 Docker 運行的 PostgreSQL
- ✗ 需要跨版本還原 (請使用邏輯備份)
- ✗ 需要選擇性備份/還原

---

## 📚 WAL 原理

### WAL (Write-Ahead Log) 工作流程

```
[Transaction] → [WAL Buffer] → [WAL File] → [Archive]
                                    ↓
                              [Data Files]

還原流程:
[Base Backup] + [WAL Replay] = [Any Point in Time]
```

### 為什麼 WAL 可以實現 PITR？

WAL 記錄了資料庫的所有變更操作：

```
WAL Record 1: INSERT INTO users VALUES (1, 'admin')  @ 10:00:00
WAL Record 2: UPDATE users SET email = 'x@y.com'    @ 10:05:00
WAL Record 3: DELETE FROM users WHERE id = 100      @ 10:10:00
WAL Record 4: INSERT INTO orders VALUES (...)       @ 10:15:00
```

透過重放 WAL 記錄，可以將資料庫還原到任意時間點：
- 還原到 10:05:00 → 重放 Record 1-2
- 還原到 10:12:00 → 重放 Record 1-3

---

## 🚀 快速開始

### 1. 配置 PostgreSQL WAL 歸檔

PostgreSQL 需要啟用 WAL 歸檔模式。

#### Docker 環境 (本專案做法)

詳見 [../postgres/README.md](../postgres/README.md#docker-環境啟用-wal-歸檔-本專案做法)

#### 非 Docker 環境

詳見 [../postgres/README.md](../postgres/README.md#非-docker-環境啟用-wal-歸檔)

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

---

## 🔧 腳本工作原理詳解

### backup.sh 做了什麼？

```bash
#!/bin/sh
# Base Backup 執行流程:

# 1. 載入環境變數配置
export $(grep -v '^#' /scripts/config/.env | xargs)

# 2. 驗證配置
#    - 檢查 POSTGRES_PASSWORD
#    - 若啟用加密，檢查 BACKUP_ENCRYPTION_PASSWORD

# 3. 測試資料庫連接
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USERNAME -c "SELECT 1;"

# 4. 執行 pg_basebackup (PostgreSQL 官方工具)
#    這會建立資料庫的完整物理副本
pg_basebackup \
    -h $POSTGRES_HOST \
    -p $POSTGRES_PORT \
    -U $POSTGRES_USERNAME \
    -D /backups/base/base_20260114_120000 \
    -Ft    # tar 格式輸出
    -Xs    # 串流 WAL
    -P     # 顯示進度
    -c fast # checkpoint 模式

# 5. 加密備份檔案 (可選)
openssl enc -aes-256-cbc -salt -pbkdf2 \
    -pass pass:$PASSWORD \
    -in base.tar.gz \
    -out base.tar.gz.enc

# 6. 清理過期備份
find $BACKUP_DIR -name "base_*" -mtime +7 -delete
```

### WAL 歸檔流程

```bash
# WAL 歸檔 (由 PostgreSQL 自動觸發)

# 1. 當 WAL 段寫滿 (預設 16MB) 或執行 pg_switch_wal()
# 2. PostgreSQL 執行 archive_command:
archive_command = 'cp %p /backups/wal/%f'

# 3. backup.sh wal 命令同步 WAL 到備份目錄
cp /postgres_backups/wal/* /backups/wal/

# 4. 可選：壓縮和加密 WAL
gzip -9 000000010000000000000001
openssl enc -aes-256-cbc -salt -pbkdf2 -in wal.gz -out wal.gz.enc
```

### restore.sh 做了什麼？

```bash
#!/bin/sh
# PITR 還原流程:

# 1. 停止 PostgreSQL 服務 (必須)
docker stop postgres

# 2. 清空現有資料目錄
rm -rf /var/lib/postgresql/data/*

# 3. 解壓縮/解密 Base Backup
openssl enc -aes-256-cbc -d -pbkdf2 -pass pass:$PASSWORD -in base.tar.gz.enc | tar xzf -

# 4. 設定還原參數
cat > recovery.signal << EOF
# 表示要進行還原
EOF

cat >> postgresql.auto.conf << EOF
restore_command = 'cp /backups/wal/%f %p'
recovery_target_time = '2026-01-14 15:30:00'
recovery_target_action = 'promote'
EOF

# 5. 啟動 PostgreSQL
#    PostgreSQL 會自動:
#    - 讀取 Base Backup
#    - 重放 WAL 直到 recovery_target_time
#    - 達到目標後 promote 為主伺服器
docker start postgres

# 6. 驗證還原結果
psql -c "SELECT pg_is_in_recovery();"  -- 應該返回 false (還原完成)
```

---

## 🔌 連接模式

### Docker 內 PostgreSQL (預設)

```env
POSTGRES_CONNECTION_MODE=docker
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### 宿主機上的 PostgreSQL

```env
POSTGRES_CONNECTION_MODE=host
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432
```

---

## 📝 備份命令

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

## 🔄 還原命令 (PITR)

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

---

## 🔐 加密配置

### 支援的加密算法

| 算法 | 說明 | 建議 |
|------|------|------|
| `aes-256-cbc` | AES 256-bit CBC 模式 | 預設，最廣泛支援 |
| `aes-128-cbc` | AES 128-bit CBC 模式 | 較快，安全性略低 |
| `aes-192-cbc` | AES 192-bit CBC 模式 | 中等 |
| `aes-256-gcm` | AES 256-bit GCM 模式 | **推薦**，認證加密 |
| `chacha20-poly1305` | ChaCha20-Poly1305 | 現代算法，高效能 |

### 配置範例

```env
# Base Backup 加密
BACKUP_ENCRYPTION_ENABLED=true
BACKUP_ENCRYPTION_ALGORITHM=aes-256-gcm
BACKUP_ENCRYPTION_PASSWORD=your_secure_password

# WAL 加密 (獨立設定)
WAL_ENCRYPTION_ENABLED=true
```

---

## 🧪 備份與還原演練指南

### 演練目的

定期進行 PITR 演練可以：
- 確認 Base Backup 和 WAL 的完整性
- 驗證 PITR 流程的正確性
- 估算還原所需時間 (RTO)
- 訓練團隊應對災難恢復

### 演練前準備

```bash
# 1. 確認備份服務運行中
docker ps | grep postgres-backup-physical

# 2. 確認有可用的 Base Backup
docker exec postgres-backup-physical /scripts/backup.sh list

# 3. 記錄當前資料庫狀態和時間
docker exec postgres psql -U postgres -c "SELECT NOW(), COUNT(*) FROM users;"
```

### 演練步驟一：建立測試環境

```bash
# 1. 確保有近期的 Base Backup
docker exec postgres-backup-physical /scripts/backup.sh base

# 2. 插入一些測試資料，記錄時間點
docker exec postgres psql -U postgres -d mydb -c "
    INSERT INTO users (username, email) VALUES ('test1', 'test1@example.com');
"
CHECKPOINT_1=$(docker exec postgres psql -U postgres -t -c "SELECT NOW();")

# 3. 強制 WAL 切換
docker exec postgres-backup-physical /scripts/backup.sh switch
docker exec postgres-backup-physical /scripts/backup.sh wal

# 4. 插入更多資料
sleep 5
docker exec postgres psql -U postgres -d mydb -c "
    INSERT INTO users (username, email) VALUES ('test2', 'test2@example.com');
"
CHECKPOINT_2=$(docker exec postgres psql -U postgres -t -c "SELECT NOW();")

# 5. 再次 WAL 切換
docker exec postgres-backup-physical /scripts/backup.sh switch
docker exec postgres-backup-physical /scripts/backup.sh wal

# 6. 插入最終資料
sleep 5
docker exec postgres psql -U postgres -d mydb -c "
    INSERT INTO users (username, email) VALUES ('test3', 'test3@example.com');
"
```

### 演練步驟二：執行 PITR 還原

```bash
# ⚠️ 警告：PITR 還原需要停止並重建 PostgreSQL 容器

# 1. 停止 PostgreSQL
docker stop postgres

# 2. 備份現有資料 (以防萬一)
sudo mv /path/to/postgres/data /path/to/postgres/data.bak

# 3. 執行 PITR 還原到 CHECKPOINT_1 時間點
# 此時應只有 test1 資料
docker exec postgres-backup-physical /scripts/restore.sh pitr base_XXXXXXXX_XXXXXX "$CHECKPOINT_1"

# 4. 啟動 PostgreSQL
docker start postgres

# 5. 驗證還原結果
docker exec postgres psql -U postgres -d mydb -c "SELECT * FROM users WHERE username LIKE 'test%';"
# 應只看到 test1，不會看到 test2, test3
```

### 演練步驟三：驗證和記錄

```bash
# 驗證資料一致性
docker exec postgres psql -U postgres -d mydb -c "
    SELECT 
        (SELECT COUNT(*) FROM users WHERE username = 'test1') as has_test1,
        (SELECT COUNT(*) FROM users WHERE username = 'test2') as has_test2,
        (SELECT COUNT(*) FROM users WHERE username = 'test3') as has_test3;
"

# 預期結果:
#  has_test1 | has_test2 | has_test3
# -----------+-----------+-----------
#          1 |         0 |         0
```

### 演練報告範本

```markdown
## PITR 演練報告

### 基本資訊
- 日期: 2026-01-14
- 執行人: [姓名]
- Base Backup: base_20260114_100000
- 目標時間點: 2026-01-14 10:30:00

### 測試資料
| 資料 | 插入時間 | 還原後存在 |
|------|----------|-----------|
| test1 | 10:20:00 | ✓ 是 |
| test2 | 10:35:00 | ✗ 否 (正確) |
| test3 | 10:50:00 | ✗ 否 (正確) |

### 效能數據
- Base Backup 還原耗時: 5 分鐘
- WAL 重放耗時: 30 秒
- 總還原時間: 5 分 30 秒

### 結論
✓ PITR 功能正常，可精確還原到指定時間點
```

### 建議演練頻率

| 環境 | 頻率 | 演練類型 |
|------|------|----------|
| 開發環境 | 每月 | 簡單還原測試 |
| 測試環境 | 每週 | 完整 PITR 演練 |
| 正式環境 | 每季 | 完整災難恢復演練 |

---

## ⏰ 排程建議

```bash
# 編輯 crontab
crontab -e

# PostgreSQL 物理備份排程
# 每週日凌晨 2:00 Base Backup
0 2 * * 0 docker exec postgres-backup-physical /scripts/backup.sh base >> /var/log/pg_physical_backup.log 2>&1

# 每小時同步 WAL (真正增量)
0 * * * * docker exec postgres-backup-physical /scripts/backup.sh switch >> /var/log/pg_physical_backup.log 2>&1

# 每月 1 日 4:00 異地備份
0 4 1 * * docker exec postgres-backup-physical /scripts/backup.sh remote >> /var/log/pg_physical_backup.log 2>&1
```

---

## 📁 目錄結構

```
backups/
├── base/               # Base Backup (完整物理備份)
│   └── base_YYYYMMDD_HHMMSS/
│       ├── base.tar.gz[.enc]
│       ├── pg_wal.tar.gz[.enc]
│       └── backup_info
├── wal/                # WAL 歸檔 (增量)
│   ├── 000000010000000000000001
│   ├── 000000010000000000000002
│   └── ...
├── remote/             # 異地備份暫存
└── logs/               # 備份日誌
    └── backup_YYYYMMDD_HHMMSS.log
```

---

## ⚠️ 注意事項

- 物理備份僅支援同版本 PostgreSQL 還原
- PITR 還原需要停止 PostgreSQL 服務
- WAL 歸檔需要 PostgreSQL 啟用 `archive_mode`
- 加密密碼務必妥善保管，遺失將無法還原
- 定期驗證備份檔案完整性

---

## 📚 延伸閱讀

- [PostgreSQL pg_basebackup 官方文件](https://www.postgresql.org/docs/current/app-pgbasebackup.html)
- [PostgreSQL Continuous Archiving and PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [PostgreSQL WAL 內部機制](https://www.postgresql.org/docs/current/wal-intro.html)
