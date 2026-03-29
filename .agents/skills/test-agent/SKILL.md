---
name: test-agent
description: 软件测试工程师。测试用例设计、单元测试编写、集成测试、API测试、性能测试时使用。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# 测试/验证 Skill

为 RAGAgentLangChain 项目提供完整的测试支持，包括单元测试、集成测试、API测试、前端测试等。

## 核心职责

- 测试用例设计和编写
- 单元测试开发（后端 pytest、前端 Vitest）
- API 接口测试
- 前端组件测试
- 集成测试
- 测试数据管理和 Mock
- 测试覆盖率分析
- 性能测试和压力测试
- 测试自动化和 CI/CD 集成

## 技术栈

### 后端测试
- **测试框架**: pytest 7.4+
- **Mock**: unittest.mock, pytest-mock
- **异步测试**: pytest-asyncio
- **HTTP测试**: httpx, TestClient (FastAPI)
- **数据库测试**: SQLAlchemy fixtures
- **覆盖率**: pytest-cov

### 前端测试
- **测试框架**: Vitest 4.0+
- **组件测试**: @vue/test-utils 2.4+
- **DOM环境**: jsdom, happy-dom
- **Mock**: vitest mock, axios-mock-adapter
- **Store测试**: @pinia/testing
- **覆盖率**: vitest coverage

## 测试架构

```
RAGAgentLangChain/
├── backend/
│   ├── tests/                          # 后端测试目录
│   │   ├── __init__.py
│   │   ├── conftest.py                 # pytest配置和fixtures
│   │   ├── test_auth_api.py            # 认证API测试
│   │   ├── test_conversation_api.py    # 对话API测试
│   │   ├── test_knowledge_api.py       # 知识库API测试
│   │   ├── test_agent_service.py       # Agent服务测试
│   │   └── test_rag_chain.py           # RAG链测试
│   └── pytest.ini                      # pytest配置文件
└── frontend/
    └── src/
        └── __tests__/                  # 前端测试目录
            ├── setup.ts                # 测试环境配置
            ├── components/             # 组件测试
            │   ├── ChatInput.test.ts
            │   └── MarkdownRenderer.test.ts
            ├── stores/                 # Store测试
            │   ├── auth.test.ts
            │   └── conversation.test.ts
            ├── composables/            # Composable测试
            │   └── useChat.test.ts
            ├── api/                    # API测试
            │   └── index.test.ts
            └── utils/                  # 工具函数测试
                └── storage.test.ts
```

## 后端测试（pytest）

### 1. 测试环境配置

创建 `backend/tests/conftest.py`：

```python
"""
pytest配置和全局fixtures
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.core.security import get_password_hash


# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def engine():
    """创建测试数据库引擎"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """创建数据库会话"""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """获取认证头"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### 2. API 测试示例

创建 `backend/tests/test_auth_api.py`：

```python
"""
认证API测试
"""
import pytest
from fastapi import status


class TestAuthAPI:
    """认证API测试类"""

    def test_register_success(self, client):
        """测试用户注册成功"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "id" in data

    def test_register_duplicate_username(self, client, test_user):
        """测试重复用户名注册失败"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "another@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "已存在" in response.json()["detail"]

    def test_login_success(self, client, test_user):
        """测试登录成功"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpass123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """测试错误密码登录失败"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, client, auth_headers):
        """测试获取当前用户信息"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
```

### 3. Service 层测试

创建 `backend/tests/test_conversation_service.py`：

```python
"""
对话服务测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.conversation_service import ConversationService
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import ConversationCreate


@pytest.fixture
def mock_repository():
    """Mock Repository"""
    return Mock(spec=ConversationRepository)


@pytest.fixture
def conversation_service(mock_repository):
    """创建ConversationService实例"""
    return ConversationService(mock_repository)


class TestConversationService:
    """对话服务测试类"""

    async def test_create_conversation(self, conversation_service, mock_repository):
        """测试创建对话"""
        # 准备测试数据
        user_id = 1
        data = ConversationCreate(title="测试对话")

        # Mock repository返回值
        mock_conversation = Mock()
        mock_conversation.id = 1
        mock_conversation.title = "测试对话"
        mock_conversation.user_id = user_id
        mock_repository.create.return_value = mock_conversation

        # 执行测试
        result = await conversation_service.create_conversation(user_id, data)

        # 验证结果
        assert result.id == 1
        assert result.title == "测试对话"
        mock_repository.create.assert_called_once()

    async def test_get_conversation_not_found(self, conversation_service, mock_repository):
        """测试获取不存在的对话"""
        # Mock repository返回None
        mock_repository.get_by_id.return_value = None

        # 执行测试并验证异常
        with pytest.raises(Exception) as exc_info:
            await conversation_service.get_conversation(999, 1)

        assert "不存在" in str(exc_info.value)
```

### 4. Mock LLM 调用

创建 `backend/tests/test_llm_mock.py`：

```python
"""
LLM调用Mock测试
"""
import pytest
from unittest.mock import patch, AsyncMock


class TestLLMMock:
    """LLM Mock测试"""

    @patch('app.core.llm.get_llm_client')
    async def test_chat_with_mock_llm(self, mock_get_llm):
        """测试使用Mock LLM进行对话"""
        # Mock LLM响应
        mock_llm = AsyncMock()
        mock_llm.agenerate.return_value = Mock(
            generations=[[Mock(text="这是模拟的AI响应")]]
        )
        mock_get_llm.return_value = mock_llm

        # 执行测试
        from app.services.conversation_service import ConversationService
        service = ConversationService(Mock())

        # 验证Mock被调用
        mock_llm.agenerate.assert_called()
```

## 前端测试（Vitest）

### 1. 测试环境配置

创建 `frontend/src/__tests__/setup.ts`：

```typescript
import { config } from '@vue/test-utils'
import { vi } from 'vitest'

// 全局Mock
global.localStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn()
}

// Vue Test Utils全局配置
config.global.mocks = {
  $t: (key: string) => key
}
```

### 2. 组件测试示例

创建 `frontend/src/__tests__/components/ChatInput.test.ts`：

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatInput from '@/components/chat/ChatInput.vue'

describe('ChatInput Component', () => {
  let wrapper: any

  beforeEach(() => {
    wrapper = mount(ChatInput, {
      props: {
        disabled: false
      }
    })
  })

  it('应该正确渲染', () => {
    expect(wrapper.find('textarea').exists()).toBe(true)
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('应该在输入时更新内容', async () => {
    const textarea = wrapper.find('textarea')
    await textarea.setValue('测试消息')

    expect(wrapper.vm.message).toBe('测试消息')
  })

  it('应该在点击发送按钮时触发事件', async () => {
    const textarea = wrapper.find('textarea')
    await textarea.setValue('测试消息')

    const button = wrapper.find('button')
    await button.trigger('click')

    expect(wrapper.emitted('send')).toBeTruthy()
    expect(wrapper.emitted('send')[0]).toEqual(['测试消息'])
  })

  it('禁用状态下不应该发送消息', async () => {
    await wrapper.setProps({ disabled: true })

    const button = wrapper.find('button')
    expect(button.attributes('disabled')).toBeDefined()
  })
})
```

### 3. Store 测试示例

创建 `frontend/src/__tests__/stores/conversation.test.ts`：

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useConversationStore } from '@/stores/conversation'

describe('Conversation Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('应该正确初始化状态', () => {
    const store = useConversationStore()

    expect(store.conversations).toEqual([])
    expect(store.currentConversation).toBeNull()
    expect(store.messages).toEqual([])
  })

  it('应该添加消息到列表', () => {
    const store = useConversationStore()

    store.addMessage({
      id: 1,
      role: 'user',
      content: '测试消息',
      created_at: new Date().toISOString()
    })

    expect(store.messages).toHaveLength(1)
    expect(store.messages[0].content).toBe('测试消息')
  })

  it('应该设置当前对话', () => {
    const store = useConversationStore()

    const conversation = {
      id: 1,
      title: '测试对话',
      created_at: new Date().toISOString()
    }

    store.setCurrentConversation(conversation)

    expect(store.currentConversation).toEqual(conversation)
  })
})
```

### 4. Composable 测试示例

已在前面的 `useChat.test.ts` 中展示。

### 5. API Mock 测试

创建 `frontend/src/__tests__/api/index.test.ts`：

```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import MockAdapter from 'axios-mock-adapter'
import { api } from '@/api'
import { login, register } from '@/api/auth'

describe('API Tests', () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(api)
  })

  afterEach(() => {
    mock.restore()
  })

  describe('Auth API', () => {
    it('应该成功登录', async () => {
      const mockResponse = {
        access_token: 'test-token',
        token_type: 'bearer'
      }

      mock.onPost('/auth/login').reply(200, mockResponse)

      const result = await login('testuser', 'password123')

      expect(result.access_token).toBe('test-token')
    })

    it('应该处理登录错误', async () => {
      mock.onPost('/auth/login').reply(401, {
        detail: '用户名或密码错误'
      })

      await expect(login('testuser', 'wrongpass')).rejects.toThrow()
    })
  })
})
```

## 测试覆盖率

### 1. 后端测试覆盖率

配置 `backend/pytest.ini`：

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

运行覆盖率测试：

```bash
# 运行测试并生成覆盖率报告
cd backend
pytest --cov=app --cov-report=html --cov-report=term

# 查看HTML报告
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### 2. 前端测试覆盖率

配置 `frontend/vitest.config.ts`：

```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/__tests__/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData'
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80
      }
    }
  }
})
```

运行覆盖率测试：

```bash
# 运行测试并生成覆盖率报告
cd frontend
npm run test:coverage

# 查看HTML报告
open coverage/index.html  # macOS
start coverage/index.html  # Windows
```

## 测试数据管理

### 1. 后端测试数据

创建 `backend/tests/fixtures/test_data.py`：

```python
"""
测试数据Fixtures
"""
import pytest
from datetime import datetime

@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }

@pytest.fixture
def sample_conversation_data():
    """示例对话数据"""
    return {
        "title": "测试对话",
        "created_at": datetime.utcnow()
    }

@pytest.fixture
def sample_message_data():
    """示例消息数据"""
    return {
        "role": "user",
        "content": "这是一条测试消息",
        "tokens": 10
    }
```

### 2. 前端测试数据

创建 `frontend/src/__tests__/fixtures/mockData.ts`：

```typescript
export const mockUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  created_at: '2026-01-01T00:00:00Z'
}

export const mockConversation = {
  id: 1,
  title: '测试对话',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z'
}

export const mockMessages = [
  {
    id: 1,
    role: 'user',
    content: '你好',
    created_at: '2026-01-01T00:00:00Z'
  },
  {
    id: 2,
    role: 'assistant',
    content: '你好！有什么可以帮助你的吗？',
    created_at: '2026-01-01T00:00:01Z'
  }
]
```

## CI/CD 集成

### GitHub Actions 配置

创建 `.github/workflows/test.yml`：

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: testpass
          MYSQL_DATABASE: test_db
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

      redis:
        image: redis:7.0-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd="redis-cli ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio

    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'

    - name: Install dependencies
      run: |
        cd frontend
        npm ci

    - name: Run tests
      run: |
        cd frontend
        npm run test:coverage

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./frontend/coverage/lcov.info
```

## 常用命令

### 后端测试命令

```bash
# 运行所有测试
cd backend
pytest

# 运行特定测试文件
pytest tests/test_auth_api.py

# 运行特定测试类
pytest tests/test_auth_api.py::TestAuthAPI

# 运行特定测试方法
pytest tests/test_auth_api.py::TestAuthAPI::test_login_success

# 运行测试并显示详细输出
pytest -v

# 运行测试并显示print输出
pytest -s

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行测试并在第一个失败时停止
pytest -x

# 运行失败的测试
pytest --lf

# 并行运行测试（需要pytest-xdist）
pytest -n auto
```

### 前端测试命令

```bash
# 运行所有测试
cd frontend
npm run test

# 运行测试并监听变化
npm run test:watch

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行特定测试文件
npm run test -- src/__tests__/components/ChatInput.test.ts

# 运行测试并显示详细输出
npm run test -- --reporter=verbose

# 运行测试UI（交互式）
npx vitest --ui
```

## 注意事项

### 1. 测试隔离

- 每个测试应该独立运行，不依赖其他测试
- 使用 `beforeEach` 和 `afterEach` 清理测试环境
- 避免共享可变状态

### 2. Mock 使用

- 对外部依赖（API、数据库、LLM）进行 Mock
- 使用真实的测试数据库进行集成测试
- Mock 应该尽可能接近真实行为

### 3. 测试命名

- 使用描述性的测试名称
- 遵循 "应该...当..." 的命名模式
- 中文测试名称更易读

### 4. 测试覆盖率

- 目标覆盖率：80%以上
- 重点测试核心业务逻辑
- 不要为了覆盖率而写无意义的测试

### 5. 异步测试

- 后端使用 `pytest-asyncio` 处理异步函数
- 前端使用 `async/await` 处理异步操作
- 确保所有异步操作都被正确等待

### 6. 测试数据

- 使用 Fixture 管理测试数据
- 避免硬编码测试数据
- 测试数据应该有代表性

### 7. 性能测试

- 关键接口应该有性能测试
- 使用 `pytest-benchmark` 或 `locust` 进行性能测试
- 设置合理的性能基准

## 协作接口

### 输入来源

- **后端开发 Skill**: API实现、Service层代码
- **前端开发 Skill**: 组件实现、Store实现
- **产品 Skill**: 测试用例需求、验收标准

### 输出交付

- **给后端开发 Skill**: 测试失败报告、Bug修复建议
- **给前端开发 Skill**: 测试失败报告、Bug修复建议
- **给运维 Skill**: 测试通过确认、部署就绪信号
- **给产品 Skill**: 测试报告、覆盖率报告

## 测试最佳实践

1. **TDD（测试驱动开发）**: 先写测试，再写实现
2. **AAA模式**: Arrange（准备）、Act（执行）、Assert（断言）
3. **单一职责**: 每个测试只测试一个功能点
4. **快速反馈**: 测试应该快速运行，提供即时反馈
5. **可维护性**: 测试代码也需要重构和维护
6. **文档作用**: 测试是最好的文档，展示如何使用代码
```
