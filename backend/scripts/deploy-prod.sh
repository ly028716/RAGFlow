#!/bin/bash
# 部署脚本 - 生产环境

set -e

echo "=========================================="
echo "AI智能助手系统 - 生产环境部署"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 检查.env文件
if [ ! -f .env.prod ]; then
    echo "错误: .env.prod文件不存在"
    echo "请创建.env.prod文件并配置生产环境变量"
    exit 1
fi

# 确认部署
read -p "确认要部署到生产环境吗？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "部署已取消"
    exit 0
fi

# 备份数据
echo ""
echo "备份数据..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份数据库
docker-compose -f docker-compose.prod.yml exec -T mysql mysqldump \
    -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} \
    > "$BACKUP_DIR/database.sql" 2>/dev/null || echo "数据库备份失败（可能是首次部署）"

# 备份上传文件和向量数据库
if [ -d "uploads" ]; then
    cp -r uploads "$BACKUP_DIR/"
fi
if [ -d "vector_db" ]; then
    cp -r vector_db "$BACKUP_DIR/"
fi

echo "备份完成: $BACKUP_DIR"

# 拉取最新代码
echo ""
echo "拉取最新代码..."
git pull origin main

# 停止现有容器
echo ""
echo "停止现有容器..."
docker-compose -f docker-compose.prod.yml down

# 构建镜像
echo ""
echo "构建Docker镜像..."
docker-compose -f docker-compose.prod.yml build --no-cache

# 启动服务
echo ""
echo "启动服务..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo ""
echo "等待服务启动..."
sleep 15

# 检查服务状态
echo ""
echo "检查服务状态..."
docker-compose -f docker-compose.prod.yml ps

# 运行数据库迁移
echo ""
echo "运行数据库迁移..."
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# 健康检查
echo ""
echo "执行健康检查..."
sleep 5
if curl -f http://localhost/api/v1/system/health > /dev/null 2>&1; then
    echo "✓ 健康检查通过"
else
    echo "✗ 健康检查失败，请检查日志"
    docker-compose -f docker-compose.prod.yml logs --tail=50
    exit 1
fi

echo ""
echo "=========================================="
echo "生产环境部署完成！"
echo "=========================================="
echo ""
echo "服务访问地址:"
echo "  - 前端: http://localhost"
echo "  - 后端API: http://localhost/api/v1"
echo "  - API文档: http://localhost/api/v1/docs"
echo ""
echo "查看日志: docker-compose -f docker-compose.prod.yml logs -f"
echo "停止服务: docker-compose -f docker-compose.prod.yml down"
echo ""
