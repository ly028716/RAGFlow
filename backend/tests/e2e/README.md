# E2E端到端测试

本目录包含RAGFlow系统的端到端测试，用于验证完整的用户场景和系统集成。

## 测试文件

### 1. test_complete_workflow.py
完整的用户工作流测试，覆盖：
- 用户注册和登录
- 知识库创建
- Web Scraper任务创建和执行
- 知识库查询
- 对话交互
- 资源清理

**测试场景**: 10个测试用例，验证端到端的完整流程

### 2. test_web_scraper_e2e.py
Web Scraper功能的专项E2E测试，覆盖：
- 任务CRUD操作（创建、读取、更新、删除）
- 一次性任务和定时任务创建
- 任务启动和停止
- 任务日志查询和筛选
- 任务列表筛选（按状态、调度类型）
- 分页功能
- 批量任务创建

**测试场景**: 14个测试用例，专注于Web Scraper功能

## 前置条件

### 1. 环境要求
- Python 3.9+
- Docker 和 Docker Compose
- 网络连接（用于安装依赖和访问API）

### 2. 依赖安装
```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. 环境配置
创建 `.env` 文件并配置必要的环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

必需的环境变量：
- `DASHSCOPE_API_KEY`: 通义千问API密钥
- `SECRET_KEY`: JWT密钥（至少32字符）
- `DATABASE_URL`: MySQL连接字符串
- `REDIS_URL`: Redis连接字符串

## 运行E2E测试

### 方法1: 使用Docker Compose（推荐）

1. **启动所有服务**
```bash
cd backend
docker-compose up -d
```

2. **等待服务就绪**
```bash
# 检查服务健康状态
docker-compose ps

# 查看后端日志
docker-compose logs -f backend
```

3. **运行数据库迁移**
```bash
docker-compose exec backend alembic upgrade head
```

4. **运行E2E测试**
```bash
# 运行所有E2E测试
pytest tests/e2e/ -v

# 运行特定测试文件
pytest tests/e2e/test_web_scraper_e2e.py -v

# 运行特定测试用例
pytest tests/e2e/test_web_scraper_e2e.py::TestWebScraperE2E::test_01_create_once_task -v
```

5. **停止服务**
```bash
docker-compose down
```

### 方法2: 本地开发环境

1. **启动MySQL和Redis**
```bash
cd backend
docker-compose up -d mysql redis
```

2. **运行数据库迁移**
```bash
alembic upgrade head
```

3. **启动后端服务**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **在另一个终端运行E2E测试**
```bash
pytest tests/e2e/ -v
```

## 测试配置

### 修改测试基础URL
如果后端服务运行在不同的地址，可以修改测试文件中的 `BASE_URL`：

```python
# tests/e2e/test_web_scraper_e2e.py
class TestWebScraperE2E:
    BASE_URL = "http://localhost:8000/api/v1"  # 修改为实际地址
```

### 测试超时设置
某些测试可能需要等待任务执行完成，可以调整等待时间：

```python
# 在测试中调整等待时间
time.sleep(5)  # 等待5秒
```

## 测试报告

### 生成HTML测试报告
```bash
pytest tests/e2e/ -v --html=report.html --self-contained-html
```

### 生成覆盖率报告
```bash
pytest tests/e2e/ --cov=app --cov-report=html
```

## 常见问题

### 1. 连接被拒绝 (Connection refused)
**问题**: `requests.exceptions.ConnectionError: Connection refused`

**解决方案**:
- 确保后端服务正在运行
- 检查服务地址和端口是否正确
- 验证防火墙设置

### 2. 认证失败
**问题**: `401 Unauthorized`

**解决方案**:
- 检查用户注册和登录流程
- 验证JWT token是否正确设置
- 确保 `SECRET_KEY` 配置正确

### 3. 数据库错误
**问题**: `sqlalchemy.exc.OperationalError`

**解决方案**:
- 确保MySQL服务正在运行
- 运行数据库迁移: `alembic upgrade head`
- 检查数据库连接字符串

### 4. 任务执行失败
**问题**: Web Scraper任务执行失败

**解决方案**:
- 检查Playwright浏览器是否已安装
- 验证目标URL是否可访问
- 查看任务日志获取详细错误信息

### 5. 测试数据清理
**问题**: 测试数据未被清理

**解决方案**:
- 测试使用 `yield` fixture自动清理
- 如果清理失败，手动删除测试数据
- 重置数据库: `alembic downgrade base && alembic upgrade head`

## 最佳实践

1. **测试隔离**: 每个测试应该独立运行，不依赖其他测试的状态
2. **数据清理**: 使用fixture的teardown确保测试数据被清理
3. **等待策略**: 使用适当的等待时间，避免测试不稳定
4. **错误处理**: 测试应该验证错误场景和边界条件
5. **测试命名**: 使用描述性的测试名称，清楚表达测试意图

## 持续集成

### GitHub Actions示例
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: rootpassword
          MYSQL_DATABASE: ragflow
        ports:
          - 3306:3306

      redis:
        image: redis:7.0-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run migrations
        run: |
          cd backend
          alembic upgrade head

      - name: Start backend
        run: |
          cd backend
          uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 10

      - name: Run E2E tests
        run: |
          cd backend
          pytest tests/e2e/ -v
```

## 贡献指南

添加新的E2E测试时，请遵循以下规范：

1. **测试文件命名**: `test_<feature>_e2e.py`
2. **测试类命名**: `Test<Feature>E2E`
3. **测试方法命名**: `test_<number>_<description>`（按执行顺序编号）
4. **使用fixture**: 共享测试设置和清理逻辑
5. **添加文档**: 在测试类和方法中添加清晰的文档字符串
6. **验证响应**: 检查HTTP状态码和响应数据结构
7. **清理资源**: 确保测试后清理所有创建的资源

## 参考资料

- [Pytest文档](https://docs.pytest.org/)
- [Requests文档](https://requests.readthedocs.io/)
- [FastAPI测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [Docker Compose文档](https://docs.docker.com/compose/)
