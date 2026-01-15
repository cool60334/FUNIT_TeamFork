---

name: bulk-style-gardener
description: 批次掃描全站修訂並存入 Style Memory；當需要全站風格學習時使用。

---

> **來源**: 本技能源自 `批次風格學習.md`。

# 全站風格學習工作流程 (Bulk Style Learning)

## 觸發條件
- 發現多篇文章有人類編輯修改時
- 新接手一個品牌網站時

## 完整流程

### Step 1: 全站掃描

使用 `revision_scanner.py` 掃描全站文章的修訂紀錄：

```bash
cd "{PROJECT_ROOT}"
python3 agents/monitoring/revision_scanner.py scan --only-changes
```

**參數說明**:
- `--only-changes`: 只顯示有差異的文章（推薦）
- `--limit N`: 限制掃描數量（用於測試）
- `--output PATH`: 指定報告輸出路徑

**輸出**:
- 終端機摘要報告
- JSON 報告存於 `outputs/FUNIT/reports/revision_scan_{timestamp}.json`

---

### Step 2: 分析報告

使用 `style_gardener.py` 分析掃描報告：

```bash
cd "{PROJECT_ROOT}"
python3 agents/monitoring/style_gardener.py analyze --report outputs/FUNIT/reports/revision_scan_{timestamp}.json
```

**輸出**:
- 逐一列出所有有意義的差異
- 每個差異包含 Before/After 對照

---

### Step 3: Antigravity 分析與決策

針對 Step 2 輸出的每個差異，Antigravity 需判斷：

1. **語氣變化類型**:
   - 命令式 → 強調式？
   - 說教式 → 共鳴式？
   - 正式 → 親切？

2. **是否值得存入**:
   - ✅ 語氣/用詞有明確變化
   - ✅ 反映品牌偏好
   - ❌ 純格式調整（括號、空格）
   - ❌ 錯字修正

---

### Step 4: 存入 Style Memory

對於值得存入的差異，執行：

```bash
cd "{PROJECT_ROOT}"
python3 agents/monitoring/style_gardener.py plant \
  --trigger "觸發情境描述" \
  --change "風格變化描述" \
  --bad "修改前文字" \
  --good "修改後文字" \
  --tags "tone,correction,empathy"
```

或使用 Python 直接存入：
```python
from utils.vector_db_manager import vector_db
from datetime import datetime

vector_db.add_style_rule(
    rule_id=f"style_learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    text="情境與範例描述...",
    metadata={
        "trigger_scenario": "...",
        "style_change": "...",
        "bad_example": "...",
        "good_example": "...",
        "tags": "...",
        "source": "Post ID XXX",
        "timestamp": datetime.now().isoformat()
    }
)
```

---

### Step 5: 驗證

確認風格學習已存入：

```python
from utils.vector_db_manager import vector_db

results = vector_db.query_style_rules("風格學習", n_results=10)
for r in results:
    if r['id'].startswith('style_learning_'):
        print(f"✅ {r['id']}: {r['metadata'].get('trigger_scenario', 'N/A')}")
```

---

## 常用標籤 (Tags)

| 標籤 | 說明 |
|:---|:---|
| `tone` | 語氣變化 |
| `structure` | 句式變化 |
| `professional` | 專業度調整 |
| `marketing` | 行銷語氣調整 |
| `promise` | 承諾/預期管理 |
| `empathy` | 同理心表達 |
| `parenthetical` | 括號註解處理 |

---

## 快速指令

```bash
# 1. 掃描全站（只看有差異的）
python3 agents/monitoring/revision_scanner.py scan --only-changes

# 2. 掃描指定數量（測試用）
python3 agents/monitoring/revision_scanner.py scan --limit 10

# 3. 分析最新報告
python3 agents/monitoring/style_gardener.py analyze --report outputs/FUNIT/reports/revision_scan_*.json

# 4. 存入單筆學習
python3 agents/monitoring/style_gardener.py plant --trigger "..." --change "..." --bad "..." --good "..." --tags "tone"
```

---

## 相關檔案

- `agents/monitoring/revision_scanner.py` - 全站掃描工具
- `agents/monitoring/style_gardener.py` - 分析與存入工具
- `utils/vector_db_manager.py` - Style DB 管理
- `utils/embedding_function.py` - 🆕 EmbeddingGemma-300m 模型載入
- `.agent/rules/style_gardener_rules.md` - 分析規則

## 🆕 Embedding 模型

系統使用 **Google EmbeddingGemma-300m** (768 維度) 進行語義向量化：

```python
# 自動載入並使用 EmbeddingGemma
from utils.vector_db_manager import vector_db

# 查詢會自動使用 EmbeddingGemma 進行向量化
results = vector_db.query_style_rules("語氣變化", n_results=5)
```

**注意**: 需在 `.env` 中設定 `HUGGINGFACE_API_KEY` 才能使用此模型。

