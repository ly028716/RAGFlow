---
name: devops
description: DevOps工程师。Docker部署、CI/CD配置、服务器运维、监控告警、日志管理时使用。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# DevOps 运维 Skill

为 RAGAgentLangChain 项目提供完整的运维支持，包括部署、监控、日志管理、备份恢复等。

## 核心职责

- Docker 容器化部署和管理
- 服务健康检查和监控
- 日志收集、分析和管理
- 数据库备份和恢复
- 环境配置管理
- 性能监控和优化
- 故障排查和应急响应
- 安全加固和漏洞修复
- CI/CD 流程配置

## 技术栈

- **容器化**: Docker 24+, Docker Compose 2.0+
- **数据库**: MySQL 8.0, Redis 7.0
- **向量数据库**: Chroma
- **Web服务器**: Uvicorn (ASGI)
- **监控**: Prometheus, 自定义健康检查
- **日志**: Python logging, 文件轮转
- **备份**: mysqldump, 定期备份脚本
- **操作系统**: Linux (生产), Windows (开发)

## 项目架构

```
RAGAgentLangChain/
├── backend/                    # 后端服务
│   ├── Dockerfile             # 后端镜像构建
│   ├── docker-compose.yml     # 服务编排
│   ├── .env.example           # 环境变量模板
│   ├── scripts/               # 运维脚本
│   │   ├── start.sh          # 生产启动脚本
│   │   ├── start-dev.sh      # 开发启动脚本
│   │   └── deploy.sh         # 部署管理脚本
│   ├── logs/                  # 日志目录
│   ├── uploads/               # 文件上传目录
│   └── vector_db/             # 向量数据库持久化
├── frontend/                   # 前端服务
└── .env                       # 环境变量配置
```

## Docker 部署管理

### 1. 服务架构

项目使用 Docker Compose 编排三个核心服务：

```yaml
services:
  mysql:      # MySQL 8.0 数据库
  redis:      # Redis 7.0 缓存
  backend:    # FastAPI 后端应用
```

### 2. 环境配置

#### 创建环境变量文件

```bash
# 复制环境变量模板
cd backend
cp .env.example .env

# 编辑环境变量（必须配置）
nano .env
```

#### 关键环境变量

**数据库配置**：
```bash
MYSQL_ROOT_PASSWORD=your-secure-root-password
MYSQL_DATABASE=ai_assistant
MYSQL_USER=ai_user
MYSQL_PASSWORD=your-secure-password
```

**安全配置**：
```bash
SECRET_KEY=your-secret-key-change-in-production-min-32-chars
BCRYPT_ROUNDS=12
```

**API密钥**：
```bash
DASHSCOPE_API_KEY=your-dashscope-api-key
```

**环境标识**：
```bash
ENVIRONMENT=production
DEBUG=False
```

### 3. 部署脚本使用

项目提供了完整的部署管理脚本 `scripts/deploy.sh`：

```bash
# 查看帮助
./scripts/deploy.sh help

# 初始化数据库
./scripts/deploy.sh init

# 启动所有服务
./scripts/deploy.sh start

# 停止所有服务
./scripts/deploy.sh stop

# 重启服务
./scripts/deploy.sh restart

# 查看日志
./scripts/deploy.sh logs

# 构建镜像
./scripts/deploy.sh build

# 备份数据库
./scripts/deploy.sh backup

# 清理容器和数据（危险操作）
./scripts/deploy.sh clean
```

### 4. 手动部署流程

#### 首次部署

```bash
cd backend

# 1. 检查环境变量
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

# 2. 构建镜像
docker-compose build

# 3. 启动数据库服务
docker-compose up -d mysql redis

# 4. 等待数据库就绪
sleep 30

# 5. 运行数据库迁移
docker-compose run --rm backend alembic upgrade head

# 6. 启动后端服务
docker-compose up -d backend

# 7. 检查服务状态
docker-compose ps
```

#### 更新部署

```bash
cd backend

# 1. 拉取最新代码
git pull origin main

# 2. 停止后端服务
docker-compose stop backend

# 3. 重新构建镜像
docker-compose build backend

# 4. 运行数据库迁移
docker-compose run --rm backend alembic upgrade head

# 5. 启动后端服务
docker-compose up -d backend

# 6. 检查服务状态
docker-compose logs -f backend
```

### 5. 容器管理

#### 查看容器状态

```bash
# 查看所有容器
docker-compose ps

# 查看容器详细信息
docker-compose ps -a

# 查看容器资源使用
docker stats ai_assistant_backend ai_assistant_mysql ai_assistant_redis
```

#### 容器操作

```bash
# 进入容器
docker-compose exec backend bash
docker-compose exec mysql bash
docker-compose exec redis redis-cli

# 重启单个服务
docker-compose restart backend

# 查看容器日志
docker-compose logs backend
docker-compose logs -f backend --tail=100

# 停止并删除容器
docker-compose down

# 停止并删除容器和数据卷（危险）
docker-compose down -v
```

## 服务监控和健康检查

### 1. 健康检查端点

后端服务提供健康检查端点：

```bash
# 基础健康检查
curl http://localhost:8000/api/v1/system/health

# 响应示例
{
  "status": "healthy",
  "timestamp": "2026-01-23T13:42:10+08:00",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "vector_store": "healthy"
  }
}
```

### 2. Docker 健康检查

所有服务都配置了 Docker 健康检查：

**MySQL 健康检查**：
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

**Redis 健康检查**：
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Backend 健康检查**：
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/system/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 3. 监控脚本

创建监控脚本 `scripts/monitor.sh`：

```bash
#!/bin/bash
# 服务监控脚本

check_service() {
    local service=$1
    local url=$2

    if curl -f -s "$url" > /dev/null; then
        echo "✓ $service is healthy"
        return 0
    else
        echo "✗ $service is unhealthy"
        return 1
    fi
}

echo "=========================================="
echo "Service Health Check"
echo "=========================================="

# 检查后端服务
check_service "Backend API" "http://localhost:8000/api/v1/system/health"

# 检查 Prometheus 指标
check_service "Metrics" "http://localhost:9090/metrics"

# 检查容器状态
echo ""
echo "Container Status:"
docker-compose ps

# 检查资源使用
echo ""
echo "Resource Usage:"
docker stats --no-stream ai_assistant_backend ai_assistant_mysql ai_assistant_redis
```

### 4. Prometheus 监控

后端服务暴露 Prometheus 指标：

```bash
# 访问指标端点
curl http://localhost:9090/metrics

# 常见指标
# - http_requests_total: HTTP 请求总数
# - http_request_duration_seconds: 请求耗时
# - llm_api_calls_total: LLM API 调用次数
# - vector_store_operations_total: 向量数据库操作次数
```

## 日志管理

### 1. 日志架构

```
logs/
├── app.log              # 应用主日志
├── app.log.1            # 轮转日志
├── app.log.2
└── ...
```

### 2. 日志配置

日志配置在 `.env` 文件中：

```bash
LOG_LEVEL=INFO                    # 日志级别: DEBUG, INFO, WARNING, ERROR
LOG_FILE=/app/logs/app.log        # 日志文件路径
LOG_MAX_BYTES=10485760            # 单个日志文件最大大小 (10MB)
LOG_BACKUP_COUNT=10               # 保留的日志文件数量
```

### 3. 查看日志

```bash
# 查看实时日志
docker-compose logs -f backend

# 查看最近100行日志
docker-compose logs --tail=100 backend

# 查看特定时间段的日志
docker-compose logs --since="2026-01-23T10:00:00" backend

# 查看所有服务日志
docker-compose logs -f

# 查看应用日志文件
tail -f backend/logs/app.log

# 搜索错误日志
grep "ERROR" backend/logs/app.log

# 搜索特定用户的操作日志
grep "user_id=123" backend/logs/app.log
```

### 4. 日志分析

```bash
# 统计错误数量
grep "ERROR" backend/logs/app.log | wc -l

# 统计各级别日志数量
for level in DEBUG INFO WARNING ERROR; do
    count=$(grep "$level" backend/logs/app.log | wc -l)
    echo "$level: $count"
done

# 查找最频繁的错误
grep "ERROR" backend/logs/app.log | sort | uniq -c | sort -rn | head -10

# 分析API响应时间
grep "request_duration" backend/logs/app.log | awk '{print $NF}' | sort -n
```

### 5. 日志轮转

日志自动轮转配置在应用中，也可以使用 logrotate：

创建 `/etc/logrotate.d/ai-assistant`：

```
/path/to/backend/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        docker-compose restart backend > /dev/null 2>&1 || true
    endscript
}
```

## 数据库备份和恢复

### 1. 自动备份脚本

创建 `scripts/backup.sh`：

```bash
#!/bin/bash
# 数据库备份脚本

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "Starting database backup..."

# 备份数据库
docker-compose exec -T mysql mysqldump \
    -u root \
    -p${MYSQL_ROOT_PASSWORD:-rootpassword} \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    ai_assistant > "$BACKUP_FILE"

# 压缩备份文件
gzip "$BACKUP_FILE"

echo "Backup completed: ${BACKUP_FILE}.gz"

# 删除30天前的备份
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete

echo "Old backups cleaned up"
```

### 2. 手动备份

```bash
# 备份数据库
docker-compose exec -T mysql mysqldump \
    -u root -p${MYSQL_ROOT_PASSWORD} \
    ai_assistant > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份并压缩
docker-compose exec -T mysql mysqldump \
    -u root -p${MYSQL_ROOT_PASSWORD} \
    ai_assistant | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 备份向量数据库
tar -czf vector_db_backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/vector_db/

# 备份上传文件
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/uploads/
```
