---
name: fact-memory-manager
description: 管理 Fact Memory（存入/查詢/匯入 PDF）；當需要維護事實記憶或導入官方文件時使用。
---

> **來源**: 本技能源自 `事實記憶系統.md`。

# 事實記憶系統 (RAG 修正機制)

這份文件說明如何讓 AI 記住過往的事實修正，避免重複犯錯。我們實作了一個基於 LanceDB 的 RAG (Retrieval-Augmented Generation) 系統。

## 🆕 Embedding 模型

系統使用 **Google EmbeddingGemma-300m** 進行語義向量化：

- **模型**: `google/embeddinggemma-300m`
- **維度**: 768
- **來源**: HuggingFace
- **實作**: `utils/embedding_function.py`

**環境設定**: 需在 `.env` 中設定 `HUGGINGFACE_API_KEY`

---

## 核心架構

我們在 `utils/vector_db_manager.py` 中使用 `facts_collection`，專門用來儲存已驗證的事實與修正紀錄。

### 1. 記憶流程 (Memorization) - C02a 事實查核

當 **C02a 事實查核** 檢查文章並發現錯誤時：

1. 它會透過 `check_and_fix` 函式進行修正。
2. 若修正成功（狀態為 `incorrect` 且有 `correction`），系統自動呼叫 `FactMemoryManager.add_fact()`。
3. 修正內容被存入 LanceDB，並附帶 `claim` (錯誤聲明) 與 `context` (原始上下文)。

**觸發條件**:

- `Status` = "incorrect"
- `Correction` != null

### 2. 回憶流程 (Retrieval) - C01 內容撰寫

當 **C01 內容撰寫** 撰寫新文章時：

1. 讀取 Brief 中的 `primary_keyword` 與 `secondary_keywords`。
2. 呼叫 `FactMemoryManager.retrieve_facts(query)` 去查詢向量資料庫。
3. 若找到相關的修正紀錄（Cos Sim 相似度高），會將其整理為 `🧠 Fact Memory` 區塊。
4. 將此區塊注入到 LLM 的 Prompt 中，並加上 "CRITICAL" 權重，要求 AI 優先採用記憶中的事實。

---

## 🆕 PDF 文件導入

系統支援直接將 PDF 官方文件導入 Fact Memory：

```bash
# 啟用虛擬環境並執行
source venv/bin/activate
python3 utils/pdf_to_fact_memory.py "path/to/document.pdf"
```

**工具參數**:

- `--chunk-size`: 每個區塊的最大字元數 (預設: 1500)
- `--dry-run`: 預覽模式，不實際存入資料庫

**範例**:

```bash
# 導入 日本環球影城 官方指南
python3 utils/pdf_to_fact_memory.py "USJ_Official_Guide_2025.pdf"

# 預覽導入結果
python3 utils/pdf_to_fact_memory.py "document.pdf" --dry-run
```

---

## 檔案結構

- `utils/vector_db_manager.py`: 管理 `facts_collection` 與相關操作方法
- `utils/embedding_function.py`: 🆕 EmbeddingGemma-300m 模型載入
- `utils/pdf_to_fact_memory.py`: 🆕 PDF 文件導入工具
- `utils/fact_memory_manager.py`: 提供高層次的 API (`add_fact`, `retrieve_facts`)
- `agents/production/c02a_fact_checker.py`: 整合寫入邏輯 (`_memorize_corrections`)
- `agents/production/c01_content_writer.py`: 整合讀取邏輯 (`_retrieve_fact_reminders`)

---

## 如何手動加入記憶？

### 方法 1: 使用 FactMemoryManager (推薦)

```python
from utils.fact_memory_manager import FactMemoryManager

fm = FactMemoryManager()
fm.add_fact(
    context="關於申請費用的說明",
    claim="申請費是 $50",
    correction="申請費已調漲為 $60",
    source="https://official-site.com/fees"
)
```

### 方法 2: 直接使用 vector_db

```python
from utils.vector_db_manager import vector_db
import uuid
from datetime import datetime

vector_db.add_fact(
    fact_id=str(uuid.uuid4()),
    text="Context: 大阪周遊卡價格\nVerified Fact: 大阪周遊卡 1日券 價格為 3300 日圓",
    metadata={
        "type": "verified_fact",
        "source": "Japan Railways Official Website",
        "added_at": datetime.now().isoformat()
    }
)
```

### 方法 3: 導入 PDF 文件

```bash
python3 utils/pdf_to_fact_memory.py "official_document.pdf"
```

---

## 查詢 Fact Memory

```python
from utils.vector_db_manager import vector_db

# 語義查詢 (使用 EmbeddingGemma-300m)
results = vector_db.query_facts("日本環球影城門票價格", n_results=5)

for r in results:
    print(f"距離: {r['distance']:.4f}")
    print(f"來源: {r['metadata'].get('source', 'N/A')}")
    print(f"內容: {r['document'][:200]}...")
    print()
```

---

## 未來優化方向

1. **Dashboard 管理**: 提供介面讓人類檢視並刪除錯誤的記憶。
2. **權重調整**: 隨著時間推移，降低舊記憶的權重（如果事實又變了）。
3. **主動學習**: 讓 AI 分析 `outputs/drafts` 的人工修改紀錄 (Diff)，自動提取修正點。
4. **多語言支援**: EmbeddingGemma 支援中英混合查詢，可進一步優化多語言場景。
