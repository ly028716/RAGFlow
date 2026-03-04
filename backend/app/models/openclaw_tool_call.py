"""
OpenClaw 工具调用记录模型

存储 OpenClaw Agent 调用工具的历史记录
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class CallStatus(str, Enum):
    """调用状态枚举"""

    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    TIMEOUT = "timeout"  # 超时


class OpenClawToolCall(Base):
    """
    OpenClaw 工具调用记录表

    存储 OpenClaw Agent 调用工具的历史记录，用于审计和统计
    """

    __tablename__ = "openclaw_tool_calls"

    id = Column(Integer, primary_key=True, index=True, comment="调用记录ID")
    tool_id = Column(
        Integer,
        ForeignKey("openclaw_tools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="工具ID",
    )
    agent_id = Column(String(100), nullable=True, index=True, comment="Agent ID")
    user_id = Column(Integer, nullable=True, index=True, comment="用户ID")
    request_params = Column(JSON, nullable=True, comment="请求参数（JSON）")
    response_data = Column(JSON, nullable=True, comment="响应数据（JSON）")
    status = Column(
        String(20),
        nullable=False,
        default=CallStatus.SUCCESS,
        index=True,
        comment="调用状态",
    )
    error_message = Column(Text, nullable=True, comment="错误信息")
    execution_time = Column(Float, nullable=True, comment="执行时间（秒）")
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="调用时间",
    )

    # 关系：关联的工具
    tool = relationship("OpenClawTool", back_populates="tool_calls")

    def __repr__(self):
        return f"<OpenClawToolCall(id={self.id}, tool_id={self.tool_id}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "tool_id": self.tool_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "status": self.status,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
