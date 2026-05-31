# Chat-Repo Configs

透過 Slack / Discord 聊天室管理 Repo 的配置檔。

## 檔案說明

| 檔案 | 說明 |
| ---- | ---- |
| `channel-repo-config.json` | Channel 與 Repo 映射設定範本 |

## 設定步驟

1. 複製 `channel-repo-config.json` 到你的 dispatcher 服務目錄
2. 替換 `DISCORD_CHANNEL_ID_*` 為實際的 Discord channel ID
3. 替換 `DISCORD_USER_ID_*` 為授權使用者 ID
4. 替換 `/repos/*` 為實際 repo 路徑
5. 設定環境變數：
   - `DISCORD_BOT_TOKEN` — Discord Bot token
   - `ANTHROPIC_API_KEY` — Claude API key
   - `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN`（如使用 Slack）

## 教學

詳見 [tutorial/16-CHAT-REPO-MANAGEMENT.md](../../tutorial/16-CHAT-REPO-MANAGEMENT.md)
