# 本地 RAG Agent 收敛 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 完成受限本地知识库 RAG Agent 的可用链路、可解释轨迹、范围收敛、质量验证与面试交付物。

**Architecture:** RAG API 透传检索和生成指标；Agent 通过四个受限本地工具编排；Web Scraper 只移除运行时，不删除历史数据表；新迁移只清理 OpenClaw 表。

**Tech Stack:** FastAPI、SQLAlchemy/Alembic、LangChain、DashScope、Chroma、Vue 3、TypeScript、Pinia、Vitest、pytest。

## Global Constraints

- 只使用 DashScope 在线 LLM/Embedding 与本地 Chroma；禁止外网检索、Shell、通用 HTTP 工具。
- 保留 009 历史迁移；新迁移只删除 OpenClaw 表和索引。
- 移除 Web Scraper API、前端入口、服务和测试，但不删除已有 Web Scraper 表。
- 每个行为变更必须先写失败测试。
- Agent 工具限定为 query_rewriter、knowledge_base_search、context_selector、citation_validator。

---

### Task 1: 修复 Agent 参数链路和 RAG 指标合同

**Files:**
- Modify: backend/app/langchain_integration/agent_executor.py
- Modify: backend/app/api/v1/rag.py
- Modify: backend/app/schemas/knowledge_base.py
- Modify: backend/tests/test_agent_executor.py
- Modify: backend/tests/test_rag_endpoints.py

**Interfaces:**
- AgentManager.execute_task 接收 knowledge_base_ids: Optional[List[int]]。
- RAGQueryResponse 和 SSE sources/done 事件包含 retrieval_time_ms、generation_time_ms。

- [ ] Step 1: 写失败测试。调用 agent_manager.execute_task('问题', knowledge_base_ids=[1])，断言完成状态和工具授权范围；让 RAG stub 返回 retrieval_time_ms=12.5、generation_time_ms=34.5，断言非流式 body 和 SSE done 均保留指标。
- [ ] Step 2: 运行 pytest backend/tests/test_agent_executor.py backend/tests/test_rag_endpoints.py -v，确认 Agent 因参数不被接收、指标因未透传失败。
- [ ] Step 3: 给 AgentManager.execute_task 增加 knowledge_base_ids 参数；扩展 RAGQueryResponse、query API 和 SSE sources/done 映射。
- [ ] Step 4: 重跑上述测试，预期全部通过。
- [ ] Step 5: 提交。git add 相关后端文件和测试；git commit -m "fix: complete Agent scope and RAG metrics"。

### Task 2: 收敛 Web Scraper 运行时并清理 OpenClaw 表

**Files:**
- Modify: backend/app/api/v1/__init__.py、backend/app/models/__init__.py
- Delete: backend/app/api/v1/web_scraper.py、backend/app/services/web_scraper、backend/app/models/web_scraper_task.py、backend/app/models/web_scraper_log.py
- Delete: frontend/src/views/web-scraper
- Modify: frontend/src/router/index.ts、frontend/src/layouts/DefaultLayout.vue
- Delete: backend/tests 中所有 test_web_scraper 专项测试
- Create: backend/migrations/versions/012_remove_openclaw_tables.py
- Create: backend/tests/migrations/test_remove_openclaw_tables.py

**Interfaces:**
- api_router 不注册 /web-scraper。
- 012 迁移在 upgrade 删除 openclaw_tools、openclaw_tool_calls 和索引；downgrade 根据 009 恢复；不删除 Web Scraper 表。

- [ ] Step 1: 写失败迁移测试，断言 upgrade 删除的表仅为两张 OpenClaw 表，且不包含 web_scraper_tasks；写路由测试，断言无 /web-scraper。
- [ ] Step 2: 运行 pytest backend/tests/migrations/test_remove_openclaw_tables.py -v，确认失败。
- [ ] Step 3: 新增 012 迁移；删除 Web Scraper 的运行时、菜单、页面和专项测试。
- [ ] Step 4: 运行 rg -n "web_scraper_router|/web-scraper" backend/app frontend/src，预期无匹配；重跑迁移测试通过。
- [ ] Step 5: 提交。git add -A；git commit -m "refactor: remove scraper runtime and clean OpenClaw tables"。

### Task 3: 实现四阶段受限 RAG Agent 与结构化轨迹

**Files:**
- Create: backend/app/services/rag/query_rewrite_service.py、context_selector_service.py、citation_service.py
- Create: backend/app/langchain_integration/tools/query_rewriter_tool.py、context_selector_tool.py、citation_validator_tool.py
- Modify: backend/app/langchain_integration/tools/__init__.py、backend/app/langchain_integration/agent_executor.py、backend/app/schemas/agent.py
- Create: backend/tests/services/test_query_rewrite_service.py、test_context_selector_service.py、test_citation_service.py
- Modify: backend/tests/test_agent_executor.py

**Interfaces:**
- QueryRewriteService.rewrite(question: str) -> str。
- ContextSelectorService.select(chunks: List[dict], max_chars: int) -> List[dict]。
- CitationService.validate(answer: str, chunks: List[dict]) -> dict，含 valid 和 missing_citation_ids。
- 执行记录含原始问题、改写查询、知识库范围、检索参数、原始和过滤片段、最终上下文、答案、引用校验、Token、检索/生成/总耗时。

- [ ] Step 1: 写失败测试：无需改写时返回原问题；上下文选择器按最高分和字符预算保留片段；答案引用未知编号时校验失败。
- [ ] Step 2: 运行 pytest backend/tests/services/test_query_rewrite_service.py backend/tests/services/test_context_selector_service.py backend/tests/services/test_citation_service.py -v，确认失败。
- [ ] Step 3: 实现三个纯服务和对应工具；Agent 内置工具固定为四项，移除 Calculator、DataAnalysis 和自定义工具执行入口；回调将 JSON 输出写入结构化 steps。
- [ ] Step 4: 运行 Agent 与服务测试，预期通过。
- [ ] Step 5: 提交。git add backend/app backend/tests；git commit -m "feat: add constrained RAG Agent workflow"。

### Task 4: 完整化 RAG Agent 调试台

**Files:**
- Modify: frontend/src/types/index.ts、frontend/src/stores/agent.ts、frontend/src/api/agent.ts、frontend/src/views/agent/AgentView.vue
- Create: frontend/src/__tests__/views/AgentWorkflowDebug.test.ts

**Interfaces:**
- 消费结构化 Agent steps、citation_validation 和 metrics。
- 展示知识库范围、Top-K、阈值、改写查询、检索片段、最终上下文、流式回答、引用校验、Token、检索/生成/总耗时。

- [ ] Step 1: 写失败 Vitest，用包含改写查询、最终上下文、通过的引用校验、128 Token、250 ms 总耗时的执行记录挂载页面并断言这些文本可见。
- [ ] Step 2: 运行 npm run test -- AgentWorkflowDebug.test.ts，确认失败。
- [ ] Step 3: 扩展类型和 Store；用可选知识库列表替代仅手工文本输入；按四阶段渲染时间线、来源卡片、上下文和指标卡。
- [ ] Step 4: 运行 npm run test -- AgentWorkflowDebug.test.ts agent.test.ts，预期通过。
- [ ] Step 5: 提交。git add frontend/src；git commit -m "feat: complete RAG Agent debug timeline"。

### Task 5: 向量删除一致性和 RAG 专项测试

**Files:**
- Modify: backend/app/services/rag/knowledge_base_service.py
- Create: backend/tests/services/test_knowledge_base_vector_cleanup.py
- Create: backend/tests/test_rag_sse_contract.py、test_rag_permissions.py、test_rag_resilience.py

**Interfaces:**
- KnowledgeBaseService.delete 在数据库删除前调用 VectorStoreManager.delete_collection(kb_id)。
- SSE 顺序为 sources、0..n token、done；失败则单个 error 结束。

- [ ] Step 1: 写失败测试：删除知识库后 mock vector store 的 delete_collection(1) 被调用；SSE sources 有 retrieval_time_ms 且 done 有 generation_time_ms。
- [ ] Step 2: 运行 pytest backend/tests/services/test_knowledge_base_vector_cleanup.py backend/tests/test_rag_sse_contract.py -v，确认失败。
- [ ] Step 3: 实现 collection 删除和 SSE 合同透传；补多知识库、权限隔离、DashScope 超时重试、引用完整性测试。
- [ ] Step 4: 运行上述专项测试，预期通过。
- [ ] Step 5: 提交。git add backend/app/services/rag backend/tests；git commit -m "test: cover RAG cleanup and resilience"。

### Task 6: 配置、评估与面试文档收敛

**Files:**
- Modify: backend/.env.example、backend/docker-compose.yml、backend/docker-compose.prod.yml
- Modify: backend/README.md、frontend/README.md、docs/部署文档.md、docs/测试文档.md
- Create: docs/rag-evaluation-dataset.jsonl、docs/RAG评估报告.md、docs/面试演示脚本.md、docs/系统架构图.md、docs/RAG数据流图.md
- Create: backend/tests/test_configuration_contract.py

**Interfaces:**
- 示例配置使用 LLM_PROVIDER=dashscope、LLM_MODEL=qwen-plus、EMBEDDING_PROVIDER=dashscope、EMBEDDING_MODEL=text-embedding-v3。
- 每行评估数据为 id、knowledge_base、question、expected_document_ids、expected_answer_points。

- [ ] Step 1: 写失败配置合同测试，读取 backend/.env.example 并断言 DashScope provider 与 text-embedding-v3。
- [ ] Step 2: 运行 pytest backend/tests/test_configuration_contract.py -v，确认失败。
- [ ] Step 3: 创建 20–50 条固定评估问题和报告，定义 Recall@K、Hit Rate、Faithfulness、Answer Relevancy、平均检索耗时、首 Token 延迟。
- [ ] Step 4: 更新 Docker、API、架构、测试和演示说明；移除文档中 OpenClaw/Web Scraper 的当前能力描述，只保留历史迁移说明。
- [ ] Step 5: 运行配置测试和 rg -n -i "openclaw|web scraper|网页采集" backend/README.md frontend/README.md docs/部署文档.md docs/测试文档.md，预期仅历史迁移说明匹配。
- [ ] Step 6: 提交。git add backend/.env.example backend/docker-compose.yml backend/docker-compose.prod.yml backend/README.md frontend/README.md docs backend/tests/test_configuration_contract.py；git commit -m "docs: complete RAG Agent evaluation and demo materials"。

## Plan Self-Review

- 六个任务覆盖 API 合同、运行时收敛、数据库迁移、四阶段 Agent、调试台、向量删除、测试、评估与文档。
- 每个任务包含文件、接口、失败测试、验证命令和提交步骤。
- 统一使用 knowledge_base_ids、retrieval_time_ms、generation_time_ms、citation_validation 命名。
