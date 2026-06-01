---
# 全域通用規則（對所有專案生效）
# 安裝到 ~/.claude/rules/global.md
---

# 通用工作規則

## 安全
- 永遠不要讀取或輸出 `.env`、`*.key`、`*.pem`、`credentials*` 等機密檔案
- 不要將 token 或密碼寫入程式碼或 commit 訊息

## 程式碼品質
- 修改完成後若有測試框架，執行對應 test 命令確認未破壞行為
- 不要過度工程化，只做被要求的改動

## Git
- Commit message 格式：`type(scope): description`（英文）
- 常用 type：`feat`, `fix`, `docs`, `refactor`, `chore`, `test`
