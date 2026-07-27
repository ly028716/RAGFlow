# 受限 Agent 工作流

RAG Agent 固定执行四个工具：`query_rewriter`、`knowledge_base_search`、`context_selector`、`citation_validator`。不允许自定义工具、外部搜索或通用 HTTP 工具进入该工作流。

查询改写的输入是原始问题，输出是便于检索的查询；若没有必要改写，则返回原始问题。
