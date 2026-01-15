---
name: 專案概覽技能
description: 執行 專案概覽技能 工作流程；當需要時使用。
---

> **來源**: 本技能源自 `README.md`。

# 🎭 AI 自動化內容團隊 - 員工名冊 (Agent Roster)

本目錄存放所有 Agent Skills 的定義與規範。

## 📋 技能目錄

| 編號 | 職稱 (Role) | 職責 (Responsibility) | 適用情境 (Trigger) |
| :--- | :--- | :--- | :--- |
| **00-09** | **管理與核心 (The Brain)** | | |
| 00 | 專案經理 (Project Manager) | 協調多步驟內容流程與跨技能串接 | 需要規劃流程、拆解任務或整合多個技能 |
| 01 | 自動化開發工頭 (Task Master) | 將自然語言需求轉換為 Ralph Loop 自動化開發指令 | 需要開發新功能或執行自動化指令 |
| 02 | 品牌建構師 (Brand Architect) | 建立或更新品牌指南、語氣與視覺識別 | 初始化品牌設定或更新品牌規範 |
| 03 | 企業知識庫 (Knowledge Base) | 管理 Fact Memory（存入/查詢/匯入 PDF） | 維護事實記憶或導入官方文件 |
| 04 | 系統醫生 (System Doctor) | 檢查系統環境、依賴、API 金鑰與連線 | 環境檢查、Debug 或初始化失敗 |
| **10-19** | **策略規劃 (Strategy)** | | |
| 10 | 關鍵字策略師 (Keyword Strategist) | 關鍵字策略分析、主題集群與重複性檢查 | 進行 SEO 主題研究與關鍵字規劃 |
| 11 | 內容企劃師 (Content Planner) | 生成內容 Brief/大綱與搜尋意圖研究 | 產出文章結構、大綱或 Brief |
| **20-29** | **內容生產 (Production)** | | |
| 20 | 內容撰稿人 (Content Writer) | 依 Brief 撰寫文章草稿並符合品牌語氣 | 撰寫內容草稿 |
| 21 | SEO優化師 (SEO Specialist) | 優化文章 SEO 元素、Meta/Schema/FAQ | 進行 SEO 優化與檢查 |
| 22 | 資訊查核員 (Fact Checker) | 查核文章中的事實與數據並修正錯誤 | 事實查核或確認內容正確性 |
| 23 | 視覺總監 (Visual Director) | 規劃文章配圖、生成圖片描述並替換連結 | 配圖規劃與圖片策略執行 |
| 24 | 內部連結專家 (Link Builder) | 在文章中插入服務或產品推薦區塊 | 需要服務推薦或建立內部連結 |
| 25 | CTA管理員 (CTA Manager) | 維護 CTA 連結與 UTM 規範並進行批次更新 | 統一或更新 CTA 連結 |
| **30-39** | **維運與工具 (Ops & Tools)** | | |
| 30 | 文章發布員 (Publisher) | 將最終文章發布或更新至 WordPress | 發布文章或更新線上內容 |
| 31 | 舊文翻新工程師 (Content Refactorer) | 自動化舊文重構流程（抓取、生成、重寫、發布） | 重構已發布的舊文章 |
| 32 | 文章維修員 (Content Corrector) | 修正已發布文章的事實錯誤並更新同步 | 修正線上文章錯誤資訊 |
| 33 | 資料同步員 (Data Syncer) | 同步 WordPress 全站資料到本地與向量資料庫 | 全站資料掃描或同步 |
| 34 | 風格學習師 (Style Gardener) | 從人類修訂中學習並更新 Style Memory | 進行風格學習或更新語氣規則 |
| 35 | 技能訓練師 (Skill Builder) | 建立或更新 Gemini Skills 的規範與流程 | 新增 Skill、整理文件或打包技能 |
| **99** | **指南 (Guide)** | | |
| 99 | 系統使用指南 (User Guide) | 引導使用者了解系統功能與工作流程 | 查詢功能、快速開始或操作指引 |

## 🛠️ 技能使用說明 (Skill Usage Guide)

本系統使用 Gemini CLI Skills + Antigravity 來擴充 AI Agent 的能力。Skills 是按需載入的專業知識模組。

### 1. 技能存放位置
Skills 來自三個主要位置，Gemini 會自動偵測：
*   **專案技能 (Project Skills)**： `.gemini/skills/` (本專案專用，隨專案版本控制)
*   **使用者技能 (User Skills)**： `~/.gemini/skills/` (跨專案通用)
*   **擴充技能 (Extension Skills)**： 來自安裝的 Extension

### 2. 在對話中使用 (Interactive Session)
在與 Gemini 的對話中，可以使用 `/skills` 指令來管理：

*   `/skills list`： 列出目前可用的所有技能與狀態。
*   `/skills reload`： 重新載入所有技能 (當你新增或修改 Skill 檔案後使用)。
*   `/skills disable <name>`： 暫時停用某個技能。
*   `/skills enable <name>`： 重新啟用技能。

### 3. 在終端機管理 (Terminal)
在終端機 (Terminal) 中，可以使用 `gemini skills` 指令：

```bash
# 列出所有已偵測到的技能
gemini skills list

# 安裝技能 (預設安裝到使用者層級 ~/.gemini/skills)
gemini skills install https://github.com/user/repo.git

# 安裝到本專案 (.gemini/skills)
gemini skills install /path/to/skill --scope workspace
```

### 4. 建立新技能 (Creating a Skill)
要建立一個新技能，只需建立一個包含 `SKILL.md` 的目錄：
1.  **建立目錄**： `mkdir .gemini/skills/my-new-skill`
2.  **定義技能**： 在該目錄下建立 `SKILL.md`，並定義 YAML metadata 與 Markdown 指令。

### 5. Google Antigravity (Natural Language)
Google Antigravity 讓你可以直接使用自然語言來呼叫 Agent，無需任何預先載入或複雜指令。

你只需要在對話中直接說出你的需求，系統會自動識別並啟動相關的 Agent Skill。

**範例**：
> User: "幫我規劃關於 'AI 工具' 的關鍵字策略"
>
> System: (自動啟動 **10. 關鍵字策略師 (Keyword Strategist)** 來處理請求)


