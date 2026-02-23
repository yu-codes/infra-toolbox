# PostgreSQL 備份方案（Shell 版本）

基於 Shell 腳本的 PostgreSQL 自動化備份解決方案，支援週全量、日全量、月異地備份，並附帶自動刪舊機制。

## 📋 功能特色

✅ **兩種備份策略**
- 週全量備份：每週完整備份（包含所有資料庫 + 全局對象）
- 日全量備份：每日個別資料庫備份
- 月異地備份：推送至遠端伺服器/NAS

✅ **壓縮與加密**
- 支援多種壓縮格式：gzip、bzip2、xz
- 可調整壓縮級別（1-9）
- OpenSSL AES-256-CBC 加密（密碼或金鑰檔案）
- GPG 加密（對稱或非對稱）
- 自動偵測並處理加密備份還原

✅ **自動刪舊機制**
- 完整備份：保留最近 4 週
- 每日備份：保留最近 7 天
- 異地備份：保留最近 3 個月
- 日誌檔案：保留最近 30 天

✅ **靈活還原功能**
- 支援從完整、每日、異地備份還原
- 可指定日期還原
- 可選擇還原特定資料庫或全部
- 支援還原到不同 PostgreSQL 實例
- 預覽模式確保安全

✅ **多種備份格式**
- SQL 格式（純文字，可手動編輯）
- Custom 格式（二進位，支援平行還原）
- 支援 gzip 壓縮

✅ **彈性配置**
- 透過環境變數輕鬆調整所有設定
- 可指定要備份的資料庫清單

---

## 📁 一、目錄規劃

假設 AP 主機備份存放在 `/opt/pg-backup`，目錄規劃如下：

```
/opt/pg-backup/
├─ scripts/                  # Shell 腳本位置
│  ├─ backup.sh              # 備份主腳本
│  ├─ restore.sh             # 還原主腳本
│  ├─ backup.env             # 備份環境變數設定
│  └─ restore.env            # 還原環境變數設定（選用）
├─ full/                     # 每週完整備份
│  ├─ 20260223/              # 依日期分類
│  │  └─ full_backup_20260223_020000.sql.gz
│  └─ 20260216/
├─ daily/                    # 每日備份
│  ├─ 20260223/
│  │  ├─ db1_20260223_020000.sql.gz
│  │  ├─ db2_20260223_020000.sql.gz
│  │  └─ db3_20260223_020000.dump
│  └─ 20260222/
├─ offsite/                  # 每月異地備份暫存
│  ├─ 202602/                # 依月份分類
│  └─ 202601/
└─ logs/                     # 備份 log
   └─ pg-backup.log
```

**目錄說明：**
- `scripts/` → Shell 腳本與環境變數
- `full/` → 週全量備份（每週執行，包含所有資料庫 + 角色/權限）
- `daily/` → 日全量備份（每日執行，個別資料庫）
- `offsite/` → 月異地備份（每月推送）
- `logs/` → 備份執行日誌

---

## ⚙️ 二、環境變數設定

編輯 `/opt/pg-backup/scripts/backup.env`：

```bash
# ---------- PostgreSQL 連線資訊 ----------
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=your_password_here

# ---------- 備份開關 ----------
ENABLE_FULL_BACKUP=true         # 週全量備份（pg_dumpall）
ENABLE_DAILY_BACKUP=true        # 每日備份（pg_dump）
ENABLE_OFFSITE=true             # 異地備份

# ---------- 備份週期 ----------
FULL_BACKUP_DAY=0               # 週日 (0=週日, 1=週一, ..., 6=週六)
DAILY_BACKUP_HOUR=2             # 每日凌晨 2 點
OFFSITE_BACKUP_DAY=1            # 每月 1 號

# ---------- 本地目錄 ----------
BACKUP_BASE=/opt/pg-backup
FULL_DIR=$BACKUP_BASE/full
DAILY_DIR=$BACKUP_BASE/daily
OFFSITE_DIR=$BACKUP_BASE/offsite
LOG_FILE=$BACKUP_BASE/logs/pg-backup.log

# ---------- 備份設定 ----------
# 備份格式：sql (純文字 SQL) 或 custom (自訂格式，支援平行還原)
BACKUP_FORMAT=sql

# 是否壓縮備份檔案（僅適用於 SQL 格式）
ENABLE_COMPRESSION=true

# 壓縮類型：gzip, bzip2, xz
COMPRESSION_TYPE=gzip

# 壓縮級別：1-9（1=最快，9=最小檔案）
COMPRESSION_LEVEL=6

# 指定要備份的資料庫（逗號分隔，留空則備份所有非範本資料庫）
# 範例：BACKUP_DATABASES=db1,db2,db3
BACKUP_DATABASES=

# ---------- 加密設定 ----------
# 是否啟用加密
ENABLE_ENCRYPTION=false

# 加密方法：openssl-aes256 或 gpg
ENCRYPTION_METHOD=openssl-aes256

# OpenSSL 加密密碼（使用 openssl-aes256 時）
ENCRYPTION_PASSWORD=

# 加密金鑰檔案路徑（選用，優先於密碼）
ENCRYPTION_KEY_FILE=

# GPG 加密收件者（使用 gpg 時）
# 對稱加密留空，非對稱加密填入收件者 email 或 key ID
GPG_RECIPIENT=

# ---------- 異地備份設定 ----------
# 遠端路徑（使用 rsync 格式）
# 範例：user@remote-server:/backup/postgres
# 範例：/mnt/nas/postgres-backup
OFFSITE_REMOTE_PATH=

# ---------- 自動刪舊設定 ----------
FULL_BACKUP_RETAIN_WEEKS=4      # 保留最近 4 週
DAILY_RETAIN_DAYS=7             # 保留最近 7 天
OFFSITE_RETAIN_MONTHS=3         # 保留最近 3 個月
LOG_RETAIN_DAYS=30              # 保留最近 30 天
```

---

## 🚀 三、部署步驟

### 3.1 安裝 PostgreSQL 客戶端工具

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y postgresql-client

# CentOS/RHEL
sudo yum install -y postgresql

# macOS
brew install postgresql

# 驗證安裝
pg_dump --version
psql --version
```

### 3.2 建立目錄結構

```bash
sudo mkdir -p /opt/pg-backup/{scripts,full,daily,offsite,logs}
sudo chown -R $USER:$USER /opt/pg-backup
```

### 3.3 複製腳本與環境變數

```bash
# 複製檔案到目標位置
cp scripts/backup.sh /opt/pg-backup/scripts/
cp scripts/restore.sh /opt/pg-backup/scripts/
cp scripts/backup.env /opt/pg-backup/scripts/
cp scripts/restore.env /opt/pg-backup/scripts/

# 設定執行權限
chmod +x /opt/pg-backup/scripts/backup.sh
chmod +x /opt/pg-backup/scripts/restore.sh
```

### 3.4 修改環境變數

```bash
vim /opt/pg-backup/scripts/backup.env
# 修改 PG_HOST、PG_PORT、PG_USER、PG_PASSWORD
```

**安全建議：**
```bash
# 設定檔案權限，防止密碼外洩
chmod 600 /opt/pg-backup/scripts/backup.env
```

### 3.5 設定 .pgpass（選用，更安全的密碼管理）

不將密碼寫在環境變數中，而是使用 `.pgpass` 檔案：

```bash
# 建立 .pgpass 檔案
cat > ~/.pgpass << EOF
localhost:5432:*:postgres:your_password_here
EOF

# 設定權限（必須）
chmod 600 ~/.pgpass
```

然後在 `backup.env` 中移除 `PG_PASSWORD` 設定。

### 3.6 測試執行

```bash
/opt/pg-backup/scripts/backup.sh
```

### 3.7 設定 cron 定時執行

```bash
crontab -e
```

加入以下內容（每天凌晨 2 點執行）：

```bash
0 2 * * * /bin/bash /opt/pg-backup/scripts/backup.sh
```

---

## 📊 四、備份策略說明

### 4.1 週全量備份 (`full`)

- **頻率**：每週一次（預設週日）
- **用途**：完整備份所有資料庫 + 全局對象（角色、權限、表空間等）
- **工具**：`pg_dumpall`
- **保留**：最近 4 週
- **目錄格式**：`/opt/pg-backup/full/YYYYMMDD/`
- **檔案格式**：`full_backup_YYYYMMDD_HHMMSS.sql.gz`

**特點：**
- 包含所有資料庫
- 包含全局對象（CREATE ROLE、CREATE TABLESPACE 等）
- 適合災難還原

### 4.2 日全量備份 (`daily`)

- **頻率**：每日一次（預設凌晨 2 點）
- **用途**：個別資料庫備份
- **工具**：`pg_dump`
- **保留**：最近 7 天
- **目錄格式**：`/opt/pg-backup/daily/YYYYMMDD/`
- **檔案格式**：
  - SQL 格式：`dbname_YYYYMMDD_HHMMSS.sql.gz`
  - Custom 格式：`dbname_YYYYMMDD_HHMMSS.dump`

**特點：**
- 可選擇備份特定資料庫
- 支援兩種格式（SQL / Custom）
- Custom 格式支援平行還原，速度更快

### 4.3 月異地備份 (`offsite`)

- **頻率**：每月一次（預設每月 1 號）
- **用途**：離線備份防災
- **保留**：最近 3 個月
- **目錄格式**：`/opt/pg-backup/offsite/YYYYMM/`

**特點：**
- 將最新週全量備份推送到遠端
- 支援 rsync 到遠端伺服器或 NAS

### 4.4 自動刪舊機制

腳本會在每次執行時自動清理過期備份：

| 備份類型 | 保留期限 | 環境變數 |
|---------|---------|---------|
| 完整備份 | 4 週 | `FULL_BACKUP_RETAIN_WEEKS` |
| 每日備份 | 7 天 | `DAILY_RETAIN_DAYS` |
| 異地備份 | 3 個月 | `OFFSITE_RETAIN_MONTHS` |
| 日誌檔案 | 30 天 | `LOG_RETAIN_DAYS` |

---

## 📝 五、日誌查看

備份執行日誌位於：`/opt/pg-backup/logs/pg-backup.log`

```bash
# 查看最新日誌
tail -f /opt/pg-backup/logs/pg-backup.log

# 查看今日日誌
grep "$(date '+%Y-%m-%d')" /opt/pg-backup/logs/pg-backup.log

# 查看備份成功/失敗記錄
grep "備份完成\|備份失敗" /opt/pg-backup/logs/pg-backup.log
```

---

## 🔄 六、資料還原

### 6.1 還原腳本功能

`restore.sh` 提供完整的還原功能：

- ✅ 從完整備份還原（所有資料庫）
- ✅ 從每日備份還原（個別資料庫）
- ✅ 從異地備份還原
- ✅ 列出所有可用備份
- ✅ 指定日期還原
- ✅ 選擇性還原（特定資料庫或全部）
- ✅ 還原到不同 PostgreSQL 實例
- ✅ 預覽模式（不實際執行）
- ✅ 強制模式（跳過確認）
- ✅ 還原前刪除現有資料庫（可選）

### 6.2 還原腳本使用方式

```bash
/opt/pg-backup/scripts/restore.sh [選項]

選項：
  -t, --type <TYPE>           備份類型 (full/daily/offsite)
  -d, --date <DATE>           備份日期 (格式：YYYYMMDD 或 YYYYMM)
  -D, --database <DB>         指定要還原的資料庫（僅適用於 daily 類型）
  -f, --file <FILE>           直接指定備份檔案路徑
  -H, --host <HOST>           目標資料庫主機（預設：使用 backup.env 設定）
  -p, --port <PORT>           目標資料庫埠號（預設：使用 backup.env 設定）
  -U, --user <USER>           目標資料庫使用者（預設：使用 backup.env 設定）
  -l, --list                  列出可用的備份
  -n, --dry-run               預覽模式（不實際執行）
  --force                     強制覆蓋，不詢問確認
  --drop-database             還原前先刪除資料庫（謹慎使用）
  -h, --help                  顯示說明
```

### 6.3 還原範例

#### 範例 1：列出所有可用的完整備份

```bash
/opt/pg-backup/scripts/restore.sh --list --type full
```

輸出：
```
==========================================
可用的 full 備份：
==========================================
  [20260223]  大小: 1.2G  檔案數: 1
  [20260216]  大小: 1.1G  檔案數: 1
  [20260209]  大小: 1.0G  檔案數: 1
==========================================
```

#### 範例 2：列出每日備份（含檔案列表）

```bash
/opt/pg-backup/scripts/restore.sh --list --type daily
```

輸出：
```
==========================================
可用的 daily 備份：
==========================================
  [20260223]  大小: 850M  檔案數: 3
          檔案：
            - myapp_20260223_020000.sql.gz (500M)
            - users_20260223_020000.sql.gz (250M)
            - logs_20260223_020000.sql.gz (100M)
  [20260222]  大小: 820M  檔案數: 3
          檔案：
            - myapp_20260222_020000.sql.gz (480M)
            - users_20260222_020000.sql.gz (240M)
            - logs_20260222_020000.sql.gz (100M)
==========================================
```

#### 範例 3：從完整備份還原所有資料庫

```bash
/opt/pg-backup/scripts/restore.sh --type full --date 20260223
```

執行時會顯示確認訊息：
```
==========================================
⚠️  警告：此操作將會覆蓋目標資料庫的資料！
==========================================
備份來源：/opt/pg-backup/full/20260223
目標主機：localhost:5432
目標使用者：postgres
還原範圍：全部資料庫
==========================================
確定要繼續嗎？(yes/no):
```

#### 範例 4：從每日備份還原特定資料庫

```bash
/opt/pg-backup/scripts/restore.sh --type daily --date 20260223 --database myapp
```

#### 範例 5：還原特定資料庫並刪除現有資料

```bash
/opt/pg-backup/scripts/restore.sh --type daily --date 20260223 --database myapp --drop-database
```

**⚠️ 警告**：`--drop-database` 會先刪除現有資料庫，請謹慎使用！

#### 範例 6：直接指定備份檔案還原

```bash
/opt/pg-backup/scripts/restore.sh --file /opt/pg-backup/daily/20260223/myapp_20260223_020000.sql.gz
```

#### 範例 7：預覽還原操作（不實際執行）

```bash
/opt/pg-backup/scripts/restore.sh --type full --date 20260223 --dry-run
```

#### 範例 8：還原到不同的 PostgreSQL 實例

```bash
/opt/pg-backup/scripts/restore.sh --type full --date 20260223 \
  --host 192.168.1.100 \
  --port 5432 \
  --user postgres \
  --force
```

#### 範例 9：從異地備份還原

```bash
/opt/pg-backup/scripts/restore.sh --type offsite --date 202602
```

### 6.4 還原最佳實踐

#### 1. 還原前檢查

```bash
# 步驟 1：列出可用備份
/opt/pg-backup/scripts/restore.sh --list --type full

# 步驟 2：使用預覽模式確認操作
/opt/pg-backup/scripts/restore.sh --type full --date 20260223 --dry-run

# 步驟 3：執行實際還原
/opt/pg-backup/scripts/restore.sh --type full --date 20260223
```

#### 2. 災難還原流程（完全重建）

```bash
# 步驟 1：停止應用程式
sudo systemctl stop your-app

# 步驟 2：（如果 PostgreSQL 需要重新安裝）
sudo apt-get install -y postgresql postgresql-client

# 步驟 3：從完整備份還原
/opt/pg-backup/scripts/restore.sh --type full --date <最新日期> --force

# 步驟 4：驗證資料
psql -U postgres -d myapp -c "SELECT COUNT(*) FROM users;"

# 步驟 5：啟動應用程式
sudo systemctl start your-app
```

#### 3. 部分還原流程（單一資料庫）

```bash
# 只還原特定資料庫，不影響其他資料庫
/opt/pg-backup/scripts/restore.sh --type daily --date 20260223 --database myapp
```

#### 4. 測試環境還原

```bash
# 還原到測試環境
/opt/pg-backup/scripts/restore.sh --type full --date 20260223 \
  --host test-db-server \
  --port 5432 \
  --user postgres
```

#### 5. 時間點還原（Point-in-Time Recovery）

如果需要還原到特定時間點：

```bash
# 步驟 1：還原最近的完整備份
/opt/pg-backup/scripts/restore.sh --type full --date 20260223

# 步驟 2：如果有 WAL 歸檔，可以使用 PostgreSQL 的 PITR 功能
# （需要事先設定 WAL 歸檔，不在此腳本範圍內）
```

### 6.5 還原環境變數設定（選用）

如果需要還原到不同的 PostgreSQL 實例，可編輯 `/opt/pg-backup/scripts/restore.env`：

```bash
# 還原目標 PostgreSQL 設定
RESTORE_PG_HOST=192.168.1.100
RESTORE_PG_PORT=5432
RESTORE_PG_USER=postgres
RESTORE_PG_PASSWORD=new_password
```

---

## 🔧 七、進階設定

### 7.1 調整備份週期

修改 `backup.env`：

```bash
FULL_BACKUP_DAY=0          # 0=週日, 1=週一, ..., 6=週六
DAILY_BACKUP_HOUR=2        # 執行時間（小時）
OFFSITE_BACKUP_DAY=1       # 每月 1-31 號
```

### 7.2 調整保留策略

修改 `backup.env`：

```bash
FULL_BACKUP_RETAIN_WEEKS=8     # 增加至 8 週
DAILY_RETAIN_DAYS=14           # 增加至 14 天
OFFSITE_RETAIN_MONTHS=6        # 增加至 6 個月
```

### 7.3 備份特定資料庫

修改 `backup.env`：

```bash
# 只備份指定的資料庫（逗號分隔）
BACKUP_DATABASES=myapp,users,logs
```

### 7.4 使用 Custom 格式（支援平行還原）

修改 `backup.env`：

```bash
# 使用 Custom 格式
BACKUP_FORMAT=custom
```

還原時使用平行處理：

```bash
# 使用 4 個並行作業還原（更快）
pg_restore -d myapp -j 4 /opt/pg-backup/daily/20260223/myapp_20260223_020000.dump
```

### 7.5 設定異地備份

修改 `backup.env`：

```bash
# 使用 rsync 推送到遠端伺服器
OFFSITE_REMOTE_PATH=user@backup-server:/backup/postgres

# 或推送到 NAS
OFFSITE_REMOTE_PATH=/mnt/nas/postgres-backup
```

**設定 SSH 免密碼登入（使用 SSH 金鑰）：**

```bash
# 產生 SSH 金鑰
ssh-keygen -t rsa -b 4096

# 複製公鑰到遠端伺服器
ssh-copy-id user@backup-server
```

### 7.6 停用某項備份

修改 `backup.env`：

```bash
ENABLE_FULL_BACKUP=true        # 保留週全量備份
ENABLE_DAILY_BACKUP=true       # 保留日備份
ENABLE_OFFSITE=false           # 停用異地備份
```

### 7.7 設定備份壓縮

修改 `backup.env`：

```bash
# 啟用壓縮
ENABLE_COMPRESSION=true

# 選擇壓縮類型
COMPRESSION_TYPE=gzip          # 或 bzip2、xz

# 調整壓縮級別（1=最快，9=最小檔案）
COMPRESSION_LEVEL=6            # 平衡速度與壓縮率
```

**壓縮類型比較：**

| 壓縮類型 | 壓縮率 | 速度 | CPU 使用 |
|---------|-------|------|---------|
| gzip    | 中等  | 快   | 低      |
| bzip2   | 高    | 慢   | 中      |
| xz      | 最高  | 最慢 | 高      |

### 7.8 設定備份加密

**方法 1：使用 OpenSSL AES-256 加密（密碼）**

修改 `backup.env`：

```bash
# 啟用加密
ENABLE_ENCRYPTION=true

# 使用 OpenSSL
ENCRYPTION_METHOD=openssl-aes256

# 設定加密密碼
ENCRYPTION_PASSWORD=your_strong_password_here
```

**方法 2：使用 OpenSSL AES-256 加密（金鑰檔案，更安全）**

```bash
# 生成金鑰檔案
openssl rand -base64 32 > /opt/pg-backup/scripts/.encryption_key
chmod 600 /opt/pg-backup/scripts/.encryption_key

# 修改 backup.env
ENABLE_ENCRYPTION=true
ENCRYPTION_METHOD=openssl-aes256
ENCRYPTION_KEY_FILE=/opt/pg-backup/scripts/.encryption_key
```

**方法 3：使用 GPG 對稱加密**

```bash
# 安裝 GPG
sudo apt-get install -y gnupg

# 修改 backup.env
ENABLE_ENCRYPTION=true
ENCRYPTION_METHOD=gpg
ENCRYPTION_PASSWORD=your_gpg_passphrase
# GPG_RECIPIENT 留空表示對稱加密
```

**方法 4：使用 GPG 非對稱加密（最安全）**

```bash
# 生成 GPG 金鑰對
gpg --full-generate-key

# 查看金鑰
gpg --list-keys

# 修改 backup.env
ENABLE_ENCRYPTION=true
ENCRYPTION_METHOD=gpg
GPG_RECIPIENT=your-email@example.com
# 或使用 Key ID
GPG_RECIPIENT=1234ABCD5678EFGH
```

**安全建議：**

```bash
# 保護環境變數檔案
chmod 600 /opt/pg-backup/scripts/backup.env

# 保護金鑰檔案
chmod 600 /opt/pg-backup/scripts/.encryption_key

# 定期更換加密密碼或金鑰
# 將金鑰備份到安全位置（離線存儲）
```

**還原加密備份：**

還原腳本會自動偵測加密檔案（副檔名 `.enc`）並要求輸入密碼或讀取金鑰檔案。確保 `backup.env` 中的加密設定與備份時一致。

---

## 🛠️ 八、故障排除

### 8.1 備份相關問題

#### 問題 1：無法連線至 PostgreSQL

**錯誤訊息**：
```
[ERROR] 無法連線至 PostgreSQL: localhost:5432
```

**解決方法**：
1. 檢查 PostgreSQL 是否啟動：
   ```bash
   sudo systemctl status postgresql
   ```

2. 確認 `PG_HOST`、`PG_PORT`、`PG_USER`、`PG_PASSWORD` 是否正確

3. 檢查 `pg_hba.conf` 是否允許連線：
   ```bash
   # 編輯 pg_hba.conf
   sudo vim /etc/postgresql/14/main/pg_hba.conf
   
   # 確保有這行（允許本地連線）
   host    all             all             127.0.0.1/32            md5
   ```

4. 測試連線：
   ```bash
   psql -h localhost -p 5432 -U postgres -c "SELECT 1"
   ```

#### 問題 2：權限不足

**錯誤訊息**：
```
ERROR:  permission denied for database
```

**解決方法**：
1. 確保使用的使用者有足夠權限：
   ```sql
   -- 授予 superuser 權限（謹慎使用）
   ALTER USER postgres WITH SUPERUSER;
   
   -- 或授予特定資料庫權限
   GRANT ALL PRIVILEGES ON DATABASE mydb TO postgres;
   ```

2. 使用 `postgres` 超級使用者執行備份

#### 問題 3：備份檔案過大導致磁碟空間不足

**解決方法**：
1. 啟用壓縮：
   ```bash
   # 在 backup.env 中
   ENABLE_COMPRESSION=true
   ```

2. 減少保留期限：
   ```bash
   FULL_BACKUP_RETAIN_WEEKS=2
   DAILY_RETAIN_DAYS=3
   ```

3. 使用 Custom 格式（通常比 SQL 格式小）：
   ```bash
   BACKUP_FORMAT=custom
   ```

4. 檢查磁碟空間：
   ```bash
   df -h /opt/pg-backup
   du -sh /opt/pg-backup/*
   ```

#### 問題 4：備份執行時間過長

**解決方法**：
1. 只備份必要的資料庫：
   ```bash
   BACKUP_DATABASES=myapp,users
   ```

2. 使用 Custom 格式（比 SQL 格式快）

3. 檢查資料庫大小：
   ```sql
   SELECT 
       pg_database.datname,
       pg_size_pretty(pg_database_size(pg_database.datname)) AS size
   FROM pg_database
   ORDER BY pg_database_size(pg_database.datname) DESC;
   ```

### 8.2 還原相關問題

#### 問題 5：找不到指定日期的備份

**錯誤訊息**：
```
[ERROR] 備份不存在：/opt/pg-backup/full/20260223
```

**解決方法**：
1. 使用 `--list` 參數查看可用備份：
   ```bash
   /opt/pg-backup/scripts/restore.sh --list --type full
   ```

2. 確認日期格式正確（完整備份：YYYYMMDD，異地備份：YYYYMM）

3. 檢查備份目錄：
   ```bash
   ls -la /opt/pg-backup/full/
   ```

#### 問題 6：還原時提示資料庫已存在

**錯誤訊息**：
```
ERROR:  database "myapp" already exists
```

**解決方法**：
1. 使用 `--drop-database` 選項（會先刪除現有資料庫）：
   ```bash
   /opt/pg-backup/scripts/restore.sh --type daily --date 20260223 \
     --database myapp --drop-database
   ```

2. 或手動刪除資料庫：
   ```bash
   psql -U postgres -c "DROP DATABASE myapp;"
   ```

#### 問題 7：還原後資料不完整

**可能原因與解決方法**：

1. **備份檔案損壞**
   ```bash
   # 檢查檔案完整性
   gunzip -t /opt/pg-backup/daily/20260223/myapp_20260223_020000.sql.gz
   ```

2. **還原過程中斷**
   - 查看日誌檔案檢查錯誤
   - 重新執行還原

3. **權限問題**
   - 確保還原使用者有足夠權限
   - 使用 superuser 執行還原

4. **版本不相容**
   ```bash
   # 檢查 PostgreSQL 版本
   psql --version
   pg_dump --version
   ```

#### 問題 8：還原 Custom 格式檔案失敗

**解決方法**：
```bash
# 使用 pg_restore 而非 psql
pg_restore -d myapp --clean --if-exists /opt/pg-backup/daily/20260223/myapp.dump

# 增加詳細輸出查看錯誤
pg_restore -d myapp --clean --if-exists --verbose /opt/pg-backup/daily/20260223/myapp.dump
```

#### 問題 9：還原時覆蓋了重要資料

**預防措施**：

1. **使用預覽模式**
   ```bash
   /opt/pg-backup/scripts/restore.sh --type full --date 20260223 --dry-run
   ```

2. **先還原到測試環境**
   ```bash
   /opt/pg-backup/scripts/restore.sh --type full --date 20260223 \
     --host test-server --user test_user
   ```

3. **在還原前手動備份當前資料**
   ```bash
   pg_dumpall > /tmp/manual_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

---

## 📚 九、相關資源

- [PostgreSQL 官方文檔 - 備份與還原](https://www.postgresql.org/docs/current/backup.html)
- [pg_dump 文檔](https://www.postgresql.org/docs/current/app-pgdump.html)
- [pg_dumpall 文檔](https://www.postgresql.org/docs/current/app-pg-dumpall.html)
- [pg_restore 文檔](https://www.postgresql.org/docs/current/app-pgrestore.html)
- [PostgreSQL 最佳實踐](https://wiki.postgresql.org/wiki/Backup_and_Recovery)

---

## 📄 授權

MIT License
