# Harness 模式：程式化運行 Claude Code Agent

Harness（Agent SDK）讓你以程式化方式運行 Claude Code，適用於 CI/CD pipeline、自動化腳本、批次任務、以及自訂 agent 應用。

---

## 概覽

| 方式 | 適用場景 | 語言 |
|------|---------|------|
| `claude -p` | Shell 腳本、CI/CD、快速自動化 | Bash |
| Agent SDK (Python) | 自訂 agent 應用、複雜邏輯 | Python |
| Agent SDK (TypeScript) | 自訂 agent 應用、Web 服務 | TypeScript |
| GitHub Actions | PR 自動化、Code Review | YAML |

---

## 方式一：CLI 非互動模式 (`claude -p`)

### 基本用法

```bash
# 單次查詢
claude -p "Explain the auth module"

# 帶工具權限
claude -p "Find and fix the bug in auth.py" --allowedTools "Read,Edit,Bash"

# 完全自動化（跳過所有權限提示）
claude -p "Run tests and fix failures" --dangerously-skip-permissions

# 帶預算上限
claude -p "Refactor the entire src/ directory" \
  --dangerously-skip-permissions \
  --max-budget-usd 5.00 \
  --max-turns 50
```

### Bare 模式（推薦用於 CI）

跳過所有自動載入（hooks, plugins, MCP, CLAUDE.md），只用你明確傳入的設定：

```bash
claude --bare -p "Summarize this file" \
  --allowedTools "Read" \
  --model sonnet
```

### 結構化輸出

```bash
# JSON 輸出（含 session ID、cost 等 metadata）
claude -p "List all API endpoints" --output-format json

# 搭配 JSON Schema 驗證
claude -p "Extract function names from auth.py" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}},"required":["functions"]}'

# 串流輸出
claude -p "Explain recursion" --output-format stream-json --verbose
```

### Pipe 資料

```bash
# 將 build log 餵給 Claude 分析
cat build-error.txt | claude -p "Explain the root cause"

# 將 PR diff 餵給 Claude 做 security review
gh pr diff 123 | claude -p \
  --append-system-prompt "You are a security engineer. Review for vulnerabilities." \
  --output-format json
```

### 延續對話

```bash
# 第一次請求
claude -p "Review this codebase for performance issues"

# 延續上次對話
claude -p "Now focus on database queries" --continue

# 取得 session ID 以便精確延續
session_id=$(claude -p "Start review" --output-format json | jq -r '.session_id')
claude -p "Continue" --resume "$session_id"
```

---

## 方式二：Agent SDK (Python)

### 安裝

```bash
pip install claude-agent-sdk
```

### 基本使用

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Bash"],
            model="sonnet",
            max_turns=20,
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)

asyncio.run(main())
```

### 進階：自訂 Agent 搭配工具權限

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def code_review_agent(repo_path: str, pr_diff: str):
    """自動化 Code Review Agent"""
    async for message in query(
        prompt=f"Review this PR diff for bugs and security issues:\n\n{pr_diff}",
        options=ClaudeAgentOptions(
            working_directory=repo_path,
            allowed_tools=["Read", "Glob", "Grep"],
            model="sonnet",
            max_turns=10,
            system_prompt="You are a senior code reviewer. Focus on bugs, security, and performance.",
        ),
    ):
        if hasattr(message, "result"):
            return message.result
    return ""

async def fix_and_test_agent(repo_path: str, issue: str):
    """自動修復並測試 Agent"""
    async for message in query(
        prompt=f"Fix this issue and run tests to verify: {issue}",
        options=ClaudeAgentOptions(
            working_directory=repo_path,
            allowed_tools=["Read", "Edit", "Bash", "Write", "Glob", "Grep"],
            model="sonnet",
            max_turns=30,
            permission_mode="bypassPermissions",
        ),
    ):
        if hasattr(message, "result"):
            return message.result
    return ""
```

---

## 方式三：Agent SDK (TypeScript)

### 安裝

```bash
npm install @anthropic-ai/claude-agent-sdk
```

### 基本使用

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

async function main() {
  for await (const message of query({
    prompt: "Find all TODO comments and create a summary",
    options: {
      allowedTools: ["Read", "Glob", "Grep"],
      model: "sonnet",
      maxTurns: 10,
    },
  })) {
    if (message.result) {
      console.log(message.result);
    }
  }
}

main();
```

---

## 方式四：GitHub Actions

### 基本設定

```yaml
# .github/workflows/claude.yml
name: Claude Code
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]

jobs:
  claude:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          # Responds to @claude mentions in comments
```

### 自動化 PR Review

```yaml
name: Auto Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Review this PR for bugs, security issues, and code quality"
          claude_args: "--max-turns 10 --model sonnet"
```

### 排程任務

```yaml
name: Daily Report
on:
  schedule:
    - cron: "0 9 * * *"

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Generate a summary of yesterday's commits and open issues"
          claude_args: "--model sonnet --max-turns 5"
```

---

## 方式五：Background Sessions

在本機長時間運行 agent：

```bash
# 啟動背景 session
claude --bg "Investigate the flaky test in auth_test.py"

# 查看所有背景 session
claude agents --json

# 附加到背景 session
claude attach <session-id>

# 查看 session 輸出
claude logs <session-id>

# 停止 session
claude stop <session-id>
```

---

## CI/CD Pipeline 範例

### GitLab CI

```yaml
# .gitlab-ci.yml
claude-review:
  image: node:20
  stage: review
  script:
    - npm install -g @anthropic-ai/claude-code
    - |
      claude --bare -p "Review the changes in this MR for issues" \
        --allowedTools "Read,Glob,Grep" \
        --output-format json \
        --max-turns 10 > review.json
    - cat review.json | jq -r '.result'
  only:
    - merge_requests
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

### Shell Script Harness

```bash
#!/bin/bash
# harness.sh - 通用 Agent 運行腳本

set -euo pipefail

REPO_PATH="${1:-.}"
TASK="${2:-Review the codebase}"
MODEL="${3:-sonnet}"
MAX_TURNS="${4:-20}"
BUDGET="${5:-2.00}"

cd "$REPO_PATH"

result=$(claude --bare -p "$TASK" \
  --dangerously-skip-permissions \
  --model "$MODEL" \
  --max-turns "$MAX_TURNS" \
  --max-budget-usd "$BUDGET" \
  --output-format json 2>/dev/null)

echo "$result" | jq -r '.result'
echo "---"
echo "Cost: $(echo "$result" | jq -r '.total_cost_usd') USD"
echo "Session: $(echo "$result" | jq -r '.session_id')"
```

---

## 配置檔參考

見 `configs/harness/` 目錄中的完整配置範本：
- `harness.sh` — Shell harness 腳本
- `agent-sdk-example.py` — Python Agent SDK 範例
- `agent-sdk-example.ts` — TypeScript Agent SDK 範例
- `github-action.yml` — GitHub Actions workflow

---

## 最佳實踐

| 實踐 | 說明 |
|------|------|
| 使用 `--bare` | CI 環境中避免載入不可預測的本地設定 |
| 設定 `--max-turns` | 防止 agent 無限循環 |
| 設定 `--max-budget-usd` | 控制成本 |
| 結構化輸出 | 用 `--output-format json` 方便程式解析 |
| Allowlist tools | 只授權必要的工具，最小權限原則 |
| 錯誤處理 | 檢查 exit code，非零表示失敗 |
| Session 持續 | 用 `--resume` 延續長任務 |
