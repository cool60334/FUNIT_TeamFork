1. 獨立分支強制規範 (Branch Isolation Rule)

適用情境：接收到任何 Feature Request、Bug Fix 或 Refactor 指令時。

Trigger: `ON receive_task` AND `branch == "main"`

具體 Rule 描述：

What to do: 必須先從 main 分支切換出新分支。分支命名格式須符合 `type/task-description` (e.g., `feat/auth-module` 或 `fix/memory-leak`)。

What NOT to do: 禁止在 main 或 master 分支下執行任何 git commit 或代碼寫入操作。

Action: `git checkout -b <new_branch_name>`

2. 主線寫入保護 (Main Branch Write Protection)

適用情境：Agent 試圖儲存變更至程式庫時。

Trigger: `BEFORE file_save` AND `current_branch == "main"`

具體 Rule 描述：

What to do: 偵測到當前分支為主線時，自動攔截寫入行為，並提示用戶「禁止直接操作主線」。

What NOT to do: 禁止使用 `--force` 參數強行推送到受保護分支。

Constraint: `ERROR_CODE: BRANCH_PROTECTED.` 指令必須轉向至工作分支。

3. 壓縮合併執行規範 (Squash Merge Enforcement)

適用情境：開發完成並準備將變更合併回主線時。

Trigger: `ON merge_request` OR `ON task_completion`

具體 Rule 描述：

What to do: 必須執行 `merge --squash`。將工作分支的所有 Commit 壓縮為一個原子化（Atomic）的 Commit。

What NOT to do: 嚴禁執行標準 `git merge` 或 `rebase`（除非內部開發流程有特殊規定），避免將中間測試過程的碎裂 Commit 帶入主線。

Action: `git checkout main && git merge --squash <feature_branch>`

4. 原子化 Commit 訊息重構 (Atomic Commit Documentation)

適用情境：在執行 Squash Merge 後的最後一次 Commit。

Trigger: `AFTER git_merge_squash`

具體 Rule 描述：

What to do: 參考並遵守commit-message.md 的規範，撰寫結構化的 Commit Message。

What NOT to do: 禁止使用 `Merged branch...` 等自動產生的預設模糊訊息。

Constraint: Commit Message 必須包含至少一個關聯的 Task ID 或 Ticket Number。

5. 環境清理與分枝生命週期管理 (Post-Merge Cleanup)

適用情境：成功合併至主線並驗證通過後。

Trigger: `AFTER main_branch_push_success`

具體 Rule 描述：

What to do: 確認合併成功後，必須立即刪除本地與遠端的功能分支（Feature Branch），保持 Repository 整潔。

What NOT to do: 禁止保留已合併（Merged）的分支，避免造成 Stale Branches 堆積。

Action: `git branch -D <feature_branch>` AND `git push origin --delete <feature_branch>`