"""
OpenClaw 工具种子数据脚本

注册知识库查询工具到系统，供 OpenClaw Agent 调用。

使用方法:
    python scripts/seed_openclaw_tools.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.openclaw_tool import OpenClawTool, ToolStatus
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_knowledge_base_query_tool(db: Session) -> None:
    """
    注册知识库查询工具

    这是 OpenClaw Agent 调用的核心工具，用于查询 RAG 知识库。
    """
    tool_name = "query_knowledge_base"

    # 检查工具是否已存在
    existing_tool = db.query(OpenClawTool).filter(
        OpenClawTool.name == tool_name
    ).first()

    if existing_tool:
        logger.info(f"工具 '{tool_name}' 已存在，跳过创建")
        logger.info(f"  - ID: {existing_tool.id}")
        logger.info(f"  - 状态: {existing_tool.status}")
        logger.info(f"  - 端点: {existing_tool.endpoint_url}")
        return

    # 构建端点 URL
    # 在生产环境中，这应该是公网可访问的 URL
    # 在开发环境中，使用 localhost
    base_url = getattr(settings, 'api_base_url', 'http://localhost:8000')
    endpoint_url = f"{base_url}/api/v1/tools/query-kb"

    # 创建工具配置
    tool = OpenClawTool(
        name=tool_name,
        display_name="知识库查询",
        description=(
            "查询 RAG 知识库中的相关文档。"
            "根据用户的问题，从指定的知识库中检索最相关的文档片段。"
            "支持多知识库联合检索、相似度阈值设置和结果数量控制。"
        ),
        endpoint_url=endpoint_url,
        method="POST",
        auth_type="api_token",
        auth_config={
            "header_name": "X-API-Token",
            "description": "在请求头中提供 API Token 进行身份验证"
        },
        parameters_schema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询内容",
                    "minLength": 1,
                    "maxLength": 1000
                },
                "knowledge_base_ids": {
                    "type": "array",
                    "description": "知识库ID列表，为空则查询所有知识库",
                    "items": {"type": "integer"},
                    "default": None
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5
                },
                "similarity_threshold": {
                    "type": "number",
                    "description": "相似度阈值（0.0-1.0）",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.7
                }
            }
        },
        response_schema={
            "type": "object",
            "properties": {
                "success": {
                    "type": "boolean",
                    "description": "是否成功"
                },
                "query": {
                    "type": "string",
                    "description": "查询内容"
                },
                "results": {
                    "type": "array",
                    "description": "检索结果",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "similarity_score": {"type": "number"},
                            "document_id": {"type": "integer"},
                            "document_name": {"type": "string"},
                            "knowledge_base_id": {"type": "integer"},
                            "knowledge_base_name": {"type": "string"}
                        }
                    }
                },
                "total_results": {
                    "type": "integer",
                    "description": "结果总数"
                }
            }
        },
        status=ToolStatus.ACTIVE,
        is_builtin=True,
        created_by=None  # 系统内置工具
    )

    db.add(tool)
    db.commit()
    db.refresh(tool)

    logger.info(f"✅ 成功注册工具: {tool_name}")
    logger.info(f"  - ID: {tool.id}")
    logger.info(f"  - 显示名称: {tool.display_name}")
    logger.info(f"  - 端点: {tool.endpoint_url}")
    logger.info(f"  - 认证类型: {tool.auth_type}")
    logger.info(f"  - 状态: {tool.status}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("OpenClaw 工具种子数据初始化")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # 注册知识库查询工具
        seed_knowledge_base_query_tool(db)

        logger.info("=" * 60)
        logger.info("✅ 工具种子数据初始化完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 初始化失败: {str(e)}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
