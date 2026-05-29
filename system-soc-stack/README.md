# System SOC Stack

Lightweight SOC (Security Operations Center) — 基於 Wazuh SIEM + ClamAV 防毒 一鍵部署

## 功能

- **SIEM 日誌關聯**：Wazuh Manager 即時分析系統事件，觸發告警
- **防毒掃描**：ClamAV 每日全碟掃描，偵測惡意程式
- **檔案完整性監控 (FIM)**：偵測關鍵系統檔案異動
- **弱點掃描**：自動偵測已知 CVE 漏洞
- **Web 儀表板**：Wazuh Dashboard 視覺化所有安全事件
- **自動病毒碼更新**：freshclam 每 2 小時自動更新

## 系統需求

- Ubuntu 20.04+ (建議 22.04 LTS)
- Docker Engine 24+ & Docker Compose v2
- RAM: 至少 4GB (建議 8GB)
- Disk: 至少 20GB 可用空間
- `vm.max_map_count >= 262144`

## 快速啟動

```bash
# 1. 設定系統參數 (OpenSearch 必要)
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf

# 2. 產生 TLS 憑證
./scripts/generate-certs.sh

# 3. 建立環境設定
cp .env.example .env

# 4. 一鍵啟動
docker compose up -d
```

首次啟動約需 5-8 分鐘（ClamAV 需下載病毒資料庫）。啟動完成後：

- **Dashboard**: https://localhost:5601
- **帳號/密碼**: admin / admin

## 目錄結構

```
system-soc-stack/
├── docker-compose.yml          # 主部署檔（所有服務定義在此）
├── .env.example                # 環境變數範本
├── .env                        # 實際環境變數（不入版控）
├── .gitattributes              # 確保 config 使用 LF 換行
│
├── config/                     # 各服務的設定檔
│   ├── clamav/                 # ClamAV 防毒設定
│   │   ├── clamd.conf          #   掃描引擎設定（掃描限制、Socket 路徑）
│   │   └── freshclam.conf      #   病毒碼更新設定（更新頻率、鏡像）
│   ├── wazuh-indexer/          # OpenSearch 索引引擎設定
│   │   ├── opensearch.yml      #   叢集、TLS、安全插件設定
│   │   └── internal_users.yml  #   內部使用者帳號與密碼雜湊
│   ├── wazuh-manager/          # Wazuh SIEM 引擎設定
│   │   ├── ossec.conf          #   主設定（日誌收集、FIM、告警規則）
│   │   └── rules/
│   │       └── clamav_rules.xml  # ClamAV 告警規則（偵測病毒事件）
│   ├── wazuh-dashboard/        # Web 儀表板設定
│   │   └── opensearch_dashboards.yml  # Dashboard 連線與 TLS 設定
│   └── wazuh-agent/            # 端點代理設定
│       └── ossec.conf          #   代理連線、監控的日誌路徑
│
├── certs/                      # TLS 憑證（由 generate-certs.sh 產生）
│   ├── root-ca.pem             #   Root CA 公鑰
│   ├── root-ca-key.pem         #   Root CA 私鑰
│   ├── admin.pem / admin-key.pem         # 管理憑證
│   ├── indexer.pem / indexer-key.pem     # Indexer 服務憑證
│   ├── manager.pem / manager-key.pem    # Manager 服務憑證
│   └── dashboard.pem / dashboard-key.pem # Dashboard 服務憑證
│
├── data/                       # 所有持久化資料（自動建立）
│   ├── indexer/                #   OpenSearch 索引資料
│   ├── manager/                #   Wazuh Manager 狀態、日誌、佇列
│   ├── dashboard/              #   Dashboard saved objects
│   ├── clamav-db/              #   ClamAV 病毒碼資料庫
│   └── clamav-logs/            #   ClamAV 掃描日誌（Agent 讀取此路徑）
│
├── scripts/                    # 操作腳本
│   ├── generate-certs.sh       #   產生所有 TLS 憑證
│   ├── clamav-scan.sh          #   排程掃描腳本（由 clamav-scanner 容器執行）
│   └── health-check.sh         #   檢查所有服務健康狀態
```

## 服務架構

```
┌─────────────────────────────────────────────────────────────┐
│                        Host (Ubuntu)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────┐    │
│  │  ClamAV  │───▶│ Wazuh Agent  │───▶│ Wazuh Manager  │    │
│  │ (掃描)   │log │ (收集日誌)    │    │ (規則比對)      │    │
│  └──────────┘    └──────────────┘    └───────┬────────┘    │
│                                              │             │
│  ┌──────────────┐                   ┌────────▼────────┐    │
│  │   Dashboard  │◀──────────────────│  Wazuh Indexer  │    │
│  │ (視覺化 UI)  │                   │  (儲存告警)      │    │
│  └──────────────┘                   └─────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 常用操作

```bash
# 查看服務狀態
docker compose ps

# 查看即時日誌
docker compose logs -f wazuh-manager

# 手動觸發病毒掃描
docker exec soc-clamav-scanner /scripts/clamav-scan.sh

# 健康檢查
./scripts/health-check.sh

# 停止所有服務
docker compose down

# 完全清除（含資料）
docker compose down && rm -rf data/
```

## 告警等級

| Level | 意義 | 範例 |
|-------|------|------|
| 3 | 資訊 | 掃描完成、病毒碼更新 |
| 7 | 中 | 掃描錯誤、更新失敗 |
| 12 | 高 | 偵測到惡意程式 |
| 14 | 嚴重 | 5 分鐘內多次偵測（疑似爆發） |

## 注意事項

- 首次啟動 ClamAV 需下載 ~300MB 病毒碼，請確保網路暢通
- `vm.max_map_count` 必須設定，否則 OpenSearch 無法啟動
- 生產環境請務必修改 `.env` 中的所有預設密碼
- `certs/` 目錄中的憑證有效期 10 年，建議定期更換

## 文件

- [操作手冊](docs/OPERATIONS.md) — 完整的啟停流程、健康檢查、故障排除
- [安全審計報告](docs/SECURITY_AUDIT_REPORT.md) — 部署驗證報告（供稽核審查）
