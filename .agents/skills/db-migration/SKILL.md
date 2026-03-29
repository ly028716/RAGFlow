---
name: db-migration
description: 生成 Alembic 数据库迁移脚本。当需要修改数据库表结构、添加新表、添加字段、创建索引时使用。
---

# 数据库迁移 Skill

为 RAGAgentLangChain 项目生成符合规范的 Alembic 数据库迁移脚本。

## 项目结构

```
backend/
├── alembic/
│   ├── env.py              # Alembic 环境配置
│   ├── versions/           # 迁移脚本目录
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_verification_codes.py
│   │   └── ...
│   └── alembic.ini         # Alembic 配置文件
└── app/
    └── models/             # SQLAlchemy 模型
```

## 创建迁移脚本的步骤

### 1. 确定迁移版本号

查看现有迁移文件，确定下一个版本号：
```bash
ls backend/alembic/versions/
```

版本号格式：`{序号}_{描述}.py`，如 `005_add_user_preferences.py`

### 2. 创建迁移脚本

文件位置：`backend/alembic/versions/{序号}_{描述}.py`

```python
"""{迁移描述}

{详细说明这次迁移做了什么}

Revision ID: {序号}_{简短标识}
Revises: {上一个版本的revision}
Create Date: {日期}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '{序号}_{简短标识}'
down_revision: Union[str, None] = '{上一个版本的revision}'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库 - {描述}"""
    pass


def downgrade() -> None:
    """降级数据库 - {描述}"""
    pass
```

## 常用迁移操作

### 创建新表

```python
def upgrade() -> None:
    """升级数据库 - 创建{table_name}表"""

    op.create_table(
        '{table_name}',
        sa.Column('id', sa.Integer(), nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='描述'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否激活'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        comment='{表注释}'
    )
    # 创建索引
    op.create_index('ix_{table_name}_id', '{table_name}', ['id'], unique=False)
    op.create_index('ix_{table_name}_user_id', '{table_name}', ['user_id'], unique=False)


def downgrade() -> None:
    """降级数据库 - 删除{table_name}表"""

    op.drop_index('ix_{table_name}_user_id', table_name='{table_name}')
    op.drop_index('ix_{table_name}_id', table_name='{table_name}')
    op.drop_table('{table_name}')
```

### 添加字段

```python
def upgrade() -> None:
    """升级数据库 - 添加{column_name}字段"""

    op.add_column(
        '{table_name}',
        sa.Column('{column_name}', sa.String(255), nullable=True, comment='字段说明')
    )


def downgrade() -> None:
    """降级数据库 - 删除{column_name}字段"""

    op.drop_column('{table_name}', '{column_name}')
```

### 修改字段

```python
def upgrade() -> None:
    """升级数据库 - 修改{column_name}字段"""

    # 修改字段类型
    op.alter_column(
        '{table_name}',
        '{column_name}',
        existing_type=sa.String(100),
        type_=sa.String(255),
        existing_nullable=True
    )

    # 修改字段为非空
    op.alter_column(
        '{table_name}',
        '{column_name}',
        existing_type=sa.String(255),
        nullable=False
    )


def downgrade() -> None:
    """降级数据库 - 恢复{column_name}字段"""

    op.alter_column(
        '{table_name}',
        '{column_name}',
        existing_type=sa.String(255),
        type_=sa.String(100),
        existing_nullable=True
    )
```

### 创建索引

```python
def upgrade() -> None:
    """升级数据库 - 创建索引"""

    # 普通索引
    op.create_index('idx_{table}_{column}', '{table_name}', ['{column_name}'])

    # 唯一索引
    op.create_index('uq_{table}_{column}', '{table_name}', ['{column_name}'], unique=True)

    # 复合索引
    op.create_index('idx_{table}_composite', '{table_name}', ['col1', 'col2'])


def downgrade() -> None:
    """降级数据库 - 删除索引"""

    op.drop_index('idx_{table}_composite', table_name='{table_name}')
    op.drop_index('uq_{table}_{column}', table_name='{table_name}')
    op.drop_index('idx_{table}_{column}', table_name='{table_name}')
```

### 添加外键

```python
def upgrade() -> None:
    """升级数据库 - 添加外键"""

    op.create_foreign_key(
        'fk_{table}_{ref_table}',
        '{table_name}',
        '{ref_table}',
        ['{column_name}'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """降级数据库 - 删除外键"""

    op.drop_constraint('fk_{table}_{ref_table}', '{table_name}', type_='foreignkey')
```

## 运行迁移命令

```bash
# 进入后端目录
cd backend

# 查看当前迁移状态
alembic current

# 查看迁移历史
alembic history

# 升级到最新版本
alembic upgrade head

# 升级到指定版本
alembic upgrade {revision}

# 降级一个版本
alembic downgrade -1

# 降级到指定版本
alembic downgrade {revision}

# 生成迁移脚本（自动检测模型变化）
alembic revision --autogenerate -m "描述"
```

## 注意事项

1. **版本链**: 确保 `down_revision` 正确指向上一个迁移版本
2. **可逆性**: 每个 `upgrade()` 必须有对应的 `downgrade()`
3. **数据安全**: 删除字段/表前考虑数据备份
4. **索引命名**: 使用统一的命名规范 `ix_`, `idx_`, `uq_`, `fk_`
5. **注释**: 为表和字段添加 `comment` 参数
6. **测试**: 在开发环境测试迁移的升级和降级

## 同步 SQLAlchemy 模型

创建迁移后，确保同步更新对应的 SQLAlchemy 模型：

文件位置：`backend/app/models/{entity}.py`

```python
"""
{Entity}数据库模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class {Entity}(Base):
    """
    {Entity}模型

    对应数据库表: {table_name}
    """

    __tablename__ = "{table_name}"
    __table_args__ = {"comment": "{表注释}"}

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    name = Column(String(100), nullable=False, comment="名称")
    description = Column(Text, nullable=True, comment="描述")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True, comment="更新时间")

    # 关系
    user = relationship("User", back_populates="{entities}")


__all__ = ['{Entity}']
```
