# 防毒 Log 轉發設定說明

## 概述

本文件說明如何將 ClamAV 防毒偵測告警透過 **TCP 527** 埠轉發至資安中心 SOC 收集器 (`172.16.5.68`)。

## 架構

```
┌─────────────────┐      UDP/1514       ┌─────────────────┐      TCP/527        ┌─────────────────┐
│  Wazuh Manager  │ ──────────────────→  │  Syslog Relay   │ ──────────────────→  │  SOC Collector  │
│  (csyslogd)     │                      │  (socat)        │                      │  172.16.5.68    │
└─────────────────┘                      └─────────────────┘                      └─────────────────┘
```

**說明**：
- Wazuh Manager 的 `csyslogd` 模組負責將符合條件的告警以 syslog 格式輸出
- 因 `csyslogd` 僅支援 UDP 輸出，使用 `socat` 容器作為 UDP→TCP 協議轉換中繼
- 中繼容器接收 UDP syslog 後，透過 TCP 連線轉發至目標 SOC 收集器

## 轉發條件

僅轉發符合以下條件的告警：

| 篩選條件 | 值 | 說明 |
|----------|-----|------|
| group | `virus,clamav` | 包含病毒/ClamAV 相關告警群組 |

涵蓋的規則包括：
- Wazuh 內建 ClamAV 規則（52502-52508）
- 自訂 ClamAV 規則（100100-100130）
- 所有帶有 `virus` 或 `clamav` 群組標記的告警

## 設定檔案

### 1. Wazuh Manager 配置 (`config/wazuh-manager/ossec.conf`)

在 `<ossec_config>` 區塊內加入：

```xml
<!-- Syslog output: Forward ClamAV/antivirus alerts to SOC collector (172.16.5.68:527/TCP) -->
<!-- csyslogd sends UDP to syslog-relay container, which forwards via TCP -->
<syslog_output>
  <server>syslog-relay</server>
  <port>1514</port>
  <format>default</format>
  <group>virus,clamav,</group>
</syslog_output>
```

**參數說明**：

| 參數 | 值 | 說明 |
|------|-----|------|
| `server` | `syslog-relay` | Docker 網路內的中繼容器主機名 |
| `port` | `1514` | 中繼容器監聽埠 |
| `format` | `default` | 標準 syslog 格式（亦可改為 `json`） |
| `group` | `virus,clamav,` | 轉發的告警群組（須以逗號結尾） |

### 2. Syslog Relay 容器 (`docker-compose.yml`)

```yaml
syslog-relay:
  image: alpine/socat:latest
  container_name: soc-syslog-relay
  hostname: syslog-relay
  restart: unless-stopped
  command: UDP-LISTEN:1514,fork,reuseaddr TCP:172.16.5.68:527
  networks:
    - soc-network
  healthcheck:
    test: ["CMD-SHELL", "pgrep socat"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 5s
  deploy:
    resources:
      limits:
        memory: 64M
```

**參數說明**：

| socat 參數 | 說明 |
|------------|------|
| `UDP-LISTEN:1514` | 監聽 UDP 1514 埠接收來自 csyslogd 的告警 |
| `fork` | 為每個封包建立子進程處理（支援並行） |
| `reuseaddr` | 允許埠重複使用 |
| `TCP:172.16.5.68:527` | 以 TCP 方式轉發到目標 SOC 收集器 |

## 驗證步驟

### 1. 確認 csyslogd 運作

```bash
sudo docker exec soc-wazuh-manager /var/ossec/bin/wazuh-control status | grep csyslog
```

預期輸出：
```
wazuh-csyslogd is running...
```

### 2. 確認轉發目標

```bash
sudo docker exec soc-wazuh-manager cat /var/ossec/logs/ossec.log | grep -i "csyslog" | grep "Forwarding"
```

預期輸出：
```
wazuh-csyslogd: INFO: Forwarding alerts via syslog to: 'syslog-relay/172.20.0.x:1514'.
```

### 3. 確認 Relay 容器健康

```bash
sudo docker ps --format "table {{.Names}}\t{{.Status}}" | grep relay
```

預期輸出：
```
soc-syslog-relay    Up X minutes (healthy)
```

### 4. 測試連線（從 relay 容器）

```bash
sudo docker exec soc-syslog-relay nc -zv 172.16.5.68 527
```

## 變更目標位址

若需變更轉發目標：

1. 編輯 `docker-compose.yml` 中 `syslog-relay` 的 `command`：
   ```yaml
   command: UDP-LISTEN:1514,fork,reuseaddr TCP:<新IP>:<新PORT>
   ```

2. 重建容器：
   ```bash
   sudo docker compose up -d syslog-relay
   ```

## 變更轉發條件

若需變更哪些告警要轉發：

1. 編輯 `config/wazuh-manager/ossec.conf` 的 `<syslog_output>` 區塊
2. 同步到 bind mount：
   ```bash
   sudo cp config/wazuh-manager/ossec.conf data/manager/etc/ossec.conf
   sudo chown root:999 data/manager/etc/ossec.conf
   sudo chmod 660 data/manager/etc/ossec.conf
   ```
3. 重啟 Manager：
   ```bash
   sudo docker compose restart wazuh-manager
   ```

## 故障排除

| 問題 | 診斷方式 | 可能原因 |
|------|----------|----------|
| csyslogd 未運行 | `wazuh-control status` | ossec.conf 語法錯誤 |
| 告警未轉發 | 檢查 ossec.log | group 名稱錯誤或無符合告警 |
| relay 容器異常 | `docker logs soc-syslog-relay` | 目標不可達 |
| 目標拒絕連線 | `nc -zv 172.16.5.68 527` | 防火牆規則/服務未啟用 |

## 日期與版本

- **設定日期**：2026-05-29
- **Wazuh 版本**：4.14.5
- **Relay 映像**：alpine/socat:latest
