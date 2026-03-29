---
name: backend-dev
description: Python后端开发工程师。开发FastAPI接口、数据库操作、LangChain集成、业务逻辑实现时使用。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# 后端开发 Skill

为 RAGAgentLangChain 项目进行 Python 后端开发。

## 核心职责

- 开发 FastAPI API 端点
- 实现业务逻辑（Service层）
- 数据访问层开发（Repository层）
- LangChain 集成开发
- Agent 工具开发
- RAG 功能实现
- 数据库操作和优化

## 技术栈

- **框架**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **迁移**: Alembic 1.12+
- **AI**: LangChain 1.0 + 通义千问
- **数据库**: MySQL 8.0 + Redis 7.0 + Chroma
- **验证**: Pydantic 2.7+
- **认证**: JWT (python-jose)
- **密码**: bcrypt (passlib)

## 开发规范

### 1. 严格遵守4层架构

```
API层 → Service层 → Repository层 → Infrastructure层
```

**禁止跨层调用**：
- ❌ API直接调用Repository
- ❌ Service直接操作数据库Model
- ✅ 每层只调用下一层

### 2. 代码组织

```
backend/app/
├── api/v1/              # API路由层
│   ├── auth.py          # 认证相关
│   ├── chat.py          # 对话相关
│   └── ...
├── services/            # 业务逻辑层
│   ├── auth_service.py
│   ├── conversation_service.py
│   └── ...
├── repositories/        # 数据访问层
│   ├── user_repository.py
│   └── ...
├── models/              # 数据库模型
│   ├── user.py
│   └── ...
├── schemas/             # Pydantic模型
│   ├── auth.py
│   └── ...
├── core/                # 核心功能
│   ├── database.py
│   ├── redis.py
│   └── security.py
└── langchain_integration/  # LangChain集成
    ├── chains.py
    ├── rag_chain.py
    └── agent_executor.py
```

## 开发流程

### 创建新API端点的完整流程

#### 1. 创建/更新数据库模型

```python
# app/models/example.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Example(Base):
    """示例模型"""
    __tablename__ = "examples"
    __table_args__ = {"comment": "示例表"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    name = Column(String(100), nullable=False, index=True, comment="名称")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系
    user = relationship("User", back_populates="examples")
```

#### 2. 创建Pydantic Schema

```python
# app/schemas/example.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ExampleCreate(BaseModel):
    """创建示例请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="名称")

class ExampleUpdate(BaseModel):
    """更新示例请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="名称")

class ExampleResponse(BaseModel):
    """示例响应模型"""
    id: int
    name: str
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

#### 3. 创建Repository

```python
# app/repositories/example_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.example import Example
from typing import List, Optional

class ExampleRepository:
    """示例数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, name: str) -> Example:
        """创建示例"""
        example = Example(user_id=user_id, name=name)
        self.db.add(example)
        self.db.commit()
        self.db.refresh(example)
        return example

    def get_by_id(self, example_id: int, user_id: int) -> Optional[Example]:
        """根据ID获取（带权限检查）"""
        return self.db.query(Example).filter(
            and_(
                Example.id == example_id,
                Example.user_id == user_id
            )
        ).first()

    def get_list(self, user_id: int, skip: int = 0, limit: int = 20) -> List[Example]:
        """获取列表（分页）"""
        return self.db.query(Example).filter(
            Example.user_id == user_id
        ).offset(skip).limit(limit).all()

    def update(self, example: Example, name: str) -> Example:
        """更新"""
        example.name = name
        self.db.commit()
        self.db.refresh(example)
        return example

    def delete(self, example: Example) -> None:
        """删除"""
        self.db.delete(example)
        self.db.commit()
```

#### 4. 创建Service

```python
# app/services/example_service.py
from app.repositories.example_repository import ExampleRepository
from app.schemas.example import ExampleCreate, ExampleUpdate, ExampleResponse
from fastapi import HTTPException, status
from typing import List

class ExampleService:
    """示例业务逻辑层"""

    def __init__(self, repository: ExampleRepository):
        self.repository = repository

    async def create_example(self, user_id: int, data: ExampleCreate) -> ExampleResponse:
        """创建示例"""
        example = self.repository.create(user_id=user_id, name=data.name)
        return ExampleResponse.model_validate(example)

    async def get_example(self, example_id: int, user_id: int) -> ExampleResponse:
        """获取示例详情"""
        example = self.repository.get_by_id(example_id, user_id)
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="示例不存在"
            )
        return ExampleResponse.model_validate(example)

    async def get_examples(self, user_id: int, page: int = 1, page_size: int = 20) -> List[ExampleResponse]:
        """获取示例列表"""
        skip = (page - 1) * page_size
        examples = self.repository.get_list(user_id, skip=skip, limit=page_size)
        return [ExampleResponse.model_validate(e) for e in examples]

    async def update_example(self, example_id: int, user_id: int, data: ExampleUpdate) -> ExampleResponse:
        """更新示例"""
        example = self.repository.get_by_id(example_id, user_id)
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="示例不存在"
            )

        if data.name:
            example = self.repository.update(example, data.name)

        return ExampleResponse.model_validate(example)

    async def delete_example(self, example_id: int, user_id: int) -> None:
        """删除示例"""
        example = self.repository.get_by_id(example_id, user_id)
        if not example:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="示例不存在"
            )

        self.repository.delete(example)
```

#### 5. 创建API路由

```python
# app/api/v1/example.py
from fastapi import APIRouter, Depends, status
from app.schemas.example import ExampleCreate, ExampleUpdate, ExampleResponse
from app.services.example_service import ExampleService
from app.repositories.example_repository import ExampleRepository
from app.dependencies import get_db, get_current_user
from app.models.user import User
from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/examples", tags=["examples"])

def get_example_service(db: Session = Depends(get_db)) -> ExampleService:
    """依赖注入：获取ExampleService"""
    repository = ExampleRepository(db)
    return ExampleService(repository)

@router.post("/", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    data: ExampleCreate,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """创建示例"""
    return await service.create_example(current_user.id, data)

@router.get("/{example_id}", response_model=ExampleResponse)
async def get_example(
    example_id: int,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """获取示例详情"""
    return await service.get_example(example_id, current_user.id)

@router.get("/", response_model=List[ExampleResponse])
async def get_examples(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    service: ExampleService = Depends(get_example_service)
):
    """获取示例列表"""
    return await service.get_examples(current_user.id, page, page_size)
```

## LangChain集成开发

### 1. 创建对话链

```python
# app/langchain_integration/chains.py
from langchain_community.llms import Tongyi
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from app.core.config import settings

def create_conversation_chain(conversation_history: list = None):
    """创建对话链"""
    llm = Tongyi(
        model_name=settings.TONGYI_MODEL_NAME,
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
        temperature=settings.TONGYI_TEMPERATURE,
        max_tokens=settings.TONGYI_MAX_TOKENS,
        streaming=True
    )

    memory = ConversationBufferMemory()

    # 加载历史对话
    if conversation_history:
        for msg in conversation_history:
            if msg.role == "user":
                memory.chat_memory.add_user_message(msg.content)
            elif msg.role == "assistant":
                memory.chat_memory.add_ai_message(msg.content)

    chain = ConversationChain(llm=llm, memory=memory, verbose=True)
    return chain
```

### 2. 实现流式响应

```python
# app/api/v1/chat.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import json

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """流式对话"""
    async def generate():
        try:
            async for chunk in service.chat_stream(
                user_id=current_user.id,
                conversation_id=request.conversation_id,
                content=request.content
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

## 代码规范

### 1. 命名规范

- 类名：PascalCase（`UserRepository`, `AuthService`）
- 函数/方法：snake_case（`get_by_id`, `create_user`）
- 常量：UPPER_SNAKE_CASE（`MAX_LOGIN_ATTEMPTS`）
- 私有方法：以下划线开头（`_check_account_locked`）

### 2. 文档规范

- 所有模块、类、公共方法必须有中文文档字符串
- 使用 Google 风格的文档字符串
- 包含 Args、Returns、Raises 说明

### 3. 类型注解

- 所有函数参数和返回值必须有类型注解
- 使用 `Optional` 标注可选参数
- 使用 `List`, `Dict`, `Tuple` 等泛型类型

### 4. 错误处理

- 使用自定义异常类
- 在 Service 层抛出业务异常
- 在 API 层转换为 HTTPException
- 提供清晰的错误信息

## 性能优化

### 1. 数据库查询优化

```python
# 使用joinedload避免N+1查询
from sqlalchemy.orm import joinedload

def get_conversations_with_messages(self, user_id: int):
    return self.db.query(Conversation).options(
        joinedload(Conversation.messages)
    ).filter(
        Conversation.user_id == user_id
    ).all()
```

### 2. 缓存优化

```python
# Repository层实现缓存
async def get_user_with_cache(self, user_id: int):
    cache_key = f"user:{user_id}"
    cached_data = await self.redis.get(cache_key)

    if cached_data:
        return json.loads(cached_data)

    user = self.db.query(User).filter(User.id == user_id).first()

    if user:
        await self.redis.setex(cache_key, 3600, json.dumps(user.to_dict()))

    return user
```

### 3. 异步处理

```python
# 使用BackgroundTasks处理耗时操作
from fastapi import BackgroundTasks

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    service: DocumentService = Depends(get_document_service)
):
    doc_id = await service.save_document(file)
    background_tasks.add_task(service.process_document, doc_id)
    return {"document_id": doc_id, "status": "processing"}
```

## 测试

### 单元测试

```python
# tests/test_example_service.py
import pytest
from app.services.example_service import ExampleService

@pytest.fixture
def example_service(db_session):
    repository = ExampleRepository(db_session)
    return ExampleService(repository)

async def test_create_example(example_service):
    data = ExampleCreate(name="Test Example")
    result = await example_service.create_example(user_id=1, data=data)

    assert result.name == "Test Example"
    assert result.user_id == 1
    assert result.id > 0
```

### API测试

```python
# tests/test_example_api.py
def test_create_example(client, auth_headers):
    response = client.post(
        "/api/v1/examples/",
        json={"name": "Test Example"},
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Example"
```

## 常用命令

```bash
# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest tests/

# 运行特定测试
pytest tests/test_example_api.py -v

# 测试覆盖率
pytest --cov=app --cov-report=html

# 生成迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 协作接口

### 输入来源

- **架构 Skill**: 技术方案、API设计、数据库设计
- **产品 Skill**: 需求规格说明、业务规则

### 输出交付

- **给前端开发 Skill**: API接口实现、接口文档
- **给测试 Skill**: 单元测试、API测试用例
- **给运维 Skill**: 部署脚本、环境配置

## 注意事项

1. **严格遵守4层架构**：不要跨层调用
2. **数据库迁移**：所有表结构变更通过Alembic
3. **权限检查**：在Repository或Service层检查用户权限
4. **配额管理**：涉及LLM调用的功能必须检查和扣除配额
5. **输入验证**：使用Pydantic进行严格的输入验证
6. **SQL注入防护**：使用ORM参数化查询
7. **日志记录**：关键操作记录日志
8. **错误处理**：提供清晰的错误信息
9. **性能考虑**：添加适当的索引，使用分页查询
10. **测试覆盖**：编写单元测试和集成测试
