# 自訂 Workflow 範例

## 範例一：全碼庫 Auth 稽核

在 Claude Code 互動模式中輸入：

```
Run a workflow to audit every API endpoint under src/routes/ for missing auth checks
```

Claude 會自動：
1. 產生一個多階段 JS 腳本
2. Phase 1：掃描所有 route 檔案
3. Phase 2：每個 route 啟動一個 agent 檢查 auth middleware
4. Phase 3：彙整結果報告

## 範例二：大規模遷移

```
Run a workflow to migrate all class components in src/ to functional components with hooks
```

## 範例三：交叉驗證研究

```
/deep-research What are the security implications of using JWT without refresh tokens?
```

## 儲存為可重用命令

當 workflow 完成後：
1. `/workflows` → 選擇該 run → 按 `s`
2. 命名為 `auth-audit`
3. 之後直接用 `/auth-audit` 執行

## 在 CI 中使用

```bash
claude -p "Run a workflow to check all API routes for missing error handling" \
  --dangerously-skip-permissions \
  --max-budget-usd 10.00
```
