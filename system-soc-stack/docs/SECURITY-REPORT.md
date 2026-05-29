# SOC 資安報告流程

本文件說明 SOC Stack 啟動後，如何截圖並產出資安報告給管理員。

## 一、啟動後驗證清單

服務啟動完成後（`docker compose ps` 所有服務顯示 healthy），依序進行以下驗證並截圖：

### Step 1：確認所有服務健康

```bash
docker compose ps
```

**截圖要求**：顯示所有容器狀態為 `healthy` 或 `Up`。

### Step 2：登入 Wazuh Dashboard

1. 開啟瀏覽器，前往 `https://<伺服器IP>:5601`
2. 接受自簽憑證警告
3. 使用帳號 `admin` / 密碼 `admin`（或 `.env` 中設定的密碼）登入

**截圖要求**：登入後的首頁（顯示 Agent 連線狀態）。

### Step 3：確認 Agent 已連線

1. Dashboard 左側選單 → **Agents**
2. 確認 `soc-agent-01` 狀態為 **Active**

**截圖要求**：Agent 列表頁面，顯示代理已上線。

### Step 4：確認安全事件正在接收

1. Dashboard 左側選單 → **Security events**
2. 確認有事件資料流入（首次啟動後可能需等 5-10 分鐘）

**截圖要求**：Security Events 頁面，顯示有事件記錄。

### Step 5：確認防毒偵測能力

驗證 ClamAV 防毒引擎運作正常：

```bash
sudo docker exec soc-clamav clamdscan --ping 1
```

**截圖要求**：
1. 終端顯示 ClamAV daemon 回應正常
2. Dashboard → Security events 中確認有 ClamAV 相關告警

### Step 6：確認弱點掃描

1. Dashboard 左側選單 → **Vulnerabilities**
2. 確認弱點掃描引擎已啟動且有掃描結果

**截圖要求**：弱點掃描頁面。

### Step 7：確認檔案完整性監控 (FIM)

1. Dashboard 左側選單 → **Integrity monitoring**
2. 確認 FIM 已啟動掃描

**截圖要求**：FIM 頁面。

---

## 二、報告範本

將上述截圖整理為報告，建議格式：

```
═══════════════════════════════════════════
SOC Stack 部署驗證報告
═══════════════════════════════════════════

日期：YYYY-MM-DD
伺服器：<hostname / IP>
負責人：<姓名>

─── 驗證項目 ────────────────────────────

1. [✓] 所有服務正常運行     (截圖 1)
2. [✓] Dashboard 可登入     (截圖 2)
3. [✓] Agent 已連線         (截圖 3)
4. [✓] 安全事件接收正常     (截圖 4)
5. [✓] 防毒偵測功能正常     (截圖 5)
6. [✓] 弱點掃描已啟動       (截圖 6)
7. [✓] 檔案完整性監控已啟動 (截圖 7)

─── 結論 ────────────────────────────────

SOC Stack 已成功部署並驗證所有核心功能正常運作。
系統目前正在監控：
- 系統日誌事件
- 惡意程式偵測
- 已知弱點
- 檔案異動

═══════════════════════════════════════════
```

---

## 三、定期報告（建議每週）

每週可產出以下報告：

### 3.1 快速健康報告

```bash
./scripts/health-check.sh --json > report_$(date +%Y%m%d).json
```

### 3.2 Dashboard 匯出 PDF

Wazuh Dashboard 支援報告匯出：

1. 進入任一模組頁面（如 Security events）
2. 設定時間範圍（如「過去 7 天」）
3. 點選右上角 **Generate report** 按鈕
4. 等待 PDF 產生後下載

### 3.3 手動掃描報告

```bash
# 觸發即時全碟掃描
docker exec soc-clamav-scanner /scripts/clamav-scan.sh

# 查看掃描結果
docker exec soc-clamav-scanner cat /var/log/clamav/scan.log | tail -20
```

---

## 四、告警通知設定（選配）

如需即時通知，可在 Wazuh Manager 的 ossec.conf 中啟用 Email 告警：

```xml
<global>
  <email_notification>yes</email_notification>
  <smtp_server>smtp.your-domain.com</smtp_server>
  <email_from>soc@your-domain.com</email_from>
  <email_to>security-admin@your-domain.com</email_to>
</global>
```

或整合 Slack / Teams webhook（透過 Wazuh Active Response 或 Integration 模組）。

---

## 五、截圖工具建議

| 方式 | 適用場景 |
|------|----------|
| `gnome-screenshot` | Ubuntu Desktop |
| `scrot` | Ubuntu Server + X11 |
| 瀏覽器 F12 → Screenshot | Dashboard 頁面 |
| `curl + jq` | API 驗證截圖（終端） |

如果是 headless 伺服器（無 GUI），建議：
- 從本地電腦瀏覽器連入 Dashboard 進行截圖
- 或使用 `./scripts/health-check.sh` 的文字輸出作為證據
