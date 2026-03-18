# 04 — 記憶系統

Claude Code 擁有三層記憶架構，讓 AI 能在不同範圍中記住上下文，提升長期協作效率。

## 三層記憶架構

```
┌──────────────────────────────────────────┐
│  User Memory（使用者記憶）                  │  ~/.claude/memories/
│  跨所有專案、跨所有對話永久保存              │
├──────────────────────────────────────────┤
│  Repo Memory（專案倉庫記憶）                │  .claude/memories/
│  專案範圍，團隊可共享                       │
├──────────────────────────────────────────┤
│  Session Memory（對話記憶）                  │  對話內暫存
│  僅限當前對話，結束後清除                    │
└──────────────────────────────────────────┘
```

| 層級 | 路徑 | 生命週期 | 用途 |
|------|------|---------|------|
| User Memory | `~/.claude/memories/` | 永久 | 個人偏好、習慣模式、通用知識 |
| Repo Memory | `.claude/memories/` | 隨 Git 提交 | 專案架構、技術決策、團隊規範 |
| Session Memory | 對話內 | 對話結束清除 | 任務上下文、臨時筆記、進度追蹤 |

## User Memory（使用者記憶）

### 適合存放的內容

- 個人程式碼風格偏好
- 常用技術棧
- 慣用的命名規範
- 除錯策略和經驗教訓
- 常用指令和快捷方式

### 操作方式

```
> 請記住：我偏好使用 TypeScript 而不是 JavaScript
> 請記住：我的 commit message 格式是 conventional commits
> 請記住：我習慣用 pnpm 而不是 npm
```

Claude 會自動將這些偏好寫入 User Memory。

### 手動管理

```
> /memory

# Claude 會顯示目前的記憶內容，你可以要求修改：
> 刪除關於 JavaScript 的記憶
> 更新我的技術棧偏好
```

### User Memory 檔案範例

```markdown
# ~/.claude/memories/preferences.md

## 程式碼風格
- 偏好 TypeScript，型別定義要完整
- 使用 2 空格縮排
- 字串使用單引號
- 行寬上限 100 字元
- 函式優先使用 arrow function

## 工具偏好
- 套件管理: pnpm
- 測試框架: vitest
- Linter: biome (不用 eslint)
- 格式化: biome format

## 溝通偏好
- 用繁體中文回答
- 程式碼註解用英文
- commit message 用英文 conventional commits
```

## Repo Memory（專案倉庫記憶）

### 適合存放的內容

- 專案架構決策和原因
- 團隊約定的開發規範
- 已知的技術限制和 workarounds
- 常見問題的解決方案
- 重要的部署注意事項

### 操作方式

```
> 為這個專案記住：我們使用 DDD 架構，domain 層不允許直接依賴 infrastructure
> 為這個專案記住：Redis 快取 TTL 統一設為 300 秒
> 為這個專案記住：API 版本控制使用 URL 前綴 /api/v1/
```

### Repo Memory 檔案範例

```markdown
# .claude/memories/architecture.md

## 架構決策
- 使用 Clean Architecture / DDD 分層
- Domain 層不依賴外部框架
- Repository pattern 封裝資料存取
- Application 層負責用例編排

## 技術限制
- PostgreSQL 不支援 JSONB 的部分更新（需整欄覆寫）
- Redis cluster 模式不支援 multi-key 操作
- 前端 API client 是自動生成的，不要手動修改 src/api/generated/

## 已知 Workarounds
- Docker 在 M1 Mac 上需要 platform: linux/amd64
- CI 中的 e2e 測試有時會因網路問題失敗，重試即可
```

## Session Memory（對話記憶）

### 適合存放的內容

- 當前任務的進度和狀態
- 臨時的除錯記錄
- 探索中的方案比較
- 尚未完成的 TODO 清單

### 操作方式

Session Memory 在對話中自動管理，你也可以明確要求：

```
> 記住我們目前在處理用戶認證模組的重構
> 記住我們決定使用 JWT + Refresh Token 方案
> 目前的進度：已完成 token 產生，接下來要做 token 驗證
```

## 記憶管理技巧

### 1. 讓 Claude 自動學習

```
> 剛才那個解法很有效，請記住這個模式以後可以複用
> 這次 debug 經驗很有價值，記住當遇到 CORS 問題時的排查步驟
```

### 2. 結構化記憶

```
> 為這個專案建立記憶，分類為：
> - 架構規範
> - 資料庫約定
> - API 設計規則
> - 部署注意事項
```

### 3. 審查和清理

```
> 顯示所有記憶內容
> 這條記憶已經過時了，請更新：[具體內容]
> 清除所有 Session Memory，我要開始新任務
```

### 4. 記憶與 CLAUDE.md 的配合

```
CLAUDE.md  → 團隊共享的規範和上下文（提交到 Git）
Repo Memory → 逐步累積的專案知識（也可提交 Git）
User Memory → 個人偏好（不提交）
```

建議的分工：

| 內容類型 | 放在 CLAUDE.md | 放在 Memory |
|---------|--------------|-------------|
| 技術棧說明 | ✓ | |
| 程式碼規範 | ✓ | |
| 架構決策記錄 | | ✓ Repo Memory |
| Debug 經驗教訓 | | ✓ Repo / User Memory |
| 個人編碼習慣 | | ✓ User Memory |
| 臨時任務筆記 | | ✓ Session Memory |

## 記憶如何影響 Claude 的行為

When Claude starts a session, it loads memory in this order:

```
1. 讀取 User Memory     → 了解你的個人偏好
2. 讀取 CLAUDE.md       → 了解專案規範
3. 讀取 Repo Memory     → 了解專案歷史知識
4. 建立 Session Memory  → 準備記錄本次對話
```

**實際效果範例：**

沒有記憶：
```
> 幫我建立一個新的 service
# Claude 可能用 JavaScript、class-based、npm...
```

有記憶：
```
> 幫我建立一個新的 service
# Claude 直接用 TypeScript、function-based、pnpm
# 遵循專案的 DDD 分層、加上正確的 type hints
# commit message 用 conventional commits 格式
```

## 進階：程式化存取記憶

在非互動模式（pipe mode）中也可以利用記憶：

```bash
# 記憶會在 pipe mode 中自動載入
echo "建立新的 UserService" | claude -p

# 結合 Git Hook 自動更新記憶
# .git/hooks/post-commit:
claude -p "根據最近的 commit 更新 Repo Memory 中的變更記錄"
```

---

⬅️ [上一篇：設定檔系統](03-CONFIGURATION.md) | ➡️ [下一篇：Prompt 工程](05-PROMPT-ENGINEERING.md)
