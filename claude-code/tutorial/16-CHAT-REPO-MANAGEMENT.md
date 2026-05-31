# 透過 Slack / Discord 聊天室管理 Repo Agent

以聊天室為單位，每個聊天室綁定一個 Git Repository，實現：
- **環境隔離**：Agent 只能存取該 repo 的檔案，無法修改外部檔案
- **記憶隔離**：每個聊天室有獨立的 CLAUDE.md 記憶與 session 歷史
- **專案管理**：在聊天室中直接下達開發指令、Code Review、部署

---

## 架構概覽

```
┌─────────────────────────────────────────────────┐
│  Slack / Discord 聊天室                          │
│  #project-backend                               │
└──────────────────┬──────────────────────────────┘
                   │ Webhook / Bot message
                   ▼
┌─────────────────────────────────────────────────┐
│  Dispatcher (Node.js / Python)                  │
│  - 根據 channel → repo 映射表                   │
│  - 啟動對應的 Claude Code session               │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Claude Code (isolated per repo)                │
│  --add-dir /repos/project-backend               │
│  --dangerously-skip-permissions                 │
│  --worktree feature-xxx                         │
│  CLAUDE.md: /repos/project-backend/CLAUDE.md    │
└─────────────────────────────────────────────────┘
```

---

## 方式一：Discord Bot + Claude Code Agent SDK

### 前置需求

| 項目 | 說明 |
|------|------|
| Claude Code | v2.1.154+ |
| Node.js | 20+ |
| Git | 已安裝 |
| Discord Bot | 有 `Send Messages`, `Read Message History`, `Message Content Intent` |

### Step 1：建立 Channel-Repo 映射設定

建立 `channel-repo-config.json`：

```json
{
  "channels": {
    "1234567890": {
      "name": "#project-backend",
      "repo": "/repos/project-backend",
      "branch": "main",
      "allowed_users": ["user-id-1", "user-id-2"],
      "claude_args": {
        "model": "sonnet",
        "permission_mode": "bypassPermissions",
        "max_turns": 50,
        "allowed_tools": ["Read", "Edit", "Bash", "Glob", "Grep", "Write"]
      }
    },
    "0987654321": {
      "name": "#project-frontend",
      "repo": "/repos/project-frontend",
      "branch": "main",
      "allowed_users": ["user-id-1"],
      "claude_args": {
        "model": "sonnet",
        "permission_mode": "acceptEdits",
        "max_turns": 30,
        "allowed_tools": ["Read", "Edit", "Bash", "Glob", "Grep", "Write"]
      }
    }
  },
  "defaults": {
    "model": "sonnet",
    "permission_mode": "acceptEdits",
    "max_turns": 20,
    "isolation": true
  }
}
```

### Step 2：Dispatcher 服務

使用 Agent SDK (TypeScript) 建立 dispatcher：

```typescript
// dispatcher.ts
import { Client, GatewayIntentBits } from "discord.js";
import { query } from "@anthropic-ai/claude-agent-sdk";
import { readFileSync } from "fs";

const config = JSON.parse(readFileSync("./channel-repo-config.json", "utf-8"));
const sessions = new Map<string, string>(); // channelId → sessionId

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

client.on("messageCreate", async (message) => {
  if (message.author.bot) return;
  if (!message.mentions.has(client.user!)) return;

  const channelConfig = config.channels[message.channelId];
  if (!channelConfig) {
    await message.reply("⚠️ This channel is not bound to any repository.");
    return;
  }

  // Check user permission
  if (!channelConfig.allowed_users.includes(message.author.id)) {
    await message.reply("🚫 You are not authorized in this channel.");
    return;
  }

  const prompt = message.content.replace(/<@!?\d+>/g, "").trim();
  if (!prompt) return;

  await message.channel.sendTyping();

  try {
    let result = "";
    for await (const msg of query({
      prompt,
      options: {
        workingDirectory: channelConfig.repo,
        allowedTools: channelConfig.claude_args.allowed_tools,
        model: channelConfig.claude_args.model,
        maxTurns: channelConfig.claude_args.max_turns,
        permissionMode: channelConfig.claude_args.permission_mode,
      },
    })) {
      if (msg.result) result = msg.result;
    }

    // Discord message limit is 2000 chars
    const chunks = result.match(/[\s\S]{1,1900}/g) || ["(no output)"];
    for (const chunk of chunks) {
      await message.reply(chunk);
    }
  } catch (err: any) {
    await message.reply(`❌ Error: ${err.message}`);
  }
});

client.login(process.env.DISCORD_BOT_TOKEN);
```

### Step 3：環境隔離機制

確保 Agent 被限制在 repo 範圍內：

```bash
# 使用 worktree 實現 git 層級隔離
claude -p "$PROMPT" \
  --worktree "$CHANNEL_NAME" \
  --dangerously-skip-permissions \
  --allowedTools "Read,Edit,Bash(git *),Bash(npm *),Bash(pytest *),Glob,Grep,Write" \
  --disallowedTools "Bash(rm -rf /*)","Bash(sudo *)" \
  --model sonnet
```

關鍵隔離措施：
1. **`--worktree`**：每個 session 使用獨立 git worktree，互不干擾
2. **`--allowedTools` 白名單**：只允許安全的 Bash 指令（git, npm, pytest 等）
3. **`--disallowedTools` 黑名單**：封鎖危險操作
4. **工作目錄限制**：Agent 的 cwd 設為 repo 路徑，只能存取該目錄下的檔案

### Step 4：記憶管理

每個 repo 有自己的 `CLAUDE.md`，Agent 自動載入：

```
/repos/project-backend/
├── CLAUDE.md              ← Agent 自動讀取的專案記憶
├── .claude/
│   ├── settings.json      ← 專案級設定
│   ├── skills/            ← 專案級技能
│   └── agents/            ← 專案級子代理
└── src/
```

跨 session 的記憶持續存在，因為 CLAUDE.md 存在 repo 內。

---

## 方式二：Slack Bot + Claude Code CLI

### Step 1：建立 Slack App

1. 前往 [Slack API](https://api.slack.com/apps) → Create New App
2. 啟用 **Socket Mode**
3. 設定 Bot Token Scopes：`chat:write`, `app_mentions:read`, `channels:history`
4. 啟用 Event Subscriptions：`app_mention`, `message.channels`

### Step 2：Slack Dispatcher

```python
# slack_dispatcher.py
import os
import json
import subprocess
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token=os.environ["SLACK_BOT_TOKEN"])

with open("channel-repo-config.json") as f:
    config = json.load(f)

@app.event("app_mention")
def handle_mention(event, say):
    channel_id = event["channel"]
    user_id = event["user"]
    text = event["text"].split(">", 1)[-1].strip()

    channel_config = config["channels"].get(channel_id)
    if not channel_config:
        say("⚠️ This channel is not bound to any repository.")
        return

    if user_id not in channel_config["allowed_users"]:
        say("🚫 You are not authorized.")
        return

    repo_path = channel_config["repo"]
    args = channel_config["claude_args"]

    # Run Claude Code in isolated mode
    result = subprocess.run(
        [
            "claude", "-p", text,
            "--dangerously-skip-permissions",
            "--model", args.get("model", "sonnet"),
            "--max-turns", str(args.get("max_turns", 20)),
            "--allowedTools", ",".join(args.get("allowed_tools", ["Read", "Glob"])),
            "--output-format", "text",
        ],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=300,
    )

    output = result.stdout or result.stderr or "(no output)"
    # Slack message limit ~4000 chars
    for i in range(0, len(output), 3900):
        say(f"```{output[i:i+3900]}```")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
```

---

## 方式三：使用 Claude Code Channels（原生方式）

如果你已經有 Discord Bot 設定（參見 [12-DISCORD-REMOTE.md](./12-DISCORD-REMOTE.md)），可以直接用 Channels 功能：

```bash
# 在對應 repo 目錄中啟動 Claude Code
cd /repos/project-backend
claude --channels plugin:discord@claude-plugins-official \
  --dangerously-skip-permissions \
  --name "project-backend"
```

每個 repo 啟動一個 Claude Code instance，自然實現隔離。

---

## Docker 部署（推薦生產環境）

使用 Docker 可以提供作業系統層級的完全隔離：

```yaml
# docker-compose.yml
services:
  agent-backend:
    build: ./agent-runner
    volumes:
      - /repos/project-backend:/workspace:rw
      - backend-claude:/root/.claude
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REPO_NAME=project-backend
      - CHANNEL_ID=1234567890
    working_dir: /workspace
    network_mode: bridge
    deploy:
      resources:
        limits:
          memory: 2G

  agent-frontend:
    build: ./agent-runner
    volumes:
      - /repos/project-frontend:/workspace:rw
      - frontend-claude:/root/.claude
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REPO_NAME=project-frontend
      - CHANNEL_ID=0987654321
    working_dir: /workspace
    network_mode: bridge

volumes:
  backend-claude:
  frontend-claude:
```

---

## 安全最佳實踐

| 措施 | 說明 |
|------|------|
| Allowlist users | 只有授權使用者可以觸發 Agent |
| Tool 白名單 | 限制可使用的 Bash 指令模式 |
| Worktree 隔離 | 每個 session 使用獨立 git worktree |
| Docker 隔離 | 生產環境建議用容器隔離檔案系統 |
| Max turns | 限制最大回合數避免無限迴圈 |
| Budget cap | 使用 `--max-budget-usd` 限制花費 |
| 唯讀 branch protection | 設定 Git branch protection rules |

---

## 疑難排解

| 問題 | 解決方案 |
|------|---------|
| Agent 修改了 repo 外的檔案 | 確認使用 `--worktree` 或 Docker volume 隔離 |
| Session 記憶消失 | 確認 CLAUDE.md 存在 repo 根目錄 |
| 回應太慢 | 降低 `--max-turns`，使用 `--bare` 加速啟動 |
| 多人同時操作衝突 | 使用 worktree，每人一個 branch |
| Bot 沒有回應 | 檢查 ANTHROPIC_API_KEY 是否正確設定 |
