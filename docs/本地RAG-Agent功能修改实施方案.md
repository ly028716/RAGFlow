# 本地 RAG Agent 功能修改实施方案

## 1. 文档目的

本文档用于指导 RAGFlow 从“多功能 RAG + OpenClaw 集成平台”收敛为“面向 AI Agent 岗位面试的本地知识库 RAG Agent 项目”。

本方案采用以下边界：

- 文档、元数据和向量索引本地持久化。
- LLM 使用在线 DashScope / Qwen 模型。
- Embedding 使用在线 DashScope Embedding 模型。
- 保留 RAG Agent、会话、权限、配额、限流和可观测能力。
- 移除 OpenClaw 及与本地知识库主流程无关的外部工具集成。

## 2. 目标与非目标

### 2.1 目标

最终项目应能完整演示以下链路：

```text
文档上传 → 文本解析 → 文档切分 → 在线 Embedding → 本地 Chroma
    → 查询改写 → 知识库检索 → 相似度过滤 → 在线 LLM 流式回答
    → 引用来源 → 会话持久化 → 检索和生成指标记录
```

项目的面试展示重点为：

1. RAG 数据处理和检索链路。
2. Agent 对检索工具的编排和执行轨迹。
3. 答案引用与可解释性。
4. 检索质量评估和性能指标。
5. 清晰的分层架构、测试和部署方式。

### 2.2 非目标

本阶段不实现以下能力：

- OpenClaw Gateway、OpenClaw 工具和工具调用记录。
- 飞书集成。
- Web Scraper 和外部网页采集。
- 外部搜索、天气、通用 HTTP API、文件操作等工具。
- 多租户、插件市场和复杂工作流编排。
- 完全离线的 LLM 或 Embedding 模型。

## 3. 目标架构

```text
Vue 3 前端
    ↓ HTTP / SSE
FastAPI API 层
    ↓
Conversation Service / RAG Agent Service
    ├── Query Rewrite
    ├── Retrieval Tool
    ├── Similarity Filter
    ├── Context Builder
    ├── Online LLM Provider
    └── Citation Validator
    ↓
MySQL：用户、知识库、文档、会话、消息、执行记录
Redis：缓存、限流、Token 黑名单、任务状态
Chroma：本地向量集合
DashScope：LLM 和 Embedding
```

## 4. 实施阶段

## Phase 1：移除 OpenClaw 运行时依赖

### 4.1 后端修改

删除或停止注册以下运行时模块：

```text
backend/app/api/v1/openclaw.py
backend/app/core/openclaw_client.py
backend/app/models/openclaw_tool.py
backend/app/models/openclaw_tool_call.py
backend/app/repositories/openclaw_tool_repository.py
backend/app/repositories/openclaw_tool_call_repository.py
backend/app/schemas/openclaw.py
backend/app/services/openclaw_tool_service.py
```

修改以下文件：

- `backend/app/api/v1/__init__.py`：移除 OpenClaw 路由注册。
- `backend/app/api/v1/chat.py`：删除 enhanced/OpenClaw 分支，统一分发普通对话和 RAG 对话。
- `backend/app/services/enhanced_conversation_service.py`：改造为纯 RAG 编排服务，或由新的 `RagConversationService` 替代。
- `backend/app/models/__init__.py`：移除 OpenClaw 模型导出。
- `backend/app/config.py`：删除 `OpenClawSettings` 及对应配置读取。
- `backend/docker-compose.yml`、`backend/docker-compose.prod.yml`：删除 `OPENCLAW_*` 环境变量。
- `backend/scripts/init_builtin_tools.py`、`backend/scripts/seed_openclaw_tools.py`：删除或改为 RAG 工具初始化脚本。

数据库迁移策略：

- 不删除已经提交的 `009_add_openclaw_tools_tables.py`，保留迁移历史完整性。
- 如果现有数据库已创建 OpenClaw 表，新增 cleanup migration 删除表和索引。
- 后续新环境不再创建 OpenClaw 相关表。

### 4.2 前端修改

删除或移除引用：

```text
frontend/src/api/openclaw.ts
frontend/src/stores/openclaw.ts
frontend/src/components/OpenClawStatus.vue
frontend/src/components/DegradationBanner.vue
frontend/src/__tests__/stores/openclaw.spec.ts
frontend/src/__tests__/stores/openclaw-backoff.spec.ts
frontend/src/__tests__/components/OpenClawStatus.spec.ts
```

同步修改：

- `frontend/src/stores/index.ts`：移除 OpenClaw store 导出。
- `frontend/src/layouts/DefaultLayout.vue`：移除 OpenClaw 状态区域。
- `frontend/src/views/chat/ChatView.vue`：移除 enhanced 模式和 OpenClaw 提示。
- `frontend/src/router/index.ts`：保留知识库、聊天和 RAG Agent 路由，移除无关入口。

### 4.3 Phase 1 验收标准

- `rg -i "openclaw" backend/app frontend/src` 不再返回运行时代码引用。
- 后端可以在没有 OpenClaw Gateway 的情况下启动。
- 前端可以完成构建。
- 普通聊天、知识库聊天、登录和文档管理功能不受影响。
- OpenClaw 历史测试不再被默认测试套件加载。

## Phase 2：收敛 RAG 主链路

### 5.1 服务边界

新增或整理 `backend/app/services/rag/` 下的服务：

```text
rag_conversation_service.py  # 对话编排和 SSE 输出
retrieval_service.py         # 检索、过滤、去重和排序
document_ingestion_service.py# 解析、切分和索引
citation_service.py          # 来源整理和引用校验
```

API 层只负责请求校验和响应封装，不直接调用 Repository 或向量库。

### 5.2 检索流程

统一实现以下流程：

```text
接收问题
  → 可选查询改写
  → Chroma top_k 检索
  → distance 转 similarity
  → similarity_threshold 过滤
  → 按 document_id 去重
  → 保留高分片段
  → 构建上下文
  → 调用 DashScope LLM
```

必须处理以下边界：

- 知识库 ID 为空。
- 知识库不存在或无访问权限。
- 知识库没有已索引文档。
- 所有结果低于相似度阈值。
- DashScope 超时或返回错误。
- SSE 客户端中途断开。

### 5.3 统一响应格式

RAG 非流式响应和 SSE `done` 事件应包含：

```json
{
  "answer": "...",
  "sources": [
    {
      "document_id": 1,
      "document_name": "架构设计.pdf",
      "chunk_index": 3,
      "similarity_score": 0.86,
      "content": "..."
    }
  ],
  "tokens_used": 420,
  "retrieval_time_ms": 80,
  "generation_time_ms": 1200
}
```

### 5.4 在线模型配置

沿用 `backend/app/core/llm.py` 和 `backend/app/core/vector_store.py`，统一配置为：

```env
LLM_PROVIDER=dashscope
LLM_MODEL=qwen-plus
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v3
DASHSCOPE_API_KEY=your-api-key
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.70
```

保留开发 Mock 模式，供单元测试和无 API Key 环境使用；生产环境必须禁止使用默认密钥。

### 5.5 Phase 2 验收标准

- 文档可完成解析、切分、Embedding 和 Chroma 写入。
- 查询结果会按照相似度阈值过滤。
- 回答能够返回来源文档和 chunk 信息。
- 无相关结果时不会将无关内容发送给 LLM。
- SSE 能够正确发送 `sources`、`token`、`done` 和 `error` 事件。
- 在线模型错误不会泄露 API Key。

## Phase 3：构建 RAG Agent

### 6.1 Agent 工具范围

只保留本地知识库相关工具：

```text
query_rewriter       # 查询改写
knowledge_base_search# 本地知识库检索
context_selector     # 上下文筛选
citation_validator   # 引用完整性检查
```

Agent 不访问外部网络，不执行任意 Shell，不调用未知 HTTP 地址。

### 6.2 Agent 执行记录

每次执行记录以下步骤：

1. 原始问题。
2. 改写后的查询。
3. 使用的知识库。
4. 检索参数。
5. 命中的文档片段。
6. 过滤后的片段。
7. LLM 生成结果。
8. 引用校验结果。
9. 总耗时和 Token 消耗。

### 6.3 前端 RAG Agent 调试台

将现有 Agent 页面改造成 RAG Agent 调试台，展示：

- 当前知识库。
- 查询改写结果。
- Top-K 和阈值。
- 检索片段及相似度。
- 最终上下文。
- 流式回答。
- 引用来源。
- 执行耗时和 Token 消耗。

## Phase 4：面试项目化完善

### 7.1 测试

补齐以下测试：

- 文档切分边界测试。
- 相似度转换和阈值过滤测试。
- 空检索结果测试。
- 多知识库检索测试。
- 权限隔离测试。
- 文档删除后向量删除测试。
- SSE 事件顺序测试。
- DashScope 超时和重试测试。
- 引用来源完整性测试。

### 7.2 RAG 评估集

准备 20～50 条固定问题，记录：

- Recall@K。
- Hit Rate。
- Answer Relevancy。
- Faithfulness。
- 平均检索耗时。
- 首 Token 延迟。

### 7.3 文档和演示

新增或更新：

- 项目 README。
- 系统架构图。
- RAG 数据流图。
- API 接口说明。
- 技术选型说明。
- RAG 评估报告。
- Docker 启动说明。
- 面试演示脚本。

推荐演示流程：

1. 创建知识库。
2. 上传一份项目架构文档。
3. 查看文档索引状态。
4. 提问一个文档内问题。
5. 展示检索片段、相似度和引用。
6. 提问一个文档外问题，展示拒答或降级。
7. 打开 RAG Agent 调试台，展示完整执行轨迹。

## 5. 关键文件变更清单

### 删除或停止注册

- OpenClaw API、Client、Model、Repository、Schema、Service。
- OpenClaw 前端 API、Store、组件和测试。
- OpenClaw Docker 配置和初始化脚本。

### 重点修改

- `backend/app/api/v1/chat.py`
- `backend/app/api/v1/__init__.py`
- `backend/app/config.py`
- `backend/app/langchain_integration/rag_chain.py`
- `backend/app/core/vector_store.py`
- `backend/app/core/llm.py`
- `backend/app/services/rag/`
- `frontend/src/views/chat/ChatView.vue`
- `frontend/src/views/knowledge/KnowledgeView.vue`
- `frontend/src/views/agent/AgentView.vue`
- `frontend/src/stores/knowledge.ts`
- `frontend/src/utils/fetch-stream.ts`

### 保留并强化

- `backend/app/models/knowledge_base.py`
- `backend/app/models/document.py`
- `backend/app/models/conversation.py`
- `backend/app/repositories/`
- `backend/migrations/`
- `backend/tests/`
- `frontend/src/__tests__/`

## 6. 风险与处理策略

| 风险 | 处理策略 |
| --- | --- |
| OpenClaw 删除导致导入错误 | 先全仓库搜索引用，再删除模块，最后运行导入检查 |
| 在线 API 不稳定 | 使用超时、重试、错误脱敏和开发 Mock |
| Embedding 模型变更导致维度不一致 | 固化模型配置，变更时创建新 Chroma collection |
| 低质量片段进入上下文 | 强制执行相似度阈值、去重和上下文长度限制 |
| 文档删除后向量残留 | 文档删除事务中同步删除 Chroma 向量 |
| 配额并发扣减不准确 | 在 Service 层使用事务和原子扣减策略 |
| 历史迁移被破坏 | 保留旧迁移，只新增清理迁移 |

## 7. 完成定义

本方案完成后，项目需要满足：

- 不依赖 OpenClaw 即可启动和运行。
- 在线 DashScope LLM 和 Embedding 可以通过环境变量配置。
- 知识库文档、Chroma 索引和业务元数据可本地持久化。
- RAG 回答具备来源引用和相似度信息。
- 低相关问题能够拒答或明确提示无相关资料。
- Agent 执行过程可视化、可追踪、可测试。
- 关键 RAG 链路具备单元测试、集成测试和评估数据。
- README、架构文档和 Docker 部署说明与实际代码一致。

## 8. 本轮补充实施记录

已补充专用知识库检索工具 `knowledge_base_search`，其特点如下：

- 仅访问本地 Chroma，不提供外部搜索、天气、HTTP 或文件操作能力。
- Agent 请求通过 `knowledge_base_ids` 指定授权检索范围，并在 API 层校验 Viewer 权限。
- 工具输出结构化引用数据，包括知识库 ID、文档 ID、片段序号、来源、相似度和内容。
- 未指定知识库范围时默认拒绝检索，避免跨库或越权访问。

RAG Agent 调试台已升级为引用时间线，展示 `tool_call`、`tool_result`、`answer` 三类事件，并呈现检索耗时、来源文档、页码、片段编号、相似度和内容摘要。
