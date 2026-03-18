# Claude Code 開發大師指南

從零開始掌握 Claude Code — Anthropic 推出的 AI 終端編程助手，讓你在命令列中直接與 Claude 協作開發。

## 學習路線圖

按順序閱讀以下文件，完成後你將具備 Claude Code 的完整實戰能力：

| # | 文件 | 主題 | 難度 |
|---|------|------|------|
| 01 | [安裝與環境設定](01-INSTALLATION.md) | 安裝 Claude Code、環境需求、認證設定 | ⭐ |
| 02 | [基礎使用與核心指令](02-BASIC-USAGE.md) | 啟動、對話模式、斜線指令、檔案操作 | ⭐ |
| 03 | [設定檔系統](03-CONFIGURATION.md) | CLAUDE.md、.claude/ 目錄、全域與專案設定 | ⭐⭐ |
| 04 | [記憶系統](04-MEMORY-SYSTEM.md) | User / Session / Repo Memory 三層記憶架構 | ⭐⭐ |
| 05 | [Prompt 工程](05-PROMPT-ENGINEERING.md) | 高效下達指令的策略、範本與反模式 | ⭐⭐ |
| 06 | [Agent 模式與自動化](06-AGENT-MODE.md) | Agentic 開發、自主任務執行、工具使用 | ⭐⭐⭐ |
| 07 | [MCP 伺服器整合](07-MCP-INTEGRATION.md) | Model Context Protocol、外部工具串接 | ⭐⭐⭐ |
| 08 | [進階工作流程](08-ADVANCED-WORKFLOWS.md) | 多檔編輯、除錯、測試、Git 整合 | ⭐⭐⭐ |
| 09 | [自訂 Skills 與 Agents](09-CUSTOM-SKILLS-AGENTS.md) | 建立專屬 Skill、定義 Agent 角色 | ⭐⭐⭐⭐ |
| 10 | [最佳實踐與技巧](10-BEST-PRACTICES.md) | 效率秘訣、常見模式、進階技巧 | ⭐⭐⭐⭐ |
| 11 | [疑難排解](11-TROUBLESHOOTING.md) | 常見問題、錯誤診斷、效能調校 | ⭐⭐ |

## 建議學習方式

```
初學者 → 01 → 02 → 03 → 05 → 11
中級者 → 04 → 06 → 08 → 10
進階者 → 07 → 09 → 全部通讀
```

## 什麼是 Claude Code？

Claude Code 是 Anthropic 推出的 **AI 驅動編程工具**，可在多種環境中使用：

| 環境 | 說明 |
|------|------|
| 終端 CLI | 完整功能的命令列介面（本指南主要內容） |
| VS Code | 在 VS Code 中使用 Claude Code 擴充 |
| JetBrains | IntelliJ、WebStorm 等 IDE 插件 |
| Desktop App | macOS / Windows 桌面應用程式（免終端） |
| Web | 在 Anthropic 雲端執行，瀏覽器即可使用 |

讓開發者直接與 Claude 協作：

- 🔍 **程式碼理解** — 快速讀懂大型程式碼庫
- ✏️ **程式碼編寫** — 自動生成、修改、重構程式碼
- 🐛 **除錯修復** — 智慧診斷並修復 Bug
- 🧪 **測試生成** — 自動撰寫測試案例
- 📁 **檔案操作** — 建立、編輯、搜尋檔案
- 🔧 **Git 操作** — 提交、分支管理、PR 建立
- 🖥️ **終端指令** — 執行 shell 命令、安裝依賴
- 🔌 **工具整合** — MCP 伺服器、Skills、Hooks、Plugins

## 與其他工具的差異

| 特性 | Claude Code (Terminal) | Copilot (VS Code) | Cursor |
|------|----------------------|-------------------|--------|
| 運行環境 | 終端 + VS Code + JetBrains + Desktop + Web | VS Code 擴充 | 獨立 IDE |
| 操作模式 | 對話式 + Agent | 行內補全 + Chat | 行內補全 + Chat |
| 檔案操作 | ✓ 完整 CRUD | △ 有限 | △ 有限 |
| 終端執行 | ✓ 原生 | △ 需切換 | △ 需切換 |
| Git 整合 | ✓ 深度整合 | △ 基礎 | △ 基礎 |
| 自主決策 | ✓ Agent 模式 | ✗ | △ 有限 |
| 可擴展性 | ✓ MCP + Skills + Hooks + Plugins | △ 擴充套件 | △ 插件 |
| 離線使用 | ✗ 需網路 | ✗ 需網路 | ✗ 需網路 |

## 先決知識

- 基本的終端 / 命令列操作能力（或使用 Desktop App 免終端）
- 至少一種程式語言的基礎
- Git 基本觀念（推薦但非必要）

## 官方資源

- 📚 [Claude Code 官方文件](https://code.claude.com/docs)
- 🛠️ [GitHub Repo](https://github.com/anthropics/claude-code)
- 🌐 [Claude Code 官網](https://code.claude.com)
