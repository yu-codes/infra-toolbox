# Skills

Claude Agent Skills 參考實現與規範。

本目錄包含 Claude Skills 系統的範例、規範及最佳實踐。

## 目錄結構

- [./skills](./skills) - Skill 範例 (創意設計、開發技術、企業通信、文件處理)
- [./spec](./spec) - Agent Skills 規範
- [./template](./template) - 基本 Skill 範本

## 快速開始

### 建立新 Skill

Skill 是包含 `SKILL.md` 文件的資料夾，最小結構如下：

```
my-skill/
└── SKILL.md
```

### SKILL.md 格式

```yaml
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Add your instructions here that Claude will follow when this skill is active]

## Examples
- Example usage 1
- Example usage 2

## Guidelines
- Guideline 1
- Guideline 2
```

### 前置資訊

- `name`: 唯一識別符 (小寫，使用連字符代替空格)
- `description`: 完整描述 (說明用途及使用情境)

## 資源

- [Agent Skills 規範](http://agentskills.io)
- [建立自訂 Skills 指南](https://support.claude.com/en/articles/12512198-creating-custom-skills)
- [在 Claude 中使用 Skills](https://support.claude.com/en/articles/12512180-using-skills-in-claude)

## Claude.ai

These example skills are all already available to paid plans in Claude.ai. 

To use any skill from this repository or upload custom skills, follow the instructions in [Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude#h_a4222fa77b).

## Claude API

You can use Anthropic's pre-built skills, and upload custom skills, via the Claude API. See the [Skills API Quickstart](https://docs.claude.com/en/api/skills-guide#creating-a-skill) for more.

# Creating a Basic Skill

Skills are simple to create - just a folder with a `SKILL.md` file containing YAML frontmatter and instructions. You can use the **template-skill** in this repository as a starting point:

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Add your instructions here that Claude will follow when this skill is active]

## Examples
- Example usage 1
- Example usage 2

## Guidelines
- Guideline 1
- Guideline 2
```

The frontmatter requires only two fields:
- `name` - A unique identifier for your skill (lowercase, hyphens for spaces)
- `description` - A complete description of what the skill does and when to use it

The markdown content below contains the instructions, examples, and guidelines that Claude will follow. For more details, see [How to create custom skills](https://support.claude.com/en/articles/12512198-creating-custom-skills).

# Partner Skills

Skills are a great way to teach Claude how to get better at using specific pieces of software. As we see awesome example skills from partners, we may highlight some of them here:

- **Notion** - [Notion Skills for Claude](https://www.notion.so/notiondevs/Notion-Skills-for-Claude-28da4445d27180c7af1df7d8615723d0)
