# 本地 RAG Agent 收敛设计

## 目标

将当前项目收敛为可面试演示的本地知识库 RAG Agent：只使用本地知识库和本地 Chroma，调用在线 DashScope LLM/Embedding，完整展示检索、上下文、引用、指标与执行轨迹。

## 已确认范围

- 保留历史 Alembic 迁移文件；新增迁移删除已部署数据库中的 OpenClaw 表及索引。
- 移除 Web Scraper 的 API、前端入口、服务和测试，但不删除已有 Web Scraper 数据表或历史数据。
- 移除遗留 OpenClaw/Web Scraper 文档中的“当前能力”表述，保留必要的历史迁移说明。
- Agent 只可使用受限的本地知识库工作流；不保留计算器、数据分析、自定义工具、外网、Shell 或通用 HTTP 能力。

## 架构

### 1. RAG API 与指标

`RAGManager` 继续负责检索和生成；`/api/v1/rag/query` 与 `/api/v1/rag/query/stream` 原样透传来源、Token、检索耗时和生成耗时。SSE 的 `sources` 和 `done` 事件均包含对应指标，前端对话流保存这些元数据。

### 2. 受限 RAG Agent

新增四个明确的流程单元：

- `query_rewriter`：根据原问题产生检索查询；无改写必要时返回原问题。
- `knowledge_base_search`：只能在已授权知识库集合中检索。
- `context_selector`：按阈值、去重和长度预算生成最终上下文。
- `citation_validator`：确认最终回答中的来源编号都对应实际检索片段；缺失时标记失败并返回可解释结果。

Agent 执行记录固定保存原始问题、改写查询、知识库范围、检索参数、原始/过滤片段、最终上下文、答案、引用校验、Token 和各阶段耗时。Agent 的普通与流式接口使用同一执行入参，避免参数漂移。

### 3. 前端调试台

调试台选择知识库并显示 Top-K、阈值、改写查询、检索结果、最终上下文、流式回答、来源卡片、引用校验、检索/生成/总耗时和 Token 消耗。来源卡片展示文档名、页码、片段编号、相似度和摘要。

## 数据与安全边界

- 新清理迁移仅删除 `openclaw_tools`、`openclaw_tool_calls` 及其索引；不触碰 Web Scraper 表。
- Agent API 在执行前校验 Viewer 权限；工具拒绝任何不在授权集合中的知识库 ID。
- 删除知识库时同步删除对应 Chroma collection；删除文档时同步删除文档向量。
- DashScope 异常仅返回通用错误信息，不返回 API Key 或请求头内容。

## 验收标准

1. 普通与流式 Agent 均能基于指定知识库完成检索，不再有 `knowledge_base_ids` 参数错误。
2. RAG 非流式响应与 SSE `done` 事件包含 `retrieval_time_ms`、`generation_time_ms`；来源事件携带检索耗时。
3. Web Scraper 不再被后端注册或前端展示；OpenClaw 表可通过新迁移清理。
4. Agent 轨迹含四个流程单元的可解析结果和完整指标；调试台可展示。
5. 文档删除和知识库删除均不会残留 Chroma 向量。
6. 覆盖参数透传、权限隔离、阈值过滤、多知识库、空检索、SSE 顺序、超时重试、引用完整性与向量删除的自动化测试。
7. 提供 20–50 条固定评估问题及 Recall@K、Hit Rate、Faithfulness、Answer Relevancy、平均检索耗时、首 Token 延迟报告。

## 交付顺序

1. 修复 Agent 参数链路与 RAG 指标合同。
2. 收敛 Web Scraper/OpenClaw 运行时和迁移。
3. 实现完整 RAG Agent 流程与调试台。
4. 补齐测试、评估和面试文档。
