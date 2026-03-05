# Phase 2: 浏览器自动化采集 - API接口规范

**文档版本**: v1.0
**创建日期**: 2026-03-04
**作者**: 架构师
**状态**: 待评审

---

## 1. 接口概述

### 1.1 基础信息

- **Base URL**: `/api/v1/scraper`
- **认证方式**: JWT Bearer Token
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

### 1.2 通用响应格式

#### 成功响应
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

#### 错误响应
```json
{
  "code": 4xx/5xx,
  "message": "错误描述",
  "detail": "详细错误信息"
}
```

### 1.3 通用错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 2. 数据模型

### 2.1 TaskResponse

```typescript
interface TaskResponse {
  id: number;
  name: string;
  description: string | null;
  url: string;
  url_pattern: string | null;
  knowledge_base_id: number;
  knowledge_base_name: string;  // 关联查询
  schedule_type: "once" | "cron";
  cron_expression: string | null;
  selector_config: SelectorConfig;
  scraper_config: ScraperConfig;
  status: "active" | "paused" | "stopped";
  last_run_at: string | null;  // ISO 8601
  next_run_at: string | null;  // ISO 8601
  created_by: number;
  created_by_name: string;  // 关联查询
  created_at: string;  // ISO 8601
  updated_at: string;  // ISO 8601
}
```

### 2.2 SelectorConfig

```typescript
interface SelectorConfig {
  title: string;  // 标题选择器
  content: string;  // 内容选择器
  author?: string;  // 作者选择器（可选）
  publish_date?: string;  // 发布日期选择器（可选）
  exclude?: string[];  // 排除选择器列表
}
```

### 2.3 ScraperConfig

```typescript
interface ScraperConfig {
  wait_for_selector: string;  // 等待的选择器
  wait_timeout: number;  // 等待超时时间（毫秒）
  screenshot: boolean;  // 是否截图
  user_agent?: string;  // User-Agent
  headers?: Record<string, string>;  // 自定义请求头
  retry_times: number;  // 重试次数
  retry_delay: number;  // 重试延迟（秒）
}
```

### 2.4 LogResponse

```typescript
interface LogResponse {
  id: number;
  task_id: number;
  status: "running" | "success" | "failed";
  start_time: string;  // ISO 8601
  end_time: string | null;  // ISO 8601
  pages_scraped: number;
  documents_created: number;
  error_message: string | null;
  execution_details: ExecutionDetails;
  created_at: string;  // ISO 8601
}
```

### 2.5 ExecutionDetails

```typescript
interface ExecutionDetails {
  urls_processed: string[];
  processing_time: {
    scraping: number;  // 秒
    processing: number;  // 秒
    storing: number;  // 秒
  };
  documents: Array<{
    title: string;
    url: string;
    document_id: number;
  }>;
  errors: string[];
}
```

---

## 3. API端点详细说明

### 3.1 创建采集任务

**端点**: `POST /api/v1/scraper/tasks`

**权限**: 需要认证，需要对目标知识库有写权限

**请求体**:
```json
{
  "name": "技术博客采集",
  "description": "采集技术博客文章到知识库",
  "url": "https://example.com/blog/article-1",
  "url_pattern": null,
  "knowledge_base_id": 1,
  "schedule_type": "once",
  "cron_expression": null,
  "selector_config": {
    "title": "h1.article-title",
    "content": "div.article-content",
    "author": "span.author-name",
    "exclude": [".advertisement", ".sidebar"]
  },
  "scraper_config": {
    "wait_for_selector": "div.article-content",
    "wait_timeout": 30000,
    "screenshot": false,
    "retry_times": 3,
    "retry_delay": 5
  }
}
```

**请求参数说明**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 任务名称，2-200字符 |
| description | string | 否 | 任务描述 |
| url | string | 是 | 目标URL，必须是有效的HTTP/HTTPS URL |
| url_pattern | string | 否 | URL匹配模式，支持通配符 |
| knowledge_base_id | integer | 是 | 目标知识库ID，必须存在且有权限 |
| schedule_type | string | 是 | 调度类型：once或cron |
| cron_expression | string | 否 | Cron表达式，当schedule_type=cron时必填 |
| selector_config | object | 是 | 选择器配置 |
| scraper_config | object | 是 | 采集器配置 |

**响应示例**:
```json
{
  "id": 1,
  "name": "技术博客采集",
  "description": "采集技术博客文章到知识库",
  "url": "https://example.com/blog/article-1",
  "url_pattern": null,
  "knowledge_base_id": 1,
  "knowledge_base_name": "技术文档库",
  "schedule_type": "once",
  "cron_expression": null,
  "selector_config": { ... },
  "scraper_config": { ... },
  "status": "active",
  "last_run_at": null,
  "next_run_at": null,
  "created_by": 1,
  "created_by_name": "张三",
  "created_at": "2026-03-04T10:00:00Z",
  "updated_at": "2026-03-04T10:00:00Z"
}
```

**错误响应**:
- `400`: 参数验证失败（URL格式错误、Cron表达式无效等）
- `403`: 对目标知识库无写权限
- `404`: 知识库不存在

---

### 3.2 获取任务列表

**端点**: `GET /api/v1/scraper/tasks`

**权限**: 需要认证

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态筛选：active/paused/stopped |
| knowledge_base_id | integer | 否 | 知识库ID筛选 |
| schedule_type | string | 否 | 调度类型筛选：once/cron |
| skip | integer | 否 | 跳过数量，默认0 |
| limit | integer | 否 | 返回数量，默认20，最大100 |

**请求示例**:
```
GET /api/v1/scraper/tasks?status=active&limit=10
```

**响应示例**:
```json
{
  "total": 25,
  "items": [
    {
      "id": 1,
      "name": "技术博客采集",
      ...
    },
    {
      "id": 2,
      "name": "新闻网站每日采集",
      ...
    }
  ]
}
```

---

### 3.3 获取任务详情

**端点**: `GET /api/v1/scraper/tasks/{task_id}`

**权限**: 需要认证，只能查看自己创建的任务或管理员可查看所有

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务ID |

**响应示例**:
```json
{
  "id": 1,
  "name": "技术博客采集",
  "description": "采集技术博客文章到知识库",
  ...
}
```

**错误响应**:
- `403`: 无权限查看此任务
- `404`: 任务不存在

---

### 3.4 更新任务

**端点**: `PUT /api/v1/scraper/tasks/{task_id}`

**权限**: 需要认证，只能更新自己创建的任务或管理员可更新所有

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务ID |

**请求体**:
```json
{
  "name": "技术博客采集（更新）",
  "description": "更新后的描述",
  "url": "https://example.com/blog/article-2",
  "selector_config": {
    "title": "h1.new-title",
    "content": "div.new-content"
  },
  "scraper_config": {
    "wait_timeout": 60000,
    "retry_times": 5
  }
}
```

**说明**:
- 所有字段都是可选的，只更新提供的字段
- 不能更新 `knowledge_base_id`、`created_by`、`created_at`
- 如果任务正在运行，更新会在下次执行时生效

**响应示例**:
```json
{
  "id": 1,
  "name": "技术博客采集（更新）",
  ...
}
```

**错误响应**:
- `400`: 参数验证失败
- `403`: 无权限更新此任务
- `404`: 任务不存在

---

### 3.5 删除任务

**端点**: `DELETE /api/v1/scraper/tasks/{task_id}`

**权限**: 需要认证，只能删除自己创建的任务或管理员可删除所有

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务ID |

**说明**:
- 删除任务会同时删除所有相关的执行日志
- 如果任务正在运行，会先停止任务再删除
- 删除操作不可逆

**响应示例**:
```json
{
  "message": "任务删除成功"
}
```

**错误响应**:
- `403`: 无权限删除此任务
- `404`: 任务不存在

---

### 3.6 启动任务

**端点**: `POST /api/v1/scraper/tasks/{task_id}/start`

**权限**: 需要认证，只能启动自己创建的任务或管理员可启动所有

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务ID |

**说明**:
- 对于一次性任务（once），立即执行一次
- 对于定时任务（cron），添加到调度器，按Cron表达式执行
- 如果任务已在运行，返回409错误

**响应示例**:
```json
{
  "message": "任务已启动",
  "task_id": 1,
  "status": "active",
  "next_run_at": "2026-03-04T10:05:00Z"
}
```

**错误响应**:
- `403`: 无权限启动此任务
- `404`: 任务不存在
- `409`: 任务已在运行

---

### 3.7 停止任务

**端点**: `POST /api/v1/scraper/tasks/{task_id}/stop`

**权限**: 需要认证，只能停止自己创建的任务或管理员可停止所有

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务ID |

**说明**:
- 停止正在运行的任务
- 对于定时任务，从调度器中移除
- 如果任务未运行，返回409错误

**响应示例**:
```json
{
  "message": "任务已停止",
  "task_id": 1,
  "status": "stopped"
}
```

**错误响应**:
- `403`: 无权限停止此任务
- `404`: 任务不存在
- `409`: 任务未运行

---

### 3.8 获取执行日志

**端点**: `GET /api/v1/scraper/tasks/{task_id}/logs`

**权限**: 需要认证，只能查看自己创建的任务日志或管理员可查看所有

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务ID |

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态筛选：running/success/failed |
| start_date | string | 否 | 开始日期，ISO 8601格式 |
| end_date | string | 否 | 结束日期，ISO 8601格式 |
| skip | integer | 否 | 跳过数量，默认0 |
| limit | integer | 否 | 返回数量，默认20，最大100 |

**请求示例**:
```
GET /api/v1/scraper/tasks/1/logs?status=success&limit=10
```

**响应示例**:
```json
{
  "total": 15,
  "items": [
    {
      "id": 1,
      "task_id": 1,
      "status": "success",
      "start_time": "2026-03-04T10:00:00Z",
      "end_time": "2026-03-04T10:02:30Z",
      "pages_scraped": 1,
      "documents_created": 1,
      "error_message": null,
      "execution_details": {
        "urls_processed": ["https://example.com/blog/article-1"],
        "processing_time": {
          "scraping": 10.5,
          "processing": 5.2,
          "storing": 2.3
        },
        "documents": [
          {
            "title": "技术文章标题",
            "url": "https://example.com/blog/article-1",
            "document_id": 123
          }
        ],
        "errors": []
      },
      "created_at": "2026-03-04T10:00:00Z"
    }
  ]
}
```

**错误响应**:
- `403`: 无权限查看此任务日志
- `404`: 任务不存在

---

## 4. 使用示例

### 4.1 创建一次性采集任务

```bash
curl -X POST "http://localhost:8000/api/v1/scraper/tasks" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "采集技术文章",
    "url": "https://example.com/article",
    "knowledge_base_id": 1,
    "schedule_type": "once",
    "selector_config": {
      "title": "h1",
      "content": "article"
    },
    "scraper_config": {
      "wait_for_selector": "article",
      "wait_timeout": 30000,
      "screenshot": false,
      "retry_times": 3,
      "retry_delay": 5
    }
  }'
```

### 4.2 创建定时采集任务（每天凌晨2点）

```bash
curl -X POST "http://localhost:8000/api/v1/scraper/tasks" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每日新闻采集",
    "url": "https://news.example.com/latest",
    "knowledge_base_id": 2,
    "schedule_type": "cron",
    "cron_expression": "0 2 * * *",
    "selector_config": {
      "title": "h2.news-title",
      "content": "div.news-body"
    },
    "scraper_config": {
      "wait_for_selector": "div.news-body",
      "wait_timeout": 30000,
      "screenshot": false,
      "retry_times": 3,
      "retry_delay": 5
    }
  }'
```

### 4.3 启动任务

```bash
curl -X POST "http://localhost:8000/api/v1/scraper/tasks/1/start" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4.4 查看执行日志

```bash
curl -X GET "http://localhost:8000/api/v1/scraper/tasks/1/logs?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 5. 前端集成指南

### 5.1 TypeScript类型定义

```typescript
// src/types/webScraper.ts

export type ScheduleType = 'once' | 'cron';
export type TaskStatus = 'active' | 'paused' | 'stopped';
export type LogStatus = 'running' | 'success' | 'failed';

export interface SelectorConfig {
  title: string;
  content: string;
  author?: string;
  publish_date?: string;
  exclude?: string[];
}

export interface ScraperConfig {
  wait_for_selector: string;
  wait_timeout: number;
  screenshot: boolean;
  user_agent?: string;
  headers?: Record<string, string>;
  retry_times: number;
  retry_delay: number;
}

export interface Task {
  id: number;
  name: string;
  description: string | null;
  url: string;
  url_pattern: string | null;
  knowledge_base_id: number;
  knowledge_base_name: string;
  schedule_type: ScheduleType;
  cron_expression: string | null;
  selector_config: SelectorConfig;
  scraper_config: ScraperConfig;
  status: TaskStatus;
  last_run_at: string | null;
  next_run_at: string | null;
  created_by: number;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface TaskCreateRequest {
  name: string;
  description?: string;
  url: string;
  url_pattern?: string;
  knowledge_base_id: number;
  schedule_type: ScheduleType;
  cron_expression?: string;
  selector_config: SelectorConfig;
  scraper_config: ScraperConfig;
}

export interface TaskListResponse {
  total: number;
  items: Task[];
}

export interface Log {
  id: number;
  task_id: number;
  status: LogStatus;
  start_time: string;
  end_time: string | null;
  pages_scraped: number;
  documents_created: number;
  error_message: string | null;
  execution_details: ExecutionDetails;
  created_at: string;
}

export interface ExecutionDetails {
  urls_processed: string[];
  processing_time: {
    scraping: number;
    processing: number;
    storing: number;
  };
  documents: Array<{
    title: string;
    url: string;
    document_id: number;
  }>;
  errors: string[];
}

export interface LogListResponse {
  total: number;
  items: Log[];
}
```

### 5.2 API客户端示例

```typescript
// src/api/webScraper.ts

import request from '@/utils/request';
import type {
  Task,
  TaskCreateRequest,
  TaskListResponse,
  LogListResponse
} from '@/types/webScraper';

export const webScraperApi = {
  // 创建任务
  createTask(data: TaskCreateRequest): Promise<Task> {
    return request.post('/scraper/tasks', data);
  },

  // 获取任务列表
  getTasks(params?: {
    status?: string;
    knowledge_base_id?: number;
    schedule_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<TaskListResponse> {
    return request.get('/scraper/tasks', { params });
  },

  // 获取任务详情
  getTask(taskId: number): Promise<Task> {
    return request.get(`/scraper/tasks/${taskId}`);
  },

  // 更新任务
  updateTask(taskId: number, data: Partial<TaskCreateRequest>): Promise<Task> {
    return request.put(`/scraper/tasks/${taskId}`, data);
  },

  // 删除任务
  deleteTask(taskId: number): Promise<void> {
    return request.delete(`/scraper/tasks/${taskId}`);
  },

  // 启动任务
  startTask(taskId: number): Promise<{ message: string }> {
    return request.post(`/scraper/tasks/${taskId}/start`);
  },

  // 停止任务
  stopTask(taskId: number): Promise<{ message: string }> {
    return request.post(`/scraper/tasks/${taskId}/stop`);
  },

  // 获取执行日志
  getLogs(taskId: number, params?: {
    status?: string;
    start_date?: string;
    end_date?: string;
    skip?: number;
    limit?: number;
  }): Promise<LogListResponse> {
    return request.get(`/scraper/tasks/${taskId}/logs`, { params });
  }
};
```

---

## 6. 注意事项

### 6.1 权限控制

- 用户只能操作自己创建的任务
- 管理员可以操作所有任务
- 需要对目标知识库有写权限才能创建任务

### 6.2 并发限制

- 系统最多同时运行5个采集任务
- 超过限制时，新任务会排队等待

### 6.3 频率限制

- 同一域名的采集间隔至少5秒
- 避免对目标网站造成过大压力

### 6.4 数据安全

- 所有敏感配置（如headers中的token）会加密存储
- 执行日志中不包含敏感信息

---

## 7. 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-03-04 | 初始版本 |
