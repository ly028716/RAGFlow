# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAGFlow is a full-stack RAG (Retrieval-Augmented Generation) knowledge base system with Agent capabilities, built for enterprise-grade knowledge management and intelligent conversation.

**Stack:**
- Backend: FastAPI 0.104+ + LangChain 1.0 + Python 3.10+
- Frontend: Vue 3 + TypeScript + Vite + Element Plus
- Databases: MySQL 8.0 (relational), Redis 7.0 (cache), Chroma (vector)
- LLM: Alibaba Cloud Tongyi Qianwen (DashScope API)

## Common Commands

### Backend Development

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development

# Start development server (with hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
alembic upgrade head                    # Apply all migrations
alembic revision --autogenerate -m "description"  # Create new migration
alembic downgrade -1                    # Rollback one migration
alembic current                         # Show current version
alembic history                         # Show migration history

# Testing
pytest                                  # Run all tests
pytest tests/test_auth.py              # Run specific test file
pytest tests/test_auth.py::test_login  # Run specific test
pytest -v                              # Verbose output
pytest -s                              # Show print statements
pytest --cov=app --cov-report=html     # Generate coverage report

# Code quality
black app/                             # Format code
isort app/                             # Sort imports
flake8 app/ --max-line-length=100     # Lint code
mypy app/                              # Type checking

# Docker deployment
docker-compose up -d                   # Start all services
docker-compose down                    # Stop all services
docker-compose logs -f backend         # View backend logs
docker-compose exec backend alembic upgrade head  # Run migrations in container
```

### Frontend Development

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Testing
npm run test                           # Run tests once
npm run test:watch                     # Run tests in watch mode
npm run test:coverage                  # Generate coverage report
```

### Full Stack Development

```bash
# Start backend and databases with Docker
cd backend && docker-compose up -d

# In another terminal, start frontend
cd frontend && npm run dev

# Access:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

## Architecture Overview

### Backend: 4-Layer Architecture

The backend follows a strict layered architecture pattern:

```
API Layer (app/api/v1/)
  ↓ Handles HTTP requests, validation, routing
Service Layer (app/services/)
  ↓ Business logic, orchestration, transactions
Repository Layer (app/repositories/)
  ↓ Data access, database queries
Infrastructure Layer (app/core/)
  ↓ Database, Redis, Vector Store, LLM
```

**Key Principle:** Each layer only depends on the layer below it. Never skip layers.

### Critical Architectural Patterns

#### 1. Dependency Injection (app/dependencies.py)

Authentication is handled via FastAPI dependency injection:

```python
from app.dependencies import get_current_user, get_current_admin_user

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
```

Available dependencies:
- `get_current_user()`: Returns authenticated User object
- `get_current_user_id()`: Returns just the user ID (lighter)
- `get_current_admin_user()`: Validates admin role
- `get_optional_current_user()`: Optional auth for public endpoints

#### 2. Configuration Management (app/config.py)

Configuration uses Pydantic Settings with 14 specialized classes:
- `DatabaseSettings`, `RedisSettings`, `JWTSettings`, `SecuritySettings`
- `TongyiSettings`, `VectorDBSettings`, `FileStorageSettings`
- `DocumentProcessingSettings`, `RAGSettings`, `QuotaSettings`
- `RateLimitSettings`, `LoggingSettings`, `CORSSettings`
- `MonitoringSettings`, `BackgroundTaskSettings`, `WebSocketSettings`

Access via global `settings` object:
```python
from app.config import settings
db_url = settings.database.database_url
api_key = settings.tongyi.api_key
```

#### 3. Error Handling (app/middleware/error_handler.py)

Unified error codes:
- `1xxx`: Authentication errors (1001: invalid credentials, 1002: token expired)
- `2xxx`: Business logic errors (2001: resource not found, 2002: quota exceeded)
- `3xxx`: System errors (3001: database error, 3002: Redis error, 3003: LLM API error)
- `4xxx`: Permission errors (4001: insufficient permissions)
- `5xxx`: Validation errors (5001: invalid input)

Always raise exceptions with proper error codes for consistent API responses.

#### 4. LLM Integration (app/core/llm.py)

**IMPORTANT:** The system uses a patched Tongyi LLM class to fix streaming issues:

```python
from app.core.llm import get_llm, get_streaming_llm

# For non-streaming responses
llm = get_llm()

# For streaming responses (SSE)
streaming_llm = get_streaming_llm()
```

Never instantiate Tongyi directly - always use these factory functions.

#### 5. Streaming Responses (app/api/v1/chat.py)

Chat uses Server-Sent Events (SSE) for streaming:

```python
from fastapi.responses import StreamingResponse

async def stream_generator():
    async for chunk in llm.astream(prompt):
        yield f"data: {json.dumps({'content': chunk})}\n\n"

return StreamingResponse(stream_generator(), media_type="text/event-stream")
```

Frontend parses SSE in `frontend/src/utils/fetch-stream.ts`.

#### 6. RAG Pipeline (app/langchain_integration/rag_chain.py)

RAG flow:
1. Document upload → chunking (1000 tokens, 200 overlap)
2. Embedding via DashScope → store in Chroma
3. Query → retrieve top-K similar chunks (default K=5)
4. LLM generates answer with retrieved context

Configuration:
- `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`
- `RAG_TOP_K=5`, `RAG_SIMILARITY_THRESHOLD=0.7`

#### 7. Agent System (app/langchain_integration/agent_executor.py)

Uses ReAct (Reasoning + Acting) pattern with built-in tools:
- `calculator_tool.py`: Math calculations
- `search_tool.py`: Web search
- `weather_tool.py`: Weather queries
- `api_call_tool.py`: HTTP API calls (whitelist required)
- `data_analysis_tool.py`: Data analysis
- `file_operations_tool.py`: File operations

Agent execution is tracked in database for audit and debugging.

### Frontend: Composition API + Pinia

**State Management (src/stores/):**
- `auth.ts`: Authentication, tokens, user info
- `conversation.ts`: Chat history, messages
- `knowledge.ts`: Knowledge bases, documents
- `agent.ts`: Agent tools, executions
- `prompts.ts`: System prompts

**Key Composables (src/composables/):**
- `useChat.ts`: Chat logic, streaming, message handling

**API Layer (src/api/):**
- Axios-based HTTP client with interceptors
- Automatic token injection
- Error handling and retry logic

## Development Workflows

### Adding a New API Endpoint

1. **Create Pydantic schemas** (app/schemas/):
```python
class ExampleCreate(BaseModel):
    name: str

class ExampleResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
```

2. **Create database model** (app/models/):
```python
class Example(Base):
    __tablename__ = "examples"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
```

3. **Create repository** (app/repositories/):
```python
class ExampleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str) -> Example:
        example = Example(name=name)
        self.db.add(example)
        self.db.commit()
        self.db.refresh(example)
        return example
```

4. **Create service** (app/services/):
```python
class ExampleService:
    def __init__(self, db: Session):
        self.repository = ExampleRepository(db)

    async def create_example(self, name: str):
        return self.repository.create(name)
```

5. **Create API route** (app/api/v1/):
```python
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user

router = APIRouter(prefix="/examples", tags=["examples"])

@router.post("/", response_model=ExampleResponse)
async def create_example(
    data: ExampleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ExampleService(db)
    return await service.create_example(data.name)
```

6. **Register router** in `app/api/v1/__init__.py`

7. **Create migration**:
```bash
alembic revision --autogenerate -m "add examples table"
alembic upgrade head
```

### Adding a New LangChain Tool

1. Create tool file in `app/langchain_integration/tools/`:
```python
from langchain.tools import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Description for the agent"

    def _run(self, query: str) -> str:
        # Tool implementation
        return result
```

2. Register in `app/langchain_integration/tools/__init__.py`

3. Add to agent executor in `app/langchain_integration/agent_executor.py`

### Database Schema Changes

**ALWAYS use Alembic for schema changes:**

```bash
# Create migration
alembic revision --autogenerate -m "add new column"

# Review generated migration in migrations/versions/
# Edit if needed (Alembic doesn't catch everything)

# Apply migration
alembic upgrade head

# If something goes wrong
alembic downgrade -1
```

**Never** modify database schema directly in production.

## Important Conventions

### Code Style

- **Backend**: PEP 8, Black formatting, 100 char line length
- **Frontend**: TypeScript strict mode, Vue 3 Composition API
- **Imports**: Use absolute imports, sorted with isort
- **Type hints**: Required for all Python functions
- **Error handling**: Use custom exceptions with error codes

### Security

- **JWT tokens**: 7 days access, 30 days refresh (configurable)
- **Password**: Bcrypt with 12 rounds, min 8 chars
- **Login protection**: 5 attempts, 15 min lockout
- **Rate limiting**: 100/min general, 5/min login, 20/min LLM
- **Input validation**: All inputs validated via Pydantic
- **SQL injection**: Prevented via SQLAlchemy ORM (never raw SQL)

### Testing

- **Backend**: pytest with fixtures in `conftest.py`
- **Frontend**: Vitest with Vue Test Utils
- **Coverage target**: >80% overall, >90% for services
- **Test naming**: `test_<function_name>_<scenario>`
- **Fixtures**: Reusable test data in conftest.py

### Git Commits

Follow Conventional Commits:
```
feat(auth): add email verification
fix(rag): correct similarity threshold
docs(api): update endpoint documentation
refactor(service): simplify conversation logic
test(agent): add tool execution tests
```

## Configuration

### Environment Variables

Required:
- `DASHSCOPE_API_KEY`: Tongyi Qianwen API key
- `SECRET_KEY`: JWT secret (min 32 chars)
- `DATABASE_URL`: MySQL connection string
- `REDIS_URL`: Redis connection string

See `.env.example` files in backend/ and frontend/ for full list.

### Docker Deployment

```bash
# Backend + MySQL + Redis
cd backend
cp .env.example .env
# Edit .env with your values
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Troubleshooting

### Backend won't start
- Check `docker-compose logs backend`
- Verify DATABASE_URL and REDIS_URL
- Ensure MySQL and Redis are healthy: `docker-compose ps`

### Database connection errors
- Check MySQL is running: `docker-compose ps mysql`
- Test connection: `docker-compose exec mysql mysql -u root -p`
- Verify credentials in .env

### LLM API errors
- Verify DASHSCOPE_API_KEY is set
- Check API quota at DashScope console
- Review logs for specific error codes

### Frontend API errors
- Check backend is running on port 8000
- Verify VITE_API_BASE_URL in frontend/.env
- Check browser console for CORS errors

### Migration conflicts
- Never edit applied migrations
- Create new migration to fix issues
- Use `alembic downgrade` to rollback if needed

## Key Files Reference

- `backend/app/main.py`: FastAPI app setup, middleware, lifespan events
- `backend/app/config.py`: All configuration classes
- `backend/app/dependencies.py`: Authentication dependencies
- `backend/app/core/security.py`: JWT, password hashing
- `backend/app/core/llm.py`: LLM configuration (patched Tongyi)
- `backend/docker-compose.yml`: Service orchestration
- `frontend/src/stores/auth.ts`: Authentication state
- `frontend/src/api/index.ts`: API client setup
- `frontend/vite.config.ts`: Vite configuration, proxy setup
