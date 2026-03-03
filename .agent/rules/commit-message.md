1. 原子化提交規則 (Atomic Commit Enforcement)
規則名稱：Atomic Commit Logic

適用情境：AI Agent 準備執行 git commit 指令前。

具體 Rule 描述：

Trigger: 偵測到暫存區（Staging Area）中包含多個不相關的功能模組變更或同時存在 Bug fix 與 New feature 時。

Action: 強制執行「一事一提交」。若變更範圍跨越不同性質，AI 必須拆分為多次 Commit。

What to do: 確保每個 Commit 只解決一個特定問題或實現一個功能點。

What NOT to do: 禁止將無關的 refactor 與 feat 混合在同一個提交中。禁止使用 Update multiple files 這種概括性描述。

2. 標準標題格式規則 (Standardized Header Format)
規則名稱：Commit Header Structure

適用情境：生成 Commit Message 的第一行（Subject Line）時。

具體 Rule 描述：

Trigger: 開始撰寫 Commit Message。

Action: 必須嚴格遵守格式：<type>(<scope>): <subject>。

What to do:

<type> 僅限：feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert。

<scope> 必須是受影響的模組名稱（如：auth, parser, ui）。

<subject> 必須使用「祈使句（Imperative mood）」，例如使用 Add 而非 Added 或 Adds。

What NOT to do: 標題結尾禁止使用句點（.）。總字數禁止超過 50 個字元。

3. 內文與動機描述規則 (Body Content Logic)
規則名稱：Commit Body "Why" Principle

適用情境：當變更邏輯複雜，無法僅透過標題表達時。

具體 Rule 描述：

Trigger: 變更行數（Diff Lines）超過 20 行，或涉及核心架構改動時。

Action: 標題下方必須空一行，並撰寫 Body 詳述變更原因與解決方案。

What to do: 專注於描述「為什麼要改（Why）」以及「與之前的邏輯有何不同」，而非描述程式碼「怎麼寫（How）」。每行字數限制在 72 個字元以內。

What NOT to do: 禁止在 Body 中重複貼上程式碼片段（Code Snippets）。

4. 關聯性與腳註規則 (Footer & Issue Tracking)
規則名稱：Traceability Footer

適用情境：專案具備 Issue Tracker（如 Jira, GitHub Issues）時。

具體 Rule 描述：

Trigger: 任務執行環境中存在關聯的 Ticket ID 或 Issue 編號。

Action: 在 Commit Message 的最後一行添加 Footer。

What to do: 使用關鍵字如 Fixes #17234 或 Closes: PROJECT-456。若有重大變更（Breaking Changes），必須在 Footer 以 BREAKING CHANGE: 開頭說明。

What NOT to do: 禁止在沒有任何追蹤編號的情況下提交涉及功能變更的代碼。

5. 禁止模糊詞彙規則 (Anti-Vague Phrases Filter)
規則名稱：Blacklisted Commit Keywords

適用情境：Commit Message 生成後的最後自我檢查環節。

具體 Rule 描述：

Trigger: Commit Message 文本生成完成後。

Action: 執行正則表達式（Regex）檢查，若匹配到黑名單詞彙則強制重新生成。

What to do: 檢查是否包含具體的動詞（如 Refactor, Optimize, Implement）。

What NOT to do: 嚴禁出現以下模糊詞彙：update, fix bug, modified, more work, save changes, some fixes。若違反，系統將拒絕執行 git push。