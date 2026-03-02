1. 憑證隔離與 .gitignore 自動稽核
規則名稱：Secrets & .gitignore Enforcement

適用情境：建立新專案、修改配置檔案或處理 API 金鑰時。

具體 Rule 描述：

Trigger: 當 Agent 偵測到任何包含敏感資訊（如 API_KEY, SECRET, PASSWORD, TOKEN）的變數定義時。

What to do:

必須將所有敏感變數存放於專案根目錄的 .env 檔案中。

必須同步產出一份 .env.example，僅保留鍵名（Keys）清空值（Values），並附註說明，作為環境建置範本。

必須在 .gitignore 檔案中明確加入 .env 項目。

What NOT to do:

絕對禁止將實質的密鑰值硬編碼（Hardcode）在原始碼或 docker-compose.yml 的 environment 區塊中。

禁止產出未經過 .gitignore 過濾的環境變數備份檔。

2. 環境變數引用去絕對路徑化
規則名稱：Portable Environment Referencing

適用情境：在 docker-compose.yml 或應用程式引啟動腳本中引用 .env 檔案時。

具體 Rule 描述：

Trigger: 當需要定義容器或行程的環境變數來源時。

What to do:

僅能使用相對路徑引用 .env 檔案。

預設優先依賴 Docker Compose 的自動加載機制（當 .env 與 docker-compose.yml 同目錄時）。

What NOT to do:

絕對禁止在 docker-compose.yml 的 env_file 欄位中使用絕對路徑（例如：/abs/path/to/.env）。

禁止在程式碼中撰寫依賴特定作業系統絕對路徑的環境讀取邏輯。

3. 環境變數強制驗證機制（Schema Validation）
規則名稱：Environment Variable Type & Presence Check

適用情境：在應用程式啟動入口點（Entrypoint）或配置初始化模組開發時。

具體 Rule 描述：

Trigger: 當應用程式啟動讀取 process.env 或系統環境變數時。

What to do:

必須實作「啟動前檢查」邏輯。若必要的環境變數缺失或格式不符（如 PORT 不是數字），必須立即拋出明確錯誤並終止進程（Fail-fast）。

建議產出具備類型定義的配置物件（Config Object），確保程式碼內不直接操作字串類型的環境變數。

What NOT to do:

禁止在缺少環境變數時使用隱式預設值（Implicit Defaults）而未給予任何警告提示。

4. 命名空間與前綴標準化
規則名稱：Variable Namespacing & Standard Prefixing

適用情境：定義新的環境變數名稱時。

具體 Rule 描述：

Trigger: 當為專案新增配置項目時。

What to do:

變數命名必須全部大寫，並使用底線連接（SNAKE_CASE）。

必須為變數加上專案或服務前綴，例如 AG_API_PORT (Antigravity API Port)。

What NOT to do:

禁止使用過於模糊的名稱，如單純的 PORT、URL 或 DEBUG，以避免在多容器環境中產生命名衝突。

5. 環境情境隔離規範 (Dev vs. Prod Layering)
規則名稱：Environment Context Segregation

適用情境：定義不同部署階段（Development, Staging, Production）的配置時。

具體 Rule 描述：

Trigger: 當專案涉及多階段部署或需要區分本地與雲端配置時。

What to do:

必須使用後綴區分環境文件，例如 .env.development, .env.production。

在 docker-compose.yml 中應優先使用 env_file 屬性來讀取對應環境的文件。

What NOT to do:

禁止在 .env.development 中放入任何生產環境（Production）的正式存取憑證。

禁止在單一 .env 文件中混雜多個環境的變數（例如同時存在 DEV_DB_URL 與 PROD_DB_URL）。