# Redis Backup Service - BDD 規格

## Feature: Redis 資料備份服務

作為一個 Docker 基礎設施工具，Redis Backup 提供自動化的 Redis 資料庫備份功能，支援排程備份、手動備份、備份還原以及備份保留策略。

---

## Feature 1: 自動排程備份

```gherkin
Feature: 自動排程備份
  As a 系統管理員
  I want 設定自動排程備份 Redis 資料
  So that 資料可以定期被安全保存，無需人工介入

  Background:
    Given Redis 服務運行於 "redis:6379"
    And 備份存儲目錄為 "/backups"
    And 備份排程設定為 "0 2 * * *" (每日凌晨 2 點)

  Scenario: 成功執行排程備份
    Given Redis 連線狀態正常
    And 備份存儲目錄有足夠空間
    When 到達排程時間
    Then 應該觸發 BGSAVE 命令
    And 等待 RDB 檔案生成完成
    And 將 RDB 檔案複製到備份目錄
    And 備份檔案應該命名為 "redis_backup_YYYYMMDD_HHMMSS.rdb"
    And 備份完成後發送通知

  Scenario: Redis 連線失敗時的備份處理
    Given Redis 連線狀態異常
    When 到達排程時間
    Then 應該記錄連線失敗錯誤
    And 重試連線最多 3 次，間隔 10 秒
    And 若仍失敗則發送告警通知
    And 備份狀態應標記為 "FAILED"

  Scenario: 備份存儲空間不足
    Given Redis 連線狀態正常
    And 備份存儲目錄剩餘空間低於閾值
    When 到達排程時間
    Then 應該先清理過期備份
    And 再次檢查空間是否足夠
    And 若空間仍不足則發送告警並取消備份

  Scenario Outline: 不同排程頻率的備份
    Given 備份排程設定為 "<cron_expression>"
    When 系統時間符合排程
    Then 應該執行備份任務

    Examples:
      | cron_expression | description    |
      | 0 2 * * *       | 每日凌晨 2 點  |
      | 0 */6 * * *     | 每 6 小時      |
      | 0 0 * * 0       | 每週日午夜     |
      | 0 0 1 * *       | 每月 1 日午夜  |
```

---

## Feature 2: 手動備份

```gherkin
Feature: 手動備份
  As a 系統管理員
  I want 透過 API 觸發立即備份
  So that 可以在關鍵操作前確保資料安全

  Scenario: 透過 API 觸發備份
    Given Redis 連線狀態正常
    And 無其他備份任務正在執行
    When 發送 POST 請求到 "/api/v1/backup/trigger"
    Then 應該返回 202 Accepted 狀態碼
    And 返回備份任務 ID
    And 開始執行備份任務

  Scenario: 查詢備份任務狀態
    Given 已存在備份任務 ID "task-123"
    When 發送 GET 請求到 "/api/v1/backup/status/task-123"
    Then 應該返回任務狀態資訊
    And 包含 "status", "start_time", "progress" 欄位

  Scenario: 同時只允許一個備份任務
    Given 已有備份任務正在執行
    When 發送 POST 請求到 "/api/v1/backup/trigger"
    Then 應該返回 409 Conflict 狀態碼
    And 返回錯誤訊息 "另一個備份任務正在執行中"

  Scenario: 帶標籤的手動備份
    Given Redis 連線狀態正常
    When 發送 POST 請求到 "/api/v1/backup/trigger"
    And 請求包含 JSON body: {"label": "pre-migration"}
    Then 備份檔案名稱應包含標籤 "pre-migration"
    And 備份記錄應標記為手動觸發
```

---

## Feature 3: 備份還原

```gherkin
Feature: 備份還原
  As a 系統管理員
  I want 從備份檔案還原 Redis 資料
  So that 可以在資料損壞或誤刪除時恢復

  Background:
    Given 存在備份檔案 "redis_backup_20240101_020000.rdb"
    And 備份檔案校驗碼正確

  Scenario: 成功還原備份
    Given Redis 服務運行中
    When 發送 POST 請求到 "/api/v1/restore"
    And 請求包含 JSON body: {"backup_file": "redis_backup_20240101_020000.rdb"}
    Then 應該停止 Redis 服務
    And 備份當前 RDB 檔案
    And 替換為選定的備份檔案
    And 重新啟動 Redis 服務
    And 驗證 Redis 資料完整性
    And 返回還原結果

  Scenario: 還原前自動備份當前狀態
    When 執行還原操作
    Then 應該先建立當前狀態的快照
    And 快照命名為 "pre_restore_YYYYMMDD_HHMMSS.rdb"
    And 記錄還原操作日誌

  Scenario: 還原失敗時回滾
    Given 還原過程中發生錯誤
    When 錯誤被捕獲
    Then 應該回滾到還原前狀態
    And 記錄錯誤詳情
    And 發送告警通知
    And 返回失敗原因

  Scenario: 還原指定的備份
    Given 存在多個備份檔案
    When 發送 GET 請求到 "/api/v1/backups"
    Then 應該返回所有可用備份列表
    And 每個備份包含 "filename", "size", "created_at", "checksum"
```

---

## Feature 4: 備份保留策略

```gherkin
Feature: 備份保留策略
  As a 系統管理員
  I want 自動清理過期備份
  So that 儲存空間可以被有效利用

  Background:
    Given 備份保留策略配置為:
      | retention_days | 7     |
      | max_backups    | 30    |
      | min_backups    | 3     |

  Scenario: 清理超過保留天數的備份
    Given 存在 10 個備份檔案
    And 其中 3 個超過 7 天
    When 執行清理任務
    Then 應該刪除 3 個超過 7 天的備份
    And 保留 7 個較新的備份
    And 記錄清理日誌

  Scenario: 保留最少備份數量
    Given 存在 3 個備份檔案
    And 全部超過 7 天
    When 執行清理任務
    Then 應該保留所有 3 個備份（不低於最小數量）
    And 記錄警告日誌

  Scenario: 超過最大備份數量時的處理
    Given 存在 35 個備份檔案
    When 執行清理任務
    Then 應該刪除最舊的 5 個備份
    And 保留 30 個最新備份

  Scenario: 標記為重要的備份不會被清理
    Given 存在備份標記為 "important"
    And 該備份超過保留天數
    When 執行清理任務
    Then 該備份應該被保留
    And 記錄保留原因
```

---

## Feature 5: 健康檢查與監控

```gherkin
Feature: 健康檢查與監控
  As a 運維人員
  I want 監控備份服務的健康狀態
  So that 可以及時發現並處理問題

  Scenario: 服務健康檢查端點
    When 發送 GET 請求到 "/health"
    Then 應該返回 200 狀態碼
    And 包含以下資訊:
      | field              | type    |
      | status             | string  |
      | redis_connected    | boolean |
      | storage_available  | string  |
      | last_backup_time   | string  |
      | next_backup_time   | string  |

  Scenario: Redis 連線異常時的健康狀態
    Given Redis 連線失敗
    When 發送 GET 請求到 "/health"
    Then 應該返回 503 Service Unavailable
    And status 應為 "unhealthy"
    And 包含錯誤詳情

  Scenario: 取得備份指標
    When 發送 GET 請求到 "/metrics"
    Then 應該返回 Prometheus 格式的指標
    And 包含以下指標:
      | metric_name                    |
      | redis_backup_total             |
      | redis_backup_success_total     |
      | redis_backup_failed_total      |
      | redis_backup_duration_seconds  |
      | redis_backup_size_bytes        |
      | redis_backup_last_success_time |
```

---

## Feature 6: 通知與告警

```gherkin
Feature: 通知與告警
  As a 系統管理員
  I want 在關鍵事件發生時收到通知
  So that 可以及時了解備份狀態

  Background:
    Given 通知設定為:
      | channel  | webhook_url                          |
      | slack    | https://hooks.slack.com/services/... |
      | email    | admin@example.com                    |

  Scenario: 備份成功通知
    Given 備份任務完成
    And 備份狀態為成功
    When 發送通知
    Then 應該發送成功通知到所有配置的頻道
    And 通知包含備份檔案名稱、大小、耗時

  Scenario: 備份失敗告警
    Given 備份任務失敗
    When 發送告警
    Then 應該發送告警到所有配置的頻道
    And 告警包含失敗原因、時間戳
    And 告警優先級應為 "high"

  Scenario: 儲存空間不足警告
    Given 儲存空間使用率超過 85%
    When 執行儲存空間檢查
    Then 應該發送警告通知
    And 建議清理過期備份或增加儲存空間
```
