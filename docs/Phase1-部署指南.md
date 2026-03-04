# Phase1 OpenClaw 集成 - 部署指南

## 概述

本文档提供 Phase1 OpenClaw Gateway 集成的完整部署指南，包括环境配置、测试验证和故障排查。

---

## 前置条件

### 1. 系统要求

- **操作系统**: Windows 10/11 + WSL2 Ubuntu，或 Linux/macOS
- **Python**: 3.10+
- **Node.js**: 18+
- **Docker**: 20.10+ (可选，用于容器化部署)
- **OpenClaw Gateway**: 运行在 localhost:19001 (WSL Ubuntu)

### 2. 依赖服务

- MySQL 8.0+
- Redis 7.0+
- OpenClaw Gateway (独立服务)

---

## 环境配置

### 1. 后端环境变量

在 `backend/.env` 文件中添加以下 OpenClaw 配置：

```bash
# OpenClaw Gateway Configuration
OPENCLAW_GATEWAY_URL=http://localhost:19001
OPENCLAW_TIMEOUT=30.0
OPENCLAW_MAX_RETRIES=3
OPENCLAW_ENABLED=True
```

#### 配置说明

| 变量 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| `OPENCLAW_GATEWAY_URL` | OpenClaw Gateway 地址 | `http://localhost:19001` | 是 |
| `OPENCLAW_TIMEOUT` | 请求超时时间（秒） | `30.0` | 否 |
| `OPENCLAW_MAX_RETRIES` | 最大重试次数 | `3` | 否 |
| `OPENCLAW_ENABLED` | 是否启用 OpenClaw | `True` | 否 |

#### 网络配置注意事项

**WSL2 环境**:
- OpenClaw Gateway 运行在 WSL Ubuntu
- 从 Windows 访问: `http://localhost:19001`
- 从 Docker 容器访问: `http://host.docker.internal:19001`

**Linux/macOS 环境**:
- 直接使用 `http://localhost:19001`

### 2. Docker 环境配置

如果使用 Docker 部署，`docker-compose.yml` 已包含 OpenClaw 配置：

```yaml
environment:
  OPENCLAW_GATEWAY_URL: ${OPENCLAW_GATEWAY_URL:-http://host.docker.internal:19001}
  OPENCLAW_TIMEOUT: ${OPENCLAW_TIMEOUT:-30.0}
  OPENCLAW_MAX_RETRIES: ${OPENCLAW_MAX_RETRIES:-3}
  OPENCLAW_ENABLED: ${OPENCLAW_ENABLED:-True}
```

在 `backend/.env` 中设置：

```bash
OPENCLAW_GATEWAY_URL=http://host.docker.internal:19001
```

---

## 部署步骤

### 方式 1: 本地开发部署

#### 1. 启动 OpenClaw Gateway

在 WSL Ubuntu 中启动 OpenClaw Gateway：

```bash
# 在 WSL Ubuntu 中
cd /path/to/openclaw
./start_gateway.sh
```

验证 Gateway 运行：

```bash
curl http://localhost:19001/health
```

预期响应：

```json
{
  "status": "healthy",
  "version": "2026.2.6-3",
  "uptime": 3600
}
```

#### 2. 启动后端服务

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. 启动前端服务

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 4. 验证集成

访问前端: http://localhost:5173

检查右上角 OpenClaw 状态指示器：
- 🟢 绿色 = 已连接
- 🔴 红色 = 不可用
- 🟡 黄色 = 连接中

### 方式 2: Docker 容器化部署

#### 1. 准备环境文件

```bash
cd backend
cp .env.example .env
# 编辑 .env，设置必要的环境变量
```

确保 `.env` 中包含：

```bash
OPENCLAW_GATEWAY_URL=http://host.docker.internal:19001
DASHSCOPE_API_KEY=your-api-key-here
SECRET_KEY=your-secret-key-here
```

#### 2. 启动所有服务

```bash
cd backend
docker-compose up -d
```

#### 3. 运行数据库迁移

```bash
docker-compose exec backend alembic upgrade head
```

#### 4. 验证服务状态

```bash
# 检查所有服务
docker-compose ps

# 检查后端日志
docker-compose logs -f backend

# 检查前端日志
docker-compose logs -f frontend
```

#### 5. 访问应用

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

---

## 集成测试

### 1. 运行单元测试

```bash
cd backend

# 运行所有单元测试
pytest tests/core/test_openclaw_client.py -v
pytest tests/api/v1/test_openclaw.py -v

# 查看测试覆盖率
pytest --cov=app.core.openclaw_client --cov=app.api.v1.openclaw --cov-report=html
```

### 2. 运行集成测试

**前提**: OpenClaw Gateway 必须运行

```bash
cd backend

# 设置环境变量
export OPENCLAW_GATEWAY_URL=http://localhost:19001

# 运行集成测试
pytest tests/integration/test_openclaw_integration.py -v -s -m integration

# 快速验证（直接运行脚本）
python tests/integration/test_openclaw_integration.py
```

### 3. 配置 pytest

在 `backend/pytest.ini` 或 `backend/pyproject.toml` 中添加：

```ini
[pytest]
markers =
    integration: Integration tests that require external services
```

### 4. 集成测试场景

集成测试覆盖以下场景：

- ✅ OpenClaw Gateway 可达性检查
- ✅ 健康检查 API
- ✅ 消息发送 API
- ✅ 带上下文的消息发送
- ✅ 全局客户端单例模式
- ✅ 端到端流程验证

---

## API 端点验证

### 1. 健康检查 API

```bash
# 无需认证
curl http://localhost:8000/api/v1/openclaw/health
```

预期响应：

```json
{
  "status": "healthy",
  "version": "2026.2.6-3",
  "uptime": 3600,
  "gateway_url": "http://localhost:19001"
}
```

### 2. 消息发送 API

```bash
# 需要认证
curl -X POST http://localhost:8000/api/v1/openclaw/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "message": "测试消息",
    "agent_id": "default",
    "context": {"test": true}
  }'
```

预期响应：

```json
{
  "response": "Agent 响应内容",
  "agent_id": "default",
  "execution_time": 1.5,
  "steps": []
}
```

---

## 前端验证

### 1. OpenClaw 状态指示器

位置: 右上角用户头像左侧

**状态说明**:
- 🟢 **已连接** (healthy): OpenClaw Gateway 正常运行
- 🔴 **不可用** (unhealthy): OpenClaw Gateway 无法连接
- 🟡 **连接中** (unknown): 正在检查连接状态

### 2. 状态详情弹窗

点击状态指示器，查看详细信息：
- 状态
- 版本号
- 运行时间
- Gateway URL
- 最后检查时间
- 错误信息（如果有）

### 3. 手动重连

如果状态为"不可用"，可以点击"重新连接"按钮手动触发重连。

### 4. 自动降级

当 OpenClaw 不可用时：
- 前端自动切换到"知识库模式"
- 显示通知: "OpenClaw 暂时不可用，已切换到知识库模式"
- 自动重试 3 次（每次间隔 5 秒）
- 重试失败后，每 5 分钟尝试恢复一次

---

## 故障排查

### 问题 1: OpenClaw Gateway 连接失败

**症状**: 前端显示红色状态，后端日志显示连接错误

**排查步骤**:

1. 检查 OpenClaw Gateway 是否运行：
   ```bash
   curl http://localhost:19001/health
   ```

2. 检查网络配置：
   - WSL2: 确保 Windows 可以访问 WSL 的 localhost
   - Docker: 使用 `host.docker.internal` 而非 `localhost`

3. 检查防火墙设置：
   ```bash
   # Windows 防火墙可能阻止 WSL 端口
   # 添加防火墙规则允许 19001 端口
   ```

4. 检查环境变量：
   ```bash
   # 后端
   echo $OPENCLAW_GATEWAY_URL

   # Docker
   docker-compose exec backend env | grep OPENCLAW
   ```

### 问题 2: 请求超时

**症状**: 后端日志显示 `OpenClawTimeoutError`

**解决方案**:

1. 增加超时时间：
   ```bash
   # .env
   OPENCLAW_TIMEOUT=60.0
   ```

2. 检查 OpenClaw Gateway 性能：
   ```bash
   # 查看 Gateway 日志
   tail -f /path/to/openclaw/logs/gateway.log
   ```

### 问题 3: 前端状态一直显示"连接中"

**症状**: 黄色状态，无法变为绿色或红色

**排查步骤**:

1. 打开浏览器开发者工具，查看 Console 错误

2. 检查 Network 标签，查看 `/api/v1/openclaw/health` 请求状态

3. 检查后端日志：
   ```bash
   # 本地开发
   tail -f backend/logs/app.log

   # Docker
   docker-compose logs -f backend
   ```

### 问题 4: 集成测试失败

**症状**: `pytest tests/integration/test_openclaw_integration.py` 失败

**解决方案**:

1. 确保 OpenClaw Gateway 运行：
   ```bash
   curl http://localhost:19001/health
   ```

2. 设置正确的环境变量：
   ```bash
   export OPENCLAW_GATEWAY_URL=http://localhost:19001
   ```

3. 跳过集成测试（如果 Gateway 不可用）：
   ```bash
   pytest -m "not integration"
   ```

### 问题 5: Docker 容器无法访问 WSL 服务

**症状**: Docker 容器中的后端无法连接到 WSL 的 OpenClaw Gateway

**解决方案**:

1. 使用 `host.docker.internal`:
   ```bash
   OPENCLAW_GATEWAY_URL=http://host.docker.internal:19001
   ```

2. 如果不工作，使用 WSL IP 地址：
   ```bash
   # 在 WSL 中获取 IP
   ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1

   # 使用该 IP
   OPENCLAW_GATEWAY_URL=http://172.x.x.x:19001
   ```

---

## 监控和日志

### 1. 后端日志

**本地开发**:
```bash
tail -f backend/logs/app.log
```

**Docker**:
```bash
docker-compose logs -f backend
```

**关键日志**:
- `OpenClawClient 初始化`: 客户端启动
- `OpenClaw 健康检查成功/失败`: 健康检查结果
- `发送消息到 OpenClaw`: 消息发送
- `OpenClaw 响应成功`: 响应接收

### 2. 前端日志

打开浏览器开发者工具 (F12)，查看 Console 标签：

- `健康检查失败`: 连接问题
- `OpenClaw 暂时不可用`: 降级通知
- `OpenClaw 已恢复`: 恢复通知

### 3. OpenClaw Gateway 日志

```bash
# 在 WSL Ubuntu 中
tail -f /path/to/openclaw/logs/gateway.log
```

---

## 性能优化

### 1. 连接池配置

OpenClaw 客户端使用 httpx 连接池：

```python
# app/core/openclaw_client.py
limits=httpx.Limits(
    max_keepalive_connections=10,  # 保持活动连接数
    max_connections=20              # 最大连接数
)
```

### 2. 超时配置

根据实际情况调整超时时间：

```bash
# 快速响应场景
OPENCLAW_TIMEOUT=10.0

# 复杂查询场景
OPENCLAW_TIMEOUT=60.0
```

### 3. 健康检查间隔

前端健康检查默认 30 秒，可在前端配置：

```typescript
// frontend/src/stores/openclaw.ts
const DEFAULT_CONFIG = {
  healthCheckInterval: 30  // 秒
}
```

---

## 安全注意事项

### 1. 认证

- `/api/v1/openclaw/health` 端点无需认证（公开）
- `/api/v1/openclaw/message` 端点需要 JWT 认证

### 2. 输入验证

- 消息长度限制: 1-10000 字符
- 使用 Pydantic 模型验证所有输入

### 3. 错误处理

- 不在日志中记录完整消息内容
- 不在响应中暴露内部错误详情

---

## 回滚方案

如果 Phase1 集成出现问题，可以快速回滚：

### 1. 禁用 OpenClaw

```bash
# .env
OPENCLAW_ENABLED=False
```

### 2. 前端降级

前端会自动检测 OpenClaw 不可用并切换到知识库模式，无需手动操作。

### 3. 代码回滚

```bash
git revert <commit-hash>
```

---

## 下一步

Phase1 部署完成后，进入 Phase2：知识库工具集成

- 文档检索工具
- 向量搜索工具
- 知识库管理工具

---

## 附录

### A. 环境变量完整列表

```bash
# OpenClaw Configuration
OPENCLAW_GATEWAY_URL=http://localhost:19001
OPENCLAW_TIMEOUT=30.0
OPENCLAW_MAX_RETRIES=3
OPENCLAW_ENABLED=True
```

### B. API 端点列表

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/v1/openclaw/health` | GET | 否 | 健康检查 |
| `/api/v1/openclaw/message` | POST | 是 | 发送消息 |

### C. 相关文档

- [Phase1 技术设计文档](./Phase1-技术设计文档.md)
- [Phase1 代码审查报告](./Phase1-代码审查报告.md)
- [Phase1 用户故事与验收测试](./Phase1-用户故事与验收测试.md)

---

**文档版本**: v1.0
**最后更新**: 2026-03-03
**维护人**: DevOps Team
