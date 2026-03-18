# 01 — 安裝與環境設定

## 系統需求

| 項目 | 最低需求 |
|------|---------|
| 作業系統 | macOS 13.0+、Windows 10 1809+、Ubuntu 20.04+、Debian 10+、Alpine 3.19+ |
| Shell | Bash、Zsh、PowerShell 或 CMD |
| 記憶體 | 4 GB RAM（建議 8 GB+） |
| 網路 | 需要穩定網路連線 |
| 帳號 | Claude Pro / Max / Team / Enterprise 訂閱，或 Anthropic Console API |
| Windows 額外 | 需安裝 [Git for Windows](https://git-scm.com/downloads/win) |

> ⚠️ Claude 免費方案（Free plan）不包含 Claude Code 存取權限。

## 安裝方式

### 方式一：原生安裝（推薦）

原生安裝會自動在背景更新，無需 Node.js 依賴。

**macOS / Linux / WSL：**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows PowerShell：**
```powershell
irm https://claude.ai/install.ps1 | iex
```

**Windows CMD：**
```cmd
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

### 方式二：Homebrew（macOS / Linux）

```bash
brew install --cask claude-code
```

> 💡 Homebrew 不會自動更新，需手動執行 `brew upgrade claude-code`。

### 方式三：WinGet（Windows）

```powershell
winget install Anthropic.ClaudeCode
```

> 💡 WinGet 不會自動更新，需手動執行 `winget upgrade Anthropic.ClaudeCode`。

### 方式四：npm（已棄用，僅用於相容需求）

需要 Node.js 18+：

```bash
npm install -g @anthropic-ai/claude-code
```

> ⚠️ npm 安裝方式已標記為棄用。建議遷移至原生安裝：
> ```bash
> curl -fsSL https://claude.ai/install.sh | bash  # 安裝原生版本
> npm uninstall -g @anthropic-ai/claude-code        # 移除舊 npm 版本
> ```

### 方式五：Desktop App（免終端）

如果你不熟悉命令列，可以下載桌面應用程式：
- **macOS**: 從 [claude.ai](https://claude.ai) 下載 DMG
- **Windows**: 從 [claude.ai](https://claude.ai) 下載 EXE

## 各平台特別指引

### macOS

```bash
# 安裝
curl -fsSL https://claude.ai/install.sh | bash

# 若 PATH 未自動設定
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 驗證
claude --version
```

**常見問題：**
- `dyld: cannot load` → macOS 版本需 13.0+，請更新系統
- 憑證簽章為 "Anthropic PBC"，已通過 Apple 公證

### Linux（Ubuntu / Debian）

```bash
# 安裝
curl -fsSL https://claude.ai/install.sh | bash

# 若 PATH 未自動設定
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 驗證
claude --version
```

**低記憶體伺服器（< 4GB RAM）：**
```bash
# 先建立 swap 空間
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 再執行安裝
curl -fsSL https://claude.ai/install.sh | bash
```

**Alpine Linux / musl 發行版：**
```bash
# 安裝必要依賴
apk add libgcc libstdc++ ripgrep

# 安裝 Claude Code
curl -fsSL https://claude.ai/install.sh | bash
```

然後在 settings.json 中設定：
```json
{ "env": { "USE_BUILTIN_RIPGREP": "0" } }
```

### Windows（原生 + Git Bash）

Claude Code **支援原生 Windows**，需要安裝 [Git for Windows](https://git-scm.com/downloads/win)：

```powershell
# 1. 先安裝 Git for Windows（若尚未安裝）
#    下載：https://git-scm.com/downloads/win
#    安裝時勾選 "Add to PATH"

# 2. 安裝 Claude Code（PowerShell）
irm https://claude.ai/install.ps1 | iex

# 3. 驗證
claude --version
```

**Git Bash 路徑找不到？** 在 settings.json 中手動指定：
```json
{
  "env": {
    "CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe"
  }
}
```

**PATH 未設定？**
```powershell
# 確認 PATH 包含安裝目錄
$env:PATH -split ';' | Select-String 'local\\bin'

# 若無輸出，手動加入（PowerShell）
[System.Environment]::SetEnvironmentVariable("PATH", "$env:USERPROFILE\.local\bin;$env:PATH", "User")
```

### Windows（WSL2）

如果偏好 Linux 環境，可透過 WSL2 使用：

```powershell
# 1. 安裝 WSL2（以系統管理員身分執行 PowerShell）
wsl --install

# 2. 重新啟動後進入 WSL
wsl
```

```bash
# 3. 在 WSL 中安裝 Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# 4. 驗證
claude --version
```

> 💡 **WSL2 vs 原生 Windows 差異：**
>
> | 特性 | 原生 Windows | WSL2 |
> |------|-------------|------|
> | 安裝複雜度 | 低（需 Git for Windows） | 中（需安裝 WSL） |
> | Sandbox 沙盒 | ✗ 不支援 | ✓ 支援（需 `bubblewrap` + `socat`） |
> | 檔案效能 | Windows FS 原生速度 | Linux FS 快；`/mnt/c/` 慢 |
> | IDE 整合 | 直接整合 | 需額外 networking 設定 |
> | Shell | Git Bash | Bash / Zsh |

**WSL2 Sandbox 安裝：**
```bash
# Ubuntu/Debian
sudo apt-get install bubblewrap socat

# Fedora
sudo dnf install bubblewrap socat
```

## 認證設定

### 方式一：OAuth 互動式登入（推薦）

```bash
# 直接啟動，Claude Code 會引導瀏覽器 OAuth 登入
claude
# 若瀏覽器未自動開啟，按 c 複製 URL 手動貼上
```

支援的訂閱方案：Claude Pro、Max、Team、Enterprise。

**WSL2 中瀏覽器無法開啟？**
```bash
# 設定 Windows 瀏覽器路徑
export BROWSER="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
claude
```

### 方式二：API Key 認證（Console 用戶）

**macOS / Linux / WSL：**
```bash
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
# 永久生效
echo 'export ANTHROPIC_API_KEY="sk-ant-xxxxx"' >> ~/.bashrc  # 或 ~/.zshrc
source ~/.bashrc
```

**Windows PowerShell：**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-xxxxx"
# 永久生效
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-xxxxx", "User")
```

**Windows CMD：**
```cmd
set ANTHROPIC_API_KEY=sk-ant-xxxxx
:: 永久生效
setx ANTHROPIC_API_KEY "sk-ant-xxxxx"
```

### 方式三：Amazon Bedrock

**macOS / Linux / WSL：**
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
export CLAUDE_CODE_USE_BEDROCK=1
claude
```

**Windows PowerShell：**
```powershell
$env:AWS_ACCESS_KEY_ID = "your-access-key"
$env:AWS_SECRET_ACCESS_KEY = "your-secret-key"
$env:AWS_REGION = "us-east-1"
$env:CLAUDE_CODE_USE_BEDROCK = "1"
claude
```

### 方式四：Google Vertex AI

**macOS / Linux / WSL：**
```bash
export CLOUD_ML_REGION="us-east5"
export ANTHROPIC_VERTEX_PROJECT_ID="your-project-id"
export CLAUDE_CODE_USE_VERTEX=1
claude
```

**Windows PowerShell：**
```powershell
$env:CLOUD_ML_REGION = "us-east5"
$env:ANTHROPIC_VERTEX_PROJECT_ID = "your-project-id"
$env:CLAUDE_CODE_USE_VERTEX = "1"
claude
```

### 方式五：Microsoft Foundry

請參考 [官方文件](https://code.claude.com/docs/en/microsoft-foundry) 設定。

## 驗證安裝成功

```bash
# 檢查版本
claude --version

# 完整健康檢查（檢查安裝、搜尋、MCP、設定等）
claude doctor

# 啟動互動模式
claude
```

## 更新 Claude Code

**原生安裝（自動更新）：**
```bash
# 原生安裝會自動背景更新，也可手動觸發
claude update
```

**Homebrew：**
```bash
brew upgrade claude-code
brew cleanup claude-code  # 清理舊版本
```

**WinGet：**
```powershell
winget upgrade Anthropic.ClaudeCode
```

**npm（棄用）：**
```bash
npm update -g @anthropic-ai/claude-code
```

### 更新通道設定

```json
// settings.json
{
  "autoUpdatesChannel": "stable"  // "latest"（預設）或 "stable"（約延遲一週，跳過有問題的版本）
}
```

### 安裝特定版本

**macOS / Linux / WSL：**
```bash
curl -fsSL https://claude.ai/install.sh | bash -s stable    # 穩定版
curl -fsSL https://claude.ai/install.sh | bash -s 1.0.58    # 指定版本
```

## 解除安裝

**原生安裝（macOS / Linux / WSL）：**
```bash
rm -f ~/.local/bin/claude
rm -rf ~/.local/share/claude
```

**原生安裝（Windows PowerShell）：**
```powershell
Remove-Item "$env:USERPROFILE\.local\bin\claude.exe" -Force
Remove-Item "$env:USERPROFILE\.local\share\claude" -Recurse -Force
```

**Homebrew：**
```bash
brew uninstall --cask claude-code
```

**WinGet：**
```powershell
winget uninstall Anthropic.ClaudeCode
```

**npm：**
```bash
npm uninstall -g @anthropic-ai/claude-code
```

### 清除設定檔（完全重置）

**macOS / Linux / WSL：**
```bash
rm -rf ~/.claude && rm -f ~/.claude.json
```

**Windows PowerShell：**
```powershell
Remove-Item "$env:USERPROFILE\.claude" -Recurse -Force
Remove-Item "$env:USERPROFILE\.claude.json" -Force
```

> ⚠️ 這會刪除所有設定、MCP 伺服器配置和對話歷史。

## 代理伺服器設定（企業環境）

**macOS / Linux / WSL：**
```bash
export HTTP_PROXY="http://proxy.company.com:8080"
export HTTPS_PROXY="http://proxy.company.com:8080"
export NO_PROXY="localhost,127.0.0.1,.company.com"
# 企業 CA 憑證
export NODE_EXTRA_CA_CERTS="/path/to/corporate-ca.pem"
```

**Windows PowerShell：**
```powershell
$env:HTTP_PROXY = "http://proxy.company.com:8080"
$env:HTTPS_PROXY = "http://proxy.company.com:8080"
$env:NO_PROXY = "localhost,127.0.0.1,.company.com"
$env:NODE_EXTRA_CA_CERTS = "C:\certs\corporate-ca.pem"

# 若遇到 TLS 問題，先啟用 TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
```

## 目錄結構預覽

| 路徑 | 用途 |
|------|------|
| `~/.claude/settings.json` | 全域使用者設定（權限、hooks、模型覆寫） |
| `~/.claude.json` | 全域狀態（主題、OAuth、MCP 伺服器） |
| `.claude/settings.json` | 專案設定（可提交 Git，團隊共享） |
| `.claude/settings.local.json` | 本地專案設定（不提交 Git） |
| `.mcp.json` | 專案 MCP 伺服器設定（可提交 Git） |
| `CLAUDE.md` | 專案層級指令檔（Claude 自動讀取） |

> 💡 Windows 上 `~` 對應 `C:\Users\你的使用者名稱`。

---

⬅️ [返回目錄](README.md) | ➡️ [下一篇：基礎使用與核心指令](02-BASIC-USAGE.md)
