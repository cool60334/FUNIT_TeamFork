---

name: cta-manager
description: 維護 CTA 連結與 UTM 規範並進行批次更新；當需要統一 CTA 連結時使用。

---

> **來源**: 本技能源自 `cta_management.md`。

# CTA 管理規範

為了確保全站行銷成效的可追蹤性，所有導向外部或特定聯絡管道的連結 (如 LINE、FB、預約頁面) 必須遵循本規範。

## 1. 資料來源 (Source of Truth)

所有 CTA 連結必須優先從 `config/brand_profile.json` 中的 `data_sources.contact_channels` 取得。

**目前設定**:
- **Official LINE**: `https://xxxxxxx(替換掉這裡)?utm_source=blog&utm_medium=article&utm_campaign=seo_content`

## 2. UTM 參數規範

所有放置於部落格文章中的 CTA 連結**必須**帶有 UTM 參數。

| 參數 | 建議值 | 說明 |
| :--- | :--- | :--- |
| `utm_source` | `blog` | 流量來源 |
| `utm_medium` | `article` | 流量媒介 |
| `utm_campaign` | `seo_content` 或 `{ARTICLE_SLUG}` | 具體的行銷活動名稱 |

## 3. 內容撰寫規則

1. **不可直接寫死 URL**: 在 AI 撰寫階段，應使用佔位符或動態讀取設定。
2. **連結檢測**: 任何指向 `使用者指定的網址` 的連結若缺少 UTM 參數，應視為錯誤並自動校正。

## 4. 批次更新程序

當品牌端變更 CTA 連結時，應執行 `scripts/batch_update_cta.py` 進行全站本地檔案同步，並重新發布至 WordPress。

