"""
System 健康检查服务模块

实现系统健康检查功能。
"""

import shutil
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import engine
from app.core.redis import get_redis_client, ping_redis
from app.core.vector_store import get_vector_store


class HealthService:
    """
    系统健康检查服务类

    提供系统健康检查功能。

    使用方式:
        service = HealthService(db)
        health = service.health_check(detailed=True)
    """

    def __init__(self, db: Session):
        """
        初始化健康检查服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db

    def health_check(self, detailed: bool = True) -> Dict[str, Any]:
        """
        系统健康检查

        检查各个组件的连接状态和健康状况。

        Returns:
            Dict[str, Any]: 健康检查结果
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
        }

        # 检查MySQL数据库
        try:
            # 执行简单查询测试连接
            self.db.execute(text("SELECT 1"))
            health_status["components"]["database"] = {
                "status": "healthy",
                "type": "mysql",
                "message": "数据库连接正常",
            }
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "type": "mysql",
                "message": f"数据库连接失败: {str(e)}" if detailed else "数据库连接失败",
            }

        # 检查Redis
        try:
            redis_ok = ping_redis()
            if redis_ok:
                redis_client = get_redis_client()
                health_status["components"]["redis"] = {
                    "status": "healthy",
                    "message": "Redis连接正常",
                }
                if detailed:
                    info = redis_client.info()
                    health_status["components"]["redis"].update(
                        {
                            "version": info.get("redis_version", "unknown"),
                            "connected_clients": info.get("connected_clients", 0),
                            "used_memory_human": info.get(
                                "used_memory_human", "unknown"
                            ),
                        }
                    )
            else:
                raise Exception("Redis ping失败")
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": f"Redis连接失败: {str(e)}" if detailed else "Redis连接失败",
            }

        # 检查向量数据库（Chroma）
        try:
            # 尝试获取向量存储实例
            # 这里使用一个测试集合名称
            vector_store = get_vector_store(knowledge_base_id=0)  # 使用特殊ID 0作为健康检查
            health_status["components"]["vector_db"] = {
                "status": "healthy",
                "type": "chroma",
                "message": "向量数据库连接正常",
            }
            if detailed:
                health_status["components"]["vector_db"]["persist_directory"] = (
                    settings.vector_db.chroma_persist_directory
                )
        except Exception as e:
            health_status["status"] = "degraded"  # 向量数据库不是关键组件，降级而非不健康
            health_status["components"]["vector_db"] = {
                "status": "unhealthy",
                "type": "chroma",
                "message": f"向量数据库连接失败: {str(e)}" if detailed else "向量数据库连接失败",
            }

        # 检查磁盘空间（可选）
        try:
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (2**30)
            health_status["components"]["disk"] = {
                "status": "healthy" if free_gb > 1 else "warning",
                "free_space_gb": free_gb,
                "message": f"可用磁盘空间: {free_gb}GB",
            }
        except Exception as e:
            health_status["components"]["disk"] = {
                "status": "unknown",
                "message": f"无法获取磁盘信息: {str(e)}" if detailed else "无法获取磁盘信息",
            }

        return health_status


__all__ = [
    "HealthService",
]
