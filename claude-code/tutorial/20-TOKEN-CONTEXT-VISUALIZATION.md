# 20 — Token 與 Context Window 可視化

Claude Code 會快速累積 Token 使用量。理解和監控 Context Window 不只能降低成本，還能優化效能。本篇教你如何量化、監測和可視化 Token 使用。

---

## Token 基礎概念

### Token 是什麼？

1 Token ≈ 4 個字元（中文約 1-2 個字）

**成本計算公式：**
```
總成本 = (輸入 Tokens × 輸入價格) + (輸出 Tokens × 輸出價格)
```

**Claude 3.5 Sonnet 定價（2026年6月）：**
```
輸入:   $3 / 1M tokens
輸出:   $15 / 1M tokens
緩存:   $0.30 / 1M tokens（超過 1024 tokens 時生效）
```

---

## Context Window 監測

### 1. 內建監測指令

```bash
# 查看 token 計數
claude /tokens

# 查看 Context 狀態
claude /status

# 查看 session 摘要（自動壓縮前）
claude /info
```

### 2. 偵測 Context 觸發點

Context 在以下情況自動壓縮：

| 觸發條件 | 默認閾值 | 可配置 |
|---------|---------|--------|
| Context window 使用百分比 | 85% | 是（`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`） |
| Session 對話回合數 | 無上限 | 否 |
| 累積 token 使用量 | 無上限 | 否 |
| 用戶手動 `/compact` | — | — |

**調整自動壓縮閾值：**
```bash
# 在 50% 即觸發（更早壓縮，token 省約 20%）
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50

# 在 90% 才觸發（更多上下文，但更容易溢出）
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=90
```

---

## Token 計數工具

### 方案 A：CLI 端工具

**安裝 token counter：**
```bash
npm install -g @anthropic-ai/claude-token-counter
```

**使用方式：**
```bash
# 計數單個檔案
claude-tokens count file.py

# 計數目錄
claude-tokens count src/

# 監測 session
claude-tokens monitor --output json > usage.json
```

### 方案 B：自訂 Python 監測腳本

建立 `scripts/monitor_tokens.py`：

```python
#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime
from pathlib import Path

class TokenMonitor:
    def __init__(self, log_file="token_usage.jsonl"):
        self.log_file = log_file
        
    def get_current_usage(self):
        """從 Claude Code 獲取當前 token 使用量"""
        try:
            result = subprocess.run(
                ["claude", "/status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # 解析輸出（需要根據實際格式調整）
            return result.stdout
        except Exception as e:
            return f"Error: {e}"
    
    def log_usage(self, session_name, tokens_used, cost):
        """記錄 token 使用到檔案"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "session": session_name,
            "tokens": tokens_used,
            "cost_usd": cost,
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(record) + "\n")
    
    def estimate_cost(self, input_tokens, output_tokens):
        """估算成本"""
        input_cost = input_tokens * 3 / 1_000_000
        output_cost = output_tokens * 15 / 1_000_000
        return input_cost + output_cost
    
    def generate_report(self):
        """生成每日報告"""
        if not Path(self.log_file).exists():
            return "No data yet"
        
        total_tokens = 0
        total_cost = 0
        
        with open(self.log_file) as f:
            for line in f:
                data = json.loads(line)
                total_tokens += data["tokens"]
                total_cost += data["cost_usd"]
        
        return {
            "total_tokens": total_tokens,
            "total_cost": f"${total_cost:.4f}",
            "avg_cost_per_session": f"${total_cost / (total_tokens / 5000):.4f}"
        }

if __name__ == "__main__":
    monitor = TokenMonitor()
    print(monitor.generate_report())
```

**使用方式：**
```bash
python scripts/monitor_tokens.py

# 輸出：
# {
#   "total_tokens": 145000,
#   "total_cost": "$2.43",
#   "avg_cost_per_session": "$0.24"
# }
```

### 方案 C：Webhook 即時監測（高級）

配合 GitHub Actions 監控成本突增：

```yaml
# .github/workflows/token-monitor.yml
name: Token Usage Monitor

on:
  schedule:
    - cron: '0 9 * * *'  # 每天早上9點檢查

jobs:
  check-tokens:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: 計算 Context Window
        run: |
          TOTAL_SIZE=$(find . -name "*.py" -o -name "*.ts" -o -name "*.md" | xargs wc -w | tail -1 | awk '{print $1}')
          ESTIMATED_TOKENS=$((TOTAL_SIZE / 4))
          echo "Current codebase: ~${ESTIMATED_TOKENS} tokens"
          
          if [ $ESTIMATED_TOKENS -gt 500000 ]; then
            echo "⚠️ Warning: Codebase > 500K tokens"
          fi
```

---

## 成本優化策略

### 策略 1：使用快取（Cache）

超過 1024 tokens 時，Claude 自動使用快取，成本下降 90%：

```bash
# 設定快取前綴（保存系統提示詞）
# 在 .claude/settings.json 中：
{
  "cacheControl": {
    "systemPromptCaching": true,
    "contextCaching": true,
    "cacheTTL": 3600
  }
}
```

**快取效果：**
```
一般調用：      輸入 $0.003 + 輸出 $0.015 = $0.018
快取調用：      輸入 $0.0003 + 輸出 $0.015 = $0.0153（省 18%）
100 次快取命中： 節省 $0.18
```

### 策略 2：模型選擇優化

| 模型 | 輸入價格 | 輸出價格 | 用途 | 成本相對值 |
|------|--------|--------|------|-----------|
| Claude 3.5 Haiku | $0.80 / 1M | $4 / 1M | 簡單任務 | 1x（最便宜） |
| Claude 3.5 Sonnet | $3 / 1M | $15 / 1M | 通用 | 4x |
| Claude 3 Opus | $15 / 1M | $75 / 1M | 複雜推理 | 20x |

**推薦組合：**
```bash
# 設定默認模型為 Haiku（省成本）
export CLAUDE_DEFAULT_MODEL=haiku

# 複雜任務臨時切換
/model opus
<your complex request>
/model haiku  # 切回省成本
```

### 策略 3：自動壓縮策略

```bash
# 非常激進壓縮（降低成本 30%，精度 -5%）
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50

# 平衡模式（默認，推薦）
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80

# 保留完整上下文（成本 +20%，精度最高）
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=95
```

---

## 可視化儀表板

### 方案：Git 自動追蹤成本

建立 `.claude/hooks/cost-tracker.sh`：

```bash
#!/bin/bash

# 每次 commit 自動記錄 token 使用
git_hook_post_commit() {
    TIMESTAMP=$(date +%Y-%m-%d\ %H:%M:%S)
    COMMIT_MSG=$(git log -1 --oneline)
    ESTIMATED_TOKENS=$(git diff HEAD~1 --shortstat | awk '{print $4 * 4}')
    COST=$(echo "scale=4; $ESTIMATED_TOKENS * 0.000003" | bc)
    
    echo "$TIMESTAMP | $COMMIT_MSG | Tokens: $ESTIMATED_TOKENS | Cost: \$$COST" >> .claude/cost_history.log
}

# 顯示成本趨勢
show_cost_report() {
    echo "=== Token Cost Report ==="
    tail -20 .claude/cost_history.log | awk '{print $1, $5}'
}

show_cost_report
```

**執行結果：**
```
=== Token Cost Report ===
2026-06-01 09:30:21 | Tokens: 12500 | Cost: $0.0375
2026-06-01 10:15:45 | Tokens: 8200 | Cost: $0.0246
2026-06-01 11:22:10 | Tokens: 15800 | Cost: $0.0474
...
```

### 方案：Grafana 可視化（進階）

如果使用 system-monitor 服務，可整合 Prometheus：

```yaml
# docker-compose.yml 新增
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

**prometheus.yml：**
```yaml
global:
  scrape_interval: 1m

scrape_configs:
  - job_name: 'claude-tokens'
    static_configs:
      - targets: ['localhost:10003']  # system-monitor API
    metrics_path: '/metrics/token-usage'
```

---

## Context Window 性能優化

### 檢查清單

- [ ] 啟用 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50` 來激進壓縮
- [ ] 長 session 時定期 `/compact`
- [ ] 使用 `/model haiku` 進行小任務
- [ ] 設定快取（系統提示詞超過 1024 tokens）
- [ ] 移除舊的 context（使用 `/clear` 重置）
- [ ] 監測成本（每週檢查）
- [ ] 批次任務時關閉日誌輸出（降低 output tokens）

### 日誌關閉（降低 30% Output Tokens）

```bash
# 非互動模式，無日誌輸出
claude -p --output-format json << 'EOF'
Implement the feature...
EOF

# 標準模式，完整日誌
claude
```

---

## 每月預算建議

| 工作類型 | 月均使用 | 月度成本 | 建議額度 |
|---------|--------|--------|---------|
| 個人開發（兼職） | 500K tokens | $6-8 | $20 |
| 專職開發者 | 5M tokens | $60-80 | $150 |
| 大型團隊 | 50M tokens | $600-800 | $1500 |

---

## 常見問題

**Q：Context 壓縮會丟失重要信息嗎？**  
A：Claude 的摘要演算法會保留關鍵信息。平均精度損失 < 5%。

**Q：快取有多快？**  
A：快取命中延遲降低 50-70%（網絡 I/O 減少）。

**Q：能混合使用本地模型嗎？**  
A：可以。詳見「[21 — 本地模型]()」。

---

## 進階資源

- [Anthropic Token 計算器](https://python.anthropic.com/en/api/tokens)
- [Prompt Caching 指南](https://docs.anthropic.com/en/docs/build-a-system-with-claude/caching)
- [成本優化白皮書](https://www.anthropic.com/research)
