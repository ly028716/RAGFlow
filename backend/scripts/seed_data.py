#!/usr/bin/env python3
"""
种子数据脚本
用于创建测试用户、示例数据和内置工具
"""
import sys
import os
from pathlib import Path
from datetime import datetime, date

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.core.security import hash_password
from app.models.user import User
from app.models.user_quota import UserQuota
from app.models.agent_tool import AgentTool
from app.models.knowledge_base import KnowledgeBase
from app.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_users(session):
    """创建测试用户"""
    logger.info("Creating test users...")
    
    users_data = [
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "Admin123456",
            "is_active": True
        },
        {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Test123456",
            "is_active": True
        }
    ]
    
    created_users = []
    for user_data in users_data:
        # Check if user already exists
        existing_user = session.query(User).filter(User.username == user_data["username"]).first()
        if existing_user:
            logger.info(f"User '{user_data['username']}' already exists, skipping...")
            created_users.append(existing_user)
            continue
        
        # Create user
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            is_active=user_data["is_active"],
            created_at=datetime.utcnow()
        )
        session.add(user)
        session.flush()  # Get user ID
        
        # Create user quota
        quota = UserQuota(
            user_id=user.id,
            monthly_quota=settings.quota.default_monthly_quota,
            used_quota=0,
            reset_date=date.today().replace(day=1),
            created_at=datetime.utcnow()
        )
        session.add(quota)
        
        created_users.append(user)
        logger.info(f"✓ Created user: {user.username} (password: {user_data['password']})")
    
    session.commit()
    return created_users


def create_builtin_tools(session) -> None:
    """创建内置工具"""
    logger.info("Creating built-in tools...")
    
    tools_data = [
        {
            "name": "calculator",
            "description": "执行数学计算，支持基本算术运算和数学函数",
            "tool_type": "builtin",
            "config": {
                "type": "calculator",
                "operations": ["add", "subtract", "multiply", "divide", "power", "sqrt"]
            },
            "is_enabled": True
        },
        {
            "name": "data_analysis",
            "description": "对数据进行分析和处理，支持统计计算、数据可视化、趋势分析等",
            "tool_type": "builtin",
            "config": {
                "type": "data_analysis",
                "supported_formats": ["csv", "json", "excel"],
                "max_rows": 10000
            },
            "is_enabled": True
        },
    ]
    
    for tool_data in tools_data:
        # Check if tool already exists
        existing_tool = session.query(AgentTool).filter(AgentTool.name == tool_data["name"]).first()
        if existing_tool:
            logger.info(f"Tool '{tool_data['name']}' already exists, skipping...")
            continue
        
        # Create tool
        tool = AgentTool(
            name=tool_data["name"],
            description=tool_data["description"],
            tool_type=tool_data["tool_type"],
            config=tool_data["config"],
            is_enabled=tool_data["is_enabled"],
            created_at=datetime.utcnow()
        )
        session.add(tool)
        logger.info(f"✓ Created tool: {tool.name}")
    
    session.commit()


def create_sample_knowledge_base(session, user):
    """创建示例知识库"""
    logger.info("Creating sample knowledge base...")
    
    # Check if knowledge base already exists
    existing_kb = session.query(KnowledgeBase).filter(
        KnowledgeBase.user_id == user.id,
        KnowledgeBase.name == "示例知识库"
    ).first()
    
    if existing_kb:
        logger.info("Sample knowledge base already exists, skipping...")
        return existing_kb
    
    # Create knowledge base
    kb = KnowledgeBase(
        user_id=user.id,
        name="示例知识库",
        description="这是一个示例知识库，用于演示RAG功能",
        category="示例",
        created_at=datetime.utcnow()
    )
    session.add(kb)
    session.commit()
    
    logger.info(f"✓ Created knowledge base: {kb.name}")
    return kb


def seed_database():
    """执行数据库种子数据填充"""
    try:
        logger.info("=" * 60)
        logger.info("Database Seeding Script")
        logger.info("=" * 60)
        
        # Create session
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Create test users
            users = create_test_users(session)
            
            # Create built-in tools
            create_builtin_tools(session)
            
            # Create sample knowledge base for first user
            if users:
                create_sample_knowledge_base(session, users[0])
            
            logger.info("=" * 60)
            logger.info("Database seeding completed successfully!")
            logger.info("=" * 60)
            logger.info("\nTest Users Created:")
            logger.info("  Username: admin, Password: Admin123456")
            logger.info("  Username: testuser, Password: Test123456")
            logger.info("\nBuilt-in Tools Created:")
            logger.info("  - calculator: 数学计算工具")
            logger.info("  - data_analysis: 数据分析工具")
            logger.info("=" * 60)
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise


if __name__ == "__main__":
    try:
        seed_database()
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        sys.exit(1)
