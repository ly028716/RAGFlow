"""
Auth 认证服务 Facade

提供统一的认证服务接口，委托给各子服务处理。
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.services.auth.exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
    PasswordMismatchError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.services.auth.lockout_service import LockoutService
from app.services.auth.login_service import LoginService
from app.services.auth.password_service import PasswordService
from app.services.auth.registration_service import RegistrationService


class AuthService:
    """
    认证服务 Facade 类

    提供用户注册、登录、密码修改等认证功能。
    内部委托给各子服务处理，保持向后兼容。

    使用方式:
        auth_service = AuthService(db)
        user = auth_service.register("username", "password123", "email@example.com")
        tokens = auth_service.login("username", "password123", "127.0.0.1")
    """

    def __init__(self, db: Session):
        """
        初始化认证服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self._registration_service = RegistrationService(db)
        self._login_service = LoginService(db)
        self._password_service = PasswordService(db)
        self._lockout_service = LockoutService()

    def register(
        self, username: str, password: str, email: Optional[str] = None
    ) -> User:
        """
        用户注册

        创建新用户账户，包含用户名唯一性检查和密码加密。

        Args:
            username: 用户名（必须唯一）
            password: 明文密码（至少8位，包含字母和数字）
            email: 邮箱地址（可选，必须唯一）

        Returns:
            User: 创建的用户对象

        Raises:
            UserAlreadyExistsError: 用户名或邮箱已存在
        """
        return self._registration_service.register(username, password, email)

    def login(self, username: str, password: str, ip_address: str = "0.0.0.0") -> dict:
        """
        用户登录

        验证用户凭证，生成JWT令牌，记录登录尝试。

        Args:
            username: 用户名
            password: 明文密码
            ip_address: 登录请求的IP地址

        Returns:
            dict: 包含access_token, refresh_token, token_type, expires_in的字典

        Raises:
            AccountLockedError: 账户已被锁定
            InvalidCredentialsError: 用户名或密码错误
        """
        return self._login_service.login(username, password, ip_address)

    def refresh_token(self, refresh_token: str) -> dict:
        """
        刷新访问令牌

        使用刷新令牌获取新的访问令牌。

        Args:
            refresh_token: 刷新令牌

        Returns:
            dict: 包含新的access_token, refresh_token, token_type, expires_in的字典

        Raises:
            InvalidCredentialsError: 刷新令牌无效或已过期
        """
        return self._login_service.refresh_token(refresh_token)

    def change_password(
        self, user_id: int, old_password: str, new_password: str
    ) -> bool:
        """
        修改密码

        验证旧密码后更新为新密码。

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            bool: 密码修改是否成功

        Raises:
            UserNotFoundError: 用户不存在
            PasswordMismatchError: 旧密码不正确
        """
        return self._password_service.change_password(user_id, old_password, new_password)

    def logout(self, access_token: str, refresh_token: Optional[str] = None) -> bool:
        """
        用户登出

        将令牌加入黑名单，使其失效。

        Args:
            access_token: 访问令牌
            refresh_token: 刷新令牌（可选）

        Returns:
            bool: 登出是否成功
        """
        return self._login_service.logout(access_token, refresh_token)

    def get_failed_attempts(self, username: str) -> int:
        """
        获取当前登录失败次数

        Args:
            username: 用户名

        Returns:
            int: 当前失败次数
        """
        return self._lockout_service.get_failed_attempts(username)

    def unlock_account(self, username: str) -> bool:
        """
        解锁账户（管理员功能）

        Args:
            username: 用户名

        Returns:
            bool: 解锁是否成功
        """
        return self._lockout_service.unlock_account(username)


__all__ = [
    "AuthService",
]
