"""
Conversation 服务包

提供对话管理功能。

使用方式:
    from app.services.conversation import ConversationService
    service = ConversationService(db)
    conversation = service.create_conversation(...)

或者使用子服务:
    from app.services.conversation import (
        ConversationManagementService,
        MessageService,
        ExportService,
        TitleService,
    )
"""

# 子服务
from app.services.conversation.conversation_service import ConversationService
from app.services.conversation.export_service import ExportService
from app.services.conversation.management_service import ConversationManagementService
from app.services.conversation.message_service import MessageService
from app.services.conversation.title_service import TitleService

# 异常
from app.services.conversation.exceptions import (
    ConversationAccessDeniedError,
    ConversationNotFoundError,
    ConversationServiceError,
)

__all__ = [
    # 服务类
    "ConversationService",
    "ConversationManagementService",
    "MessageService",
    "ExportService",
    "TitleService",
    # 异常
    "ConversationServiceError",
    "ConversationNotFoundError",
    "ConversationAccessDeniedError",
]
