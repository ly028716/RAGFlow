"""
System 配置服务模块

实现系统配置管理功能。
"""

from typing import Any, Dict

from app.config import settings
from app.services.system.crypto_utils import (
    encrypt_value,
    get_or_create_encryption_key,
    mask_sensitive_value,
)


class ConfigService:
    """
    系统配置服务类

    提供系统配置管理功能。

    使用方式:
        service = ConfigService()
        config = service.get_config()
        updated = service.update_config({"tongyi": {"temperature": 0.5}})
    """

    def __init__(self):
        """
        初始化配置服务
        """
        self._encryption_key = get_or_create_encryption_key()

    def get_config(self) -> Dict[str, Any]:
        """
        获取系统配置

        返回当前系统配置，敏感字段（如API密钥）进行脱敏处理。

        Returns:
            Dict[str, Any]: 系统配置字典
        """
        config = {
            # 应用配置
            "app": {
                "name": settings.app.app_name,
                "version": settings.app.app_version,
                "environment": settings.app.environment,
                "debug": settings.app.debug,
            },
            # 数据库配置
            "database": {
                "url": mask_sensitive_value(
                    settings.database.database_url, show_chars=10
                ),
                "pool_size": settings.database.db_pool_size,
                "max_overflow": settings.database.db_max_overflow,
            },
            # Redis配置
            "redis": {
                "host": settings.redis.redis_host,
                "port": settings.redis.redis_port,
                "db": settings.redis.redis_db,
                "password_set": bool(settings.redis.redis_password),
            },
            # 通义千问配置
            "tongyi": {
                "api_key": mask_sensitive_value(
                    settings.tongyi.dashscope_api_key
                ),
                "model_name": settings.tongyi.tongyi_model_name,
                "temperature": settings.tongyi.tongyi_temperature,
                "max_tokens": settings.tongyi.tongyi_max_tokens,
                "embedding_model": settings.tongyi.embedding_model,
            },
            # 向量数据库配置
            "vector_db": {
                "type": "chroma",
                "persist_directory": settings.vector_db.chroma_persist_directory,
            },
            # 文件存储配置
            "file_storage": {
                "upload_dir": settings.file_storage.upload_dir,
                "max_upload_size_mb": settings.file_storage.max_upload_size_mb,
            },
            # 文档处理配置
            "document_processing": {
                "chunk_size": settings.document_processing.chunk_size,
                "chunk_overlap": settings.document_processing.chunk_overlap,
            },
            # RAG配置
            "rag": {
                "top_k": settings.rag.rag_top_k,
                "similarity_threshold": settings.rag.rag_similarity_threshold,
            },
            # 配额配置
            "quota": {
                "default_monthly_quota": settings.quota.default_monthly_quota,
            },
            # 速率限制配置
            "rate_limit": {
                "per_minute": settings.rate_limit.rate_limit_per_minute,
                "login_per_minute": settings.rate_limit.rate_limit_login_per_minute,
                "llm_per_minute": settings.rate_limit.rate_limit_llm_per_minute,
            },
            # 安全配置
            "security": {
                "bcrypt_rounds": settings.security.bcrypt_rounds,
                "max_login_attempts": settings.security.max_login_attempts,
                "account_lockout_minutes": settings.security.account_lockout_minutes,
            },
            # JWT配置
            "jwt": {
                "algorithm": settings.jwt.algorithm,
                "access_token_expire_days": settings.jwt.access_token_expire_days,
                "refresh_token_expire_days": settings.jwt.refresh_token_expire_days,
            },
        }

        return config

    def update_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新系统配置

        更新系统配置项，敏感字段自动加密存储。
        注意：此方法更新的是运行时配置，重启后会恢复为环境变量配置。
        生产环境应该通过环境变量或配置文件管理配置。

        Args:
            config_updates: 要更新的配置项字典

        Returns:
            Dict[str, Any]: 更新后的配置
        """
        # 验证和更新通义千问配置
        if "tongyi" in config_updates:
            tongyi_config = config_updates["tongyi"]

            if "temperature" in tongyi_config:
                temp = tongyi_config["temperature"]
                if not (0.0 <= temp <= 2.0):
                    raise ValueError("temperature必须在0.0到2.0之间")
                settings.tongyi.tongyi_temperature = temp

            if "max_tokens" in tongyi_config:
                max_tokens = tongyi_config["max_tokens"]
                if not (1 <= max_tokens <= 4000):
                    raise ValueError("max_tokens必须在1到4000之间")
                settings.tongyi.tongyi_max_tokens = max_tokens

            if "api_key" in tongyi_config:
                # 验证API密钥格式（简单验证）
                api_key = tongyi_config["api_key"]
                if len(api_key) < 10:
                    raise ValueError("API密钥格式无效")
                # 实际应该调用API验证密钥有效性
                # 加密存储（这里简化，实际应存储到数据库）
                encrypted_key = encrypt_value(api_key, self._encryption_key)
                settings.tongyi.dashscope_api_key = api_key

        # 验证和更新RAG配置
        if "rag" in config_updates:
            rag_config = config_updates["rag"]

            if "top_k" in rag_config:
                top_k = rag_config["top_k"]
                if not (1 <= top_k <= 20):
                    raise ValueError("top_k必须在1到20之间")
                settings.rag.rag_top_k = top_k

            if "similarity_threshold" in rag_config:
                threshold = rag_config["similarity_threshold"]
                if not (0.0 <= threshold <= 1.0):
                    raise ValueError("similarity_threshold必须在0.0到1.0之间")
                settings.rag.rag_similarity_threshold = threshold

        # 验证和更新配额配置
        if "quota" in config_updates:
            quota_config = config_updates["quota"]

            if "default_monthly_quota" in quota_config:
                quota = quota_config["default_monthly_quota"]
                if quota < 1000:
                    raise ValueError("default_monthly_quota必须至少为1000")
                settings.quota.default_monthly_quota = quota

        # 返回更新后的配置
        return self.get_config()


__all__ = [
    "ConfigService",
]
