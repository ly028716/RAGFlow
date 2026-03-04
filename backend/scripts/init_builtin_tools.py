"""
初始化内置工具

创建系统内置的 OpenClaw 工具记录
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.openclaw_tool_service import OpenClawToolService
from app.config import settings


def init_builtin_tools():
    """初始化内置工具"""
    db: Session = SessionLocal()

    try:
        tool_service = OpenClawToolService(db)

        # 1. 知识库查询工具
        kb_tool_name = "query_knowledge_base"
        existing_tool = tool_service.get_tool_by_name(kb_tool_name)

        if existing_tool:
            print(f"✓ 工具 '{kb_tool_name}' 已存在 (ID: {existing_tool.id})")
        else:
            tool = tool_service.register_tool(
                name=kb_tool_name,
                display_name="知识库查询",
                description="查询指定知识库中的相关文档，支持语义检索和相似度匹配",
                endpoint_url="http://localhost:8000/api/v1/tools/query-kb",
                method="POST",
                auth_type="api_token",
                auth_config={
                    "header_name": "X-API-Token",
                    "description": "需要在请求头中提供有效的 API Token",
                },
                parameters_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "查询内容",
                            "minLength": 1,
                            "maxLength": 1000,
                        },
                        "knowledge_base_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "知识库ID列表，为空则查询所有",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回结果数量",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "相似度阈值",
                            "default": 0.7,
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                    },
                },
                response_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "query": {"type": "string"},
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "similarity_score": {"type": "number"},
                                    "document_id": {"type": "integer"},
                                    "document_name": {"type": "string"},
                                    "knowledge_base_id": {"type": "integer"},
                                    "knowledge_base_name": {"type": "string"},
                                },
                            },
                        },
                        "total_results": {"type": "integer"},
                    },
                },
                is_builtin=True,
            )
            print(f"✓ 工具 '{kb_tool_name}' 创建成功 (ID: {tool.id})")

        print("\n内置工具初始化完成！")
        print(f"\n配置提示：")
        print(f"1. 确保在 backend/.env 中配置了 OPENCLAW_API_TOKENS")
        print(f"2. 在 OpenClaw Gateway 中注册此工具：")
        print(f"   - 工具名称: {kb_tool_name}")
        print(f"   - 端点URL: http://host.docker.internal:8000/api/v1/tools/query-kb")
        print(f"   - 认证方式: API Token (Header: X-API-Token)")

    except Exception as e:
        print(f"✗ 初始化失败: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("开始初始化内置工具...")
    init_builtin_tools()
