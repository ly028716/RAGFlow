"""
Agent执行记录模型

定义AgentExecution数据库模型，用于存储Agent任务执行的记录和步骤信息。
"""

import enum
from datetime import datetime

from sqlalchemy import (JSON, Column, DateTime, Enum, ForeignKey, Index,
                        Integer, Text)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExecutionStatus(str, enum.Enum):
    """
    执行状态枚举

    - pending: 等待执行
    - running: 执行中
    - completed: 执行完成
    - failed: 执行失败
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


class AgentExecution(Base):
    """
    Agent执行记录模型

    存储Agent任务执行的完整记录，包括任务描述、执行步骤、结果和状态。

    字段说明:
        id: 执行记录唯一标识
        user_id: 执行任务的用户ID（外键）
        task: 任务描述
        steps: 执行步骤记录（JSON格式，包含每步的推理和行动）
        result: 最终执行结果
        status: 执行状态（pending/running/completed/failed）
        error_message: 错误信息（执行失败时记录）
        created_at: 任务创建时间
        completed_at: 任务完成时间

    关系:
        user: 执行任务的用户

    索引:
        - user_id: 用于快速查询用户的执行记录
        - created_at: 用于按时间排序
        - (user_id, created_at): 复合索引，优化用户执行历史查询

    需求引用:
        - 需求6.2: Agent执行计划生成完成后创建执行记录
        - 需求6.4: 记录每个执行步骤的工具名称、输入参数、输出结果和推理过程
    """

    __tablename__ = "agent_executions"

    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="执行记录ID")

    # 外键
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )

    # 任务信息
    task = Column(Text, nullable=False, comment="任务描述")

    # 执行步骤（JSON格式存储）
    # 格式示例:
    # [
    #   {
    #     "step_number": 1,
    #     "thought": "我需要搜索相关信息",
    #     "action": "search",
    #     "action_input": {"query": "Python教程"},
    #     "observation": "找到了相关结果"
    #   },
    #   ...
    # ]
    steps = Column(JSON, nullable=True, comment="执行步骤记录")

    # 执行结果
    result = Column(Text, nullable=True, comment="执行结果")

    # 执行状态
    status = Column(
        Enum(ExecutionStatus, values_callable=_enum_values, name="executionstatus"),
        default=ExecutionStatus.PENDING,
        nullable=False,
        comment="执行状态",
    )

    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 时间戳
    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True, comment="创建时间"
    )
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 关系映射
    user = relationship("User", backref="agent_executions")

    # 复合索引
    __table_args__ = (
        Index("idx_agent_exec_user_created", "user_id", "created_at"),
        {"comment": "Agent执行记录表"},
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<AgentExecution(id={self.id}, user_id={self.user_id}, status='{self.status.value}')>"

    def __str__(self) -> str:
        """用户友好的字符串表示"""
        return f"AgentExecution: {self.task[:50]}..."
