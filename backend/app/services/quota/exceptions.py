"""
配额服务异常模块

定义配额相关的所有异常类。
"""


class QuotaServiceError(Exception):
    """配额服务异常基类"""
    pass


class QuotaNotFoundError(QuotaServiceError):
    """配额记录不存在异常"""
    pass


class InsufficientQuotaError(QuotaServiceError):
    """配额不足异常"""

    def __init__(self, message: str, remaining: int = 0, required: int = 0):
        super().__init__(message)
        self.remaining = remaining
        self.required = required


class InvalidQuotaValueError(QuotaServiceError):
    """无效配额值异常"""
    pass


__all__ = [
    "QuotaServiceError",
    "QuotaNotFoundError",
    "InsufficientQuotaError",
    "InvalidQuotaValueError",
]
