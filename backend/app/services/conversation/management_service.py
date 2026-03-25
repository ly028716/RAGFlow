"""
Conversation 管理服务模块

实现对话管理相关业务逻辑，包括创建、查询、更新、删除。
"""

import logging
from typing import List, Tuple, Optional

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.repositories.conversation_repository import ConversationRepository
from app.services.conversation.exceptions import ConversationNotFoundError

logger = logging.getLogger(__name__)


class ConversationManagementService:
    """
    对话管理服务类

    提供对话的CRUD操作。

    使用方式:
        service = ConversationManagementService(db)
        conversation = service.create(user_id=1, title="新对话")
        conversations, total = service.get_list(user_id=1)
    """

    def __init__(self, db: Session):
        """
        初始化对话管理服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.conversation_repo = ConversationRepository(db)

    def create(self, user_id: int, title: str = "新对话") -> Conversation:
        """
        创建新对话

        Args:
            user_id: 用户ID
            title: 对话标题，默认为"新对话"

        Returns:
            Conversation: 创建的对话对象
        """
        conversation = self.conversation_repo.create(user_id=user_id, title=title)
        return conversation

    def get_list(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> Tuple[List[dict], int]:
        """
        获取用户的对话列表（分页）

        按更新时间倒序排列，返回对话列表和总数。
        每个对话包含消息数量统计。

        Args:
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            Tuple[List[dict], int]: (对话列表, 总数)
        """
        conversations, total = self.conversation_repo.get_by_user(
            user_id=user_id, skip=skip, limit=limit, include_deleted=False
        )

        # 批量获取所有对话的消息数量，避免 N+1 查询
        conversation_ids = [conv.id for conv in conversations]
        message_counts = self.conversation_repo.get_message_counts_batch(
            conversation_ids
        )

        # 为每个对话添加消息数量
        result = []
        for conv in conversations:
            result.append(
                {
                    "id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                    "message_count": message_counts.get(conv.id, 0),
                }
            )

        return result, total

    def get_by_id(self, conversation_id: int, user_id: int) -> Conversation:
        """
        获取单个对话

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）

        Returns:
            Conversation: 对话对象

        Raises:
            ConversationNotFoundError: 对话不存在或不属于该用户
        """
        conversation = self.conversation_repo.get_by_id_and_user(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        return conversation

    def update(
        self, conversation_id: int, user_id: int, title: str
    ) -> Conversation:
        """
        更新对话标题

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）
            title: 新标题

        Returns:
            Conversation: 更新后的对话对象

        Raises:
            ConversationNotFoundError: 对话不存在或不属于该用户
        """
        conversation = self.conversation_repo.update(
            conversation_id=conversation_id, user_id=user_id, title=title
        )

        if not conversation:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        return conversation

    def delete(self, conversation_id: int, user_id: int) -> bool:
        """
        软删除对话

        将对话的is_deleted字段标记为True，而非物理删除。

        Args:
            conversation_id: 对话ID
            user_id: 用户ID（用于权限验证）

        Returns:
            bool: 删除成功返回True

        Raises:
            ConversationNotFoundError: 对话不存在或不属于该用户
        """
        success = self.conversation_repo.soft_delete(
            conversation_id=conversation_id, user_id=user_id
        )

        if not success:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        return True

    def update_title(
        self, conversation_id: int, title: str
    ) -> Optional[Conversation]:
        """
        更新对话标题（不验证用户）

        用于系统自动生成标题等场景。

        Args:
            conversation_id: 对话ID
            title: 新标题

        Returns:
            Optional[Conversation]: 更新后的对话对象
        """
        return self.conversation_repo.update_title(
            conversation_id=conversation_id, title=title
        )

    def exists(self, conversation_id: int, user_id: int) -> bool:
        """
        检查对话是否存在且属于指定用户

        Args:
            conversation_id: 对话ID
            user_id: 用户ID

        Returns:
            bool: 存在返回True，否则返回False
        """
        return self.conversation_repo.exists(
            conversation_id=conversation_id, user_id=user_id
        )


__all__ = [
    "ConversationManagementService",
]
