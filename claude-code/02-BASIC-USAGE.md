# 02 — 基礎使用與核心指令

## 啟動 Claude Code

```bash
# 在專案根目錄啟動（推薦）
cd /path/to/your/project
claude

# 帶初始指令啟動
claude "請分析這個專案的架構"

# 以非互動模式執行單一任務
claude -p "列出所有 TODO 註解"

# 繼續上次的對話
claude --continue

# 從特定對話恢復
claude --resume
```

## 互動模式基本操作

啟動後進入互動式 REPL，你可以直接用自然語言溝通：

```
> 幫我讀取 src/main.py 並解釋核心邏輯
> 這個函式有 bug，幫我修好
> 建立一個新的 REST API endpoint
> 執行測試並修復失敗的案例
```

### 多行輸入

```
# 按 Shift+Enter 或使用反斜線換行
> 幫我建立一個函式，需求如下：\
  1. 接受一個字串參數\
  2. 回傳反轉後的字串\
  3. 包含 type hints
```

## 斜線指令速查表

| 指令 | 功能 | 說明 |
|------|------|------|
| `/help` | 顯示說明 | 列出所有可用指令 |
| `/clear` | 清除對話 | 重置目前的對話上下文 |
| `/compact` | 壓縮上下文 | 將長對話摘要化，釋放 token 空間 |
| `/config` | 開啟設定 | 查看或修改 Claude Code 設定 |
| `/cost` | 顯示費用 | 查看目前對話的 token 使用量與費用 |
| `/doctor` | 健康檢查 | 診斷 Claude Code 的安裝與設定狀態 |
| `/init` | 初始化專案 | 產生 CLAUDE.md 專案設定檔 |
| `/login` | 登入 | 切換或重新認證帳號 |
| `/logout` | 登出 | 清除目前的認證資訊 |
| `/memory` | 記憶管理 | 查看或編輯 CLAUDE.md 記憶檔 |
| `/model` | 切換模型 | 選擇使用的模型（如 Claude Sonnet/Opus） |
| `/permissions` | 權限設定 | 管理工具的允許 / 拒絕規則 |
| `/review` | 程式碼審查 | 對目前變更進行 code review |
| `/status` | 顯示狀態 | 顯示目前 Git 狀態、模型、費用等資訊 |
| `/terminal-setup` | 終端設定 | 設定 Shift+Enter 多行輸入 |
| `/vim` | Vim 模式 | 切換 Vim 風格鍵位綁定 |
| `/hooks` | Hooks 管理 | 瀏覽和設定自動觸發的腳本 |
| `/sandbox` | 沙盒模式 | 啟用 OS 層級的檔案系統和網路隔離 |
| `/rewind` | 回溯 | 恢復到之前的對話和程式碼狀態 |
| `/rename` | 重新命名 | 為目前對話設定描述性名稱 |
| `/btw` | 旁問 | 快速提問，不佔用對話上下文 |
| `/bug` | 回報問題 | 直接向 Anthropic 回報 bug |
| `/plugin` | 插件 | 瀏覽和安裝社群插件 |

## CLI 啟動參數

```bash
# 常用參數
claude                          # 互動模式
claude "指令"                   # 帶初始訊息的互動模式
claude -p "指令"                # 非互動模式（print 模式），執行完即退出
claude -p "指令" --output-format json       # 非互動模式 + JSON 輸出
claude -p "指令" --output-format stream-json # 串流 JSON 輸出
claude --continue               # 繼續最近一次對話
claude --resume                 # 選擇並恢復歷史對話
claude --model claude-sonnet-4-20250514  # 指定模型
claude --allowedTools "Edit,Write"       # 限定可用工具

# 管道模式（Pipeline）
cat error.log | claude -p "分析這個錯誤日誌"
git diff | claude -p "審查這些變更"
```

## 權限系統

Claude Code 有分層的權限模型來確保安全：

### 工具分類

| 類別 | 風險等級 | 預設行為 | 範例工具 |
|------|---------|---------|---------|
| 唯讀工具 | 低 | 自動允許 | Read File, List Directory, Grep Search |
| 寫入工具 | 中 | 需確認 | Edit File, Create File |
| 執行工具 | 高 | 需確認 | Run Terminal Command |

### 權限回應選項

當 Claude 請求需要權限的操作時，你會看到：

```
Claude wants to edit src/main.py
[y] Allow once  [n] Deny  [a] Always allow for this session  [A] Always allow
```

| 選項 | 效果 |
|------|------|
| `y` | 本次允許 |
| `n` | 本次拒絕 |
| `a` | 本次工作階段內自動允許同類操作 |
| `A` | 永久允許（寫入設定檔） |

### 自動允許設定（進階使用者）

```bash
# 允許所有編輯操作（不再逐次確認）
claude --allowedTools "Edit" --allowedTools "Write"

# 完全信任模式（謹慎使用！）
claude --dangerously-skip-permissions
```

> ⚠️ `--dangerously-skip-permissions` 會跳過所有確認，只建議在安全的開發環境中使用。

## 常見操作範例

### 檔案操作

```
> 讀取 src/config.ts 的內容
> 在 src/utils/ 下建立 helpers.ts，包含日期格式化函式
> 把 src/old.js 的內容搬到 src/new.ts 並轉換為 TypeScript
> 刪除所有 .log 檔案
```

### 程式碼生成

```
> 幫我寫一個 Express.js REST API，包含 CRUD endpoints
> 為 UserService 類別產生單元測試
> 將這個 callback-based 函式重構為 async/await
```

### 搜尋與分析

```
> 找出所有使用 deprecated API 的地方
> 這個專案有哪些安全漏洞？
> 分析 src/ 目錄的依賴關係
```

### 終端命令執行

```
> 執行 npm test 並修復失敗的測試
> 安裝 express 和 cors 套件
> 啟動開發伺服器
```

### Git 操作

```
> 查看目前的 git 狀態和未提交的變更
> 提交目前的變更，commit message 用英文
> 建立一個新的 feature branch
> 產生 PR 描述
```

## 對話管理

### 上下文視窗

Claude Code 有上下文長度限制。當對話變長時：

```
# 壓縮目前的上下文（保留重點，釋放空間）
/compact

# 帶自訂摘要指引壓縮
/compact 請保留所有與 API 設計相關的討論

# 如果上下文完全混亂，清除重來
/clear
```

### 費用監控

```
# 查看目前對話的費用
/cost

# 輸出範例：
# Session cost: $0.45
# Total tokens: input 50,000 / output 12,000
```

## 快捷鍵

| 按鍵 | 功能 |
|------|------|
| `Enter` | 送出訊息 |
| `Shift+Enter` | 換行（需先 `/terminal-setup`） |
| `Ctrl+C` | 中斷目前操作 |
| `Ctrl+D` | 退出 Claude Code |
| `↑` / `↓` | 瀏覽歷史訊息 |
| `Escape` | 中斷 Claude 操作（保留上下文） |
| `Escape` × 2 | 開啟 `/rewind` 回溯選單 |
| `Ctrl+G` | 切換 Plan Mode / Normal Mode |
| `Tab` | 自動補全檔案路徑 |
| `@` | 引用特定檔案（Claude 會先讀取） |

---

⬅️ [上一篇：安裝與環境設定](01-INSTALLATION.md) | ➡️ [下一篇：設定檔系統](03-CONFIGURATION.md)
