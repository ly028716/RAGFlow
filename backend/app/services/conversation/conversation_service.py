"""
Conversation 服务模块 (Facade)

此模块现在作为 Facade，内部委托给子服务。
所有实际功能已迁移到 app.services.conversation 包中的子服务。

推荐使用方式:
    from app.services.conversation import (
        ConversationManagementService,
        MessageService,
        ExportService,
        TitleService,
    )

向后兼容用法:
    from app.services.conversation import ConversationService
    service = ConversationService(db)  # 内部委托给子服务
"""

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole

from app.services.conversation.export_service import ExportService
from app.services.conversation.management_service import ConversationManagementService
from app.services.conversation.message_service import MessageService
from app.services.conversation.title_service import TitleService


class ConversationService:
    """
    对话服务类 (Facade)

    提供对话管理功能。
    此服务现在作为 Facade，内部委托给子服务。

    向后兼容用法:
        service = ConversationService(db)
        conversation = service.create_conversation(...)

    推荐新用法:
        from app.services.conversation import ConversationManagementService, MessageService
        mgmt_service = ConversationManagementService(db)
        msg_service = MessageService(db)
    """

    def __init__(self, db: Session):
        """
        初始化对话服务

        Args:
            db: 数据库会话
        """
        self.db = db
        # 初始化子服务
        self._mgmt_service = ConversationManagementService(db)
        self._msg_service = MessageService(db)
        self._export_service = ExportService()
        self._title_service = TitleService()

    # ==================== 对话管理 (委托给 ConversationManagementService) ====================

    def create_conversation(self, user_id: int, title: str = "新对话") -> Conversation:
        """创建新对话"""
        return self._mgmt_service.create(user_id=user_id, title=title)

    def get_conversations(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> Tuple[List[dict], int]:
        """获取用户的对话列表"""
        return self._mgmt_service.get_list(user_id=user_id, skip=skip, limit=limit)

    def get_conversation(self, conversation_id: int, user_id: int) -> Conversation:
        """获取单个对话"""
        return self._mgmt_service.get_by_id(conversation_id, user_id)

    def update_conversation(
        self, conversation_id: int, user_id: int, title: str
    ) -> Conversation:
        """更新对话标题"""
        return self._mgmt_service.update(conversation_id, user_id, title)

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """软删除对话"""
        return self._mgmt_service.delete(conversation_id, user_id)

    def update_conversation_title(
        self, conversation_id: int, title: str
    ) -> Optional[Conversation]:
        """更新对话标题（不验证用户）"""
        return self._mgmt_service.update_title(conversation_id, title)

    def conversation_exists(self, conversation_id: int, user_id: int) -> bool:
        """检查对话是否存在且属于指定用户"""
        return self._mgmt_service.exists(conversation_id, user_id)

    # ==================== 消息管理 (委托给 MessageService) ====================

    def get_messages(
        self,
        conversation_id: int,
        user_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """获取对话的所有消息"""
        return self._msg_service.get_list(conversation_id, user_id, skip, limit)

    def add_message(
        self,
        conversation_id: int,
        user_id: int,
        role: MessageRole,
        content: str,
        tokens: int = 0,
    ) -> Message:
        """添加消息到对话"""
        return self._msg_service.add(
            conversation_id, user_id, role, content, tokens
        )

    def get_recent_messages(
        self, conversation_id: int, user_id: int, limit: int = 10
    ) -> List[Message]:
        """获取对话的最近消息"""
        return self._msg_service.get_recent(conversation_id, user_id, limit)

    def get_conversation_token_usage(self, conversation_id: int, user_id: int) -> int:
        """获取对话的总token消耗"""
        return self._msg_service.get_token_usage(conversation_id, user_id)

    def is_first_user_message(self, conversation_id: int) -> bool:
        """检查对话是否还没有用户消息"""
        return self._msg_service.is_first_user_message(conversation_id)

    # ==================== 导出功能 (委托给 ExportService) ====================

    def export_conversation(
        self, conversation_id: int, user_id: int, format: str = "markdown"
    ) -> str:
        """导出对话内容"""
        from app.services.conversation.exceptions import ConversationNotFoundError
        from app.repositories.conversation_repository import ConversationRepository
        from app.repositories.message_repository import MessageRepository

        conversation_repo = ConversationRepository(self.db)
        message_repo = MessageRepository(self.db)

        # 验证格式
        format = format.lower()
        if format not in ("markdown", "json", "md"):
            raise ValueError(f"不支持的导出格式: {format}，支持的格式: markdown, json")

        # 获取对话
        conversation = conversation_repo.get_by_id_and_user(
            conversation_id=conversation_id, user_id=user_id
        )

        if not conversation:
            raise ConversationNotFoundError(f"对话 {conversation_id} 不存在或无权访问")

        # 获取所有消息
        messages = message_repo.get_by_conversation(
            conversation_id=conversation_id, skip=0, limit=None, order_asc=True
        )

        return self._export_service.export(conversation, messages, format)

    # ==================== 标题生成 (委托给 TitleService) ====================

    async def generate_title(self, first_message: str, max_length: int = 20) -> str:
        """使用LLM根据第一条消息生成对话标题"""
        return await self._title_service.generate(first_message, max_length)

    def generate_title_sync(self, first_message: str, max_length: int = 20) -> str:
        """同步版本：使用LLM根据第一条消息生成对话标题"""
        return self._title_service.generate_sync(first_message, max_length)


__all__ = [
    "ConversationService",
]
