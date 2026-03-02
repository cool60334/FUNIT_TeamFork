1. 環境初始化規範 (Project Bootstrapping)
規則名稱: DOCKER_AUTO_INIT

適用情境: 當 AI 偵測到新專案建立、或是既有專案缺乏容器設定時。

具體 Rule 描述:

Trigger: 專案目錄內缺少 Dockerfile 或 docker-compose.yml。

Action: 自動分析技術棧（如 Node.js, Python, Go），並生成對應的 Docker 配置檔案，嚴禁手動安裝依賴於宿主機。

What to do: 優先生成一個基本的 .dockerignore 檔案，排除 node_modules、.git、.env 等。

確保 docker-compose.yml 包含 restart: unless-stopped 策略。

What NOT to do: 禁止在未建立 Docker 設定的情況下要求使用者執行 npm install 或 pip install。

2. 數據持久化與磁碟卷期規範 (Data Persistence)
規則名稱: NAMED_VOLUME_ENFORCEMENT

適用情境: 定義資料庫、緩存、上傳資料夾或日誌服務時。

具體 Rule 描述:

Trigger: docker-compose.yml 中涉及 volumes 定義。

Action: 必須使用 Named Volumes 管理持久化數據。

What to do: 使用頂層 volumes 宣告，例如 db_data: {}。僅在「開發模式」下的原始碼同步（Source Code Sync）才允許使用 Host Bind Mounts（如 ./src:/app/src）。

What NOT to do: 嚴禁將數據庫路徑對應到宿主機路徑，例如:./mysql_data:/var/lib/mysql (Prohibited)。嚴禁在未宣告頂層 Volume 的情況下使用匿名卷。

3. 容器安全性與權限規範 (Container Security)
規則名稱: NON_ROOT_SECURITY

適用情境: 撰寫或修改 Dockerfile 時。

具體 Rule 描述:

Trigger: 生成 Dockerfile 的最後執行階段。

Action: 強制建立一個非 root 使用者並切換權限。

What to do: 使用 `RUN groupadd -r appuser && useradd -r -g appuser appuser`。使用 USER appuser 指令。確保 WORKDIR 的權限已正確賦予該使用者。

What NOT to do: 嚴禁以預設的 root 使用者啟動應用程序。嚴禁在 Dockerfile 中執行 chmod 777 這種不安全的權限分配。

4. 環境配置移植規範 (Environment Portability)
規則名稱: RELATIVE_PATH_PORTABILITY

適用情境: 在 docker-compose.yml 中引用外部配置或環境變數時。

具體 Rule 描述:

Trigger: 定義 env_file 或 build context。

Action: 強制使用相對路徑，並優先依賴 Docker Compose 的自動加載機制。

What to do: 使用 `env_file: .env` 或是直接依賴預設的 .env。使用 `context: .` 表示當前目錄。

What NOT to do: 嚴禁出現任何形式的絕對路徑，如 /home/user/project/.env。嚴禁在 docker-compose.yml 中硬編碼（Hardcode）敏感資訊（如 API Keys）。

5. 效能與構建優化規範 (Build Efficiency)
規則名稱: MULTI_STAGE_OPTIMIZATION

適用情境: 任何需要編譯（Build）的應用程序（如 Java, Go, TypeScript）。

具體 Rule 描述:

Trigger: 偵測到編譯型語言或需要構建 Artifacts 的前端專案。

Action: 強制實施 Multi-stage builds。

What to do: 第一階段（Build stage）安裝編譯工具。第二階段（Runtime stage）僅複製編譯後的二進位檔或靜態檔案，並使用 Alpine 或 Distroless 等輕量化 Base Image。

What NOT to do: 禁止將編譯工具（如 gcc, git, node-gyp）保留在最終發佈的 Image 中。

6. 自動錯誤診斷與自癒規範 (Failure Diagnostics)
規則名稱: DEPLOYMENT_FAILURE_RECOVERY

適用情境: 當 AI 執行 docker-compose up 失敗或容器進入 CrashLoopBackOff 狀態時。

具體 Rule 描述:

Trigger: 命令回傳非 0 狀態碼 (Exit code != 0) 或容器 Health Check 失敗。

Action: 必須依序執行標準化診斷流程，並根據錯誤日誌修正設定。

What to do: 
1. 執行 `docker-compose config` 驗證語法。
2. 執行 `docker-compose logs --tail=50 <service_name>` 抓取啟動錯誤。
3. 檢查 .env 檔案中是否缺失了必要的環境變數。
4. 自動檢查宿主機 Port 是否被佔用。

What NOT to do: 禁止在未查看日誌（Logs）的情況下重複嘗試相同的部署指令。禁止直接刪除所有 Volumes 作為首選重置手段。