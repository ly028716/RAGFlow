"""
Pytest配置文件

提供测试所需的fixtures和配置。
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.core.security import hash_password, create_access_token


# 使用内存SQLite数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    创建测试数据库会话
    
    每个测试函数都会获得一个新的数据库会话，
    测试结束后会回滚所有更改。
    """
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # 清理所有表
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    创建测试客户端
    
    使用测试数据库会话覆盖应用的数据库依赖。
    """
    app.dependency_overrides[get_db] = lambda: db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db: Session) -> User:
    """
    创建测试用户
    
    Returns:
        User: 测试用户对象
    """
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User) -> dict:
    """
    创建认证头
    
    Args:
        test_user: 测试用户
        
    Returns:
        dict: 包含Authorization头的字典
    """
    token = create_access_token(subject=test_user.id, username=test_user.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def other_user(db: Session) -> User:
    """
    创建另一个测试用户
    
    Returns:
        User: 另一个测试用户对象
    """
    user = User(
        username="otheruser",
        email="other@example.com",
        password_hash=hash_password("otherpassword123"),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def other_auth_headers(other_user: User) -> dict:
    """
    创建另一个用户的认证头

    Args:
        other_user: 另一个测试用户

    Returns:
        dict: 包含Authorization头的字典
    """
    token = create_access_token(subject=other_user.id, username=other_user.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_kb(db: Session, test_user: User) -> KnowledgeBase:
    """
    创建测试知识库

    Args:
        db: 数据库会话
        test_user: 测试用户

    Returns:
        KnowledgeBase: 测试知识库对象
    """
    kb = KnowledgeBase(
        name="测试知识库",
        description="用于测试的知识库",
        user_id=test_user.id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@pytest.fixture(scope="function", autouse=True)
def mock_openclaw_api_tokens(monkeypatch):
    """
    为测试环境配置 OpenClaw API Tokens

    自动应用于所有测试,使得 "test-token" 成为有效的 API Token
    """
    from app.config import settings

    # 设置测试用的 API Token
    monkeypatch.setattr(settings.openclaw, "api_tokens", "test-token,another-test-token")

    return settings.openclaw
