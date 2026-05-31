# Dynamic Workflows：大規模子代理編排

Dynamic Workflows 是 Claude Code v2.1.154+ 推出的功能，讓你透過 JavaScript 腳本編排大量子代理（subagents），適合全碼庫稽核、大規模遷移、交叉驗證研究等任務。

---

## 核心概念

| 概念 | 說明 |
|------|------|
| Workflow | 一個 JS 腳本，由 runtime 執行，編排多個 subagent |
| Phase | 工作流程中的一個階段，包含多個 agent |
| Subagent | 被 workflow 啟動的獨立 Claude 工作者 |
| Runtime | 執行 workflow 的隔離環境，結果存在腳本變數中 |

### 與 Subagents / Skills 的差異

| | Subagents | Skills | Workflows |
|-|-----------|--------|-----------|
| 計劃由誰持有 | Claude（逐回合決策） | Claude（按 prompt 執行） | 腳本 |
| 中間結果存放 | Claude context | Claude context | 腳本變數 |
| 可重複性 | 定義可重複 | 指令可重複 | 整個編排流程可重複 |
| 規模 | 每回合幾個 | 同上 | 每次運行數十至數百個 agent |
| 中斷恢復 | 重啟回合 | 重啟回合 | 同一 session 內可恢復 |

---

## 快速開始

### 使用內建 Workflow：`/deep-research`

```
/deep-research What changed in the Node.js permission model between v20 and v22?
```

這會：
1. 扇出多個網路搜尋，從多個角度調查
2. 擷取與交叉驗證來源
3. 對每個宣告投票
4. 回傳附引用的報告（未通過交叉驗證的宣告已過濾）

### 在 Prompt 中觸發自訂 Workflow

在 prompt 中包含 `workflow` 這個字，Claude 會自動編寫一個 workflow 腳本：

```
Run a workflow to audit every API endpoint under src/routes/ for missing auth checks
```

Claude Code 會高亮 `workflow` 一字，並產生編排腳本而非逐回合工作。

### 使用 Ultracode 模式

設定最高 effort，讓 Claude 自動決定何時使用 workflow：

```
/effort ultracode
```

Ultracode 下，每個實質性任務都可能觸發多個 workflow：理解程式碼、做出變更、驗證結果。

---

## 管理 Workflow 運行

### 查看進度

```
/workflows
```

顯示正在執行與已完成的 workflow，可選擇一個查看其進度：

| 按鍵 | 動作 |
|------|------|
| ↑ / ↓ | 選擇 phase 或 agent |
| Enter / → | 深入查看 phase / agent 詳情 |
| Esc | 返回上一層 |
| j / k | 滾動 agent 詳情 |
| p | 暫停 / 恢復 |
| x | 停止選定 agent 或整個 workflow |
| r | 重啟選定 agent |
| s | 儲存腳本為命令 |

### 儲存為可重用命令

1. 執行 `/workflows`
2. 選擇要保留的 run
3. 按 `s`
4. 選擇儲存位置：
   - `.claude/workflows/` — 專案層級，隨 repo 分享
   - `~/.claude/workflows/` — 個人層級，全專案可用
5. 之後用 `/<name>` 直接執行

---

## 權限模式

| 模式 | Workflow 啟動提示 |
|------|-----------------|
| Default / Accept Edits | 每次都問（除非選了「不再問」） |
| Auto | 首次啟動時問一次 |
| Bypass / `claude -p` / Agent SDK | 不問，直接開始 |

Workflow 中的 subagent 固定使用 `acceptEdits` 模式，繼承你的工具白名單。File edits 自動批准。

---

## 行為與限制

| 限制 | 說明 |
|------|------|
| 無 mid-run 使用者輸入 | 只有 agent 權限提示可以暫停 |
| Workflow 本身無法直接存取檔案系統 | 由 agent 代為操作 |
| 最多 16 個並行 agent | 受本機 CPU 限制 |
| 每次 run 最多 1,000 agent | 防止失控迴圈 |

---

## 非互動模式使用

在 CI/CD 或 Agent SDK 中使用 workflow：

```bash
# CLI 非互動模式
claude -p "Run a workflow to audit all endpoints for missing auth" \
  --dangerously-skip-permissions \
  --model sonnet

# 因為是 bypass 模式，workflow 直接啟動不會提示
```

---

## 停用 Workflows

```bash
# 方式一：在 /config 中切換 Dynamic workflows
# 方式二：settings.json
echo '{"disableWorkflows": true}' # 加入 ~/.claude/settings.json

# 方式三：環境變數
export CLAUDE_CODE_DISABLE_WORKFLOWS=1
```

組織管理員可在 [Claude Code admin settings](https://claude.ai/admin-settings/claude-code) 或 managed settings 中全域停用。

---

## 成本控制

Workflow 會啟動大量 agent，單次 run 可能使用顯著更多 token。建議：

1. 大型 run 前用 `/model` 確認當前模型
2. 請 Claude 對非關鍵階段使用較小模型
3. 隨時可從 `/workflows` 停止 run，已完成的工作不會遺失
4. 使用 `--max-budget-usd` 設定總預算上限

---

## 配置檔參考

見 `configs/workflows/` 目錄：
- `example-workflow.md` — 自訂 workflow 範例說明
- `settings-workflow.json` — 啟用 / 停用 workflow 的設定範本

---

## 相關資源

- [Sub-agents](https://code.claude.com/docs/en/sub-agents)：workflow 編排的基本工作單元
- [Agent Teams](https://code.claude.com/docs/en/agent-teams)：平行 agent 協作
- [Worktrees](https://code.claude.com/docs/en/worktrees)：隔離 session
- [Costs](https://code.claude.com/docs/en/costs)：多 agent run 的費用計算
