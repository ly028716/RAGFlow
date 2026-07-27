# 架构总览

RAGFlow 将用户、知识库、文档和执行轨迹存储在 MySQL，将向量索引存储在本地 Chroma。模型推理和嵌入通过 DashScope 在线完成，因此文档向量保留在本地而模型能力不需要本地部署。

前端通过 HTTP/SSE 调用 FastAPI。Redis 用于缓存、限流和任务状态。
