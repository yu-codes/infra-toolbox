# Redis Backup Service

Docker 化的 Redis 自動備份服務，提供排程備份、手動備份、備份還原和保留策略管理功能。

## 功能特點

- 🕐 **排程備份**: 支援 Cron 表達式設定自動備份時間
- 🔧 **手動備份**: 透過 API 觸發立即備份
- 🔄 **備份還原**: 從備份檔案還原 Redis 資料
- 🧹 **保留策略**: 自動清理過期備份，節省儲存空間
- 📊 **健康監控**: 提供健康檢查和 Prometheus 指標
- 🔔 **通知功能**: 支援 Slack、Email 等通知管道

## 快速開始

### 使用 Docker Compose

```bash
# 啟動服務
docker-compose up -d

# 查看日誌
docker-compose logs -f backup

# 停止服務
docker-compose down
```

### 環境變數配置

| 變數名 | 描述 | 預設值 |
|--------|------|--------|
| `REDIS_HOST` | Redis 主機位址 | `redis` |
| `REDIS_PORT` | Redis 連接埠 | `6379` |
| `REDIS_PASSWORD` | Redis 密碼 | - |
| `BACKUP_PATH` | 備份存儲路徑 | `/backups` |
| `BACKUP_SCHEDULE` | 備份排程 (Cron) | `0 2 * * *` |
| `RETENTION_DAYS` | 備份保留天數 | `7` |
| `MAX_BACKUPS` | 最大備份數量 | `30` |
| `MIN_BACKUPS` | 最小備份數量 | `3` |

## API 端點

### 備份操作

- `POST /api/v1/backup/trigger` - 觸發手動備份
- `GET /api/v1/backup/status/{task_id}` - 查詢備份任務狀態
- `GET /api/v1/backups` - 列出所有備份

### 還原操作

- `POST /api/v1/restore` - 執行備份還原
- `GET /api/v1/restore/status/{task_id}` - 查詢還原任務狀態

### 監控

- `GET /health` - 健康檢查
- `GET /metrics` - Prometheus 指標

## 文件

本服務使用 BDD-DDD-TDD 開發方法論建構，完整文件請參考：

- [BDD 規格](docs/BDD_SPEC.md) - 行為規格定義
- [DDD 設計](docs/DDD_DESIGN.md) - 領域驅動設計文件
- [TDD 測試](docs/TDD_DESIGN.md) - 測試驅動開發文件

## 開發

### 執行測試

```bash
# 進入容器執行測試
docker-compose exec backup pytest tests/ -v

# 或在本地執行
cd api
pytest tests/ -v --cov=src
```

### 專案結構

```
redis_backup/
├── docker-compose.yml
├── README.md
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── src/
│       ├── domain/           # 領域層
│       ├── application/      # 應用層
│       ├── infrastructure/   # 基礎設施層
│       └── api/              # API 層
├── scripts/
│   ├── backup.sh
│   └── restore.sh
└── docs/
    ├── BDD_SPEC.md
    ├── DDD_DESIGN.md
    └── TDD_DESIGN.md
```

## License

MIT
