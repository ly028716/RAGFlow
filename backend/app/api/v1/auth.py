"""
认证API路由模块

实现用户注册、登录、令牌刷新和密码修改等认证相关的API端点。

需求引用:
    - 需求1.1: 用户注册
    - 需求1.2: 用户登录和JWT令牌生成
    - 需求1.4: 密码修改
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.middleware.rate_limiter import rate_limit_login
from app.models.user import User
from app.schemas.auth import (MessageResponse, PasswordChangeRequest,
                              RefreshTokenRequest, TokenResponse, UserLogin,
                              UserRegister, UserResponse)
from app.services.auth import (AccountLockedError, AuthService,
                               InvalidCredentialsError, PasswordMismatchError,
                               UserAlreadyExistsError, UserNotFoundError)
from app.utils.client_ip import get_client_ip

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
    description="创建新用户账户。用户名必须唯一，密码至少8位且包含字母和数字。",
)
@rate_limit_login()
def register(
    user_data: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    用户注册端点

    需求引用:
        - 需求1.1: 用户名唯一且密码强度符合要求时创建新用户账户并返回成功状态

    Args:
        user_data: 用户注册信息
        db: 数据库会话

    Returns:
        UserResponse: 创建的用户信息

    Raises:
        HTTPException 400: 用户名或邮箱已存在
    """
    auth_service = AuthService(db)

    try:
        user = auth_service.register(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
        )
        return UserResponse.model_validate(user)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="验证用户凭证并返回JWT令牌。连续5次登录失败将锁定账户15分钟。",
)
@rate_limit_login()
def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    用户登录端点

    需求引用:
        - 需求1.2: 凭证正确时生成JWT令牌，访问令牌有效期7天，刷新令牌有效期30天
        - 需求1.7: 连续5次登录失败后锁定账户15分钟

    Args:
        credentials: 登录凭证
        request: HTTP请求对象
        db: 数据库会话

    Returns:
        TokenResponse: JWT令牌信息

    Raises:
        HTTPException 401: 用户名或密码错误
        HTTPException 423: 账户已被锁定
    """
    auth_service = AuthService(db)
    client_ip = get_client_ip(request)

    try:
        tokens = auth_service.login(
            username=credentials.username,
            password=credentials.password,
            ip_address=client_ip,
        )
        return TokenResponse(**tokens)
    except AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(e))
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="刷新令牌",
    description="使用刷新令牌获取新的访问令牌。",
)
def refresh_token(
    token_data: RefreshTokenRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """
    刷新令牌端点

    使用刷新令牌获取新的访问令牌和刷新令牌。
    旧的刷新令牌将被加入黑名单。

    Args:
        token_data: 刷新令牌请求
        db: 数据库会话

    Returns:
        TokenResponse: 新的JWT令牌信息

    Raises:
        HTTPException 401: 刷新令牌无效或已过期
    """
    auth_service = AuthService(db)

    try:
        tokens = auth_service.refresh_token(token_data.refresh_token)
        return TokenResponse(**tokens)
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get(
    "/profile",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="获取当前登录用户的详细信息。",
)
def get_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """
    获取当前用户信息端点

    Args:
        current_user: 当前认证用户

    Returns:
        UserResponse: 用户信息
    """
    return UserResponse.model_validate(current_user)


@router.put(
    "/password",
    response_model=MessageResponse,
    summary="修改密码",
    description="修改当前用户的密码。需要提供正确的旧密码。",
)
def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    修改密码端点

    需求引用:
        - 需求1.4: 提供正确的旧密码时使用bcrypt加密新密码并更新数据库记录

    Args:
        password_data: 密码修改请求
        current_user: 当前认证用户
        db: 数据库会话

    Returns:
        MessageResponse: 成功消息

    Raises:
        HTTPException 401: 未认证或令牌无效
        HTTPException 400: 旧密码不正确
        HTTPException 404: 用户不存在
    """
    auth_service = AuthService(db)

    try:
        auth_service.change_password(
            user_id=current_user.id,
            old_password=password_data.old_password,
            new_password=password_data.new_password,
        )
        return MessageResponse(message="密码修改成功")
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PasswordMismatchError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# 导出
__all__ = ["router"]
