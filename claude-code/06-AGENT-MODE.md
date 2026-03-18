# 06 — Agent 模式與自動化

Agent 模式是 Claude Code 最強大的特性 — Claude 不只是回答問題，而是自主規劃、執行、驗證完整的開發任務。

## Plan Mode（規劃模式）

**Plan Mode 是官方推薦的「先探索→再規劃→最後寫程式」工作流程的核心。**

### 切換方式

| 操作 | 鍵盤快捷鍵 |
|------|------------|
| 切換到 Plan Mode | `Ctrl+G` 或 `Cmd+G` |
| 切回 Act Mode | `Ctrl+G` 或 `Cmd+G`（再按一次） |

### Plan Mode vs Act Mode

| | Plan Mode | Act Mode（預設） |
|---|-----------|--------------------|
| 讀取檔案 | ✓ | ✓ |
| 搜尋程式碼 | ✓ | ✓ |
| **編輯檔案** | ✘ | ✓ |
| **執行命令** | ✘ | ✓ |
| 適用場景 | 架構規劃、方案診斷 | 實際開發、修復 |

### 典型工作流程

```
1. 按 Ctrl+G 進入 Plan Mode
2. > 重構我們的認證系統，支援 OAuth2 + OIDC
3. Claude 探索程式碼、分析架構、產出計畫...
4. 你審查計畫，給予回饋
5. 確認後按 Ctrl+G 切回 Act Mode
6. Claude 依計畫執行
```

## Agent 模式概念

### 傳統 Chat vs Agent 模式

| 傳統 Chat 模式 | Agent 模式 |
|---------------|-----------|
| 一問一答 | 自主規劃多步驟 |
| 手動逐步指示 | 自動決策下一步 |
| 需要你確認每個動作 | 自動執行直到完成 |
| 被動的程式碼建議 | 主動探索、修改、測試 |

### Agent 工作流程

```
你的指令 → Claude 分析 → 制定計劃
                            ↓
                     ┌──────────────┐
                     │  執行步驟 1   │ → 搜尋程式碼
                     ├──────────────┤
                     │  執行步驟 2   │ → 修改檔案
                     ├──────────────┤
                     │  執行步驟 3   │ → 執行測試
                     ├──────────────┤
                     │  執行步驟 4   │ → 修復失敗
                     ├──────────────┤
                     │  執行步驟 5   │ → 再次測試
                     └──────────────┘
                            ↓
                     報告完成結果
```

## 觸發 Agentic 行為

你不需要特別「開啟」Agent 模式 — 當你描述一個需要多步驟完成的任務時，Claude 會自動規劃：

### 簡單指令（非 Agent）

```
> 讀取 src/main.ts 的內容     ← 單步操作
```

### 觸發 Agent（自動）

```
> 修復所有測試失敗的案例       ← Claude 會：
                              1. 執行測試找出失敗項目
                              2. 閱讀失敗的測試和原始碼
                              3. 分析失敗原因
                              4. 修改程式碼
                              5. 重新執行測試確認
                              6. 重複直到全部通過
```

## 工具使用（Tool Use）

Claude Code 有一組內建工具，Agent 模式會自主決定何時使用：

### 內建工具列表

| 工具 | 功能 | 權限等級 |
|------|------|---------|
| `Read File` | 讀取檔案內容 | 唯讀（自動） |
| `List Directory` | 列出目錄結構 | 唯讀（自動） |
| `Grep Search` | 文字搜尋 | 唯讀（自動） |
| `Semantic Search` | 語意搜尋 | 唯讀（自動） |
| `Edit File` | 編輯既有檔案 | 寫入（需確認） |
| `Create File` | 建立新檔案 | 寫入（需確認） |
| `Run Terminal` | 執行 shell 命令 | 執行（需確認） |
| `Manage Todo List` | 任務追蹤 | 自動 |

### 工具選擇邏輯

Claude 會根據任務：

```
"修復登入 bug"
├── Grep Search → 搜尋 "login" 相關程式碼
├── Read File → 閱讀找到的檔案
├── Semantic Search → 找出相關的認證邏輯
├── Read File → 閱讀測試檔案
├── Edit File → 修改有 bug 的程式碼
├── Run Terminal → 執行測試
└── Edit File → 如果測試失敗，繼續修復
```

## Headless 模式（無人值守）

以程式化方式使用 Claude Code，適合 CI/CD 和自動化腳本：

### 基本用法

```bash
# -p（print）模式：非互動，執行完即退出
claude -p "列出所有 TODO 註解" 

# 支援 stdin
cat requirements.txt | claude -p "檢查有沒有已知的安全漏洞"

# JSON 格式輸出
claude -p "分析 src/main.ts 的複雜度" --json

# 設定最大回合數
claude -p "重構 auth 模組" --max-turns 20
```

### 結合管道組成工作流

```bash
# 自動 code review
git diff --staged | claude -p "
審查這些即將提交的變更：
1. 檢查是否有 bug
2. 檢查是否有安全漏洞
3. 格式：每個問題一行，前綴 [severity: high/medium/low]
如果沒有問題，只輸出 LGTM
"

# 自動產生 commit message
git diff --staged | claude -p "
產生 conventional commit message：
- 分析變更內容
- 格式：<type>(<scope>): <description>
- 只輸出 commit message，不要其他文字
"

# 自動產生 PR 描述
git log main..HEAD --oneline | claude -p "
根據這些 commit 產生 Pull Request 描述：
- 包含：Summary, Changes, Testing 區段
- 用 Markdown 格式
"
```

### CI/CD 整合範例

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Install Claude Code
        run: |
          curl -fsSL https://cli.claude.com/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: AI Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          git diff origin/main...HEAD | claude -p "
          Perform a code review. Focus on:
          1. Security vulnerabilities
          2. Performance issues
          3. Logic errors
          Output as GitHub PR review comments format.
          " --output-format json > review.json
```

> ⚠️ npm 安裝方式已過時，CI 中請用 `curl` 原生安裝。

## 自動化食譜

### 自動修復 CI

```bash
#!/bin/bash
# fix-ci.sh - 讓 Claude 自動修復 CI 失敗

# 取得 CI 失敗的日誌
CI_LOG=$(gh run view --log-failed 2>&1)

# 餵給 Claude 修復
echo "$CI_LOG" | claude -p "
CI 構建失敗了。請：
1. 分析失敗原因
2. 修復程式碼
3. 確認本地測試通過
"
```

### 自動文件更新

```bash
#!/bin/bash
# update-docs.sh - 程式碼變更後自動更新文件

claude -p "
比對 src/ 目錄的程式碼和 docs/ 目錄的文件：
1. 找出文件中已過期的 API 描述
2. 更新這些文件以反映目前的程式碼
3. 列出所有修改的檔案
"
```

### 定期程式碼健檢

```bash
#!/bin/bash
# health-check.sh - 定期程式碼品質掃描

claude -p "
對這個專案進行健康檢查：
1. 找出未使用的函式和 import
2. 找出可能的記憶體洩漏
3. 檢查是否有硬編碼的敏感資訊
4. 列出超過 200 行的函式（需要重構候選）
5. 輸出 JSON 格式的報告
" --json > health-report.json
```

## Sub-Agent（子代理）

Claude Code 支援定義可重用的 Subagent，將獨立子任務分派給新的 Agent 處理，每個 Subagent 擁有自己的上下文和工具權限：

### 定義方式

在 `.claude/agents/` 目錄建立 Markdown 檔案：

```markdown
<!-- .claude/agents/code-reviewer.md -->
---
name: code-reviewer
description: 喴格的程式碼審查專家。專注品質、安全、效能。
tools:
  - Read File
  - Grep Search
  - Semantic Search
  # 注意：沒有 Edit 和 Terminal — 只讀不寫
---

你是程式碼審查專家。逐行審查，不放過任何問題。
報告格式：🔴 嚴重 / 🟡 建議 / 🟢 小問題
```

### 使用 Subagent

```
> 請用 code-reviewer agent 審查 src/auth/ 的變更

# 或在對話中直接請 Claude 分派：
> 幫我完成以下任務（可平行進行）：
> 1. 搜尋並列出所有 deprecated 的 API 呼叫
> 2. 分析專案的依賴樹，找出需要更新的套件
> 3. 檢查所有檔案的命名是否符合規範
```

### Sub-Agent 適用場景

- 大型程式碼庫的平行搜尋
- 獨立的檔案分析任務
- 不互相依賴的修改操作
- **探索性任務** — 用 Subagent 研究，不污染主對話上下文

## Agent Teams（多 Agent 協作）

多個 Claude Code 實例可以平行工作，每個處理不同的子任務（fan-out 模式）：

```bash
# 平行啟動多個 Claude 實例
claude -p "refactor auth module" --output-format json &
claude -p "add unit tests for payment" --output-format json &
claude -p "update API documentation" --output-format json &
wait

# 各自獨立工作，最後合併結果
```

### Fan-out 最佳實踐

- 確保任務之間不修改相同檔案
- 使用 Git worktrees 讓每個 Agent 在獨立分支工作
- 合併前執行測試確認無衝突

## Hooks（確定性自動化）

Hooks 是與 Agent Mode 配合使用的確定性動作，在特定事件發生時自動執行（不需要 Claude 判斷）：

```json
// .claude/settings.json
{
  "hooks": {
    "on_file_edit": [
      { "command": "npx prettier --write {{filePath}}" }
    ],
    "on_tool_use": [
      { "command": "npm test -- --bail", "tool": "Edit" }
    ]
  }
}
```

| Hook | 觸發時機 | 典型用法 |
|------|---------|----------|
| `on_file_edit` | 檔案被編輯後 | Formatter、Linter |
| `on_tool_use` | 工具被呼叫後 | 自動跑測試 |
| `on_message_send` | Claude 回覆後 | 日誌、通知 |
| `on_session_start` | 對話啟動時 | 環境檢查 |

> Hooks vs MCP：Hooks 是「每次都執行」；MCP 工具是「Claude 判斷是否需要執行」。

## /sandbox（OS 層級隱離）

`/sandbox` 讓 Claude 在隱離的環境中執行操作，不會影響你的本機：

```
> /sandbox
# Claude 會在容器化環境中執行後續操作
# 適合執行不確定是否安全的命令
```

## 任務追蹤（Todo List）

Agent 在處理複雜任務時會自動使用 Todo List 追蹤進度：

```
> 重構用戶管理模組

# Claude 會內部建立 Todo List：
# ☐ 分析現有 UserService 結構
# ☐ 辨識需要拆分的職責
# ☐ 建立 UserRepository 介面
# ☐ 實作 PostgresUserRepository
# ☐ 重構 UserService
# ☐ 更新相關的測試
# ☐ 執行全部測試確認

# 每完成一步，Claude 會更新狀態並繼續
```

## 安全控制

### 確認模式（預設）

```
Claude wants to run: npm test
[y] Allow once  [n] Deny  [a] Always for session
> y

Claude wants to edit: src/main.ts
[y] Allow once  [n] Deny  [a] Always for session
> a   ← 本次對話中自動允許所有編輯
```

### 預設放行常見操作

在 `.claude/settings.json` 中預先允許安全操作：

```json
{
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "Bash(npm test *)",
      "Bash(npm run lint *)",
      "Bash(npx vitest *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(ls *)",
      "Bash(cat *)",
      "Bash(find *)"
    ]
  }
}
```

### 信任場景（完全自動）

```bash
# 在安全的 CI/CD 環境中：
claude -p "修復所有測試" \
  --allowedTools "Edit" "Write" "Bash" \
  --max-turns 30

# 或使用完全跳過確認（僅限安全環境）
claude -p "修復所有測試" --dangerously-skip-permissions
```

> ⚠️ 永遠不要在生產環境使用 `--dangerously-skip-permissions`。

## 對話控制技巧

| 操作 | 方法 | 說明 |
|------|------|------|
| 暂停執行 | `Escape` | 停止目前操作，保留上下文 |
| 回滯檢查點 | `Escape×2` 或 `/rewind` | 回到上一個檢查點 |
| 側問題 | `/btw <問題>` | 不污染主對話上下文 |
| 壓縮上下文 | `/compact` | 縮減 token 使用，保留重點 |
| 對話命名 | `/rename <名稱>` | 給對話命名以便稍後繼續 |
| 繼續對話 | `claude --resume` | 繼續之前的對話 |

---

⬅️ [上一篇：Prompt 工程](05-PROMPT-ENGINEERING.md) | ➡️ [下一篇：MCP 伺服器整合](07-MCP-INTEGRATION.md)
