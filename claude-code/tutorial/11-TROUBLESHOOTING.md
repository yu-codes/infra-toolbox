# 11 — 疑難排解

遇到問題時的快速診斷和解決指南。

## 快速診斷

```bash
# 第一步：使用內建完整診斷
claude doctor

# 或在互動模式中
> /doctor

# 會檢查：
# ✓ 安裝類型、版本、搜尋功能
# ✓ 自動更新狀態
# ✓ 設定檔語法（JSON 格式、類型錯誤）
# ✓ MCP 伺服器設定
# ✓ 鍵位綁定
# ✓ 上下文警告（CLAUDE.md 過大、MCP token 用量、不可達的權限規則）
# ✓ Plugin 和 Agent 載入錯誤
```

## 安裝與啟動問題

### 問題：`claude: command not found`

不同平台的錯誤訊息：

| 平台 | 錯誤訊息 |
|------|---------|
| macOS | `zsh: command not found: claude` |
| Linux | `bash: claude: command not found` |
| Windows CMD | `'claude' is not recognized as an internal or external command` |
| PowerShell | `claude : The term 'claude' is not recognized` |

**macOS 解方：**
```bash
echo $PATH | tr ':' '\n' | grep local/bin
# 若無輸出，手動加入
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Linux 解方：**
```bash
echo $PATH | tr ':' '\n' | grep local/bin
# 若無輸出，手動加入
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Windows PowerShell 解方：**
```powershell
$env:PATH -split ';' | Select-String 'local\\bin'
# 若無輸出，手動加入
[System.Environment]::SetEnvironmentVariable("PATH", "$env:USERPROFILE\.local\bin;$env:PATH", "User")
# 重啟終端
```

### 問題：安裝腳本下載失敗

**所有平台 — 確認網路連通：**
```bash
curl -sI https://storage.googleapis.com
```

如果失敗，使用替代安裝方式：

**macOS / Linux：**
```bash
brew install --cask claude-code
```

**Windows：**
```powershell
winget install Anthropic.ClaudeCode
```

### 問題：TLS / SSL 錯誤

**Ubuntu / Debian：**
```bash
sudo apt-get update && sudo apt-get install ca-certificates
```

**macOS：**
```bash
brew install ca-certificates
```

**Windows PowerShell（啟用 TLS 1.2）：**
```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
irm https://claude.ai/install.ps1 | iex
```

**企業代理 CA 憑證：**
```bash
# macOS / Linux
export NODE_EXTRA_CA_CERTS="/path/to/corporate-ca.pem"

# Windows PowerShell
$env:NODE_EXTRA_CA_CERTS = "C:\certs\corporate-ca.pem"
```

### 問題：Windows "requires git-bash"

```powershell
# 安裝 Git for Windows
# 下載：https://git-scm.com/downloads/win

# 若已安裝但找不到，手動指定路徑
# 在 settings.json 中加入：
```
```json
{
  "env": {
    "CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe"
  }
}
```

### 問題：Linux 低記憶體伺服器安裝被 Killed

```bash
# 建立 2GB swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 重試安裝
curl -fsSL https://claude.ai/install.sh | bash
```

### 問題：Linux 架構不符（Illegal instruction）

```bash
# 檢查架構
uname -m  # x86_64 或 aarch64

# 若二進位與 CPU 不匹配，用替代方式安裝
brew install --cask claude-code
```

### 問題：權限錯誤 (Permission denied)

```bash
# 檢查安裝目錄可寫
test -w ~/.local/bin && echo "writable" || echo "not writable"

# 修復權限
sudo mkdir -p ~/.local/bin
sudo chown -R $(whoami) ~/.local

# 或直接使用原生安裝（不需要 sudo）
curl -fsSL https://claude.ai/install.sh | bash
```

### 問題：WSL 中的特殊問題

```bash
# 確認使用的是 Linux 的 node，不是 Windows 的
which node  # 應該是 /usr/... 開頭，不是 /mnt/c/...

# 若指向 Windows，用 nvm 安裝 Linux node
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install 20

# WSL2 Sandbox 需要額外套件
sudo apt-get install bubblewrap socat  # Ubuntu/Debian
```

### 問題：多重安裝衝突

**macOS / Linux：**
```bash
# 列出所有安裝
which -a claude
ls -la ~/.local/bin/claude
npm -g ls @anthropic-ai/claude-code 2>/dev/null

# 保留原生安裝，移除其他
npm uninstall -g @anthropic-ai/claude-code    # 移除 npm 版本
brew uninstall --cask claude-code              # 移除 Homebrew 版本（若需要）
```

**Windows PowerShell：**
```powershell
# 檢查安裝位置
Get-Command claude | Select-Object Source
```

## 認證問題

### 問題：API Key 無效

**macOS / Linux：**
```bash
echo $ANTHROPIC_API_KEY  # 確認有值且以 sk-ant- 開頭
```

**Windows PowerShell：**
```powershell
echo $env:ANTHROPIC_API_KEY
```

### 問題：OAuth 登入失敗

```bash
# 瀏覽器未自動開啟 → 按 c 複製 URL 手動貼上
# 登入碼過期 → 按 Enter 重試，快速完成

# WSL2 中瀏覽器無法開啟
export BROWSER="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
claude

# 重新登入
> /logout
> /login
```

### 問題：403 Forbidden

```
API Error: 403 ... Request not allowed
```

- **Claude Pro/Max 用戶**：確認訂閱在 claude.ai/settings 中是活躍的
- **Console 用戶**：確認帳號有 "Claude Code" 角色
- **舊 API Key 干擾**：`unset ANTHROPIC_API_KEY`（或移除 shell profile 中的 export）
- **代理干擾**：參考代理設定章節

### 問題：Token 過期

```
> /login   # 重新認證
```

若頻繁發生，檢查系統時鐘是否準確（token 驗證依賴正確的時間戳）。

## 連線問題

### 問題：API 連線超時

**macOS / Linux：**
```bash
curl -I https://api.anthropic.com
# 在代理環境中
export HTTPS_PROXY="http://your-proxy:8080"
```

**Windows PowerShell：**
```powershell
Invoke-WebRequest -Uri "https://api.anthropic.com" -Method Head
$env:HTTPS_PROXY = "http://your-proxy:8080"
```

### 問題：Rate Limiting (429)

```
# 等待後重試，或切換到較小模型
> /model claude-sonnet-4-20250514

# 長期方案：升級 API 方案
```

## 搜尋與發現問題

### 問題：Search、@file、Skills 不正常

安裝系統級 `ripgrep`：

**macOS：**
```bash
brew install ripgrep
```

**Windows：**
```powershell
winget install BurntSushi.ripgrep.MSVC
```

**Ubuntu / Debian：**
```bash
sudo apt install ripgrep
```

**Alpine：**
```bash
apk add ripgrep
```

然後設定 `USE_BUILTIN_RIPGREP=0`。

### 問題：WSL 搜尋結果不完整

WSL 跨檔案系統讀取效能差，導致搜尋結果偏少。

- 將專案移到 Linux 檔案系統（`/home/`）
- 或使用原生 Windows 的 Claude Code
- 或提供更具體的搜尋範圍

## MCP 相關問題

### 問題：MCP 伺服器未啟動

**macOS / Linux：**
```bash
cat .claude/settings.json | python3 -m json.tool  # 檢查 JSON 語法
npx -y @modelcontextprotocol/server-github         # 測試手動啟動
env | grep GITHUB_TOKEN                             # 確認環境變數
```

**Windows PowerShell：**
```powershell
Get-Content .claude\settings.json | python -m json.tool
npx -y @modelcontextprotocol/server-github
$env:GITHUB_TOKEN
```

### 問題：MCP 工具不可用

```
> /status                    # 檢查 MCP 連線狀態
> 列出所有可用的 MCP 工具    # 確認工具清單
```

可能原因：settings.json 中 deny 了該工具、伺服器連線失敗、環境變數缺失。

## 效能問題

| 症狀 | 原因 | 解方 |
|------|------|------|
| 回應慢 | 上下文太長 | `/compact` 或 `/clear` 開新對話 |
| 回應慢 | 模型太重 | `/model claude-sonnet-4-20250514` |
| CPU/記憶體高 | 大型程式碼庫 | `/compact`、重啟 Claude Code |
| 卡住不動 | 操作掛起 | `Ctrl+C` 中斷，或關閉終端重啟 |

## 設定問題

### 問題：CLAUDE.md 沒有被載入

- 確認在專案根目錄或 `~/.claude/CLAUDE.md`
- 確認 UTF-8 編碼
- 直接問 Claude：`你有讀到 CLAUDE.md 嗎？`

### 問題：Settings 不生效

- 確認 JSON 語法正確（用 `/doctor` 檢查）
- 確認檔案在正確位置（全域：`~/.claude/settings.json`、專案：`.claude/settings.json`）
- 注意：**deny 永遠優先於 allow**

### 問題：權限反覆提示

```
> /permissions    # 設定常用指令的允許清單
```

或在 settings.json 中預設允許安全操作。

## 常見錯誤訊息速查

| 錯誤訊息 | 原因 | 解方 |
|---------|------|------|
| `command not found: claude` | PATH 未設定 | 見安裝章節 |
| `syntax error near '<'` | 安裝腳本返回 HTML | 網路問題或地區限制 |
| `ANTHROPIC_API_KEY not set` | 缺少 API Key | 設定環境變數或用 OAuth |
| `403 Forbidden` | 認證問題 | 檢查訂閱、移除舊 API Key |
| `Context window exceeded` | 對話太長 | `/compact` 或開新對話 |
| `Tool not allowed` | 被權限拒絕 | 檢查 permissions 設定 |
| `MCP server failed to start` | MCP 設定有誤 | 檢查 command/args/env |
| `Rate limit exceeded` (429) | API 頻率超限 | 等待重試或升級方案 |
| `Illegal instruction` | CPU 架構不符 | 用 Homebrew 安裝替代 |
| `requires git-bash` | 缺少 Git for Windows | 安裝 Git for Windows |
| `This organization has been disabled` | 舊 API Key 干擾 | `unset ANTHROPIC_API_KEY` |
| `unable to get local issuer certificate` | 企業 CA 憑證問題 | 設定 `NODE_EXTRA_CA_CERTS` |

## 升級問題

```bash
# 檢查版本
claude --version

# 手動更新
claude update

# 回退到穩定版
curl -fsSL https://claude.ai/install.sh | bash -s stable
```

## 求助管道

1. **內建診斷**：`/doctor` — 最快的第一步
2. **回報 Bug**：`/bug` — 直接向 Anthropic 回報
3. **問 Claude**：直接問 Claude 它的功能和設定
4. **官方文件**：https://code.claude.com/docs
5. **GitHub Issues**：https://github.com/anthropics/claude-code

## 除錯清單

遇到問題時，按順序檢查：

```
□ claude --version 能正常顯示？
□ claude doctor 沒有紅色警告？
□ API Key / OAuth 認證有效？
□ 網路可以連到 storage.googleapis.com？
□ 設定檔 JSON 語法正確？
□ CLAUDE.md 在正確的位置？
□ 環境變數都有設定？
□ MCP 伺服器能手動啟動？
□ 權限 deny 規則沒有太廣？
□ ripgrep 已安裝（搜尋功能需要）？
```

---

⬅️ [上一篇：最佳實踐與技巧](10-BEST-PRACTICES.md) | 🏠 [返回目錄](README.md)
