"""
Auth 登录服务模块

实现用户登录、令牌刷新和登出功能。
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    add_token_to_blacklist,
    create_token_pair,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth.exceptions import InvalidCredentialsError
from app.services.auth.lockout_service import LockoutService

logger = logging.getLogger(__name__)


class LoginService:
    """
    用户登录服务类

    提供用户登录、令牌刷新和登出功能。

    使用方式:
        service = LoginService(db)
        tokens = service.login("username", "password123", "127.0.0.1")
        new_tokens = service.refresh_token("refresh_token_string")
        service.logout("access_token", "refresh_token")
    """

    def __init__(self, db: Session):
        """
        初始化登录服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.user_repo = UserRepository(db)
        self.lockout_service = LockoutService()

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
        # 检查账户是否被锁定
        is_locked, remaining_minutes = self.lockout_service.check_account_locked(username)
        if is_locked:
            from app.services.auth.exceptions import AccountLockedError
            raise AccountLockedError(
                f"账户已被锁定，请在 {remaining_minutes} 分钟后重试",
                remaining_minutes=remaining_minutes,
            )

        # 获取用户
        user = self.user_repo.get_by_username(username)

        # 验证用户存在且密码正确
        if not user or not verify_password(password, user.password_hash):
            # 记录登录失败
            self.lockout_service.record_login_attempt(self.db, username, ip_address, success=False)
            self.lockout_service.increment_failed_attempts(username)
            raise InvalidCredentialsError("用户名或密码错误")

        # 检查用户是否激活
        if not user.is_active:
            self.lockout_service.record_login_attempt(self.db, username, ip_address, success=False)
            raise InvalidCredentialsError("账户已被禁用")

        # 登录成功，清除失败计数
        self.lockout_service.clear_failed_attempts(username)

        # 记录登录成功
        self.lockout_service.record_login_attempt(self.db, username, ip_address, success=True)

        # 更新最后登录时间
        self.user_repo.update_last_login(user.id)

        # 生成令牌对
        tokens = create_token_pair(user.id, user.username)

        return tokens

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
        # 验证刷新令牌
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise InvalidCredentialsError("刷新令牌无效或已过期")

        user_id = int(payload["sub"])
        username = payload["username"]

        # 验证用户是否存在且激活
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise InvalidCredentialsError("用户不存在或已被禁用")

        # 将旧的刷新令牌加入黑名单
        add_token_to_blacklist(refresh_token)

        # 生成新的令牌对
        tokens = create_token_pair(user.id, user.username)

        return tokens

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
        # 将访问令牌加入黑名单
        add_token_to_blacklist(access_token)

        # 如果提供了刷新令牌，也加入黑名单
        if refresh_token:
            add_token_to_blacklist(refresh_token)

        return True


__all__ = [
    "LoginService",
]
