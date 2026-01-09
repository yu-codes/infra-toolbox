# MinIO Object Storage

S3 相容的物件儲存服務。

## 服務端口

| 服務 | 端口 |
|------|------|
| MinIO API | 10010 |
| MinIO Console | 10011 |

## 快速開始

```bash
# 1. 配置環境變數
cp .env.example .env
# 編輯 .env

# 2. 建立網路 (首次)
docker network create infra-toolbox-network

# 3. 啟動服務
docker-compose up -d

# 4. 訪問控制台
# http://localhost:10011
```

## 配置說明

| 變數 | 說明 | 預設值 |
|------|------|--------|
| MINIO_ROOT_USER | 管理員帳號 | minioadmin |
| MINIO_ROOT_PASSWORD | 管理員密碼 | minioadmin123 |
| MINIO_BROWSER | 控制台開關 | on |

## 目錄結構

```
data/     # 儲存資料 (自動建立)
```
