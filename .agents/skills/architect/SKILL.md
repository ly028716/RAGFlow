---
name: architect
description: 系统架构设计和技术方案制定。当需要设计系统架构、制定技术方案、技术选型、API设计、数据库设计时使用。
allowed-tools: Read, Grep, Glob
---

# 架构/技术方案 Skill

为 RAGAgentLangChain 项目进行系统架构设计和技术方案制定。

## 核心职责

- 系统架构设计
- 技术方案制定
- 技术选型和评估
- API接口设计
- 数据库设计
- 性能优化方案
- 安全架构设计

## 项目架构概览

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端层 (Vue 3)                        │
│  - 用户界面                                              │
│  - 状态管理 (Pinia)                                      │
│  - 路由管理 (Vue Router)                                 │
└─────────────────────────────────────────────────────────┘
                            ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────┐
│                  API网关层 (FastAPI)                     │
│  - 路由分发                                              │
│  - 认证授权 (JWT)                                        │
│  - 速率限制                                              │
│  - 请求日志                                              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   业务逻辑层 (Services)                  │
│  - 对话服务                                              │
│  - RAG服务                                               │
│  - Agent服务                                             │
│  - 配额服务                                              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              数据访问层 (Repositories)                   │
│  - ORM操作                                               │
│  - 缓存管理                                              │
│  - 事务管理                                              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   数据存储层                             │
│  MySQL (业务数据) | Redis (缓存) | Chroma (向量)         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   AI服务层                               │
│  通义千问 (LLM) | DashScope (Embeddings)                │
└─────────────────────────────────────────────────────────┘
```

### 后端4层架构

**严格遵守的分层原则：**

1. **API层** (`app/api/v1/`)
   - 职责：HTTP请求处理、参数验证、响应序列化
   - 不包含：业务逻辑、数据库操作
   - 依赖：Service层

2. **Service层** (`app/services/`)
   - 职责：业务逻辑、流程编排、事务管理
   - 不包含：HTTP处理、直接数据库操作
   - 依赖：Repository层、LangChain集成层

3. **Repository层** (`app/repositories/`)
   - 职责：数据访问抽象、ORM操作、缓存管理
   - 不包含：业务逻辑
   - 依赖：Model层、Core层

4. **Infrastructure层** (`app/core/`, `app/models/`)
   - 职责：数据库连接、Redis连接、配置管理
   - 不包含：业务逻辑

**禁止跨层调用：** API层不能直接调用Repository层

## 技术栈详解

### 前端技术栈

- **Vue 3.5+**: Composition API为主
- **TypeScript 5.9+**: 类型安全
- **Vite 7.2+**: 构建工具
- **Element Plus 2.9+**: UI组件库
- **Pinia 3.0+**: 状态管理
- **Axios 1.9+**: HTTP客户端
- **markdown-it 14.1+**: Markdown渲染
- **highlight.js 11.11+**: 代码高亮

### 后端技术栈

- **FastAPI 0.104+**: Web框架
- **LangChain 1.0**: LLM应用框架
- **SQLAlchemy 2.0+**: ORM
- **Alembic 1.12+**: 数据库迁移
- **PyMySQL 1.1+**: MySQL驱动
- **Redis 5.0+**: 缓存客户端
- **Pydantic 2.7+**: 数据验证
- **python-jose 3.3+**: JWT处理
- **passlib 1.7+**: 密码加密
- **chromadb 0.4+**: 向量数据库

### AI服务

- **通义千问**: qwen-turbo模型（对话）
- **DashScope Embeddings**: text-embedding-v1（向量化）

## 架构设计原则

### 1. 单一职责原则

每个模块、类、函数只负责一个功能：
- API层只处理HTTP
- Service层只处理业务逻辑
- Repository层只处理数据访问

### 2. 依赖倒置原则

高层模块不依赖低层模块，都依赖抽象：
- Service依赖Repository接口，不依赖具体实现
- 使用依赖注入（FastAPI的Depends）

### 3. 开闭原则

对扩展开放，对修改关闭：
- 新增功能通过添加新的Service/Repository
- 不修改现有核心代码

### 4. 接口隔离原则

客户端不应依赖它不需要的接口：
- Repository提供细粒度的方法
- 不要创建大而全的接口

## 常见架构模式

### 1. 流式响应模式（SSE）

**场景**: 对话、RAG问答

```python
# API层
@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        service.chat_stream(request),
        media_type="text/event-stream"
    )

# Service层
async def chat_stream(self, request):
    async for chunk in llm_chain.astream(request.content):
        yield f"data: {json.dumps(chunk)}\n\n"
```

### 2. 异步任务模式

**场景**: 文档处理、Agent执行

```python
# API层
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    doc_id = await service.create_document(file)
    background_tasks.add_task(service.process_document, doc_id)
    return {"document_id": doc_id, "status": "processing"}
```

### 3. 缓存模式

**场景**: 用户信息、对话列表

```python
# Repository层
async def get_user(self, user_id: int):
    # 1. 尝试从Redis获取
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    # 2. 从数据库获取
    user = self.db.query(User).filter(User.id == user_id).first()

    # 3. 写入Redis
    await redis.setex(f"user:{user_id}", 3600, json.dumps(user))

    return user
```

### 4. 配额检查模式

**场景**: LLM调用前检查配额

```python
# Service层
async def chat(self, user_id: int, content: str):
    # 1. 检查配额
    quota = await quota_service.check_quota(user_id)
    if not quota.has_enough():
        raise QuotaExceededException()

    # 2. 调用LLM
    response = await llm_chain.ainvoke(content)

    # 3. 扣除配额
    await quota_service.deduct_quota(user_id, response.tokens)

    return response
```

## 数据库设计原则

### 1. 表设计规范

- 使用自增主键 `id`
- 添加时间戳字段 `created_at`, `updated_at`
- 软删除使用 `is_deleted` 字段
- 外键使用 `_id` 后缀（如 `user_id`）

### 2. 索引策略

- 主键自动索引
- 外键添加索引
- 频繁查询的字段添加索引
- 复合索引考虑最左前缀原则

### 3. 数据类型选择

- 字符串：VARCHAR(长度)，不要用TEXT除非必要
- 整数：INT或BIGINT
- 时间：DATETIME，使用UTC时区
- 布尔：TINYINT(1)
- JSON：JSON类型（MySQL 8.0+）

## API设计规范

### 1. RESTful风格

```
GET    /api/v1/conversations          # 获取列表
POST   /api/v1/conversations          # 创建
GET    /api/v1/conversations/{id}     # 获取详情
PUT    /api/v1/conversations/{id}     # 更新
DELETE /api/v1/conversations/{id}     # 删除
```

### 2. 响应格式

**成功响应**:
```json
{
  "id": 1,
  "title": "对话标题",
  "created_at": "2025-01-16T10:00:00Z"
}
```

**错误响应**:
```json
{
  "detail": "错误描述",
  "error_code": "QUOTA_EXCEEDED",
  "request_id": "uuid"
}
```

### 3. 分页格式

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

## 性能优化策略

### 1. 数据库优化

- 使用连接池（pool_size=10, max_overflow=20）
- 添加适当索引
- 使用分页查询
- 避免N+1查询（使用joinedload）
- 慢查询日志监控

### 2. 缓存策略

- 用户信息缓存1小时
- 对话列表缓存10分钟
- 配额信息缓存5分钟
- 使用Redis Pipeline批量操作

### 3. LLM调用优化

- 使用流式输出减少首字响应时间
- 批量文档向量化
- 结果缓存（可选）
- 超时和重试机制

### 4. 异步处理

- 文档处理异步化
- Agent执行异步化
- 使用BackgroundTasks

## 安全架构

### 1. 认证授权

- JWT Token认证
- Access Token（7天）+ Refresh Token（30天）
- Token存储在Redis，支持撤销
- 密码bcrypt加密（12轮）

### 2. 输入验证

- Pydantic模型验证
- SQL注入防护（ORM参数化）
- XSS防护（输入清理）
- 文件上传类型和大小限制

### 3. 速率限制

- 登录：5次/分钟
- LLM调用：20次/分钟
- 一般API：100次/分钟

### 4. 敏感数据保护

- API密钥AES-256加密存储
- 密码不可逆加密
- HTTPS传输
- 日志脱敏

## 技术方案模板

### 新功能技术方案

1. **需求分析**
   - 功能描述
   - 用户场景
   - 技术挑战

2. **架构设计**
   - 模块划分
   - 数据流图
   - 接口设计

3. **数据库设计**
   - 表结构
   - 索引设计
   - 迁移脚本

4. **API设计**
   - 端点列表
   - 请求/响应格式
   - 错误码定义

5. **实现计划**
   - Model层
   - Repository层
   - Service层
   - API层
   - 前端集成

6. **测试计划**
   - 单元测试
   - 集成测试
   - 性能测试

7. **部署方案**
   - 数据库迁移
   - 配置变更
   - 回滚方案

## 技术选型考虑因素

### 1. 功能需求

- 是否满足功能要求
- 是否支持扩展

### 2. 性能要求

- 响应时间
- 并发能力
- 资源消耗

### 3. 生态系统

- 社区活跃度
- 文档完善度
- 第三方库支持

### 4. 团队能力

- 学习曲线
- 现有技术栈
- 维护成本

### 5. 成本考虑

- 开发成本
- 运维成本
- 许可证成本

## 协作接口

### 输入来源

- **产品 Skill**: 需求规格说明、功能边界定义
- **业务需求**: 性能要求、安全要求

### 输出交付

- **给后端开发 Skill**: 技术方案、API设计、数据库设计
- **给前端开发 Skill**: API接口文档、数据格式定义
- **给测试 Skill**: 架构说明、性能指标、测试重点
- **给运维 Skill**: 部署架构、监控指标、扩展方案

## 注意事项

1. **始终遵守4层架构**：不要跨层调用
2. **数据库迁移**：所有表结构变更必须通过Alembic
3. **API版本管理**：所有API在 `/api/v1/` 下
4. **错误处理**：统一的错误处理中间件
5. **日志记录**：关键操作必须记录日志
6. **性能监控**：使用Prometheus监控关键指标
7. **安全第一**：所有输入必须验证，敏感数据必须加密
8. **文档同步**：架构变更及时更新AGENTS.md

## 输出格式

技术方案文档应包含：
- 架构图（使用ASCII或描述）
- 数据流图
- 数据库设计（表结构、索引）
- API接口设计（端点、请求/响应）
- 实现步骤
- 测试计划
- 部署方案
- 风险评估
