# 透過 Discord / Channels 進行遠端開發

透過 Claude Code 的 Channels 功能，你可以從 Discord、Telegram 或 iMessage 向本機執行中的 Claude Code session 發送訊息，讓 Claude 在你不在電腦前時也能處理任務。

> **⚠️ Research Preview**：Channels 目前為研究預覽功能（v2.1.80+）。`--channels` 的語法與 plugin 協定未來可能改變。詳見[官方文件](https://code.claude.com/docs/en/channels)。

## 前置條件

| 項目 | 需求 |
|------|------|
| Claude Code 版本 | v2.1.80 或以上 |
| 認證方式 | claude.ai 帳號 或 Console API key |
| 執行環境 | [Bun](https://bun.sh/) 已安裝 |
| 方案 | Pro / Max / Team / Enterprise |

> **注意**：
> - Team / Enterprise 方案需要管理員在 [Admin settings → Claude Code → Channels](https://claude.ai/admin-settings/claude-code) 中啟用。
> - Console API key 帳號預設允許使用 Channels；claude.ai Pro/Max 帳號同樣可用。
> - Amazon Bedrock、Google Vertex AI、Microsoft Foundry 不支援 Channels。

---

## 方式一：Discord Channel（推薦用於遠端開發）

### Step 1：建立 Discord Bot

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 點擊 **New Application**，輸入名稱（例如 `Claude Dev Bot`）
3. 進入 **Bot** 頁面：
   - 點擊 **Reset Token** → 複製你的 Bot Token（稍後需要）
   - 開啟 **Message Content Intent**
4. 進入 **OAuth2 > URL Generator**：
   - Scopes: 勾選 `bot`
   - Bot Permissions: 勾選 `Send Messages`, `Read Message History`
   - 複製產生的 URL，在瀏覽器開啟邀請 Bot 進入你的 Discord Server

### Step 2：安裝 Discord Channel Plugin

在 Claude Code 中執行：

```bash
# 安裝 Discord channel plugin
/plugin install discord@claude-plugins-official
```

> **若顯示 plugin not found**，表示 Marketplace 不存在或需要更新：
> ```bash
> # 新增官方 Marketplace（首次使用）
> /plugin marketplace add anthropics/claude-plugins-official
>
> # 或更新已存在的 Marketplace
> /plugin marketplace update claude-plugins-official
> ```

安裝完成後執行 `/reload-plugins` 啟用 configure 指令。

### Step 3：設定 Bot Token

```bash
/discord:configure <你的_BOT_TOKEN>
```

這會將 token 儲存到 `~/.claude/channels/discord/.env`。

你也可以在啟動 Claude Code 前設定環境變數：
```bash
export DISCORD_BOT_TOKEN="你的_BOT_TOKEN"
```

### Step 4：啟動 Claude Code 並啟用 Channel

```bash
claude --channels plugin:discord@claude-plugins-official
```

### Step 5：配對你的 Discord 帳號

1. 打開 Discord，在任何 Channel 中 `@` 你的 Bot 或私訊 Bot
2. Bot 會回覆一個 **配對碼（pairing code）**
3. 回到 Claude Code 終端，執行：

```bash
/discord:access pair <配對碼>
```

4. 鎖定存取權限（只允許你的帳號）：

```bash
/discord:access policy allowlist
```

### Step 6：開始使用

現在你可以從 Discord 傳送訊息給 Bot：
- Bot 會將訊息轉發到你的 Claude Code session
- Claude 會執行任務並透過 Bot 回覆你
- 你的本機檔案系統、MCP servers、工具都保持可用

---

## 方式二：Remote Control（推薦用於行動裝置）

如果你想從手機或另一台電腦的瀏覽器操控 Claude Code，可以使用 Remote Control：

### Step 1：啟動 Remote Control

```bash
# 專門的 server 模式（推薦）
claude remote-control

# 或帶自訂名稱
claude remote-control --name "My Project"

# 或在既有 session 中啟動
/remote-control
```

### Step 2：連線

啟動後會顯示：
- **Session URL** — 在任何瀏覽器開啟即可操控
- **QR Code** — 按空白鍵顯示，用手機掃描直接在 Claude App 中開啟

你也可以直接：
1. 開啟 [claude.ai/code](https://claude.ai/code)
2. 在 session 列表中找到你的 session（有綠色狀態點）

### Step 3：透過手機操控

安裝 Claude App（[iOS](https://apps.apple.com/us/app/claude-by-anthropic/id6473753684) / [Android](https://play.google.com/store/apps/details?id=com.anthropic.claude)），登入相同帳號：
- 點選 **Code** → 找到你的 session
- 直接打字下達指令
- Claude 在你的本機執行並即時回覆

---

## 方式三：Telegram Channel

### 快速設定

```bash
# 1. 在 Telegram 中找 @BotFather，發送 /newbot 建立 Bot，取得 token

# 2. 安裝 plugin
/plugin install telegram@claude-plugins-official

# 3. 設定 token（儲存到 ~/.claude/channels/telegram/.env）
/telegram:configure <你的_BOT_TOKEN>

# 4. 啟動
claude --channels plugin:telegram@claude-plugins-official

# 5. 在 Telegram 私訊你的 Bot，Bot 回覆配對碼
/telegram:access pair <配對碼>
/telegram:access policy allowlist
```

---

## 進階配置

### 多 Channel 同時啟用

```bash
claude --channels plugin:discord@claude-plugins-official plugin:telegram@claude-plugins-official
```

### 永久啟用 Remote Control

在 Claude Code 中執行 `/config`，將 **Enable Remote Control for all sessions** 設為 `true`。

### Push 通知（行動裝置）

1. 安裝 Claude App 並登入
2. 在 Claude Code 中執行 `/config`
3. 啟用 **Push when Claude decides**

Claude 會在長時間任務完成或需要你決策時推送通知。

### Server 模式（多 Session）

```bash
# 允許多個遠端 session
claude remote-control --spawn worktree --capacity 5

# 每個 session 會有自己的 git worktree
```

---

## 安全注意事項

- 所有流量透過 Anthropic API 經由 TLS 傳輸，不開啟本機的 inbound ports
- 每個 Channel 都有 sender allowlist：只有你配對過的帳號可以發送訊息
- 使用 `--channels` 明確指定哪些 channel 在本次 session 有效
- 不要在不信任的環境中使用 `--dangerously-skip-permissions`

---

## 使用場景建議

| 場景 | 推薦方案 |
|------|---------|
| 出門在外，用手機操控正在跑的 session | Remote Control + Claude App |
| 在 Discord 下達開發指令，不想開電腦 | Discord Channel |
| CI 失敗時自動通知並讓 Claude 修復 | Channel + Webhook receiver |
| 多人協作，在群組中 @Bot 執行任務 | Discord Channel (allowlist 多人) |

---

## 疑難排解

| 問題 | 解決方案 |
|------|---------|
| Bot 不回應 | 確認 Claude Code 有加 `--channels` 啟動 |
| "Channels not enabled" | Team/Enterprise 管理員需在 Admin settings 啟用 |
| Remote Control 連不上 | 確認用 claude.ai 帳號登入，非 API key |
| Plugin not found | 執行 `/plugin marketplace update claude-plugins-official` |
| 配對碼無效 | 重新發送訊息給 Bot 取得新碼 |
