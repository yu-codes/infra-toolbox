# 04 — 記憶系統

Claude Code 的記憶機制讓 AI 在不同範圍中保留上下文，提升長期協作效率。記憶分為兩個主要來源：**你手動撰寫的 CLAUDE.md**，以及 **Claude 自動累積的 auto memory**。

## 記憶架構總覽

```
┌──────────────────────────────────────────────────────────┐
│  CLAUDE.md（人工撰寫）                                      │
│  你定義規範、上下文、技術棧，Claude 每次啟動時自動載入          │
├──────────────────────────────────────────────────────────┤
│  Auto Memory（Claude 自動累積）                              │
│  Claude 把對話中的重要知識寫入記憶檔，下次 session 自動讀取    │
└──────────────────────────────────────────────────────────┘
```

### CLAUDE.md 的作用範圍

| CLAUDE.md 位置 | 作用範圍 | 說明 |
|------|---------|------|
| `~/.claude/CLAUDE.md` | 全域 | 所有專案共用（個人偏好） |
| `<專案>/CLAUDE.md` | 專案 | 團隊共享，可提交 Git |
| `<專案>/.claude/CLAUDE.md` | 專案 | 同上，替代位置 |
| `<子目錄>/CLAUDE.md` | 子目錄 | 進入子目錄時自動載入 |
| `CLAUDE.local.md` | 本地 | 個人偏好，建議加入 .gitignore |

---

## 一、CLAUDE.md（人工記憶）

CLAUDE.md 是你明確告訴 Claude 的指令文件，是最直接的「記憶」形式。Claude 在每次 session 開始時自動讀取所有作用範圍內的 CLAUDE.md。

### 全域 CLAUDE.md（使用者層）

儲存你的個人偏好，跨所有專案套用：

```markdown
# ~/.claude/CLAUDE.md

## 溝通偏好
- 回覆語言：繁體中文
- 程式碼註解：英文

## 程式碼風格
- 語言：TypeScript（優先）、Python
- 縮排：2 空格
- 套件管理：pnpm
- Commit 格式：Conventional Commits（英文）

## 安全原則
- 不讀取 .env、secrets、keys 檔案
- 不寫入 credentials 到程式碼
```

> **設定方式**：將 `claude-code/global/.claude/CLAUDE.md` 複製到 `~/.claude/CLAUDE.md`，依個人需求修改。

### 專案 CLAUDE.md（專案層）

儲存專案規範，與團隊共享（提交到 Git）：

```markdown
# CLAUDE.md  ← 專案根目錄

FastAPI + PostgreSQL 電商後端。Python 3.12、SQLAlchemy 2.0、Redis 快取。

## 規範
- PEP 8，行寬 120，所有函式加 type hints
- Commit：conventional commits
- 新功能必須附單元測試，覆蓋率 ≥ 80%
- 測試指令：`pytest tests/ -v`
- 不修改 migrations/ 中已存在的檔案

## 目錄結構
src/api/ — routes | src/domain/ — models | src/infrastructure/ — DB/external

@docs/ARCHITECTURE.md   ← 引入架構文件（詳細內容不塞進 CLAUDE.md）
@docs/API_SPEC.md
```

### `@` 引入語法

用 `@` 把詳細文件引入，讓 CLAUDE.md 保持簡潔：

```markdown
# CLAUDE.md
這是一個 FastAPI 專案。詳細規範見下方。

@docs/CODING_STANDARDS.md
@docs/DATABASE_CONVENTIONS.md
@.claude/skills/ddd-developer/SKILL.md
```

> 路徑相對於 CLAUDE.md 所在目錄。Claude 按需載入，不會一次全塞進 context。

### 用 `/init` 自動生成

讓 Claude 掃描專案後自動產生 CLAUDE.md：

```bash
claude
> /init
```

Claude 會分析專案結構、依賴、測試設定，生成第一版 CLAUDE.md。

---

## 二、Auto Memory（自動記憶）

Auto Memory 讓 Claude 把對話中學到的重要知識**自動寫入記憶檔**，下次 session 啟動時自動讀取前 200 行。

### 儲存位置

```
~/.claude/projects/<project_path_hash>/memory/MEMORY.md
```

> 這是 Claude Code 自動管理的路徑。每個專案對應一個獨立的記憶檔。

### 運作方式

你不需要手動操作。Claude 會判斷哪些資訊值得記住：

```
> 我們的 Redis 快取 TTL 統一設為 300 秒
> 生產環境不允許使用 root 帳號連線資料庫
> 這個專案有個已知問題：Docker 在 M1 Mac 需加 platform: linux/amd64
```

Claude 會在適當時機把這些知識寫入 auto memory，下次開啟 session 時自動可用。

### 查看目前記憶

在 Claude Code session 中執行：

```
> /memory
```

Claude 會顯示目前載入的所有記憶內容（來自 CLAUDE.md 和 auto memory）。

### 明確要求記住

你也可以主動告知：

```
> 請記住：我們使用 JWT + Refresh Token 方案（已決定，不再討論其他方案）
> 這次 debug 經驗很有價值，請把解法記下來
> 請更新記憶中關於 Redis 的部分，TTL 現在改為 600 秒
```

---

## 三、記憶 vs. CLAUDE.md 的分工

| 內容類型 | 推薦做法 |
|---------|---------|
| 技術棧、框架說明 | 寫在 `CLAUDE.md`（提交 Git，團隊共享） |
| 程式碼規範、命名規則 | 寫在 `CLAUDE.md` |
| 個人偏好（語言、工具） | 寫在 `~/.claude/CLAUDE.md`（不提交） |
| 累積的架構決策 | 讓 Claude 寫入 auto memory |
| 除錯經驗、已知 workarounds | 讓 Claude 寫入 auto memory |
| 當前任務進度（臨時） | 只在對話中提及，不需永久記憶 |

---

## 四、非互動模式下的記憶

使用 `claude -p`（pipe mode）時，記憶會**照常載入**（CLAUDE.md + auto memory），除非使用 `--bare` flag：

```bash
# 一般 pipe mode（載入 CLAUDE.md + auto memory）
echo "建立新的 UserService" | claude -p

# --bare 模式（跳過所有記憶載入，適合 CI）
claude --bare -p "Review this file" --allowedTools "Read"
```

> **CI/CD 建議**：在 CI 環境使用 `--bare`，避免受到本機 `~/.claude/` 配置影響，確保結果一致。

---

## 五、記憶安全提示

- `CLAUDE.md` 會提交 Git，**不要放敏感資訊**（密碼、API key、內部 IP）
- Auto memory 儲存在本機 `~/.claude/`，不會同步到任何服務
- 使用 `CLAUDE.local.md`（加入 `.gitignore`）來存放個人的、不想共享的指令

---

⬅️ [上一篇：設定檔系統](03-CONFIGURATION.md) | ➡️ [下一篇：Prompt 工程](05-PROMPT-ENGINEERING.md)
