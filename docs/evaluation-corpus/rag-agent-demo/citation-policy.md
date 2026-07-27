# 引用策略

答案中的事实应带有检索片段的引用。引用 ID 由 `document_id` 和 `chunk_index` 组成，格式为 `[citation:<document_id>:<chunk_index>]`，用来支持可追溯和校验。

当答案引用了最终上下文中不存在的片段时，`citation_validator` 返回 `valid=false`，并在 `missing_citation_ids` 中列出未知编号。
