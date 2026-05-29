# System SOC Stack — 安全監控系統部署驗證報告

| 項目 | 內容 |
|------|------|
| **文件編號** | SOC-AUDIT-20260528 |
| **報告日期** | 2026-05-28 |
| **系統名稱** | System SOC Stack（Wazuh SIEM + ClamAV） |
| **部署環境** | Ubuntu Linux 6.8.0-106-generic x86_64 |
| **執行人員** | 系統管理員 |
| **報告版本** | v1.0 |

---

## 1. 執行摘要

本次部署驗證作業針對 System SOC Stack 安全監控系統進行完整的啟動、配置檢查、功能驗證及健康監控。系統包含 Wazuh SIEM 4.14.5（日誌收集、事件關聯、威脅偵測）及 ClamAV 1.4.4（防毒掃描）兩大核心元件，透過 Docker Compose 容器化部署。

### 驗證結論

| 評估項目 | 狀態 |
|----------|------|
| 服務啟動 | ✅ 全部正常 |
| 安全配置 | ✅ 符合要求 |
| TLS 加密 | ✅ 已啟用 |
| 防毒偵測 | ✅ 功能正常 |
| 日誌收集 | ✅ 運作中 |
| 告警產生 | ✅ 已驗證 |
| 健康檢查 | ✅ 9/9 通過 |

---

## 2. 系統架構

### 2.1 元件清單

| 元件 | 版本 | 容器名稱 | 用途 |
|------|------|----------|------|
| Wazuh Indexer | 4.14.5 (OpenSearch 2.19.5) | soc-wazuh-indexer | 日誌索引與儲存 |
| Wazuh Manager | 4.14.5 | soc-wazuh-manager | SIEM 引擎、規則關聯、代理管理 |
| Wazuh Dashboard | 4.14.5 | soc-wazuh-dashboard | Web UI 告警視覺化 |
| Wazuh Agent | 4.14.5 | soc-wazuh-agent | 端點監控、日誌收集 |
| ClamAV | 1.4.4 | soc-clamav | 防毒引擎（clamd + freshclam） |
| ClamAV Scanner | 1.4.4 | soc-clamav-scanner | 排程全磁碟掃描（cron） |

### 2.2 資料流程

```
主機日誌 ──→ Wazuh Agent ──→ Wazuh Manager（規則引擎） ──→ Indexer ──→ Dashboard
                ↑
ClamAV 掃描 → scan.log ─┘
```

### 2.3 網路架構

| 服務 | 監聽埠 | 用途 |
|------|--------|------|
| Wazuh Indexer | 9200 | OpenSearch REST API |
| Wazuh Manager | 1514 | Agent 通訊 |
| Wazuh Manager | 1515 | Agent 註冊 |
| Wazuh Manager | 55000 | Wazuh REST API |
| Wazuh Dashboard | 5601 | Web 管理介面 |

所有服務間通訊均透過 Docker 內部網路 `soc-network`，僅必要埠對外暴露。

---

## 3. 安全配置驗證

### 3.1 TLS/SSL 配置

| 項目 | 配置 |
|------|------|
| 根憑證 | CN=SOC-Root-CA, OU=SOC, O=Infra, C=TW |
| 有效期限 | 2026-05-25 至 2036-05-22（10 年） |
| 協定版本 | TLSv1.2（強制） |
| 加密套件 | TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 |
|          | TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 |
|          | TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256 |
|          | TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 |
| 憑證用途 | Indexer、Manager(Filebeat)、Dashboard 各有獨立憑證 |

**評估**: TLS 配置符合業界標準，僅允許 TLSv1.2 及 AEAD 加密套件，禁用弱加密演算法。

### 3.2 認證與存取控制

| 項目 | 配置 |
|------|------|
| Indexer 認證 | OpenSearch Security Plugin（內部使用者 + RBAC） |
| API 認證 | Bearer Token（JWT，wazuh-wui 帳號） |
| Dashboard 認證 | 內建登入頁面 + Session Cookie |
| Agent 註冊 | 自動協商 SSL（ssl_auto_negotiate=yes） |
| API 密碼策略 | 符合 Wazuh 強度要求（大小寫 + 數字 + 特殊字元 + 最少 8 位） |

### 3.3 監控功能

| 功能模組 | 狀態 | 說明 |
|----------|------|------|
| FIM（檔案完整性監控） | ✅ 啟用 | 監控 /etc, /usr/bin, /usr/sbin 等關鍵路徑 |
| Rootcheck | ✅ 啟用 | Rootkit 偵測 |
| SCA（安全配置評估） | ✅ 啟用 | CIS Amazon Linux 2023 基準 |
| Vulnerability Detection | ✅ 啟用 | 軟體漏洞偵測 |
| Log Collection | ✅ 啟用 | syslog, auth.log, kern.log, dpkg.log |
| Syscollector | ✅ 啟用 | 系統硬體/軟體/網路清單 |

### 3.4 ClamAV 防毒配置

| 項目 | 設定值 |
|------|--------|
| 病毒庫版本 | 28013（2026-05-27 更新） |
| 自動更新頻率 | 每 2 小時（Checks 12） |
| 更新來源 | database.clamav.net |
| 排程掃描 | 每日凌晨 02:00（`0 2 * * *`） |
| 掃描範圍 | 全磁碟（`/scandir` = 主機根目錄） |
| 資源限制 | 最大記憶體 2GB |

### 3.5 自訂告警規則

系統已配置 ClamAV 相關自訂規則（規則 ID 100100-100130）：

| 規則 ID | 等級 | 說明 |
|---------|------|------|
| 100100 | 3 | ClamAV 掃描開始 |
| 100101 | 3 | ClamAV 掃描完成（無威脅） |
| 100110 | 7 | ClamAV 偵測到惡意軟體 |
| 100120 | 12 | ClamAV 偵測到多個威脅 |
| 100130 | 14 | ClamAV 掃描失敗 |

---

## 4. 健康檢查結果

### 4.1 容器狀態

執行時間：2026-05-28T04:20:00Z

| 容器名稱 | 狀態 | 啟動時間 |
|----------|------|----------|
| soc-wazuh-indexer | ✅ healthy | 2026-05-28T03:57:22Z |
| soc-wazuh-manager | ✅ healthy | 2026-05-28T03:57:35Z |
| soc-wazuh-dashboard | ✅ healthy | 2026-05-28T04:15:39Z |
| soc-wazuh-agent | ✅ healthy | 2026-05-28T03:57:48Z |
| soc-clamav | ✅ healthy | 2026-05-28T03:57:22Z |
| soc-clamav-scanner | ✅ healthy | 2026-05-28T04:18:13Z |

### 4.2 服務健康指標

| 檢查項目 | 結果 |
|----------|------|
| Indexer 叢集狀態 | ✅ GREEN（100% active shards） |
| Active Primary Shards | 23 |
| Active Shards | 23 |
| Unassigned Shards | 0 |
| ClamAV 病毒庫 | ✅ 最新（< 3 日） |
| 磁碟使用率 | ✅ 40%（正常） |

### 4.3 Wazuh Manager 服務

| 服務程序 | 狀態 |
|----------|------|
| wazuh-modulesd | ✅ running |
| wazuh-monitord | ✅ running |
| wazuh-logcollector | ✅ running |
| wazuh-remoted | ✅ running |
| wazuh-syscheckd | ✅ running |
| wazuh-analysisd | ✅ running |
| wazuh-execd | ✅ running |
| wazuh-db | ✅ running |
| wazuh-authd | ✅ running |
| wazuh-apid | ✅ running |

### 4.4 Wazuh Agent 狀態

| Agent ID | 名稱 | 狀態 | IP |
|----------|------|------|-----|
| 000 | wazuh-manager | ✅ active | 127.0.0.1 |
| 001 | soc-agent-01 | ✅ active | 172.20.0.6 |

---

## 5. 功能驗證測試

### 5.1 防毒偵測引擎驗證

| 測試項目 | 結果 |
|----------|------|
| ClamAV Daemon 運作 | ✅ PASS |
| 病毒庫自動更新 | ✅ PASS（freshclam 每 2 小時檢查） |
| Wazuh 告警鏈路 | ✅ PASS |

**詳細結果**:
- ClamAV daemon 回應正常（clamdscan --ping）
- 事件從 ClamAV → Agent → Manager → Indexer 完整鏈路驗證通過
- 防毒告警已設定轉發至 SOC 收集器（172.16.5.68:527/TCP）

### 5.2 日誌收集驗證

Agent 已確認收集以下日誌來源：

| 日誌來源 | 路徑 | 狀態 |
|----------|------|------|
| ClamAV clamd | /var/log/clamav/clamd.log | ✅ 分析中 |
| ClamAV freshclam | /var/log/clamav/freshclam.log | ✅ 分析中 |
| 系統日誌 | /host/var/log/syslog | ✅ 分析中 |
| 認證日誌 | /host/var/log/auth.log | ✅ 分析中 |
| 核心日誌 | /host/var/log/kern.log | ✅ 分析中 |
| 套件安裝 | /host/var/log/dpkg.log | ✅ 分析中 |

---

## 6. 合規性對應

### 6.1 資安框架對應

| 框架 | 控制項 | SOC Stack 對應 |
|------|--------|----------------|
| NIST CSF | ID.AM | Syscollector 資產盤點 |
| NIST CSF | PR.DS | FIM 檔案完整性監控 |
| NIST CSF | DE.CM | 持續監控（日誌、漏洞、入侵） |
| NIST CSF | DE.AE | 事件關聯與告警 |
| NIST CSF | RS.AN | Dashboard 事件分析 |
| ISO 27001 | A.12.4 | 日誌記錄與監控 |
| ISO 27001 | A.12.6 | 技術弱點管理（Vulnerability Detection） |
| ISO 27001 | A.12.2 | 防範惡意軟體（ClamAV） |
| PCI-DSS | 5.1 | 防毒軟體部署（ClamAV） |
| PCI-DSS | 10.2 | 安全事件日誌記錄 |
| PCI-DSS | 11.5 | 檔案完整性監控（FIM） |

---

## 7. 基礎設施資訊

| 項目 | 值 |
|------|-----|
| 作業系統 | Ubuntu Linux (kernel 6.8.0-106-generic) |
| Docker | 29.5.1 |
| Docker Compose | v5.1.3 |
| vm.max_map_count | 1048576（已配置，OpenSearch 必要） |
| 時區 | UTC+8 |

---

## 8. 已知限制與建議

### 8.1 目前限制

1. **單節點部署**: Indexer 為單節點，無副本（適合輕量環境）
2. **Agent 範圍**: 目前僅部署 1 個 containerized agent，若需監控更多主機需額外部署
3. **Dashboard 啟動時間**: Dashboard 完全啟動約需 60-90 秒

### 8.2 安全建議

1. **定期更新**: 建議每月檢查 Wazuh 及 ClamAV 更新
2. **密碼輪換**: 建議每 90 天更換 API 及管理密碼
3. **備份**: 建議定期備份 Indexer 資料（`./data/indexer`）
4. **憑證更新**: 根憑證有效期至 2036 年，各服務憑證需追蹤
5. **告警通知**: 建議整合郵件或 Webhook 告警通知機制

---

## 9. 結論

System SOC Stack 安全監控系統已成功部署並通過全面驗證。所有核心功能（SIEM 日誌收集、事件關聯、防毒掃描、告警產生、Web 視覺化）均運作正常。系統配置符合安全最佳實踐，包括 TLS 加密通訊、強密碼策略、RBAC 存取控制等。

系統支援一鍵啟動（`sudo docker compose up -d`）與一鍵關閉（`sudo docker compose down`），並內建健康檢查腳本供日常監控使用。

---

**報告結束**

| 審核 | 簽章 | 日期 |
|------|------|------|
| 製表人 |  | 2026-05-28 |
| 審核人 |  |  |
| 核准人 |  |  |
