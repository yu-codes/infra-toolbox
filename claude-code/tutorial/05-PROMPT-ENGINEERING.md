# 05 — Prompt 工程

掌握如何有效地與 Claude Code 溝通，是從「使用者」進化為「大師」的關鍵。

## 核心原則

### 0. 讓 Claude 訪談你（Interview Pattern）

官方推薦的最佳實踐：不確定如何表達需求時，讓 Claude 反過來問你：

```
> 我想建立一個通知系統，但不確定技術方案。
> 請問我 5 個問題來釨清需求，然後再開始設計。

# Claude 會問：
# 1. 通知要支援哪些管道？
# 2. 是即時推撥還是排程發送？
# 3. ...
```

這比你花 30 分鐘寫一個超長 prompt 更有效。

### 1. 具體勝過模糊

```
❌ 不好：幫我改善這個程式碼
✅ 好的：將 src/api/users.ts 中的 getUser 函式從同步改為 async/await，
        加上 try-catch 錯誤處理，並回傳統一的 ApiResponse 格式
```

### 2. 提供上下文

```
❌ 不好：寫一個登入功能
✅ 好的：在 src/auth/ 目錄下建立登入功能，使用 JWT + bcrypt，
        遵循專案既有的 controller → service → repository 分層，
        參考 src/auth/register.ts 的風格
```

### 3. 拆解複雜任務

```
❌ 不好：幫我建立完整的用戶管理系統

✅ 好的（分步驟）：
> 步驟一：先幫我設計 User domain model，包含 id, email, name, role 欄位
> 步驟二：建立 UserRepository 介面和 PostgreSQL 實作
> 步驟三：建立 UserService 包含 CRUD 操作
> 步驟四：建立 REST API endpoints
```

### 4. 指定約束條件

```
> 重構 PaymentService，但要保持以下條件：
> 1. 現有的公開 API 介面不變
> 2. 所有測試必須繼續通過
> 3. 不引入新的依賴套件
> 4. 保持向後相容
```

## Prompt 範本庫

### 程式碼審查

```
請審查 src/services/order.ts 的變更，關注以下重點：
1. 是否有潛在的 bug 或邊界條件未處理
2. 效能是否有改善空間
3. 是否符合 SOLID 原則
4. 錯誤處理是否完整
5. 是否有安全性漏洞

請列出發現的問題和建議的修復方案。
```

### 除錯

```
我遇到一個問題：
- 症狀：[描述你看到的行為]
- 期望：[描述你期望的行為]
- 重現步驟：[如何重現]
- 已嘗試：[你已經試過什麼]
- 相關檔案：[可能相關的檔案路徑]

請幫我找出根本原因並修復。
```

### 新功能開發

```
請在 src/features/ 下建立「通知系統」功能：

需求：
- 支援 Email、SMS、推播三種管道
- 使用 Strategy Pattern 讓管道可擴展
- 通知內容支援模板渲染
- 記錄發送歷史到資料庫

技術限制：
- 使用既有的 MailService 發送 Email
- SMS 使用 Twilio SDK
- 推播使用 Firebase Cloud Messaging

請先規劃檔案結構，確認後再開始實作。
```

### 重構

```
重構 src/legacy/monolith.ts：
- 目前：所有邏輯在一個 800 行的檔案中
- 目標：拆分為獨立的模組，遵循單一職責原則
- 方法：先分析目前的函式依賴關係，再提出拆分計劃

注意：要確保每步重構後測試都通過。
```

### 測試生成

```
為 src/services/payment.ts 撰寫單元測試：
- 使用 vitest 框架
- Mock 所有外部依賴（DB、API）
- 覆蓋以下情境：
  - 正常支付流程
  - 餘額不足
  - 支付閘道超時
  - 重複支付防護
  - 退款流程
- 使用 Arrange-Act-Assert 模式
- 測試檔案放在 tests/unit/services/payment.test.ts
```

## Prompt 技巧

### 技巧 1：讓 Claude 先分析再動手（配合 Plan Mode）

```
# 按 Ctrl+G 進入 Plan Mode，Claude 只規劃不執行
> 重構 UserService，拆分成 3 個小 Service

# Plan Mode 中 Claude 會：
# 1. 分析目前架構
# 2. 列出重構計畫（不寫程式碼）
# 3. 等你確認後，按 Ctrl+G 切回執行模式再實作

# 傳統方式（也有效）：
> 先閱讀 src/core/ 目錄下的所有檔案
> 然後畫出模組之間的依賴關係圖
> 找出可能的循環依賴
> 最後才提出重構建議
```

> 💡 **Plan Mode（Ctrl+G）** 是官方推薦的「先探索、再規劃、最後寫程式」工作流程的核心。

### 技巧 2：使用參考範例

```
> 參考 src/services/user.service.ts 的實作風格
> 建立一個新的 product.service.ts
> 保持一致的 error handling、logging 和命名規範
```

### 技巧 3：限定操作範圍

```
> 只修改 src/api/ 目錄下的檔案
> 不要動 src/domain/ 和 tests/ 的任何東西
> 專注在 API 層的錯誤處理改善
```

### 技巧 4：漸進式確認

```
> 幫我重構認證模組，但每個步驟先跟我確認：
> 1. 第一步：分析目前的架構（分析完後暫停）
> 2. 第二步：提出重構計劃（確認後再動手）
> 3. 第三步：逐一實施（每完成一個檔案報告進度）
```

### 技巧 5：利用管道輸入外部資訊

```bash
# 將錯誤訊息直接餵入
npm test 2>&1 | claude -p "分析這些測試失敗的原因並修復"

# 將 API 文件餵入
curl -s https://api.example.com/docs | claude -p "根據這個 API 文件產生 TypeScript client"

# 將 diff 餵入
git diff main..feature | claude -p "審查這些變更，列出潛在問題"
```

### 技巧 6：用 /btw 問側問題

對話中突然想問一個不相關的問題，但不想污染當前上下文：

```
> /btw Node.js 的 crypto.randomUUID() 需要 Node 幾版以上？
```

`/btw` 會在獨立上下文中回答，不影響主對話的 token 和流程。

### 技巧 7：要求多方案比較

```
> 我需要實作快取策略，請提供三種方案：
> 1. 記憶體快取（Map）
> 2. Redis 快取
> 3. 檔案系統快取
>
> 每個方案列出：優缺點、適用場景、效能影響、實作複雜度
> 最後根據我們的專案特性推薦一個
```

### 技巧 8：使用 Extended Thinking

Claude Code 支援 extended thinking 模式（使用 Opus/Sonnet 模型），讓 Claude 在回答前先做深度思考：

```
> 這個問題比較複雜，請深入思考後再回答：
> src/core/event-bus.ts 目前的事件分發機制在高併發下會有什麼問題？
> 如何在不改變公開 API 的前提下提升效能？
```

## 反模式（避免這樣做）

### ❌ 過於模糊

```
> 修好它
> 讓它更好
> 隨便改改
```

### ❌ 一次做太多

```
> 幫我重構整個專案、加上測試、更新文件、升級所有依賴、
> 改善 CI/CD、加上監控，然後部署到生產環境
```

### ❌ 不提供必要上下文

```
> 修這個 bug（沒有說是什麼 bug、在哪裡）
> 加個功能（沒有說加什麼功能、需求規格）
```

### ❌ 矛盾的指令

```
> 不要修改任何檔案，但要修好所有 bug
> 不要寫測試，但要確保覆蓋率 100%
```

### ❌ 忽略 Claude 的回饋

```
# Claude 說："這個修改可能破壞 X 功能..."
> 不管，直接做                     ← 可能造成更多問題

# 更好的做法：
> 你說的風險是合理的，那我們改成...   ← 雙向溝通
```

## Prompt 組合心法

### 黃金公式

```
[目標] + [上下文] + [約束] + [預期輸出格式]
```

範例：
```
目標：建立 API rate limiter middleware
上下文：Express.js 後端，已有 Redis 連線
約束：使用 sliding window 演算法，限制每 IP 每分鐘 60 次
輸出：先寫骨架讓我確認，確認後再完整實作
```

### 複雜任務框架

```
## 背景
[為什麼需要做這件事]

## 目標
[要達成什麼結果]

## 當前狀態
[目前是什麼樣子]

## 技術要求
[用什麼技術、遵循什麼規範]

## 驗收標準
[怎樣算完成]
```

---

⬅️ [上一篇：記憶系統](04-MEMORY-SYSTEM.md) | ➡️ [下一篇：Agent 模式與自動化](06-AGENT-MODE.md)
