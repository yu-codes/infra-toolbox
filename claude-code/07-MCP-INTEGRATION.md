# 07 — MCP 伺服器整合

Model Context Protocol（MCP）是 Anthropic 發布的開放協定，讓 Claude Code 連接外部工具和資料源，大幅擴展能力。

## MCP 概念

```
┌──────────────┐     MCP 協定      ┌──────────────────┐
│  Claude Code  │ ◄──────────────► │  MCP Server       │
│  (MCP Client) │                  │  (外部工具/資料)    │
└──────────────┘                   └──────────────────┘
                                          │
                                   ┌──────┴──────┐
                                   │ GitHub API  │
                                   │ Database    │
                                   │ File System │
                                   │ Slack       │
                                   │ Jira        │
                                   │ 自訂工具     │
                                   └─────────────┘
```

### MCP 提供的能力

| 能力 | 說明 | 範例 |
|------|------|------|
| **Tools** | 可執行的動作 | 建立 GitHub Issue、查詢資料庫 |
| **Resources** | 可讀取的資料 | 文件內容、API 回應 |
| **Prompts** | 預定義的提示範本 | 程式碼審查模板 |

## 設定 MCP 伺服器

### 方法一：CLI 指令（推薦）

```bash
# 新增 MCP 伺服器
claude mcp add <name> -- <command> [args...]

# 範例
claude mcp add github -- npx -y @modelcontextprotocol/server-github
claude mcp add postgres -- npx -y @modelcontextprotocol/server-postgres "$DATABASE_URL"
claude mcp add fetch -- npx -y @modelcontextprotocol/server-fetch

# 帶環境變數
claude mcp add github -e GITHUB_TOKEN=ghp_xxx -- npx -y @modelcontextprotocol/server-github

# 列出 / 移除
claude mcp list
claude mcp remove github
```

### 方法二：.mcp.json 設定檔（專案層級，可提交 Git）

```json
// 專案根目錄/.mcp.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### 方法三：settings.json（舊式，仍支援）

```json
// 專案層級：.claude/settings.json
// 全域層級：~/.claude/settings.json
{
  "mcpServers": {
    "server-name": {
      "command": "執行命令",
      "args": ["參數"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

## 常用 MCP 伺服器

### 1. GitHub

讓 Claude 操作 GitHub — 建立 Issue、PR、管理 Repository。

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**提供的工具：**
- `create_issue` — 建立 Issue
- `create_pull_request` — 建立 PR
- `search_repositories` — 搜尋 Repo
- `get_file_contents` — 讀取 GitHub 上的檔案
- `list_commits` — 列出 commit 歷史

**使用範例：**
```
> 在 GitHub 上建立一個 Issue，標題是 "修復登入頁面 CSS"，
  加上 bug 和 frontend 標籤

> 把目前的變更建立一個 PR 到 main branch，
  自動產生 PR 描述
```

### 2. Filesystem（檔案系統）

擴展的檔案操作能力：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y", "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/directory"
      ]
    }
  }
}
```

### 3. PostgreSQL

直接查詢和分析資料庫：

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y", "@modelcontextprotocol/server-postgres",
        "${DATABASE_URL}"
      ]
    }
  }
}
```

**使用範例：**
```
> 查詢 users 表的結構
> 找出最近 7 天沒有登入的用戶數量
> 分析 orders 表的索引使用情況
```

### 4. Puppeteer（瀏覽器操作）

讓 Claude 控制瀏覽器：

```json
{
  "mcpServers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

**使用範例：**
```
> 打開 http://localhost:3000 截圖
> 測試登入流程是否正常
> 檢查首頁的 Lighthouse 分數
```

### 5. Slack

讓 Claude 發送 Slack 訊息和管理頻道：

```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${SLACK_TOKEN}",
        "SLACK_TEAM_ID": "${SLACK_TEAM}"
      }
    }
  }
}
```

### 6. Fetch（HTTP 請求）

讓 Claude 發送 HTTP 請求：

```json
{
  "mcpServers": {
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```

**使用範例：**
```
> 呼叫 https://api.example.com/users 並分析回應格式
> 測試我們的 API endpoint 是否回傳正確的 status code
```

### 7. Memory（持久化記憶）

基於知識圖譜的長期記憶：

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

## 多個 MCP 伺服器同時使用

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "${DATABASE_URL}"]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```

## MCP 工具權限管理

```json
{
  "permissions": {
    "allow": [
      "mcp__github__create_issue",
      "mcp__github__create_pull_request",
      "mcp__postgres__query"
    ],
    "deny": [
      "mcp__postgres__execute",
      "mcp__filesystem__delete_file"
    ]
  }
}
```

命名規則：`mcp__<server-name>__<tool-name>`

## 除錯 MCP 連線

### 檢查 MCP 狀態

```bash
# 用 CLI 列出已設定的 MCP 伺服器
claude mcp list

# 啟動 Claude Code 後
> /status

# 或直接問
> 列出目前可用的 MCP 工具

# 檢查特定伺服器
> MCP github 伺服器是否正常連線？
```

### 常見問題

**問題：MCP 伺服器連線失敗**
```bash
# 確認套件可用
npx -y @modelcontextprotocol/server-github --help

# 確認環境變數有設定
echo $GITHUB_TOKEN
```

**問題：工具呼叫被拒絕**
```json
// 檢查 permissions 設定
{
  "permissions": {
    "allow": ["mcp__github__*"]  // 允許 github 所有工具
  }
}
```

**問題：伺服器啟動超時**
```json
{
  "mcpServers": {
    "slow-server": {
      "command": "node",
      "args": ["server.js"],
      "timeout": 30000  // 加大超時毫秒數
    }
  }
}
```

## 建立自訂 MCP 伺服器

如果現有伺服器不夠用，你可以建立自己的：

### 基本結構（TypeScript）

```typescript
// my-mcp-server/src/index.ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "my-custom-server",
  version: "1.0.0",
});

// 定義工具
server.tool(
  "query_internal_api",
  "查詢內部 API",
  {
    endpoint: z.string().describe("API endpoint path"),
    method: z.enum(["GET", "POST"]).describe("HTTP method"),
  },
  async ({ endpoint, method }) => {
    // 你的實作邏輯
    const result = await fetch(`https://internal-api.company.com${endpoint}`, {
      method,
    });
    const data = await result.json();
    return {
      content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    };
  }
);

// 啟動伺服器
const transport = new StdioServerTransport();
await server.connect(transport);
```

### 基本結構（Python）

```python
# my-mcp-server/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("my-custom-server")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_database",
            description="查詢內部資料庫",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query"}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "query_database":
        # 你的實作邏輯
        result = execute_query(arguments["query"])
        return [TextContent(type="text", text=str(result))]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 註冊你的自訂伺服器

```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["./my-mcp-server/dist/index.js"]
    }
  }
}
```

## 實戰組合技

### GitHub + 資料庫 = 自動 Bug 修復

```
> 從 GitHub 取得所有標籤為 "bug" 的 open issues
> 根據 issue 描述找到相關程式碼
> 修復 bug 並建立 PR
> 在原 issue 加上 PR 連結
```

### Fetch + Filesystem = API 文件自動化

```
> 從 https://api.example.com/swagger.json 取得 API 規格
> 在 docs/ 目錄下產生完整的 API 文件
> 比對目前的程式碼確保文件是最新的
```

---

⬅️ [上一篇：Agent 模式與自動化](06-AGENT-MODE.md) | ➡️ [下一篇：進階工作流程](08-ADVANCED-WORKFLOWS.md)
