"""
API v1 路由模块

导出所有v1版本的API路由。
"""

from fastapi import APIRouter

from app.api.v1.agent import router as agent_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.documents import router as documents_router
from app.api.v1.kb_permissions import router as kb_permissions_router
from app.api.v1.knowledge_bases import router as knowledge_bases_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.quota import router as quota_router
from app.api.v1.rag import router as rag_router
from app.api.v1.system import router as system_router
from app.api.v1.user import router as user_router
from app.api.v1.verification import router as verification_router

# 创建v1 API路由器
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(auth_router)
api_router.include_router(conversations_router)
api_router.include_router(chat_router)
api_router.include_router(quota_router)
api_router.include_router(knowledge_bases_router)
api_router.include_router(documents_router)
api_router.include_router(rag_router)
api_router.include_router(agent_router)
api_router.include_router(system_router)
api_router.include_router(verification_router)
api_router.include_router(prompts_router)
api_router.include_router(user_router)
api_router.include_router(kb_permissions_router)


# 导出
__all__ = [
    "api_router",
    "auth_router",
    "conversations_router",
    "chat_router",
    "quota_router",
    "knowledge_bases_router",
    "documents_router",
    "rag_router",
    "agent_router",
    "system_router",
    "verification_router",
    "prompts_router",
    "user_router",
    "kb_permissions_router",
]
