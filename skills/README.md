# Skills

AI Agent Skills 參考實現與規範 - 適用於任何 AI 模型與開發工具。

本目錄包含 Agent Skills 系統的範例、規範及最佳實踐。這些 Skills 設計為通用格式，可在任何支援長上下文或系統提示的 AI 工具中使用。

## 支援的 AI 工具與模型

Skills 可以在以下環境中使用：

| 工具/平台 | 使用方式 |
|----------|---------|
| Claude.ai | 上傳 SKILL.md 到對話或使用 Projects |
| ChatGPT | 上傳 SKILL.md 或貼入 Custom Instructions |
| GitHub Copilot | 放入 `.github/copilot-instructions.md` |
| Cursor | 放入 `.cursorrules` 或 `.cursor/rules/` |
| Windsurf | 放入 `.windsurfrules` 或 Project Rules |
| Cline | 放入 `.clinerules` 或自訂指令 |
| Aider | 放入 `.aider.conf.yml` 的 read 設定 |
| Continue.dev | 放入 `.continue/rules/` |
| 其他 IDE AI 插件 | 作為系統提示或上下文使用 |

## 目錄結構

```
skills/
├── skills/           # Skill 範例
│   ├── algorithmic-art/    # 演算法藝術生成
│   ├── brand-guidelines/   # 品牌指南設計
│   ├── canvas-design/      # 視覺畫布設計
│   ├── doc-coauthoring/    # 文件協作
│   ├── docx/               # Word 文件處理
│   ├── frontend-design/    # 前端設計
│   ├── internal-comms/     # 企業內部通訊
│   ├── mcp-builder/        # MCP 伺服器建構
│   ├── pdf/                # PDF 處理
│   ├── pptx/               # PowerPoint 處理
│   ├── skill-creator/      # Skill 建立輔助
│   ├── slack-gif-creator/  # Slack GIF 製作
│   ├── theme-factory/      # 主題工廠
│   ├── web-artifacts-builder/  # Web 元件建構
│   ├── webapp-testing/     # Web 應用測試
│   └── xlsx/               # Excel 處理
├── spec/             # Agent Skills 規範
├── template/         # 基本 Skill 範本
└── README.md
```

---

## 開發新 Skill 流程

### 1. 建立 Skill 資料夾

```bash
mkdir -p skills/skills/my-new-skill
```

### 2. 建立 SKILL.md

最小結構：

```
my-new-skill/
└── SKILL.md
```

完整結構：

```
my-new-skill/
├── SKILL.md          # 主要指令文件 (必要)
├── LICENSE.txt       # 授權聲明 (建議)
├── examples/         # 範例檔案 (可選)
├── templates/        # 模板檔案 (可選)
├── scripts/          # 輔助腳本 (可選)
└── reference/        # 參考文件 (可選)
```

### 3. SKILL.md 格式

```yaml
---
name: my-skill-name
description: 清楚描述這個 Skill 做什麼以及何時使用它
version: 1.0.0
author: Your Name
license: MIT
tags:
  - category1
  - category2
---

# My Skill Name

## 概述

[簡短描述 Skill 的用途和目標]

## 使用指南

### 何時使用此 Skill

- 情境 1
- 情境 2

### 核心功能

1. 功能 1
2. 功能 2

## 指令

[詳細的指令內容，AI 將根據這些指令執行任務]

### 步驟一

[指令內容]

### 步驟二

[指令內容]

## 範例

### 範例 1: [標題]

輸入：
```
用戶請求範例
```

輸出：
```
預期輸出範例
```

## 注意事項

- 注意事項 1
- 注意事項 2

## 參考資源

- [資源 1](連結)
- [資源 2](連結)
```

### 4. 前置資訊 (Frontmatter)

| 欄位 | 必要 | 說明 |
|------|------|------|
| `name` | ✓ | 唯一識別符 (小寫，使用連字符) |
| `description` | ✓ | 完整描述 (說明用途及使用情境) |
| `version` | 建議 | 版本號 (遵循 semver) |
| `author` | 建議 | 作者名稱 |
| `license` | 建議 | 授權類型 |
| `tags` | 可選 | 分類標籤 |

### 5. 撰寫最佳實踐

1. **清晰具體**: 指令要明確，避免模糊描述
2. **結構化**: 使用標題、列表、程式碼區塊組織內容
3. **包含範例**: 提供輸入輸出範例
4. **設定邊界**: 明確說明 Skill 的能力範圍
5. **考慮上下文**: 思考 AI 需要什麼資訊才能執行
6. **測試驗證**: 在多個 AI 工具中測試 Skill 效果

---

## 使用 Skill 方法

### 方法一：直接上傳到 AI 對話

適用於 Claude.ai、ChatGPT 等支援檔案上傳的平台：

1. 開始新對話
2. 上傳 `SKILL.md` 檔案
3. 開始與 AI 互動

### 方法二：IDE AI 整合

#### GitHub Copilot

```bash
# 將 Skill 內容複製到專案根目錄
cp skills/skills/my-skill/SKILL.md .github/copilot-instructions.md
```

#### Cursor

```bash
# 方法 1: 單一規則檔
cp skills/skills/my-skill/SKILL.md .cursorrules

# 方法 2: 規則目錄 (支援多個 Skill)
mkdir -p .cursor/rules
cp skills/skills/my-skill/SKILL.md .cursor/rules/my-skill.md
```

#### Windsurf

```bash
# 方法 1: 單一規則檔
cp skills/skills/my-skill/SKILL.md .windsurfrules

# 方法 2: 專案規則 (在 Windsurf 設定中配置)
```

#### Cline

```bash
# 複製到 .clinerules
cp skills/skills/my-skill/SKILL.md .clinerules
```

#### Continue.dev

```bash
# 複製到 rules 目錄
mkdir -p .continue/rules
cp skills/skills/my-skill/SKILL.md .continue/rules/my-skill.md
```

#### Aider

```yaml
# 在 .aider.conf.yml 中設定
read:
  - skills/skills/my-skill/SKILL.md
```

### 方法三：系統提示整合

對於 API 呼叫或自訂工具，將 Skill 內容作為系統提示：

```python
import anthropic

# 讀取 Skill 內容
with open("skills/skills/my-skill/SKILL.md", "r") as f:
    skill_content = f.read()

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system=skill_content,
    messages=[
        {"role": "user", "content": "執行任務..."}
    ]
)
```

### 方法四：多 Skill 組合

可以組合多個 Skill 使用：

```bash
# 建立組合 Skill 檔案
cat skills/skills/skill-a/SKILL.md > combined-skills.md
echo "\n---\n" >> combined-skills.md
cat skills/skills/skill-b/SKILL.md >> combined-skills.md
```

---

## 通用配置檔

為了方便在不同 AI 工具中使用，本目錄提供通用配置範本：

### `.ai-rules` (通用格式)

```yaml
# .ai-rules - 通用 AI 規則配置
# 可被轉換為各 IDE 專用格式

skills:
  - path: skills/skills/my-skill/SKILL.md
    enabled: true
  - path: skills/skills/another-skill/SKILL.md
    enabled: true

global_rules: |
  - 使用繁體中文回應
  - 程式碼註解使用英文
  - 遵循專案程式碼風格
```

---

## 資源

- [Agent Skills 規範](https://agentskills.io/specification)
- [建立自訂 Skills 指南](https://support.claude.com/en/articles/12512198-creating-custom-skills)
- [在 Claude 中使用 Skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude)

## Claude.ai

These example skills are all already available to paid plans in Claude.ai. 

To use any skill from this repository or upload custom skills, follow the instructions in [Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude#h_a4222fa77b).

## Claude API

You can use Anthropic's pre-built skills, and upload custom skills, via the Claude API. See the [Skills API Quickstart](https://docs.claude.com/en/api/skills-guide#creating-a-skill) for more.

## Partner Skills

Skills are a great way to teach Claude how to get better at using specific pieces of software. As we see awesome example skills from partners, we may highlight some of them here:

- **Notion** - [Notion Skills for Claude](https://www.notion.so/notiondevs/Notion-Skills-for-Claude-28da4445d27180c7af1df7d8615723d0)
