---
trigger: always_on
---

# Antigravity AI Agent 核心執行與規則讀取導引 (Master Protocol)

身為 Antigravity AI Agent，你必須嚴格遵循「先讀取規則、後執行動作」的作業標準。當使用者提出的要求涉及特定開發流程時，你必須立即檢索對應的 `.md` 規則文件，並將其約束條件納入當前任務的 context 中。

---

## 🛠 任務與規則對照表 (Rule Mapping)

當使用者提到以下關鍵字或執行相關操作前，你**必須讀取**對應的規則檔案：

| 使用者意圖 / 執行動作 | 應檢索之規則文件 | 核心守則 (Core Constraints) |
| :--- | :--- | :--- |
| **Git 提交 / 寫 Commit** | `commit-message.md` | 原子化提交、`<type>(<scope>): <subject>` 格式。 |
| **首次建立/推送到倉庫** | `initial-push.md` | 嚴禁洩漏 Secrets、強制檢查 `.gitignore`。 |
| **日常開發與常規推送** | `normal-push.md` | 測試覆蓋率、自動排除 Build Artifacts。 |
| **容器化 / Docker 構建** | `build-docker.md` | 使用 Non-root User、Named Volumes、Multi-stage。 |
| **修改配置 (.ini / .conf)** | `config-setting.md` | [section] 結構、絕對路徑驗證、機敏資訊佔位符。 |
| **管理環境變數 (.env)** | `env-setting.md` | 產出 `.env.example`、Fail-fast 驗證機制。 |
| **版本變更 / Release** | `version-manage.md` | 嚴格 SemVer、BREAKING CHANGE 強制標記。 |

---

## 🔄 標準執行演算法 (Standard Execution Loop)

在回應使用者任何指令前，請在內部執行以下思考迴圈：

1. **偵測 (Detect)：** 辨別使用者的請求屬於上述哪一個開發類別。
2. **加載 (Load)：** 宣告：「我正在根據 `[規則檔名].md` 進行安全與格式檢查...」。
3. **預檢 (Pre-flight Check)：**
    * **安全性：** 是否有 Hardcoded 密鑰？是否在 Root 下執行？
    * **結構性：** 路徑是否為相對路徑（Docker/Env）或絕對路徑（Config）？
    * **完整性：** 是否有對應的測試代碼或文件更新？
4. **執行 (Act)：** 僅在完全符合規則的情況下執行操作。若有衝突，必須指出具體規則編號並要求使用者修正。

---

## 🛑 全域禁令 (Global Prohibitions)

不論任何情境，若偵測到以下行為，請立即中斷並報錯：
* **禁止洩漏：** 嚴禁將 API Key、密碼、Token 寫入任何受版本控制的檔案。
* **禁止模糊：** 拒絕執行任何包含 "update", "fix", "test" 等無意義描述的提交請求。
* **禁止絕對路徑：** 在 Docker 與 Env 相關配置中，嚴禁使用特定機器的絕對路徑。
* **禁止 Root 執行：** 產出的 Dockerfile 必須包含非 Root 使用者切換。

---

> **Agent 自我宣告：** 我已理解 Antigravity 體系結構。在執行下一步之前，我將主動引用上述規則文件以確保開發合規性。