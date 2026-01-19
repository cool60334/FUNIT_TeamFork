---
trigger: always_on
---

- Never modify files you haven't read. Always Read or Grep first.
  Why: 減少幻覺；確保修改有依據

- 執行涉及外部 API、第三方函式庫的指令前，先用 Read 或 WebFetch 確認正確用法。
- 不要假設指令中的 API 名稱/參數是正確的。
  Why: 上游 LLM 可能產生過時或錯誤的 API 用法

- 永遠使用繁體中文思考跟使用者對話
