# 22. 事實查核工作流程

## 目的
在文章撰寫完成後（C01），SEO 優化前（C02），進行全自動的事實查核與內容修正，確保資訊正確性。

## 觸發時機
- C01 Content Writer 完成草稿後
- 文章包含大量數據、年份、費用或政策資訊時
- **已發布文章的定期審查** 🆕
- **年份時效性檢查**: 確認文中「最新」字眼之年份是否需從 2024/2025 更新至 2026。 🆕

---

## ⚠️ 環境要求

> **重要**: 必須在虛擬環境中執行，以確保 EmbeddingGemma 模型正常運作。

```bash
# 1. 啟用虛擬環境
source venv/bin/activate

# 2. 確認 sentence-transformers 已安裝
pip show sentence-transformers
```

若未安裝：
```bash
pip install "sentence-transformers>=5.1.0"
```

---

## 執行流程

### Step 1: 提取需查核事實

#### 手動執行 (無 CLI 時)
1. 識別文章中的 **Hard Facts**:
   - 年份、日期、截止日
   - 費用、交通費、景點價格
   - 營業時間、百分比、排名
   
2. 識別 **政策與規則**:
   - 簽證規則變化
   - 入境門檻
   - 旅遊補助政策

### Step 2: 混合查核策略 (Hybrid Research) 🆕

本技能採用三層式查核架構：

1.  **L1: AI 代理搜尋 (AI Agent Search)**: 呼叫 Gemini Google Search Grounding，讓 AI 以代理人身份直接訪問網際網路進行全文查核。
2.  **L2: Python 針對性搜尋 (Targeted Search)**: 若 L1 無法判定，則退回使用 DuckDuckGo 進行精確查詢 (例如 PTT/Dcard 站內搜尋)。
3.  **L3: 深度抓取 (Deep Fetch)**: 針對關鍵網址進行全文抓取分析，確保數據精確無誤。

#### 2a. 查詢 Fact Memory (RAG)
先查詢向量資料庫，檢查是否已有相關修正記錄：

```python
from utils.vector_db_manager import vector_db

results = vector_db.query_facts(
    query_text="<相關關鍵字>",
    n_results=5
)

for r in results:
    print(f"來源: {r['metadata'].get('source')}")
    print(f"內容: {r['document'][:200]}...")
```

#### 2b. 網路搜尋驗證
使用 `search_web` 工具搜尋官方來源：
- 優先搜尋 `.gov`, `.edu`, 官方網站
- 交叉比對多個來源

### Step 3: 判定與修正

| 狀態 | 定義 | 動作 |
|------|------|------|
| **Verified** | 與官方來源一致 | Pass |
| **Incorrect** | 與官方來源矛盾 | 自動修正 |
| **Uncertain** | 無法確認 | 標記待人工審查 |

### Step 4: 存入 Fact Memory 🆕

**所有查核結果都應存入向量資料庫**，供未來文章自動參考。

```python
from utils.fact_memory_manager import FactMemoryManager

fm = FactMemoryManager()
fm.add_fact(
    context="<事實的背景描述>",
    claim="<原本錯誤的聲明>",
    correction="<查核後的正確資訊>",
    source="<來源 URL 或名稱>"
)
```

### Step 5: 檢查查核報告
- 輸出路徑: `outputs/FUNIT/reports/latest_fact_check.json`
- 格式:
  ```json
  [
    {
      "claim": "大阪周遊卡包含環球影城門票",
      "status": "incorrect",
      "correction": "大阪周遊卡不包含環球影城，僅包含樂高樂園",
      "source": "https://www.osp.osaka-info.jp/cht/",
      "fact_memory_id": "598fcb65-ec3c-478a-..."
    }
  ]
  ```

### Step 6: 繼續下游流程
- **新文章**: 將修正後的草稿傳遞給 C02 SEO Optimizer
- **已發布文章**: 執行 `/c06_文章修正` 流程

---

## 高風險查核項目 🆕

以下類型的事實特別容易過時，需優先查核：

| 類型 | 範例 | 建議查核頻率 |
|------|------|-------------|
| 簽證/入境政策 | 日本免簽規定/入境填寫表格 | 每季 |
| 票券價格 | 環球影城/迪士尼門票價格 | 每季 |
| 交通時刻表 | 新幹線/鐵路時刻表變更 | 每年 |
| 景點營業資訊 | 設施維修/休館公告 | 即時 |

---

## 相關規則
- `c02a_rules.md` (查核判定標準)
- `事實記憶系統.md` (Fact Memory 詳細說明)

## 相關流程
- `/c06_文章修正` (已發布文章的修正流程) 🆕
