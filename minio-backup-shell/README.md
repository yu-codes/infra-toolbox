# MinIO 備份方案（Shell 版本）

基於 Shell 腳本的 MinIO 自動化備份解決方案，支援週全量、日增量、月異地備份，並附帶自動刪舊機制。

## 📋 功能特色

✅ **三種備份策略**
- 週全量備份：每週完整快照
- 日增量備份：每日同步變更
- 月異地備份：推送至遠端 S3/MinIO/NAS

✅ **壓縮與加密**
- 支援多種壓縮格式：gzip、bzip2、xz
- 可調整壓縮級別（1-9）
- OpenSSL AES-256-CBC 加密（密碼或金鑰檔案）
- GPG 加密（對稱或非對稱）
- 自動打包、壓縮、加密備份目錄
- 自動偵測並處理加密備份還原

✅ **自動刪舊機制**
- 完整備份：保留最近 4 週
- 增量備份：保留最近 7 天
- 異地備份：保留最近 3 個月
- 日誌檔案：保留最近 30 天

✅ **靈活還原功能**
- 支援從完整、增量、異地備份還原
- 可指定日期還原
- 可選擇還原特定 bucket 或全部
- 支援還原到不同 MinIO 實例
- 預覽模式確保安全

✅ **可中斷續傳**
- 支援大檔案傳輸中斷後續傳

✅ **彈性配置**
- 透過環境變數輕鬆調整所有設定

---

## 📁 一、目錄規劃

假設 AP 主機備份存放在 `/opt/minio-backup`，目錄規劃如下：

```
/opt/minio-backup/
├─ scripts/                  # Shell 腳本位置
│  ├─ backup.sh        # 備份主腳本
│  ├─ restore.sh             # 還原主腳本
│  ├─ backup.env       # 備份環境變數設定
│  └─ restore.env            # 還原環境變數設定（選用）
├─ full/                     # 每週完整備份
│  ├─ 20260223/              # 依日期分類
│  └─ 20260216/
├─ incremental/              # 每日增量備份
│  ├─ 20260223/
│  └─ 20260222/
├─ offsite/                  # 每月異地備份暫存
│  ├─ 202602/                # 依月份分類
│  └─ 202601/
└─ logs/                     # 備份 log
   └─ minio-backup.log
```

**目錄說明：**
- `scripts/` → Shell 腳本與環境變數
- `full/` → 週全量備份（每週執行）
- `incremental/` → 日增量備份（每日執行）
- `offsite/` → 月異地備份（每月推送）
- `logs/` → 備份執行日誌

---

## ⚙️ 二、環境變數設定

編輯 `/opt/minio-backup/scripts/backup.env`：

```bash
# DB MinIO 連線資訊
MINIO_HOST=http://172.16.1.129:9000
MINIO_USER=MINIO_ROOT_USER
MINIO_PASS=MINIO_ROOT_PASSWORD

# 備份開關
ENABLE_FULL_BACKUP=true
ENABLE_INCREMENTAL=true
ENABLE_OFFSITE=true

# 備份週期
FULL_BACKUP_DAY=0          # 週日 (0=週日, 1=週一, ..., 6=週六)
INCREMENTAL_BACKUP_HOUR=2  # 每日凌晨 2 點
OFFSITE_BACKUP_DAY=1       # 每月 1 號

# 本地目錄
BACKUP_BASE=/opt/minio-backup
FULL_DIR=$BACKUP_BASE/full
INCREMENTAL_DIR=$BACKUP_BASE/incremental
OFFSITE_DIR=$BACKUP_BASE/offsite
LOG_FILE=$BACKUP_BASE/logs/minio-backup.log

# 壓縮設定
COMPRESSION_TYPE=gzip          # gzip, bzip2, xz
COMPRESSION_LEVEL=6            # 1-9（1=最快，9=最小檔案）

# 加密設定
ENABLE_ENCRYPTION=false        # 是否啟用加密
ENCRYPTION_METHOD=openssl-aes256  # openssl-aes256 或 gpg
ENCRYPTION_PASSWORD=           # OpenSSL 加密密碼
ENCRYPTION_KEY_FILE=           # 加密金鑰檔案路徑（優先於密碼）
GPG_RECIPIENT=                 # GPG 收件者（email 或 key ID）

# 異地備份 alias (S3 / MinIO / NAS)
OFFSITE_ALIAS=offsite_minio

# 自動刪舊設定
FULL_BACKUP_RETAIN_WEEKS=4    # 保留最近 4 週
INCREMENTAL_RETAIN_DAYS=7     # 保留最近 7 天
OFFSITE_RETAIN_MONTHS=3       # 保留最近 3 個月
LOG_RETAIN_DAYS=30            # 保留最近 30 天

# mc 設定
export MC_HTTP_TIMEOUT=0
export MC_CONCURRENCY=1
```

---

## 🚀 三、部署步驟

### 3.1 安裝 MinIO Client (mc)

```bash
# Linux / macOS
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# 驗證安裝
mc --version
```

### 3.2 建立目錄結構

```bash
sudo mkdir -p /opt/minio-backup/{scripts,full,incremental,offsite,logs}
sudo chown -R $USER:$USER /opt/minio-backup
```

### 3.3 複製腳本與環境變數

```bash
# 複製檔案到目標位置
cp scripts/backup.sh /opt/minio-backup/scripts/
cp scripts/restore.sh /opt/minio-backup/scripts/
cp scripts/backup.env /opt/minio-backup/scripts/
cp scripts/restore.env /opt/minio-backup/scripts/

# 設定執行權限
chmod +x /opt/minio-backup/scripts/backup.sh
chmod +x /opt/minio-backup/scripts/restore.sh
```

### 3.4 修改環境變數

```bash
vim /opt/minio-backup/scripts/backup.env
# 修改 MINIO_HOST、MINIO_USER、MINIO_PASS
```

### 3.5 設定異地備份 alias（選用）

如果需要推送到遠端 S3/MinIO，先設定 alias：

```bash
mc alias set offsite_minio https://remote-minio.example.com REMOTE_USER REMOTE_PASS
```

### 3.6 測試執行

```bash
/opt/minio-backup/scripts/backup.sh
```

### 3.7 設定 cron 定時執行

```bash
crontab -e
```

加入以下內容（每天凌晨 2 點執行）：

```bash
0 2 * * * /bin/bash /opt/minio-backup/scripts/backup.sh
```

---

## 📊 四、備份策略說明

### 4.1 週全量備份 (`full`)

- **頻率**：每週一次（預設週日）
- **用途**：完整快照與異地推送
- **保留**：最近 4 週
- **目錄格式**：`/opt/minio-backup/full/YYYYMMDD/`

### 4.2 日增量備份 (`incremental`)

- **頻率**：每日一次（預設凌晨 2 點）
- **用途**：同步變更檔案
- **保留**：最近 7 天
- **目錄格式**：`/opt/minio-backup/incremental/YYYYMMDD/`

### 4.3 月異地備份 (`offsite`)

- **頻率**：每月一次（預設每月 1 號）
- **用途**：離線備份防災
- **保留**：最近 3 個月
- **目錄格式**：`/opt/minio-backup/offsite/YYYYMM/`

### 4.4 自動刪舊機制

腳本會在每次執行時自動清理過期備份：

| 備份類型 | 保留期限 | 環境變數 |
|---------|---------|---------|
| 完整備份 | 4 週 | `FULL_BACKUP_RETAIN_WEEKS` |
| 增量備份 | 7 天 | `INCREMENTAL_RETAIN_DAYS` |
| 異地備份 | 3 個月 | `OFFSITE_RETAIN_MONTHS` |
| 日誌檔案 | 30 天 | `LOG_RETAIN_DAYS` |

---

## 📝 五、日誌查看

備份執行日誌位於：`/opt/minio-backup/logs/minio-backup.log`

```bash
# 查看最新日誌
tail -f /opt/minio-backup/logs/minio-backup.log

# 查看今日日誌
grep "$(date '+%Y-%m-%d')" /opt/minio-backup/logs/minio-backup.log
```

---

## � 六、資料還原

### 6.1 還原腳本功能

`restore.sh` 提供完整的還原功能：

- ✅ 從完整備份還原
- ✅ 從增量備份還原
- ✅ 從異地備份還原
- ✅ 列出所有可用備份
- ✅ 指定日期還原
- ✅ 選擇性還原（特定 bucket 或全部）
- ✅ 還原到不同 MinIO 實例
- ✅ 預覽模式（不實際執行）
- ✅ 強制模式（跳過確認）

### 6.2 還原腳本使用方式

```bash
/opt/minio-backup/scripts/restore.sh [選項]

選項：
  -t, --type <TYPE>           備份類型 (full/incremental/offsite)
  -d, --date <DATE>           備份日期 (格式：YYYYMMDD 或 YYYYMM)
  -b, --bucket <BUCKET>       指定要還原的 bucket（不指定則還原全部）
  -r, --target <ALIAS>        還原目標 MinIO alias（預設：dbminio）
  -l, --list                  列出可用的備份
  -n, --dry-run               預覽模式（不實際執行）
  -f, --force                 強制覆蓋，不詢問確認
  -h, --help                  顯示說明
```

### 6.3 還原範例

#### 範例 1：列出所有可用的完整備份

```bash
/opt/minio-backup/scripts/restore.sh --list --type full
```

輸出：
```
==========================================
可用的 full 備份：
==========================================
  [20260223]  大小: 2.5G  檔案數: 1523
  [20260216]  大小: 2.3G  檔案數: 1456
  [20260209]  大小: 2.1G  檔案數: 1389
==========================================
```

#### 範例 2：從完整備份還原全部資料

```bash
/opt/minio-backup/scripts/restore.sh --type full --date 20260223
```

執行時會顯示確認訊息：
```
==========================================
⚠️  警告：此操作將會覆蓋目標 MinIO 的資料！
==========================================
備份來源：/opt/minio-backup/full/20260223
還原目標：dbminio
還原範圍：全部 buckets
==========================================
確定要繼續嗎？(yes/no):
```

#### 範例 3：還原特定 bucket

```bash
/opt/minio-backup/scripts/restore.sh --type full --date 20260223 --bucket my-bucket
```

#### 範例 4：預覽還原操作（不實際執行）

```bash
/opt/minio-backup/scripts/restore.sh --type full --date 20260223 --dry-run
```

#### 範例 5：強制還原（跳過確認）

```bash
/opt/minio-backup/scripts/restore.sh --type full --date 20260223 --force
```

#### 範例 6：還原到不同的 MinIO 實例

```bash
# 先設定新的 MinIO alias
mc alias set new_minio http://192.168.1.100:9000 NEW_USER NEW_PASS

# 還原到新實例
/opt/minio-backup/scripts/restore.sh --type full --date 20260223 --target new_minio
```

#### 範例 7：從增量備份還原

```bash
/opt/minio-backup/scripts/restore.sh --type incremental --date 20260223
```

#### 範例 8：從異地備份還原

```bash
/opt/minio-backup/scripts/restore.sh --type offsite --date 202602
```

### 6.4 還原最佳實踐

#### 1. 還原前檢查

```bash
# 1. 列出可用備份
/opt/minio-backup/scripts/restore.sh --list --type full

# 2. 使用預覽模式確認操作
/opt/minio-backup/scripts/restore.sh --type full --date 20260223 --dry-run

# 3. 執行實際還原
/opt/minio-backup/scripts/restore.sh --type full --date 20260223
```

#### 2. 災難還原流程

```bash
# 步驟 1：安裝 MinIO Client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc && sudo mv mc /usr/local/bin/

# 步驟 2：設定目標 MinIO alias
mc alias set dbminio http://172.16.1.129:9000 MINIO_USER MINIO_PASS

# 步驟 3：列出可用備份
/opt/minio-backup/scripts/restore.sh --list

# 步驟 4：選擇最新的完整備份還原
/opt/minio-backup/scripts/restore.sh --type full --date <最新日期>
```

#### 3. 部分還原流程

```bash
# 只還原特定 bucket
/opt/minio-backup/scripts/restore.sh --type full --date 20260223 --bucket important-data
```

#### 4. 測試環境還原

```bash
# 設定測試環境 MinIO
mc alias set test_minio http://test-server:9000 TEST_USER TEST_PASS

# 還原到測試環境
/opt/minio-backup/scripts/restore.sh --type full --date 20260223 --target test_minio
```

### 6.5 還原環境變數設定（選用）

如果需要還原到不同的 MinIO 實例，可編輯 `/opt/minio-backup/scripts/restore.env`：

```bash
# 還原目標 MinIO 設定
RESTORE_MINIO_HOST=http://192.168.1.100:9000
RESTORE_MINIO_USER=NEW_MINIO_USER
RESTORE_MINIO_PASS=NEW_MINIO_PASSWORD
RESTORE_MINIO_ALIAS=restore_target
```

---

## 🔧 七、進階設定

### 7.1 調整備份週期

修改 `backup.env`：

```bash
FULL_BACKUP_DAY=0          # 0=週日, 1=週一, ..., 6=週六
INCREMENTAL_BACKUP_HOUR=2  # 執行時間（小時）
OFFSITE_BACKUP_DAY=1       # 每月 1-31 號
```

### 7.2 調整保留策略

修改 `backup.env`：

```bash
FULL_BACKUP_RETAIN_WEEKS=8     # 增加至 8 週
INCREMENTAL_RETAIN_DAYS=14     # 增加至 14 天
OFFSITE_RETAIN_MONTHS=6        # 增加至 6 個月
```

### 7.3 停用某項備份

修改 `backup.env`：

```bash
ENABLE_FULL_BACKUP=false       # 停用週全量備份
ENABLE_INCREMENTAL=true        # 保留日增量備份
ENABLE_OFFSITE=false           # 停用異地備份
```

### 7.4 設定備份壓縮

修改 `backup.env`：

```bash
# 選擇壓縮類型
COMPRESSION_TYPE=gzip          # 或 bzip2、xz

# 調整壓縮級別（1=最快，9=最小檔案）
COMPRESSION_LEVEL=6            # 平衡速度與壓縮率
```

**壓縮類型比較：**

| 壓縮類型 | 壓縮率 | 速度 | CPU 使用 | 適用場景 |
|---------|-------|------|---------|---------|
| gzip    | 中等  | 快   | 低      | 一般備份 |
| bzip2   | 高    | 慢   | 中      | 節省空間 |
| xz      | 最高  | 最慢 | 高      | 長期存檔 |

### 7.5 設定備份加密

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
openssl rand -base64 32 > /opt/minio-backup/scripts/.encryption_key
chmod 600 /opt/minio-backup/scripts/.encryption_key

# 修改 backup.env
ENABLE_ENCRYPTION=true
ENCRYPTION_METHOD=openssl-aes256
ENCRYPTION_KEY_FILE=/opt/minio-backup/scripts/.encryption_key
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
chmod 600 /opt/minio-backup/scripts/backup.env

# 保護金鑰檔案
chmod 600 /opt/minio-backup/scripts/.encryption_key

# 定期更換加密密碼或金鑰
# 將金鑰備份到安全位置（離線存儲）
```

**還原加密備份：**

還原腳本會自動偵測加密檔案（副檔名 `.enc`）並要求輸入密碼或讀取金鑰檔案。確保 `backup.env` 中的加密設定與備份時一致。

---

## 🛠️ 八、故障排除

### 8.1 備份相關問題

#### 問題 1：無法連線至 MinIO

**錯誤訊息**：
```
[ERROR] 無法連線至 MinIO: http://172.16.1.129:9000
```

**解決方法**：
1. 檢查 MinIO 是否啟動
2. 確認 `MINIO_HOST`、`MINIO_USER`、`MINIO_PASS` 是否正確
3. 測試連線：`mc alias set test $MINIO_HOST $MINIO_USER $MINIO_PASS`

#### 問題 2：備份檔案過大導致執行時間過長

**解決方法**：
1. 調整 `MC_CONCURRENCY` 增加並發數（預設 1）
2. 使用增量備份取代全量備份
3. 排除不必要的 bucket

#### 問題 3：磁碟空間不足

**解決方法**：
1. 減少保留週期
2. 定期清理舊備份
3. 使用 `du -sh /opt/minio-backup/*` 查看各目錄大小

### 8.2 還原相關問題

#### 問題 4：找不到指定日期的備份

**錯誤訊息**：
```
[ERROR] 備份不存在：/opt/minio-backup/full/20260223
```

**解決方法**：
1. 使用 `--list` 參數查看可用備份：
   ```bash
   /opt/minio-backup/scripts/restore.sh --list --type full
   ```
2. 確認日期格式正確（完整備份：YYYYMMDD，異地備份：YYYYMM）
3. 檢查備份目錄是否存在：`ls -la /opt/minio-backup/full/`

#### 問題 5：還原時提示 alias 不存在

**錯誤訊息**：
```
[ERROR] 目標 alias 不存在：dbminio
```

**解決方法**：
1. 設定 MinIO alias：
   ```bash
   mc alias set dbminio http://172.16.1.129:9000 MINIO_USER MINIO_PASS
   ```
2. 確認 alias 已設定：
   ```bash
   mc alias list
   ```

#### 問題 6：還原後資料不完整

**可能原因**：
1. 備份檔案損壞
2. 還原過程中斷
3. 磁碟空間不足

**解決方法**：
1. 先使用 `--dry-run` 預覽還原操作
2. 檢查備份檔案完整性：
   ```bash
   find /opt/minio-backup/full/20260223 -type f | wc -l
   ```
3. 確保目標 MinIO 有足夠空間
4. 查看還原日誌檢查錯誤訊息

#### 問題 7：還原時覆蓋了重要資料

**預防措施**：
1. 使用 `--dry-run` 預覽模式先確認
2. 先還原到測試環境驗證
3. 在還原前手動備份當前資料：
   ```bash
   mc mirror dbminio /backup/manual-backup-$(date +%Y%m%d)
   ```

#### 問題 8：還原特定 bucket 失敗

**錯誤訊息**：
```
[ERROR] 備份中不存在 bucket：my-bucket
```

**解決方法**：
1. 確認備份中包含該 bucket：
   ```bash
   ls -la /opt/minio-backup/full/20260223/
   ```
2. 檢查 bucket 名稱拼寫是否正確
3. 如果 bucket 不在備份中，改為還原全部後再手動處理

---

## 📚 九、相關資源

- [MinIO Client 官方文檔](https://min.io/docs/minio/linux/reference/minio-mc.html)
- [MinIO Server 官方網站](https://min.io/)
- [Shell 腳本最佳實踐](https://google.github.io/styleguide/shellguide.html)

---

## 📄 授權

MIT License
