"""
Conversation 消息服务模块

实现消息管理相关业务逻辑。
"""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.conversation.exceptions import ConversationNotFoundError

logger = logging.getLogger(__name__)


class MessageService:
    """
    消息服务类

    提供消息的CRUD操作。

    使用方式:
        service = MessageService(db)
        message = service.add(conversation_id=1, user_id=1, role=MessageRole.USER, content="你好")
        messages = service.get_list(conversation_id=1, user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化消息服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.message_repo = MessageRepository(db)

    def add(
        self,
        conversation_id: int,
        user_id: int,
        role: MessageRole,
        content: str,
        tokens: int = 0,
    ) -> Message:
        """
        添加消息到对话

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）
            role: 消息角色
            content: 消息内容
            tokens: 消耗的token数量

        Returns:
            Message: 创建的消息对象

        Raises:
            ConversationNotFoundError: 对话不存在或不属于该用户
        """
        # 验证对话存在且属于该用户
        conversation = self.conversation_repo.get_by_id_and_user(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        # 创建消息
        message = self.message_repo.create(
            conversation_id=conversation_id, role=role, content=content, tokens=tokens
        )

        # 更新对话的更新时间
        self.conversation_repo.touch(conversation_id)

        return message

    def get_list(
        self,
        conversation_id: int,
        user_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        获取对话的所有消息

        按创建时间升序排列（从旧到新）。

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）
            skip: 跳过的记录数
            limit: 返回的最大记录数，None表示不限制

        Returns:
            List[Message]: 消息列表

        Raises:
            ConversationNotFoundError: 对话不存在或不属于该用户
        """
        # 验证对话存在且属于该用户
        conversation = self.conversation_repo.get_by_id_and_user(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        messages = self.message_repo.get_by_conversation(
            conversation_id=conversation_id, skip=skip, limit=limit, order_asc=True
        )

        return messages

    def get_recent(
        self, conversation_id: int, user_id: int, limit: int = 10
    ) -> List[Message]:
        """
        获取对话的最近消息

        用于获取对话上下文。

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）
            limit: 返回的最大记录数

        Returns:
            List[Message]: 消息列表（按时间正序）

        Raises:
            ConversationNotFoundError: 对话不存在或不属于该用户
        """
        # 验证对话存在且属于该用户
        conversation = self.conversation_repo.get_by_id_and_user(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        return self.message_repo.get_recent_messages(
            conversation_id=conversation_id, limit=limit
        )

    def get_token_usage(self, conversation_id: int, user_id: int) -> int:
        """
        获取对话的总token消耗

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）

        Returns:
            int: 总token数量

        Raises:
            ConversationNotFoundError: 对话不存在或不属于该用户
        """
        # 验证对话存在且属于该用户
        conversation = self.conversation_repo.get_by_id_and_user(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        return self.message_repo.get_total_tokens(conversation_id)

    def is_first_user_message(self, conversation_id: int) -> bool:
        """
        检查对话是否还没有用户消息

        用于判断是否需要自动生成标题。

        Args:
            conversation_id: 对话ID

        Returns:
            bool: 如果没有用户消息返回True
        """
        messages = self.message_repo.get_by_conversation(
            conversation_id=conversation_id, skip=0, limit=1, order_asc=True
        )

        # 检查是否有用户消息
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        return len(user_messages) == 0


__all__ = [
    "MessageService",
]
