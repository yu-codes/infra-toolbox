# System SOC Stack — 操作手冊

## 概述

System SOC Stack 是基於 Docker Compose 的輕量級 SOC（安全運營中心）解決方案，整合 Wazuh SIEM 與 ClamAV 防毒引擎，提供完整的安全監控能力。

---

## 前置需求

| 項目 | 要求 |
|------|------|
| Docker | ≥ 24.0 |
| Docker Compose | ≥ v2.20 |
| 記憶體 | ≥ 8 GB（建議 16 GB） |
| 磁碟空間 | ≥ 20 GB |
| vm.max_map_count | ≥ 262144（OpenSearch 需求） |
| sudo 權限 | 必要（若使用者不在 docker group） |

### 檢查前置條件

```bash
# 檢查 Docker
docker --version
docker compose version

# 檢查 vm.max_map_count（必須 ≥ 262144）
sysctl vm.max_map_count

# 若需調整（臨時）
sudo sysctl -w vm.max_map_count=1048576

# 永久設定
echo "vm.max_map_count=1048576" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 一鍵啟動

```bash
cd /path/to/agrres-services/system-soc-stack

# 啟動所有服務
sudo docker compose up -d
```

**啟動順序（自動處理）**:
1. Wazuh Indexer（等待 healthy）
2. ClamAV（等待 healthy）
3. Indexer Init（一次性初始化）
4. ClamAV Scanner（排程掃描）
5. Wazuh Manager（等待 healthy）
6. Wazuh Agent
7. Wazuh Dashboard

**預期啟動時間**: 約 30-90 秒（Dashboard 啟動最慢）

---

## 一鍵關閉

```bash
cd /path/to/agrres-services/system-soc-stack

# 停止所有服務（保留資料）
sudo docker compose down

# 停止並刪除所有資料（完全重置）
sudo docker compose down -v
```

> ⚠️ `down -v` 會刪除 Wazuh Manager 的 named volumes，所有 agent 註冊、規則狀態將遺失。

---

## 健康檢查

### 快速檢查

```bash
sudo bash scripts/health-check.sh
```

### 詳細輸出

```bash
sudo bash scripts/health-check.sh --verbose
```

### JSON 格式（適合自動化）

```bash
sudo bash scripts/health-check.sh --json
```

**預期結果**: `Overall: healthy (healthy:9 warnings:0 unhealthy:0)`

### 手動驗證各元件

```bash
# 容器狀態
sudo docker ps --format "table {{.Names}}\t{{.Status}}" | grep soc

# Indexer 叢集
sudo curl -sku "admin:admin" "https://localhost:9200/_cluster/health?pretty"

# Wazuh API
TOKEN=$(sudo curl -sku "wazuh-wui:Wazuh@S0c2026!" -X POST \
  "https://localhost:55000/security/user/authenticate" 2>/dev/null | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")
sudo curl -sk -H "Authorization: Bearer $TOKEN" "https://localhost:55000/agents?pretty=true"

# ClamAV
sudo docker exec soc-clamav clamscan --version
sudo docker exec soc-clamav clamdscan --ping 1

# Dashboard（瀏覽器）
# https://localhost:5601  (admin / admin)
```

---

## 產生安全報告

安全審計報告位於 `docs/SECURITY_AUDIT_REPORT.md`。

### 更新報告流程

1. 確認服務全部啟動且健康：
   ```bash
   sudo bash scripts/health-check.sh --verbose
   ```

2. 收集系統狀態資訊（用於更新報告內容）：
   ```bash
   # 健康檢查 JSON
   sudo bash scripts/health-check.sh --json | python3 -m json.tool

   # Wazuh 版本
   sudo curl -sku "admin:admin" "https://localhost:9200" 2>&1

   # ClamAV 版本及病毒庫
   sudo docker exec soc-clamav clamscan --version

   # 憑證有效期
   openssl x509 -in certs/root-ca.pem -noout -subject -dates
   ```

4. 更新 `docs/SECURITY_AUDIT_REPORT.md` 中的日期及驗證結果

---

## 日常維運

### 查看告警

```bash
# 最新 10 筆告警
sudo docker exec soc-wazuh-manager tail -10 /var/ossec/logs/alerts/alerts.json | python3 -m json.tool

# 搜尋特定關鍵字
sudo docker exec soc-wazuh-manager grep -i "malware\|clamav" /var/ossec/logs/alerts/alerts.json | tail -5
```

### 手動觸發 ClamAV 掃描

```bash
sudo docker exec soc-clamav-scanner /scripts/clamav-scan.sh
```

### 查看掃描結果

```bash
sudo docker exec soc-clamav-scanner cat /var/log/clamav/scan.log
```

### 重啟單一服務

```bash
sudo docker compose restart <service-name>
# 例如: sudo docker compose restart wazuh-dashboard
```

---

## 故障排除

### Dashboard 啟動緩慢（503）

Dashboard 正常啟動需 60-90 秒，此期間回傳 503。等待 healthcheck 通過即可。

```bash
# 檢查啟動進度
sudo docker logs --tail 5 soc-wazuh-dashboard
```

### ClamAV 病毒庫過期

```bash
# 檢查病毒庫更新時間
sudo docker exec soc-clamav ls -la /var/lib/clamav/*.cvd

# 手動觸發更新
sudo docker exec soc-clamav freshclam
```

### Agent 無法連線

```bash
# 檢查 Agent 狀態
sudo docker exec soc-wazuh-agent /var/ossec/bin/wazuh-control status

# 檢查 Agent 日誌
sudo docker logs --tail 20 soc-wazuh-agent

# 重新註冊（需重建 Agent）
sudo docker compose up -d --force-recreate wazuh-agent
```

### Indexer 記憶體不足

```bash
# 調整 .env 中的 INDEXER_HEAP（預設 512m）
# 修改後重啟
sudo docker compose up -d --force-recreate wazuh-indexer
```

---

## 配置檔案結構

```
system-soc-stack/
├── docker-compose.yml          # 主部署檔
├── .env                        # 環境變數配置
├── config/
│   ├── clamav/
│   │   ├── clamd.conf          # ClamAV daemon 配置
│   │   └── freshclam.conf      # 病毒庫更新配置
│   ├── wazuh-manager/
│   │   ├── ossec.conf          # Manager 主配置
│   │   └── rules/
│   │       └── clamav_rules.xml # 自訂 ClamAV 規則
│   ├── wazuh-agent/
│   │   └── ossec.conf          # Agent 監控配置
│   ├── wazuh-indexer/
│   │   └── opensearch.yml      # OpenSearch 配置
│   └── wazuh-dashboard/
│       └── opensearch_dashboards.yml
├── certs/                      # TLS 憑證
├── scripts/
│   ├── generate-certs.sh       # 產生憑證
│   ├── health-check.sh         # 健康檢查
│   └── clamav-scan.sh          # ClamAV 掃描腳本
├── data/                       # 持久化資料（自動產生）
│   ├── indexer/
│   ├── clamav-db/
│   ├── clamav-logs/
│   └── dashboard/
└── docs/
    ├── OPERATIONS.md           # 本文件
    └── SECURITY_AUDIT_REPORT.md
```

---

## 完整操作流程（SOP）

### 首次部署

1. 確認前置條件（Docker、vm.max_map_count）
2. 產生 TLS 憑證：`sudo bash scripts/generate-certs.sh`
3. 啟動：`sudo docker compose up -d`
4. 等待所有服務 healthy：`sudo docker ps | grep soc`
5. 驗證健康：`sudo bash scripts/health-check.sh --verbose`
6. 登入 Dashboard 確認：`https://localhost:5601`

### 定期維護（每月）

1. 健康檢查：`sudo bash scripts/health-check.sh --verbose`
2. 確認病毒庫最新：`sudo docker exec soc-clamav clamscan --version`
3. 檢查磁碟使用量
4. 檢視告警趨勢（Dashboard）
5. 更新審計報告

### 緊急停機

```bash
sudo docker compose down
```

### 緊急重啟

```bash
sudo docker compose down && sudo docker compose up -d
```
