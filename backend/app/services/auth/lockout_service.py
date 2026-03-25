"""
Auth 账户锁定服务模块

实现账户锁定管理功能。
"""

import logging
from typing import Tuple

from sqlalchemy.orm import Session

from app.config import settings
from app.core.redis import RedisKeys, get_redis_client
from app.models.login_attempt import LoginAttempt

logger = logging.getLogger(__name__)


class LockoutService:
    """
    账户锁定服务类

    提供账户锁定管理功能。

    使用方式:
        service = LockoutService()
        is_locked, minutes = service.check_account_locked("username")
        service.unlock_account("username")
    """

    def __init__(self):
        """
        初始化锁定服务
        """
        self.max_login_attempts = settings.security.max_login_attempts
        self.lockout_minutes = settings.security.account_lockout_minutes

    def check_account_locked(self, username: str) -> Tuple[bool, int]:
        """
        检查账户是否被锁定

        Args:
            username: 用户名

        Returns:
            Tuple[bool, int]: (是否锁定, 剩余锁定分钟数)
        """
        try:
            redis_client = get_redis_client()
            lock_key = RedisKeys.format_key(RedisKeys.ACCOUNT_LOCKED, username=username)

            ttl = redis_client.ttl(lock_key)
            if ttl > 0:
                remaining_minutes = (ttl + 59) // 60  # 向上取整
                return True, remaining_minutes

            return False, 0
        except Exception as e:
            logger.error(f"检查账户锁定状态失败: {e}")
            return False, 0

    def increment_failed_attempts(self, username: str) -> int:
        """
        增加登录失败次数

        如果达到最大失败次数，锁定账户。

        Args:
            username: 用户名

        Returns:
            int: 当前失败次数
        """
        try:
            redis_client = get_redis_client()
            attempts_key = RedisKeys.format_key(
                RedisKeys.LOGIN_ATTEMPTS, username=username
            )

            # 增加失败次数
            attempts = redis_client.incr(attempts_key)

            # 设置过期时间（锁定时长）
            redis_client.expire(attempts_key, self.lockout_minutes * 60)

            # 检查是否需要锁定账户
            if attempts >= self.max_login_attempts:
                self._lock_account(username)

            return attempts
        except Exception as e:
            logger.error(f"增加登录失败次数失败: {e}")
            return 0

    def clear_failed_attempts(self, username: str) -> None:
        """
        清除登录失败次数

        Args:
            username: 用户名
        """
        try:
            redis_client = get_redis_client()
            attempts_key = RedisKeys.format_key(
                RedisKeys.LOGIN_ATTEMPTS, username=username
            )
            redis_client.delete(attempts_key)
        except Exception as e:
            logger.error(f"清除登录失败次数失败: {e}")

    def _lock_account(self, username: str) -> None:
        """
        锁定账户

        Args:
            username: 用户名
        """
        try:
            redis_client = get_redis_client()
            lock_key = RedisKeys.format_key(RedisKeys.ACCOUNT_LOCKED, username=username)

            # 设置锁定标记，过期时间为锁定时长
            redis_client.setex(lock_key, self.lockout_minutes * 60, "1")
        except Exception as e:
            logger.error(f"锁定账户失败: {e}")

    def record_login_attempt(
        self, db: Session, username: str, ip_address: str, success: bool
    ) -> None:
        """
        记录登录尝试到数据库

        Args:
            db: SQLAlchemy数据库会话
            username: 用户名
            ip_address: IP地址
            success: 是否成功
        """
        try:
            login_attempt = LoginAttempt(
                username=username, ip_address=ip_address, success=success
            )
            db.add(login_attempt)
            db.commit()
        except Exception as e:
            logger.error(f"记录登录尝试失败: {e}")
            db.rollback()

    def get_failed_attempts(self, username: str) -> int:
        """
        获取当前登录失败次数

        Args:
            username: 用户名

        Returns:
            int: 当前失败次数
        """
        try:
            redis_client = get_redis_client()
            attempts_key = RedisKeys.format_key(
                RedisKeys.LOGIN_ATTEMPTS, username=username
            )

            attempts = redis_client.get(attempts_key)
            return int(attempts) if attempts else 0
        except Exception as e:
            logger.error(f"获取登录失败次数失败: {e}")
            return 0

    def unlock_account(self, username: str) -> bool:
        """
        解锁账户（管理员功能）

        Args:
            username: 用户名

        Returns:
            bool: 解锁是否成功
        """
        try:
            redis_client = get_redis_client()

            # 删除锁定标记
            lock_key = RedisKeys.format_key(RedisKeys.ACCOUNT_LOCKED, username=username)
            redis_client.delete(lock_key)

            # 清除失败次数
            self.clear_failed_attempts(username)

            return True
        except Exception as e:
            logger.error(f"解锁账户失败: {e}")
            return False


__all__ = [
    "LockoutService",
]
