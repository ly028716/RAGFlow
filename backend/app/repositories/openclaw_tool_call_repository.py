"""
OpenClaw 工具调用记录 Repository

处理 OpenClaw 工具调用记录的数据访问操作
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.models.openclaw_tool_call import CallStatus, OpenClawToolCall


class OpenClawToolCallRepository:
    """OpenClaw 工具调用记录数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, call_data: dict) -> OpenClawToolCall:
        """创建调用记录"""
        call = OpenClawToolCall(**call_data)
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return call

    def get_by_id(self, call_id: int) -> Optional[OpenClawToolCall]:
        """根据ID获取调用记录"""
        return (
            self.db.query(OpenClawToolCall)
            .filter(OpenClawToolCall.id == call_id)
            .first()
        )

    def get_by_tool_id(
        self,
        tool_id: int,
        status: Optional[CallStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenClawToolCall]:
        """获取指定工具的调用记录"""
        query = self.db.query(OpenClawToolCall).filter(
            OpenClawToolCall.tool_id == tool_id
        )

        if status:
            query = query.filter(OpenClawToolCall.status == status)

        return query.order_by(desc(OpenClawToolCall.created_at)).offset(skip).limit(limit).all()

    def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenClawToolCall]:
        """获取指定用户的调用记录"""
        return (
            self.db.query(OpenClawToolCall)
            .filter(OpenClawToolCall.user_id == user_id)
            .order_by(desc(OpenClawToolCall.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_agent_id(
        self,
        agent_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenClawToolCall]:
        """获取指定Agent的调用记录"""
        return (
            self.db.query(OpenClawToolCall)
            .filter(OpenClawToolCall.agent_id == agent_id)
            .order_by(desc(OpenClawToolCall.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_recent_calls(
        self,
        hours: int = 24,
        skip: int = 0,
        limit: int = 100,
    ) -> List[OpenClawToolCall]:
        """获取最近的调用记录"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db.query(OpenClawToolCall)
            .filter(OpenClawToolCall.created_at >= since)
            .order_by(desc(OpenClawToolCall.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_tool(self, tool_id: int, status: Optional[CallStatus] = None) -> int:
        """统计工具调用次数"""
        query = self.db.query(OpenClawToolCall).filter(
            OpenClawToolCall.tool_id == tool_id
        )
        if status:
            query = query.filter(OpenClawToolCall.status == status)
        return query.count()

    def get_tool_stats(self, tool_id: int) -> dict:
        """获取工具调用统计"""
        total = self.count_by_tool(tool_id)
        success = self.count_by_tool(tool_id, CallStatus.SUCCESS)
        failed = self.count_by_tool(tool_id, CallStatus.FAILED)
        timeout = self.count_by_tool(tool_id, CallStatus.TIMEOUT)

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "timeout": timeout,
            "success_rate": (success / total * 100) if total > 0 else 0,
        }
