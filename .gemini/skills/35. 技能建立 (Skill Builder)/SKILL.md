---

name: skill-builder
description: 建立或更新 Gemini Skills 的規範與流程；當需要新增 Skill、整理 SKILL.md 或打包 .skill 時使用。

---

# 技能建立 (Skill Builder)

## 任務要點
- 以 `.agent/workflows/*.md` 為流程來源，轉換為對應的 Skill。
- 保持單一品牌模式：路徑統一使用 `outputs/FUNIT/`，設定檔為 `config/brand_profile.json` 與 `docs/brand_guideline.md`。
- 每個 Skill 需包含 `SKILL.md`（只允許 `name` 與 `description` 的 YAML frontmatter）。
- 內容以「指令型」描述流程，避免多品牌與切換品牌說明。

## 打包
- 使用 `package_skill.py` 產出 `.skill` 檔。
