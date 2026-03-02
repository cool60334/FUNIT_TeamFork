1. 結構完整性與標準化格式規則 (Structural Integrity & Formatting)
適用情境：任何新建或修改 .cfg, .conf, .ini 檔案的操作。

Trigger: 偵測到檔案寫入請求或語法檢查程序啟動。

具體 Rule 描述：

Action: 所有設定必須嚴格遵循 [section] 下方接 key = value 的結構。禁止在 Section 外部定義任何參數。

What to do: 

每個 Section 必須有明確的主題（如 [DATABASE], [NETWORK]）。

使用 # 進行單行註釋，且必須在參數上方說明該參數的用途與資料型別（例如：# Integer: Connection timeout in seconds）。

What NOT to do: 

禁止使用空值（Null/Empty）而不提供預設邏輯。

禁止在同一檔案中使用重複的 [section] 名稱。

2. 路徑與可調用對象驗證規則 (Path & Callable Validation)
適用情境：設定 log_path, upload_directory 或任何以 _callable 結尾的邏輯對應參數。

Trigger: 參數名稱包含 path, dir, root 或 callable 關鍵字。

具體 Rule 描述：

Action: 針對路徑類參數，AI Agent 必須執行「絕對路徑校驗」；針對 Callable 參數，必須驗證其符合 Python 導入規範或系統執行格式。

What to do: 

路徑：必須使用絕對路徑（Absolute Path），如 /opt/antigravity/logs/。

Callable：必須使用 module.submodule:function_name 格式，確保動態加載時具備確定的進入點。

What NOT to do: 

禁止使用相對路徑（如 ./logs），以防止因執行路徑切換導致的檔案存取錯誤。

禁止指向不存在的模組路徑或未經授權的系統指令。

3. 機敏資訊與環境變數對應規則 (Secret Management & Env Mapping)
適用情境：處理資料庫密碼、API 金鑰或任何敏感的身份驗證資訊。

Trigger: 參數鍵值包含 password, secret, token, key 或 user。

具體 Rule 描述：

Action: 強制執行「環境變數優先（Environment Overrides）」邏輯。設定檔中僅允許存放變數佔位符，嚴禁明文。

參數對應邏輯 (Mapping Logic)：對應規則必須符合 ANTIGRAVITY_{SECTION}_{KEY} 的大寫命名慣例。例如 [DATABASE] 下的 password 應對應 ANTIGRAVITY_DATABASE_PASSWORD。

What to do: 

使用 ${ENV_VAR_NAME} 語法作為值，例如 db_password = ${DB_PASSWORD}。

What NOT to do: 

絕對禁止 在設定檔中以明文寫入任何生產環境（Production）的登入憑據或私鑰。

4. 基礎設施與網路邊界規則 (Network & Infrastructure Constraints)
適用情境：配置 host, port, timeout 等基礎設施參數。

Trigger: 修改 [NETWORK] 或 [INFRASTRUCTURE] 區塊內容。

具體 Rule 描述：

Action: 執行數值邊界檢查（Boundary Check）與合法 IP 格式驗證。

What to do: 

port 必須在 1024-65535 之間，除非是受信任的系統服務設定。

host 若為本機監聽必須明確寫為 127.0.0.1 或 0.0.0.0，禁止使用模糊的自定義 hostname 而未配套 DNS 邏輯。

What NOT to do: 

timeout 禁止設定為 0 (無限等待)，必須設定合理的整數上限（建議預設 30-60 秒）。

5. 環境運行模式與日誌等級一致性規則 (Environment & Logging Logic)
適用情境：切換 environment (dev/prod) 或調整 log_level。

Trigger: 變更 environment 參數值。

具體 Rule 描述：

Action: 當 environment = production 時，Agent 必須強制執行安全性與效能檢查鎖定。

What to do: 

若環境為 production，log_level 必須限制為 INFO, WARNING, 或 ERROR。

必須在 [APP_BEHAVIOR] 區塊中明確標註 feature_flags 的狀態。

What NOT to do: 

禁止在 production 環境下開啟 DEBUG 日誌等級，以防敏感資訊流出。

禁止在生產環境中啟用 enable_mock_data = true 等測試類旗標。