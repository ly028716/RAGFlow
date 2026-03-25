"""
服务层模块

提供业务逻辑处理服务。
"""

from app.services.auth import (AccountLockedError, AuthService, AuthServiceError,
                               InvalidCredentialsError, PasswordMismatchError,
                               UserAlreadyExistsError, UserNotFoundError)
from app.services.conversation import (ConversationAccessDeniedError,
                                               ConversationNotFoundError,
                                               ConversationService,
                                               ConversationServiceError)
from app.services.file_service import FileService, file_service
from app.services.knowledge_base_permission import (
    PERMISSION_LEVELS, KnowledgeBasePermissionService)
from app.services.quota import (InsufficientQuotaError, InvalidQuotaValueError,
                                QuotaNotFoundError, QuotaService, QuotaServiceError)
from app.services.system_prompt_service import SystemPromptService

__all__ = [
    # 认证服务
    "AuthService",
    "AuthServiceError",
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "UserNotFoundError",
    "PasswordMismatchError",
    # 对话服务
    "ConversationService",
    "ConversationServiceError",
    "ConversationNotFoundError",
    "ConversationAccessDeniedError",
    # 配额服务
    "QuotaService",
    "QuotaServiceError",
    "QuotaNotFoundError",
    "InsufficientQuotaError",
    "InvalidQuotaValueError",
    # 文件服务
    "FileService",
    "file_service",
    # 系统提示词服务
    "SystemPromptService",
    # 知识库权限服务
    "KnowledgeBasePermissionService",
    "PERMISSION_LEVELS",
]
