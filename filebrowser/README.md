# File Browser

Web 檔案管理器，提供簡潔的檔案上傳/下載/管理介面。

## 服務端口

| 服務 | 端口 |
|------|------|
| File Browser | 10020 |

## 快速開始

```bash
# 1. 建立網路 (首次)
docker network create infra-toolbox-network

# 2. 啟動服務
docker-compose up -d

# 3. 訪問介面
# http://localhost:10020
# 預設帳號: admin
# 預設密碼: admin
```

## 目錄結構

```
data/       # 檔案儲存目錄
database/   # 設定資料庫
```

## 注意事項

- 首次登入後請立即修改預設密碼
- 可在設定中配置使用者權限
