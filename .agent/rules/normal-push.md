1. 敏感資訊過濾與憑證管理 (Secrets & Credentials Protection)
規則名稱：Zero-Leak Credential Policy

適用情境：撰寫設定檔、常數定義或進行 Git Commit 階段。

具體 Rule 描述：

Trigger: 偵測到字串符合 API Key、OAuth Token、SSH Key、密碼格式，或副檔名為 .env, .pem, .json (含金鑰內容) 時。

Action: 立即阻斷該段程式碼生成或提交，並強制將敏感參數移至環境變數（Environment Variables）或 Secret Manager。

What to do: 使用 process.env 或系統變數讀取憑證，並自動檢查 .gitignore 是否已包含該敏感檔案。

What NOT to do: 禁止將任何測試用或正式環境的 Hard-coded secrets 直接寫入原始碼中。

2. 規範化提交訊息 (Conventional Commits Enforcement)
規則名稱：Standardized Git Message Protocol

適用情境：執行 git commit 指令時。

具體 Rule 描述：

Trigger: AI 準備執行提交動作前。

Action: 強制將提交訊息格式化為：<type>: <description>。

What to do: 參考commit-message.md。

What NOT to do: 禁止使用 "update code"、"fix bug" 或無意義的隨機字串作為 Commit Message。

3. 專案結構與環境隔離 (Git Hygiene & Ignore Rules)
規則名稱：Artifact & Dependency Exclusion

適用情境：檔案新增、修改或執行 git add 時。

具體 Rule 描述：

Trigger: 當目錄中出現 build artifacts (如 dist/, bin/)、依賴套件 (如 node_modules/, venv/) 或系統暫存檔 (如 .DS_Store)。

Action: 自動檢查並更新 .gitignore 檔案，確保上述路徑被排除於版本控制之外。

What to do: 確保專案根目錄具備 .gitignore 與 .editorconfig，維持跨平台開發的一致性。

What NOT to do: 禁止將第三方依賴庫（Dependency packages）或編譯後的二進位檔（Binary files）上傳至遠端倉庫。

4. 單元測試覆蓋要求 (Automated Testing Mandate)
規則名稱：Test-Driven Integrity (TDI)

適用情境：新增功能邏輯 (Function/Logic) 或修改現有模組時。

具體 Rule 描述：

Trigger: 當 AI 生成新的業務邏輯程式碼或 Export Function 時。

Action: 同步生成對應的單元測試（Unit Test）檔案，並確保測試通過。

What to do: 新功能的測試覆蓋率必須達到專案設定的 Baseline（如 80%），且必須包含邊界條件（Edge cases）的測試。

What NOT to do: 禁止在沒有提供測試腳本的情況下，直接將複雜邏輯程式碼推送至 main 或 develop 分支。

5. 文件化與專案進入點維護 (Documentation & README Sync)
規則名稱：Auto-Sync Documentation

適用情境：專案初始化、API 介面變更或目錄結構調整時。

具體 Rule 描述：

Trigger: 偵測到 README.md 缺失，或代碼中出現新的依賴項、環境變數要求時。

Action: 自動更新 README.md 中的 "Installation", "Usage", "Environment Variables" 章節。

What to do: 文件需使用正確的 Markdown 語法，包含開發者如何啟動專案的明確步驟（Getting Started）。

What NOT to do: 禁止上傳結構不明確、缺乏說明文件的專案至 GitHub。