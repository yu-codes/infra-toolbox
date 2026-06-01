# 21 — 本地模型（Ollama、LM Studio、Llama.cpp）

Claude Code 可與本地 LLM 混合使用。用本地模型處理敏感數據、離線開發或降低成本，用 Claude 處理複雜推理。本篇教你搭建、配置和最佳實踐。

---

## 為什麼使用本地模型？

| 場景 | 本地模型 | Claude 雲端 | 建議 |
|------|--------|----------|------|
| **隱私敏感**（醫療、金融） | ✅ 完全隱私 | ❌ 發送到 Anthropic 雲 | 必須本地 |
| **離線開發**（飛機、山區） | ✅ 無網絡需求 | ❌ 需要網絡 | 混合模式 |
| **成本控制**（日用小任務） | ✅ 免費 | ❌ 每 token 計費 | 本地優先 |
| **複雜推理**（架構設計） | ❌ 能力弱 | ✅ 最佳 | Claude 優先 |
| **實時性**（邊緣計算） | ✅ <100ms | ❌ 500ms+ | 本地 |

---

## 支持的本地模型

### 推薦模型選擇

| 模型 | 大小 | 記憶需求 | 速度 | 推薦用途 |
|------|------|--------|------|---------|
| **Llama 2 Chat** | 7B | 8GB | 快 | 代碼完成、文本總結 |
| **Mistral 7B** | 7B | 8GB | 快 | 通用任務、簡單 coding |
| **Neural Chat** | 7B | 8GB | 快 | 對話、生成文案 |
| **Code Llama** | 7B | 8GB | 中 | **專業代碼任務** ⭐ |
| **Code Llama 34B** | 34B | 40GB | 慢 | 複雜代碼分析 |
| **Phi 2** | 2.7B | 4GB | 非常快 | 輕量級任務、移動設備 |

**推薦組合：**
- 日常小任務：`Phi 2`（4GB）
- 代碼開發：`Code Llama 7B`（8GB）
- 複雜推理：`Claude Sonnet`（雲端）

---

## 安裝和配置

### 方案 A：Ollama（推薦，最簡單）

**1. 安裝 Ollama**

```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh

# Windows
# 下載 https://ollama.ai/download/windows
```

**2. 啟動 Ollama 服務**

```bash
# 啟動背景服務
ollama serve

# 或前台運行
ollama run llama2
```

**3. 拉取模型**

```bash
# 代碼專用
ollama pull codellama

# 通用模型
ollama pull mistral
ollama pull neural-chat

# 輕量級
ollama pull phi
```

**4. 測試本地 API**

```bash
# Ollama 自動運行在 http://localhost:11434
curl http://localhost:11434/api/generate -d '{
  "model": "codellama",
  "prompt": "func fibonacci(n) {",
  "stream": false
}'
```

### 方案 B：LM Studio（UI 友好）

**1. 下載 LM Studio**  
https://lmstudio.ai/

**2. 在 GUI 中選擇並下載模型**  
搜索 → `Code Llama` → Download

**3. 啟動本地伺服器**  
點擊「Start Server」→ 默認 `localhost:1234`

### 方案 C：Llama.cpp（極輕量）

```bash
# 編譯
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make

# 下載量化模型（4-bit，極小）
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/Mistral-7B-Instruct-v0.1.Q4_K_M.gguf

# 啟動伺服器
./server -m Mistral-7B-Instruct-v0.1.Q4_K_M.gguf -ngl 35 -c 2048
```

---

## Claude Code 集成

### 集成方式 1：MCP 適配器（推薦）

在 `<project>/.mcp.json` 中新增本地 LLM：

```json
{
  "mcpServers": {
    "local-llm": {
      "type": "stdio",
      "command": "node",
      "args": ["./mcp/local-llm-adapter.js"],
      "env": {
        "LOCAL_LLM_URL": "http://localhost:11434",
        "LOCAL_LLM_MODEL": "codellama"
      }
    }
  }
}
```

**建立 `mcp/local-llm-adapter.js`：**

```javascript
const fetch = require('node-fetch');
const readline = require('readline');

const LOCAL_URL = process.env.LOCAL_LLM_URL || 'http://localhost:11434';
const MODEL = process.env.LOCAL_LLM_MODEL || 'mistral';

async function callLocalLLM(prompt) {
  try {
    const response = await fetch(`${LOCAL_URL}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: MODEL,
        prompt: prompt,
        stream: false,
        num_predict: 512
      })
    });
    
    const data = await response.json();
    return data.response;
  } catch (err) {
    return `Error calling local LLM: ${err.message}`;
  }
}

// MCP 標準輸入/輸出
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', async (line) => {
  const request = JSON.parse(line);
  
  if (request.method === 'complete') {
    const result = await callLocalLLM(request.prompt);
    console.log(JSON.stringify({
      result: result,
      tokens: Math.ceil(result.length / 4)
    }));
  }
});
```

使用方式：

```bash
> /mcp

# 查看可用的本地 LLM 工具
Available MCP servers: local-llm

> 用 local-llm 完成這個函數：def fib(n):
```

### 集成方式 2：自訂 Command（簡易版）

在 `<project>/.claude/commands/local.md` 中：

```markdown
---
description: 用本地模型快速處理
---

# /local

快速用本地 LLM 回應（不消耗 Claude tokens）。

## 使用方式

\`\`\`
/local <prompt>
\`\`\`

## 範例

\`\`\`
/local 寫個 Python decorator 用於緩存
/local 解釋這段 SQL
\`\`\`
```

對應的實現在 `.claude/agents/local-runner.md`：

```bash
#!/bin/bash

# 簡易本地 LLM 呼叫
curl http://localhost:11434/api/generate \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${LOCAL_MODEL:-codellama}\",
    \"prompt\": \"$1\",
    \"stream\": false
  }" | jq -r '.response'
```

---

## 最佳實踐

### 模式 1：本地優先 + Claude 增強

**日常流程：**
```
1. 簡單任務 → 用 /local（0 成本）
   範例：代碼格式檢查、文本摘要、簡單 bug 修復
   
2. 需要驗證 → /claude 審查（成本低）
   範例：檢查我的本地 LLM 建議是否正確
   
3. 複雜推理 → /model opus（完整功能）
   範例：重新設計架構、多層次推理
```

**成本節省：**
```
每天 100 次任務
- 全用 Claude：$0.12 /天 = $3.60 /月
- 本地優先：$0.02 /天 = $0.60 /月（省 83%）
```

### 模式 2：隱私保護工作流

**敏感任務：**
```
醫療記錄分析
  ↓
1. 用本地 Code Llama 初步分析（本機）
2. 移除個人信息
3. 發送給 Claude 進行高層分析
```

**配置示例：**
```bash
# 敏感任務使用本地模型
/local 分析這份醫療數據（不上傳）

# 安全後再用 Claude
<redacted summary>
/claude 基於此摘要給出建議
```

### 模式 3：離線開發

**場景：飛行中開發**

```bash
# 出發前準備
ollama pull codellama
export CLAUDE_OFFLINE_MODE=true

# 在飛機上
claude --local-only  # 只用本地模型

# 著陸後同步
claude --sync-session  # 上傳 session 到雲端
```

### 模式 4：成本控制 SLA

設定自動降級：

```bash
# 在 .claude/settings.json 中
{
  "costControl": {
    "dailyBudget": 5.00,
    "fallbackModel": "local",
    "localModel": "codellama",
    "cloudModelThreshold": 0.50
  }
}
```

邏輯：
```
cost today < $4.50 → 用 Claude
cost today >= $4.50 → 自動切換到 /local
```

---

## 性能對比

### 代碼完成速度

```
Phi 2 (4GB)        : 50ms   ⚡⚡⚡ (快但質量一般)
Code Llama 7B      : 200ms  ⚡⚡  (平衡)
Code Llama 34B     : 800ms  ⚡   (慢但精準)
Claude Sonnet      : 1200ms ⚡   (網絡延遲 + 推理)
```

### 代碼質量評分（0-100）

```
簡單任務（變數命名、格式化）:
  Phi 2           : 75
  Mistral 7B      : 82
  Code Llama 7B   : 88
  Claude Sonnet   : 96

複雜任務（架構設計、重構）:
  Phi 2           : 45
  Mistral 7B      : 62
  Code Llama 7B   : 75
  Claude Sonnet   : 98
```

---

## 故障排除

### 問題 1：本地模型回應慢

**症狀：** 等待 > 5 秒

**解決方案：**
```bash
# 檢查 GPU 是否啟用
ollama list
# 應顯示 "[GPU]" 標記

# 啟用 GPU 加速（Ollama）
export CUDA_VISIBLE_DEVICES=0
ollama serve

# 減少 token 預測長度
/local --max-tokens 256 <prompt>
```

### 問題 2：記憶體不足

**症狀：** OOM kill

**解決方案：**
```bash
# 使用量化模型（-Q4, -Q5）
ollama pull mistral:7b-instruct-q4  # 量化版，5GB

# 或用更小的模型
ollama pull phi  # 2.7B，4GB

# 限制批次大小
ollama serve --batch-size 1
```

### 問題 3：качество 不如預期

**症狀：** 結果錯誤或不相關

**解決方案：**
```bash
# 1. 改用更大的模型
ollama pull neural-chat  # 更好的對話能力

# 2. 調整 temperature（創意度）
curl http://localhost:11434/api/generate \
  -d '{"model":"mistral", "temperature": 0.2, "prompt":"..."}'

# 3. 添加系統提示詞
/local --system "你是代碼審查專家" <code>

# 4. 對複雜任務用 Claude
/model opus
<complex reasoning task>
```

---

## Docker 容器化本地 LLM

**docker-compose.yml：**

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: local-llm
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    environment:
      - CUDA_VISIBLE_DEVICES=0
    command: ollama serve

  claude-local-adapter:
    build: .
    container_name: claude-mcp-local
    ports:
      - "3000:3000"
    depends_on:
      - ollama
    environment:
      - LOCAL_LLM_URL=http://ollama:11434
      - LOCAL_LLM_MODEL=codellama
    volumes:
      - ./mcp:/app/mcp

volumes:
  ollama-data:

networks:
  default:
    name: infra-toolbox-network
    external: true
```

**啟動：**
```bash
docker compose up -d

# 初始化模型
docker exec local-llm ollama pull codellama
```

---

## 常見問題

**Q：本地模型會取代 Claude 嗎？**  
A：不會。用於不同場景：本地模型 = 快速、隱私、成本；Claude = 精準、推理、複雜。

**Q：可以在 MacBook Air M1 上跑 7B 模型嗎？**  
A：可以。Llama 2 7B 需要 8GB RAM，M1 有統一記憶體，完全夠。

**Q：如何選擇量化精度？**  
A：優先 Q4（5-7GB），若記憶體不足用 Q3（3-4GB），若精度要求高用 Q5（8-10GB）。

---

## 進階資源

- [Ollama 官方文檔](https://ollama.ai)
- [Code Llama 論文](https://arxiv.org/abs/2308.12950)
- [Llama 2 評測基準](https://huggingface.co/collections/meta-llama/llama-2-family-661e55ba7c4767a1aef4b723)
- [本地 LLM 性能優化](https://github.com/ggerganov/llama.cpp/discussions)
