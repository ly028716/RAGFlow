#!/bin/bash
# 部署脚本 - 开发环境

set -e

echo "=========================================="
echo "AI智能助手系统 - 开发环境部署"
echo "=========================================="

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 检查.env文件
if [ ! -f .env ]; then
    echo "警告: .env文件不存在，从.env.example复制..."
    cp .env.example .env
    echo "请编辑.env文件配置必要的环境变量（特别是DASHSCOPE_API_KEY和SECRET_KEY）"
    exit 1
fi

# 停止现有容器
echo ""
echo "停止现有容器..."
docker-compose down

# 构建镜像
echo ""
echo "构建Docker镜像..."
docker-compose build --no-cache

# 启动服务
echo ""
echo "启动服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "检查服务状态..."
docker-compose ps

# 运行数据库迁移
echo ""
echo "运行数据库迁移..."
docker-compose exec -T backend alembic upgrade head

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "服务访问地址:"
echo "  - 前端: http://localhost:5173"
echo "  - 后端API: http://localhost:8000"
echo "  - API文档: http://localhost:8000/docs"
echo "  - 监控指标: http://localhost:9090/metrics"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo ""
