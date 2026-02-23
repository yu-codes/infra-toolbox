# MinIO Backup Service

基於 Docker 的 MinIO 物件儲存備份與還原服務，使用 MinIO 官方工具 `mc` (MinIO Client) 進行資料備份。

---

## 🔍 為什麼使用 Shell 腳本而非 API 程式？

> **這是業界標準做法，非自創方案。**

### 核心概念：mc 是 MinIO 官方客戶端工具

`mc` (MinIO Client) 是 MinIO 官方提供的命令列工具，專為以下場景設計：
- 資料遷移和備份
- 批次操作
- 自動化腳本
- 跨雲端資料同步

### 為什麼不用 API 或程式碼備份？

| 方式 | 說明 | 問題 |
|------|------|------|
| ❌ 自寫 API 客戶端 | 使用 S3 SDK | 需處理分頁、錯誤重試、大檔案分塊 |
| ❌ Web Console 手動備份 | 透過網頁下載 | 無法自動化，不適合生產環境 |
| ✅ **mc** | MinIO 官方工具 | 自動處理所有複雜邏輯 |

### mc 的優勢

```bash
# mc 自動處理以下所有情況：
# - 大檔案分塊傳輸 (multipart upload)
# - 斷點續傳
# - 錯誤自動重試
# - 遞迴目錄處理
# - 元資料 (metadata) 保留
# - 並行傳輸優化
# - S3 相容性 (可用於 AWS S3, GCS 等)
```

### 官方文獻參考

- [MinIO Client 官方文件](https://min.io/docs/minio/linux/reference/minio-mc.html)
- [MinIO Backup and Restore](https://min.io/docs/minio/linux/operations/install-deploy-manage/migrate-fs-gateway.html)

> *"MinIO Client (mc) provides a modern alternative to UNIX commands like ls, cat, cp, mirror, diff, find etc. It supports filesystems and Amazon S3 compatible cloud storage service."* — MinIO Documentation

### 業界實踐

| 服務/公司 | 備份方式 |
|-----------|----------|
| GitLab | 使用 mc 進行物件儲存備份 |
| Kubernetes Operators | Velero 使用 mc/restic 備份 PV |
| 企業環境 | 使用 mc mirror 進行跨區域複製 |

---

## 📋 功能特性

| 功能 | 說明 |
|------|------|
| Bucket 備份 | 完整下載 Bucket 內容並打包 |
| 壓縮 | gzip 壓縮減少備份大小 |
| 加密 | OpenSSL AES-256-CBC (可選) |
| 自動清理 | 依保留天數清理過期備份 |
| S3 相容 | 可用於任何 S3 相容儲存 |

---

## 🚀 快速開始

```bash
# 1. 配置環境變數
cp .env.example .env
# 編輯 .env 設定 MinIO 連接資訊

# 2. 建立網路 (首次)
docker network create infra-toolbox-network

# 3. 啟動服務
docker-compose up -d

# 4. 執行備份
docker exec minio-backup /scripts/backup.sh

# 5. 列出備份
docker exec minio-backup /scripts/restore.sh list

# 6. 還原備份
docker exec minio-backup /scripts/restore.sh restore /backups/minio_backup_XXXXXXXX_XXXXXX.tar.gz
```

---

## 🔧 腳本工作原理詳解

### backup.sh 做了什麼？

```bash
#!/bin/sh
# 備份執行流程:

# 1. 載入環境變數配置
export $(grep -v '^#' /scripts/config/.env | xargs)

# 2. 設定 mc alias (連接 MinIO)
#    mc 使用 alias 管理多個儲存端點
mc alias set backup http://minio:9000 $ACCESS_KEY $SECRET_KEY --api S3v4

# 3. 驗證連接和 Bucket
mc ls backup/$BUCKET_NAME

# 4. 下載 Bucket 所有內容
#    mc cp --recursive 會遞迴下載所有檔案
mc cp --recursive backup/$BUCKET_NAME/ /tmp/backup/

# 5. 打包成 tar
#    將所有檔案打包成單一歸檔
tar -cf backup.tar -C /tmp/backup .

# 6. 壓縮 (可選)
#    使用 gzip 壓縮，通常可減少 50-80% 大小
gzip -9 backup.tar

# 7. 加密 (可選)
#    使用 OpenSSL AES-256 加密
openssl enc -aes-256-cbc -salt -pbkdf2 -pass pass:$PASSWORD \
    -in backup.tar.gz \
    -out backup.tar.gz.enc

# 8. 清理過期備份
find $BACKUP_DIR -name "minio_backup_*" -mtime +$RETENTION_DAYS -delete
```

### restore.sh 做了什麼？

```bash
#!/bin/sh
# 還原執行流程:

# 1. 檢測備份檔案類型
#    根據副檔名判斷是否壓縮/加密

# 2. 解密 (若備份已加密)
openssl enc -aes-256-cbc -d -pbkdf2 -pass pass:$PASSWORD \
    -in backup.tar.gz.enc \
    -out backup.tar.gz

# 3. 解壓縮 (若備份已壓縮)
tar -xzf backup.tar.gz -C /tmp/restore/

# 4. 設定 mc alias
mc alias set restore http://minio:9000 $ACCESS_KEY $SECRET_KEY --api S3v4

# 5. 建立目標 Bucket (若不存在)
mc mb restore/$BUCKET_NAME 2>/dev/null || true

# 6. 上傳所有檔案到 MinIO
#    mc cp --recursive 會遞迴上傳所有檔案
mc cp --recursive /tmp/restore/ restore/$BUCKET_NAME/

# 7. 驗證還原結果
mc ls restore/$BUCKET_NAME/
```

### 備份檔案內容

備份檔案是一個標準的 tar 歸檔，包含 Bucket 的所有檔案：

```
minio_backup_20260114_120000.tar.gz
├── documents/
│   ├── report.pdf
│   └── data.xlsx
├── images/
│   ├── logo.png
│   └── banner.jpg
└── uploads/
    └── user_files/
        └── ...
```

---

## 🔐 加密配置

### 配置範例

```env
# 啟用加密
BACKUP_ENCRYPTION_ENABLED=true

# 設定加密密碼 (必填)
BACKUP_ENCRYPTION_PASSWORD=your_secure_password_here
```

### 備份檔案格式

| 壓縮 | 加密 | 副檔名 |
|------|------|--------|
| ✗ | ✗ | `.tar` |
| ✓ | ✗ | `.tar.gz` |
| ✗ | ✓ | `.tar.enc` |
| ✓ | ✓ | `.tar.gz.enc` |

---

## 🧪 備份與還原演練指南

### 演練目的

定期進行備份還原演練可以：
- 確認備份檔案的完整性
- 驗證還原流程的正確性
- 估算還原所需時間 (RTO)
- 訓練團隊應對災難恢復

### 演練前準備

```bash
# 1. 確認 MinIO 和備份服務運行中
docker ps | grep -E "minio|minio-backup"

# 2. 確認有可用的備份檔案
docker exec minio-backup /scripts/restore.sh list

# 3. 記錄當前 Bucket 狀態
docker exec minio-backup mc ls backup/data/ | wc -l
```

### 演練步驟一：建立測試資料

```bash
# 1. 上傳測試檔案到 MinIO
echo "Test file 1 - $(date)" > /tmp/test1.txt
echo "Test file 2 - $(date)" > /tmp/test2.txt
echo '{"key": "value", "timestamp": "'$(date -Iseconds)'"}' > /tmp/test.json

# 使用 mc 上傳
docker exec minio mc alias set local http://minio:9000 minioadmin minioadmin123
docker exec minio mc cp /tmp/test1.txt local/data/
docker exec minio mc cp /tmp/test2.txt local/data/
docker exec minio mc cp /tmp/test.json local/data/

# 2. 確認上傳成功
docker exec minio-backup mc ls backup/data/
```

### 演練步驟二：執行備份

```bash
# 1. 執行備份
docker exec minio-backup /scripts/backup.sh

# 2. 確認備份建立成功
docker exec minio-backup ls -la /backups/

# 3. 檢查備份檔案大小
docker exec minio-backup du -h /backups/minio_backup_*.tar.gz
```

### 演練步驟三：模擬災難

```bash
# ⚠️ 以下操作會刪除資料，僅在測試環境執行！

# 方案 A：刪除部分檔案
docker exec minio-backup mc rm backup/data/test1.txt

# 方案 B：刪除所有檔案
docker exec minio-backup mc rm --recursive --force backup/data/

# 方案 C：刪除整個 Bucket
docker exec minio-backup mc rb --force backup/data
```

### 演練步驟四：執行還原

```bash
# 1. 列出可用備份
docker exec minio-backup /scripts/restore.sh list

# 2. 執行還原
docker exec minio-backup /scripts/restore.sh restore /backups/minio_backup_XXXXXXXX_XXXXXX.tar.gz

# 3. 驗證還原結果
docker exec minio-backup mc ls backup/data/

# 4. 驗證檔案內容
docker exec minio-backup mc cat backup/data/test.json
```

### 演練步驟五：記錄結果

```markdown
## MinIO 備份還原演練報告

### 基本資訊
- 日期: 2026-01-14
- 執行人: [姓名]
- 備份檔案: minio_backup_20260114_120000.tar.gz

### 測試資料
| 檔案 | 原始大小 | 還原後存在 | 內容一致 |
|------|----------|-----------|----------|
| test1.txt | 50 bytes | ✓ | ✓ |
| test2.txt | 50 bytes | ✓ | ✓ |
| test.json | 100 bytes | ✓ | ✓ |

### 效能數據
- 備份資料量: 500MB
- 備份檔案大小: 150MB (壓縮後)
- 備份耗時: 2 分鐘
- 還原耗時: 3 分鐘

### 結論
✓ 備份還原功能正常，資料完整無誤
```

### 建議演練頻率

| 環境 | 頻率 | 說明 |
|------|------|------|
| 開發環境 | 每月 | 確保備份流程正常 |
| 測試環境 | 每週 | 測試新功能備份相容性 |
| 正式環境 | 每季 | 完整災難恢復演練 |

---

## ⏰ 排程建議

使用 Cron 設定自動備份：

```bash
# 編輯 crontab
crontab -e

# MinIO 備份排程
# 每日凌晨 3:00 執行備份
0 3 * * * docker exec minio-backup /scripts/backup.sh >> /var/log/minio_backup.log 2>&1

# 每週清理過期備份 (可選，腳本會自動清理)
0 4 * * 0 find /path/to/backups -name "minio_backup_*" -mtime +30 -delete
```

---

## 📁 目錄結構

```
backups/
├── minio_backup_YYYYMMDD_HHMMSS.tar.gz[.enc]   # 備份檔案
└── logs/                                        # 備份日誌
    └── backup_YYYYMMDD_HHMMSS.log
```

---

## 🔧 配置說明

詳見 [.env.example](.env.example)

### 主要配置項

| 配置項 | 預設值 | 說明 |
|--------|--------|------|
| `MINIO_ENDPOINT` | minio:9000 | MinIO 伺服器位址 |
| `MINIO_ACCESS_KEY` | minioadmin | MinIO Access Key |
| `MINIO_SECRET_KEY` | minioadmin | MinIO Secret Key |
| `MINIO_USE_SSL` | false | 是否使用 HTTPS |
| `BACKUP_BUCKET` | data | 要備份的 Bucket 名稱 |
| `BACKUP_RETENTION_DAYS` | 30 | 備份保留天數 |
| `BACKUP_COMPRESSION_ENABLED` | true | 啟用壓縮 |
| `BACKUP_ENCRYPTION_ENABLED` | false | 啟用加密 |
| `BACKUP_ENCRYPTION_PASSWORD` | - | 加密密碼 |

---

## ⚠️ 注意事項

- 備份過程會暫時佔用額外磁碟空間 (原始資料大小)
- 大型 Bucket 備份可能需要較長時間
- 加密密碼務必妥善保管，遺失將無法還原
- 建議定期驗證備份檔案完整性

---

## 📚 延伸閱讀

- [MinIO Client (mc) 官方文件](https://min.io/docs/minio/linux/reference/minio-mc.html)
- [MinIO 管理指南](https://min.io/docs/minio/linux/operations/install-deploy-manage.html)
- [S3 相容性說明](https://min.io/docs/minio/linux/operations/concepts.html)
