"""
OpenClaw 工具配置模型

存储注册到 OpenClaw Gateway 的自定义工具配置
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class ToolStatus(str, Enum):
    """工具状态枚举"""

    ACTIVE = "active"  # 激活
    INACTIVE = "inactive"  # 停用
    DELETED = "deleted"  # 已删除


class OpenClawTool(Base):
    """
    OpenClaw 工具配置表

    存储注册到 OpenClaw Gateway 的自定义工具配置信息
    """

    __tablename__ = "openclaw_tools"

    id = Column(Integer, primary_key=True, index=True, comment="工具ID")
    name = Column(
        String(100), unique=True, nullable=False, index=True, comment="工具名称（唯一）"
    )
    display_name = Column(String(200), nullable=False, comment="工具显示名称")
    description = Column(Text, nullable=False, comment="工具描述")
    endpoint_url = Column(String(500), nullable=False, comment="工具端点URL")
    method = Column(
        String(10), nullable=False, default="POST", comment="HTTP方法（GET/POST）"
    )
    auth_type = Column(
        String(50), nullable=False, default="api_token", comment="认证类型"
    )
    auth_config = Column(JSON, nullable=True, comment="认证配置（JSON）")
    parameters_schema = Column(JSON, nullable=True, comment="参数Schema（JSON Schema）")
    response_schema = Column(JSON, nullable=True, comment="响应Schema（JSON Schema）")
    status = Column(
        String(20),
        nullable=False,
        default=ToolStatus.ACTIVE,
        index=True,
        comment="工具状态",
    )
    is_builtin = Column(
        Boolean, nullable=False, default=False, comment="是否为内置工具"
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建者用户ID"
    )
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    # 关系：工具调用记录
    tool_calls = relationship(
        "OpenClawToolCall", back_populates="tool", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<OpenClawTool(id={self.id}, name={self.name}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "endpoint_url": self.endpoint_url,
            "method": self.method,
            "auth_type": self.auth_type,
            "status": self.status,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
