"""
Auth 注册服务模块

实现用户注册功能。
"""

import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth.exceptions import UserAlreadyExistsError

logger = logging.getLogger(__name__)


class RegistrationService:
    """
    用户注册服务类

    提供用户注册功能。

    使用方式:
        service = RegistrationService(db)
        user = service.register("username", "password123", "email@example.com")
    """

    def __init__(self, db: Session):
        """
        初始化注册服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.user_repo = UserRepository(db)

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
        # 检查用户名是否已存在
        if self.user_repo.username_exists(username):
            raise UserAlreadyExistsError(f"用户名 '{username}' 已存在")

        # 检查邮箱是否已存在
        if email and self.user_repo.email_exists(email):
            raise UserAlreadyExistsError(f"邮箱 '{email}' 已被注册")

        # 加密密码
        password_hash = hash_password(password)

        # 创建用户
        try:
            user = self.user_repo.create(
                username=username, password_hash=password_hash, email=email
            )
            return user
        except IntegrityError:
            self.db.rollback()
            raise UserAlreadyExistsError("用户名或邮箱已存在")


__all__ = [
    "RegistrationService",
]
