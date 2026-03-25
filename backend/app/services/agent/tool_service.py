"""
Agent 工具服务模块

实现 Agent 工具的 CRUD 管理功能。
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent_tool import AgentTool, ToolType
from app.repositories.agent_repository import AgentToolRepository

logger = logging.getLogger(__name__)


class ToolService:
    """
    Agent 工具服务类

    提供工具的 CRUD 操作。

    使用方式:
        service = ToolService(db)
        tools = service.get_list(user_id=1)
        tool = service.create(user_id=1, name="工具", description="描述")
    """

    def __init__(self, db: Session):
        """
        初始化工具服务

        Args:
            db: SQLAlchemy数据库会话
        """
        self.db = db
        self.tool_repo = AgentToolRepository(db)

    def get_list(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        tool_type: Optional[ToolType] = None,
        is_enabled: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取可用工具列表

        Args:
            user_id: 用户ID（用于权限验证）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            tool_type: 工具类型过滤（builtin/custom）
            is_enabled: 启用状态过滤

        Returns:
            工具信息列表
        """
        # 从数据库获取工具
        tools = self.tool_repo.get_all(
            skip=skip, limit=limit, tool_type=tool_type, is_enabled=is_enabled
        )

        # 转换为字典格式
        tools_list = []
        for tool in tools:
            tools_list.append(
                {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type.value,
                    "config": tool.config,
                    "is_enabled": tool.is_enabled,
                    "created_at": tool.created_at.isoformat(),
                }
            )

        return tools_list

    def get_list_with_total(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        tool_type: Optional[ToolType] = None,
        is_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """获取工具列表和总数"""
        tools = self.tool_repo.get_all(
            skip=skip, limit=limit, tool_type=tool_type, is_enabled=is_enabled
        )
        total = self.tool_repo.count(tool_type=tool_type, is_enabled=is_enabled)

        tools_list: List[Dict[str, Any]] = []
        for tool in tools:
            tools_list.append(
                {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type.value,
                    "config": tool.config,
                    "is_enabled": tool.is_enabled,
                    "created_at": tool.created_at.isoformat(),
                }
            )

        return {"total": total, "items": tools_list}

    def get_by_id(self, tool_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取单个工具信息

        Args:
            tool_id: 工具ID
            user_id: 用户ID（用于权限验证）

        Returns:
            工具信息字典，不存在则返回None
        """
        tool = self.tool_repo.get_by_id(tool_id)
        if not tool:
            return None

        return {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "tool_type": tool.tool_type.value,
            "config": tool.config,
            "is_enabled": tool.is_enabled,
            "created_at": tool.created_at.isoformat(),
        }

    def create(
        self,
        user_id: int,
        name: str,
        description: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建自定义工具

        Args:
            user_id: 用户ID
            name: 工具名称
            description: 工具描述
            config: 工具配置参数

        Returns:
            创建的工具信息字典

        Raises:
            ValueError: 工具名称已存在时抛出
        """
        # 检查工具名称是否已存在
        if self.tool_repo.name_exists(name):
            raise ValueError(f"工具名称 '{name}' 已存在")

        # 创建工具
        tool = self.tool_repo.create(
            name=name,
            description=description,
            tool_type=ToolType.CUSTOM,
            config=config,
            is_enabled=True,
        )

        logger.info(f"用户 {user_id} 创建了自定义工具: {name}")

        return {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "tool_type": tool.tool_type.value,
            "config": tool.config,
            "is_enabled": tool.is_enabled,
            "created_at": tool.created_at.isoformat(),
        }

    def update(
        self,
        tool_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_enabled: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        更新工具配置

        Args:
            tool_id: 工具ID
            user_id: 用户ID
            name: 新工具名称
            description: 新描述
            config: 新配置参数
            is_enabled: 是否启用

        Returns:
            更新后的工具信息字典，工具不存在则返回None

        Raises:
            ValueError: 工具名称已被其他工具使用时抛出
        """
        # 检查工具是否存在
        tool = self.tool_repo.get_by_id(tool_id)
        if not tool:
            return None

        # 如果更新名称，检查新名称是否已存在
        if name and name != tool.name:
            if self.tool_repo.name_exists(name, exclude_tool_id=tool_id):
                raise ValueError(f"工具名称 '{name}' 已存在")

        # 更新工具
        updated_tool = self.tool_repo.update(
            tool_id=tool_id,
            name=name,
            description=description,
            config=config,
            is_enabled=is_enabled,
        )

        if updated_tool:
            logger.info(f"用户 {user_id} 更新了工具 {tool_id}")
            return {
                "id": updated_tool.id,
                "name": updated_tool.name,
                "description": updated_tool.description,
                "tool_type": updated_tool.tool_type.value,
                "config": updated_tool.config,
                "is_enabled": updated_tool.is_enabled,
                "created_at": updated_tool.created_at.isoformat(),
            }

        return None

    def delete(self, tool_id: int, user_id: int) -> bool:
        """
        删除工具

        Args:
            tool_id: 工具ID
            user_id: 用户ID

        Returns:
            删除成功返回True，工具不存在返回False
        """
        # 检查工具是否存在
        tool = self.tool_repo.get_by_id(tool_id)
        if not tool:
            return False

        # 只允许删除自定义工具
        if tool.tool_type == ToolType.BUILTIN:
            raise ValueError("不能删除内置工具")

        # 删除工具
        success = self.tool_repo.delete(tool_id)

        if success:
            logger.info(f"用户 {user_id} 删除了工具 {tool_id}")

        return success


__all__ = [
    "ToolService",
]
