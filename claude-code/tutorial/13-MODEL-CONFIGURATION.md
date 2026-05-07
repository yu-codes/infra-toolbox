# 模型配置指南：第三方模型與本地端模型

本指南涵蓋 Claude Code 的模型切換、第三方雲端模型、LLM Gateway、以及本地端模型配置。

---

## 基礎：切換 Claude 模型

### 可用模型別名

| 別名 | 用途 |
|------|------|
| `sonnet` | 日常開發工作（推薦預設） |
| `opus` | 複雜推理、架構設計 |
| `haiku` | 簡單任務、快速回應 |
| `opusplan` | Plan 模式用 Opus，執行用 Sonnet |
| `sonnet[1m]` | Sonnet + 1M token 上下文 |
| `opus[1m]` | Opus + 1M token 上下文 |

### 切換方式

```bash
# 啟動時指定
claude --model opus

# Session 中切換
/model sonnet

# 環境變數
export ANTHROPIC_MODEL=opus

# settings.json 永久設定
{
  "model": "sonnet"
}
```

### Effort Level（思考強度）

```bash
# 互動式調整
/effort

# 直接設定
/effort high
/effort xhigh

# 環境變數
export CLAUDE_CODE_EFFORT_LEVEL=xhigh
```

| Level | 適用場景 |
|-------|---------|
| low | 簡單、低延遲任務 |
| medium | 成本敏感的日常工作 |
| high | 需要智慧的任務（推薦預設） |
| xhigh | Opus 4.7 推薦預設，複雜開發 |
| max | 極度複雜任務（單次 session） |

---

## 第三方雲端模型配置

### Amazon Bedrock

```bash
# 啟用 Bedrock
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_REGION=us-east-1

# 如果使用 AWS SSO
export AWS_PROFILE=your-profile

# 指定模型版本（推薦明確指定）
export ANTHROPIC_DEFAULT_OPUS_MODEL='us.anthropic.claude-opus-4-7'
export ANTHROPIC_DEFAULT_SONNET_MODEL='us.anthropic.claude-sonnet-4-6'
export ANTHROPIC_DEFAULT_HAIKU_MODEL='us.anthropic.claude-haiku-4-5'
```

確認你的 AWS 帳號有 Bedrock 的存取權限和對應 Model Access。

### Google Vertex AI

```bash
# 啟用 Vertex AI
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=us-east5
export ANTHROPIC_VERTEX_PROJECT_ID=your-gcp-project-id

# 確認已登入 gcloud
gcloud auth application-default login

# 指定模型版本
export ANTHROPIC_DEFAULT_OPUS_MODEL='claude-opus-4-7'
export ANTHROPIC_DEFAULT_SONNET_MODEL='claude-sonnet-4-6'
```

### Microsoft Azure Foundry

```bash
# 啟用 Foundry
export CLAUDE_CODE_USE_FOUNDRY=1
export ANTHROPIC_FOUNDRY_RESOURCE=your-resource-name
export ANTHROPIC_FOUNDRY_API_KEY=your-api-key

# 或使用 Entra ID 認證（不設 API key 即自動使用）
```

---

## LLM Gateway 配置

如果你的組織使用 LLM Gateway（如 LiteLLM、OpenRouter 等）代理請求：

```bash
# 直接 API 的 Gateway
export ANTHROPIC_BASE_URL=https://your-gateway.example.com/v1

# Bedrock Gateway
export ANTHROPIC_BEDROCK_BASE_URL=https://your-bedrock-gateway.example.com

# Vertex AI Gateway
export ANTHROPIC_VERTEX_BASE_URL=https://your-vertex-gateway.example.com
```

### 搭配 Corporate Proxy

```bash
# 所有出站流量走 Proxy
export HTTPS_PROXY='https://proxy.example.com:8080'
```

### 自訂模型選項

如果你的 Gateway 有自訂的 model ID：

```bash
export ANTHROPIC_CUSTOM_MODEL_OPTION="my-gateway/claude-opus-4-7"
export ANTHROPIC_CUSTOM_MODEL_OPTION_NAME="Opus via Gateway"
export ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION="Internal gateway routed model"
```

---

## 本地端模型配置

> **重要提示**: Claude Code 官方僅支援 Anthropic 的模型（透過直連、Bedrock、Vertex、Foundry）。
> 本地端模型需要透過相容 Anthropic API 的 Gateway 來橋接。

### 方案一：使用 LiteLLM 作為中間層

LiteLLM 可以將多種模型（包括 Ollama 本地模型）包裝成 Anthropic API 相容格式。

#### Step 1：安裝 LiteLLM

```bash
pip install litellm[proxy]
```

#### Step 2：建立設定檔

建立 `litellm_config.yaml`：

```yaml
model_list:
  # 本地 Ollama 模型映射為 Claude 格式
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: ollama/qwen2.5-coder:32b
      api_base: http://localhost:11434
  
  - model_name: claude-haiku-4-5
    litellm_params:
      model: ollama/qwen2.5-coder:7b
      api_base: http://localhost:11434

  # 也可以混合使用雲端模型
  - model_name: claude-opus-4-7
    litellm_params:
      model: anthropic/claude-opus-4-7
      api_key: os.environ/ANTHROPIC_API_KEY
```

#### Step 3：啟動 LiteLLM Proxy

```bash
litellm --config litellm_config.yaml --port 4000
```

#### Step 4：設定 Claude Code 指向 LiteLLM

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000
export ANTHROPIC_API_KEY=sk-fake-key  # LiteLLM 需要一個 key，隨意填寫
```

#### Step 5：啟動 Claude Code

```bash
claude
```

### 方案二：使用 Ollama + OpenAI 相容層

如果你只需要簡單的本地模型，可以直接用 Ollama 的 OpenAI 相容 endpoint：

#### Step 1：安裝並啟動 Ollama

```bash
# macOS
brew install ollama
ollama serve

# Linux
curl -fsSL https://ollama.ai/install.sh | sh
systemctl start ollama

# Windows
# 從 https://ollama.ai 下載安裝程式
```

#### Step 2：下載模型

```bash
# 推薦的程式碼模型
ollama pull qwen2.5-coder:32b     # 大型，品質最好
ollama pull qwen2.5-coder:14b     # 中型，平衡效能
ollama pull deepseek-coder-v2:16b # 另一個好選擇
ollama pull codellama:34b          # Meta 的程式碼模型
```

#### Step 3：配合 LiteLLM 使用

同方案一的 LiteLLM 設定，將 Ollama 模型映射為 Anthropic API 格式。

### 方案三：使用 OpenRouter

OpenRouter 提供多種模型的統一 API，包括開源模型：

```bash
export ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
export ANTHROPIC_API_KEY=your-openrouter-key

# 可以存取各種模型包括：
# anthropic/claude-opus-4-7
# google/gemini-2.5-pro
# deepseek/deepseek-r1
# meta/llama-3.3-70b
```

---

## 成本優化策略

### 推薦的 settings.json 配置

```json
{
  "model": "sonnet",
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "60",
    "CLAUDE_CODE_SUBAGENT_MODEL": "haiku"
  }
}
```

### 日常工作流程

| 指令 | 用途 |
|------|------|
| `/model sonnet` | 大部分任務的預設 |
| `/model opus` | 複雜架構、深度 debug |
| `/model haiku` | 簡單的程式碼生成 |
| `/clear` | 任務間清除上下文（免費） |
| `/compact` | 邏輯斷點壓縮上下文 |
| `/cost` | 查看當前 session 花費 |

### Context Window 管理

- 控制啟用的 MCP server 數量（建議 <10 個）
- 控制 active tools 數量（建議 <80 個）
- 用 `/mcp` 停用不需要的 MCP server
- 任務之間使用 `/clear` 重置

---

## 環境變數快速參考

| 變數 | 用途 |
|------|------|
| `ANTHROPIC_MODEL` | 覆蓋預設模型 |
| `ANTHROPIC_API_KEY` | API key（Console 認證） |
| `CLAUDE_CODE_USE_BEDROCK=1` | 啟用 Amazon Bedrock |
| `CLAUDE_CODE_USE_VERTEX=1` | 啟用 Google Vertex AI |
| `CLAUDE_CODE_USE_FOUNDRY=1` | 啟用 Microsoft Foundry |
| `ANTHROPIC_BASE_URL` | 自訂 API endpoint |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | 覆蓋 opus 別名 |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | 覆蓋 sonnet 別名 |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | 覆蓋 haiku 別名 |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Subagent 使用的模型 |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 自動壓縮觸發百分比 |
| `MAX_THINKING_TOKENS` | 思考 token 上限 |

---

## 疑難排解

| 問題 | 解決方案 |
|------|---------|
| "Model not available" | 確認你的帳號/雲端有該模型存取權 |
| Bedrock 連不上 | 檢查 `AWS_REGION` 和 IAM 權限 |
| Vertex AI 錯誤 | 確認 `gcloud auth` 已登入 |
| LiteLLM 無回應 | 確認 Proxy 正在執行、Ollama 模型已下載 |
| 本地模型品質差 | 使用更大的模型或切回雲端 Claude |
| `/model` 不顯示選項 | 更新 Claude Code 到最新版 |
