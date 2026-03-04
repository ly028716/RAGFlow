# Phase 1: OpenClaw 基础集成 - 技术设计文档

**文档版本**: v1.0
**创建日期**: 2026-03-03
**作者**: 架构师
**状态**: 待评审

---

## 1. 设计概述

### 1.1 目标

实现 FastAPI 后端与 OpenClaw Gateway 的基础通信能力，为后续的浏览器采集、混合推理等高级功能奠定基础。

### 1.2 核心功能

1. **OpenClaw 客户端封装** - 提供统一的 OpenClaw Gateway API 调用接口
2. **健康检查端点** - 监控 OpenClaw Gateway 连接状态
3. **消息发送端点** - 支持向 OpenClaw Agent 发送消息
4. **前端状态指示器** - 实时显示 OpenClaw 连接状态

### 1.3 技术约束

- 遵循项目 4 层架构（API → Service → Repository → Infrastructure）
- 使用 API 代理模式（FastAPI 作为统一网关）
- OpenClaw Gateway 运行在 WSL Ubuntu，监听 localhost:19001
- 支持异步调用（async/await）
- 完整的错误处理和日志记录

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                  前端 Vue 3 应用                         │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  OpenClawStatus.vue                            │    │
│  │  - 连接状态显示（绿色/红色/黄色）              │    │
│  │  - 定时健康检查（每 30 秒）                    │    │
│  │  - 版本信息显示                                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI 后端（API 网关层）                  │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  app/api/v1/openclaw.py                        │    │
│  │  - GET  /api/v1/openclaw/health                │    │
│  │  - POST /api/v1/openclaw/message               │    │
│  └────────────────────────────────────────────────┘    │
│                          │                              │
│                          ▼                              │
│  ┌────────────────────────────────────────────────┐    │
│  │  app/core/openclaw_client.py                   │    │
│  │  - OpenClawClient 类                           │    │
│  │  - 连接管理、请求转发、错误处理                │    │
│  └────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────┐
│           OpenClaw Gateway (WSL Ubuntu)                  │
│           http://localhost:19001                         │
│                                                          │
│  - /health - 健康检查                                   │
│  - /api/message - 消息发送                              │
│  - /api/agents - Agent 列表                             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

#### 健康检查流程

```
前端 OpenClawStatus.vue
    │
    │ 1. 每 30 秒发起请求
    ▼
GET /api/v1/openclaw/health
    │
    │ 2. FastAPI 路由处理
    ▼
OpenClawClient.health_check()
    │
    │ 3. HTTP 请求到 OpenClaw Gateway
    ▼
http://localhost:19001/health
    │
    │ 4. 返回健康状态
    ▼
{
  "status": "healthy",
  "version": "2026.2.6-3",
  "uptime": 3600
}
    │
    │ 5. 前端更新状态指示器
    ▼
显示绿色/红色状态
```

#### 消息发送流程

```
前端/其他服务
    │
    │ 1. 发送消息请求
    ▼
POST /api/v1/openclaw/message
{
  "message": "查询知识库",
  "agent_id": "default",
  "context": {...}
}
    │
    │ 2. JWT 认证验证
    ▼
OpenClawClient.send_message()
    │
    │ 3. 转发到 OpenClaw Gateway
    ▼
POST http://localhost:19001/api/message
    │
    │ 4. OpenClaw Agent 处理
    ▼
{
  "response": "查询结果...",
  "agent_id": "default",
  "execution_time": 1.5
}
    │
    │ 5. 返回给前端
    ▼
显示响应结果
```

---

## 3. 详细设计

### 3.1 OpenClawClient 类设计

#### 文件位置
`backend/app/core/openclaw_client.py`

#### 类定义

```python
import httpx
from typing import Optional, Dict, Any, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class OpenClawClient:
    """
    OpenClaw Gateway API 客户端

    提供与 OpenClaw Gateway 通信的统一接口，包括：
    - 健康检查
    - 消息发送
    - 连接管理
    - 错误处理和重试
    """

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        初始化 OpenClaw 客户端

        Args:
            gateway_url: OpenClaw Gateway URL，默认从配置读取
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.gateway_url = gateway_url or self._get_default_gateway_url()
        self.timeout = timeout
        self.max_retries = max_retries

        # 创建 httpx 异步客户端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "RAGAgent/1.0"
            },
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
        )

        logger.info(
            f"OpenClawClient 初始化: gateway_url={self.gateway_url}, "
            f"timeout={timeout}s, max_retries={max_retries}"
        )

    def _get_default_gateway_url(self) -> str:
        """从配置获取默认 Gateway URL"""
        # 从环境变量或配置文件读取
        return "http://localhost:19001"

    async def health_check(self) -> Dict[str, Any]:
        """
        检查 OpenClaw Gateway 健康状态

        Returns:
            健康状态信息:
            {
                "status": "healthy" | "unhealthy",
                "version": "2026.2.6-3",
                "uptime": 3600,
                "error": "错误信息（如果不健康）"
            }

        Raises:
            OpenClawConnectionError: 连接失败
        """
        try:
            response = await self.client.get(f"{self.gateway_url}/health")
            response.raise_for_status()

            data = response.json()
            logger.debug(f"OpenClaw 健康检查成功: {data}")

            return {
                "status": "healthy",
                "version": data.get("version", "unknown"),
                "uptime": data.get("uptime", 0),
                "gateway_url": self.gateway_url
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenClaw 健康检查失败: HTTP {e.response.status_code}")
            return {
                "status": "unhealthy",
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "gateway_url": self.gateway_url
            }

        except httpx.ConnectError as e:
            logger.error(f"OpenClaw 连接失败: {str(e)}")
            return {
                "status": "unhealthy",
                "error": f"连接失败: {str(e)}",
                "gateway_url": self.gateway_url
            }

        except Exception as e:
            logger.error(f"OpenClaw 健康检查异常: {str(e)}")
            return {
                "status": "unhealthy",
                "error": f"未知错误: {str(e)}",
                "gateway_url": self.gateway_url
            }

    async def send_message(
        self,
        message: str,
        agent_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        发送消息到 OpenClaw Agent

        Args:
            message: 消息内容
            agent_id: Agent ID，默认使用 default agent
            context: 上下文信息（可选）
            stream: 是否使用流式响应

        Returns:
            Agent 响应:
            {
                "response": "响应内容",
                "agent_id": "default",
                "execution_time": 1.5,
                "steps": [...]  # Agent 执行步骤（如果有）
            }

        Raises:
            OpenClawAPIError: API 调用失败
            OpenClawTimeoutError: 请求超时
        """
        payload = {
            "message": message,
            "agent_id": agent_id or "default",
            "context": context or {},
            "stream": stream
        }

        logger.info(
            f"发送消息到 OpenClaw: agent_id={agent_id}, "
            f"message_length={len(message)}, stream={stream}"
        )

        try:
            response = await self.client.post(
                f"{self.gateway_url}/api/message",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"OpenClaw 响应成功: execution_time={data.get('execution_time')}s")

            return data

        except httpx.HTTPStatusError as e:
            error_msg = f"OpenClaw API 错误: HTTP {e.response.status_code}"
            logger.error(f"{error_msg}: {e.response.text}")
            raise OpenClawAPIError(error_msg, status_code=e.response.status_code)

        except httpx.TimeoutException as e:
            error_msg = f"OpenClaw 请求超时: {self.timeout}s"
            logger.error(error_msg)
            raise OpenClawTimeoutError(error_msg)

        except Exception as e:
            error_msg = f"OpenClaw 调用失败: {str(e)}"
            logger.error(error_msg)
            raise OpenClawAPIError(error_msg)

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
        logger.info("OpenClawClient 连接已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 全局客户端实例（单例模式）
_openclaw_client: Optional[OpenClawClient] = None

def get_openclaw_client() -> OpenClawClient:
    """
    获取全局 OpenClaw 客户端实例（单例）

    Returns:
        OpenClawClient 实例
    """
    global _openclaw_client
    if _openclaw_client is None:
        _openclaw_client = OpenClawClient()
    return _openclaw_client

async def close_openclaw_client():
    """关闭全局 OpenClaw 客户端"""
    global _openclaw_client
    if _openclaw_client is not None:
        await _openclaw_client.close()
        _openclaw_client = None
```


#### 自定义异常类

```python
# backend/app/core/openclaw_client.py (续)

class OpenClawError(Exception):
    """OpenClaw 基础异常类"""
    pass

class OpenClawConnectionError(OpenClawError):
    """OpenClaw 连接错误"""
    pass

class OpenClawAPIError(OpenClawError):
    """OpenClaw API 调用错误"""
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)

class OpenClawTimeoutError(OpenClawError):
    """OpenClaw 请求超时"""
    pass
```

### 3.2 API 端点设计

#### 文件位置
`backend/app/api/v1/openclaw.py`

#### 端点定义

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.models.user import User
from app.core.openclaw_client import get_openclaw_client, OpenClawClient
from app.schemas.openclaw import (
    OpenClawHealthResponse,
    OpenClawMessageRequest,
    OpenClawMessageResponse
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openclaw", tags=["openclaw"])

@router.get(
    "/health",
    response_model=OpenClawHealthResponse,
    summary="OpenClaw 健康检查",
    description="检查 OpenClaw Gateway 的连接状态和健康信息"
)
async def check_openclaw_health(
    openclaw_client: OpenClawClient = Depends(get_openclaw_client)
) -> OpenClawHealthResponse:
    """检查 OpenClaw Gateway 健康状态，无需认证"""
    health_info = await openclaw_client.health_check()
    return OpenClawHealthResponse(**health_info)

@router.post(
    "/message",
    response_model=OpenClawMessageResponse,
    summary="发送消息到 OpenClaw Agent",
    description="向 OpenClaw Agent 发送消息并获取响应"
)
async def send_message_to_openclaw(
    request: OpenClawMessageRequest,
    current_user: User = Depends(get_current_user),
    openclaw_client: OpenClawClient = Depends(get_openclaw_client)
) -> OpenClawMessageResponse:
    """发送消息到 OpenClaw Agent，需要用户认证"""
    logger.info(
        f"用户 {current_user.id} 发送消息到 OpenClaw: "
        f"agent_id={request.agent_id}, message_length={len(request.message)}"
    )
    
    try:
        response = await openclaw_client.send_message(
            message=request.message,
            agent_id=request.agent_id,
            context=request.context,
            stream=request.stream
        )
        return OpenClawMessageResponse(**response)
    except Exception as e:
        logger.error(f"OpenClaw 消息发送失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OpenClaw 服务不可用: {str(e)}"
        )
```


### 3.3 Pydantic Schemas 设计

#### 文件位置
`backend/app/schemas/openclaw.py`

#### Schema 定义

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class OpenClawStatus(str, Enum):
    """OpenClaw 状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class OpenClawHealthResponse(BaseModel):
    """OpenClaw 健康检查响应"""
    status: OpenClawStatus = Field(..., description="健康状态")
    version: Optional[str] = Field(None, description="OpenClaw 版本")
    uptime: Optional[int] = Field(None, description="运行时间（秒）")
    gateway_url: str = Field(..., description="Gateway URL")
    error: Optional[str] = Field(None, description="错误信息（如果不健康）")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "2026.2.6-3",
                "uptime": 3600,
                "gateway_url": "http://localhost:19001",
                "error": None
            }
        }

class OpenClawMessageRequest(BaseModel):
    """OpenClaw 消息发送请求"""
    message: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    agent_id: Optional[str] = Field("default", description="Agent ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")
    stream: bool = Field(False, description="是否使用流式响应")

class AgentStep(BaseModel):
    """Agent 执行步骤"""
    type: str = Field(..., description="步骤类型: thought, action, observation")
    content: str = Field(..., description="步骤内容")
    timestamp: Optional[str] = Field(None, description="时间戳")

class OpenClawMessageResponse(BaseModel):
    """OpenClaw 消息响应"""
    response: str = Field(..., description="Agent 响应内容")
    agent_id: str = Field(..., description="Agent ID")
    execution_time: float = Field(..., description="执行时间（秒）")
    steps: Optional[List[AgentStep]] = Field(None, description="执行步骤（如果有）")
```

---

## 4. 用户体验设计

### 4.1 前端状态指示器 UI 规范

#### 4.1.1 组件位置

**推荐位置**: 顶部导航栏右侧区域

```
┌─────────────────────────────────────────────────────────┐
│  Logo    导航菜单              [OpenClaw状态] [用户]    │
└─────────────────────────────────────────────────────────┘
```

**设计原则**:
- 不遮挡主要功能区域
- 易于发现但不干扰用户操作
- 响应式布局：移动端可折叠到菜单中

#### 4.1.2 状态展示规范

**三种状态视觉设计**:

| 状态 | 图标 | 颜色 | 文本 | 说明 |
|------|------|------|------|------|
| 正常 | 🟢 | `#52c41a` (绿色) | "OpenClaw 已连接" | Gateway 健康检查通过 |
| 连接中 | 🟡 | `#faad14` (黄色) | "OpenClaw 连接中..." | 正在进行健康检查或重试 |
| 不可用 | 🔴 | `#ff4d4f` (红色) | "OpenClaw 不可用" | 连接失败或超时 |

**状态指示器组件结构**:

```vue
<template>
  <div class="openclaw-status" :class="statusClass">
    <el-badge :value="retryCount" :hidden="retryCount === 0">
      <div class="status-indicator">
        <span class="status-dot" :style="{ backgroundColor: statusColor }"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </el-badge>

    <!-- 版本信息（鼠标悬停显示） -->
    <el-tooltip :content="tooltipContent" placement="bottom">
      <el-icon class="info-icon"><InfoFilled /></el-icon>
    </el-tooltip>
  </div>
</template>
```

#### 4.1.3 交互行为规范

**1. 点击交互**

点击状态指示器打开详情弹窗，显示：

```
┌─────────────────────────────────────┐
│  OpenClaw 连接详情                  │
├─────────────────────────────────────┤
│  状态: 🟢 正常                      │
│  版本: 2026.2.6-3                   │
│  运行时间: 2小时15分钟              │
│  Gateway URL: localhost:19001       │
│  最后检查: 5秒前                    │
├─────────────────────────────────────┤
│  [重新连接]  [关闭]                 │
└─────────────────────────────────────┘
```

**2. 自动刷新机制**

- 健康检查间隔: 30秒
- 连接失败后重试间隔: 5秒（最多3次）
- 重试失败后降级，每5分钟尝试恢复一次

**3. 状态变化通知**

使用 Element Plus Toast 通知用户状态变化：

```typescript
// 连接成功
ElNotification.success({
  title: 'OpenClaw 已连接',
  message: '版本: 2026.2.6-3',
  duration: 3000
})

// 连接失败（降级）
ElNotification.warning({
  title: 'OpenClaw 暂时不可用',
  message: '已切换到知识库模式，功能不受影响',
  duration: 5000
})

// 连接恢复
ElNotification.success({
  title: 'OpenClaw 已恢复',
  message: '现在可以使用完整功能',
  duration: 3000
})
```

**4. 用户配置选项**

允许用户配置通知行为（存储在 localStorage）：

```typescript
interface OpenClawUIConfig {
  showNotifications: boolean;      // 是否显示状态变化通知
  notificationDuration: number;    // 通知显示时长（毫秒）
  autoRetry: boolean;              // 是否自动重试连接
  healthCheckInterval: number;     // 健康检查间隔（秒）
}
```

---

### 4.2 降级体验设计

#### 4.2.1 降级场景识别

**场景1: OpenClaw 完全不可用**

```
用户操作: 发送消息 "帮我查询最新的产品文档"
系统行为:
  1. 检测到 OpenClaw 不可用
  2. 自动切换到纯 RAG 模式
  3. 在消息旁显示标识: [知识库模式]
  4. 正常返回知识库中的答案
```

**场景2: OpenClaw 响应超时**

```
用户操作: 发送需要 OpenClaw 处理的消息
系统行为:
  1. 显示加载状态: "OpenClaw 处理中..."
  2. 30秒后超时
  3. 显示提示: "OpenClaw 响应超时，使用知识库模式回答"
  4. 降级到 RAG 模式返回结果
```

**场景3: OpenClaw 部分功能不可用**

```
用户操作: 请求浏览器采集功能
系统行为:
  1. 检测到浏览器采集功能不可用
  2. 提示: "浏览器采集功能暂时不可用，使用知识库回答"
  3. 降级到 RAG 模式
```

#### 4.2.2 降级 UI 设计

**1. 消息模式标识**

在每条消息旁边显示小图标标识使用的模式：

```
┌─────────────────────────────────────┐
│  用户: 查询最新产品文档             │
├─────────────────────────────────────┤
│  AI [🔵 OpenClaw]: 正在采集...      │  ← OpenClaw 模式
│                                     │
│  AI [📚 知识库]: 根据知识库...      │  ← 降级到知识库模式
└─────────────────────────────────────┘
```

**图标说明**:
- 🔵 OpenClaw 模式: 使用 OpenClaw Agent 处理
- 📚 知识库模式: 使用纯 RAG 模式
- ⚠️ 降级模式: 原本应该用 OpenClaw，但降级了

**2. 降级提示设计**

在消息上方显示降级提示条：

```vue
<el-alert
  type="warning"
  :closable="true"
  show-icon
  title="当前使用知识库模式"
  description="OpenClaw 暂时不可用，部分功能受限。系统将自动尝试恢复连接。"
/>
```

**3. 功能受限说明**

在输入框上方显示功能受限提示：

```
┌─────────────────────────────────────┐
│  ⚠️ OpenClaw 不可用，以下功能受限:  │
│  • 实时网页采集                     │
│  • 浏览器自动化                     │
│  • 混合推理                         │
│  当前可用: 知识库问答               │
└─────────────────────────────────────┘
```

#### 4.2.3 用户体验优化

**1. 无感知降级**

- 用户发送消息时，系统自动判断是否需要 OpenClaw
- 如果不需要（纯知识库查询），不显示任何降级提示
- 只在确实需要 OpenClaw 功能时才提示降级

**2. 降级状态持久化**

```typescript
// 存储降级状态到 Pinia store
interface OpenClawState {
  status: 'healthy' | 'unhealthy' | 'unknown';
  degraded: boolean;              // 是否处于降级状态
  degradedSince: Date | null;     // 降级开始时间
  lastHealthCheck: Date | null;   // 最后健康检查时间
  retryCount: number;             // 重试次数
}
```

**3. 降级恢复动画**

当 OpenClaw 恢复时，使用动画效果：

```css
.status-indicator.recovering {
  animation: pulse 1s ease-in-out;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

### 4.3 性能 SLA 指标

#### 4.3.1 响应时间指标

**健康检查性能**:

| 指标 | 目标值 | 说明 |
|------|--------|------|
| P50 | < 200ms | 50% 的请求在 200ms 内完成 |
| P95 | < 500ms | 95% 的请求在 500ms 内完成 |
| P99 | < 1s | 99% 的请求在 1s 内完成 |
| 超时 | 3s | 超过 3s 视为超时 |

**消息发送性能**:

| 指标 | 目标值 | 说明 |
|------|--------|------|
| P50 | < 1s | 50% 的请求在 1s 内完成 |
| P95 | < 3s | 95% 的请求在 3s 内完成 |
| P99 | < 5s | 99% 的请求在 5s 内完成 |
| 超时 | 30s | 超过 30s 自动降级 |

**首字响应时间（TTFB）**:

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 流式响应 TTFB | < 500ms | 用户看到第一个字的时间 |
| 非流式响应 | < 2s | 完整响应返回时间 |

#### 4.3.2 可用性指标

**系统可用性**:

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 月度可用性 | > 99.5% | 每月停机时间 < 3.6 小时 |
| 连续失败容忍 | 3次 | 连续失败 3 次后降级 |
| 降级恢复时间 | < 5分钟 | 从降级到恢复的时间 |

**并发能力**:

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 并发请求数 | 10+ | 同时处理的请求数 |
| 排队等待时间 | < 2s | 请求在队列中的等待时间 |
| 连接池大小 | 10-20 | httpx 连接池配置 |

#### 4.3.3 性能监控

**监控指标采集**:

```python
# backend/app/core/openclaw_client.py

import time
from prometheus_client import Histogram, Counter

# 定义 Prometheus 指标
openclaw_request_duration = Histogram(
    'openclaw_request_duration_seconds',
    'OpenClaw request duration',
    ['endpoint', 'status']
)

openclaw_request_total = Counter(
    'openclaw_request_total',
    'Total OpenClaw requests',
    ['endpoint', 'status']
)

async def health_check(self) -> Dict[str, Any]:
    start_time = time.time()
    try:
        response = await self.client.get(f"{self.gateway_url}/health")
        duration = time.time() - start_time

        # 记录指标
        openclaw_request_duration.labels(
            endpoint='health',
            status='success'
        ).observe(duration)

        openclaw_request_total.labels(
            endpoint='health',
            status='success'
        ).inc()

        return response.json()
    except Exception as e:
        duration = time.time() - start_time
        openclaw_request_duration.labels(
            endpoint='health',
            status='error'
        ).observe(duration)

        openclaw_request_total.labels(
            endpoint='health',
            status='error'
        ).inc()

        raise
```

**性能告警规则**:

```yaml
# prometheus/alerts.yml

groups:
  - name: openclaw_performance
    rules:
      # P95 响应时间告警
      - alert: OpenClawSlowResponse
        expr: histogram_quantile(0.95, openclaw_request_duration_seconds) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "OpenClaw P95 响应时间超过 5 秒"

      # 错误率告警
      - alert: OpenClawHighErrorRate
        expr: rate(openclaw_request_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "OpenClaw 错误率超过 10%"
```

---

### 4.4 降级策略详细设计

#### 4.4.1 降级触发条件

**自动降级触发条件**:

| 条件 | 阈值 | 行为 |
|------|------|------|
| 健康检查连续失败 | 3次（90秒） | 立即降级 |
| 消息发送超时 | 30秒 | 单次请求降级 |
| API 返回 5xx 错误 | 连续 3 次 | 立即降级 |
| 连接错误 | 任意 1 次 | 立即降级 |
| 响应时间过长 | P95 > 10s | 逐步降级 |

**降级决策流程**:

```
┌─────────────────────────────────────────────────────────┐
│  用户发送消息                                            │
└─────────────────┬───────────────────────────────────────┘
                  ▼
         ┌────────────────┐
         │ 检查 OpenClaw  │
         │ 健康状态       │
         └────────┬───────┘
                  ▼
         ┌────────────────┐
    ┌────│ 状态正常？     │────┐
    │ 否 └────────────────┘ 是 │
    ▼                          ▼
┌─────────────┐        ┌──────────────┐
│ 使用 RAG    │        │ 使用 OpenClaw│
│ 模式        │        │ 模式         │
│ [降级]      │        └──────┬───────┘
└─────────────┘               ▼
                      ┌──────────────┐
                      │ 请求成功？   │
                      └──────┬───────┘
                             │
                    ┌────────┴────────┐
                    │ 是              │ 否
                    ▼                 ▼
            ┌──────────────┐  ┌──────────────┐
            │ 返回结果     │  │ 降级到 RAG   │
            └──────────────┘  │ 返回结果     │
                              └──────────────┘
```

#### 4.4.2 降级行为规范

**1. 前端降级行为**

```typescript
// frontend/src/stores/openclaw.ts

export const useOpenClawStore = defineStore('openclaw', {
  state: (): OpenClawState => ({
    status: 'unknown',
    degraded: false,
    degradedSince: null,
    lastHealthCheck: null,
    retryCount: 0,
    config: {
      maxRetries: 3,
      retryInterval: 5000,      // 5秒
      healthCheckInterval: 30000, // 30秒
      recoveryCheckInterval: 300000 // 5分钟
    }
  }),

  actions: {
    async checkHealth() {
      try {
        const response = await api.openclaw.health()

        if (response.status === 'healthy') {
          // 如果之前是降级状态，现在恢复了
          if (this.degraded) {
            this.handleRecovery()
          }
          this.status = 'healthy'
          this.degraded = false
          this.retryCount = 0
        } else {
          this.handleDegradation()
        }
      } catch (error) {
        this.handleDegradation()
      }

      this.lastHealthCheck = new Date()
    },

    handleDegradation() {
      if (!this.degraded) {
        // 首次降级
        this.degraded = true
        this.degradedSince = new Date()

        ElNotification.warning({
          title: 'OpenClaw 暂时不可用',
          message: '已切换到知识库模式，功能不受影响',
          duration: 5000
        })
      }

      this.status = 'unhealthy'
      this.retryCount++

      // 如果重试次数未超限，继续重试
      if (this.retryCount < this.config.maxRetries) {
        setTimeout(() => this.checkHealth(), this.config.retryInterval)
      } else {
        // 重试失败，进入长期降级模式
        this.enterLongTermDegradation()
      }
    },

    enterLongTermDegradation() {
      // 每5分钟尝试恢复一次
      setInterval(() => {
        this.retryCount = 0
        this.checkHealth()
      }, this.config.recoveryCheckInterval)
    },

    handleRecovery() {
      ElNotification.success({
        title: 'OpenClaw 已恢复',
        message: '现在可以使用完整功能',
        duration: 3000
      })

      this.degraded = false
      this.degradedSince = null
      this.retryCount = 0
    }
  }
})
```

**2. 后端降级行为**

```python
# backend/app/services/chat_service.py

class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.openclaw_client = get_openclaw_client()
        self.rag_service = RAGService(db)

    async def send_message(
        self,
        user_id: int,
        content: str,
        use_openclaw: bool = True
    ) -> ChatResponse:
        """
        发送消息，支持自动降级

        Args:
            user_id: 用户ID
            content: 消息内容
            use_openclaw: 是否尝试使用 OpenClaw（默认 True）
        """
        # 1. 检查 OpenClaw 健康状态
        if use_openclaw:
            health = await self.openclaw_client.health_check()

            if health['status'] == 'healthy':
                try:
                    # 2. 尝试使用 OpenClaw
                    response = await self._send_with_openclaw(
                        user_id, content
                    )
                    response.mode = 'openclaw'
                    return response

                except OpenClawTimeoutError:
                    logger.warning(
                        f"OpenClaw 超时，降级到 RAG 模式: "
                        f"user_id={user_id}"
                    )
                    # 超时降级

                except OpenClawAPIError as e:
                    logger.error(
                        f"OpenClaw API 错误，降级到 RAG 模式: "
                        f"user_id={user_id}, error={str(e)}"
                    )
                    # API 错误降级

        # 3. 降级到纯 RAG 模式
        response = await self._send_with_rag(user_id, content)
        response.mode = 'rag'
        response.degraded = True
        return response

    async def _send_with_openclaw(
        self,
        user_id: int,
        content: str
    ) -> ChatResponse:
        """使用 OpenClaw 发送消息"""
        result = await self.openclaw_client.send_message(
            message=content,
            agent_id='default',
            context={'user_id': user_id}
        )

        return ChatResponse(
            content=result['response'],
            execution_time=result['execution_time'],
            mode='openclaw'
        )

    async def _send_with_rag(
        self,
        user_id: int,
        content: str
    ) -> ChatResponse:
        """使用纯 RAG 模式发送消息"""
        result = await self.rag_service.query(
            user_id=user_id,
            query=content
        )

        return ChatResponse(
            content=result['answer'],
            execution_time=result['execution_time'],
            mode='rag',
            degraded=True
        )
```

#### 4.4.3 恢复策略

**自动恢复机制**:

```python
# backend/app/core/openclaw_client.py

class OpenClawClient:
    def __init__(self):
        self.degraded = False
        self.degraded_since = None
        self.recovery_check_interval = 300  # 5分钟

    async def start_recovery_monitor(self):
        """启动恢复监控任务"""
        while True:
            if self.degraded:
                try:
                    health = await self.health_check()
                    if health['status'] == 'healthy':
                        await self.recover()
                except Exception as e:
                    logger.debug(f"恢复检查失败: {str(e)}")

            await asyncio.sleep(self.recovery_check_interval)

    async def recover(self):
        """从降级状态恢复"""
        logger.info("OpenClaw 连接已恢复")
        self.degraded = False
        self.degraded_since = None

        # 发送恢复事件（可选：通过 WebSocket 通知前端）
        await self.notify_recovery()
```

**手动恢复触发**:

用户可以在状态详情弹窗中点击"重新连接"按钮手动触发恢复：

```typescript
// frontend/src/components/OpenClawStatus.vue

async function manualReconnect() {
  loading.value = true

  try {
    await openclawStore.checkHealth()

    if (openclawStore.status === 'healthy') {
      ElMessage.success('重新连接成功')
    } else {
      ElMessage.error('重新连接失败，请稍后再试')
    }
  } finally {
    loading.value = false
  }
}
```

#### 4.4.4 降级状态监控

**降级指标采集**:

```python
from prometheus_client import Gauge, Counter

# 降级状态指标
openclaw_degraded = Gauge(
    'openclaw_degraded',
    'OpenClaw degradation status (1=degraded, 0=normal)'
)

# 降级次数计数
openclaw_degradation_total = Counter(
    'openclaw_degradation_total',
    'Total number of degradations'
)

# 降级持续时间
openclaw_degradation_duration = Histogram(
    'openclaw_degradation_duration_seconds',
    'Duration of degradation periods'
)
```

**降级告警**:

```yaml
# prometheus/alerts.yml

- alert: OpenClawDegraded
  expr: openclaw_degraded == 1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "OpenClaw 已降级超过 10 分钟"
    description: "OpenClaw 自 {{ $value }} 开始处于降级状态"

- alert: OpenClawFrequentDegradation
  expr: rate(openclaw_degradation_total[1h]) > 5
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "OpenClaw 频繁降级"
    description: "过去 1 小时内降级超过 5 次"
```

---

## 5. 错误处理规范

### 4.1 错误码定义

在现有的 `ErrorCode` 枚举中添加 OpenClaw 相关错误码：

```python
# backend/app/middleware/error_handler.py

class ErrorCode(str, Enum):
    # ... 现有错误码 ...
    
    # OpenClaw 错误 (6xxx)
    OPENCLAW_CONNECTION_ERROR = "6001"
    OPENCLAW_API_ERROR = "6002"
    OPENCLAW_TIMEOUT_ERROR = "6003"
    OPENCLAW_UNAVAILABLE = "6004"
```

### 4.2 异常处理策略

#### 连接失败处理

```python
try:
    response = await openclaw_client.health_check()
except OpenClawConnectionError as e:
    logger.error(f"OpenClaw 连接失败: {str(e)}")
    # 返回 unhealthy 状态，不抛出异常
    return {"status": "unhealthy", "error": str(e)}
```

#### API 调用失败处理

```python
try:
    response = await openclaw_client.send_message(...)
except OpenClawTimeoutError as e:
    raise AppException(
        error_code=ErrorCode.OPENCLAW_TIMEOUT_ERROR,
        message="OpenClaw 请求超时",
        status_code=status.HTTP_504_GATEWAY_TIMEOUT
    )
except OpenClawAPIError as e:
    raise AppException(
        error_code=ErrorCode.OPENCLAW_API_ERROR,
        message=f"OpenClaw API 错误: {str(e)}",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE
    )
```

### 4.3 降级策略

当 OpenClaw 不可用时，系统应该能够继续运行：

```python
async def send_message_with_fallback(message: str):
    try:
        # 尝试使用 OpenClaw
        return await openclaw_client.send_message(message)
    except OpenClawError:
        # 降级到纯 RAG 模式
        logger.warning("OpenClaw 不可用，降级到纯 RAG 模式")
        return await rag_service.query(message)
```

---

## 6. 日志记录规范

### 6.1 日志级别

- **DEBUG**: 详细的请求/响应数据
- **INFO**: 关键操作（连接建立、消息发送）
- **WARNING**: 降级、重试
- **ERROR**: 连接失败、API 错误

### 5.2 日志格式

```python
# 连接建立
logger.info(f"OpenClawClient 初始化: gateway_url={gateway_url}, timeout={timeout}s")

# 健康检查
logger.debug(f"OpenClaw 健康检查成功: version={version}, uptime={uptime}s")

# 消息发送
logger.info(
    f"用户 {user_id} 发送消息到 OpenClaw: "
    f"agent_id={agent_id}, message_length={len(message)}"
)

# 错误日志
logger.error(
    f"OpenClaw API 错误: status_code={status_code}, "
    f"error={error_message}, request_id={request_id}"
)
```

### 5.3 敏感信息脱敏

```python
# 不要记录完整的消息内容，只记录长度
logger.info(f"message_length={len(message)}")  # ✅ 正确

# 不要记录用户的敏感上下文
logger.info(f"context_keys={list(context.keys())}")  # ✅ 正确
logger.info(f"context={context}")  # ❌ 错误
```

---

## 7. 配置管理

### 7.1 环境变量

在 `.env` 文件中添加 OpenClaw 配置：

```bash
# OpenClaw Gateway Configuration
OPENCLAW_GATEWAY_URL=http://localhost:19001
OPENCLAW_TIMEOUT=30
OPENCLAW_MAX_RETRIES=3
OPENCLAW_ENABLED=True
```

### 6.2 配置类

在 `backend/app/config.py` 中添加配置类：

```python
class OpenClawSettings(BaseSettings):
    """OpenClaw 配置"""
    
    model_config = SettingsConfigDict(env_prefix="OPENCLAW_", case_sensitive=False)
    
    gateway_url: str = Field(
        default="http://localhost:19001",
        description="OpenClaw Gateway URL"
    )
    timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=300.0,
        description="请求超时时间（秒）"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数"
    )
    enabled: bool = Field(
        default=True,
        description="是否启用 OpenClaw 集成"
    )

# 在 Settings 类中添加
class Settings(BaseSettings):
    # ... 现有配置 ...
    openclaw: OpenClawSettings = Field(default_factory=OpenClawSettings)
```

---

## 8. 测试计划

### 8.1 单元测试

#### OpenClawClient 测试

```python
# backend/tests/core/test_openclaw_client.py
import pytest
from unittest.mock import AsyncMock, patch
from app.core.openclaw_client import OpenClawClient

@pytest.mark.asyncio
async def test_health_check_success():
    """测试健康检查成功"""
    client = OpenClawClient()

    with patch.object(client.client, 'get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'version': '2026.2.6-3',
            'uptime': 3600
        }
        mock_get.return_value = mock_response

        result = await client.health_check()

        assert result['status'] == 'healthy'
        assert result['version'] == '2026.2.6-3'
```

### 7.2 集成测试

需要 OpenClaw Gateway 运行在 localhost:19001

### 7.3 测试覆盖率目标

- OpenClawClient: > 90%
- API 端点: > 85%
- 异常处理: 100%

---

## 9. 部署方案

### 9.1 环境准备

```bash
# 确认 OpenClaw Gateway 运行
wsl bash -c "openclaw health"

# 配置环境变量
OPENCLAW_GATEWAY_URL=http://localhost:19001
OPENCLAW_TIMEOUT=30
OPENCLAW_ENABLED=True
```

### 8.2 部署步骤

1. 安装依赖：`pip install httpx`
2. 创建文件：openclaw_client.py, openclaw.py, schemas/openclaw.py
3. 注册路由到 app/api/v1/__init__.py
4. 重启服务

### 8.3 验证部署

```bash
curl http://localhost:8000/api/v1/openclaw/health
```

---

## 10. 监控与运维

### 10.1 监控指标

- 连接状态：OpenClaw Gateway 可用性
- 性能指标：响应时间 P50/P95/P99
- 错误指标：连接错误、API 错误、超时

### 9.2 告警规则

- OpenClaw 不可用 > 5 分钟
- 错误率 > 10%
- 响应时间 P95 > 5 秒

---

## 11. 性能优化

### 11.1 连接池管理

使用 httpx 连接池，保持 10 个活动连接

### 10.2 请求缓存

健康检查结果缓存 30 秒

### 10.3 异步并发

使用 asyncio.gather 并发处理多个请求

---

## 12. 安全考虑

### 12.1 网络安全

- OpenClaw Gateway 仅监听 localhost
- 所有外部请求通过 FastAPI 网关统一认证
- 生产环境使用 HTTPS

### 11.2 输入验证

- 消息长度限制：1-10000 字符
- Agent ID 白名单验证
- Context 数据大小限制

### 11.3 速率限制

每分钟最多 20 次 OpenClaw 调用

---

## 13. 总结

### 13.1 交付物清单

- [x] OpenClawClient 类实现
- [x] API 端点实现（health, message）
- [x] Pydantic Schemas 定义
- [x] 前端状态组件
- [x] 错误处理规范
- [x] 日志记录规范
- [x] 配置管理
- [x] 测试计划
- [x] 部署文档

### 12.2 验收标准

#### 功能验收
- [ ] 可以从 FastAPI 成功调用 OpenClaw Gateway
- [ ] 健康检查 API 正常工作
- [ ] 消息发送 API 正常工作
- [ ] 前端显示 OpenClaw 连接状态

#### 质量验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 所有测试通过
- [ ] 代码审查通过
- [ ] 无严重安全漏洞

#### 性能验收
- [ ] 健康检查响应时间 < 1 秒
- [ ] 消息发送响应时间 < 5 秒
- [ ] 支持 10+ 并发请求

### 12.3 后续工作

Phase 1 完成后，将进入 Phase 2：知识库工具集成

- 在 OpenClaw 中注册自定义工具 `query_knowledge_base`
- 实现工具端点 `/api/v1/openclaw/tools/query-kb`
- 测试 Agent 调用知识库查询

---

**文档结束**
