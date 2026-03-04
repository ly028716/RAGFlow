"""
OpenClaw 工具服务

处理 OpenClaw 工具注册、查询和调用记录的业务逻辑
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.openclaw_tool import OpenClawTool, ToolStatus
from app.models.openclaw_tool_call import CallStatus, OpenClawToolCall
from app.repositories.openclaw_tool_call_repository import (
    OpenClawToolCallRepository,
)
from app.repositories.openclaw_tool_repository import OpenClawToolRepository

logger = logging.getLogger(__name__)


class OpenClawToolService:
    """OpenClaw 工具服务层"""

    def __init__(self, db: Session):
        self.db = db
        self.tool_repo = OpenClawToolRepository(db)
        self.call_repo = OpenClawToolCallRepository(db)

    # ========================================================================
    # 工具管理
    # ========================================================================

    def register_tool(
        self,
        name: str,
        display_name: str,
        description: str,
        endpoint_url: str,
        method: str = "POST",
        auth_type: str = "api_token",
        auth_config: Optional[Dict] = None,
        parameters_schema: Optional[Dict] = None,
        response_schema: Optional[Dict] = None,
        is_builtin: bool = False,
        created_by: Optional[int] = None,
    ) -> OpenClawTool:
        """
        注册新工具

        Args:
            name: 工具名称（唯一标识）
            display_name: 显示名称
            description: 工具描述
            endpoint_url: 端点URL
            method: HTTP方法
            auth_type: 认证类型
            auth_config: 认证配置
            parameters_schema: 参数Schema
            response_schema: 响应Schema
            is_builtin: 是否为内置工具
            created_by: 创建者用户ID

        Returns:
            创建的工具对象

        Raises:
            ValueError: 工具名称已存在
        """
        # 检查工具名称是否已存在
        existing_tool = self.tool_repo.get_by_name(name)
        if existing_tool:
            raise ValueError(f"工具名称 '{name}' 已存在")

        tool_data = {
            "name": name,
            "display_name": display_name,
            "description": description,
            "endpoint_url": endpoint_url,
            "method": method.upper(),
            "auth_type": auth_type,
            "auth_config": auth_config or {},
            "parameters_schema": parameters_schema,
            "response_schema": response_schema,
            "status": ToolStatus.ACTIVE,
            "is_builtin": is_builtin,
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        tool = self.tool_repo.create(tool_data)
        logger.info(f"工具注册成功: {name} (ID: {tool.id})")
        return tool

    def get_tool(self, tool_id: int) -> Optional[OpenClawTool]:
        """获取工具详情"""
        return self.tool_repo.get_by_id(tool_id)

    def get_tool_by_name(self, name: str) -> Optional[OpenClawTool]:
        """根据名称获取工具"""
        return self.tool_repo.get_by_name(name)

    def list_tools(
        self,
        status: Optional[ToolStatus] = None,
        is_builtin: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenClawTool]:
        """获取工具列表"""
        return self.tool_repo.get_all(
            status=status, is_builtin=is_builtin, skip=skip, limit=limit
        )

    def get_active_tools(self) -> List[OpenClawTool]:
        """获取所有激活的工具"""
        return self.tool_repo.get_active_tools()

    def update_tool(
        self, tool_id: int, update_data: Dict
    ) -> Optional[OpenClawTool]:
        """
        更新工具配置

        Args:
            tool_id: 工具ID
            update_data: 更新数据

        Returns:
            更新后的工具对象
        """
        # 添加更新时间
        update_data["updated_at"] = datetime.utcnow()

        tool = self.tool_repo.update(tool_id, update_data)
        if tool:
            logger.info(f"工具更新成功: {tool.name} (ID: {tool_id})")
        return tool

    def delete_tool(self, tool_id: int) -> bool:
        """删除工具（软删除）"""
        success = self.tool_repo.delete(tool_id)
        if success:
            logger.info(f"工具删除成功: ID {tool_id}")
        return success

    def activate_tool(self, tool_id: int) -> Optional[OpenClawTool]:
        """激活工具"""
        return self.update_tool(tool_id, {"status": ToolStatus.ACTIVE})

    def deactivate_tool(self, tool_id: int) -> Optional[OpenClawTool]:
        """停用工具"""
        return self.update_tool(tool_id, {"status": ToolStatus.INACTIVE})

    # ========================================================================
    # 工具调用记录
    # ========================================================================

    def record_tool_call(
        self,
        tool_id: int,
        agent_id: Optional[str] = None,
        user_id: Optional[int] = None,
        request_params: Optional[Dict] = None,
        response_data: Optional[Dict] = None,
        status: CallStatus = CallStatus.SUCCESS,
        error_message: Optional[str] = None,
        execution_time: Optional[float] = None,
    ) -> OpenClawToolCall:
        """
        记录工具调用

        Args:
            tool_id: 工具ID
            agent_id: Agent ID
            user_id: 用户ID
            request_params: 请求参数
            response_data: 响应数据
            status: 调用状态
            error_message: 错误信息
            execution_time: 执行时间（秒）

        Returns:
            调用记录对象
        """
        # 过滤敏感参数
        SENSITIVE_KEYS = {'password', 'token', 'api_key', 'secret', 'credential'}
        safe_params = None
        if request_params:
            safe_params = {
                k: v for k, v in request_params.items()
                if k.lower() not in SENSITIVE_KEYS
            }

        call_data = {
            "tool_id": tool_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "request_params": safe_params,
            "response_data": response_data,
            "status": status,
            "error_message": error_message,
            "execution_time": execution_time,
            "created_at": datetime.utcnow(),
        }

        call = self.call_repo.create(call_data)
        logger.debug(
            f"工具调用记录: tool_id={tool_id}, status={status}, "
            f"execution_time={execution_time}s"
        )
        return call

    def get_tool_calls(
        self,
        tool_id: Optional[int] = None,
        user_id: Optional[int] = None,
        agent_id: Optional[str] = None,
        status: Optional[CallStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenClawToolCall]:
        """获取工具调用记录"""
        if tool_id:
            return self.call_repo.get_by_tool_id(tool_id, status, skip, limit)
        elif user_id:
            return self.call_repo.get_by_user_id(user_id, skip, limit)
        elif agent_id:
            return self.call_repo.get_by_agent_id(agent_id, skip, limit)
        else:
            return self.call_repo.get_recent_calls(hours=24, skip=skip, limit=limit)

    def get_tool_stats(self, tool_id: int) -> Dict:
        """获取工具调用统计"""
        return self.call_repo.get_tool_stats(tool_id)
