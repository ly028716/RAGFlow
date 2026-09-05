"""
认证相关的Pydantic模型

定义用户注册、登录、令牌响应等API请求和响应的数据模型。
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserRegister(BaseModel):
    """
    用户注册请求模型

    需求引用:
        - 需求1.1: 用户名唯一且密码强度符合要求（至少8位，包含字母和数字）
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="用户名（3-50个字符）",
        examples=["testuser", "john_doe", "alice2024"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="密码（至少8位，包含字母和数字）",
        examples=["Password123", "SecurePass456"],
    )
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "testuser",
                    "password": "Password123",
                }
            ]
        }
    }

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度：至少8位，包含字母和数字"""
        if len(v) < 8:
            raise ValueError("密码长度至少8位")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("密码必须包含字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含数字")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式"""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v


class UserLogin(BaseModel):
    """用户登录请求模型"""

    username: str = Field(..., description="用户名", examples=["testuser"])
    password: str = Field(..., description="密码", examples=["Password123"])

    model_config = {
        "json_schema_extra": {
            "examples": [{"username": "testuser", "password": "Password123"}]
        }
    }


class TokenResponse(BaseModel):
    """
    令牌响应模型

    需求引用:
        - 需求1.2: 访问令牌有效期为7天，刷新令牌有效期为30天
    """

    access_token: str = Field(
        ..., description="访问令牌", examples=["eyJ0eXAiOiJKV1QiLCJhbGc..."]
    )
    refresh_token: str = Field(
        ..., description="刷新令牌", examples=["eyJ0eXAiOiJKV1QiLCJhbGc..."]
    )
    token_type: str = Field(default="bearer", description="令牌类型", examples=["bearer"])
    expires_in: int = Field(..., description="访问令牌有效期（秒）", examples=[604800])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                    "expires_in": 604800,
                }
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""

    refresh_token: str = Field(..., description="刷新令牌")


class PasswordChangeRequest(BaseModel):
    """
    修改密码请求模型

    需求引用:
        - 需求1.4: 提供正确的旧密码时使用bcrypt加密新密码并更新
    """

    old_password: str = Field(..., description="旧密码", examples=["OldPassword123"])
    new_password: str = Field(
        ..., min_length=8, description="新密码（至少8位，包含字母和数字）", examples=["NewPassword456"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"old_password": "OldPassword123", "new_password": "NewPassword456"}
            ]
        }
    }

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        """验证新密码强度"""
        if len(v) < 8:
            raise ValueError("密码长度至少8位")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("密码必须包含字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含数字")
        return v


class UserResponse(BaseModel):
    """用户信息响应模型"""

    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(default=None, description="邮箱地址")
    avatar: Optional[str] = Field(default=None, description="头像URL")
    created_at: datetime = Field(..., description="创建时间")
    is_active: bool = Field(..., description="是否激活")

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """通用消息响应模型"""

    message: str = Field(..., description="响应消息")


# 导出
__all__ = [
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "RefreshTokenRequest",
    "PasswordChangeRequest",
    "UserResponse",
    "MessageResponse",
]
