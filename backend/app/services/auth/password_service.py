"""
Auth 密码服务模块

实现密码修改功能。
"""

import logging

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.services.auth.exceptions import PasswordMismatchError, UserNotFoundError

logger = logging.getLogger(__name__)


class PasswordService:
    """
    密码服务类

    提供密码修改功能。

    使用方式:
        service = PasswordService(db)
        service.change_password(user_id=1, old_password="old", new_password="new")
    """

    def __init__(self, db: Session):
        """
        初始化密码服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.user_repo = UserRepository(db)

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
        # 获取用户
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError("用户不存在")

        # 验证旧密码
        if not verify_password(old_password, user.password_hash):
            raise PasswordMismatchError("旧密码不正确")

        # 加密新密码
        new_password_hash = hash_password(new_password)

        # 更新密码
        self.user_repo.update(user_id, password_hash=new_password_hash)

        return True


__all__ = [
    "PasswordService",
]
