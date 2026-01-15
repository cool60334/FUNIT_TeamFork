---
name: system-doctor
description: 檢查系統環境、依賴、API 金鑰與 WordPress/LanceDB 連線；當需要環境檢查或初始化失敗時使用。
---

> **來源**: 本技能源自 `00_環境檢查.md`。

# 00 環境檢查 - 環境部署檢查

> **⚠️ 重要**: 這是系統使用的**第一步**，必須在執行任何其他 workflow 前完成。

## 角色定義

您是系統環境部署工程師，負責確保使用者的本地環境已正確設定，所有必要條件都已滿足。

## 檢查項目

### 0. 專案掃描 (Project Scanning) 🆕

- 掃描專案根目錄是否存在虛擬環境資料夾 (`venv/`, `.venv/`)
- **Action**: 若發現虛擬環境但當前未啟用，必須提示使用者並且啟動這個虛擬環境，或者是安裝 Python 執行。

### 1. Python 環境

- 檢查 Python 版本（需 3.10+，建議 3.11+）
- 確認 pip 可用
- **檢查是否在虛擬環境中** (Virtual Environment)
  - 檢查 `VIRTUAL_ENV` 環境變數
  - **重要**: 避免使用系統全域 Python，以防止 PEP 668 錯誤（externally-managed-environment）。

### 2. 系統依賴檢查 (System Dependencies)

#### BeautifulSoup (HTML Parsing)

- **Purpose**: Parse and clean legacy WordPress HTML content.
- **Check**: `pip show beautifulsoup4`
- **Install**: `pip install beautifulsoup4`

#### lxml (HTML Parser Backend)

- **Purpose**: High-performance HTML parser for BeautifulSoup.
- **Check**: `pip show lxml`
- **Install**: `pip install lxml` (Optional, falls back to Python's html.parser)

- [ ] **FFmpeg**: 必須安裝 (用於音訊轉檔)
  - 檢查指令: `ffmpeg -version`
  - 若未安裝:
    - macOS: `brew install ffmpeg`
    - Windows: 下載並設定 PATH
    - Linux: `sudo apt install ffmpeg`

### 3. Python 套件檢查 (Python Packages)

檢查 `requirements.txt` 中的套件是否已安裝，並分為「必要」與「選用」：

**必要套件（缺少會 error）**:

- `pydantic`, `pydantic-settings`, `python-dotenv`
- `lancedb`, `pyarrow`, `google-generativeai`, `sentence-transformers`
- `requests`, `beautifulsoup4`

**選用套件（缺少會 warning）**:

- `openai-whisper`, `crawl4ai`, `yt-dlp`, `ddgs`
- `woocommerce`, `pdfplumber`, `google-genai`
- `fastapi`, `uvicorn`

### 4. 環境變數設定

驗證 `.env` 檔案是否存在並包含：

**必要**:

- `WP_SITE_URL`
- `WP_USERNAME`
- `WP_APP_PASSWORD`
- `GEMINI_API_KEY`

**建議**:

- `HUGGINGFACE_API_KEY` (用於 EmbeddingGemma-300m)

**選用**:

- `LANCEDB_PATH`
- `WOOCOMMERCE_CONSUMER_KEY`
- `WOOCOMMERCE_CONSUMER_SECRET`

### 4. 資料夾結構

確認以下資料夾存在且可寫入：

- `./data/lancedb/`
- `./outputs/FUNIT/收集到的資料/`
- `./outputs/FUNIT/briefs/`
- `./outputs/FUNIT/drafts/`
- `./outputs/FUNIT/optimized/`
- `./outputs/FUNIT/final/`
- `./outputs/FUNIT/images/`
- `./outputs/FUNIT/reports/`
- `./outputs/FUNIT/strategies/`

### 5. 外部連線測試

> **⚠️ 重要**: 所有 WordPress API 測試**必須**使用 `utils/wordpress_client.py` 的 `wp_client`，禁止使用 `requests.get()` 直接發送請求。否則會因缺少 User-Agent Header 而被伺服器阻擋 (403 Forbidden)。

- **WordPress API**: 測試是否能成功連線

  ```python
  # ✅ 正確做法：使用 wp_client
  from utils.wordpress_client import wp_client
  posts, total_pages = wp_client.get_posts_batch(page=1, per_page=1)

  # ❌ 禁止：直接使用 requests
  # requests.get(f"{url}/wp-json/wp/v2/posts")  # 會被 403 阻擋！
  ```

- **Gemini API**: 驗證 API Key 是否有效
- **WooCommerce API**: （如有設定）測試連線

### 6. LanceDB 測試

- 連接資料庫
- 測試寫入與讀取
- 清除測試資料

## 執行流程

### Python Tool 執行任務

```bash
# 1. 若存在 venv：source venv/bin/activate
# 2. 執行檢查（沒有 venv 時，改用系統 Python）
PYTHONPATH=. python3 agents/core/tech_agent.py --full-check
```

Python Tool 將執行所有檢查並生成報告：

```json
{
  "status": "success|warning|error",
  "checks": {
    "python_version": {
      "status": "ok|error",
      "version": "3.11.5",
      "virtual_env": false,
      "message": "Python version is compatible"
    },
    "packages": {
      "status": "ok|warning|error",
      "installed": ["pydantic", "lancedb", "..."],
      "missing_critical": [],
      "missing_optional": ["woocommerce"],
      "message": "Missing optional packages: woocommerce"
    },
    "env_file": {
      "status": "ok|warning|error",
      "found": true,
      "missing_variables": ["HUGGINGFACE_API_KEY"],
      "missing_optional": ["LANCEDB_PATH"],
      "message": "Missing recommended vars: HUGGINGFACE_API_KEY"
    },
    "directories": {
      "status": "ok|warning",
      "existing": ["./data/lancedb", "..."],
      "missing": [],
      "not_writable": [],
      "message": "All required directories present and writable"
    },
    "ffmpeg": {
      "status": "ok|error",
      "message": "FFmpeg detected"
    },
    "wordpress_connection": {
      "status": "ok|error|skipped",
      "response_time_ms": 234,
      "message": "WordPress API accessible"
    },
    "woocommerce_connection": {
      "status": "ok|error|skipped",
      "message": "WooCommerce keys not configured"
    },
    "gemini_api": {
      "status": "ok|error|skipped",
      "response_time_ms": 120,
      "message": "Gemini API accessible"
    },
    "lancedb": {
      "status": "ok|error",
      "db_path": "./data/lancedb",
      "writable": true,
      "message": "LanceDB accessible"
    }
  },
  "summary": {
    "total_checks": 9,
    "passed": 6,
    "warnings": 2,
    "skipped": 1,
    "errors": 0
  },
  "recommendations": [
    "安裝缺少的套件: pip install -r requirements.txt",
    "補齊建議環境變數（如 HUGGINGFACE_API_KEY）"
  ],
  "next_steps": [
    "環境基本可用，但有警告項目可優先修正",
    "修正後可再次執行 /00_環境檢查"
  ]
}
```

## Antigravity 職責

### 1. 解讀檢查報告

根據 Python Tool 回傳的報告，向使用者說明：

- ✅ **全部通過**: 「太好了！您的環境已經完全設定好。接下來可以執行 /s01\_品牌建構師 建立品牌指南。」

- ⚠️ **有警告**: 「您的環境基本正常，但有 {X} 個警告需要注意：{列出警告項目}。您可以選擇現在修正，或稍後處理。」

- ❌ **有錯誤**: 「抱歉，您的環境設定有 {X} 個錯誤需要修正：{列出錯誤項目}。請依照建議修正後，再次執行 /00\_環境檢查。」

### 2. 提供修正建議

針對常見問題提供詳細解決方案：

**缺少套件**：
請使用專案的 `requirements.txt` 安裝：

```bash
pip install -r requirements.txt
```

**缺少套件或 PEP 668 錯誤**：
macOS 禁止直接使用 pip 安裝全域套件，請建立虛擬環境：

```bash
# 1. 建立虛擬環境
python3 -m venv venv

# 2. 啟動虛擬環境
source venv/bin/activate

# 3. 安裝套件
pip install -r requirements.txt
```

**缺少 .env 檔案**：

```
請建立 .env 檔案，可參考 .env.example 範本。
您可以說「幫我建立 .env 範本」，我會為您生成一個。
```

**WordPress 連線失敗**：

```
請檢查：
1. WP_SITE_URL 是否正確（如 https://example.com）
2. Application Password 是否有效
3. WordPress 網站是否開啟 REST API
4. 網路連線是否正常
```

**LanceDB 無法寫入**：

```
請檢查資料夾權限：
chmod -R 755 ./data/lancedb/
```

### 3. 引導使用者修正

如果有問題，引導使用者逐步修正：

```
您想要我幫您：
A. 協助安裝缺少的套件
B. 生成 .env 檔案範本
C. 測試 WordPress 連線
D. 跳過（稍後手動處理）

請選擇 A/B/C/D
```

## 輸出格式

### 成功輸出

當所有檢查通過時：

```markdown
✅ **環境檢查完成！**

系統已就緒，所有檢查通過：

- Python 3.11.x ✓
- 套件完整 ✓
- 環境變數設定正確 ✓
- WordPress 連線正常 ✓
- LanceDB 可用 ✓
- FFmpeg 可用 ✓

**下一步**：執行 `/s01_品牌建構師` 建立您的品牌指南。
```

### 警告輸出

當有非關鍵問題時：

```markdown
⚠️ **環境檢查完成（有警告）**

系統可以使用，但建議處理以下警告：

- 缺少選用套件或建議環境變數

**您可以**：

1. 現在設定 WooCommerce API
2. 繼續使用（稍後再設定）

輸入 1 或 2
```

### 錯誤輸出

當有關鍵錯誤時：

```markdown
❌ **環境檢查失敗**

發現 2 個錯誤需要修正：

1. **缺少套件**: woocommerce, crawl4ai
   修正：`pip install -r requirements.txt`

2. **WordPress 連線失敗**: Connection timeout
   修正：請檢查 WP_SITE_URL 和網路連線

**請修正後重新執行**: `/00_環境檢查`
```

## 修復功能（可選）

如果使用者同意，Antigravity 可以執行修復指令協助處理某些問題：

### 可由 Antigravity 協助修復項目

- ✅ 安裝缺少的 Python 套件
- ✅ 建立缺少的資料夾
- ✅ 生成 .env 範本檔案

### 需手動修復項目

- ❌ WordPress 連線問題（需使用者提供正確設定）
- ❌ Gemini API 問題（需使用者提供有效 API Key）
- ❌ 檔案權限問題（可能需要 sudo 權限）

## 驗證規則（Antigravity 自我檢查）

### 必須通過的檢查

- Python 版本 >= 3.10
- 必要套件已安裝
- .env 檔案存在且必要變數齊全
- WordPress 與 Gemini 連線可用
- LanceDB 可寫入
- FFmpeg 可用

### 可選的檢查

- WooCommerce API（如不使用商品功能）
- 完整的套件列表（某些套件可能只在特定功能需要）

## 執行時機

### 必須執行

1. **系統首次啟動**
2. **遷移至新環境**
3. **升級 Python 或相關套件後**

### 建議執行

4. **系統出現異常錯誤時**
5. **長時間未使用後重新啟動**

## 後續步驟

檢查通過後，引導使用者：

````
太好了！環境設定完成。

接下來您可以：
1. 執行 /s01_品牌建構師 - 建立品牌指南
2. 或者輸入「系統有哪些功能？」了解完整功能

推薦：先建立品牌指南，這是使用系統的基礎。

## 附錄：WordPress REST API 工具使用說明

本系統內建強大的 WordPress API 工具，位於 `utils/wordpress_client.py` 與 `agents/site_auditor.py`。

### 1. 網站結構稽核 (Site Auditor)
快速抓取網站所有內容結構：
```bash
python agents/site_auditor.py
````

輸出：`outputs/FUNIT/收集到的資料/site_structure.json`（若無則為 `outputs/FUNIT/raw_data/site_structure.json`）

### 2. WordPress Client 開發指南

若需開發新的 Agent，可直接呼叫 `wp_client`：

```python
from utils.wordpress_client import wp_client

# 取得所有文章
posts = wp_client.get_all_posts()

# 建立新文章
wp_client.create_post(
    title="Hello World",
    content="My first AI post",
    categories=[1],
    status="draft"
)
```

### 3. 支援功能

- **CRUD**: 文章 (Posts)、頁面 (Pages)、媒體 (Media)
- **批次抓取**: 自動處理分頁 (Pagination)
- **錯誤重試**: 內建 Retry 機制 (3 次重試)

```

---

## 技術實作筆記

`agents/core/tech_agent.py` 現在會檢查：
1. Python 版本與 venv 狀態
2. 必要/選用套件是否安裝
3. `.env` 是否存在與關鍵變數是否齊全
4. 目錄結構是否存在且可寫入
5. WordPress / WooCommerce / Gemini 連線
6. LanceDB 讀寫測試

---

**結束語**

Tech Agent 是確保系統順利運行的守門員，雖然只在系統啟動時執行，但它的重要性不可忽視。
```
