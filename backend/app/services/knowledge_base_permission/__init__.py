"""
知识库权限服务包

提供知识库权限管理的所有服务。

导出:
    - KnowledgeBasePermissionService: 权限服务 Facade
    - PermissionCheckService: 权限检查服务
    - PermissionManagementService: 权限管理服务
    - SharingService: 分享服务
    - PERMISSION_LEVELS: 权限等级常量

使用示例:
    from app.services.knowledge_base_permission import KnowledgeBasePermissionService

    service = KnowledgeBasePermissionService(db)
    has_permission, kb = service.check_permission(kb_id, user_id)
"""

from app.services.knowledge_base_permission.constants import PERMISSION_LEVELS
from app.services.knowledge_base_permission.knowledge_base_permission_service import \
    KnowledgeBasePermissionService
from app.services.knowledge_base_permission.permission_check_service import \
    PermissionCheckService
from app.services.knowledge_base_permission.permission_management_service import \
    PermissionManagementService
from app.services.knowledge_base_permission.sharing_service import SharingService

__all__ = [
    # Facade
    "KnowledgeBasePermissionService",
    # Sub-services
    "PermissionCheckService",
    "PermissionManagementService",
    "SharingService",
    # Constants
    "PERMISSION_LEVELS",
]
