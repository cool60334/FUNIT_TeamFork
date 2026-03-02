1. SemVer 強制遞增準則
規則名稱：SemVer 強制遞增準則

適用情境：提交任何程式碼變更 (Commit/PR)

具體 Rule 描述：

Trigger: 偵測到代碼庫變更。

Action: 嚴格執行 MAJOR.MINOR.PATCH 邏輯。 

What to do: 若為 Bug Fix 僅增加 PATCH；新增功能且向下相容增加 MINOR；涉及破壞性變更（Breaking Changes）必須增加 MAJOR。

What NOT to do: 禁止跳號（如從 1.0.1 直接跳 1.0.5）或在未變更 API 的情況下增加 MAJOR。

2. 破壞性變更強制標記
規則名稱：SemVer 破壞性變更強制標記

適用情境：修改公用 API 或現有函式簽章

具體 Rule 描述：

Trigger: 修改受保護的 Public Interface 或修改現有 Function Signature。

Action: Constraint: 系統必須在 PR 描述中強制加入 BREAKING CHANGE 關鍵字。

What to do: 必須同步更新受影響的單元測試，並在代碼註解中使用 @deprecated 標籤。

What NOT to do: 禁止在 MINOR 或 PATCH 版本中引入會導致現有客戶端編譯失敗或 Runtime 錯誤的變更。

3. 自動化變更日誌聯鎖
規則名稱：自動化變更日誌聯鎖

適用情境：版本號變動時

具體 Rule 描述：

Trigger: 執行 version bump 動作。

Action: 自動同步更新 CHANGELOG.md。

What to do: 依據 Conventional Commits 規範分類紀錄（feat, fix, refactor, chore）。每一條記錄必須關聯至具體的 Issue ID 或 PR Link。

What NOT to do: 禁止產生「Update code」或「Minor fix」等無實質意義的模糊描述。

4. 依賴版本鎖定與驗證
規則名稱：依賴版本鎖定與驗證

適用情境：修改配置檔案 (如 package.json, go.mod)

具體 Rule 描述：

Trigger: 新增或更新第三方依賴庫（Dependency）。

Action: 執行相容性檢查（Compatibility Check）。

What to do: 優先使用固定的版本號（Pinned Versions）或帶有安全範圍的標籤（如 ^ 或 ~）。必須執行 vulnerability scan 確認無已知安全漏洞。

What NOT to do: 禁止引入處於 Alpha 或實驗性階段且未經過審核的外部依賴。

5. 預發布與候選版本管理
規則名稱：預發布與候選版本管理

適用情境：合併至非 Master/Main 分支時

具體 Rule 描述：

Trigger: 合併至 develop 或 staging 分支。

Action: 自動附加 Pre-release 標籤。

What to do: 使用 -alpha.x, -beta.x 或 -rc.x 後綴標註版本狀態。確保預發布版本的 metadata 包含 Build Timestamp。

What NOT to do: 禁止將帶有 Pre-release 標籤的代碼直接標記為正式釋出版本（Production Ready）。