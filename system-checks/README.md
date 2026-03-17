# System Checks 系統檢查工具

本目錄包含一系列用於 Linux 系統維護和監控的 Bash 腳本。

## 適用作業系統

- **Ubuntu** (20.04 LTS 及以上)
- **Debian** (11 及以上)
- 其他基於 Debian/APT 的 Linux 發行版

> ⚠️ 注意：這些腳本需要 `sudo` 權限執行

## 包含的腳本

### 1. `check_apt.sh` - APT 套件升級診斷

**功能：**
- 更新套件索引
- 執行升級前的模擬測試（不改動系統）
- 實際執行系統升級
- 自動清理不必要的套件
- 檢查是否需要重開機
- 顯示磁碟使用量

**使用方式：**
```bash
bash check_apt.sh [log_directory]
```

**範例：**
```bash
bash check_apt.sh ./logs  # 日誌存放於 ./logs 目錄
```

---

### 2. `check_cve.sh` - CVE 漏洞檢查與修補

**功能：**
- 檢測 Ubuntu Pro 附加狀態
- 取得系統安全狀態（文字和 JSON 格式）
- 列出待修補的安全更新
- 收集受影響套件的 Changelog（包含 CVE/USN 資訊）
- 自動執行安全更新
  - 若有 Ubuntu Pro：使用 Pro 路線（含 ESM 支援）
  - 若無：使用標準版自動修補
- 更新後再次檢查安全狀態

**輸出文件：**
- 文字日誌：`cve_check_TIMESTAMP.txt`
- JSON 狀態：`cve_status_TIMESTAMP.json`（修補前後各一份）
- Changelog 目錄：`changelogs_TIMESTAMP/`（最多 10 個套件）

**使用方式：**
```bash
bash check_cve.sh [log_directory]
```

**範例：**
```bash
bash check_cve.sh ./logs  # 日誌存放於 ./logs 目錄
```

---

### 3. `check_hosts.sh` - 主機連線檢測

**功能：**
- 從 `hosts.txt` 檔案讀取主機和連接埠
- 使用 `nc`（netcat）測試 TCP 連線
- 逐行輸出每個主機的連線狀態

**依賴：**
- `nc`（netcat）工具，通常預裝在 Ubuntu/Debian 上

**使用方式：**
```bash
bash check_hosts.sh
```

**hosts.txt 格式：**
```
example.com 80
192.168.1.100 443
# 這是註解，會被跳過
database.local 5432
```

**輸出範例：**
```
測試結果：
Host:Port => 狀態
example.com:80 => 可連
192.168.1.100:443 => 無法連
```

---

## 快速開始

1. **準備執行環境：**
   ```bash
   cd system-checks
   chmod +x *.sh  # 給予執行權限
   ```

2. **執行檢查（範例）：**
   ```bash
   # 系統升級診斷
   bash check_apt.sh
   
   # CVE 漏洞檢查（需 sudo）
   sudo bash check_cve.sh
   
   # 主機連線檢測（需準備 hosts.txt）
   bash check_hosts.sh
   ```

---

## 日誌與報告

大多數腳本會將執行結果存放在 `logs/` 目錄：

```
logs/
├── upgrade_YYYYMMDD_HHMMSS.txt          # check_apt.sh 日誌
├── cve_check_YYYYMMDD_HHMMSS.txt        # check_cve.sh 日誌
├── cve_status_YYYYMMDD_HHMMSS.json      # CVE 修補前狀態
├── cve_status_YYYYMMDD_HHMMSS_after.json # CVE 修補後狀態
└── changelogs_YYYYMMDD_HHMMSS/          # 套件 Changelog 目錄
    ├── package1.changelog
    ├── package2.changelog
    └── ...
```

---

## 權限要求

| 腳本 | 需要 sudo | 描述 |
|------|----------|------|
| `check_apt.sh` | ✅ 是 | 涉及系統套件更新 |
| `check_cve.sh` | ✅ 是 | 涉及安全更新和系統修改 |
| `check_hosts.sh` | ❌ 否 | 僅測試網路連線 |

---

## 故障排除

### check_cve.sh 提示找不到 ubuntu-security-status

**解決方案：**
```bash
sudo apt update
sudo apt install -y ubuntu-security-status
```

### check_hosts.sh 提示找不到 nc

**解決方案：**
```bash
sudo apt update
sudo apt install -y netcat-openbsd  # 或 netcat
```

### hosts.txt 檔案不存在

**解決方案：** 在 `check_hosts.sh` 同目錄建立 `hosts.txt`，格式如上述範例。

---

## 建議使用場景

- **日常維護：** 每週或每月執行 `check_apt.sh` 保持系統更新
- **安全運維：** 使用 `check_cve.sh` 定期檢查和修補 CVE 漏洞
- **監控：** 定期執行 `check_hosts.sh` 確保關鍵服務可達性
- **自動化：** 藉由 cron job 自動化上述檢查

**cron 範例：**
```bash
# 每週日凌晨 2 點執行安全檢查
0 2 * * 0 cd /path/to/system-checks && sudo bash check_cve.sh

# 每天晚上 10 點執行主機連線檢測
0 22 * * * cd /path/to/system-checks && bash check_hosts.sh
```
