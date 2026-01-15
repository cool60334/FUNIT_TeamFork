---

name: refactor-engineer
description: 自動化舊文重構流程（抓取、生成 Brief、重寫與發布）；當需要重構已發布文章時使用。

---

> **來源**: 本技能源自 `文章重構.md`。

# 文章重構工作流程

## 指令 (Command)
`/文章重構` or `python3 agents/content/refactor_article.py --id <POST_ID>`

## 簡介 (Overview)
此工作流程用於自動化「舊文重構 (Content Refactoring)」。它會直接從 WordPress 抓取現有文章內容，分析其優缺點，使用 P02 生成優化版 Content Brief，並依序執行完整的內容生產流水線。

## 完整執行流程 (Pipeline Steps)

### 1. 啟動重構 (Refactor Agent)
抓取舊文並生成 Brief。
// turbo
```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/content/refactor_article.py --id <POST_ID>
```
*   **Input**: WordPress Post ID
*   **Output**: Content Brief (`outputs/FUNIT/briefs/{SLUG}_brief.json`)
*   **Result**: 取得生成的 `{SLUG}`。

### 1.5 手動確認 Brief (Manual Check) 🆕
**重要**：在執行 C01 之前，請確認以下項目：
- [ ] `target_audience` 是否為具體描述（非檔案路徑）
- [ ] `outline[0].key_points` 是否包含**具體的** Hook 策略
- [ ] `internal_link_opportunities` 是否包含 Pillar Page 回連

若有問題，請手動修正 Brief。

### 1.1 Legacy Content Notice (NEW)

> [!NOTE]
> **傳統編輯器 (Traditional Editor) 相容性**
> 
> 若舊文來自傳統編輯器，`refactor_article.py` 在抓取時會自動執行以下清洗：
> - 移除 Table of Contents 插件代碼 (如 `ez-toc-container`)
> - 提取圖片 Alt Text 作為內容的一部分
> - 清洗 H2 標題的內聯樣式
> 
> 這確保 Brief 生成時能正確分析舊文結構。

### 2. 撰寫草稿 (C01 內容撰寫)
參考舊文與 Brief 撰寫新文章。
// turbo
```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/production/c01_content_writer.py --slug <SLUG>
```

### 3. SEO 優化 (C02 SEO 優化)
優化標題、Meta Description、Schema 與 FAQ。
// turbo
```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/production/c02_seo_optimizer.py --slug <SLUG>
```

### 4. 事實查核 (C02a 事實查核) - Optional
查核文中數據、法規與連結正確性。
```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/production/c02a_fact_checker.py --slug <SLUG>
```
> ⚠️ 注意：C02a 對時效性資料（如費用、法規）的查核可能不準確，建議手動驗證。

### 5. 服務推薦 (C03 服務推薦) - Optional
根據文章內容插入相關服務或產品推薦。
```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/production/c03_service_recommender.py --slug <SLUG>
```

### 6. 視覺設計 (C04 視覺設計)
生成配圖並上傳至 WordPress，同時清除 `[PREMIUM_IMAGE_PROMPT]` 區塊。
// turbo
```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/production/c04_visual_director.py --slug <SLUG>
```
> ⚠️ 注意：若 API Quota 超限，圖片生成會失敗，需手動上傳圖片。

### 7. 手動內容審核 (Manual Review) 🆕
**重要**：在發布之前，請確認以下項目：
- [ ] 標題是否包含年份（如「2026 最新版」）
- [ ] 開頭 Hook 是否符合 Search Intent Research 策略
- [ ] 是否有殘留的 `PLACEHOLDER`、`PREMIUM_PLACEHOLDER` 或 `[PREMIUM_IMAGE_PROMPT]`
- [ ] 內部連結是否正確，Pillar Page 回連是否存在

### 8. 文章發布 (C05 文章發布)
將最終文章發布回 WordPress (保留原 ID，更新內容)。
// turbo
```bash
export PYTHONPATH=$PYTHONPATH:. && venv/bin/python agents/production/c05_publisher.py --slug <SLUG>
```

---

## 注意事項 (Notes)
- **URL 保持不變**: C05 會檢測到文章已存在 (基於 Slug 或 ID)，因此執行的是「Update」而非「Create」，這對 SEO 至關重要。
- **標題優化**: C02 會根據關鍵字優化標題，若原標題過於發散可能會被修改。
- **圖片更新**: C04 會生成新圖片，舊圖片不會自動刪除，需手動清理媒體庫 (若有需要)。
- **Hook 差異化**: C01 必須依照 P02 Brief 的具體 Hook 策略撰寫，禁止使用公式化開頭。

