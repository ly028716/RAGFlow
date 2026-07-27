# 文档处理可靠性 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 FastAPI 内置后台任务中提供文档处理状态、有限重试、查询与健康统计。

**Architecture:** 上传服务持久化处理任务并投递 `BackgroundTasks`；处理服务负责状态机和重试；API 负责权限与序列化。启动时中断遗留任务，不自动恢复。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、pytest、MySQL。

## Global Constraints

- 不引入 Celery、Redis 队列或独立 Worker。
- 服务重启仅标记 `queued`/`running` 任务为 `interrupted`。
- 瞬时错误最多三次指数退避；格式/校验错误直接失败。
- 所有任务读取和重试均经过知识库权限校验。

### Task 1: 持久化任务模型和迁移

**Files:**

- Create: `backend/app/models/document_processing_task.py`
- Create: `backend/app/repositories/document_processing_task_repository.py`
- Create: `backend/migrations/versions/013_add_document_processing_tasks.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/models/test_document_processing_task.py`

**Interfaces:** `DocumentProcessingTask` 包含 `queued/running/completed/failed/interrupted` 状态、阶段、进度、尝试次数、错误、阶段耗时和时间戳；仓储暴露创建、用户范围查询、阶段更新、完成、失败和中断方法。

- [ ] 写失败测试：创建任务默认 `queued`、`progress=0`、`max_attempts=3`；状态更新记录阶段耗时。
- [ ] 运行 `pytest backend/tests/models/test_document_processing_task.py -v`，预期因模型缺失失败。
- [ ] 实现模型、仓储、导出和 Alembic 迁移；为 `document_id`、`knowledge_base_id`、`status`、`created_at` 建索引。
- [ ] 重跑模型测试，预期通过。
- [ ] 提交：`git commit -m "feat: track document processing tasks"`。

### Task 2: 后台处理编排、重试和启动中断

**Files:**

- Create: `backend/app/services/rag/document_processing_service.py`
- Modify: `backend/app/services/rag/document_upload_service.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/services/test_document_processing_service.py`

**Interfaces:** `DocumentProcessingService.run(task_id: int) -> None`；`mark_incomplete_tasks_interrupted() -> int`。上传创建任务后投递 `run(task_id)`。

- [ ] 写失败测试：`TimeoutError` 后第二次嵌入成功时完成且尝试次数为 2；不支持格式错误立即失败；启动时 running 任务变 interrupted。
- [ ] 运行 `pytest backend/tests/services/test_document_processing_service.py -v`，预期失败。
- [ ] 实现固定流转 `queued → parsing → chunking → embedding → completed`，每阶段写进度和耗时；仅对 `TimeoutError`、连接错误指数退避重试。
- [ ] 上传服务创建任务并投递；lifespan 启动时标记遗留任务中断。
- [ ] 重跑服务测试，预期通过。
- [ ] 提交：`git commit -m "feat: orchestrate document processing"`。

### Task 3: 任务查询、手动重试和健康 API

**Files:**

- Create: `backend/app/api/v1/document_processing_tasks.py`
- Create: `backend/app/schemas/document_processing_task.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/api/v1/system.py`
- Test: `backend/tests/api/v1/test_document_processing_tasks.py`

**Interfaces:**

- `GET /document-processing-tasks`：知识库/文档/状态筛选和分页。
- `GET /document-processing-tasks/{task_id}`：阶段、进度、错误、尝试和耗时。
- `POST /document-processing-tasks/{task_id}/retry`：仅 `failed`/`interrupted` 且有权限的用户可重投。
- `GET /system/processing-health`：24 小时总数、成功率、失败数、平均时长、queued/running 数。

- [ ] 写失败 API 测试：他人无法读取或重试任务；失败任务可重试；完成任务不能重试；健康汇总正确。
- [ ] 运行 `pytest backend/tests/api/v1/test_document_processing_tasks.py -v`，预期路由缺失失败。
- [ ] 实现 Pydantic schema、权限范围服务方法、路由注册、重试投递和统计聚合。
- [ ] 重跑 API 测试，预期通过。
- [ ] 提交：`git commit -m "feat: expose processing task observability"`。

### Task 4: 端到端契约与运维文档

**Files:**

- Create: `backend/tests/test_document_processing_startup.py`
- Modify: `backend/README.md`
- Modify: `docs/部署文档.md`
- Modify: `docs/测试文档.md`

- [ ] 写失败测试：启动中断标记、任务健康统计和上传非阻塞处理。
- [ ] 运行所有新增测试：`pytest backend/tests/models/test_document_processing_task.py backend/tests/services/test_document_processing_service.py backend/tests/api/v1/test_document_processing_tasks.py backend/tests/test_document_processing_startup.py -v`。
- [ ] 写明重启不恢复、用户手动重试、三次重试限制及健康接口运维含义。
- [ ] 修复测试并重新运行；如果环境依赖阻塞，执行 `py_compile`、静态检查并在报告中记录。
- [ ] 提交：`git commit -m "docs: document processing reliability operations"`。

## Plan Self-Review

- 持久化、状态机、重试、重启中断、权限 API、健康统计、测试和文档均有对应任务。
- 无 TBD、TODO 或未定义接口。
- 后续任务只依赖前置任务明确定义的 `DocumentProcessingTask`、仓储和处理服务接口。
