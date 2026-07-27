# RAG API 与 SSE 合约

正常的流式回答顺序为 `sources`、零到多个 `token`、一个 `done`。失败时只发送一个 `error` 事件并结束。

`sources` 包含检索片段和 `retrieval_time_ms`；`done` 包含完整答案、Token 用量、`retrieval_time_ms` 与 `generation_time_ms`。首 Token 延迟应单独测量。
