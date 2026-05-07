# 08 — 進階工作流程

從日常開發到複雜專案，Claude Code 可以深度融入你的開發流程。

## 多檔案協同編輯

### 跨檔案重構

```
> 我要把 src/services/user.ts 中的驗證邏輯抽出來：
> 1. 建立 src/validators/user.validator.ts
> 2. 將 validateEmail, validatePassword, validateUsername 搬過去
> 3. 更新所有 import 該模組的檔案
> 4. 確認沒有遺漏的引用
```

Claude 會：
1. 讀取 `user.ts` 找到要抽取的函式
2. 搜尋所有使用這些函式的檔案
3. 建立新的 validator 檔案
4. 修改原始檔案（移除函式、加入 import）
5. 更新所有消費端的 import 路徑
6. 執行 TypeScript 編譯確認無誤

### 批次修改

```
> 將專案中所有的 console.log 替換為 logger.info
> 所有受影響的檔案要加上 import { logger } from '@/lib/logger'
> 排除 tests/ 目錄
```

## 除錯工作流

### 系統化除錯流程

```
> 我遇到一個問題，當使用者同時發兩個請求時會出現 race condition，
> 請用以下流程幫我排查：
> 1. 找出所有共享狀態的存取點
> 2. 辨識哪些操作不是原子性的
> 3. 畫出併發存取的時序圖
> 4. 提出修復方案
> 5. 實作修復並加上測試
```

### 日誌分析除錯

```bash
# 將日誌導入 Claude 分析
cat /var/log/app/error.log | claude -p "
分析這些錯誤日誌：
1. 按錯誤類別分組
2. 找出最頻繁的錯誤
3. 辨識根本原因
4. 建議修復優先級
"
```

### 效能除錯

```
> 我們的 API /api/users/search 回應時間超過 3 秒
> 請幫我：
> 1. 分析這個 endpoint 的完整程式碼路徑
> 2. 找出效能瓶頸（N+1 查詢？缺少索引？）
> 3. 提出改善方案並估算改善幅度
> 4. 實施最有效的改善方案
```

## 測試工作流

### TDD 流程

```
> 我們要用 TDD 方式開發 OrderService.calculateTotal 功能：
> 
> 需求：
> - 計算訂單總金額
> - 支援百分比折扣和固定金額折扣
> - 當折扣後金額小於 0 時回傳 0
> - 金額四捨五入到小數第二位
>
> 請依照 Red → Green → Refactor 流程進行：
> 1. 先寫測試（測試要會失敗）
> 2. 寫最少的程式碼讓測試通過
> 3. 重構
```

### 補齊測試覆蓋率

```
> 分析 src/services/ 目錄中所有 service 的測試覆蓋率：
> 1. 找出哪些函式沒有被測試覆蓋
> 2. 按風險等級排序（核心業務邏輯優先）
> 3. 為排名前 5 的函式補齊單元測試
```

### 整合測試

```
> 為我們的 REST API 建立整合測試：
> 1. 使用 supertest + vitest
> 2. 設定 test database
> 3. 覆蓋所有 CRUD endpoints
> 4. 包含認證和權限測試
> 5. 每個測試用例獨立、可重複執行
```

## Git 工作流

### 智慧 Commit

```
> 查看目前的所有變更
> 按邏輯將變更分成多個 commit：
> - 重構相關的變更一起
> - 新功能相關的一起
> - 測試相關的一起
> 每個 commit 寫清楚的 conventional commit message
```

### 分支管理

```
> 建立 feature/user-preferences 分支
> 在這個分支上完成用戶偏好設定功能
> 完成後 rebase 到最新的 main
> 建立 PR（自動產生描述）
```

### 衝突解決

```
> 目前 merge main 有衝突
> 請分析每個衝突：
> 1. 解釋衝突的原因
> 2. 根據兩邊的意圖，建議保留哪邊
> 3. 自動解決衝突
> 4. 確保解決後的程式碼功能正確
```

### 互動式 Code Review

```
> 對 feature/payment-v2 分支的變更做 code review
> 重點關注：
> - 金額計算的精確度
> - 交易的原子性
> - 錯誤回滾機制
> - 是否有重複扣款的風險
```

## 專案初始化工作流

### 新專案快速啟動

```
> 幫我建立一個 Node.js 後端專案：
> 
> 技術棧：
> - TypeScript + Express.js
> - PostgreSQL + Prisma ORM
> - JWT 認證
> - vitest 測試
> - Docker Compose 開發環境
> 
> 專案結構：
> - src/controllers/
> - src/services/
> - src/repositories/
> - src/middleware/
> - src/types/
> - tests/
> 
> 初始功能：
> - 健康檢查 endpoint
> - 用戶註冊/登入
> - 基本的 JWT middleware
> 
> 額外：
> - ESLint + Prettier 設定
> - GitHub Actions CI
> - Docker multi-stage build
> - CLAUDE.md 專案設定
```

### 既有專案快速上手

```
> 我剛 clone 了這個專案，幫我：
> 1. 分析完整的專案架構
> 2. 辨識使用的技術棧
> 3. 找出主要的進入點（entry points）
> 4. 畫出核心模組的依賴關係
> 5. 列出如何啟動和測試
> 6. 產生 CLAUDE.md 讓未來開發更高效
```

## 文件工作流

### 自動產生 API 文件

```
> 掃描 src/controllers/ 下所有的 endpoint
> 為每個 endpoint 產生 API 文件，包含：
> - HTTP method 和路徑
> - Request/Response 的 TypeScript 型別
> - 使用範例（curl）
> - 錯誤代碼說明
> 輸出為 docs/API.md
```

### README 更新

```
> 根據目前的程式碼和配置更新 README.md：
> - 確保安裝步驟是正確的
> - 環境變數清單是完整的
> - 啟動命令是最新的
> - 專案結構反映目前的狀態
```

## 資料庫工作流

### Migration 生成

```
> 我需要為 orders 表加一個 discount_code 欄位：
> 1. 設計欄位型別和約束
> 2. 產生 migration 檔案
> 3. 更新 Prisma schema
> 4. 更新相關的 TypeScript 型別
> 5. 順帶更新用到 orders 的 service 邏輯
```

### 查詢最佳化

```
> 分析 src/repositories/order.repo.ts 中的所有資料庫查詢：
> 1. 找出 N+1 查詢問題
> 2. 辨識缺少索引的查詢
> 3. 建議改善方案
> 4. 產生需要的索引 migration
```

## 安全審查工作流

```
> 對這個專案做安全審查：
> 
> 1. OWASP Top 10 檢查（Injection, XSS, CSRF 等）
> 2. 檢查密碼處理是否安全（hashing, salting）
> 3. 檢查 JWT 設定（expiry, algorithm, secret 管理）
> 4. 檢查是否有硬編碼的 secret 或 API key
> 5. 檢查依賴套件的已知漏洞
> 6. 檢查 HTTP headers 設定
> 7. 檢查 rate limiting
> 
> 每個發現列出：嚴重度、位置、修復建議
> 嚴重度為 High 的問題直接修復
```

## 工作流程自動化腳本模板

### pre-commit hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
# 讓 Claude 在 commit 前做快速審查

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACMR)

if [ -n "$STAGED_FILES" ]; then
  git diff --cached | claude -p "
    快速審查這些即將提交的變更：
    - 有無明顯 bug？
    - 有無遺漏的 error handling？
    - 有無敏感資訊？
    回答 PASS 或列出問題。
  " | tee /tmp/claude-review.txt

  if grep -q "PASS" /tmp/claude-review.txt; then
    exit 0
  else
    echo "⚠️ Claude 發現潛在問題，請檢查後再提交"
    exit 1
  fi
fi
```

---

⬅️ [上一篇：MCP 伺服器整合](07-MCP-INTEGRATION.md) | ➡️ [下一篇：自訂 Skills 與 Agents](09-CUSTOM-SKILLS-AGENTS.md)
