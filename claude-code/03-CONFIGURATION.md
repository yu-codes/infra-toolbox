# 03 — 設定檔系統

Claude Code 使用分層設定架構，讓你在不同層級（全域 → 專案 → 對話）精確控制行為。

## 設定層級總覽

```
優先級（低 → 高）：

1. 全域設定          ~/.claude/settings.json
2. 企業策略          由組織管理員配發
3. 專案設定          .claude/settings.json（可提交 Git）
4. 專案本地設定      .claude/settings.local.json（Git 忽略）
5. CLAUDE.md        專案指令檔
6. 對話中指令        即時下達的 /config 或自然語言指示
```

## CLAUDE.md — 核心指令檔

CLAUDE.md 是 Claude Code 自動讀取的指令文件。Claude 在啟動時會載入它，作為整個對話的系統背景。

> ⚠️ **官方建議：保持 CLAUDE.md 簡潔。** 過長的 CLAUDE.md 會稀釋 Claude 的注意力。
> 每條指令用一行說完，刪掉多餘的解釋和範例。

### 放置位置與作用範圍

| 位置 | 作用範圍 | 說明 |
|------|---------|------|
| `~/CLAUDE.md` | 全域 | 所有專案共用的偏好設定 |
| `專案根/CLAUDE.md` | 專案 | 專案特定的規範和上下文 |
| `專案根/.claude/CLAUDE.md` | 專案 | 同上，替代位置 |
| `子目錄/CLAUDE.md` | 子目錄 | 該子目錄特定的規範（進入時載入） |
| `CLAUDE.local.md` | 本地 | 個人偏好，不提交到 Git |

### CLAUDE.md 範例（簡潔版 — 官方推薦風格）

```markdown
# 專案指引

FastAPI + PostgreSQL 電商後端 API。Python 3.12、SQLAlchemy 2.0、Redis caching。

## 規範
- PEP 8，行寬 120，所有函式加 type hints
- commit: conventional commits，繁體中文
- 新功能必須附單元測試，覆蓋率 ≥ 80%
- 測試: `pytest tests/ -v`
- 不修改 migrations/ 已有檔，敏感資訊存 .env

## 目錄
src/api/ — routes | src/domain/ — models + logic | src/infrastructure/ — DB, external | tests/

@docs/API_SPEC.md      ← 引入 API 規格
@docs/ARCHITECTURE.md  ← 引入架構文件
```

### `@` 引入語法（Import Syntax）

CLAUDE.md 支援用 `@` 引入其他檔案的內容，讓你把詳細說明拆到專用檔案，CLAUDE.md 本身保持簡潔：

```markdown
# CLAUDE.md
這是一個 FastAPI 專案。規範見下方引入。

@docs/CODING_STANDARDS.md
@docs/API_CONVENTIONS.md
@docs/TESTING_GUIDE.md
@.claude/skills/ddd-developer/SKILL.md
```

> `@` 路徑相對於 CLAUDE.md 所在目錄。Claude 會在需要時才載入引用的檔案，不會全部塊入上下文。

### 用 /init 自動產生 CLAUDE.md

```bash
# 讓 Claude 分析你的專案後自動產生
claude
> /init

# Claude 會：
# 1. 掃描專案結構
# 2. 分析程式語言和框架
# 3. 讀取已有的 README、package.json 等
# 4. 產生客製化的 CLAUDE.md
```

## .mcp.json — MCP 伺服器設定檔

除了在 `settings.json` 中設定 MCP 伺服器，Claude Code 也支援專用的 `.mcp.json` 檔案：

```json
// 專案根目錄/.mcp.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
    }
  }
}
```

快速新增 MCP 伺服器的 CLI 指令：

```bash
# 新增 MCP 伺服器（互動式引導）
claude mcp add github -- npx -y @modelcontextprotocol/server-github

# 列出已設定的 MCP 伺服器
claude mcp list

# 移除 MCP 伺服器
claude mcp remove github
```

## settings.json 設定檔

### 全域設定 `~/.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "mcp__github__create_pull_request"
    ],
    "deny": [
      "mcp__shell__dangerous_command"
    ]
  },
  "env": {
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "16000",
    "ANTHROPIC_MODEL": "claude-sonnet-4-20250514"
  }
}
```

### 專案設定 `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "Bash(npm test:*)",
      "Bash(npx prettier:*)",
      "Bash(npx eslint:*)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push --force)"
    ]
  },
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 本地設定 `.claude/settings.local.json`

```json
{
  "env": {
    "DATABASE_URL": "postgresql://localhost:5432/mydb",
    "GITHUB_TOKEN": "ghp_xxxx"
  },
  "permissions": {
    "allow": [
      "Bash(docker compose *)"
    ]
  }
}
```

> 💡 `.local.json` 適合存放個人環境特定的設定，加入 `.gitignore` 避免洩漏。

## 權限規則語法

### Bash 指令白名單模式

```json
{
  "permissions": {
    "allow": [
      "Bash(npm *)",           // 允許所有 npm 開頭的指令
      "Bash(npx prettier *)",  // 允許 prettier 格式化
      "Bash(python -m pytest *)", // 允許 pytest
      "Bash(git status)",      // 只允許 git status
      "Bash(docker compose up *)", // 允許 docker compose up
      "Bash(ls *)",            // 允許 ls
      "Bash(cat *)"            // 允許 cat
    ],
    "deny": [
      "Bash(rm -rf /)",        // 禁止危險刪除
      "Bash(git push --force *)", // 禁止強制推送
      "Bash(sudo *)",          // 禁止 sudo
      "Bash(curl * | bash)",   // 禁止管道執行
      "Bash(chmod 777 *)"     // 禁止開放所有權限
    ]
  }
}
```

### MCP 工具權限

```json
{
  "permissions": {
    "allow": [
      "mcp__github__create_issue",
      "mcp__github__create_pull_request",
      "mcp__filesystem__read_file"
    ],
    "deny": [
      "mcp__filesystem__delete_file"
    ]
  }
}
```

## 環境變數

### Claude Code 專用環境變數

| 變數 | 說明 | 範例值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | API 金鑰 | `sk-ant-xxx` |
| `ANTHROPIC_MODEL` | 預設模型 | `claude-sonnet-4-20250514` |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | 最大輸出 tokens | `16000` |
| `CLAUDE_CODE_USE_BEDROCK` | 使用 AWS Bedrock | `1` |
| `CLAUDE_CODE_USE_VERTEX` | 使用 Google Vertex | `1` |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 停用遙測 | `1` |
| `HTTP_PROXY` / `HTTPS_PROXY` | 代理伺服器 | `http://proxy:8080` |

### 在設定中引用環境變數

```json
{
  "env": {
    "API_KEY": "${MY_SECRET_KEY}"
  },
  "mcpServers": {
    "server": {
      "env": {
        "TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

## Hooks 設定

Hooks 是確定性動作，在特定事件發生時自動執行（不需要 Claude 決定）：

```json
// .claude/settings.json
{
  "hooks": {
    "on_file_edit": [
      {
        "command": "npx prettier --write {{filePath}}",
        "description": "編輯檔案後自動格式化"
      }
    ],
    "on_message_send": [
      {
        "command": "echo 'Claude responded'",
        "description": "Claude 回覆時觸發"
      }
    ],
    "on_tool_use": [
      {
        "command": "npm test -- --bail",
        "tool": "Edit",
        "description": "編輯檔案後自動跑測試"
      }
    ]
  }
}
```

Hooks 可用事件：

| 事件 | 觸發時機 |
|------|----------|
| `on_file_edit` | 檔案被編輯後 |
| `on_message_send` | Claude 回覆後 |
| `on_tool_use` | 工具被呼叫後（可指定工具名） |
| `on_session_start` | 對話啟動時 |

> Hooks 與 MCP / Skill 的差異：Hooks 是「確定性」的——每次事件發生都會執行，不由 Claude 判斷。

## .gitignore 建議

```gitignore
# Claude Code 本地設定（不要提交）
.claude/settings.local.json
CLAUDE.local.md

# 以下檔案可以提交（團隊共享）
# .claude/settings.json  ← 可提交
# .mcp.json               ← 可提交（MCP 設定）
# CLAUDE.md               ← 可提交
```

## 設定優先級實例

假設你有以下設定同時存在：

```
~/.claude/settings.json     → deny: ["Bash(rm *)"]
.claude/settings.json       → allow: ["Bash(rm test_*)"]
.claude/settings.local.json → allow: ["Bash(rm -rf node_modules)"]
```

結果：
- `rm test_output.txt` → ✅ 專案設定允許
- `rm -rf node_modules` → ✅ 本地設定允許
- `rm important_file.py` → ❌ 全域設定拒絕
- deny 規則始終優先於 allow（安全原則）

## 快速設定指南

### 最小化設定（新手友好）

```bash
# 只需要一個 CLAUDE.md
claude
> /init
# 完成！開始使用
```

### 團隊協作設定

```bash
# 1. 產生專案 CLAUDE.md
claude
> /init

# 2. 建立共享設定
mkdir -p .claude
cat > .claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": ["Edit", "Write", "Bash(npm *)"],
    "deny": ["Bash(git push --force *)"]
  }
}
EOF

# 3. 建議隊友建立自己的 local 設定
echo '.claude/settings.local.json' >> .gitignore
echo 'CLAUDE.local.md' >> .gitignore
```

---

⬅️ [上一篇：基礎使用與核心指令](02-BASIC-USAGE.md) | ➡️ [下一篇：記憶系統](04-MEMORY-SYSTEM.md)
