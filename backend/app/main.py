"""
FastAPI应用主入口

配置FastAPI应用，注册路由，配置中间件，启动定时任务。
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session

# 必须在所有其他导入之前导入平台兼容性模块
# 用于在 Windows 平台上 mock Unix/Linux 特有的 pwd 和 grp 模块
import app.utils.platform_compat  # noqa: F401
from app.config import settings
from app.core.database import Base, engine, get_db
from app.middleware.error_handler import register_exception_handlers
from app.middleware.prometheus_middleware import PrometheusMiddleware
from app.middleware.rate_limiter import register_rate_limiter
from app.middleware.request_id import RequestIDMiddleware
from app.tasks.cleanup_tasks import run_all_cleanup_tasks
from app.tasks.quota_tasks import reset_monthly_quotas
from app.utils.logger import (get_logger, set_third_party_log_levels,
                              setup_logging)

# 配置日志系统
setup_logging()
set_third_party_log_levels()
logger = get_logger(__name__)


# 全局调度器实例
scheduler: AsyncIOScheduler = None


def setup_scheduler() -> AsyncIOScheduler:
    """
    配置并启动APScheduler定时任务调度器

    配置的定时任务:
        1. 配额重置任务: 每月1日凌晨0点执行
        2. 清理任务: 每天凌晨2点执行

    Returns:
        AsyncIOScheduler: 配置好的调度器实例

    需求引用:
        - 需求11.6: 每月1日自动重置所有用户的配额
        - 需求8.5: 清理旧登录记录任务
    """
    # 创建调度器
    scheduler = AsyncIOScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": True,  # 合并错过的任务
            "max_instances": 1,  # 每个任务最多同时运行1个实例
            "misfire_grace_time": 3600,  # 错过任务的宽限时间（秒）
        },
    )

    # 添加配额重置任务（每月1日凌晨0点）
    if settings.background_task.enable_scheduler:
        try:
            # 从配置读取cron表达式，默认为 "0 0 1 * *"（每月1日凌晨0点）
            cron_expr = settings.background_task.quota_reset_cron

            # 解析cron表达式
            # 格式: 分 时 日 月 星期
            parts = cron_expr.split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts

                scheduler.add_job(
                    reset_monthly_quotas,
                    trigger=CronTrigger(
                        minute=minute,
                        hour=hour,
                        day=day,
                        month=month,
                        day_of_week=day_of_week,
                        timezone="UTC",
                    ),
                    id="reset_monthly_quotas",
                    name="重置月度配额",
                    replace_existing=True,
                )
                logger.info(f"已添加配额重置任务: {cron_expr}")
            else:
                logger.warning(f"无效的cron表达式: {cron_expr}，使用默认配置")
                # 使用默认配置：每月1日凌晨0点
                scheduler.add_job(
                    reset_monthly_quotas,
                    trigger=CronTrigger(minute=0, hour=0, day=1, timezone="UTC"),
                    id="reset_monthly_quotas",
                    name="重置月度配额",
                    replace_existing=True,
                )
                logger.info("已添加配额重置任务: 每月1日凌晨0点")
        except Exception as e:
            logger.error(f"添加配额重置任务失败: {str(e)}")

        # 添加清理任务（每天凌晨2点）
        try:
            scheduler.add_job(
                run_all_cleanup_tasks,
                trigger=CronTrigger(minute=0, hour=2, timezone="UTC"),
                id="run_all_cleanup_tasks",
                name="运行所有清理任务",
                replace_existing=True,
            )
            logger.info("已添加清理任务: 每天凌晨2点")
        except Exception as e:
            logger.error(f"添加清理任务失败: {str(e)}")
    else:
        logger.info("定时任务调度器已禁用")

    return scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    应用生命周期管理

    启动时:
        - 初始化数据库表
        - 初始化Redis连接
        - 初始化向量数据库
        - 启动定时任务调度器
        - 记录启动日志

    关闭时:
        - 关闭定时任务调度器
        - 关闭Redis连接
        - 关闭数据库连接
        - 记录关闭日志

    需求引用:
        - 需求10.5: 应用启动和关闭事件管理

    Args:
        app: FastAPI应用实例

    Yields:
        None
    """
    global scheduler

    # 启动时执行
    logger.info("=" * 60)
    logger.info(f"启动 {settings.app.app_name} v{settings.app.app_version}")
    logger.info(f"环境: {settings.app.environment}")
    logger.info(f"调试模式: {settings.app.debug}")
    logger.info("=" * 60)

    config_ok = settings.validate_all()
    if not config_ok:
        if settings.app.environment in ("staging", "production"):
            raise RuntimeError("配置验证失败，应用启动中止")
        logger.warning("配置验证失败，部分功能可能不可用")

    # 初始化数据库表（如果需要）
    try:
        # 注意：在生产环境中应该使用Alembic进行数据库迁移
        # 这里仅用于开发环境快速启动
        if settings.app.debug:
            logger.info("检查数据库表...")
            # Base.metadata.create_all(bind=engine)
            logger.info("数据库表检查完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")

    # 初始化Redis连接
    try:
        from app.core.redis import ping_redis

        if ping_redis():
            logger.info("Redis连接成功")
        else:
            logger.warning("Redis连接失败，某些功能可能不可用")
    except Exception as e:
        logger.error(f"Redis初始化失败: {str(e)}")

    # 初始化Web Scraper调度器
    try:
        from app.core.redis import get_async_redis_client
        from app.core.scheduler import initialize_scheduler

        async_redis = get_async_redis_client()
        await initialize_scheduler(async_redis, max_concurrent_tasks=5)
        logger.info("Web Scraper调度器已启动")
    except Exception as e:
        logger.error(f"启动Web Scraper调度器失败: {str(e)}")

    # 初始化向量数据库
    try:
        from app.core.vector_store import get_vector_store_manager

        vector_manager = get_vector_store_manager()
        logger.info(f"向量数据库初始化成功: {vector_manager.persist_directory}")
    except Exception as e:
        logger.error(f"向量数据库初始化失败: {str(e)}")

    # 启动定时任务调度器
    if settings.background_task.enable_scheduler:
        try:
            scheduler = setup_scheduler()
            scheduler.start()
            logger.info("定时任务调度器已启动")

            # 打印已注册的任务
            jobs = scheduler.get_jobs()
            if jobs:
                logger.info(f"已注册 {len(jobs)} 个定时任务:")
                for job in jobs:
                    logger.info(f"  - {job.name} (ID: {job.id})")
                    logger.info(f"    下次执行: {job.next_run_time}")
            else:
                logger.warning("没有注册任何定时任务")
        except Exception as e:
            logger.error(f"启动定时任务调度器失败: {str(e)}")
            scheduler = None
    else:
        logger.info("定时任务调度器已禁用（通过配置）")

    logger.info("应用启动完成")
    logger.info("=" * 60)

    yield

    # 关闭时执行
    logger.info("=" * 60)
    logger.info("正在关闭应用...")

    # 关闭定时任务调度器
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("定时任务调度器已关闭")
        except Exception as e:
            logger.error(f"关闭定时任务调度器失败: {str(e)}")

    # 关闭Web Scraper调度器
    try:
        from app.core.scheduler import shutdown_scheduler

        await shutdown_scheduler()
        logger.info("Web Scraper调度器已关闭")
    except Exception as e:
        logger.error(f"关闭Web Scraper调度器失败: {str(e)}")

    # 关闭Redis连接
    try:
        from app.core.redis import close_redis, close_async_redis

        close_redis()
        await close_async_redis()
        logger.info("Redis连接已关闭")
    except Exception as e:
        logger.error(f"关闭Redis连接失败: {str(e)}")

    # 关闭数据库连接
    try:
        from app.core.database import close_db

        close_db()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {str(e)}")

    logger.info("应用已关闭")
    logger.info("=" * 60)


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def _require_admin_user(request: Request, db: Session) -> None:
    from app.core.security import verify_access_token
    from app.repositories.user_repository import UserRepository

    token = _extract_bearer_token(request)
    payload = verify_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌格式无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限"
        )


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app.app_name,
    version=settings.app.app_version,
    description="""
## AI智能助手系统后端API

基于FastAPI和LangChain 1.0框架构建的企业级AI智能助手系统，提供以下核心功能：

### 核心功能

* **智能对话** - 支持多轮对话、流式响应、对话历史管理
* **RAG知识库** - 文档上传、向量化、智能检索问答
* **Agent智能代理** - 工具调用、任务执行、推理过程可视化
* **用户管理** - 注册登录、JWT认证、配额管理
* **系统监控** - 使用统计、健康检查、Prometheus指标

### 技术栈

* **Web框架**: FastAPI 0.104+
* **AI框架**: LangChain 1.0
* **数据库**: MySQL 8.0, Redis 7.0, Chroma
* **LLM**: 通义千问 (Tongyi Qianwen)

### 认证方式

大部分API端点需要JWT认证。在请求头中添加：
```
Authorization: Bearer <access_token>
```

### 速率限制

* 登录接口: 5次/分钟
* 普通API: 100次/分钟
* LLM调用: 20次/分钟

### 错误响应格式

所有错误响应遵循统一格式：
```json
{
    "error_code": "1001",
    "message": "错误描述",
    "request_id": "uuid"
}
```
    """,
    summary="AI智能助手系统API",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "API Support",
        "url": "https://example.com/support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs" if settings.app.debug else None,
    redoc_url="/redoc" if settings.app.debug else None,
    openapi_tags=[
        {
            "name": "认证",
            "description": "用户注册、登录、令牌管理等认证相关操作",
        },
        {
            "name": "对话",
            "description": "对话会话管理、消息历史、对话导出等功能",
        },
        {
            "name": "聊天",
            "description": "实时聊天、流式响应、AI对话交互",
        },
        {
            "name": "配额",
            "description": "用户配额查询和管理",
        },
        {
            "name": "知识库",
            "description": "知识库创建、管理、文档上传等操作",
        },
        {
            "name": "文档",
            "description": "文档上传、处理状态查询、预览和删除",
        },
        {
            "name": "RAG",
            "description": "基于知识库的检索增强生成问答",
        },
        {
            "name": "Agent",
            "description": "智能代理工具管理和任务执行",
        },
        {
            "name": "系统",
            "description": "系统配置、使用统计、健康检查等管理功能",
        },
    ],
    lifespan=lifespan,
    responses={
        400: {
            "description": "请求参数错误",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "2001",
                        "message": "参数验证失败",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
        401: {
            "description": "未授权 - JWT令牌无效或已过期",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "1002",
                        "message": "令牌已过期",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
        403: {
            "description": "禁止访问 - 配额不足或权限不足",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "4001",
                        "message": "配额已用尽",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
        404: {
            "description": "资源不存在",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "2001",
                        "message": "对话不存在",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
        429: {
            "description": "请求过于频繁 - 超出速率限制",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Rate limit exceeded",
                        "message": "请求过于频繁，请稍后再试",
                    }
                }
            },
        },
        500: {
            "description": "服务器内部错误",
            "content": {
                "application/json": {
                    "example": {
                        "error_code": "3001",
                        "message": "数据库连接失败",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
    },
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.origins_list,
    allow_credentials=settings.cors.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求ID中间件
app.add_middleware(RequestIDMiddleware)

# 添加Prometheus监控中间件
app.add_middleware(PrometheusMiddleware)

# 添加错误处理器
register_exception_handlers(app)

# 配置速率限制
register_rate_limiter(app)


# 注册API路由
from app.api.v1 import api_router

app.include_router(api_router)


@app.get("/", tags=["根路径"])
async def root():
    """
    API根路径

    返回API基本信息和可用端点链接。

    Returns:
        dict: API基本信息
    """
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        "environment": settings.app.environment,
        "status": "running",
        "docs_url": "/docs" if settings.app.debug else None,
        "redoc_url": "/redoc" if settings.app.debug else None,
        "api_prefix": "/api/v1",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "scheduler_jobs": "/scheduler/jobs",
            "api_docs": "/docs",
            "api_redoc": "/redoc",
        },
    }


@app.get("/health", tags=["监控"])
async def health_check():
    """
    健康检查端点

    检查应用运行状态和各组件健康状况。

    Returns:
        dict: 健康状态信息，包括应用状态、调度器状态等

    Example:
        ```json
        {
            "status": "healthy",
            "app_name": "AI智能助手系统",
            "version": "1.0.0",
            "environment": "development",
            "scheduler": "running",
            "scheduled_jobs": 2
        }
        ```
    """
    if settings.app.environment == "production":
        return {"status": "healthy"}

    health_status = {
        "status": "healthy",
        "app_name": settings.app.app_name,
        "version": settings.app.app_version,
        "environment": settings.app.environment,
    }

    # 检查调度器状态
    if settings.background_task.enable_scheduler:
        if scheduler and scheduler.running:
            health_status["scheduler"] = "running"
            health_status["scheduled_jobs"] = len(scheduler.get_jobs())
        else:
            health_status["scheduler"] = "stopped"
            health_status["scheduled_jobs"] = 0
    else:
        health_status["scheduler"] = "disabled"

    return health_status


@app.get("/scheduler/jobs", tags=["监控"])
async def list_scheduled_jobs(request: Request, db: Session = Depends(get_db)):
    """
    列出所有定时任务

    显示系统中配置的所有定时任务及其执行状态。

    Returns:
        dict: 定时任务列表，包括任务ID、名称、下次执行时间等

    Example:
        ```json
        {
            "enabled": true,
            "running": true,
            "job_count": 2,
            "jobs": [
                {
                    "id": "reset_monthly_quotas",
                    "name": "重置月度配额",
                    "next_run_time": "2025-02-01T00:00:00",
                    "trigger": "cron[month='*', day='1', hour='0', minute='0']"
                }
            ]
        }
        ```
    """
    if settings.app.environment in ("staging", "production"):
        _require_admin_user(request, db)

    if not settings.background_task.enable_scheduler:
        return {"enabled": False, "message": "定时任务调度器已禁用"}

    if not scheduler or not scheduler.running:
        return {"enabled": True, "running": False, "message": "定时任务调度器未运行"}

    jobs = scheduler.get_jobs()
    job_list = []

    for job in jobs:
        job_info = {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat()
            if job.next_run_time
            else None,
            "trigger": str(job.trigger),
        }
        job_list.append(job_info)

    return {
        "enabled": True,
        "running": True,
        "job_count": len(job_list),
        "jobs": job_list,
    }


@app.get("/metrics", tags=["监控"])
async def metrics(request: Request, db: Session = Depends(get_db)):
    """
    Prometheus监控指标端点

    返回Prometheus格式的监控指标，用于系统监控和告警。

    **可用指标:**

    * `http_requests_total` - HTTP请求总数（按方法、路径、状态码分组）
    * `http_request_duration_seconds` - HTTP请求时长分布
    * `http_requests_active` - 当前活跃的HTTP请求数
    * `llm_calls_total` - LLM调用总数（按模型分组）
    * `llm_tokens_total` - LLM token使用总量（按类型分组）
    * `db_connections_active` - 数据库活跃连接数
    * `redis_connection_status` - Redis连接状态

    需求引用:
        - 需求8.1: 提供监控指标接口

    Returns:
        Response: Prometheus格式的指标数据（text/plain格式）

    Example:
        ```
        # HELP http_requests_total Total HTTP requests
        # TYPE http_requests_total counter
        http_requests_total{method="GET",path="/api/v1/conversations",status="200"} 1523.0

        # HELP http_request_duration_seconds HTTP request duration
        # TYPE http_request_duration_seconds histogram
        http_request_duration_seconds_bucket{le="0.1"} 1234.0
        ```
    """
    if not settings.monitoring.enable_metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if settings.app.environment in ("staging", "production"):
        _require_admin_user(request, db)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level=settings.logging.log_level.lower(),
    )
