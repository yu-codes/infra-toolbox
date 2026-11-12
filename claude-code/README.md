# Claude Code 基礎設定檔白板

本目錄提供**一份**通用的 Claude Code 基礎設定（白板）。這份白板是唯一正本，要用時就整包複製到需要它生效的位置（某台主機或某個專案）。
規則以**通用、基礎**為主，實際使用時再依需求增修。

> 已不再維護「全域版 / 專案版」兩套內容 —— 現在只有這一份白板，複製到不同位置就是了，內容都一樣。

---

## 目錄結構

```
claude-code/
├── README.md                 # 本文件
├── .mcp.json                 # MCP 伺服器範本（→ 專案 .mcp.json 或用 claude mcp add）
├── .claude/                  # ═══ 基礎設定白板（可整包複製）═══
│   ├── CLAUDE.md             # 偏好設定：語言、工作原則、編碼風格、安全
│   ├── settings.json         # 工具權限、env、模型偏好
│   └── rules/                # 每次 session 自動載入的規則目錄
│       └── .gitkeep          #   通用規則已併入 CLAUDE.md；此處留作 path-scoped 規則擴充點
└── tutorial/                 # 教學文件（21 篇）
```

---

## 官方檔案位置對照

**同一份白板內容**複製到不同位置時，各檔案的官方合法路徑（本白板已符合此標準）：

| 檔案 | 複製到某台主機（`~/.claude/`） | 複製到某個專案（`./.claude/`） |
|------|------|------|
| **CLAUDE.md** | `~/.claude/CLAUDE.md` | `./CLAUDE.md` **或** `./.claude/CLAUDE.md`（兩者皆為官方位置） |
| **settings.json** | `~/.claude/settings.json` | `./.claude/settings.json` |
| **settings.local.json**（本地密鑰，不提交） | — | `./.claude/settings.local.json` |
| **rules/** | `~/.claude/rules/` | `./.claude/rules/` |
| **MCP 設定** | `~/.claude.json` | `./.mcp.json` |

> 這張表不是「兩種版本」，是同一份內容放到不同位置時檔案該落在哪。`CLAUDE.md` 放在專案根目錄或 `.claude/` 內皆為官方合法位置；本白板統一放在 `.claude/CLAUDE.md`，好處是整個 `.claude/` 可當成一個單位整包複製。
>
> `.claude/rules/*.md` 會在每次 session 自動載入，優先級與 `.claude/CLAUDE.md` 相同；可用 YAML frontmatter 的 `paths` 欄位限定只在特定檔案類型時才載入。

---

## 快速開始（部署白板）

只有**一份**白板。要用時整包複製到你要它生效的位置即可 —— 內容都一樣，差別只在「放哪」。

**複製到某個專案**（隨專案版控，僅該專案生效）：

```bash
cp -r .claude <your-project>/.claude       # 整包複製 CLAUDE.md、settings.json、rules/
cp .mcp.json <your-project>/.mcp.json       # MCP（可選；需設定 GITHUB_TOKEN）
echo '.claude/settings.local.json' >> <your-project>/.gitignore
echo 'CLAUDE.local.md' >> <your-project>/.gitignore
```

**複製到某台主機**（該機器所有專案共用）：

```bash
cp -r .claude/. ~/.claude/                  # 內容進 ~/.claude/
# MCP 建議用 claude mcp add（見下方「MCP 設定」）
```

> 以上兩者是**同一份白板**放到不同位置，不是兩套設定。若兩處同時存在，載入優先級（低 → 高）：`~/.claude/` → 專案 `.claude/` → `.claude/settings.local.json` → 對話指令。

---

## `.claude/` 內容說明

### `CLAUDE.md` — 偏好設定

每次 session 開頭自動載入，包含：

- **語言與溝通**：繁體中文回覆、英文註解、Conventional Commits
- **工作原則**（通用鐵則）：
  1. 先講清楚假設 — 不確定就先問，不要自己猜
  2. 不要過度工程化 — 能簡單解決就不加戲
  3. 不碰無關範圍 — 修 bug 就修，不要順手重構全世界
  4. 做完必須驗證 — 跑測試、看結果、確認真的可用
  5. 不主動生成沒有明確指令要求的開發文件
- **編碼風格**：優先使用標準庫
- **安全原則**：不硬編碼密鑰、敏感資訊進環境變數、OWASP Top 10、驗證外部輸入

### `settings.json` — 權限與模型

- `permissions.allow`：常用開發工具白名單（git、gh、docker、python/uv/ruff、npm/pnpm/node 等）
- `permissions.deny`：封鎖讀取 `.env`、`*.key`、`*.pem`、`credentials*` 等機密檔案
- `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`：`50`（context 到 50% 即觸發自動壓縮）
- `model`：`sonnet`（預設模型，複雜推理時再 `/model opus`）

### `rules/global.md` — 通用工作規則

自動載入的通用規範（安全、程式碼品質、Git）。這是「白板」層級的基礎規則；各專案可在自己的 `.claude/rules/` 下新增專屬規則（如 `python.md`、`vue.md`）。

---

## MCP 設定

`.mcp.json` 提供四個通用 MCP 伺服器範本：

| MCP | 用途 | 需要 Key |
|-----|------|---------|
| `github` | PR / Issue / Repo / Code Search | `${GITHUB_TOKEN}` |
| `context7` | 即時查詢框架 / 函式庫文件 | 無 |
| `sequential-thinking` | 複雜推理鏈分解 | 無 |
| `memory` | 跨 session 持久記憶 | 無 |

> `github` 使用環境變數 `${GITHUB_TOKEN}` 引用，避免把 token 寫進檔案。

### 設定 GitHub Token

1. 產生 Fine-grained PAT：[GitHub Settings → Personal access tokens](https://github.com/settings/tokens?type=beta)
   - 建議最小權限：Contents / Issues / Pull requests（Read and write）、Metadata（Read-only）
2. 設定環境變數：

   **Linux/macOS**（加入 `~/.bashrc` 或 `~/.zshrc`）：
   ```bash
   export GITHUB_TOKEN="github_pat_xxxxxxxx"
   ```

   **Windows**（PowerShell，永久設定）：
   ```powershell
   [System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'github_pat_xxxxxxxx', 'User')
   ```

### 三種安裝 MCP 的方式

```bash
# 方式一：CLI 自動寫入使用者層級 ~/.claude.json（最簡單）
claude mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_TOKEN -- npx -y @modelcontextprotocol/server-github

# 方式二：複製 .mcp.json 到專案根目錄（隨專案版控，用 ${VAR} 引用）
cp .mcp.json <your-project>/.mcp.json

# 方式三：寫入專案本地設定 <project>/.claude/settings.local.json（不提交 Git）
```

### 驗證 MCP

```bash
claude          # 啟動
> /mcp          # 檢視 MCP 連線狀態
> /status       # 檢視整體環境（設定、MCP、模型）
```

### 常用環境變數速查

| 環境變數 | 用途 | 取得方式 |
|---------|------|---------|
| `GITHUB_TOKEN` | GitHub MCP | [github.com/settings/tokens](https://github.com/settings/tokens?type=beta) |
| `ANTHROPIC_API_KEY` | Claude API（自帶 key 時） | [console.anthropic.com](https://console.anthropic.com/) |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 自動壓縮閾值 | 設定值（如 `50`） |

---

## .gitignore 建議

```gitignore
# Claude Code 本地設定（不提交，含 token/密鑰）
.claude/settings.local.json
CLAUDE.local.md

# 以下可提交（團隊共享）：
# .claude/CLAUDE.md          ← 專案指引
# .claude/settings.json      ← 專案權限
# .claude/rules/             ← 編碼規範
# .mcp.json                  ← 用 ${VAR} 引用密鑰，不含明文 token
```

---

## 指令參考

### Claude Code 內建指令（常用）

| 指令 | 功能 | 使用時機 |
|------|------|---------|
| `/help` | 顯示所有可用指令 | 不確定時 |
| `/model <name>` | 切換模型 (sonnet/opus/haiku) | sonnet 預設，opus 用於複雜推理 |
| `/clear` | 清空對話、重置 session | 切換不相關任務時（免費、即時） |
| `/compact [instruction]` | 壓縮上下文保留摘要 | 邏輯斷點（研究完→實作前） |
| `/cost` | 顯示本次 session token 花費 | 監控成本 |
| `/config` | 開啟配置管理介面 | 修改 permissions/model/env |
| `/memory` | 檢視/編輯載入的記憶與規則檔 | 確認 CLAUDE.md / rules 是否載入 |
| `/mcp` | 管理 MCP 伺服器連線 | 啟用/停用/檢查 MCP |
| `/permissions` | 檢視/修改工具權限 | 調整 allow/deny |
| `/status` | 顯示環境狀態 | 確認配置正確載入 |
| `/doctor` | 診斷環境問題 | 功能異常除錯 |
| `/init` | 產生專案 CLAUDE.md | 新專案 |
| `/review` | 審查未提交的變更 | 提交前 |

### CLI 啟動指令

| 指令 | 功能 |
|------|------|
| `claude` | 啟動互動式 REPL |
| `claude "prompt"` | 單次對話後退出 |
| `claude -p "prompt"` | 管道模式（無互動 UI） |
| `claude -c` | 繼續上次對話 |
| `claude --model opus` | 以指定模型啟動 |
| `claude mcp` | MCP 伺服器管理 CLI |
| `claude update` | 更新 Claude Code |

---

## 需求環境

| 工具 | 用途 | 安裝指令 |
|------|------|---------|
| Claude Code CLI | AI 編程助手 | `npm install -g @anthropic-ai/claude-code` |
| Node.js ≥20 | MCP 執行環境 | [nodejs.org](https://nodejs.org) |
| gh | GitHub CLI（PR review） | `brew install gh` / `winget install GitHub.cli` |

> 其餘語言工具鏈（Python、ruff、mypy、Docker 等）依專案需求安裝；`settings.json` 的權限白名單已預留常見工具。

---

## 教學文件

| # | 文件 | 主題 | 難度 |
|---|------|------|------|
| 01 | [安裝與環境設定](tutorial/01-INSTALLATION.md) | 安裝 Claude Code | ⭐ |
| 02 | [基礎使用](tutorial/02-BASIC-USAGE.md) | 對話模式、斜線指令 | ⭐ |
| 03 | [設定檔系統](tutorial/03-CONFIGURATION.md) | CLAUDE.md、.claude/ | ⭐⭐ |
| 04 | [記憶系統](tutorial/04-MEMORY-SYSTEM.md) | CLAUDE.md + Auto Memory | ⭐⭐ |
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
| 19 | [多渠道機器人](tutorial/19-MULTI-CHANNEL-BOT.md) | Discord/Slack/Telegram Bot | ⭐⭐⭐⭐ |
| 20 | [Token & Context 可視化](tutorial/20-TOKEN-CONTEXT-VISUALIZATION.md) | 成本監測 | ⭐⭐⭐ |
| 21 | [本地模型整合](tutorial/21-LOCAL-MODELS.md) | Ollama / LM Studio / Llama.cpp | ⭐⭐⭐⭐ |
