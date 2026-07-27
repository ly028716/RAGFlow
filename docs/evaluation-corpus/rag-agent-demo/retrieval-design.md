# 检索设计

`knowledge_base_search` 只搜索当前用户被授权的 `knowledge_base_ids`。Top-K 限制候选片段数量，相似度阈值过滤低相关候选；两者共同平衡召回与上下文噪声。

候选会按 `document_id` 去重，以避免同一文档重复占用上下文并提升来源多样性。高相关的片段进入上下文选择阶段。
