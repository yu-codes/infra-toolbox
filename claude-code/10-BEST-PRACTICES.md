# 10 — 最佳實踐與技巧

來自 Anthropic 官方指南與社群的精煉實戰智慧。每一條都能直接提升你的 Claude Code 效率。

---

## 1. 讓 Claude 自我驗證

> **核心原則：提供驗證標準，讓 Claude 檢查自己的產出。這是單一最高槓桿的做法。**

```
❌ 實作 email 驗證函式
✅ 寫一個 validateEmail 函式。測試案例：user@example.com → true，
   invalid → false，user@.com → false。實作後執行測試。
```

```
❌ 改善 dashboard 的外觀
✅ [貼上截圖] 按照這個設計實作。完成後截圖比較，列出差異並修正。
```

| 場景 | 驗證方式 |
|------|---------|
| 邏輯修改 | 測試套件（`npm test`、`pytest`） |
| UI 變更 | 截圖比較（搭配 Chrome 擴充） |
| 建置修復 | 確認 build 成功且錯誤消失 |
| API 開發 | curl 測試 + 狀態碼驗證 |

---

## 2. 探索 → 計劃 → 實作

> **核心原則：分離研究與實作，避免解決錯誤的問題。用 Plan Mode 先探索再動手。**

```
步驟 1（Plan Mode, Ctrl+G）：
> 閱讀 src/auth/ 了解目前的 session 和登入機制

步驟 2（Plan Mode）：
> 我要加入 Google OAuth。哪些檔案需要修改？session 流程是什麼？建立計劃。

步驟 3（Normal Mode, Ctrl+G）：
> 按照計劃實作 OAuth 流程。為 callback handler 寫測試，執行測試套件並修復失敗。

步驟 4：
> 用描述性訊息 commit 並建立 PR
```

**何時跳過計劃：** 修 typo、加 log、重新命名變數 — 一句話能描述 diff 的任務直接做。

---

## 3. 提供具體上下文

> **核心原則：越精確的指令 → 越少的修正來回。引用檔案、指定約束、指向現有模式。**

| 技巧 | 差的做法 | 好的做法 |
|------|---------|---------|
| 限定範圍 | `加測試` | `為 foo.py 寫測試，覆蓋用戶登出的邊界案例，不用 mock` |
| 指向來源 | `為什麼 API 這麼奇怪？` | `查看 ExecutionFactory 的 git history，摘要 API 為什麼變成這樣` |
| 參考模式 | `加一個元件` | `參考 HotDogWidget.php 的模式，實作日曆元件` |
| 描述症狀 | `修登入 bug` | `用戶報告 session timeout 後登入失敗。檢查 src/auth/ 的 token refresh` |

**豐富的輸入方式：**
- `@filename` 引用檔案（Claude 會先讀取）
- 直接貼圖片（複製貼上或拖放）
- 給 URL 作為文件參考
- 管道輸入：`cat error.log | claude`
- 告訴 Claude 自己去取：「用 git log 查看最近的修改」

---

## 4. 配置你的環境

> **核心原則：前期投入設定功夫，長期每次會話都受益。**

### CLAUDE.md — 要精煉

```markdown
# 好的 CLAUDE.md：具體且可操作
- Use ES modules (import/export), not CommonJS
- Run tests: pnpm test -- --grep "test name"
- Typecheck after code changes: pnpm typecheck

# 刪掉這些：Claude 已經知道或能自己推斷的
❌ "Write clean code"           ← 不言自明
❌ 詳細的 API 文件              ← 改為連結
❌ 經常變動的資訊               ← 很快過時
```

**精煉原則：** 對每一行問「移除它會不會讓 Claude 犯錯？」如果不會，就刪。CLAUDE.md 過長會讓 Claude 忽略真正重要的規則。

**用 `@` 語法引入其他文件：**
```markdown
See @README.md for project overview and @package.json for npm commands.
- Git workflow: @docs/git-instructions.md
```

### 權限 — 減少打擾

```
> /permissions              # 設定白名單
> /sandbox                  # 啟用 OS 層級沙盒隔離
```

### CLI 工具 — 善用已有工具

告訴 Claude 使用 `gh`、`aws`、`gcloud`、`sentry-cli` 等 CLI 工具。它們是最節省 context token 的方式。

```
> 用 gh issue list 查看目前的 bug，然後修復最嚴重的那個
> 使用 'foo-cli --help' 學習 foo 工具，然後用它完成 A, B, C
```

### Hooks — 確保必做動作

```
> 幫我寫一個 hook，在每次編輯檔案後自動執行 eslint
> 幫我寫一個 hook，阻止寫入 migrations 資料夾
```

Hooks 在 `.claude/settings.json` 中設定，與 CLAUDE.md 不同的是：Hooks 是確定性的（一定會執行），CLAUDE.md 是建議性的。

### Skills — 領域知識按需載入

```yaml
# .claude/skills/api-conventions/SKILL.md
---
name: api-conventions
description: REST API design conventions for our services
---
- Use kebab-case for URL paths
- Use camelCase for JSON properties
- Always include pagination for list endpoints
```

Skills 只在相關時載入，不會佔用每次對話的上下文。

### Plugins — 一鍵擴展

```
> /plugin      # 瀏覽和安裝社群插件
```

如果使用 typed language，安裝 code intelligence plugin 讓 Claude 有精確的符號導航。

---

## 5. 有效溝通

> **核心原則：像跟資深工程師對話一樣提問。複雜需求讓 Claude 先訪談你。**

### 問程式碼問題

```
> Logging 怎麼運作的？
> 如何新增 API endpoint？
> foo.rs 第 134 行的 async move { ... } 是什麼意思？
> 這段程式碼為什麼呼叫 foo() 而不是 bar()？
```

這是最有效的 onboarding 方式。

### 讓 Claude 訪談你

```
我想建立 [簡短描述]。用 AskUserQuestion 工具詳細訪談我。

問技術實作、UI/UX、邊界案例、疑慮和取捨。
不要問顯而易見的問題，深入我可能沒考慮到的部分。

持續訪談直到全部涵蓋，然後寫完整 spec 到 SPEC.md。
```

Spec 完成後，**開新 session 來實作**。新 session 有乾淨的上下文，專注在實作。

---

## 6. 管理你的 Session

> **核心原則：上下文視窗是最重要的資源。積極管理它。**

### 及早修正方向

- `Escape` — 中斷操作（保留上下文）
- `Escape` × 2 — 開啟 `/rewind` 回溯選單
- `"撤銷剛才的修改"` — 讓 Claude 復原
- 同一問題修正超過兩次？→ `/clear` 後用更好的 prompt 重新開始

### 積極管理上下文

```
/clear                                    # 任務之間重置
/compact                                  # 壓縮保留重點
/compact 保留 API 修改和測試指令的清單     # 帶指引壓縮
/btw 這個函式的回傳型別是什麼？            # 旁問，不佔上下文
```

在 CLAUDE.md 中自訂壓縮行為：
```
When compacting, always preserve the full list of modified files and any test commands.
```

### 用 Subagent 做調查

```
> 使用 subagent 調查我們的認證系統如何處理 token refresh，
  以及是否有現有的 OAuth 工具可以重用
```

Subagent 在獨立的上下文視窗中探索，只回報摘要，不汙染主對話。

### Checkpoint 隨時回溯

每個 Claude 操作都自動建立 checkpoint。`Escape` × 2 或 `/rewind` 可以：
- 只還原對話
- 只還原程式碼
- 兩者都還原
- 從選定的訊息開始摘要

大膽嘗試風險操作 — 不行就回溯。

### 善用 Resume

```bash
claude --continue         # 繼續最近的對話
claude --resume           # 選擇歷史對話

> /rename oauth-migration # 為 session 命名，方便日後查找
```

---

## 7. 自動化與規模化

> **核心原則：掌握一個 Claude 後，用平行 session 和非互動模式倍增產出。**

### 非互動模式

```bash
claude -p "說明這個專案做什麼"                          # 一次性查詢
claude -p "列出所有 API endpoints" --output-format json  # 結構化輸出
claude -p "分析日誌" --output-format stream-json         # 串流 JSON
```

### 平行 Session

| 模式 | 說明 |
|------|------|
| Desktop App | 視覺化管理多個本地 session，各自獨立 worktree |
| Web | 在 Anthropic 雲端的隔離 VM 中運行 |
| Agent Teams | 多個 session 自動協調，含共享任務和團隊管理者 |

**Writer / Reviewer 模式：** Session A 實作 → Session B 審查 → Session A 修復反饋。

### Fan-out 批次處理

```bash
# 列出需要遷移的檔案
claude -p "列出所有需要從 React 遷移到 Vue 的檔案" > files.txt

# 平行處理
for file in $(cat files.txt); do
  claude -p "將 $file 從 React 遷移到 Vue。回傳 OK 或 FAIL。" \
    --allowedTools "Edit,Bash(git commit *)"
done
```

---

## 8. 避免常見失敗模式

| 模式 | 問題 | 修正 |
|------|------|------|
| **大雜燴 session** | 一個 session 混雜不相關任務，上下文雜亂 | `/clear` 切換任務 |
| **反覆修正** | 修了又錯，上下文被失敗嘗試汙染 | 兩次失敗後 `/clear` + 更好的 prompt |
| **過長 CLAUDE.md** | 太長導致 Claude 忽略重要規則 | 精簡到只留必要的；轉為 hook 或 skill |
| **不驗證產出** | 看起來對但有邊界案例 | 永遠提供驗證（測試、腳本、截圖） |
| **無限探索** | 叫 Claude 「調查」但沒限定範圍 | 限定範圍或用 subagent |
| **一次改太多** | 20 個檔案同時改，出錯難 debug | 分步驟，每步 git commit |
| **安全操作不審查** | 盲目 allow rm -rf、git push --force | 看清每個確認，deny 危險指令 |

---

## 9. 費用最佳化

| 策略 | 效果 | 做法 |
|------|------|------|
| 精確 prompt | ⭐⭐⭐ | 一次到位，減少來回 |
| 模型選擇 | ⭐⭐⭐ | 日常用 Sonnet，複雜用 Opus |
| 管理上下文 | ⭐⭐ | 頻繁 `/compact` 和 `/clear` |
| 限定範圍 | ⭐⭐ | 告訴 Claude 只看特定目錄 |
| 非互動模式 | ⭐⭐ | `-p` 模式一次性任務 |
| Subagent | ⭐ | 研究用 subagent，不佔主上下文 |

```
> /model claude-sonnet-4-20250514  # 日常寫碼（快速、便宜）
> /model claude-opus-4-20250514    # 複雜架構設計（深度思考）
```

---

## 10. 培養直覺

這些模式不是一成不變的。有時該讓上下文累積（深入複雜問題時歷史有價值）、有時該跳過計劃（探索性任務）、有時模糊 prompt 反而好（想看 Claude 如何解讀）。

**當 Claude 產出優秀結果時** — 記住你做了什麼：prompt 結構、提供的上下文、使用的模式。

**當 Claude 表現不佳時** — 問為什麼：上下文太嘈雜？prompt 太模糊？任務太大？

隨著經驗累積，你會知道什麼時候精確、什麼時候開放，什麼時候計劃、什麼時候探索。

---

## 速查宣言

```
✅ 提供驗證標準 — 測試、截圖、預期輸出
✅ 先探索再計劃再實作 — Plan Mode (Ctrl+G)
✅ 具體精確 — 引用檔案、指定約束、指向模式
✅ CLAUDE.md 精煉 — 只留 Claude 不知道的事
✅ 管理上下文 — /clear、/compact、subagent
✅ 及早修正 — Escape 中斷、/rewind 回溯
✅ 自動化 — -p 模式、hooks、fan-out
✅ 驗證產出 — 不測試就不發布
```

---

⬅️ [上一篇：自訂 Skills 與 Agents](09-CUSTOM-SKILLS-AGENTS.md) | ➡️ [下一篇：疑難排解](11-TROUBLESHOOTING.md)
