---
name: api-dev
description: 按照项目三层架构规范创建新的 FastAPI 端点。当需要添加新 API、创建端点、实现接口时使用。包含路由层、服务层、仓储层的完整实现。
---

# API 开发 Skill

为 RAGAgentLangChain 项目创建符合规范的 API 端点。

## 项目架构

本项目采用三层架构：

```
backend/app/
├── api/v1/          # API 路由层 - 处理 HTTP 请求/响应
├── services/        # 服务层 - 业务逻辑
├── repositories/    # 仓储层 - 数据访问
├── models/          # SQLAlchemy 数据库模型
└── schemas/         # Pydantic 数据验证模型
```

## 创建新 API 的步骤

### 1. 创建 Repository（如需新数据访问）

文件位置：`backend/app/repositories/{entity}_repository.py`

```python
"""
{Entity}数据访问层（Repository）

封装{entity}相关的数据库操作，提供统一的数据访问接口。
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.{entity} import {Entity}


class {Entity}Repository:
    """
    {Entity}Repository类

    提供{entity}数据的CRUD操作和查询功能。

    使用方式:
        repo = {Entity}Repository(db)
        item = repo.create(...)
        item = repo.get_by_id(1)
    """

    def __init__(self, db: Session):
        """
        初始化Repository

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db

    def create(self, **kwargs) -> {Entity}:
        """创建新记录"""
        item = {Entity}(**kwargs)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_by_id(self, id: int) -> Optional[{Entity}]:
        """根据ID获取记录"""
        return self.db.query({Entity}).filter({Entity}.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[{Entity}]:
        """获取所有记录（分页）"""
        return self.db.query({Entity}).offset(skip).limit(limit).all()

    def update(self, id: int, **kwargs) -> Optional[{Entity}]:
        """更新记录"""
        item = self.get_by_id(id)
        if not item:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, id: int) -> bool:
        """删除记录"""
        item = self.get_by_id(id)
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True


__all__ = ['{Entity}Repository']
```

### 2. 创建 Service

文件位置：`backend/app/services/{entity}_service.py`

```python
"""
{Entity}服务模块

实现{entity}相关业务逻辑。
需求: 需求X.X
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.repositories.{entity}_repository import {Entity}Repository
from app.models.{entity} import {Entity}


class {Entity}ServiceError(Exception):
    """服务异常基类"""
    pass


class {Entity}NotFoundError({Entity}ServiceError):
    """记录不存在异常"""
    pass


class {Entity}Service:
    """
    {Entity}服务类

    提供{entity}相关的业务功能。

    使用方式:
        service = {Entity}Service(db)
        item = service.create(...)
    """

    def __init__(self, db: Session):
        """
        初始化服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.repo = {Entity}Repository(db)

    def create(self, **kwargs) -> {Entity}:
        """
        创建{entity}

        Args:
            **kwargs: 创建参数

        Returns:
            {Entity}: 创建的对象

        需求引用:
            - 需求X.X: 描述
        """
        return self.repo.create(**kwargs)

    def get_by_id(self, id: int) -> {Entity}:
        """获取{entity}"""
        item = self.repo.get_by_id(id)
        if not item:
            raise {Entity}NotFoundError(f"{Entity} {id} 不存在")
        return item


__all__ = [
    '{Entity}Service',
    '{Entity}ServiceError',
    '{Entity}NotFoundError',
]
```

### 3. 创建 Pydantic Schemas

文件位置：`backend/app/schemas/{entity}.py`

```python
"""
{Entity} Pydantic 模型

定义{entity}相关的请求和响应数据模型。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class {Entity}Create(BaseModel):
    """创建{entity}请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="名称")
    description: Optional[str] = Field(None, max_length=500, description="描述")


class {Entity}Update(BaseModel):
    """更新{entity}请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class {Entity}Response(BaseModel):
    """响应模型"""
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
```

### 4. 创建 API 路由

文件位置：`backend/app/api/v1/{entity}.py`

```python
"""
{Entity} API路由模块

实现{entity}相关的API端点。

需求引用:
    - 需求X.X: 描述
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.{entity} import (
    {Entity}Create,
    {Entity}Update,
    {Entity}Response,
    MessageResponse,
)
from app.services.{entity}_service import (
    {Entity}Service,
    {Entity}NotFoundError,
)


router = APIRouter(prefix="/{entities}", tags=["{Entity}"])


@router.post(
    "",
    response_model={Entity}Response,
    status_code=status.HTTP_201_CREATED,
    summary="创建{entity}",
    description="创建新的{entity}记录。"
)
def create_{entity}(
    data: {Entity}Create,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> {Entity}Response:
    """
    创建{entity}端点

    需求引用:
        - 需求X.X: 描述

    Args:
        data: 创建数据
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        {Entity}Response: 创建的{entity}信息
    """
    service = {Entity}Service(db)
    item = service.create(
        user_id=current_user.id,
        **data.model_dump()
    )
    return {Entity}Response.model_validate(item)


@router.get(
    "/{id}",
    response_model={Entity}Response,
    summary="获取{entity}详情"
)
def get_{entity}(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> {Entity}Response:
    """获取{entity}详情端点"""
    service = {Entity}Service(db)
    try:
        item = service.get_by_id(id)
        return {Entity}Response.model_validate(item)
    except {Entity}NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "",
    response_model=List[{Entity}Response],
    summary="获取{entity}列表"
)
def list_{entities}(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[{Entity}Response]:
    """获取{entity}列表端点"""
    service = {Entity}Service(db)
    items = service.get_all(skip=skip, limit=limit)
    return [
        {Entity}Response.model_validate(item)
        for item in items
    ]


# 导出
__all__ = ['router']
```

### 5. 注册路由

在 `backend/app/main.py` 中注册新路由：

```python
from app.api.v1.{entity} import router as {entity}_router

app.include_router({entity}_router, prefix="/api/v1")
```

## 代码规范

1. **中文注释**: 所有文档字符串和注释使用中文
2. **类型注解**: 所有函数参数和返回值必须有类型注解
3. **需求引用**: 在文档字符串中引用相关需求编号
4. **异常处理**: 使用自定义异常类，在 API 层转换为 HTTPException
5. **导出声明**: 每个模块末尾使用 `__all__` 声明导出内容

## 常用依赖

```python
from app.core.database import get_db          # 数据库会话
from app.dependencies import get_current_user  # 当前用户
from app.config import settings               # 配置
from app.core.redis import get_redis_client   # Redis客户端
```
