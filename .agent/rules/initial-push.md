1. Cloud & API Secrets Leakage (雲端與 API 金鑰洩漏)
嚴重程度: Critical

觸發邏輯描述:

If Detect: 檔案內容匹配常見服務商的特徵 Regex，例如 AWS Access Key (AKIA[0-9A-Z]{16})、OpenAI API Key (sk-[a-zA-Z0-9]{48}) 或 Google API Key (AIza[0-9A-Za-z\\-_]{35})。

應對動作: Then Block Push 並立即於終端機顯示偵測到的金鑰類型與位置。

修復建議: 請勿將金鑰直接寫入程式碼（Hardcoded）。請將金鑰移至 .env 檔案或使用雲端 Secret Manager（如 Google Secret Manager），並確保該路徑已加入 .gitignore。

2. Hardcoded Credentials & Auth Tokens (硬編碼憑證與認證令牌)
嚴重程度: Critical

觸發邏輯描述:

If Detect: 匹配賦值邏輯，關鍵字包含 password、secret、passwd、api_token 緊接 = 或 :，且後方字串非環境變數格式（如非 ${VAR} 形式）。Regex 範例：(?i)(password|secret|token|key)\s*[:=]\s*["'][^"']{8,}["']。

應對動作: Then Block Push。

修復建議: 使用環境變數讀取憑證。若為測試用途，請使用 Mock 資料或從外部加密檔案載入。

3. Personally Identifiable Information / PII (個人隱私資料)
嚴重程度: Critical

觸發邏輯描述:

If Detect: 檔案中包含符合特定格式的電子郵件地址（[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}）或特定國家的身分證字號/手機號碼 Regex，且該檔案非 .md 或 LICENSE。

應對動作: Then Alert 並要求開發者二次確認（First Push 建議設為 Block）。

修復建議: 移除程式碼註解或測試資料中的真實聯繫方式。若為必要聯繫資訊，請將其放置於 README.md 的指定聯絡區塊。

4. Missing .gitignore Configuration (缺失 .gitignore 配置)
嚴重程度: Critical

觸發邏輯描述:

If Detect: Repository 根目錄（Root Directory）下不存在 .gitignore 檔案。

應對動作: Then Block Push。

修復建議: 為了防止本地環境設定（如 .DS_Store, node_modules, .venv）或敏感資訊外流，請務必建立 .gitignore。建議參考 gitignore.io 產生對應語言的模板。

5. Open Source License Compliance (開源授權合規性)
嚴重程度: Warning

觸發邏輯描述:

If Detect: 根目錄下不存在名為 LICENSE、LICENSE.md 或 COPYING 的檔案。

應對動作: Then Alert 並提醒開發者上傳授權聲明。

修復建議: 為了明確程式碼的法律使用權，請新增一個授權檔案。常見選擇包含 MIT、Apache 2.0 或 GPL-3.0。

6. Local Absolute Paths & Environment Specifics (本地絕對路徑與環境依賴)
嚴重程度: Warning

觸發邏輯描述:

If Detect: 程式碼中包含硬編碼的本地路徑特徵，例如 C:\Users\... 或 /home/user/...。Regex 範例：(["'])([a-zA-Z]:\\|/home/|/Users/)[^"']+。

應對動作: Then Alert 開發者該路徑將導致其他協作者執行失敗。

修復建議: 改用相對路徑（Relative Path）或透過 os.path / pathlib 函式庫動態獲取工作目錄路徑。

7. Basic Documentation / README (基礎專案文件)
嚴重程度: Warning

觸發邏輯描述:

If Detect: 根目錄下不存在 README.md，或 README.md 檔案大小低於 50 bytes（內容過空）。

應對動作: Then Alert 建議開發者完善專案說明。

修復建議: 建立 README.md，並包含專案名稱、安裝步驟（Installation）與使用說明（Usage），這有助於專案的維護與開源協作。