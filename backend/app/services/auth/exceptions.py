"""
Auth 服务异常模块

定义认证相关的所有异常类。
"""


class AuthServiceError(Exception):
    """认证服务异常基类"""
    pass


class UserAlreadyExistsError(AuthServiceError):
    """用户已存在异常"""
    pass


class InvalidCredentialsError(AuthServiceError):
    """凭证无效异常"""
    pass


class AccountLockedError(AuthServiceError):
    """账户已锁定异常"""

    def __init__(self, message: str, remaining_minutes: int = 0):
        super().__init__(message)
        self.remaining_minutes = remaining_minutes


class UserNotFoundError(AuthServiceError):
    """用户不存在异常"""
    pass


class PasswordMismatchError(AuthServiceError):
    """密码不匹配异常"""
    pass


__all__ = [
    "AuthServiceError",
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "UserNotFoundError",
    "PasswordMismatchError",
]
