"""
Conversation 服务异常模块

定义 Conversation 相关的所有异常类。
"""


class ConversationServiceError(Exception):
    """对话服务异常基类"""
    pass


class ConversationNotFoundError(ConversationServiceError):
    """对话不存在异常"""
    pass


class ConversationAccessDeniedError(ConversationServiceError):
    """对话访问被拒绝异常"""
    pass


__all__ = [
    "ConversationServiceError",
    "ConversationNotFoundError",
    "ConversationAccessDeniedError",
]
