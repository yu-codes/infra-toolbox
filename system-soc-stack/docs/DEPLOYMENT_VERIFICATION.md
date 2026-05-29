# 安全監控系統部署驗證報告

## 驗證資訊

| 項目 | 內容 |
|------|------|
| **系統名稱** | 安全監控系統 (Wazuh SIEM 4.14.5 + ClamAV) |
| **部署日期** | [部署日期] |
| **部署人員** | [部署人員姓名] |
| **伺服器環境** | [伺服器主機名/IP] |
| **驗證日期** | [驗證日期] |
| **驗證人員** | [驗證人員姓名] |

---

## 部署驗證清單

### 1. 前置環境驗證

```bash
# Docker 版本檢查
docker --version
# 預期結果: Docker version 24+

# Docker Compose 版本檢查
docker compose version
# 預期結果: Docker Compose version v2+

# 系統參數檢查
sysctl vm.max_map_count
# 預期結果: vm.max_map_count >= 262144
```

**驗證結果：** [ ] 通過 [ ] 未通過

---

### 2. 容器運行狀態驗證

**命令：**
```bash
docker compose ps
```

**預期結果：** 所有容器狀態為 `healthy` 或 `Up`

**容器列表：**

| 容器名稱 | 狀態 | 啟動時間 | 說明 |
|---------|------|---------|------|
| soc-wazuh-indexer | [ ] | [ ] | OpenSearch 索引引擎 |
| soc-wazuh-manager | [ ] | [ ] | Wazuh SIEM 核心引擎 |
| soc-wazuh-dashboard | [ ] | [ ] | Web 儀表板 |
| soc-wazuh-agent | [ ] | [ ] | 日誌收集代理 |
| soc-clamav | [ ] | [ ] | ClamAV 掃描引擎 |
| soc-clamav-scanner | [ ] | [ ] | 排程掃描器 |

**驗證結果：** [ ] 通過 [ ] 未通過

---

### 3. 服務健康檢查驗證

**命令：**
```bash
bash scripts/health-check.sh
```

**預期結果：** `Overall: healthy`

**檢查項目：**
- [ ] Wazuh Indexer: healthy
- [ ] Wazuh Manager: healthy
- [ ] Wazuh Dashboard: healthy
- [ ] Wazuh Agent: healthy
- [ ] ClamAV Daemon: healthy
- [ ] ClamAV DB: up to date
- [ ] Disk usage: normal

**驗證結果：** [ ] 通過 [ ] 未通過

---

### 4. Dashboard 訪問驗證

**訪問地址：** https://[伺服器IP或主機名]:5601

**登入測試：**
- [ ] Dashboard 可訪問
- [ ] 能正常登入（帳號: admin）
- [ ] 首頁加載完成
- [ ] 能查看代理連線狀態

**驗證結果：** [ ] 通過 [ ] 未通過

---

### 5. 代理連線驗證

**Dashboard 操作：**
1. 左側選單 → **Agents**
2. 查看代理連線狀況

**預期結果：** 至少 1 個代理顯示 **Active** 狀態

**代理列表：**

| 代理名稱 | 狀態 | 版本 | 連線時間 |
|---------|------|------|---------|
| soc-agent-01 | [ ] Active | [ ] | [ ] |

**驗證結果：** [ ] 通過 [ ] 未通過

---

### 6. 安全事件接收驗證

**Dashboard 操作：**
1. 左側選單 → **Security events**
2. 查看事件流入狀況

**預期結果：** 有事件記錄流入，支持即時查看

**驗證項目：**
- [ ] 能進入 Security events 頁面
- [ ] 有事件資料流入
- [ ] 能查看事件詳情
- [ ] 能進行事件搜尋

**驗證結果：** [ ] 通過 [ ] 未通過

---

### 7. 防毒掃描驗證

**命令：**
```bash
bash scripts/test-eicar.sh
```

**預期結果：** `[PASS] EICAR detected`

**驗證項目：**
- [ ] EICAR 測試檔案創建成功
- [ ] ClamAV 正確偵測到測試檔案
- [ ] Dashboard 中出現相應告警
- [ ] 告警資訊完整

**驗證結果：** [ ] 通過 [ ] 未通過

---

### 8. 日誌生成驗證

**命令：**
```bash
# 查看 Wazuh Manager 日誌
docker compose logs wazuh-manager --tail 30

# 查看 ClamAV 日誌
docker compose logs clamav --tail 30

# 查看 Dashboard 日誌
docker compose logs wazuh-dashboard --tail 30
```

**預期結果：** 各服務日誌正常生成，無錯誤

**驗證項目：**
- [ ] Wazuh Manager 日誌正常
- [ ] ClamAV 日誌正常
- [ ] Dashboard 日誌正常
- [ ] 無關鍵錯誤訊息

**驗證結果：** [ ] 通過 [ ] 未通過

---

## 整體部署驗證結果

**總體狀態：**

| 驗證項目 | 結果 |
|---------|------|
| 前置環境 | [ ] 通過 [ ] 未通過 |
| 容器運行 | [ ] 通過 [ ] 未通過 |
| 健康檢查 | [ ] 通過 [ ] 未通過 |
| Dashboard 訪問 | [ ] 通過 [ ] 未通過 |
| 代理連線 | [ ] 通過 [ ] 未通過 |
| 事件接收 | [ ] 通過 [ ] 未通過 |
| 防毒掃描 | [ ] 通過 [ ] 未通過 |
| 日誌生成 | [ ] 通過 [ ] 未通過 |

**最終驗證結果：** [ ] **全部通過** [ ] **部分通過** [ ] **未通過**

---

## 部署後的後續步驟

### 立即行動

- [ ] 修改 Dashboard 默認密碼 (admin/admin)
- [ ] 配置告警通知（郵件/Slack/Teams）
- [ ] 設置備份策略
- [ ] 配置日誌保留期限

### 定期維護

- [ ] 每周檢查 Dashboard 告警摘要
- [ ] 每月生成安全報告
- [ ] 定期更新病毒庫和系統補丁
- [ ] 定期備份配置和數據

### 監控要點

- [ ] 建立告警響應流程
- [ ] 設定關鍵告警的自動通知
- [ ] 定期進行安全演練
- [ ] 維護操作日誌記錄

---

## 簽名確認

**部署人員簽名：** __________________________ 日期：__________

**驗證人員簽名：** __________________________ 日期：__________

**資安主管簽名：** __________________________ 日期：__________

---

## 附錄：故障排除指南

### 容器無法啟動

**檢查步驟：**
```bash
# 查看容器日誌
docker compose logs

# 檢查系統參數
sysctl vm.max_map_count

# 重新啟動服務
docker compose down
docker compose up -d
```

### Dashboard 無法訪問

**檢查步驟：**
```bash
# 查看 Dashboard 容器狀態
docker compose ps | grep dashboard

# 查看 Dashboard 日誌
docker compose logs wazuh-dashboard

# 檢查網絡連接
curl -k https://localhost:5601
```

### 代理無法連線

**檢查步驟：**
```bash
# 查看 Manager 日誌
docker compose logs wazuh-manager | grep agent

# 查看 Agent 日誌
docker compose logs wazuh-agent
```

### 防毒掃描失敗

**檢查步驟：**
```bash
# 查看 ClamAV 日誌
docker compose logs clamav

# 檢查病毒庫狀態
docker exec soc-clamav clamscan --version

# 手動更新病毒庫
docker exec soc-clamav freshclam
```

---

*報告終止*  
*此報告應妥善保管，作為部署驗證的正式紀錄*