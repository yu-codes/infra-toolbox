# Claude Design：用 AI 建立前端介面

Claude Design 是 Anthropic 官方的 `frontend-design` skill，讓 Claude 能生成高品質、有設計感的前端介面。它不是簡單的 UI 模板生成器 — 而是能產出具有獨特美學風格、可生產使用的前端程式碼。

---

## 什麼是 Claude Design？

Claude Design（正式名稱：`frontend-design` skill）教導 Claude：
- 在寫程式碼前先進行設計思考
- 產出視覺獨特、避免「AI 通用風格」的介面
- 生成可直接使用的 HTML/CSS/JS、React 或 Vue 程式碼
- 注重字型、色彩、動畫、空間構成等設計細節

---

## 安裝方式

### 方式一：透過 Plugin Marketplace 安裝（推薦）

```bash
# 在 Claude Code 中執行
/plugin marketplace add anthropics/skills

# 安裝 example-skills plugin（包含 frontend-design）
/plugin install example-skills@anthropic-agent-skills
```

安裝後，直接在對話中提到設計相關需求即可自動使用。

### 方式二：手動安裝 Skill

1. 建立 skill 目錄：

```bash
mkdir -p ~/.claude/skills/frontend-design
```

2. 建立 `~/.claude/skills/frontend-design/SKILL.md`：

```markdown
---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications.
---

# Frontend Design Skill

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian
- **Constraints**: Technical requirements (framework, performance, accessibility)
- **Differentiation**: What makes this UNFORGETTABLE?

## Implementation

Generate working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Aesthetics Guidelines

- **Typography**: Choose distinctive fonts, avoid generic ones (Inter, Arial, Roboto)
- **Color & Theme**: Commit to a cohesive palette. Dominant colors with sharp accents
- **Motion**: CSS animations, micro-interactions, scroll-triggered effects
- **Spatial Composition**: Unexpected layouts, asymmetry, overlap, generous negative space
- **Backgrounds**: Gradient meshes, noise textures, geometric patterns, layered transparencies

## Anti-patterns (NEVER do these)

- Generic AI aesthetics (purple gradients on white)
- Overused font families (Inter, Roboto, system fonts)
- Predictable layouts and cookie-cutter patterns
- Same design repeated across generations
```

### 方式三：專案級安裝（Vue 專用版）

在你的專案中建立 `.claude/skills/frontend-design/SKILL.md`，加入 Vue 特化的指引：

```markdown
---
name: frontend-design
description: Create distinctive Vue 3 components and pages with high design quality.
---

# Frontend Design (Vue 3)

## Framework Requirements
- Use Vue 3 with `<script setup lang="ts">`
- Prefer scoped styles or Tailwind CSS
- Use Vue transition components for animations
- Import icons from a consistent library (heroicons, lucide)

## Design Process
1. Identify the component's purpose and audience
2. Choose a bold aesthetic direction
3. Implement with Vue SFC structure
4. Add transitions and micro-interactions
5. Ensure responsive design

## Template Structure
Generate components as single Vue SFC files:
- `<script setup>` with TypeScript
- `<template>` with semantic HTML
- `<style scoped>` with CSS variables for theming
```

---

## 使用方式

### 基本用法

安裝 skill 後，直接用自然語言描述你想要的設計：

```
幫我建立一個深色主題的 Dashboard 頁面，包含左側導航欄和主要內容區域。
風格要現代、科技感，使用漸層和微妙的動畫效果。
```

```
建立一個 Landing Page，要有 hero section、feature cards 和 pricing table。
風格走極簡主義路線，大量留白，精緻的字型搭配。
```

```
設計一個 Login/Register 表單組件，要有視覺衝擊力，不要普通的白底表單。
```

### 進階用法：指定美學方向

你可以在 prompt 中明確指定設計風格：

```
用 Art Deco 幾何風格設計一個 pricing page。
金色配深藍/黑色背景，裝飾性邊框，幾何圖案。
字型用 Playfair Display + Montserrat。
```

```
設計一個 brutalist 風格的 portfolio 頁面。
Raw typography，不規則佈局，高對比，像是用打字機印出來的感覺。
```

```
建立一個 glassmorphism 風格的天氣 widget，
毛玻璃效果、柔和陰影、半透明層疊。
```

### 與 Vue 搭配使用

```
用 Vue 3 <script setup> 建立一個 kanban board component。
要有拖拽動畫、card 展開細節、直覺的使用者體驗。
設計風格：soft pastel + rounded corners + subtle shadows。
```

---

## 最佳實踐

### 1. 提供明確的設計約束

```
❌ "建立一個 button component"
✅ "建立一個 CTA button，要在深色背景上非常顯眼，有 hover 時的彈跳動畫，
    寬度自適應，支援 loading 狀態。風格偏向 luxury/refined。"
```

### 2. 一次聚焦一個組件

不要一次要求整個頁面的所有組件。拆分請求，逐步建立：
1. 先做 Layout / Navigation
2. 再做主要內容區
3. 最後做細節和互動動畫

### 3. 迭代改善

```
第一次：「建立基本的 card component，風格走 editorial/magazine」
第二次：「加入 hover 時的 parallax 效果和圖片放大動畫」
第三次：「調整色彩，改用更大膽的配色，增加 grain texture 背景」
```

### 4. 參考現有設計系統

```
參考 Linear.app 的設計風格，建立一個 issue tracker 的 list view。
保持那種乾淨但有力的感覺，深色主題，精確的間距。
```

---

## 常見應用場景

| 場景 | 提示範例 |
|------|---------|
| Landing Page | "Build a SaaS landing page, dark theme, gradient accents" |
| Dashboard | "Create an analytics dashboard with charts, minimal and clean" |
| Form | "Design a multi-step onboarding form with progress animation" |
| Card Component | "Make a product card with image, pricing, and hover effects" |
| Navigation | "Build a responsive sidebar nav with collapse animation" |
| Modal/Dialog | "Design a confirmation dialog with spring animation" |
| Data Table | "Create a sortable data table with row expansion" |

---

## 停用 / 移除

```bash
# 如果用 plugin 安裝
/plugin list
# 找到 example-skills@anthropic-agent-skills，然後
/plugin uninstall example-skills@anthropic-agent-skills

# 如果手動安裝
rm -rf ~/.claude/skills/frontend-design
# 或
rm -rf .claude/skills/frontend-design
```

---

## 注意事項

- Claude Design 生成的是**靜態的前端程式碼**，不含後端邏輯
- 生成的 HTML 可以直接在瀏覽器開啟預覽
- Vue / React 組件需要在對應的專案環境中使用
- 字型引用可能需要確認授權（Google Fonts 通常免費）
- 動畫效果在低階設備上可能需要降級處理
