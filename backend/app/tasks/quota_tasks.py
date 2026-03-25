"""
配额重置定时任务模块

实现用户配额的定时重置功能，在每月1日自动重置所有用户的配额。
使用APScheduler配置定时任务。

需求引用:
    - 需求11.6: 每月1日自动重置所有用户的配额
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.quota import QuotaService

# 配置日志
logger = logging.getLogger(__name__)


def reset_monthly_quotas() -> dict:
    """
    重置所有过期的用户配额

    此函数由定时任务调度器在每月1日执行。
    重置所有需要重置的用户配额，将已使用配额清零。

    Returns:
        dict: 包含执行结果的字典
            - success: 是否成功
            - reset_count: 重置的配额数量
            - message: 执行消息
            - timestamp: 执行时间

    需求引用:
        - 需求11.6: 每月1日自动重置所有用户的配额

    使用方式:
        # 手动调用（用于测试）
        result = reset_monthly_quotas()
        print(f"重置了 {result['reset_count']} 个用户的配额")

        # 由APScheduler自动调用
        scheduler.add_job(
            reset_monthly_quotas,
            trigger='cron',
            day=1,
            hour=0,
            minute=0
        )
    """
    db: Optional[Session] = None
    start_time = datetime.utcnow()

    try:
        logger.info("开始执行月度配额重置任务")

        # 创建数据库会话
        db = SessionLocal()

        # 创建配额服务实例
        quota_service = QuotaService(db)

        # 执行重置
        reset_count = quota_service.reset_all_quotas()

        # 提交事务
        db.commit()

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"月度配额重置任务完成: 重置了 {reset_count} 个用户的配额, " f"耗时 {duration:.2f} 秒")

        return {
            "success": True,
            "reset_count": reset_count,
            "message": f"成功重置 {reset_count} 个用户的配额",
            "timestamp": end_time.isoformat(),
            "duration_seconds": duration,
        }

    except Exception as e:
        logger.error(f"月度配额重置任务失败: {str(e)}", exc_info=True)

        # 回滚事务
        if db:
            db.rollback()

        return {
            "success": False,
            "reset_count": 0,
            "message": f"配额重置失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }

    finally:
        # 关闭数据库会话
        if db:
            db.close()


def reset_single_user_quota(user_id: int) -> dict:
    """
    重置单个用户的配额（管理员功能或手动触发）

    Args:
        user_id: 用户ID

    Returns:
        dict: 包含执行结果的字典
            - success: 是否成功
            - user_id: 用户ID
            - message: 执行消息
            - timestamp: 执行时间

    使用方式:
        # 手动重置特定用户的配额
        result = reset_single_user_quota(user_id=123)
        if result['success']:
            print(f"用户 {user_id} 的配额已重置")
    """
    db: Optional[Session] = None

    try:
        logger.info(f"开始重置用户 {user_id} 的配额")

        # 创建数据库会话
        db = SessionLocal()

        # 创建配额服务实例
        quota_service = QuotaService(db)

        # 重置用户配额
        quota = quota_service.reset_monthly_quota(user_id)

        # 提交事务
        db.commit()

        logger.info(f"用户 {user_id} 的配额重置成功")

        return {
            "success": True,
            "user_id": user_id,
            "monthly_quota": quota.monthly_quota,
            "used_quota": quota.used_quota,
            "reset_date": quota.reset_date.isoformat(),
            "message": f"用户 {user_id} 的配额已重置",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"重置用户 {user_id} 的配额失败: {str(e)}", exc_info=True)

        # 回滚事务
        if db:
            db.rollback()

        return {
            "success": False,
            "user_id": user_id,
            "message": f"配额重置失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }

    finally:
        # 关闭数据库会话
        if db:
            db.close()


# 导出
__all__ = [
    "reset_monthly_quotas",
    "reset_single_user_quota",
]
