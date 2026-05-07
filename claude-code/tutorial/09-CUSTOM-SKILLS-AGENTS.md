# 09 — 自訂 Skills、Agents 與 Plugins

透過自訂 Skills、Agents 和 Plugins，你可以讓 Claude Code 成為領域專家，擁有特定的知識和行為模式。

## Skills、Agents、Plugins 的差異

| | Skills | Agents (Subagents) | Plugins |
|---|--------|-----------|--------|
| 定義 | 領域知識 + 工作流程 | 角色定義 + 工具限制 | Claude Code 擴充套件 |
| 位置 | `.claude/skills/` 或 `.github/skills/` | `.claude/agents/` | `/plugin` 安裝 |
| 觸發 | 任務匹配技能描述 | 明確指定使用 | 自動或手動觸發 |
| 內容 | 技術指引、工具使用、範本 | 系統指令、工具限制 | 可執行代碼 + MCP |
| 類比 | 一本教科書 | 一個專業角色 | 一個擴充套件 |

## 自訂 Skills

### Skill 檔案結構

官方推薦放在 `.claude/skills/`（也支援 `.github/skills/`）：

```
.claude/skills/
└── my-skill/
    ├── SKILL.md          # 主要的 Skill 定義檔
    ├── templates/         # 範本檔案（選填）
    ├── scripts/           # 輔助腳本（選填）
    └── reference/         # 參考資料（選填）
```

### SKILL.md 格式

```markdown
---
name: api-designer
description: >
  RESTful API 設計專家。當需要設計、審查或重構 API endpoint 時使用此 Skill。
  涵蓋路由命名、HTTP 方法選擇、狀態碼規範、分頁、版本控制等最佳實踐。
tools:
  - Read File
  - Edit File
  - Grep Search
  - Run Terminal
disable-model-invocation: false   # true = 禁止 Skill 呼叫 AI 模型（純工具式 Skill）
---

# API Designer Skill

## 你的角色
你是 RESTful API 設計專家，負責確保所有 API 遵循一致的設計規範。

## 設計原則

### 路由命名規範
- 使用複數名詞：`/users` 而非 `/user`
- 使用 kebab-case：`/user-profiles` 而非 `/userProfiles`
- 最多 3 層嵌套：`/users/{id}/orders/{orderId}`
- 集合操作使用查詢參數：`/users?role=admin&status=active`

### HTTP 方法對應
| 操作 | HTTP Method | 路由範例 | 回應碼 |
|------|------------|---------|--------|
| 列表 | GET | /users | 200 |
| 取得 | GET | /users/:id | 200 / 404 |
| 建立 | POST | /users | 201 |
| 完整更新 | PUT | /users/:id | 200 / 404 |
| 部分更新 | PATCH | /users/:id | 200 / 404 |
| 刪除 | DELETE | /users/:id | 204 / 404 |

### 回應格式
所有回應統一使用：
\```json
{
  "data": {},
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 100
  },
  "error": null
}
\```

## 工作流程
1. 分析需求，確定需要的 endpoint
2. 設計路由和 HTTP 方法
3. 定義 Request / Response 型別
4. 實作 controller 和 validation
5. 撰寫 API 文件
6. 加上整合測試
```

### Skill 的觸發方式

Claude Code 會根據任務描述自動匹配 Skill：

```
> 設計一個新的 API endpoint

# Claude 讀到任務關鍵詞 "API" "endpoint" "設計"
# 自動載入 api-designer skill
# 按照 skill 中定義的規範和流程執行
```

也可以在 CLAUDE.md 中用 `@` 引入：

```markdown
# CLAUDE.md
@.claude/skills/api-designer/SKILL.md
@.claude/skills/ddd-developer/SKILL.md
```

## 自訂 Agents（Subagents）

### Agent 定義方式

在 `.claude/agents/` 目錄中建立 Markdown 檔案：

```markdown
# .github/AGENTS.md 或 .claude/agents/code-reviewer.md

## 方式一：單一檔案（.claude/agents/）

<!-- .claude/agents/code-reviewer.md -->
---
name: code-reviewer
description: 喴格的程式碼審查專家，專注於品質、安全、效能。
tools:
  - Read File
  - Grep Search
  - Semantic Search
---

你是程式碼審查專家。逐行審查，不放過任何問題。
嚴重問題 🔴 | 建議改善 🟡 | 小問題 🟢
審查後給出整體評分（A-F）。

### test-writer
**描述：** 測試撰寫專家，擅長設計全面的測試案例。

## 方式二：AGENTS.md（集中定義）

```markdown
# .github/AGENTS.md

## test-writer
測試撰寫專家。使用 AAA 模式，優先覆蓋邊界條件和錯誤路徑。

## docs-writer
技術文件撰寫專家。簡潔明瞭，包含程式碼範例，中文文件、英文程式碼。
```

### VS Code 中的 Agent 定義

如果你使用 VS Code + GitHub Copilot Chat，可以建立 `.github/.agent.md` 檔案：

```yaml
# .github/.agent.md
---
name: security-auditor
description: 安全審計專家。專注於發現和修復安全漏洞。
tools:
  - Read File
  - Grep Search
  - Semantic Search
---
你是資安專家。檢查 OWASP Top 10、硬編碼密碼、不安全的密碼學用法。
報告格式：🔴/🟡/🟢 嚴重度 + 📍 檔案行號 + 📝 描述 + 🔧 修復建議
```

## Plugins（擴充套件）

Plugins 是 Claude Code 的擴充機制，可以新增工具、指令和行為：

### 安裝與管理

```
# 在 Claude Code 對話中
> /plugin

# Claude 會引導你瀏覽和安裝可用的 Plugins
```

### Plugin 與 Skill / MCP 的差異

| | Plugin | Skill | MCP Server |
|---|--------|-------|------------|
| 安裝方式 | `/plugin` | 放在 `.claude/skills/` | `claude mcp add` |
| 功能 | 工具 + 指令 + 行為 | 領域知識 + 流程 | 外部工具 / 資料 |
| 執行環境 | Claude Code 內建 | 文字指引 | 獨立進程 |
| 適用場景 | 擴展 Claude 能力 | 規範工作流 | 連接外部系統 |

## 實戰範例：建立完整的 Skill

### DDD 開發 Skill

```markdown
---
name: ddd-developer
description: >
  Domain-Driven Design 開發專家。當需要設計領域模型、建立 bounded context、
  實作 aggregate、使用 repository pattern 時使用此 Skill。
---

# DDD Developer Skill

## 分層架構

\```
src/
├── domain/           # 領域層（純邏輯，無框架依賴）
│   ├── models/       # Aggregate Roots, Entities, Value Objects
│   ├── events/       # Domain Events
│   ├── services/     # Domain Services
│   └── repositories/ # Repository Interfaces
├── application/      # 應用層（Use Cases / Commands / Queries）
│   ├── commands/
│   ├── queries/
│   └── services/
├── infrastructure/   # 基礎設施層（具體實作）
│   ├── persistence/  # Repository 實作
│   ├── messaging/    # Event Bus 實作
│   └── external/     # 外部 API 接口
└── presentation/     # 展示層（Controllers, DTOs）
    ├── controllers/
    └── dtos/
\```

## 命名規範
- Aggregate Root: `Order`, `User`, `Product`
- Value Object: `Money`, `Address`, `EmailAddress`
- Domain Event: `OrderCreated`, `PaymentProcessed`
- Command: `CreateOrderCommand`, `CancelOrderCommand`
- Query: `GetOrderByIdQuery`, `ListUserOrdersQuery`
- Repository: `OrderRepository` (interface), `PostgresOrderRepository` (impl)

## 設計流程
1. **Event Storming** — 辨識 Domain Events
2. **定義 Bounded Contexts** — 劃分模組邊界
3. **設計 Aggregates** — 定義一致性邊界
4. **定義 Repository Interfaces** — 在 Domain 層定義介面
5. **實作 Application Services** — 編排 Use Cases
6. **實作 Infrastructure** — 具體的持久化和外部服務
7. **建立 Presentation** — API Controllers 和 DTOs

## 規則
- Domain 層不允許 import 任何框架套件
- Domain Model 不允許有 ORM decorator
- Infrastructure 層實作 Domain 層定義的介面
- Application 層負責交易邊界（Transaction）
- 跨 Aggregate 的通訊必須透過 Domain Event
```

## Skill 設計最佳實踐

### 1. 明確的觸發描述

```yaml
# ✅ 好的 description — 具體的觸發詞
description: >
  RESTful API 設計專家。當需要設計、審查、重構 API endpoint，
  定義路由規範或 HTTP 狀態碼時使用。

# ❌ 不好的 description — 太模糊
description: 幫助寫程式碼
```

### 2. 限定工具範圍

```yaml
# 安全審計 Skill 只需要讀取能力
tools:
  - Read File
  - Grep Search
  - Semantic Search
  # 不包含 Edit, Write, Terminal
```

### 3. 提供具體範例

在 Skill 中包含實際的程式碼範例，讓 Claude 能準確模仿風格。

### 4. 定義工作流程

明確列出步驟順序，而不是只描述最終結果。

### 5. 包含反模式

告訴 Claude 什麼「不要」做，和告訴它要做什麼一樣重要。

## 組合 Skills + Agents + Plugins + Memory + Hooks

```
CLAUDE.md        → 專案基礎規範、@ 引入詳細規格
Skills           → 特定任務的知識和流程
Agents           → 特定角色的行為模式 + 工具限制
Plugins          → 擴展 Claude Code 能力
Hooks            → 確定性自動化（格式化、測試）
Memory           → 累積的經驗和偏好
MCP Servers      → 外部工具和資料
                    ↓
          = 完全客製化的 AI 開發夥伴
```

---

⬅️ [上一篇：進階工作流程](08-ADVANCED-WORKFLOWS.md) | ➡️ [下一篇：最佳實踐與技巧](10-BEST-PRACTICES.md)
