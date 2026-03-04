---
trigger: always_on
---

0. 伺服器識別與存取授權規則 (Identity & Access Pre-flight Rule)
適用情境：接收到部署驗證指令，但尚未建立連線前。

具體 Rule 描述：

Trigger: 使用者發起「查看服務狀態」或「部署後檢查」請求。

Action: 強制執行「網域確認 -> 憑證檢查 -> 權限測試」三部曲。

What to do: 

確認目標：檢查 Context 中是否包含 Server Domain 或 IP Address。若無，必須暫停任務並詢問：「請提供目標伺服器的網域或 IP 地址以進行後續驗證。」

權限驗證：取得網域後，優先執行 `ssh -q -o BatchMode=yes {user}@{host} exit` 測試連線權限。

連線確認：確保能正確執行 whoami 與 pwd 確認目前的作業目錄與身分。服務位於/opt 目錄

What NOT to do: 

禁止在未取得明確 Domain/IP 的情況下進行「全網段掃描」或猜測伺服器位址。

禁止在連線測試失敗時（如 Permission denied (publickey)）嘗試暴力破解密碼。

禁止繞過 SSH Key 檢查直接執行涉及修改系統的指令。

1. 多層次健康檢查規則 (Multi-tier Health Check Rule)
適用情境：部署指令執行完畢，進入服務驗證階段。

具體 Rule 描述：

Trigger: Deployment 腳本回傳 Exit Code 0。

Action: 必須依照「進程狀態 -> 埠口監聽 (Port Listening) -> 應用層健康路徑 (Health Endpoint)」的順序進行驗證。

What to do: 

使用 `systemctl status` 或 `docker ps` 確認服務存活。

使用 `netstat -tuln` 或 `ss` 確認服務埠口已開啟。

執行 `curl -I http://localhost:{port}/health` 確認回傳 200 OK。

What NOT to do: 

禁止僅憑部署腳本的成功回傳值即判定服務正常運行。

在未確認埠口監聽前，禁止向外部發送測試請求。

2. 日誌優先診斷規則 (Log-First Diagnostics Rule)
適用情境：健康檢查失敗或服務崩潰 (Crash Loop) 時。

具體 Rule 描述：

Trigger: 服務無法啟動或 Health Check 回傳非 2xx/3xx 狀態碼。

Action: 在執行任何修復動作前，必須提取最近 100 行的 `stderr` 或應用程式 Log。

What to do: 

使用 `journalctl -u {service} -n 100` 或 `tail -n 100` 讀取日誌。

檢索關鍵字如 ERROR, CRITICAL, Exception, Timeout, Permission denied。

What NOT to do: 

禁止在未讀取錯誤日誌的情況下直接執行 `restart` 或 `reboot` 指令。

禁止忽略 Log 中的 Stack Trace 直接猜測修復方案。

3. 非破壞性修復規則 (Non-Destructive Remediation Rule)
適用情境：發現設定錯誤或環境變數缺失需要修復時。

具體 Rule 描述：

Trigger: Agent 判定需要修改伺服器上的設定檔以解決部署失敗。

Action: 任何修改動作前必須先進行備份，且修改後必須具備回滾 (Rollback) 邏輯。

What to do: 

執行修改前使用 `cp config.yaml config.yaml.bak_{timestamp}`。

優先使用 `sed` 或專門的 CLI 工具修改配置，而非重新覆蓋整個檔案。

若缺少 `.env` 檔案或環境變數不完整，請使用者自行調整。

What NOT to do: 

禁止直接刪除現有的設定檔或目錄（如 `rm -rf`）。

禁止在沒有備份的情況下修改 `.env` 檔案。

禁止複製本機的 `.env` 檔案。

4. 資源與權限邊界規則 (Resource & Permission Boundary Rule)
適用情境：診斷權限不足或效能瓶頸引起的失敗。

具體 Rule 描述：

Trigger: 錯誤日誌顯示 Permission denied 或 Out of memory。

Action: 僅檢查與該服務直接相關的權限與資源，禁止提升至全域 Root 權限進行暴力破解。

What to do: 

使用 `ls -l` 檢查特定檔案的 Owner 與 Mode。

使用 `free -m` 或 `top` 檢查當前系統資源負載。

What NOT to do: 

禁止對任何目錄執行 `chmod 777`。

禁止隨意殺掉（`kill -9`）非目標服務的其他系統進程。

5. 終止與升級回報規則 (Termination & Escalation Rule)
適用情境：多次修復嘗試無效時。

具體 Rule 描述：

Trigger: 對同一錯誤嘗試修復超過 3 次，或遇到無法解析的二進制損壞。

Action: 停止自動修復循環，保留現場日誌，並產生完整的診斷報告提交給人類工程師。

What to do: 

彙整已嘗試過的修復指令 (Attempted Fixes)。

輸出最後一次失敗的完整 Context。

What NOT to do: 

禁止進入無限次的 Fix-Restart-Fail 循環（Infinite Loop）。

禁止在無法修復時直接顯示「部署成功」以敷衍系統。