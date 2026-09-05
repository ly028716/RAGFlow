"""
用户数据访问层（Repository）

封装用户相关的数据库操作，提供统一的数据访问接口。
实现CRUD操作和用户字段唯一性检查。
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """
    用户Repository类

    提供用户数据的CRUD操作和查询功能。

    使用方式:
        repo = UserRepository(db)
        user = repo.create(username="test", password_hash="hash", email="test@example.com")
        user = repo.get_by_id(1)
    """

    def __init__(self, db: Session):
        """
        初始化Repository

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db

    def create(
        self,
        username: str,
        password_hash: str,
        email: Optional[str] = None,
        avatar: Optional[str] = None,
    ) -> User:
        """
        创建新用户

        Args:
            username: 用户名（必须唯一）
            password_hash: 密码哈希值
            email: 邮箱地址（可选，必须唯一）
            avatar: 头像URL（可选）

        Returns:
            User: 创建的用户对象

        Raises:
            IntegrityError: 用户名或资料邮箱已存在时抛出
        """
        user = User(
            username=username, password_hash=password_hash, email=email, avatar=avatar
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 用户对象，不存在则返回None
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户

        Args:
            username: 用户名

        Returns:
            Optional[User]: 用户对象，不存在则返回None
        """
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户

        Args:
            email: 邮箱地址

        Returns:
            Optional[User]: 用户对象，不存在则返回None
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        获取所有用户（分页）

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            List[User]: 用户列表
        """
        return self.db.query(User).offset(skip).limit(limit).all()

    def update(
        self,
        user_id: int,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        avatar: Optional[str] = None,
        is_active: Optional[bool] = None,
        last_login: Optional[datetime] = None,
    ) -> Optional[User]:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            username: 新用户名（可选）
            email: 新邮箱（可选）
            password_hash: 新密码哈希（可选）
            avatar: 新头像URL（可选）
            is_active: 是否激活（可选）
            last_login: 最后登录时间（可选）

        Returns:
            Optional[User]: 更新后的用户对象，用户不存在则返回None

        Raises:
            IntegrityError: 用户名或资料邮箱已被其他用户使用时抛出
        """
        user = self.get_by_id(user_id)
        if not user:
            return None

        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        if password_hash is not None:
            user.password_hash = password_hash
        if avatar is not None:
            user.avatar = avatar
        if is_active is not None:
            user.is_active = is_active
        if last_login is not None:
            user.last_login = last_login

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: int) -> bool:
        """
        删除用户

        Args:
            user_id: 用户ID

        Returns:
            bool: 删除成功返回True，用户不存在返回False
        """
        user = self.get_by_id(user_id)
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()
        return True

    def username_exists(
        self, username: str, exclude_user_id: Optional[int] = None
    ) -> bool:
        """
        检查用户名是否已存在

        Args:
            username: 要检查的用户名
            exclude_user_id: 排除的用户ID（用于更新时排除自己）

        Returns:
            bool: 用户名已存在返回True，否则返回False
        """
        query = self.db.query(User).filter(User.username == username)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    def email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        检查邮箱是否已存在

        Args:
            email: 要检查的邮箱
            exclude_user_id: 排除的用户ID（用于更新时排除自己）

        Returns:
            bool: 邮箱已存在返回True，否则返回False
        """
        if email is None:
            return False

        query = self.db.query(User).filter(User.email == email)
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return query.first() is not None

    def update_last_login(self, user_id: int) -> Optional[User]:
        """
        更新用户最后登录时间

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 更新后的用户对象，用户不存在则返回None
        """
        return self.update(user_id, last_login=datetime.utcnow())

    def deactivate(self, user_id: int) -> Optional[User]:
        """
        停用用户账户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 更新后的用户对象，用户不存在则返回None
        """
        return self.update(user_id, is_active=False)

    def activate(self, user_id: int) -> Optional[User]:
        """
        激活用户账户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 更新后的用户对象，用户不存在则返回None
        """
        return self.update(user_id, is_active=True)

    def count(self) -> int:
        """
        获取用户总数

        Returns:
            int: 用户总数
        """
        return self.db.query(User).count()

    def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        获取所有激活的用户（分页）

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            List[User]: 激活用户列表
        """
        return (
            self.db.query(User)
            .filter(User.is_active.is_(True))
            .offset(skip)
            .limit(limit)
            .all()
        )


# 导出
__all__ = ["UserRepository"]
