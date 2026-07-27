# RAGFlow 后端：受限本地知识库 RAG Agent

本服务用于展示一个面向 AI Agent 岗位面试的 RAG 项目：文档和向量索引保留在本地，LLM 与 Embedding 均通过 DashScope 在线调用。它不提供外部网页搜索、通用 HTTP 调用或任意自定义工具执行。

## 运行链路

1. 上传文档、解析和切分后，使用 DashScope `text-embedding-v3` 写入本地 Chroma。
2. 用户选择自己有权限的知识库并发起问题。
3. Agent 固定执行四个阶段：`query_rewriter`、`knowledge_base_search`、`context_selector`、`citation_validator`。
4. DashScope `qwen-plus` 基于筛选后的本地上下文流式生成答案；SSE 和执行记录返回来源、引用校验、Token 与耗时。

## 快速启动

```bash
cd backend
cp .env.example .env
# 编辑 .env：至少设置 DASHSCOPE_API_KEY 与 SECRET_KEY
docker compose up -d
docker compose exec backend alembic upgrade head
```

开发模式：

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

接口文档：<http://localhost:8000/docs>；健康检查：<http://localhost:8000/api/v1/system/health>。

## 模型配置契约

项目只接受 DashScope 提供商。不要改为本地模型或其他云厂商；启动时非 `dashscope` 的提供商会被配置校验拒绝。

```dotenv
DASHSCOPE_API_KEY=your-dashscope-api-key
LLM_PROVIDER=dashscope
LLM_MODEL=qwen-plus
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v3
```

`TONGYI_MODEL_NAME` 仅作为旧部署环境的兼容别名，新的配置和部署示例应使用 `LLM_MODEL`。

## 关键 API

- `POST /api/v1/knowledge-bases`：创建知识库；删除知识库时同步清理同名 Chroma collection。
- `POST /api/v1/rag/query` 与 `POST /api/v1/rag/query/stream`：本地知识库检索和回答。`sources`/`done` 事件包含检索、生成耗时。
- `POST /api/v1/agent/execute` 与对应流式端点：执行四阶段受限 RAG Agent，并保存可解释执行轨迹。

所有知识库、文档与查询均按当前用户授权范围隔离。不要将 API 密钥、数据库密码或生产 `.env` 提交到仓库。

## 测试与评估

```bash
cd backend
pytest tests/test_configuration_contract.py -v
pytest tests/test_agent_executor.py tests/test_rag_sse_contract.py -v
```

完整测试策略见 [../docs/测试文档.md](../docs/测试文档.md)。固定评测集、评分口径和报告模板见 [../docs/RAG评估报告.md](../docs/RAG评估报告.md)。

## 迁移说明

`012_remove_openclaw_tables` 仅用于清理历史遗留的两张集成表。`009` 至 `011` 迁移文件必须保留，且 `010`/`011` 的历史 Web Scraper 表与数据不会由 `012` 删除；它们不代表当前产品能力。
