"""
OpenClaw 工具 Repository

处理 OpenClaw 工具配置的数据访问操作
"""

from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.openclaw_tool import OpenClawTool, ToolStatus


class OpenClawToolRepository:
    """OpenClaw 工具配置数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, tool_data: dict) -> OpenClawTool:
        """创建工具配置"""
        tool = OpenClawTool(**tool_data)
        self.db.add(tool)
        self.db.commit()
        self.db.refresh(tool)
        return tool

    def get_by_id(self, tool_id: int) -> Optional[OpenClawTool]:
        """根据ID获取工具"""
        return self.db.query(OpenClawTool).filter(OpenClawTool.id == tool_id).first()

    def get_by_name(self, name: str) -> Optional[OpenClawTool]:
        """根据名称获取工具"""
        return self.db.query(OpenClawTool).filter(OpenClawTool.name == name).first()

    def get_all(
        self,
        status: Optional[ToolStatus] = None,
        is_builtin: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenClawTool]:
        """获取工具列表"""
        query = self.db.query(OpenClawTool)

        if status:
            query = query.filter(OpenClawTool.status == status)
        if is_builtin is not None:
            query = query.filter(OpenClawTool.is_builtin == is_builtin)

        return query.offset(skip).limit(limit).all()

    def get_active_tools(self) -> List[OpenClawTool]:
        """获取所有激活的工具"""
        return (
            self.db.query(OpenClawTool)
            .filter(OpenClawTool.status == ToolStatus.ACTIVE)
            .all()
        )

    def update(self, tool_id: int, update_data: dict) -> Optional[OpenClawTool]:
        """更新工具配置"""
        # 定义允许更新的字段白名单
        ALLOWED_UPDATE_FIELDS = {
            'display_name', 'description', 'endpoint_url',
            'method', 'auth_type', 'auth_config',
            'parameters_schema', 'response_schema', 'status'
        }

        tool = self.get_by_id(tool_id)
        if not tool:
            return None

        for key, value in update_data.items():
            if key in ALLOWED_UPDATE_FIELDS and hasattr(tool, key):
                setattr(tool, key, value)

        self.db.commit()
        self.db.refresh(tool)
        return tool

    def delete(self, tool_id: int) -> bool:
        """删除工具（软删除）"""
        tool = self.get_by_id(tool_id)
        if not tool:
            return False

        tool.status = ToolStatus.DELETED
        self.db.commit()
        return True

    def hard_delete(self, tool_id: int) -> bool:
        """硬删除工具"""
        tool = self.get_by_id(tool_id)
        if not tool:
            return False

        self.db.delete(tool)
        self.db.commit()
        return True

    def count(self, status: Optional[ToolStatus] = None) -> int:
        """统计工具数量"""
        query = self.db.query(OpenClawTool)
        if status:
            query = query.filter(OpenClawTool.status == status)
        return query.count()
