---

name: article-corrector
description: 修正已發布文章的事實錯誤並更新 WordPress/Fact Memory；當需要更正錯誤資訊時使用。

---

> **來源**: 本技能源自 `c06_文章修正.md`。

# C06 現有文章修正工作流程

## 目的
當發現已發布文章中有事實錯誤時，提供標準化的修正流程。適用於：
- 政策變更（如各國簽證規則調整）
- 過時資訊（如費用、日期）
- 事實查核發現的錯誤

---

## 觸發時機
- 執行 `/c02a_事實查核` 後發現錯誤
- 用戶手動回報錯誤
- 政策更新公告

---

## 執行流程

### Step 1: 識別錯誤內容

1. **取得文章修訂差異**：
   ```bash
   source venv/bin/activate
   python3 agents/monitoring/style_gardener.py harvest --post-id <POST_ID> --count 5 --json
   ```

2. **或直接從 WordPress 讀取**：
   ```python
   from utils.wordpress_client import wp_client
   post = wp_client.get_post(post_id)
   ```

### Step 2: 查核與驗證

1. **網路搜尋驗證**：使用 `search_web` 工具搜尋官方來源
2. **Fact Memory 比對**：查詢向量資料庫是否已有正確資訊
   ```python
   from utils.vector_db_manager import vector_db
   results = vector_db.query_facts(query_text="<相關關鍵字>", n_results=5)
   ```

### Step 3: 更新文章

#### 方法 A: WordPress API (優先)
```python
from utils.wordpress_client import wp_client

wp_client.update_post(
    post_id=<POST_ID>,
    content="<更新後的 HTML 內容>"
)
```

#### 方法 B: 瀏覽器自動化 (API 被封鎖時)
```
使用 browser_subagent 登入 WordPress 後台進行編輯
```

#### 方法 C: 手動更新 (最後手段)
1. 產出手動更新指引 Markdown
2. 列出具體的「找到→替換為」文字
3. 用戶自行登入後台修改

#### 目錄 (TOC) 處理規則 🆕
由於插件 Shortcode (如 `[ez-toc]`) 可能導致依賴問題，請遵循以下規則：
1. **檢查**: 確認文章是否已有目錄。
2. **生成**: 若無目錄，**必須**生成「純 HTML」目錄 (HTML Anchor List)。
   - **格式**: 使用標準 `<ul>` 與 `<li>` 標籤，配合內部連結錨點 (Anchor Links)。
     ```html
     <div class="toc-container">
       <h3>目錄</h3>
       <ul>
         <li><a href="#section-1">標題一</a></li>
         <li><a href="#section-2">標題二</a></li>
       </ul>
     </div>
     ```
   - **位置**: 插入在第一個 H2 標題之前。
3. **錨點設定**: 必須確保對應的 H2/H3 標籤具有 `id` 屬性 (如 `<h2 id="section-1">`) 或 Gutenberg Block 的 `anchor` 屬性。
4. **禁止**: **嚴禁**使用 `[ez-toc]`、`[toc]` 等依賴特定外掛的 Shortcode，以免插件失效時顯示未解析代碼。

### Step 4: 存入 Fact Memory

**重要**: 所有修正後的正確資訊都應存入 Fact Memory，避免未來再犯。

```python
from utils.fact_memory_manager import FactMemoryManager

fm = FactMemoryManager()
fm.add_fact(
    context="<事實背景描述>",
    claim="<錯誤的聲明>",
    correction="<正確的資訊>",
    source="<來源 URL 或名稱>"
)
```

### Step 5: 驗證與記錄

1. 確認 WordPress 文章已更新
2. 確認 Fact Memory 已存入
3. 產出修正報告（可選）

---

## 常見錯誤類型與處理

### 簽證與入境規範
- **來源**: 各國外交部/移民局官網
- **注意**: 規定可能隨時變更（如 免簽天數、疫苗要求）

### 門票費用與交通規則
- **來源**: 官方網站、JR/鐵路公司官網
- **注意**: 價格可能按匯率或旺季調整

### 飯店入住標準
- **來源**: 訂房網、飯店官網
- **注意**: 入住時間與取消政策可能變動

---

## 相關規則
- `c02a_rules.md` (事實查核判定標準)

---

## 限制與注意事項

1. **WordPress API 封鎖**: 部分網站設有 WAF 防火牆，可能封鎖 API 呼叫 (403/429)
2. **瀏覽器 Rate Limit**: browser_subagent 可能遇到 429 錯誤
3. **venv 環境**: 執行腳本時需先 `source venv/bin/activate`

