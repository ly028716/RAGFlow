"""
Auth 服务包

提供用户认证相关的所有服务。

导出:
    - AuthService: 认证服务 Facade
    - RegistrationService: 注册服务
    - LoginService: 登录服务
    - PasswordService: 密码服务
    - LockoutService: 账户锁定服务
    - 异常类: AuthServiceError, UserAlreadyExistsError, etc.

使用示例:
    from app.services.auth import AuthService
    from app.services.auth.exceptions import InvalidCredentialsError

    auth_service = AuthService(db)
    try:
        tokens = auth_service.login("username", "password")
    except InvalidCredentialsError:
        print("登录失败")
"""

from app.services.auth.auth_service import AuthService
from app.services.auth.exceptions import (
    AccountLockedError,
    AuthServiceError,
    InvalidCredentialsError,
    PasswordMismatchError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.services.auth.lockout_service import LockoutService
from app.services.auth.login_service import LoginService
from app.services.auth.password_service import PasswordService
from app.services.auth.registration_service import RegistrationService

__all__ = [
    # Facade
    "AuthService",
    # Sub-services
    "RegistrationService",
    "LoginService",
    "PasswordService",
    "LockoutService",
    # Exceptions
    "AuthServiceError",
    "UserAlreadyExistsError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "UserNotFoundError",
    "PasswordMismatchError",
]
