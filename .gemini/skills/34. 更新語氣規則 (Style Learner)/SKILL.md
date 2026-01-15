# 34. 風格學習工作流程

# Agent L (The Style Learner) 執行流程

## 觸發條件
使用者在 WordPress 手動修改文章後，執行腳本通知。

## 執行步驟

### Step 1: 執行資料準備腳本
```bash
cd "{PROJECT_ROOT}"
python3 agents/monitoring/style_gardener.py harvest --post-id <文章ID>
```

腳本會輸出差異內容（Before & After）。

### Step 2: 分析語氣與風格變化

檢視輸出的差異，判斷以下項目：

1. **語氣變化類型**:
   - 命令式 → 強調式？
   - 說教式 → 共鳴式？
   - 冷淡式 → 溫暖式？
   - 正式 → 親切？

2. **句式結構變化**:
   - 長句 → 短句？
   - 問句 → 陳述？
   - 被動 → 主動？
   - 抽象 → 具體？

3. **用詞策略變化**:
   - 專業術語 → 白話文？
   - 英文 → 中文？
   - 簡體 → 繁體？
   - 中性 → 情感？

### Step 3: 價值判斷

**問自己**:
- 這個變化反映了品牌的語氣偏好嗎？
- 這個變化值得讓其他 Agent 學習嗎？
- 這只是錯字修正或格式調整嗎？

**判斷結果**:
- ✅ **值得存入** → 繼續 Step 4
- ❌ **不值得** → 結束流程

### Step 4: 建構分析結果

確定以下資訊：
- **規則**: `@.agent/rules/12_style_learning_core.md`
- **trigger_scenario**: 什麼情境下會用到這個語氣？（例如：糾正讀者觀念、文章開頭、推薦服務）
- **style_change**: 具體的語氣/句式/用詞變化描述
- **bad_example**: 修改前的文字（原始版本）
- **good_example**: 修改後的文字（人類版本）
- **tags**: 分類標籤（例如：tone, correction, empathy, intro）

### Step 5: 存入 Style Memory

執行以下 Python 代碼：

```python
from utils.style_memory_manager import StyleMemoryManager

mgr = StyleMemoryManager()
mgr.add_example(
    trigger_scenario="<Step 4 確定的情境>",
    style_change="<Step 4 確定的變化描述>",
    bad_example="<修改前的文字>",
    good_example="<修改後的文字>",
    tags=["<標籤1>", "<標籤2>"]
)
```

### Step 6: 確認存入成功

檢查終端機輸出：
- ✅ 看到 `成功新增範例 (ID: xxxxxxxx...)` → 完成
- ❌ 看到錯誤訊息 → 檢查 `.env`、向量資料庫路徑與 `HUGGINGFACE_API_KEY`

### Step 7: （選填）驗證檢索

測試剛才存入的範例是否能被檢索到：

```python
from utils.style_memory_manager import StyleMemoryManager

mgr = StyleMemoryManager()
results = mgr.retrieve_examples(query="<相關情境描述>", k=3)

for i, ex in enumerate(results, 1):
    print(f"{i}. {ex['trigger_scenario']}")
    print(f"   Good: {ex['good_example'][:50]}...\n")
```

## 常見問題

### Q: 如果差異很多，該怎麼辦？
A: 一次只分析一個最重要的變化。如果有多個值得存入的變化，可以分批執行 Step 4-5。

### Q: 如果不確定是否值得存入？
A: 優先儲存「重複出現的修改模式」。例如，如果人類多次把「停！」改成「才...」，這就是明確的品牌偏好。

### Q: 標籤該怎麼選？
A: 常用標籤：
- `tone` - 語氣變化
- `structure` - 句式變化
- `correction` - 糾正觀念
- `intro` - 文章開頭
- `conclusion` - 文章結尾
- `empathy` - 同理心
- `professional` - 專業度

## 成功案例

### 案例 1: Post ID 7498
**差異**:
- Before: "停！客戶不在乎你的技術"
- After: "客戶才不在乎你的技術"

**分析**:
- trigger_scenario: 糾正讀者常見迷思時
- style_change: 從命令式/警示語氣轉為強調式/帶有傲嬌感的口語
- tags: ["tone", "correction", "empathy"]
