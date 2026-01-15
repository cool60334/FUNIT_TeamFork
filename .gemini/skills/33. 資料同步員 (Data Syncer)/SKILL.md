---
name: site-manager
description: 同步 WordPress 全站資料到本地與向量資料庫；當需要全站掃描或資料同步時使用。
---

> **來源**: 本技能源自 `全站掃描同步.md`。

# 全站掃描同步工作流程

## 指令 (Command)

`/site_sync` or `python3 agents/site_auditor.py`

## 簡介 (Overview)

此工作流程用於同步 WordPress 網站的所有資料（文章、頁面、分類、產品）至本地資料。它會自動執行以下動作：

1. **全站掃描 (Site Scanning)**：從 WordPress API 抓取所有最新內容。
2. **資料索引更新 (JSON Update)**：更新 `posts_index.json` 與 `site_structure.json`。
3. **向量資料庫同步 (Vector DB Sync)**：將清理後的文本、標題與圖片 Alt 資訊同步至 LanceDB (Content DB)，供後續 RAG 查詢與重複性檢查使用。

## 執行流程 (Pipeline Steps)

### 1. 執行掃描與同步

// turbo

```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/site_auditor.py
```

- **輸出檔案**:
  - `outputs/FUNIT/收集到的資料/site_structure.json`
  - `outputs/FUNIT/收集到的資料/posts_index.json`
- **同步目標**: 向量資料庫 `data/lancedb/`

## 為什麼要執行此流程？

- **發布新文章後**：確保向量資料庫擁有最新文章，避免後續推薦或撰寫時發生重複。
- **手動調整 WordPress 內容後**：同步最新的修改至本地索引。
- **定期維護**：確保本地資料與雲端網站一致。

## 注意事項 (Notes)

- **覆蓋機制**：向量資料庫使用 `upsert`，會根據 Post ID 自動覆蓋舊有記錄，不會產生重複。
- **效能優化**：腳本採用分頁抓取 (Batch Processing)，即使文章數量眾多也能穩定執行。
- **排除項**：預設會自動排除「缺貨 (outofstock)」的產品。
