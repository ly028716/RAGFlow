# 文档处理可靠性设计

## 目标

在不引入外部 Worker 的前提下，为本地知识库的文档解析、切分和向量化流程提供可追踪、有限重试和可观测能力。任务由 FastAPI `BackgroundTasks` 执行；服务重启后不自动恢复运行中的任务。

## 边界

- 覆盖上传后的文档处理链路，不改变 RAG 查询和 Agent 工作流。
- 使用 MySQL 持久化任务状态；不引入 Celery、Redis 队列或独立 Worker。
- 不承诺进程重启后的自动续跑；将未完成任务标识为 `interrupted`，由用户手动重试。

## 数据模型

新增 `DocumentProcessingTask`，关联 `knowledge_base_id`、`document_id` 和创建人。字段包括：

- `status`：`queued`、`running`、`completed`、`failed`、`interrupted`。
- `stage`：`queued`、`parsing`、`chunking`、`embedding`、`completed`、`failed`、`interrupted`。
- `progress`（0–100）、`attempt_count`、`max_attempts`（默认 3）。
- `error_message`、`error_type`、`task_id`。
- `started_at`、`completed_at`、`created_at`、`updated_at`，以及解析、切分、向量化耗时字段。

任务只表达一次文档处理尝试的当前状态；重试接口复用原任务记录并增加 `attempt_count`，以保留完整可审计历史。

## 执行流

1. 上传接口创建文档和处理任务，状态为 `queued`，随后注册 `BackgroundTasks`。
2. 后台处理服务将任务标记为 `running`，依次执行 `parsing`、`chunking`、`embedding`。
3. 每个阶段完成时更新进度、阶段耗时和结构化日志上下文（`task_id`、`document_id`、`knowledge_base_id`）。
4. 处理成功后写入 `completed`、`completed_at` 和 100% 进度。
5. 仅对明确的瞬时基础设施异常进行指数退避重试，最多三次。文件格式、校验和权限类确定性错误立即标记为 `failed`。
6. 应用启动时，将遗留的 `queued` 或 `running` 任务标记为 `interrupted`，不自动重投。

## API

- `GET /document-processing-tasks`：按知识库、文档、状态筛选并分页查询当前用户任务。
- `GET /document-processing-tasks/{task_id}`：返回任务阶段、进度、尝试次数、错误和耗时。
- `POST /document-processing-tasks/{task_id}/retry`：仅允许任务创建人对 `failed` 或 `interrupted` 任务重试。
- `GET /system/processing-health`：返回近 24 小时任务数、成功率、失败数、平均时长及当前 queued/running 数。

所有读取和重试均复用知识库权限校验，不能通过任务 ID 越权读取其他用户的文档处理信息。

## 错误处理

- 后台任务内部捕获异常并持久化失败状态，不让异常影响 HTTP 上传响应。
- 重试期间仍保留最近一次错误摘要；重试耗尽后保留最终错误类型和消息。
- 向量化阶段失败不会删除已上传文件或已有文档记录，用户可直接调用重试接口。
- 未知异常按瞬时错误处理一次后失败，避免无限循环。

## 测试与验收

- 单元测试：状态流转、阶段进度、瞬时错误重试、确定性错误不重试、失败/中断任务重试。
- API 测试：权限隔离、筛选分页、重试投递和健康统计。
- 启动测试：遗留运行中任务被标记为 `interrupted`。
- 验收：上传响应不阻塞长处理；用户能查询准确进度和失败原因；失败文档可手动重试；健康接口反映 24 小时汇总。

## 非目标

- 不提供跨进程任务调度、自动故障恢复或分布式并发控制。
- 不新增前端管理页面；现有前端可在后续迭代消费任务 API。
