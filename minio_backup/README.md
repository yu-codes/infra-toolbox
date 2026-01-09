# MinIO Backup Service

基於 Docker 的 MinIO 物件儲存備份與還原服務。

## 功能特性

| 功能 | 說明 |
|------|------|
| Bucket 備份 | 完整下載 Bucket 內容並打包 |
| 壓縮 | gzip 壓縮減少備份大小 |
| 加密 | OpenSSL AES-256-CBC (可選) |
| 自動清理 | 依保留天數清理過期備份 |

## 快速開始

```bash
# 1. 配置環境變數
cp .env.example .env
# 編輯 .env

# 2. 建立網路 (首次)
docker network create infra-toolbox-network

# 3. 啟動服務
docker-compose up -d

# 4. 執行備份
docker exec minio-backup /scripts/backup.sh

# 5. 還原備份
docker exec minio-backup /scripts/restore.sh list
docker exec minio-backup /scripts/restore.sh restore /backups/minio_backup_XXXXXXXX_XXXXXX.tar.gz
```

## 配置說明

詳見 [.env.example](.env.example)

## 目錄結構

```
backups/
├── minio_backup_*.tar.gz    # 備份檔案
└── logs/                    # 備份日誌
```
