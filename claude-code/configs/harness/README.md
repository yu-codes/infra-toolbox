# Harness Configs

Claude Code Agent 自動化運行的配置檔與範例腳本。

## 檔案說明

| 檔案 | 說明 |
| ---- | ---- |
| `harness.sh` | 通用 Shell harness 腳本，可在 CI 或本機執行 |
| `agent-sdk-example.py` | Python Agent SDK 範例 |
| `agent-sdk-example.ts` | TypeScript Agent SDK 範例 |
| `github-action.yml` | GitHub Actions workflow 範本 |

## 使用方式

```bash
# Shell harness
chmod +x harness.sh
./harness.sh /path/to/repo "Fix all lint errors" sonnet 30 5.00

# Python SDK
pip install claude-agent-sdk
REPO_PATH=/path/to/repo TASK="Run tests" python agent-sdk-example.py

# TypeScript SDK
npm install @anthropic-ai/claude-agent-sdk
REPO_PATH=/path/to/repo TASK="Run tests" npx tsx agent-sdk-example.ts
```
