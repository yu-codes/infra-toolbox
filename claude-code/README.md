# Claude Code 全端工程師配置包

針對 **Python + FastAPI + Docker + Vue** 全端技術棧最佳化的 Claude Code 配置。
參考 [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) 設計理念，精簡為單人全端工程師即時可用的配置包。

---

## 快速開始

```bash
# 複製整個 .claude/ 到你的使用者目錄（全域生效）
cp -r .claude/ ~/.claude/

# 或複製到單一專案（僅該專案生效）
cp -r .claude/ <your-project>/.claude/
cp .claude/CLAUDE.md <your-project>/CLAUDE.md
```

MCP 伺服器（可選）：
```bash
cp .claude/mcp.json <your-project>/.mcp.json
# 編輯 .mcp.json，替換 YOUR_GITHUB_PAT_HERE
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
| `/plan <描述>` | 建立詳細實作計畫 | 使用 planner (opus) 規劃，不寫 code，等確認 |
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
.claude/
├── settings.json              # 核心設定：權限、模型、hooks、環境變數
├── CLAUDE.md                  # 專案記憶模板（複製到專案根目錄）
├── mcp.json                   # MCP Server 配置模板
├── agents/                    # 7 個 AI 子代理
│   ├── planner.md
│   ├── code-reviewer.md
│   ├── tdd-guide.md
│   ├── security-reviewer.md
│   ├── build-error-resolver.md
│   ├── python-reviewer.md
│   └── refactor-cleaner.md
├── commands/                  # 8 個自訂 Slash 指令
│   ├── plan.md
│   ├── code-review.md
│   ├── build-fix.md
│   ├── refactor-clean.md
│   ├── quality-gate.md
│   ├── python-review.md
│   ├── test-coverage.md
│   └── update-docs.md
├── skills/                    # 7 個工作流程技能
│   ├── tdd-workflow/SKILL.md
│   ├── search-first/SKILL.md
│   ├── api-design/SKILL.md
│   ├── docker-patterns/SKILL.md
│   ├── security-review/SKILL.md
│   ├── verification-loop/SKILL.md
│   └── strategic-compact/SKILL.md
└── rules/                     # 永遠遵循的規範（自動載入）
    ├── common/
    │   ├── coding-style.md    # KISS、DRY、命名慣例
    │   ├── git-workflow.md    # Conventional Commits、分支策略
    │   ├── testing.md         # 測試策略、覆蓋率目標
    │   └── security.md        # 安全原則、禁止行為
    ├── python/
    │   └── python-fastapi.md  # async、Pydantic v2、service layer
    ├── vue/
    │   └── vue-rules.md       # Composition API、script setup、Pinia
    └── docker/
        └── docker-rules.md    # 多階段建構、非 root、health check
```

---

## Hooks（自動觸發）

配置在 `settings.json` 的 `hooks` 區段，無需額外腳本：

| 觸發時機 | 條件 | 動作 |
|---------|------|------|
| PostToolUse (Edit/Write) | `.py` 檔案 | 自動 `ruff format` + `ruff check --fix` |
| PostToolUse (Edit/Write) | `.ts/.vue/.js` 檔案 | 自動 `prettier --write` |
| PostToolUse (Edit/Write) | `.ts/.vue/.js/.jsx/.tsx` 檔案 | 偵測並警告殘留 `console.log` |
| PreToolUse (Bash) | `git push` / `docker push` | 提醒先跑 `/quality-gate` |

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

### 新功能開發
```
/plan "Add user authentication with JWT"    → planner 產出計畫
                                             → 確認後開始
使用 tdd-workflow skill                      → 寫測試 → 實作 → 重構
/code-review                                 → 審查品質
/quality-gate                                → 跑完整管線
git commit                                   → hook 自動格式化
```

### Bug 修復
```
使用 tdd-workflow skill                      → 先寫 regression test
                                             → 實作修復
/build-fix                                   → 確保 build 通過
/code-review                                 → 確認無 regression
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

| MCP | 用途 | 需要 Key |
|-----|------|---------|
| `github` | PR/Issue/Repo/Code Search | GitHub PAT |
| `context7` | 即時查詢任何框架/函式庫文件 | 無 |
| `sequential-thinking` | 複雜推理鏈分解 | 無 |
| `playwright` | 瀏覽器自動化 / E2E 測試 | 無 |
| `memory` | 跨 session 持久記憶 | 無 |

> 保持 ≤5 個 MCP 以避免 context 被過度佔用。

---

## 啟用 / 停用元件

```bash
# 停用某個 agent
rm ~/.claude/agents/refactor-cleaner.md

# 停用某個 rule（例如純後端專案不需要 Vue rule）
rm ~/.claude/rules/vue/vue-rules.md

# 停用 hooks（在 settings.json 中刪除 hooks 區段）

# 新增自訂 rule
echo "# My Rule" > ~/.claude/rules/common/my-rule.md

# 新增自訂 command
cat > ~/.claude/commands/my-cmd.md << 'EOF'
---
description: My custom command
---
# My Command
Do something useful.
EOF
```

---

## 需求環境

| 工具 | 用途 | 安裝指令 |
|------|------|---------|
| Claude Code CLI ≥2.1 | AI 編程助手 | `npm install -g @anthropic-ai/claude-code` |
| Python ≥3.11 | 後端執行環境 | [python.org](https://python.org) |
| Node.js ≥18 | 前端 + MCP 執行環境 | [nodejs.org](https://nodejs.org) |
| ruff | Python formatter + linter | `pip install ruff` |
| mypy | Python type checker | `pip install mypy` |
| bandit | Python security scanner | `pip install bandit` |
| prettier | Vue/TS formatter | `npm install -g prettier` |
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

---

## 參考

- [Everything Claude Code](https://github.com/affaan-m/everything-claude-code) — 175K+ stars 的完整配置系統
- [Claude Code 官方文件](https://docs.anthropic.com/en/docs/claude-code)
- [Claude Code Settings Schema](https://json.schemastore.org/claude-code-settings.json)
