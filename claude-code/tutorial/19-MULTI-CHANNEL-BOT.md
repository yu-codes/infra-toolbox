# 19 — 多頻道多 Repo 獨立 Claude 架構

在單一 Slack 或 Discord Server 中，透過不同頻道分別管理不同的 Repo，每個頻道擁有獨立的 Claude 對話、memory 與工具環境。

## 目標架構

```
Slack/Discord Channel A     Slack/Discord Channel B
         ↓                           ↓
      Bot A                       Bot B
    (或同一個 Bot，依 channel 路由)
         ↓                           ↓
  Container A                  Container B
  (claude-runner)              (claude-runner)
         ↓                           ↓
    Repo A                       Repo B
  (/workspace)                 (/workspace)
         ↓                           ↓
  Claude Session A             Claude Session B
  (獨立 ~/.claude/)             (獨立 ~/.claude/)
```

**隔離機制**：每個 Container 擁有獨立的 Docker Volume 作為 `~/.claude/`，確保：
- Session history 各自獨立
- Auto memory 各自獨立
- CLAUDE.md、settings 各自獨立
- 不同頻道的操作不互相影響

---

## 前置需求

| 項目 | 需求 |
|------|------|
| Docker + Docker Compose | v2.20+ |
| Anthropic API Key | Console 帳號或 Claude Max/Team 訂閱 |
| Discord / Slack | Bot 建立權限 |
| Git Repo | 每個頻道對應一個 Repo（本機路徑） |

> ⚠️ 此架構使用 `claude -p`（非互動模式），需要 **Anthropic API Key**，不能使用 claude.ai OAuth 帳號登入方式。

---

## 專案結構

```
multi-bot/
├── docker-compose.yml
├── .env
├── bot/                        # Discord/Slack Bot 服務
│   ├── Dockerfile
│   ├── requirements.txt
│   └── bot.py
├── claude-runner/              # Claude Code 執行服務
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py
└── repos/                      # 本機 Repo（或掛載已有 Repo）
    ├── repo-a/                 # 對應 Channel A
    └── repo-b/                 # 對應 Channel B
```

---

## Step 1：建立 Discord Bot

為每個頻道建立一個 Bot（或使用同一個 Bot 依 channel ID 路由）：

### 建立 Bot（以 Discord 為例）

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → 輸入名稱（例如 `RepoA-Claude`）
3. 進入 **Bot** 頁面：
   - 點 **Reset Token** → 複製 Token
   - 啟用 **Message Content Intent**（必須）
4. 進入 **OAuth2 → URL Generator**：
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Read Message History`
   - 複製邀請網址，邀請 Bot 進入你的 Server

重複以上步驟建立 Bot B（若需要完全獨立的 Bot），或使用同一個 Bot 靠 Channel ID 路由。

---

## Step 2：準備 Repo

```bash
mkdir -p multi-bot/repos/repo-a multi-bot/repos/repo-b

# 若是已有 Repo，掛載路徑（在 docker-compose.yml 中調整 volumes）
# git clone https://github.com/yourorg/repo-a multi-bot/repos/repo-a
# git clone https://github.com/yourorg/repo-b multi-bot/repos/repo-b
```

---

## Step 3：Claude Runner 服務

Claude Runner 是一個簡單的 HTTP 服務，接收訊息並呼叫 `claude -p --continue`，回傳結果。

### `claude-runner/server.py`

```python
import subprocess
import json
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
WORKSPACE = os.environ.get("WORKSPACE", "/workspace")
ALLOWED_TOOLS = os.environ.get("ALLOWED_TOOLS", "Read,Edit,Write,Bash")


class RunRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok", "workspace": WORKSPACE}


@app.post("/run")
def run_claude(req: RunRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # 使用 --bare --continue 保持 session 連續性
    # --bare：跳過 hooks/plugins 自動載入（CI 友善）
    # --continue：延續上次在此目錄的 session
    cmd = [
        "claude",
        "--bare",
        "-p",
        "--continue",
        "--allowedTools", ALLOWED_TOOLS,
        "--output-format", "json",
        req.message,
    ]

    logger.info("Running: %s in %s", " ".join(cmd[:5]) + " ...", WORKSPACE)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=WORKSPACE,
            timeout=300,  # 5 分鐘 timeout
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Claude timed out (>5 min)")

    if result.returncode != 0:
        logger.error("Claude stderr: %s", result.stderr)
        # 若是第一次執行（沒有 session 可 continue），自動重試不帶 --continue
        if "No conversation found" in result.stderr:
            cmd_fresh = [c for c in cmd if c != "--continue"]
            result = subprocess.run(
                cmd_fresh, capture_output=True, text=True, cwd=WORKSPACE, timeout=300
            )

    try:
        output = json.loads(result.stdout)
        return {
            "result": output.get("result", "（無輸出）"),
            "session_id": output.get("session_id"),
            "cost_usd": output.get("cost_usd"),
        }
    except json.JSONDecodeError:
        # 非 JSON 輸出時直接回傳原始文字
        return {"result": result.stdout.strip() or result.stderr.strip()}
```

### `claude-runner/requirements.txt`

```
fastapi==0.115.0
uvicorn==0.30.0
pydantic==2.7.0
```

### `claude-runner/Dockerfile`

```dockerfile
FROM python:3.12-slim

# 安裝 Claude Code 原生版本
RUN apt-get update && apt-get install -y curl ca-certificates git && \
    curl -fsSL https://claude.ai/install.sh | bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# 預設工作目錄（會被 docker-compose volumes 掛載實際 Repo）
RUN mkdir -p /workspace

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Step 4：Bot 服務

Bot 服務監聽 Discord（或 Slack），依 Channel ID 路由到對應的 Claude Runner。

### Discord Bot（`bot/bot.py`）

```python
import os
import httpx
import asyncio
import logging
import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 從環境變數讀取 channel → runner 對應表
# 格式：CHANNEL_MAP=123456789:http://claude-runner-a:8080,987654321:http://claude-runner-b:8080
CHANNEL_MAP: dict[int, str] = {}
for entry in os.environ.get("CHANNEL_MAP", "").split(","):
    if ":" in entry:
        parts = entry.strip().split(":", 1)
        try:
            CHANNEL_MAP[int(parts[0])] = parts[1]
        except ValueError:
            pass

logger.info("Channel map: %s", CHANNEL_MAP)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info("Bot ready: %s (ID: %s)", bot.user, bot.user.id)


@bot.event
async def on_message(message: discord.Message):
    # 忽略自己的訊息
    if message.author == bot.user:
        return

    channel_id = message.channel.id
    runner_url = CHANNEL_MAP.get(channel_id)
    if not runner_url:
        return  # 此頻道未配置，忽略

    content = message.content.strip()
    if not content:
        return

    logger.info("Channel %d → %s: %s", channel_id, runner_url, content[:80])

    # 顯示「正在處理」狀態
    async with message.channel.typing():
        try:
            async with httpx.AsyncClient(timeout=310) as client:
                resp = await client.post(
                    f"{runner_url}/run",
                    json={"message": content},
                )
                resp.raise_for_status()
                data = resp.json()
                result = data.get("result", "（無回應）")
        except httpx.TimeoutException:
            result = "⏱️ 處理超時（>5 分鐘），請嘗試更簡短的任務。"
        except Exception as e:
            logger.error("Runner error: %s", e)
            result = f"❌ 執行錯誤：{e}"

    # Discord 訊息上限 2000 字元，超過則分段傳送
    for i in range(0, len(result), 1900):
        await message.channel.send(result[i : i + 1900])

    await bot.process_commands(message)


if __name__ == "__main__":
    token = os.environ["DISCORD_TOKEN"]
    bot.run(token)
```

### `bot/requirements.txt`

```
discord.py==2.4.0
httpx==0.27.0
```

### `bot/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
CMD ["python", "bot.py"]
```

---

## Step 5：Docker Compose

### `docker-compose.yml`

```yaml
services:
  # ── Bot 服務（監聽 Discord，路由到對應 Runner）──────────────────
  discord-bot:
    build: ./bot
    restart: unless-stopped
    env_file: .env
    environment:
      # CHANNEL_MAP 格式：<channel_id>:<runner_url>,<channel_id>:<runner_url>
      - CHANNEL_MAP=${CHANNEL_A_ID}:http://claude-runner-a:8080,${CHANNEL_B_ID}:http://claude-runner-b:8080
    depends_on:
      - claude-runner-a
      - claude-runner-b
    networks:
      - bot-net

  # ── Claude Runner A（Repo A 專用）──────────────────────────────
  claude-runner-a:
    build: ./claude-runner
    restart: unless-stopped
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - WORKSPACE=/workspace
      - ALLOWED_TOOLS=Read,Edit,Write,Bash(git *),Bash(npm *),Bash(python *)
    volumes:
      # Repo A 原始碼
      - ${REPO_A_PATH}:/workspace
      # 獨立的 Claude home（session + memory 隔離關鍵）
      - claude-home-a:/root/.claude
    networks:
      - bot-net

  # ── Claude Runner B（Repo B 專用）──────────────────────────────
  claude-runner-b:
    build: ./claude-runner
    restart: unless-stopped
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - WORKSPACE=/workspace
      - ALLOWED_TOOLS=Read,Edit,Write,Bash(git *),Bash(npm *),Bash(python *)
    volumes:
      # Repo B 原始碼
      - ${REPO_B_PATH}:/workspace
      # 獨立的 Claude home（session + memory 隔離關鍵）
      - claude-home-b:/root/.claude
    networks:
      - bot-net

# Named volumes 提供持久化的獨立 Claude home
volumes:
  claude-home-a:
  claude-home-b:

networks:
  bot-net:
    driver: bridge
```

### `.env`

```env
# Anthropic API Key（必填）
ANTHROPIC_API_KEY=sk-ant-api03-...

# Discord Bot Token
DISCORD_TOKEN=your_discord_bot_token_here

# Discord Channel IDs（右鍵點擊頻道 → Copy Channel ID）
CHANNEL_A_ID=123456789012345678
CHANNEL_B_ID=987654321098765432

# Repo 路徑（本機絕對路徑）
REPO_A_PATH=/path/to/repo-a
REPO_B_PATH=/path/to/repo-b
```

---

## Step 6：啟動

```bash
cd multi-bot/

# 第一次啟動，建立 image
docker compose build

# 啟動所有服務
docker compose up -d

# 確認狀態
docker compose ps
docker compose logs -f discord-bot

# 測試 Claude Runner 是否正常
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"message": "列出目前目錄的檔案"}'
```

---

## Step 7：Slack 版本

若使用 Slack，替換 Bot 服務即可，Runner 服務完全不變。

### Slack Bot 設定

1. 前往 [Slack API Apps](https://api.slack.com/apps) → **Create New App** → From scratch
2. **OAuth & Permissions** → Bot Token Scopes：
   - `channels:history`、`chat:write`、`im:history`
3. **Event Subscriptions** → Enable → Request URL（需要公開 URL 或 ngrok）：
   - Subscribe to bot events：`message.channels`、`message.im`
4. **Socket Mode** → Enable（不需公開 URL，推薦開發用）

### Slack Bot（`bot/slack_bot.py`）

```python
import os
import httpx
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CHANNEL_MAP 格式同 Discord
CHANNEL_MAP: dict[str, str] = {}
for entry in os.environ.get("CHANNEL_MAP", "").split(","):
    if ":" in entry:
        parts = entry.strip().split(":", 1)
        CHANNEL_MAP[parts[0]] = parts[1]

app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.event("message")
def handle_message(event, say):
    channel_id = event.get("channel", "")
    runner_url = CHANNEL_MAP.get(channel_id)
    if not runner_url or event.get("bot_id"):
        return  # 忽略未配置頻道或 Bot 自己的訊息

    text = event.get("text", "").strip()
    if not text:
        return

    try:
        with httpx.Client(timeout=310) as client:
            resp = client.post(f"{runner_url}/run", json={"message": text})
            resp.raise_for_status()
            result = resp.json().get("result", "（無回應）")
    except Exception as e:
        result = f"❌ 執行錯誤：{e}"

    # Slack 訊息上限 3000 字元
    say(result[:3000])


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
```

Slack 需要額外安裝 `slack-bolt`：
```
# bot/requirements.txt（Slack 版本）
slack-bolt==1.20.0
httpx==0.27.0
```

---

## Session 與 Memory 隔離原理

隔離的核心在於 Docker Volume：

```
claude-home-a → /root/.claude/（Container A 內）
│
├── projects/
│   └── <workspace-hash>/
│       └── memory/
│           ├── MEMORY.md    ← Channel A 的 auto memory
│           └── ...
├── sessions/
│   └── <session-id>.json   ← Channel A 的對話歷史
└── settings.json           ← Channel A 的設定（可個別客製化）

claude-home-b → /root/.claude/（Container B 內）
└── ...（完全獨立）
```

- **每次對話**：`--continue` 自動延續此目錄最近的 session
- **Memory**：Claude 自動在 `~/.claude/projects/*/memory/` 累積知識，不跨容器共享
- **CLAUDE.md**：從 `/workspace`（Repo）讀取，每個 Repo 可有自己的 CLAUDE.md

---

## 新增更多頻道

擴展至第三個頻道只需：

1. 在 `docker-compose.yml` 新增 `claude-runner-c` 服務和 `claude-home-c` volume
2. 在 `.env` 新增 `CHANNEL_C_ID` 和 `REPO_C_PATH`
3. 更新 `CHANNEL_MAP` 環境變數加入新的 mapping
4. `docker compose up -d claude-runner-c && docker compose restart discord-bot`

---

## 安全考量

| 風險 | 對策 |
|------|------|
| 任意使用者控制 Claude | 僅在私有頻道使用 Bot，或在 Bot 程式中加入白名單驗證 `message.author.id` |
| API Key 外洩 | `.env` 加入 `.gitignore`，不提交 git |
| Claude 存取機密檔案 | 在 `ALLOWED_TOOLS` 中限制 Bash 命令；CLAUDE.md 加入讀取限制 |
| Repo 被誤改 | 測試階段可將 volumes 設為 `:ro`（read-only）；生產環境搭配 git 分支保護 |
| 無限耗費 API 費用 | Claude runner 已設 5 分鐘 timeout；可在 `.env` 加入 `CLAUDE_MAX_BUDGET_USD` |

---

## 常用指令

```bash
# 查看特定 Runner 的 Claude 對話日誌
docker compose logs claude-runner-a

# 進入 Runner Container 手動測試
docker exec -it multi-bot-claude-runner-a-1 bash
claude -p "列出目前目錄" --output-format json

# 清除某個頻道的所有 session（重新開始）
docker volume rm multi-bot_claude-home-a
docker compose up -d claude-runner-a

# 查看 Channel A 的 auto memory
docker exec multi-bot-claude-runner-a-1 \
  cat /root/.claude/projects/$(ls /root/.claude/projects/)/memory/MEMORY.md

# 更新到最新 Claude Code 版本
docker compose build --no-cache claude-runner-a claude-runner-b
docker compose up -d
```

---

## 延伸閱讀

- [12-DISCORD-REMOTE.md](./12-DISCORD-REMOTE.md) — 單機互動式 Channels 設定
- [17-HARNESS-AGENT.md](./17-HARNESS-AGENT.md) — `claude -p` 非互動模式詳解
- [官方 Channels 文件](https://code.claude.com/docs/en/channels) — 若希望使用原生 Channels Plugin 方案
- [官方 Agent SDK 文件](https://code.claude.com/docs/en/agent-sdk/overview) — Python/TypeScript SDK 整合
