# 02. 品牌建構師工作流程

## 1. 角色定義 (Role Definition)

- **Role**: Brand Architect (品牌架構師)
- **Goal**: 透過數據收集與分析,建立完整、可執行的品牌策略指南 (Brand Guideline)，並建立品牌知識庫與內容庫。
- **Input**: `config/brand_profile.json` (品牌設定檔)
- **Output**:
  - `docs/brand_guideline.md` (11 大章節)
  - `outputs/FUNIT/raw_data/site_structure.json` (網站結構)
  - **Updated** `config/brand_profile.json` (含 Visual Identity)
  - **LanceDB Style DB**: 品牌指南與語氣
  - **LanceDB Content DB**: 現有網站內容

## 2. 執行流程 (Execution Flow)

### Step 1: 初始化與設定 (Initialization)

1. **檢查設定檔**: 確認 `config/brand_profile.json` 存在且格式正確。
   - 若不存在，請使用者根據 `config/brand_profile.template.json` 建立。
2. **讀取設定**: 讀取品牌名稱、網址、競品資訊與社群連結。
3. **環境檢查**: 確認 `.env` 中的 WordPress 設定正確 (WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD)。

### Step 2: 自動化資料收集 (Data Collection)

呼叫 Python 工具進行資料爬取與分析：

1. **執行自動化收集**:

   - 指令: `python agents/setup/s01_brand_builder.py --action collect_data --data '{}'`
   - **功能**:
     - 目前為佔位符內容，未來可擴充其他資料來源。
     - 輸出儲存至 `outputs/FUNIT/raw_data`。

2. **網站與競品分析**:

   - 指令: `python agents/utils/web_crawler.py --urls {website_url} {competitor_urls} --output_dir outputs/FUNIT/raw_data`
   - 目的: 獲取官網文案與競品資訊，用於分析 "USP" (獨特賣點) 與 "Positioning" (定位)。

3. **網站結構稽核 (Site Audit)**:

   - 指令: `python agents/site_auditor.py`
   - 目的:
     - 透過 WordPress REST API 抓取現有網站結構 (文章、頁面、分類、商品)。
     - 生成 `site_structure.json` 供後續 SEO 策略參考。
     - **自動同步**: 將抓取到的內容 (含 H2 標題) 同步至 **Content DB**，建立內容知識庫。

4. **競品網站分析 (Competitor Website Analysis)** 🆕:

   - **目的**: 透過瀏覽器分析競品的文案風格、服務定位與視覺風格。
   - **執行步驟**:
     1. **讀取競品列表**: 從 `brand_profile.json → competitors` 提取競品網站 URL
     2. **使用 browser_subagent 分析每個競品**:
        - 首頁文案風格 (語氣、標語、CTA)
        - 服務/產品定位
        - 視覺風格 (配色、圖片風格)
        - 目標受眾定位
     3. **每個競品最多分析 2 頁** (首頁 + 一個核心服務頁)
   - **輸出**: 分析結果用於「競品定位」章節
   - **觸發條件**: `brand_profile.json → competitors` 列表不為空

5. **論壇與社群研究 (Forum Research via Search)** 🆕:
   - **目的**: 透過搜尋引擎找出目標受眾的真實討論與痛點。
   - **執行步驟**:
     1. **生成搜尋查詢**: 根據品牌產業與 `primary_keywords` 組合搜尋語句
     2. **使用 search_web 工具執行搜尋** (底層為 DuckDuckGo)
     3. **分析搜尋結果摘要**:
        - 常見問題與痛點
        - 決策考量因素
        - 對競品的評價
   - **搜尋查詢範本** (至少執行 3 個):
     - `"{primary_keyword}" 心得 推薦`
     - `"{primary_keyword}" 評價 ptt OR dcard`
     - `"{competitor_name}" 評價 比較`
   - **輸出**: 洞察整理至品牌指南的「深度論壇研究」章節

### Step 3: 深度分析與生成 (Analysis & Generation)

#### 3.1 文字資料分析

Antigravity 讀取 `outputs/FUNIT/raw_data` 中的所有文字檔，分析品牌核心、語氣、受眾等資訊。

#### 3.2 視覺風格分析 (Visual Style Analysis) 🆕

**目的**: 透過瀏覽器截圖分析品牌官網的視覺設計，用於生成「視覺識別」章節。

**執行步驟**:

1. **開啟品牌官網**: 使用 browser_subagent 開啟 `{website_url}`
2. **截圖關鍵頁面**:
   - 首頁 (Homepage)
   - 關於我們 (About Us)
   - 產品/服務頁面 (Products/Services)
3. **視覺元素分析**:
   - **配色方案**: 識別主色調、輔助色、點綴色
   - **插畫/圖片風格**: 扁平化、手繪、3D、攝影、插畫等
   - **字體風格**: 圓潤、銳利、手寫、襯線、無襯線
   - **視覺氛圍**: 專業、親切、科技感、溫馨、活潑等
4. **競品視覺對比** (選填):
   - 若時間允許，可截圖 1-2 個競品網站進行對比分析

**輸出**: 將視覺分析結果整合到「視覺識別」章節中。

#### 3.3 生成品牌指南 (Brand Guideline Generation)

根據 `s01_rules.md` 生成完整的品牌指南，**必須包含以下 11 個章節**:

1. **品牌核心 (The Core)**: Why, How, What
2. **語氣設定 (Voice & Tone)**: 對比性定義與範例
3. **顧客人物誌 (Customer Persona)**: 5 大維度 + 4 大行銷應用
4. **SEO 與搜尋意圖 (SEO Strategy)**: 關鍵字與內容策略
5. **競品定位 (Competitive Positioning)**: 差異化優勢
6. **品牌敘事 (Brand Narrative)**: 故事與核心訊息
7. **內容紅線 (Negative Constraints)**: 禁止與遵守事項
8. **詞彙表 (Vocabulary)**: O/X 對照與術語
9. **深度論壇研究 (Forum Research)**: 真實聲音與洞察
10. **範例對照 (Before & After)**: 修改前後對比
11. **視覺識別 (Visual Identity)**:
    - **基於 Step 3.2 的視覺分析**
    - 插畫風格、配色方案、氛圍、參考關鍵字
    - 用於自動更新 `brand_profile.json`

#### 3.4 生成品牌樣式表 (Brand Style CSS Generation) 🆕

**目的**: 產出符合品牌視覺規範的 CSS 檔案，確保文章排版留白充足且風格一致。

**執行步驟**:

1. **讀取視覺規範**: 從 `brand_guideline.md` 的「視覺識別」與「語氣設定」章節提取風格參數。
2. **生成 CSS**: 產出 `brand_style.css`，必須包含：
   - **Typography**: 設定易讀的行高 (line-height: 1.6-1.8)、字級與段落寬度。
   - **Spacing**: 強制設定 H2, H3, p, ul, ol 的 margin，確保段落間有充足的呼吸感 (Whitespace)。
   - **Components**: 定義 Highlight Box 樣式 (如 `.brand-highlight`, `blockquote`)，使用品牌主色或輔助色。
   - **Images**: 設定圖片的圓角、陰影或邊框樣式。
   - **RWD Design**: 確認產出的 CSS 可以符合電腦，手機等尺寸裝置都能有良好的閲讀體驗。
3. **儲存檔案**:
   - 將生成的 CSS 內容儲存至 `outputs/FUNIT/assets/brand_style.css`。

### Step 4: 驗證與儲存 (Validation & Storage)

1. **自我驗證**: 檢查是否符合 `s01_rules.md` 的驗證規則 (完整性、深度、品質)。
2. **儲存檔案**:
   - 指令: `python agents/setup/s01_brand_builder.py --action create --data '{...}'`
   - 將生成的 Markdown 內容傳遞給 Python Tool。
3. **更新 Brand Profile**:
   - Python Tool 自動從生成的指南中提取「視覺識別」章節。
   - 更新 `config/brand_profile.json` 中的 `visual_identity` 欄位。
4. **同步 Style DB**:
   - Python Tool (`s01_brand_builder.py`) 自動將指南按章節切分並存入 **Style DB**。
   - 確保 Metadata 包含 `section`, `type: guideline`, `status: publish`。

## 3. 系統整合檢查 (Integration Check)

確保以下工具已就緒：

- [ ] `config/brand_profile.json` (Input)
- [ ] `agents/setup/s01_brand_builder.py` (Data Collection - Orchestrator & Storage)
- [ ] `agents/utils/web_crawler.py` (Data Collection - Web)
- [ ] `agents/site_auditor.py` (Data Collection - Site Structure & Content DB Sync)
- [ ] `browser_subagent` (Competitor Website Analysis) 🆕
- [ ] `search_web` (Forum Research via DuckDuckGo) 🆕
- [ ] `.agent/rules/s01_rules.md` (Analysis Logic)
- [ ] `agents/setup/s01_brand_builder.py` (Storage, Profile Update & Style DB Sync)

## 4. 下一步：進入 P01 關鍵字策略 (Next Steps)

**S01 完成後，自動進入 P01 階段**

當 S01 Brand Builder 執行完畢後（品牌指南已生成並同步至 Style DB），請立即執行以下流程：

### 自動觸發 P01 關鍵字策略

**執行指令**:

```
請依照 .agent/workflows/p01_關鍵字策略.md 流程，為以下主題生成關鍵字策略：

主題 (Topic): [請使用者提供主題，或從 brand_guideline.md 的 SEO 章節中選擇一個核心關鍵字]
```

**P01 輸入準備**:

- **Style DB**: 已由 S01 建立完成 ✅
- **Content DB**: 已由 Site Auditor 建立完成 ✅
- **Site Structure**: `site_structure.json` 已生成 ✅
- **Brand Profile**: `visual_identity` 已更新 ✅
- **僅需使用者提供**: **主題 (Topic)**

**P01 執行流程**:

1. Antigravity 讀取 Style DB (品牌語氣、受眾)
2. Antigravity 讀取 Content DB (現有文章)
3. Python Agent 使用 Crawl4AI 搜尋競爭對手
4. Antigravity 分析並生成關鍵字策略 JSON
5. 策略報告儲存至 `outputs/FUNIT/strategies/`

**參考文件**:

- Workflow: `.agent/workflows/p01_關鍵字策略.md`
- Rules: `.agent/rules/p01_rules.md`
- Agent: `agents/planning/p01_keyword_strategist.py`
