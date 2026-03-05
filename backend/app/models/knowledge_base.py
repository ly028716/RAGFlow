"""
知识库模型

定义KnowledgeBase数据库模型，用于存储用户的知识库信息。
"""

from datetime import datetime

from sqlalchemy import (Column, DateTime, ForeignKey, Index, Integer, String,
                        Text)
from sqlalchemy.orm import relationship

from app.core.database import Base


class KnowledgeBase(Base):
    """
    知识库模型

    存储用户创建的知识库信息。每个知识库可以包含多个文档。

    字段说明:
        id: 知识库唯一标识
        user_id: 所属用户ID（外键）
        name: 知识库名称
        description: 知识库描述
        category: 知识库分类
        created_at: 知识库创建时间
        updated_at: 知识库最后更新时间

    关系:
        user: 所属用户
        documents: 知识库中的所有文档

    索引:
        - user_id: 用于快速查询用户的所有知识库
        - created_at: 用于按时间排序
        - (user_id, created_at): 复合索引，优化用户知识库列表查询

    需求引用:
        - 需求3.1: 用户创建知识库且提供名称和描述
    """

    __tablename__ = "knowledge_bases"

    # 主键
    id = Column(Integer, primary_key=True, index=True, comment="知识库ID")

    # 外键
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="用户ID",
    )

    # 基本信息
    name = Column(String(100), nullable=False, comment="知识库名称")
    description = Column(Text, nullable=True, comment="知识库描述")
    category = Column(String(50), nullable=True, comment="知识库分类")

    # 可见性设置
    visibility = Column(
        String(20),
        default="private",
        nullable=False,
        comment="可见性: private/shared/public",
    )

    # 时间戳
    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="更新时间",
    )

    # 关系映射
    user = relationship("User", back_populates="knowledge_bases")
    documents = relationship(
        "Document",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        order_by="Document.created_at.desc()",
    )
    scraper_tasks = relationship(
        "WebScraperTask",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        order_by="desc(WebScraperTask.created_at)",
    )

    # 复合索引
    __table_args__ = (
        Index("idx_kb_user_created", "user_id", "created_at"),
        {"comment": "知识库表"},
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<KnowledgeBase(id={self.id}, user_id={self.user_id}, name='{self.name}')>"
        )

    def __str__(self) -> str:
        """用户友好的字符串表示"""
        return f"KnowledgeBase: {self.name}"
