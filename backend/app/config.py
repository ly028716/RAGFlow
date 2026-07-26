"""
配置管理模块

使用pydantic-settings从环境变量加载配置，提供配置验证和默认值。
支持数据库、Redis、JWT、文件存储、LLM等各类配置。
"""

import os
from typing import List, Optional

from pydantic import AliasChoices, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET_KEY = "your-secret-key-here-change-in-production"
DEFAULT_DASHSCOPE_API_KEY = "your-dashscope-api-key-here"


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="mysql+pymysql://user:password@localhost:3306/ai_assistant",
        description="数据库连接URL",
    )
    db_pool_size: int = Field(default=10, ge=1, le=50, description="连接池大小")
    db_max_overflow: int = Field(default=20, ge=0, le=100, description="连接池最大溢出")
    db_pool_recycle: int = Field(default=3600, ge=300, description="连接回收时间（秒）")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or not v.startswith(("mysql", "postgresql", "sqlite")):
            raise ValueError("数据库URL必须以mysql、postgresql或sqlite开头")
        return v


class RedisSettings(BaseSettings):
    """Redis配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    redis_host: str = Field(default="localhost", description="Redis主机地址")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis端口")
    redis_password: Optional[str] = Field(default=None, description="Redis密码")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis数据库编号")

    @property
    def redis_url(self) -> str:
        """构建Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class JWTSettings(BaseSettings):
    """JWT认证配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    secret_key: str = Field(
        default=DEFAULT_JWT_SECRET_KEY,
        min_length=32,
        description="JWT密钥",
    )
    algorithm: str = Field(default="HS256", description="JWT算法")
    access_token_expire_days: int = Field(
        default=7, ge=1, le=365, description="访问令牌有效期（天）"
    )
    refresh_token_expire_days: int = Field(
        default=30, ge=1, le=365, description="刷新令牌有效期（天）"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT密钥长度必须至少32个字符")
        return v


class SecuritySettings(BaseSettings):
    """安全配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    bcrypt_rounds: int = Field(default=12, ge=10, le=15, description="Bcrypt工作因子")
    max_login_attempts: int = Field(default=5, ge=3, le=10, description="最大登录尝试次数")
    account_lockout_minutes: int = Field(
        default=15, ge=5, le=60, description="账户锁定时长（分钟）"
    )


class TongyiSettings(BaseSettings):
    """通义千问API配置"""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    dashscope_api_key: str = Field(
        default=DEFAULT_DASHSCOPE_API_KEY,
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "API_KEY"),
        description="DashScope API密钥",
    )
    tongyi_model_name: str = Field(default="qwen-turbo", description="模型名称")
    tongyi_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    tongyi_max_tokens: int = Field(default=2000, ge=1, le=4000, description="最大token数")
    embedding_model: str = Field(default="text-embedding-v1", description="嵌入模型名称")

    @field_validator("dashscope_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        api_key_env = (os.getenv("API_KEY") or "").strip()
        if api_key_env and not cls._is_placeholder_key(api_key_env):
            if cls._is_placeholder_key(v):
                v = api_key_env

        env = (os.getenv("ENVIRONMENT") or "development").strip().lower()
        debug_raw = (os.getenv("DEBUG") or "false").strip().lower()
        debug = debug_raw in ("1", "true", "yes", "y", "on")

        if env == "development" or debug:
            return v

        key = (v or "").strip()
        if (
            not key
            or key == DEFAULT_DASHSCOPE_API_KEY
            or key == "DUMMY_DASHSCOPE_API_KEY"
            or key == "sk-INSERT_YOUR_KEY_HERE"
            or "YOUR_DASHSCOPE_API_KEY" in key
            or "INSERT_YOUR_KEY" in key
        ):
            raise ValueError("请配置有效的DashScope API密钥")
        return v

    @staticmethod
    def _is_placeholder_key(api_key: Optional[str]) -> bool:
        if not api_key:
            return True
        key = api_key.strip()
        if not key:
            return True
        if key == DEFAULT_DASHSCOPE_API_KEY:
            return True
        if key == "DUMMY_DASHSCOPE_API_KEY":
            return True
        if key == "sk-INSERT_YOUR_KEY_HERE":
            return True
        if "YOUR_DASHSCOPE_API_KEY" in key or "INSERT_YOUR_KEY" in key:
            return True
        return False


class VectorDBSettings(BaseSettings):
    """向量数据库配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    chroma_persist_directory: str = Field(
        default="./data/chroma", description="Chroma持久化目录"
    )
    chroma_collection_name: str = Field(default="documents", description="默认集合名称")


class FileStorageSettings(BaseSettings):
    """文件存储配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    upload_dir: str = Field(default="./data/uploads", description="上传文件目录")
    max_upload_size_mb: int = Field(
        default=10, ge=1, le=100, description="最大上传文件大小（MB）"
    )

    @property
    def max_upload_size_bytes(self) -> int:
        """返回字节单位的最大上传大小"""
        return self.max_upload_size_mb * 1024 * 1024


class DocumentProcessingSettings(BaseSettings):
    """文档处理配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    chunk_size: int = Field(default=1000, ge=100, le=5000, description="文档分块大小")
    chunk_overlap: int = Field(default=200, ge=0, le=1000, description="分块重叠大小")


class RAGSettings(BaseSettings):
    """RAG配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    rag_top_k: int = Field(default=5, ge=1, le=20, description="检索文档数量")
    rag_similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="相似度阈值"
    )


class QuotaSettings(BaseSettings):
    """配额配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    default_monthly_quota: int = Field(
        default=100000, ge=1000, description="默认月度配额（tokens）"
    )


class RateLimitSettings(BaseSettings):
    """速率限制配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    rate_limit_per_minute: int = Field(default=100, ge=10, description="普通API每分钟请求限制")
    rate_limit_login_per_minute: int = Field(
        default=5, ge=1, description="登录API每分钟请求限制"
    )
    rate_limit_llm_per_minute: int = Field(default=20, ge=1, description="LLM调用每分钟请求限制")


class LoggingSettings(BaseSettings):
    """日志配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="./logs/app.log", description="日志文件路径")
    log_max_bytes: int = Field(default=10485760, ge=1048576, description="日志文件最大大小（字节）")
    log_backup_count: int = Field(default=10, ge=1, le=100, description="日志备份数量")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"日志级别必须是以下之一: {', '.join(valid_levels)}")
        return v_upper


class CORSSettings(BaseSettings):
    """CORS配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="允许的CORS源（逗号分隔）",
    )
    cors_allow_credentials: bool = Field(default=True, description="是否允许凭证")

    @property
    def origins_list(self) -> List[str]:
        """返回CORS源列表"""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


class MonitoringSettings(BaseSettings):
    """监控配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    enable_metrics: bool = Field(default=True, description="是否启用Prometheus指标")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="指标端口")


class BackgroundTaskSettings(BaseSettings):
    """后台任务配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    enable_scheduler: bool = Field(default=True, description="是否启用定时任务调度器")
    quota_reset_cron: str = Field(default="0 0 1 * *", description="配额重置Cron表达式")


class WebSocketSettings(BaseSettings):
    """WebSocket配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    ws_heartbeat_interval: int = Field(default=30, ge=10, le=300, description="心跳间隔（秒）")


class AgentToolsSettings(BaseSettings):
    """Agent工具配置"""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    agent_tool_allowed_hosts: str = Field(
        default="",
        description="允许的HTTP工具目标Host（逗号分隔）。生产/预发布环境为空将拒绝创建/执行http_api工具。",
    )
    agent_tool_default_timeout_ms: int = Field(
        default=8000, ge=100, le=60000, description="HTTP工具默认超时（毫秒）"
    )
    agent_tool_default_output_max_chars: int = Field(
        default=4000, ge=256, le=20000, description="HTTP工具默认输出最大字符数"
    )

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip().lower() for h in self.agent_tool_allowed_hosts.split(",") if h.strip()]


class AppSettings(BaseSettings):
    """应用主配置"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # 应用基本信息
    app_name: str = Field(default="AI智能助手系统", description="应用名称")
    app_version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    environment: str = Field(default="development", description="运行环境")

    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, ge=1024, le=65535, description="服务器端口")
    trust_proxy_headers: bool = Field(
        default=False,
        description="是否信任反向代理头（X-Forwarded-For/X-Real-IP）",
    )
    trusted_proxy_ips: str = Field(
        default="127.0.0.1,::1",
        description="可信代理IP/CIDR列表（逗号分隔），仅在 trust_proxy_headers=true 时生效",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"环境必须是以下之一: {', '.join(valid_envs)}")
        return v


class Settings:
    """
    全局配置类，整合所有配置模块

    使用方式:
        from app.config import settings

        # 访问数据库配置
        db_url = settings.database.database_url

        # 访问Redis配置
        redis_url = settings.redis.redis_url

        # 访问JWT配置
        secret = settings.jwt.secret_key
    """

    def __init__(self):
        # 应用配置
        self.app = AppSettings()
        self.debug = self.app.debug
        self.environment = self.app.environment

        # 数据库配置
        self.database = DatabaseSettings()

        # Redis配置
        self.redis = RedisSettings()

        # JWT配置
        self.jwt = JWTSettings()

        # 安全配置
        self.security = SecuritySettings()

        # 通义千问配置
        self.tongyi = TongyiSettings()

        # 向量数据库配置
        self.vector_db = VectorDBSettings()

        # 文件存储配置
        self.file_storage = FileStorageSettings()

        # 文档处理配置
        self.document_processing = DocumentProcessingSettings()

        # RAG配置
        self.rag = RAGSettings()

        # 配额配置
        self.quota = QuotaSettings()

        # 速率限制配置
        self.rate_limit = RateLimitSettings()

        # 日志配置
        self.logging = LoggingSettings()

        # CORS配置
        self.cors = CORSSettings()

        # 监控配置
        self.monitoring = MonitoringSettings()

        # 后台任务配置
        self.background_task = BackgroundTaskSettings()

        # WebSocket配置
        self.websocket = WebSocketSettings()

        # Agent工具配置
        self.agent_tools = AgentToolsSettings()

    def validate_all(self) -> bool:
        """
        验证所有配置的有效性

        Returns:
            bool: 所有配置是否有效
        """
        try:
            # 验证关键配置
            assert self.database.database_url, "数据库URL未配置"
            assert self.jwt.secret_key, "JWT密钥未配置"
            assert (
                self.tongyi.dashscope_api_key != DEFAULT_DASHSCOPE_API_KEY
            ), "DashScope API密钥未配置"
            if self.app.environment in ("staging", "production"):
                assert (
                    self.jwt.secret_key != DEFAULT_JWT_SECRET_KEY
                ), "生产/预发布环境必须配置JWT密钥"

            return True
        except (AssertionError, ValueError) as e:
            print(f"配置验证失败: {e}")
            return False

    def get_config_summary(self) -> dict:
        """
        获取配置摘要（用于调试和日志）

        Returns:
            dict: 配置摘要字典
        """
        return {
            "app_name": self.app.app_name,
            "app_version": self.app.app_version,
            "environment": self.app.environment,
            "debug": self.app.debug,
            "database_configured": bool(self.database.database_url),
            "redis_configured": bool(self.redis.redis_host),
            "jwt_configured": bool(self.jwt.secret_key)
            and self.jwt.secret_key != DEFAULT_JWT_SECRET_KEY,
            "tongyi_configured": self.tongyi.dashscope_api_key
            != DEFAULT_DASHSCOPE_API_KEY,
            "vector_db_path": self.vector_db.chroma_persist_directory,
            "upload_dir": self.file_storage.upload_dir,
        }


# 创建全局配置实例
settings = Settings()


# 导出常用配置（便于直接导入）
__all__ = [
    "Settings",
    "settings",
    "AppSettings",
    "DatabaseSettings",
    "RedisSettings",
    "JWTSettings",
    "SecuritySettings",
    "TongyiSettings",
    "VectorDBSettings",
    "FileStorageSettings",
    "DocumentProcessingSettings",
    "RAGSettings",
    "QuotaSettings",
    "RateLimitSettings",
    "LoggingSettings",
    "CORSSettings",
    "MonitoringSettings",
    "BackgroundTaskSettings",
    "WebSocketSettings",
    "AgentToolsSettings",
]
