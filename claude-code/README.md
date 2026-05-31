# Claude Code 全端工程師配置包

針對 **Python + FastAPI + PostgreSQL + Vue 3** 全端技術棧最佳化的 Claude Code 配置。
參考 [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) 設計理念，精簡為單人全端工程師即時可用的配置包。

本配置提供 **兩個版本**：

| 版本 | 目錄 | 安裝位置 | 作用範圍 |
|------|------|---------|---------|
| **全域版** | `global/` | `~/.claude/` + `~/CLAUDE.md` | 所有專案共用 |
| **專案版** | `project/` | `<project>/.claude/` + `<project>/CLAUDE.md` | 僅該專案生效 |

---

## 快速開始

### 方式 A：僅安裝全域版（推薦新手）

```bash
# 1. 複製全域設定
cp global/CLAUDE.md ~/CLAUDE.md
mkdir -p ~/.claude
cp global/settings.json ~/.claude/settings.json
cp global/mcp.json ~/.claude/mcp.json

# 2. 設定 MCP 環境變數（見下方「MCP 環境變數設定」章節）
```

### 方式 B：僅安裝專案版

```bash
# 1. 複製專案設定到你的專案
cp project/CLAUDE.md <your-project>/CLAUDE.md
cp -r project/.claude/ <your-project>/.claude/
cp project/.mcp.json <your-project>/.mcp.json

# 2. 建立本地設定（存放密鑰，不提交 Git）
cp <your-project>/.claude/settings.local.json.example <your-project>/.claude/settings.local.json
# 編輯 settings.local.json，填入你的 token

# 3. 更新 .gitignore
echo '.claude/settings.local.json' >> <your-project>/.gitignore
echo 'CLAUDE.local.md' >> <your-project>/.gitignore
```

### 方式 C：全域 + 專案（推薦進階用戶）

```bash
# 1. 安裝全域版（個人偏好 + 通用 MCP）
cp global/CLAUDE.md ~/CLAUDE.md
mkdir -p ~/.claude
cp global/settings.json ~/.claude/settings.json
cp global/mcp.json ~/.claude/mcp.json

# 2. 安裝專案版（專案規範 + agents/commands/skills/rules）
cp project/CLAUDE.md <your-project>/CLAUDE.md
cp -r project/.claude/ <your-project>/.claude/
cp project/.mcp.json <your-project>/.mcp.json

# 3. 建立本地設定
cp <your-project>/.claude/settings.local.json.example <your-project>/.claude/settings.local.json

# 4. 更新 .gitignore
echo '.claude/settings.local.json' >> <your-project>/.gitignore
```

> **優先級**（低 → 高）：全域 `~/.claude/settings.json` → 專案 `.claude/settings.json` → 本地 `.claude/settings.local.json` → 對話指令

---

## 全域版 vs 專案版差異

### 全域版 (`global/`) — 安裝到 `~/.claude/`

適合放置所有專案都通用的個人偏好設定：

| 檔案 | 安裝位置 | 說明 |
|------|---------|------|
| `CLAUDE.md` | `~/CLAUDE.md` | 個人編碼偏好、語言、風格規範 |
| `settings.json` | `~/.claude/settings.json` | 通用工具權限、模型偏好、autocompact |
| `mcp.json` | `~/.claude/mcp.json` | 通用 MCP 伺服器（GitHub, context7, memory） |

**全域版特點：**
- ✅ 不含 hooks（避免在不同技術棧專案產生衝突）
- ✅ 不含 agents/commands/skills/rules（這些是專案特定的）
- ✅ MCP 僅含不需專案上下文的通用工具

### 專案版 (`project/`) — 安裝到 `<project>/.claude/`

適合放置專案特定的規範和工具：

| 檔案/目錄 | 安裝位置 | 說明 |
|----------|---------|------|
| `CLAUDE.md` | `<project>/CLAUDE.md` | 專案架構、技術棧、開發指令 |
| `.claude/settings.json` | `<project>/.claude/settings.json` | 專案權限 + hooks（auto-format, lint） |
| `.claude/settings.local.json.example` | 複製為 `.claude/settings.local.json` | 本地密鑰（不提交 Git） |
| `.mcp.json` | `<project>/.mcp.json` | 專案 MCP（含 playwright 等） |
| `.claude/agents/` | `<project>/.claude/agents/` | 7 個 AI 子代理 |
| `.claude/commands/` | `<project>/.claude/commands/` | 11 個自訂 Slash 指令 |
| `.claude/skills/` | `<project>/.claude/skills/` | 8 個工作流程技能 |
| `.claude/rules/` | `<project>/.claude/rules/` | 編碼規範（Python, Vue, Docker, Git） |

**專案版特點：**
- ✅ 包含完整 hooks（Python auto-format, Prettier, console.log 警告）
- ✅ 包含所有 agents, commands, skills, rules
- ✅ MCP 使用 `${GITHUB_TOKEN}` 環境變數引用（從 settings.local.json 或 shell 讀取）

---

## MCP 環境變數完整設定

### Step 1：產生 GitHub Personal Access Token (PAT)

1. 開啟 [GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. 點擊 **Generate new token**
3. 設定：
   - **Token name**: `claude-code`
   - **Expiration**: 建議 90 天（到期後重新產生）
   - **Repository access**: 選擇 `All repositories` 或指定需要的 repo
   - **Permissions**（建議最小權限）：

     | 權限類別 | 權限 | 存取等級 |
     |---------|------|---------|
     | Repository | Contents | Read and write |
     | Repository | Issues | Read and write |
     | Repository | Pull requests | Read and write |
     | Repository | Metadata | Read-only |
     | Repository | Commit statuses | Read-only |

4. 點擊 **Generate token**，複製 token（格式：`github_pat_...` 或 `ghp_...`）

> ⚠️ Token 只顯示一次，請立即儲存！

### Step 2：設定 Token（選擇一種方式）

#### 方式 A：寫入全域 MCP 設定檔（簡單直接）

```bash
# 編輯 ~/.claude/mcp.json
# 將 YOUR_GITHUB_PAT_HERE 替換為你的 token
```

```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "github_pat_xxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

#### 方式 B：使用環境變數引用（推薦，更安全）

**Linux/macOS** — 加入 shell profile：
```bash
# 加到 ~/.bashrc 或 ~/.zshrc
export GITHUB_TOKEN="github_pat_xxxxxxxxxxxxxxxx"

# 重新載入
source ~/.bashrc  # 或 source ~/.zshrc
```

**Windows** — 設定環境變數：
```powershell
# PowerShell（永久設定）
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'github_pat_xxxxxxxxxxxxxxxx', 'User')

# 或使用 GUI：系統設定 → 進階系統設定 → 環境變數 → 使用者變數 → 新增
```

然後在 MCP 設定檔中引用：
```json
{
  "mcpServers": {
    "github": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

#### 方式 C：使用 Claude CLI 設定（最簡單）

```bash
# 自動寫入全域 MCP 設定
claude mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_xxx -- npx -y @modelcontextprotocol/server-github

# 確認
claude mcp list
```

#### 方式 D：寫入專案本地設定（不提交 Git）

```bash
# 編輯 <project>/.claude/settings.local.json
```

```json
{
  "env": {
    "GITHUB_TOKEN": "github_pat_xxxxxxxxxxxxxxxx"
  }
}
```

### Step 3：設定其他 MCP 服務的環境變數（可選）

#### PostgreSQL 資料庫

```bash
# 環境變數
export DATABASE_URL="postgresql://user:password@localhost:5432/mydb"
```

在 `.mcp.json` 中新增：
```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
    }
  }
}
```

#### Slack Bot

1. 建立 Slack App：[api.slack.com/apps](https://api.slack.com/apps) → **Create New App**
2. 新增 Bot Token Scopes：`chat:write`, `channels:read`, `channels:history`
3. 安裝到 Workspace，取得 Bot Token（`xoxb-...`）

```bash
export SLACK_BOT_TOKEN="xoxb-your-bot-token"
export SLACK_TEAM_ID="T0123456789"
```

```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_BOT_TOKEN}",
        "SLACK_TEAM_ID": "${SLACK_TEAM_ID}"
      }
    }
  }
}
```

#### Linear（專案管理）

1. 取得 API Key：[linear.app/settings/api](https://linear.app/settings/api)

```bash
export LINEAR_API_KEY="lin_api_xxxxxxxx"
```

```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "@linear/mcp-server"],
      "env": {
        "LINEAR_API_KEY": "${LINEAR_API_KEY}"
      }
    }
  }
}
```

#### Sentry（錯誤追蹤）

1. 取得 Auth Token：[sentry.io/settings/auth-tokens](https://sentry.io/settings/auth-tokens/)

```bash
export SENTRY_AUTH_TOKEN="sntrys_xxxxxxxx"
```

```json
{
  "mcpServers": {
    "sentry": {
      "command": "npx",
      "args": ["-y", "@sentry/mcp-server"],
      "env": {
        "SENTRY_AUTH_TOKEN": "${SENTRY_AUTH_TOKEN}"
      }
    }
  }
}
```

### Step 4：驗證 MCP 連線

```bash
# 啟動 Claude Code
claude

# 方法一：用 /mcp 指令
> /mcp

# 方法二：用 /status 指令
> /status

# 方法三：直接詢問
> 列出目前可用的 MCP 工具

# 方法四：測試 GitHub MCP
> 用 GitHub MCP 搜尋我的 repositories
```

### 環境變數速查表

| 環境變數 | 用途 | 取得方式 |
|---------|------|---------|
| `GITHUB_TOKEN` | GitHub MCP (PRs, Issues, Repos) | [github.com/settings/tokens](https://github.com/settings/tokens?type=beta) |
| `DATABASE_URL` | PostgreSQL MCP | 你的資料庫連線字串 |
| `SLACK_BOT_TOKEN` | Slack MCP | [api.slack.com/apps](https://api.slack.com/apps) |
| `SLACK_TEAM_ID` | Slack MCP | Slack Workspace 設定 |
| `LINEAR_API_KEY` | Linear MCP | [linear.app/settings/api](https://linear.app/settings/api) |
| `SENTRY_AUTH_TOKEN` | Sentry MCP | [sentry.io/settings/auth-tokens](https://sentry.io/settings/auth-tokens/) |
| `ANTHROPIC_API_KEY` | Claude API (自帶 key 時) | [console.anthropic.com](https://console.anthropic.com/) |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 自動壓縮閾值 | 設定值（如 `50`） |

---

## .gitignore 建議

在專案的 `.gitignore` 中加入：

```gitignore
# Claude Code 本地設定（不要提交，含 token/密鑰）
.claude/settings.local.json
CLAUDE.local.md

# 以下檔案可以提交（團隊共享）
# .claude/settings.json      ← 可提交（專案權限 + hooks）
# .claude/agents/             ← 可提交（子代理定義）
# .claude/commands/            ← 可提交（自訂指令）
# .claude/skills/              ← 可提交（工作流程）
# .claude/rules/               ← 可提交（編碼規範）
# .mcp.json                    ← 可提交（使用 ${VAR} 引用密鑰，不含明文 token）
# CLAUDE.md                    ← 可提交（專案指引）
```

---

## 指令完全參考

### Claude Code 內建指令（全部）

| 指令 | 功能 | 使用時機 |
|------|------|---------|
| `/help` | 顯示所有可用指令與用法 | 不確定時 |
| `/model <name>` | 切換模型 (sonnet/opus/haiku) | sonnet 預設，opus 用於複雜推理 |
| `/clear` | 清空對話記錄，重置 session | 切換不相關任務時（免費、即時） |
| `/compact [instruction]` | 壓縮上下文保留摘要 | 邏輯斷點（研究完→實作前） |
| `/cost` | 顯示本次 session token 花費 | 監控成本消耗 |
| `/config` | 開啟配置管理介面 | 修改 permissions/model/env |
| `/memory` | 讀取/新增持久化記憶 | 儲存跨 session 需保留的資訊 |
| `/mcp` | 管理 MCP 伺服器連線 | 啟用/停用/檢查 MCP 狀態 |
| `/permissions` | 檢視/修改工具權限 | 調整 allow/deny 規則 |
| `/status` | 顯示環境狀態（設定、MCP、模型） | 確認配置是否正確載入 |
| `/doctor` | 診斷環境問題 | 功能異常時除錯 |
| `/bug` | 回報 Claude Code 自身 bug | Claude 行為不符預期時 |
| `/login` | 重新登入 API | Token 過期 |
| `/logout` | 登出 | 切換帳號 |
| `/vim` | 切換 vim 鍵位模式 | 偏好 vim 操作 |
| `/terminal-setup` | 設定終端整合（Shift+Enter） | 初次設定 |
| `/init` | 初始化 CLAUDE.md 到專案 | 新專案 |
| `/review` | 審查目前未提交的變更 | 提交前自動審查 |
| `/pr-review` | 審查指定 GitHub PR | PR 到來時 |
| `/add-dir <path>` | 新增工作目錄到 session | 多目錄/monorepo 專案 |

### CLI 啟動指令

| 指令 | 功能 |
|------|------|
| `claude` | 啟動互動式 REPL |
| `claude "prompt"` | 單次對話後退出 |
| `claude -p "prompt"` | 管道模式（無互動 UI） |
| `claude -c` | 繼續上次中斷的對話 |
| `claude --model opus` | 以指定模型啟動 |
| `claude --allowedTools "..."` | 啟動時限制工具 |
| `cat file | claude -p "review"` | 管道輸入 |
| `claude mcp` | MCP 伺服器管理 CLI |
| `claude config` | 配置管理 CLI |
| `claude update` | 更新 Claude Code |

### 本配置自訂 Slash 指令

| 指令 | 功能 | 說明 |
|------|------|------|
| `/scaffold <描述>` | 生成 FastAPI + Vue 服務骨架 | Docker, .env.example, README, tests 一次到位 |
| `/plan <描述>` | 建立詳細實作計畫 | 使用 planner (opus) 規劃，不寫 code，等確認 |
| `/commit` | 分析 staged 變更，生成 Conventional Commit | 顯示預覽，確認後才執行 |
| `/debug <錯誤描述>` | 結構化除錯流程 | Reproduce→Isolate→Diagnose→Fix→Verify |
| `/code-review [PR#]` | 全面程式碼審查 | 本地 diff 或 GitHub PR 7 階段審查 |
| `/build-fix` | 修復所有 build/type 錯誤 | 偵測→解析→修復迴圈→驗證 |
| `/refactor-clean` | 偵測並移除 dead code | 安全分級：SAFE/CAUTION/DANGER |
| `/quality-gate` | 品質管線（format+lint+type+test+security） | 一鍵執行 6 項檢查 |
| `/python-review [path]` | Python 專屬程式碼審查 | PEP8/typing/FastAPI/security |
| `/test-coverage [path]` | 測試覆蓋率分析 | 找出未覆蓋的程式碼，建議補測試 |
| `/update-docs` | 同步文件與程式碼 | 偵測 code 變更並更新對應文件 |

### Skills（工作流程）

| Skill | 功能 | 引用方式 |
|-------|------|---------|
| `tdd-workflow` | Red-Green-Refactor TDD 循環 | "用 tdd-workflow 實作這功能" |
| `debug-workflow` | 結構化除錯：Reproduce→Isolate→Diagnose→Fix→Verify | "用 debug-workflow 找這個 bug" |
| `search-first` | 研究優先，讀完再寫 | "用 search-first 研究這個 API" |
| `api-design` | FastAPI REST API 設計模式 | "用 api-design 建 CRUD endpoints" |
| `docker-patterns` | Docker/Compose 最佳實踐 | "用 docker-patterns 寫 Dockerfile" |
| `security-review` | OWASP Top 10 安全檢查 | "跑 security-review 檢查" |
| `verification-loop` | Build→Type→Lint→Format→Test→Security | "跑 verification-loop 確認一切正常" |
| `strategic-compact` | Context 管理策略 | 長 session 時自動建議 |

### Agents（子代理）

| Agent | 職責 | 模型 | 可用工具 |
|-------|------|------|---------|
| `planner` | 任務規劃（不寫 code） | opus | Read, Grep, Glob |
| `code-reviewer` | 品質+安全+模式審查 | sonnet | Read, Grep, Glob, Bash |
| `tdd-guide` | TDD 流程執行 | sonnet | Read, Write, Edit, Bash, Grep |
| `security-reviewer` | 安全漏洞偵測 | sonnet | Read, Write, Edit, Bash, Grep, Glob |
| `build-error-resolver` | Build 錯誤修復 | sonnet | Read, Write, Edit, Bash, Grep, Glob |
| `python-reviewer` | Python 專屬審查 | sonnet | Read, Grep, Glob, Bash |
| `refactor-cleaner` | Dead code 清理 | sonnet | Read, Write, Edit, Bash, Grep, Glob |

---

## 配置架構

```
claude-code/
├── README.md                      # 本文件（完整教學）
│
├── global/                        # ═══ 全域版（→ ~/.claude/）═══
│   ├── CLAUDE.md                  # → ~/CLAUDE.md（個人偏好）
│   ├── settings.json              # → ~/.claude/settings.json（通用權限、模型）
│   └── mcp.json                   # → ~/.claude/mcp.json（通用 MCP）
│
├── project/                       # ═══ 專案版（→ <project>/.claude/）═══
│   ├── CLAUDE.md                  # → <project>/CLAUDE.md（專案記憶模板）
│   ├── .mcp.json                  # → <project>/.mcp.json（專案 MCP）
│   └── .claude/
│       ├── settings.json          # 專案設定：權限、hooks、環境變數
│       ├── settings.local.json.example  # 本地密鑰範本（複製後填入 token）
│       ├── agents/                # 7 個 AI 子代理
│       │   ├── planner.md
│       │   ├── code-reviewer.md
│       │   ├── tdd-guide.md
│       │   ├── security-reviewer.md
│       │   ├── build-error-resolver.md
│       │   ├── python-reviewer.md
│       │   └── refactor-cleaner.md
│       ├── commands/              # 11 個自訂 Slash 指令
│       │   ├── scaffold.md
│       │   ├── plan.md
│       │   ├── commit.md
│       │   ├── debug.md
│       │   ├── code-review.md
│       │   ├── build-fix.md
│       │   ├── refactor-clean.md
│       │   ├── quality-gate.md
│       │   ├── python-review.md
│       │   ├── test-coverage.md
│       │   └── update-docs.md
│       ├── skills/                # 8 個工作流程技能
│       │   ├── tdd-workflow/SKILL.md
│       │   ├── debug-workflow/SKILL.md
│       │   ├── search-first/SKILL.md
│       │   ├── api-design/SKILL.md
│       │   ├── docker-patterns/SKILL.md
│       │   ├── security-review/SKILL.md
│       │   ├── verification-loop/SKILL.md
│       │   └── strategic-compact/SKILL.md
│       └── rules/                 # 永遠遵循的規範（自動載入）
│           ├── common/
│           │   ├── coding-style.md
│           │   ├── git-workflow.md
│           │   ├── testing.md
│           │   └── security.md
│           ├── python/
│           │   └── python-fastapi.md
│           ├── vue/
│           │   └── vue-rules.md
│           └── docker/
│               └── docker-rules.md
│
├── .claude/                       # ═══ 舊版統一配置（保留相容）═══
│   └── ...
│
└── tutorial/                      # 教學文件（15 篇）
    ├── 01-INSTALLATION.md
    └── ...
```

### 安裝後的檔案位置對照

```
全域版安裝後：                          專案版安裝後：
~/                                     <project>/
├── CLAUDE.md          ← 個人偏好       ├── CLAUDE.md              ← 專案規範
└── .claude/                           ├── .mcp.json              ← 專案 MCP
    ├── settings.json  ← 通用權限       └── .claude/
    └── mcp.json       ← 通用 MCP          ├── settings.json      ← 專案權限 + hooks
                                           ├── settings.local.json ← 本地密鑰（⚠️ 不提交 Git）
                                           ├── agents/
                                           ├── commands/
                                           ├── skills/
                                           └── rules/
```

---

## Hooks（自動觸發）

配置在 `settings.json` 的 `hooks` 區段，無需額外腳本：

| 觸發時機 | 條件 | 動作 |
|---------|------|------|
| PostToolUse (Edit/Write) | `.py` 檔案 | 自動 `ruff format` + `ruff check --fix` |
| PostToolUse (Edit/Write) | `.ts/.tsx/.vue/.js/.jsx/.css/.json` 檔案 | 自動 `prettier --write` |
| PostToolUse (Edit/Write) | `.ts/.tsx/.vue/.js/.jsx` 檔案 | 偵測並警告殘留 `console.log` |
| PreToolUse (Bash) | `git push` / `docker push` | 提醒先跑 `/quality-gate` |
| PreToolUse (Bash) | `rm -rf` / `DROP TABLE` / `truncate` | 警告破壞性指令 |

---

## Token 最佳化策略

| 設定 | 值 | 效果 |
|------|---|------|
| `model` | `sonnet` | 預設用 Sonnet（成本降低 ~60%） |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `50` | 50% context 即觸發自動壓縮 |
| `/model opus` | 臨時切換 | 僅用於複雜架構推理或 planner |
| `/clear` | 切換任務時 | 免費即時重置（不同任務間） |
| `/compact` | 邏輯斷點 | 保留摘要，釋放 context |
| MCP 數量 | ≤5 個 | 每個 MCP 佔用 context window |

---

## 開發流程

### 新服務從零啟動
```
/scaffold "task-api: task management"        → 生成完整骨架（Docker, env, tests）
                                             → cd <service> && cp .env.example .env
                                             → docker compose up -d
/plan "實作功能 X"                           → planner 產出計畫，確認後開始
```

### 新功能開發
```
/plan "Add user authentication with JWT"    → planner 產出計畫
                                             → 確認後開始
使用 tdd-workflow skill                      → 寫測試 → 實作 → 重構
/code-review                                 → 審查品質
/quality-gate                                → 跑完整管線
/commit                                      → 智慧型 Conventional Commit
```

### Bug 修復
```
/debug "錯誤訊息或描述"                      → Reproduce→Isolate→Diagnose
使用 debug-workflow skill                    → 系統化定位根因
使用 tdd-workflow skill                      → 先寫 regression test → 實作修復
/build-fix                                   → 確保 build 通過
```

### 程式碼清理
```
/refactor-clean                              → 偵測並移除 dead code
/test-coverage                               → 確認覆蓋率未下降
/quality-gate                                → 嚴格品質檢查
```

### 安全審查
```
使用 security-review skill                   → OWASP Top 10 檢查
/python-review                               → Python 安全模式
/quality-gate                                → bandit + npm audit
```

---

## MCP 伺服器

### 全域版預設 MCP（`global/mcp.json` → `~/.claude/mcp.json`）

| MCP | 用途 | 需要 Key | 放全域原因 |
|-----|------|---------|-----------|
| `github` | PR/Issue/Repo/Code Search | GitHub PAT | 所有專案都需要 |
| `context7` | 即時查詢任何框架/函式庫文件 | 無 | 通用工具 |
| `sequential-thinking` | 複雜推理鏈分解 | 無 | 通用工具 |
| `memory` | 跨 session 持久記憶 | 無 | 個人記憶 |

### 專案版預設 MCP（`project/.mcp.json` → `<project>/.mcp.json`）

| MCP | 用途 | 需要 Key | 放專案原因 |
|-----|------|---------|-----------|
| `github` | PR/Issue/Repo/Code Search | `${GITHUB_TOKEN}` | 使用環境變數引用 |
| `context7` | 即時查詢文件 | 無 | — |
| `sequential-thinking` | 複雜推理鏈分解 | 無 | — |
| `playwright` | 瀏覽器自動化 / E2E 測試 | 無 | 前端專案才需要 |
| `memory` | 跨 session 持久記憶 | 無 | — |

### 可選 MCP（按需新增）

| MCP | 用途 | 需要 Key | 建議位置 |
|-----|------|---------|---------|
| `postgres` | 資料庫查詢 | `${DATABASE_URL}` | 專案 |
| `slack` | Slack 訊息 | `${SLACK_BOT_TOKEN}` | 全域或專案 |
| `linear` | 專案管理 | `${LINEAR_API_KEY}` | 全域 |
| `sentry` | 錯誤追蹤 | `${SENTRY_AUTH_TOKEN}` | 專案 |
| `filesystem` | 擴展檔案操作 | 無 | 專案 |
| `fetch` | HTTP 請求 | 無 | 全域 |
| `puppeteer` | 瀏覽器控制 | 無 | 專案 |

> 保持全域 + 專案 MCP 總數 ≤ 10 以避免 context 被過度佔用。

### MCP 環境變數設定（完整教學見上方「MCP 環境變數完整設定」章節）

---

## 啟用 / 停用元件

### 全域版

```bash
# 修改全域偏好
nano ~/CLAUDE.md

# 修改全域權限或模型
nano ~/.claude/settings.json

# 新增/移除全域 MCP
claude mcp add fetch -- npx -y @modelcontextprotocol/server-fetch
claude mcp remove memory
```

### 專案版

```bash
# 停用某個 agent
rm <project>/.claude/agents/refactor-cleaner.md

# 停用某個 rule（例如純後端專案不需要 Vue rule）
rm <project>/.claude/rules/vue/vue-rules.md

# 停用 hooks（在 settings.json 中刪除 hooks 區段）

# 新增自訂 rule
echo "# My Rule" > <project>/.claude/rules/common/my-rule.md

# 新增自訂 command
cat > <project>/.claude/commands/my-cmd.md << 'EOF'
---
description: My custom command
---
# My Command
Do something useful.
EOF

# 新增專案 MCP
claude mcp add postgres -- npx -y @modelcontextprotocol/server-postgres "$DATABASE_URL"
```

---

## 需求環境

| 工具 | 用途 | 安裝指令 |
|------|------|---------|
| Claude Code CLI ≥2.1 | AI 編程助手 | `npm install -g @anthropic-ai/claude-code` |
| Python ≥3.11 | Python 後端執行環境 | [python.org](https://python.org) |
| Node.js ≥20 | 前端工具鏈 + MCP 執行環境 | [nodejs.org](https://nodejs.org) |
| ruff | Python formatter + linter | `pip install ruff` |
| mypy | Python type checker | `pip install mypy` |
| bandit | Python security scanner | `pip install bandit` |
| prettier | TS/Vue/React formatter | `npm install -g prettier` |
| Docker | 容器化 | [docker.com](https://docker.com) |
| gh | GitHub CLI (PR review 用) | `brew install gh` / `winget install GitHub.cli` |

---

## 教學文件

| # | 文件 | 主題 | 難度 |
|---|------|------|------|
| 01 | [安裝與環境設定](tutorial/01-INSTALLATION.md) | 安裝 Claude Code | ⭐ |
| 02 | [基礎使用](tutorial/02-BASIC-USAGE.md) | 對話模式、斜線指令 | ⭐ |
| 03 | [設定檔系統](tutorial/03-CONFIGURATION.md) | CLAUDE.md、.claude/ | ⭐⭐ |
| 04 | [記憶系統](tutorial/04-MEMORY-SYSTEM.md) | 三層記憶架構 | ⭐⭐ |
| 05 | [Prompt 工程](tutorial/05-PROMPT-ENGINEERING.md) | 高效指令策略 | ⭐⭐ |
| 06 | [Agent 模式](tutorial/06-AGENT-MODE.md) | 自主任務執行 | ⭐⭐⭐ |
| 07 | [MCP 整合](tutorial/07-MCP-INTEGRATION.md) | 外部工具串接 | ⭐⭐⭐ |
| 08 | [進階工作流程](tutorial/08-ADVANCED-WORKFLOWS.md) | 多檔編輯、Git | ⭐⭐⭐ |
| 09 | [自訂 Skills/Agents](tutorial/09-CUSTOM-SKILLS-AGENTS.md) | 建立專屬配置 | ⭐⭐⭐⭐ |
| 10 | [最佳實踐](tutorial/10-BEST-PRACTICES.md) | 效率秘訣 | ⭐⭐⭐⭐ |
| 11 | [疑難排解](tutorial/11-TROUBLESHOOTING.md) | 常見問題 | ⭐⭐ |
| 12 | [Discord 遠端開發](tutorial/12-DISCORD-REMOTE.md) | Remote Control | ⭐⭐⭐ |
| 13 | [模型配置](tutorial/13-MODEL-CONFIGURATION.md) | 本地/第三方模型 | ⭐⭐⭐ |
| 14 | [Claude Design](tutorial/14-CLAUDE-DESIGN.md) | 前端設計 Skill | ⭐⭐ |
| 15 | [完整使用情境](tutorial/15-USAGE-SCENARIO.md) | 端到端開發範例 | ⭐⭐⭐ |
| 16 | [聊天室 Repo 管理](tutorial/16-CHAT-REPO-MANAGEMENT.md) | Slack/Discord 管理 Repo | ⭐⭐⭐⭐ |
| 17 | [Harness Agent](tutorial/17-HARNESS-AGENT.md) | 程式化運行 Agent / CI | ⭐⭐⭐ |
| 18 | [Dynamic Workflows](tutorial/18-WORKFLOWS.md) | 大規模子代理編排 | ⭐⭐⭐⭐ |

---

## 配置檔目錄

| 目錄 | 說明 |
|------|------|
| `configs/chat-repo/` | 聊天室 ↔ Repo 映射設定 |
| `configs/harness/` | Agent SDK / CI 自動化腳本 |
| `configs/workflows/` | Dynamic Workflows 設定 |

---

## 參考

- [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) — 175K+ stars 的完整配置系統
- [Claude Code 官方文件](https://docs.anthropic.com/en/docs/claude-code)
- [Claude Code Settings Schema](https://json.schemastore.org/claude-code-settings.json)
